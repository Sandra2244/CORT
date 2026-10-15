"""Paridad de la cara: los números del orbe y de la voz son **los mismos** en el PC y en el teléfono.

La dueña lo pidió literalmente: «necesito que se active en modo orbe … como es el
proyecto CORT acá en PC», «la voz no sé si sea la misma, parece otra», y —lo que
más pesa para el futuro— «lo mismo funcione: actualizaciones cuando publiques lo
debe tener tanto el que funciona en PC como el APK que funciona en Android».

La respuesta no puede ser «ya me fijé y se parecen». Este archivo **lee el fuente
de la cara de PC** (`apps/web/src/cort/palette.ts`, `cort/voz.ts`, `scene/Core.tsx`,
`scene/Particles.tsx`, `scene/Scene.tsx`) y exige que los literales del teléfono
(`apps/apk/src/dev/sandra/cort/Orbe.java`, `Paleta.java`, `Voz.java`) digan el mismo
número. Si alguien afina la respiración del reactor en TypeScript y no la toca en
Java, o cambia el acento de la voz en un aparato y no en el otro, **esta suite se
cae**: la paridad deja de ser una promesa y pasa a ser una prueba.

Qué no cubre, dicho en claro:

* El orbe del teléfono es `Canvas` 2D y el del PC es WebGL con tres.js; se copian
  las **constantes de movimiento y de color**, no los shaders. La cantidad de polvo
  sí está recortada (4 000 en GPU, `POLVO` en `Canvas`) y por eso una prueba exige
  que el recorte esté escrito en el propio archivo.
* Que se *vea* bien en el teléfono es de dedo (`#29`), no de regex. Aquí se prueba
  que el dibujo y los estados están cableados y que sus números coinciden.
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
APK = RAIZ / "apps" / "apk"
JAVA = APK / "src" / "dev" / "sandra" / "cort"
WEB = RAIZ / "apps" / "web" / "src"

PALETA_TS = WEB / "cort" / "palette.ts"
VOZ_TS = WEB / "cort" / "voz.ts"
CORE_TSX = WEB / "scene" / "Core.tsx"
PARTICULAS_TSX = WEB / "scene" / "Particles.tsx"
ESCENA_TSX = WEB / "scene" / "Scene.tsx"

ORBE = JAVA / "Orbe.java"
PALETA_JAVA = JAVA / "Paleta.java"
VOZ_JAVA = JAVA / "Voz.java"
CARA_JAVA = JAVA / "Cara.java"
ANILLO = JAVA / "Anillo.java"
PRINCIPAL = JAVA / "MainActivity.java"


def fuente(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


def numero_ts(texto: str, patron: str) -> float:
    """El primer número que captura `patron` en el TypeScript."""
    coincidencia = re.search(patron, texto)
    assert coincidencia, f"el TypeScript ya no dice `{patron}`: hay que actualizar la paridad"
    return float(coincidencia.group(1))


def numero_java(ruta: Path, nombre: str) -> float:
    """El literal `static final float NOMBRE = 0.55f;` del teléfono."""
    coincidencia = re.search(rf"\b{nombre}\s*=\s*([0-9.]+)f\b", fuente(ruta))
    assert coincidencia, f"{ruta.name}: falta la constante `{nombre}`"
    return float(coincidencia.group(1))


def entero_java(texto: str, nombre: str) -> int:
    """Un `static final int` — ni los puntos del baremo de voces ni la cantidad de
    polvo son decimales."""
    coincidencia = re.search(rf"\b{nombre}\s*=\s*([0-9]+)\b", texto)
    assert coincidencia, f"falta la constante entera `{nombre}`"
    return int(coincidencia.group(1))


def hex_ts(texto: str, patron: str) -> str:
    coincidencia = re.search(patron, texto, re.I)
    assert coincidencia, f"el TypeScript ya no tiene un `#rrggbb` en `{patron}`"
    return coincidencia.group(1).upper()


def hex_java(nombre: str) -> str:
    coincidencia = re.search(rf"\b{nombre}\s*=\s*0xFF([0-9A-Fa-f]{{6}})\b", fuente(PALETA_JAVA))
    assert coincidencia, f"Paleta.java: falta el color `{nombre}`"
    return coincidencia.group(1).upper()


class TestLosMismosColores(unittest.TestCase):
    """Dos aparatos, un solo acento. Un hex que diverge es la cara partida."""

    def test_el_magenta_de_pensar_es_el_de_la_cara_de_pc(self):
        """`THINKING_HOT` (`palette.ts`) = `Paleta.PENSAMIENTO`."""
        esperado = hex_ts(fuente(PALETA_TS), r"THINKING_HOT\s*=\s*'#([0-9a-fA-F]{6})'")
        self.assertEqual(esperado, hex_java("PENSAMIENTO"),
                         "el orbe del teléfono piensa en otro color que el del PC")

    def test_el_polvo_del_cascaron_es_el_de_la_cara_de_pc(self):
        """`uColor` (`Particles.tsx`) = `Paleta.POLVO`."""
        esperado = hex_ts(fuente(PARTICULAS_TSX),
                          r"uColor:\s*\{ value: new THREE\.Color\('#([0-9a-fA-F]{6})'\)")
        self.assertEqual(esperado, hex_java("POLVO"),
                         "el polvo del teléfono es de otro color que el del PC")

    def test_los_dos_colores_nuevos_se_usan_en_el_orbe(self):
        """Que estén en `Paleta.java` no alcanza: si `Orbe.java` no los mira, la
        paridad es decorativa."""
        codigo = fuente(ORBE)
        for nombre in ("PENSAMIENTO", "POLVO"):
            self.assertIn(f"Paleta.{nombre}", codigo,
                          f"Orbe.java declara el color pero no lo dibuja: `{nombre}`")


class TestLosMismosNumerosDeMovimiento(unittest.TestCase):
    """El reactor se mueve con los literales de `Scene.tsx`, `Core.tsx` y
    `Particles.tsx`. Cada prueba nombra la línea de la que sale."""

    def test_la_caida_del_nivel(self):
        """`target.nivel *= Math.exp(-dt * 4.5)`."""
        esperado = numero_ts(fuente(ESCENA_TSX), r"nivel \*= Math\.exp\(-dt \* ([0-9.]+)\)")
        self.assertEqual(esperado, numero_java(ORBE, "CAIDA"))

    def test_la_respiracion_en_reposo_y_su_extra_al_pensar(self):
        """`const idle = 0.05 + (target.spin > 1 ? 0.22 : 0)`."""
        texto = fuente(ESCENA_TSX)
        self.assertEqual(numero_ts(texto, r"const idle = ([0-9.]+) \+"),
                         numero_java(ORBE, "RESPIRACION"))
        self.assertEqual(numero_ts(texto, r"spin > [0-9.]+ \? ([0-9.]+) : 0"),
                         numero_java(ORBE, "RESPIRO_PENSAR"),
                         "el orbe del teléfono no respira más fuerte al pensar")

    def test_el_pulso_de_la_respiracion(self):
        """`Math.sin(t * 0.9) * 0.5 + 0.5`."""
        esperado = numero_ts(fuente(ESCENA_TSX), r"Math\.sin\(t \* ([0-9.]+)\) \* 0\.5 \+ 0\.5")
        self.assertEqual(esperado, numero_java(ORBE, "PULSO_RESP"))

    def test_la_curva_de_cuando_habla(self):
        """`0.28 + 0.22 * |sin(t * 7.1)| * (0.6 + 0.4 * sin(t * 2.3))`."""
        texto = fuente(ESCENA_TSX)
        base = numero_ts(texto, r"target\.habla \? ([0-9.]+) \+")
        onda = numero_ts(texto, r"habla \? [0-9.]+ \+ ([0-9.]+) \* Math\.abs")
        rapida = numero_ts(texto, r"Math\.abs\(Math\.sin\(t \* ([0-9.]+)\)\)")
        lenta = numero_ts(texto, r"0\.4 \* Math\.sin\(t \* ([0-9.]+)\)\)")
        self.assertEqual((base, onda, rapida, lenta),
                         (numero_java(ORBE, "HABLA_BASE"), numero_java(ORBE, "HABLA_ONDA"),
                          numero_java(ORBE, "HABLA_RAPIDA"), numero_java(ORBE, "HABLA_LENTA")),
                         "la boca del orbe late a otra velocidad en el teléfono")

    def test_la_curva_de_cuando_escucha(self):
        """`0.35 + 0.3 * max(0, sin(t * 0.7)) * |sin(t * 5.0)|`."""
        texto = fuente(ESCENA_TSX)
        base = numero_ts(texto, r"forzar === 'escucha'\s*\?\s*([0-9.]+) \+")
        onda = numero_ts(texto, r"escucha'\s*\?\s*[0-9.]+ \+ ([0-9.]+) \* Math\.max")
        lenta = numero_ts(texto, r"Math\.max\(0, Math\.sin\(t \* ([0-9.]+)\)\)")
        rapida = numero_ts(texto, r"Math\.max\(0, Math\.sin\(t \* [0-9.]+\)\) \* Math\.abs\(Math\.sin\(t \* ([0-9.]+)\)\)")
        self.assertEqual((base, onda, lenta, rapida),
                         (numero_java(ORBE, "ESCUCHA_BASE"), numero_java(ORBE, "ESCUCHA_ONDA"),
                          numero_java(ORBE, "ESCUCHA_LENTA"), numero_java(ORBE, "ESCUCHA_RAPIDA")),
                         "el micrófono del teléfono agita el orbe a otro ritmo")

    def test_el_giro_de_reposo_y_el_de_pensar(self):
        """`SPIN = { idle: 0.55, thinking: 2.8 }`."""
        texto = fuente(PALETA_TS)
        self.assertEqual(numero_ts(texto, r"SPIN = \{ idle: ([0-9.]+)"),
                         numero_java(ORBE, "GIRO_REPOSO"))
        self.assertEqual(numero_ts(texto, r"thinking: ([0-9.]+)"),
                         numero_java(ORBE, "GIRO_PENSAR"))

    def test_el_radio_y_el_grosor_del_anillo(self):
        """`float R = 0.74 + wob + grain + uLevel * 0.03` y `band(r, R, 0.030)`."""
        texto = fuente(CORE_TSX)
        self.assertEqual(numero_ts(texto, r"float R = ([0-9.]+) \+ wob"),
                         numero_java(ORBE, "RADIO"))
        self.assertEqual(numero_ts(texto, r"band\(r, R, ([0-9.]+)\)"),
                         numero_java(ORBE, "GROSOR"))
        self.assertEqual(numero_ts(texto, r"grain \+ uLevel \* ([0-9.]+)"),
                         numero_java(ORBE, "CRECIMIENTO"))

    def test_la_oscilacion_y_la_granilla_del_borde(self):
        """`fbm(ring * 2.6 + …) * 0.055` y `fbm(ring * 9.0 - …) * 0.020`."""
        texto = fuente(CORE_TSX)
        self.assertEqual(numero_ts(texto, r"wob\s+= fbm\(.*?\* ([0-9.]+);"),
                         numero_java(ORBE, "OSCILACION"))
        self.assertEqual(numero_ts(texto, r"grain\s+= fbm\(.*?\* ([0-9.]+);"),
                         numero_java(ORBE, "GRANILLA"))

    def test_el_suavizado_del_nivel(self):
        """`u.uLevel.value += (drive.level - u.uLevel.value) * Math.min(1, dt * 8)`."""
        esperado = numero_ts(fuente(CORE_TSX), r"u\.uLevel\.value\)\s*\*\s*Math\.min\(1, dt \* ([0-9.]+)\)")
        self.assertEqual(esperado, numero_java(ORBE, "SUAVIZADO"))

    def test_el_empuje_y_el_temblor_del_polvo(self):
        """`push = 1.0 + uLevel * 0.35 + sin(uTime * 2.0 + aSeed * 12.0) * 0.02`."""
        texto = fuente(PARTICULAS_TSX)
        self.assertEqual(numero_ts(texto, r"push = 1\.0 \+ uLevel \* ([0-9.]+)"),
                         numero_java(ORBE, "EMPUJE"))
        self.assertEqual(numero_ts(texto, r"aSeed \* 12\.0\) \* ([0-9.]+)"),
                         numero_java(ORBE, "TEMBLOR"))
        self.assertEqual(2.0, numero_ts(texto, r"sin\(uTime \* ([0-9.]+) \+ aSeed"))

    def test_el_cascaron_del_polvo(self):
        """`const radius = 1.9 + Math.pow(Math.random(), 2) * 2.6`."""
        texto = fuente(PARTICULAS_TSX)
        self.assertEqual(numero_ts(texto, r"const radius = ([0-9.]+) \+"),
                         numero_java(ORBE, "CASCARON_INICIO"))
        self.assertEqual(numero_ts(texto, r"Math\.random\(\), 2\) \* ([0-9.]+)"),
                         numero_java(ORBE, "CASCARON_ANCHO"))


class TestElRecorteDePolvoEstaDeclarado(unittest.TestCase):
    """Aquí sí hay una diferencia entre los dos aparatos, y se dice en el propio
    archivo en vez de fingir que no existe."""

    def test_la_cara_de_pc_usa_mucho_mas_polvo_que_el_canvas(self):
        cantidad = int(entero_java(fuente(PARTICULAS_TSX), "COUNT"))
        polvo = int(entero_java(fuente(ORBE), "POLVO"))
        self.assertLess(polvo, cantidad, "el `Canvas` del teléfono no puede con 4 000 puntos")
        self.assertGreaterEqual(polvo, 120, "con menos de 120 puntos ya no es un cascarón")

    def test_el_recorte_esta_escrito_en_el_archivo(self):
        """Sin el número de la GPU en un comentario, la constante parece inventada."""
        texto = fuente(ORBE)
        self.assertIn("4 000", texto,
                      "Orbe.java debe decir de dónde se recorta el polvo (4 000 de la GPU)")


class TestLaMismaVoz(unittest.TestCase):
    """La dueña notó que «parece otra». Desde aquí la selección de voz del teléfono
    se rige por los mismos literales de `voz.ts`."""

    def test_el_idioma(self):
        esperado = re.search(r"const IDIOMA = '([\w-]+)'", fuente(VOZ_TS)).group(1)
        actual = re.search(r'\bIDIOMA = "([\w-]+)"', fuente(VOZ_JAVA)).group(1)
        self.assertEqual(esperado, actual,
                         "el teléfono dicta y habla en otro idioma que el PC")

    def test_la_velocidad_y_el_tono(self):
        texto = fuente(VOZ_TS)
        self.assertEqual(numero_ts(texto, r"velocidad: ([0-9.]+), tono"),
                         numero_java(VOZ_JAVA, "VELOCIDAD"))
        self.assertEqual(numero_ts(texto, r"tono: ([0-9.]+) \}"),
                         numero_java(VOZ_JAVA, "TONO"))

    def test_la_lista_de_voces_preferidas_es_la_mesma_y_en_orden(self):
        ts = re.findall(r"'(\w+)'", re.search(r"const PREFERIDAS = \[([^\]]+)\]",
                                              fuente(VOZ_TS)).group(1))
        java = re.findall(r'"(\w+)"', re.search(r"PREFERIDAS = \{([^}]+)\}",
                                                fuente(VOZ_JAVA)).group(1))
        self.assertEqual(ts, java,
                         "las voces preferidas de Android se eligen en otro orden que en el PC")

    def test_el_baremo_de_preferencia(self):
        """`(/natural/ ? 0 : /online/ ? 20 : 40)`."""
        texto = fuente(VOZ_TS)
        java = fuente(VOZ_JAVA)
        self.assertEqual(0, numero_ts(texto, r"/natural/i\.test\(v\.name\) \? ([0-9.]+)"))
        self.assertEqual(20, numero_ts(texto, r"/online/i\.test\(v\.name\) \? ([0-9.]+)"))
        self.assertEqual(40, numero_ts(texto, r"\? 20 : ([0-9.]+)\)"))
        self.assertEqual(0, entero_java(java, "PUNTOS_NATURAL"))
        self.assertEqual(20, entero_java(java, "PUNTOS_EN_LINEA"))
        self.assertEqual(40, entero_java(java, "PUNTOS_LOCAL"))

    def test_los_acentos_americanos_que_vale_menos_penalizar(self):
        """`/es-(co|mx|us|419)/i`."""
        grupo = re.search(r"es-\(([\w|]+)\)", fuente(VOZ_TS)).group(1).split("|")
        java = re.findall(r'"(\w+)"', re.search(r"ACENTOS = \{([^}]+)\}",
                                                fuente(VOZ_JAVA)).group(1))
        self.assertEqual(grupo, java)


class TestElOrbeEstaMontadoYCableado(unittest.TestCase):
    """Números que coinciden y una cara que no los usa serían peores que un número
    equivocado: son la prueba de que nadie montó el dibujo."""

    def test_la_cara_nativa_monta_el_orbe_en_lugar_del_anillo_quieto(self):
        cara = fuente(CARA_JAVA)
        self.assertIn("new Orbe(actividad)", cara,
                      "Cara.java sigue sin montar el reactor animado")
        self.assertNotIn("cuerpo.addView(anillo", cara,
                         "el anillo quieto volvió a la cara nativa")

    def test_la_marca_sigue_viviendo_donde_tocaba(self):
        """`Anillo` es la marca de la casa: la usa el arranque, no la cara."""
        self.assertIn("new Anillo(", fuente(PRINCIPAL),
                      "MainActivity ya no dibuja la marca al arrancar")

    def test_los_cuatro_estados_de_la_conversacion_llegan_al_orbe(self):
        cara = fuente(CARA_JAVA)
        for modo in ("REPOSO", "ESCUCHA", "PENSAR", "HABLA"):
            self.assertIn(f"Orbe.{modo}", cara,
                          f"el orbe nunca entra en `{modo}` desde Cara.java")

    def test_el_nivel_del_microfono_llega_al_orbe(self):
        """La ventaja del teléfono sobre el navegador: Android sí da el volumen del
        micrófono (`onRmsChanged`) y el PC tiene que simularlo."""
        voz = fuente(VOZ_JAVA)
        self.assertRegex(re.sub(r"\s+", " ", voz),
                         r"onRmsChanged\(float[^)]*\)[^{]*\{[^}]*medidor\.nivel\(",
                         "el `onRmsChanged` no reenvía el nivel al orbe")
        self.assertIn("normalizarRms", voz)
        cara = fuente(CARA_JAVA)
        self.assertIn("ponerNivel(", cara, "Cara.java no escucha el nivel del micrófono")

    def test_el_orbe_sabe_cuando_la_boca_calla(self):
        """En el PC el modo `HABLA` lo apaga un evento del sintetizador; en Android
        se pregunta al motor, y la cara tiene que devolver el orbe a reposo."""
        self.assertIn("isSpeaking()", fuente(VOZ_JAVA),
                      "Voz.java dejó de preguntar si está sonando")
        cara = fuente(CARA_JAVA)
        self.assertIn("orbe.modo(Orbe.REPOSO)", cara)
        self.assertIn("postDelayed(hastaQueCalle", cara)

    def test_dibujar_sin_cuadros_por_segundo_no_es_orbe(self):
        """El bucle de animación es `postInvalidateOnAnimation`; sin él el orbe sale
        pintado una vez y quieto para siempre."""
        orbe = fuente(ORBE)
        self.assertIn("postInvalidateOnAnimation()", orbe)
        self.assertIn("protected void onDraw(Canvas", orbe)
        self.assertIn("orbe.quieto(true)", fuente(CARA_JAVA),
                      "Cara.java no congela el orbe al cerrarse (dibuja en vano)")


if __name__ == "__main__":
    unittest.main()
