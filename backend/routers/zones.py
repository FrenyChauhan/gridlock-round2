"""
backend/routers/zones.py
=========================
GET  /zones/                  — list all zones (filtered by region/tier)
GET  /zones/heatmap           — heatmap JSON (Red+Amber only)
GET  /zones/unassigned-red    — Red tier zones with no assigned team
GET  /zones/{zone_id}         — single zone detail
"""

from __future__ import annotations

import math
from typing import Optional, List
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth import get_current_user, get_station_filter
from backend import database as db
from backend.models import Zone

router = APIRouter(prefix="/zones", tags=["Zones"])


def _apply_region_filter(df: pd.DataFrame, user: dict) -> pd.DataFrame:
    """Filter rows to the stations this user is allowed to see."""
    stations = get_station_filter(user)
    if stations is None:
        return df   # superadmin / all
    if not stations:
        return df   # empty list = no filter
    if "dominant_police_station" in df.columns:
        return df[df["dominant_police_station"].isin(stations)]
    return df


def _team_for_zone(cluster_id: int, time_band: str) -> Optional[str]:
    mask = (
        (db.df_assignments["cluster_id"] == cluster_id) &
        (db.df_assignments["time_band"]  == time_band) &
        (db.df_assignments["status"].isin(["predicted", "assigned", "enroute", "onsite"]))
    )
    rows = db.df_assignments[mask]
    if rows.empty:
        return None
    return str(rows.iloc[-1]["team_id"])


def _assignment_status_for_zone(cluster_id: int, time_band: str) -> Optional[str]:
    mask = (
        (db.df_assignments["cluster_id"] == cluster_id) &
        (db.df_assignments["time_band"]  == time_band)
    )
    rows = db.df_assignments[mask]
    if rows.empty:
        return None
    return str(rows.iloc[-1]["status"])


def _zone_id_str(cluster_id: int, time_band: str) -> str:
    return f"ZONE-{cluster_id:04d}-{time_band}"


def _get_zone_dict(row: pd.Series) -> dict:
    """Convert a priority DataFrame row to a Zone dict."""
    cid = int(row["cluster_id"])
    tband = str(row["time_band"])
    
    # Merge region info if needed
    station = str(row.get("dominant_police_station", "Unknown"))
    
    # Find region for station
    from backend.auth import REGION_STATIONS
    region_val = None
    for r, st_list in REGION_STATIONS.items():
        if station in st_list:
            region_val = r
            break
            
    return {
        "zone_id": _zone_id_str(cid, tband),
        "cluster_id": cid,
        "centroid_lat": float(row["centroid_lat"]) if pd.notna(row.get("centroid_lat")) else None,
        "centroid_lon": float(row["centroid_lon"]) if pd.notna(row.get("centroid_lon")) else None,
        "tier": str(row["tier"]),
        "priority_score": float(row["final_priority_score"]),
        "cii_score": float(row["cii_score"]) if pd.notna(row.get("cii_score")) else None,
        "predicted_violations": float(row.get("predicted_violations", row.get("buffered_forecast", 0.0))),
        "buffered_forecast": float(row["buffered_forecast"]) if pd.notna(row.get("buffered_forecast")) else None,
        "time_band": tband,
        "volatility_class": str(row["volatility_class"]) if pd.notna(row.get("volatility_class")) else None,
        "confidence_level": str(row["confidence_level"]) if pd.notna(row.get("confidence_level")) else None,
        "dominant_station": station,
        "region": region_val,
        "assigned_team_id": _team_for_zone(cid, tband),
        "assignment_status": _assignment_status_for_zone(cid, tband),
    }


def _distance_km(lat1, lon1, lat2, lon2):
    """Haversine formula for distance between coords."""
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


@router.get("/", response_model=List[Zone], summary="List zones with filters")
def list_zones(
    tier: Optional[str] = Query(None, description="Red, Amber, or Green"),
    time_band: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    station: Optional[str] = Query(None),
    confidence_level: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    df = _apply_region_filter(db.df_priority, user)

    if tier:
        df = df[df["tier"].str.lower() == tier.lower()]
    if time_band:
        df = df[df["time_band"] == time_band]
    if station:
        df = df[df["dominant_police_station"] == station]
    if confidence_level:
        df = df[df["confidence_level"] == confidence_level]
        
    if region and "dominant_police_station" in df.columns:
        from backend.auth import REGION_STATIONS
        allowed_stations = REGION_STATIONS.get(region, [])
        df = df[df["dominant_police_station"].isin(allowed_stations)]

    df = df.sort_values("final_priority_score", ascending=False)
    
    return [_get_zone_dict(row) for _, row in df.iterrows()]


@router.get("/heatmap", summary="Heatmap data for map widget")
def heatmap(
    user: dict = Depends(get_current_user),
):
    """Returns heatmap_data.json filtered by region."""
    data = db.get_heatmap_for_bands(None)
    stations = get_station_filter(user)
    
    if stations:
        filtered = {}
        for band, points in data.items():
            filtered[band] = [p for p in points if p.get("station") in stations]
        return filtered

    return data


@router.get("/heatmap-points", summary="Heatmap points for leaflet.heat")
def heatmap_points(user: dict = Depends(get_current_user)):
    import os
    csv_path = os.path.join(os.path.dirname(__file__), "../../data/processed/clustered_violations.csv")
    if not os.path.exists(csv_path):
        return []
        
    df = pd.read_csv(csv_path)
    
    stations = get_station_filter(user)
    if stations and "police_station" in df.columns:
        df = df[df["police_station"].isin(stations)]
        
    if len(df) > 5000:
        df = df.sample(5000, random_state=42)
        
    results = []
    for _, row in df.iterrows():
        lat = float(row["latitude"]) if pd.notna(row.get("latitude")) else None
        lng = float(row["longitude"]) if pd.notna(row.get("longitude")) else None
        if lat is None or lng is None:
            continue
        intensity = float(row.get("combined_severity_norm", 0.5))
        results.append({
            "lat": lat,
            "lng": lng,
            "intensity": max(0.0, min(1.0, intensity))
        })
    return results


@router.get("/unassigned-red", summary="Red tier zones with no assigned team")
def unassigned_red(user: dict = Depends(get_current_user)):
    df = _apply_region_filter(db.df_priority, user)
    red_df = df[df["tier"] == "Red"].sort_values("final_priority_score", ascending=False)
    
    results = []
    
    for _, row in red_df.iterrows():
        cid = int(row["cluster_id"])
        tband = str(row["time_band"])
        
        assigned_team = _team_for_zone(cid, tband)
        if assigned_team is not None:
            continue
            
        z_dict = _get_zone_dict(row)
        
        # Find recommended team (nearest available)
        best_team = None
        min_dist = float('inf')
        
        available_teams = db.df_teams[db.df_teams["status"] == "available"]
        for _, t_row in available_teams.iterrows():
            t_id = str(t_row["team_id"])
            t_station = str(t_row.get("station", ""))
            
            # Distance approximation: if same station, dist=0
            if t_station == row.get("dominant_police_station"):
                dist = 0
            else:
                dist = 10  # Arbitrary penalty for different station if we lack coords
                
            if dist < min_dist:
                min_dist = dist
                best_team = t_id
                
        z_dict["recommended_team"] = best_team
        results.append(z_dict)
        
    return results


@router.get("/{zone_id}", summary="Single zone full detail")
def zone_detail(zone_id: str, user: dict = Depends(get_current_user)):
    # zone_id format: ZONE-0010-early_morning
    parts = zone_id.split("-")
    if len(parts) >= 3 and parts[0] == "ZONE":
        cluster_id = int(parts[1])
        time_band = "-".join(parts[2:])
    else:
        raise HTTPException(status_code=400, detail="Invalid zone_id format. Expected ZONE-XXXX-time_band")
        
    zone = db.get_zone_priority(cluster_id, time_band)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found.")
        
    # Region check
    stations = get_station_filter(user)
    if stations and zone.get("dominant_police_station") not in stations:
        raise HTTPException(status_code=403, detail="Zone not in your region.")

    # Base dict
    z_dict = _get_zone_dict(pd.Series(zone))
    
    # False positive rate
    outcomes = db.df_outcomes[
        (db.df_outcomes["cluster_id"] == cluster_id) & 
        (db.df_outcomes["time_band"] == time_band)
    ]
    
    fp_rate = 0.0
    if not outcomes.empty:
        fp_rate = float((outcomes["outcome_type"] == "false_positive").mean())
        
    z_dict["false_positive_rate"] = fp_rate
    
    # Assignment history (last 5)
    assignments = db.df_assignments[
        (db.df_assignments["cluster_id"] == cluster_id) & 
        (db.df_assignments["time_band"] == time_band)
    ].sort_values("assigned_at", ascending=False).head(5)
    
    history = []
    for _, a in assignments.iterrows():
        a_id = a.get("assignment_id")
        # find matching outcome if any
        o_row = outcomes[outcomes["assignment_id"] == a_id]
        outcome_type = str(o_row.iloc[0]["outcome_type"]) if not o_row.empty else None
        
        history.append({
            "assignment_id": str(a_id),
            "team_id": str(a.get("team_id")),
            "assigned_at": str(a.get("assigned_at")),
            "status": str(a.get("status")),
            "outcome_type": outcome_type,
        })
        
    z_dict["assignment_history"] = history
    
    # Trend explanation
    vc = z_dict["volatility_class"]
    if vc == "volatile_growing":
        z_dict["trend_explanation"] = "Highly erratic violations with an overall upward growth trend."
    elif vc == "volatile_stable":
        z_dict["trend_explanation"] = "Violations spike unpredictably but long-term average is flat."
    elif vc == "stable_growing":
        z_dict["trend_explanation"] = "Consistent violations increasing steadily over time."
    else:
        z_dict["trend_explanation"] = "Stable violations with no significant growth trend."

    return z_dict
