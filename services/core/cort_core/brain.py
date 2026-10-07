import os
import httpx

OLLAMA_URL = os.getenv("CORT_OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("CORT_MODEL", "qwen2.5:0.5b")
SYSTEM = ("Eres CORT, un asistente personal sereno, curioso y directo. "
          "Responde en el idioma del usuario, breve y útil.")

async def think(history: list[dict]) -> str:
    """history: [{'role':'user'|'assistant','content':str}]"""
    payload = {"model": MODEL, "stream": False,
               "messages": [{"role": "system", "content": SYSTEM}, *history]}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]
    except Exception:
        last = history[-1]["content"] if history else ""
        return f"[modo eco: Ollama no responde] Dijiste: {last}"
