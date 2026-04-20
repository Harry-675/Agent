from dataclasses import dataclass
from pathlib import Path


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
    workers: int = 4
