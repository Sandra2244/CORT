#!/usr/bin/env python3
"""
CORT — puente local (cerebro real)
==================================
Un solo proceso, dos puertos:
  * 8766 -> sirve la interfaz (sustituye a `python3 -m http.server`)
  * 8765 -> WebSocket /ws, que es la URL que la interfaz ya conoce

Habla el MISMO protocolo JSON que la demo de referencia, así que la página no
cambia. Lo que aquí se responde es REAL:

  check_ollama_status   -> http://127.0.0.1:11434/api/tags + inventario leído en
                           ~/.ollama/models (así la lista funciona con Ollama apagado)
  pull_ollama_model     -> /api/pull (progreso real, byte a byte)
  set_local_model       -> se guarda en cort_state.json
  user_input            -> /api/chat con el modelo elegido (cerebro de CORT)
  system_stats          -> /proc/stat, /proc/meminfo, /proc/stat de disco
  av-scan / scan        -> auditoría local real (autostart, procesos, firmas)
  weather               -> geocoding open-meteo (ciudad) o ipapi.co (por IP) + open-meteo

Todo lo que NO se pueda verificar se dice con la letra grande: el campo
`origen` vale "real" o "no disponible" en cada mensaje. Nada se inventa.

Hardware medido en este equipo: 2 núcleos, 1851 MB de RAM total, ~280 MB libres
con Qoder y el navegador abiertos. Por eso hay DOS puertas: para DESCARGAR un
modelo se pide disco (la RAM no manda); para CARGARLO y chatear se mide la RAM
libre y, si no cabe, se dice el número en vez de congelar el equipo.
"""

import asyncio
import json
import os
import shutil
import signal
import unicodedata
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib import request as urlreq
from urllib.error import URLError, HTTPError
import urllib.parse

BASE = Path(__file__).resolve().parent.parent / "cort-web"
ESTADO = Path(__file__).resolve().parent / "cort_state.json"
OLLAMA = os.environ.get("CORT_OLLAMA", "http://127.0.0.1:11434")
PUERTO_WS = int(os.environ.get("CORT_WS_PORT", "8765"))
PUERTO_WEB = int(os.environ.get("CORT_WEB_PORT", "8766"))

# Modelos que la interfaz ofrece. Dos puertas distintas, porque son dos cosas
# distintas: DESCARGAR gasta disco (y poca RAM), CARGAR el modelo gasta RAM.
# Confundirlas fue lo que dejó CORT sin cerebro: con 288 MB libres el puente
# negaba también la descarga, que no necesita esos 288 MB.
#   ram_uso : MB de RAM disponible exigidos para usarlo en chat
#   mb      : tamaño aproximado del archivo, para el control de disco
MODELOS = {
    "qwen3:4b": {"ram_uso": 2600, "mb": 2500, "tam": "2,5 GB", "nota": "el que recomienda la guía de referencia"},
    "qwen3:8b": {"ram_uso": 5400, "mb": 5200, "tam": "5,2 GB", "nota": "contexto amplio"},
    "dolphin3": {"ram_uso": 2600, "mb": 2500, "tam": "2,5 GB", "nota": "sin filtros, el que trae la demo"},
    "qwen2.5:1.5b": {"ram_uso": 1500, "mb": 1000, "tam": "~1 GB", "nota": "el más ligero que responde bien"},
    "qwen2.5:0.5b": {"ram_uso": 800, "mb": 350, "tam": "~350 MB", "nota": "cabe en la Canaima, responde poco"},
    "phi3:mini": {"ram_uso": 4200, "mb": 3800, "tam": "~3,8 GB", "nota": "pide GPU"},
}

RAM_SERVIDOR = 350     # MB libres mínimos para tener `ollama serve` de pie
RAM_DESCARGA = 250     # MB libres mínimos mientras baja el archivo (es I/O)
MARGEN_DISCO = 500     # MB de colchón además del tamaño del modelo

# Inventario del disco: ~/.ollama/models. Se lee sin necesidad de que el servidor
# esté vivo, que es justo cuando la interfaz no sabía qué había.
OLLAMA_MODELOS = Path(os.environ.get(
    "OLLAMA_MODELOS", os.path.expanduser("~/.ollama/models")))


def ram_estimada_desde_peso(mb_peso):
    """El peso del archivo es MEDIDO; la RAM que hará falta es ESTIMACIÓN
    (pesos + caché KV + contexto). Se avisa de que es estimación al decirlo."""
    return int(mb_peso * 1.4) + 150

from aiohttp import web  # presente en este equipo (verificado)


# ---------------------------------------------------------------- utilidades
def leer_estado():
    try:
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    except Exception:
        return {}


def escribir_estado(d):
    try:
        ESTADO.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[CORT] no se pudo guardar el estado: {e}", file=sys.stderr)


def http_json(url, datos=None, timeout=6):
    """GET si datos es None, POST en caso contrario. Devuelve (ok, dict/str)."""
    try:
        req = urlreq.Request(
            url,
            data=None if datos is None else json.dumps(datos).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlreq.urlopen(req, timeout=timeout) as r:
            cuerpo = r.read().decode("utf-8", "replace")
            try:
                return True, json.loads(cuerpo)
            except json.JSONDecodeError:
                return True, cuerpo
    except (URLError, HTTPError, OSError, TimeoutError) as e:
        return False, str(e)


def ram_disponible_mb():
    """MB disponibles según el kernel, no según una estimación."""
    try:
        for linea in Path("/proc/meminfo").read_text().splitlines():
            if linea.startswith("MemAvailable:"):
                return int(linea.split()[1]) // 1024
    except Exception:
        pass
    return -1


def cpu_ram_disco():
    """Medida real: /proc/stat entre dos muestras, /proc/meminfo, statvfs."""
    try:
        ahora = Path("/proc/stat").read_text().splitlines()[0].split()[1:]
        vals = [int(x) for x in ahora]
        total, ocioso = sum(vals), vals[3] + vals[4]
        global _muestra_prev, _cpu_ultimo, _t_cpu_ultimo
        ahora_t = time.monotonic()
        prev = globals().get("_muestra_prev")
        _muestra_prev = (total, ocioso)
        cpu = globals().get("_cpu_ultimo", 0.0)
        # Con dos muestras separadas por milisegundos el porcentaje es ruido: se
        # reutiliza la última medida válida (ventana mínima de medio segundo).
        if prev and total > prev[0] and ahora_t - globals().get("_t_cpu_ultimo", 0) >= 0.5:
            dt, do = total - prev[0], ocioso - prev[1]
            cpu = max(0.0, min(100.0, 100.0 * (1 - do / dt)))
            _cpu_ultimo = cpu
            _t_cpu_ultimo = ahora_t
        mem = ram_disponible_mb()
        total_mb = 0
        for linea in Path("/proc/meminfo").read_text().splitlines():
            if linea.startswith("MemTotal:"):
                total_mb = int(linea.split()[1]) // 1024
        u = shutil.disk_usage("/")
        return {
            "cpu": round(cpu, 1),
            "ram": round(100 * (1 - mem / total_mb), 1) if total_mb else 0,
            "ram_disponible_mb": mem,
            "ram_total_mb": total_mb,
            "disco_pct": round(100 * u.used / u.total, 1),
            "nucleos": os.cpu_count(),
            "origen": "real",
        }
    except Exception as e:
        return {"cpu": 0, "ram": 0, "origen": f"error: {e}"}


def ollama_vivo():
    ok, datos = http_json(f"{OLLAMA}/api/tags", timeout=3)
    if not ok:
        return False, {}
    modelos = {m.get("name", ""): m.get("name", "") for m in datos.get("models", [])}
    return True, modelos


_inventario_cache = {"t": 0.0, "datos": {}}


def inventario_disco(fuerzo=False):
    """Modelos que YA están en ~/.ollama/models, leídos de los manifests.

    No pregunta al servidor: funciona con Ollama apagado, que es cuando la
    interfaz se quedaba sin lista. Devuelve {nombre:tag: {"mb": peso medido del
    blob mayor, "ram_est": MB libres estimados para usarlo}}. Si no hay carpeta o
    algo no se puede leer, devuelve lo que sí se pudo leer (y se ve vacío, no una
    lista inventada). Se guarda en caché 20 s porque se consulta desde varios sitios
    y dentro de una ordenación.
    """
    ahora = time.monotonic()
    if not fuerzo and ahora - _inventario_cache["t"] < 20:
        return _inventario_cache["datos"]
    out = {}
    try:
        for f in sorted(OLLAMA_MODELOS.glob("manifests/*/*/*/*")):
            partes = str(f).split("/manifests/")[1].split("/")
            nombre, tag = partes[2], partes[3]
            try:
                m = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            pesos = []
            for capa in m.get("layers", []):
                b = OLLAMA_MODELOS / "blobs" / capa["digest"].replace(":", "-")
                try:
                    if b.is_file():
                        pesos.append(b.stat().st_size)
                except OSError:
                    continue
            if not pesos:
                continue
            mb = max(pesos) // (1024 * 1024)
            out[f"{nombre}:{tag}"] = {"mb": mb, "ram_est": ram_estimada_desde_peso(mb)}
    except Exception:
        return {}
    _inventario_cache["t"] = ahora
    _inventario_cache["datos"] = out
    return out


def catalogo():
    """Los descargables de siempre + los que ya están en disco, sin duplicar.

    Cada entrada lleva `origen` para que la interfaz pueda decir la verdad:
    "instalado" (en disco), "descargable" (hay que bajarlo) o ambos.
    """
    cat = {k: dict(v, instalado=False) for k, v in MODELOS.items()}
    for nombre, datos in inventario_disco().items():
        entrada = cat.get(nombre) or {"tam": f"{datos['mb']} MB", "nota": "ya está en tu disco"}
        cat[nombre] = dict(entrada, mb=datos["mb"], ram_uso=datos["ram_est"], instalado=True)
    return cat


def estado_ollama():
    """El estado que pide la interfaz. Con Ollama apagado no devuelve la lista vacía:
    los modelos leídos en disco entran en `found_local_models` porque están instalados
    de verdad, y `en_disco` / `catalogo` dan el detalle con pesos medidos."""
    vivo, modelos = ollama_vivo()
    disco = inventario_disco()
    lista = dict(modelos)
    for nombre in disco:
        lista.setdefault(nombre, nombre)
    return {
        "online": vivo,
        "found_local_models": lista,
        "selected_model": leer_estado().get("local_model", ""),
        "ram_disponible_mb": ram_disponible_mb(),
        "ram_total_mb": cpu_ram_disco().get("ram_total_mb", 0),
        "nucleos": os.cpu_count(),
        "en_disco": disco,
        "catalogo": catalogo(),
        "origen": "real",
    }


def presupuesto_del_modelo(modelo):
    """MB libres que exige `modelo`. Prioridad: lo medido en disco > el catálogo >
    una cuenta prudente por si el modelo no se conoce."""
    disco = inventario_disco().get(modelo)
    if disco:
        return disco["ram_est"], f"peso medido {disco['mb']} MB"
    info = MODELOS.get(modelo) or catalogo().get(modelo) or {}
    if info.get("ram_uso"):
        return int(info["ram_uso"]), "tabla del catálogo"
    return 1200, "sin medir: se aplica el suelo prudente de 1200 MB"


def ollama_arrancar():
    """Levanta `ollama serve` sólo si el binario existe y la RAM lo permite."""
    binario = shutil.which("ollama")
    if not binario:
        return False, "el binario `ollama` no está instalado"
    libre = ram_disponible_mb()
    if libre < RAM_SERVIDOR:
        return False, (
            f"RAM disponible medida: {libre} MB. El servidor `ollama serve` pide ~{RAM_SERVIDOR} MB libres "
            "para no congelar el equipo. Cierra el navegador o las apps pesadas e inténtalo otra vez. "
            "(Descargar un modelo después solo necesita disco.)"
        )
    try:
        subprocess.Popen(
            [binario, "serve"],
            stdout=open("/tmp/cort-ollama.log", "wb"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        return True, f"servidor Ollama iniciado con {libre} MB libres"
    except Exception as e:
        return False, f"no se pudo iniciar: {e}"


# ------------------------------------------------------------------ clima
_ultima_ubicacion = {"lat": None, "lon": None, "ciudad": ""}


def resolver_ubicacion(ciudad=""):
    """(lat, lon, ciudad, origen_del_dato). Dos servicios gratuitos sin clave:

    * nombre de ciudad -> geocoding de open-meteo. ipapi.co NO sirve aquí: su
      ruta `/{x}/json/` pide una IP y con un nombre contesta
      `{"error": true, "reason": "Invalid IP Address"}`, que era como el panel
      del clima se quedaba vacío en cuanto Sandra escribía su ciudad en Ajustes.
    * sin nombre -> ipapi.co por IP.
    """
    if ciudad:
        ok, geo = http_json(
            "https://geocoding-api.open-meteo.com/v1/search?count=1&language=es"
            f"&name={urllib.parse.quote(ciudad)}", timeout=6)
        resultados = (geo or {}).get("results") if isinstance(geo, dict) else None
        if ok and resultados:
            r = resultados[0]
            return r.get("latitude"), r.get("longitude"), r.get("name") or ciudad, "geocoding open-meteo"
        return None, None, ciudad, "geocoding sin resultados"
    ok, geo = http_json("https://ipapi.co/json/", timeout=6)
    if ok and isinstance(geo, dict) and "latitude" in geo and not geo.get("error"):
        return geo["latitude"], geo["longitude"], geo.get("city") or "", "ipapi por IP"
    motivo = (geo or {}).get("reason", "no respondió") if isinstance(geo, dict) else str(geo)
    return None, None, "", f"ipapi: {motivo}"


def clima(ciudad=""):
    """Coordenadas -> open-meteo (sin clave). Si la resolución falla, se usan las
    últimas coordenadas buenas que CORT conoció, y se dice en el mensaje que el
    punto del mapa viene de ahí en vez de dejar el panel vacío."""
    lat, lon, nombre, como = resolver_ubicacion(ciudad)
    de_cache = False
    aviso = ""
    if lat is None and _ultima_ubicacion["lat"] is not None:
        lat, lon = _ultima_ubicacion["lat"], _ultima_ubicacion["lon"]
        aviso = (f"No encontré «{ciudad}» ({como}); te doy el clima del último punto conocido: "
                 f"{_ultima_ubicacion['ciudad'] or 'tu ubicación por IP'}.")
        nombre = _ultima_ubicacion["ciudad"]
        de_cache = True
    if lat is None:
        return {"ok": False, "motivo": f"no se pudo resolver la ubicación ({como}); tampoco hay una anterior guardada"}
    _ultima_ubicacion.update({"lat": lat, "lon": lon, "ciudad": nombre or ciudad})
    ok, w = http_json(
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
        "&timezone=auto",
        timeout=6,
    )
    if not ok or not isinstance(w, dict) or "current" not in w:
        return {"ok": False, "motivo": f"open-meteo no respondió ({str(w)[:90]})"}
    c = w.get("current", {})
    codigos = {0: "despejado", 1: "mayormente despejado", 2: "nublado", 3: "cubierto",
               45: "niebla", 48: "niebla helada", 51: "llovizna ligera", 53: "llovizna",
               61: "lluvia ligera", 63: "lluvia", 65: "lluvia fuerte", 71: "nieve",
               80: "chubascos", 95: "tormenta"}
    return {
        "ok": True, "origen": "real",
        "ville": nombre or ciudad or "tu ubicación",
        "temperature": c.get("temperature_2m"),
        "ressenti": c.get("apparent_temperature"),
        "humidite": c.get("relative_humidity_2m"),
        "vent": c.get("wind_speed_10m"),
        "code": c.get("weather_code"),
        "description": codigos.get(c.get("weather_code"), f"código {c.get('weather_code')}"),
        # Datos del punto usado, para poder decirlo con nombre y sin inventar:
        "resolucion": como,
        "desde_cache": de_cache,
        "ciudad_pedida": ciudad,
        "aviso": aviso,
        "coordenadas": f"{lat},{lon}",
    }


# --------------------------------------------------------------- antivirus
def con_clase(hallazgos, clase):
    """La interfaz imprime `threat.class` en su registro; sin ese campo sale
    «undefined». Se añade aquí, en español, porque el registro se traduce."""
    for h in hallazgos:
        h.setdefault("class", clase)
    return hallazgos


def paso_autostart():
    hallazgos = con_clase(_autostart(), "Arranque")
    return hallazgos


def _autostart():
    """Entradas de arranque del usuario que ejecutan desde rutas temporales o descargan código."""
    hallazgos = []
    casa = Path.home()
    for carpeta in (casa / ".config/autostart", Path("/etc/xdg/autostart")):
        if not carpeta.is_dir():
            continue
        for f in sorted(carpeta.glob("*.desktop"))[:400]:
            try:
                txt = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            exec_line = [l for l in txt.splitlines() if l.startswith("Exec=")]
            if not exec_line:
                continue
            destino = exec_line[0].split("=", 1)[1]
            if any(m in destino for m in ("/tmp/", "/dev/shm/", "curl ", "wget ", "nc ", "base64 -d")):
                hallazgos.append({
                    "name": f"Arranque sospechoso: {f.name}",
                    "desc": "Una entrada de autostart ejecuta algo desde una ruta temporal o descarga código.",
                    "target": str(f),
                })
    return hallazgos


def paso_procesos():
    hallazgos = con_clase(_procesos(), "Proceso")
    return hallazgos


def _procesos():
    """Procesos vivos cuyo binario vive en una carpeta temporal."""
    hallazgos = []
    for pid in sorted((x for x in os.listdir("/proc") if x.isdigit()), key=int):
        try:
            exe = os.readlink(f"/proc/{pid}/exe")
        except OSError:
            continue
        if exe.startswith(("/tmp/", "/dev/shm/", "/var/tmp/")):
            try:
                nombre = Path(f"/proc/{pid}/comm").read_text().strip()
            except Exception:
                nombre = "?"
            hallazgos.append({
                "name": f"Proceso desde carpeta temporal (pid {pid})",
                "desc": f"«{nombre}» se ejecuta desde {exe}; el software legítimo no suele vivir ahí.",
                "target": exe,
            })
    return hallazgos


# Tope de archivos por carpeta: en una Canaima el .cache tiene miles y el paseo
# completo tardaría más que el escaneo; se revisan los primeros y se informa.
TOPE_ARCHIVOS = 2500


def paso_archivos():
    hallazgos = con_clase(_archivos(), "Archivo")
    return hallazgos


def _archivos():
    """Dobles extensiones y firma de prueba EICAR (inofensiva) en carpetas de uso diario."""
    hallazgos = []
    casa = Path.home()
    fin = time.monotonic() + PRESUPUESTO_S
    revisados = 0
    eicar = r"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR"
    for carpeta in (casa / "Escritorio", casa / "Desktop", casa / "Descargas", casa / "Downloads",
                    casa / ".cache", Path("/tmp")):
        if not carpeta.is_dir():
            continue
        try:
            with os.scandir(carpeta) as it:
                for e in it:
                    if revisados >= TOPE_ARCHIVOS or time.monotonic() > fin:
                        hallazgos.append({
                            "name": "Paseo truncado por el tope de archivos",
                            "desc": f"Se revisaron {revisados} entradas (tope del puente para no congelar el equipo); "
                                    "hay carpetas con más contenido del que cabe en una pasada.",
                            "target": str(carpeta),
                        })
                        return hallazgos
                    try:
                        if not e.is_file() or e.stat().st_size > 5 * 1024 * 1024:
                            continue
                        revisados += 1
                        partes = e.name.lower().split(".")
                        if len(partes) >= 3 and partes[-2] in ("pdf", "doc", "jpg", "png", "txt") \
                                and partes[-1] in ("exe", "msi", "scr", "bat", "cmd", "lnk", "vbs", "js"):
                            hallazgos.append({
                                "name": f"Doble extensión: {e.name}",
                                "desc": "El nombre imita un documento pero termina en ejecutable.",
                                "target": e.path,
                            })
                        if e.stat().st_size < 200 and eicar.encode() in open(e.path, "rb").read():
                            hallazgos.append({
                                "name": f"Firma EICAR en {e.name}",
                                "desc": "Archivo de prueba de antivirus. Es inofensivo, pero demuestra que la detección funciona.",
                                "target": e.path,
                            })
                    except OSError:
                        continue
        except OSError:
            continue
    return hallazgos


# El paseo por ~/.config en una Canaima toca decenas de miles de archivos: sin
# tope de tiempo el escaneo congela el equipo. Se limita y se dice en el informe.
PRESUPUESTO_S = 8.0
MAX_HALLAZGOS = 15
OMITIR = {".cache", "Code Cache", "GPUCache", "ShaderCache", "node_modules",
          "crashpad", "Crash Reports", "tmp", "logs", "backups"}


def paso_permisos():
    hallazgos = con_clase(_permisos(), "Permiso")
    return hallazgos


def _permisos():
    """Scripts de la sesión que cualquier otro usuario puede modificar."""
    casa = Path.home()
    raiz = casa / ".config"
    if not raiz.is_dir():
        return []
    fin = time.monotonic() + PRESUPUESTO_S
    hallazgos, revisados, truncado = [], 0, False
    for carpeta, dirs, archivos in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in OMITIR and not d.startswith(".")]
        if time.monotonic() > fin:
            truncado = True
            break
        for n in archivos:
            if not n.endswith(".sh"):
                continue
            ruta = os.path.join(carpeta, n)
            try:
                st = os.stat(ruta)
            except OSError:
                continue
            revisados += 1
            if st.st_mode & 0o022 and os.access(ruta, os.X_OK):
                hallazgos.append({
                    "name": f"Script modificable por otros usuarios: {n}",
                    "desc": "Permisos de escritura globales en un ejecutable de tu sesión.",
                    "target": ruta,
                })
        if len(hallazgos) >= MAX_HALLAZGOS:
            truncado = True
            break
    if truncado:
        hallazgos.append({
            "name": "Paseo de permisos detenido por el tope",
            "desc": f"Se revisaron {revisados} scripts en {PRESUPUESTO_S:.0f} s y había más; el puente corta a propósito "
                    "para no congelar el equipo. Ejecuta la auditoría otra vez para continuar.",
            "target": str(raiz),
        })
    return hallazgos


# Orden del escaneo: cada paso se reporta ANTES de ejecutarse, así el HUD avanza
# aunque un paso tarde (auditoría real, no animación).
PASOS = [
    ("autostart", "claves de arranque del usuario", paso_autostart),
    ("procesos", "procesos en ejecución con ruta de binario", paso_procesos),
    ("archivos", "dobles extensiones y firma de prueba EICAR", paso_archivos),
    ("permisos", "ejecutables escribibles por cualquiera en la sesión", paso_permisos),
]


def firmas_sospechosas():
    """Corrida completa (se usa en pruebas de consola). No borra ni bloquea nada."""
    d = time.time()
    h = []
    for _, _, fn in PASOS:
        h += fn()
    return h, [(c, n) for c, n, _ in PASOS], round(time.time() - d, 2)


# ------------------------------------------------------------------ jarvis os
JARVIS_OS_PUERTO = int(os.environ.get("CORT_JARVIS_OS_PUERTO", "3000"))


def jarvis_os_vivo(puerto=JARVIS_OS_PUERTO):
    """Solo mira si algo escucha en 127.0.0.1:3000. No instala ni toca el disco."""
    try:
        with socket.create_connection(("127.0.0.1", puerto), timeout=0.6):
            return True
    except OSError:
        return False


# ------------------------------------------------------- intenciones locales
def sin_acentos(t):
    """«cómo va el sistema» y «como va el sistema» son la misma pregunta."""
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower())
                   if unicodedata.category(c) != "Mn")


def intentos_locales(texto, estado):
    """Lo que CORT responde con datos REALES aunque Ollama esté apagado.

    Devuelve (respuesta, extras) o None. `extras` son mensajes sueltos que la
    interfaz entiende (weather_panel, av_open...). Cada número sale de /proc,
    de la red o de una medida con marca origen=real: nada se inventa.
    """
    q = sin_acentos(texto)
    tiene = lambda *v: any(x in q for x in v)

    if tiene("que hora", "la hora", "hora es", "hora actual", "dime la hora"):
        return f"Son las {time.strftime('%H:%M')}.", []

    if tiene("que dia", "la fecha", "hoy es", "dia es", "que dia es", "fecha de hoy"):
        # strftime con %A/%B depende del locale del equipo y aquí sale en inglés,
        # así que los nombres se ponen a mano.
        dias = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
        meses = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                 "septiembre", "octubre", "noviembre", "diciembre")
        a = time.localtime()
        return (f"Hoy es {dias[a.tm_wday]}, {a.tm_mday} de {meses[a.tm_mon - 1]} de {a.tm_year} "
                f"y son las {time.strftime('%H:%M')} (reloj del equipo)."), []

    if tiene("clima", "tiempo hace", "temperatura exterior", "lluvia", "llover", "hace frio", "hace calor", "va a llover"):
        w = clima(estado.get("user_city") or "")
        if not w.get("ok"):
            return f"No pude leer el clima real: {w.get('motivo')}", []
        return (f"En {w['ville']}: {w['temperature']} grados, sensación {w['ressenti']}, "
                f"{w['description']}, viento {w['vent']} km/h. Dato tomado de open-meteo hace segundos."
                + (f" {w['aviso']}" if w.get("aviso") else "")), [
            {"type": "weather_panel", "data": w}]

    if tiene("virus", "amenaza", "auditor", "seguridad", "escaneo", "optimiza", "escan", "analisis"):
        return "Empiezo la auditoría real: arranque, procesos, archivos y permisos. No borro nada.", [
            {"type": "av_open"}, {"type": "av-scan"}]

    if tiene("cpu", "ram", "memoria", "disco", "rendimiento", "estado del sistema", "como va el sistema",
               "como esta el equipo", "va el equipo", "estado del equipo", "como va todo"):
        cpu_ram_disco()             # primera muestra: marca el punto de partida
        time.sleep(0.6)             # sin intervalo no hay porcentaje real que dar
        m = cpu_ram_disco()
        return (f"Medido ahora mismo: CPU al {m['cpu']} %, RAM usada {m['ram']} % de {m['ram_total_mb']} MB "
                f"({m['ram_disponible_mb']} MB libres), disco al {m['disco_pct']} % en {m['nucleos']} núcleos. "
                "Con esta memoria no puedo cargar un modelo grande; el puente lo bloquea para no congelarte."), []

    if tiene("ollama", "modelo", "cerebro", "descarga", "instala"):
        vivo, modelos = ollama_vivo()
        disco = inventario_disco()
        total_mb = cpu_ram_disco().get("ram_total_mb", 0)
        if vivo:
            return (f"Ollama está vivo en 127.0.0.1:11434 con {len(modelos)} modelo(s): "
                    f"{', '.join(sorted(modelos)) or 'ninguno cargado'}. "
                    f"En disco hay {len(disco)}: {', '.join(sorted(disco)) or 'ninguno'}."), []
        if disco:
            los_chicos = sorted(disco, key=lambda k: disco[k]["ram_est"])[:2]
            return (f"Ollama está apagado y hay {ram_disponible_mb()} MB libres de {total_mb}. "
                    f"Pero no hace falta descargar nada: en tu disco ya hay {len(disco)} modelos "
                    f"({', '.join(sorted(disco))}). El más ligero, {los_chicos[0]}, pide ~"
                    f"{disco[los_chicos[0]]['ram_est']} MB libres, que es una estimación sobre su peso medido. "
                    "Cierra navegador y editor y lo cargo en el turno de noche."), []
        return (f"Ollama no responde y no hay ningún modelo en disco; hay {ram_disponible_mb()} MB libres "
                f"de {total_mb}. Descargar solo necesita disco; cargar el modelo necesita memoria, "
                "y ahora no cabe ninguno."), []

    if tiene("jarvis os", "sistema operativo"):
        v = jarvis_os_vivo()
        if v:
            return f"Jarvis OS está escuchando en el puerto {JARVIS_OS_PUERTO}.", []
        return ("Jarvis OS no está instalado en este equipo, y no voy a instalarlo: pide el disco entero de tu "
                "Canaima y borraría MX Linux. Si algún día lo quieres, primero hacemos respaldo completo."), []

    if tiene("quien eres", "que eres", "tu nombre", "presentate"):
        return ("Soy CORT: Cognitiva, Omnipresente, Rapsodia, Terminal. Corro en local en tu equipo y digo "
                "siempre si un dato es real o simulado."), []

    return None


# ------------------------------------------------------------------ chat
def cerebro(prompt, historial, estado):
    vivo, modelos = ollama_vivo()
    if not vivo:
        # Antes de rendirse, intenta levantar el servidor con su propia puerta de
        # RAM: si no cabe, ollama_arrancar() dice el número y no congel nada.
        ok, detalle = ollama_arrancar()
        if ok:
            for _ in range(12):
                time.sleep(1.5)
                vivo, modelos = ollama_vivo()
                if vivo:
                    break
        if not vivo:
            return {"ok": False, "texto": None,
                    "motivo": (f"Ollama no responde en 127.0.0.1:11434 y tampoco lo pude levantar: {detalle}. "
                               "Sin cerebro local no contesto con el modelo; puedo seguir con las funciones "
                               "locales (clima, sistema, auditoría).")}
    modelo = estado.get("local_model") or estado.get("model") or ""
    libre = ram_disponible_mb()
    if modelo:
        falta, como = presupuesto_del_modelo(modelo)
        if libre < falta:
            chicos = sorted(inventario_disco(), key=lambda k: inventario_disco()[k]["ram_est"])
            mejor = chicos[0] if chicos else "ninguno en disco"
            return {"ok": False, "texto": None,
                    "motivo": (f"{modelo} pide ~{falta} MB libres ({como}) y ahora hay {libre}. "
                               "Está descargado, pero no cabe en la memoria: cierra cosas o usa el más chico "
                               f"que tienes en disco ({mejor}).")}
    if not modelo:
        instalado = list(modelos) or sorted(inventario_disco())
        if not instalado:
            return {"ok": False, "texto": None, "motivo": "no hay ningún modelo descargado; elige uno en Ajustes > Cerebro local"}
        modelo = min(instalado, key=lambda m: presupuesto_del_modelo(m)[0])
    nombre = estado.get("user_name") or "Sandra"
    sistema = (
        "Eres CORT: asistente personal de " + nombre + ". Respondes en español neutro, corto, "
        "sin listas salvo que se pidan. Si no sabes un dato, lo dices; no lo inventas. "
        "Horario local y sistema: Linux."
    )
    mensajes = [{"role": "system", "content": sistema}] + historial[-8:] + [
        {"role": "user", "content": prompt}
    ]
    ok, r = http_json(
        f"{OLLAMA}/api/chat",
        {"model": modelo, "messages": mensajes, "stream": False},
        timeout=int(os.environ.get("CORT_CHAT_TIMEOUT", "180")),
    )
    if not ok:
        return {"ok": False, "texto": None, "motivo": f"el modelo no respondió: {r}"}
    texto = (r.get("message") or {}).get("content") if isinstance(r, dict) else None
    return {"ok": bool(texto), "texto": texto, "modelo": modelo, "origen": "real"}


# --------------------------------------------------------------------- WS
CONEXIONES = set()
PULANDO = {}
CANCELADOS = set()   # conexiones cuyo escaneo pidió cancelar la interfaz
ESCANEANDO = set()   # conexiones con un escaneo en curso (no se duplican)


async def ws_handler(request):
    ws = web.WebSocketResponse(heartbeat=25)
    await ws.prepare(request)
    CONEXIONES.add(ws)
    print(f"[CORT] interfaz conectada ({len(CONEXIONES)} sesión/es)")
    historial = []

    await ws.send_json({"type": "connected", "origen": "real", "puente": "cort-bridge v0"})
    await ws.send_json({"type": "system_stats", **cpu_ram_disco()})

    try:
        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue
            try:
                d = json.loads(msg.data)
            except json.JSONDecodeError:
                continue
            t = d.get("type") or d.get("action") or ""

            if t == "system_stats":
                await ws.send_json({"type": "system_stats", **cpu_ram_disco()})

            elif t == "check_ollama_status":
                # En un hilo: lee disco y hace una petición HTTP, y eso no puede
                # congelar el bucle que atiende a las demás conexiones.
                estado = await asyncio.get_event_loop().run_in_executor(None, estado_ollama)
                await ws.send_json({"type": "ollama_status_reply", "status": estado})

            elif t == "start_ollama":
                ok, detalle = ollama_arrancar()
                await ws.send_json({"type": "ollama_start_result", "ok": ok, "detalle": detalle, "origen": "real"})
                if ok:
                    # El servidor tarda un poco en escuchar; dar margen antes de preguntar.
                    await asyncio.sleep(3)
                estado = await asyncio.get_event_loop().run_in_executor(None, estado_ollama)
                await ws.send_json({"type": "ollama_status_reply", "status": estado})

            elif t == "pull_ollama_model":
                modelo = d.get("model") or ""
                info = catalogo().get(modelo, {})
                libre = ram_disponible_mb()
                if PULANDO.get(modelo):
                    await ws.send_json({"type": "ollama_pull_progress", "status": "esa descarga ya está en curso",
                                        "pct": PULANDO[modelo], "done": False, "origen": "real"})
                    continue
                # Si ya está en disco, no se vuelve a bajar: se dice y se explica que
                # lo que falta es memoria, no descarga.
                ya = inventario_disco().get(modelo)
                if ya:
                    await ws.send_json({
                        "type": "ollama_pull_progress", "done": True, "success": True, "pct": 100,
                        "status": (f"{modelo} ya está descargado ({ya['mb']} MB) — no hace falta bajarlo otra vez"),
                        "origen": "real"})
                    await decir(ws, f"{modelo} ya estaba en tu disco, pesa {ya['mb']} MB. Para pensarlo "
                                    f"hacen falta ~{ya['ram_est']} MB libres (estimación sobre su peso medido) "
                                    f"y ahora hay {ram_disponible_mb()}. Con el navegador cerrado lo cargo; "
                                    "para eso está el turno de noche.")
                    continue
                # Puerta de DESCARGA: disco y RAM del servidor. La RAM de CARGA se
                # comprueba al chatear, que es donde hace falta.
                falta_disco = info.get("mb", 700) + MARGEN_DISCO
                libre_disco_mb = shutil.disk_usage("/").free // (1024 * 1024)
                if libre_disco_mb < falta_disco:
                    await ws.send_json({
                        "type": "ollama_pull_progress", "done": True, "success": False, "pct": 0,
                        "status": (f"Disco insuficiente: {libre_disco_mb} MB libres, hacen falta {falta_disco} MB "
                                   f"para {modelo} ({info.get('tam', 'tamano sin medir')})."),
                        "origen": "real",
                    })
                    continue
                vivo, _ = ollama_vivo()
                if not vivo:
                    # La puerta de RAM solo aplica si somos nosotros quienes tenemos
                    # que levantar el servidor; si ya está vivo, bajar un modelo es
                    # puro disco y no congelar nada.
                    if libre < RAM_SERVIDOR:
                        await ws.send_json({
                            "type": "ollama_pull_progress", "done": True, "success": False, "pct": 0,
                            "origen": "real",
                            "status": (f"RAM insuficiente para levantar el servidor: {libre} MB libres, "
                                       f"hacen falta {RAM_SERVIDOR} MB. Cierra pestañas y vuelve a pedirlo."),
                        })
                        continue
                    ok_arranque, detalle = ollama_arrancar()
                    if not ok_arranque:
                        await ws.send_json({"type": "ollama_pull_progress", "done": True, "success": False,
                                            "pct": 0, "status": detalle, "origen": "real"})
                        continue
                    await ws.send_json({"type": "ollama_pull_progress", "done": False, "pct": 0,
                                        "status": f"Arrancando Ollama: {detalle}", "origen": "real"})
                    for _ in range(20):
                        await asyncio.sleep(1)
                        vivo, _ = ollama_vivo()
                        if vivo:
                            break
                    if not vivo:
                        await ws.send_json({"type": "ollama_pull_progress", "done": True, "success": False,
                                            "pct": 0, "origen": "real",
                                            "status": "Ollama no llegó a responder en 20 s; mira /tmp/cort-ollama.log"})
                        continue
                asyncio.create_task(pull(modelo, ws))

            elif t == "set_local_model":
                modelo_elegido = d.get("model", "")
                e = leer_estado(); e["local_model"] = modelo_elegido
                escribir_estado(e)
                vivo, cargados = ollama_vivo()
                disco = inventario_disco()
                datos = disco.get(modelo_elegido) or {}
                if modelo_elegido and not datos and modelo_elegido not in cargados:
                    mb = (MODELOS.get(modelo_elegido) or {}).get("mb", 700)
                    aviso = (f"{modelo_elegido} no está en el disco ni cargado: hay que descargarlo antes "
                             f"(~{mb} MB de disco).")
                elif datos:
                    aviso = (f"{modelo_elegido} está en disco, pesa {datos['mb']} MB. Para pensarlo hacen falta "
                             f"~{datos['ram_est']} MB libres (estimación sobre el peso medido) y ahora hay "
                             f"{ram_disponible_mb()}.")
                else:
                    aviso = f"{modelo_elegido} elegido; está cargado en el servidor."
                await ws.send_json({"type": "local_model_set", "model": modelo_elegido,
                                    "aviso": aviso, "origen": "real"})
                await decir(ws, aviso)

            elif t in ("settings-save", "settings_save"):
                e = leer_estado()
                for k, v in (d.get("settings") or d).items():
                    if isinstance(v, (str, int, float, bool, list, dict)) and k not in ("type", "action"):
                        e[k] = v
                escribir_estado(e)
                await ws.send_json({"type": "settings_saved", "origen": "real"})

            elif t == "weather":
                ciudad = d.get("city") or leer_estado().get("user_city") or ""
                w = await asyncio.get_event_loop().run_in_executor(None, clima, ciudad)
                await ws.send_json({"type": "weather_panel", "data": w})

            elif t in ("av-scan", "run_security_scan", "security_scan", "av_scan_start"):
                if ws in ESCANEANDO:
                    # La interfaz pide el escaneo dos veces (abre el panel y además
                    # dispara su propio botón): el segundo se ignora para no duplicar
                    # cada línea del registro.
                    await ws.send_json({"type": "av_progress", "percent": 50, "step": "curso",
                                        "message": "La auditoría ya está en curso", "origen": "real"})
                    continue
                CANCELADOS.discard(ws)
                asyncio.create_task(escaneo(ws))

            elif t == "av_scan_cancel":
                CANCELADOS.add(ws)
                await ws.send_json({"type": "av_cancel", "origen": "real"})

            elif t == "av_threat_action":
                # Regla dura: CORT informa, no borra ni mata procesos por su cuenta.
                await ws.send_json({
                    "type": "av_action_result", "ok": False,
                    "message": "No voy a borrar ni bloquear «" + str((d.get("threat") or {}).get("name", "?")) +
                               "». Un falso positivo cuesta más que una amenaza visible: dime tú qué hacer.",
                    "origen": "real",
                })

            elif t == "get_agent_models":
                installed = sorted(catalogo())
                await ws.send_json({"type": "agent_models_info",
                                    "data": {"available_models": {a: installed for a in ("principal", "rapido", "seguro")}},
                                    "origen": "real"})

            elif t == "set_agent_models":
                e = leer_estado(); e["agent_models"] = d.get("models") or {}
                escribir_estado(e)
                await ws.send_json({"type": "agent_models_saved", "origen": "real"})

            elif t == "check_jarvis_os_status":
                vivo = await asyncio.get_event_loop().run_in_executor(None, jarvis_os_vivo)
                await ws.send_json({"type": "jarvis_os_status_reply", "installed": vivo,
                                    "port": JARVIS_OS_PUERTO,
                                    "motivo": None if vivo else "nada escuchando en 127.0.0.1:%d" % JARVIS_OS_PUERTO,
                                    "origen": "real"})

            elif t.startswith("jarvis_os_"):
                # Se responde con honestidad en vez de dejar el panel colgado: instalar
                # un SO entero en una Canaima de 1,8 GiB significaría borrar su disco.
                await ws.send_json({"type": "jarvis_os_install_progress", "done": True, "progress": 0,
                                    "status": "Detenido a propósito por CORT",
                                    "log": ("Jarvis OS necesita el disco completo; en este equipo (2 núcleos, "
                                            "1851 MB) sustituiría tu MX Linux. No lo instalo sin tu orden explícita "
                                            "y un respaldo previo.\n"),
                                    "origen": "real"})

            elif t == "location_update":
                e = leer_estado()
                for k in ("lat", "lon", "city"):
                    if k in d:
                        e[k] = d[k]
                escribir_estado(e)

            elif t == "user_input":
                texto = (d.get("text") or "").strip()
                if not texto:
                    continue
                await ws.send_json({"state": "thinking"})
                estado = leer_estado()
                local = await asyncio.get_event_loop().run_in_executor(None, intentos_locales, texto, estado)
                if local:
                    respuesta, extras = local
                    for m in extras:
                        if m.get("type") == "av-scan":
                            asyncio.create_task(escaneo(ws))
                        else:
                            await ws.send_json({**m, "action": m.get("type")})
                    historial.append({"role": "user", "content": texto})
                    historial.append({"role": "assistant", "content": respuesta})
                    await decir(ws, respuesta)
                    await ws.send_json({"type": "brain_used", "modelo": "reglas locales + datos del sistema",
                                        "origen": "real"})
                    continue
                r = await asyncio.get_event_loop().run_in_executor(None, cerebro, texto, historial, estado)
                if r["ok"]:
                    historial.append({"role": "user", "content": texto})
                    historial.append({"role": "assistant", "content": r["texto"]})
                    await decir(ws, r["texto"])
                    await ws.send_json({"type": "brain_used", "modelo": r.get("modelo"), "origen": "real"})
                else:
                    await decir(ws, "Sin cerebro local: " + r["motivo"])
    finally:
        CONEXIONES.discard(ws)
        print("[CORT] interfaz desconectada")
    return ws


async def decir(ws, texto):
    """Respuesta visible en el HUD: la app enseña subtítulos con live_subtitles."""
    ident = "cort-%d" % int(time.time() * 1000)
    await ws.send_json({"state": "speaking"})
    await ws.send_json({"type": "user_speech", "text": ""})
    trozos = [texto[i:i + 26] for i in range(0, len(texto), 26)] or [texto]
    await ws.send_json({"type": "live_subtitles", "id": ident, "phase": "start"})
    for k, trozo in enumerate(trozos):
        await ws.send_json({"type": "live_subtitles", "id": ident, "phase": "delta", "text": trozo + " "})
        await asyncio.sleep(0.05)
    await ws.send_json({"type": "live_subtitles", "id": ident, "phase": "end"})
    await ws.send_json({"type": "jarvis_text", "text": texto, "origen": "real"})
    await asyncio.sleep(max(1.2, len(texto) * 0.03))
    await ws.send_json({"state": "idle"})


async def pull(modelo, ws):
    """Descarga real con progreso real, leyendo el stream NDJSON de Ollama."""
    PULANDO[modelo] = 0
    try:
        datos = json.dumps({"name": modelo, "insecure": False}).encode()
        req = urlreq.Request(f"{OLLAMA}/api/pull", data=datos, headers={"Content-Type": "application/json"})
        ultimo = 0.0
        with urlreq.urlopen(req, timeout=60 * 60) as r:
            for linea in r:
                if not linea.strip():
                    continue
                try:
                    j = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                if j.get("error"):
                    await ws.send_json({"type": "ollama_pull_progress", "done": True, "success": False,
                                        "status": j["error"], "origen": "real"})
                    return
                tot, done = j.get("total") or 0, j.get("completed") or 0
                pct = int(ultimo) if not tot else max(int(ultimo), int(100 * done / tot))
                ultimo = pct
                estado_txt = j.get("status", "")
                if estado_txt.lower() in ("success", ""):
                    # La última línea del stream dice "success" sin contadores: si se
                    # manda tal cual, la barra de la interfaz vuelve al 0 % en inglés.
                    continue
                if tot:
                    estado_txt = f"{estado_txt} — {done/1e6:.0f} / {tot/1e6:.0f} MB"
                await ws.send_json({"type": "ollama_pull_progress", "status": estado_txt,
                                    "pct": pct, "done": False, "origen": "real"})
        vivo, modelos = ollama_vivo()
        recien = inventario_disco(fuerzo=True)   # el archivo nuevo no puede taparlo la caché
        if modelo in modelos or modelo in recien or any(k.startswith(modelo.split(":")[0]) for k in modelos):
            await ws.send_json({"type": "ollama_pull_progress", "done": True, "success": True, "pct": 100,
                                "status": f"{modelo} instalado", "origen": "real"})
            await decir(ws, f"Modelo {modelo} descargado y listo. Ya puedo pensar con él.")
        else:
            await ws.send_json({"type": "ollama_pull_progress", "done": True, "success": False,
                                "status": "la descarga terminó pero el modelo no aparece en la lista",
                                "origen": "real"})
    except Exception as e:
        await ws.send_json({"type": "ollama_pull_progress", "done": True, "success": False,
                            "status": f"descarga interrumpida: {e}", "origen": "real"})
    finally:
        PULANDO.pop(modelo, None)


async def escaneo(ws):
    """Auditoría por pasos: se avisa antes de cada comprobación y se envían los
    hallazgos de ese paso, de modo que el globo y la barra avanzan con datos reales."""
    d = time.time()
    ESCANEANDO.add(ws)
    try:
        await ws.send_json({"type": "av_start", "message": "Auditoría de seguridad local", "origen": "real"})
        total = len(PASOS) + 1
        hallazgos = []
        for i, (clave, nombre, fn) in enumerate(PASOS, start=1):
            await ws.send_json({"type": "av_progress", "percent": int(100 * i / total),
                                "step": clave, "message": f"Comprobando {nombre}",
                                "threats_found": len(hallazgos), "origen": "real"})
            if ws in CANCELADOS:
                CANCELADOS.discard(ws)
                await ws.send_json({"type": "av_cancel", "origen": "real"})
                return
            nuevo_ = await asyncio.get_event_loop().run_in_executor(None, fn)
            hallazgos += nuevo_
            for h in nuevo_:
                await ws.send_json({"type": "av_threat_detected", "threat": h, "origen": "real"})
        dur = round(time.time() - d, 2)
        await ws.send_json({"type": "av_progress", "percent": 100, "step": "fin",
                            "message": f"{len(hallazgos)} hallazgo(s) en {dur} s",
                            "threats_found": len(hallazgos), "origen": "real"})
        # La interfaz solo entra en su rama de amenazas si status vale "infected" y
        # lee el conteo en `threats`; con otro nombre muestra "sin amenazas" encima
        # de un registro con hallazgos (así se detectó midiéndolo).
        await ws.send_json({"type": "av_complete",
                            "status": "ok" if not hallazgos else "infected",
                            "threats": hallazgos, "hallazgos": len(hallazgos),
                            "threats_found": len(hallazgos), "segundos": dur, "origen": "real"})
        await decir(ws, (f"Auditoría terminada en {dur} segundos: sin hallazgos. No borro ni bloqueo nada; informo."
                         if not hallazgos else
                         f"Auditoría terminada en {dur} segundos: {len(hallazgos)} cosas que deberías mirar."))
    finally:
        ESCANEANDO.discard(ws)


async def latido():
    """Empuja estadísticas reales cada 4 s a la interfaz conectada."""
    while True:
        datos = {"type": "system_stats", **cpu_ram_disco()}
        for ws in list(CONEXIONES):
            try:
                await ws.send_json(datos)
            except Exception:
                CONEXIONES.discard(ws)
        await asyncio.sleep(4)


async def main():
    app_ws = web.Application()
    app_ws.router.add_get("/ws", ws_handler)
    app_ws.router.add_get("/", ws_handler)

    app_web = web.Application()
    app_web.router.add_get("/", lambda r: web.FileResponse(BASE / "index.html"))
    app_web.router.add_static("/", BASE, show_index=False, follow_symlinks=True)

    print(f"[CORT] interfaz  http://127.0.0.1:{PUERTO_WEB}/index.html")
    print(f"[CORT] websocket ws://127.0.0.1:{PUERTO_WS}/ws")
    print(f"[CORT] RAM disponible ahora: {ram_disponible_mb()} MB · núcleos {os.cpu_count()}")
    vivo, modelos = ollama_vivo()
    disco = inventario_disco()
    print(f"[CORT] Ollama: {'vivo' if vivo else 'apagado'} · cargados: {list(modelos) or 'ninguno'}")
    if disco:
        los_chicos = sorted(disco, key=lambda k: disco[k]["ram_est"])
        print(f"[CORT] en disco: {len(disco)} modelo(s) — " +
              ", ".join(f"{n} ({disco[n]['mb']} MB, pide ~{disco[n]['ram_est']})" for n in los_chicos))
    else:
        print("[CORT] en disco: ninguno (~/.ollama/models vacío o ilegible)")

    runner_ws = web.AppRunner(app_ws)
    runner_web = web.AppRunner(app_web)
    await runner_ws.setup(); await runner_web.setup()
    await web.TCPSite(runner_ws, "127.0.0.1", PUERTO_WS).start()
    await web.TCPSite(runner_web, "127.0.0.1", PUERTO_WEB).start()
    asyncio.create_task(latido())
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[CORT] puente detenido")
