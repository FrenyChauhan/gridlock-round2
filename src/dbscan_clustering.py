"""
Bengaluru Parking Violations — DBSCAN Spatial Clustering (v3)
=============================================================
Input : data/processed/featured_violations.csv
Output:
  - data/processed/clustered_violations.csv
  - data/processed/cluster_registry.csv
  - outputs/plots/kdistance_plot.png
  - outputs/plots/cluster_size_histogram.png
  - outputs/plots/cluster_map.html
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import silhouette_score
import folium
from src.utils import load_config, setup_logging

# ─────────────────────────────────────────────
# CONSTANTS & CONFIG
# ─────────────────────────────────────────────

CITY_CENTRE_LAT = 12.9716
CITY_CENTRE_LON = 77.5946

# Colour palette for clusters
COLOURS = [
    "#e63946", "#457b9d", "#2a9d8f", "#e9c46a", "#f4a261",
    "#264653", "#a8dadc", "#606c38", "#dda15e", "#bc6c25",
    "#8ecae6", "#219ebc", "#023047", "#ffb703", "#fb8500",
]


def dominant(series):
    return series.mode().iloc[0] if len(series) > 0 else None


def cluster_radius(group):
    clat = group["latitude"].mean()
    clon = group["longitude"].mean()
    dists = np.sqrt(
        (group["latitude"]  - clat) ** 2 +
        (group["longitude"] - clon) ** 2
    )
    return dists.mean()


def run_dbscan_clustering(
    input_path: str,
    clustered_path: str,
    registry_path: str,
    kdist_plot_path: str,
    hist_plot_path: str,
    cluster_map_path: str,
    eps: float,
    min_samples: int,
    min_cluster_size: int,
    logger=None
):
    """
    Executes the DBSCAN spatial clustering pipeline (v3) with a post-clustering size filter.
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

    log(f"Loading featured data from: {input_path}")
    if not os.path.exists(input_path):
        err = f"Featured dataset not found at {input_path}."
        log(err, "error")
        raise FileNotFoundError(err)

    df = pd.read_csv(input_path, low_memory=False)
    log(f"  Shape: {df.shape}")

    coords = df[["latitude", "longitude"]].values
    log(f"  Coordinate matrix: {coords.shape}")

    # ─────────────────────────────────────────────
    # 2. K-DISTANCE ELBOW PLOT
    # ─────────────────────────────────────────────
    log(f"\nComputing k-distance plot (k={min_samples})...")
    log("  This may take 1-2 minutes...")
    nbrs = NearestNeighbors(n_neighbors=min_samples, algorithm="ball_tree").fit(coords)
    distances, _ = nbrs.kneighbors(coords)
    k_distances  = np.sort(distances[:, -1])[::-1]

    os.makedirs(os.path.dirname(kdist_plot_path), exist_ok=True)
    plt.figure(figsize=(11, 5))
    plt.plot(k_distances, linewidth=1.5, color="#e63946")
    plt.axhline(y=eps, color="#457b9d", linestyle="--", linewidth=2,
                label=f"Selected eps = {eps}")
    plt.xlabel("Points sorted by distance (descending)", fontsize=12)
    plt.ylabel(f"Distance to {min_samples}th nearest neighbour", fontsize=12)
    plt.title(f"K-Distance Elbow Plot (k={min_samples})", fontsize=14)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(kdist_plot_path, dpi=150)
    plt.close()
    log(f"  Saved: {kdist_plot_path}")

    # ─────────────────────────────────────────────
    # 3. RUN DBSCAN
    # ─────────────────────────────────────────────
    log(f"\nRunning DBSCAN (eps={eps}, min_samples={min_samples})...")
    db = DBSCAN(
        eps=eps,
        min_samples=min_samples,
        algorithm="ball_tree",
        n_jobs=-1
    ).fit(coords)

    df["cluster_id"] = db.labels_

    n_clusters  = len(set(db.labels_)) - (1 if -1 in db.labels_ else 0)
    n_noise     = (db.labels_ == -1).sum()
    n_clustered = (db.labels_ != -1).sum()
    cluster_sizes = df[df["cluster_id"] != -1]["cluster_id"].value_counts()

    log(f"\n  Raw DBSCAN Results:")
    log(f"  Total points    : {len(df):,}")
    log(f"  Clusters found  : {n_clusters}")
    log(f"  Clustered points: {n_clustered:,} ({n_clustered/len(df)*100:.1f}%)")
    log(f"  Noise points    : {n_noise:,} ({n_noise/len(df)*100:.1f}%)")
    if not cluster_sizes.empty:
        log(f"  Largest cluster : {cluster_sizes.max():,} violations (Upparpet — genuine density)")
        log(f"  Smallest cluster: {cluster_sizes.min():,} violations")
        log(f"  Median cluster  : {cluster_sizes.median():.0f} violations")

    # ─────────────────────────────────────────────
    # 4. SILHOUETTE SCORE
    # ─────────────────────────────────────────────
    log("\nComputing silhouette score (10,000 point sample)...")
    df_cl = df[df["cluster_id"] != -1]
    coords_cl = coords[df_cl.index]

    if len(df_cl) > 10000:
        idx = np.random.choice(len(df_cl), 10000, replace=False)
        sil_coords = coords_cl[idx]
        sil_labels = df_cl.iloc[idx]["cluster_id"].values
    else:
        sil_coords = coords_cl
        sil_labels = df_cl["cluster_id"].values

    if len(set(sil_labels)) > 1:
        sil = silhouette_score(sil_coords, sil_labels)
        log(f"  Silhouette Score: {sil:.4f}")
        if sil > 0.5:
            log("  -> Strong clusters.")
        elif sil > 0.2:
            log("  -> Reasonable clusters. Acceptable for geographic data.")
        else:
            log("  -> Weak clusters.")
    else:
        log("  -> Only one cluster found.")

    # ─────────────────────────────────────────────
    # 5. BUILD CLUSTER REGISTRY (pre-filter)
    # ─────────────────────────────────────────────
    log("\nBuilding cluster registry...")
    df_clustered = df[df["cluster_id"] != -1].copy()

    registry = df_clustered.groupby("cluster_id").apply(
        lambda g: pd.Series({
            "centroid_lat"            : g["latitude"].mean(),
            "centroid_lon"            : g["longitude"].mean(),
            "radius_deg"              : cluster_radius(g),
            "radius_m"                : cluster_radius(g) * 111_000,
            "total_violations"        : len(g),
            "dominant_police_station" : dominant(g["police_station"]),
            "dominant_junction"       : dominant(g["junction_name"]),
            "dominant_time_band"      : dominant(g["time_band"]),
            "dominant_vehicle_type"   : dominant(g["vehicle_type"]),
            "pct_at_junction"         : g["is_junction"].mean() * 100,
            "pct_btp_junction"        : (g["junction_proxy"] == 1.0).mean() * 100,
            "mean_junction_proxy"     : g["junction_proxy"].mean(),
            "mean_severity_score"     : g["severity_score"].mean(),
            "mean_combined_severity"  : g["combined_severity_norm"].mean(),
            "mean_vehicle_weight"     : g["vehicle_weight"].mean(),
            "mean_vehicle_blockage"   : g["vehicle_blockage_norm"].mean(),
            "mean_record_risk_score"  : g["record_risk_score_norm"].mean(),
            "mean_cii_component"      : g["cii_component"].mean(),
            "pct_peak_junction"       : g["is_peak_junction"].mean() * 100,
            "pct_heavy_at_junction"   : g["heavy_at_junction"].mean() * 100,
            "mean_time_demand"        : g["time_demand_multiplier"].mean(),
        })
    ).reset_index()

    log(f"  Registry built (pre-filter): {len(registry)} clusters")

    # ─────────────────────────────────────────────
    # 6. FILTER TINY CLUSTERS
    # ─────────────────────────────────────────────
    log(f"\nFiltering clusters with < {min_cluster_size} violations...")
    before_count = len(registry)
    valid_clusters = registry[
        registry["total_violations"] >= min_cluster_size
    ]["cluster_id"].tolist()

    df["cluster_id"] = df["cluster_id"].where(
        df["cluster_id"].isin(valid_clusters), other=-1
    )

    registry = registry[
        registry["cluster_id"].isin(valid_clusters)
    ].reset_index(drop=True)

    after_count = len(registry)
    log(f"  Clusters before filter : {before_count}")
    log(f"  Clusters after filter  : {after_count}")
    log(f"  Tiny clusters removed  : {before_count - after_count}")

    n_noise_final     = (df["cluster_id"] == -1).sum()
    n_clustered_final = (df["cluster_id"] != -1).sum()
    log(f"  Final clustered points : {n_clustered_final:,} ({n_clustered_final/len(df)*100:.1f}%)")
    log(f"  Final noise points     : {n_noise_final:,} ({n_noise_final/len(df)*100:.1f}%)")

    registry = registry.sort_values("total_violations", ascending=False).reset_index(drop=True)

    log(f"\n  Top 10 clusters by violation count:")
    log(registry[[
        "cluster_id", "dominant_police_station", "total_violations",
        "centroid_lat", "centroid_lon", "dominant_junction"
    ]].head(10).to_string(index=False))

    # ─────────────────────────────────────────────
    # 7. CLUSTER SIZE HISTOGRAM
    # ─────────────────────────────────────────────
    final_sizes = registry["total_violations"]
    if not final_sizes.empty:
        os.makedirs(os.path.dirname(hist_plot_path), exist_ok=True)
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Left — full distribution
        axes[0].hist(final_sizes, bins=40, color="#457b9d", edgecolor="white", linewidth=0.5)
        axes[0].axvline(final_sizes.median(), color="#e63946", linestyle="--", linewidth=1.5,
                        label=f"Median = {final_sizes.median():.0f}")
        axes[0].set_xlabel("Cluster Size (violations)", fontsize=11)
        axes[0].set_ylabel("Number of Clusters", fontsize=11)
        axes[0].set_title(f"Cluster Size Distribution ({after_count} clusters)", fontsize=12)
        axes[0].legend(fontsize=10)
        axes[0].grid(True, alpha=0.3)

        # Right — exclude the top outlier to see small cluster spread
        p95 = final_sizes.quantile(0.95)
        axes[1].hist(final_sizes[final_sizes <= p95], bins=40, color="#2a9d8f", edgecolor="white", linewidth=0.5)
        axes[1].set_xlabel("Cluster Size (violations)", fontsize=11)
        axes[1].set_ylabel("Number of Clusters", fontsize=11)
        axes[1].set_title("Size Distribution (excl. top 5% outliers)", fontsize=12)
        axes[1].grid(True, alpha=0.3)

        plt.suptitle(f"DBSCAN Cluster Sizes — eps={eps}, min_samples={min_samples}", fontsize=13, y=1.02)
        plt.tight_layout()
        plt.savefig(hist_plot_path, dpi=150, bbox_inches="tight")
        plt.close()
        log(f"\nCluster size histogram saved: {hist_plot_path}")

    # ─────────────────────────────────────────────
    # 8. FOLIUM CLUSTER MAP
    # ─────────────────────────────────────────────
    log("\nBuilding cluster map...")
    os.makedirs(os.path.dirname(cluster_map_path), exist_ok=True)

    m = folium.Map(
        location=[CITY_CENTRE_LAT, CITY_CENTRE_LON],
        zoom_start=12,
        tiles="CartoDB positron"
    )

    for _, row in registry.iterrows():
        cid    = int(row["cluster_id"])
        colour = COLOURS[cid % len(COLOURS)]
        r = max(5, min(np.log1p(row["total_violations"]) * 2, 25))

        folium.CircleMarker(
            location=[row["centroid_lat"], row["centroid_lon"]],
            radius=r,
            color=colour,
            fill=True,
            fill_color=colour,
            fill_opacity=0.7,
            popup=folium.Popup(
                f"""
                <b>Cluster {cid}</b><br>
                Station   : {row['dominant_police_station']}<br>
                Junction  : {row['dominant_junction']}<br>
                Violations: {int(row['total_violations']):,}<br>
                Radius    : {row['radius_m']:.0f}m<br>
                Risk Score: {row['mean_record_risk_score']:.3f}<br>
                CII       : {row['mean_cii_component']:.3f}
                """,
                max_width=260
            ),
            tooltip=f"Cluster {cid} — {row['dominant_police_station']} ({int(row['total_violations']):,} violations)"
        ).add_to(m)

    if n_noise_final > 0:
        noise_df = df[df["cluster_id"] == -1].sample(
            min(3000, n_noise_final), random_state=42
        )
        for _, row in noise_df.iterrows():
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=1,
                color="#cccccc",
                fill=True,
                fill_opacity=0.3,
            ).add_to(m)

    m.save(cluster_map_path)
    log(f"  Cluster map saved: {cluster_map_path}")

    # ─────────────────────────────────────────────
    # 9. EXPORT
    # ─────────────────────────────────────────────
    df.to_csv(clustered_path, index=False)
    registry.to_csv(registry_path, index=False)
    log(f"\nClustered violations -> {clustered_path}")
    log(f"Cluster registry     -> {registry_path}")

    # ─────────────────────────────────────────────
    # 10. FINAL SUMMARY
    # ─────────────────────────────────────────────
    log("\n" + "="*55)
    log("DBSCAN CLUSTERING SUMMARY (v3)")
    log("="*55)
    log(f"  eps                  : {eps} (~{eps*111_000:.0f}m)")
    log(f"  min_samples          : {min_samples}")
    log(f"  min_cluster_size     : {min_cluster_size} (post-filter)")
    log(f"  Clusters (raw)       : {n_clusters}")
    log(f"  Clusters (filtered)  : {after_count}")
    log(f"  Clustered points     : {n_clustered_final:,} ({n_clustered_final/len(df)*100:.1f}%)")
    log(f"  Noise points         : {n_noise_final:,} ({n_noise_final/len(df)*100:.1f}%)")
    if not registry.empty:
        log(f"  Largest cluster      : {registry['total_violations'].max():,} (Upparpet — real density)")
        log(f"  Smallest cluster     : {registry['total_violations'].min():,}")
        log(f"  Median cluster size  : {registry['total_violations'].median():.0f}")
    log(f"\n  Outputs:")
    log(f"  -> {clustered_path}")
    log(f"  -> {registry_path}")
    log(f"  -> {kdist_plot_path}")
    log(f"  -> {hist_plot_path}")
    log(f"  -> {cluster_map_path}")

    return df, registry


if __name__ == "__main__":
    logger = setup_logging()
    config = load_config()

    input_path = config["data"]["featured_violation_path"]
    clustered_path = config["data"]["clustered_violation_path"]
    registry_path = config["data"]["cluster_registry_path"]
    kdist_plot_path = config["data"]["kdist_plot_path"]
    hist_plot_path = config["data"]["hist_plot_path"]
    cluster_map_path = config["data"]["cluster_map_path"]

    eps = float(config["clustering"]["eps"])
    min_samples = int(config["clustering"]["min_samples"])
    min_cluster_size = int(config["clustering"]["min_cluster_size"])

    run_dbscan_clustering(
        input_path,
        clustered_path,
        registry_path,
        kdist_plot_path,
        hist_plot_path,
        cluster_map_path,
        eps,
        min_samples,
        min_cluster_size,
        logger
    )
