"""Pruebas del temporizador: la cuenta atrás que sólo existe cuando se pide.

Tres frentes:

1. **Parsear** — que «1 hora y 15 minutos» sean 4500 s y no 1, y que un número
   suelto sin palabra de pedir no arranque nada.
2. **Contar** — cuántos cuadros salen y con qué números, con `PASO_S` en
   centésimas. Una prueba que esperara el minuto real sería una prueba que nadie
   ejecuta.
3. **El cable** — que el cuadro `timer` sale por el WebSocket, que «cancela»
   apaga la tarea de verdad, y que la cuenta muere con la conexión. La tarea se
   sustituye por una de mentira que deja marca al morir: es la única forma de
   comprobar que no queda ninguna suelta, que en esta máquina (2 núcleos, 1,8 GiB)
   es justo el punto de la función.

Nada de esto toca Ollama ni ejecuta un comando del sistema.
"""
import ast
import asyncio
import inspect
import pathlib
import sys
import time
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from cort_core import server, timer
from cort_core.server import app


class TestParse(unittest.TestCase):
    def test_una_unidad_sencilla(self):
        self.assertEqual(300, timer.parse("pon un temporizador de 5 minutos"))

    def test_las_piezas_se_suman(self):
        """El error fácil era usar `search` y quedarse con el primer número: eso
        daría 1 minuto."""
        self.assertEqual(4500, timer.parse("cuenta atrás de 1 hora y 15 minutos"))

    def test_la_coma_es_decimal(self):
        self.assertEqual(150, timer.parse("temporizador de 2,5 minutos"))

    def test_sin_palabra_de_pedir_no_hay_temporizador(self):
        """«5 minutos» suelto es un trozo de conversación, no una orden. Adivinar
        aquí sería peor que callar."""
        self.assertIsNone(timer.parse("5 minutos"))
        self.assertIsNone(timer.parse("hace 3 horas llovió"))

    def test_media_hora_sin_numero(self):
        self.assertEqual(1800, timer.parse("que suene en media hora"))

    def test_un_numero_sin_unidad_no_se_adivina(self):
        self.assertIsNone(timer.parse("temporizador 7"))

    def test_segundos_horas_y_plural(self):
        self.assertEqual(90, timer.parse("temporizador de 90 segundos"))
        self.assertEqual(7200, timer.parse("pon 2 horas de temporizador"))

    def test_cancelar_no_arranca_nada(self):
        """«cancela el temporizador» lleva la palabra mágica pero no cantidad: si
        `parse` devolviera 0 y el server lo aceptara, la usuaria vería una cuenta
        atrás vacía en vez de una cancelada."""
        self.assertIsNone(timer.parse("cancela el temporizador"))


class TestCancelar(unittest.TestCase):
    def test_detecta_las_formas_de_decirlo(self):
        for texto in ("cancela el temporizador", "para la cuenta atrás",
                      "detén la alarma", "olvídalo"):
            self.assertTrue(timer.quiere_cancelar(texto), texto)

    def test_no_casa_lo_que_no_es_cancelar(self):
        for texto in ("sube el volumen", "¿qué tiempo hace?", "temporizador de 5 minutos"):
            self.assertFalse(timer.quiere_cancelar(texto), texto)


class TestTexto(unittest.TestCase):
    def test_una_confirmacion_legible(self):
        self.assertEqual("5 min", timer.texto(300))
        self.assertEqual("1 h 15 min", timer.texto(4500))
        self.assertEqual("45 s", timer.texto(45))
        # Cero segundos no es «sin texto»: un vacío en la burbuja parecería un fallo.
        self.assertEqual("0 s", timer.texto(0))


class TestContar(unittest.IsolatedAsyncioTestCase):
    """`correr` con la función de enviar inyectada y el paso en centésimas: ni
    socket montado ni minuto real esperado."""

    def setUp(self):
        patcher = mock.patch.object(timer, "PASO_S", 0.01)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.cuadros: list[dict] = []

    async def enviar(self, cuadro: dict) -> None:
        self.cuadros.append(cuadro)

    async def test_salen_todos_los_cuadros_y_terminan_en_cero(self):
        self.assertEqual("termina", await timer.correr(self.enviar, 3))
        self.assertEqual([3, 2, 1, 0], [c["restante"] for c in self.cuadros])
        self.assertEqual(["corre"] * 3 + ["termina"], [c["estado"] for c in self.cuadros])
        self.assertTrue(all(c["type"] == "timer" for c in self.cuadros))
        self.assertTrue(all(c["total"] == 3 for c in self.cuadros),
                        "sin `total` la interfaz no puede saber qué porción va gastada")

    async def test_una_cuenta_de_un_segundo_tambien_termina(self):
        await timer.correr(self.enviar, 1)
        self.assertEqual(2, len(self.cuadros))
        self.assertEqual(0, self.cuadros[-1]["restante"])

    async def test_la_cancelacion_se_propaga(self):
        """`correr` no tiene estado que limpiar, así que no debe tragarse
        `CancelledError`: si lo capturara, la tarea seguiría viva mandando cuadros
        a una conexión cerrada."""
        tarea = asyncio.create_task(timer.correr(self.enviar, 3600))
        await asyncio.sleep(0.05)
        tarea.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await tarea
        self.assertTrue(self.cuadros, "debería haber alcanzado a emitir algún cuadro")


def cuenta_espiada(marcas: list[str]):
    """Sustituto de `_correr_cuenta`: emite un cuadro y se queda dormida hasta que
    la cancelen, dejando marca de haber muerto. Con la cuenta de verdad no se
    puede distinguir «la cancelé yo» de «terminó sola»."""

    async def _correr(sock, segundos: int) -> None:
        try:
            await sock.send_json({"type": "timer", "estado": "corre",
                                  "restante": segundos, "total": segundos})
            while True:
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            marcas.append("cancelada")
            raise

    return _correr


class TestCable(unittest.TestCase):
    """El temporizador a través del WebSocket del server.

    Al pedir un temporizador hay **dos** emisores en el lazo: el bucle de la
    conexión (que confirma) y la tarea de la cuenta (que cuenta). Qué cuadro
    llega primero no es contrato de nada, así que se lee el conjunto y se
    comprueban los contenidos. Lo que sí es contrato: que los dos existen, que
    los números bajan y que al final no queda ninguna tarea viva.
    """

    def handshake(self, ws):
        tipos = [ws.receive_json()["type"] for _ in range(3)]
        self.assertEqual(["state", "greeting", "status"], tipos)

    def test_la_cuenta_atras_sale_por_el_cable(self):
        """Con la cuenta de verdad y el paso en centésimas: 3 segundos reales son
        ~0,03 s de suite, y es lo que prueba que `parse`, el server y `correr`
        están conectados y no cada uno por su lado."""
        with mock.patch.object(timer, "PASO_S", 0.01):
            with TestClient(app).websocket_connect("/ws") as ws:
                self.handshake(ws)
                ws.send_json({"type": "user_message", "text": "pon un temporizador de 3 segundos"})
                salida = []
                while True:
                    m = ws.receive_json()
                    salida.append(m)
                    if m.get("type") == "timer" and m.get("estado") == "termina":
                        break
                # El aviso de que se acabó va detrás del último cuadro: la tarea
                # primero emite el cero y luego habla.
                salida += [ws.receive_json() for _ in range(2)]

        confirmacion = [m for m in salida if m["type"] == "assistant_message"]
        self.assertIn("Cuenta atrás de 3 s.", [m["text"] for m in confirmacion])
        cuadros = [m for m in salida if m["type"] == "timer"]
        self.assertEqual([3, 2, 1, 0], [c["restante"] for c in cuadros])
        self.assertEqual("termina", cuadros[-1]["estado"])
        self.assertEqual("Se acabó el tiempo.", confirmacion[-1]["text"])
        self.assertIn("pulse", [m.get("kind") for m in salida if m["type"] == "effect"])

    def test_cancela_apaga_la_tarea_de_verdad(self):
        marcas: list[str] = []
        with mock.patch.object(server, "_correr_cuenta", cuenta_espiada(marcas)):
            with TestClient(app).websocket_connect("/ws") as ws:
                self.handshake(ws)
                ws.send_json({"type": "user_message", "text": "temporizador de 1 hora"})
                arranque = [ws.receive_json() for _ in range(2)]
                self.assertEqual({"timer", "assistant_message"}, {m["type"] for m in arranque})
                ws.send_json({"type": "user_message", "text": "cancela el temporizador"})
                # Dos cuadros y se acabó: el de la cancelación y el aviso. Si la
                # tarea siguiera viva, aquí llegarían más `timer` de cuenta.
                apagado = [ws.receive_json() for _ in range(2)]
                time.sleep(0.1)
        self.assertEqual(["cancelada"], marcas)
        self.assertIn("cancela", [m.get("estado") for m in apagado])
        self.assertIn("Temporizador cancelado.", [m.get("text") for m in apagado])

    def test_la_cuenta_muere_con_la_conexion(self):
        """Sin el `finally` que cancela, una hora de cuenta seguiría emitiendo
        cuadros hacia una pestaña cerrada: CPU y memoria que nadie ve."""
        marcas: list[str] = []
        with mock.patch.object(server, "_correr_cuenta", cuenta_espiada(marcas)):
            with TestClient(app).websocket_connect("/ws") as ws:
                self.handshake(ws)
                ws.send_json({"type": "user_message", "text": "temporizador de 1 hora"})
                tipos = {m["type"] for m in [ws.receive_json() for _ in range(2)]}
                self.assertIn("timer", tipos)
            time.sleep(0.1)
        self.assertEqual(["cancelada"], marcas)

    def test_dos_cuentas_a_la_vez_no_salen_juntas(self):
        marcas: list[str] = []
        with mock.patch.object(server, "_correr_cuenta", cuenta_espiada(marcas)):
            with TestClient(app).websocket_connect("/ws") as ws:
                self.handshake(ws)
                ws.send_json({"type": "user_message", "text": "temporizador de 1 hora"})
                [ws.receive_json() for _ in range(2)]
                ws.send_json({"type": "user_message", "text": "temporizador de 2 minutos"})
                segundo = ws.receive_json()
        self.assertEqual("assistant_message", segundo["type"])
        self.assertIn("Ya hay una cuenta atrás en marcha", segundo["text"])

    def test_sin_cuenta_en_marcha_el_cancela_no_es_del_temporizador(self):
        """«cancela» a secas, sin cuenta atrás, es conversación: tiene que llegar
        al modelo y no producir un «Temporizador cancelado.» falso."""

        async def think_falso(mensajes):
            return "no hay nada que cancelar"

        with mock.patch.object(server, "think", think_falso):
            with TestClient(app).websocket_connect("/ws") as ws:
                self.handshake(ws)
                ws.send_json({"type": "user_message", "text": "cancela"})
                # Un turno de LLM son cuatro cuadros: `state` de pensando, la
                # respuesta, `state` otra vez y `status`.
                salida = [ws.receive_json() for _ in range(4)]
        respuestas = [m["text"] for m in salida if m["type"] == "assistant_message"]
        self.assertEqual(["no hay nada que cancelar"], respuestas)
        self.assertNotIn("Temporizador cancelado.", respuestas)


class TestFronteraSeguridad(unittest.TestCase):
    """El temporizador **no puede ejecutar nada**, y eso se comprueba leyendo el
    módulo en vez de fiarse de su palabra.

    Es la misma razón que en `test_initiative.py`: un `import actions` colado en
    un merge pasaría todas las demás pruebas de este archivo y sólo se vería aquí.
    """

    def imports(self) -> set[str]:
        arbol = ast.parse(inspect.getsource(timer))
        salida: set[str] = set()
        for node in ast.walk(arbol):
            if isinstance(node, ast.Import):
                salida |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                salida.add(node.module or "")
        return salida

    def test_solo_sabe_dormir_y_comparar_numeros(self):
        # `asyncio`, `re` y `typing` no abren un proceso ni un archivo.
        self.assertEqual({"__future__", "asyncio", "re", "typing"}, self.imports())

    def test_no_hay_ninguna_llamada_que_esecute(self):
        arbol = ast.parse(inspect.getsource(timer))
        # Dos formas de llamar mal: la llamada suelta (`eval`, `open`) y la
        # enredada en un módulo (`os.system`). `re.compile` comparte nombre con el
        # peligro y por eso la lista va completa: si no, acusaría al propio `re`.
        sueltas = {node.func.id for node in ast.walk(arbol)
                   if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        prohibidas_sueltas = {"eval", "exec", "compile", "__import__", "open", "input"}
        dotted: set[str] = set()
        for node in ast.walk(arbol):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                cadena, actual = [], node.func
                while isinstance(actual, ast.Attribute):
                    cadena.append(actual.attr)
                    actual = actual.value
                if isinstance(actual, ast.Name):
                    cadena.append(actual.id)
                    dotted.add(".".join(reversed(cadena)))
        prohibidas_dotted = {"os.system", "os.popen", "os.execv", "os.spawnl",
                             "subprocess.run", "subprocess.Popen"}
        self.assertEqual(set(), sueltas & prohibidas_sueltas)
        self.assertEqual(set(), dotted & prohibidas_dotted)


if __name__ == "__main__":
    unittest.main()

