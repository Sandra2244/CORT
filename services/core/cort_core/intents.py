"""Comandos locales rápidos. Devuelven una acción estructurada o None (-> va al LLM).
Las acciones reales sobre el sistema se implementan en services/audio y services/sensors."""
import re

_PATTERNS = [
    (r"\b(sube|aumenta)\b.*\bvolumen\b", {"action": "volume", "delta": +10}),
    (r"\b(baja|reduce)\b.*\bvolumen\b", {"action": "volume", "delta": -10}),
    (r"\b(pausa|pausar)\b", {"action": "media", "cmd": "pause"}),
    (r"\b(reproduce|continúa|continua|play)\b", {"action": "media", "cmd": "play"}),
    (r"\bsiguiente\b", {"action": "media", "cmd": "next"}),
    (r"\becualizador\b", {"action": "equalizer", "cmd": "toggle"}),
]

def match_intent(text: str):
    t = text.lower()
    for pattern, action in _PATTERNS:
        if re.search(pattern, t):
            return dict(action)
    return None
