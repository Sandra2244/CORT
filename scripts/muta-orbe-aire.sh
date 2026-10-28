#!/usr/bin/env bash
# ── La batería de mutaciones de la pasada del orbe y del arranque (27/10) ──────────
#
# Diez mutaciones, una por pieza nueva: cada una deshace UN cambio concreto que se hizo
# mirando los dos videos de referencia, y tiene que volver roja SU comprobación nombrada.
# Si alguna queda verde, esa pieza no está vigilada: se puede volver a 7,2, a `animation:
# none` o a la cascada de ventanas sin que ninguna suite diga nada — que es exactamente
# como pasó la 2.16.0, cuando el orbe se quedó en «una bola de alambre» y sólo se veía en
# pantalla.
#
# Todo se restaura desde /tmp/respaldo-mut-orbe pase lo que pase (`trap`), y la restauración
# se certifica con `md5sum -c` sobre el manifiesto tomado ANTES de tocar nada.
#
# Uso:  bash scripts/muta-orbe-aire.sh      (una vez y media de la suite de costura: ~3 min)
cd /home/Sandra/Documentos/CORT || exit 1
PIT=/tmp/respaldo-mut-orbe
ARCH=(ui/js/orbe-plexo.js ui/js/orbe-cara.js ui/css/hud.css ui/js/hud.js)

mkdir -p "$PIT"
for f in "${ARCH[@]}"; do cp "$f" "$PIT/$(basename "$f")"; done
rm -f "$PIT/manifiesto.md5"
for f in "${ARCH[@]}"; do md5sum "$f" >> "$PIT/manifiesto.md5"; done

restaura() {
  local r
  for r in "${ARCH[@]}"; do cp "$PIT/$(basename "$r")" "$r"; done
}
trap restaura EXIT

# mut <nombre> <suite> <archivo> <texto viejo> <texto nuevo> <etiqueta que debe caerse>
mut() {
  local n="$1" suite="$2" a="$3" viejo="$4" nuevo="$5" e="$6"
  restaura
  python3 -c '
import pathlib, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
if sys.argv[2] not in t: sys.exit("NO APLICA")
p.write_text(t.replace(sys.argv[2], sys.argv[3], 1), encoding="utf-8")
' "$a" "$viejo" "$nuevo" || { echo "$n · ✗ la mutación no aplica ($viejo)"; return; }
  case "$suite" in
    orbe)      out=$(nice -n 19 node scripts/prueba-orbe.mjs 2>&1) ;;
    orbe-cara) out=$(nice -n 19 node scripts/prueba-orbe-cara.mjs 2>&1) ;;
    manto)     out=$(nice -n 19 node scripts/prueba-manto.mjs 2>&1) ;;
    costura)   out=$(nice -n 19 python3 scripts/prueba-costura.py 2>&1) ;;
  esac
  if grep -qF "$e" <<<"$out"; then echo "$n · muerde ✔";
  else echo "$n · ✘ NO MUERDE ($e quedó verde)"; fi
}

# [1-2] La lente: el tercio del alto que mide el video (§5.2), no el cuarto de la 2.16.0.
mut "M1 · la cámara vuelve a 7,2          " orbe-cara ui/js/orbe-plexo.js \
    'export const DISTANCIA = 5.8;' 'export const DISTANCIA = 7.2;' \
    'NO  la esfera queda a 5,8 de cámara'
mut "M2 · el PointSize deja de leerla     " orbe ui/js/orbe-plexo.js \
    '(${DISTANCIA} / max(0.5, -vis.z))' '(7.2 / max(0.5, -vis.z))' \
    'NO  la distancia de cámara es UN número'

# [3-6] El aire: lo de atrás se apaga (regla 1 del archivo — apagar, no borrar vértices).
mut "M3 · el fondo se mide sin inclinar   " orbe ui/js/orbe-plexo.js \
    'vFondo = clamp((-vis.z - (${DISTANCIA} - 1.0))' 'vFondo = clamp((-mv.z - (${DISTANCIA} - 1.0))' \
    'NO  y lo escribe la INCLINACIÓN'
mut "M4 · la declaración, desaparecida    " orbe ui/js/orbe-plexo.js \
    'varying float vFondo;' '' \
    'NO  vFondo se declara una sola vez'
mut "M5 · las líneas dejan de apagarse    " orbe ui/js/orbe-plexo.js \
    '* (1.0 - 0.72 * vFondo)' '* (1.0 - 0.00 * vFondo)' \
    'NO  las líneas se apagan el 72 % atrás'
mut "M6 · y los puntos también            " orbe ui/js/orbe-plexo.js \
    '* (1.0 - 0.45 * vFondo)' '* (1.0 - 0.45 * vBrillo)' \
    'NO  las líneas se apagan el 72 % atrás'

# [7-9] El fuego: el centro quemado del video, en el halo pintado y en cada mota.
mut "M7 · el halo, otra vez en colorB     " orbe ui/js/orbe-plexo.js \
    'opacity: 0.52, color: colorA.clone()' 'opacity: 0.52, color: colorB.clone()' \
    'NO  el núcleo del halo es el color primario'
mut "M8 · el anillo vuelve a encender     " orbe ui/js/orbe-plexo.js \
    '- 0.47 * portal' '+ 0.47 * portal' \
    'NO  la explosión da un portazo de luz'
mut "M9 · el núcleo de cada mota sin tope " orbe ui/js/orbe-plexo.js \
    'min(1.0, 0.75 * vCalor + 0.5 * nucleo)' '0.75 * vCalor + 0.5 * nucleo' \
    'NO  y cada punto tiene su núcleo blanco'

# [10] El freno de la dueña: apaga lo caro, no la cara.
mut "M10 · el freno mata la ola otra vez  " costura ui/css/hud.css \
    'html.freno #agua{filter:none;opacity:.14}' \
    'html.freno #agua{filter:none;opacity:.14;animation:none;transform:none}' \
    'el agua con freno'

# [11-12] El arranque: la cara se queda con el orbe solo, sin cascada de ventanas.
mut "M11 · la cascada vuelve al arranque  " manto ui/js/hud.js \
    'setTimeout(chipNotes, mobile() ? 2200 : 2600);' \
    'W.chat.show(); setTimeout(chipNotes, 2600);' \
    'NO  el arranque deja el orbe solo'
mut "M12 · y el saludo del celular se calla" manto ui/js/hud.js \
    "speakTTS('Sistemas en línea. CORT a sus órdenes.'), 600);" \
    "speakTTS('Nada'), 600);" \
    'NO  y el saludo hablado del teléfono no se pierde'

restaura
if md5sum -c "$PIT/manifiesto.md5" >/dev/null 2>&1; then
  echo "restaurado: los cuatro archivos vuelven a ser los de antes (md5 conforme)"
else
  echo "CUIDADO: la restauración no coincidió -- revisar ui/js, ui/css y $PIT"
  md5sum -c "$PIT/manifiesto.md5" || true
fi
