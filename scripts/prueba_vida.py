"""Prueba de F4 por el WebSocket, sobre un puente en arena (CORT_DATOS /tmp).

Nada de esto toca la lista ni las notas de verdad: el puente de prueba arranca con
CORT_DATOS apuntando a /tmp y puertos 8775/8776. Se prueban las tres vías a la vez:
frase dictada/escrita, orden directa del panel y el vencimiento de un temporizador.
"""
import asyncio
import json
import sys

import websockets

PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8775
FRASES = [
    "cómprame leche, tres huevos y pan",
    "cómprame leche",
    "quita de la lista los huevos",
    "qué tengo que comprar",
    "anota que el suelo pelviano tiene tres capas",
    "mis notas",
    "recuerdame llamar a la tía en 10 minutos",
    "temporizador de 4 segundos",
    "léeme la selección",
    "qué tengo pendiente",
]
DIRECTAS = [{"type": "get_shopping_list"},
            {"type": "save_obsidian_note", "titre": "prueba puente", "content": "tres líneas"},
            {"type": "read_obsidian_note", "titre": "prueba puente"},
            {"type": "vida_estado"}]
MIRAR = ("jarvis_text", "shopping_list", "obsidian_notes", "obsidian_note_content",
         "vida_estado", "reminder_trigger", "puente_aviso", "timer_add")


async def main():
    vistos = []
    async with websockets.connect(f"ws://127.0.0.1:{PUERTO}/ws") as w:
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
                if t in MIRAR:
                    resumen = json.dumps({k: v for k, v in m.items() if k in
                                          ("type", "text", "items", "notes", "titre", "content",
                                           "origen", "motivo", "nota", "time", "datos",
                                           "compras", "pendientes", "resumen", "duration")},
                                         ensure_ascii=False)
                    print("<<", resumen[:420], flush=True)
                    vistos.append(m)

        o = asyncio.create_task(escucha())
        for f in FRASES[:8]:
            await w.send(json.dumps({"type": "user_input", "text": f}))
            print(">>", f, flush=True)
            await asyncio.sleep(4.5)
        await asyncio.sleep(6)          # que venza el temporizador de 4 segundos
        for d in DIRECTAS:
            await w.send(json.dumps(d))
            print(">>", json.dumps(d, ensure_ascii=False)[:90], flush=True)
            await asyncio.sleep(2.5)
        # la selección se queda para las dos últimas frases, después del panel
        await w.send(json.dumps({"type": "user_input", "text": FRASES[8]}))
        await asyncio.sleep(4)
        await w.send(json.dumps({"type": "user_input", "text": FRASES[9]}))
        await asyncio.sleep(5)
        parando.set()
        o.cancel()
    tipos = [v.get("type") for v in vistos]
    print("\nTIPOS VISTOS:", {t: tipos.count(t) for t in set(tipos)})
    print("¿SIN ORIGEN REAL?:", [v for v in vistos if v.get("origen") not in ("real", None)])
asyncio.run(main())
