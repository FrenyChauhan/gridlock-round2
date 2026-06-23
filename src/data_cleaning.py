"""
Bengaluru Parking Violations — Data Cleaning & Preprocessing
=============================================================
Steps:
  0. Load raw CSV
  1. Drop fully-null columns
  2. Filter validation_status
  3. Fix datetime (UTC → IST) and extract temporal features
  4. Engineer time_band, day_type
  5. Engineer severity_score from violation_type
  6. Engineer vehicle_weight from vehicle_type
  7. Engineer is_junction from junction_name
  8. Coordinate validation (latitude/longitude boundaries)
  9. Fill minor nulls
  10. Final column selection & export
"""

import os
import pandas as pd
import numpy as np
from src.utils import load_config, setup_logging

# ─────────────────────────────────────────────
# MAPS & HELPER FUNCTIONS
# ─────────────────────────────────────────────

# Time demand multiplier — used in hotspot scoring formula
TIME_DEMAND_MAP = {
    "morning_transition": 1.0,
    "evening"           : 0.8,
    "evening_night"     : 0.6,
    "early_morning"     : 0.3,
    "dead_zone"         : 0.2,
}

VEHICLE_WEIGHT_MAP = {
    "MAXI-CAB"      : 1.0,
    "LGV"           : 1.0,
    "PRIVATE BUS"   : 1.0,
    "VAN"           : 0.7,
    "CAR"           : 0.7,
    "GOODS AUTO"    : 0.6,
    "PASSENGER AUTO": 0.5,
    "MOTOR CYCLE"   : 0.2,
    "SCOOTER"       : 0.2,
    "MOPED"         : 0.2,
}

# Bengaluru bounding box (from EDA)
LAT_MIN, LAT_MAX = 12.80, 13.30
LON_MIN, LON_MAX = 77.44, 77.78

KEEP_COLS = [
    # Identifiers
    "id",
    # Geography
    "latitude", "longitude", "location",
    # Vehicle
    "vehicle_number", "vehicle_type", "vehicle_weight",
    # Violation
    "violation_type", "offence_code", "severity_score",
    # Junction
    "junction_name", "is_junction", "junction_multiplier",
    # Station
    "police_station",
    # Temporal
    "created_datetime_ist", "hour", "day_of_week", "month", "date",
    "time_band", "time_demand_multiplier", "day_type",
    # Validation
    "validation_status", "sample_weight",
]


def assign_time_band(hour):
    """
    Map IST hour to traffic time band.
    early_morning    : 0–6   (low activity, late night / pre-dawn)
    morning_transition: 7–9  (commute ramp-up)
    dead_zone        : 10–15 (mid-day lull)
    evening          : 16–18 (peak evening traffic)
    evening_night    : 19–23 (post-peak winding down)
    """
    if 0 <= hour <= 6:
        return "early_morning"
    elif 7 <= hour <= 9:
        return "morning_transition"
    elif 10 <= hour <= 15:
        return "dead_zone"
    elif 16 <= hour <= 18:
        return "evening"
    elif 19 <= hour <= 23:
        return "evening_night"
    else:
        return "early_morning"        # fallback (should never trigger)


def compute_severity(vtype_str):
    """
    Score each record by the worst violation it contains.
    Main road parking = most severe (blocks traffic lanes)
    Wrong/No parking  = medium
    Footpath          = lower (pedestrian impact, not carriageway)
    Defective plate   = lowest (admin, no blockage)
    """
    if pd.isna(vtype_str):
        return 0.3  # default for unknown

    v = str(vtype_str).upper()

    if "PARKING IN A MAIN ROAD" in v:
        return 1.0
    elif "PARKING ON FOOTPATH" in v:
        return 0.5
    elif "NO PARKING" in v or "WRONG PARKING" in v:
        return 0.6
    elif "DEFECTIVE NUMBER PLATE" in v:
        return 0.3
    else:
        return 0.3


def get_vehicle_weight(vtype):
    if pd.isna(vtype):
        return 0.5  # default mid-weight
    return VEHICLE_WEIGHT_MAP.get(str(vtype).strip().upper(), 0.5)


def clean_data(raw_path: str, output_path: str, logger=None):
    """
    Executes the full data cleaning pipeline on raw parking violations CSV.
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

    log(f"Loading raw data from: {raw_path}")
    if not os.path.exists(raw_path):
        err = f"Raw dataset not found at {raw_path}."
        log(err, "error")
        raise FileNotFoundError(err)

    df = pd.read_csv(raw_path, low_memory=False)
    log(f"  Raw shape: {df.shape}")

    # 1. Drop fully-null columns
    fully_null = [col for col in df.columns if df[col].isna().all()]
    if fully_null:
        log(f"Dropping fully-null columns: {fully_null}")
        df.drop(columns=fully_null, inplace=True)

    # 2. Filter validation_status — drop only 'rejected'; assign sample_weight
    before = len(df)
    df = df[
        df["validation_status"].isna() |
        df["validation_status"].isin(["approved", "created1"])
    ].copy()
    after = len(df)
    log(f"Validation filter: {before} -> {after} rows "
        f"(removed {before - after} rejected rows)")

    # Assign sample_weight based on validation_status reliability
    def assign_sample_weight(status):
        if pd.isna(status):
            return 0.7   # NaN treated as implicitly approved but lower confidence
        elif status == "approved":
            return 1.0   # highest confidence
        elif status == "created1":
            return 0.8   # submitted but not fully validated
        return 0.7       # fallback (should not occur after filter above)

    df["sample_weight"] = df["validation_status"].apply(assign_sample_weight)
    log(f"Sample weight distribution:\n{df['sample_weight'].value_counts().to_string()}")

    # 3. Datetime processing (UTC -> IST)
    log("Converting created_datetime UTC -> IST...")
    df["created_datetime"] = pd.to_datetime(df["created_datetime"], utc=True, format="mixed")
    df["created_datetime_ist"] = df["created_datetime"].dt.tz_convert("Asia/Kolkata")

    # Extract temporal features
    df["hour"]        = df["created_datetime_ist"].dt.hour
    df["day_of_week"] = df["created_datetime_ist"].dt.dayofweek
    df["month"]       = df["created_datetime_ist"].dt.month
    df["date"]        = df["created_datetime_ist"].dt.date

    # 4. Time band & day type
    df["time_band"] = df["hour"].apply(assign_time_band)
    df["time_demand_multiplier"] = df["time_band"].map(TIME_DEMAND_MAP)
    df["day_type"] = df["day_of_week"].apply(
        lambda x: "weekend" if x >= 5 else "weekday"
    )

    # 5. Severity score
    df["severity_score"] = df["violation_type"].apply(compute_severity)

    # 6. Vehicle weight
    df["vehicle_weight"] = df["vehicle_type"].apply(get_vehicle_weight)

    # 7. Junction features
    df["is_junction"] = df["junction_name"].apply(
        lambda x: False if pd.isna(x) or str(x).strip() == "No Junction" else True
    )
    df["junction_multiplier"] = df["junction_name"].apply(
        lambda x: 1.4 if (not pd.isna(x) and str(x).strip().startswith("BTP")) else 1.0
    )

    # 8. Coordinate validation
    invalid_coords = (
        (df["latitude"]  < LAT_MIN) | (df["latitude"]  > LAT_MAX) |
        (df["longitude"] < LON_MIN) | (df["longitude"] > LON_MAX)
    )
    log(f"Invalid coordinates (outside Bengaluru bbox): {invalid_coords.sum()}")
    df = df[~invalid_coords].copy()

    # 9. Fill minor nulls
    df["police_station"] = df["police_station"].fillna("Unknown")
    df["junction_name"]  = df["junction_name"].fillna("No Junction")

    # 10. Columns selection & Export
    df_clean = df[KEEP_COLS].copy()

    # Save to directory
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_clean.to_csv(output_path, index=False)
    log(f"Cleaned data saved to: {output_path}")

    # Summary log
    log("\n" + "="*50)
    log("CLEANED DATASET SUMMARY")
    log("="*50)
    log(f"  Shape          : {df_clean.shape}")
    log(f"  Date range     : {df_clean['created_datetime_ist'].min()} -> {df_clean['created_datetime_ist'].max()}")
    log(f"  Null counts    :")
    nulls = df_clean.isnull().sum()
    log(nulls[nulls > 0].to_string() if nulls.any() else "    None")
    log(f"\n  Time bands     :\n{df_clean['time_band'].value_counts().to_string()}")
    log(f"\n  Day types      :\n{df_clean['day_type'].value_counts().to_string()}")
    log(f"\n  Top stations   :\n{df_clean['police_station'].value_counts().head(5).to_string()}")

    return df_clean


if __name__ == "__main__":
    # Setup logger
    logger = setup_logging()
    
    # Load config
    config = load_config()
    
    raw_path = config["data"]["raw_violation_path"]
    output_path = config["data"]["cleaned_violation_path"]
    
    clean_data(raw_path, output_path, logger)
