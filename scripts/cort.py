#!/usr/bin/env python3
"""Arranca CORT: core, interfaz y navegador, con una terminal que dice algo.

Dos puertas, un mismo cuerpo. Doble clic en `CORT.desktop` / `cort.bat` lanza
esto mismo con la terminal abierta; para el usuario que prefiere la interfaz sin
ver consola, `--quiet`.

Sin dependencias. Esta máquina tiene 1,8 GiB de RAM y cada proceso cuenta, así
que el lanzador no instala nada ni arranca un framework de terminal: ANSI
directo y la biblioteca estándar.

Lo que hace el `--serve dist` por defecto: si `apps/web/dist` existe, se sirve
desde ahí con un servidor estático de 40 líneas en vez de levantar Vite. Vite en
dev son ~120 MB de RAM y un watcher de archivos; para encender y hablar no hacen
falta ninguno de los dos.
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web"
CORE = ROOT / "services" / "core"
DATA = CORE / "data"

# El violeta de CORT en la paleta de 256 colores de la terminal.
VIOLET = "\033[38;5;141m"
CYAN = "\033[38;5;81m"
DIM = "\033[2m"
BOLD = "\033[1m"
RED = "\033[38;5;204m"
GREEN = "\033[38;5;120m"
RESET = "\033[0m"

# Todo ANSI de 16/256 colores cabe en este patrón; sirve para desvestir el texto.
ANSI = re.compile(r"\033\[[0-9;]*m")

BANNER = r"""
  ██████╗  ██████╗ ██████╗ ████████╗
 ██╔════╝ ██╔═══██╗██╔══██╗╚══██╔══╝
 ██║      ██║   ██║██████╔╝   ██║
 ██║      ██║   ██║██╔══██╗   ██║
 ╚██████╗ ╚██████╔╝██║  ██║   ██║
  ╚═════╝  ╚═════╝ ╚═╝  ╚═╝   ╚═╝
"""


def paint(text: str, enabled: bool) -> str:
    """Sin ANSI si la salida no es una terminal o se pidió --no-color.

    Un archivo redirigido o una tubería no interpretan secuencias de escape: lo
    que vería quien abra el log sería basura entre el texto. Quitar los códigos
    no es quitar el texto — por eso se borran con una expresión y el resto
    queda tal cual. Devolver la cadena vacía aquí hacía desaparecer las barras
    de estado del log, que era justo lo que había que dejar.
    """
    return text if enabled else ANSI.sub("", text)


def banner(color: bool) -> str:
    return paint(VIOLET + BOLD, color) + BANNER + paint(RESET, color)


def bar(label: str, ok: bool, color: bool, note: str = "") -> str:
    """Una línea de estado: `● core        en 127.0.0.1:8765`."""
    dot = paint((GREEN if ok else RED) + "●", color)
    name = paint(BOLD + f"{label:<12}" + RESET, color)
    tail = paint(f"{DIM}{note}{RESET}", color) if note else ""
    return (" " + dot + " " + name + (" " + tail if tail else "")).rstrip()


def port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def pick_web_mode(serve: str) -> str:
    """`auto` elige dist si está construido, si no dev; `dist` y `dev` mandan."""
    if serve == "auto":
        return "dist" if (WEB / "dist" / "index.html").exists() else "dev"
    return serve


def npm_command(*args: str) -> list[str]:
    """En Windows `npm` es un .cmd y CreateProcess no lo encuentra por el nombre."""
    if os.name == "nt":
        return ["cmd", "/c", "npm", *args]
    return ["npm", *args]


def demo_db_path(env: dict[str, str]) -> str:
    """La ruta de la memoria de usar y tirar que pone `--demo`.

    Existe para que una captura de pantalla o una demo no escriban en la base
    real: quien enseña CORT no debería arriesgarse a dejarle recuerdos.
    """
    return str(Path(env.get("TMPDIR", "/tmp")) / "cort-demo.db")


def core_python() -> Path:
    """El intérprete del venv del proyecto, en el orden que lo escribe cada SO."""
    for candidate in (ROOT / ".venv" / "bin" / "python", ROOT / ".venv" / "Scripts" / "python.exe"):
        if candidate.exists():
            return candidate
    raise SystemExit(
        "No está el venv. Crea primero las dependencias:  make setup"
        "   (o en Windows:  py -m venv .venv && .venv\\Scripts\\pip install -r services/core/requirements.txt)"
    )


def ollama_alive(timeout: float = 0.6) -> bool:
    url = os.getenv("CORT_OLLAMA_URL", "http://localhost:11434") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except (urllib.error.URLError, OSError):
        return False


def models_available() -> list[str]:
    """Los modelos que tiene Ollama, para enseñarlos en la barra. [] si no hay."""
    url = os.getenv("CORT_OLLAMA_URL", "http://localhost:11434") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=1.5) as res:
            return [m["name"] for m in json.load(res).get("models", [])]
    except (urllib.error.URLError, OSError, KeyError, ValueError):
        return []


# `wpctl status` imprime secciones anidadas. Las entradas de dispositivo van
# numeradas (" *   35. Dummy Output   [vol: 1.00]"), y las cabeceras no.
_ENTRY = re.compile(r"^\s*[*!_]?\s*\d+\.\s+(.+?)\s*(?:\[[^\]]*\]\s*)?$")


def parse_wpctl(text: str) -> tuple[list[str], list[str]]:
    """Devuelve (salidas, entradas) de audio desde la salida de `wpctl status`.

    Recorta **sólo la sección `Audio`** a propósito: `Video` tiene sus propios
    apartados `Sinks:` y `Sources:`, y sus fuentes son las cámaras. Medido en
    esta máquina: dos cámaras en `Video → Sources` y **ninguna** entrada en
    `Audio → Sources`. Leer el texto entero diría que hay micrófono, y ahí es
    donde un «te escucho» sería una mentira.
    """
    audio = re.search(r"^\s*Audio\s*$", text, re.M)
    if not audio:
        return [], []
    rest = text[audio.end():]
    video = re.search(r"^\s*Video\s*$", rest, re.M)
    chunk = rest[: video.start()] if video else rest

    buckets: dict[str, list[str]] = {}
    current: list[str] | None = None
    for raw in chunk.splitlines():
        line = re.sub(r"[│├└─]", "", raw).strip()
        if not line:
            continue
        if line.endswith(":"):
            current = buckets.setdefault(line[:-1], [])
            continue
        m = _ENTRY.match(line)
        if m and current is not None:
            current.append(m.group(1))
    return buckets.get("Sinks", []), buckets.get("Sources", [])


def audio_probe() -> tuple[list[str], list[str]] | None:
    """(salidas, entradas) reales, o None si la sonda no puede afirmar nada.

    None hay en dos casos, y los dos callan la barra en vez de mentir: este SO no
    tiene `wpctl` (Windows y macOS piden otra sonda que aquí no está escrita), o
    `wpctl status` no contestó a tiempo. Lo segundo se vio en esta máquina: con
    el core arrancando, los dos segundos de margen no dieron abasto y la barra de
    audio desapareció de un arranque que promete siete. De ahí el margen de 5 s.
    """
    if not shutil.which("wpctl"):
        return None
    try:
        out = subprocess.run(["wpctl", "status"], capture_output=True, text=True,
                             timeout=5, errors="replace").stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_wpctl(out)


def audio_note(sinks: list[str], sources: list[str]) -> tuple[bool, str]:
    """Punto de estado y texto para la barra de audio.

    Un sink llamado *Dummy Output* no es un altavoz: es lo que PipeWire pone
    cuando no hay ningún dispositivo de salida. Contarlo como salida diría
    «audio listo» en una máquina muda — y ya se vio que `wpctl set-volume`
    responde 0 sobre él sin mover nada.
    """
    reales = [s for s in sinks if "dummy" not in s.lower()]
    salida = ", ".join(reales[:2]) if reales else (
        "ninguna real (Dummy Output)" if sinks else "ninguna")
    ok = bool(reales and sources)
    texto = f"{len(reales)} salida(s): {salida} · {len(sources)} entrada(s)"
    if not ok:
        texto += " — sin esto no hay voz que verificar"
    return ok, texto


def camera_probe() -> list[tuple[str, bool]]:
    """Las cámaras de vídeo del sistema como `(nombre, se_puede_abrir)`.

    Se mira `/dev/video*` y además el permiso real de esta usuaria: un
    `/dev/video0` que no se puede abrir es exactamente el mismo problema que no
    tener cámara, y decir «1 cámara» cuando luego el navegador no puede encenderla
    es el tipo de mentira que hace perder una tarde.
    """
    cams: list[tuple[str, bool]] = []
    for dev in sorted(Path("/dev").glob("video*")):
        try:
            usable = os.access(dev, os.R_OK | os.W_OK)
        except OSError:
            usable = False
        cams.append((dev.name, usable))
    return cams


def camera_note(cams: list[tuple[str, bool]]) -> tuple[bool, str]:
    """Punto de estado y texto para la barra de cámara.

    El aviso final no es relleno: quien abre la cámara es el navegador con
    `getUserMedia`, no el core. Que CORT la vea no quita el permiso que Chrome
    pide en la propia página, y conviene decirlo antes de que se busque el fallo
    en el sitio equivocado.
    """
    if not cams:
        return False, "sin /dev/video*: en Windows y macOS hace falta otra sonda (aún no escrita)"
    nombres = ", ".join(n for n, _ in cams)
    bloqueadas = [n for n, ok in cams if not ok]
    if bloqueadas:
        return False, f"{len(cams)} cámara(s): {nombres} — sin permiso en {', '.join(bloqueadas)}; añade tu usuario al grupo `video`"
    return True, f"{len(cams)} cámara(s): {nombres} · la abre el navegador desde la página, con permiso tuyo"


def memory_note(db: Path, count: int | None, demo: bool = False) -> tuple[bool, str]:
    """Punto de estado y texto para la barra de memoria.

    Que no exista la base no es una avería: es la primera vez que se enciende.
    Que exista y no se pueda leer sí lo es, y las dos cosas dan `count=None`, así
    que la barra mira el archivo antes de decir qué pasa.
    """
    tag = "  (demo)" if demo else ""
    if not db.exists():
        return True, f"sin recuerdos todavía: la base se crea al primero{tag}"
    if count is None:
        return False, f"hay base en {db.name} pero no se puede leer"
    return True, f"{count} recuerdos en {db.name}{tag}"


def memory_count(db: Path) -> int | None:
    """Cuántos recuerdos hay. None si la base no existe todavía."""
    if not db.exists():
        return None
    import sqlite3

    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    try:
        return conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    except sqlite3.Error:
        return None
    finally:
        conn.close()


class StaticHandler(http.server.SimpleHTTPRequestHandler):
    """Sirve apps/web/dist. Suficiente: la interfaz es una sola página sin rutas."""

    def log_message(self, *_args):
        pass  # El ruido de cada .js lo tapa la terminal; aquí no aporta nada.


def serve_static(directory: Path, port: int, host: str = "127.0.0.1") -> http.server.ThreadingHTTPServer:
    handler = lambda *a, **kw: StaticHandler(*a, directory=str(directory), **kw)  # noqa: E731
    srv = http.server.ThreadingHTTPServer((host, port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def stream(prefix: str, pipe, color: bool) -> None:
    """Pasa la salida de un hijo a la terminal, con su etiqueta de color."""
    tag = paint(f"{DIM}{prefix}{RESET} ", color)
    for line in iter(pipe.readline, ""):
        print(f" {tag}{line.rstrip()}", flush=True)
    pipe.close()


def load_dotenv() -> list[str]:
    """Lee `.env` **con el mismo código que el core**, no con una copia.

    El lanzador no puede `import cort_core` (esa carpeta no está en el `PYTHONPATH`
    y el lanzador no instala nada), así que se carga el módulo por su archivo. Lo
    que se evita aquí es el fallo clásico: dos parsers de `.env` que discrepan y
    un puerto que el lanzador cree uno y el servidor otro.
    """
    import importlib.util

    module = CORE / "cort_core" / "env.py"
    if not module.is_file():
        return []
    try:
        spec = importlib.util.spec_from_file_location("cort_dotenv", module)
        env_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(env_module)
        return env_module.load_env()
    except (OSError, RuntimeError, AttributeError):
        return []


def lan_address() -> str | None:
    """La IP que la red ve de esta máquina, o None si no tiene red.

    Se pregunta al socket de salida en vez de enumerar interfases: `connect` a
    una IP pública no envía ningún paquete, sólo hace que el kernel elija la
    interfase correcta. Así se evita imprimir la `127.0.0.1` o la dirección de
    un túnel VPN que el teléfono nunca va a alcanzar.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


# ── Que el teléfono encuentre a CORT sin teclear nada (divulgación por UDP) ───
#
# Dos datagramas en un puerto aparte, y ahí acaba el protocolo:
#
#   sonda      teléfono → broadcast  «CORT-ENCONTRARSO-1»
#   respuesta  portátil → teléfono    «CORT-AQUI-1|http://<ip>:<puerto>/?token=…»
#
# La respuesta **lleva la llave**, y eso es una decisión tomada con sus costes,
# no un descuido: hasta ahora el enlace había que leerlo en la pantalla del
# portátil y copiarlo en el teléfono, que es exactamente la fricción que la
# dueña pidió quitar («no puede iniciar con su animación como una IA normal»).
# Lo que se gana es cero tecleo. Lo que se expone es la llave a quien pregunte
# **desde dentro de la misma Wi-Fi** — el radio que `--lan` ya está aceptando al
# publicar el puerto, y el enlace ya viaja en claro por ese Wi-Fi sin HTTPS
# (decisión de Sandra, no ticket de código). Por eso hay tres frenos: se responde
# sólo con `--lan` puesto y modo `dist`, cada respuesta se imprime con la IP que
# la pidió, y `--sin-descubrimiento` (o `CORT_LAN_DISCOVER=0`) apaga el puerto.
DESCUBRIR = "CORT-ENCONTRARSO-1"
DESCUBRIR_RESPUESTA = "CORT-AQUI-1"
DESCUBRIR_PUERTO = 8781        # el 8780 es la página; éste es sólo el «¿estás ahí?»


def puerto_descubrimiento(env: dict[str, str]) -> int:
    """El puerto de divulgación: el que diga `CORT_DISCOVERY_PORT`, o 8781.

    Un valor que no sea un puerto útil **no** detiene CORT: se usa el de siempre.
    Es una comodidad de la LAN, no un interruptor de seguridad —el interruptor es
    la llave de red, y ésa no se toca—.
    """
    valor = (env.get("CORT_DISCOVERY_PORT") or "").strip()
    if valor.isdigit() and 1 <= int(valor) <= 65535:
        return int(valor)
    return DESCUBRIR_PUERTO


def sonda_valida(datos: bytes) -> bool:
    """¿Es esta pregunta de CORT, o tráfico cualquiera del vecindario?

    El socket escucha en `0.0.0.0`: escáneres, impresoras y routers van a caer
    aquí. Se compara la mágica exacta antes del primer espacio —la sonda puede
    traer un nonce detrás, y un datagrama de tres bytes no merece una respuesta—.
    """
    if not datos:
        return False
    return datos.decode("utf-8", "replace").split(" ")[0] == DESCUBRIR


def respuesta_descubrimiento(enlace: str) -> bytes:
    """El datagrama con el que CORT se da a conocer; vacío si no hay enlace.

    Vacío es también la forma de decir «no hay nada que responder»: sin `--lan`
    publicado no existe un enlace que abrir desde el teléfono, y el bucle lo
    comprueba antes de contestar.
    """
    if not enlace:
        return b""
    return f"{DESCUBRIR_RESPUESTA}|{enlace}".encode("utf-8")


def abrir_descubrimiento(puerto: int) -> tuple[socket.socket | None, str | None]:
    """El UDP escuchando en `0.0.0.0:puerto`, o el motivo por el que no.

    `SO_REUSEADDR` porque al reiniciar CORT dos veces seguidas el socket anterior
    puede seguir en `TIME_WAIT`; si aun así el puerto está ocupado, el lanzador
    lo dice **una vez** y sigue andando: el teléfono siempre puede pegar el enlace,
    que es el camino de siempre y no se ha quitado.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", puerto))
    except OSError as error:
        sock.close()
        return None, f"puerto {puerto} ocupado ({error.strerror})"
    return sock, None


def bucle_descubrimiento(sock: socket.socket, enlace: str, parada: threading.Event,
                         avisa) -> None:
    """Atende sondas hasta que `parada` se marque. Corre en su propio hilo.

    El socket viene de fuera a propósito: así el lazo se puede probar en
    `127.0.0.1` con un puerto libre, sin tocar la Wi-Fi de esta máquina. `avisa`
    se llama **después** de responder, con la IP de quien preguntó — es el registro
    de «a quién le di la llave», y se imprime en la terminal del arranque—.
    """
    sock.settimeout(0.5)
    while not parada.is_set():
        try:
            datos, origen = sock.recvfrom(256)
        except socket.timeout:
            continue
        except OSError:
            return                      # socket cerrado al apagar: salida limpia
        if not sonda_valida(datos):
            continue
        mensaje = respuesta_descubrimiento(enlace)
        if not mensaje:
            continue
        try:
            sock.sendto(mensaje, origen)
        except OSError:
            return
        avisa(origen[0])


def rechazo_de_red(lan: bool, token: str | None) -> str | None:
    """El motivo por el que `--lan` no debe abrir el puerto, o `None` si se puede.

    Función aparte y sin `print` porque es la única decisión de seguridad que
    toma el lanzador, y tiene que poder probarse sin arrancar un servidor. El
    criterio es el mismo que el del core (`cort_core/security.py`), y si algún
    día discrepan gana el del core: él es el que está escuchando.

    Desde `v0.14.0` esta es la **última** barrera, no la primera: la llave que
    falte se crea sola (`llave_de_red`) antes de llegar aquí, así que este motivo
    sólo se imprime si el `.env` no se puede escribir o si alguien borra la
    variable a la vez que falla el disco. La regla no ha cambiado —sin secreto
    no se publica—; lo que cambió es quién la escribe.
    """
    if not lan or (token or "").strip():
        return None
    return "--lan cancelado: no hay CORT_LAN_TOKEN en el .env y no se pudo crear."


def verdad(valor: str | None) -> bool:
    """Lo que una persona escribe en un `.env` para decir «sí»."""
    return (valor or "").strip().lower() in {"1", "true", "si", "sí", "on", "y", "yes"}


def asegurar_token_lan(file: Path, largo: int = 18) -> tuple[str, str | None]:
    """Genera la llave de red, la escribe en `.env` y devuelve `(token, None)`.

    Existe porque el muro que veía la dueña era este: encender el teléfono
    pedía editar un archivo de configuración a mano, y una pantalla roja de
    terminal no es la cara de un asistente. **La protección sigue entera** —lo
    que se quitó es el tecleo—: la llave sale de `secrets`, queda en el `.env`
    (fuera del repo, regla 7) y el core la sigue exigiendo en cada conexión.

    Devuelve `("", motivo)` si el archivo no se puede escribir, en vez de abrir
    el puerto con una llave que sólo vive en la memoria de este proceso: al
    reiniciar, nadie sabría el enlace y el teléfono se quedaría otra vez fuera.
    """
    token = secrets.token_urlsafe(largo)
    bloque = (f"\n# Llave de red que CORT creó solo al pedir `--lan` "
              f"({time.strftime('%Y-%m-%d')}).\n"
              f"# Puedes cambiarla por otra de 20 caracteres o más; el enlace que\n"
              f"# imprime el arranque ya lleva esta. Si la borras, se crea otra.\n"
              f"CORT_LAN_TOKEN={token}\n")
    try:
        previo = file.read_text(encoding="utf-8", errors="replace") if file.is_file() else ""
        with file.open("a", encoding="utf-8") as handle:
            # Sin el salto extra, un `.env` que no termine en retorno de carro
            # pegar la llave al final de la última línea y la dejaría inservible.
            handle.write(bloque if not previo or previo.endswith("\n") else "\n" + bloque)
        os.chmod(file, 0o600)   # es un secreto: que no lo lea nadie más de la máquina
    except OSError as error:
        return "", f"--lan cancelado: no se pudo escribir la llave en {file} ({error})."
    return token, None


def llave_de_red(lan: bool, env_file: Path,
                 environ: dict[str, str] | None = None) -> tuple[str, str | None, bool]:
    """La llave con la que se abre el puerto: `(token, motivo, creada_ahora)`.

    Se prueba sin tocar el disco: el `environ` se pasa a mano en las pruebas para
    comprobar que una variable ya exportada manda y no se genera otra encima.
    """
    env = os.environ if environ is None else environ
    token = (env.get("CORT_LAN_TOKEN") or "").strip()
    if not lan or token:
        return token, None, False
    nuevo, motivo = asegurar_token_lan(env_file)
    if motivo is None:
        env["CORT_LAN_TOKEN"] = nuevo
    return nuevo, motivo, motivo is None


def main() -> int:
    # Antes que nada: `--port` toma su valor por defecto del entorno, y el entorno
    # puede venir del `.env`. Si se lee tarde, el lanzador comprueba un puerto
    # mientras el core escucha en otro.
    added_keys = load_dotenv()

    ap = argparse.ArgumentParser(description="Arranca CORT (core + interfaz + navegador).")
    ap.add_argument("--port", type=int, default=int(os.getenv("CORT_PORT", "8765")))
    ap.add_argument("--web-port", type=int, default=8780, help="puerto del servidor estático")
    ap.add_argument("--serve", choices=["auto", "dist", "dev"], default="auto")
    ap.add_argument("--no-browser", action="store_true", help="no abre el navegador")
    ap.add_argument("--quiet", action="store_true", help="sin banner ni salida de los hijos")
    ap.add_argument("--demo", action="store_true",
                    help="memoria de usar y tirar: no escribe en la base real")
    ap.add_argument("--lan", dest="lan", action="store_true", default=None,
                    help="publica la interfaz en la red local (para abrir CORT desde el móvil)")
    ap.add_argument("--sin-lan", dest="lan", action="store_false",
                    help="aunque el .env pida la red, quédate en 127.0.0.1")
    ap.add_argument("--sin-descubrimiento", dest="descubrir", action="store_false",
                    default=True,
                    help="no contestar por UDP a quien pregunte por CORT en la Wi-Fi")
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args()

    # `CORT_LAN=1` en el `.env` equivale a escribir `--lan`: el doble clic del
    # escritorio no lleva banderas, y la dueña no puede estar recordando una.
    # Con `default=None` el lanzador distingue «no lo puso» de «dijo que no»,
    # que es lo que hace falta para respetar `--sin-lan`.
    if args.lan is None:
        args.lan = verdad(os.getenv("CORT_LAN", ""))

    color = sys.stdout.isatty() and not args.no_color and not args.quiet
    # Sin esto, con la salida redirigida a un archivo stdout búferes de bloque:
    # las barras de estado se quedaban escritas en memoria y se perdían al
    # recibir la señal de cierre. Línea a línea siempre llegan al log.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    if not args.quiet:
        print(banner(color))
        if added_keys:
            # Sólo los NOMBRES de las variables, nunca sus valores: una terminal
            # de arranque acaba en una captura, y una captura acaba en un chat.
            some = ", ".join(added_keys[:6]) + (" …" if len(added_keys) > 6 else "")
            print(paint(f" {DIM}.env → {some}{RESET}", color))

    if args.demo:
        os.environ["CORT_MEMORY_DB"] = demo_db_path(os.environ)
    db = Path(os.getenv("CORT_MEMORY_DB", DATA / "memory.db"))

    token, motivo, creada = llave_de_red(args.lan, ROOT / ".env")
    motivo = motivo or rechazo_de_red(args.lan, token)
    if motivo:
        # `--lan` sin llave **y sin poder crearla** no se abre, y el lanzador se
        # niega en vez de levantar el puerto "y ya veremos". El motivo es concreto:
        # por ese WebSocket se puede cambiar el volumen, abrir aplicaciones y
        # capturar la pantalla de esta máquina. Quien lo publica sin secreto le está
        # prestando el PC a todo el Wi-Fi, y eso no puede ser consecuencia de una
        # variable que nadie puso.
        print(paint(f"\n{RED}{motivo}{RESET}", color))
        print(paint(f" {DIM}Escribe tú la línea en {ROOT / '.env'} —un secreto de 20 "
                    f"caracteres o más— o arregla el permiso del archivo:{RESET}", color))
        print(paint(f"   {CYAN}CORT_LAN_TOKEN=…{RESET}", color))
        print(paint(f" {DIM}Sin eso el core sigue en 127.0.0.1: arráncalo con --sin-lan si el "
                    f"teléfono no hace falta.{RESET}", color))
        return 1
    if creada and not args.quiet:
        # Se avisa, pero sin imprimir el valor: la barra `red` de abajo ya da el
        # enlace completo con la llave, y un secreto en la terminal es un secreto
        # que acaba en una captura (la misma razón de la nota del `.env`).
        print(paint(f" {DIM}llave de red: CORT la creó sola y la guardó en "
                    f"{ROOT / '.env'} — no vuelve a pedirla{RESET}", color))

    children: list[subprocess.Popen] = []
    salida = threading.Lock()   # la terminal la escribe también el hilo UDP
    # El hilo de divulgación (UDP) se apaga con todo lo demás. Se declaran aquí,
    # vacíos, para que `shutdown()` pueda nombrarlos aunque el arranque falle antes
    # de abrir el puerto: un `NameError` al limpiar sería una pantalla de Error de
    # Windows en la cara de la dueña, que es justo lo que este lanzador evitó.
    divulgar_parada: threading.Event | None = None
    divulgar_sock: socket.socket | None = None

    def shutdown() -> None:
        if divulgar_parada is not None:
            divulgar_parada.set()
        if divulgar_sock is not None:
            divulgar_sock.close()
        for proc in children:
            if proc.poll() is None:
                proc.terminate()
        for proc in children:
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

    env = {**os.environ, "CORT_PORT": str(args.port)}
    # Con `--lan` el core pasa a escuchar en todas las interfases. Se lo dice por
    # entorno y no por un argumento nuevo: `server.py` ya lee `CORT_HOST`, así que
    # el lanzador no tiene que saber cómo se arranca uvicorn.
    if args.lan:
        env["CORT_HOST"] = "0.0.0.0"
    out = subprocess.DEVNULL if args.quiet else subprocess.PIPE
    core = subprocess.Popen([str(core_python()), "-m", "cort_core.server"],
                            cwd=CORE, env=env, stdout=out, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    children.append(core)
    if not args.quiet:
        threading.Thread(target=stream, args=("[core]", core.stdout, color), daemon=True).start()

    for _ in range(60):
        if port_open("127.0.0.1", args.port):
            break
        if core.poll() is not None:
            print(paint(f"{RED}El core murió al arrancar (código {core.returncode}).{RESET}", color))
            return 1
        time.sleep(0.25)

    mode = pick_web_mode(args.serve)
    url = f"http://127.0.0.1:{args.port}"
    if mode == "dist":
        # Con `--lan` el servidor estático también se publica: de nada sirve un
        # core accesible si la página sigue escuchando sólo para esta máquina.
        serve_static(WEB / "dist", args.web_port, "0.0.0.0" if args.lan else "127.0.0.1")
        url = f"http://127.0.0.1:{args.web_port}"
    else:
        if not (WEB / "node_modules").exists():
            print(paint(f"{RED}Faltan las dependencias de la interfaz.{RESET}", color)
                  + "  make web-deps")
            shutdown()
            return 1
        web = subprocess.Popen(npm_command("run", "dev"), cwd=WEB, env=env,
                               stdout=out, stderr=subprocess.STDOUT, text=True,
                               encoding="utf-8", errors="replace")
        children.append(web)
        if not args.quiet:
            threading.Thread(target=stream, args=("[web]", web.stdout, color), daemon=True).start()
        for _ in range(120):
            if port_open("127.0.0.1", 5173):
                break
            time.sleep(0.25)
        url = "http://localhost:5173/"

    # ── El teléfono pregunta y CORT contesta ───────────────────────────────────
    # La IP y el enlace se calculan **una vez**, y fuera del bloque de la terminal:
    # con `--quiet` — el doble clic sin consola — el teléfono tiene que seguir
    # encontrando a CORT solo, y lo que se divulga tiene que ser literalmente el
    # mismo enlace que se imprime. Vite en dev escucha sólo en `127.0.0.1`: con
    # `--serve dev` no hay enlace que divulgar, y el bucle no se abre.
    ip_lan = lan_address() if args.lan else None
    enlace_lan = (f"http://{ip_lan}:{args.web_port}/?token={token}"
                  if ip_lan and mode == "dist" else "")
    motivo_udp = ""
    if args.lan and args.descubrir and enlace_lan and verdad(os.getenv("CORT_LAN_DISCOVER", "1")):
        sock_udp, motivo = abrir_descubrimiento(puerto_descubrimiento(os.environ))
        if sock_udp is None:
            motivo_udp = motivo or "puerto de divulgación sin abrir"
        else:
            divulgar_sock = sock_udp
            divulgar_parada = threading.Event()

            def quien_pregunta(ip: str) -> None:
                # El registro de «a quién le di la llave». Se imprime con la IP de
                # la propia red de la casa: no va a ningún sitio, pero sí a la
                # terminal, donde se ve si alguien que no es su teléfono está
                # preguntando.
                if args.quiet:
                    return
                with salida:
                    print(paint(f" {DIM}[red] {ip} preguntó por CORT: se le dio el "
                                f"enlace con su llave{RESET}", color))

            threading.Thread(target=bucle_descubrimiento,
                             args=(sock_udp, enlace_lan, divulgar_parada, quien_pregunta),
                             daemon=True).start()

    if not args.quiet:
        models = models_available() if ollama_alive() else []
        ready_mem, mem_note = memory_note(db, memory_count(db), args.demo)
        print()
        print(bar("core", True, color, f"ws://127.0.0.1:{args.port}/ws"))
        print(bar("interfaz", True, color, url + f"   ({'dist' if mode == 'dist' else 'vite dev'})"))
        print(bar("ollama", bool(models), color,
                  ", ".join(models[:4]) if models else "apagado — CORT responde en modo eco"))
        print(bar("memoria", ready_mem, color, mem_note))
        audio = audio_probe()
        if audio is not None:
            ok_audio, note_audio = audio_note(*audio)
            print(bar("audio", ok_audio, color, note_audio))
        ok_cam, note_cam = camera_note(camera_probe())
        print(bar("camara", ok_cam, color, note_cam))
        if args.lan:
            # La IP que vería el teléfono. Si no se imprime, el `--lan` no sirve:
            # la usuaria no puede adivinar su propia dirección.
            notes = {"dist": f"el móvil abre {enlace_lan}",
                     "dev": "interfaz en modo dev: el móvil verá el core, pero no la página — usa --serve dist"}
            print(bar("red", bool(enlace_lan), color,
                      notes[mode] if ip_lan else "sin IP de red: el teléfono no podrá entrar"))
            if enlace_lan:
                # La frase de uso, sin repetir el secreto: la llave ya viajó una vez
                # arriba y cada copia extra en pantalla es una captura más donde vive.
                if divulgar_parada is not None:
                    print(paint(f" {DIM}↳ el APK abre CORT solo: pregunta por UDP en el "
                                f"puerto {puerto_descubrimiento(os.environ)} y esta máquina "
                                f"contesta con su enlace. No hay que pegar nada la primera "
                                f"vez.{RESET}", color))
                    print(paint(f" {DIM}   (se apaga con --sin-descubrimiento o "
                                f"CORT_LAN_DISCOVER=0; quien pregunte queda impreso "
                                f"arriba){RESET}", color))
                else:
                    print(paint(f" {DIM}↳ pega eso, ENTERO, en la app la primera vez: viaja en "
                                f"claro por tu Wi-Fi (no hay HTTPS) y la app lo guarda."
                                f"{(' Divulgación UDP: ' + motivo_udp) if motivo_udp else ''}"
                                f"{RESET}", color))
        print()
        print(paint(f" {CYAN}{BOLD}CORT en línea{RESET}   Ctrl+C para cerrar todo.", color))
        print(paint(f" {DIM}{'─' * 58}{RESET}", color))

    if not args.no_browser:
        webbrowser.open(url)

    try:
        while core.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        if not args.quiet:
            print(paint(f"\n {DIM}cerrando…{RESET}", color))
    finally:
        shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
