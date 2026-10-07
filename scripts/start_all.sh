#!/usr/bin/env bash
set -euo pipefail

# scripts/start_all.sh
# Convenience script to prepare and start backend + frontend for development.
# Makes a venv in backend/.venv, installs minimal deps, starts uvicorn and vite in background
# Logs are written to logs/backend.log and logs/frontend.log
# PIDs are stored in .run/backend.pid and .run/frontend.pid

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs .run

echo "Starting CORT dev environment from: $ROOT"

# --- Backend venv and deps ---
if [ ! -d backend/.venv ]; then
  echo "Creating Python venv for backend..."
  python3 -m venv backend/.venv
fi

# Activate venv
# shellcheck disable=SC1091
source backend/.venv/bin/activate

echo "Upgrading pip and installing minimal backend deps (may take a moment)..."
python -m pip install --upgrade pip >/dev/null
# Install minimal required deps; skip optional heavy ML packages
python -m pip install "uvicorn[standard]" fastapi httpx[http2] python-dotenv python-multipart websockets >/dev/null || true

# Start backend (use --app-dir so you can run from repo root)
if [ -f .run/backend.pid ]; then
  OLD_PID=$(cat .run/backend.pid)
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Backend appears already running (pid $OLD_PID)." 
  else
    echo "Stale backend pid file found, removing."
    rm -f .run/backend.pid
  fi
fi

if [ ! -f .run/backend.pid ]; then
  echo "Starting backend (uvicorn) -> logs/backend.log"
  nohup backend/.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend > logs/backend.log 2>&1 &
  echo $! > .run/backend.pid
  sleep 1
fi

# --- Frontend (vite) ---
cd frontend
if [ ! -d node_modules ]; then
  echo "Installing frontend npm deps (this may take a minute)..."
  npm install --silent
fi

if [ -f ../.run/frontend.pid ]; then
  OLD_PID=$(cat ../.run/frontend.pid)
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Frontend appears already running (pid $OLD_PID)."
  else
    echo "Stale frontend pid file found, removing."
    rm -f ../.run/frontend.pid
  fi
fi

if [ ! -f ../.run/frontend.pid ]; then
  echo "Starting frontend (vite) -> logs/frontend.log"
  nohup npm run dev -- --host 0.0.0.0 > ../logs/frontend.log 2>&1 &
  echo $! > ../.run/frontend.pid
fi

cd "$ROOT"

echo
echo "CORT dev started."
echo "Backend: http://localhost:8000 (health: /health)"
echo "Frontend: http://localhost:5173"
echo "Logs: $ROOT/logs/backend.log and $ROOT/logs/frontend.log"
echo "To stop: ./scripts/stop_all.sh"
