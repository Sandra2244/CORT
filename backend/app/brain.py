"""CORT — cerebro híbrido.

Ruta de decisión (automática, según el equipo donde esté instalado):
  1. Comando local instantáneo  -> sin IA, sin internet (hora, batería, CPU...)
  2. Cerebro LOCAL  (Ollama en localhost:11434, si está disponible)
  3. Cerebro ONLINE (Groq, luego Gemini, si hay API key en .env)
  4. Modo supervivencia offline (respuestas útiles sin IA)

CORT_MODE en .env fuerza la ruta: auto | local | online | offline
"""
from __future__ import annotations

import os
import re
import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
MODE = os.environ.get("CORT_MODE", "auto").lower()

SYSTEM_PROMPT = (
    "Eres CORT (Cognitive Orchestrator / Real-Time), un asistente personal "
    "holográfico inspirado en JARVIS y Cortana. Hablas español natural (túneame "
    "al idioma del usuario). Breve, preciso, con ligera elegancia británica tipo "
    "JARVIS ('a sus órdenes', 'señoría' solo en broma). Cuando no puedas hacer "
    "algo físico, dime exactamente qué comando o botón lo haría."
)


def system_prompt() -> str:
    """SYSTEM_PROMPT + preferencias del perfil (ventana PERFIL / POST /api/profile)."""
    try:
        try:
            import memory  # uvicorn importa app/ en sys.path (módulo plano)
        except ImportError:
            from . import memory  # modo paquete (from app import brain)
        p = memory.get_profile() or {}
    except Exception:
        p = {}
    extra = []
    if p.get("asistente"):
        extra.append(f"Tu nombre es {p['asistente']} (el usuario lo eligió).")
    if p.get("usuario"):
        extra.append(f"El usuario se llama {p['usuario']}; salúdalo por su nombre.")
    if p.get("tono"):
        extra.append(f"Tono: {p['tono']}.")
    if p.get("idioma"):
        extra.append(f"Idioma preferido: {p['idioma']}.")
    return SYSTEM_PROMPT + (" " + " ".join(extra) if extra else "")

# ---------------------------------------------------------------- utilidades
def _ollama_available() -> bool:
    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.5).status_code == 200
    except Exception:
        return False


def _ollama_chat(message: str, history: list[dict]) -> str:
    msgs = [{"role": "system", "content": system_prompt()}] + history[-8:] + [
        {"role": "user", "content": message}]
    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={"model": OLLAMA_MODEL, "messages": msgs, "stream": False},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def _groq_chat(message: str, history: list[dict]) -> str:
    msgs = [{"role": "system", "content": system_prompt()}] + history[-12:] + [
        {"role": "user", "content": message}]
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}"},
        json={"model": "llama-3.3-70b-versatile", "messages": msgs,
              "max_tokens": 700, "temperature": 0.6},
        timeout=40,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _gemini_chat(message: str, history: list[dict]) -> str:
    contents = [{"role": "user" if h["role"] == "user" else "model",
                 "parts": [{"text": h["content"]}]} for h in history[-12:]]
    contents.append({"role": "user", "parts": [{"text": message}]})
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}",
        json={"system_instruction": {"parts": [{"text": system_prompt()}]},
              "contents": contents},
        timeout=40,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def _offline_reply(message: str) -> str:
    m = message.lower()
    if "hola" in m or "buen" in m:
        return ("Hola, soy CORT en modo supervivencia (sin red ni cerebro local). "
                "Puedo darte hora, estado del sistema y clima si hay red. "
                "Para conversación completa configura GROQ_API_KEY o instala Ollama.")
    return ("Estoy en modo offline: sin API configurada ni Ollama disponible. "
            "Los comandos locales (hora, fecha, batería, CPU) siguen operativos.")


# ------------------------------------------------------- comandos locales
def local_command(message: str) -> str | None:
    """Coincidencias instantáneas, sin IA ni internet. Devuelve None si no aplica."""
    import local_commands  # mismo carpeta app/ (en sys.path vía main.py)
    m = message.lower().strip()
    if re.search(r"\b(hora|qué hora|que hora)\b", m):
        return local_commands.now()
    if re.search(r"\bfecha|día (es|hoy)|dia (es|hoy)\b", m):
        return local_commands.today()
    if re.search(r"\b(batería|bateria|battery)\b", m):
        return local_commands.battery()
    if re.search(r"\b(cpu|procesador|ram|memoria|estado del sistema)\b", m):
        return local_commands.system_stats()
    if re.search(r"\bclima|temperatura|qué tiempo|que tiempo\b", m):
        import sensors
        w = sensors.weather()
        return (f"Exterior: {w['temp']:.0f} °C, {w['cielo']}, viento {w['viento']:.0f} km/h."
                if w.get("ok") else "No pude obtener el clima (¿sin internet?).")
    if re.search(r"\b(archivos|carpetas|explorador)\b", m) and len(m) < 30:
        return ("Abriendo el panel de archivos en tu holograma. "
                "También puedes decirme: muestra documentos.")
    if re.search(r"\b(hola|buenas|buenos días|buenas tardes)\b", m) and len(m) < 24:
        return local_commands.greeting()
    return None


# ------------------------------------------------------------- entrada
def think(message: str, history: list[dict]) -> tuple[str, str]:
    """Devuelve (respuesta, fuente) donde fuente ∈
    local | ollama | groq | gemini | offline."""
    if MODE != "online":                 # incluso en 'auto' y 'local'
        cmd = local_command(message)
        if cmd:
            return cmd, "local"

    if MODE in ("auto", "local") and _ollama_available():
        try:
            return _ollama_chat(message, history), "ollama"
        except Exception:
            if MODE == "local":
                return _offline_reply(message), "offline"

    if MODE in ("auto", "online"):
        if GROQ_KEY:
            try:
                return _groq_chat(message, history), "groq"
            except Exception:
                pass
        if GEMINI_KEY:
            try:
                return _gemini_chat(message, history), "gemini"
            except Exception:
                pass

    return _offline_reply(message), "offline"


def brain_status() -> dict:
    return {
        "mode": MODE,
        "ollama": _ollama_available(),
        "ollama_model": OLLAMA_MODEL,
        "groq": bool(GROQ_KEY),
        "gemini": bool(GEMINI_KEY),
    }
