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
        """Tres marcos al conectar: el estado del holograma, el saludo y la
        telemetría. El orden es el que la interfaz necesita: el orbe se colorea
        antes de que llegue texto que leer. Devuelve los mensajes por si el test
        quiere mirar algún campo.

        El saludo es `greeting`, no `assistant_message`: la interfaz lo pinta
        sólo sobre un registro vacío, porque una reconexión no es una
        presentación. Si volviera a viajar como mensaje normal, cada reintento
        del WebSocket añadiría un «Hola, soy CORT.» a la conversación en curso
        — cuatro reinicios, cuatro saludos, medido en el navegador."""
        got = [ws.receive_json() for _ in range(3)]
        self.assertEqual(["state", "greeting", "status"], [m["type"] for m in got])
        return got

    def turn(self, ws, text):
        """Un turno de acción: envía y lee los cuatro marcos que produce.
        Devuelve los mensajes en orden, terminando por el `status` nuevo."""
        ws.send_json({"type": "user_message", "text": text})
        got = [ws.receive_json() for _ in range(4)]
        self.assertEqual(["intent", "effect", "assistant_message", "status"],
                         [m["type"] for m in got])
        return got

    def test_connect_gives_state_then_greeting(self):
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)

    def test_the_greeting_is_text_a_person_can_read(self):
        """Viaja en su propio marco, así que hay que comprobar que sigue diciendo
        algo: un `greeting` sin `text` pintaría una burbuja vacía al abrir."""
        with self.client.websocket_connect("/ws") as ws:
            g = self.handshake(ws)[1]
        self.assertIsInstance(g["text"], str)
        self.assertTrue(g["text"].strip())

    def test_the_status_frame_carries_the_telemetry_the_panel_paints(self):
        """La interfaz pinta estos campos sin comprobarlos, así que tienen que
        estar y ser del tipo que espera. `brain` puede venir en null —aquí aún
        no se ha preguntado al modelo—, pero la clave existe."""
        with self.client.websocket_connect("/ws") as ws:
            s = self.handshake(ws)[2]
        self.assertEqual("status", s["type"])
        for key in ("memories", "keep", "brain", "ollama", "actions"):
            self.assertIn(key, s)
        self.assertIsInstance(s["memories"], int)
        self.assertIsInstance(s["actions"], bool)

    def test_intent_emits_an_effect(self):
        """El pulso es lo que hace visible que algo se ejecutó. Si el orden se
        rompe, el HUD puede animarse antes de que exista el intent."""
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            got = self.turn(ws, "sube el volumen")

        self.assertEqual("pulse", got[1]["kind"])

    def test_the_reply_carries_the_number_the_command_returned(self):
        """CORT no dice «entendido» y se queda tan ancha: dice el nivel que leyó
        después de cambiarlo. Un texto fijo taparía un mando que no hace nada."""
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            msgs = self.turn(ws, "sube el volumen")
        self.assertEqual("Volumen al 45 %.", msgs[2]["text"])

    def test_a_failed_action_shows_as_a_tear_not_a_wave(self):
        with mock.patch.object(actions, "spawn", failing_spawn):
            with self.client.websocket_connect("/ws") as ws:
                self.handshake(ws)
                msgs = self.turn(ws, "sube el volumen")
        self.assertEqual("glitch", msgs[1]["kind"])
        self.assertIn("wpctl: no hay sink", msgs[2]["text"])

    def test_effect_kind_is_one_the_ui_can_play(self):
        """El cliente valida `kind` contra su propia lista y descarta lo que no
        conoce; un nombre inventado aquí sería un efecto que nunca se ve."""
        playable = {"glitch", "pulse", "scan", "shake", "flash"}
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            kinds = {m["kind"] for m in self.turn(ws, "sube el volumen") if "kind" in m}
        self.assertTrue(kinds <= playable, f"kinds fuera del protocolo: {kinds - playable}")

    def test_una_respuesta_sacude_la_pantalla(self):
        """Hasta hoy `shake` estaba **arreglado y muerto** a la vez: el cliente lo
        sabía tocar, pero el core sólo mandaba `pulse` y `glitch`, así que nunca
        llegaba. Se pide una respuesta que no sea una orden y se compran dos cosas:
        que el efecto venga y que venga **después** del texto — una animación que
        se dispara antes de que exista la respuesta es un aviso, no una reacción.
        El saludo también queda comprobado por omisión: `handshake()` exige tres
        marcos y ninguno es `effect`, así que reconectar no hace temblar la
        pantalla."""
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            ws.send_json({"type": "user_message", "text": "hola cort"})
            vistos = []
            while True:
                vistos.append(ws.receive_json())
                tipos = [m["type"] for m in vistos]
                if "assistant_message" in tipos and vistos[-1]["type"] == "effect":
                    break
                if len(vistos) > 12:
                    self.fail(f"demasiados marcos para un turno: {tipos}")
        tipos = [m["type"] for m in vistos]
        i = tipos.index("assistant_message")
        self.assertEqual("effect", tipos[i + 1])
        self.assertEqual("shake", vistos[i + 1]["kind"])

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
