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
esté en la lista de sueltas), y escribe el JSON con su marca de tiempo.

Uso — necesita red, y **no** forma parte de `make test`:

    python3 scripts/simbolos_android.py

Después de refrescarlo, `make test` es quien comprueba que el Java del APK siga
dentro del diccionario (`services/core/tests/test_apk_cerebro.py`).
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


def descargar(clase: str, ruta: str) -> list[str]:
    texto = urllib.request.urlopen(BASE + ruta, timeout=90).read().decode("utf-8", "replace")
    nombres = sorted(n for n in set(CONSTANTE.findall(texto))
                     if n.startswith(PREFIJOS) or n in SUELTAS)
    if not nombres:
        raise SystemExit(f"{clase}: ninguna constante encontrada — cambió la ruta en AOSP")
    return nombres


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
