#!/usr/bin/env python3
"""La marca de CORT, generada con código y sin dependencias.

Existe porque el logo de la app (el atajo de escritorio, el instalador, la
portada del README) tiene que salir del MISMO sitio que los iconos de la PWA, y
ese sitio son los colores de `apps/web/src/cort/palette.ts` — no un fichero
binario suelto ni arte de terceros. Aquí se dibuja el anillo holográfico de
CORT (banda cian, halo violeta por dentro, núcleo brillante sobre fondo espacial
`#02040c`) píxel a píxel y se codifica a PNG con `zlib` de la biblioteca
estándar. Regla 13 y regla 7: nada que instalar, nada que descargar.

Uso:
    python3 scripts/marca.py OUTDIR            # logo.png (1024) + logo.ico (256)
    python3 scripts/marca.py OUTDIR --sizes    # además cort-192/512/maskable/180

El empaquetado ICO embebe el PNG (Vista+ lo admite): un ICONDIR + una entrada +
los bytes del 256. Sin librerías.
"""
from __future__ import annotations

import math
import struct
import sys
import zlib
from pathlib import Path

# Colores literales de palette.ts / index.css. Si allí cambian, aquí se cambia.
BG = (0x02, 0x04, 0x0C)        # --bg
CYAN = (0x5C, 0xE1, 0xFF)      # --tint / work.ui
CYAN_CORE = (0x3F, 0xD8, 0xFF)  # work.core
VIOLET = (0x8F, 0x5C, 0xFF)    # night.core
HOT = (0xDF, 0xFB, 0xFF)       # work.hot (el núcleo)


def _clamp(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def render(size: int, ring_r: float = 0.34, band: float = 0.012, pad: float = 0.0) -> bytearray:
    """Devuelve RGBA sin pre-multiplicar, fondo opaco. `pad` enche para maskable."""
    px = bytearray(size * size * 4)
    c = (size - 1) / 2.0
    inv = 1.0 / (size / 2.0)
    rr = ring_r * (1.0 - pad)
    for y in range(size):
        for x in range(size):
            dx = (x - c) * inv
            dy = (y - c) * inv
            d = math.hypot(dx, dy)
            r, g, b = BG
            # Halo violeta: disco que rema justo dentro de la banda y se oscurece
            # hacia el centro (el corazón de CORT es casi fondo, no relleno).
            glow = math.exp(-((d - rr * 0.9) ** 2) / (2 * (0.16 * (1 - pad)) ** 2))
            r += VIOLET[0] * glow * 0.5
            g += VIOLET[1] * glow * 0.5
            b += VIOLET[2] * glow * 0.5
            # Banda cian: pulso fino y nítido + una aureola estrecha alrededor.
            thin = math.exp(-((d - rr) ** 2) / (2 * (band * (1 - pad)) ** 2))
            aura = math.exp(-((d - rr) ** 2) / (2 * (band * 3.5) ** 2)) * 0.4
            band_i = _clamp(thin + aura)
            r += CYAN[0] * band_i
            g += CYAN[1] * band_i
            b += CYAN[2] * band_i
            # Núcleo: un punto caliente pequeño en el centro.
            core = math.exp(-(d * d) / (2 * (0.035 * (1 - pad)) ** 2))
            r += HOT[0] * core
            g += HOT[1] * core
            b += HOT[2] * core
            o = (y * size + x) * 4
            px[o] = min(255, int(r))
            px[o + 1] = min(255, int(g))
            px[o + 2] = min(255, int(b))
            px[o + 3] = 255
    return px


def encode_png(size: int, rgba: bytearray) -> bytes:
    """PNG truecolour+alpha, filtro 0 por línea, un IDAT. Solo biblioteca estándar."""
    raw = bytearray()
    stride = size * 4
    for y in range(size):
        raw.append(0)  # filtro "None"
        raw += rgba[y * stride:(y + 1) * stride]

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def wrap_ico(png_bytes: bytes, dim: int) -> bytes:
    """Un ICONDIR con una entrada que embebe el PNG (dim=256 → w/h se codifican 0)."""
    w = 0 if dim >= 256 else dim
    h = 0 if dim >= 256 else dim
    header = struct.pack("<HHH", 0, 1, 1)
    offset = 6 + 16
    entry = struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(png_bytes), offset)
    return header + entry + png_bytes


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 64
    out = Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    logo = encode_png(1024, render(1024))
    (out / "cort-logo.png").write_bytes(logo)
    ico_png = encode_png(256, render(256))
    (out / "cort.ico").write_bytes(wrap_ico(ico_png, 256))
    print(f"cort-logo.png {len(logo)} B · cort.ico {6 + 16 + len(ico_png)} B")
    if "--sizes" in argv:
        for name, dim in (("cort-192.png", 192), ("cort-512.png", 512),
                          ("cort-180.png", 180)):
            (out / name).write_bytes(encode_png(dim, render(dim)))
        (out / "cort-maskable-512.png").write_bytes(
            encode_png(512, render(512, pad=0.18)))
        print("tamaños PWA regenerados en", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
