@echo off
"%~dp0runtime\python\python.exe" -c "from docling.cli.main import app; app()" %*
