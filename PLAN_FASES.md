# PLAN DE FASES — CORT

Del 2026-11-02. Cada fase tiene **5 tareas exactas** y una **salida medible**: si la
salida no se puede medir, la fase no está cerrada. Los números vienen del censo de
`INFORME_FUNCIONES.md` (mismo día): 155 botones, 34 órdenes sondeadas de las que
contestan 6, 138 comandos anunciados de los que responden bien 4, 10 paneles que se
abren vacíos.

La base de la demo de TechEnClair **se conserva como andamio** (menú, botones,
ventanas, HUD) y se rediseña por encima. Se acredita como referencia visual en el
README y en el repo. No se piden permisos y no se publican los `.orig` ni el espejo
descargado: ahí está la línea que protege tu autoría sin frenar nada.

---

## F1 — Que nada mienta (cimientos del puente)

1. Cola de escritura por conexión con candado: CORT habla y sigue leyendo órdenes a la
   vez. Hoy hay ~9 s de sordera medida en una respuesta larga.
2. `enviar_seguro()`: envíos que toleran pestaña cerrada y limpieza de conexiones
   muertas. Elimina la traza `Cannot write to closing transport` al recargar.
3. `update_settings` y `get_settings` atendidos: el botón GUARDAR de Ajustes guarda de
   verdad y Ajustes recupera ciudad, idioma y modelo al abrir.
4. Clima y temperatura reales en pantalla: la página pide clima al cargar y cada 10 min;
   el panel térmico lee `/sys/class/thermal` (medido: thermal_zone2 = 49,0 °C).
5. Sello de estado en los 10 paneles zombis: si no hay datos dicen «sin datos: falta X»
   con botón de reintento, en vez de un indicador de carga infinito.

**Salida:** al sondear las 34 órdenes, ninguna queda muda (contesta dato o contesta
motivo); 0 trazas en `/tmp/cort_bridge.log` tras recargar tres veces a media frase.

**CERRADA el 2026-11-02 con la vara medida:** `cort_probe.py menu` → 34 contestan · 0 en
silencio; 0 trazas tras tres recargas a mitad de subtítulo y de escáner (puente con 5 min
de vida, RSS estable en 43 MB, 8 conexiones y 7 cierres: nada se queda colgado). La prueba
de sordera: `user_input` + `av_scan_start` en el mismo canal y a 0,2 s de distancia → los
dos contestan (15 subtítulos y 5 avances del escáner en la misma escucha).
El sondeo de clima no lo hace la página sino el puente (`latido_clima`, cada 10 min, una
sola petición a open-meteo compartida por todas las pestañas) y llega marcado `empujado`:
eso pinta los números pero ya no abre el panel por la cara.

---

## F2 — El orbe y el arranque, ya de CORT

1. Capa `cort/cort-orbe.js` al lado del Three.js vendorizado: 7 estados con color
   propio (reposo, escucha, pensando, hablando, ejecutando, alerta, descarga).
2. Ráfaga tipo **vórtice** al ejecutar una orden: dispersión de partículas y
   reensamblado, disparada por un mensaje nuevo `estado: ejecutando` del puente.
3. Anillo de progreso mientras baja un modelo o corre la auditoría antivirus
   (el puente ya emite `ollama_pull_progress` y `av_progress` reales).
4. Pantalla de arranque con el nombre y el logo de CORT: fuera «JARVIS» y fuera los
   rótulos en francés del `boot-overlay`.
5. Medición en el navegador integrado: capturas de los 7 estados y FPS con 2 núcleos,
   para fijar el mínimo de partículas que no congela el equipo.

**Salida:** 7 estados visibles, dispersión en menos de 400 ms, FPS ≥ 24 medido, y el
orbe se ve distinto del original sin tocar el JS minificado.

**CERRADA el 2026-11-02, con una vara aplazada y otra cumplida.** Los 7 estados están
pintados y fotografiados en `montaje-estados-orbe.png`; el vórtice (esfera → toroide →
dispersión) y la ráfaga en cometa salen en `DISENO_ORBE.md` §5 con sus fotogramas; el
anillo de progreso se llena con el % real de `ollama_pull_progress`; y el saludo de
arranque se dispara con la apertura del WebSocket, no con un reloj. Duraciones en pared:
vórtice 856-982 ms y ráfaga 372-449 ms, siempre `dur` + un fotograma. **El FPS ≥ 24 no
se pudo verificar en esta ventana y se dice como lo que es:** achicar y ocultar los lienzos
WebGL de la demo no cambió el número (10 → 11 → 9 FPS), mientras `top` marcaba load 5,9 en
2 núcleos y 1,36 GB en swap con el entorno del agente comiéndose el CPU; la medida limpia
se toma de madrugada junto a la tarea 5. Lo que sí se aísla es el costo de la capa propia:
**2,3 ms por fotograma con 260 partículas**, y el recorte automático ya no se dispara por
culpa ajena (0 recortes tras el arranque, antes 4-6).

---

## F3 — Cerebro encendido y voz  ·  **voz CERRADA el 2026-11-02; cerebro parcial**

Cerrado con número: espeak-ng (factor 0,14 ms de CPU por segundo de audio) y Piper
(1,90 / 2,55 + 14 s de carga del modelo, cargado UNA vez dentro del puente). El camino
de salida se probó con un sink nulo temporal y midió RMS 2521 / pico 32754: el puente
entrega audio de verdad; lo que no hay en la Canaima es altavoz físico (`auto_null`).
Vosk transcribe el WAV generado por CORT (7,0 s de proceso para 3,9 s de audio), así que
oír->entender funciona sin micrófono. Órdenes vivas: `voz_estado/voz_on/voz_off/voz_motor/
av_speak/mic_on/mic_off/mic_estado/check_local_tts_status/check_kokoro_status`.

Pendiente de la fase: puntos 1 (turno de noche con `smollm2:135m`), 2 (historial
persistente) y 3 (reglas corregidas); el micrófono real sigue sin hardware — entra por
el teléfono en F7.

1. Turno de noche real: cargar `smollm2:135m` con `CORT_RAM_MIN=900 MODELO=smollm2:135m
./cort_cerebro.sh` y verificar con `cort_probe.py cerebro` (hoy: 210–320 MB libres, el
   modelo pide ~511 MB).
2. Historial persistente y resumen de sesión en `cort_state.json` (ahora el historial
   vive en memoria y se pierde al reiniciar).
3. Reglas locales corregidas: coincidencia por palabra completa y orden de prioridad,
   para que «Inspírame» no suelte estadísticas de RAM.
4. Motor de voz de salida elegido e instalado (espeak-ng, Piper local o Web Audio) con
   lectura larga sin cortes ni desbordes de memoria.
5. Micrófono en zona de pruebas, con el orbe marcando el estado de escucha.

**Salida:** conversación de 5 turnos con un modelo real nombrado en pantalla, y CORT
diciendo en voz alta una respuesta de más de 300 caracteres sin congelar el equipo.

---

## F4 — Vida diaria (17 comandos del censo)  ·  **CERRADA el 2026-11-03**

`cort-bridge/cort_vida.py`, sólo con la biblioteca estándar. Todo se escribe en
`~/.local/share/cort/vida/*.json` **antes** de responder, y se reléye: prometer
«guardado» sin volver a abrir el archivo es la forma fina de mentir.

Medido con un puente en arena (`CORT_DATOS=/tmp`, para no llenar la lista real de
pruebas) y con la interfaz en el navegador integrado:

| prueba | resultado |
|---|---|
| «cómprame leche, tres huevos y pan» | 3 artículos (se divide por `,`, ` y `, `+`) |
| «cómprame leche» otra vez | «0 nuevo(s), 1 ya estaban» — no duplica |
| «quítame de la lista los huevos» | saca `tres huevos` buscando la palabra suelta |
| «ya compre el pan» | lo tacha |
| «anota que el sónar muestra tres capas» | nota «El sónar muestra tres capas» (27 caracteres) |
| «mis notas» / panel de notas | `MODIFICADO: 03/11/2026 00:09 · TAMAÑO: 29 B` con datos del puente |
| «recuerdame llamar a la tía en media hora» | pendiente a 1 800 s, **con sus tildes** |
| «temporizador de 5 segundos» | puesto a los 0,00 s, `reminder_trigger` a los **5,52 s** (vela de 1 s) |
| frase → `jarvis_text` | **0,34 s** de ida y vuelta con el puente y el navegador abiertos |
| «léeme la selección» | leídos 44 caracteres del portapapeles primario (xclip) y dichos en voz alta |
| apagar y levantar el puente | la lista, las notas y los pendientes **siguen ahí** |

Lo que **no** se hizo de la lista y por qué: las escenas «modo estudio» y «modo
madrugada» (punto 5) son decoración de la fase F6 — se recortaron con su acuerdo;
el aviso hablado del temporizador depende del motor de voz de F3 y en la Canaima no
hay altavoz físico, así que se ve en pantalla y se oye sólo si hay HDMI o dongle USB.

Dos defectos que esta fase destapó en el puente, corregidos aquí mismo:

1. La regla de estado del equipo buscaba `ram` como subcadena, y «cóm**pram**e leche»
   contestaba con el uso de memoria. Las siglas (`cpu`, `ram`, `disco`) se buscan ahora
   con frontera de palabra.
2. Todo lo que se guardaba se guardaba sin tildes, porque las reglas trabajan sobre la
   frase normalizada. Se añade `_rebanada()`: se busca en la versión sin acentos y se
   recorta del texto original, así que la lista y las notas conservan lo que escribió.

El panel de notas de la plantilla se llama Obsidian; Obsidian **no está instalado**
en este equipo. Se alimenta con las notas de CORT y el propio mensaje lo dice
(`"no es Obsidian"`), que es lo que se prometió en F1.

**Salida:** los 17 comandos de esta familia responden con datos que **sobreviven a un
reinicio** del puente.

---

## F5 — Acciones sobre el equipo (35 comandos del censo)  ·  **CERRADA el 2026-11-02**

`cort-bridge/cort_acciones.py` con lista blanca de verbos Linux y `shell=False` en todas
las llamadas. Doce acciones medidas en la Canaima: abrir aplicación (165 entradas
.desktop leídas; «abre vlc» lanzó VLC y «cierra la ventana vlc» la cerró 2 s después de
mapear), ventanas con wmctrl, volumen y silencio con pactl, brillo (sin brilloctl: se
avisa que el gamma de X11 no es luz real), teclas multimedia por xdotool, notificaciones,
captura con scrot, portapapeles y selección primaria con xclip, fondo con xfconf-query,
`apt list --upgradable` en lugar de winget y dpkg en lugar del registro de Windows.

Registro auditable en `~/.local/share/cort/registro-acciones.jsonl` (hora, acción, frase
de origen, resultado). Apagar y reiniciar no se ejecutan sin confirmación explícita:
probado — «apaga el equipo» respondió pidiendo confirmación y no tocó nada.

Queda fuera a propósito: desinstalar programas y lanzar juegos (F5+ con confirmación en
pantalla) y el panel gráfico de acciones, que se hace sobre el testigo `pc` de la pantalla.

1. Capa `acciones.py` con lista blanca cerrada de verbos Linux: abrir carpeta, abrir
   app, volumen, brillo, captura de pantalla, apagar el salvapantallas.
2. Zona de pruebas con `CORT_HOME` separado del resto del disco y registro de cada
   comando ejecutado con su hora.
3. Confirmación en pantalla antes de cualquier acción que escriba o cierre algo.
4. Prohibiciones duras escritas en el código: apagar, formatear, matar procesos, borrar
   fuera de su home. El antivirus ya funciona así (informa, no borra).
5. Prueba real medida en la Canaima: abrir el gestor de archivos, bajar el volumen,
   tomar una captura.

**Salida:** 10 acciones funcionando con su registro auditable y 0 ejecuciones fuera de
la lista blanca.

---

## F6 — Mapa propio y CORT OS de escenas  ·  **APARCADA (recorte acordado)**

Fue lo primero que se tiró del plan cuando quedó claro que no daba tiempo a todo:
no aporta nada que no pudiera esperar. Sin mapa no hay nada que fingir, así que el
panel queda como está y no se disfraza.


1. Quitar el `<iframe>` de ArcGIS y montar el mapa con el **Leaflet ya vendorizado**
   (`cort/vendor/leaflet/`): funciona sin internet si se añaden teselas locales.
2. Vuelo a ciudad, marcador y rutas desde el puente, usando la lat/lon que ya guarda
   `cort_state.json` (hoy el globo arranca en 0,0 frente a África).
3. Capa de clima sobre el mapa con los datos de open-meteo que el puente ya calcula.
4. **CORT OS** como lanzador propio de escenas y accesos directos dentro de la
   interfaz, no como sistema operativo: se queda el panel, se va la instalación.
5. Inventario final de dependencias externas (hoy quedan teselas de Google, Windy con
   clave y `hls.js` bajo demanda) y decisión de cada una.

**Salida:** globo y mapa funcionando sin conexión, centrados en tu posición real, con
vuelos pedidos por voz.

---

## F7 — Teléfono: app de asistente y puente con la Canaima  ·  **PWA CERRADA el 2026-11-03 · APK ESCRITO Y COMPILADO EN ACTIONS el 2026-11-04**

Hecho y medido en el navegador integrado: `manifest.webmanifest` parsea (3 iconos,
`start_url` `/index.html`, `display` standalone), el service worker queda `activated`
en `http://127.0.0.1:8766/` y la caché `cort-v1` guarda las **9 piezas del programa**
— nunca `/audio/` ni medidas, para que un número viejo no se disfrace de actual. El
puente arranca con `CORT_BIND` (por defecto `127.0.0.1`) y `CORT_TLS=cert,clave`: sin
HTTPS el teléfono no instala la app ni presta el micrófono, y eso se imprime al arrancar.
Medida también la traducción de las etiquetas del panel de notas (`MODIFICADO:` /
`TAMAÑO:`), que el diccionario no alcanzaba porque van dentro del nodo con la fecha.

**El 2026-11-04 deja de ser pendiente y pasa a estar construido**, con estas cifras:

- Por qué no se compila en casa: medido en esta laptop, hay OpenJDK 21 **sólo runtime**
  (`javac` no existe), y no hay Gradle, ni SDK de Android, ni `adb`. Lo que se puede
  garantizar es que el APK salga del código de este repo con un workflow leído
  (`.github/workflows/apk.yml`) y que su peso y SHA-256 se publiquen medidos.
- El proyecto `apps/android/` no declara **ninguna** dependencia externa: WebView +
  `AudioRecord` + `org.json`, todo del SDK, y **no usa Gradle**: `apps/android/compilar.sh`
  llama a `aapt2`, `javac --release 11`, `d8`, `zipalign` y `apksigner` del runner
  (`minSdk 26`, `targetSdk 34`), que es el método ya probado por la otra línea del repo.
  Sin el secreto `CORT_APK_KEYSTORE_B64` la firma es desechable y hay que desinstalar el
  anterior: se dice en la release, no escondido en el log.
- El oído del teléfono entra por `POST /mic` en el puente (el navegador no da
  `getUserMedia` por `http`). Medido con `scripts/prueba_mic_telefono.py`: **7/7**,
  22,4 s la primera subida (Vosk cargando 58 MB) y **2,82 s** con el modelo en RAM para
  ~2 s de habla; el WAV se borra después de transcribir y lo que no es WAV se rechaza
  con `origen: no disponible`.
- La instalación Linux que el teléfono necesita (`--red`, `CORT_BIND=0.0.0.0`) ahora es un
  script: `scripts/instala_cort.sh`, probado en esta máquina de principio a fin.

Sigue pendiente, y se dice con nombre: **emparejamiento y clave** (S3) — con `--red`
cualquiera de tu Wi‑Fi llega al puente; la firma de autora con `CORT_APK_KEYSTORE_B64`; y
la prueba física en el A16, que sólo puedes hacer tú. No se instala ningún `.apk` de un
acortador.

1. Elegir linaje y montar su proyecto fuente: `2.11.0-nucleo` (47,5 MB, con Vosk
   español sin internet y su propia `assets/ui`) o `bolsillo` (1 MB, fuente en
   `Sandra2244/CORT-nuevo` con `apps/bolsillo/compilar.sh`).
2. Añadir el `VoiceInteractionService` con su `xml/pre-services` para que el A16 te la
   liste en **Ajustes › Aplicación de asistente** (ahora sólo aparece Google).
3. Lectura en voz alta de lo que hay en pantalla y dictado: lo que uses para estudiar.
4. Conexión por red local al puente de la Canaima con token pareado y QR **generado en
   local** (fuera `api.qrserver.com`).
5. Compilación por GitHub Actions con el método que ya funciona: `aapt2` + `d8` +
   `zipalign 4` + `apksigner` v2/v3 con `CORT_APK_KEYSTORE_B64`, y prueba instalada en
   el teléfono sin avisos de Play Protect.

**Salida:** APK instalada, seleccionada como asistente del teléfono y respondiendo con
el puente de la Canaima por Wi-Fi.

---

## F8 — Presentación y publicación  ·  **README y LICENSE cerradas; empujar, no**

El README está reescrito en español con arquitectura, instructivo de instalación paso a
paso, variables de entorno y la tabla de lo que funciona **con su número medido**.
`LICENSE` es MIT (c) 2026 Sandra Sofía Lopez y la nota de referencia visual a TechEnClair
queda en el propio README y en `PROCEDENCIA.md`.

Lo que falta es suyo, no mío: **empujar a `Sandra2244/CORT`, la etiqueta y el ZIP** no se
hacen sin su autorización explícita. Sigue sin publicarse `.orig`, el espejo descargado,
los estados personales ni las capturas de terceros.

1. Rótulos definitivos: cero «JARVIS» a la vista y cero francés (hoy quedan 3 cadenas
   visibles, medido con el propio detector de la página).
2. README en español con arquitectura y su instructivo de instalación paso a paso.
3. `LICENSE` MIT a tu nombre y nota clara: *interfaz inspirada en el proyecto JARVIS
   web de TechEnClair (referencia visual, con capturas; algunas cosas se replicaron
   como base); puente Python, rediseño, traducción y funciones, propios*.
4. Limpieza del repo antes de publicar: sin `.orig`, sin espejo descargado, sin estado
   personal, con `PROCEDENCIA.md` y `LEEME.md` revisados.
5. Empujar a `Sandra2244/CORT`, etiqueta de versión y release con el APK.

**Salida:** repo público que se defiende solo: se entiende qué es tuyo, qué es
referencia y cómo se instala.

---

## Lo que no entra en el plan (y por qué)

* Servicios con clave de pago y tarjeta (Spotify, YouTube API, Gmail, ElevenLabs): no
  tienes Visa/Mastercard y cada uno abre una llave que hay que mantener.
* Instalar Jarvis OS como sistema operativo: pide el disco entero y borraría MX Linux.
* Visión por cámara y gestos al mando del ratón: media resolución de la Canaima y
  MediaPipe; se decide después de tener F1 a F4 cerrados.
* Compilar el APK en la Canaima: no hay SDK y el Actions ya lo hace mejor.
