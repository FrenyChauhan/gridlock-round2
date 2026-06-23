"""
src/final_priority.py
=====================
Bengaluru Traffic Violation Prediction - Final Priority Scoring & Team Allocation

Pipeline:
  1. Load global_forecast.csv, volatility_scores.csv, cii_scores.csv,
     cluster_registry.csv
  2. Compute buffered_forecast = predicted_violations x patrol_buffer_multiplier
  3. Hotspot score with Bayesian shrinkage (UNCHANGED from original)
  4. Final Priority Score = hotspot_score x cii_score  (UNCHANGED)
  5. Tier assignment: Red top-20%, Amber next-30%, Green bottom-50% (UNCHANGED)
  6. Add volatility columns + confidence_level
  7. Generate patrol_teams.csv (40 teams, 10 stations, 4 each)
  8. Greedy zone-to-team allocation -> team_assignments.csv
  9. Print summary report
"""

import os
import sys
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


# ==================================================================
# CONSTANTS
# ==================================================================

STATIONS = [
    "Upparpet", "Shivajinagar", "Malleshwaram", "HAL Old Airport",
    "City Market", "Vijayanagara", "Rajajinagar", "Kodigehalli",
    "Magadi Road", "Jeevanbheemanagar",
]
TEAMS_PER_STATION = 4
TOTAL_TEAMS       = len(STATIONS) * TEAMS_PER_STATION   # 40


# ==================================================================
# 1.  BAYESIAN SHRINKAGE + HOTSPOT SCORE  (unchanged logic)
# ==================================================================

def compute_hotspot_score(
    df: pd.DataFrame,
    volume_col: str,
    global_mean_severity: float,
    k: float = 30,
) -> pd.DataFrame:
    """
    Shrink each cluster's severity toward the global mean, weighted by
    how much data that cluster has:

        adjusted = (n * own_mean + k * global_mean) / (n + k)

    Then compute raw hotspot score and MinMax-normalise.
    Uses 'buffered_forecast' as the volume driver (instead of raw prediction).
    """
    df = df.copy()

    n = df[volume_col]
    df["adjusted_severity_norm"] = (
        n * df["mean_combined_severity"] + k * global_mean_severity
    ) / (n + k)

    df["hotspot_score_raw"] = df[volume_col] * df["adjusted_severity_norm"]

    lo, hi = df["hotspot_score_raw"].min(), df["hotspot_score_raw"].max()
    if hi > lo:
        df["hotspot_score"] = (df["hotspot_score_raw"] - lo) / (hi - lo)
    else:
        df["hotspot_score"] = 0.0

    return df


# ==================================================================
# 2.  TIER ASSIGNMENT  (unchanged logic)
# ==================================================================

def assign_tiers(df: pd.DataFrame, score_col: str = "final_priority_score") -> tuple:
    df = df.copy()
    red_thresh   = df[score_col].quantile(0.80)
    amber_thresh = df[score_col].quantile(0.50)

    def _tier(score):
        if score >= red_thresh:
            return "Red"
        elif score >= amber_thresh:
            return "Amber"
        return "Green"

    df["tier"] = df[score_col].apply(_tier)
    return df, red_thresh, amber_thresh


# ==================================================================
# 3.  CONFIDENCE LEVEL  (from cv)
# ==================================================================

def confidence_level(cv: float) -> str:
    if cv < 0.3:
        return "High"
    elif cv <= 0.6:
        return "Medium"
    return "Low"


# ==================================================================
# 4.  PATROL TEAMS TABLE
# ==================================================================

def build_patrol_teams() -> pd.DataFrame:
    """Create 40 teams distributed evenly across 10 stations (4 each)."""
    rows = []
    team_num = 1
    for station in STATIONS:
        for _ in range(TEAMS_PER_STATION):
            rows.append({
                "team_id"      : f"T{team_num:03d}",
                "status"       : "available",
                "current_zone" : None,
                "station"      : station,
            })
            team_num += 1
    return pd.DataFrame(rows)


# ==================================================================
# 5.  GREEDY ALLOCATION
# ==================================================================

def greedy_allocate(
    priority_df : pd.DataFrame,
    teams_df    : pd.DataFrame,
    registry    : pd.DataFrame,
) -> pd.DataFrame:
    """
    Assign available teams to Red-tier zones by priority score.

    Strategy:
    - Sort Red zones by final_priority_score descending.
    - For each zone: prefer a team from the zone's dominant_station.
    - If no same-station team is available, take any available team.
    - Mark assigned teams as 'assigned'.
    """
    teams = teams_df.copy()
    teams["available"] = teams["status"] == "available"

    red_zones = (
        priority_df[priority_df["tier"] == "Red"]
        .sort_values("final_priority_score", ascending=False)
        .reset_index(drop=True)
    )

    # Pull centroid coords from registry for the output
    reg_coords = registry[["cluster_id", "centroid_lat", "centroid_lon"]].copy()

    assignments = []
    assignment_id = 1
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for _, zone in red_zones.iterrows():
        station = str(zone.get("dominant_police_station", "")).strip()

        # Try same-station team first
        same_mask = teams["available"] & (teams["station"] == station)
        any_mask  = teams["available"]

        if same_mask.any():
            idx = same_mask.idxmax()
        elif any_mask.any():
            idx = any_mask.idxmax()
        else:
            break   # all 40 teams assigned

        team = teams.loc[idx]
        teams.at[idx, "status"]    = "assigned"
        teams.at[idx, "available"] = False
        teams.at[idx, "current_zone"] = int(zone["cluster_id"])

        # Centroid
        coords = reg_coords[reg_coords["cluster_id"] == zone["cluster_id"]]
        lat = float(coords["centroid_lat"].iloc[0]) if not coords.empty else None
        lon = float(coords["centroid_lon"].iloc[0]) if not coords.empty else None

        assignments.append({
            "assignment_id"     : f"A{assignment_id:04d}",
            "team_id"           : team["team_id"],
            "zone_id"           : f"ZONE-{int(zone['cluster_id']):04d}",
            "cluster_id"        : int(zone["cluster_id"]),
            "centroid_lat"      : lat,
            "centroid_lon"      : lon,
            "tier"              : zone["tier"],
            "priority_score"    : round(float(zone["final_priority_score"]), 6),
            "buffered_forecast" : round(float(zone["buffered_forecast"]), 2),
            "time_band"         : zone["time_band"],
            "volatility_class"  : zone.get("volatility_class", ""),
            "dominant_station"  : station,
            "status"            : "predicted",
            "assigned_at"       : now_str,
        })
        assignment_id += 1

    assign_df = pd.DataFrame(assignments)
    return assign_df, teams


# ==================================================================
# 6.  MAIN BUILD FUNCTION
# ==================================================================

def build_final_table(
    forecast_path    : str,
    volatility_path  : str,
    cii_path         : str,
    registry_path    : str,
    output_path      : str,
    teams_path       : str,
    assignments_path : str,
    k                : float = 30,
) -> pd.DataFrame:

    # ── Load ──────────────────────────────────────────────────────
    print("Loading inputs...")
    forecast   = pd.read_csv(forecast_path)
    volatility = pd.read_csv(volatility_path)
    cii        = pd.read_csv(cii_path)
    registry   = pd.read_csv(registry_path)

    print(f"  global_forecast   : {forecast.shape}")
    print(f"  volatility_scores : {volatility.shape}")
    print(f"  cii_scores        : {cii.shape}")
    print(f"  cluster_registry  : {registry.shape}")

    # ── Merge forecast + volatility ───────────────────────────────
    df = forecast.merge(
        volatility[[
            "cluster_id", "time_band",
            "patrol_buffer_multiplier", "volatility_class",
            "trend_slope", "cv",
        ]],
        on=["cluster_id", "time_band"],
        how="left",
    )
    df["patrol_buffer_multiplier"] = df["patrol_buffer_multiplier"].fillna(1.0)
    df["volatility_class"]         = df["volatility_class"].fillna("stable_flat")
    df["trend_slope"]              = df["trend_slope"].fillna(0.0)
    df["cv"]                       = df["cv"].fillna(0.0)

    # ── Buffered forecast ──────────────────────────────────────────
    df["buffered_forecast"] = df["predicted_violations"] * df["patrol_buffer_multiplier"]

    # ── Merge registry for severity + metadata ────────────────────
    reg_cols = [
        "cluster_id", "mean_combined_severity",
        "centroid_lat", "centroid_lon", "radius_m",
        "dominant_police_station", "dominant_junction",
    ]
    df = df.merge(registry[reg_cols], on="cluster_id", how="left")

    # ── Merge CII ─────────────────────────────────────────────────
    df = df.merge(
        cii[["cluster_id", "time_band", "cii_score",
             "dominant_police_station", "dominant_junction"]],
        on=["cluster_id", "time_band"],
        how="left",
        suffixes=("", "_cii"),
    )
    # Prefer CII dominant_police_station (per time_band resolution) where available
    df["dominant_police_station"] = df["dominant_police_station_cii"].combine_first(
        df["dominant_police_station"]
    )
    df["dominant_junction"] = df["dominant_junction_cii"].combine_first(
        df["dominant_junction"]
    )
    df = df.drop(columns=["dominant_police_station_cii", "dominant_junction_cii"],
                 errors="ignore")

    missing_cii = df["cii_score"].isna().sum()
    if missing_cii:
        print(f"  WARNING: {missing_cii} rows have no CII score — filling with global mean.")
    df["cii_score"] = df["cii_score"].fillna(df["cii_score"].mean())

    # ── Bayesian shrinkage + hotspot score ────────────────────────
    global_mean_severity = (
        df["buffered_forecast"] * df["mean_combined_severity"]
    ).sum() / df["buffered_forecast"].sum()
    print(f"\nGlobal mean severity (shrinkage prior): {global_mean_severity:.4f}  k={k}")

    df = compute_hotspot_score(df, "buffered_forecast", global_mean_severity, k=k)

    # ── Final priority score + tiers ──────────────────────────────
    df["final_priority_score"] = df["hotspot_score"] * df["cii_score"]
    df, red_thresh, amber_thresh = assign_tiers(df)

    # ── Confidence level from cv ───────────────────────────────────
    df["confidence_level"] = df["cv"].apply(confidence_level)

    # ── Sort + save final priority table ──────────────────────────
    df = df.sort_values("final_priority_score", ascending=False).reset_index(drop=True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\nFinal priority table saved: {output_path}  ({len(df):,} rows)")

    # ── Patrol teams ───────────────────────────────────────────────
    teams_df = build_patrol_teams()
    os.makedirs(os.path.dirname(teams_path), exist_ok=True)
    teams_df.to_csv(teams_path, index=False)
    print(f"Patrol teams saved   : {teams_path}  ({len(teams_df)} teams)")

    # ── Greedy allocation ──────────────────────────────────────────
    assign_df, teams_final = greedy_allocate(df, teams_df, registry)
    os.makedirs(os.path.dirname(assignments_path), exist_ok=True)
    assign_df.to_csv(assignments_path, index=False)
    print(f"Team assignments saved: {assignments_path}  ({len(assign_df)} assignments)")

    # ── Summary report ─────────────────────────────────────────────
    tier_counts   = df["tier"].value_counts()
    n_red         = tier_counts.get("Red",   0)
    n_amber       = tier_counts.get("Amber", 0)
    n_green       = tier_counts.get("Green", 0)
    n_assigned    = len(assign_df)
    vg_in_red     = (
        (df["tier"] == "Red") & (df["volatility_class"] == "volatile_growing")
    ).sum()

    print("\n" + "=" * 60)
    print("FINAL PRIORITY SUMMARY")
    print("=" * 60)
    print(f"  Red zones    : {n_red:>4}  (top 20%,  buffer threshold: {red_thresh:.4f})")
    print(f"  Amber zones  : {n_amber:>4}  (next 30%, buffer threshold: {amber_thresh:.4f})")
    print(f"  Green zones  : {n_green:>4}  (bottom 50%)")
    print(f"  Teams assigned : {n_assigned} / {TOTAL_TEAMS}")
    print(f"  volatile_growing zones in Red tier : {vg_in_red}")

    print(f"\n  Confidence level distribution:")
    for lvl in ["High", "Medium", "Low"]:
        cnt = (df["confidence_level"] == lvl).sum()
        pct = cnt / len(df) * 100
        print(f"    {lvl:<6} (cv-based): {cnt:>4} zones  ({pct:.1f}%)")

    print(f"\n  Top 5 priority zones:")
    top5_cols = [
        "cluster_id", "time_band", "dominant_police_station",
        "buffered_forecast", "hotspot_score", "cii_score",
        "final_priority_score", "volatility_class", "tier",
    ]
    present = [c for c in top5_cols if c in df.columns]
    top5 = df[present].head(5)
    col_widths = {
        "cluster_id": 10, "time_band": 22, "dominant_police_station": 20,
        "buffered_forecast": 17, "hotspot_score": 12, "cii_score": 10,
        "final_priority_score": 20, "volatility_class": 18, "tier": 6,
    }
    header = "  " + "  ".join(f"{c:<{col_widths.get(c,12)}}" for c in present)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for _, row in top5.iterrows():
        line = "  " + "  ".join(
            f"{str(row[c]):<{col_widths.get(c,12)}}" for c in present
        )
        print(line)

    print("=" * 60)
    return df


# ==================================================================
# CLI ENTRY POINT
# ==================================================================

if __name__ == "__main__":
    config = load_config(os.path.join(PROJECT_ROOT, "configs", "config.yaml"))

    def rp(rel):
        return os.path.join(PROJECT_ROOT, rel)

    build_final_table(
        forecast_path    = rp("data/processed/global_forecast.csv"),
        volatility_path  = rp("data/processed/volatility_scores.csv"),
        cii_path         = rp(config["forecasting"]["cii_scores_path"]),
        registry_path    = rp(config["data"]["cluster_registry_path"]),
        output_path      = rp(config["forecasting"]["final_priority_table_path"]),
        teams_path       = rp("data/processed/patrol_teams.csv"),
        assignments_path = rp("data/processed/team_assignments.csv"),
        k                = float(config["forecasting"]["shrinkage_k"]),
    )
