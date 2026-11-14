@echo off
pushd "%~dp0" 2>nul
title AgroShift Crop Finder
echo ============================================================================
echo   Starting AgroShift Crop Finder in WSL
echo ============================================================================
echo.
echo Launching AgroShift on http://localhost:8501 ...
echo.

:: Automatically open default browser
start "" http://localhost:8501

:: Run via WSL
wsl -d Ubuntu-26.04 -- bash -c "cd /home/asus/.gemini/antigravity/worktrees/nasa/agroshift_latest 2>/dev/null || cd /home/asus/.gemini/antigravity/worktrees/nasa/agroshift_scientific_upgrade 2>/dev/null || cd /home/asus/nasa 2>/dev/null || cd /home/asus/.gemini/antigravity/worktrees/nasa/agroshift_scientific_engineering_upgrade; bash scripts/run.sh"
if errorlevel 1 (
    wsl -- bash -c "cd /home/asus/.gemini/antigravity/worktrees/nasa/agroshift_latest 2>/dev/null || cd /home/asus/.gemini/antigravity/worktrees/nasa/agroshift_scientific_upgrade 2>/dev/null || cd /home/asus/nasa 2>/dev/null || cd /home/asus/.gemini/antigravity/worktrees/nasa/agroshift_scientific_engineering_upgrade; bash scripts/run.sh"
)

popd 2>nul
pause
