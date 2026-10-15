"""El bucle del agente: proponer → ejecutar → medir → decirle el resultado → seguir.

Hasta hoy el modelo en la nube podía proponer **una** herramienta por mensaje:
`server.py` sacaba el primer JSON, lo ejecutaba y se callaba. Un asistente que
hace una cosa por turno no es un mayordomo, es un formulario. Aquí está el
escalón que faltaba: después de cada ejecución el resultado **vuelve al modelo**
(«ya abrí Spotify, ¿qué falta?»), y el modelo decide el siguiente paso o cierra.
Lo que sale de cada paso se ejecuta por el mismo `herramientas.ejecutar` de
siempre —lista cerrada, argumentos validados, regla 6—; este archivo no toca el
sistema: ni `subprocess`, ni shell, ni rutas. Todo lo del mundo exterior entra
inyectado (`think`, `ejecutar`), así que se prueba sin encender nada.

Tres guardas que son promesas:
* **tope**: `PASOS_MAX` llamadas y `PASOS_MAX` turnos de modelo por mensaje. Sin
  tope, un modelo terco convierte un turno en un bucle girando contra la cuota
  de la usuaria.
* **repetición**: una llamada idéntica a una ya ejecutada no se ejecuta dos
  veces. Los modelos pequeños repiten su propio JSON; sin esta guarda, repetir
  es exactamente como quedarse en loop.
* **validación antes de ejecutar**: la llamada del modelo pasa por
  `herramientas.validar` aquí, y el motivo del rechazo **se le devuelve** para
  que corrija («formatear_disco no existe» → el modelo se disculpa o propone
  otra cosa). Un rechazo no ejecuta nada y no emite efecto: sale la frase
  «No pude hacer eso: …», la misma que decía el camino antiguo.

Y una decisión de honestidad: cuando hubo pasos ejecutados, el texto que ve la
usuaria es el **recuento medido** de `planner`, no la prosa final del modelo.
El modelo puede prometer; sólo `ejecutar` puede afirmar, porque es el que midió.
"""

from __future__ import annotations

from . import herramientas, planner
from .intents import PASOS_MAX


def _resultado(etiqueta: str, ok: bool, texto: str) -> str:
    """El mensaje de vuelta al modelo: qué pasó, y qué puede hacer ahora."""
    estado = "hecho" if ok else "no salió"
    return (f"Resultado de «{etiqueta}»: {estado} — {texto}. "
            "Si la usuaria pidió algo más que puedas hacer con tus herramientas, "
            "responde con otro objeto JSON; si ya terminaste, responde con texto normal.")


async def turno(history: list[dict], *, think, ejecutar) -> tuple[str, list[tuple[str, bool, str]]]:
    """Un turno de conversación con bucle de herramientas.

    `think(msgs)` es el mismo cerebro de siempre (devuelve texto); `ejecutar(llamada)`
    corre **una** herramienta ya validada y devuelve `(ok, texto)`. Devuelve
    `(lo que se le muestra a la usuaria, hechos)`, con `hechos` como
    `(etiqueta, ok, texto)` en el orden en que ocurrieron.

    Sin llamadas en la primera respuesta, el turno es conversación pura: sale
    el texto del modelo tal cual, exactamente como salía antes.
    """
    msgs = list(history)
    hechos: list[tuple[str, bool, str]] = []
    rechazos: set[int] = set()
    vistas: list[dict] = []
    reply = ""
    for _ in range(PASOS_MAX):
        reply = (await think(msgs)) or ""
        propuestas = [c for c in herramientas.extraer_llamadas(reply)]
        nuevas = []
        for c in propuestas:
            limpia, _ = herramientas.validar(c)
            # lo comparado es lo que se guardó en `vistas`: la llamada limpia si
            # validó, la cruda si fue rechazada (un rechazo repetido no repite).
            if (limpia if limpia is not None else c) in vistas:
                continue
            nuevas.append(c)
        if not nuevas:
            break
        # La respuesta del modelo entra al historial antes que sus resultados:
        # es el orden de una conversación, y `think` lo va a leer así.
        msgs.append({"role": "assistant", "content": reply})
        for llamada in nuevas:
            if len(hechos) >= PASOS_MAX:
                break
            limpia, motivo = herramientas.validar(llamada)
            etiqueta = herramientas.etiqueta(limpia or llamada)
            if limpia is None:
                # Rechazo: nada tocó el sistema, nada que medir. Se le dice el
                # motivo al modelo —puede corregirse— y a la usuaria con la
                # frase de siempre, sin marco `effect`: no hubo intento. La
                # llamada rechazada entra a `vistas` igual que las ejecutadas:
                # un modelo que repite su error no repite el rechazo cuatro veces.
                vistas.append(llamada)
                rechazos.add(len(hechos))
                hechos.append((etiqueta, False, motivo))
                msgs.append({"role": "user", "content": _resultado(etiqueta, False, motivo)})
                continue
            vistas.append(limpia)
            ok, texto = await ejecutar(limpia)
            hechos.append((etiqueta, bool(ok), str(texto)))
            msgs.append({"role": "user", "content": _resultado(etiqueta, bool(ok), str(texto))})
    if not hechos:
        return reply, []
    if len(hechos) == 1 and 0 in rechazos:
        return f"No pude hacer eso: {hechos[0][2]}.", hechos
    return planner.dicho(hechos), hechos
