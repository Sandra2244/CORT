import os
import httpx

OLLAMA_URL = os.getenv("CORT_OLLAMA_URL", "http://localhost:11434")

# Cadena de sustitución: se usa el primero que responda. El orden importa y va
# de menos a más memoria.
CHAIN = [m.strip() for m in
         os.getenv("CORT_LLM_CHAIN", "qwen2.5:0.5b,qwen3:0.6b").split(",") if m.strip()]

TIMEOUT_S = float(os.getenv("CORT_LLM_TIMEOUT_S", "180"))
MAX_TOKENS = int(os.getenv("CORT_LLM_MAX_TOKENS", "120"))

# Techo de RAM del modelo, en MiB. No es un detalle de rendimiento: esta máquina
# tiene 1,8 GiB y cargar qwen3.5:2b (2,4 GiB en disco) la congeló hasta que
# hubo que apagarla a la fuerza. Un modelo que no cabe no se prueba, aunque
# esté instalado y aunque la cadena lo pida.
MAX_MODEL_MIB = float(os.getenv("CORT_LLM_MAX_MODEL_MIB", "700"))

# Medido aquí: con el modelo ya cargado un prompt de 50 tokens cuesta 0,9 s;
# recién cargado, 113 s. Sin keep_alive Ollama lo descarga a los 5 minutos y
# cada conversación empieza pagando esa descarga.
KEEP_ALIVE = os.getenv("CORT_LLM_KEEP_ALIVE", "30m")

SYSTEM = ("Eres CORT, un asistente personal sereno, curioso y directo. "
          "Responde en el idioma del usuario, breve y útil.")


async def _sizes(client: httpx.AsyncClient) -> dict[str, float]:
    """Nombre -> tamaño en MiB de lo que hay descargado. Vacío si no hay server."""
    r = await client.get(f"{OLLAMA_URL}/api/tags")
    r.raise_for_status()
    return {m["name"]: m["size"] / 2**20 for m in r.json().get("models", [])}


def candidates(chain: list[str], sizes: dict[str, float]) -> list[str]:
    """
    La cadena filtrada a lo que cabe en memoria.

    Un modelo que no aparece en `sizes` se deja pasar: puede ser uno que Ollama
    descargaría bajo demanda, y negarse por no verlo sería más restrictivo que
    la realidad. El que sí se ve y es demasiado grande se descarta siempre.
    """
    return [m for m in chain if sizes.get(m, 0) <= MAX_MODEL_MIB]


async def _ask(client: httpx.AsyncClient, model: str, messages: list[dict]) -> str:
    r = await client.post(
        f"{OLLAMA_URL}/api/chat",
        json={"model": model, "stream": False, "keep_alive": KEEP_ALIVE,
              "options": {"num_predict": MAX_TOKENS},
              "messages": messages},
    )
    r.raise_for_status()
    return r.json()["message"]["content"]


async def think(history: list[dict], client: httpx.AsyncClient | None = None) -> str:
    """history: [{'role':'user'|'assistant','content':str}]

    Prueba los modelos de la cadena en orden y devuelve la primera respuesta.
    Si ninguno sirve, modo eco: la interfaz sigue viva sin Ollama encendido.

    `client` existe para poder probar la cadena con un transporte simulado; sin
    él no hay forma de ejercitar el orden de sustitución sin encender Ollama de
    verdad, y encenderlo de verdad es lo que congeló esta máquina una vez.
    """
    last = history[-1]["content"] if history else ""
    messages = [{"role": "system", "content": SYSTEM}, *history]
    own = client is None
    if own:
        client = httpx.AsyncClient(timeout=TIMEOUT_S)
    try:
        try:
            sizes = await _sizes(client)
            reachable = True
        except Exception:
            # Sin catálogo no hay forma de saber tamaños; se intenta igual,
            # pero el fallo final se reporta distinto (ver abajo).
            sizes = {}
            reachable = False
        for model in candidates(CHAIN, sizes):
            try:
                return await _ask(client, model, messages)
            except Exception:
                # Timeout o error: el siguiente de la cadena puede ser más
                # pequeño y sí responder a tiempo.
                continue
        if not reachable:
            return f"[modo eco: Ollama no responde] Dijiste: {last}"
        return f"[ningún modelo de la cadena respondió] Dijiste: {last}"
    except Exception:
        return f"[modo eco: Ollama no responde] Dijiste: {last}"
    finally:
        if own:
            await client.aclose()


