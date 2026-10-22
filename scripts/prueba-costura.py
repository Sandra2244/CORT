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

# ── veredicto ───────────────────────────────────────────────────────────────
print()
if FALLOS:
    print(f"FALTA {len(FALLOS)} COSA(S):")
    for f in FALLOS:
        print("  ·", f)
    sys.exit(1)
print("costura cosida: manifiesto, Java y cara se nombran lo mismo.")
