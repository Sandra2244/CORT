import sys, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from cort_core.outfit import pick_outfit
from cort_core.intents import match_intent

class T(unittest.TestCase):
    def test_night(self): self.assertEqual(pick_outfit(23, 20), "night")
    def test_cold(self): self.assertEqual(pick_outfit(12, 5), "hoodie")
    def test_hot(self): self.assertEqual(pick_outfit(12, 32), "light")
    def test_work(self): self.assertEqual(pick_outfit(11, 20), "work")
    def test_casual(self): self.assertEqual(pick_outfit(19, 20), "casual")
    def test_bad_hour(self):
        with self.assertRaises(ValueError): pick_outfit(24, 20)
    def test_volume(self): self.assertEqual(match_intent("sube el volumen")["delta"], 10)
    def test_none(self): self.assertIsNone(match_intent("cuéntame un chiste"))
    def test_open_files(self):
        self.assertEqual(match_intent("abre el gestor de archivos"), {"action": "launch", "app": "archivos"})
    def test_open_terminal_infinitive(self):
        self.assertEqual(match_intent("quiero abrir la terminal"), {"action": "launch", "app": "terminal"})
    def test_capture_wins_over_opening(self):
        """El orden de la tabla es una decisión: si una frase pide dos cosas,
        CORT hace la primera que casa y lo dice."""
        self.assertEqual(match_intent("haz una captura y abre archivos")["action"], "screenshot")
    def test_opening_something_unknown_is_not_an_intent(self):
        """Sin patrón no hay intent, y sin intent el texto va al LLM: CORT no
        abre lo que no está en su tabla."""
        self.assertIsNone(match_intent("abre el editor de video"))

if __name__ == "__main__": unittest.main()
