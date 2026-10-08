import os
import re
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
from .brain import think
from .intents import match_intent
from .memory.facts import extract
from .memory.store import MemoryStore
from .outfit import pick_outfit

app = FastAPI(title="CORT core")
memory = MemoryStore()

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
                await sock.send_json({"type": "assistant_message", "text": f"Entendido: {intent['action']}.", "mood": "calm"})
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
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("CORT_PORT", "8765")))
