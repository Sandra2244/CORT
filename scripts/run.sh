#!/usr/bin/env bash
# Inicia CORT completo (Linux/macOS) — UN solo proceso:
# el backend FastAPI reparte la API *y* el holograma en el mismo puerto.
#
#   bash scripts/run.sh                     -> http://localhost:8000   (sólo este PC)
#   CORT_PORT=8090 bash scripts/run.sh      (si el 8000 está ocupado)
#   CORT_LAN=1 bash scripts/run.sh          -> además visible en la Wi-Fi (teléfono)
set -e
cd "$(dirname "$0")/.."
PORT="${CORT_PORT:-8000}"
HOST="127.0.0.1"
[ "${CORT_LAN:-0}" = "1" ] && HOST="0.0.0.0"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r backend/requirements.txt
[ -f backend/.env ] || cp backend/.env.example backend/.env

# IP local en la red (para decirle a su teléfono la dirección exacta)
LAN_IP=""
if command -v hostname >/dev/null 2>&1; then
  LAN_IP=$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^(192\.|10\.|172\.)' | head -1 || true)
fi
if [ -z "$LAN_IP" ] && command -v ip >/dev/null 2>&1; then
  LAN_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -1 || true)
fi

echo "▶ CORT v0.2 — todo en un solo lugar:"
echo "  holograma + cerebro ->  http://localhost:$PORT   (ábrela en Chrome/Edge)"
echo "  API REST            ->  http://127.0.0.1:$PORT/api/status"
echo "  (si aún sirves la interfaz aparte en :8080, CORT la detecta sola)"
if [ "$HOST" = "0.0.0.0" ]; then
  echo
  echo "  📱 MODO TELÉFONO (Wi-Fi): abre en tu celular"
  echo "       http://${LAN_IP:-IP-DE-ESTE-PC}:$PORT"
  echo "     Los dos tienen que estar en la misma red. El micrófono del navegador"
  echo "     sólo funciona por HTTPS, así que en el teléfono usarás teclado, gestos"
  echo "     y las ventanas; la voz nativa vive en el APK."
fi

CORT_SERVE_UI=1 .venv/bin/uvicorn --app-dir backend app.main:app --host "$HOST" --port "$PORT" &
BACK=$!
trap 'kill $BACK 2>/dev/null' EXIT
sleep 1.5
command -v xdg-open >/dev/null 2>&1 && xdg-open "http://localhost:$PORT" >/dev/null 2>&1 || true
command -v open     >/dev/null 2>&1 && open "http://localhost:$PORT" >/dev/null 2>&1 || true
wait $BACK
