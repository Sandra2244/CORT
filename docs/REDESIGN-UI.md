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

## 7. R5 · La reestructura por ventanas (2026-10-11)

**Qué dijo Sandra, con sus palabras:** «chimbo y horrible: reestructura la base y luego agregas todo eso, las ventanas de vidrio, diséñalo todo, y luego se le cambian colores a mi estética». No es una crítica a un botón: es un orden de trabajo, y ese orden es el que está ejecutado aquí.

**El diagnóstico de por qué el rediseño del 10 se veía mal.** No por las capas —ésas siguen— sino porque **dejó dos superficies que hacían lo mismo y ninguna se podía manejar**: la bandeja del HUD (con su asa, su barra de estado y su botón «ajustes») y el `<dialog>` modal (con cinco pestañas y su propio lenguaje de control). De ahí vienen los tres defectos que se le notaron de golpe: los mandos estaban **regados** (punto de la esquina + «ajustes» + teclas + pestañas), el modal **tapaba la cara** y no dejaba abrir otra cosa encima, y **no había forma de echar una superficie con el dedo** — cerrar era `Esc` o pulsar el overlay, y en el teléfono el overlay no existe como idea. Un interfaz con dos formas de hacer lo mismo se desordena sola, por mucho que se pula el color.

**Los tres pasos, en el orden que pidió.**

1. **La base.** Una sola primitiva, `ui/Ventana.tsx`: tubo (asa + rótulo + `⤾` + `✕`) y cuerpo. Todo lo demás pasó a ser contenido dentro de ella: `Charla`, `Voz`, `GestoCamara`, `Atuendos`, `Telemetry`, `Ayuda`. Se borraron `Hud.tsx`, `Bandeja.tsx` y `Panel.tsx` y sus **29 reglas de CSS duplicadas**; `index.css` pasó de **1338 a 1309 líneas** — la hoja casi no encogió en neto porque las reglas muertas salieron y entró el bloque nuevo del cristal, el muelle y la charla (1338 − 29 fuera + el bloque de ventanas = 1309, medido con `wc -l`). El registro `ui/Ventanas.tsx` (`id → cuerpo`) es lo que evita que esto vuelva a pasar: una ventana nueva es una fila, no una superficie nueva que inventar.
2. **El vidrio.** `backdrop-filter: blur(14px) saturate(150%)` sobre un dosel violeta en dos gradientes, filo iluminado (`--glass-line`), hilo de luz en el tubo, sombra que despega la ventana del reactor y entrada con revelado de 260 ms. **Sólo** en ventana y muelle: cada `backdrop-filter` cuesta un búfer por capa y esta máquina no tiene GPU, así que ponerlo en cada línea de texto sería pagar fps por decoración. Los cuatro cantos de escritorio y la cascada de 46 px en móvil existen para que las ventanas se puedan **colocar y mover**, que es lo que ella pidió el 9 («puede colocar, mover»).
3. **Sus colores.** El cian de consola sale de la hoja: `:root` pasa a tokens (`--glass-*`, `--tint`, `--glow`, `--bg` hollín-violeta) y las ~25 apariciones de `rgba(120, 190, 230, …)` y `rgba(92, 225, 255, …)` se reasignan a ellos. `palette.ts` deja de tener un atuendo verde-agua y un cian: los cinco quedan en morado/azul con distinta luminancia, y `DEFAULT_OUTFIT` pasa de `work` a `night` (el morado de Cortana), coincidiendo con el `--tint` de la hoja.

**Qué se verificó y qué no** (2026-10-11, core real en `--demo`, viewport del navegador de prueba 536×521):

| Comprobación | Resultado |
|---|---|
| Tipos y compilado | `tsc --noEmit` sin errores; `vite build` en 7,5 s |
| Pruebas del core | `Ran 331 tests in 78,208 s — OK` (el `shake` sigue teniendo productor y protocolo cerrado) |
| Reposo | 0 ventanas en el DOM, muelle con seis accesos, `dot on` (conectado al core) |
| Varias ventanas | ayuda (z 10, `top` 62) + voz (z 11, `top` 108) conviviendo; la cascada de 46 px sale medida, no supuesta |
| Cristal | `getComputedStyle(...).backdropFilter = blur(14px) saturate(1.5)` — antes del arreglo del orden de prefijos leía `none` |
| **Jalón para echar (build final)** | puntero abajo **150 px** desde el tubo → la ventana **desaparece del DOM** (`querySelectorAll('.ventano') = []`). Medido sobre el bundle de las 14:06, que ya lleva la corrección: se compara el `clientY` del puntero, no la posición sujeta de la ventana |
| **Micro-arrastre (build final)** | el mismo recorrido de **25 px** → **no** se cierra: `top` 62 → 87 y aparece `⤾`. Es la prueba que faltaba para saber que el jalón no cierra por cualquier toque |
| `⤾` recolocar | `top` 87 → **62** y el botón vuelve a desaparecer (la ventana ya no está desplazada) |
| `✕` | cierra la ventana desde el tubo; los seis accesos del muelle quedan en `aria-pressed="false"` |
| `Esc` | con dos abiertas cerró **sólo** la de enfrente (voz) y dejó ayuda |
| Arrastre | `top` de la ventana charla: 108 → 304 con una arrancada de puntero |
| Efecto `shake` | tras «hola cort» apareció `.ventana.fx-shaking` (antes apuntaba a `.hud`, que ya no existe) |
| **Coste del cristal (medido hoy)** | `requestAnimationFrame` sobre 1,2 s: **2 fps con dos ventanas** de vidrio y **1 fps en reposo** con el canvas vacío de ventanas. La diferencia está dentro del ruido de esta máquina: **el cuello no son los `backdrop-filter`, es la escena 3D renderizada por CPU** (sin GPU, 2 núcleos). Mismo número honesto que los ~7 fps del VRM del 10-09 |
| Consola | sin errores ni avisos de React |

**Sin verificar, y así queda:** el reparto en cuatro cantos en una pantalla de escritorio (el navegador de prueba no se pudo redimensionar; sólo se ejercitó la rama de ≤760 px), el dedo real sobre el teléfono, y los fps **en un equipo con GPU** — lo medido aquí es CPU pura y no sirve como promesa para otra máquina.

**Lo que NO se copió.** La referencia de ventanas que ella señaló (`jaredrhod/fullstack-agent`) es **AGPL-3.0**: de ahí viene la *idea* de ventanas flotantes sobre la escena, no una línea de código. El arrastre sí es transplante declarado de `adewaskar/JARVIS` (MIT, atribuido en `apps/web/CREDITS.md`), y sigue siendo el mismo archivo `cort/arrastre.ts` que ya estaba.

---

## 8. R6 · La cara tiene dos estados más: reposo y escucha (2026-10-12)

La cara que salió de R5 tenía **una** sola expresión: el reactor encendido, siempre igual, con ventanas encima. Los videos de referencia que ella trajeron el 10-10 mostraban otra cosa — un asistente que **se recoge cuando nadie le habla** y **forma un anillo cuando escucha**. Este apartado añade esos dos estados y deja el reactor como lo que era.

**Las tres caras, y una sola a la vez.**

| Cara | Qué se pinta | Cuándo |
|---|---|---|
| **Reactor** | el orbe de `scene/Core.tsx` + el polvo de `scene/Particles.tsx` | hay actividad reciente: un gesto, un mensaje, una palabra |
| **Reposo** | `scene/Nube.tsx` en modo hilos: ~11 000 puntos curvos y punteados alrededor de un destello casi quieto | pasan `REPOSO_MS` (30 s) sin nada de lo anterior |
| **Escucha** | el mismo campo de puntos, junto, en un anillo que gira con estelas, agitado por el nivel de la voz | `connection.ts` tiene `escucha` a `true` (micrófono abierto en `cort/voz.ts`) |

**Las tres reglas que sostienen el diseño.**

1. **Nunca dos caras pintando a la vez.** `Scene.tsx` baja la del reactor con `drive.intensity = 1 - Math.max(drive.escucha, drive.reposo)`, y el fundido va en el propio material. No es un adorno: en esta máquina (2 núcleos, sin GPU) dos campos de puntos vivos son dos facturas de fotogramas, y una pantalla a medio segundo por cuadro no comunica nada.
2. **El coste se paga en el *shader*, no en JavaScript.** `Nube.tsx` sube **ocho uniformes por cuadro** y no calcula una sola posición de partícula en el hilo de JS; el movimiento de los hilos, la respiración y la agitación por nivel se resuelven en el *vertex shader* sobre **un** `Points`. Medido el 2026-10-12 con el bundle final, ventana de `requestAnimationFrame` de 3-4 s por estado, viewport 535×521: **1,21 fps el reactor · 1,09 fps la nube en reposo · 1,09 fps el anillo de escucha**. La nube cuesta ~0,1 fps; el cuello sigue siendo la escena 3D renderizada por CPU, exactamente igual que en la medición del cristal de R5.
3. **El reposo lo decide la actividad real, y se puede apagar.** `connection.ts` apunta `actividad` en los gestos (`pointerdown/move`, `keydown`, `wheel`, `touchstart`, todos `passive`), en el envío de un mensaje y cuando el core dice `thinking: true`. Un `state` repetido con `thinking: false` **no** renueva la actividad —si contara, el reposo no llegaría nunca, que es el fallo que esta regla evita—. `?reposo=10` lo muestra pronto y `?reposo=0` lo desactiva para quien no quiera la cara.

**Dónde se fue la voz, y por qué.** El altavoz y el micrófono vivían dentro de `ui/Voz.tsx`, o sea dentro de una ventana: se cerraba la ventana y se cerraba la escucha. El 2026-10-12 la lógica pasó a **`cort/voz.ts`**, que `App.tsx` arranca con `iniciarVoz()` una sola vez, y `ui/Voz.tsx` quedó como un cuerpo de 100 líneas pegado a ese módulo con `useSyncExternalStore`. La **frase de activación** («OK CORT») se separó además en **`cort/activacion.ts`**, un módulo puro sin navegador ni dependencias, precisamente para poder probarlo: **12 pruebas** en `make test-web` (`scripts/pruebas-web.mjs`, el riel que se había jubilado el 10-10 y vuelve con esta capa), incluidas las que exigen que «cortometraje», «corte» o «hola Laura, cortá la música» **no** despierten al asistente.

**Qué se verificó y qué no** (2026-10-12, core en `--demo`):

| Comprobación | Resultado |
|---|---|
| Tipos y compilado | `tsc --noEmit` sin errores; `vite build` sin errores |
| Pruebas | core en verde; `make test-web` 12/12 |
| Tres caras | vistas en navegador con `?demo=reposo` y `?demo=escucha`: `docs/assets/nube-reposo-2026-10-12.png`, `docs/assets/nube-escucha-2026-10-12.png` |
| Coste | la tabla de arriba: 1,21 / 1,09 / 1,09 fps medidos, no supuestos |
| Falsa activación | 12 pruebas de `activacion.ts`, con las trampas léxicas |

**Sin verificar, y así queda:** el micrófono real agitándole la nube a CORT (en este portátil `wpctl status` no lista ningún *Source*; la escucha se probó forzada con `?demo=escucha`), oír la voz con auriculares, el dedo en el teléfono, y los fps de la nube en un equipo con GPU. Las funciones afectadas llevan su fila en `docs/FUNCTIONS.md`: **11, 12, 13, 22 y 83**.

---
---
*Análisis hecho el 2026-10-10 sobre los videos de `Respaldo Proyectos Programacion/`, el código de `apps/web/src/` a `cort-local-verified` (post-v0.6.1) y `docs/STATUS.md`. Los frames extraídos son temporales (`/tmp/frames/`); los videos fuente, respaldados. Ejecutar este plan requiere luz verde de Sandra y se hace capa por capa, midiendo en esta máquina antes de afirmarlo.*
