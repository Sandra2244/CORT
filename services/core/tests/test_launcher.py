"""Pruebas del lanzador de doble clic (scripts/cort.py).

Se importa por ruta, no como paquete: el lanzador vive en `scripts/`, fuera del
paquete `cort_core`, y no piensa instalar nada para poder ejecutarse.
"""
import importlib
import importlib.util
import os
import sqlite3
import sys
import socket
import tempfile
import threading
import time
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

    def test_lan_sin_token_se_niega(self):
        """Última barrera: sin secreto no se abre el puerto, porque por ese cable
        se cambia el volumen, se abren apps y se captura la pantalla. Desde
        `v0.14.0` casi nadie llega aquí — la llave se crea sola antes —, pero la
        decisión de seguridad sigue siendo la misma."""
        motivo = self.m.rechazo_de_red(True, "")
        self.assertIsNotNone(motivo)
        self.assertIn("CORT_LAN_TOKEN", motivo)

    def test_lan_con_token_se_puede(self):
        self.assertIsNone(self.m.rechazo_de_red(True, "un-secreto"))

    def test_un_token_de_solo_espacios_no_es_un_secreto(self):
        self.assertIsNotNone(self.m.rechazo_de_red(True, "   "))

    def test_sin_lan_no_se_pide_nada(self):
        """En `127.0.0.1` no hay a quién autorizar: exigir token ahí sería un
        paso de más para la dueña del portátil, y rompería el doble clic."""
        self.assertIsNone(self.m.rechazo_de_red(False, ""))


class TestLlaveQueSeCreaSola(unittest.TestCase):
    """`--lan` ya no es un muro: la llave que falta se crea y se guarda sola.

    Lo que se prueba aquí es el cambio de contrato que pidió la dueña del
    proyecto (2026-10-15): el arranque no puede pedirle a nadie que edite un
    `.env` a mano para que su teléfono funcione. La protección NO se tocó —la
    sigue aplicando `cort_core/security.py` en cada conexión—; lo que se quitó
    fue el tecleo, y con él la pantalla roja.
    """

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env_file = Path(self.tmp.name) / ".env"

    def test_sin_llave_se_crea_y_se_escribe_en_el_env(self):
        env: dict[str, str] = {}
        token, motivo, creada = self.m.llave_de_red(True, self.env_file, env)
        self.assertIsNone(motivo)
        self.assertTrue(creada)
        self.assertGreaterEqual(len(token), 20, "una llave corta es un secreto débil")
        self.assertIn(f"CORT_LAN_TOKEN={token}", self.env_file.read_text())
        self.assertEqual(env["CORT_LAN_TOKEN"], token, "el core tiene que recibirla")
        # Y con la llave ya en la mano, la última barrera se aparta sola.
        self.assertIsNone(self.m.rechazo_de_red(True, token))

    def test_el_archivo_queda_con_permiso_de_secreto(self):
        # `.env` lleva la llave de red: 0600 para que no la lea otro usuario de
        # la máquina. Sin esto, un portátil compartido filtraría el acceso.
        self.m.llave_de_red(True, self.env_file, {})
        self.assertEqual(self.env_file.stat().st_mode & 0o777, 0o600)

    def test_segunda_vez_no_duplica_ni_cambia_la_llave(self):
        first, _, _ = self.m.llave_de_red(True, self.env_file, {})
        env = {"CORT_LAN_TOKEN": first}
        again, motivo, creada = self.m.llave_de_red(True, self.env_file, env)
        self.assertEqual(again, first)
        self.assertFalse(creada, "una llave guardada no se regenera: el teléfono perdería el enlace")
        text = self.env_file.read_text()
        self.assertEqual(text.count("CORT_LAN_TOKEN="), 1)

    def test_un_env_que_no_termina_en_salto_no_se_pega(self):
        # El fallo clásico de escribir a pelo: `CORT_PORT=8765` sin `\n` final y
        # la llave quedando `8765CORT_LAN_TOKEN=…`, que no parsea nadie.
        self.env_file.write_text("CORT_PORT=8765")
        token, motivo, _ = self.m.llave_de_red(True, self.env_file, {})
        self.assertIsNone(motivo)
        lineas = self.env_file.read_text().splitlines()
        self.assertEqual(lineas[0], "CORT_PORT=8765")
        self.assertIn(f"CORT_LAN_TOKEN={token}", lineas)

    def test_sin_lan_el_env_ni_se_toca(self):
        self.env_file.write_text("CORT_PORT=8765\n")
        token, motivo, creada = self.m.llave_de_red(False, self.env_file, {})
        self.assertEqual((token, motivo, creada), ("", None, False))
        self.assertEqual(self.env_file.read_text(), "CORT_PORT=8765\n")

    def test_solo_lectura_devuelve_motivo_en_lugar_de_reventar(self):
        if hasattr(self.m.os, "geteuid") and self.m.os.geteuid() == 0:
            self.skipTest("como root el chmod 400 no niega la escritura")
        self.env_file.write_text("A=1\n")
        self.env_file.chmod(0o400)
        token, motivo, creada = self.m.llave_de_red(True, self.env_file, {})
        self.assertEqual(token, "")
        self.assertFalse(creada)
        self.assertIsNotNone(motivo, "sin disco de escritura hay que negarse, no abrir sin llave")
        self.assertIn("no se pudo escribir", motivo)

    def test_CORT_LAN_en_el_entorno_enciende_la_red_sin_bandera(self):
        # El doble clic del escritorio no lleva banderas: `CORT_LAN=1` en el
        # `.env` tiene que valer lo mismo que escribir `--lan`.
        for valor in ("1", "true", "si", "sí", "on", "YES"):
            self.assertTrue(self.m.verdad(valor), valor)
        for valor in ("", "0", "no", "off", "nunca"):
            self.assertFalse(self.m.verdad(valor), valor)


class TestBarraDeCamara(unittest.TestCase):
    """La sonda de vídeo: qué se ve, y si esta usuaria puede abrirlo."""

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_sin_dispositivos_es_sonda_incompleta_no_camara_rota(self):
        # En Windows y macOS no existe `/dev/video*`. La barra lo dice como lo que
        # es — que aquí falta esa sonda — y no como un fallo de hardware.
        ok, texto = self.m.camera_note([])
        self.assertFalse(ok)
        self.assertIn("Windows", texto)

    def test_camara_presente_y_accesible(self):
        ok, texto = self.m.camera_note([("video0", True)])
        self.assertTrue(ok)
        self.assertIn("1 cámara(s): video0", texto)
        # Que la abra el navegador va en la propia barra: sin ese aviso, quien lea
        # «ok» irá a buscar el permiso al core, que no tiene ninguno que dar.
        self.assertIn("navegador", texto)

    def test_camara_sin_permiso_no_cuenta_como_camara(self):
        ok, texto = self.m.camera_note([("video0", False)])
        self.assertFalse(ok)
        self.assertIn("grupo `video`", texto, "el aviso tiene que decir qué hacer, no sólo que falla")

    def test_probe_ordena_y_comprueba_acceso(self):
        v0 = Path("/dev/video0")
        v1 = Path("/dev/video1")
        with mock.patch.object(self.m.Path, "glob", return_value=iter([v1, v0])), \
             mock.patch.object(self.m.os, "access", side_effect=[True, False]):
            self.assertEqual(self.m.camera_probe(), [("video0", True), ("video1", False)])


if __name__ == "__main__":
    unittest.main()


class TestDescubrimientoPorRed(unittest.TestCase):
    """El «¿estás ahí?» por UDP que le ahorra a la dueña pegar el enlace.

    El lazo se prueba en `127.0.0.1` con un puerto libre de verdad: el bucle es
    el mismo que escucha en la Wi-Fi de la casa, y una sonda que no recibe
    respuesta es un teléfono que se queda en la pantalla de pegar.
    """

    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def setUp(self):
        self.parada = threading.Event()
        self.hilos = []

    def tearDown(self):
        self.parada.set()
        for hilo in self.hilos:
            hilo.join(timeout=3)

    def sondear(self, puerto, datos=b"CORT-ENCONTRARSO-1"):
        cliente = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        cliente.settimeout(3)
        try:
            cliente.sendto(datos, ("127.0.0.1", puerto))
            try:
                respuesta, _ = cliente.recvfrom(512)
                return respuesta
            except socket.timeout:
                return None
        finally:
            cliente.close()

    def esperando(self, registro, hasta=2.0):
        """`bucle_descubrimiento` primero **contesta** y después apunta quién
        preguntó, así que el `recvfrom` de arriba puede volver antes de que esa
        segunda mitad ocurra. Con la suite entera corriendo en los dos núcleos de
        esta máquina se cumplió el caso: `test_una_sonda_legitima…` salió roja
        dentro de `make test` (el 2026-10-15, con 571 pruebas) y pasó tres veces
        sola — era la prueba la que iba justita de tiempo, no el producto, y así
        queda escrito en vez de rezar para que el ordenate vaya lento.

        Se espera con techo y se devuelve lo que haya: si en dos segundos no aparece
        nada, el `assertEqual` de enfrente falla con el valor real y no con una
        carrera.
        """
        limite = time.time() + hasta
        while not registro and time.time() < limite:
            time.sleep(0.02)
        return registro

    def test_el_puerto_por_defecto_es_el_que_lleva_el_apk(self):
        self.assertEqual(8781, self.m.puerto_descubrimiento({}))

    def test_un_puerto_del_env_manda(self):
        self.assertEqual(9999, self.m.puerto_descubrimiento({"CORT_DISCOVERY_PORT": "9999"}))

    def test_un_puerto_absurdo_no_detiene_el_arranque(self):
        # La divulgación es una comodidad, no un interruptor de seguridad: si el
        # valor no es un puerto, se usa el de siempre y CORT arranca igual.
        for malo in ("", "  ", "abc", "0", "70000", "-1"):
            with self.subTest(malo=malo):
                self.assertEqual(8781, self.m.puerto_descubrimiento({"CORT_DISCOVERY_PORT": malo}))

    def test_la_sonda_se_reconoce_con_nonce_detras(self):
        self.assertTrue(self.m.sonda_valida(b"CORT-ENCONTRARSO-1"))
        self.assertTrue(self.m.sonda_valida(b"CORT-ENCONTRARSO-1 8f2a"))

    def test_lo_que_no_es_de_cort_no_merece_respuesta(self):
        # El socket escucha en 0.0.0.0: caen escáneres, impresoras y routers.
        for basura in (b"", b"\n", b"ohoi", b"CORT-ENCONTRARSO-1x", b"CORT-ENCONTRARSO",
                       b"\x00\x01\x02"):
            with self.subTest(basura=basura):
                self.assertFalse(self.m.sonda_valida(basura))

    def test_sin_enlace_no_hay_nada_que_contestar(self):
        self.assertEqual(b"", self.m.respuesta_descubrimiento(""))

    def test_la_respuesta_es_el_enlace_completo_con_su_llave(self):
        dato = self.m.respuesta_descubrimiento("http://192.168.100.xxx:8780/?token=abc")
        self.assertEqual(b"CORT-AQUI-1|http://192.168.100.xxx:8780/?token=abc", dato)

    def test_una_sonda_legitima_vuelve_con_el_enlace_y_queda_apuntada(self):
        sock, motivo = self.m.abrir_descubrimiento(0)
        self.assertIsNotNone(sock, motivo)
        self.addCleanup(sock.close)
        puerto = sock.getsockname()[1]
        quien = []
        hilo = threading.Thread(target=self.m.bucle_descubrimiento,
                                args=(sock, "http://192.168.100.xxx:8780/?token=abc",
                                      self.parada, quien.append), daemon=True)
        hilo.start()
        self.hilos.append(hilo)
        self.assertEqual(b"CORT-AQUI-1|http://192.168.100.xxx:8780/?token=abc",
                         self.sondear(puerto))
        # El `print` va **detrás** de la respuesta en el lazo del lanzador: se espera.
        self.assertEqual(["127.0.0.1"], self.esperando(quien),
                         "quien pidió la llave tiene que quedar impreso")

    def test_una_sonda_basura_no_saca_respuesta(self):
        sock, motivo = self.m.abrir_descubrimiento(0)
        self.assertIsNotNone(sock, motivo)
        self.addCleanup(sock.close)
        puerto = sock.getsockname()[1]
        oidos = []
        hilo = threading.Thread(target=self.m.bucle_descubrimiento,
                                args=(sock, "http://192.168.100.xxx:8780/?token=abc",
                                      self.parada, oidos.append), daemon=True)
        hilo.start()
        self.hilos.append(hilo)
        self.assertIsNone(self.sondear(puerto, b"CORT-ENCONTRARSO-1x"))
        self.assertEqual([], oidos)

    def test_sin_enlace_no_responde_aunque_la_sonda_es_buena(self):
        sock, motivo = self.m.abrir_descubrimiento(0)
        self.assertIsNotNone(sock, motivo)
        self.addCleanup(sock.close)
        puerto = sock.getsockname()[1]
        oidos = []
        hilo = threading.Thread(target=self.m.bucle_descubrimiento,
                                args=(sock, "", self.parada, oidos.append), daemon=True)
        hilo.start()
        self.hilos.append(hilo)
        self.assertIsNone(self.sondear(puerto))
        self.assertEqual([], oidos)


