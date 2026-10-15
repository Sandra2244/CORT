#!/usr/bin/env python3
"""Refresca `apps/apk/simbolos-android.json`: el diccionario de constantes del SDK.

Por qué existe este script y no simplemente «mirar la documentación»:

* En esta máquina **no hay SDK ni `javac`** (medido). El único compilador del
  proyecto corre en un runner de GitHub Actions, y allí un `cannot find symbol`
  cuesta un Run entero — dos costó: `AlarmClock.EXTRA_TIME_IN_MILLIS` primero y
  `AlarmClock.EXTRA_COUNTDOWN` después, los dos escritos de memoria y los dos
  **inexistentes** en AOSP.
* La documentación pública de Android se renderiza con JavaScript y no se puede
  leer desde una terminal; el fuente de AOSP sí.

Qué hace: descarga las clases que usa el APK, saca toda constante pública
`static final` en mayúsculas que empiece por alguno de los prefijos de abajo (o
esté en la lista de sueltas), y escribe el JSON con su marca de tiempo. **Desde
`v0.15.5` escribe además `apps/apk/lanza-android.json`**, con las firmas `throws`
de los métodos que el Java llama sobre objetos del sistema — otro error que sólo
existe al compilar, y que costó una Release entera (leer el bloque de abajo)—.
**Desde `v0.16.0` escribe la tercera salida**, `apps/apk/devuelve-android.json`,
con el tipo que devuelve cada método cuyo resultado se guarda en una variable.

Uso — necesita red, y **no** forma parte de `make test`:

    python3 scripts/simbolos_android.py

Después de refrescarlo, `make test` es quien comprueba que el Java del APK siga
dentro del diccionario (`services/core/tests/test_apk_cerebro.py`) y que recoja
lo que las firmas declaran lanzar (`services/core/tests/test_apk_manifesta.py`).
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "apps" / "apk" / "simbolos-android.json"
SALIDA2 = RAIZ / "apps" / "apk" / "lanza-android.json"
SALIDA3 = RAIZ / "apps" / "apk" / "devuelve-android.json"

BASE = "https://raw.githubusercontent.com/aosp-mirror/platform_frameworks_base/main/"

# Las clases que el Java del APK usa (o podría usar). Las rutas son las de AOSP:
# `AudioManager` vive en `media/`, no en `core/`, y eso también se aprendió aquí.
ARCHIVOS = {
    "AlarmClock": "core/java/android/provider/AlarmClock.java",
    "AudioManager": "media/java/android/media/AudioManager.java",
    "Build": "core/java/android/os/Build.java",
    "EditorInfo": "core/java/android/view/inputmethod/EditorInfo.java",
    "Intent": "core/java/android/content/Intent.java",
    "PackageManager": "core/java/android/content/pm/PackageManager.java",
    "RecognizerIntent": "core/java/android/speech/RecognizerIntent.java",
    "Settings": "core/java/android/provider/Settings.java",
    "SpeechRecognizer": "core/java/android/speech/SpeechRecognizer.java",
    "TextToSpeech": "core/java/android/speech/tts/TextToSpeech.java",
    "View": "core/java/android/view/View.java",
    # Desde `v0.15.1` la pantalla de ajustes de la nube también nombra
    # `InputType.TYPE_TEXT_VARIATION_PASSWORD` y `..._URI`, y un flag de teclado
    # escrito de memoria es exactamente el `cannot find symbol` que ya costó dos
    # Runs con `AlarmClock`.
    "InputType": "core/java/android/text/InputType.java",
}

PREFIJOS = ("ACTION_", "EXTRA_", "CATEGORY_", "FLAG_", "STREAM_", "ADJUST_", "RINGER_",
            "MODE_", "ERROR_", "LANG_", "QUEUE_", "IME_", "PERMISSION_", "RESULTS_",
            "LANGUAGE_MODEL_", "ALARM_SEARCH_MODE_", "TYPE_")
SUELTAS = {"SUCCESS", "INFINITE", "FOCUS_DOWN", "FOCUS_UP", "FOCUS_LEFT", "FOCUS_RIGHT",
           "VISIBLE", "INVISIBLE", "GONE", "MANUFACTURER", "MODEL", "VERSION", "SDK_INT",
           "DEVICE", "PRODUCT", "BRAND"}

CONSTANTE = re.compile(r"public\s+static\s+final\s+[\w.<>\[\]]+\s+([A-Z][A-Z0-9_]*)\b")

"""
LOS MÉTODOS QUE OBLIGAN A RECOGER ALGO (segunda salida del script)
==================================================================

`javac` no sólo mira que el símbolo exista: mira qué **declara** cada método que se
llama. Un `throws` sin recoger es un error de compilación, y en esta máquina no hay
`javac`. El run **38812262724** de `compilar-apk` se cayó por uno:

    Reconocimiento.java:40: error: unreported exception RemoteException;
    must be caught or declared to be thrown

porque `RecognitionService.Callback.error(int)` declara `throws RemoteException`
(leyendo AOSP: es un proxy a otro proceso). `v0.15.4` quedó publicado con su texto y
**sin APK**. Desde aquí se sacan las firmas con `throws` de las clases cuyo objeto
llama el Java del APK, y `test_apk_manifesta.py` (`TestLoQueJavacObligaARecoger`)
exige que cada llamada aparezca dentro de un `try` que recoja lo declarado.
"""
LANZA = {
    # nombre de la clase de AOSP: (ruta en el repo, (métodos que nuestro Java llama))
    "RecognitionService": ("core/java/android/speech/RecognitionService.java",
                           ("error", "results", "partialResults", "beginningOfSpeech",
                            "endOfSpeech", "bufferReceived", "rmsChanged",
                            "readyForSpeech", "segmentResults", "endOfSegmentedSession")),
}

FIRMA = re.compile(
    r"public\s+(?:@\w+\s+)*(?:static\s+|final\s+|synchronized\s+)*"
    r"[\w.<>@\[\] ]+?\s(\w+)\s*\([^)]*\)\s*(?:throws\s+([\w.,\s@<>]+?))?\s*[;{]")

"""
LO QUE DEVUELVE CADA MÉTODO DEL SDK (tercera salida del script)
===============================================================

La tercera clase de error que **sólo existe al compilar**: recibir el resultado de
un método del SDK en una variable del tipo equivocado. `TextToSpeech.getVoices()`
devuelve `Set<Voice>`, y este corte lo tenía declarado como `List<Voice>` — escrito
de memoria, otra vez. `javac` lo rechaza con «incompatible types», el runner cae y
la Release sale sin APK. Es el mismo fallo de forma que los dos `AlarmClock` y que
el `RemoteException`: **aquí no se confía en el recuerdo, se lee AOSP**.

Se guarda el tipo de retorno declarado y `test_apk_manifesta.py`
(`TestLoQueElSdkDevuelve`) exige que toda asignación `Tipo x = …método(…)` del Java
use ese tipo — o un supertipo suyo, que también compila—.
"""
DEVUELVE = {
    "TextToSpeech": ("core/java/android/speech/tts/TextToSpeech.java",
                     ("getVoices", "isSpeaking", "setVoice", "setSpeechRate",
                      "setPitch", "setLanguage")),
    "Bundle": ("core/java/android/os/Bundle.java", ("getStringArrayList",)),
}

REGRESA = re.compile(
    r"public\s+(?:@\w+\s+)*(?:static\s+|final\s+|synchronized\s+)*"
    r"([\w.<>@\[\]]+(?:\s*\[\])?)\s+(\w+)\s*\([^)]*\)\s*(?:throws[^;{]+)?[;{]")


def descargar(clase: str, ruta: str) -> list[str]:
    texto = urllib.request.urlopen(BASE + ruta, timeout=90).read().decode("utf-8", "replace")
    nombres = sorted(n for n in set(CONSTANTE.findall(texto))
                     if n.startswith(PREFIJOS) or n in SUELTAS)
    if not nombres:
        raise SystemExit(f"{clase}: ninguna constante encontrada — cambió la ruta en AOSP")
    return nombres


def firma_clase(archivo: str) -> str:
    return urllib.request.urlopen(BASE + archivo, timeout=90).read().decode("utf-8", "replace")


def metodos_que_lanzan(clase: str, archivo: str, nombres: tuple[str, ...]) -> dict[str, list[str]]:
    """`{método: [excepciones declaradas]}` para los métodos que interesan.

    Una clase puede declarar el mismo método dos veces (el `Callback` abstracto y su
    `Stub`), así que se **unen** las excepciones de todas las firmas encontradas.
    """
    texto = firma_clase(archivo)
    salida: dict[str, set[str]] = {}
    for nombre, excepciones in FIRMA.findall(texto):
        if nombre not in nombres:
            continue
        declaradas = {e.strip().split(".")[-1].replace("@", "")
                      for e in excepciones.split(",")} if excepciones.strip() else set()
        salida.setdefault(nombre, set()).update(e for e in declaradas if e and e != nombre)
    resultado = {n: sorted(v) for n, v in salida.items() if v}
    faltan = sorted(set(nombres) - set(resultado))
    if faltan:
        raise SystemExit(f"{clase}: no encontró la firma de {faltan} — cambió AOSP o la ruta")
    return resultado



def metodos_que_devuelven(clase: str, archivo: str,
                          nombres: tuple[str, ...]) -> dict[str, list[str]]:
    """`{método: [tipos declarados tras `public`]}` para los métodos que interesan.

    Como con las firmas `throws`, un método sobrecargado puede devolver tipos
    distintos en AOSP: se guardan **todos** y la prueba admite cualquiera. Si un
    método nombrado no aparece, el script falla en vez de escribir un hueco.
    """
    texto = firma_clase(archivo)
    salida: dict[str, set[str]] = {}
    for tipo, nombre in REGRESA.findall(texto):
        if nombre in nombres:
            salida.setdefault(nombre, set()).add(" ".join(tipo.split()))
    faltan = sorted(set(nombres) - set(salida))
    if faltan:
        raise SystemExit(f"{clase}: no encontró el retorno de {faltan} — cambió AOSP o la ruta")
    return {n: sorted(v) for n, v in salida.items()}


def main() -> int:
    clases = {}
    for clase, ruta in ARCHIVOS.items():
        clases[clase] = descargar(clase, ruta)
        print(f"  {clase}: {len(clases[clase])} constantes")
    contenido = {
        "que_es": "Las constantes públicas del SDK de Android que puede nombrar el Java del "
                  "APK. Aquí no hay `javac` ni SDK: el único compilador vive en un runner y "
                  "cada `cannot find symbol` cuesta un Run, así que la lista se copia de "
                  "AOSP y no de memoria.",
        "fuente": "aosp-mirror/platform_frameworks_base, rama main",
        "url_base": BASE,
        "verificado": date.today().isoformat(),
        "como_refrescar": "python3 scripts/simbolos_android.py",
        "recorte": "constantes con alguno de los `prefijos`, más las `sueltas` nombradas",
        "prefijos": list(PREFIJOS),
        "sueltas": sorted(SUELTAS),
        "clases": clases,
    }
    SALIDA.write_text(json.dumps(contenido, ensure_ascii=False, indent=1) + "\n",
                      encoding="utf-8")
    total = sum(len(v) for v in clases.values())
    print(f"{SALIDA.relative_to(RAIZ)}: {total} constantes en {len(clases)} clases")

    lanzan, verificado = {}, date.today().isoformat()
    for clase, (archivo, nombres) in LANZA.items():
        metodos = metodos_que_lanzan(clase, archivo, nombres)
        lanzan[clase] = {"archivo": archivo, "metodos": metodos}
        print(f"  {clase}: {len(metodos)} métodos con `throws` "
              f"({', '.join(sorted({e for m in metodos.values() for e in m}))})")
    SALIDA2.write_text(json.dumps({
        "que_es": "Los métodos de las clases de Android que **declaran** `throws` y que el "
                  "Java del APK llama sobre un objeto del sistema. `javac` obliga a recoger "
                  "un `throws` declarado, y aquí no hay `javac`: el run 38812262724 cayó "
                  "porque `RecognitionService.Callback.error(int)` lanza `RemoteException` "
                  "y no se recogía. Las pruebas del APK (`TestLoQueJavacObligaARecoger`) "
                  "leen este archivo y exigen el `catch`.",
        "fuente": "aosp-mirror/platform_frameworks_base, rama main",
        "url_base": BASE,
        "verificado": verificado,
        "como_refrescar": "python3 scripts/simbolos_android.py",
        "clases": lanzan,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{SALIDA2.relative_to(RAIZ)}: {sum(len(v['metodos']) for v in lanzan.values())} "
          f"firmas en {len(lanzan)} clases")

    devuelven = {}
    for clase, (archivo, nombres) in DEVUELVE.items():
        metodos = metodos_que_devuelven(clase, archivo, nombres)
        devuelven[clase] = {"archivo": archivo, "metodos": metodos}
        print(f"  {clase}: {len(metodos)} retornos ({', '.join(f'{m}→{t[0]}' for m, t in metodos.items())})")
    SALIDA3.write_text(json.dumps({
        "que_es": "El tipo que **devuelve** cada método del SDK de Android que el Java del APK "
                  "recibe en una variable. `javac` rechaza un tipo equivocado en la asignación, "
                  "y aquí no hay `javac`: así que el retorno se copia de AOSP. Es la tercera "
                  "clase de error que sólo existe al compilar, después de las constantes "
                  "inventadas (`simbolos-android.json`), el `Pattern` pasado a `String.split` y "
                  "el `throws` sin recoger (`lanza-android.json`).",
        "fuente": "aosp-mirror/platform_frameworks_base, rama main",
        "url_base": BASE,
        "verificado": date.today().isoformat(),
        "como_refrescar": "python3 scripts/simbolos_android.py",
        "clases": devuelven,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{SALIDA3.relative_to(RAIZ)}: {sum(len(v['metodos']) for v in devuelven.values())} "
          f"retornos en {len(devuelven)} clases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
