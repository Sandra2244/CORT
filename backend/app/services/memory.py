import os
import sqlite3
from typing import List

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'memory.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

class MemoryService:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._ensure()

    def _ensure(self):
        cur = self.conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                content TEXT
            )
        ''')
        self.conn.commit()

    def add(self, user: str, content: str):
        cur = self.conn.cursor()
        cur.execute('INSERT INTO memory (user, content) VALUES (?,?)', (user, content))
        self.conn.commit()

    def query(self, q: str, user: str | None = None, k: int = 5) -> List[dict]:
        cur = self.conn.cursor()
        if user:
            cur.execute('SELECT id, user, content FROM memory WHERE user = ? AND content LIKE ? ORDER BY id DESC LIMIT ?', (user, f'%{q}%', k))
        else:
            cur.execute('SELECT id, user, content FROM memory WHERE content LIKE ? ORDER BY id DESC LIMIT ?', (f'%{q}%', k))
        rows = cur.fetchall()
        return [{'id': r[0], 'user': r[1], 'content': r[2]} for r in rows]
