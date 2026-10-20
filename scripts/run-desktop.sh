#!/usr/bin/env bash
# CORT holograma de escritorio (Linux/macOS): UN solo backend que reparte
# API + interfaz, y la ventana Electron encima.
#   bash scripts/run-desktop.sh              -> modo CABINA (ventana oscura sin marco; va en cualquier equipo)
#   CORT_GLASS=1 bash scripts/run-desktop.sh -> modo VIDRIO (transparente; requiere GPU+compositor)
set -e
cd "$(dirname "$0")/.."
PORT="${CORT_PORT:-8000}"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r backend/requirements.txt
[ -f backend/.env ] || cp backend/.env.example backend/.env
[ -d desktop/node_modules/electron/dist ] || (cd desktop && npm install)
CORT_SERVE_UI=1 .venv/bin/uvicorn --app-dir backend app.main:app --port "$PORT" &
B1=$!
trap 'kill $B1 2>/dev/null' EXIT
sleep 1.5
if [ "$CORT_GLASS" = "1" ]; then
  echo "Modo VIDRIO: si no ves nada, tu Linux necesita GPU+compositor. Usa modo CABINA (sin CORT_GLASS)."
fi
(cd desktop && CORT_PORT="$PORT" DISPLAY=${DISPLAY:-:0} npx electron .)
