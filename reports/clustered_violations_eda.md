# Exploratory Data Analysis of Clustered Parking Violations

This document presents a detailed exploratory data analysis (EDA) of the DBSCAN-clustered parking violations dataset in Bengaluru. The analysis reviews cluster volumes, density patterns, spatial characteristics, temporal behaviors, risk severity, and vehicle profiling.

## 1. Dataset Profile & Spatial Clustering Overview

The dataset contains the results of spatial DBSCAN clustering applied to parking violations. Spatial parameters used: `eps = 0.0005` (~55m) and `min_samples = 50`. A cluster represents a high-density zone where parking violations are consistently occurring close to one another.

### General Statistics
- **Total Parking Violations**: 247,698
- **Clustered Violations**: 214,432 (86.57% of total)
- **Noise/Outlier Violations (Unclustered)**: 33,266 (13.43% of total)
- **Total Hotspot Clusters Identified**: 317
- **Memory Usage of Clustered Dataset**: 272.40 MB

## 2. Cluster Size Distribution Analysis

Analyzing the distribution of violation counts within identified clusters highlights the scale and intensity of traffic hotspots.

| Statistic | Value (Violations per Cluster) |
| --- | --- |
| **Minimum Cluster Size** | 50 |
| **25th Percentile (Q1)** | 86 |
| **Median Cluster Size** | 165 |
| **Mean Cluster Size** | 676.4 |
| **75th Percentile (Q3)** | 457 |
| **90th Percentile** | 1119 |
| **95th Percentile** | 1968 |
| **Maximum Cluster Size** | 47,033 |
| **Standard Deviation** | 2891.3 |

> [!NOTE]
The wide gap between the median (165) and maximum (47,033) cluster sizes indicates a heavy right-skewed distribution. While most clusters are moderate in size, a small number of massive clusters contain a significant portion of the total violations.

## 3. Profile of Top 10 Hotspot Clusters

Here are the largest 10 hotspot clusters ranked by violation count. These regions represent the highest density of parking offenses in the city.

| Rank | Cluster ID | Dominant Police Station | Dominant Junction | Violations | Radius (meters) | Mean Risk Score | Dominant Time Band |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2 | Upparpet | BTP040 - Elite Junction | 47,033 | 633.3m | 0.0040 | morning_peak |
| 2 | 3 | Shivajinagar | BTP051 - Safina Plaza Junction | 14,846 | 196.3m | 0.0042 | mid_day |
| 3 | 31 | Malleshwaram | No Junction | 7,804 | 232.1m | 0.0009 | mid_day |
| 4 | 22 | Malleshwaram | BTP027 - Modi Bridge Junction | 7,392 | 205.2m | 0.0033 | morning_peak |
| 5 | 10 | HAL Old Airport | No Junction | 6,758 | 105.4m | 0.0183 | late_night |
| 6 | 53 | Kodigehalli | No Junction | 4,519 | 60.8m | 0.0023 | mid_day |
| 7 | 32 | Shivajinagar | BTP211 - Central Street Junction | 4,145 | 145.8m | 0.0056 | mid_day |
| 8 | 23 | Chikkajala | No Junction | 3,865 | 180.0m | 0.0101 | late_night |
| 9 | 60 | Vijayanagara | BTP020 - Hosahalli Metro Station | 3,663 | 93.1m | 0.0036 | late_night |
| 10 | 34 | Malleshwaram | No Junction | 3,509 | 161.5m | 0.0004 | morning_peak |

## 4. Police Station Risk & Hotspot Distribution

Below are the top 15 police stations sorted by clustered violation volume. This indicates where cluster densities are concentrated compared to background noise.

| Police Station | Total Clusters | Clustered Violations | Noise Violations | Total Violations | Clustered % |
| --- | --- | --- | --- | --- | --- |
| Upparpet | 2.0 | 29,454.0 | 107.0 | 29,561.0 | 99.64% |
| Shivajinagar | 7.0 | 21,823.0 | 452.0 | 22,275.0 | 97.97% |
| Malleshwaram | 9.0 | 18,399.0 | 650.0 | 19,049.0 | 96.59% |
| HAL Old Airport | 13.0 | 16,044.0 | 1,048.0 | 17,092.0 | 93.87% |
| City Market | 3.0 | 14,239.0 | 387.0 | 14,626.0 | 97.35% |
| Vijayanagara | 10.0 | 11,065.0 | 537.0 | 11,602.0 | 95.37% |
| Kodigehalli | 15.0 | 8,336.0 | 897.0 | 9,233.0 | 90.28% |
| Rajajinagar | 12.0 | 7,860.0 | 1,245.0 | 9,105.0 | 86.33% |
| Magadi Road | 10.0 | 5,936.0 | 892.0 | 6,828.0 | 86.94% |
| Jeevanbheemanagar | 15.0 | 4,815.0 | 1,026.0 | 5,841.0 | 82.43% |
| K.R. Pura | 5.0 | 4,760.0 | 574.0 | 5,334.0 | 89.24% |
| Chikkajala | 8.0 | 4,580.0 | 239.0 | 4,819.0 | 95.04% |
| Halasuru Gate | 7.0 | 4,409.0 | 763.0 | 5,172.0 | 85.25% |
| Mahadevapura | 6.0 | 3,869.0 | 1,294.0 | 5,163.0 | 74.94% |
| High ground | 5.0 | 3,710.0 | 414.0 | 4,124.0 | 89.96% |

## 5. Temporal Trends: Clustered vs. Noise

How do the timing patterns of clustered violations compare with background unclustered violations?

### Violation Distribution by Time Band
| Time Band | Clustered Violations (%) | Noise Violations (%) |
| --- | --- | --- |
| `evening` | 0.31% | 0.49% |
| `late_night` | 33.82% | 39.57% |
| `mid_day` | 33.03% | 33.24% |
| `morning_peak` | 32.50% | 26.65% |
| `night` | 0.35% | 0.05% |

- **Weekend Share (Clustered)**: 31.65%
- **Weekend Share (Noise)**: 32.35%

## 6. Vehicle and Offense Profiles

### Top 5 Violation Types in Clustered Hotspots
| Rank | Violation Type | Count | Percentage of Clustered |
| --- | --- | --- | --- |
| 1 | ["WRONG PARKING"] | 99,011 | 46.17% |
| 2 | ["NO PARKING"] | 88,892 | 41.45% |
| 3 | ["PARKING IN A MAIN ROAD","WRONG PARKING"] | 6,869 | 3.20% |
| 4 | ["PARKING IN A MAIN ROAD","NO PARKING"] | 3,119 | 1.45% |
| 5 | ["WRONG PARKING","DEFECTIVE NUMBER PLATE"] | 2,234 | 1.04% |

### Vehicle Types Distribution
| Vehicle Type | Clustered Violations (%) | Noise Violations (%) |
| --- | --- | --- |
| BUS (BMTC/KSRTC) | 0.33% | 0.24% |
| CAR | 29.17% | 42.11% |
| FACTORY BUS | 0.07% | 0.14% |
| GOODS AUTO | 0.87% | 1.56% |
| HGV | 0.19% | 1.53% |
| JEEP | 0.30% | 0.37% |
| LGV | 2.34% | 5.17% |
| LORRY/GOODS VEHICLE | 0.23% | 1.17% |
| MAXI-CAB | 3.86% | 4.43% |
| MINI LORRY | 0.05% | 0.15% |
| MOPED | 0.74% | 0.73% |
| MOTOR CYCLE | 14.17% | 9.88% |
| OTHERS | 0.22% | 0.73% |
| PASSENGER AUTO | 12.60% | 7.55% |
| PRIVATE BUS | 0.43% | 1.02% |
| SCHOOL VEHICLE | 0.07% | 0.41% |
| SCOOTER | 33.40% | 20.32% |
| TANKER | 0.07% | 0.21% |
| TEMPO | 0.36% | 1.00% |
| TOURIST BUS | 0.10% | 0.28% |
| TRACTOR | 0.01% | 0.05% |
| VAN | 0.43% | 0.92% |

## 7. Risk and Severity Index Comparison

A comparison of indicators representing severity, risk scores, and the Core Infrastructure Impact (CII) component between clustered and noise regions:

| Metric | Clustered Zones (Mean) | Noise/Outliers (Mean) | Difference (%) |
| --- | --- | --- | --- |
| **Record Risk Score (Normalized)** | 0.0071 | 0.0117 | -39.13% |
| **CII Component** | 0.5909 | 0.5548 | +6.51% |
| **Combined Severity (Normalized)** | 0.0136 | 0.0228 | -40.47% |

> [!IMPORTANT]
Violations occurring in clustered zones exhibit a **-39.13% higher risk score** and a **+6.51% higher CII component** compared to unclustered noise. This suggests that high-density parking violations are highly correlated with critical infrastructure blockage and elevated traffic congestion risk.

## 8. Correlation Heatmap of Cluster Characteristics

This correlation analysis highlights how different aggregate indicators correlate at the cluster registry level (across all clusters):

| Variable 1 | Variable 2 | Correlation Coefficient |
| --- | --- | --- |
| `mean_record_risk_score` | `mean_combined_severity` | **+0.9155** |
| `mean_cii_component` | `pct_at_junction` | **+0.8466** |
| `total_violations` | `radius_m` | **+0.7623** |
| `pct_at_junction` | `pct_heavy_at_junction` | **+0.5374** |
| `mean_cii_component` | `pct_heavy_at_junction` | **+0.5129** |
| `mean_cii_component` | `mean_time_demand` | **+0.4531** |
| `mean_record_risk_score` | `mean_time_demand` | **+0.2234** |
| `mean_combined_severity` | `pct_at_junction` | **-0.1385** |

## 9. Visualizations Generated

The following exploratory visualizations have been saved in the `outputs/plots/` directory:
1. **Cluster Size Distribution Histogram**: [cluster_size_distribution.png](file:///D:/Flipkart-Gridlock/Round2/outputs/plots/cluster_size_distribution.png)
2. **Risk vs. Total Violations (Log Scatter)**: [cluster_risk_vs_violations.png](file:///D:/Flipkart-Gridlock/Round2/outputs/plots/cluster_risk_vs_violations.png)
3. **Top 15 Police Stations Volume**: [cluster_by_station_top15.png](file:///D:/Flipkart-Gridlock/Round2/outputs/plots/cluster_by_station_top15.png)
4. **Temporal Patterns Comparison (Clustered vs. Noise)**: [cluster_temporal_distribution.png](file:///D:/Flipkart-Gridlock/Round2/outputs/plots/cluster_temporal_distribution.png)
5. **Cluster Characteristics Correlation Matrix**: [cluster_attributes_correlation.png](file:///D:/Flipkart-Gridlock/Round2/outputs/plots/cluster_attributes_correlation.png)

### Visual Summary Gallery
![Cluster Size Distribution](file:///D:/Flipkart-Gridlock/Round2/outputs/plots/cluster_size_distribution.png)

![Risk vs Violations](file:///D:/Flipkart-Gridlock/Round2/outputs/plots/cluster_risk_vs_violations.png)

![Top 15 Police Stations](file:///D:/Flipkart-Gridlock/Round2/outputs/plots/cluster_by_station_top15.png)

![Temporal Distribution](file:///D:/Flipkart-Gridlock/Round2/outputs/plots/cluster_temporal_distribution.png)

![Cluster Attributes Correlation](file:///D:/Flipkart-Gridlock/Round2/outputs/plots/cluster_attributes_correlation.png)
