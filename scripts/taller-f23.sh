#!/usr/bin/env bash
# Taller de mutaciones de F23: «el Arnés de CORT».
#
# Por qué existe: la costura del sector [36] comprueba seis cosas que, si se
# caen, no duelen en la consola —duelen en el teléfono de la dueña—. El Arnés
# volvería a tener una lista de 91 intenciones escrita a mano (y se quedaría
# vieja a la primera ronda), pintaría de verde un puente que no contesta,
# esperaría al portátil antes de enseñar nada (hoja en blanco con el PC dormido),
# se abriría en negro por falta de su regla CSS, enseñaría una frase y ejecutaría
# otra, o la sonda dejaría de medirlo todo y seguiría verde. Aquí se rompe cada
# promesa a propósito y se exige que la costura se ponga roja Y que el rojo
# NOMBRE la comprobación que faltaba. Un verde que no puede caerse no prueba
# nada.
#
# Dónde se corre: en el taller, NUNCA como paso del pipeline. Trabaja sobre una
# copia de links duros en `/tmp`; rompe el link antes de tocar, así que el repo
# no se entera.
#
# Uso:  bash scripts/taller-f23.sh              (≈1 minuto)
#       bash scripts/taller-f23.sh sonda        (sólo las que digan eso)
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TALLER="$(mktemp -d /tmp/cort-taller-f23-XXXXXX)"
trap 'rm -rf "$TALLER"' EXIT

for d in ui apps backend desktop scripts .github docs; do
  cp -al "$REPO/$d" "$TALLER/$d" 2>/dev/null || cp -a "$REPO/$d" "$TALLER/$d"
done

ARNES="ui/js/arnes.js"
PANT="ui/js/pantallas.js"
CSS="ui/css/hud.css"
APPS="ui/css/apps.css"
SONDA="ui/sonda-carita.html"
DOC="docs/ARNES-CORT.md"

CAEN=0
AGUANTAN=0
SOLO="${1:-}"
[ -n "$SOLO" ] && echo "  (filtro: sólo las mutaciones que contienen «$SOLO»)"

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

# ── F23 · las cuentas y las fuentes ─────────────────────────────────────────

# 1 · el Arnés escribe 91/736 a mano: mañana el diccionario crece y la hoja
#     enseña una cuenta que no es la que ejecuta la voz.
muta "las cuentas a mano" "$ARNES" \
  '${TOTALES.intents} intenciones y ${TOTALES.frases}' \
  '91 intenciones y 736' \
  "F23 · las herramientas"

# 2 · el Arnés deja de leer `capacidades()`: el perfil y los seis servicios
#     saldrían del aire, no del manifiesto instalado.
muta "sin capacidades()" "$ARNES" \
  "  const caps = N && typeof N.capacidades === 'function'
    ? objeto(intenta(() => N.capacidades(), '')) : {};" \
  "  const caps = {};" \
  "F23 · las fuentes"

# 3 · el Arnés se olvida del estado de la música: la fila de Salud mentiría con
#     «en silencio» mientras suena una canción.
muta "sin musicaEstado()" "$ARNES" \
  "  const musi = N && typeof N.musicaEstado === 'function'
    ? objeto(intenta(() => N.musicaEstado(), '')) : {};" \
  "  const musi = {};" \
  "F23 · las fuentes"

# 4 · el Arnés pide un permiso: es un tablero, y la dueña ya dijo que nada nuevo
#     se pide sin decir el precio.
muta "el Arnés pide permiso" "$ARNES" \
  "  const camara = N && typeof N.hasPermission === 'function'" \
  "  N.requestPermission('camara');
  const camara = N && typeof N.hasPermission === 'function'" \
  "F23 · los permisos"

# 5 · el Arnés espera al portátil antes de pintar: con el PC dormido la hoja se
#     queda en blanco 1,8 s, que es justo lo que la lectura local evitaba.
muta "pinta después del PC" "$ARNES" \
  "  pinta();                              // primero lo del aparato, sin esperar al PC" \
  "  void 0;" \
  "F23 · el orden"

# ── F23 · la hoja y sus ejemplos ────────────────────────────────────────────

# 6 · la hoja del Arnés deja de encenderse: se monta y se queda en negro (el
#     mismo fallo que tuvo el Centro el 2026-10-24).
muta "la hoja no se enciende" "$CSS" \
  "html.pantallas-montadas.p-arnes #scr-arnes{display:flex}" \
  "html.pantallas-montadas.p-arnes-viejo #scr-arnes{display:flex}" \
  "F23 · la hoja"

# 7 · el cuerpo vuelve a `display:flex`: las cajas se comprimen y las filas de
#     Salud dejan de leerse.
muta "el cuerpo vuelve a flex" "$APPS" \
  "#scr-arnes .scr-cuerpo{display:block;overflow-y:auto" \
  "#scr-arnes .scr-cuerpo{display:flex;overflow-y:auto" \
  "F23 · la hoja"

# 8 · la dirección del núcleo se congela al montar: cambiarla en Equipo ▸ 9 · PC
#     dejaría al Arnés mirando el PC viejo.
muta "la api congelada" "$PANT" \
  "api: () => (ctx?.api ? ctx.api() : '')" \
  "api: () => ''" \
  "F23 · la hoja"

# 9 · tocar un ejemplo manda una frase fija: enseñaría una orden y ejecutaría
#     otra, y las dos listas se separarían a la primera ronda.
muta "el ejemplo manda otra frase" "$ARNES" \
  "texto: frase.dataset.frase" \
  "texto: 'sube el volumen'" \
  "F23 · los ejemplos"

# 10 · el Arnés no muestra los cinco datos del puente que sí existen: sin
#      `memoria` se quedaría con una caja de Memoria vacía y sin decirlo.
muta "sin memoria()" "$ARNES" \
  "  const mem = N && typeof N.memoria === 'function'
    ? objeto(intenta(() => N.memoria('{\"que\":\"estado\"}'), '')) : {};" \
  "  const mem = { ok: true, hechos: 0, recuerdos: 0, habilidades: 0 };" \
  "F23 · las fuentes"

# ── F23 · la sonda y el documento ───────────────────────────────────────────

# 11 · la sonda deja de entrar en el Arnés: la hoja podría estar vacía y seguir
#      verde, que es el fallo que este taller existe para cazar.
muta "la sonda no entra" "$SONDA" \
  "m.ir('arnes');" \
  "m.ir('orbe');" \
  "F23 · la sonda"

# 12 · el documento deja de escribir lo que CORT NO hace: la arquitectura vuelve
#      a ser una promesa suelta.
muta "el documento promete de más" "$DOC" \
  "## 4 · Lo que el Arnés NO promete" \
  "## 4 · Lo que el Arnés sí promete" \
  "F23 · el documento"

echo
echo "taller F23: $CAEN caen, $AGUANTAN aguantan"
[ "$AGUANTAN" -eq 0 ]
