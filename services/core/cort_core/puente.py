"""El puente de memoria: que el teléfono y el portátil sepan lo mismo de Sandra.

`v0.15.0` dejó **dos cabezas** — `memory.db` en Python y `cort.db` dentro del APK —
sin saber la una de la otra, y `docs/PLATFORM.md` lo apuntó como la segunda deuda del
acuerdo Java: lo que la dueña aprendía en el aparato no lo sabía el portátil, y al
revés. Este módulo es la mitad del portátil, y está escrita **sin red dentro**: sabe
serializar y fusionar, y es `server.py` el que la asoma al mundo. Que sea puro no es
decoración — en esta máquina no hay dónde levantar un teléfono, así que lo que se
puede probar es la lógica, y se prueba aquí.

Cuatro reglas, cada una contra un modo concreto en que sincronizar sale peor que no
sincronizar:

1. **La llave de red no viaja dentro de un recuerdo.** El cuadro se pide por HTTP con
   el token en la consulta, y lo que se exporta es la memoria de la usuaria. Si un
   hecho contiene la llave —«mi clave del wifi es …»—, esa fila **no sale**: exportar
   no puede convertirse en regalar la llave a quien ya tiene el enlace. Se cuenta como
   `ocultados` para que el número se vea y no se pierda en silencio.
2. **Dedupe normalizado, no literal.** `remember()` compara cadenas exactas y su
   limitación está escrita en `docs/STATUS.md` («Me llamo X» y «me llamo X» son dos
   filas). Un puente que comparara igual multiplicaría el mismo dato una vez por
   sincronía, en dos bases que se sacan fotos. Aquí la clave de la fila es
   `normaliza()`: minúsculas (`casefold`) y espacios colapsados.
3. **Fusionar nunca borra.** Un lado que se poda no es un lado que olvidó: es un lado
   que hizo borrar en el otro. `fusionar` sólo añade, y lo que no cabe (vacío, largo,
   con la llave dentro, con control characters) se **cuenta** como rechazado en vez de
   guardarse a medias.
4. **Topos de una lista cerrada, y por escrito.** `MAX_CONTENIDO` por fila,
   `MAX_FILAS` por viaje y `MAX_BYTES` por petición. Un puente sin techo es una
   petición que se come los 1,8 GiB de esta máquina.

Código en español como el resto del borde (`audit.py`, `security.py`, `agenda.py`);
documentación e interfaz también, que es la regla 8 de `AGENTS.md` aplicada a un
módulo que sólo habla con la dueña.
"""
from __future__ import annotations

import re

VERSION = 1

# Topes. No son un capricho: esta máquina tiene 1,8 GiB y un payload sin techo se
# carga el servidor antes de llegar a la primera fila.
MAX_CONTENIDO = 300      # caracteres por recuerdo
MAX_FILAS = 500          # recuerdos por viaje
MAX_BYTES = 262_144      # cuerpo de una petición de subida (256 KiB)

_ESPACIOS = re.compile(r"\s+")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def normaliza(texto: object) -> str:
    """Clave de comparación de un recuerdo: sin espacios de sobra y sin mayúsculas.

    No se quitan tildes: «canción» y «cancion» son dos cosas distintas para la dueña
    y aquí no se decide por ella. Sí se `casefold`, que es más ancho que `lower()` y
    por eso «SS» y «ss» quedan igual.
    """
    return _ESPACIOS.sub(" ", str(texto or "")).strip().casefold()


def exportar(filas, *, origen: str = "escritorio", llave: str = "",
             tope: int = MAX_FILAS) -> dict:
    """El cuadro viajero a partir de las filas del almacén.

    `filas` es una secuencia de dicts con `content` y `created_at` — lo que devuelve
    `MemoryStore.filas()` — y se aceptan dicts sueltos a propósito: el lado del
    teléfono no tiene un `MemoryStore` detrás, y la misma función sirve para los dos.

    Una fila no sale si está vacía, si pasa `MAX_CONTENIDO`, o si lleva la llave de
    red dentro (regla 1). Lo descartado se devuelve **contado** en `ocultados`.
    """
    recuerdos: list[dict] = []
    ocultados = 0
    for fila in filas:
        contenido = str(fila.get("content") or fila.get("contenido") or "").strip()
        if not contenido or len(contenido) > MAX_CONTENIDO:
            ocultados += 1
            continue
        if llave and llave in contenido:
            ocultados += 1
            continue
        recuerdos.append({"contenido": contenido,
                          "cuando": str(fila.get("created_at") or fila.get("cuando") or "")})
        if len(recuerdos) >= tope:
            break
    return {"tipo": "memoria", "version": VERSION, "origen": origen,
            "total": len(recuerdos), "ocultados": ocultados, "recuerdos": recuerdos}


def fusionar(destino, cuadro, *, llave: str = "") -> dict:
    """Metiendo un cuadro viajero en un almacén, **sin borrar nada** (regla 3).

    `destino` es cualquier cosa con `.remember(texto)` — `MemoryStore` en el
    portátil—. Devuelve el recuento de las cuatro salidas posibles, y ese recuento es
    lo que el teléfono enseña: «4 nuevos, 12 ya estaban, 1 descartado».

    Valora el cuadro antes de tocar disco: versión que no es la suya, `recuerdos` que
    no es una lista, o un payload que pasa `MAX_FILAS` son `ValueError` con mensaje en
    español — el servidor los traduce a 400 y no deja medio importing dentro.
    """
    if not isinstance(cuadro, dict):
        raise ValueError("el cuadro de memoria no es un objeto")
    if cuadro.get("version") != VERSION:
        raise ValueError(f"versión de cuadro {cuadro.get('version')!r}: este puente habla la {VERSION}")
    recuerdos = cuadro.get("recuerdos")
    if not isinstance(recuerdos, list):
        raise ValueError("el cuadro no trae lista de recuerdos")
    if len(recuerdos) > MAX_FILAS:
        raise ValueError(f"demasiados recuerdos en un viaje: {len(recuerdos)} (tope {MAX_FILAS})")

    existentes = {normaliza(fila.get("content") or fila.get("contenido") or "")
                  for fila in destino.filas()}
    nuevos = repetidos = rechazados = 0
    for fila in recuerdos:
        contenido = _limpia(fila, llave)
        if contenido is None:
            rechazados += 1
            continue
        clave = normaliza(contenido)
        if not clave or clave in existentes:
            repetidos += 1
            continue
        existentes.add(clave)
        destino.remember(contenido)
        nuevos += 1
    return {"nuevos": nuevos, "repetidos": repetidos, "rechazados": rechazados,
            "total": nuevos + repetidos + rechazados}


def _limpia(fila, llave: str) -> str | None:
    """El recuerdo listo para guardar, o `None` si no debe guardarse.

    Los caracteres de control se quitan — dentro del SQLite no hay problema, pero
    viajan por JSON y un `\x00` en un recuerdo es una fila que luego nadie puede leer
    en la pantalla del teléfono.
    """
    if not isinstance(fila, dict):
        return None
    contenido = _CONTROL.sub(" ", str(fila.get("contenido")
                                      or fila.get("content") or "")).strip()
    if not contenido or len(contenido) > MAX_CONTENIDO:
        return None
    if llave and llave in contenido:
        return None
    return contenido
