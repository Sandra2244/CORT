"""Lo que CORT puede afirmar de sí mismo.

El panel de la interfaz enseña hechos medidos, no etiquetas decorativas: un
holograma que dice "en línea" porque sí no informa de nada. Cada valor sale de
este proceso —cuántos recuerdos hay en la base, qué modelo contestó la última
vez, si la capa de permisos está encendida.

No hay reloj ni latido: el estado se manda al conectar y después de cada turno,
que es cuando algo puede haber cambiado. Un número que se queda quieto mientras
nada ocurre es exactamente tan cierto como uno que anda solo.
"""

from . import actions, brain


def build(memory, keep: int) -> dict:
    """`brain` es None hasta que el LLM interviene por primera vez: no se puede
    decir qué modelo contesta sin haberle preguntado nunca."""
    return {
        "type": "status",
        "memories": memory.count(),
        "keep": int(keep),
        "brain": brain.last_model(),
        "ollama": brain.last_reachable(),
        "actions": actions.enabled(),
    }
