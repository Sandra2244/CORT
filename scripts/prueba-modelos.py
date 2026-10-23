"""Prueba decisiva del gestor de modelos (F13), SIN red, SIN Ollama y SIN tocar
los datos de la dueña.

Qué se comprueba, y por qué cada una de estas comprobaciones existía:

  1. **El módulo vive sin `psutil`.** Se importaba en cabecera y, si el equipo no
     lo tenía, `import models` reventaba y con él TODAS las rutas `/api/models*`
     (el runner de Actions ya lo sufrió: run 39879890814). Aquí se importa con un
     bloqueador de `sys.meta_path` y se exige que siga funcionando y que diga
     «sin medir» en vez de inventarse el veredicto.
  2. **Ollama se levanta escuchando la red.** El motivo nº 1 de «no descarga los
     modelos» desde el teléfono: `ollama serve` arrancaba con el entorno de
     siempre y se quedaba en `127.0.0.1`. Se comprueba el `env` que se le pasa de
     verdad a `Popen`, que el mando `ollama_red` en `falso` sí llega al servidor,
     y que si la dueña ya puso su `OLLAMA_HOST` no se le pisa.
  3. **La dirección que se enseña es la que responde.** `info_red()` tiene que
     decir la IP real, si se ve desde fuera, y el motivo exacto cuando no. Y
     `visible_en_red()` no puede estar llamando a internet: con Ollama apagado se
     corta antes de importar `requests` (el stub lo cacaría).
  4. **El disco se mira antes de lanzar**, no a medias bajada, y un modelo que no
     está en el catálogo NO se negativea (no podemos prometer un peso que no
     medimos, tampoco un fallo que no ocurrió).

Nada de esto abre `~/.cort` real ni arranca un servidor de verdad: `CORT_HOME` se
apunta a una caja temporal, y `binario`, `corriendo`, `ip_local`, `subprocess`,
`threading` y `time` se sustituyen por gemelos del taller.

Uso:  python3 scripts/prueba-modelos.py     (un segundo)
"""
from __future__ import annotations

import contextlib
import os
import pathlib
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "backend" / "app"

# La casa de CORT se va a una caja temporal ANTES de importar nada: si algún
# módulo leyera `~/.cort` real, esta prueba no la toca.
CAJA = tempfile.TemporaryDirectory(prefix="cort-prueba-modelos-")
os.environ["CORT_HOME"] = CAJA.name

FALLOS = []


def dice_ok(que, como):
    print(f"  ok   {que:46} {como}")


def falla(que, como):
    FALLOS.append(que)
    print(f"  FALLA {que:46} {como}")


def espero(que, obtenido, querido):
    if obtenido == querido:
        dice_ok(que, repr(obtenido)[:60])
    else:
        falla(que, f"dio {obtenido!r} y tenía que dar {querido!r}")


def cumple(que, obtenido, prueba):
    if prueba(obtenido):
        dice_ok(que, repr(obtenido)[:60])
    else:
        falla(que, f"dio {obtenido!r}, y eso no pasa la prueba")


# ── 1 · el módulo sin `psutil` (en un proceso aparte: es al importar) ──────────
print("\n· psutil opcional: el gestor vive sin él")
GUION_SIN_PSUTIL = r"""
import sys
class Bloquea:
    def find_spec(self, nombre, ruta=None, objetivo=None):
        if nombre == 'psutil':
            raise ImportError('psutil no está, como en una instalación sin .venv')
        return None
sys.meta_path.insert(0, Bloquea())
sys.path.insert(0, sys.argv[1])
import models
print('PSUTIL', models.psutil)
print('RAM', models.ram_total_gb(), models.ram_libre_gb())
print('VEREDICTO', models.veredicto(models.POR_NOMBRE['qwen2.5:0.5b'])['estado'])
# para mirar /proc de verdad y no matarle a ella un Ollama que esté sonando
models._procs_ollama_sin_psutil = lambda: []
print('CIERRE', models.detener_servidor()['via'])
"""
with tempfile.TemporaryDirectory(prefix="cort-sin-psutil-") as caja:
    import subprocess
    entorno = dict(os.environ)
    entorno.pop("PYTHONSTARTUP", None)
    entorno["CORT_HOME"] = caja
    r = subprocess.run([sys.executable, "-c", GUION_SIN_PSUTIL, str(BACKEND)],
                       capture_output=True, text=True, timeout=60, env=entorno)
salida = r.stdout or ""
if r.returncode != 0:
    falla("models se importa sin psutil",
          f"el proceso murió: {(salida or r.stderr)[-200:]!r}")
else:
    dice_ok("models se importa sin psutil", "exit 0")
    espero("models.psutil es None sin el paquete", "PSUTIL None" in salida, True)
espero("las dos RAM dan 0,0 en vez de reventar", "RAM 0.0 0.0" in salida, True)
espero("el veredicto NO se inventa", "VEREDICTO sin medir" in salida, True)
espero("detener_servidor tiene ruta por /proc", "CIERRE /proc" in salida, True)

# y con `psutil` presente (el caso normal de este portátil) tiene que medir de
# verdad. Se comprueba la COHERENCIA, no un número fijo, porque esta suite se
# corre también en el runner de Actions, donde `psutil` NO está instalado (fue lo
# que mató el run 39879890814): un verde que dependiera del equipo donde corre
# no es un verde.
sys.path.insert(0, str(BACKEND))
import models          # noqa: E402

cumple("la RAM se mide si y sólo si hay psutil",
       (models.ram_total_gb(), models.psutil),
       lambda v: (v[0] > 0) == (v[1] is not None))


# ── los gemelos del taller ────────────────────────────────────────────────────
def con(**gemelos):
    """Pone gemelos en `models` y los quita al salir, aunque el cuerpo explote."""
    viejos = {k: getattr(models, k, None) for k in gemelos}
    for k, v in gemelos.items():
        setattr(models, k, v)
    try:
        yield
    finally:
        for k, v in viejos.items():
            setattr(models, k, v)


con = contextlib.contextmanager(con)


def sin_romperse(que, hacer, por=None):
    """Llama y devuelve el resultado. Si el código de `models` revienta, esto
    apunta el fallo CON NOMBRE en vez de dejar la suite con un traceback a medias:
    así cada mutación del taller dice qué comprobación era la que faltaba.

    `por` es el valor de relleno para que las líneas de después no mueran por un
    `KeyError` cuando el fallo ya está apuntado.
    """
    try:
        return hacer()
    except Exception as e:
        falla(que, f"el código reventó: {type(e).__name__}: {e}")
        return {} if por is None else por


class OllamaFalso:
    """`corriendo()` con memoria: despierta cuando le pasan un `Popen`, como el
    servidor de verdad. Sin esto no se puede probar el `env` de arrancar, porque
    con `corriendo` siempre `True` la función sale antes y no lanza nada."""

    def __init__(self, despierto=False):
        self.levantado = despierto
        self.popen = []           # lo que se le pasó a `Popen`, por si alguien lo mira

    def corriendo(self):
        return self.levantado

    def Popen(self, args, env=None, **kw):
        self.popen.append({"args": args, "env": env or {}})
        self.levantado = True


class HiloFalso:
    """Anota los hilos que se apuntan pero NO los corre: aquí no se baja nada."""

    def __init__(self):
        self.usados = 0

    class _Hilo:
        def __init__(self, target=None, args=(), daemon=False):
            pass

        def start(self):
            pass

    def Thread(self, *a, **k):
        self.usados += 1
        return HiloFalso._Hilo()


class SubprocessFalso:
    """Gemelo del módulo `subprocess`, sólo con lo que usa `models` a la hora de
    correr; `DEVNULL` tiene que existir porque se le pasa al `Popen` real."""
    DEVNULL = -3

    def __init__(self, ollama):
        self.ollama = ollama

    def Popen(self, *a, **k):
        return self.ollama.Popen(*a, **k)


class TimeFalso:
    """`sleep` no duerme (la prueba tarda un segundo) y `time` sigue siendo real."""

    def __init__(self):
        import time as reloj
        self._tiempo = reloj.time

    def sleep(self, _):
        pass

    def time(self):
        return self._tiempo()


# ── 2 · la red: lo que ve el teléfono ─────────────────────────────────────────
print("\n· la red: Ollama tiene que escuchar fuera de este equipo")
espero("por defecto quiere la red", models.quiere_red(), True)
espero("y el host que levanta es 0.0.0.0", models.host_sirve(), "0.0.0.0:11434")

with con(quiere_red=lambda: False):
    espero("con `ollama_red` apagado escucha solo en casa",
           models.host_sirve(), "127.0.0.1:11434")

# …y el mando tiene que LLEGAR, no sólo estar escrito. `config_store.raw()`
# devuelve solamente las claves que están en su tabla `DEFAULTS`, y `set_value`
# rechaza las que no: si `ollama_red` se queda fuera de esa lista, la dueña lo
# pone en Ajustes y aquí nadie lo lee. Se escribe el JSON de verdad en la caja de
# arena (con `CORT_HOME` ya apuntado a otra parte, línea arriba).
import config_store                                    # noqa: E402

ESPEJO = config_store.FILE
with tempfile.TemporaryDirectory(prefix="cort-mando-") as caja:
    config_store.FILE = pathlib.Path(caja) / "cort_config.json"
    try:
        espero("sin escribir nada: la red abierta", models.quiere_red(), True)
        espero("`set_value` acepta `ollama_red`",
               config_store.set_value("ollama_red", "no"), True)
        espero("y `raw()` se lo devuelve a `quiere_red()`",
               config_store.raw().get("ollama_red"), "no")
        espero("`ollama_red` = «no» apaga la red", models.quiere_red(), False)
        config_store.set_value("ollama_red", "1")
        espero("y volver a abrirlo también obedece", models.quiere_red(), True)
    finally:
        config_store.FILE = ESPEJO

BINARIO = "/usr/local/bin/ollama"
IP = "192.168.100.171"

# (a) con Ollama apagado: se levanta CON el host de red en su entorno
os.environ.pop("OLLAMA_HOST", None)
apagado = OllamaFalso(despierto=False)
hilos = HiloFalso()
with con(binario=lambda: BINARIO, corriendo=apagado.corriendo,
         subprocess=SubprocessFalso(apagado), threading=hilos, time=TimeFalso(),
         ip_local=lambda: IP, visible_en_red=lambda: True,
         quiere_red=lambda: True, info_red=lambda: {"url": f"http://{IP}:11434"}):
    r = sin_romperse("arrancar con Ollama apagado", lambda: models.arrancar_servidor())
espero("con Ollama apagado sí se lanza UN servidor", len(apagado.popen), 1)
espero("arrancar pasa OLLAMA_HOST de red al servidor",
       [a["env"].get("OLLAMA_HOST") for a in apagado.popen], ["0.0.0.0:11434"])
espero("y dice por dónde quedó escuchando", r.get("detalle"),
       "Ollama encendido en 0.0.0.0:11434")

# (b) el mando de ella llega al servidor, no sólo a la pantalla
apagado = OllamaFalso(despierto=False)
with con(binario=lambda: BINARIO, corriendo=apagado.corriendo,
         subprocess=SubprocessFalso(apagado), threading=hilos, time=TimeFalso(),
         ip_local=lambda: IP, visible_en_red=lambda: False,
         quiere_red=lambda: False, info_red=lambda: {"url": ""}):
    sin_romperse("arrancar con `ollama_red` en falso", lambda: models.arrancar_servidor())
espero("`ollama_red` en falso escucha sólo en casa",
       [a["env"].get("OLLAMA_HOST") for a in apagado.popen], ["127.0.0.1:11434"])

# (c) si la dueña ya puso el suyo, no se le pisa
apagado = OllamaFalso(despierto=False)
viejo_host = os.environ.get("OLLAMA_HOST")
os.environ["OLLAMA_HOST"] = "0.0.0.0:11999"
try:
    with con(binario=lambda: BINARIO, corriendo=apagado.corriendo,
             subprocess=SubprocessFalso(apagado), threading=hilos, time=TimeFalso(),
             ip_local=lambda: IP, visible_en_red=lambda: True,
             quiere_red=lambda: True, info_red=lambda: {"url": ""}):
        sin_romperse("arrancar respetando su host", lambda: models.arrancar_servidor())
finally:
    if viejo_host is None:
        os.environ.pop("OLLAMA_HOST", None)
    else:
        os.environ["OLLAMA_HOST"] = viejo_host
espero("respeta el OLLAMA_HOST que ella ya puso",
       [a["env"].get("OLLAMA_HOST") for a in apagado.popen], ["0.0.0.0:11999"])

# (d) si ya estaba en marcha, NO se lanza un segundo servidor
despierto = OllamaFalso(despierto=True)
with con(binario=lambda: BINARIO, corriendo=despierto.corriendo,
         subprocess=SubprocessFalso(despierto), threading=hilos, time=TimeFalso(),
         ip_local=lambda: IP, visible_en_red=lambda: True,
         quiere_red=lambda: True, info_red=lambda: {"url": f"http://{IP}:11434"}):
    r = sin_romperse("arrancar con Ollama despierto", lambda: models.arrancar_servidor())
espero("con Ollama despierto no arranca otro", despierto.popen, [])
espero("y dice que ya estaba", r.get("ya"), True)

# ── 3 · lo que se escribe en pantalla tiene que ser lo que ocurre ─────────────
print("\n· info_red: la dirección que se enseña es la que responde")
with con(ip_local=lambda: "", corriendo=lambda: False):
    r = sin_romperse("info_red sin IP", lambda: models.info_red())
espero("sin IP: manda conectar el Wi-Fi", "conéctalo a la Wi-Fi" in r.get("nota", ""), True)
espero("sin IP: no hay url que copiar", r.get("url"), "")

with con(ip_local=lambda: IP, corriendo=lambda: False, visible_en_red=lambda: False):
    r = sin_romperse("info_red con Ollama apagado", lambda: models.info_red())
espero("apagado: lo dice en vez de dar una url vacía",
       "Ollama está apagado" in r.get("nota", ""), True)
espero("apagado: la url sí es la suya", r.get("url"), f"http://{IP}:11434")

with con(ip_local=lambda: IP, corriendo=lambda: True, visible_en_red=lambda: True):
    r = sin_romperse("info_red visible", lambda: models.info_red())
espero("visible: dice que el teléfono la puede usar", "se ve desde la Wi-Fi" in r.get("nota", ""), True)
espero("visible: `visible` viaja en el JSON", r.get("visible"), True)

with con(ip_local=lambda: IP, corriendo=lambda: True, visible_en_red=lambda: False,
         **{"quiere_red": lambda: True}):
    r = sin_romperse("info_red mudo", lambda: models.info_red())
espero("mudo: culpa al cortafuegos, no al aire", "cortafuegos" in r.get("nota", ""), True)

with con(ip_local=lambda: IP, corriendo=lambda: True, visible_en_red=lambda: False,
         **{"quiere_red": lambda: False}):
    r = sin_romperse("info_red con el mando cerrado", lambda: models.info_red())
espero("y si fue ella quien lo cerró, lo dice", "`ollama_red` está apagado" in r.get("nota", ""), True)

# `visible_en_red` no puede ni tocar la red con Ollama apagado: si lo hiciera, el
# stub de `requests` lo avisa. El aviso hereda de `BaseException` y NO de
# `Exception` a propósito: dentro de la función hay un `except Exception` que se
# tragaría un AssertionError y la prueba daría verde con el código roto.
class SeSaleALaRed(BaseException):
    pass


@contextlib.contextmanager
def sin_requests():
    class Prohibido:
        def get(self, *a, **k):
            raise SeSaleALaRed("pidió /api/tags por la red")

    viejo = sys.modules.get("requests")
    sys.modules["requests"] = Prohibido()
    try:
        yield
    finally:
        if viejo is None:
            sys.modules.pop("requests", None)
        else:
            sys.modules["requests"] = viejo


with con(ip_local=lambda: IP, corriendo=lambda: False):
    with sin_requests():
        try:
            espero("sin Ollama no se sale a la red a preguntarse",
                   models.visible_en_red(), False)
        except SeSaleALaRed as salida_a_la_red:
            falla("sin Ollama no se sale a la red a preguntarse",
                  f"con Ollama apagado {salida_a_la_red} en vez de responder False")

cumple("ip_local real devuelve IPv4 o nada", models.ip_local(),
       lambda v: v == "" or all(p.isdigit() and 0 <= int(p) < 256 for p in v.split(".")))

# ── 4 · el sitio del disco, antes de lanzar ───────────────────────────────────
print("\n· disco: se mide antes de bajar, no a medias")
hilos = HiloFalso()
with con(threading=hilos, time=TimeFalso()):
    with con(binario=lambda: BINARIO, disco_libre_gb=lambda: 0.5,
             corriendo=lambda: True):
        r = sin_romperse("descargar sin sitio", lambda: models.descargar("llama3.1:8b"))
    espero("no cabe: no se lanza la descarga", r.get("ok"), False)
    cumple("no cabe: el error dice los bytes", r.get("error", ""),
           lambda v: "no cabe en el disco" in v and "4.9" in v and "0.5" in v)
    espero("no cabe: no hubo hilo de descarga", hilos.usados, 0)
    espero("no cabe: la fila quedó vacía", "llama3.1:8b" in models.PULLS, False)

    with con(binario=lambda: BINARIO, disco_libre_gb=lambda: 220.0,
             corriendo=lambda: True):
        r = sin_romperse("descargar con sitio", lambda: models.descargar("qwen2.5:0.5b"))
    espero("con sitio de sobra sí se apunta", r.get("ok"), True)
    espero("y su barra empieza en cero", (models.PULLS.get("qwen2.5:0.5b") or {}).get("pct"), 0)
    espero("el hilo de la bajada se apuntó", hilos.usados, 1)
    models.PULLS.pop("qwen2.5:0.5b", None)

    # un modelo que no está en el catálogo medido NO se le niega: no sabemos su
    # peso, así que no tenemos derecho a decir que no cabe.
    with con(binario=lambda: BINARIO, disco_libre_gb=lambda: 0.5,
             corriendo=lambda: True):
        r = sin_romperse("descargar desconocido", lambda: models.descargar("modelo-misterioso:9b"))
    espero("desconocido: no se le negativea", r.get("ok"), True)
    espero("desconocido: sí se apuntó su fila",
           models.PULLS.pop("modelo-misterioso:9b", None) is not None, True)

    # y sin disco medido (0,0) tampoco se negativea: es ignorancia, no un disco lleno
    with con(binario=lambda: BINARIO, disco_libre_gb=lambda: 0.0,
             corriendo=lambda: True):
        r = sin_romperse("descargar con disco sin medir", lambda: models.descargar("qwen3:0.6b"))
    espero("disco sin medir: no se frena la bajada", r.get("ok"), True)
    espero("disco sin medir: se limpia la fila",
           models.PULLS.pop("qwen3:0.6b", None) is not None, True)

    with con(binario=lambda: None, disco_libre_gb=lambda: 220.0,
             corriendo=lambda: True):
        r = sin_romperse("descargar sin binario", lambda: models.descargar("qwen2.5:0.5b"))
    espero("sin Ollama instalado dice cómo conseguirlo",
           "ollama.com/download" in r.get("detalle", ""), True)
    espero("y no se quedó en la fila", "qwen2.5:0.5b" in models.PULLS, False)

cumple("disco libre real: hay sitio medido", models.disco_libre_gb(),
       lambda v: v > 0)

# ── 5 · el estado que consume la cara ─────────────────────────────────────────
print("\n· /api/models: la cara recibe la red y el disco sin tener que adivinar")
with con(binario=lambda: "", corriendo=lambda: False, ip_local=lambda: IP,
         visible_en_red=lambda: False, uso_disco_gb=lambda: 0.0,
         disco_libre_gb=lambda: 231.7, instalados=lambda dado=False: {}):
    e = sin_romperse("estado_completo sin Ollama", lambda: models.estado_completo())
cumple("el estado trae la dirección del PC", e.get("red", {}).get("url"),
       lambda v: v == f"http://{IP}:11434")
espero("trae el sitio libre", e.get("disco_libre_gb"), 231.7)
espero("avisa de que falta Ollama y dice dónde conseguirlo",
       "no está instalado" in e.get("aviso", ""), True)
espero("trae todos los del catálogo", len(e["modelos"]), len(models.CATALOGO))
espero("y el veredicto viaja con cada uno",
       all(m.get("estado") in ("va", "justo", "no cabe", "sin medir")
           for m in e["modelos"]), True)

# el caso que a ella le duele: Ollama instalado pero APAGADO. La cara tiene que
# decir que al bajar se levanta solo, y la red tiene que prometer 0.0.0.0.
with con(binario=lambda: BINARIO, corriendo=lambda: False, ip_local=lambda: IP,
         visible_en_red=lambda: False, uso_disco_gb=lambda: 0.0,
         disco_libre_gb=lambda: 231.7, instalados=lambda dado=False: {},
         **{"quiere_red": lambda: True}):
    e2 = sin_romperse("estado_completo apagado", lambda: models.estado_completo())
espero("apagado: promete levantarlo al pulsar ↓", "lo enciendo solo" in e2.get("aviso", ""), True)
espero("apagado: la cara lee que escuchará la red", e2.get("red", {}).get("escucha"), "0.0.0.0:11434")
espero("apagado: y no dice que ya se ve", e2.get("red", {}).get("visible"), False)

print()
CAJA.cleanup()
if FALLOS:
    print(f"modelos: {len(FALLOS)} FALLA(S) -> {', '.join(FALLOS)}")
    sys.exit(1)
print(f"modelos cosidos: sin psutil se vive, Ollama escucha la red, la cara dice "
      f"la IP que responde y el disco se mide antes de bajar. "
      f"({len(FALLOS)}/0 fallos)")
