#!/usr/bin/env bash
# Taller de mutaciones de F17: «cambiar traje ⇒ cambian TODOS los colores del orbe».
#
# Por qué existe: **un verde que no puede caerse no es prueba.** El sector [32] de
# `scripts/prueba-costura.py` vigila las costuras de la cara vestida, y
# `prueba-colores.mjs` mide la derivación pura. Aquí se rompe a propósito —una
# mutación por cada promesa— para exigir que el verde se ponga rojo Y que el rojo
# NOMBRE la comprobación que faltaba. Si el código roto sigue verde, la prueba es
# decoración: el orbe volvería a amanecer azul con Matrix puesto, la burbuja a ser
# un punto quieto, o el agua a animarse en el teléfono de 4 GB.
#
# Qué se rompe, en una línea: que los dieciséis canales existan y se pinten, que
# la cara llame a `vestir` al cambiar y al arrancar con el traje guardado, que la
# tabla de `prueba-colores.mjs` siga casando con `Paleta.java` y corra en el
# pipeline, que la burbuja conserve reposo/arrastre/modo juego con sus 44 dp, que
# el freno lo pongan la poca RAM y el juego, y que la sonda se quede fuera del
# APK. Las dos últimas mutaciones corren la prueba de node entera: sólo ella ve
# que una partícula se congela en el cian de fábrica o que el secundario se cuela
# donde manda el primario.
#
# Dónde se corre: en el taller, NUNCA como paso del pipeline. Trabaja sobre una
# copia de links duros en `/tmp`; rompe el link antes de tocar, así que el repo
# no se entera.
#
# Uso:  bash scripts/taller-f17.sh              (≈1 minuto)
#       bash scripts/taller-f17.sh particulars  (sólo las que digan eso)
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TALLER="$(mktemp -d /tmp/cort-taller-f17-XXXXXX)"
trap 'rm -rf "$TALLER"' EXIT

for d in ui apps backend desktop scripts .github; do
  cp -al "$REPO/$d" "$TALLER/$d" 2>/dev/null || cp -a "$REPO/$d" "$TALLER/$d"
done

TRAJE="ui/js/traje.js"
ORB="ui/js/orb.js"
TEL="ui/js/telefono.js"
PAN="ui/js/pantallas.js"
HTML="ui/index.html"
CSS="ui/css/hud.css"
FLOT="apps/apk/src/com/cort/ia/Flotante.java"
PALETA="apps/apk/src/com/cort/ia/Paleta.java"
COL="scripts/prueba-colores.mjs"
SONDA="ui/sonda-colores.html"
YML=".github/workflows/build.yml"
COMP="apps/apk/compilar.sh"

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

restaura() {
  rm -f "$TALLER/$1"
  cp "$REPO/$1" "$TALLER/$1"
}

muta() {  # muta <nombre> <archivo> <de> <a> [esperado]
  local nombre="$1" rel="$2" viejo="$3" nuevo="$4" espera="${5:-}"
  if [ -n "$SOLO" ] && ! printf '%s' "$nombre" | grep -qi -- "$SOLO"; then
    return 0
  fi
  restaura "$rel"
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
  restaura "$rel"
}

muta_node() {  # muta_node <nombre> <archivo> <de> <a> [esperado]
  local nombre="$1" rel="$2" viejo="$3" nuevo="$4" espera="${5:-}"
  if [ -n "$SOLO" ] && ! printf '%s' "$nombre" | grep -qi -- "$SOLO"; then
    return 0
  fi
  restaura "$rel"
  if ! reemplaza "$rel" "$viejo" "$nuevo"; then
    echo "  ???     $nombre: el reemplazo no encontró el texto (mutación mal escrita)"
    AGUANTAN=$((AGUANTAN + 1))
    return
  fi
  local log="$TALLER/colores.log"
  if node "$TALLER/scripts/prueba-colores.mjs" > "$log" 2>&1; then
    echo "  AGUANTA $nombre: prueba-colores dio verde con $rel roto"
    AGUANTAN=$((AGUANTAN + 1))
  elif [ -n "$espera" ] && ! grep -q -- "$espera" "$log"; then
    echo "  AGUANTA $nombre: cayó, pero no por «$espera»"
    AGUANTAN=$((AGUANTAN + 1))
  else
    echo "  cae     $nombre: prueba-colores lo vio («$espera»)"
    CAEN=$((CAEN + 1))
  fi
  restaura "$rel"
}

# 1 · un canal menos: el orbe y la prueba dejarían de medir lo mismo, y ese
#     material se quedaría con el color del traje anterior sin que nadie lo vea.
muta "un canal menos en traje.js" "$TRAJE" \
  "  'chispa', 'onda'," \
  "  'chispa'," \
  "F17 · el orbe vestido"

# 2 · `aplica()` deja de pintar las chispas: el portal saldría con el azul de
#     fábrica aunque el HUD esté en Matrix.
muta "aplica no pinta las chispas" "$ORB" \
  "    spkMat.uniforms.uColor.value.set(c.chispa);
" \
  "" \
  "F17 · el orbe vestido"

# 3 · vuelve un color fijo al shader de partículas: cambiar de traje pintaría
#     dieciséis menos una, y esa una es la cáscara entera.
muta "vuelve un color fijo al orbe" "$ORB" \
  "uColor: { value: new THREE.Color(colores.particula) }," \
  "uColor: { value: new THREE.Color(0x4fc6ff) }," \
  "F17 · el orbe vestido"

# 4 · la cara cambia el CSS pero no avisa al orbe: el HUD se viste y la bola se
#     queda con el traje anterior hasta recargar.
muta "la cara no viste el orbe" "$TEL" \
  "if (p || s) ctx?.orb?.vestir?.(p, s);" \
  "if (p || s) { /* muda */ }" \
  "F17 · la cara viste"

# 5 · al abrir CORT no se aplica el traje guardado: con Matrix puesto el orbe
#     amanecería azul hasta que la dueña volviera a elegirlo.
muta "al montar no se aplica el puesto" "$TEL" \
  "      vistePuesto();
" \
  "" \
  "F17 · la cara viste"

# 6 · el `puesto` se busca mal: se coge el primero de la lista (Cortana) en vez
#     del que Java tiene guardado.
muta "el puesto se busca mal" "$TEL" \
  "const a = estado.atuendos.find(x => x.nombre === estado.puesto);" \
  "const a = estado.atuendos[0];" \
  "F17 · la cara viste"

# 7 · un color de `Paleta.java` cambia y la prueba no se entera: mediría un cian
#     que el teléfono ya no tiene.
muta "Paleta y prueba se separan" "$PALETA" \
  '{"JARVIS",    "#ffc46b", "#241405"},' \
  '{"JARVIS",    "#ffc46c", "#241405"},' \
  "F17 · la prueba de colores"

# 8 · la prueba deja de exigir los dieciséis: un canal olvidado pasaría en verde.
muta "la prueba deja de exigir dieciséis" "$COL" \
  "CLAVES.length === 16" \
  "CLAVES.length === 15" \
  "F17 · la prueba de colores"

# 9 · el paso sale del pipeline: la prueba existiría y nadie la correría.
muta "el paso sale del pipeline" "$YML" \
  "node scripts/prueba-colores.mjs > /tmp/colores.log 2>&1" \
  "true > /tmp/colores.log 2>&1" \
  "F17 · la prueba de colores"

# 10 · la burbuja crece más de 44 dp: cambia el contrato de la sección 6 y tapa
#      más de lo que la dueña aceptó.
muta "la burbuja crece de 44 dp" "$FLOT" \
  "private static final int DIAMETRO_DP = 44;" \
  "private static final int DIAMETRO_DP = 48;" \
  "F17 · la burbuja 1.1.4"

# 11 · el modo juego deja de ir primero: el punto aparecería encima de la partida.
muta "el modo juego deja de ir primero" "$FLOT" \
  "if (juego(app)) {" \
  "if (juego(app) && false) {" \
  "F17 · la burbuja 1.1.4"

# 12 · la burbuja vuelve a robar el foco: escribiría en ella en vez de en la app
#      de debajo.
muta "la burbuja roba el foco" "$FLOT" \
  "WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE" \
  "WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL" \
  "F17 · la burbuja 1.1.4"

# 13 · el freno deja de mirar la RAM: el portátil de 1,8 GiB volvería a animar el
#      agua y a pagar el `backdrop-filter`.
muta "el freno no mira la RAM" "$PAN" \
  "return Number.isFinite(g) && g > 0 && g <= 2;" \
  "return Number.isFinite(g) && g > 0 && g <= 0;" \
  "F17 · el agua con freno"

# 14 · el freno deja de apagar el agua: la clase se pone y la ola sigue.
muta "el freno no apaga el agua" "$CSS" \
  "html.freno #agua{filter:none;opacity:.08;animation:none;transform:none}" \
  "#agua.freno{filter:none;opacity:.08;animation:none;transform:none}" \
  "F17 · el agua con freno"

# 15 · la capa de agua desaparece del HTML: el CSS la animaría sin nada que pintar
#      (o al revés: la dueña pide agua y no hay).
muta "sin capa de agua" "$HTML" \
  '<div id="agua" aria-hidden="true"></div>' \
  '' \
  "F17 · el agua con freno"

# 16 · la sonda pierde un traje: enseñaría cinco y rompería la promesa de los seis.
muta "la sonda pierde un traje" "$SONDA" \
  "  ['Neutron',   '#e8eef2', '#1b2226']," \
  "" \
  "F17 · la sonda"

# 17 · el pipeline deja de descartar `sonda-*.html`: la sonda viajaría dentro del
#      APK y engordaría la cara sin hacer nada.
muta "la sonda viaja en el APK" "$COMP" \
  "find assets/ui -maxdepth 1 -name 'sonda-*.html' -delete" \
  "true" \
  "F17 · la sonda"

# 18 · la partícula se congela en el cian de fábrica: el HUD cambiaría de traje y
#      la cáscara de 2.600 puntos se quedaría azul. La costura no lo ve porque
#      `aplica()` sigue llamando al canal; sólo la prueba pura lo mide.
muta_node "la partícula se congela" "$TRAJE" \
  "    particula: aHex(p),                           // cáscara de 2.600 partículas" \
  "    particula: POR_DEFECTO.primario,               // mutación: congelada" \
  "cambian LOS DIECISÉIS colores del orbe"

# 19 · el secundario se cuela en la partícula: cambiar sólo el borde del traje
#      movería también el color de la cáscara, que debe mandarlo el primario.
muta_node "el secundario se cuela" "$TRAJE" \
  "    particula: aHex(p),                           // cáscara de 2.600 partículas" \
  "    particula: aHex(s),                           // mutación: se cuela el secundario" \
  "y el primario no se mueve"

echo
if [ "$AGUANTAN" -gt 0 ]; then
  echo "TALLER F17 CON $AGUANTAN AGUANTE(S): hay comprobaciones que no prueban nada."
  exit 1
fi
[ "$CAEN" -eq 0 ] && echo "el filtro no casó con ninguna mutación" && exit 0
echo "TALLER F17 OK: $CAEN mutaciones, las $CAEN caen nombrando lo que faltaba."
