"""
Bengaluru Parking Violations — Hotspot Scoring (v1)
===================================================
Input : data/processed/clustered_violations.csv
        data/processed/cluster_registry.csv
Output:
  - data/processed/hotspot_scores.csv       (one row per cluster × time slice)
  - outputs/plots/hotspot_score_dist.png    (score distribution plot)
  - outputs/plots/top_hotspots_bar.png      (top 20 hotspot zones)
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

from sklearn.preprocessing import MinMaxScaler
from src.utils import load_config, setup_logging

def run_hotspot_scoring(
    clustered_path: str,
    registry_path: str,
    hotspot_path: str,
    dist_plot_path: str,
    bar_plot_path: str,
    min_cluster_size: int,
    min_slice_count: int,
    usable_bands: list,
    logger=None
):
    """
    Computes density-based temporal risk hotspot scores for clustered parking violations.
    """
    def log(msg, level="info"):
        if logger:
            if level == "info":
                logger.info(msg)
            elif level == "debug":
                logger.debug(msg)
            elif level == "warning":
                logger.warning(msg)
            elif level == "error":
                logger.error(msg)
        else:
            print(msg)

    log("Loading clustered violations...")
    df = pd.read_csv(clustered_path, low_memory=False)
    log(f"  Shape: {df.shape}")

    log("Loading cluster registry...")
    registry = pd.read_csv(registry_path)
    log(f"  Registry: {len(registry)} clusters")

    # ─────────────────────────────────────────────
    # FILTER TINY CLUSTERS & NOISE
    # ─────────────────────────────────────────────
    log(f"\nFiltering clusters < {min_cluster_size} violations and noise points...")
    before_clusters = df["cluster_id"].nunique() - (1 if -1 in df["cluster_id"].values else 0)

    valid_clusters = registry[
        registry["total_violations"] >= min_cluster_size
    ]["cluster_id"].tolist()

    df = df[df["cluster_id"].isin(valid_clusters)].copy()
    registry = registry[registry["cluster_id"].isin(valid_clusters)].reset_index(drop=True)

    after_clusters = len(valid_clusters)
    log(f"  Clusters before filter : {before_clusters}")
    log(f"  Clusters after filter  : {after_clusters}")
    log(f"  Rows retained          : {len(df):,}")

    # ─────────────────────────────────────────────
    # FILTER TO USABLE TIME BANDS
    # ─────────────────────────────────────────────
    log(f"\nFiltering to usable time bands: {usable_bands}")
    before = len(df)
    df = df[df["time_band"].isin(usable_bands)].copy()
    log(f"  Rows retained: {len(df):,} (removed {before - len(df):,} evening/night rows)")

    # ─────────────────────────────────────────────
    # BUILD FREQUENCY TABLE
    # ─────────────────────────────────────────────
    log("\nBuilding frequency table...")
    freq = df.groupby(
        ["cluster_id", "time_band", "day_type", "month"],
        as_index=False
    ).agg(
        violation_count          = ("id",                      "count"),
        mean_severity            = ("combined_severity_norm",  "mean"),
        mean_time_demand         = ("time_demand_multiplier",  "mean"),
        mean_junction_mult       = ("junction_multiplier",     "mean"),
        mean_junction_proxy      = ("junction_proxy",          "mean"),
        mean_combined_severity   = ("combined_severity_norm",  "mean"),
        mean_vehicle_blockage    = ("vehicle_blockage_norm",   "mean"),
        pct_at_junction          = ("is_junction",             "mean"),
        pct_peak_junction        = ("is_peak_junction",        "mean"),
        pct_heavy_at_junction    = ("heavy_at_junction",       "mean"),
    )

    log(f"  Frequency table shape: {freq.shape}")
    log(f"  Unique clusters      : {freq['cluster_id'].nunique()}")
    log(f"  Unique time bands    : {freq['time_band'].unique()}")

    # ─────────────────────────────────────────────
    # JOIN CLUSTER REGISTRY ATTRIBUTES
    # ─────────────────────────────────────────────
    registry_cols = [
        "cluster_id", "centroid_lat", "centroid_lon",
        "dominant_police_station", "dominant_junction",
        "radius_m", "total_violations"
    ]
    freq = freq.merge(registry[registry_cols], on="cluster_id", how="left")
    log(f"\nAfter registry join: {freq.shape}")

    # ─────────────────────────────────────────────
    # FILTER SPARSE SLICES
    # ─────────────────────────────────────────────
    log(f"\nFiltering slices with < {min_slice_count} violations...")
    before_slices = len(freq)
    freq = freq[freq["violation_count"] >= min_slice_count].copy()
    log(f"  Slices before: {before_slices:,}")
    log(f"  Slices after : {len(freq):,}")
    log(f"  Slices dropped: {before_slices - len(freq):,}")

    # ─────────────────────────────────────────────
    # HOTSPOT SCORING FORMULA
    # ─────────────────────────────────────────────
    log("\nComputing hotspot scores...")
    freq["hotspot_score_raw"] = (
        freq["violation_count"]
        * freq["mean_combined_severity"]
        * freq["mean_time_demand"]
        * freq["mean_junction_mult"]
    )

    # Normalise to 0-1 across all slices
    scaler = MinMaxScaler()
    freq["hotspot_score"] = scaler.fit_transform(
        freq[["hotspot_score_raw"]]
    ).round(6)

    log(f"  Raw score range  : {freq['hotspot_score_raw'].min():.4f} - {freq['hotspot_score_raw'].max():.4f}")
    log(f"  Normalised range : {freq['hotspot_score'].min():.4f} - {freq['hotspot_score'].max():.4f}")
    log(f"  Mean score       : {freq['hotspot_score'].mean():.4f}")
    log(f"  Median score     : {freq['hotspot_score'].median():.4f}")

    # ─────────────────────────────────────────────
    # SCORE DISTRIBUTION ANALYSIS
    # ─────────────────────────────────────────────
    log("\nScore distribution (percentiles):")
    percentiles = [10, 25, 50, 70, 80, 90, 95, 99]
    for p in percentiles:
         log(f"  {p:>3}th percentile : {np.percentile(freq['hotspot_score'], p):.4f}")

    # ─────────────────────────────────────────────
    # TOP HOTSPOTS PER TIME BAND
    # ─────────────────────────────────────────────
    log("\nTop 5 hotspot slices per time band:")
    for band in usable_bands:
        band_df = freq[freq["time_band"] == band].nlargest(5, "hotspot_score")
        log(f"\n  [{band.upper()}]")
        log(band_df[[
            "cluster_id", "dominant_police_station", "dominant_junction",
            "violation_count", "hotspot_score"
        ]].to_string(index=False))

    # ─────────────────────────────────────────────
    # VISUALISATION — Score Distribution
    # ─────────────────────────────────────────────
    os.makedirs(os.path.dirname(dist_plot_path), exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Left — overall score histogram
    axes[0].hist(freq["hotspot_score"], bins=40, color="#457b9d", edgecolor="white", linewidth=0.5)
    axes[0].axvline(freq["hotspot_score"].quantile(0.80), color="#e63946", linestyle="--", linewidth=2,
                    label="80th pct (Red threshold)")
    axes[0].axvline(freq["hotspot_score"].quantile(0.50), color="#f4a261", linestyle="--", linewidth=2,
                    label="50th pct (Green threshold)")
    axes[0].set_xlabel("Hotspot Score (0–1)", fontsize=11)
    axes[0].set_ylabel("Number of Slices", fontsize=11)
    axes[0].set_title("Hotspot Score Distribution", fontsize=13)
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)

    # Right — score by time band (box plot)
    band_data = [
        freq[freq["time_band"] == b]["hotspot_score"].values
        for b in usable_bands
    ]
    bp = axes[1].boxplot(band_data, labels=usable_bands, patch_artist=True)
    colours = ["#264653", "#2a9d8f", "#e9c46a"]
    for patch, colour in zip(bp["boxes"], colours):
        patch.set_facecolor(colour)
        patch.set_alpha(0.7)
    axes[1].set_xlabel("Time Band", fontsize=11)
    axes[1].set_ylabel("Hotspot Score (0–1)", fontsize=11)
    axes[1].set_title("Score Distribution by Time Band", fontsize=13)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(dist_plot_path, dpi=150)
    plt.close()
    log(f"\nScore distribution plot saved: {dist_plot_path}")

    # ─────────────────────────────────────────────
    # VISUALISATION — Top 20 Hotspot Zones
    # ─────────────────────────────────────────────
    top20 = freq.nlargest(20, "hotspot_score").copy()
    top20["label"] = (
        top20["dominant_police_station"] + "\n" +
        top20["time_band"] + " / " + top20["day_type"]
    )

    colours_bar = ["#e63946" if s >= freq["hotspot_score"].quantile(0.80)
                   else "#f4a261" if s >= freq["hotspot_score"].quantile(0.50)
                   else "#2a9d8f"
                   for s in top20["hotspot_score"]]

    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.barh(top20["label"], top20["hotspot_score"], color=colours_bar, edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Hotspot Score (0–1)", fontsize=11)
    ax.set_title("Top 20 Hotspot Zones — by Score", fontsize=13)
    ax.invert_yaxis()
    ax.axvline(freq["hotspot_score"].quantile(0.80), color="#e63946", linestyle="--", linewidth=1.5, label="Red threshold")
    ax.axvline(freq["hotspot_score"].quantile(0.50), color="#f4a261", linestyle="--", linewidth=1.5, label="Green threshold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis="x")
    plt.tight_layout()
    plt.savefig(bar_plot_path, dpi=150, bbox_inches="tight")
    plt.close()
    log(f"Top hotspots bar chart saved: {bar_plot_path}")

    # ─────────────────────────────────────────────
    # EXPORT
    # ─────────────────────────────────────────────
    OUTPUT_COLS = [
        "cluster_id", "dominant_police_station", "dominant_junction",
        "centroid_lat", "centroid_lon", "radius_m",
        "time_band", "day_type", "month",
        "violation_count", "total_violations",
        "mean_severity", "mean_time_demand", "mean_junction_mult",
        "mean_junction_proxy", "mean_vehicle_blockage",
        "pct_at_junction", "pct_peak_junction", "pct_heavy_at_junction",
        "hotspot_score_raw", "hotspot_score",
    ]
    freq_out = freq[OUTPUT_COLS].sort_values("hotspot_score", ascending=False)
    freq_out.to_csv(hotspot_path, index=False)
    log(f"\nHotspot scores saved to: {hotspot_path}")

    # ─────────────────────────────────────────────
    # FINAL SUMMARY
    # ─────────────────────────────────────────────
    log("\n" + "="*55)
    log("HOTSPOT SCORING SUMMARY")
    log("="*55)
    log(f"  Total slices scored    : {len(freq_out):,}")
    log(f"  Unique clusters        : {freq_out['cluster_id'].nunique()}")
    log(f"  Unique police stations : {freq_out['dominant_police_station'].nunique()}")
    log(f"  Score range            : {freq_out['hotspot_score'].min():.4f} - {freq_out['hotspot_score'].max():.4f}")
    log(f"  80th pct (Red line)    : {freq_out['hotspot_score'].quantile(0.80):.4f}")
    log(f"  50th pct (Green line)  : {freq_out['hotspot_score'].quantile(0.50):.4f}")
    log(f"\n  Time band breakdown:")
    log(freq_out.groupby("time_band")["hotspot_score"].agg(["count","mean","max"]).round(4).to_string())
    log(f"\n  Top 5 slices:")
    log(freq_out[[
        "cluster_id","dominant_police_station","time_band",
        "day_type","month","violation_count","hotspot_score"
    ]].head(5).to_string(index=False))

    return freq_out

if __name__ == "__main__":
    logger = setup_logging()
    config = load_config()

    clustered_path = config["data"]["clustered_violation_path"]
    registry_path = config["data"]["cluster_registry_path"]
    hotspot_path = config["data"]["hotspot_scores_path"]
    dist_plot_path = config["data"]["hotspot_dist_plot_path"]
    bar_plot_path = config["data"]["top_hotspots_plot_path"]

    min_cluster_size = int(config["hotspot_scoring"]["min_cluster_size"])
    min_slice_count = int(config["hotspot_scoring"]["min_slice_count"])
    usable_bands = list(config["hotspot_scoring"]["usable_bands"])

    run_hotspot_scoring(
        clustered_path,
        registry_path,
        hotspot_path,
        dist_plot_path,
        bar_plot_path,
        min_cluster_size,
        min_slice_count,
        usable_bands,
        logger
    )
