# INFORME DE FUNCIONES REALES DE CORT

**Fecha de la medición:** lunes 2 de noviembre de 2026
**Equipo medido:** Classmate «Canaima» — MX Linux, 2 núcleos, 1851 MB de RAM total
**RAM libre durante la medición:** entre 210 y 321 MB (no es un dato fijo: la medí varias veces)
**Cómo se midió:** tres sondas, sin inventar nada

1. `cort-bridge/cort_probe.py menu` → manda cada orden de LEER que la interfaz sabe
   enviar y escucha si alguien contesta.
2. Navegador integrado con la página abierta (`http://127.0.0.1:8766`) → se pulsaron
   los botones uno a uno y se midió qué panel aparece, de alto y con qué texto.
3. `cort-bridge/cort_repertorio.py` → cruza los 138 comandos que el propio menú
   promete contra las reglas del puente. Su salida es literalmente la tabla de abajo.

Todo lo que aquí dice **real** tiene una medición detrás. Lo que dice **no hace nada**
significa que la interfaz mandó el mensaje y el puente calló, o que el botón no
dispara ninguna carga.

---

## 1. Los cinco números del proyecto hoy

| Qué | Cantidad | Fuente |
|---|---|---|
| Botones con `id` en la interfaz | **155** | volcado de `index.html` |
| Entradas del menú lateral | **6** (globo, antivirus, protección en tiempo real, VPN, juegos, fondos) | medido en pantalla |
| Grupos y botones dentro de Ajustes | **21 grupos · 25 botones** | medido en pantalla |
| Órdenes de lectura sondeadas al puente | **34 → contestan 6, callan 28** | `cort_probe.py menu` |
| Comandos de voz que el menú anuncia | **138 → hoy responden bien 4** | `cort_repertorio.py` |

Esa última fila es la más importante y la más incómoda: **la interfaz presume de 138
cosas y el equipo que hay detrás hoy hace bien 4.** El informe completo está abajo;
la encuesta sale de aquí.

---

## 1bis. Addendum: qué cambió al cerrar la fase F1 (mismo día, después de este censo)

Las cifras de arriba son la foto del censo. Con la fase F1 cerrada (commit `21162c5`):

| Qué | Antes | Después (medido) |
|---|---|---|
| Órdenes de lectura que contestan | 6 de 34 | **34 de 34** (28 contestan con `puente_aviso`: motivo + lo que hace falta) |
| Trazas al recargar a media frase | 1 por recarga | **0** tras tres recargas |
| Órdenes simultáneas en un canal | la segunda se perdía | **las dos contestan** (cola de salida con un único escritor) |
| Temperatura del panel térmico | 21,8 °C inventados por el simulador | **48–49 °C del sensor TCPU**, con el nombre del sensor y la advertencia de que es el chip |
| Clima | 22 °C inventados si el puente estaba caído | dato real de open-meteo, renovado cada 10 min por el puente |
| Paneles zombis | «Cargando…» eterno | caja ámbar «aquí no hay nada medido» + los «Cargando…» convertidos en «— sin datos —» |

Sigue sin funcionar lo que no depende de la interfaz: no hay cliente VPN, ni Home
Assistant en la red, ni motor de voz de salida, ni micrófono activado. Eso es F3, F5 y F7.

---

## 2. Lo que SÍ funciona hoy (real, medido en esta sesión)

| Función | Qué hace realmente | Prueba de esta sesión |
|---|---|---|
| **HUD de CPU / RAM** (esquinas) | Lee `/proc/stat` y `/proc/meminfo`, empuja cada 4 s el latido `system_stats` | pantalla mostraba `CPU 96%` / `RAM 81%` con números vivos |
| **Reloj y fecha (arriba a la derecha, rediseñado)** | Reloj del equipo, formato cyberpunk, en español | visible en las mediciones |
| **Antivirus / auditoría de seguridad** | 4 pasos reales: arranque, procesos, archivos, permisos. **No borra ni mata nada** | 12 mensajes `av_*` en 9.3 s (primera vez) y 11 en 4.0 s (segunda). 4–5 hallazgos, con `origen=real` |
| **Clima** | Geocodifica la ciudad (open-meteo) o usa la IP; guarda el último punto y avisa si la ciudad no existe | «En Carora: 32.0 grados, sensación 33.9, llovizna ligera, viento 16.0 km/h» a las 15:16 |
| **Cerebro / Ollama** | Estado real: servidor vivo o apagado, modelos **leídos del disco** (no de una lista falsa), RAM libre, catálogo | `ollama_status_reply` con 6 modelos en disco y «294 MB libres de 1851» |
| **Elegir modelo en Ajustes → CEREBRO //** | Escribe en `cort-bridge/cort_state.json` y avisa con el peso medido si el modelo cabe o no | fila visible: «Ollama apagado · 294 MB libres», botones en rojo punteado para lo que no cabe |
| **Descargar un modelo** | Puerta de disco (500 MB de margen) y puerta de RAM (350 MB para levantar servidor). Si ya está en disco, no lo vuelve a bajar y lo dice | verificado con sonda: «smollm2:135m ya está descargado (258 MB) — no hace falta bajarlo otra vez» |
| **Idioma español por defecto + cambio a francés/inglés** | Traducción en el DOM con diccionario + reglas; observador de cambios | al abrir todos los paneles zombis quedan **3** cadenas francesas visibles (antes de este trabajo había cientos) |
| **Arranque sin depender de internet** | Se quitaron los 3 `<script>` de MediaPipe del CDN | consola limpia al cargar; el arranque no pide nada fuera |
| **Subtítulos y voz del puente** | `decir()` parte la respuesta en trozos y manda `live_subtitles` + `jarvis_text` | medido: pregunta de prueba devolvió `user_speech`, 12 `live_subtitles`, `jarvis_text` |
| **Panel del repertorio de comandos** | Se abre y muestra los 138 comandos | 521 px, 299 líneas, 138 frases citadas |

**Chat con cerebro propio:** sigue cortado por RAM. Con 210–320 MB libres ningún
modelo cabe cargado. El más ligero que ya está en tu disco (`smollm2:135m`, 258 MB
de peso real) pide ~511 MB libres. Eso es una tarea de la madrugada, no de ahora.

---

## 3. Lo que ABRE pero está vacío (el peor grupo: parece que funciona)

Estos paneles aparecen en pantalla con buen aspecto, pero no tienen nadie detrás.
El usuario no puede saber si están pensando o muertos. Es lo primero que hay que
corregir, y es barato: **un panel vacío debe decir que está vacío.**

| Panel | Lo que se ve | Por qué |
|---|---|---|
| **VPN** (`menu-vpn-btn`) | «DESCONECTADO · IP: Chargement… · ELEGIR UN PAÍS: Cargando países…» para siempre | `vpn_get_status` / `vpn_get_countries` → silencio medido |
| **MIS JUEGOS** (`menu-games-btn`) | Biblioteca vacía | `games_get_library` → silencio (es un catálogo de Windows) |
| **DESINSTALADOR** | «CARGANDO LISTA DE PROGRAMAS…» eterno | `get_installed_programs` → silencio (winget no existe en Linux) |
| **DOMÓTICA (Home Assistant)** | Panel con botones, sin dispositivos | `ha_get_states` → silencio; no hay servidor HA en tu red |
| **LISTA DE COMPRAS** | Sale con 3 artículos de muestra: «Café en grano · Filamento 3D azul · Cable USB-C trenzado» | son datos de ejemplo de la demo; `get_shopping_list`/`update_shopping_list` → silencio, así que **nada de lo que añadas persiste** |
| **MEDIA PLAYER / IPTV** | «NINGÚN MEDIO CARGADO» | no hay reproductor ni backend |
| **PANEL TÉRMICO** | «--- -- °C» cuando el equipo **sí** tiene sensores: thermal_zone2 = 49,0 °C | nadie lee `/sys/class/thermal` todavía |
| **ANÁLISIS ATMOSFÉRICO** (clima en pantalla) | «--- · -- °C · OBTENIENDO…» | el puente sabe el clima real, pero **la página nunca lo pide**: la demo esperaba que el backend lo empujara |
| **WINGET (MAJ LOGICIELS)** | interruptor que se pone activo, 0 programas | `get_winget_upgrades` → silencio |
| **IMPRESIÓN 3D** | interruptor activo, panel nunca aparece | `print3d_check_deps` / `print3d_check_hardware` → silencio |

---

## 4. Lo que NO HACE NADA (botón → silencio)

| Botón / orden | Medición |
|---|---|
| `jarvis-os-toggle-btn` (🐧 CORT OS) | `aria-pressed` sigue en `false`, panel 0 px. **No abre.** |
| `update-jarvis-btn`, `clear-cache-btn`, `btn-open-jarvis-folder`, `btn-install-piper/chatterbox/kokoro`, `btn-open-gmail-guide`, `claude-code-*`, `nemotron-*`, `mobile-pairing-btn` | mandan una orden que el puente no conoce: no pasa nada visible |
| `api-keys-save-btn`, botón «GUARDAR» de Ajustes | **bug medido:** la interfaz manda `update_settings` y el puente sólo entiende `settings-save`. Nadie lo atiende: lo que escribas en Ajustes no se guarda del lado del puente |
| `get_settings` | silencio: la interfaz nunca recupera lo que hay guardado |
| Micrófono, cámara, gestos, «¿qué estás viendo?», visión | desactivados a propósito por ti hasta decidir el alcance |

---

## 5. El GLOBO 3D: qué es de verdad

Medido en el navegador: el botón abre un lienzo a pantalla completa (521 px) cuyo
contenido es un `<iframe>` que carga

```
https://www.arcgis.com/home/webscene/viewer.html?webscene=6682f70b89c4483f88e8df839a011c1e&ui=min&viewpoint=cam:0,0,18000;0;0
```

Eso significa tres cosas, todas importantes para ti:

1. **El globo no es tuyo ni es local:** es una escena 3D alojada por Esri (ArcGIS).
   Sin internet queda en blanco.
2. **Arranca en lat 0, lon 0** (en el medio del océano, frente a África), porque nadie
   le manda tu posición real. El puente sí tiene una ruta `location_update` guardando
   lat/lon/ciudad en `cort_state.json`.
3. **Puede ser tuyo:** en `cort/vendor/leaflet/` ya tienes Leaflet en local (BSD-3).
   Un globo/mapa propio se puede hacer 100 % local y 100 % tuyo, y entonces CORT sí
   puede mandarle «vuela a Carora», «traza una ruta», «marcador aquí». Es un trabajo
   de interfaz, no de infraestructura.

---

## 6. CORT OS (lo que la demo llama «JARVIS OS»)

Qué es realmente en el proyecto original: un panel que intenta instalar y arrancar un
**sistema operativo aparte** que escucha en `127.0.0.1:8001`, con tienda de apps,
barra de herramientas (reiniciar / parar / compartida / desinstalar) y asistente de
instalación.

Qué hace tu puente hoy (medido): `check_jarvis_os_status` responde `installed: false`
con el motivo real («nada escuchando en 127.0.0.1:8001»), y cualquier `jarvis_os_*`
devuelve **«Detenido a propósito por CORT»** explicando que instalar ese sistema
pediría el disco entero de la Canaima y borraría tu MX Linux. Eso está bien: no voy a
borrar tu equipo para imitar una demo.

Pero el botón no abre el panel, así que ni siquiera se ve esa respuesta honesta.
Un **CORT OS propio** no tiene por qué ser un sistema operativo: puede ser una
capa tuya de *lanzar, ordenar y mandar* — ventanas, apps, temporizadores,
recordatorios, escenas («modo estudio»), con sus iconos y su escritorio dentro del
navegador. Es la decisión más grande de la encuesta.

---

## 7. El ORBE: motor actual y dónde meter tus dos vídeos

Medido en el código de la demo:

* El orbe se dibuja con **Three.js local** (`assets/three.module-DBf_OzsH.js`, ya
  vendorizado, con su licencia) sobre un `<canvas id="orb-canvas">`.
* Son **2000 partículas** repartidas sobre una esfera (coordenadas esféricas con
  distribución uniforme), cámara a z=115.
* Su factoría expone una API: `setState`, `setVolume`, `setAnalyser`, `setQuality`,
  `setTheme`, `triggerDemo`, `showWord`.
* Estados ya cableados: `idle`, `listening`, `thinking`, `speaking` (la interfaz los
  lee de los mensajes `state` que **nuestro puente ya manda** al hablar).
* Si WebGL falla, cae en un orbe mudo: no revienta.

Lo que piden tus dos vídeos y cómo encaja:

| Vídeo | Qué se ve | Cómo se hace sin romper nada |
|---|---|---|
| 1 | Al ejecutar una acción, las partículas se **dispersan como un vórtice** y vuelven | la demo ya tiene `particles.explode(...)` y `spawnRing(...)` para el modo holograma; una capa nuestra (`cort/cort-orbe.js`) puede lanzar la dispersión cuando el puente emita un `estado: ejecutando` y dejar que el orbe se reensamble. **Sin tocar el JS minificado** |
| 2 | El color **cambia según el estado** de ejecución | mismo sitio: un mapa estado→color (menta reposo, cian escucha, ámbar pensando, verde hablando, rojo alerta, violeta descarga). El orbe ya acepta `setTheme`, pero la instancia no está expuesta al DOM: se resuelve con nuestra capa de partículas encima, que es lo que además te lo hace **tuyo** y ayuda a que no se parezca al original |

Nota honesta: todavía no he abierto los vídeos (el equipo no tiene `ffmpeg` y la
prioridad era el informe). Cuando toquemos el orbe, saco 3–4 fotogramas de cada uno y
copio el timing, no lo invento.

---

## 8. Los 138 comandos anunciados: censo real

Salida textual de `python3 cort-bridge/cort_repertorio.py repertorio_comandos.json`:

```
comandos anunciados por la interfaz: 138
  los coge una regla local hoy: 9  (revisar el texto abajo)
  sin nadie que los atienda:    129

--- por familia (lo que hace falta para cada una) ---
  35  acciones sobre el equipo (capa Linux)
  17  temporizadores, notas, tareas, compras
  13  conversación e identidad (cerebro LLM)
  12  equipo y clima (datos reales del puente)
  12  música y vídeo (Spotify/YouTube/IPTV)
  10  correo, documentos y calendario
   9  sin clasificar
   7  domótica Home Assistant
   7  deportes y restaurantes
   5  crear con IA (imagen, música, web, prompt)
   5  globo 3D y mapas
   3  visión y control de pantalla
   3  antivirus y seguridad
```

Y esto es lo que contesta hoy cada regla, **tal cual**, con los errores a la vista:

| Comando prometido | Lo que sale hoy | Veredicto |
|---|---|---|
| «¿Qué hora es?» | «Son las 15:16.» | ✅ bien |
| «Clima en [ciudad]» | «En Carora: 32.0 grados… open-meteo» | ✅ bien |
| «Inicia un análisis de antivirus» / «ANTIVIRUS» | «Empiezo la auditoría real… No borro nada.» | ✅ bien |
| «¿Qué hora es en Tokio?» | «Son las 15:17.» (la tuya, no la de Tokio) | ❌ mal |
| «Inspírame / dame una cita» | suelta las estadísticas de CPU/RAM | ❌ mal |
| «Muéstrame vídeos de [artista]» | suelta las estadísticas de CPU/RAM | ❌ mal |
| «Ouvre Steam / Discord / VSCode» | suelta las estadísticas de CPU/RAM | ❌ mal |
| «Abre mis descargas» | habla de modelos de Ollama | ❌ mal |

Los cuatro errores son el mismo defecto: las reglas buscan **subcadenas sin límite de
palabra**. «inspi**ram**e» dispara la regla de `ram`; «**disco**rd» dispara `disco`;
«descargas» dispara `descarga`. Se arregla con coincidencia por palabra completa y
reordenando las reglas. **Total honesto: 4 comandos bien de 138.**

Con el cerebro encendido, la familia de 13 de conversación pasaría a responder el
modelo (con smollm2:135m, que es pequeño: respuestas simples). Las otras 107 familias
necesitan una capa de acciones o una API, no un modelo de lenguaje.

---

## 9. Bug y fragilidad nuevos destapados al medir (todos con evidencia)

1. **`update_settings` no lo atiende nadie.** La interfaz manda `update_settings`; el
   puente escucha `settings-save`/`settings_save`. Botón GUARDAR = no guarda. Medido:
   `update_settings` → silencio; `settings_save` → `settings_saved` en 1.5 s.
2. **`get_settings` en silencio.** Ajustes nunca recupera lo guardado (ciudad, idioma,
   modelos). Por eso tu ciudad vive sólo en `cort_state.json`.
3. **La página nunca pide el clima** → panel «OBTENIENDO…» eterno con datos que el
   puente sí tiene. Arreglo: pedirlo al cargar y refrescar cada 10 min.
4. **Mientras CORT habla, el puente está sordo.** El lazo de lectura espera a que
   `decir()` termine sus pausas. Para una respuesta de 300 caracteres son ~9 s
   calculadas (12 trozos × 0.05 s + `len × 0.03`); la prueba empírica: al mandar
   `av_scan_start` justo después de una pregunta, tardó el escaneo en arrancar y el
   sondeo lo leyó como silencio. Arreglo: un hilo de escritura por conexión (cola +
   candado) para leer y hablar a la vez.
5. **Traza al cerrar la pestaña a media frase.** `Cannot write to closing transport`
   en `/tmp/cort_bridge.log`, línea 961 del puente. El servidor sobrevive, pero hay que
   envolver los envíos para tolerar conexiones muertas. Sucede cada vez que recargas
   mientras CORT está hablando, o sea constantemente.
6. **Paneles zombis con indicador de carga infinito** (sección 3). Cuestan 1 línea por
   panel: si no hay datos, decir «sin datos y por qué».

Nada de esto está arreglado todavía: lo medí para que la encuesta decida el orden.

---

## 10. Teléfono: el APK que ya tienes y lo que falta

Medido en `~/Escritorio/CORT-IA-2.11.0-nucleo.apk` (47.509.644 bytes, 55 entradas):

* `com.cort.ia`, firma propia (`META-INF/CORT.RSA`/`CORT.SF`).
* Voz **sin internet**: `assets/motor/vosk-model-small-es-0.42.zip` (39.817.833 bytes)
  más `libvosk.so` para `armeabi-v7a` **y** `arm64-v8a` → sirve para tu Galaxy A16.
* Su propia interfaz: `assets/ui/` con `orb.js` (31 KB), `hud.js` (130 KB),
  `diccionario.js` (41 KB), `mandos.js`, `gestures.js`, `voice.js`, `android-bridge.js`
  y `vendor/three.module.js` (1,27 MB) con su licencia.
* Configuración de asistente: `res/xml/asistente.xml` (388 B) — eso es un
  `VoiceInteractionService`.

Y hay un segundo linaje, más reciente, que **sí está en GitHub**:
`Sandra2244/CORT-nuevo` (público, rama `main`, actualizado 2026-10-29) con
`apps/bolsillo/` → `AndroidManifest.xml`, `compilar.sh`, `llave.sh`,
`src/com/cort/ia/{MainActivity, LeerActivity, LectorService}.java` y el workflow
`.github/workflows/apk.yml`. Los ficheros `CORT-IA-3.0.1-bolsillo-auditoria.txt` y
`-firma.txt` en `~/Escritorio/cort-bolsillo/` documentan el método: `aapt2` + `d8` +
`zipalign 4` + `apksigner` con la llave del secreto `CORT_APK_KEYSTORE_B64`, firmado
**v2 y v3 verificados**, `minSdk 26 / targetSdk 34`, 1,0 MB. **Ése es el método que
dices que «no molesta a Play Protect»**: compila GitHub, no tu Canaima (aquí no hay
SDK: `/usr/local/lib/android/sdk` no existe).

Para que el A16 te deje ponerla como **«Aplicación de asistente»** (ahora sólo aparece
Google) hace falta que la app publique el `VoiceInteractionService` en el manifiesto
con el intent `VoiceInteractionService` y un `xml/pre-services`, y después Android
pide confirmarlo una vez en Ajustes. El `nucleo` ya trae `res/xml/asistente.xml`, así
que el trabajo es heredar eso, no inventarlo. **No lo he probado en el teléfono
todavía**: es una decisión de la encuesta (implica que el micrófono se abra con el
botón de inicio).

---

## 11. Licencia y publicación: la situación real, sin adornos

* `~/Escritorio/CORT/LICENSE` ya puesto: **MIT © 2026 Sandra Sofia Lopez**.
* La demo de TechEnClair **no tiene licencia** (ni LICENSE ni encabezados). Legalmente
  eso significa «todos los derechos reservados», no «libre». Copiar la apariencia y
  reescribir el código es un terreno defendible, pero el texto de arriba no borra el
  origen.
* La carta pidiendo permiso por escrito está **escrita y sin enviar**
  (`~/Escritorio/JARVIS-FUENTES/PERMISO_TECHENCLAIR.md`, correo jean@domotique.fr +
  Discord). `cort-web/PROCEDENCIA.md` lo dice igual de claro y por eso la carpeta
  está marcada como «no publicar hasta la respuesta».
* Lo que sí es 100 % tuyo y se puede publicar **ya**: `cort-bridge/` (el puente Python,
  ~1000 líneas medidas) y `cort-web/cort/` (interfaz, traducción, mock, estilos,
  rediseño). Nada de eso es una copia del JS de la demo.
* Para la referencia visual honrosa en GitHub y en las etiquetas hay una redacción que
  es cierta y además te protege: *«interfaz inspirada en el proyecto JARVIS web de
  TechEnClair, con su permiso solicitado; código, puente Python, rediseño, traducción
  y funciones desarrollados desde cero»*. Lo que no se puede escribir es que no tiene
  ninguna relación, porque la tiene y está documentada en `PROCEDENCIA.md`.

---

## 12. Límites duros que no se negocian (por tu equipo)

* 2 núcleos y 1851 MB. Ollama + navegador + servidor de desarrollo a la vez = congelación.
* Puerta de descarga: disco libre ≥ peso + 500 MB. Puerta de carga: RAM libre ≥
  peso × 1,4 + 150 MB. Las dos se citan con el número medido, nunca con un «no se puede».
* El antivirus informa y no borra procesos ni archivos.
* CORT no ejecuta órdenes reales («abre», «pausa», «reproduce», «apaga») mientras no
  aprobemos una zona de pruebas con `CORT_HOME` aparte.
* El turno de madrugada (`CORT_RAM_MIN=900 MODELO=smollm2:135m ./cort_cerebro.sh`) es
  la única forma realista de tener cerebro despierto en este equipo.

---

## 13. Lo que NO se hace en esta fase, y por qué

* **No se toca el JS minificado de la demo** para el orbe: se añade una capa nuestra.
  Editar 453 KB minificados es la ruta más rápida a romper sin poder volver atrás.
* **No se instala Jarvis OS / CORT OS como sistema operativo**: pediría tu disco entero.
* **No se integran servicios con clave de pago** (Spotify, YouTube API, Gmail, ElevenLabs)
  sin que tú los autorices y sin tarjeta: tú has dicho que no tienes Visa/Mastercard.
* **No se publican en GitHub las copias espejo** de la demo ni los `.orig`.
* **No se persiguen acortadores ni se ejecutan `.exe`** de terceros.

---

## 14. Orden propuesto (esto es lo que contesta la encuesta)

1. **Honestidad en pantalla** (bug 1, 2, 3, 6): 1 sesión, cambios pequeños, se nota al instante.
2. **Puente robusto** (bug 4, 5): cola de escritura + envíos tolerantes.
3. **Orbe tuyo** (tus dos vídeos): dispersión vórtice + color por estado.
4. **Globo 3D tuyo** (Leaflet local, posición real, vuelo a ciudad).
5. **Capa de acciones Linux** para la familia de 35 comandos, en zona de pruebas.
6. **Encuestas → decidir las 3 familias que merecen la pena** antes de escribir código.
7. **APK** sobre el método de `CORT-nuevo` (Actions), como app de asistente.
8. **Publicación** en `Sandra2244/CORT` cuando el rediseño ya lo haga distinto.
