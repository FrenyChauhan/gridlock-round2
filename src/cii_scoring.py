"""
CII Scoring — Congestion Impact Index
========================================
Input:  clustered_violations.csv (per-violation rows)
Output: cii_scores.csv  (one row per cluster_id x time_band)
"""

import os
import pandas as pd
from src.utils import load_config

# Weights -- must sum to 1.0
JUNCTION_WEIGHT = 0.4
VEHICLE_WEIGHT = 0.3
TIME_WEIGHT = 0.3


def compute_cii(input_path: str, output_path: str, usable_bands: list) -> pd.DataFrame:
    df = pd.read_csv(input_path)

    before = len(df)
    df = df[df["cluster_id"] != -1].copy()
    print(f"Dropped {before - len(df):,} noise rows (cluster_id == -1)")

    before = len(df)
    df = df[df["time_band"].isin(usable_bands)].copy()
    print(f"Dropped {before - len(df):,} evening/night rows")

    grouped = (
        df.groupby(["cluster_id", "time_band"])
        .agg(
            mean_junction_proxy=("junction_proxy", "mean"),
            mean_vehicle_blockage=("vehicle_blockage_norm", "mean"),
            mean_time_demand=("time_demand_multiplier", "mean"),
            violation_count=("id", "count"),
            dominant_police_station=("police_station", lambda s: s.mode().iloc[0] if len(s.mode()) else "Unknown"),
            dominant_junction=("junction_name", lambda s: s.mode().iloc[0] if len(s.mode()) else "Unknown"),
        )
        .reset_index()
    )

    grouped["cii_score"] = (
        grouped["mean_junction_proxy"] * JUNCTION_WEIGHT
        + grouped["mean_vehicle_blockage"] * VEHICLE_WEIGHT
        + grouped["mean_time_demand"] * TIME_WEIGHT
    )

    assert grouped["cii_score"].between(0, 1).all(), "CII out of [0,1] -- check input ranges"

    grouped = grouped.sort_values(["cluster_id", "time_band"]).reset_index(drop=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    grouped.to_csv(output_path, index=False)

    print(f"\nCII scoring complete.")
    print(f"  Rows (cluster_id x time_band): {len(grouped):,}")
    print(f"  Unique clusters: {grouped['cluster_id'].nunique():,}")
    print(f"  CII range: {grouped['cii_score'].min():.4f} - {grouped['cii_score'].max():.4f}")
    print(f"  CII mean: {grouped['cii_score'].mean():.4f}")
    print(f"  Saved to: {output_path}")

    return grouped


if __name__ == "__main__":
    config = load_config()
    input_path = config["data"]["clustered_violation_path"]
    output_path = config["forecasting"]["cii_scores_path"]
    usable_bands = config["hotspot_scoring"]["usable_bands"]
    
    compute_cii(input_path, output_path, usable_bands)
