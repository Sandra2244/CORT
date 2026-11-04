#!/usr/bin/env bash
# scripts/para_cort.sh — apaga el puente de CORT sin matar nada más.
#
# Primero prueba systemd (el servicio de usuario que escribe instala_cort.sh) y,
# si fue arrancado a mano, busca el proceso por su línea de comando exacta y lo
# apaga por PID. No usa pkill con un patrón suelto: un patrón como "cort_server"
# también puede casar con la terminal que lo lanzó y dejar la sesión colgada.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if command -v systemctl >/dev/null 2>&1 && systemctl --user list-unit-files cort.service >/dev/null 2>&1; then
  if systemctl --user is-active --quiet cort 2>/dev/null; then
    systemctl --user stop cort
    echo "servicio de usuario cort parado"
    exit 0
  fi
fi

PIDS="$(pgrep -f "^$ROOT/.venv/bin/python -u $ROOT/cort-bridge/cort_server.py" 2>/dev/null || true)"
if [ -z "$PIDS" ]; then
  PIDS="$(pgrep -f "cort-bridge/cort_server.py" 2>/dev/null || true)"
fi
if [ -z "$PIDS" ]; then
  echo "no hay ningún puente de CORT corriendo"
  exit 0
fi
for p in $PIDS; do
  kill "$p" 2>/dev/null && echo "pedido apagado al puente pid=$p"
done
sleep 1
for p in $PIDS; do
  kill -0 "$p" 2>/dev/null && kill -TERM "$p" 2>/dev/null && echo "segunda pasada a pid=$p"
done
