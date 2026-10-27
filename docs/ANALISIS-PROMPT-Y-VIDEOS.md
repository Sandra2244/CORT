# Su prompt contra su código — qué prometió CORT y qué tiene hoy

27 oct 2026 · comprobado sobre el commit `c844b9f` de `v0.2-demo` · con la rama limpia de
la dueña en frente (`CortNative.java`, `Flotante.java`, `MainActivity.java`, `brain.py`,
`pool.py`, `reproductor.py`, `actions.py`, `main.py`, `musica.py`, `rutas.py`, `README.md`
y sus docs están **sin commitear en sus manos**; nada de eso se tocó ni se versionó aquí).

## 0 · De dónde sale cada palabra de este documento

Dos fuentes, y ninguna de las dos se leyó «por encima»:

- **Su prompt**, `~/Escritorio/Promp CORT Idea y Desarrollo`, leído entero. Ahí están las
  promesas, y este documento las toma **una por una**.
- **Los videos**, que ya están medidos fotograma a fotograma y transcritos en
  `docs/REFERENCIAS-VIDEOS-JARVIS.md`. Aquí **no se volvieron a extraer cuadros**: ese
  trabajo está hecho, con sus medidas de diámetro, sus colores muestreados y su tempo de
  0,5 / 2,0 / 4,0 / 1,5 s (§5 de aquel documento), y duplicarlo sería otro archivo
  contando lo mismo con otras palabras. Lo que se hace abajo es cruzar lo que **ella
  pidió por escrito** con lo que **hoy responde si le grepas**.

Regla del casa: una promesa sólo se marca `HECHO` si tiene archivo y función donde
vivir. Si no la encuentro, se escribe **no existe**, aunque suene feo. Ninguna fila de
abajo está redactada para quedar bien.

## 1 · Las promesas de su prompt, una por una

| # | lo que ella escribió | estado | dónde vive hoy | qué falta de verdad |
|---|---|---|---|---|
| 1 | «usar una IA para crear otra IA… instalar un cerebro en tu PC», todo local | **HECHO** | `backend/app/brain.py` con su escalera Ollama → Groq → Gemini → diccionario; `10 · Modelos` y `/api/models` | nada; y el modelo se cambia en caliente |
| 2 | «agregarle una memoria `memory.py` que se sincronice con `main.py`… recuerde que me llamo Askher Vargas» | **HECHO** | `backend/app/memory.py`, `/api/memories` y `/api/profile` (`main.py:189-195` y `main.py:266-297`), `Recuerdos.java` en el teléfono | que la cara nueva tenga su hoja tan visible como el muro viejo |
| 3 | «carpeta de conocimiento y `knowledge.py` para que CORT lea mis documentos» | **PARCIAL — y el nombre no existe** | `sensors.leer_texto` + `/api/lee` (`main.py:246`), con candado: sólo Documentos/Escritorio/Descargas/Imágenes/Música/Videos y `../` bloqueado, tope 20 000 caracteres | **no hay corpus ni índice**: hoy CORT lee un archivo *cuando se lo nombras*, no sabe qué hay en su carpeta. Y PDF/docx no los lee (`actions.py:665-667` lo dice tal cual) |
| 4 | «reconociendo la palabra CORT o Sofi se activa y escucha, sin responder por chat» | **NO EXISTE como palabra de activación** | hay voz (`Reconocimiento.java`, `voz.py`) y hay burbuja flotante, pero **no hay punto de escucha permanente ni detector de palabra** | es el hueco más citado de su prompt y el más difícil: escuchar 24 h en 2 núcleos no cabe; hay que decidir cuándo se escucha |
| 5 | «se prende al iniciar la PC mediante un archivo .VBS copiado a la carpeta de inicio» | **NO EXISTE** | `scripts/instalar-linux.sh:81` crea un `.desktop` en el **Escritorio** (doble clic), `scripts/run.bat` en Windows | el acceso directo y su copia a `StartUp`/`~/.config/autostart`; y en Android eso es `RECEIVE_BOOT_COMPLETED`, que **no se declara** sin su permiso (`Alarma.java:28-30` lo dice) |
| 6 | «reproduce, playlist ordenada, pausar, reanudar, adelantar 5 o 10 segundos» | **HECHO en PC, con su boletín honesto** | `backend/app/reproductor.py` (suyo, sin commitear) + `/api/reproductor/orden`, `/api/music`, `/api/music/lista`; en Java, `Musica.java` | sólo el detalle de si el reproductor de turno admite `seek`: `reproductor.py:444-446` se niega y lo dice en vez de fingir |
| 7 | «CORT busca… en Google primero, y si es un archivo en el dispositivo» | **HECHO en sus dos mitades** | en PC, patrones de `actions.py` + `/api/files` y `/api/tree`; en el teléfono, `Acciones.java` abre la búsqueda | nada estructural; el buscador de la cara nueva ya enlaza `/api/music` y el árbol |
| 8 | «abre aplicaciones, archivos, COD Mobile, la calculadora, el reloj» | **HECHO** | `/api/launch`, `/api/open`, `Acciones.java` (su diccionario de paquetes incluye WhatsApp) | nada |
| 9 | «alarma a las 6:30 con el mensaje leído «Buenos días», y hoy te toca MORFO 3 / el ciclo de la Urea» | **MEDIA — y muy buena la mitad** | `Alarma.java` pone la alarma **ella misma** con `AlarmManager`, con canción, nota y rutina; `Agenda.java` lee `CalendarContract.Instances` | que la **nota de la alarma salga del calendario**: hoy son dos máquinas separadas. Falta el puente «mañana 8:00 MORFO 3 → alarma con esa materia» |
| 10 | «escaneos de sistema, nos dice cuándo el procesador o la RAM están elevadas, **en todo momento**» | **HECHO a demanda, NO en continuo** | `local_commands.py:30-32` (`psutil` cpu/ram/disco), `optimize.py` (mira y vacía cachés sin permisos), el freno `freno-ram` de la cara | no hay vigilancia con umbral ni aviso espontáneo; eso necesita el punto 12 |
| 11 | «automatización» (reglas, sus «automatizaciones», las habilidades del video 2 paso 6) | **HECHO con su límite escrito** | `ui/js/automatiza.js` — módulo puro, motor de reglas «cuando X, entonces Y» y `marcapasos` cada 30 s (`:248`) | **las reglas sólo se evalúan mientras la cara está en pantalla** (`automatiza.js:21-26`); con el WebView cerrado no hay quien las piense |
| 12 | «son las 12, a las 3 de la tarde mandas un mensaje a mi hermano JOAO» (tarea **diferida**) | **NO EXISTE** | nada. No hay planificador en el repo: ni APScheduler, ni `asyncio.call_later` de dominio, ni cola de tareas persistida. Las frases de «temporizador» (`habilidades.py:215`) son cuenta atrás en el teléfono, no «haz X a las Y» | **es el hueco más grande de su prompt**: hace falta una tabla de tareas con su hora, un ejecutor que viva sin pantalla y una hoja donde ver lo programado |
| 13 | «escribir usando mi teclado en mi PC o móvil para dejar mensajes» | **NO EXISTE** | en Android, `Avisos.java:26` dice por escrito que WhatsApp **no publica API** para leer ni escribir sus chats | se puede **dejar el mensaje redactado y abrir el chat con el texto puesto** (`ACTION_SENDTO` con `sms:`/`whatsapp:`), pero **enviarlo ella, un toque**. Es el límite honesto y no se cruza fingiendo un envío |
| 14 | «ponerla en un HOST, 24/7» | **NO, y ella ya lo sabe** | `docs/ALOJAR-CORT.md` (suyo, sin commitear) está en eso | recursos; es su decisión de cuando el planificador exista |
| 15 | «conectarlo con varios dispositivos» | **HECHO en la forma que cabe** | la cara viaja dentro del APK y el teléfono apunta a la IP del PC; `/api/port` | no hay descubrimiento automático (ni mDNS ni QR); se pone la dirección a mano |
| 16 | «publicarlo en GitHub bajo Sandra2244/CORT» | **HECHO** | el repo es ése, con `build.yml` y sus suites | que la README (suya, sin commitear) hable del rediseño |
| 17 | «Discord funcionando… no tengo, analízalo del video» | **NO Y NO HACE FALTA** | sólo se nombra en `habilidades.py` y en `referencia-openjarvis.md` | nada: sin cuenta no hay bot, y el video lo que enseña es un conector más |
| 18 | «Asyncio, Tkinter, darle su hilo aparte y privado» | **UNO SÍ, OTRO NO** | Asyncio: todo el núcleo es FastAPI/uvicorn. Tkinter: **no se usa** — el escritorio es Electron (`desktop/main.cjs`) | cambiar de idea a estas alturas sería tirar la cara hecha; el hilo privado del copiloto ya existe en la cara (J2.3) |

## 2 · Los tres huecos que de verdad separan CORT de un JARVIS

Todo lo demás es pulido. Estos tres son estructura:

**2.1 · Que CORT actúe cuando ella no está mirando.** Es la promesa 12 y el paso 7 del
video 2 («ponlo a trabajar solo»), y es el mismo faltante que limita las automatizaciones
existentes (`automatiza.js:21-26`) y el escaneo continuo (10). Lo que hace falta no es un
`setInterval`: es una **tabla de tareas persistida** (`tareas` con su hora, su acción, su
estado y su prueba de que se cumplió), un ejecutor dentro del proceso del núcleo —que ya
existe y ya es async— y una hoja en la cara donde se vea lo programado y se pueda
cancelar. En el teléfono hay una segunda mitad distinta y ya probada: `Alarma.java` usa
`AlarmManager` real, pero **no sobrevive a apagar el equipo** porque no se declara
`RECEIVE_BOOT_COMPLETED` (decisión de la casa: no se añaden permisos sin que ella lo pida).

**2.2 · Que sepa qué hay en sus carpetas sin que se lo digas.** Promesa 3. Hoy `/api/lee`
es un lector con candado, no un conocimiento. El paso honesto es pequeño: un índice de la
carpeta de conocimiento (ruta, título, tamaño, fecha) refrescado al arrancar, y que la
charla pueda decir «leí tres notas sobre el ciclo de la urea, ¿cuál abro?» en vez de
esperar la ruta exacta. **Sin parser de PDF ni embeddings**: con 1,8 GiB el índice de
texto plano es lo que cabe, y el resto se sigue declarando con la honestidad de
`actions.py:665-667`.

**2.3 · Que te llame o te escriba ella a ti.** Promesa 13 y el video 3 (la llamada
saliente). La marca ya existe (`Telefono.java`, sin permiso nuevo: deja el marcador
escrito), lo que falta es la **regla de urgencia guardada** y el disparador del 2.1. Escribir
en WhatsApp tiene su techo legal y técnico por escrito en `Avisos.java:26`, y la forma
correcta de prometerlo es **dejar el mensaje compuesto y abrir el chat**, no fingir un
envío.

## 3 · Lo que no se le promete, y por qué se lo dice en la cara

- **Contestar llamadas o hablar por WhatsApp sin ella.** Exigiría ser la app de teléfono
  predeterminada (`ROLE_CALLING` + `InCallService`); `Telefono.java` lo documenta como
  límite y no se cruza.
- **Oído permanente con palabra de activación.** Escuchar sin parar es un hilo de Vosk
  vivo, y en este equipo hay que elegir: o CORT piensa, o escucha. La decisión que cabe
  es *ventanas* de escucha (la burbuja presionada, el auricular, los primeros segundos al
  encender), no un micrófono abierto.
- **24/7 sin servidor.** Un host ajeno significa sacar a la nube su memoria y sus rutas;
  el límite de `AGENTS.md` sigue en pie: nada privado sale sin pedirlo.
- **Discord** sin su cuenta. **Aprender de cada usuario** publicado: eso requiere que el
  aprendizaje local se exporte, y hoy el perfil es local y exportable a mano.
- **Tkinter**: el escritorio ya es Electron y la cara ya viaja en el APK.

## 4 · Lo que necesita su decisión antes de programar

| cosa | por qué está bloqueada |
|---|---|
| el planificador del 2.1 | vive en `main.py` y `actions.py`, **sus dos archivos sin commitear**. Puedo escribirlo, pero no versionar encima de su trabajo sin que ella decida |
| las alarmas con materia del calendario | mitad Java (`Alarma.java`/`Agenda.java`), mitad suya y sin commit |
| escuchar sin tocar | mitad `Flotante.java`, que está en sus manos con la burbuja T1 |
| el escaneo continuo con umbral | es CPU; necesita que ella diga qué umbral y qué hace CORT al pasarse (aviso, optimizar, callarse) |
| la carpeta de conocimiento | ¿qué ruta es? hoy el candado de `sensors.py:15-25` abre seis raíces (Documentos, Escritorio, Descargas, Imágenes, Música, Videos, cada una con su alias en inglés); falta la suya concreta |

## 5 · Cómo queda la fase después de hoy

Cerrado y **commiteado** en esta sesión, cada cosa con su módulo puro, su suite enganchada
a `.github/workflows/build.yml` y sus mutaciones probadas:

- `a3e980b` **J2.1** — la superficie A distingue hablar de ejecutar, y el chip de «qué
  hizo» sólo pinta lo que el núcleo devolvió en `done`.
- `8c1e728` + `abfe528` **paso 1.3** — la placa de arriba; y la mentira que delató la
  vista previa (el modelo *elegido* no es el que *habló*) corregida.
- `c844b9f` **J2.3** — `ui/js/pasos.js`, la máquina de estados del hilo del copiloto
  (pendiente → corriendo → ok / falló / rechazado / enseñado) con su botón rojo terminal,
  34 comprobaciones y su paso en `build.yml`.

Las tres comprobadas **en vivo** contra el núcleo en `:8000` desde el navegador de Qoder,
sin encender Ollama y sin abrir un segundo navegador.

Los huecos de este documento son la siguiente fase. El plan de `docs/PLAN-FASE-2-JARVIS.md`
(suyo, sin commitear) no los nombra todavía, y ahí es donde hay que escribirlos: **J3 ·
que CORT trabaje sola** (2.1), **J4 · lo que sabe de sus carpetas** (2.2), **J5 · la boca
y el disparador** (2.3).
