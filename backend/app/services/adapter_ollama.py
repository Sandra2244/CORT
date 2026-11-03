import httpx
import asyncio
from typing import List, Any

class OllamaAdapter:
    def __init__(self, base_url: str, keep_alive: str = "2m"):
        self.base_url = base_url.rstrip('/')
        self.keep_alive = keep_alive

    async def generate(self, model: str, messages: List[Any]):
        """
        Llama al endpoint real de Ollama: POST /api/chat.
        (Antes apuntaba a /chat, que no existe, por eso el backend respondía error.)

        keep_alive libera el modelo de la RAM cuando dejas de usarlo: clave para
        que CORT no congele una laptop de 1,8 GB.
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.keep_alive,
            # num_ctx bajo = menos RAM. 2048 ya da contexto suficiente para charlar.
            "options": {"num_ctx": 2048, "num_thread": 2, "temperature": 0.7},
        }
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
