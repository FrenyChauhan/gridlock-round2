@echo off
echo ============================================================
echo  Gridlock Round 2 - Environment Setup
echo ============================================================
echo.

REM Step 1: Create virtual environment
echo [1/3] Creating virtual environment: gridlock_env ...
python -m venv gridlock_env
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment. Make sure Python is installed.
    pause
    exit /b 1
)
echo Done.
echo.

REM Step 2: Activate virtual environment
echo [2/3] Activating gridlock_env ...
call gridlock_env\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)
echo Done.
echo.

REM Step 3: Upgrade pip and install packages
echo [3/3] Installing required packages ...
python -m pip install --upgrade pip
pip install ^
    pandas ^
    numpy ^
    scikit-learn ^
    lightgbm ^
    matplotlib ^
    seaborn ^
    plotly ^
    fastapi ^
    uvicorn ^
    python-multipart ^
    requests ^
    pyyaml ^
    scipy ^
    folium ^
    tqdm ^
    joblib ^
    holidays

if %errorlevel% neq 0 (
    echo ERROR: Some packages failed to install. Check the output above.
    pause
    exit /b 1
)
echo.
echo ============================================================
echo  Setup complete! Environment is ready.
echo  To activate later, run: gridlock_env\Scripts\activate.bat
echo ============================================================
pause
