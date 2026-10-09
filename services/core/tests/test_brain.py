import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx

from cort_core import brain

MIB = 2**20


def transport(catalogue, answers, calls):
    """Un Ollama de mentira: `/api/tags` devuelve `catalogue` y `/api/chat`
    contesta según `answers`, que mapa nombre de modelo -> texto o excepción."""

    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": catalogue})
        body = json.loads(request.content)
        model = body["model"]
        calls.append(model)
        outcome = answers.get(model, "respuesta de " + model)
        if isinstance(outcome, Exception):
            raise outcome
        return httpx.Response(200, json={"message": {"role": "assistant",
                                                     "content": outcome}})

    return httpx.MockTransport(handler)


def model(name, mib):
    return {"name": name, "size": mib * MIB}


class TestCandidates(unittest.TestCase):
    def test_drops_models_that_do_not_fit(self):
        """El caso que congeló el PC: 2,4 GiB de modelo en 1,8 GiB de máquina."""
        sizes = {"qwen2.5:0.5b": 379, "qwen3.5:2b": 2614}
        brain.MAX_MODEL_MIB = 700
        self.assertEqual(brain.candidates(["qwen2.5:0.5b", "qwen3.5:2b"], sizes),
                         ["qwen2.5:0.5b"])

    def test_keeps_unknown_models(self):
        """Un modelo que no está en el catálogo podría descargarse bajo demanda;
        descartarlo por no verlo sería más restrictivo que la realidad."""
        brain.MAX_MODEL_MIB = 700
        self.assertEqual(brain.candidates(["nuevo:latest"], {}), ["nuevo:latest"])

    def test_order_is_preserved(self):
        sizes = {"b": 100, "a": 100}
        brain.MAX_MODEL_MIB = 700
        self.assertEqual(brain.candidates(["b", "a"], sizes), ["b", "a"])


class TestChain(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._chain = brain.CHAIN
        self._cap = brain.MAX_MODEL_MIB

    def tearDown(self):
        brain.CHAIN = self._chain
        brain.MAX_MODEL_MIB = self._cap

    async def think_with(self, catalogue, answers, calls):
        async with httpx.AsyncClient(transport=transport(catalogue, answers, calls)) as client:
            return await brain.think([{"role": "user", "content": "hola"}], client)

    async def test_first_model_wins_when_it_answers(self):
        brain.CHAIN = ["pequeño:1b", "mediano:2b"]
        calls = []
        out = await self.think_with([model("pequeño:1b", 300), model("mediano:2b", 500)],
                                    {}, calls)
        self.assertEqual(out, "respuesta de pequeño:1b")
        self.assertEqual(calls, ["pequeño:1b"], "no debía llegar al segundo")

    async def test_substitutes_when_the_first_fails(self):
        """El motivo de la cadena: si uno falla, habla el siguiente sin que se
        entere nadie."""
        brain.CHAIN = ["roto:1b", "sano:1b"]
        calls = []
        out = await self.think_with([model("roto:1b", 300), model("sano:1b", 300)],
                                    {"roto:1b": httpx.ConnectError("muerto")}, calls)
        self.assertEqual(out, "respuesta de sano:1b")
        self.assertEqual(calls, ["roto:1b", "sano:1b"])

    async def test_oversized_model_is_never_called(self):
        """La guarda no es un mensaje: el modelo grande no se invoca ni una vez,
        porque invocarlo es lo que tumba la máquina."""
        brain.CHAIN = ["enorme:3b", "pequeño:1b"]
        calls = []
        out = await self.think_with([model("enorme:3b", 2614), model("pequeño:1b", 300)],
                                    {}, calls)
        self.assertEqual(calls, ["pequeño:1b"])
        self.assertEqual(out, "respuesta de pequeño:1b")

    async def test_timeout_counts_as_a_failure_and_moves_on(self):
        brain.CHAIN = ["lento:1b", "listo:1b"]
        calls = []
        out = await self.think_with([model("lento:1b", 300), model("listo:1b", 300)],
                                    {"lento:1b": httpx.ReadTimeout("tarde")}, calls)
        self.assertEqual(out, "respuesta de listo:1b")

    async def test_eco_when_the_whole_chain_is_dead(self):
        brain.CHAIN = ["a:1b", "b:1b"]
        calls = []
        out = await self.think_with([model("a:1b", 300), model("b:1b", 300)],
                                    {"a:1b": httpx.ConnectError("x"),
                                     "b:1b": httpx.ConnectError("x")}, calls)
        self.assertIn("ningún modelo", out)
        self.assertIn("hola", out, "el eco debe repetir lo que dijiste")

    async def test_eco_when_there_is_no_server_at_all(self):
        """Sin Ollama arrancado la interfaz tiene que seguir respondiendo."""
        brain.CHAIN = ["a:1b"]
        def refuses(request):
            raise httpx.ConnectError("nada escuchando")
        async with httpx.AsyncClient(transport=httpx.MockTransport(refuses)) as client:
            out = await brain.think([{"role": "user", "content": "hola"}], client)
        self.assertIn("modo eco", out)

    async def test_keep_alive_is_sent(self):
        """Sin esto Ollama descarga el modelo a los 5 minutos y la siguiente
        conversación paga otra vez la carga completa (113 s medidos)."""
        brain.CHAIN = ["a:1b"]
        seen = {}

        def handler(request):
            if request.url.path == "/api/tags":
                return httpx.Response(200, json={"models": [model("a:1b", 300)]})
            seen.update(json.loads(request.content))
            return httpx.Response(200, json={"message": {"content": "ok"}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await brain.think([{"role": "user", "content": "hola"}], client)
        self.assertEqual(seen["keep_alive"], brain.KEEP_ALIVE)
        self.assertEqual(seen["options"]["num_predict"], brain.MAX_TOKENS)


if __name__ == "__main__":
    unittest.main()
