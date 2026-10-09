"""El planificador: pone nombre a los pasos de un mensaje y cuenta qué pasó.

Regla 6 de `AGENTS.md` hecha módulo. Aquí no hay ninguna vía hacia el sistema:
`intents.py` decide **qué** se puede pedir (la lista cerrada), `actions.py` lo
convierte en un argv fijo y lo comprueba, `server.py` los enlaza. Este archivo
sólo mira una lista de acciones ya estructuradas y escribe texto en español, así
que no hay forma de que un comando de la usuaria —o del modelo— se cuele por
aquí: no lee texto para fabricar órdenes, lee dicts que salieron de la tabla.

Para qué sirve teniendo ya `match_intent`: hasta hoy un mensaje con dos órdenes
se resolvía como la primera y la segunda se perdía sin decir nada. Un agente que
no puede decir *«esto sí, esto no»* es un autómata con buena letra.
"""

from .actions import APP_NOMBRE
from .intents import match_all

#: Cómo se nombra cada paso en el resumen. No es el texto de la acción —ése lo
#: devuelve `actions.perform` con el número medido—, es la etiqueta con la que la
#: usuaria reconoce lo que pidió: «2 de 3 pasos hechos: … No pude: …».
_MEDIA = {"play": "reanudar la reproducción",
          "pause": "pausar la reproducción",
          "next": "pasar a la siguiente pista"}

_SUELTO = {"screenshot": "la captura de pantalla", "equalizer": "el ecualizador"}


def pasos(texto):
    """La lista de pasos ejecutables, vacía si el mensaje no es una orden."""
    return match_all(texto)


def es_plan(lista) -> bool:
    """Dos o más pasos. Con uno no hay plan que contar: sigue valiendo la frase
    corta de siempre, que dice la magnitud medida («Volumen al 45 %.») en lugar
    de un resumen. Cambiar este umbral cambiaría el protocolo de todos los
    comandos sueltos, así que está escrito y no deducido."""
    return isinstance(lista, list) and len(lista) > 1


def etiqueta(intent) -> str:
    """El paso en palabras. Una acción que no figure aquí se devuelve con su
    nombre técnico en vez de inventarse una frase: el resumen es texto, y un
    texto falso en un resumen es peor que un nombre feo."""
    if not isinstance(intent, dict):
        return ""
    accion = intent.get("action")
    if not accion:
        return ""
    if accion == "volume":
        try:
            delta = int(intent.get("delta") or 0)
        except (TypeError, ValueError):
            delta = 0
        return "subir el volumen" if delta > 0 else ("bajar el volumen" if delta < 0
                                                     else "mover el volumen")
    if accion == "launch":
        app = intent.get("app")
        return f"abrir {APP_NOMBRE.get(app) or app or 'la aplicación'}"
    if accion == "media":
        return _MEDIA.get(intent.get("cmd"), f"la reproducción ({intent.get('cmd')})")
    return _SUELTO.get(accion, accion)


def resumen(hechos) -> str:
    """Qué se hizo de lo que se pidió, dicho de una vez.

    `hechos` son las triples ``(etiqueta, ok, motivo)`` que van saliendo del
    bucle de `server.py`, en el orden de ejecución. El criterio del recuento no
    es mío: `ok` viene de `actions.perform`, que sólo lo devuelve cuando **midió**
    el cambio (el nivel de volumen leído antes y después, el archivo de la
    captura en disco, un proceso más en la lista). Por eso aquí hace falta un
    contador y no una promesa.

    Sin pasos no hay frase, y con motivo vacío no hay paréntesis suelto.
    """
    lista = [(str(e), bool(o), str(m or "").strip()) for e, o, m in hechos]
    if not lista:
        return ""
    bien = [e for e, o, _ in lista if o]
    mal = [(e, m) for e, o, m in lista if not o]
    total = len(lista)
    plural = "s" if total > 1 else ""
    dicho = f"{len(bien)} de {total} paso{plural} hecho{plural}"
    if bien:
        dicho += ": " + ", ".join(bien)
    if mal:
        dicho += ". No pude: " + ", ".join(f"{e} ({m})" if m else e for e, m in mal)
    return dicho
