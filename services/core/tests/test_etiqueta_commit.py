"""Pruebas de `scripts/etiqueta_del_commit.py` — la etiqueta de *este* commit.

Es el resolutor que usa `compilar-apk.yml` para escribir la versión dentro del
APK cuando el run vino por rama. Se prueba la función pura con el JSON tal cual
lo devuelve `api.github.com/repos/…/tags`, sin red y sin runner: el fallo que
cubrió es exacto y medido (el `CORT-v0.14.1.apk` salió con `versionName «main»`
porque el workflow leyó `GITHUB_REF_NAME` en vez de mirar los tags).
"""
import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "etiqueta_del_commit.py"

_espec = importlib.util.spec_from_file_location("etiqueta_del_commit", SCRIPT)
etiqueta_del_commit = importlib.util.module_from_spec(_espec)
_espec.loader.exec_module(etiqueta_del_commit)

SHA_141 = "26e80027bb1a4a0f4b3f2f42b1cf0d9e4b000141"
SHA_140 = "9e671568ae30873dff55454162520f03bfa724b5"

RESPUESTA = json.dumps([
    {"name": "v0.14.1", "commit": {"sha": SHA_141}},
    {"name": "v0.14.0", "commit": {"sha": SHA_140}},
    {"name": "v0.13.1", "commit": {"sha": "a7213c01111111111111111111111111111111aa"}},
])


class TestResolutor(unittest.TestCase):
    def test_coincidencia_completa(self):
        self.assertEqual("v0.14.1", etiqueta_del_commit.desde_json(RESPUESTA, SHA_141))
        self.assertEqual("v0.14.0", etiqueta_del_commit.desde_json(RESPUESTA, SHA_140))

    def test_acepta_el_prefijo_corto_del_run(self):
        """El YAML escribe `${GITHUB_SHA:0:7}` por legibilidad: 7 hex bastan."""
        self.assertEqual("v0.14.1", etiqueta_del_commit.desde_json(RESPUESTA, SHA_141[:7]))

    def test_acepta_el_sha_mayusculas(self):
        self.assertEqual("v0.14.0", etiqueta_del_commit.desde_json(RESPUESTA, SHA_140.upper()))

    def test_vacio_cuando_ninguna_apunta_a_ese_commit(self):
        respuesta = json.dumps([{"name": "v0.13.1", "commit": {"sha": "a7213c0" + "0" * 33}}])
        self.assertEqual("", etiqueta_del_commit.desde_json(respuesta, SHA_141))

    def test_prefijo_demasiado_corto_no_vale(self):
        """Con tres letras casaría media docena de commits: es inventarse una etiqueta."""
        self.assertEqual("", etiqueta_del_commit.desde_json(RESPUESTA, "26e"))
        self.assertEqual("", etiqueta_del_commit.desde_json(RESPUESTA, ""))
        self.assertEqual("", etiqueta_del_commit.desde_json(RESPUESTA, None))

    def test_devuelve_la_primera_si_hay_dos_sobre_el_mismo_commit(self):
        dos = json.dumps([
            {"name": "v0.15.0", "commit": {"sha": SHA_141}},
            {"name": "v0.14.1", "commit": {"sha": SHA_141}},
        ])
        self.assertEqual("v0.15.0", etiqueta_del_commit.desde_json(dos, SHA_141))

    def test_no_rompe_con_formas_raras(self):
        """El paso no puede morir por un JSON raro: sin redada, sin etiqueta."""
        for basura in ("", "no es json", "{}", "[]", "null",
                      json.dumps([{}]),
                      json.dumps([{"name": "v1.0.0"}]),
                      json.dumps([{"name": "v1.0.0", "commit": None}]),
                      json.dumps([{"commit": {"sha": SHA_141}}]),
                      json.dumps(["v0.14.1"])):
            with self.subTest(texto=basura[:24]):
                self.assertEqual("", etiqueta_del_commit.desde_json(basura, SHA_141))

    def test_etiqueta_sin_nombre_no_se_inventa(self):
        rara = json.dumps([{"name": None, "commit": {"sha": SHA_141}}])
        self.assertEqual("", etiqueta_del_commit.desde_json(rara, SHA_141))


class TestCable(unittest.TestCase):
    def test_main_imprime_la_etiqueta_y_sale_cero(self):
        buf = io.StringIO()
        original = sys.stdin
        sys.stdin = io.StringIO(RESPUESTA)
        try:
            with redirect_stdout(buf):
                self.assertEqual(0, etiqueta_del_commit.main(["x", SHA_141]))
        finally:
            sys.stdin = original
        self.assertEqual("v0.14.1\n", buf.getvalue())

    def test_main_sin_coincidencia_no_imprime_nada(self):
        buf = io.StringIO()
        original = sys.stdin
        sys.stdin = io.StringIO(json.dumps(
            [{"name": "v0.9.9", "commit": {"sha": "1111111111111111111111111111111111111111"}}]))
        try:
            with redirect_stdout(buf):
                self.assertEqual(0, etiqueta_del_commit.main(["x", SHA_141]))
        finally:
            sys.stdin = original
        self.assertEqual("", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
