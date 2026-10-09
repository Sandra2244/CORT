import importlib
import os, sys, pathlib, tempfile, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from cort_core.memory.store import MemoryStore
from cort_core.memory.facts import extract


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = pathlib.Path(self.tmp.name) / "memory.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_remember_and_recall(self):
        store = MemoryStore(self.db)
        store.remember("El usuario se llama Sandra")
        self.assertIn("El usuario se llama Sandra", store.recall("¿cómo me llamo?"))

    def test_persists_across_reopen(self):
        """Criterio del ROADMAP: la memoria sobrevive a reiniciar el proceso."""
        first = MemoryStore(self.db)
        first.remember("El usuario estudia ingeniería")
        first.close()
        reopened = MemoryStore(self.db)
        self.assertIn("El usuario estudia ingeniería", reopened.recall("qué estudio"))

    def test_does_not_duplicate(self):
        store = MemoryStore(self.db)
        a = store.remember("Al usuario le gusta el café")
        b = store.remember("Al usuario le gusta el café")
        self.assertEqual(a, b)
        self.assertEqual(len(store.all()), 1)

    def test_recall_empty_when_nothing_matches(self):
        store = MemoryStore(self.db)
        store.remember("El usuario se llama Sandra")
        self.assertEqual([], store.recall("cuánto es dos más dos"))

    def test_recall_ignores_stopwords(self):
        """Palabras funcionales como 'como' o 'que' no deben traerse recuerdos al azar."""
        store = MemoryStore(self.db)
        store.remember("El usuario se llama Sandra")
        self.assertEqual([], store.recall("y eso como que"))

    def test_context_rescues_a_question_with_no_root_in_common(self):
        """El fallo real: '¿qué sabes de mí?' no comparte raíz con 'se llama Sandra',
        así que recall devuelve vacío y el modelo contestaba que no conocía al
        usuario teniendo los datos delante."""
        store = MemoryStore(self.db)
        store.remember("El usuario se llama Sandra")
        store.remember("El usuario estudia ingeniería")
        self.assertEqual([], store.recall("¿qué sabes de mí?"))
        self.assertEqual(["El usuario se llama Sandra", "El usuario estudia ingeniería"],
                         store.context_for("¿qué sabes de mí?"))

    def test_context_prefers_matches_over_recent(self):
        """Con coincidencias no se diluye el recuerdo relevante metiendo todo."""
        store = MemoryStore(self.db)
        store.remember("El usuario se llama Sandra")
        store.remember("Al usuario le gusta el café")
        self.assertEqual(["Al usuario le gusta el café"],
                         store.context_for("qué bebida me gusta"))

    def test_context_is_bounded(self):
        """Cada token de contexto se paga en el prompt, y evaluar el prompt es lo
        caro de esta máquina: el rescate no puede crecer sin techo."""
        store = MemoryStore(self.db)
        for i in range(20):
            store.remember(f"Dato número {i}")
        self.assertEqual(6, len(store.context_for("¿qué sabes de mí?")))
        self.assertEqual(["Dato número 19"], store.context_for("¿qué sabes de mí?", limit=1))

    def test_el_rescate_prioriza_lo_declarado_sobre_lo_reciente(self):
        """El criterio era "los más recientes" y medido era ruido: con 50
        "Preferencia NNN" escritos después del nombre, ésos tapaban al nombre.
        Ahora el orden lo dice el contenido, no la fecha."""
        store = MemoryStore(self.db)
        store.remember("El usuario se llama Sandra")
        store.remember("Al usuario le gusta el café")
        for i in range(50):
            store.remember(f"Preferencia {i}")
        ctx = store.context_for("¿qué sabes de mí?")
        self.assertEqual(["El usuario se llama Sandra", "Al usuario le gusta el café"], ctx[:2])
        self.assertEqual([f"Preferencia {i}" for i in (49, 48, 47, 46)], ctx[2:])

    def test_el_rescate_cabe_una_consulta_y_no_vaciar_la_base(self):
        """`all()[-limit:]` leía todos los recuerdos para quedarse con seis. Con
        el techo en 200 da igual; con el `context_for` preguntando en cada turno
        no. Se spy-ea la conexión: si vuelve a haber un escaneo sin `LIMIT`, esto
        lo pilla."""
        store = MemoryStore(self.db)
        store.remember("El usuario se llama Sandra")

        class Proxy:
            def __init__(self, conn):
                self.conn = conn
                self.sql: list[str] = []

            def execute(self, statement, *args, **kwargs):
                self.sql.append(statement)
                return self.conn.execute(statement, *args, **kwargs)

        proxy = Proxy(store.conn)
        store.conn = proxy
        store.context_for("¿qué sabes de mí?")
        rescate = [s for s in proxy.sql if "CASE" in s]
        self.assertEqual(1, len(rescate))
        self.assertIn("LIMIT", rescate[0])
        self.assertNotIn("SELECT content FROM memories ORDER BY id", proxy.sql)

    def test_creates_missing_parent_dir(self):
        nested = pathlib.Path(self.tmp.name) / "a" / "b" / "memory.db"
        store = MemoryStore(nested)
        store.remember("prueba")
        self.assertTrue(nested.exists())

    def test_name_survives_restart(self):
        """Criterio literal del ROADMAP fase 1: CORT recuerda tu nombre tras reiniciar."""
        first = MemoryStore(self.db)
        for fact in extract("hola, me llamo Sandra"):
            first.remember(fact)
        first.close()
        reopened = MemoryStore(self.db)
        self.assertEqual("Sandra", reopened.name_of_user())

    def test_name_is_none_without_facts(self):
        self.assertIsNone(MemoryStore(self.db).name_of_user())

    def test_rejects_empty_fact(self):
        store = MemoryStore(self.db)
        with self.assertRaises(ValueError):
            store.remember("   ")


class TestPrune(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = pathlib.Path(self.tmp.name) / "memory.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_drops_the_oldest(self):
        store = MemoryStore(self.db)
        for i in range(10):
            store.remember(f"Dato número {i}")
        self.assertEqual(4, store.prune(keep=6))
        self.assertEqual([f"Dato número {i}" for i in range(4, 10)], store.all())

    def test_never_prunes_the_name(self):
        """El nombre es casi siempre el recuerdo más antiguo, y es del que dependen
        el saludo y '¿cómo me llamo?'. Podarlo sería olvidar lo único imprescindible."""
        store = MemoryStore(self.db)
        store.remember("El usuario se llama Sandra")
        for i in range(10):
            store.remember(f"Dato número {i}")
        store.prune(keep=3)
        self.assertEqual("Sandra", store.name_of_user())

    def test_recall_survives_a_full_roadmap_case(self):
        """Criterio del ROADMAP: tras 300 recuerdos, seguir encontrando lo relevante."""
        store = MemoryStore(self.db)
        store.remember("El usuario se llama Sandra")
        for i in range(300):
            store.remember(f"Preferencia {i} del usuario")
        store.remember("El usuario estudia ingeniería")
        store.prune(keep=50)
        self.assertIn("El usuario estudia ingeniería", store.recall("¿qué estudio?"))
        self.assertEqual("Sandra", store.name_of_user())
        self.assertLessEqual(len(store.all()), 51)

    def test_prune_is_idempotent(self):
        store = MemoryStore(self.db)
        for i in range(5):
            store.remember(f"Dato número {i}")
        store.prune(keep=5)
        self.assertEqual(0, store.prune(keep=5))
        self.assertEqual(5, len(store.all()))


class TestFacts(unittest.TestCase):
    def test_name(self):
        self.assertEqual(["El usuario se llama Sandra"], extract("Hola, me llamo Sandra"))

    def test_name_variant(self):
        self.assertEqual(["El usuario se llama Ana"], extract("mi nombre es Ana"))

    def test_preserves_capitalization(self):
        """El regex va con re.I pero captura del texto original: no se pierde 'Sandra'."""
        self.assertEqual(["El usuario se llama SANDRA"], extract("ME LLAMO SANDRA"))

    def test_studies(self):
        self.assertEqual(["El usuario estudia ingeniería de software"],
                         extract("estudio ingeniería de software."))

    def test_stops_at_punctuation(self):
        """Un hecho termina en el primer signo: no se arrastra el resto de la frase."""
        self.assertEqual(["El usuario estudia ingeniería"],
                         extract("estudio ingeniería, y trabajo en paralelo"))

    def test_preference(self):
        self.assertEqual(["Al usuario le gusta el café"], extract("me gusta el café"))

    def test_nothing_to_extract(self):
        self.assertEqual([], extract("qué tiempo hace hoy"))

    def test_multiple_facts(self):
        self.assertEqual(2, len(extract("me llamo Sandra y me gusta el café")))


class TestDbPathOverride(unittest.TestCase):
    """`CORT_MEMORY_DB` decide qué cabeza usa un CORT: una demo no escribe encima
    de la memoria real de nadie, y ésa es la única forma de enseñar la interfaz
    con un saludo neutro sin moverle a nadie su base de datos."""

    def setUp(self):
        from cort_core.memory import store as store_module
        self.module = store_module
        self.original = os.environ.get("CORT_MEMORY_DB")
        self.addCleanup(self._restore)

    def _restore(self):
        if self.original is None:
            os.environ.pop("CORT_MEMORY_DB", None)
        else:
            os.environ["CORT_MEMORY_DB"] = self.original
        importlib.reload(self.module)

    def _reload(self):
        importlib.reload(self.module)
        return self.module.DB_PATH

    def test_env_var_wins(self):
        os.environ["CORT_MEMORY_DB"] = "/tmp/memoria-demo.db"
        self.assertEqual(pathlib.Path("/tmp/memoria-demo.db"), self._reload())

    def test_default_is_the_project_data_folder(self):
        os.environ.pop("CORT_MEMORY_DB", None)
        self.assertEqual("memory.db", self._reload().name)
        self.assertEqual("data", self._reload().parent.name)


if __name__ == "__main__":
    unittest.main()
