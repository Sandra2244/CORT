setup:
	python -m venv .venv && . .venv/bin/activate && pip install -r services/core/requirements.txt
dev:
	. .venv/bin/activate && cd services/core && python -m cort_core.server
web:
	cd apps/web && python -m http.server 5173
test:
	cd services/core && python -m unittest discover -s tests -v
