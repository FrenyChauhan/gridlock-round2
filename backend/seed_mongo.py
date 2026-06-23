"""
backend/seed_mongo.py
======================
Reads all CSVs and JSONs from data/processed and seeds the MongoDB Atlas cluster.
"""

import os
import json
import math
import time
from pathlib import Path
import pandas as pd
from pymongo import MongoClient
from pymongo.errors import AutoReconnect

MONGODB_URI = "mongodb+srv://hackbaroda:Ic1Rg4OGmMkHJEsu@hackbaroda.y4bpo48.mongodb.net/?appName=HackBaroda"
DB_NAME = "gridlock"

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
DATA_DIR = _PROJECT_ROOT / "data" / "processed"

_PATHS = {
    # ML Pipeline Intermediates (Too large for free-tier Mongo to stream in one go during demo)
    # "cleaned"       : DATA_DIR / "cleaned_violations.csv",
    # "featured"      : DATA_DIR / "featured_violations.csv",
    # "clustered"     : DATA_DIR / "clustered_violations.csv",
    
    # Operational Dashboard Data (Tiny and fast)
    "registry"      : DATA_DIR / "cluster_registry.csv",
    "weekly"        : DATA_DIR / "weekly_cluster_timeband.csv",
    "cii"           : DATA_DIR / "cii_scores.csv",
    "forecast"      : DATA_DIR / "global_forecast.csv",
    "volatility"    : DATA_DIR / "volatility_scores.csv",
    "priority"      : DATA_DIR / "final_priority_table.csv",
    "teams"         : DATA_DIR / "patrol_teams.csv",
    "assignments"   : DATA_DIR / "team_assignments.csv",
    "outcomes"      : DATA_DIR / "enforcement_outcomes.csv",
    "heatmap"       : DATA_DIR / "heatmap_data.json",
    "retrain_status": DATA_DIR / "retrain_status.json",
}

def clean_dict(d):
    """Recursively convert float('nan') to None so MongoDB doesn't complain."""
    for k, v in d.items():
        if isinstance(v, float) and math.isnan(v):
            d[k] = None
        elif isinstance(v, dict):
            clean_dict(v)
    return d

def seed_mongo():
    print(f"Connecting to MongoDB at {MONGODB_URI.split('@')[1]}...")
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    
    print("Dropping existing collections to ensure a clean seed...")
    for coll in db.list_collection_names():
        db[coll].drop()

    for key, path in _PATHS.items():
        if not path.exists():
            print(f"Skipping {key}, file not found: {path}")
            continue

        print(f"Seeding {key}...")
        
        if path.suffix == ".csv":
            df = pd.read_csv(path, low_memory=False)
            records = df.to_dict(orient="records")
            cleaned_records = [clean_dict(r) for r in records]
            
            if cleaned_records:
                BATCH_SIZE = 1000
                total = len(cleaned_records)
                inserted = 0
                for i in range(0, total, BATCH_SIZE):
                    batch = cleaned_records[i:i + BATCH_SIZE]
                    retries = 3
                    while retries > 0:
                        try:
                            db[key].insert_many(batch)
                            inserted += len(batch)
                            print(f"  Inserted {inserted}/{total} into '{key}'...")
                            time.sleep(0.1) # Soften the blow to free-tier Atlas
                            break
                        except AutoReconnect as e:
                            retries -= 1
                            print(f"  Connection lost. Retries left: {retries}. Waiting 5 seconds...")
                            time.sleep(5)
                            if retries == 0:
                                raise e
            else:
                print(f"  No records found in '{key}'")
                
        elif path.suffix == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # For JSON blobs, we store a single document with the whole payload
            doc = {"_type": "singleton", "data": clean_dict(data)}
            db[key].insert_one(doc)
            print(f"  Inserted JSON blob into '{key}'")
            
    print("\nCreating indexes...")
    # Add indexes based on our architectural plan
    db.priority.create_index([("cluster_id", 1), ("time_band", 1)])
    db.teams.create_index("team_id", unique=True)
    db.assignments.create_index("team_id")
    db.assignments.create_index("assignment_id", unique=True)
    
    print("Seed complete!")

if __name__ == "__main__":
    seed_mongo()
