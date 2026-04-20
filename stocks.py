import argparse
from datetime import datetime, timedelta
from pathlib import Path

from stock_pipeline import PipelineConfig, fetch_stock_and_index_data, train_mlp


def parse_args() -> argparse.Namespace:
    default_end = datetime.now().strftime("%Y-%m-%d")
    default_start = (datetime.now() - timedelta(days=365 * 5 + 5)).strftime("%Y-%m-%d")

    parser = argparse.ArgumentParser(description="A-share 5-day-up MLP pipeline.")
    parser.add_argument("--start-date", default=default_start, help="e.g. 2021-04-20")
    parser.add_argument("--end-date", default=default_end, help="e.g. 2026-04-20")
    parser.add_argument("--stock-data-file", default="data/all_stock_daily_5y.csv")
    parser.add_argument("--index-data-file", default="data/index_daily_5y.csv")
    parser.add_argument("--model-file", default="artifacts/stock_up_mlp.pt")
    parser.add_argument("--window-size", type=int, default=120)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--max-samples", type=int, default=500_000)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--mode",
        choices=["fetch", "train", "all"],
        default="all",
        help="fetch: only fetch raw data; train: only train from existing file; all: fetch then train",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = PipelineConfig(
        start_date=args.start_date,
        end_date=args.end_date,
        stock_data_file=Path(args.stock_data_file),
        index_data_file=Path(args.index_data_file),
        model_file=Path(args.model_file),
        window_size=args.window_size,
        horizon=args.horizon,
        max_samples=args.max_samples,
        batch_size=args.batch_size,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        hidden_dim=args.hidden_dim,
        workers=args.workers,
    )

    if args.mode in ("fetch", "all"):
        fetch_stock_and_index_data(config)
    if args.mode in ("train", "all"):
        train_mlp(config)


if __name__ == "__main__":
    main()
