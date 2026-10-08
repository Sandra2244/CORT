"""Pruebas del cargador de `.env` (`cort_core/env.py`).

Se prueban las tres promesas del módulo: la variable exportada manda, lo que no
casa se ignora sin reventar, y **en las pruebas no se lee el archivo de nadie**.
"""
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from cort_core.env import ROOT, load_env, parse


class TestParse(unittest.TestCase):
    def test_clave_valor(self):
        self.assertEqual(parse("CORT_PORT=8899"), {"CORT_PORT": "8899"})

    def test_comentarios_y_lineas_vacias_no_son_configuracion(self):
        text = "# esto es un comentario\n\n   \nCORT_CITY_TEMP_C=19\n"
        self.assertEqual(parse(text), {"CORT_CITY_TEMP_C": "19"})

    def test_export_es_costumbre_de_shell_no_parte_de_la_clave(self):
        self.assertEqual(parse("export CORT_LLM_CHAIN=qwen3:0.6b"),
                         {"CORT_LLM_CHAIN": "qwen3:0.6b"})

    def test_comillas(self):
        self.assertEqual(parse('A="con espacios"'), {"A": "con espacios"})
        self.assertEqual(parse("B='otra'"), {"B": "otra"})

    def test_comentario_detras_de_un_valor_sin_comillas(self):
        self.assertEqual(parse("CORT_SHOTS_DIR=/tmp/shots # donde caen"),
                         {"CORT_SHOTS_DIR": "/tmp/shots"})

    def test_valor_vacio_es_un_valor(self):
        self.assertEqual(parse("CORT_CITY="), {"CORT_CITY": ""})

    def test_lo_que_no_casa_se_ignora_en_silencio(self):
        # Un archivo de configuración no es un programa: reventar el arranque por
        # una línea mal escrita es un fallo de diseñadora, no de usuaria.
        self.assertEqual(parse("esto no es una variable\n=2\n9CORT_X=1\nOK=1"),
                         {"OK": "1"})

    def test_la_ultima_aparicion_manda(self):
        self.assertEqual(parse("A=1\nA=2"), {"A": "2"})


class TestLoad(unittest.TestCase):
    def test_una_variable_ya_exportada_gana(self):
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / ".env"
            file.write_text("CORT_PORT=8899\n", encoding="utf-8")
            env = {"CORT_PORT": "7000"}
            self.assertEqual(load_env(file, env), [])
            self.assertEqual(env["CORT_PORT"], "7000")

    def test_lo_que_no_esta_en_el_entorno_entra_y_se_reporta_por_nombre(self):
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / ".env"
            file.write_text("CORT_LLM_CHAIN=qwen2.5:0.5b\n", encoding="utf-8")
            env = {}
            self.assertEqual(load_env(file, env), ["CORT_LLM_CHAIN"])
            self.assertEqual(env["CORT_LLM_CHAIN"], "qwen2.5:0.5b")

    def test_sin_archivo_no_hay_drama(self):
        env = {}
        self.assertEqual(load_env(Path("/no/existe/.env"), env), [])
        self.assertEqual(env, {})

    def test_CORT_DOTENV_0_no_toca_nada(self):
        # Es lo que hace `make test`. Sin esto, un `.env` con una `CORT_MEMORY_DB`
        # personal desviaría la suite a la base de datos real de quien programa.
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / ".env"
            file.write_text("CORT_MEMORY_DB=/otra/base.db\n", encoding="utf-8")
            env = {"CORT_DOTENV": "0"}
            self.assertEqual(load_env(file, env), [])
            self.assertNotIn("CORT_MEMORY_DB", env)

    def test_el_apagado_se_lee_del_entorno_actual(self):
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / ".env"
            file.write_text("CORT_PORT=1\n", encoding="utf-8")
            original = os.environ.get("CORT_DOTENV")
            os.environ["CORT_DOTENV"] = "0"
            try:
                self.assertEqual(load_env(file), [])
            finally:
                if original is None:
                    del os.environ["CORT_DOTENV"]
                else:
                    os.environ["CORT_DOTENV"] = original

    def test_el_archivo_que_busca_por_defecto_es_el_de_la_raiz(self):
        # Sin argumentos el cargador apunta a ROOT/.env; si ROOT no fuera la raíz
        # del repo, el lanzador y el core buscarían en sitios distintos.
        self.assertEqual(ROOT.name, "CORT")
        self.assertTrue((ROOT / "Makefile").is_file(), f"ROOT apunta a {ROOT}")


if __name__ == "__main__":
    unittest.main()
