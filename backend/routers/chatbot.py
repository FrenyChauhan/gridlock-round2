"""
backend/routers/chatbot.py
===========================
POST /chatbot/query   — LLM-powered queries for Control Room
"""

from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import pandas as pd

from backend.auth import require_control_room, get_station_filter
from backend import database as db

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

class ChatbotQuery(BaseModel):
    question: str


def _build_context(user: dict) -> dict:
    """Builds the live data context payload based on the user's region."""
    stations = get_station_filter(user)
    
    # Base DataFrames
    priority_df = db.df_priority
    teams_df = db.df_teams
    outcomes_df = db.df_outcomes
    assignments_df = db.df_assignments
    
    if stations:
        priority_df = priority_df[priority_df["dominant_police_station"].isin(stations)]
        teams_df = teams_df[teams_df["station"].isin(stations)]
        # Filter outcomes/assignments by team_id
        valid_teams = teams_df["team_id"].tolist()
        if not outcomes_df.empty:
            outcomes_df = outcomes_df[outcomes_df["officer_id"].isin(valid_teams)]
        if not assignments_df.empty:
            assignments_df = assignments_df[assignments_df["team_id"].isin(valid_teams)]
            
    # 1. Top 10 unassigned red zones
    red_df = priority_df[priority_df["tier"] == "Red"].sort_values("final_priority_score", ascending=False)
    active_assigns = assignments_df[assignments_df["status"].isin(["predicted", "assigned", "enroute", "onsite"])] if not assignments_df.empty else pd.DataFrame()
    assigned_keys = set()
    if not active_assigns.empty:
        assigned_keys = set(zip(active_assigns["cluster_id"], active_assigns["time_band"]))
        
    top_unassigned = []
    for _, row in red_df.iterrows():
        if (row["cluster_id"], row["time_band"]) not in assigned_keys:
            top_unassigned.append({
                "zone_id": f"ZONE-{row['cluster_id']:04d}-{row['time_band']}",
                "station": row.get("dominant_police_station"),
                "score": round(float(row["final_priority_score"]), 2),
                "volatility": row.get("volatility_class")
            })
            if len(top_unassigned) >= 10:
                break
                
    # 2. Team availability summary
    team_status = teams_df["status"].value_counts().to_dict() if not teams_df.empty else {}
    
    # 3. Today's false positive zones
    fp_zones = []
    if not outcomes_df.empty and "outcome_type" in outcomes_df.columns:
        fp_df = outcomes_df[outcomes_df["outcome_type"] == "false_positive"]
        if not fp_df.empty:
            fp_counts = fp_df["cluster_id"].value_counts().head(5).to_dict()
            fp_zones = [{"cluster_id": k, "fp_count": v} for k, v in fp_counts.items()]
            
    # 4. Volatile-growing zones
    vg_count = int((priority_df["volatility_class"] == "volatile_growing").sum()) if "volatility_class" in priority_df.columns else 0
    
    # 5. Recent outcomes summary
    recent_outcomes = []
    if not outcomes_df.empty:
        recent_df = outcomes_df.sort_values("created_at", ascending=False).head(5)
        for _, row in recent_df.iterrows():
            recent_outcomes.append({
                "team": row.get("officer_id"),
                "outcome": row.get("outcome_type"),
                "actual_violations": row.get("actual_violations_found")
            })

    return {
        "region_filter": user.get("region", "All"),
        "top_10_unassigned_red_zones": top_unassigned,
        "team_status_counts": team_status,
        "todays_high_false_positive_zones": fp_zones,
        "volatile_growing_zone_count": vg_count,
        "recent_outcomes": recent_outcomes
    }


@router.post("/query", summary="LLM Chatbot for Control Room")
def query_chatbot(body: ChatbotQuery, user: dict = Depends(require_control_room)):
    context = _build_context(user)
    context_json = json.dumps(context, indent=2)
    
    system_prompt = f"""You are an intelligent traffic enforcement assistant for 
Bengaluru Traffic Police control room. You help senior officers 
make patrol dispatch decisions. Answer concisely in 2-4 sentences. 
Use simple English. Provide actionable recommendations.
Current data:
{context_json}"""

    # Attempt to call Anthropic API, handle gracefully if missing/unconfigured
    answer = ""
    try:
        import anthropic
        import os
        
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
            
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=300,
            system=system_prompt,
            messages=[
                {"role": "user", "content": body.question}
            ]
        )
        answer = response.content[0].text
    except ImportError:
        answer = (
            f"[Fallback Mode: Anthropic SDK not installed]\n"
            f"Based on the data, you have {len(context['top_10_unassigned_red_zones'])} "
            f"unassigned red zones and {context['team_status_counts'].get('available', 0)} "
            f"teams available. Please install the anthropic package to enable AI insights."
        )
    except ValueError as e:
        answer = (
            f"[Fallback Mode: {str(e)}]\n"
            f"Data snapshot: {context['team_status_counts'].get('available', 0)} teams available, "
            f"{context['volatile_growing_zone_count']} volatile-growing zones active."
        )
    except Exception as e:
        answer = f"[Fallback Mode: API Error - {str(e)}]\nContext retrieved successfully, but LLM generation failed."

    return {
        "answer": answer,
        "data_used": list(context.keys())
    }
