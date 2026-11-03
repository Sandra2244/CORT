"""Prueba de F5 por el WebSocket, con las acciones que sí tocan el equipo.

Lanza VLC y lo cierra: es el round-trip completo (abrir -> ver la ventana ->
cerrarla) sobre una aplicación que no tiene trabajo sin guardar.
"""
import asyncio
import json
import sys

import websockets

ORDENES = [
    {"type": "pc_estado"},
    {"type": "pc_accion", "accion": "volumen", "paso": 0},
    {"type": "detect_apps"},
    {"type": "get_winget_upgrades"},
    {"type": "user_input", "text": "abre vlc"},
    {"type": "user_input", "text": "cierra la ventana vlc"},
]
ESPERADOS = ("pc_estado", "cort_accion", "detected_apps", "winget_upgrades",
             "jarvis_text", "user_input", "brain_used", "voz_audio", "state")


async def main():
    async with websockets.connect("ws://127.0.0.1:8765/ws") as w:
        parando = asyncio.Event()

        async def escucha():
            while not parando.is_set():
                try:
                    m = json.loads(await asyncio.wait_for(w.recv(), timeout=0.5))
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    return
                t = m.get("type") or m.get("action") or ""
                if t in ESPERADOS or "aviso" in t:
                    resumen = json.dumps({k: v for k, v in m.items()
                                          if k in ("type", "accion", "ok", "detalle", "nota",
                                                   "text", "apps", "upgrades", "ventanas",
                                                   "volumen", "brillo", "motor", "url", "motivo")},
                                         ensure_ascii=False)
                    print("<<", resumen[:330], flush=True)

        o = asyncio.create_task(escucha())
        for orden in ORDENES:
            await w.send(json.dumps(orden))
            print(">>", json.dumps(orden, ensure_ascii=False)[:90], flush=True)
            await asyncio.sleep(9 if "vlc" in json.dumps(orden) else 3)
        await asyncio.sleep(6)
        parando.set()
        o.cancel()
asyncio.run(main())
