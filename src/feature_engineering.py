"""
Bengaluru Parking Violations — Preprocessing & Feature Engineering
==================================================================
Input : data/processed/cleaned_violations.csv
Output: data/processed/featured_violations.csv

Feature Groups Built:
  A. Temporal features       — cyclical encoding of hour, day, month
  B. Violation severity      — already in cleaned data, normalised here
  C. Vehicle blockage        — already in cleaned data, normalised here
  D. Junction features       — extended with proxy congestion weight
  E. Spatial features        — coordinate normalisation for DBSCAN
  F. Composite risk features — interaction terms for scoring pipeline
  G. Encoding                — label encode categoricals for modelling
"""

import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from src.utils import load_config, setup_logging

# ─────────────────────────────────────────────
# MAPS & HELPER FUNCTIONS
# ─────────────────────────────────────────────

CITY_CENTRE_LAT = 12.9716
CITY_CENTRE_LON = 77.5946

FEATURE_GROUPS = {
    "Identifiers"          : ["id"],
    "Geography (raw)"      : ["latitude", "longitude", "location"],
    "Geography (features)" : ["lat_norm", "lon_norm", "dist_from_centre", "dist_from_centre_norm"],
    "Temporal (raw)"       : ["hour", "day_of_week", "month", "date", "created_datetime_ist"],
    "Temporal (features)"  : ["hour_sin", "hour_cos", "dow_sin", "dow_cos",
                               "month_sin", "month_cos", "is_weekend", "is_morning_peak",
                               "is_early_morning", "is_month_end"],
    "Time band"            : ["time_band", "time_band_enc", "day_type", "day_type_enc",
                               "time_demand_multiplier"],
    "Violation"            : ["violation_type", "offence_code", "severity_score",
                               "violation_count_in_record", "combined_severity",
                               "combined_severity_norm",
                               "violation_type_count", "primary_violation",
                               "primary_violation_severity"],
    "Vehicle"              : ["vehicle_type", "vehicle_weight", "vehicle_blockage_norm",
                               "blockage_category", "blockage_cat_enc", "vehicle_category"],
    "Junction"             : ["junction_name", "is_junction", "junction_multiplier",
                               "junction_proxy", "btp_code"],
    "Police station"       : ["police_station", "police_station_enc"],
    "Composite risk"       : ["record_risk_score", "record_risk_score_norm",
                               "cii_component", "is_peak_junction", "heavy_at_junction"],
    "Validation"           : ["validation_status"],
}


def count_violations_in_record(vtype_str):
    """Count how many distinct violations appear in one record string."""
    if pd.isna(vtype_str):
        return 1
    # Each violation is separated by a comma inside the JSON-like string
    return max(1, str(vtype_str).count(",") + 1)


def blockage_category(weight):
    if weight >= 0.9:
        return "high"
    elif weight >= 0.6:
        return "medium"
    else:
        return "low"


def extract_btp_code(jname):
    if pd.isna(jname):
        return None
    jname = str(jname).strip()
    if jname.startswith("BTP"):
        try:
            return int(jname[3:6])
        except:
            return None
    return None


# ─────────────────────────────────────────────
# NEW HELPER MAPS & FUNCTIONS (Section H features)
# ─────────────────────────────────────────────

PRIMARY_VIOLATION_SEVERITY_MAP = {
    "PARKING IN A MAIN ROAD": 1.0,
    "WRONG PARKING"         : 0.7,
    "NO PARKING"            : 0.6,
    "PARKING ON FOOTPATH"   : 0.5,
}

VEHICLE_CATEGORY_MAP = {
    # heavy
    "PRIVATE BUS"           : "heavy",
    "BUS (BMTC/KSRTC)"      : "heavy",
    "HGV"                   : "heavy",
    "LORRY/GOODS VEHICLE"   : "heavy",
    "TEMPO"                 : "heavy",
    # medium
    "CAR"                   : "medium",
    "MAXI-CAB"              : "medium",
    "LGV"                   : "medium",
    "VAN"                   : "medium",
    "GOODS AUTO"            : "medium",
    "JEEP"                  : "medium",
    # light
    "SCOOTER"               : "light",
    "MOTOR CYCLE"           : "light",
    "MOPED"                 : "light",
    "PASSENGER AUTO"        : "light",
}


def parse_offence_codes(offence_str):
    """
    Parse the offence_code JSON-like array string and return a list of
    individual violation strings.
    Examples:
      '["WRONG PARKING"]'        -> ["WRONG PARKING"]
      '["NO PARKING","FOOTPATH"]' -> ["NO PARKING", "FOOTPATH"]
      'NO PARKING'               -> ["NO PARKING"]   (plain string fallback)
    """
    import ast, json
    if pd.isna(offence_str):
        return []
    s = str(offence_str).strip()
    # Try JSON / Python literal first
    if s.startswith("["):
        try:
            parsed = json.loads(s)
            return [str(v).strip() for v in parsed if v]
        except (json.JSONDecodeError, ValueError):
            pass
        try:
            parsed = ast.literal_eval(s)
            return [str(v).strip() for v in parsed if v]
        except Exception:
            pass
    # Plain comma-separated fallback
    return [v.strip() for v in s.split(",") if v.strip()]


def get_violation_type_count(offence_str):
    """Number of distinct violations in the offence_code field."""
    codes = parse_offence_codes(offence_str)
    return max(1, len(codes))


def get_primary_violation(offence_str):
    """First violation string from the offence_code field."""
    codes = parse_offence_codes(offence_str)
    return codes[0].upper() if codes else "UNKNOWN"


def get_primary_violation_severity(offence_str):
    """Severity score for the primary (first) violation."""
    primary = get_primary_violation(offence_str)
    for key, score in PRIMARY_VIOLATION_SEVERITY_MAP.items():
        if key in primary:
            return score
    return 0.4   # default


def get_vehicle_category(vtype):
    """Map vehicle_type to heavy / medium / light."""
    if pd.isna(vtype):
        return "medium"   # default
    return VEHICLE_CATEGORY_MAP.get(str(vtype).strip().upper(), "medium")


def run_feature_engineering(input_path: str, output_path: str, logger=None):
    """
    Load cleaned violations data and engineer features for downstream modelling.
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

    log(f"Loading cleaned data from: {input_path}")
    if not os.path.exists(input_path):
        err = f"Cleaned dataset not found at {input_path}."
        log(err, "error")
        raise FileNotFoundError(err)

    df = pd.read_csv(input_path, low_memory=False)
    df["created_datetime_ist"] = pd.to_datetime(df["created_datetime_ist"], utc=True, format="mixed")
    log(f"  Shape: {df.shape}")

    # ═══════════════════════════════════════════════════════════════
    # A. TEMPORAL FEATURES — CYCLICAL ENCODING
    # ═══════════════════════════════════════════════════════════════
    log("\n[A] Building cyclical temporal features...")
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["is_morning_peak"] = (df["time_band"] == "morning_transition").astype(int)

    # ═══════════════════════════════════════════════════════════════
    # B. VIOLATION SEVERITY — NORMALISE & EXTEND
    # ═══════════════════════════════════════════════════════════════
    log("\n[B] Extending violation severity features...")
    df["violation_count_in_record"] = df["violation_type"].apply(count_violations_in_record)
    df["combined_severity"] = df["severity_score"] * df["violation_count_in_record"]
    scaler = MinMaxScaler()
    df["combined_severity_norm"] = scaler.fit_transform(df[["combined_severity"]])

    # ═══════════════════════════════════════════════════════════════
    # C. VEHICLE BLOCKAGE — NORMALISE & EXTEND
    # ═══════════════════════════════════════════════════════════════
    log("\n[C] Extending vehicle blockage features...")
    df["blockage_category"] = df["vehicle_weight"].apply(blockage_category)
    df["vehicle_blockage_norm"] = df["vehicle_weight"]

    # ═══════════════════════════════════════════════════════════════
    # D. JUNCTION FEATURES — EXTENDED
    # ═══════════════════════════════════════════════════════════════
    log("\n[D] Extending junction features...")
    df["junction_proxy"] = df["junction_name"].apply(
        lambda x: 1.0 if (not pd.isna(x) and str(x).strip().startswith("BTP")) else 0.5
    )
    df["btp_code"] = df["junction_name"].apply(extract_btp_code)

    # ═══════════════════════════════════════════════════════════════
    # E. SPATIAL FEATURES
    # ═══════════════════════════════════════════════════════════════
    log("\n[E] Building spatial features...")
    df["lat_norm"] = scaler.fit_transform(df[["latitude"]])
    df["lon_norm"] = scaler.fit_transform(df[["longitude"]])
    df["dist_from_centre"] = np.sqrt(
        (df["latitude"]  - CITY_CENTRE_LAT) ** 2 +
        (df["longitude"] - CITY_CENTRE_LON) ** 2
    )
    df["dist_from_centre_norm"] = scaler.fit_transform(df[["dist_from_centre"]])

    # ═══════════════════════════════════════════════════════════════
    # F. COMPOSITE RISK FEATURES
    # ═══════════════════════════════════════════════════════════════
    log("\n[F] Building composite risk features...")
    df["record_risk_score"] = (
        df["combined_severity_norm"]
        * df["time_demand_multiplier"]
        * df["junction_multiplier"]
    )
    df["record_risk_score_norm"] = scaler.fit_transform(df[["record_risk_score"]])

    df["cii_component"] = (
        (df["junction_proxy"]        * 0.4) +
        (df["vehicle_blockage_norm"] * 0.3) +
        (df["time_demand_multiplier"]* 0.3)
    )

    df["is_peak_junction"] = (
        (df["is_junction"] == True) &
        (df["time_band"] == "morning_peak")
    ).astype(int)

    df["heavy_at_junction"] = (
        (df["blockage_category"] == "high") &
        (df["is_junction"] == True)
    ).astype(int)

    # ═══════════════════════════════════════════════════════════════
    # G. CATEGORICAL ENCODING
    # ═══════════════════════════════════════════════════════════════
    log("\n[G] Encoding categorical features...")
    le = LabelEncoder()
    df["time_band_enc"] = le.fit_transform(df["time_band"])
    df["day_type_enc"] = le.fit_transform(df["day_type"])
    df["police_station_enc"] = le.fit_transform(df["police_station"].astype(str))
    df["blockage_cat_enc"] = le.fit_transform(df["blockage_category"])

    # ═══════════════════════════════════════════════════════════════
    # H. NEW EXTENDED FEATURES
    # ═══════════════════════════════════════════════════════════════
    log("\n[H] Building new extended features...")

    # H1. is_early_morning — binary flag for early_morning time band
    df["is_early_morning"] = (df["time_band"] == "early_morning").astype(int)

    # H2. is_weekend — binary flag (Saturday=5, Sunday=6)
    #     Already computed in section A from day_of_week; kept consistent.

    # H3. is_month_end — binary flag, day of month >= 25
    df["is_month_end"] = (
        df["created_datetime_ist"].dt.day >= 25
    ).astype(int)

    # H4. violation_type_count — number of violations in offence_code
    df["violation_type_count"] = df["offence_code"].apply(get_violation_type_count)

    # H5. primary_violation — first violation string from offence_code
    df["primary_violation"] = df["offence_code"].apply(get_primary_violation)

    # H6. primary_violation_severity — severity score for primary violation
    df["primary_violation_severity"] = df["offence_code"].apply(get_primary_violation_severity)

    # H7. vehicle_category — heavy / medium / light from vehicle_type
    df["vehicle_category"] = df["vehicle_type"].apply(get_vehicle_category)

    log(f"  is_early_morning counts   : {df['is_early_morning'].sum():,}")
    log(f"  is_month_end counts       : {df['is_month_end'].sum():,}")
    log(f"  violation_type_count dist :\n{df['violation_type_count'].value_counts().head().to_string()}")
    log(f"  primary_violation top-5   :\n{df['primary_violation'].value_counts().head().to_string()}")
    log(f"  vehicle_category dist     :\n{df['vehicle_category'].value_counts().to_string()}")

    # ═══════════════════════════════════════════════════════════════
    # I. FILTER COLUMNS & EXPORT
    # ═══════════════════════════════════════════════════════════════
    all_cols = [col for cols in FEATURE_GROUPS.values() for col in cols]
    df_featured = df[all_cols].copy()

    # Export
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_featured.to_csv(output_path, index=False)
    log(f"\nFeatured dataset saved to: {output_path}")

    # Summary log
    log("\n" + "="*60)
    log("FEATURE ENGINEERING SUMMARY")
    log("="*60)
    for group, cols in FEATURE_GROUPS.items():
        log(f"  {group} ({len(cols)} columns)")
    log(f"\nFinal shape: {df_featured.shape}")

    return df_featured


if __name__ == "__main__":
    logger = setup_logging()
    config = load_config()

    input_path = config["data"]["cleaned_violation_path"]
    output_path = config["data"]["featured_violation_path"]

    run_feature_engineering(input_path, output_path, logger)
