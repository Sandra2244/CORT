# Los dos episodios del tutorial — leídos cuadro a cuadro

27 oct 2026 · primera pasada · fuentes: `~/Escritorio/Referencias IA CORT/Como crear un
Asistente Virtual propio (J.A.R.V.I.S.) (Episodio 1)(480P).mp4` y `Cómo crear un asistente
Virtual Propio (J.A.R.V.I.S. casi muere a mitad de camino) _ (EPISODIO 2)(720P_HD).mp4`

**Cómo se leyeron, y qué se puede afirmar de esto.** Las duraciones están medidas sobre la
caja `mvhd` del MP4 con Python estándar, no calculadas a ojo: **episodio 1 = 682,7 s
(11 m 22 s)** y **episodio 2 = 452,1 s (7 m 32 s)**. Los cuadros se extrajeron con el filtro
de escena de VLC (`--scene-ratio=300 --scene-width=640`), o sea **un fotograma cada ~10
segundos**, y sobre esos cuadros se leyeron los **subtítulos quemados** y el código que se ve
en pantalla. Cada afirmación de abajo lleva su cuadro (`sceneNNNNN.jpg`) y su minuto
aproximado; lo que no tiene cuadro no está escrito.

Cuando se escribió este documento **la transcripción del audio con Vosk local seguía
corriendo** (el portátil es de dos núcleos y va con `nice -19` para no comerse la máquina de
la dueña). Así que esto es la mitad visual, completa y medida; la narración dirá si hay algún
paso dicho sólo en voz. Ese hueco se anota al final, sin rellenarlo por las buenas.

**No hay nada de esto en `docs/REFERENCIAS-VIDEOS-JARVIS.md`:** ese documento cubre los
cuatro videos que llegaron por WhatsApp (`VID-20261024-WA0034`, `a074ef6a…`, `f7d16b9e…` y el
de la llamada). Los dos episodios son otra fuente, y son **la que ella describió palabra por
palabra en su prompt**.

---

## 1 · Qué es cada episodio, dicho con precisión

| | episodio 1 | episodio 2 |
|---|---|---|
| título en pantalla | «Construyendo IA Local tipo Jarvis» (en la barra de la ventana de Gemini, `scene12601`) | el mismo proyecto, más tarde |
| sistema operativo | **Windows** (barra de tareas, «Activar Windows», rutas `C:\Users\…`) | el mismo |
| con quién programa | primero **ChatGPT** web (`chatgpt.com`, `scene07201`), luego **Gemini** (`gemini.google.com`, `scene09001` y `scene16201`) | Gemini |
| nombre del asistente del autor | **Viernes** — se lee en la propia conversación: «¿Qué bien que ya conteste, **Viernes**. Viendo tu…» (`scene16201`) | idem |
| interfaz | **Tkinter** (`class JarvisUI(tk.Tk)`, `scene12601`) y luego archivos `.hta` (`scene05701` del ep. 2) | idem |
| story | de cero a la cara: Ollama, `main.py`, el bug de la fecha, `memory.py`, `interfaz.py` | «casi muere a mitad de camino»: el cerebro dañado con Gemini, `weather.py`, los conectores (Discord, WhatsApp) y el HUD definitivo |

Esto es lo que ella resumió en su prompt como «el video tutorial de como crear un JARVIS
espisodio 1» y «Resumen video de como hacer un JARVIS capitulo 2». Cuadra: son los mismos
archivos, los mismos errores y la misma salida.

---

## 2 · Episodio 1, en el orden en que se ve

| t | cuadro | qué se ve (leído, no supuesto) |
|---|---|---|
| 0:00-1:00 | `scene00301` | clip de película (Iron Man / taller) con subtítulo «Y MÁS DE MARVEL». Es **su introducción**, la misma que ella copió en su prompt |
| 2:00 | `scene03601` | pantalla oscura desenfocada de **Ollama** con el subtítulo «ES SOLO LA BASE QUE MODIFICAREMOS» — literal contra su prompt: «este cerebro no es el producto final, es solo la base que modificaremos» |
| 4:00 | `scene07201` | ChatGPT web + VS Code con `main.py`. Banner del paso: **«PASO 5 — ABRIR TERMINAL EN ESA CARPETA»**. En el código se lee `import datetime`, `def hablar_tu_fecha_actual():`, `fecha_actual = datetime.datetime.now()`, `entrada = input(...)`, `if entrada.lower() == "salir": break`. En la terminal: `cd C:\Users\…\Documents\proy` y `python main.py`. Subtítulo: «PENSANDO QUE EL ÚLTIMO DÍA» |
| 5:00 | `scene09001` | Gemini con la imagen del PC viejo → PC gamer con luces rojas y subtítulo «LE MANDÉ LOS DOS CÓDIGOS ANTIGUOS Y ME…» — el autor le pasa a la IA lo que ya tenía escrito |
| 7:00 | `scene12601` | VS Code con **`memory.py`** y la interfaz abiertos. Se lee el `import`: `from memory import (load_long_memory, save_long_memory, get_memory_context, add_user_message, add_ai_message)`, `import threading`, `class JarvisUI(tk.Tk)` con `self.title("IA Local tipo Jarvis")`, `self.state("zoomed")`, `self.geometry("1024x768")`, `self.memory = load_long_memory()`, `self.chat_box = tk.Text(...)`, `self.input_box = tk.Entry(...)`, `self.send_btn = tk.Button(..., text="Enviar", command=self.send_message)`. En la terminal, `python interfaz.py`. Subtítulo: «Gemini es una IA y puede cometer errores» |
| 9:00 | `scene16201` | Gemini con una captura del HUD final y el texto: «…que la info está saliendo un poco "desactualizada"… son las 3:30 p. m. según tu reloj de Windows» y «Vamos a limpiar el cerebro de Viernes para que sea otra ultra precisa con el tiempo y **siempre esté lista en segundo plano**. Aquí tienes el código de `interfaz.py` **definitivo para que funcione desde la barra de tareas**» |
| 10:00 | `scene18001` | **El HUD que ella quiere**: anillo cian de círculos concéntricos con núcleo brillante, panel «VIERNES — SYSTEM LOG» con un informe de diagnóstico (estado operativo, subsistemas de visualización y reconocimiento de voz «en fase de calibración», advertencia `[23:14:46]`, aviso de que el análisis es un modelo y no una verificación humana), «SYSTEM METRICS» con **CPU 17 % · RAM 73 % · DISK 81 %** en barras, y «AI STATUS» con «IA INICTIVA / escucho…presion para activar». Pie: «VIERNES SYSTEM ONLINE · 12/11/2025» |

**Los tres aprendizajes del episodio 1**, en las palabras de ella y con su cuadro: (a) el
modelo cree que hoy es el último día de su entrenamiento → hay que sacarle la hora y la fecha
al aparato, no al cerebro (`scene07201` + `scene16201`); (b) la memoria es un archivo con sus
funciones de carga/guardado y contexto, no un truco del prompt (`scene12601`); (c) el asistente
vive **en segundo plano y en la barra de tareas** (`scene16201`).

---

## 3 · Episodio 2, en el orden en que se ve

| t | cuadro | qué se ve |
|---|---|---|
| 0:00 | `scene00001` | abre con el **Explorador de Windows** en `Este equipo > Documentos > mi_jar…` con **24 elementos**, y es la lista más informativa de los dos videos: carpetas `_pycache_`, `Chat Guardado`, **`conocimientos`**, `img`, y archivos **`knowledge.py`**, `memory.py`, `main.py`, `interfaz.py`, `interfaz_v2.py`, **`hud_v2_index.hta`**, **`INTERFAZ_PRINCIPAL.hta`**, `fundamentos.py`, `perfil_construccion.py`, `procesa_imagen.py`, `video.py`, **`discord_bot.py`**, **`whatsapp_bot.py`**, `integraciones_config.json`, `long_term_memory.json`, `requirements.txt`, `README.md`, `test.exe`, `prueba_llama.exe` |
| 1:30 | `scene02701` | VS Code con **`weather.py`** (la pestaña lo nombra). Se lee la tabla `DESCRIPCIONES = {0:"despejado", 1:"mayormente despejado", … 99:"tormenta con granizo intenso"}` — los **códigos WMO en español** — y `def obtener_ubicacion(): """Obtiene ubicación por IP pública. (Cachada: la ubicación no cambia entre preguntas…)"""` con `requests.get("https://ipapi.co/json/", timeout=…)`, `lat/lon/ciudad`, `_cache_ubicacion`, y el `except: print("No se pudo detectar la ubicación real.")` |
| 3:10 | `scene05701` | el Explorador otra vez, con `mi_jar…` abierto (la misma lista de 24) y, a la derecha, **`discord_bridge.py`** en VS Code: `def enviar_recordatorio(titulo):` con `embed = discord.Embed(title="Recordatorio", description=f"⏰ {titulo}", color=discord.Color.blue())`, `for ch in canales_discord: try: ch.send(embed=embed) except: pass`, `def activar_sentencia_musica(nombre_cancion="")`, **`futuro = asyncio.run_coroutine_threadsafe(enviar_mensaje_dsc, salgo_loop)`**, `def enviar_ubicacion_ua():`. En la terminal: `python main.py` con un **traceback** (`File "C:\Users\…\interfaz_jarvisia_juan\correct…", line 2 column 1 (char 27), se guardó una copia en …`) y el chat contestando «hola / No he podido entenderte… / No» |
| 4:30-7:30 | — | (pendiente: estos cinco minutos los va a cerrar la transcripción; aquí no hay cuadro leído todavía) |

**Lo que el episodio 2 le confirma a ella, y a nosotros:** el autor **también se quedó
trabado** —el título lo dice («casi muere a mitad de camino») y el traceback de
`scene05701` lo prueba—; su arreglo fue **especificar el cerebro** y pasar de Gemini, que es
exactamente lo que ella escribió en su prompt. Y las tres cosas que ella quiere copiar están
ahí nombradas con su archivo: `knowledge.py` + `conocimientos/`, `weather.py` sin API key, y
el hilo aparte de `asyncio` con sus conectores.

---

## 4 · Cruce con CORT: qué tiene cada enseñanza, con archivo y línea

| la enseñanza del tutorial | ¿qué tiene CORT hoy? | veredicto |
|---|---|---|
| el modelo no sabe qué día es: sacárselo del aparato (`scene07201`, `scene16201`) | `ui/js/placa.js` pinta `horaPlaca(new Date())` y `fechaPlaca(new Date())` con el **reloj del equipo**, y su regla `medible()` borra el campo si no hay valor; `scripts/prueba-placa.mjs` (49) lo comprueba con el reloj congelado | **HECHO, y con prueba** |
| `memory.py` con `load_long_memory` / `save_long_memory` / `get_memory_context` (`scene12601`) | `backend/app/memory.py` + `/api/memories` y `/api/profile` (`main.py:189-195`, `main.py:266-297`) + `Recuerdos.java` en el teléfono | **HECHO** |
| `knowledge.py` + la carpeta `conocimientos` (`scene00001`) | `backend/app/conocimiento.py` desde el commit `1ce2ab3` de hoy: índice con título/fecha/tamaño, búsqueda 3/2/1, cita o confiesa, candado con `../` cortado. 47 comprobaciones en arena y 7 mutaciones que muerden | **HECHO en el módulo; la ruta HTTP espera a su `main.py`** |
| `weather.py` con WMO en español, `ipapi.co` y caché, sin API key (`scene02701`) | `backend/app/sensors.py`: la **misma tabla** en `CIELO_WMO` (líneas 33-42, con los mismos textos que se leen en el cuadro del video) y `WEATHER_CACHE` (línea 29), con `cielo_de()` que devuelve «sin dato de cielo» si el código no está | **HECHO, y la tabla es idéntica** |
| Discord con `enviar_recordatorio` y `asyncio.run_coroutine_threadsafe` (`scene05701`) | nada de Discord, y ella no tiene cuenta. El **hilo aparte** sí existe en CORT de otra forma: el núcleo es FastAPI/uvicorn (async de fábrica) y la cara tiene su propio lazo de estados (`ui/js/pasos.js`) | **NO COPIABLE tal cual; la idea sí está cubierta** |
| WhatsApp bot (`whatsapp_bot.py` en la lista) | `Avisos.java:26` dice por escrito que WhatsApp no publica API para leer sus chats. Lo que sí hay: abrir el chat (`Acciones.java:106-108`) y la llamada saliente (`Telefono.java`) | **Límite honesto, no se finge** |
| Tkinter (`class JarvisUI(tk.Tk)`) e interfaces `.hta` | CORT tiene **tres** pieles para el mismo cuerpo: la cara web (`ui/`, Three.js), el APK que la envuelve y Electron (`desktop/main.cjs`). Su prompt pedía «Asyncio, Tkinter, darle su hilo aparte», y aquí Tkinter **no** existe | **DECIDIDO: no se reescribe la cara en Tkinter.** Sería tirar lo hecho para parecerse al tutorial |
| «siempre lista en segundo plano… desde la barra de tareas» (`scene16201`) | en PC: el servidor y la bandeja no tienen arranque automático (su promesa del `.VBS` sigue sin existir); en el teléfono: `Alarma.java` usa `AlarmManager` real pero **no** sobrevive a apagar (`Alarma.java:29`) porque no se declara `RECEIVE_BOOT_COMPLETED` | **NO EXISTE** — es el hueco del arranque solo |
| «SYSTEM METRICS» con CPU/RAM/DISK en barras y «SYSTEM LOG» (`scene18001`) | las barras ya están: `ui/js/hud.js:141-142` (`#envcpu`, `#bar-cpu`, `#ramgb`, `#bar-ram`), medidas con `psutil` en `local_commands.py:30-32`. Lo que **no** existe: el panel de registro con el informe de diagnóstico ni el aviso espontáneo al pasarse del umbral | **MEDIA: la medida sí, la vigilancia continua no** |
| «AI STATUS: escucho… presiona para activar» (`scene18001`) | en la cara hay estados de verdad en el orbe y en la placa (`ESTADOS_PLACA`, 7 estados), y en el teléfono la burbuja se presiona (su `Flotante.java`, sin commitear). Lo que no hay es **escucha permanente con palabra de activación** | **MEDIA: el estado sí, el oído no** |

---

## 5 · Lo que se construye a partir de esto (con su puerta)

1. **El panel «SYSTEM LOG» con umbral.** Es lo único del HUD del tutorial que a CORT le falta
   de verdad, y ya tiene sus piezas: `local_commands.py` mide, `hud.js` pinta barras, y
   `optimize.py` sabe quién come la RAM. Falta: una muestra periódica con umbral y su frase
   honesta («RAM 88 % · cerrando cachés» / «RAM 88 % · te lo digo y no toco nada»). **Necesita
   que ella diga el umbral y qué hace CORT al pasarse.**
2. **El arranque solo, en serio.** Un `.desktop` en `~/.config/autostart` en Linux y el
   acceso directo en `StartUp` en Windows, sin permisos nuevos y sin servicios. Su promesa del
   `.VBS` cabe aquí.
3. **Cosido del conocimiento.** El módulo ya está probado; falta `GET /api/conocimiento` en su
   `main.py` y su hoja en la cara. Bloqueado por su archivo sin commitear.
4. **La transcripción de los dos episodios**, cuando termine la pasada de Vosk, para cazar lo
   que se dijo sólo en voz (los pasos numerados del episodio 1 y los últimos tres minutos del
   episodio 2).

## 6 · Lo que este documento NO afirma

- No afirma nada sobre el contenido de los **minutos 4:30-7:32 del episodio 2** ni sobre la
  narración de ninguno de los dos: eso lo dirá el audio, y al momento de escribir esto seguía
  procesándose.
- No afirma que el tutorial funcione: se ven sus errores (el «No he podido entenderte» y el
  traceback de `scene05701`), y eso es parte de por qué sirve de referencia.
- No copia la pila del tutorial. Copia sus **ideas comprobables** —la fecha del aparato, la
  memoria con funciones, el clima sin llave, el índice de conocimiento— y deja su interfaz
  Tkinter/HTA, que en CORT ya está resuelto de otra manera y mejor para el teléfono.
