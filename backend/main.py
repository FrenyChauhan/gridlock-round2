"""
backend/main.py
================
Gridlock 2.0 — FastAPI Application Entry Point

Run with:
    backend/start.bat (Windows)
    backend/start.sh (Mac/Linux)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Ensure project root is on sys.path
PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import database FIRST so DataFrames load before routers register
from backend import database as db  # noqa: F401

from backend.routers import (
    auth_router,
    zones,
    teams,
    assignments,
    feedback,
    dashboard,
    chatbot,
)

# ==================================================================
# APP INSTANCE
# ==================================================================

app = FastAPI(
    title       = "Gridlock 2.0 — Bengaluru Traffic Violation API",
    description = (
        "Real-time patrol allocation, zone priority scoring, "
        "and enforcement feedback for the BTP traffic violation prediction system."
    ),
    version     = "2.0.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

# ==================================================================
# CORS
# ==================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================================================================
# GLOBAL EXCEPTION HANDLER
# ==================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code = 500,
        content     = {
            "detail": f"Internal server error: {type(exc).__name__}: {exc}",
            "path"  : str(request.url),
        },
    )

# ==================================================================
# ROUTERS
# ==================================================================

app.include_router(auth_router.router, prefix="/api")
app.include_router(zones.router, prefix="/api")
app.include_router(teams.router, prefix="/api")
app.include_router(assignments.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(chatbot.router, prefix="/api")

# ==================================================================
# ROOT + HEALTH ENDPOINTS
# ==================================================================

@app.get("/", tags=["Health"], summary="API root / Health check")
def root():
    return {
        "service": "Gridlock 2.0 API",
        "version": "2.0.0",
        "status": "running"
    }


# ==================================================================
# STARTUP / SHUTDOWN EVENTS
# ==================================================================

@app.on_event("startup")
async def on_startup():
    print("\n" + "=" * 55)
    print("  Gridlock 2.0 Backend Started")
    print(f"  Priority zones : {len(db.df_priority):,}")
    print(f"  Teams          : {len(db.df_teams)}")
    print(f"  Assignments    : {len(db.df_assignments)}")
    print("=" * 55 + "\n")


@app.on_event("shutdown")
async def on_shutdown():
    print("\nGridlock 2.0 API — Shutting down.")
