#!/usr/bin/env bash
# scripts/actualiza.sh — autorreparación del CORT de escritorio en Linux.
#
# Para qué sirve, en una frase: baja el AppImage más nuevo de la Release,
# respalda la carpeta actual y la sustituye por la nueva, SIN permisos de
# administrador y SIN tocar nunca `~/.cort/` — que ahí viven las notas, la
# memoria y la llave de Groq, y nada de eso se borre ni con una actualización.
#
# Uso:
#   bash scripts/actualiza.sh                    # la última Release pública
#   CORT_URL=https://…/CORT-x.y.AppImage bash scripts/actualiza.sh
#
# Dónde toca (y fuera de ahí, NO):
#   ~/Aplicaciones/CORT                    la app extraída (como instalar-linux.sh)
#   ~/Aplicaciones/CORT.anterior-<fecha>   el respaldo, por si hay que volver
#   ~/.cort/actualiza/                     la descarga temporal del AppImage
#
# Es re-ejecutable: cada corrida deja SU propio respaldo con fecha y hora, y
# si algo sale torcido el respaldo viejo sigue intacto donde lo dejaste.
# La URL sale de la API pública de GitHub con `curl` + `python3` (sin `jq`:
# el portátil de la dueña no lo tiene y no hay por qué pedirlo).
set -euo pipefail

APP="$HOME/Aplicaciones/CORT"
BASE="$HOME/Aplicaciones"
ZONA="$HOME/.cort/actualiza"          # el único rincón de ~/.cort que este script usa

# ── 1 · ¿aquí se puede? solo Linux; Windows se repara con el .exe de la Release
case "$(uname -s)" in
  Linux) ;;
  Darwin) echo "  ! en macOS este script no aplica: baja el .dmg de la Release." ; exit 1 ;;
  *) echo "  ! Windows no es terreno de este script: usa el .exe de la Release" \
       "  (github.com/Sandra2244/CORT/releases)." ; exit 1 ;;
esac

mkdir -p "$BASE" "$ZONA"

# ── 2 · la URL del AppImage más nuevo (API pública, sin clave)
URL="${CORT_URL:-}"
if [ -z "$URL" ]; then
  echo "→ buscando el AppImage de la última Release…"
  URL=$(curl -s -m 20 https://api.github.com/repos/Sandra2244/CORT/releases/latest \
        | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
a = [x["browser_download_url"] for x in d.get("assets", [])
     if x.get("name", "").lower().endswith(".appimage")]
print(a[0] if a else "")')
fi
[ -n "$URL" ] || { echo "  ! no encontré ningún AppImage en la Release" \
  " (¿estás sin internet o la Release no lo incluye?)."; exit 1; }
echo "  · $URL"

# ── 3 · descargar EN ~/.cort/actualiza (pesa ~100 MB: aquí no congelamos nada,
#        curl escribe en disco y la RAM sólo ve trocitos)
ARCHIVO="$ZONA/$(basename "$URL")"
echo "→ descargando en $ARCHIVO…"
curl -L --fail -m 900 -o "$ARCHIVO.tmp" "$URL"
mv "$ARCHIVO.tmp" "$ARCHIVO"          # descarga completa o nada: nunca a medias
chmod +x "$ARCHIVO"

# ── 4 · extraer el AppImage SIN montarlo (fuse no hace falta, y en 1,8 GiB
#        de RAM es peor: se desmonta solo en un nido de la zona de descarga)
NIDO="$ZONA/nido"
rm -rf "$NIDO"                        # sólo borramos DENTRO de ~/.cort/actualiza
mkdir -p "$NIDO"
( cd "$NIDO" && "$ARCHIVO" --appimage-extract >/dev/null )
[ -d "$NIDO/squashfs-root" ] || { echo "  ! el AppImage no se extrajo como esperaba."; exit 1; }

# ── 5 · respaldar la carpeta actual ANTES de sustituirla (volver atrás siempre
#        posible; no se borra ningún respaldo viejo)
RESPALDO=""
if [ -d "$APP" ]; then
  RESPALDO="$BASE/CORT.anterior-$(date +%Y%m%d-%H%M)"
  while [ -e "$RESPALDO" ]; do RESPALDO="$RESPALDO-b"; done
  echo "→ respaldando la versión actual en $RESPALDO…"
  mv "$APP" "$RESPALDO"
fi

# ── 6 · copiar la nueva por encima, en ~/Aplicaciones/CORT, sin sudo
echo "→ instalando la nueva en $APP…"
mkdir -p "$APP"
cp -a "$NIDO/squashfs-root/." "$APP/"
chmod +x "$APP" 2>/dev/null || true
for bin in CORT cort-desktop AppRun; do
  [ -f "$APP/$bin" ] && chmod +x "$APP/$bin" || true
done
rm -rf "$NIDO"                        # de nuevo: sólo dentro de ~/.cort/actualiza

echo
echo "listo: CORT actualizado en $APP (los datos de ~/.cort siguen igual)."
if [ -n "$RESPALDO" ]; then
  echo "para volver a la versión anterior:"
  echo "  mv ~/Aplicaciones/CORT ~/Aplicaciones/CORT.roto && mv '$RESPALDO' ~/Aplicaciones/CORT"
fi
