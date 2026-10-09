"""
Los atuendos del avatar son archivos que viven en el disco de la usuaria, no en
el repositorio.

Tres razones, en orden de importancia:

1. **Peso.** Un VRM de CORT mide entre 16 y 21 MB. Ocho atuendos son 150 MB de
   binario en el historial de git para siempre, y `git clone` dejaría de ser un
   comando que uno echa a volar.
2. **Licencia.** Los modelos vienen de fuera y su permiso de redistribución no
   está comprobado. Servirlos desde una carpeta que ella ya tiene evita el
   asunto; commithearlos lo convertiría en una pregunta legal.
3. **Privacidad.** La carpeta de avatares puede tener renders con su cara.

Por eso la raíz la decide ella con `CORT_AVATAR_DIR`. **Sin variable no hay
función**: `raiz()` devuelve `None`, el endpoint responde 404 y la interfaz ni
siquiera muestra el selector. Y con variable, sólo se ve lo que hay dentro de
esa carpeta — nunca lo demás del disco.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Lo que se sirve, con su `Content-Type`. La lista es cerrada a propósito: una
# extensión que no esté aquí no se entrega aunque exista en la carpeta, así que
# colar un `.py` o un `.sh` en el directorio de avatares no convierte CORT en un
# lector de código fuente.
EXTENSIONES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".vrm": "model/vrm",
}

# Nombres de archivo reales: «Aira pijama sin fondo.png», «aira_base.vrm»,
# «5. Modelo Cyber Tecnológica 2D». Lo que no entra es la ruta con `..`, el
# separador o el carácter nulo — no hace falta una lista negra si la forma
# permitida es estrecha.
NOMBRE_VALIDO = re.compile(r"^[\w][\w .()º'&\-]{0,119}$", re.UNICODE)


def raiz() -> Path | None:
    """El directorio de atuendos, o `None` si la usuaria no lo activó."""
    bruto = os.getenv("CORT_AVATAR_DIR", "").strip()
    if not bruto:
        return None
    base = Path(bruto).expanduser()
    return base if base.is_dir() else None


def listar(base: Path | None = None) -> list[dict]:
    """
    Los archivos de atuendo, ordenados por nombre.

    Se resuelve la raíz antes de comparar: si `CORT_AVATAR_DIR` apunta a un enlace
    simbólico, `Path.iterdir()` devuelve rutas con el enlace en el nombre y un
    `relative_to` ingenuo contra la raíz *sin resolver* fallaría en silencio,
    dejando el selector vacío sin explicación.
    """
    base = base or raiz()
    if base is None:
        return []
    base = base.resolve()
    items: list[dict] = []
    for ruta in sorted(base.iterdir(), key=lambda p: p.name.lower()):
        if not ruta.is_file() or ruta.name.startswith("."):
            continue
        tipo = EXTENSIONES.get(ruta.suffix.lower())
        if tipo is None:
            continue
        items.append({
            "nombre": ruta.name,
            "mime": tipo,
            "bytes": ruta.stat().st_size,
        })
    return items


def ruta_segura(nombre: str, base: Path | None = None) -> Path | None:
    """
    La ruta real de un atuendo, o `None` si no se debe servir.

    El orden importa: primero la forma del nombre (así un `../../etc/passwd` se
    rechaza sin tocar el disco), luego resolver, y sólo después comprobar que lo
    resuelto sigue dentro de la raíz. Comprobar con `startswith` sobre cadenas es
    el fallo clásico: `/avatares2/x.png` empieza por `/avatares` y no está dentro.
    """
    base = base or raiz()
    if base is None or not isinstance(nombre, str) or not NOMBRE_VALIDO.match(nombre):
        return None
    candidato = (base / nombre).resolve()
    try:
        candidato.relative_to(base.resolve())
    except ValueError:
        return None
    if candidato.suffix.lower() not in EXTENSIONES or not candidato.is_file():
        return None
    return candidato


def tipo_de(ruta: Path) -> str:
    return EXTENSIONES[ruta.suffix.lower()]
