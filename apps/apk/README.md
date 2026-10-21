# CORT en el teléfono (APK)

## Los dos APK que salen de aquí, y cuál instalar

| archivo | cómo se hace | dónde se publica |
|---|---|---|
| `CORT-IA-1.1.2.apk` | **`rempaquetar.sh`**: el cuerpo es `base/CORT-IA-1.1.0.apk` (el APK original de la dueña: Kotlin, cuatro `classes.dex`, su icono de anillo, `ListenService`, permisos de archivos y almacenamiento) y sólo se le cambia `assets/ui/` por el `ui/` del commit, se realinea y se refirma | la **Release** — es el que se parece al de siempre |
| `CORT-IA-1.2.1-asistente.apk` | **`compilar.sh`**: Java escrito en este repo, sin Gradle (`aapt2` + `javac` + `d8` + `apksigner`), con el holograma embebido bajo `https://cort.local`, puente de voz propio, traje de `VoiceInteractionService` (asistente predeterminado), `MediaSession` (doble toque del auricular) y `Avisos` (lee en voz alta lo que llega a la barra de notificaciones) | la **Release** desde `v0.2.8-demo`: antes era sólo artefacto del run y había que tener sesión de GitHub para bajarlo |

> Los dos comparten el paquete `com.cort.ia`, así que **en el teléfono sólo puede
> vivir uno a la vez** — y como salen firmados con llaves distintas, cambiar de
> uno a otro obliga a desinstalar. El 1.1.2 es el cuerpo de siempre con la cara
> nueva; el 1.2.1 es el que tiene asistente predeterminado y el oído de los avisos.

El original no se recompila desde este repo porque **el proyecto Gradle que lo
generó no está aquí**: lo que siempre se guardó fue el binario (comprobado: el
blob de `instaladores/CORT-IA-1.1.0.apk` y la copia del Escritorio dan el mismo
SHA-256 `b5fa07fa9f065d6545e0d6ad9d51e3d4368a41519034e763016ad3a68666fb76`).
Por eso la actualización del teléfono se hace metiendo la cara nueva dentro del
binario, y por eso el `versionName` que ve Ajustes sigue siendo 1.1.0.

Todo lo que sigue en este archivo describe la pata de Java (`compilar.sh`).

Este APK **se compila en GitHub Actions**, nunca en el portátil de la dueña:
1,8 GiB de RAM, `javac` que no está (medido) y un `gradle build` que congeló la
máquina. El pipeline usa las cuatro herramientas que el runner ya trae —`aapt2`,
`javac`, `d8`, `apksigner`— y `compilar.sh` las ordena. Sin Gradle, sin AndroidX,
sin Node: la cara del teléfono es la misma carpeta `ui/` del repo.

## Qué es

| pieza | qué hace |
|---|---|
| `MainActivity.java` | un `WebView` a pantalla completa y **tres** superficies en una: la dirección del PC guardada (`http://IP:8000`, el holograma actual con sus once ventanas y su backend real), la cara embebida en el APK (`assets/ui/`, servida bajo `https://cort.local` y cortada en `shouldInterceptRequest` contra los assets), y el menú del botón «CORT · PC» para cambiar entre ellas |
| `CortNative.java` | `window.CortNative`: el micrófono (`SpeechRecognizer`), la voz (`TextToSpeech`), los permisos, el bloqueo de pantalla y la dirección del PC. Hace falta porque una página en `http` de red local **no es origen seguro** y Chrome no le presta Web Speech ni `getUserMedia` |
| `Asistente.java` + `Sesiones.java` + `Sesion.java` | el traje de **asistente predeterminado**: Ajustes ▸ Aplicaciones ▸ Aplicación de asistencia predeterminada ▸ CORT. Desde ahí, el gesto de asistente, la tecla del auricular y la pantalla bloqueada abren CORT y lo ponen a escuchar |
| `Reconocimiento.java` | el `RecognitionService` que el contrato de AOSP **exige** para aparecer en esa lista. CORT no trae modelo propio de palabra de activación, así que cede el oído al micrófono de la cara y cierra con `ERROR_NO_MATCH` |
| `MediaSession` (dentro de `MainActivity`) | el **doble toque del auricular**: dos pulsaciones de `HEADSETHOOK` / `PLAY_PAUSE` en menos de 500 ms abren el micrófono. La primera pulsación se devuelve `false`, así que pausar la música sigue siendo cosa de Spotify o de quien la mande |
| `Avisos.java` | el **oído de la barra de notificaciones** (`NotificationListenerService`): cada aviso que llega —WhatsApp, Messenger, Instagram, Facebook, Gmail, Telegram, Signal— se convierte en una línea `de quién: texto` y se guarda en una `ArrayDeque` de **doce entradas en RAM**, se van solas, y nunca se escriben a disco ni se envían a ningún sitio. `resumen(3)` es lo que CORT habla cuando dices «lee mis avisos» |
| `AndroidManifest.xml` | permisos (`INTERNET`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS`, `VIBRATE`), los cuatro `<service>` —asistente y sesión con `BIND_VOICE_INTERACTION`, reconocedor con `BIND_SPEECH_RECOGNIZER` y `Avisos` con `BIND_NOTIFICATION_LISTENER_SERVICE`—, la meta-datos hacia `res/xml/asistente.xml`, y `usesCleartextTraffic` para la Wi‑Fi sin TLS. **No** se añade ningún permiso de lectura de WhatsApp, SMS o contactos: la barra de notificaciones es un interruptor que pone la dueña en Ajustes, y CORT sólo ve lo que ahí ya se muestra |
| `res/xml/asistente.xml` | el contrato del asistente, con los atributos **sin** prefijo `android:` (son recursos internos del sistema y `aapt2` rechazaría la forma con prefijo) |

`assets/ui/` y `res/mipmap-*/` están en `.gitignore`: son generados. La única
copia buena de la cara es la que sale del `ui/` del commit etiquetado, y el
icono lo dibuja `scripts/marca.py` (el mismo anillo del logo del README).

## Usarlo

1. En la Release, descarga el que quieras usar: **`CORT-IA-1.1.2.apk`** (el cuerpo
   original con la interfaz nueva dentro) o **`CORT-IA-1.2.1-asistente.apk`** (el
   de Java, que es el que puede ser asistente predeterminado y leer tus avisos).
   Los dos están publicados como archivo de la Release, así que el enlace se
   descarga con un clic. Escoja uno: van en el mismo paquete y no conviven.
2. **Desinstala el APK anterior** la primera vez. No es capricho: este APK se
   firma con una llave del pipeline, y para Android una firma distinta es otra
   aplicación. Si la dueña guarda el secreto `CORT_APK_KEYSTORE_B64` en
   Settings ▸ Secrets and variables ▸ Actions, las Releases siguientes **sí** se
   instalan encima. El run publica a lado de cada APK su `-firma.txt` con la
   huella del certificado usado: esa es la prueba pública de con qué llave salió,
   porque los logs de Actions no son públicos.
3. Instálalo y concede el micrófono cuando lo pida.
4. Para que use tu PC por Wi‑Fi: en el portátil, `bash scripts/telefono.sh` y
   anota la dirección que imprime; en el teléfono, botón **CORT · PC** ▸
   «Conectar con mi PC por Wi‑Fi» y escríbela (`http://192.168.100.171:8000`).
   Los dos tienen que estar en la misma red. Si el PC no contesta, la app abre
   sola la cara embebida y funciona sin servidor.
5. Para que mande el doble toque de los audífonos: botón **CORT · PC** ▸ «Poner
   CORT como asistente» (o Ajustes ▸ Aplicaciones ▸ Aplicación de asistencia
   predeterminada ▸ **CORT**). En los Galaxy Buds, la acción del doble toque se
   deja en «Asistente digital».
6. Para que te lea los avisos (sólo en el `1.2.1`): botón **CORT · PC** ▸ «Dar el
   permiso de los avisos» y activa CORT en la lista del sistema. Desde ahí, di
   **«lee mis avisos»** y te cuenta en voz alta los últimos tres, y el menú te
   muestra si el oído está puesto o pendiente. «olvida los avisos» los borra de
   la RAM. En el PC, por Wi‑Fi, lo que lee son tus notas, tus pendientes y los
   textos de tus carpetas: «lee mis notas», «lee mis tareas», «lee el documento
   recibo».

## Lo que NO hace, dicho sin adornos

- **No** mantiene el «OK Google» con la pantalla apagada: esa palabra de
  activación la dice el servidor de Google y no viaja con este APK.
- **No** oye «Oye CORT» con la app cerrada: la escucha continua vive dentro del
  WebView, así que funciona con la cara abierta.
- La cara embebida, sin PC, **no** tiene cerebro de nube propio: la conversación
  libre, los modelos de Ollama y el optimizador viven en el backend del
  portátil. Por eso el paso 4 es el que de verdad le da las once ventanas. Sin
  PC, «lee mis notas» o «lee mis tareas» contestan el aviso de «sin PC» traduciado
  a una frase, no un silencio.
- **No** lee WhatsApp por la puerta de atrás: no hay API de WhatsApp, así que
  `Avisos.java` mira la **misma barra de notificaciones** que mirarías tú. Si
  tienes las previsualizaciones apagadas en WhatsApp, CORT ve «Mensaje (1)» y no
  el texto — eso es el teléfono hablando, no este APK.
- **No** guarda los avisos: ni en disco, ni en SQLite, ni en un servidor. Doce
  líneas en RAM del proceso, se van solas al pasar y «olvida los avisos» las tira.
  El permiso se quita en Ajustes en un segundo, y el menú lo muestra en su
  etiqueta («permiso: hecho» / «permiso: pendiente»).
- En el `1.1.2` (el cuerpo original) **no** hay lectura de avisos: ese Kotlin
  nunca tuvo el puente `CortNative.avisos()`, y la cara lo comprueba antes de
  llamar; en vez de romperse, te dice que eso lo trae el APK del asistente.
- Nada de esto está verificado con un dedo encima: no hay teléfono en esta
  máquina. Lo que sí comprueba el pipeline es que el Java compila contra la
  plataforma (`javac` revisa las firmas de `VoiceInteractionSession.onShow`,
  `RecognitionService.Callback.error`, `NotificationListenerService.onNotificationPosted`
  y compañía), que `aapt2` enlace el manifiesto, que `apksigner` valide la firma y
  que el APK quede alineado. Y `scripts/prueba-costura.py`, que corre aquí, revisa
  sin teléfono que manifiesto, Java y cara se nombran lo mismo.
