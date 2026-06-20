"""
Final Priority Scoring + Tiering
===================================
Input:  - forecast output (predicted_violation_count per cluster_id x
          time_band x week, from generate_forecast.py)
        - cii_scores.csv (from cii_scoring.py)
Output: final_priority_table.csv -- one row per cluster_id x time_band,
        ready to hand off to the LLM patrol-allocation step / heatmap.
"""

import os
import pandas as pd
import numpy as np
from src.utils import load_config


def compute_hotspot_score(forecast_df: pd.DataFrame, global_mean_severity: float, k: float = 30) -> pd.DataFrame:
    """
    SHRINKAGE FIX:
    mean_severity_norm is the average of a near-binary per-record value
    (0 unless a record logs multiple violation types together, which is
    rare). With few violations, this average is noise. Shrink each
    cluster's severity toward the GLOBAL mean severity, weighted by how
    much data that cluster actually has:

        adjusted = (n*own_mean + k*global_mean) / (n + k)
    """
    df = forecast_df.copy()

    n = df["historical_violation_count"] if "historical_violation_count" in df.columns else df["predicted_violation_count"]
    df["adjusted_severity_norm"] = (
        n * df["mean_severity_norm"] + k * global_mean_severity
    ) / (n + k)

    df["hotspot_score_raw"] = df["predicted_violation_count"] * df["adjusted_severity_norm"]

    lo, hi = df["hotspot_score_raw"].min(), df["hotspot_score_raw"].max()
    if hi > lo:
        df["hotspot_score"] = (df["hotspot_score_raw"] - lo) / (hi - lo)
    else:
        df["hotspot_score"] = 0.0
    return df


def assign_tiers(df: pd.DataFrame, score_col: str = "final_priority_score") -> pd.DataFrame:
    df = df.copy()
    red_threshold = df[score_col].quantile(0.80)
    amber_threshold = df[score_col].quantile(0.50)

    def tier(score):
        if score >= red_threshold:
            return "Red"
        elif score >= amber_threshold:
            return "Amber"
        else:
            return "Green"

    df["tier"] = df[score_col].apply(tier)
    return df, red_threshold, amber_threshold


def build_final_table(forecast_path: str, cii_path: str, output_path: str, k: float = 30) -> pd.DataFrame:
    forecast = pd.read_csv(forecast_path)
    cii = pd.read_csv(cii_path)

    # Global prior for severity shrinkage: the overall mean severity_norm
    # across ALL clusters/time_bands, weighted by each cluster's own
    # historical volume.
    global_mean_severity = (
        forecast["historical_violation_count"] * forecast["mean_severity_norm"]
    ).sum() / forecast["historical_violation_count"].sum()
    print(f"Global mean severity (shrinkage prior): {global_mean_severity:.4f}, k={k}")

    forecast = compute_hotspot_score(forecast, global_mean_severity, k=k)

    merged = forecast.merge(
        cii[["cluster_id", "time_band", "cii_score", "dominant_police_station", "dominant_junction"]],
        on=["cluster_id", "time_band"],
        how="left",
    )

    missing_cii = merged["cii_score"].isna().sum()
    if missing_cii:
        print(f"WARNING: {missing_cii} rows have no matching CII score (cluster_id/time_band "
              f"combo not in cii_scores.csv) -- check these aren't silently dropped downstream.")

    merged["final_priority_score"] = merged["hotspot_score"] * merged["cii_score"]

    merged, red_thresh, amber_thresh = assign_tiers(merged)

    merged = merged.sort_values("final_priority_score", ascending=False).reset_index(drop=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    merged.to_csv(output_path, index=False)

    print(f"\nFinal priority table built.")
    print(f"  Rows: {len(merged):,}")
    print(f"  Red threshold (80th pct): {red_thresh:.4f}")
    print(f"  Amber threshold (50th pct): {amber_thresh:.4f}")
    print(f"  Tier counts:\n{merged['tier'].value_counts()}")
    print(f"\n  Top 10 priority zones:")
    cols = ["cluster_id", "time_band", "dominant_police_station", "predicted_violation_count",
            "hotspot_score", "cii_score", "final_priority_score", "tier"]
    print(merged[cols].head(10).to_string(index=False))
    print(f"\n  Saved to: {output_path}")

    return merged


if __name__ == "__main__":
    config = load_config()
    forecast_path = config["forecasting"]["weekly_forecast_path"]
    cii_path = config["forecasting"]["cii_scores_path"]
    output_path = config["forecasting"]["final_priority_table_path"]
    k = float(config["forecasting"]["shrinkage_k"])
    
    build_final_table(forecast_path, cii_path, output_path, k)
