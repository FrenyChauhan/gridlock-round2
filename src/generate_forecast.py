"""
Production Forecast Generator
================================
Input:  weekly_cluster_timeband.csv (from weekly_aggregation.py)
Output: weekly_forecast.csv -- one row per (cluster_id, time_band)
"""

import os
import pandas as pd
from src.utils import load_config


def generate_forecast(weekly_path: str, output_path: str) -> pd.DataFrame:
    weekly = pd.read_csv(weekly_path)
    weekly["week"] = pd.to_datetime(weekly["week"])
    weekly = weekly.sort_values(["cluster_id", "time_band", "week"])

    summary = (
        weekly.groupby(["cluster_id", "time_band"])
        .agg(
            predicted_violation_count=("violation_count", "mean"),
            historical_violation_count=("violation_count", "sum"),
            history_std=("violation_count", "std"),
            n_weeks_history=("violation_count", "count"),
            mean_severity_norm=("mean_severity_norm", "mean"),
            last_observed_week=("week", "max"),
        )
        .reset_index()
    )

    summary["history_std"] = summary["history_std"].fillna(0.0)
    summary["forecast_for_week_starting"] = summary["last_observed_week"] + pd.Timedelta(days=7)

    summary = summary.sort_values(["cluster_id", "time_band"]).reset_index(drop=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    summary.to_csv(output_path, index=False)

    print(f"Forecast generation complete.")
    print(f"  Series forecasted: {len(summary):,}")
    print(f"  Series with only 1 week of history: {(summary['n_weeks_history']==1).sum():,}")
    print(f"  Saved to: {output_path}")

    return summary


if __name__ == "__main__":
    config = load_config()
    weekly_path = config["forecasting"]["weekly_aggregation_path"]
    output_path = config["forecasting"]["weekly_forecast_path"]
    
    generate_forecast(weekly_path, output_path)
