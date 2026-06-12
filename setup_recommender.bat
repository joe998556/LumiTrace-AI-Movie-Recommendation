@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set "PY=py -3"
) else (
  set "PY=python"
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating local virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 goto fail
)

call ".venv\Scripts\activate.bat"

echo Installing Python dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto fail
python -m pip install -r requirements.txt
if errorlevel 1 goto fail

echo.
echo Building the LumiTrace recommendation vector index.
echo Choose a larger preset for better coverage. Larger presets can take a long time.
python tools\bootstrap_recommender.py
if errorlevel 1 goto fail

echo.
choice /M "Start the BERT recommendation service now"
if errorlevel 2 goto done

python ai_engine\bert_service.py
goto done

:fail
echo.
echo Setup failed. Check the message above.
pause
exit /b 1

:done
echo.
echo Done.
pause
