import os
import httpx

OLLAMA_URL = os.getenv("CORT_OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("CORT_MODEL", "qwen2.5:0.5b")
# Medido en esta máquina (1.8 GiB, sin GPU): 0.53 tokens/s con el modelo ya
# cargado. Esos dos valores existen porque sin ellos cualquier respuesta corta
# tarda más de un minuto y el fallo se disfraza de servidor caído.
TIMEOUT_S = float(os.getenv("CORT_LLM_TIMEOUT_S", "180"))
MAX_TOKENS = int(os.getenv("CORT_LLM_MAX_TOKENS", "120"))
SYSTEM = ("Eres CORT, un asistente personal sereno, curioso y directo. "
          "Responde en el idioma del usuario, breve y útil.")

async def think(history: list[dict]) -> str:
    """history: [{'role':'user'|'assistant','content':str}]"""
    payload = {"model": MODEL, "stream": False,
               "options": {"num_predict": MAX_TOKENS},
               "messages": [{"role": "system", "content": SYSTEM}, *history]}
    last = history[-1]["content"] if history else ""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
            r = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]
    except httpx.TimeoutException:
        # Ollama está vivo pero no terminó a tiempo. Confundirlo con el caso
        # anterior hace buscar un servidor caído que no existe.
        return f"[el modelo tardó más de {TIMEOUT_S:.0f} s] Dijiste: {last}"
    except Exception:
        return f"[modo eco: Ollama no responde] Dijiste: {last}"

