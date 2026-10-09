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
	@cp -n .env.example .env && echo "creado .env (edítalo: ahí va tu cadena de modelos)" || echo ".env ya existe, no lo toco"

dev:
	cd $(CORE) && $(PY) -m cort_core.server

# El mismo arranque que el doble clic, pero en la terminal que ya tienes abierta:
# core + interfaz + navegador, con las barras de estado y Ctrl+C que cierra todo.
launch:
	$(PY) scripts/cort.py

# Instalación completa de primera vez: venv + dependencias del core + .env +
# interfaz construida. Después de esto `make launch` sirve `dist` y no gasta los
# ~120 MB de Vite en desarrollo.
install: setup web-deps web-build
	@echo ""
	@echo "CORT instalado. Para encenderlo:  make launch   (o doble clic en CORT.desktop)"

# Qué tiene esta máquina y qué le falta. No instala nada: mira.
doctor:
	@for cmd in python3 node npm; do \
	  printf "%-9s " "$$cmd"; \
	  command -v $$cmd >/dev/null 2>&1 && $$cmd --version 2>&1 | head -1 || echo "FALTA"; \
	done
	@printf "%-9s " "venv"; test -x $(PY) && echo "ok ($(PY))" || echo "FALTA — make setup"
	@printf "%-9s " ".env"; test -f .env && echo "ok" || echo "FALTA — make setup lo crea desde .env.example"
	@printf "%-9s " "node_modules"; test -d $(WEB)/node_modules && echo "ok" || echo "FALTA — make web-deps"
	@printf "%-9s " "dist"; test -f $(WEB)/dist/index.html && echo "ok (el lanzador lo sirve)" || echo "no construido — make web-build"
	@printf "%-9s " "ollama"; command -v ollama >/dev/null 2>&1 && echo "instalado (arranca con: ollama serve)" || echo "no está — CORT responde en modo eco"
	@printf "%-9s " "audio"; command -v wpctl >/dev/null 2>&1 && wpctl status 2>/dev/null | sed -n '/^Audio/,/Video/p' | grep -cE '^\s.*\*\s+[0-9]+\.' | xargs -I{} echo "{} sink(s) activo(s)" || echo "sin wpctl"

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

# `CORT_DOTENV=0` no es un adorno: el core ahora lee `.env`, y un `.env` con una
# `CORT_MEMORY_DB` personal desviaría la suite a la base de datos de quien
# programa. Las pruebas nunca leen el archivo de nadie. `CORT_AUDIT_LOG` va por el
# mismo motivo con la bitácora nueva: las pruebas de red **sí** rechazan lazos a
# propósito, y esas líneas falsa no pueden acabar en `data/rechazos.jsonl`, que es
# el registro que la usuaria lee para saber si alguien probó su puerta.
test:
	cd $(CORE) && CORT_DOTENV=0 CORT_AUDIT_LOG=$${TMPDIR:-/tmp}/cort-make-test-rechazos.jsonl $(PY) -m unittest discover -s tests -v

# Quién intentó lo que CORT no dejó: lee el registro real, en la carpeta que
# ignora `.gitignore`. Aquí **sí** se lee el `.env` (sin `CORT_DOTENV=0`), porque
# lo que se busca es la bitácora de esta máquina, no una base de pruebas.
rechazos:
	cd $(CORE) && $(PY) -m cort_core.audit

.PHONY: setup install doctor dev launch web web-deps web-build demo test rechazos

