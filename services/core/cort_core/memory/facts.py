"""Convierte frases del usuario en hechos almacenables."""
import re
import unicodedata

#: Nombres de dispositivo admitidos. La lista es cerrada a propósito: «uso un
#: martillo» no debe guardarse como si fuera un teléfono.
_DISP = r"tel[ée]fono|celular|m[óo]vil|tableta|tablet|laptop|port[áa]til|computadora|pc|equipo"

#: Marcas conocidas. Se exige la marca porque «uso un ...» aparece también en
#: órdenes («uso el cronómetro a diario»): sin ancla, cualquier frase con «uso»
#: llenaría la memoria de basura. El modelo se acepta sólo si lleva dígitos
#: («A16», «S23»), que es como se escriben de verdad.
_MARCA = (r"Samsung|Xiaomi|Huawei|Motorola|OPPO|Canaima|Lenovo|HP|Dell|Asus|"
          r"Acer|Apple|iPhone|iPad|Galaxy|Redmi|Nokia|Alcatel|ZTE")

#: Las dos formas canónicas que el portátil reconoce como «dato de la persona»,
#: escritas **una sola vez**. No son un detalle de estilo: `store.py` busca el
#: nombre con `LIKE 'El usuario se llama%'` para el saludo, para
#: `name_of_user()` y para no podarlo nunca, y `context_for()` ordena por él. Si
#: la plantilla se copiara en un segundo sitio, cambiar una de las dos dejaría al
#: portátil saludando sin nombre mientras tiene el recuerdo guardado.
NOMBRE = "El usuario se llama {}"
DISPOSITIVO = "El usuario dice que su {} es {}"

_PATTERNS = [
    (r"\b(?:me llamo|mi nombre es)\s+([\w]+)", NOMBRE),
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
     DISPOSITIVO),
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


#: Claves del teléfono (`hechos` de `cort.db`) que en el portátil son **el nombre**
#: de la persona. Es la lista cerrada de `Recuerdos.quienSoy()` más sus variantes.
_NOMBRE = {"nombre", "me llamo", "soy", "como me llamo"}
#: …y las que son un aparato suyo.
_APARATO = {"telefono", "movil", "celular", "tableta", "tablet", "portatil",
            "laptop", "computadora", "pc", "equipo", "smartphone", "ordenador"}

#: `clave: valor` tal y como lo escribe `Recuerdos.lista()` al exportar. El espacio
#: **después** de los dos puntos es obligatorio a propósito: sin él, una memoria con
#: una hora («salí a las 8: 30») o una URL («bajalo de http://…») se partía en dos
#: y el portátil guardaba la mitad equivocada como si fuera una clave.
_PAREJA = re.compile(r"^\s*([^:\n]{1,40}?):\s+(.+)$", re.S)


def _sueltas(texto: object) -> str:
    """Forma de **clasificar** una clave: sin tildes, sin mayúsculas, sin espacios de sobra.

    Diferencia deliberada respecto a `puente.normaliza`, que conserva los acentos:
    allí se comparan recuerdos enteros y «canción» no es «cancion»; aquí se decide
    sólo en qué casilla del portátil cae una clave del teléfono, y la dueña escribe
    `teléfono`, `Teléfono` o `telefono` según de dónde lo haya dictado. El habla
    dentro del APK ya se normaliza sin marcas (`Cerebro.normaliza`), así que las dos
    mitades de esta función coinciden.
    """
    crudo = unicodedata.normalize("NFD", str(texto or ""))
    sin_marcas = "".join(c for c in crudo if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_marcas).strip().casefold()


def desde_el_telefono(texto: str) -> list[str]:
    """Un hecho que llega de `cort.db`, reescrito en la forma canónica del portátil.

    El teléfono guarda `clave: valor` («nombre: Sandra») y el portátil guarda frases
    canónicas («El usuario se llama Sandra»). Sin esta traducción el puente
    funcionaría igual y la dueña seguiría teniendo que decir quién es: la fila
    viajaría, pero `name_of_user()` —que busca `LIKE 'El usuario se llama%'`— no la
    reconocería, el saludo seguiría sin nombre y `prune()` podría podarla por ser la
    más antigua. Este detalle es el motivo de existir del puente, no un adorno.

    Tres reglas, en orden:

    1. Si la frase **ya** casa con un patrón de `extract` (el teléfono guardó «me
       llamo Sandra» como texto suelto), esa es la forma canónica.
    2. Si tiene forma `clave: valor` y la clave es de nombre o de aparato, se
       reconstruye con las plantillas `NOMBRE` / `DISPOSITIVO`. Cualquier otra clave
       viaja tal cual: un dato que el portátil no sabe canónico sigue siendo un dato
       útil, y «no lo entiendo» no significa «tíralo».
    3. Si nada casa, se devuelve la frase original sin cortar.

    Con texto vacío devuelve `[]` (no hay nada que guardar); con texto **no** vacío
    nunca devuelve lista vacía, que sería el modo silencioso de perder un recuerdo al
    sincronizar.
    """
    limpio = (texto or "").strip()
    if not limpio:
        return []
    hechos = extract(limpio)
    pareja = _PAREJA.match(limpio)
    if pareja:
        clave = _sueltas(pareja.group(1))
        valor = pareja.group(2).strip()
        if valor:
            if clave in _NOMBRE:
                hecho = NOMBRE.format(valor)
            elif clave in _APARATO:
                # La palabra del aparato sale del texto original en minúsculas, no de
                # la forma clasificada: «El usuario dice que su teléfono es …» con
                # tilde, que es como `extract` lo escribe desde el portátil.
                hecho = DISPOSITIVO.format(pareja.group(1).strip().lower(), valor)
            else:
                hecho = limpio
            if hecho not in hechos:
                hechos.append(hecho)
    return hechos or [limpio]

