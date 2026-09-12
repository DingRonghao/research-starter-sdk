@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "PROJECT_PYTHON=%~dp0.venv\Scripts\python.exe"
set "CONFIG_FILE=%~dp0config.local.json"

if not exist "%CONFIG_FILE%" (
  copy /y "%~dp0config.example.json" "%CONFIG_FILE%" >nul || goto :fail
  powershell.exe -NoProfile -Command "$p='%CONFIG_FILE%'; $c=Get-Content -Raw -LiteralPath $p | ConvertFrom-Json; $c.codex_home=Join-Path $env:USERPROFILE '.codex'; $common='C:\Program Files\Obsidian\Obsidian.exe'; if(Test-Path -LiteralPath $common){$c.obsidian_exe=$common}; $c | ConvertTo-Json | Set-Content -LiteralPath $p -Encoding utf8" || goto :fail
)

if not exist "%PROJECT_PYTHON%" (
  set "BASE_PYTHON="
  for /f "usebackq delims=" %%I in (`powershell.exe -NoProfile -Command "$value=(Get-Content -Raw -LiteralPath '%CONFIG_FILE%' | ConvertFrom-Json).base_python; if ($value) { [IO.Path]::GetFullPath($value, '%~dp0') }"`) do set "BASE_PYTHON=%%I"
  if exist "!BASE_PYTHON!" "!BASE_PYTHON!" -c "import sys;raise SystemExit(0 if (3,10) <= sys.version_info[:2] < (3,13) else 1)" >nul 2>nul || set "BASE_PYTHON="
  if not exist "!BASE_PYTHON!" for /f "usebackq delims=" %%I in (`py -3.12 -c "import sys;print(sys.executable)" 2^>nul`) do set "BASE_PYTHON=%%I"
  if not exist "!BASE_PYTHON!" for /f "usebackq delims=" %%I in (`py -3.11 -c "import sys;print(sys.executable)" 2^>nul`) do set "BASE_PYTHON=%%I"
  if not exist "!BASE_PYTHON!" for /f "usebackq delims=" %%I in (`py -3.10 -c "import sys;print(sys.executable)" 2^>nul`) do set "BASE_PYTHON=%%I"
  if not exist "!BASE_PYTHON!" for /f "usebackq delims=" %%I in (`python -c "import sys;assert (3,10) ^<^= sys.version_info[:2] ^< (3,13);print(sys.executable)" 2^>nul`) do set "BASE_PYTHON=%%I"
  if not exist "!BASE_PYTHON!" (
    echo Research Starter setup failed: no compatible existing Python 3.10-3.12 was found.
    echo Set base_python in config.local.json to an existing compatible python.exe.
    pause
    exit /b 1
  )
  powershell.exe -NoProfile -Command "$p='%CONFIG_FILE%'; $c=Get-Content -Raw -LiteralPath $p | ConvertFrom-Json; $c.base_python='!BASE_PYTHON!'; $c | ConvertTo-Json | Set-Content -LiteralPath $p -Encoding utf8" || goto :fail
  "!BASE_PYTHON!" -m venv "%~dp0.venv" || goto :fail
  "%PROJECT_PYTHON%" -m pip install setuptools==84.0.0 || goto :fail
  "%PROJECT_PYTHON%" -m pip install --no-build-isolation antlr4-python3-runtime==4.9.3 || goto :fail
  "%PROJECT_PYTHON%" -m pip install -r "%~dp0requirements.txt" || goto :fail
)

if not exist "%~dp0node_modules\pptxgenjs" (
  call npm install --ignore-scripts --cache "%~dp0.runtime\npm-cache" || goto :fail
)

powershell.exe -NoProfile -WindowStyle Hidden -Command "Start-Process -FilePath '%PROJECT_PYTHON%' -ArgumentList '-m','web.launcher' -WorkingDirectory '%~dp0' -WindowStyle Hidden"
exit /b 0

:fail
echo Research Starter setup failed. See the message above.
pause
exit /b 1
