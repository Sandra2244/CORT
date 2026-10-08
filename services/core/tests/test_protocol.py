"""Pruebas del protocolo WebSocket, con el core en memoria y sin tocar Ollama.

Se usan intents porque atajan antes de la llamada al LLM: así el test mide el
protocolo y no la velocidad del modelo, que en esta máquina es de segundos.

Y se sustituye el ejecutor de `actions.py` por uno de mentira: estas pruebas
tienen que ver el mensaje que produce una acción que funcionó, y la forma de
verlo sin hacer que el portátil conteste con un `wpctl` de verdad es no dejarle
hacerlo.
"""
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from cort_core import actions
from cort_core.server import app


#: El volumen se lee antes y después de mandarlo, así que el fake tiene que
#: responder dos niveles distintos o CORT reportaría "no cambió".
LEVELS = ["1.00", "0.45"]


async def fake_spawn(argv):
    """Acepta lo que le venga y dice que el nivel quedó en 45 %."""
    if "get-volume" in argv:
        out = LEVELS.pop(0) if len(LEVELS) > 1 else LEVELS[0]
        return 0, f"Volume: {out}"
    return 0, ""


class TestProtocol(unittest.TestCase):
    def setUp(self):
        # Cada conexión espera un cambio, así que la lista vuelve a su sitio.
        LEVELS[:] = ["1.00", "0.45"]
        # Patches abiertos antes de TestClient y cerrados en tearDown: si el
        # ejecutor real se escapara, el test no fallaría — movería el volumen.
        patcher = mock.patch.object(actions, "spawn", fake_spawn)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(app)

    def handshake(self, ws):
        types = [ws.receive_json()["type"] for _ in range(2)]
        self.assertEqual(["state", "assistant_message"], types)

    def test_connect_gives_state_then_greeting(self):
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)

    def test_intent_emits_an_effect(self):
        """El pulso es lo que hace visible que algo se ejecutó. Si el orden se
        rompe, el HUD puede animarse antes de que exista el intent."""
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            ws.send_json({"type": "user_message", "text": "sube el volumen"})
            got = [ws.receive_json() for _ in range(3)]

        self.assertEqual(["intent", "effect", "assistant_message"], [m["type"] for m in got])
        self.assertEqual("pulse", got[1]["kind"])

    def test_the_reply_carries_the_number_the_command_returned(self):
        """CORT no dice «entendido» y se queda tan ancha: dice el nivel que leyó
        después de cambiarlo. Un texto fijo taparía un mando que no hace nada."""
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            ws.send_json({"type": "user_message", "text": "sube el volumen"})
            msgs = [ws.receive_json() for _ in range(3)]
        self.assertEqual("Volumen al 45 %.", msgs[-1]["text"])

    def test_a_failed_action_shows_as_a_tear_not_a_wave(self):
        with mock.patch.object(actions, "spawn", failing_spawn):
            with self.client.websocket_connect("/ws") as ws:
                self.handshake(ws)
                ws.send_json({"type": "user_message", "text": "sube el volumen"})
                msgs = [ws.receive_json() for _ in range(3)]
        self.assertEqual("glitch", msgs[1]["kind"])
        self.assertIn("wpctl: no hay sink", msgs[-1]["text"])

    def test_effect_kind_is_one_the_ui_can_play(self):
        """El cliente valida `kind` contra su propia lista y descarta lo que no
        conoce; un nombre inventado aquí sería un efecto que nunca se ve."""
        playable = {"glitch", "pulse", "scan", "shake", "flash"}
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            ws.send_json({"type": "user_message", "text": "sube el volumen"})
            kinds = {m["kind"] for m in (ws.receive_json() for _ in range(3))
                     if m["type"] == "effect"}
        self.assertTrue(kinds <= playable, f"kinds fuera del protocolo: {kinds - playable}")

    def test_ignored_message_gets_no_reply(self):
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            ws.send_json({"type": "otra_cosa"})
            ws.send_json({"type": "user_message", "text": "   "})
            # Ninguno de los dos debe producir respuesta: el siguiente mensaje
            # válido es el que tiene que contestar.
            ws.send_json({"type": "user_message", "text": "baja el volumen"})
            m = ws.receive_json()
        self.assertEqual("intent", m["type"])


async def failing_spawn(argv):
    return 1, "wpctl: no hay sink"


if __name__ == "__main__":
    unittest.main()
