#!/usr/bin/env bash
# scripts/arranca_cort.sh — levanta el puente una sola vez y se va.
#
# Es lo que llama el lanzador de escritorio y el arranque automático de XFCE. Si ya
# hay un puente corriendo no duplica nada: lo dice y sale. El registro va a
# ~/.local/share/cort/logs/puente.log y el PID a .run/puente.pid, para que
# para_cort.sh sepa a quién llamar.
#
# Opciones: --red abre el puente a la red local (para el teléfono).
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BIND=""
for a in "$@"; do
  case "$a" in
    --red) BIND="0.0.0.0" ;;
    *) echo "opción desconocida: $a (--red)"; exit 2 ;;
  esac
done

PYTHON=".venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"
if [ ! -x ".venv/bin/python" ]; then
  echo "aviso: no está .venv; se usa python3 del sistema y puede faltar aiohttp" >&2
fi

PID="$(cat .run/puente.pid 2>/dev/null || true)"
if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
  echo "CORT ya está corriendo (pid $PID). Si quieres reiniciarlo: scripts/para_cort.sh"
  exit 0
fi
if ss -ltn 2>/dev/null | grep -q ":${CORT_WEB_PORT:-8766} "; then
  echo "algo escucha ya en el puerto ${CORT_WEB_PORT:-8766}: CORT está puesto por otro camino."
  exit 0
fi

mkdir -p .run "${CORT_HOME:-$HOME/.local/share/cort}/logs"
LOG="${CORT_HOME:-$HOME/.local/share/cort}/logs/puente.log"

if [ -n "$BIND" ]; then
  CORT_BIND="$BIND" nohup "$PYTHON" -u cort-bridge/cort_server.py >> "$LOG" 2>&1 &
else
  nohup "$PYTHON" -u cort-bridge/cort_server.py >> "$LOG" 2>&1 &
fi
echo $! > .run/puente.pid
sleep 2
if kill -0 "$(cat .run/puente.pid)" 2>/dev/null; then
  echo "CORT arriba (pid $(cat .run/puente.pid)) · http://127.0.0.1:${CORT_WEB_PORT:-8766}/index.html"
else
  echo "el puente se cayó al arrancar; las últimas líneas de $LOG:" >&2
  tail -5 "$LOG" >&2 || true
  exit 1
fi
