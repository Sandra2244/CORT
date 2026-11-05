"""F12 — el teléfono autónomo: lo que tiene que cumplir un APK que oye solo.

Esta prueba **no enciende el teléfono ni baja nada**: auditiza en el repositorio
las condiciones que hacen que el APK funcione sin IP. Nació de la queja medida de
la dueña — «su apk no pesa nada, no lo has compilado bien» — y de la promesa que
ella quiere cumplir: descargar y correr las cosas locales en el aparato.

Cada comprobación es una de esas condiciones que se rompen en silencio:

* Si falta `extractNativeLibs="false"` o las `.so` viajan comprimidas, el
  `System.loadLibrary("vosk")` falla y CORT dicta por internet creyendo que
  dicta solo.
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
    prueba("extractNativeLibs=false: el .so se carga desde el APK, sin copiarlo a datos",
           atrib(app_elem, "extractNativeLibs") == "false")
    prueba("el icono es la marca del orbe (F11), no el cuadrado viejo",
           atrib(app_elem, "icon") == "@mipmap/ic_cort")
    prueba("el manifiesto declara las tres piezas del asistente",
           len([h for h in (app_elem.iter() if app_elem is not None else []) if h.tag == "service"]) == 3)

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
    prueba("Motor.java no abre ninguna conexión (local por construcción)",
           "java.net" not in motor and "HttpURL" not in motor)
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
    prueba("las .so van SIN comprimir (zip -0)", re.search(r"zip\s+-[A-Za-z0-9 -]*-0\s", script) is not None)
    prueba("y alineadas a página (zipalign -p)", "zipalign\" -f -p 4" in script or "zipalign -f -p 4" in script)
    prueba("no se firma con llave distinta sin decirlo (firma.txt y auditoría)",
           "auditoria.txt" in script and "--print-certs" in script)
    prueba("el min/target siguen en 26/34", "--min-sdk-version 26" in script and "--target-sdk-version 34" in script)
    prueba("la suma se anota con el nombre desnudo (`sha256sum -c` sirve en la release)",
           "(cd build && sha256sum CORT-movil.apk)" in script,
           "con `sha256sum build/CORT-movil.apk` el -c busca build/ y falla")

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
           "urlDelPuente(enlace)" in puente_parl and "RUTA_PARLAMENTO" in puente_parl)
    prueba("y si el enlace no es de CORT no inventa una dirección",
           "return null;" in puente_parl[:400])
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
                                "NOTAS_CHECS": "0"}),
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
