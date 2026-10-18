@echo off
REM Inicia CORT completo (Windows): backend + interfaz holografica
cd /d %~dp0\..
if not exist .venv python -m venv .venv
.venv\Scripts\pip install -q -r backend\requirements.txt
if not exist backend\.env copy backend\.env.example backend\.env
echo Backend CORT:  http://127.0.0.1:8000
echo Holograma:     http://localhost:8080   (abre Chrome/Edge y escribe esa direccion)
start /b .venv\Scripts\uvicorn --app-dir backend app.main:app --port 8000
python -m http.server 8080 -d ui
