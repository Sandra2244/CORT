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
