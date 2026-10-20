"""Config persistente de CORT — la que se edita desde la ventana PERFIL.

Motivos de existir:
  * En un teléfono (o en cualquier equipo) no se puede editar un `.env` ni
    reiniciar el servidor, así que el cerebro lee SUS ajustes de un archivo
    JSON al momento de cada petición.
  * Las claves de Groq/Gemini se quedan en el propio disco, nunca viajan a
    ningún servidor. `GET /api/config` solo devuelve una máscara.

Orden de prioridad de cada valor:  cort_config.json  >  variable de entorno  >  default
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "cort_config.json"
LOCK = threading.Lock()

# claves conocidas y su valor por defecto (vacio = "sin configurar")
DEFAULTS = {
    "mode": "",
    "groq_key": "",
    "gemini_key": "",
    "ollama_url": "",
    "ollama_model": "",
    "gemini_model": "",
    "bg_beeps": "1",
}

ENV_NAMES = {
    "mode": "CORT_MODE",
    "groq_key": "GROQ_API_KEY",
    "gemini_key": "GEMINI_API_KEY",
    "ollama_url": "OLLAMA_URL",
    "ollama_model": "OLLAMA_MODEL",
    "gemini_model": "GEMINI_MODEL",
}

ENV_DEFAULTS = {
    "ollama_url": "http://localhost:11434",
    "ollama_model": "qwen2.5:3b",
    "gemini_model": "gemini-2.0-flash",
    "mode": "auto",
}


def raw() -> dict:
    """Los 7 ajustes ya resueltos (archivo > env > default).

    Un valor guardado vacío ('') cuenta como "escrito a propósito" y pisa el
    entorno: así la interfaz puede borrar una clave o un URL sin reiniciar nada."""
    import os

    try:
        stored = json.loads(FILE.read_text(encoding="utf-8"))
        if not isinstance(stored, dict):
            stored = {}
    except (OSError, ValueError):
        stored = {}
    out = {}
    for k, dflt in DEFAULTS.items():
        if k in stored:
            v = stored[k]
        else:
            v = os.environ.get(ENV_NAMES.get(k, "")) or dflt or ENV_DEFAULTS.get(k, "")
        out[k] = str(v).strip()
    out["mode"] = out["mode"] if out["mode"] in ("auto", "local", "online", "offline") else "auto"
    return out


def masked() -> dict:
    """Como `raw()`, pero las claves solo se insinúan: sirve para la interfaz."""
    c = raw()
    for k in ("groq_key", "gemini_key"):
        v = c.get(k, "")
        c[k] = (v[:6] + "…" + str(len(v))) if v else ""
    return c


def set_value(clave: str, valor: str) -> bool:
    if clave not in DEFAULTS:
        return False
    valor = (valor or "").strip()
    delete = valor in ("-", "(vacio)", "null")           # la pantalla pide borrar
    if clave == "mode" and not delete and valor not in ("auto", "local", "online", "offline"):
        return False
    with LOCK:
        try:
            data = json.loads(FILE.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {}
        except (OSError, ValueError):
            data = {}
        if delete:
            data.pop(clave, None)
        elif valor:
            data[clave] = valor
        else:
            data[clave] = ""          # guardar vacío = borrar de verdad (pisa al .env)
        FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(FILE)
    return True
