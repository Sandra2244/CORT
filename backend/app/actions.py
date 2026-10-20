"""Acciones del sistema para CORT — POST /api/command.

La pantalla ya resuelve sola las órdenes que son *de ventana* (organizar,
ocultar, abrir el cerebro…). Aquí va lo que necesita al **sistema operativo**:
apuntar una nota, abrir una carpeta o un archivo, lanzar un sitio de la lista
blanca y reproducir música.

Diseño: una frase puede contener VARIAS órdenes separadas por «y / luego /
después», así que se ejecutan todas y se responde con un resumen. Si alguna
requiere inteligencia (p. ej. «abre mi carpeta de facturas y dime cuánto
gasté»), el texto sobrante se manda al cerebro híbrido.

Seguridad: ninguna acción usa shell; solo las funciones de `sensors`, que ya
validan que la ruta caiga dentro de las raíces permitidas y que la extensión
no sea ejecutable.
"""
from __future__ import annotations

import re

import memory
import sensors

SPLIT = re.compile(r"\s+(?:y\s+|luego\s+|despu[eé]s\s+|tambi[eé]n\s+)", re.I)

RE_NOTA = re.compile(r"^(?:apunta|anota|apunta que|recuerda|takes? note|nota[:\s])\s+(.+)", re.I | re.S)
RE_LANCAR = re.compile(r"^(?:abre|abrir|lanza|lanza|abre\s+la\s+p[aá]gina\s+de|open)\s+"
                       r"(youtube|el\s+navegador|navegador|la\s+navegador)\b[\s\.\!]*$", re.I)
RE_CARPETA = re.compile(r"^(?:abre|muestra|mu[eé]strame|abre\s+la\s+carpeta)\s+"
                        r"(?:la\s+carpeta\s+(?:de\s+)?|los\s+|las\s+|el\s+)?([\wáéíóúñü .\-]+)", re.I)
RE_ARCHIVO = re.compile(r"^(?:abre|abrir|muestra|mu[eé]strame)\s+(?:el\s+archivo\s+|la\s+)?(\S+\.\w{2,5})\b", re.I)
RE_MUSICA = re.compile(r"^(?:reproduce|pon|ponme|toca)\s+(?:m[uú]sica|la\sm[uú]sica|unapo|una\s+canci[oó]n)"
                        r"[\s\.\!]*$|^(?:reproduce|pon|ponme|toca)\s+m[uú]sica", re.I)
RE_YOUTUBE = re.compile(r"youtube", re.I)

ROOT_NAMES = list(sensors.ROOTS.keys())


def _find_root(word: str) -> str | None:
    """«Documentos», «documentos», «mi carpeta de Documentos» → la clave exacta."""
    w = word.strip().lower()
    for name in ROOT_NAMES:
        if name.lower() == w:
            return name
    for name in ROOT_NAMES:
        if w and (w in name.lower() or name.lower() in w):
            return name
    return None


def run_command(message: str) -> dict:
    """{reply, source, done:[nombre-de-acción]} — lo que espera la pantalla."""
    text = (message or "").strip()
    if not text:
        return {"reply": "¿En qué puedo ayudarte?", "source": "local", "done": []}

    done: list[str] = []
    lines: list[str] = []
    leftovers: list[str] = []

    for chunk in SPLIT.split(text):
        c = chunk.strip(" .,¡!")
        if not c:
            continue
        hit = _one(c)
        if hit is None:
            leftovers.append(chunk.strip())
        else:
            name, msg = hit
            done.append(name)
            if msg:
                lines.append(msg)

    if not done:
        return _brain(text)

    if leftovers:
        extra = " ".join(leftovers)
        reply, source = _brain(extra)[:2]
        lines.append(reply)
    else:
        source = "ejecutor"

    reply = " · ".join(lines) if lines else "Hecho."
    memory.remember("user", text, "accion")
    memory.remember("assistant", reply, source)
    return {"reply": reply, "source": source, "done": done}


def _one(c: str) -> tuple[str, str] | None:
    """Una orden suelta → (nombre, mensaje) o None si no es acción."""
    m = RE_NOTA.match(c)
    if m:
        txt = m.group(1).strip()
        if len(txt) < 2:
            return None
        nid = memory.add_note(txt)
        return "nota", f"Nota #{nid} apuntada: «{txt[:60]}»"

    if RE_LANCAR.match(c) or RE_YOUTUBE.search(c):
        key = "youtube" if RE_YOUTUBE.search(c) else "navegador"
        r = sensors.launch_app(key)
        return "app", (f"Abriendo {key} en tu navegador." if r.get("ok")
                       else f"No pude abrir {key}: {r.get('error', 'sin navegador')}")

    m = RE_ARCHIVO.match(c)
    if m:
        rel = m.group(1).strip()
        cand = _guess_file(rel)
        if cand:
            r = sensors.open_path(cand)
            if r.get("ok"):
                return "archivo", f"Abriendo {cand.split('/')[-1]} en su visor."
            return "archivo", f"No pude abrir {cand.split('/')[-1]}: {r.get('error')}"
        return None

    m = RE_CARPETA.match(c)
    if m:
        root = _find_root(m.group(1))
        if root:
            r = sensors.open_dir(root)
            return ("carpeta", f"Abriendo la carpeta {root} en el explorador."
                    if r.get("ok") else f"No pude abrir {root}: {r.get('error')}")
        return None

    if RE_MUSICA.match(c):
        r = sensors.play_external()
        return ("musica", f"Poniendo {r['cancion']} en tu reproductor."
                if r.get("ok") else f"Sin música: {r.get('error')}")

    return None


def _guess_file(nombre: str) -> str | None:
    """Busca `nombre` (o su raíz) dentro de las raíces y devuelve la ruta relativa."""
    needle = nombre.lower().strip()
    stem = re.sub(r"\.\w{2,5}$", "", needle)
    for root_name, root in sensors.ROOTS.items():
        if not root.exists():
            continue
        try:
            for f in root.rglob("*"):
                if not f.is_file():
                    continue
                fn = f.name.lower()
                if fn == needle or stem and (stem in fn or fn.startswith(stem)):
                    if f.suffix.lower() in sensors.OPEN_EXT:
                        return f"{root_name}/{f.relative_to(root)}".replace("\\", "/")
        except (PermissionError, OSError):
            continue
    return None


def _brain(text: str) -> dict:
    import brain
    reply, source = brain.think(text, memory.history())
    memory.remember("user", text)
    memory.remember("assistant", reply, source)
    return {"reply": reply, "source": source, "done": []}
