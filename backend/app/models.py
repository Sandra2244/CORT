"""Gestor de modelos locales (Ollama) para CORT.

Qué hace:
  · catálogo real de modelos con su peso aproximado y la RAM que necesitan
  · veredicto para ESTE equipo: «va», «justo» o «no cabe»
  · arranca el servidor de Ollama si está apagado
  · descarga (`ollama pull`) en un hilo aparte, con progreso al 1 %
  · borra modelos y pone uno como el activo del cerebro

Nunca falla feo: si Ollama no está instalado, devuelve el catálogo con
`instalado: False` y la instrucción para conseguirlo.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time

# `psutil` es OPCIONAL, y por eso se importa con red. Importarlo en cabecera a pelo
# (`import psutil`) mata el módulo ENTERO si el equipo no lo tiene: ya pasó en el
# runner de Actions (run 39879890814, `ModuleNotFoundError: No module named
# 'psutil'`) y pasaría en cualquier instalación sin `.venv`. Sin `psutil` el
# gestor sigue trabajando —la descarga no depende de él— y lo único que falta es la
# RAM medida, que se declara como «sin medir» en vez de inventarse un veredicto.
try:
    import psutil
except ImportError:
    psutil = None

OLLAMA_URL = "http://127.0.0.1:11434"
PULLS: dict[str, dict] = {}          # nombre -> progreso
_CANCELADOS: set[str] = set()        # nombres que la dueña cortó a media bajada
_CANDADO = threading.Lock()
# Un solo `ollama pull` a la vez. Sin esto, dos descargas simultáneas se comen el
# ancho de banda y, sobre todo, la RAM del equipo: en 1,8 GB el segundo modelo
# llega a la vez que el primero y Ollama se queda sin memoria a media bajada.
_FILA_PULL = threading.Semaphore(1)

# `gb` son los bytes que baja `ollama pull`, MEDIDOS: la suma de las capas del
# manifiesto que sirve `registry.ollama.ai/v2/library/<modelo>/manifests/<tag>`
# (2026-10-23 desde este portátil, con `scripts/mede-catalogo.py`). `b` guarda el
# número exacto para que la cara del teléfono y la ventana de escritorio digan el
# mismo peso. `ram` sigue siendo una estimación honesta de lo que hace falta para
# CORRERLO (eso no lo dice el registro), y por eso el veredicto llama «justo» al
# que queda entre 0,6 y 0,95 de la RAM del equipo en vez de prometerlo.
CATALOGO = [
    {"modelo": "qwen2.5:0.5b",   "gb": 0.4, "b": 397820829, "ram": 1.0, "nivel": "ligero",
     "para": "frases cortas, órdenes y resúmenes rápidos"},
    {"modelo": "qwen3:0.6b",     "gb": 0.5, "b": 522653277, "ram": 1.3, "nivel": "ligero",
     "para": "el más moderno que cabe en un equipo de 2 GB"},
    {"modelo": "tinyllama:1.1b", "gb": 0.6, "b": 637699655, "ram": 1.2, "nivel": "ligero",
     "para": "conversación muy básica en inglés"},
    {"modelo": "deepseek-r1:1.5b", "gb": 1.1, "b": 1117322281, "ram": 2.0, "nivel": "ligero",
     "para": "razonar paso a paso (matemáticas, lógica simple)"},
    {"modelo": "llama3.2:1b",    "gb": 1.3, "b": 1321097844, "ram": 2.2, "nivel": "ligero",
     "para": "español decente con respuestas cortas"},
    {"modelo": "qwen3:1.7b",     "gb": 1.4, "b": 1359292957, "ram": 2.6, "nivel": "medio",
     "para": "bueno para 4 GB: razona y escribe en español"},
    {"modelo": "gemma2:2b",      "gb": 1.6, "b": 1629518008, "ram": 3.0, "nivel": "medio",
     "para": "buen equilibrio calidad/peso"},
    {"modelo": "qwen2.5:3b",     "gb": 1.9, "b": 1929911945, "ram": 3.5, "nivel": "medio",
     "para": "el recomendado para CORT (español y herramientas)"},
    {"modelo": "phi3:mini",      "gb": 2.2, "b": 2176178430, "ram": 4.0, "nivel": "medio",
     "para": "código y razonamiento corto"},
    {"modelo": "qwen3:4b",       "gb": 2.5, "b": 2497293444, "ram": 5.0, "nivel": "medio",
     "para": "el mejor de tamaño medio (necesita 8 GB para ir suelto)"},
    {"modelo": "mistral:7b",     "gb": 4.4, "b": 4372823897, "ram": 7.0, "nivel": "pesado",
     "para": "conversación amplia (necesita 8 GB)"},
    {"modelo": "llama3.1:8b",    "gb": 4.9, "b": 4920752841, "ram": 8.0, "nivel": "pesado",
     "para": "el estándar abierto (8 GB o más)"},
    {"modelo": "qwen2.5:7b",     "gb": 4.7, "b": 4683086845, "ram": 8.0, "nivel": "pesado",
     "para": "multilingüe fuerte, español muy bueno"},
    {"modelo": "codellama:7b",   "gb": 3.8, "b": 3825910133, "ram": 8.0, "nivel": "pesado",
     "para": "programar: autocompletar y explicar código"},
]
POR_NOMBRE = {c["modelo"]: c for c in CATALOGO}


# ───────────────────────────── estado del equipo ─────────────────────────────
def ram_total_gb() -> float:
    """RAM del equipo, o `0,0` si `psutil` no está. Cero y no `None` para que el
    veredicto sepa distinguirlo sin tener que comprobar tipos."""
    if psutil is None:
        return 0.0
    return round(psutil.virtual_memory().total / 1e9, 2)


def ram_libre_gb() -> float:
    """Lo que queda libre AHORA (con esto se dice por qué un modelo de 4,7 GB no va
    en un portátil de 1,8 GB con el navegador abierto)."""
    if psutil is None:
        return 0.0
    return round(psutil.virtual_memory().available / 1e9, 2)


def veredicto(ficha: dict) -> dict:
    """Si este modelo va a poder correr aquí, con la RAM que hay."""
    total = ram_total_gb()
    necesita = ficha["ram"]
    if not total:
        # Sin `psutil` no nos inventamos el veredicto: lo que se puede hacer con
        # los números que sí tenemos es comparar contra la RAM que DECLARA la
        # dueña en Ajustes, y eso lo hace la cara, no este fichero.
        return {"estado": "sin medir",
                "nota": "no puedo medir la RAM de este equipo (instalando `psutil` "
                        "vuelve el veredicto; descargar sigue funcionando igual)",
                "ram_equipo": 0.0}
    if necesita <= total * 0.6:
        estado, nota = "va", "te sobra RAM para correrlo"
    elif necesita <= total * 0.95:
        estado, nota = "justo", "va a ir lento: cierra el navegador antes"
    else:
        estado, nota = "no cabe", f"necesita ~{necesita:g} GB y tu equipo tiene {total:g} GB"
    return {"estado": estado, "nota": nota, "ram_equipo": total}


def binario() -> str | None:
    return shutil.which("ollama")


def corriendo() -> bool:
    import requests
    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.2).status_code == 200
    except Exception:
        return False


def _raiz_modelos():
    """Carpeta donde Ollama guarda los manifiestos y los blobs."""
    import os
    from pathlib import Path
    r = os.environ.get("OLLAMA_MODELS") or str(Path.home() / ".ollama" / "models")
    return Path(r)


# ─────────────────────────── la red: lo que ve el teléfono ───────────────────
# El motivo nº 1 por el que «no se pueden descargar modelos» desde el móvil:
# `ollama serve` arranca escuchando SOLO en 127.0.0.1, así que el portátil
# contestó siempre a CORT-PC y nunca a CORT-teléfono. Antes esto se explicaba en
# un `docs/` (hacerlo a mano con `systemctl edit ollama`), que es un manual, no un
# arreglo. Aquí se arranca YA con `OLLAMA_HOST=0.0.0.0` y se comprueba de verdad
# si se le ve desde la red, en vez de dar una dirección esperando que funcione.
PUERTO_OLLAMA = 11434


def quiere_red() -> bool:
    """Si Ollama debe escuchar fuera de este equipo. Mando de la dueña:
    `ollama_red` a `false`/`no`/`0` en `~/.cort/cort_config.json` lo deja en casa
    (127.0.0.1), que es lo que querrá quien no quiera tener el puerto abierto."""
    try:
        import config_store
        v = str(config_store.raw().get("ollama_red", "")).strip().lower()
    except Exception:
        return True                      # sin config: el default es la red
    return v not in ("false", "0", "no", "off", "apagado", "nunca")


def host_sirve() -> str:
    """La dirección que se le pasa a `OLLAMA_HOST` al levantar el servidor."""
    return f"0.0.0.0:{PUERTO_OLLAMA}" if quiere_red() else f"127.0.0.1:{PUERTO_OLLAMA}"


def ip_local() -> str:
    """La IP que vería el teléfono. El truco del socket UDP **no manda ningún
    paquete**: sólo le pregunta a la tabla de rutas por qué interfaz saldría, así
    que funciona sin internet y sin vecinos que escuchen."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(("10.255.255.255", 1))         # dirección imposible: cero tráfico
        return s.getsockname()[0]
    except OSError:
        return ""
    finally:
        if s is not None:
            try:
                s.close()
            except OSError:
                pass


def visible_en_red() -> bool:
    """¿Se le ve de verdad desde fuera? Se comprueba entrando por SU propia IP de
    la red, no por 127.0.0.1: es la única forma de no escribir en la pantalla una
    dirección que no responde. Con Ollama apagado responde `False` (y la cara lo
    dice como lo que es)."""
    ip = ip_local()
    if not ip or not corriendo():
        return False
    import requests
    try:
        return requests.get(f"http://{ip}:{PUERTO_OLLAMA}/api/tags",
                            timeout=1.5).status_code == 200
    except Exception:
        return False


def info_red() -> dict:
    """Lo que la cara del PC tiene que enseñar para que el móvil se conecte a
    primera: la dirección exacta, si de verdad se ve, y qué hacer si no."""
    ip = ip_local()
    url = f"http://{ip}:{PUERTO_OLLAMA}" if ip else ""
    if not ip:
        nota = "no encuentro la IP de este equipo: conéctalo a la Wi-Fi del teléfono"
    elif not corriendo():
        nota = "Ollama está apagado: al pulsar ↓ lo levanto escuchando la red"
    elif visible_en_red():
        nota = "se ve desde la Wi-Fi: pon esa dirección en el teléfono"
    elif not quiere_red():
        nota = ("escucha solo para este equipo porque `ollama_red` está apagado; "
                "ponlo en `verdadero` para que el teléfono lo vea")
    else:
        nota = ("Ollama está levantado pero NO se ve desde fuera: suele ser el "
                "cortafuegos del portable (abrir el puerto 11434 en la red local) "
                "o que lo arrancó otro programa sin `OLLAMA_HOST=0.0.0.0`")
    return {"ip": ip, "puerto": PUERTO_OLLAMA, "url": url,
            "escucha": host_sirve(), "visible": visible_en_red(), "nota": nota}


def en_disco() -> dict[str, dict]:
    """Modelos que ya están bajados, leyendo el disco (sirve con Ollama apagado).

    Ollama guarda cada modelo como un manifiesto en
    `~/.ollama/models/manifests/<registry>/<familia>/<etiqueta>`; el peso real
    está en los blobs que ese manifiesto referencia."""
    raiz = _raiz_modelos()
    mans, blobs = raiz / "manifests", raiz / "blobs"
    if not mans.exists():
        return {}
    salida: dict[str, dict] = {}
    for f in mans.rglob("*"):
        if not f.is_file():
            continue
        partes = f.relative_to(mans).parts
        if len(partes) < 2:
            continue
        familia, etiqueta = partes[-2], partes[-1]
        nombre = f"{familia}:{etiqueta}"
        gb = 0.0
        try:
            datos = json.loads(f.read_text())
            capas = datos.get("layers") or datos.get("file_descriptors") or []
            for d in capas:
                tam = d.get("size") or 0
                if not tam:
                    b = blobs / (d.get("digest") or "").replace(":", "-")
                    if b.is_file():
                        tam = b.stat().st_size
                gb += tam
        except Exception:
            pass
        salida[nombre] = {"nombre": nombre, "gb": round(gb / 1e9, 2), "modificado": ""}
    return salida


def instalados(dado: bool | None = None) -> dict[str, dict]:
    """Modelos que ya están en el disco, con su peso real.

    `dado` permite pasar por escrito si Ollama está encendido, para no volver a
    preguntarle por red dentro de una misma llamada a `/api/models`."""
    encendido = corriendo() if dado is None else dado
    if encendido:
        import requests
        try:
            datos = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3).json()
        except Exception:
            return en_disco()
        salida = {}
        for m in datos.get("models", []):
            nombre = (m.get("name") or "").strip()
            if nombre:
                salida[nombre] = {"nombre": nombre,
                                  "gb": round((m.get("size") or 0) / 1e9, 2),
                                  "modificado": m.get("modified", "")}
        return salida
    return en_disco()


def uso_disco_gb() -> float:
    """Cuánto ocupa Ollama en el disco (los blobs, sin contar dos veces una capa)."""
    raiz = _raiz_modelos()
    total, tope = 0, time.time() + 2.0
    for base, _, archivos in os.walk(raiz):
        for a in archivos:
            try:
                total += os.path.getsize(os.path.join(base, a))
            except OSError:
                pass
        if time.time() > tope:
            break
    return round(total / 1e9, 2)


def disco_libre_gb() -> float:
    """Sitio libre DONDE Ollama escribe (no donde vive el repo: si `OLLAMA_MODELS`
    apunta a otro disco, ese es el que hay que mirar)."""
    try:
        raiz = _raiz_modelos()
        while not raiz.exists() and raiz.parent != raiz:
            raiz = raiz.parent
        return round(shutil.disk_usage(str(raiz)).free / 1e9, 2)
    except OSError:
        return 0.0


def estado_completo() -> dict:
    """Catálogo + qué hay descargado + el veredicto de cada uno."""
    hay_binario = bool(binario())
    encendido = corriendo() if hay_binario else False
    tengo = instalados(encendido)
    activo = ""
    try:
        import config_store
        activo = config_store.raw().get("ollama_model", "")
    except Exception:
        pass
    modelos = []
    for ficha in CATALOGO:
        copia = dict(ficha)
        copia.update(veredicto(ficha))
        clave = _coincide(ficha["modelo"], tengo)
        copia["descargado"] = bool(clave)
        copia["peso_real_gb"] = tengo[clave]["gb"] if clave else None
        copia["activo"] = (clave == activo)
        modelos.append(copia)
    # los que estén descargados pero no estén en el catálogo
    for nombre, datos in tengo.items():
        if not any(_coincide(c["modelo"], {nombre: 1}) for c in CATALOGO):
            est = round(max(datos["gb"], 0.3) * 1.7, 1)
            modelos.append({"modelo": nombre, "gb": datos["gb"], "ram": est,
                            "nivel": "otros", "para": "fuera del catálogo",
                            "descargado": True, "peso_real_gb": datos["gb"],
                            "activo": nombre == activo,
                            **veredicto({"ram": est})})
    aviso = ""
    if not hay_binario:
        aviso = ("Ollama no está instalado: bájalo de https://ollama.com/download "
                 "(solo tiene sentido en equipos con 8 GB o más de RAM)")
    elif not encendido:
        aviso = ("Ollama está apagado: los pesos se leen del disco. Al pulsar ↓ descargar "
                 "lo enciendo solo, y puedes apagarlo para devolver memoria.")
    return {"instalado": hay_binario, "corriendo": encendido,
            "binario": binario() or "", "ram_equipo": ram_total_gb(),
            "ram_libre_gb": ram_libre_gb(),
            "activo": activo, "modelos": modelos, "aviso": aviso,
            "disco_gb": uso_disco_gb(), "disco_libre_gb": disco_libre_gb(),
            "red": info_red()}


def _coincide(nombre_catalogo: str, dic: dict) -> str | None:
    """Busca tolerante pero SIN confundirse de tamaño: `qwen2.5:3b` vale si Ollama lo
    reporta como `qwen2.5:3b-instruct`, pero nunca como `qwen2.5:0.5b`."""
    if nombre_catalogo in dic:
        return nombre_catalogo
    for clave in dic:
        if clave.startswith(nombre_catalogo + "-") or clave.startswith(nombre_catalogo + " "):
            return clave
    base = nombre_catalogo.split(":")[0]
    for clave in dic:
        cb, _, tag = clave.partition(":")
        if cb == base and (not tag or tag == "latest") and ":" not in nombre_catalogo:
            return clave
    return None


# ───────────────────────────── acciones del equipo ─────────────────────────────
def arrancar_servidor() -> dict:
    if not binario():
        return {"ok": False, "error": "no hay ollama instalado"}
    if corriendo():
        return {"ok": True, "ya": True, "detalle": "Ollama ya estaba en marcha",
                "red": info_red()}
    entorno = dict(os.environ)
    # `setdefault`, no `=`: si la dueña ya puso su `OLLAMA_HOST` (en systemd, en el
    # perfil de Windows o a mano), Mandamos su decisión y no la pisamos.
    entorno.setdefault("OLLAMA_HOST", host_sirve())
    subprocess.Popen([binario(), "serve"], env=entorno,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    for _ in range(20):
        time.sleep(0.5)
        if corriendo():
            r = {"ok": True, "detalle": f"Ollama encendido en {entorno['OLLAMA_HOST']}"}
            if quiere_red():
                visto = visible_en_red()
                r["red"] = info_red()
                if not visto:
                    r["aviso_red"] = ("levanté Ollama para toda la red pero el teléfono "
                                      "aún no lo ve: revisa el cortafuegos del portable")
            return r
    return {"ok": False, "error": "tardó demasiado en responder"}


def _procs_ollama_sin_psutil() -> list[int]:
    """Los PIDs de `ollama` leyendo `/proc`, para equipos sin `psutil` (Linux)."""
    salida = []
    for entrada in os.listdir("/proc"):
        if not entrada.isdigit():
            continue
        pid = int(entrada)
        if pid == os.getpid():
            continue
        try:
            with open(f"/proc/{pid}/comm", "r", encoding="utf-8") as f:
                nombre = f.read().strip().lower()
        except OSError:
            continue
        if nombre in ("ollama", "ollama_llama_server"):
            salida.append(pid)
    return salida


def detener_servidor() -> dict:
    muertos = 0
    if psutil is None:
        import signal
        for pid in _procs_ollama_sin_psutil():
            try:
                os.kill(pid, signal.SIGTERM)
                muertos += 1
            except OSError:
                pass
        return {"ok": muertos > 0, "cerrados": muertos, "via": "/proc",
                "detalle": (f"{muertos} proceso(s) de Ollama cerrados" if muertos
                            else "no había ninguno en marcha")
                            if muertos else
                            "sin `psutil` sólo puedo cerrar Ollama en Linux; en "
                            "Windows usa el icono de la bandeja"}
    for p in psutil.process_iter(["name"]):
        try:
            if (p.info["name"] or "").lower() in ("ollama", "ollama_llama_server"):
                p.terminate()
                muertos += 1
        except Exception:
            pass
    return {"ok": muertos > 0, "cerrados": muertos, "via": "psutil",
            "detalle": f"{muertos} proceso(s) de Ollama cerrados" if muertos
            else "no había ninguno en marcha"}


def descargar(nombre: str) -> dict:
    """Apunta la descarga y devuelve **al instante**.

    El arreglo de «no me deja descargar modelos de una vez»: antes esta función
    llamaba a `arrancar_servidor()` dentro de la petición HTTP, y como Ollama
    estaba apagado la dueña pulsaba «↓ descargar» y el botón no hacía nada visible
    durante diez segundos (a veces más, y con el holograma congelado). Ahora el
    POST responde en milímetros de segundo, la fila de descargas se ve en la
    ventana 10 con su estado —`en cola`, `encendiendo`, `descargando`— y el hilo
    se ocupa de encender Ollama si hace falta.

    Se pueden apuntar varios a la vez: se van bajando **uno detrás de otro**
    (`_FILA_PULL`), porque dos descargas simultáneas en 1,8 GB de RAM revientan la
    primera a medias. Cada uno conserva su propia barra y su puesto en la fila.
    """
    if not binario():
        return {"ok": False,
                "error": "no hay ollama instalado en este equipo",
                "detalle": "bájalo de https://ollama.com/download (con 1,8 GB de RAM "
                           "solo merece un modelo de menos de 0,6 GB)"}
    nombre = (nombre or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9._:/@-]{2,64}", nombre):
        return {"ok": False, "error": "nombre de modelo no válido"}
    # El sitio se comprueba ANTES de lanzar nada: cortar una bajada de 4,7 GB
    # cuando el disco ya está lleno deja el modelo a medias y la cara sin saber
    # por qué. Si no está en el catálogo (`b` medido) no se puede prometer nada:
    # se deja pasar, porque negativear un modelo desconocido sería peor.
    ficha = POR_NOMBRE.get(nombre)
    libre = disco_libre_gb()
    if ficha and ficha.get("b") and libre and ficha["b"] / 1e9 > libre - 1.0:
        return {"ok": False,
                "error": (f"no cabe en el disco: {nombre} pesa "
                          f"{ficha['gb']:g} GB y quedan {libre:g} GB libres"),
                "detalle": "borra modelos con 🗑 o libera sitio; la descarga no se lanzó"}
    with _CANDADO:
        previo = PULLS.get(nombre)
        if previo and previo.get("estado") in ("descargando", "en cola", "encendiendo"):
            return {"ok": True, "detalle": "ya estaba en la fila", "modelo": nombre,
                    "estado": previo["estado"]}
        _CANCELADOS.discard(nombre)
        PULLS[nombre] = {"estado": "en cola", "pct": 0, "mb": 0, "mb_total": 0,
                         "vel": 0, "detalle": "en la fila", "empezó": time.time(),
                         "error": ""}
        # Puesto real: se bajan de uno en uno, así que va delante de quien ya
        # esté bajando y de quien esté esperando como él.
        puesto = 1 + sum(1 for k, v in PULLS.items()
                         if k != nombre
                         and v.get("estado") in ("descargando", "encendiendo", "en cola"))
        if puesto > 1:
            PULLS[nombre]["detalle"] = f"en la fila, detrás de {puesto - 1}"
    threading.Thread(target=_jalar, args=(nombre,), daemon=True).start()
    return {"ok": True, "modelo": nombre, "puesto": puesto,
            "detalle": "descarga apuntada" if puesto == 1 else f"en la fila ({puesto})"}


def cancelar(nombre: str) -> dict:
    """Corta una descarga en curso o la quita de la fila."""
    nombre = (nombre or "").strip()
    with _CANDADO:
        if nombre not in PULLS:
            return {"ok": False, "error": "ese modelo no se estaba bajando"}
        _CANCELADOS.add(nombre)
        PULLS[nombre]["estado"] = "cancelando"
        PULLS[nombre]["detalle"] = "cortando…"
    return {"ok": True, "modelo": nombre, "detalle": f"cancelando {nombre}"}


# El progreso real de Ollama viene por capas (`digest`); se suman todas para que
# la barra no salte de 100 % de una capa a 0 % de la siguiente.
def _cortada(nombre: str) -> bool:
    """¿La dueña canceló este modelo? Si sí, lo quita de la fila y responde True."""
    with _CANDADO:
        if nombre in _CANCELADOS or (PULLS.get(nombre) or {}).get("estado") in \
                ("cancelando", "cancelado"):
            _CANCELADOS.discard(nombre)
            PULLS.pop(nombre, None)
            return True
    return False


def _jalar(nombre: str) -> None:
    """Espera su turno y luego baja. Con la fila vacía arranca al instante.

    La comprobación se repite **después** de coger el turno: si canceló mientras
    esperaba y el semáforo se libera justo en ese instante, el bucle no llega a
    pasar por arriba y el modelo se bajaría igual.
    """
    while not _FILA_PULL.acquire(timeout=0.5):
        if _cortada(nombre):
            return
        _marca(nombre, "en cola", detalle="en la fila: espera su turno")
    try:
        if _cortada(nombre):
            return
        _bajar(nombre)
    finally:
        _FILA_PULL.release()


def _bajar(nombre: str) -> None:
    import requests
    if not corriendo():
        _marca(nombre, "encendiendo", detalle="despertando Ollama…")
        r = arrancar_servidor()
        if not r.get("ok"):
            _marca(nombre, "error",
                   error="Ollama no arrancó: " + (r.get("error") or "sin respuesta"))
            return
    # En cuanto tiene el turno deja de estar «en cola», aunque tarden los
    # primeros bytes: si no, el puesto de los siguientes se calcula mal.
    _marca(nombre, "descargando", detalle="conectando con Ollama…")
    capas: dict[str, list[float]] = {}
    try:
        with requests.post(f"{OLLAMA_URL}/api/pull", json={"model": nombre, "stream": True},
                           stream=True, timeout=(10, None)) as r:
            if r.status_code != 200:
                _marca(nombre, "error", error=f"Ollama respondió {r.status_code}")
                return
            for linea in r.iter_lines():
                if nombre in _CANCELADOS:
                    _CANCELADOS.discard(nombre)
                    _marca(nombre, "cancelado", detalle="cancelada por ti")
                    return
                if not linea:
                    continue
                try:
                    d = json.loads(linea)
                except Exception:
                    continue
                est = (d.get("status") or "").lower()
                if "error" in d:
                    _marca(nombre, "error", error=str(d["error"])[:180])
                    return
                dig, tot, done = d.get("digest"), d.get("total"), d.get("completed")
                if dig and tot:
                    capas[dig] = [float(done or 0), float(tot)]
                hecha = sum(v[0] for v in capas.values())
                total = sum(v[1] for v in capas.values())
                if total:
                    mb, mbt, pct = hecha / 1e6, total / 1e6, round(hecha / total * 100, 1)
                    _marca(nombre, "descargando", pct=pct, mb=round(mb, 1),
                           mb_total=round(mbt, 1),
                           detalle=f"{est or 'bajando'} · {mb:.0f} de {mbt:.0f} MB")
                else:
                    _marca(nombre, "descargando", detalle=est or "…")
        _marca(nombre, "listo", pct=100, detalle="en el disco")
    except Exception as e:
        _marca(nombre, "error", error=f"{type(e).__name__}: {e}")


def _marca(nombre: str, estado: str, pct: float | None = None, detalle: str = "",
           error: str = "", mb: float | None = None, mb_total: float | None = None) -> None:
    with _CANDADO:
        p = PULLS.setdefault(nombre, {"empezó": time.time()})
        ahora = time.time()
        p["estado"] = estado
        if pct is not None:
            p["pct"] = pct
        if detalle:
            p["detalle"] = detalle
        if error:
            p["error"] = error
        if mb is not None:
            p["mb"] = mb
        if mb_total is not None:
            p["mb_total"] = mb_total
        if mb is not None:
            # Velocidad MEDIA desde que empezó la bajada, no instantánea: con dos
            # núcleos un pico por línea haría que el número saltara cada segundo.
            p["vel"] = round(mb / max(1.0, ahora - p.get("empezó", ahora)), 2)
        p["ahora"] = ahora


def progreso() -> dict:
    with _CANDADO:
        copia = {k: dict(v) for k, v in PULLS.items()}
    # limpieza: lo que ya terminó hace media hora deja de ocupar la ventana
    corte = time.time() - 1800
    with _CANDADO:
        for k in [k for k, v in PULLS.items()
                  if v.get("estado") in ("listo", "error", "cancelado")
                  and v.get("ahora", 0) < corte]:
            PULLS.pop(k, None)
    return copia


def borrar(nombre: str) -> dict:
    if not binario():
        return {"ok": False, "error": "no hay ollama instalado"}
    r = subprocess.run([binario(), "rm", nombre.strip()], capture_output=True, text=True,
                       timeout=60)
    return {"ok": r.returncode == 0,
            "detalle": (r.stdout or r.stderr or "").strip()[:200]}


def usar(nombre: str) -> dict:
    """Lo pone como modelo local del cerebro."""
    try:
        import config_store
        config_store.set_value("ollama_model", nombre.strip())
        return {"ok": True, "modelo": nombre.strip()}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
