"""
Stage 2 — Rolling / Lag Feature Construction
==============================================
Input:  weekly_cluster_timeband.csv (from Stage 1)
Output: weekly_features.csv

For each (cluster_id, time_band, week) row, builds features describing
the RECENT HISTORY of that series, to predict NEXT week's hotspot_score.
"""

import os
import pandas as pd
import numpy as np
from src.utils import load_config


def build_rolling_features(weekly: pd.DataFrame, min_weeks_for_model: int = 4) -> pd.DataFrame:
    weekly = weekly.sort_values(["cluster_id", "time_band", "week"]).copy()

    group = weekly.groupby(["cluster_id", "time_band"])

    # How many prior weeks of history exist before this row
    weekly["weeks_of_prior_history"] = group.cumcount()

    # Lag features: previous 1, 2, 3 weeks' violation_count and hotspot_score.
    for lag in [1, 2, 3]:
        weekly[f"lag{lag}_violation_count"] = group["violation_count"].shift(lag)
        weekly[f"lag{lag}_hotspot_score"] = group["hotspot_score"].shift(lag)

    # Rolling mean/std over the trailing 3 weeks
    shifted_vc = group["violation_count"].shift(1)
    shifted_hs = group["hotspot_score"].shift(1)

    keys = [weekly["cluster_id"], weekly["time_band"]]
    weekly["roll3_mean_violation_count"] = shifted_vc.groupby(keys).transform(
        lambda s: s.rolling(3, min_periods=1).mean()
    )
    weekly["roll3_std_violation_count"] = shifted_vc.groupby(keys).transform(
        lambda s: s.rolling(3, min_periods=1).std()
    )
    weekly["roll3_mean_hotspot_score"] = shifted_hs.groupby(keys).transform(
        lambda s: s.rolling(3, min_periods=1).mean()
    )

    # Trend direction
    weekly["trend_violation_count"] = weekly["lag1_violation_count"] - weekly["lag2_violation_count"]

    # Cumulative historical mean up to (not including) this week
    weekly["expanding_mean_violation_count"] = shifted_vc.groupby(keys).transform(
        lambda s: s.expanding().mean()
    )
    weekly["expanding_mean_hotspot_score"] = shifted_hs.groupby(keys).transform(
        lambda s: s.expanding().mean()
    )

    # Targets for next week
    weekly["target_next_week_violation_count"] = group["violation_count"].shift(-1)
    weekly["target_next_week_hotspot_score"] = group["hotspot_score"].shift(-1)

    # Tier assignment
    weekly["tier"] = np.where(
        weekly["weeks_of_prior_history"] >= min_weeks_for_model, "model", "fallback"
    )

    return weekly


def run_rolling_features(input_path: str, output_path: str, min_weeks_for_model: int = 4) -> pd.DataFrame:
    weekly = pd.read_csv(input_path)
    weekly["week"] = pd.to_datetime(weekly["week"])

    featured = build_rolling_features(weekly, min_weeks_for_model)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    featured.to_csv(output_path, index=False)

    n_rows_with_target = featured["target_next_week_hotspot_score"].notna().sum()
    n_model_tier = (featured["tier"] == "model").sum()
    n_fallback_tier = (featured["tier"] == "fallback").sum()

    print(f"Rolling feature construction complete.")
    print(f"  Total rows: {len(featured):,}")
    print(f"  Rows with a valid next-week target: {n_rows_with_target:,}")
    print(f"  Tier counts -> model: {n_model_tier:,} | fallback: {n_fallback_tier:,}")
    print(f"  Saved to: {output_path}")

    return featured


if __name__ == "__main__":
    config = load_config()
    input_path = config["forecasting"]["weekly_aggregation_path"]
    output_path = config["forecasting"]["weekly_features_path"]
    min_weeks = int(config["forecasting"]["min_weeks_for_model"])
    
    run_rolling_features(input_path, output_path, min_weeks)
