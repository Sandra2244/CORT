"""Pruebas del protocolo WebSocket, con el core en memoria y sin tocar Ollama.

Se usan intents porque atajan antes de la llamada al LLM: así el test mide el
protocolo y no la velocidad del modelo, que en esta máquina es de segundos.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from cort_core.server import app


class TestProtocol(unittest.TestCase):
    def setUp(self):
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


if __name__ == "__main__":
    unittest.main()
