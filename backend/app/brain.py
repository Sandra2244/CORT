"""CORT — cerebro híbrido.

Ruta de decisión (automática, según el equipo donde esté instalado):
  1. Comando local instantáneo  -> sin IA, sin internet (hora, batería, CPU...)
  2. Cerebro LOCAL  (Ollama en localhost:11434, si está disponible)
  3. Cerebro ONLINE (Groq, luego Gemini, si hay API key en .env)
  4. Modo supervivencia offline (respuestas útiles sin IA)

CORT_MODE en .env fuerza la ruta: auto | local | online | offline
(Se puede cambiar SIN reiniciar desde la ventana PERFIL → /api/config.)
"""
from __future__ import annotations

import re
import time

import requests

try:
    import config_store                      # uvicorn pone app/ en sys.path
except ImportError:                          # modo paquete (from app import brain)
    from . import config_store


def cfg() -> dict:
    """Ajustes vigentes EN ESTE MOMENTO: archivo de perfil > .env > default."""
    return config_store.raw()

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
def _ollama_available(c: dict | None = None) -> bool:
    c = c or cfg()
    try:
        return requests.get(f"{c['ollama_url']}/api/tags", timeout=1.5).status_code == 200
    except Exception:
        return False


def _ollama_chat(message: str, history: list[dict]) -> str:
    c = cfg()
    msgs = [{"role": "system", "content": system_prompt()}] + history[-8:] + [
        {"role": "user", "content": message}]
    r = requests.post(
        f"{c['ollama_url']}/api/chat",
        json={"model": c["ollama_model"], "messages": msgs, "stream": False},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def _groq_chat(message: str, history: list[dict]) -> str:
    c = cfg()
    msgs = [{"role": "system", "content": system_prompt()}] + history[-12:] + [
        {"role": "user", "content": message}]
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {c['groq_key']}"},
        json={"model": "llama-3.3-70b-versatile", "messages": msgs,
              "max_tokens": 700, "temperature": 0.6},
        timeout=40,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _gemini_chat(message: str, history: list[dict]) -> str:
    c = cfg()
    contents = [{"role": "user" if h["role"] == "user" else "model",
                 "parts": [{"text": h["content"]}]} for h in history[-12:]]
    contents.append({"role": "user", "parts": [{"text": message}]})
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{c['gemini_model']}:generateContent?key={c['gemini_key']}",
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
    c = cfg()
    mode = c["mode"]
    if mode != "online":                 # incluso en 'auto' y 'local'
        cmd = local_command(message)
        if cmd:
            return cmd, "local"

    if mode in ("auto", "local") and _ollama_available(c):
        try:
            return _ollama_chat(message, history), "ollama"
        except Exception:
            if mode == "local":
                return _offline_reply(message), "offline"

    if mode in ("auto", "online"):
        if c["groq_key"]:
            try:
                return _groq_chat(message, history), "groq"
            except Exception:
                pass
        if c["gemini_key"]:
            try:
                return _gemini_chat(message, history), "gemini"
            except Exception:
                pass

    return _offline_reply(message), "offline"


def brain_status() -> dict:
    c = cfg()
    return {
        "mode": c["mode"],
        "ollama": _ollama_available(c),
        "ollama_model": c["ollama_model"],
        "groq": bool(c["groq_key"]),
        "gemini": bool(c["gemini_key"]),
    }


# -------------------------------------------------- prueba del cerebro (Perfil)
GROQ_TEST_MODEL = "llama-3.1-8b-instant"


def test_all() -> list[dict]:
    """Prueba CADA cerebro disponible y reporta en milisegundos.
    Lo usa el botón «Probar cerebro» de la ventana PERFIL, para que pegar una
    clave tenga respuesta inmediata en pantalla en vez de un reinicio."""
    c = cfg()
    out: list[dict] = []

    def probe(name: str, fn, model: str, needs: str = "",
              ok_detail: str = "") -> None:
        if not needs:
            out.append({"proveedor": name, "ok": False,
                        "detalle": "sin configurar", "modelo": model, "ms": 0})
            return
        t0 = time.time()
        try:
            found = fn()
            out.append({"proveedor": name, "ok": True, "detalle": ok_detail,
                        "modelo": found or model,
                        "ms": int((time.time() - t0) * 1000)})
        except Exception as e:
            out.append({"proveedor": name, "ok": False,
                        "detalle": _nice_error(e), "modelo": model,
                        "ms": int((time.time() - t0) * 1000)})

    def ollama_ping():
        r = requests.get(f"{c['ollama_url']}/api/tags", timeout=3)
        r.raise_for_status()
        models = [m.get("name") for m in r.json().get("models", [])]
        return next((m for m in models if m == c["ollama_model"]),
                    models[0] if models else c["ollama_model"])

    probe("local (Ollama)", ollama_ping, c["ollama_model"],
          needs="siempre", ok_detail="sin modelos instalados")

    probe("Groq", lambda: requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {c['groq_key']}"},
        json={"model": GROQ_TEST_MODEL,
              "messages": [{"role": "user", "content": "responde solo: OK"}],
              "max_tokens": 5}, timeout=20).raise_for_status(),
        GROQ_TEST_MODEL, needs=c["groq_key"])

    def gemini():
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{c['gemini_model']}:generateContent?key={c['gemini_key']}",
            json={"contents": [{"parts": [{"text": "responde solo: OK"}]}]},
            timeout=25)
        r.raise_for_status()
        if not r.json().get("candidates"):
            raise RuntimeError("respuesta vacía")

    if c["gemini_key"]:
        probe("Gemini", gemini, c["gemini_model"])
    else:
        out.append({"proveedor": "Gemini", "ok": False, "detalle": "sin configurar",
                    "modelo": c["gemini_model"], "ms": 0})
    return out


def _nice_error(e: Exception) -> str:
    txt = str(e)
    if "401" in txt or "403" in txt:
        return "clave rechazada (401/403)"
    if "429" in txt:
        return "sin cuota libre ahora (429)"
    if "timeout" in txt.lower():
        return "tardó demasiado (sin red o saturada)"
    if "Failed to establish" in txt or "Connection" in txt:
        return "sin conexión"
    return txt[:60]

