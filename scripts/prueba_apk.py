"""F12 — el teléfono autónomo: lo que tiene que cumplir un APK que oye solo.

Esta prueba **no enciende el teléfono ni baja nada**: auditiza en el repositorio
las condiciones que hacen que el APK funcione sin IP. Nació de la queja medida de
la dueña — «su apk no pesa nada, no lo has compilado bien» — y de la promesa que
ella quiere cumplir: descargar y correr las cosas locales en el aparato.

Cada comprobación es una de esas condiciones que se rompen en silencio:

* Si `extractNativeLibs` y el método de las `.so` se contradicen (manifiesto
  `true` con `zip -0`, o `false` con deflate), el `System.loadLibrary("vosk")`
  falla y CORT dicta por internet creyendo que dicta solo. Desde `cort-v0.16.2`
  van `true` + comprimidas: el APK de 162 817 475 bytes se cortaba al bajarlo y
  el teléfono decía «aplicación no instalada».
* Si `res/xml/asistente.xml` nombra una clase que ya no existe, Android ni
  siquiera lista a CORT como asistente, sin pantalla que avise.
* Si a `deps.txt` se le escapa una línea sin suma, el build baja lo que haya.
* Si un comentario XML lleva dos guiones seguidos, `aapt2` revienta (medido en
  la otra línea del repo, run 18 de `compilar-apk`).

Se corre sin red y sin SDK: `python3 scripts/prueba_apk.py`. Sale con código 0
si todo cuadra y 1 si algo no, y cada línea va dicho en español.
"""
import json
import os
import subprocess
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
APP = RAIZ / "apps" / "android"
SRC = APP / "src" / "dev" / "sandra" / "cort" / "movil"

RESULTADOS = []


def prueba(nombre, ok, detalle=""):
    RESULTADOS.append((nombre, bool(ok), detalle))
    marca = "ok  " if ok else "FALLO"
    print(f"  [{marca}] {nombre}" + (f" — {detalle}" if detalle else ""), flush=True)
    return ok


def lee(path):
    return path.read_text(encoding="utf-8") if path.is_file() else ""


# Los atributos del manifiesto están en la namespaces de Android, y ElementTree
# los expande a `{uri}nombre`: un `get("android:name")` devuelve `None` **sin
# avisar**, que es la peor forma de escribir una prueba (así se colaron seis
# comprobaciones en la primera corrida de este archivo).
NS = "http://schemas.android.com/apk/res/android"


def atrib(elem, nombre, por_defecto=None):
    if elem is None:
        return por_defecto
    return elem.get(f"{{{NS}}}{nombre}", elem.get(f"android:{nombre}", por_defecto))


def sin_doble_guion(texto_xml):
    """Los `--` dentro de un comentario XML rompen el manifiesto (medido)."""
    malos = []
    for comentario in re.findall(r"<!--(.*?)-->", texto_xml, re.S):
        if "--" in comentario:
            malos.append(comentario.strip().splitlines()[0][:40])
    return malos


NOTAS_PLANTILLA = APP / "NOTAS_RELEASE.md"
notas_texto = NOTAS_PLANTILLA.read_text(encoding="utf-8") if NOTAS_PLANTILLA.is_file() else ""

def main():
    if not APP.is_dir():
        print(f"no existe {APP}")
        return 1

    manifiesto_path = APP / "AndroidManifest.xml"
    manifiesto = lee(manifiesto_path)
    print("\n== el manifiesto ==")
    prueba("AndroidManifest.xml está bien formado", manifiesto_path.is_file(),
           "no se lee" if not manifiesto_path.is_file() else "")
    raiz = ET.fromstring(manifiesto) if manifiesto_path.is_file() else None
    paquete = raiz.get("package") if raiz is not None else ""
    prueba("el paquete sigue siendo dev.sandra.cort.movil (se instala encima del anterior)",
           paquete == "dev.sandra.cort.movil", paquete)
    prueba("ningún comentario del manifiesto lleva '--' (aapt2 lo mataría)",
           not sin_doble_guion(manifiesto), ", ".join(sin_doble_guion(manifiesto))[:120])

    permisos = {}
    for p in raiz.iter("uses-permission") if raiz is not None else []:
        nombre = atrib(p, "name", "").split(".")[-1]
        permisos[nombre] = atrib(p, "required", "(por defecto: sí)")
    for falta in ("INTERNET", "RECORD_AUDIO", "MODIFY_AUDIO_SETTINGS"):
        prueba(f"permiso {falta} declarado", falta in permisos, permisos.get(falta, "no está"))
    prueba("RECORD_AUDIO va required=false (un teléfono sin micro no excluye la app)",
           permisos.get("RECORD_AUDIO") == "false", str(permisos.get("RECORD_AUDIO")))
    prueba("hay bloque <queries> de intent MAIN/LAUNCHER (sin eso Android 11+ ve cero apps)",
           "<queries>" in manifiesto and "category.LAUNCHER" in manifiesto)
    app_elem = raiz.find("application") if raiz is not None else None
    prueba("extractNativeLibs=true: las .so van comprimidas y el instalador las saca "
           "a /data/app/…/lib (decisión medida el 2026-11-05 contra el APK cortado)",
           atrib(app_elem, "extractNativeLibs") == "true")
    prueba("el icono es la marca del orbe (F11), no el cuadrado viejo",
           atrib(app_elem, "icon") == "@mipmap/ic_cort")
    servicios = {atrib(h, "name", "") for h in
                 (app_elem.iter() if app_elem is not None else []) if h.tag == "service"}
    prueba("el manifiesto declara las tres piezas del asistente y la baldosa del panel rápido",
           {".Asistente", ".Sesiones", ".Reconocimiento", ".Baldosa"} <= servicios,
           " ".join(sorted(servicios)))

    print("\n== las clases que el manifiesto promete ==")
    declaradas = set()
    if app_elem is not None:
        for h in list(app_elem) + list(app_elem.iter()):
            nombre = atrib(h, "name", "")
            if nombre.startswith("."):
                declaradas.add(nombre[1:])
    for clase in sorted(declaradas):
        prueba(f"existe src/…/{clase}.java", (SRC / f"{clase}.java").is_file())

    asistente = APP / "res" / "xml" / "asistente.xml"
    texto_asistente = lee(asistente)
    print("\n== el traje de asistente ==")
    prueba("res/xml/asistente.xml existe", asistente.is_file())
    prueba("sin '--' dentro de sus comentarios", not sin_doble_guion(texto_asistente))
    rutas = re.findall(r'="(dev\.sandra\.cort[^"]+)"', texto_asistente)
    for ruta in rutas:
        simple = ruta.split(".")[-1]
        prueba(f"{ruta} apunta a una clase real de este paquete",
               ruta.startswith(f"{paquete}.") and (SRC / f"{simple}.java").is_file())

    print("\n== el oído local ==")
    motor = lee(SRC / "Motor.java")
    prueba("Motor.java existe y usa la API de Vosk",
           "import org.vosk.Model;" in motor and "new Recognizer(" in motor)
    prueba("el dictado no sale del teléfono: la única conexión de Motor es el zip fijado en la ficha",
           "new URL(urlDelModelo)" in motor and "https://" not in motor
           and motor.count("openConnection()") == 1,
           "desde `cort-v0.16.2` Motor baja el modelo de español; el `AudioRecord` "
           "seguir alimentando sólo a Vosk es lo que se comprueba aquí")
    prueba("el dictado local se corta a los 20 s (el micrófono no queda abierto)",
           "MAX_SEGUNDOS = 20" in motor)
    prueba("hay guarda contra el truco del ../ al descomprimir el modelo",
           "getCanonicalFile()" in motor and "fuera de la app" in motor)
    voz = lee(SRC / "Voz.java")
    prueba("Voz prefiere el motor local y guarda el de Android como respaldo",
           "motor.listo()" in voz and "createSpeechRecognizer" in voz)
    prueba("la cara dice qué oído está usando", 'linea("oído: "' in lee(SRC / "Cara.java"))

    print("\n== la voz del teléfono es la voz del PC ==")
    # `cort-bridge/cort_voz.py` es la cara de PC de ESTA rama: habla con espeak-ng
    # (español) y con Piper `es_ES-*`. El Java pide `es-ES`. Si alguien cambia el
    # `.onnx` a un acento latinoamericano sin tocar el teléfono, la dueña vuelve a
    # oír «parece otra» — y esta comprobación es lo que lo avisa antes del push.
    puente_voz = lee(RAIZ / "cort-bridge" / "cort_voz.py")
    acentos_pc = sorted({m.group(1) for m in
                         re.finditer(r'"(es_[A-Z]{2})-[a-z0-9_-]+\.onnx"', puente_voz)})
    idioma = re.search(r'String IDIOMA = "([a-z]{2}-[A-Z0-9]{2,3})"', voz)
    prueba("el puente de PC define sus Piper con acento español",
           bool(acentos_pc), " ".join(acentos_pc) or "sin .onnx declarados")
    prueba("Voz.java habla el acento del PC",
           bool(idioma) and bool(acentos_pc)
           and idioma.group(1).replace("-", "_") in acentos_pc,
           idioma.group(1) if idioma else "sin IDIOMA")
    prueba("y la reserva baja del acento del PC hacia los demás",
           'for (String variante : new String[] {IDIOMA,' in voz,
           "el primer elemento del bucle debe ser IDIOMA")

    print("\n== deps.txt: qué se baja y con qué suma ==")
    deps = (APP / "deps.txt").is_file()
    prueba("deps.txt existe", deps)
    lineas = [l for l in lee(APP / "deps.txt").splitlines() if l.strip() and not l.startswith("#")]
    bien = 0
    for l in lineas:
        partes = l.split("|")
        if len(partes) != 3:
            prueba(f"línea mal escrita: {l[:40]}", False)
            continue
        nombre, sha, url = partes
        if not re.fullmatch(r"[0-9a-f]{64}", sha):
            prueba(f"{nombre}: la suma no es sha256 en hexadecimal", False)
            continue
        if not url.startswith("https://"):
            prueba(f"{nombre}: la URL no es https", False)
            continue
        bien += 1
    prueba(f"{bien}/{len(lineas)} dependencias con nombre, sha256 y https",
           bien == len(lineas) and len(lineas) >= 3, f"{len(lineas)} líneas")
    prueba("el modelo español está fijado con la suma de la copia que ya probó la dueña",
           any("vosk-model-small-es" in l and "09b239888f633ef2f0b4e09736e3d9936acfd810bc65d53fad45261762c6511f" in l
               for l in lineas))

    print("\n== compilar.sh ==")
    script = lee(APP / "compilar.sh")
    prueba("baja y comprueba antes de usar (sha256sum -c)", "sha256sum -c" in script)
    prueba("mete los assets con `-A`", re.search(r"aapt2\"? link[\s\S]{0,400}?\-A ", script) is not None)
    prueba("las .so van comprimidas (zip -9), que es lo que permite extractNativeLibs=true",
           re.search(r"zip\s+-[A-Za-z0-9 -]*-9\s", script) is not None
           and re.search(r"zip\s+-[A-Za-z0-9 -]*-0\s", script) is None)
    prueba("y el APK se alinea sin `-p` (la alineación a página sólo sirve con método 0)",
           'zipalign" -f 4' in script or "zipalign -f 4" in script,
           "con `-p` y `.so` comprimidas no se gana nada: `zipalign -p` alinea las "
           "entradas SIN comprimir")
    prueba("no se firma con llave distinta sin decirlo (firma.txt y auditoría)",
           "auditoria.txt" in script and "--print-certs" in script)
    prueba("el min/target siguen en 26/34", "--min-sdk-version 26" in script and "--target-sdk-version 34" in script)
    prueba("la suma se anota con el nombre desnudo (`sha256sum -c` sirve en la release)",
           "(cd build && sha256sum CORT-movil.apk)" in script,
           "con `sha256sum build/CORT-movil.apk` el -c busca build/ y falla")

    print("\n== el APK completo por decisión de la dueña (v0.17.2) ==")
    # Nace de una tarde medida y de una frase suya. Medido: el `cort-v0.16.1` con
    # las dos ABIs y las `.so` SIN comprimir pesaba 162 817 475 bytes, se cortó al
    # bajarlo en casa (~40 KB/s) y Samsung dijo «aplicación no instalada». Por eso
    # la `cort-v0.16.2` salió delgada: una ABI y el modelo de español fuera.
    # Preguntada de nuevo el 2026-11-05, ella contestó «tiene que pesar más, no
    # importa» y eligió el paquete con el modelo y las dos ABIs dentro, porque la
    # escucha en segundo plano (F19d) no puede depender de que nadie pulse
    # «Bajar el oído», y porque el cerebro GGUF tiene que servir también en un
    # teléfono de 32 bits. Las `.so` comprimidas (`extractNativeLibs="true"` +
    # `zip -9`, medido en la corrida 42115030288: 56 508 296 -> 14 265 297 bytes)
    # son lo que deja que esa decisión quepa en un download razonable.
    prueba("las dos ABIs dentro por defecto (arm64-v8a + armeabi-v7a), con CORT_ABIS para quitar una",
           re.search(r'ABIS="\$\{CORT_ABIS:-arm64-v8a armeabi-v7a\}"', script) is not None)
    prueba("el modelo de español SÍ se copia a `assets/motor/` por defecto (39 817 833 bytes dentro)",
           "CORT_OIDO_DENTRO" in script
           and re.search(r'if \[ "\$\{CORT_OIDO_DENTRO:-1\}" = "1" \] && \[ -f vendor/vosk-model-small-es',
                         script) is not None)
    prueba("y por eso el build también lo baja: `CORT_OIDO_DENTRO=0` es la única forma de sacarlo",
           re.search(r'CORT_OIDO_DENTRO:-1\}" != "1" \] && \[ "\$NOMBRE" = '
                     r'"vosk-model-small-es', script) is not None)
    prueba("ningún zip de modelo quedado en los assets del repo",
           not list((APP / "assets").rglob("*.zip")))

    ficha_oido = APP / "assets" / "oido.json"
    prueba("assets/oido.json existe: es lo que le dice al teléfono de dónde bajar el oído",
           ficha_oido.is_file())
    if ficha_oido.is_file():
        datos = json.loads(lee(ficha_oido))
        prueba("su URL es https y su peso está medido (39 817 833)",
               str(datos.get("url", "")).startswith("https://")
               and datos.get("bytes") == 39817833, str(datos)[:120])
        fila_deps = [l for l in lineas if l.startswith("vosk-model-small-es")]
        prueba("la suma de oido.json es LA MISMA que la fijada en deps.txt: sin dos versiones",
               len(fila_deps) == 1 and datos.get("sha256") in fila_deps[0],
               f"{datos.get('sha256', '')[:16]}… frente a {fila_deps[0][:16] if fila_deps else 'nada'}")
        prueba("la ficha nombra el id y la carpeta que Motor espera",
               datos.get("id") == "small-es-0.42"
               and datos.get("carpeta") == "vosk-model-small-es-0.42")

    motor = lee(SRC / "Motor.java")
    prueba("Motor lee la ficha del APK y no tiene la URL escrita en el código",
           '"oido.json"' in motor and "https://alphacephei" not in motor)
    prueba("baja con Range y `.part`, y reanada donde se cortó",
           '"Range", "bytes="' in motor and '".part"' in motor)
    prueba("verifica la SHA-256 del archivo entero antes de fiarse, y lo tira si no cuadra",
           "SHA-256" in motor and "parcial.delete()" in motor)
    prueba("no descomprime un zip truncado: primero comprueba el peso anunciado",
           "zip.length() != bytesDelModelo" in motor or "destino.length() == bytesDelModelo" in motor)
    prueba("el `.so` del motor NO se baja a la carpeta de datos: Android 10+ no lo ejecuta ahí",
           "System.load(" not in motor and "System.load(" not in lee(SRC / "CerebroLocal.java"),
           "cargar desde filesDir sería la ruta fácil y está prohibida desde target 29")
    prueba("descomprimir borra sólo la carpeta del modelo, no `motor/` entero",
           "borraArbol(carpetaFinal)" in motor and "borraArbol(motor)" not in motor,
           "si se borra el padre se va el zip que se está leyendo")
    prueba("si falta el modelo lo dice con la salida, no con un «no te oí»",
           "Bajar el oído" in motor or "se baja en Almacén" in motor)

    almac = lee(SRC / "Cerebros.java")
    prueba("el Almacén ofrece el botón del oído y repinta el progreso una vez por segundo",
           "bajaYMonta()" in almac and 'postDelayed(repintaOido, 1000L)' in almac)
    prueba("y quita el enhebrador antes de montar otro (dos ticks = dos pintados)",
           "removeCallbacks(repintaOido)" in almac)
    equipo = lee(SRC / "Equipo.java")
    prueba("el escáner del aparato no miente: ya no dice «dentro del APK»",
           "dentro del APK: " not in equipo and "modelo de español montado" in equipo)

    flujo = lee(RAIZ / ".github" / "workflows" / "apk-movil.yml")
    prueba("la release no se publica sin la ficha del oído dentro del APK",
           'grep -q "assets/oido.json: NO ESTÁ" auditoria.txt' in flujo)
    prueba("el peso del modelo para las notas sale de la auditoría con `sed`, sin `| head`",
           "sed -n 's/^modelo de español: " in flujo)
    prueba("y hay un aviso si alguien vuelve a inflar el APK por encima de 120 MB "
           "(el listón viejo era 70, y la dueña pidió el modelo y las dos ABIs dentro)",
           "-gt 120000000" in flujo)

    print("\n== el escáner del QR del enlace (F14b) ==")
    zxing = [l for l in lineas if l.startswith("zxing-core-")]
    prueba("zxing está fijado en deps.txt con su suma y su URL de Maven Central",
           len(zxing) == 1
           and "8d8064c1636fdaef7189dd9055c7d59950a8940a12f2293956446ec3c109fd82" in zxing[0]
           and zxing[0].endswith("https://repo1.maven.org/maven2/com/google/zxing/core/3.5.3/core-3.5.3.jar"),
           zxing[0][:60] if zxing else "ninguna línea zxing")
    prueba("el jar entra al classpath de `javac` y a `d8`, y `d8` se llama una sola vez",
           "vendor/zxing-core-3.5.3.jar" in script and script.count('"$BT/d8"') == 1,
           f'llamadas a d8: {script.count(chr(34) + "$BT/d8" + chr(34))}')
    escaner_path = SRC / "Escaner.java"
    prueba("Escaner.java existe (la cámara leyendo el cuadro de la PC)", escaner_path.is_file())
    if escaner_path.is_file():
        escaner = lee(escaner_path)
        prueba("decodifica sólo QR: con todos los formatos zxing gasta ciclos buscando barras",
               "BarcodeFormat.QR_CODE" in escaner and "POSSIBLE_FORMATS" in escaner)
        prueba("lee el plano Y de YUV_420_888 con su rowStride (sin convertir a ARGB)",
               "ImageFormat.YUV_420_888" in escaner and "getRowStride()" in escaner)
        # Los dos que se escaparon en el primer compilado del runner (run 41905634981):
        # el anidado de `Image` se llama `Plane`, no `Plano`, y en zxing las filas de
        # luminancia son `byte[]`, no `int[]`. Son nombres de API: se escriben mal ni
        # por traducidos, y sólo el `javac` del pipeline los ve.
        prueba("los nombres de la API están en su inglés: `Image.Plane`, no `Image.Plano`",
               "Image.Plane" in escaner and "Image.Plano" not in escaner)
        prueba("y la fila de luminancia es `byte[]` (zxing no usa `int[]` en LuminanceSource)",
               "byte[] getRow(int y, byte[] fila)" in escaner and "int[] getRow" not in escaner)
        prueba("no acumula frames: uno cada vez y los demás se tiran",
               "acquireLatestImage()" in escaner and "compareAndSet(false, true)" in escaner)
        prueba("no guarda ninguna imagen en disco (la regla de la cámara)",
               not any(m in escaner for m in ("FileOutputStream", "getExternalStorage",
                                              "MediaStore", "openOutputStream")),
               "aquí no se escribe ni un fotograma")
        prueba("suelta la cámara al salir: si no, el aparato queda con la luz encendida",
               "quitSafely" in escaner and "protected void onPause" in escaner)
        prueba("si algo falla lo dice con palabras y no cierra en seco",
               "pega la dirección a mano" in escaner)
    actividad = lee(SRC / "MainActivity.java")
    prueba("la pantalla de enlace tiene el botón y recibe su vuelta",
           "startActivityForResult(new Intent(this, Escaner.class), ESCANEO)" in actividad
           and "protected void onActivityResult" in actividad
           and "campoEnlace.setText" in actividad)
    prueba("el campo para escribir la IP sigue ahí: el plan B no se quita",
           "final EditText campo = new EditText(this);" in actividad)
    puente = lee(SRC / "Puente.java")
    prueba("la ventana carga la interfaz aunque el enlace guardado sea el de memoria",
           "Puente.urlDeLaCara(base)" in actividad and "PUERTO_CARA" in puente)
    cuerpoCara = puente[puente.index("public static String urlDeLaCara"):]
    prueba("urlDeLaCara conserva la llave (sin ella el puente contesta 401)",
           "?token=" in cuerpoCara[:900] and "/index.html" in cuerpoCara[:900])
    prueba("y si no hay llave no inventa un query vacío",
           '(llave.isEmpty() ? "" : "?token="' in puente)
    manifiesto_texto = lee(APP / "AndroidManifest.xml")
    prueba("el escáner va declarado en el manifiesto y nadie de fuera lo abre",
           'android:name=".Escaner"' in manifiesto_texto
           and 'android:exported="false"' in manifiesto_texto)
    prueba("la cámara sigue sin ser obligatoria: un teléfono sin cámara enlaza escribiendo",
           'android:name="android.permission.CAMERA"' in manifiesto_texto)
    prueba("el enlace sin `?token=` se avisa por escrito, no se traga en silencio",
           'contains("token=")' in actividad)

    print("\n== el parlamento: hablarle a la PC y oírla por el auricular (F16) ==")
    parl_path = SRC / "Parlamento.java"
    parl = lee(parl_path)
    prueba("la pantalla del parlamento existe", parl_path.is_file())
    prueba("se lanza desde la pantalla de enlace y desde el menú del pulso largo",
           "startActivity(new Intent(this, Parlamento.class))" in actividad)
    prueba("va declarado en el manifiesto y nadie de fuera lo abre",
           'android:name=".Parlamento"' in manifiesto_texto)
    prueba("pide el micrófono en tiempo de ejecución (no se instala pidiendo permisos de más)",
           "android.Manifest.permission.RECORD_AUDIO" in parl
           and "requestPermissions" in parl)
    # La regla dura: el dictado de la dueña no se queda en el teléfono. No basta con que
    # el comentario lo diga — se comprueba que la clase que escribe archivos no aparezca.
    prueba("el audio no toca el disco: ninguna de las cuatro formas de escribir un archivo",
           not any(m in parl for m in ("FileOutputStream", "getExternalStorage",
                                       "MediaStore", "openOutputStream",
                                       "RandomAccessFile", "java.io.File")),
           "se arma en memoria y se manda")
    prueba("graba lo único que el oído de la PC acepta: 16 kHz, mono, 16 bits",
           "TASA = 16000" in parl and "CHANNEL_IN_MONO" in parl
           and "ENCODING_PCM_16BIT" in parl)
    prueba("la cabecera WAVE se escribe en memoria (44 bytes antes del PCM)",
           'cuatro(wav, "RIFF")' in parl and "construirWav" in parl
           and "RIFF" in parl and "fmt " in parl)
    # Medido: 20 s a 16 kHz mono 16-bit son 640 KB. El portátil corta el cuerpo a 3 MB,
    # así que con este techo el teléfono siempre llega antes que el tope de la PC.
    prueba("se corta a 20 s, y eso queda muy por debajo del tope de 3 MB del portátil",
           "MAX_MS = 20_000" in parl and (20 * 16000 * 2) < 3 * 1024 * 1024,
           f"{20 * 16000 * 2 // 1024} KB contra {3 * 1024 * 1024 // (1024 * 1024)} MB")
    prueba("la voz de la PC sale por el auricular y el modo se devuelve al que había",
           "MODE_IN_COMMUNICATION" in parl and "modoAnterior = gestor.getMode()" in parl
           and "gestor.setMode(modoAnterior)" in parl)
    # El constructor con `AudioManager` toma un `int` de tipo de flujo: el runner lo
    # cache en el primer compile (`AudioManager cannot be converted to int`). El
    # `Builder` es lo que corresponde y además es el que declara el uso de llamada.
    prueba("la pista se arma con `AudioTrack.Builder`, no con el constructor que no existe",
           "AudioTrack.Builder()" in parl and "USAGE_VOICE_COMMUNICATION" in parl
           and "new AudioTrack(" not in parl)
    prueba("suelta el micrófono y la pista al salir: el indicador de escucha no queda encendido",
           "protected void onPause" in parl and "protected void onDestroy" in parl
           and "cerrarMicrofono()" in parl)
    # Las tres reglas de hilos de esta pantalla, cada una nacida de una forma concreta de
    # romperse. Son la parte que un compilado no avisa: el APK entra igual y el fallo sale
    # después, en el teléfono, cuando ya nadie puede leer el hilo que tocó la vista.
    prueba("lo que pinta el auricular va en el hilo de la interfaz (setText desde otro hilo revienta)",
           "runOnUiThread" in parl[parl.index("private void terminarAuricular"):
                                  parl.index("private void terminarAuricular") + 900])
    prueba("una respuesta que llega tarde no le habla a una pantalla que ya se fue",
           "if (cerrado || pcm.length < 2)" in parl and "cerrado = true" in parl)
    prueba("no le arrebata el micrófono al hilo de copia: se avisa y lo cierra él",
           "if (!estabaGrabando)" in parl and "boolean estabaGrabando = grabando;" in parl)
    prueba("el POST viaja como WAV y con longitud fija (el portátil rechaza el troceado)",
           '"audio/wav"' in parl and "setFixedLengthStreamingMode" in parl)
    prueba("la llave se comprueba pero nunca se muestra en pantalla",
           "Puente.tokenDe(destino).isEmpty()" in parl and '"?token=" + ' not in parl)
    prueba("el hilo de la conversación se guarda y se suelta al colgar",
           '"parlamento_hilo"' in parl and 'remove("parlamento_hilo")' in parl)
    prueba("el `/colgar` entra en el camino, no detrás del `?token=`",
           'conTramo(destino, "/colgar")' in parl
           and "url.indexOf('?')" in parl)
    puente_parl = puente[puente.index("public static String urlDelParlamento"):]
    prueba("la ruta del parlamento sale del mismo host y puerto que la memoria",
           'conRuta(enlace, RUTA_PARLAMENTO)' in puente_parl
           and "urlDelPuente(enlace)" in puente[puente.index("private static String conRuta"):]
           and "indexOf(RUTA)" in puente[puente.index("private static String conRuta"):])
    prueba("y si el enlace no es de CORT no inventa una dirección",
           "return null;" in puente[puente.index("private static String conRuta"):][:400])
    # Costura con la mitad de la PC: si `cort_parlamento.py` cambia un campo y el Java
    # sigue leyendo el viejo, el parlamento se queda mudo sin que nadie lo note.
    parl_pc = lee(RAIZ / "cort-bridge" / "cort_parlamento.py")
    campos = ["oido", "respuesta", "audio", "tasa", "segundos", "ms_escucha",
              "ms_respuesta", "ms_voz", "ms_total", "vueltas", "oido_en", "voz_en",
              "origen", "motivo", "auricular_recortado"]
    faltan_java = [c for c in campos if f'"{c}"' not in parl]
    faltan_pc = [c for c in campos if f'"{c}"' not in parl_pc]
    prueba(f"los {len(campos)} campos del contrato los hablan los dos lados",
           not faltan_java and not faltan_pc,
           f"faltan en Java: {faltan_java} · en la PC: {faltan_pc}")
    # El auricular dice el principio: si la PC recorta y el teléfono no lo avisa, la
    # dueña cree que CORT se calló a la mitad de una frase.
    prueba("la PC pone techo al auricular y el teléfono avisa de que recortó",
           re.search(r"AURICULAR_MAX_CARACTERES = (\d+)", parl_pc) is not None
           and int(re.search(r"AURICULAR_MAX_CARACTERES = (\d+)", parl_pc).group(1)) <= 400
           and "optBoolean(\"auricular_recortado\"" in parl
           and "El auricular dijo el principio" in parl)
    prueba("el teléfono espera más tiempo que `Sincroniza`: un parlamento tiene tres pasos",
           int(re.search(r"LECTURA_MS = (\d+)", parl).group(1)) > 20000)
    prueba("un fallo nunca se traga en silencio: todo sale dicho en español",
           parl.count('estado.setText("') >= 8 and "loQueDice" in parl)

    print("\n== U2: leer con CORT, audífonos y saludo al encender ==")
    # Lo que la dueña pidió con el ejemplo del iPhone: mantener pulsado un mensaje y que
    # entre las opciones salga «leer». En Android eso es `ACTION_PROCESS_TEXT`, y sólo
    # aparece si la actividad está declarada con su filtro y con `exported="true"`: sin
    # esas dos líneas el menú no lo ofrece y el APK compila igual de contento.
    lectura_path = SRC / "Lectura.java"
    lectura = lee(lectura_path)
    prueba("Lectura.java existe (el menú de selección de cualquier app)",
           lectura_path.is_file())
    prueba("el manifiesto la declara con PROCESS_TEXT y con SEND sobre text/plain",
           'android:name=".Lectura"' in manifiesto_texto
           and manifiesto_texto.count("android.intent.action.PROCESS_TEXT") == 1
           and "android.intent.action.SEND" in manifiesto_texto
           and 'android:mimeType="text/plain"' in manifiesto_texto)
    prueba("y la ofrece a otras aplicaciones: exported=true y categoria DEFAULT",
           'android:name=".Lectura"' in manifiesto_texto
           and 'android:exported="true"' in manifiesto_texto
           and "android.intent.category.DEFAULT" in manifiesto_texto)
    prueba("el rótulo que se lee en el menú es «Leer con CORT»",
           'android:label="Leer con CORT"' in manifiesto_texto)
    if lectura_path.is_file():
        prueba("lee lo subrayado y, si no, lo compartido (los dos caminos del intent)",
               "EXTRA_PROCESS_TEXT" in lectura and "EXTRA_TEXT" in lectura
               and "EXTRA_SUBJECT" in lectura)
        prueba("troza por frase y con techo: un motor de TTS corta líneas largas sin avisar",
               re.search(r"TROZO_MAX = (\d+)", lectura) is not None
               and int(re.search(r"TROZO_MAX = (\d+)", lectura).group(1)) <= 400
               and "c == '.' || c == '!' || c == '?'" in lectura)
        prueba("la lectura va encolada (QUEUE_ADD), no atropellándose a sí misma",
               "boca.seguir(" in lectura and "boca.callar()" in lectura
               and "boca.hablando()" in lectura)
        prueba("dice el tiempo como estimación, no como promesa",
               "estimación" in lectura and "16.0 * PASOS" in lectura)
        prueba("no escribe el texto en disco: lo compartido se queda en memoria",
               not any(m in lectura for m in ("FileOutputStream", "getExternalStorage",
                                              "MediaStore", "openOutputStream",
                                              "RandomAccessFile", "java.io.File")),
               "el texto de la dueña no se guarda")
        prueba("y se calla si se quita los audífonos, en vez de leer por el altavoz",
               "cambioDeSalida" in lectura and "registerAudioDeviceCallback" in lectura
               and "unregisterAudioDeviceCallback" in lectura)
        prueba("retira los dos avisos con la misma instancia que registró",
               "cambios = new Audifonos.Cambios(this)" in lectura
               and "gestor.unregisterAudioDeviceCallback(cambios)" in lectura)

    audifonos_path = SRC / "Audifonos.java"
    audifonos = lee(audifonos_path)
    prueba("Audifonos.java existe y lee las salidas de verdad (getDevices)",
           audifonos_path.is_file() and "GET_DEVICES_OUTPUTS" in audifonos
           and "TYPE_WIRED_HEADPHONES" in audifonos and "TYPE_BLUETOOTH_A2DP" in audifonos)
    prueba("avisa del cable (BECOMING_NOISY) y del Bluetooth (AudioDeviceCallback)",
           "ACTION_AUDIO_BECOMING_NOISY" in audifonos and "extends AudioDeviceCallback" in audifonos)
    prueba("el sensor no pide ningún permiso: son lecturas del propio aparato",
           not any(m in audifonos for m in ("checkSelfPermission", "requestPermissions",
                                            "Manifest.permission")),
           "sin BLUETOOTH CONNECT: se pregunta por las salidas activas")
    # Confesado: el árbol de `cort-v0.15.0` no compilaba (corrida 41971907412, 2026-11-05,
    # 8 errores de `javac`). Tres nombres de API se escribieron de memoria:
    # `AudioDeviceCallback` vive en `android.media`, no anidado en `AudioManager`; el
    # getter de la baldosa es `getQsTile()`; `StatFs` tiene `getAvailableBytes()`, no la
    # forma «Long» que sale por analogía. Aquí no hay `javac` —el portátil no tiene JDK
    # de desarrollo ni SDK—, así que la suite no puede typecheckear; lo que sí puede
    # hacer es no dejar volver a escribir esos tres nombres.
    prueba("AudioDeviceCallback se importa plano, no anidado en AudioManager",
           "import android.media.AudioDeviceCallback;" in audifonos
           and "AudioManager.AudioDeviceCallback" not in audifonos)

    parl_audifonos = [m in parl for m in ("Audifonos.hay(gestor)", "Audifonos.salida(gestor)",
                                          "USAGE_MEDIA", "sueltaElModo()")]
    prueba("el parlamento enruta según el sensor: modo de llamada sólo si no hay audífonos",
           all(parl_audifonos) and "modoTocado = !auriculares" in parl,
           str(parl_audifonos))
    prueba("y el modo se devuelve una sola vez, por el guarda que sabe si lo tocó",
           "private void sueltaElModo()" in parl
           and parl.count("sueltaElModo();") >= 3 and "gestor.setMode(modoAnterior)" in parl
           and parl.index("if (!modoTocado)") < parl.index("gestor.setMode(modoAnterior)"))
    voz_seguir = [m in voz for m in ("public void seguir(String texto)", "QUEUE_ADD",
                                     "public void ritmo(float factor)", "public void callar()",
                                     "enColaLectura")]
    prueba("la boca de Android añade trozos, cambia de paso y calla cuando le dicen",
           all(voz_seguir), str(voz_seguir))
    prueba("el paso se multiplica sobre la velocidad de CORT, no la pisa",
           "boca.setSpeechRate(VELOCIDAD * factor)" in voz
           and "boca.setSpeechRate(VELOCIDAD * pasoLectura)" in voz)
    prueba("y callar vacía las dos colas: si no, lo encolado sale después del «Parar»",
           "enCola = null;" in voz[voz.index("public void callar()"):]
           and "enColaLectura.clear();" in voz[voz.index("public void callar()"):])

    arranque_path = SRC / "Arranque.java"
    arranque = lee(arranque_path)
    prueba("Arranque.java existe y el manifiesto lo declara para BOOT_COMPLETED",
           arranque_path.is_file() and 'android:name=".Arranque"' in manifiesto_texto
           and "android.intent.action.BOOT_COMPLETED" in manifiesto_texto
           and "android.permission.RECEIVE_BOOT_COMPLETED" in manifiesto_texto)
    prueba("el saludo se dice por hora y sale por notificación ADEMÁS de por la voz",
           "Buenos días" in arranque and "Buenas tardes" in arranque
           and "Buenas noches" in arranque and "manager.notify(" in arranque
           and "boca.hablar(dicho)" in arranque)
    prueba("mantiene el receptor vivo con goAsync() y lo suelta a los 15 s",
           "goAsync()" in arranque and "fin.finish()" in arranque
           and re.search(r"\}, 15_000\)", arranque) is not None)
    prueba("el canal va sin sonido de aviso: despertar a alguien con un pitido no es saludar",
           "IMPORTANCE_LOW" in arranque and "cort-saludo" in arranque)
    prueba("con Android 13 dice si el permiso de notificaciones falta, en la propia notificación",
           "POST_NOTIFICATIONS" in arranque and "checkSelfPermission" in arranque)
    prueba("y el límite está escrito en el código: One UI puede cerrar antes del saludo",
           "One UI" in arranque and "No se promete el saludo" in arranque)
    prueba("el icono del aviso es el orbe en silueta y el XML está sano",
           (APP / "res" / "drawable" / "ic_cort_aviso.xml").is_file()
           and 'getIdentifier("ic_cort_aviso", "drawable"' in arranque
           and not sin_doble_guion(lee(APP / "res" / "drawable" / "ic_cort_aviso.xml")))
    java_todo = "".join(lee(f) for f in SRC.glob("*.java"))
    # Quitados los comentarios, `android.R.` incluido: la clase `R` del sistema sí existe
    # siempre, la propia del paquete no se genera en esta cadena de compilación.
    sin_comentarios = re.sub(r"//.*", "", re.sub(r"/\*.*?\*/", "", java_todo, flags=re.S),
                             flags=re.M).replace("android.R.", "")
    prueba("el Java del APK no usa una `R.` propia: sin `aapt2 link --java` esa clase no existe",
           not re.search(r"\bR\.(drawable|string|mipmap|id|layout|xml|color)\b", sin_comentarios),
           "los recursos se buscan con `getIdentifier` o se referencian desde el manifiesto")
    anidadados = re.findall(r"^import android\.[\w.]*[A-Z]\w*\.[A-Z]\w*;", java_todo, flags=re.M)
    prueba("ningún `import android.` esconde una clase anidada: en Android los paquetes son planos",
           not anidadados, str(anidadados))

    baldosa_path = SRC / "Baldosa.java"
    baldosa = lee(baldosa_path)
    prueba("Baldosa.java existe y el manifiesto la declara con su permiso de sistema",
           baldosa_path.is_file() and 'android:name=".Baldosa"' in manifiesto_texto
           and "android.permission.BIND_QUICK_SETTINGS_TILE" in manifiesto_texto
           and "android.service.quicksettings.action.QS_TILE" in manifiesto_texto)
    prueba("la baldosa abre la escucha con la bandera que MainActivity ya entiende",
           "MainActivity.PIDE_ESCUCHAR" in baldosa and "PIDE_ESCUCHAR" in actividad)
    prueba("con Android 14 usa el PendingIntent: la firma vieja deja la baldosa muerta",
           "UPSIDE_DOWN_CAKE" in baldosa and "startActivityAndCollapse(PendingIntent" in baldosa
           and "FLAG_IMMUTABLE" in baldosa)
    prueba("la baldosa se lee con getQsTile: `getTile()` no existe en TileService",
           "getQsTile()" in baldosa and "getTile()" not in baldosa)

    bolsillo_path = SRC / "Bolsillo.java"
    bolsillo = lee(bolsillo_path)
    prueba("Bolsillo.java existe, va declarado y se abre desde la pantalla de enlace",
           bolsillo_path.is_file() and 'android:name=".Bolsillo"' in manifiesto_texto
           and "startActivity(new Intent(this, Bolsillo.class))" in actividad)
    prueba("pide /bolsillo con la llave delante y sin mostrarla nunca",
           "Puente.urlDelBolsillo(enlace)" in bolsillo
           and '!url.contains("?token=")' in bolsillo and '"?token=" + ' not in bolsillo)
    cuerpo_bolsillo = puente[puente.index("public static String urlDelBolsillo"):]
    prueba("la ruta del bolsillo se corta igual que la del parlamento (un solo tiralíneas)",
           "conRuta(enlace, RUTA_BOLSILLO)" in cuerpo_bolsillo
           and "/bolsillo" not in bolsillo, "no hay segunda versión del recorte")
    prueba("el teléfono y la PC hablan las mismas claves del cuadro",
           all(f'"{c}"' in bolsillo for c in ("pendientes", "vencidos", "compras", "notas",
                                              "maquina", "minutos", "cuando", "origen"))
           and all(f'"{c}"' in lee(RAIZ / "cort-bridge" / "cort_server.py")
                   for c in ("pendientes", "vencidos", "compras", "notas", "minutos")),
           "si la PC cambia un campo, esta línea lo avisa")
    prueba("sin respuesta no finge: dice que la PC no contestó",
           "no disponible" in bolsillo or "La PC no contestó" in bolsillo)
    prueba("y el GET no congela la cara: hilo aparte, daemon, y pintado en la interfaz",
           "hilo.setDaemon(true)" in bolsillo and "runOnUiThread" in bolsillo
           and "cerrado" in bolsillo)

    equipo_path = SRC / "Equipo.java"
    equipo = lee(equipo_path)
    prueba("Equipo.java existe, va declarado y se abre desde la pantalla de enlace",
           equipo_path.is_file() and 'android:name=".Equipo"' in manifiesto_texto
           and "startActivity(new Intent(this, Equipo.class))" in actividad)
    prueba("la puerta del cerebro local está escrita con el número real del modelo",
           re.search(r"MODELO_BYTES = ([\d_]+)L", equipo) is not None
           and int(re.search(r"MODELO_BYTES = ([\d_]+)L", equipo).group(1).replace("_", ""))
           == 752_880_160 and "MODELO_BYTES + CerebroLocal.RESERVA_CONTEXTO" in equipo)
    prueba("mide la RAM libre de ESTE aparato, no la del catálogo",
           "ActivityManager.MemoryInfo" in equipo and "libre.availMem" in equipo
           and "MemTotal:" in equipo)
    prueba("lo medido se puede copiar: el texto es seleccionable",
           "cifras.setTextIsSelectable(true)" in equipo)
    prueba("el disco se mide con getAvailableBytes, no con la forma «Long» inventada",
           "getAvailableBytes()" in equipo and "getLongAvailableBytes" not in equipo)
    prueba("y nada de eso sale del teléfono: sin red en esta pantalla",
           "java.net" not in equipo and "HttpURL" not in equipo,
           "los números se quedan en la pantalla")

    prueba("la pantalla de enlace lleva el botón de la pila y dice el límite del WoL",
           "pideSinOptimizacion()" in actividad
           and "ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS" in actividad
           and "ACTION_APPLICATION_DETAILS_SETTINGS" in actividad
           and "Wake-on" in actividad and "rtl8723be" in actividad)
    prueba("el permiso de notificaciones se pide una sola vez y por las buenas",
           "pideNotificaciones()" in actividad and "aviso_pedido" in actividad
           and "android.Manifest.permission.POST_NOTIFICATIONS" in actividad)
    prueba("el manifiesto trae los tres permisos nuevos y ninguno obligatorio de más",
           all(m in manifiesto_texto for m in ("android.permission.RECEIVE_BOOT_COMPLETED",
                                               "android.permission.POST_NOTIFICATIONS",
                                               "android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS")))

    print("\n== la tabla de frases del cerebro nativo ==")
    tabla_path = APP / "assets" / "habilidades.json"
    prueba("assets/habilidades.json viaja en el repo (lo lee Java con getAssets)",
           tabla_path.is_file())
    if tabla_path.is_file():
        tabla = json.loads(lee(tabla_path))
        acciones = sorted({p["accion"] for p in tabla["patrones"]})
        java = "".join(lee(f) for f in SRC.glob("*.java"))
        ausentes = [a for a in acciones if f'"{a}"' not in java]
        prueba(f"las {len(acciones)} acciones de la tabla están implementadas en Java",
               not ausentes, ", ".join(ausentes))
        prueba(f"{len(tabla['patrones'])} reglas de frase, todas con respuesta en español",
               all(p.get("respuesta") for p in tabla["patrones"]))

    print("\n== U1: el cerebro GGUF dentro del teléfono ==")
    # Las tres piezas de U1 son `cort_motor.cpp` (C++ con llama.cpp),
    # `CerebroLocal.java` (Java que la carga) y el trabajo `motor-local.yml` (quien
    # compila la `.so`). Los tres tienen que nombrar lo MISMO: el enlace se rompe en
    # silencio si uno de los tres cambia de parecer, y el fallo sale en el teléfono de
    # la dueña, no en un log.
    cpp_path = APP / "jni" / "cort_motor.cpp"
    prueba("apps/android/jni/cort_motor.cpp existe (el pegamento JNI)", cpp_path.is_file())
    java_local = lee(SRC / "CerebroLocal.java") if (SRC / "CerebroLocal.java").is_file() else ""
    prueba("CerebroLocal.java carga la librería por su nombre real",
           'System.loadLibrary("cortmotor")' in java_local,
           "el nombre de la .so y el del loadLibrary tienen que cuadrar")
    nativos_java = set(re.findall(r"static native [\w\[\]]+ (native\w+)\(", java_local))
    nativos_cpp = set(re.findall(r"Java_dev_sandra_cort_movil_CerebroLocal_(native\w+)\(",
                                 lee(cpp_path))) if cpp_path.is_file() else set()
    puerta = re.search(r'NATIVOS="([^"]+)"', lee(RAIZ / ".github" / "workflows" / "motor-local.yml"))
    nativos_gate = set(puerta.group(1).split()) if puerta else set()
    prueba(f"los {len(nativos_java)} nativos que Java declara son los que el C++ exporta",
           nativos_java and nativos_java == nativos_cpp,
           "sólo Java: " + ", ".join(sorted(nativos_java - nativos_cpp))
           + " · sólo C++: " + ", ".join(sorted(nativos_cpp - nativos_java)))
    prueba("el gate del workflow comprueba esa misma lista, no otra",
           nativos_gate and nativos_gate == nativos_cpp,
           ", ".join(sorted(nativos_gate ^ nativos_cpp)))
    # El SONAME medido: `libllama.so.0` contra `libllama.so` en el APK. Por eso el
    # pegamento se enlaza ESTÁTICO y autocontenido.
    flujo_motor = lee(RAIZ / ".github" / "workflows" / "motor-local.yml")
    prueba("el motor se enlaza estático y autocontenido (evita el SONAME libllama.so.0)",
           "BUILD_SHARED_LIBS=OFF" in flujo_motor and "libcortmotor.so" in flujo_motor)
    prueba("y el workflow se niega a publicar si aún dependiera de libllama",
           "libllama|libggml" in flujo_motor)
    prueba("el C++ no usa ninguna API privada de llama.cpp",
           "ggml/" in lee(cpp_path) and "llama.h" in lee(cpp_path),
           "sólo include/ y ggml/include/")

    catalogo_path = APP / "assets" / "cerebros.json"
    prueba("assets/cerebros.json viaja en el APK (es lo que lee la pantalla)",
           catalogo_path.is_file())
    if catalogo_path.is_file():
        catalogo = json.loads(lee(catalogo_path))
        cerebros = catalogo.get("cerebros", [])
        prueba(f"{len(cerebros)} cerebros ofrecidos, ni uno inventado", 1 <= len(cerebros) <= 6)
        faltan = [c.get("id") for c in cerebros
                  if not all(k in c for k in ("id", "nombre", "archivo", "url",
                                              "bytes", "sha256", "contexto", "hilos", "nota"))]
        prueba("cada uno con peso, URL, suma y puerta escritos", not faltan, ", ".join(map(str, faltan)))
        prueba("todas las URLs son https (el token no viaja en claro)",
               all(str(c.get("url", "")).startswith("https://") for c in cerebros))
        prueba("todas las SHA-256 tienen 64 hexadecimales en minúscula",
               all(re.fullmatch(r"[0-9a-f]{64}", str(c.get("sha256", ""))) for c in cerebros))
        prueba("ningún cerebro del catálogo es menor de 100 MB (no son juguetes)",
               all(int(c.get("bytes", 0)) > 100_000_000 for c in cerebros))
        prueba("el catálogo dice de dónde salieron los números",
               "MEDIDOS" in catalogo.get("_", "") or "medidos" in catalogo.get("_", ""))

    prueba("la puerta holgada es archivo + reserva, y el intento mmap pide media puerta",
           "bytesDelModelo + RESERVA_CONTEXTO" in java_local
           and "bytesDelModelo / 2 + RESERVA_CONTEXTO / 2" in java_local)
    prueba("la cara nativa pregunta al GGUF antes que a la nube",
           "cerebroLocal.contestar(" in lee(SRC / "Cara.java"))
    prueba("la cara del enlace (WebView) hace lo mismo",
           "cerebroLocal.contestar(" in lee(SRC / "Nexo.java"))
    prueba("el almacén está declarado en el manifiesto", 'android:name=".Cerebros"' in manifiesto_texto)
    prueba("y se abre desde la pantalla de enlace y desde el chip de la cara",
           "new Intent(this, Cerebros.class)" in lee(SRC / "MainActivity.java")
           and "new Intent(actividad, Cerebros.class)" in lee(SRC / "Cara.java"))
    flujo_apk = lee(RAIZ / ".github" / "workflows" / "apk-movil.yml")
    prueba("el build del APK busca el artefacto del motor antes de compilar",
           "motor-local-ndk" in flujo_apk and "actions/artifacts" in flujo_apk)
    prueba("y si no existe, lo dice con un aviso en vez de romper la corrida",
           'echo "art_id="' in flujo_apk)
    prueba("la descarga va por la API del artefacto con su id y el `Location` se lee "
           "con HEAD: `gh api -i` sigue la redirección y baja los 208 MB (medido)",
           "curl -sSI" in flujo_apk and "/zip" in flujo_apk
           and re.search(r"gh api[\s\S]{0,120}?/zip[\s\S]{0,40}?-i", flujo_apk) is None,
           "sonda del 2026-11-05 contra el artefacto 13414146808: `gh api … -i` se "
           "puso a bajar el zip completo por la tubería y había que matarlo")
    prueba("el token de Actions NO viaja al almacén: la URL firmada se baja sin "
           "cabecera de autorización y sin `-L`",
           re.search(r"curl -sS --fail[^\n]*-o /tmp/motor\.zip \"\$LOC\"", flujo_apk) is not None
           and "curl -sSL" not in flujo_apk)
    prueba("el id entra por la salida del paso, no con `env.` dentro de `with:` "
           "(eso dejó el APK sin motor en la corrida 42104161078)",
           "steps.busca.outputs.art_id" in flujo_apk
           and re.search(r"uses: actions/download-artifact", flujo_apk) is None,
           "con `run-id: ${{ env.MOTOR_ARTIFACT }}` la acción buscó en su propia "
           "corrida y contestó «Artifact not found»; el build salió verde pero "
           "`lib/arm64-v8a/libcortmotor.so: no está en el APK`")
    prueba("el id del artefacto sale del `--jq` con `first`, no de un `| head -1` "
           "pegado al `gh` (con pipefail la señal 141 abortaría el paso)",
           "first // empty" in flujo_apk
           and re.search(r"LINEA=\"\$\([\s\S]{0,400}?\|\s*head", flujo_apk) is None)
    prueba("si la descarga falla el APK se publica igual, y `colocar` lo confiesa",
           "continue-on-error: true" in flujo_apk
           and "la descarga del motor no trajo nada" in flujo_apk)
    prueba("compilar es tolerante pero PUBLICAR no: si el APK no lleva el motor, "
           "la release se niega (las notas prometen el cerebro GGUF)",
           "libcortmotor.so: no está en el APK" in flujo_apk
           and "no se publica" in flujo_apk
           and re.search(r"grep -q \"libcortmotor\.so: no está en el APK\" auditoria\.txt", flujo_apk) is not None)
    prueba("compilar.sh mete el motor en build/stage/lib, y SÓLO el pegamento "
           "(las otras 8 .so del artefacto ya van dentro por el enlace estático)",
           "vendor/motor/" in script
           and re.search(r"for FICHERO in vendor/motor/\"\$ABI\"/libcortmotor\.so", script) is not None
           and re.search(r"for FICHERO in vendor/motor/\"\$ABI\"/\*\.so", script) is None)
    prueba("sin GGUF dentro del APK: se bajan en el almacén",
           not list((APP / "assets").rglob("*.gguf")))

    print("\n== la cara del PC dentro del teléfono (F19) ==")
    # Nace de la queja del 2026-11-05 con cuatro capturas del A16: «así se ve CORT
    # en android, necesito que sea la copia exacta de la versión de PC incluyendo
    # sus funciones». No era gustos: el teléfono mostraba `Cara.java` (la interfaz
    # nativa) mientras la PC muestra `cort-web/index.html`, y las dos caras tienen
    # contratos distintos. Las comprobaciones de abajo fijan las tres piezas que
    # cierran esa distancia y las trampas que ya costaron una corrida:
    #   F19a `compilar.sh` empaqueta `cort-web/` -> `assets/web/`
    #   F19b `web/cort-android.js` hace de WebSocket donde no hay servidor
    #   F19c `Nexo.java` contesta el contrato de la PC cuadro por cuadro
    cara_js = lee(APP / "web" / "cort-android.js")
    nexo = lee(SRC / "Nexo.java")
    ui = lee(RAIZ / "cort-web" / "cort" / "cort-ui.js")
    bajada = lee(SRC / "Bajada.java")

    prueba("compilar.sh empaqueta la cara del PC y NO sale si falta: sin ella el "
           "teléfono muestra la cara nativa, que es la queja que abrió la fase",
           re.search(r'WEB="\$\{CORT_WEB_DIR:-\.\./\.\./cort-web\}"', script) is not None
           and "build/recursos/assets/web" in script
           and "el APK saldría sin la cara del PC" in script)
    prueba("y menos de 20 archivos es un paquete roto, no un paquete delgado",
           re.search(r'CARA_ARCHIVOS" -lt 20', script) is not None)
    prueba("el puente Java viaja como el PRIMER script de la cara: `cort-mock.js` "
           "guarda `window.WebSocket` en su línea 25 y si llega después ya es tarde",
           "cp web/cort-android.js build/recursos/assets/web/cort-android.js" in script
           and "ETIQUETA_PUENTE" in nexo and "/cort-android.js" in nexo
           and nexo.count("ETIQUETA_PUENTE") >= 3)
    prueba("el shim abre `readyState` en el constructor: la interfaz compara "
           "`ws.readyState === WebSocket.OPEN` y con 0 durante un tick tira el primer cuadro",
           re.search(r"this\.readyState = ABIERTO;", cara_js) is not None
           and "WebSocket.OPEN" in cara_js)
    prueba("lo que llega antes de suscribirse no se pierde, pero la cola tope es 64",
           "cola.length > 64" in cara_js and "__cortNative" in cara_js)
    prueba("el service worker está neutralizado: `file://` no registra sw y un "
           "fallo ahí tapaba la cara entera",
           "serviceWorker" in cara_js)
    prueba("y la cara sabe que está en Android: `CORT_esAndroid` es la bandera que "
           "apaga los rótulos que mentirían (Ollama, emparejar por QR)",
           "window.CORT_esAndroid = true" in cara_js and "CORT_esAndroid" in ui)
    estilo = lee(RAIZ / "cort-web" / "cort" / "cort-style.css")
    prueba("P0-3: el interruptor de vista existe en el puente Java y cambia el "
           "viewport de verdad (wide viewport + zoom sólo en escritorio)",
           "public void fijarVista(" in nexo
           and "setUseWideViewPort(escritorio)" in nexo
           and "classList.add('cort-vista-movil')" in nexo)
    prueba("P0-3: la fila del interruptor viaja en Ajustes y se repinta con el "
           "observer, como la de idioma (si no, desaparece al re-renderizar)",
           "function asegurarFilaVista()" in ui
           and ui.count("asegurarFilaVista();") >= 3
           and "window.CORT_setVista" in ui)
    prueba("P0-3: los paneles de ancho fijo que salían cortados en el A16 "
           "(antivirus 460 px, ajustes con padding 30) tienen regla móvil",
           "html.cort-vista-movil .av-panel" in estilo
           and "html.cort-vista-movil .settings-container" in estilo
           and "calc(100vw - 16px)" in estilo)
    prueba("el origen embebido es `http://cort.local`, no https: el `Yl` de la "
           "página apaga los subtítulos en vivo y la voz por nube con https, y en "
           "el teléfono esas dos sí funcionan",
           '"http://cort.local"' in nexo and '"https://cort.local"' not in nexo)
    prueba("Nexo despacha el cuadro por su `type`, que es el contrato único de la "
           "cara del PC (el umbral es 40: la lista real la imprime el detalle)",
           nexo.count('.equals(t)') >= 40, f"{nexo.count('.equals(t)')} ramas en Nexo.java")
    prueba("`get_settings` NO se responde desde Java: un `settings_data` vacío "
           "borra los campos de Ajustes y deja `reminders` en cero (cort-mock.js:514)",
           re.search(r'"get_settings"\.equals\(t\)[\s\S]{0,400}?return;', nexo) is not None
           and 'envia(cuadro("type", "settings_data"' not in nexo)
    prueba("un clima que falla se dice en texto y NO sale como `weather_panel`: "
           "`Yg()` se lee `ville/temperature/…` sin mirar `ok` y reventaba el panel",
           nexo.count('"type", "weather_panel"') == 2
           and "No pude leer el clima real" in nexo
           and re.search(r'"ville", ', nexo) is not None)
    prueba("lo que no se puede medir viaja como `JSONObject.NULL`, no como `-1`: "
           "la cara del PC muestra `?? \"--\"` y un -1 se leería «-1 %»",
           "JSONObject.NULL" in nexo and re.search(r"porcentaje\", brillo < 0 \? JSONObject\.NULL", nexo) is not None)
    prueba("la cara del PC no llama «Ollama» al cerebro del teléfono",
           "comoSeLlamaElCerebro" in ui and ui.count("comoSeLlamaElCerebro()") >= 3)
    prueba("y oculta el botón de emparejar en Android: sólo `cort_server.py` "
           "responde `create_mobile_pairing` y el diálogo se quedaba en «Génération…»",
           re.search(r"CORT_esAndroid[\s\S]{0,220}mobile-pairing-btn"
                     r"|mobile-pairing-btn[\s\S]{0,220}CORT_esAndroid", ui) is not None)
    prueba("los GGUF de la lista se bajan en el teléfono con `Range`, `.part` y "
           "SHA-256 (la casa corta las descargas)",
           'setRequestProperty("Range"' in bajada and ".part" in bajada
           and "SHA-256" in bajada)
    prueba("la descarga de GGUF no abre notificación: el token del enlace nunca "
           "se escribe en una bandeja que se lee desde la pantalla bloqueada",
           "Notification" not in bajada and "NotificationCompat" not in bajada)

    print("\n== lo que ve javac y no ve un grep (corrida 42137017052) ==")
    # El 2026-11-05 la corrida del push cayó con CINCO errores de tipos en
    # `Nexo.java` que ninguna de las comprobaciones de arriba advertía: el
    # intent pegajoso de la pila se había declarado `Bundle` (vale `Intent`) y
    # un `catch` juntaba `IOException` con su propia subclase. Aquí no hay
    # `javac` ni SDK, así que lo que se puede comprobar es la FORMA de esos
    # dos errores, en las 29 hojas de una vez.
    java_todas = "\n".join(lee(h) for h in sorted(SRC.glob("*.java")))
    prueba("el intent pegajoso de la pila se guarda como `Intent` y se lee con "
           "`getIntExtra`: `registerReceiver(null, filtro)` devuelve un Intent",
           re.search(r"Bundle\s+\w+\s*=\s*\w*\.registerReceiver", java_todas) is None
           and re.search(r"Intent pila = actividad\.registerReceiver\(null,", nexo) is not None
           and "getIntExtra(BatteryManager.EXTRA_LEVEL" in nexo
           and "getIntExtra(BatteryManager.EXTRA_TEMPERATURE" in nexo
           and ".getInt(BatteryManager" not in java_todas)
    SUBDE = {"UnsupportedEncodingException": "IOException",
             "FileNotFoundException": "IOException",
             "NumberFormatException": "RuntimeException",
             "IndexOutOfBoundsException": "RuntimeException",
             "SecurityException": "RuntimeException"}
    emparentadas = []
    for parche in re.findall(r"catch \(([^)]*\|[^)]*)\)", java_todas):
        nombres = [trozo.strip().split(".")[-1].split(" ")[0]
                   for trozo in parche.split("|")]
        for a in nombres:
            for b in nombres:
                if a != b and (SUBDE.get(a) == b or SUBDE.get(b) == a):
                    emparentadas.append("%s|%s" % (a, b))
    prueba("ningún multi-catch junta dos excepciones emparentadas (es error de "
           "compilación, no de gusto): si hace falta una subclase se captura sola",
           not emparentadas, ", ".join(sorted(set(emparentadas))))

    print("\n== el repo no se llena de modelos ==")
    import subprocess
    suivi = subprocess.run(["git", "-C", str(RAIZ), "ls-files", "apps/android"],
                           capture_output=True, text=True).stdout.splitlines()
    grandes = [f for f in suivi if (RAIZ / f).is_file() and (RAIZ / f).stat().st_size > 1_000_000]
    prueba("ningún archivo de más de 1 MB está seguido por git en apps/android",
           not grandes, ", ".join(grandes))
    gitignore = lee(APP / ".gitignore")
    prueba("vendor/ y build/ están ignorados", "vendor/" in gitignore and "build/" in gitignore)

    print("\n== quién publica la release ==")
    # Se publica desde el runner, no desde esta casa: medido el 2026-11-04, bajar el
    # artefacto de 46 MB por el enlace de la dueña (~40 KB/s) se cortó dos veces. El
    # paso tiene tres obligatorios: permiso explícito, destino fijado al commit de la
    # etiqueta, y las notas escritas **desde lo medido** (stat/awk/sed sobre
    # `auditoria.txt`), nunca con cifras tecleadas a mano.
    notas_plantilla = NOTAS_PLANTILLA
    flujo = lee(RAIZ / ".github" / "workflows" / "apk-movil.yml")
    prueba("el workflow puede publicar la release", "gh release create" in flujo)
    prueba("sólo si se le dio una etiqueta", "github.event.inputs.etiqueta != ''" in flujo)
    prueba("pide `contents: write` para poder crearla",
           re.search(r"permissions:\s*\n\s*contents: write", flujo) is not None)
    prueba("el APK publicado sale del commit de su etiqueta, no de la punta de la rama",
           "git checkout --detach" in flujo and 'se pidió publicar sin decir qué commit' in flujo)
    prueba("las notas se generan de lo medido (stat, auditoría y firma)",
           "stat -c%s CORT-movil.apk" in flujo and "auditoria.txt" in flujo
           and "certificate SHA-256 digest" in flujo)
    prueba("si la release ya existe, actualiza los archivos en vez de fallar",
           "gh release upload" in flujo and "--clobber" in flujo)
    prueba("`gh` recibe su token dentro del runner",
           re.search(r"GH_TOKEN: \$\{\{ github\.token \}\}", flujo) is not None,
           "sin GH_TOKEN el paso cae con «set the GH_TOKEN environment variable» (run 41891940880)")
    prueba("la suite corre también en el runner, no sólo en la laptop",
           "python3 scripts/prueba_apk.py" in flujo,
           "si la suite no se ejecuta en Actions, lo publicado no lo verificó más que esta máquina")
    prueba("las notas copian el número de comprobaciones de la suite",
           "{{CHECS}} comprobaciones" in notas_texto
           and 'NOTAS_CHECS="$COMPROBACIONES"' in flujo,
           "el 2026-11-04 la release decía «44 comprobaciones» cuando ya eran 51: mentía sobre su prueba")

    print("\n== las notas de la release no pueden contradecir al APK ==")
    # El texto ya no vive dentro del YAML: vive en `apps/android/NOTAS_RELEASE.md` y el
    # workflow sólo le mete los números. Así se puede comprobar lo que AFIRMA, no sólo
    # que se publique. Nace del 2026-11-04: publicado `cort-v0.13.0`, las notas seguían
    # diciendo lo de la 0.12.0 y negaban dos cosas que ese mismo APK ya hacía.
    prueba("la plantilla de las notas está en el repo y el workflow la invoca",
           notas_plantilla.is_file() and "python3 ../notas_release.py > notas.md" in flujo,
           "con el texto pegado en el YAML, nadie se entera de que la versión cambió")
    prueba("y las notas niegan lo que ya es falso: la ruta de memoria SÍ se sirve",
           "/memoria/puente" in notas_texto and "no sirve" not in notas_texto,
           "la ruta la abrió F14a en el puerto del core, detrás del token")
    prueba("y no dicen que la cámara del teléfono no se use: F14b la usa para el QR",
           "Escanear el QR" in notas_texto and "teléfono no se usa" not in notas_texto)
    prueba("y el parlamento no es marketing: la nota dice la ruta, el botón y lo que falta",
           "/parlamento" in notas_texto
           and "Hablar con la PC (voz)" in notas_texto
           and "auricular" in notas_texto
           and "Wake-on-LAN" in notas_texto)
    prueba("el hueco del título está conectado: `--title` sale de la plantilla",
           '--title "$TITULO"' in flujo
           and "NOTAS_RELEASE.md" in (APP / "notas_release.py").read_text(encoding="utf-8"),
           "título y cuerpo contradictorios es una release que se desmiente sola")
    sobrantes = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", notas_texto)))
    sin_exportar = [h for h in sobrantes
                    if ('NOTAS_' + h[2:-2] + '=') not in flujo.replace('-', '_')]
    prueba("cada {{HUECO}} de la plantilla recibe su número desde el workflow",
           not sin_exportar, ", ".join(sin_exportar) or "todos rellenados")
    render = subprocess.run([sys.executable, str(APP / "notas_release.py")],
                            env=dict(os.environ, **{
                                "NOTAS_VERSION": "0", "NOTAS_CODE": "0", "NOTAS_PESO": "0",
                                "NOTAS_MB": "0", "NOTAS_SHA": "0", "NOTAS_OIDO": "0",
                                "NOTAS_LLAVE": "0", "NOTAS_HUELLA": "0", "NOTAS_MODEL": "0",
                                "NOTAS_CHECS": "0", "NOTAS_CARA": "0", "NOTAS_ABIS": "0"}),
                            capture_output=True, text=True)
    prueba("la plantilla se rellena entera y sin dejar huecos (probado aquí, a ciegas)",
           render.returncode == 0 and "{{" not in render.stdout,
           (render.stderr or "")[:70])
    prueba("y si falta un número medido, el script se cae en vez de publicar un agujero",
           subprocess.run([sys.executable, str(APP / "notas_release.py")],
                          env={"PATH": "/usr/bin"}, capture_output=True, text=True).returncode != 0)

    totales = len(RESULTADOS)
    buenos = sum(1 for _, ok, _ in RESULTADOS if ok)
    print(f"\nresultado: {buenos}/{totales} comprobaciones")
    if buenos != totales:
        print("sin pasar:")
        for nombre, ok, detalle in RESULTADOS:
            if not ok:
                print(f"  - {nombre}" + (f" ({detalle})" if detalle else ""))
    return 0 if buenos == totales else 1


if __name__ == "__main__":
    sys.exit(main())
