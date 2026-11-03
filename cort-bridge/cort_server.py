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
import base64
import json
import os
import re
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

# --------------------------------------------------------------- voz (fase F3)
# El módulo vive al lado del puente y trae lo medido (motores, dispositivos,
# factores). Se importa con ruta explícita porque el puente puede arrancarse desde
# cualquier carpeta con systemd --user, y ahí el directorio actual no es el repo.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import cort_voz
except Exception as _e_voz:                 # sin venv el puente sigue valiendo; la voz avisa
    cort_voz = None
    VOZ_ERROR = f"{type(_e_voz).__name__}: {_e_voz}"
else:
    VOZ_ERROR = ""

# Capa de acción nativa (F5). Solo usa la biblioteca estándar, así que si la voz
# no está disponible, las manos del equipo sí lo están.
try:
    import cort_acciones
except Exception as _e_acc:
    cort_acciones = None
    ACCIONES_ERROR = f"{type(_e_acc).__name__}: {_e_acc}"
else:
    ACCIONES_ERROR = ""

# Vida diaria (F4): lista de compras, notas, recordatorios y temporizadores.
# Biblioteca estándar sola; si la voz o las manos fallan, esto sigue en pie.
try:
    import cort_vida
except Exception as _e_vida:
    cort_vida = None
    VIDA_ERROR = f"{type(_e_vida).__name__}: {_e_vida}"
else:
    VIDA_ERROR = ""

# La reja del núcleo (F9): recibe el plan que propuso el modelo y decide si puede
# ejecutarse. Si este módulo no carga, el puente sigue con todo lo demás pero NINGÚN
# plan llega al disco: sin reja no hay manos, y eso es exactamente el punto.
try:
    import cort_intenciones
except Exception as _e_reja:
    cort_intenciones = None
    REJA_ERROR = f"{type(_e_reja).__name__}: {_e_reja}"
else:
    REJA_ERROR = ""

# U1: el canal de actualización. Si no carga, CORT simplemente no avisa de versiones.
try:
    import cort_actualiza
except Exception:
    cort_actualiza = None

VOZ_ACTIVA = os.environ.get("CORT_VOZ", "1") == "1"   # hablar en voz alta con cada respuesta
MICRO_ACTIVO = os.environ.get("CORT_MIC", "0") == "1"  # el micro sigue apagado hasta que se pida
MIC = None                                          # cort_voz.EscuchaContinua, uno solo
BUCLE = None                                        # el lazo de asyncio, para avisos desde hilos
ALMENOS_AUDIO = 200                                 # MB libres mínimos para cargar Vosk

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


NAVEGADORES = ("firefox", "chromium", "chrome", "brave", "epiphany", "midori", "tor browser")


def _rebanada(original, q, m, grupo=1):
    """El trozo de texto ORIGINAL que corresponde al match hecho sobre `q`."""
    if not m:
        return ""
    if not original or original == q:
        return (m.group(grupo) or "").strip()
    mapa = []
    for i, ch in enumerate(original):
        for c in unicodedata.normalize("NFD", ch.lower()):
            if unicodedata.category(c) != "Mn":
                mapa.append(i)
    mapa.append(len(original))
    try:
        return original[mapa[m.start(grupo)]:mapa[m.end(grupo)]].strip()
    except Exception:
        return (m.group(grupo) or "").strip()


def _objetivo_despues(q, *verbos, original=None):
    """«abre el vlc» -> 'vlc'. Quita artículo, cortesía y la palabra ventana.

    Sin esto, «cierra la ventana vlc» buscaba una ventana llamada «ventana vlc» y
    no encontraba ninguna: el sustantivo del medio hay que tirarlo.
    """
    for v in verbos:
        m = re.search(r"\b" + v + r"\s+(?:el|la|los|las|un|una|mi|por)?\s*([a-z0-9 ._\-]{2,40})", q)
        if m:
            objetivo = m.group(1).strip()
            for sobra in ("por favor", "ahora", "enseguida", "inmediatamente", "favor"):
                objetivo = objetivo.replace(sobra, "").strip()
            objetivo = re.sub(r"^(ventana|ventanas|app|aplicacion|aplicaciones|programa|archivo)\s+",
                              "", objetivo).strip()
            if objetivo:
                if original:
                    m2 = re.search(r"\b" + v + r"\s+(?:el|la|los|las|un|una|mi|por)?\s*([a-z0-9 ._\-]{2,40})", q)
                    cortado = _rebanada(original, q, m2)
                    for sobra in ("por favor", "ahora", "enseguida", "inmediatamente", "favor"):
                        cortado = cortado.replace(sobra, "").strip()
                    cortado = re.sub(r"^(ventana|ventanas|app|aplicacion|aplicaciones|programa|archivo)\s+",
                                     "", cortado, flags=re.I).strip()
                    if cortado:
                        return cortado
                return objetivo
    return ""


def accion_desde_frase(q, original=None):
    """Traduce una frase a una acción real de Linux y la ejecuta.

    Devuelve (texto, extras) o None si la frase no pide tocar nada. Aquí es donde
    CORT deja de ser un chat: cada rama llama a cort_acciones, que ejecuta con
    lista de argumentos (jamás con shell) y responde con `origen`.
    """
    if cort_acciones is None:
        return None
    o = original or q        # lo escrito por la usuaria, con sus tildes: eso es lo que se guarda
    tiene = lambda *v: any(x in q for x in v)
    r = None

    # confirmación por escrito de lo peligroso (apagar / reiniciar)
    if tiene("confirmar apagar", "apagar confirmado", "confirmar reiniciar", "reiniciar confirmado"):
        que = "apagar" if "apagar" in q else "reiniciar"
        r = cort_acciones.energia(que, confirmar=True)
        return (f"Hecho: {r['detalle']}.", [])

    if tiene("sube el volumen", "subir volumen", "mas volumen", "sube volumen", "mas fuerte"):
        r = cort_acciones.cambiar_volumen(paso=+10)
    elif tiene("baja el volumen", "bajar volumen", "menos volumen", "baja volumen", "mas bajo"):
        r = cort_acciones.cambiar_volumen(paso=-10)
    elif tiene("volumen al ", "pon el volumen", "volumen a "):
        m = re.search(r"(\d{1,3})\s*%?", q)
        r = cort_acciones.cambiar_volumen(destino=int(m.group(1)) if m else 50)
    elif tiene("silencio", "deja el sonido", "calla el equipo", "mute"):
        r = cort_acciones.cambiar_volumen(mudo=True)
    elif tiene("quita el silencio", "devuelve el sonido"):
        r = cort_acciones.cambiar_volumen(mudo=False)
    elif tiene("sube el brillo", "mas brillo"):
        r = cort_acciones.cambiar_brillo(paso=+10)
    elif tiene("baja el brillo", "menos brillo"):
        r = cort_acciones.cambiar_brillo(paso=-10)
    elif tiene("ventanas abiertas", "que ventanas", "que hay abierto", "lista de ventanas"):
        vs = cort_acciones.ventanas()
        titulos = ", ".join(v["titulo"].replace("Sandra ", "")[:30] for v in vs[:8])
        return (f"Hay {len(vs)} ventanas abiertas: {titulos or 'ninguna'}.", [])
    elif tiene("cierra la ventana", "cierra ventana", "cerrar ventana"):
        r = cort_acciones.cerrar_ventana(_objetivo_despues(q, "cierra", "cerrar"))
    elif tiene("minimiza", "esconde la ventana"):
        r = cort_acciones.minimizar_ventana(_objetivo_despues(q, "minimiza", "esconde"))
    elif tiene("al frente", "enfoca", "trae la ventana"):
        r = cort_acciones.enfocar_ventana(_objetivo_despues(q, "enfoca", "trae"))
    elif tiene("captura de pantalla", "pantallazo", "haz una captura", "captura pantalla"):
        r = cort_acciones.captura_pantalla()
    elif tiene("pausa la musica", "pausa el video", "pausa el audio", "pon pausa"):
        r = cort_acciones.tecla_media("pause")
    elif tiene("reanuda", "sigue la musica", "play de nuevo"):
        r = cort_acciones.tecla_media("play")
    elif tiene("siguiente cancion", "tema siguiente", "pasa a la siguiente"):
        r = cort_acciones.tecla_media("next")
    elif tiene("bloquea la pantalla", "bloqueo de pantalla", "pon la pantalla en bloqueo"):
        r = cort_acciones.energia("bloquear")
    elif tiene("apaga el equipo", "apaga la laptop", "apaga todo", "reinicia el equipo",
               "reinicia la laptop"):
        que = "reiniciar" if "reinicia" in q else "apagar"
        r = cort_acciones.energia(que)          # sin confirmar: responde pidiendo confirmación
    elif tiene("actualizaciones disponibles", "que se puede actualizar", "paquetes pendientes"):
        r = cort_acciones.actualizaciones()
    elif tiene("fondo de pantalla", "que fondo"):
        r = cort_acciones.fondo_escritorio()
    elif tiene("notifica en pantalla", "avisame en pantalla", "muestra una notificacion"):
        texto = _objetivo_despues(q, "notifica", "avisame", "muestra") or "CORT está listo"
        r = cort_acciones.notificar(texto)
    # ------------------------------------------------------------- vida (F4) ----
    elif cort_vida and tiene("comprame", "anota en la lista", "agrega a la lista", "papela",
               "pon en la lista", "apunta en la compra"):
        m2 = re.search(r"comprame(?:me)?\s+(.{2,160})", q)
        qu = _rebanada(o, q, m2) if m2 else ""
        if not qu:
            m2 = re.search(r"(?:lista|compra)[^a-z]{0,12}(.{2,160})", q)
            qu = _rebanada(o, q, m2)
        r = cort_vida.comprar(qu) if qu else {"ok": False, "motivo": "no dice qué comprar"}
    elif cort_vida and ((re.search(r"\b(?:quita|quitame|tacha|tachame|borra|saca)\w*\b", q) and
                         re.search(r"\b(?:lista|compra|papela)\b", q)) or
                        re.search(r"\bya\b.*\bcompre\b", q)):
        qu = _objetivo_despues(q, "quita", "quitame", "tacha", "tachame", "borra", "saca",
                               original=o) or o
        qu = re.sub(r"^ya\s+(?:he\s+)?compre\s+", "", qu)
        # el nombre del medio ("de la lista", "en la compra") se tira por donde esté
        qu = re.sub(r"\b(?:de|en|a|para)?\s*(?:la|el|mi|nuestra)?\s*(?:lista|compra|papela)\b", " ", qu)
        qu = re.sub(r"\s+", " ", qu).strip()
        qu = re.sub(r"^(?:de|el|la|los|las|un|una|mi)\s+", "", qu)
        r = cort_vida.quitar_compra(qu or "nada")
    elif cort_vida and tiene("vacia la lista", "termino la lista"):
        r = cort_vida.vaciar_compras()
    elif cort_vida and tiene("que tengo que comprar", "lista de compras", "que falta comprar", "lee la lista"):
        items = cort_vida.compras()
        return ("Tu lista de compras: " + (", ".join(items) if items else "está vacía") + ".",
                [{"type": "shopping_list", "items": items, "origen": "real"}])
    elif cort_vida and tiene("anota que", "apunta que", "nueva nota", "guarda la nota"):
        m = re.search(r"(?:anota|apunta|guarda)(?:\s+la nota)?\s+que\s+(.{3,600})", q)
        cuerpo = _rebanada(o, q, m) if m else o
        titulo = re.split(r"[,.]", cuerpo)[0].strip()[:48] or "nota de cort"
        r = cort_vida.guardar_nota(titulo[:1].upper() + titulo[1:], cuerpo)
        return (f"Nota guardada: «{r.get('titulo','')}» ({r.get('caracteres',0)} caracteres). " +
                (r.get("motivo", "") if not r.get("ok") else ""),
                [{"type": "obsidian_notes", "notes": notas_para_panel(), "origen": "real"}])
    elif cort_vida and tiene("mis notas", "lee mis notas", "que notas tengo"):
        n = cort_vida.notas()
        return (f"Tienes {len(n)} nota(s): " + (", ".join(x["titulo"] for x in n[:8]) or "ninguna") + ".",
                [{"type": "obsidian_notes", "notes": notas_para_panel(), "origen": "real",
                  "nota": "son las notas de CORT; Obsidian no está instalado"}])
    elif cort_vida and (tiene("recuerdame", "recorda me") or tiene("no se me olvide")):
        m = (re.search(r"recuerdame\s+(.{3,200})", q) or
             re.search(r"no se me olvide\s+(.{3,200})", q))
        cuerpo = _rebanada(o, q, m) if m else o
        r = cort_vida.poner_recordatorio(cuerpo, cuando=cuerpo)
        if r.get("ok"):
            return (f"Te lo recuerdo dentro de {r['item']['segundos']} segundos "
                    f"({r['item']['texto']}).",
                    [{"type": "vida_estado", "origen": "real",
                      "pendientes": cort_vida.recordatorios(pendientes=True)}])
        return ("No supe cuándo: " + r.get("motivo", ""), [])
    elif cort_vida and tiene("temporizador", "countdown", "dame una alerta de", "cronometra"):
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*(minutos?|segundos?|horas?)", q)
        seg = cort_vida.segundos_en(q) if m else None
        if not seg:
            return ("Dime la duración en minutos o segundos: «temporizador de 10 minutos».", [])
        r = cort_vida.poner_recordatorio(f"temporizador de {seg} segundos",
                                         cuando=f"{seg} segundos", tipo="temporizador")
        return ((f"Temporizador puesto: {seg} segundos. Te aviso y hablo cuando termine."
                 if r.get("ok") else "No pude ponerlo: " + r.get("motivo", "")),
                [{"type": "timer_add", "duration": seg, "origen": "real"}])
    elif cort_vida and tiene("que tengo pendiente", "que pendientes", "resumen del dia",
               "que tengo anotado", "como va mi dia"):
        return (cort_vida.resumen_hablado(),
                [{"type": "vida_estado", "origen": "real",
                  "datos": cort_vida.disponibilidad(), "compras": cort_vida.compras()}])
    elif cort_vida and tiene("leeme la seleccion", "lee lo que tengo seleccionado", "leeme esto",
               "lee la seleccion"):
        p = cort_acciones.portapapeles(seleccion_primaria=True)
        if not p.get("ok"):
            return ("No hay selección que leer: " + p.get("motivo", ""), [])
        txt = (p.get("texto") or "").strip()
        if not txt:
            return ("No hay texto subrayado que leer: el portapapeles primario está vacío.", [])
        return (txt[:600] + ("…" if len(txt) > 600 else ""),
                [{"type": "vida_estado", "origen": "real", "seleccion_leida": len(txt)}])
    elif tiene("abre ", "abrir ", "lanza ", "ejecuta ", "arranca "):
        objetivo = _objetivo_despues(q, "abre", "abrir", "lanza", "ejecuta", "arranca")
        if not objetivo:
            return None
        if any(n in objetivo for n in ("navegador", "browser")) or objetivo.split()[0] in NAVEGADORES:
            apps = cort_acciones.apps_disponibles()
            elegido = next((a for n in NAVEGADORES for a in apps if n in a["nombre"].lower()), None)
            if not elegido:
                return ("No hay navegador instalado en este equipo: busqué "
                        + ", ".join(NAVEGADORES) + " entre las entradas de escritorio.", [])
            objetivo = elegido["nombre"]
        r = cort_acciones.abrir_aplicacion(objetivo)
    elif tiene("cierra ", "cerrar "):
        r = cort_acciones.cerrar_ventana(_objetivo_despues(q, "cierra", "cerrar"))
    if not r:
        return None
    if "detalle" not in r:
        # Los resultados de vida diaria (F4) traen otros campos: se les traduce el
        # texto aquí y no se registran como acción de la máquina, que no lo son.
        decir = r.get("nota") or r.get("motivo") or (
            "apuntado" if r.get("ok") else "no se pudo")
        return (str(decir) + ("." if not str(decir).endswith((".", "…")) else ""),
                [{"type": "vida_estado", "origen": "real",
                  "datos": cort_vida.disponibilidad(), "compras": cort_vida.compras()}])
    cort_acciones.registrar(r.get("accion"), {"frase": q[:90]}, r)
    extra = (" " + r["nota"]) if r.get("nota") else ""
    if r.get("pide_confirmacion"):
        return (r["detalle"] + " Si de verdad quieres, responde «confirmar " +
                str(r.get("accion", "")) + "».", [])
    return ((r["detalle"] or ("no se pudo: " + str(r.get("motivo", "")))) + extra,
            [{"type": "cort_accion", "accion": r.get("accion"), "ok": r.get("ok"),
              "origen": "real"}])


def intentos_locales(texto, estado):
    """Lo que CORT responde con datos REALES aunque Ollama esté apagado.

    Devuelve (respuesta, extras) o None. `extras` son mensajes sueltos que la
    interfaz entiende (weather_panel, av_open...). Cada número sale de /proc,
    de la red o de una medida con marca origen=real: nada se inventa.
    """
    q = sin_acentos(texto)
    tiene = lambda *v: any(x in q for x in v)
    # Las siglas van con frontera de palabra: "ram" vive dentro de «cómprame», y
    # una lista de la compra contestada con el uso de memoria es un robo de turno.
    dice = lambda *v: any(re.search(r"\b" + x + r"\b", q) for x in v)

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

    if tiene("clima", "tiempo hace", "temperatura exterior", "lluvia", "llover",
             "hace frio", "hace calor", "va a llover", "fuera", "afuera", "el tiempo"):
        w = clima(estado.get("user_city") or "")
        if not w.get("ok"):
            return f"No pude leer el clima real: {w.get('motivo')}", []
        return (f"En {w['ville']}: {w['temperature']} grados, sensación {w['ressenti']}, "
                f"{w['description']}, viento {w['vent']} km/h. Dato tomado de open-meteo hace segundos."
                + (f" {w['aviso']}" if w.get("aviso") else "")), [
            {"type": "weather_panel", "data": w}]

    interior = tiene("temperatura ambiente", "que temperatura", "cual es la temperatura",
                     "temperatura de la sala", "temperatura del equipo", "cuanto marca",
                     "temperatura interior")
    # "qué temperatura hace fuera" es clima, no sensores: si la frase habla de la
    # calle se deja pasar a la regla del clima de arriba.
    if interior and not tiene("fuera", "afuera", "exterior", "calle", "en la ciudad"):
        # No es clima: son los sensores térmicos del kernel. Se dice el nombre del
        # sensor porque en esta laptop no hay sonda de ambiente y confundirlos
        # sería una mentira con número.
        t = temperatura_sala()
        if not t.get("ok"):
            return f"No puedo darte una temperatura real: {t.get('motivo')}", []
        return (f"{t['piece']} a {t['temperature']} grados. {t['aviso']} "
                f"El clima de la calle es otra medida: pregunta por el tiempo."), [
            {"type": "sala_temperatura", "data": t}]

    if tiene("virus", "amenaza", "auditor", "seguridad", "escaneo", "optimiza", "escan", "analisis"):
        return "Empiezo la auditoría real: arranque, procesos, archivos y permisos. No borro nada.", [
            {"type": "av_open"}, {"type": "av-scan"}]

    if dice("cpu", "ram", "memoria", "disco", "rendimiento", "estado del sistema", "como va el sistema",
            "como esta el equipo", "va el equipo", "estado del equipo", "como va todo"):
        cpu_ram_disco()             # primera muestra: marca el punto de partida
        time.sleep(0.6)             # sin intervalo no hay porcentaje real que dar
        m = cpu_ram_disco()
        return (f"Medido ahora mismo: CPU al {m['cpu']} %, RAM usada {m['ram']} % de {m['ram_total_mb']} MB "
                f"({m['ram_disponible_mb']} MB libres), disco al {m['disco_pct']} % en {m['nucleos']} núcleos. "
                "Con esta memoria no puedo cargar un modelo grande; el puente lo bloquea para no congelarte."), []

    if tiene("ollama") or dice("modelo", "modelos", "cerebro", "descarga", "instala"):
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

    # ---- F5: órdenes que tocan el equipo -------------------------------------------
    # Van al final a propósito: primero responden las reglas de lectura (hora, clima,
    # temperatura, cerebro) y sólo si no eran eso se intenta una acción real.
    accion = accion_desde_frase(q, texto)
    if accion:
        return accion

    return None


# ------------------------------------------------------ compilador de intenciones ----
# Fase F9. Lo que falta entre «oí la frase» y «lo hice». El modelo pequeño no comprende,
# predice texto: por eso acá sólo produce una propuesta y `cort_intenciones` decide si es
# ejecutable. Dos puertas antes de llamarlo, porque la experiencia de F3/F4 fue clara:
#   * si Ollama no está vivo, no se levanta para esto: cargar un modelo con la RAM justa
#     es congelar la Canaima a mitad de una frase.
#   * si el modelo elegido no cabe en la RAM medida, se dice el número y se usa la
#     respuesta normal del chat, no se intenta el carga.
# CORT_NUCLEO_FALSO='{"intencion":"listar_archivos",...}' permite probar todo el camino
# sin modelo, igual que la arena de las fases anteriores.
SISTEMA_NUCLEO = (
    "Eres el compilador de intenciones de CORT, un asistente local en Linux. "
    "Recibes una frase hablada, a veces con errores de dictado. Devuelves SOLO un objeto "
    "JSON, sin prosa y sin cercas de markdown, con estas llaves: "
    '"intencion": una de {listar_archivos, mover_archivo, copiar_archivo, crear_carpeta, '
    'reproducir, pausar, siguiente, investigar, playlists_telefono, borrar_archivo, nada}; '
    '"argumentos": un objeto con las rutas o nombres que nombraron (origen, destino, '
    'carpeta, nombre, pista, playlist, tema); '
    '"necesita_confirmacion": true si el usuario pidió sobrescribir o borrar; '
    '"no_entendido": true si la frase no corresponde a ninguna acción. '
    'Nunca inventes rutas: si no nombraron la carpeta, deja el argumento vacío. '
    'Si la frase es un saludo, una pregunta o una charla, responde '
    '{"intencion":"nada","no_entendido":true,"argumentos":{}}.'
)
PENDIENTE: dict = {}                  # el último plan que pidió un sí humano, con su hora
NUCLEO_ON = os.environ.get("CORT_NUCLEO", "1") == "1"


def ollama_cargados():
    """Modelos que YA están en memoria según /api/ps. Si uno está cargado, usarlo no
    cuesta el presupuesto de carga: cobrarlo igual sería una puerta que miente."""
    ok, datos = http_json(f"{OLLAMA}/api/ps", datos={}, timeout=3)
    if not ok or not isinstance(datos, dict):
        return []
    return [m.get("name", "") for m in datos.get("models", []) if isinstance(m, dict)]


def modelo_del_nucleo(estado):
    """El modelo que se usa para compilar, con su puerta de RAM. (nombre|None, motivo)."""
    vivo, modelos = ollama_vivo()
    if not vivo:
        return None, ("Ollama no está levantando ahora mismo; el núcleo no carga un modelo "
                      "por su cuenta para no congelar el equipo.")
    pedido = estado.get("nucleo_model") or estado.get("local_model") or estado.get("model") or ""
    candidatos = list(modelos) or sorted(inventario_disco())
    if not candidatos:
        return None, "no hay ningún modelo descargado; elige uno en Ajustes > Cerebro local"
    elegido = pedido if pedido in candidatos else min(candidatos, key=lambda m: presupuesto_del_modelo(m)[0])
    if elegido not in candidatos:
        return None, f"{pedido} no está en disco; lo que hay es {', '.join(sorted(candidatos))}"
    if elegido not in ollama_cargados():
        falta, como = presupuesto_del_modelo(elegido)
        libre = ram_disponible_mb()
        if libre < falta:
            chicos = sorted(inventario_disco(), key=lambda k: inventario_disco()[k]["ram_est"])
            mejor = chicos[0] if chicos else "ninguno en disco"
            return None, (f"{elegido} pide ~{falta} MB libres ({como}) y hay {libre}: no lo cargo para "
                          f"esto, congelaría la máquina. Cierra cosas o usa el más chico ({mejor}).")
    return elegido, ""


def compilar_intencion(frase, estado):
    """frase hablada -> (plan|None, motivo). No ejecuta absolutamente nada."""
    if cort_intenciones is None:
        return None, "la reja del núcleo no cargó: " + REJA_ERROR
    simulado = os.environ.get("CORT_NUCLEO_FALSO")
    if simulado:
        return cort_intenciones.plan_desde_texto(simulado), "plan simulado por variable de prueba"
    modelo, motivo = modelo_del_nucleo(estado)
    if not modelo:
        return None, motivo
    ok, r = http_json(
        f"{OLLAMA}/api/generate",
        {"model": modelo, "system": SISTEMA_NUCLEO, "prompt": frase, "stream": False,
         "format": "json", "keep_alive": os.environ.get("CORT_KEEP_ALIVE", "2m"),
         "options": {"temperature": 0, "num_ctx": 2048, "num_predict": 180}},
        timeout=int(os.environ.get("CORT_NUCLEO_TIMEOUT", "90")),
    )
    if not ok:
        return None, f"el cerebro no respondió: {r}"
    crudo = (r.get("response") if isinstance(r, dict) else None) or ""
    return cort_intenciones.plan_desde_texto(crudo), crudo[:200]


NOMBRE_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,63}$")


def probar_cerebro(modelo, frase):
    """Un disparo real al modelo, sin ejecutar nada: mide latencia y si la reja
    aceptaría el plan. La puerta de RAM sigue mandando — si el modelo no cabe, se
    dice el número y no se carga, que es como se evita congelar el equipo."""
    if not modelo or not NOMBRE_MODEL.match(modelo):
        return {"ok": False, "motivo": "ese nombre de modelo no es válido"}
    if cort_intenciones is None:
        return {"ok": False, "motivo": "la reja del núcleo no cargó: " + REJA_ERROR}
    vivo, cargados = ollama_vivo()
    if not vivo:
        ok, detalle = ollama_arrancar()
        if not ok:
            return {"ok": False, "motivo": detalle}
        vivo, cargados = ollama_vivo()
        if not vivo:
            return {"ok": False, "motivo": "Ollama sigue sin responder tras intentarlo levantar"}
    if modelo not in cargados:
        falta = presupuesto_del_modelo(modelo)[0]
        libre = ram_disponible_mb()
        if 0 <= libre < falta:
            return {"ok": False,
                    "motivo": f"{modelo} pide ~{falta} MB libres y hay {libre}: no lo cargo "
                              f"para no congelar el equipo. Cierra programas y vuelve a probar."}
    t0 = time.monotonic()
    ok, r = http_json(
        f"{OLLAMA}/api/generate",
        {"model": modelo, "system": SISTEMA_NUCLEO, "prompt": frase, "stream": False,
         "format": "json", "keep_alive": os.environ.get("CORT_KEEP_ALIVE", "2m"),
         "options": {"temperature": 0, "num_ctx": 2048, "num_predict": 180}},
        timeout=int(os.environ.get("CORT_NUCLEO_TIMEOUT", "120")),
    )
    ms = int((time.monotonic() - t0) * 1000)
    if not ok:
        return {"ok": False, "motivo": f"el cerebro no respondió: {r}", "ms": ms}
    crudo = (r.get("response") if isinstance(r, dict) else None) or ""
    plan = cort_intenciones.plan_desde_texto(crudo)
    valido, motivo = (False, "el modelo devolvió prosa en vez de un objeto JSON")
    if plan is not None:
        valido, motivo = cort_intenciones.validar(plan)
    tokens = (r.get("eval_count") or 0) if isinstance(r, dict) else 0
    return {"ok": True, "modelo": modelo, "frase": frase, "ms": ms,
            "tok_s": round(tokens / max(0.4, ms / 1000.0), 1),
            "crudo": crudo[:240], "plan": plan, "valido": valido, "motivo": motivo,
            "origen": "real"}


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

# Salidas: cada conexión tiene su cola y su redactor.
#
# Por qué: antes el lazo de lectura esperaba a que terminar de hablar. Una
# respuesta larga dormía ~9 s (0,05 s por cada trozo de subtítulo más el final) y
# durante ese tiempo CORT no oía ningún botón: la auditoría del informe leyó un
# escaneo como "silencio" por culpa de esto. Con la cola, quien habla se limita a
# dejar mensajes en la bandeja y el lazo de lectura sigue libre.
SALIDA = {}      # ws -> asyncio.Queue de (datos, pausa_antes)
REDACTOR = {}    # ws -> tarea que vacía esa bandeja


def enviar(ws, datos, pausa=0.0):
    """Deja un mensaje en la bandeja de salida de esta conexión.

    Es sincrónico a propósito: pedir algo nunca puede bloquear al que pregunta.
    Si la conexión ya no tiene bandeja (se cerró) se ignora en vez de reventar.
    """
    cola = SALIDA.get(ws)
    if cola is None:
        return False
    try:
        cola.put_nowait((datos, pausa))
        return True
    except Exception:
        return False


async def redactor(ws, cola):
    """Único que escribe en el WebSocket: así no hay dos tareas pisándose."""
    while True:
        try:
            datos, pausa = await cola.get()
        except asyncio.CancelledError:
            break
        if pausa:
            await asyncio.sleep(pausa)
        try:
            if ws.closed:
                break
            await ws.send_json(datos)
        except Exception as e:
            # Pestaña cerrada a media frase: es lo normal al recargar, no es un error
            # que merezca una traza de 15 líneas en el registro.
            print(f"[CORT] conexión caída al escribir ({type(e).__name__}); la retiro")
            break
    CONEXIONES.discard(ws)
    SALIDA.pop(ws, None)
    REDACTOR.pop(ws, None)


async def abrir_canal(ws):
    global MUESTREO
    cola = asyncio.Queue(maxsize=512)
    SALIDA[ws] = cola
    REDACTOR[ws] = asyncio.create_task(redactor(ws, cola))
    # Con la primera pestaña abierta arranca el muestreo por su cuenta; si no, los
    # paneles de clima y temperatura esperarían a que alguien los abriera para tener
    # un número. Una sola tarea para todas las conexiones.
    if MUESTREO is None or MUESTREO.done():
        MUESTREO = asyncio.create_task(latido_clima())
    return cola


async def cerrar_canal(ws):
    tarea = REDACTOR.pop(ws, None)
    SALIDA.pop(ws, None)
    if tarea:
        # Se le da un instante para escribir lo último que quedaba.
        await asyncio.sleep(0.05)
        tarea.cancel()


# ------------------------------------------- qué le falta a cada panel muerto
# El censo del 2026-11-02 (INFORME_FUNCIONES.md) midió 34 órdenes de lectura y sólo
# 6 tenían alguien al otro lado. Estas tablas son la verdad de cada una: si el
# puente no puede, lo dice con el motivo y con lo que haría falta. Nada de
# indicadores de carga eternos.
PANEL_DE_ORDEN = {
    "vpn_get_status": "vpn-panel", "vpn_get_countries": "vpn-panel",
    "vpn_connect": "vpn-panel", "vpn_disconnect": "vpn-panel", "vpn_cancel": "vpn-panel",
    "get_winget_upgrades": "winget-panel", "run_winget_upgrade": "winget-panel",
    "get_installed_programs": "uninstaller-panel", "uninstall_program": "uninstaller-panel",
    "clean_leftovers": "uninstaller-panel",
    "games_get_library": "games-panel", "games_scan": "games-panel", "detect_apps": "games-panel",
    "games_launch": "games-panel", "games_hide": "games-panel", "games_pick_folder": "games-panel",
    "get_desktop_wallpaper": "wallpaper-modal",
    "ha_get_states": "ha-panel", "ha_call_service": "ha-panel", "ha_add_voice_alias": "ha-panel",
    "update_shopping_list": "shopping-panel", "get_shopping_list": "shopping-panel",
    "print3d_check_deps": "print3d-panel", "print3d_check_hardware": "print3d-panel",
    "print3d_generate": "print3d-panel", "print3d_install": "print3d-panel",
    "print3d_generate_lithophane": "print3d-panel", "print3d_open_folder": "print3d-panel",
    "read_obsidian_note": "obsidian-panel", "save_obsidian_note": "obsidian-panel",
    "delete_obsidian_note": "obsidian-panel",
    "get_windy_webcams": "webcam-preview-panel",
    "iptv_open_file": "iptv-panel", "iptv_parse_m3u": "iptv-panel", "iptv_parse_url": "iptv-panel",
    "open_browser": "hud-browser-panel", "close_browser": "hud-browser-panel",
    "get_https_tunnel_status": "", "mobile_auth": "",
    "get_elevenlabs_voices": "settings-modal",
}

# Lo que responde el puente cuando la orden no está en ningún otro sitio.
FALTA_EN_EL_PUENTE = {
    "vpn_get_status": ("El puente no levanta ninguna VPN.",
                       "hace falta un cliente (ProtonVPN o WireGuard) y tú decides cuál; ahora no hay ninguno configurado"),
    "vpn_get_countries": ("La lista de países la daba el backend de la demo, que ya no existe.",
                          "misma razón: sin cliente VPN no hay países que listar"),
    "ha_get_states": ("No hay servidor Home Assistant en tu red, así que no hay sensores que leer.",
                      "hace falta la IP y el token de un Home Assistant; sin eso el panel está vacío por verdad, no por fallo"),
    "get_windy_webcams": ("Las cámaras de Windy piden una clave gratuita de su API.",
                          "con clave en Ajustes esto funciona; sin clave no se inventa nada"),
    "get_elevenlabs_voices": ("Las voces de ElevenLabs son de pago y piden clave.",
                              "no tienes tarjeta: desde F3 CORT habla con Piper/espeak-ng aquí dentro"),
    "claude_code_status": ("Claude Code no está instalado ni autenticado en este equipo.",
                           "node sí está (/usr/bin/node), pero pide cuenta y clave: no entra sin tu autorización"),
    "print3d_check_hardware": ("El puente no detecta ninguna impresora 3D conectada.",
                               "haría caso si algún día la conectas; no se finge un hardware"),
    "get_https_tunnel_status": ("Túnel HTTPS: no se abre ningún agujero al exterior sin tu orden explícita.",
                                "el teléfono se enlaza por red local con token (F7), sin exponer nada a internet"),
    "mobile_auth": ("El emparejamiento con el teléfono aún no existe.",
                    "se hace en F7 por Wi-Fi local con QR generado aquí, no con api.qrserver.com"),
    "clear_cache": ("El puente no guarda cachas propias que limpiar todavía (solo 20 s de inventario en memoria).",
                    "se dirá con cifras cuando exista algo que limpiar"),
}

RAZON_GENERICA = ("Nadie atiende esta orden en el puente: la plantilla la mandaba a su backend de Windows.",
                  "está anotada en PLAN_FASES.md y se decide en la fase que corresponda")


def aviso_sin_backend(orden, extra=""):
    """Mensaje honesto para una orden que el puente no puede cumplir."""
    panel = PANEL_DE_ORDEN.get(orden, "")
    motivo, hace_falta = FALTA_EN_EL_PUENTE.get(orden, RAZON_GENERICA)
    return {"type": "puente_aviso", "orden": orden, "panel": panel,
            "motivo": motivo, "hace_falta": hace_falta, "origen": "real",
            "nota": extra or ""}


# ------------------------------------------------------------------ voz (F3) ----
# El puente no puede esperar a que el motor hable: Piper tarda y esta máquina tiene
# dos núcleos. Así que la síntesis va en su hilo (cort_voz.hablar_en_hilo) y aquí
# sólo se vigila el resultado, que se convierte en una URL que la página reproduce.
# Dos salidas y no una: en la Canaima suena el altavoz conectado (HDMI/USB) si lo hay,
# y en el teléfono suena el navegador. Si ninguna de las dos existe, se dice con el
# nombre del dispositivo, que es la regla de F1: nada de callarse fingiendo hablar.

def estado_voz():
    """Inventario real de la voz, con el campo `origen` que pide el contrato."""
    if cort_voz is None:
        return {"type": "voz_estado", "origen": "real", "ok": False,
                "motor": None, "motivo": "el módulo de voz no se pudo importar",
                "nota": VOZ_ERROR,
                "hace_falta": "arrancar el puente con .venv/bin/python (vosk + piper)"}
    d = cort_voz.disponibilidad()
    return {"type": "voz_estado", "origen": "real", "ok": bool(d.get("habla")),
            "habla": d.get("habla"), "motor": cort_voz.MOTOR,
            "activa": VOZ_ACTIVA, "sintetiza_ms": d.get("factor_medido"),
            "stt": d.get("stt"), "stt_mb": d.get("stt_mb"),
            "altavoz_real": d["dispositivos"]["suena"],
            "sink": cort_voz.salida_por_defecto(),
            "micro": d["dispositivos"]["escucha"],
            "microfonos": [m["nombre"] for m in d["dispositivos"]["microfonos_reales"]],
            "entradas_que_ve": [e["nombre"] for e in d["dispositivos"]["entradas"]],
            "escucha": (MIC.estado if MIC else "apagada"),
            "nota": ("" if d["dispositivos"]["suena"] else
                     "no hay altavoz físico: la única salida es auto_null (conecta HDMI o dongle USB)"),
            }


def avisa_desde_hilo(mensaje):
    """Un hilo de voz/escucha deja su mensaje en todas las bandejas sin tocar el lazo."""
    def repartir():
        for ws in list(CONEXIONES):
            enviar(ws, mensaje)
    if BUCLE is not None:
        try:
            BUCLE.call_soon_threadsafe(repartir)
        except Exception:
            pass


# ------------------------------------------------------------------ vida (F4) ----
def notas_para_panel() -> list:
    """El panel de notas de la plantilla pide `titre` / `mtime` / `taille`. Le
    llegan las notas reales de CORT; se avisa en el mensaje de que no es Obsidian."""
    if cort_vida is None:
        return []
    salida = []
    for n in cort_vida.notas():
        epoca = 0
        try:
            epoca = int(time.mktime(time.strptime(n.get("hora", ""), "%Y-%m-%dT%H:%M:%S")))
        except Exception:
            pass
        salida.append({"titre": n["titulo"], "mtime": epoca, "taille": n.get("chars", 0)})
    return salida


def al_vencer_recordatorio(r):
    """La vela de cort_vida avisa desde su hilo: panel + voz, no sólo consola."""
    falta = max(0, int(r.get("para", 0) - time.time()))
    hora = time.strftime("%H:%M", time.localtime(r.get("para", time.time())))
    enviar_aviso = {"type": "reminder_trigger", "time": hora, "text": r.get("texto", ""),
                    "origen": "real", "tipo": r.get("tipo", "recordatorio"), "seg": falta}
    avisa_desde_hilo(enviar_aviso)
    if VOZ_ACTIVA and cort_voz:
        decir = (f"Temporizador terminado." if r.get("tipo") == "temporizador"
                 else f"Recordatorio: {r.get('texto', '')}")
        try:
            cort_voz.hablar_en_hilo(decir[:200])
        except Exception:
            pass


if cort_vida:
    cort_vida.al_vencer(al_vencer_recordatorio)


async def vigilar_voz(ws, ident):
    """Espera el resultado de una frase sintetizada y lo manda a la página."""
    for _ in range(220):                     # hasta ~66 s; Piper con modelo frío pesa
        await asyncio.sleep(0.3)
        r = cort_voz.tarea(ident) if cort_voz else None
        if not r:
            continue
        nombre = Path(r.get("archivo", "")).name if r.get("ok") else ""
        enviar(ws, {"type": "voz_audio", "origen": "real", "id": ident,
                    "url": ("/audio/" + nombre) if nombre else None,
                    "texto": r.get("texto"), "motor": r.get("motor"),
                    "ms_sintesis": r.get("ms_sintesis"),
                    "audio_segundos": r.get("audio_segundos"),
                    "reproducido": r.get("reproducido"),
                    "altavoz_real": r.get("altavoz_real"),
                    "ok": r.get("ok"), "nota": r.get("nota") or r.get("motivo") or ""})
        return


async def hablar_por_el_puente(ws, texto):
    """Voz de salida para una respuesta: en hilo, con subtítulo ya enviado."""
    global VOZ_ACTIVA
    if cort_voz is None or not VOZ_ACTIVA or not (texto or "").strip():
        return
    ident = cort_voz.hablar_en_hilo(texto[:400])
    asyncio.create_task(vigilar_voz(ws, ident))


def mic_arrancar(ws, historial, candado):
    """Escucha continua sobre el micrófono real. Si no hay micro, lo dice con nombre."""
    global MIC
    if cort_voz is None:
        return {"ok": False, "motivo": "sin módulo de voz", "nota": VOZ_ERROR}
    libre = ram_disponible_mb()
    if libre < ALMENOS_AUDIO:
        return {"ok": False, "motivo": f"hacen falta ~{ALMENOS_AUDIO} MB libres para cargar Vosk "
                                       f"y hay {libre}", "origen": "real"}
    if MIC is not None and MIC.hilo and MIC.hilo.is_alive():
        return {"ok": True, "estado": MIC.estado, "nota": "ya estaba escuchando"}

    def al_texto(texto):
        avisa_desde_hilo({"type": "mic_texto", "texto": texto, "origen": "real"})
        try:
            BUCLE.call_soon_threadsafe(
                lambda: asyncio.create_task(atender_input(ws, texto, historial, candado)))
        except Exception as e:
            avisa_desde_hilo({"type": "mic_error", "motivo": f"{type(e).__name__}", "origen": "real"})

    def al_estado(estado):
        avisa_desde_hilo({"type": "mic_estado", "estado": estado, "origen": "real"})

    MIC = cort_voz.EscuchaContinua(al_texto, al_estado)
    r = MIC.arrancar()
    r["estado"] = MIC.estado
    return r


def mic_apagar():
    global MIC
    if MIC is None:
        return {"ok": True, "estado": "apagada", "nota": "no estaba encendida"}
    r = MIC.detener()
    r["textos"] = MIC.textos
    if MIC.errores:
        r["errores"] = MIC.errores[-3:]
    return r


def temperatura_sala():
    """Temperatura real del equipo, leída de los sensores del kernel.

    No hay sonda de ambiente en esta laptop: se dice el nombre del sensor que se
    está leyendo, para que nadie confunda la temperatura de la CPU con la de la sala.
    """
    zonas = []
    for p in sorted(Path("/sys/class/thermal").glob("thermal_zone*/temp")):
        try:
            valor = float(p.read_text().strip()) / 1000.0
        except Exception:
            continue
        try:
            nombre = (p.parent / "type").read_text().strip()
        except Exception:
            nombre = p.parent.name
        zonas.append((nombre, valor))
    if not zonas:
        return {"ok": False, "motivo": "no hay sensores térmicos en este equipo"}
    nombre, valor = max(zonas, key=lambda z: z[1])
    return {"ok": True, "origen": "real", "piece": f"sensor {nombre}",
            "temperature": round(valor, 1), "sensores": dict(zonas),
            "aviso": "Es la temperatura del chip, no la de la sala: no hay sonda ambiente."}


def ajustes_reales():
    """Lo que Ajustes debe rellenar con datos del puente (no con valores de ejemplo)."""
    e = leer_estado()
    compras = cort_vida.compras() if cort_vida else e.get("shopping", [])
    pend = ([r["texto"] for r in cort_vida.recordatorios(pendientes=True)]
            if cort_vida else e.get("reminders", []))
    return {"user_name": e.get("user_name", ""), "user_age": str(e.get("user_age", "")),
            "user_city": e.get("user_city", ""), "local_model": e.get("local_model", ""),
            "language": e.get("language", "es"), "reminders": pend,
            "shopping": compras}


async def muestra_medidas():
    """Mide lo que la pantalla necesita y nadie pidió: cerebro, sensores y clima.

    Se marca con `empujado` porque no es una petición de la usuaria: la demo abre
    sus paneles en cuanto llega un dato, y un dato que nadie pidió no tiene derecho
    a taparle la pantalla. Se pinta, pero se deja cerrado.
    """
    bucle = asyncio.get_event_loop()
    estado = await bucle.run_in_executor(None, estado_ollama)
    t = await bucle.run_in_executor(None, temperatura_sala)
    w = await bucle.run_in_executor(None, clima, leer_estado().get("user_city") or "")
    return [
        {"type": "ollama_status_reply", "status": estado},
        {"type": "sala_temperatura", "data": t, "empujado": True},
        {"type": "weather_panel", "data": w, "empujado": True},
    ]


async def muestrear_al_conectar(ws):
    for m in await muestra_medidas():
        if m["type"] == "sala_temperatura" and not m["data"].get("ok"):
            continue
        if m["type"] == "weather_panel" and not m["data"].get("ok"):
            continue
        enviar(ws, m)
    if cort_voz is not None:
        # La voz también se empuja: si no hay altavoz, la pantalla lo dice desde el
        # primer segundo en vez de dejar un icono de altavoz esperando un sonido que no llega.
        estado = await asyncio.get_event_loop().run_in_executor(None, estado_voz)
        enviar(ws, estado)


MUESTREO = None
MINUTOS_CLIMA = 10


async def latido_clima():
    """Renueva las medidas por su cuenta: así el panel tiene datos sin que nadie
    tenga que preguntar, y el coste es una petición a open-meteo cada 10 minutos."""
    while True:
        try:
            mensajes = await muestra_medidas()
            for ws in list(CONEXIONES):
                for m in mensajes:
                    if m["type"] == "sala_temperatura" and not m["data"].get("ok"):
                        continue
                    if m["type"] == "weather_panel" and not m["data"].get("ok"):
                        continue
                    enviar(ws, m)
        except Exception as e:
            print(f"[CORT] muestreo periódico falló ({type(e).__name__}): {e}")
        await asyncio.sleep(MINUTOS_CLIMA * 60)


async def ws_handler(request):
    global VOZ_ACTIVA, MICRO_ACTIVO
    ws = web.WebSocketResponse(heartbeat=25)
    await ws.prepare(request)
    CONEXIONES.add(ws)
    await abrir_canal(ws)
    candado = asyncio.Lock()
    print(f"[CORT] interfaz conectada ({len(CONEXIONES)} sesión/es)")
    historial = []

    enviar(ws, {"type": "connected", "origen": "real", "puente": "cort-bridge v0"})
    enviar(ws, {"type": "system_stats", **cpu_ram_disco()})
    # Al conectar ya se empuja lo que la pantalla muestra vacío si nadie lo pide:
    # estado del cerebro, temperatura del equipo y clima. La demo esperaba que su
    # backend propio con estos datos; ése era el motivo del «OBTENIENDO…» eterno.
    asyncio.create_task(muestrear_al_conectar(ws))

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
                enviar(ws, {"type": "system_stats", **cpu_ram_disco()})

            elif t == "check_ollama_status":
                # En un hilo: lee disco y hace una petición HTTP, y eso no puede
                # congelar el bucle que atiende a las demás conexiones.
                estado = await asyncio.get_event_loop().run_in_executor(None, estado_ollama)
                enviar(ws, {"type": "ollama_status_reply", "status": estado})

            elif t == "start_ollama":
                ok, detalle = ollama_arrancar()
                enviar(ws, {"type": "ollama_start_result", "ok": ok, "detalle": detalle, "origen": "real"})
                if ok:
                    # El servidor tarda un poco en escuchar; dar margen antes de preguntar.
                    await asyncio.sleep(3)
                estado = await asyncio.get_event_loop().run_in_executor(None, estado_ollama)
                enviar(ws, {"type": "ollama_status_reply", "status": estado})

            elif t == "buscar_actualizacion":
                if cort_actualiza is None:
                    enviar(ws, {"type": "actualizacion", "origen": "no disponible", "ok": False,
                                "motivo": "el módulo del canal de actualización no cargó"})
                    continue
                r = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: cort_actualiza.registrar(cort_actualiza.consultar()))
                enviar(ws, {"type": "actualizacion", **r})
                await decir(ws, (f"Hay una versión nueva de CORT: {r['remota']}. "
                                 f"Para traerla: {r['como']}") if r.get("hay_nueva") else
                            (r.get("motivo") or f"CORT {r['version_local']} está al día "
                             f"respecto a {r.get('remota')}"))

            elif t == "probar_cerebro":
                modelo = (d.get("model") or "").strip()
                frase = (d.get("frase") or "mueve la carpeta proyectos a documentos").strip()[:300]
                enviar(ws, {"type": "cerebro_prueba", "origen": "real", "empezando": True,
                            "modelo": modelo, "frase": frase})
                r = await asyncio.get_event_loop().run_in_executor(
                    None, probar_cerebro, modelo, frase)
                enviar(ws, {"type": "cerebro_prueba", "origen": r.get("origen") or "no disponible",
                            "modelo": modelo,
                            **{k: v for k, v in r.items() if k not in ("origen", "modelo")}})
                if not r.get("ok"):
                    await decir(ws, "No probé el cerebro: " + r.get("motivo", ""))

            elif t == "pull_ollama_model":
                modelo = d.get("model") or ""
                info = catalogo().get(modelo, {})
                libre = ram_disponible_mb()
                if PULANDO.get(modelo):
                    enviar(ws, {"type": "ollama_pull_progress", "status": "esa descarga ya está en curso",
                                        "pct": PULANDO[modelo], "done": False, "origen": "real"})
                    continue
                # Si ya está en disco, no se vuelve a bajar: se dice y se explica que
                # lo que falta es memoria, no descarga.
                ya = inventario_disco().get(modelo)
                if ya:
                    enviar(ws, {
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
                    enviar(ws, {
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
                        enviar(ws, {
                            "type": "ollama_pull_progress", "done": True, "success": False, "pct": 0,
                            "origen": "real",
                            "status": (f"RAM insuficiente para levantar el servidor: {libre} MB libres, "
                                       f"hacen falta {RAM_SERVIDOR} MB. Cierra pestañas y vuelve a pedirlo."),
                        })
                        continue
                    ok_arranque, detalle = ollama_arrancar()
                    if not ok_arranque:
                        enviar(ws, {"type": "ollama_pull_progress", "done": True, "success": False,
                                            "pct": 0, "status": detalle, "origen": "real"})
                        continue
                    enviar(ws, {"type": "ollama_pull_progress", "done": False, "pct": 0,
                                        "status": f"Arrancando Ollama: {detalle}", "origen": "real"})
                    for _ in range(20):
                        await asyncio.sleep(1)
                        vivo, _ = ollama_vivo()
                        if vivo:
                            break
                    if not vivo:
                        enviar(ws, {"type": "ollama_pull_progress", "done": True, "success": False,
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
                enviar(ws, {"type": "local_model_set", "model": modelo_elegido,
                                    "aviso": aviso, "origen": "real"})
                await decir(ws, aviso)

            elif t in ("settings-save", "settings_save", "update_settings"):
                # La interfaz manda `update_settings` al pulsar GUARDAR y el puente
                # sólo entendía `settings-save`: el botón llevaba todo el proyecto
                # sin guardar nada. Los tres nombres son el mismo acto.
                e = leer_estado()
                for k, v in (d.get("settings") or d).items():
                    if isinstance(v, (str, int, float, bool, list, dict)) and k not in ("type", "action"):
                        e[k] = v
                escribir_estado(e)
                enviar(ws, {"type": "settings_saved", "origen": "real"})
                enviar(ws, {"type": "settings_data", "data": ajustes_reales()})

            elif t == "get_settings":
                enviar(ws, {"type": "settings_data", "data": ajustes_reales(), "origen": "real"})

            elif t == "get_shopping_list":
                if cort_vida is None:
                    enviar(ws, aviso_sin_backend(t, VIDA_ERROR))
                else:
                    items = cort_vida.compras()
                    enviar(ws, {"type": "shopping_list", "items": items, "origen": "real",
                                "nota": f"lista de CORT, guardada en {cort_vida.VIDA}",
                                "empujado": bool(d.get("empujado"))})

            elif t == "update_shopping_list":
                if cort_vida is None:
                    enviar(ws, aviso_sin_backend(t, VIDA_ERROR))
                else:
                    r = await asyncio.get_event_loop().run_in_executor(
                        None, cort_vida.fijar_compras, d.get("items") or [])
                    if r.get("ok"):
                        enviar(ws, {"type": "shopping_list", "items": r["items"],
                                    "origen": "real"})
                    else:
                        enviar(ws, {"type": "shopping_list", "items": cort_vida.compras(),
                                    "origen": "no disponible", "motivo": r.get("motivo", "")})

            elif t == "vida_estado":
                if cort_vida is None:
                    enviar(ws, aviso_sin_backend(t, VIDA_ERROR))
                else:
                    enviar(ws, {"type": "vida_estado", "origen": "real",
                                "datos": cort_vida.disponibilidad(),
                                "compras": cort_vida.compras(),
                                "notas": cort_vida.notas(),
                                "pendientes": cort_vida.recordatorios(pendientes=True),
                                "resumen": cort_vida.resumen_hablado()})

            elif t == "save_obsidian_note":
                # El panel se llama Obsidian en la plantilla, pero Obsidian no está
                # instalado: aquí mandan las notas de CORT, y se dice en la propia nota.
                if cort_vida is None:
                    enviar(ws, aviso_sin_backend(t, VIDA_ERROR))
                else:
                    r = cort_vida.guardar_nota(d.get("titre") or d.get("titulo") or "",
                                               d.get("content") or d.get("texto") or "")
                    if r.get("ok"):
                        enviar(ws, {"type": "obsidian_notes", "notes": notas_para_panel(),
                                    "origen": "real",
                                    "nota": f"nota de CORT en {cort_vida.VIDA} (no es Obsidian)"})
                        enviar(ws, {"type": "obsidian_note_content", "titre": r["titulo"],
                                    "content": (d.get("content") or "")[:20000],
                                    "origen": "real"})
                    else:
                        enviar(ws, {"type": "puente_aviso", "orden": t, "panel": "obsidian-panel",
                                    "motivo": r.get("motivo", "no se pudo guardar"),
                                    "hace_falta": "un título y un texto", "origen": "real"})

            elif t == "read_obsidian_note":
                if cort_vida is None:
                    enviar(ws, aviso_sin_backend(t, VIDA_ERROR))
                else:
                    r = cort_vida.leer_nota(d.get("titre") or d.get("titulo") or "")
                    enviar(ws, {"type": "obsidian_notes", "notes": notas_para_panel(),
                                "origen": "real"})
                    if r.get("ok"):
                        enviar(ws, {"type": "obsidian_note_content", "titre": r["titulo"],
                                    "content": r["content"], "origen": "real"})
                    else:
                        enviar(ws, {"type": "puente_aviso", "orden": t, "panel": "obsidian-panel",
                                    "motivo": r.get("motivo", ""), "hace_falta": "un título guardado",
                                    "origen": "real"})

            elif t == "delete_obsidian_note":
                if cort_vida is None:
                    enviar(ws, aviso_sin_backend(t, VIDA_ERROR))
                else:
                    r = cort_vida.borrar_nota(d.get("titre") or d.get("titulo") or "")
                    enviar(ws, {"type": "obsidian_notes", "notes": notas_para_panel(),
                                "origen": "real"})
                    enviar(ws, {"type": "puente_aviso" if not r.get("ok") else "obsidian_nota_borrada",
                                "orden": t, "panel": "obsidian-panel", "titulo": r.get("titulo", ""),
                                "motivo": r.get("motivo", ""), "origen": "real"})

            elif t == "ha_get_states":
                # Sin servidor no hay sensores: se dice con `success` y el aviso, para
                # que el panel deje de girar mostrando una carga que nunca termina.
                enviar(ws, {"type": "ha_states", "success": False, "states": [],
                            "motivo": "no hay Home Assistant en esta red", "origen": "real"})
                enviar(ws, aviso_sin_backend("ha_get_states"))

            elif t == "temperatura":
                tx = await asyncio.get_event_loop().run_in_executor(None, temperatura_sala)
                if tx.get("ok"):
                    enviar(ws, {"type": "sala_temperatura", "data": tx})
                else:
                    enviar(ws, aviso_sin_backend("temperatura", tx.get("motivo", "")))

            elif t == "weather":
                ciudad = d.get("city") or leer_estado().get("user_city") or ""
                w = await asyncio.get_event_loop().run_in_executor(None, clima, ciudad)
                enviar(ws, {"type": "weather_panel", "data": w})

            elif t in ("av-scan", "run_security_scan", "security_scan", "av_scan_start"):
                if ws in ESCANEANDO:
                    # La interfaz pide el escaneo dos veces (abre el panel y además
                    # dispara su propio botón): el segundo se ignora para no duplicar
                    # cada línea del registro.
                    enviar(ws, {"type": "av_progress", "percent": 50, "step": "curso",
                                        "message": "La auditoría ya está en curso", "origen": "real"})
                    continue
                CANCELADOS.discard(ws)
                asyncio.create_task(escaneo(ws))

            elif t == "av_scan_cancel":
                CANCELADOS.add(ws)
                enviar(ws, {"type": "av_cancel", "origen": "real"})

            elif t == "av_threat_action":
                # Regla dura: CORT informa, no borra ni mata procesos por su cuenta.
                enviar(ws, {
                    "type": "av_action_result", "ok": False,
                    "message": "No voy a borrar ni bloquear «" + str((d.get("threat") or {}).get("name", "?")) +
                               "». Un falso positivo cuesta más que una amenaza visible: dime tú qué hacer.",
                    "origen": "real",
                })

            elif t == "get_agent_models":
                installed = sorted(catalogo())
                enviar(ws, {"type": "agent_models_info",
                                    "data": {"available_models": {a: installed for a in ("principal", "rapido", "seguro")}},
                                    "origen": "real"})

            elif t == "set_agent_models":
                e = leer_estado(); e["agent_models"] = d.get("models") or {}
                escribir_estado(e)
                enviar(ws, {"type": "agent_models_saved", "origen": "real"})

            elif t == "check_jarvis_os_status":
                vivo = await asyncio.get_event_loop().run_in_executor(None, jarvis_os_vivo)
                enviar(ws, {"type": "jarvis_os_status_reply", "installed": vivo,
                                    "port": JARVIS_OS_PUERTO,
                                    "motivo": None if vivo else "nada escuchando en 127.0.0.1:%d" % JARVIS_OS_PUERTO,
                                    "origen": "real"})

            elif t.startswith("jarvis_os_"):
                # Se responde con honestidad en vez de dejar el panel colgado: instalar
                # un SO entero en una Canaima de 1,8 GiB significaría borrar su disco.
                enviar(ws, {"type": "jarvis_os_install_progress", "done": True, "progress": 0,
                                    "status": "Detenido a propósito por CORT",
                                    "log": ("Jarvis OS necesita el disco completo; en este equipo (2 núcleos, "
                                            "1851 MB) sustituiría tu MX Linux. No lo instalo sin tu orden explícita "
                                            "y un respaldo previo.\n"),
                                    "origen": "real"})

            elif t in ("voz_estado", "check_local_tts_status"):
                # La demo lee su fila de Ajustes por `local_tts_status_reply` con el
                # campo status.piper; se manda también, además del estado completo.
                estado = estado_voz()
                enviar(ws, estado)
                if t == "check_local_tts_status":
                    enviar(ws, {"type": "local_tts_status_reply", "origen": "real",
                                "status": {"piper": bool(estado.get("habla")),
                                           "chatterbox": False,
                                           "chatterbox_missing": ["chatterbox (no instalado a propósito)"],
                                           "motor": estado.get("motor"),
                                           "altavoz_real": estado.get("altavoz_real")}})

            elif t == "voz_on":
                VOZ_ACTIVA = True
                r = estado_voz(); r["type"] = "voz_activada"
                enviar(ws, r)

            elif t == "voz_off":
                VOZ_ACTIVA = False
                enviar(ws, {"type": "voz_desactivada", "origen": "real",
                            "nota": "el texto sigue apareciendo en pantalla"})

            elif t == "voz_motor":
                nuevo = (d.get("motor") or d.get("value") or "").strip()
                if cort_voz is None:
                    enviar(ws, {"type": "voz_motor_result", "origen": "real", "ok": False,
                                "motivo": "sin módulo de voz", "nota": VOZ_ERROR})
                else:
                    r = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: cort_voz.cambiar_motor(nuevo))
                    # La primera frase con Piper paga la carga del modelo (14 s medidos).
                    enviar(ws, {"type": "voz_motor_result", "origen": "real", **r,
                                "aviso": ("el primer saying tarda ~15 s: el modelo se carga una sola vez"
                                          if r.get("ok") and nuevo != "rapida" else "")})

            elif t == "av_speak":
                texto = (d.get("text") or d.get("texto") or "").strip()
                if cort_voz is None or not texto:
                    enviar(ws, aviso_sin_backend("av_speak", "no llega texto que hablar"
                                                 if not texto else VOZ_ERROR))
                else:
                    ident = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: cort_voz.hablar_en_hilo(texto[:400]))
                    enviar(ws, {"type": "voz_pedido", "origen": "real", "id": ident,
                                "texto": texto[:120],
                                "nota": "sintetizando en segundo plano"})
                    asyncio.create_task(vigilar_voz(ws, ident))

            elif t in ("toggle_mic", "toggle_always_listen", "mic_on"):
                if MICRO_ACTIVO:
                    enviar(ws, {"type": "mic_estado", "estado": (MIC.estado if MIC else "apagada"),
                                "origen": "real", "nota": "ya encendido"})
                else:
                    r = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: mic_arrancar(ws, historial, candado))
                    MICRO_ACTIVO = bool(r.get("ok"))
                    enviar(ws, {"type": "mic_estado", "origen": "real",
                                "estado": r.get("estado", "apagada"),
                                "ok": r.get("ok"), "motivo": r.get("motivo", ""),
                                "microfonos": [m["nombre"] for m in
                                               cort_voz.dispositivos()["microfonos_reales"]]
                                              if cort_voz else [],
                                "nota": ("el orbe indica cuándo escucha" if r.get("ok")
                                         else "sin micro en este equipo: el del teléfono entra en F7")})

            elif t in ("mic_off", "stop_listening"):
                r = await asyncio.get_event_loop().run_in_executor(None, mic_apagar)
                MICRO_ACTIVO = False
                enviar(ws, {"type": "mic_estado", "origen": "real", **r})

            elif t == "mic_estado":
                enviar(ws, estado_voz())

            elif t == "check_kokoro_status":
                # Kokoro no está instalado y no se baja a ciegas: hay Piper local medido.
                # La demo pinta esto por `kokoro_status_reply` leyendo status.online.
                enviar(ws, {"type": "kokoro_status_reply", "origen": "real",
                            "status": {"online": False, "installed": False,
                                       "motivo": "Kokoro baja varios GB de modelos y este equipo tiene 1851 MB"},
                            "nota": ("en su lugar: Piper es_ES + espeak-ng, medidos en la tabla de F3 "
                                     "(0,14 y 1,90 ms de CPU por segundo de audio)"
                                     if cort_voz else "sin módulo de voz")})

            elif t == "pc_accion":
                # La vía directa del panel: {accion: "...", ...datos}. Todo lo que
                # ejecuta el equipo pasa por aquí o por las frases de abajo.
                if cort_acciones is None:
                    enviar(ws, aviso_sin_backend(t, ACCIONES_ERROR))
                else:
                    nombre = (d.get("accion") or "").strip()
                    r = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: cort_acciones.accion(nombre, d))
                    enviar(ws, {**r, "type": "cort_accion", "origen": "real"})

            elif t == "pc_estado":
                if cort_acciones is None:
                    enviar(ws, aviso_sin_backend(t, ACCIONES_ERROR))
                else:
                    enviar(ws, await asyncio.get_event_loop().run_in_executor(
                        None, cort_acciones.estado_pc))

            elif t == "open_browser":
                # El navegador incrustado de la demo se fue con su backend. Lo que sí
                # existe es abrir la URL en el navegador del sistema y decirlo.
                url = (d.get("url") or "").strip()
                if cort_acciones is None or not url:
                    enviar(ws, aviso_sin_backend("open_browser",
                                                 "no llega URL que abrir" if not url else ACCIONES_ERROR))
                else:
                    r = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: cort_acciones.abrir_url(url))
                    enviar(ws, {"type": "browser_state", "origen": "real",
                                "state": "abierto-en-el-sistema" if r.get("ok") else "cerrado",
                                "url": url,
                                "nota": "el panel incrustado ya no existe: se abrió en el navegador "
                                        "por defecto de MX Linux con xdg-open"})

            elif t == "detect_apps":
                if cort_acciones is None:
                    enviar(ws, aviso_sin_backend(t, ACCIONES_ERROR))
                else:
                    a = await asyncio.get_event_loop().run_in_executor(
                        None, cort_acciones.apps_disponibles)
                    # La demo lee `nom` y `chemin` (los campos de su backend francés).
                    enviar(ws, {"type": "detected_apps", "origen": "real",
                                "apps": [{"nom": x["nombre"], "chemin": x["ejec"] or x["archivo"]}
                                         for x in a]})

            elif t == "get_installed_programs":
                if cort_acciones is None:
                    enviar(ws, aviso_sin_backend(t, ACCIONES_ERROR))
                else:
                    r = await asyncio.get_event_loop().run_in_executor(
                        None, cort_acciones.programas_instalados)
                    enviar(ws, {"type": "installed_programs", "origen": "real",
                                "programs": [{"name": p["nombre"], "version": p["version"],
                                              "publisher": "dpkg (gestor de paquetes de este equipo)",
                                              "hive": f"{p['tamano_kb']} KB"}
                                             for p in r.get("programs", [])]})

            elif t == "get_winget_upgrades":
                if cort_acciones is None:
                    enviar(ws, aviso_sin_backend(t, ACCIONES_ERROR))
                else:
                    r = await asyncio.get_event_loop().run_in_executor(
                        None, cort_acciones.actualizaciones)
                    enviar(ws, {"type": "winget_upgrades", "origen": "real",
                                "nota": ("winget no existe en Linux: leído con `apt list --upgradable`"),
                                "upgrades": [{"name": u["nombre"], "id": u["nombre"],
                                              "version": u["de"], "available": u["a"],
                                              "source": "apt"}
                                             for u in r.get("upgrades", [])]})

            elif t == "games_get_library":
                if cort_acciones is None:
                    enviar(ws, aviso_sin_backend(t, ACCIONES_ERROR))
                else:
                    def biblioteca():
                        apps = cort_acciones.apps_disponibles()
                        juegos = [a for a in apps if "game" in (a.get("nota", "") + a["archivo"]).lower()]
                        return juegos
                    juegos = await asyncio.get_event_loop().run_in_executor(None, biblioteca)
                    enviar(ws, {"type": "games_library", "origen": "real",
                                "games": [{"name": g["nombre"], "path": g["ejec"],
                                           "exe": g["ejec"], "folder": str(Path(g["archivo"]).parent)}
                                          for g in juegos],
                                "folders": sorted({str(Path(g["archivo"]).parent) for g in juegos}),
                                "nota": "biblioteca leída de los .desktop con categoría Game; "
                                        "no hay Steam en este equipo"})

            elif t == "get_desktop_wallpaper":
                if cort_acciones is None:
                    enviar(ws, aviso_sin_backend(t, ACCIONES_ERROR))
                else:
                    r = await asyncio.get_event_loop().run_in_executor(
                        None, cort_acciones.fondo_escritorio)
                    data_url = ""
                    if r.get("existe") and r.get("archivo") and Path(r["archivo"]).is_file():
                        crudo = Path(r["archivo"]).read_bytes()
                        if len(crudo) < 4_000_000:            # 4 MB de base64 ya no caben por WS
                            data_url = ("data:image/png;base64," +
                                        base64.b64encode(crudo).decode())
                    enviar(ws, {"type": "desktop_wallpaper_result", "origen": "real",
                                "data_url": data_url, "archivo": r.get("archivo") or "",
                                "nota": (r["detalle"] if not data_url else
                                         f"fondo leído con xfconf-query: {r.get('archivo')}")})

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
                # Se atiende en su propia tarea: si no, mientras el modelo piensa o
                # mientras CORT habla, el lazo no lee ningún botón más. El candado
                # mantiene las respuestas en orden de pregunta.
                asyncio.create_task(atender_input(ws, texto, historial, candado))

            else:
                # Ninguna orden se queda ya sin respuesta: si el puente no puede,
                # dice por qué y qué haría falta. Así se distingue "no hace nada"
                # de "está esperando", y el censo de la sonda deja de leer silencios.
                enviar(ws, aviso_sin_backend(t or "(vacío)",
                                             d.get("model") or d.get("city") or ""))
    finally:
        await cerrar_canal(ws)
        CONEXIONES.discard(ws)
        print("[CORT] interfaz desconectada")
    return ws


async def atender_input(ws, texto, historial, candado):
    """Responde una frase escrita o dictada: primero reglas locales, luego modelo."""
    async with candado:
        if ws not in SALIDA:
            return
        enviar(ws, {"state": "thinking"})
        estado = leer_estado()
        local = await asyncio.get_event_loop().run_in_executor(None, intentos_locales, texto, estado)
        if local:
            respuesta, extras = local
            for m in extras:
                if m.get("type") == "av-scan":
                    asyncio.create_task(escaneo(ws))
                else:
                    enviar(ws, {**m, "action": m.get("type")})
            historial.append({"role": "user", "content": texto})
            historial.append({"role": "assistant", "content": respuesta})
            await decir(ws, respuesta)
            enviar(ws, {"type": "brain_used", "modelo": "reglas locales + datos del sistema",
                        "origen": "real"})
            return
        # ---- F9: si la frase es una orden, no es charla ----
        # La confirmación se pide y se recibe con palabras, igual que en F5 con apagar:
        # un plan del modelo nunca se autosirve.
        oido = (sin_acentos(texto) or "").strip()
        if PENDIENTE.get("plan") and re.match(r"^(confirmar|confirma|adelante|hazlo)\b", oido):
            if time.monotonic() - PENDIENTE["hora"] > 120:
                PENDIENTE.clear()
                await responder_plan(ws, {"decir": "Ese plan ya se venció: pídeme la orden de nuevo.",
                                          "valido": False, "origen": "no disponible",
                                          "intencion": "", "motivo": "confirmación fuera de tiempo"},
                                     texto, historial, "")
                return
            plan = PENDIENTE["plan"]
            PENDIENTE.clear()
            r = await asyncio.get_event_loop().run_in_executor(
                None, lambda: cort_intenciones.ejecutar(plan, confirmar=True))
            await responder_plan(ws, r, texto, historial, "")
            return
        if NUCLEO_ON and cort_intenciones is not None:
            plan, crudo = await asyncio.get_event_loop().run_in_executor(
                None, compilar_intencion, texto, estado)
            if plan is not None:
                r = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: cort_intenciones.ejecutar(plan))
                es_charla = (r.get("intencion") or "nada") in ("nada", "") and not r.get("valido")
                if not es_charla:
                    if not r["valido"] and "confirmaci" in (r.get("motivo") or ""):
                        # un sí humano, no del modelo; y no caduca si la pestaña se recarga
                        PENDIENTE.update({"plan": plan, "hora": time.monotonic()})
                    await responder_plan(ws, r, texto, historial, crudo)
                    return
        r = await asyncio.get_event_loop().run_in_executor(None, cerebro, texto, historial, estado)
        if r["ok"]:
            historial.append({"role": "user", "content": texto})
            historial.append({"role": "assistant", "content": r["texto"]})
            await decir(ws, r["texto"])
            enviar(ws, {"type": "brain_used", "modelo": r.get("modelo"), "origen": "real"})
        else:
            await decir(ws, "Sin cerebro local: " + r["motivo"])


async def responder_plan(ws, r, texto, historial, crudo=""):
    """Cuenta qué entendió el cerebro, qué aceptó la reja y qué salió de ejecutarlo."""
    enviar(ws, {"type": "plan_resultado", "origen": r.get("origen") or "no disponible",
                "intencion": r.get("intencion") or "", "valido": bool(r.get("valido")),
                "decir": r.get("decir") or "", "motivo": r.get("motivo") or "",
                "plan": r.get("plan"), "detalle": r.get("detalle"),
                "crudo": (crudo or "")[:240], "frase": texto})
    historial.append({"role": "user", "content": texto})
    historial.append({"role": "assistant", "content": r.get("decir") or ""})
    await decir(ws, r.get("decir") or "")
    enviar(ws, {"type": "brain_used", "modelo": "modelo local + reja de intenciones",
                "origen": "real"})


async def decir(ws, texto):
    """Deja la respuesta en la bandeja de salida y sigue su camino.

    Antes dormía aquí entre subtítulo y subtítulo: una frase de 300 caracteres
    tenía sorda a CORT unos 9 s. Ahora cada pieza lleva su pausa y el redactor la
    aplica, que es quien escribe de verdad.
    """
    ident = "cort-%d" % int(time.time() * 1000)
    enviar(ws, {"state": "speaking"})
    enviar(ws, {"type": "user_speech", "text": ""})
    trozos = [texto[i:i + 26] for i in range(0, len(texto), 26)] or [texto]
    enviar(ws, {"type": "live_subtitles", "id": ident, "phase": "start"})
    for trozo in trozos:
        enviar(ws, {"type": "live_subtitles", "id": ident, "phase": "delta", "text": trozo + " "},
               pausa=0.05)
    enviar(ws, {"type": "live_subtitles", "id": ident, "phase": "end"})
    enviar(ws, {"type": "jarvis_text", "text": texto, "origen": "real"})
    # El respiro antes de volver a "idle" se tope en 4 s: con una respuesta larga
    # (la selección subrayada llega a tener mil caracteres) la pausa de 30 s dejaba
    # la bandeja sin oír ningún botón, que es el defecto que ya combatimos en F3.
    enviar(ws, {"state": "idle"}, pausa=min(4.0, max(1.2, len(texto) * 0.03)))
    # Y además lo dice: la voz sale en su hilo, así que el subtítulo y la escucha
    # de botones no esperan los milisegundos que tarde sintetizar.
    await hablar_por_el_puente(ws, texto)


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
                    enviar(ws, {"type": "ollama_pull_progress", "done": True, "success": False,
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
                enviar(ws, {"type": "ollama_pull_progress", "status": estado_txt,
                                    "pct": pct, "done": False, "origen": "real"})
        vivo, modelos = ollama_vivo()
        recien = inventario_disco(fuerzo=True)   # el archivo nuevo no puede taparlo la caché
        if modelo in modelos or modelo in recien or any(k.startswith(modelo.split(":")[0]) for k in modelos):
            enviar(ws, {"type": "ollama_pull_progress", "done": True, "success": True, "pct": 100,
                                "status": f"{modelo} instalado", "origen": "real"})
            await decir(ws, f"Modelo {modelo} descargado y listo. Ya puedo pensar con él.")
        else:
            enviar(ws, {"type": "ollama_pull_progress", "done": True, "success": False,
                                "status": "la descarga terminó pero el modelo no aparece en la lista",
                                "origen": "real"})
    except Exception as e:
        enviar(ws, {"type": "ollama_pull_progress", "done": True, "success": False,
                            "status": f"descarga interrumpida: {e}", "origen": "real"})
    finally:
        PULANDO.pop(modelo, None)


async def escaneo(ws):
    """Auditoría por pasos: se avisa antes de cada comprobación y se envían los
    hallazgos de ese paso, de modo que el globo y la barra avanzan con datos reales."""
    d = time.time()
    ESCANEANDO.add(ws)
    try:
        enviar(ws, {"type": "av_start", "message": "Auditoría de seguridad local", "origen": "real"})
        total = len(PASOS) + 1
        hallazgos = []
        for i, (clave, nombre, fn) in enumerate(PASOS, start=1):
            enviar(ws, {"type": "av_progress", "percent": int(100 * i / total),
                                "step": clave, "message": f"Comprobando {nombre}",
                                "threats_found": len(hallazgos), "origen": "real"})
            if ws in CANCELADOS:
                CANCELADOS.discard(ws)
                enviar(ws, {"type": "av_cancel", "origen": "real"})
                return
            nuevo_ = await asyncio.get_event_loop().run_in_executor(None, fn)
            hallazgos += nuevo_
            for h in nuevo_:
                enviar(ws, {"type": "av_threat_detected", "threat": h, "origen": "real"})
        dur = round(time.time() - d, 2)
        enviar(ws, {"type": "av_progress", "percent": 100, "step": "fin",
                            "message": f"{len(hallazgos)} hallazgo(s) en {dur} s",
                            "threats_found": len(hallazgos), "origen": "real"})
        # La interfaz solo entra en su rama de amenazas si status vale "infected" y
        # lee el conteo en `threats`; con otro nombre muestra "sin amenazas" encima
        # de un registro con hallazgos (así se detectó midiéndolo).
        enviar(ws, {"type": "av_complete",
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
                enviar(ws, datos)
            except Exception:
                CONEXIONES.discard(ws)
        await asyncio.sleep(4)


async def auto_sonda():
    """CORT se mide sola cuando la RAM lo permite (M2).

    Espera la ventana —con Qoder y el navegador abiertos no hay 900 MB libres—,
    prueba el modelo más chico que quepa y deja el número en
    `mediciones/medicion-cerebro.json`. No ejecuta ninguna orden y no insiste: si
    el disparo no cabe, vuelve a mirar en diez minutos; si sale, se apaga.
    """
    umbral = int(os.environ.get("CORT_AUTOSONDA_UMBRAL", "900"))
    frase = os.environ.get("CORT_AUTOSONDA_FRASE", "mueve la carpeta proyectos a documentos")
    archivo = Path(os.environ.get("CORT_MEDICIONES",
                                  str(BASE.parent / "mediciones"))) / "medicion-cerebro.json"
    bucle = asyncio.get_running_loop()
    while True:
        await asyncio.sleep(int(os.environ.get("CORT_AUTOSONDA_CICLO", "600")))
        if archivo.exists() and os.environ.get("CORT_AUTOSONDA_REPITA", "0") != "1":
            return
        libre = ram_disponible_mb()
        if 0 <= libre < umbral:
            continue
        candidatos = sorted(inventario_disco().items(), key=lambda kv: kv[1]["ram_est"])
        elegido = next((n for n, d in candidatos if d["ram_est"] <= libre), None)
        if not elegido:
            continue
        r = await bucle.run_in_executor(None, probar_cerebro, elegido, frase)
        if not r.get("ok"):
            print(f"[CORT] auto-sonda con {elegido}: {r.get('motivo')}", file=sys.stderr)
            continue
        try:
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError as e:
            print(f"[CORT] no se pudo guardar la medición: {e}", file=sys.stderr)
        print(f"[CORT] cerebro medido solo: {elegido} respondió en {r['ms']} ms "
              f"({r['tok_s']} tok/s), reja: {'acepta' if r['valido'] else 'rechaza'}")
        for w in list(CONEXIONES):
            enviar(w, {"type": "cerebro_prueba", "origen": "real", "auto": True, **r})
        return


async def vigila_version():
    """U1: mira las etiquetas del repo de vez en cuando y avisa si hay versión nueva.

    No descarga ni instala nada: un asistente que se actualiza solo es la puerta de
    entrada a que lo haga otro. Aquí se informa el número y el comando.
    """
    ciclo = int(os.environ.get("CORT_ACTUALIZA_CICLO", "21600"))
    await asyncio.sleep(20)
    bucle = asyncio.get_running_loop()
    while cort_actualiza is not None:
        r = await bucle.run_in_executor(None, lambda: cort_actualiza.registrar(cort_actualiza.consultar()))
        if r.get("hay_nueva"):
            print(f"[CORT] versión nueva disponible: {r['remota']} (local {r['version_local']})")
            for w in list(CONEXIONES):
                enviar(w, {"type": "actualizacion", **r})
        await asyncio.sleep(ciclo)


async def main():
    global BUCLE
    BUCLE = asyncio.get_running_loop()
    if cort_vida:
        cort_vida.avivar()      # un hilo, grano de 1 s: los pendientes vencen solos
    if os.environ.get("CORT_AUTOSONDA", "0") == "1":
        asyncio.create_task(auto_sonda())
    if os.environ.get("CORT_ACTUALIZA", "1") == "1" and cort_actualiza is not None:
        asyncio.create_task(vigila_version())

    # F7: por defecto el puente sólo escucha en casa (127.0.0.1). Abrirlo a la red
    # local es decisión de la usuaria, con la variable CORT_BIND, y sin HTTPS el
    # teléfono no puede instalar la aplicación (los navegadores sólo permiten el
    # service worker y el micrófono en origen seguro).
    bind = os.environ.get("CORT_BIND", "127.0.0.1")
    ssl_ctx = None
    tls = os.environ.get("CORT_TLS", "")
    if tls:
        try:
            cert, clave = tls.split(",")
            import ssl as _ssl
            ssl_ctx = _ssl.create_default_context(_ssl.Purpose.CLIENT_AUTH)
            ssl_ctx.load_cert_chain(cert, clave)
        except Exception as e:
            print(f"[CORT] TLS pedido pero no cargó ({type(e).__name__}: {e}); sigo en http")
    protocolo = "https" if ssl_ctx else "http"
    ws_protocolo = "wss" if ssl_ctx else "ws"

    app_ws = web.Application()
    app_ws.router.add_get("/ws", ws_handler)
    app_ws.router.add_get("/", ws_handler)

    app_web = web.Application()
    app_web.router.add_get("/", lambda r: web.FileResponse(BASE / "index.html"))

    async def audio(request):
        """Sirve el WAV recién hablado, para que suene también en el navegador.

        Ruta cerrada: sólo nombres con el formato que escribe cort_voz y sólo desde
        su carpeta temporal. Un navegador en el teléfono no puede leer /tmp.
        """
        nombre = request.match_info.get("nombre", "")
        if not re.fullmatch(r"(decir|escucha)-[0-9]+(-[0-9]+)?\.wav", nombre):
            return web.Response(status=404, text="no existe")
        ruta = Path(cort_voz.TMP if cort_voz else "/tmp/cort-voz") / nombre
        if not ruta.is_file():
            return web.Response(status=404, text="no existe")
        return web.FileResponse(ruta)

    app_web.router.add_get("/audio/{nombre}", audio)
    app_web.router.add_static("/", BASE, show_index=False, follow_symlinks=True)

    print(f"[CORT] interfaz  {protocolo}://{bind}:{PUERTO_WEB}/index.html")
    print(f"[CORT] websocket {ws_protocolo}://{bind}:{PUERTO_WS}/ws")
    if bind != "127.0.0.1":
        ip = socket.gethostbyname_ex(socket.gethostname())[2]
        print(f"[CORT] a la red local: {protocolo}://{(ip or [bind])[0]}:{PUERTO_WEB}/ "
              + ("(HTTPS: se puede instalar como aplicación)" if ssl_ctx else
                 "(sin HTTPS el teléfono no instala la PWA ni da micrófono: origen no seguro)"))
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
    await web.TCPSite(runner_ws, bind, PUERTO_WS, ssl_context=ssl_ctx).start()
    await web.TCPSite(runner_web, bind, PUERTO_WEB, ssl_context=ssl_ctx).start()
    asyncio.create_task(latido())
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[CORT] puente detenido")
