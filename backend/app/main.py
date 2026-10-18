"""CORT backend — FastAPI.

Endpoints:
  POST /api/chat    {message}            -> {reply, source}
  GET  /api/status                       -> estado del cerebro híbrido + sistema
  GET  /api/history                      -> últimas respuestas recordadas
  POST /api/profile   {clave, valor}     -> memoria de preferencias
  GET  /api/files?path=                  -> explorador de carpetas (raíces seguras)
  GET  /api/tree?path=                   -> hijos de una carpeta con conteos (árbol lateral)
  GET  /api/memories                     -> muro de recuerdos (notas + conversaciones)
  GET  /api/weather                      -> clima actual (Open-Meteo, cacheado)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# carga .env antes de importar brain
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from brain import brain_status, think          # noqa: E402
import memory                                   # noqa: E402
import local_commands                           # noqa: E402
import sensors                                  # noqa: E402

from fastapi import FastAPI                     # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel                  # noqa: E402

app = FastAPI(title="CORT", version="0.1.0")

# El holograma (Electron o navegador) habla con el backend solo desde localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:8080", "http://127.0.0.1:8080",
                   "http://localhost:3000", "http://127.0.0.1:3000", "null"],
    allow_methods=["*"], allow_headers=["*"],
)


class Msg(BaseModel):
    message: str


class Perfil(BaseModel):
    clave: str
    valor: str


@app.post("/api/chat")
def chat(msg: Msg):
    question = msg.message.strip()
    if not question:
        return {"reply": "¿En qué puedo ayudarte?", "source": "local"}
    hist = memory.history()
    reply, source = think(question, hist)
    memory.remember("user", question)
    memory.remember("assistant", reply, source)
    return {"reply": reply, "source": source}


@app.get("/api/status")
def status():
    return {"brain": brain_status(), "system": local_commands.system_stats(),
            "battery": local_commands.battery()}


@app.get("/api/history")
def history(n: int = 10):
    with memory._conn() as c:
        rows = c.execute(
            "SELECT rol, texto, fuente, t FROM conversacion ORDER BY id DESC LIMIT ?",
            (n,)).fetchall()
    return [{"rol": r, "texto": t, "fuente": f, "t": ts} for r, t, f, ts in rows[::-1]]


@app.post("/api/profile")
def profile(p: Perfil):
    memory.set_profile(p.clave, p.valor)
    return {"ok": True}


@app.get("/api/profile")
def profile_get():
    return memory.get_profile()


class Nota(BaseModel):
    texto: str


@app.get("/api/notes")
def notes():
    return memory.list_notes()


@app.post("/api/notes")
def notes_add(n: Nota):
    if not n.texto.strip():
        return {"error": "nota vacía"}
    return {"id": memory.add_note(n.texto)}


@app.delete("/api/notes/{note_id}")
def notes_del(note_id: int):
    return {"ok": memory.delete_note(note_id)}


@app.get("/api/files")
def files(path: str = ""):
    return sensors.list_dir(path)


@app.get("/api/tree")
def tree(path: str = ""):
    """Hijos de una carpeta con sus conteos — para expandir el árbol lateral."""
    return sensors.tree(path)


@app.get("/api/memories")
def memories(n: int = 24):
    """Muro de recuerdos (notas + conversaciones) para la ventana Cerebro."""
    return {"recuerdos": memory.memories(n)}


@app.get("/api/weather")
def weather():
    return sensors.weather()


@app.get("/api/music")
def music():
    return {"canciones": sensors.music_list()}


@app.get("/api/audio")
def audio(ruta: str):
    from fastapi.responses import FileResponse
    f = sensors.music_path(ruta)
    if not f:
        return {"error": "archivo no encontrado o fuera de Música"}
    return FileResponse(f)


class Play(BaseModel):
    ruta: str = ""


@app.post("/api/play")
def play(p: Play):
    """Ejecutor de música en el SISTEMA: abre el reproductor predeterminado
    (VLC u otro) con una canción; sin ruta, elige una al azar de ~/Música."""
    return sensors.play_external(p.ruta)


class Launch(BaseModel):
    app: str = ""


@app.post("/api/launch")
def launch(l: Launch):
    """«Abre YouTube» → lanza la app de la LISTA BLISTA con el navegador
    predeterminado (referencia: APPLICATION LANCÉE del video francés)."""
    return sensors.launch_app(l.app)
