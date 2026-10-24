#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# taller-mandos.sh — las mutaciones de F12: «un verde que no puede caerse no es
# prueba». Aquí se rompe a mano cada cosa que la ronda arregló y se exige que la
# suite que la vigila se ponga ROJA nombrando lo que falta. Después se restaura.
#
# No va en `build.yml` a propósito, igual que los talleres de modelos y de Ollama:
# mutar el árbol durante el pipeline convertiría el CI en un sitio donde el código
# cambia solo. Se corre en el portátil, que es donde se mide.
#
#   bash scripts/taller-mandos.sh
#
# Cada caso dice: archivo, texto exacto que se rompe, con qué se sustituye y qué
# suite tiene que caer. Si una mutación NO tumba su suite, se informa como
# «AGUANTÓ» y el taller termina en rojo: eso significa que la comprobación no
# prueba lo que dice probar.
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail
cd "$(dirname "$0")/.."

SAL=/tmp/cort-taller-mandos
rm -rf "$SAL"; mkdir -p "$SAL"

fallos=0
casos=0

# `cambia archivo busca pon` — sustitución EXACTA, una sola vez, con Python para
# no pelear con las comillas de las expresiones regulares de `mandos.js`.
cambia() {
  python3 - "$1" "$2" "$3" <<'PY'
import sys
ruta, busca, pon = sys.argv[1], sys.argv[2], sys.argv[3]
t = open(ruta, encoding="utf-8").read()
if t.count(busca) != 1:
    sys.exit(f"el texto aparece {t.count(busca)} veces, se esperaba 1: {busca[:60]!r}")
open(ruta, "w", encoding="utf-8").write(t.replace(busca, pon, 1))
PY
}

# `mide nombre archivo busca pon comando...` — rompe, corre, exige rojo, restaura.
mide() {
  local nombre="$1" arch="$2" busca="$3" pon="$4"; shift 4
  casos=$((casos + 1))

  local resp="$SAL/$casos.$(basename "$arch")"
  cp "$arch" "$resp"

  if ! cambia "$arch" "$busca" "$pon" 2>"$SAL/$casos.err"; then
    echo "  ROTO  $nombre"
    sed 's/^/        /' "$SAL/$casos.err"
    cp "$resp" "$arch"
    fallos=$((fallos + 1))
    return 0
  fi

  if "$@" >"$SAL/$casos.log" 2>&1; then
    echo "  AGUANTÓ  $nombre — la suite siguió en verde con el fallo dentro"
    sed -n '1,6p' "$SAL/$casos.log" | sed 's/^/        /'
    fallos=$((fallos + 1))
  else
    local pista
    pista=$(grep -E '^  NO ' "$SAL/$casos.log" | head -2 | tr '\n' ' ')
    [ -n "$pista" ] || pista=$(grep -E 'FALLA|Traceback|Error|error' "$SAL/$casos.log" | head -2 | tr '\n' ' ')
    echo "  cae   $nombre — ${pista:0:150}"
  fi
  cp "$resp" "$arch"
}

echo "== taller de F12: 11 mutaciones, dos capas"
echo "   node  → la tabla pura de los mandos (63 comprobaciones)"
echo "   python→ la costura [27] (ducking, teclas, freno de la música)"

# ── la tabla pura: el punto del reconocedor ──────────────────────────────────
mide "mandos · el punto vuelve a no limpiarse" \
  ui/js/mandos.js \
  '.,;:!?»«¡¿]+$/g' \
  '»«¡¿]+$/g' \
  node scripts/prueba-mandos.mjs

mide "mandos · se casa la frase cruda, sin paraCasar" \
  ui/js/mandos.js \
  'export function mandoDe(msg) {
  const m = paraCasar(msg);' \
  'export function mandoDe(msg) {
  const m = String(msg ?? "");' \
  node scripts/prueba-mandos.mjs

# ── la tabla pura: los destinos ──────────────────────────────────────────────
mide "mandos · la pausa deja de tener tecla para otra app" \
  ui/js/mandos.js \
  "{ id: 'pausa', met: 'musicaPausa', tecla: 'pausa'" \
  "{ id: 'pausa', met: 'musicaPausa', tecla: null" \
  node scripts/prueba-mandos.mjs

mide "mandos · lo propio ya no va al reproductor de CORT" \
  ui/js/mandos.js \
  "if (mio) return { a: 'propio'" \
  "if (false) return { a: 'propio'" \
  node scripts/prueba-mandos.mjs

mide "mandos · otra app cae siempre en «sin teclas»" \
  ui/js/mandos.js \
  "return teclas ? { a: 'ajeno'" \
  "return false ? { a: 'ajeno'" \
  node scripts/prueba-mandos.mjs

mide "mandos · promete la pausa aunque no haya teclas" \
  ui/js/mandos.js \
  "dijo: ruta.a === 'propio' ? mando.dijo(estado.e, m)" \
  "dijo: true ? mando.dijo(estado.e, m)" \
  node scripts/prueba-mandos.mjs

mide "mandos · «cuadro» se lo come en cualquier frase larga" \
  ui/js/mandos.js \
  '              && m.split(/\s+/).length <= 3)' \
  '              )' \
  node scripts/prueba-mandos.mjs

# ── la costura [27]: Oido → puente → cara → suite ───────────────────────────
mide "costura · el oído pide foco sin permiso para agachar" \
  apps/apk/src/com/cort/ia/Oido.kt \
  'AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK' \
  'AudioManager.AUDIOFOCUS_GAIN' \
  python3 scripts/prueba-costura.py

mide "costura · el foco no se devuelve (música agachada para siempre)" \
  apps/apk/src/com/cort/ia/Oido.kt \
  'abandonAudioFocusRequest' \
  'abandonAudioFocusOlvidado' \
  python3 scripts/prueba-costura.py

mide "costura · Java renombra la tecla y la cara manda «pausa»" \
  apps/apk/src/com/cort/ia/CortNative.java \
  'case "pausa":' \
  'case "pause":' \
  python3 scripts/prueba-costura.py

mide "costura · la cara vuelve a cerrar el oído por música" \
  ui/js/voice.js \
  'if (hayMusica() && !puedeDuckear()) return' \
  'if (hayMusica()) return' \
  python3 scripts/prueba-costura.py

# ── el código limpio tiene que volver a verde ────────────────────────────────
echo
echo "== el árbol restaurado vuelve a verde"
if ! node scripts/prueba-mandos.mjs >"$SAL/limpio-mandos.log" 2>&1; then
  echo "  ROJO  prueba-mandos después de restaurar"; tail -8 "$SAL/limpio-mandos.log"; fallos=$((fallos+1))
else
  echo "  ok    prueba-mandos: $(grep -o '[0-9]* comprobaciones' "$SAL/limpio-mandos.log" | tail -1)"
fi
if ! python3 scripts/prueba-costura.py >"$SAL/limpio-costura.log" 2>&1; then
  echo "  ROJO  prueba-costura después de restaurar"; tail -8 "$SAL/limpio-costura.log"; fallos=$((fallos+1))
else
  echo "  ok    prueba-costura: $(grep -c 'F12 ·' "$SAL/limpio-costura.log") líneas de F12 en verde"
fi

echo
if [ "$fallos" -ne 0 ]; then
  echo "taller en ROJO: $fallos de $casos mutaciones no se comportaron como debían."
  exit 1
fi
echo "taller en verde: $casos mutaciones, todas caen y el árbol limpio vuelve a dar verde."
