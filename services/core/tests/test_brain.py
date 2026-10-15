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


class TestCloud(unittest.IsolatedAsyncioTestCase):
    """La nube es opcional y nunca debe dejar a CORT callada: si falla, habla
    la cadena local, y lo dice."""

    ENV = {"CORT_LLM_PROVIDER": "anthropic", "CORT_ANTHROPIC_API_KEY": "sk-ant-PRUEBA"}

    def setUp(self):
        import os
        from unittest import mock
        self._chain, self._cap = brain.CHAIN, brain.MAX_MODEL_MIB
        brain.CHAIN, brain.MAX_MODEL_MIB = ["local:1b"], 3000
        for k in ("CORT_LLM_PROVIDER", "CORT_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY",
                  "CORT_OPENAI_API_KEY", "CORT_OPENAI_MODEL", "CORT_OPENAI_BASE_URL",
                  "CORT_ANTHROPIC_EFFORT", "CORT_ANTHROPIC_MODEL", "CORT_OPENAI_REASONING_EFFORT"):
            os.environ.pop(k, None)
        self._patch = mock.patch.dict(os.environ, {})
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        brain.CHAIN, brain.MAX_MODEL_MIB = self._chain, self._cap

    def cloud(self, status=200, text="hola desde la nube", seen=None, local=None):
        def handler(request):
            if request.url.host == "api.anthropic.com":
                if seen is not None:
                    seen.update(headers=dict(request.headers), body=json.loads(request.content))
                if status != 200:
                    return httpx.Response(status, json={"error": {"message": "credit balance is too low"}})
                return httpx.Response(200, json={"content": [{"type": "text", "text": text}]})
            if request.url.path == "/api/tags":
                return httpx.Response(200, json={"models": [model("local:1b", 300)]})
            if local is not None:
                local.append(1)
            return httpx.Response(200, json={"message": {"content": "respuesta local"}})
        return httpx.MockTransport(handler)

    async def run_think(self, transport_, history=None):
        async with httpx.AsyncClient(transport=transport_) as client:
            return await brain.think(history or [{"role": "user", "content": "hola"}], client)

    async def test_default_is_local_and_never_touches_the_cloud(self):
        hosts = []
        def handler(request):
            hosts.append(request.url.host)
            if request.url.path == "/api/tags":
                return httpx.Response(200, json={"models": [model("local:1b", 300)]})
            return httpx.Response(200, json={"message": {"content": "local"}})
        out = await self.run_think(httpx.MockTransport(handler))
        self.assertEqual(out, "local")
        self.assertNotIn("api.anthropic.com", hosts)

    async def test_anthropic_answers_and_ollama_is_not_asked(self):
        import os
        os.environ.update(self.ENV)
        local, seen = [], {}
        out = await self.run_think(self.cloud(seen=seen, local=local))
        self.assertEqual(out, "hola desde la nube")
        self.assertEqual(local, [], "con la nube respondiendo no se toca Ollama")
        self.assertEqual(brain.last_model(), "anthropic:claude-haiku-5-5")
        self.assertEqual(seen["headers"]["x-api-key"], "sk-ant-PRUEBA")
        self.assertEqual(seen["headers"]["anthropic-version"], "2023-06-01")

    async def test_request_shape_matches_what_current_claude_models_accept(self):
        """Los Claude recientes rechazan `temperature` y `top_p`, y el `system`
        va aparte; un tope de 120 tokens cortaría la respuesta antes del texto."""
        import os
        os.environ.update(self.ENV)
        seen = {}
        await self.run_think(self.cloud(seen=seen))
        b = seen["body"]
        self.assertNotIn("temperature", b)
        self.assertNotIn("top_p", b)
        self.assertTrue(b["system"].startswith(brain.SYSTEM))
        self.assertGreaterEqual(b["max_tokens"], 512)
        self.assertEqual(b["output_config"], {"effort": "low"})

    async def test_conversation_starts_with_the_user(self):
        import os
        os.environ.update(self.ENV)
        seen = {}
        await self.run_think(self.cloud(seen=seen), [
            {"role": "assistant", "content": "Hola, soy CORT."},
            {"role": "user", "content": "¿qué tal?"}])
        self.assertEqual(seen["body"]["messages"][0]["role"], "user")

    async def test_effort_can_be_turned_off_for_older_models(self):
        import os
        os.environ.update({**self.ENV, "CORT_ANTHROPIC_EFFORT": ""})
        seen = {}
        await self.run_think(self.cloud(seen=seen))
        self.assertNotIn("output_config", seen["body"])

    async def test_cloud_failure_falls_back_to_local_and_says_why(self):
        import os
        os.environ.update(self.ENV)
        out = await self.run_think(self.cloud(status=400))
        self.assertTrue(out.startswith("[nube no disponible"), out)
        self.assertIn("credit balance", out, "el motivo real ayuda a arreglarlo")
        self.assertTrue(out.endswith("respuesta local"))
        self.assertNotIn("sk-ant", out, "la clave jamás sale en un mensaje")
        self.assertEqual(brain.last_model(), "local:1b")

    async def test_rejected_key_is_reported_as_such(self):
        import os
        os.environ.update(self.ENV)
        out = await self.run_think(self.cloud(status=401))
        self.assertIn("clave rechazada", out)

    async def test_missing_key_is_reported_without_calling_the_cloud(self):
        import os
        os.environ["CORT_LLM_PROVIDER"] = "anthropic"
        hosts = []
        base = self.cloud()
        def handler(request):
            hosts.append(request.url.host)
            return base.handle_request(request)
        out = await self.run_think(httpx.MockTransport(handler))
        self.assertIn("falta CORT_ANTHROPIC_API_KEY", out)
        self.assertNotIn("api.anthropic.com", hosts)

    async def test_empty_cloud_answer_counts_as_a_failure(self):
        import os
        os.environ.update(self.ENV)
        out = await self.run_think(self.cloud(text=""))
        self.assertIn("vacía", out)

    async def test_gemini_style_list_error_body_still_explains_itself(self):
        """Gemini manda el error dentro de una lista. Un 404 por «el modelo ya
        no existe» salía como «error 404», sin motivo, y no había por dónde
        empezar a arreglarlo."""
        import os
        os.environ.update({"CORT_LLM_PROVIDER": "openai", "CORT_OPENAI_API_KEY": "AIza-SECRETA",
                           "CORT_OPENAI_MODEL": "gemini-viejo"})
        def handler(request):
            if request.url.host == "generativelanguage.googleapis.com":
                return httpx.Response(404, json=[{"error": {"code": 404, "message":
                    "models/gemini-viejo is no longer available. Key AIza-SECRETA"}}])
            if request.url.path == "/api/tags":
                return httpx.Response(200, json={"models": [model("local:1b", 300)]})
            return httpx.Response(200, json={"message": {"content": "respuesta local"}})
        os.environ["CORT_OPENAI_BASE_URL"] = "https://generativelanguage.googleapis.com/v1beta/openai/"
        out = await self.run_think(httpx.MockTransport(handler))
        self.assertIn("error 404", out)
        self.assertIn("gemini-viejo is no longer available", out)
        self.assertNotIn("AIza-SECRETA", out, "ni aunque el proveedor la repita")

    async def test_plain_text_error_body_is_shown_too(self):
        import os
        os.environ.update(self.ENV)
        def handler(request):
            if request.url.host == "api.anthropic.com":
                return httpx.Response(502, text="Bad gateway")
            if request.url.path == "/api/tags":
                return httpx.Response(200, json={"models": [model("local:1b", 300)]})
            return httpx.Response(200, json={"message": {"content": "respuesta local"}})
        out = await self.run_think(httpx.MockTransport(handler))
        self.assertIn("error 502: Bad gateway", out)

    def test_system_prompt_tells_the_model_what_time_it_is(self):
        """Sin esto, «¿qué hora es?» recibía «no tengo acceso a la hora»."""
        import os
        from datetime import datetime
        from unittest import mock
        with mock.patch.dict(os.environ, {"CORT_CITY": "Bogota"}):
            texto = brain.system()
        ahora = datetime.now().astimezone()
        self.assertTrue(texto.startswith(brain.SYSTEM))
        self.assertIn("Fecha y hora actuales", texto)
        self.assertIn(str(ahora.year), texto)
        self.assertIn(f"{ahora:%H:%M}", texto)
        self.assertIn("Bogota", texto)

    def test_system_prompt_without_a_city_does_not_invent_one(self):
        import os
        from unittest import mock
        env = {k: v for k, v in os.environ.items() if k != "CORT_CITY"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertNotIn("La usuaria está en", brain.system())

    async def test_openai_compatible_endpoint(self):
        import os
        os.environ.update({"CORT_LLM_PROVIDER": "openai", "CORT_OPENAI_API_KEY": "gsk-PRUEBA",
                           "CORT_OPENAI_MODEL": "modelo-x",
                           "CORT_OPENAI_BASE_URL": "https://api.groq.com/openai/v1/"})
        seen = {}
        def handler(request):
            seen.update(url=str(request.url), auth=request.headers["authorization"],
                        body=json.loads(request.content))
            return httpx.Response(200, json={"choices": [{"message": {"content": "hola compatible"}}]})
        out = await self.run_think(httpx.MockTransport(handler))
        self.assertEqual(out, "hola compatible")
        self.assertEqual(seen["url"], "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(seen["auth"], "Bearer gsk-PRUEBA")
        self.assertEqual(seen["body"]["messages"][0]["role"], "system")
        self.assertIn("max_tokens", seen["body"])
        self.assertEqual(brain.last_model(), "openai:modelo-x")

    async def test_reasoning_effort_is_sent_only_when_asked_for(self):
        import os
        base = {"CORT_LLM_PROVIDER": "openai", "CORT_OPENAI_API_KEY": "k", "CORT_OPENAI_MODEL": "m",
                "CORT_OPENAI_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai/"}
        seen = {}
        def handler(request):
            seen.update(url=str(request.url), body=json.loads(request.content))
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
        os.environ.update(base)
        await self.run_think(httpx.MockTransport(handler))
        self.assertNotIn("reasoning_effort", seen["body"])
        self.assertEqual(seen["url"],
                         "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
        os.environ["CORT_OPENAI_REASONING_EFFORT"] = "low"
        await self.run_think(httpx.MockTransport(handler))
        self.assertEqual(seen["body"]["reasoning_effort"], "low")
        os.environ.pop("CORT_OPENAI_REASONING_EFFORT", None)

    async def test_openai_proper_uses_the_new_token_cap_name(self):
        import os
        os.environ.update({"CORT_LLM_PROVIDER": "openai", "CORT_OPENAI_API_KEY": "k",
                           "CORT_OPENAI_MODEL": "m"})
        seen = {}
        def handler(request):
            seen.update(body=json.loads(request.content))
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
        await self.run_think(httpx.MockTransport(handler))
        self.assertIn("max_completion_tokens", seen["body"])
        self.assertNotIn("max_tokens", seen["body"])


if __name__ == "__main__":
    unittest.main()
