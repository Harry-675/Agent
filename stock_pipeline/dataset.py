from typing import List, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from stock_pipeline.data_fetch import stock_to_index


def _zscore(values: np.ndarray) -> np.ndarray:
    mean = values.mean()
    std = values.std() + 1e-8
    return (values - mean) / std


def build_samples(
    stock_df: pd.DataFrame,
    index_df: pd.DataFrame,
    window_size: int,
    horizon: int,
    max_samples: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    stock_df = stock_df.copy()
    index_df = index_df.copy()
    stock_df["date"] = pd.to_datetime(stock_df["date"])
    index_df["date"] = pd.to_datetime(index_df["date"])

    for c in ["close", "volume"]:
        stock_df[c] = pd.to_numeric(stock_df[c], errors="coerce")
        index_df[c] = pd.to_numeric(index_df[c], errors="coerce")

    idx_group = {
        code: g.sort_values("date")[["date", "close", "volume"]].dropna()
        for code, g in index_df.groupby("index_code")
    }

    x_list: List[np.ndarray] = []
    y_list: List[int] = []
    d_list: List[np.datetime64] = []

    for i, (code, g_stock) in enumerate(stock_df.groupby("code"), start=1):
        stock_sorted = g_stock.sort_values("date")[["date", "close", "volume"]].dropna()
        index_code = stock_to_index(str(code))
        if index_code not in idx_group:
            continue
        merged = stock_sorted.merge(
            idx_group[index_code],
            on="date",
            how="inner",
            suffixes=("_stock", "_index"),
        )
        if len(merged) < window_size + horizon + 1:
            continue

        s_close = merged["close_stock"].to_numpy(dtype=np.float64)
        s_vol = merged["volume_stock"].to_numpy(dtype=np.float64)
        i_close = merged["close_index"].to_numpy(dtype=np.float64)
        i_vol = merged["volume_index"].to_numpy(dtype=np.float64)
        dates = merged["date"].to_numpy()

        for t in range(window_size - 1, len(merged) - horizon):
            future = s_close[t + 1 : t + horizon + 1]
            label = 1 if np.max(future) > s_close[t] else 0

            feat = np.concatenate(
                [
                    _zscore(s_close[t - window_size + 1 : t + 1]),
                    _zscore(s_vol[t - window_size + 1 : t + 1]),
                    _zscore(i_close[t - window_size + 1 : t + 1]),
                    _zscore(i_vol[t - window_size + 1 : t + 1]),
                ]
            )
            x_list.append(feat.astype(np.float32))
            y_list.append(label)
            d_list.append(dates[t])

        if i % 500 == 0:
            print(f"[sample] processed {i} stocks")

    if not x_list:
        raise RuntimeError("No samples generated from input data.")

    X = np.asarray(x_list, dtype=np.float32)
    y = np.asarray(y_list, dtype=np.int64)
    d = np.asarray(d_list, dtype="datetime64[ns]")

    if len(y) > max_samples:
        rng = np.random.default_rng(42)
        pick = rng.choice(len(y), size=max_samples, replace=False)
        X, y, d = X[pick], y[pick], d[pick]

    return X, y, d


class StockIndexDataset(Dataset):
    def __init__(self, features: np.ndarray, labels: np.ndarray) -> None:
        self.features = torch.from_numpy(features).float()
        self.labels = torch.from_numpy(labels).float()

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int):
        return self.features[idx], self.labels[idx]
