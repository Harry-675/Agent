import argparse
from pathlib import Path

from stock_pipeline.config import PipelineConfig, load_pipeline_config
from stock_pipeline.inference import predict_stock_up


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict whether a stock may go up within 5 trading days."
    )
    parser.add_argument("--stock", required=True, help="股票代码或名称，例如 sh.600000 或 浦发银行")
    parser.add_argument(
        "--date",
        default=None,
        help="可选，预测基准日期(YYYY-MM-DD)。不传则自动使用最新交易日。",
    )
    parser.add_argument("--config", default="configs/stock_train.yaml", help="YAML配置文件路径")
    parser.add_argument("--model-file", default=None, help="可选，覆盖模型路径")
    parser.add_argument("--window-size", type=int, default=None, help="可选，覆盖窗口大小")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    if config_path.exists():
        config = load_pipeline_config(config_path)
    else:
        config = PipelineConfig(
            start_date="2021-01-01",
            end_date="2026-01-01",
            stock_data_file=Path("data/all_stock_daily_5y.csv"),
            index_data_file=Path("data/index_daily_5y.csv"),
            model_file=Path("artifacts/stock_up_mlp.pt"),
        )

    if args.model_file:
        config.model_file = Path(args.model_file)
    if args.window_size:
        config.window_size = args.window_size

    if not config.model_file.exists():
        raise FileNotFoundError(f"Model file not found: {config.model_file}")

    result = predict_stock_up(config, stock=args.stock, date_text=args.date)
    print("=== 推理结果 ===")
    print(f"股票: {result['stock_name']} ({result['stock_code']})")
    print(f"基准交易日: {result['trade_date']}")
    print(f"特征截至日: {result['feature_asof_date']}")
    print(f"对应指数: {result['index_code']}")
    print(f"未来5日上涨概率: {result['up_prob_5d']:.4f}")
    print(f"预测标签: {result['prediction']} ({result['prediction_text']})")


if __name__ == "__main__":
    main()
