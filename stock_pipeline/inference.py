import io
import re
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from typing import Optional, Tuple

import baostock as bs
import numpy as np
import pandas as pd
import torch

from stock_pipeline.config import PipelineConfig
from stock_pipeline.data_fetch import stock_to_index
from stock_pipeline.dataset import FEATURE_COLS, _zscore
from stock_pipeline.modeling import MLPClassifier


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


def _resolve_trade_date(date_text: Optional[str]) -> str:
    if date_text:
        end_date = date_text
    else:
        end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=30)).strftime(
        "%Y-%m-%d"
    )
    rs = bs.query_trade_dates(start_date=start_date, end_date=end_date)
    if rs.error_code != "0":
        raise RuntimeError(f"query_trade_dates failed: {rs.error_msg}")
    trading_days = []
    while rs.next():
        row = rs.get_row_data()
        if len(row) >= 2 and row[1] == "1":
            trading_days.append(row[0])
    if not trading_days:
        raise RuntimeError(f"No trading day found before {end_date}.")
    return trading_days[-1]


def _normalize_stock_code_or_name(stock: str, trade_date: str) -> Tuple[str, str]:
    s = stock.strip()
    if re.match(r"^(sh|sz)\.\d{6}$", s.lower()):
        return s.lower(), s

    rs = bs.query_all_stock(day=trade_date)
    if rs.error_code != "0":
        raise RuntimeError(f"query_all_stock failed: {rs.error_msg}")
    candidates = []
    while rs.next():
        row = rs.get_row_data()
        if len(row) < 3:
            continue
        code, _, name = row[0], row[1], row[2]
        if name == s:
            return code, name
        if s in name:
            candidates.append((code, name))
    if candidates:
        return candidates[0][0], candidates[0][1]
    raise ValueError(f"Cannot resolve stock name/code: {stock}")


def _fetch_k_data(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    fields = "date," + ",".join(FEATURE_COLS)
    rs = bs.query_history_k_data_plus(
        code=code,
        fields=fields,
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="3",
    )
    if rs.error_code != "0":
        raise RuntimeError(f"{code} fetch failed: {rs.error_msg}")
    rows = []
    while rs.next():
        rows.append(rs.get_row_data())
    cols = ["date"] + list(FEATURE_COLS)
    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    for c in FEATURE_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna().sort_values("date")
    return df


def _build_infer_feature(
    stock_df: pd.DataFrame, index_df: pd.DataFrame, window_size: int
) -> Tuple[np.ndarray, str]:
    merged = stock_df.merge(index_df, on="date", how="inner", suffixes=("_stock", "_index"))
    if len(merged) < window_size:
        raise RuntimeError(
            f"Not enough aligned data for inference: {len(merged)} < window_size({window_size})."
        )
    tail = merged.iloc[-window_size:]
    parts = []
    for col in FEATURE_COLS:
        parts.append(_zscore(tail[f"{col}_stock"].to_numpy(dtype=np.float64)))
    for col in FEATURE_COLS:
        parts.append(_zscore(tail[f"{col}_index"].to_numpy(dtype=np.float64)))
    feat = np.concatenate(parts).astype(np.float32)
    asof_date = str(tail["date"].iloc[-1].date())
    return feat, asof_date


def predict_stock_up(config: PipelineConfig, stock: str, date_text: Optional[str]) -> dict:
    _login()
    try:
        trade_date = _resolve_trade_date(date_text)
        code, resolved_name = _normalize_stock_code_or_name(stock, trade_date)
        index_code = stock_to_index(code)

        lookback_days = max(config.window_size * 3, 400)
        start_date = (
            datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=lookback_days)
        ).strftime("%Y-%m-%d")

        stock_df = _fetch_k_data(code, start_date, trade_date)
        index_df = _fetch_k_data(index_code, start_date, trade_date)
        feat, asof_date = _build_infer_feature(stock_df, index_df, config.window_size)
    finally:
        _logout()

    ckpt = torch.load(config.model_file, map_location="cpu")
    input_dim = int(ckpt.get("input_dim", len(feat)))
    hidden_dim = int(ckpt.get("hidden_dim", config.hidden_dim))
    model = MLPClassifier(input_dim=input_dim, hidden_dim=hidden_dim)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    x = torch.from_numpy(feat).unsqueeze(0)
    with torch.no_grad():
        prob = torch.sigmoid(model(x)).item()
    pred = 1 if prob >= 0.5 else 0
    return {
        "stock_code": code,
        "stock_name": resolved_name,
        "trade_date": trade_date,
        "feature_asof_date": asof_date,
        "index_code": index_code,
        "up_prob_5d": prob,
        "prediction": pred,
        "prediction_text": "未来5个交易日内可能上涨" if pred == 1 else "未来5个交易日内可能不涨",
    }
