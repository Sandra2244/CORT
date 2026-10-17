"""Pruebas de la guarda de empaquetado (scripts/empaquetar.py).

Por qué son necesarias y no decorativas: el 2026-10-17 apareció un ZIP del
proyecto con un `.env` de 26 variables **con valores reales** y el registro
`data/rechazos.jsonl` dentro. Esos ficheros nunca estuvieron en git; el error fue
empaquetar la carpeta a pelo. La única defensa que sirve es la que se ejecuta: si
esta guarda se cae en un merge, la próxima clave sale publicada otra vez.

Se importa `empaquetar.py` por ruta, igual que las pruebas del lanzador: el script
vive fuera del paquete `cort_core` y no piensa instalar nada para poder correr.
"""
import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

EMPAQUETAR = Path(__file__).resolve().parents[3] / "scripts" / "empaquetar.py"
REPO = EMPAQUETAR.parent.parent

# `v0.17.0`, `0.17.0-3-g…`, `v1.2`; el guion de prefijo es opcional porque una
# etiqueta sin `v` sigue siendo una versión.
_PARECE_VERSION = re.compile(r"^v?\d+\.\d+")


def cargar():
    especificacion = importlib.util.spec_from_file_location("cort_empaquetar", EMPAQUETAR)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


class TestGuarda(unittest.TestCase):
    def setUp(self):
        self.modulo = cargar()

    def test_un_env_con_valores_no_sale_jamas(self):
        """El caso que motivó el archivo: `.env` en la raíz del paquete."""
        self.assertEqual(self.modulo.revisar([".env"]), [".env"])

    def test_la_plantilla_si_viaja(self):
        """.env.example es documentación: prohibirla rompería la instalación."""
        self.assertEqual(self.modulo.revisar([".env.example"]), [])

    def test_los_entornos_virtuales_y_los_builds_estan_fuera(self):
        """Lo que hacía que el ZIP anterior pesara 171 MB con 94 % de basura."""
        sospechosas = [
            ".venv/Lib/site-packages/fastapi/applications.py",
            "apps/web/node_modules/three/build/three.module.js",
            "apps/web/android/app/build/intermediates/apk/debug/app-debug.apk",
            "services/core/cort_core/__pycache__/server.cpython-313.pyc",
        ]
        encontradas = self.modulo.revisar(sospechosas)
        self.assertEqual(len(encontradas), 4, f"se colaron: {set(sospechosas) - set(encontradas)}")

    def test_los_datos_personales_y_la_llave_de_firma_no_viajan(self):
        """La bitácora de rechazos, los `.vrm` ajenos y el keystore con su contraseña."""
        sospechosas = [
            "services/core/data/rechazos.jsonl",
            "services/core/data/agenda.json",
            "services/core/data/atuendos/cortana.vrm",
            "apps/apk/llave/cort.keystore",
            "apps/apk/llave/cort.keystore.pass",
        ]
        self.assertEqual(len(self.modulo.revisar(sospechosas)), 5)

    def test_un_paquete_limpio_pasa_sin_falsos_positivos(self):
        """El árbol real de fuente: código, docs y plantillas, nada de lo demás."""
        limpio = [
            "README.md",
            "AGENTS.md",
            ".env.example",
            ".gitignore",
            "Makefile",
            "docs/STATUS.md",
            "docs/assets/ventanas-vidrio-2026-10-11.png",
            "services/core/cort_core/server.py",
            "services/core/tests/test_empaquetar.py",
            "apps/web/src/App.tsx",
            "apps/web/package-lock.json",
            "apps/apk/src/com/cort/app/Cara.java",
            "apps/apk/README.md",
            "packaging/cort.iss",
            ".github/workflows/compilar-apk.yml",
        ]
        self.assertEqual(self.modulo.revisar(limpio), [])

    def test_una_lista_vacia_no_inventa_nada(self):
        self.assertEqual(self.modulo.revisar([]), [])


class TestArchivoReal(unittest.TestCase):
    """El extremo a extremo: que lo que produce `git archive` pase la guarda."""

    @unittest.skipUnless((REPO / ".git").exists(), "sin git no hay nada que empaquetar")
    def test_lo_versionado_pasa_la_guarda(self):
        modulo = cargar()
        with tempfile.TemporaryDirectory() as caja:
            ruta, entradas, bytes_ = modulo.empaquetar(REPO, Path(caja))
            self.assertTrue(ruta.exists(), "no se escribió el archivo")
            self.assertGreater(len(entradas), modulo.ENTRADAS_MINIMAS)
            self.assertGreater(bytes_, 10_000)
            coladas = modulo.revisar(entradas)
            self.assertEqual(coladas, [], f"el paquete lleva cosas prohibidas: {coladas[:5]}")

    @unittest.skipUnless((REPO / ".git").exists(), "sin git no hay versión que leer")
    def test_el_nombre_lleva_la_version_del_commit(self):
        """Un archivo sin versión no se puede reclamar en un foro: es el de siempre.

        Dos formas válidas y medida cada una. En el portátil hay etiquetas y
        `git describe` devuelve `v0.17.0-3-gea447c8`. En el run 39075588328 de
        GitHub el clon no traía etiquetas y `--always` cayó al hash (`ea447c84…`),
        que **también** rastrea el commit exacto: exigir sólo la primera forma
        ponía rojo el pipeline por una diferencia del clon, no del código. Lo que
        no puede salir nunca es un nombre vacío ni `sin-version`, porque ahí es
        donde el ZIP anónimo vuelve a confundirse con el de la semana pasada.
        """
        modulo = cargar()
        version = modulo.version_de(REPO)
        self.assertTrue(version, "la guarda devolvió una versión vacía")
        self.assertNotEqual(version, "sin-version")
        base = version.removesuffix("-dirty")
        cabeza = modulo.git(REPO, "rev-parse", "HEAD")
        es_version = bool(_PARECE_VERSION.match(base))
        es_hash = len(base) >= 7 and cabeza.startswith(base)
        self.assertTrue(
            es_version or es_hash,
            f"{version!r} no es ni etiqueta ni hash de HEAD ({cabeza[:12]!r})",
        )


if __name__ == "__main__":
    unittest.main()
