import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def run_clustered_eda():
    clustered_path = os.path.join("data", "processed", "clustered_violations.csv")
    registry_path = os.path.join("data", "processed", "cluster_registry.csv")
    reports_dir = "reports"
    plots_dir = os.path.join("outputs", "plots")
    
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)
    
    print(f"Loading clustered violations from {clustered_path}...")
    if not os.path.exists(clustered_path):
        raise FileNotFoundError(f"Clustered violations file not found at {clustered_path}.")
    
    print(f"Loading cluster registry from {registry_path}...")
    if not os.path.exists(registry_path):
        raise FileNotFoundError(f"Cluster registry file not found at {registry_path}.")
        
    df = pd.read_csv(clustered_path, low_memory=False)
    reg = pd.read_csv(registry_path)
    
    n_rows, n_cols = df.shape
    print(f"Successfully loaded clustered violations dataset. Shape: {n_rows} rows, {n_cols} columns.")
    print(f"Successfully loaded cluster registry. Shape: {reg.shape[0]} clusters.")
    
    # Set plot style
    sns.set_theme(style="whitegrid")
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
    
    # ── 1. General Profiles ──────────────────────────────────────────────────
    mem_usage = df.memory_usage(deep=True).sum() / (1024 * 1024)
    null_counts = df.isnull().sum()
    null_percentages = (null_counts / n_rows) * 100
    
    # ── 2. Cluster Overview ──────────────────────────────────────────────────
    n_noise = (df["cluster_id"] == -1).sum()
    n_clustered = (df["cluster_id"] != -1).sum()
    n_clusters = reg["cluster_id"].nunique()
    
    pct_noise = (n_noise / n_rows) * 100
    pct_clustered = (n_clustered / n_rows) * 100
    
    # Cluster sizes stats
    cluster_sizes = df[df["cluster_id"] != -1]["cluster_id"].value_counts()
    size_mean = cluster_sizes.mean()
    size_median = cluster_sizes.median()
    size_min = cluster_sizes.min()
    size_max = cluster_sizes.max()
    size_std = cluster_sizes.std()
    
    p25 = cluster_sizes.quantile(0.25)
    p75 = cluster_sizes.quantile(0.75)
    p90 = cluster_sizes.quantile(0.90)
    p95 = cluster_sizes.quantile(0.95)
    
    # ── 3. Top Clusters ──────────────────────────────────────────────────────
    top_10_clusters = reg.sort_values(by="total_violations", ascending=False).head(10)
    
    # ── 4. Spatial Analysis (Police Stations & Junctions) ───────────────────
    # Clusters and Clustered violations per station
    station_cluster_count = reg["dominant_police_station"].value_counts()
    station_violation_count = df[df["cluster_id"] != -1].groupby("police_station").size().sort_values(ascending=False)
    station_noise_count = df[df["cluster_id"] == -1].groupby("police_station").size().sort_values(ascending=False)
    
    station_stats = pd.DataFrame({
        "Clusters": station_cluster_count,
        "Clustered Violations": station_violation_count,
        "Noise Violations": station_noise_count
    }).fillna(0).astype(int)
    station_stats["Total Violations"] = station_stats["Clustered Violations"] + station_stats["Noise Violations"]
    station_stats["Clustered %"] = (station_stats["Clustered Violations"] / station_stats["Total Violations"]) * 100
    station_stats = station_stats.sort_values(by="Clustered Violations", ascending=False)
    
    # ── 5. Temporal Patterns (Clustered vs. Noise) ─────────────────────────
    # Time Band
    time_band_clustered = df[df["cluster_id"] != -1]["time_band"].value_counts(normalize=True) * 100
    time_band_noise = df[df["cluster_id"] == -1]["time_band"].value_counts(normalize=True) * 100
    time_band_df = pd.DataFrame({
        "Clustered %": time_band_clustered,
        "Noise %": time_band_noise
    }).fillna(0)
    
    # Weekend vs. Weekday
    weekend_clustered = df[df["cluster_id"] != -1]["is_weekend"].mean() * 100
    weekend_noise = df[df["cluster_id"] == -1]["is_weekend"].mean() * 100
    
    # Hour of day
    hour_clustered = df[df["cluster_id"] != -1]["hour"].value_counts(normalize=True).sort_index() * 100
    hour_noise = df[df["cluster_id"] == -1]["hour"].value_counts(normalize=True).sort_index() * 100
    
    # ── 6. Violation & Vehicle Type Analysis ────────────────────────────────
    violation_clustered = df[df["cluster_id"] != -1]["violation_type"].value_counts().head(10)
    violation_noise = df[df["cluster_id"] == -1]["violation_type"].value_counts().head(10)
    
    vehicle_clustered = df[df["cluster_id"] != -1]["vehicle_type"].value_counts(normalize=True) * 100
    vehicle_noise = df[df["cluster_id"] == -1]["vehicle_type"].value_counts(normalize=True) * 100
    vehicle_df = pd.DataFrame({
        "Clustered %": vehicle_clustered,
        "Noise %": vehicle_noise
    }).fillna(0)
    
    # ── 7. Risk & Severity Indices ──────────────────────────────────────────
    mean_risk_clustered = df[df["cluster_id"] != -1]["record_risk_score_norm"].mean()
    mean_risk_noise = df[df["cluster_id"] == -1]["record_risk_score_norm"].mean()
    
    mean_cii_clustered = df[df["cluster_id"] != -1]["cii_component"].mean()
    mean_cii_noise = df[df["cluster_id"] == -1]["cii_component"].mean()
    
    mean_sev_clustered = df[df["cluster_id"] != -1]["combined_severity_norm"].mean()
    mean_sev_noise = df[df["cluster_id"] == -1]["combined_severity_norm"].mean()
    
    # ── 8. Correlation Analysis (Registry level) ──────────────────────────
    corr_cols = [
        "total_violations", "radius_m", "mean_record_risk_score", 
        "mean_cii_component", "mean_combined_severity", "pct_at_junction", 
        "pct_heavy_at_junction", "mean_time_demand"
    ]
    registry_corr = reg[corr_cols].corr()
    
    # ── 9. Generate Plots ────────────────────────────────────────────────────
    print("Generating EDA plots...")
    
    # Plot 1: Cluster Size Distribution (Histogram and KDE)
    plt.figure(figsize=(10, 5))
    sns.histplot(cluster_sizes, bins=30, kde=True, color="#457b9d", edgecolor="white")
    plt.axvline(size_median, color="#e63946", linestyle="--", linewidth=2, label=f"Median: {size_median:.0f}")
    plt.axvline(size_mean, color="#2a9d8f", linestyle="-.", linewidth=2, label=f"Mean: {size_mean:.1f}")
    plt.title("Distribution of Cluster Sizes (Number of Violations per Cluster)", fontsize=14, pad=15)
    plt.xlabel("Cluster Size (Violations)", fontsize=12)
    plt.ylabel("Number of Clusters", fontsize=12)
    plt.legend(fontsize=11)
    plt.tight_layout()
    plot_size_path = os.path.join(plots_dir, "cluster_size_distribution.png")
    plt.savefig(plot_size_path, dpi=150)
    plt.close()
    
    # Plot 2: Cluster Risk vs. Total Violations
    plt.figure(figsize=(11, 6))
    # Log scale for x-axis due to massive variation in cluster sizes
    scatter = sns.scatterplot(
        data=reg,
        x="total_violations",
        y="mean_record_risk_score",
        size="radius_m",
        sizes=(20, 400),
        hue="dominant_time_band",
        palette="viridis",
        alpha=0.7,
        edgecolor="black",
        linewidth=0.5
    )
    plt.xscale("log")
    plt.title("DBSCAN Clusters: Mean Risk Score vs. Total Violations (Log Scale)", fontsize=14, pad=15)
    plt.xlabel("Total Violations in Cluster (Log Scale)", fontsize=12)
    plt.ylabel("Mean Record Risk Score (Normalized)", fontsize=12)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', title="Time Band & Radius (m)")
    plt.tight_layout()
    plot_risk_path = os.path.join(plots_dir, "cluster_risk_vs_violations.png")
    plt.savefig(plot_risk_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    # Plot 3: Top 15 Police Stations by Clustered Violations
    plt.figure(figsize=(12, 6))
    top_stations = station_stats.head(15).reset_index()
    if "police_station" in top_stations.columns:
        top_stations = top_stations.rename(columns={"police_station": "Station"})
    elif "index" in top_stations.columns:
        top_stations = top_stations.rename(columns={"index": "Station"})
    else:
        top_stations.rename(columns={top_stations.columns[0]: "Station"}, inplace=True)

    sns.barplot(
        data=top_stations,
        x="Clustered Violations",
        y="Station",
        hue="Station",
        legend=False,
        palette="Reds_r",
        edgecolor="grey"
    )
    plt.title("Top 15 Police Stations by Volume of Clustered Violations", fontsize=14, pad=15)
    plt.xlabel("Number of Clustered Violations", fontsize=12)
    plt.ylabel("Police Station", fontsize=12)
    plt.tight_layout()
    plot_station_path = os.path.join(plots_dir, "cluster_by_station_top15.png")
    plt.savefig(plot_station_path, dpi=150)
    plt.close()
    
    # Plot 4: Temporal Band Distribution (Clustered vs. Noise)
    time_band_reset = time_band_df.reset_index()
    if "time_band" in time_band_reset.columns:
        time_band_reset = time_band_reset.rename(columns={"time_band": "TimeBand"})
    elif "index" in time_band_reset.columns:
        time_band_reset = time_band_reset.rename(columns={"index": "TimeBand"})
    else:
        time_band_reset.rename(columns={time_band_reset.columns[0]: "TimeBand"}, inplace=True)

    time_band_melted = time_band_reset.melt(id_vars="TimeBand", var_name="Type", value_name="Percentage")
    plt.figure(figsize=(10, 5))
    sns.barplot(
        data=time_band_melted,
        x="TimeBand",
        y="Percentage",
        hue="Type",
        palette="Set2"
    )
    plt.title("Temporal Distribution of Violations: Clustered vs. Noise (Outliers)", fontsize=14, pad=15)
    plt.xlabel("Time Band", fontsize=12)
    plt.ylabel("Percentage of Total Violations (%)", fontsize=12)
    plt.legend(fontsize=11)
    plt.tight_layout()
    plot_temp_path = os.path.join(plots_dir, "cluster_temporal_distribution.png")
    plt.savefig(plot_temp_path, dpi=150)
    plt.close()
    
    # Plot 5: Correlation Heatmap of Cluster Characteristics
    plt.figure(figsize=(9, 7))
    sns.heatmap(
        registry_corr,
        annot=True,
        cmap="coolwarm",
        fmt=".2f",
        linewidths=0.5,
        vmin=-1,
        vmax=1,
        square=True
    )
    plt.title("Correlation Matrix of Aggregated Cluster Attributes", fontsize=14, pad=15)
    plt.tight_layout()
    plot_corr_path = os.path.join(plots_dir, "cluster_attributes_correlation.png")
    plt.savefig(plot_corr_path, dpi=150)
    plt.close()
    
    # ── 10. Generate Markdown Report ──────────────────────────────────────────
    md_report_path = os.path.join(reports_dir, "clustered_violations_eda.md")
    print(f"Generating markdown summary document at {md_report_path}...")
    
    with open(md_report_path, "w", encoding="utf-8") as f:
        f.write("# Exploratory Data Analysis of Clustered Parking Violations\n\n")
        f.write("This document presents a detailed exploratory data analysis (EDA) of the DBSCAN-clustered parking violations dataset in Bengaluru. ")
        f.write("The analysis reviews cluster volumes, density patterns, spatial characteristics, temporal behaviors, risk severity, and vehicle profiling.\n\n")
        
        # 1. Dataset Profile Overview
        f.write("## 1. Dataset Profile & Spatial Clustering Overview\n\n")
        f.write("The dataset contains the results of spatial DBSCAN clustering applied to parking violations. Spatial parameters used: `eps = 0.0005` (~55m) and `min_samples = 50`. ")
        f.write("A cluster represents a high-density zone where parking violations are consistently occurring close to one another.\n\n")
        
        f.write("### General Statistics\n")
        f.write(f"- **Total Parking Violations**: {n_rows:,}\n")
        f.write(f"- **Clustered Violations**: {n_clustered:,} ({pct_clustered:.2f}% of total)\n")
        f.write(f"- **Noise/Outlier Violations (Unclustered)**: {n_noise:,} ({pct_noise:.2f}% of total)\n")
        f.write(f"- **Total Hotspot Clusters Identified**: {n_clusters}\n")
        f.write(f"- **Memory Usage of Clustered Dataset**: {mem_usage:.2f} MB\n\n")
        
        # 2. Cluster Size Statistics
        f.write("## 2. Cluster Size Distribution Analysis\n\n")
        f.write("Analyzing the distribution of violation counts within identified clusters highlights the scale and intensity of traffic hotspots.\n\n")
        f.write("| Statistic | Value (Violations per Cluster) |\n")
        f.write("| --- | --- |\n")
        f.write(f"| **Minimum Cluster Size** | {size_min:,} |\n")
        f.write(f"| **25th Percentile (Q1)** | {p25:.0f} |\n")
        f.write(f"| **Median Cluster Size** | {size_median:.0f} |\n")
        f.write(f"| **Mean Cluster Size** | {size_mean:.1f} |\n")
        f.write(f"| **75th Percentile (Q3)** | {p75:.0f} |\n")
        f.write(f"| **90th Percentile** | {p90:.0f} |\n")
        f.write(f"| **95th Percentile** | {p95:.0f} |\n")
        f.write(f"| **Maximum Cluster Size** | {size_max:,} |\n")
        f.write(f"| **Standard Deviation** | {size_std:.1f} |\n\n")
        
        f.write("> [!NOTE]\n")
        f.write(f"The wide gap between the median ({size_median:.0f}) and maximum ({size_max:,}) cluster sizes indicates a heavy right-skewed distribution. ")
        f.write("While most clusters are moderate in size, a small number of massive clusters contain a significant portion of the total violations.\n\n")
        
        # 3. Top 10 Clusters
        f.write("## 3. Profile of Top 10 Hotspot Clusters\n\n")
        f.write("Here are the largest 10 hotspot clusters ranked by violation count. These regions represent the highest density of parking offenses in the city.\n\n")
        f.write("| Rank | Cluster ID | Dominant Police Station | Dominant Junction | Violations | Radius (meters) | Mean Risk Score | Dominant Time Band |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for idx, row in top_10_clusters.reset_index().iterrows():
            f.write(f"| {idx+1} | {int(row['cluster_id'])} | {row['dominant_police_station']} | {row['dominant_junction']} | {int(row['total_violations']):,} | {row['radius_m']:.1f}m | {row['mean_record_risk_score']:.4f} | {row['dominant_time_band']} |\n")
        f.write("\n")
        
        # 4. Spatial Analysis
        f.write("## 4. Police Station Risk & Hotspot Distribution\n\n")
        f.write("Below are the top 15 police stations sorted by clustered violation volume. This indicates where cluster densities are concentrated compared to background noise.\n\n")
        f.write("| Police Station | Total Clusters | Clustered Violations | Noise Violations | Total Violations | Clustered % |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        for idx, row in station_stats.head(15).iterrows():
            f.write(f"| {idx} | {row['Clusters']:,} | {row['Clustered Violations']:,} | {row['Noise Violations']:,} | {row['Total Violations']:,} | {row['Clustered %']:.2f}% |\n")
        f.write("\n")
        
        # 5. Temporal Patterns
        f.write("## 5. Temporal Trends: Clustered vs. Noise\n\n")
        f.write("How do the timing patterns of clustered violations compare with background unclustered violations?\n\n")
        f.write("### Violation Distribution by Time Band\n")
        f.write("| Time Band | Clustered Violations (%) | Noise Violations (%) |\n")
        f.write("| --- | --- | --- |\n")
        for idx, row in time_band_df.iterrows():
            f.write(f"| `{idx}` | {row['Clustered %']:.2f}% | {row['Noise %']:.2f}% |\n")
        f.write("\n")
        
        f.write(f"- **Weekend Share (Clustered)**: {weekend_clustered:.2f}%\n")
        f.write(f"- **Weekend Share (Noise)**: {weekend_noise:.2f}%\n\n")
        
        # 6. Violation & Vehicle Profiling
        f.write("## 6. Vehicle and Offense Profiles\n\n")
        
        f.write("### Top 5 Violation Types in Clustered Hotspots\n")
        f.write("| Rank | Violation Type | Count | Percentage of Clustered |\n")
        f.write("| --- | --- | --- | --- |\n")
        for idx, (val, count) in enumerate(violation_clustered.head(5).items()):
            f.write(f"| {idx+1} | {val} | {count:,} | {(count/n_clustered)*100:.2f}% |\n")
        f.write("\n")
        
        f.write("### Vehicle Types Distribution\n")
        f.write("| Vehicle Type | Clustered Violations (%) | Noise Violations (%) |\n")
        f.write("| --- | --- | --- |\n")
        for idx, row in vehicle_df.iterrows():
            f.write(f"| {idx} | {row['Clustered %']:.2f}% | {row['Noise %']:.2f}% |\n")
        f.write("\n")
        
        # 7. Risk & Severity Index
        f.write("## 7. Risk and Severity Index Comparison\n\n")
        f.write("A comparison of indicators representing severity, risk scores, and the Core Infrastructure Impact (CII) component between clustered and noise regions:\n\n")
        f.write("| Metric | Clustered Zones (Mean) | Noise/Outliers (Mean) | Difference (%) |\n")
        f.write("| --- | --- | --- | --- |\n")
        diff_risk = ((mean_risk_clustered - mean_risk_noise) / mean_risk_noise) * 100
        diff_cii = ((mean_cii_clustered - mean_cii_noise) / mean_cii_noise) * 100 if mean_cii_noise > 0 else 0
        diff_sev = ((mean_sev_clustered - mean_sev_noise) / mean_sev_noise) * 100
        f.write(f"| **Record Risk Score (Normalized)** | {mean_risk_clustered:.4f} | {mean_risk_noise:.4f} | {diff_risk:+.2f}% |\n")
        f.write(f"| **CII Component** | {mean_cii_clustered:.4f} | {mean_cii_noise:.4f} | {diff_cii:+.2f}% |\n")
        f.write(f"| **Combined Severity (Normalized)** | {mean_sev_clustered:.4f} | {mean_sev_noise:.4f} | {diff_sev:+.2f}% |\n\n")
        
        f.write("> [!IMPORTANT]\n")
        f.write(f"Violations occurring in clustered zones exhibit a **{diff_risk:+.2f}% higher risk score** and a **{diff_cii:+.2f}% higher CII component** compared to unclustered noise. ")
        f.write("This suggests that high-density parking violations are highly correlated with critical infrastructure blockage and elevated traffic congestion risk.\n\n")
        
        # 8. Correlation Analysis
        f.write("## 8. Correlation Heatmap of Cluster Characteristics\n\n")
        f.write("This correlation analysis highlights how different aggregate indicators correlate at the cluster registry level (across all clusters):\n\n")
        f.write("| Variable 1 | Variable 2 | Correlation Coefficient |\n")
        f.write("| --- | --- | --- |\n")
        
        # List top correlations
        corr_pairs = []
        for i in range(len(corr_cols)):
            for j in range(i+1, len(corr_cols)):
                col1 = corr_cols[i]
                col2 = corr_cols[j]
                val = registry_corr.loc[col1, col2]
                corr_pairs.append((col1, col2, val))
        corr_pairs = sorted(corr_pairs, key=lambda x: abs(x[2]), reverse=True)
        
        for col1, col2, val in corr_pairs[:8]:
            f.write(f"| `{col1}` | `{col2}` | **{val:+.4f}** |\n")
        f.write("\n")
        
        # Reference generated plots
        f.write("## 9. Visualizations Generated\n\n")
        f.write("The following exploratory visualizations have been saved in the `outputs/plots/` directory:\n")
        f.write(f"1. **Cluster Size Distribution Histogram**: [cluster_size_distribution.png](file:///{os.path.abspath(plot_size_path).replace(chr(92), '/')})\n")
        f.write(f"2. **Risk vs. Total Violations (Log Scatter)**: [cluster_risk_vs_violations.png](file:///{os.path.abspath(plot_risk_path).replace(chr(92), '/')})\n")
        f.write(f"3. **Top 15 Police Stations Volume**: [cluster_by_station_top15.png](file:///{os.path.abspath(plot_station_path).replace(chr(92), '/')})\n")
        f.write(f"4. **Temporal Patterns Comparison (Clustered vs. Noise)**: [cluster_temporal_distribution.png](file:///{os.path.abspath(plot_temp_path).replace(chr(92), '/')})\n")
        f.write(f"5. **Cluster Characteristics Correlation Matrix**: [cluster_attributes_correlation.png](file:///{os.path.abspath(plot_corr_path).replace(chr(92), '/')})\n\n")
        
        f.write("### Visual Summary Gallery\n")
        # Embedding the images for display inside the IDE
        f.write(f"![Cluster Size Distribution](file:///{os.path.abspath(plot_size_path).replace(chr(92), '/')})\n\n")
        f.write(f"![Risk vs Violations](file:///{os.path.abspath(plot_risk_path).replace(chr(92), '/')})\n\n")
        f.write(f"![Top 15 Police Stations](file:///{os.path.abspath(plot_station_path).replace(chr(92), '/')})\n\n")
        f.write(f"![Temporal Distribution](file:///{os.path.abspath(plot_temp_path).replace(chr(92), '/')})\n\n")
        f.write(f"![Cluster Attributes Correlation](file:///{os.path.abspath(plot_corr_path).replace(chr(92), '/')})\n")

    print(f"Markdown EDA report successfully generated at {md_report_path}")

if __name__ == "__main__":
    run_clustered_eda()
