#!/usr/bin/env bash
# Inicia el backend de CORT (Linux/macOS). La interfaz se abre aparte: ui/index.html
set -e
cd "$(dirname "$0")/.."
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r backend/requirements.txt
[ -f backend/.env ] || cp backend/.env.example backend/.env
echo "▶ CORT backend en http://127.0.0.1:8000  (Ctrl+C para apagar)"
echo "▶ Interfaz: abre cort/ui/index.html en Chrome/Edge, o:  python3 -m http.server 8080 -d ui"
.venv/bin/uvicorn --app-dir backend app.main:app --port 8000
