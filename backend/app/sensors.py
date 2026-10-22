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

WEATHER_CACHE: dict[str, dict] = {}   # por lo que se preguntó: {clave: {"t":…, "data":…}}

# Códigos WMO de Open-Meteo, en español y de menor a mayor: la tabla es EXACTA por
# código, y el «variable» sólo cubre un número que Open-Meteo no publicara ese día.
CIELO_WMO = {
    0: "despejado", 1: "mayormente despejado", 2: "parcialmente nublado", 3: "nublado",
    45: "niebla", 48: "niebla con escarcha", 51: "llovizna débil", 53: "llovizna",
    55: "llovizna intensa", 56: "llovizna helada", 57: "llovizna helada intensa",
    61: "lluvia débil", 63: "lluvia", 65: "lluvia fuerte", 66: "lluvia helada",
    67: "lluvia helada fuerte", 71: "nevada débil", 73: "nevada", 75: "nevada intensa",
    77: "granizo fino", 80: "chubascos débiles", 81: "chubascos", 82: "chubascos fuertes",
    85: "chubascos de nieve", 86: "chubascos de nieve fuertes",
    95: "tormenta eléctrica", 96: "tormenta con granizo", 99: "tormenta con granizo fuerte",
}


def cielo_de(codigo) -> str:
    """Nombre en español de un código WMO. Nunca inventa: desconocido es desconocido."""
    try:
        c = int(codigo)
    except (TypeError, ValueError):
        return "sin dato de cielo"
    return CIELO_WMO.get(c, f"cielo sin clasificar (código {c})")



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


def geo(lugar: str) -> dict:
    """Convierte un topónimo en coordenadas con el geocoder gratuito de Open-Meteo.

    Sin clave API y sin cuenta: `GET https://geocoding-api.open-meteo.com/v1/search`.
    Medido el 2026-10-22 con `name=Madrid`: contestó con `results[0]` =
    `{latitude: 40.4165, longitude: -3.70256, country: "España", admin1: "Comunidad
    Autónoma de Madrid", timezone: "Europe/Madrid"}`, así que de ahí salen las
    coordenadas Y el nombre que se enseña, y no hace falta inventarse ninguno.

    Cachea el nombre 6 h (un topónimo no se mueve) y NUNCA adivina: si el geocoder no
    lista resultados, devuelve `sin-lugar` con lo que se buscó, para que la cara lo
    repita entre comillas en vez de dar el tiempo de otra ciudad.
    """
    busca = (lugar or "").strip()
    if not busca:
        return {"ok": False, "error": "sin-lugar", "busca": lugar}
    clave = "geo:" + busca.lower()
    ahora = time.time()
    guardado = WEATHER_CACHE.get(clave)
    if guardado and ahora - guardado["t"] < 6 * 3600:
        return guardado["data"]
    try:
        r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                         params={"name": busca, "count": 5, "language": "es",
                                 "format": "json"}, timeout=8)
        r.raise_for_status()
        resultados = r.json().get("results") or []
        if not resultados:
            # `sin-lugar` NO es un fallo de red: es que ese nombre no está en el mapa.
            # Se sale con eso escrito para que nadie lo confunda con «no hay internet».
            return {"ok": False, "error": "sin-lugar", "busca": busca}
        # Si la dueña dice «Madrid» y el primer golpe es «Madrid de Cilicia» (Turquía),
        # el orden del geocoder ya trae primero el de más población; se toma `results[0]`
        # y se enseña país y región para que el propio renglón permita rectificar.
        g = resultados[0]
        nombre = ", ".join(x for x in (g.get("name"), g.get("country")) if x)
        data = {"ok": True, "lat": g["latitude"], "lon": g["longitude"],
                "lugar": nombre, "region": g.get("admin1") or "",
                "nombre": g.get("name") or busca}
        WEATHER_CACHE[clave] = {"t": ahora, "data": data}
        return data
    except Exception as e:
        return {"ok": False, "error": f"sin datos de lugar ({type(e).__name__})"}


def weather(lugar: str | None = None, lat: float | None = None,
            lon: float | None = None) -> dict:
    """Clima de un sitio: por nombre si lo trae `lugar`, y si no, por IP.

    Open-Meteo otra vez (`/v1/forecast`, gratis y sin clave), con `current` y `daily`
    en la misma llamada para no pedir dos veces lo mismo. Cachea 20 minutos POR
    CONSULTA: antes había un único hueco de caché, así que preguntar por Madrid y
    luego por Sevilla se pisaban la respuesta, y con ella la ventana de entorno
    refresco cada 10 min se comía el clima de la ciudad anterior.

    Honestidad medida: si falta un campo, se dice `sin-datos` con el motivo y se
    devuelve `ok: false`; en ningún momento se rellena un número inventado, y el
    código de cielo que no está en la tabla WMO se llama a sí mismo
    «cielo sin clasificar (código N)» en vez de «despejado» — que era lo que salía
    antes por culpa de un `next(… if cod >= k)` que ganaba siempre el 0.
    """
    ahora = time.time()
    por_ip = False
    if lat is None and lugar:
        g = geo(lugar)
        if not g.get("ok"):
            return g
        lat, lon = g["lat"], g["lon"]
        nombre = g["lugar"]
    elif lat is not None:
        nombre = lugar or "ese sitio"
    else:
        # Sin ciudad nombrada: la IP. `ip-api.com` es el único que había, y ahora pide
        # también `city`, porque «Exterior: 15 °C» sin decir de dónde es media respuesta.
        por_ip = True
        clave = "auto"
        guardado = WEATHER_CACHE.get(clave)
        if guardado and ahora - guardado["t"] < 1200:
            return guardado["data"]
        try:
            g = requests.get("http://ip-api.com/json/", params={"fields": "lat,lon,city"},
                             timeout=6).json()
        except Exception as e:
            return {"ok": False, "error": f"sin datos de clima ({type(e).__name__})"}
        lat, lon = g.get("lat"), g.get("lon")
        if not lat:
            return {"ok": False, "error": "sin-datos: ni la IP dio coordenadas"}
        nombre = g.get("city") or "tu ubicación"

    clave = f"w:{round(lat, 3)},{round(lon, 3)}"
    guardado = WEATHER_CACHE.get(clave)
    if guardado and ahora - guardado["t"] < 1200:
        return guardado["data"]
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": round(lat, 3), "longitude": round(lon, 3),
                    "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                               "weather_code,wind_speed_10m",
                    "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                             "precipitation_probability_max",
                    "timezone": "auto", "forecast_days": 2},
            timeout=8)
        r.raise_for_status()
        w = r.json()
        cur = w.get("current") or {}
        if "temperature_2m" not in cur:
            return {"ok": False, "error": "sin-datos: Open-Meteo contestó sin `current`"}
        dia = (w.get("daily") or {})
        def hoy(campo):
            v = (dia.get(campo) or [None])[0]
            return v
        def manana(campo):
            lista = dia.get(campo) or []
            return lista[1] if len(lista) > 1 else None
        data = {"ok": True, "lugar": nombre, "lat": lat, "lon": lon,
                "hora": cur.get("time"), "zona": w.get("timezone"),
                "temp": cur["temperature_2m"], "sensacion": cur.get("apparent_temperature"),
                "humedad": cur.get("relative_humidity_2m"),
                "viento": cur.get("wind_speed_10m"),
                "codigo": cur.get("weather_code"), "cielo": cielo_de(cur.get("weather_code")),
                "max": hoy("temperature_2m_max"), "min": hoy("temperature_2m_min"),
                "lluvia": hoy("precipitation_probability_max"),
                "cielo_manana": cielo_de(manana("weather_code")),
                "lluvia_manana": manana("precipitation_probability_max"),
                "max_manana": manana("temperature_2m_max"),
                "min_manana": manana("temperature_2m_min")}
        WEATHER_CACHE[clave] = {"t": ahora, "data": data}
        if por_ip:
            # La ranura «auto» es LA DE LA IP: sólo se escribe desde ese camino. Si se
            # escribiera también al preguntar por una ciudad, la ventana de entorno
            # (que llama sin argumentos cada 10 min) leería el clima de Madrid creyendo
            # que es el de la ubicación del PC.
            WEATHER_CACHE["auto"] = {"t": ahora, "data": data}
        return data
    except Exception as e:
        return {"ok": False, "error": f"sin datos de clima ({type(e).__name__})"}


def frase(w: dict) -> str:
    """El clima dicho en una frase, con lo que hay y sin inventar lo que no."""
    if not w.get("ok"):
        return ""
    piezas = [f"{w['temp']:.0f} °C, {w['cielo']}"]
    if w.get("sensacion") is not None and abs(w["sensacion"] - w["temp"]) >= 1.5:
        piezas.append(f"sensación {w['sensacion']:.0f} °C")
    if w.get("viento") is not None:
        piezas.append(f"viento {w['viento']:.0f} km/h")
    if w.get("humedad") is not None:
        piezas.append(f"humedad {w['humedad']:.0f} %")
    donde = w.get("lugar") or "aquí"
    dicho = f"En {donde}: " + ", ".join(piezas) + "."
    if w.get("max") is not None and w.get("min") is not None:
        dicho += f" Hoy entre {w['min']:.0f} y {w['max']:.0f} °C"
        if w.get("lluvia") is not None:
            dicho += f", con un {w['lluvia']:.0f} % de probabilidad de lluvia"
        dicho += "."
    if w.get("lluvia_manana") is not None and w["lluvia_manana"] >= 40:
        dicho += (f" Mañana pinta serio: {w['lluvia_manana']:.0f} % de lluvia "
                  f"y {w['cielo_manana']}.")
    return dicho

