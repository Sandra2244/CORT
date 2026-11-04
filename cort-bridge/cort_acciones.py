#!/usr/bin/env python3
"""CORT — manos en la máquina (fase F5).

Por qué este archivo existe: hasta aquí el puente sabía *decir* cosas y *medir*
cosas, pero no podía tocar nada. Este módulo es la capa de acción nativa de Linux
que sustituye al backend de Windows de la plantilla (registro, winget, PowerShell).

Tres reglas duras, medidas contra los fallos reales de la plantilla:

1. Nada de `shell=True` y nada de texto suelto en un comando. Toda llamada es una
   lista de argumentos y lo que llega del navegador se compara contra una lista de
   cosas que ya existen en el equipo (ventanas abiertas, .desktop instalados).
   "Abre X" no inyecta X en un shell: busca X y, si no está, dice que no está.
2. Lo que apaga o suspende el equipo pide confirmación explícita (`confirmar=True`).
   Un mensaje perdido no debe tumbar una sesión de trabajo.
3. Cada resultado lleva `origen`: "real" si el comando corrió y devolvió algo,
   "no disponible" si el programa no está instalado en este equipo. Nunca se
   inventa un éxito.

Herramientas verificadas en la Canaima el 2026-11-02 (`command -v`):
  presentes   wmctrl, xdotool, pactl, loginctl, systemctl, xfconf-query,
              notify-send, xclip, scrot, xdg-open, vlc, espeak-ng
  ausentes    brightnessctl, playerctl, xsel, gtk-launch, mpv, firefox
  brillo      /sys/class/backlight/intel_backlight (sin brilloctl: se prueba el
              archivo y, si no se puede escribir, se dice en vez de fingir)
"""
from __future__ import annotations

import base64
import json
import os
import re
import shlex
import shutil
import subprocess
import time
import unicodedata
from pathlib import Path

# ------------------------------------------------------- qué se puede tocar ----
# Cada acción declara su herramienta. Si la herramienta no está, la acción responde
# "no disponible" con el nombre del programa que falta: eso es lo que la plantilla
# no hacía y dejaba el panel girando.
HERRAMIENTAS = {
    "ventanas": "wmctrl",
    "ventanas_acciones": "wmctrl",
    "teclas_media": "xdotool",
    "volumen": "pactl",
    "notificar": "notify-send",
    "captura": "scrot",
    "portapapeles": "xclip",
    "abrir": "xdg-open",
    "fondo": "xfconf-query",
    "energia": "systemctl",
}

# Apps que CORT puede lanzar sin pregunta: las que existen como .desktop en el
# equipo. Se construye al llamar, no al importar, para que un escritorio recién
# instalado no obligue a reiniciar el puente.
CARPETAS_APPS = [Path("/usr/share/applications"),
                 Path(os.environ.get("HOME", "/root")) / ".local/share/applications"]
CARPETAS_APP_EXTRA = [Path("/var/lib/flatpak/exports/share/applications")]

# Cosas que NO se abren por muy bien que suenen: el puente no es un lanzador de
# binarios cualesquiera, sino de las entradas de escritorio del usuario.
EJECUTABLES_PROHIBIDOS = {"rm", "mkfs", "dd", "shutdown", "reboot", "poweroff", "init"}


def _sin(t: str) -> str:
    """Minúsculas, sin acentos ni espacios de más: para comparar nombres a mano limpia."""
    t = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip()


def _hay(herramienta: str):
    return shutil.which(HERRAMIENTAS.get(herramienta, herramienta))


def _correr(args, segundos=8):
    """Ejecuta una lista de argumentos, sin shell, y devuelve (rc, stdout, stderr)."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=segundos)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", "no existe " + str(args[0])
    except subprocess.TimeoutExpired:
        return 124, "", "tiempo agotado en " + str(args[0])
    except Exception as e:
        return 1, "", f"{type(e).__name__}: {e}"


def resultado(nombre_accion, ok, detalle="", origen="real", **extra):
    r = {"type": "cort_accion", "accion": nombre_accion, "ok": bool(ok),
         "detalle": detalle, "origen": origen if ok or origen == "no disponible" else "real"}
    r.update(extra)
    return r


# ------------------------------------------------------------- registro ----
# Cada acción que toca el equipo se anota en un archivo aparte, con hora. Es el
# requisito de F5: si CORT hizo algo en la máquina, tiene que poder enseñar cuándo.
REGISTRO = Path(os.environ.get("CORT_DATOS",
                               str(Path(os.environ.get("HOME", "/root")) / ".local" / "share" / "cort"))) / "registro-acciones.jsonl"


def registrar(que, datos, r):
    try:
        REGISTRO.parent.mkdir(parents=True, exist_ok=True)
        linea = {"hora": time.strftime("%Y-%m-%dT%H:%M:%S"),
                 "accion": que, "datos": {k: str(v)[:60] for k, v in (datos or {}).items()
                                          if k != "type"},
                 "ok": r.get("ok"), "origen": r.get("origen"),
                 "detalle": str(r.get("detalle", ""))[:160]}
        with REGISTRO.open("a", encoding="utf-8") as f:
            f.write(json.dumps(linea, ensure_ascii=False) + "\n")
        return linea
    except Exception:
        return None            # un registro que falla no puede tumbar la acción


# ------------------------------------------------------- inventario de apps ----
_APPS_CACHE: tuple[float, list] = (0.0, [])
_APP_CACHE_SEG = 60      # leer 165 .desktop cuesta ~2 s medidos; no se repite cada orden


def apps_disponibles(refrescar: bool = False) -> list[dict]:
    """Las entradas de escritorio reales del equipo (nombre, ejecutable, icono)."""
    global _APPS_CACHE
    ahora = time.time()
    if not refrescar and _APPS_CACHE[1] and ahora - _APPS_CACHE[0] < _APP_CACHE_SEG:
        return _APPS_CACHE[1]
    vistos, salida = set(), []
    for carp in CARPETAS_APPS + CARPETAS_APP_EXTRA:
        if not carp.is_dir():
            continue
        for f in sorted(carp.glob("*.desktop")):
            try:
                texto = f.read_text(errors="ignore")
            except Exception:
                continue
            if re.search(r"^NoDisplay=true", texto, re.M):
                continue
            campos = {}
            for clave in ("Name", "Exec", "Icon", "Comment"):
                m = re.search(rf"^{clave}=(.*)$", texto, re.M)
                if m and clave not in campos:
                    campos[clave] = m.group(1).strip()
            nombre = campos.get("Name") or f.stem
            if not nombre or _sin(nombre) in vistos:
                continue
            vistos.add(_sin(nombre))
            salida.append({"nombre": nombre, "ejec": campos.get("Exec", ""),
                           "icono": campos.get("Icon", ""), "nota": campos.get("Comment", "")[:90],
                           "archivo": str(f)})
    _APPS_CACHE = (ahora, salida)
    return salida


def _buscar_app(nombre: str, apps: list[dict]):
    objetivo = _sin(nombre)
    if not objetivo:
        return None
    for a in apps:                                  # coincidencia exacta primero
        if _sin(a["nombre"]) == objetivo:
            return a
    for a in apps:                                  # después "abre firefox" -> Firefox ESR
        if objetivo in _sin(a["nombre"]):
            return a
    return None


def abrir_aplicacion(nombre: str) -> dict:
    """Lanza una entrada de escritorio existente. No mete texto del usuario en un shell."""
    if not _hay("abrir"):
        return resultado("abrir_app", False, "no está xdg-open en el equipo", "no disponible",
                         hace_falta="paquete xdg-utils")
    apps = apps_disponibles()
    app = _buscar_app(nombre, apps)
    if not app:
        return resultado("abrir_app", False,
                         f"no hay ninguna aplicación de escritorio llamada «{nombre}» "
                         f"(se compararon {len(apps)} entradas del equipo)")
    ejec = app["ejec"]
    if not ejec:
        return resultado("abrir_app", False, f"«{app['nombre']}» no tiene línea Exec")
    # Los códigos de campo de la especificidad (.desktop %u %f) se quitan: sin
    # archivo encima, la mayoría de las apps arranca igual.
    limpio = re.sub(r"%[a-zA-Z]", "", ejec).strip()
    try:
        args = shlex.split(limpio)
    except ValueError:
        return resultado("abrir_app", False, f"línea Exec ilegible en {app['archivo']}")
    if not args or args[0].split("/")[-1] in EJECUTABLES_PROHIBIDOS:
        return resultado("abrir_app", False, "ese ejecutable está en la lista de prohibidos")
    if any(c in limpio for c in ";|&`$()<>"):
        # Un .desktop con metacaracteres es terreno de ataque; mejor no ejecutarlo.
        return resultado("abrir_app", False,
                         f"«{app['nombre']}» tiene símbolos raros en Exec; no se ejecuta",
                         app=app["nombre"])
    try:
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except Exception as e:
        return resultado("abrir_app", False, f"falló al arrancar: {type(e).__name__}: {e}")
    return resultado("abrir_app", True, f"{app['nombre']} lanzada", app=app["nombre"],
                     ejec=args[0])


def abrir_url(url: str) -> dict:
    """Sólo http/https/mailto/file con ruta dentro de casa. Nada de esquemas raros."""
    u = (url or "").strip()
    if not re.match(r"^(https?://|mailto:)", u):
        return resultado("abrir_url", False, "sólo se abren enlaces http, https o correo")
    if not _hay("abrir"):
        return resultado("abrir_url", False, "no está xdg-open", "no disponible")
    rc, _, err = _correr(["xdg-open", u], segundos=6)
    return resultado("abrir_url", rc == 0, err[:120] or f"abierto en el navegador por defecto", url=u)


def abrir_carpeta(ruta: str) -> dict:
    """Abre una carpeta del usuario (no del sistema) en el gestor de archivos."""
    p = Path(os.path.expanduser(ruta or "~"))
    if not p.is_dir():
        return resultado("abrir_carpeta", False, f"no existe la carpeta {p}")
    if not _hay("abrir"):
        return resultado("abrir_carpeta", False, "no está xdg-open", "no disponible")
    rc, _, err = _correr(["xdg-open", str(p)], segundos=6)
    return resultado("abrir_carpeta", rc == 0, err[:120] or str(p), carpeta=str(p))


# --------------------------------------------------------------------- ventanas ----
def ventanas() -> list[dict]:
    """Lista real de ventanas: `wmctrl -lp` leído ahora mismo."""
    if not _hay("ventanas"):
        return []
    rc, salida, _ = _correr(["wmctrl", "-lp"])
    if rc != 0:
        return []
    v = []
    for linea in salida.splitlines():
        partes = linea.split(None, 3)
        if len(partes) < 4:
            continue
        vid, escritorio, pid, titulo = partes[0], partes[1], partes[2], partes[3]
        v.append({"id": vid, "escritorio": int(escritorio) if escritorio.isdigit() else escritorio,
                  "pid": int(pid) if pid.isdigit() else pid, "titulo": titulo})
    return v


def _ventana_por_titulo(texto: str):
    objetivo = _sin(texto)
    vs = ventanas()
    exactas = [w for w in vs if _sin(w["titulo"]) == objetivo]
    parciales = [w for w in vs if objetivo and objetivo in _sin(w["titulo"])]
    return (exactas or parciales), vs


def cerrar_ventana(texto: str) -> dict:
    candidatos, todas = _ventana_por_titulo(texto)
    if not _hay("ventanas_acciones"):
        return resultado("cerrar_ventana", False, "no está wmctrl", "no disponible")
    if not candidatos:
        return resultado("cerrar_ventana", False,
                         f"ninguna ventana abierta coincide con «{texto}» "
                         f"(hay {len(todas)}: " + ", ".join(w["titulo"][:22] for w in todas[:6]) + ")")
    if len(candidatos) > 1:
        return resultado("cerrar_ventana", False,
                         "varias ventanas coinciden, se cierra la primera solo si lo confirmas",
                         opciones=[c["titulo"] for c in candidatos[:6]])
    w = candidatos[0]
    rc, _, err = _correr(["wmctrl", "-i", "-c", w["id"]])
    return resultado("cerrar_ventana", rc == 0, err[:120] or f"cerrada «{w['titulo']}»",
                     titulo=w["titulo"])


def minimizar_ventana(texto: str) -> dict:
    candidatos, _ = _ventana_por_titulo(texto)
    if not candidatos:
        return resultado("minimizar_ventana", False, f"no hay ninguna ventana con «{texto}»")
    w = candidatos[0]
    rc, _, err = _correr(["wmctrl", "-i", "-b", "add,hidden", w["id"]])
    return resultado("minimizar_ventana", rc == 0, err[:120] or f"minimizada «{w['titulo']}»")


def enfocar_ventana(texto: str) -> dict:
    candidatos, _ = _ventana_por_titulo(texto)
    if not candidatos:
        return resultado("enfocar_ventana", False, f"no hay ninguna ventana con «{texto}»")
    w = candidatos[0]
    rc, _, err = _correr(["wmctrl", "-i", "-a", w["id"]])
    return resultado("enfocar_ventana", rc == 0, err[:120] or f"al frente «{w['titulo']}»")


def ventana_activa():
    """Id de la ventana que tiene el foco ahora mismo, o None si no se puede saber.

    Sin `xdotool` no se adivina: devolver la primera de la lista haría que
    «cambiar de ventana» moviera el foco a una ventana cualquiera creyendo que era
    la activa.

    `xdotool getactivewindow` imprime el id en decimal (`90177540`) y `wmctrl` en
    hexadecimal (`0x059f0004`); sin convertir, la comparación nunca cuadra y la
    ventana activa parecería siempre desconocida.
    """
    if _hay("xdotool"):
        rc, salida, _ = _correr(["xdotool", "getactivewindow"])
        texto = salida.strip()
        if rc == 0 and texto:
            try:
                numero = int(texto, 16) if texto.startswith("0x") else int(texto)
            except ValueError:
                return None
            return "0x%08x" % numero
    return None


def accion_sobre_activa(que: str) -> dict:
    """Maximizar / restaurar / minimizar la ventana que está al frente (S2 y voz).

    Se actúa sobre `:ACTIVE:` y no sobre un título: el gesto no dice qué ventana es,
    y elegir una a ciegas movería otra cosa. Después se verifica el estado real.
    """
    banderas = {"maximizar": "add,maximized_vert,maximized_horz",
                "restaurar": "remove,maximized_vert,maximized_horz",
                "minimizar": "add,hidden"}
    if que not in banderas:
        return resultado(que + "_activa", False, "orden de ventana desconocida", "no disponible")
    if not _hay("ventanas_acciones"):
        return resultado(que + "_activa", False, "no está wmctrl", "no disponible")
    if not ventanas():
        return resultado(que + "_activa", False, "no hay ninguna ventana abierta en este equipo")
    rc, _, err = _correr(["wmctrl", "-r", ":ACTIVE:", "-b", banderas[que]])
    return resultado(que + "_activa", rc == 0,
                     err[:120] or f"{que} sobre la ventana al frente", origen="real",
                     ventanas=len(ventanas()))


def cambiar_ventana(direccion: str = "siguiente") -> dict:
    """Pasar el foco a la ventana siguiente o anterior de la lista real."""
    vs = ventanas()
    if len(vs) < 2:
        return resultado("cambiar_ventana", False,
                         f"hay {len(vs)} ventana(s): no hay a dónde cambiar")
    activa = ventana_activa()
    ids = [w["id"] for w in vs]
    try:
        i = ids.index(activa) if activa else 0
    except ValueError:
        i = 0
    paso = 1 if direccion != "anterior" else -1
    destino = vs[(i + paso) % len(vs)]
    rc, _, err = _correr(["wmctrl", "-i", "-a", destino["id"]])
    despues = ventana_activa()
    ok = rc == 0 and (despues == destino["id"] or despues is None)
    return resultado("cambiar_ventana", ok,
                     err[:120] or f"foco en «{destino['titulo']}»",
                     titulo=destino["titulo"], total=len(vs))


# ------------------------------------------------------------------ volumen ----
def volumen_actual() -> dict:
    sink = _correr(["pactl", "get-default-sink"])[1].strip()
    if not sink:
        return {"sink": None, "porcentaje": None, "mudo": None}
    rc, salida, _ = _correr(["pactl", "get-sink-volume", sink])
    m = re.search(r"(\d+)%", salida)
    rc2, mut, _ = _correr(["pactl", "get-sink-mute", sink])
    return {"sink": sink, "porcentaje": int(m.group(1)) if m else None,
            "mudo": "yes" in mut if rc2 == 0 else None}


def cambiar_volumen(destino=None, paso=None, mudo=None) -> dict:
    if not _hay("volumen"):
        return resultado("volumen", False, "no está pactl", "no disponible")
    antes = volumen_actual()
    if not antes["sink"]:
        return resultado("volumen", False, "PipeWire no reporta ningún sink")
    if mudo is not None:
        _correr(["pactl", "set-sink-mute", antes["sink"], "1" if mudo else "0"])
    if destino is None and paso is not None:
        base = antes["porcentaje"] if isinstance(antes["porcentaje"], int) else 50
        destino = max(0, min(150, base + paso))
    if destino is not None:
        destino = max(0, min(150, int(destino)))
        _correr(["pactl", "set-sink-volume", antes["sink"], f"{destino}%"])
    despues = volumen_actual()
    return resultado("volumen", True,
                     f"{antes['porcentaje']}% → {despues['porcentaje']}% en {despues['sink']}"
                     + (" (silenciado)" if despues["mudo"] else ""),
                     sink=despues["sink"], antes=antes["porcentaje"], ahora=despues["porcentaje"],
                     mudo=despues["mudo"],
                     nota="" if antes["sink"] != "auto_null" else
                     "el sink es auto_null: no hay altavoz físico conectado (HDMI o dongle USB)")


# -------------------------------------------------------------------- brillo ----
def brillo_actual() -> dict:
    for carp in Path("/sys/class/backlight").glob("*"):
        try:
            maximo = int((carp / "max_brightness").read_text().strip())
            actual = int((carp / "brightness").read_text().strip())
            return {"sensor": carp.name, "actual": actual, "maximo": maximo,
                    "porcentaje": round(100 * actual / max(maximo, 1))}
        except Exception:
            continue
    return {"sensor": None}


def cambiar_brillo(porcentaje=None, paso=None) -> dict:
    actual = brillo_actual()
    if not actual.get("sensor"):
        return resultado("brillo", False, "no hay /sys/class/backlight legible", "no disponible")
    ruta = Path("/sys/class/backlight") / actual["sensor"] / "brightness"
    maximo = actual["maximo"]
    destino = actual["actual"] if porcentaje is None else int(maximo * max(1, min(100, porcentaje)) / 100)
    if paso is not None:
        destino = max(1, min(maximo, actual["actual"] + int(maximo * paso / 100)))
    try:
        ruta.write_text(str(destino))
    except Exception:
        # Sin brilloctl y sin permiso sobre sysfs queda el truco de X11, que NO es
        # brillo real del panel: se dice, porque cambiar el gamma no es bajar la luz.
        rc, _, err = _correr(["xrandr", "--output", ":0.0", "--brightness",
                             f"{max(0.3, min(1.0, destino / max(maximo, 1))):.2f}"])
        return resultado("brillo", rc == 0,
                         "no se puede escribir en /sys (falta brilloctl o permisos); "
                         "se aplicó gamma de X11, que aclara la imagen pero no baja la luz real",
                         sensor=actual["sensor"], medido=actual["porcentaje"],
                         hace_falta="brillo o sudo sobre /sys/class/backlight")
    return resultado("brillo", True, f"brillo al {round(100*destino/maximo)}%",
                     sensor=actual["sensor"], medido=actual["porcentaje"])


# --------------------------------------------------------------- multimedia ----
TECLAS = {"play": "XF86AudioPlay", "pause": "XF86AudioPause", "stop": "XF86AudioStop",
          "next": "XF86AudioNext", "prev": "XF86AudioPrev", "mute": "XF86AudioMute",
          "mas": "XF86AudioRaiseVolume", "menos": "XF86AudioLowerVolume"}


def tecla_media(que: str) -> dict:
    """Sin playerctl en este equipo se envía la tecla del reproductor por X11.

    Es honesto decir la diferencia: una tecla XF86 la atiende el reproductor que
    escucha atajos globales; no es un control directo del proceso de VLC.
    """
    if que not in TECLAS:
        return resultado("media", False, "tecla desconocida", teclas=list(TECLAS))
    if not _hay("teclas_media"):
        return resultado("media", False, "no está xdotool", "no disponible",
                         hace_falta="paquete xdotool (está instalado en este equipo)")
    rc, _, err = _correr(["xdotool", "key", TECLAS[que]])
    return resultado("media", rc == 0,
                     (err[:100] or f"tecla {TECLAS[que]} enviada"),
                     metodo="atajo de X11 (no hay playerctl instalado)",
                     reproductor="vlc" if shutil.which("vlc") else None)


# ------------------------------------------------------------------ notificar ----
def notificar(texto: str, titulo: str = "CORT") -> dict:
    if not _hay("notificar"):
        return resultado("notificar", False, "no está notify-send", "no disponible")
    rc, _, err = _correr(["notify-send", titulo[:80], (texto or "")[:400]])
    return resultado("notificar", rc == 0, err[:120] or "notificación enviada al escritorio")


def captura_pantalla() -> dict:
    if not _hay("captura"):
        return resultado("captura", False, "no está scrot", "no disponible")
    casa = Path(os.environ.get("HOME", "/root")) / "Imágenes" / "cort"
    casa.mkdir(parents=True, exist_ok=True)
    ruta = casa / f"captura-{int(time.time())}.png"
    rc, _, err = _correr(["scrot", "--overwrite", str(ruta)], segundos=12)
    if rc != 0 or not ruta.is_file():
        return resultado("captura", False, err[:140] or "scrot no dejó archivo")
    return resultado("captura", True, f"guardada en {ruta}", archivo=str(ruta),
                     mb=round(ruta.stat().st_size / 1e6, 2))


# ------------------------------------------------------------ portapapeles ----
def portapapeles(texto=None, seleccion_primaria=False) -> dict:
    """Lee o escribe el portapapeles. Con `seleccion_primaria` lee lo subrayado,
    que es por donde entra la lectura en voz alta de F4."""
    if not _hay("portapapeles"):
        return resultado("portapapeles", False, "no está xclip", "no disponible")
    sel = ["-selection", "primary" if seleccion_primaria else "clipboard"]
    if texto is None:
        rc, salida, err = _correr(["xclip", "-o"] + sel, segundos=5)
        if rc != 0:
            return resultado("portapapeles", False,
                             err[:120] or "no hay texto seleccionado en el portapapeles")
        return resultado("portapapeles", True, "leído del portapapeles",
                         texto=salida[:4000], caracteres=len(salida))
    try:
        p = subprocess.Popen(["xclip"] + sel, stdin=subprocess.PIPE, text=True)
        p.communicate(str(texto)[:200000], timeout=6)
        return resultado("portapapeles", p.returncode == 0, "portapapeles actualizado",
                         caracteres=len(str(texto)))
    except Exception as e:
        return resultado("portapapeles", False, f"xclip falló: {type(e).__name__}")


# ----------------------------------------------------------------- fondo ----
def fondo_escritorio() -> dict:
    """Ruta real del fondo que usa XFCE, leída con xfconf-query (canal probado aquí)."""
    if not _hay("fondo"):
        return resultado("fondo", False, "no está xfconf-query", "no disponible")
    rc, salida, err = _correr(["xfconf-query", "-c", "xfce4-desktop", "-p",
                               "/backdrop/screen0/monitorVirtual-1/workspace0/last-image"])
    if rc != 0 or not salida.strip():
        # El nombre del monitor cambia entre equipos: se barre la propiedad raíz.
        rc2, arbol, _ = _correr(["xfconf-query", "-c", "xfce4-desktop", "-l"])
        rutas = [l.strip() for l in arbol.splitlines() if l.strip().endswith("last-image")]
        for r in rutas:
            rc3, valor, _ = _correr(["xfconf-query", "-c", "xfce4-desktop", "-p", r])
            if rc3 == 0 and valor.strip():
                salida = valor
                break
        else:
            return resultado("fondo", False, (err or "sin propiedad last-image en xfce4-desktop")[:140])
    ruta = Path(salida.strip())
    if not ruta.is_file():
        return resultado("fondo", True, f"la propiedad apunta a un archivo que no existe: {ruta}",
                         archivo=str(ruta), existe=False)
    return resultado("fondo", True, f"fondo actual: {ruta.name}", archivo=str(ruta),
                     existe=True, mb=round(ruta.stat().st_size / 1e6, 2))


# ------------------------------------------------------------- paquetes ----
def actualizaciones() -> dict:
    """Qué se puede actualizar con APT (lectura, sin tocar nada).

    Sustituye a `get_winget_upgrades` de la plantilla: winget no existe en Linux y
    mentir con un panel vacío era peor que decir el gestor que sí hay.
    """
    if not shutil.which("apt"):
        return resultado("actualizaciones", False, "no está apt en este equipo", "no disponible")
    rc, salida, err = _correr(["apt", "list", "--upgradable"], segundos=45)
    if rc != 0:
        return resultado("actualizaciones", False, (err or salida)[:200],
                         nota="apt list respondió con error; puede pedir disco o red")
    filas = []
    for linea in salida.splitlines():
        if "/" not in linea or "upgradable" not in linea:
            continue
        nombre = linea.split("/")[0]
        m = re.search(r"\[upgradable[^\]]*?\]", linea)
        partes = linea.split()
        filas.append({"nombre": nombre, "de": partes[1] if len(partes) > 1 else "",
                      "a": partes[2] if len(partes) > 2 else "",
                      "crudo": (m.group(0) if m else "")[:60]})
    return resultado("actualizaciones", True,
                     f"{len(filas)} paquetes con actualización disponible (leído con apt, sin instalar nada)",
                     upgrades=filas[:120],
                     nota="aplicarlas es una orden tuya con confirmación: apt-get upgrade gasta disco y reinicia servicios")


def programas_instalados() -> dict:
    """Listado de dpkg: reemplaza al desinstalador que leía el registro de Windows."""
    if not shutil.which("dpkg-query"):
        return resultado("programas", False, "no está dpkg-query", "no disponible")
    rc, salida, _ = _correr(["dpkg-query", "-W", "-f",
                             "${Package}\t${Version}\t${Installed-Size}\n"], segundos=30)
    programas = []
    for linea in salida.splitlines():
        p = linea.split("\t")
        if len(p) >= 2 and p[0]:
            try:
                tam = int(p[2]) if len(p) > 2 and p[2].strip("-") else 0
            except ValueError:
                tam = 0
            programas.append({"nombre": p[0], "version": p[1], "tamano_kb": tam})
    programas.sort(key=lambda x: -x["tamano_kb"])
    return resultado("programas", True, f"{len(programas)} paquetes instalados (dpkg)",
                     programs=programas[:400],
                     nota="desinstalar no es automático: hace falta tu confirmación y apt, no un registro de Windows")


# --------------------------------------------------------------- energía ----
def energia(que: str, confirmar: bool = False) -> dict:
    """Bloquear, suspender, apagar. Las dos últimas piden confirmación explícita."""
    orden = {"bloquear": ["loginctl", "lock-sessions"],
             "suspender": ["systemctl", "suspend"],
             "apagar": ["systemctl", "poweroff"],
             "reiniciar": ["systemctl", "reboot"]}.get(que)
    if not orden:
        return resultado("energia", False, "acción desconocida",
                         acciones=["bloquear", "suspender", "apagar", "reiniciar"])
    if que in ("apagar", "reiniciar") and not confirmar:
        return resultado("energia", False,
                         f"«{que}» cierra la sesión y puede tirar trabajo sin guardar; "
                         "se hace con confirmación explícita",
                         pide_confirmacion=True, accion=que)
    if not shutil.which(orden[0]):
        return resultado("energia", False, f"no está {orden[0]}", "no disponible")
    rc, _, err = _correr(orden, segundos=10)
    return resultado("energia", rc == 0, err[:120] or f"{que} enviado a {orden[0]}", accion=que)


# --------------------------------------------------------------------- estado ----
def inventario_herramientas() -> dict:
    """Qué hay y qué falta para que cada acción exista. Medido, no supuesto."""
    return {clave: {"programa": prog, "esta": bool(shutil.which(prog))}
            for clave, prog in HERRAMIENTAS.items()}


def estado_pc() -> dict:
    apps = apps_disponibles()
    vs = ventanas()
    return {"type": "pc_estado", "origen": "real",
            "apps": len(apps), "ventanas": len(vs),
            "ventanas_lista": [w["titulo"][:34] for w in vs[:8]],
            "volumen": volumen_actual(), "brillo": brillo_actual(),
            "herramientas": inventario_herramientas(),
            "fondo": fondo_escritorio().get("archivo"),
            "nota": "todas las cifras leídas de wmctrl, pactl, sysfs y los .desktop del equipo"}


def accion(nombre: str, datos: dict) -> dict:
    """Punto de entrada del puente: ejecuta la acción y la anota en el registro."""
    d = datos or {}
    r = _ejecutar(nombre, d)
    registrar(nombre, d, r)
    return r


def _ejecutar(nombre: str, d: dict) -> dict:
    if nombre in ("abrir_app", "abrir"):
        return abrir_aplicacion(d.get("objetivo") or d.get("app") or d.get("nombre") or "")
    if nombre == "abrir_url":
        return abrir_url(d.get("url") or d.get("objetivo") or "")
    if nombre == "abrir_carpeta":
        return abrir_carpeta(d.get("ruta") or d.get("objetivo") or "~")
    if nombre == "cerrar_ventana":
        return cerrar_ventana(d.get("objetivo") or d.get("titulo") or "")
    if nombre == "minimizar_ventana":
        return minimizar_ventana(d.get("objetivo") or d.get("titulo") or "")
    if nombre == "enfocar_ventana":
        return enfocar_ventana(d.get("objetivo") or d.get("titulo") or "")
    if nombre == "ventanas":
        vs = ventanas()
        return resultado("ventanas", bool(vs), f"{len(vs)} ventanas abiertas", ventanas=vs)
    # S2: las órdenes que llegan de un gesto no nombran ventana, actúan sobre la que
    # está al frente. Están también en la voz por el mismo motivo.
    if nombre in ("maximizar", "restaurar", "minimizar_activa"):
        return accion_sobre_activa("maximizar" if nombre == "maximizar" else
                                   "restaurar" if nombre == "restaurar" else "minimizar")
    if nombre == "cambiar_ventana":
        return cambiar_ventana(d.get("direccion") or d.get("objetivo") or "siguiente")
    if nombre == "volumen":
        return cambiar_volumen(destino=d.get("valor"), paso=d.get("paso"),
                               mudo=(1 if d.get("mudo") else 0 if d.get("mudo") is False else None))
    if nombre == "brillo":
        return cambiar_brillo(porcentaje=d.get("valor"), paso=d.get("paso"))
    if nombre == "media":
        return tecla_media(d.get("tecla") or d.get("objetivo") or "play")
    if nombre == "notificar":
        return notificar(d.get("texto") or d.get("objetivo") or "", d.get("titulo") or "CORT")
    if nombre == "captura":
        return captura_pantalla()
    if nombre == "portapapeles_leer":
        return portapapeles()
    if nombre == "seleccion_leer":
        return portapapeles(seleccion_primaria=True)
    if nombre == "portapapeles_escribir":
        return portapapeles(texto=d.get("texto") or "")
    if nombre == "fondo":
        return fondo_escritorio()
    if nombre == "actualizaciones":
        return actualizaciones()
    if nombre == "programas":
        return programas_instalados()
    if nombre == "apps":
        a = apps_disponibles()
        return resultado("apps", bool(a), f"{len(a)} entradas de escritorio", apps=a)
    if nombre == "energia":
        return energia(d.get("objetivo") or d.get("accion") or "bloquear",
                       confirmar=bool(d.get("confirmar")))
    return resultado(nombre or "(vacío)", False, "esa acción no está en la lista de F5")


if __name__ == "__main__":
    # Auto-prueba: sólo lecturas, para poder correr esto sin tocar el equipo.
    import sys
    que = sys.argv[1] if len(sys.argv) > 1 else "estado"
    if que == "estado":
        print(json.dumps(estado_pc(), indent=2, ensure_ascii=False))
    elif que in ("ventanas", "apps", "fondo", "volumen_estado"):
        if que == "volumen_estado":
            print(json.dumps(volumen_actual(), ensure_ascii=False))
        else:
            print(json.dumps(accion(que, {}), indent=2, ensure_ascii=False)[:3000])
    elif que == "accion":
        print(json.dumps(accion(sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}),
                         indent=2, ensure_ascii=False))
    else:
        print(__doc__)
