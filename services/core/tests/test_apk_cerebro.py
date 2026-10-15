"""El cerebro nativo del APK: la tabla de frases y su costura con el Java.

Desde `v0.15.0` CORT vive también dentro del teléfono, y esa parte del proyecto
tiene un problema de verificación conocido: **aquí no hay `javac`**, así que el
Java sólo se compila en el runner. Lo que sí se puede probar en esta máquina es
el **dato** sobre el que ese Java decide: `apps/apk/assets/habilidades.json`.

Estas pruebas leen la tabla y el Java a la vez, y exigen que las dos mitades
sigan hablándose. Cada una corresponde a un modo concreto de fallar en silencio
dentro de un móvil que nadie tiene delante:

* un patrón escrito con tille nunca casa (el habla se normaliza sin acentos),
* una acción nueva en la tabla sin su `case` en `Acciones.java` se traga la
  frase y no dice nada,
* un parámetro inventado (`volumen: "altísimo"`) llega a Java y no lo entiende
  nadie,
* un hueco de plantilla mal escrito (`{hora}` vs `{horas}`) se imprime tal cual.

Nada de esto abre un teléfono: son dos segundos de `make test`.
"""
import json
import re
import unicodedata
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
APK = RAIZ / "apps" / "apk"
TABLA = APK / "assets" / "habilidades.json"
FUENTE = APK / "src" / "dev" / "sandra" / "cort"
ACCIONES_JAVA = FUENTE / "Acciones.java"
CARA_JAVA = FUENTE / "Cara.java"
CEREBRO_JAVA = FUENTE / "Cerebro.java"

HUECOS = {"hora", "fecha", "resto", "lista", "valor"}


def normaliza(texto):
    """Espejo en Python de `Cerebro.normaliza` (Java). Si las dos mitades
    discrepan, la tabla casa distinto según quién la lea: por eso está aquí."""
    suelto = unicodedata.normalize("NFD", texto)
    sin_marcas = "".join(c for c in suelto if not unicodedata.combining(c))
    sin_signos = re.sub(r"[¿?¡!.,;:\"“”'()]", " ", sin_marcas.lower())
    return re.sub(r"\s+", " ", sin_signos).strip()


class TestTabla(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tabla = json.loads(TABLA.read_text(encoding="utf-8"))
        cls.reglas = cls.tabla["patrones"]
        cls.acciones = set(cls.tabla["acciones"])
        cls.parametros = cls.tabla.get("parametros", {})

    def test_existe_y_no_esta_vacia(self):
        self.assertGreaterEqual(len(self.reglas), 20,
                                "la tabla es el cerebro offline: veinte frases es su suelo")

    def test_las_ids_no_se_repiten(self):
        vistas = [r["id"] for r in self.reglas]
        self.assertEqual(len(vistas), len(set(vistas)), "dos reglas con el mismo id")

    def test_toda_accion_esta_en_la_lista_cerrada(self):
        """Regla 6 de `AGENTS.md`, también en el teléfono: no hay acción que no
        esté declarada arriba, y arriba no entra nada que ejecute comandos."""
        for regla in self.reglas:
            self.assertIn(regla["accion"], self.acciones,
                          f"{regla['id']}: acción fuera de la lista cerrada")

    def test_los_parametros_vienen_del_diccionario(self):
        for regla in self.reglas:
            param = regla.get("param")
            if param:
                permitidos = self.parametros.get(regla["accion"], [])
                self.assertIn(param, permitidos,
                              f"{regla['id']}: «{param}» no es un {regla['accion']} conocido")

    def test_los_patrones_estan_en_forma_normalizada(self):
        """Un patrón con tilde o con doble espacio **no puede casar jamas**: la
        frase hablada llega normalizada y la comparación es exacta."""
        for regla in self.reglas:
            self.assertTrue(regla["patrones"], f"{regla['id']} no tiene patrones")
            for patron in regla["patrones"]:
                self.assertEqual(normaliza(patron), patron,
                                 f"{regla['id']}: «{patron}» no está en forma normalizada")

    def test_un_patron_no_sombra_a_otro_exactamente(self):
        vistas = {}
        for regla in self.reglas:
            for patron in regla["patrones"]:
                clave = patron.split("{resto}")[0].strip()
                self.assertNotIn(clave, vistas,
                                 f"«{patron}» se repite: {vistas.get(clave)} y {regla['id']}")
                vistas[clave] = regla["id"]

    def test_los_patrones_con_resto_tienen_prefijo(self):
        for regla in self.reglas:
            for patron in regla["patrones"]:
                if "{resto}" in patron:
                    self.assertTrue(patron.split("{resto}")[0].strip(),
                                    f"{regla['id']}: patrón con {{resto}} sin prefijo")

    def test_los_huecos_de_las_respuestas_existen(self):
        for regla in self.reglas:
            for hueco in re.findall(r"\{(\w+)\}", regla.get("respuesta", "")):
                self.assertIn(hueco, HUECOS, f"{regla['id']}: hueco {{ {hueco} }} desconocido")


class TestCosturaConJava(unittest.TestCase):
    """La tabla y el Java se leen en sentidos opuestos: Java parsea la tabla, y
    estas pruebas leen los dos archivos. Si uno de los dos cambia solo, esto
    revienta antes de empujar."""

    @classmethod
    def setUpClass(cls):
        cls.tabla = json.loads(TABLA.read_text(encoding="utf-8"))
        cls.acciones = {r["accion"] for r in cls.tabla["patrones"]}
        cls.acciones_java = ACCIONES_JAVA.read_text(encoding="utf-8")
        cls.cara = CARA_JAVA.read_text(encoding="utf-8")
        cls.cerebro = CEREBRO_JAVA.read_text(encoding="utf-8")

    def test_toda_accion_de_la_tabla_tiene_su_case_en_java(self):
        casos = set(re.findall(r'case "(\w+)":', self.acciones_java))
        self.assertEqual(set(), self.acciones - casos,
                         "la tabla ofrece una acción que `Acciones.java` no sabe ejecutar")

    def test_los_huecos_prometidos_se_rellenan(self):
        rellenos = set(re.findall(r'replace\("\{(\w+)\}"', self.acciones_java))
        usados = set()
        for regla in self.tabla["patrones"]:
            usados |= set(re.findall(r"\{(\w+)\}", regla.get("respuesta", "")))
        self.assertEqual(set(), usados - rellenos,
                         "una respuesta pide un hueco que `rellena()` no escribe")

    def test_lo_que_se_puede_aprender_es_lista_cerrada_y_sin_datos(self):
        """`Cara.proponer` ofrece acciones a la dueña para que CORT aprenda
        frases nuevas. Una habilidad aprendida se guarda con **la frase entera**
        como `resto` y sin `param`, así que sólo valen las acciones que
        contestan sin necesitar nada: las que tienen parámetro en la tabla
        (`volumen`, `abrir`, `saber`) y las que lo piden dicho
        (`alarma`, `cronometro`, `guardar`, `buscar`) quedarían vacías."""
        bloque = self.cara[self.cara.index("APRENDIBLES"):self.cara.index("private final")]
        aprendibles = set(re.findall(r'"(\w+)"', bloque))
        self.assertTrue(aprendibles, "la lista de aprendibles desapareció")
        self.assertEqual(set(), aprendibles - self.acciones,
                         "se ofrece aprender una acción que la tabla no tiene")
        self.assertEqual(set(), aprendibles - {"decir", "hora", "fecha", "listar"},
                         "se ofrece aprender una acción que necesita un dato que "
                         "la habilidad aprendida no puede tener")
        con_param = {k["accion"] for k in self.tabla["patrones"] if k.get("param")}
        self.assertEqual(set(), aprendibles & con_param,
                         "se ofrece aprender una acción que necesita parámetro")

    def test_el_java_lee_la_tabla_por_su_nombre(self):
        self.assertIn('open("habilidades.json")', self.cerebro)
        self.assertIn('tabla.optJSONArray("patrones")', self.cerebro)

    def test_la_normalizacion_de_java_mira_los_mismos_signos(self):
        """El conjunto de signos que Java borra tiene que ser el que borra este
        espejo en Python; si no, un patrón pasa la prueba y muere en el móvil."""
        java = re.search(r'replaceAll\("\[(.*?)\]", " "\)', self.cerebro)
        self.assertIsNotNone(java, "cambió la normalización de Java y este espejo miente")
        # El archivo fuente dice `\"` porque así lo exige el literal de cadena de
        # Java; lo que ve su motor de regex en tiempo de ejecución es la comilla
        # desnuda, que es la que quita el espejo de Python. Sin este desescape la
        # comparación acusaría un `\` que no existe dentro de la clase.
        self.assertEqual(set(java.group(1).replace('\\"', '"')),
                         set("¿?¡!.,;:\"“”'()"))


class TestSimbolosDeAndroid(unittest.TestCase):
    """El único `javac` que tiene este proyecto vive en un runner, y un símbolo
    inventado de `android.provider.*` cuesta un Run rojo y veinte minutos de
    cuota. Esta lista es la documentación pública de Android copiada aquí: lo que
    no esté, no existe, y se detecta en dos segundos de `make test`.

    Nace de un fallo propio y medido en el código: el primer borrador de
    `Acciones.cronometro` usaba `AlarmClock.ACTION_SHOW_TIMER` y
    `AlarmClock.EXTRA_TIME_IN_MILLIS`, dos constantes que **no** están en el SDK.
    """

    # android.provider.AlarmClock
    ALARMCLOCK = {"ACTION_SET_ALARM", "ACTION_SET_TIMER", "ACTION_SHOW_ALARMS",
                  "ACTION_SHOW_TIMERS", "ACTION_DISMISS_ALARM", "ACTION_INSPECT_ALARM",
                  "EXTRA_HOUR", "EXTRA_MINUTES", "EXTRA_SECONDS", "EXTRA_MESSAGE",
                  "EXTRA_SKIP_UI", "EXTRA_VIBRATE", "EXTRA_DAYS_OF_WEEK",
                  "EXTRA_RINGTONE", "EXTRA_COUNTDOWN", "EXTRA_SILENT"}
    # android.provider.Settings
    SETTINGS = {"ACTION_SETTINGS", "ACTION_DATE_SETTINGS", "ACTION_INPUT_METHOD_SETTINGS",
                "ACTION_SOUND_SETTINGS", "ACTION_DISPLAY_SETTINGS", "ACTION_LOCALE_SETTINGS",
                "ACTION_WIFI_SETTINGS", "ACTION_APPLICATION_SETTINGS", "ACTION_ACCESSIBILITY_SETTINGS"}
    # android.content.Intent (sólo las constantes que el APK usa o podría usar)
    INTENT = {"ACTION_MAIN", "ACTION_DIAL", "ACTION_WEB_SEARCH", "ACTION_VIEW",
              "ACTION_SEND", "ACTION_SET_ALARM",
              "CATEGORY_APP_BROWSER", "CATEGORY_APP_MUSIC", "CATEGORY_APP_MESSAGING",
              "CATEGORY_APP_EMAIL", "CATEGORY_APP_CALENDAR", "CATEGORY_APP_CONTACTS",
              "CATEGORY_APP_CLOCK", "CATEGORY_APP_CALCULATOR",
              "FLAG_ACTIVITY_NEW_TASK", "FLAG_ACTIVITY_CLEAR_TOP", "EXTRA_TEXT"}
    # android.media.AudioManager
    AUDIO = {"STREAM_MUSIC", "STREAM_RING", "STREAM_ALARM", "STREAM_NOTIFICATION",
             "ADJUST_RAISE", "ADJUST_LOWER", "ADJUST_MUTE", "ADJUST_UNMUTE",
             "FLAG_SHOW_UI", "FLAG_ALLOW_RINGER_MODES", "RINGER_MODE_NORMAL",
             "RINGER_MODE_SILENT", "MODE_NORMAL"}
    # android.speech.*
    VOZ = {"ACTION_RECOGNIZE_SPEECH", "EXTRA_LANGUAGE", "EXTRA_LANGUAGE_MODEL",
           "EXTRA_MAX_RESULTS", "EXTRA_CALLING_PACKAGE", "EXTRA_PARTIAL_RESULTS",
           "LANGUAGE_MODEL_FREE_FORM", "LANGUAGE_MODEL_WEB_SEARCH",
           "RESULTS_RECOGNITION", "ERROR_AUDIO", "ERROR_CLIENT",
           "ERROR_INSUFFICIENT_PERMISSIONS", "ERROR_NETWORK", "ERROR_NETWORK_TIMEOUT",
           "ERROR_NO_MATCH", "ERROR_RECOGNIZER_BUSY", "ERROR_SERVER", "ERROR_SPEECH_TIMEOUT",
           "LANG_MISSING_DATA", "LANG_NOT_SUPPORTED", "QUEUE_FLUSH", "QUEUE_ADD", "SUCCESS",
           "ERROR"}
    CERRADA = {
        "AlarmClock": ALARMCLOCK, "Settings": SETTINGS, "Intent": INTENT,
        "AudioManager": AUDIO, "RecognizerIntent": VOZ, "SpeechRecognizer": VOZ,
        "TextToSpeech": VOZ,
    }
    # Constantes de una sola clase, para no mezclarlas con las de arriba.
    OTROS = {"EditorInfo": {"IME_ACTION_SEND", "IME_ACTION_GO", "IME_ACTION_DONE"},
             "PackageManager": {"PERMISSION_GRANTED", "PERMISSION_DENIED"},
             "Build": {"MANUFACTURER", "MODEL", "VERSION", "SDK_INT"},
             "View": {"FOCUS_DOWN", "FOCUS_UP", "VISIBLE", "INVISIBLE", "GONE"}}

    @classmethod
    def setUpClass(cls):
        cls.fuentes = {p.name: p.read_text(encoding="utf-8")
                       for p in sorted(FUENTE.glob("*.java"))}

    def test_ninguna_constante_de_android_esta_inventada(self):
        for nombre, texto in self.fuentes.items():
            for clase, simbolo in re.findall(
                    r"\b(AlarmClock|Settings|Intent|AudioManager|RecognizerIntent"
                    r"|SpeechRecognizer|TextToSpeech|EditorInfo|PackageManager|Build|View)"
                    r"\.([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*)(?![a-z])", texto):
                permitidas = self.CERRADA.get(clase) or self.OTROS.get(clase)
                self.assertIsNotNone(permitidas, f"{clase} fuera del diccionario")
                self.assertIn(simbolo, permitidas,
                              f"{nombre}: {clase}.{simbolo} no existe en el SDK de Android")

    def test_los_simbolos_de_api_reciente_estan_detras_de_su_comprobacion(self):
        """`ACTION_SHOW_ALARMS` es de API 29 y el suelo del APK es 26: usarla sin
        mirar `SDK_INT` no falla al compilar — falla al instalar en un móvil
        viejo, que es el fallo que aquí no se puede ver con un dedo—.
        """
        java = self.fuentes["Acciones.java"]
        uso = java.index("setAction(AlarmClock.ACTION_SHOW_ALARMS)")
        # Se mira hacia atrás desde la **llamada**, no desde la primera aparición
        # de la constante: la primera está en un comentario que explica justo esto.
        self.assertIn("SDK_INT", java[max(0, uso - 260):uso],
                      "ACTION_SHOW_ALARMS (API 29) se usa sin comprobar la versión")

    def test_el_java_no_escribe_en_kotlin_lo_que_es_java(self):
        """`readableDatabase` / `writableDatabase` son **métodos**
        (`getReadableDatabase()`); la forma corta existe en Kotlin y en Java no, y
        así lo escribió este archivo la primera vez. Costó el Run e519f35
        (`cannot find symbol: variable readableDatabase`, cinco veces) y es
        exactamente el error que aquí no puede ver ningún compilador porque no
        hay `javac` en la máquina: por eso lo ve una prueba y no un editor.
        """
        for nombre, texto in self.fuentes.items():
            for kotlinismo in ("readableDatabase.", "writableDatabase.", "database.use("):
                self.assertNotIn(kotlinismo, texto,
                                 f"{nombre}: `{kotlinismo[:-1]}` no es un campo, es un getter")

    def test_el_java_no_llama_a_ningun_shell(self):
        """Regla 6 de `AGENTS.md` también dentro del teléfono: CORT no ejecuta
        comandos, ejecuta intenciones de la lista cerrada."""
        for nombre, texto in self.fuentes.items():
            for prohibido in ("Runtime.getRuntime", "ProcessBuilder", "exec(", "/system/bin"):
                self.assertNotIn(prohibido, texto, f"{nombre}: {prohibido}")


if __name__ == "__main__":
    unittest.main()
