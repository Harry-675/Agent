from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from torch import nn
from torch.utils.data import DataLoader
from tqdm import tqdm

from stock_pipeline.config import PipelineConfig
from stock_pipeline.dataset import StockIndexDataset, build_samples
from stock_pipeline.modeling import MLPClassifier


def _resolve_device_ids(config: PipelineConfig) -> Optional[List[int]]:
    n = torch.cuda.device_count()
    if n <= 0:
        return None
    if config.cuda_device_ids is None:
        return list(range(n))
    ids = [i for i in config.cuda_device_ids if 0 <= i < n]
    if not ids:
        print(f"[train] cuda_device_ids invalid or out of range, using 0..{n-1}")
        return list(range(n))
    return ids


def _unwrap_model(model: nn.Module) -> nn.Module:
    return model.module if isinstance(model, nn.DataParallel) else model


def _split_by_time(
    X: np.ndarray, y: np.ndarray, d: np.ndarray, train_ratio: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    order = np.argsort(d)
    X = X[order]
    y = y[order]
    split = int(len(y) * train_ratio)
    return X[:split], y[:split], X[split:], y[split:]


def _split_by_interleaved_time_blocks(
    X: np.ndarray,
    y: np.ndarray,
    d: np.ndarray,
    time_block_days: int,
    test_blocks_every: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if time_block_days <= 0:
        raise ValueError("time_block_days must be > 0")
    if test_blocks_every <= 1:
        raise ValueError("test_blocks_every must be > 1")

    order = np.argsort(d)
    X = X[order]
    y = y[order]
    d = d[order]

    day_idx = d.astype("datetime64[D]").astype(np.int64)
    block_ids = (day_idx - day_idx.min()) // time_block_days
    test_mask = (block_ids % test_blocks_every) == (test_blocks_every - 1)
    train_mask = ~test_mask

    # Fallback for pathological cases (e.g., too short span)
    if train_mask.sum() == 0 or test_mask.sum() == 0:
        return _split_by_time(X, y, d, train_ratio=0.8)

    return X[train_mask], y[train_mask], X[test_mask], y[test_mask]


def train_mlp(config: PipelineConfig) -> None:
    if not config.stock_data_file.exists():
        raise FileNotFoundError(f"stock data not found: {config.stock_data_file}")
    if not config.index_data_file.exists():
        raise FileNotFoundError(f"index data not found: {config.index_data_file}")

    stock_df = pd.read_csv(config.stock_data_file, dtype={"code": "string"})
    index_df = pd.read_csv(config.index_data_file, dtype={"index_code": "string"})
    X, y, d = build_samples(
        stock_df=stock_df,
        index_df=index_df,
        window_size=config.window_size,
        horizon=config.horizon,
        max_samples=config.max_samples,
    )
    print(f"[train] feature dim={X.shape[1]} (samples={len(y)})")
    if config.split_mode == "time_tail":
        X_train, y_train, X_test, y_test = _split_by_time(X, y, d, config.train_ratio)
        print(
            f"[split] mode=time_tail, train_ratio={config.train_ratio:.2f}, "
            f"train={len(y_train)}, test={len(y_test)}"
        )
    elif config.split_mode == "interleaved_time":
        X_train, y_train, X_test, y_test = _split_by_interleaved_time_blocks(
            X=X,
            y=y,
            d=d,
            time_block_days=config.time_block_days,
            test_blocks_every=config.test_blocks_every,
        )
        test_ratio = len(y_test) / max(len(y_train) + len(y_test), 1)
        print(
            f"[split] mode=interleaved_time, block_days={config.time_block_days}, "
            f"test_every={config.test_blocks_every}, train={len(y_train)}, "
            f"test={len(y_test)}, test_ratio={test_ratio:.3f}"
        )
    else:
        raise ValueError(
            f"Unsupported split_mode={config.split_mode}. "
            "Use 'time_tail' or 'interleaved_time'."
        )

    train_ds = StockIndexDataset(X_train, y_train)
    test_ds = StockIndexDataset(X_test, y_test)
    train_loader = DataLoader(train_ds, batch_size=config.batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=config.batch_size, shuffle=False)

    if torch.cuda.is_available():
        device_ids = _resolve_device_ids(config)
        device = torch.device(f"cuda:{device_ids[0]}")
        model = MLPClassifier(input_dim=X.shape[1], hidden_dim=config.hidden_dim).to(device)
        if (
            config.multi_gpu
            and len(device_ids) > 1
        ):
            model = nn.DataParallel(model, device_ids=device_ids)
            print(f"[train] DataParallel enabled on GPUs: {device_ids}")
        else:
            print(f"[train] single GPU: cuda:{device_ids[0]}")
    else:
        device = torch.device("cpu")
        model = MLPClassifier(input_dim=X.shape[1], hidden_dim=config.hidden_dim).to(device)
        print("[train] CUDA not available, using CPU")

    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)

    for epoch in range(1, config.epochs + 1):
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        batch_pbar = tqdm(
            train_loader,
            desc=f"Epoch {epoch}/{config.epochs}",
            leave=True,
            dynamic_ncols=True,
        )
        for xb, yb in batch_pbar:
            xb = xb.to(device)
            yb = yb.to(device)
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            bs = xb.size(0)
            total_loss += float(loss.item()) * bs
            with torch.no_grad():
                pred = (torch.sigmoid(logits) >= 0.5).float()
                correct += int((pred == yb).sum().item())
            total += bs
            running_acc = correct / max(total, 1)
            batch_pbar.set_postfix(
                loss=f"{loss.item():.4f}",
                acc=f"{running_acc:.4f}",
            )
        batch_pbar.close()
        avg_loss = total_loss / max(total, 1)
        train_acc = correct / max(total, 1)
        print(
            f"[epoch {epoch:02d}] train_loss={avg_loss:.6f} train_acc={train_acc:.4f} "
            f"({correct}/{total})"
        )

    model.eval()
    probas = []
    labels = []
    with torch.no_grad():
        for xb, yb in tqdm(
            test_loader,
            desc="Evaluating",
            leave=True,
            dynamic_ncols=True,
        ):
            xb = xb.to(device)
            logits = model(xb)
            prob = torch.sigmoid(logits).cpu().numpy()
            probas.append(prob)
            labels.append(yb.numpy())
    y_prob = np.concatenate(probas)
    y_true = np.concatenate(labels).astype(np.int64)
    y_pred = (y_prob >= 0.5).astype(np.int64)

    auc = roc_auc_score(y_true, y_prob)
    acc = accuracy_score(y_true, y_pred)
    print(f"[train] train samples={len(train_ds)}, test samples={len(test_ds)}")
    print(f"[eval] ROC-AUC={auc:.4f} accuracy={acc:.4f}")
    print(classification_report(y_true, y_pred, digits=4))

    config.model_file.parent.mkdir(parents=True, exist_ok=True)
    module = _unwrap_model(model)
    torch.save(
        {
            "state_dict": module.state_dict(),
            "input_dim": X.shape[1],
            "hidden_dim": config.hidden_dim,
            "window_size": config.window_size,
            "horizon": config.horizon,
        },
        Path(config.model_file),
    )
    print(f"[train] model saved: {config.model_file}")
