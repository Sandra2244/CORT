"""El planificador: un mensaje puede pedir varias cosas, y CORT las hace una por una.

Regla 6 de `AGENTS.md` y por eso estas pruebas son el corazón del módulo: el
planificador **no inventa acciones**, sólo parte la frase y reparte lo que ya
estaba en la tabla cerrada de `intents.py`. Un paso que no casa con esa tabla no
existe, y el texto sigue su camino al LLM.

Nada de aquí ejecuta nada: `actions.perform` es el que ejecuta y comprueba, y se
prueba en `test_actions.py`. Aquí se prueba la descomposición y lo que se dice
después de haberla hecho.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from cort_core import intents
from cort_core import planner


class TestSegmentar(unittest.TestCase):
    def test_dos_ordenes_unidas_por_y(self):
        pasos = intents.match_all("sube el volumen y haz una captura")
        self.assertEqual([p["action"] for p in pasos], ["volume", "screenshot"])

    def test_el_orden_es_el_de_la_frase_no_el_de_la_tabla(self):
        # En la tabla `screenshot` va antes que `volume`; en la frase no.
        self.assertEqual([p["action"] for p in intents.match_all(
            "baja el volumen y captura la pantalla")], ["volume", "screenshot"])

    def test_luego_y_despues_tambien_separan(self):
        for conector in ("luego", "después", "despues", "entonces", "además"):
            with self.subTest(conector=conector):
                pasos = intents.match_all(f"abre la terminal {conector} sube el volumen")
                self.assertEqual([p["action"] for p in pasos], ["launch", "volume"])

    def test_coma_y_punto_y_coma(self):
        self.assertEqual(len(intents.match_all("sube el volumen; baja el volumen")), 2)
        self.assertEqual(len(intents.match_all("captura, pausa la música")), 2)

    def test_una_sola_orden_da_un_solo_paso(self):
        self.assertEqual(intents.match_all("sube el volumen"), [{"action": "volume", "delta": 10}])

    def test_la_charla_no_produce_plan(self):
        self.assertEqual(intents.match_all("cuéntame qué tiempo hace mañana"), [])

    def test_la_mitad_charla_y_la_mitad_orden_saca_lo_que_hay(self):
        pasos = intents.match_all("qué hora es y sube el volumen")
        self.assertEqual([p["action"] for p in pasos], ["volume"])

    def test_el_verbose_hereda_cuando_el_segmento_solo_nombra_una_app(self):
        """«abre la terminal y el gestor de archivos»: el segundo tramo no tiene
        verbo. Sin heredarlo, el paso se perdería y CORT prometería dos cosas que
        no hace."""
        pasos = intents.match_all("abre la terminal y el gestor de archivos")
        self.assertEqual(pasos, [{"action": "launch", "app": "terminal"},
                                 {"action": "launch", "app": "archivos"}])

    def test_heredar_no_abre_la_tabla(self):
        """La heredación vuelve a pasar por los mismos patrones: «el editor de
        video» no está en la lista y no se cuela por llevar el verbo delante."""
        self.assertEqual(intents.match_all("abre la terminal y el editor de video"),
                         [{"action": "launch", "app": "terminal"}])

    def test_duplicado_exacto_no_se_repite(self):
        self.assertEqual(intents.match_all("sube el volumen y sube el volumen"),
                         [{"action": "volume", "delta": 10}])

    def test_dos_deltas_distintos_si_son_dos_pasos(self):
        pasos = intents.match_all("sube el volumen y baja el volumen")
        self.assertEqual([p["delta"] for p in pasos], [10, -10])

    def test_tope_de_pasos(self):
        larga = " y ".join(["sube el volumen"] * 2 + ["haz una captura",
                                                     "abre la terminal", "pausa la música",
                                                     "baja el volumen"])
        self.assertEqual(len(intents.match_all(larga)), intents.PASOS_MAX)

    def test_texto_vacio_y_basura_no_rompen(self):
        for bicho in ("", "   ", None, 42, "!!!", "y" * 30):
            with self.subTest(texto=bicho):
                self.assertIsInstance(intents.match_all(bicho), list)

    def test_mayusculas_y_acentos(self):
        self.assertEqual(len(intents.match_all("SUBE EL VOLUMEN Y TOMA UNA CAPTURA")), 2)

    def test_match_intent_no_cambia(self):
        """Regresión: `match_intent` sigue siendo la primera que casa. El camino
        de un solo paso no se toca, así que ninguna frase que funcionaba ayer
        cambia de comportamiento hoy."""
        self.assertEqual(intents.match_intent("haz una captura y abre archivos")["action"],
                         "screenshot")


class TestEtiqueta(unittest.TestCase):
    def test_cada_accion_se_nombre_sola(self):
        casos = {
            ("volume", 10): "subir el volumen",
            ("volume", -10): "bajar el volumen",
            ("volume", 0): "mover el volumen",
            ("screenshot", None): "la captura de pantalla",
            ("launch", "terminal"): "abrir la terminal",
            ("launch", "archivos"): "abrir el gestor de archivos",
            ("media", "play"): "reanudar la reproducción",
            ("media", "pause"): "pausar la reproducción",
            ("media", "next"): "pasar a la siguiente pista",
            ("equalizer", None): "el ecualizador",
        }
        for (accion, dato), esperado in casos.items():
            with self.subTest(accion=accion, dato=dato):
                intent = {"action": accion}
                if accion == "volume":
                    intent["delta"] = dato
                elif dato is not None:
                    intent["app" if accion == "launch" else "cmd"] = dato
                self.assertEqual(planner.etiqueta(intent), esperado)

    def test_una_accion_que_no_conoce_no_explota(self):
        self.assertEqual(planner.etiqueta({"action": "borrar-disco"}), "borrar-disco")
        self.assertEqual(planner.etiqueta({}), "")

    def test_la_lista_cerrada_es_la_que_se_nombre(self):
        """Las etiquetas salen de los mismos intents que puede producir la tabla:
        si mañana hay una acción nueva sin etiqueta, esta prueba lo nota."""
        for intent in intents.match_all("abre la terminal y sube el volumen y "
                                        "haz una captura y pausa la música"):
            self.assertTrue(planner.etiqueta(intent))


class TestResumen(unittest.TestCase):
    def test_todos_hechos(self):
        r = planner.resumen([("subir el volumen", True, ""),
                             ("la captura de pantalla", True, "")])
        self.assertEqual(r, "2 de 2 pasos hechos: subir el volumen, la captura de pantalla")

    def test_parcial_dice_lo_que_fallo_y_por_que(self):
        r = planner.resumen([("subir el volumen", True, ""),
                             ("abrir la terminal", False, "no llegó a arrancar")])
        self.assertEqual(r, "1 de 2 pasos hechos: subir el volumen. "
                            "No pude: abrir la terminal (no llegó a arrancar)")

    def test_ninguno(self):
        r = planner.resumen([("abrir la terminal", False, "no está instalado"),
                             ("subir el volumen", False, "sigue en 100 %")])
        self.assertEqual(r, "0 de 2 pasos hechos. No pude: abrir la terminal (no está instalado), "
                            "subir el volumen (sigue en 100 %)")

    def test_un_motivo_vacio_no_deja_parentesis_suelto(self):
        self.assertEqual(planner.resumen([("la captura de pantalla", False, "")]),
                         "0 de 1 paso hecho. No pude: la captura de pantalla")

    def test_sin_pasos_no_hay_frase(self):
        self.assertEqual(planner.resumen([]), "")

    def test_un_paso_se_dice_en_singular(self):
        self.assertEqual(planner.resumen([("subir el volumen", True, "")]),
                         "1 de 1 paso hecho: subir el volumen")

    def test_es_plan(self):
        self.assertFalse(planner.es_plan([]))
        self.assertFalse(planner.es_plan([{"action": "volume", "delta": 10}]))
        self.assertTrue(planner.es_plan([{"action": "volume"}, {"action": "media"}]))


class TestQueNoHayHerramientasSueltas(unittest.TestCase):
    def test_el_planificador_no_tiene_camino_al_shell(self):
        """Regla 6, medida sobre el módulo y no sobre la buena voluntad: `planner`
        no importa `subprocess` ni `asyncio.create_subprocess`, y no construye
        argv a partir de texto."""
        fuente = pathlib.Path(planner.__file__).read_text(encoding="utf-8")
        for prohibido in ("subprocess", "create_subprocess", "os.system", "eval(", "exec("):
            self.assertNotIn(prohibido, fuente)

    def test_un_texto_que_pide_comandos_no_aparece_en_el_plan(self):
        """El ataque obvio: meter una orden de shell dentro de la frase. El
        planificador no tiene ninguna acción para «rm», así que devuelve una
        lista vacía y el texto va al LLM, que tampoco tiene manos."""
        for frase in ("rm -rf / y sube el volumen",
                      "; rm -rf /",
                      "ejecuta sudo shutdown ahora y captura"):
            with self.subTest(frase=frase):
                pasos = intents.match_all(frase)
                for p in pasos:
                    self.assertIn(p["action"], ("volume", "screenshot", "launch",
                                               "media", "equalizer"))


if __name__ == "__main__":
    unittest.main()
