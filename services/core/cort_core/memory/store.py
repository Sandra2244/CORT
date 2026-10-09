"""Memoria persistente de CORT en SQLite.

Solo biblioteca estándar: la alternativa (sentence-transformers + faiss, como en la rama
scaffold) necesita ~1,5 GiB de RAM y esta máquina no la tiene.
"""
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# `CORT_MEMORY_DB` permite levantar otro CORT con otra cabeza: una demo, una
# segunda persona en el mismo PC, o una base vacía para una captura. Sin esto la
# única alternativa sería moverle a nadie su memory.db de en medio, y eso no se
# hace ni para sacar una foto.
DB_PATH = Path(os.getenv("CORT_MEMORY_DB")
               or Path(__file__).resolve().parents[2] / "data" / "memory.db")

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
        # check_same_thread=False: el store se construye al importar el módulo,
        # en el hilo principal, y la conexión no puede usarse desde otro hilo con
        # el valor por defecto — falla en la primera consulta. Hoy el bucle
        # asíncrono de uvicorn corre en ese mismo hilo, pero el test de protocolo
        # (TestClient) la atiende en uno de portal distinto. La desactivación es
        # segura mientras el acceso siga viniendo de un solo hilo a la vez.
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
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

    def count(self) -> int:
        """Cuántos recuerdos hay, sin traerlos.

        El panel de la interfaz pregunta esto en cada turno. `len(self.all())`
        daría el mismo número leyendo la base entera para enseñar un dígito.
        """
        return int(self.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0])

    def context_for(self, query: str, limit: int = 6) -> list[str]:
        """
        Lo que se mete en el prompt.

        `recall` coincide por raíces de 4 letras, así que "¿qué sabes de mí?" no
        encuentra "El usuario se llama Sandra": no comparten ninguna raíz. Sin
        ese rescate la pregunta llegaba al modelo sin contexto y CORT contestaba
        —con razón— que no sabía nada del usuario.

        El rescate **ya no es "los más recientes"**, que era lo que sonaba bien y
        medido resultó ruido: con 300 recuerdos de prueba "¿qué sabes de mí?" se
        traía cinco "Preferencia NNN" por ser los últimos y dejaba fuera el nombre.
        Ahora ordena por **qué dice** el recuerdo: primero cómo se llama la
        persona, después lo declarado como hecho propio (`El usuario …`,
        `Al usuario …`), y se rellena con el resto del más nuevo al más viejo.

        Una sola consulta con `CASE`, y no `all()` cortado en Python: leer la base
        entera para quedarse con seis filas es justo lo que `count()` evita. El
        `limit` importa: evaluar el prompt es lo caro de esta máquina.
        """
        hits = self.recall(query)
        if hits:
            return hits
        rows = self.conn.execute(
            """SELECT content FROM memories
               ORDER BY CASE
                          WHEN content LIKE 'El usuario se llama%' THEN 0
                          WHEN content LIKE 'El usuario %' OR content LIKE 'Al usuario %' THEN 1
                          ELSE 2
                        END,
                        id DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [row["content"] for row in rows]

    def name_of_user(self) -> str | None:
        row = self.conn.execute(
            "SELECT content FROM memories WHERE content LIKE 'El usuario se llama%' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row["content"].split(" ", 4)[-1] if row else None

    def prune(self, keep: int = 100) -> int:
        """
        Borra los recuerdos más antiguos dejando los `keep` recientes.

        Dos cosas que no son obvias:

        - La fila del nombre **nunca** se borra. De ella dependen el saludo al
          conectar y la respuesta a "¿cómo me llamo?"; podarla por ser la más
          antigua sería precisamente olvidar lo único que no se puede olvidar.
          Por eso el total tras podar puede ser keep + 1.
        - Se poda por `id`, no por `created_at`: los ids son únicos y crecen, así
          que el orden es estable aunque dos hechos se guarden en el mismo segundo.
        """
        cur = self.conn.execute(
            """DELETE FROM memories
               WHERE id NOT IN (SELECT id FROM memories ORDER BY id DESC LIMIT ?)
                 AND content NOT LIKE 'El usuario se llama%'""",
            (keep,),
        )
        self.conn.commit()
        return cur.rowcount


    def close(self):
        self.conn.close()
