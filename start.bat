@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

echo ============================================================
echo              AI Agent Web Starter
echo ============================================================
echo.
echo Current folder:
echo %CD%
echo.

REM ============================================================
REM 1. Check Python virtual environment
REM ============================================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv was not found.
    echo.
    echo Expected:
    echo %CD%\.venv\Scripts\python.exe
    echo.
    pause
    exit /b 1
)

echo [OK] Virtual environment found.
echo.

REM ============================================================
REM 2. Check app.py
REM ============================================================

if not exist "app.py" (
    echo [ERROR] app.py was not found.
    echo.
    echo Expected:
    echo %CD%\app.py
    echo.
    pause
    exit /b 1
)

echo [OK] app.py found.
echo.

REM ============================================================
REM 3. Check Streamlit
REM ============================================================

".venv\Scripts\python.exe" -m streamlit --version >nul 2>&1

if errorlevel 1 (
    echo [ERROR] Streamlit is not installed.
    echo.
    echo Installing Streamlit...
    ".venv\Scripts\python.exe" -m pip install streamlit

    if errorlevel 1 (
        echo.
        echo [ERROR] Streamlit installation failed.
        pause
        exit /b 1
    )
)

echo [OK] Streamlit is available.
echo.

REM ============================================================
REM 4. Get local IPv4 address
REM ============================================================

set "LOCAL_IP=Unavailable"

for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /R /C:"IPv4 Address" /C:"IPv4 µÿ÷∑"') do (
    set "LOCAL_IP=%%A"
    set "LOCAL_IP=!LOCAL_IP: =!"
    goto :IP_FOUND
)

:IP_FOUND

REM ============================================================
REM 5. Display access information
REM ============================================================

echo ============================================================
echo                    STARTING AI AGENT
echo ============================================================
echo.
echo Computer:
echo http://localhost:8501
echo.
echo Tablet / Phone on same Wi-Fi:
echo http://%LOCAL_IP%:8501
echo.
echo ============================================================
echo Keep this black window open while using the website.
echo ============================================================
echo.

REM ============================================================
REM 6. Start Streamlit
REM ============================================================

start "" "http://localhost:8501"

".venv\Scripts\python.exe" -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501

pause