#!/usr/bin/env bash
# Saca el anillo que CORT tiene EN EL TELÉFONO y lo pone como logo de los
# instaladores de escritorio (`desktop/build/icon.png` e `icon.ico`), para que el
# ejecutor del PC, el acceso directo y la icono de la app sean el MISMO dibujo
# que la dueña ve en su launcher de Android.
#
# ¿De dónde sale el dibujo? Del APK original del teléfono, que vive en este repo
# (`apps/apk/base/CORT-IA-1.1.0.apk`). Dentro lleva un **icono adaptativo** de
# Android: `ic_launcher_foreground.png` a 432 px sobre un fondo. Android recorta
# ese lienzo a 72/108 partes, así que para recomponer lo que el teléfono enseña
# hay que escalar el frente a 432·72/108 = 288 px y centrarlo sobre el color de
# fondo: el resultado es un icono con **detalle real de 288 px**, en vez de
# estirar el PNG de 192 que viene recortado.
#
# Se ejecuta UNA VEZ, en una máquina con ImageMagick, y los dos archivos que
# produce se commitean: el pipeline de GitHub Actions no necesita `convert` ni
# este script para construir los instaladores.
#
# Uso:  bash scripts/icono-del-telefonito.sh
set -euo pipefail
cd "$(dirname "$0")/.."

BASE="apps/apk/base"
APK="$(ls "$BASE"/*.apk 2>/dev/null | head -1)"
[ -n "$APK" ] || { echo "no hay APK de referencia en $BASE"; exit 1; }
command -v convert >/dev/null || { echo "hace falta ImageMagick (`convert`)"; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

unzip -p "$APK" res/mipmap-xxxhdpi-v4/ic_launcher_foreground.png > "$TMP/fg.png"
# El color de fondo es el espacio de CORT: `#02040a`, el mismo literal que
# `scripts/marca.py` llama `BG`. Se comprueba a mano (la esquina del icono que
# trae el APK) y se escribe aquí en claro: el `convert` de este portátil no tiene
# forma de imprimir un píxel (`%[pixel:…]` responde vacío), y vale más un literal
# con su nota que un sondeo que falla en silencio.
FONDO=02040A
echo "fondo del icono del teléfono: #$FONDO"

convert "$TMP/fg.png" -filter Lanczos -resize 288x288 -gravity center \
        -crop 192x192+0+0 +repage "$TMP/nucleo.png"
convert -size 192x192 "xc:#$FONDO" "$TMP/fondo.png"
composite -gravity center "$TMP/nucleo.png" "$TMP/fondo.png" "$TMP/base.png"

# 512 para el `.png` (Linux/Windows lo piden grande; viene de 288 px reales, así
# que el estirado es suave). El `.ico` no pasa de 256.
convert "$TMP/base.png" -filter Lanczos -resize 512x512 desktop/build/icon.png
for s in 16 24 32 48 64 128 256; do
    convert "$TMP/base.png" -filter Lanczos -resize ${s}x${s} "$TMP/ico-$s.png"
done
# ImageMagick no escribe ICO en este portátil: los mete dentro `empaqueta-ico.py`.
python3 scripts/empaqueta-ico.py desktop/build/icon.ico \
    "$TMP/ico-16.png" "$TMP/ico-24.png" "$TMP/ico-32.png" "$TMP/ico-48.png" \
    "$TMP/ico-64.png" "$TMP/ico-128.png" "$TMP/ico-256.png"

echo "logo de los instaladores: anillo del teléfono"
identify desktop/build/icon.png desktop/build/icon.ico
ls -l desktop/build/icon.png desktop/build/icon.ico
