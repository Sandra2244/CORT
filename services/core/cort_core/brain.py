import os
from datetime import datetime
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

SYSTEM = ("Eres CORT, un asistente personal con modales de mayordomo digital: "
          "sereno, cortés, elegante, curioso y directo, con un humor seco y discreto. "
          "Se te activa diciendo «OK CORT». "
          "Responde en el idioma del usuario, breve y útil. "
          "Tus respuestas se pueden leer en voz alta: habla natural, "
          "sin listas, sin markdown y sin emojis. "
          "No afirmes que puedes hacer algo si no estás segura: dilo con sinceridad.")

_DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre")


def system() -> str:
    """Las instrucciones de siempre más lo que un modelo no puede saber solo: qué
    día y qué hora es, y dónde está la usuaria. Sin esto, «¿qué hora es?» recibe
    «no tengo acceso a la hora» (se vio con Gemini). Se arma en cada petición:
    una hora fija en `SYSTEM` envejecería desde el arranque."""
    ahora = datetime.now().astimezone()
    extra = (f" Fecha y hora actuales: {_DIAS[ahora.weekday()]} {ahora.day} de "
             f"{_MESES[ahora.month - 1]} de {ahora.year}, {ahora:%H:%M} (hora local del equipo).")
    ciudad = (os.getenv("CORT_CITY") or "").strip()
    if ciudad:
        extra += f" La usuaria está en {ciudad}."
    # Las herramientas sólo se le ofrecen al modelo en la nube: uno de 0,5-3B no
    # sostiene el formato y convertiría la charla en JSON suelto. `CORT_TOOLS=0`
    # las apaga también para la nube.
    if provider() != "ollama" and os.getenv("CORT_TOOLS", "1") != "0":
        from .herramientas import instrucciones
        extra += instrucciones()
    return SYSTEM + extra


# -- Modelo en la nube (opcional) ---------------------------------------------
# Por defecto todo sigue siendo local: con `CORT_LLM_PROVIDER=ollama` (o sin
# poner nada) no sale ninguna petición de esta máquina. Un modelo de 0,5-3B que
# cabe en 8 GB responde flojo; para conversar de verdad se puede apuntar a una
# API. Es una decisión de la usuaria, y el costo de privacidad es real: lo que
# se escribe (y el contexto de memoria que se le suma) viaja al proveedor.
#
#   anthropic  -> API de Claude   (CORT_ANTHROPIC_API_KEY, CORT_ANTHROPIC_MODEL)
#   openai     -> cualquier API compatible con /chat/completions: Groq, Gemini,
#                 OpenRouter, OpenAI… (CORT_OPENAI_BASE_URL/API_KEY/MODEL)
#
# Si la nube falla (sin internet, clave mala, saldo agotado) se usa la cadena
# local de siempre, y la respuesta lo dice: un fallo callado se confunde con
# «el modelo es malo».
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
CLOUD_TIMEOUT_S = float(os.getenv("CORT_CLOUD_TIMEOUT_S", "60"))
# Holgado a propósito: en los Claude recientes el «pensar» cuenta contra
# `max_tokens`, y un tope de 120 deja la respuesta cortada antes del texto.
CLOUD_MAX_TOKENS = int(os.getenv("CORT_CLOUD_MAX_TOKENS", "1024"))


def provider() -> str:
    p = os.getenv("CORT_LLM_PROVIDER", "ollama").strip().lower()
    return p if p in ("anthropic", "openai") else "ollama"


class CloudError(Exception):
    """Un fallo de la nube con un motivo que se le puede enseñar a la usuaria."""


def _detail(resp: httpx.Response) -> str:
    """El mensaje de error del proveedor, venga como venga: Claude y OpenAI lo
    mandan como `{"error": {"message": ...}}`, pero Gemini a veces lo manda
    dentro de una lista, y otros sólo texto. Antes un 404 de Gemini salía pelado
    («error 404») y no decía que el modelo ya no existía."""
    msg = ""
    try:
        data = resp.json()
        if isinstance(data, list) and data:
            data = data[0]
        if isinstance(data, dict):
            err = data.get("error", data)
            msg = str(err.get("message", "")) if isinstance(err, dict) else str(err)
    except Exception:
        pass
    if not msg:
        msg = (resp.text or "").strip()
    # Ninguna clave sale en un mensaje, ni aunque el proveedor la repita.
    for var in ("CORT_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY", "CORT_OPENAI_API_KEY"):
        key = os.getenv(var)
        if key:
            msg = msg.replace(key, "***")
    return " ".join(msg.split())


def _reason(exc: Exception) -> str:
    """Motivo corto y legible. Nunca incluye cabeceras ni la clave."""
    if isinstance(exc, CloudError):
        return str(exc)
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        msg = _detail(exc.response)
        if code in (401, 403):
            return f"clave rechazada ({code})"
        if code == 429:
            return "límite de uso alcanzado (429)"
        return f"error {code}" + (f": {msg[:160]}" if msg else "")
    if isinstance(exc, httpx.TimeoutException):
        return "tardó demasiado"
    return "sin conexión"


def _alternating(history: list[dict]) -> list[dict]:
    """La API de Claude espera que la conversación empiece con el usuario."""
    msgs = [m for m in history if m.get("content")]
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    return msgs


async def _ask_anthropic(client: httpx.AsyncClient, history: list[dict]) -> tuple[str, str]:
    key = os.getenv("CORT_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise CloudError("falta CORT_ANTHROPIC_API_KEY en el .env")
    model = os.getenv("CORT_ANTHROPIC_MODEL", "claude-haiku-5-5").strip()
    body: dict = {"model": model, "max_tokens": CLOUD_MAX_TOKENS, "system": system(),
                  "messages": _alternating(history)}
    # `low`: la charla no necesita razonar a fondo y así responde rápido y barato.
    # Vacío lo desactiva (los modelos viejos no conocen el parámetro).
    effort = os.getenv("CORT_ANTHROPIC_EFFORT", "low").strip()
    if effort:
        body["output_config"] = {"effort": effort}
    r = await client.post(ANTHROPIC_URL, timeout=CLOUD_TIMEOUT_S, json=body,
                          headers={"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION})
    r.raise_for_status()
    text = "".join(b.get("text", "") for b in r.json().get("content", [])
                   if b.get("type") == "text").strip()
    if not text:
        raise CloudError("la respuesta llegó vacía")
    return text, f"anthropic:{model}"


async def _ask_openai(client: httpx.AsyncClient, history: list[dict]) -> tuple[str, str]:
    key = os.getenv("CORT_OPENAI_API_KEY")
    model = os.getenv("CORT_OPENAI_MODEL", "").strip()
    base = os.getenv("CORT_OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")
    if not key:
        raise CloudError("falta CORT_OPENAI_API_KEY en el .env")
    if not model:
        raise CloudError("falta CORT_OPENAI_MODEL en el .env")
    # OpenAI propiamente dicha cambió el nombre del tope; los demás siguen con el viejo.
    cap = "max_completion_tokens" if "api.openai.com" in base else "max_tokens"
    body: dict = {"model": model, cap: CLOUD_MAX_TOKENS,
                  "messages": [{"role": "system", "content": system()}, *history]}
    # Los modelos que «piensan» (Gemini 2.5, por ejemplo) gastan parte del tope en
    # pensar; `low` deja la charla rápida y con el tope entero para la respuesta.
    # Opcional: no todos los proveedores conocen el parámetro.
    effort = os.getenv("CORT_OPENAI_REASONING_EFFORT", "").strip()
    if effort:
        body["reasoning_effort"] = effort
    r = await client.post(f"{base}/chat/completions", timeout=CLOUD_TIMEOUT_S,
                          headers={"Authorization": f"Bearer {key}"}, json=body)
    r.raise_for_status()
    text = (r.json()["choices"][0]["message"].get("content") or "").strip()
    if not text:
        raise CloudError("la respuesta llegó vacía")
    return text, f"openai:{model}"


# Lo que hizo el último `think()`. `status.py` lo lee para que el panel de la
# interfaz nombre el modelo que respondió de verdad, no el que la cadena
# preferiría usar: con `qwen3:0.6b` fuera por tamaño, decir "qwen3" sería mentira.
_last: dict = {"model": None, "ollama": None, "cloud_error": None}


def last_model() -> str | None:
    return _last["model"]


def last_reachable() -> bool | None:
    """None = todavía no se ha intentado. No se afirma nada de Ollama sin haberlo probado."""
    return _last["ollama"]


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
    messages = [{"role": "system", "content": system()}, *history]
    own = client is None
    if own:
        client = httpx.AsyncClient(timeout=TIMEOUT_S)
    nota = ""
    try:
        if provider() != "ollama":
            try:
                ask = _ask_anthropic if provider() == "anthropic" else _ask_openai
                answer, name = await ask(client, history)
                _last["model"] = name
                _last["cloud_error"] = None
                return answer
            except Exception as exc:
                _last["cloud_error"] = _reason(exc)
                nota = f"[nube no disponible: {_last['cloud_error']}] "
        try:
            sizes = await _sizes(client)
            reachable = True
        except Exception:
            # Sin catálogo no hay forma de saber tamaños; se intenta igual,
            # pero el fallo final se reporta distinto (ver abajo).
            sizes = {}
            reachable = False
        _last["ollama"] = reachable
        for model in candidates(CHAIN, sizes):
            try:
                answer = await _ask(client, model, messages)
            except Exception:
                # Timeout o error: el siguiente de la cadena puede ser más
                # pequeño y sí responder a tiempo.
                continue
            _last["model"] = model
            return nota + answer
        _last["model"] = None
        if not reachable:
            return f"{nota}[modo eco: Ollama no responde] Dijiste: {last}"
        return f"{nota}[ningún modelo de la cadena respondió] Dijiste: {last}"
    except Exception:
        _last["model"] = None
        return f"{nota}[modo eco: Ollama no responde] Dijiste: {last}"
    finally:
        if own:
            await client.aclose()


