"""
src/mock_feedback_generator.py
================================
Bengaluru Traffic Violation Prediction - Mock Field Feedback Generator

Loads team_assignments.csv and simulates realistic cop field outcomes
for every assignment, writing results to enforcement_outcomes.csv.

Outcome distribution:
  60%  violation_confirmed  actual = predicted x Uniform(0.70, 1.30)
  25%  false_positive       actual = 0
  10%  needs_backup         actual = predicted x Uniform(1.40, 2.00)
   5%  resolved_quickly     actual = predicted x Uniform(0.30, 0.60)

Response time: Uniform(8, 35) minutes
Arrived-at / resolved-at: simulated around 2024-04-15 08:00 IST
"""

import os
import sys
import random
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

# ------------------------------------------------------------------
# PATH SETUP
# ------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.feedback_manager import (
    initialize_outcomes,
    add_outcome,
    check_retrain_trigger,
    prepare_retrain_data,
    OUTCOMES_PATH,
)

# ------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------
RANDOM_SEED = 42

# Outcome probabilities (must sum to 1.0)
OUTCOME_PROBS = {
    "violation_confirmed" : 0.60,
    "false_positive"      : 0.25,
    "needs_backup"        : 0.10,
    "resolved_quickly"    : 0.05,
}

# Actual-violations multiplier ranges per outcome type
ACTUAL_MULTIPLIERS = {
    "violation_confirmed" : (0.70, 1.30),
    "false_positive"      : (0.00, 0.00),   # always 0
    "needs_backup"        : (1.40, 2.00),
    "resolved_quickly"    : (0.30, 0.60),
}

RESPONSE_TIME_MIN = 8.0
RESPONSE_TIME_MAX = 35.0

# Simulated patrol date (day after last forecast)
PATROL_DATE = datetime(2024, 4, 15, 8, 0, 0, tzinfo=timezone.utc)

ASSIGNMENTS_PATH = os.path.join(PROJECT_ROOT, "data/processed/team_assignments.csv")


# ==================================================================
# HELPERS
# ==================================================================

def _pick_outcome_type(rng: np.random.Generator) -> str:
    outcomes = list(OUTCOME_PROBS.keys())
    probs    = list(OUTCOME_PROBS.values())
    return rng.choice(outcomes, p=probs)


def _compute_actual(rng: np.random.Generator, outcome_type: str, predicted: float) -> float:
    lo, hi = ACTUAL_MULTIPLIERS[outcome_type]
    if lo == hi == 0.0:
        return 0.0
    multiplier = rng.uniform(lo, hi)
    return max(0.0, round(predicted * multiplier, 1))


def _make_timestamps(rng: np.random.Generator, response_minutes: float):
    """Return (arrived_at_str, resolved_at_str) as UTC ISO strings."""
    # Stagger patrol arrivals across the shift (±4 hours from PATROL_DATE)
    offset_hours = rng.uniform(-4, 4)
    arrived  = PATROL_DATE + timedelta(hours=offset_hours)
    resolved = arrived + timedelta(minutes=response_minutes)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return arrived.strftime(fmt), resolved.strftime(fmt)


# ==================================================================
# MAIN GENERATOR
# ==================================================================

def generate_mock_outcomes(
    assignments_path : str = ASSIGNMENTS_PATH,
    outcomes_path    : str = OUTCOMES_PATH,
    seed             : int = RANDOM_SEED,
) -> pd.DataFrame:
    """
    For each assignment row generate one realistic field outcome and
    write it to enforcement_outcomes.csv.

    Returns the DataFrame of generated outcomes.
    """
    rng = np.random.default_rng(seed)
    random.seed(seed)

    # Load assignments
    if not os.path.exists(assignments_path):
        raise FileNotFoundError(
            f"team_assignments.csv not found at: {assignments_path}\n"
            "Run src/final_priority.py first."
        )
    assignments = pd.read_csv(assignments_path)
    print(f"Loaded {len(assignments)} assignments from: {assignments_path}")

    # Re-initialise outcomes file (fresh for mock generation)
    if os.path.exists(outcomes_path):
        os.remove(outcomes_path)
        print(f"Removed existing outcomes file: {outcomes_path}")
    initialize_outcomes(outcomes_path)

    generated = []

    for _, row in assignments.iterrows():
        outcome_type      = _pick_outcome_type(rng)
        predicted         = float(row.get("buffered_forecast", 0) or 0)
        actual            = _compute_actual(rng, outcome_type, predicted)
        response_minutes  = round(rng.uniform(RESPONSE_TIME_MIN, RESPONSE_TIME_MAX), 1)
        arrived, resolved = _make_timestamps(rng, response_minutes)

        outcome_dict = {
            "assignment_id"           : str(row["assignment_id"]),
            "zone_id"                 : str(row["zone_id"]),
            "cluster_id"              : int(row["cluster_id"]),
            "time_band"               : str(row["time_band"]),
            "forecast_date"           : "2024-04-15",
            "predicted_violations"    : round(predicted, 2),
            "actual_violations_found" : actual,
            "outcome_type"            : outcome_type,
            "officer_id"              : str(row["team_id"]),
            "arrived_at"              : arrived,
            "resolved_at"             : resolved,
            "response_time_minutes"   : response_minutes,
        }

        oid = add_outcome(outcome_dict, path=outcomes_path)
        outcome_dict["outcome_id"] = oid
        generated.append(outcome_dict)

    outcomes_df = pd.DataFrame(generated)

    # ── Summary ────────────────────────────────────────────────────
    n               = len(outcomes_df)
    fp_rate         = (outcomes_df["outcome_type"] == "false_positive").mean()
    avg_resp        = outcomes_df["response_time_minutes"].mean()
    type_counts     = outcomes_df["outcome_type"].value_counts()

    print("\n" + "=" * 55)
    print("MOCK FEEDBACK GENERATION SUMMARY")
    print("=" * 55)
    print(f"  Outcomes generated   : {n}")
    print(f"  Saved to             : {outcomes_path}")
    print(f"\n  Outcome distribution :")
    for otype, cnt in type_counts.items():
        pct = cnt / n * 100
        print(f"    {otype:<22} : {cnt:>3}  ({pct:.1f}%)")
    print(f"\n  False positive rate  : {fp_rate:.1%}")
    print(f"  Avg response time    : {avg_resp:.1f} min")
    print(f"  Min response time    : {outcomes_df['response_time_minutes'].min():.1f} min")
    print(f"  Max response time    : {outcomes_df['response_time_minutes'].max():.1f} min")

    avg_ratio_df = outcomes_df[
        (outcomes_df["predicted_violations"] > 0) &
        (outcomes_df["outcome_type"] != "false_positive")
    ].copy()
    if len(avg_ratio_df) > 0:
        avg_ratio_df["ratio"] = (
            avg_ratio_df["actual_violations_found"] / avg_ratio_df["predicted_violations"]
        )
        print(f"\n  Avg actual/predicted ratio (excl. FP): "
              f"{avg_ratio_df['ratio'].mean():.3f}")

    print("=" * 55)

    return outcomes_df


# ==================================================================
# CLI ENTRY POINT
# ==================================================================

if __name__ == "__main__":
    # Step 1: Generate mock field outcomes
    outcomes_df = generate_mock_outcomes()

    # Step 2: Check whether these outcomes trigger retraining
    print()
    triggered = check_retrain_trigger()

    # Step 3: Prepare ground-truth-merged retrain dataset
    print()
    try:
        prepare_retrain_data()
    except FileNotFoundError as e:
        print(f"[prepare_retrain_data] Skipped: {e}")
