"""Convierte frases del usuario en hechos almacenables."""
import re

#: Nombres de dispositivo admitidos. La lista es cerrada a propósito: «uso un
#: martillo» no debe guardarse como si fuera un teléfono.
_DISP = r"tel[ée]fono|celular|m[óo]vil|tableta|tablet|laptop|port[áa]til|computadora|pc|equipo"

#: Marcas conocidas. Se exige la marca porque «uso un ...» aparece también en
#: órdenes («uso el cronómetro a diario»): sin ancla, cualquier frase con «uso»
#: llenaría la memoria de basura. El modelo se acepta sólo si lleva dígitos
#: («A16», «S23»), que es como se escriben de verdad.
_MARCA = (r"Samsung|Xiaomi|Huawei|Motorola|OPPO|Canaima|Lenovo|HP|Dell|Asus|"
          r"Acer|Apple|iPhone|iPad|Galaxy|Redmi|Nokia|Alcatel|ZTE")

_PATTERNS = [
    (r"\b(?:me llamo|mi nombre es)\s+([\w]+)", "El usuario se llama {}"),
    (r"\bestudio\s+(.+?)(?=[.,!?]|$)", "El usuario estudia {}"),
    (r"\bme gusta\s+(.+?)(?=[.,!?]|$)", "Al usuario le gusta {}"),
    # El dispositivo se guarda una vez y no se pregunta más: la dueña de CORT
    # cambia entre el portátil y el teléfono, y cada dato que hay que repetirle
    # al modelo es un turno entero perdido. Una fila más en SQLite cuesta un
    # INSERT; repetirlo en cada charla cuesta la charla.
    # El artículo NO se salta en el patrón: se captura con el resto, porque un
    # hecho que diga «es Redmi Note 12» suena a etiqueta, y «es un Redmi Note 12»
    # es la frase que CORT puede reutilizar tal cual en un prompt.
    (rf"\bmi\s+({_DISP})\s+(?:es|era)\s+(.+?)(?=[.,!?]|$)",
     "El usuario dice que su {} es {}"),
    # `(?:…)` alrededor de la marca: sin él, el sufijo de modelo colgara sólo de
    # la ULTIMA alternativa ("ZTE16"), y «Samsung A16» salia como «Samsung».
    (rf"\buso\s+(un|una)\s+((?:{_MARCA})(?:\s+[A-Za-z]*\d[A-Za-z0-9]*)?)(?=[.,!?]|$|\s)",
     "El usuario usa {} {}"),
]


def extract(text: str) -> list[str]:
    facts = []
    for pattern, template in _PATTERNS:
        # re.I para reconocer "ME LLAMO", pero el capture sale del texto original
        # y asi el nombre conserva sus mayusculas.
        match = re.search(pattern, text, re.I)
        if match:
            # `format` con todos los grupos: los patrones de un solo grupo siguen
            # igual, y el de «mi teléfono es …» llena sus dos huecos.
            facts.append(template.format(*(g.strip() for g in match.groups())))
    return facts
