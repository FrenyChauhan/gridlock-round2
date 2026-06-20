"""
Stage 1 — Weekly Aggregation
=============================
Input:  clustered_violations.csv (per-violation rows, full dataset)
Output: weekly_cluster_timeband.csv
        One row per (cluster_id, time_band, week), with:
          - violation_count (the raw weekly volume)
          - mean_combined_severity_norm, mean_time_demand_multiplier,
            mean_junction_multiplier, mean_vehicle_blockage_norm
          - hotspot_score_raw / hotspot_score (recomputed using the
            same formula as the existing historical hotspot scoring step,
            but at WEEKLY grain instead of monthly)
"""

import os
import pandas as pd
import numpy as np
from src.utils import load_config, setup_logging


def load_and_prepare(path: str, usable_bands: list) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])

    # Exclude noise points (cluster_id == -1) -- consistent with existing
    # pipeline, which only scores actual clusters, not unclustered noise.
    before = len(df)
    df = df[df["cluster_id"] != -1].copy()
    print(f"Dropped {before - len(df):,} noise rows (cluster_id == -1)")

    # Exclude evening/night bands -- consistent with hotspot_scoring.py
    before = len(df)
    df = df[df["time_band"].isin(usable_bands)].copy()
    print(f"Dropped {before - len(df):,} evening/night rows")

    # ISO week label, anchored Monday, for stable weekly bucketing
    df["week"] = df["date"].dt.to_period("W-SUN").apply(lambda p: p.start_time)

    return df


def aggregate_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per (cluster_id, time_band, week).
    """
    grouped = (
        df.groupby(["cluster_id", "time_band", "week"])
        .agg(
            violation_count=("id", "count"),
            mean_severity_norm=("combined_severity_norm", "mean"),
            mean_time_demand=("time_demand_multiplier", "mean"),
            mean_junction_mult=("junction_multiplier", "mean"),
            mean_vehicle_blockage=("vehicle_blockage_norm", "mean"),
            pct_weekend=("is_weekend", "mean"),
            pct_at_junction=("is_junction", "mean"),
        )
        .reset_index()
    )
    return grouped


def compute_weekly_hotspot_score(weekly: pd.DataFrame) -> pd.DataFrame:
    """
    Same multiplicative formula as the existing (monthly) hotspot scoring
    step, applied at weekly grain:

        raw = violation_count * mean_severity_norm
                               * mean_time_demand
                               * mean_junction_mult

    Then MinMax-normalised GLOBALLY across all weekly rows.
    """
    weekly = weekly.copy()
    weekly["hotspot_score_raw"] = (
        weekly["violation_count"]
        * weekly["mean_severity_norm"]
        * weekly["mean_time_demand"]
        * weekly["mean_junction_mult"]
    )

    lo, hi = weekly["hotspot_score_raw"].min(), weekly["hotspot_score_raw"].max()
    if hi > lo:
        weekly["hotspot_score"] = (weekly["hotspot_score_raw"] - lo) / (hi - lo)
    else:
        weekly["hotspot_score"] = 0.0

    return weekly


def run_weekly_aggregation(input_path: str, output_path: str, usable_bands: list) -> pd.DataFrame:
    df = load_and_prepare(input_path, usable_bands)
    weekly = aggregate_weekly(df)
    weekly = compute_weekly_hotspot_score(weekly)

    weekly = weekly.sort_values(["cluster_id", "time_band", "week"]).reset_index(drop=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    weekly.to_csv(output_path, index=False)

    print(f"\nWeekly aggregation complete.")
    print(f"  Rows: {len(weekly):,}")
    print(f"  Unique (cluster_id, time_band) pairs: {weekly.groupby(['cluster_id','time_band']).ngroups:,}")
    print(f"  Week range: {weekly['week'].min()} to {weekly['week'].max()}")
    print(f"  Saved to: {output_path}")

    return weekly


if __name__ == "__main__":
    config = load_config()
    input_path = config["data"]["clustered_violation_path"]
    output_path = config["forecasting"]["weekly_aggregation_path"]
    usable_bands = config["hotspot_scoring"]["usable_bands"]
    
    run_weekly_aggregation(input_path, output_path, usable_bands)
