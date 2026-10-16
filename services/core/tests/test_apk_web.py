"""Guardias de `v0.17.0`: la cara del portátil **dentro** del APK.

El corte cambia de arquitectura, y con ella llega una clase nueva de fallo que no
existía: las dos caras dejan de ser dos programas que se parecen y pasan a ser
**un solo paquete servido por dos transportes**. `Nexo.java` (el `WebView` con el
puente) y `apps/web/src/cort/connection.ts` (el manejador de cuadros) tienen que
quedar de acuerdo en cuatro cosas que ningún compilador comprueba porque están
escritas en dos lenguajes distintos:

* los **tipos de cuadro** que Java empuja son los que `maneja` sabe leer;
* los **métodos del puente** que la página llama existen como `@JavascriptInterface`;
* la **lista cerrada de rutas** sirve todo lo que la página pide y nada más;
* el **`dist` que compila el runner** es el que se copia dentro del APK.

Nada de esto toca el teléfono: lee archivos fuente. Es exactamente lo que
`test_apk_orbe.py` hace desde `v0.16.0` con los números del orbe, y la razón de
ser es la misma de siempre (regla 11 del repo): aquí no hay `javac` ni WebView ni
Android, así que lo único que se puede verificar en esta máquina es la forma, y
la forma es donde nacen los cinco errores que ya costaron Runs.
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
APK = RAIZ / "apps" / "apk"
WEB = RAIZ / "apps" / "web"
FUENTES = APK / "src" / "dev" / "sandra" / "cort"
NEXO = FUENTES / "Nexo.java"
ACTIVITY = FUENTES / "MainActivity.java"
CONECTION = WEB / "src" / "cort" / "connection.ts"
VOZ_TS = WEB / "src" / "cort" / "voz.ts"
INDICE_HTML = WEB / "index.html"
VITE = WEB / "vite.config.ts"
GITIGNORE = RAIZ / ".gitignore"
WORKFLOW = RAIZ / ".github" / "workflows" / "compilar-apk.yml"


def texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


def sin_comentarios(codigo: str) -> str:
    """El Java sin su documentación, para contar llamadas.

    Es el mismo motivo que llevó a `solo_codigo` en `test_apk_manifesta.py`: la
    javadoc de `Nexo.numeroDe` **cita** el bug que previene —`String.format("%.2f",
    0.4)` sin `Locale`—, y una guarda que lee prosa como código acusaría al
    comentario. Aquí se tiran sólo los bloques `/* */` y las líneas `//`; las
    cadenas se quedan, porque los tipos de cuadro se buscan dentro de ellas.
    """
    salida, i, n = [], 0, len(codigo)
    while i < n:
        c = codigo[i]
        if c in '"\'':                       # literal: se conserva entero
            j = i + 1
            while j < n:
                if codigo[j] == "\\":
                    j += 2
                    continue
                if codigo[j] == c:
                    break
                j += 1
            salida.append(codigo[i:min(j + 1, n)])
            i = j + 1
        elif c == "/" and i + 1 < n and codigo[i + 1] == "/":
            k = codigo.find("\n", i)
            i = n if k < 0 else k
        elif c == "/" and i + 1 < n and codigo[i + 1] == "*":
            k = codigo.find("*/", i + 2)
            i = n if k < 0 else k + 2
        else:
            salida.append(c)
            i += 1
    return "".join(salida)


# Los cuadros que Java mete en `window.cortRecibe` aparecen en el fuente como
# cadenas con comillas escapadas: `{\"type\":\"state\",...}`.
CUADRO_JAVA = re.compile(r'\\"type\\":\\"([a-z_]+)\\"')
# Lo que el manejador del cliente distingue.
CUADRO_TS = re.compile(r"m\.type === '([a-z_]+)'")
METODO_PUENTE = re.compile(r"@JavascriptInterface\s+public void (\w+)\(")
LLAMADA_PUENTE = re.compile(r"\bn\.(enviar|escuchar|callar|hablar|pedirAvatares)\(")


class TestLosMismosCuadros(unittest.TestCase):
    """Un manejador, dos transportes: si Java inventa un cuadro la página lo
    ignora en silencio, y eso es un CORT que no contesta sin ningún error."""

    def huerfanas(self, java: str) -> list[str]:
        """Los tipos que Java empuja y `maneja` no conoce, sobre el texto que sea."""
        return sorted(set(CUADRO_JAVA.findall(java)) - set(CUADRO_TS.findall(texto(CONECTION))))

    def setUp(self):
        self.java = texto(NEXO)
        self.ts = texto(CONECTION)

    def test_el_cliente_maneja_todo_lo_que_java_empuja(self):
        self.assertTrue(CUADRO_JAVA.findall(self.java), "Nexo.java no empuja ningún cuadro")
        self.assertEqual([], self.huerfanas(self.java),
                         "Nexo.java emite un cuadro que `maneja` no conoce: llega a la "
                         "página y se tira, que es un CORT mudo sin ningún error")

    def test_la_guarda_de_cuadros_no_es_decorativa(self):
        """Empujando un tipo inventado, la paridad tiene que verlo. (Se escribe con
        `\\u` escapado y un nombre de la gramática del protocolo: si el nombre no
        casa con `[a-z_]+`, `CUADRO_JAVA` no lo recoge y la prueba mentiría verde.)"""
        inventado = self.java.replace('"{\\"type\\":\\"intent\\"', '"{\\"type\\":\\"chisme\\"')
        self.assertNotEqual(inventado, self.java, "el cuadro `intent` ya no está como se espera")
        self.assertEqual(["chisme"], self.huerfanas(inventado),
                         "la guarda dejó de comparar los dos vocabularios")

    def test_el_diccionario_de_cuadros_del_puente(self):
        """Dicho literal, para que un tipo nuevo se añada a la lista y no se olvide."""
        self.assertEqual({"state", "status", "intent", "assistant_message",
                          "user_message", "avatars"},
                         set(CUADRO_JAVA.findall(self.java)))

    def test_user_message_viaje_en_los_dos_sentidos(self):
        """Lo que el micrófono de Android oye entra a la cara como si la usuaria lo
        hubiera tecleado: el cuadro no existía antes del puente."""
        self.assertIn('"type":"user_message"', self.java.replace('\\"', '"'))
        self.assertRegex(self.ts, r"m\.type === 'user_message'")

    def test_la_palabra_del_puente_es_la_ventanilla_del_cliente(self):
        """Java llama a `window.cortRecibe`; si el cliente la renombró, el puente
        queda apuntando a `undefined` y no pasa nada visible."""
        self.assertIn("window.cortRecibe", self.java)
        self.assertRegex(self.ts, r"window\.cortRecibe\s*=")

    def test_el_nivel_del_micfono_llega_al_reactor(self):
        """El añadido de este corte: `state` trae `nivel` y `applyState` lo sube."""
        self.assertRegex(self.java, r'\\"nivel\\":')
        self.assertRegex(self.ts, r"if \(Number\.isFinite\(m\.nivel\)\) target\.nivel")


class TestElPuenteTieneLasDosCaras(unittest.TestCase):
    """Los métodos que la página puede llamar son los que Java declaró."""

    def setUp(self):
        self.java = texto(NEXO)
        self.ts = texto(CONECTION) + "\n" + texto(VOZ_TS)

    def test_la_lista_de_metodos_del_puente(self):
        declarados = set(METODO_PUENTE.findall(self.java))
        self.assertEqual({"enviar", "escuchar", "callar", "hablar", "pedirAvatares"},
                         declarados,
                         "un método del puente se añadió o se fue sin escribirlo aquí")

    def test_todo_lo_que_la_pagina_llama_esta_declarado(self):
        que_llama = set(LLAMADA_PUENTE.findall(self.ts))
        huerfanos = sorted(que_llama - set(METODO_PUENTE.findall(self.java)))
        self.assertEqual([], huerfanos,
                         f"la página llama a {huerfanos} y Java no lo expone: "
                         "`window.Nexo.enviar` sería `undefined`")
        self.assertTrue(que_llama, "la página no llama a ningún método del puente")

    def test_el_objeto_se_mete_con_el_nombre_que_la_pagina_busca(self):
        self.assertRegex(self.java, r'addJavascriptInterface\(this,\s*"Nexo"\)')
        self.assertRegex(self.ts, r"window\.Nexo")

    def test_tipos_del_puente_y_su_lista(self):
        """`type Nexo` en TS es el contrato escrito del otro lado del cristal."""
        bloque = re.search(r"export type Nexo = \{(.*?)\}", self.ts, re.S)
        self.assertIsNotNone(bloque, "no hay tipo `Nexo` en connection.ts")
        declarados = set(re.findall(r"(\w+)\(", bloque.group(1)))
        self.assertEqual(set(METODO_PUENTE.findall(self.java)), declarados)

    def test_sin_el_no_hay_puente_y_sigue_el_cable(self):
        """La cara de PC no puede romperse: si `window.Nexo` no está, todo el camino
        nuevo se salta y queda el WebSocket de siempre."""
        self.assertRegex(self.ts, r"typeof window !== 'undefined' && window\.Nexo")
        self.assertRegex(self.ts, r"const s = new WebSocket\(WS_URL\)")


class TestLaListaCerradaDeArchivos(unittest.TestCase):
    """`rutaDe` es la única puerta de los archivos del APK a la red del WebView.
    Regla 6 del repo, aplicada a un nombre de archivo."""

    def setUp(self):
        self.java = texto(NEXO)

    def _lista(self, nombre: str) -> list[str]:
        bloque = re.search(rf"{nombre} = \{{(.*?)\}}", self.java, re.S)
        self.assertIsNotNone(bloque, f"no se encuentra `{nombre}` en Nexo.java")
        return re.findall(r'"([^"]+)"', bloque.group(1))

    def test_todo_lo_que_pide_la_pagina_esta_en_la_lista(self):
        """Las rutas absolutas que `index.html` referencia tienen que resolver."""
        raices = self._lista("RAICES")
        prefijos = self._lista("PREFIJOS")
        pedidas = set(re.findall(r'(?:href|src)="(/[^"]+)"', texto(INDICE_HTML)))
        self.assertTrue(pedidas, "index.html no referencia ninguna ruta")
        for ruta in sorted(pedidas):
            camino = ruta.lstrip("/")
            if camino.endswith(".tsx"):
                continue  # `/src/main.tsx` lo resuelve Vite, no el asset
            permitido = camino in raices or any(camino.startswith(p) for p in prefijos)
            self.assertTrue(permitido,
                            f"la página pide `{ruta}` y `rutaDe` la rechazaría con 404")

    def test_la_raiz_y_el_dossier_suenan_igual_que_el_build(self):
        self.assertEqual("index.html", self._lista("RAICES")[0])
        dossier = re.search(r'static final String DOSSIER = "(\w+)"', self.java).group(1)
        self.assertEqual("web", dossier)
        self.assertIn('CARPETA = DOSSIER + "/"', self.java)
        self.assertIn('ORIGEN = "https://cort.local"', self.java)

    def test_el_escape_de_ruta_se_corta_antes_del_permiso(self):
        """El orden importa: `assets/../habilidades.json` empieza por un prefijo
        permitido. La comprobación de `..` tiene que estar **antes** del bucle."""
        codigo = self.java
        negado = codigo.index('camino.contains("..")')
        permitido = codigo.index("boolean permitido = false;")
        self.assertLess(negado, permitido,
                        "`rutaDe` admite el prefijo antes de mirar el `..`")
        self.assertIn('camino.startsWith("/")', codigo)

    def test_el_tipo_se_sabe_por_extension_y_no_por_el_sistema(self):
        """`MimeTypeMap.getSingletonInstance()` no existe; lo que existe es
        `getSingleton()`. La lista propia evita la trampa y evita preguntar."""
        self.assertNotIn("MimeTypeMap", self.java)
        for ext in ("html", "js", "css", "json", "webmanifest", "svg", "png", "ico"):
            self.assertRegex(self.java, rf'case "{ext}":', f"sin tipo para .{ext}")

    def test_el_404_es_uno_de_verdad_y_no_una_pagina_de_red(self):
        """Si un asset falta, el WebView no debe salir a la red tras un host que no
        existe: se le contesta 404 en la propia interceptación."""
        self.assertRegex(self.java, r"new WebResourceResponse\(\"text/plain\", \"utf-8\", "
                                    r"404, \"Not Found\"")
        self.assertRegex(self.java, r"return ruta == null \? noExiste\(\) : sirve\(ruta\)")

    def test_no_se_abre_el_disco(self):
        """`setAllowFileAccess` se queda en su defecto: la cara lee `getAssets()`
        por mano propia y con lista cerrada, que es más estrecho."""
        self.assertNotIn("setAllowFileAccess(true)", self.java)
        self.assertRegex(self.java, r"s\.setJavaScriptEnabled\(true\)")
        self.assertRegex(self.java, r"s\.setDomStorageEnabled\(true\)")


class TestLaComaQueRompeElJson(unittest.TestCase):
    """En un teléfono con idioma español, `String.format("%.2f", 0.4)` devuelve
    `0,4`. Ese número viaja dentro de un cuadro JSON y `JSON.parse` del otro lado
    tira el cuadro entero: el orbe no anima y la frase no se contesta.

    Es la misma clase de bug que solo se ve en el aparato —aquí `locale-gen` manda
    y no hay un Android con `es_CO`—, así que la guarda es textual: ningún
    `String.format` sin `Locale` explícita en el Java del APK.
    """

    def sin_locale(self, codigo: str) -> list[str]:
        """Las llamadas a `String.format` cuyo argumento de idioma no aparece.

        Se busca sobre el texto limpio y se corta sobre el mismo, para que los
        desplazamientos no se descolocaen con los comentarios retirados.
        """
        limpio = sin_comentarios(codigo)
        pecado = []
        for coincidencia in re.finditer(r"String\.format\(", limpio):
            trozo = limpio[coincidencia.end():coincidencia.end() + 120].split(";")[0]
            if "Locale" not in trozo:
                pecado.append(f"`format({trozo[:48].strip()}`")
        return pecado

    def test_todo_format_nombra_su_locale(self):
        pecado = []
        for java in sorted(FUENTES.glob("*.java")):
            pecado += [f"{java.name}: {p}" for p in self.sin_locale(texto(java))]
        self.assertEqual([], pecado,
                         f"`String.format` sin `Locale` en {pecado}: en es_CO da coma")

    def test_la_guarda_no_es_decorativa(self):
        """Quitándole el `Locale.ROOT` a la línea que forma el nivel, la guarda tiene
        que verlo. Sin esto, un escáner que no mira nada daría verde igual."""
        roto = texto(NEXO).replace('String.format(Locale.ROOT, "%.2f", valor)',
                                   'String.format("%.2f", valor)')
        self.assertNotEqual(roto, texto(NEXO), "`numeroDe` ya no forma como se espera")
        self.assertTrue(self.sin_locale(roto), "la guarda no cazó la coma inventada")

    def test_el_numero_del_nivel_sale_con_punto(self):
        self.assertRegex(texto(NEXO),
                         r'String\.format\(Locale\.ROOT,\s*"%.2f",\s*valor\)')

    def test_la_escapada_de_json_cierra_comillas_y_control(self):
        """Un recuerdo con `"` o un salto de línea rompe el cuadro igual que la coma."""
        bloque = re.search(r"public static String escapa\(String texto\) \{(.*?)\n    \}",
                           texto(NEXO), re.S)
        self.assertIsNotNone(bloque, "no se encuentra `escapa`")
        cuerpo = bloque.group(1)
        for literal in (r"'\"'", r"'\\\\'", r'"\\\\n"', r'"\\\\u%04x"'):
            self.assertRegex(cuerpo, literal, f"`escapa` ya no cubre {literal}")


class TestElDistViajaAlRunner(unittest.TestCase):
    """El `dist` no se commitea (regla 7: nada generado en el repo) y el APK no es
    nada sin él. Lo compila el runner, y si el paso se borra el APK sale **verde con
    la cara vieja** porque la cara nativa sigue ahí de respaldo. Esta es la guarda
    que evita celebrar un Release sin la cara dentro."""

    def setUp(self):
        self.yml = texto(WORKFLOW)

    def test_el_build_instala_node_y_compila_la_cara(self):
        self.assertIn("actions/setup-node@v4", self.yml)
        self.assertIn("npm ci", self.yml)
        self.assertIn("npm run build", self.yml)
        self.assertIn("apps/web/package-lock.json", self.yml,
                      "la caché de npm no está atada al lockfile: build no reproducible")

    def test_se_exigen_las_rutas_relativas_antes_de_copiar(self):
        """`base: './'` sin comprobación es una línea de configuración. El paso falla
        si Vite emitiera `/assets/`: dentro del APK eso apuntaría fuera del origen."""
        self.assertRegex(self.yml, r"src=\"\./assets/")
        self.assertIn("::error::", self.yml)
        self.assertRegex(texto(VITE), r"base:\s*'\./'")

    def desajuste(self, yml: str) -> str:
        """Qué escribe el pipeline y qué lee Java, dicho de una vez."""
        copia = re.search(r"cp\s+-r\s+\S+\s+(\S*apk/assets/(\w+)/?)", yml)
        if copia is None:
            return "no se ve la copia del `dist` a los assets del APK"
        dossier = re.search(r'static final String DOSSIER = "(\w+)"', texto(NEXO)).group(1)
        return "" if copia.group(2) == dossier else f"pipeline `{copia.group(2)}` ≠ Java `{dossier}`"

    def test_el_destino_de_la_copia_es_el_dossier_que_lee_java(self):
        self.assertEqual("", self.desajuste(self.yml),
                         "el pipeline escribe una carpeta y Java lee otra: el APK sale "
                         "verde y sin cara dentro")

    def test_la_guarda_del_dossier_no_es_decorativa(self):
        """Renombrando la carpeta del pipeline, el desajuste tiene que verse."""
        y = self.desajuste(self.yml.replace("assets/web/", "assets/cara/"))
        self.assertNotEqual("", y, "renombrar el destino del `dist` no rompe nada")
        self.assertIn("cara", y)

    def test_la_cara_embebida_esta_ignorada_y_respalda_la_nativa(self):
        self.assertIn("apps/apk/assets/web/", texto(GITIGNORE))
        yml = self.yml
        self.assertIn("rm -rf", yml, "sin limpiar, un dist viejo se queda dentro del APK")
        actividad = texto(ACTIVITY)
        self.assertIn("hayCaraEmbebida", actividad)
        self.assertIn("volverACara", actividad,
                      "si el WebView se cae no hay respaldo nativo: pantalla negra")
        self.assertRegex(actividad, r"new Nexo\(this,")


class TestElVocabularioDelPuenteNoEsElDelCable(unittest.TestCase):
    """Lo que el puente **no** promete, escrito para que nadie lo simule."""

    def test_sin_avatares_y_dicho(self):
        """No hay `.vrm` en el APK (regla 7), así que `pedirAvatares` contesta vacío
        en vez de dejar la cara esperando un cuadro que no llega."""
        self.assertRegex(texto(NEXO), r'\\"type\\":\\"avatars\\",\\"items\\":\[\]')

    def test_la_vigilia_sigue_siendo_del_portatil(self):
        """La frase de activación continua no viaja por el puente: el reconocedor de
        Android cierra tras una frase, y `arrancarReconocimiento` lo **rechaza** en
        su rama del puente en vez de fingir un modo vigilia a medias. Está escrito
        en `apps/apk/README.md`."""
        ts = texto(VOZ_TS)
        arrancar = re.search(r"function arrancarReconocimiento\(\) \{.*?\n\}", ts, re.S)
        self.assertIsNotNone(arrancar, "no se encuentra `arrancarReconocimiento`")
        rama = re.search(r"const n = nexo\(\)\n  if \(n\) \{.*?\n  \}", arrancar.group(0), re.S)
        self.assertIsNotNone(rama, "la rama del puente se fue de `arrancarReconocimiento`")
        self.assertRegex(rama.group(0), r"if \(!escuchaOn\) return",
                         "la vigilia volvió a aceptarse por el puente sin implementarla")
        self.assertNotIn("continuous", rama.group(0),
                         "se simuló captura continua sobre un reconocedor que no la hace")


if __name__ == "__main__":
    unittest.main()
