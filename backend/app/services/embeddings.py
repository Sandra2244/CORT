import os
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import sqlite3

MODEL_NAME = os.environ.get('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'memory.db')
INDEX_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'faiss.index')

class EmbeddingsService:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._ensure_tables()
        self.index = None
        self._load_index()

    def _ensure_tables(self):
        cur = self.conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                content TEXT
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS embeddings_meta (
                id INTEGER PRIMARY KEY,
                dim INTEGER
            )
        ''')
        self.conn.commit()

    def _load_index(self):
        if os.path.exists(INDEX_PATH):
            try:
                self.index = faiss.read_index(INDEX_PATH)
            except Exception:
                self.index = None
        else:
            self.index = None

    def _save_index(self):
        if self.index is not None:
            faiss.write_index(self.index, INDEX_PATH)

    def add(self, user: str, content: str):
        cur = self.conn.cursor()
        cur.execute('INSERT INTO memory (user, content) VALUES (?,?)', (user, content))
        rowid = cur.lastrowid
        self.conn.commit()

        emb = self.model.encode([content])[0].astype('float32')
        if self.index is None:
            dim = emb.shape[0]
            self.index = faiss.IndexFlatL2(dim)
            cur.execute('INSERT OR REPLACE INTO embeddings_meta (id, dim) VALUES (1, ?)', (dim,))
            self.conn.commit()
        self.index.add(np.expand_dims(emb, axis=0))
        self._save_index()
        return rowid

    def query(self, q: str, k: int = 5):
        if self.index is None:
            return []
        emb = self.model.encode([q])[0].astype('float32')
        D, I = self.index.search(np.expand_dims(emb, axis=0), k)
        results = []
        cur = self.conn.cursor()
        for idx in I[0]:
            if idx == -1:
                continue
            # idx is 0-based index into index; map to rowid by ordering
            cur.execute('SELECT id, user, content FROM memory ORDER BY id LIMIT 1 OFFSET ?', (idx,))
            r = cur.fetchone()
            if r:
                results.append({'id': r[0], 'user': r[1], 'content': r[2]})
        return results

# singleton
_embeddings_singleton = None

def get_embeddings_service():
    global _embeddings_singleton
    if _embeddings_singleton is None:
        _embeddings_singleton = EmbeddingsService()
    return _embeddings_singleton
