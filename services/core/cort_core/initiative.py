"""Iniciativa: CORT dice algo sin que se lo pidan, y **no ejecuta nada**.

Esto es lo que separa un autómata que obedece de un compañero que se fija. Y es
también la parte del proyecto donde más fácil se rompe la regla 6 de `AGENTS.md`,
así que la frontera está escrita en el módulo entero: aquí no hay un `subprocess`,
no se importa `actions`, y lo único que sale de `sugerir()` es **una frase**. El
que decide si algo se ejecuta vive en otro sitio y con otra lista.

Dos decisiones de esta máquina, ambas medidas:

- **Sin LLM.** Evaluar el prompt cuesta 0,9 s con el modelo caliente y 113 s en
  frío, y esto se mira cada treinta segundos: una regla determinista que compara
  números es lo único que no congela el portátil. El texto sale de una plantilla,
  no de un modelo.
- **Una vez por tema y por conexión.** `dichas` vive en el lazo del WebSocket.
  Repetir el mismo aviso cada media hora no es iniciativa, es una alarma.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime

_HORA = re.compile(r"([01]?\d|2[0-3])")

#: Temperaturas de corte. No son clima: son las dos situaciones en las que decir
#: algo por iniciativa propia vale la pena, y cada una está en un extremo.
FRIO_C = 12.0
CALOR_C = 28.0


@dataclass(frozen=True)
class Momento:
    """Lo que CORT puede mirar sin pedirle nada a nadie.

    `temp_c` es **None si no hay clima medido**: un consejo de abrigo sacado de
    la temperatura de reserva (`CORT_CITY_TEMP_C`) sería un aviso inventado. Sin
    ciudad configurada no sale ninguna sugerencia de temperatura, igual que el
    cabezal no pinta un `0°` que nadie midió.
    """

    hora: int
    temp_c: float | None
    recuerdos: int


@dataclass(frozen=True)
class Sugerencia:
    clave: str
    texto: str


def enabled() -> bool:
    """`CORT_INITIATIVE=0` la apaga sin tocar código, como la capa de permisos."""
    return os.getenv("CORT_INITIATIVE", "1") != "0"


def ahora(recuerdos: int, temp_c: float | None) -> Momento:
    """El reloj de la máquina con el clima ya medido (leído de la caché).

    `CORT_NOW` existe para poder probar un turno de madrugada sin esperar a la
    madrugada: lo que se comprueba aquí son las reglas, no la hora del planeta.
    """
    override = os.getenv("CORT_NOW", "").strip()
    hora = int(override) if _HORA.fullmatch(override) else datetime.now().hour
    return Momento(hora=hora, temp_c=temp_c, recuerdos=recuerdos)


def _posibles(m: Momento):
    """Las reglas, en orden de prioridad. La primera que se cumpla es la que se dice.

    Orden deliberado: primero lo que sólo se dice una vez en la vida de la base
    (no saber el nombre), después el cuerpo (frío, calor) y al final la hora, que
    vuelve a ser cierta cada mañana.
    """
    if m.recuerdos == 0:
        yield "sin_nombre", ("Todavía no sé nada de ti. Con un «me llamo …» ya "
                             "saludo por tu nombre y me acuerdo.")
    if m.temp_c is not None and m.temp_c <= FRIO_C:
        yield "frio", f"Está a {m.temp_c:.0f}° ahí fuera. Abrígate antes de salir."
    elif m.temp_c is not None and m.temp_c >= CALOR_C:
        yield "calor", f"Hace {m.temp_c:.0f}°. Bebe agua, que yo me quedo con lo demás."
    if 0 <= m.hora <= 4:
        yield "madrugada", (f"Son las {m.hora} de la madrugada. Si estás despierto "
                            "por algo concreto, dímelo y lo intento.")
    if 6 <= m.hora <= 9:
        yield "cafete", f"Son las {m.hora} de la mañana. ¿Empezamos con café?"
    if 22 <= m.hora <= 23:
        yield "tarde", "Es tarde ya. Sigo aquí mañana si prefieres descansar."


def sugerir(m: Momento, dichas: set[str]) -> Sugerencia | None:
    """La primera regla que se cumpla y no se haya dicho ya en esta conexión.

    `None` es la respuesta más frecuente y es la correcta: un asistente que
    habla cada treinta segundos no está proponiendo nada, está interrumpiendo.
    """
    for clave, texto in _posibles(m):
        if clave not in dichas:
            return Sugerencia(clave=clave, texto=texto)
    return None
