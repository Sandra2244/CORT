#!/usr/bin/env bash
# M2 — Enciende el puente con el núcleo nuevo y deja que CORT se mida sola.
#
# Qué hace: para el puente viejo (el que está corriendo ahora con código anterior a
# F9), arranca el actual con CORT_AUTOSONDA=1 y se queda mirando la RAM. Cuando
# queden >= 900 MB libres —o sea, con Qoder y el navegador cerrados— prueba el
# modelo más chico que quepa, sin ejecutar ninguna orden, y guarda el número en
#   cort-web/mediciones/medicion-cerebro.json
# Si el disparo no cabe, no insiste: vuelve a mirar en diez minutos.
#
# Uso:  bash scripts/arranca_con_sonda.sh
#       (déjalo corriendo y cierra Qoder; el resultado se lee después)
set -e
cd "$(dirname "$0")/.."

VIEJO=$(ss -ltnp 2>/dev/null | grep ':8765' | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2 | cut -d= -f2)
if [ -n "${VIEJO:-}" ]; then
  echo "[sonda] parando el puente viejo (pid $VIEJO) para que corra el de F9"
  kill "$VIEJO" 2>/dev/null || true
  sleep 2
fi

mkdir -p mediciones
LIBRE=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
echo "[sonda] RAM libre ahora: $LIBRE MB · umbral de la auto-sonda: 900 MB"
if [ "$LIBRE" -lt 900 ]; then
  echo "[sonda] todavía no cabe: el puente arranca igual y la sonda espera su turno."
  echo "[sonda] para que llegue el turno: cierra Qoder y el navegador."
fi

CORT_AUTOSONDA=1 nohup .venv/bin/python -u cort-bridge/cort_server.py \
  >> mediciones/puente-sonda.log 2>&1 &
sleep 4
echo "[sonda] puente arriba (log: mediciones/puente-sonda.log)"
echo "[sonda] cuando termine de medir, lee: mediciones/medicion-cerebro.json"
echo "[sonda] y la interfaz está en http://127.0.0.1:8766/index.html"
