"""
validate_outputs.py
====================
Gridlock 2.0 - Pipeline Validation Report Generator

Loads all pipeline outputs and prints a structured validation report.
Saves the same report to data/processed/pipeline_validation_report.txt

Usage:
    gridlock_env\\Scripts\\python.exe validate_outputs.py
"""

import os
import sys
import json
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np

# ------------------------------------------------------------------
# PATH SETUP
# ------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.utils import load_config

CONFIG_PATH = os.path.join(PROJECT_ROOT, "configs", "config.yaml")
config      = load_config(CONFIG_PATH)

def rp(rel: str) -> str:
    return os.path.join(PROJECT_ROOT, rel)

# ------------------------------------------------------------------
# ALL FILE PATHS
# ------------------------------------------------------------------
RAW_DATA_PATH     = r"D:\Flipkart-r2\Data\jan to may police violation_anonymized791b166 (1).csv"
CLEANED_PATH      = rp(config["data"]["cleaned_violation_path"])
CLUSTERED_PATH    = rp(config["data"]["clustered_violation_path"])
REGISTRY_PATH     = rp(config["data"]["cluster_registry_path"])
WEEKLY_PATH       = rp(config["forecasting"]["weekly_aggregation_path"])
FORECAST_PATH     = rp("data/processed/global_forecast.csv")
VOLATILITY_PATH   = rp("data/processed/volatility_scores.csv")
PRIORITY_PATH     = rp(config["forecasting"]["final_priority_table_path"])
ASSIGNMENTS_PATH  = rp("data/processed/team_assignments.csv")
OUTCOMES_PATH     = rp("data/processed/enforcement_outcomes.csv")
HEATMAP_PATH      = rp(config["forecasting"]["heatmap_data_path"])
RETRAIN_STATUS    = rp("data/processed/retrain_status.json")
REPORT_PATH       = rp("data/processed/pipeline_validation_report.txt")

TOTAL_TEAMS       = 40
TOTAL_STATIONS    = 10


# ==================================================================
# SAFE LOADERS
# ==================================================================

def load_csv(path: str, label: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"[MISSING] {label}: {path}")
    return pd.read_csv(path, low_memory=False)


def load_json(path: str, label: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"[MISSING] {label}: {path}")
    with open(path) as f:
        return json.load(f)


# ==================================================================
# DATA COLLECTION
# ==================================================================

def collect_all() -> dict:
    d = {}

    # ── 1. Raw + cleaned counts ───────────────────────────────────
    if os.path.exists(RAW_DATA_PATH):
        d["raw_rows"] = sum(1 for _ in open(RAW_DATA_PATH, encoding="utf-8")) - 1
    else:
        d["raw_rows"] = "N/A"

    cleaned = load_csv(CLEANED_PATH, "cleaned_violations.csv")
    d["clean_rows"]     = len(cleaned)
    d["retention_pct"]  = (
        round(d["clean_rows"] / d["raw_rows"] * 100, 1)
        if isinstance(d["raw_rows"], int) else "N/A"
    )

    # Time band distribution from cleaned data
    if "time_band" in cleaned.columns:
        tb = cleaned["time_band"].value_counts(normalize=True) * 100
        d["time_band_dist"] = {k: round(v, 1) for k, v in tb.items()}
    else:
        d["time_band_dist"] = {}

    # ── 2. Clustering ─────────────────────────────────────────────
    clustered = load_csv(CLUSTERED_PATH, "clustered_violations.csv")
    d["total_points"]  = len(clustered)
    d["noise_count"]   = int((clustered["cluster_id"] == -1).sum())
    d["noise_pct"]     = round(d["noise_count"] / d["total_points"] * 100, 1)

    registry = load_csv(REGISTRY_PATH, "cluster_registry.csv")
    d["n_clusters"] = registry["cluster_id"].nunique()

    # ── 3. Forecast ───────────────────────────────────────────────
    forecast = load_csv(FORECAST_PATH, "global_forecast.csv")
    d["forecast_method"] = (
        "Global LightGBM"
        if forecast["forecast_method"].iloc[0] == "global_lgbm"
        else "Historical Mean"
    )

    # MAE / RMSE: compute from forecast vs weekly actual (last 5 weeks)
    weekly = load_csv(WEEKLY_PATH, "weekly_cluster_timeband.csv")
    weekly["week"] = pd.to_datetime(weekly["week"])
    last5_cutoff   = sorted(weekly["week"].unique())[-5]
    test_weekly    = weekly[weekly["week"] >= last5_cutoff]

    test_merged = test_weekly.merge(
        forecast[["cluster_id", "time_band", "predicted_violations"]],
        on=["cluster_id", "time_band"],
        how="inner",
    )
    if len(test_merged) > 0:
        residuals    = test_merged["violation_count"] - test_merged["predicted_violations"]
        d["mae"]     = round(float(residuals.abs().mean()), 2)
        d["rmse"]    = round(float(np.sqrt((residuals ** 2).mean())), 2)
    else:
        d["mae"]  = "N/A"
        d["rmse"] = "N/A"

    # ── 4. Volatility ─────────────────────────────────────────────
    volatility = load_csv(VOLATILITY_PATH, "volatility_scores.csv")
    d["volatile_growing"] = int((volatility["volatility_class"] == "volatile_growing").sum())

    # ── 5. Priority zones ─────────────────────────────────────────
    priority = load_csv(PRIORITY_PATH, "final_priority_table.csv")

    tier_counts   = priority["tier"].value_counts()
    d["n_red"]    = int(tier_counts.get("Red",   0))
    d["n_amber"]  = int(tier_counts.get("Amber", 0))
    d["n_green"]  = int(tier_counts.get("Green", 0))
    d["n_total"]  = len(priority)

    # Confidence
    if "confidence_level" in priority.columns:
        cl = priority["confidence_level"].value_counts()
        d["conf_high"]   = int(cl.get("High",   0))
        d["conf_medium"] = int(cl.get("Medium", 0))
        d["conf_low"]    = int(cl.get("Low",    0))
    else:
        d["conf_high"] = d["conf_medium"] = d["conf_low"] = "N/A"

    # Red tier police stations
    red_zones = priority[priority["tier"] == "Red"].copy()
    if "dominant_police_station" in red_zones.columns:
        d["red_stations"] = red_zones["dominant_police_station"].nunique()
    else:
        d["red_stations"] = "N/A"

    # Top 5 priority zones
    top5_cols = [
        "cluster_id", "time_band", "dominant_police_station",
        "buffered_forecast", "cii_score", "final_priority_score",
    ]
    present_cols = [c for c in top5_cols if c in priority.columns]
    top5 = priority[present_cols].head(5).reset_index(drop=True)
    d["top5"] = top5

    # ── 6. Team assignments ───────────────────────────────────────
    assign = load_csv(ASSIGNMENTS_PATH, "team_assignments.csv")
    d["n_assigned"]   = len(assign)
    d["unassigned_red"] = max(0, d["n_red"] - d["n_assigned"])
    if "priority_score" in assign.columns:
        d["avg_assigned_score"] = round(float(assign["priority_score"].mean()), 4)
    else:
        d["avg_assigned_score"] = "N/A"

    # Team lookup (cluster_id, time_band) -> team_id
    team_map = {}
    if "cluster_id" in assign.columns and "team_id" in assign.columns:
        for _, row in assign.iterrows():
            team_map[(int(row["cluster_id"]), str(row["time_band"]))] = str(row["team_id"])
    d["team_map"] = team_map

    # ── 7. Feedback / outcomes ────────────────────────────────────
    outcomes = load_csv(OUTCOMES_PATH, "enforcement_outcomes.csv")
    d["n_outcomes"]    = len(outcomes)
    ot = outcomes["outcome_type"].value_counts(normalize=True) * 100
    d["confirmed_pct"]  = round(float(ot.get("violation_confirmed", 0)), 1)
    d["fp_pct"]         = round(float(ot.get("false_positive",       0)), 1)

    # Per-zone FP rate  > 50%
    fp_by_zone = (
        outcomes.groupby("cluster_id")["outcome_type"]
        .apply(lambda s: (s == "false_positive").mean())
    )
    d["zones_fp_over50"] = int((fp_by_zone > 0.50).sum())

    # Retrain trigger
    d["retrain_trigger"] = "NO"
    if os.path.exists(RETRAIN_STATUS):
        with open(RETRAIN_STATUS) as f:
            rs = json.load(f)
        d["retrain_trigger"] = "YES" if rs.get("should_retrain", False) else "NO"

    # ── 8. Heatmap ────────────────────────────────────────────────
    heatmap = load_json(HEATMAP_PATH, "heatmap_data.json")
    d["heatmap_zones"] = sum(len(v) for v in heatmap.values())

    return d, top5, team_map


# ==================================================================
# REPORT BUILDER
# ==================================================================

def build_report(d: dict, top5: pd.DataFrame, team_map: dict) -> str:
    lines = []
    A = lines.append

    A("=== PIPELINE VALIDATION REPORT ===")
    A("")

    # ── Section 1: Data Quality ───────────────────────────────────
    A("1. DATA QUALITY")
    A(f"   Raw rows: {d['raw_rows']:,}  |  After cleaning: {d['clean_rows']:,}  "
      f"|  Retention rate: {d['retention_pct']}%")
    A(f"   Clusters found: {d['n_clusters']}  |  Noise points: {d['noise_pct']}%")

    tb = d["time_band_dist"]
    if tb:
        tb_str = "  |  ".join(f"{k}: {v}%" for k, v in sorted(tb.items()))
        A(f"   Time band distribution: [{tb_str}]")
    else:
        A("   Time band distribution: [N/A]")

    A("")

    # ── Section 2: Forecasting ────────────────────────────────────
    A("2. FORECASTING")
    A(f"   Method: {d['forecast_method']}")
    A(f"   MAE: {d['mae']} violations/week  |  RMSE: {d['rmse']}")
    A(f"   Zones with High confidence: {d['conf_high']}  "
      f"|  Medium: {d['conf_medium']}  |  Low: {d['conf_low']}")
    A(f"   Volatile-growing zones: {d['volatile_growing']} (these get 1.3x patrol buffer)")
    A("")

    # ── Section 3: Priority Zones ─────────────────────────────────
    A("3. PRIORITY ZONES")
    A(f"   Red tier: {d['n_red']} zones across {d['red_stations']} police stations")
    A("   Top 5 zones:")

    for rank, (_, row) in enumerate(top5.iterrows(), 1):
        cid    = int(row.get("cluster_id", 0))
        tband  = str(row.get("time_band", ""))
        key    = (cid, tband)
        team   = team_map.get(key, "unassigned")

        station   = str(row.get("dominant_police_station", "Unknown"))
        predicted = row.get("buffered_forecast", row.get("predicted_violations", "N/A"))
        cii       = row.get("cii_score", "N/A")
        score     = row.get("final_priority_score", "N/A")

        try:
            predicted = f"{float(predicted):.1f}"
        except (TypeError, ValueError):
            predicted = str(predicted)
        try:
            cii = f"{float(cii):.3f}"
        except (TypeError, ValueError):
            cii = str(cii)
        try:
            score = f"{float(score):.4f}"
        except (TypeError, ValueError):
            score = str(score)

        A(f"   {rank}. {station:<22} | {tband:<20} | predicted: {predicted:>7} "
          f"| CII: {cii} | score: {score} | team: {team}")
    A("")

    # ── Section 4: Team Allocation ────────────────────────────────
    A("4. TEAM ALLOCATION")
    A(f"   {TOTAL_TEAMS} teams across {TOTAL_STATIONS} stations")
    A(f"   Assigned: {d['n_assigned']}  |  "
      f"Unassigned red zones: {d['unassigned_red']} (need backup)")
    A(f"   Avg priority score of assigned zones: {d['avg_assigned_score']}")
    A("")

    # ── Section 5: Feedback Loop ──────────────────────────────────
    A("5. FEEDBACK LOOP")
    A(f"   Mock outcomes: {d['n_outcomes']}  "
      f"|  Confirmed: {d['confirmed_pct']}%  "
      f"|  False Positive: {d['fp_pct']}%")
    A(f"   Retrain trigger: {d['retrain_trigger']}")
    A(f"   Zones with >50% FP rate: {d['zones_fp_over50']} (model over-predicts here)")
    A("")

    # ── Section 6: Ready for Backend ─────────────────────────────
    A("6. READY FOR BACKEND")
    A(f"   heatmap_data.json:         {d['heatmap_zones']} zones exported")
    A(f"   team_assignments.csv:      {d['n_assigned']} rows")
    A(f"   enforcement_outcomes.csv:  {d['n_outcomes']} rows")
    A("===================================")

    return "\n".join(lines)


# ==================================================================
# MAIN
# ==================================================================

def main():
    print("Loading all pipeline outputs...")
    try:
        d, top5, team_map = collect_all()
    except FileNotFoundError as exc:
        print(f"\n[ERROR] {exc}")
        print("Run run_full_pipeline.py first to generate all outputs.")
        sys.exit(1)

    report = build_report(d, top5, team_map)

    # Print to terminal
    print()
    print(report)

    # Save to file
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)
        f.write("\n")
    print(f"\nReport saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
