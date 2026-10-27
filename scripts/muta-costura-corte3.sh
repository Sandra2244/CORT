#!/usr/bin/env bash
# Siete mutaciones sobre el corte 3 (A–G): cada una borra UNA pieza del marco nuevo o de su
# registro y tiene que volver roja SU comprobación nombrada. Si alguna queda verde, la red
# está aflojada.
#
# Por qué este guion se respalda a sí MISMO al empezar, y no usa una carpeta de otra ronda:
# el 27/10, tras el corte 4, esta batería se corrió con `/tmp/respaldo-mut` lleno por una
# sesión anterior —con un `pantallas.js` de 3.035 líneas, el de antes del corte 3, y un
# `marco.js` al que le faltaba `abreCajon`—. El `trap` restauró desde ese polvo y el repo
# perdió de golpe los dos cortes. Un respaldo que no se toma en el mismo proceso en el que
# se usa no es un respaldo: es una bomba de tiempo. Ahora el `cp` del principio congela el
# estado real del archivo, el `md5sum` del principio y del final lo certifica, y si algo
# sobra distinto, el guion sale rojo.
cd /home/Sandra/Documentos/CORT || exit 1
PIT=/tmp/respaldo-mut          # se pisa a propósito: siempre fresco
ARCHIVOS=(ui/js/marco.js ui/js/pantallas.js)
mkdir -p "$PIT"
for f in "${ARCHIVOS[@]}"; do
  cp "$f" "$PIT/$(basename "$f")"
done
md5sum "${ARCHIVOS[@]}" > "$PIT/md5-inicio"

restaura() {
  local f
  for f in "${ARCHIVOS[@]}"; do
    cp "$PIT/$(basename "$f")" "$f"
  done
}
trap restaura EXIT

# mut <nombre> <archivo> <cadena> <etiqueta que debe caerse>
mut() {
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
mut "B · sin despachar el registro " ui/js/marco.js     "ENTRADAS.get(actual)?.();"              "F19 · el Centro"
mut "C · MV sin escondida          " ui/js/marco.js     "escondida: true"                         "letra fusionada"
mut "D · sin fila del Arnés        " ui/js/marco.js     "{ id: 'arnes',"                          "F23 · la hoja"
mut "E · sin alEntrar del Arnés    " ui/js/pantallas.js "alEntrar('arnes', pintaArnes);"          "F23 · la hoja"
mut "F · sin fila del Centro       " ui/js/marco.js     "{ id: 'centro'"                          "F19 · el Centro"
mut "G · sin la fila de mv         " ui/js/marco.js     "{ id: 'mv',"                             "MV"

restaura
if md5sum -c --quiet "$PIT/md5-inicio"; then
  echo "restaurado: los dos archivos vuelven a ser los de antes (md5)"
else
  echo "CUIDADO: la restauración no coincidió -- revisar ui/js"
  md5sum "${ARCHIVOS[@]}"
  exit 1
fi
