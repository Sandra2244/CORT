# REDESIGN — la cara de CORT, por capas

> **Estado: EJECUTADO el 2026-10-10 (R1–R6 verificados en navegador; R7 escrito y
> sin medir — esta copia del proyecto no trae ningún `.vrm` ni sprite).**
> Este documento fue el análisis de las 8 referencias en video que trajo Sandra
> (2026-10-09/10, carpetas `Referencias IA CORT/` e `IA CORT/`), el diagnóstico
> del front actual (`apps/web/src/`, 1 798 líneas) y el plan de rediseño. Lo que
> se implementó y midió está marcado en `STATUS.md` (fila del 2026-10-10); lo que
> no, sigue siendo diseño, no realidad.
> Los frames extraídos para este análisis vivieron en `/tmp/frames/` (48 imágenes,
> 6 por video); `/tmp` se borra con el reinicio — los videos fuente sí están
> respaldados en `Respaldo Proyectos Programacion/`.

---

## 1. Qué dice cada referencia

### El inventario de los 8 videos

| Video | Qué es | Lo que enseña |
|---|---|---|
| v1 — `035346…` (@sued.tiago, 17 s) | JARVIS de GitHub sobre webcam | **Un anillo azul como único protagonista.** El resto son chips circulares flotantes y UNA línea de texto con los gestos disponibles. Las tarjetas de contenido salen volando del anillo hacia la mano. Cero paneles fijos. |
| v2 — `07bf92…` (@techencclair, 5:11, tutorial) | Instalación de "Jarvis Final" | Backend: **Python + Ursina (motor 3D) + edge-tts + PyAutoGUI + google-genai**, todo por `.env` con claves (Gemini, Groq, SerpAPI, Home Assistant). La interfaz es un juego, no una web: ventana transparente a pantalla completa. |
| v3 — `90e21d…` (@techencclair, 3:31) | El HUD en acción | **Overlay a pantalla completa sobre el escritorio real**: núcleo orbe en el centro, un avatar pequeñito de pie en la esquina derecha, y **los gestos de mano abren y cierran superficies**. El panel de ajustes es UN modal centrado que aparece y desaparece. Nada vive en pantalla permanentemente salvo el núcleo y la hora. |
| v4 — `f7d1…` (@techencclair, 3:12) | El mismo JARVIS empaquetado | **La pila del instalador de Windows: Python 3.12 + Node/NPM + venv + Flask + WebSockets + frontend Vite/TypeScript + OpenCV + edge-tts.** Es exactamente la pila de CORT (Python + FastAPI/WebSocket + React/Vite). Se distribuye como `JARVIS_Setup_v1.0.exe` (Inno Setup) que instala dependencias y pregunta datos de memoria (nombres de la familia) durante la instalación. |
| v5 — `fb05…` (@techencclair, 2:12) | HUD con reloj y átomo | Reloj digital arriba al centro, orbe-átomo en el centro, avatar pequeño abajo a la derecha, **el escritorio se ve a través del fondo translúcido**. El gesto de "pinzar" manipula ventanas reales. Tres elementos en pantalla, no treinta. |
| v6 — `fd38…` (@iacontuki, 45 s) | "Blackbox" en terminal | Prueba de que la **estética terminal monocromática** (J.A.R.V.I.S persona en CLI) también vende; no aporta layout para CORT, pero sí la lección de que la personalidad puede vivir en el texto, no en 12 botones. |
| v7 — `My AI agent built me a real Iron Man Jarvis…` (3:18) | Jarvis con tarjetas verdes | **Tarjetas de terminal arrastrables flotando sobre la cámara/escritorio**: cada resultado es una tarjeta con borde de neón que se agarra con la mano y se lanza. La lista de archivos ES la interfaz; no hay árbol de carpetas permanente. |
| v8 — `VID-20261009-WA0022.mp4` | **Foto de la pantalla de CORT hoy** | La evidencia del problema, en español y con nombre: el chat montado ENCIMA del reactor, el cabezal con estado+atuendo+clima+reloj, el botón "gestos con la cámara", el párrafo de explicación del permiso, dos bloques blancos sin pintar, la telemetría asomando arriba a la derecha, el tirador "ocultar" abajo a la derecha y el formulario ENVIAR. Todo a la vez. |

### La gramática común (lo que las 7 referencias hacen igual)

1. **Un solo protagonista**: el núcleo/orbe, centrado. Todo lo demás es invitado.
2. **Transparencia sobre el escritorio**: el asistente vive ENCIMA del trabajo, no ocupa una ventana. El fondo es el sistema real oscurecido, no un lienzo opaco.
3. **Superficies transitorias**: los paneles nacen, cumplen y mueren (modal centrado o tarjeta que se lanza). Ninguna referencia tiene un panel abierto los 365 días.
4. **El avatar es pequeño hasta que importa**: en v3/v5 el cuerpo holográfico es una figurita en la esquina; se agranda sólo cuando habla. (CORT con su VRM a 7 fps puede copiar esto sin costo: un VRM pequeño cuesta menos fotogramas que uno a pantalla completa.)
5. **Instrucciones fuera de la cara**: ninguna referencia explica sus controles con párrafos. Los gestos caben en UNA línea al pie (v1) o se descubren haciendo.
6. **Cromatografía de dos tonos**: azul/cyan + un acento, sobre casi-negro. El ruido visual lo eliminan los huecos, no los bordes.

## 2. Diagnóstico del CORT actual

Lo que hay hoy (`App.tsx` + `Hud.tsx` + CSS), con la bandeja abierta — que es el estado del video v8:

| Elemento | Problema |
|---|---|
| Cabezal del HUD (estado · atuendo · ciudad · clima · reloj · ⤾) | Cuatro datos + reloj + botón en una línea que **nunca se oculta**. Es un riel disfrazado de cabecera. |
| `GestoCamara` + `Voz` + `Atuendos` apilados | **El riel.** Tres bloques de botones con sus párrafos explicativos (`gesto-nota`) siempre visibles cuando la bandeja está abierta. Son 6 controles y ~8 líneas de manual. |
| `Telemetry` (arriba a la derecha) | Panel de diagnóstico operativo viviendo en la cara pública. Es información del `make doctor`, no del holograma. |
| `log` de mensajes | Chat completo siempre montado; con la bandeja abierta tapa el reactor (literalmente, en v8 el texto pasa por encima del anillo). |
| `Bandeja` (esquina) | El mecanismo es correcto — es lo que más se acerca a las referencias — pero abre DEMASIADO: abre el riel entero, no una superficie a la vez. |
| Formulario + ENVIAR | Fijo abajo, siempre. En las referencias la entrada es un susurro bajo el núcleo que sólo existe cuando se le llama. |
| Bloques blancos del v8 | Render de `atuendos` sin carpeta configurada pintando huecos: estado vacío sin diseñar. |

**Conclusión honesta**: el andamiaje (reactor, paleta, WebSocket, capas) es mejor que el de las referencias —ninguna tiene memoria persistente ni capa de permisos—. Lo que sobra es **superficie visible permanente**: CORT muestra su caja de herramientas; las referencias muestran una cara.

## 3. El rediseño por capas

Regla madre: **en reposo, la pantalla tiene exactamente tres cosas — el reactor/VRM, la hora, y un punto de entrada.** Todo lo demás se invoca y se despide.

```
L0  ESCENARIO   fondo: escritorio real oscurecido (overlay transparente)
L1  CARA        reactor/VRM centrado + reloj mínimo. Permanente. Lo único fijo.
L2  VOZ         superficie de conversación: aparece bajo el núcleo, se desvanece
                8 s después de la última respuesta. Nunca tapa el anillo.
L3  HERRAMIENTAS modal único centrado (estilo v3): pestañas voz · cámara ·
                atuendos · telemetría · ayuda. Se abre con un gesto/tecla, se
                cierra con Esc. Un modal, no tres rieles.
L4  RESULTADOS  tarjetas transitorias (estilo v7): captura, clima, cuenta atrás,
                respuesta larga. Nacen del núcleo, se arrastran, se cierran.
L5  EFECTOS     pulso/glitch/scanlines: igual que hoy, sin cambios.
```

### Qué se quita y qué se convierte en qué

| Hoy | Pasará a | Por qué (referencia) |
|---|---|---|
| Cabezal con 4 datos + reloj + botón | **Sólo el reloj**, pequeño, arriba al centro; el estado (línea/procesando) se comunica con el COLOR del anillo, que ya lo hace | v5: reloj + núcleo y nada más |
| Riel `GestoCamara`+`Voz`+`Atuendos` con párrafos | Chips de icono en el modal L3; los párrafos `gesto-nota` se mudan a la pestaña **ayuda** del mismo modal | v1: una línea al pie; ninguna referencia explica en la cara |
| `Telemetry` en esquina | Fila dentro del modal L3 (pestaña sistema); en la cara, sólo un punto de color que coincide con el estado | v3: el diagnóstico no es decoración |
| Chat siempre montado | Superficie L2: última respuesta en texto holográfico bajo el anillo; el historial vive en la bandeja (que ya existe) | v8 muestra el chat tapando el reactor; v1/v7 muestran UNA tarjeta a la vez |
| Formulario fijo | Input que se despliega al pulsar el núcleo o al tocar la pantalla (y sigue accesible por `Ctrl+/` para teclado) | Las referencias de mano no tienen caja de texto: la invocación ES el gesto |
| Tirador "⌃ mensajes" | Se queda, simplificado a un punto con contador sin texto | Ya es el mecanismo correcto |
| Temporizador | Tarjeta L4 (ya es un número que aparece; sólo cambia de domicilio) | — |

### Estética (la imagen Cortana que Sandra eligió como referencia de arte)

- Paleta actual (azul #4fc3f7-ish / violeta, scanlines, polvo de partículas) **ya coincide** con el arte de referencia: conservar.
- Con el VRM montado: el cuerpo es la CARA (L1), el reactor pasa a ser su zócalo/anillo — como la figurita de v3/v5 pero invertido: en CORT el cuerpo manda cuando está puesto. A 7 fps medidos, el cuerpo pequeño cuesta menos que el reactor lleno: redimensionar el VRM al 40 % debería dar margen (sin medir aún — es hipótesis con prueba barata: el contador de fps de `Scene.tsx` ya existe).
- Estados vacíos diseñados: sin `CORT_AVATAR_DIR`, el selector de atuendos NO pinta bloques blancos; pinta una línea: "sin atuendos — carpeta por configurar".

## 4. La parte multi-SO y APK — qué probó la referencia v4

La pregunta de Sandra: *"¿funcionará en APK y conservará las mismas funciones que en PC, en Windows y Linux/KDE?"* La respuesta con la evidencia de los videos y `PLATFORM.md`:

1. **La pila no se toca.** v4 demuestra que un JARVIS con el MISMO esquema que CORT (backend Python + WebSockets + frontend Vite/TS) se empaqueta y se instala en Windows con un `.exe` (Inno Setup) que trae su propio Python y Node. CORT no necesita cambiar una línea de arquitectura para eso; necesita un instalador, que es Fase 8/9 (lanzador), no reescritura.
2. **La cara es la misma en todos los SO porque ya es una PWA servida por el core.** Windows (Edge), Linux/KDE (Konqueror… no: Firefox/Chrome), y Android (Chrome vía `--lan`) pintan el mismo `dist`. El rediseño por capas respeta esto: ninguna capa nueva usa API que no sea ya web.
3. **APK**: Capacitor (decisión ya medida en `PLATFORM.md`) envuelve la PWA. Lo que NO viaja a la APK: las acciones de sistema (`wpctl`, `xdotool`, capturas) — ésas viven en el core Python, que corre en el PC; el teléfono es una **cara remota**, no un segundo cerebro. Esto es exactamente lo que hace la referencia de Home Assistant en v2 (token + URL): el teléfono manda, el servidor hace.
4. **El cuello de botella real del teléfono sigue siendo HTTPS** (cámara/micrófono por `http://` LAN están bloqueados por el navegador — ya escrito en STATUS). Ningún rediseño lo evita; es una decisión de Sandra: certificado local o servir por túnel.
5. **Gestos de mano**: v3/v5 los hacen con MediaPipe. CORT decidió lo contrario (Laplaciano, 0 dependencias, 17 fps medidos) y esa decisión se mantiene: el rediseño usa gestos sólo como *atajos*, nunca como *única puerta* — en el teléfono no hay webcam frontal libre mientras se usa la app.

## 5. Orden de ejecución propuesto (una capa por commit, con su prueba)

| Paso | Qué | Coste aprox. | Riesgo | Resultado (medido 2026-10-10) |
|---|---|---|---|---|
| R1 | **Silenciar la cara**: ocultar cabezal (salvo reloj), telemetría y riel por defecto; el estado viaja sólo en el anillo | pequeño (CSS + `abierto` por defecto ya casi está) | bajo — no toca lógica | **hecho y visto**: en reposo el DOM son reloj+dot+esquina; captura `/tmp/cort-cara2.jpg` |
| R2 | **Modal L3 único**: voz/cámara/atuendos/telemetría/ayuda como pestañas; los párrafos `gesto-nota` se mueven a ayuda | mediano (reacomodo de componentes existentes, sin reescribirlos) | bajo | **hecho y visto**: `<dialog>` con `showModal()`, 5 pestañas navegadas, foco atrapado, `Esc` nativo; captura `/tmp/cort-modal-ayuda.jpg` |
| R3 | **Superficie L2**: última respuesta bajo el anillo, auto-ocultable; historial se queda en la bandeja | mediano | medio — cuidado con el `log` que ya prueban las suites | **hecho y visto**: saludo del core → subtítulo con ✕ → desapareció solo; el `log` intacto y las 228 pruebas verdes |
| R4 | **Estados vacíos** (atuendos sin carpeta, clima sin ciudad) | pequeño | bajo | **hecho y visto**: sin `CORT_AVATAR_DIR` la pestaña declara la instrucción del `.env`; miniaturas con fundido al decodificar |
| R5 | **Entrada invocada** (tap núcleo → input) | mediano | medio en móvil — sin verificar en físico, como todo lo táctil | **hecho en escritorio** (tap al centro abre y enfoca; `Ctrl+/` idem); **en móvil: sin verificar** |
| R6 | **Tarjetas L4** para captura/clima/temporizador | grande | alto — dejar para último, quizá nunca | **versión mínima**: el temporizador ya era tarjeta propia; captura y clima viajan por el subtítulo y la pestaña sistema. Las tarjetas dedicadas se quedan sin hacer, como proponía la fila |
| R7 | VRM pequeño como cara + reactor como zócalo | mediano | medio — medir fps antes de prometer | **escrito, sin medir**: `ALTURA` 2,3 + `PEDESTAL` 0,9 + zoom 0,55 compilados; **ningún `.vrm` en esta copia** (regla 7), así que ni un solo fps nuevo. *Actualizado 2026-10-10 (II): ya hay 8 `.vrm` reales en la máquina (`CORT_AVATAR_DIR`), se listan y se eligen verificado; materialización, reposo procedural, parpadeo y tres tamaños escritos — el render en pantalla sigue **sin verificar** (la dueña pidió no abrir el navegador)* |

Nada de esto añade dependencias (ni framer-motion ni zustand: la regla de los 1,8 GiB sigue). Nada toca el protocolo WebSocket, salvo R3/R4 que usan marcos que ya existen. `make test` (**228 pruebas** desde el 2026-10-09) siguió verde tras el rediseño: `Ran 228 tests in 68,948 s ... OK`. Las pruebas del HUD que hoy existen se reescriben cuando su superficie cambia, no antes. **Un hallazgo que no estaba en el plan**: plegar la bandeja sólo con `visibility` dejaba el degradado del HUD ocupando media pantalla y **cortando el reactor por la mitad** — el pliegue nuevo también anima `max-height` (220 ms, sólo durante la animación).

## 6. Conclusiones: qué mejorará esto en el proyecto

- **Deja de parecer un formulario con un adorno brillante y pasa a parecer una cara**: el problema del v8 se resuelve por su raíz (superficie permanente), no retoque a retoque.
- **Consigue fps gratis**: ocultar DOM y paneles en reposo es trabajo de compositor que deja más GPU/CPU para el reactor y el VRM (los 7 fps del cuerpo son hoy el número más flaco del proyecto).
- **Sobrevive igual en PC y APK**: menos superficie fija = menos que reflowear a 536 px; el patrón "núcleo + modal" es idéntico en ventana de 1366 px y en pantalla de teléfono.
- **Da el paso de instalación que la referencia v4 ya validó**: un `CORT_Setup.exe` con Python empotrado es factible con la pila actual; abre la puerta a que otra persona —no sólo Sandra— use CORT en Windows sin terminal.
- **No rompe nada verificado**: el core, el protocolo, la memoria, los permisos y las 226 pruebas quedan intactos; esto es una capa visual sobre el cable que ya funciona.

---
*Análisis hecho el 2026-10-10 sobre los videos de `Respaldo Proyectos Programacion/`, el código de `apps/web/src/` a `cort-local-verified` (post-v0.6.1) y `docs/STATUS.md`. Los frames extraídos son temporales (`/tmp/frames/`); los videos fuente, respaldados. Ejecutar este plan requiere luz verde de Sandra y se hace capa por capa, midiendo en esta máquina antes de afirmarlo.*
