#!/usr/bin/env bash
# Genera el lanzador de doble clic para Linux con la ruta real del repo.
#
# El .desktop lleva rutas absolutas: es la única forma que tienen XFCE y GNOME de
# arrancar algo. Por eso NO se guarda en el repositorio —el repo es público y ahí
# aparecería la carpeta personal de quien lo usa— y este script lo escribe en la
# raíz del proyecto con la ruta de esta máquina, además de instalarlo en
# ~/.local/share/applications, que es donde lo ve el lanzador de aplicaciones.
#
#   ./scripts/install-desktop.sh            # escribe CORT.desktop y lo instala
#   ./scripts/install-desktop.sh --desktop  # y además un acceso en el escritorio
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || { echo "No está el venv en $PY — ejecuta 'make setup' primero."; exit 1; }

OUT="$ROOT/CORT.desktop"
cat > "$OUT" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=CORT
GenericName=Asistente holográfico
Comment=Arranca el core, abre la interfaz y muestra la terminal de CORT
Exec=$PY $ROOT/scripts/cort.py
Path=$ROOT
Icon=$ROOT/docs/assets/prototipo-v0.1.0.png
Terminal=true
Categories=Utility;
Keywords=cort;asistente;ollama;
StartupNotify=true
EOF

install -Dm 755 "$OUT" "$HOME/.local/share/applications/CORT.desktop"
echo "escrito $OUT e instalado en el menú de aplicaciones: CORT"

if [ "${1:-}" = "--desktop" ]; then
  DESKTOP="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Escritorio")"
  install -Dm 755 "$HOME/.local/share/applications/CORT.desktop" "$DESKTOP/CORT.desktop"
  # Sin esto, GNOME y XFCE muestran el icono pero se niegan a ejecutarlo.
  gio set "$DESKTOP/CORT.desktop" metadata::trusted true 2>/dev/null || true
  echo "acceso puesto en $DESKTOP (doble clic)"
fi
