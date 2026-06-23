@echo off
cd /d "%~dp0.."
call gridlock_env\Scripts\activate.bat
uvicorn backend.main:app --reload --port 8000
