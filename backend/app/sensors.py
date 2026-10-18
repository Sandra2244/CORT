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


def list_dir(rel: str = "") -> dict:
    """rel va con '/' entre raíz y subcarpetas, p.ej. 'Documentos/CORT/docs'."""
    parts = [p for p in rel.replace("\\", "/").split("/") if p]
    if not parts:
        out = []
        for k, v in ROOTS.items():
            if not v.exists():
                continue
            try:
                n = sum(1 for e in v.iterdir() if not e.name.startswith("."))
            except OSError:
                n = 0
            out.append({"name": k, "type": "dir", "size": n, "fecha": _fecha(v)})
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
        return {"error": "sin permiso para leer esa carpeta"}
    return {"path": "/".join(parts), "entries": entries}


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
