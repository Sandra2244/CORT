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

---

## 15. Censo completo del 4 de noviembre — la versión que se publica

**Puente medido:** el instalado en `~/Escritorio/CORT` tras correr `scripts/instala_cort.sh`,
con los datos reales de la casa (`~/.local/share/cort`).
**Cómo se midió:** `scripts/inventario_funciones.py` manda cada orden de **leer** por el
WebSocket y espera el mensaje que el propio puente promete devolver (el mapa está leído en
`cort_server.py`, no adivinado). 29 sondas, `nice -19`, carga del equipo entre 6,7 y 9,9.
**Nada de esto ejecuta una orden de actuar:** `pc_accion`, `open_browser`, `mic_on`,
`vision_on`, `start_ollama` y `pull_ollama_model` se dejaron fuera a propósito.

| orden | qué contesta | origen | ms | qué se ve en pantalla |
|---|---|---|---|---|
| `system_stats` | `system_stats` | real | 4 | cpu 98,7 % · 118 MB libres de 1851 · disco 22,3 % |
| `check_ollama_status` | `ollama_status_reply` | real | 8 | apagado; 6 modelos en disco |
| `perfil_equipo` | `perfil_reply` | real | 1040 | Celeron N2805, 2 núcleos, sin AVX/AVX2, nivel 0 |
| `buscar_actualizacion` | `actualizacion` | real | 4781 | 30 etiquetas de otra base; ninguna `cort-` comparable aún |
| `get_settings` | `settings_data` | real | 4374 | ciudad Carora, modelo pedido `smollm2:135m`, idioma es |
| `get_shopping_list` | `shopping_list` | real | 15 | lista vacía, en `~/.local/share/cort/vida` |
| `vida_estado` | `vida_estado` | real | 44 | 0 compras · 0 notas · 0 pendientes |
| `ha_get_states` | `ha_states` | real | 11 | «no hay Home Assistant en esta red» |
| `temperatura` | `sala_temperatura` | real | 16 | TCPU 49,0 °C (4 sensores leídos de sysfs) |
| `weather` | `weather_panel` | real | 2376 | Caracas 18,9 °C, sensación 21,0, nublado |
| `get_agent_models` | `agent_models_info` | real | 0 | familia de modelos disponibles por rol |
| `check_jarvis_os_status` | `jarvis_os_status_reply` | real | 6 | nada escuchando en 127.0.0.1:3000 |
| `check_local_tts_status` | `local_tts_status_reply` | real | 206 | Piper sí, Chatterbox no (a propósito), motor `rapida` |
| `voz_estado` | `voz_estado` | real | 144 | sin altavoz físico: sólo `auto_null` |
| `mic_estado` | `voz_estado` | real | 148 | el mismo inventario: no hay fuente de captura en el PC |
| `vision_estado` | `vision_estado` | real | 15 | «la mirada está apagada» (encenderla es orden tuya) |
| `memoria_estado` | `memoria_estado` | real | 5 | archivo existe, 1 preferencia, constitución de 786 caracteres |
| `check_kokoro_status` | `kokoro_status_reply` | real | 5 | Kokoro no; en su lugar Piper + espeak-ng con sus números |
| `pc_estado` | `pc_estado` | real | 11428 | ventanas, volumen y apps leídas de wmctrl/pactl/sysfs |
| `detect_apps` | `detected_apps` | real | 10 | apps leídas de los `.desktop` del sistema |
| `get_installed_programs` | `installed_programs` | real | 718 | leído con dpkg, con tamaño en KB |
| `get_winget_upgrades` | `winget_upgrades` | real (en arena) | 7638 arena / >20000 aquí | «winget no existe en Linux: leído con `apt list --upgradable`» |
| `games_get_library` | `games_library` | real | 2376 | biblioteca de `.desktop` con categoría Game; sin Steam |
| `get_desktop_wallpaper` | `desktop_wallpaper_result` | real | 284 | leído con xfconf-query |
| `av_scan_cancel` | `av_cancel` | real | 1 | cancela si había análisis; si no, lo dice |
| «hola CORT, qué eres» | `jarvis_text` | real | 325 | se describe y dice que distingue real de simulado |
| «qué sabes de mí» | `jarvis_text` | real | 4104 | «Sé 1 cosa de ti: te llamas Sandra…» |
| «qué hora es» | `jarvis_text` | real | 3359 | «Son las 02:24» |
| «gracias» | `jarvis_text` | real | 2032 | dice sin rodeos que no hay cerebro local y por qué (217 MB libres) |

**28 de 29 contestan con `origen: real`.** La que no llegó aquí (`get_winget_upgrades`) sí
contestó en 7,6 s contra el puente de arena: `apt list --upgradable` se arrastra con el
equipo al 98 % de CPU. Es lento, no mudo, y ya está apuntada su mejora.

### Lo que este censo destapó (confesado antes de arreglado)

1. **`instala_cort.sh` fallaba a medias**: pedía `vosk.__version__` y el paquete vosk no
   expone ese atributo → `AttributeError` y el instalador se caía antes de escribir el
   lanzador. Ahora lee la versión con `importlib.metadata` y el instalador terminó
   entero en esta máquina (eso es como está medida la tabla).
2. **En MX Linux 13 + XFCE no hay instancia de usuario de systemd**: `/run/user/1000/bus`
   no existe y `systemctl --user` contesta «Failed to connect to user scope bus». El
   instalador ya lo comprueba y, cuando no está, lo dice y deja el arranque automático
   de XFCE, que es el que funciona en esta laptop. En Debian/Ubuntu con user manager sí
   escribe y activa la unidad.
3. **`mic_estado` no estaba roto**: contesta con el inventario de voz completo
   (`voz_estado`), y la primera versión del censo buscaba un mensaje `mic_estado` que
   nadie manda. El fallo era del sondeo, no del puente — por eso el mapa de respuestas
   se leyó en el código en vez de adivinarse.
4. **La memoria real estaba vacía.** El puente vivo contestó «Aún no sé nada de ti».
   Todo lo que se midió en S4 con nombre y examen era arena (`/tmp`). Para cerrar la
   prueba de escritura contra tus datos reales se guardó una sola cosa, y es tuya:
   `preferencias.nombre = "Sandra"`. Se borra así:
   `rm ~/.local/share/cort/memoria.json` (CORT vuelve a preguntar y a empezar de cero).
5. **`Sé 1 cosas de ti`** salía con el plural mal cuando había un solo asunto. Corregido
   y verificado en vivo: «Sé 1 cosa de ti: te llamas Sandra».

### El oído del teléfono, medido (F7)

`POST /mic` con un WAV de 16 kHz mono 16 bits, generado con espeak-ng + sox
(`scripts/prueba_mic_telefono.py`, 7/7 casos):

| qué | cifra |
|---|---|
| round trip completo, primera subida (modelo Vosk cargando) | 22 440 ms |
| round trip con el modelo ya en RAM | 2 820 ms |
| trabajo de transcripción solo (Vosk) | 2 463 ms sobre 2 s de audio |
| audio que cabe por la ruta | 4 MB = ~62 s de habla |
| qué queda en disco después | nada: el WAV se borra (`micro-*.wav` no existe) |
| qué pasa si sube otra cosa | `ok: false`, `origen: no disponible`, «lo que subió el teléfono no es un WAV» |

Condiciones para que el teléfono alcance al puente: abrirlo a la red local
(`instala_cort.sh --red`, que pone `CORT_BIND=0.0.0.0`). Sin HTTPS la PWA no se instala en
Android y el navegador no da micro por `http`, y de ahí que el cliente sea un APK.


## 16. El APK publicado: `cort-v0.11.0` (4 de noviembre, 06:41–06:45)

Lo que estaba escrito y sin compilar ahora es un archivo descargable. Dos runs verdes de
`.github/workflows/apk-movil.yml`: `41787218390` (push de la rama, 25 s) y `41787686415`
(push de la etiqueta, 22 s). El segundo confirma que el `versionName` también sale del
nombre de la etiqueta, no sólo del `workflow_dispatch`.

| qué | cifra medida |
|---|---|
| peso del APK | **16 873 bytes** (0,016 MB) |
| lo que hay dentro | `AndroidManifest.xml` 2 352 · `classes.dex` 15 120 · `resources.arsc` 952 · icono vectorial 640 · `META-INF` de la firma |
| versión y código | `versionName 0.11.0`, `versionCode 1100` (derivado de la versión; manda Android para decidir si es actualización) |
| SDK | minSdk 26 · targetSdk 34 · compilado con build-tools **37.0.0** sobre platform **android-37.2** (el runner tiene hasta API 37; el script toma el más nuevo y `--target-sdk-version` sigue fijando 34) |
| firma | **llave del repo**, no desechable: el secreto `CORT_APK_KEYSTORE_B64` estaba montado desde el 2026-10-21 (lo puso la otra línea). `llave: la del repo (se instala encima de la versión anterior)` salió impreso por el propio script, y la huella del certificado es `faabef468f3ae04fdfab9659d6a051c453d6ded7b965468c9c3b85caffa31977` |
| SHA-256 del APK | `bc384b621439e9f16ccaa3d55a1f8e67ab6664d3f9ea05c15a9ee7f71f8f4012` |
| comprobación externa | se volvió a descargar con `curl` desde la página de la release y la suma **coincidió byte a byte** (16 873 bytes, HTTP 200) |
| paquetes en el teléfono | `dev.sandra.cort.movil` (esta línea) y `dev.sandra.cort` (la de `main`) son **dos aplicaciones distintas**: conviven, no se pisan |

**Dos correcciones que se hicieron leyendo, no corriendo.** Este equipo no tiene `javac`
(OpenJDK 21 sólo runtime) ni SDK de Android, así que el Java no se puede compilar aquí: cada
error se paga con un run. Al releer `MainActivity.java` salieron dos —el recurso del WebView
se llama `PermissionRequest.RESOURCE_AUDIO_CAPTURE` y aquí estaba escrito `REQUEST_AUDIO_CAPTURE`,
que no existe; y el texto transcrito se metía al JS con comillas a mano, que un salto de línea
de Vosk rompía. Ambos corregidos antes de empujar, y el run salió verde a la primera.

**Lo que el run 22–25 s no demuestra.** Que el botón funcione con una voz real en un Galaxy
A16. La ruta `/mic` está medida con audio sintético (7/7, §15) y el APK está firmado y
descargable, pero nadie lo ha instalado aún en el teléfono: el permiso de micrófono, la
dirección del puente con `--red` y la latencia real con el Wi‑Fi de la casa son cosa de la
prueba física.

## 17. Cara publicable: marca, capturas reales y el cierre del idioma (4 de noviembre)

**La marca sale del orbe, no de un dibujo nuevo.** `cort-web/iconos/cort.svg` se genera
con la misma distribución de puntos que pinta `cort-orbe.js`: 140 puntos sobre una esfera
(espiral de Fibonacci, eje inclinado 0,42 rad), núcleo blanco–cian y dos órbitas (cian
sólida y magenta punteada), sobre `#03070d`. Paleta tomada de `cort-style.css`: menta
`#00ffc8`, cian `#22e5ff`, magenta `#ff2bd6`, violeta `#7b5cff`. Sin texto en el isotipo:
a 48 px una palabra no se lee y el launcher recorta los bordes.

| Archivo | cómo se obtuvo | medida |
|---|---|---|
| `cort.svg` | `rsvg-convert` (renderer real, no el de ImageMagick) | 13 595 bytes |
| `cort-192.png` / `cort-512.png` | rasterizados del SVG, los dos que pide `manifest.webmanifest` | 24 272 B / 89 799 B |
| `apps/android/res/mipmap-anydpi-v26/ic_cort.xml` | icono adaptativo generado con la misma matemática (21 puntos del hemisferio delantero) | 548 B + foreground 5 172 B + background 724 B |

**El icono ya está dentro del APK compilado.** Run `41803422504` del flujo `apk-movil`
(commit `911b2ff`): verde, **21 140 bytes** (antes 16 873; la diferencia son los vectores)
y al abrir el zip aparecen `res/mipmap-anydpi-v26/ic_cort.xml`, `ic_cort_foreground.xml` e
`ic_cort_background.xml`, los tres nombrados también en `resources.arsc`. `minSdk` es 26,
así que no hacen falta los PNG de densidades. Que pese poco es una decisión, no un olvido:
la carcasa nativa no lleva el cerebro dentro todavía — eso es F12, y ahí el peso sube a
decenas de MB con el modelo Vosk y las librerías.

**Capturas: todas reales, ninguna generada.** Se tomaron en el navegador integrado, cuyo
viewport está medido en **525×521**. Con 153 MB libres no se puede abrir un Chrome sin
interfaz para captar a 1600×900 (el límite es de RAM, no de ganas), así que el banner se
compuso con GraphicsMagick bajando cada captura de 525 a 380 px de ancho — reducir no
inventa detalle. `docs/promo/banner.png` (1600×720, 602 KB) lleva marca + 4 pantallas;
`docs/promo/recorrido.gif` (525×567, 6 fotogramas, 595 KB) recorre orbe → menú → pedido →
lista → repertorio → antivirus, con pie de foto quemado en cada cuadro. Las 7 capturas
quedan en `docs/promo/capturas/` por si hay que comprobar de dónde salió el banner.

**El detalle que la promo destapó: el medidor de idiomas mentía.** `window.CORT.estado()`
presumía «cobertura 100 %» contando sólo 504 cadenas como francesas, porque el clasificador
no reconocía el francés **sin tilde** ni palabras corrientes. Con el menú abierto se leían
`◈ CONTROLES_SYSTEME // MENU` e `INTELLIGENCE ARTIFICIELLE` en la pantalla. Al arreglarlo:

| | antes | después del arreglo |
|---|---|---|
| cadenas reconocidas como francesas | 504 | 644 |
| pendientes de traducir | 1 | 59 (36 + 23) |
| cobertura declarada | «100 %» | medida real |

Las 59 se tradujeron (958 triples `[fr, es, en]` más reglas para las que llevan datos
dinámicos pegados: `CHARGEMENT... N%`, `Caméra (…)`, los estados de instalar Ollama).
Cierre medido con todos los paneles abiertos —menú, lista, repertorio, antivirus y
Ajustes—: **1804 cadenas vistas, 644 francesas, 644 traducidas, 0 pendientes**.

Dos cosas se evitaron a propósito. «é» **no** entró en la firma de letras francesas: el
español la usa en «café», «esté», «hablé» y en el voseo, y habría contado como pendiente
texto que ya es español; esos términos entran uno a uno con la forma `[eé]`. Y quedaron
fuera del clasificador las grafías que son palabra española igual (`tres`, `video`,
`micro`, `agenda`, `carte`, `liste`, `tache`, `retro`): 33 casos de prueba, 0 falsos
positivos. Lo que el número no cubre: sigue siendo un detector por vocabulario, no una
traducción automática — una frase francesa con palabras fuera de la lista se escapa, y se
escapa en silencio.

## 18. El teléfono autónomo: F12 (4 de noviembre, 13:22–14:10)

Dos frases tuyas eran la misma cosa: *«no necesito ajuro una IP para usarlo»* y *«su apk no
pesa nada, no lo has compilado bien»*. Se arreglan metiendo el oído dentro.

**Qué entró en `apps/android`.** 18 clases Java, 5 119 líneas: la cara del orbe, el registro,
el cerebro de 33 reglas con 15 manos locales, la memoria SQLite del aparato y el traje de
asistente de Android, transplantados de la otra línea (`origin/main`) y adaptados a los
puertos de esta rama (interfaz 8766, core 8765). Y una clase nueva, `Motor.java`, que es lo que
quita la IP de en medio: Vosk con el modelo español dentro del teléfono.

**Los números del APK, del run 41881069892** (verde, `0.12.0`, `versionCode 1200`):

| | antes (`cort-v0.11.0`) | ahora (F12) |
|---|---|---|
| peso | 16 873 bytes | **59 335 837 bytes = 56,59 MB** |
| `classes.dex` | 15 120 B | 294 056 B |
| oído | el del aparato, **por internet** | Vosk dentro del APK + respaldo del aparato |
| dependencias | ninguna | Vosk 0.3.75 (Apache-2.0), JNA 5.14.0 (LGPL-2.1+), modelo (Apache-2.0) |
| firma | llave del repo `faabef46…1977` | la misma: se instala encima sin desinstalar |

Dentro del APK, medido sobre el archivo que bajé del artefacto y no del log:
modelo `vosk-model-small-es-0.42.zip` **39 817 833 B**, `libvosk.so` **10 042 800 B** (arm64) y
**8 985 628 B** (v7a), `libjnidispatch.so` 168 176 / 122 296 B, `habilidades.json` 9 770 B;
16 entradas y 59 458 359 B sin comprimir. La SHA-256 del APK
(`aa8dea3f…d5c1f4`) la volví a calcular aquí y coincide con la que publicó el runner.

**Tres cosas que se arreglaron al repasar el código transplantado, y se confiesan:**

1. `Puente.java` decía «la página vive en el 8780». En esta rama son 8766 y 8765.
2. El puente de esta rama **no sirve `/memoria/puente`** (sólo `POST /mic` y estática,
   `cort-bridge/cort_server.py:2808`), así que la sincronía con la PC da 404. `Sincroniza`
   ahora lo traduce: *«ese puente aún no tiene memoria compartida: la ruta llega con F14. CORT
   sigue acordándose aquí, en el teléfono»*. No se vende como hecho lo que no está.
3. La voz pedía `es-CO` porque la otra línea usa `speechSynthesis` con ese acento. **La voz del
   PC de esta rama es castellana** (`cort-bridge/cort_voz.py`: espeak-ng y Piper
   `es_ES-mls_10246-low` a 1,90× y `davefx-medium` a 2,55×), así que el teléfono pasó a `es-ES`
   y `scripts/prueba_apk.py` compara el `IDIOMA` del Java con los `.onnx` del puente. Fue un
   descuido de transplantar sin mirar la cara de la otra rama.

**Lo que sigue sin medir, dicho con la boca llena:** cuánto tarda el modelo en cargarse en el
A16, cuánta RAM ocupa y cuánto tarda un dictado real tuyo. `Motor.java` imprime el tiempo de
cada dictado (`ultimoDictadoMs`) para que esa cifra salga de la mano y no de un deseo. Lo que
sí está comprobado sin teléfono: el compile, la firma, que las `.so` van sin comprimir y
alineadas a página (`extractNativeLibs="false"` muere sin eso), y las 53 comprobaciones de
`scripts/prueba_apk.py` que corren sin red. Desde este commit la suite no es sólo de la laptop:
el workflow la ejecuta en el runner antes de publicar, y las notas de la release copian de su
salida el número de comprobaciones — hasta hoy lo decía el texto a mano, y se había quedado en
44 mintiendo sobre su propia prueba.

**Un bug que te tocó a ti:** el archivo `.sha256` del artefacto decía
`build/CORT-movil.apk`, así que `sha256sum -c` respondía *«no existe el fichero»* aunque la
suma fuera buena. Se anotó el nombre desnudo y hay una comprobación que lo vigila.

**Publicada (14:03–14:20, la parte de publicar costó tres corridas).** La release
[`cort-v0.12.0`](https://github.com/Sandra2244/CORT/releases/tag/cort-v0.12.0) está en GitHub con
sus cuatro archivos: `CORT-movil.apk` **59 335 837 bytes**, `CORT-movil.apk.sha256`,
`auditoria.txt` y `firma.txt`, señalando al commit `db45adc` del que salió el binario. La creó el
runner, no esta laptop: bajar el artefacto a casa se cortó dos veces por el enlace de ~40 KB/s.
Las dos caídas previas fueron medidas y están dichas aquí, no borradas — el run 41891940880
falló sólo en «publicar la release» con *«set the GH_TOKEN environment variable»* (código 4) y se
arregló pasando `GH_TOKEN: ${{ github.token }}`, que es el token efímero del job, no un secreto
nuestro; `contents: write` ya estaba. **Comprobado desde fuera**, sin fiarse del log:
`sha256sum -c` contra el `.sha256` de la release da OK con el nombre desnudo, y la suma publicada
en la página (`d4de166a…f08ab`) es la del archivo que se descarga.

**Y una mentira que se cazó a sí misma:** las notas decían «44 comprobaciones automáticas» cuando
la suite ya llevaba 51 (ahora 53). El número estaba escrito a mano en el YAML. Hoy el workflow
corre la suite en el runner y copia el total de su salida; si la suite cae, la release no se
publica. Dos comprobaciones nuevas vigilan eso.
