# CORT — análisis del núcleo inteligente (F9 a F13)

Escrito el 2026-11-03 con la máquina encendida y medida, no con teoría. Cada número de
aquí se tomó en la Classmate o en el A16 en las condiciones que se dicen.

---

## 1. Lo que mide esta máquina ahora mismo

| cosa | medido | qué significa |
|---|---|---|
| RAM total | **1851 MB** | techo duro, sin swap útil (swappen es congelar) |
| Qoder (agente) | **1,09 GB en 17 procesos** | mientras yo trabajo, el cerebro no cabe |
| puente CORT | **11 MB** | el puente no es el problema |
| libre con todo abierto | **150-178 MB** | ni el modelo más chico |
| libre con Qoder cerrado | **~1,25 GB** | aquí es donde CORT puede pensar |
| disco libre | **213 GB** | caben los 6 modelos de Ollama y cinco más |
| `adb` | **no instalado** | el PC no puede ver el teléfono por USB hoy |
| `~/Música/Dark Rose` | **1 pista (`2 on - tinashe … slowed reverb.mp3`)** | la playlist existe en el PC |
| `Stereo Love Slowed` en el PC | **no está** | esa pista vive en Lark Player del teléfono |
| reproductores en el PC | VLC y Strawberry (`/usr/share/applications`) | se puede mandar música aquí sin inventar nada |
| `~/Documentos` | existe | `~/Documentos/proyectos` **no existe** (buscado en 4 rutas) |

### Lo que pide cada modelo que ya está en tu disco

Corregido el 2026-11-03 a las 01:10: en la versión de Ollama que tienes, `ollama show`
**no** reporta "system requirements" (se comprobó con los cuatro candidatos: sólo da
arquitectura, parámetros, contexto, cuantización). Los pesos en disco sí están medidos,
y el servidor vacío también: `ollama serve` ocupa **35,9 MB** antes de cargar nada. La
columna de RAM es **estimación** (pesos + cache KV para 2048 tokens + overhead del
corredor), no medida; la sonda la convierte en número real.

| modelo | peso medido en disco | RAM estimada | ¿cabe con Qoder cerrado (~1,25 GB)? |
|---|---|---|---|
| smollm2:135m | 271 MB | ~450-510 MB | sí, sobrado |
| gemma3:270m | 292 MB | ~480-540 MB | sí |
| qwen2.5:0.5b | 398 MB | ~600-680 MB | **sí — el candidato** |
| qwen3:0.6b | 523 MB | ~780-850 MB | sí, justo |
| airaos-local | 718 MB | ~1,1-1,2 GB | al límite: riesgo de congelar |
| qwen3.5:2b | 2614 MB | ~3,8 GB | **no entra nunca en 1,8 GB** |

Con Qoder abierto quedan 170 MB (medido con el agente corriendo), así que ni el más
chico cabe mientras yo trabajo: por eso la sonda la corres tú con el agente cerrado.

---

## 2. La verdad del cerebro, dicha sin adornos

Un modelo de 0,5 B parámetros **no** comprende ni tiene consciencia: predice la siguiente
palabra. Lo que la gente percibe como "inteligente" en un asistente no es el tamaño del
modelo, es que **cada frase rara se traduzca a una orden concreta, se ejecute contra datos
reales y se verifique después**. Siri y Gemini hacen exactamente eso: el modelo propone y
un ejecutor determinístico hace.

De ahí la regla de arquitectura de CORT:

> **El modelo nunca toca el disco, la red ni el teléfono. Sólo propone un plan en JSON.
> El ejecutor valida el plan contra el estado real; si no valida, CORT pregunta o dice
> que no, y nunca finge que lo hizo.**

Esa es la respuesta directa a "que no delire": la alucinación se corta por el medio, con
validación, no con un modelo más grande. Un modelo de 7 B (los que planifican de verdad
en varios pasos) pide 4-5 GB: en esta máquina no existe, ni con Qoder cerrado.

Lo que **sí** se consigue con 0,5-0,6 B bien usado:

* entender frases largas y con errores de dictado («muevme varios archivo»);
* elegir entre ~30 verbos propios sin diccionario de frases fijas;
* rellenar huecos (`destino`, `pista`, `playlist`, `ciudad`) con lo que hay en el equipo;
* decidir si hace falta confirmar (borrar, apagar, mover fuera de casa).

Lo que **no** se consigue aquí y no se promete: razonar en varios pasos sobre algo que no
está en el disco, investigar temas complejos con fuentes, o aprender cosas nuevas por
conversación (entrenar/ajustar un modelo pide GPU y no se hace en esta máquina).

---

## 3. Arquitectura del núcleo (cinco capas)

```
micrófono / bandeja de texto
        │
   [1] OÍDO     wake word + STT (Vosk es-42 en PC; en el A16 puede ser siempre-encendido)
        │  texto
   [2] COMPILADOR  modelo local con salida JSON obligatoria (format/schema de Ollama)
        │  {"intencion":"mover","origen":"~/Documentos/proyectos","destino":"~/Documentos"}
   [3] VALIDADOR   comprueba rutas, permisos, lista blanca de raíces, verbos peligrosos
        │  plan aceptado / pregunta / rechazo con motivo
   [4] EJECUTOR    cort_acciones (PC) o la API del APK (teléfono), sin shell
        │  resultado con números
   [5] VERIFICADOR  re-lee el estado (¿existe en el destino? ¿está sonando?) y responde
        │
   voz + subtítulo + registro auditable (registro-acciones.jsonl ya existe)
```

Piezas nuevas que hay que escribir (F9/F10):

* `cort_intenciones.py` — el compilador: esquema JSON, 12 ejemplos tuyos como `few-shot`,
  temperatura 0, y una tabla de intenciones con sus argumentos obligatorios.
* `cort_archivos.py` — verbos de archivo (buscar, mover, copiar, crear carpeta, listar)
  con raíz blanca (`~/Documentos`, `~/Descargas`, `~/Escritorio`, `~/Música`,
  `~/Imágenes`, `~/Videos`) y `mv` sólo dentro de esa lista.
* `cort_media.py` — playlists leídas del disco (carpetas y `.m3u`) y control de VLC por
  MPRIS; en el teléfono, la misma interfaz la contesta el APK.
* en `cort_server.py`: la rama `plan` (frase → JSON → ejecutar → verificar) y el botón de
  "¿qué entendí?" para que se pueda corregir en una frase.

---

## 4. Tus cuatro frases, resueltas una por una

**a) «Investígame en Google qué es la toxoplasmosis»**
Ruta: [2] `intencion=investigar, fuente=google, tema="toxoplasmosis"` → [3] el puente
busca en tu disco si hay algo guardado de eso (nota/`~/Documentos`) → [4] abre la URL de
búsqueda en el navegador real (`cort_acciones.abrir_url`) y, si hay red, lee el primer
fragmento con `open-meteo`-style fetch propio → [5] responde con la fuente y la hora de la
lectura. **Sin red te lo dice, no lo inventa.** Hoy el puente ya sabe abrir el navegador
(F5 medido). Falta la capa `investigar` (F9).

**b) «Mueve la carpeta proyectos a Documentos»**
Ruta: [2] `mover` → [3] `~/Documentos/proyectos` **no existe** (acabo de buscarlo en 4
rutas): CORT responde «no encuentro esa carpeta; sí existe ~/Documentos. ¿La creo o te
refieres a otra?» en vez de mover lo que sea que casque por parecido. Cuando existe:
`mv` dentro de la raíz blanca, y [5] verifica con `ls` el destino y dice
«3 archivos movidos a ~/Documentos/proyectos (verificado)». **Nunca** `rm`, y fuera de las
raíces listas pide confirmación por escrito.

**c) «Pon en Lark Player la playlist Dark Rose y reproduce Stereo Love Slowed»**
Ésta es la difícil y tiene dos mitades distintas:
* En el **PC** se puede hoy: `~/Música/Dark Rose` existe; se lee la lista, se busca la
  pista por parecido de nombre y se manda a VLC por MPRIS. Si la pista no está (como
  `Stereo Love Slowed`, que no está en el PC) CORT dice «no está en ~/Música; está en el
  teléfono» — con el dato real, no con un silencio.
* En el **teléfono** hace falta el APK (F11/F12). Lark Player no tiene API pública; se le
  llega por dos vías reales: **(1) MediaStore** — leer `MediaStore.Playlists` y
  `MediaStore.Audio` (con `READ_MEDIA_AUDIO` en Android 13+) y abrir la pista con
  `Intent(ACTION_VIEW, content://media/external/audio/media/<id>)`, que Lark intercepta;
  **(2) MediaSession** — `MediaController`/`AudioPlaybackCapture` requiere permiso de
  notificaciones y sólo controla lo que ya suena (pausa, siguiente), no puede pedir
  "busca tal pista". La vía (1) es la que da el "reproduce Stereo Love Slowed".
  **adb no está instalado** y el teléfono no se ve por USB: sin APK no hay forma de que
  el PC toque la música del teléfono.

**d) «Que arranque con el teléfono, te salude y se quede en segundo plano»**
Es un trabajo de app nativa, no de web: `RECEIVE_BOOT_COMPLETED` + `ACTION_USER_PRESENT`
para el «hola, buenos días Sandra» (con tu nombre, que ya está en el estado del puente),
un **servicio en primer plano** con tipo `microphone` para no que cuando la pantalla se
apaga, y en One UI 7 hace falta pedir `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` o el sistema
lo mata (medido en cualquier app de dictado). El botón de auricular mantenido y el botón
Función de la pantalla bloqueada se atienden con `MediaButton` + `KEYCODE_ASSIST` y con
ser la **aplicación de asistente digital** elegida: para eso el APK declara un
`VoiceInteractionService` con `BIND_VOICE_INTERACTION`; sólo así CORT aparece en la
pantalla que tú fotografiaste (hoy esa lista sólo tiene Google, porque ninguna otra app
declara ese servicio). La pantalla transparente con la estética de CORT es una ventana de
superposición (`SYSTEM_ALERT_WINDOW`, permiso "mostrar sobre otras apps") dibujada por el
propio `VoiceInteractionSession`. **Una PWA no puede hacer nada de esto**: el navegador no
tiene permisos de asistente, no arranca con el teléfono y no se superpone a otras apps.

---

## 5. Presupuesto de latencia (tu objetivo: 4-5 s)

Tramos medidos o estimados, marcados como tales:

| tramo | PC (Classmate) | A16 | estado |
|---|---|---|---|
| wake word + fin de frase | 0,4-1,2 s | 0,3-0,8 s | **por medir** (F10) |
| STT Vosk es-42 | **1,8× el audio** (medido: 3,9 s de audio = 7,0 s) | ~0,5× esperado | medido en PC |
| compilador qwen 0,5-0,6 B | ~1,5-3 s (2 núcleos) | no aplica (va al PC por Wi-Fi) | **por medir** (F9) |
| validación + ejecución | 0,1-0,5 s | 0,2-1 s (MediaStore) | medido en F5 |
| verificación | 0,1-0,3 s | 0,1-0,3 s | medido en F4 |
| síntesis de voz | **0,14 ms/ms** (espeak-ng, medido) | 0,1× (media/nativo) | medido |

Conclusión honesta: **en el PC no se cumplen los 4-5 s** con una frase de 6-8 s de audio
(sólo el oído tarda ~10 s). **En el A16 sí es alcanzable** (8 núcleos para el oído y el
cerebro de 0,5 B en el PC por Wi-Fi, o el modelo pequeño dentro del teléfono). Ésa es la
razón por la que el teléfono es el frente donde CORT tiene que oír, y el PC donde actúa.

---

## 6. Fases propuestas

| fase | qué entrega | se corta si… |
|---|---|---|
| **F9 — compilador de intenciones** | `cort_intenciones.py` + `cort_archivos.py` + `cort_media.py`; tus frases largas → JSON → ejecutar → verificar. Prueba: 12 frases tuyas, con el modelo cargado y Qoder cerrado | — (es el corazón que pides) |
| **F10 — oído en el PC** | wake word «oye CORT» con gramática de Vosk + botón para hablar; medida real de factor de tiempo | se aplaza si el factor >1,5× (se dice con número) |
| **F11 — APK asistente (F7 pendiente)** | `VoiceInteractionService` + overlay transparente + saludo al encender + dictado en segundo plano; instalada y elegida como asistente en tu A16 | — |
| **F12 — manos del teléfono** | MediaStore: listar playlists y pistas, reproducir por nombre, pausar/siguiente; API local al puente por Wi-Fi con token | se recorta a "abrir la playlist" si MediaStore no expone las listas de Lark |
| **F13 — investigación con fuentes** | `investigar` = búsqueda real + lectura del fragmento + cita con URL y hora; sin red lo dice | entra al final |

**No entra** (y por qué): entrenar o afinar un modelo propio (sin GPU y sin tarjeta para
alquilar una); un cerebro que razone en 6 pasos (pide 4-5 GB de RAM); controlar el teléfono
por adb (el PC no lo ve y no se instala software de terceros de un acortador).

---

## 7. Cómo se mide el cerebro sin congelar la máquina

`scripts/sonda_cerebro.sh` (escrito en esta fase) hace la única prueba decisiva: mide la
RAM disponible, **se niega** a cargar si no hay 900 MB, arranca Ollama, y corre
`scripts/cerebro_prueba.py` con los dos candidatos (`qwen2.5:0.5b` y `qwen3:0.6b`, ambos
ya en disco): pasa tus 12 frases reales por el compilador, apunta cuántas JSON salieron
bien y cuántos tokens/s da, y libera el modelo al terminar. Se corre **con Qoder cerrado**,
porque con el agente abierto la RAM libre medida hoy es 170 MB y el resultado sería una
máquina congelada, no una medida.

Salida esperada en el archivo `~/.local/share/cort/registro-cerebro.jsonl`: por cada frase,
el JSON que propuso el modelo, si el validador lo aceptó y los milisegundos que tardó. Con
eso se decide el modelo (0,5 B vs 0,6 B) con datos, y no por gusto.

---

## 8. La reja ya está construida y medida (2026-11-03, 01:00)

El modelo todavía no se midió (hace falta Qoder cerrado), pero la parte que no depende
de él ya corre y ya tiene número: `cort_archivos.py`, `cort_media.py`,
`cort_intenciones.py` y su prueba `scripts/prueba_intenciones.py`.

| qué | medido |
|---|---|
| casos de la reja | **18 / 18 correctos**, salida 0 |
| planes buenos ejecutados | 6 (mover, listar, crear, reproducir, JSON en cercado, JSON plano en inglés) |
| planes malos frenados | 12 (borrar, `/etc`, `../../../../etc/passwd`, prosa en vez de JSON, verbo inexistente, argumento faltante, sobrescribir sin confirmar, vacío, dos rutas ambiguas) |
| raíces reales en esta laptop | `Documentos`, `Descargas`, `Escritorio`, `Imágenes`, `Música` — `Videos` **no existe** |
| pistas encontradas en `~/Música` | **16** (la carpeta `Dark Rose` está entre ellas) |
| reproductor | `vlc` presente; `playerctl` **ausente** → pausar/siguiente responden «no puedo» en vez de fingir |
| borra algo CORT? | no existe el verbo: `dir(cort_archivos)` no tiene `borrar`, `rm` ni `vaciar` |
| sobrescribir | con `confirmar=True` lo anterior se rescata como `informe-cort-010058.txt`; sin confirmar, se pide |

Lo que falta para cerrar F9 es el primer tramo (frase → JSON): el modelo, que mide la
sonda. La reja no cambia cuál sea el modelo que se elija.

### 8.1 Y ya está conectado al puente y a la pantalla (2026-11-03, 02:15)

`scripts/prueba_nucleo.py` sube un Ollama falso en un puerto de arena, arranca el puente
contra una casa falsa y habla por WebSocket como lo hace la interfaz:

| qué | medido |
|---|---|
| frases de extremo a extremo | **7 / 7 correctas**, salida 0 |
| qué se le mandó al modelo | `format=json`, `temperature=0` en las **6** llamadas a `/api/generate` |
| la charla sigue siendo charla | «hola buenos días» → sin `plan_resultado`, con respuesta del chat |
| confirmación con sí humano | `confirma` ejecutó y rescató lo viejo como `informe-cort-021204.txt` |
| casa real | `~/Documentos/proyectos` **no existe** antes y después: intacta |
| regresión F4 | `prueba_vida.py 8775` → salida 0, `TIPOS VISTOS` con 10 `jarvis_text`, **nada** sin `origen: real` |

En la pantalla (navegador integrado, viewport 525×521):

| qué | medido |
|---|---|
| bandeja de petición | 12,453 · 501×56 — la frase se escribe y se manda, el campo se limpia solo |
| tarjeta del plan | 12,256 · 430×113 (y 12,221 · 430×148 con el botón) — título `hecho · mover_archivo · real`, la frase entre comillas, los argumentos y lo que CORT dijo |
| botón «Confirmar» | 25,331 · 85×27, sólo cuando el motivo habla de confirmación; al pulsarlo llega `«confirma»` y la tarjeta cambia a `hecho · real` |
| choque que se corrigió | la bandeja tapaba el badge de voz (clicable, 6,439) y las tres líneas de estado (458/479/487); las cuatro se subieron a la franja libre 12,50 → 12,138 |
| segundo choque corregido | la tarjeta a `bottom:78` tapaba micrófono, silencio y escucha continua (197,378 · 58×58); ahora a `bottom:152` |

Un detalle sin resolver y dicho aquí para que no se pierda: en el primer volcado de F4
apareció un `jarvis_text` con el texto en inglés «Weighing the options…». No está en
ningún archivo del repo y **no volvió en tres corridas completas** (`grep -c` = 0). Se
queda mirando; si reaparece, se rastrea por la hora del mensaje.

---

## 9. L1 · D1 · M1 · M2 · U1 (2026-11-03, madrugada)

### L1 — la autoría es de Sandra y Askher
`LICENSE` reemplazada: atribución + uso libre + **prohibición de monetizar** sin atribuir
créditos y sin contacto previo a `Sandrasofialopezgomez3@gmail.com` / `Carlosa3325@gmail.com`;
`© 2026 Askher Vargas y Sandra Lopez`. Se agregó `AVISO_LEGAL.md` y la pantalla de arranque,
el rótulo del HUD, la fila de Ajustes y la respuesta a «¿quién te creó?» dicen lo mismo en
español. TechEnClair queda acreditado **sólo como referencia visual** (maqueta y orbe) y
Cortana como estilo; no hay asset de Microsoft en el repo.

### D1 — rediseño Cortana y bandeja de tirador (medido en 525×521)

| qué | medido |
|---|---|
| tirador ‹ › | 0,381 · 34×66 — tocado, la bandeja sale de 12,453 (447×56) y se va a x=-461 con `opacity:0` y `pointer-events:none`; el segundo toque la devuelve a x=12 |
| chip ◉ del cerebro | 0,327 · 34×44, con punto rojo de aviso arriba a la derecha cuando hay versión nueva |
| botones del pie | micrófono 146,378 · escucha continua 234,378 · silencio 322,378 (los tres 58×58, centros equidistantes 88 px alrededor de 263) |
| franja superior | badge de voz 12,50 · 326×48; debajo, las tres líneas de estado |
| arreglo para el teléfono | el `mouseenter` que abría la bandeja ahora sólo se escucha con cursor de verdad (`hover:hover and pointer:fine`): en Android el navegador dispara el hover antes del click y abrir+cerrar en el mismo toque dejaba la bandeja inservible |

### M1 + M2 — bajar y probar modelos desde la propia pantalla
Panel `#cort-cerebro`: estado de Ollama, RAM libre medida, núcleos, y una fila por modelo con
`en disco N MB · pide ~M MB · cabe / no cabe ahora`. Los no bajados traen botón **descargar**
(con progreso por WebSocket) y todos los instalados **probar el cerebro**, que hace un disparo
real con `format:json`, `temperature:0` y `num_ctx:2048` y devuelve `ms`, `tok/s`, el plan y si
la reja lo aceptaría. La puerta de RAM manda: con 172-233 MB libres medidos, ningún modelo
cabe y CORT lo dice con la cifra en vez de congelar el equipo. `scripts/prueba_sonda.py` cierra
el ciclo sin modelo: falso Ollama + modelo de juguete en arena → `mini:1m respondió en 4 ms
(105.0 tok/s) · reja: acepta`, y `auto_sonda()` escribe `mediciones/medicion-cerebro.json` en
cuanto la RAM supere el umbral (900 MB por defecto).

### U1 — canal de actualización (7/7 en `scripts/prueba_actualiza.py`)
`cort-bridge/cort_actualiza.py` lee las etiquetas del repo **derivado de `git remote`** y la
versión local de `git describe`; consulta GitHub con 8 s de tiempo de vida y responde
`origen: real` o `no disponible`. El primer aviso real midió
`{version_local: 0.9.0, remota: v0.17.0, hay_nueva: true, sin_etiqueta_local: true}` y en la
pantalla quedó, arriba del panel y sin hacer scroll:

> **nueva versión** v0.17.0 · local 0.9.0 · git fetch --tags y revisa
> https://github.com/Sandra2244/CORT/tags — cambiar de versión con `git checkout v0.17.0`
> reescribe el árbol de trabajo, así que se hace con el proyecto commiteado y decidido por ti
> · origen real

**CORT no se autoinstala.** Bajar y cambiar código en el equipo de la usuaria es decisión suya;
el puente informa el número, el comando y dónde mirar. Dos defectos corregidos en esta fase:
las variables de entorno se leían al importar (los cuatro casos de prueba devolvían el mismo
dict) y el repo venía adivinado — adivinarlo mandó la primera corrida a buscar etiquetas de un
proyecto que no era el suyo, y el consejo de `git checkout` habría reescrito su árbol de trabajo.

### S1 — escáner de capacidades (14/14 en `scripts/prueba_perfil.py`)
`cort-bridge/cort_perfil.py` lee `/proc/cpuinfo`, `/proc/meminfo`, `sysfs` y `lspci` y saca dos
cosas: el **nivel de cerebro** al que aspira el equipo ahora mismo y el **plan de degradación**
(lo que se apaga para que lo importante quepa). Las pruebas no comprueban el número de esta
laptop —ése se ve en la pantalla— sino la **decisión**: un chip sin AVX se queda en nivel 0
aunque tenga 15 000 MB libres, CUDA sube al 3, y sin cámara los gestos se apagan solos con su
motivo.

Lo que dijo la Canaima medida (no de memoria):

| Qué | Número | De dónde sale |
|---|---|---|
| CPU | Intel Celeron N2805 @1467 MHz, 2 núcleos | `/proc/cpuinfo` |
| Instrucciones | `sse4_2` sí, **AVX no, AVX2 no** | flags del kernel |
| RAM | 174–282 MB libres de 1851 | `MemAvailable` |
| GPU | Atom Z36xxx/Z37xxx, `/dev/dri/card0`, sin CUDA | `lspci` + `/dev/dri` |
| Cámara | `/dev/video0` y `/dev/video1` («USB 2.0 Camera») | `/sys/class/video4linux` |
| Temperatura | 47–49 °C (sensor TCPU) | `/sys/class/thermal` |
| Carga | 4,15–8,69 a 1 min | `os.getloadavg()` |
| Nivel | **0 — reglas locales** | el motivo, abajo |

El motivo del nivel 0 es doble y ahora está dicho con la instrucción concreta: *los binarios
oficiales de llama.cpp piden AVX y revientan con `Illegal instruction`* — además de la RAM, que
ya se sabía. Esto explica por qué el cerebro nunca cargó aquí aunque hubiera modelos en disco.

El escaneo **no es un cartel, es comportamiento**. Conectar la interfaz dispara la medición sola
(397 ms de ida y vuelta por WebSocket, medido en arena con `CORT_WS_PORT=8791`) y el plan se
obedece: `CORT_orbe.tope(30)` baja el techo de fotogramas del orbe —con tope 0 se conserva el
comportamiento anterior, 20 fps en reposo y a tope con efecto— y las rejillas de scanlines de los
17 paneles pasan a `display:none`. En la pantalla de 525×521 la tarjeta quedó en y=215, alto 193
(fondo 408), visible sin scroll, con el botón `reescanear` y la marca `medido 2026-11-03 10:03:27`.

`latido_perfil()` re-mide cada `CORT_PERFIL_CICLO` (900 s) y **sólo avisa si el nivel cambia**:
la RAM de esta máquina se mueve de 150 a 350 MB según lo abierto, así que el nivel de hace una
hora no es el de ahora. Y `auto_sonda()` (M2) pregunta primero al perfil: si el chip no tiene
AVX se para con el motivo en vez de estrellarse cada diez minutos contra el mismo muro.

### S2 — la mirada: cámara → gesto → ventana (11/11 en `scripts/prueba_vision.py`, 5/5 en `cort_vision.py selftest`)

`cort-bridge/cort_vision.py` hace lo que se pidió con la cámara: **una mano delante de la
webcam mueve ventanas**. No hay modelo de visión —no cabe en 1851 MB— y no hace falta: se
detecta piel por croma (Cb/Cr del propio YUY2), se mide el bulto y su centro, y cuatro gestos
discretos se traducen en las cuatro órdenes que ya estaban en la voz.

Medido en esta máquina, con la webcam real y el navegador cerrado:

| Qué | Número | De dónde sale |
|---|---|---|
| Formato que negocia | **YUY2 320×240, 153 600 B/cuadro** | GStreamer + `/dev/video0` |
| Ritmo real | **14,9–15,1 cuadros/s** (67–68 ms entre cuadros) | `estado()["fps_reciente"]` |
| Coste de la pasada | **1,9–4,6 ms/cuadro** (2,5 con la máquina quieta, 4,6 con el navegador y el agente abiertos) | `estado()["ms_calculo"]` |
| Arranque | **~2,4 s** hasta el primer cuadro | cronometrado en el puente |
| Worker | **33,7 MB** de RSS, proceso aparte con `/usr/bin/python3` | `ps` |
| Cuadros acumulados en la prueba de puente | **1092** sin disparar un gesto | `vision_off` |

El detalle que costó: pedir `framerate=10/1` **clavado** pone la tubería en `failure` y no sale
ni un cuadro —esta cámara sólo sabe dar 15/1 a ese tamaño. Se pide el rango `[1/1, 30/1]` y
negocia lo que puede. Esto se probó por las malas: la primera vez la mirada «se encendía» y no
traía nada.

**Gestos y qué hacen de verdad** (`GESTO_A_ACCION`, verificado con `xprop _NET_WM_STATE` sobre
dos terminales que abre y cierra la propia prueba):

| Gesto | Orden | Verificación medida |
|---|---|---|
| barrido derecha/izquierda | `cambiar_ventana` | la ventana activa pasa de `0x06000003` a `0x06200003` |
| palma arriba / mano levantada | `maximizar` | `_NET_WM_STATE_MAXIMIZED_VERT/HORZ` presentes |
| empujar abajo | `restaurar` | las banderas desaparecen (queda `FOCUSED`) |
| puño | `minimizar_activa` | `wmctrl -b add,hidden` |

Un error que habría hecho todo esto inútil: `xdotool getactivewindow` imprime el id en
**decimal** (`90177540`) y `wmctrl` en hexadecimal (`0x059f0004`). Sin convertir, la ventana
activa «no se podía leer» y el barrido se aplicaba a la primera de la lista. Ahora se normaliza
a `0x%08x`.

**El falso positivo que encontró la cámara real, y cómo se cerró.** La primera prueba con la
webcam encendida y la usuaria sentada delante dio, en 8 segundos, **ocho gestos `palma_arriba`**:
la cara y el pecho cumplen la regla de «bulto de piel grande en la mitad de arriba» (medido: área
15 %, centro (0,53 / 0,28), `mov` 0,0000–0,0003). Con el puente vivo eso maximiza una ventana por
segundo sin que nadie mueva la mano. La solución no es subir el área —el bulto real de una mano
y el de una cara tienen un tamaño parecido—, es exigir **cambio**:

* `MOV_MINIMO = 0,02`: palma y puño sólo cuentan si en la ventana se movió al menos el 2 % de los
  píxeles. Medido en escena quieta: 0,00–0,23 %. Es decir, el piso está **ocho veces por encima**
  del ruido de una persona sentada, y una mano que entra en cuadro mueve el 18,8 % (caso g del
  `selftest`).
* *la mano tiene que **llegar***: dentro de la ventana tiene que haber al menos un cuadro sin
  bulto. Quien ya está en el cuadro no puede dar la orden; se espera el gesto.
* `REFRACCARIO = 2,0 s` entre órdenes (antes 1 s): la misma mano repetía.

Verificado dos veces: en sintético (`selftest` 7/7, con los casos «una persona quieta no es un
gesto» y «la palma que llega sí lo es») y con la webcam real apuntando a la usuaria: **59 cuadros,
bulto en los 59, área media 15,0 %, mov máximo 0,23 %, 0 gestos emitidos**. En la suite de
ventanas, el mismo caso con un worker que manda 44 cuadros quietos: `0 gestos`.

Por el puente (`cort_server.py`): `vision_on` / `vision_off` / `vision_estado`, y el puente
empuja `vision_gesto` y `vision_estado`. Tres puertas antes de encender —módulo cargado, cámara
vista por S1, RAM libre≥ el piso del worker— y cada una dice su motivo con número. Medido por
WebSocket en arena (`CORT_WS_PORT=8790`): `vision_on` contesta en **1,01 s**, y a los 5 s el
estado empujado traía `cuadros:300, fps_reciente:15, ms_calculo:1.9`.

En la interfaz, la tarjeta `mirada` vive dentro del panel del cerebro, justo debajo del escaneo
de S1: 389×112 px en la pantalla de 525×521 (y=416, visible sin scroll), botón de **122×34 px**
—el mínimo que se puede tocar con el pulgar en el A16—, y mientras la cámara calienta dice
*«esperando el primer cuadro (la cámara tarda ~2,4 s)»* en lugar de un `0 cuadros/s` que
parecería un fallo. El botón y el estado se probaron contra el puente real: encendido → `15
cuadros/s · 300 leídos · 3,9 ms`; apagado → `mirada apagada · 334 cuadros`.

**Nunca se guarda una imagen.** El worker vierte bytes crudos por un pipe, el hilo saca cuatro
números y tira el cuadro; no existe en el código ninguna ruta que escriba un cuadro a disco. Si
algún día la hubiera, esta frase se borra.

### S4 — carisma y memoria escrita: constitución, autocorrección e iniciativa (23/23 en `scripts/prueba_memoria.py`, 16/16 en `cort_memoria.py selftest`)

`cort-bridge/cort_memoria.py` (599 líneas) responde a la pregunta que abrió la fase: *¿cómo
aprenden Claude o Gemini, y puede CORT aprender igual?* Hay dos mecanismos que se llaman
«aprender» y no son el mismo.

| Mecanismo | Qué pasa dentro | Qué hace falta | Qué hace CORT |
|---|---|---|---|
| Entrenar pesos | predecir el token siguiente miles de millones de veces sobre una constitución de principios, y auto-reflexionar sobre las propias respuestas | GPU, días, terabytes | **no**: sin AVX/AVX2 y con 158–268 MB libres medidos en `/proc`, ni siquiera cabe un modelo de 1 B cargado |
| Memoria escrita | guardar en un archivo lo que la usuaria corrigió o pidió recordar, y **re-inyectarlo en el prompt** cada vez que se habla | leer y escribir texto | **sí**: 2,16 ms por ciclo memoria+prompt+revisión |

Lo que se copió de los productos grandes es la *forma*, no el peso: una **constitución** de 7
principios (786 caracteres, editable en `constitucion.md`) que va en el `system` de cada llamada,
en lugar de filtrar respuesta por respuesta a mano; la **autocorrección** por reglas antes de
hablar; y la **iniciativa**: CORT abre la boca primero una vez al conectar, con un pendiente que
vence, la RAM leída en `/proc` o el nivel del escáner S1 —con enfriamiento de 30 min / 1 h / 6 h
para no ser pesado.

**Medido en arena** (`CORT_HOME=/tmp/…`, Ollama simulada que registra lo que le llega):

| Qué | Número | De dónde sale |
|---|---|---|
| Coste del ciclo completo | **1,56–3,21 ms por frase** (2,16 en la corrida de esta noche) | `selftest` |
| Compruebas | **23/23** en `prueba_memoria.py` + **16/16** en el selftest | salida de la suite |
| Constitución que viaja en el `system` | **1207 caracteres** de prompt de sistema | la falsa Ollama imprime lo que recibió |
| Tope del prompt de memoria | **420 caracteres**, y el `system` completo **1400** recortando líneas enteras | `LIMITE_CONTEXTO`, `sistema()` |
| Ida y vuelta `memoria_estado` | **3–9 ms** con cliente crudo | cronometrado contra el puente |
| Tarjeta llena en el navegador | **113 ms** desde la orden | medido en la página |

**Lo que la suite obligó a confesar** (cuatro fallos reales, no de prueba):

1. `¿qué sabes de mí?` nunca funcionaba: la expresión estaba escrita con tilde y el texto de
   entrada llega **sin acentos** (los pliegue para que «memoria» y «memória» sean la misma
   palabra). Se reescribió sin tilde.
2. «borra la carpeta proyectos» se guardaba como preferencia. La guardia de verbos buscaba la
   raíz `borra` y el subjuntivo «borre» no la contiene; ahora la lista está **conjugada** (abre,
   abrir, abra, borre, cerre…) y una orden disfrazada de recuerdo se rechaza con su motivo.
3. Las pruebas de arena escribían en el `cort_state.json` **de casa**: el puente lo cargaba por
   ruta fija. Se añadió `CORT_STATE` y las tres suites lo usan. No era un detalle de test: era la
   puerta de RAM decidiendo con datos de otra sesión.
4. La tarjeta de memoria se abría vacía **7 segundos**. El empuje de iniciativa al conectar
   bloqueaba en el `await` del escáner S1 (1,3 s en frío medido) *antes* de entrar al bucle de
   lectura, así que la primera pregunta de la pantalla se contestaba cuando el puente se
   dignaba. Ahora va en `asyncio.create_task(empujar_iniciativa(ws))` y la suite lo comprueba.

**Honestidad antes de hablar** (`revisar()`): si el modelo responde en markdown, se convierte a
texto plano; si promete en pasado algo que la reja no ejecutó o que no tiene prueba del sistema,
se sustituye por *«No puedo afirmar que lo hice: no hay prueba del sistema.»* y se empuja
`autocritica` a la pantalla con los ajustes aplicados. Medido: el caso «ya cerré la ventana» con
`origen: "modelo"` sale corregido y sin `**`.

**En la interfaz**, la tarjeta `memoria` vive debajo de `mirada` dentro del panel del cerebro:
**389×195 px en 525×521** (x=57, y=250, dentro del panel de 430×323). Tiene tres estados y no
dos: *«consultando tu archivo…»* mientras la orden va por el cable, *«el puente no pudo
medirla»* con el motivo si `origen` no es `real`, y el recuento con plurales correctos
(`1 apunte · 1 corrección · 1 preferencia`). Debajo, la frase literal que CORT le mandaría al
modelo —«lo que sabe de ti: …»— y el camino entero del archivo: un «tengo 3 cosas de ti» sin
dirección es una promesa sin prueba.

**Lo que NO hace esta fase, dicho con todas sus letras:** no entrena pesos, no usa
*embeddings* (la recuperación es por palabra clave, porque una red semántica no cabe en 2
núcleos), no habla sola por el altavoz —eso es F3/F10— y no destila de modelos de la nube. Lo
segundo sí es posible y está pendiente: guardar los ejemplos buenos que da un modelo grande y
recitarlos como banco local, que es la única forma honesta de «aprender de otros modelos» en
esta máquina.


### S5 — ¿y si partes de CORT fueran en C? La respuesta medida, no opinada (`bash mediciones/s5-medida.sh`)

La pregunta de la fase es legítima y se contestó escribiendo el programa, compilándolo y
cronometrándolo en esta máquina. `mediciones/s5-ventanas.c` (34 líneas) es un ayudante de X11
que **sólo lee** `_NET_CLIENT_LIST` y los títulos —no mueve ni activa ventanas, por eso pudo
correrse en el equipo real sin arena.

| Qué | Número | Cómo se midió |
|---|---|---|
| Cadena de toolchain | **gcc 14.2.0**, `g++`, `rustc 1.98.1` y `cargo` presentes; `Xlib.h` sí y **`pkg-config` de x11 no** (se enlaza `-lX11` a mano); **`javac` ausente** | `gcc --version`, `ls /usr/include/X11/Xlib.h`, `which cargo javac` |
| Compilar el ayudante | **826 ms** (3,0 s en la primera corrida, con el disco frío) | `date +%s%N` alrededor de gcc |
| Tamaño del binario | **16 320 bytes** | `stat -c%s` |
| Memoria del proceso hijo | **~11 MB** de RSS, igual en C, en `wmctrl` y en `xdotool` | `ru_maxrss` de `RUSAGE_CHILDREN` |
| Coste por orden, desde el puente **ya en marcha** | ayudante C **13,6–15,3 ms** · `xdotool getactivewindow` **12,9–17,5 ms** · `wmctrl -l` **21,8–27,4 ms** | mediana de 5–7 corridas |
| Intérprete Python frío | **75,9–76,8 ms** (esto lo paga un script suelto, no el puente) | `python -c pass` |
| `estado_pc()` completo | **452 ms** repartidos así: apps 380 ms · ventanas 256 ms · volumen 252 ms · brillo 3 ms (solapados en la misma llamada) | cronometrado función por función |

**Lo que dicen los números.** Un ayudante en C le gana a `wmctrl` unos **8–12 ms por orden**.
Una orden de ventana que la usuaria dice en voz alta cuesta del orden de **cientos de
milisegundos** en el puente (leer la frase, validar, ejecutar, verificar), así que el C
mejoraría ese trayecto en un **poco más del 2 %**. No es un cambio de producto: es una
reescritura con su propio costo de mantenimiento, y en esta máquina cada línea extra de C es
una línea que no cubre ninguna de las 23+16 compruebas de la suite.

**Dónde sí pagaría C, y ya lo tenemos.** El bucle que sí corre por cuadro es la mirada:
**1,9–4,6 ms por cuadro** medidos en S2 —y ese trabajo lo hace numpy, que *es* C debajo. El
reconocimiento de voz (F3/F10) corre sobre Vosk, que también es C++. Es decir: CORT ya está
sentado sobre C; lo que no hace falta es escribir C propio para saltar por encima de él.

**Decisión de la fase:** **no entra C/C++ ni Rust en este release.** Se guarda la sonda
(`mediciones/s5-medida.sh`) para que la decisión se pueda volver a medir en cualquier equipo
—en una máquina con GPU y 32 GB la respuesta puede ser otra, y ahí el escáner S1 ya dirá el
nivel—. Y aquí va la corrección de un bulto que iba a escribir en esta misma página: se iba a
afirmar «Rust no está instalado». **Sí está** —`rustc 1.98.1`, `cargo 1.98.1` en
`~/.cargo/bin`, y `g++` también—, así que se midió en vez de suponerlo:

| Lenguaje | Compilar un programa de 2–34 líneas | Binario | Coste por corrida | Veredicto |
|---|---|---|---|---|
| C (`gcc -O2`, X11) | **826 ms** | **16 KB** | **13,6–15,3 ms** por orden de ventana | gana 8–12 ms a `wmctrl`; no justifica reescribir |
| Rust (`rustc -O`) | **33,5 s** | **4,5 MB** | **11,7 ms** en la suma de 200 000 enteros, contra **96,0 ms** de Python | 8 veces más rápido que Python *en ese bucle*, pero 33 s de compilación por cada cambio en una máquina de 2 núcleos |
| Python (lo que hay) | 0 ms (interpretado) | — | 96,0 ms en el mismo bucle | sigue siendo el idioma del puente: se cambia y corre al instante |
| Java/Kotlin | `javac` **ausente** en este equipo | — | — | sólo en el **APK** (F7/F12), que se compila en GitHub Actions, no aquí |

Lo que cada uno pediría para entrar: C, un bucle que corra **por cuadro** y no por orden (y el
único que hay hoy —la mirada— ya lo hace numpy, que es C debajo); Rust, una prueba de que el
ahorro de 84 ms en un bucle suelto cambia algo que la usuaria note, más un plan para pagar 33 s
de compilación por cada cambio en esta laptop. Ninguna de las dos está en el horizonte de las
próximas fases, y eso es lo que se deja dicho con número.


**La medida que sí duele y queda anotada:** con el navegador del agente abierto (media de
carga **6,5** en 2 núcleos) la misma orden `pc_estado` contestó en **6 234 ms** por WebSocket,
contra **452 ms** con la máquina quieta. El idioma no es el problema: es la saturación. Eso
refuerza la regla de la casa —no medir con el agente corriendo— y apunta a la optimización
correcta (cachear `apps_disponibles`, que es lo más caro de la lista), no a reescribir en C.


### Lo que se deja dicho, con número, de las dos peticiones que no entran esta noche
- **Sensores de cámara para mover ventanas del sistema**: la sonda de esta mañana corrigió el
  pronóstico. La webcam **sí da cuadros** en este equipo: 10/10 cuadros recibidos a 320×240 RGB,
  a 640×480 MJPG y a 320×240 YUY2 (a 160×120 no da ninguno: ese formato no lo trae). Lo que no
  hay es ffmpeg ni OpenCV en el entorno, y un modelo de visión no cabe en 1851 MB. El camino
  medido es un detector propio sobre numpy (piel y movimiento), no MediaPipe; se construye como
  fase S2 con los cuadros sin guardar nunca en disco. **(Hecho: ver S2 arriba.)**
- **Vincular PC ↔ Android para que CORT aprenda de ti**: el puente ya puede hablar con el
  teléfono (`CORT_BIND` + TLS + token), pero sin HTTPS el navegador del A16 no instala la PWA
  ni deja usar el micrófono, y el APK (F11/F12) es el que lo resuelve de verdad. La memoria
  compartida entre dispositivos se escribe cifrada en el repo local de cada equipo; sin APK,
  compartir memoria significaría exponerla en la red local.
