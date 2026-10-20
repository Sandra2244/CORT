@echo off
REM Inicia CORT completo (Windows) -- UN solo proceso:
REM el backend reparte la API y el holograma en el mismo puerto.
REM   Cambia el puerto con:  set CORT_PORT=8090  antes de ejecutar.
cd /d %~dp0\..
if not defined CORT_PORT set CORT_PORT=8000
if not exist .venv python -m venv .venv
.venv\Scripts\pip install -q -r backend\requirements.txt
if not exist backend\.env copy backend\.env.example backend\.env
echo CORT v0.2 -- todo en un solo lugar:
echo   holograma + cerebro -^  http://localhost:%CORT_PORT%   (Chrome o Edge)
echo   API REST            -^  http://127.0.0.1:%CORT_PORT%\api\status
set CORT_SERVE_UI=1
start "" /b .venv\Scripts\uvicorn --app-dir backend app.main:app --port %CORT_PORT%
timeout /t 2 /nobreak >nul
start "" http://localhost:%CORT_PORT%
pause
