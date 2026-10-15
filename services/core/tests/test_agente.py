"""Pruebas del bucle del agente (`agente.py`): proponer → ejecutar → medir → seguir.

Nada de aquí toca el sistema: el modelo es un guion y el ejecutor una lista. Lo
que se prueba es la **forma del lazo** —cuántas veces se llama al modelo, qué le
vuelve después de cada paso, cuándo se corta—, que es justo lo que no existía.
"""
import ast
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from cort_core import agente
from cort_core.intents import PASOS_MAX


class Guion:
    """Modelo de prueba: devuelve respuestas en orden y guarda lo que le preguntaron."""

    def __init__(self, respuestas, final="Terminado."):
        self.respuestas = list(respuestas)
        self.final = final
        self.ve = []

    async def think(self, history):
        self.ve.append([dict(m) for m in history])
        return self.respuestas.pop(0) if self.respuestas else self.final


class Ejecutor:
    """Ejecutor de prueba: anota lo que le tocó y responde lo que se le pacte."""

    def __init__(self, resultados=None):
        self.hechas = []
        self.resultados = resultados or {}

    async def __call__(self, llamada):
        self.hechas.append(llamada)
        return self.resultados.get(len(self.hechas), (True, "hecho."))


def spotify(q):
    return '{"herramienta": "spotify", "args": {"consulta": "%s"}}' % q


class TestConversacion(unittest.IsolatedAsyncioTestCase):
    async def test_texto_normal_sale_tal_cual_y_no_se_ejecuta_nada(self):
        guion, eje = Guion(["Con gusto. ¿Jazz o clásica?"]), Ejecutor()
        dicho, hechos = await agente.turno([{"role": "user", "content": "hola"}],
                                           think=guion.think, ejecutar=eje)
        self.assertEqual(dicho, "Con gusto. ¿Jazz o clásica?")
        self.assertEqual((hechos, eje.hechas, len(guion.ve)), ([], [], 1))


class TestUnPaso(unittest.IsolatedAsyncioTestCase):
    async def test_una_llamada_se_ejecuta_y_su_resultado_vuelve_al_modelo(self):
        guion = Guion([spotify("bach"), "Ya está."])
        eje = Ejecutor({1: (True, "Abrí Spotify con la búsqueda «bach».")})
        dicho, hechos = await agente.turno([{"role": "user", "content": "pon bach"}],
                                           think=guion.think, ejecutar=eje)
        self.assertEqual(len(eje.hechas), 1)
        self.assertEqual(dicho, "Abrí Spotify con la búsqueda «bach».")
        self.assertEqual(hechos, [("buscar en Spotify", True,
                                   "Abrí Spotify con la búsqueda «bach».")])
        # el segundo turno del modelo vio el resultado medido, no su promesa
        segunda = guion.ve[1]
        self.assertEqual(segunda[-1]["role"], "user")
        self.assertIn("Resultado de «buscar en Spotify»: hecho", segunda[-1]["content"])
        self.assertEqual(segunda[-2]["role"], "assistant")


class TestVariosPasos(unittest.IsolatedAsyncioTestCase):
    async def test_dos_turnos_del_modelo_dos_herramientas_y_un_recuento(self):
        guion = Guion([spotify("bach"), '{"herramienta": "nota", "args": {"texto": "pan"}}',
                       "Listo."])
        eje = Ejecutor()
        dicho, hechos = await agente.turno([{"role": "user", "content": "x"}],
                                           think=guion.think, ejecutar=eje)
        self.assertEqual([c["herramienta"] for c in eje.hechas], ["spotify", "nota"])
        self.assertTrue(dicho.startswith("2 de 2 pasos hechos"), dicho)
        # la prosa final del modelo NO pisa el recuento medido
        self.assertNotIn("Listo", dicho)

    async def test_dos_json_en_una_sola_respuesta_se_ejecutan_los_dos(self):
        guion = Guion([spotify("bach") + " y " + '{"herramienta": "hora", "args": {}}',
                       "Listo."])
        eje = Ejecutor()
        dicho, hechos = await agente.turno([{"role": "user", "content": "x"}],
                                           think=guion.think, ejecutar=eje)
        self.assertEqual([c["herramienta"] for c in eje.hechas], ["spotify", "hora"])
        self.assertTrue(dicho.startswith("2 de 2"), dicho)


class TestGuardas(unittest.IsolatedAsyncioTestCase):
    async def test_el_tope_es_PASOS_MAX_llamadas_y_ese_mismo_de_turnos(self):
        n = PASOS_MAX + 3
        guion = Guion([spotify(f"pista {i}") for i in range(n)], final="sigue el JSON")
        eje = Ejecutor()
        dicho, hechos = await agente.turno([{"role": "user", "content": "x"}],
                                           think=guion.think, ejecutar=eje)
        self.assertEqual(len(eje.hechas), PASOS_MAX)
        self.assertEqual(len(guion.ve), PASOS_MAX)
        self.assertTrue(dicho.startswith(f"{PASOS_MAX} de {PASOS_MAX}"), dicho)

    async def test_una_llamada_repetida_no_se_ejecuta_dos_veces(self):
        # el modelo terco: el mismo JSON en cada turno, hasta el final del guion
        guion = Guion([spotify("bach"), spotify("bach"), spotify("bach")])
        eje = Ejecutor()
        dicho, hechos = await agente.turno([{"role": "user", "content": "x"}],
                                           think=guion.think, ejecutar=eje)
        self.assertEqual(len(eje.hechas), 1)
        self.assertEqual(len(hechos), 1)
        self.assertEqual(dicho, "hecho.")


class TestRechazoYReparacion(unittest.IsolatedAsyncioTestCase):
    async def test_una_herramienta_inventada_no_toca_nada_y_se_dice_como_antes(self):
        guion = Guion(['{"herramienta": "formatear_disco", "args": {"unidad": "C:"}}'])
        eje = Ejecutor()
        dicho, hechos = await agente.turno([{"role": "user", "content": "x"}],
                                           think=guion.think, ejecutar=eje)
        self.assertEqual(eje.hechas, [])
        self.assertTrue(dicho.startswith("No pude hacer eso"), dicho)
        self.assertFalse(hechos[0][1])

    async def test_el_motivo_del_rechazo_vuelve_al_modelo_y_puede_corregir(self):
        guion = Guion(['{"herramienta": "alarma", "args": {}}',
                       spotify("bach"), "Listo."])
        eje = Ejecutor()
        dicho, hechos = await agente.turno([{"role": "user", "content": "x"}],
                                           think=guion.think, ejecutar=eje)
        self.assertIn("falta «cuando»", guion.ve[1][-1]["content"])
        self.assertEqual([c["herramienta"] for c in eje.hechas], ["spotify"])
        self.assertTrue(dicho.startswith("1 de 2"), dicho)


class TestQueNoHayCaminoAlSistema(unittest.TestCase):
    def test_el_fuente_no_tiene_nada_de_ejecucion(self):
        """Regla 6: este módulo enlaza, no ejecuta. Como en `test_planner`, se
        lee el fuente y se cierra por AST: ni `subprocess`, ni `os.system`,
        ni `eval`. Lo del mundo exterior entra sólo por `ejecutar`, inyectado."""
        fuente = pathlib.Path(agente.__file__).read_text(encoding="utf-8")
        árbol = ast.parse(fuente)
        importados = set()
        for nodo in ast.walk(árbol):
            if isinstance(nodo, ast.Import):
                importados.update(a.name.split(".")[0] for a in nodo.names)
            elif isinstance(nodo, ast.ImportFrom):
                importados.add((nodo.module or "").split(".")[0])
        self.assertNotIn("subprocess", importados)
        self.assertNotIn("os", importados)
        for v in ("system", "popen", "eval", "exec"):
            self.assertNotIn(v + "(", fuente)


if __name__ == "__main__":
    unittest.main()
