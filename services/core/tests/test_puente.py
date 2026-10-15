"""Pruebas del puente de memoria (`cort_core/puente.py`) — deuda 2 de `v0.15.2`.

El acuerdo Java dejó dos cabezas que no se hablaban: `memory.db` en el portátil y
`cort.db` dentro del APK. Este puente es la mitad portable de ese arreglo, y lo que
se prueba aquí es justo lo que **no** puede hacer:

1. **No puede llevarse la llave de red puestas.** Un recuerdo que contiene el token
   no sale en el cuadro, y se cuenta como `ocultados` en vez de perderse en silencio.
2. **No puede borrar.** Fusionar sólo añade; un lado podado no es un lado que olvidó,
   es un lado que hizo borrar en el otro.
3. **No puede duplicar por culpa de una mayúscula.** El dedupe va por
   `normaliza()`, no por cadena exacta — la limitación de `remember()` está escrita en
   `docs/STATUS.md` y un puente literal la multiplicaría una vez por sincronía.
4. **No puede tocar la red ni el disco por su cuenta.** Es lógica pura, y hay una
   prueba que le lee el `import` para que siga siéndolo.

No hay FastAPI aquí a propósito: el extremo HTTP se prueba en `test_puente_red.py`.
"""
from __future__ import annotations

import ast
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from cort_core import puente
from cort_core.memory.store import MemoryStore


class Almacen:
    """Un almacén de juguete con la interfaz que el puente exige: `filas` y `remember`.

    Con uno de verdad (`MemoryStore`) también corren las pruebas de abajo; éste
    existe para contar rechazos y fusiones sin abrir disco en cada assert.
    """

    def __init__(self, iniciales=()):
        self.guardadas = [str(x) for x in iniciales]

    def filas(self):
        return [{"id": n + 1, "content": c, "created_at": "2026-10-15T00:00:00+00:00"}
                for n, c in enumerate(self.guardadas)]

    def remember(self, content):
        self.guardadas.append(content)
        return len(self.guardadas)


class TestNormaliza(unittest.TestCase):

    def test_ignora_mayusculas_y_espacios_de_sobra(self):
        self.assertEqual(puente.normaliza("  Me   llamo Sandra "),
                         puente.normaliza("me llamo sandra"))

    def test_no_quita_las_tildes(self):
        """«canción» y «cancion» son dos recuerdos distintos y aquí no se decide por ella."""
        self.assertNotEqual(puente.normaliza("mi canción"), puente.normaliza("mi cancion"))

    def test_casefold_hasta_el_final_s(self):
        self.assertEqual(puente.normaliza("SS"), puente.normaliza("ss"))

    def test_algo_que_no_es_texto_no_reventa(self):
        self.assertEqual("", puente.normaliza(None))
        self.assertEqual("42", puente.normaliza(42))


class TestExportar(unittest.TestCase):

    def test_la_forma_del_cuadro(self):
        cuadro = puente.exportar([{"content": "El usuario se llama Sandra",
                                   "created_at": "2026-10-15T10:00:00+00:00"}])
        self.assertEqual("memoria", cuadro["tipo"])
        self.assertEqual(puente.VERSION, cuadro["version"])
        self.assertEqual("escritorio", cuadro["origen"])
        self.assertEqual(1, cuadro["total"])
        self.assertEqual([{"contenido": "El usuario se llama Sandra",
                           "cuando": "2026-10-15T10:00:00+00:00"}], cuadro["recuerdos"])

    def test_acepta_las_dos_formas_de_fila(self):
        """El portátil da `content`/`created_at`; el teléfono, `contenido`/`cuando`."""
        uno = puente.exportar([{"content": "a", "created_at": "x"}])
        dos = puente.exportar([{"contenido": "a", "cuando": "x"}])
        self.assertEqual(uno["recuerdos"], dos["recuerdos"])

    def test_una_fila_vacia_se_oculta_y_se_cuenta(self):
        cuadro = puente.exportar([{"content": "   "}, {"content": "sí existe"}])
        self.assertEqual(1, cuadro["total"])
        self.assertEqual(1, cuadro["ocultados"])

    def test_un_recuerdo_desmedido_no_sale(self):
        cuadro = puente.exportar([{"content": "x" * (puente.MAX_CONTENIDO + 1)}])
        self.assertEqual([], cuadro["recuerdos"])
        self.assertEqual(1, cuadro["ocultados"])

    def test_la_llave_de_red_jamas_sale_dentro_de_un_recuerdo(self):
        """Regla 1: exportar no puede regalar la llave a quien ya tiene el enlace."""
        cuadro = puente.exportar(
            [{"content": "mi clave del wifi es cort-9f3a1b"},
             {"content": "uso un Samsung A16"}],
            llave="cort-9f3a1b")
        self.assertEqual([{"contenido": "uso un Samsung A16", "cuando": ""}],
                         cuadro["recuerdos"])
        self.assertEqual(1, cuadro["ocultados"])

    def test_sin_llave_configurada_no_filtra_nada(self):
        cuadro = puente.exportar([{"content": "mi clave del wifi es cort-9f3a1b"}])
        self.assertEqual(1, cuadro["total"])

    def test_el_tope_de_filas_corta_sin_reventar(self):
        cuadro = puente.exportar([{"content": f"hecho {n}"} for n in range(10)], tope=3)
        self.assertEqual(3, cuadro["total"])
        self.assertEqual(3, len(cuadro["recuerdos"]))

    def test_los_topos_estan_escritos_y_son_los_que_el_servidor_lee(self):
        self.assertEqual(300, puente.MAX_CONTENIDO)
        self.assertEqual(500, puente.MAX_FILAS)
        self.assertEqual(262_144, puente.MAX_BYTES)


class TestCanoniza(unittest.TestCase):
    """`canoniza`: el cuadro sale igual por fuera y traducido por dentro.

    El puente no puede conocer a `facts` (una prueba le lee el AST y sólo le
    permite `re`), así que la traducción llega como callable. Lo que se prueba aquí
    es la **mecánica** del reemplazo; las reglas de qué es canónico viven en
    `test_memory.py`, junto a la función que las aplica.
    """

    def dos_formas(self, texto):
        """Un canon de juguete que devuelve dos hechos **distintos** por frase.

        Distintos de verdad: si devolviera la misma frase en mayúsculas, el dedupe
        normalizado de abajo la colapsaría — que es lo correcto, y lo que hace que
        este juguete tenga que elegir palabras que no se parezcan tanto.
        """
        return [texto, "HECHO: " + texto] if texto else []

    def revienta(self, texto):
        raise RuntimeError("el traductor se cayó")

    def test_reescribe_y_devuelve_el_mismo_cuadro_por_fuera(self):
        cuadro = {"tipo": "memoria", "version": 1, "origen": "telefono", "total": 1,
                  "ocultados": 0, "recuerdos": [{"contenido": "nombre: Sandra",
                                                 "cuando": "2026-10-15T10:00:00+00:00"}]}
        salida = puente.canoniza(cuadro, lambda t: ["El usuario se llama Sandra"])
        self.assertEqual(["El usuario se llama Sandra"],
                         [r["contenido"] for r in salida["recuerdos"]])
        self.assertEqual("telefono", salida["origen"])
        self.assertEqual(1, salida["total"], "el total se recalcula: es lo que viaja")
        self.assertEqual("2026-10-15T10:00:00+00:00", salida["recuerdos"][0]["cuando"],
                         "el cuándo del recuerdo se conserva, no se pone a cero")

    def test_una_fila_puede_volverse_varias(self):
        salida = puente.canoniza({"version": 1, "recuerdos": [{"contenido": "me llamo Sandra"}]},
                                 self.dos_formas)
        self.assertEqual(["me llamo Sandra", "HECHO: me llamo Sandra"],
                         [r["contenido"] for r in salida["recuerdos"]])

    def test_dos_formas_que_difieren_solo_en_mayusculas_no_ocupan_dos_sitios(self):
        """`normaliza` es la clave del dedupe también dentro del cuadro traducido."""
        salida = puente.canoniza({"version": 1, "recuerdos": [{"contenido": "x"}]},
                                 lambda t: [t, t.upper()])
        self.assertEqual(["x"], [r["contenido"] for r in salida["recuerdos"]])

    def test_dos_filas_que_canonizan_igual_solo_van_una_vez(self):
        """El dedupe del cuadro evita la fila duplicada *antes* de llegar a disco."""
        salida = puente.canoniza({"version": 1, "recuerdos": [
            {"contenido": "nombre: Sandra"}, {"contenido": "me llamo: Sandra"}]},
            lambda t: ["El usuario se llama Sandra"])
        self.assertEqual(1, len(salida["recuerdos"]))

    def test_un_canon_que_no_devuelve_nada_conserva_la_fila(self):
        """La diferencia entre «no lo entendí» y «lo tiré»: un `[]` no borra un dato."""
        salida = puente.canoniza({"version": 1, "recuerdos": [{"contenido": "hobby: tocar"}]},
                                 lambda t: [])
        self.assertEqual(["hobby: tocar"], [r["contenido"] for r in salida["recuerdos"]])

    def test_un_canon_que_revienta_no_rompe_la_subida(self):
        salida = puente.canoniza({"version": 1, "recuerdos": [{"contenido": "nombre: Ana"}]},
                                 self.revienta)
        self.assertEqual(["nombre: Ana"], [r["contenido"] for r in salida["recuerdos"]])

    def test_el_tope_de_filas_se_respeta_traduciendo(self):
        cuadro = {"version": 1, "recuerdos": [{"contenido": f"hecho {n}"}
                                              for n in range(puente.MAX_FILAS)]}
        salida = puente.canoniza(cuadro, self.dos_formas)
        self.assertEqual(puente.MAX_FILAS, len(salida["recuerdos"]),
                         "un cuadro que al traducirse pasa del tope se corta, no revienta")

    def test_un_cuadro_mal_formado_pasa_sin_tocar(self):
        """`fusionar` es quien da el error de forma; canonizar no decide por él."""
        for basura in (None, "texto", {"version": 1}, {"version": 1, "recuerdos": "no"}):
            self.assertEqual(basura, puente.canoniza(basura, str))
        cuadro = {"version": 1, "recuerdos": [{"contenido": "x"}]}
        self.assertEqual(cuadro, puente.canoniza(cuadro, None))

    def test_traducir_no_le_devuelve_la_llave_al_puerto(self):
        """El orden del servidor (canoniza → fusionar) no puede reabrir la regla 1:
        una fila con la llave sigue rechazándose aunque la traducción la reescriba."""
        almac = Almacen()
        cuadro = puente.canoniza({"version": 1, "recuerdos": [{"contenido": "clave: llave-123"}]},
                                 lambda t: [f"El usuario se llama {t}"])
        recuento = puente.fusionar(almac, cuadro, llave="llave-123")
        self.assertEqual({"nuevos": 0, "repetidos": 0, "rechazados": 1, "total": 1}, recuento)
        self.assertEqual([], almac.guardadas)

    def test_despues_de_canonizar_almacena_la_forma_canonica(self):
        """El extremo a extremo del puente, sin HTTP: es la prueba que paga el corte."""
        from cort_core.memory.facts import desde_el_telefono
        almac = Almacen()
        cuadro = puente.canoniza(puente.exportar(
            [{"content": "nombre: Sandra"}, {"content": "nota cualquiera"}],
            origen="telefono"), desde_el_telefono)
        puente.fusionar(almac, cuadro)
        self.assertEqual(["El usuario se llama Sandra", "nota cualquiera"], almac.guardadas)


class TestFusionar(unittest.TestCase):

    def test_mete_los_nuevos_y_cuenta_los_que_ya_estaban(self):
        almac = Almacen(["uso un Samsung A16"])
        recuento = puente.fusionar(almac, puente.exportar(
            [{"content": "uso un Samsung A16"}, {"content": "me llamo Sandra"}]))
        self.assertEqual({"nuevos": 1, "repetidos": 1, "rechazados": 0, "total": 2}, recuento)
        self.assertEqual(["uso un Samsung A16", "me llamo Sandra"], almac.guardadas)

    def test_el_dedupe_es_normalizado_no_literal(self):
        """La deuda de `remember()` (mayúsculas) no puede viajar de contrabando."""
        almac = Almacen(["Me   llamo Sandra"])
        recuento = puente.fusionar(almac, {"version": 1,
                                          "recuerdos": [{"contenido": "me llamo sandra"}]})
        self.assertEqual(0, recuento["nuevos"])
        self.assertEqual(1, recuento["repetidos"])

    def test_dentro_del_mismo_lote_tampoco_se_repite(self):
        almac = Almacen()
        recuento = puente.fusionar(almac, {"version": 1, "recuerdos": [
            {"contenido": "trabajo en mi casa"}, {"contenido": "Trabajo en mi casa"}]})
        self.assertEqual({"nuevos": 1, "repetidos": 1, "rechazados": 0, "total": 2}, recuento)

    def test_fusionar_nunca_borra(self):
        """Regla 3: un cuadro vacío no es una orden de limpiar la cabeza del otro."""
        almac = Almacen(["el usuario se llama Sandra", "uso un Samsung A16"])
        puente.fusionar(almac, puente.exportar([]))
        self.assertEqual(2, len(almac.guardadas))

    def test_un_viaje_ida_y_vuelta_no_cambia_nada(self):
        """Sincronizar dos veces no puede duplicar: el segundo viaje trae 0 nuevos."""
        una = Almacen()
        cuadro = puente.exportar([{"content": "me llamo Sandra"},
                                  {"content": "mi teléfono es un Samsung A16"}])
        puente.fusionar(una, cuadro)
        segundo = puente.fusionar(una, cuadro)
        self.assertEqual(0, segundo["nuevos"])
        self.assertEqual(2, segundo["repetidos"])

    def test_un_caracter_de_control_se_limpia_no_se_deja_pasar(self):
        almac = Almacen()
        puente.fusionar(almac, {"version": 1, "recuerdos": [{"contenido": "hola\x00mundo"}]})
        self.assertEqual(["hola mundo"], almac.guardadas)

    def test_lo_que_no_cabe_se_cuenta_como_rechazado(self):
        almac = Almacen()
        recuento = puente.fusionar(almac, {"version": 1, "recuerdos": [
            "una cadena suelta, no un objeto",
            {"contenido": ""},
            {"contenido": "x" * (puente.MAX_CONTENIDO + 1)},
            {"contenido": "este sí"}]})
        self.assertEqual({"nuevos": 1, "repetidos": 0, "rechazados": 3, "total": 4}, recuento)

    def test_la_llave_tampoco_entra_desde_el_telefono(self):
        almac = Almacen()
        recuento = puente.fusionar(almac, {"version": 1, "recuerdos": [
            {"contenido": "mi token es cort-9f3a1b"}]}, llave="cort-9f3a1b")
        self.assertEqual(1, recuento["rechazados"])
        self.assertEqual([], almac.guardadas)

    def test_una_version_distinta_no_deja_nada_a_medias(self):
        almac = Almacen(["ya estaba"])
        with self.assertRaises(ValueError):
            puente.fusionar(almac, {"version": 99, "recuerdos": [{"contenido": "nuevo"}]})
        self.assertEqual(["ya estaba"], almac.guardadas)

    def test_una_lista_que_no_es_lista_es_un_error_de_forma(self):
        with self.assertRaises(ValueError):
            puente.fusionar(Almacen(), {"version": 1, "recuerdos": "hola"})

    def test_pasarse_del_tope_se_rechaza_antes_de_tocar_disco(self):
        almac = Almacen()
        too_many = {"version": 1,
                    "recuerdos": [{"contenido": f"hecho {n}"} for n in range(puente.MAX_FILAS + 1)]}
        with self.assertRaises(ValueError):
            puente.fusionar(almac, too_many)
        self.assertEqual([], almac.guardadas)

    def test_un_objeto_que_no_es_objeto(self):
        with self.assertRaises(ValueError):
            puente.fusionar(Almacen(), ["una", "lista"])


class TestConAlmacenDeVerdad(unittest.TestCase):
    """Sobre un `MemoryStore` real en `tempfile`: el puente tiene que hablar con él
    sin que nadie le mueva la memoria a la dueña."""

    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio.cleanup)
        self.ruta = pathlib.Path(self.directorio.name) / "memory.db"

    def almac(self, nombre):
        """Un `MemoryStore` de usar y tirar, cerrado al acabar (sin `ResourceWarning`)."""
        store = MemoryStore(self.ruta.with_name(nombre))
        self.addCleanup(store.close)
        return store

    def test_exportar_desde_el_almacen_real_y_volver_a_entrar(self):
        uno = self.almac("una.db")
        uno.remember("El usuario se llama Sandra")
        uno.remember("El usuario usa un Samsung A16")
        cuadro = puente.exportar(uno.filas(), origen="escritorio")
        self.assertEqual(2, cuadro["total"])

        otro = self.almac("otra.db")
        recuento = puente.fusionar(otro, cuadro)
        self.assertEqual(2, recuento["nuevos"])
        self.assertEqual(sorted(uno.all()), sorted(otro.all()))
        self.assertEqual(0, puente.fusionar(otro, cuadro)["nuevos"])

    def test_las_filas_del_almacen_traen_lo_que_el_puente_necesita(self):
        store = self.almac("filas.db")
        store.remember("El usuario se llama Sandra")
        filas = store.filas()
        self.assertEqual([{"id", "content", "created_at"}], [set(f) for f in filas])
        self.assertEqual([], store.filas(tope=0))  # el tope manda: nunca un SELECT sin límite


class TestQueSigaSiendoPuro(unittest.TestCase):
    """El puente no puede abrir la red ni el disco por su cuenta: es lo que hace que
    estas pruebas valgan en una máquina sin teléfono delante."""

    PERMITIDOS = {"__future__", "re"}
    PROHIBIDOS = ("subprocess", "os.system", "socket", "http", "urllib", "sqlite3",
                  "Runtime", "eval(", "exec(")

    def setUp(self):
        self.fuente = (pathlib.Path(__file__).resolve().parents[1]
                       / "cort_core" / "puente.py").read_text(encoding="utf-8")

    def test_solo_importa_lo_que_puede_tocar_texto(self):
        arbol = ast.parse(self.fuente)
        nomes = set()
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                nomes.update(a.name.split(".")[0] for a in nodo.names)
            elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                nomes.add(nodo.module.split(".")[0])
        self.assertEqual(self.PERMITIDOS, nomes)

    def test_no_hay_ninguna_manera_de_tocar_el_sistema(self):
        sin_comentarios = "\n".join(
            l for l in self.fuente.splitlines() if not l.strip().startswith("#"))
        for bicho in self.PROHIBIDOS:
            self.assertNotIn(bicho, sin_comentarios, f"el puente no puede usar {bicho}")

    def test_no_abre_ningun_archivo(self):
        self.assertNotIn("open(", self.fuente)


if __name__ == "__main__":
    unittest.main()
