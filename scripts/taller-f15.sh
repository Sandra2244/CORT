#!/usr/bin/env bash
# Taller de mutaciones de F15: «pon After Dark», la lista y el ecualizador.
#
# Por qué existe: **un verde que no puede caer no es prueba.** El sector [30] de
# `scripts/prueba-costura.py` da verde sobre las piezas de F15, y `Prueba6` da
# verde sobre `Elige`. Aquí se rompe a propósito —una mutación por cada costura
# que se vigila— para exigir que el verde se ponga rojo Y que el rojo NOMBRE la
# comprobación que faltaba. Si el código roto sigue verde, la comprobación es
# decoración y la canción volvería a sonar mal.
#
# Qué se rompe, en una línea: que `Elige` siga siendo Java puro, que cada
# decisión tenga UN dueño, que el ecualizador no se cuele en la suite de papel,
# que el efecto se enganche a la sesión real y se suelte antes que el
# `MediaPlayer`, que la sección de música por nombre lleve guardia, que «pon X»
# siga buscando en la biblioteca y que `Prueba6` corra en el bucle. La última
# corre la suite entera, porque sólo ella puede ver que `Elige` elige mal.
#
# Dónde se corre: en el taller, NUNCA como paso del pipeline. Trabaja sobre una
# copia de links duros en `/tmp`; rompe el link antes de tocar, así que el repo
# no se entera.
#
# Uso:  bash scripts/taller-f15.sh            (≈1 minuto)
#       bash scripts/taller-f15.sh ecualizador    (sólo las que digan eso)
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TALLER="$(mktemp -d /tmp/cort-taller-f15-XXXXXX)"
trap 'rm -rf "$TALLER"' EXIT

for d in apps ui backend desktop scripts .github; do
  cp -al "$REPO/$d" "$TALLER/$d" 2>/dev/null || cp -a "$REPO/$d" "$TALLER/$d"
done

ELIGE="apps/apk/src/com/cort/ia/Elige.java"
PUENTE="apps/apk/src/com/cort/ia/CortNative.java"
EQ="apps/apk/src/com/cort/ia/Ecualizador.java"
REP="apps/apk/src/com/cort/ia/Reproductor.java"
TEL="ui/js/telefono.js"
DIC="ui/js/diccionario.js"
JSON_APK="apps/apk/assets/habilidades.json"
SH="scripts/prueba-mente.sh"

CAEN=0
AGUANTAN=0
SOLO="${1:-}"
[ -n "$SOLO" ] && echo "  (filtro: sólo las mutaciones que contienen «$SOLO»)"

# reemplaza <archivo> <de> <a>: cambio exacto y comprobado (si no cambia, es que
# la mutación está mal escrita y el taller lo dice en vez de fingir que probó).
reemplaza() {
  python3 - "$TALLER/$1" "$2" "$3" <<'PY'
import pathlib, sys
p, viejo, nuevo = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
t = p.read_text(encoding="utf-8")
if viejo not in t:
    sys.exit(3)
p.write_text(t.replace(viejo, nuevo, 1), encoding="utf-8")
PY
}

muta() {  # muta <nombre> <archivo> <de> <a> [esperado]
  local nombre="$1" rel="$2" viejo="$3" nuevo="$4" espera="${5:-}"
  if [ -n "$SOLO" ] && ! printf '%s' "$nombre" | grep -qi -- "$SOLO"; then
    return 0
  fi
  rm -f "$TALLER/$rel"
  cp "$REPO/$rel" "$TALLER/$rel"
  if ! reemplaza "$rel" "$viejo" "$nuevo"; then
    echo "  ???     $nombre: el reemplazo no encontró el texto (mutación mal escrita)"
    AGUANTAN=$((AGUANTAN + 1))
    return
  fi
  local log="$TALLER/salida.log"
  if python3 "$TALLER/scripts/prueba-costura.py" > "$log" 2>&1; then
    echo "  AGUANTA $nombre: la costura dio verde con $rel roto"
    AGUANTAN=$((AGUANTAN + 1))
  elif [ -n "$espera" ] && ! grep -q -- "$espera" "$log"; then
    echo "  AGUANTA $nombre: cayó, pero no por «$espera» (la costura falló por otra cosa)"
    AGUANTAN=$((AGUANTAN + 1))
  else
    echo "  cae     $nombre: ${espera:-la costura lo vio}"
    CAEN=$((CAEN + 1))
  fi
  # Se devuelve el fichero a su sitio: la mutación siguiente tiene que medir SU
  # rotura, no la suma de todas (el 8 corría la suite con el bucle del 7 roto).
  rm -f "$TALLER/$rel"; cp "$REPO/$rel" "$TALLER/$rel"
  return 0
}

# 1 · si `Elige` deja de ser puro, `Prueba6` no lo puede compilar en el portátil.
muta "Elige deja de ser puro" "$ELIGE" \
  'import java.text.Normalizer;' \
  'import android.content.Context;
import java.text.Normalizer;' \
  "F15 · Elige puro"

# 2 · dos dueños para la misma decisión: el puente empieza a elegir presets y
#     `Ecualizador` también. Cada uno decidiría distinto.
muta "dos dueños para el preset" "$PUENTE" \
  'int cual = Elige.mejor(pedida, candidatas);' \
  'int cual = Elige.mejor(pedida, candidatas);
        int otro = Elige.preset(pedida, new java.util.ArrayList<String>());' \
  "F15 · dueño de Elige"

# 3 · el ecualizador se cuela en la suite de papel, donde no existe el Android
#     Equalizer: el verde de `prueba-mente.sh` sería de cartón.
muta "el ecualizador entra en la suite de papel" "$SH" \
  '"$E"/Despertar.java "$T/src/com/cort/ia/"' \
  '"$E"/Despertar.java "$E"/Ecualizador.java "$T/src/com/cort/ia/"' \
  "F15 · ecualizador"

# 4 · se engancha a una sesión que no es la del reproductor. El código compila y
#     la cara dice «hecho», pero el efecto no toca esa música.
muta "el ecualizador se engancha a la sesión equivocada" "$REP" \
  'Ecualizador.engancha(m.getAudioSessionId())' \
  'Ecualizador.engancha(0)' \
  "F15 · reproductor"

# 5 · la sección de música por nombre pierde la guardia: en un APK viejo corre
#     igual y cada frase de música acaba en un error de puente.
muta "la música por nombre sin guardia" "$TEL" \
  "if (puede('musicaPonerNombre')) {" \
  "if (true) {" \
  "F15 · las teclas"

# 6 · «pon la canción X» pierde su intención. Se cambia en el asset Y en la cara
#     para que no caiga por el 29 (las dos bocas siguen diciendo lo mismo) sino
#     por el 30, que es quien exige que esa intención exista.
if [ -z "$SOLO" ] || printf '%s' "«pon» vuelve a abrir apps" | grep -qi -- "$SOLO"; then
  rm -f "$TALLER/$JSON_APK" "$TALLER/$DIC"
  cp "$REPO/$JSON_APK" "$TALLER/$JSON_APK"
  cp "$REPO/$DIC" "$TALLER/$DIC"
  python3 - "$TALLER" "$JSON_APK" "$DIC" <<'PY'
import pathlib, sys
taller, j, d = map(pathlib.Path, sys.argv[1:])
for p in (taller / j, taller / d):
    t = p.read_text(encoding="utf-8")
    p.write_text(t.replace('"musica-pon-nombre"', '"musica-poner-viejo"'), encoding="utf-8")
PY
  log="$TALLER/salida.log"
  if python3 "$TALLER/scripts/prueba-costura.py" > "$log" 2>&1; then
    echo "  AGUANTA «pon» vuelve a abrir apps: la costura dio verde sin la intención"
    AGUANTAN=$((AGUANTAN + 1))
  elif ! grep -q "F15 · el diccionario" "$log"; then
    echo "  AGUANTA «pon» vuelve a abrir apps: cayó, pero no por el diccionario"
    AGUANTAN=$((AGUANTAN + 1))
  else
    echo "  cae     «pon» vuelve a abrir apps: F15 · el diccionario lo vio"
    CAEN=$((CAEN + 1))
  fi
  for rel in "$JSON_APK" "$DIC"; do
    rm -f "$TALLER/$rel"; cp "$REPO/$rel" "$TALLER/$rel"
  done
fi

# 7 · `Prueba6` fuera del bucle: la suite daría verde sin haber mirado una sola
#     elección de canción.
muta "Prueba6 fuera del bucle" "$SH" \
  'for suite in Prueba Prueba2 Prueba3 Prueba4 Prueba5 Prueba6 Prueba7; do' \
  'for suite in Prueba Prueba2 Prueba3 Prueba4 Prueba5 Prueba7; do' \
  "F15 · la suite enchufada"

# 8 · y la única que corre la suite de verdad: con el umbral a cero, `Elige`
#     elige «algo» para cualquier frase y «lo que no está» deja de quedarse en —.
if [ -z "$SOLO" ] || printf '%s' "Elige elige siempre algo" | grep -qi -- "$SOLO"; then
  for rel in "$JSON_APK" "$DIC"; do      # la mutación 6 ya no tiene que seguir puesta
    rm -f "$TALLER/$rel"; cp "$REPO/$rel" "$TALLER/$rel"
  done
  rm -f "$TALLER/$ELIGE"
  cp "$REPO/$ELIGE" "$TALLER/$ELIGE"
  if reemplaza "$ELIGE" 'return nota >= 200 ? mejor : -1;' 'return mejor;'; then
    log="$TALLER/mente.log"
    if bash "$TALLER/scripts/prueba-mente.sh" > "$log" 2>&1; then
      echo "  AGUANTA Elige elige siempre algo: la suite dio verde"
      AGUANTAN=$((AGUANTAN + 1))
    elif ! grep -q "FALLO  lo que no está se queda en —" "$log"; then
      echo "  AGUANTA Elige elige siempre algo: cayó, pero no por la canción que no está"
      AGUANTAN=$((AGUANTAN + 1))
    else
      echo "  cae     Elige elige siempre algo: Prueba6 lo vio («lo que no está»)"
      CAEN=$((CAEN + 1))
    fi
  else
    echo "  ???     Elige elige siempre algo: el reemplazo no encontró el umbral"
    AGUANTAN=$((AGUANTAN + 1))
  fi
fi

echo
if [ "$AGUANTAN" -gt 0 ]; then
  echo "TALLER F15 CON $AGUANTAN AGUANTE(S): hay comprobaciones que no prueban nada."
  exit 1
fi
[ "$CAEN" -eq 0 ] && echo "el filtro no casó con ninguna mutación" && exit 0
echo "TALLER F15 OK: $CAEN mutaciones, las $CAEN caen nombrando lo que faltaba."
