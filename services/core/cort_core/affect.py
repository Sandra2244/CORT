"""De lo que pasó en el core a la palabra que la cara sabe pintar.

Función 29 del inventario (`docs/FUNCTIONS.md`): «expresiones según estado
afectivo». El `mood` ya viajaba en cada `assistant_message`, `greeting`, `state`
y `proactive` — pero siempre con el literal `"calm"`, o sea viajaba vacío. Este
módulo es lo único que lo llena, y lo llena con dos cosas honestas:

- **Señales medidas.** `actions.perform` dice si el volumen *subió* de verdad,
  `timer` dice que la cuenta terminó, `memory` dice que se guardó un hecho, el
  lazo de iniciativa dice que CORT habló tras 90 s de silencio. Eso es evidencia.
- **Un léxico determinista sobre el texto**, sólo cuando no hay evidencia. No es
  análisis de sentimiento: no hay modelo, no hay red, no hay promesa. Es una
  lista cerrada de formas de decir «no puedo» y de decir «listo», para que una
  respuesta del LLM que rehusó algo no salga con una sonrisa.

Y un tope que es el que de verdad protege a la interfaz: **la salida es siempre
una de `MOODS`**. El cuerpo 3D tiene cinco expresiones mapeadas
(`apps/web/src/cort/afecto.ts`); un estado inventado al otro lado del cable no se
puede pintar, así que aquí se convierte en reposo antes de salir por el puerto.

Regla 6 de `AGENTS.md` sigue mandando: este módulo no ejecuta nada ni decide
cuándo hablar. Se prueba en `services/core/tests/test_affect.py`.
"""
import re
import unicodedata

# El vocabulario que la cara entiende. Añadir uno aquí obliga a añadir su peso
# en `cort/afecto.ts`; por eso es una tupla y no un `str` suelto.
MOODS = ("calm", "happy", "sad", "surprised", "relaxed")

# Lo que el servidor sabe que pasó. Cada nombre lo escribe un sitio concreto de
# `server.py`, y ninguno es una opinión sobre el texto.
SENALES = (
    "saludo",          # `greeting`: CORT se presenta
    "logro",           # `actions.perform` midió el cambio
    "fallo",           # `perform` no lo midió: «No pude: …»
    "plan_completo",   # `planner`: todos los pasos salieron
    "plan_con_fallo",  # `planner`: al menos un paso no
    "memoria",         # `memory.remember` guardó un hecho nuevo
    "fin_cuenta",      # `timer`: se acabó el tiempo
    "cancelado",       # `timer`: la usuaria mandó parar
    "iniciativa",      # `proactive`: habló sola tras el silencio pactado
    "eco",             # sin Ollama: repite, no opina
)

# Señal medida → estado. Es un `dict` y no una cadena de `if` porque la tabla *es*
# el contrato: leerla de una pasada dice qué puede afirmar CORT y qué no.
_POR_SENAL = {
    "saludo": "happy",
    "logro": "happy",
    "plan_completo": "happy",
    "memoria": "happy",
    "fallo": "sad",
    "plan_con_fallo": "sad",
    "fin_cuenta": "surprised",
    "cancelado": "calm",
    "iniciativa": "relaxed",
    # El eco queda en reposo a propósito: sin modelo no hay nada que celebrar.
    "eco": "calm",
}

# El léxico va sobre el texto **normalizado** (minúsculas y sin tildes), así que
# las formas aquí van sin tilde y cubren a la vez «falló» y «fallo», «está» y
# «esta». Primera persona: lo que CORT confiesa de sí mismo, no lo que la
# usuaria pregunta — «¿no puedes…?» no es una tristeza de CORT.
_TRISTE = re.compile(
    r"no puedo|no pude|no pu[eé]do|no s[ée]|no puedo hacerlo|no funciona|no hay forma"
    r"|error|fallo|fall[aó]|sin permiso|no me deja|no est[aá] disponible"
)
_ALEGRE = re.compile(
    r"listo|gracias|perfecto|genial|estupend[oa]|encantad[oa]|ya esta|ya est[aá]"
    r"|hecho|funcionando|todo bien|ahi va|a tu servicio"
)
# Niega la celebración: «no está hecho», «todavía no listo». Se mira la palabra
# que precede, no una sintaxis — con dos mil caracteres de frase, un análisis de
# dependencias sería otra máquina más en un portátil de dos núcleos.
_NEGADO = re.compile(r"\b(no|todav[ií]a|nunca|tampoco)\s+[^\s]{0,12}$")


def normaliza(texto: str) -> str:
    """Minúsculas y sin marcas: el único sitio donde se comparan las palabras."""
    suelto = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in suelto if unicodedata.category(c) != "Mn")


def _celebra(texto_norm: str) -> bool:
    for m in _ALEGRE.finditer(texto_norm):
        # Si justo antes de la palabra alegre hay un «no», la frase dice lo
        # contrario de lo que la palabra suelta.
        if _NEGADO.search(texto_norm[: m.start()]):
            continue
        return True
    return False


def mood_for(texto: str, senal: str | None = None) -> str:
    """El estado que se puede afirmar de este mensaje, siempre de `MOODS`.

    Prioridad: la señal medida, luego el léxico del texto, luego reposo. Nunca
    lanza: si el core manda un nombre que no está en `SENALES` se cae al léxico,
    y si el léxico no dice nada, a `calm`.
    """
    if senal in _POR_SENAL:
        return _POR_SENAL[senal]
    norm = normaliza(texto)
    if not norm.strip():
        return "calm"
    # El fallo se comprueba primero: una frase que dice «no pude, pero gracias»
    # es una disculpa, no una fiesta.
    if _TRISTE.search(norm):
        return "sad"
    if _celebra(norm):
        return "happy"
    return "calm"


def marco(tipo: str, texto: str, senal: str | None = None, **extra) -> dict:
    """El cuadro listo para mandar por el WebSocket, con su `mood`.

    Vive aquí y no en `server.py` porque el bucle del lazo tiene once sitios que
    dicen algo, y en once sitios es donde se olvida uno. El texto se manda
    **exactamente** como vino: este módulo pone la cara, no las palabras.
    """
    cuadro = {"type": tipo, "text": texto, "mood": mood_for(texto, senal)}
    cuadro.update(extra)
    return cuadro
