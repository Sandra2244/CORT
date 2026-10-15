"""«mañana a las 7», «en 20 minutos»: la hora se entiende o se dice que no."""
import unittest
from datetime import datetime

from cort_core import tiempo

# Lunes 12 de octubre de 2026, 9:30 de la noche. Fija: nada de esto espera al reloj.
AHORA = datetime(2026, 10, 12, 21, 30)


def cuando(texto, **kw):
    d, _ = tiempo.extraer_cuando(texto, AHORA, **kw)
    return d.strftime("%Y-%m-%d %H:%M") if d else None


class TestRelativo(unittest.TestCase):
    def test_tabla(self):
        for texto, esperado in [
            ("en 20 minutos", "2026-10-12 21:50"),
            ("en media hora", "2026-10-12 22:00"),
            ("en una hora y media", "2026-10-12 23:00"),
            ("en 1 hora y media", "2026-10-12 23:00"),
            ("en 2 horas y 15 minutos", "2026-10-12 23:45"),
            ("en 90 segundos", "2026-10-12 21:31"),
            ("en 2,5 horas", "2026-10-13 00:00"),
        ]:
            with self.subTest(texto):
                self.assertEqual(cuando(texto), esperado)


class TestHoraDelDia(unittest.TestCase):
    def test_sin_pista_es_la_proxima_vez(self):
        # a las 21:30: las 7 son mañana, las 10 son esta noche.
        self.assertEqual(cuando("a las 7"), "2026-10-13 07:00")
        self.assertEqual(cuando("a las 10"), "2026-10-12 22:00")

    def test_con_pista(self):
        for texto, esperado in [
            ("a las 7 de la mañana", "2026-10-13 07:00"),
            ("a las 7 de la noche", "2026-10-13 19:00"),   # las 19:00 de hoy ya pasaron
            ("a las 9 pm", "2026-10-13 21:00"),             # las 21:00 de hoy ya pasaron
            ("hoy a las 11 de la noche", "2026-10-12 23:00"),
            ("a las 12 de la noche", "2026-10-13 00:00"),
            ("a las 12", "2026-10-13 12:00"),               # a secas, el mediodía
            ("a las 19", "2026-10-13 19:00"),
            ("a las 11:30 p. m.", "2026-10-12 23:30"),
        ]:
            with self.subTest(texto):
                self.assertEqual(cuando(texto), esperado)

    def test_palabras_y_fracciones(self):
        self.assertEqual(cuando("a las siete y media"), "2026-10-13 07:30")
        self.assertEqual(cuando("a las 8 menos cuarto"), "2026-10-13 07:45")
        self.assertEqual(cuando("a las cinco y cuarto de la tarde"), "2026-10-13 17:15")

    def test_mediodia_y_medianoche(self):
        self.assertEqual(cuando("al mediodía"), "2026-10-13 12:00")
        self.assertEqual(cuando("a medianoche"), "2026-10-13 00:00")

    def test_la_manana_de_la_hora_no_es_el_dia_de_manana(self):
        """«a las 7 de la mañana» es una hora; «mañana a las 7» es un día y una hora."""
        self.assertEqual(cuando("a las 7 de la mañana"), cuando("mañana a las 7"))
        d, resto = tiempo.extraer_cuando("a las 7 de la mañana llamar", AHORA)
        self.assertEqual(resto, "llamar")


class TestDias(unittest.TestCase):
    def test_tabla(self):
        for texto, esperado in [
            ("mañana a las 3", "2026-10-13 15:00"),         # 1-4 con día: de la tarde
            ("mañana a las 8", "2026-10-13 08:00"),         # 5-11 con día: de la mañana
            ("pasado mañana a las 10", "2026-10-14 10:00"),
            ("el lunes a las 9", "2026-10-19 09:00"),       # hoy es lunes: el que viene
            ("el viernes a las 6 de la tarde", "2026-10-16 18:00"),
            ("el 3 de noviembre a las 15:00", "2026-11-03 15:00"),
            ("el 15/11 a las 8 am", "2026-11-15 08:00"),
            ("el 3 de marzo a las 10 am", "2027-03-03 10:00"),   # ya pasó este año
        ]:
            with self.subTest(texto):
                self.assertEqual(cuando(texto), esperado)

    def test_sin_hora_no_se_adivina_salvo_que_se_pida(self):
        self.assertIsNone(cuando("mañana"))
        self.assertEqual(cuando("mañana", hora_por_defecto=(9, 0)), "2026-10-13 09:00")


class TestLoQueNoEsTiempo(unittest.TestCase):
    def test_none(self):
        for texto in ["hola", "qué tal", "a las 25", "a las 7:75", "compra pan"]:
            with self.subTest(texto):
                self.assertIsNone(cuando(texto))

    def test_devuelve_el_resto_sin_la_expresion(self):
        d, resto = tiempo.extraer_cuando("sacar la pasta en 20 minutos", AHORA)
        self.assertEqual(resto, "sacar la pasta")


class TestComoSeDice(unittest.TestCase):
    def test_12_horas(self):
        self.assertEqual(tiempo.hora_12(datetime(2026, 1, 1, 19, 5)), "7:05 p. m.")
        self.assertEqual(tiempo.hora_12(datetime(2026, 1, 1, 0, 0)), "12:00 a. m.")
        self.assertEqual(tiempo.hora_12(datetime(2026, 1, 1, 12, 30)), "12:30 p. m.")

    def test_cuando_texto(self):
        self.assertEqual(tiempo.cuando_texto(datetime(2026, 10, 12, 22, 0), AHORA), "hoy a las 10:00 p. m.")
        self.assertEqual(tiempo.cuando_texto(datetime(2026, 10, 13, 7, 0), AHORA), "mañana a las 7:00 a. m.")
        self.assertEqual(tiempo.cuando_texto(datetime(2026, 10, 16, 18, 0), AHORA), "el viernes a las 6:00 p. m.")
        self.assertIn("19 de octubre", tiempo.cuando_texto(datetime(2026, 10, 19, 9, 0), AHORA))


if __name__ == "__main__":
    unittest.main()
