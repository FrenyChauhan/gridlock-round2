"""
src/feedback_manager.py
========================
Bengaluru Traffic Violation Prediction - Enforcement Feedback Manager

Handles cop field outcomes feeding back into the prediction system.

Functions:
  - initialize_outcomes()       : create enforcement_outcomes.csv if absent
  - add_outcome(outcome_dict)   : append a single validated outcome row
  - get_zone_stats(cluster_id)  : per-zone accuracy & response stats
  - check_retrain_trigger()     : decide if model retraining is warranted
  - prepare_retrain_data()      : merge outcomes with weekly agg for ground truth
"""

import os
import sys
import json
import uuid
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from datetime import datetime, timezone

# ------------------------------------------------------------------
# PATH SETUP
# ------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils import load_config

# ------------------------------------------------------------------
# FILE PATHS
# ------------------------------------------------------------------
_config = load_config(os.path.join(PROJECT_ROOT, "configs", "config.yaml"))

OUTCOMES_PATH      = os.path.join(PROJECT_ROOT, "data/processed/enforcement_outcomes.csv")
RETRAIN_STATUS     = os.path.join(PROJECT_ROOT, "data/processed/retrain_status.json")
RETRAIN_READY_PATH = os.path.join(PROJECT_ROOT, "data/processed/retrain_ready.csv")
WEEKLY_PATH        = os.path.join(PROJECT_ROOT,
                        _config["forecasting"]["weekly_aggregation_path"])

# ------------------------------------------------------------------
# SCHEMA
# ------------------------------------------------------------------
OUTCOMES_SCHEMA = {
    "outcome_id"               : str,
    "assignment_id"            : str,
    "zone_id"                  : str,
    "cluster_id"               : int,
    "time_band"                : str,
    "forecast_date"            : str,
    "predicted_violations"     : float,
    "actual_violations_found"  : float,
    "outcome_type"             : str,     # violation_confirmed | false_positive |
                                          # needs_backup | resolved_quickly
    "officer_id"               : str,
    "arrived_at"               : str,
    "resolved_at"              : str,
    "response_time_minutes"    : float,
    "created_at"               : str,
}

VALID_OUTCOME_TYPES = {
    "violation_confirmed",
    "false_positive",
    "needs_backup",
    "resolved_quickly",
}

# Thresholds for retrain trigger
RETRAIN_NEW_OUTCOMES_THRESHOLD   = 100
FP_RATE_THRESHOLD                = 0.65
FP_LOOKBACK_ASSIGNMENTS          = 15


# ==================================================================
# HELPERS
# ==================================================================

def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _new_outcome_id() -> str:
    return "OC-" + str(uuid.uuid4())[:8].upper()


# ==================================================================
# 1.  INITIALISE
# ==================================================================

def initialize_outcomes(path: str = OUTCOMES_PATH) -> pd.DataFrame:
    """
    Create enforcement_outcomes.csv with the correct schema if it does not
    exist. If it already exists, load and return it unchanged.

    Returns the (possibly empty) DataFrame.
    """
    _ensure_dir(path)

    if os.path.exists(path):
        df = pd.read_csv(path)
        # Ensure all schema columns exist (forward-compatible)
        for col, dtype in OUTCOMES_SCHEMA.items():
            if col not in df.columns:
                df[col] = None
        return df

    df = pd.DataFrame(columns=list(OUTCOMES_SCHEMA.keys()))
    df.to_csv(path, index=False)
    print(f"[feedback_manager] Initialised empty outcomes file: {path}")
    return df


# ==================================================================
# 2.  ADD OUTCOME
# ==================================================================

def add_outcome(
    outcome_dict : dict,
    path         : str = OUTCOMES_PATH,
) -> str:
    """
    Validate and append a single enforcement outcome row.

    Required keys in outcome_dict:
      assignment_id, zone_id, cluster_id, time_band, forecast_date,
      predicted_violations, actual_violations_found, outcome_type

    Optional (will be auto-filled if missing):
      outcome_id, officer_id, arrived_at, resolved_at,
      response_time_minutes, created_at

    Returns the outcome_id (str).
    """
    # ── Validate required fields ───────────────────────────────────
    required = [
        "assignment_id", "zone_id", "cluster_id", "time_band",
        "forecast_date", "predicted_violations",
        "actual_violations_found", "outcome_type",
    ]
    missing_keys = [k for k in required if k not in outcome_dict]
    if missing_keys:
        raise ValueError(f"add_outcome: missing required fields: {missing_keys}")

    if outcome_dict["outcome_type"] not in VALID_OUTCOME_TYPES:
        raise ValueError(
            f"add_outcome: invalid outcome_type '{outcome_dict['outcome_type']}'. "
            f"Must be one of {sorted(VALID_OUTCOME_TYPES)}"
        )

    # ── Auto-fill optional fields ──────────────────────────────────
    row = dict(outcome_dict)
    row.setdefault("outcome_id",            _new_outcome_id())
    row.setdefault("officer_id",            "UNKNOWN")
    row.setdefault("arrived_at",            _now_utc())
    row.setdefault("resolved_at",           _now_utc())
    row.setdefault("response_time_minutes", None)
    row.setdefault("created_at",            _now_utc())

    # ── Coerce types ───────────────────────────────────────────────
    row["cluster_id"]              = int(row["cluster_id"])
    row["predicted_violations"]    = float(row["predicted_violations"])
    row["actual_violations_found"] = float(row["actual_violations_found"])
    if row["response_time_minutes"] is not None:
        row["response_time_minutes"] = float(row["response_time_minutes"])

    # ── Append ─────────────────────────────────────────────────────
    initialize_outcomes(path)    # create file if absent
    existing = pd.read_csv(path)
    new_row  = pd.DataFrame([row])
    updated  = pd.concat([existing, new_row], ignore_index=True)
    updated.to_csv(path, index=False)

    return row["outcome_id"]


# ==================================================================
# 3.  ZONE STATS
# ==================================================================

def get_zone_stats(
    cluster_id : int,
    path       : str = OUTCOMES_PATH,
) -> dict:
    """
    Return accuracy and response-time statistics for one cluster.

    Returns
    -------
    dict with keys:
      total_assignments, confirmed_rate, false_positive_rate,
      avg_actual_vs_predicted_ratio, avg_response_minutes
    Returns None if no outcomes exist for this cluster.
    """
    if not os.path.exists(path):
        return None

    df = pd.read_csv(path)
    zone_df = df[df["cluster_id"] == int(cluster_id)].copy()

    if zone_df.empty:
        return None

    n = len(zone_df)

    confirmed_rate = (zone_df["outcome_type"] == "violation_confirmed").mean()
    fp_rate        = (zone_df["outcome_type"] == "false_positive").mean()

    # Actual/predicted ratio (skip false positives where predicted=0 or actual=0)
    ratio_df = zone_df[
        (zone_df["predicted_violations"] > 0) &
        (zone_df["outcome_type"] != "false_positive")
    ].copy()
    if len(ratio_df) > 0:
        ratio_df["ratio"] = (
            ratio_df["actual_violations_found"] / ratio_df["predicted_violations"]
        )
        avg_ratio = float(ratio_df["ratio"].mean())
    else:
        avg_ratio = None

    avg_resp = None
    resp_df = zone_df["response_time_minutes"].dropna()
    if len(resp_df) > 0:
        avg_resp = float(resp_df.mean())

    return {
        "cluster_id"                  : int(cluster_id),
        "total_assignments"           : n,
        "confirmed_rate"              : round(confirmed_rate, 4),
        "false_positive_rate"         : round(fp_rate, 4),
        "avg_actual_vs_predicted_ratio": round(avg_ratio, 4) if avg_ratio is not None else None,
        "avg_response_minutes"        : round(avg_resp, 2) if avg_resp is not None else None,
    }


# ==================================================================
# 4.  RETRAIN TRIGGER CHECK
# ==================================================================

def check_retrain_trigger(
    path           : str = OUTCOMES_PATH,
    status_path    : str = RETRAIN_STATUS,
) -> bool:
    """
    Return True if retraining should be triggered.

    Trigger conditions (OR):
      A. >= RETRAIN_NEW_OUTCOMES_THRESHOLD new outcomes since last check
      B. Any zone has false_positive_rate > FP_RATE_THRESHOLD
         over its last FP_LOOKBACK_ASSIGNMENTS assignments

    Saves/updates retrain_status.json.
    """
    _ensure_dir(status_path)

    # Load previous status
    if os.path.exists(status_path):
        with open(status_path, "r") as f:
            status = json.load(f)
    else:
        status = {"last_checked_count": 0, "last_checked_at": None}

    if not os.path.exists(path):
        print("[check_retrain_trigger] No outcomes file found. No trigger.")
        return False

    df = pd.read_csv(path)
    current_count = len(df)
    last_count    = int(status.get("last_checked_count", 0))
    new_count     = current_count - last_count

    should_retrain = False
    trigger_reason = []

    # Condition A
    if new_count >= RETRAIN_NEW_OUTCOMES_THRESHOLD:
        should_retrain = True
        trigger_reason.append(
            f"Condition A: {new_count} new outcomes >= threshold {RETRAIN_NEW_OUTCOMES_THRESHOLD}"
        )

    # Condition B: per-zone false positive rate over last N assignments
    if not df.empty:
        for cid, grp in df.groupby("cluster_id"):
            recent = grp.tail(FP_LOOKBACK_ASSIGNMENTS)
            fp_rate = (recent["outcome_type"] == "false_positive").mean()
            if fp_rate > FP_RATE_THRESHOLD:
                should_retrain = True
                trigger_reason.append(
                    f"Condition B: cluster {cid} FP rate={fp_rate:.2f} > "
                    f"{FP_RATE_THRESHOLD} over last {len(recent)} assignments"
                )
                break   # one zone is enough to trigger

    # Update status
    status.update({
        "last_checked_count" : current_count,
        "last_checked_at"    : _now_utc(),
        "should_retrain"     : should_retrain,
        "trigger_reasons"    : trigger_reason,
        "total_outcomes"     : current_count,
        "new_since_last"     : new_count,
    })
    with open(status_path, "w") as f:
        json.dump(status, f, indent=2)

    if should_retrain:
        print(f"[check_retrain_trigger] RETRAIN TRIGGERED:")
        for r in trigger_reason:
            print(f"  - {r}")
    else:
        print(f"[check_retrain_trigger] No retrain needed. "
              f"({new_count} new outcomes, threshold={RETRAIN_NEW_OUTCOMES_THRESHOLD})")

    return should_retrain


# ==================================================================
# 5.  PREPARE RETRAIN DATA
# ==================================================================

def prepare_retrain_data(
    outcomes_path  : str = OUTCOMES_PATH,
    weekly_path    : str = WEEKLY_PATH,
    output_path    : str = RETRAIN_READY_PATH,
) -> pd.DataFrame:
    """
    Merge enforcement outcomes with the weekly aggregated time series.

    Where an actual field outcome exists for a (cluster_id, time_band, week):
      - Replace violation_count with actual_violations_found  (ground truth)
      - Flag the row as has_ground_truth = True

    Rows without matching outcomes are kept as-is (has_ground_truth = False).

    Saves to data/processed/retrain_ready.csv.
    """
    if not os.path.exists(outcomes_path):
        raise FileNotFoundError(
            f"Outcomes file not found: {outcomes_path}. "
            "Run mock_feedback_generator.py first."
        )
    if not os.path.exists(weekly_path):
        raise FileNotFoundError(
            f"Weekly aggregation not found: {weekly_path}. "
            "Run weekly_aggregation.py first."
        )

    outcomes = pd.read_csv(outcomes_path)
    weekly   = pd.read_csv(weekly_path)
    weekly["week"] = pd.to_datetime(weekly["week"])

    # Parse forecast_date in outcomes -> week start (Monday-anchored)
    outcomes["forecast_date"] = pd.to_datetime(outcomes["forecast_date"], errors="coerce")
    outcomes["week"] = outcomes["forecast_date"].dt.to_period("W-SUN").apply(
        lambda p: p.start_time if pd.notna(p) else pd.NaT
    )

    # Aggregate outcomes to (cluster_id, time_band, week):
    # take mean of actual_violations_found where multiple outcomes per cell
    agg_outcomes = (
        outcomes
        .dropna(subset=["week"])
        .groupby(["cluster_id", "time_band", "week"])
        .agg(
            actual_violations_found=("actual_violations_found", "mean"),
            outcome_count=("outcome_id", "count"),
        )
        .reset_index()
    )

    # Merge onto weekly
    merged = weekly.merge(
        agg_outcomes,
        on=["cluster_id", "time_band", "week"],
        how="left",
    )

    # Override violation_count where we have ground truth
    merged["has_ground_truth"] = merged["actual_violations_found"].notna()
    merged["violation_count_original"] = merged["violation_count"].copy()
    merged.loc[merged["has_ground_truth"], "violation_count"] = (
        merged.loc[merged["has_ground_truth"], "actual_violations_found"]
    )

    _ensure_dir(output_path)
    merged.to_csv(output_path, index=False)

    n_gt  = merged["has_ground_truth"].sum()
    n_tot = len(merged)
    print(f"\n[prepare_retrain_data] Retrain-ready dataset saved: {output_path}")
    print(f"  Total rows          : {n_tot:,}")
    print(f"  Rows with GT        : {n_gt:,}  ({n_gt/n_tot*100:.1f}% have field-verified counts)")
    print(f"  Rows without GT     : {n_tot - n_gt:,}  (using original weekly aggregation)")

    return merged
