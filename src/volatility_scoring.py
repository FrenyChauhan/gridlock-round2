"""
src/volatility_scoring.py
==========================
Bengaluru Traffic Violation Prediction - Volatility Scoring

For every (cluster_id, time_band) series we compute a suite of volatility
metrics from the weekly_cluster_timeband.csv, classify each series into one
of four regimes, and assign a patrol_buffer_multiplier so that patrol
resources scale with both volume AND unpredictability.

Regime matrix:
   +--------------+-----------------+------------------+
   |              |  trend_slope>0  |  trend_slope<=0  |
   +--------------+-----------------+------------------+
   |  cv > 0.5   | volatile_growing | volatile_stable  |
   |  cv <= 0.5  | stable_growing   | stable_flat      |
   +--------------+-----------------+------------------+

Patrol buffer multipliers:
   volatile_growing : 1.30  (growing AND unpredictable -> max extra resources)
   volatile_stable  : 1.15  (unpredictable but not growing)
   stable_growing   : 1.10  (predictable but rising trend)
   stable_flat      : 1.00  (no buffer needed)

Output: data/processed/volatility_scores.csv
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from scipy.stats import linregress

# ------------------------------------------------------------------
# PATH SETUP
# ------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils import load_config, setup_logging


# ==================================================================
# CONSTANTS
# ==================================================================

CV_THRESHOLD = 0.5          # boundary between volatile / stable

PATROL_BUFFER = {
    "volatile_growing" : 1.30,
    "volatile_stable"  : 1.15,
    "stable_growing"   : 1.10,
    "stable_flat"      : 1.00,
}

OUTPUT_COLS = [
    "cluster_id", "time_band",
    "mean_violations", "std_violations", "cv",
    "max_spike", "zero_weeks_pct", "trend_slope",
    "volatility_class", "patrol_buffer_multiplier",
]


# ==================================================================
# METRIC COMPUTATION  (per series)
# ==================================================================

def compute_series_metrics(group: pd.DataFrame) -> pd.Series:
    """
    Receives a DataFrame for one (cluster_id, time_band) series,
    sorted by week. Returns a Series of volatility metrics.
    """
    counts = group["violation_count"].values.astype(float)
    n      = len(counts)

    mean_v = counts.mean()
    std_v  = counts.std(ddof=1) if n > 1 else 0.0

    # Coefficient of Variation (guard against zero mean)
    cv = (std_v / mean_v) if mean_v > 0 else 0.0

    # Max spike: ratio of single worst week to mean
    max_spike = (counts.max() / mean_v) if mean_v > 0 else 0.0

    # Intermittency: % of weeks with 0 violations
    zero_weeks_pct = (counts == 0).sum() / n * 100.0

    # Trend slope: ordinary least-squares over week index
    if n >= 3:
        x = np.arange(n, dtype=float)
        slope, *_ = linregress(x, counts)
    else:
        slope = 0.0

    return pd.Series({
        "mean_violations" : round(mean_v, 4),
        "std_violations"  : round(std_v,  4),
        "cv"              : round(cv,     4),
        "max_spike"       : round(max_spike, 4),
        "zero_weeks_pct"  : round(zero_weeks_pct, 2),
        "trend_slope"     : round(slope,  4),
    })


# ==================================================================
# CLASSIFICATION
# ==================================================================

def classify_series(cv: float, slope: float) -> str:
    if cv > CV_THRESHOLD:
        return "volatile_growing" if slope > 0 else "volatile_stable"
    else:
        return "stable_growing"   if slope > 0 else "stable_flat"


# ==================================================================
# SUMMARY PRINTER
# ==================================================================

def print_summary(scores: pd.DataFrame, log) -> None:
    sep = "=" * 58

    log("\n" + sep)
    log("VOLATILITY SCORING SUMMARY")
    log(sep)

    # Class distribution
    class_counts = scores["volatility_class"].value_counts()
    log("\nSeries count by volatility class:")
    for cls in ["volatile_growing", "volatile_stable", "stable_growing", "stable_flat"]:
        cnt = class_counts.get(cls, 0)
        pct = cnt / len(scores) * 100
        buf = PATROL_BUFFER[cls]
        log(f"  {cls:<20}  {cnt:>4} series  ({pct:5.1f}%)   buffer={buf}")

    # Global stats
    log(f"\nOverall cv distribution:")
    log(f"  median cv : {scores['cv'].median():.3f}")
    log(f"  mean cv   : {scores['cv'].mean():.3f}")
    log(f"  max cv    : {scores['cv'].max():.3f}")

    log(f"\nSeries with zero-weeks_pct > 50%: "
        f"{(scores['zero_weeks_pct'] > 50).sum()} (intermittent/sparse)")

    # Top 10 volatile_growing zones
    vg = scores[scores["volatility_class"] == "volatile_growing"].copy()
    vg_sorted = vg.sort_values(
        ["mean_violations", "cv"], ascending=[False, False]
    ).head(10)

    log("\nTop 10 volatile_growing zones (high volume + unpredictable + growing):")
    log(f"  {'cluster_id':>10}  {'time_band':<22}  "
        f"{'mean':>7}  {'cv':>6}  {'slope':>8}  {'max_spike':>9}")
    log("  " + "-" * 68)
    for _, row in vg_sorted.iterrows():
        log(f"  {int(row['cluster_id']):>10}  {row['time_band']:<22}  "
            f"{row['mean_violations']:>7.1f}  "
            f"{row['cv']:>6.3f}  "
            f"{row['trend_slope']:>8.3f}  "
            f"{row['max_spike']:>9.2f}x")

    log("\n" + sep)


# ==================================================================
# MAIN FUNCTION
# ==================================================================

def run_volatility_scoring(
    weekly_path  : str,
    output_path  : str,
    logger       = None,
) -> pd.DataFrame:
    """
    Compute volatility metrics and patrol buffer multipliers for every
    (cluster_id, time_band) series.

    Parameters
    ----------
    weekly_path  : path to weekly_cluster_timeband.csv
    output_path  : where to save volatility_scores.csv
    logger       : optional Python logger (falls back to print)

    Returns
    -------
    pd.DataFrame : the volatility scores table
    """

    def log(msg, level="info"):
        if logger:
            getattr(logger, level, logger.info)(msg)
        else:
            print(msg)

    # ── Load ──────────────────────────────────────────────────────
    log(f"\nLoading weekly data from: {weekly_path}")
    if not os.path.exists(weekly_path):
        raise FileNotFoundError(
            f"Weekly aggregation file not found: {weekly_path}\n"
            "Run src/weekly_aggregation.py first."
        )

    df = pd.read_csv(weekly_path)
    df["week"] = pd.to_datetime(df["week"])
    df = df.sort_values(["cluster_id", "time_band", "week"]).reset_index(drop=True)

    n_series = df.groupby(["cluster_id", "time_band"]).ngroups
    log(f"  Rows: {len(df):,}  |  Unique series: {n_series:,}  |  "
        f"Weeks: {df['week'].nunique()}")

    # ── Per-series metrics ─────────────────────────────────────────
    log("\nComputing per-series volatility metrics...")
    metrics = (
        df.groupby(["cluster_id", "time_band"], sort=True)
        .apply(compute_series_metrics, include_groups=False)
        .reset_index()
    )
    log(f"  Computed metrics for {len(metrics):,} series.")

    # ── Classification ─────────────────────────────────────────────
    log("Classifying series into volatility regimes...")
    metrics["volatility_class"] = metrics.apply(
        lambda r: classify_series(r["cv"], r["trend_slope"]), axis=1
    )

    # ── Patrol buffer multiplier ───────────────────────────────────
    metrics["patrol_buffer_multiplier"] = metrics["volatility_class"].map(PATROL_BUFFER)

    # ── Finalise & export ──────────────────────────────────────────
    scores = metrics[OUTPUT_COLS].copy()
    scores = scores.sort_values(
        ["volatility_class", "mean_violations"], ascending=[True, False]
    ).reset_index(drop=True)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    scores.to_csv(output_path, index=False)
    log(f"\nVolatility scores saved to: {output_path}")
    log(f"  Shape: {scores.shape}")

    # ── Summary report ─────────────────────────────────────────────
    print_summary(scores, log)

    return scores


# ==================================================================
# CLI ENTRY POINT
# ==================================================================

if __name__ == "__main__":
    logger = setup_logging("pipeline.log")
    config = load_config(os.path.join(PROJECT_ROOT, "configs", "config.yaml"))

    weekly_path = os.path.join(
        PROJECT_ROOT, config["forecasting"]["weekly_aggregation_path"]
    )
    output_path = os.path.join(
        PROJECT_ROOT, "data/processed/volatility_scores.csv"
    )

    run_volatility_scoring(
        weekly_path = weekly_path,
        output_path = output_path,
        logger      = logger,
    )
