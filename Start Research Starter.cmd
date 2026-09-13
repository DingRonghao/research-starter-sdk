@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PROJECT_PYTHON=%~dp0runtime\python\python.exe"
set "PROJECT_NODE=%~dp0runtime\node\node.exe"

if not exist "%PROJECT_PYTHON%" (
  echo Research Starter cannot start: bundled Python runtime is missing.
  echo Please download and extract the complete Windows release package.
  goto :fail
)

if not exist "%PROJECT_NODE%" (
  echo Research Starter cannot start: bundled Node.js runtime is missing.
  echo Please download and extract the complete Windows release package.
  goto :fail
)

if not exist "%~dp0node_modules\pptxgenjs" (
  echo Research Starter cannot start: bundled application dependencies are missing.
  echo Please download and extract the complete Windows release package.
  goto :fail
)

set "PATH=%~dp0runtime\node;%~dp0runtime\python;%~dp0runtime\python\Scripts;%PATH%"
start "" /b "%PROJECT_PYTHON%" -m web.launcher
exit /b 0

:fail
echo.
echo Setup is not required. No system Python or Node.js will be modified.
pause
exit /b 1
