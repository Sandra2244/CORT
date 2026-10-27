# Mapa del repo — paso 0.2 de la Fase 0

**Medido:** 2026-10-25 · **Rama:** `v0.2-demo`, en el commit `0a471df` (APK publicado
**2.11.0** / `versionCode` **21100**) · **Paso de sólo lectura:** no se tocó ni un archivo
de código; esto describe, no arregla.

**Vuelto a medir el 2026-10-27**, después de la limpieza (commit `b4e6e09`, el APK base ya
no viaja versionado) y del **corte 3** de la refactorización (`marco.js` + `charla.js`). Los
números de los apartados 1 y 2 son de hoy; lo que se escribió el 25 y no ha cambiado se
queda como estaba.

**Cómo se midió, para que se pueda repetir.** Todo lo que sigue sale de comandos sobre
este disco, no de memoria ni del README: `git ls-files` (**235 archivos rastreados**,
**8.458.306 B de contenido versionado**), `wc -l`, `du -sh`, `grep -c` y lectura de las
líneas citadas.
Cada dato lleva `archivo:línea`. Las cuentas de pruebas (314 `ok`, 213 de la sonda, etc.)
**no** van aquí: esas son la línea base del paso 0.3, y ponerlas ahora sería heredarlas.

---

## 1. Qué es CORT en el disco, en una frase

Cuatro cuerpos que se hablan por HTTP y por un puente de JavaScript, y un quinto que sólo
empaqueta:

| cuerpo | dónde | tamaño medido | qué es |
| --- | --- | --- | --- |
| **La cara** | `ui/` | 1,0 MB sin `vendor` · **16.462 líneas** de la cara que viaja (14.257 en 25 módulos JS + 1.994 de CSS en tres hojas + 211 de `index.html`); las cuatro sondas suman 1.925 más, hasta 18.387 | HTML, CSS y módulos ES + Three.js; viaja **dentro del APK** como `assets/ui/` y también la sirve el backend en el PC |
| **El aparato** | `apps/apk/` | 57 MB en disco (17 MB son `build/`, sin versionar) | **32 `.java` = 14.501 líneas**, más `Oido.kt` con 616 (**15.117 entre los dos**) en `src/com/cort/ia/`, el manifiesto, los recursos y el `compilar.sh` sin Gradle |
| **El núcleo de casa** | `backend/app/` | 808 KB · **17 módulos `.py` versionados = 5.925 líneas** (19 archivos y 6.823 líneas en el disco de hoy: `pool.py` y `reproductor.py` están sin commitear) | FastAPI que ve Ollama, los modelos, la voz, los archivos y la memoria del portátil |
| **El puente de escritorio** | `desktop/` | 268 MB en disco, casi todo `node_modules` | Electron (`main.cjs`, 151 líneas) que levanta el backend si no está y mete la cara |
| **La fábrica** | `.github/workflows/build.yml` | 111.250 B · **1.578 líneas versionadas** (1.634 con los dos pasos que añadió el corte 3) | Compila los tres envases del APK y los instaladores, y publica la Release |

Fuera del versionado, en el disco: `.venv` (136 MB), `desktop/node_modules` (268 MB),
`apps/apk/build` (17 MB), `apps/apk/assets/motor` (38 MB, el modelo Vosk) y
`backend/app/__pycache__` (420 KB). Los cinco están en `.gitignore` y ningún archivo de
esos aparece en `git ls-files`.

Dentro del versionado pesan más que nada: `ui/vendor/three.module.js`
(**1.272.972 B**, 53.044 líneas), `docs/screenshots/escritorio-linux.png`
(478.223 B), `scripts/prueba-costura.py` (**327.868 B**, 5.282 líneas — la suite grande del
repo), siete montages (`docs/referencias/`, 200–300 KB cada uno), `desktop/build/icon.png`
(250.457 B) y `README.md` (219.097 B). El APK base (**1.815.389 B**, la 1.1.4 de referencia
de la burbuja) ya **no** está: salió del versionado en `b4e6e09` y viaja como respaldo fuera
del repo.

## 2. La cara (`ui/`) y su grafo de módulos

Por tamaño (medido con `wc -l`, y vigilado archivo por archivo por
`scripts/prueba-tope.mjs` contra `scripts/tope-lineas.json` — la regla de la dueña: mil
líneas máximo por archivo de interfaz, y la deuda sólo se admite mientras baje):
`js/telefono.js` 2.769 · `js/hud.js` 2.571 · `js/pantallas.js` 2.184 ·
`js/diccionario.js` 1.601 · `css/hud.css` 1.183 · `js/charla.js` 899 ·
`js/orbe-plexo.js` 757 · `css/apps.css` 687 · `js/orb.js` 637 · `js/voice.js` 399 ·
`js/gestures.js` 302 · `js/arnes.js` 285 · `js/marco.js` 275 · `js/automatiza.js` 267 ·
`js/traje.js` 242 · `js/orbe-cara.js` 233 · `index.html` 211 · `js/centro.js` 191 ·
`js/mandos.js` 143 · `css/jarvis.css` 124 · `js/windows.js` 91 · `js/placa.js` 88 ·
`js/pasos.js` 82 · `js/android-bridge.js` 57 · `js/ordenes.js` 53 · `js/icons.js` 38 ·
`js/texto.js` 29 · `js/letra.js` 28 · `js/md.js` 40.

**La deuda que queda visible.** Cuatro archivos pasan del millar y los cuatro están
registrados en `tope-lineas.json` con su techo de hoy: `telefono.js` 2.770, `hud.js` 2.572,
`pantallas.js` 2.185, `diccionario.js` 1.602. El techo sólo puede bajar; subirlo o borrar la
fila pone la compilación en rojo, así que la deuda no se esconde. En `pantallas.js` los
siguientes cortes están marcados por los rótulos de sector y medidos sobre el archivo de
hoy: «02 · CÓDIGO» (`:331-719`, 389 líneas) sale primero, luego «03 · MÚSICA» con su
transporte (`:720-1725`, 1.006) y «04 · MV» con el agua y el modo juego (`:1726-2184`,
459). Los tres fuera dejan la hoja en ~330 líneas y el millar se cumple sin apretar nada.

**Los cortes de la refactorización.** Paso 1 (`texto.js`): los tres pliegues que estaban
copiados cinco veces. Paso 2 (`md.js`, `letra.js`): el markdown, la hora de la burbuja y el
parser de la letra. Paso 3 (esta ronda): `marco.js` —el `ctx` vivo, el puente de Java, la
tabla de hojas, las bottom sheets, el cajón, la pregunta «¿hay núcleo?» y el router `ir()`
con registro de ganchos— y `charla.js`, que se llevó los 856 líneas del sector «01 · CHARLA»
de `pantallas.js` (3.035 → 2.184). El orden de carga es marco → carcasa → hojas, y el import
sólo va hacia arriba: ninguna hoja importa `pantallas.js`, así que no hay círculo.
`scripts/lib-cara.mjs` declara qué archivos son «la cara» y es la MISMA lista que lee
`prueba-costura.py`, para que una hoja nueva no pueda quedarse sin medir en silencio.

Quién importa a quién (medido sobre los `import` reales):

```
index.html ──> hud.js
hud.js ──> windows.js, voice.js, pantallas.js, telefono.js, mandos.js, diccionario.js
pantallas.js ──> marco.js, charla.js, telefono.js, centro.js, arnes.js, pasos.js, letra.js, texto.js
charla.js ──> marco.js, md.js, ordenes.js, texto.js
marco.js ──> texto.js                    (y nada más: el marco no sabe qué hojas existen)
centro.js ─┐
arnes.js ──┴──> diccionario.js          (DICCIONARIO y TOTALES: 91 intenciones / 736 frases,
                                         diccionario.js:1593)
telefono.js ──> automatiza.js, diccionario.js
gestures.js ──> voice.js
orb.js ──> ../vendor/three.module.js, traje.js
```

`hud.js` es la raíz y el que decide el nodo: `API = ''` en Android
(`ui/js/hud.js:26-29`) y `discoverApi()` corre en paralelo al arranque
(`:34-56`, `:75`). **`diccionario.js` es el sumidero común**: la cara, Java y las pruebas
leen de ahí, y `TOTALES` (`:1593`) es la única cifra de órdenes que existe. Que un `import`
punte a algo inexistente mata la cara entera (pasó en la 2.10.0 con `handleTelefonoEvento`
sin `export`); por eso la costura tiene un sector que resuelve cada import contra el
archivo de destino (`33 · enlaces de módulos`, 113 nombres) y otro que exige que toda hoja
que importe el marco esté en la lista de `lib-cara.mjs` (`33 · la lista de la cara`).

**Media adopción de los íconos (importante para el paso 1.3).** `ui/js/icons.js` ya existe
y **es un set SVG de línea con un solo grosor** (`icons.js:1-2`, «sustituyen a los emojis,
que Android pinta a color»). Pero sólo lo consumen `index.html` (11 `data-ic=`) y `hud.js`
(21 llamadas a `ic(`). **`pantallas.js`, `charla.js`, `marco.js`, `telefono.js`, `centro.js`
y `arnes.js` no lo usan nada**: ahí siguen los glifos, y desde el corte 3 las fichas de pantalla están en
`marco.js` (`✦` en `marco.js:75`, `⌘` en `:87`, `⌬` en `:91`), con los modos de la Charla en
`charla.js:78` y `charla.js:117`, la sugerencia de `charla.js:352` y los títulos de
`arnes.js:163` y `arnes.js:198`. O sea: T3 no está por empezar, está a medias.

## 3. El aparato (`apps/apk/`)

**Núcleo del aparato.** `MainActivity.java` (1.044 líneas) es la única Activity: monta el
WebView en `MainActivity.java:129`, cuelga el puente en `:144`, intercepta los assets en
`:342` y carga en `:334`. En `onResume` (`:287`) recarga si no hay URL, activa los mandos y
`puente.reanuda()` (`:296`); en `onPause` (`:304`) apaga mandos, `puente.pausa()` (`:307`,
cierra el micro) y suelta los sentidos; en `onDestroy` (`:314`) libera el puente.
Alrededor: `Aparato.java` (307) da el JSON de hardware, `Sentidos.java` (245) los sensores,
`ArchivosProvider.java` (234) es el `FileProvider` con autoridad `com.cort.ia.files`
(`:54`), `Panel.java` (119) el baldosín, `Asistente`/`Sesiones`/`Reconocimiento` (25/25/57)
el traje de asistente del sistema —vacío a propósito, `Asistente.java:6-12`—, y
`AlarmaSuena.java` (37) un receptor de tres líneas que reenvía a `Alarma`.

**Cerebro y decisiones.** `Cerebro.java` (507) tabla frase→acción, `Razon.java` (828)
cuentas y fechas, `Mente.java` (325) enruta quién responde, `Acciones.java` (1.219) ejecuta
órdenes del sistema, `Recuerdos.java` (706) memoria SQLite del teléfono,
`Sincroniza.java` (351) la única clase que habla HTTP con el portátil, `Nube.java` (468) y
`Ollama.java` (801) los proveedores, `Elige.java` (136) y `Despertar.java` (192) las
piezas de música y de alarma compuesta, `Agenda.java` (216) y `Telefono.java` (162).

**Medios.** `Reproductor.java` (897) servicio en primer plano con MediaPlayer+MediaSession,
`Musica.java` (559) índice del teléfono, `Oido.kt` (616) Vosk —Kotlin a propósito,
`Oido.kt:19-24`—, `VozNueva.java` (679) los motores TTS, `Alarma.java` (518) `AlarmManager`,
`Ecualizador.java` (151), `Paleta.java` (356), `Timbre.java` (92).

**Interfaz nativa.** `Flotante.java` (629): la burbuja **no es un servicio**, es un `View`
estático con `WindowManager.addView` (`Flotante.java:213`), publicado en el hilo principal
con `new Handler(Looper.getMainLooper()).post(...)` (`:270`, tras importar ambas clases en
`:71-72`) y chequeo de hilo (`:250`). El arrastre está acotado por `MARGEN_DP = 10` (`:91`) y el
diámetro es la constante `DIAMETRO_DP = 44` (`:89`) — dato vivo para el paso 1.1.

**Las clases de papel** (se prueban sin teléfono, sin `android.*`): `Razon.java`,
`Elige.java` y `Despertar.java` no importan nada de Android (medido con `grep -L`);
`Cerebro`, `Nube`, `Mente` y `Ollama` sólo tocan stubs. Su runner es
`scripts/prueba-mente.sh`, que copia las 7 clases y sus gemelos (`:66-68`) y ejecuta las 7
suites en el bucle de `:99`; el oído tiene el suyo en `scripts/prueba-oido.sh`. Los gemelos
viven en `apps/apk/prueba/papeles/` (**19 archivos** `org/json`, `android/media`,
`android/net`, `content`, `util/Log` y un clon de `Timbre`) y las pruebas son
`apps/apk/prueba/Prueba.java` … `Prueba7.java` (7 archivos) + `PruebaOido.kt`.

## 4. El contrato del puente (lo que la cara puede pedir)

**83 métodos `@JavascriptInterface` en `CortNative.java`** (el `grep -c` da 85 porque dos
están dentro de comentarios, en las líneas 52 y 1632; 83 nombres distintos, sin
duplicados). No hay un `switch` global: cada método se llama por su nombre desde JS. El
único dispatcher de acciones es `teclaMedia`, `CortNative.java:878` con sus casos
`"pausa"/"play"/"siguiente"/"anterior"/"parar"` (`:879-883`). Los eventos vuelven a la cara
por `window.__cortNative.emit(...)` desde `cuadro()` (`:2070-2074`).

Por familias (todos los números de línea de este párrafo son de `CortNative.java`): escucha
(`listen:264`, `stopListening:366`, `cancelListening:377`,
`oidoEstado:602`, `oidoPropio:623`), voz (`speak:459`, `stopSpeaking:514`, `voices:560`,
`ajusteVoz:1665`), permisos (`hasPermission:643`, `requestPermission:648`, 4
`abreAjustes*`), fondo y nodo (`bgStatus:750`, `setBackground:790`, `keepAwake:796`,
`setPc:805`, `menuPC:1202`, `abreMenu:1213`), capacidades (`capacidades:948`,
`disponible:589`, `avisos:982`), música (28 métodos entre `musicaPuedeLeer:1069` y
`musicaEstado:1448`, más `ecualiza:1326`), sistema (`accion:1638`, `alarma*:1349-1358`,
`modoJuego:1539`, `contactos:1600`, `llamar:1610`), memoria y cabeza (`memoria:1695`,
`mente:1705`, `atuendo:1715`, `agenda:1728`, `burbuja:1758`, `comparte:1797`,
`sensores:1912`, `aparato:1922`). Y un detalle: `accion` delega la linterna y
las apps en `apps/apk/src/com/cort/ia/Acciones.java`.

**Seis métodos que la cara no menciona nunca** (medido: cero coincidencias en `ui/` para
cada nombre): `abreAjustesArchivos` (`:1092`), `abreAjustesAvisos` (`:1004`),
`abreAjustesBurbuja` (`:1769`), `menuPC` (`:1202`), `puedeMarcar` (`:1595`),
`puedeOrdenarArchivos` (`:1081`). Son 6 de 83. **Al revés no hay ningún hueco**: la cara no
llama a nada que Java no tenga. El contrato escrito está en
`docs/CONTRATO-PUENTE-2.1.md` y su resumen en `CortNative.java:27-36`.

## 5. Manifiesto y los tres envases (con la cuenta corregida)

`apps/apk/AndroidManifest.xml` (459 líneas), paquete `com.cort.ia` (`:108`). Medido sobre el
XML **sin contar los comentarios** (`perfil.py:162` avisa justo de ese error):

- **24 `<uses-permission>`** declarados (`:110` a `:210`): INTERNET, ACCESS_NETWORK_STATE,
  RECORD_AUDIO, MODIFY_AUDIO_SETTINGS, VIBRATE, CAMERA, SET_ALARM,
  REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, SYSTEM_ALERT_WINDOW, READ/WRITE_EXTERNAL_STORAGE,
  READ_MEDIA_AUDIO/VIDEO/IMAGES/VISUAL_USER_SELECTED, MANAGE_EXTERNAL_STORAGE, CALL_PHONE,
  READ_CONTACTS, READ_CALENDAR, FOREGROUND_SERVICE, FOREGROUND_SERVICE_MEDIA_PLAYBACK,
  POST_NOTIFICATIONS, WAKE_LOCK, BLUETOOTH.
- **1 actividad, 1 receptor, 1 provider y 6 servicios**, de los cuales **5 van protegidos
  por un permiso `BIND_*`**: `.Panel` `BIND_QUICK_SETTINGS_TILE` (`:360`), `.Asistente`
  (`:372`) y `.Sesiones` (`:385`) ambos con `BIND_VOICE_INTERACTION`, `.Reconocimiento`
  `BIND_SPEECH_RECOGNIZER` (`:391`) y `.Avisos` `BIND_NOTIFICATION_LISTENER_SERVICE`
  (`:405`). El sexto, `.Reproductor` (`:421`), es de primer plano y no es `BIND_*`.
- `<queries>` en `:227-270`: 7 intents y 12 paquetes.

**Ojo con la cifra publicada, que es cierta pero está mal etiquetada.** El README y los
`-firma.txt` dicen «28 permisos y 4 servicios `BIND_*`». `scripts/audita-apk.sh:244-259`
cuenta **cadenas `*.permission.*` del pool de strings UTF-16 del manifiesto binario**, así
que los 28 son **24 permisos declarados + las 4 cadenas `BIND_*` que protegen servicios**, y
esos 4 son las cadenas *distintas* de **5 servicios** (`.Asistente` y `.Sesiones` comparten
`BIND_VOICE_INTERACTION`). El número no está mal; la palabra «servicios» sí. Lo dejo
anotado como deuda de documentación (punto 9, fila 7), no lo cambio aquí porque tocar el
README y el auditor es otro paso.

**Cómo salen los tres envases.** Tres regiones marcadas en el propio manifiesto
(`PERFIL-DESDE/HASTA`: llamadas en `:177`/`:197`, acciones-asistente en `:308`/`:329`,
servicios-privilegiados en `:349`/`:412`) que corta `apps/apk/perfil.py`: `PERFILES` en
`perfil.py:90-93` (completo no corta nada; núcleo corta las tres) y recorte en `recorta()`
(`:99`), con el meta-dato `com.cort.ia.PERFIL` clavado en `:136-155`. Medido sobre las
regiones: «llamadas» se lleva **3 permisos** (`CALL_PHONE`, `READ_CALENDAR`,
`READ_CONTACTS`) → el núcleo queda en **21 permisos y 0 `BIND_*`**, exacto a lo publicado;
«servicios-privilegiados» se lleva los **5 servicios**. `compilar.sh:365-367` genera
`build/manifest-$PERFIL.xml` y el tercer envase es núcleo + `APK_SIN_OIDO=1`
(`build.yml:534-538`, procesado en `compilar.sh:155` y `:232`, que quita las 4 `.so` y el
modelo de 39,8 MB).

## 6. El núcleo de casa (`backend/app/`)

19 módulos, 6.823 líneas (contados con `wc -l` el 2026-10-27, en el árbol de trabajo:
`pool.py` y `reproductor.py` están **sin commitear**; versionados van 17 con 5.925).
`main.py` (664) con
**51 rutas** (contadas una a una, sin duplicados; no hay `APIRouter`: todas cuelgan de
`app`), `models.py` (734) el gestor de Ollama, `actions.py` (724), `musica.py` (623) —lee la
discoteca: ID3v2, `TLEN` en milisegundos, estilo de `TCON` **o de la carpeta**, `.m3u`/`.pls`
(2.18.0)—, `sensors.py` (532), `reproductor.py` (546) —**manda** el reproductor del sistema
por MPRIS sobre el bus de sesión, con `python3-dbus` (2.20.0)—, `brain.py` (509) el cerebro
híbrido local→nube→offline, `copiloto.py` (389), `pool.py` (352), `conocimiento.py` (291) —el
índice de lo que hay en sus carpetas, J4—, `voz.py` (318),
`optimize.py` (317), `actualiza.py` (180), `organiza.py` (178), `memory.py` (135),
`config_store.py` (122), `letras.py` (87), `rutas.py` (81) y `local_commands.py` (41).

Por grupos (números medidos en `main.py` el 2026-10-27, tras la ronda 2.20.0): charla y
estado (`/api/chat:124`, `/api/status:144`, `/api/port:150`, `/api/support:175`,
`/api/history:180`), configuración y cerebro (`/api/config:203/208` con máscara,
`/api/brain/test:214`), memoria, notas y perfil (`/api/notes:224/229`,
`DELETE /api/notes/{id}:236`, `/api/memories:266/276`, `/api/profile:189/195`), archivos
(`/api/files:241`, `/api/lee:246`, `/api/tree:260`, `/api/organizar:601` y su
`/aplicar:607`), modelos (`/api/models:488`, `/api/models/progreso:495`, `pull:501`,
`cancel:508`, `rm:514`, `use:519` y `ollama:525` — la única ruta que enciende el servidor,
no existe `/api/ollama` suelta), voz y música (`/api/voice:307`, `/api/voice/say:328`,
`/api/music:346`, `/api/audio:362`, `/api/play:375`, `/api/play/estado:387`,
`/api/music/lista:448`, `/api/letras:595` y las **cuatro de la 2.20.0**:
`/api/reproductor:417`, `/orden:423`, `/abrir:430`, `/ventana:437`), sistema
(`/api/command:136`, `/api/launch:460`, `/api/open:471`, `/api/weather:299`), mantenimiento
(`/api/optimize:539`, `clean:546`, `kill:553`, `/api/update:634`, `/api/update/aplicar:640`)
y copiloto (`/api/copiloto:614`, `/api/copiloto/plan:621`, `/api/copiloto/ejecuta:627`).
Esas nueve agrupaciones suman las **51** sin dejar ninguna fuera.

**Configuración y secretos.** `.env` se carga antes de importar `brain`
(`main.py:47-51`); CORS sólo con localhost en cualquier puerto (`main.py:80-85`); sin caché
en API y UI (`main.py:88-104`); la cara se monta en el mismo puerto si `CORT_SERVE_UI=1`
(`main.py:569-571`). **El puerto y el host no viven en el código**: los fija
`scripts/run.sh:10` (`CORT_PORT:-8000`) y `:44` al invocar uvicorn. El arranque llama
además a `scripts/puente-dbus.sh` (`:19`), que **enlaza el `python3-dbus` del sistema
dentro del `.venv`** —la binding no se puede instalar con pip y sin ella `reproductor.py`
sólo puede abrir la canción, no gobernarla—; comprueba la versión de Python antes de enlazar
porque los `_dbus_*` son binarios, y si falta avisa con el comando exacto sin frenar el
arranque. La prioridad es
`cort_config.json` > env > default (`config_store.py:10,62-83`) y las claves se enmascaran
(`config_store.py:86-95`). `OLLAMA_HOST` se decide en `models.py:164-166` con `setdefault`
para no pisar el de la dueña (`:383`); el modelo por defecto es `qwen2.5:3b`
(`config_store.py:55-56`). En disco existe `backend/.env` con GROQ/GEMINI **vacíos** y está
ignorada (`.gitignore:4`); la llave del APK nunca entra al repo (`.gitignore:12`).

**Persistencia.** `rutas.py:36-46`: datos en `~/.cort/` (o `%APPDATA%\CORT` en Windows, o
`CORT_HOME`). Dos archivos: `cort_config.json` (`config_store.py:25`) y `cort_memory.db`
(`memory.py:17`), SQLite con 4 tablas (`memory.py:22-36`): `conversacion`, `perfil`,
`notas`, `pendientes`. La primera arrancada **copia** (no mueve) lo viejo de `backend/`
(`rutas.py:51-66`). **Backup: no existe** en el backend. Los gustos y playlists de música no
van a este SQLite: viven en el teléfono (SharedPreferences) y suben como recuerdos por
`POST /api/memories` (`main.py:268-288`).

## 7. El puente de escritorio y la fábrica

`desktop/main.cjs` (152 líneas): puerto 8000 por defecto (`main.cjs:21`), sondea
`/api/port` (`:55-62`), y si no hay backend busca Python/uvicorn y levanta uno propio con
`CORT_SERVE_UI=1` (`:78-102`); empaquetado sirve `resources/ui` por un mini-servidor
(`:39-52`) y en desarrollo cae a `http://127.0.0.1:8080` (`:127`).
`scripts/run-desktop.sh` crea `.venv`, instala y lanza `npx electron .`. Empaquetado:
electron-builder con NSIS en Windows (`package.json:27-36`) y AppImage + .deb en Linux
(`:37-41`); `extraResources` mete `ui/` y `backend/*.py` (`:22-26`).

**El pipeline** (`.github/workflows/build.yml`) corre con `workflow_dispatch` o empujando
una etiqueta `v*` (`:14-17`) — por eso empujar una rama sin etiqueta **no** gasta minutos.
Job `build` (matriz Windows/Ubuntu) → job `apk` (`:152-399` encadena todas las pruebas, que
es hoy el único lugar donde corren en fila) → compilar (`:400-446`), bautizar (`:447-455`),
núcleo (`:456-510`), núcleo-ligero (`:511-552`), subir (`:553-564`) → job `release` **sólo
si hubo etiqueta** (`:568`, `softprops/action-gh-release@v2`, cuerpo en `:586-591`).

**Cómo se versiona.** `APK_VERSION: "2.11.0"` en `build.yml:73` debe ser igual al default de
`compilar.sh:131` (`APK_VERSION="${APK_VERSION:-2.11.0}"`); la sincronía la vigila la
costura. Y `versionCode` se calcula, no se escribe: `compilar.sh:171-177` hace
`MA*10000 + MI*100 + PA`, o sea 2.11.0 → **21100** (una versión tipo `2.11.10` desbordaría
el millar: está pensado para pálchups de 0 a 99). Orden dentro de `compilar.sh`: SDK del
runner (`:157-162`, con respaldo `platforms;android-34` + `build-tools;34.0.0` en `:188`),
copia `ui/` → `assets/ui/` (`:201-204`) y **descarte de las sondas** `sonda-*.html`
(`:212`), perfil (`:365`), `aapt2 compile/link` con `--min-sdk-version 26
--target-sdk-version 34` (`:370-376`), `kotlinc` (`:393-406`), `javac --release 11`
(`:440`), `d8 --min-api 26` (`:454`), `zipalign -f 4` (`:473`), `apksigner` con v1+v2+v3
explícitos (`:499-512`), `verify` (`:521`) y la auditoría que escribe `firma.txt` (`:594`).

## 8. Pruebas: las 28 suites y cómo se corren

**28 `scripts/prueba-*` + 5 baterías de mutación (`mutaciones-*.py` y
`muta-costura-corte3.sh`) + 8 `scripts/taller-*` + 7 `Prueba*.java` + 4 sondas en `ui/` + 1
`scripts/sonda-voz.html`.** Ninguna necesita teléfono.

| suite | qué mira | necesita | comando |
| --- | --- | --- | --- |
| `prueba-costura.py` (5.282 líneas) | la costura manifiesto↔Java↔cara por sectores; lee la lista de la cara en `scripts/lib-cara.mjs` (41) en vez de copiarla | nada | `python3 scripts/prueba-costura.py` |
| `prueba-musica.py` (530) | la discoteca leída de verdad: ID3v2, `TLEN` en ms, `.m3u`/`.pls`, `/api/audio` y el reproductor del sistema | nada: monte de mentiras en `mktemp` y `reproductor.abrir` sustituido para **no salir al bus de sesión** | `python3 scripts/prueba-musica.py` |
| `prueba-reproductor.py` (682) | **MPRIS hablado**: firmas (`x`, `ox`, `s`), microsegundos, interfaces, el `None` que no es 0, el segundo plano sin ventana, la ventana con `CanRaise`, y las frases de voz/bandeja que se vuelven orden | nada: un módulo `dbus` falso graba cada `call_blocking`, y `subprocess`/`shutil`/`time` están sustituidos —**ningún reproductor real arranca**— | `python3 scripts/prueba-reproductor.py` |
| `mutaciones-reproductor.py` (202) · `mutaciones-musica.py` (114) | **las baterías de mutaciones**: 33 y 11 errores sembrados de uno en uno; el verde tiene que caerse | copian `backend/app` a `/tmp` y corren la suite con `CORT_CODIGO`; **el repo no se muta** y al final se imprimen los `md5` | `python3 scripts/mutaciones-<x>.py` (~2 min cada una) |
| `prueba-marco.mjs` (300) | **el marco ejecutado**: 11 sectores contra un DOM y un puente escritos a mano, con el orden de los ganchos (`cerrar → repintar → entrar → pintar`), la hoja escondida `mv`, el `llama` que calla sin puente y el `hayNucleo` que cachea el éxito pero reintenta el fallo. 45 hechos | node | `node scripts/prueba-marco.mjs` |
| `prueba-tope.mjs` (109) + `tope-lineas.json` | **la regla de los mil**: cada archivo de la cara contra su techo registrado; sube el techo, borra la fila o falta el libro → rojo. Se baja con `--baja` al cortar un archivo | node y `git show HEAD:` (lee el libro versionado) | `node scripts/prueba-tope.mjs` |
| `mutaciones-marco.py` (130) · `muta-costura-corte3.sh` (37) | 12 errores sembrados en una **copia en `/tmp`** del marco + 7 en la costura: el verde tiene que caerse nombrando la comprobación | lo mismo que sus suites; **el repo no se muta** (compara `md5` al final) | `python3 scripts/mutaciones-marco.py` |
| `prueba-clima.py` · `prueba-datos.py` · `prueba-lectura.py` · `prueba-modelos.py` · `prueba-organiza.py` · `prueba-voz.py` | módulos del backend con gemelos de papel y `mktemp` | nada (el de modelos finge el servidor) | `python3 scripts/<x>.py` |
| `prueba-automatiza.mjs` · `prueba-colores.mjs` · `prueba-mandos.mjs` | reglas «cuando X», 16 canales × 6 trajes, mandos de voz | node | `node scripts/<x>.mjs` |
| `prueba-mente.sh` | las 7 suites Java sobre las clases de papel | el **módulo `jdk.compiler`** del JRE (sí está: pasa aquí, 60 s medidos) | `bash scripts/prueba-mente.sh` |
| `prueba-oido.sh` | `PruebaOido.kt` con Vosk real | nada que bajar: `~/.cache/cort-kotlin` (96 MB) y `~/.cache/cort-motor` (77 MB, con `vosk-0.3.45.jar`, `jna-5.13.0.jar` y el modelo en español) ya están; **lo que le falta es RAM** (`KOTLIN_MEM=320m`) | `bash scripts/prueba-oido.sh` |
| `prueba-llave.sh` | resolución de la llave de firma | nada (tarda **12 s**, medidos; toma la rama de `keytool` porque el JRE lo trae) | `bash scripts/prueba-llave.sh` |
| `taller-f15/f16/f17/f18/f23.sh` y `taller-mandos/modelos/ollama.sh` | **mutaciones**: el verde debe caerse nombrando la comprobación | la suite que tallerea | `bash scripts/taller-<x>.sh` (de uno en uno: comparten `/tmp/cort-mente`) |
| `ui/sonda-carita.html` (1.158 líneas) | la cara con puente falso | **navegador y servidor** | `bash scripts/run.sh` y abrir `/sonda-carita.html` |
| `ui/sonda-camara.html` · `ui/sonda-colores.html` · `scripts/sonda-voz.html` | orden del permiso de cámara / colores / `getVoices()` | navegador (la cámara exige HTTPS o localhost) | abrir el archivo |

**Un script que las corra todas en fila: no existe** (buscado en `scripts/`). Lo más cerca
que hay es el job `apk` del workflow (`build.yml:152-399`), que no se puede ejecutar local
sin el SDK de Android. Eso es deuda (punto 9, fila 4) y lo resuelve la línea base del paso
0.3.

## 9. Deuda técnica y riesgos, medida

1. **Dos CORT en el mismo repo, sin ancestro común.** `git merge-base v0.2-demo origin/main`
   no devuelve nada: `v0.2-demo` (la nuestra, APK Java 2.11.0, etiquetas `v0.2.x-demo`) tiene
   **100 commits**; `origin/main` tiene **143**, paró el 2026-10-17, y es otra arquitectura
   (`AGENTS.md`, `CLAUDE.md`, `services/`, `packaging/`, `Makefile`, etiquetas `v0.15.1` …
   `v0.17.0`, «la fábrica — 811 pruebas en servidor») **sin `apps/apk/src/com/cort/ia/`**.
   `main` es la **rama por defecto de GitHub**, así que la README que ve quien entra al repo
   no es la que mantenemos. También existen `cort-local-verified` y `cort-nucleo`. Es
   `[DECISIÓN]` de la dueña, no un bug.
2. **`CortNative.java` es un dios de 2.120 líneas** (STT, TTS, permisos, música, alarma, EQ,
   teléfono y JSON a mano con `textoDe/mal/conTipo/comilla` en `:2059-2110`) mientras existen
   `Musica`, `Reproductor` y `Alarma` como clases propias. `MainActivity.java` (1.044) mezcla
   Activity + `WebChromeClient` + MediaSession + botón nativo.
3. **6 de 83 métodos del puente están muertos** para la cara (punto 4). El contrato publicado
   los sigue contando como vivos.
4. **No hay runner local de todo** (punto 8): cada tanda se arma a mano y es fácil olvidar
   una suite. El pipeline las encadena, pero sólo en la nube y sólo con etiqueta.
5. **Dependencias del backend sin lock.** `backend/requirements.txt` son 5 líneas con `>=`
   (fastapi, uvicorn[standard], psutil, requests, python-dotenv); no hay `requirements.lock`
   ni `uv.lock`. Un día `fastapi` cambia y el instalador se arma distinto sin que nadie lo
   haya tocado. (`desktop/package-lock.json` sí existe.)
6. **Lo que no se puede reproducir en este portátil es el APK, no las pruebas.** Medido el
   2026-10-25: `compilar.sh:162` muere sin `ANDROID_HOME` porque hacen falta `aapt2`, `d8`,
   `zipalign` y `apksigner` del SDK de Android, y el SDK no está instalado. Todo lo demás sí
   funciona aquí: el JRE (`openjdk-21-jre-headless`) trae **`keytool`** y el módulo
   **`jdk.compiler`**, así que `prueba-mente.sh` compila y pasa en 60 s; `kotlinc` y el modelo
   de Vosk ya están en `~/.cache`; y la cara se puede correr con `scripts/run.sh`. Quedan
   cuatro comentarios del repo que decían lo contrario y están corregidos en este mismo
   commit (`prueba-llave.sh:6-9`, `prueba-costura.py:3-6` y `:481`, `prueba-mente.sh:54`). La
   cara sí se puede correr local; el APK no, y **no es por falta de Java**.
7. **Etiquetas del manifiesto mal nombradas en el README** (punto 5): «4 servicios `BIND_*`»
   son 4 cadenas que protegen 5 servicios; «28 permisos» son 24 + 4. El número que publica el
   auditor es correcto; la palabra no.
8. **8 scripts sin prueba propia** (no hay ningún `prueba-*` que los ejercite):
   `actualiza.sh`, `instala-apk.sh`, `instalar-linux.sh`, `telefono.sh`, `marca.py`,
   `mede-catalogo.py`, `empaqueta-ico.py`, `icono-del-telefonito.sh`. Son los que tocan la
   instalación de la dueña.
9. **Basura generada conviviendo con el código**: `apps/apk/__pycache__/` (la deja
   `perfil.py` al importarse ahí). Está ignorada por git, pero ensucia el árbol.
10. **Cadenas de interfaz dentro de Java**: 11 literales `"dice"` con fraseo de cara en el
    puente, `botonMenu.setText("CORT · PC")` en `MainActivity.java:191` (el botón que ya no
    se muestra), un Toast en `MainActivity.java:921` y un label en el manifiesto (`:359`).
    Eso es lo que T15/T16 quieren pulir, y hoy vive fuera de la cara.
11. **Peso versionado que no hace falta**: el `CORT-IA-1.1.0.apk` de referencia
    (1.815.389 B) y `three.module.js` (1.272.972 B) viajan en el repo; no molestan al APK,
    pero sí a cualquier clon.

## 10. Dónde pega cada ficha (lo medido, para no descubrirlo al editar)

Esta sección es la única razón de ser del paso 0.2: que cuando llegue la ficha T ya sepamos
dónde toca y qué se va a encontrar. Nada de lo de abajo está cambiado todavía.

| ficha | dónde vive hoy (medido) | qué se va a encontrar quien la ejecute |
| --- | --- | --- |
| **T1 · burbuja** (decidido: 58 dp **sin** icono) | `apps/apk/src/com/cort/ia/Flotante.java` (629 líneas): `DIAMETRO_DP = 44` (`:89`), `MARGEN_DP = 10` (`:91`), `ALFA_REPOSO = .28f` (`:93`, aplicado en `:332` y `:351`), `ESPERA_OPACIDAD = 1800` (`:95`, usado en `postDelayed(seApaga, …)` `:401` y `:404`), degradado del cristal `new float[]{0f, .58f, 1f}` (`:456`) y **el icono dibujado dentro** (`cajaIcono` `:468`, `ic_launcher_round` por `getIdentifier` `:485-487`) | Hay que tocar **dos cosas y son contrarias**: subir `:89` de 44 a 58 y **quitar** lo que la 2.11.0 añadió (`:468-487`). Y el latido **está apagado a propósito**, lo dice el comentario `:37-38`: «un latido por fotograma en segundo plano sería batería y RAM en un teléfono de dos núcleos; el latido vivo es de la cara». Si T1 pide latido en la burbuja, eso choca con la decisión ya tomada y hay que preguntarle a ella antes de escribirlo. |
| **T2 · arranque y versión honesta** | `ui/index.html:42` deja escrito `v0.2` y `ui/js/hud.js:93-96` lo sustituye por `'v' + s.version` **sólo si el backend contesta**; en Android `API = ''` (`hud.js:26-29`) y `discoverApi()` corre en paralelo (`:34-56`, `:75`) | Con el backend apagado la cara muestra `v0.2` aunque el APK sea 2.11.0. Es justo lo que prohíbe A3 (honestidad de estado), así que T2 no es un pulido estético: es cambiar el texto de fallback por algo que admita «sin confirmar». |
| **T3 · íconos SVG de línea** | `ui/js/icons.js` (38 líneas) tiene **24 íconos** ya dibujados con un solo grosor (`:1` lo explica, `window.ic` en `:30-31`, `fill()` en `:32-34`). Lo consumen **sólo** `ui/index.html` (11 `data-ic=`) y `ui/js/hud.js` (21 llamadas a `ic('`): con el corte 3 son **2 archivos de los 26** de la cara. Medido con `python3` sobre los bloques U+1F000–1FAFF, U+2190–2BFF y U+FE0F, quedan **86 glifos distintos repartidos en 23 archivos**; los que se ven son los de las fichas (`marco.js`: 13 distintos), la Charla (`charla.js`: 25) y `pantallas.js` (40) — en `hud.js` (36) y `automatiza.js` hay cientos de ocurrencias que son arte de comentario (`─`, `═`) y no cara, por eso la cifra que importa es *distintos*, no ocurrencias | T3 está **a medias, no sin empezar**, y el mapa de a dónde ir cambió con el corte 3: los glifos de las pantallas ya no están en `pantallas.js` sino en `marco.js`. Y hay una trampa: `fill()` sólo corre al cargar el documento (`icons.js:36-37`), así que sustituir un glifo dentro de HTML generado después no lo pinta; hay que llamar `ic()` en el string o rellenar tras el `innerHTML`. |
| **T4/T5/T6 · menú y pantallas** | Las fichas **ya no viven en `pantallas.js`**: son la tabla `PANTALLAS` de `ui/js/marco.js` (275 líneas), `:64-92`, con `✦` en `:75` (`charla`), `⌘` en `:87` (`centro`) y `⌬` en `:91` (`arnes`). El cambio de pantalla es `ir()` (`:221-244`) sobre cuatro registros (`alEntrar` `:213`, `alCerrar` `:215`, `alRepintar` `:217`, `alPintar` `:219`). Las hojas siguen en `pantallas.js` (2.184) + `charla.js` (899) | El menú ya existe, está en su propia hoja y cada pantalla se registra a sí misma: T4/T5/T6 se pueden tocar ahí sin abrir `pantallas.js`. Conviene arreglarlo en la misma tanda que T3 para no pintar dos veces el mismo glifo, y ojo: `prueba-costura.py` 34 y `prueba-marco.mjs` vigilan tanto la tabla como el registro, así que mover una ficha sin su `alEntrar` corta la compilación. |
| **T15/T16 · textos y cuentas** | `diccionario.js:1593` es `TOTALES` (91 intenciones / 736 frases) y es **la única cifra real**; pero el número está escrito a mano, otra vez, en `diccionario.js:1595` (`AYUDA`), `arnes.js:14`, `centro.js:4`, `marco.js:84` (el comentario de la ficha del Centro; estaba en `pantallas.js:83` y se fue con el corte 3) y `pantallas.js:318` («las 91 herramientas») | Cinco sitios repiten lo que ya se puede leer de `TOTALES`. Si el diccionario crece, esos cinco se quedan mentirosos. T15/T16 deben leer de `TOTALES`, no reescribirlo. |
| **Fase 2 · modelos locales** | El backend **ya tiene las siete rutas**: `/api/models` (`backend/app/main.py:395`), `/api/models/progreso` (`:402`), `pull` (`:408`), `cancel` (`:415`), `rm` (`:421`), `use` (`:426`), `ollama` (`:432`) | 2.2 no es «crear la descarga», es revisar lo que hay contra la referencia (`docs/referencia-openjarvis.md`): lo que falta es barra de progreso real, pausa/reanudar y control de espacio en disco, que en OpenJarvis **tampoco existen**. |
| **Fase 4 · música / Lark** | `Reproductor.java` (897) ya es servicio en primer plano con MediaPlayer+MediaSession, `Musica.java` (559) indexa el teléfono, `Ecualizador.java` (151), `Paleta.java` (356) | El reproductor propio ya existe; lo que ella pide («que suene en VLC/Lark») es otro camino: intent explícito a la app del sistema, y ahí entran las 7 intents y 12 paquetes de `<queries>` (`AndroidManifest.xml:227-270`). |
| **Fase 5 · acciones y permisos** | **24 `<uses-permission>`** en el manifiesto, repartidos en tres regiones recortables (`:177`/`:197`, `:308`/`:329`, `:349`/`:412`) que corta `apps/apk/perfil.py:90-93` | Añadir un permiso es cambiar el manifiesto y con él los tres envases y el contrato del auditor. A3 lo bloquea sin autorización explícita, y las regiones obligan a decidir **en qué envase** vive el permiso nuevo, no sólo si va. |

## 11. Puerta de la Fase 0 — cerrada el 2026-10-25

El 0.3 se corrió y quedó escrito: **`docs/linea-base.md`**. Dice la máquina exacta donde se
midió (2 núcleos, 1.851 MB, Qoder abierto, **sin Ollama ni navegador**: las cifras de tiempo
son techo, no suelo), las **12 suites que sí corren aquí** todas verdes con su `rc` y su
tiempo, los **8 talleres de mutación (7 verdes, 1 rojo)**, lo que **no** se pudo medir en
este portátil y los agujeros de prueba encontrados midiendo. Con ese tercer documento la
puerta se cerró y la Fase 1 se abrió.

**Lo que sigue vigente de aquel paso, porque es deuda y no estado:** (a) **no existe un runner
local** de las 28 suites — la línea base armó la tanda a mano en su sección 7 y así se sigue
corriendo; (b) el rojo del taller F15 era por dos mutaciones muertas, y (c) la cara servida
por el navegador **no** está verificada aquí: lo que se comprueba en local es el código
estático y los módulos ejecutados con gemelos de papel.

**Y lo que cambió el mapa desde el 25:** la limpieza `b4e6e09` sacó del versionado el APK base
y la segunda `_suena` de `voz.py`; después llegaron J2.1, J4 y la refactorización por tamaño,
cuyo **corte 3** (`marco.js` + `charla.js`) es lo que mueve las líneas citadas de los
apartados 2 y 10. Los apartados 1, 2, 8 y 10 están vueltos a medir el 2026-10-27; de las
secciones 3 a 9, las líneas citadas siguen siendo las del 25 en los archivos que no se tocaron
(`CortNative.java`, el manifiesto, `Reproductor.java`) y están desactualizadas en los que sí:
`backend/app/` pasó de 15 módulos y 4.422 líneas a 17 versionados y 5.925 (19 y 6.823 en el
disco de hoy con `pool.py` y `reproductor.py` sin commitear).

**Lo que este paso no hizo, dicho en vez de fingido:** no se ejecutó ninguna suite salvo la
costura (para confirmar que el repo estaba intacto antes de describirlo), no se compiló nada, no
se cambió una línea de código, y no se tocó `main` ni las otras ramas.
