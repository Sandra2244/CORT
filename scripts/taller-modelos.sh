#!/usr/bin/env bash
# Taller de mutaciones de `scripts/prueba-modelos.py` (F13).
#
# Por qué existe: **un verde que no puede caer no es prueba.** Aquí se rompe el
# código a propósito —una mutación por cada red que la suite vigila— y se exige
# que la suite caiga Y ADEMÁS diga qué comprobación era la que faltaba. Si el
# código roto sigue dando verde, la comprobación es decoración.
#
# Dónde se corre: en el taller, NUNCA como paso del pipeline. El pipeline ya
# corre `prueba-modelos.py` limpio; estas 17 mutaciones son para cuando se toca
# `backend/app/models.py` o `config_store.py`. Trabaja sobre una copia de links
# duros en `/tmp` y rompe el link antes de tocar, así que el repo no se entera.
#
# Uso:  bash scripts/taller-modelos.sh     (≈20 segundos)
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TALLER="$(mktemp -d /tmp/cort-taller-modelos-XXXXXX)"
trap 'rm -rf "$TALLER"' EXIT

cp -al "$REPO/backend" "$TALLER/backend" 2>/dev/null || cp -a "$REPO/backend" "$TALLER/backend"
mkdir -p "$TALLER/scripts"
cp -al "$REPO/scripts/prueba-modelos.py" "$TALLER/scripts/" 2>/dev/null \
  || cp -a "$REPO/scripts/prueba-modelos.py" "$TALLER/scripts/"

CAEN=0
AGUANTAN=0

muta() {  # muta <nombre> <sed> [archivo relativo; por defecto backend/app/models.py]
  local nombre="$1" expr="$2" rel="${3:-backend/app/models.py}"
  rm -f "$TALLER/$rel"                       # rompe el link duro antes de tocar
  cp "$REPO/$rel" "$TALLER/$rel"
  sed -i "$expr" "$TALLER/$rel"
  if cmp -s "$REPO/$rel" "$TALLER/$rel"; then
    echo "  ???     $nombre: el sed no cambió nada (mutación mal escrita)"
    AGUANTAN=$((AGUANTAN + 1))
    return
  fi
  local log="$TALLER/salida.log"
  if python3 "$TALLER/scripts/prueba-modelos.py" > "$log" 2>&1; then
    echo "  AGUANTA $nombre: la suite dio verde con $rel roto"
    AGUANTAN=$((AGUANTAN + 1))
  else
    echo "  cae     $nombre -> $(grep -m1 'FALLA' "$log" | sed 's/^ *FALLA *//' | cut -c1-92)"
    CAEN=$((CAEN + 1))
  fi
}

echo
echo "· taller de mutaciones del gestor de modelos"

# — la RAM y `psutil` (el rojo que ya mató un run: 39879890814) —
muta "psutil obligatorio otra vez"        's/^    psutil = None$/    raise ImportError("sin psutil")/'
muta "el veredicto se inventa sin medir"   's/"estado": "sin medir"/"estado": "va"/'
muta "confunde cuándo se puede medir"     's/^    if psutil is None:$/    if psutil is not None:/'
muta "dice psutil aunque cierre por /proc" 's/"via": "\/proc"/"via": "psutil"/'

# — levantar el servidor de cara a la red —
muta "host fijo en casa (ignora el mando)" 's|return f"0.0.0.0:{PUERTO_OLLAMA}" if quiere_red() else f"127.0.0.1:{PUERTO_OLLAMA}"|return f"127.0.0.1:{PUERTO_OLLAMA}"|'
muta "arranca sin OLLAMA_HOST (el bug original)" '/entorno\.setdefault("OLLAMA_HOST", host_sirve())/d'
muta "pisa el OLLAMA_HOST de la dueña"     's/entorno\.setdefault("OLLAMA_HOST", host_sirve())/entorno["OLLAMA_HOST"] = host_sirve()/'
muta "lanza un segundo servidor encima"    's/^    if corriendo():$/    if False:/'

# — lo que se escribe en la pantalla —
muta "miente con la IP (url siempre llena)" 's|url = f"http://{ip}:{PUERTO_OLLAMA}" if ip else ""|url = f"http://127.0.0.1:{PUERTO_OLLAMA}"|'
muta "avisa lo mismo si hay IP o no"       's/^    if not ip:$/    if False:/'
muta "sale a la red con Ollama apagado"    's/if not ip or not corriendo():/if not ip:/'
muta "culpa al aire cuando cerró ella"     's/^    elif not quiere_red():$/    elif False:/'

# — el disco, antes de lanzar la bajada —
muta "baja sin mirar el disco"             's/if ficha and ficha\.get("b") and libre and/if False and/'
muta "negativea un modelo desconocido"     's/ficha = POR_NOMBRE\.get(nombre)/ficha = POR_NOMBRE.get(nombre) or {"gb": 9.9, "b": 9_900_000_000, "ram": 1}/'

# — el JSON que consume la cara —
muta "el estado ya no trae la red"         's/            "red": info_red()}/}/'
muta "el estado ya no trae el sitio libre" 's/"disco_libre_gb": disco_libre_gb(),//'

# — y el mando de Ajustes, que vive en `config_store` —
muta 'ollama_red fuera de la tabla de Ajustes' 's/^    "ollama_red": "1",$/    # MUTA: fuera de DEFAULTS/' backend/app/config_store.py

# Con el código limpio tiene que volver a dar verde; si no, el recuento de arriba
# no significa nada (el taller se quedó con un fichero roto).
rm -f "$TALLER/backend/app/models.py" "$TALLER/backend/app/config_store.py"
cp "$REPO/backend/app/models.py" "$TALLER/backend/app/models.py"
cp "$REPO/backend/app/config_store.py" "$TALLER/backend/app/config_store.py"
if python3 "$TALLER/scripts/prueba-modelos.py" > "$TALLER/limpio.log" 2>&1; then
  echo
  echo "  (y con el código limpio vuelve a dar verde)"
else
  echo
  echo "  OJO: con el código limpio la suite cayó"
  AGUANTAN=$((AGUANTAN + 1))
fi
echo
echo "mutaciones: caen $CAEN, aguantan $AGUANTAN"
[[ $AGUANTAN -eq 0 ]]
