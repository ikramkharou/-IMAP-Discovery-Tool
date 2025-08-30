@echo off
echo Installing IMAP Discovery Tool Dependencies...
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://python.org
    pause
    exit /b 1
)

:: Install dependencies
echo Installing required packages...
pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ✅ Installation completed successfully!
echo.
echo Available Tools:
echo   python start_server.py         (Web Interface - Recommended)
echo   python run_discovery.py        (Command Line - Interactive)
echo   python email_imap_finder.py    (Command Line - Direct)
echo   python backend.py              (Web Server Only)
echo.
echo 🌐 For the best experience, use: python start_server.py
echo.
pause
