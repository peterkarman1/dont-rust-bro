@echo off
set "DRB_ROOT=%~dp0.."
set "PYTHON=%DRB_ROOT%\venv\Scripts\python.exe"
set "PYTHONPATH=%DRB_ROOT%;%PYTHONPATH%"
"%PYTHON%" -m drb.cli %*
