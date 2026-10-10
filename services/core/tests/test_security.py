"""Pruebas de la puerta de la red (`cort_core/security.py`).

La mitad pura se prueba a pelo: direcciones, tokens y las cuatro combinaciones
de «¿estoy publicado? × ¿tengo llave?». La otra mitad se prueba contra el
servidor de verdad con `TestClient`, que es donde un candado se olvida: una ruta
protegida y una sin proteger se ven idénticas hasta que alguien las recorre.

El vecino que simula `TestClient` es `"testclient"`, que no es una dirección de
bucle invertido: así, cuando el core está publicado, estas pruebas caen
exactamente en el caso del teléfono por Wi-Fi y no en el del portátil hablándose
a sí mismo.
"""
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# **Antes** de importar el servidor: este módulo rechaza lazos y archivos a propósito,
# y desde `v0.8.0` cada rechazo se apunta en la bitácora. Sin esta línea las pruebas de
# red escribirían `testclient` y `arranque-sin-llave` **en el registro real de la
# usuaria** (`services/core/data/rechazos.jsonl`), que es justo el archivo que tiene
# que ser de fiar. `make test` pone la variable también por su cuenta; esta línea es
# para quien corre `unittest` a mano.
os.environ.setdefault("CORT_AUDIT_LOG",
                      str(pathlib.Path(tempfile.gettempdir()) / "cort-pruebas-rechazos.jsonl"))

from fastapi.testclient import TestClient

from cort_core import security
from cort_core.server import app


class TestRegistroDePruebaFueraDelReal(unittest.TestCase):
    def test_la_bitacora_que_escriben_estas_pruebas_no_es_la_de_la_usuaria(self):
        """Un registro de rechazos sólo vale si es de fiar; si las pruebas de red le
        llenan el archivo de `testclient` y `arranque-sin-llave` falsos, deja de
        serlo. Esta prueba vigila el `setdefault` de arriba."""
        from cort_core import audit
        self.assertTrue(str(audit.ruta_de_bitacora()).startswith(tempfile.gettempdir()),
                        f"la bitácora de pruebas cae en {audit.ruta_de_bitacora()}")


class TestEsLocal(unittest.TestCase):
    def test_bucle_invertido_en_todas_sus_formas(self):
        for d in ("127.0.0.1", "127.0.0.53", "127.255.9.9", "::1", "localhost",
                  "LOCALHOST", " ::1 ", "::ffff:127.0.0.1"):
            self.assertTrue(security.es_local(d), d)

    def test_lo_demas_no_es_local(self):
        for d in ("192.168.100.7", "10.0.0.1", "0.0.0.0", "8.8.8.8", "testclient",
                  "", None, "no-es-una-ip", "127.0.0.1.5"):
            self.assertFalse(security.es_local(d), d)

    def test_nada_de_empezar_por_127(self):
        # Un `startswith("127.")` aceptaría `127.ejemplo.com` y cualquier cosa
        # que empiece igual. Aquí se compara como red, y esto es la prueba.
        self.assertFalse(security.es_local("127.ejemplo.com"))


class TestToken(unittest.TestCase):
    def test_sin_variable_no_hay_token(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual("", security.token_configurado())

    def test_un_espacio_no_es_un_secreto(self):
        with mock.patch.dict(os.environ, {"CORT_LAN_TOKEN": "   "}):
            self.assertEqual("", security.token_configurado())

    def test_el_host_por_defecto_es_la_propia_maquina(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual("127.0.0.1", security.host_de_escucha())


class TestArranque(unittest.TestCase):
    def test_en_local_no_se_pide_token(self):
        self.assertIsNone(security.rechazo_de_arranque("127.0.0.1", ""))

    def test_publicado_sin_token_se_niega(self):
        motivo = security.rechazo_de_arranque("0.0.0.0", "")
        self.assertIsNotNone(motivo)
        self.assertIn("CORT_LAN_TOKEN", motivo)

    def test_publicado_con_token_se_puede(self):
        self.assertIsNone(security.rechazo_de_arranque("0.0.0.0", "s3creto"))


class TestAutorizado(unittest.TestCase):
    def test_local_entr_a_sin_preguntar(self):
        self.assertTrue(security.autorizado("127.0.0.1", "192.168.1.9", "", None))

    def test_publicado_pero_el_vecino_es_el_propio_equipo(self):
        self.assertTrue(security.autorizado("0.0.0.0", "127.0.0.1", "abc", None))

    def test_publicado_con_el_token_exacto(self):
        self.assertTrue(security.autorizado("0.0.0.0", "192.168.1.9", "abc", "abc"))

    def test_publicado_con_el_token_malo(self):
        self.assertFalse(security.autorizado("0.0.0.0", "192.168.1.9", "abc", "abd"))

    def test_publicado_sin_token_nadie_pasa(self):
        # Sin secreto no hay forma de autorizar a nadie: fallar cerrado.
        self.assertFalse(security.autorizado("0.0.0.0", "192.168.1.9", "", None))
        self.assertFalse(security.autorizado("0.0.0.0", "192.168.1.9", "", ""))

    def test_un_token_largo_no_se_acepta_recortado_por_delante(self):
        self.assertFalse(security.autorizado("0.0.0.0", "192.168.1.9", "abc", "xabc"))


class ConRedPublicada:
    """El core escuchando en `0.0.0.0` con un token puesto, y una carpeta de atuendos."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        raiz = pathlib.Path(self.tmp.name)
        (raiz / "casual.png").write_bytes(b"\x89PNG\r\n\x1a\n-fake")
        self.parche = mock.patch.dict(os.environ, {
            "CORT_HOST": "0.0.0.0",
            "CORT_LAN_TOKEN": "llave-de-prueba",
            "CORT_AVATAR_DIR": str(raiz),
            "CORT_DOTENV": "0",
        })
        self.parche.start()
        self.client = TestClient(app)
        return self

    def __exit__(self, *exc):
        self.parche.stop()
        self.tmp.cleanup()


class TestWebSocketProtegido(unittest.TestCase):
    def test_sin_token_no_hay_saludo(self):
        """El lazo se cierra **antes** de `accept()`: ni saludo, ni estado, ni tarea."""
        with ConRedPublicada() as ctx:
            with self.assertRaises(Exception) as sube:
                with ctx.client.websocket_connect("/ws"):
                    self.fail("el WebSocket debería haberse rechazado antes de abrirse")
            self.assertIn("WebSocketDisconnect", type(sube.exception).__name__)

    def test_con_el_token_incorrecto_tampoco(self):
        with ConRedPublicada() as ctx:
            with self.assertRaises(Exception):
                with ctx.client.websocket_connect("/ws?token=otra-cosa"):
                    self.fail("un token equivocado no abre la puerta")

    def test_con_el_token_correcto_los_tres_marcos_de_siempre(self):
        with ConRedPublicada() as ctx:
            with ctx.client.websocket_connect("/ws?token=llave-de-prueba") as ws:
                tipos = [ws.receive_json()["type"] for _ in range(3)]
                self.assertEqual(["state", "greeting", "status"], tipos)

    def test_en_local_no_se_pide_nada(self):
        """Sin `CORT_HOST` publicado el candado no existe: es el comportamiento
        que tiene hoy el portátil, y lo que estas pruebas no pueden romper."""
        with mock.patch.dict(os.environ, {"CORT_DOTENV": "0"}, clear=False):
            os.environ.pop("CORT_HOST", None)
            os.environ.pop("CORT_LAN_TOKEN", None)
            client = TestClient(app)
            with client.websocket_connect("/ws") as ws:
                tipos = [ws.receive_json()["type"] for _ in range(3)]
                self.assertEqual(["state", "greeting", "status"], tipos)


class TestArchivosProtegidos(unittest.TestCase):
    def test_sin_token_401(self):
        with ConRedPublicada() as ctx:
            r = ctx.client.get("/avatars/casual.png")
            self.assertEqual(401, r.status_code)
            self.assertIn("token", r.json()["detail"])

    def test_con_token_200(self):
        with ConRedPublicada() as ctx:
            r = ctx.client.get("/avatars/casual.png?token=llave-de-prueba")
            self.assertEqual(200, r.status_code)
            self.assertEqual("image/png", r.headers["content-type"])

    def test_el_token_se_mira_antes_de_tocar_el_disco(self):
        """Un nombre que no existe, pedido desde la red sin llave, responde 401 y
        no 404: con 404 estaría confirmando qué nombres son válidos, que es justo
        lo que `avatars` evita al devolver 404 en vez de 403 por una evasión."""
        with ConRedPublicada() as ctx:
            r = ctx.client.get("/avatars/no-existe.png")
            self.assertEqual(401, r.status_code)
            # Y con la llave, el mismo nombre sí es un 404 honesto.
            r2 = ctx.client.get("/avatars/no-existe.png?token=llave-de-prueba")
            self.assertEqual(404, r2.status_code)

    def test_con_token_el_nombre_malo_sigue_siendo_404(self):
        with ConRedPublicada() as ctx:
            r = ctx.client.get("/avatars/notas.txt?token=llave-de-prueba")
            self.assertEqual(404, r.status_code)

    def test_en_local_se_sigue_sirviendo_como_siempre(self):
        with mock.patch.dict(os.environ, {"CORT_DOTENV": "0"}, clear=False):
            os.environ.pop("CORT_HOST", None)
            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            raiz = pathlib.Path(tmp.name)
            (raiz / "casual.png").write_bytes(b"\x89PNG\r\n\x1a\n-fake")
            with mock.patch.dict(os.environ, {"CORT_AVATAR_DIR": str(raiz)}):
                r = TestClient(app).get("/avatars/casual.png")
                self.assertEqual(200, r.status_code)


class TestLanzadorNiegaRedSinToken(unittest.TestCase):
    def test_el_motivo_de_negarse_llega_a_la_terminal(self):
        """`python -m cort_core.server` con `CORT_HOST=0.0.0.0` y sin token tiene
        que salir con código 1 y decir por qué, no arrancar un puerto abierto."""
        import subprocess
        here = pathlib.Path(__file__).resolve().parents[1]
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        env = {**os.environ, "CORT_DOTENV": "0", "CORT_HOST": "0.0.0.0",
               "CORT_MEMORY_DB": str(pathlib.Path(tmp.name) / "prueba.db")}
        env.pop("CORT_LAN_TOKEN", None)
        # Techo de 180 s, no de 60: medido el 2026-10-09, el proceso niega el
        # arranque y sale en **3,6 s** solo, pero en una máquina de dos núcleos
        # con el resto de la suite encima se pasó de 60 y la prueba explotó por
        # `TimeoutExpired` — sin relación con lo que comprueba. Lo que sigue
        # caducando es la guarda: si alguien quitara el `raise`, el lanzador se
        # quedaría escuchando y la prueba esperaría sus tres minutos enteros.
        r = subprocess.run([sys.executable, "-m", "cort_core.server"],
                           cwd=here, env=env, capture_output=True, text=True,
                           timeout=180)
        self.assertEqual(1, r.returncode, r.stdout + r.stderr)
        self.assertIn("CORT no arranca", r.stdout)
        self.assertIn("CORT_LAN_TOKEN", r.stdout)


if __name__ == "__main__":
    unittest.main()
