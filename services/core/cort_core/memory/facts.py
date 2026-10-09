"""Convierte frases del usuario en hechos almacenables."""
import re

_PATTERNS = [
    (r"\b(?:me llamo|mi nombre es)\s+([\w]+)", "El usuario se llama {}"),
    (r"\bestudio\s+(.+?)(?=[.,!?]|$)", "El usuario estudia {}"),
    (r"\bme gusta\s+(.+?)(?=[.,!?]|$)", "Al usuario le gusta {}"),
]


def extract(text: str) -> list[str]:
    facts = []
    for pattern, template in _PATTERNS:
        # re.I para reconocer "ME LLAMO", pero el capture sale del texto original
        # y asi el nombre conserva sus mayusculas.
        match = re.search(pattern, text, re.I)
        if match:
            facts.append(template.format(match.group(1).strip()))
    return facts
