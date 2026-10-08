"""Pruebas del lanzador de doble clic (scripts/cort.py).

Se importa por ruta, no como paquete: el lanzador vive en `scripts/`, fuera del
paquete `cort_core`, y no piensa instalar nada para poder ejecutarse.
"""
import importlib
import importlib.util
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

LAUNCHER = Path(__file__).resolve().parents[3] / "scripts" / "cort.py"


def load():
    spec = importlib.util.spec_from_file_location("cort_launcher", LAUNCHER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestColores(unittest.TestCase):
    """Lo que se rompió la primera vez que se redirigió la salida a un archivo."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_sin_color_queda_el_texto_sin_los_escapes(self):
        line = self.m.bar("core", True, False, "ws://127.0.0.1:8765/ws")
        self.assertNotIn("\033", line)
        self.assertIn("core", line)
        self.assertIn("8765", line)

    def test_con_color_los_escapes_estan(self):
        self.assertIn("\033[", self.m.bar("core", True, True, "nota"))

    def test_el_banner_se_ve_sin_color(self):
        banner = self.m.banner(False)
        self.assertNotIn("\033", banner)
        self.assertTrue(any(ch in banner for ch in "█╔╗╚╝║═"), "el banner se quedó sin arte")

    def test_desvestir_un_texto_deja_el_texto(self):
        # El fallo original: `paint` devolvía "" sin color y las cuatro barras
        # desaparecían del log. Los códigos sueltos sí deben desaparecer.
        self.assertEqual(self.m.paint("\033[1m", False), "")
        self.assertEqual(self.m.paint("hola", False), "hola")
        self.assertEqual(self.m.paint("\033[1mHola\033[0m", False), "Hola")
        self.assertEqual(self.m.paint("\033[1mHola\033[0m", True), "\033[1mHola\033[0m")

    def test_sin_nota_no_pinta_un_escape_huerfano(self):
        # Con nota vacía se colaba `\033[2m\033[0m`: dos códigos para nada.
        self.assertNotIn("\033[2m", self.m.bar("memoria", True, True))
        self.assertIn("\033[2m", self.m.bar("memoria", True, True, "3 recuerdos"))


class TestDecisiones(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_auto_elige_dist_cuando_esta_construido(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "dist" / "index.html"
            with mock.patch.object(self.m, "WEB", Path(tmp)):
                self.assertEqual(self.m.pick_web_mode("auto"), "dev")
                index.parent.mkdir()
                index.write_text("<html></html>")
                self.assertEqual(self.m.pick_web_mode("auto"), "dist")

    def test_dist_y_dev_mandan_sobre_auto(self):
        self.assertEqual(self.m.pick_web_mode("dist"), "dist")
        self.assertEqual(self.m.pick_web_mode("dev"), "dev")

    def test_en_windows_npm_es_un_cmd(self):
        with mock.patch.object(os, "name", "nt"):
            self.assertEqual(self.m.npm_command("run", "dev"), ["cmd", "/c", "npm", "run", "dev"])
        with mock.patch.object(os, "name", "posix"):
            self.assertEqual(self.m.npm_command("run", "dev"), ["npm", "run", "dev"])

    def test_un_puerto_cerrado_no_es_un_puerto_abierto(self):
        self.assertFalse(self.m.port_open("127.0.0.1", 1, timeout=0.05))


class TestMemoria(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_sin_base_no_hay_recuerdo_que_contar(self):
        self.assertIsNone(self.m.memory_count(Path(tempfile.gettempdir()) / "no-existe-42.db"))

    def test_cuenta_los_recuerdos(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "memory.db"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE memories (id INTEGER PRIMARY KEY, text TEXT)")
            conn.executemany("INSERT INTO memories (text) VALUES (?)", [("a",), ("b",)])
            conn.commit()
            conn.close()
            self.assertEqual(self.m.memory_count(db), 2)

    def test_no_escribe_ni_rota_la_base_al_contar(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "memory.db"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE memories (id INTEGER PRIMARY KEY, text TEXT)")
            conn.commit()
            conn.close()
            before = db.stat().st_mtime_ns
            self.m.memory_count(db)
            self.assertEqual(db.stat().st_mtime_ns, before)

    def test_una_tabla_que_no_existe_devuelve_none_en_lugar_de_reventar(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "otra.db"
            sqlite3.connect(db).close()
            self.assertIsNone(self.m.memory_count(db))


class TestBarraDeMemoria(unittest.TestCase):
    """Las tres situaciones que puede haber al encender, dichas de tres maneras."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_primera_vez_no_es_una_avaria(self):
        ok, note = self.m.memory_note(Path(tempfile.gettempdir()) / "sin-crear-9.db", None)
        self.assertTrue(ok, "un estreno no se marca en rojo")
        self.assertIn("se crea al primero", note)

    def test_base_leyendose_muestra_la_cuenta(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "memory.db"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE memories (id INTEGER PRIMARY KEY, text TEXT)")
            conn.execute("INSERT INTO memories (text) VALUES ('x')")
            conn.commit()
            conn.close()
            ok, note = self.m.memory_note(db, self.m.memory_count(db))
            self.assertTrue(ok)
            self.assertIn("1 recuerdos", note)

    def test_base_que_existe_y_no_se_lee_si_es_roja(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "rota.db"
            db.write_bytes(b"esto no es una base sqlite")
            ok, note = self.m.memory_note(db, self.m.memory_count(db))
            self.assertFalse(ok, "aquí sí hay que avisar en rojo")
            self.assertIn("no se puede leer", note)

    def test_la_demo_se_anota_en_la_barra(self):
        ok, note = self.m.memory_note(Path(tempfile.gettempdir()) / "sin-crear-9.db", None, True)
        self.assertTrue(ok)
        self.assertIn("(demo)", note)


class TestDemoNoTocaLaBaseReal(unittest.TestCase):
    """`--demo` existe para que una captura no escriba en la memoria de Sandra."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_demo_usa_el_directorio_temporal_y_no_el_del_proyecto(self):
        path = Path(self.m.demo_db_path({"TMPDIR": "/algún/temp"}))
        self.assertEqual(path.name, "cort-demo.db")
        self.assertEqual(path.parent, Path("/algún/temp"))
        self.assertNotIn(str(self.m.DATA), str(path))

    def test_sin_TMPDIR_elige_tmp(self):
        self.assertEqual(self.m.demo_db_path({}), "/tmp/cort-demo.db")

    def test_en_demo_el_store_escribe_donde_dice_el_lanzador(self):
        # Une las dos mitades: la ruta que inventa `--demo` es la que obedece el
        # core, así que una captura no puede escribir en data/memory.db.
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        with tempfile.TemporaryDirectory() as tmp:
            route = self.m.demo_db_path({"TMPDIR": tmp})
            with mock.patch.dict(os.environ, {"CORT_MEMORY_DB": route}):
                from cort_core.memory import store as store_module

                importlib.reload(store_module)
                self.assertEqual(str(store_module.DB_PATH), route)
                store_module.MemoryStore(store_module.DB_PATH).close()


if __name__ == "__main__":
    unittest.main()
