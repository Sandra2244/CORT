# Ruta absoluta: cada receta de make corre en su propio shell y cambia de directorio,
# así que una ruta relativa (.venv/bin/python) dejaría de funcionar tras un `cd`.
VENV := $(CURDIR)/.venv
PY   := $(VENV)/bin/python
CORE := services/core

setup:
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r $(CORE)/requirements.txt

dev:
	cd $(CORE) && $(PY) -m cort_core.server

web:
	$(PY) -m http.server 5173 --directory apps/web

test:
	cd $(CORE) && $(PY) -m unittest discover -s tests -v

.PHONY: setup dev web test
