# Exploratory Data Analysis & Dataset Summary

This document summarizes the core statistics and distributions extracted from the police violation dataset.

## 1. Dataset Profile Overview
- **Total Rows**: 298,450
- **Total Columns**: 24
- **Memory Usage**: 320.50 MB
- **Temporal Range**: 2023-11-09 19:11:46+00:00 to 2024-04-08 17:30:46+00:00

### Column Details and Missing Rates
| Column | Data Type | Null Count | Null % |
| --- | --- | --- | --- |
| `id` | object | 0 | 0.00% |
| `latitude` | float64 | 0 | 0.00% |
| `longitude` | float64 | 0 | 0.00% |
| `location` | object | 3,041 | 1.02% |
| `vehicle_number` | object | 0 | 0.00% |
| `vehicle_type` | object | 0 | 0.00% |
| `description` | float64 | 298,450 | 100.00% |
| `violation_type` | object | 0 | 0.00% |
| `offence_code` | object | 0 | 0.00% |
| `created_datetime` | object | 0 | 0.00% |
| `closed_datetime` | float64 | 298,450 | 100.00% |
| `modified_datetime` | object | 0 | 0.00% |
| `device_id` | object | 0 | 0.00% |
| `created_by_id` | object | 5 | 0.00% |
| `center_code` | float64 | 11,260 | 3.77% |
| `police_station` | object | 5 | 0.00% |
| `data_sent_to_scita` | bool | 0 | 0.00% |
| `junction_name` | object | 5 | 0.00% |
| `action_taken_timestamp` | float64 | 298,450 | 100.00% |
| `data_sent_to_scita_timestamp` | object | 256,289 | 85.87% |
| `updated_vehicle_number` | object | 125,254 | 41.97% |
| `updated_vehicle_type` | object | 125,254 | 41.97% |
| `validation_status` | object | 125,254 | 41.97% |
| `validation_timestamp` | object | 125,254 | 41.97% |

## 2. Key Categorical Distributions

### Top 10 Violation Types
| Violation Type | Count | Percentage |
| --- | --- | --- |
| ["WRONG PARKING"] | 138,764 | 46.49% |
| ["NO PARKING"] | 119,576 | 40.07% |
| ["PARKING IN A MAIN ROAD","WRONG PARKING"] | 9,472 | 3.17% |
| ["PARKING IN A MAIN ROAD","NO PARKING"] | 4,818 | 1.61% |
| ["WRONG PARKING","DEFECTIVE NUMBER PLATE"] | 3,317 | 1.11% |
| ["NO PARKING","PARKING IN A MAIN ROAD"] | 2,449 | 0.82% |
| ["NO PARKING","DEFECTIVE NUMBER PLATE"] | 2,380 | 0.80% |
| ["WRONG PARKING","PARKING IN A MAIN ROAD"] | 1,955 | 0.66% |
| ["PARKING ON FOOTPATH","WRONG PARKING"] | 1,190 | 0.40% |
| ["NO PARKING","WRONG PARKING"] | 891 | 0.30% |

### Top 10 Police Stations
| Police Station | Count | Percentage |
| --- | --- | --- |
| Upparpet | 34,468 | 11.55% |
| Shivajinagar | 28,044 | 9.40% |
| Malleshwaram | 22,200 | 7.44% |
| HAL Old Airport | 20,819 | 6.98% |
| City Market | 17,646 | 5.91% |
| Vijayanagara | 14,652 | 4.91% |
| Rajajinagar | 10,998 | 3.69% |
| Kodigehalli | 10,916 | 3.66% |
| Magadi Road | 8,558 | 2.87% |
| Jeevanbheemanagar | 6,736 | 2.26% |

### Top 10 Vehicle Types
| Vehicle Type | Count | Percentage |
| --- | --- | --- |
| SCOOTER | 94,856 | 31.78% |
| CAR | 88,870 | 29.78% |
| MOTOR CYCLE | 40,811 | 13.67% |
| PASSENGER AUTO | 37,813 | 12.67% |
| MAXI-CAB | 11,372 | 3.81% |
| LGV | 8,255 | 2.77% |
| GOODS AUTO | 2,934 | 0.98% |
| MOPED | 2,199 | 0.74% |
| PRIVATE BUS | 1,633 | 0.55% |
| VAN | 1,466 | 0.49% |

### Validation Status
| Status | Count | Percentage |
| --- | --- | --- |
| nan | 125,254 | 41.97% |
| approved | 115,400 | 38.67% |
| rejected | 49,754 | 16.67% |
| created1 | 7,044 | 2.36% |
| processing | 678 | 0.23% |
| duplicate | 320 | 0.11% |

### Top 10 Junctions
| Junction | Count | Percentage |
| --- | --- | --- |
| No Junction | 147,880 | 49.55% |
| BTP051 - Safina Plaza Junction | 15,449 | 5.18% |
| BTP082 - KR Market Junction | 11,538 | 3.87% |
| BTP040 - Elite Junction | 10,718 | 3.59% |
| BTP044 - Sagar Theatre Junction | 10,549 | 3.53% |
| BTP211 - Central Street Junction | 5,388 | 1.81% |
| BTP058 - Subbanna Junction | 5,189 | 1.74% |
| BTP027 - Modi Bridge Junction | 4,584 | 1.54% |
| BTP020 - Hosahalli Metro Station | 4,101 | 1.37% |
| BTP057 - Anand Rao Junction | 3,935 | 1.32% |

## 3. Geographical Insights
Coordinates bounding box (excluding noise outside Bengaluru area):
- **Latitude Range**: [12.802667, 13.293684] (Mean: 12.980802)
- **Longitude Range**: [77.442553, 77.771735] (Mean: 77.600512)
- **Total Rows with Invalid Coordinates**: 0 (0.00%)

## 4. Temporal Analysis: Hourly Violation Activity
| Hour of Day | Violations | Percentage |
| --- | --- | --- |
| 0:00 | 21,760 | 7.29% |
| 1:00 | 17,155 | 5.75% |
| 2:00 | 24,770 | 8.30% |
| 3:00 | 25,707 | 8.61% |
| 4:00 | 29,102 | 9.75% |
| 5:00 | 34,085 | 11.42% |
| 6:00 | 26,890 | 9.01% |
| 7:00 | 14,608 | 4.89% |
| 8:00 | 8,556 | 2.87% |
| 9:00 | 3,145 | 1.05% |
| 10:00 | 518 | 0.17% |
| 11:00 | 577 | 0.19% |
| 12:00 | 219 | 0.07% |
| 13:00 | 56 | 0.02% |
| 14:00 | 16 | 0.01% |
| 15:00 | 66 | 0.02% |
| 16:00 | 416 | 0.14% |
| 17:00 | 818 | 0.27% |
| 18:00 | 1,971 | 0.66% |
| 19:00 | 10,713 | 3.59% |
| 20:00 | 11,834 | 3.97% |
| 21:00 | 19,763 | 6.62% |
| 22:00 | 22,839 | 7.65% |
| 23:00 | 22,861 | 7.66% |
