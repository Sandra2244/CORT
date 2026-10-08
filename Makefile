# Ruta absoluta: cada receta de make corre en su propio shell y cambia de directorio,
# así que una ruta relativa (.venv/bin/python) dejaría de funcionar tras un `cd`.
VENV := $(CURDIR)/.venv
PY   := $(VENV)/bin/python
CORE := services/core
WEB  := apps/web

setup:
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r $(CORE)/requirements.txt

dev:
	cd $(CORE) && $(PY) -m cort_core.server

# El mismo arranque que el doble clic, pero en la terminal que ya tienes abierta:
# core + interfaz + navegador, con las barras de estado y Ctrl+C que cierra todo.
launch:
	$(PY) scripts/cort.py

# Una prueba sin tocar la memoria real: la base se va a /tmp y se puede llenar
# de "hola" sin consecuencias.
demo:
	$(PY) scripts/cort.py --demo

web-deps:
	cd $(WEB) && npm install

# `python -m http.server` ya no sirve aquí: apps/web es una app Vite, y
# servir los .tsx por HTTP daría una página en blanco sin ningún error.
web:
	cd $(WEB) && npm run dev

web-build:
	cd $(WEB) && npm run typecheck && npm run build

test:
	cd $(CORE) && $(PY) -m unittest discover -s tests -v

.PHONY: setup dev web web-deps web-build test

