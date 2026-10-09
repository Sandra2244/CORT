"""Pruebas del catálogo de atuendos (`cort_core/avatars.py`).

Van contra un directorio de mentira montado en `tempfile`, con `CORT_AVATAR_DIR`
parcheado: en una máquina donde la carpeta real pesa 165 MB y contiene modelos con
licencia ajena, una prueba que la leyera sería lenta, frágil y además indiscreta.

Lo que de verdad se prueba aquí no es que sepa listar —eso lo hace cualquier `ls`—
son las dos puertas que no se pueden abrir: que sin variable no hay función, y que
con variable no se sale de la carpeta.
"""
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from cort_core import avatars
from cort_core.server import app


class ConDirectorio:
    """Contexto: un directorio con dos imágenes, un VRM, un .txt y un oculto."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = pathlib.Path(self.tmp.name)
        (self.raiz / "aira_default.png").write_bytes(b"\x89PNG\r\n\x1a\n-fake")
        (self.raiz / "Aira pijama sin fondo.png").write_bytes(b"\x89PNG\r\n\x1a\n-fake2")
        (self.raiz / "aira_base.vrm").write_bytes(b"glTF-fake")
        (self.raiz / "notas.txt").write_text("esto no se sirve")
        (self.raiz / ".oculta.png").write_bytes(b"\x89PNG")
        (self.raiz / "subdir").mkdir()
        (self.raiz / "subdir" / "dentro.png").write_bytes(b"\x89PNG")
        self.parche = mock.patch.dict(os.environ, {"CORT_AVATAR_DIR": str(self.raiz)})
        self.parche.start()
        return self

    def __exit__(self, *exc):
        self.parche.stop()
        self.tmp.cleanup()
        return False


class TestSinActivar(unittest.TestCase):
    def test_sin_variable_no_hay_funcion(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(avatars.raiz())
            self.assertEqual(avatars.listar(), [])
            self.assertIsNone(avatars.ruta_segura("aira_default.png"))

    def test_variable_apuntando_a_nada(self):
        # Una ruta que no es directorio está tan apagada como no tener variable:
        # no se inventa un catálogo vacío con pinta de catálogo lleno.
        with mock.patch.dict(os.environ, {"CORT_AVATAR_DIR": "/no/existe/la/carpeta"}):
            self.assertIsNone(avatars.raiz())
            self.assertEqual(avatars.listar(), [])


class TestListar(unittest.TestCase):
    def test_solo_extensiones_permitidas_y_sin_ocultos(self):
        with ConDirectorio() as d:
            items = avatars.listar()
            nombres = [i["nombre"] for i in items]
            # Orden por nombre en minúsculas, para que «Aira…» y «aira…» no
            # dependan de la tabla de códigos.
            self.assertEqual(nombres, ["Aira pijama sin fondo.png", "aira_base.vrm", "aira_default.png"])
            self.assertNotIn("notas.txt", nombres, "una extensión fuera de la lista no se sirve")
            self.assertNotIn(".oculta.png", nombres, "un archivo oculto no se enseña en el catálogo")
            self.assertEqual(len(nombres), 3, "subdir/ no es archivo y no entra")
            self.assertTrue(all(i["bytes"] > 0 for i in items))
            self.assertTrue(d.raiz.is_dir())

    def test_mime_por_extension(self):
        with ConDirectorio():
            tipos = {i["nombre"]: i["mime"] for i in avatars.listar()}
            self.assertEqual(tipos["aira_default.png"], "image/png")
            self.assertEqual(tipos["aira_base.vrm"], "model/vrm")


class TestRutaSegura(unittest.TestCase):
    def test_sirve_lo_que_existe(self):
        with ConDirectorio() as d:
            self.assertEqual(avatars.ruta_segura("aira_default.png"),
                             (d.raiz / "aira_default.png").resolve())

    def test_nombre_con_espacios_y_mayusculas(self):
        # Los nombres reales de sus archivos son así: «Aira pijama sin fondo.png».
        with ConDirectorio():
            self.assertIsNotNone(avatars.ruta_segura("Aira pijama sin fondo.png"))

    def test_rechaza_salir_de_la_raiz(self):
        with ConDirectorio():
            for malo in [
                "../aira_default.png",
                "../../etc/passwd",
                "/etc/passwd",
                "subdir/dentro.png",
                "aira_default.png\u0000.txt",
                "..",
                "",
                "$(rm -rf /)",
                "air@a_default.png",
            ]:
                with self.subTest(malo=malo):
                    self.assertIsNone(avatars.ruta_segura(malo))

    def test_rechaza_extension_no_permitida(self):
        with ConDirectorio():
            self.assertIsNone(avatars.ruta_segura("notas.txt"))

    def test_rechaza_lo_que_no_existe(self):
        with ConDirectorio():
            self.assertIsNone(avatars.ruta_segura("no-esta-aqui.png"))

    def test_rechaza_enlace_simbolico_que_sale(self):
        # El caso que cuela un `startswith`: un eslabón dentro de la carpeta que
        # apunta fuera. Al resolver, ya no está bajo la raíz, y no se sirve.
        with ConDirectorio() as d:
            fuera = pathlib.Path(d.tmp.name).parent / "fuera-del-directorio.png"
            try:
                fuera.write_bytes(b"\x89PNG")
                (d.raiz / "tramposo.png").symlink_to(fuera)
                self.assertIsNone(avatars.ruta_segura("tramposo.png"))
            finally:
                fuera.unlink(missing_ok=True)


class TestEndpoint(unittest.TestCase):
    def test_404_sin_directorio(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with TestClient(app) as cliente:
                self.assertEqual(cliente.get("/avatars/aira_default.png").status_code, 404)

    def test_200_con_contenido(self):
        with ConDirectorio():
            with TestClient(app) as cliente:
                r = cliente.get("/avatars/aira_default.png")
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.headers["content-type"], "image/png")
                self.assertTrue(r.content.startswith(b"\x89PNG"))

    def test_404_tambien_para_traversal_codificada(self):
        with ConDirectorio():
            with TestClient(app) as cliente:
                # El cliente normaliza `%2e%2e/` antes de llegar; sea como sea que
                # entre, no sale de la carpeta.
                self.assertEqual(cliente.get("/avatars/../notas.txt").status_code, 404)
                self.assertEqual(cliente.get("/avatars/notas.txt").status_code, 404)


class TestListadoPorWebSocket(unittest.TestCase):
    def test_pedido_y_respuesta(self):
        with ConDirectorio():
            with TestClient(app) as cliente:
                with cliente.websocket_connect("/ws") as ws:
                    # Los tres cuadros de siempre al conectar: estado, saludo, telemetría.
                    ws.receive_json()
                    ws.receive_json()
                    ws.receive_json()
                    ws.send_json({"type": "list_avatars"})
                    cuadro = ws.receive_json()
                    self.assertEqual(cuadro["type"], "avatars")
                    self.assertEqual(len(cuadro["items"]), 3)

    def test_sin_directorio_devuelve_lista_vacia(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with TestClient(app) as cliente:
                with cliente.websocket_connect("/ws") as ws:
                    ws.receive_json()
                    ws.receive_json()
                    ws.receive_json()
                    ws.send_json({"type": "list_avatars"})
                    cuadro = ws.receive_json()
                    self.assertEqual(cuadro["items"], [])


if __name__ == "__main__":
    unittest.main()
