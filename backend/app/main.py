"""CORT backend — FastAPI.

Endpoints:
  POST /api/chat    {message}            -> {reply, source}
  GET  /api/status                       -> estado del cerebro híbrido + sistema
  GET  /api/history                      -> últimas respuestas recordadas
  POST /api/profile   {clave, valor}     -> memoria de preferencias
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

from fastapi import FastAPI                     # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel                  # noqa: E402

app = FastAPI(title="CORT", version="0.1.0")

# El holograma (Electron o navegador) habla con el backend solo desde localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
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
