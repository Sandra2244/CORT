"""CORT — cerebro híbrido.

Ruta de decisión (automática, según el equipo donde esté instalado):
  1. Comando local instantáneo  -> sin IA, sin internet (hora, batería, CPU, clima)
  2. Cerebro LOCAL  (Ollama en localhost:11434, si está disponible)
  3. Cerebro ONLINE (Groq, luego Gemini, si hay API key en .env)
  4. Modo supervivencia offline (respuestas útiles sin IA)

CORT_MODE en .env fuerza la ruta: auto | local | online | offline
(Se puede cambiar SIN reiniciar desde la ventana PERFIL → /api/config.)

Dos registros, un solo cerebro: `think()` decide si la frase es de código
(`es_programacion`) y baja `modo="coder"` a los tres cerebros, que manda otra
consigna de sistema (`CODER_PROMPT`) y más espacio de salida. No es otra IA, no
pide otra clave y no cuesta un segundo consumo.
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

# Segundo registro del mismo cerebro: cuando la pregunta es de código, el tono de
# «señoría» estorba y lo que sirve es lo técnico. Es el modo que elige `think()` al
# detectar lenguajes o herramientas, no una IA distinta ni una clave distinta: el
# cambio está sólo en el `system` que se manda.
CODER_PROMPT = (
    "Eres CORT en registro de programación. La usuaria está aprendiendo a programar "
    "desde cero, en español, en un portátil de 2 núcleos y 1,8 GiB de RAM (Linux "
    "Xfce), y su proyecto es C.O.R.T.: un asistente con interfaz web en JavaScript "
    "plano, backend en Python/FastAPI, escritorio en Electron y una app de Android "
    "compilada sin Gradle (aapt2 + kotlinc + d8). Responde en español con los términos "
    "técnicos en su idioma original. Da primero el código que funciona y después dos o "
    "tres líneas explicando qué hace cada parte; nada de párrafos de teoría. Si falta "
    "un dato para saberlo (versión, sistema, archivo), dilo en una frase y da la "
    "suposición más razonable marcada como suposición. Nunca inventes una API, una "
    "bandera ni un nombre de archivo: si no estás seguro, escribe «no lo sé, comprueba "
    "X». Si el snippet es largo, córtalo y di «¿seguimos?» en vez de volcar 200 líneas. "
    "Optimiza para equipo limitado: nada de instalar servidores ni modelos grandes."
)

# Palabras que por sí solas abren el registro de programación: un nombre de lenguaje,
# de herramienta o de pila. Están en minúsculas y se comparan como palabra SUELTA
# (el texto se rodea de espacios y se busca " python "), así que «go» dentro de
# «luego» no cuenta.
CODER_FUERTES = (
    "python javascript typescript kotlin java swift golang rust ruby php scala "
    "html css sql bash shell zsh powershell regex json yaml toml docker gradle "
    "git github electron nodejs node npm pip uvicorn fastapi flask django react "
    "vue three.js capacitor android apk aapt2 kotlinc javac d8 ffmpeg sqlite "
    "matplotlib numpy pandas pytest jest webpack vite eslint tailwind bootstrap "
    "unity godot unity3d markdown latex"
).split()

# Y las que abren sólo si van acompañadas de un verbo de trabajo con código:
# «explícame qué hora es» no es programación; «explícame este código» sí.
CODER_DEBILES = (
    "código codigo programa programación programacion script función funcion "
    "bucle bucles variable variables array arreglo matriz api endpoint error "
    "errores bug bugs depurar debugging compilar compilación compilacion "
    "algoritmo algoritmos repositorio rama commit merge dockerfile terminal "
    "consola framework librería libreria biblioteca interfaz backend frontend "
    "servidor asíncrono async await promesa markdown csv xml"
).split()

CODER_VERBOS = (
    "escribe escriba crea creame haz hazme hace hacer arregla corrige revisa "
    "explica explicame explícame genera refactoriza optimiza instala compila "
    "prueba depura parchea modifica cambia implementa añade agregar pegar "
    "ejecutar arrancar montar"
).split()


def es_programacion(m: str) -> bool:
    """True si la frase pide código. Diseñada para NO robarles la respuesta a los
    comandos locales: hace falta un nombre de lenguaje/herramienta suelto, o bien un
    sustantivo técnico MÁS un verbo de trabajo (así «hazme una app» entra, y
    «¿qué tiempo hace?» se queda con el clima)."""
    tx = " " + re.sub(r"[^\wáéíóúñüÁÉÍÓÚÑÜ+#.]+", " ", m.lower()) + " "
    if any(f" {t} " in tx for t in CODER_FUERTES):
        return True
    debil = next((t for t in CODER_DEBILES if f" {t} " in tx), None)
    if not debil:
        return False
    return any(f" {v} " in tx for v in CODER_VERBOS)


def _perfil_clave(clave: str) -> str:
    """Una preferencia libre del perfil (ventana PERFIL / POST /api/profile)."""
    try:
        try:
            import memory
        except ImportError:
            from . import memory
        return (memory.get_profile() or {}).get(clave, "") or ""
    except Exception:
        return ""


# Palabras que pueden colarse detrás de «en»/«de» sin ser un topónimo. Si lo que
# captura la regex está aquí, NO se busca en el mapa: se pregunta el clima por IP
# como siempre. Sin esta lista, «el tiempo de la semana» daría `sin-lugar` y CORT
# se quedaría diciendo que «semana» no existe en el mapa.
NO_LUGAR = {
    "la", "el", "los", "las", "un", "una", "unos", "unas", "de", "del", "en", "y",
    "ciudad", "pueblo", "region", "región", "localidad", "sitio", "lugar", "parte",
    "zona", "aqui", "aquí", "allá", "alla", "afuera", "fuera", "casa", "trabajo",
    "oficina", "escuela", "clase", "semana", "mes", "ano", "año", "hoy", "manana",
    "mañana", "tarde", "noche", "mediodia", "mediodía", "verdad", "rato", "ratito",
    "momento", "día", "dia", "fin", "puente", "viaje", "clima", "tiempo",
    "temperatura", "lluvia", "sol", "nube", "ventana", "mundo", "pais", "país",
    "mismo", "misma", "mismos", "mismas", "ahorita", "ratote",
}

# Los topónimos que empiezan por estas palabras llevan el segundo término pegado:
# «Nueva York», «Las Palmas», «San Sebastián», «La Paz». Con uno solo de sus
# trozos el geocoder falla, así que aquí NO se corta al primer vocablo.
COMPUESTOS = {"san", "santa", "santo", "nueva", "nuevo", "puerto", "punta", "rio",
              "río", "las", "los", "la", "el", "ciudad", "villa", "piedras", "cabo"}


def sitio_nombrado(m: str) -> str:
    """El topónimo NOMBRADO en la frase: «qué tiempo hace EN Sevilla» → `Sevilla`.

    NO mira el Perfil: quien llama quiere saber si la dueña pidió una ciudad
    concreta o si hay que usar la suya. Quita primero los huecos de tiempo
    («mañana», «hoy», «ahora»), porque «en Madrid mañana» tiene que dar `Madrid`,
    no «Madrid mañana» — con esa cola el geocoder no encuentra nada y la respuesta
    sería un `sin-lugar` con la culpa a medio explicar.
    """
    t = re.sub(r"\b(?:ahora|hoy|ma[ñn]ana|paso|pasado|antier|mediod[íi]a|noche|tarde|"
               r"viernes|s[áa]bado|domingo|lunes|martes|mi[ée]rcoles|jueves|"
               r"esta\s+semana|el\s+fin\s+de\s+semana)\b", " ", m.lower())
    for g in re.finditer(r"\b(?:en|de|para|hacia|desde)\s+((?:\w+\s+){0,2}\w+)", t):
        crudo = g.group(1).lower().split()
        if crudo[0] in COMPUESTOS and len(crudo) > 1 and crudo[1] not in NO_LUGAR:
            sitio = " ".join(crudo[:2])          # «nueva york», «las palmas», «la paz»
        else:
            resto = [w for w in crudo if w not in NO_LUGAR]
            sitio = resto[0] if resto else ""    # «gijón ahora mismo» → gijón
        if len(sitio) >= 3:
            return sitio.title()
    return ""


def system_prompt(modo: str = "asistente") -> str:
    """SYSTEM_PROMPT (o CODER_PROMPT) + preferencias del perfil.

    Las preferencias se añaden en los dos registros: «tu nombre es X» y «el usuario
    se llama Y» siguen siendo verdad cuando se habla de código."""
    base = CODER_PROMPT if modo == "coder" else SYSTEM_PROMPT
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
    if p.get("ciudad"):
        extra.append(f"Su ciudad es {p['ciudad']}; úsala para el clima salvo que "
                     "pida otra.")
    return base + (" " + " ".join(extra) if extra else "")

# ---------------------------------------------------------------- utilidades
def _ollama_available(c: dict | None = None) -> bool:
    c = c or cfg()
    try:
        return requests.get(f"{c['ollama_url']}/api/tags", timeout=1.5).status_code == 200
    except Exception:
        return False


def _ollama_chat(message: str, history: list[dict], modo: str = "asistente") -> str:
    c = cfg()
    msgs = [{"role": "system", "content": system_prompt(modo)}] + history[-8:] + [
        {"role": "user", "content": message}]
    r = requests.post(
        f"{c['ollama_url']}/api/chat",
        json={"model": c["ollama_model"], "messages": msgs, "stream": False},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def _groq_chat(message: str, history: list[dict], modo: str = "asistente") -> str:
    c = cfg()
    msgs = [{"role": "system", "content": system_prompt(modo)}] + history[-12:] + [
        {"role": "user", "content": message}]
    # Un bloque de código caben mal en 700 tokens: el registro de programación pide
    # más salida, y sólo ése, para no inflar la cuota en las frases de siempre.
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {c['groq_key']}"},
        json={"model": "llama-3.3-70b-versatile", "messages": msgs,
              "max_tokens": 1400 if modo == "coder" else 700, "temperature": 0.6},
        timeout=40,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _gemini_chat(message: str, history: list[dict], modo: str = "asistente") -> str:
    c = cfg()
    contents = [{"role": "user" if h["role"] == "user" else "model",
                 "parts": [{"text": h["content"]}]} for h in history[-12:]]
    contents.append({"role": "user", "parts": [{"text": message}]})
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{c['gemini_model']}:generateContent?key={c['gemini_key']}",
        json={"system_instruction": {"parts": [{"text": system_prompt(modo)}]},
              "contents": contents},
        timeout=40,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def _offline_reply(message: str) -> str:
    m = message.lower()
    if es_programacion(message):
        return ("Esa pregunta necesita un cerebro de código y ahora mismo no hay "
                "ninguno: ni Ollama en local ni clave en PERFIL. Los comandos de "
                "siempre (hora, batería, clima, archivos) sí funcionan sin red. "
                "Pega una GROQ_API_KEY en la ventana PERFIL y con eso respondo "
                "código, en español y con el bloque listo para copiar.")
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
    # Clima: por palabra obvia, o por «tiempo» acompañado de un SITIO NOMBRADO. Lo
    # segundo está separado a propósito: «tengo poco tiempo» no debe contestar con
    # el termómetro ni siquiera teniendo `ciudad` guardada en el Perfil.
    obvio = bool(re.search(r"\bclima\b|temperatura|qu[ée]\s+tiempo|el\s+tiempo|"
                           r"lluvia|llover|llueve|pron[óo]stico|\bgrados\b|"
                           r"nublado|despejado|hace\s+(?:fr[íi]o|calor|sol|viento)", m))
    pedido = sitio_nombrado(m)
    if obvio or ("tiempo" in m and bool(pedido)):
        import sensors
        sitio = pedido or _perfil_clave("ciudad")
        w = sensors.weather(lugar=sitio) if sitio else sensors.weather()
        if w.get("ok"):
            return sensors.frase(w)
        if w.get("error") == "sin-lugar":
            # Se repite ENTRE COMILLAS el nombre que se buscó: si CORT dice «no encuentro
            # el sitio» sin decir cuál, la dueña no puede saber si escribió mal la ciudad
            # o si el geocoder no la tiene.
            return (f"No encontré «{w.get('busca', '')}» en el mapa. Di el nombre de otra "
                    "manera («el tiempo en Gijón») o pon tu ciudad en la ventana PERFIL.")
        return f"No pude obtener el clima: {w.get('error', 'sin motivo')}."
    if re.search(r"\b(archivos|carpetas|explorador)\b", m) and len(m) < 30:
        return ("Abriendo el panel de archivos en tu holograma. "
                "También puedes decirme: muestra documentos.")
    if re.search(r"\b(hola|buenas|buenos días|buenas tardes)\b", m) and len(m) < 24:
        return local_commands.greeting()
    return None


# ------------------------------------------------------------- entrada
def think(message: str, history: list[dict]) -> tuple[str, str]:
    """Devuelve (respuesta, fuente) donde fuente ∈
    local | ollama | groq | gemini | offline.

    `modo` (`asistente` | `coder`) se decide AQUÍ y se baja a los tres cerebros:
    es la misma IA con otra consigna. Y cuando toca el registro de programación se
    salta `local_command`, porque «hazme una app del clima en Python» lleva la
    palabra «clima» y el comando local contestaría con el tiempo de verdad."""
    c = cfg()
    mode = c["mode"]
    coder = es_programacion(message)
    modo = "coder" if coder else "asistente"
    if mode != "online" and not coder:      # incluso en 'auto' y 'local'
        cmd = local_command(message)
        if cmd:
            return cmd, "local"

    if mode in ("auto", "local") and _ollama_available(c):
        try:
            return _ollama_chat(message, history, modo), "ollama"
        except Exception:
            if mode == "local":
                return _offline_reply(message), "offline"

    if mode in ("auto", "online"):
        if c["groq_key"]:
            try:
                return _groq_chat(message, history, modo), "groq"
            except Exception:
                pass
        if c["gemini_key"]:
            try:
                return _gemini_chat(message, history, modo), "gemini"
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

