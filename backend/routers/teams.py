"""
backend/routers/teams.py
=========================
GET   /teams/
GET   /teams/{team_id}
POST  /teams/add
PATCH /teams/{team_id}/status
GET   /teams/substitution-available
GET   /teams/availability-timeline
POST  /teams/bulk-update-status
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from typing import Optional, List

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.auth import get_current_user, require_control_room, get_station_filter
from backend import database as db
from backend.models import Team

router = APIRouter(prefix="/teams", tags=["Teams"])


# ==================================================================
# REQUEST MODELS
# ==================================================================

class TeamAddRequest(BaseModel):
    team_id: str
    officer_names: List[str]
    vehicle_type: str
    station: str
    category: str


class TeamStatusPatch(BaseModel):
    status: str
    reason: Optional[str] = None


class BulkStatusUpdate(BaseModel):
    current_status: str
    new_status: str


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


def _apply_region_filter(df: pd.DataFrame, user: dict) -> pd.DataFrame:
    stations = get_station_filter(user)
    if stations is None:
        return df
    if not stations:
        return pd.DataFrame(columns=df.columns)
    if "station" in df.columns:
        return df[df["station"].isin(stations)]
    return df


def _parse_timestamp(val) -> Optional[datetime]:
    if pd.isna(val) or not val:
        return None
    try:
        if isinstance(val, str):
            return datetime.fromisoformat(val.replace("Z", "+00:00")).replace(tzinfo=None)
        return val
    except:
        return None


def _get_team_dict(row: pd.Series) -> dict:
    d = dict(row)
    
    # Parse list string for officer names
    officer_names = []
    if "officer_names" in d and pd.notna(d["officer_names"]):
        try:
            val = d["officer_names"]
            if isinstance(val, str):
                if val.startswith("["):
                    officer_names = json.loads(val.replace("'", '"'))
                else:
                    officer_names = [v.strip() for v in val.split(",")]
        except:
            officer_names = [str(d["officer_names"])]
            
    # Default category to primary if not present
    category = d.get("category", "primary")
    if pd.isna(category):
        category = "primary"
        
    return {
        "team_id": str(d["team_id"]),
        "officer_names": officer_names,
        "vehicle_type": str(d.get("vehicle_type")) if pd.notna(d.get("vehicle_type")) else None,
        "station": str(d.get("station", "Unknown")),
        "category": str(category),
        "status": str(d.get("status", "available")),
        "current_zone_id": str(d.get("current_zone")) if pd.notna(d.get("current_zone")) else None,
        "expected_free_at": _parse_timestamp(d.get("expected_free_at")),
        "last_updated": _parse_timestamp(d.get("last_updated")),
    }


# ==================================================================
# ENDPOINTS
# ==================================================================

@router.get("/", response_model=List[Team], summary="List all teams")
def list_teams(
    status: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    station: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    df = db.df_teams.copy()
    
    # Base region filter for control room
    df = _apply_region_filter(df, user)
    
    # Specific query filters
    if status:
        df = df[df["status"] == status]
    if category and "category" in df.columns:
        df = df[df["category"] == category]
    if station:
        df = df[df["station"] == station]
        
    if region and "station" in df.columns:
        from backend.auth import REGION_STATIONS
        allowed_stations = REGION_STATIONS.get(region, [])
        df = df[df["station"].isin(allowed_stations)]

    return [_get_team_dict(row) for _, row in df.iterrows()]


@router.get("/substitution-available", summary="Find backup teams")
def substitution_available(
    zone_id: Optional[str] = Query(None, description="Requesting zone to sort by proximity"),
    user: dict = Depends(get_current_user)
):
    df = _apply_region_filter(db.df_teams, user)
    
    if "category" in df.columns:
        df = df[(df["category"] == "substitution") & (df["status"] == "available")]
    else:
        df = pd.DataFrame(columns=df.columns)
        
    teams = [_get_team_dict(row) for _, row in df.iterrows()]
    
    # Sort by proximity if zone_id provided
    if zone_id and teams:
        parts = zone_id.split("-")
        if len(parts) >= 3 and parts[0] == "ZONE":
            cid = int(parts[1])
            tband = "-".join(parts[2:])
            
            zone = db.get_zone_priority(cid, tband)
            if zone:
                z_lat = float(zone.get("centroid_lat")) if pd.notna(zone.get("centroid_lat")) else None
                z_lon = float(zone.get("centroid_lon")) if pd.notna(zone.get("centroid_lon")) else None
                
                # We need station coords. In a real system, we'd lookup station coords. 
                # For now, approximate based on station name match
                z_station = zone.get("dominant_police_station")
                
                for t in teams:
                    if t["station"] == z_station:
                        t["distance_km"] = 0.0
                    else:
                        t["distance_km"] = 10.0 # penalty
                
                teams.sort(key=lambda x: x.get("distance_km", 999.0))
                
    return teams


@router.get("/availability-timeline", summary="Future team availability slots")
def availability_timeline(user: dict = Depends(require_control_room)):
    df = _apply_region_filter(db.df_teams, user)
    now = datetime.utcnow()
    
    # 4 hours in 30 min slots = 8 slots
    slots = []
    current_slot = now
    
    for i in range(8):
        slot_end = current_slot + timedelta(minutes=30)
        
        avail_count = int((df["status"] == "available").sum())
        returning_count = 0
        
        if "expected_free_at" in df.columns:
            for _, row in df[df["status"].isin(["assigned", "enroute", "onsite", "returning"])].iterrows():
                expected = _parse_timestamp(row.get("expected_free_at"))
                if expected and current_slot <= expected < slot_end:
                    returning_count += 1
                    
        slots.append({
            "time_slot": current_slot.strftime("%H:%M"),
            "available_count": avail_count,
            "returning_count": returning_count,
            "total_expected_available": avail_count + returning_count
        })
        
        current_slot = slot_end
        
    return slots


@router.get("/{team_id}", summary="Full team detail")
def team_detail(team_id: str, user: dict = Depends(get_current_user)):
    # Officers can only view their own
    if user["role"] == "officer" and user.get("team_id") != team_id:
        raise HTTPException(status_code=403, detail="You can only view your own team.")

    row = db.df_teams[db.df_teams["team_id"] == team_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="Team not found.")
        
    t_dict = _get_team_dict(row.iloc[0])
    
    # Current assignment
    assign_df = db.df_assignments[
        (db.df_assignments["team_id"] == team_id) & 
        (db.df_assignments["status"].isin(["predicted", "assigned", "enroute", "onsite"]))
    ]
    t_dict["current_assignment"] = assign_df.iloc[-1].to_dict() if not assign_df.empty else None
    
    # History (last 10 from outcomes)
    outcomes = db.df_outcomes[db.df_outcomes["officer_id"] == team_id].sort_values("created_at", ascending=False).head(10)
    
    history = []
    for _, o in outcomes.iterrows():
        history.append({
            "assignment_id": str(o["assignment_id"]),
            "zone_id": str(o.get("zone_id", f"ZONE-{o['cluster_id']:04d}-{o['time_band']}")),
            "outcome_type": str(o["outcome_type"]),
            "actual_violations_found": float(o["actual_violations_found"]),
            "response_time_minutes": float(o["response_time_minutes"]) if pd.notna(o.get("response_time_minutes")) else None,
            "resolved_at": str(o["resolved_at"])
        })
    t_dict["assignment_history"] = history
    
    # Performance stats
    if not outcomes.empty:
        confirmed = (outcomes["outcome_type"] == "violation_confirmed").mean()
        t_dict["confirmed_rate"] = float(confirmed)
        
        if "response_time_minutes" in outcomes.columns:
            resp = outcomes["response_time_minutes"].dropna()
            t_dict["avg_response_time"] = float(resp.mean()) if not resp.empty else None
    else:
        t_dict["confirmed_rate"] = 0.0
        t_dict["avg_response_time"] = None
        
    return t_dict


@router.post("/add", summary="Add new team")
def add_team(body: TeamAddRequest, user: dict = Depends(require_control_room)):
    df = db.df_teams
    if not df[df["team_id"] == body.team_id].empty:
        raise HTTPException(status_code=409, detail=f"Team {body.team_id} already exists.")
        
    now_str = datetime.utcnow().isoformat() + "Z"
    
    new_row = {
        "team_id": body.team_id,
        "officer_names": json.dumps(body.officer_names),
        "vehicle_type": body.vehicle_type,
        "station": body.station,
        "category": body.category,
        "status": "available",
        "last_updated": now_str
    }
    
    # Add any missing columns to match schema
    for col in df.columns:
        if col not in new_row:
            new_row[col] = None
            
    updated_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    db.save_teams(updated_df)
    
    return {"status": "added", "team_id": body.team_id}


@router.patch("/{team_id}/status", summary="Update team status state machine")
def patch_team_status(
    team_id: str, 
    body: TeamStatusPatch, 
    user: dict = Depends(require_control_room)
):
    """
    Valid transitions:
      available → assigned
      assigned → enroute
      enroute → onsite
      onsite → returning
      returning → available
      any → standby
      any → off_duty
    """
    df = db.df_teams
    mask = df["team_id"] == team_id
    if not mask.any():
        raise HTTPException(status_code=404, detail="Team not found.")
        
    current = df[mask].iloc[0]
    curr_status = current.get("status", "available")
    new_status = body.status
    
    # State machine validation
    valid = False
    if new_status in ["standby", "off_duty"]:
        valid = True
    elif curr_status == "available" and new_status == "assigned":
        valid = True
    elif curr_status == "assigned" and new_status == "enroute":
        valid = True
    elif curr_status == "enroute" and new_status == "onsite":
        valid = True
    elif curr_status == "onsite" and new_status == "returning":
        valid = True
    elif curr_status == "returning" and new_status == "available":
        valid = True
        
    if not valid:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status transition from {curr_status} to {new_status}"
        )
        
    now = datetime.utcnow()
    now_str = now.isoformat() + "Z"
    
    updated_df = df.copy()
    updated_df.loc[mask, "status"] = new_status
    updated_df.loc[mask, "last_updated"] = now_str
    
    # expected_free_at logic
    if new_status == "returning":
        free_at = (now + timedelta(minutes=15)).isoformat() + "Z"
        updated_df.loc[mask, "expected_free_at"] = free_at
    elif new_status in ["available", "standby", "off_duty"]:
        updated_df.loc[mask, "expected_free_at"] = None
        
    db.save_teams(updated_df)
    
    # Sync assignment status if applicable
    assign_df = db.df_assignments
    a_mask = (assign_df["team_id"] == team_id) & (assign_df["status"].isin(["predicted", "assigned", "enroute", "onsite"]))
    if a_mask.any():
        upd_assign = assign_df.copy()
        if new_status == "enroute":
            upd_assign.loc[a_mask, "status"] = "enroute"
        elif new_status == "onsite":
            upd_assign.loc[a_mask, "status"] = "onsite"
            upd_assign.loc[a_mask, "arrived_at"] = now_str
        elif new_status == "returning":
            upd_assign.loc[a_mask, "status"] = "resolved"
            upd_assign.loc[a_mask, "resolved_at"] = now_str
        elif new_status == "available":
            upd_assign.loc[a_mask, "status"] = "cleared"
            
        db.save_assignments(upd_assign)
        
    return {
        "team_id": team_id,
        "old_status": curr_status,
        "new_status": new_status,
        "updated_at": now_str
    }


@router.post("/bulk-update-status", summary="Shift changeover bulk update")
def bulk_update_status(body: BulkStatusUpdate, user: dict = Depends(require_control_room)):
    df = db.df_teams
    stations = get_station_filter(user)
    
    mask = df["status"] == body.current_status
    if stations:
        mask = mask & df["station"].isin(stations)
        
    updated_count = int(mask.sum())
    
    if updated_count > 0:
        updated_df = df.copy()
        now_str = datetime.utcnow().isoformat() + "Z"
        
        updated_df.loc[mask, "status"] = body.new_status
        updated_df.loc[mask, "last_updated"] = now_str
        
        if body.new_status in ["available", "standby", "off_duty"]:
            updated_df.loc[mask, "expected_free_at"] = None
            updated_df.loc[mask, "current_zone"] = None
            
        db.save_teams(updated_df)
        
    return {
        "updated_count": updated_count,
        "from_status": body.current_status,
        "to_status": body.new_status
    }
