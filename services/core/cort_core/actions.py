"""La capa de permisos: acciones reales sobre el sistema, y sólo las de la lista.

Regla 6 de `AGENTS.md`. Nada de aquí construye una orden a partir de texto:
`intents.py` produce una acción estructurada cuyo único dato es un `delta` entero
de *nuestra* tabla, y aquí se convierte en un argv fijo. El LLM no tiene camino
hasta el shell —`brain.py` devuelve texto y ese texto se pinta—, así que pedirle
que borre una carpeta no borra nada.

El `runner` es inyectable para que los tests comprueben el argv sin tocar el
audio real de esta máquina.
"""

import asyncio
import os
import re
from datetime import datetime
from pathlib import Path

SINK = "@DEFAULT_AUDIO_SINK@"

#: Donde caen las capturas. `~/Imágenes` es el XDG Pictures de esta máquina
#: (medido con `xdg-user-dir PICTURES`); con `CORT_SHOTS_DIR` se cambia.
SHOTS_DIR = Path(os.getenv("CORT_SHOTS_DIR") or Path.home() / "Imágenes" / "CORT")

#: Los únicos reproductores que se manejan por tecla. `playerctl` no está
#: instalado en el equipo de desarrollo, y una tecla XF86 la escucha el que
#: suene, sin saber qué suena.
MEDIA_KEYS = {"play": "XF86AudioPlay", "pause": "XF86AudioPause", "next": "XF86AudioNext"}

TIMEOUT_S = float(os.getenv("CORT_ACTION_TIMEOUT_S", "5"))


def enabled() -> bool:
    return os.getenv("CORT_SYSTEM_ACTIONS", "1") != "0"


def volume_argv(delta: int) -> list[str]:
    """`10%+` / `10%-`, y `-l 1.0` para que subir no pase del tope."""
    step = f"{abs(int(delta))}%" + ("+" if int(delta) > 0 else "-")
    return ["wpctl", "set-volume", "-l", "1.0", SINK, step]


def shot_path(now: datetime) -> Path:
    """Nombre de la captura, generado por nosotros.

    La marca de tiempo lleva microsegundos para que dos órdenes en el mismo
    segundo no se pisen: `-o` de scrot sobreescribe, y perder una captura por
    un nombre repetido no es un fallo que se vea.
    """
    return SHOTS_DIR / f"cort-{now:%Y%m%d-%H%M%S-%f}.png"


def screenshot_argv(path: Path) -> list[str]:
    return ["scrot", "-o", str(path)]


async def spawn(argv: list[str]) -> tuple[int, str]:
    """(returncode, salida). Ejecuta la lista, sin shell."""
    proc = None
    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            ),
            timeout=TIMEOUT_S,
        )
        out = (await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_S))[0]
    except (asyncio.TimeoutError, OSError) as err:
        # OSError es el mando no existiendo; TimeoutError, uno colgado. Ambos
        # son un hecho sobre el sistema, no una razón para dejar el bucle parado.
        if proc is not None:
            proc.kill()
        return 124, f"{type(err).__name__}: {err}"
    return proc.returncode, out.decode(errors="replace").strip()


def _percent(out: str) -> str | None:
    """Lee el nivel real que `wpctl get-volume` responde ("Volume: 0.60")."""
    m = re.search(r"Volume:\s*([0-9.]+)", out)
    if not m:
        return None
    return f"{round(float(m.group(1)) * 100)}"


async def _level(runner) -> str | None:
    code, out = await runner(["wpctl", "get-volume", SINK])
    return _percent(out) if code == 0 else None


async def perform(intent: dict, runner=None) -> tuple[bool, str]:
    """Ejecuta la acción y devuelve (ok, lo que CORT dice).

    `runner` se mira en cada llamada y no en la firma: así el test del protocolo
    lo sustituye sin tener que conocer el ejecutor, y la suite no le mueve el
    audio a nadie.

    El texto va en español porque es lo que lee Sandra.
    """
    runner = runner or spawn
    if not enabled():
        return False, "las acciones del sistema están apagadas (CORT_SYSTEM_ACTIONS=0)"

    action = intent.get("action")

    if action == "volume":
        try:
            delta = int(intent.get("delta") or 0)
        except (TypeError, ValueError):
            return False, "el delta de volumen no era un número"
        if not delta:
            return False, "no sabía cuánto mover el volumen"
        # Se lee antes y después, y lo que se afirma es la diferencia. `wpctl`
        # devuelve 0 aunque el destino no acepte el cambio — medido en este
        # portátil con el sink "Dummy Output": bajar un 10 % dejaba el nivel en
        # 1.00 y el returncode en 0. Filtrar por returncode diría "hecho".
        before = await _level(runner)
        code, out = await runner(volume_argv(delta))
        if code != 0:
            return False, f"no pude tocar el volumen: {out or f'wpctl devolvió {code}'}"
        after = await _level(runner)
        if after is None:
            return True, "Volumen ajustado."
        if before == after:
            return False, f"el mando obedeció pero el nivel sigue en {after} % (¿salida de audio en Dummy?)"
        return True, f"Volumen al {after} %."

    if action == "media":
        key = MEDIA_KEYS.get(intent.get("cmd"))
        if not key:
            return False, f"no tengo ese control de reproducción: {intent.get('cmd')}"
        code, out = await runner(["xdotool", "key", key])
        if code != 0:
            return False, f"no pude enviar la tecla: {out or f'xdotool devolvió {code}'}"
        return True, f"Enviar {key}."

    if action == "screenshot":
        path = shot_path(datetime.now())
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as err:
            return False, f"no puedo escribir en {path.parent}: {err.strerror or err}"
        code, out = await runner(screenshot_argv(path))
        if code != 0:
            return False, f"no pude tomar la captura: {out or f'scrot devolvió {code}'}"
        # La misma lección que con el volumen: el returncode no es la prueba de
        # que algo ocurriera. Sin archivo no hay captura, por muy bien que le
        # haya ido al mando.
        try:
            size = path.stat().st_size
        except OSError:
            return False, f"scrot respondió bien y {path.name} no apareció"
        if size < 1024:
            return False, f"la captura está vacía ({size} bytes)"
        return True, f"Captura guardada en «{path.name}» ({size // 1024} KB, en {path.parent})."

    return False, f"la acción «{action}» no está en la lista permitida"
