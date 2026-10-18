#!/usr/bin/env bash
# CORT holograma de escritorio (Linux): backend + servidor UI + ventana Electron.
#   bash scripts/run-desktop.sh            -> modo CABINA (ventana oscura sin marco; funciona en cualquier equipo)
#   CORT_GLASS=1 bash scripts/run-desktop.sh -> modo VIDRIO (transparente sobre el escritorio; requiere GPU/compositor)
set -e
cd "$(dirname "$0")/.."
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r backend/requirements.txt
[ -f backend/.env ] || cp backend/.env.example backend/.env
[ -d desktop/node_modules/electron/dist ] || (cd desktop && npm install)
.venv/bin/uvicorn --app-dir backend app.main:app --port 8000 &
B1=$!
python3 -m http.server 8080 -d ui &
B2=$!
trap 'kill $B1 $B2 2>/dev/null' EXIT
sleep 2
if [ "$CORT_GLASS" = "1" ]; then
  echo "Modo VIDRIO: si no ves nada, tu Linux necesita GPU+compositor. Usa modo CABINA (sin CORT_GLASS)."
fi
(cd desktop && DISPLAY=${DISPLAY:-:0} npx electron .)
