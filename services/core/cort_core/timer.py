"""Temporizador de cuenta atrás: se pide, se ve, se apaga solo.

Dos cosas que deciden su forma, y las dos vinieron de la dueña del proyecto:

- **«Que salga cuando se solicite»**: no hay reloj pintado en pantalla ni
  contadores vivos en reposo. El único `asyncio.Task` que existe es el que
  arranca con un «pon un temporizador de 5 minutos», y muere al terminar o al
  cerrar la conexión. En reposo el coste de esta función es **cero bytes y cero
  CPU**, que en 1,8 GiB no es una obviedad: es la razón de no usar
  `setInterval` en la interfaz para contar.
- **Un cuadro por segundo y nada más**: la cuenta atrás viaja por el WebSocket
  como `timer`. Diez minutos son 600 cuadros de ~60 bytes; la alternativa era un
  temporizador en el navegador, que seguiría contando aunque CORT estuviera
  apagado —y un reloj que miente cuando el servidor no está es justo lo que este
  proyecto lleva evitando desde el primer panel de estado.

No toca el sistema: no importa `actions`, no ejecuta un comando, no suena (esta
máquina no tiene salida de audio verificada). Avisa por la interfaz y por el
registro de mensajes.
"""

from __future__ import annotations

import asyncio
import re
from typing import Awaitable, Callable

#: Segundos entre dos cuadros de la cuenta atrás. 1,0 es lo que ve una persona;
#: en las pruebas se baja a centésimas para no dormir la suite entera.
PASO_S = 1.0

_UNIDAD = {
    "segundo": 1,
    "segundos": 1,
    "minuto": 60,
    "minutos": 60,
    "hora": 3600,
    "horas": 3600,
}

#: «pon un temporizador de 5 minutos», «cuenta atrás de 1 hora y 30 minutos»,
#: «recuérdamelo en 20 minutos». La unidad es obligatoria: un número suelto no
#: dice si son minutos o segundos, y adivinarlo sería peor que no responder.
_MONADA = re.compile(r"(\d+(?:[.,]\d+)?)\s*(segundos?|minutos?|horas?)", re.I)

_SEED = re.compile(
    r"\b(temporizador|cuenta\s*atrás|cuenta atras|alarma|recordatorio|"
    r"en\s+(\d+)\s*(segundos?|minutos?|horas?)|suene|cron[oó]metro|timer)\b",
    re.I,
)

_CANCELA = re.compile(r"\b(cancela|cancelar|para|parar|det[ée]n|detener|olv[íi]dalo|apaga)\b.*\b(temporizador|cuenta\s*atrás|cuenta atras|alarma|recordatorio|cron[oó]metro|timer)\b|\b(cancela|olv[íi]dalo)\b", re.I)


def _numero(texto: str) -> float:
    """«2,5» → 2.5. La coma decimal es la de aquí, no la de allá. Devuelve
    `float` y no `int`: redondear antes de multiplicar convertía «2,5 minutos»
    en 120 segundos en vez de 150."""
    return float(texto.replace(",", "."))


def parse(text: str) -> int | None:
    """Segundos de cuenta atrás, o `None` si el texto no pide un temporizador.

    Suma las piezas: «1 hora y 15 minutos» son 4500 segundos, no 1 minuto (que es
    lo que daría un `search` a secas, porque el primer número que ve es el 1).
    Y si no hay palabra de pedir, tampoco hay temporizador: «5 minutos» a secas
    es un fragmento de conversación, no una orden.
    """
    if not _SEED.search(text):
        return None
    total = 0
    for cantidad, unidad in _MONADA.findall(text):
        total += int(round(_numero(cantidad) * _UNIDAD[unidad.lower()]))
    # «media hora» sin número: se dice mucho y no la saca la expresión anterior.
    if not total and re.search(r"\bmedia\b.*\bhora\b", text, re.I):
        total = 1800
    return total or None


def quiere_cancelar(text: str) -> bool:
    """`parse` y esto no se solapan: «cancela el temporizador» no debe arrancar
    una cuenta atrás nueva de cero segundos."""
    return bool(_CANCELA.search(text))


def texto(segundos: int) -> str:
    """«4500» → «1 h 15 min», para poder confirmar en español lo que se acaba de
    pedir. Se hace aquí y no en la interfaz porque el número lo sabe el core."""
    n = int(segundos)
    h, resto = divmod(n, 3600)
    m, s = divmod(resto, 60)
    piezas = []
    if h:
        piezas.append(f"{h} h")
    if m:
        piezas.append(f"{m} min")
    if s or not piezas:
        piezas.append(f"{s} s")
    return " ".join(piezas)


async def correr(enviar: Callable[[dict], Awaitable[None]], segundos: int) -> str:
    """Cuenta atrás que emite un cuadro por paso y devuelve cómo terminó.

    `enviar` es una función inyectada y no el `WebSocket`: así la prueba mide el
    comportamiento (cuántos cuadros, qué números, cómo sale) sin montar un socket,
    y el core decide el transporte.

    Se cancela con `Task.cancel()` —lo hace el server cuando la usuaria dice
    «cancela» o cuando se cierra el lazo—, y `CancelledError` **no se captura**:
    la cuenta atrás no tiene estado que limpiar, así que dejarla propagar es lo
    correcto y lo que `asyncio` espera.
    """
    restante = int(segundos)
    await enviar({"type": "timer", "restante": restante, "total": int(segundos), "estado": "corre"})
    while restante > 1:
        await asyncio.sleep(PASO_S)
        restante -= 1
        await enviar({"type": "timer", "restante": restante, "total": int(segundos), "estado": "corre"})
    if restante == 1:
        await asyncio.sleep(PASO_S)
    # El último cuadro es el cero **y** el aviso: un `termina` seguido de un
    # `corre` en cero pintaría dos veces el mismo instante.
    await enviar({"type": "timer", "restante": 0, "total": int(segundos), "estado": "termina"})
    return "termina"
