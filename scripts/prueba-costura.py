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
     `.vaciarAvisos`, `.assistantState`, `.openAssistantSettings`) están escritos, y
     los que no existen en el cuerpo Kotlin del APK del teléfono no se invocan sin
     su `typeof`: la cara se degrada con un mensaje, no con un `TypeError`.
  4. El **traje de asistente**, que es lo que «no sale en la lista»: el nodo
     `voice-interaction-service` con sus dos servicios existentes, **sin**
     `settingsActivity` (AOSP descarta a una app que no sea del sistema si la
     declara), el `RoleManager.ROLE_ASSISTANT` con su guard de API 29, y el
     `pause`/`resume` que evita que el micro quede abierto en segundo plano.

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

# Los métodos NUEVOS del puente (asistente, música) tampoco existen en el cuerpo
# Kotlin del APK del teléfono: cada uno tiene que ir precedido de su `typeof`.
for met in ("openAssistantSettings", "assistantState", "vaciarAvisos"):
    if met in expuestos and re.search(r"typeof N\." + met + r"\s*[!=]==?\s*'function'", cara):
        dice_ok(f"respaldo {met}", "la cara pregunta antes de llamar")
    elif met in expuestos:
        falla(f"respaldo {met}", f"hud.js llama a {met}() sin `typeof`:TypeError en el cuerpo Kotlin")

voz = (RAIZ / "ui" / "js" / "voice.js").read_text(encoding="utf-8")
if re.search(r"typeof N\.musicPlaying\s*[!=]==?\s*'function'", voz):
    dice_ok("respaldo musicPlaying", "voice.js pregunta si el puente sabe si hay música")
else:
    falla("respaldo musicPlaying", "voice.js llama a musicPlaying() sin comprobar su existencia")
if "musicPlaying" in expuestos:
    dice_ok("CortNative.musicPlaying()", "el puente del APK lo expone")
else:
    falla("CortNative.musicPlaying()", "no está marcado @JavascriptInterface: el freno de música no funciona")

# ── 4 · el traje de asistente, que es lo que «no sale en la lista» ───────────
print("\n[4] res/xml/asistente.xml ↔ RoleManager ↔ pausa/reanuda")
ASIS = (APK / "res" / "xml" / "asistente.xml").read_text(encoding="utf-8")
try:
    ET.fromstring(ASIS)
    dice_ok("es XML", "el sistema lo puede parsear")
except ET.ParseError as e:
    falla("es XML", f"Android descartaría al asistente — {e}")

nodo = re.search(r"<voice-interaction-service[^>]*>", ASIS, flags=re.S)
if not nodo:
    falla("nodo", "no hay <voice-interaction-service>: sin esto CORT no aparece NUNCA")
else:
    atrib = dict(re.findall(r'(\w+)\s*=\s*"([^"]+)"', nodo.group(0)))
    for key in ("sessionService", "recognitionService"):
        valor = atrib.get(key)
        if not valor:
            falla(key, "el parser de AOSP exige el atributo y se queda sin asistente")
            continue
        archivo = APK / "src" / (valor.replace("com.cort.ia.", "").replace(".", "/") + ".java")
        if not archivo.exists() and not (APK / "src" / "com" / "cort" / "ia" / (valor.split(".")[-1] + ".java")).exists():
            falla(key, f"apunta a {valor}, que no existe como archivo Java")
        else:
            dice_ok(key, valor.split(".")[-1] + ".java")
    # LA REGLA QUE CUESTA APARECER: `VoiceInteractionServiceInfo` rechaza una
    # `settingsActivity` que no sea de una app del sistema (`FLAG_SYSTEM`), y una
    # APK instalada a mano nunca lo es. Con el atributo puesto, CORT desaparece de
    # la lista de asistentes **sin ningún aviso en pantalla**. Se mira el **nodo**,
    # no el archivo entero: la prosa que explica la regla también nombra el atributo.
    if atrib.get("settingsActivity"):
        falla("settingsActivity",
              f"declarada ({atrib['settingsActivity']}) en el nodo: para una APK "
              "sideloaded Android tira el parseo y CORT no sale en la lista de asistentes")
    else:
        dice_ok("settingsActivity", "ausente a propósito; los ajustes se piden por RoleManager")

main = vecinos["MainActivity.java"]
if "ROLE_ASSISTANT" in main and "createRequestRoleIntent" in main:
    dice_ok("RoleManager", "el botón pide el rol de asistente (API 29+)")
else:
    falla("RoleManager", "MainActivity no usa createRequestRoleIntent(ROLE_ASSISTANT): "
                         "el diálogo moderno de Android no se abre")
if "SDK_INT >= 29" in main:
    dice_ok("SDK_INT", "comprobada la versión antes de tocar RoleManager (minSdk 26)")
else:
    falla("SDK_INT", "falta el guard de API 29: el puente reventaría en Android 8/9")

puente_txt = re.sub(r"/\*.*?\*/", "", puente).replace('\\"', '"')
# El micro en segundo plano: Java cierra el reconocedor, pero la cara sólo deja de
# reabrirlo si recibe el aviso. Sin `pause` el teléfono se queda con el micro
# abierto en bucle detrás de la app —el «traba» que la dueña nota al optimizar o
# al escuchar música.
if '{"type":"pause"}' in puente_txt and "cuadro" in puente_txt.split("void pausa")[1][:200]:
    dice_ok("pausa()", "avisa a la cara antes de cerrar el reconocedor")
else:
    falla("pausa()", "no emite el evento `pause`: voice.js reabre el micro en segundo plano")
if '{"type":"resume"}' in puente_txt and "void reanuda" in puente_txt:
    dice_ok("reanuda()", "devuelve el oído al volver la app al frente")
else:
    falla("reanuda()", "falta el método que manda `resume`: CORT se queda muda al volver")
if "puente.reanuda()" in main:
    dice_ok("onResume", "MainActivity avisa al puente cuando la cara vuelve")
else:
    falla("onResume", "nadie llama a reanuda(): el oído no vuelve nunca")

for patron, etiqueta in ((r"case 'pause'", "pause"), (r"case 'resume'", "resume")):
    if re.search(patron, voz):
        dice_ok(f"voice.js {etiqueta}", "el evento tiene su rama")
    else:
        falla(f"voice.js {etiqueta}", "Java manda el evento y la cara lo ignora")
if "motivoFreno" in voz and "enPausa" in voz:
    dice_ok("freno del oído", "la escucha no se rearma con la app parada o con música")
else:
    falla("freno del oído", "voice.js no comprueba el freno antes de reabrir el micro")
if re.search(r"scheduleWake\([^)]*\)\s*;\s*\n\s*return", voz) or "if (motivoFreno())" in voz:
    dice_ok("retroceso", "con el freno puesto se reintenta suave en vez de abrir el micro")
else:
    falla("retroceso", "scheduleWake no respeta el freno")

# ── veredicto ───────────────────────────────────────────────────────────────
print()
if FALLOS:
    print(f"FALTA {len(FALLOS)} COSA(S):")
    for f in FALLOS:
        print("  ·", f)
    sys.exit(1)
print("costura cosida: manifiesto, Java y cara se nombran lo mismo.")
