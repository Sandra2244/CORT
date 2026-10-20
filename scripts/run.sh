#!/usr/bin/env bash
# Inicia CORT completo (Linux/macOS) — UN solo proceso:
# el backend FastAPI reparte la API *y* el holograma en el mismo puerto.
#
#   bash scripts/run.sh                 -> http://localhost:8000
#   CORT_PORT=8090 bash scripts/run.sh   (si el 8000 está ocupado)
set -e
cd "$(dirname "$0")/.."
PORT="${CORT_PORT:-8000}"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r backend/requirements.txt
[ -f backend/.env ] || cp backend/.env.example backend/.env

echo "▶ CORT v0.2 — todo en un solo lugar:"
echo "  holograma + cerebro ->  http://localhost:$PORT   (ábrela en Chrome/Edge)"
echo "  API REST            ->  http://127.0.0.1:$PORT/api/status"
echo "  (si aún sirves la interfaz aparte en :8080, CORT la detecta sola)"

CORT_SERVE_UI=1 .venv/bin/uvicorn --app-dir backend app.main:app --port "$PORT" &
BACK=$!
trap 'kill $BACK 2>/dev/null' EXIT
sleep 1.5
command -v xdg-open >/dev/null 2>&1 && xdg-open "http://localhost:$PORT" >/dev/null 2>&1 || true
command -v open     >/dev/null 2>&1 && open "http://localhost:$PORT" >/dev/null 2>&1 || true
wait $BACK
