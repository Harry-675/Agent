from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import classification_report, roc_auc_score
from torch import nn
from torch.utils.data import DataLoader

from stock_pipeline.config import PipelineConfig
from stock_pipeline.dataset import StockIndexDataset, build_samples
from stock_pipeline.modeling import MLPClassifier


def _split_by_time(
    X: np.ndarray, y: np.ndarray, d: np.ndarray, train_ratio: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    order = np.argsort(d)
    X = X[order]
    y = y[order]
    split = int(len(y) * train_ratio)
    return X[:split], y[:split], X[split:], y[split:]


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
    X_train, y_train, X_test, y_test = _split_by_time(X, y, d, config.train_ratio)

    train_ds = StockIndexDataset(X_train, y_train)
    test_ds = StockIndexDataset(X_test, y_test)
    train_loader = DataLoader(train_ds, batch_size=config.batch_size, shuffle=True)
    test_loader = DataLoader(test_ds, batch_size=config.batch_size, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MLPClassifier(input_dim=X.shape[1], hidden_dim=config.hidden_dim).to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)

    for epoch in range(1, config.epochs + 1):
        model.train()
        total_loss = 0.0
        for xb, yb in train_loader:
            xb = xb.to(device)
            yb = yb.to(device)
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item()) * xb.size(0)
        avg_loss = total_loss / max(len(train_ds), 1)
        print(f"[epoch {epoch:02d}] train_loss={avg_loss:.6f}")

    model.eval()
    probas = []
    labels = []
    with torch.no_grad():
        for xb, yb in test_loader:
            xb = xb.to(device)
            logits = model(xb)
            prob = torch.sigmoid(logits).cpu().numpy()
            probas.append(prob)
            labels.append(yb.numpy())
    y_prob = np.concatenate(probas)
    y_true = np.concatenate(labels).astype(np.int64)
    y_pred = (y_prob >= 0.5).astype(np.int64)

    auc = roc_auc_score(y_true, y_prob)
    print(f"[train] train samples={len(train_ds)}, test samples={len(test_ds)}")
    print(f"[eval] ROC-AUC={auc:.4f}")
    print(classification_report(y_true, y_pred, digits=4))

    config.model_file.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "input_dim": X.shape[1],
            "hidden_dim": config.hidden_dim,
            "window_size": config.window_size,
            "horizon": config.horizon,
        },
        Path(config.model_file),
    )
    print(f"[train] model saved: {config.model_file}")
