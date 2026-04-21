import argparse
from datetime import datetime, timedelta
from pathlib import Path

from stock_pipeline import (
    PipelineConfig,
    fetch_stock_and_index_data,
    load_pipeline_config,
    train_mlp,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A-share 5-day-up MLP pipeline.")
    parser.add_argument(
        "--config",
        default="configs/stock_train.yaml",
        help="YAML config file path",
    )
    parser.add_argument("--start-date", default=None, help="e.g. 2021-04-20")
    parser.add_argument("--end-date", default=None, help="e.g. 2026-04-20")
    parser.add_argument("--stock-data-file", default=None)
    parser.add_argument("--index-data-file", default=None)
    parser.add_argument("--model-file", default=None)
    parser.add_argument("--window-size", type=int, default=None)
    parser.add_argument("--horizon", type=int, default=None)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument("--hidden-dim", type=int, default=None)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument(
        "--mode",
        choices=["fetch", "train", "all"],
        default="all",
        help="fetch: only fetch raw data; train: only train from existing file; all: fetch then train",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    if config_path.exists():
        config = load_pipeline_config(config_path)
    else:
        default_end = datetime.now().strftime("%Y-%m-%d")
        default_start = (datetime.now() - timedelta(days=365 * 5 + 5)).strftime(
            "%Y-%m-%d"
        )
        config = PipelineConfig(
            start_date=default_start,
            end_date=default_end,
            stock_data_file=Path("data/all_stock_daily_5y.csv"),
            index_data_file=Path("data/index_daily_5y.csv"),
            model_file=Path("artifacts/stock_up_mlp.pt"),
        )
    # CLI overrides only when explicitly provided.
    if args.start_date is not None:
        config.start_date = args.start_date
    if args.end_date is not None:
        config.end_date = args.end_date
    if args.stock_data_file is not None:
        config.stock_data_file = Path(args.stock_data_file)
    if args.index_data_file is not None:
        config.index_data_file = Path(args.index_data_file)
    if args.model_file is not None:
        config.model_file = Path(args.model_file)
    if args.window_size is not None:
        config.window_size = args.window_size
    if args.horizon is not None:
        config.horizon = args.horizon
    if args.max_samples is not None:
        config.max_samples = args.max_samples
    if args.batch_size is not None:
        config.batch_size = args.batch_size
    if args.epochs is not None:
        config.epochs = args.epochs
    if args.learning_rate is not None:
        config.learning_rate = args.learning_rate
    if args.hidden_dim is not None:
        config.hidden_dim = args.hidden_dim
    if args.workers is not None:
        config.workers = args.workers

    if args.mode in ("fetch", "all"):
        fetch_stock_and_index_data(config)
    if args.mode in ("train", "all"):
        train_mlp(config)


if __name__ == "__main__":
    main()
