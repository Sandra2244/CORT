"""Optimizador del equipo para CORT: ver qué come la RAM y vaciar cachés.

Reglas de seguridad (por eso no necesita permisos de administrador):
  · solo mira y toca cosas DENTRO de la carpeta personal de Sandra
  · solo borra cachés de una lista cerrada; nunca documentos, notas ni la base
    de datos de CORT
  · para cerrar procesos rechaza el escritorio, el audio y la red del sistema
"""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

import psutil

HOME = Path.home()

# (ruta relativa al hogar, qué es, nivel de riesgo)
CACHES = [
    (".cache/pip", "paquetes de Python ya descargados", "seguro"),
    (".cache/thumbnails", "miniaturas de imágenes y videos", "seguro"),
    (".cache/mesa_shader_cache", "sombras de GPU ya compiladas (vuelven a crearse)", "seguro"),
    (".cache/mesa_shader_cache_db", "sombras de GPU ya compiladas (vuelven a crearse)", "seguro"),
    (".cache/google-chrome", "caché web de Chrome (se vuelve a bajar al navegar)", "seguro"),
    (".cache/google-chrome-headless", "caché del Chrome sin ventana de pruebas", "seguro"),
    (".cache/electron", "empaquetados de Electron ya usados", "seguro"),
    (".cache/airaos-electron", "caché de otra app Electron", "seguro"),
    (".cache/mozilla", "caché web de Firefox", "seguro"),
    (".cache/fontconfig", "índices de fuentes (se regeneran solos)", "seguro"),
    (".cache/gstreamer-1.0", "comprobaciones de códecs de audio/video", "seguro"),
    (".cache/event-sound-cache.tdb.2d058e346319e204b8ce584550e22f86.x86_64-pc-linux-gnu",
     "sonidos del escritorio ya registrados", "seguro"),
    (".npm/_cacache", "paquetes de npm ya descargados", "seguro"),
    (".cache/uv", "entornos virtuales en caché de uv", "seguro"),
    (".cache/pip3", "caché alterna de pip", "seguro"),
    (".cache/JARVIS", "caché de un proyecto anterior", "cuidado"),
    (".cache/claude", "caché de una IA de programación", "cuidado"),
    (".cache/Codex", "caché de una IA de programación", "cuidado"),
    (".cache/codex-runtimes", "binarios de esa IA (tarda en volver a bajarlos)", "cuidado"),
    (".cache/huggingface", "modelos descargados por librerías de IA", "cuidado"),
    (".cache/flatpak", "metadatos de Flatpak", "cuidado"),
    (".local/share/Trash", "papelera (cosas que ya tiraste)", "papelera"),
]

# procesos que NUNCA se cierran desde aquí
INTOCABLES = ("systemd", "Xorg", "Xwayland", "lightdm", "xfce4-session", "xfwm4",
              "xfdesktop", "xfpanel", "thunar", "dbus-daemon", "pulseaudio",
              "pipewire", "wireplumber", "NetworkManager", "wpa_supplicant",
              "xfce4-panel", "xfce4-power-manager", "xfce4-settings", "cort",
              "uvicorn", "python3", "electron")


def _tamano(p: Path, tope_s: float = 2.5) -> tuple[int, bool]:
    """Bytes de un árbol, con tope de tiempo: en un equipo de 2 núcleos no se
    puede quedar 30 segundos contando archivos. Devuelve (bytes, aproximado)."""
    total, fin = 0, time.time() + tope_s
    try:
        for raiz, dirs, archivos in os.walk(p, topdown=True, onerror=lambda e: None,
                                            followlinks=False):
            for a in archivos:
                try:
                    fp = Path(raiz) / a
                    if not fp.is_symlink():
                        total += fp.stat().st_size
                except OSError:
                    pass
            if time.time() > fin:
                return total, True
    except Exception:
        return 0, False
    return total, False


def _mb(b: int) -> float:
    return round(b / 1024 / 1024, 1)


def ram() -> dict:
    v = psutil.virtual_memory()
    return {"total_gb": round(v.total / 1e9, 2), "usado_pct": v.percent,
            "disponible_mb": _mb(v.available), "usada_mb": _mb(v.used),
            "intercambio_mb": _mb(psutil.swap_memory().used)}


def _instantanea() -> list[dict]:
    """UNA pasada por la lista de procesos del sistema, para reutilizarla.

    Antes costaba más de lo que parecía: `informe()` llamaba a `procesos_top()`
    dos veces (una para la ventana y otra dentro de `_sugerencias`) y `caches()`
    hacía su propia pasada con `abiertos()`. En un portátil de 2 núcleos eso son
    cuatro recorridos de `/proc` por cada «analiza el equipo». Ahora se recorre
    una vez y se reparte.
    """
    try:
        miusuario = os.getlogin()
    except OSError:
        miusuario = os.environ.get("USER", "")
    uid = os.getuid()
    fila = []
    for p in psutil.process_iter(["pid", "name", "memory_info", "username"]):
        try:
            dueno = p.info["username"] or ""
            if miusuario and dueno and dueno != miusuario:
                continue
            if not dueno and p.uids().real != uid:
                continue
            fila.append(p.info)
        except Exception:
            continue
    return fila


def procesos_top(n: int = 8, instantanea: list[dict] | None = None) -> list[dict]:
    """Los que más memoria real están ocupando ahora mismo (solo tu usuario)."""
    fila = []
    for info in (instantanea if instantanea is not None else _instantanea()):
        mi = info["memory_info"]
        if mi and mi.rss > 30 * 1024 * 1024:
            fila.append({"pid": info["pid"], "nombre": info["name"] or "?",
                         "mb": _mb(mi.rss)})
    fila.sort(key=lambda d: -d["mb"])
    top = fila[:n]
    for d in top:
        d["intocable"] = any(x in d["nombre"].lower() for x in INTOCABLES)
    return top


def abiertos(instantanea: list[dict] | None = None) -> set[str]:
    """Nombres de programas que ahora mismo tienen cosas abiertas (Chrome, Electron…)."""
    salida = set()
    for info in (instantanea if instantanea is not None else _instantanea()):
        n = (info["name"] or "").lower()
        if any(x in n for x in ("chrome", "firefox", "electron", "thunar", "vlc")):
            salida.add(n)
    return salida


def caches(con_tamaño: bool = True, solo_seguro: bool = False,
           presupuesto_s: float = 4.0,
           instantanea: list[dict] | None = None) -> list[dict]:
    """Tamaño de cada caché. `solo_seguro=True` es el modo rápido: no cuenta los
    nidos enormes de modelos y metadatos. Hay presupuesto global de tiempo porque
    contar archivos cuesta en 2 núcleos: lo que no entra, se reporta sin medir."""
    corriendo = " ".join(abiertos(instantanea))
    fin = time.time() + presupuesto_s
    salida = []
    for rel, que, nivel in CACHES:
        if solo_seguro and nivel != "seguro":
            continue
        p = HOME / rel
        if not p.exists():
            continue
        restante = fin - time.time()
        if con_tamaño and restante <= 0.2:
            continue
        b, aprox = (_tamano(p, tope_s=max(0.3, restante)) if con_tamaño else (0, False))
        if b < 1024 * 1024:
            continue
        ocupada = any(k in rel.lower() for k in ("chrome", "mozilla", "flatpak")) and \
            any(c in corriendo for c in ("chrome", "firefox", "flatpak"))
        salida.append({"ruta": rel, "que": que, "nivel": nivel, "mb": _mb(b),
                       "aprox": aprox, "abierta": bool(ocupada)})
    salida.sort(key=lambda d: -d["mb"])
    return salida


_MEMORIA: dict = {}                   # caché de las mediciones caras (contar archivos)
_MIDIENDO = threading.Event()         # está un hilo contando ahora mismo
_CANDADO = threading.Lock()
TTL_S = 300                           # 5 minutos valen las cachés medidas


def _medir_en_hilo() -> None:
    """Cuenta cachés y disco FUERA de la petición HTTP.

    Es el arreglo del «analiza el equipo dura bastante»: antes la ventana 11
    esperaba sentada a que el servidor terminara de recorrer `~/.cache` entero
    (hasta 8 s de disco en un portátil de 2 núcleos) y mientras tanto no pintaba
    nada. Ahora `informe()` contesta al instante con la RAM y los procesos —que
    son baratos—, y la parte cara se calcula en un hilo que va actualizando esta
    memoria. La interfaz pregunta otra vez dos segundos después y ya lo tiene.
    """
    if _MIDIENDO.is_set():
        return
    _MIDIENDO.set()

    def trabajo():
        try:
            instantanea = _instantanea()
            c = caches(instantanea=instantanea)
            try:
                import models
                disc = models.uso_disco_gb()
            except Exception:
                disc = 0
            with _CANDADO:
                _MEMORIA.update(caches=c, discos=disc, cuando=time.time())
        finally:
            _MIDIENDO.clear()

    threading.Thread(target=trabajo, daemon=True).start()


def invalidar() -> None:
    """Tira la medición guardada (después de barrer cachés, que ya no vale)."""
    with _CANDADO:
        _MEMORIA.pop("caches", None)


def informe(fresco: bool = False) -> dict:
    """Lo que ve la ventana 11. Tarda ~una décima: RAM y procesos se miden en el
    acto; las cachés vienen de la medición en segundo plano (o avisan de que van)."""
    ahora = time.time()
    with _CANDADO:
        c = _MEMORIA.get("caches")
        disc = _MEMORIA.get("discos", 0)
        cuando = _MEMORIA.get("cuando", 0)
    caducado = c is None or (ahora - cuando) > TTL_S
    if fresco or caducado:
        c = None if fresco else c        # «fresco» empieza de cero, en el hilo
        _medir_en_hilo()
    instantanea = _instantanea()
    procs = procesos_top(instantanea=instantanea)
    return {"ram": ram(), "procesos": procs, "caches": c or [],
            "midiendo": _MIDIENDO.is_set() or c is None,
            "modelos_gb": disc,
            "liberable_mb": round(sum(x["mb"] for x in (c or []) if x["nivel"] == "seguro"), 1),
            "todo_mb": round(sum(x["mb"] for x in (c or []) if x["nivel"] != "papelera"), 1),
            "papelera_mb": round(sum(x["mb"] for x in (c or []) if x["nivel"] == "papelera"), 1),
            "medido_hace": int(ahora - cuando) if c else None,
            "sugerencias": _sugerencias(disc, procs)}


def _sugerencias(modelos_gb: float = 0, procs: list[dict] | None = None) -> list[str]:
    s = []
    v = psutil.virtual_memory()
    if v.percent > 85:
        s.append(f"RAM al {v.percent} %: cierra el navegador y las ventanas de "
                 "Electron antes de pedirle nada pesado a CORT.")
    pesados = {}
    for d in (procs if procs is not None else procesos_top(20))[:20]:
        pesados[d["nombre"]] = pesados.get(d["nombre"], 0) + d["mb"]
    for nombre, mb in sorted(pesados.items(), key=lambda kv: -kv[1])[:3]:
        if mb > 250:
            s.append(f"{nombre} está usando {round(mb)} MB acumulados.")
    if v.total < 3e9:
        s.append("Con menos de 3 GB de RAM no instales Ollama con modelos de 7B: "
                 "usa el cerebro online gratuito (Groq o Gemini).")
    if modelos_gb >= 0.5:
        s.append(f"Los modelos de Ollama ocupan {modelos_gb} GB en el disco. En "
                 "10 · Modelos puedes borrar los que ya no uses (✕ borrar).")
    if not s:
        s.append("El equipo está holgado: no hace falta limpiar nada.")
    return s


def limpiar(nivel: str = "seguro") -> dict:
    """Vacía las cachés del nivel pedido.
    `seguro` = solo lo que se regenera solo · `todo` = además las "cuidado"
    (cachés de otras apps) · `papelera` = únicamente la papelera."""
    permite = {"seguro": ("seguro",), "todo": ("seguro", "cuidado"),
               "papelera": ("papelera",)}.get(nivel)
    if permite is None:
        return {"ok": False, "error": "nivel desconocido"}
    antes = psutil.virtual_memory().available
    borrado, errores, mb = [], [], 0.0
    for c in caches(solo_seguro=(nivel == "seguro")):
        if c["nivel"] not in permite:
            continue
        p = HOME / c["ruta"]
        try:
            if p.is_file() or p.is_symlink():
                p.unlink()
            else:
                for hijo in p.iterdir():
                    try:
                        shutil.rmtree(hijo) if hijo.is_dir() and not hijo.is_symlink() \
                            else hijo.unlink()
                    except OSError as e:
                        errores.append(f"{hijo.name}: {e.strerror}")
                p.mkdir(parents=True, exist_ok=True)
            mb += c["mb"]
            borrado.append({"ruta": c["ruta"], "mb": c["mb"], "abierta": c["abierta"]})
        except OSError as e:
            errores.append(f"{c['ruta']}: {e.strerror}")
    tiempo = time.time()
    invalidar()                             # ya no vale lo medido antes de barrer
    return {"ok": True, "borrado": borrado, "mb_liberados": round(mb, 1),
            "ram_ganada_mb": _mb(max(0, psutil.virtual_memory().available - antes)),
            "errores": errores[:6], "cuando": tiempo,
            "nota": "las cachés con programas abiertos se liberan cuando esos programas cierren"}


def cerrar(pid: int) -> dict:
    """Cierra UN proceso concreto de tu usuario, con lista negra de seguridad."""
    try:
        p = psutil.Process(int(pid))
        nombre = (p.name() or "?").lower()
        if p.uids().real != os.getuid():
            return {"ok": False, "error": "ese proceso es de otro usuario"}
        if any(x in nombre for x in INTOCABLES):
            return {"ok": False, "error": f"{nombre} es del sistema: no lo cierro"}
        mb = _mb(p.memory_info().rss)
        p.terminate()
        time.sleep(1.2)
        if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
            p.kill()
        return {"ok": True, "nombre": p.name(), "mb": mb,
                "detalle": f"{p.name()} cerrado ({round(mb)} MB devueltos)"}
    except psutil.NoSuchProcess:
        return {"ok": False, "error": "ese proceso ya no existe"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
