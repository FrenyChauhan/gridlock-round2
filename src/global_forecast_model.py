"""
src/global_forecast_model.py
============================
Bengaluru Traffic Violation Prediction - Global LightGBM Forecast Model

Strategy: M5-competition-style global model.
Instead of one model per (cluster_id, time_band) series, we train a SINGLE
LightGBM model on ALL series simultaneously. Cross-series learning lets the
model generalise even for short or sparse series.

Pipeline:
  1. Load weekly_cluster_timeband.csv  (output of weekly_aggregation.py)
  2. Join cluster-level static features from cluster_registry.csv
  3. Build lag + temporal + static features
  4. Chronological train / test split (last 5 weeks held out)
  5. Train global LightGBM + two baselines (hist-mean, naive-lag1)
  6. Evaluate MAE & RMSE; pick winner
  7. Save feature importance plot
  8. Generate next-week forecasts for every (cluster_id, time_band)
     -> data/processed/global_forecast.csv
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import lightgbm as lgb
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error

# ------------------------------------------------------------------
# PATH SETUP
# ------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils import load_config, setup_logging


# ==================================================================
# CONSTANTS
# ==================================================================

LGBM_PARAMS = dict(
    n_estimators      = 500,
    learning_rate     = 0.03,
    max_depth         = 6,
    num_leaves        = 31,
    min_child_samples = 20,
    subsample         = 0.8,
    colsample_bytree  = 0.8,
    random_state      = 42,
    n_jobs            = -1,
    verbose           = -1,
)

TEST_WEEKS   = 5          # last N weeks for evaluation
LAG_WEEKS    = [1, 2, 3]  # lag feature offsets
ROLL_WINDOW  = 3          # rolling mean window


# ==================================================================
# 1.  DATA LOADING
# ==================================================================

def load_weekly(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["week"] = pd.to_datetime(df["week"])
    df = df.sort_values(["cluster_id", "time_band", "week"]).reset_index(drop=True)
    return df


def load_registry(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


# ==================================================================
# 2.  FEATURE ENGINEERING
# ==================================================================

def build_static_features(weekly: pd.DataFrame, registry: pd.DataFrame) -> pd.DataFrame:
    """
    Merge cluster-level static features from the registry onto every row.
    We keep only numeric/encodable columns; strings are label-encoded.
    """
    reg = registry[[
        "cluster_id",
        "total_violations",   # cluster_size proxy
        "radius_m",
        "dominant_police_station",
        "pct_heavy_at_junction",   # heavy vehicle mix
        "mean_vehicle_blockage",   # light vehicle proxy (inverse)
    ]].copy()

    reg = reg.rename(columns={
        "total_violations"      : "cluster_size",
        "radius_m"              : "cluster_radius",
        "pct_heavy_at_junction" : "zone_heavy_pct",
        "mean_vehicle_blockage" : "zone_blockage_mean",
    })

    # zone_vehicle_mix_light_pct: invert blockage (heavy vehicles have high blockage)
    reg["zone_light_pct"] = 1.0 - reg["zone_blockage_mean"]

    le_station = LabelEncoder()
    reg["dominant_station_enc"] = le_station.fit_transform(
        reg["dominant_police_station"].fillna("Unknown")
    )
    reg = reg.drop(columns=["dominant_police_station"])

    return weekly.merge(reg, on="cluster_id", how="left"), le_station


def build_time_band_features(df: pd.DataFrame) -> pd.DataFrame:
    """Encode time_band as integer + two binary flags."""
    le_band = LabelEncoder()
    df["time_band_enc"] = le_band.fit_transform(df["time_band"])
    df["is_early_morning_band"] = (df["time_band"] == "early_morning").astype(int)
    df["is_evening_night_band"] = (df["time_band"] == "evening_night").astype(int)
    return df, le_band


def build_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Week-of-month, month, global week index, month-end flag."""
    df["month"]            = df["week"].dt.month
    df["week_of_month"]    = (df["week"].dt.day - 1) // 7 + 1   # 1..4

    # Global monotonic index (weeks since the first week in the dataset)
    min_week = df["week"].min()
    df["weeks_since_start"] = ((df["week"] - min_week).dt.days // 7).astype(int)

    # is_month_end_week: week starts within the last 7 days of the month
    days_in_month = df["week"].dt.days_in_month
    df["is_month_end_week"] = (df["week"].dt.day >= (days_in_month - 6)).astype(int)

    return df


def build_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-series lag & rolling features, plus city-wide and station-level lags.
    All lags are computed within the TRAINING window to avoid leakage;
    for test rows the lags are filled from the actual preceding data.
    """
    df = df.sort_values(["cluster_id", "time_band", "week"]).reset_index(drop=True)

    # --- Per-series lags (lag1, lag2, lag3, rolling3_mean) --------
    grp = df.groupby(["cluster_id", "time_band"])["violation_count"]

    for lag in LAG_WEEKS:
        df[f"lag{lag}_count"] = grp.shift(lag)

    df["rolling3_mean"] = (
        df.groupby(["cluster_id", "time_band"])["violation_count"]
        .transform(lambda s: s.shift(1).rolling(ROLL_WINDOW, min_periods=1).mean())
    )

    # --- City-wide weekly total (lagged by 1 week) ----------------
    city_weekly = (
        df.groupby("week")["violation_count"]
        .sum()
        .rename("city_total")
        .reset_index()
    )
    city_weekly["city_total_lag1"] = city_weekly["city_total"].shift(1)
    df = df.merge(city_weekly[["week", "city_total", "city_total_lag1"]],
                  on="week", how="left")

    # zone_vs_city_ratio: this zone's share of city violations (3-week rolling avg)
    df["zone_city_ratio"] = df["rolling3_mean"] / (df["city_total_lag1"] + 1e-6)

    # --- Station-level lag1 (same police station, same time_band) -
    # We approximate this from cluster registry dominant_station_enc
    # by summing across clusters sharing the same station + time_band
    station_week = (
        df.groupby(["dominant_station_enc", "time_band", "week"])["violation_count"]
        .sum()
        .rename("station_count")
        .reset_index()
    )
    station_week = station_week.sort_values(["dominant_station_enc", "time_band", "week"])
    station_week["station_lag1"] = station_week.groupby(
        ["dominant_station_enc", "time_band"]
    )["station_count"].shift(1)

    df = df.merge(
        station_week[["dominant_station_enc", "time_band", "week", "station_lag1"]],
        on=["dominant_station_enc", "time_band", "week"],
        how="left",
    )

    return df


# ==================================================================
# 3.  TRAIN / TEST SPLIT (chronological)
# ==================================================================

def train_test_split_chrono(df: pd.DataFrame, n_test_weeks: int):
    all_weeks = sorted(df["week"].unique())
    if len(all_weeks) <= n_test_weeks:
        raise ValueError(
            f"Only {len(all_weeks)} weeks available but n_test_weeks={n_test_weeks}. "
            "Reduce TEST_WEEKS or run on more data."
        )
    cutoff = all_weeks[-n_test_weeks]
    train = df[df["week"] < cutoff].copy()
    test  = df[df["week"] >= cutoff].copy()
    return train, test, cutoff


# ==================================================================
# 4.  FEATURE COLUMNS
# ==================================================================

CATEGORICAL_COLS = ["time_band_enc", "dominant_station_enc", "month"]

FEATURE_COLS = [
    # Temporal
    "week_of_month", "month", "weeks_since_start", "is_month_end_week",
    # Time band
    "time_band_enc", "is_early_morning_band", "is_evening_night_band",
    # Cluster static
    "cluster_size", "cluster_radius", "dominant_station_enc",
    "zone_heavy_pct", "zone_light_pct",
    # Lag / rolling
    "lag1_count", "lag2_count", "lag3_count", "rolling3_mean",
    "city_total_lag1", "zone_city_ratio", "station_lag1",
]

TARGET_COL = "violation_count"


# ==================================================================
# 5.  MODEL TRAINING & EVALUATION
# ==================================================================

def eval_metrics(y_true, y_pred, name: str, log) -> dict:
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    log(f"  {name:<30}  MAE={mae:8.2f}   RMSE={rmse:8.2f}")
    return {"name": name, "mae": mae, "rmse": rmse}


def baseline_hist_mean(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Per-series expanding mean from the training period."""
    means = (
        train.groupby(["cluster_id", "time_band"])[TARGET_COL]
        .mean()
        .rename("hist_mean")
        .reset_index()
    )
    pred = test.merge(means, on=["cluster_id", "time_band"], how="left")
    global_mean = train[TARGET_COL].mean()
    return pred["hist_mean"].fillna(global_mean).values


def baseline_naive_lag1(test: pd.DataFrame) -> np.ndarray:
    """Naive: predict the same as last week (lag1)."""
    return test["lag1_count"].fillna(test[TARGET_COL].mean()).values


def compute_sample_weights(train_df):
    """
    Assign higher weight to more recent weeks.
    Uses exponential decay: weight = decay_rate ^ weeks_ago
    decay_rate = 0.85 (tunable)
    """
    max_week = train_df['week'].max()
    train_df = train_df.copy()
    train_df['weeks_ago'] = (
        (max_week - train_df['week']).dt.days / 7
    ).round().astype(int)
    
    decay_rate = 0.85
    train_df['sample_weight'] = decay_rate ** train_df['weeks_ago']
    
    # Normalize weights to sum to len(train_df)
    # so effective sample size is preserved
    total = train_df['sample_weight'].sum()
    train_df['sample_weight'] = (
        train_df['sample_weight'] / total * len(train_df)
    )
    return train_df


def train_lgbm(train: pd.DataFrame, log, use_weights: bool = False):
    feat_cols = [c for c in FEATURE_COLS if c in train.columns]
    cat_cols  = [c for c in CATEGORICAL_COLS if c in train.columns]
    train_clean = train.dropna(subset=feat_cols + [TARGET_COL])

    if use_weights:
        train_clean = compute_sample_weights(train_clean)
        sample_weight = train_clean['sample_weight']
    else:
        sample_weight = None

    log(f"\n  Training on {len(train_clean):,} rows  |  {len(feat_cols)} features | weighted={use_weights}")
    model = lgb.LGBMRegressor(**LGBM_PARAMS)
    model.fit(
        train_clean[feat_cols],
        train_clean[TARGET_COL],
        sample_weight=sample_weight,
        categorical_feature=cat_cols,
        callbacks=[lgb.log_evaluation(period=100)],
    )
    return model, feat_cols


# ==================================================================
# 6.  FEATURE IMPORTANCE PLOT
# ==================================================================

def save_feature_importance(model, feat_cols: list, plot_path: str, log):
    os.makedirs(os.path.dirname(plot_path), exist_ok=True)
    importances = pd.Series(model.feature_importances_, index=feat_cols).sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(10, max(6, len(feat_cols) * 0.4)))
    colors = ["#e63946" if i >= len(importances) - 5 else "#457b9d"
              for i in range(len(importances))]
    importances.plot(kind="barh", ax=ax, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_title("Global LightGBM - Feature Importance (Gain)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Importance (gain)", fontsize=11)
    ax.set_ylabel("")
    ax.grid(True, axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(plot_path, dpi=150)
    plt.close()
    log(f"  Feature importance plot saved: {plot_path}")


# ==================================================================
# 7.  NEXT-WEEK FORECAST GENERATION
# ==================================================================

def generate_next_week_forecast(
    df: pd.DataFrame,
    model,
    feat_cols: list,
    hist_means: pd.DataFrame,
    global_lgbm_wins: bool,
    log,
) -> pd.DataFrame:
    """
    Build feature rows for the NEXT week (1 week beyond the last observed week)
    for every (cluster_id, time_band) series, then predict.
    Confidence interval: +/- 1 std of residuals on the training set.
    """
    last_week = df["week"].max()
    next_week = last_week + pd.Timedelta(weeks=1)
    log(f"\n  Forecasting for week: {next_week.date()}")

    # Take the last observed row per series as template
    last_rows = (
        df.sort_values("week")
        .groupby(["cluster_id", "time_band"])
        .tail(1)
        .copy()
    )

    last_rows["week"]             = next_week
    last_rows["month"]            = next_week.month
    last_rows["week_of_month"]    = (next_week.day - 1) // 7 + 1
    last_rows["weeks_since_start"] = last_rows["weeks_since_start"] + 1
    days_in_month = next_week.days_in_month
    last_rows["is_month_end_week"] = int(next_week.day >= (days_in_month - 6))

    # Shift lags: last week's actual count becomes lag1
    last_rows["lag2_count"]  = last_rows["lag1_count"]
    last_rows["lag3_count"]  = last_rows["lag2_count"]
    last_rows["lag1_count"]  = last_rows[TARGET_COL]
    last_rows["rolling3_mean"] = (
        last_rows[["lag1_count", "lag2_count", "lag3_count"]].mean(axis=1)
    )

    # City-wide: use last known city total as lag1
    city_last = df.groupby("week")[TARGET_COL].sum().iloc[-1]
    last_rows["city_total_lag1"] = city_last
    last_rows["zone_city_ratio"] = last_rows["rolling3_mean"] / (city_last + 1e-6)

    # Station lag1: use current station sums
    station_now = (
        df[df["week"] == last_week]
        .groupby(["dominant_station_enc", "time_band"])[TARGET_COL]
        .sum()
        .rename("station_lag1")
        .reset_index()
    )
    last_rows = last_rows.drop(columns=["station_lag1"], errors="ignore")
    last_rows = last_rows.merge(
        station_now, on=["dominant_station_enc", "time_band"], how="left"
    )

    feat_cols_present = [c for c in feat_cols if c in last_rows.columns]
    X_next = last_rows[feat_cols_present].fillna(0)

    if global_lgbm_wins:
        preds = np.maximum(0, model.predict(X_next))
        method = "global_lgbm"
        # Residual std from training set predictions
        train_clean = df.dropna(subset=feat_cols_present + [TARGET_COL])
        train_preds = np.maximum(0, model.predict(train_clean[feat_cols_present]))
        resid_std   = np.std(train_clean[TARGET_COL].values - train_preds)
    else:
        merged = last_rows.merge(hist_means, on=["cluster_id", "time_band"], how="left")
        global_mean = df[TARGET_COL].mean()
        preds  = merged["hist_mean"].fillna(global_mean).values
        method = "historical_mean"
        resid_std = df.groupby(["cluster_id", "time_band"])[TARGET_COL].std().mean()

    z = 1.645  # 90% CI
    lower = np.maximum(0, preds - z * resid_std)
    upper = preds + z * resid_std

    forecast_df = pd.DataFrame({
        "cluster_id"          : last_rows["cluster_id"].values,
        "time_band"           : last_rows["time_band"].values,
        "forecast_week"       : next_week.date(),
        "predicted_violations": np.round(preds, 2),
        "lower_bound"         : np.round(lower, 2),
        "upper_bound"         : np.round(upper, 2),
        "forecast_method"     : method,
    })

    return forecast_df.sort_values(["cluster_id", "time_band"]).reset_index(drop=True)


# ==================================================================
# 8.  MAIN ENTRY POINT
# ==================================================================

def run_global_forecast_model(
    weekly_path   : str,
    registry_path : str,
    forecast_path : str,
    plot_path     : str,
    logger        = None,
):
    def log(msg, level="info"):
        if logger:
            getattr(logger, level, logger.info)(msg)
        else:
            print(msg)

    # ── Load ──────────────────────────────────────────────────────
    log(f"\nLoading weekly data from: {weekly_path}")
    if not os.path.exists(weekly_path):
        raise FileNotFoundError(f"Weekly aggregation file not found: {weekly_path}")
    df = load_weekly(weekly_path)
    log(f"  Shape: {df.shape}  |  weeks: {df['week'].nunique()}  |  "
        f"series: {df.groupby(['cluster_id','time_band']).ngroups}")

    log(f"\nLoading cluster registry from: {registry_path}")
    registry = load_registry(registry_path)
    log(f"  Registry shape: {registry.shape}")

    # ── Feature engineering ───────────────────────────────────────
    log("\nBuilding static features...")
    df, le_station = build_static_features(df, registry)

    log("Building time-band features...")
    df, le_band = build_time_band_features(df)

    log("Building temporal features...")
    df = build_temporal_features(df)

    log("Building lag features (this may take a moment)...")
    df = build_lag_features(df)

    log(f"  Final feature dataframe shape: {df.shape}")

    # ── Train / test split ────────────────────────────────────────
    log(f"\nSplitting: last {TEST_WEEKS} weeks as test...")
    train, test, cutoff = train_test_split_chrono(df, TEST_WEEKS)
    log(f"  Train weeks: {train['week'].nunique()}  ({len(train):,} rows)")
    log(f"  Test  weeks: {test['week'].nunique()}   ({len(test):,} rows)  | cutoff: {cutoff.date()}")

    # ── Baselines ─────────────────────────────────────────────────
    log("\n--- Baselines ---")
    hist_means = (
        train.groupby(["cluster_id", "time_band"])[TARGET_COL]
        .mean()
        .rename("hist_mean")
        .reset_index()
    )

    y_test = test[TARGET_COL].values
    results = []

    hm_pred = baseline_hist_mean(train, test)
    results.append(eval_metrics(y_test, hm_pred, "Historical Mean", log))

    nl_pred = baseline_naive_lag1(test)
    nl_valid = ~np.isnan(nl_pred)
    if nl_valid.sum() > 0:
        results.append(eval_metrics(y_test[nl_valid], nl_pred[nl_valid], "Naive Lag-1", log))

    # ── Global LightGBM (Unweighted) ───────────────────────────────────────────
    log("\n--- Global LightGBM (Unweighted) ---")
    model_unw, feat_cols = train_lgbm(train, log, use_weights=False)

    feat_cols_present = [c for c in feat_cols if c in test.columns]
    test_clean  = test.dropna(subset=feat_cols_present + [TARGET_COL])
    lgbm_preds_unw  = np.maximum(0, model_unw.predict(test_clean[feat_cols_present]))
    lgbm_result_unw = eval_metrics(test_clean[TARGET_COL].values, lgbm_preds_unw, "Global LightGBM (Unweighted)", log)
    results.append(lgbm_result_unw)

    # ── Global LightGBM (Temporally Weighted) ───────────────────────────────────────────
    log("\n--- Global LightGBM (Temporally Weighted) ---")
    model_w, feat_cols_w = train_lgbm(train, log, use_weights=True)

    lgbm_preds_w  = np.maximum(0, model_w.predict(test_clean[feat_cols_present]))
    lgbm_result_w = eval_metrics(test_clean[TARGET_COL].values, lgbm_preds_w, "Global LightGBM (Weighted)", log)
    results.append(lgbm_result_w)

    # ── Decision ──────────────────────────────────────────────────
    hm_mae   = next(r["mae"] for r in results if r["name"] == "Historical Mean")
    lgbm_unw_mae = lgbm_result_unw["mae"]
    lgbm_w_mae = lgbm_result_w["mae"]

    log("\n" + "=" * 55)
    log("MODEL SELECTION")
    log("=" * 55)
    
    best_lgbm_mae = min(lgbm_unw_mae, lgbm_w_mae)
    best_model_name = "Global LightGBM (Weighted)" if lgbm_w_mae < lgbm_unw_mae else "Global LightGBM (Unweighted)"
    model = model_w if lgbm_w_mae < lgbm_unw_mae else model_unw

    if best_lgbm_mae < hm_mae:
        global_lgbm_wins = True
        improvement = (hm_mae - best_lgbm_mae) / hm_mae * 100
        log(f"  WINNER: {best_model_name}  (MAE improvement: {improvement:.1f}%)")
        log("  Saving as production model.")
    else:
        global_lgbm_wins = False
        log(f"  WINNER: Historical Mean")
        log(f"  Best LightGBM MAE ({best_lgbm_mae:.2f}) >= Historical Mean MAE ({hm_mae:.2f}).")
        log("  Using historical mean for production forecasts.")
        log("  Honest assessment: global model did not beat the simple baseline.")
        log("  Consider: more data, feature tuning, or a different target transform.")
        
    # Write report
    report_path = os.path.join(PROJECT_ROOT, "data/processed/temporal_weight_report.txt")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write("TEMPORAL WEIGHTING EXPERIMENT REPORT\n")
        f.write("====================================\n\n")
        for r in results:
            f.write(f"{r['name']:<35} MAE: {r['mae']:.4f}\n")
        f.write("\n")
        if global_lgbm_wins:
            f.write(f"Decision: Using {best_model_name} for production.\n")
        else:
            f.write("Decision: Using Historical Mean for production.\n")

    # ── Feature importance ────────────────────────────────────────
    log("\nSaving feature importance plot...")
    save_feature_importance(model, feat_cols, plot_path, log)

    # ── Generate next-week forecasts ──────────────────────────────
    log("\nGenerating next-week forecasts...")
    forecast_df = generate_next_week_forecast(
        df, model, feat_cols, hist_means, global_lgbm_wins, log
    )

    os.makedirs(os.path.dirname(forecast_path), exist_ok=True)
    forecast_df.to_csv(forecast_path, index=False)
    log(f"\n  Forecast saved: {forecast_path}")
    log(f"  Rows: {len(forecast_df):,}  |  "
        f"method: {forecast_df['forecast_method'].iloc[0]}")

    log("\n" + "=" * 55)
    log("GLOBAL FORECAST MODEL SUMMARY")
    log("=" * 55)
    for r in results:
        log(f"  {r['name']:<30}  MAE={r['mae']:8.2f}   RMSE={r['rmse']:8.2f}")
    log(f"\n  Production method : {'Global LightGBM' if global_lgbm_wins else 'Historical Mean'}")
    log(f"  Forecast file     : {forecast_path}")
    log(f"  Importance plot   : {plot_path}")

    return forecast_df, model, results


# ==================================================================
# CLI ENTRY POINT
# ==================================================================

if __name__ == "__main__":
    logger = setup_logging("pipeline.log")
    config = load_config(os.path.join(PROJECT_ROOT, "configs", "config.yaml"))

    weekly_path   = os.path.join(PROJECT_ROOT, config["forecasting"]["weekly_aggregation_path"])
    registry_path = os.path.join(PROJECT_ROOT, config["data"]["cluster_registry_path"])
    forecast_path = os.path.join(PROJECT_ROOT, "data/processed/global_forecast.csv")
    plot_path     = os.path.join(PROJECT_ROOT, "outputs/plots/feature_importance.png")

    run_global_forecast_model(
        weekly_path   = weekly_path,
        registry_path = registry_path,
        forecast_path = forecast_path,
        plot_path     = plot_path,
        logger        = logger,
    )
