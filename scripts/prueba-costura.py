"""La costura del APK: manifiesto ↔ Java ↔ interfaz, comprobada sin teléfono.

Aquí no hay `javac` (medido: el único compilador real del proyecto es el del
runner de GitHub Actions), así que lo que se puede comprobar en esta máquina es
**que las tres capas se nombran lo mismo**. Cada error de estos es un run rojo o,
peor, un botón que no hace nada en el teléfono de la dueña:

  1. `AndroidManifest.xml` declara los **cuatro** servicios con su
     `android:permission` y su `<action>`; sin ellos Android no mira el asistente
     ni el oído de los avisos. Y el quinto (`.Reproductor`) con su
     `foregroundServiceType`, que Android 14 exige para que la música suene con la
     cara cerrada. La lista de `<uses-permission>` se comprueba por conjunto: están
     los que justifican las funciones (música, archivos, marcar, notificaciones) y
     no se ha colado ninguno desproporcionado (`READ_SMS`, `QUERY_ALL_PACKAGES`…).
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
  5. El reproductor, la música y el teléfono (`Reproductor.java`, `Musica.java`,
     `Telefono.java`) están enganchados al puente con los métodos de verdad.
  6. Cada pantalla que ofrece la cara tiene su ventana en el HUD y su puerta en el
     núcleo, o dice que no la hay.
  7. El SDK: ningún símbolo que `javac --release 11` o `d8` rechacen, nada de
     AndroidX en un proyecto que compila con `aapt2`.
  8. La ronda 2.0.0 (MV, modo juego, organizador, letras) sigue cosida después de
     los cambios de la 2.1.
  9. La ronda 2.1 entera, medida en **cuatro sitios a la vez** (`docs/CONTRATO-PUENTE-2.1.md`
     es la única fuente de los nombres): la clase existe, el puente expone
     `@JavascriptInterface` con ese `que`, la cara lo llama, y el manifiesto o el
     backend ponen su mitad — `accion`, `ajusteVoz`, `memoria`, `mente`, `atuendo`,
     `agenda`, `burbuja`, `comparte`. Aquí caen los bugs que en Java son silenciosos:
     un evento que Java emite con un nombre y la cara escucha con otro, un
     `<queries>` a medias, `assets/habilidades.json` vacío, una `/api/*` que el
     portátil no tiene, o —que pasó de verdad— un panel entero (`bgStatus()` de
     07 · Perfil) al que la cara le pregunta siete claves y Java sólo le devolvía
     dos.

Uso:  python3 scripts/prueba-costura.py     (una fracción de segundo)
"""
from __future__ import annotations

import ast
import pathlib
import re
import subprocess
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


def puente_texto() -> str:
    """El puente como texto, para las comprobaciones que lo necesitan antes de sector [8]."""
    return (APK / "src" / "com" / "cort" / "ia" / "CortNative.java").read_text(encoding="utf-8")


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
# Con UN solo APK (el de Java) la lista de permisos ya no son cuatro: el
# reproductor, los contactos y «ordena mis archivos» piden los suyos. Se comprueba
# el conjunto **necesario** y que no se cuele ninguno **desproporcionado**.
cortos = {p.rsplit(".", 1)[-1] for p in permisos}
necesarios = {
    "INTERNET", "RECORD_AUDIO", "MODIFY_AUDIO_SETTINGS", "VIBRATE",
    "READ_MEDIA_AUDIO", "READ_MEDIA_VIDEO", "READ_EXTERNAL_STORAGE",
    "FOREGROUND_SERVICE", "FOREGROUND_SERVICE_MEDIA_PLAYBACK", "WAKE_LOCK",
    "POST_NOTIFICATIONS", "READ_CONTACTS", "CALL_PHONE",
    # Los cuatro de la ronda 2.1, cada uno con su función nombrada abajo: la cámara
    # es la linterna (`Acciones`), `SET_ALARM` el despertador que CORT pone desde la
    # voz, `READ_CALENDAR` el «¿qué tengo hoy?» (`Agenda`) y el superposición el
    # punto flotante (`Flotante`). Con `READ_CALENDAR` sólo de lectura: apuntar una
    # cita abre el formulario y lo guarda su dedo.
    "CAMERA", "SET_ALARM", "READ_CALENDAR",
    "SYSTEM_ALERT_WINDOW",
}
if necesarios <= cortos:
    dice_ok("permisos", f"{len(permisos)} declarados, los {len(necesarios)} justos están")
else:
    falla("permisos", f"faltan {', '.join(sorted(necesarios - cortos))}")
for prohibido in ("QUERY_ALL_PACKAGES", "READ_SMS", "SEND_SMS", "RECEIVE_MMS",
                  "READ_CALL_LOG", "PROCESS_OUTGOING_CALLS",
                  "GET_ACCOUNTS", "MASTER_ACCOUNT", "WRITE_SECURE_SETTINGS"):
    if prohibido in cortos:
        falla("permiso de más", f"{prohibido}: no hace falta para lo que CORT promete")
# `SYSTEM_ALERT_WINDOW` estaba en la lista de arriba y aquí tiene su propia regla,
# porque la **burbuja flotante** (contrato 2.1, sector [6]) no existe sin él: es el
# punto de CORT que abre el micrófono sin sacar de la partida. Es un permiso de
# interruptor en Ajustes, no de cuadro, y sólo se concede si la dueña lo da. La
# comprobación, entonces, no es «no está» sino «si está, es porque hay función que
# lo usa y pantalla donde darlo»: un permiso sin dueño es exactamente el tipo de
# cosa que la dueña rechazó del APK original.
if "SYSTEM_ALERT_WINDOW" in cortos:
    flotante = APK / "src" / "com" / "cort" / "ia" / "Flotante.java"
    if not flotante.is_file():
        falla("permiso de más", "SYSTEM_ALERT_WINDOW declarado sin Flotante.java: "
                                "un permiso que no usa nadie")
    elif "ACTION_MANAGE_OVERLAY_PERMISSION" not in puente_texto():
        falla("permiso de más", "SYSTEM_ALERT_WINDOW sin pantalla donde la dueña lo dé "
                                "(`abreAjustesBurbuja`)")
    else:
        dice_ok("permiso de la burbuja", "SYSTEM_ALERT_WINDOW con su clase y su pantalla "
                                         "de Ajustes: se da a mano y se puede quitar")
elif (APK / "src" / "com" / "cort" / "ia" / "Flotante.java").is_file():
    falla("burbuja", "Flotante.java existe pero el manifiesto no declara "
                     "SYSTEM_ALERT_WINDOW: el punto nunca aparecería")
if 'android:foregroundServiceType="mediaPlayback"' in XML:
    dice_ok("servicio de música", "declarado con su tipo, como exige Android 14")
else:
    falla("servicio de música", "falta `.Reproductor` con `foregroundServiceType=\"mediaPlayback\"`")
if 'android:roundIcon="@mipmap/ic_launcher_round"' in XML:
    dice_ok("icono", "el manifiesto pide el anillo (los PNG los saca compilar.sh del base APK)")
else:
    falla("icono", "el manifiesto no declara `roundIcon`: el cajón mostraría el genérico")

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

# ── 5 · el reproductor y los contactos: las clases nuevas se nombran ─────────
print("\n[5] Reproductor.java / Musica.java / Telefono.java ↔ el puente")

def metodos_de(texto: str) -> set[str]:
    """Nombres de método declarados a cuatro espacios (o en una línea con `{`)."""
    limpio = re.sub(r"/\*.*?\*/", "", texto, flags=re.S)
    limpio = re.sub(r"//[^\n]*", "", limpio)
    sale: set[str] = set()
    for linea in limpio.splitlines():
        l = linea.strip()
        if not linea.startswith("    ") or not l:
            continue
        if l.split(" ")[0] in ("return", "if", "for", "while", "switch", "catch", "else"):
            continue
        for m in (re.match(r"^(?:(?:public|private|protected|static|final|synchronized)\s+)*"
                           r"[A-Za-z_][\w<>\[\], .]*\s+(\w+)\s*\(", l),
                  re.match(r"^(?:(?:public|private|protected|static|final|synchronized)\s+)*"
                           r"[A-Za-z_][\w<>\[\], .]*\s+(\w+)\s*\([^)]*\)\s*\{", l)):
            if m and m.group(1) not in ("new", "class", "int", "String"):
                sale.add(m.group(1))
    return sale

usa = {
    "CortNative.java": vecinos["CortNative.java"],
    "MainActivity.java": vecinos["MainActivity.java"],
    "Reproductor.java": (APK / "src" / "com" / "cort" / "ia" / "Reproductor.java").read_text(encoding="utf-8"),
}
for nombre_carpeta in ("Reproductor", "Musica", "Telefono"):
    ruta = APK / "src" / "com" / "cort" / "ia" / f"{nombre_carpeta}.java"
    if not ruta.exists():
        falla(f"{nombre_carpeta}.java", "no existe: `compilar.sh` no tendría nada que compilar")
        continue
    definidos = metodos_de(ruta.read_text(encoding="utf-8"))
    llamados: set[tuple[str, str]] = set()
    para, origen = re.compile(rf"\b{nombre_carpeta}\.(\w+)\s*\("), None
    for quien, texto in usa.items():
        limpio = re.sub(r"/\*.*?\*/", "", texto, flags=re.S)
        limpio = re.sub(r"//[^\n]*", "", limpio)
        for met in para.findall(limpio):
            llamados.add((quien, met))
    roto = [f"{quien} → {nombre_carpeta}.{met}()" for quien, met in sorted(llamados)
            if met not in definidos and met[0].islower()]
    if roto:
        for r in roto:
            falla("costura", f"{r} no está definido en {nombre_carpeta}.java "
                             f"(hay {len(definidos)} métodos)")
    else:
        dice_ok(f"{nombre_carpeta}.java", f"{len(llamados)} llamadas, todas definidas")

# El aviso del reproductor al puente: `Reproductor.avisa()` llama a
# `MainActivity.front().puente().musicaCambio()`, y ése tiene que existir y emitir
# el evento `music` que la cara escucha. Sin él, los botones de play se quedan con
# la barra quieta.
if "musicaCambio" in usa["Reproductor.java"]:
    if "void musicaCambio" in puente_txt and '"type":"music"' in puente_txt:
        dice_ok("evento music", "el puente avisa a la cara en cada play, pausa y canción nueva")
    else:
        falla("evento music", "Reproductor pide aviso pero CortNative no emite `music`")
if "static MainActivity front()" in main and "CortNative puente()" in main:
    dice_ok("MainActivity.front()", "el servicio puede hablar con la cara aunque esté en otro hilo")
else:
    falla("MainActivity.front()", "falta el acceso estático: Reproductor no tiene cómo avisar")

# Los tres casos nuevos del menú de Java tienen su método en el puente.
for met in re.findall(r"puente\.(\w+)\(\)", main):
    if met in metodos_de(puente):
        dice_ok(f"menú → puente.{met}()", "existe")
    else:
        falla(f"menú → puente.{met}()", "el menú llama a un método que CortNative no tiene")

# Y el número de versión del APK: `build.yml` Bautiza el artefacto con el suyo,
# `compilar.sh` pone el `versionName`. Si se separan, la Release sale con un APK
# que no se llama como el enlace que anuncia.
yml = (RAIZ / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
en_yml = re.search(r'APK_VERSION:\s*"([\d.]+)"', yml)
en_sh = re.search(r'APK_VERSION="\$\{APK_VERSION:-([\d.]+)\}"',
                  (APK / "compilar.sh").read_text(encoding="utf-8"))
if en_yml and en_sh and en_yml.group(1) == en_sh.group(1):
    dice_ok("versión del APK", en_yml.group(1) + " en los dos lados")
else:
    falla("versión del APK", f"build.yml dice {en_yml and en_yml.group(1)!r} y "
                             f"compilar.sh {en_sh and en_sh.group(1)!r}")
if "rempaquetar" in yml and "Rempaquetar el APK" in yml:
    falla("un solo APK", "build.yml sigue montando el paso de rempaquetar: "
                         "la dueña volvería a tener dos APK que elegir")
else:
    dice_ok("un solo APK", "no hay paso de rempaquetar: sale uno, el de Java")

# ── 6 · las pantallas nuevas: que la cara no llame a lo que no existe ────────
# `ui/js/pantallas.js` es capa nueva encima de las tres de antes: habla con el
# puente de Java (`llama('musicaPoner', …)`), con el núcleo de PC
# (`fetch(ctx.api() + '/api/chat')`) y con `hud.js` (que tiene que montarla y
# escuchar su voz). Cada nombre mal escrito es un botón que no hace nada, y en el
# teléfono no hay consola donde verlo: se comprueba aquí.
print("\n[6] las pantallas (cara ↔ puente ↔ núcleo)")
scr_txt = (RAIZ / "ui" / "js" / "pantallas.js").read_text(encoding="utf-8")
hud_txt = (RAIZ / "ui" / "js" / "hud.js").read_text(encoding="utf-8")

# 6.a · los métodos del puente que usan las pantallas tienen que estar en CortNative
puente_metodos = metodos_de(puente)
llamadas = set(re.findall(r"llama\(\s*'(\w+)'", scr_txt))
# `hud.js` también habla con el puente a pelo (`window.CortNative.musicaPausa()`),
# y son órdenes de voz: si el nombre está mal escrito, «pausa la música» no hace nada.
llamadas |= set(re.findall(r"CortNative\.(\w+)\s*\(", hud_txt))
llamadas |= set(re.findall(r"\bN\.(\w+)\s*\(", hud_txt))
hueros = sorted(m for m in llamadas if m not in puente_metodos)
if hueros:
    falla("puente", "la cara pide " + ", ".join(f"CortNative.{m}()" for m in hueros)
                  + " y CortNative.java no lo tiene")
else:
    dice_ok("puente", f"{len(llamadas)} métodos llamados desde las pantallas y la voz, "
                      f"todos en CortNative.java")

# 6.b · y las rutas del núcleo existen de verdad en el backend
backend = "\n".join(p.read_text(encoding="utf-8", errors="ignore")
                    for p in (RAIZ / "backend" / "app").rglob("*.py"))
rutas = sorted(set(re.findall(r"fetch\(ctx\.api\(\)\s*\+\s*'(/api/\w+)", scr_txt))
               | set(re.findall(r"fetch\((?:base|ctx\?\.api\(\))\s*\+\s*'(/api/\w+)", scr_txt)))
sin_backend = [r for r in rutas if f'"{r}"' not in backend and f"'{r}'" not in backend]
if sin_backend:
    falla("núcleo", "pantallas.js llama a " + ", ".join(sin_backend)
                  + " y el backend no tiene esa ruta (inventada)")
else:
    dice_ok("núcleo", ", ".join(rutas) + " — todas existen en backend/app")

# 6.c · hud.js tiene que montarlas y cederles la voz; si no, son código muerto
if re.search(r"import\s*\{[^}]*\binitPantallas\b[^}]*\}\s*from\s*'\./pantallas\.js'", hud_txt) \
        and "initPantallas({" in hud_txt and "porVoz(msg)" in hud_txt:
    dice_ok("montaje", "hud.js importa initPantallas, la llama y le pasa la voz con porVoz()")
else:
    falla("montaje", "hud.js no importa o no llama a initPantallas/porVoz: "
                     "las pantallas serían código muerto y no aparecería la barra ☰")

# 6.d · CSS: nada de pantalla en negro si el módulo falla. Las reglas que tapan el
# orbe cuelgan de `.pantallas-montadas`, la clase que se pone AL FINAL del montaje.
css_txt = (RAIZ / "ui" / "css" / "hud.css").read_text(encoding="utf-8")
ciegas = re.findall(r"html:not\(\.p-orbe\)\s+#[\w-]+\{display:none", css_txt)
if ciegas:
    falla("css", f"{len(ciegas)} regla(s) que ocultan el HUD sin comprobar que las "
                 f"pantallas se montaron: si el módulo falla, la pantalla queda en negro")
elif "#scene" in css_txt and "pantallas-montadas" in css_txt:
    dice_ok("css", "el orbe sólo se apaga cuando `pantallas-montadas` existe: un fallo "
                   "del módulo deja la interfaz de siempre intacta")
else:
    falla("css", "no se encuentra la regla que apaga el orbe en las otras pantallas")

# 6.e · el evento que el puente emite y la cara escucha tienen que llamarse igual
if re.search(r"__cortNative\.on", scr_txt) and re.search(r"type\s*[!=]==\s*'music'", scr_txt):
    dice_ok("evento music en la cara", "pantallas.js pinta la barra desde el evento, sin martillar al puente")
else:
    falla("evento music en la cara", "la pantalla de música no escucha `music`: la barra no avanzaría")

# ── 7 · el SDK de verdad: nada oculto, nada de AndroidX ─────────────────────
# Aquí no hay `javac` (el portátil de la dueña lo comprobó: no está) y el APK se
# compila en Actions. El precio de no poder compilar es escribir un símbolo que
# el `android.jar` del runner rechaza. `v0.2.11-demo` cayó así, con 14 errores y
# todos en `Reproductor.java`: `android.media.MediaSession` existe pero es
# `@hide` (el público es `android.media.session.MediaSession`),
# `MediaStyle.fromSession()` es de marco interno, y `METADATA_KEY_MEDIA_TYPE` con
# sus `MEDIA_TYPE_MOVIE`/`MEDIA_TYPE_MUSIC` son de AndroidX
# (`MediaMetadataCompat`), que este proyecto no usa. Se comprueba aquí, leyendo el
# código **sin comentarios ni literales**, para que un aviso que explique el error
# no vuelva a parecer el error.
print("\n[7] el SDK: símbolos ocultos o de AndroidX")

def sin_comentarios(txt: str) -> str:
    """Queda sólo código: fuera comentarios y literales de texto/carácter."""
    salida, i, n = [], 0, len(txt)
    while i < n:
        ch = txt[i]
        if ch == '"' or ch == "'":
            cierre = ch; i += 1
            while i < n:
                if txt[i] == "\\": i += 2; continue
                if txt[i] == cierre: i += 1; break
                i += 1
            continue
        if txt.startswith("//", i):
            j = txt.find("\n", i); i = n if j < 0 else j; continue
        if txt.startswith("/*", i):
            j = txt.find("*/", i + 2); i = n if j < 0 else j + 2; continue
        salida.append(ch); i += 1
    return "".join(salida)


def literales(txt: str) -> str:
    """Al revés que `sin_comentarios`: SOLO el contenido de los literales de texto.

    Lo que el puente y la cara se dicen vive dentro de comillas
    (`"{\"type\":\"auricular\"…}"`, `b + "/api/memories"`), y los comentarios
    documentan también lo que NO existe («la puerta `/api/memoria` del encargo no
    existe»). Comparar contra el archivo entero es encontrar lo que el propio
    comentario niega, y el rojo sale del revés.

    El contenido se suelta de sus escapes (`\"` → `"`) y se vuelve a entrecomillar,
    para que sirvan las dos formas de buscar: `"mente"` como cadena suelta del puente
    y `"type":"auricular"` dentro del JSON que Java arma a mano.
    """
    salida, i, n = [], 0, len(txt)
    while i < n:
        ch = txt[i]
        if ch == '"':
            j = i + 1
            while j < n:
                if txt[j] == "\\": j += 2; continue
                if txt[j] == '"': break
                j += 1
            dentro = re.sub(r'\\(.)', r'\1', txt[i + 1:j])
            salida.append('"' + dentro + '"'); i = j + 1; continue
        if txt.startswith("//", i):
            k = txt.find("\n", i); i = n if k < 0 else k; continue
        if txt.startswith("/*", i):
            k = txt.find("*/", i + 2); i = n if k < 0 else k + 2; continue
        i += 1
    return " ".join(salida)

PROHIBIDOS = [
    ("android.media.MediaSession",
     "es @hide; el público es android.media.session.MediaSession (el mismo de MainActivity)"),
    ("MediaStyle.fromSession",
     "es de marco interno; lo público es new Notification.MediaStyle().setMediaSession(sesion.getSessionToken())"),
    ("METADATA_KEY_MEDIA_TYPE",
     "es de androidx MediaMetadataCompat, no de android.media.MediaMetadata"),
    ("MEDIA_TYPE_MOVIE", "tampoco está en android.media.MediaMetadata"),
    ("MEDIA_TYPE_MUSIC", "tampoco está en android.media.MediaMetadata"),
    ("androidx.", "este APK se compila sin AndroidX: el runner no tiene esas clases"),
    # Los tres últimos, medidos por `javac` en el run rojo de `v0.2.14-demo`
    # (39668659120). Ninguno está en la lista pública del SDK 34, y los tres
    # parecían obvios: son API que uno «recuerda» haber usado.
    ("android.content.FileProvider",
     "no existe: `javac` dijo «cannot find symbol: class FileProvider». Lo del "
     "framework es la clase base, `android.content.ContentProvider`, y sobre ella "
     "está escrito `ArchivosProvider` (AndroidX queda fuera del proyecto)"),
    ("isDefault()",
     "sólo la trae `Voice.Style`; `android.speech.tts.Voice` no la tiene. La voz "
     "por defecto se pide al motor con `TextToSpeech.getDefaultVoice()` y se "
     "compara por nombre"),
    ("isMusicMute",
     "es `@SystemApi` y `javac` la rechaza aunque el teléfono la tenga. Silencio "
     "medido con API pública: `nivel(audio) == 0`"),
    # Las dos últimas, medida por `javac` en el run rojo de `v0.2.17-demo`
    # (39685806249) — el primer run que llevaba ya `Aparato` y `Sentidos` dentro.
    (".isLowMemory(",
     "`ActivityManager` no tiene ese método; lo público es el campo `lowMemory` de "
     "`ActivityManager.MemoryInfo`, que rellena `getMemoryInfo(m)`"),
    (".getResource()",
     "en `android.webkit.PermissionRequest` el método es `getResources()` (plural, "
     "devuelve `String[]`); el singular se lo inventó quien escribió la línea y "
     "`javac` lo paró"),
    # La última, medida por `javac` en el run rojo de `v0.2.32-demo` (39902845281,
    # 2026-10-23): F10 pedía la letra incrustada al índice creyendo que MediaStore
    # guarda la etiqueta ID3 de siempre. No la guarda como columna.
    ("Media.LYRICS",
     "`MediaStore.Audio.Media` **no tiene columna `LYRICS`**: `javac` dijo «cannot "
     "find symbol: variable LYRICS, location: class Media» y cerró el APK entero. "
     "La letra se mira en el archivo hermano (`.lrc` / `.txt`), que es lo que Lark "
     "lee y lo que CORT puede comprobar sin decodificar"),
]
cazas = []
java_limpio = {}
for p in sorted((RAIZ / "apps" / "apk" / "src" / "com" / "cort" / "ia").glob("*.java")):
    java_limpio[p.name] = sin_comentarios(p.read_text(encoding="utf-8"))
for nombre, motivo in PROHIBIDOS:
    culpables = [f"{archivo}:{linea}" for archivo, codigo in java_limpio.items()
                 for linea, texto in enumerate(codigo.splitlines(), 1)
                 if nombre in texto]
    if culpables:
        cazas.append(f"{nombre} ({motivo}) en {', '.join(culpables[:4])}")
if cazas:
    falla("SDK", "; ".join(cazas))
else:
    dice_ok("SDK", f"{len(java_limpio)} archivos Java sin símbolos ocultos ni de AndroidX")

# Y en positivo: la notificación tiene que colgar del Token de la sesión, que es
# lo que hace que el auricular y la pantalla de bloqueo obedezcan.
rep = java_limpio.get("Reproductor.java", "")
if "setMediaSession(" in rep and "getSessionToken()" in rep:
    dice_ok("MediaStyle", "la notificación usa setMediaSession(sesion.getSessionToken())")
else:
    falla("MediaStyle", "Reproductor.java no enlaza su notificación con el Token de la sesión: "
                        "los botones de la barra y del bloqueo no mandarían nada")

# El máscara de acciones de PlaybackState es de 64 bits: pasarla `int` deja a
# javac sin sobrecarga válida de setState (error medido en v0.2.11-demo).
if re.search(r"long\s+ACCIONES\s*=", rep):
    dice_ok("PlaybackState", "la máscara de acciones es `long`, como pide setState(…)")
elif "ACTION_PLAY" in rep:
    falla("PlaybackState", "la máscara de acciones de PlaybackState no se declara como `long`: "
                           "setState(…) no encuentra sobrecarga")

# ── 8 · la ronda 2.0.0: MV, modo juego, organizador y letras ─────────────────
# Cuatro funciones nuevas que se pueden romper sin que ningún compilador se entere:
# una hoja que está escrita pero nunca se monta, un `<video>` al que el WebView no
# deja entrar, un interruptor que no llega a Java o un organizador que un día
# alguien «mejora» borrando. Cada comprobación es una duda, no diez.
print("\n[8] la ronda 2.0.0 (MV · modo juego · organizador · letras)")

lectura = lambda *p: (RAIZ.joinpath(*p)).read_text(encoding="utf-8")
cara = lectura("ui", "js", "pantallas.js")
hud = lectura("ui", "js", "hud.js")
css = lectura("ui", "css", "hud.css")

# 8.a · la hoja MV existe de arriba abajo: menú, montaje, CSS y el `<video>`.
for etiqueta, condicion in (
        ("está en PANTALLAS", re.search(r"\{\s*id:\s*'mv'", cara)),
        ("se monta",          "montaMV()" in cara),
        ("su cuerpo se pinta", "montaMV" in cara and "mv-video" in cara),
        ("el CSS la enseña",  re.search(r"html\.p-mv #scr-mv", css))):
    if condicion:
        dice_ok("MV", f"la hoja {etiqueta}")
    else:
        falla("MV", f"la hoja {etiqueta}: la pantalla pediría «abre el mv» y no saldría nada")

# 8.b · el `<video>` de MV apunta a una `content://` del MediaStore: sin acceso a
# contenido del WebView, la imagen no abre nunca y el aviso honesto no lo arregla.
main_java = lectura("apps", "apk", "src", "com", "cort", "ia", "MainActivity.java")
if "setAllowContentAccess(true)" in main_java:
    dice_ok("MV · contenido", "el WebView tiene setAllowContentAccess(true): lee las content:// del índice")
else:
    falla("MV · contenido", "falta setAllowContentAccess(true) en MainActivity: ningún <video> "
                           "reproduciría una URI content:// del MediaStore")

# 8.c · el contrato de estado: la cara lee `uri`, `video` y `juego` de una sola vez.
# En Java las claves van ESCAPADAS dentro del literal (`\"uri\"`), así que buscar
# `"uri"` a pelo no encuentra nada: se busca la forma con barra inclinada.
rep_crudo = (RAIZ / "apps" / "apk" / "src" / "com" / "cort" / "ia" / "Reproductor.java").read_text(encoding="utf-8")
inicio = rep_crudo.find("String estadoJson(")
trozo = rep_crudo[inicio:inicio + 1600] if inicio >= 0 else ""
faltan = [k for k in ("uri", "video", "juego", "pista") if f'\\"{k}\\"' not in trozo]
if not trozo:
    falla("estadoJson", "Reproductor.java no define `String estadoJson(`: la cara no tiene "
                        "de dónde leer ni la URI del vídeo ni el estado del modo juego")
elif faltan:
    falla("estadoJson", f"no mete {', '.join(faltan)} en el JSON: la cara no puede pintar MV ni el "
                        "interruptor de juego sin preguntar dos veces")
else:
    dice_ok("estadoJson", "uri, video, juego y pista salen en la misma lectura del puente")

# 8.d · el modo juego: existe en Java, la cara lo llama con guardia, y el manifiesto
# NO trae espionaje (la dueña rechazó `PACKAGE_USAGE_STATS` y `QUERY_ALL_PACKAGES`).
puente = lectura("apps", "apk", "src", "com", "cort", "ia", "CortNative.java")
if "@JavascriptInterface" in puente and re.search(r"modoJuego\s*\(", puente):
    dice_ok("modo juego", "CortNative expone modoJuego(...)")
else:
    falla("modo juego", "CortNative.java no expone modoJuego: el botón diría «puesto» y Java seguiría escuchando")
if re.search(r"llama\('modoJuego'", cara):
    dice_ok("modo juego · cara", "la cara lo llama con `llama(…)`, así que un APK viejo no revienta")
else:
    falla("modo juego · cara", "la cara invoca modoJuego sin pasar por `llama(…)` o no lo invoca")
manifiesto = lectura("apps", "apk", "AndroidManifest.xml")
# Se comprueba la **declaración**, no el texto del manifiesto: la cabecera de
# `AndroidManifest.xml` explica nombre por nombre lo que la dueña rechazó y lo que
# este APK NO pide. Buscar en el archivo entero convertía esa explicación en un
# fallo — y un fallo así enseña a borrar la advertencia, que es lo contrario de lo
# que advierte.
rechazados = ("PACKAGE_USAGE_STATS", "QUERY_ALL_PACKAGES", "READ_SMS", "PROCESS_OUTGOING_CALLS")
colados = [p for p in rechazados if p in cortos]
if colados:
    falla("modo juego · permisos", f"se han colado permisos que la dueña no quiere: {', '.join(colados)}")
else:
    dice_ok("modo juego · permisos", "sin PACKAGE_USAGE_STATS ni QUERY_ALL_PACKAGES: es un interruptor, no un detector")

# 8.e · el organizador no borra. Es la promesa que se le hizo a la dueña: «mover, y
# sólo después de ver el plan». Si alguien añade un `remove`, esto tiene que rugir.
# Se mira SÓLO el código: el propio módulo documenta que no borra, y esa frase no
# puede ser la que rompa la prueba (`#` y docstrings fuera, como en [7] con Java).
def codigo_python(txt: str) -> str:
    salida, i, n = [], 0, len(txt)
    while i < n:
        ch = txt[i]
        if txt.startswith('"""', i) or txt.startswith("'''", i):
            marca = txt[i:i + 3]
            j = txt.find(marca, i + 3)
            i = n if j < 0 else j + 3
            continue
        if ch == "#":
            j = txt.find("\n", i)
            i = n if j < 0 else j
            continue
        if ch in "\"'":
            cierre, i = ch, i + 1
            while i < n:
                if txt[i] == "\\":
                    i += 2
                    continue
                if txt[i] == cierre:
                    i += 1
                    break
                i += 1
            continue
        salida.append(ch)
        i += 1
    return "".join(salida)


org = codigo_python(lectura("backend", "app", "organiza.py"))
# Mover (`os.rename`, `shutil.move`) es LA función; lo vetado es deshacerse de algo.
borra = [m for m in ("os.remove", "os.unlink", "shutil.rmtree", "shutil.os.remove",
                     ".unlink(", ".rmdir(", "send2trash", "trash") if m in org]
if borra:
    falla("organizador", f"organiza.py conoce el borrado ({', '.join(borra)}): la promesa de «no pierdes nada» se rompió")
else:
    dice_ok("organizador", "organiza.py no tiene ninguna primitiva de borrado: sólo renombra y mueve")

# 8.f · las letras no pueden congelar la cara: timeouts y el aviso de reintento.
let = lectura("backend", "app", "letras.py")
if "timeout=" in let and "reintenta" in let:
    dice_ok("letras", "la llamada a LRCLIB lleva timeout y avisa `reintenta` si el servidor está saturado")
else:
    falla("letras", "letras.py se queda sin timeout o sin aviso de reintento: un 503 de LRCLIB "
                    "dejaría la hoja MV colgada sin decir por qué")

# ── 9 · la ronda 2.1: «el APK completo», comprobado sin teléfono ─────────────
# La dueña abrió el 2.0.0 y dijo «no pesa lo que debería». Medido: la proporción de
# compresión era casi la misma que la del 1.1.0 original (0,42 contra 0,40); lo que
# pesaba de menos era **contenido**: el manifiesto había perdido el `<queries>`, el
# `FileProvider` y las reglas de respaldo, y dentro no estaba lo que se le prometió
# (mandar sobre el aparato, elegir voz, recordar sin PC, pensar sin PC, cambiar de
# traje, el punto flotante, la agenda y el correo). Este sector es el que impide que
# vuelva a pasar: cada promesa nueva tiene que estar en los CUATRO sitios donde vive
# —la clase que la hace, el puente que la expone, la cara que la llama y el
# manifiesto o el portátil que la autoriza—. Falta uno y el botón miente.
print("\n[9] contrato 2.1 · las funciones completas, en los cuatro sitios")

METODOS_21 = {
    # nombre en el puente → (clase que la hace, los `que` que tiene que conocer)
    "accion":    ("Acciones.java",   ("volumen", "linterna", "alarma", "temporizador",
                                      "abrir", "lanzadores", "buscar", "estado")),
    "ajusteVoz": ("VozNueva.java",   ("lista", "poner", "predefinida", "descargar",
                                      "probar", "estado")),
    "memoria":   ("Recuerdos.java",  ("guardar", "buscar", "lista", "quien", "olvidar",
                                      "sincronizar", "estado")),
    "mente":     ("Mente.java",      ("estado", "ajustar", "preguntar", "probar", "ollama")),
    "atuendo":   ("Paleta.java",     ("lista", "poner")),
    "agenda":    ("Agenda.java",     ("hoy", "proximos", "abrir", "correo", "apunta")),
}
CARA_21 = (RAIZ / "ui" / "js" / "telefono.js").read_text(encoding="utf-8")
puente_bruto = puente_texto()
puente_21 = sin_comentarios(puente_bruto)
# Los nombres de MÉTODO y de CLASE se buscan en el código limpio de comentarios
# (`puente_21`), para que una prosa no apruebe la prueba. Lo que vive DENTRO de las
# comillas —los `que`, los nombres de evento, las rutas `/api/*`— se busca con
# `literales()`: `sin_comentarios` borra justo esas cadenas, y comparar contra el
# archivo crudo además encuentra lo que un comentario niega.

for metodo, (clase, ques) in METODOS_21.items():
    ruta = APK / "src" / "com" / "cort" / "ia" / clase
    if not ruta.is_file():
        falla(f"2.1 · {metodo}", f"falta {clase}: la cara ofrece el botón y nadie lo hace")
        continue
    bruto = ruta.read_text(encoding="utf-8")
    dicho = literales(bruto)
    expuesto = re.search(r"@JavascriptInterface\s+(?:public\s+)?String\s+" + metodo + r"\s*\(",
                         puente_21)
    if not expuesto:
        falla(f"2.1 · {metodo}", "CortNative no lo expone con @JavascriptInterface: "
                                 "`puede('" + metodo + "')` daría falso y la hoja saldría vacía")
        continue
    if clase.split(".")[0] not in puente_21:
        falla(f"2.1 · {metodo}", f"el puente no nombra a {clase} en ningún sitio")
        continue
    desconocidos = [q for q in ques if f'"{q}"' not in dicho]
    if desconocidos:
        falla(f"2.1 · {metodo}", f"{clase} no conoce los que: {', '.join(desconocidos)} "
                                 "(la cara los manda y Java callaría)")
        continue
    if not re.search(r"\b(?:puede|envia|llama)\s*\(\s*'" + metodo + "'", CARA_21):
        falla(f"2.1 · {metodo}", "la cara no lo llama: quedó escrito en Java y olvidado en `ui/`")
        continue
    dice_ok(f"2.1 · {metodo}", f"{clase} + puente + cara, con sus {len(ques)} `que`")

# Los dos del contrato que NO llevan JSON dentro —`burbuja(boolean)` y
# `comparte(ruta)`—, comprobados igual: Java los expone y la cara los pregunta con su
# `typeof`. `comparte` vive en la pantalla de Música (es donde hay un archivo a mano),
# así que se miran los dos archivos de la cara.
CARA_PANTALLAS = (RAIZ / "ui" / "js" / "pantallas.js").read_text(encoding="utf-8")
for metodo, donde in (("burbuja", "la hoja de Atuendos"), ("comparte", "el transporte de Música/MV")):
    expuesto = re.search(r"@JavascriptInterface\s+(?:public\s+)?(?:String|void)\s+"
                         + metodo + r"\s*\(", puente_21)
    llama = re.search(r"\b(?:puede|llama|envia)\s*\(\s*'" + metodo + "'",
                      CARA_21 + "\n" + CARA_PANTALLAS)
    if not expuesto:
        falla(f"2.1 · {metodo}", "CortNative no lo expone con @JavascriptInterface")
    elif not llama:
        falla(f"2.1 · {metodo}", f"la cara no lo llama ({donde}): quedaría en Java, sin botón")
    else:
        dice_ok(f"2.1 · {metodo}", f"puente + cara ({donde})")

# Las piezas que sostienen lo de arriba: no todas las llama la cara directamente
# (`Sincroniza` la llama `Recuerdos`, y `Cerebro` la llama `Mente`), así que se
# comprueba que **algún** Java del paquete la use. Un archivo sin dueño es peso
# muerto dentro del APK, y peso muerto es exactamente lo que se le reprochó al 2.0.
todo_java = {p.name: p.read_text(encoding="utf-8")
             for p in sorted((APK / "src" / "com" / "cort" / "ia").glob("*.java"))}
for pieza in ("Nube.java", "Cerebro.java", "Sincroniza.java", "Flotante.java",
              "ArchivosProvider.java", "Recuerdos.java"):
    nombre = pieza.split(".")[0]
    usa = [d for d, texto in todo_java.items()
           if d != pieza and nombre in sin_comentarios(texto)]
    if pieza not in todo_java:
        falla("2.1 · piezas", f"falta {pieza}")
    elif not usa:
        falla("2.1 · piezas", f"{pieza} no la usa ningún otro Java: código muerto "
                              "que además pesa en el APK")
    else:
        dice_ok("2.1 · pieza", f"{pieza} la usan {', '.join(sorted(usa))}")

# 9.a · los eventos: lo que Java empuja y lo que la cara escucha tienen el mismo nombre
# Se busca en los LITERALES del Java: el nombre del evento vive dentro del JSON que
# cada clase arma a mano (`"{\"type\":\"auricular\",…}"`), con las comillas escapadas,
# así que una comprobación sobre el texto crudo nunca lo ve.
#
# Y se exige que sea el **tipo** del evento, no cualquier cadena con ese nombre: la
# primera versión de esta prueba dio `ok` para `accion` porque `Mente.java` escribe
# `,"accion":"volumen"` como CAMPO de la respuesta de `mente`. Un campo no es un
# evento, y confundirlo es tener una pantalla escuchando un aviso que nadie manda.
def emitido(texto: str, evento: str) -> bool:
    dicho = literales(texto)
    if f'"type":"{evento}"' in dicho:
        return True
    # `conTipo(json, "mente")`: el puente añade el tipo en el enganche, y ese es el
    # sitio honesto donde vive el nombre (las clases de abajo devuelven sin `type`).
    # Se busca en el texto crudo porque el nombre ESTÁ dentro de una cadena, y
    # `sin_comentarios` la borraría; el riesgo de que un comentario la imite es
    # mucho menor que el de no ver la llamada de verdad.
    return bool(re.search(r'conTipo\([^,]+,\s*"' + evento + r'"\)', texto))


for evento in ("mente", "memoria", "auricular"):
    sale = any(emitido(texto, evento) for texto in todo_java.values())
    escucha = re.search(r"type\s*===?\s*'" + evento + "'", CARA_21) or \
              re.search(r"type\s*===?\s*'" + evento + "'",
                        (RAIZ / "ui" / "js" / "hud.js").read_text(encoding="utf-8"))
    if not sale:
        falla(f"evento {evento}", "Java no lo emite: la pantalla espera un aviso que no llega")
    elif not escucha:
        falla(f"evento {evento}", "la cara no lo escucha: Java habla y nadie recoge el aviso")
    else:
        dice_ok(f"evento {evento}", "emisión en Java y escucha en la cara, con el mismo nombre")

# `accion` **no** es un evento: es síncrono, y su respuesta la lee la cara del
# `envia(...)` de vuelta. Lo que sí tiene que existir es el reenvío del cerebro
# local: `Mente` nombra la acción (`"accion":"volumen"`) y no la ejecuta, así que la
# cara tiene que mandarla a `accion()` o «sube el volumen» sin PC se quedaría en un
# «vale» sin nada debajo.
if re.search(r"ev\.accion", CARA_21) and re.search(r"envia\('accion'", CARA_21):
    dice_ok("cerebro local · acción", "la cara reenvía `accion`/`param` del evento `mente` a `accion()`")
else:
    falla("cerebro local · acción", "el evento `mente` trae `accion` y la cara no la ejecuta: "
                                    "pensar sin PC diría «vale» sin hacer la cosa")

# 9.b · el manifiesto que se perdió en el 2.0 y volvió: proveedor de archivos,
# visibilidad de paquetes y las reglas de respaldo. Cada uno es una función concreta
# («envíame ese archivo», «abre WhatsApp», «no pierdas la dirección del PC»).
cuatro = {"archivos": "archivos.xml", "seguridad_red": "seguridad_red.xml",
          "respaldo": "respaldo.xml", "extraccion": "extraccion.xml"}
for nombre, archivo in cuatro.items():
    if "@xml/" + nombre in XML:
        if (APK / "res" / "xml" / archivo).is_file():
            dice_ok("res/xml", f"{archivo} declarado y existe: aapt2 lo encuentra")
        else:
            falla("res/xml", f"el manifiesto pide @xml/{nombre} y `res/xml/{archivo}` "
                             "no está: el enlace falla al enlazar, en el runner")
referencias = set(re.findall(r'"@xml/(\w+)"', XML))
sin_archivo = [r for r in referencias if not (APK / "res" / "xml" / (r + ".xml")).is_file()]
if sin_archivo:
    falla("res/xml", "el manifiesto apunta a @xml/" + ", @xml/".join(sin_archivo)
                    + " y no existen")

if 'android:name=".ArchivosProvider"' in XML and 'android:authorities="com.cort.ia.files"' in XML:
    dice_ok("FileProvider", "declarado con su autoridad: «envíame ese archivo» puede salir")
else:
    falla("FileProvider", "falta el `<provider>` con `com.cort.ia.files`: compartir un "
                          "archivo con `file://` revienta en Android 7+")

consultas = re.search(r"<queries>.*?</queries>", XML, re.S)
if not consultas:
    falla("<queries>", "el manifiesto no tiene `<queries>`: Android 11+ no deja VER a "
                       "WhatsApp ni al motor de voz, y «abre whatsapp» diría que no está")
else:
    bloque = consultas.group(0)
    # El nombre real es `android.intent.action.TTS_SERVICE` (`TtsServices` es un
    # invento; escribir mal la acción es una visibilidad a medias: «no encuentro
    # motor de voz» en un teléfono que sí lo tiene).
    faltan = [f for f in ("android.intent.action.MAIN", "android.intent.action.TTS_SERVICE",
                          "android.intent.action.SET_ALARM") if f not in bloque]
    if faltan:
        falla("<queries>", "sin " + ", ".join(faltan) + ": la visibilidad queda a medias")
    else:
        dice_ok("<queries>", f"visibilidad declarada ({len(re.findall(chr(60) + 'intent', bloque))} "
                             "intents y " + str(len(re.findall('<package ', bloque))) + " apps nombradas), "
                             "sin `QUERY_ALL_PACKAGES`")

# 9.c · el portátil también puso su mitad: las dos puertas que cruza `Sincroniza.java`
# Se comparan los LITERALES del código, no el archivo entero: la javadoc documenta
# una puerta que NO existe (`/api/memoria`) y buscarla en el texto crudo la daba por
# llamada. El backend es el que tiene que decir si una puerta está o no.
sinc = (APK / "src" / "com" / "cort" / "ia" / "Sincroniza.java").read_text(encoding="utf-8")
puertas = set(re.findall(r'(/api/[a-z_]+)', literales(sinc)))
nucleo = "\n".join(p.read_text(encoding="utf-8")
                   for p in sorted((RAIZ / "backend" / "app").glob("*.py")))
if not puertas:
    falla("sincronía", "`Sincroniza.java` no llama a ninguna puerta `/api/*`: "
                       "la sincronía con el portátil sería un botón que no hace nada")
for puerta in sorted(puertas):
    if puerta not in nucleo:
        falla("sincronía", f"el APK llama a {puerta} y el backend del repo no la tiene: "
                           "la cara vería el aviso de «puerta que falta»")
    else:
        dice_ok("sincronía", f"{puerta} existe en `backend/app/main.py`")
if 'setRequestProperty("Authorization", "Bearer "' in sinc:
    dice_ok("sincronía · clave", "la clave de red viaja sólo en la cabecera `Authorization`")
elif "Authorization" in sinc:
    dice_ok("sincronía · clave", "la clave va en cabecera, no en la URL")
else:
    dice_ok("sincronía · clave", "el APK no manda ninguna clave al portátil")

# 9.d · `assets/habilidades.json`: la memoria del teléfono aprende patrones, y el
# archivo tiene que viajar dentro del APK (lo empaqueta `aapt2 link -A assets`).
habilidades = APK / "assets" / "habilidades.json"
if habilidades.is_file():
    import json as _json
    try:
        datos = _json.loads(habilidades.read_text(encoding="utf-8"))
        # La clave del archivo es `patrones` (la lista de frases que CORT reconoce
        # sin PC); `habilidades` sería contar cero y conformarse con un APK mudo.
        cuenta = len(datos.get("patrones") or [])
        if cuenta == 0:
            falla("habilidades", "`assets/habilidades.json` está vacío o no trae `patrones`: "
                                 "la cara del teléfono no sabría hacer nada sin el portátil")
        else:
            dice_ok("habilidades", f"{cuenta} patrones dentro del APK")
    except Exception as e:
        falla("habilidades", f"`assets/habilidades.json` no es JSON válido: {e}")
else:
    falla("habilidades", "falta `apps/apk/assets/habilidades.json`: "
                         "Recuerdos.leer() no tendría de dónde aprender")

# 9.e · el panel «▸ Segundo plano» de 07 · Perfil: lee siete claves de `bgStatus()`
# y durante una ronda entera Java sólo devolvía `bg` y `pc`. Como en `burbuja`, el
# daño era silencioso: el interruptor nunca se iluminaba, las cuatro filas salían
# siempre sin marcar y `on = !undefined` daba `true`, así que NO se podía apagar.
# La comprobación es en las dos direcciones y sobre el texto crudo: toda clave que
# la cara pregunta como `st.<clave>` tiene que estar en el JSON que arma Java.
HUD_21 = (RAIZ / "ui" / "js" / "hud.js").read_text(encoding="utf-8")
try:
    inicio = puente_bruto.index("public String bgStatus()")
    # El método se recorta a mano (los literales llevan llaves dentro y un contador
    # de llaves se creería cualquier cosa): hasta `setBackground`, que es el siguiente.
    fin = puente_bruto.index("public void setBackground", inicio)
    bg_java = literales(puente_bruto[inicio:fin])
except ValueError:
    bg_java = ""
    falla("segundo plano", "`bgStatus()` no aparece en CortNative.java: el panel no tiene de dónde leer")
if bg_java:
    # Las claves que la cara pregunta en su panel (BG_PERMS + lo que leen renderBg).
    panel = HUD_21[HUD_21.index("const BG_PERMS"):HUD_21.index("async function toggleBg")]
    pedidas = set(re.findall(r"\bst\.([a-zA-Z_]+)", panel)) | {"mic", "notif", "overlay", "battery"}
    faltan_bg = [k for k in sorted(pedidas) if f'"{k}":' not in bg_java]
    if faltan_bg:
        falla("segundo plano", "la cara pregunta " + ", ".join(f"`{k}`" for k in faltan_bg)
                           + " y `bgStatus()` no la emite: el panel miente o se queda mudo")
    else:
        dice_ok("segundo plano", f"las {len(pedidas)} claves que lee el panel están en `bgStatus()`")
    # Y al revés: los tres botones «Dar» del panel tienen que caer en una pantalla
    # real de Android (cuadro, interruptor de Ajustes o lista de batería).
    for kind, donde in (("overlay", "la pantalla de aparecer encima"),
                        ("battery", "la pantalla de batería"),
                        ("autostart", "los ajustes de la app")):
        if not re.search(r'k\.startsWith\("' + kind + '"', (RAIZ / "apps" / "apk" / "src" / "com" /
                                                            "cort" / "ia" / "MainActivity.java")
                         .read_text(encoding="utf-8")):
            falla("segundo plano", f"el botón «Dar» de `{kind}` no tiene a dónde ir: "
                                   + donde + " nunca se abre")
        else:
            dice_ok(f"segundo plano · {kind}", "su botón abre " + donde)

# 9.f · La misma lección de `notif` y de `files`, pero general: cada clase de
# permiso que la cara manda a Java (`perms.ask`, `permRow`, `requestPermission` y
# las filas del panel) tiene que tener una rama en los DOS lados del puente.
# `MainActivity.pidePermiso` decide QUÉ se abre (cuadro o pantalla de Ajustes) y
# `CortNative.permiso` decide si ya está concedido. Los dos terminan en una
# reserva (`grupoDe` devuelve micrófono, `permiso` devuelve `true`) y caer en ella
# es el fallo silencioso exacto: pedir micrófono por una carpeta, o prometer
# archivos que el teléfono nunca concedió.
CARA_TODA = "\n".join(p.read_text(encoding="utf-8")
                      for p in sorted((RAIZ / "ui" / "js").glob("*.js")))
clases = set(re.findall(r"perms\.(?:ask|has)\(\s*'([a-zA-Z_]+)'", CARA_TODA))
clases |= set(re.findall(r"permRow\(\s*'([a-zA-Z_]+)'", CARA_TODA))
clases |= set(re.findall(r"'requestPermission'\s*,\s*'([a-zA-Z_]+)'", CARA_TODA))
panel_perm = HUD_21[HUD_21.index("const BG_PERMS"):HUD_21.index("function bgStatus()")]
clases |= set(re.findall(r"^\s*\['([a-z_]+)'", panel_perm, re.M))
clases.discard("mic")            # el micrófono ES la reserva de `grupoDe`, y está bien

texto_ma = (RAIZ / "apps" / "apk" / "src" / "com" / "cort" / "ia" / "MainActivity.java").read_text(encoding="utf-8")
i = texto_ma.find("void pidePermiso(String kind)")
j = texto_ma.find("private static String[] permisosDeArchivos", i)
# La ventana va desde el principio de `pidePermiso` —con sus tres salidas tempranas:
# burbuja, batería e inicio automático— hasta el final de `grupoDe`, que es justo
# donde empieza lo de siempre.
CUADRO_BRUTO = texto_ma[i:j] if i >= 0 and j > i else ""
PERMISO_BRUTO = ""
k0 = puente_bruto.find("private boolean permiso(String kind)")
k1 = puente_bruto.find("private void pedir(String kind)", k0)
if k0 >= 0 and k1 > k0:
    PERMISO_BRUTO = puente_bruto[k0:k1]

if not CUADRO_BRUTO or not PERMISO_BRUTO:
    falla("permisos", "`pidePermiso` o `permiso` no se encuentran en Java: nada que comprobar")
elif not clases:
    falla("permisos", "la cara no pregunta ningún permiso con clave literal: "
                      "el puente se reformó sin avisar a la prueba")
else:
    sin_rama = []
    for clase in sorted(clases):
        for donde, cuerpo in (("cuadro", CUADRO_BRUTO), ("medición", PERMISO_BRUTO)):
            ramificaciones = re.findall(r'k\.(?:startsWith|equals)\("([a-zA-Z_]+)"', cuerpo)
            if not any(pref == clase or clase.startswith(pref) for pref in ramificaciones):
                sin_rama.append(f"`{clase}` (se queda sin {donde})")
    if sin_rama:
        falla("permisos", "la cara pregunta y Java no tiene rama: " + ", ".join(sin_rama)
              + " → cae en la reserva (micrófono o `true`)")
    else:
        dice_ok("permisos",
                f"las {len(clases)} clases que pregunta la cara tienen rama en el cuadro y en la medición")

# 10 · La ronda 2.2: el cerebro se agrandó (`Razon`), el teléfono empezó a mirar
# lo que tiene dentro (`Aparato`, `Sentidos`) y la tabla de frases se duplicó de
# 144 a 283. Todo eso tiene tres costuras nuevas, y las tres se ven sin teléfono.

# 10.a · Las DOS tablas de frases tienen que ser las mismas frases.
# `assets/habilidades.json` es la que viaja dentro del APK y `tablaDelCodigo` es el
# suelo cuando el asset falta o viene roto. Si se separan, la dueña oye un CORT
# distinto según cómo cargó su teléfono, y eso no se ve desde la cara: sólo aquí.
import json as _json
try:
    _tabla = _json.loads((RAIZ / "apps" / "apk" / "assets" / "habilidades.json")
                         .read_text(encoding="utf-8"))
    del_asset = {r["id"]: (r["accion"], r["param"], r.get("respuesta", ""),
                           tuple(r["patrones"]))
                 for r in _tabla["patrones"]}
except Exception as roto:
    del_asset = {}
    falla("frases", f"`habilidades.json` no se puede leer: {roto}")

_java_tabla = (RAIZ / "apps" / "apk" / "src" / "com" / "cort" / "ia" / "Cerebro.java") \
    .read_text(encoding="utf-8")
_cuerpo = _java_tabla[_java_tabla.index("private void tablaDelCodigo()"):]
_cuerpo = _cuerpo[:_cuerpo.index("\n    }\n")]
del_codigo = []
for _m in re.finditer(r'reglas\.add\(r\((.*?)\)\);', _cuerpo, re.S):
    _args = re.findall(r'"((?:[^"\\]|\\.)*)"', _m.group(1))
    if len(_args) < 4:
        continue
    del_codigo.append((_args[0], _args[1], _args[2], tuple(_args[3:])))

if del_asset:
    # Regla por regla, y la tupla ENTERA: acción, param, la respuesta que se oye y
    # sus frases, en el orden de la tabla (el orden ES la prioridad). Antes se
    # comparaba por pareja (acción, param), y eso era ciego: seis reglas comparten
    # `saludo`/"" así que, mirando sólo la pareja, cinco de sus respuestas podían
    # estar mal en una de las dos tablas y el chequeo daba por bueno.
    del_asset_lista = [(acc, par, resp, ps) for acc, par, resp, ps in del_asset.values()]
    if del_asset_lista != del_codigo:
        solo_a = [f"`{a}`/`{p}`" for a, p, _r, _ps in del_asset_lista
                  if (a, p, _r, _ps) not in del_codigo]
        solo_c = [f"`{a}`/`{p}`" for a, p, _r, _ps in del_codigo
                  if (a, p, _r, _ps) not in del_asset_lista]
        partes = []
        if solo_a:
            partes.append("sólo en el asset: " + ", ".join(solo_a[:6]))
        if solo_c:
            partes.append("sólo en el código: " + ", ".join(solo_c[:6]))
        if not partes:
            # Mismas reglas, distinto orden: la prioridad se ha movido.
            partes.append("el ORDEN (la prioridad) de las reglas es distinto en cada lado")
        falla("frases", "el asset y el código no son la misma tabla: " + "; ".join(partes)
              + " → viértelos otra vez con `python3 scripts/habilidades.py`")
    else:
        _frases = sum(len(ps) for _a, _p, _r, ps in del_asset_lista)
        dice_ok("frases", f"las {len(del_asset_lista)} reglas del asset, con sus respuestas "
                          f"y sus {_frases} frases en el mismo orden, son las {len(del_codigo)} "
                          f"del código")
    # Y las dos promesas que `Razon` ya cumple: si la tabla las recupera, la dueña
    # vuelve a oír la respuesta de adorno en vez de la hora o el día de verdad.
    _excusas = ("barra de estado", "dia que marca el telefono", "día que marca el teléfono")
    _las_dicen = [e for e in _excusas
                  if e in _java_tabla or e in (RAIZ / "apps" / "apk" / "assets"
                                               / "habilidades.json").read_text(encoding="utf-8")]
    if _las_dicen:
        falla("frases", "la tabla otra dice " + ", ".join(f"«{e}»" for e in _las_dicen)
              + ": `Razon` ya sabe la hora y la fecha, esa regla le roba la frase")
    else:
        dice_ok("frases sin excusas", "ninguna regla vuelve a negar la hora y la fecha "
                                      "(`Razon` las dice de verdad)")

def sin_comentarios_js(txt: str) -> str:
    """`//` y `/* */` fuera: un comentario que nombra `CortNative.pausa()` no es una llamada."""
    txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    return re.sub(r"//[^\n]*", "", txt)


def claves_emitidas(ruta_java: str) -> set[str]:
    t = (RAIZ / "apps" / "apk" / "src" / "com" / "cort" / "ia" / ruta_java).read_text(encoding="utf-8")
    # `Json` tiene tres bocas: `p` (cruda), `n` (número) y `s` (texto). Contar sólo
    # `p` era el fallo de esta misma prueba: `Aparato` escribe casi todo con `n`/`s`.
    return set(re.findall(r'\.[pns]\("(\w+)"', t)) | set(re.findall(r'\\"(\w+)\\":', t))


# 10.b · Cada método del puente que la cara llama existe de verdad en Java.
# Con `const N = window.CortNative`, un `N.aparato()` mal escrito no da error: sale
# `undefined`, la cara lo parsea como JSON roto y el panel se queda mudo. Es la
# misma familia de fallo que `notif`, `burbuja` y `files` con los permisos, pero por
# el lado de los métodos.
PUENTE_JAVA = puente_texto()
if not PUENTE_JAVA:
    falla("puente", "no encuentro `CortNative.java` para cruzar los nombres")
metodos_javascript = set(re.findall(
    r'@JavascriptInterface\s+(?:public\s+)?(?:static\s+)?[A-Za-z<>\[\], ]+\s+(\w+)\s*\(',
    PUENTE_JAVA))
llamados = set()
for _p in sorted((RAIZ / "ui" / "js").glob("*.js")):
    _t = sin_comentarios_js(_p.read_text(encoding="utf-8"))
    llamados |= set(re.findall(r"(?:window\.)?CortNative\.(\w+)\s*\(", _t))
    # `N.` sólo es el puente en el fichero que de verdad hace `const N = window.CortNative`.
    if re.search(r"\bN\s*=\s*window\.CortNative", _t):
        llamados |= set(re.findall(r"\bN\.(\w+)\s*\(", _t))
llamados -= {"emit", "available"}            # el emisor de la cara, no un método de Java
inventados = sorted(n for n in llamados if n not in metodos_javascript)
if inventados:
    falla("puente", "la cara llama " + ", ".join(f"`{n}()`" for n in inventados)
          + " y no hay ningún `@JavascriptInterface` con ese nombre → sale `undefined`")
else:
    dice_ok("puente", f"los {len(llamados)} métodos que la cara nombra están en Java "
                      f"(de {len(metodos_javascript)})")


# 10.c · `Aparato` y `Sentidos` emiten las claves que el panel «Entorno» lee.
# Lo mismo que se exige a los permisos: si la cara pide `a.battTemp` y Java nunca
# escribe esa clave, el panel pinta `undefined` y la dueña lee un teléfono raro en
# vez de leer que falta un dato.
_ap = HUD_21[HUD_21.index("function pintaAparato"):HUD_21.index("function pintaSensores")]
lee_aparato = set(re.findall(r"\ba\.(\w+)", _ap)) - {"length", "toFixed", "map", "filter"}
emite_aparato = claves_emitidas("Aparato.java")
faltan_a = sorted(k for k in lee_aparato if k not in emite_aparato)
if faltan_a:
    falla("entorno", "`pintaAparato` lee " + ", ".join(f"`a.{k}`" for k in faltan_a)
          + " y `Aparato.estado()` no la emite")
else:
    dice_ok("entorno", f"las {len(lee_aparato)} claves que pinta `pintaAparato` las emite `Aparato`")

# La fila de un sensor la escribe `pintaSensores` con la variable `x`, no con `d`.
_fin_sensores = HUD_21.index("\n}", HUD_21.index("function pintaSensores"))
lee_sens = set(re.findall(r"\bx\.(\w+)", HUD_21[HUD_21.index("function pintaSensores"):_fin_sensores]))
lee_sens -= {"length", "map", "filter", "toFixed", "join"}
emite_sens = claves_emitidas("Sentidos.java")
faltan_s = sorted(k for k in lee_sens if k not in emite_sens)
if not lee_sens:
    falla("entorno", "`pintaSensores` no se puede recortar: la prueba queda vacía")
elif faltan_s:
    falla("entorno", "`pintaSensores` lee " + ", ".join(f"`x.{k}`" for k in faltan_s)
          + " y `Sentidos.lectura()` no la emite")
else:
    dice_ok("entorno", f"las {len(lee_sens)} claves de una fila de sensores las emite `Sentidos`")

# ── [9b] el oído propio: motor.sh ↔ Oido.kt ↔ manifiesto ↔ pipeline ─────────
# La ronda 2.3 mete un motor de reconocimiento dentro del APK. Son cuatro sitios
# que tienen que decir el mismo número y tres trampas que ya están medidas; si uno
# se separa, el fallo no sale en `javac`: sale en el teléfono, en forma de modelo
# que no carga o de `.so` que no se instalan.
MOTOR_SH = (APK / "motor.sh").read_text(encoding="utf-8") if (APK / "motor.sh").exists() else ""
OIDO_KT = next((p.read_text(encoding="utf-8") for p in (APK / "src" / "com" / "cort" / "ia").glob("Oido.kt")), "")
COMPILAR_SH = (APK / "compilar.sh").read_text(encoding="utf-8")
WORKFLOW = (RAIZ / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
MANIFIESTO = (APK / "AndroidManifest.xml").read_text(encoding="utf-8")

if not MOTOR_SH or not OIDO_KT:
    falla("oído", "falta apps/apk/motor.sh o `Oido.kt`: el oído propio no está en el repo")
else:
    m_motor = re.search(r'^MODELO="([a-z0-9.\-]+)"', MOTOR_SH, re.M)
    m_oido = re.search(r'const val MODELO = "([a-z0-9.\-]+)"', OIDO_KT)
    p_modelo = re.search(r'^MODELO_PESO=(\d+)', MOTOR_SH, re.M)
    p_oido = re.search(r'const val PESO_ZIP = (\d+)L', OIDO_KT)
    if not (m_motor and m_oido):
        falla("oído", "no se encuentra el nombre del modelo en `motor.sh` o en `Oido.kt`")
    elif m_motor.group(1) != m_oido.group(1):
        falla("oído", f"`motor.sh` baja `{m_motor.group(1)}` y `Oido.kt` busca `{m_oido.group(1)}`: "
                      "el desempaque buscaría un ZIP que no existe")
    else:
        dice_ok("oído", f"el modelo se nombra igual en los dos sitios: `{m_motor.group(1)}`")
    # El peso del ZIP se comprueba en `motor.sh` (`MODELO_PESO`) y en `Oido.kt`
    # (`PESO_ZIP`, la marca que escribe el desempaque). Si se separan, la marca
    # nunca cuadra y CORT copia 60 MB en cada arranque.
    if p_oido and p_modelo and p_oido.group(1) != p_modelo.group(1):
        falla("oído", f"`Oido.kt` dice PESO_ZIP={p_oido.group(1)} y `motor.sh` baja {p_modelo.group(1)}: "
                      "la marca del desempaque no cuadraría y se re-extraería siempre")
    elif p_oido and p_modelo:
        dice_ok("oído", f"el peso del ZIP es el mismo en los dos: {p_oido.group(1)} B")

    # Las dos trampas del AAR de Vosk, medidas leyendo el fuente de Alpha Cephei.
    # Se miran SIN los comentarios: `Oido.kt` explica en su cabecera por qué NO los
    # usa, y esa explicación contendría los dos nombres.
    OIDO_CODIGO = re.sub(r"/\*.*?\*/", " ", OIDO_KT, flags=re.S)
    OIDO_CODIGO = re.sub(r"//[^\n]*", " ", OIDO_CODIGO)
    for trampa, por_que in [
        ("SpeechService", "su hilo lanza `RuntimeException(«error reading audio buffer»)`: "
                          "el micrófono que quita un juego tumbaría la app"),
        ("StorageService", "necesita `res/raw` con `AssetFileDescriptor`, y `aapt2` comprime "
                           "los assets: ese descriptor no existe"),
    ]:
        if trampa in OIDO_CODIGO:
            falla("oído", f"`Oido.kt` vuelve a usar `{trampa}`: {por_que}")
    if not any(t in OIDO_CODIGO for t in ("SpeechService", "StorageService")):
        dice_ok("oído", "el desempaque y la escucha van a mano, sin `SpeechService` ni `StorageService`")

    # El trato de las `.so`: comprimidas sólo son legales con `extractNativeLibs`.
    if 'android:extractNativeLibs="true"' not in MANIFIESTO:
        falla("oído", "el manifiesto no pone `android:extractNativeLibs=\"true\"`: con las `.so` "
                      "comprimidas del `zip -r` la app instala y no arranca")
    elif "zip -q -r ../apk/sin-alinear.apk lib" not in COMPILAR_SH:
        falla("oído", "el manifiesto declara las `.so` extraíbles pero `compilar.sh` no las mete en el APK")
    else:
        dice_ok("oído", "las `.so` viajan comprimidas y el manifiesto permite extraerlas al instalar")

    # El pipeline: versión, descarga cacheada y prueba antes del build.
    v_yml = re.search(r'APK_VERSION:\s*"([0-9.]+)"', WORKFLOW)
    v_sh = re.search(r'APK_VERSION="\$\{APK_VERSION:-([0-9.]+)\}"', COMPILAR_SH)
    if v_yml and v_sh and v_yml.group(1) != v_sh.group(1):
        falla("oído", f"`build.yml` compila la {v_yml.group(1)} y `compilar.sh` espera la {v_sh.group(1)}")
    elif v_yml and v_sh:
        dice_ok("oído", f"la versión del APK es la misma en el pipeline y en el script: {v_yml.group(1)}")
    if "prueba-oido.sh" not in WORKFLOW:
        falla("oído", "`build.yml` no corre `scripts/prueba-oido.sh`: el oído llegaría al teléfono sin probar")
    else:
        dice_ok("oído", "la prueba del oído con Vosk de verdad va en el pipeline, antes del APK")

# ── 10 · la ronda 2.4: los cerebros de casa (Ollama por Wi-Fi) ──────────────
# La dueña pidió «que CORT sí pueda instalar modelos locales de Ollama». Medido:
# Ollama NO cabe dentro de un APK (es un servidor en Go que pide Linux), así que la
# promesa honesta es que el teléfono HABLE con el Ollama del PC por Wi-Fi: listar,
# bajar, borrar, elegir y preguntar. Son cuatro piezas con el nombre exacto —la
# clase del HTTP, la ruta de `Mente`, la hoja y el pipeline— y si una falta el
# botón miente. Aquí se cose la ronda entera sin teléfono.
print("\n[10] ronda 2.4 · Ollama en la Wi-Fi de casa")

OLLAMA_RUTA = APK / "src" / "com" / "cort" / "ia" / "Ollama.java"
MENTE_RUTA = APK / "src" / "com" / "cort" / "ia" / "Mente.java"
NUBE_RUTA = APK / "src" / "com" / "cort" / "ia" / "Nube.java"
ACCIONES_24 = ("estado", "lista", "descubre", "fija", "usa", "descarga", "borra")
if not OLLAMA_RUTA.is_file():
    falla("2.4 · ollama", "falta `Ollama.java`: la cara ofrece los botones y nadie habla con el PC")
else:
    ollama_txt = OLLAMA_RUTA.read_text(encoding="utf-8")
    mente_txt = MENTE_RUTA.read_text(encoding="utf-8")
    # Los cuadros llevan dentro `\"que\":\"lista\"`; sin las barras del escape de
    # Java se leen como el JSON que de verdad sale al WebView.
    ollama_plano = ollama_txt.replace("\\", "")
    mente_lits = literales(mente_txt)

    sin_que = [a for a in ACCIONES_24 if f'"que":"{a}"' not in ollama_plano]
    if sin_que:
        falla("2.4 · cuadros", f"`Ollama.java` no etiqueta sus cuadros con: {', '.join(sin_que)} "
                               "— la cara no sabría qué pintar (y una descarga fallida no bajaría la barra)")
    else:
        dice_ok("2.4 · cuadros", f"los {len(ACCIONES_24)} cuadros salen etiquetados con su `que`")

    sin_ruta = [a for a in ACCIONES_24 if f'"{a}"' not in mente_lits]
    if '"ollama"' not in mente_lits:
        falla("2.4 · ruta", "`Mente` no compara con \"ollama\": la orden de la cara no llega a `Ollama`")
    elif sin_ruta:
        falla("2.4 · ruta", f"`Mente.java` no conoce las acciones: {', '.join(sin_ruta)} "
                            "(la cara las manda y Java contestaría «no conozco esa acción»)")
    else:
        dice_ok("2.4 · ruta", f"`Mente` despacha `que:\"ollama\"` con sus {len(ACCIONES_24)} acciones")

    if "new Ollama(" not in sin_comentarios(mente_txt):
        falla("2.4 · ruta", "`Mente` no monta `Ollama`: la clase está escrita y aislada")
    else:
        dice_ok("2.4 · puente", "no hace falta método nuevo: entra por `mente()`, que `CortNative` ya expone")

    # La hoja: que llame las acciones y que escuche el evento con el mismo nombre.
    sin_cara = [a for a in ACCIONES_24 if f"'{a}'" not in CARA_21]
    if "que: 'ollama'" not in CARA_21:
        falla("2.4 · cara", "la hoja no manda nunca `{que:'ollama'}`: quedó en Java, sin botón")
    elif sin_cara:
        falla("2.4 · cara", f"la hoja no ofrece: {', '.join(sin_cara)}")
    elif "ev.de === 'ollama'" not in CARA_21:
        falla("2.4 · cara", "la cara no escucha `de:'ollama'` en el evento `mente`: la lista y la "
                            "barra no se moverían nunca")
    else:
        dice_ok("2.4 · cara", f"las {len(ACCIONES_24)} acciones a la vista y el evento `de:'ollama'` escuchado")

    # Cada `id` del bloque tiene que estar enganchado o escrito por Java: un botón
    # sin `onclick` es exactamente el «no hace nada» que ya se reprochó al 2.0.0.
    ids = sorted(set(re.findall(r'id="(eq-oll-[a-z-]+)"', CARA_21)))
    # `-est` y `-dice` no se buscan a pelo: los escribe `linea('oll'…)` /
    # `avisa('oll'…)` montando el id, igual que el resto de la hoja.
    sin_enganche = [i for i in ids if f"el('{i}')" not in CARA_21
                    and not (i.endswith(("-est", "-dice")) and "'oll'" in CARA_21)]
    if not ids:
        falla("2.4 · hoja", "no hay ningún `eq-oll-*` en `CARA_CEREBRO`: el bloque no existe")
    elif sin_enganche:
        falla("2.4 · hoja", f"escritos y sin dueño: {', '.join(sin_enganche)}")
    else:
        dice_ok("2.4 · hoja", f"los {len(ids)} ids del bloque tienen su gancho")

    CSS = (RAIZ / "ui" / "css" / "hud.css").read_text(encoding="utf-8")
    sin_css = [c for c in (".eq-barra", ".eq-mod") if c not in CSS]
    if sin_css:
        falla("2.4 · hoja", f"la cara usa {', '.join(sin_css)} y `hud.css` no lo define: "
                            "saldría sin estilos en el teléfono")
    else:
        dice_ok("2.4 · hoja", "la barra de descarga y la fila de modelo tienen su CSS")

    # Cero permisos nuevos: `descubre` se hace con la IPv4 propia, sin `WifiInfo`.
    if "ACCESS_WIFI_STATE" in MANIFIESTO:
        falla("2.4 · permisos", "`descubre` habría pedido ACCESS_WIFI_STATE: se prometió no añadir ninguno")
    elif "getNetworkInterfaces" not in ollama_plano:
        falla("2.4 · permisos", "`descubre` no usa `NetworkInterface`: ¿con qué saca ahora el rango de la Wi-Fi?")
    else:
        dice_ok("2.4 · permisos", "cero permisos nuevos: la red propia se lee con `NetworkInterface`")

    # `usa` escribe lo que `Nube` lee: si los nombres de las prefs se separan, el
    # modelo elegido no se usa y la cara dice «listo» mintiendo.
    ollama_lits = literales(ollama_txt)
    nube_lits = literales(NUBE_RUTA.read_text(encoding="utf-8"))
    separadas = [c for c in ("nube-proveedor", "nube-base", "nube-modelo", "ollama-servidor")
                 if f'"{c}"' not in ollama_lits]
    leidas = [c for c in ("nube-proveedor", "nube-base", "nube-modelo") if f'"{c}"' not in nube_lits]
    if separadas:
        falla("2.4 · prefs", f"`Ollama.usa` no escribe {', '.join(separadas)}: elegir un modelo no lo usaría")
    elif leidas:
        falla("2.4 · prefs", f"`Nube` no lee {', '.join(leidas)}: las claves se escriben en un idioma que él no habla")
    else:
        dice_ok("2.4 · prefs", "`usa` escribe y `Nube` lee las mismas cuatro claves")

    if '"ollama"' not in nube_lits:
        falla("2.4 · Nube", "el catálogo de `Nube` no tiene `ollama`: elegirlo dejaría la base vacía")
    elif "'ollama'" not in CARA_21:
        falla("2.4 · Nube", "`PROVEEDORES` de la cara no ofrece `ollama`")
    else:
        dice_ok("2.4 · Nube", "ollama es un proveedor más, sin clave y con su base /v1")

# ── 10b · la terminal ampliada (#77): ayuda ↔ CMDS ↔ router ─────────────────
# La dueña pidió «la terminal de CORT… que se pueda ampliar en teléfono y funcione
# con esos cerebros locales». Ampliarla son tres capas que tienen que decir el mismo
# nombre: la lista que `ayuda` enumera en la hoja, el `CMDS` que el HUD usa para el
# Tab y la pantalla 09 · Ayuda, y el router de `telefono.js` que la atiende. El daño
# clásico es la promesa vacía: una ayuda que enumera un comando sin router deja a la
# dueña escribiendo cosas que CORT ignora en silencio.
print("\n[10b] la terminal del teléfono (lo que promete, lo que completa, lo que atiende)")

PROMESAS_24 = ("busca cerebros", "modelos", "usa el modelo", "descarga el modelo",
               "borra el modelo", "piensa", "ayuda", "olvida la terminal")
ayuda_24 = re.search(r"const CMD_TELEFONO = \[(.*?)\];", CARA_21, re.S)
cmds_24 = re.search(r"const CMDS = \[(.*?)\];", HUD_21, re.S)
if not ayuda_24:
    falla("terminal · ayuda", "`telefono.js` no tiene `CMD_TELEFONO`: «ayuda» no sabe qué enumerar")
elif not cmds_24:
    falla("terminal · ayuda", "`hud.js` no tiene `CMDS`: ni el Tab ni la pantalla 09 muestran comandos")
else:
    en_ayuda = ayuda_24.group(1)
    lista_cmds = re.findall(r"'([^']*)'", cmds_24.group(1))
    hueso = [p for p in PROMESAS_24 if p not in en_ayuda]
    huérfanas = [p for p in PROMESAS_24
                 if p not in hueso and not any(c.startswith(p) for c in lista_cmds)]
    if hueso:
        falla("terminal · ayuda", f"`ayuda` ya no promete: {', '.join(hueso)}")
    elif huérfanas:
        falla("terminal · ayuda", f"se prometen pero el Tab/09 · Ayuda no los ofrece: {', '.join(huérfanas)} "
                                  "— en el teléfono no hay forma de saberlos sin leer el código")
    else:
        dice_ok("terminal · ayuda",
                f"las {len(PROMESAS_24)} promesas de `ayuda` están también en `CMDS` "
                f"({len(lista_cmds)} comandos completados por el Tab)")

    # Que la consola del PC no se pierda lo del teléfono: `pantallas.js` tiene que
    # importar la boca ampliada y llamarla ANTES de intentar el núcleo.
    if "export function terminalTelefono" not in CARA_21:
        falla("terminal · costura", "`terminalTelefono` no está exportado: `pantallas.js` no podría llamarlo")
    elif not re.search(r"import\s*\{[^}]*\bterminalTelefono\b[^}]*\}\s*from\s*'\./telefono\.js'", scr_txt):
        falla("terminal · costura", "`pantallas.js` no importa `terminalTelefono`: la pantalla Código "
                                    "seguiría mandando todo al núcleo, que en el teléfono no está")
    elif "terminalTelefono(orden" not in scr_txt:
        falla("terminal · costura", "`pantallas.js` importa `terminalTelefono` y no lo llama: código muerto")
    elif "CMD_TELEFONO.forEach" not in CARA_21:
        falla("terminal · costura", "«ayuda» no recorre `CMD_TELEFONO`: la lista quedaría escrita y muda")
    else:
        dice_ok("terminal · costura", "la pantalla Código del teléfono pasa por el puente "
                                      "y devuelve el eco a su propia consola")

    # El grupo 4b: sin él, «busca cerebros» se lo llevaban la app o el buscador.
    if not re.search(r"\\b\(ollama\|modelo\|modelos\|cerebros\)\\b", CARA_21):
        falla("terminal · router", "`telefonoPorVoz` no tiene el grupo de `ollama|modelo|modelos|cerebros`: "
                                   "escribir «modelos» abriría una app o el navegador")
    else:
        dice_ok("terminal · router", "el grupo de los cerebros va antes que «abre una app» y «busca …»")

# La prueba que decide todo: el diálogo HTTP se comprueba contra un Ollama de
# mentira levantado dentro del JDK, sin teléfono y sin internet.
PRUEBA4 = APK / "prueba" / "Prueba4.java"
SH_24 = (RAIZ / "scripts" / "prueba-mente.sh").read_text(encoding="utf-8")
if not PRUEBA4.is_file():
    falla("2.4 · prueba", "falta `apps/apk/prueba/Prueba4.java`: Ollama llegaría al teléfono sin probar")
elif "Prueba4" not in SH_24 or "jdk.httpserver" not in SH_24:
    falla("2.4 · prueba", "`prueba-mente.sh` no corre `Prueba4` o no añade `jdk.httpserver`: "
                          "la suite quedaría fuera del pipeline")
elif "Ollama.java" not in SH_24:
    falla("2.4 · prueba", "`prueba-mente.sh` no copia `Ollama.java` a /tmp: `Prueba4` no compilaría")
elif "prueba-mente.sh" not in WORKFLOW:
    falla("2.4 · prueba", "`build.yml` no corre la mente: las suites no se ejecutan antes del APK")
else:
    dice_ok("2.4 · prueba", "Prueba4 (servidor de mentira) va en `prueba-mente.sh` y en el pipeline")

# ── 11 · la ronda 2.4: las reglas «cuando X, entonces Y» ─────────────────────
# «la automatización como es JARVIS o Cortana, eso necesito». Son tres capas: el
# motor (`automatiza.js`, puro y probado con node), la cara que lo pinta y le da las
# manos (`telefono.js`), y la seña de Java que lo alimenta (`type:"aviso"` nuevo).
# El error que se caza aquí es el de siempre: un `<select>` que ofrece una acción que
# nadie atiende, o una regla que se pinta pero no se monta.
print("\n[11] las automatizaciones (motor ↔ manos ↔ seña de Java)")

MOTOR_RUTA = RAIZ / "ui" / "js" / "automatiza.js"
if not MOTOR_RUTA.is_file():
    falla("2.4b · motor", "falta `ui/js/automatiza.js`: la hoja promete reglas y no hay quien las cumpla")
else:
    motor = MOTOR_RUTA.read_text(encoding="utf-8")

    def array_js(nombre):
        m = re.search(r"export const " + nombre + r" = \[(.*?)\n\];", motor, re.S)
        return m.group(1) if m else ""

    disp = re.findall(r"\{ id: '([a-z]+)',", array_js("DISPARADORES"))
    acciones = re.findall(r"\{ id: '([a-z]+)',", array_js("ACCIONES"))
    if not disp or not acciones:
        falla("2.4b · motor", "no se leen los disparadores o las acciones del motor")
    else:
        # 11.a · cada acción que ofrece el `<select>` tiene su `case` en las manos.
        manos = re.search(r"function ejecutaAccion\(que, a\) \{(.*?)\n\}\n", CARA_21, re.S)
        if not manos:
            falla("2.4b · manos", "`telefono.js` no define `ejecutaAccion`: las reglas no tendrían manos")
        else:
            casos = set(re.findall(r"case '([a-z]+)'", manos.group(1)))
            sin_mano = [a for a in acciones if a not in casos]
            huérfanas = sorted(casos - set(acciones))
            if sin_mano:
                falla("2.4b · manos", f"la hoja ofrece acciones que nadie atiende: {', '.join(sin_mano)} "
                                      "— la regla se cumpliría «a medias» y en silencio")
            elif huérfanas:
                falla("2.4b · manos", f"las manos atienden {', '.join(huérfanas)} pero la hoja no las ofrece")
            else:
                dice_ok("2.4b · manos", f"las {len(acciones)} acciones del formulario tienen su `case`")

        # 11.b · cada señal que promete un disparador existe de verdad. `reloj` y
        # `aparato` las produce la cara; `aviso` y `auricular` las emite Java, y ésa
        # es la que hay que comprobar contra el puente.
        senales = set(re.findall(r"senal: '([^']+)'", array_js("DISPARADORES")))
        inventadas = [s for s in senales if s not in ("aviso", "auricular", "aparato", "reloj",
                                                     "stt-final / terminal")]
        java = puente_texto()
        if inventadas:
            falla("2.4b · señales", f"disparadores con señal inventada: {', '.join(inventadas)}")
        elif '"type\\":\\"aviso\\"' not in java:
            falla("2.4b · señales", "Java no emite `{type:\"aviso\"}`: la regla de avisos nunca se enteraría")
        elif '"type\\":\\"auricular\\"' not in java:
            falla("2.4b · señales", "Java no emite el evento del auricular")
        elif 'ev.type === \'aviso\'' not in CARA_21 or 'ev.type === \'auricular\'' not in CARA_21:
            falla("2.4b · señales", "la cara no escucha `aviso`/`auricular`: las señales llegan y se pierden")
        else:
            dice_ok("2.4b · señales", ", ".join(sorted(senales)) + " — todas con su emisor o su origen en la cara")

        # 11.c · Java: quien manda la seña tiene que ser `.Avisos`, en el momento.
        avisos_java = (APK / "src" / "com" / "cort" / "ia" / "Avisos.java").read_text(encoding="utf-8")
        if "avisoEnLaCara" not in avisos_java or "avisoEnLaCara" not in java:
            falla("2.4b · java", "`Avisos` no avisa a la cara cuando llega algo: la automatización de avisos "
                                 "sólo funcionaría al abrir la hoja")
        elif "MainActivity.front()" not in avisos_java:
            falla("2.4b · java", "el aviso se manda sin preguntar si la cara está: con la app cerrada sería un fallo")
        else:
            dice_ok("2.4b · java", "`.Avisos` manda la seña nada más guardar el aviso, y sólo si la cara está viva")

    # 11.d · la hoja: bloque montado, enganchado y pintado.
    sin_montar = [x for x in ("bloque('autos'", "enganchaAutos();", "pintaAutos();")
                  if x not in CARA_21]
    ids = sorted(set(re.findall(r'id="(eq-aut-[a-z]+)"', CARA_21)))
    # `-est` y `-dice` no se buscan a pelo: los montan `linea('autos'…)` /
    # `avisa('autos'…)` / `diceBien('autos'…)` con el prefijo, como en el resto de la hoja.
    sin_dueno = [i for i in ids if f"el('{i}')" not in CARA_21
                 and not (i.endswith(("-est", "-dice")) and "'autos'" in CARA_21)]
    if "from './automatiza.js'" not in CARA_21:
        falla("2.4b · hoja", "`telefono.js` no importa el motor: la hoja sería decoration")
    elif sin_montar:
        falla("2.4b · hoja", f"el bloque no está del todo montado: falta {', '.join(sin_montar)}")
    elif not ids:
        falla("2.4b · hoja", "no hay ningún `eq-aut-*`: el formulario no existe")
    elif sin_dueno:
        falla("2.4b · hoja", f"escritos y sin dueño: {', '.join(sin_dueno)}")
    else:
        dice_ok("2.4b · hoja", f"bloque 8 montado, con sus {len(ids)} campos enganchados")

    sin_css = [c for c in (".eq-mod.apagada", ".eq-mod-b", ".eq-mod-n") if c not in
               (RAIZ / "ui" / "css" / "hud.css").read_text(encoding="utf-8")]
    if sin_css:
        falla("2.4b · css", f"la hoja usa {', '.join(sin_css)} y `hud.css` no lo define")
    else:
        dice_ok("2.4b · css", "la fila de una regla, su apagado y sus botones tienen estilo")

    # 11.e · las reglas mandan ANTES que la boca de CORT, y la frase se puede crear
    # de una vez. Sin el −1, «modo noche» se lo llevaba el volumen de siempre.
    antes = CARA_21.index("export function telefonoPorVoz")
    cuerpo = CARA_21[antes:antes + 4000]
    if "autos.dispara({ tipo: 'frase'" not in cuerpo:
        falla("2.4b · voz", "las reglas no se consultan en `telefonoPorVoz`: la frase se va a la boca de siempre")
    elif "reglaDeVoz" not in cuerpo:
        falla("2.4b · voz", "«cuando … haz …» no crea ninguna regla: habría que escribirla a mano")
    elif "case 'recuerdo'" not in (manos.group(1) if manos else ""):
        falla("2.4b · voz", "la regla de apuntar recuerdos no está entre las manos")
    else:
        dice_ok("2.4b · voz", "las reglas van en el sitio −1 (ganan) y se crean hablando")

    # 11.f · la prueba del motor, en el pipeline.
    PRUEBA_AUTO = RAIZ / "scripts" / "prueba-automatiza.mjs"
    if not PRUEBA_AUTO.is_file():
        falla("2.4b · prueba", "falta `scripts/prueba-automatiza.mjs`: el motor llegaría al teléfono sin probar")
    elif "prueba-automatiza.mjs" not in WORKFLOW:
        falla("2.4b · prueba", "`build.yml` no corre la prueba del motor: quedaría fuera del pipeline")
    else:
        dice_ok("2.4b · prueba", "el motor se prueba con node, en el portátil y en el pipeline")

# ── 12 · la ronda 2.4.1: las vías para abrir CORT, y el auricular sin cara ───
# Cinco caminos nuevos que no se pueden probar en el portátil y que se rompen en
# silencio: un `<intent-filter>` que falta y Android no ofrece a CORT en el listado
# del asistente; un `@string/…` escrito como literal y los atajos del icono dejan
# de salir; un `hojaDe` que devuelve «equipo» y una pantalla que en la lista se
# llama distinto; un `type:"atajo"` que Java emite y la cara no escucha; y un
# `teclaDe` que vuelve a ser `private` — ése lo para `javac`, pero lo para en el
# run, con la Release ya anunciada.
print("\n[12] ronda 2.4.1 · asistente, baldosín, atajos y el doble toque sin cara")

MAN = (APK / "AndroidManifest.xml").read_text(encoding="utf-8")
ACCIONES_MAN = set(re.findall(r'<action android:name="([^"]+)"', MAN))
PROPIAS = ("com.cort.ia.ESCUCHAR", "com.cort.ia.EQUIPO", "com.cort.ia.CHARLA")
FALTAN = [a for a in ("android.intent.action.ASSIST", "android.intent.action.VOICE_COMMAND",
                      "android.service.quicksettings.action.QS_TILE", *PROPIAS)
          if a not in ACCIONES_MAN]
if FALTAN:
    falla("2.4.1 · manifiesto", f"no se declara {', '.join(FALTAN)}: esa vía de arranque "
                                "no existe para Android, y el gesto se lo queda Google en silencio")
else:
    dice_ok("2.4.1 · manifiesto", "ASSIST, VOICE_COMMAND, el baldosín y las tres acciones propias")

if "android.permission.BIND_QUICK_SETTINGS_TILE" not in MAN:
    falla("2.4.1 · baldosín", "el `<service>` no lleva su `android:permission`: la cortina no lo lista")
elif 'android:name="android.app.shortcuts"' not in MAN:
    falla("2.4.1 · atajos", "falta la meta-datos `android.app.shortcuts`: mantener el icono no da nada")
else:
    dice_ok("2.4.1 · cortina", "TileService protegido y los atajos del icono anunciados")

ATAJOS_RUTA = APK / "res" / "xml" / "atajos.xml"
ETIQUETAS = [p for p in sorted((APK / "res" / "values").glob("*.xml"))] if (APK / "res" / "values").is_dir() else []
texto_etiquetas = " ".join(p.read_text(encoding="utf-8") for p in ETIQUETAS)
if not ATAJOS_RUTA.is_file():
    falla("2.4.1 · atajos", "`res/xml/atajos.xml` no existe y el manifiesto apunta a él: aapt2 muere al enlazar")
else:
    arbol = ET.fromstring(ATAJOS_RUTA.read_text(encoding="utf-8"))
    A = "{http://schemas.android.com/apk/res/android}"
    atajos = arbol.findall("shortcut")
    id_de = lambda s: s.get(A + "shortcutId") or "?"
    # Los atributos del `<intent>` van con el prefijo `android:`, y `ElementTree`
    # los guarda como nombre expandido: leerlos sin `A +` da `None` y el sector se
    # queja de un destino vacío que en el archivo sí está escrito.
    viajes = {(i.get(A + "action") or "", i.get(A + "targetClass") or "")
              for s in atajos for i in s.findall("intent")}
    sin_via = [a for a, c in viajes if a not in ACCIONES_MAN]
    mal_destino = [c for a, c in viajes if c != "com.cort.ia.MainActivity"]
    # La trampa medida: con `android:shortcutShortLabel="Escucha"` (literal) el
    # `ShortcutPackage` del sistema espera un recurso y el atajo no aparece.
    huesos = [id_de(s) for s in atajos
              if not (s.get(A + "shortcutShortLabel") or "").startswith("@string/")]
    sin_recurso = sorted({m.group(1) for s in atajos for m in
                          (re.search(r'@string/(\w+)', s.get(A + k) or "") for k in
                           ("shortcutShortLabel", "shortcutLongLabel", "shortcutDisabledMessage"))
                          if m and f'name="{m.group(1)}"' not in texto_etiquetas})
    if len(atajos) != 3:
        falla("2.4.1 · atajos", f"hay {len(atajos)} atajos y la hoja promete tres")
    elif sin_via:
        falla("2.4.1 · atajos", f"el icono manda {', '.join(sin_via)} y el manifiesto no las recibe")
    elif mal_destino:
        falla("2.4.1 · atajos", f"viaje hacia {', '.join(mal_destino)} en vez de `com.cort.ia.MainActivity`")
    elif huesos:
        falla("2.4.1 · atajos", f"etiqueta sin `@string/` en {', '.join(huesos)}: Android no pinta ese atajo")
    elif sin_recurso:
        falla("2.4.1 · atajos", f"etiquetas que no existen en `res/values`: {', '.join(sin_recurso)}")
    else:
        dice_ok("2.4.1 · atajos", "tres atajos, con su acción declarada, su destino y su `@string/`")

# El baldosín: la clase tiene que existir con el nombre exacto del manifiesto.
PANEL = APK / "src" / "com" / "cort" / "ia" / "Panel.java"
if not PANEL.is_file():
    falla("2.4.1 · baldosín", "`Panel.java` no existe: `javac` compila el manifiesto igual y el App se instala sin tile")
else:
    panel_txt = sin_comentarios(PANEL.read_text(encoding="utf-8"))
    sin_panel = [x for x in ("extends TileService", "startActivityAndCollapse",
                             "MainActivity.PIDE_ESCUCHAR", "android.service.quicksettings.TileService")
                 if x not in panel_txt]
    if ".Panel" not in MAN:
        falla("2.4.1 · baldosín", "el manifiesto no declara `android:name=\".Panel\"`")
    elif sin_panel:
        falla("2.4.1 · baldosín", f"en `Panel.java` falta {', '.join(sin_panel)}")
    elif re.search(r"unlockAndRun\(\s*[A-Za-z_][A-Za-z0-9_]*\s*\)", panel_txt):
        # Medido en el run rojo de `v0.2.26-demo` (39820927537): la firma pública es
        # `unlockAndRun(Runnable)`, y pasarle el `PendingIntent` —que es lo que uno
        # «recuerda» de los baldosines— da «PendingIntent cannot be converted to
        # Runnable». `javac` lo para, pero lo para seis minutos después.
        falla("2.4.1 · baldosín", "`unlockAndRun` recibe un `Runnable`, no un `PendingIntent`: "
                                 "hay que escribir `unlockAndRun(() -> …)`")
    elif "unlockAndRun(() ->" not in panel_txt:
        falla("2.4.1 · baldosín", "sin `unlockAndRun(() -> …)` el toque con la pantalla bloqueada se pierde")
    else:
        dice_ok("2.4.1 · baldosín", "TileService público (API 24+, este App arranca en 26), "
                                    "con su `Runnable` de desbloqueo y la cara pidiendo escuchar")

# Java: las cuatro vías se traducen en `abreLoQueToque`, y las hojas que nombra
# tienen que existir en `PANTALLAS` (si no, `ir()` cae en el Orbe sin avisar).
main_txt = (APK / "src" / "com" / "cort" / "ia" / "MainActivity.java").read_text(encoding="utf-8")
main_plano = main_txt.replace("\\", "")
sin_accion = [a for a in ("android.intent.action.ASSIST", "android.intent.action.VOICE_COMMAND", *PROPIAS)
              if f'"{a}"' not in literales(main_txt)]
if sin_accion:
    falla("2.4.1 · cara abre", f"`abreLoQueToque` no conoce {', '.join(sin_accion)}: Android llama y CORT no hace nada")
else:
    hojas = sorted(set(re.findall(r'return "(equipo|charla|orbe|musica|mv|codigo)"', main_plano)))
    pantallas_js = lectura("ui", "js", "pantallas.js")
    ids = set(re.findall(r"\{ id: '(\w+)'", pantallas_js))
    fuera = [h for h in hojas if h not in ids]
    if not hojas:
        falla("2.4.1 · cara abre", "`hojaDe` no devuelve ninguna hoja: los atajos de hoja no abren nada")
    elif fuera:
        falla("2.4.1 · cara abre", f"Java pide {', '.join(fuera)} y `pantallas.js` no tiene esa pantalla")
    else:
        dice_ok("2.4.1 · cara abre", f"las cinco vías se reconocen y sus hojas ({', '.join(hojas)}) existen")

# La costura del atajo: Java lo emite, la cara lo escucha y alguien llama a `ir`.
p = puente_texto().replace("\\", "")
if '"type":"atajo"' not in p:
    falla("2.4.1 · puente", "`atajoEnLaCara` no emite `type:\"atajo\"`: el atajo se queda en Java")
else:
    pant = lectura("ui", "js", "pantallas.js")
    sin_cara = [x for x in ("ev.type !== 'atajo'", "escuchaAtajos();", "ir(id)") if x not in pant]
    if sin_cara:
        falla("2.4.1 · cara", f"en `pantallas.js` falta {', '.join(sin_cara)}: el aviso llega a ninguna parte")
    else:
        dice_ok("2.4.1 · cara", "el evento se escucha, `initPantallas` engancha el oyente y `ir` mueve la hoja")

# El auricular sin la cara delante: la sesión del reproductor tenía los `onPlay` y
# compañía, pero NO `onMediaButtonEvent`, así que el doble toque sólo vivía en
# `MainActivity` y se desactivaba en `onPause`. Y `teclaDe` tiene que seguir
# siendo accessible desde el paquete: con `private` lo pararía `javac` en el run.
rep_txt = java_limpio.get("Reproductor.java", "")
sin_toque = [x for x in ("onMediaButtonEvent", "dobleToque", "pausar();", "CortNative.enJuego()")
             if x not in rep_txt]
if sin_toque:
    falla("2.4.1 · auricular", f"`Reproductor.java` no tiene {', '.join(sin_toque)}: con la cara cerrada "
                               "el doble toque se lo queda la música y CORT no despierta")
elif re.search(r"private\s+static\s+KeyEvent\s+teclaDe", main_txt):
    falla("2.4.1 · auricular", "`MainActivity.teclaDe` volvió a ser `private`: `Reproductor` no puede leerla y javac lo canta")
elif "static KeyEvent teclaDe" not in main_txt:
    falla("2.4.1 · auricular", "`teclaDe` no es ya de paquete: las dos sesiones leerían la tecla por caminos distintos")
else:
    dice_ok("2.4.1 · auricular", "la sesión del reproductor caza el segundo toque, pausa y abre el micro")

# ── 13 · la ronda 2.4.2: la variedad LIGERA, para aislar el aviso de Play Protect ─
# La medida que abre la ronda: el `1.1.4` de la dueña se instala y el 2.x no, con los
# MISMOS permisos gordos en los dos manifiestos. Así que la sospecha es el bulto
# nativo del oído, y la única forma de comprobarlo es un APK idéntico en todo menos
# en ese bulto. Este sector no prueba el teléfono (eso sólo puede hacerlo ella):
# prueba que la variante ligera NO es un truco, que no se le ha olvidado quitar nada
# y que el oído avisa de su ausencia en vez de quedarse callado.
comp_txt = (RAIZ / "apps/apk" / "compilar.sh").read_text(encoding="utf-8")
falta = []
if 'SIN_OIDO="${APK_SIN_OIDO:-0}"' not in comp_txt:
    falta.append("la bandera `APK_SIN_OIDO`")
if "META_MOTOR=0" not in comp_txt or "rm -rf assets/motor" not in comp_txt:
    falta.append("el `rm -rf assets/motor` con `META_MOTOR=0`")
# Las dos cosas que hacen pesado el APK tienen que estar gobernadas por META_MOTOR,
# no por HAY_MOTOR: HAY_MOTOR son los `.jar` de COMPILAR, que hacen falta incluso en
# la ligera porque `Oido.kt` se compila contra ellos.
if comp_txt.count('[ "$META_MOTOR" = "1" ] && D8_JARS') != 1:
    falta.append("el dex de Vosk/JNA gobernado por `META_MOTOR`")
if 'if [ "$META_MOTOR" = "1" ]; then\n    (cd build/motor' not in comp_txt:
    falta.append("el `zip` de las `.so` gobernado por `META_MOTOR`")
if 'variedad: LIGERA' not in comp_txt:
    falta.append("que el `-firma.txt` declare `variedad: LIGERA` (si no lo dice, la "
                 "Release engaña)")
if falta:
    falla("2.4.2 · compilar.sh", "no gobernaría de verdad la variedad ligera: " + ", ".join(falta))
else:
    dice_ok("2.4.2 · compilar.sh", "la bandera quita modelo, `.so` y clases del motor, y lo dice en el `-firma.txt`")

# Que el workflow pase la bandera y bautice el archivo: si falta una de las dos, la
# Release saca UN APK y la prueba no se puede hacer.
wf_txt = (RAIZ / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
sin_wf = [x for x in ('APK_SIN_OIDO: "1"', "-ligero.apk", "-ligero-firma.txt") if x not in wf_txt]
if sin_wf:
    falla("2.4.2 · pipeline", f"en `build.yml` no está {', '.join(sin_wf)}: la variedad ligera no llegaría a la Release")
else:
    dice_ok("2.4.2 · pipeline", "compila las dos variedades y sube las dos con su firma")

# Y que el instalador de script no se equivoque de envase: la API de Releases enumera
# los archivos en el orden en que se subieron, y el `‑ligero` sale ANTES que el
# completo. Si `scripts/instala-apk.sh` volviera a buscar «el primer .apk», la dueña
# se instalaría por USB el que no oye sin nube creyendo que es el de siempre.
ins_txt = (RAIZ / "scripts" / "instala-apk.sh").read_text(encoding="utf-8")
if '("-ligero" in n) == ligero' not in ins_txt:
    falla("2.4.2 · instala-apk.sh", "no filtra por variedad: bajaría el ligero por defecto")
elif "--ligero) VARIEDAD=ligero" not in ins_txt or "VARIEDAD=completo" not in ins_txt:
    falla("2.4.2 · instala-apk.sh", "no tiene la bandera `--ligero` ni el defecto `completo`")
else:
    dice_ok("2.4.2 · instala-apk.sh", "por defecto baja el completo y `--ligero` pide el envase sin oído")

# La versión por defecto del script y la del workflow tienen que ser la misma, o el
# `versionCode` del APK publicado no es el que dice la hoja de la Release.
m_comp = re.search(r'APK_VERSION="\$\{APK_VERSION:-([0-9.]+)\}"', comp_txt)
m_wf = re.search(r'APK_VERSION: "([0-9.]+)"', wf_txt)
if not m_comp or not m_wf or m_comp.group(1) != m_wf.group(1):
    falla("2.4.2 · versión", f"`compilar.sh` dice {m_comp.group(1) if m_comp else '?'} y "
                             f"`build.yml` dice {m_wf.group(1) if m_wf else '?'}: un APK "
                             "publicado con el nombre de otra")
else:
    dice_ok("2.4.2 · versión", f"las dos partes nombran {m_comp.group(1)}")

# Y que la ausencia del motor se DIGA: sin esto, la hoja Equipo quedaría en
# «sin-arrancar» para siempre y la dueña no sabría si es la variedad ligera o un fallo.
cuerpo = java_limpio.get("CortNative.java", "")
# `java_limpio` quita también los literales, y el `sin-modelo` vive dentro de uno (es
# el JSON que se manda a la cara), así que esa parte se mira en el archivo crudo.
cuerpo_crudo = (APK / "src" / "com" / "cort" / "ia" / "CortNative.java").read_text(encoding="utf-8")
sin_aviso = [x for x in ("sinOidoPropio", "catch (Throwable motorFuera)") if x not in cuerpo]
sin_aviso += [x for x in (r'\"sin-modelo\"',) if x not in cuerpo_crudo]
if sin_aviso:
    falla("2.4.2 · aviso", f"`CortNative.java` no informa de la variedad ligera: falta {', '.join(sin_aviso)}")
elif "sin-modelo" not in (RAIZ / "ui" / "js" / "telefono.js").read_text(encoding="utf-8"):
    falla("2.4.2 · aviso", "la cara no tiene frase para `sin-modelo`: pintaría la palabra cruda")
elif 'estado = "sin-modelo"' not in (APK / "src" / "com" / "cort" / "ia" / "Oido.kt").read_text(encoding="utf-8"):
    falla("2.4.2 · aviso", "`Oido.kt` ya no emite `sin-modelo` cuando el modelo no está en los assets")
else:
    dice_ok("2.4.2 · aviso", "sin motor: `Oido` lo dice, `CortNative` lo resume y la cara lo traduce")

# La auditoría no puede afirmar que hay cuatro `.so` en un APK que no tiene ninguna.
if "if so:" not in (RAIZ / "scripts" / "audita-apk.sh").read_text(encoding="utf-8"):
    falla("2.4.2 · auditoría", "`audita-apk.sh` sigue describiendo librerías nativas aunque no haya: "
                               "el `-firma.txt` mentiría en la variedad ligera")
else:
    dice_ok("2.4.2 · auditoría", "el `-firma.txt` distingue completo de ligero sin mentir")


# ── 14 · la ronda 2.5: los dos PERFILES del manifiesto ───────────────────────
# La medida que abre la ronda, con el método de `apps/apk/perfil.py` (leer la
# charca UTF-16 del `AndroidManifest.xml` binario) sobre los tres APK que hay en el
# mismo disco de la dueña:
#
#   CORT-IA-1.1.0   13 permisos · 0 servicios BIND_*   se instala
#   CORT-IA-1.1.4   13 permisos · 0 servicios BIND_*   se instala
#   CORT-IA-2.4.2   28 permisos · 4 BIND_* en 5 servicios   BLOQUEADO
#
# Con esto cae también la segunda explicación cómoda: el `-ligero` de la 2.4.2 pesa
# 1,6 MB, no lleva ni una `.so` ni el modelo, y se bloquea igual que el de 47 MB. El
# peso no era. Este sector no prueba el teléfono (eso sólo puede hacerlo ella):
# prueba que el recorte existe, que se ejecuta de verdad, que el `nucleo` no deja
# NINGUNA de las cadenas que delatan, y que la cara no ofrece una puerta que su
# manifiesto no declaró.
import importlib.util as _ilu
import difflib as _difflib
import xml.etree.ElementTree as _ET

perfil_py = APK / "perfil.py"
_espec = _ilu.spec_from_file_location("perfil", perfil_py) if perfil_py.exists() else None
if _espec:
    _modulo = _ilu.module_from_spec(_espec)
    _espec.loader.exec_module(_modulo)
    PERFIL_DELATORES = list(_modulo.DELATORES)
else:
    PERFIL_DELATORES = []
if not perfil_py.exists():
    falla("2.5 · perfil.py", "no existe: no se puede generar el manifiesto del núcleo")
else:
    salidas = {}
    rompio = []
    for per in ("completo", "nucleo"):
        r = subprocess.run([sys.executable, str(perfil_py), "--perfil", per],
                           capture_output=True, text=True)
        if r.returncode != 0:
            rompio.append(f"{per} (salió {r.returncode}: {(r.stderr or '').strip()[:90]})")
        salidas[per] = r.stdout
    if rompio:
        falla("2.5 · perfil.py", "no genera el manifiesto: " + "; ".join(rompio))
    else:
        dice_ok("2.5 · perfil.py", "los dos perfiles se generan y validan como XML")

        sin_c = lambda t: re.sub(r"<!--.*?-->", "", t, flags=re.S)   # aapt2 no copia comentarios
        # 1. `completo` tiene que ser lo de siempre: la superficie entera, sin recortar.
        del_ok = [d for d in PERFIL_DELATORES if d in sin_c(salidas["completo"])]
        # 2. `nucleo` no puede dejar SOBRAR ninguna.
        del_malo = [d for d in PERFIL_DELATORES if d in sin_c(salidas["nucleo"])]
        if del_malo:
            falla("2.5 · nucleo", "el recorte deja la superficie privilegiada dentro: "
                                  + ", ".join(del_malo))
        elif len(del_ok) != len(PERFIL_DELATORES):
            falla("2.5 · completo", f"el perfil completo perdió {len(PERFIL_DELATORES) - len(del_ok)} "
                                    "de las cadenas que debe conservar: el APK de siempre cambiaría")
        else:
            dice_ok("2.5 · recorte", f"las {len(PERFIL_DELATORES)} cadenas privilegiadas están en "
                                     "`completo` y cero en `nucleo`")
        # 3. Los servicios: en `completo` los seis; en `nucleo` sólo el reproductor.
        servicios_malos = []
        for per, esperado in (("completo", 6), ("nucleo", 1)):
            n = len(re.findall(r"<service\b", sin_c(salidas[per])))
            if n != esperado:
                servicios_malos.append(f"{per} tiene {n} (tienen que ser {esperado})")
        if servicios_malos:
            falla("2.5 · servicios", "; ".join(servicios_malos))
        else:
            dice_ok("2.5 · servicios", "seis en el completo, uno (`.Reproductor`) en el núcleo")
        # 4. La meta-datos del perfil, que es lo que lee `capacidades()`.
        sin_meta = [per for per in ("completo", "nucleo")
                    if f'android:name="com.cort.ia.PERFIL" android:value="{per}"'
                    not in sin_c(salidas[per])]
        if sin_meta:
            falla(f"2.5 · meta-datos {', '.join(sin_meta)}", "el manifiesto no declara su perfil: "
                  "`capacidades()` adivinaría y la cara ofrecería puertas cerradas")
        else:
            dice_ok("2.5 · meta-datos", "cada envase lleva escrito dentro cuál es su perfil")
        # 5. Ningún marcador `PERFIL-DESDE/HASTA` sobrevive en la salida. Si uno
        #    quedara, la hoja publicada llevaría dentro las instrucciones del recorte
        #    y recortar dos veces se convertiría en otra cosa.
        superviven = [per for per in ("completo", "nucleo") if "PERFIL-" in salidas[per]]
        if superviven:
            falla("2.5 · marcadores", "dejan sus propias marcas en la salida ("
                                      + ", ".join(superviven) + "): el segundo recorte "
                                      "no encontraría regiones que cortar")
        else:
            dice_ok("2.5 · marcadores", "los seis `PERFIL-DESDE/HASTA` no aparecen en ningún manifiesto generado")
        # 6. LA PRUEBA DURA DE LA RONDA. El envase `completo` no puede ser un
        #    manifiesto nuevo: tiene que ser EL MISMO que ella ya tiene, y lo único
        #    que lo distingue es la línea del perfil. Se reconstruye la fuente por
        #    fuera (sin llamar a `perfil.py`: quitar las seis líneas de marcador y
        #    clavarse la meta-datos) y se compara BYTE A BYTE.
        fuente = (APK / "AndroidManifest.xml").read_text(encoding="utf-8")
        ref = "".join(l for l in fuente.splitlines(keepends=True) if "PERFIL-" not in l)
        corte = ref.index(">", ref.find("<application")) + 1
        ref = (ref[:corte] + "\n        <meta-data "
               'android:name="com.cort.ia.PERFIL" android:value="completo" />' + ref[corte:])
        if ref != salidas["completo"]:
            delta = [l for l in _difflib.unified_diff(ref.splitlines(),
                                                      salidas["completo"].splitlines(),
                                                      lineterm="")
                     if l[:1] in "+-" and l[:3] not in ("+++", "---")]
            falla("2.5 · completo", f"no reproduce el manifiesto de siempre: {len(delta)} "
                                    f"renglones de diferencia ({delta[:3]})")
        else:
            dice_ok("2.5 · completo", "idéntico al manifiesto publicado hoy, más la única "
                                      "línea nueva: la meta-datos del perfil")
        # 7. La trampa del `--origen`: recortar un fichero que ya lleva la etiqueta
        #    puesta tiene que REESCRIBIR el valor, no respetar el del recorte anterior.
        #    Sin esto, un `nucleo` generado desde `manifest-completo.xml` saldría
        #    diciendo `completo`, que es la mentira que esta línea existe para evitar.
        reconvertido = _modulo.pon_perfil(salidas["completo"], "nucleo")
        if 'android:value="nucleo"' not in reconvertido or 'android:value="completo"' in reconvertido:
            falla("2.5 · meta-datos", "no reescribe el perfil pedido sobre uno ya marcado")
        else:
            dice_ok("2.5 · meta-datos", "el valor siempre es el del recorte pedido, no el del fichero de entrada")

# Que el recorte LLEGUE al aapt2: si `compilar.sh` siguiera pasando el manifiesto del
# repo, los dos APK de la Release serían idénticos y la prueba no se podría hacer.
if 'PERFIL="${APK_PERFIL:-completo}"' not in comp_txt or '--manifest "$MANIFIESTO"' not in comp_txt:
    falla("2.5 · compilar.sh", "no gobierna el perfil hasta `aapt2 link`: "
                               "`APK_PERFIL` o `--manifest \"$MANIFIESTO\"` no están")
elif "python3 perfil.py --perfil" not in comp_txt:
    falla("2.5 · compilar.sh", "no llama a `perfil.py`: el `-firma.txt` diría un perfil que no se cortó")
elif 'echo "perfil: $PERFIL' not in comp_txt:
    falla("2.5 · compilar.sh", "el `-firma.txt` no declara el perfil del archivo")
else:
    dice_ok("2.5 · compilar.sh", "`APK_PERFIL` corta el manifiesto, lo pasa a `aapt2` y lo declara en la hoja")

# El pipeline tiene que compilar los TRES envases y subirlos con su hoja: con uno de
# ellos la prueba del teléfono no se puede hacer.
sin_wf25 = [x for x in ('APK_PERFIL: "nucleo"', "-nucleo.apk", "-nucleo-firma.txt",
                        'APK_PERFIL: "nucleo"', "nucleo-ligero.apk") if x not in wf_txt]
if sin_wf25:
    falla("2.5 · pipeline", f"en `build.yml` no está {', '.join(set(sin_wf25))}: "
                            "la Release no subiría el núcleo y no hay prueba que hacer")
else:
    dice_ok("2.5 · pipeline", "compila completo, núcleo y núcleo-ligero, y sube los tres con su hoja")

# Y la cara tiene que saber qué lleva instalado. La cadena que se lee del manifiesto
# y las tres puertas que se niegan en el núcleo.
if r'"com.cort.ia.PERFIL"' not in cuerpo_crudo or "public String capacidades()" not in cuerpo_crudo:
    falla("2.5 · puente", "`CortNative.java` no expone `capacidades()` ni lee la meta-datos del perfil")
else:
    dice_ok("2.5 · puente", "`capacidades()` devuelve el perfil del archivo instalado")
puente_js = (RAIZ / "ui" / "js" / "android-bridge.js").read_text(encoding="utf-8")
if "window.CORTcapaz" not in puente_js or "window.CORTperfil" not in puente_js:
    falla("2.5 · cara", "`android-bridge.js` no define `CORTcapaz`/`CORTperfil`")
elif "caps[puerta] !== false" not in puente_js:
    falla("2.5 · cara", "`CORTcapaz` no es generosa por defecto: en el PC o con un APK "
                        "anterior a la 2.5 cerraría puertas que sí existen")
else:
    dice_ok("2.5 · cara", "`CORTcapaz` consulta el perfil y, si no puede mirar, dice `true`")
hud_txt = (RAIZ / "ui" / "js" / "hud.js").read_text(encoding="utf-8")
sin_hud = [x for x in ("CORTcapaz('avisos')", "CORTcapaz('asistente')", "CORTcapaz('llamadas')")
           if x not in hud_txt]
if sin_hud:
    falla("2.5 · cara", "en el núcleo la cara seguiría ofreciendo " + ", ".join(sin_hud))
else:
    dice_ok("2.5 · cara", "avisos, asistente y llamadas se niegan con su frase, no con un botón mudo")
tel_txt = (RAIZ / "ui" / "js" / "telefono.js").read_text(encoding="utf-8")
if "const PUERTAS" not in tel_txt or "CORTcapaz(puerta)" not in tel_txt:
    falla("2.5 · cara", "`puede()` de `telefono.js` no consulta el perfil: la hoja Equipo "
                        "prometería agenda y contactos en el núcleo")
elif "envase " not in tel_txt:
    falla("2.5 · cara", "la barra de Equipo no dice qué envase está instalado; con tres APK "
                        "en la Release la dueña no puede saber cuál tiene delante")
else:
    dice_ok("2.5 · cara", "la hoja Equipo dice «envase nucleo/completo» y cierra sus puertas")

# La auditoría publicada tiene que SEGUIR midiendo el binario, no el texto del repo:
# es la única prueba de que el recorte llegó al archivo que se instala.
aud_txt = (RAIZ / "scripts" / "audita-apk.sh").read_text(encoding="utf-8")
sin_aud = [x for x in ("AndroidManifest.xml", ".permission.BIND_", "perfil declarado",
                       "el perfil nucleo salió con") if x not in aud_txt]
if sin_aud:
    falla("2.5 · auditoría", "`audita-apk.sh` no lee el perfil ni sus servicios del APK final: "
                             + ", ".join(sin_aud))
else:
    dice_ok("2.5 · auditoría", "los permisos, los `BIND_*` y el perfil se leen del binario y "
                                "un núcleo con servicios privilegiados pone el pipeline rojo")

# Y el instalador de script no puede equivocarse de envase: la Release lista los
# archivos en el orden en que se subieron.
if '"-nucleo" in n' not in ins_txt or "--nucleo) PERFIL=nucleo" not in ins_txt:
    falla("2.5 · instala-apk.sh", "no distingue el núcleo: bajaría el envase equivocado")
else:
    dice_ok("2.5 · instala-apk.sh", "por defecto el de siempre y `--nucleo` el recortado")


# ── [15] F7l · el clima por ciudad y el registro de código, cosidos por las tres capas
# La prueba vive en `scripts/prueba-clima.py` (sin red); aquí se comprueba el COSTURE,
# que es lo que un cambio de cualquier capa puede romper: que la puerta del backend
# acepte la ciudad, que la cara la ofrezca y la guarde, que las tres IAs reciban el
# `modo`, y que la prueba nueva esté montada en el pipeline.
clima_py = RAIZ / "scripts" / "prueba-clima.py"
if not clima_py.exists():
    falla("2.5 · F7l · prueba", "no existe `scripts/prueba-clima.py`: el clima por ciudad "
                                "y el registro de código quedarían sin probar")
elif "python3 scripts/prueba-clima.py" not in wf_txt:
    falla("2.5 · F7l · pipeline", "`build.yml` no corre `prueba-clima.py`: la suite existiría "
                                  "y nadie la ejecutaría")
else:
    dice_ok("2.5 · F7l", "la suite existe y está montada en el trabajo `apk`")
backend_txt = (RAIZ / "backend" / "app" / "main.py").read_text(encoding="utf-8")
if "def weather(lugar: str" not in backend_txt or "lugar=lugar.strip()" not in backend_txt:
    falla("2.5 · F7l · puerta", "`GET /api/weather` no admite `?lugar=`: la cara no podría "
                                "pedir una ciudad")
else:
    dice_ok("2.5 · F7l · puerta", "/api/weather espera `lugar` y lo pasa a `sensors.weather`")
if "id=\"pf-ciudad\"" not in hud_txt or "'ciudad'" not in hud_txt:
    falla("2.5 · F7l · cara", "la ventana PERFIL no tiene campo `ciudad`: la preferencia "
                              "que lee `brain._perfil_clave` no se puede escribir")
elif "id=\"wx-ciudad\"" not in hud_txt or "/api/weather?lugar=" not in hud_txt:
    falla("2.5 · F7l · cara", "02 · Entorno no pide ni envía la ciudad: el panel seguiría "
                              "atado a la IP")
else:
    dice_ok("2.5 · F7l · cara", "hay caja de ciudad en Entorno, campo en Perfil y se guarda por /api/profile")
cerebro_txt = (RAIZ / "backend" / "app" / "brain.py").read_text(encoding="utf-8")
usos = cerebro_txt.count("system_prompt(modo)")
if usos < 3:
    falla("2.5 · F7l · cerebro", f"algún proveedor no recibe la consigna del registro "
                                 f"(se ven {usos} usos de `system_prompt(modo)`, tienen que ser 3)")
elif 'modo = "coder" if coder else "asistente"' not in cerebro_txt:
    falla("2.5 · F7l · cerebro", "`think()` no decide el registro: `es_programacion` existiría sin efecto")
elif "and not coder" not in cerebro_txt:
    falla("2.5 · F7l · cerebro", "el mando local no se salta en las frases de código: "
                                 "«hazme una app del clima en Python» se contestaría con el termómetro")
else:
    dice_ok("2.5 · F7l · cerebro", "los tres proveedores reciben `modo` y el código no pasa por el sensor")


# ── [16] F7m · la boca del escritorio: voz por el núcleo, cosida por las tres capas
# Medido el 2026-10-22 con `scripts/sonda-voz.html` en el Chromium de este equipo:
# `speechSynthesis` responde pero da CERO voces, y `voiceschanged` dispara con la
# lista vacía. O sea: en Linux la cara fingía hablar (saltaba su `onend`) y no se
# oía nada, y los deslizadores de 07 · Perfil no mandaban en nada. Desde entonces la
# boca se ELIGE y el timbre viaja en un POST, así que hay tres capas que tienen que
# seguir nombrándose lo mismo: si una cambia de nombre, la otra calla en silencio.
# Se exige la LÍNEA que invoca la suite, no el simple nombre: el nombre también
# sale en el comentario y en la anotación de `::error::`, y con buscarlo suelto una
# suite quitada del pipeline seguiría dando por cosida. Medido con una mutación.
voz_suite = RAIZ / "scripts" / "prueba-voz.py"
if not voz_suite.exists():
    falla("F7m · prueba", "no existe `scripts/prueba-voz.py`: la boca del escritorio quedaría sin probar")
elif "python3 scripts/prueba-voz.py" not in wf_txt:
    falla("F7m · pipeline", "`build.yml` no corre `prueba-voz.py`: la suite existiría y nadie la ejecutaría")
else:
    dice_ok("F7m", "la suite de la boca existe y está montada en el trabajo `apk`")
nucleo_voz = (RAIZ / "backend" / "app" / "voz.py").read_text(encoding="utf-8")
if "import voz" not in backend_txt or '@app.get("/api/voice")' not in backend_txt \
        or '@app.post("/api/voice/say")' not in backend_txt:
    falla("F7m · puerta", "`main.py` no monta /api/voice y /api/voice/say: la cara no tendría boca que preguntar")
else:
    dice_ok("F7m · puerta", "el núcleo ofrece /api/voice (qué hay) y /api/voice/say (el WAV)")
campos = [c for c in ("texto:", "voz:", "tono:", "velocidad:") if c not in backend_txt]
if campos:
    falla("F7m · contrato", "a `Decir` le faltan " + ", ".join(campos) +
                            ": la cara manda esos cuatro campos y el pydantic los descartaría en silencio")
else:
    dice_ok("F7m · contrato", "texto/voz/tono/velocidad entran por la puerta y salen por `voz.sintetiza`")
if 'media_type="audio/wav"' not in backend_txt or "503" not in backend_txt:
    falla("F7m · puerta", "el audio no se declara WAV, o el fallo no viaja con código: la cara no sabría distinguirlo")
else:
    dice_ok("F7m · puerta", "responde audio/wav y, si no puede, 503 con el motivo con nombre")
voice_txt = (RAIZ / "ui" / "js" / "voice.js").read_text(encoding="utf-8")
if "'nativa'" not in voice_txt or "'navegador'" not in voice_txt or "'núcleo'" not in voice_txt \
        or "'muda'" not in voice_txt:
    falla("F7m · boca", "`voice.js` no elige entre las cuatro bocas: volvería a suponer que el navegador siempre habla")
else:
    dice_ok("F7m · boca", "nativa (teléfono) · navegador (Windows/Mac) · núcleo (Linux) · muda (se avisa)")
if "h.onError && h.onError('sin-boca')" not in voice_txt or "'sin-boca'" not in hud_txt:
    falla("F7m · aviso", "sin boca la cara callaría en silencio otra vez: tiene que salir el error por nombre")
elif "boca:" not in voice_txt or "startsWith('boca:')" not in hud_txt:
    falla("F7m · aviso", "el fallo del motor no llega a la consola: `voz.py` dice `no-suena` y nadie lo lee")
else:
    dice_ok("F7m · aviso", "el silencio tiene nombre en la consola (`sin-boca`, `boca:no-suena`…)")
if "api: () => API" not in hud_txt or "voice.descubreMotor()" not in hud_txt:
    falla("F7m · cara", "la cara no pregunta al núcleo qué boca hay (o lo pregunta a una URL fija): "
                        "en Linux el desplegable saldría vacío otra vez")
elif 'id="pf-voz-nota"' not in hud_txt or "boca === 'muda'" not in hud_txt:
    falla("F7m · cara", "07 · Perfil no dice qué boca está hablando: sin esa línea un equipo sin motor "
                        "parece un CORT roto en vez de un CORT sin espeak-ng")
else:
    dice_ok("F7m · cara", "pregunta el motor al arrancar, repinta el desplegable y dice la boca en uso")
if "voz: cfg.voice" not in voice_txt or "tono: cfg.pitch" not in voice_txt or "velocidad: cfg.rate" not in voice_txt:
    falla("F7m · viaje", "el POST del WAV no se arma con los tres mandos del Perfil: "
                         "los deslizadores volverían a ser decorativos")
elif "URL.revokeObjectURL" not in voice_txt:
    falla("F7m · memoria", "el `object URL` del WAV no se libera: en 1,8 GiB de RAM cada frase dejaría audio colgando")
else:
    dice_ok("F7m · viaje", "timbre, tono y velocidad salen del Perfil y el audio se suelta al terminar")
# La ruta del teléfono no se toca: sigue hablando por el puente, con los cinco argumentos.
if "N.speak(t.slice(0, 3800), id, cfg.voice || '', +cfg.pitch || 0.82, +cfg.rate || 1)" not in voice_txt:
    falla("F7m · teléfono", "la llamada a `CortNative.speak()` cambió de forma: el puente espera "
                            "(texto, id, voz, tono, velocidad) y el APK se quedaría mudo")
else:
    dice_ok("F7m · teléfono", "el APK sigue con su `TextToSpeech` de siempre: la boca nueva es sólo el escritorio")
cristal = (RAIZ / "desktop" / "main.cjs").read_text(encoding="utf-8")
if "autoplay-policy" not in cristal or "no-user-gesture-required" not in cristal:
    falla("F7m · escritorio", "Electron sigue con la política de autoplay de Chromium: el `<audio>` del "
                              "saludo se corta antes de empezar y la boca nueva no se oye")
else:
    dice_ok("F7m · escritorio", "Electron permite hablar sin gesto previo (saludo, dictado, avisos)")


# ── [17] F8 · la cara ordenada: el gesto no se traga los botones, la música vive en
#             la esquina y el chat se acuerda (docs/PLAN-MAESTRO.md, ronda F8)
# Cuatro quejas medidas en el código de la dueña («se traban los botones», «la bandeja
# de abajo está atravesada», «en el chat no puedo seleccionar», «el historial no
# aparece»). Son puramente de `ui/` más una puerta que ya existía, así que lo que se
# comprueba aquí es la COSTURA: el JS crea unos ids y el CSS los viste; la cara pide
# `/api/history` y el núcleo lo sirve. Si un nombre se cambia en una capa sin cambiarlo
# en la otra, el botón aparece sin forma o el historial se queda vacío sin decir por qué.
f8_js = scr_txt if 'scr_txt' in dir() else (RAIZ / "ui" / "js" / "pantallas.js").read_text(encoding="utf-8")
f8_css = (RAIZ / "ui" / "css" / "hud.css").read_text(encoding="utf-8")
if "NO_ES_GESTO" not in f8_js or "button" not in f8_js:
    falla("F8 · gesto", "`montaGesto()` no excluye los controles: deslizar el pulgar sobre el play "
                        "cambiaba de hoja en vez de reproducir (la causa de «se traban los botones»)")
else:
    for b in (".mu-transporte", "#mic", "#dock", "#repro-pildora"):
        if b not in f8_js:
            falla("F8 · gesto", f"`{b}` no está en la lista de no-gesto: ahí vuelve a comerse el deslizamiento")
    dice_ok("F8 · gesto", "el deslizamiento de hojas no arranca desde ningún botón ni desde la píldora")
if "montaPildora" not in f8_js or "pintaPildora" not in f8_js:
    falla("F8 · píldora", "no existe la píldora de música: la bandeja del dock seguiría cruzando la pantalla")
else:
    dice_ok("F8 · píldora", "la píldora existe y se pliega con su ✕ hasta que la pista pare")
# Se CUENTAN las llamadas (`(?<!function )` deja fuera la definición: buscar la
# subcadena a secas daba verde con la píldora montada y nunca repintada, medido con
# una mutación que borraba la llamada de `pintaProgreso`).
llamadas_pint = len(re.findall(r"(?<!function )\bpintaPildora\s*\(", f8_js))
llamadas_mont = len(re.findall(r"(?<!function )\bmontaPildora\s*\(", f8_js))
if llamadas_mont < 1:
    falla("F8 · píldora", "`montaPildora()` está definido pero nadie lo llama: no hay píldora en pantalla")
elif llamadas_pint < 3:
    falla("F8 · píldora", f"`pintaPildora()` se llama {llamadas_pint} vez/veces y hacen falta 3 "
                          "(el aviso de Java, el cambio de hoja y el arranque): con una menos la píldora "
                          "se queda con la canción anterior o no aparece hasta que algo suene")
elif not re.search(r"pintaPildora\(estadoMusica\(\)\)", f8_js):
    falla("F8 · píldora", "al entrar en una hoja no se repinta con el estado que ya trae el servicio: "
                          "volver a la app con la pista sonando dejaría la esquina vacía")
else:
    dice_ok("F8 · píldora", "se monta una vez y se repinta desde los tres sitios (aviso · hoja · arranque)")
if "actual !== 'musica' && actual !== 'mv'" not in f8_js:
    falla("F8 · píldora", "la píldora no se apaga en Música y MV: se ENCIMARÍA dos mandos del mismo "
                          "reproductor, y apagar uno desde el otro no es una interfaz, es una trampa")
else:
    dice_ok("F8 · píldora", "fuera de Música/MV se ve; dentro no, y en modo juego tampoco")
ids_js = set(re.findall(r"#?\b(rp-[a-z]+|repro-pildora)\b", f8_js))
huérfanos = sorted(i for i in ids_js if "#" + i not in f8_css)
creados = set(re.findall(r'id="(rp-[a-z]+)"', f8_js)) | {"repro-pildora"}
if not ids_js:
    falla("F8 · píldora", "la cara no crea ningún id de la píldora (cambió la forma del `innerHTML`)")
elif huérfanos:
    falla("F8 · css", "la cara menciona " + ", ".join("#" + i for i in huérfanos) +
                      " y `hud.css` no lo viste: saliría como texto suelto sin forma ni lugar, "
                      "o `querySelector` devolvería `null` y el montaje se caería entero")
elif creados != ids_js:
    falla("F8 · píldora", "la cara menciona " + ", ".join(sorted(ids_js - creados)) +
                          " sin crearlo con `id=\"…\"` (o crea algo que no selecciona): ese botón existe "
                          "en el CSS y en nada más, así que pulsarlo no es pulsar nada")
else:
    dice_ok("F8 · css", f"los {len(ids_js)} ids de la píldora se crean, se seleccionan y tienen su regla")
if "$('play').onclick = alternaReproduccion" not in f8_js:
    falla("F8 · transporte", "el play del transporte volvió a ir por su cuenta: dos mandos del mismo "
                             "play/pausa que un día mandan distinto")
else:
    dice_ok("F8 · transporte", "píldora y transporte usan la MISMA función de play/pausa")
# EL BUG QUE ESTA RONDA SACÓ A LA LUZ (medido con `ui/sonda-carita.html`, 2026-10-22):
# `enganchaTransporte` armaba el selector como `'#' + p + s`, o sea `#muplay`, mientras
# `transporteHTML` escribe los ids con guion (`mu-play`). El primer `$('play').onclick`
# devolvía `null` y saltaba un `TypeError` DENTRO de `initPantallas`, que es el sitio al
# que el CSS llama «la cara de siempre se queda intacta»: sin la clase
# `pantallas-montadas` no se monta NINGUNA hoja nueva. Así que desde la ronda 2.0
# (5faf8fe) el teléfono mostraba la tira de botones vieja y ningún botón del
# reproductor hacía nada — que es, palabra por palabra, «se traban los botones».
# Se comprueban los dos lados de la costura, no el arreglo concreto.
ayudante = re.search(r"const \$ = s => donde\.querySelector\((.*?)\);", f8_js)
if not ayudante:
    falla("F8 · transporte", "ya no se reconoce el ayudante `$` de `enganchaTransporte`: la comprobación "
                             "del guion se quedaría ciega y el bug volvería colado")
elif "'#' + p + '-' + s" not in ayudante.group(1):
    falla("F8 · transporte", f"el ayudante `$` arma los selectores como `{ayudante.group(1)}`: sin el GUION "
                             "sale `#muplay`, que no existe, el primer `onclick` revienta y se lleva la cara "
                             "nueva entera (así estaba desde la ronda 2.0)")
else:
    dice_ok("F8 · transporte", "`$` arma `#mu-play` / `#mv-play`, que son los ids que de verdad se pintan")
plantilla = set(re.findall(r'id="\$\{p\}(-[a-z0-9-]+)"', f8_js))
duros = set(re.findall(r"\$\('([a-z0-9-]+)'\)\.(?:onclick|oninput)", f8_js))
sin_id = sorted(g for g in duros if '-' + g not in plantilla)
if not duros or not plantilla:
    falla("F8 · transporte", "la cara dejó de reconocer los botones del transporte (cambió la forma del "
                             "`$()` o del `innerHTML`): la comprobación ya no ve nada y no sirve")
elif sin_id:
    falla("F8 · transporte", "`enganchaTransporte` engancha " + ", ".join("$('" + g + "')" for g in sin_id) +
                             " pero `transporteHTML` no pinta ese id: el `null` del primer botón tira "
                             "`initPantallas` y deja el teléfono sin hojas nuevas")
else:
    dice_ok("F8 · transporte", f"los {len(duros)} botones enganchados están pintados por la plantilla")
if '@app.get("/api/history")' in backend_txt:
    if "/api/history" not in f8_js:
        falla("F8 · charla", "el núcleo sirve /api/history y la cara no lo pide nunca: la hoja se abre en "
                             "blanco aunque CORT se acuerde (así estaba antes de esta ronda)")
    else:
        dice_ok("F8 · charla", "la Charla trae el historial del núcleo cuando llega vacía")
else:
    falla("F8 · charla", "`/api/history` ya no está en `main.py`: la cara pediría un historial que no existe")
if "html.mobile #log" not in f8_css or "#termlog" not in f8_css:
    falla("F8 · seleccionar", "`user-select:none` del móvil sigue tapando la consola: la dueña no puede "
                              "copiar lo que leyó (su queja textual)")
else:
    dice_ok("F8 · seleccionar", "la consola y la terminal del móvil se pueden seleccionar y copiar")


# ── [18] F9 · la cara partida en apps: UN botón en el orbe, Lark en Música y
#             Gemini en Charla (docs/PLAN-MAESTRO.md, ronda F9)
# La dueña pidió dos cosas concretas: que el orbe quede sólo con el botón del menú, y
# que cada apartado parezca OTRA app —Música calco de Lark Player, Charla calco de
# Gemini/Qoder, con su modelo, sus modos y su adjunto—. Todo eso vive en `ui/` más una
# puerta nueva en el portátil, así que el riesgo no es de compilación sino de NOMBRES:
# el cajón lo PINTA `index.html` y lo ENCHUFA `pantallas.js`; el calco lo escribe el
# `innerHTML` y lo VISTE `css/apps.css`; y el adjunto cruza cara → `main.py` →
# `sensors.py`. Cada nombre que cambia en una capa sin cambiar en la otra es un botón
# mudo —que es, palabra por palabra, el bug del sector [17]—.
f9_js = (RAIZ / "ui" / "js" / "pantallas.js").read_text(encoding="utf-8")
f9_css = (RAIZ / "ui" / "css" / "hud.css").read_text(encoding="utf-8")
f9_ropa_ruta = RAIZ / "ui" / "css" / "apps.css"
f9_ropa = f9_ropa_ruta.read_text(encoding="utf-8") if f9_ropa_ruta.exists() else ""
f9_indice = (RAIZ / "ui" / "index.html").read_text(encoding="utf-8")
f9_hudjs = (RAIZ / "ui" / "js" / "hud.js").read_text(encoding="utf-8")
f9_vidrio = (RAIZ / "ui" / "js" / "windows.js").read_text(encoding="utf-8")
f9_sensores = (RAIZ / "backend" / "app" / "sensors.py").read_text(encoding="utf-8")
print("\n[18] F9 · el cajón de un botón, el calco de Lark y el de Gemini")

# 1 · la ropa: que exista, que esté enlazada y que vaya DESPUÉS de hud.css
if not f9_ropa:
    falla("F9 · ropa", "no existe `ui/css/apps.css` (o está vacío): el calco de Lark y de Gemini "
                       "está escrito en el JS pero no se VISTE, así que las hojas saldrían con la "
                       "ropa de siempre y la dueña no vería ninguna de las dos apps nuevas")
elif 'css/apps.css' not in f9_indice:
    falla("F9 · ropa", "`index.html` no enlaza `css/apps.css`: el JS pinta clases `lk-`/`gm-` que "
                       "ninguna hoja de estilo conoce, y una clase sin regla es texto suelto")
elif 'href="css/hud.css"' not in f9_indice or \
        f9_indice.index('href="css/hud.css"') > f9_indice.index('href="css/apps.css"'):
    falla("F9 · ropa", "`apps.css` se enlaza ANTES que `hud.css`: ganan las reglas viejas y el "
                       "calco desaparece. El orden de las dos hojas es parte del contrato")
else:
    dice_ok("F9 · ropa", f"`apps.css` ({len(f9_ropa.splitlines())} líneas) existe y va enlazada "
                         "después de `hud.css`")

# 2 · el envase: el pipeline copia `ui/` ENTERO, así que la ropa nueva viaja sola
f9_emp = (RAIZ / "apps" / "apk" / "compilar.sh").read_text(encoding="utf-8")
if "cp -r ../../ui/. assets/ui/" not in f9_emp:
    falla("F9 · envase", "`compilar.sh` ya no copia `ui/.` entero a `assets/ui/`: si la lista de "
                         "archivos pasa a ser fija, `css/apps.css` se queda fuera y el APK sale con "
                         "la cara vieja sin que ningún check se entere")
elif "sonda-*.html" not in f9_emp:
    falla("F9 · envase", "el instrumento del taller (`ui/sonda-carita.html`) vuelve a viajar dentro "
                         "del APK: se copia `ui/.` entero y la sonda se saca con el patrón "
                         "`sonda-*.html`, así que si ese `find … -delete` se borra el teléfono "
                         "engulle 26.424 B que nadie puede abrir (no hay barra de direcciones en el "
                         "`WebView`)")
else:
    dice_ok("F9 · envase", "el pipeline copia `ui/.` completo —la ropa nueva entra sin que nadie la "
                           "anuncie archivo por archivo— y descarta la sonda del taller")

# 3 · el cajón: los nodos los pinta el índice y la cara los enchufa (en los dos sentidos)
F9_DUEÑOS = ("orb-menu", "cortina", "cj-cierra", "cj-apps", "cj-ajustes")
f9_agarra = set(re.findall(r"getElementById\('([a-z0-9-]+)'\)", f9_js))
f9_sin_nodo = sorted(n for n in F9_DUEÑOS if f'id="{n}"' not in f9_indice)
f9_sin_dueño = sorted(n for n in F9_DUEÑOS if n not in f9_agarra)
if "montaNavegacion" not in f9_js:
    falla("F9 · cajón", "no existe `montaNavegacion()`: ☰, la cortina y la ✕ estarían pintados sin "
                        "un solo manejador —el botón único del orbe no abriría nada")
elif not re.search(r"(?<!function )montaNavegacion\(\);", f9_js):
    falla("F9 · cajón", "`montaNavegacion()` está definido pero nadie lo llama: ☰ queda mudo")
elif f9_sin_nodo:
    falla("F9 · cajón", "la cara enchufa " + ", ".join("#" + n for n in f9_sin_nodo) +
                        " y `index.html` no lo pinta: `getElementById` da `null`, el `onclick` no "
                        "se pone y ese botón no hace nada (el mismo silencio del sector [17])")
elif f9_sin_dueño:
    falla("F9 · cajón", "`index.html` pinta " + ", ".join("#" + n for n in f9_sin_dueño) +
                        " y la cara no lo enchufa ni lo rellena: es markup muerto en el menú")
else:
    dice_ok("F9 · cajón", f"los {len(F9_DUEÑOS)} nodos del cajón están pintados en el índice y "
                          "enchufados por la cara")

# 4 · el orbe: UN solo botón. Las dos tiras viejas no pueden seguir en el índice ni
#     seguir vivas en la cara, o el menú tendría dos puertas y el orbe seguiría lleno.
if 'id="pantalla-bar"' in f9_indice or 'id="pantalla-menu"' in f9_indice:
    falla("F9 · orbe", "`index.html` sigue pintando la barra de hojas vieja (`#pantalla-bar` / "
                       "`#pantalla-menu`): el orbe no está limpio, que es lo que se pidió")
elif 'pantalla-bar' in f9_js or 'pantalla-menu' in f9_js:
    falla("F9 · orbe", "`pantallas.js` se refiere todavía a " +
                       ", ".join(x for x in ("pantalla-bar", "pantalla-menu") if x in f9_js) +
                       ": esas hojas ya no se pintan, así que `querySelector` devuelve `null` y el "
                       "código que las usaba no corre nunca")
else:
    dice_ok("F9 · orbe", "no queda ni la barra de hojas ni el menú viejo: en el orbe sólo hay ☰")

# 5 · el dock VIAJA dentro del cajón (no se duplica) y `apps.css` lo reabre: sin esa
#     regla el menú saldría sin los botones de las ventanas de vidrio, porque `hud.css`
#     esconde `#dock` en cuanto se sale del orbe.
f9_dock = f9_indice.count('id="dock"')
if f9_dock != 1:
    falla("F9 · cajón", f"hay {f9_dock} nodos `id=\"dock\"` en el índice: `windows.js` enchufa "
                        "`#dock [data-win=…]` y siempre coge el primero, así que la otra mitad de "
                        "los botones quedaría sorda")
elif not ('id="cajon"' in f9_indice and f9_indice.index('id="cajon"') < f9_indice.index('id="dock"')):
    falla("F9 · cajón", "el `#dock` no está DENTRO de `#cajon`: las doce ventanas de vidrio siguen "
                        "fuera del menú y el cajón sale sin herramientas")
elif '#cajon #dock' not in f9_ropa:
    falla("F9 · ropa", "`apps.css` no reabre `#cajon #dock`: `hud.css` esconde el dock fuera del "
                       "orbe, así que el cajón se pintaría vacío de botones")
elif 'html.pantallas-montadas:not(.p-orbe) #dock' not in f9_css:
    falla("F9 · ropa", "cambió la regla de `hud.css` que esconde `#dock` fuera del orbe: esta "
                       "comprobación se queda ciega y hay que reescribirla a la par")
elif '#dock [data-win="' not in f9_vidrio:
    falla("F9 · cajón", "`windows.js` ya no busca sus botones dentro de `#dock`: hay que cambiar "
                        "esta costura, porque la cara los metió en el cajón contando con ello")
else:
    dice_ok("F9 · cajón", "un solo `#dock`, metido en el cajón, reabierto por apps.css y seguido "
                          "enlazando las ventanas de vidrio")

# 6 · la clase de bug que la sonda cazó en vivo (`mv-letra`): el transporte repite su
#     plantilla con prefijo, y si un id dinámico coincide con un id fijo de la cara hay
#     DOS nodos con el mismo `id`. `getElementById` devuelve el primero y el segundo se
#     pinta encima sin que nadie lo vea. Se comprueban los dos lados de la plantilla.
f9_prefijos = set(re.findall(r"transporteHTML\('([a-z]+)'\)", f9_js))
f9_sufijos = set(re.findall(r'id="\$\{p\}(-[a-z0-9-]+)"', f9_js))
f9_fijos = set(re.findall(r'id="([a-z0-9-]+)"', f9_js)) | set(re.findall(r'id="([a-z0-9-]+)"', f9_indice))
f9_choque = sorted({a + b for a in f9_prefijos for b in f9_sufijos} & f9_fijos)
if len(f9_prefijos) < 2 or len(f9_sufijos) < 10:
    falla("F9 · transporte", f"la plantilla del transporte cambió de forma ({len(f9_prefijos)} "
                             f"prefijos, {len(f9_sufijos)} ids dinámicos): la comprobación de "
                             "choques ya no ve nada y hay que reescribirla a la par")
elif f9_choque:
    falla("F9 · transporte", "el transporte pinta " + ", ".join("#" + c for c in f9_choque) +
                             " y ése es OTRO id de la cara: dos nodos con el mismo id. Así estaba "
                             "`mv-letra`, el botón de la letra montado encima de la caja de letras")
else:
    dice_ok("F9 · transporte", f"los {len(f9_sufijos)} ids del transporte × {len(f9_prefijos)} hojas "
                              f"no chocan con ninguno de los {len(f9_fijos)} ids fijos de la cara")

# 7 · el adjunto de la Charla cruza las tres capas: la cara pide `/api/lee`, el núcleo lo
#     declara y lo fía a `sensors.leer_texto` (que ya tenía su candado de rutas). Y la
#     cara no puede leer claves que el núcleo no devuelve.
f9_pide_lee = "/api/lee" in f9_js
if not f9_pide_lee:
    falla("F9 · adjunto", "la cara no pide `/api/lee`: el botón 「+」 no puede tener archivo, "
                          "sería un adjunto de mentira")
elif '@app.get("/api/lee")' not in backend_txt:
    falla("F9 · adjunto", "la cara pide `/api/lee` y `main.py` no lo sirve: el 404 se traduce en "
                          "«el portátil no contestó a lo de leer el archivo», que es mentira")
elif "leer_texto" not in backend_txt or "def leer_texto" not in f9_sensores:
    falla("F9 · adjunto", "`/api/lee` no se apoya en `sensors.leer_texto`: o se duplicó el lectura "
                          "por otro lado, o se perdió el candado de las raíces permitidas")
else:
    cuerpo_lee = f9_sensores.split("def leer_texto", 1)[1].split("\ndef ", 1)[0]
    da = set(re.findall(r'"([a-z_]+)":', cuerpo_lee))
    pide = set(re.findall(r"\br\.([a-z_]+)\b",
                          f9_js.split("async function adjuntaArchivo", 1)[1]
                              .split("async function ", 1)[0]))
    de_mas = sorted(pide - da)
    if de_mas:
        falla("F9 · adjunto", "la cara lee " + ", ".join("r." + k for k in de_mas) +
                              " de `/api/lee` y `leer_texto` no devuelve esa clave: saldría "
                              "`undefined` en el mensaje de la dueña")
    else:
        dice_ok("F9 · adjunto", "`/api/lee` está en la cara, en `main.py` y en `sensors.py`, y las "
                                "claves que se leen (" + ", ".join(sorted(pide)) + ") son las que devuelve")

# 8 · el cuerpo de los POST contra los modelos de pydantic. `Nota` tiene UN campo que es
#     `texto`: la Charla lo mandaba como `text` (arreglado) y el Código también. Con el
#     nombre equivocado FastAPI contesta 422, y la cara lo cuenta como «el núcleo no dejó
#     guardarlo» —culpa del núcleo, cuando el fallo estaba escrito en el repo.
F9_MODELOS = {"chat": "Msg", "notes": "Nota", "models/use": "Modelo"}
f9_campos = {}
for f9_ruta, f9_cls in F9_MODELOS.items():
    m = re.search(r"class " + f9_cls + r"\(BaseModel\):\n((?:    \w+: [^\n]*\n)+)", backend_txt)
    f9_campos[f9_ruta] = set(re.findall(r"^    (\w+):", m.group(1), re.M)) if m else set()
if not all(f9_campos.values()):
    falla("F9 · contrato", "algún modelo del núcleo ya no se reconoce (" +
                           ", ".join(k for k, v in f9_campos.items() if not v) +
                           " sin campos): la comprobación de los POST queda ciega")
else:
    torcidos = []
    for m in re.finditer(r"fetch\((?:ctx\.api\(\)|base) \+ '(/api/[a-z/_]+)'[\s\S]{0,420}?"
                         r"body: JSON\.stringify\(\{([^}]*?)\}\)", f9_js):
        f9_ruta = m.group(1)[len("/api/"):]
        if f9_ruta not in f9_campos:
            continue
        llaves = set(re.findall(r"(\w+):", m.group(2)))
        if not llaves <= f9_campos[f9_ruta]:
            torcidos.append(f9_ruta + " manda " + ", ".join(sorted(llaves)) +
                            " y el modelo sólo tiene " + ", ".join(sorted(f9_campos[f9_ruta])))
    if torcidos:
        falla("F9 · contrato", "; ".join(torcidos))
    else:
        dice_ok("F9 · contrato", "los POST de la cara mandan exactamente los campos de `Msg`, "
                                 "`Nota` y `Modelo` (422 = «el núcleo no dejó guardarlo», mentira)")

# 9 · modos de la Charla: `Msg` sólo tiene `message`, así que el modo NO puede ser un
#     campo del cuerpo —es la instrucción que va DELANTE de la pregunta. Si alguien añade
#     el campo al backend sin cambiar la cara, esta comprobación avisa de que ya no es la
#     única forma de decir el modo.
if "CH_MODOS" not in f9_js or "pide:" not in f9_js:
    falla("F9 · modos", "no existen los modos con su instrucción (`CH_MODOS` / `pide:`): la fila "
                        "de seis botones de abajo sería decoración")
elif "modo.pide" not in f9_js.split("const envio = [", 1)[-1].split("];", 1)[0]:
    falla("F9 · modos", "`charla()` ya no pone la instrucción del modo delante de la pregunta: "
                        "elegir 「Resume」 no resumiría nada")
else:
    dice_ok("F9 · modos", "el modo viaja dentro de `message`, que es lo único que acepta `/api/chat`")

# 10 · el Escape: `hud.js` lo escucha en `document` para cerrar las ventanas de vidrio. La
#      cara tiene que ganarle el tecla en la FASE DE CAPTURA y cortar la propagación, o
#      cerrar el cajón reabriría el vidrio detrás.
if "Escape" not in f9_hudjs:
    falla("F9 · teclas", "`hud.js` ya no usa Escape: el `capture` de la cara sobra y hay que "
                         "reescribir esta comprobación")
elif "stopImmediatePropagation" not in f9_js or "{ capture: true }" not in f9_js:
    falla("F9 · teclas", "la cara no se adelanta a `hud.js` con `capture` + `stopImmediatePropagation`: "
                         "un Escape cerraría la hoja Y abriría las ventanas de vidrio a la vez")
else:
    dice_ok("F9 · teclas", "Escape lo coge primero la cara (capture) y no lo deja llegar a hud.js")


# ── [19] El entorno del runner: cada guion que Actions ejecuta tiene que poder
#         importar lo que arrastra SU cadena de `import`, no sólo lo que importa él.
# El run 39879890814 (etiqueta v0.2.30-demo) se cayó aquí, y el código no tenía nada
# que ver: `scripts/prueba-clima.py` llamaba a `brain.local_command` → `import
# local_commands` → `import psutil`. El paso instalaba `requests` y nada más, así que
# el rojo fue un `ModuleNotFoundError` que en el portátil de la dueña NO se ve nunca,
# porque ahí el `.venv` tiene todo. Esta comprobación rehace en local la cadena de
# imports de cada guion del workflow y exige que el workflow declare, en un `pip
# install`, cada paquete de terceros que hace falta —y que lo compruebe importando,
# porque un `pip install` que falla en silencio da el mismo rojo vacío—.
print("\n[19] El runner instala lo que los guiones importan")

F19_WORKFLOW = RAIZ / ".github" / "workflows" / "build.yml"
f19_yml = F19_WORKFLOW.read_text(encoding="utf-8") if F19_WORKFLOW.exists() else ""
# Los paquetes se buscan por el nombre del MÓDULO; estos dos se escriben distinto.
F19_ALIAS = {"python-dotenv": "dotenv", "pyyaml": "yaml", "pillow": "PIL"}
F19_CARPETAS = [RAIZ / "backend" / "app", RAIZ / "scripts", RAIZ / "backend", RAIZ]


def f19_local(nombre: str):
    """La ruta del módulo si es de este proyecto, o `None` (no está en `site-packages`)."""
    for f19_c in F19_CARPETAS:
        f19_p = f19_c / (nombre + ".py")
        if f19_p.exists():
            return f19_p
    return None


def f19_terceros(f19_ruta, f19_vistos) -> set:
    """Nombres que hay que instalar por `pip` para leer este archivo sin `ImportError`.

    Camina los `import` del guion y, cuando el módulo es del proyecto, entra en él:
    el bug no estaba en `prueba-clima.py`, estaba en la tercera capa de su cadena.
    """
    hace_falta = set()
    try:
        f19_arbol = ast.parse(f19_ruta.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return hace_falta
    for f19_nodo in ast.walk(f19_arbol):
        f19_nombres = []
        if isinstance(f19_nodo, ast.Import):
            f19_nombres = [a.name.split(".")[0] for a in f19_nodo.names]
        elif isinstance(f19_nodo, ast.ImportFrom) and f19_nodo.level == 0 and f19_nodo.module:
            f19_nombres = [f19_nodo.module.split(".")[0]]
        for f19_n in f19_nombres:
            if f19_n in f19_vistos:
                continue
            f19_p = f19_local(f19_n)
            if f19_p is not None:
                f19_vistos.add(f19_n)
                hace_falta |= f19_terceros(f19_p, f19_vistos)
            elif f19_n not in sys.stdlib_module_names:
                f19_vistos.add(f19_n)
                hace_falta.add(f19_n)
    return hace_falta


f19_guiones = sorted(set(re.findall(r"python3[^\n]*?\b(scripts/[a-z0-9_-]+\.py)", f19_yml)))
f19_instalados = set()
for f19_linea in re.findall(r"pip install[^\n>]+", f19_yml):   # hasta el primer `>`
    for f19_token in f19_linea.split()[2:]:          # se salta «pip install»
        if not f19_token.startswith(("-", "$", "/")):
            f19_instalados.add(F19_ALIAS.get(f19_token, f19_token).replace("-", "_"))

if not f19_yml:
    falla("runner · workflow", "no se puede leer `.github/workflows/build.yml`: esta comprobación "
                               "queda ciega y el rojo sólo saldría en Actions")
elif not hasattr(sys, "stdlib_module_names"):
    falla("runner · entorno", f"este Python ({sys.version.split()[0]}) no tiene "
                              "`sys.stdlib_module_names` y no sabe distinguir la librería "
                              "estándar de la que hay que instalar: hay que ejecutar la "
                              "costura con Python 3.10 o más nuevo")
elif len(f19_guiones) < 3:
    falla("runner · workflow", f"el workflow sólo declara {len(f19_guiones)} guiones "
                               f"({', '.join(f19_guiones) or 'ninguno'}): se cambió la forma de "
                               "invocarlos y esta comprobación ya no mira los de verdad")
elif not f19_instalados:
    falla("runner · workflow", "no hay ningún `pip install` en el workflow, y los guiones sí "
                               "arrastran paquetes de terceros: en casa el `.venv` los tiene y "
                               "aquí nadie los instala")
else:
    f19_rojos = []
    for f19_g in f19_guiones:
        f19_ruta = RAIZ / f19_g
        if not f19_ruta.exists():
            f19_rojos.append(f"{f19_g} no existe")
            continue
        f19_quedan = sorted(f19_terceros(f19_ruta, set()) - f19_instalados)
        if f19_quedan:
            f19_rojos.append(f"{f19_g} importa " + ", ".join(f19_quedan))
    if f19_rojos:
        falla("runner · dependencias", "; ".join(f19_rojos) +
              " y el workflow no los instala — `ModuleNotFoundError` en Actions, verde en casa, "
              "que es justo el fallo que el run 39879890814")
    elif not any('-c "import' in f19_yml[max(0, i - 900):i + 900]
                 for i in (m.start() for m in re.finditer(r"pip install", f19_yml))):
        falla("runner · dependencias", "ningún `pip install` va acompañado de una comprobación "
                                       "`python3 -c \"import …\"` cerca: si la imagen bloquea pip "
                                       "(PEP 668) el paso sigue adelante y el fallo llega dentro "
                                       "del guion, sin decir quién fue")
    else:
        dice_ok("runner · dependencias",
                "los " + str(len(f19_guiones)) + " guiones de Actions (" + ", ".join(
                    g.split("/")[-1] for g in f19_guiones) + ") importan sólo lo que el workflow "
                    "instala (" + ", ".join(sorted(f19_instalados)) + "), y lo comprueba antes de "
                    "lanzarlos")


# ── [20] F10 · la Música de Lark: carátulas, vídeos, buscador, letra dentro del
#         reproductor y el botón nativo que no estorba.
# La dueña describió 2.6.0-nucleo con cinco fallos de frente («no se ven las carátulas,
# no reproduce, no cargan los vídeos, la playlist no es Lark, el buscador no acierta, y
# el cartel de modo juego no se quita»). Cada comprobación de abajo ata UNO de esos
# quejas con las dos capas que tienen que decir lo mismo: si la cara pide una carátula
# que Java no sabe dar, la fila sale vacía en el teléfono y verde en cualquier prueba
# que sólo mire el JS.
print("\n[20] F10 · carátulas, vídeos, buscador y la letra fusionada")

F20_JAVA = puente_texto()
F20_CARA = (RAIZ / "ui" / "js" / "pantallas.js").read_text(encoding="utf-8")
F20_SIN = sin_comentarios_js(F20_CARA)
F20_MAIN = (APK / "src" / "com" / "cort" / "ia" / "MainActivity.java").read_text(encoding="utf-8")
F20_MUS = (APK / "src" / "com" / "cort" / "ia" / "Musica.java").read_text(encoding="utf-8")
F20_HUDJS = (RAIZ / "ui" / "js" / "hud.js").read_text(encoding="utf-8")
F20_HUDCSS = (RAIZ / "ui" / "css" / "hud.css").read_text(encoding="utf-8")
F20_APPS = (RAIZ / "ui" / "css" / "apps.css").read_text(encoding="utf-8")

# 20.a · `llama('X')` / `puede('X')`: la cara no puede pedir un método que Java no
# expone. `llama` devuelve `null` en silencio cuando falta (`pantallas.js:81`), así que
# el síntoma en el teléfono es un botón mudo — que es exactamente lo que reportó.
f20_llamados = set()
for _f20 in sorted((RAIZ / "ui" / "js").glob("*.js")):
    f20_llamados |= set(re.findall(
        r"\b(?:llama|puede)\(\s*['\"](\w+)['\"]",
        sin_comentarios_js(_f20.read_text(encoding="utf-8"))))
if not f20_llamados:
    falla("puente · llama()", "la prueba no encontró NINGÚN `llama(…)`: está vacía, "
                              "y un verde que no puede ponerse rojo no es prueba")
else:
    f20_faltan = sorted(n for n in f20_llamados if n not in metodos_javascript)
    if f20_faltan:
        falla("puente · llama()", "la cara llama " + ", ".join(f"`{n}`" for n in f20_faltan)
              + " y no hay `@JavascriptInterface` con ese nombre → `null` en silencio, "
                "botón muerto en el teléfono")
    else:
        dice_ok("puente · llama()", f"los {len(f20_llamados)} métodos que la cara pide por "
                                    f"`llama`/`puede` están expuestos en Java")

# 20.b · Las carátulas: Java las da (con `loadThumbnail`, y en base64 porque el WebView
# tiene `setAllowFileAccess(false)`), y la cara las pide detrás de `puede(...)` para que
# un APK viejo congele la lista.
if "musicaCaratula" not in F20_JAVA:
    falla("carátulas", "CortNative no expone `musicaCaratula`: «no se ven las carátulas»")
elif "loadThumbnail" not in F20_MUS or "base64" not in F20_MUS:
    falla("carátulas", "Musica.java no saca la imagen del índice (`loadThumbnail`) o no la "
                       "mete en base64, y un `file://` nunca carga en este WebView")
elif "musicaCaratula" not in F20_SIN:
    falla("carátulas", "la cara no pide carátulas: la fila seguiría con su glifo")
elif "data-cara" not in F20_CARA:
    falla("carátulas", "la cara pide la imagen pero ningún `<img data-cara=…>` la recibe")
else:
    dice_ok("carátulas", "`musicaCaratula` en Java, `loadThumbnail`+base64, y la cara la "
                         "pide de 4 en 4 con su `<img data-cara>`")

# 20.c · Vídeos y buscador, que eran el mismo bug con dos caras: `MAX` era compartido.
if "MAX_VIDEO" not in F20_MUS:
    falla("vídeos", "Musica.java no separa el tope de vídeos del de canciones: 400 para "
                    "todo y la pestaña de vídeos sale medio vacía")
elif "plegar" not in F20_MUS:
    falla("buscador", "sin `plegar()` el filtro queda en el `LIKE` del SQLite, que sólo "
                      "ignora mayúsculas del ASCII: los acentos y la ñ no aciertan")
elif "lk-cuadricula" not in F20_APPS:
    falla("vídeos", "la pestaña de vídeos no tiene rejilla: `.lk-cuadricula` no está en apps.css")
else:
    dice_ok("vídeos y buscador", "topes separados, filtro plegado en Java y rejilla para los vídeos")

# 20.d · La letra fusionada: sigue existiendo como hoja, pero ya no se ofrece como otra
# app, y el orbe no se despierta encima del vídeo (lo pidió dicho: «no me gusta que
# aparezca en MV»).
if "escondida: true" not in F20_CARA:
    falla("letra fusionada", "MV sigue ofreciéndose sola en el cajón: no está fusionada en Música")
elif "montables()" not in F20_CARA or "const visibles" not in F20_CARA:
    falla("letra fusionada", "no hay dos listas (`montables`/`visibles`): esconder MV dejaría "
                             "de montarla y el botón «letra» no tendría adónde ir")
elif "p-mv #scene" in F20_HUDCSS:
    falla("letra fusionada", "hud.css sigue intentando poner el orbe encima del vídeo")
elif "orb.pausa(false); orb.setDisc(true)" in F20_HUDJS:
    falla("letra fusionada", "hud.js sigue despertando el WebGL en la hoja de letra")
elif "abreLetra" not in F20_SIN:
    falla("letra fusionada", "el botón «letra» no llama a `abreLetra()`: no hay fusión")
else:
    dice_ok("letra fusionada", "la letra vive dentro de Música (hoja escondida + `abreLetra`) "
                               "y el orbe se apaga como en las demás hojas")

# 20.e · El botón nativo «CORT · PC»: la cara lo esconde en las hojas que no son el
# orbe. Un `@JavascriptInterface` que llama a un método ausente en `MainActivity` es un
# `NoSuchMethodError` que tiraría el puente, así que se cruzan las dos mitades Java.
if "menuPC" not in F20_JAVA:
    falla("botón nativo", "CortNative no expone `menuPC`: el botón no se puede ocultar")
elif "muestraMenuPC" not in F20_MAIN:
    falla("botón nativo", "`menuPC` llama a `act.muestraMenuPC` y ese método no está en "
                          "MainActivity: `NoSuchMethodError` en cuanto la cara cambie de hoja")
elif "menuPC" not in F20_SIN:
    falla("botón nativo", "la cara nunca lo oculta: sigue atravesado sobre la píldora")
else:
    dice_ok("botón nativo", "`menuPC` ↔ `MainActivity.muestraMenuPC`, y la cara lo usa al cambiar de hoja")

# 20.f · El modo juego clavado: el negativo tiene que tener nombre en las tres capas
# (Java lo dice, voice.js lo pasa, hud.js lo explica). Sin una de las tres, la dueña
# vuelve a quedarse con un micrófono mudo y un cartel que no se quita.
if not re.search(r'stt-error[^\n]*juego', F20_JAVA):
    falla("modo juego", "Java sigue abortando la escucha sin decir `juego`: el micro parece roto")
elif "'juego'" not in (RAIZ / "ui" / "js" / "voice.js").read_text(encoding="utf-8"):
    falla("modo juego", "voice.js no traduce el `juego` de Java a `onError`")
elif "e === 'juego'" not in F20_HUDJS:
    falla("modo juego", "hud.js no le pone palabras al negativo: la boca no dice qué pasa")
elif "juego.id = 'pantalla-juego'" not in F20_CARA:
    falla("modo juego", "el cartel sigue siendo un aviso: no hay forma de tocarlo para salir")
elif "salirDeJuegoPorMusica" not in F20_JAVA:
    falla("modo juego", "poner música desde la cara no sale del modo: `.Reproductor` pide el "
                        "foco, lo rechaza y la canción carga en silencio")
else:
    dice_ok("modo juego", "el negativo se nombra (Java→voice.js→hud.js), el cartel es un botón "
                          "y la música manda salir del modo")

# 20.g · La cara no puede prometer lo que el puente no da: las cuatro funciones nuevas
# del menú ⋮ se exigen por su nombre en las dos mitades.
for f20_metodo, f20_qu in (("musicaVelocidad", "Velocidad"), ("musicaDuerme", "dormir"),
                           ("musicaOculta", "Ocultar"), ("abreEnlace", "Sitios")):
    if f20_metodo not in F20_JAVA:
        falla(f"menú ⋮ · {f20_qu}", f"CortNative no expone `{f20_metodo}`")
    elif f20_metodo not in F20_SIN:
        falla(f"menú ⋮ · {f20_qu}", f"`{f20_metodo}` está en Java pero la cara no lo llama: "
                                     "la fila sería un adorno")
    else:
        dice_ok(f"menú ⋮ · {f20_qu}", f"`{f20_metodo}` en las dos capas")

# ── [21] F10 · la sonda no puede comprobar una cara que no existe ───────────
# `ui/sonda-carita.html` es lo único que permite VER la cara del teléfono en este
# portátil. Y tiene su propio modo de mentir: si un selector está mal escrito,
# `querySelector` devuelve `null`, `[].length` da `0` y una prueba negativa se pone
# VERDE sin haber mirado nada. Antes de fiarse de un verde de la sonda se comprueba,
# sin abrir el navegador, que cada selector que consulta existe en la cara que se
# instala, y que su puente de mentira simula TODO lo que la cara pide: si falta un
# método, el `puede()` de `pantallas.js:83` da `false` y la sonda recorre la rama del
# APK viejo — que no es la que la dueña lleva en el bolsillo.
print("\n[21] F10 · la sonda, la cara y el puente de mentira, los tres a la vez")

F21_SONDA = (RAIZ / "ui" / "sonda-carita.html").read_text(encoding="utf-8")
F21_MODULO = re.search(r'<script type="module">(.*)</script>', F21_SONDA, re.S)
if not F21_MODULO:
    falla("sonda", 'no hay `<script type="module">` que leer: la sonda dejó de ser un módulo')
else:
    F21_JS = sin_comentarios_js(F21_MODULO.group(1))

    def f21_sin_html(txt: str) -> str:
        return re.sub(r"<!--.*?-->", "", txt, flags=re.S)

    # Los módulos que la sonda carga DE VERDAD: `pantallas.js` y su cadena de `import`.
    # `hud.js` queda fuera a propósito: es la cara del PC, y exigirle sus nodos a esta
    # hoja sería pedirle a la sonda que simule una pantalla que no monta.
    F21_COLA, F21_MODS = ["pantallas.js"], {}
    while F21_COLA:
        f21_nombre = F21_COLA.pop()
        if f21_nombre in F21_MODS:
            continue
        f21_txt = sin_comentarios_js((RAIZ / "ui" / "js" / f21_nombre).read_text(encoding="utf-8"))
        F21_MODS[f21_nombre] = f21_txt
        F21_COLA += re.findall(r"from '\./([\w.-]+\.js)'", f21_txt)
    F21_CARA = "".join(F21_MODS.values()) + "".join(
        f21_sin_html(sin_comentarios_js(f.read_text(encoding="utf-8")))
        for f in sorted((RAIZ / "ui" / "css").glob("*.css"))) + f21_sin_html(
        sin_comentarios_js((RAIZ / "ui" / "index.html").read_text(encoding="utf-8")))

    # 21.a · El puente de mentirijilla no puede prometer más de lo que el teléfono da,
    # ni quedarse por debajo de lo que la cara pide. Las dos direcciones, porque en la
    # práctica fallan las dos: una tecla que Java no tiene es adorno, y una que falta
    # apaga la pantalla entera sin decir nada.
    f21_lin = F21_MODULO.group(1).splitlines()
    if not any(l.startswith("window.CortNative =") for l in f21_lin):
        falla("sonda · puente", "no se encuentra `window.CortNative = {`: la prueba está ciega")
    else:
        f21_ini = next(k for k, l in enumerate(f21_lin) if l.startswith("window.CortNative ="))
        f21_fin = next(k for k in range(f21_ini + 1, len(f21_lin)) if f21_lin[k].strip() == "};")
        f21_fake = {m.group(1) for k in range(f21_ini + 1, f21_fin)
                    for m in [re.match(r"  (\w+)\s*:", f21_lin[k])] if m}
        f21_pide = set()
        for f21_txt in F21_MODS.values():
            f21_pide |= set(re.findall(r"\b(?:llama|puede)\(\s*['\"](\w+)['\"]", f21_txt))
        if not f21_pide:
            falla("sonda · puente", "ningún módulo montado por la sonda pide métodos: la prueba no mira nada")
        else:
            f21_fingidos = sorted(f21_fake - metodos_javascript)
            f21_sin_simular = sorted(f21_pide - f21_fake)
            if f21_fingidos:
                falla("sonda · puente", "la sonda simula " + ", ".join(f"`{n}`" for n in f21_fingidos)
                      + " y `CortNative.java` no los expone: es un método inventado, y la cara "
                        "del teléfono jamás lo va a contestar")
            elif f21_sin_simular:
                falla("sonda · puente", f"la cara pide {len(f21_sin_simular)} métodos ("
                      + ", ".join(f"`{n}`" for n in f21_sin_simular)
                      + ") y el puente de mentira no los tiene: `puede()` da `false` y la sonda "
                        "recorre la rama del APK viejo, verde pero mirando otra cosa")
            else:
                dice_ok("sonda · puente", f"los {len(f21_pide)} métodos que piden "
                      + ", ".join(sorted(F21_MODS)) + " están simulados, y las "
                      f"{len(f21_fake)} teclas fingidas existen todas en Java")

    # 21.b · Cada selector que la sonda consulta tiene que existir en la cara montada,
    # salvo los que la sonda DECLARA como negativos (`NEGATIVOS`): Lark trae ecualizador,
    # cola y carpetas y el puente de CORT no los da, así que ahí se prueba la ausencia.
    # Los ids compuestos (`${p}-play`, `'scr-' + p.id`) y los que la propia sonda se
    # fabrica (`<button id="otro">`) también valen: se buscan por su regla de nombre.
    # Un selector empieza en `#id` o `.clase`, y puede llevar detrás lo que lleva
    # cualquier selector de verdad: atributos (`[data-c="videos"]`), pseudo-clases
    # (`:last-child`), descendientes (`.lk-fila .lk-txt b`) y etiquetas sueltas.
    f21_forma = re.compile(r"[.#][\w-]+[A-Za-z0-9_\-\s.,>+~#*:\[\]='\"|()^$]*")
    f21_sels: set[str] = set()
    for f21_q in (re.findall(r"'([^'\n]*)'", F21_JS) + re.findall(r'"([^"\n]*)"', F21_JS)):
        if f21_forma.fullmatch(f21_q.strip()):
            f21_sels |= set(re.findall(r"[.#][A-Za-z][\w-]*", f21_q))
    f21_sels = {s for s in f21_sels if not re.fullmatch(r"#[0-9a-fA-F]{3,8}", s)}
    f21_compuestos = {"#" + f21_pre + "-" + f21_cola
                      for f21_pre in set(re.findall(r"transporteHTML\('(\w+)'\)", F21_CARA))
                      for f21_cola in re.findall(r"\$\{p\}-([\w-]+)", F21_CARA)}
    f21_compuestos |= {"#scr-" + f21_p for f21_p in re.findall(r"\{\s*id:\s*'(\w+)'", F21_CARA)}
    f21_propios = set(re.findall(r'id="([\w-]+)"', F21_JS))
    f21_neg = {m for bloque in re.findall(r"const NEGATIVOS\s*=\s*\[([^\]]*)\]", F21_JS, re.S)
               for m in re.findall(r"['\"]([.#][\w-]+)['\"]", bloque)}
    if not f21_sels:
        falla("sonda · selectores", "la sonda no consulta NINGÚN selector: la prueba está vacía")
    else:
        f21_huerfanos = sorted(s for s in f21_sels
                               if s[1:] not in F21_CARA and s[1:] not in f21_propios
                               and s not in f21_compuestos and s not in f21_neg)
        f21_vivos = sorted(s for s in f21_neg if s[1:] in F21_CARA or s in f21_compuestos)
        if f21_huerfanos:
            falla("sonda · selectores", "la sonda pregunta por "
                  + ", ".join(f"`{s}`" for s in f21_huerfanos)
                  + " y nada en la cara lo monta: `null` o lista vacía, y una prueba "
                    "negativa con un selector roto se pone verde sin haber visto nada")
        elif f21_vivos:
            falla("sonda · selectores", "declarados como «lo que CORT no tiene» pero la cara ya "
                  "los montó: " + ", ".join(f"`{s}`" for s in f21_vivos)
                  + " · la comprobación `nada inventado` está caducada")
        else:
            dice_ok("sonda · selectores", f"los {len(f21_sels)} selectores que la sonda consulta "
                    f"existen en la cara (montada, compuesta o fabricada por la propia sonda), "
                    f"y los {len(f21_neg)} negativos declarados siguen sin existir")

    # 21.c · Ninguna pantalla que se le ofrece a la dueña puede quedarse sin mirar.
    f21_tabla = re.search(r"const PANTALLAS = \[(.*?)\n\];", F21_CARA, re.S)
    if not f21_tabla:
        falla("sonda · pantallas", "`pantallas.js` no tiene la tabla `PANTALLAS`: no hay qué mirar")
    else:
        f21_visibles = [m.group(1) for f21_p in re.split(r"(?=\{\s*id:)", f21_tabla.group(1))
                        for m in [re.search(r"\{\s*id:\s*'(\w+)'", f21_p)]
                        if m and "escondida" not in f21_p]
        f21_visitas = set(re.findall(r"\.ir\('(\w+)'\)", F21_JS))
        f21_ciegas = [p for p in f21_visibles if p not in f21_visitas]
        if not f21_visibles:
            falla("sonda · pantallas", "la tabla no deja NI UNA pantalla visible: está vacía")
        elif f21_ciegas:
            falla("sonda · pantallas", "estas hojas se le ofrecen a la dueña y la sonda nunca "
                  "entra en ellas: " + ", ".join(f"`{p}`" for p in f21_ciegas))
        else:
            dice_ok("sonda · pantallas", "las " + str(len(f21_visibles)) + " hojas visibles ("
                    + ", ".join(f21_visibles) + ") las recorre la sonda, y la escondida (`mv`) "
                      "sigue montada sin ofrecerse")


# ── [22] F10 · las columnas del índice, leídas por su número ─────────────────
# El run rojo de `v0.2.32-demo` (39902845281) paró el APK por una columna inventada, y
# al arreglarla aparece el riesgo de al lado: `Musica.leerEn` rellena la pista con
# `texto(cur, 4)`, números que tienen que casar con el ORDEN de la proyección. Quitar o
# mover una columna no da error de compilación —da la letra del álbum, o la fecha como
# duración—, y en el teléfono sale una lista con campos cambiados. El analizador
# sintáctico del portátil no lo ve (los `cannot find symbol` se filtran a propósito),
# así que lo cruza esta prueba: el número escrito en el código contra la posición real
# dentro del `String[] columnas`, leído del mismo archivo.
print("\n[22] F10 · el índice del cursor y la columna que dice leer, la misma vez")
F22_MUS = (APK / "src" / "com" / "cort" / "ia" / "Musica.java").read_text(encoding="utf-8")
F22_PROY = re.search(
    r"String\[\]\s+columnas\s*=\s*video\s*\?\s*new\s+String\[\]\s*\{(.*?)\}\s*:\s*"
    r"new\s+String\[\]\s*\{(.*?)\}\s*;", F22_MUS, re.S)
if not F22_PROY:
    falla("cursor · proyección", "la prueba no encuentra el `String[] columnas = video ? … : …` "
                                 "de `Musica.leerEn`: está vacía, y un verde que no puede "
                                 "ponerse rojo no es prueba")
else:
    f22_cols = {}
    for f22_ramo, f22_rama in ((F22_PROY.group(1), "vídeo"), (F22_PROY.group(2), "audio")):
        f22_cols[f22_rama] = [x.strip().split(".")[-1]
                              for x in f22_ramo.split(",") if x.strip()]
    # (`qué`, cómo se reconoce la línea, columna que DEBE ser, ramas en ese orden)
    f22_lecturas = [
        ("el título",     r"p\.titulo = texto\(cur, (\d+)\)",
                          "TITLE", ("vídeo", "audio")),
        ("el artista",    r"p\.artista = texto\(cur, (\d+)\)",
                          "ARTIST", ("vídeo", "audio")),
        ("el género",     r'p\.genero = video \? "" : texto\(cur, (\d+)\)',
                          "GENRE", ("audio",)),
        ("el álbum",      r'p\.album = video \? "" : texto\(cur, (\d+)\)',
                          "ALBUM", ("audio",)),
        ("la duración",   r"p\.dur = cur\.getLong\(video \? (\d+) : (\d+)\)",
                          "DURATION", ("vídeo", "audio")),
        ("la fecha",      r"p\.fecha = cur\.getLong\(video \? (\d+) : (\d+)\)",
                          "DATE_ADDED", ("vídeo", "audio")),
        ("la ruta",       r"hayArchivoDeLetra\(texto\(cur, video \? (\d+) : (\d+)\)\)",
                          "DATA", ("vídeo", "audio")),
    ]
    f22_cambios = []
    for f22_que, f22_calco, f22_columna, f22_ramas in f22_lecturas:
        f22_m = re.search(f22_calco, F22_MUS)
        if not f22_m:
            f22_cambios.append(f"{f22_que}: la línea que lee `{f22_columna}` ya no está como "
                               "la prueba la conoce (hay que leerla y actualizarla)")
            continue
        for f22_i, f22_rama in enumerate(f22_ramas):
            # Una línea puede llevar un número para las dos ramas (`texto(cur, 1)`, que
            # vale si TITLE cae en el mismo sitio en las dos proyecciones) o uno por rama
            # (`cur.getLong(video ? 3 : 5)`). Se casa con la que haya escrito.
            f22_escrito = int(f22_m.group(f22_i + 1 if len(f22_m.groups()) == len(f22_ramas) else 1))
            if f22_columna not in f22_cols[f22_rama]:
                f22_cambios.append(f"{f22_que}: `{f22_columna}` no está en la proyección de "
                                   f"{f22_rama}, y el código la lee en la {f22_escrito}")
                continue
            f22_real = f22_cols[f22_rama].index(f22_columna)
            if f22_escrito != f22_real:
                f22_cambios.append(
                    f"{f22_que}: el código lee la posición {f22_escrito} y en la proyección de "
                    f"{f22_rama} `{f22_columna}` está en la {f22_real} → sale el campo de al lado")
    if f22_cambios:
        falla("cursor · índices", "; ".join(f22_cambios))
    else:
        dice_ok("cursor · índices", "las " + str(len(f22_lecturas)) + " lecturas por número de "
                                    "`Musica.leerEn` caen en la columna que nombran ("
                                    f"proyección de {len(f22_cols['vídeo'])} columnas de vídeo y "
                                    f"{len(f22_cols['audio'])} de audio)")

    # Y la letra, que es lo que se quedó sin columna: tiene que seguir viva en los dos
    # caminos (el listado y la URI suelta), si no la píldora `LETRAS` de Lark vuelve a
    # ser un adorno que nunca se pinta.
    f22_llamadas = F22_MUS.count("hayArchivoDeLetra(")
    if f22_llamadas < 3:
        falla("letra", f"`hayArchivoDeLetra` aparece {f22_llamadas} veces contando su "
                       "definición: hacen tres (la definición, el listado y `unaPorUri`), y sin "
                       "una de las dos llamadas la píldora LETRAS sale siempre vacía")
    elif F22_MUS.count("p.letra =") < 2:
        falla("letra", "`p.letra` no se rellena en los dos caminos: la cara recibiría `false` "
                       "en las canciones que sí tienen `.lrc`")
    else:
        dice_ok("letra", "la píldora LETRAS se la gana el archivo hermano (`.lrc` / `.txt`) en "
                         "el listado y por URI, sin pedirle al índice una columna que no existe")

# ── veredicto ───────────────────────────────────────────────────────────────
print()
if FALLOS:
    print(f"FALTA {len(FALLOS)} COSA(S):")
    for f in FALLOS:
        print("  ·", f)
    sys.exit(1)
print("costura cosida: manifiesto, Java y cara se nombran lo mismo.")
