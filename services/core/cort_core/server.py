import os
import re
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
from .actions import perform
from .brain import think
from .intents import match_intent
from .memory.facts import extract
from .memory.store import MemoryStore
from .outfit import pick_outfit
from .status import build as status_payload

app = FastAPI(title="CORT core")

# Cuántos recuerdos se conservan. No es sólo higiene del disco: `context_for`
# puede llegar a meter los más recientes en el prompt, y evaluar el prompt es lo
# caro de esta máquina (2 núcleos). Sin techo, la base de datos se haría grande y
# cada turno más lento.
MEMORY_KEEP = int(os.getenv("CORT_MEMORY_KEEP", "200"))

memory = MemoryStore()
memory.prune(keep=MEMORY_KEEP)

WHO_AM_I = re.compile(r"\b(cómo|como)\s+me\s+llamo\b|\b¿?qui[ée]n\s+soy\b|\bmi nombre\b", re.I)

def state(thinking=False):
    temp = float(os.getenv("CORT_CITY_TEMP_C", "22"))  # TODO: reemplazar por API de clima/sensor
    return {"type": "state", "outfit": pick_outfit(datetime.now().hour, temp),
            "mood": "calm", "thinking": thinking}

@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    history: list[dict] = []
    name = memory.name_of_user()
    await sock.send_json(state())
    await sock.send_json({"type": "assistant_message",
                          "text": f"Hola de nuevo, {name}." if name else "Hola, soy CORT.",
                          "mood": "calm"})
    # Después del saludo, no antes: `count()` es una lectura al disco, y lo
    # primero que debe notar quien abre la página es que CORT contesta.
    await sock.send_json(status_payload(memory, MEMORY_KEEP))
    try:
        while True:
            msg = await sock.receive_json()
            if msg.get("type") != "user_message":
                continue
            text = msg.get("text", "").strip()
            if not text:
                continue
            for fact in extract(text):
                memory.remember(fact)
            intent = match_intent(text)
            if intent:
                await sock.send_json({"type": "intent", **intent})
                ok, said = await perform(intent)
                # La onda marca el momento en que algo se ejecutó de verdad y el
                # rasgón cuando no: un holograma que parpadea todo el tiempo no
                # comunica nada.
                await sock.send_json({"type": "effect", "kind": "pulse" if ok else "glitch"})
                await sock.send_json({"type": "assistant_message",
                                      "text": said if ok else f"No pude: {said}.",
                                      "mood": "calm"})
                # Los hechos de un mensaje se guardan antes de mirar los intents,
                # así que el contador puede haber cambiado incluso sin LLM.
                await sock.send_json(status_payload(memory, MEMORY_KEEP))
                continue
            if WHO_AM_I.search(text):
                # Se responde desde la memoria, sin LLM: funciona aunque Ollama no esté.
                known = memory.name_of_user()
                reply = f"Te llamas {known}." if known else "Aún no me has dicho tu nombre."
                await sock.send_json({"type": "assistant_message", "text": reply, "mood": "calm"})
                continue
            history.append({"role": "user", "content": text})
            await sock.send_json(state(thinking=True))
            relevant = memory.context_for(text)
            context = [{"role": "system", "content": "Datos del usuario: " + "; ".join(relevant)}] if relevant else []
            reply = await think([*context, *history[-20:]])
            history.append({"role": "assistant", "content": reply})
            await sock.send_json({"type": "assistant_message", "text": reply, "mood": "calm"})
            await sock.send_json(state())
            # Después de `think()` es cuando `brain.last_model()` tiene algo que
            # decir: el panel nombra el modelo que acaba de contestar.
            await sock.send_json(status_payload(memory, MEMORY_KEEP))
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("CORT_PORT", "8765")))
