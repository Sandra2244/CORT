#!/usr/bin/env bash
# Cinco mutaciones sobre el corte 3: cada una borra UNA pieza del marco nuevo y tiene que
# volver roja su comprobación en `prueba-costura.py`. Si alguna queda verde, la red está
# aflojada. Todo se restaura desde /tmp/respaldo-mut al final, pase lo que pase.
cd /home/Sandra/Documentos/CORT || exit 1
PIT=/tmp/respaldo-mut

restaura() { cp "$PIT/marco.js" ui/js/marco.js; cp "$PIT/pantallas.js" ui/js/pantallas.js; }
trap restaura EXIT

mut() {   # mut <nombre> <archivo> <cadena> <etiqueta que debe caerse>
  local n="$1" a="$2" c="$3" e="$4"
  restaura
  python3 -c '
import pathlib, sys
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
if sys.argv[2] not in t: sys.exit("NO APLICA")
p.write_text(t.replace(sys.argv[2], "", 1), encoding="utf-8")
' "$a" "$c" || { echo "$n · ✗ la mutación no aplica ($c)"; return; }
  out=$(python3 scripts/prueba-costura.py 2>&1)
  if grep -q "^  NO  $e" <<<"$out"; then echo "$n · muerde ✔"; else echo "$n · ✘ NO MUERDE ($e verde)"; fi
}

mut "A · sin alEntrar del Centro   " ui/js/pantallas.js "alEntrar('centro', pintaCentro);"        "F19 · el Centro"
mut "B · sin despachar el registro " ui/js/marco.js     "ENTRADAS.get(actual)?.();"               "F19 · el Centro"
mut "C · MV sin escondida          " ui/js/marco.js     "escondida: true"                          "letra fusionada"
mut "D · sin fila del Arnés        " ui/js/marco.js     "{ id: 'arnes',"                           "F23 · la hoja"
mut "E · sin alEntrar del Arnés    " ui/js/pantallas.js "alEntrar('arnes', pintaArnes);"           "F23 · la hoja"
mut "F · sin fila del Centro       " ui/js/marco.js     "{ id: 'centro'"                           "F19 · el Centro"
mut "G · sin la fila de mv         " ui/js/marco.js     "{ id: 'mv',"                              "MV"

restaura
if cmp -s $PIT/marco.js ui/js/marco.js && cmp -s $PIT/pantallas.js ui/js/pantallas.js; then
  echo "restaurado: los dos archivos vuelven a ser los de antes"
else
  echo "CUIDADO: la restauración no coincidió -- revisar ui/js"
fi
