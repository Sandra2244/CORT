# REDESIGN-NUCLEO — CORT como núcleo estilo JARVIS (plan)

> Propuesta de rediseño nacida de **cuatro videos de referencia nuevos** que aportó la dueña
> del proyecto (2 de `@sued.tiago` / `@techenclear` con la interfaz Iron‑Man/JARVIS y el
> agente que «te tira lo que pides», y dos de `@techenclear` en francés con el núcleo
> holográfico al centro y ventanas de chat/código). Se miraron **frame a frame** con un
> `ffmpeg` estático desde un entorno de usar y tirar (hojas de contacto de 8 fotogramas por
> clip). **Cero assets, cero fotogramas, cero líneas de código de terceros entran al repo**:
> se copia distribución y comportamiento, no expresión protegida (regla 9).

Este documento **no ejecuta nada todavía**: es el mapa de qué se integra, dónde es factible
en esta máquina y con esta pila (Python + React + Ollama, regla 13), y en qué orden. Cada
pieza lleva su veredicto honesto —**hecho factible aquí / necesita dependencia nueva /
inviable sin APK / choca con una regla de seguridad**—, dicho en vez de simulado (reglas 10 y 11).

## Los seis patrones que salen de los cuatro videos

1. **El núcleo es la cara, con paneles alrededor.** Un reactor/orbe holográfico vive en el
   centro de la pantalla y los paneles (archivos, chat, reloj, controles) flotan a los lados
   sobre el escritorio real, translúcidos. CORT ya tiene el reactor y el HUD por capas; lo que
   falta es que los paneles **sean ventanas de vidrio flotantes**, no un solo `<dialog>`.
2. **Ventanas y tarjetas que se agarran y se sueltan.** Tarjetas de archivos y paneles que se
   arrastran con el ratón, el dedo **o la mano**. CORT ya tiene arrastre de paneles con puntero
   (función 37, `cort/arrastre.ts`, medido en DOM); falta la variante con la mano y el modo
   «vidrio» (transparencia + desenfoque).
3. **Gesto con la cámara: la mano es el cursor.** Las dos grabaciones de `@sued.tiago` y una de
   `@techenclear` mueven tarjetas **con los dedos frente a la webcam**, sin tocar nada. Eso es
   **seguimiento de mano** (MediaPipe Hands en el navegador). Hoy CORT sólo tiene el gesto de
   **desenfoque** (función 71: borroso ↔ nítido cambia el tamaño del orbe) — no detecta la mano.
4. **Voz que abre cosas y un agente que las hace.** «JARVIS, abre X» lanza la app/ventana, y un
   panel de chat (tipo Claude Code en el video) ejecuta tareas. CORT ya tiene voz (función de
   `Voz.tsx`), intents de abrir apps y ejecutar acciones (`intents.py`, `actions.py`), y un
   planificador multi‑paso (función 75). Falta la **consola de chat‑agente** como superficie
   propia y visible.
5. **Un núcleo que actúa por petición O por iniciativa propia.** Alarmas, recordatorios, «te
   habla solo». CORT ya tiene temporizadores/alarmas (`timer.py`), iniciativa (`initiative.py`)
   y memoria (SQLite). Falta el **calendario con fechas naturales** («mi amiga cumple el 23 de
   noviembre de 2008») y conectarlo con la voz para que avise solo.
6. **Secciones y menús propios, no una sola pantalla.** La dueña lo pide explícito: «otras
   pantallas, otros menús… dividido en secciones». Es la pieza de arquitectura: la cara pasa de
   «un modal» a un **espacio de trabajo con secciones** (Núcleo · Archivos · Agenda ·
   Dispositivos · Consola · Documentos · Ayuda), cada una una ventana de vidrio.

## Qué pediste cada cosa, y su veredicto en ESTA máquina

| # | Lo que quieres | Veredicto | Dónde y con qué |
|---|---|---|---|
| N1 | **Ventanas de vidrio flotantes y arrastrables** (mover el reloj, el logo, ocultar paneles, transparencia) | **Factible aquí, sin dependencia nueva** | Extiende `cort/arrastre.ts` (ya medido) a un modo `glass` (`backdrop-filter`, opacidad regulable) y a más superficies (reloj, logo, tarjetas). React puro. |
| N2 | **Calendario + recordatorios con lenguaje natural** y que **hable solo** | **Factible aquí, sin dependencia nueva** | Módulo nuevo en el core (`calendar.py`): parseo de fechas en español con la biblioteca estándar, tabla SQLite propia, y disparo por `initiative.py` + `timer.py` → voz. Pruebas `test_calendar.py`. |
| N3 | **Consola de chat‑agente** (una ventana donde CORT ejecuta tareas paso a paso, como el Claude Code del video) | **Factible aquí** (UI; el cerebro ya existe) | Superficie React nueva que muestra el plan (`planner.py`) y cada `intent` ejecutado con su resultado. Reusa el protocolo WS actual; si añade marco, se documenta en ARCHITECTURE (regla 5). |
| N4 | **Secciones / otras pantallas / otros menús** | **Factible aquí** | Reorganizar la cara en un espacio de trabajo con secciones (N1 las hace ventanas). Es el contenedor de N1–N3 y N5–N6. |
| N5 | **Gestos con la mano** (la mano como cursor, agarrar y lanzar tarjetas) | **Factible en el navegador, con una dependencia nueva y pesada** | MediaPipe Hands (`tasks-vision`) corre en el cliente web, no en el core. **Coste medible**: WASM + modelo de ~2–10 MB y CPU por frame — en 2 núcleos hay que medir fps antes de prometerlo. Se propone como **N5 opcional** y medido, no asumido. |
| N6 | **Reproductor que controle el móvil** (poner Lark Player por defecto, «pon la playlist looksmaxing», reproducir vídeo como música, estilo YouTube Music sin conexión) | **INViable desde esta máquina y desde el navegador: pide APK nativo Android** | Un navegador/PWA **no puede** elegir la app reproductora del sistema ni lanzar Lark Player con una playlist: eso exige permisos nativos (`QUERY_ALL_PACKAGES`, MediaSession, un servicio en primer plano) → un **APK**, y aquí no se compila (JDK/SDK/Gradle congelan el portátil, `docs/PLATFORM.md`). **Además** la decisión LAN está sin tomar (que el móvil hable con el core del PC). Lo que SÍ se puede: un **reproductor propio en la interfaz web** (HTML5 `<audio>`/`<video>`) que suena en el PC y, por `--lan`, en el navegador del móvil — sin tocar apps nativas. |
| N7 | **«Ejecutara todo sin limitación»** (que CORT haga cualquier cosa sin pedir permiso) | **Choca con la regla 6 — NO se hace así** | Regla 6: toda acción sobre el sistema pasa por una **capa de permisos** y **nunca** comandos arbitrarios del usuario ni del LLM. Un modelo local pequeño puede inventar un `rm` o un comando dañino; «sin limitación» en un núcleo que ejecuta es justo lo que no debe existir. **Lo que sí**: ampliar la **lista cerrada** de acciones (más apps, más controles) con confirmación y bitácora de rechazos (`audit.py` ya existe). Se puede abrir MUCHO sin quitar el freno de seguridad. |
| N8 | **Documentos tipo Kimi** (subir referencia → CORT arma PDF / Word / diapositivas) | **Parcialmente factible aquí; la calidad depende del modelo; los formatos piden dependencias** | Redactar el contenido lo hace el LLM local (`brain.py`); con `llama3.2:3b` en 2 núcleos el resultado es **borrador, no nivel Kimi** (Kimi usa modelos mucho mayores y en la nube). Exportar a `.docx`/`.pptx`/`.pdf` real exige librerías nuevas (`python-docx`, `python-pptx`, `reportlab`/LibreOffice) → **dependencias que hay que justificar** (regla 4). Se puede empezar por **Markdown y HTML** (sin dependencias) y añadir exportadores como fase aparte. |

## Orden de ejecución propuesto (una fase a la vez, regla 1)

Se avanza por increments pequeños, cada uno con sus pruebas y **sin abrir Ollama + navegador
+ build a la vez** (la máquina se congela; `feedback-no-congelar-pc`). El orden maximiza la
cara JARVIS visible con **cero dependencias nuevas** antes de tocar nada que cueste RAM:

- **N1 — Ventanas de vidrio.** El cambio más «JARVIS» y más barato: los paneles del modal se
  vuelven ventanas flotantes translúcidas, arrastrables y ocultables. Front puro.
- **N4 — Secciones.** El espacio de trabajo que las contiene (Núcleo · Archivos · Agenda ·
  Consola · Ayuda). Front puro.
- **N2 — Agenda que habla sola.** `calendar.py` en el core + fechas naturales + disparo por
  iniciativa/voz. Python estándar, con pruebas. Es lo que hace a CORT un *núcleo* útil en el día.
- **N3 — Consola de chat‑agente.** La ventana donde se ve a CORT ejecutar el plan paso a paso.
- **N5 — Mano (opcional y medido).** Sólo después de medir fps; si no corre en 2 núcleos, se
  queda en el gesto de desenfoque que ya existe y se dice.
- **N6/N7/N8** quedan **documentadas como están aquí**: N6 pide APK (otra máquina + decisión
  LAN), N7 no se hace «sin limitación» por seguridad, N8 empieza en Markdown/HTML y crece con
  dependencias justificadas.

## Reglas que este plan respeta y por qué

- **Regla 13 (la pila no cambia):** todo lo anterior es Python + React + Ollama. N5 usa
  MediaPipe en el *navegador* (no añade nada al core), N6/N8 son las únicas que asoman fuera y
  ambas están marcadas como inviables/aquí‑no.
- **Regla 6 (permisos):** N7 se rechaza tal como está enunciada y se ofrece su versión segura.
- **Regla 11 (no afirmar sin ejecutar):** ninguna fila de este plan va al `README.md` ni a
  `FUNCTIONS.md` como ✅ hasta medirse en esta máquina; lo no hecho dice «sin verificar».
- **Regla 12:** la portada del README sólo cambia cuando un increment esté ejecutado y visto.
