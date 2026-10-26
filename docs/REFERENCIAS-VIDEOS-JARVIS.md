# Los tres videos del 26/10 — leídos, no adivinados

26 oct 2026 · ronda 2.15.0 · fuente de `docs/PLAN-FASE-2-JARVIS.md`

La dueña mandó tres MP4 por WhatsApp y describió con qué los quiere:

| archivo (en `~/Escritorio/Referencias IA CORT/`) | qué dice ella que es | lo que resultó ser |
|---|---|---|
| `VID-20261024-WA0034.mp4` (30 MB, ~4:15) | «el primero: estilo, lógica, modelos, cómo funcionará en PC y en Android» | la **cara** de un JARVIS ajeno: chat en el teléfono, desplegable de modelos en el PC y una ventana de agente con botones aceptar/rechazar |
| `a074ef6a5fb08f4108de2d3934cd9d9e.mp4` (9,8 MB, ~0:43) | «el segundo: lógica, cerebro, automatización y pasos para crear un JARVIS» | un reel hablado en español con **siete pasos** numerados, transcritos abajo palabra por palabra |
| `Hay un jefe que ya no puede ignorar a su asistente…mp4` (4,7 MB, ~0:53) | «el tercero: cómo hablará, será inteligente, sin límites; luego múltiples voces en sus ajustes» | una **demo de llamada saliente**: el asistente llama al jefe por teléfono cuando el asunto es urgente |

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

## 5 · Qué se llevó cada video al plan

- Video 1 → **Superficie A** (la charla de conversación, ya montada en el paso 1.4) y
  el **desplegable de modelos** (ya calcado) y **Superficie B** con su fila de botones
  aceptar/rechazar.
- Video 2 → el esqueleto de la fase nueva, paso por paso, con lo hecho / lo a medias /
  lo que no existe.
- Video 3 → la **boca y el teléfono**: voces en ajustes, y la llamada saliente con su
  regla de urgencia, dentro del límite que ya documenta `Telefono.java`.

Todo eso está desarrollado en `docs/PLAN-FASE-2-JARVIS.md`.
