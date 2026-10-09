"""Pruebas de la iniciativa (`cort_core/initiative.py`) y de su reloj en el server.

Lo que se comprueba aquí es una frontera, no un acierto de conversación: CORT
puede hablar primero, pero **no puede ejecutar nada** por su cuenta. De ahí que la
última clase lea el fuente del módulo buscando `subprocess` —es la regla 6 de
`AGENTS.md` vuelta prueba, y la única forma de que se note el día que alguien la
añada sin pensar.

Nada de esto enciende Ollama ni abre navegador. Las reglas son comparaciones de
números, y el bucle se prueba con un socket de mentira y centésimas de segundo:
una prueba que esperara treinta segundos reales sería una prueba que nadie ejecuta.
"""
import asyncio
import ast
import dataclasses
import inspect
import os
import pathlib
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from cort_core import initiative, server, weather
from cort_core.memory.store import MemoryStore
from cort_core.server import app


def momento(hora: int = 13, temp_c=None, recuerdos: int = 1) -> initiative.Momento:
    """Momento con defaults que **no** disparan ninguna regla: la hora 13 no está
    en madrugada, ni de café, ni de «es tarde», y hay recuerdos guardados."""
    return initiative.Momento(hora=hora, temp_c=temp_c, recuerdos=recuerdos)


def nuevo_store() -> MemoryStore:
    return MemoryStore(pathlib.Path(tempfile.mkdtemp(prefix="cort-init-")) / "memory.db")


class TestReglas(unittest.TestCase):
    """Las reglas puras: sin socket, sin reloj de verdad, sin red."""

    def test_sin_nombre_es_lo_primero(self):
        # Gana sobre el frío aunque el frío también se cumpla: es lo único que se
        # dice una vez en la vida de la base, y retrasarlo sería dejarla muda.
        s = initiative.sugerir(momento(hora=3, temp_c=5.0, recuerdos=0), set())
        self.assertEqual("sin_nombre", s.clave)

    def test_frío_por_debajo_del_umbral(self):
        self.assertEqual("frio", initiative.sugerir(momento(temp_c=11.9), set()).clave)

    def test_el_umbral_de_frío_incluye(self):
        self.assertEqual("frio", initiative.sugerir(momento(temp_c=initiative.FRIO_C), set()).clave)

    def test_calor_por_encima_del_umbral(self):
        self.assertEqual("calor", initiative.sugerir(momento(temp_c=28.1), set()).clave)
        self.assertEqual("calor", initiative.sugerir(momento(temp_c=initiative.CALOR_C), set()).clave)

    def test_temperatura_templada_no_molesta(self):
        self.assertIsNone(initiative.sugerir(momento(temp_c=20.0), set()))

    def test_sin_clima_medido_no_hay_consejo_de_abrigo(self):
        """El caso que separa un aviso de una invención: sin ciudad configurada no
        se dice nada de temperatura, aunque el `.env` traiga 22° de reserva."""
        self.assertIsNone(initiative.sugerir(momento(temp_c=None), set()))

    def test_reglas_del_reloj(self):
        for hora, clave in [(0, "madrugada"), (3, "madrugada"), (4, "madrugada"),
                            (6, "cafete"), (7, "cafete"), (9, "cafete"),
                            (22, "tarde"), (23, "tarde")]:
            with self.subTest(hora=hora):
                self.assertEqual(clave, initiative.sugerir(momento(hora=hora), set()).clave)

    def test_la_misma_regla_no_se_dice_dos_vez(self):
        m = momento(temp_c=5.0)
        self.assertEqual("frio", initiative.sugerir(m, set()).clave)
        self.assertIsNone(initiative.sugerir(m, {"frio"}))

    def test_agotadas_las_reglas_calla(self):
        # A las 7 con 30° se cumplen «calor» y «cafete»; dichas las dos, el bucle
        # tiene que devolver None y no inventarse un tema.
        self.assertIsNone(initiative.sugerir(momento(hora=7, temp_c=30.0), {"calor", "cafete"}))

    def test_una_sugerencia_solo_lleva_texto(self):
        """La prueba de la frontera: una sugerencia tiene dos campos y ambos son
        cadena. No hay sitio donde meter una orden."""
        campos = dataclasses.fields(initiative.Sugerencia)
        self.assertEqual({"clave", "texto"}, {f.name for f in campos})
        self.assertTrue(all(f.type == "str" for f in campos))
        self.assertIsInstance(initiative.sugerir(momento(temp_c=5.0), set()).texto, str)


class TestConfig(unittest.TestCase):
    def test_apagador_por_variable(self):
        with mock.patch.dict(os.environ, {"CORT_INITIATIVE": "0"}):
            self.assertFalse(initiative.enabled())
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(initiative.enabled())

    def test_solo_el_cero_apaga(self):
        """`false`, `off` y el vacío **no** apagan: el contrato es el literal `0`,
        el mismo que usa la capa de permisos. Documentarlo aquí es para que nadie
        lo cambie a un `if not valor` y deje el apagador a medias."""
        for valor in ("false", "off", "", "NO"):
            with self.subTest(valor=valor), mock.patch.dict(os.environ, {"CORT_INITIATIVE": valor}):
                self.assertTrue(initiative.enabled())

    def test_cort_now_domina_la_hora(self):
        with mock.patch.dict(os.environ, {"CORT_NOW": "3"}):
            self.assertEqual(3, initiative.ahora(1, None).hora)
        with mock.patch.dict(os.environ, {"CORT_NOW": " 22 "}):
            self.assertEqual(22, initiative.ahora(1, None).hora)

    def test_cort_now_basura_no_rompe_el_reloj(self):
        # «25» y «abc» no son horas: se ignora el override y manda el reloj real,
        # que siempre está entre 0 y 23. No es un fallo, es una pifia tecleada.
        for basura in ("25", "abc", "-1", "12:00"):
            with self.subTest(basura=basura), mock.patch.dict(os.environ, {"CORT_NOW": basura}):
                self.assertTrue(0 <= initiative.ahora(1, None).hora <= 23)

    def test_ahora_lleva_lo_que_se_le_da(self):
        with mock.patch.dict(os.environ, {"CORT_NOW": "13"}):
            m = initiative.ahora(recuerdos=17, temp_c=9.5)
        self.assertEqual((13, 9.5, 17), (m.hora, m.temp_c, m.recuerdos))


class SocketFalso:
    """Un lazo que acumula cuadros en vez de enviarlos, para poder leerlos después.

    `send_json` es `async` porque el bucle lo.awaita: si fuera síncrona el `await`
    daría `TypeError` y la prueba se rompería por el sitio equivocado.
    """

    def __init__(self):
        self.cuadros: list[dict] = []

    async def send_json(self, cuadro: dict) -> None:
        self.cuadros.append(cuadro)

    def proactive(self) -> list[dict]:
        return [c for c in self.cuadros if c.get("type") == "proactive"]


class TestBucle(unittest.IsolatedAsyncioTestCase):
    """El turno de reloj real: `_cuidar_iniciativa` con intervalos de centésimas.

    Se parchea `server.memory` por una base en `/tmp`: el módulo importa un store
    apuntando a `data/memory.db`, y una prueba que lo usara escribiría —o leería—
    los recuerdos reales de esta máquina.
    """

    def setUp(self):
        self.store = nuevo_store()
        self.addCleanup(self.store.close)
        self.memoria = mock.patch.object(server, "memory", self.store)
        self.memoria.start()
        # CORT_NOW=13 deja **una sola** regla viva (la de no saber el nombre) con
        # la base vacía: así «no repite» se puede probar contando cuadros.
        self.entorno = mock.patch.dict(os.environ, {"CORT_NOW": "13", "CORT_INITIATIVE": "1"})
        self.entorno.start()
        # Sin ciudad configurada no hay clima, y el clima real dependería de la red.
        self.clima = mock.patch.object(weather, "snapshot", return_value=None)
        self.clima.start()
        self.intervalo = mock.patch.object(server, "INICIATIVA_S", 0.02)
        self.intervalo.start()
        self.silencio = mock.patch.object(server, "INICIATIVA_QUIET_S", 0.0)
        self.silencio.start()
        self.addCleanup(mock.patch.stopall)

    async def correr(self, actividad: dict, *, esperar: float = 0.4) -> SocketFalso:
        sock = SocketFalso()
        tarea = asyncio.create_task(server._cuidar_iniciativa(sock, actividad))
        try:
            await asyncio.sleep(esperar)
        finally:
            tarea.cancel()
            await asyncio.gather(tarea, return_exceptions=True)
        return sock

    async def test_habla_una_vez_y_no_repite(self):
        sock = await self.correr({"ultimo": time.monotonic()})
        cuadros = sock.proactive()
        self.assertTrue(cuadros, "con la base vacía tiene que proponer el nombre")
        self.assertEqual("sin_nombre", cuadros[0]["clave"])
        self.assertEqual(len(cuadros), 1, f"dichas deduplica, llegó {len(cuadros)}")
        self.assertEqual("calm", cuadros[0]["mood"])
        self.assertIsInstance(cuadros[0]["text"], str)

    async def test_no_habla_mientras_la_usuaria_espera_su_turno(self):
        """El marcador `ocupada`: con Ollama tardando entre 15 y 60 s medidos, un
        «¿café?» colado delante de la respuesta es el fallo que esta prueba cierra."""
        sock = await self.correr({"ultimo": time.monotonic() - 99, "ocupada": True})
        self.assertEqual([], sock.proactive())

    async def test_respeta_la_ventana_de_silencio(self):
        # Acaba de hablar: con INICIATIVA_QUIET_S grande no es su turno todavía.
        with mock.patch.object(server, "INICIATIVA_QUIET_S", 60.0):
            sock = await self.correr({"ultimo": time.monotonic()})
        self.assertEqual([], sock.proactive())

    async def test_habla_en_cuanto_vence_el_silencio(self):
        sock = await self.correr({"ultimo": time.monotonic() - 61})
        self.assertEqual(1, len(sock.proactive()))

    async def test_apagada_no_arranca_siquiera(self):
        with mock.patch.dict(os.environ, {"CORT_INITIATIVE": "0"}):
            sock = SocketFalso()
            tarea = asyncio.create_task(server._cuidar_iniciativa(sock, {"ultimo": time.monotonic()}))
            await asyncio.gather(tarea, return_exceptions=True)
        self.assertTrue(tarea.done(), "con el apagador sale al instante, sin dormir 30 s")
        self.assertEqual([], sock.cuadros)

    async def test_intervalo_cero_es_apagador(self):
        """`CORT_INITIATIVE_INTERVAL_S=0` no puede convertirse en un bucle cerrado
        girando a tope: 2 núcleos no perdonan un `while True` sin dormir."""
        with mock.patch.object(server, "INICIATIVA_S", 0.0):
            sock = await self.correr({"ultimo": time.monotonic()}, esperar=0.1)
        self.assertEqual([], sock.cuadros)

    async def test_sin_recuerdos_ni_clima_el_unico_tema_es_el_nombre(self):
        self.store.remember("El usuario se llama Sandra")
        sock = await self.correr({"ultimo": time.monotonic()})
        self.assertEqual([], sock.proactive(), "a las 13 con nombre no hay nada que decir")


class TestMontaje(unittest.TestCase):
    """Que `ws()` arranque el reloj con cada conexión y lo apague con ella.

    Aquí no se prueba ninguna regla —eso ya está en `TestBucle`—, sino el cable:
    que el cuadro `proactive` sale por el mismo WebSocket que los demás y que la
    tarea muere con la pestaña. Se sustituye el bucle entero por uno de mentira
    que habla al instante, porque un `receive_json` esperando un cuadro que puede
    no llegar es un test que cuelga la suite entera en vez de fallar.
    """

    def test_reloj_nace_y_morre_con_la_conexion(self):
        from fastapi.testclient import TestClient

        marca: list[str] = []

        async def reloj_falso(sock, actividad):
            try:
                await sock.send_json({"type": "proactive", "text": "marca de prueba",
                                      "mood": "calm", "clave": "prueba"})
                while True:
                    await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                marca.append("cancelada")
                raise

        with mock.patch.object(server, "_cuidar_iniciativa", reloj_falso):
            with TestClient(app) as cliente:
                with cliente.websocket_connect("/ws") as ws:
                    tipos = [ws.receive_json()["type"] for _ in range(4)]
                # Fuera del `with` la conexión está cerrada; el bucle del portal
                # corre en otro hilo, así que la cancelación se recoge un instante
                # después y no en el mismo saltito del `with`.
                time.sleep(0.1)
            self.assertIn("proactive", tipos)
            # El orden de los tres primeros es el contrato del arranque, pero la
            # tarea del reloj se crea **antes** del primer `send_json`: el cuadro
            # propio puede colarse en cualquier hueco. Se quita y se comprueba el
            # resto, que es lo que la interfaz necesita.
            self.assertEqual(["state", "greeting", "status"], [t for t in tipos if t != "proactive"])
            self.assertEqual(["cancelada"], marca, "una tarea suelta por pestaña cerrada se acumula de por vida")


class TestFronteraSeguridad(unittest.TestCase):
    """Que la iniciativa sea sólo texto se comprueba en el **árbol de sintaxis**,
    porque es la promesa y no el comportamiento visible.

    Un `import actions` aquí dentro pasaría todas las demás pruebas y rompería la
    regla 6 de `AGENTS.md` en el primer merge. Se mira el AST y no el texto: la
    palabra `subprocess` aparece en el docstring del módulo explicando que no está,
    y un `assertNotIn` sobre la fuente daría falso positivo contra la propia
    disculpa.
    """

    @staticmethod
    def _llamadas(codigo: ast.AST) -> set[str]:
        """Nombres de llamada punteados (`sock.send_json`), ignorando lo que no se
        pueda escribir como nombre (`(lambda: …)()`, decoradores, compresiones)."""
        out = set()
        for nodo in ast.walk(codigo):
            if not isinstance(nodo, ast.Call):
                continue
            partes, f = [], nodo.func
            while isinstance(f, ast.Attribute):
                partes.append(f.attr)
                f = f.value
            if isinstance(f, ast.Name):
                partes.append(f.id)
                out.add(".".join(reversed(partes)))
        return out

    @staticmethod
    def _importes(codigo: ast.AST) -> set[str]:
        out = set()
        for nodo in ast.walk(codigo):
            if isinstance(nodo, ast.Import):
                out |= {a.name.split(".")[0] for a in nodo.names}
            elif isinstance(nodo, ast.ImportFrom):
                out.add((nodo.module or "").split(".")[0])
        return out

    def test_el_modulo_no_puede_ejecutar_nada(self):
        arbol = ast.parse(inspect.getsource(initiative))
        # Lista cerrada de imports: si alguien añade `actions` o `subprocess`, esta
        # línea es la que se queja, y se queja antes del merge que del usuario.
        self.assertEqual({"__future__", "os", "re", "dataclasses", "datetime"},
                         self._importes(arbol))
        prohibidas = {"os.system", "os.popen", "os.execv", "os.spawnl", "subprocess.run",
                      "subprocess.Popen", "eval", "exec", "compile", "__import__", "open"}
        self.assertEqual(set(), self._llamadas(arbol) & prohibidas)

    def test_el_reloj_del_server_tampoco(self):
        # `_cuidar_iniciativa` es el trozo que vive atado a una conexión abierta, y
        # su única salida permitida es un cuadro de WebSocket: igualar la lista a
        # mano obliga a quien la amplíe a pasar por aquí y pensarlo dos veces.
        arbol = ast.parse(inspect.getsource(server._cuidar_iniciativa)).body[0]
        self.assertEqual(
            {"initiative.enabled", "asyncio.sleep", "actividad.get", "time.monotonic",
             "weather.snapshot", "initiative.ahora", "memory.count", "initiative.sugerir",
             "dichas.add", "sock.send_json", "set"},
            self._llamadas(arbol),
        )
        self.assertNotIn("perform", " ".join(self._llamadas(arbol)))


if __name__ == "__main__":
    unittest.main()
