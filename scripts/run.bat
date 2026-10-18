@echo off
REM Inicia el backend de CORT (Windows)
cd /d %~dp0\..
if not exist .venv python -m venv .venv
.venv\Scripts\pip install -q -r backend\requirements.txt
if not exist backend\.env copy backend\.env.example backend\.env
echo CORT backend en http://127.0.0.1:8000  (Ctrl+C para apagar)
echo Interfaz: abre cort\ui\index.html en Chrome/Edge
.venv\Scripts\uvicorn --app-dir backend app.main:app --port 8000
