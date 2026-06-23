"""
backend/routers/feedback.py
============================
POST /feedback/submit                  — cop submits outcome
GET  /feedback/zone-accuracy/{cid}     — per-zone stats for control room
GET  /feedback/retrain-status          — status of retrain triggers
POST /feedback/trigger-retrain         — superadmin only: force retrain data prep
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth import get_current_user, require_control_room, require_superadmin
from backend import database as db

# Import pipeline helpers
import sys
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.feedback_manager import add_outcome, check_retrain_trigger, prepare_retrain_data

router = APIRouter(prefix="/feedback", tags=["Feedback"])


class SubmitOutcomeRequest(BaseModel):
    assignment_id: str
    actual_violations_found: float
    outcome_type: str = Field(..., description="violation_confirmed/false_positive/needs_backup/resolved_quickly")
    notes: Optional[str] = None


@router.post("/submit", summary="Cop submits enforcement outcome")
def submit_outcome(body: SubmitOutcomeRequest, user: dict = Depends(get_current_user)):
    df = db.df_assignments
    mask = df["assignment_id"] == body.assignment_id
    if not mask.any():
        raise HTTPException(status_code=404, detail="Assignment not found")
        
    record = df[mask].iloc[0]
    
    # Validate assignment belongs to cop's team
    if user["role"] == "officer" and str(record["team_id"]) != user.get("team_id"):
        raise HTTPException(status_code=403, detail="You can only submit outcomes for your own team's assignments")
        
    # Build dict for add_outcome
    outcome_dict = {
        "assignment_id": body.assignment_id,
        "zone_id": str(record.get("zone_id", f"ZONE-{record['cluster_id']:04d}-{record['time_band']}")),
        "cluster_id": int(record["cluster_id"]),
        "time_band": str(record["time_band"]),
        "forecast_date": "2024-04-15", # Default based on existing pipeline
        "predicted_violations": float(record.get("predicted_violations", 0)),
        "actual_violations_found": body.actual_violations_found,
        "outcome_type": body.outcome_type,
        "officer_id": str(record["team_id"]),
        "response_time_minutes": 20.0 # Default mock
    }
    
    # Calculate response time if timestamps exist
    arrived = record.get("arrived_at")
    resolved = record.get("resolved_at") or db.utc_now()
    if pd.notna(arrived) and pd.notna(resolved):
        try:
            from datetime import datetime
            arr = datetime.fromisoformat(str(arrived).replace("Z", "+00:00")).replace(tzinfo=None)
            res = datetime.fromisoformat(str(resolved).replace("Z", "+00:00")).replace(tzinfo=None)
            mins = (res - arr).total_seconds() / 60.0
            outcome_dict["response_time_minutes"] = max(1.0, round(mins, 1))
        except:
            pass
            
    # Add to file
    outcome_id = add_outcome(outcome_dict)
    
    # Reload outcomes to keep memory in sync
    from backend.database import _load_csv
    db.df_outcomes = _load_csv("outcomes")
    
    # Check retrain trigger
    check_retrain_trigger()
    
    # Sync retrain_status memory
    from backend.database import _load_json
    db.retrain_status = _load_json("retrain_status", required=False)
    
    # Get accuracy stats
    zone_outcomes = db.df_outcomes[db.df_outcomes["cluster_id"] == int(record["cluster_id"])]
    confirmed_rate = 0.0
    fp_rate = 0.0
    if not zone_outcomes.empty:
        confirmed_rate = float((zone_outcomes["outcome_type"] == "violation_confirmed").mean())
        fp_rate = float((zone_outcomes["outcome_type"] == "false_positive").mean())
        
    return {
        "outcome_id": outcome_id,
        "status": "recorded",
        "zone_accuracy": {
            "cluster_id": int(record["cluster_id"]),
            "confirmed_rate": round(confirmed_rate, 4),
            "false_positive_rate": round(fp_rate, 4)
        }
    }


@router.get("/zone-accuracy/{cluster_id}", summary="Per-zone accuracy stats")
def zone_accuracy(cluster_id: int, user: dict = Depends(require_control_room)):
    df = db.df_outcomes
    if df.empty or "cluster_id" not in df.columns:
        return {"total_outcomes": 0}
        
    zone_df = df[df["cluster_id"] == cluster_id]
    n = len(zone_df)
    if n == 0:
        return {"total_outcomes": 0}
        
    confirmed_r = float((zone_df["outcome_type"] == "violation_confirmed").mean()) * 100.0
    fp_rate = float((zone_df["outcome_type"] == "false_positive").mean()) * 100.0
    
    avg_pred = float(zone_df["predicted_violations"].mean()) if "predicted_violations" in zone_df.columns else 0.0
    avg_act = float(zone_df["actual_violations_found"].mean()) if "actual_violations_found" in zone_df.columns else 0.0
    
    avg_resp = float(zone_df["response_time_minutes"].mean()) if "response_time_minutes" in zone_df.columns else 15.0
    
    return {
        "cluster_id": cluster_id,
        "total_outcomes": n,
        "confirmed_rate": round(confirmed_r, 1),
        "fp_rate": round(fp_rate, 1),
        "avg_predicted": round(avg_pred, 1),
        "avg_actual": round(avg_act, 1),
        "avg_response_time": round(avg_resp, 1)
    }


@router.get("/retrain-status", summary="Current retrain trigger status")
def get_retrain_status(user: dict = Depends(require_control_room)):
    status = db.retrain_status
    if not status:
        return {"message": "No retrain status generated yet."}
        
    return {
        "should_retrain": status.get("should_retrain", False),
        "last_checked_at": status.get("last_checked_at"),
        "total_outcomes": status.get("total_outcomes", 0),
        "new_since_last": status.get("new_since_last", 0),
        "trigger_reasons": status.get("trigger_reasons", [])
    }


@router.post("/trigger-retrain", summary="Force retrain data prep (superadmin only)")
def trigger_retrain(user: dict = Depends(require_superadmin)):
    try:
        merged_df = prepare_retrain_data()
        
        # Count rows with GT injected
        if "has_ground_truth" in merged_df.columns:
            gt_count = int(merged_df["has_ground_truth"].sum())
        else:
            gt_count = 0
            
        return {
            "message": "Retrain dataset prepped successfully.",
            "retrain_ready_rows": len(merged_df),
            "zones_corrected_with_ground_truth": gt_count,
            "path": "data/processed/retrain_ready.csv"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
