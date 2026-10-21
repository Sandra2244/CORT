#!/usr/bin/env python3
"""Empaqueta varios PNG en un `.ico` de Windows, sin dependencias.

Existe porque el ImageMagick de este portátil (y el de muchos) **no sabe
escribir ICO**: `convert a.png b.ico` responde «No encode delegate for this
image format (ICO)» y te deja el instalador de Windows con el logo viejo. La
lectura sí funciona, así que el redimensionado lo hace `convert` y el
embolsado aquí, con `struct`.

El formato es el de siempre:

    ICONDIR         reserved=0, type=1, count
    ICONDIRENTRY×N  ancho, alto, colores=0, reservado=0, planes=1, bits=32,
                    tamaño, desplazamiento     (16 bytes por entrada)
    datos×N         el PNG **tal cual**

Embeber PNG en vez de BMP es legal desde Windows Vista y es lo que hace
electron-builder con sus propios iconos: un `.ico` de siete tamaños en ~90 KB
en lugar de ~600 KB. El `0` en ancho/alto significa 256 (un byte no llega).

Uso:  python3 scripts/empaqueta-ico.py SALIDA.ico ico-16.png ico-32.png …
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path


def alto_ancho(png: bytes) -> tuple[int, int]:
    """El `IHDR` de un PNG lleva el ancho y el alto en claro, big-endian."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("no es un PNG")
    w, h = struct.unpack(">II", png[16:24])
    return w, h


def embolsar(pdfs: list[Path]) -> bytes:
    entradas, cuerpos = [], []
    desplazamiento = 6 + 16 * len(pdfs)
    for p in pdfs:
        datos = p.read_bytes()
        w, h = alto_ancho(datos)
        if w > 256 or h > 256:
            raise ValueError(f"{p.name} mide {w}x{h}: un .ico no pasa de 256")
        # 256 se codifica como 0 porque el campo es de un byte.
        entradas.append(struct.pack("<BBBBHHII",
                                    w % 256, h % 256, 0, 0, 1, 32,
                                    len(datos), desplazamiento))
        desplazamiento += len(datos)
        cuerpos.append(datos)
    return struct.pack("<HHH", 0, 1, len(pdfs)) + b"".join(entradas) + b"".join(cuerpos)


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    salida = Path(sys.argv[1])
    pdfs = [Path(p) for p in sys.argv[2:]]
    bytes_ico = embolsar(pdfs)
    salida.write_bytes(bytes_ico)
    tamaños = ", ".join(f"{alto_ancho(p.read_bytes())[0]}" for p in pdfs)
    print(f"{salida.name}: {len(pdfs)} tamaños ({tamaños}), {len(bytes_ico)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
