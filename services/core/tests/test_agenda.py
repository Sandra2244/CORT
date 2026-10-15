"""La agenda: sobrevive a cerrar CORT y no gasta nada en reposo."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from cort_core.agenda import MAX_PENDIENTES, MAX_TEXTO, Agenda, marco

AHORA = datetime(2026, 10, 12, 21, 30)


class TestAgenda(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.ruta = Path(self.dir.name) / "agenda.json"
        self.ag = Agenda(self.ruta)

    def test_sobrevive_a_reabrir(self):
        self.ag.agregar("alarma", AHORA + timedelta(hours=9), "gym")
        otra = Agenda(self.ruta)                       # «cerrar y abrir CORT»
        self.assertEqual([i["texto"] for i in otra.pendientes()], ["gym"])
        self.assertEqual(otra.agregar("alarma", AHORA, "x")["id"], 2, "los ids no se repiten")

    def test_pendientes_en_orden(self):
        self.ag.agregar("recordatorio", AHORA + timedelta(hours=2), "b")
        self.ag.agregar("alarma", AHORA + timedelta(hours=1), "a")
        self.assertEqual([i["texto"] for i in self.ag.pendientes()], ["a", "b"])

    def test_vencidos_y_entregados(self):
        i = self.ag.agregar("alarma", AHORA - timedelta(minutes=5), "pasó")
        self.ag.agregar("alarma", AHORA + timedelta(minutes=5), "viene")
        self.assertEqual([v["texto"] for v in self.ag.vencidos(AHORA)], ["pasó"])
        self.ag.marcar_entregado(i["id"])
        self.assertEqual(self.ag.vencidos(AHORA), [], "lo entregado no vuelve a sonar")
        self.assertEqual(len(Agenda(self.ruta).pendientes()), 1, "y no vuelve tras reabrir")

    def test_cuanto_dormir(self):
        self.assertIsNone(self.ag.segundos_hasta_proximo(AHORA), "vacía: no hay nada que esperar")
        self.ag.agregar("alarma", AHORA - timedelta(minutes=1), "vencida")
        self.assertIsNone(self.ag.segundos_hasta_proximo(AHORA),
                          "una vencida sin entregar no cuenta: haría un bucle sin dormir")
        self.ag.agregar("alarma", AHORA + timedelta(seconds=90), "futura")
        self.assertEqual(self.ag.segundos_hasta_proximo(AHORA), 90.0)

    def test_cancelar(self):
        self.ag.agregar("alarma", AHORA + timedelta(hours=1), "a")
        self.ag.agregar("recordatorio", AHORA + timedelta(hours=2), "pan")
        self.assertEqual(self.ag.cancelar(tipo="alarma"), 1)
        self.assertEqual(self.ag.cancelar(texto="PAN"), 1)
        self.assertEqual(self.ag.pendientes(), [])

    def test_cancelar_por_id(self):
        i = self.ag.agregar("alarma", AHORA + timedelta(hours=1), "a")
        self.assertTrue(self.ag.cancelar_id(i["id"]))
        self.assertFalse(self.ag.cancelar_id(i["id"]))

    def test_tope_de_pendientes_y_de_texto(self):
        for n in range(MAX_PENDIENTES):
            self.ag.agregar("alarma", AHORA + timedelta(minutes=n + 1), "x")
        with self.assertRaises(ValueError):
            self.ag.agregar("alarma", AHORA + timedelta(days=1), "una más")
        self.assertLessEqual(len(Agenda(Path(self.dir.name) / "otra.json").agregar("alarma", AHORA, "y" * 999)["texto"]), MAX_TEXTO)

    def test_archivo_roto_no_impide_arrancar_ni_se_borra(self):
        self.ruta.write_text("{esto no es json", encoding="utf-8")
        self.assertEqual(Agenda(self.ruta).pendientes(), [])
        self.assertEqual(self.ruta.read_text(encoding="utf-8"), "{esto no es json")

    def test_entradas_malas_se_descartan_las_buenas_quedan(self):
        self.ruta.write_text(json.dumps({"items": [
            {"id": 1, "tipo": "alarma", "cuando": "2026-10-13T07:00:00", "texto": "ok"},
            {"id": 2, "tipo": "alarma", "cuando": "no es fecha"},
            {"tipo": "alarma"},
        ]}), encoding="utf-8")
        self.assertEqual([i["texto"] for i in Agenda(self.ruta).pendientes()], ["ok"])

    def test_el_marco_del_protocolo(self):
        i = self.ag.agregar("alarma", datetime(2026, 10, 13, 7, 5), "gym")
        self.assertEqual(marco(i), {"type": "alarm", "id": 1, "tipo": "alarma", "texto": "gym",
                                    "cuando": "07:05", "atrasada": False})
        self.assertTrue(marco(i, atrasada=True)["atrasada"])


if __name__ == "__main__":
    unittest.main()
