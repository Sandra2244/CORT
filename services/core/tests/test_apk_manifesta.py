"""Guardias del APK: el manifiesto, su versión y lo que firma `compilar.sh`.

Nacen de dos fallos medidos el 2026-10-15, ambos **imposibles de ver desde esta
máquina** (aquí no hay `javac` ni SDK: el binario lo compila el runner):

1. El run 18 de `compilar-apk` cayó sobre `af8b138` porque escribí, dentro de un
   comentario del manifiesto, dos guiones seguidos. En XML eso no es un
   comentario: es manifiesto mal formado, y `aapt2 link` se niega. El log del run
   es privado; lo que sí es público es la annotation, y ahí estaba el error.
2. El manifiesto llevaba `android:versionName="0.13.0"` fijado que sobrevivía a
   todas las Releases — dos verdades de la versión, y la del manifiesto mentía—.

Estas pruebas no compilan nada: leen los archivos de entrada del build. Cuestan
milisegundos y son la única forma de enterarse de esto *antes* de empujar.
"""
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
APK = RAIZ / "apps" / "apk"
MANIFIESTO = APK / "AndroidManifest.xml"
COMPILAR = APK / "compilar.sh"
JAVA = APK / "src" / "dev" / "sandra" / "cort" / "MainActivity.java"

ANDROIDE = "{http://schemas.android.com/apk/res/android}"


class TestManifiesto(unittest.TestCase):
    def setUp(self):
        self.texto = MANIFIESTO.read_text(encoding="utf-8")
        self.raiz = ET.fromstring(self.texto)

    def test_es_xml_bien_formado(self):
        """Que `ET` lo parses ya es la prueba: `aapt2` exige lo mismo."""
        self.assertEqual("manifest", self.raiz.tag)
        self.assertEqual("dev.sandra.cort", self.raiz.get("package"))

    def test_ningun_comentario_lleva_dos_guiones_seguidos(self):
        """El bug del run 18: un `--` dentro de `<!-- … -->` rompe el manifiesto."""
        for numero, comentario in enumerate(
                re.findall(r"<!--(.*?)-->", self.texto, re.S), start=1):
            self.assertNotIn("--", comentario,
                             f"comentario {numero} del manifiesto lleva dos guiones seguidos")

    def test_la_version_no_vive_en_el_manifiesto(self):
        """La escribe `compilar.sh` desde la etiqueta del corte: una sola verdad."""
        prohibidos = {ANDROIDE + "versionCode", ANDROIDE + "versionName"}
        self.assertEqual([], sorted(prohibidos & set(self.raiz.attrib)))

    def test_los_tres_permisos_y_su_required(self):
        pedidos = {e.get(ANDROIDE + "name"): e.get(ANDROIDE + "required")
                   for e in self.raiz if e.tag.endswith("uses-permission")}
        self.assertIn("android.permission.INTERNET", pedidos)
        for micro in ("android.permission.RECORD_AUDIO", "android.permission.CAMERA"):
            self.assertIn(micro, pedidos, micro)
            self.assertEqual("false", pedidos[micro],
                             f"{micro} debe ser required=false: sin teléfono delante no se instala distinto")

    def test_la_actividad_es_launchable_y_exported(self):
        actividades = [e for e in self.raiz.iter() if e.tag.endswith("activity")]
        self.assertEqual(1, len(actividades), "el APK es una sola actividad")
        actividad = actividades[0]
        self.assertEqual("true", actividad.get(ANDROIDE + "exported"))
        filtros = [e for e in actividad.iter() if e.tag.endswith("intent-filter")]
        acciones = [e.get(ANDROIDE + "name") for f in filtros for e in f.iter()
                    if e.tag.endswith("action")]
        self.assertIn("android.intent.action.MAIN", acciones)
        self.assertIn("android.intent.category.LAUNCHER",
                      [e.get(ANDROIDE + "name") for f in filtros for e in f.iter()
                       if e.tag.endswith("category")])


class TestCompilar(unittest.TestCase):
    def setUp(self):
        self.texto = COMPILAR.read_text(encoding="utf-8")

    def test_la_version_y_el_codigo_vienen_del_argumento(self):
        self.assertIn('--version-code "$CODE"', self.texto)
        self.assertIn('--version-name "$VERSION"', self.texto)
        # Y el `1` fijado de antes no vuelve: fue la causa de que Android creyera
        # que cada Release era la misma aplicación ya instalada.
        self.assertNotIn("--version-code 1", self.texto)

    def test_el_codigo_se_deriva_con_suelo_uno(self):
        self.assertIn("CODE=$(( 10#$MA * 10000 + 10#$MI * 100 + 10#$PA ))", self.texto)
        self.assertIn('[ "$CODE" -ge 1 ] || CODE=1', self.texto)

    def test_firma_cuenta_version_y_codigo(self):
        """`…-firma.txt` es la única ventana pública del build: tiene que decir qué
        versión salió, no sólo con qué llave."""
        self.assertIn('echo "APK de CORT $VERSION (versionCode $CODE)"', self.texto)


class TestPaquete(unittest.TestCase):
    def test_manifiesto_y_java_dicen_el_mismo_paquete(self):
        raiz = ET.fromstring(MANIFIESTO.read_text(encoding="utf-8"))
        java = JAVA.read_text(encoding="utf-8")
        self.assertEqual("dev.sandra.cort", raiz.get("package"))
        self.assertIn("package dev.sandra.cort;", java)

    def test_el_java_sigue_sin_androidx(self):
        """Regla escrita en el README del APK: una actividad de `android.app` y
        `android.webkit`, nada más — eso es lo que compila sin Gradle—.
        """
        java = JAVA.read_text(encoding="utf-8")
        for importado in re.findall(r"^import ([\w.]+);", java, re.M):
            self.assertTrue(importado.startswith(("android.", "java.", "dev.sandra.cort")),
                            f"import fuera de la lista cerrada: {importado}")


if __name__ == "__main__":
    unittest.main()
