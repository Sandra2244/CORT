# Los videos de referencia — leídos, no adivinados

26 oct 2026 · ronda 2.15.0, ampliado en 2.17.0 · fuente de `docs/PLAN-FASE-2-JARVIS.md`

La dueña mandó cuatro MP4 por WhatsApp y describió con qué los quiere:

| archivo (en `~/Escritorio/Referencias IA CORT/`) | qué dice ella que es | lo que resultó ser |
|---|---|---|
| `VID-20261024-WA0034.mp4` (30 MB, ~4:15) | «el primero: estilo, lógica, modelos, cómo funcionará en PC y en Android» | la **cara** de un JARVIS ajeno: chat en el teléfono, desplegable de modelos en el PC y una ventana de agente con botones aceptar/rechazar |
| `a074ef6a5fb08f4108de2d3934cd9d9e.mp4` (9,8 MB, ~0:43) | «el segundo: lógica, cerebro, automatización y pasos para crear un JARVIS» | un reel hablado en español con **siete pasos** numerados, transcritos abajo palabra por palabra |
| `Hay un jefe que ya no puede ignorar a su asistente…mp4` (4,7 MB, ~0:53) | «el tercero: cómo hablará, será inteligente, sin límites; luego múltiples voces en sus ajustes» | una **demo de llamada saliente**: el asistente llama al jefe por teléfono cuando el asunto es urgente |
| `f7d16b9e47ae45c813969bed77fedcf3.mp4` (30 MB, 3:07, 480×853 de 4K vertical) | «el segundo, la **animación dispersiva**: cuando responde o ejecuta forma ese vórtice, hazlo igual que en el video» | un TikTok en francés de **@technclair** («JARVIS v3.0», marca de agua `www.technclair.fr`): mitad **coreografía del orbe** (sección 5) y mitad **instalador con perfil del usuario** |

**Cuidado con los números:** ella llama «el segundo» a `f7d16b9e…` por el orden en que
lo envió en este último mensaje, y este documento llama «video 2» a `a074ef6a…` por el
orden del mensaje anterior. Son archivos distintos. Para no discutir en números, abajo
cada uno se nombra por las primeras ocho letras de su archivo.

Nada de lo que sigue está recordado de ver el video una vez: cada afirmación tiene su
fotograma guardado en el repo o su transcripción, y más abajo está la orden exacta que
lo produjo.

---

## 1 · Cómo se leyeron en este portátil (y por qué así)

El equipo de la dueña no tiene `ffmpeg` ni `ffprobe` ni `cv2`, y su Chromium no
decodifica HEVC. Lo que sí hay es VLC y su propio modelo de Vosk en español. Éstas son
las tres herramientas, en el orden en que hicieron falta:

**Ver la pantalla (H.264) — el arnés del navegador.** `ui/sonda-*` ya se usaba así: una
página con `<video>` y un `<canvas>`, y funciones para saltar a un segundo y recortar un
zoom. Con esto se midieron los fotogramas del video 1 (los del teléfono y los del PC).

**Ver la pantalla (HEVC) — VLC con filtro de escena**, un JPG cada 30 fotogramas:

```bash
cvlc -I dummy "VID-20261024-WA0034.mp4" --start-time=150 --stop-time=215 --no-audio \
     --video-filter=scene --scene-format=jpg --scene-ratio=30 --scene-width=900 \
     --scene-path=/tmp/frames/ vlc://quit
```

(En este build `--scene-quality` no existe; con él VLC se cae. Y `--start-time` sí
funciona, que es lo que permite ir a un minuto concreto sin pasar el video entero.)

**Oír el audio — VLC a WAV + Vosk.** El truco que costó encontrar: `mux=raw` suelta PCM
sin cabecera y `wave.open` lo rechaza; hay que pedir `mux=wav`:

```bash
cvlc -I dummy "a074ef6a5fb08f4108de2d3934cd9d9e.mp4" --no-audio \
     --sout '#transcode{acodec=s16l,channels=1,samplerate=16000}:std{access=file,mux=wav,dst=/tmp/v2.wav}' \
     vlc://quit
/tmp/stt/bin/python /tmp/stt.py /tmp/v2.wav      # vosk-model-small-es-0.42, sin red
```

El venv de `/tmp/stt` es desechable y el modelo es el zip que CORT ya usa para oír; no
se instaló nada nuevo en el equipo ni se mandó audio a ningún sitio.

**Lo que NO salió:** el video 1 no tiene narración en español. Transcrito con Vosk, su
pista de audio da cuatro minutos de música de fondo y basura («yo quiera paga y tabla
utilizando la petit…»). Eso es un resultado, no un fallo de la prueba: **todo lo que el
video 1 dice, lo dice en la pantalla**, y por eso abajo se describe con fotogramas.

---

## 2 · Video 1 — la cara que ella quiere copiar

### 2.1 El chat en el teléfono (`docs/referencias/v1-charla-096.jpg`, minuto 1:36)

De arriba abajo, medido sobre el fotograma:

1. **Nombre a la izquierda, en blanco y grueso** («Jarvis»), sin caja ni barra detrás.
2. **A la derecha del nombre, el estado**: la palabra «connecté» y un **punto verde** a
   su lado. No es adorno: es el aparato diciendo si está vivo, y cuando no lo está el
   video enseña otra cosa.
3. **Dos iconos redondos sueltos** en la esquina (recargar y un ajuste/cámara). Sin
   menú, sin texto: dos botones circulares.
4. **Nada de cabecera fija ni tarjetas**: el fondo —una malla de puntos que se mueve, el
   equivalente a nuestro orbe— ocupa toda la pantalla y el chat va **encima**.
5. **Lo tuyo, una pastilla de color** (coral en su caso porque ese es SU traje) con las
   esquinas muy redondeadas, texto centrado y sombra.
6. **Lo de él, texto suelto**: sin caja, sin avatar, sin nombre repetido, alineado a la
   izquierda y con una sombra negra para leerse sobre el fondo animado. Debajo de la
   pastilla del usuario, no en columna aparte.
7. **Abajo, dos botones**: una pastilla «STOP» y un micrófono redondo. Nada más. No hay
   campo de texto visible en ese plano (está en el gesto de la mano, fuera de cuadro).

Esto es exactamente lo que montó el paso 1.4 (`ui/css/jarvis.css`): el orbe detrás, la
pastilla de acento para lo tuyo, texto pelado para lo de CORT, nombre + estado de verdad
arriba, y «parar» sólo mientras se espera. Lo que **no** se copió: el coral. En CORT el
acento lo manda `Paleta.java`, así que su chat puede ser cian, lima o rosa según el
atuendo, y `scripts/prueba-manto.mjs` [3] no deja escribir un color de traje a mano.

### 2.2 El desplegable de modelos en el PC (`v1-modelos-186.jpg` y `v1-pc-165.jpg`)

Ventana de escritorio (con minimizar/maximizar/cerrar, Windows en francés) y un
**`Modèle :`** con su flecha, que al abrirse suelta una lista de una línea por modelo:

`Gemini 3.5 Flash · Gemini 3.1 Pro · Gemini 2.5 Flash · Gemini 2.5 Pro · Claude 5
Sonnet · Claude 5 Fable · Claude 4.8 Opus · Grok 4.5 · Grok 4.20 · Mistral Large ·
Codeltral · Omith-1.0 (Local) · Omith-35b (Local) · Qwen2.5-Coder (Local) ·
DeepSeek-Coder (Local)`

Las tres cosas que hay que leerle bien: **nube y local en la misma lista**, los locales
marcados con la palabra `(Local)` detrás del nombre, y el elegido resaltado en el botón
de arriba. No hay tarjetas, ni párrafos, ni pestañas. Ésta es la pantalla que ya está
calcada en 10 · Modelos (ver `docs/PLAN-FASE-1.md` §4.5); el video 1 la confirma en su
versión de escritorio.

En `v1-pc-165.jpg` (minuto 2:45) se ve el PC con **una ventana de código/terminal a la
izquierda** —texto en verde agua, línea por línea, como un registro— **y el orbe a la
derecha**, con sus dos botones redondos debajo. Es decir: en el escritorio, la charla y
lo que se ejecuta viven **uno al lado de la otra**, no en pantallas separadas.

### 2.3 La ventana de agente y sus botones (`v1-agente-159.jpg`, minuto 2:39)

Al fondo de una ventana oscura tipo editor hay una fila de cuatro botones: uno gris
pequeño, uno **azul**, uno **rojo** y uno **verde**. Es el patrón de un agente que
propone cambios y espera: azul = seguir, rojo = rechazar, verde = aceptar. El video lo
enseña como parte del flujo, no como un detalle del editor.

Esto es lo que la dueña pidió como «el otro chat, con entorno de código, igual que
Qoder»: no un chat más bonito, sino **el hilo de pasos con el resultado de cada uno y
dos botones que mandan**. En CORT el motor ya existe (`/api/copiloto/plan` y
`/api/copiloto/ejecuta`); lo que falta es esa cara.

---

## 3 · Video 2 — los siete pasos, transcritos

Audio de 43 s, español, Vosk-small-es. Transcripción cruda (sin puntuación, que es como
sale del motor):

> «así pues armar tu propio y harbin en un fin de semana en sólo siete pasos uno dale
> una casa una computadora vieja o un servidor en la nube ahí va vivirás veinticuatro
> horas del día dos dale un cerebro que germina en el que quiera sido puedes cambiar sin
> tres instalarle un arder deja de ser son cerebro las manos para usar herramientas y
> memoria para recordar cosas cuatro de quién eres qué haces qué herramientas usas que
> suscripciones tienes todo cinco conectado a todo tu correo tu whatsapp tus documentos
> tu base de datos seis y habilidades para tus tareas repetitivas como cargar facturas o
> redactar documento y siete pueblo a trabajar solo deja de tareas programadas y las
> mientras tú de…»

Puesta en limpio, que es como se usó en el plan:

| paso | dice el video | ¿qué tiene CORT hoy? |
|---|---|---|
| 1 | **dale una casa**: un equipo viejo o un servidor, 24 h encendido | `scripts/telefono.sh` sirve la cara por Wi-Fi; `docs/ALOJAR-CORT.md` (suyo, sin commitear) está en eso. Falta: que CORT sobreviva sin el portátil delante |
| 2 | **dale un cerebro** que puedas cambiar | `backend/app/brain.py` + 10 · Modelos; el modelo se elige en caliente. **Hecho** |
| 3 | **dale un agente**: manos para usar herramientas y memoria para recordar | `/api/copiloto/*` (manos, sólo lectura), `/api/memories` y `/api/profile` (memoria). **Medio hecho**: las manos no pueden escribir |
| 4 | **dile quién eres**: qué haces, qué herramientas usas, qué suscripciones tienes | `/api/profile` + el muro de recuerdos. Falta: un archivo de «quién soy» editado desde la cara |
| 5 | **conéctalo a todo**: correo, WhatsApp, documentos, base de datos | en el teléfono: `Avisos.java` (oído de notificaciones), `Agenda.java` (correo = cuántos avisos de Gmail), `Acciones.java` (abre WhatsApp). En el PC: el sistema de archivos. **No hay** IMAP ni base de datos |
| 6 | **dale habilidades** para lo repetitivo (facturas, documentos) | `/api/organizar` (mover/archivar con plan y confirmación) es la única habilidad con forma. Falta el marco de «habilidades» |
| 7 | **ponlo a trabajar solo**: tareas programadas mientras tú duermes | **Nada.** Ni un planificador en el repo. Es el hueco más grande de los siete |

La promesa del video («un fin de semana») no se traslada: los pasos 5 y 7 son los que
valen dinero o tiempo de verdad, y aquí van a su fase, con su prueba.

---

## 4 · Video 3 — la llamada saliente

Transcripción (53 s):

> «tengo una mala noticia y una buena, cuál quieres primero. la mala noticia: ya tengo
> su número, así que ya no podrá dejar de contestarme. y ahora dime, ahora podemos estar
> mucho más comunicados, esté donde esté. excelente. ¿qué es lo primero que quiere que
> le avise por llamada? —cualquier tema urgente— entendido, le avisaré de inmediato ante
> cualquier emergencia de la oficina. gracias, a sus órdenes, que lo atento.»

Lo que se ve no es un chat: es una **conversación que termina en una llamada de
verdad**, y lo que se configura en ella es la *regla* («¿qué te aviso por llamada?»), no
el número.

En CORT esto está más cerca de lo que parece, y hay que decirlo con precisión:

- **Marcar ya existe.** `apps/apk/src/com/cort/ia/Telefono.java` busca el contacto y
  abre la llamada; con `CALL_PHONE` (declarado en `apps/apk/AndroidManifest.xml:183`) va
  directo, y sin él deja el marcador escrito a mano. No hace falta ningún permiso nuevo.
- **Contestar por ella, no.** El propio fichero lo dice en su cabecera: exigiría ser el
  teléfono predeterminado (`ROLE_CALLING` + `InCallService`), y a medias rompe el
  marcador normal. Ese es el límite honesto y no se cruza sin que ella lo pida.
- **El disparador** («avísame si es urgente») no tiene dónde vivir todavía: necesita el
  paso 7 del video 2 (tareas programadas) más una regla de urgencia guardada.
- **Las múltiples voces** que ella añadió encima ya tienen casi todo: `VozNueva.java`
  (contrato 2.1, `ajusteVoz` = lista/poner/predefinida/descargar/probar/estado) y
  `ui/js/telefono.js:653-730` lo manejan; en PC es `backend/app/voz.py` con las
  variantes de espeak (`VARIANTES`, línea 75). Lo que falta es **la sección en los
  ajustes de la cara nueva**, no la capacidad.

Un defecto encontrado al leer `voz.py` para este plan, y que hay que limpiar antes de
tocar voces: la función `_suena` está **definida dos veces** (líneas 126 y 161). Python
se queda con la segunda, que además borra el WAV en su `finally`. La primera es código
muerto. No se tocó en esta ronda porque no es del paso 1.4; entra con el paso de voces.

---

## 5 · Video `f7d16b9e…` — la animación dispersiva, medida fotograma a fotograma

Ella lo pidió con estas palabras: «del segundo copiarás la animación dispersiva, en la
que cuando responde CORT o ejecuta una respuesta forma esa clase de vórtice; **hazlo
igual que en el video**». Así que esto no es una impresión: son fases con su segundo, su
diodía en píxeles y su fotograma guardado en `docs/referencias/`.

### 5.1 Cómo se leyó

Son 3:07 de 4K vertical grabados a mano sobre un monitor curvo. El audio es **narración
en francés**, así que el Vosk en español de CORT no sirve aquí (da basura, ya lo probé
con el otro video); lo que dice el video está **quemado en los subtítulos**, y eso es lo
que se lee. La herramienta fue la misma VLC de siempre, dos ventanas densas de un
fotograma cada 0,5 s y una pasada de alta resolución:

```bash
cvlc -I dummy "f7d16b9e47ae45c813969bed77fedcf3.mp4" --start-time=0  --stop-time=14 \
     --no-audio --video-filter=scene --scene-format=jpg --scene-ratio=15 --scene-width=1000 \
     --scene-path=/tmp/f7-alta/ vlc://quit
cvlc -I dummy "…mismo…" --start-time=36 --stop-time=52 --scene-ratio=15 --scene-width=480 \
     --scene-path=/tmp/f7-zona-b/ vlc://quit
```

### 5.2 La coreografía, con su reloj

El video entero es **dos escenas** de la misma animación (0-14 s y 36-52 s) y luego el
instalador. Lo que le pasa al orbe, en orden:

| t | qué se ve | fotograma |
|---|---|---|
| 0,0-2,5 | **reposo**: plexus pequeño, ~1/3 de la altura de la pantalla, con núcleo brillante y radios cortos. Gira lento. | `f7-orbe-000.jpg` |
| 3,0 | **dispersión**: el núcleo estalla hacia fuera. Los puntos dejan de estar en la esfera y salen disparados en **estelas** (cada punto se ve como un rabo de 3-6 px, no como un punto), y en el centro queda un **agujero oscuro** con un aro blanco dentro. | `f7-dispersa-030.jpg` |
| 4,5 | **nace el anillo**: las estelas se ordenan en una **corona toroidal** inclinada, todavía con partículas sueltas alrededor. | `f7-anillo-045.jpg` |
| 5,5-6,5 | **anillo abierto**: el toro ya es estable, ocupa casi toda la pantalla y tiene **dos o tres puntos calientes** que recorren la corona (no está igual de brillante por todo el aro). | `f7-anillo-055.jpg`, `f7-anillo-065.jpg` |
| 7,5-9,0 | **el anillo enmarca la acción**: se abre una ventana de la aplicación **dentro del agujero** del toro; el anillo sigue girando arriba y abajo de la ventana mientras el asistente trabaja. Esto es lo que ella llama «cuando ejecuta una respuesta». | `f7-portal-075.jpg` |
| 10,5+ | se apaga: la pantalla pasa al navegador y el anillo **no** queda de fondo. Vuelve al reposo. | — |

Medido sobre el fotograma de 6,5 s (perfil de luminancia por una línea horizontal que
cruza el centro, umbral 150):

- **Diámetro exterior del anillo**: 215 px sobre una pantalla de 415 px visibles → el
  **52 % del ancho** de la pantalla y el **82 % de su alto visible** (la foto está
  tomada en picado, así que el alto real es aún mayor).
- **Agujero**: 145 px → el **0,68 del diámetro exterior**. El toro es **hueco de verdad**:
  dentro no hay puntos, y ésa es la razón por la que la ventana cabe dentro.
- **Grosor de la corona**: 20-24 px por lado, ≈ **16 % del diámetro exterior**. No es un
  aro fino: es una banda de partículas con sus estelas.
- **Forma**: casi circular en pantalla (215 × 206 px), con una inclinación suave; la
  elipse mide menos de un 5 % de achatamiento, así que el giro del toro es de pocos
  grados, no un corte seco.
- **Colores** (muestreados en el fotograma de 1000 px, núcleo → banda → halo → fondo):
  `#90EFFF` blanco-cian en el centro de las estelas, `#6AB9D8` / `#56A8CE` en la banda,
  `#1D4E76` en el halo exterior y `#373C59` el fondo casi negro azulado. **No hay rojo
  ni verde**: todo el vórtice es blanco sobre cian sobre azul.

Y las duraciones, que son lo que hay que copiar para que "se sienta igual":

| tramo | segundos |
|---|---|
| reposo → dispersión (la explosión) | ~0,5 |
| dispersión → anillo establecido | ~2,0 |
| anillo mantenido mientras ejecuta | ~4,0 |
| anillo → reposo | ~1,5 |

#### Y lo que devolvió el navegador cuando la animación ya estaba hecha

La coreografía está implementada en `ui/js/orbe-plexo.js` como **morph en la GPU**: tres
uniforms (`uDispersa`, `uVortice`, `uPortal`) que mueven los 220 puntos ya existentes. La
geometría no se toca ni un byte —es la regla 1 del archivo y hay una prueba que lo exige
comparando la suma de los vértices antes y después del baile.

Medido en `ui/sonda-orbe.html` (pestaña de 536 × 521 px, congelando el cuadro a los 5 s
con `pinta` parcheado, y leyendo los píxeles del lienzo con un `drawImage`):

| qué | el video | CORT, primera versión | CORT, corregida |
|---|---|---|---|
| caja proyectada del anillo | 215 × 206 px (relación **0,96**) | 272 × 315 (**1,16**: más alto que ancho) | 325 × 308 (**0,95**) |
| coste del orbe por frame | — | 0,20 ms en reposo | **0,25 ms** con el anillo montado |

El 0,96 del video sale de sus propias medidas de arriba (215 × 206); el 1,16 de la
primera versión era el fallo: **el anillo se veía de canto**, una raya verde cruzando la
pantalla, y no había agujero que leer. Costó dos correcciones y las dos están contadas en
el comentario de `INCLINA`:

1. La inclinación no puede aplicarse en el **espacio del objeto**, porque el orbe entero
   rota en Y respirando: el plano del anillo barría la cámara y a los pocos segundos
   volvía a ponerse de canto. Se aplica **después** de `modelViewMatrix`.
2. Y ese giro tiene que pivotar **sobre el centro del orbe**, no sobre el origen del
   espacio de cámara (que es la lente): pivotando en la lente, con el anillo a 7,2 de
   distancia, inclinar 70° mandaba el orbe 6,8 unidades hacia arriba y se salía de la
   pantalla. Eso dio la caja de 93 × 93 px en una esquina.

Lo otro que hubo que quitar del medio: **las 700 líneas del plexo**. Con el alfa de
siempre, la explosión y la corona se tapaban con una tela blanca y el agujero
desaparecía; en el video la dispersión son estelas de partículas, no una malla. Ahora el
fragmento de las líneas multiplica su alfa por `1 − 0,85 · máx(uDispersa, uPortal)`, o
sea que durante el morfeado quedan al 15 % y los puntos siguen a tope. Las cuerdas que
cruzan el agujero se quedan, y bien: en `f7-dispersa-030.jpg` el video también tiene su
polígono de hilos tendido por debajo.

**No se puede copiar del video, y no se ha copiado:** las estelas con rabo (movimiento
realmente borroso, que exige post-proceso y en 2 núcleos no se paga), el bloom óptico y
los ~10 000 puntos de su nube. Aquí son 220 puntos con `vCalor` aclarándolos hacia el
`#90EFFF` medido. Los fps de la pestaña automatizada (17-21) **no son comparables** con
los 60 fps medidos en la 2.12.0 en el navegador normal: la pestaña del prototipo de
captura va limitada por el propio lazo de screenshots.


### 5.3 Lo que el orbe viejo ya hacía, y lo que no se puede copiar de él

`ui/js/orb.js` **ya tiene** esta coreografía traducida, y no es casualidad: se hizo a
ojo con este mismo video. En `orb.js:336-342`, `activate()` lanza `shockwave()`,
`spinBoost = 6`, `vortexWant = 1`, `scatter = 1`; a los **1700 ms** suelta el vórtice y
enciende el portal (`poWant = 1`), y a los **3200 ms** lo apaga. Esos 1700/3200 caen
casi exactos sobre los ~2,0 s y ~4,0 s medidos arriba, así que el *tempo* viejo es
bueno y se conserva.

Lo que **no** se copia es el *cómo*: el orbe viejo mueve los vértices en la CPU cada
frame reescribiendo `position.array`, y eso es justo lo que el orbe nuevo
(`ui/js/orbe-plexo.js`) juró no hacer —su regla 1 dice «la geometría se calcula UNA VEZ
al nacer y no se toca más» (`orbe-plexo.js:14-16`). En el plexo nuevo el vórtice tiene
que ser una **mezcla en el vertex shader**: tres uniformes más, cero trabajo por frame
en el CPU. La forma de anillo ya está presupuestada: `RADIOS.anillo = 1.62`
(`orbe-plexo.js:46`) coincide con el 52 %/33 % medido.

### 5.4 La otra mitad del video: el instalador con perfil

Del minuto 0:50 al 3:00 el mismo video enseña `JARVIS_Setup_v1.exe` instalándose en
Windows, y **cada pantalla es un dato del perfil**. Traducidas del francés, en orden:

1. **Idioma** del asistente (`Français` en un desplegable) — `f7-perfil-056.jpg`.
2. **Perfil**: «estos datos permiten a JARVIS personalizar sus respuestas. **Todos los
   campos son opcionales, deja vacío para saltar**: tu edad, tu ciudad, tu profesión /
   oficio» — `f7-perfil-076.jpg`.
3. **Pasiones y preferencias**: aficiones (ej. tecnología, videojuegos, cocina) y a qué
   se dedica (ej. desarrollador, abogado) — fotograma de 1:26.
4. **Nombres de los hijos**, tipo de contrato, **la playlist de Spotify** y **el correo**
   que se usa para las automatizaciones.
5. **Claves de servicios web, todas opcionales y con la dirección donde se piden**:
   SerpAPI (`serpapi.com/manage-api-key`, búsqueda web), YouTube
   (`console.cloud.google.com` → *YouTube Data API v3*), Spotify (clic derecho en la
   playlist → compartir → copiar URI), Open-Meteo y un «API Flight Radar» —
   `f7-claves-101.jpg`.
6. **Home Assistant** con su URL y su token (fotograma de 1:45).
7. **La guía de comandos**: una consola negra con texto amarillo monoespaciado, por
   secciones —`[ Météo ] «¿qué tiempo hace? / previsiones / ¿va a llover? / temperatura
   exterior»`, `[ Sport ] «resultados Ligue 1 / Premier League / Liga / Bundesliga /
   clasificación / resultados en directo → Gemini + Google Search»`, `[ Google Workspace ]`
   —y un botón **«guardar la guía en el Escritorio»** — `f7-guia-126.jpg`.

Tres lecturas que importan más que la lista:

- **No hay cuenta, ni correo de registro, ni nube.** El perfil se guarda **en el
  propio PC**, en el instalador, y las claves las pone la persona. Esto es lo que
  responde de verdad a lo que ella pidió («autenticación con correo… y que al
  actualizar en PC se compare la misma información si es el mismo usuario»): sin
  servidor, la alternativa honesta es **un perfil local exportable**, no una cuenta
  falsa. Está desarrollado en la tarea pendiente de `docs/PLAN-FASE-2-JARVIS.md`.
- **La guía de comandos es la "automatización" del video**: no es un motor, es una
  lista imprimible de frases que el asistente ya sabe ejecutar. CORT tiene el motor
  (`/api/copiloto/*`) y le falta esa **lista a la vista**, que es justo lo que ella
  pidió al principio: «sus automatizaciones».
- El instalador **sí** pide datos personales (ciudad, hijos, correo). En CORT eso iría
  al muro de recuerdos local, y el límite de `AGENTS.md` sigue en pie: nada privado
  sale a la nube sin pedirlo.

---

## 6 · Qué se llevó cada video al plan

- Video 1 → **Superficie A** (la charla de conversación, ya montada en el paso 1.4) y
  el **desplegable de modelos** (ya calcado) y **Superficie B** con su fila de botones
  aceptar/rechazar.
- Video 2 (`a074ef6a…`) → el esqueleto de la fase nueva, paso por paso, con lo hecho /
  lo a medias / lo que no existe.
- Video 3 → la **boca y el teléfono**: voces en ajustes, y la llamada saliente con su
  regla de urgencia, dentro del límite que ya documenta `Telefono.java`.
- Video 4 (`f7d16b9e…`) → la **animación dispersiva** del orbe nuevo (tarea del paso
  1.1e: `uDispersa`/`uVortice`/`uPortal` en el vertex shader, con el tempo de 5.3) y el
  **perfil local con guía de comandos** como respuesta honesta a «cuenta y
  sincronización».

Todo eso está desarrollado en `docs/PLAN-FASE-2-JARVIS.md`.
