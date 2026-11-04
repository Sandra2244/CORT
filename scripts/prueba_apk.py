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
           re.search(r"\$COMPROBACIONES comprobaciones", flujo) is not None,
           "el 2026-11-04 la release decía «44 comprobaciones» cuando ya eran 51: mentía sobre su prueba")

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
