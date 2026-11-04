"""Censo de funciones: manda cada orden de LEER al puente y apunta qué contestó.

Es la misma idea de `cort_probe.py menu`, pero con las fases que llegaron después
(F4 vida, S1 perfil, S2 visión, S4 memoria, U1 versión, F7 micrófono del teléfono)
y con el tiempo de respuesta medido.

Cada orden se compara contra el tipo de mensaje que el propio puente anuncia que
va a mandar (la tabla está leída en `cort_server.py`, no adivinada): así un
`no contestó` significa que de verdad no llegó nada, y no que esta sonda buscaba
el mensaje equivocado entre los que sí llegaban.

Sólo órdenes que leen. Las que mueven el equipo —`pc_accion`, `open_browser`,
`mic_on`, `vision_on`, `av_threat_action`, `start_ollama`, `pull_ollama_model`—
no están aquí a propósito: una prueba que abre VLC o enciende la cámara sin
pedirlo es peor que la función que comprueba.

Destino: el puente de arena (8775). Si se apunta a 8765 se está sondando el
puente vivo de la casa, y lo que se mida allí no es lo que se probó.
"""
import asyncio
import json
import os
import sys
import time

import websockets

PUERTO_WS = os.environ.get("CORT_WS_PORT", "8775")
URL = f"ws://127.0.0.1:{PUERTO_WS}/ws"

# orden -> (carga, mensaje que el puente promete devolver)
ORDENES = [
    ("system_stats", {}, "system_stats"),
    ("check_ollama_status", {}, "ollama_status_reply"),
    ("perfil_equipo", {}, "perfil_reply"),
    ("buscar_actualizacion", {}, "actualizacion"),
    ("get_settings", {}, "settings_data"),
    ("get_shopping_list", {}, "shopping_list"),
    ("vida_estado", {}, "vida_estado"),
    ("ha_get_states", {}, "ha_states"),
    ("temperatura", {}, "sala_temperatura"),
    ("weather", {"city": "Caracas"}, "weather_panel"),
    ("get_agent_models", {}, "agent_models_info"),
    ("check_jarvis_os_status", {}, "jarvis_os_status_reply"),
    ("check_local_tts_status", {}, "local_tts_status_reply"),
    ("voz_estado", {}, "voz_estado"),
    # mic_estado contesta con el inventario de voz completo: la misma respuesta
    # sirve para el altavoz y para el micro, y el puente no inventa un tipo nuevo.
    ("mic_estado", {}, "voz_estado"),
    ("vision_estado", {}, "vision_estado"),
    ("memoria_estado", {}, "memoria_estado"),
    ("check_kokoro_status", {}, "kokoro_status_reply"),
    ("pc_estado", {}, "pc_estado"),
    ("detect_apps", {}, "detected_apps"),
    ("get_installed_programs", {}, "installed_programs"),
    ("get_winget_upgrades", {}, "winget_upgrades"),
    ("games_get_library", {}, "games_library"),
    ("get_desktop_wallpaper", {}, "desktop_wallpaper_result"),
    ("av_scan_cancel", {}, "av_cancel"),
]

FRASES = [
    "hola CORT, qué eres",
    "qué sabes de mí",
    "qué hora es",
    "gracias",   # ninguna orden de actuar: este censo es 100 % de lectura
]

ESPERA = float(os.environ.get("CORT_PROBE_ESPERA", "25"))


async def espera_tipo(ws, tipo):
    t0 = time.monotonic()
    while time.monotonic() - t0 < ESPERA:
        try:
            m = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.4))
        except asyncio.TimeoutError:
            continue
        except websockets.ConnectionClosed:
            return None, int((time.monotonic() - t0) * 1000)
        if m.get("type") == tipo:
            return m, int((time.monotonic() - t0) * 1000)
    return None, int((time.monotonic() - t0) * 1000)


async def espera_respuesta(ws):
    """Una frase contestada llega como `jarvis_text` (el subtítulo completo)."""
    return await espera_tipo(ws, "jarvis_text")


def resume(m):
    if m is None:
        return "—", "—"
    origen = m.get("origen") or (m.get("status", {}) or {}).get("origen") \
        or (m.get("data", {}) or {}).get("origen") or "sin campo origen"
    for clave in ("text", "respuesta", "motivo", "nota"):
        if m.get(clave):
            return origen, str(m[clave])
    cuerpo = json.dumps({k: v for k, v in m.items() if k != "type"}, ensure_ascii=False)
    return origen, cuerpo


async def main():
    print(f"destino: {URL}" + ("" if PUERTO_WS != "8765" else "   << PUENTE VIVO >>"), flush=True)
    filas = []
    async with websockets.connect(URL, max_size=8 * 1024 * 1024) as ws:
        # el puente empuja solo al conectar (latido, perfil, iniciativa): se sacude
        # la bandeja antes de medir para no tomar un empujón por una respuesta.
        t0 = time.monotonic()
        while time.monotonic() - t0 < 2.5:
            try:
                await asyncio.wait_for(ws.recv(), timeout=0.4)
            except Exception:
                break

        for tipo, carga, esperado in ORDENES:
            await ws.send(json.dumps({"type": tipo, **carga}))
            m, ms = await espera_tipo(ws, esperado)
            origen, texto = resume(m)
            filas.append((tipo, esperado, origen, ms, texto))
            print(f"| {tipo} | {esperado} | {origen} | {ms} | {texto[:120]} |", flush=True)

        for f in FRASES:
            await ws.send(json.dumps({"type": "user_input", "text": f}))
            m, ms = await espera_respuesta(ws)
            origen, texto = resume(m)
            filas.append(("user_input", f, origen, ms, texto))
            print(f"| «{f}» | jarvis_text | {origen} | {ms} | {texto[:120]} |", flush=True)

    reales = sum(1 for x in filas if x[2] == "real")
    mudos = sum(1 for x in filas if x[4] == "—")
    print(f"\n{len(filas)} sondas · {reales} con origen real · {mudos} sin respuesta "
          f"en {ESPERA:.0f} s", flush=True)
    ruta = "/tmp/cort-inventario.md"
    with open(ruta, "w") as fp:
        fp.write("| orden | contesta | origen | ms | qué dice |\n|---|---|---|---|---|\n")
        for a, b, c, d, e in filas:
            fp.write(f"| {a} | {b} | {c} | {d} | {str(e)[:160].replace('|', '·')} |\n")
    print("tabla guardada en " + ruta, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
