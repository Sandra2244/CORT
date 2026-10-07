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

if __name__ == "__main__": unittest.main()
