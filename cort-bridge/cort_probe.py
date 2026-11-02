#!/usr/bin/env python3
"""Prueba de consola del puente CORT: habla el protocolo WebSocket sin abrir el
navegador, para no gastar la RAM de la Canaima en una pestaña de más.

Uso:
    python3 cort_probe.py            #=status y sistema (rápido, no toca el disco)
    python3 cort_probe.py av         #+ auditoría del antivirus con tiempos
    python3 cort_probe.py cerebro "pregunta"   #+ una pregunta al modelo local

Todo lo que se imprime lleva la marca origen=real o origen=simulado: el puente
nunca disfraza una simulación de medida.
"""
import asyncio
import json
import sys
import time

import aiohttp

WS = "ws://127.0.0.1:8765/ws"


async def oir(ws, tipos, segundos=45, etiquetas=()):
    """Devuelve los mensajes cuyo type está en `tipos` (o todos los de `etiquetas`)."""
    sal = []
    fin = time.monotonic() + segundos
    while time.monotonic() < fin:
        try:
            msg = await ws.receive(timeout=segundos)
        except Exception:
            break
        if msg.type != aiohttp.WSMsgType.TEXT:
            break
        d = json.loads(msg.data)
        t = d.get("type", "")
        if t in tipos or any(e in t for e in etiquetas):
            sal.append(d)
            print(f"  {t}: {json.dumps({k: v for k, v in d.items() if k != 'type'}, ensure_ascii=False)[:220]}")
        if t == "av_complete" or (t == "ollama_pull_progress" and d.get("done")):
            break
    return sal


async def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect(WS, timeout=10) as ws:
            t0 = time.monotonic()

            await ws.send_str(json.dumps({"type": "check_ollama_status"}))
            print("[cerebro]"); await oir(ws, {"ollama_status_reply"}, 10)

            await ws.send_str(json.dumps({"type": "system_stats"}))
            print("[sistema]"); await oir(ws, {"system_stats"}, 10)

            await ws.send_str(json.dumps({"type": "weather"}))
            print("[clima]"); await oir(ws, {"weather_panel"}, 15)

            if modo == "av":
                t_av = time.monotonic()
                await ws.send_str(json.dumps({"type": "av-scan"}))
                print("[antivirus] auditoría real:")
                r = await oir(ws, set(), 60, etiquetas=("av_",))
                print(f"  duración de la auditoría: {time.monotonic() - t_av:.1f} s · mensajes av_*: {len(r)}")

            if modo == "cerebro":
                pregunta = " ".join(sys.argv[2:]) or "Hola CORT, ¿qué eres?"
                await ws.send_str(json.dumps({"type": "user_input", "text": pregunta}))
                print("[cerebro] pregunta:", pregunta)
                await oir(ws, {"jarvis_text", "brain_used", "state"}, 200)

            await ws.close()


if __name__ == "__main__":
    asyncio.run(main())
