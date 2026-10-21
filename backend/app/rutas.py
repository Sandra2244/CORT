"""Dónde guarda CORT sus datos — y por qué ya no viven dentro de la app.

El motivo es el disgusto real de la dueña: `cort_config.json` (las claves de
Groq/Gemini que ella pega en **07 · Perfil**) y `cort_memory.db` (sus notas y
pendientes) estaban escritos **junto al código**, dentro de `backend/`. Al
actualizar el instalador —`.exe`, AppImage o `.deb`— se sustituye esa carpeta
entera, y con ella se iba la clave: había que volver a pegarla y CORT se
quedaba mudo hasta entonces.

Ahora viven en la carpeta personal, que ningún instalador toca:

| sistema | dónde |
|---|---|
| Linux / macOS | `~/.cort/` |
| Windows | `%APPDATA%\\CORT\\` (si no existe la variable, `~\\CORT\\`) |
| cualquiera con `CORT_HOME` | exactly donde ella diga (lo usan las pruebas) |

Y la primera vez que arranca, si encuentra los archivos viejos dentro de
`backend/`, los **copia** a la carpeta nueva — copia, no movimiento: si algo se
torciese, el original sigue donde siempre, que es lo que deja poder volver atrás.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

# dónde estaba el código (…/backend/app/rutas.py → …/backend)
CODIGO = Path(__file__).resolve().parent.parent

# los dos archivos que son datos de la dueña y no del programa
DATOS_ARCHIVOS = ("cort_config.json", "cort_memory.db")


def _carpeta_por_defecto() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        return (Path(base) if base else Path.home()) / "CORT"
    return Path.home() / ".cort"


# `CORT_HOME` pisa todo: así las pruebas pueden sandboxear sin tocar su carpeta
# real, y así existe una forma de llevar los datos a un pendrive sin recompilar.
DATOS = Path(os.environ.get("CORT_HOME") or "").expanduser() if os.environ.get("CORT_HOME") \
    else _carpeta_por_defecto()

MIGRADOS: list[str] = []


def archivo(nombre: str) -> Path:
    """Ruta de un archivo de datos, con la mudanza vie→nueva hecha si toca."""
    destino = DATOS / nombre
    if destino.exists():
        return destino
    viejo = CODIGO / nombre
    if viejo.is_file():
        try:
            DATOS.mkdir(parents=True, exist_ok=True)
            shutil.copy2(viejo, destino)
            MIGRADOS.append(nombre)
        except OSError:
            # sin permisos, sin disco, o lo que sea: se sigue usando el de
            # siempre. CORT no se niega a arrancar por una mudanza fallida.
            return viejo
    return destino


def resumen() -> str:
    """Una línea para la consola de arranque: dónde está lo suyo, dicho claro."""
    donde = ", ".join(f"{n} (mudado desde backend/)" for n in MIGRADOS) or "ya estaba aquí"
    return f"datos en {DATOS} · {donde}"
