#!/bin/bash
# CORT — la sonda del cerebro en un solo pegado, para correr CON QODER CERRADO.
#
# Pregunta a dos modelos locales las doce frases tuyas y deja las cifras en disco.
# No mueve archivos, no cierra ventanas, no suena nada: sólo mide.
#
#   bash scripts/sonda_cerebro.sh
#
# RAM medida: con el agente abierto quedan 150-191 MB libres y qwen2.5:0.5b pide ~680 MB.
# Por eso el primer paso es cerrar Qoder; si aun así no hay aire, el script se niega y
# lo dice con número (una medida con el equipo swapoteando no es una medida).

set -o pipefail
cd "$HOME/Escritorio/CORT" || exit 1
mkdir -p mediciones

LIBRE=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
echo "RAM disponible: ${LIBRE} MB de $(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo) MB"
if [ "$LIBRE" -lt 900 ]; then
  echo
  echo "NO arranco: hacen falta 900 MB libres. Cierra Qoder (1,09 GB medidos) y el"
  echo "navegador, y vuelve a pegar este comando. No insisto: cargar el modelo así es"
  echo "congelar la laptop."
  exit 2
fi

FECHA=$(date +%Y%m%d-%H%M)
for MODELO in qwen2.5:0.5b qwen3:0.6b; do
  BITACORA="mediciones/cerebro-${MODELO%%:*}-${FECHA}.txt"
  echo
  echo "=== ${MODELO} → ${BITACORA}"
  python3 scripts/cerebro_prueba.py --modelo "$MODELO" --parar-ollama 2>&1 | tee "$BITACORA"
  echo "exit ${?} en ${MODELO}"
done

echo
echo "Listo. Los números quedaron en:"
echo "  mediciones/cerebro-*-${FECHA}.txt   (las tablas que viste)"
echo "  ~/.local/share/cort/registro-cerebro.jsonl   (una línea por frase y modelo)"
echo "Abre Qoder y dime «sonda lista»: leo el registro y con eso se elige el cerebro."
