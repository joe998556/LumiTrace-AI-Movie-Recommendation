@echo off
setlocal EnableExtensions EnableDelayedExpansion
title LumiTrace Windows AI Setup

cd /d "%~dp0"

echo.
echo ============================================================
echo  LumiTrace Windows AI Setup
echo ============================================================
echo.
echo This script sets up the optional local BERT recommendation
echo server for the LumiTrace Android app.
echo.
echo You need:
echo   1. Windows PC on the same Wi-Fi/LAN as your phone
echo   2. Python 3.10 or newer
echo   3. A TMDB API key
echo.
echo The Android app still needs your TMDB key in Settings.
echo The BERT endpoint generated here is only for AI Recommend.
echo.

if not exist "tools\bootstrap_recommender.py" (
  echo ERROR: This BAT must be run from the LumiTrace repository root.
  echo.
  echo Download the source code zip from GitHub Releases, extract it,
  echo then run this file from the extracted folder.
  echo.
  pause
  exit /b 1
)

set "OPEN_TMDB=Y"
set /p "OPEN_TMDB=Open TMDB API page now to apply/copy your key? [Y/n]: "
if /I not "%OPEN_TMDB%"=="n" (
  start "" "https://www.themoviedb.org/settings/api"
  echo.
  echo After creating/copying your TMDB API key, return to this window.
  echo.
)

set "TMDB_API_KEY="
set /p "TMDB_API_KEY=Paste your TMDB API key here: "
if "%TMDB_API_KEY%"=="" (
  echo.
  echo ERROR: TMDB API key is required to download movie data.
  pause
  exit /b 1
)

echo.
echo Choose data size:
echo   1. demo   - about   200 movies, fastest smoke test
echo   2. small  - about 1,000 movies, good first run
echo   3. medium - about 5,000 movies, better coverage
echo   4. large  - about 15,000 movies, long run
echo   5. xlarge - about 30,000 movies, GPU/overnight recommended
echo.
set "PRESET=small"
set /p "PRESET_CHOICE=Select 1-5 [2]: "
if "%PRESET_CHOICE%"=="1" set "PRESET=demo"
if "%PRESET_CHOICE%"=="2" set "PRESET=small"
if "%PRESET_CHOICE%"=="" set "PRESET=small"
if "%PRESET_CHOICE%"=="3" set "PRESET=medium"
if "%PRESET_CHOICE%"=="4" set "PRESET=large"
if "%PRESET_CHOICE%"=="5" set "PRESET=xlarge"

echo.
echo Choose compute device:
echo   auto - use CUDA GPU if PyTorch can see it, otherwise CPU
echo   cpu  - force CPU
echo   cuda - force NVIDIA CUDA GPU
echo.
set "DEVICE=auto"
set /p "DEVICE=Device [auto]: "
if "%DEVICE%"=="" set "DEVICE=auto"

set "PORT=5001"
set /p "PORT=Server port [5001]: "
if "%PORT%"=="" set "PORT=5001"

set "PYTHON="
where python >nul 2>nul
if not errorlevel 1 set "PYTHON=python"

if "%PYTHON%"=="" (
  where py >nul 2>nul
  if not errorlevel 1 set "PYTHON=py -3"
)

if "%PYTHON%"=="" (
  echo.
  echo ERROR: Python was not found.
  echo Install Python 3.10+ from https://www.python.org/downloads/
  pause
  exit /b 1
)

echo.
echo Creating Python virtual environment...
if not exist ".venv\Scripts\python.exe" (
  %PYTHON% -m venv .venv
  if errorlevel 1 (
    echo ERROR: Failed to create .venv
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"

echo.
echo Installing Python dependencies. This can take a while.
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo.
echo Building LumiTrace movie vectors.
echo Preset: %PRESET%
echo Device: %DEVICE%
echo.
python tools\bootstrap_recommender.py --preset "%PRESET%" --tmdb-key "%TMDB_API_KEY%" --device "%DEVICE%"
if errorlevel 1 goto :fail

echo.
echo Detecting this PC's LAN IP address...
set "LAN_IP="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$ips=Get-NetIPConfiguration ^| Where-Object { $_.IPv4Address -and $_.NetAdapter.Status -eq 'Up' } ^| ForEach-Object { $_.IPv4Address.IPAddress } ^| Where-Object { $_ -match '^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)' }; if ($ips) { $ips ^| Select-Object -First 1 } else { Get-NetIPAddress -AddressFamily IPv4 ^| Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.)' } ^| Select-Object -First 1 -ExpandProperty IPAddress }"`) do set "LAN_IP=%%I"

if "%LAN_IP%"=="" (
  set "LAN_IP=YOUR_PC_LAN_IP"
)

set "PHONE_ENDPOINT=http://%LAN_IP%:%PORT%/search"

echo.
echo ============================================================
echo  Phone endpoint
echo ============================================================
echo.
echo In LumiTrace Android:
echo   Settings - Connect BERT gateway
echo.
echo Paste this endpoint:
echo   %PHONE_ENDPOINT%
echo.
echo The phone and this PC must be on the same Wi-Fi/LAN.
echo Keep this window open while using AI Recommend.
echo.
(
  echo LumiTrace Android endpoint
  echo.
  echo Paste this into Settings - Connect BERT gateway:
  echo %PHONE_ENDPOINT%
  echo.
  echo Your phone and PC must be on the same Wi-Fi/LAN.
  echo Keep the BERT server window open while using AI Recommend.
) > LumiTrace-phone-endpoint.txt

echo A copy was saved to:
echo   %CD%\LumiTrace-phone-endpoint.txt
echo.

set "FIREWALL=Y"
set /p "FIREWALL=Try to add Windows Firewall rule for TCP %PORT%? [Y/n]: "
if /I not "%FIREWALL%"=="n" (
  netsh advfirewall firewall add rule name="LumiTrace BERT %PORT%" dir=in action=allow protocol=TCP localport=%PORT% profile=private >nul 2>nul
  if errorlevel 1 (
    echo.
    echo Firewall rule was not added. If your phone cannot connect,
    echo run this BAT as Administrator or allow TCP %PORT% manually.
  ) else (
    echo Firewall rule added for private networks on TCP %PORT%.
  )
)

echo.
echo Starting BERT server...
echo Stop it with Ctrl+C.
echo.
python ai_engine\bert_service.py --host 0.0.0.0 --port "%PORT%" --device "%DEVICE%" --vectors movie_vectors.json
goto :end

:fail
echo.
echo ERROR: Setup failed. Check the messages above.
pause
exit /b 1

:end
echo.
echo Server stopped.
pause
