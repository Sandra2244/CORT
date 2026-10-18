#!/usr/bin/env bash
# Inicia CORT completo (Linux/macOS): backend + interfaz holográfica
set -e
cd "$(dirname "$0")/.."
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r backend/requirements.txt
[ -f backend/.env ] || cp backend/.env.example backend/.env
echo "▶ Backend CORT:  http://127.0.0.1:8000"
echo "▶ Holograma:     http://localhost:8080   (ábrelo en Chrome/Edge)"
.venv/bin/uvicorn --app-dir backend app.main:app --port 8000 &
BACK=$!
trap 'kill $BACK 2>/dev/null' EXIT
python3 -m http.server 8080 -d ui
