#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CORT recuerda: constitución, memoria tuya y autocrítica antes de hablar (S4).

Por qué este módulo existe y por qué NO es entrenamiento
--------------------------------------------------------
Los asistentes grandes (Claude, Gemini) aprenden de dos maneras distintas, y
confundirlas es la trampa habitual:

1. **Los pesos**: una red que predice el token siguiente, ajustada millones de
   veces sobre un corpus. Eso ocurre en GPU y tarda días. En este equipo está
   medido y descartado: Celeron N2805, 2 núcleos, sin AVX/AVX2 y entre 150 y 348
   MB libres (cort_perfil). Reentrenar aquí no cabe, y prometerlo sería mentir.

2. **La memoria escrita**: lo que el asistente "sabe de ti" entre sesión y sesión
   no vive en los pesos, vive en texto que se vuelve a meter en el prompt cada
   vez. Eso es leer y escribir un archivo: cuesta milisegundos de CPU y cabe
   entero en la Canaima. **Esto es lo que hace este módulo**, y es la parte que
   hace que un asistente parezca una persona que te conoce.

Lo mismo con la "constitución" y la "autorreflexión" que se describen en el
entrenamiento real: la constitución es un texto de principios que va en el
system prompt, y la autorreflexión es una pasada de control antes de responder.
Aquí las dos son código determinista y medible, no magia: `constitucion()` y
`revisar()`. Con un modelo de 135 M de parámetros en 260 MB de RAM, un control
escrito y probado vale más que pedirle buena voluntad.

Qué se guarda y qué no
----------------------
Se guarda: preferencias (cómo llamarte, tono, ciudad), hechos que tú dices, y
correcciones ("no me digas X, dime Y"). Todo en texto plano dentro de
`CORT_DATOS/memoria.json`, en tu equipo, sin salir a ninguna red. No se guarda
una sola frase de más: si no aporta un hecho o una preferencia, `aprender()` lo
dice y no lo escribe. Nunca se guarda lo que se lee por cámara ni el contenido
de micrófono (S2/F3): aquí entra sólo lo que se escribe o se dicta como orden
de memoria.
"""
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

VERSION = "s4"

CASA = Path(os.environ.get("CORT_HOME", str(Path.home())))
DATOS = Path(os.environ.get("CORT_DATOS", str(CASA / ".local" / "share" / "cort")))
RUTA = DATOS / "memoria.json"

# Cuánto se le deja al prompt. Un modelo pequeño pierde el hilo si el contexto es
# largo, y cada token de más en la Canaima es tiempo de respuesta medible.
LIMITE_CONTEXTO = int(os.environ.get("CORT_MEM_LIMITE", "420"))
LIMITE_HECHOS = 200                 # hechos sueltos; más allá, se poda por antigüedad
MAX_CARACTERES_VOZ = 420            # lo que CORT dice en voz alta, para no ser sermón

# ------------------------------------------------------------------ almacenamiento
def _leer():
    try:
        with open(RUTA, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            d.setdefault("preferencias", {})
            d.setdefault("hechos", [])
            d.setdefault("correcciones", [])
            return d
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return {"preferencias": {}, "hechos": [], "correcciones": []}


def _escribir(d):
    """Escribe y reléye antes de decir "guardado"."""
    try:
        DATOS.mkdir(parents=True, exist_ok=True)
        with open(RUTA, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        with open(RUTA, encoding="utf-8") as f:
            json.load(f)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "motivo": f"{type(e).__name__}: {e}"}


def sin_acentos(t):
    return "".join(c if not unicodedata.combining(c) else ""
                   for c in unicodedata.normalize("NFD", (t or "").lower()))


# --------------------------------------------------------------------- constitución
CONSTITUCION = (
    "PRINCIPIOS DE CORT (versión {v}):\n"
    "1. Nada inventado. Si un dato no se midió ni se leyó, se dice que falta y qué haría "
    "falta para tenerlo.\n"
    "2. La puerta de la memoria manda: si el modelo o la acción no caben en la RAM medida, "
    "se dice el número y no se intenta.\n"
    "3. Privacidad: los cuadros de la cámara no se guardan; las notas y la memoria sólo "
    "viven en este equipo; nada se comparte con un dispositivo que no está emparejado.\n"
    "4. Las órdenes que borran, tapan o apagan piden un sí humano; un plan del modelo "
    "nunca se autosirve.\n"
    "5. CORT es útil y tiene carácter: puede bromear, puede insistir una vez si sabe que "
    "equivocarse cuesta caro, pero nunca discute ni sermona.\n"
    "6. Responde corto y en español, sin listas salvo que se pidan.\n"
    "7. Si la reja rechazó una acción, CORT no dice que la hizo."
)


def constitucion():
    """El texto de principios. Si existe CORT_DATOS/constitucion.md, ése manda:
    la constitución es editable porque el producto es tuyo, no de un proveedor."""
    personalizada = DATOS / "constitucion.md"
    try:
        texto = personalizada.read_text(encoding="utf-8").strip()
        if len(texto) > 40:
            return texto
    except Exception:
        pass
    return CONSTITUCION.format(v=VERSION)


# ------------------------------------------------------------------------ la persona
def preferencias():
    return _leer()["preferencias"]


def nombre_de(d):
    return (d.get("preferencias", {}).get("nombre")
            or os.environ.get("CORT_NOMBRE") or "Sandra")


def nombre():
    """Cómo se llama quien habla, según su memoria (o CORT_NOMBRE si aún no la llenó)."""
    return nombre_de(_leer())


def tono(d):
    return d.get("preferencias", {}).get("tono", "cercano")


# Palabras de humor: se eligen por hora y por frase, no por azar puro, para que el
# cambio sea estable dentro de una misma respuesta y no suene a ruleta.
SALUDOS = {
    "mañana": ("Buenos días, {n}.", "{n}, aquí sigo desde las {h}.", "Día {d}, {h}: vamos, {n}."),
    "tarde":  ("Buenas tardes, {n}.", "{n}, te escucho.", "Sigo encendido, {n}."),
    "noche":  ("Buenas noches, {n}.", "{n}, aquí estoy.", "A estas horas {h}, {n}: dime rápido."),
}
APERTURAS = ("", "Mira, ", "Pues ", "Va: ", "Aquí está: ")


def variedad(semilla, opciones):
    """Elección determinista pero que cambia: la misma pregunta a la misma hora suena
    igual, y a otra hora no parece una grabación rota."""
    if not opciones:
        return ""
    n = int(time.strftime("%H")) // 2
    for c in str(semilla or ""):
        n += ord(c)
    return opciones[n % len(opciones)]


def franja():
    h = int(time.strftime("%H"))
    return "mañana" if 5 <= h < 12 else ("tarde" if 12 <= h < 20 else "noche")


def saludo(nombre=None):
    plantilla = variedad(time.strftime("%Y%m%d%H"), SALUDOS[franja()])
    return plantilla.format(n=nombre or "CORT", h=time.strftime("%H:%M"),
                            d=time.strftime("%A"))


# --------------------------------------------------------------------------- memoria
def _palabras(texto):
    return [w for w in re.findall(r"[a-zñ]{4,}", sin_acentos(texto)) if w not in STOP]


STOP = set("este esta esto para como pero porque cuando donde tiene tengo haces eres eres "
           "puedes podrías antes después desde hasta siendo estando".split())


def _apuntar(texto, clave=None):
    """Una frase de memoria: la clave manda si existe, si no las palabras largas."""
    d = _leer()
    k = sin_acentos(clave or "").strip()
    heuristica = " ".join(_palabras(texto)[:6]) or sin_acentos(texto)[:40]
    clave_final = k or heuristica
    if not clave_final:
        return {"ok": False, "motivo": "no hay nada que recordar en esa frase"}
    d["hechos"].append({"clave": clave_final, "texto": texto.strip(),
                        "hora": int(time.time())})
    if len(d["hechos"]) > LIMITE_HECHOS:
        d["hechos"] = d["hechos"][-LIMITE_HECHOS:]
    r = _escribir(d)
    return {**r, "hechos": len(d["hechos"]), "clave": clave_final}


# "recuerda que X" / "aprende que X" / "no me digas X, dime Y" / "llámame X"
# Nota y "anota que"/"guarda la nota" NO van aquí: ésas son de cort_vida (F4), que
# guarda el texto entero como nota. Aquí sólo caben preferencias y hechos cortos.
RE_MEMORIA = re.compile(
    r"(?:recuerda|aprende|guárdate|guardate|ten presente|memo)\s+(?:que\s+)?(.{4,200})$",
    re.I)
RE_PREFERENCIA = re.compile(r"(?:prefiero|me gusta|no me gusta)\s+(?:que\s+)?(.{4,160})$", re.I)
RE_NOMBRE = re.compile(r"(?:me llamo|mi nombre es) (\w{2,24})$", re.I)
RE_LLAMAME = re.compile(r"(?:llámame|llamame)\s+(\w{2,20})$", re.I)
RE_TONO = re.compile(r"(?:con|en|a)\s+(?:el\s+)?tono\s+(?:de\s+)?([\wáéíóúñ]{3,20})$", re.I)
RE_CORRECCION = re.compile(r"no me (?:digas|cantes|sueltas) «?(.+?)»?,?\s*(?:dime|di|mejor)\s+(.+)$", re.I)
RE_OLVIDA = re.compile(r"olvida (?:que\s+)?(.{3,120})$", re.I)
# Ojo con las tildes: esta se compara contra el texto SIN acentos (`q`), así que va
# escrita sin ellos. Es el fallo que encontró la suite: con «qué» y tilde, la pregunta
# «¿qué sabes de mí?» no casaba nunca y CORT contestaba con el modelo en vez de con
# su propia memoria.
RE_QUÉ_SABES = re.compile(r"que (?:sabes|guardas|recuerdas|tienes) (?:de mi|sobre mi)", re.I)

# Freno de falsos positivos: una orden disfrazada de preferencia («prefiero que
# abras el navegador») no es un gusto, es una acción, y si se guarda como gusto
# CORT deja de hacerla. La memoria sólo admite frases sin verbo de acción.
# Van las formas conjugadas completas y no la raíz: «abril» tiene que poder
# guardarse («recuerda que el examen es en abril») y por eso no basta con "abr".
ACCIONES = set("""
abre abrir abres abra abras abran abierto abierta abrid
cierra cerrar cierres cierre cierren cerrado cerrada cerre cierre
mueve mover muevas mueva muevan movido movida
copia copiar copies copie copien copiado
borra borrar borres borre borren borrado
reproduce reproducir reproduzcas reproduzca reproducido
pausa pausar pauses pause pausado
apaga apagar apagues apague apagado
enciende encender enciendas encienda encendido
maximiza maximizar maximice minimiza minimizar minimice
envia enviar envias envies envie enviado
descarga descargar descargues descargue descargado
crea crear creas cree creen creado
""".split())


def _hay_accion(clause):
    return bool(set(_palabras(clause)) & ACCIONES)


def aprender(texto):
    """Devuelve la respuesta si la frase es una orden de memoria, o None si no lo es.

    Es el camino por el que CORT «entrena» sin GPU: tus correcciones se quedan
    escritas y vuelven en el prompt de la próxima pregunta.
    """
    crudo = (texto or "").strip()
    if not crudo:
        return None
    q = sin_acentos(crudo)

    m = RE_CORRECCION.search(crudo)
    if m:
        d = _leer()
        # Se quitan las comillas angulares por delante y por detrás: si no, la
        # corrección se guarda como ««jefa»» y al recordarla sale duplicada.
        limpia = lambda s: s.strip().strip("«»\"' ").strip()
        d["correcciones"].append({"no": limpia(m.group(1)), "di": limpia(m.group(2)),
                                  "hora": int(time.time())})
        d["correcciones"] = d["correcciones"][-40:]
        r = _escribir(d)
        if not r.get("ok"):
            return f"No pude guardarlo: {r.get('motivo')}"
        return (f"Anotado: no diré «{limpia(m.group(1))}» y en su lugar diré "
                f"«{limpia(m.group(2))}». Está en {RUTA.name}, en tu equipo.")

    m = RE_NOMBRE.search(crudo)
    if m:
        d = _leer()
        d["preferencias"]["nombre"] = m.group(1).capitalize()
        _escribir(d)
        return f"Hecho, {m.group(1).capitalize()}. Así te llamo de ahora en adelante."

    m = RE_LLAMAME.search(crudo)
    if m:
        d = _leer()
        d["preferencias"]["nombre"] = m.group(1).capitalize()
        _escribir(d)
        return f"Vale, {m.group(1).capitalize()}."

    m = RE_TONO.search(crudo)
    if m:
        d = _leer()
        d["preferencias"]["tono"] = m.group(1).lower()
        _escribir(d)
        return f"Tono {m.group(1).lower()} guardado. Lo aplico al responderte."

    if RE_QUÉ_SABES.search(q):
        return resumen()

    m = RE_OLVIDA.search(crudo)
    if m:
        d = _leer()
        buscar = sin_acentos(m.group(1))
        antes = len(d["hechos"])
        d["hechos"] = [h for h in d["hechos"]
                       if buscar not in sin_acentos(h.get("texto", "") + " " + h.get("clave", ""))]
        _escribir(d)
        n = antes - len(d["hechos"])
        return (f"Olvidado: {n} apunte{'s' if n != 1 else ''} sobre «{m.group(1).strip()}»."
                if n else f"No tenía nada guardado con «{m.group(1).strip()}».")

    m = RE_PREFERENCIA.search(crudo)
    if m:
        if _hay_accion(m.group(1)):
            return None          # es una orden disfrazada: la atiende la capa de acción
        d = _leer()
        d["preferencias"].setdefault("gustos", [])
        d["preferencias"]["gustos"] = (d["preferencias"]["gustos"] +
                                       [m.group(1).strip()])[-20:]
        _escribir(d)
        return f"De acuerdo: {m.group(1).strip()}. Lo tengo en cuenta."

    m = RE_MEMORIA.search(crudo)
    if m:
        if _hay_accion(m.group(1)):
            return None          # «recuerda que abrí la nota» no es un hecho, es una orden
        r = _apuntar(m.group(1))
        if not r.get("ok"):
            return f"No pude guardarlo: {r.get('motivo')}"
        n = r['hechos']
        return (f"Guardado: {m.group(1).strip()}  "
                f"({n} apunte{'s' if n != 1 else ''} en tu memoria local).")

    return None


def resumen():
    d = _leer()
    p = d.get("preferencias", {})
    trozos = []
    if p.get("nombre"):
        trozos.append("te llamas " + p["nombre"])
    if p.get("ciudad"):
        trozos.append("tu ciudad es " + p["ciudad"])
    if p.get("tono"):
        trozos.append("hablamos en tono " + p["tono"])
    gustos = p.get("gustos") or []
    if gustos:
        trozos.append("preferencias: " + "; ".join(gustos[-3:]))
    if d.get("correcciones"):
        c = d["correcciones"][-1]
        trozos.append(f"última corrección: no «{c['no']}», di «{c['di']}»")
    n = len(d.get("hechos", []))
    ultimo = (d.get("hechos") or [{}])[-1].get("texto", "")
    if ultimo:
        trozos.append("último apunte: " + ultimo[:90])
    return (f"Sé {len(trozos)} cosas de ti y tengo {n} apunte" + ("s" if n != 1 else "") + ": " +
            "; ".join(trozos) + f". Todo dentro de {RUTA}, en este equipo.")


def contexto(texto, limite=None):
    """Los apuntes que tienen que ver con esta pregunta, ya listos para el prompt.

    Sin vectorizar nada: coincidencia de palabras. En 2 núcleos una búsqueda
    semántica con modelo costaría más tiempo del que gana.
    """
    limite = limite or LIMITE_CONTEXTO
    d = _leer()
    claves = set(_palabras(texto))
    elegidos = []
    for h in reversed(d.get("hechos", [])):
        if not claves:
            break
        si = set(_palabras(h.get("clave", "") + " " + h.get("texto", "")))
        if si & claves:
            elegidos.append(h["texto"])
        if sum(len(x) for x in elegidos) > limite:
            break
    p = d.get("preferencias", {})
    cabecera = []
    if p.get("nombre"):
        cabecera.append(f"Se llama {p['nombre']}.")
    if p.get("tono"):
        cabecera.append(f"Tono: {p['tono']}.")
    cuerpo = " · ".join(elegidos[::-1])[:max(0, limite)]
    aviso = ""
    if d.get("correcciones"):
        ult = d["correcciones"][-1]
        aviso = f"Corrección pedida: no digas «{ult['no']}», di «{ult['di']}»."
    partes = [" ".join(cabecera)]
    if cuerpo:
        partes.append("Apuntes: " + cuerpo + ".")
    if aviso:
        partes.append(aviso)
    return " ".join(x for x in partes if x).strip()


# ------------------------------------------------------------------ el system prompt
def sistema(texto, estado=None, nombre=None):
    """System prompt del chat: persona + constitución + lo que sabe de ti.

    Antes estaba escrito a mano en el puente con dos frases fijas; aquí se arma
    cada vez con la constitución y la memoria recuperada, que es lo que hace que
    dos preguntas seguidas se contesten con la misma información de ti.
    """
    estado = estado or {}
    quien = nombre or nombre_de(_leer())
    memo = contexto(texto)
    base = (f"Eres CORT, asistente personal de {quien} en Linux, con humor fino y "
            f"sentido práctico. Hablas español neutro, corto y sin listas salvo que se "
            f"pidan. Nunca inventas un dato ni una ruta: si falta, lo dices con el número "
            f"que tienes y qué haría falta para tener el que falta.\n")
    const = constitucion()
    trozo = base + const
    if memo:
        trozo += f"\nLO QUE SABES DE {quien}: {memo}"
    if estado.get("user_city"):
        trozo += f"\nCiudad declarada: {estado['user_city']}."
    # El tope existe porque un prompt largo en un modelo de 135 M cuesta segundos
    # medibles en esta máquina; si la constitución empuja demasiado, se corta por
    # líneas y no a mitad de palabra.
    if len(trozo) > 1400:
        lineas = trozo.split("\n")
        while len("\n".join(lineas)) > 1400 and len(lineas) > 3:
            lineas.pop(1)
        trozo = "\n".join(lineas)
    return trozo


# ----------------------------------------------------------------------- autocrítica
PROMESA_VACIA = re.compile(r"\b(ya (cerré|abrí|borré|moví|pausé|apagué|reinicié)|"
                           r"listo[,]? (cerré|abrí|borré|moví|hecho)|"
                           r"he (cerrado|abierto|borrado|movido))\b", re.I)
NO_SE = re.compile(r"\b(no sé|no lo sé|no tengo ese dato|no puedo saberlo|no está medido)\b", re.I)
MARKDOWN = re.compile(r"(\*\*|```|^\s*[-*]\s|^\s*\d+\.\s)", re.M)


def revisar(texto, origen="real", accion_rechazada=None):
    """La pasada de autorreflexión, hecha con reglas que se pueden probar.

    No es el modelo criticándose: es un control escrito. Devuelve el texto limpio y
    la lista de lo que cambió, para que el puente pueda decirlo en pantalla.
    """
    crudo = (texto or "").strip()
    ajustes = []
    if not crudo:
        return {"ok": True, "texto": crudo, "ajustes": ajustes}

    limpio = MARKDOWN.sub("", crudo).replace("  ", " ").strip()
    if limpio != crudo:
        ajustes.append("sin formato de lista ni negritas")

    if PROMESA_VACIA.search(limpio) and origen != "real":
        limpio = ("No puedo afirmar que lo hice: no hay prueba del sistema. "
                  + limpio)
        ajustes.append("se quitó una promesa sin verificación")

    if accion_rechazada:
        limpio = (f"Eso lo paró la reja: {accion_rechazada}. "
                  f"No voy a decir que lo hice.")
        ajustes.append("la reja rechazó la acción y CORT no la promete")

    # Un modelo pequeño dice «no sé» aunque la memoria sí tenga el dato. Aquí se lo
    # recuerda, que es exactamente la diferencia entre un chat y un asistente.
    if NO_SE.search(limpio):
        # (el contexto ya va en el prompt; se avisa para que el puente pueda reintentar)
        ajustes.append("admite que no sabe")

    if len(limpio) > MAX_CARACTERES_VOZ:
        corte = limpio[:MAX_CARACTERES_VOZ]
        punto = max(corte.rfind("."), corte.rfind("?"), corte.rfind("!"))
        limpio = (corte[:punto + 1] if punto > 60 else corte.rstrip() + "…")
        ajustes.append(f"cortado a {len(limpio)} caracteres para voz")

    return {"ok": True, "texto": limpio, "ajustes": ajustes}


# ------------------------------------------------------------------------ iniciativa
def iniciativa(estado=None, pendiente=None, nivel=None, ram_libre=None):
    """Lo que CORT propone antes de que se lo pidas.

    Es la parte «anticipativa» de un asistente: no adivina el futuro, mira lo que
    ya está medido (recordatorio venciendo, RAM, nivel de cerebro) y comenta una
    vez. Insistir dos veces ya es molestar.
    """
    d = _leer()
    avisos = d.setdefault("avisos", {})
    ahora = time.time()
    salidas = []

    if pendiente:
        clave = f"pend:{pendiente.get('id')}"
        if ahora - avisos.get(clave, 0) > 1800:
            faltan = pendiente.get("faltan_seg", 0)
            si = ("en " + (f"{faltan//60} min" if faltan >= 60 else f"{faltan} s")) if faltan else "ahora"
            salidas.append(f"Ojo: «{pendiente['texto']}» {si}.")
            avisos[clave] = ahora

    if ram_libre is not None and ram_libre < 200:
        clave = "ram:justa"
        if ahora - avisos.get(clave, 0) > 3600:
            salidas.append(f"RAM justo: {ram_libre} MB libres. Si cargo un modelo me atraganto.")
            avisos[clave] = ahora

    if nivel == 0:
        clave = "nivel:0"
        if ahora - avisos.get(clave, 0) > 21600:
            salidas.append("Hoy respondo con reglas locales: sin RAM suficiente no bajo el cerebro.")
            avisos[clave] = ahora

    if salidas:
        _escribir(d)
    return variedad(str([s[:12] for s in salidas]),
                    salidas) if len(salidas) == 1 else " ".join(salidas)


# ------------------------------------------------------------------------- comando
def disponibilidad():
    d = _leer()
    return {"modulo": "cort_memoria", "version": VERSION, "origen": "real",
            "ruta": str(RUTA), "existe": RUTA.exists(),
            "hechos": len(d.get("hechos", [])),
            "preferencias": len(d.get("preferencias", {})),
            "correcciones": len(d.get("correcciones", [])),
            "constitucion": len(constitucion())}


def main(argv):
    if len(argv) > 1 and argv[1] == "selftest":
        return selftest()
    print(json.dumps(disponibilidad(), ensure_ascii=False, indent=1))
    return 0


def selftest():
    """Pruebas de la memoria, la constitución y la autocrítica, con número."""
    import tempfile
    global DATOS, RUTA
    arena = Path(tempfile.mkdtemp(prefix="cort-mem-"))
    DATOS, RUTA = arena, arena / "memoria.json"
    casos = []

    aprender("recuerda que el examen de suelo pelviano es el 12 de noviembre")
    ctx = contexto("cuándo es el examen")
    casos.append(("el apunte vuelve en el contexto", "suelo pelviano" in ctx))

    r = aprender("llámame Askher")
    casos.append(("nombre guardado", "Askher" in (r or "") and
                  preferencias().get("nombre") == "Askher"))

    r = aprender("no me digas «usuario», dime «jefa»")
    casos.append(("corrección guardada", bool(_leer()["correcciones"]) and "jefa" in (r or "")))

    r = aprender("hola, ¿qué tal?")
    casos.append(("una charla no se guarda como memoria", r is None))
    casos.append(("la charla no borró lo demás", len(_leer()["hechos"]) == 1))

    r = aprender("prefiero que abras el navegador")
    casos.append(("una orden disfrazada no se guarda como gusto", r is None))
    r = aprender("recuerda que borre la carpeta")
    casos.append(("una orden disfrazada no se guarda como hecho", r is None))

    s = sistema("cuándo es el examen", {"user_city": "Carora"})
    casos.append(("la constitución va en el prompt", "PRINCIPIOS DE CORT" in s))
    casos.append(("la memoria va en el prompt", "suelo pelviano" in s))
    casos.append(("el prompt cabe (<=1400)", len(s) <= 1400))

    v = revisar("- **Ya cerré la ventana** y listo\n- otra cosa", origen="no disponible")
    casos.append(("sin markdown en la voz", "*" not in v["texto"]))
    casos.append(("promesa sin prueba se corrigió", "No puedo afirmar" in v["texto"]))

    w = revisar("ya " + "borré " * 120)
    casos.append(("sermón recortado", len(w["texto"]) <= MAX_CARACTERES_VOZ + 4))

    x = revisar("cualquier cosa", origen="real", accion_rechazada="eso toca tu /")
    casos.append(("la reja rechazó y no se promete", "paró la reja" in x["texto"]))

    y = iniciativa({"x": 1}, pendiente={"id": 1, "texto": "beber agua", "faltan_seg": 90},
                   nivel=0, ram_libre=150)
    casos.append(("iniciativa ante un pendiente", "beber agua" in (y or "")))
    z = iniciativa({"x": 1}, pendiente={"id": 1, "texto": "beber agua", "faltan_seg": 90},
                   nivel=0, ram_libre=150)
    casos.append(("no insiste a la segunda", not z))

    ok = 0
    for nombre, bien in casos:
        print(f"{'ok  ' if bien else 'FALLO'} {nombre}")
        ok += bool(bien)

    # Costo medido en esta máquina: si la memoria fuera cara, el puente no la
    # consultaría en cada frase. Se cronometra el ciclo completo, no una llamada suelta.
    t0 = time.perf_counter()
    for _ in range(50):
        aprender("¿qué sabes de mí?")
        contexto("cuándo es el examen")
        sistema("cuándo es el examen", {})
        revisar("una respuesta normal", origen="real")
    ms = (time.perf_counter() - t0) * 1000 / 50
    print(f"ciclo memoria+prompt+revisión: {ms:.2f} ms por frase")
    print(f"{ok}/{len(casos)} · memoria en {RUTA}")
    return 0 if ok == len(casos) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
