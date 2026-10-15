"""Lo único del core que habla con el sistema operativo de verdad.

Dos verbos, y ninguno recibe texto de la usuaria ni del modelo:

* `abrir(destino)`: pide al sistema que abra un archivo, carpeta, dirección web
  o `esquema:` con el programa que tenga registrado. Los destinos los fabrica
  `herramientas.py` desde listas cerradas y direcciones armadas con `quote`.
  **Sin shell**: en Windows es `os.startfile` (la API `ShellExecute`), así que
  nada de lo que contenga el destino se interpreta como una orden.
* `pulsar(tecla)`: manda una tecla multimedia o de volumen, como si se pulsara en
  el teclado. Es lo que hacen los reproductores y el mezclador de Windows: no hay
  que saber qué reproductor suena, igual que con el teclado físico.

Todo lo de Windows está detrás de `sys.platform == "win32"` y se importa
`ctypes` dentro de la función: en otro sistema este módulo se importa sin
efectos. **Sin verificar en Windows** (se escribió y probó con un ejecutor
falso, en un equipo Linux): las pruebas comprueban qué se pide, no qué hace el
sistema; quien lo usa en Windows es quien lo comprueba.
"""

from __future__ import annotations

import os
import subprocess
import sys

#: Códigos de tecla virtual de Windows (`VK_*`). Son números fijos de la API.
VK = {
    "silenciar": 0xAD,
    "bajar_volumen": 0xAE,
    "subir_volumen": 0xAF,
    "siguiente": 0xB0,
    "anterior": 0xB1,
    "play_pausa": 0xB3,
}
_VK_LWIN, _VK_SHIFT, _VK_S = 0x5B, 0x10, 0x53
_KEYUP = 0x0002


def es_windows() -> bool:
    return sys.platform == "win32"


def abrir(destino: str) -> None:
    """Abre `destino` con el programa del sistema. Lanza `OSError` si no hay uno."""
    if es_windows():
        os.startfile(destino)  # noqa: S606 - destino sale de listas cerradas
    elif sys.platform == "darwin":
        subprocess.Popen(["open", destino], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(["xdg-open", destino], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)


def pulsar(tecla: str, veces: int = 1) -> None:
    """Pulsa una tecla de `VK` `veces` veces. Sólo Windows; en otro sistema,
    `OSError`, para que quien llama lo diga en vez de fingir."""
    if not es_windows():
        raise OSError("las teclas multimedia sólo están implementadas en Windows")
    import ctypes
    vk = VK[tecla]
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    for _ in range(max(1, min(int(veces), 50))):
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, _KEYUP, 0)


def recorte() -> None:
    """Abre el recorte de pantalla de Windows (Win + Mayús + S)."""
    if not es_windows():
        raise OSError("el recorte de pantalla sólo está implementado en Windows")
    import ctypes
    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    for vk in (_VK_LWIN, _VK_SHIFT, _VK_S):
        user32.keybd_event(vk, 0, 0, 0)
    for vk in (_VK_S, _VK_SHIFT, _VK_LWIN):
        user32.keybd_event(vk, 0, _KEYUP, 0)


def bloquear() -> None:
    """Bloquea la sesión (lo mismo que Win + L)."""
    if not es_windows():
        raise OSError("bloquear la sesión sólo está implementado en Windows")
    import ctypes
    ctypes.windll.user32.LockWorkStation()  # type: ignore[attr-defined]
