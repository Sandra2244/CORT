"""Carga del archivo `.env`: la configuración deja de ser humo de documentación.

`AGENTS.md` prohíbe subir `.env` (regla 7: son claves), pero un archivo de ejemplo
que ningún código lee es peor que no tenerlo: `cp .env.example .env` y seguir sin
que nada funcione es exactamente la instalación "mal" que vio una persona nueva.

Reglas de este módulo, por orden de importancia:
1. **Una variable ya exportada gana.** El `.env` es un respaldo, no una imposición:
   `CORT_LLM_CHAIN=qwen3:0.6b make dev` tiene que seguir mandando sobre el archivo.
2. **No se lee en las pruebas.** `CORT_DOTENV=0` lo apaga, y el objetivo `test` del
   `Makefile` lo pone. Sin eso, un `.env` con `CORT_MEMORY_DB=/ruta/personal`
   desviaría la suite a la memoria real de quien programa.
3. **Nunca se devuelven valores.** Lo que se registra son las *claves* que se
   añadieron: un log con `CORT_LLM_*` lleno de rutas y tokens no es un log.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

# Raíz del proyecto: env.py vive en services/core/cort_core/, tres niveles por debajo.
ROOT = Path(__file__).resolve().parents[3]

# `export` al principio es costumbre de shell; un valor puede venir entre comillas.
_LINE = re.compile(r"^(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*(.*)$")


def parse(text: str) -> dict[str, str]:
    """Convierte el texto de un `.env` en un diccionario, con criterio tolerante.

    Lo que no casa se ignora en silencio y en bloque: un archivo de configuración
    no es un programa, y reventar el arranque del asistente por una línea mal
    escrita es un fallo de diseñadora, no de usuaria.
    """
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _LINE.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            out[key] = value[1:-1]
            continue
        # Comentario al final de un valor sin comillas: `PUERTO=8765 # el de siempre`
        out[key] = value.split(" #", 1)[0].strip()
    return out


def load_env(path: Path | str | None = None, environ: dict[str, str] | None = None
             ) -> list[str]:
    """Añade al entorno lo que falte y devuelve las **claves** añadidas.

    Con `CORT_DOTENV=0` no toca nada: así la suite de pruebas no puede escribir
    en la base de datos personal de nadie por culpa de un archivo olvidado.
    """
    env = os.environ if environ is None else environ
    if env.get("CORT_DOTENV", "1") == "0":
        return []
    file = Path(path) if path is not None else ROOT / ".env"
    if not file.is_file():
        return []
    added: list[str] = []
    for key, value in parse(file.read_text(encoding="utf-8", errors="replace")).items():
        if key in env:
            continue
        env[key] = value
        added.append(key)
    return added
