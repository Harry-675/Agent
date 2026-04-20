from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
import io
from pathlib import Path
from contextlib import redirect_stdout
from typing import Dict, List

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
    _login()
    try:
        ref_date = _resolve_stock_universe_date(config.end_date)
        all_rs = bs.query_all_stock(day=ref_date)
        if all_rs.error_code != "0":
            raise RuntimeError(f"query_all_stock failed: {all_rs.error_msg}")
        print(f"[fetch-stock] use stock universe date: {ref_date}")

        stock_codes: List[str] = []
        while all_rs.next():
            row = all_rs.get_row_data()
            if row and row[0] and row[0].startswith(("sh.6", "sh.688", "sz.0", "sz.3")):
                stock_codes.append(row[0])

        workers = max(1, int(config.workers))
        # Keep chunks smaller so progress bar updates more frequently.
        chunk_size = max(20, len(stock_codes) // max(workers * 8, 1))
        code_chunks = _chunked(stock_codes, chunk_size)
        print(
            f"[fetch-stock] multiprocessing enabled: workers={workers}, chunks={len(code_chunks)}, chunk_size~{chunk_size}"
        )
        stock_rows: List[List[str]] = []
        failed_codes: List[str] = []
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    _fetch_stock_chunk, chunk, config.start_date, config.end_date
                )
                for chunk in code_chunks
            ]
            completed = 0
            with tqdm(
                total=len(futures),
                desc="Fetching stock daily data",
                unit="chunk",
                dynamic_ncols=True,
            ) as pbar:
                for fut in as_completed(futures):
                    result = fut.result()
                    stock_rows.extend(result.get("rows", []))
                    failed_codes.extend(result.get("failed", []))
                    completed += 1
                    pbar.update(1)
                    # Extra plain logs for terminal/file viewers that don't render tqdm refresh.
                    if completed % 5 == 0 or completed == len(futures):
                        print(
                            f"[fetch-stock] chunks completed: {completed}/{len(futures)}, rows={len(stock_rows)}"
                        )
        if failed_codes:
            print(f"[fetch-stock] failed stocks: {len(failed_codes)}")

        stock_df = pd.DataFrame(stock_rows, columns=STOCK_COLUMNS)
        stock_df.to_csv(config.stock_data_file, index=False, encoding="utf-8-sig")
        print(f"[fetch-stock] saved: {config.stock_data_file}")

        # Multiprocessing stock fetch can run for several minutes; refresh login
        # before index queries to avoid "用户未登录" due to session timeout/state drift.
        _logout()
        _login()

        index_rows: List[List[str]] = []
        for idx_code in tqdm(
            INDEX_MAP.values(), desc="Fetching index daily data", unit="index"
        ):
            try:
                rows = _fetch_history_rows(idx_code, config.start_date, config.end_date)
                for r in rows:
                    index_rows.append([idx_code] + r)
            except Exception as exc:
                print(f"[warn] skip index {idx_code}: {exc}")
        index_df = pd.DataFrame(index_rows, columns=INDEX_COLUMNS)
        index_df.to_csv(config.index_data_file, index=False, encoding="utf-8-sig")
        print(f"[fetch-index] saved: {config.index_data_file}")
    finally:
        _logout()
