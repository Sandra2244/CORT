#!/usr/bin/env python3
"""Cuenta el inventario de `docs/FUNCTIONS.md` y escupe las filas del README.

Por qué existe: las cuentas del README (totales, hechas, en curso, pendientes
por grupo) se habían estado pasando a mano de documento a documento, y se
desactualizaban —el README del 2026-10-11 decía 77 funciones cuando el inventario
largo ya tenía 82—. La regla 11 de `AGENTS.md` pide números ejecutados, no de
memoria; este script es esa ejecución.

Salida: una tabla Markdown lista para pegar en el apartado **Funciones** del
README, más la línea de totales. Sin dependencias: `re` y `pathlib`.

    python scripts/cuenta_funciones.py            # las filas del README
    python scripts/cuenta_funciones.py --grupos   # también el desglose por grupo
"""

import re
import sys
from pathlib import Path

# El nombre de la sección en FUNCTIONS.md y cómo se llama en la tabla del README.
SECCIONES = [
    ("Núcleo", "Núcleo (chat, memoria, intents, acciones en cadena, clima, "
               "configuración, atuendos en disco, cuenta atrás, llave de red, "
               "bitácora de rechazos…)"),
    ("Voz y audio", "Voz y audio (wake word, STT, TTS, volumen, reproductor, "
                    "sonda de audio…)"),
    ("Avatar", "Avatar y HUD (partículas, VRM, atuendo, tamaño, ventanas de "
               "vidrio y muelle, teclado de la cara, cuerpo proyectado, overlay, "
               "efectos, móvil)"),
    ("Gestos y visión", "Gestos y visión (desenfoque con cámara, arrastrar "
                        "paneles, MediaPipe, rostro, descripción de cámara)"),
    ("Control de dispositivos", "Control de dispositivos (apps, brillo, captura, "
                                "notificaciones…)"),
    ("Sensores y contexto", "Sensores y contexto (cámara en el arranque, "
                            "temperatura, red, MQTT, preferencias)"),
]

HECHA, CURSO, PEND = "✅", "🔨", "⬜"

# `| 38-44 | … | ✅ | …` — los rangos cuentan por lo que suman, no como una fila.
FILA = re.compile(r"^\|\s*(\d+)(?:\s*-\s*(\d+))?\s*\|")


def celdas(linea: str) -> list[str]:
    """Las celdas de una fila de tabla, sin el `|` de los bordes."""
    return [c.strip() for c in linea.strip().strip("|").split("|")]


def contar(texto: str) -> dict[str, dict[str, int]]:
    """`{sección: {total, hecha, curso, pend}}`, en el orden de `SECCIONES`."""
    cuenta = {nombre: {"total": 0, "hecha": 0, "curso": 0, "pend": 0}
              for nombre, _ in SECCIONES}
    actual = None
    for linea in texto.splitlines():
        if linea.startswith("## "):
            titulo = linea[3:].strip()
            actual = next((n for n, _ in SECCIONES if n == titulo), None)
            continue
        if actual is None or not FILA.match(linea):
            continue
        c = celdas(linea)
        if len(c) < 3:
            continue
        estado = c[2]
        if estado not in (HECHA, CURSO, PEND):
            continue  # fila de encabezado o de separación
        a, b = FILA.match(linea).groups()
        n = (int(b) - int(a) + 1) if b else 1
        cuenta[actual]["total"] += n
        cuenta[actual]["hecha" if estado == HECHA else
                     "curso" if estado == CURSO else "pend"] += n
    return cuenta


def main() -> int:
    ruta = Path(__file__).resolve().parent.parent / "docs" / "FUNCTIONS.md"
    cuenta = contar(ruta.read_text(encoding="utf-8"))
    for nombre, etiqueta in SECCIONES:
        v = cuenta[nombre]
        print(f"| {etiqueta} | {v['total']} | {v['hecha']} | {v['curso']} | {v['pend']} |")
    tot = {k: sum(v[k] for v in cuenta.values()) for k in ("total", "hecha", "curso", "pend")}
    print(f"| **Total** | **{tot['total']}** | **{tot['hecha']}** | "
          f"**{tot['curso']}** | **{tot['pend']}** |")
    if "--grupos" in sys.argv:
        print()
        for nombre, _ in SECCIONES:
            print(f"{nombre}: {cuenta[nombre]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
