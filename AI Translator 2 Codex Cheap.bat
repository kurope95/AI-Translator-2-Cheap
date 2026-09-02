@echo off
echo =======================================================
echo       AI TRANSLATOR 2 CODEX CHEAP STARTUP SCRIPT
echo =======================================================
echo.

cd /d "%~dp0"
set "AI_TRANSLATOR_PORT=5030"

echo [1] Starting AI Translator on port 5030...
echo.

python "app.py"
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] python command failed, trying py launcher...
    py "app.py"
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Could not start app.py using python or py.
    echo Install Python 3 and ensure python/py works in terminal.
)

pause
