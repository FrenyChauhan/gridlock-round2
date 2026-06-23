"""
Heatmap Data Export
======================
Input:  final_priority_table.csv  (from final_priority.py)
        cluster_registry.csv      (from dbscan_clustering.py)
        team_assignments.csv      (from final_priority.py greedy allocator)
Output: heatmap_data.json -- one key per time_band, each a list of zone
        points ready to feed directly into the heatmap widget.

Filters to Red + Amber tiers only.
New fields added per zone object:
  volatility_class, trend_slope, patrol_buffer_multiplier,
  confidence_level, assigned_team_id, assignment_status,
  buffered_forecast, time_band
"""

import os
import json
import pandas as pd

# ------------------------------------------------------------------
# PATH SETUP (needed when imported as a module from run_full_pipeline)
# ------------------------------------------------------------------
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils import load_config

CENTROID_LAT_COL = "centroid_lat"
CENTROID_LON_COL = "centroid_lon"
TIERS_TO_INCLUDE = ["Red", "Amber"]


def export_heatmap_data(
    priority_table_path   : str,
    cluster_registry_path : str,
    output_path           : str,
    assignments_path      : str = None,
    tiers                 : list = None,
) -> dict:
    tiers = tiers or TIERS_TO_INCLUDE

    priority = pd.read_csv(priority_table_path)
    registry = pd.read_csv(cluster_registry_path)

    # ------------------------------------------------------------------
    # Merge centroid coordinates
    # ------------------------------------------------------------------
    missing_cols = [
        c for c in [CENTROID_LAT_COL, CENTROID_LON_COL]
        if c not in registry.columns
    ]
    if missing_cols:
        raise KeyError(
            f"cluster_registry.csv is missing expected columns {missing_cols}. "
            f"Available: {list(registry.columns)}."
        )

    # centroid_lat/lon may already be in priority table (joined from registry
    # inside final_priority.py). Only merge from registry if they are absent.
    if CENTROID_LAT_COL not in priority.columns or CENTROID_LON_COL not in priority.columns:
        priority = priority.merge(
            registry[["cluster_id", CENTROID_LAT_COL, CENTROID_LON_COL]],
            on="cluster_id",
            how="left",
        )

    missing_coords = priority[CENTROID_LAT_COL].isna().sum()
    if missing_coords:
        print(
            f"WARNING: {missing_coords} rows have no matching centroid — "
            "dropped from heatmap."
        )
    priority = priority.dropna(subset=[CENTROID_LAT_COL, CENTROID_LON_COL])

    # ------------------------------------------------------------------
    # Load team assignments for team_id lookup
    # ------------------------------------------------------------------
    team_lookup = {}   # (cluster_id, time_band) -> {team_id, status}
    if assignments_path and os.path.exists(assignments_path):
        assign_df = pd.read_csv(assignments_path)
        for _, arow in assign_df.iterrows():
            key = (int(arow["cluster_id"]), str(arow["time_band"]))
            team_lookup[key] = {
                "team_id" : str(arow["team_id"]),
                "status"  : str(arow["status"]),
            }

    # ------------------------------------------------------------------
    # Filter to requested tiers
    # ------------------------------------------------------------------
    filtered = priority[priority["tier"].isin(tiers)].copy()

    # ------------------------------------------------------------------
    # Build band-keyed JSON structure
    # ------------------------------------------------------------------
    bands = {}
    for band in sorted(filtered["time_band"].unique()):
        sub = filtered[filtered["time_band"] == band].sort_values(
            "final_priority_score", ascending=False
        )
        points = []
        for _, row in sub.iterrows():
            cid  = int(row["cluster_id"])
            tband = str(row["time_band"])
            team_info = team_lookup.get((cid, tband), {})

            # volume: prefer buffered_forecast, fall back to predicted_violations
            if "buffered_forecast" in row and pd.notna(row["buffered_forecast"]):
                volume = round(float(row["buffered_forecast"]), 1)
            elif "predicted_violations" in row and pd.notna(row["predicted_violations"]):
                volume = round(float(row["predicted_violations"]), 1)
            else:
                volume = None

            points.append({
                # ── Existing fields ────────────────────────────────────
                "lat"    : round(float(row[CENTROID_LAT_COL]), 5),
                "lon"    : round(float(row[CENTROID_LON_COL]), 5),
                "station": str(row.get("dominant_police_station", "Unknown")),
                "score"  : round(float(row["final_priority_score"]), 4),
                "tier"   : str(row["tier"]),
                "volume" : volume,
                "cii"    : round(float(row["cii_score"]), 3),
                "cluster": cid,
                # ── New fields ─────────────────────────────────────────
                "time_band"                 : tband,
                "volatility_class"          : str(row.get("volatility_class",     "")),
                "trend_slope"               : (
                    round(float(row["trend_slope"]), 4)
                    if "trend_slope" in row and pd.notna(row["trend_slope"])
                    else None
                ),
                "patrol_buffer_multiplier"  : (
                    round(float(row["patrol_buffer_multiplier"]), 2)
                    if "patrol_buffer_multiplier" in row and pd.notna(row["patrol_buffer_multiplier"])
                    else 1.0
                ),
                "confidence_level"          : str(row.get("confidence_level",     "Low")),
                "buffered_forecast"         : volume,
                "assigned_team_id"          : team_info.get("team_id",  None),
                "assignment_status"         : team_info.get("status",   "unassigned"),
            })
        bands[band] = points

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(bands, f, indent=2)

    total_zones = sum(len(v) for v in bands.values())
    print("Heatmap data export complete.")
    for band, pts in bands.items():
        assigned = sum(1 for p in pts if p["assigned_team_id"] is not None)
        print(f"  {band}: {len(pts)} zones  ({assigned} team-assigned)")
    print(f"  Total zones in JSON : {total_zones}")
    print(f"  Saved to: {output_path}")

    return bands


if __name__ == "__main__":
    config = load_config(os.path.join(PROJECT_ROOT, "configs", "config.yaml"))

    def rp(rel):
        return os.path.join(PROJECT_ROOT, rel)

    export_heatmap_data(
        priority_table_path   = rp(config["forecasting"]["final_priority_table_path"]),
        cluster_registry_path = rp(config["data"]["cluster_registry_path"]),
        output_path           = rp(config["forecasting"]["heatmap_data_path"]),
        assignments_path      = rp("data/processed/team_assignments.csv"),
    )
