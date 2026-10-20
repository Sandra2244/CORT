#!/usr/bin/env bash
# Instala el CORT de escritorio en Linux SIN permisos de administrador.
#
# El instalador `.AppImage` de Electron necesita fuse2 para montarse, y en
# muchos equipos (y en cualquier PC con poca RAM) no hace falta: se extrae,
# se copia el código dentro y queda un lanzador normal en el escritorio.
#
# Uso:
#   bash scripts/instalar-linux.sh                       # descarga la última release
#   bash scripts/instalar-linux.sh Cort-0.2.0.AppImage   # usa el archivo local
#
# Qué deja:
#   ~/Aplicaciones/CORT/          la app extraída (ventana + ui + backend)
#   ~/Aplicaciones/CORT/arrancar-cort.sh   lanza el backend y luego la ventana
#   ~/Escritorio/CORT.desktop     icono doble clic
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP="$HOME/Aplicaciones/CORT"
RAM=$(awk '/MemTotal/ {printf "%d", $2/1048576}' /proc/meminfo 2>/dev/null || echo 0)
SRC="${1:-}"

if [ -z "$SRC" ]; then
  echo "→ buscando la última versión en GitHub…"
  URL=$(curl -s https://api.github.com/repos/Sandra2244/CORT/releases/latest \
        | grep -o '"browser_download_url": *"[^"]*[Aa]pp[Ii]mage[^"]*"' | head -1 \
        | cut -d'"' -f4)
  [ -n "$URL" ] || { echo "  ! no la encontré: pasa el AppImage como argumento."; exit 1; }
  SRC="/tmp/$(basename "$URL")"
  echo "→ descargando $URL"
  curl -L -o "$SRC" "$URL"
fi
[ -f "$SRC" ] || { echo "  ! no existe $SRC"; exit 1; }

echo "→ extrayendo $SRC en $APP"
rm -rf "$APP"; mkdir -p "$APP"
chmod +x "$SRC"
"$SRC" --appimage-extract >/dev/null 2>&1 || {
  # sin FUSE: extraer con 7z como plan B
  command -v 7z >/dev/null || { echo "  ! necesitas 7z o FUSE: sudo apt install p7zip-full"; exit 1; }
  7z x -y -o"$APP" "$SRC" >/dev/null
}
if [ -d "$APP/squashfs-root" ]; then
  mv "$APP"/squashfs-root/* "$APP"/ 2>/dev/null || true
  rmdir "$APP/squashfs-root" 2>/dev/null || true
fi

# El instalador trae la UI y el backend dentro de resources/: se refrescan con
# el código de este repositorio para que la app instalada sea idéntica a la rama.
if [ -d "$APP/resources" ]; then
  [ -d "$APP/resources/ui" ] && cp -a "$APP/resources" "$APP/resources.respaldo"
  rsync -a --delete "$REPO/ui/" "$APP/resources/ui/"
  rsync -a "$REPO/backend/app/"*.py "$APP/resources/backend/app/" 2>/dev/null || true
fi

BIN=$(find "$APP" -maxdepth 1 -type f \( -name 'cort-desktop' -o -name 'CORT' \) | head -1)
[ -n "$BIN" ] || BIN="$APP/CORT"
chmod +x "$BIN" 2>/dev/null || true

cat > "$APP/arrancar-cort.sh" <<LANZADOR
#!/usr/bin/env bash
# Deja el núcleo (backend) en marcha y abre la ventana.
# La app de Linux no trae Python dentro: usa el entorno del repositorio.
set -e
APP="$APP"; REPO="$REPO"; PORT="\${CORT_PORT:-8000}"
vivo() { curl -s -m 1 -o /dev/null "http://127.0.0.1:\$PORT/api/port" 2>/dev/null; }
if ! vivo; then
  if [ -x "\$REPO/.venv/bin/uvicorn" ]; then
    echo "→ levantando el núcleo en el puerto \$PORT…"
    ( cd "\$REPO" && CORT_SERVE_UI=1 setsid nohup .venv/bin/uvicorn \\
        --app-dir backend app.main:app --port "\$PORT" > "\$HOME/.cort-backend.log" 2>&1 & )
    for _ in \$(seq 12); do sleep 1; vivo && break; done
  else
    echo "  ! no está \$REPO/.venv: prepara el entorno con  bash \$REPO/scripts/run.sh"
  fi
fi
exec "$BIN" --no-sandbox "\$@"
LANZADOR
chmod +x "$APP/arrancar-cort.sh"

mkdir -p "$HOME/Escritorio"
cat > "$HOME/Escritorio/CORT.desktop" <<ESCRITORIO
[Desktop Entry]
Type=Application
Name=CORT — holograma
Comment=Asistente holográfico C.O.R.T.
Exec=$APP/arrancar-cort.sh
Path=$APP
Icon=$APP/cort-desktop.png
Terminal=false
Categories=Utility;
ESCRITORIO
chmod +x "$HOME/Escritorio/CORT.desktop" 2>/dev/null || true

echo
echo "Listo. Abre CORT con el icono del escritorio o con:"
echo "  bash $APP/arrancar-cort.sh"
[ "$RAM" -gt 0 ] && [ "$RAM" -lt 3 ] && echo \
  "  (tu equipo tiene ${RAM} GB de RAM: usa el cerebro online gratuito; Ollama irá lento)"
