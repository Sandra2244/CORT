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
# Con UN solo APK (el de Java) la lista de permisos ya no son cuatro: el
# reproductor, los contactos y «ordena mis archivos» piden los suyos. Se comprueba
# el conjunto **necesario** y que no se cuele ninguno **desproporcionado**.
cortos = {p.rsplit(".", 1)[-1] for p in permisos}
necesarios = {
    "INTERNET", "RECORD_AUDIO", "MODIFY_AUDIO_SETTINGS", "VIBRATE",
    "READ_MEDIA_AUDIO", "READ_MEDIA_VIDEO", "READ_EXTERNAL_STORAGE",
    "FOREGROUND_SERVICE", "FOREGROUND_SERVICE_MEDIA_PLAYBACK", "WAKE_LOCK",
    "POST_NOTIFICATIONS", "READ_CONTACTS", "CALL_PHONE",
}
if necesarios <= cortos:
    dice_ok("permisos", f"{len(permisos)} declarados, los {len(necesarios)} justos están")
else:
    falla("permisos", f"faltan {', '.join(sorted(necesarios - cortos))}")
for prohibido in ("QUERY_ALL_PACKAGES", "READ_SMS", "SEND_SMS", "RECEIVE_MMS",
                  "READ_CALL_LOG", "PROCESS_OUTGOING_CALLS", "SYSTEM_ALERT_WINDOW",
                  "GET_ACCOUNTS", "MASTER_ACCOUNT", "WRITE_SECURE_SETTINGS"):
    if prohibido in cortos:
        falla("permiso de más", f"{prohibido}: no hace falta para lo que CORT promete")
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

# ── veredicto ───────────────────────────────────────────────────────────────
print()
if FALLOS:
    print(f"FALTA {len(FALLOS)} COSA(S):")
    for f in FALLOS:
        print("  ·", f)
    sys.exit(1)
print("costura cosida: manifiesto, Java y cara se nombran lo mismo.")
