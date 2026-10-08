"""El panel de estado no puede inventar nada.

La interfaz pinta estos valores tal cual, así que cada uno tiene que ser una
comprobación: cuántos recuerdos hay de verdad, qué modelo contestó de verdad, si
la capa de permisos está encendida de verdad. Un panel que adornara con «eco»
mientras Ollama está respondiendo sería peor que no tener panel.

Se prueba el paquete completo —no las funciones sueltas— porque lo que llega a
la pantalla es el dict que sale de `status.build`.
"""
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx

from cort_core import brain, status
from cort_core.memory.store import MemoryStore

MIB = 2**20


def new_store() -> MemoryStore:
    """Una base en un directorio aparte: estas pruebas no pueden tocar los
    recuerdos reales de esta máquina, ni aunque algo se quede a media frase."""
    return MemoryStore(pathlib.Path(tempfile.mkdtemp(prefix="cort-status-")) / "memory.db")


class FakeConn:
    """Conexión de mentira que recuerda el SQL que le pasó."""

    def __init__(self, row):
        self._row = row
        self.queries = []

    def execute(self, query, params=()):
        self.queries.append(query)
        return self

    def fetchone(self):
        return self._row


class TestCuenta(unittest.TestCase):
    def setUp(self):
        self.store = new_store()
        self.addCleanup(self.store.close)

    def test_vacia_es_cero(self):
        self.assertEqual(0, self.store.count())

    def test_cuenta_hechos_distintos(self):
        self.store.remember("Al usuario le gusta el café")
        self.store.remember("El usuario se llama Sandra")
        self.assertEqual(2, self.store.count())

    def test_repetir_el_mismo_hecho_no_duplica_la_fila(self):
        """`content` es UNIQUE, así que un eco de la misma frase no infla el
        contador del panel. No lo es cambiando mayúsculas: medido aquí, «El
        usuario tiene perro» y «el usuario tiene perro» son dos filas."""
        self.store.remember("El usuario tiene perro")
        self.store.remember("El usuario tiene perro")
        self.assertEqual(1, self.store.count())

    def test_hace_un_count_y_no_lee_los_recuerdos(self):
        """El panel se manda en cada turno. Si alguien sustituye esto por
        `len(self.all())`, cada turno leería la base entera para enseñar un
        número."""
        fake = FakeConn((7,))
        real = self.store.conn
        self.store.conn = fake
        try:
            self.assertEqual(7, self.store.count())
        finally:
            self.store.conn = real
        self.assertEqual(1, len(fake.queries))
        self.assertIn("COUNT", fake.queries[0].upper())
        self.assertNotIn("SELECT content", fake.queries[0])


class TestPaquete(unittest.TestCase):
    def setUp(self):
        self.store = new_store()
        self.addCleanup(self.store.close)

    def test_trae_lo_mismo_que_la_base(self):
        for i in range(3):
            self.store.remember(f"Recuerdo {i}")
        with mock.patch.dict(os.environ, {"CORT_SYSTEM_ACTIONS": "1"}):
            s = status.build(self.store, keep=200)
        self.assertEqual("status", s["type"])
        self.assertEqual(3, s["memories"])
        self.assertEqual(200, s["keep"])

    def test_el_kill_switch_se_ve_en_el_panel(self):
        """Con las acciones apagadas la interfaz tiene que decirlo: si no, un
        «sube el volumen» que no hace nada parece un fallo del mando."""
        with mock.patch.dict(os.environ, {"CORT_SYSTEM_ACTIONS": "0"}):
            self.assertIs(False, status.build(self.store, keep=200)["actions"])

    def test_sin_haber_preguntado_al_modelo_no_se_inventa_uno(self):
        with mock.patch.object(brain, "_last", {"model": None, "ollama": None}):
            s = status.build(self.store, keep=200)
        self.assertIsNone(s["brain"])
        self.assertIsNone(s["ollama"])


class TestCerebroReal(unittest.IsolatedAsyncioTestCase):
    """`status` lee a `brain`, y `brain` sólo sabe algo después de un `think()`.

    Con el transporte simulado de siempre: encender Ollama de verdad para
    comprobar un nombre es justo lo que congeló esta máquina una vez.
    """

    def setUp(self):
        self.store = new_store()
        self.addCleanup(self.store.close)

    def ollama(self, answers):
        """Un Ollama de mentira con dos modelos de 300 MiB, ambos caben."""
        catalogue = [{"name": "roto:1b", "size": 300 * MIB},
                     {"name": "pequeno:1b", "size": 300 * MIB}]

        def handler(request):
            if request.url.path == "/api/tags":
                return httpx.Response(200, json={"models": catalogue})
            model = json.loads(request.content)["model"]
            outcome = answers.get(model, "respuesta de " + model)
            if isinstance(outcome, Exception):
                raise outcome
            return httpx.Response(200, json={"message": {"content": outcome}})

        return httpx.MockTransport(handler)

    async def test_el_panel_nombra_el_modelo_que_contesto(self):
        """El primero de la cadena falla; el panel tiene que decir el segundo."""
        with mock.patch.object(brain, "CHAIN", ["roto:1b", "pequeno:1b"]):
            async with httpx.AsyncClient(transport=self.ollama({"roto:1b": httpx.ConnectError("muerto")})) as client:
                await brain.think([{"role": "user", "content": "hola"}], client)
            s = status.build(self.store, keep=200)
        self.assertEqual("pequeno:1b", s["brain"])
        self.assertIs(True, s["ollama"])

    async def test_sin_servidor_el_panel_lo_admite(self):
        def refuses(request):
            raise httpx.ConnectError("nada escuchando")

        with mock.patch.object(brain, "CHAIN", ["pequeno:1b"]):
            async with httpx.AsyncClient(transport=httpx.MockTransport(refuses)) as client:
                await brain.think([{"role": "user", "content": "hola"}], client)
            s = status.build(self.store, keep=200)
        self.assertIsNone(s["brain"])
        self.assertIs(False, s["ollama"])


if __name__ == "__main__":
    unittest.main()
