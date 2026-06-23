"""
backend/database.py
====================
In-memory data store for Gridlock 2.0 Backend.

All CSVs and JSON are loaded into module-level DataFrames at import time.
Write helpers flush changes back to disk so state persists across restarts.
"""

from __future__ import annotations

import json
import os
import threading
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from pymongo import MongoClient

MONGODB_URI = "mongodb+srv://hackbaroda:Ic1Rg4OGmMkHJEsu@hackbaroda.y4bpo48.mongodb.net/?appName=HackBaroda"
DB_NAME = "gridlock"

print("[database] Connecting to MongoDB Atlas...")
client = MongoClient(MONGODB_URI)
db_mongo = client[DB_NAME]

# Thread lock for all database writes
_write_lock = threading.Lock()


# ------------------------------------------------------------------
# LOADER HELPERS
# ------------------------------------------------------------------

def _load_mongo_df(collection_name: str, required: bool = True) -> Optional[pd.DataFrame]:
    print(f"  [DB] Fetching {collection_name} from Atlas...")
    cursor = db_mongo[collection_name].find({}, {"_id": 0})
    records = list(cursor)
    if not records:
        if required:
            print(f"  [WARNING] Collection '{collection_name}' is empty.")
        return pd.DataFrame()
    df = pd.DataFrame(records)
    print(f"  [DB] Loaded {collection_name:<14} : {len(df):>7,} rows")
    return df

def _load_mongo_json(collection_name: str, required: bool = True) -> dict:
    print(f"  [DB] Fetching {collection_name} from Atlas...")
    doc = db_mongo[collection_name].find_one({"_type": "singleton"}, {"_id": 0})
    if not doc or "data" not in doc:
        if required:
            print(f"  [WARNING] Collection '{collection_name}' is empty.")
        return {}
    return doc["data"]

# ------------------------------------------------------------------
# MODULE-LEVEL DATA STORE
# ------------------------------------------------------------------

print("[database] Loading all pipeline outputs into memory from MongoDB...")

# Read-mostly tables (large — loaded once)
df_registry   : pd.DataFrame = _load_mongo_df("registry")
df_weekly     : pd.DataFrame = _load_mongo_df("weekly")
df_cii        : pd.DataFrame = _load_mongo_df("cii")
df_forecast   : pd.DataFrame = _load_mongo_df("forecast")
df_volatility : pd.DataFrame = _load_mongo_df("volatility")
df_priority   : pd.DataFrame = _load_mongo_df("priority")

# Mutable tables (written back to disk on updates)
df_teams      : pd.DataFrame = _load_mongo_df("teams")
if df_teams is not None and not df_teams.empty:
    for col in ["current_zone", "current_assignment_id", "expected_free_at", "last_updated"]:
        if col in df_teams.columns:
            df_teams[col] = df_teams[col].astype(object)

df_assignments: pd.DataFrame = _load_mongo_df("assignments")
if df_assignments is not None and not df_assignments.empty:
    for col in ["arrived_at", "resolved_at", "expected_free_at", "outcome_type", "notes"]:
        if col in df_assignments.columns:
            df_assignments[col] = df_assignments[col].astype(object)

df_outcomes   : pd.DataFrame = _load_mongo_df("outcomes", required=False)

# JSON blobs
heatmap_data  : dict = _load_mongo_json("heatmap")

# Retrain status
retrain_status: dict = _load_mongo_json("retrain_status", required=False)

print(f"[database] Ready. {len(df_priority):,} priority zones | "
      f"{len(df_teams)} teams | {len(df_assignments)} assignments | "
      f"{len(df_outcomes)} outcomes")


# ------------------------------------------------------------------
# WRITE-BACK HELPERS
# ------------------------------------------------------------------

def _clean_dict(d):
    for k, v in d.items():
        if isinstance(v, float) and math.isnan(v):
            d[k] = None
    return d


def save_teams(df: pd.DataFrame) -> None:
    global df_teams
    df_teams = df.copy()
    with _write_lock:
        db_mongo["teams"].delete_many({})
        records = df_teams.to_dict(orient="records")
        if records:
            records = [_clean_dict(r) for r in records]
            db_mongo["teams"].insert_many(records)


def save_assignments(df: pd.DataFrame) -> None:
    global df_assignments
    df_assignments = df.copy()
    with _write_lock:
        db_mongo["assignments"].delete_many({})
        records = df_assignments.to_dict(orient="records")
        if records:
            records = [_clean_dict(r) for r in records]
            db_mongo["assignments"].insert_many(records)


def save_outcomes(df: pd.DataFrame) -> None:
    global df_outcomes
    df_outcomes = df.copy()
    with _write_lock:
        db_mongo["outcomes"].delete_many({})
        records = df_outcomes.to_dict(orient="records")
        if records:
            records = [_clean_dict(r) for r in records]
            db_mongo["outcomes"].insert_many(records)


def append_outcome(row: dict) -> None:
    """Append a single outcome row and flush."""
    global df_outcomes
    new_row = pd.DataFrame([row])
    with _write_lock:
        df_outcomes = pd.concat([df_outcomes, new_row], ignore_index=True)
        db_mongo["outcomes"].insert_one(_clean_dict(row.copy()))


def update_team_status(team_id: str, status: str, current_zone=None) -> bool:
    """
    Update a team's status in df_teams and flush.
    Returns True if team found, False otherwise.
    """
    global df_teams
    mask = df_teams["team_id"] == team_id
    if not mask.any():
        return False
    with _write_lock:
        df_teams.loc[mask, "status"] = status
        update_doc = {"$set": {"status": status}}
        if current_zone is not None:
            df_teams.loc[mask, "current_zone"] = current_zone
            update_doc["$set"]["current_zone"] = current_zone
        db_mongo["teams"].update_one({"team_id": team_id}, update_doc)
    return True


def get_team(team_id: str) -> Optional[dict]:
    row = df_teams[df_teams["team_id"] == team_id]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def get_zone_priority(cluster_id: int, time_band: str) -> Optional[dict]:
    mask = (
        (df_priority["cluster_id"] == cluster_id) &
        (df_priority["time_band"]  == time_band)
    )
    rows = df_priority[mask]
    if rows.empty:
        return None
    return rows.iloc[0].to_dict()


def get_heatmap_for_bands(bands: Optional[list[str]] = None) -> dict:
    if bands is None:
        return heatmap_data
    return {b: heatmap_data.get(b, []) for b in bands}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
