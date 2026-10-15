"""El asistente por el lado del servidor: alarmas que suenan, herramientas por el
WebSocket y propuestas del modelo que pasan por la misma validación.

Nada de esto toca el sistema: el contexto de las herramientas es de mentira y la
agenda vive en una carpeta temporal.
"""
import asyncio
import pathlib
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from cort_core import agenda as agenda_mod
from cort_core import herramientas, server


class SO:
    def __init__(self):
        self.abierto, self.teclas = [], []

    def abrir(self, d):
        self.abierto.append(d)

    def pulsar(self, t, veces=1):
        self.teclas.append((t, veces))


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.so = SO()
        self.ag = agenda_mod.Agenda(pathlib.Path(self.dir.name) / "agenda.json")
        ctx = herramientas.Contexto(agenda=self.ag, abrir=self.so.abrir, pulsar=self.so.pulsar,
                                    windows=True, acciones=lambda: True, home=pathlib.Path("/casa"),
                                    notas=pathlib.Path(self.dir.name) / "notas.txt")
        for p in (mock.patch.object(server, "herr_ctx", lambda: ctx),
                  mock.patch.object(server, "_agenda", self.ag),
                  mock.patch.object(server, "think", self.think)):
            p.start()
            self.addCleanup(p.stop)
        self.respuesta_modelo = "Buenas tardes."
        self.client = TestClient(server.app)

    async def think(self, history):
        return self.respuesta_modelo

    def handshake(self, ws):
        got = [ws.receive_json() for _ in range(3)]
        self.assertEqual(["state", "greeting", "status"], [m["type"] for m in got])

    def hasta_status(self, ws):
        """Lee marcos hasta el `status` que cierra todo turno. Contar marcos a mano
        es lo que hace colgarse una prueba cuando un camino emite uno de más o de menos."""
        vistos = []
        while True:
            vistos.append(ws.receive_json())
            if vistos[-1]["type"] == "status":
                return vistos

    def turno(self, ws, texto, n=3):
        ws.send_json({"type": "user_message", "text": texto})
        return [ws.receive_json() for _ in range(n)]


class TestHerramientasPorElSocket(Base):
    def test_abrir_youtube_es_un_efecto_un_mensaje_y_un_status(self):
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            got = self.turno(ws, "pon música relajante en youtube")
        self.assertEqual(["effect", "assistant_message", "status"], [m["type"] for m in got])
        self.assertEqual(got[0]["kind"], "pulse")
        self.assertIn("relajante", got[1]["text"])
        self.assertEqual(self.so.abierto, ["https://www.youtube.com/results?search_query=m%C3%BAsica+relajante"])

    def test_no_llama_al_modelo(self):
        self.think = mock.AsyncMock(side_effect=AssertionError("el modelo no debía intervenir"))
        with mock.patch.object(server, "think", self.think), self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            self.turno(ws, "abre la calculadora")
        self.think.assert_not_called()

    def test_una_alarma_queda_en_la_agenda_y_se_confirma(self):
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            got = self.turno(ws, "pon una alarma en 10 minutos")
        self.assertIn("Alarma puesta para", got[1]["text"])
        self.assertEqual(len(self.ag.pendientes()), 1)

    def test_lo_que_falla_se_ve_como_rasgon_y_se_dice(self):
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            self.so.abrir = None
            herramientas.Contexto  # (el contexto ya está atado; se fuerza el fallo por la llave)
            with mock.patch.object(server, "herr_ctx", lambda: herramientas.Contexto(
                    agenda=self.ag, abrir=lambda d: (_ for _ in ()).throw(FileNotFoundError()),
                    windows=True, acciones=lambda: True)):
                got = self.turno(ws, "abre la calculadora")
        self.assertEqual(got[0]["kind"], "glitch")
        self.assertTrue(got[1]["text"].startswith("No pude:"))

    def test_dos_ordenes_son_un_resumen(self):
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            got = self.turno(ws, "abre la calculadora y abre youtube", 4)
        self.assertEqual(["effect", "effect", "assistant_message", "status"], [m["type"] for m in got])
        self.assertTrue(got[2]["text"].startswith("2 de 2 pasos hechos"))

    def test_una_conversacion_normal_sigue_yendo_al_modelo(self):
        self.respuesta_modelo = "Muy bien, gracias."
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            ws.send_json({"type": "user_message", "text": "hola, ¿cómo estás?"})
            marcos = self.hasta_status(ws)
        self.assertIn("Muy bien, gracias.", [m.get("text") for m in marcos])
        self.assertEqual(self.so.abierto, [])

    def test_con_CORT_TOOLS_0_no_se_interpretan(self):
        with mock.patch.dict("os.environ", {"CORT_TOOLS": "0"}), self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            ws.send_json({"type": "user_message", "text": "abre youtube"})
            tipos = [m["type"] for m in self.hasta_status(ws)]
        self.assertEqual(self.so.abierto, [])
        self.assertIn("assistant_message", tipos)


class TestCronometro(Base):
    def test_iniciar_y_parar(self):
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            ws.send_json({"type": "user_message", "text": "inicia el cronómetro"})
            vistos = []
            while not any(m["type"] == "status" for m in vistos):
                vistos.append(ws.receive_json())
            self.assertIn("sube", [m.get("estado") for m in vistos if m["type"] == "timer"])
            ws.send_json({"type": "user_message", "text": "para el cronómetro"})
            vistos = []
            while not any(m["type"] == "status" for m in vistos):
                vistos.append(ws.receive_json())
        finales = [m for m in vistos if m["type"] == "timer" and m["estado"] == "para"]
        self.assertEqual(len(finales), 1)
        self.assertGreaterEqual(finales[0]["restante"], 0)
        self.assertIn("Cronómetro detenido", [m for m in vistos if m["type"] == "assistant_message"][0]["text"])


class TestPropuestaDelModelo(Base):
    def propone(self, texto_modelo, usuario="ponme algo tranquilo para trabajar"):
        self.respuesta_modelo = texto_modelo
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            ws.send_json({"type": "user_message", "text": usuario})
            return self.hasta_status(ws)

    def test_una_llamada_valida_se_ejecuta_y_se_muestra_lo_que_se_hizo(self):
        got = self.propone('{"herramienta": "spotify", "args": {"consulta": "música tranquila para trabajar"}}')
        mensaje = [m for m in got if m["type"] == "assistant_message"][0]["text"]
        self.assertIn("Abrí Spotify con la búsqueda", mensaje)
        self.assertNotIn("herramienta", mensaje, "el JSON del modelo nunca se pinta")
        self.assertEqual(self.so.abierto, ["spotify:search:m%C3%BAsica%20tranquila%20para%20trabajar"])

    def test_una_herramienta_inventada_no_hace_nada(self):
        got = self.propone('{"herramienta": "formatear_disco", "args": {"unidad": "C:"}}')
        mensaje = [m for m in got if m["type"] == "assistant_message"][0]["text"]
        self.assertTrue(mensaje.startswith("No pude hacer eso"))
        self.assertEqual((self.so.abierto, self.so.teclas), ([], []))

    def test_una_url_propia_del_modelo_no_se_abre(self):
        got = self.propone('{"herramienta": "abrir_app", "args": {"nombre": "https://malo.example/virus.exe"}}')
        self.assertEqual(self.so.abierto, [])
        mensaje = [m for m in got if m["type"] == "assistant_message"][0]["text"]
        self.assertIn("No pude:", mensaje)

    def test_texto_normal_del_modelo_se_muestra_tal_cual(self):
        got = self.propone("Con gusto. ¿Prefiere jazz o música clásica?")
        mensaje = [m for m in got if m["type"] == "assistant_message"][0]["text"]
        self.assertEqual(mensaje, "Con gusto. ¿Prefiere jazz o música clásica?")


class TestBucleDelModelo(Base):
    """El lazo de `agente.turno`: el modelo propone, CORT ejecuta y mide, el
    resultado **vuelve** al modelo, y ése decide el siguiente paso o cierra.
    Antes de este bucle, la segunda propuesta del modelo se perdía."""

    def guion(self, respuestas, usuario="háblame de Bach"):
        it = iter(respuestas)

        async def think(history):
            return next(it)

        with mock.patch.object(server, "think", think), self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            ws.send_json({"type": "user_message", "text": usuario})
            return self.hasta_status(ws)

    def acciones(self, marcos):
        """Los `effect` de acción (pulso/temblorcito), sin el `shake` de cierre."""
        return [m for m in marcos if m["type"] == "effect" and m["kind"] in ("pulse", "glitch")]

    def test_dos_propuestas_seguidas_son_dos_acciones_medidas(self):
        got = self.guion(['{"herramienta": "youtube", "args": {"consulta": "bach"}}',
                          '{"herramienta": "nota", "args": {"texto": "escuchar a Bach"}}',
                          "Con gusto."])
        self.assertEqual(len(self.acciones(got)), 2)
        mensaje = [m for m in got if m["type"] == "assistant_message"][0]["text"]
        self.assertTrue(mensaje.startswith("2 de 2"), mensaje)
        self.assertEqual(self.so.abierto,
                         ["https://www.youtube.com/results?search_query=bach"])

    def test_el_tope_es_cuatro_turnos_y_no_gira_infinito(self):
        # un modelo terco: nueve propuestas distintas donde sólo caben cuatro
        got = self.guion(['{"herramienta": "nota", "args": {"texto": "pan %d"}}' % i
                          for i in range(9)])
        self.assertEqual(len(self.acciones(got)), 4)
        mensaje = [m for m in got if m["type"] == "assistant_message"][0]["text"]
        self.assertTrue(mensaje.startswith("4 de 4"), mensaje)


class TestPlanParcialPorElSocket(Base):
    """«abre YouTube y cuéntame un chiste»: YouTube se abre por reglas y el
    chiste se le pregunta al modelo. Con la nube configurada responde; sin ella,
    CORT dice literalmente qué parte no supo hacer —en vez de no hacer ninguna—.
    """

    def turno(self, texto):
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            ws.send_json({"type": "user_message", "text": texto})
            return self.hasta_status(ws)

    def test_con_nube_el_cabo_va_al_modelo_y_lo_hecho_se_cuenta(self):
        self.respuesta_modelo = "Un chiste: un programador entra a un bar y pide 0.5 cervezas."
        with mock.patch.object(server.brain, "provider", lambda: "openai"):
            got = self.turno("abre youtube y cuéntame un chiste")
        tipos = [m["type"] for m in got]
        self.assertEqual(["effect", "state", "assistant_message", "status"], tipos)
        mensaje = [m for m in got if m["type"] == "assistant_message"][0]["text"]
        self.assertIn("Abriendo YouTube", mensaje)
        self.assertIn("chiste", mensaje)

    def test_sin_nube_el_cabo_se_dice_con_la_letra(self):
        got = self.turno("abre youtube y cuéntame un chiste")
        mensaje = [m for m in got if m["type"] == "assistant_message"][0]["text"]
        self.assertIn("Abriendo YouTube", mensaje)
        self.assertIn("no supe cómo hacer: cuéntame un chiste", mensaje)
        # y el modelo local no se llama ni una vez: el turno no cuesta 60 segundos
        self.assertNotIn("state", [m["type"] for m in got])


class TestAlarmasQueSuenan(Base):
    def test_lo_vencido_se_avisa_al_conectar(self):
        self.ag.agregar("alarma", datetime.now() - timedelta(minutes=30), "gimnasio")
        with self.client.websocket_connect("/ws") as ws:
            self.handshake(ws)
            alarma = ws.receive_json()
        self.assertEqual((alarma["type"], alarma["texto"], alarma["atrasada"]), ("alarm", "gimnasio", True))
        self.assertEqual(self.ag.pendientes(), [], "entregada: no suena otra vez")

    def test_sin_nadie_conectado_queda_pendiente(self):
        self.ag.agregar("alarma", datetime.now() - timedelta(minutes=1), "x")
        asyncio.run(server._entregar_vencidos())
        self.assertEqual(len(self.ag.pendientes()), 1, "no se da por entregada una alarma que nadie oyó")

    def test_se_entrega_a_todas_las_pestañas(self):
        class Sock:
            def __init__(self):
                self.recibido = []

            async def send_json(self, m):
                self.recibido.append(m)
        a, b = Sock(), Sock()
        self.ag.agregar("recordatorio", datetime.now() - timedelta(seconds=5), "pan")
        with mock.patch.object(server, "CONEXIONES", {a, b}):
            asyncio.run(server._entregar_vencidos())
        self.assertEqual([m["texto"] for m in a.recibido], ["pan"])
        self.assertEqual([m["texto"] for m in b.recibido], ["pan"])

    def test_el_vigilante_despierta_a_la_hora(self):
        class Sock:
            def __init__(self):
                self.recibido = []

            async def send_json(self, m):
                self.recibido.append(m)
        sock = Sock()

        async def prueba():
            self.ag.agregar("alarma", datetime.now() + timedelta(seconds=1), "ahora")
            evento = asyncio.Event()
            tarea = asyncio.create_task(server._vigilar_agenda(evento))
            for _ in range(60):
                await asyncio.sleep(0.05)
                if sock.recibido:
                    break
            tarea.cancel()
        with mock.patch.object(server, "CONEXIONES", {sock}):
            asyncio.run(prueba())
        self.assertEqual([m["texto"] for m in sock.recibido], ["ahora"])

    def test_con_la_agenda_vacia_el_vigilante_no_gira(self):
        async def prueba():
            evento = asyncio.Event()
            tarea = asyncio.create_task(server._vigilar_agenda(evento))
            await asyncio.sleep(0.3)
            estado = tarea.done()
            tarea.cancel()
            return estado
        self.assertFalse(asyncio.run(prueba()))
        self.assertIsNone(self.ag.segundos_hasta_proximo(datetime.now()), "nada que esperar: duerme hasta que lo despierten")


if __name__ == "__main__":
    unittest.main()
