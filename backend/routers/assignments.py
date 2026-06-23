"""
backend/routers/assignments.py
================================
GET  /assignments/
GET  /assignments/{assignment_id}
POST /assignments/create
POST /assignments/{assignment_id}/status-update
GET  /assignments/active
GET  /assignments/history
"""

from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.auth import get_current_user, require_control_room, get_station_filter
from backend import database as db
from backend.models import Assignment

router = APIRouter(prefix="/assignments", tags=["Assignments"])


# ==================================================================
# REQUEST MODELS
# ==================================================================

class CreateAssignmentBody(BaseModel):
    zone_id: str
    team_id: str
    priority_override: Optional[float] = None
    notes: Optional[str] = None


class StatusUpdateBody(BaseModel):
    new_status: str
    notes: Optional[str] = None


# ==================================================================
# HELPERS
# ==================================================================

def _distance_km(lat1, lon1, lat2, lon2):
    if any(x is None or math.isnan(x) for x in [lat1, lon1, lat2, lon2]):
        return 999.0
    R = 6371  # km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


def _apply_region_filter(df: pd.DataFrame, user: dict, station_col="dominant_station") -> pd.DataFrame:
    stations = get_station_filter(user)
    if stations is None:
        return df
    if not stations:
        return pd.DataFrame(columns=df.columns)
    if station_col in df.columns:
        return df[df[station_col].isin(stations)]
    return df


def _parse_zone_id(zone_id: str):
    parts = zone_id.split("-")
    if len(parts) >= 3 and parts[0] == "ZONE":
        cluster_id = int(parts[1])
        time_band = "-".join(parts[2:])
        return cluster_id, time_band
    raise ValueError("Invalid zone_id format")


def _parse_timestamp(val) -> Optional[datetime]:
    if pd.isna(val) or not val:
        return None
    try:
        if isinstance(val, str):
            return datetime.fromisoformat(val.replace("Z", "+00:00")).replace(tzinfo=None)
        return val
    except:
        return None


def _get_assignment_dict(row: pd.Series) -> dict:
    d = dict(row)
    cid = int(d["cluster_id"])
    tband = str(d["time_band"])
    zone_id = d.get("zone_id", f"ZONE-{cid:04d}-{tband}")
    
    return {
        "assignment_id": str(d["assignment_id"]),
        "team_id": str(d["team_id"]),
        "zone_id": str(zone_id),
        "cluster_id": cid,
        "centroid_lat": float(d["centroid_lat"]) if pd.notna(d.get("centroid_lat")) else None,
        "centroid_lon": float(d["centroid_lon"]) if pd.notna(d.get("centroid_lon")) else None,
        "dominant_station": str(d.get("dominant_station", "Unknown")),
        "tier": str(d.get("tier", "Green")),
        "priority_score": float(d.get("priority_score", 0.0)),
        "predicted_violations": float(d.get("predicted_violations", d.get("buffered_forecast", 0.0))),
        "time_band": tband,
        "status": str(d.get("status", "predicted")),
        "assigned_at": _parse_timestamp(d.get("assigned_at")),
        "arrived_at": _parse_timestamp(d.get("arrived_at")),
        "resolved_at": _parse_timestamp(d.get("resolved_at")),
        "expected_free_at": _parse_timestamp(d.get("expected_free_at")),
        "outcome_type": str(d["outcome_type"]) if pd.notna(d.get("outcome_type")) else None,
    }


# ==================================================================
# ENDPOINTS
# ==================================================================

@router.get("/", summary="List assignments")
def list_assignments(
    status: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    team_id: Optional[str] = Query(None),
    date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    user: dict = Depends(get_current_user),
):
    df = db.df_assignments.copy()

    if user["role"] == "officer":
        df = df[df["team_id"] == user.get("team_id", "")]
    else:
        df = _apply_region_filter(df, user, station_col="dominant_station")
        if region and "dominant_station" in df.columns:
            from backend.auth import REGION_STATIONS
            allowed = REGION_STATIONS.get(region, [])
            df = df[df["dominant_station"].isin(allowed)]

    if status:
        df = df[df["status"] == status]
    if tier and "tier" in df.columns:
        df = df[df["tier"] == tier]
    if team_id:
        df = df[df["team_id"] == team_id]
        
    if date and "assigned_at" in df.columns:
        # Simple string prefix match for date if ISO format
        df = df[df["assigned_at"].astype(str).str.startswith(date)]

    return [_get_assignment_dict(row) for _, row in df.iterrows()]


@router.get("/active", summary="All active assignments grouped")
def active_assignments(user: dict = Depends(get_current_user)):
    df = _apply_region_filter(db.df_assignments, user, station_col="dominant_station")
    
    active_df = df[df["status"].isin(["assigned", "enroute", "onsite", "needs_backup"])]
    
    result = {
        "active": [],
        "pending_backup": [],
        "completing_soon": []
    }
    
    now = datetime.utcnow()
    soon_threshold = now + timedelta(minutes=30)
    
    for _, row in active_df.iterrows():
        a_dict = _get_assignment_dict(row)
        
        if a_dict["status"] == "needs_backup":
            result["pending_backup"].append(a_dict)
        else:
            result["active"].append(a_dict)
            
        exp_free = a_dict.get("expected_free_at")
        if exp_free and exp_free <= soon_threshold:
            result["completing_soon"].append(a_dict)
            
    return result


@router.get("/history", summary="Past 7 days resolved/cleared")
def assignment_history(user: dict = Depends(get_current_user)):
    df = _apply_region_filter(db.df_assignments, user, station_col="dominant_station")
    
    now = datetime.utcnow()
    seven_days_ago = (now - timedelta(days=7)).isoformat()
    
    # Filter resolved/cleared and in last 7 days
    hist_df = df[
        (df["status"].isin(["resolved", "cleared"])) & 
        (df["resolved_at"].astype(str) >= seven_days_ago)
    ]
    
    outcomes = db.df_outcomes
    results = []
    
    for _, row in hist_df.iterrows():
        a_dict = _get_assignment_dict(row)
        a_id = a_dict["assignment_id"]
        
        # Join outcome info
        o_row = outcomes[outcomes["assignment_id"] == a_id]
        if not o_row.empty:
            a_dict["outcome_type"] = str(o_row.iloc[0]["outcome_type"])
            a_dict["response_time_minutes"] = float(o_row.iloc[0]["response_time_minutes"]) if pd.notna(o_row.iloc[0].get("response_time_minutes")) else None
            
        results.append(a_dict)
        
    # Sort descending by resolved_at
    results.sort(key=lambda x: str(x.get("resolved_at", "")), reverse=True)
    return results


@router.get("/{assignment_id}", summary="Full detail of single assignment")
def get_assignment_detail(assignment_id: str, user: dict = Depends(get_current_user)):
    df = db.df_assignments
    row = df[df["assignment_id"] == assignment_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="Assignment not found")
        
    record = _get_assignment_dict(row.iloc[0])
    
    if user["role"] == "officer" and record.get("team_id") != user.get("team_id"):
        raise HTTPException(status_code=403, detail="Access denied.")
        
    # Join zone info
    cid = record["cluster_id"]
    tband = record["time_band"]
    zone = db.get_zone_priority(cid, tband)
    if zone:
        record["zone"] = {
            "volatility_class": zone.get("volatility_class"),
            "confidence_level": zone.get("confidence_level"),
            "cii_score": zone.get("cii_score"),
            "trend_slope": zone.get("trend_slope")
        }
        
    # Join team info
    team = db.get_team(record["team_id"])
    if team:
        record["team"] = {
            "station": team.get("station"),
            "category": team.get("category"),
            "vehicle_type": team.get("vehicle_type"),
            "officer_names": team.get("officer_names")
        }
        
    # Join outcome if resolved
    if record["status"] in ["resolved", "cleared"]:
        o_row = db.df_outcomes[db.df_outcomes["assignment_id"] == assignment_id]
        if not o_row.empty:
            record["outcome"] = o_row.iloc[0].to_dict()

    return record


@router.post("/create", summary="Create new assignment")
def create_assignment(body: CreateAssignmentBody, user: dict = Depends(require_control_room)):
    try:
        cid, tband = _parse_zone_id(body.zone_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid zone_id format")

    # Validate team
    team = db.get_team(body.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if team.get("status") not in ["available", "standby"]:
        raise HTTPException(status_code=400, detail=f"Team is {team.get('status')}")

    # Validate zone in region
    zone = db.get_zone_priority(cid, tband)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
        
    stations = get_station_filter(user)
    if stations and zone.get("dominant_police_station") not in stations:
        raise HTTPException(status_code=403, detail="Zone not in your region")
        
    # Validate zone not already actively assigned
    active = db.df_assignments[
        (db.df_assignments["cluster_id"] == cid) & 
        (db.df_assignments["time_band"] == tband) &
        (db.df_assignments["status"].isin(["assigned", "enroute", "onsite"]))
    ]
    if not active.empty:
        raise HTTPException(status_code=409, detail="Zone already actively assigned")

    # Create assignment
    assign_id = f"A{str(uuid.uuid4())[:8].upper()}"
    now_str = datetime.utcnow().isoformat() + "Z"
    
    score = body.priority_override if body.priority_override is not None else zone.get("final_priority_score")
    
    new_row = {
        "assignment_id": assign_id,
        "team_id": body.team_id,
        "zone_id": body.zone_id,
        "cluster_id": cid,
        "centroid_lat": zone.get("centroid_lat"),
        "centroid_lon": zone.get("centroid_lon"),
        "dominant_station": zone.get("dominant_police_station"),
        "tier": zone.get("tier"),
        "priority_score": score,
        "predicted_violations": zone.get("buffered_forecast", zone.get("predicted_violations")),
        "time_band": tband,
        "status": "assigned",
        "assigned_at": now_str,
        "notes": body.notes
    }

    # Flush assignment
    import pandas as pd
    for col in db.df_assignments.columns:
        if col not in new_row:
            new_row[col] = None
    upd_assignments = pd.concat([db.df_assignments, pd.DataFrame([new_row])], ignore_index=True)
    db.save_assignments(upd_assignments)
    
    # Update team status
    upd_teams = db.df_teams.copy()
    mask = upd_teams["team_id"] == body.team_id
    upd_teams.loc[mask, "status"] = "assigned"
    upd_teams.loc[mask, "current_zone"] = body.zone_id
    upd_teams.loc[mask, "current_assignment_id"] = assign_id
    db.save_teams(upd_teams)
    
    return {
        "message": "Assignment created successfully",
        "assignment_id": assign_id,
        "centroid_lat": new_row["centroid_lat"],
        "centroid_lon": new_row["centroid_lon"]
    }


@router.post("/{assignment_id}/status-update", summary="Update assignment status flow")
def update_assignment_status(assignment_id: str, body: StatusUpdateBody, user: dict = Depends(get_current_user)):
    df = db.df_assignments
    mask = df["assignment_id"] == assignment_id
    if not mask.any():
        raise HTTPException(status_code=404, detail="Assignment not found")
        
    record = df[mask].iloc[0]
    team_id = str(record["team_id"])
    
    if user["role"] == "officer" and team_id != user.get("team_id"):
        raise HTTPException(status_code=403, detail="You can only update your own assignment")
        
    curr_status = record.get("status", "assigned")
    new_status = body.new_status
    now = datetime.utcnow()
    now_str = now.isoformat() + "Z"
    
    upd_assignments = df.copy()
    upd_teams = db.df_teams.copy()
    t_mask = upd_teams["team_id"] == team_id
    
    feedback_prompt = False
    new_assignment = None
    
    if curr_status == "assigned" and new_status == "enroute":
        upd_assignments.loc[mask, "status"] = "enroute"
        # upd_assignments.loc[mask, "assigned_at"] = now_str # usually set on creation, but we can set here too
        upd_teams.loc[t_mask, "status"] = "enroute"
        
    elif curr_status == "enroute" and new_status == "onsite":
        upd_assignments.loc[mask, "status"] = "onsite"
        upd_assignments.loc[mask, "arrived_at"] = now_str
        upd_teams.loc[t_mask, "status"] = "onsite"
        
        # Compute expected free at (default 45 min)
        # Check team history for avg
        outcomes = db.df_outcomes[db.df_outcomes["officer_id"] == team_id]
        avg_res = 45.0
        if not outcomes.empty and "response_time_minutes" in outcomes.columns:
            val = outcomes["response_time_minutes"].mean()
            if not math.isnan(val):
                avg_res = float(val)
                
        free_at = (now + timedelta(minutes=avg_res)).isoformat() + "Z"
        upd_assignments.loc[mask, "expected_free_at"] = free_at
        upd_teams.loc[t_mask, "expected_free_at"] = free_at
        
    elif curr_status == "onsite" and new_status == "needs_backup":
        upd_assignments.loc[mask, "status"] = "needs_backup"
        upd_teams.loc[t_mask, "status"] = "needs_backup"
        
        # Find nearest substitution team
        z_lat = record.get("centroid_lat")
        z_lon = record.get("centroid_lon")
        
        sub_teams = upd_teams[(upd_teams["category"] == "substitution") & (upd_teams["status"] == "available")]
        best_team = None
        min_dist = float('inf')
        
        for _, st in sub_teams.iterrows():
            st_station = st.get("station")
            # Fake distance if no coords: 0 if same station else 10
            dist = 0 if st_station == record.get("dominant_station") else 10
            if dist < min_dist:
                min_dist = dist
                best_team = str(st["team_id"])
                
        if best_team:
            # Auto create new assignment
            new_a_id = f"A{str(uuid.uuid4())[:8].upper()}"
            new_row = dict(record)
            new_row["assignment_id"] = new_a_id
            new_row["team_id"] = best_team
            new_row["status"] = "assigned"
            new_row["assigned_at"] = now_str
            new_row["arrived_at"] = None
            new_row["resolved_at"] = None
            new_row["expected_free_at"] = None
            new_row["notes"] = "AUTO-DISPATCH: Backup requested"
            
            import pandas as pd
            for col in upd_assignments.columns:
                if col not in new_row:
                    new_row[col] = None
            upd_assignments = pd.concat([upd_assignments, pd.DataFrame([new_row])], ignore_index=True)
            
            # update sub team
            st_mask = upd_teams["team_id"] == best_team
            upd_teams.loc[st_mask, "status"] = "assigned"
            upd_teams.loc[st_mask, "current_zone"] = record.get("zone_id")
            
            new_assignment = {"assignment_id": new_a_id, "team_id": best_team}
            
    elif curr_status in ["onsite", "needs_backup"] and new_status in ["resolved", "cleared"]:
        upd_assignments.loc[mask, "status"] = new_status
        upd_assignments.loc[mask, "resolved_at"] = now_str
        
        # Free the team
        upd_teams.loc[t_mask, "status"] = "available"
        upd_teams.loc[t_mask, "current_zone"] = None
        upd_teams.loc[t_mask, "expected_free_at"] = None
        
        feedback_prompt = True
        
    else:
        raise HTTPException(status_code=400, detail=f"Invalid status transition from {curr_status} to {new_status}")
        
    db.save_assignments(upd_assignments)
    db.save_teams(upd_teams)
    
    return {
        "assignment_id": assignment_id,
        "old_status": curr_status,
        "new_status": new_status,
        "trigger_feedback_prompt": feedback_prompt,
        "backup_dispatched": new_assignment
    }
