@echo off
setlocal

cd /d "%~dp0"

echo ========================================
echo       DataRakshak Windows Builder
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment was not found.
    echo Run the setup inside the DataRakshak project folder.
    echo.
    pause
    exit /b 1
)

echo Running automated tests...
echo.

".venv\Scripts\python.exe" -m unittest discover -s tests -v

if errorlevel 1 (
    echo.
    echo ERROR: Automated tests failed.
    echo EXE build has been stopped.
    echo.
    pause
    exit /b 1
)

echo.
echo Removing old build files...

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo Building DataRakshak EXE...

".venv\Scripts\python.exe" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --console ^
    --name DataRakshak ^
    ".\main.py"

if errorlevel 1 (
    echo.
    echo ERROR: DataRakshak EXE build failed.
    echo.
    pause
    exit /b 1
)

if not exist ".\dist\DataRakshak\DataRakshak.exe" (
    echo.
    echo ERROR: DataRakshak.exe was not created.
    echo.
    pause
    exit /b 1
)

echo.
echo Creating distribution ZIP...

powershell.exe -NoProfile -Command ^
    "Compress-Archive -Path '.\dist\DataRakshak\*' -DestinationPath '.\dist\DataRakshak-Windows.zip' -Force"

if errorlevel 1 (
    echo.
    echo WARNING: EXE was created, but ZIP creation failed.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD COMPLETED SUCCESSFULLY
echo ========================================
echo.
echo EXE:
echo dist\DataRakshak\DataRakshak.exe
echo.
echo ZIP:
echo dist\DataRakshak-Windows.zip
echo.
echo Real USB wiping remains disabled.
echo USB detection is read-only.
echo.
pause

endlocal