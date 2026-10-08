import asyncio
import os
import re
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

# El `.env` se lee **antes** del resto de los imports del paquete: `memory/store.py`
# fija su `DB_PATH` al importarse, y una ruta leída después llegaría tarde.
from .env import load_env
load_env()

from .actions import perform
from .brain import think
from .intents import match_intent
from .memory.facts import extract
from .memory.store import MemoryStore
from .outfit import pick_outfit
from .status import build as status_payload
from . import weather

app = FastAPI(title="CORT core")


@app.on_event("startup")
async def _start_weather() -> None:
    # Con `CORT_CITY` sin configurar `keep_updating` sale al instante: sin ciudad
    # no sale ni una petición de la máquina, y así quiere seguir CORT por defecto.
    app.state.weather = asyncio.create_task(weather.keep_updating())

# Cuántos recuerdos se conservan. No es sólo higiene del disco: `context_for`
# puede llegar a meter los más recientes en el prompt, y evaluar el prompt es lo
# caro de esta máquina (2 núcleos). Sin techo, la base de datos se haría grande y
# cada turno más lento.
MEMORY_KEEP = int(os.getenv("CORT_MEMORY_KEEP", "200"))

memory = MemoryStore()
memory.prune(keep=MEMORY_KEEP)

WHO_AM_I = re.compile(r"\b(cómo|como)\s+me\s+llamo\b|\b¿?qui[ée]n\s+soy\b|\bmi nombre\b", re.I)

def state(thinking=False):
    # El clima se lee de la caché, nunca se pide aquí: `state()` corre dentro del
    # bucle del WebSocket y una petición HTTP bloqueante pararía a todos los
    # clientes mientras el servicio de turno contesta.
    clima = weather.snapshot()
    temp = float(os.getenv("CORT_CITY_TEMP_C", "22")) if clima is None else clima["temp_c"]
    frame = {"type": "state", "outfit": pick_outfit(datetime.now().hour, temp),
             "mood": "calm", "thinking": thinking}
    if clima is not None:
        frame["city"] = clima["city"]
        frame["temp_c"] = clima["temp_c"]
    return frame

@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    history: list[dict] = []
    name = memory.name_of_user()
    await sock.send_json(state())
    # `greeting` y no `assistant_message`: el saludo es lo que CORT dice al
    # *presentarse*, y una reconexión no es una presentación. Medido en el
    # navegador: la pestaña que sobrevive a varios reinicios del core muestra el
    # reintento cada tres segundos, y acumuló cuatro «Hola, soy CORT.» seguidos.
    # La interfaz sólo pinta éste si el registro está vacío.
    await sock.send_json({"type": "greeting",
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
    # 127.0.0.1 por defecto, y no 0.0.0.0: el core no tiene autenticación ni TLS.
    # Publicarlo en la red es decisión explícita de quien arranca (`cort.py --lan`),
    # no un regalo del valor por defecto.
    uvicorn.run(app, host=os.getenv("CORT_HOST", "127.0.0.1"),
                port=int(os.getenv("CORT_PORT", "8765")))
