from datetime import datetime, timedelta
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
import io
from pathlib import Path
from contextlib import redirect_stdout
from typing import Dict, List, Optional

import baostock as bs
import pandas as pd
from tqdm import tqdm

from stock_pipeline.config import PipelineConfig

STOCK_COLUMNS = ["code", "date", "open", "high", "low", "close", "volume"]
INDEX_COLUMNS = ["index_code", "date", "open", "high", "low", "close", "volume"]

INDEX_MAP: Dict[str, str] = {
    "sse": "sh.000001",  # 上证指数
    "szse": "sz.399001",  # 深证成指
    "gem": "sz.399006",  # 创业板指
    "star": "sh.000688",  # 科创50
}


def stock_to_index(stock_code: str) -> str:
    if stock_code.startswith("sh.688"):
        return INDEX_MAP["star"]
    if stock_code.startswith("sh.6"):
        return INDEX_MAP["sse"]
    if stock_code.startswith("sz.3"):
        return INDEX_MAP["gem"]
    return INDEX_MAP["szse"]


def _login() -> None:
    with redirect_stdout(io.StringIO()):
        lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"baostock login failed: {lg.error_msg}")


def _logout() -> None:
    try:
        with redirect_stdout(io.StringIO()):
            bs.logout()
    except Exception:
        pass


def _latest_trading_date(end_date: str) -> str:
    start = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=30)).strftime(
        "%Y-%m-%d"
    )
    rs = bs.query_trade_dates(start_date=start, end_date=end_date)
    if rs.error_code != "0":
        raise RuntimeError(f"query_trade_dates failed: {rs.error_msg}")
    dates: List[str] = []
    while rs.next():
        row = rs.get_row_data()
        if len(row) >= 2 and row[1] == "1":
            dates.append(row[0])
    if not dates:
        raise RuntimeError("No trading dates found.")
    return dates[-1]


def _resolve_stock_universe_date(end_date: str, max_backtrack_days: int = 10) -> str:
    """Find nearest date where query_all_stock returns rows."""
    base = datetime.strptime(end_date, "%Y-%m-%d").date()
    for offset in range(max_backtrack_days + 1):
        day = (base - timedelta(days=offset)).strftime("%Y-%m-%d")
        rs = bs.query_all_stock(day=day)
        if rs.error_code != "0":
            continue
        if rs.next():
            return day
    # fallback to last trading date if all probes failed
    return _latest_trading_date(end_date)


def _fetch_history_rows(code: str, start_date: str, end_date: str) -> List[List[str]]:
    rs = bs.query_history_k_data_plus(
        code=code,
        fields="date,open,high,low,close,volume",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="3",
    )
    if rs.error_code != "0":
        raise RuntimeError(f"{code} fetch failed: {rs.error_msg}")
    rows: List[List[str]] = []
    while rs.next():
        rows.append(rs.get_row_data())
    return rows


def _read_existing_data(path: Path, required_cols: List[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=required_cols)
    try:
        df = pd.read_csv(path, dtype="string")
    except Exception:
        return pd.DataFrame(columns=required_cols)
    if df.empty:
        return pd.DataFrame(columns=required_cols)
    if not set(required_cols).issubset(df.columns):
        return pd.DataFrame(columns=required_cols)
    return df


def _next_date(date_text: str) -> str:
    d = datetime.strptime(date_text, "%Y-%m-%d").date()
    return (d + timedelta(days=1)).strftime("%Y-%m-%d")


def _merge_and_save(
    existing_df: pd.DataFrame,
    new_rows: List[List[str]],
    columns: List[str],
    path: Path,
    key_cols: List[str],
) -> pd.DataFrame:
    new_df = pd.DataFrame(new_rows, columns=columns)
    combined = pd.concat([existing_df, new_df], ignore_index=True)
    if combined.empty:
        combined = pd.DataFrame(columns=columns)
    else:
        combined = combined.drop_duplicates(subset=key_cols, keep="last")
        if "date" in combined.columns:
            combined = combined.sort_values(key_cols)
    combined.to_csv(path, index=False, encoding="utf-8-sig")
    return combined


def _chunked(items: List[str], chunk_size: int) -> List[List[str]]:
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def _fetch_stock_chunk(
    codes: List[str], start_date: str, end_date: str
) -> Dict[str, List[List[str]]]:
    rows_out: List[List[str]] = []
    failed: List[str] = []
    with redirect_stdout(io.StringIO()):
        lg = bs.login()
    if lg.error_code != "0":
        return {"rows": rows_out, "failed": codes}
    try:
        for code in codes:
            try:
                rows = _fetch_history_rows(code, start_date, end_date)
                rows_out.extend([[code] + r for r in rows])
            except Exception:
                failed.append(code)
    finally:
        try:
            with redirect_stdout(io.StringIO()):
                bs.logout()
        except Exception:
            pass
    return {"rows": rows_out, "failed": failed}


def fetch_stock_and_index_data(config: PipelineConfig) -> None:
    config.stock_data_file.parent.mkdir(parents=True, exist_ok=True)
    config.index_data_file.parent.mkdir(parents=True, exist_ok=True)
    existing_stock_df = _read_existing_data(config.stock_data_file, STOCK_COLUMNS)
    existing_index_df = _read_existing_data(config.index_data_file, INDEX_COLUMNS)
    _login()
    try:
        stock_last_date: Optional[str] = None
        if not existing_stock_df.empty and "date" in existing_stock_df.columns:
            stock_last_date = str(existing_stock_df["date"].max())
        stock_start = config.start_date
        if stock_last_date:
            stock_start = max(stock_start, _next_date(stock_last_date))

        stock_rows: List[List[str]] = []
        if stock_start <= config.end_date:
            ref_date = _resolve_stock_universe_date(config.end_date)
            all_rs = bs.query_all_stock(day=ref_date)
            if all_rs.error_code != "0":
                raise RuntimeError(f"query_all_stock failed: {all_rs.error_msg}")
            print(
                f"[fetch-stock] use stock universe date: {ref_date}, "
                f"incremental range: {stock_start} -> {config.end_date}"
            )

            stock_codes: List[str] = []
            while all_rs.next():
                row = all_rs.get_row_data()
                if row and row[0] and row[0].startswith(("sh.6", "sh.688", "sz.0", "sz.3")):
                    stock_codes.append(row[0])

            workers = max(1, int(config.workers))
            # 小块：避免单 chunk 卡住时长时间无进度；上限由配置控制
            raw_chunk = max(10, len(stock_codes) // max(workers * 8, 1))
            chunk_size = min(int(config.fetch_max_chunk_size), max(10, raw_chunk))
            code_chunks = _chunked(stock_codes, chunk_size)
            print(
                f"[fetch-stock] multiprocessing enabled: workers={workers}, chunks={len(code_chunks)}, "
                f"chunk_size={chunk_size}, chunk_timeout_sec={config.fetch_chunk_timeout_sec}, "
                f"stall_rounds={config.fetch_stall_rounds}"
            )
            failed_codes: List[str] = []
            total_chunks = len(code_chunks)
            timeout_sec = max(30, int(config.fetch_chunk_timeout_sec))
            stall_limit = max(1, int(config.fetch_stall_rounds))

            with ProcessPoolExecutor(max_workers=workers) as executor:
                future_to_chunk = {
                    executor.submit(
                        _fetch_stock_chunk, chunk, stock_start, config.end_date
                    ): chunk
                    for chunk in code_chunks
                }
                pending = set(future_to_chunk.keys())
                completed = 0
                stall_rounds = 0
                with tqdm(
                    total=total_chunks,
                    desc="Fetching stock daily data",
                    unit="chunk",
                    dynamic_ncols=True,
                ) as pbar:
                    while pending:
                        done, pending = wait(
                            pending,
                            timeout=timeout_sec,
                            return_when=FIRST_COMPLETED,
                        )
                        if not done:
                            stall_rounds += 1
                            print(
                                f"[warn] fetch stall {stall_rounds}/{stall_limit}: "
                                f"no chunk finished in {timeout_sec}s, pending={len(pending)}"
                            )
                            if stall_rounds >= stall_limit:
                                pending_chunks = [future_to_chunk[f] for f in pending]
                                print(
                                    "[fetch-stock] pool appears stuck; shutdown and serial retry "
                                    f"{len(pending_chunks)} pending chunks"
                                )
                                executor.shutdown(wait=False, cancel_futures=True)
                                # 释放主进程会话，避免与子任务内 login 冲突
                                _logout()
                                for chunk in pending_chunks:
                                    try:
                                        sr = _fetch_stock_chunk(
                                            chunk, stock_start, config.end_date
                                        )
                                        stock_rows.extend(sr.get("rows", []))
                                        failed_codes.extend(sr.get("failed", []))
                                    except Exception as exc:
                                        print(
                                            f"[warn] serial chunk failed ({len(chunk)} codes): {exc}"
                                        )
                                pbar.update(len(pending_chunks))
                                completed += len(pending_chunks)
                                pending.clear()
                                _login()
                                break
                            continue

                        stall_rounds = 0
                        for fut in done:
                            chunk = future_to_chunk.get(fut)
                            try:
                                result = fut.result(timeout=0)
                            except Exception as exc:
                                print(
                                    f"[warn] chunk failed ({len(chunk) if chunk else 0} codes): {exc}"
                                )
                                result = {"rows": [], "failed": list(chunk or [])}
                            stock_rows.extend(result.get("rows", []))
                            failed_codes.extend(result.get("failed", []))
                            completed += 1
                            pbar.update(1)
                            if completed % 5 == 0 or completed == total_chunks:
                                print(
                                    f"[fetch-stock] chunks completed: {completed}/{total_chunks}, rows={len(stock_rows)}"
                                )
            if failed_codes:
                print(f"[fetch-stock] failed stocks: {len(failed_codes)}")
        else:
            print("[fetch-stock] up-to-date, no new stock data to append.")

        stock_df = _merge_and_save(
            existing_df=existing_stock_df,
            new_rows=stock_rows,
            columns=STOCK_COLUMNS,
            path=config.stock_data_file,
            key_cols=["code", "date"],
        )
        print(f"[fetch-stock] saved: {config.stock_data_file}, rows={len(stock_df)}")

        # Multiprocessing stock fetch can run for several minutes; refresh login
        # before index queries to avoid "用户未登录" due to session timeout/state drift.
        _logout()
        _login()

        index_last_date: Optional[str] = None
        if not existing_index_df.empty and "date" in existing_index_df.columns:
            index_last_date = str(existing_index_df["date"].max())
        index_start = config.start_date
        if index_last_date:
            index_start = max(index_start, _next_date(index_last_date))

        index_rows: List[List[str]] = []
        if index_start <= config.end_date:
            print(
                f"[fetch-index] incremental range: {index_start} -> {config.end_date}"
            )
            for idx_code in tqdm(
                INDEX_MAP.values(), desc="Fetching index daily data", unit="index"
            ):
                try:
                    rows = _fetch_history_rows(idx_code, index_start, config.end_date)
                    for r in rows:
                        index_rows.append([idx_code] + r)
                except Exception as exc:
                    print(f"[warn] skip index {idx_code}: {exc}")
        else:
            print("[fetch-index] up-to-date, no new index data to append.")
        index_df = _merge_and_save(
            existing_df=existing_index_df,
            new_rows=index_rows,
            columns=INDEX_COLUMNS,
            path=config.index_data_file,
            key_cols=["index_code", "date"],
        )
        print(f"[fetch-index] saved: {config.index_data_file}, rows={len(index_df)}")
    finally:
        _logout()
