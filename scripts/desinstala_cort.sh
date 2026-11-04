#!/usr/bin/env bash
# scripts/desinstala_cort.sh — quita lo que puso instala_cort.sh y nada más.
#
# NO borra ~/.local/share/cort: ahí están tu memoria, tus notas y tu lista.
# Ese borrado se hace a mano, leyendo antes lo que hay (mira el README, la tabla
# «Qué guarda CORT de ti»). El entorno .venv tampoco se toca: pesa poco y si
# quieres fuera, rm -rf .venv.
set -uo pipefail

if systemctl --user list-unit-files cort.service >/dev/null 2>&1; then
  systemctl --user stop cort 2>/dev/null || true
  systemctl --user disable cort 2>/dev/null || true
  rm -f "$HOME/.config/systemd/user/cort.service"
  systemctl --user daemon-reload
  echo "servicio de usuario quitado"
fi

rm -f "$HOME/.local/share/applications/cort.desktop"
rm -f "$HOME/.config/autostart/cort.desktop"
for d in Escritorio Desktop; do rm -f "$HOME/$d/CORT.desktop" 2>/dev/null || true; done

echo "lanzador y arranque automático quitados"
echo "tus datos siguen en ${CORT_DATOS:-$HOME/.local/share/cort} (aquí se borran a mano, con calma)"
