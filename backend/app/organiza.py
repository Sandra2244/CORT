"""Organiza los archivos y la música — primero el PLAN, luego el sí.

Por qué va en dos pasos: la dueña pidió orden, no sustos. `plan()` sólo MIRA y
devuelve la lista de movimientos propuestos con un `token`; no toca un solo
archivo. `aplicar()` ejecuta esa misma lista, y sólo si el token sigue siendo
el del último plan pedido (si cambió el árbol, o pasó el tiempo, se rechaza).

Reglas duras, en este orden de importancia:
  · NUNCA borra: aquí no hay `os.remove`, ni `unlink`, ni `rmtree`.
  · NUNCA sobrescribe: si el destino existe (en disco o en el propio plan),
    el nombre gana un sufijo ` (2)`, ` (3)`…
  · NUNCA sale de las raíces de `sensors.ROOTS`: las rutas del plan son
    RELATIVAS a la raíz, para que la cara de JS pueda mostrarlas sin exponer
    el disco entero.
  · Un archivo que ya está donde toca no entra en el plan: movimiento vacío.

Sólo stdlib — sin dependencias nuevas, y leyendo de uno en uno para no
congelar un portátil de 2 núcleos y 1,8 GiB de RAM.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

import sensors

# extensión → carpeta de la promesa «Documentos/<PDF|DOCX|TXT|IMG|AUDIO|VIDEO|OTROS>»
TIPO_EXT = {
    "PDF": (".pdf",),
    "DOCX": (".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx",
             ".ods", ".odp", ".epub"),
    "TXT": (".txt", ".md", ".log", ".csv", ".json"),
    "IMG": (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".heic"),
    "AUDIO": (".mp3", ".ogg", ".wav", ".m4a", ".flac", ".opus"),
    "VIDEO": (".mp4", ".mkv", ".webm", ".mov", ".avi"),
}
EXT_A_TIPO = {e: t for t, exts in TIPO_EXT.items() for e in exts}
CRITERIOS = ("tipo", "anio", "mes")

# cuánto vale un plan antes de caducar: 15 minutos. Después, «pide otro»,
# porque el árbol ya puede no ser el que se prometió.
TTL_S = 900

# último plan en memoria del módulo: sin esto no hay confirmación que valer
_ULTIMO: dict = {}


def _tipo(nombre: str) -> str:
    return EXT_A_TIPO.get(Path(nombre).suffix.lower(), "OTROS")


def _destino(nombre: str, criterio: str, mtime: float) -> tuple[str, str]:
    """(carpetas relativas a la raíz, motivo) para un archivo según el criterio."""
    tipo = _tipo(nombre)
    fecha = dt.datetime.fromtimestamp(mtime)
    periodo = ""
    partes = [tipo]
    if criterio == "anio":
        periodo = str(fecha.year)
        partes.append(periodo)
    elif criterio == "mes":
        periodo = fecha.strftime("%Y-%m")
        partes.append(periodo)
    motivo = tipo.lower() + (f" · {periodo}" if periodo else "")
    return "/".join(partes), motivo


def _construir(raiz: str, criterio: str, limite: int) -> list[dict]:
    """Recorre la raíz y devuelve las entradas propuestas, con sufijos anti-choque.

    Es el mismo código que usan `plan()` y `aplicar()`: lo que se confirma es
    literalmente lo que se recalcularía al aplicar, no una versión de memoria.
    """
    root = sensors.ROOTS[raiz]
    entradas: list[dict] = []
    usadas: set[str] = set()
    for carpeta, dirs, archivos in os.walk(root, topdown=True, followlinks=False,
                                           onerror=lambda e: None):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for nombre in sorted(archivos):
            if len(entradas) >= limite:
                return entradas
            if nombre.startswith("."):
                continue
            f = Path(carpeta) / nombre
            if f.is_symlink() or not f.is_file():
                continue          # enlaces y bichos raros no se mueven
            try:
                rel = f.relative_to(root).as_posix()
                mtime = f.stat().st_mtime
            except OSError:
                continue
            carpetas, motivo = _destino(nombre, criterio, mtime)
            destino = f"{carpetas}/{nombre}"
            if destino == rel:
                continue          # ya está donde toca: movimiento vacío, fuera
            if destino in usadas or (root / destino).exists():
                p = Path(nombre)
                candidato = f"{carpetas}/{p.stem} (2){p.suffix}"
                n = 3
                while candidato in usadas or (root / candidato).exists():
                    candidato = f"{carpetas}/{p.stem} ({n}){p.suffix}"
                    n += 1
                destino = candidato
            usadas.add(destino)
            entradas.append({"de": rel, "a": destino, "motivo": motivo})
    return entradas


def plan(raiz: str, criterio: str = "tipo", limite: int = 2000) -> dict:
    """La propuesta de orden, sin tocar nada. Guarda el token en `_ULTIMO`."""
    if raiz not in sensors.ROOTS:
        return {"ok": False,
                "error": f"no puedo tocar fuera de tus carpetas conocidas: "
                         f"{', '.join(sensors.ROOTS)}"}
    if criterio not in CRITERIOS:
        return {"ok": False, "error": f"criterio desconocido: {criterio} "
                                      f"(usa {', '.join(CRITERIOS)})"}
    root = sensors.ROOTS[raiz]
    if not root.is_dir():
        return {"ok": False, "error": f"la carpeta {raiz} no existe en este equipo"}
    entradas = _construir(raiz, criterio, limite)
    cuando = time.time()
    serial = json.dumps({"raiz": raiz, "criterio": criterio, "entradas": entradas},
                        sort_keys=True, ensure_ascii=False)
    token = hashlib.sha256(f"{serial}|{cuando}".encode("utf-8")).hexdigest()[:16]
    _ULTIMO.clear()
    _ULTIMO.update(raiz=raiz, criterio=criterio, token=token, cuando=cuando)
    return {"ok": True, "raiz": raiz, "criterio": criterio,
            "total": len(entradas), "entradas": entradas, "token": token,
            "caduca_en_s": int(TTL_S)}


def _desocupar(destino: Path) -> Path:
    """Primer nombre libre con sufijo ` (n)`: la última barrera anti-sobrescritura."""
    if not destino.exists():
        return destino
    n = 2
    while True:
        candidato = destino.parent / f"{destino.stem} ({n}){destino.suffix}"
        if not candidato.exists():
            return candidato
        n += 1


def aplicar(raiz: str, criterio: str, token: str) -> dict:
    """Ejecuta el último plan confirmado, uno a uno. Borrar, jamás."""
    if (not _ULTIMO or _ULTIMO.get("raiz") != raiz or _ULTIMO.get("criterio") != criterio
            or _ULTIMO.get("token") != token or time.time() - _ULTIMO.get("cuando", 0) > TTL_S):
        return {"ok": False, "error": "no hay plan que confirmar: pide primero el plan"}
    if raiz not in sensors.ROOTS:
        return {"ok": False,
                "error": f"no puedo tocar fuera de tus carpetas conocidas: "
                         f"{', '.join(sensors.ROOTS)}"}
    root = sensors.ROOTS[raiz]
    # se recalcula el plan AHORA: si el árbol cambió desde la propuesta,
    # se mueve lo que hay, no lo que había
    entradas = _construir(raiz, criterio, 2000)
    movidos, errores = 0, []
    for e in entradas:
        origen = root / e["de"]
        destino = root / e["a"]
        if not origen.is_file():
            continue
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino = _desocupar(destino)       # nunca sobrescribir, ni por asomo
            shutil.move(str(origen), str(destino))
            movidos += 1
        except (OSError, shutil.Error) as ex:
            errores.append(f"{e['de']}: {ex}")
    _ULTIMO.clear()                             # plan consumido: toca pedir otro
    return {"ok": True, "movidos": movidos, "errores": errores}
