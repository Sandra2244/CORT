#!/usr/bin/env bash
# Siete mutaciones sobre el corte 4 (`codigo.js`): cada una borra UNA pieza del corte y
# tiene que volver roja SU comprobación nombrada. Si alguna queda verde, la red está
# aflojada y el corte no está vigilado. Todo se restaura desde /tmp/respaldo-mut4 al
# final, pase lo que pase (`trap`), y se comprueba con `cmp` que los archivos vuelven a
# ser los de antes.
#
# La línea 33.b («la lista de la cara») nació en el corte 3 y ESTAS mutaciones son las
# que descubrieron que estaba vacía: comparaba `p.parent == UI` con `UI = ui/`, y los
# módulos viven en `ui/js`, así que nunca podía encontrar a nadie. M1 la deja roja con
# `codigo.js` fuera de la lista; si el filtro vuelve a estar roto, M1 queda verde.
cd /home/Sandra/Documentos/CORT || exit 1
PIT=/tmp/respaldo-mut4
mkdir -p "$PIT"
for a in ui/js/pantallas.js ui/js/codigo.js ui/js/marco.js scripts/lib-cara.mjs; do
  cp "$a" "$PIT/$(basename "$a")"
done

restaura() {
  # Ojo con el nombre de la variable: bash tiene alcance DINÁMICO, y si aquí se
  # reutilizara `a` pisaría el `local a` de `mut` (que llama a esta función antes de
  # mutar) y todas las mutaciones acabarían apuntando a `marco.js`.
  local f
  for f in pantallas.js codigo.js marco.js; do
    cp "$PIT/$f" "ui/js/$f"
  done
  cp "$PIT/lib-cara.mjs" scripts/lib-cara.mjs
}
trap restaura EXIT

# mut <nombre> <suite> <archivo> <cadena> <etiqueta que debe caerse>
mut() {
  local n="$1" suite="$2" a="$3" c="$4" e="$5"
  restaura
  python3 -c '
import pathlib, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
if sys.argv[2] not in t: sys.exit("NO APLICA")
p.write_text(t.replace(sys.argv[2], "", 1), encoding="utf-8")
' "$a" "$c" || { echo "$n · ✗ la mutación no aplica ($c)"; return; }
  case "$suite" in
    costura) out=$(python3 scripts/prueba-costura.py 2>&1) ;;
    pasos)   out=$(node scripts/prueba-pasos.mjs 2>&1) ;;
  esac
  if grep -qF "$e" <<<"$out"; then echo "$n · muerde ✔"; else echo "$n · ✘ NO MUERDE ($e verde)"; fi
}

mut "M1 · codigo.js fuera de la lista   " costura scripts/lib-cara.mjs ", 'codigo.js'" \
    "33 · la lista de la cara"
mut "M2 · sin el alta del Código        " costura ui/js/pantallas.js \
    "alEntrar('codigo', pintaCodigo);" "33 · toda hoja tiene su entrada"
mut "M3 · sin exportar lo que la carcasa monta" costura ui/js/codigo.js \
    "export { montaCodigo, pintaCodigo };" "33 · enlaces de módulos"
mut "M4 · el ▶ fuera de la rama segura  " costura ui/js/codigo.js \
    "<button class=\"cp-b puesta\" data-ejecuta=\"" "copiloto · cara"
mut "M5 · el modo ya no se recuerda     " costura ui/js/codigo.js \
    "cort-copiloto" "copiloto · cara"
mut "M6 · la ruta del plan, desaparecida " costura ui/js/codigo.js \
    "/api/copiloto/plan" "copiloto · rutas"
mut "M7 · el verde del paso deja de pasar por arranca" pasos ui/js/codigo.js \
    "if (arranca(paso) !== 'corriendo') return;" 'NO  el verde pasa por `arranca`'

restaura
if cmp -s "$PIT/pantallas.js" ui/js/pantallas.js && cmp -s "$PIT/codigo.js" ui/js/codigo.js \
   && cmp -s "$PIT/marco.js" ui/js/marco.js && cmp -s "$PIT/lib-cara.mjs" scripts/lib-cara.mjs; then
  echo "restaurado: los cuatro archivos vuelven a ser los de antes"
else
  echo "CUIDADO: la restauración no coincidió -- revisar ui/js y scripts/lib-cara.mjs"
fi
