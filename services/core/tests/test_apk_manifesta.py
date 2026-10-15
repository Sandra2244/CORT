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

Desde `v0.15.0` hay una tercera razón de ser: el APK ya no es sólo un WebView,
lleva nueve archivos Java y un activo JSON. Aquí no hay `javac`, así que lo que
estas guardias pueden comprobar es la forma —el paquete, la lista cerrada de
`import`, que los activos se enlacen y que los permisos sigan siendo los cuatro
prometidos—; la semántica del cerebro nativo la prueba `test_apk_cerebro.py`.
"""
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
APK = RAIZ / "apps" / "apk"
MANIFIESTO = APK / "AndroidManifest.xml"
COMPILAR = APK / "compilar.sh"
FUENTES = APK / "src" / "dev" / "sandra" / "cort"
JAVA = FUENTES / "MainActivity.java"

ANDROIDE = "{http://schemas.android.com/apk/res/android}"

# La lista cerrada de permisos del APK. `MODIFY_AUDIO_SETTINGS` llega en
# v0.15.0 porque la cara nativa sube y baja el volumen del teléfono; es un
# permiso **normal** (se concede al instalar), y por eso puede estar aquí. Un
# permiso *dangerous* fuera de los dos que la usuaria ve en el diálogo de
# runtime —micrófono y cámara— sería pedirle algo nuevo sin necesidad.
PERMISOS = {"android.permission.INTERNET", "android.permission.RECORD_AUDIO",
            "android.permission.CAMERA", "android.permission.MODIFY_AUDIO_SETTINGS"}


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

    def test_los_permisos_son_la_lista_cerrada_de_cuatro(self):
        pedidos = {e.get(ANDROIDE + "name"): e.get(ANDROIDE + "required")
                   for e in self.raiz if e.tag.endswith("uses-permission")}
        self.assertEqual(PERMISOS, set(pedidos),
                         "el APK pide permisos distintos de los cuatro prometidos a la dueña")
        for micro in ("android.permission.RECORD_AUDIO", "android.permission.CAMERA",
                      "android.permission.MODIFY_AUDIO_SETTINGS"):
            self.assertEqual("false", pedidos[micro],
                             f"{micro} debe ser required=false: sin teléfono delante no se instala distinto")

    def test_todo_lo_que_se_puede_negar_es_requitable(self):
        """`required=false` no es decoración: es lo que deja instalar el APK en un
        teléfono sin micrófono o sin cámara. La única excepción honesta es
        INTERNET, que el WebView necesita para vivir."""
        pedidos = {e.get(ANDROIDE + "name"): e.get(ANDROIDE + "required")
                   for e in self.raiz if e.tag.endswith("uses-permission")}
        for nombre, requerido in pedidos.items():
            if nombre == "android.permission.INTERNET":
                continue
            self.assertEqual("false", requerido, nombre)
        funciones = {e.get(ANDROIDE + "name"): e.get(ANDROIDE + "required")
                     for e in self.raiz if e.tag.endswith("uses-feature")}
        self.assertEqual({}, {k: v for k, v in funciones.items() if v != "false"},
                         "un uses-feature obligatorio filtraría teléfonos de la Release")

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

    def test_los_activos_se_enlazan(self):
        """`-A assets`: sin esa bandera el JSON de la tabla de frases se queda en
        el repo y `getAssets().open()` falla en el teléfono — la cara nativa
        abriría con la boca vacía, y aquí no hay un `javac` que lo avise—.
        """
        self.assertIn("-A assets \\", self.texto)

    def test_el_java_de_todas_las_fuentes_esta_en_el_build(self):
        """`javac` compila `$(find src -name '*.java')`: si alguien cambia la
        Find por una lista fija, los archivos nuevos no entran al APK y el
        fallo sólo se ve en el teléfono."""
        self.assertIn("$(find src -name '*.java')", self.texto)


class TestPaquete(unittest.TestCase):
    def setUp(self):
        self.fuentes = sorted(FUENTES.glob("*.java"))

    def test_hay_fuentes_y_el_manifiesto_dicen_el_mismo_paquete(self):
        raiz = ET.fromstring(MANIFIESTO.read_text(encoding="utf-8"))
        self.assertEqual("dev.sandra.cort", raiz.get("package"))
        self.assertGreaterEqual(len(self.fuentes), 9,
                                "la cara nativa son nueve archivos; si faltan, el build no los compiló")
        for java in self.fuentes:
            texto = java.read_text(encoding="utf-8")
            self.assertIn("package dev.sandra.cort;", texto, java.name)

    def test_el_paquete_del_manifiesto_coincide_con_la_actividad(self):
        """`.MainActivity` se resuelve contra `package=`: si los dos se separan,
        Android instala un APK que no arranca, y el pipeline sale verde igual.
        """
        raiz = ET.fromstring(MANIFIESTO.read_text(encoding="utf-8"))
        actividad = next(e for e in raiz.iter() if e.tag.endswith("activity"))
        nombre = actividad.get(ANDROIDE + "name")
        self.assertTrue(nombre.startswith("."), nombre)
        self.assertEqual("dev.sandra.cort" + nombre, "dev.sandra.cort.MainActivity")

    def test_los_imports_son_la_lista_cerrada_sin_androidx(self):
        """Regla escrita en el README del APK: sólo `android.*`, `java.*` y
        `org.json.*` —eso es lo que compila con `aapt2` + `javac` + `d8` sin
        Gradle y sin descargar una sola dependencia—. `org.json` entra desde
        v0.15.0 porque viene **dentro** de `android.jar`, no del Maven.
        """
        for java in self.fuentes:
            texto = java.read_text(encoding="utf-8")
            for importado in re.findall(r"^import ([\w.]+);", texto, re.M):
                self.assertTrue(
                    importado.startswith(("android.", "java.", "org.json.")),
                    f"import fuera de la lista cerrada en {java.name}: {importado}")

    def test_ningun_archivo_trae_kotlin_o_AndroidX(self):
        for java in self.fuentes:
            texto = java.read_text(encoding="utf-8")
            for prohibido in ("androidx.", "kotlin.", "com.google.android"):
                self.assertNotIn(prohibido, texto,
                                 f"{prohibido} en {java.name}: el pipeline no lo puede descargar")

    def test_la_clase_publica_se_llama_como_el_archivo(self):
        """`javac` lo exigiría, pero el `find` del script podría quedarse a
        medias: un archivo vacío o mal renombrado se ve aquí antes del run.
        """
        for java in self.fuentes:
            self.assertIsNotNone(
                re.search(r"\b(?:public\s+)?(?:final\s+)?class\s+" + java.stem + r"\b",
                          java.read_text(encoding="utf-8")),
                f"{java.name} no declara la clase que su nombre promete")


class TestProtocoloDeDivulgacion(unittest.TestCase):
    """El teléfono pregunta por UDP y el lanzador contesta: los dos lados tienen
    que decir **literalmente** lo mismo, y aquí no hay un import compartido que
    los ate. Esta prueba es la costura entre Java y Python.

    Sin ella, cambiar la mágica en un lado deja el descubrimiento mudo en el
    teléfono — y eso sólo se vería en un dedo, que es justo lo que no tenemos.
    """

    @classmethod
    def setUpClass(cls):
        import importlib.util
        lan = RAIZ / "scripts" / "cort.py"
        spec = importlib.util.spec_from_file_location("cort_launcher_manifesta", lan)
        cls.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.m)
        cls.java = JAVA.read_text(encoding="utf-8")

    def test_la_sonda_del_java_es_la_que_reconoce_el_lanzador(self):
        self.assertIn('String SONDA = "' + self.m.DESCUBRIR + '";', self.java)

    def test_larespuesta_del_lanzador_es_la_que_el_java_espera(self):
        self.assertIn('String RESPUESTA = "' + self.m.DESCUBRIR_RESPUESTA + '|";', self.java)

    def test_el_puerto_esta_del_mismo_numero_en_los_dos_lados(self):
        self.assertIn("int PUERTO_DIVULGACION = %d;" % self.m.DESCUBRIR_PUERTO, self.java)

    def test_el_java_emite_broadcast_sin_pedir_permiso_nuevo(self):
        # `setBroadcast(true)` sobre 255.255.255.255 no necesita nada más que
        # INTERNET, que ya está declarado; el descubrimiento por UDP tiene que
        # seguir funcionando con los cuatro permisos de siempre y ni uno más.
        self.assertIn("setBroadcast(true)", self.java)
        self.assertIn('InetAddress.getByName("255.255.255.255")', self.java)
        raiz = ET.fromstring(MANIFIESTO.read_text(encoding="utf-8"))
        permisos = {e.get(ANDROIDE + "name") for e in raiz.findall("uses-permission")}
        self.assertEqual(PERMISOS, permisos)

    def test_la_busqueda_corre_fuera_del_hilo_de_la_interfaz(self):
        # `receive()` bloquea: si se llamara en el hilo de la UI el anillo se
        # congela y la pantalla de estreno vuelve a ser un formulario quieto.
        inicio = self.java.index("private void buscarATelefonoSilencio()")
        trozo = self.java[inicio:inicio + 1300]
        self.assertIn("new Thread(", trozo)
        self.assertIn("runOnUiThread", trozo)
        antes, despues = trozo.split("new Thread(", 1)
        self.assertNotIn("preguntarEnLaRed()", antes, "la sonda no puede ir en el hilo de la UI")
        self.assertIn("preguntarEnLaRed()", despues)

    def test_el_portatil_que_no_esta_no_deja_al_telefono_sin_cara(self):
        """v0.15.0: el descubrimiento dejó de ser el portero de la app. Si no
        contesta nadie, MainActivity no muestra un formulario vacío: monta la
        cara nativa y le avisa a la dueña dónde está el portátil.
        """
        inicio = self.java.index("private void buscarATelefonoSilencio()")
        trozo = self.java[inicio:inicio + 1300]
        self.assertIn("cara != null", trozo)
        self.assertIn("decirDondeEstaElPortatil(false)", trozo)
        self.assertIn("mostrarOSetup", self.java)


def solo_codigo(texto):
    """El Java de **verdad**, sin comentarios ni literales de cadena.

    Hace falta porque la primera versión de `test_la_clave_guardada_nunca_vuelve_a
    _la_pantalla` contó cuatro usos de `nube.clave()` cuando había tres: el cuarto
    estaba dentro del comentario que explica precisamente que no se muestra. Un
    filtro que lee prosa como si fuera código acaba acusando (o perdonando) lo que
    no debe, así que aquí se quitan los bloques `/* */`, las líneas `//` y las
    cadenas `"..."` antes de buscar nada.
    """
    salida, i, n = [], 0, len(texto)
    while i < n:
        c = texto[i]
        if c == "/" and i + 1 < n and texto[i + 1] == "/":
            j = texto.find("\n", i)
            i = n if j < 0 else j
        elif c == "/" and i + 1 < n and texto[i + 1] == "*":
            j = texto.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif c in '"\'':
            j = i + 1
            while j < n:
                if texto[j] == "\\":
                    j += 2
                    continue
                if texto[j] == c:
                    break
                j += 1
            i = j + 1
        else:
            salida.append(c)
            i += 1
    return "".join(salida)


class TestAjustesDeNube(unittest.TestCase):
    """`v0.15.1`: la dueña eligió «nube si hay internet, local si no», y la mitad
    de la nube estaba **inaccesible** — `Nube` leía la clave de un `SharedPreferences`
    que ningún dedo podía escribir desde el teléfono—.

    Estas pruebas leen el fuente, como las demás: en esta máquina no hay `javac`,
    así que lo que se puede fijar es la forma de la pantalla y las tres promesas
    que la hacen segura — la clave no se muestra, no se guarda en el repo, y
    probarla no congela la cara—.
    """

    @classmethod
    def setUpClass(cls):
        cls.cara = (FUENTES / "Cara.java").read_text(encoding="utf-8")
        cls.nube = (FUENTES / "Nube.java").read_text(encoding="utf-8")
        cls.todos = {p.name: p.read_text(encoding="utf-8") for p in sorted(FUENTES.glob("*.java"))}
        cls.activos = (APK / "assets" / "habilidades.json").read_text(encoding="utf-8")

    def test_la_pantalla_existe_y_se_abre_desde_la_cara(self):
        self.assertIn("public void abrirAjustes()", self.cara)
        self.assertIn("setOnClickListener(v -> abrirAjustes())", self.cara)
        self.assertIn("actualizandoChip();", self.cara)

    def test_la_clave_se_teclea_en_un_campo_que_no_la_devela(self):
        """`TYPE_TEXT_VARIATION_PASSWORD` es lo que hace que Android pinte puntos
        en vez de la clave; sin eso, cualquier hombro cercano lee el secreto."""
        self.assertIn("InputType.TYPE_TEXT_VARIATION_PASSWORD", self.cara)
        self.assertIn("InputType.TYPE_TEXT_VARIATION_URI", self.cara)

    def test_la_clave_guardada_nunca_vuelve_a_la_pantalla(self):
        """A `nube.clave()` sólo se le piden **tres** cosas: si existe
        (`.isEmpty()`), cuántos caracteres tiene (`.length()`, para la pista del
        campo) y conservarse cuando la dueña no teclea nada. Ninguna de las tres
        la escribe en una pantalla, y ésa es la diferencia entre «el campo dice
        que hay una clave de 35 caracteres» y «el hombro de al lado lee el
        secreto»."""
        # Tres y sólo tres licencias. Se busca sobre `solo_codigo` porque el
        # comentario que explica esta misma regla nombra `nube.clave()`, y esa
        # mención no es un uso.
        codigo = solo_codigo(self.cara)
        self.assertIn("nube.clave().isEmpty()", codigo)
        self.assertIn("nube.clave().length()", codigo)
        self.assertIn("tecleada.isEmpty() ? nube.clave() : tecleada", codigo)
        # Y ninguna aparición más: fuera de medir si existe, medir su longitud y
        # conservarse, `nube.clave()` sólo puede acabar escrito en una pantalla.
        for m in re.finditer(r"nube\.clave\(\)", codigo):
            despues = codigo[m.end():m.end() + 12]
            anterior = codigo[max(0, m.start() - 24):m.start()].rstrip()
            self.assertTrue(despues.startswith((".isEmpty()", ".length()")) or anterior.endswith("?"),
                            f"la clave se está mostrando: nube.clave(){despues!r}")
        self.assertEqual(3, len(re.findall(r"nube\.clave\(\)", codigo)),
                        "aparece un uso nuevo de la clave: míralo uno a uno antes de pasar")
        self.assertNotIn("setText(nube.clave()", codigo)
        # Y el campo se construye con el valor vacío, no con la guardada.
        self.assertIn('"", true);', self.cara)

    def test_escribir_poco_no_borra_la_clave(self):
        """Dejar el campo en blanco significa «no la cambio», no «quítala»: si no,
        tocar el modelo obligaría a reescribir el secreto cada vez."""
        self.assertIn("tecleada.isEmpty() ? nube.clave() : tecleada", self.cara)

    def test_se_puede_apagar_sin_dejar_la_cara_a_medias(self):
        self.assertIn('nube.ajustar(modo[0], lo(base), lo(modelo), "");', self.cara)
        # Y sin clave la cara sigue respondiendo: la nube es un añadido, no un requisito.
        inicio = self.cara.index("private void porNube(")
        trozo = self.cara[inicio:inicio + 700]
        self.assertIn("if (!nube.configurada())", trozo)
        self.assertIn("proponer(dicho)", trozo)

    def test_probar_la_conexion_no_corre_en_el_hilo_de_la_interfaz(self):
        """`Nube.preguntar` es HTTPS bloqueante (12 s de conexión, 25 s de lectura).
        En el hilo de la UI congela la cara, y una cara congelada vuelve a ser el
        formulario que `v0.15.0` vino a quitar."""
        inicio = self.cara.index("private void probandoNube(")
        trozo = self.cara[inicio:inicio + 900]
        antes, despues = trozo.split("new Thread(", 1)
        self.assertNotIn("nube.preguntar(", antes, "la llamada no puede ir en el hilo de la UI")
        self.assertIn("nube.preguntar(", despues)
        self.assertIn("runOnUiThread", despues)

    def test_el_panel_de_ajustes_pinta_su_fondo_antes_que_su_texto(self):
        """Android da el `AlertDialog` con tema **claro** y la paleta de CORT es
        oscura: si el panel no se pinta su propio fondo, los avisos en blanco al
        54 % salen sobre blanco. Es un detalle que sólo se ve con un dedo delante,
        así que lo fija una línea de fuente en vez de una captura.
        """
        self.assertIn("desplegable.setBackgroundColor(Paleta.FONDO);", self.cara)

    def test_todo_campo_de_texto_de_la_cara_trae_su_vidrio_oscuro(self):
        """`new EditText(actividad)` dentro de un `AlertDialog` de Android sale
        sobre el blanco del diálogo, y la cara pinta su texto en `Paleta.CLARO`:
        blanco sobre blanco. Pasó en el diálogo de aprender frases (`v0.15.0`, sin
        instalar aún) y por eso la regla se fija aquí, no con una captura.
        """
        crea = [m.start() for m in re.finditer(r"new EditText\(actividad\)", self.cara)]
        self.assertEqual(3, len(crea), "la cara tiene tres campos: el de hablar, el de "
                                       "responder y los de ajustes")
        for inicio in crea:
            trozo = self.cara[inicio:inicio + 700]
            self.assertIn("setBackgroundColor(Paleta.CAMPO)", trozo,
                          "hay un campo de texto sin fondo oscuro: invisible sobre el diálogo")

    def test_ningun_secreto_del_mundo_real_vive_en_el_apk(self):
        """Regla 7: ni la clave de la nube ni la llave de firma se suben. Aquí se
        mide que en **ninguna** fuente ni activo hay una cadena con forma de clave
        de Anthropic/OpenAI, y que el valor por defecto del secreto está vacío."""
        forma = re.compile(r"sk-(?:ant-)?[A-Za-z0-9_\-]{16,}")
        for nombre, texto in self.todos.items():
            self.assertIsNone(forma.search(texto), f"{nombre}: hay una clave literal dentro")
        self.assertIsNone(forma.search(self.activos), "habilidades.json lleva una clave")
        self.assertIn('prefs.getString("clave", "")', self.nube)

    def test_la_unica_escritura_de_ese_almacen_es_el_ajustar_de_nube(self):
        """`Cara` no escribe `SharedPreferences` por su cuenta: si la pantalla
        empezara a guardar la clave por su lado, `Nube.configurada()` mentiría."""
        for prohibido in ('getSharedPreferences("cort-nube"', 'putString("clave"'):
            self.assertNotIn(prohibido, self.cara)
        self.assertIn('.putString("clave", clave).apply();', self.nube)

    def test_los_textos_de_la_cara_abren_y_cierran_su_comilla(self):
        """Español con «comillas angulares»: en `v0.15.0` una frase aprendida se
        anunciaba con `diré «hola"`, cerrando con la comilla de escape de Java. Es
        el tipo de errata que ningún compilador ve y que la dueña lee en la pantalla."""
        for nombre, texto in self.todos.items():
            self.assertEqual(texto.count("«"), texto.count("»"),
                             f"{nombre}: hay una « sin su » (o al revés)")


if __name__ == "__main__":
    unittest.main()
