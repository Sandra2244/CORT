#!/usr/bin/env python3
"""Prueba de consola del puente CORT: habla el protocolo WebSocket sin abrir el
navegador, para no gastar la RAM de la Canaima en una pestaña de más.

Uso:
    python3 cort_probe.py            #=status y sistema (rápido, no toca el disco)
    python3 cort_probe.py av         #+ auditoría del antivirus con tiempos
    python3 cort_probe.py modelos    #+ inventario del disco, catálogo y puertas de RAM
    python3 cort_probe.py clima      #+ clima por IP, por ciudad escrita y ciudad falsa
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


async def oir(ws, tipos, segundos=45, etiquetas=(), parar_al_primero=False):
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
        if t == "av_complete" or (t == "ollama_pull_progress" and d.get("done")) or (parar_al_primero and sal):
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

            if modo == "modelos":
                # Inventario leído en disco + lo que pasará al elegir modelo.
                await ws.send_str(json.dumps({"type": "check_ollama_status"}))
                r = await oir(ws, {"ollama_status_reply"}, 15, parar_al_primero=True)
                st = (r[0].get("status") or {}) if r else {}
                libre = st.get("ram_disponible_mb") or 0
                print(f"  online={st.get('online')} · RAM libre={libre} MB "
                      f"de {st.get('ram_total_mb')} · núcleos {st.get('nucleos')}")
                for n, dat in sorted((st.get("en_disco") or {}).items(), key=lambda kv: kv[1]["ram_est"]):
                    print(f"    {n:22s} {dat['mb']:5d} MB  pide ~{dat['ram_est']} MB  → "
                          f"{'CABE' if libre >= dat['ram_est'] else 'no cabe'}")
                cat = st.get("catalogo") or {}
                print(f"  catálogo: {len(cat)} entradas "
                      f"(instaladas: {sum(1 for v in cat.values() if v.get('instalado'))})")

                await ws.send_str(json.dumps({"type": "get_agent_models"}))
                await oir(ws, {"agent_models_info"}, 10, parar_al_primero=True)

                for m in ("smollm2:135m", "dolphin3"):
                    await ws.send_str(json.dumps({"type": "set_local_model", "model": m}))
                    print(f"[elegir {m}]")
                    await oir(ws, {"local_model_set"}, 10, parar_al_primero=True)

                await ws.send_str(json.dumps({"type": "pull_ollama_model", "model": "smollm2:135m"}))
                print("[bajar algo que ya está]")
                await oir(ws, {"ollama_pull_progress"}, 20)

                # Dejar elegido el que sí existe: si no, el estado queda apuntando a
                # un modelo que no está en el disco.
                await ws.send_str(json.dumps({"type": "set_local_model", "model": "smollm2:135m"}))
                print("[volver al más ligero instalado]")
                await oir(ws, {"local_model_set"}, 10, parar_al_primero=True)

            if modo == "clima":
                # La prueba que destapó el bug: con una ciudad escrita a mano, ipapi
                # contesta "Invalid IP Address" y el panel quedaba vacío.
                for ciudad in ("", "Carora", "París", "NadaDeEsto"):
                    await ws.send_str(json.dumps({"type": "weather", "city": ciudad}))
                    print(f"[clima ciudad={ciudad or '(auto por IP)'}]")
                    r = await oir(ws, {"weather_panel"}, 25, parar_al_primero=True)
                    if r:
                        print("    " + json.dumps(r[0].get("data") or {}, ensure_ascii=False))

            if modo == "cerebro":
                pregunta = " ".join(sys.argv[2:]) or "Hola CORT, ¿qué eres?"
                await ws.send_str(json.dumps({"type": "user_input", "text": pregunta}))
                print("[cerebro] pregunta:", pregunta)
                await oir(ws, {"jarvis_text", "brain_used", "state"}, 200)

            await ws.close()


if __name__ == "__main__":
    asyncio.run(main())
