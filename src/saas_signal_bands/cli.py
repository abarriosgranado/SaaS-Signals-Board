from __future__ import annotations

import argparse
from pathlib import Path

from saas_signal_bands.bands import add_signal_bands
from saas_signal_bands.dashboard import build_dashboard
from saas_signal_bands.data import load_ravenstack
from saas_signal_bands.metrics import build_monthly_metrics
from saas_signal_bands.plotting import plot_signal_bands


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SaaS Signal Bands charts.")
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--metric", default="mrr")
    parser.add_argument("--window", type=int, default=12)
    parser.add_argument("--multiplier", type=float, default=2.0)
    parser.add_argument("--gross-margin", type=float, default=0.80)
    parser.add_argument("--dashboard", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        data = load_ravenstack(args.data_dir)
    except FileNotFoundError as exc:
        raise SystemExit(
            f"{exc}\n\n"
            "Download the Kaggle dataset and place the CSV files in data/raw/:\n"
            "https://www.kaggle.com/datasets/rivalytics/saas-subscription-and-churn-analytics-dataset"
        ) from exc

    monthly = build_monthly_metrics(
        data["subscriptions"],
        data["churn_events"],
        gross_margin=args.gross_margin,
    )

    if args.dashboard:
        dashboard_path = build_dashboard(
            monthly,
            output_dir=args.output_dir,
            window=args.window,
        )
        print(f"Wrote {dashboard_path}")
        return

    with_bands = add_signal_bands(
        monthly,
        metric=args.metric,
        window=args.window,
        multiplier=args.multiplier,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    monthly_path = args.output_dir / "monthly_metrics.csv"
    chart_path = args.output_dir / f"{args.metric}_signal_bands.svg"
    with_bands.to_csv(monthly_path, index=False)
    plot_signal_bands(with_bands, args.metric, chart_path)

    signal_counts = with_bands[f"{args.metric}_signal"].value_counts().to_dict()
    print(f"Wrote {monthly_path}")
    print(f"Wrote {chart_path}")
    print(f"Signals for {args.metric}: {signal_counts}")


if __name__ == "__main__":
    main()
