#!/usr/bin/env bash
# Pon CORT en la Wi-Fi para ver el holograma desde el teléfono (misma red).
#   bash scripts/telefono.sh            (puerto 8000)
#   CORT_PORT=8090 bash scripts/telefono.sh
export CORT_LAN=1
exec bash "$(dirname "$0")/run.sh"
