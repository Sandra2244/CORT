"""Prueba de F3 por el camino del navegador: órdenes de voz y descarga del WAV."""
import asyncio
import json
import sys
import urllib.request

import websockets


async def main():
    async with websockets.connect("ws://127.0.0.1:8765/ws") as w:

        async def envia(o):
            await w.send(json.dumps(o))

        await envia({"type": "voz_estado"})
        await envia({"type": "av_speak",
                     "text": "CORT en línea. Esta es mi voz real en la Canaima."})
        await envia({"type": "check_kokoro_status"})
        await envia({"type": "toggle_mic"})
        t0 = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - t0 < 45:
            try:
                m = json.loads(await asyncio.wait_for(w.recv(), timeout=5))
            except asyncio.TimeoutError:
                continue
            t = m.get("type")
            if t in ("voz_estado", "voz_pedido", "voz_audio", "kokoro_status", "mic_estado"):
                rec = {k: v for k, v in m.items() if k != "dispositivos"}
                print("<<", json.dumps(rec, ensure_ascii=False)[:400], flush=True)
                if t == "voz_audio" and m.get("url"):
                    with urllib.request.urlopen("http://127.0.0.1:8766" + m["url"]) as r:
                        datos = r.read()
                        print("HTTP", r.status, len(datos), "bytes", datos[:4], flush=True)
                    return
asyncio.run(main())
