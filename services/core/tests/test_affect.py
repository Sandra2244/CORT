"""El estado afectivo que CORT puede **afirmar**, no el que parece bonito.

Regla 11 de `AGENTS.md`: no se puede afirmar que CORT «se siente» algo que no
pasa en el código. Así que este módulo no hace análisis de sentimiento con un
modelo — esta máquina no lo paga junto con Ollama —, sino que traduce **señales
que ya existen** en el servidor (una acción medida por `actions.perform`, una
cuenta atrás que termina, un recuerdo guardado, un mensaje de iniciativa) y,
sólo cuando no hay señal, un léxico determinista sobre el texto que se va a decir.

De ahí salen dos reglas que estas pruebas fijan:

1. **La salida es un conjunto cerrado.** El cuerpo 3D tiene cinco expresiones
   mapeadas; un `mood` inventado o mal escrito no puede viajar por el cable,
   porque al otro lado no hay nada que pintarlo. Todo lo desconocido es `calm`.
2. **La señal manda sobre el léxico.** `actions.perform` *midió* un cambio; una
   palabra simpática en el texto sólo se parece a uno. Prioridad: señal medida →
   léxico del texto → reposo.

Nada de aquí decide cuándo hablar: eso lo hacen `initiative.py` y el bucle del
WebSocket. Aquí sólo se pone nombre a lo que ya pasó.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from cort_core import affect


class TestConjuntoCerrado(unittest.TestCase):
    def test_las_seales_conocidas_salen_todas_del_inventario(self):
        for senal in affect.SENALES:
            with self.subTest(senal=senal):
                self.assertIn(affect.mood_for("", senal), affect.MOODS)

    def test_una_senal_desconocida_no_viaja(self):
        # El bucle del WebSocket puede pasar cualquier cosa; un nombre escrito mal
        # es reposo, no un estado que la interfaz no sabe pintar.
        self.assertEqual(affect.mood_for("hola", "enfado_terrible"), "calm")

    def test_sin_senal_y_sin_texto_es_reposo(self):
        self.assertEqual(affect.mood_for(""), "calm")
        self.assertEqual(affect.mood_for("   "), "calm")


class TestSenales(unittest.TestCase):
    """Lo que pasó de verdad en el core, cuadro por cuadro."""

    def test_accion_medida_y_ok_es_alegria(self):
        self.assertEqual(affect.mood_for("Volumen al 40.", "logro"), "happy")

    def test_accion_que_no_se_pudo_hacer_es_tristeza(self):
        # El servidor dice «No pude: …» cuando `perform` no midió el cambio.
        self.assertEqual(affect.mood_for("No pude: sin permiso.", "fallo"), "sad")

    def test_el_plan_sale_entero_o_con_un_hueco(self):
        self.assertEqual(affect.mood_for("Hice las dos cosas.", "plan_completo"), "happy")
        self.assertEqual(affect.mood_for("Una salió mal.", "plan_con_fallo"), "sad")

    def test_se_guardo_un_recuerdo(self):
        self.assertEqual(affect.mood_for("Anotado.", "memoria"), "happy")

    def test_acabo_la_cuenta_es_sorpresa(self):
        # Es el único aviso que llega sin que nadie lo pida en ese momento: la
        # cara tiene que volverse, no sonreír.
        self.assertEqual(affect.mood_for("Se acabó el tiempo.", "fin_cuenta"), "surprised")

    def test_hablar_primero_es_calma_no_alegria(self):
        # La iniciativa habla tras 90 s de silencio. Fingir entusiasmo ahí sería
        # un salto en la cara de la usuaria; lo que se quiere es suavidad.
        self.assertEqual(affect.mood_for("Llevas un rato callada.", "iniciativa"), "relaxed")

    def test_el_saludo_se_alegra(self):
        self.assertEqual(affect.mood_for("Hola, soy CORT.", "saludo"), "happy")

    def test_el_eco_no_tiene_sentimientos(self):
        # Sin Ollama CORT repite lo que se le dijo. Ponerle cara alegre a un eco
        # sería afirmar algo que no pasó.
        self.assertEqual(affect.mood_for("hola", "eco"), "calm")

    def test_cancelar_es_neutro(self):
        self.assertEqual(affect.mood_for("Temporizador cancelado.", "cancelado"), "calm")


class TestLexico(unittest.TestCase):
    """Cuando no hay señal medida: el texto que se va a decir, sin modelo."""

    def test_agradecimiento_y_listo_alegran(self):
        for texto in ("¡Listo!", "Gracias, ya está hecho", "Perfecto, funcionando"):
            with self.subTest(texto=texto):
                self.assertEqual(affect.mood_for(texto), "happy")

    def test_no_poder_entristece(self):
        for texto in ("No puedo hacer eso.", "No sé a qué te refieres",
                      "Hubo un error al abrir la app", "Falló el permiso"):
            with self.subTest(texto=texto):
                self.assertEqual(affect.mood_for(texto), "sad")

    def test_la_negacion_de_una_pregunta_no_es_tristeza(self):
        # «¿No puedes subir el volumen?» es una petición de la usuaria, no una
        # confesión de CORT: los patrones de fallo están escritos en primera
        # persona («no puedo», «no pude», «no sé»).
        self.assertEqual(affect.mood_for("¿No puedes subir el volumen?"), "calm")

    def test_texto_plano_no_inventa_nada(self):
        for texto in ("Está a 22 grados en Bogotá.",
                      "Tienes 14 recuerdos guardados.",
                      "The quick brown fox"):
            with self.subTest(texto=texto):
                self.assertEqual(affect.mood_for(texto), "calm")

    def test_acento_y_mayusculas_da_igual(self):
        self.assertEqual(affect.mood_for("LISTO"), "happy")
        self.assertEqual(affect.mood_for("no pude"), "sad")
        self.assertEqual(affect.mood_for("FALLÓ el permiso"), "sad")


class TestPrioridad(unittest.TestCase):
    def test_la_senal_mandada_manda_sobre_el_texto(self):
        # `perform` midió el cambio: eso es evidencia. Que el texto tenga una
        # palabra triste no borra lo medido.
        self.assertEqual(affect.mood_for("No estoy seguro, pero subió.", "logro"), "happy")

    def test_una_senal_desconocida_deja_pasar_al_lexico(self):
        # Si el core manda un nombre que este módulo no conoce, lo que no se
        # puede afirmar por señal sí se puede leer en el texto.
        self.assertEqual(affect.mood_for("¡Listo!", "senal_del_futuro"), "happy")


class TestFormaDelMarco(unittest.TestCase):
    def test_marco_de_asistente_lleva_mood_valido(self):
        marco = affect.marco("assistant_message", "¡Listo!", senal="logro")
        self.assertEqual(marco, {"type": "assistant_message", "text": "¡Listo!",
                                 "mood": "happy"})

    def test_el_texto_no_se_toca(self):
        # La cara cambia, las palabras no: un módulo de expresiones que reescribiera
        # lo que CORT dice estaría en el archivo equivocado.
        texto = "  Hola, qué tal?  "
        self.assertEqual(affect.marco("assistant_message", texto)["text"], texto)


if __name__ == "__main__":
    unittest.main()
