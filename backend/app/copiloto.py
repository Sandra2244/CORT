"""El copiloto de CORT — piensa el plan, y sólo ejecuta lo que no puede romper nada.

La dueña lo pidió con estas palabras: «CORT debe guiarte como copiloto y ejecutar
los comandos él solo». Aquí está, con la parte que se puede prometer en un producto
y la parte que no:

  · **Plan.** `plan(objetivo)` devuelve los pasos concretos, con el comando exacto
    de cada uno. Los saca el cerebro que esté puesto (Groq, Ollama de casa, Gemini)
    y, si no hay ninguno o contesta torcido, las plantillas de abajo — que son
    órdenes probadas, no inventadas. Nunca se queda en «no puedo» sin decir por qué.

  · **Ejecutar.** `ejecutar(token, indice)` corre UN paso, sin `shell`, con
    temporizador y salida cortada. Y sólo corre comandos de **sólo lectura**: tres
    listas escritas a mano, verbo por verbo — `LEE_SOLO` (el verbo mira siempre, con
    sus opciones prohibidas: `find -delete`, `tail -f`…), `SUB_LECTURA` (el verbo
    depende del suborden: `git status` sí, `git push` no; `systemctl status` sí,
    `systemctl stop` no) y `NUNCA` (`rm`, `sed -i`, `curl`, `apt`, `ssh`…). Lo que
    escribe, borra o instala **no se ejecuta aquí**, se enseña escrito para copiarlo
    y, si es de archivos, se manda por `/api/organizar`, que es el camino que ya
    tiene plan + token + confirmación de la dueña.

  · **Quien manda es ella.** `~/.cort/copiloto.json` (`{"permito": ["mkdir"], "nunca": ["df"]}`)
    añade o quita verbos. Se relee en cada ejecución, así que quitar un permiso
    surte en el acto. Lo que ella permita se ve en la cara con el sello
    «permitido por ti». `permito` no abre `NUNCA`: ni aun escrita se puede pedir
    una borrada en automático — eso sigue yendo por `/api/organizar`.

Por qué tan tieso: el mismo backend se sirve al teléfono por Wi-Fi (`scripts/telefono.sh`),
así que una puerta a ejecutar cualquier cosa en el portátil sería una puerta abierta
en la red de casa. Un copiloto que rompe la casa no es copiloto.

Sólo stdlib, sin dependencias nuevas.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import time
from pathlib import Path

# ───────────────────────────── la puerta de mando ────────────────────────────
# Cuánto tarda como máximo un paso y cuánta salida se guarda (el portátil es de
# 1,8 GiB: un `find` que suelta 200.000 líneas se comería la pestaña del WebView).
TIMEOUT_S = 25
SALIDA_MAX = 8000
TTL_S = 900                                  # el plan caduca a los 15 minutos

# Los verbos que se pueden correr solos, y las opciones que NUNCA se dejan aunque
# el verbo esté en la lista (una tupla vacía = todas sus opciones son de lectura).
LEE_SOLO: dict[str, tuple[str, ...]] = {
    "ls": (), "ll": (), "dir": (), "cat": (), "head": (), "tail": ("-f", "--follow"),
    "wc": (), "grep": (), "rg": (), "fgrep": (), "egrep": (),
    "find": ("-delete", "-exec", "-execdir", "-ok", "-okdir"),
    "fd": (), "tree": ("-o",), "stat": (), "file": (), "readlink": (),
    "du": (), "df": (), "lsblk": (), "lscpu": (), "lsusb": (), "lspci": (),
    "free": (), "ps": (), "pgrep": (), "uptime": (), "vmstat": (), "iostat": (),
    "uname": (), "hostname": (), "whoami": (), "id": (), "pwd": (), "which": (),
    "whereis": (), "type": (), "date": (), "cal": (), "env": (), "printenv": (),
    "sort": (), "uniq": (), "cut": (), "tr": (), "column": (), "jq": (),
    "basename": (), "dirname": (), "realpath": (), "md5sum": (), "sha256sum": (),
    "diff": (), "cmp": (), "lsof": (), "netstat": (),
    "ss": (), "ip": (), "ping": (), "traceroute": (), "dig": (), "host": (),
    "nslookup": (), "ifconfig": (), "arch": (), "locale": (), "tty": (),
    "inxi": (), "sensors": (), "nvidia-smi": (), "upower": (), "brightnessctl": (),
    "journalctl": (),
    "mediainfo": (), "ffprobe": (), "pdfinfo": (), "exiftool": (),
}

# Verbos que están en las dos listas a la vez: escriben según qué suborden usen,
# así que sólo se dejan cuando el suborden es de mirar. `git status` vale,
# `git push` no; `ollama list` vale, `ollama pull` no; `python3` sólo responde
# a «qué versión eres» y nunca corre un script.
SUB_LECTURA: dict[str, tuple[str, ...]] = {
    "git": ("status", "log", "diff", "show", "branch", "remote", "rev-parse",
            "describe", "blame", "shortlog", "ls-files", "--version"),
    "ollama": ("list", "ps", "version", "show", "tags"),
    "npm": ("ls", "outdated", "--version", "-v"),
    "pip": ("list", "show", "check"), "pip3": ("list", "show", "check"),
    "uv": ("list",),
    "docker": ("ps", "images", "version", "info", "inspect"),
    "systemctl": ("status", "show", "list-units", "list-unit-files", "is-active",
                  "is-enabled", "cat"),
    "crontab": ("-l",),
    "cargo": ("--version",),
    "java": ("--version", "-version"),
    "python": ("--version", "-V"), "python3": ("--version", "-V"),
    "node": ("--version", "-v"),
}


# Estos verbos se niegan SIEMPRE: son los que escriben, borran o no tienen vuelta
# atrás. Ni siquiera `permito` los abre — para eso está `/api/organizar`, que sí
# pide confirmación de la dueña paso por paso.
NUNCA = ("rm", "rmdir", "mv", "cp", "dd", "mkfs", "fdisk", "parted", "truncate",
         "chmod", "chown", "chgrp", "kill", "pkill", "killall", "shutdown", "reboot",
         "poweroff", "halt", "tee", "sed", "awk", "perl", "bash", "sh", "zsh", "fish",
         "sudo", "su", "doas", "mount", "umount", "apt", "apt-get", "dnf",
         "pacman", "yum", "snap", "flatpak", "gem",
         "curl", "wget", "tar", "zip", "unzip", "gzip", "bzip2", "rsync",
         "scp", "ssh", "nc", "ncat", "make", "kubectl",
         "eval", "source", "xargs", "gnome-terminal", "xdg-open")
# `git`, `pip`, `npm`, `cargo`, `docker`, `systemctl` y `crontab` no están en esta
# lista: viven en `SUB_LECTURA`, donde el mandamiento depende del suborden — por eso
# `git status` se ejecuta solo y `git push` se queda escrito.

# Plantillas probadas: lo que CORT propone cuando no hay cerebro, o cuando el
# cerebro contesta fuera de formato. Cada receta es un objetivo dicho por ella y
# sus pasos, todos de lectura y todos sin tuberías ni `$( )` — aquí no hay `shell`,
# así que un paso con `|` se quedaría escrito y no se ejecutaría nunca.
RECETAS: list[tuple[re.Pattern, str, list[str]]] = [
    (re.compile(r"\b(equip|portatil|portátil|maquina|máquina|ram|cpu|disco|sistema|diagnostico|diagnóstico)", re.I),
     "ver cómo está el equipo",
     ["uname -a", "lscpu", "free -h", "df -h", "ps aux --sort=-rss"]),
    (re.compile(r"\b(ocupa|espacio|llen|pesad|liber|disko)", re.I),
     "ver qué está ocupando el disco",
     ["df -h", "du -h --max-depth=1 ~", "du -h --max-depth=1 ~/Descargas"]),
    (re.compile(r"\b(duplicad|repetid|igual|mismo)", re.I),
     "buscar archivos repetidos por nombre",
     ["find ~ -maxdepth 3 -type f -name '*copia*'",
      "find ~ -maxdepth 3 -type f -name '*(*)*'"]),
    (re.compile(r"\b(version|instalad|que tengo|qué tengo|programas|paquetes)", re.I),
     "ver qué está instalado",
     ["python3 --version", "node --version", "git --version", "ollama list"]),
    (re.compile(r"\b(red|wifi|internet|conexi|conexion|caida|caída|lento)", re.I),
     "mirar la conexión",
     ["ip a", "ss -tunp", "ping -c 3 1.1.1.1"]),
    (re.compile(r"\b(pila|bater|energía|enegía|luz|brillo)", re.I),
     "mirar la batería y el brillo",
     ["upower -e", "upower -i /org/freedesktop/UPower/devices/battery_BAT0",
      "brightnessctl get"]),
    (re.compile(r"\b(foto|imagen|camara|cámara|exif|donde saqué|donde saque)", re.I),
     "mirar los datos de una foto",
     ["exiftool -m ~/Imágenes", "mediainfo ~/Imágenes"]),
    (re.compile(r"\b(git|repo|repositor|commit|cambios|rama)", re.I),
     "ver el estado de un repositorio",
     ["git status", "git log --oneline -n 15", "git diff --stat"]),
]


def _archivo_permisos() -> Path:
    return Path(os.environ.get("CORT_CASA", str(Path.home()))) / ".cort" / "copiloto.json"


def permisos() -> dict:
    """Lo que ella escribió a mano. Se relee siempre: quitar un permiso vale ya."""
    ruta = _archivo_permisos()
    datos = {"permito": [], "nunca": []}
    try:
        crudo = json.loads(ruta.read_text(encoding="utf8"))
        if isinstance(crudo, dict):
            for clave in ("permito", "nunca"):
                valor = crudo.get(clave)
                if isinstance(valor, list):
                    datos[clave] = [str(v) for v in valor]
    except (OSError, ValueError):
        pass                                  # sin archivo o torcido: la lista de casa
    return datos


def _suborden(argv: list[str]) -> str:
    """La palabra que decide si el comando mira o toca: el primer argumento sin
    guion (`git status` -> `status`), y si no lo hay, la bandera que trae
    (`git --version`, `crontab -l`). Con nada de eso devuelve ``."""
    for arg in argv[1:]:
        if not arg.startswith("-"):
            return arg
    for arg in argv[1:]:
        if arg in ("--version", "-version", "-v", "-V", "-l", "--list"):
            return arg
    return ""


def clasifica(argv: list[str]) -> dict:
    """¿Este comando se puede ejecutar solo? Devuelve {seguro, motivo}."""
    if not argv:
        return {"seguro": False, "motivo": "no hay comando"}
    verbo = Path(argv[0]).name
    extra = permisos()
    if verbo in extra.get("nunca", []):
        return {"seguro": False, "motivo": f"`{verbo}` lo quitaste tú en copiloto.json"}
    # 1) verbo que depende del suborden: `git status` sí, `git push` no
    if verbo in SUB_LECTURA:
        sub = _suborden(argv)
        if sub in SUB_LECTURA[verbo]:
            return {"seguro": True, "motivo": f"`{verbo} {sub}` es de sólo lectura",
                    "permitido_por_ella": verbo in extra.get("permito", [])}
        return {"seguro": False,
                "motivo": f"`{verbo} {sub or '…'}` toca el equipo; de `{verbo}` sólo se "
                          f"deja {', '.join(SUB_LECTURA[verbo])}"}
    # 2) verbo sin vuelta atrás: ni con permiso escrito
    if verbo in NUNCA:
        return {"seguro": False,
                "motivo": f"`{verbo}` escribe o no tiene vuelta atrás: CORT no lo ejecuta, "
                          "te lo deja escrito para que lo copies"}
    # 3) verbo de lectura, con sus opciones prohibidas (`find -delete`, `tail -f`)
    if verbo in LEE_SOLO:
        prohibidas = LEE_SOLO[verbo]
        for arg in argv[1:]:
            for mala in prohibidas:
                if arg == mala or arg.startswith(mala + "="):
                    return {"seguro": False,
                            "motivo": f"`{verbo} {mala}` no es de sólo lectura"}
        if any(re.search(r"[><|;&`$]", a) for a in argv[1:]):
            return {"seguro": False,
                    "motivo": "hay redirección, tubería o subshell: se queda escrito para ti"}
        return {"seguro": True, "motivo": "sólo lectura",
                "permitido_por_ella": verbo in extra.get("permito", [])}
    # 4) lo que ella añadió a mano en ~/.cort/copiloto.json
    if verbo in extra.get("permito", []):
        return {"seguro": True, "motivo": f"permitido por ti en {_archivo_permisos()}",
                "permitido_por_ella": True}
    return {"seguro": False,
            "motivo": f"`{verbo}` no está en la lista de sólo lectura (si quieres, "
                      "añádelo a ~/.cort/copiloto.json)"}


def _argv(orden: str) -> list[str]:
    """El comando partido en argumentos, sin `shell` y con la `~` de casa vuelta
    ruta real — `subprocess` no la expande y un `du ~` buscaría una carpeta «~»."""
    try:
        trozos = shlex.split(orden)
    except ValueError:
        return []
    return [os.path.expanduser(t) if "~" in t else t for t in trozos]


def _pasos_desde_cerebro(texto: str) -> list[str]:
    """El cerebro responde con JSON; si viene envuelto en ``` o con prosa, se limpia."""
    limpio = texto.strip()
    limpio = re.sub(r"^```(?:json)?\s*|\s*```$", "", limpio, flags=re.S)
    try:
        datos = json.loads(limpio)
    except ValueError:
        inicio = limpio.find("{")
        fin = limpio.rfind("}")
        if inicio < 0 or fin <= inicio:
            return []
        try:
            datos = json.loads(limpio[inicio:fin + 1])
        except ValueError:
            return []
    pasos = datos.get("pasos") if isinstance(datos, dict) else None
    if not isinstance(pasos, list):
        return []
    salida = []
    for paso in pasos[:8]:
        if isinstance(paso, dict):
            orden = str(paso.get("orden") or paso.get("comando") or "").strip()
        else:
            orden = str(paso).strip()
        if orden:
            salida.append(orden)
    return salida


def _pide_a_la_nube(objetivo: str) -> list[str]:
    try:
        import brain
    except ImportError:
        return []
    consigna = ('Eres el copiloto de terminal de CORT. Devuelve SOLO un objeto JSON con la forma '
                '{"pasos":[{"paso":"qué mira","orden":"comando"}]} y nada más. '
                'Reglas duras: comandos de SOLO LECTURA (mirar, listar, contar, version); '
                'nada de borrar, mover, instalar, escribir archivos ni pipe a cosas que escriban; '
                'sin `rm`, `mv`, `cp`, `sed -i`, `>>`, sudo ni descargas. '
                'Entre 2 y 5 pasos, en el orden en que se deben ejecutar, en español.')
    try:
        texto, _origen = brain.think(f"{consigna}\n\nObjetivo: {objetivo}", [])
    except Exception:
        return []
    return _pasos_desde_cerebro(texto)


def _recipe(objetivo: str) -> tuple[str, list[str]] | None:
    for rx, titulo, pasos in RECETAS:
        if rx.search(objetivo):
            return titulo, list(pasos)
    return None


_ULTIMO: dict = {}                         # el último plan en pie, con su token


def plan(objetivo: str) -> dict:
    """La propuesta de pasos, con su token. No ejecuta nada de nada."""
    objetivo = (objetivo or "").strip()
    if not objetivo:
        return {"ok": False, "dice": "dime qué quieres averiguar o hacer"}
    origin, pasos = "cerebro", _pide_a_la_nube(objetivo)
    if not pasos:
        receta = _recipe(objetivo)
        if receta:
            titulo, pasos = receta
            origin = "plantilla probada"
        else:
            # Sin cerebro y sin receta no se inventa un comando: se dice.
            return {"ok": False, "dice":
                    "no tengo un cerebro puesto ni una receta para eso, y no voy a inventar "
                    "el comando. Prueba con «diagnóstico del equipo», «qué ocupa espacio», "
                    "«busca duplicados» o «qué tengo instalado», o pon una nube en Ajustes.",
                    "objetivo": objetivo}
    filas = []
    for i, orden in enumerate(pasos, 1):
        argv = _argv(orden)
        veredicto = clasifica(argv) if argv else {"seguro": False, "motivo": "no se entiende"}
        filas.append({"indice": i - 1, "paso": f"paso {i}", "orden": orden, "argv": argv,
                      "seguro": bool(veredicto.get("seguro")), "motivo": veredicto.get("motivo", ""),
                      "permitido_por_ella": bool(veredicto.get("permitido_por_ella"))})
    token = hashlib.sha256((objetivo + json.dumps([f["orden"] for f in filas])
                            + str(time.time())).encode("utf8")).hexdigest()[:16]
    global _ULTIMO
    _ULTIMO = {"token": token, "objetivo": objetivo, "filas": filas, "a las": time.time()}
    seguros = sum(1 for f in filas if f["seguro"])
    return {"ok": True, "objetivo": objetivo, "origen": origin, "pasos": filas,
            "token": token, "caduca_en": TTL_S, "seguros": seguros,
            "dice": f"{len(filas)} pasos · {seguros} se pueden ejecutar solos · "
                    f"{len(filas) - seguros} quedan escritos para que los copies"}



def _vale(token: str) -> dict | None:
    if not _ULTIMO or _ULTIMO.get("token") != token:
        return None
    if time.time() - float(_ULTIMO.get("a las", 0)) > TTL_S:
        return None
    return _ULTIMO


def ejecutar(token: str, indice: int, forzar: bool = False) -> dict:
    """Corre UN paso del último plan. Con token viejo o paso peligroso, se niega.

    `forzar` no abre la puerta: sólo cambia el mensaje. Ningún comando de escritura
    se ejecuta desde aquí, ni con confirmación — para eso está `/api/organizar`."""
    plan_vivo = _vale(token)
    if not plan_vivo:
        return {"ok": False, "ejecutado": False,
                "dice": "ese plan ya no vale (caducó o pediste otro). Pide el plan otra vez."}
    try:
        i = int(indice)
    except (TypeError, ValueError):
        return {"ok": False, "ejecutado": False, "dice": "el índice del paso no se entiende"}
    filas = plan_vivo["filas"]
    if i < 0 or i >= len(filas):
        return {"ok": False, "ejecutado": False, "dice": f"ese paso no está en el plan (hay {len(filas)})"}
    fila = filas[i]
    veredicto = clasifica(fila["argv"])
    if not fila["seguro"] or not veredicto.get("seguro"):
        return {"ok": False, "ejecutado": False,
                "motivo": veredicto.get("motivo", "no es de sólo lectura"),
                "dice": f"no ejecuto `{fila['orden']}`: "
                        + veredicto.get("motivo", "no es de sólo lectura")}
    inicio = time.time()
    try:
        proceso = subprocess.run(fila["argv"], capture_output=True, text=True,
                                 timeout=TIMEOUT_S, check=False)
    except FileNotFoundError:
        return {"ok": False, "ejecutado": True, "codigo": 127,
                "dice": f"`{fila['argv'][0]}` no está en este equipo", "salida": ""}
    except subprocess.TimeoutExpired:
        return {"ok": False, "ejecutado": True, "codigo": -1,
                "dice": f"tardó más de {TIMEOUT_S} s y lo corté (nada se rompió)", "salida": ""}
    salida = (proceso.stdout or "") + (("\n" + proceso.stderr) if proceso.stderr else "")
    cortada = len(salida) > SALIDA_MAX
    return {"ok": proceso.returncode == 0, "ejecutado": True, "codigo": proceso.returncode,
            "salida": salida[:SALIDA_MAX], "cortada": cortada,
            "ms": int((time.time() - inicio) * 1000),
            "orden": fila["orden"],
            "dice": (f"salió bien en {int((time.time() - inicio) * 1000)} ms"
                     + (f" · la salida se corta en {SALIDA_MAX} caracteres" if cortada else ""))
                    if proceso.returncode == 0
                    else f"terminó con código {proceso.returncode}"}


def estado() -> dict:
    """Lo que la cara enseña en Ajustes: qué se puede ejecutar solo y qué no."""
    extra = permisos()
    return {"ok": True, "solo_lectura": sorted(LEE_SOLO),
            "subordenes_lectura": {v: list(s) for v, s in sorted(SUB_LECTURA.items())},
            "negados_siempre": sorted(NUNCA),
            "permito": extra.get("permito", []), "nunca": extra.get("nunca", []),
            "archivo": str(_archivo_permisos()),
            "recetas": [titulo for _rx, titulo, _p in RECETAS],
            "dice": f"{len(LEE_SOLO)} comandos de sólo lectura · "
                    f"{len(SUB_LECTURA)} que dependen del suborden · "
                    f"{len(extra.get('permito', []))} permitidos por ti"}
