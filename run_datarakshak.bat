@echo off
setlocal

cd /d "%~dp0"

echo Starting DataRakshak...
echo.

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" ".\main.py"
) else (
    echo Virtual environment was not found.
    echo Trying the system Python installation...
    echo.

    python ".\main.py"
)

if errorlevel 1 (
    echo.
    echo DataRakshak could not be started.
    echo Check Python and project dependencies.
    echo.
    pause
)

endlocal