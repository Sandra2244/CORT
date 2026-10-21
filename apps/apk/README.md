# CORT en el teléfono (APK)

## Un solo APK: `CORT-IA-2.1.0.apk`

| archivo | cómo se hace | dónde se publica |
|---|---|---|
| `CORT-IA-2.1.0.apk` | **`compilar.sh`**: Java escrito en este repo, sin Gradle (`aapt2` + `javac --release 11` + `d8` + `zipalign` + `apksigner`), con el holograma embebido bajo `https://cort.local`, puente de voz y de cuerpo propio (`CortNative.java`, **59** `@JavascriptInterface`), traje de `VoiceInteractionService` (asistente predeterminado), `MediaSession` (doble toque del auricular), `Avisos` (lee en voz alta lo que llega a la barra de notificaciones), **su propio reproductor**, el **marcador de contactos** y la ronda 2.1 entera (mando, voz, memoria, cerebro propio, atuendos, agenda, burbuja, compartir). El icono es el anillo de siempre: `compilar.sh` lo saca de `base/CORT-IA-1.1.0.apk` | la **Release**, como archivo descargable con un clic |

Hubo **dos** APK hasta `v0.2.10-demo`: el cuerpo original de Kotlin rempaquetado
(`rempaquetar.sh`, sólo con la cara cambiada) y éste de Java. La dueña lo cortó
por lo sano: dos archivos que había que saber elegir, con logos distintos y con
funciones que caían en uno u otro, eran trabajo de más y tardaban el doble en
publicarse. **`rempaquetar.sh` está borrado del repo y del workflow**: todo lo
nuevo entra en el APK que se compila aquí.

Lo que sí se conserva del binario original es su **icono**, que es lo que lo hace
reconocible en el cajón de aplicaciones. `compilar.sh` descomprime
`base/CORT-IA-1.1.0.apk`, saca los cinco `mipmap-*` y el XML adaptativo
(`mipmap-anydpi-v26`), y si algún día ese `base/` no viene en el checkout, cae a
`scripts/marca.py` para que el pipeline no se rompa.

El proyecto Gradle que generó el `1.1.0` nunca estuvo en este repo: lo guardado
siempre fue el binario (comprobado: el blob de `instaladores/CORT-IA-1.1.0.apk` y
la copia del Escritorio dan el mismo SHA-256
`b5fa07fa9f065d6545e0d6ad9d51e3d4368a41519034e763016ad3a68666fb76`). Por eso ese
Kotlin no se recompila: se compila Java propio, y por eso el `versionName` que
ve Ajustes ahora **sí** es el nuestro (`2.1.0`, con `versionCode` 20100), porque
el manifiesto es de este repo. El `1.3.0` llevaba 10300 y el `2.0.0` 20000, así
que Android ve el nuevo como actualización y se instala **encima** — con la misma
llave de firma, que es el otro requisito para que no obligue a desinstalar.

Este APK **se compila en GitHub Actions**, nunca en el portátil de la dueña:
1,8 GiB de RAM, `javac` que no está (medido) y un `gradle build` que congeló la
máquina. El pipeline usa las cuatro herramientas que el runner ya trae y
`compilar.sh` las ordena. Sin Gradle, sin AndroidX, sin Node: la cara del
teléfono es la misma carpeta `ui/` del repo.

## Qué es

| pieza | qué hace |
|---|---|
| `MainActivity.java` | un `WebView` a pantalla completa y **tres** superficies en una: la dirección del PC guardada (`http://IP:8000`, el holograma con sus once ventanas y su backend real), la cara embebida en el APK (`assets/ui/`, servida bajo `https://cort.local` y cortada en `shouldInterceptRequest` contra los assets), y el menú del botón «CORT · PC» para cambiar entre ellas. Interception aparte: corta los `/api/*` cuando no hay PC, para que la cara traduzca el 501 en una frase y no en un silencio. Guarda una referencia estática a la cara (`front()`) para que el servicio de música pueda avisar aunque esté en otro hilo |
| `CortNative.java` | `window.CortNative`: el micrófono (`SpeechRecognizer`), la voz (`TextToSpeech`), los permisos, el bloqueo de pantalla, la dirección del PC **y el cuerpo entero del reproductor y del marcador**. Los `@JavascriptInterface` se ejecutan en el hilo del puente, no en el de la interfaz: así una consulta a `MediaStore` con dos mil canciones no congela el orbe (lo pedido expreso: que la música no trabe el teléfono) |
| `Reproductor.java` | el **reproductor de CORT**, un `Service` en primer plano con `foregroundServiceType="mediaPlayback"`: suena con la cara cerrada y en segundo plano. `MediaSession` + `PlaybackState` + `MediaMetadata` (así lo ven Spotify, los botones del auricular y la pantalla de bloqueo), `AudioFocusRequest` (baja la música si llama alguien), notificación `MediaStyle` con play/siguiente, y cola estática porque `startForegroundService` es asíncoro: la cola puede llenarse antes de que el sistema haya creado el servicio, y `onCreate` la consume. Con `cuadro()` se avanza **fotograma a fotograma** en vídeo |
| `Musica.java` | la **biblioteca** y los **gustos**. Lee `MediaStore.Audio` (y vídeo) filtrando `IS_MUSIC != 0` para que no se cuelen tonos de llamada ni grabaciones, busca por título/artista/álbum, y guarda en las preferencias de la app un contador por artista y por género: 👍 suma tres, 👎 resta dos, topado ±9. Con eso sale «ponme algo de lo que me gusta» (`porGusto`) y el perfil que CORT te lee en voz alta. Las playlists se guardan como `playlist\|nombre` con sus URIs. **Se va al desinstalar la app**: lo que no se pierde es el cerebro del PC |
| `Telefono.java` | busca en tus **contactos** (`ContactsContract`) y **marca** (`ACTION_CALL` si diste el permiso de llamar, si no `ACTION_DIAL` para que tú pulséis verde). No contesta por ti: eso exige el rol `ROLE_CALLING` y un `InCallService`, y está anotado como pendiente |
| `Acciones.java` | el **mando del aparato** (`accion(que,args)`): volumen, linterna (con su `CAMERA` pedido en el momento), alarma y temporizador (por `SET_ALARM`, que es el camino público y no necesita ser la app de reloj), cronómetro, `abrir` las apps de siempre con sus alias (WhatsApp y su versión de
negocio, YouTube, Maps, Spotify, Gmail, calendario, Instagram, Facebook, TikTok,
archivos —con sus cinco nombres de fabricante— y el reproductor MV/Lark), `app` por parecido, `lanzadores` (lista de instaladas gracias al `<queries>`), `buscar` y `estado`. Todo síncrono y en JSON; lo que Android no deja, lo dice con el camino de Ajustes en vez de quedarse callado |
| `VozNueva.java` | la **voz que gusta** (`ajusteVoz`): lista de voces del motor (filtra el idioma y avisa si faltan datos), `poner` con velocidad y tono, `predefinida` (siri / alexa / cortana / española / mexicana / neutra: elige la mejor instalada parecida al estilo y, si no está, lo dice), `descargar` (abre el instalador de datos TTS de Android) y `probar`. La voz elegida se guarda en las preferencias y **la respeta todo CORT**: la cara, el menú, los avisos leídos y el saludo de arranque, no sólo el botón de la hoja. Se monta con `Looper` en el hilo de la interfaz porque el `init` de `TextToSpeech` se entrega al hilo que lo construyó |
| `Recuerdos.java` + `Sincroniza.java` | la **memoria del teléfono**: SQLite propio (`cort.db`) con `guardar`/`buscar`/`lista`/`quien`/`olvidar` (sólo lo que CORT guardó; nunca archivos), y `sincronizar`, que es **bidireccional** —baja hechos y muro del portátil por `GET /api/profile` y `GET /api/memories`, sube lo suyo con `POST` a las dos puertas— por la LAN, con la clave de red sólo en la cabecera `Authorization`. La clave de la API del PC jamás viaja a la cara: se dice `clavePuesta:true` |
| `Mente.java` + `Nube.java` + `Cerebro.java` | **pensar sin el portátil**: `mente(que,args)` con `estado`/`ajustar`/`preguntar`/`probar` sobre siete proveedores de nube (Groq, OpenAI, DeepSeek, Mistral, Qwen, Anthropic y
`ollama` apuntando a `http://127.0.0.1:11434/v1` para el modelo local). `preguntar` contesta `{"pendiente":true}` enseguida y devuelve en el evento `mente` desde su hilo. Con la nube apagada, `Cerebro` usa los 35 patrones de `assets/habilidades.json` y contesta `accion`+`param`, que **la cara reenvía a `accion()`** — pensar y hacer son dos clases distintas a propósito: la que reconoce no toca el aparato |
| `Paleta.java` | los **atuendos** (`atuendo`): Cortana, JARVIS, Siri, Matrix, Atardecer y Neutron, cada uno con su `--primario`/`--secundario`. La cara pinta las variables y `MainActivity.usaAtuendo()` pinta con él el botón «CORT · PC», para que el traje se note aunque la cara esté cerrada |
| `Agenda.java` | **tus citas y lo que llegó al correo** (`agenda`): lee `CalendarContract.Instances` de hoy o de N días con `READ_CALENDAR` **y nada de escritura** —`apunta` abre el formulario del calendario relleno y el dedo que guarda es el de la dueña—; `correo` cuenta los avisos de Gmail que ya oyó `Avisos` y abre la app. Sin permiso dice «no lo sé» en vez de inventar citas |
| `Flotante.java` | la **burbuja**: un punto de 44 dp con `SYSTEM_ALERT_WINDOW` (permiso que pone la dueña a mano; el botón lleva directo a esa pantalla de Ajustes). Al tocarla, CORT se abre y escucha. En **modo juego no aparece**, y poner el modo juego quita la que estuviera puesta |
| `ArchivosProvider.java` | el proveedor de archivos **escrito sobre `android.content.ContentProvider`** (autoridad `com.cort.ia.files`, sin AndroidX) detrás de `comparte(ruta)`: «envíame ese archivo» sale por `ACTION_SEND` con `content://`, que es la única forma que no revienta en Android 7+. No es `androidx.core.content.FileProvider` —aquí no hay AndroidX— y **`android.content.FileProvider` no existe**: lo que es del framework es la clase base, y las rutas se leen en tiempo de ejecución de `res/xml/archivos.xml`, así que el XML y el código no se pueden separar. Sólo lectura, `Android/` cortado, y si la lista no se lee no se deja pasar nada. Acepta también el `content://` del índice, que es lo único que sabe la pantalla de Música |
| `Asistente.java` + `Sesiones.java` + `Sesion.java` | el traje de **asistente predeterminado**. `MainActivity.abreAjustesDeAsistente()` pide el **rol** con `RoleManager.createRequestRoleIntent(ROLE_ASSISTANT)` (Android 10+), que es el cuadro de Android que de verdad te elige; en Android 8 y 9 cae a las pantallas de Ajustes de siempre, y si ninguna existe lo dice con el camino a mano. Desde ahí, el gesto de asistente, la tecla del auricular y la pantalla bloqueada abren CORT y lo ponen a escuchar. También se puede pedir por voz: **«pon CORT como asistente»** |
| `Reconocimiento.java` | el `RecognitionService` que el contrato de AOSP **exige** para aparecer en esa lista. CORT no trae modelo propio de palabra de activación, así que cede el oído al micrófono de la cara y cierra con `ERROR_NO_MATCH` |
| `MediaSession` (dentro de `MainActivity`) | el **doble toque del auricular**: dos pulsaciones de `HEADSETHOOK` / `PLAY_PAUSE` en menos de 500 ms abren el micrófono. La primera pulsación se devuelve `false`, así que pausar la música sigue siendo cosa de quien la mande |
| `Avisos.java` | el **oído de la barra de notificaciones** (`NotificationListenerService`): cada aviso que llega —WhatsApp, Messenger, Instagram, Facebook, Gmail, Telegram, Signal— se convierte en una línea `de quién: texto` y se guarda en una `ArrayDeque` de **doce entradas en RAM**, se van solas, y nunca se escriben a disco ni se envían a ningún sitio. `resumen(3)` es lo que CORT habla cuando dices «lee mis avisos» |
| `CortNative.modoJuego(bool)` / `juegoActivo()` / `reanuda()` | el **modo juego**. Con él puesto (`true`), `Reproductor.pideFoco()` devuelve `false` — o sea, CORT **no le roba el foco audio** a una partida —, el micrófono de «Oye CORT» se cierra y la voz se calla por el auricular; `silenciar()` baja lo que estuviera sonando y `soltarSesion()`/`recuperarSesion()` entregan y vuelven a tomar la `MediaSession`. El estado se guarda en las preferencias (`static volatile boolean juego`), así que sobrevive a cerrar la cara, y `reanuda()` re-emite el `pause` a la interfaz para que el interruptor se pinte como está de verdad. **Sin** `PACKAGE_USAGE_STATS` ni `QUERY_ALL_PACKAGES`: la dueña lo decidió así, y por eso es un interruptor (voz, hoja Música/MV o menú `CORT · PC`) y no un detector automático de juegos |
| `Reproductor.estadoJson()` | el **estado completo** que lee la cara en un solo bocado: `vivo`, `suena`, `pos`, `dur`, `idx`, `total`, `uri`, `video`, `juego` y el objeto `pista` (`titulo`, `artista`, `genero`, `uri`, `video`). `uri` y `video` van repetidos arriba a propósito: la hoja **MV** necesita la `content://` del `MediaStore` para su `<video>` sin preguntar si hay canción, y en Java no existe el `?.` de JavaScript. Con `setAllowContentAccess(true)` en el `WebView`, esa URI es exactamente lo que un `<video>` puede reproducir |
| `ui/js/pantallas.js` (en la cara) | las **pantallas que no tocan el orbe**: una barra con ☰ arriba, hojas a pantalla completa y cambio deslizando el dedo de lado, con `Alt+←/→` o por voz. Hay seis: **Orbe** (la interfaz de siempre, sin mover nada), **Música** (sólo en el teléfono, manda al `Reproductor`), **MV** (sólo en el teléfono: el videoclip en un `<video>` con la **letra sincronizada** debajo y el orbe de disco en una esquina), **Charla** (burbujas, modelos de Ollama, copiar y guardar en Notas), **Código** (terminal contra `/api/command` + cuaderno) y **Equipo** (sólo en el teléfono **y sólo si el puente trae `accion`**: los seis bloques del contrato 2.1, que son Voz · Mando · Cerebro · Memoria · Atuendos · Agenda). Cuando no es la pantalla del orbe, el lienzo WebGL **se apaga** (`orb.pausa()`): en un teléfono modesto eso es RAM, GPU y batería. Y si el módulo de pantallas fallara al montarse, el CSS está atado a la clase `pantallas-montadas`, así que la interfaz de siempre queda intacta en vez de negro |
| `AndroidManifest.xml` | **23** permisos declarados y cada uno con su función detrás: `INTERNET`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS`, `VIBRATE`, los tres `READ_MEDIA_*` (Android 13+) con su `READ_EXTERNAL_STORAGE`/`WRITE_EXTERNAL_STORAGE` hasta Android 12 y `READ_MEDIA_VISUAL_USER_SELECTED` (el «selecciona fotos» de Android 14), `MANAGE_EXTERNAL_STORAGE` para «ordena mis archivos», `READ_CONTACTS` + `CALL_PHONE`, `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_MEDIA_PLAYBACK`, `POST_NOTIFICATIONS`, `WAKE_LOCK`, `BLUETOOTH`, y los cuatro que trajo la 2.1: `CAMERA` (sólo la linterna), `com.android.alarm.permission.SET_ALARM` (alarma y temporizador por el reloj del sistema), `READ_CALENDAR` (leer citas; **nunca** `WRITE_CALENDAR`) y `SYSTEM_ALERT_WINDOW` (la burbuja, que se da a mano en Ajustes y se puede quitar). Están además los `<queries>` de Android 11+ —los lanzables, el motor de voz, los servicios de alarma/temporizador/búsqueda/marcado y doce paquetes nombrados—, el `<provider>` `com.cort.ia.files` y las reglas de `res/xml` (`seguridad_red`, `respaldo`, `extraccion`, `archivos`). **No** hay `READ_SMS`, `QUERY_ALL_PACKAGES`, `WRITE_CALENDAR`, `PACKAGE_USAGE_STATS` ni `PROCESS_OUTGOING_CALLS`: la barra de notificaciones es un interruptor que pone la dueña, marcar se pide a mano y la lista de instaladas sale de los `<queries>`, no de espiar el teléfono entero |
| `res/xml/asistente.xml` | el contrato del asistente, con los atributos **sin** prefijo `android:` (son recursos internos del sistema y `aapt2` rechazaría la forma con prefijo). **Y sin `settingsActivity` a propósito**: `VoiceInteractionServiceInfo` descarta al asistente cuya pantalla de ajustes no pertenezca a una app del sistema (`FLAG_SYSTEM`), y una APK instalada a mano nunca lo es — con ese atributo puesto, CORT desaparecía de la lista de asistentes sin ningún aviso. Los ajustes se piden ahora por `RoleManager`, que es la vía pública y no cuesta aparecer |
| `CortNative.pausa()` / `reanuda()` + `musicPlaying()` | el **freno del oído**. Al ir a segundo plano, Java cierra el `SpeechRecognizer` **y avisa** con el evento `pause`; al volver, manda `resume`. Sin ese aviso, `ui/js/voice.js` reabría la escucha cuatrocientos milisegundos después de cerrarla: un micro abierto en bucle detrás de la app, que es lo que se nota como «traba». La cara además no rearma con la pantalla apagada, mientras suena música (`musicPlaying()` → `AudioManager.isMusicActive()`, con un margen de 1,5 s para no confundir la música con la propia voz de CORT) ni mientras la ventana 11 está contando caché, y se españa cada vez más si nadie dice «Oye CORT» |
| `CortNative.musicaCambio()` → evento `music` | el reproductor **avisa** a la cara en cada play, pausa y canción nueva. La pantalla de música pinta su barra a partir de ese evento y no pregunta cada medio segundo: cero martillazos al puente |
| `llave.sh` | la llave de firma, en este orden: secreto `CORT_APK_KEYSTORE_B64` (+`_PASS`) ▸ la caché de Actions (`apps/apk/keystore`) ▸ generar una nueva y dejarla en esa carpeta. Escribe en `firma.txt` cuál usó y deja la huella SHA-256 como anotación del check-run. **Medido en `v0.2.10-demo`: el segundo camino no sirve entre Releases** — `actions/cache` guarda por *ref* y cada etiqueta es otro ref, así que la huella cambia y hay que desinstalar. Lo que sí es permanente es el secreto; se fabrica con `scripts/llave-nueva.sh`. La llave está en `.gitignore`: el repo es público y con esa llave cualquiera firmaría actualizaciones de su CORT |
| `scripts/llave-nueva.sh` (en la raíz del repo) | genera en TU PC la llave definitiva con `keytool` (la misma receta que el runner) y deja `cort-llave.b64` + `cort-llave.pass` listos para pegar como los dos secretos del repo. Imprime la huella SHA-256 para cotejarla con el `-firma.txt` |

`assets/ui/` y `res/mipmap-*/` están en `.gitignore`: son generados. La única
copia buena de la cara es la que sale del `ui/` del commit etiquetado, y el icono
viene del `base/CORT-IA-1.1.0.apk` (o de `scripts/marca.py` si ese binario no
está en el checkout). El logo de los **instaladores de escritorio** es el mismo
anillo tal cual lo enseña el teléfono: `bash scripts/icono-del-telefonito.sh`
recompone el icono adaptativo del APK original (`ic_launcher_foreground.png` a
288 px sobre `#02040a`, que es la proporción 72/108 con la que Android lo recorta)
y escribe `desktop/build/icon.png` e `icon.ico` — el `.ico` lo embolsa
`scripts/empaqueta-ico.py`, porque el ImageMagick de este portátil lee ICO pero
no sabe escribirlos. Se corre una vez y los dos archivos se commitean.
`apps/apk/keystore/` también está ignorado, pero por lo contrario: es lo que
**no** puede salir de la caché del pipeline.

## Usarlo

1. En la Release, descarga **`CORT-IA-2.1.0.apk`**. No hay dos versiones que
   elegir: es el único APK y lleva todo dentro.
2. **Instalar encima: se puede desde esta versión.** `versionCode` es
   `2·10000 + 1·100 + 0 = 20100`, por encima del `20000` del `2.0.0` y del `10300`
   del `1.1.0`, el paquete sigue siendo `com.cort.ia` y **la firma es la misma**, así
   que Android lo pone encima y **no se pierde nada**: quedan el micrófono concedido,
   el doble toque, el permiso de los avisos, la dirección del PC y lo que CORT anotó
   **en el teléfono** (tus gustos y tus listas). El juez público es el `-firma.txt`:
   si las dos Releases traen
   `SHA-256 digest: faabef468f3ae04fdfab9659d6a051c453d6ded7b965468c9c3b85caffa31977`,
   es la misma llave y se instala encima. **La única excepción**: si tu teléfono aún
   tiene un APK de antes de `v0.2.13-demo` —ésos salieron firmados con llaves
   desechables, y para Android una firma distinta es otra aplicación—, ésa sí exige
   desinstalar **una vez**, y después ya no. No se va el cerebro: notas, recuerdos,
   pendientes y claves viven en el PC, en `~/.cort/` (`%APPDATA%\CORT\` en Windows).
   Los dos secretos (`CORT_APK_KEYSTORE_B64` y `CORT_APK_KEYSTORE_PASS`) están puestos
   en Settings ▸ Secrets and variables ▸ Actions (medido el 2026-10-21) y
   `llave.sh` firma desde entonces con **tu llave fija**; `v0.2.13-demo` ya lo hizo y
   su `-firma.txt` declara `actualizar instalando encima: sí`.
3. Instálalo y concede el micrófono cuando lo pida.
4. Para que use tu PC por Wi‑Fi: en el portátil, `bash scripts/telefono.sh` y
   anota la dirección que imprime; en el teléfono, botón **CORT · PC** ▸
   «Conectar con mi PC por Wi‑Fi» y escríbela (`http://192.168.100.171:8000`).
   Los dos tienen que estar en la misma red. Si el PC no contesta, la app abre
   sola la cara embebida y funciona sin servidor.
5. Para que mande el doble toque de los audífonos: botón **CORT · PC** ▸ «Poner
   CORT como asistente» (o di **«pon CORT como asistente»**), y acepta el cuadro
   de Android. En Android 8 y 9, o si el fabricante no ofrece el cuadro, Ajustes ▸
   Aplicaciones ▸ Aplicación de asistencia predeterminada ▸ **CORT**. La propia
   fila del menú dice en qué estado está (`ya elegido` / `pendiente` / `bloqueado
   por el fabricante`). En los Galaxy Buds, la acción del doble toque se deja en
   «Asistente digital».
6. Para que te lea los avisos: botón **CORT · PC** ▸ «Dar el permiso de los
   avisos» y activa CORT en la lista del sistema. Desde ahí, di
   **«lee mis avisos»** y te cuenta en voz alta los últimos tres. «olvida los
   avisos» los borra de la RAM.
7. Para la música: **dale el permiso de los medios**, que es lo único que le
   falta a CORT para ver tu discoteca. Hay tres puertas y las tres llevan al
   mismo cuadro de Android: el aviso que pinta la pantalla **Música** cuando no
   ve nada («Dar permiso a la música y los archivos» — es pulsable), decir
   **«ponme algo que me guste»** (ahí `musicaAutomatica()` comprueba y abre el
   cuadro solo), o el botón flotante **CORT · PC** ▸
   «Dar permiso a la música y los archivos (hecho/pendiente)», que dice en su
   propia fila si ya está concedido. Después busca por título o artista, o di
   **«ponme algo que me guste»**. Cada canción tiene su 👍/👎, y con tres o cuatro
   valoraciones CORT ya te perfila artistas y géneros. En vídeo, los botones
   **◂ cuadro ▸** mueven un fotograma. Se reproduce con la cara cerrada: es un
   servicio en primer plano, no un `WebView` sonando.
8. Para las llamadas: di **«llama a Samuel»** en la pantalla de Charla o del
   canal de voz. `READ_CONTACTS` y `CALL_PHONE` **no** se piden al abrir la app:
   se piden la primera vez que la llamada sale mal — sin permiso de contactos el
   índice devuelve vacío, el puente contesta `ok:false` (`Telefono.llamar`), y
   entonces `llamarA()` de `ui/js/hud.js` llama a `pidePermisoTelefono()` y te lo
   dice en voz alta: «No lo tengo en los contactos. Dame un momento y pídeme la
   llamada otra vez.». Con `CALL_PHONE` concedido, marca directo (`ACTION_CALL`);
   sin él abre el marcador con el número puesto (`ACTION_DIAL`) para que tú
   pulses verde — que es lo que Android deja a una app que no es el teléfono del
   sistema.
9. Para el **MV con la letra**: abre la hoja **MV** (☰ ▸ MV, deslizando, o di
   **«abre el mv»** / «el video con la letra»). Si lo que suena es un vídeo, la
   imagen se pone con la misma `content://` del reproductor y el orbe se encoge a
   una esquina girando como disco; si es audio, la hoja lo dice en vez de dejar un
   cuadro negro y la letra se muestra igual. La letra la trae el PC por
   `/api/letras` (LRCLIB, sin clave): hace falta estar conectado por Wi-Fi. El
   botón **↻ rebuscar la letra** sirve cuando el servidor contesta saturado, y
   **copiar letra** te la deja en el portapapeles sin marcas de tiempo. Pulsar una
   línea salta a ese segundo (se lo manda al servicio y mueve la imagen a la vez).
10. Para el **modo juego**: di **«modo juego»** antes de entrar a Call of Duty (o
    usa el interruptor de la hoja Música/MV, o el botón **CORT · PC** ▸ «Modo juego
    (silencio: sí/no)», que dice en su propia fila cómo está). Con él puesto CORT
    cierra el micrófono, no pide el foco audio y no
    habla por el auricular; en la barra superior queda el badge 🎮 para que sepas
    que está callado y no apagado. **«vuelve CORT»** lo quita. No hay permiso de
    uso de aplicaciones ni lista de instalados: se pone y se quita a mano, y así se
    firmó en el manifiesto a petición de la dueña.
11. Para la **burbuja** (el puntito de CORT flotando sobre otra app): di
    **«burbuja»** o pulsa `● burbuja flotante` en el bloque **Atuendos** de la hoja
    Equipo. Necesita el interruptor **«Aparecer encima de otras apps»**, que Android
    **no** concede con un cuadro: es un ajuste de la lista. Cuando falta, Java lo
    dice con el camino exacto y la cara abre sola esa pantalla (`requestPermission
    ('burbuja')` → `CortNative.abreAjustesBurbuja()`); si tu fabricante no tiene esa
    pantalla, cae en Ajustes ▸ Aplicaciones ▸ CORT y te lo escribe en un aviso.
    Tocar el punto abre CORT y le suelta el micrófono. Con **modo juego puesto la
    burbuja no aparece nunca**, y al poner el modo juego la que estuviera puesta se
    quita sola: es la promesa del interruptor 🎮.
12. Para la **linterna**: di **«enciende la linterna»** o pulsa `🔦 linterna` en el
    bloque **Mando**. Va por `CameraManager.setTorchMode`, que **no captura imagen ni
    abre la cámara**, pero Android la protege con el permiso de cámara, así que es el
    único interruptor nuevo que hay que dar: Ajustes ▸ Aplicaciones ▸ CORT ▸ Permisos
    ▸ **Cámara**. CORT **no lo fuerza**: sin él la orden contesta «la linterna va por
    el permiso de cámara y no lo tengo» y no hace nada a escondidas.
13. Para la **agenda**: di **«¿qué tengo hoy?»**, **«mi agenda»**, **«las citas de la
    semana»**, o abre el bloque **Agenda** de la hoja Equipo y pulsa `hoy` /
    `7 días` / `abrir calendario`. Pide `READ_CALENDAR` la primera vez que preguntas
    (no al abrir la app). **Sólo lectura**: `WRITE_CALENDAR` no está ni en el
    manifiesto, y `apunta cena con Samuel el jueves a las 9` rellena el
    **formulario del calendario del sistema** para que el dedo que guarda sea el
    tuyo. Sin el permiso contesta `ok:false` con la explicación; nunca un cero
    disfrazado de «no tienes nada».
14. Para el **correo**: di **«revisa el correo»** / «¿qué hay en el correo?». No hay
    API para leer el Gmail de otra app, y CORT no simula ser Google. Lo que hace es
    **contar los avisos de Gmail que ya salieron en tu barra** (necesita el permiso
    de los avisos del paso 6) y **abrirte Gmail** con un toque. Si el oído de avisos
    está apagado lo dice en vez de contar ceros.
15. Para la **pantalla Equipo**: `☰ ▸ Equipo`, o di **«abre el equipo»**. Sale sólo
    si el puente trae `accion` (un APK viejo la esconde en vez de prometerla). Son
    seis bloques —**Voz · Mando · Cerebro · Memoria · Atuendos · Agenda**— y cada uno
    avisa en su propio pie si lo que le falta es el APK nuevo, el permiso o el PC.
    Ahí se cambian la voz y el traje, se manda el volumen y la alarma, se pregunta
    sin el portátil con `piensa…`, y se cuadra la memoria con **«sincronizar con el
    portátil»**.


## Lo que NO hace, dicho sin adornos

- **No** mantiene el «OK Google» con la pantalla apagada: esa palabra de
  activación la dice el servidor de Google y no viaja con este APK.
- **No** oye «Oye CORT» con la app cerrada: la escucha continua vive dentro del
  WebView, así que funciona con la cara abierta (o con la **burbuja** tocada). El
  panel **07 · Perfil ▸ Segundo plano** ya no promete lo contrario: su interruptor
  pide que CORT **siga vivo** con su aviso fijo —con eso siguen obedeciendo la música
  y el doble toque del auricular—, y dice en la propia frase que el micrófono queda
  cerrado para no trabar el teléfono. Sus siete estados (`enabled`, `running`, `mic`,
  `notif`, `overlay`, `battery`, `maker`) los mide Java en `bgStatus()`; antes la cara
  preguntaba claves que no existían y el panel se quedaba mudo.
- **No contesta tus llamadas ni hace de buzón de voz, y no lee SMS ni el
  contenido de tus chats de WhatsApp.** Contestar por ti exige quedarse con la
  pantalla de llamadas del sistema (`ROLE_CALLING` + `InCallService`), y para
  SMS/chat no hay API: se anunciaría como hecho y no lo está. Lo que sí hace:
  ver la barra de notificaciones (con tu interruptor), ver tus contactos y marcar.
- **Correo y agenda: lo que se puede saber sin meterse en tu cuenta.** CORT lee
  tus **citas del calendario** (`READ_CALENDAR`, sólo lectura) y te las cuenta o las
  pinta en la hoja Agenda; `apunta` abre el formulario del calendario del sistema
  ya relleno y **el que guarda eres tú**, porque `WRITE_CALENDAR` no está pedido a
  propósito. Del **correo** no lee el contenido: cuenta los avisos que `Avisos` oyó
  del paquete de Gmail y te abre la app. No hay IMAP ni contraseña de correo dentro
  del APK, y decir «leo tu Gmail» sería mentira.
- **No** ordena archivos por su cuenta sin permiso: `MANAGE_EXTERNAL_STORAGE` es
  un interruptor que pone la dueña en Ajustes, y cualquier reorganización sale
  primero como plan para confirmarlo. Borrar, sólo si lo dices.
- La cara embebida, sin PC, **no** tiene los modelos de Ollama ni el optimizador:
  eso vive en el backend del portátil (1,8 GiB no con un `ollama serve`), y por eso
  el paso 4 es el que de verdad da las once ventanas. Lo que **sí** hay sin PC es la
  ronda 2.1: mando del aparato, voz, memoria en SQLite, atuendos, agenda y un
  **cerebro propio** — `Mente` con la nube que ajustes tú (Groq, OpenAI, DeepSeek,
  Mistral, Qwen, Anthropic u Ollama en red local) y, sin nube, los 35 patrones de
  `assets/habilidades.json`, que reconocen la orden y la reenvían a `Acciones`.
  «Lee mis notas» o la pantalla **Código** sin PC contestan el aviso de «sin PC»
  traducido a una frase, no un silencio.
- La pantalla **Código** ejecuta en el **PC**, no en el teléfono: Android no deja
  abrir un shell desde una app normal, y decir lo contrario sería mentira.
- **No** lee WhatsApp por la puerta de atrás: `Avisos.java` mira la **misma barra
  de notificaciones** que mirarías tú. Si tienes las previsualizaciones apagadas
  en WhatsApp, CORT ve «Mensaje (1)» y no el texto — eso es el teléfono hablando,
  no este APK.
- **No** guarda los avisos: ni en disco, ni en SQLite, ni en un servidor. Doce
  líneas en RAM del proceso, se van solas al pasar y «olvida los avisos» las tira.
  El permiso se quita en Ajustes en un segundo, y el menú lo muestra en su
  etiqueta («permiso: hecho» / «permiso: pendiente»).
- Nada de esto está verificado con un dedo encima: no hay teléfono en esta
  máquina. Lo que sí comprueba el pipeline es que el Java compila contra la
  plataforma (`javac` revisa las firmas de `VoiceInteractionSession.onShow`,
  `RecognitionService.Callback.error`, `NotificationListenerService.onNotificationPosted`,
  `MediaSession`, `ContactsContract`, `CalendarContract.Instances` y compañía),
  que `aapt2` enlace el manifiesto, que `apksigner` valide la firma y
  que el APK quede alineado. Y `scripts/prueba-costura.py`, que corre aquí sin
  teléfono, revisa en **nueve sectores** que manifiesto, Java, puente y cara se
  nombran lo mismo: los **59 `@JavascriptInterface`** del puente y las ocho funciones
  del contrato 2.1 (`accion`, `ajusteVoz`, `memoria`, `mente`, `atuendo`, `agenda`,
  `burbuja`, `comparte`) —cada una comprobada en los **cuatro** sitios donde vive:
  la clase, el puente, la cara y el manifiesto/portátil—, los tres eventos nuevos,
  los `<queries>`, el `FileProvider`, las reglas de `res/xml`, los 35 patrones de
  `habilidades.json` y las dos puertas `/api/*` de la sincronía. También que no se
  cuele ningún permiso desproporcionado: sin `PACKAGE_USAGE_STATS`, sin
  `QUERY_ALL_PACKAGES`, sin `READ_SMS` y sin `WRITE_CALENDAR`.
