"""Pruebas de `scripts/marca.py` — la marca generada con código.

Tres cosas que se rompen de verdad en un escritor de PNG/ICO a mano y ninguna
necesita un visor: la firma y dimensiones del PNG, la cabecera del ICO (que el
PNG embebido empiece donde la entrada dice), y que el dibujo sea la marca de
CORT y no un cuadrado: centro casi fondo, anillo cian brillante a ~0,34 del
radio, y todo opaco (un icono con alfa 0 en las esquinas se ve recortado raro
en algunos escritorios Linux). Se corren con tamaño pequeño para que el coste
sea de milisegundos: la prueba mira la FORMA, no la belleza.
"""
from __future__ import annotations

import importlib.util
import struct
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "marca.py"
_espec = importlib.util.spec_from_file_location("marca", SCRIPT)
marca = importlib.util.module_from_spec(_espec)
sys.modules["marca"] = marca
_espec.loader.exec_module(marca)


class TestCodificadores(unittest.TestCase):
    def test_png_firma_y_dimensiones(self):
        size = 24
        png = marca.encode_png(size, marca.render(size))
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        (w, h, bit, color) = struct.unpack(">IIBB", png[16:26])
        self.assertEqual((w, h, bit, color), (size, size, 8, 6))  # 6 = RGBA

    def test_ico_apunta_al_png_y_lo_embebe(self):
        png = marca.encode_png(256, b"\x00" * (256 * 256 * 4))
        ico = marca.wrap_ico(png, 256)
        reservado, tipo, n = struct.unpack("<HHH", ico[:6])
        self.assertEqual((reservado, tipo, n), (0, 1, 1))
        w, h = ico[6], ico[7]
        self.assertEqual((w, h), (0, 0))  # 0 == 256 en el formato ICO
        (bits,) = struct.unpack("<H", ico[12:14])
        (largo, offset) = struct.unpack("<II", ico[14:22])
        self.assertEqual(bits, 32)
        self.assertEqual(offset, 22)
        self.assertEqual(largo, len(png))
        self.assertEqual(ico[offset:], png)


class TestDibujo(unittest.TestCase):
    def test_la_marca_es_un_anillo_no_un_cuadrado(self):
        size = 64
        rgba = marca.render(size)
        c = size // 2

        def px(x, y):
            o = (y * size + x) * 4
            return rgba[o], rgba[o + 1], rgba[o + 2], rgba[o + 3]

        # Corazón: un punto caliente y claro en el centro exacto.
        centro = px(c, c)
        self.assertGreater(centro[2], 150, "el núcleo debería ser un punto claro")
        # Campo medio (entre el núcleo y el anillo): más oscuro que el anillo,
        # que es lo que hace que la banda cian se lea como anillo y no como disco.
        medio = px(c, c - int(0.18 * (size / 2)))
        # El anillo, a 0,34 del semirradio: azul-verdoso dominante y brillante.
        r = int(0.34 * (size / 2))
        anillo = px(c, c - r)
        self.assertGreater(anillo[2], 180, "el anillo cian no brilla")
        self.assertGreater(anillo[2], anillo[0], "el anillo debería ser cian, no rojo")
        self.assertLess(medio[2], anillo[2], "el campo medio debería quedar tras el anillo")
        # Y todo opaco, esquina incluida.
        self.assertEqual(px(0, 0)[3], 255)

    def test_alpha_opaco_en_toda_la_imagen(self):
        size = 16
        rgba = marca.render(size)
        canales_alfa = rgba[3::4]
        self.assertEqual(set(canales_alfa), {255})


if __name__ == "__main__":
    unittest.main()
