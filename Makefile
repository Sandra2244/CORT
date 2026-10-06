.PHONY: setup dev build lint test help install-py install-node run-core run-voice run-bridge run-web clean

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

help:
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)CORT - Cognitive Operating Reactive Technology$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)Available targets:$(NC)"
	@echo "  make setup           - Install all dependencies (Python + Node)"
	@echo "  make dev             - Start all services locally"
	@echo "  make install-py      - Install Python dependencies only"
	@echo "  make install-node    - Install Node dependencies only"
	@echo "  make run-core        - Start CORT Core service"
	@echo "  make run-voice       - Start CORT Voice service"
	@echo "  make run-bridge      - Start CORT Bridge (WebSocket server)"
	@echo "  make run-web         - Start Web UI"
	@echo "  make build           - Build for production"
	@echo "  make clean           - Remove generated files"
	@echo ""

setup: install-py install-node
	@echo "$(GREEN)✅ Setup complete!$(NC)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Copy .env.example to .env"
	@echo "  2. Install Ollama from https://ollama.ai"
	@echo "  3. Run: make dev"

install-py:
	@echo "$(YELLOW)📦 Installing Python dependencies...$(NC)"
	@if [ ! -d ".venv" ]; then \
		python3 -m venv .venv; \
		echo "$(GREEN)✓ Virtual environment created$(NC)"; \
	fi
	@. .venv/bin/activate && pip install -U pip setuptools wheel
	@cd services/core && ../../.venv/bin/pip install -e . && cd ../..
	@cd services/voice && ../../.venv/bin/pip install -e . && cd ../..
	@echo "$(GREEN)✓ Python dependencies installed$(NC)"

install-node:
	@echo "$(YELLOW)📦 Installing Node dependencies...$(NC)"
	@cd apps/web && npm install && cd ../..
	@cd services/bridge && npm install && cd ../..
	@echo "$(GREEN)✓ Node dependencies installed$(NC)"

dev:
	@echo "$(BLUE)🚀 Starting CORT Development Environment$(NC)"
	@bash scripts/dev.sh

run-core:
	@echo "$(YELLOW)Starting CORT Core on port 8000...$(NC)"
	@. .venv/bin/activate && python services/core/src/main.py

run-voice:
	@echo "$(YELLOW)Starting CORT Voice on port 8001...$(NC)"
	@. .venv/bin/activate && python services/voice/src/main.py

run-bridge:
	@echo "$(YELLOW)Starting CORT Bridge on port 8787...$(NC)"
	@cd services/bridge && npm run dev

run-web:
	@echo "$(YELLOW)Starting Web UI on port 5173...$(NC)"
	@cd apps/web && npm run dev

build:
	@echo "$(YELLOW)🔨 Building project...$(NC)"
	@cd apps/web && npm run build

clean:
	@echo "$(YELLOW)🧹 Cleaning up...$(NC)"
	@rm -rf .venv
	@rm -rf node_modules
	@rm -rf apps/web/node_modules
	@rm -rf services/bridge/node_modules
	@rm -rf dist/ build/
	@echo "$(GREEN)✓ Clean complete$(NC)"
