"""Pruebas del puente de memoria **asomado a la red** (`GET/POST /memoria/puente`).

`test_puente.py` prueba la lógica pura; este archivo prueba lo que esa lógica no puede
por sí sola: que las dos rutas están detrás del **mismo** candado que el WebSocket y
los atuendos, que la llave de red no se cuela en el cuadro ni yendo ni viniendo, que un
cuerpo desmedido se rechaza sin parsear, y que un cuadro malo no deja memoria a medias.

El almacén es siempre una base en `/tmp`: `make test` no fija `CORT_MEMORY_DB`, así que
el `MemoryStore` que `server.py` construye al importar apunta a `data/memory.db` — la
cabeza real de la dueña—. Parchear `server.memory` (como hace `test_initiative.py`) no
es limpieza, es la única forma de que una prueba de sincronía no le escriba recuerdos
de mentira.
"""
from __future__ import annotations

import json
import os
import sys
import pathlib
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from cort_core import audit
from cort_core import puente
from cort_core import server
from cort_core.memory.store import MemoryStore

LLAVE = "llave-de-prueba"


def nuevo_store() -> MemoryStore:
    return MemoryStore(pathlib.Path(tempfile.mkdtemp(prefix="cort-puente-")) / "memory.db")


class ConRed:
    """El core publicado en `0.0.0.0` con su llave, una bitácora aparte y otra cabeza."""

    def __init__(self, *, publicado=True):
        self.publicado = publicado

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        raiz = pathlib.Path(self.tmp.name)
        entorno = {"CORT_DOTENV": "0",
                   "CORT_AUDIT_LOG": str(raiz / "rechazos.jsonl"),
                   "CORT_LAN_TOKEN": LLAVE}
        if self.publicado:
            entorno["CORT_HOST"] = "0.0.0.0"
        self.parche = mock.patch.dict(os.environ, entorno)
        self.parche.start()
        if not self.publicado:
            os.environ.pop("CORT_HOST", None)
        self.store = nuevo_store()
        self.memoria = mock.patch.object(server, "memory", self.store)
        self.memoria.start()
        self.client = TestClient(server.app)
        return self

    def __exit__(self, *exc):
        self.memoria.stop()
        self.store.close()
        self.parche.stop()
        self.tmp.cleanup()

    def bitacora(self) -> list[dict]:
        ruta = pathlib.Path(self.tmp.name) / "rechazos.jsonl"
        if not ruta.exists():
            return []
        return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


class TestPuertaAbajodelaLlave(unittest.TestCase):

    def test_sin_token_no_hay_cuadro(self):
        with ConRed() as ctx:
            self.assertEqual(401, ctx.client.get("/memoria/puente").status_code)

    def test_con_el_token_malo_tampoco(self):
        with ConRed() as ctx:
            self.assertEqual(401, ctx.client.get(f"/memoria/puente?token=otra").status_code)

    def test_con_el_token_bueno_si(self):
        with ConRed() as ctx:
            ctx.store.remember("El usuario se llama Sandra")
            r = ctx.client.get(f"/memoria/puente?token={LLAVE}")
            self.assertEqual(200, r.status_code)
            cuadro = r.json()
            self.assertEqual("memoria", cuadro["tipo"])
            self.assertEqual(puente.VERSION, cuadro["version"])
            self.assertEqual("escritorio", cuadro["origen"])
            self.assertEqual([{"contenido": "El usuario se llama Sandra",
                               "cuando": cuadro["recuerdos"][0]["cuando"]}],
                             cuadro["recuerdos"])

    def test_en_local_no_se_pide_nada(self):
        """Sin `CORT_HOST` publicado el candado no existe: el portátil sigue igual."""
        with ConRed(publicado=False) as ctx:
            ctx.store.remember("uso un Samsung A16")
            r = ctx.client.get("/memoria/puente")
            self.assertEqual(200, r.status_code)
            self.assertEqual(1, r.json()["total"])

    def test_un_rechazo_queda_apuntado_sin_la_llave_dentro(self):
        """El `?token=` nunca va a la bitácora: una log con el query dentro es un
        archivo de claves. Se comprueba el detalle, que es donde caería."""
        with ConRed() as ctx:
            ctx.client.get(f"/memoria/puente?token=incorrecta")
            lineas = ctx.bitacora()
            self.assertTrue(lineas, "un intento sin llave válida tiene que quedar escrito")
            self.assertIn("GET /memoria/puente", lineas[-1]["detalle"])
            for linea in lineas:
                self.assertNotIn(LLAVE, json.dumps(linea, ensure_ascii=False))

    def test_estas_dos_rutas_no_abren_el_cors(self):
        """`/avatars/{nombre}` sí lo abre (lo llama un `<img>`); el puente lo llama una
        app Java. Declararlo aquí sería regalarle a cualquier pestaña leer la memoria."""
        with ConRed() as ctx:
            r = ctx.client.get(f"/memoria/puente?token={LLAVE}")
            self.assertNotIn("access-control-allow-origin",
                             {k.lower() for k in r.headers})


class TestLaLlaveNoViaja(unittest.TestCase):

    def test_un_recuerdo_que_contiene_la_llave_no_sale(self):
        with ConRed() as ctx:
            ctx.store.remember("mi clave del wifi es " + LLAVE)
            ctx.store.remember("El usuario se llama Sandra")
            cuadro = ctx.client.get(f"/memoria/puente?token={LLAVE}").json()
            self.assertEqual(1, cuadro["total"])
            self.assertEqual(1, cuadro["ocultados"])
            self.assertNotIn(LLAVE, json.dumps(cuadro))

    def test_un_recuerdo_del_telefono_con_la_llave_dentro_se_rechaza(self):
        with ConRed() as ctx:
            r = ctx.client.post(f"/memoria/puente?token={LLAVE}", json={
                "version": 1,
                "recuerdos": [{"contenido": f"apuntar: {LLAVE}"},
                              {"contenido": "me llamo Sandra"}]})
            self.assertEqual({"nuevos": 1, "repetidos": 0, "rechazados": 1, "total": 2},
                             {k: r.json()[k] for k in ("nuevos", "repetidos", "rechazados", "total")})
            self.assertEqual(["me llamo Sandra"], ctx.store.all())
            self.assertNotIn(LLAVE, json.dumps(ctx.store.all()))


class TestSubida(unittest.TestCase):

    def test_sin_token_tampoco_se_escribe_nada(self):
        with ConRed() as ctx:
            r = ctx.client.post("/memoria/puente",
                                json={"version": 1, "recuerdos": [{"contenido": "x"}]})
            self.assertEqual(401, r.status_code)
            self.assertEqual([], ctx.store.all())

    def test_un_cuadro_bueno_suma_y_devuelve_el_recuento(self):
        with ConRed() as ctx:
            ctx.store.remember("El usuario se llama Sandra")
            r = ctx.client.post(f"/memoria/puente?token={LLAVE}", json={
                "version": 1,
                "recuerdos": [{"contenido": "El usuario se llama sandra"},
                              {"contenido": "El usuario usa un Samsung A16"}]})
            self.assertEqual(200, r.status_code)
            cuerpo = r.json()
            self.assertEqual(1, cuerpo["nuevos"])
            self.assertEqual(1, cuerpo["repetidos"])
            self.assertEqual(2, cuerpo["total"])
            self.assertEqual(2, ctx.store.count())

    def test_una_basura_responde_400_y_no_deja_nada_a_medias(self):
        with ConRed() as ctx:
            ctx.store.remember("El usuario se llama Sandra")
            for cuerpo in (b'{"version": 1, "recuerdos": ', b"no es json"):
                r = ctx.client.post(f"/memoria/puente?token={LLAVE}",
                                    content=cuerpo,
                                    headers={"content-type": "application/json"})
                self.assertEqual(400, r.status_code, cuerpo)
            self.assertEqual(["El usuario se llama Sandra"], ctx.store.all())

    def test_otra_version_del_cuadro_es_un_error_de_forma_no_un_vacio(self):
        with ConRed() as ctx:
            r = ctx.client.post(f"/memoria/puente?token={LLAVE}",
                                json={"version": 99, "recuerdos": [{"contenido": "nuevo"}]})
            self.assertEqual(400, r.status_code)
            self.assertIn("99", r.json()["detail"])
            self.assertEqual([], ctx.store.all())

    def test_un_cuadro_que_pasa_el_tope_se_rechaza_sin_leerlo(self):
        with ConRed() as ctx:
            # Filas largas **y** más de las permitidas: el 413 tiene que caer antes de
            # mirar el contenido, así que el cuerpo tiene que pasar los dos topes.
            gigante = json.dumps({"version": 1, "recuerdos": [
                {"contenido": f"hecho {n} " + "x" * (puente.MAX_CONTENIDO - 12)}
                for n in range(puente.MAX_FILAS + 400)]}).encode()
            self.assertGreater(len(gigante), puente.MAX_BYTES)
            self.assertGreater(len(json.loads(gigante)["recuerdos"]), puente.MAX_FILAS)
            r = ctx.client.post(f"/memoria/puente?token={LLAVE}",
                                content=gigante,
                                headers={"content-type": "application/json"})
            self.assertEqual(413, r.status_code)
            self.assertEqual([], ctx.store.all())

    def test_un_content_length_mentiroso_no_burla_el_tope(self):
        """El freno gordo es el `Content-Length` (no se bufferiza un cuerpo gigante), y
        además se mide el cuerpo real: sin ese segundo control, mentir en la cabecera
        sería el atajo."""
        with ConRed() as ctx:
            r = ctx.client.post(f"/memoria/puente?token={LLAVE}",
                                content=b"x" * (puente.MAX_BYTES + 1),
                                headers={"content-type": "application/json",
                                         "content-length": "10"})
            self.assertEqual(413, r.status_code)

    def test_subir_un_cuadro_vacio_no_poda_la_memoria(self):
        with ConRed() as ctx:
            ctx.store.remember("El usuario se llama Sandra")
            r = ctx.client.post(f"/memoria/puente?token={LLAVE}",
                                json={"version": 1, "recuerdos": []})
            self.assertEqual(200, r.status_code)
            self.assertEqual(0, r.json()["nuevos"])
            self.assertEqual(["El usuario se llama Sandra"], ctx.store.all())


class TestIdayVuelta(unittest.TestCase):
    """La escena que justifica el corte: la dueña dice un dato en el teléfono y el
    portátil lo sabe; y al revés. Con dos bases y las dos rutas, sin Java delante."""

    def test_un_dato_del_telefono_llega_al_portatil_y_al_reves(self):
        with ConRed() as ctx:
            ctx.store.remember("El usuario se llama Sandra")
            cuadro = ctx.client.get(f"/memoria/puente?token={LLAVE}").json()

            telefono = nuevo_store()
            self.addCleanup(telefono.close)
            telefono.remember("El usuario usa un Samsung A16")
            puente.fusionar(telefono, cuadro)
            self.assertEqual(["El usuario se llama Sandra",
                              "El usuario usa un Samsung A16"], sorted(telefono.all()))

            de_vuelta = puente.exportar(telefono.filas(), origen="telefono")
            respuesta = ctx.client.post(f"/memoria/puente?token={LLAVE}",
                                        json=de_vuelta).json()
            # Quien responde se anuncia a sí mismo (`escritorio`), no repite el `origen`
            # que le llegó: es la misma forma del cuadro, y el teléfono la usa para
            # comprobar que habló con el portátil y no con otro teléfono.
            self.assertEqual("escritorio", respuesta["origen"])
            self.assertEqual(1, respuesta["nuevos"])
            self.assertEqual(sorted(telefono.all()), sorted(ctx.store.all()))
            self.assertEqual(0, puente.fusionar(ctx.store, de_vuelta)["nuevos"])


class TestQueElServidorUseElPuente(unittest.TestCase):
    """Costura: que `server.py` no se haya quedado en su propia copia de la lógica.

    Un endpoint que reimplementa el dedupe por su cuenta es un segundo puente que
    alguien afinará por separado.
    """

    def setUp(self):
        self.fuente = (pathlib.Path(__file__).resolve().parents[1]
                       / "cort_core" / "server.py").read_text(encoding="utf-8")

    def test_llama_a_exportar_y_a_fusionar(self):
        self.assertIn("puente.exportar(", self.fuente)
        self.assertIn("puente.fusionar(", self.fuente)

    def test_pasa_la_llave_en_ambos_sentidos(self):
        self.assertEqual(2, self.fuente.count("llave=security.token_configurado()"))

    def test_el_tope_del_cuerpo_es_el_del_puente_no_un_numero_suelto(self):
        self.assertIn("_MAX_CUERPO = puente.MAX_BYTES", self.fuente)


if __name__ == "__main__":
    unittest.main()
