import httpx
import asyncio
from typing import List, Any

class OllamaAdapter:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    async def generate(self, model: str, messages: List[Any]):
        """
        Minimal async adapter to call a local Ollama-like HTTP chat endpoint.
        Adjust the endpoint or payload to match your Ollama version.
        """
        url = f"{self.base_url}/chat"
        payload = {
            "model": model,
            "messages": messages,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
