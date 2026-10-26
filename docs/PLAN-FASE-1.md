# PLAN FASE 1 (nueva) — la CARA: el orbe y su forma de trabajar

Escrito el **2026-10-26** después de releer el mega prompt v2, medir el video de
referencia y leer el orbe actual línea por línea. Este documento **sustituye el orden
de la PARTE C del mega prompt para lo que queda de cara**: la Fase 1 anterior
(burbuja, arranque, iconos, textos) ya está mayormente dentro del repo (2.11.0), y lo
que ella pidió ahora es otra cosa: **que la cara se vea y se comporte como la
referencia antes de seguir añadiendo funciones**.

Regla que manda sobre todo: **una fase no avanza si la anterior no está operando
correctamente.** Cada paso tiene su prueba y su puerta; la puerta de esta fase se
cierra cuando ella lo vea funcionando en su portátil y en su teléfono.

---

## 1 · Las cuatro decisiones de la dueña (2026-10-26, respondidas)

1. **Alcance:** sólo la cara. La pantalla de modelos («Cerebro», catálogo, descarga con
   reanudación, recomendación por hardware) **queda en la Fase 2** con su puerta propia.
2. **Ruta:** **prototipo medido primero** en una página aparte. `ui/js/orb.js` y los CSS
   reales no se tocan hasta que ella apruebe el prototipo. Motivo: el precedente de la
   2.10.0, donde un `import` roto dejó la cara muerta entera.
3. **El árbol sucio** (`Flotante.java`, `MainActivity.java`, `CortNative.java`,
   `brain.py`, el nuevo `pool.py` y `docs/ALOJAR-CORT.md` del taller F15) **se deja
   intacto**: ni se commitea ni se borra. Esta fase vive sólo en `ui/` y `scripts/`.
   Si una prueba se pone roja por esos archivos, se dice y no se arregla de rondón.
4. **Versionado:** `2.12.0` por paso con su entrada de changelog; etiqueta y Release
   sólo al cerrar la fase.

---

## 2 · La referencia, medida (no recordada)

Del video `VID-20261024-WA0034.mp4` (360×640, 4:15) se extrajeron 10 fotogramas y se
miraron. Lo que hay, literalmente:

- Un monitor con un **orbe de puntos y líneas entrelazadas** (plexus), no una bola lisa
  ni una malla rellena. Se ve **aire** dentro: las líneas cruzan, la esfera no es opaca.
- **Cambia de color por estado**: blanco-frío en reposo → cian → **verde lima** cuando
  trabaja o habla. El color es el indicador, no un adorno.
- **Arriba al centro**, un recuadro pequeño con la **hora en monoespaciada** y debajo una
  fila de datos; en un tramo, una columna de texto tipo consola a la izquierda.
- Delante, el **teléfono con un chat oscuro, cabecera de acento y burbujas transparentes**
  (sin caja: el fondo se ve a través del texto).
- En `a074ef6a…mp4` (43 s): un Windows con una ventanita **«Models»** — «+ Load a model»
  y la lista con tamaños. Eso es el «otro apartado» que ella menciona; **es Fase 2**.

**Segunda mirada, con el prototipo ya pintado (2026-10-26).** La primera versión del
orbe se probó contra el código, no contra el video, y el código estaba conforme consigo
mismo: **120 puntos y 322 líneas salieron leyendo como un poliedro**, una bola de aristas
duras, sin el pelo ni el aire de la referencia. Se volvieron a montar los fotogramas
lado a lado con capturas reales del navegador (`vid-01/03/05` frente a `reposo`,
`escucha` y `habla`) y el diagnóstico fue de **densidad y brillo**, no de forma:

| lo que se veía en el video | lo que hacía el prototipo | qué se cambió |
|---|---|---|
| un bulto de puntos, con relieve y thickness | puntos exactos sobre el radio 1,000 | `GRANO = 0.14`: cada punto se sale ±7 % del radio con la misma semilla |
| una maraña: se cuentan decenas de líneas por palmo | 2,7 líneas por punto | `N_PUNTOS` 120→**220**, `VECINOS` 5→**6** (≈700 líneas, 3 dibujos igual) |
| blanco-frío que **ocupa** la pantalla | `#dff6ff`→`#4a7f9e` con alfa **0,62**: se leía gris | `reposo` a `#f6fbff`/`#a9c9dd` con alfa **0,82** |

La prueba (`scripts/prueba-orbe.mjs`) se reescribió a la vez: la comprobación «todos a un
radio exacto» pasó a ser «todos dentro de la banda `1 ± GRANO/2`», el umbral de vecino más
cercano bajó de 0,10 a **0,07** (con el cálculo hecho: 220 puntos con grano siguen sin
tocarse), y el tope de líneas subió de 600 a **900** con un candado nuevo
`n ≤ N_PUNTOS · VECINOS`. Resultado medido: **56 hechos, 0 fallos · 220 puntos, 700 líneas**,
y el coste por frame sigue en **0,03–0,06 ms** de JavaScript.

De GitHub, verificado (26/10/2026, con licencia):

| referencia | licencia | qué tomamos | qué NO |
|---|---|---|---|
| `mrdoob/three.js` — ejemplos `webgl_buffergeometry_lines.html`, `webgl_lines_colors.html`, `webgl_buffergeometry_points.html` | MIT | el patrón: **una** `BufferGeometry` + **un** `LineSegments` estático, animado sólo con uniforms | `webgl_gpgpu_protoplanet.html` es GPGPU: mata 2 núcleos |
| no existe un «orbe plexus» MIT aprovechable (las búsquedas dan repos de 0–22★, muertos o en Unity) | — | se construye propio con ese patrón | no se copia arte ni código de terceros |
| `nomic-ai/gpt4all` — `gpt4all-chat/src/modellist.cpp` (`filesize`, `ramrequirements`, `quantization`, `md5sum`) | MIT | el esquema del catálogo **de la Fase 2** | — |
| `ollama/ollama` — `server/download.go` (offset + backoff), `server/images.go` `PullModel` → `{status,digest,total,completed}` | MIT | los eventos de progreso que retransmitiremos en Fase 2 | — |
| `google-ai-edge/mediapipe-samples-web` (`hand_landmarker.task` 7,82 MB + wasm 3,59 MB) | Apache-2.0 | **Fase posterior**: el vocabulario de gestos | mover ventanas de **otras apps** en Android exige `AccessibilityService`: eso es superficie privilegiada y cuesta reinstallabilidad; no entra sin decisión explícita |

---

## 3 · Qué hay hoy y por qué el orbe del video es MÁS BARATO que el nuestro

Medido en `ui/js/orb.js`:

| pieza | línea | coste |
|---|---|---|
| sprite núcleo + glow | 31–40 | 2 draw |
| **2600 partículas** con `ShaderMaterial` y profundidad de campo falsa | 43–51, 60–87 | 2600 vértices + shader por fragmento |
| halo esfera 1.02 | 91–93 | 1 draw translúcido |
| **cáscara icosaedro (1.28, detalle 3) = 1280 triángulos** con 4 ondas + Fresnel | 105–142 | el más caro: geometría + shader |
| 3 arcos toroidales | 148–161 | 3 draw |
| **plexus**: 160 nodos, umbral 0.26², **recalculado cada 3 frames** | 165–194, 478 | CPU recurrente |
| rejilla `GridHelper(16,26)` + 900 estrellas | 205–237 | 2 draw |

Total: ~10 draws, ~5000 vértices y un recálculo de aristas cada 3 frames. **El orbe de
la referencia son ~120 puntos y ~300 líneas estáticas animadas con uniforms: un orden
de magnitud más barato y, además, se parece más.** Por eso el rediseño es **quitar**, no
añadir. El freno ya existe (`html.freno`, 372–379, 487–493) y se respeta.

Riesgos conocidos que este plan respeta: el grafo de `index.html` (un import roto mata
la cara), el literal `"shell.visible = !frenoOn"` que vigila `prueba-costura.py`, los
16 canales `Paleta.java ↔ traje.js ↔ --primario/--secundario` que vigila
`prueba-colores.mjs`, y el blackout que depende de las clases `p-<hoja>`.

---

## 4 · Los pasos y su puerta

Cada paso: una sesión, un entregable, su prueba, informe PARTE E y `2.12.x`.

**1.1 · El orbe nuevo, medido y aparte** → `ui/js/orbe-plexo.js` (módulo puro con la
geometría) + `ui/sonda-orbe.html` (la página para verlo) + `scripts/prueba-orbe.mjs`.
Estados `reposo / escucha / piensa / habla` con su color, nivel de audio que lo mueve,
`pause()` y freno. *Aceptación:* 30 fps estables en el portátil de 2 núcleos, <15 % de
un núcleo, geometría precalculada **una** vez, cero recálculos por frame, prueba en
verde. **No toca `orb.js` ni `hud.css`.**

**1.2 · Color por estado y trajes** → la tabla de estados del prototipo, atada a los
canales de `traje.js` para que un atuendo siga pintando todo el orbe. *Aceptación:*
`prueba-colores.mjs` en verde y los cuatro estados distinguibles con el brillo bajo.

**1.3 · El panel de arriba** (reloj y cuadro de datos de la referencia) → placa
monoespaciada con hora, fecha, nodo (PC/teléfono), modelo que respondió y estado.
*Honestidad:* lo que no se pueda medir no se pinta (nada de `undefined`).

**1.4 · El chat transparente estilo mensajería** → **una sola** piel de burbuja (hoy hay
dos: la vieja `.u/.a` de `hud.css:201-208` y la `.gm-msgs` de `apps.css:501-503`), sin
caja, con hora corta, indicador de espera y acciones por mensaje. *Aceptación:* el
fondo se ve a través de la charla, el texto se puede seleccionar, y la hoja no
re-renderiza todo el historial por mensaje.

**1.5 · La forma de ejecutar y confirmar** → el flujo visible: petición → orbe en
escucha → piensa → **qué hizo** (chip con la acción real y su resultado) → habla →
reposo. Con estados de verdad: si algo falló, el chip lo dice.

**PUERTA DE LA FASE:** las cinco cosas funcionando en `ui/` real, `prueba-costura.py` y
`prueba-orbe.mjs` en verde, fps medidos contra `docs/linea-base.md`, y la lista
«verificar en el teléfono» confirmada por ella. Sin puerta cerrada no empieza la
Fase 2 (modelos).

---

## 4.5 · La pantalla de modelos, copiada del video y probada de verdad (2026-10-26)

**El calco.** En `vid-09` del video de referencia hay un desplegable titulado
**`Modèle:`**: una fila por modelo, el nombre a la izquierda, el actual resaltado con su
caja, y los que viven en la máquina marcados **`(Local)`** (`Ollma-1.0 (Local)`,
`Qwen2.5-Coder (Local)`…). No hay tarjetas ni párrafos: una línea, un toque. Eso es lo
que se copió en la ventana **10 · Modelos** de `ui/js/hud.js` (`moFila`) y su CSS en
`ui/css/hud.css` (`.mo-cab`, `.mo-fila`, `.mo-local`, `.mo-w`, `.mo-go`, `.mo-x`):
cabecera `MODELO: [qwen2.5:0.5b]` + ⏻ + ↻, y filas de una línea con peso, etiqueta de
RAM y la acción al final. **Pulsar la fila entera es la acción** (usar si está bajado,
↓ si no); el ✕ de borrar va aparte y pequeño, porque es lo único que no debe salir al
primer toque.

**La bajada, medida en esta máquina (no en el papel).** Se añadió `smollm2:135m` al
catálogo con su peso real, **medido con `scripts/mede-catalogo.py`: 270.898.111 B**. Bajado
desde la interfaz, pulsando su fila:

| lo que pasó | número |
|---|---|
| cortado con el ✕ de la propia fila | a **74,5 %** (201,9 de 270,9 MB), quedó un blob `-partial` de 193 MB |
| vuelto a pulsar ↓ | la barra siguió en ~74 % y terminó: **Ollama reanuda, no recomienza** |
| estado final | `listo · en el disco`, y `ollama list` lo enseña (270 MB, «18 seconds ago») |
| velocidad vista | ~3,2 MB/s sostenidos |

**Lo que se arregló para que «no se rompa a pesar de todo problema muy común»**
(`backend/app/models.py`, con su prueba en `scripts/prueba-descargas.py`):

1. **Reintento con espera creciente** (`REINTENTOS = 4`, `ESPERAS = (2,5,12,25)`). Antes
   la primera excepción marcaba `error` y moría. Como Ollama reanuda, el reintento
   continúa donde estaba; la barra no vuelve a cero.
2. **Tope de lectura** (`SILENCIO = 90`). El `timeout` viejo no tenía tope de lectura: una
   conexión muda dejaba el hilo colgado **para siempre** y bloqueaba la fila de los
   demás modelos.
3. **Cancelar manda también durante la espera**: se duerme en trocitos de 0,4 s.
4. **Techo de contexto al encender Ollama** (`OLLAMA_CONTEXT_LENGTH` con `setdefault`,
   512 en equipos de < 4 GB). MEDIDO con `smollm2:135m` y la misma frase: con los 4096
   por defecto de Ollama, **110 s y sin respuesta** (116 MB libres al final); con
   `num_ctx` 512, **respondió en 14,6 s**.

**La prueba, y que no está de adorno.** `scripts/prueba-descargas.py`: **22 comprobaciones
en 8 sectores**, stdlib puro, sin red y sin tocar `~/.ollama` (`_jala` sustituida por un
muñeco, el reloj de espera a cero). Verde. Sobre una **copia** del módulo se lanzaron dos
mutaciones para ver si muerde de verdad: quitar `SILENCIO` del `timeout` → **2** en rojo;
hacer que el bucle se rinda a la primera excepción → **7** en rojo. En el pipeline es el
paso `descargas` del trabajo `apk`.

**Lo que TODAVÍA no hace que CORT responda en local, dicho con su línea:**
`backend/app/brain.py:247-251` (`_ollama_chat`) manda la petición **sin `options`**: sin
tope de salida, el modelo escribe hasta llenar el contexto, y en 2 núcleos eso son
minutos. Con eso sin cambiar, `/api/chat` siguió cayendo a `offline` (`tardó demasiado`).
El arreglo es una línea en `brain.py`, y **no se tocó** porque la dueña lo tiene con
cambios sin commitear: se deja aquí escrito para cuando quede limpio.

**Y la condición de fondo, que no es un bug:** en este portátil, con Qoder abierto
(~800 MB), la memoria libre para cargar un modelo anda entre 100 y 500 MB según el
momento. El único momento en que el cerebro local respondió es con 213 MB libres y el
modelo ya cargado. **Ningún modelo grande va a responder aquí mientras haya que
competir por la RAM**: eso es lo que justifica los guardas de la Fase de acciones.

## 5 · Fuera de esta fase, con su sitio

- **Modelos** — adelantado a esta ronda (2026-10-26) porque la dueña lo pidió como lo
  primordial: «que CORT tenga ya cerebros y responda; luego se amplían capacidades».
  Hecho y **medido de verdad**: ver §4.5. Lo que queda de Fase 2: catálogo con
  verificación de suma (`md5`/digest), espacio por delante y cola con prioridades, y la
  hoja interactiva en el teléfono.
- **Gestos con la mano para mover ventanas**: posible en el PC (Electron + `SetWindowPos`
  / `wmctrl`); en Android sólo para ventanas **propias** vía overlay. Mover ventanas de
  otras apps cuesta `AccessibilityService` = superficie que delata el envase ante Play
  Protect. Se pide decisión antes de tocar el manifiesto.
- **Acciones por voz** (clima, alarma, calculadora, canción de alarma, guardas de RAM y
  temperatura) y **escucha proactiva**: Fase de acciones. Guardas ya investigadas:
  `psutil` (BSD-3), `nice`/`ionice` en Linux, temperatura por `/sys/class/hwmon` y
  `nvidia-smi`, batería por `/sys/class/power_supply`.
