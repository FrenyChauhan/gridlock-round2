"""
Stage 3 — Chronological Split, Model Training, Baseline Comparison
=====================================================================
Input:  weekly_features.csv (from Stage 2)
Output: trained model (lightgbm_hotspot_forecast.txt)
        validation_report.txt (MAE/RMSE vs naive baselines, on held-out weeks)
"""

import os
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
from src.utils import load_config

FEATURE_COLS = [
    "lag1_violation_count", "lag2_violation_count", "lag3_violation_count",
    "lag1_hotspot_score", "lag2_hotspot_score", "lag3_hotspot_score",
    "roll3_mean_violation_count", "roll3_std_violation_count",
    "roll3_mean_hotspot_score", "trend_violation_count",
    "expanding_mean_violation_count", "expanding_mean_hotspot_score",
    "weeks_of_prior_history", "pct_weekend", "pct_at_junction",
    "mean_severity_norm", "mean_time_demand", "mean_junction_mult",
    "mean_vehicle_blockage",
]
CATEGORICAL_COLS = ["cluster_id", "time_band"]
TARGET_COL = "target_next_week_violation_count"


def chronological_split(df: pd.DataFrame, test_weeks: int = 6):
    """
    Last `test_weeks` distinct weeks (by calendar order) become the test set.
    """
    weeks_sorted = sorted(df["week"].unique())
    if len(weeks_sorted) <= test_weeks:
        raise ValueError(
            f"Only {len(weeks_sorted)} distinct weeks available, "
            f"need more than test_weeks={test_weeks} to split."
        )
    split_week = weeks_sorted[-test_weeks]
    train = df[df["week"] < split_week].copy()
    test = df[df["week"] >= split_week].copy()
    return train, test, split_week


def train_model(train: pd.DataFrame):
    for c in CATEGORICAL_COLS:
        train[c] = train[c].astype("category")

    X_train = train[FEATURE_COLS + CATEGORICAL_COLS]
    y_train = train[TARGET_COL]

    model = lgb.LGBMRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=5,
        num_leaves=15,
        min_child_samples=10,
        random_state=42,
        verbosity=-1,
    )
    model.fit(X_train, y_train, categorical_feature=CATEGORICAL_COLS)
    return model


def evaluate(model, test: pd.DataFrame) -> dict:
    for c in CATEGORICAL_COLS:
        test[c] = test[c].astype("category")

    X_test = test[FEATURE_COLS + CATEGORICAL_COLS]
    y_test = test[TARGET_COL]

    model_pred = model.predict(X_test)
    naive_lag1_pred = test["violation_count"].values
    naive_mean_pred = test["expanding_mean_violation_count"].fillna(
        test["violation_count"].median()
    ).values

    results = {}
    for name, pred in [
        ("LightGBM model", model_pred),
        ("Naive lag-1 baseline", naive_lag1_pred),
        ("Historical mean baseline", naive_mean_pred),
    ]:
        mae = mean_absolute_error(y_test, pred)
        rmse = np.sqrt(mean_squared_error(y_test, pred))
        results[name] = {"MAE": mae, "RMSE": rmse}

    return results


def recombine_into_hotspot_score(
    test: pd.DataFrame, predicted_violation_count: np.ndarray, score_min: float, score_max: float
) -> pd.DataFrame:
    """
    Forecasting only predicts violation_count (the volatile quantity).
    """
    out = test.copy()
    out["predicted_violation_count"] = predicted_violation_count

    raw = (
        out["predicted_violation_count"]
        * out["mean_severity_norm"]
        * out["mean_time_demand"]
        * out["mean_junction_mult"]
    )
    out["predicted_hotspot_score_raw"] = raw

    if score_max > score_min:
        out["predicted_hotspot_score"] = (
            (raw - score_min) / (score_max - score_min)
        ).clip(0, 1)
    else:
        out["predicted_hotspot_score"] = 0.0

    return out


def run_training(input_path: str, model_output_path: str, report_output_path: str, test_weeks: int = 6):
    df = pd.read_csv(input_path)
    df["week"] = pd.to_datetime(df["week"])

    raw_min, raw_max = df["hotspot_score_raw"].min(), df["hotspot_score_raw"].max()

    # Restrict to rows actually usable for training/eval
    usable = df[(df["tier"] == "model") & (df[TARGET_COL].notna())].copy()
    print(f"Usable rows (model tier, valid target): {len(usable):,} of {len(df):,} total")

    train, test, split_week = chronological_split(usable, test_weeks=test_weeks)
    print(f"Chronological split at week {split_week.date()}")
    print(f"  Train: {len(train):,} rows, weeks {train['week'].min().date()} to {train['week'].max().date()}")
    print(f"  Test:  {len(test):,} rows, weeks {test['week'].min().date()} to {test['week'].max().date()}")

    if len(train) < 30:
        print("\n*** WARNING: very few training rows. Results below are illustrative only ***")
        print("*** This is expected on the 4% sample -- re-run on the full dataset. ***\n")

    model = train_model(train)
    results = evaluate(model, test)

    report_lines = [
        f"Chronological split at week {split_week.date()}",
        f"Train rows: {len(train)} | Test rows: {len(test)}",
        f"Target: {TARGET_COL}", ""
    ]
    print(f"\nValidation results (held-out weeks, target = {TARGET_COL}):")
    for name, metrics in results.items():
        line = f"  {name:30s} MAE={metrics['MAE']:.4f}  RMSE={metrics['RMSE']:.4f}"
        print(line)
        report_lines.append(line)

    # Recombine forecasted violation_count into a forecasted hotspot_score
    for c in CATEGORICAL_COLS:
        test[c] = test[c].astype("category")
    X_test = test[FEATURE_COLS + CATEGORICAL_COLS]
    pred_counts = model.predict(X_test)
    recombined = recombine_into_hotspot_score(test, pred_counts, raw_min, raw_max)

    score_mae = mean_absolute_error(
        recombined["target_next_week_hotspot_score"], recombined["predicted_hotspot_score"]
    )
    score_line = f"\nRecombined hotspot_score MAE (vs actual next-week score): {score_mae:.4f}"
    print(score_line)
    report_lines.append(score_line)

    os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
    os.makedirs(os.path.dirname(report_output_path), exist_ok=True)
    
    model.booster_.save_model(model_output_path)
    with open(report_output_path, "w") as f:
        f.write("\n".join(report_lines))

    print(f"\nModel saved to: {model_output_path}")
    print(f"Report saved to: {report_output_path}")

    return model, results, recombined


if __name__ == "__main__":
    config = load_config()
    input_path = config["forecasting"]["weekly_features_path"]
    model_output_path = config["forecasting"]["model_output_path"]
    report_output_path = config["forecasting"]["report_output_path"]
    test_weeks = int(config["forecasting"]["test_weeks"])
    
    run_training(input_path, model_output_path, report_output_path, test_weeks)
