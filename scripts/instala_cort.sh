#!/usr/bin/env bash
# scripts/instala_cort.sh — instalar CORT en Debian / Ubuntu / MX Linux (XFCE)
#
# Qué hace, en orden y dicho con palabras:
#   1. comprueba python3 y el módulo venv
#   2. crea .venv en el repo e instala SOLO lo que está en requirements-cort.txt
#   3. escribe el servicio de usuario systemd con la RUTA REAL del repo, si el
#      equipo tiene instancia de usuario; si no, lo dice y se usa XFCE
#   4. escribe el lanzador de menú y el arranque automático de XFCE
#   5. imprime la dirección del puente y lo que el equipo puede y no puede hacer
#
# Qué NO hace: no ejecuta nada con sudo sin preguntarte con los paquetes exactos
# delante, no baja instaladores de terceros para tubería a shell, no toca
# ~/.local/share/cort si ya tiene datos, y no abre el puente a la red salvo que
# se lo pidas con --red.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RED=0; AUTOSTART=1; PREGUNTA=1
for a in "$@"; do
  case "$a" in
    --red) RED=1 ;;
    --sin-autostart) AUTOSTART=0 ;;
    --sin-pregunta) PREGUNTA=0 ;;
    -h|--help) sed -n '1,32p' "$0"; exit 0 ;;
    *) echo "opción desconocida: $a (--red, --sin-autostart, --sin-pregunta)"; exit 2 ;;
  esac
done

echo "CORT · instalación en $ROOT"
echo

if [ ! -f cort-bridge/cort_server.py ]; then
  echo "Esto no parece el repo de CORT (falta cort-bridge/cort_server.py). Abre el script desde la raíz del repo." >&2
  exit 1
fi

command -v python3 >/dev/null 2>&1 || { echo "falta python3"; exit 1; }
if ! python3 -c "import venv" >/dev/null 2>&1; then
  echo "El módulo venv no está. En Debian/Ubuntu/MX entra con:"
  echo "  sudo apt install python3-venv python3-pip"
  echo "Este script no ejecuta sudo por ti."
  [ "$PREGUNTA" = 1 ] || exit 1
  read -r -p "¿Ejecutarlo ahora con sudo? [y/N] " r
  case "$r" in [yY]*) sudo apt install -y python3-venv python3-pip ;; *) echo "sin venv no se puede crear el entorno; salgo"; exit 1 ;; esac
fi

if [ ! -d .venv ]; then
  echo "creando el entorno .venv…"
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --quiet --upgrade pip
echo "instalando dependencias de requirements-cort.txt…"
.venv/bin/python -m pip install --quiet -r requirements-cort.txt
.venv/bin/python - <<'PY'
import sys
from importlib.metadata import version
import aiohttp, vosk, numpy  # noqa: F401  (se importan sólo para confirmar que están)
print("  python %s · aiohttp %s · vosk %s · numpy %s" % (
    sys.version.split()[0], version("aiohttp"), version("vosk"), version("numpy")))
PY

PYTHON="$ROOT/.venv/bin/python"
if ! "$PYTHON" -c "import aiohttp" >/dev/null 2>&1; then
  echo "el entorno no quedó bien; revisa el mensaje de pip de arriba" >&2
  exit 1
fi

# --- modelo de Vosk: se avisa, no se baja a ciegas -------------------------------
MODELO="${CORT_DATOS:-$HOME/.local/share/cort}/modelos/vosk-es"
if [ -d "$MODELO" ]; then
  echo "modelo de español para el oído: presente ($(du -sh "$MODELO" 2>/dev/null | cut -f1))"
else
  echo "ojo: no está el modelo de Vosk en $MODELO."
  echo "  CORT entenderá texto pero no voz. La descarga y el desempaquetado están"
  echo "  explicados en el README (se baja el zip, se mira, y luego se descomprime)."
fi

# --- servicio de usuario ----------------------------------------------------------
# Medido en esta máquina (MX Linux 13 + XFCE): no hay instancia de usuario de
# systemd — /run/user/1000/bus no existe y systemctl --user contesta «Failed to
# connect to user scope bus». Donde sí la haya (Debian y Ubuntu de hoy, Fedora),
# el archivo se escribe y se activa; donde no, se dice y el arranque automático
# se hace por XFCE, que es lo que de verdad funciona.
if command -v systemctl >/dev/null 2>&1; then
  if [ -S "/run/user/$(id -u)/bus" ] && systemctl --user show-environment >/dev/null 2>&1; then
    mkdir -p "$HOME/.config/systemd/user"
    {
      echo "[Unit]"
      echo "Description=CORT — puente local (interfaz 8766, websocket 8765)"
      echo "After=default.target"
      echo
      echo "[Service]"
      echo "WorkingDirectory=$ROOT"
      echo "ExecStart=$PYTHON -u $ROOT/cort-bridge/cort_server.py"
      echo "Restart=on-failure"
      echo "RestartSec=4"
      echo "Nice=10"
      [ "$RED" = 1 ] && echo "Environment=CORT_BIND=0.0.0.0"
      echo
      echo "[Install]"
      echo "WantedBy=default.target"
    } > "$HOME/.config/systemd/user/cort.service"
    systemctl --user daemon-reload
    systemctl --user enable cort >/dev/null 2>&1 || true
    echo "servicio de usuario escrito y activado en ~/.config/systemd/user/cort.service"
    echo "  arrancar: systemctl --user start cort    mirar: journalctl --user -u cort -f"
    AUTOSTART=0   # con systemd, el aut arranque de XFCE sería un duplicado
  else
    echo "aquí no hay instancia de usuario de systemd (medido: /run/user/$(id -u)/bus no existe)."
    echo "  el arranque automático de XFCE, más abajo, es lo que sí funciona aquí."
    echo "  si prefieres systemd como servicio del sistema, hay que escribir la unidad"
    echo "  a mano con sudo y la usuaria dentro del unit: se documenta en el README."
  fi
else
  echo "no hay systemctl: queda el lanzador de menú y el aut arranque de XFCE."
fi

# --- lanzador de menú (XFCE y demás) ---------------------------------------------
mkdir -p "$HOME/.local/share/applications"
ARRANQUE="$ROOT/scripts/arranca_cort.sh"
[ "$RED" = 1 ] && ARRANQUE="$ARRANQUE --red"
cat > "$HOME/.local/share/applications/cort.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=CORT
Comment=Asistente local, en tu red
Exec=$ARRANQUE
Terminal=false
Categories=Utility;System;
Icon=$ROOT/cort-web/iconos/cort.svg
EOF
chmod +x "$HOME/.local/share/applications/cort.desktop"
if [ -d "$HOME/Escritorio" ]; then
  cp "$HOME/.local/share/applications/cort.desktop" "$HOME/Escritorio/CORT.desktop" 2>/dev/null || true
  chmod +x "$HOME/Escritorio/CORT.desktop" 2>/dev/null || true
fi
echo "lanzador escrito en ~/.local/share/applications/cort.desktop"

if [ "$AUTOSTART" = 1 ]; then
  mkdir -p "$HOME/.config/autostart"
  {
    cat "$HOME/.local/share/applications/cort.desktop"
    echo "X-GNOME-Autostart-enabled=true"
  } > "$HOME/.config/autostart/cort.desktop"
  echo "arranque automático activado en XFCE (~/.config/autostart/cort.desktop)"
fi

# --- lo que el equipo puede hacer, medido ----------------------------------------
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
LIBRE=$(awk '/MemAvailable/{printf "%.0f", $2/1024}' /proc/meminfo)
echo
echo "ya está. El puente arranca en http://127.0.0.1:8766/index.html"
if [ "$RED" = 1 ]; then
  echo "abierto a la red local:  http://${IP:-IP_DEL_EQUIPO}:8766/index.html"
  echo "en el teléfono, esa misma dirección dentro de la aplicación."
else
  echo "para usarlo desde el teléfono:  CORT_BIND=0.0.0.0 .venv/bin/python -u cort-bridge/cort_server.py"
  echo "(o reinstala con --red). Sin HTTPS el teléfono no instala la PWA: usa el APK."
fi
echo "RAM disponible ahora: ${LIBRE} MB · núcleos $(nproc)"
echo
echo "prueba sin tocar nada:  $PYTHON cort-bridge/cort_voz.py estado"
