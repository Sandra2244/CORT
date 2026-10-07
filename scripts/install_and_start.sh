#!/usr/bin/env bash
set -euo pipefail

# scripts/install_and_start.sh
# Installer + starter for CORT (scaffold branch)
# - Installs system packages (git, python3, nodejs) on Debian/Ubuntu
# - Prepares backend virtualenv and minimal Python deps
# - Installs frontend npm deps
# - Creates a Desktop launcher to start CORT with one click
# NOTE: run this once from the project root (~/Escritorio/CORT) or run with full path.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "CORT installer — will prepare environment and create a desktop launcher"

if [ "$EUID" -ne 0 ]; then
  SUDO='sudo'
else
  SUDO=''
fi

read -p "This script may install system packages (apt). Continue? [Y/n] " REPLY
REPLY=${REPLY:-Y}
if [[ ! "$REPLY" =~ ^[Yy]$ ]]; then
  echo "Aborted by user"
  exit 1
fi

# Detect distro (only Debian/Ubuntu tested)
if command -v apt >/dev/null 2>&1; then
  PKG_MANAGER='apt'
else
  echo "No supported package manager found (apt expected). Please install prerequisites manually: git, python3, python3-venv, python3-pip, nodejs, npm" >&2
  exit 1
fi

echo "Updating package lists... (may ask for your password)"
$SUDO apt update

# Install minimal system deps
echo "Installing system packages: git curl build-essential python3 python3-venv python3-pip ffmpeg"
$SUDO apt install -y git curl build-essential python3 python3-venv python3-pip ffmpeg || true

# Install Node 18 if node not present or too old
NEED_NODE=0
if command -v node >/dev/null 2>&1; then
  NODE_V=$(node -v | sed 's/v//')
  echo "Detected node version: $NODE_V"
else
  NEED_NODE=1
fi

if [ $NEED_NODE -eq 1 ]; then
  echo "Installing Node.js 18 (NodeSource)..."
  curl -fsSL https://deb.nodesource.com/setup_18.x | $SUDO -E bash -
  $SUDO apt-get install -y nodejs
fi

# Optional: global tools
echo "Installing optional global npm tools (wscat)..."
# Install wscat globally (no failure if it fails)
if command -v npm >/dev/null 2>&1; then
  npm i -g wscat >/dev/null 2>&1 || true
fi

# Ensure repo is present
if [ ! -d "$ROOT/.git" ]; then
  echo "This does not look like the CORT repository root: $ROOT" >&2
  echo "Please clone the repo first and run this script from the repo root." >&2
  exit 1
fi

# Create backend venv and install minimal Python deps
if [ ! -d backend/.venv ]; then
  echo "Creating Python virtualenv for backend..."
  python3 -m venv backend/.venv
fi

echo "Activating backend venv and installing Python packages (minimal)..."
# shellcheck disable=SC1091
source backend/.venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "uvicorn[standard]" fastapi httpx[http2] python-dotenv python-multipart websockets >/dev/null

# Install frontend deps
echo "Installing frontend npm dependencies (this may take a minute)..."
cd frontend
npm install --silent || npm install

cd "$ROOT"

# Make sure start/stop scripts are executable
chmod +x scripts/start_all.sh || true
chmod +x scripts/stop_all.sh || true
chmod +x scripts/install_and_start.sh || true

# Create Desktop launcher (XFCE / Linux)
DESKTOP_FILE="$HOME/Desktop/CORT-Start.desktop"
LAUNCH_CMD="bash -lc 'cd \"$ROOT\" && ./scripts/start_all.sh; exec bash'"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=CORT - Start Dev
Comment=Start CORT (backend + frontend)
Exec=$LAUNCH_CMD
Icon=$ROOT/frontend/public/icon.png
Terminal=true
Categories=Development;Utility;
EOF
chmod +x "$DESKTOP_FILE"

# Create stop desktop launcher
DESKTOP_STOP="$HOME/Desktop/CORT-Stop.desktop"
STOP_CMD="bash -lc 'cd \"$ROOT\" && ./scripts/stop_all.sh; exec bash'"
cat > "$DESKTOP_STOP" <<EOF
[Desktop Entry]
Type=Application
Name=CORT - Stop Dev
Comment=Stop CORT (backend + frontend)
Exec=$STOP_CMD
Icon=$ROOT/frontend/public/icon.png
Terminal=true
Categories=Development;Utility;
EOF
chmod +x "$DESKTOP_STOP"

# Start services once
echo "Starting CORT services now..."
./scripts/start_all.sh

echo
echo "Installer finished. Two desktop shortcuts were created on your Desktop:" 
echo " - $DESKTOP_FILE  (start)"
echo " - $DESKTOP_STOP (stop)"

echo "Open http://localhost:5173 in your browser once frontend is ready."

echo "If you want the full ML stack (Whisper, Coqui, FAISS), run:"
echo "  ./scripts/start_all.sh --full-install" || true

exit 0
