"""Pruebas del registro de intentos rechazados (`cort_core/audit.py`).

La bitscora de CORT no es un adorno: hasta hoy el core rechazaba y callaba, así
que nadie podía responder «¿*quién* lo intentó?». Esas pruebas miran las tres
cosas que este módulo no puede romper nunca:

1. **Que no se cuele el secreto.** El detalle lo escribe input de la otra parte;
   si alguien mete la llave en un nombre de archivo, la llave no acaba en el log.
2. **Que no se falsee una línea.** Un `\\n` en el detalle sería la forma clásica
   de fabricarse un registro limpio en medio de uno sucio.
3. **Que un fallo de disco no tumbe al servidor.** Registrar es secundario; si
   el disco está lleno, CORT sigue rechazando igual y no se cae.

La parte de servidor se prueba con `TestClient`, que es donde un candado se
olvida: cuatro rechazos de verdad y se lee el archivo que dejaron.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from cort_core import audit, security
from cort_core.server import app

AHORA = datetime(2026, 10, 9, 12, 30, 0, tzinfo=timezone.utc)


class TestLineaPura(unittest.TestCase):
    """`linea()` y `normaliza()` no tocan el disco: son pura forma."""

    def test_es_una_sola_linea_de_json_con_sus_campos(self):
        bruto = audit.linea("acceso-sin-llave", "192.168.1.9", "GET /avatars", AHORA)
        self.assertNotIn("\n", bruto.rstrip("\n"))
        cuadro = json.loads(bruto)
        self.assertEqual({"iso", "motivo", "origen", "detalle"}, set(cuadro))
        self.assertEqual("2026-10-09T12:30:00+00:00", cuadro["iso"])
        self.assertEqual("acceso-sin-llave", cuadro["motivo"])

    def test_el_salto_de_linea_no_fabrica_un_cuadro_nuevo(self):
        """El ataque de log clásico: meter `\n` y un JSON falso detrás."""
        bruto = audit.linea("ruta-rechazada", "1.2.3.4",
                            '../../etc/passwd\n{"iso":"x","motivo":"nada"}', AHORA)
        self.assertEqual(1, len(bruto.strip().splitlines()))
        cuadro = json.loads(bruto)
        self.assertNotIn("\n", cuadro["detalle"])
        self.assertIn("etc/passwd", cuadro["detalle"])

    def test_el_detalle_largo_se_recorta_sin_reventar(self):
        cuadro = json.loads(audit.linea("ruta-rechazada", "1.2.3.4", "A" * 5000, AHORA))
        self.assertLessEqual(len(cuadro["detalle"]), audit.DETALLE_MAX)
        self.assertTrue(cuadro["detalle"].startswith("AAAA"))

    def test_lo_inesperado_no_rompe_la_forma(self):
        for origen in (None, "", "nombredispositivo.local"):
            cuadro = json.loads(audit.linea("arranque-sin-llave", origen, "", AHORA))
            self.assertIsInstance(cuadro["origen"], str)
        # Un detalle que no es texto (un None, un número) no puede colarse: se
        # normaliza, no se serializa crudo.
        cuadro = json.loads(audit.linea("acceso-sin-llave", None, None, AHORA))
        self.assertEqual("", cuadro["detalle"])

    def test_la_forma_es_la_que_los_lectores_esperan(self):
        self.assertTrue(audit.MOTIVOS, "la lista de motivos no puede estar vacía")
        for motivo in audit.MOTIVOS:
            self.assertIsInstance(json.loads(audit.linea(motivo, "", "", AHORA)), dict)


class TestBitacora(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = pathlib.Path(self.tmp.name) / "rechazos.jsonl"
        self.parche = mock.patch.dict(os.environ, {
            "CORT_DOTENV": "0",
            "CORT_AUDIT_LOG": str(self.log),
            "CORT_LAN_TOKEN": "llave-de-prueba",
        })
        self.parche.start()
        self.addCleanup(self.parche.stop)

    def test_registrar_crea_el_directorio_y_escribe(self):
        self.assertTrue(audit.registrar("acceso-sin-llave", "192.168.1.9", "GET /ws"))
        self.assertTrue(self.log.is_file())
        self.assertEqual(1, len(self.log.read_text(encoding="utf-8").splitlines()))

    def test_un_motivo_que_no_existe_no_se_escribe(self):
        """Lista cerrada, como la de las acciones: nadie inventa categorías post
        fact, y un `motivo` que no está en la lista se rechaza sin escribir."""
        self.assertFalse(audit.registrar("todo-bien-aqui", "1.2.3.4", "ok"))
        self.assertFalse(self.log.exists())

    def test_la_llave_nunca_atermina_en_el_log(self):
        """El detalle lo escribe la otra parte: si mete el secreto en un nombre,
        lo que se guarda es la señal de que se coló, no el secreto."""
        audit.registrar("ruta-rechazada", "1.2.3.4",
                        "mira mi archivo llave-de-prueba.png")
        guardado = self.log.read_text(encoding="utf-8")
        self.assertNotIn("llave-de-prueba", guardado)
        self.assertIn("«llave»", guardado)

    def test_sin_configurar_llave_no_hay_nada_que_oscurecer(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ["CORT_AUDIT_LOG"] = str(self.log)
            audit.registrar("ruta-rechazada", "1.2.3.4", "llave-de-prueba")
        self.assertIn("llave-de-prueba", self.log.read_text(encoding="utf-8"))

    def test_recientes_da_lo_ultimo_primero_y_sin_romperse(self):
        for n in range(3):
            audit.registrar("acceso-sin-llave", f"10.0.0.{n}", f"detalle {n}")
        # Una línea escrita a mano y estropeada: el lector la ignora, no revienta.
        with self.log.open("a", encoding="utf-8") as f:
            f.write("{esto no es json}\n\n")
        audit.registrar("llave-incorrecta", "10.0.0.9", "otro intento")
        recientes = audit.recientes()
        self.assertEqual(4, len(recientes))
        self.assertEqual("llave-incorrecta", recientes[0]["motivo"])
        self.assertEqual("10.0.0.0", recientes[-1]["origen"])

    def test_recientes_respeta_el_maximo(self):
        for n in range(5):
            audit.registrar("acceso-sin-llave", "10.0.0.1", str(n))
        self.assertEqual(2, len(audit.recientes(2)))

    def test_el_archivo_no_crece_sin_freno(self):
        """Con un vecino terco el log no puede llenarle el disco a la usuaria: se
        recorta y lo que se conserva son los intentos **más nuevos**."""
        with mock.patch.object(audit, "LIMITE_BYTES", 1200):
            for n in range(60):
                audit.registrar("acceso-sin-llave", "10.0.0.1", f"intento {n}")
            self.assertLess(self.log.stat().st_size, 4000)
            lineas = self.log.read_text(encoding="utf-8").splitlines()
            self.assertLess(len(lineas), 60)
            self.assertIn("intento 59", lineas[-1])
            # Y lo que queda sigue siendo JSON válido línea por línea.
            for bruto in lineas:
                json.loads(bruto)

    def test_un_fallo_de_disco_no_tumba_nada(self):
        """El camino del log apunta a un archivo que no es un directorio: `mkdir`
        falla. Registrar tiene que devolver False y no lanzar — si lanzara desde
        el servidor, un disco lleno cerraría la puerta *incorrecta*."""
        bloque = pathlib.Path(self.tmp.name) / "bloque"
        bloque.write_text("no soy un directorio", encoding="utf-8")
        with mock.patch.dict(os.environ, {"CORT_AUDIT_LOG": str(bloque / "rechazos.jsonl")}):
            self.assertFalse(audit.registrar("acceso-sin-llave", "1.2.3.4", "GET /ws"))
        self.assertEqual("no soy un directorio", bloque.read_text(encoding="utf-8"))

    def test_sin_variable_apunta_a_data_y_no_al_repo(self):
        """El default vive en `services/core/data/`, que está en `.gitignore`:
        un registro de intentos no se sube a un repositorio público."""
        with mock.patch.dict(os.environ, {}, clear=True):
            ruta = audit.ruta_de_bitacora()
        self.assertEqual("rechazos.jsonl", ruta.name)
        self.assertEqual("data", ruta.parent.name)
        self.assertTrue(str(ruta).endswith("services/core/data/rechazos.jsonl"))


class ConRedPublicada(unittest.TestCase):
    """Cuatro rechazos reales a través del servidor, leídos después en el disco."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        raiz = pathlib.Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        (raiz / "casual.png").write_bytes(b"\x89PNG\r\n\x1a\n-fake")
        self.log = raiz / "rechazos.jsonl"
        self.parche = mock.patch.dict(os.environ, {
            "CORT_DOTENV": "0",
            "CORT_HOST": "0.0.0.0",
            "CORT_LAN_TOKEN": "llave-de-prueba",
            "CORT_AVATAR_DIR": str(raiz / "atuendos"),
            "CORT_AUDIT_LOG": str(self.log),
        })
        (raiz / "atuendos").mkdir()
        (raiz / "atuendos" / "casual.png").write_bytes(b"\x89PNG\r\n\x1a\n-fake")
        self.parche.start()
        self.addCleanup(self.parche.stop)
        self.client = TestClient(app)

    def test_el_web_socket_rechazado_deja_rastro(self):
        with self.assertRaises(Exception):
            with self.client.websocket_connect("/ws"):
                pass
        with self.assertRaises(Exception):
            with self.client.websocket_connect("/ws?token=otra"):
                pass
        recientes = audit.recientes()
        self.assertEqual(["llave-incorrecta", "acceso-sin-llave"],
                         [r["motivo"] for r in recientes])  # lo último primero
        self.assertEqual("testclient", recientes[0]["origen"])
        self.assertNotIn("llave-de-prueba", self.log.read_text(encoding="utf-8"))

    def test_el_401_deja_rastro_y_el_nombre_estropeado_tambien(self):
        self.assertEqual(401, self.client.get("/avatars/casual.png").status_code)
        # Con la llave puesta, ahora intenta sacar un archivo de fuera:
        self.assertEqual(404, self.client.get("/avatars/no-existe.png?token=llave-de-prueba").status_code)
        motivos = [r["motivo"] for r in audit.recientes()]
        self.assertEqual(["acceso-sin-llave"], motivos)

    def test_una_ruta_fuera_de_la_carpeta_se_registra_como_intento(self):
        """`../../etc/passwd` normalizado no llega a la ruta, pero **sí** deja
        constar que alguien lo pidió desde la red con la llave en la mano."""
        r = self.client.get("/avatars/notas.txt?token=llave-de-prueba")
        self.assertEqual(404, r.status_code)
        recientes = audit.recientes()
        self.assertEqual("extension-no-permitida", recientes[0]["motivo"])
        self.assertNotIn("llave-de-prueba", json.dumps(recientes))

    def test_en_local_un_rechazo_de_archivo_no_grita(self):
        """Sin `CORT_HOST` publicado no hay vecino que temer: un nombre que no
        casa es un 404 normal, no un intento registrado. Si esto escribiera, el
        log se llenaría de erratas propias."""
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.update({"CORT_DOTENV": "0",
                               "CORT_AVATAR_DIR": str(pathlib.Path(self.tmp.name) / "atuendos"),
                               "CORT_AUDIT_LOG": str(self.log)})
            os.environ.pop("CORT_HOST", None)
            c = TestClient(app)
            self.assertEqual(404, c.get("/avatars/notas.txt").status_code)
            self.assertEqual(404, c.get("/avatars/no-hay.png").status_code)
        self.assertFalse(self.log.exists())


class TestArranqueNiegaYLoApunta(unittest.TestCase):
    def test_el_arranque_negado_queda_escrito(self):
        """`python -m cort_core.server` publicado y sin llave: sale con código 1,
        lo dice en la terminal **y** deja la línea en la bitácora."""
        here = pathlib.Path(__file__).resolve().parents[1]
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        log = pathlib.Path(tmp.name) / "rechazos.jsonl"
        env = {**os.environ, "CORT_DOTENV": "0", "CORT_HOST": "0.0.0.0",
               "CORT_MEMORY_DB": str(pathlib.Path(tmp.name) / "prueba.db"),
               "CORT_AUDIT_LOG": str(log)}
        env.pop("CORT_LAN_TOKEN", None)
        r = subprocess.run([sys.executable, "-m", "cort_core.server"],
                           cwd=here, env=env, capture_output=True, text=True,
                           timeout=60)
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertIn("CORT no arranca", r.stdout)
        self.assertTrue(log.is_file(), r.stdout + r.stderr)
        linea = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual("arranque-sin-llave", linea["motivo"])


class TestLecturaPorTerminal(unittest.TestCase):
    def test_el_comando_de_lectura_imprime_lo_que_hay(self):
        """`python -m cort_core.audit` es la única forma de leer la bitácora sin
        abrir el archivo a mano: se prueba que existe, que responde y que no
        inventa cuando está vacía."""
        here = pathlib.Path(__file__).resolve().parents[1]
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        log = pathlib.Path(tmp.name) / "rechazos.jsonl"
        base = {**os.environ, "CORT_DOTENV": "0", "CORT_AUDIT_LOG": str(log)}

        vacio = subprocess.run([sys.executable, "-m", "cort_core.audit"],
                              cwd=here, env=base, capture_output=True, text=True,
                              timeout=60)
        self.assertEqual(0, vacio.returncode, vacio.stderr)
        self.assertIn("sin rechazos", vacio.stdout)

        with log.open("w", encoding="utf-8") as f:
            f.write(audit.linea("acceso-sin-llave", "192.168.100.42", "GET /ws", AHORA))
            f.write(audit.linea("ruta-rechazada", "192.168.100.42", "../../etc/passwd", AHORA))
        lleno = subprocess.run([sys.executable, "-m", "cort_core.audit"],
                              cwd=here, env=base, capture_output=True, text=True,
                              timeout=60)
        self.assertEqual(0, lleno.returncode, lleno.stderr)
        self.assertIn("192.168.100.42", lleno.stdout)
        self.assertIn("acceso-sin-llave", lleno.stdout)
        self.assertIn("2", lleno.stdout.splitlines()[0])


if __name__ == "__main__":
    unittest.main()
