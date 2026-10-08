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


AUDIO_STATUS = """
Audio
 ├─ Devices:
 │      49. Audio Interno                       [alsa]
 │
 ├─ Sinks:
 │  *   35. Dummy Output                        [vol: 1.00]
 │
 ├─ Sources:
 │
 ├─ Filters:
 │
 └─ Streams:

Video
 ├─ Devices:
 │      58. USB 2.0 Camera                      [v4l2]
 │
 ├─ Sinks:
 │
 ├─ Sources:
 │  *   60. USB 2.0 Camera (V4L2)
 │      63. Built-in Front Camera
 │
 └─ Streams:
"""


class TestBarraDeAudio(unittest.TestCase):
    """La quinta barra: lo que `wpctl status` dice de verdad en esta máquina.

    El fixture es la salida medida aquí (1.8 GiB, sin altavoz ni micro), recortada
    a las secciones `Audio` y `Video`. La cabecera de `wpctl` y su apartado
    `Clients:` van fuera a propósito: imprimen `usuario@maquina` y un test no es
    el sitio para publicar el nombre de nadie.
    """

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_lo_que_mide_el_analisis_son_los_sinks_y_sources_de_audio(self):
        sinks, sources = self.m.parse_wpctl(AUDIO_STATUS)
        self.assertEqual(sinks, ["Dummy Output"])
        self.assertEqual(sources, [])

    def test_las_camaras_no_cuentan_como_microfono(self):
        # El tropiezo real: `Video → Sources` tiene dos cámaras. Un análisis que
        # lea el texto entero diría «2 entrada(s)» y mentiría sobre el micrófono.
        sinks, sources = self.m.parse_wpctl(AUDIO_STATUS)
        self.assertFalse([s for s in sources + sinks if "Camera" in s])

    def test_un_texto_sin_seccion_de_audio_no_inventa_dispositivos(self):
        self.assertEqual(self.m.parse_wpctl("PipeWire 1.4.5\n └─ Clients:\n"), ([], []))

    def test_lo_que_hay_delante_de_audio_no_se_confunde_con_sinks(self):
        con_clientes = (
            "PipeWire 'pipewire-0' [1.4.5, usuario@maquina, cookie:1]\n"
            " └─ Clients:\n"
            "        33. pipewire            [1.4.5, usuario@maquina, pid:2906]\n"
            "        34. xfce4-plugin        [1.4.5, usuario@maquina, pid:2663]\n"
            + AUDIO_STATUS
        )
        sinks, sources = self.m.parse_wpctl(con_clientes)
        self.assertEqual(sinks, ["Dummy Output"])
        self.assertEqual(sources, [])

    def test_dummy_output_no_es_un_altavoz(self):
        ok, note = self.m.audio_note(["Dummy Output"], [])
        self.assertFalse(ok, "aquí es donde la barra tiene que salir en rojo")
        self.assertIn("ninguna real", note)
        self.assertIn("sin esto no hay voz", note)

    def test_altavoz_y_micro_a_la_vez_si_ponen_la_barra_en_verde(self):
        ok, note = self.m.audio_note(["Audio Interno HDA"], ["Auriculares USB"])
        self.assertTrue(ok)
        self.assertIn("Audio Interno HDA", note)
        self.assertNotIn("sin esto no hay voz", note)

    def test_altavoz_sin_micro_tampoco_es_voz(self):
        # Falta la mitad de la escucha: `ok` es `reales and sources`, no sólo
        # que haya a dónde hablar.
        ok, _ = self.m.audio_note(["Audio Interno HDA"], [])
        self.assertFalse(ok)

    def test_sin_wpctl_la_barra_se_calla_en_lugar_de_mentir(self):
        with mock.patch.object(self.m.shutil, "which", return_value=None):
            self.assertIsNone(self.m.audio_probe())

    def test_wpctl_que_falla_no_rompe_el_arranque(self):
        with mock.patch.object(self.m.shutil, "which", return_value="/usr/bin/wpctl"), \
             mock.patch.object(self.m.subprocess, "run",
                               side_effect=OSError("sin demonio de sonido")):
            self.assertIsNone(self.m.audio_probe())


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


class TestRed(unittest.TestCase):
    """`--lan`: la única bandera que abre CORT a otro aparato.

    Se prueba sobre todo lo contrario: que **sin** la bandera nada se publica.
    Un valor por defecto equivocado aquí sería dejar el core —sin contraseña ni
    TLS— escuchando en todas las interfases de la máquina.
    """

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_serve_static_sin_host_escucha_solo_en_loopback(self):
        srv = self.m.serve_static(Path("."), 0)
        try:
            self.assertEqual(srv.server_address[0], "127.0.0.1")
        finally:
            srv.shutdown()

    def test_serve_static_con_host_se_publica(self):
        srv = self.m.serve_static(Path("."), 0, "0.0.0.0")
        try:
            self.assertEqual(srv.server_address[0], "0.0.0.0")
        finally:
            srv.shutdown()

    def test_la_ip_de_red_es_una_v4_o_nada(self):
        # En una máquina sin red la sonda devuelve None, y la barra se pinta en
        # rojo en vez de imprimir una dirección inventada que no abre.
        ip = self.m.lan_address()
        if ip is not None:
            parts = ip.split(".")
            self.assertEqual(len(parts), 4)
            self.assertTrue(all(p.isdigit() and 0 <= int(p) <= 255 for p in parts), ip)

    def test_sonda_de_red_que_explota_no_tumba_el_arranque(self):
        class Boom:
            def connect(self, *_):
                raise OSError("sin ruteo")
            def close(self):
                pass

        with mock.patch.object(self.m.socket, "socket", return_value=Boom()):
            self.assertIsNone(self.m.lan_address())


if __name__ == "__main__":
    unittest.main()
