"""Comandos locales rápidos. Devuelven una acción estructurada o None (-> va al LLM).
Las acciones reales sobre el sistema se implementan en services/audio y services/sensors."""
import re

_PATTERNS = [
    (r"\b(sube|aumenta)\b.*\bvolumen\b", {"action": "volume", "delta": +10}),
    (r"\b(baja|reduce)\b.*\bvolumen\b", {"action": "volume", "delta": -10}),
    (r"\b(captura|capturar|pantallazo|screenshot)\b", {"action": "screenshot"}),
    # `match_intent` devuelve el primer patrón que casa, así que el orden es
    # una decisión: "haz una captura y abre archivos" se resuelve como captura.
    (r"\b(abre|abrir|abrid)\b.*\b(archivos|explorador|gestor de archivos)\b", {"action": "launch", "app": "archivos"}),
    (r"\b(abre|abrir|abrid)\b.*\bterminal\b", {"action": "launch", "app": "terminal"}),
    (r"\b(pausa|pausar)\b", {"action": "media", "cmd": "pause"}),
    (r"\b(reproduce|continúa|continua|play)\b", {"action": "media", "cmd": "play"}),
    (r"\bsiguiente\b", {"action": "media", "cmd": "next"}),
    (r"\becualizador\b", {"action": "equalizer", "cmd": "toggle"}),
]

#: Cuántos pasos se sacan como mucho de un mensaje. Cuatro es el techo de lo que
#: una persona enlista de verdad en una frase, y cada paso es un mando con su
#: comprobación: sin tope, un pegar-copy de cien órdenes metería cien esperas de
#: `SETTLE_S` en el bucle que atiende a la usuaria.
PASOS_MAX = 4

#: Lo que separa una orden de otra. La `y` suelta es la más frecuente y la más
#: engañosa, así que va rodeada de espacios: con `y` dentro de una palabra no se
#: parte. `despu[ée]s` cubre la tilde y la falta de ella porque la gente escribe
#: de las dos formas. No hay analizador sintáctico detrás —éste es un planificador
#: de lista cerrada, no un modelo—, sólo estas pocas formas y la puntuación.
_SEPARA = re.compile(
    r"\s*[;,]\s*|\s+(?:y|luego|despu[ée]s|entonces|adem[áa]s)\s+",
    re.I,
)


def match_intent(text: str):
    t = text.lower()
    for pattern, action in _PATTERNS:
        if re.search(pattern, t):
            return dict(action)
    return None


def match_all(text):
    """Todos los pasos ejecutables de un mensaje, en el orden en que se pidieron.

    Es el escalón que faltaba entre «sube el volumen» (una orden, un mando) y
    «sube el volumen y abre la terminal», que hasta hoy se resolvía como la
    primera y la segunda se perdía sin decirlo. Cada trozo pasa por los *mismos*
    patrones de `match_intent`: por eso una frase que pida `rm -rf /` no produce
    un paso —no está en la tabla, y aquí no se añade nada que no esté en ella—.

    Dos decisiones que son una promesa:
    * **el orden es el de la frase**, no el de la tabla. `match_intent` sigue
      dando la primera que casa (ninguna frase de un solo paso cambia de
      comportamiento), pero cuando hay dos órdenes la usuaria las dijo en un
      orden y CORT las hace en ese.
    * **se hereda el verbo** del tramo anterior cuando el siguiente sólo nombra
      el destino: «abre la terminal y el gestor de archivos». El heredado vuelve
      a pasar por la tabla, así que «y el editor de video» no se cuela.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    pasos: list[dict] = []
    verbo = ""
    for trozo in _SEPARA.split(text):
        t = trozo.strip()
        if not t:
            continue
        intent = match_intent(t)
        if intent is not None:
            # El verbo de la frase que casa es el que se presta al siguiente
            # tramo. Se guarda en minúscula porque `match_intent` ya baja todo.
            verbo = t.split()[0].lower()
        elif verbo:
            intent = match_intent(f"{verbo} {t}")
        if intent is None or intent in pasos:
            continue
        pasos.append(intent)
        if len(pasos) >= PASOS_MAX:
            break
    return pasos
