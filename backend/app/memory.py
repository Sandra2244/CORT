"""Memoria persistente de CORT — SQLite, funciona igual en Linux y Windows."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "cort_memory.db"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB)
    c.execute(
        "CREATE TABLE IF NOT EXISTS conversacion ("
        " id INTEGER PRIMARY KEY, t REAL, rol TEXT, texto TEXT, fuente TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS perfil (clave TEXT PRIMARY KEY, valor TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS notas ("
        " id INTEGER PRIMARY KEY, t REAL, texto TEXT)"
    )
    return c


def remember(rol: str, texto: str, fuente: str = "") -> None:
    with _conn() as c:
        c.execute("INSERT INTO conversacion (t, rol, texto, fuente) VALUES (?,?,?,?)",
                  (time.time(), rol, texto, fuente))


def history(limit: int = 20) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT rol, texto FROM conversacion ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()[::-1]
    return [{"role": r, "content": t} for r, t in rows if r in ("user", "assistant")]


def set_profile(key: str, value: str) -> None:
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO perfil (clave, valor) VALUES (?,?)",
                  (key, value))


def get_profile() -> dict:
    with _conn() as c:
        return dict(c.execute("SELECT clave, valor FROM perfil").fetchall())


# ------------------------------------------------------------- notas (01 ·)
def add_note(texto: str) -> int:
    with _conn() as c:
        cur = c.execute("INSERT INTO notas (t, texto) VALUES (?,?)",
                        (time.time(), texto.strip()))
        return cur.lastrowid


def list_notes(limit: int = 50) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, t, texto FROM notas ORDER BY id DESC LIMIT ?",
            (limit,)).fetchall()
    import datetime as dt
    return [{"id": i, "fecha": dt.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M"),
             "texto": x} for i, t, x in rows][::-1]


def delete_note(note_id: int) -> bool:
    with _conn() as c:
        cur = c.execute("DELETE FROM notas WHERE id=?", (note_id,))
        return cur.rowcount > 0


# ------------------------------------------------- recuerdos (muro del cerebro)
def memories(limit: int = 24) -> list[dict]:
    """Recuerdos sueltos — notas e intercambios con el cerebro — para el muro
    de cuadros (la 'sala de recuerdos' de la referencia)."""
    import datetime as dt
    def fmt(t):
        return dt.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")
    out: list[dict] = []
    with _conn() as c:
        for t, texto, fuente in c.execute(
                "SELECT t, texto, fuente FROM conversacion ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall():
            out.append({"tipo": "charla", "texto": texto, "fuente": fuente or "—",
                        "fecha": fmt(t)})
        for t, texto in c.execute(
                "SELECT t, texto FROM notas ORDER BY id DESC LIMIT 10").fetchall():
            out.append({"tipo": "nota", "texto": texto, "fuente": "nota",
                        "fecha": fmt(t)})
    return sorted(out, key=lambda m: m["fecha"])[-limit:]
