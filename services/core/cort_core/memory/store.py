"""Memoria persistente de CORT en SQLite.

Solo biblioteca estándar: la alternativa (sentence-transformers + faiss, como en la rama
scaffold) necesita ~1,5 GiB de RAM y esta máquina no la tiene.
"""
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "memory.db"

# Palabras que aparecen en cualquier frase y no identifican un recuerdo.
_STOP = {"como", "cual", "cuando", "donde", "porque", "para", "pero", "este", "esta",
         "esto", "eso", "esa", "ese", "que", "los", "las", "del", "con", "una", "uno",
         "por", "muy", "mas", "todo", "todos", "nada", "algo", "cosas", "mismo"}


def _stems(text: str) -> list[str]:
    """Raíces cortas: 'llamo' -> 'llam' coincide con 'llama' en el texto almacenado."""
    out = []
    for word in re.findall(r"\w+", text.lower()):
        if len(word) > 3 and word not in _STOP:
            out.append(word[:4])
    return out


class MemoryStore:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS memories (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   content TEXT NOT NULL UNIQUE,
                   created_at TEXT NOT NULL
               )"""
        )
        self.conn.commit()

    def remember(self, content: str) -> int:
        content = content.strip()
        if not content:
            raise ValueError("content no puede estar vacío")
        existing = self.conn.execute(
            "SELECT id FROM memories WHERE content = ?", (content,)
        ).fetchone()
        if existing:
            return existing["id"]
        cur = self.conn.execute(
            "INSERT INTO memories (content, created_at) VALUES (?, ?)",
            (content, datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        self.conn.commit()
        return cur.lastrowid

    def recall(self, query: str, limit: int = 3) -> list[str]:
        stems = _stems(query)
        if not stems:
            return []
        # Los placeholders se generan por cantidad, nunca con texto del usuario: no hay
        # inyección SQL posible aquí.
        where = " OR ".join(["content LIKE ?"] * len(stems))
        rows = self.conn.execute(
            f"SELECT content FROM memories WHERE {where} ORDER BY id DESC LIMIT ?",
            [f"%{stem}%" for stem in stems] + [limit],
        ).fetchall()
        return [row["content"] for row in rows]

    def all(self) -> list[str]:
        return [row["content"] for row in
                self.conn.execute("SELECT content FROM memories ORDER BY id")]

    def name_of_user(self) -> str | None:
        row = self.conn.execute(
            "SELECT content FROM memories WHERE content LIKE 'El usuario se llama%' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row["content"].split(" ", 4)[-1] if row else None

    def close(self):
        self.conn.close()
