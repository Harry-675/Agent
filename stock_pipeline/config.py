from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class PipelineConfig:
    start_date: str
    end_date: str
    stock_data_file: Path
    index_data_file: Path
    model_file: Path
    window_size: int = 120
    horizon: int = 5
    max_samples: int = 500_000
    batch_size: int = 1024
    epochs: int = 15
    learning_rate: float = 1e-3
    hidden_dim: int = 256
    train_ratio: float = 0.8
    split_mode: str = "interleaved_time"
    time_block_days: int = 20
    test_blocks_every: int = 5
    workers: int = 4
    # 多进程抓取：单 chunk 最长等待（秒）；连续多轮无完成则放弃进程池并串行补抓
    fetch_chunk_timeout_sec: int = 180
    fetch_stall_rounds: int = 5
    fetch_max_chunk_size: int = 30
    # 训练多 GPU：DataParallel（多卡单进程）；cuda_device_ids 如 "0,1" 或 None=全部可见卡
    multi_gpu: bool = True
    cuda_device_ids: Optional[List[int]] = None


def _to_path(value: Any, default: str) -> Path:
    if value is None:
        return Path(default)
    return Path(str(value))


def load_pipeline_config(config_path: Path) -> PipelineConfig:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        raw: Dict[str, Any] = yaml.safe_load(f) or {}

    data_cfg = raw.get("data", {})
    model_cfg = raw.get("model", {})
    train_cfg = raw.get("training", {})
    fetch_cfg = raw.get("fetch", {})

    return PipelineConfig(
        start_date=str(data_cfg.get("start_date", "2021-01-01")),
        end_date=str(data_cfg.get("end_date", "2026-01-01")),
        stock_data_file=_to_path(data_cfg.get("stock_data_file"), "data/all_stock_daily_5y.csv"),
        index_data_file=_to_path(data_cfg.get("index_data_file"), "data/index_daily_5y.csv"),
        model_file=_to_path(model_cfg.get("model_file"), "artifacts/stock_up_mlp.pt"),
        window_size=int(model_cfg.get("window_size", 120)),
        horizon=int(model_cfg.get("horizon", 5)),
        hidden_dim=int(model_cfg.get("hidden_dim", 256)),
        max_samples=int(train_cfg.get("max_samples", 500_000)),
        batch_size=int(train_cfg.get("batch_size", 1024)),
        epochs=int(train_cfg.get("epochs", 15)),
        learning_rate=float(train_cfg.get("learning_rate", 1e-3)),
        train_ratio=float(train_cfg.get("train_ratio", 0.8)),
        split_mode=str(train_cfg.get("split_mode", "interleaved_time")),
        time_block_days=int(train_cfg.get("time_block_days", 20)),
        test_blocks_every=int(train_cfg.get("test_blocks_every", 5)),
        workers=int(fetch_cfg.get("workers", 4)),
        fetch_chunk_timeout_sec=int(fetch_cfg.get("chunk_timeout_sec", 180)),
        fetch_stall_rounds=int(fetch_cfg.get("stall_rounds", 5)),
        fetch_max_chunk_size=int(fetch_cfg.get("max_chunk_size", 30)),
        multi_gpu=bool(train_cfg.get("multi_gpu", True)),
        cuda_device_ids=_parse_cuda_device_ids(train_cfg.get("cuda_device_ids")),
    )


def _parse_cuda_device_ids(raw: Any) -> Optional[List[int]]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, list):
        return [int(x) for x in raw]
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        return [int(p) for p in parts] if parts else None
    return None
