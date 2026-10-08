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
    """(salidas, entradas) reales, o None si este SO no tiene `wpctl`.

    None no se pinta como «sin audio»: en Windows y macOS la sonda es otra y
    aquí no se ha escrito. Silenciar la barra es la única salida honesta.
    """
    if not shutil.which("wpctl"):
        return None
    try:
        out = subprocess.run(["wpctl", "status"], capture_output=True, text=True,
                             timeout=2, errors="replace").stdout
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


def serve_static(directory: Path, port: int) -> http.server.ThreadingHTTPServer:
    handler = lambda *a, **kw: StaticHandler(*a, directory=str(directory), **kw)  # noqa: E731
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
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
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args()

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

    children: list[subprocess.Popen] = []

    def shutdown() -> None:
        for proc in children:
            if proc.poll() is None:
                proc.terminate()
        for proc in children:
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()

    env = {**os.environ, "CORT_PORT": str(args.port)}
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
        serve_static(WEB / "dist", args.web_port)
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
