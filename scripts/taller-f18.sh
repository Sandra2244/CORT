#!/usr/bin/env bash
# Taller de mutaciones de F18 y F19: «el orbe con ánimo» y «el Centro de mando».
#
# Por qué existe: la costura del sector [34] comprueba cuatro cosas que, si se
# caen, no duelen en la consola —duelen en el teléfono de la dueña—. El orbe
# volvería a tener un solo aspecto mientras escucha, piensa y habla; el Centro
# se abriría en negro (pasó de verdad el 2026-10-24); su catálogo enseñaría una
# frase y ejecutaría otra; o los chips se comprimirían hasta desaparecer. Aquí se
# rompe cada promesa a propósito y se exige que la costura se ponga roja Y que el
# rojo NOMBRE la comprobación que faltaba. Un verde que no puede caerse no prueba
# nada.
#
# Qué se rompe, en una línea: que existan los cuatro estados y que un nombre
# desconocido caiga a reposo, que la lámpara de la cara los mande y que el Centro
# entre por el mismo `send()` que la voz, que la cáscara y los arcos se pinten de
# los dieciséis canales y respeten el freno, que la hoja del Centro se encienda
# con su cuerpo en bloque, que lea el diccionario y mande la frase que enseña, y
# que la sonda mida que la hoja se ve.
#
# Dónde se corre: en el taller, NUNCA como paso del pipeline. Trabaja sobre una
# copia de links duros en `/tmp`; rompe el link antes de tocar, así que el repo
# no se entera.
#
# Uso:  bash scripts/taller-f18.sh              (≈1 minuto)
#       bash scripts/taller-f18.sh centro       (sólo las que digan eso)
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TALLER="$(mktemp -d /tmp/cort-taller-f18-XXXXXX)"
trap 'rm -rf "$TALLER"' EXIT

for d in ui apps backend desktop scripts .github; do
  cp -al "$REPO/$d" "$TALLER/$d" 2>/dev/null || cp -a "$REPO/$d" "$TALLER/$d"
done

TRAJE="ui/js/traje.js"
ORB="ui/js/orb.js"
HUD="ui/js/hud.js"
CENTRO="ui/js/centro.js"
PANT="ui/js/pantallas.js"
CSS="ui/css/hud.css"
APPS="ui/css/apps.css"
SONDA="ui/sonda-carita.html"

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

# ── F18 · el orbe con ánimo ──────────────────────────────────────────────────

# 1 · el orbe pierde «piensa»: volvería a verse igual pensando que en reposo, y
#     la lámpara de la cara diría una cosa mientras la bola dice otra.
muta "el orbe pierde un estado" "$ORB" \
  "  piensa:  { amp: .150, vel: 2.20, rim: 1.75, arco: 1.00, pulso: .34, giro: 2.7 },
" \
  "" \
  "F18 · los cuatro estados"

# 2 · `estado()` deja de caer a reposo: un nombre que Java o la cara escriban
#     distinto dejaría el orbe clavado en el último ánimo para siempre.
muta "el estado no cae a reposo" "$ORB" \
  "      return ponEstado(String(nombre).toLowerCase());" \
  "      return estadoNom;" \
  "F18 · los cuatro estados"

# 3 · la lámpara no traduce «pensando»: la cara diría «pensando» y el orbe
#     seguiría respirando como en reposo.
muta "la lámpara no traduce pensando" "$HUD" \
  "escucha: 'escucha', pensando: 'piensa'," \
  "escucha: 'escucha', pensando: 'reposo'," \
  "F18 · la lámpara manda"

# 4 · el Centro deja de entrar por el `send()` de la voz: el catálogo se vería
#     completo y tocar una orden no haría nada.
muta "el Centro no ejecuta" "$HUD" \
  "    if (texto) send(texto);" \
  "    if (texto) { /* muda */ }" \
  "F18 · la lámpara manda"

# 5 · la cáscara no pasa por `aplica()`: con Matrix puesto se quedaría con el
#     cian de fábrica, que es el bug de F17 otra vez.
muta "la cáscara no se pinta" "$ORB" \
  "    shellMat.uniforms.uColor.value.set(c.hilos);
" \
  "" \
  "F18 · los cuatro estados"

# 6 · la cáscara ignora el freno: en el teléfono de 4 GB se dibujaría igual y el
#     ahorro de la sección 6 sería mentira.
muta "la cáscara no respeta el freno" "$ORB" \
  "    shell.visible = !frenoOn && (vx + pox + dm) < .55;" \
  "    shell.visible = (vx + pox + dm) < .55;" \
  "F18 · los cuatro estados"

# 7 · los arcos ignoran el freno: la mitad visual del orbe seguiría animándose
#     aunque la clase `freno` esté puesta.
muta "los arcos no respetan el freno" "$ORB" \
  "      a.m.visible = !frenoOn;" \
  "      a.m.visible = true;" \
  "F18 · los cuatro estados"

# 8 · un canal menos: la cáscara comparte los dieciséis a propósito, y con quince
#     uno de los dos trajes se quedaría a medias sin que nadie lo viera.
muta "un canal menos" "$TRAJE" \
  "  'chispa', 'onda'," \
  "  'chispa'," \
  "F18 · los cuatro estados"

# ── F19 · el Centro de mando ─────────────────────────────────────────────────

# 9 · la hoja del Centro deja de encenderse: se monta y se queda en negro, que es
#     exactamente lo que pasó el 2026-10-24.
muta "la hoja del Centro no se enciende" "$CSS" \
  "html.pantallas-montadas.p-centro #scr-centro{display:flex}" \
  "html.pantallas-montadas.p-centro-viejo #scr-centro{display:flex}" \
  "F19 · el Centro"

# 10 · el Centro escribe una frase a mano: enseñaría una orden y ejecutaría otra,
#      y las dos listas se separarían a la primera ronda.
muta "el Centro escribe la frase a mano" "$CENTRO" \
  "texto: b.dataset.frase" \
  "texto: 'sube el volumen'" \
  "F19 · el Centro"

# 11 · el Centro deja de recibir `visibles()`: en el PC ofrecería Música o Equipo,
#      que allí no existen.
muta "el Centro no recibe visibles()" "$PANT" \
  "montaCentro(raiz, { ir, apps: visibles() })" \
  "montaCentro(raiz, { ir, apps: [] })" \
  "F19 · el Centro"

# 12 · `ir()` entra en el Centro pero no lo pinta: la hoja aparecería vacía.
muta "el Centro no se pinta al entrar" "$PANT" \
  "if (actual === 'centro') pintaCentro();" \
  "if (actual === 'centro') { /* muda */ }" \
  "F19 · el Centro"

# 13 · la búsqueda deja de plegar tildes: «razon» no encontraría «razón», y la
#      dueña escribiría sin tildes, que es como escribe.
muta "la búsqueda no pliega tildes" "$CENTRO" \
  ".normalize('NFD')" \
  ".normalize('NFC')" \
  "F19 · el Centro"

# 14 · el cuerpo del Centro vuelve a `display:flex`: los chips se comprimen a
#      14 px y su texto desaparece (pasó de verdad al montarlo).
muta "el cuerpo del Centro vuelve a flex" "$APPS" \
  "#scr-centro .scr-cuerpo{display:block;overflow-y:auto" \
  "#scr-centro .scr-cuerpo{display:flex;overflow-y:auto" \
  "F19 · el Centro"

# 15 · la sonda deja de medir que la hoja se ve: el fallo de la pantalla negra
#      volvería a pasar sin que ninguna prueba lo note.
muta "la sonda no mide la hoja" "$SONDA" \
  "getComputedStyle(\$('#scr-centro')).display === 'flex'" \
  "getComputedStyle(\$('#scr-centro')).display !== 'none'" \
  "F19 · la sonda"

echo
if [ "$AGUANTAN" -gt 0 ]; then
  echo "TALLER F18 CON $AGUANTAN AGUANTE(S): hay comprobaciones que no prueban nada."
  exit 1
fi
[ "$CAEN" -eq 0 ] && echo "el filtro no casó con ninguna mutación" && exit 0
echo "TALLER F18 OK: $CAEN mutaciones, las $CAEN caen nombrando lo que faltaba."
