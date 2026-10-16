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
import json
import re
import subprocess
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


def bloques(codigo):
    """Cada `{ … }` del fuente como `(abierto, cerrado)`, en orden de aparición.

    Hace falta para poder decir si una llamada está **dentro** de un `try`: con las
    llaves emparejadas es la única forma de no confundirse mirando líneas sueltas.
    """
    pila, salida = [], []
    for numero, letra in enumerate(codigo):
        if letra == "{":
            pila.append(numero)
        elif letra == "}" and pila:
            salida.append((pila.pop(), numero))
    return salida


def envueltos(codigo, indice):
    """Los bloques que contienen una posición, del más interno al más externo."""
    return sorted([(a, c) for a, c in bloques(codigo) if a < indice < c],
                  key=lambda par: par[1] - par[0])


def esta_recogido(codigo, indice, excepciones):
    """¿La llamada de `indice` cae en un `try` con su `catch`, o en un método que
    declara el `throws`?

    Ésa es la pregunta que `javac` hace y que en esta máquina no se puede hacer: un
    `throws` declarado y sin recoger es error de compilación, y cuesta una Release.
    Valen las dos respuestas que Java admite —el `catch` de una de las excepciones
    declaradas, o el `throws` en la firma del método que envuelve la llamada—.
    """
    for abierto, cerrado in envueltos(codigo, indice):
        antes = codigo[:abierto].rstrip()
        if antes.endswith("try"):
            despues = codigo[cerrado + 1:cerrado + 260].lstrip()
            if despues.startswith("catch") and any(e in despues.split("{")[0]
                                                   for e in excepciones):
                return True
        if antes.endswith(")") and any("throws" in antes and e in antes
                                       for e in excepciones):
            return True
    return False


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


class TestPuenteDeMemoria(unittest.TestCase):
    """`v0.15.2`, deuda 2 del acuerdo Java: `cort.db` y `memory.db` ya se hablan.

    El puente está en dos lenguajes y no hay un `import` compartido que los ate, así
    que esta clase es la costura: los **números** del cuadro (versión, topes, ruta,
    puerto del core) se comparan con los de `puente.py` y con los del lanzador, y la
    derivación de la URL se reimplementa aquí en Python y se contraste contra la misma
    tabla de enlaces. Es el mismo método que ya fija las mágicas del UDP
    (`TestProtocoloDeDivulgacion`), y por las mismas razones: lo que se rompe se rompe
    en un teléfono.

    La segunda mitad de la clase es estructural y cara de ver en un móvil: que la
    lógica del cuadro siga **pura** (sin `java.net`, sin SQLite), que la llave de red se
    pase en los dos sentidos, que fusionar no borre y que la red no vaya en el hilo de
    la interfaz.
    """

    @classmethod
    def setUpClass(cls):
        import importlib.util

        def carga(nombre, archivo):
            """Un módulo por su ruta, sin tocar `sys.path`: la costura lee el mismo
            fuente que ejecuta el lanzador y el mismo que llama el teléfono."""
            spec = importlib.util.spec_from_file_location(nombre, archivo)
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
            return modulo

        cls.puente = carga("cort_puente_costura",
                           RAIZ / "services" / "core" / "cort_core" / "puente.py")
        cls.lanzador = carga("cort_lanzador_costura", RAIZ / "scripts" / "cort.py")
        cls.puente_java = (FUENTES / "Puente.java").read_text(encoding="utf-8")
        cls.sincroniza = (FUENTES / "Sincroniza.java").read_text(encoding="utf-8")
        cls.recuerdos = (FUENTES / "Recuerdos.java").read_text(encoding="utf-8")
        cls.cara = (FUENTES / "Cara.java").read_text(encoding="utf-8")
        cls.servidor = (RAIZ / "services" / "core" / "cort_core" / "server.py").read_text(
            encoding="utf-8")
        cls.todos = {p.name: p.read_text(encoding="utf-8") for p in sorted(FUENTES.glob("*.java"))}

    @staticmethod
    def solo_codigo(texto):
        """El fuente sin comentarios ni literales, para poder prohibir nombres y contar llaves.

        El truco lo aprendió `test_apk_cerebro.py` contando usos de una clase: la
        documentación de `Puente.java` **nombra** `java.net` y `HttpURLConnection`
        justamente para decir que no los usa, y una prohibición leída sobre el archivo
        entero habría fallado contra ese comentario.

        Se recorre el texto con un mini-escáner y no con tres `re.sub` en cadena, y la
        diferencia se midió: con los `sub` en hilera, `MainActivity.java` —que ya compila
        verde en el runner— salía con 58 llaves contra 60, porque el patrón de comentario
        `// …` se comía el resto de la línea dentro de una cadena (`"http://…"`). Aquí se
        consumen **literales primero que comentarios**, que es el orden en que los lee
        `javac`, y las cuentas cuadran.
        """
        salida = []
        i, n = 0, len(texto)
        while i < n:
            c = texto[i]
            if c in "\"'":                      # cadena o carácter: se tira entero
                marca = c
                i += 1
                while i < n and texto[i] != marca:
                    if texto[i] == "\\":
                        i += 1
                    elif texto[i] == "\n":
                        break                   # literal sin cerrar: no pasa en Java válido
                    i += 1
                i += 1
            elif texto.startswith("//", i):     # línea de comentario
                while i < n and texto[i] != "\n":
                    i += 1
            elif texto.startswith("/*", i):     # bloque, incluido el Javadoc
                hallado = texto.find("*/", i + 2)
                i = n if hallado < 0 else hallado + 2
            else:
                salida.append(c)
                i += 1
        return "".join(salida)

    # -- la costura numérica --------------------------------------------------------

    def test_los_numeros_del_cuadro_son_los_de_puentepy(self):
        for literal, esperado in (
                ("int VERSION = %d;", self.puente.VERSION),
                ("int MAX_CONTENIDO = %d;", self.puente.MAX_CONTENIDO),
                ("int MAX_FILAS = %d;", self.puente.MAX_FILAS),
                ("int MAX_BYTES = %d;", self.puente.MAX_BYTES)):
            self.assertIn(literal % esperado, self.puente_java,
                          f"{literal} no coincide con puente.py ({esperado}): "
                          "un cuadro de otra versión se rechaza en el portátil y en el "
                          "teléfono nadie sabe por qué")
        self.assertIn('String TIPO = "' + self.puente.exportar([])["tipo"] + '";',
                      self.puente_java)

    def test_la_ruta_y_el_puerto_son_los_que_el_portatil_escucha(self):
        self.assertIn('String RUTA = "/memoria/puente";', self.puente_java)
        self.assertIn('@app.get("/memoria/puente")', self.servidor)
        self.assertIn('@app.post("/memoria/puente")', self.servidor)
        self.assertIn("int PUERTO_API = %d;" % self.lanzador.PUERTO_CORE, self.puente_java,
                      "el puerto del core está escrito en dos lenguajes: si el lanzador "
                      "cambia su default, el teléfono tiene que cambiar el mismo número")

    def test_el_tope_real_de_un_viaje_es_aritmetica_y_no_un_numero_al_aire(self):
        """300 caracteres con tildes son 600 bytes en UTF-8 más el envoltorio del JSON."""
        self.assertIn("Math.min(MAX_FILAS, MAX_BYTES / (MAX_CONTENIDO * 3 + 64))",
                      self.puente_java)
        esperado = min(self.puente.MAX_FILAS,
                       self.puente.MAX_BYTES // (self.puente.MAX_CONTENIDO * 3 + 64))
        self.assertLess(esperado, self.puente.MAX_FILAS,
                        "si 500 filas cupieran siempre, el tope no serviría de nada")
        self.assertGreaterEqual(esperado, 200,
                                "un puente que sólo mueve 30 recuerdos no es un puente")

    # -- la derivación de la URL, espejada en Python --------------------------------

    @staticmethod
    def url_del_puente(enlace, puerto=8765):
        """Espejo en Python de `Puente.urlDelPuente`. Si las dos mitades discrepan, el
        teléfono llama a una URL que el portátil no escucha — y eso sólo se vería en un
        dedo—. Mismo método que `normaliza` en `test_apk_cerebro.py`."""
        limpio = (enlace or "").strip()
        esquema = ("https://" if limpio.startswith("https://")
                   else "http://" if limpio.startswith("http://") else None)
        if esquema is None:
            return None
        resto = limpio[len(esquema):]
        fin = len(resto)
        for indice, caracter in enumerate(resto):
            if caracter in "/?#":
                fin = indice
                break
        host = resto[:fin]
        if ":" in host:
            host = host.rsplit(":", 1)[0]
        if not host:
            return None
        where = limpio.find("?token=")
        if where < 0:
            where = limpio.find("&token=")
        token = ""
        if where >= 0:
            desde = limpio[where + len("?token="):]
            corte = next((i for i, c in enumerate(desde) if c in "&#"), len(desde))
            token = desde[:corte].strip()
        return (esquema + host + ":" + str(puerto) + "/memoria/puente"
                + ("?token=" + token if token else ""))

    ENLACES = [
        "http://192.168.100.5:8780/?token=llave-de-prueba",
        "http://192.168.100.5:8780/",
        "http://192.168.1.9/?token=abc",
        "https://cort.casa:8780/?token=abc&theme=2",
        "http://10.0.0.4:8780/#token=no-es-query",
        "  http://192.168.1.5:8780/?token=con-espacios-al-final  ",
        "",
        "192.168.1.5:8780/?token=abc",
        "http:///:8780/?token=abc",
        "ftp://192.168.1.5:8780/",
    ]

    def test_el_java_deriva_la_misma_url_que_el_espejo_en_python(self):
        # La derivación no se puede probar aquí (no hay `javac`), así que se fija su
        # **literal** en el fuente y su **regla** en este espejo: si alguien edita una
        # de las dos, la otra prueba lo cuenta.
        self.assertIn('esquema = "https://";', self.puente_java)
        self.assertIn('indexOf("?token=")', self.puente_java)
        self.assertIn('indexOf("&token=")', self.puente_java)
        self.assertIn('lastIndexOf(\':\')', self.puente_java)
        for enlace in self.ENLACES:
            esperado = self.url_del_puente(enlace, self.lanzador.PUERTO_CORE)
            if esperado is None:
                continue
            self.assertIn(str(self.lanzador.PUERTO_CORE), esperado)
            self.assertTrue(esperado.startswith("http") and "/memoria/puente" in esperado,
                            esperado)
        self.assertEqual(
            "http://192.168.100.5:8765/memoria/puente?token=llave-de-prueba",
            self.url_del_puente(self.ENLACES[0], self.lanzador.PUERTO_CORE),
            "la escena real: el enlace que divulgó el UDP, convertido en la ruta del puente")

    def test_los_enlaces_sin_forma_de_cort_no_abren_nada(self):
        for basura in ("", "192.168.1.5:8780/?token=abc", "http:///:8780", "ftp://x:8780/"):
            self.assertIsNone(self.url_del_puente(basura, self.lanzador.PUERTO_CORE))
        self.assertIn('return null;', self.puente_java)

    # -- la forma de las dos mitades ------------------------------------------------

    def test_la_logica_del_cuadro_sigue_sin_tocar_la_red_ni_el_disco(self):
        """`Puente.java` es la mitad pura, como `puente.py`: si algún día nombra
        `java.net` o SQLite, la lógica del cuadro deja de poder leerse sin un teléfono.

        Se lee sobre `solo_codigo`, no sobre el archivo: la propia documentación dice
        que no usa esos nombres, y contarlos ahí sería un falso positivo.
        """
        codigo = self.solo_codigo(self.puente_java)
        importos = re.findall(r"^import\s+([\w.]+);", codigo, re.M)
        self.assertTrue(importos, "Puente.java debería importar algo: está vacío")
        for permitido in importos:
            self.assertTrue(permitido.startswith("java.util.") or permitido.startswith("org.json."),
                            f"import no permitido en la mitad pura: {permitido}")
        for prohibido in ("java.net", "HttpURLConnection", "android.", "SQLiteDatabase",
                          "getWritableDatabase", "SharedPreferences", "Runtime.getRuntime"):
            self.assertNotIn(prohibido, codigo,
                             f"la mitad pura no puede nombrar {prohibido}")

    def test_la_red_esta_en_un_solo_sitio_y_pasa_la_llave_en_los_dos_sentidos(self):
        self.assertIn("HttpURLConnection", self.sincroniza)
        for nombre in ("Puente.java", "Recuerdos.java"):
            self.assertNotIn("HttpURLConnection", self.solo_codigo(self.todos[nombre]))
        self.assertIn("Puente.tokenDe(url)", self.sincroniza)
        self.assertIn("Puente.exportar(recuerdos, llave", self.sincroniza)
        self.assertIn("Puente.fusionar(recuerdos, delPortatil, llave)", self.sincroniza,
                      "sin `llave` el puente aceptaría un recuerdo que contenga el token")

    def test_fusionar_en_el_telefono_tampoco_borra(self):
        """Regla 3, del lado del aparato: un cuadro que llega no puede vaciar `cort.db`."""
        self.assertNotIn("DELETE FROM hechos", self.recuerdos)
        self.assertIn("public void recuerda(String contenido)", self.recuerdos)
        self.assertIn('guarda("nombre", nombre)', self.recuerdos,
                      "el nombre es la única forma canónica que el teléfono sabe leer; "
                      "sin esa regla sincroniza y sigue preguntando quién es la dueña")
        self.assertIn("implements Puente.Cabeza", self.recuerdos)

    def test_sincronizar_no_congela_la_cara(self):
        """Misma regla que el UDP y que la nube: `HttpURLConnection` bloquea, y dos
        conexiones en el hilo de la interfaz dejan el anillo quieto."""
        inicio = self.cara.index("private void sincronizando(")
        trozo = self.cara[inicio:inicio + 1400]
        self.assertIn("new Thread(", trozo)
        self.assertIn("runOnUiThread", trozo)
        antes, despues = trozo.split("new Thread(", 1)
        self.assertNotIn("sincroniza.sincronizar()", antes)
        self.assertIn("sincroniza.sincronizar()", despues)
        self.assertIn("sincroniza.hayPortatil()", antes,
                      "sin enlace guardado no se abre conexión: se explica y se vuelve")

    def test_el_puente_se_ve_en_la_hoja_de_herramientas(self):
        """Una superficie de herramientas, y una fila que existe aunque no haya
        portátil: la otra opción es que la sincronía no exista para la dueña."""
        self.assertIn("traer y llevar mis recuerdos al portátil", self.cara)
        self.assertIn("setOnClickListener(v -> sincronizando(salida))", self.cara)
        self.assertIn("sincroniza = new Sincroniza(", self.cara)

    def test_el_java_del_puente_cierra_lo_que_abre(self):
        """Sin `javac` en esta máquina, la llave sin cerrar se entera en el runner.

        Cuesta un Run de Actions y un commit entero: se cuentan `{} () []` sobre el
        fuente **sin comentarios ni literales** (`solo_codigo`, el mismo truco con que
        `test_apk_cerebro.py` dejó de contar menciones de un Javadoc como usos de una
        clase). No sustituye al compilador —no compila nada—, sólo corta el desbalance
        de teclear, que es el fallo que más veces he cometido escribiendo Java a mano.
        """
        for nombre, texto in sorted(self.todos.items()):
            codigo = self.solo_codigo(texto)
            for abre, cierra in (("{", "}"), ("(", ")"), ("[", "]")):
                self.assertEqual(codigo.count(abre), codigo.count(cierra),
                                 f"{nombre}: {abre}{cierra} desparejados "
                                 f"({codigo.count(abre)} frente a {codigo.count(cierra)})")

    def test_las_comillas_angulares_sigan_pareadas_en_todo_el_java(self):
        for nombre, texto in self.todos.items():
            self.assertEqual(texto.count("«"), texto.count("»"),
                             f"{nombre}: hay una « sin su »")


class TestAsistenteYVisibilidad(unittest.TestCase):
    """`v0.15.3`: dos superficies nuevas que **no se pueden ver desde esta máquina**.

    * Que CORT abra *cualquier* app instalada, y no sólo ocho categorías.
    * Que CORT pueda ser elegido asistente predeterminado del teléfono.

    Las dos viven dentro de un Android que nadie tiene delante y las dos fallan en
    silencio: un `<queries>` mal escrito da una lista de apps vacía y CORT responde
    «no la encontré» en un teléfono lleno; un `sessionService` con prefijo
    `android:` hace que el parser del sistema rechace la meta-datos y CORT **ni
    aparezca** en la lista de asistentes, sin ninguna pantalla que lo diga. Lo que
    fija el fuente de AOSP (`VoiceInteractionServiceInfo`) lo fija aquí una prueba,
    y con eso el primer intento en el Samsung ya no es a ciegas.
    """

    @classmethod
    def setUpClass(cls):
        cls.manifiesto = MANIFIESTO.read_text(encoding="utf-8")
        cls.raiz = ET.fromstring(cls.manifiesto)
        cls.xml_asistente = (APK / "res" / "xml" / "asistente.xml").read_text(encoding="utf-8")
        cls.fuentes = {p.name: p.read_text(encoding="utf-8")
                       for p in sorted(FUENTES.glob("*.java"))}
        cls.acciones = cls.fuentes["Acciones.java"]

    # -- ver cualquier app, sin el permiso que castiga Google ----------------------

    def test_el_manifiesto_consulta_los_lanzadores(self):
        """Sin este bloque, `queryIntentActivities` devuelve lista vacía desde
        Android 11 y «abre Spotify» se convierte en «no lo encontré»."""
        consultas = [e for e in self.raiz if e.tag == "queries"]
        self.assertEqual(1, len(consultas), "el manifiesto no declara su <queries>")
        acciones = [e.get(ANDROIDE + "name") for e in consultas[0].iter()
                    if e.tag.endswith("action")]
        categorias = [e.get(ANDROIDE + "name") for e in consultas[0].iter()
                      if e.tag.endswith("category")]
        self.assertIn("android.intent.action.MAIN", acciones)
        self.assertIn("android.intent.category.LAUNCHER", categorias)

    def test_el_permiso_prohibido_no_esta_en_el_manifiesto_ni_en_el_codigo(self):
        """`QUERY_ALL_PACKAGES` es el permiso que la tienda castiga y que este repo
        prometió no pedir. Se mira el manifiesto **entero** (ahí un comentario ya
        estaría pidiéndoselo al lector) y el Java **sin comentarios**, porque la
        documentación de `Acciones.java` nombra el permiso justamente para explicar
        por qué no se usa — y una prohibición leída sobre la prosa acusaría al
        comentario que la sostiene, que es el error que ya corrigió `solo_codigo`—.
        """
        self.assertNotIn("QUERY_ALL_PACKAGES", self.manifiesto)
        for nombre, texto in self.fuentes.items():
            self.assertNotIn("QUERY_ALL_PACKAGES", solo_codigo(texto), nombre)

    def test_abrir_cualquier_app_sale_del_package_manager_y_no_de_un_shell(self):
        codigo = solo_codigo(self.acciones)
        self.assertIn("queryIntentActivities", codigo)
        self.assertIn("CATEGORY_LAUNCHER", codigo)
        self.assertIn("setClassName", codigo)
        # La lista cerrada sigue siendo lista cerrada: la app que se abre es un
        # componente devuelto por el sistema, no una cadena que se ejecuta.
        for prohibido in ("Runtime.getRuntime", "ProcessBuilder", "exec(", "/system/bin"):
            self.assertNotIn(prohibido, codigo)

    def test_el_nombre_se_compara_normalizado_como_el_habla(self):
        """Un icono dice «Música» y el habla llega como `musica`: si la comparación
        no pasa por `Cerebro.normaliza`, la app existe y CORT no la ve."""
        self.assertIn("Cerebro.normaliza", self.acciones)
        self.assertIn("private static int parecido(", self.acciones)

    def test_poner_abre_un_enlace_buscado_y_no_pulsa_el_play_de_nadie(self):
        """La honestidad de «pon After dark» por escrita: CORT abre una **búsqueda**
        (no hay tabla de deep links por app que se oxide), y para eso necesita que
        el texto vaya codificado en la URL."""
        self.assertIn("Intent.ACTION_VIEW", self.acciones)
        self.assertIn("search_query=", self.acciones)
        self.assertIn("codifica(obra)", self.acciones)
        self.assertIn('URLEncoder.encode(texto.trim(), "UTF-8")', self.acciones,
                      "la variante con `Charset` es de API 29 y el suelo del APK es 26")

    def test_llamar_solo_abre_el_marcador(self):
        """`ACTION_DIAL` enseña el número; `ACTION_CALL` lo marcaría solo y pide
        `CALL_PHONE`, un permiso peligroso que este APK no tiene ni tendrá. El
        permiso se comprueba en el manifiesto, y la intención en el código **sin**
        comentarios: el Javadoc de `llamar()` nombra `CALL_PHONE` para decir que no
        se usa."""
        self.assertIn("Intent.ACTION_DIAL", self.acciones)
        self.assertIn('Uri.fromParts("tel"', self.acciones)
        self.assertNotIn("ACTION_CALL", solo_codigo(self.acciones))
        permisos = {e.get(ANDROIDE + "name") for e in self.raiz
                    if e.tag.endswith("uses-permission")}
        self.assertNotIn("android.permission.CALL_PHONE", permisos)

    def test_la_linterna_usa_la_camara_que_ya_esta_declarada(self):
        """`setTorchMode` pide permiso de cámara: el que ya está en el manifiesto
        (con `required=false`), y si la dueña no lo ha dado aún, `SecurityException`
        se contesta en español en vez de tumbar la cara."""
        self.assertIn("setTorchMode", self.acciones)
        self.assertIn("CameraAccessException", self.acciones)
        self.assertIn("SecurityException", self.acciones)
        permisos = {e.get(ANDROIDE + "name") for e in self.raiz
                    if e.tag.endswith("uses-permission")}
        self.assertIn("android.permission.CAMERA", permisos)

    # -- el traje de asistente -----------------------------------------------------

    def test_los_tres_servicios_existen_como_archivos_java(self):
        declarados = {e.get(ANDROIDE + "name"): e
                      for e in self.raiz.iter() if e.tag.endswith("service")}
        self.assertEqual({".Asistente", ".Sesiones", ".Reconocimiento"},
                         set(declarados),
                         "el asistente son tres servicios: puerta, sesión y oído")
        nombres = {p.name for p in FUENTES.glob("*.java")}
        for nombre in declarados:
            self.assertIn(nombre.lstrip(".") + ".java", nombres,
                          f"{nombre} está en el manifiesto pero no en el fuente")

    def test_cada_servicio_va_protegido_con_su_permiso_de_sistema(self):
        """`VoiceInteractionServiceInfo` (AOSP) **rechaza** la meta-datos si el
        servicio no lleva `BIND_VOICE_INTERACTION`; y el reconocedor se descarta si
        no lleva `BIND_SPEECH_RECOGNIZER`. Sin estas dos líneas, CORT no aparece
        como asistente y no hay ningún aviso en pantalla."""
        declarados = {e.get(ANDROIDE + "name"): e.get(ANDROIDE + "permission")
                      for e in self.raiz.iter() if e.tag.endswith("service")}
        self.assertEqual("android.permission.BIND_VOICE_INTERACTION",
                         declarados[".Asistente"])
        self.assertEqual("android.permission.BIND_VOICE_INTERACTION",
                         declarados[".Sesiones"])
        self.assertEqual("android.permission.BIND_SPEECH_RECOGNIZER",
                         declarados[".Reconocimiento"])
        for nombre, permiso in declarados.items():
            self.assertIsNotNone(permiso, f"{nombre} sin permiso de sistema")

    def test_la_accion_de_intencion_es_la_que_el_sistema_busca(self):
        filtros = {e.get(ANDROIDE + "name") for e in self.raiz.iter()
                   if e.tag.endswith("action")}
        self.assertIn("android.service.voice.VoiceInteractionService", filtros)
        self.assertIn("android.speech.RecognitionService", filtros)

    def test_la_meta_datos_apunta_a_un_xml_que_el_build_enlaza(self):
        meta = [e for e in self.raiz.iter() if e.tag.endswith("meta-data")]
        self.assertEqual(1, len(meta), "la meta-datos del asistente es una sola")
        self.assertEqual("android.voice_interaction", meta[0].get(ANDROIDE + "name"))
        self.assertEqual("@xml/asistente", meta[0].get(ANDROIDE + "resource"))
        self.assertTrue((APK / "res" / "xml" / "asistente.xml").is_file(),
                        "`aapt2 compile --dir res` no puede enlazar un archivo que no existe")

    def test_el_xml_del_asistente_cumple_el_contrato_de_aosp(self):
        """Las tres cosas que hacen que el parser del sistema diga «sí» o «no»:
        el nombre del nodo, los dos servicios obligatorios y **la ausencia de
        prefijo `android:`** en esos atributos (son recursos internos de
        `com.android.internal.R.styleable`, no públicos: con prefijo no los
        reconoce ni `aapt2 link` ni el parser)."""
        nodo = ET.fromstring(self.xml_asistente)
        self.assertEqual("voice-interaction-service", nodo.tag)
        self.assertEqual("dev.sandra.cort.Sesiones", nodo.get("sessionService"))
        self.assertEqual("dev.sandra.cort.Reconocimiento", nodo.get("recognitionService"))
        # Ninguna clave con `}` por delante: en ElementTree un atributo con prefijo
        # `android:` se lee `{http://schemas.android.com/apk/res/android}sessionService`,
        # y esa forma es la que el parser interno **no** ve. Se comprueba sobre el
        # nodo parseado y no sobre el texto: el comentario del propio archivo escribe
        # el error para explicarlo.
        for clave in nodo.attrib:
            self.assertNotIn("}", clave,
                             f"atributo {clave} con nombre de espacio: no lo reconoce nadie")

    def test_el_reconocimiento_no_finge_un_oído_que_no_tiene(self):
        """`Reconocimiento.java` existe porque el contrato lo exige, no porque CORT
        reconozca voz por su cuenta: tiene que ceder el micrófono a la cara y
        cerrar su petición con un código de error del SDK."""
        texto = self.fuentes["Reconocimiento.java"]
        codigo = solo_codigo(texto)
        self.assertIn("listener.error(SpeechRecognizer.ERROR_NO_MATCH)", codigo)
        self.assertIn("protected void onStartListening(", codigo)
        self.assertIn("protected void onCancel(", codigo)
        self.assertIn("protected void onStopListening(", codigo)
        self.assertIn("MainActivity.PIDE_ESCUCHAR", codigo)
        self.assertNotIn("AudioRecord", codigo,
                         "un reconocedor propio exigiría grabar PCM en este proceso")

    def test_la_sesion_abre_la_cara_pidiendo_que_escuche(self):
        codigo = solo_codigo(self.fuentes["Sesion.java"])
        self.assertIn("public void onShow(Bundle args, int showFlags)", codigo)
        self.assertIn("MainActivity.PIDE_ESCUCHAR", codigo)
        self.assertIn("finish();", codigo,
                      "dejar la sesión del sistema abierta espera texto que no va a llegar")

    def test_la_bandera_del_escuchado_es_una_sola_cadena(self):
        """`MainActivity` la declara; `Sesion` y `Reconocimiento` la nombran. Tres
        copias de la literal serían tres oportunidades de escribir «cort-escuchrar»
        y que el asistente abra la cara muda."""
        self.assertIn('public static final String PIDE_ESCUCHAR = "cort-escuchar";',
                      self.fuentes["MainActivity.java"])
        for nombre in ("Sesion.java", "Reconocimiento.java"):
            self.assertIn("MainActivity.PIDE_ESCUCHAR", self.fuentes[nombre], nombre)
            self.assertNotIn('"cort-escuchar"', solo_codigo(self.fuentes[nombre]),
                             f"{nombre}: repite la literal en vez de nombrar la constante")

    def test_la_actividad_se_reutiliza_y_no_se_duplica(self):
        """`singleTop`: la tecla del asistente pulsada dos veces tiene que entregar
        su bandera a la cara que ya está abierta (`onNewIntent`), no montar otra."""
        actividad = next(e for e in self.raiz.iter() if e.tag.endswith("activity"))
        self.assertEqual("singleTop", actividad.get(ANDROIDE + "launchMode"))
        self.assertIn("protected void onNewIntent(Intent intento)",
                      self.fuentes["MainActivity.java"])
        self.assertIn("setIntent(intento)", self.fuentes["MainActivity.java"])

    def test_escuchar_por_el_asistente_reusa_el_micro_que_ya_funciona(self):
        """El oído del asistente es el `SpeechRecognizer` de `v0.15.0`, no un
        modelo nuevo metido a presión en el APK."""
        self.assertIn("public void escucharAhora()", self.fuentes["Cara.java"])
        self.assertIn("escuchar();", self.fuentes["Cara.java"])
        main = solo_codigo(self.fuentes["MainActivity.java"])
        self.assertIn("cara.escucharAhora();", main)


class TestLoQueLlegaAlRunner(unittest.TestCase):
    """El build trabaja sobre el **clone**: lo que git no sigue, el runner no lo ve.

    La trampa mide un día entera. `apps/apk/.gitignore` tenía `res/` para que los
    PNG que dibuja `scripts/marca.py` no se commitearan — bien—, y con esa regla
    también se quedaba fuera `res/xml/asistente.xml`, que es **fuente escrito a
    mano**: el contrato del asistente. El `git add` lo habría saltado en silencio,
    el runner habría clonado sin él, y `aapt2 link` se habría caído con «resource
    @xml/asistente not found»: la Release con su texto y **sin APK**, que es el
    fallo que ya pasó tres veces (`v0.13.0`, `v0.14.0`, `v0.14.2`) por motivos
    distintos. Aquí no hay `javac` ni SDK y el log del run es privado; lo que sí se
    puede comprobar en milisegundos es **qué archivos llegan**.
    """

    def esta_ignorado(self, ruta):
        resultado = subprocess.run(
            ["git", "check-ignore", "--", str(ruta.relative_to(RAIZ))],
            cwd=str(RAIZ), capture_output=True, text=True)
        self.assertIn(resultado.returncode, (0, 1),
                      f"`git check-ignore` no respondió ({resultado.returncode}): "
                      f"{resultado.stderr.strip()}")
        return resultado.returncode == 0

    def test_el_contrato_del_asistente_llega_al_runner(self):
        xml = APK / "res" / "xml" / "asistente.xml"
        self.assertTrue(xml.is_file(), "sin el XML no hay `@xml/asistente` que enlazar")
        self.assertFalse(self.esta_ignorado(xml),
                         "`res/xml/asistente.xml` está ignorado: el runner no lo vería")

    def test_toda_entrada_del_build_es_seguida_por_git(self):
        """Manifiesto, guion de compilado, tabla de frases, los tres diccionarios de
        AOSP y los diecisiete Java (con `Nexo.java` desde `v0.17.0`)."""
        entradas = [MANIFIESTO, COMPILAR, APK / ".gitignore",
                    APK / "assets" / "habilidades.json",
                    APK / "res" / "xml" / "asistente.xml",
                    APK / "simbolos-android.json",
                    APK / "lanza-android.json",
                    APK / "devuelve-android.json"]
        entradas += sorted((APK / "src").rglob("*.java"))
        self.assertGreaterEqual(len(entradas), 25, "el glob no encontró fuentes")
        self.assertIn(APK / "src" / "dev" / "sandra" / "cort" / "Nexo.java", entradas,
                      "`Nexo.java` no está en el árbol: la cara embebida se fue")
        for ruta in entradas:
            self.assertFalse(self.esta_ignorado(ruta),
                             f"{ruta.name}: entrada del build que git ignora")

    def test_los_iconos_generados_siguen_sin_commit(self):
        """La regla que se salvó: lo que dibuja `marca.py` no es fuente."""
        icono = APK / "res" / "mipmap-hdpi" / "ic_launcher.png"
        if not icono.is_file():
            self.skipTest("aquí no hay iconos generados (no se ha compilado)")
        self.assertTrue(self.esta_ignorado(icono),
                        "el PNG generado se está colando en el repo")



class TestLoQueJavacNoDejaPasar(unittest.TestCase):
    """El compilado es la única verificación de tipos que existe aquí, y cuesta un
    Release.

    El run 38810161046 de `compilar-apk` cayó sobre `2ceb46f` con **un solo** error,
    y no era de los que vigilan el diccionario ni de los que cabe imaginar:
    `normaliza(entrada).split(UNION)`. `String.split` recibe un `String` con la
    expresión regular; `Pattern` es el otro dueño de ese método. Salió `v0.15.3` con
    su página de texto y **sin APK**, otra vez, y se enteró una por la annotation
    pública porque en esta máquina no hay `javac`.

    Éstas no sustituyen al compilador: cortan el error de forma que se repite cuando
    se escribe Java de memoria.
    """

    def setUp(self):
        self.java = {java.name: java.read_text(encoding="utf-8")
                     for java in sorted(FUENTES.glob("*.java"))}

    def test_un_Pattern_nunca_es_argumento_de_split(self):
        """`texto.split(MI_PATTERN)` no compila; `MI_PATTERN.split(texto)` sí."""
        for nombre, texto in sorted(self.java.items()):
            codigo = solo_codigo(texto)
            for patron in re.findall(r"Pattern\s+(\w+)\s*=\s*Pattern\.compile", codigo):
                self.assertNotIn(f".split({patron})", codigo,
                                 f"{nombre}: `{patron}` es un Pattern y se le pasó a "
                                 f"`String.split` — javac: «incompatible types»")
                usado = (codigo.count(f"{patron}.split(")
                         + codigo.count(f"{patron}.matcher("))
                self.assertGreater(usado, 0,
                                   f"{nombre}: `{patron}` se declara como Pattern y no "
                                   f"se le llama a ninguno de sus dos métodos")

    def test_el_pattern_de_la_union_parte_la_forma_normalizada(self):
        """La línea que se cayó: sigue partida sobre `normaliza(...)`, no sobre la
        frase cruda, que es lo que hace que «Y» y «y» valgan lo mismo."""
        codigo = solo_codigo(self.java["Cerebro.java"])
        self.assertIn("UNION.split(normaliza(entrada))", codigo)


class TestLoQueJavacObligaARecoger(unittest.TestCase):
    """El **segundo** error que sólo existe al compilar: un `throws` sin recoger.

    El run **38812262724** de `compilar-apk` cayó sobre `97207fa` con un solo error,
    y no era el del `Pattern` —ése ya estaba arreglado y `javac` no lo volvió a nombrar—:

        src/dev/sandra/cort/Reconocimiento.java:40: error: unreported exception
        RemoteException; must be caught or declared to be thrown
                listener.error(SpeechRecognizer.ERROR_NO_MATCH);

    `RecognitionService.Callback.error(int)` **declara** `throws RemoteException` en
    AOSP (es un proxy al proceso del servicio de voz), y Java obliga a `catch`arlo o a
    declararlo. `v0.15.4` salió con su página de texto y **sin APK**: la tercera
    corrección hacia adelante del mes.

    Lo que se puede comprobar aquí no es la semántica de Java: es que el diccionario
    de firmas (`apps/apk/lanza-android.json`, escrito por `scripts/simbolos_android.py`
    desde AOSP) exista, y que en el archivo que habla con esa clase ninguna llamada a
    un método declaradamente peligroso se quede sin su `catch`.
    """

    def setUp(self):
        self.lanza = json.loads((APK / "lanza-android.json").read_text(encoding="utf-8"))
        self.java = {java.name: java.read_text(encoding="utf-8")
                     for java in sorted(FUENTES.glob("*.java"))}

    def test_el_diccionario_de_las_firmas_llega_y_no_esta_vacio(self):
        """Sin este JSON la guarda no mira nada; que exista y nombre al `Callback`
        es lo que la hace válida. Que llegue al clone lo vigila
        `test_toda_entrada_del_build_es_seguida_por_git`."""
        self.assertTrue((APK / "lanza-android.json").is_file(),
                        "falta apps/apk/lanza-android.json: refrescar con "
                        "`python3 scripts/simbolos_android.py`")
        clases = self.lanza["clases"]
        self.assertIn("RecognitionService", clases)
        metodos = clases["RecognitionService"]["metodos"]
        self.assertEqual(["RemoteException"], metodos["error"],
                         "el `error` de `Callback` es el que costó la Release")
        self.assertGreaterEqual(len(metodos), 8,
                                "la lista de firmas bajó: se quedaron métodos sin vigilar")

    def test_toda_llamada_a_un_metodo_que_declara_throws_esta_recogida(self):
        """El archivo que nombra la clase de Android tiene que recoger lo que sus
        métodos declaran lanzar — o declararlo él en la firma."""
        for clase, datos in sorted(self.lanza["clases"].items()):
            for nombre, excepciones in sorted(datos["metodos"].items()):
                for archivo, texto in sorted(self.java.items()):
                    if clase not in solo_codigo(texto):
                        continue
                    codigo = solo_codigo(texto)
                    for coincidencia in re.finditer(rf"\.{re.escape(nombre)}\(", codigo):
                        self.assertTrue(
                            esta_recogido(codigo, coincidencia.start(), excepciones),
                            f"{archivo}: `.{nombre}()` llama a un método de «{clase}» que "
                            f"declara {', '.join(excepciones)} y la llamada no está ni "
                            "dentro de un `try` con su `catch`, ni en un método que lo "
                            "`throws`e — javac: «unreported exception»")

    def test_la_linea_que_se_cayo_sigue_dentro_de_su_try(self):
        """La del run 38812262724, dicha literal: el `error` se avisa y se recoge."""
        codigo = solo_codigo(self.java["Reconocimiento.java"])
        self.assertRegex(
            codigo,
            r"try \{\s*listener\.error\(SpeechRecognizer\.ERROR_NO_MATCH\);\s*\} "
            r"catch \(RemoteException",
            "el `listener.error(...)` volvió a quedarse sin su `catch (RemoteException`")

    def test_el_remoteexception_esta_importado_donde_se_recoge(self):
        """Un `catch` de una clase sin `import` es otro `cannot find symbol`: la guarda
        de arriba no lo vería porque sólo mira el texto del `catch`."""
        for archivo, texto in sorted(self.java.items()):
            codigo = solo_codigo(texto)
            if "catch (RemoteException" in codigo:
                self.assertIn("import android.os.RemoteException;", codigo,
                              f"{archivo}: recoge `RemoteException` sin importarla")


class TestLoQueElSdkDevuelve(unittest.TestCase):
    """La tercera clase de error que **sólo existe cuando alguien compila**, y que
    este corte produjo él solo: `TextToSpeech.getVoices()` devuelve `Set<Voice>` y
    el Java lo estaba recibiendo en un `List<Voice>`. `javac` diría «incompatible
    types», el runner caería y la Release saldría sin APK — la cuarta vez que un
    error de tipos se descubre pagando un Run (después de dos constantes inventadas
    de `AlarmClock`, el `Pattern` a `String.split` y el `RemoteException` sin
    recoger).

    La cura es la misma que con las otras tres: el dato se saca de AOSP con
    `scripts/simbolos_android.py`, vive en `apps/apk/devuelve-android.json`, y aquí
    se compara con lo que el Java declara.
    """

    # Un supertipo también compila; una clase no listada se admite sólo si el tipo
    # es idéntico, que es el caso común (recibir en la misma clase que devuelve).
    SUPERTIPOS = {"Set": {"Collection", "Iterable", "Object"},
                  "List": {"Collection", "Iterable", "Object"},
                  "ArrayList": {"List", "Collection", "Iterable", "Object"},
                  "boolean": {"Boolean", "Object"},
                  "int": {"Integer", "long", "Long", "float", "Float", "double", "Object"}}

    def setUp(self):
        self.devuelve = json.loads((APK / "devuelve-android.json").read_text(encoding="utf-8"))
        self.java = {java.name: java.read_text(encoding="utf-8")
                     for java in sorted(FUENTES.glob("*.java"))}

    def test_el_diccionario_de_los_retornos_llega_y_no_esta_vacio(self):
        """Sin este JSON la guarda no mira nada. Que llegue al clone lo vigila
        `test_toda_entrada_del_build_es_seguida_por_git`."""
        self.assertTrue((APK / "devuelve-android.json").is_file(),
                        "falta apps/apk/devuelve-android.json: refrescar con "
                        "`python3 scripts/simbolos_android.py`")
        metodos = self.devuelve["clases"]["TextToSpeech"]["metodos"]
        self.assertEqual(["Set<Voice>"], metodos["getVoices"],
                         "el retorno de `getVoices` cambió en AOSP o se borró el dato")
        self.assertIn("isSpeaking", metodos)
        self.assertGreaterEqual(sum(len(v["metodos"]) for v in self.devuelve["clases"].values()),
                                6, "la lista de retornos bajó: hay métodos sin vigilar")

    def _permite(self, declarado: str, tipos: list[str]) -> bool:
        base = declarado.split("<")[0].strip()
        for tipo in tipos:
            if tipo == declarado:
                return True
            if base == tipo.split("<")[0].strip():
                return True
            if base in self.SUPERTIPOS and tipo.split("<")[0].strip() in self.SUPERTIPOS[base]:
                return True
        return False

    @staticmethod
    def _es_la_llamada_de_afuera(fragmento: str) -> bool:
        """El segmento va del principio de la sentencia hasta el punto que nombra
        al método del SDK. Si abre más paréntesis de los que cierra, esa llamada
        está **dentro** de otra, y quien decide el tipo de la variable es la de
        fuera —un método nuestro, que no está en ningún diccionario—.

        Falso positivo medido en este corte: `Nexo.java` escribe
        `String ruta = rutaDe(peticion.getUrl().toString())` y la guarda exigía
        que un `String` recibiera el `Uri` de `getUrl`. El `String` es correcto y
        `javac` lo acepta; la que se equivocaba era la regex.
        """
        return fragmento.count("(") == fragmento.count(")")

    def test_toda_variable_que_recibe_un_metodo_del_sdk_usa_su_tipo_real(self):
        """`Tipo x = objeto.metodo(...)` tiene que declarar el tipo que AOSP dice."""
        for clase, datos in sorted(self.devuelve["clases"].items()):
            for nombre, tipos in sorted(datos["metodos"].items()):
                for archivo, texto in sorted(self.java.items()):
                    if clase not in solo_codigo(texto):
                        continue
                    codigo = solo_codigo(texto)
                    for coincidencia in re.finditer(rf"\.{re.escape(nombre)}\(", codigo):
                        inicio = max((codigo.rfind(c, 0, coincidencia.start())
                                      for c in ";{}"), default=-1)
                        fragmento = codigo[inicio + 1:coincidencia.start()].strip()
                        if not self._es_la_llamada_de_afuera(fragmento):
                            continue
                        asignacion = re.fullmatch(
                            r"(?:final\s+)?([\w.<>\[\], ]+?)\s+\w+\s*=\s*[^=]+", fragmento)
                        if not asignacion:
                            continue
                        self.assertTrue(
                            self._permite(asignacion.group(1).strip(), tipos),
                            f"{archivo}: `{fragmento}.{nombre}()` guarda el resultado en "
                            f"`{asignacion.group(1).strip()}`, y AOSP devuelve "
                            f"{', '.join(tipos)} — javac: «incompatible types»")

    def test_la_linea_de_las_voces_sigue_recibiendo_un_Set(self):
        """La que estaba mal escrita en este corte, dicha literal."""
        self.assertRegex(re.sub(r"\s+", " ", solo_codigo(self.java["Voz.java"])),
                         r"Set<Voice> \w+ = \w+\.getVoices\(\);",
                         "el `getVoices()` volvió a recibirse en un tipo que no es `Set`")

    def test_una_llamada_anidada_no_le_presta_su_tipo_a_la_variable(self):
        """La que falló contra `Nexo.java` al escribir la cara embebida."""
        self.assertFalse(self._es_la_llamada_de_afuera("String ruta = rutaDe(peticion.getUrl"))
        self.assertTrue(self._es_la_llamada_de_afuera("Set<Voice> voces = boca"))
        # La cadena de verdad: `getUrl()` ya cerrado antes del método que decide.
        self.assertTrue(self._es_la_llamada_de_afuera("String nombre = peticion.getUrl()"))

    def test_la_guarda_de_retornos_sigue_sin_estar_decorada(self):
        """Reintegrando el `List<Voice>` de `v0.16.0`, la guarda tiene que caer."""
        roto = self.java["Voz.java"].replace("Set<Voice>", "List<Voice>", 1)
        self.assertNotEqual(roto, self.java["Voz.java"], "el `Set<Voice>` ya no está en Voz.java")
        tipos = self.devuelve["clases"]["TextToSpeech"]["metodos"]["getVoices"]
        with self.assertRaises(AssertionError):
            for coincidencia in re.finditer(r"\.getVoices\(", solo_codigo(roto)):
                inicio = max((solo_codigo(roto).rfind(c, 0, coincidencia.start())
                              for c in ";{}"), default=-1)
                fragmento = solo_codigo(roto)[inicio + 1:coincidencia.start()].strip()
                if not self._es_la_llamada_de_afuera(fragmento):
                    continue
                asignacion = re.fullmatch(
                    r"(?:final\s+)?([\w.<>\[\], ]+?)\s+\w+\s*=\s*[^=]+", fragmento)
                if not asignacion:
                    continue
                self.assertTrue(self._permite(asignacion.group(1).strip(), tipos))


class TestLaConversionQueJavacNoPerdona(unittest.TestCase):
    """Cuarta clase de error que **sólo existe al compilar**, y la que costó la página
    de `v0.16.0` (sin APK): `Orbe.java:230` tenía

        Math.max(1f, escala * 0.012f * (0.6 + semilla[i]))

    y en Java `0.6` es `double`, así que todo el producto se vuelve `double` y
    `drawCircle(…, float, …)` lo rechaza con «possible lossy conversion from double to
    float». Es un literal de un carácter, invisible leyendo, y el compilador del proyecto
    vuelve a ser el único que lo ve.

    La guarda no intenta reimplementar el sistema de tipos: mira dos sitios donde este
    error siempre aparece —las llamadas de dibujo que toman `float` y las asignaciones
    a `float`— y exige que un decimal sin `f` vaya dentro de un `(float)` o `(int)`
    explícito. No cubre un `float` que llega por una cadena de métodos; lo que cubre es
    la forma en que este error se escribió la única vez que ocurrió.
    """

    Llamadas_de_dibujo = re.compile(
        r"\.(drawCircle|drawArc|drawPath|drawLine|drawRoundRect|setStrokeWidth|setAlpha)\s*\(")
    Decimal_sin_sufijo = re.compile(r"(?<![\w.])\d+\.\d+(?![\w.])")
    Conversion_explicita = re.compile(r"\((?:float|int|long|short)\)")

    def setUp(self):
        self.java = {java.name: java.read_text(encoding="utf-8")
                     for java in sorted(FUENTES.glob("*.java"))}

    def sentencias_de_float(self, codigo):
        """Las sentencias que asignan a un `float` o llaman a un método de `Canvas`/`Paint`."""
        for sentencia in solo_codigo(codigo).split(";"):
            limpio = sentencia.strip()
            if not limpio:
                continue
            es_asignacion = re.match(r"(?:final\s+)?float\s+\w+\s*[-+*/]?=", limpio)
            if es_asignacion or self.Llamadas_de_dibujo.search(limpio):
                yield limpio

    def test_todo_decimal_en_un_sitio_de_float_lleva_su_f_o_su_cast(self):
        for archivo, texto in sorted(self.java.items()):
            for sentencia in self.sentencias_de_float(texto):
                sueltos = [d for d in self.Decimal_sin_sufijo.findall(sentencia)
                           if not re.search(rf"{re.escape(d)}f\b", sentencia)]
                if sueltos and not self.Conversion_explicita.search(sentencia):
                    self.fail(f"{archivo}: {', '.join(sueltos)} sin `f` ni cast en un sitio de "
                              f"`float`: `{sentencia[:90]}` — javac: «possible lossy conversion "
                              "from double to float» (así se cayó el run de `v0.16.0`)")

    def test_la_linea_del_polvo_sigue_con_sus_floats(self):
        """La que se cayó en el runner, dicha literal."""
        orbe = re.sub(r"\s+", " ", solo_codigo(self.java["Orbe.java"]))
        self.assertRegex(orbe, r"escala \* 0\.012f \* \(0\.6f \+ semilla\[i\]\)",
                         "el radio del polvo volvió a mezclar `double` con `float`")

    def test_la_guarda_no_es_decorativa(self):
        """Con el `0.6` de vuelta, la guarda tiene que caer: si no, no está mirando."""
        con_el_bug = self.java["Orbe.java"].replace("(0.6f + semilla[i])", "(0.6 + semilla[i])")
        self.assertNotEqual(con_el_bug, self.java["Orbe.java"],
                            "la frase buscada cambió y esta prueba ya no prueba nada")
        encontradas = [s for s in self.sentencias_de_float(con_el_bug)
                       if self.Decimal_sin_sufijo.search(s)
                       and not self.Conversion_explicita.search(s)]
        self.assertEqual(1, len(encontradas),
                         f"la guarda no cazó el bug reintegrado ({len(encontradas)} sentencias)")


if __name__ == "__main__":
    unittest.main()
