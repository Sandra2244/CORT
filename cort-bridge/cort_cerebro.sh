#!/usr/bin/env bash
# cort_cerebro.sh — turno de descarga del cerebro de CORT
# =========================================================
# Bajar un modelo de Ollama es puro disco; USARLO es RAM. Este guion hace lo
# primero con la memoria ya libre, que es como cabe en una Classmate de 1,8 GiB.
#
# Uso (con Qoder y el navegador CERRADOS):
#     bash cort_cerebro.sh                # baja qwen2.5:0.5b (~350 MB)
#     bash cort_cerebro.sh qwen2.5:1.5b   # baja el de ~1 GB (pide 1500 MB libres)
#
# Qué hace, en orden y con números medidos:
#   1) mide la RAM libre real y exige un mínimo antes de tocar nada;
#   2) levanta `ollama serve` y espera a que responda;
#   3) descarga el modelo y verifica que aparezca en /api/tags;
#   4) lo anota en cort_state.json como cerebro de CORT;
#   5) deja el servidor APAGADO para que no te coma memoria.
#
# No borra ni modifica nada fuera de la carpeta de modelos de Ollama.

set -euo pipefail

MODELO="${1:-qwen2.5:0.5b}"
RAM_MIN="${CORT_RAM_MIN:-900}"          # MB libres exigidos antes de empezar
AQUI="$(cd "$(dirname "$0")" && pwd)"
ESTADO="$AQUI/cort_state.json"

libre_mb() { awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo; }

echo "[CORT] modelo pedido : $MODELO"
echo "[CORT] RAM libre ahora: $(libre_mb) MB de $(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo) MB"
echo "[CORT] disco libre   : $(df -BG --output=avail / | tail -1 | tr -d ' ')"

if ! command -v ollama >/dev/null 2>&1; then
  echo "[CORT] NO está instalado el binario ollama. Sin eso no hay cerebro local." >&2
  exit 1
fi

LIBRE="$(libre_mb)"
if [ "$LIBRE" -lt "$RAM_MIN" ]; then
  echo "[CORT] BLOQUEADO: hacen falta $RAM_MIN MB libres y hay $LIBRE. Cierra el navegador" \
       "y Qoder (o apaga el puente) y vuelve a lanzar este guion." >&2
  exit 2
fi

echo "[CORT] levantando ollama serve…"
if ! curl -s -o /dev/null http://127.0.0.1:11434/api/tags; then
  nohup ollama serve > /tmp/cort-ollama.log 2>&1 &
  for i in $(seq 1 20); do
    sleep 1
    curl -s -o /dev/null http://127.0.0.1:11434/api/tags && break
  done
fi
if ! curl -s -o /dev/null http://127.0.0.1:11434/api/tags; then
  echo "[CORT] Ollama no respondió en 20 s. Mira /tmp/cort-ollama.log" >&2
  exit 3
fi
echo "[CORT] Ollama vivo · RAM libre: $(libre_mb) MB"

echo "[CORT] descargando $MODELO (esto es red y disco, no congela el equipo)…"
ollama pull "$MODELO"

echo "[CORT] verificando la lista de modelos:"
curl -s http://127.0.0.1:11434/api/tags | python3 -c '
import json,sys
ms = json.load(sys.stdin).get("models", [])
print("   ", [m.get("name") for m in ms] or "NINGUNO")
'

echo "[CORT] anotando $MODELO como cerebro de CORT en cort_state.json"
MODELO="$MODELO" ESTADO="$ESTADO" python3 -c '
import json, os
from pathlib import Path
ruta = Path(os.environ["ESTADO"])
try:
    e = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
except Exception:
    e = {}
e["local_model"] = os.environ["MODELO"]
ruta.write_text(json.dumps(e, ensure_ascii=False, indent=2), encoding="utf-8")
print("   estado guardado en", ruta)
'

echo "[CORT] apagando ollama serve para devolverte la memoria…"
pkill -f "ollama serve" || true
sleep 1
curl -s -o /dev/null http://127.0.0.1:11434/api/tags && echo "[CORT] OJO: sigue vivo" || echo "[CORT] servidor apagado"
echo "[CORT] listo. Cuando abras el puente y el puente cargue $(libre_mb) MB libres, CORT piensa con $MODELO."
