"""Sensores de CORT: explorador de archivos seguro + clima (Open-Meteo, gratis).

Todo con caché y tolerancia a estar sin internet.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

HOME = Path.home()
# Solo se puede navegar por estas raíces (seguridad: CORT no lee el sistema entero)
ROOTS = {
    "Documentos": HOME / "Documentos",
    "Documents": HOME / "Documents",
    "Escritorio": HOME / "Escritorio",
    "Desktop": HOME / "Desktop",
    "Descargas": HOME / "Descargas",
    "Downloads": HOME / "Downloads",
    "Imágenes": HOME / "Imágenes",
    "Pictures": HOME / "Pictures",
    "Música": HOME / "Música",
    "Music": HOME / "Music",
    "Videos": HOME / "Videos",
}

WEATHER_CACHE = {"t": 0.0, "data": None}


def _fecha(p: Path) -> str:
    """Última modificación como AAAA-MM-DD HH:MM (columna estilo JARVIS)."""
    import datetime as _dt
    try:
        return _dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except OSError:
        return ""


def _counts(p: Path) -> tuple[int, int]:
    """(carpetas, archivos) directos, ignorando ocultos — la sublínea
    «6 folders · 2 notes» del árbol de la referencia."""
    f = n = 0
    try:
        for e in p.iterdir():
            if e.name.startswith("."):
                continue
            if e.is_dir():
                f += 1
            else:
                n += 1
    except OSError:
        return 0, 0
    return f, n


def list_dir(rel: str = "") -> dict:
    """rel va con '/' entre raíz y subcarpetas, p.ej. 'Documentos/CORT/docs'."""
    parts = [p for p in rel.replace("\\", "/").split("/") if p]
    if not parts:
        out = []
        for k, v in ROOTS.items():
            if not v.exists():
                continue
            folders, files = _counts(v)
            out.append({"name": k, "type": "dir", "size": folders + files,
                        "folders": folders, "files": files, "fecha": _fecha(v)})
        return {"path": "", "entries": out}
    root_name = parts[0]
    if root_name not in ROOTS:
        return {"error": f"raíz no permitida: {root_name}"}
    target = ROOTS[root_name]
    for p in parts[1:]:
        target = target / p
    try:
        target = target.resolve()
        target.relative_to(ROOTS[root_name].resolve())  # bloquea ../
    except (ValueError, RuntimeError):
        return {"error": "ruta fuera de las carpetas permitidas"}
    if not target.is_dir():
        return {"error": f"no es carpeta: {target.name}"}
    entries = []
    try:
        for e in sorted(target.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            if e.name.startswith("."):
                continue
            entries.append({
                "name": e.name,
                "type": "dir" if e.is_dir() else "file",
                "size": e.stat().st_size if e.is_file() else 0,
                "fecha": _fecha(e),
            })
            if len(entries) >= 300:
                break
    except PermissionError:
        return {"path": "/".join(parts), "entries": [],
                "error": "sin permiso para leer esa carpeta", "needPermission": True}
    return {"path": "/".join(parts), "entries": entries}


def tree(rel: str = "", limit: int = 12) -> dict:
    """Hijos DIRECTOS de una carpeta, cada uno con sus propios conteos.
    Sirve para expandir el árbol lateral sin abrir la ventana de Archivos."""
    d = list_dir(rel)
    if "error" in d:
        return d
    kids = []
    for e in d["entries"]:
        if e["type"] != "dir":
            continue
        sub = "/".join(x for x in [d["path"], e["name"]] if x)
        folders, files = _counts(_resolve(sub))
        kids.append({"name": e["name"], "path": sub,
                     "folders": folders, "files": files, "fecha": e["fecha"]})
        if len(kids) >= limit:
            break
    return {"path": d["path"], "children": kids}


def _resolve(rel: str) -> Path:
    parts = [p for p in rel.replace("\\", "/").split("/") if p]
    target = ROOTS[parts[0]] if parts and parts[0] in ROOTS else HOME
    for p in parts[1:]:
        target = target / p
    return target


AUDIO_EXT = {".mp3", ".ogg", ".wav", ".m4a", ".flac", ".opus"}


def music_list(limit: int = 200) -> list[dict]:
    """Canciones dentro de las raíces Música/Music (recursivo, sin salir de ellas)."""
    out: list[dict] = []
    for root_name in ("Música", "Music"):
        root = ROOTS.get(root_name)
        if not root or not root.exists():
            continue
        for f in sorted(root.rglob("*")):
            if f.suffix.lower() in AUDIO_EXT and f.is_file():
                try:
                    rel = f.relative_to(root)
                    out.append({"nombre": f.stem, "artista": rel.parent.name
                                if str(rel.parent) != "." else "—",
                                "ruta": f"{root_name}/{rel}".replace("\\", "/"),
                                "dur": ""})
                except ValueError:
                    continue
            if len(out) >= limit:
                return out
    return out


def music_path(rel: str) -> Path | None:
    """Resuelve una ruta relativa segura dentro de las raíces de música."""
    parts = [p for p in rel.replace("\\", "/").split("/") if p]
    if not parts or parts[0] not in ("Música", "Music"):
        return None
    root = ROOTS.get(parts[0])
    if not root:
        return None
    target = root.joinpath(*parts[1:])
    try:
        target = target.resolve()
        target.relative_to(root.resolve())
    except (ValueError, RuntimeError):
        return None
    return target if target.is_file() and target.suffix.lower() in AUDIO_EXT else None


def play_external(rel: str = "") -> dict:
    """Abre una canción con el reproductor PREDETERMINADO del sistema
    (VLC, etc.). Sin `rel` elige una al azar de tu carpeta Música.
    Seguridad: solo archivos ya validados por music_path()."""
    import platform
    import random
    import subprocess

    if rel:
        f = music_path(rel)
        if not f:
            return {"ok": False, "error": "canción no encontrada en Música"}
    else:
        songs = music_list()
        if not songs:
            return {"ok": False, "error": "no hay música en ~/Música"}
        f = music_path(random.choice(songs)["ruta"])
    try:
        if platform.system() == "Windows":
            import os
            os.startfile(str(f))  # noqa: S606 — ruta validada
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", str(f)])
        else:
            subprocess.Popen(["xdg-open", str(f)])
        return {"ok": True, "cancion": f.stem, "reproductor": "predeterminado"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# Lanzador de aplicaciones (video f7d16b9e: "APPLICATION LANCÉE"):
# LISTA BLISTA estricta — solo estas claves, con URL fija. Nunca se abre
# nada que el usuario escriba libremente (seguridad ante todo).
LAUNCH_ALLOWLIST = {
    "youtube": "https://www.youtube.com",
    "navegador": "https://duckduckgo.com",
}


def launch_app(name: str) -> dict:
    """Abre una app/sitio de la lista blanca con el navegador predeterminado."""
    import webbrowser

    key = (name or "").strip().lower()
    url = LAUNCH_ALLOWLIST.get(key)
    if not url:
        return {"ok": False, "error": f"no permitida: {key or '(vacío)'} "
                f"(solo: {', '.join(LAUNCH_ALLOWLIST)})"}
    try:
        ok = webbrowser.open(url)  # usa el navegador predeterminado del sistema
        return {"ok": bool(ok), "app": key, "url": url}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# Abrir un archivo desde la ventana ARCHIVOS (POST /api/open).
# Reglas de seguridad, por orden:
#   1. la ruta tiene que resolver dentro de una ROOTS (nunca /etc, nunca ~/)
#   2. extensión en lista blanca de DOCUMENTOS/MEDIA — nada ejecutable
#   3. se entrega al visor predeterminado del sistema, sin shell=True
OPEN_EXT = {
    ".pdf", ".txt", ".md", ".rtf", ".csv", ".json", ".log",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".heic",
    ".mp3", ".ogg", ".wav", ".m4a", ".flac", ".opus",
    ".mp4", ".mkv", ".webm", ".mov", ".avi",
    ".zip", ".epub",
}
OPEN_MAX_MB = 400


def open_path(rel: str) -> dict:
    import platform
    import subprocess

    f = _resolve(rel or "")
    parts = [p for p in (rel or "").replace("\\", "/").split("/") if p]
    if not parts:
        return open_dir("")          # «raíces» → la carpeta personal
    if parts[0] not in ROOTS:
        return {"ok": False, "error": "ruta fuera de las carpetas permitidas"}
    try:
        f = f.resolve()
        f.relative_to(ROOTS[parts[0]].resolve())
    except (ValueError, RuntimeError, OSError):
        return {"ok": False, "error": "ruta fuera de las carpetas permitidas"}
    if not f.is_file():
        if f.is_dir():
            return open_dir(rel)
        return {"ok": False, "error": f"no existe: {f.name}"}
    ext = f.suffix.lower()
    if ext not in OPEN_EXT:
        return {"ok": False, "error": f"tipo {ext or '(sin extensión)'} no abrible por seguridad"}
    try:
        if f.stat().st_size > OPEN_MAX_MB * 1024 * 1024:
            return {"ok": False, "error": "archivo demasiado grande para abrirlo aquí"}
    except OSError:
        return {"ok": False, "needPermission": True, "error": "sin permiso para leer el archivo"}

    def spawn(cmd: list[str]) -> bool:
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False

    if platform.system() == "Windows":
        try:
            import os
            os.startfile(str(f))  # noqa: S606 — ruta ya validada contra ROOTS
            return {"ok": True, "archivo": f.name, "app": "visor predeterminado"}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    if platform.system() == "Darwin":
        ok = spawn(["open", str(f)])
    else:
        ok = spawn(["xdg-open", str(f)]) or spawn(["gio", "open", str(f)])
    return ({"ok": ok, "archivo": f.name, "app": "visor predeterminado"} if ok
            else {"ok": False, "error": "no hay visor predeterminado (xdg-open) instalado"})


# ── leer en voz alta: sólo texto plano, con el mismo candado de raíces ────────
# `open_path` entrega el archivo al visor del sistema; para hablarlo hace falta el
# **contenido**, y por la boca de CORT no cabe un `.docx` ni un `.pdf`: la lista es
# de lo que se puede leer carácter por carácter. El tope de tamaño y el
# `errors="replace"` están a propósito —el portátil de la dueña tiene 1,8 GiB de
# RAM y esto corre dentro del backend—: un archivo de 200 MB no puede congelar una
# respuesta, y un `.txt` con bytes sueltos no puede cancelar la frase.
LEE_EXT = {".txt", ".md", ".markdown", ".log"}
LEE_MAX_KB = 400


def leer_texto(rel: str, max_caracteres: int = 1400) -> dict:
    """Contenido legible en voz de un archivo de texto dentro de las raíces."""
    parts = [p for p in (rel or "").replace("\\", "/").split("/") if p]
    if not parts or parts[0] not in ROOTS:
        return {"ok": False, "error": "ruta fuera de las carpetas permitidas"}
    try:
        f = _resolve(rel).resolve()
        f.relative_to(ROOTS[parts[0]].resolve())
    except (ValueError, RuntimeError, OSError):
        return {"ok": False, "error": "ruta fuera de las carpetas permitidas"}
    if not f.is_file():
        return {"ok": False, "error": f"no existe: {f.name}"}
    ext = f.suffix.lower()
    if ext not in LEE_EXT:
        if ext in OPEN_EXT:
            # Se marca como «abrir» para que quien lo reciba pueda ofrecer el visor,
            # pero aquí no se abre nada: pedir una lectura no debe levantar ventanas.
            return {"ok": False, "error": f"{f.name} no es un texto que se pueda leer letra a letra",
                    "abrir": rel}
        return {"ok": False, "error": f"{f.name} no es un tipo que pueda leer"}
    try:
        if f.stat().st_size > LEE_MAX_KB * 1024:
            return {"ok": False, "error": f"{f.name} es muy grande para leerlo aquí"}
        crudo = f.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"ok": False, "error": f"sin permiso para leer {f.name}"}
    limpio = " ".join(crudo.split()).strip()
    if not limpio:
        return {"ok": False, "error": f"{f.name} está vacío"}
    cabe = limpio[:max_caracteres]
    return {"ok": True, "archivo": f.name, "carpetas": parts[0],
            "texto": cabe, "entero": len(limpio) <= max_caracteres,
            "caracteres": len(limpio)}


def open_dir(rel: str) -> dict:
    """Abrir una carpeta en el explorador del sistema (mismas reglas de raíz)."""
    import platform
    import subprocess

    parts = [p for p in (rel or "").replace("\\", "/").split("/") if p]
    if parts and parts[0] not in ROOTS:
        return {"ok": False, "error": "ruta fuera de las carpetas permitidas"}
    if not parts:
        # sin ruta = «raíces»: se abre la carpeta personal, donde viven las permitidas
        d = HOME
    else:
        d = _resolve(rel).resolve()
        try:
            d.relative_to(ROOTS[parts[0]].resolve())
        except (ValueError, RuntimeError, OSError):
            return {"ok": False, "error": "ruta fuera de las carpetas permitidas"}
    if not d.is_dir():
        return {"ok": False, "error": "no es carpeta"}
    cmd = (["explorer", str(d)] if platform.system() == "Windows" else
           ["open", str(d)] if platform.system() == "Darwin" else
           ["xdg-open", str(d)])
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"ok": True, "carpeta": d.name, "app": "explorador del sistema"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def weather(lat: float | None = None, lon: float | None = None) -> dict:
    """Clima actual. Usa IP geolocation si no se pasan coordenadas. Cachea 20 min."""
    now = time.time()
    if WEATHER_CACHE["data"] and now - WEATHER_CACHE["t"] < 1200:
        return WEATHER_CACHE["data"]
    try:
        if lat is None:
            g = requests.get("http://ip-api.com/json/?fields=lat,lon", timeout=6).json()
            lat, lon = g.get("lat"), g.get("lon")
            if not lat:
                raise ValueError("sin geo")
        w = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": round(lat, 3), "longitude": round(lon, 3),
                    "current": "temperature_2m,weather_code,wind_speed_10m",
                    "timezone": "auto"},
            timeout=8).json()
        cur = w["current"]
        cod = cur["weather_code"]
        cielos = {0: "despejado", 1: "mayormente despejado", 2: "parcialmente nublado",
                  3: "nublado", 45: "niebla", 48: "niebla helada", 51: "llovizna",
                  61: "lluvia", 63: "lluvia fuerte", 71: "nieve", 80: "chubascos",
                  95: "tormenta eléctrica"}
        desc = next((v for k, v in cielos.items() if cod >= k), "variable")
        data = {"ok": True, "temp": cur["temperature_2m"], "viento": cur["wind_speed_10m"],
                "cielo": desc, "lat": lat, "lon": lon}
        WEATHER_CACHE.update(t=now, data=data)
        return data
    except Exception as e:
        return {"ok": False, "error": f"sin datos de clima ({type(e).__name__})"}
