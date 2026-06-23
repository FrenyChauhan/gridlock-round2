"""
run_full_pipeline.py
=====================
Bengaluru Traffic Violation Prediction - GRIDLOCK 2.0 Full Pipeline

Runs all 10 stages in order, validates outputs after each step,
and prints the final mission-control summary banner.

Usage (from project root with venv active):
    gridlock_env\\Scripts\\python.exe run_full_pipeline.py
"""

import os
import sys
import time
import json
import traceback

import pandas as pd

# ------------------------------------------------------------------
# Ensure project root is on sys.path so src.* imports resolve
# ------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Force UTF-8 stdout to avoid cp1252 codec errors on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ------------------------------------------------------------------
# RAW DATA PATH  (update if file is renamed / moved)
# ------------------------------------------------------------------
RAW_DATA_PATH = r"D:\Flipkart-r2\Data\jan to may police violation_anonymized791b166 (1).csv"

# ------------------------------------------------------------------
# PATH HELPERS
# ------------------------------------------------------------------
from src.utils import load_config, setup_logging

CONFIG_PATH = os.path.join(PROJECT_ROOT, "configs", "config.yaml")
config      = load_config(CONFIG_PATH)

def rp(rel: str) -> str:
    return os.path.join(PROJECT_ROOT, rel)

# All processed file paths
CLEANED_PATH      = rp(config["data"]["cleaned_violation_path"])
FEATURED_PATH     = rp(config["data"]["featured_violation_path"])
CLUSTERED_PATH    = rp(config["data"]["clustered_violation_path"])
REGISTRY_PATH     = rp(config["data"]["cluster_registry_path"])
WEEKLY_PATH       = rp(config["forecasting"]["weekly_aggregation_path"])
CII_PATH          = rp(config["forecasting"]["cii_scores_path"])
FORECAST_PATH     = rp("data/processed/global_forecast.csv")
VOLATILITY_PATH   = rp("data/processed/volatility_scores.csv")
PRIORITY_PATH     = rp(config["forecasting"]["final_priority_table_path"])
TEAMS_PATH        = rp("data/processed/patrol_teams.csv")
ASSIGNMENTS_PATH  = rp("data/processed/team_assignments.csv")
OUTCOMES_PATH     = rp("data/processed/enforcement_outcomes.csv")
HEATMAP_PATH      = rp(config["forecasting"]["heatmap_data_path"])
KDIST_PLOT        = rp(config["data"]["kdist_plot_path"])
HIST_PLOT         = rp(config["data"]["hist_plot_path"])
CLUSTER_MAP       = rp(config["data"]["cluster_map_path"])
FEATURE_IMP_PLOT  = rp("outputs/plots/feature_importance.png")

USABLE_BANDS      = config["hotspot_scoring"]["usable_bands"]
EPS               = float(config["clustering"]["eps"])
MIN_SAMPLES       = int(config["clustering"]["min_samples"])
MIN_CLUSTER_SIZE  = int(config["clustering"]["min_cluster_size"])
SHRINKAGE_K       = float(config["forecasting"]["shrinkage_k"])


# ==================================================================
# OUTPUT ACCUMULATOR  (collected across all steps for final banner)
# ==================================================================
results = {
    "zones_total"      : 0,
    "red"              : 0,
    "amber"            : 0,
    "green"            : 0,
    "teams_deployed"   : 0,
    "volatile_growing" : 0,
    "lgbm_mae"         : None,
    "baseline_mae"     : None,
    "conf_high"        : 0,
    "conf_medium"      : 0,
    "conf_low"         : 0,
    "mock_outcomes"    : 0,
    "fp_rate_pct"      : 0.0,
    "heatmap_zones"    : 0,
}


# ==================================================================
# HELPERS
# ==================================================================

def banner(text: str):
    width = 65
    print("\n" + "=" * width)
    print("  " + text)
    print("=" * width)


def ok(msg: str):
    print("  [OK]  " + msg)


def warn(msg: str):
    print("  [WARN]" + msg)


def fail(step: str, exc: Exception):
    print(f"\n  [FAIL] Step failed: {step}")
    print(f"         {type(exc).__name__}: {exc}")
    traceback.print_exc()
    print("\n  Pipeline aborted. Fix the error above and re-run.")
    sys.exit(1)


def validate_file(path: str, label: str, min_rows: int = 1) -> int:
    """Assert file exists and has >= min_rows. Returns row count."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"{label} not found: {path}")
    df = pd.read_csv(path, low_memory=False)
    n  = len(df)
    if n < min_rows:
        raise ValueError(f"{label} has only {n} rows (expected >= {min_rows})")
    ok(f"{label}: {n:,} rows")
    return n


def ensure_dirs(*paths: str):
    for p in paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)


# ==================================================================
# PRE-FLIGHT
# ==================================================================

banner("GRIDLOCK 2.0 — Full Pipeline")
print(f"  Project root : {PROJECT_ROOT}")
print(f"  Config       : {CONFIG_PATH}")

if not os.path.exists(RAW_DATA_PATH):
    print(f"\n  [FAIL] Raw data not found: {RAW_DATA_PATH}")
    sys.exit(1)

raw_mb = os.path.getsize(RAW_DATA_PATH) / (1024 ** 2)
print(f"  Raw data     : {RAW_DATA_PATH}  ({raw_mb:.1f} MB)")

ensure_dirs(
    CLEANED_PATH, FEATURED_PATH, CLUSTERED_PATH, REGISTRY_PATH,
    WEEKLY_PATH, CII_PATH, FORECAST_PATH, VOLATILITY_PATH,
    PRIORITY_PATH, TEAMS_PATH, ASSIGNMENTS_PATH, OUTCOMES_PATH,
    HEATMAP_PATH, KDIST_PLOT, HIST_PLOT, CLUSTER_MAP, FEATURE_IMP_PLOT,
)

log_path = os.path.join(PROJECT_ROOT, "pipeline_full.log")
logger   = setup_logging(log_path)
pipeline_start = time.time()


# ==================================================================
# STEP 1 — DATA CLEANING
# ==================================================================

banner("STEP 1 / 10 — Data Cleaning")
t0 = time.time()
try:
    from src.data_cleaning import clean_data
    raw_count = sum(1 for _ in open(RAW_DATA_PATH, encoding="utf-8")) - 1
    df_clean  = clean_data(RAW_DATA_PATH, CLEANED_PATH, logger)
    n_clean   = validate_file(CLEANED_PATH, "cleaned_violations.csv", min_rows=1000)
    dropped   = raw_count - n_clean
    ok(f"Raw={raw_count:,}  Kept={n_clean:,}  Dropped={dropped:,} ({dropped/raw_count*100:.1f}%)")
    ok(f"Step 1 done in {time.time()-t0:.1f}s")
except Exception as e:
    fail("Data Cleaning", e)


# ==================================================================
# STEP 2 — FEATURE ENGINEERING
# ==================================================================

banner("STEP 2 / 10 — Feature Engineering")
t0 = time.time()
try:
    from src.feature_engineering import run_feature_engineering
    df_feat = run_feature_engineering(CLEANED_PATH, FEATURED_PATH, logger)
    n_feat  = validate_file(FEATURED_PATH, "featured_violations.csv", min_rows=1000)
    ok(f"Columns: {df_feat.shape[1]}  |  Rows: {n_feat:,}")
    ok(f"Step 2 done in {time.time()-t0:.1f}s")
except Exception as e:
    fail("Feature Engineering", e)


# ==================================================================
# STEP 3 — DBSCAN CLUSTERING
# ==================================================================

banner("STEP 3 / 10 — DBSCAN Spatial Clustering")
t0 = time.time()
try:
    from src.dbscan_clustering import run_dbscan_clustering
    df_clust, registry = run_dbscan_clustering(
        input_path       = FEATURED_PATH,
        clustered_path   = CLUSTERED_PATH,
        registry_path    = REGISTRY_PATH,
        kdist_plot_path  = KDIST_PLOT,
        hist_plot_path   = HIST_PLOT,
        cluster_map_path = CLUSTER_MAP,
        eps              = EPS,
        min_samples      = MIN_SAMPLES,
        min_cluster_size = MIN_CLUSTER_SIZE,
        logger           = logger,
    )
    n_clusters   = registry["cluster_id"].nunique()
    n_clustered  = (df_clust["cluster_id"] != -1).sum()
    pct_in       = n_clustered / len(df_clust) * 100
    validate_file(CLUSTERED_PATH, "clustered_violations.csv", min_rows=1000)
    validate_file(REGISTRY_PATH,  "cluster_registry.csv",     min_rows=10)
    ok(f"Clusters={n_clusters}  |  Clustered={n_clustered:,} ({pct_in:.1f}%)")
    ok(f"Step 3 done in {time.time()-t0:.1f}s")
except Exception as e:
    fail("DBSCAN Clustering", e)


# ==================================================================
# STEP 4 — WEEKLY AGGREGATION
# ==================================================================

banner("STEP 4 / 10 — Weekly Aggregation")
t0 = time.time()
try:
    from src.weekly_aggregation import run_weekly_aggregation
    df_weekly = run_weekly_aggregation(CLUSTERED_PATH, WEEKLY_PATH, USABLE_BANDS)
    n_weekly  = validate_file(WEEKLY_PATH, "weekly_cluster_timeband.csv", min_rows=100)
    ok(f"Series: {df_weekly.groupby(['cluster_id','time_band']).ngroups}  |  "
       f"Weeks: {df_weekly['week'].nunique()}  |  Rows: {n_weekly:,}")
    ok(f"Step 4 done in {time.time()-t0:.1f}s")
except Exception as e:
    fail("Weekly Aggregation", e)


# ==================================================================
# STEP 5 — CII SCORING
# ==================================================================

banner("STEP 5 / 10 — CII Scoring")
t0 = time.time()
try:
    from src.cii_scoring import compute_cii
    df_cii = compute_cii(CLUSTERED_PATH, CII_PATH, USABLE_BANDS)
    n_cii  = validate_file(CII_PATH, "cii_scores.csv", min_rows=100)
    ok(f"CII range: {df_cii['cii_score'].min():.4f} - {df_cii['cii_score'].max():.4f}  |  "
       f"Mean: {df_cii['cii_score'].mean():.4f}")
    ok(f"Step 5 done in {time.time()-t0:.1f}s")
except Exception as e:
    fail("CII Scoring", e)


# ==================================================================
# STEP 6 — GLOBAL FORECAST MODEL
# ==================================================================

banner("STEP 6 / 10 — Global LightGBM Forecast Model")
t0 = time.time()
try:
    from src.global_forecast_model import run_global_forecast_model
    forecast_df, model, eval_results = run_global_forecast_model(
        weekly_path   = WEEKLY_PATH,
        registry_path = REGISTRY_PATH,
        forecast_path = FORECAST_PATH,
        plot_path     = FEATURE_IMP_PLOT,
        logger        = logger,
    )
    n_fc = validate_file(FORECAST_PATH, "global_forecast.csv", min_rows=100)
    ok(f"Forecast rows: {n_fc:,}  |  Method: {forecast_df['forecast_method'].iloc[0]}")

    # Collect metrics for final banner
    for r in eval_results:
        if "LightGBM" in r["name"]:
            results["lgbm_mae"] = round(r["mae"], 2)
        if "Historical Mean" in r["name"]:
            results["baseline_mae"] = round(r["mae"], 2)

    ok(f"Step 6 done in {time.time()-t0:.1f}s")
except Exception as e:
    fail("Global Forecast Model", e)


# ==================================================================
# STEP 7 — VOLATILITY SCORING
# ==================================================================

banner("STEP 7 / 10 — Volatility Scoring")
t0 = time.time()
try:
    from src.volatility_scoring import run_volatility_scoring
    df_vol = run_volatility_scoring(WEEKLY_PATH, VOLATILITY_PATH, logger)
    n_vol  = validate_file(VOLATILITY_PATH, "volatility_scores.csv", min_rows=100)
    class_counts = df_vol["volatility_class"].value_counts()
    ok(f"Volatile-growing: {class_counts.get('volatile_growing',0)}  |  "
       f"Volatile-stable: {class_counts.get('volatile_stable',0)}  |  "
       f"Stable: {class_counts.get('stable_flat',0)+class_counts.get('stable_growing',0)}")
    ok(f"Step 7 done in {time.time()-t0:.1f}s")
except Exception as e:
    fail("Volatility Scoring", e)


# ==================================================================
# STEP 8 — FINAL PRIORITY + TEAM ALLOCATION
# ==================================================================

banner("STEP 8 / 10 — Final Priority Scoring & Team Allocation")
t0 = time.time()
try:
    from src.final_priority import build_final_table
    df_priority = build_final_table(
        forecast_path    = FORECAST_PATH,
        volatility_path  = VOLATILITY_PATH,
        cii_path         = CII_PATH,
        registry_path    = REGISTRY_PATH,
        output_path      = PRIORITY_PATH,
        teams_path       = TEAMS_PATH,
        assignments_path = ASSIGNMENTS_PATH,
        k                = SHRINKAGE_K,
    )
    validate_file(PRIORITY_PATH,  "final_priority_table.csv", min_rows=100)
    validate_file(TEAMS_PATH,      "patrol_teams.csv",         min_rows=40)
    validate_file(ASSIGNMENTS_PATH,"team_assignments.csv",     min_rows=1)

    tier_counts = df_priority["tier"].value_counts()
    results["zones_total"]    = len(df_priority)
    results["red"]            = int(tier_counts.get("Red",   0))
    results["amber"]          = int(tier_counts.get("Amber", 0))
    results["green"]          = int(tier_counts.get("Green", 0))
    results["teams_deployed"] = int(pd.read_csv(ASSIGNMENTS_PATH).shape[0])
    if "volatility_class" in df_priority.columns:
        results["volatile_growing"] = int(
            ((df_priority["tier"] == "Red") & (df_priority["volatility_class"] == "volatile_growing")).sum()
        )
    if "confidence_level" in df_priority.columns:
        cl = df_priority["confidence_level"].value_counts()
        results["conf_high"]   = int(cl.get("High",   0))
        results["conf_medium"] = int(cl.get("Medium", 0))
        results["conf_low"]    = int(cl.get("Low",    0))

    ok(f"Red={results['red']}  Amber={results['amber']}  Green={results['green']}")
    ok(f"Teams deployed: {results['teams_deployed']}/40")
    ok(f"Step 8 done in {time.time()-t0:.1f}s")
except Exception as e:
    fail("Final Priority", e)


# ==================================================================
# STEP 9 — FEEDBACK MANAGER  (init + mock data)
# ==================================================================

banner("STEP 9 / 10 — Feedback Manager & Mock Field Data")
t0 = time.time()
try:
    from src.mock_feedback_generator import generate_mock_outcomes
    from src.feedback_manager        import check_retrain_trigger, prepare_retrain_data

    outcomes_df = generate_mock_outcomes(
        assignments_path = ASSIGNMENTS_PATH,
        outcomes_path    = OUTCOMES_PATH,
    )
    validate_file(OUTCOMES_PATH, "enforcement_outcomes.csv", min_rows=1)
    check_retrain_trigger()
    prepare_retrain_data(
        outcomes_path = OUTCOMES_PATH,
        weekly_path   = WEEKLY_PATH,
        output_path   = rp("data/processed/retrain_ready.csv"),
    )

    n_outcomes = len(outcomes_df)
    fp_rate    = (outcomes_df["outcome_type"] == "false_positive").mean() * 100
    results["mock_outcomes"] = n_outcomes
    results["fp_rate_pct"]   = round(fp_rate, 1)

    ok(f"Outcomes generated: {n_outcomes}  |  FP rate: {fp_rate:.1f}%")
    ok(f"Step 9 done in {time.time()-t0:.1f}s")
except Exception as e:
    fail("Feedback Manager", e)


# ==================================================================
# STEP 10 — HEATMAP DATA EXPORT
# ==================================================================

banner("STEP 10 / 10 — Heatmap Data Export")
t0 = time.time()
try:
    from src.heatmap_data_export import export_heatmap_data
    bands = export_heatmap_data(
        priority_table_path   = PRIORITY_PATH,
        cluster_registry_path = REGISTRY_PATH,
        output_path           = HEATMAP_PATH,
        assignments_path      = ASSIGNMENTS_PATH,
    )
    heatmap_zones = sum(len(v) for v in bands.values())
    results["heatmap_zones"] = heatmap_zones
    ok(f"Heatmap zones exported: {heatmap_zones}")
    ok(f"Step 10 done in {time.time()-t0:.1f}s")
except Exception as e:
    fail("Heatmap Data Export", e)


# ==================================================================
# FINAL SUMMARY BANNER
# ==================================================================

total_elapsed = time.time() - pipeline_start

print()
print("=== GRIDLOCK 2.0 PIPELINE COMPLETE ===")
print(f"Zones identified: {results['zones_total']} "
      f"(Red: {results['red']} | Amber: {results['amber']} | Green: {results['green']})")
print(f"Teams deployed: {results['teams_deployed']}/40")
print(f"Volatile-growing hotspots: {results['volatile_growing']}")

lgbm_str = f"{results['lgbm_mae']}" if results['lgbm_mae'] is not None else "N/A"
base_str  = f"{results['baseline_mae']}" if results['baseline_mae'] is not None else "N/A"
print(f"Global model MAE: {lgbm_str} | Baseline MAE: {base_str}")
print(f"Forecast confidence: High {results['conf_high']} | "
      f"Medium {results['conf_medium']} | Low {results['conf_low']}")
print(f"Mock feedback outcomes: {results['mock_outcomes']} "
      f"(FP rate: {results['fp_rate_pct']}%)")
print(f"Heatmap zones exported: {results['heatmap_zones']}")
print("======================================")
print(f"\nTotal pipeline time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
print(f"Full log: {log_path}")
print()
