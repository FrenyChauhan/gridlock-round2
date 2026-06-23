#!/bin/bash
cd "$(dirname "$0")/.."
source gridlock_env/Scripts/activate
uvicorn backend.main:app --reload --port 8000
