"""Pruebas de `scripts/nota_release.py` — el recorte de la nota por etiqueta.

Es la herramienta que usa el pipeline de Release: si recorta mal, la página de
GitHub sale con la nota de otra versión o con la mitad de la siguiente pegada.
Se prueba la función pura sobre texto de mentira (rápido y sin depender del
documento real) y luego el cable completo contra `docs/RELEASE-NOTES.md` de
verdad, que es donde vive el error tonto: una raya mal contada.
"""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "nota_release.py"

_espec = importlib.util.spec_from_file_location("nota_release", SCRIPT)
nota_release = importlib.util.module_from_spec(_espec)
_espec.loader.exec_module(nota_release)

DOC = """# Notas de las Release

Cabecera que no es sección.

---

## `v0.9.0` — CORT ya hace más de una cosa por mensaje

Párrafo primero de la 0.9.

- **un bullets** con su medida.

**Zip**: `https://github.com/x/y/archive/refs/tags/v0.9.0.zip`

---

## `v0.8.0` — lo que se rechaza queda escrito

Párrafo primero de la 0.8.

---
"""


class TestRecorte(unittest.TestCase):
    def test_titulo_sin_la_etiqueta_delantera(self):
        titulo, _ = nota_release.buscar_seccion(DOC, "v0.9.0")
        self.assertEqual("CORT ya hace más de una cosa por mensaje", titulo)

    def test_el_cuerpo_para_en_la_siguiente_seccion(self):
        _, cuerpo = nota_release.buscar_seccion(DOC, "v0.9.0")
        self.assertIn("Párrafo primero de la 0.9", cuerpo)
        self.assertIn("un bullets", cuerpo)
        self.assertNotIn("lo que se rechaza queda escrito", cuerpo)
        self.assertNotIn("Párrafo primero de la 0.8", cuerpo)

    def test_la_raya_de_separacion_no_entra_en_la_nota(self):
        _, cuerpo = nota_release.buscar_seccion(DOC, "v0.9.0")
        self.assertNotIn("---", cuerpo)
        self.assertEqual(cuerpo, cuerpo.strip())

    def test_etiqueta_que_no_esta_devuelve_nada(self):
        self.assertIsNone(nota_release.buscar_seccion(DOC, "v0.7.0"))

    def test_no_confunde_v09_con_v090(self):
        # `v0.9` es prefijo de `v0.9.0`: sin la tilde de cierre del acento grave
        # la búsqueda por `startswith` se quedaría con la sección equivocada.
        self.assertIsNone(nota_release.buscar_seccion(DOC, "v0.9"))


class TestLista(unittest.TestCase):
    """El manifiesto que lee el pipeline al empujar `main`: qué etiquetas tienen
    nota escrita, en el orden del documento."""

    def test_dan_las_etiquetas_con_seccion_en_orden(self):
        self.assertEqual(["v0.9.0", "v0.8.0"], nota_release.listar_etiquetas(DOC))

    def test_ignora_lo_que_no_es_una_seccion(self):
        sucio = "# Notas\n\n## `v1.0.0\n\n## otra cosa — sin acentos\n\n" + DOC
        self.assertEqual(["v0.9.0", "v0.8.0"], nota_release.listar_etiquetas(sucio))

    def test_un_documento_sin_secciones_da_lista_vacia(self):
        self.assertEqual([], nota_release.listar_etiquetas("# solo párrafos\n"))


class TestCableReal(unittest.TestCase):
    """La herramienta contra el documento de verdad, sin escribir en el repo."""

    def test_cada_etiqueta_del_documento_tiene_su_nota(self):
        texto = nota_release.NOTAS.read_text(encoding="utf-8")
        etiquetas = nota_release.listar_etiquetas(texto)
        self.assertGreaterEqual(len(etiquetas), 4, "el documento de notas se quedó corto")
        for etiqueta in etiquetas:
            encontrada = nota_release.buscar_seccion(texto, etiqueta)
            self.assertIsNotNone(encontrada, etiqueta)
            titulo, cuerpo = encontrada
            self.assertTrue(titulo, f"{etiqueta} sin título")
            self.assertGreater(len(cuerpo), 200, f"{etiqueta} con nota recortada")
            self.assertIn("Zip", cuerpo, f"{etiqueta} sin su línea de ZIP")

    def test_listar_devuelve_cero_y_saca_cada_etiqueta(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(0, nota_release.main(["nota_release.py", "--list"]))
        self.assertEqual(nota_release.listar_etiquetas(
            nota_release.NOTAS.read_text(encoding="utf-8")),
            buf.getvalue().split())

    def test_salida_del_script_y_codigo_al_no_estar(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            cuerpo = Path(tmp) / "cuerpo.md"
            titulo = Path(tmp) / "titulo.txt"
            self.assertEqual(0, nota_release.main(
                ["nota_release.py", "v0.7.0", str(cuerpo), str(titulo)]))
            self.assertTrue(titulo.read_text(encoding="utf-8").strip())
            self.assertIn("Zip", cuerpo.read_text(encoding="utf-8"))
            self.assertEqual(2, nota_release.main(
                ["nota_release.py", "v99.0.0", str(cuerpo), str(titulo)]))


if __name__ == "__main__":
    unittest.main()
