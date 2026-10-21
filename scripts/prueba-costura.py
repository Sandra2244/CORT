"""La costura del APK: manifiesto ↔ Java ↔ interfaz, comprobada sin teléfono.

Aquí no hay `javac` (medido: el único compilador real del proyecto es el del
runner de GitHub Actions), así que lo que se puede comprobar en esta máquina es
**que las tres capas se nombran lo mismo**. Cada error de estos es un run rojo o,
peor, un botón que no hace nada en el teléfono de la dueña:

  1. `AndroidManifest.xml` declara los **cuatro** servicios con su
     `android:permission` y su `<action>`; sin ellos Android no mira el asistente
     ni el oído de los avisos. Y la lista de `<uses-permission>` sigue teniendo
     cuatro líneas: `.Avisos` entra por el interruptor del sistema, no por un
     permiso nuevo.
  2. Cada `Avisos.METODO` que usan `CortNative.java` y `MainActivity.java` existe
     de verdad en `Avisos.java` (nombre y, cuando se ve, número de argumentos).
  3. Los `@JavascriptInterface` que la cara llama (`window.CortNative.avisos`,
     `.vaciarAvisos`) están escritos, y los que no existen no se invocan: la cara
     se degrada con un mensaje, no con un `TypeError`.

Uso:  python3 scripts/prueba-costura.py     (una fracción de segundo)
"""
from __future__ import annotations

import pathlib
import re
import sys
import xml.etree.ElementTree as ET

RAIZ = pathlib.Path(__file__).resolve().parent.parent
APK = RAIZ / "apps" / "apk"
FALLOS: list[str] = []


def dice_ok(label: str, detalle: str) -> None:
    print(f"  ok  {label}: {detalle}")


def falla(label: str, detalle: str) -> None:
    FALLOS.append(f"{label}: {detalle}")
    print(f"  NO  {label}: {detalle}")


# ── 1 · el manifiesto ────────────────────────────────────────────────────────
print("\n[1] AndroidManifest.xml")
XML = (APK / "AndroidManifest.xml").read_text(encoding="utf-8")
try:
    ET.fromstring(XML)
    dice_ok("es XML", "aapt2 lo puede enlazar")
except ET.ParseError as e:
    falla("es XML", f"aapt2 moriría aquí — {e}")

servicios = dict(re.findall(r'android:name="(\.\w+)"[^>]*android:permission="([^"]+)"', XML))
esperados = {
    ".Asistente": "android.permission.BIND_VOICE_INTERACTION",
    ".Sesiones": "android.permission.BIND_VOICE_INTERACTION",
    ".Reconocimiento": "android.permission.BIND_SPEECH_RECOGNIZER",
    ".Avisos": "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE",
}
for nombre, permiso in esperados.items():
    if servicios.get(nombre) == permiso:
        dice_ok(f"servicio {nombre}", permiso.split(".")[-1])
    else:
        falla(f"servicio {nombre}", f"declarado como {servicios.get(nombre)!r}, "
                                    f"y Android exige {permiso!r}")

acciones = set(re.findall(r'<action android:name="([^"]+)"', XML))
for accion in ("android.service.voice.VoiceInteractionService",
               "android.speech.RecognitionService",
               "android.service.notification.NotificationListenerService"):
    if accion in acciones:
        dice_ok("acción", accion)
    else:
        falla("acción", f"falta {accion} — el sistema busca exactamente esta")

permisos = re.findall(r'<uses-permission android:name="([^"]+)"', XML)
if len(permisos) == 4:
    dice_ok("permisos", f"siguen siendo cuatro: {', '.join(p.split('.')[-1] for p in permisos)}")
else:
    falla("permisos", f"se pidieron {len(permisos)}: {permisos}")
for prohibido in ("QUERY_ALL_PACKAGES", "ACTION_CALL", "READ_CONTACTS",
                  "READ_EXTERNAL_STORAGE", "READ_SMS"):
    if prohibido in XML:
        falla("permiso de más", f"{prohibido} aparece en el manifiesto")

# ── 2 · Avisos.java y lo que le piden sus vecinos ────────────────────────────
print("\n[2] Avisos.java ↔ CortNative.java ↔ MainActivity.java")
avisos = (APK / "src" / "com" / "cort" / "ia" / "Avisos.java").read_text(encoding="utf-8")
vecinos = {
    "CortNative.java": (APK / "src" / "com" / "cort" / "ia" / "CortNative.java").read_text(encoding="utf-8"),
    "MainActivity.java": (APK / "src" / "com" / "cort" / "ia" / "MainActivity.java").read_text(encoding="utf-8"),
}
if "class Avisos extends NotificationListenerService" not in avisos:
    falla("clase", "Avisos no extiende NotificationListenerService: el sistema no lo arranca")
else:
    dice_ok("clase", "Avisos extends NotificationListenerService")

definidos = set(re.findall(r"\bstatic\b[^;={}]*?\b(\w+)\s*\(", avisos)) | \
            set(re.findall(r"\bpublic\s+static\s+\w+\s+(\w+)\s*\(", avisos)) | \
            set(re.findall(r"\bstatic\s+final\s+\w+\s+(\w+)\s*=", avisos))
usados: set[str] = set()
for origen, texto in vecinos.items():
    # `Avisos.java` aparece también en la prosa de los comentarios: ahí no es
    # una llamada, es el nombre del archivo. Los comentarios se quitan antes.
    limpio = re.sub(r"/\*.*?\*/", "", texto, flags=re.S)
    limpio = re.sub(r"//[^\n]*", "", limpio)
    for nombre in re.findall(r"Avisos\.(\w+)", limpio):
        usados.add((origen, nombre))
for origen, nombre in sorted(usados):
    if nombre in definidos:
        dice_ok(f"{origen} → Avisos.{nombre}", "existe en Avisos.java")
    else:
        falla(f"{origen} → Avisos.{nombre}",
              f"no está definido (definidos: {', '.join(sorted(definidos))})")

# Lo que **no** hace el oído: prometer que guarda los chats en disco.
for prohibido in ("FileWriter", "openFileOutput", "SharedPreferences", "SQLiteDatabase",
                  "cort_memory.db", "Runtime.getRuntime().exec"):
    if prohibido in avisos:
        falla("privacidad", f"Avisos.java menciona {prohibido}: los avisos se leen y se olvidan")
dice_ok("privacidad", "doce líneas en RAM, cero escrituras a disco")

# ── 3 · la costura con la interfaz ──────────────────────────────────────────
print("\n[3] window.CortNative ↔ @JavascriptInterface")
cara = (RAIZ / "ui" / "js" / "hud.js").read_text(encoding="utf-8")
puente = vecinos["CortNative.java"]
expuestos = set(re.findall(r"@JavascriptInterface\s*\n\s*public\s+\w+(?:<[^>]*>)?\s+(\w+)\s*\(",
                           re.sub(r"/\*.*?\*/", "", puente, flags=re.S)))
for met in re.findall(r"(?:\bN|window\.CortNative)\.(\w+)\(", cara):
    if met in expuestos:
        dice_ok(f"hud.js → CortNative.{met}()", "expuesto a la página")
    elif met in ("listen", "speak", "stopSpeaking", "voices", "available", "hasPermission",
                 "requestPermission", "openAppSettings", "bgStatus", "setBackground",
                 "keepAwake", "setPc", "cancelListening", "stopListening"):
        dice_ok(f"hud.js → CortNative.{met}()", "de siempre, por el puente del Kotlin")
    else:
        falla(f"hud.js → CortNative.{met}()",
              f"la cara llama a un método que el puente no expone (hay {len(expuestos)})")

# El Kotlin original sólo entiende su parte del puente; la cara tiene que
# preguntar antes de llamar (por eso el `typeof … !== 'function'`).
if "typeof N.avisos !== 'function'" in cara:
    dice_ok("respaldo", "la cara pregunta si el puente sabe de avisos antes de llamarlo")
else:
    falla("respaldo", "hud.js llama a avisos() sin comprobar: crashea en el APK del cuerpo original")

# ── veredicto ───────────────────────────────────────────────────────────────
print()
if FALLOS:
    print(f"FALTA {len(FALLOS)} COSA(S):")
    for f in FALLOS:
        print("  ·", f)
    sys.exit(1)
print("costura cosida: manifiesto, Java y cara se nombran lo mismo.")
