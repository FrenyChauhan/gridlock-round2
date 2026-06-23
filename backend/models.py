"""
backend/models.py
==================
Pydantic request/response models for Gridlock 2.0 API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

# ==================================================================
# ZONE
# ==================================================================

class Zone(BaseModel):
    zone_id: str
    cluster_id: int
    centroid_lat: Optional[float]
    centroid_lon: Optional[float]
    tier: str  # red/amber/green
    priority_score: float
    cii_score: Optional[float]
    predicted_violations: float
    buffered_forecast: Optional[float]
    time_band: str
    volatility_class: Optional[str]
    confidence_level: Optional[str]
    dominant_station: str
    region: Optional[str]
    assigned_team_id: Optional[str] = None
    assignment_status: Optional[str] = None


# ==================================================================
# TEAM
# ==================================================================

class Team(BaseModel):
    team_id: str
    officer_names: List[str] = []
    vehicle_type: Optional[str] = None
    station: str
    region: Optional[str] = None
    category: str = Field(..., description="primary/substitution/reserve")
    status: str = Field(
        ...,
        description="available/assigned/on_site/needs_backup/returning/standby/off_duty"
    )
    current_zone_id: Optional[str] = None
    current_assignment_id: Optional[str] = None
    expected_free_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None


# ==================================================================
# ASSIGNMENT
# ==================================================================

class Assignment(BaseModel):
    assignment_id: str
    team_id: str
    zone_id: str
    cluster_id: int
    centroid_lat: Optional[float]
    centroid_lon: Optional[float]
    dominant_station: str
    tier: str
    priority_score: float
    predicted_violations: float
    time_band: str
    status: str = Field(
        ...,
        description="predicted/assigned/enroute/onsite/resolved/cleared/needs_backup"
    )
    assigned_at: Optional[datetime] = None
    arrived_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    expected_free_at: Optional[datetime] = None
    outcome_type: Optional[str] = None  # null until resolved


# ==================================================================
# ENFORCEMENT OUTCOME
# ==================================================================

class EnforcementOutcome(BaseModel):
    outcome_id: str
    assignment_id: str
    zone_id: str
    cluster_id: int
    time_band: str
    predicted_violations: float
    actual_violations_found: float
    outcome_type: str = Field(
        ...,
        description="violation_confirmed/false_positive/needs_backup/resolved"
    )
    officer_id: str
    arrived_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    response_time_minutes: Optional[float] = None


# ==================================================================
# DASHBOARD STATS
# ==================================================================

class DashboardStats(BaseModel):
    total_red_zones: int
    total_amber_zones: int
    teams_available: int
    teams_assigned: int
    teams_on_site: int
    teams_standby: int
    unassigned_red_zones: int
    volatile_growing_active: int
    false_positive_rate_today: float
    avg_response_time_minutes: Optional[float] = None
    region: Optional[str] = None


# ==================================================================
# TEAM AVAILABILITY FORECAST
# ==================================================================

class RecommendedZone(BaseModel):
    zone_id: str
    cluster_id: int
    priority_score: float
    distance_km: Optional[float] = None

class TeamAvailabilityForecast(BaseModel):
    team_id: str
    current_status: str
    zone_id: Optional[str] = None
    expected_free_at: Optional[datetime] = None
    minutes_until_free: Optional[float] = None
    recommended_next_zone: Optional[RecommendedZone] = None


# ==================================================================
# AUTHENTICATION
# ==================================================================

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    region: Optional[str]
    team_id: Optional[str]
    expires_in: int

class UserInfo(BaseModel):
    user_id: str
    email: str
    role: str
    region: Optional[str]
    team_id: Optional[str]
    full_name: str
