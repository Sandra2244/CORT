@echo off
rem CORT — doble clic en Windows.
rem Si existe el venv del proyecto se usa ese interprete; si no, el del sistema,
rem y el lanzador dira como crearlo en vez de fallar con un traceback.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (set "PY=.venv\Scripts\python.exe") else (set "PY=python")
"%PY%" scripts\cort.py %*
if errorlevel 1 pause
