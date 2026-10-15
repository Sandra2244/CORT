"""Entender «mañana a las 7», «en 20 minutos», «el lunes a las 9 de la noche».

Lógica pura: recibe texto y un `ahora`, devuelve un `datetime`. No lee el reloj
(quien llama lo pasa), no toca el disco, no ejecuta nada: por eso se prueba con
una tabla de frases y una fecha fija, sin esperar a que pase el tiempo.

Es una lista cerrada de formas, no un analizador del idioma. Lo que no reconoce
devuelve `None` y quien llama lo dice («no entendí a qué hora»); adivinar una
hora es peor que preguntar, porque una alarma a la hora equivocada falla en
silencio justo cuando importa.

Una decisión que es una promesa: **sin «de la mañana/tarde/noche» ni am/pm, la
hora se resuelve a la próxima vez que ocurra** («a las 7» a las 9 de la noche es
mañana a las 7:00), y quien confirma la dice completa en 12 horas con a. m. o
p. m. para que la usuaria corrija si se entendió otra cosa.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta

_NUM_PALABRA = {
    "un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
}
_HORA_PAL = "|".join(sorted((k for k in _NUM_PALABRA if k != "un"), key=len, reverse=True))

DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre")


def sin_tildes(s: str) -> str:
    """«miércoles» → «miercoles»: la gente escribe con y sin tilde, y el
    reconocimiento de voz casi nunca la pone."""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


# -- relativo: «en 20 minutos», «en una hora y media», «en media hora» -------------
_REL_PIEZA = r"(?:\d+(?:[.,]\d+)?|una?|media)\s*(?:segundos?|minutos?|horas?)(?:\s+y\s+media)?"
_REL = re.compile(rf"\ben\s+(?P<cuerpo>{_REL_PIEZA}(?:\s*(?:y|con|,)?\s*{_REL_PIEZA})*)", re.I)
_REL_ITEM = re.compile(r"(\d+(?:[.,]\d+)?|una?|media)\s*(segundos?|minutos?|horas?)(\s+y\s+media)?", re.I)
_SEG = {"segundo": 1, "minuto": 60, "hora": 3600}


def _cantidad(txt: str) -> float:
    t = txt.lower()
    if t == "media":
        return 0.5
    if t in ("un", "una"):
        return 1.0
    return float(t.replace(",", "."))


def _segundos_relativos(cuerpo: str) -> int:
    total = 0.0
    for cant, unidad, y_media in _REL_ITEM.findall(cuerpo):
        base = _SEG[unidad.lower().rstrip("s")]
        total += _cantidad(cant) * base + (base / 2 if y_media else 0)
    return int(round(total))


# -- hora del día: «a las 7:30», «a las siete y media de la tarde», «a las 19» ------
_HORA = re.compile(
    rf"\b(?:a\s+las?|a\s+la)\s+(?P<h>\d{{1,2}}|{_HORA_PAL}|una)"
    r"(?:\s*[:.h]\s*(?P<m>\d{2}))?"
    r"(?:\s*(?P<mer>a\.?\s?m\.?|p\.?\s?m\.?))?"
    r"(?:\s+y\s+(?P<mas>media|cuarto)|\s+menos\s+(?P<menos>cuarto|\d{1,2}))?"
    r"(?:\s+(?:de|por)\s+la\s+(?P<parte>ma[ñn]ana|tarde|noche|madrugada))?",
    re.I,
)
_MEDIODIA = re.compile(r"\b(?:(?:al|a)\s+)?(?P<x>medio\s?d[ií]a|medianoche)\b", re.I)

# -- día: «hoy», «mañana», «pasado mañana», «el lunes», «el 15 de noviembre» ---------
_PASADO = re.compile(r"\bpasado\s+ma[ñn]ana\b", re.I)
# «mañana» sólo es el día si no es «de la mañana»: esa ya la consumió la hora.
_MANANA = re.compile(r"(?<!la )\bma[ñn]ana\b", re.I)
_HOY = re.compile(r"\bhoy\b", re.I)
_SEMANA = re.compile(r"\b(?:el\s+)?(?:pr[óo]ximo\s+)?(lunes|martes|mi[ée]rcoles|jueves|viernes|s[áa]bado|domingo)\b", re.I)
_FECHA_MES = re.compile(r"\b(?:el\s+)?(\d{1,2})\s+de\s+(" + "|".join(MESES) + r")\b(?:\s+de\s+(\d{4}))?", re.I)
_FECHA_NUM = re.compile(r"\b(?:el\s+)?(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b")


def _hora_del_dia(m: re.Match) -> tuple[int, int, bool] | None:
    """(hora 0-23, minuto, ¿era ambigua entre mañana y tarde?)."""
    raw = m.group("h").lower()
    h = int(raw) if raw.isdigit() else _NUM_PALABRA[raw]
    mi = int(m.group("m")) if m.group("m") else 0
    if m.group("mas") == "media":
        mi = 30
    elif m.group("mas") == "cuarto":
        mi = 15
    elif m.group("menos"):
        resta = 15 if m.group("menos") == "cuarto" else int(m.group("menos"))
        mi = 60 - resta
        h = (h - 1) % 24 if h else 23
    if h > 24 or mi > 59:
        return None
    mer = (m.group("mer") or "").lower().replace(".", "").replace(" ", "")
    parte = sin_tildes((m.group("parte") or "").lower())
    if h > 12:                      # «a las 19»: ya es de 24 horas, no hay duda
        return h % 24, mi, False
    if mer == "pm" or parte in ("tarde", "noche"):
        if parte == "noche" and h in (11, 12):
            return (23 if h == 11 else 0), mi, False   # 11 de la noche; 12 de la noche = 0
        return (h % 12) + 12, mi, False
    if mer == "am" or parte in ("manana", "madrugada"):
        return (0 if h == 12 else h), mi, False
    if h == 12:                     # «a las 12» sin más: el mediodía, no la medianoche
        return 12, mi, False
    return h, mi, h <= 12           # sin pista: se resuelve a la próxima vez


def _dia_explicito(texto: str, ahora: datetime) -> tuple[datetime | None, str]:
    """La fecha que el texto nombra (a las 00:00) y el texto sin esa expresión."""
    if (m := _PASADO.search(texto)):
        return _a_medianoche(ahora + timedelta(days=2)), texto[: m.start()] + texto[m.end():]
    if (m := _MANANA.search(texto)):
        return _a_medianoche(ahora + timedelta(days=1)), texto[: m.start()] + texto[m.end():]
    if (m := _HOY.search(texto)):
        return _a_medianoche(ahora), texto[: m.start()] + texto[m.end():]
    if (m := _FECHA_MES.search(texto)):
        dia, mes, anio = int(m.group(1)), MESES.index(m.group(2).lower()) + 1, m.group(3)
        d = _fecha(ahora, dia, mes, int(anio) if anio else None)
        if d:
            return d, texto[: m.start()] + texto[m.end():]
    if (m := _FECHA_NUM.search(texto)):
        dia, mes, anio = int(m.group(1)), int(m.group(2)), m.group(3)
        if anio and len(anio) == 2:
            anio = "20" + anio
        d = _fecha(ahora, dia, mes, int(anio) if anio else None)
        if d:
            return d, texto[: m.start()] + texto[m.end():]
    if (m := _SEMANA.search(texto)):
        objetivo = DIAS.index(_normaliza_dia(m.group(1)))
        falta = (objetivo - ahora.weekday()) % 7
        # «el lunes» dicho un lunes es el que viene, no hoy: si fuera hoy, diría «hoy».
        return _a_medianoche(ahora + timedelta(days=falta or 7)), texto[: m.start()] + texto[m.end():]
    return None, texto


def _normaliza_dia(txt: str) -> str:
    t = sin_tildes(txt.lower())
    for d in DIAS:
        if sin_tildes(d) == t:
            return d
    return t


def _a_medianoche(d: datetime) -> datetime:
    return d.replace(hour=0, minute=0, second=0, microsecond=0)


def _fecha(ahora: datetime, dia: int, mes: int, anio: int | None) -> datetime | None:
    try:
        if anio is not None:
            return datetime(anio, mes, dia, tzinfo=ahora.tzinfo)
        d = datetime(ahora.year, mes, dia, tzinfo=ahora.tzinfo)
        # «el 3 de marzo» dicho en octubre es el del año que viene.
        return d if d >= _a_medianoche(ahora) else datetime(ahora.year + 1, mes, dia, tzinfo=ahora.tzinfo)
    except ValueError:
        return None


def extraer_cuando(texto: str, ahora: datetime, *, hora_por_defecto: tuple[int, int] | None = None
                   ) -> tuple[datetime | None, str]:
    """(cuándo, texto sin la expresión de tiempo), o `(None, texto)` si no hay.

    `hora_por_defecto`: para un evento «mañana» sin hora, qué hora ponerle; sin
    ella, un día sin hora es `None` (una alarma no puede adivinarla).
    """
    # 1) «en 20 minutos»: no necesita más.
    if (m := _REL.search(texto)):
        seg = _segundos_relativos(m.group("cuerpo"))
        if seg > 0:
            return ahora + timedelta(seconds=seg), (texto[: m.start()] + texto[m.end():]).strip()
    resto = texto
    # 2) la hora primero, porque consume «de la mañana» y deja libre «mañana» el día.
    hora = None
    ambigua = False
    if (m := _MEDIODIA.search(resto)):
        hora = (12, 0) if sin_tildes(m.group("x").lower()).replace(" ", "") == "mediodia" else (0, 0)
        resto = resto[: m.start()] + resto[m.end():]
    elif (m := _HORA.search(resto)):
        parsed = _hora_del_dia(m)
        if parsed is None:
            return None, texto
        hora, ambigua = (parsed[0], parsed[1]), parsed[2]
        resto = resto[: m.start()] + resto[m.end():]
    dia, resto = _dia_explicito(resto, ahora)
    resto = re.sub(r"\s{2,}", " ", resto).strip(" ,.")
    if hora is None:
        if dia is None or hora_por_defecto is None:
            return None, texto
        hora = hora_por_defecto
    h, mi = hora
    if dia is not None:
        base = dia
        if ambigua and 1 <= h <= 12:
            # Con día pero sin am/pm: 5-11 se toman de la mañana, 1-4 de la tarde.
            h = h if 5 <= h <= 11 else (12 if h == 12 else h + 12)
        cuando = base.replace(hour=h, minute=mi)
        return cuando, resto
    # Sin día: la próxima vez que ocurra. Si es ambigua (1-12), la más cercana de
    # las dos (mañana o tarde).
    candidatas = [(h, mi)]
    if ambigua and 1 <= h <= 12:
        candidatas = [(h % 12, mi), ((h % 12) + 12, mi)]
    posibles = []
    for ch, cm in candidatas:
        c = ahora.replace(hour=ch, minute=cm, second=0, microsecond=0)
        if c <= ahora:
            c += timedelta(days=1)
        posibles.append(c)
    return min(posibles), resto


# -- cómo se dice -----------------------------------------------------------------
def hora_12(d: datetime) -> str:
    """«19:05» → «7:05 p. m.»: se confirma así para que una hora mal entendida se note."""
    h = d.hour % 12 or 12
    return f"{h}:{d.minute:02d} {'a. m.' if d.hour < 12 else 'p. m.'}"


def cuando_texto(d: datetime, ahora: datetime) -> str:
    """«hoy a las 7:00 p. m.», «mañana a las 8:30 a. m.», «el lunes 19 de octubre a las …»."""
    dias = (_a_medianoche(d) - _a_medianoche(ahora)).days
    if dias == 0:
        dia = "hoy"
    elif dias == 1:
        dia = "mañana"
    elif dias < 7:
        dia = f"el {DIAS[d.weekday()]}"
    else:
        dia = f"el {DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"
    return f"{dia} a las {hora_12(d)}"


def duracion_texto(seg: int) -> str:
    """«4500» → «1 h 15 min»."""
    h, resto = divmod(int(seg), 3600)
    m, s = divmod(resto, 60)
    piezas = ([f"{h} h"] if h else []) + ([f"{m} min"] if m else [])
    if s or not piezas:
        piezas.append(f"{s} s")
    return " ".join(piezas)
