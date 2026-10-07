dev:
	@echo "Starting backend and frontend in development mode"
	@echo "1) Start Ollama locally (see README)"
	@echo "2) In a terminal run: make backend"
	@echo "3) In another terminal run: make frontend"

backend:
	cd backend && python -m venv .venv || true && . .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload --host ${BACKEND_HOST:-0.0.0.0} --port ${BACKEND_PORT:-8000}

frontend:
	cd frontend && npm install && npm run dev

start-ollama:
	@echo "Ollama must be installed separately. See README for install and pull model instructions."

clean:
	rm -rf backend/.venv
