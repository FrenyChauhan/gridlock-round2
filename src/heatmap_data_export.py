"""
Heatmap Data Export
======================
Input:  final_priority_table.csv (from final_priority.py)
        cluster_registry.csv (from dbscan_clustering.py)
Output: heatmap_data.json -- one key per time_band, each a list of zone
        points ready to feed directly into the heatmap widget.

Filters to Red + Amber tiers only.
"""

import os
import json
import pandas as pd
from src.utils import load_config

CENTROID_LAT_COL = "centroid_lat"
CENTROID_LON_COL = "centroid_lon"
TIERS_TO_INCLUDE = ["Red", "Amber"]


def export_heatmap_data(
    priority_table_path: str,
    cluster_registry_path: str,
    output_path: str,
    tiers: list = None,
) -> dict:
    tiers = tiers or TIERS_TO_INCLUDE

    priority = pd.read_csv(priority_table_path)
    registry = pd.read_csv(cluster_registry_path)

    missing_cols = [c for c in [CENTROID_LAT_COL, CENTROID_LON_COL] if c not in registry.columns]
    if missing_cols:
        raise KeyError(
            f"cluster_registry.csv is missing expected columns {missing_cols}. "
            f"Available columns: {list(registry.columns)}. "
            f"Update CENTROID_LAT_COL / CENTROID_LON_COL at the top of this script "
            f"to match your actual column names."
        )

    merged = priority.merge(
        registry[["cluster_id", CENTROID_LAT_COL, CENTROID_LON_COL]],
        on="cluster_id",
        how="left",
    )

    missing_coords = merged[CENTROID_LAT_COL].isna().sum()
    if missing_coords:
        print(
            f"WARNING: {missing_coords} rows have no matching centroid in "
            f"cluster_registry.csv (cluster_id not found). These rows will "
            f"be dropped from the heatmap."
        )
    merged = merged.dropna(subset=[CENTROID_LAT_COL, CENTROID_LON_COL])

    filtered = merged[merged["tier"].isin(tiers)].copy()

    bands = {}
    for band in sorted(filtered["time_band"].unique()):
        sub = filtered[filtered["time_band"] == band].sort_values(
            "final_priority_score", ascending=False
        )
        points = []
        for _, row in sub.iterrows():
            points.append({
                "lat": round(float(row[CENTROID_LAT_COL]), 5),
                "lon": round(float(row[CENTROID_LON_COL]), 5),
                "station": str(row.get("dominant_police_station", "Unknown")),
                "score": round(float(row["final_priority_score"]), 4),
                "tier": str(row["tier"]),
                "volume": round(float(row["predicted_violation_count"]), 1),
                "cii": round(float(row["cii_score"]), 3),
                "cluster": int(row["cluster_id"]),
            })
        bands[band] = points

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(bands, f)

    print(f"Heatmap data export complete.")
    for band, points in bands.items():
        print(f"  {band}: {len(points)} zones ({tiers})")
    print(f"  Saved to: {output_path}")

    return bands


if __name__ == "__main__":
    config = load_config()
    priority_table_path = config["forecasting"]["final_priority_table_path"]
    cluster_registry_path = config["data"]["cluster_registry_path"]
    output_path = config["forecasting"]["heatmap_data_path"]
    
    export_heatmap_data(priority_table_path, cluster_registry_path, output_path)
