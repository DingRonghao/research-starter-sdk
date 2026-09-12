@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "PROJECT_PYTHON=%~dp0.venv\Scripts\python.exe"
set "CONFIG_FILE=%~dp0config.local.json"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Bootstrap Research Starter.ps1" -ProjectRoot "%~dp0" || goto :fail

if not exist "%PROJECT_PYTHON%" (
  set "BASE_PYTHON="
  for /f "usebackq delims=" %%I in (`powershell.exe -NoProfile -Command "$value=(Get-Content -Raw -LiteralPath '%CONFIG_FILE%' | ConvertFrom-Json).base_python; if ($value) { [IO.Path]::GetFullPath($value, '%~dp0') }"`) do set "BASE_PYTHON=%%I"
  if not exist "!BASE_PYTHON!" (
    echo Research Starter setup failed: the selected Python is unavailable.
    pause
    exit /b 1
  )
  "!BASE_PYTHON!" -m venv "%~dp0.venv" || goto :fail
  "%PROJECT_PYTHON%" -m pip install setuptools==84.0.0 || goto :fail
  "%PROJECT_PYTHON%" -m pip install --no-build-isolation antlr4-python3-runtime==4.9.3 || goto :fail
  "%PROJECT_PYTHON%" -m pip install -r "%~dp0requirements.txt" || goto :fail
)

if not exist "%~dp0node_modules\pptxgenjs" (
  set "NPM_CMD="
  for /f "usebackq delims=" %%I in (`powershell.exe -NoProfile -Command "$value=(Get-Content -Raw -LiteralPath '%CONFIG_FILE%' | ConvertFrom-Json).npm_cmd; if ($value) { [IO.Path]::GetFullPath($value, '%~dp0') }"`) do set "NPM_CMD=%%I"
  call "!NPM_CMD!" install --ignore-scripts --cache "%~dp0.runtime\npm-cache" || goto :fail
)

powershell.exe -NoProfile -WindowStyle Hidden -Command "Start-Process -FilePath '%PROJECT_PYTHON%' -ArgumentList '-m','web.launcher' -WorkingDirectory '%~dp0' -WindowStyle Hidden"
exit /b 0

:fail
echo Research Starter setup failed. See the message above.
pause
exit /b 1
