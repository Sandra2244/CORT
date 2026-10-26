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
**HECHO el 2026-10-26** — con una decisión que no estaba en el plan y que hay que leer
antes de tocar nada: el matiz del estado es fijo y el atuendo sólo modula saturación,
luz y el reposo. Ver §4.6.

**1.3 · El panel de arriba** (reloj y cuadro de datos de la referencia) → placa
monoespaciada con hora, fecha, nodo (PC/teléfono), modelo que respondió y estado.
*Honestidad:* lo que no se pueda medir no se pinta (nada de `undefined`).

**1.4 · El chat transparente estilo mensajería** → **una sola** piel de burbuja (hoy hay
dos: la vieja `.u/.a` de `hud.css:201-208` y la `.gm-msgs` de `apps.css:501-503`), sin
caja, con hora corta, indicador de espera y acciones por mensaje. *Aceptación:* el
fondo se ve a través de la charla, el texto se puede seleccionar, y la hoja no
re-renderiza todo el historial por mensaje.
**HECHO el 2026-10-26, ronda 2.15.0** — pero con dos decisiones que cambiaron el
enunciado y que hay que leer antes de tocar `jarvis.css`: **no se unificaron las dos
pieles**, se cubrió la de siempre con una capa reversible (`ui/css/jarvis.css`, atada a
`html.manto-jarvis`), y **el orbe sí vuelve a estar detrás de la charla**, que es lo que
sale en el video de referencia y lo contrario de lo que estaba vigente desde el 22/10.
Ver §4.7.

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

## 4.6 · El paso 1.2: el atuendo pinta los cinco estados (2026-10-26, ronda 2.14.0)

**Lo que se pidió.** Que el orbe del prototipo no llevara sus colores escritos a mano:
los cinco estados tienen que salir de `ui/js/traje.js`, que es el módulo que mide
`scripts/prueba-colores.mjs`. Y que al cambiar de atuendo cambie el orbe **entero**, que
es la prueba decisiva de F17.

**La tensión, que es lo único interesante del paso.** El color ES el estado (cian al
oír, turquesa al pensar, lima al hablar, rojo al fallar: eso lo dice el video), pero el
atuendo también tiene que pintar el orbe. Si las dos cosas se dejan en la misma mano, la
segunda le roba a la primera.

**Primer borrador, y lo que midió.** El estado bebía su saturación y su luz del traje.
`prueba-colores.mjs` [6] —que exige que los cinco estados se distingan entre sí, no sólo
del de fábrica— lo reventó con **6 rojos**: con `Neutron` (un gris casi blanco,
`#e8eef2`) el par `escucha/piensa` medía **2,8** de distancia en el cubo RGB. Cinco
estados que se leían como uno solo. Sin la prueba, esto habría salido «bonito» en la
sonda y roto en el teléfono.

**Segundo borrador, el reparto que quedó.**

| parte del color | de quién es | por qué |
|---|---|---|
| el **matiz** (197° / 164° / 100° / rojo) | del **estado**, fijo | es el idioma; con JARVIS «hablar» sigue siendo lima |
| la **saturación y la luz** | del estado, **moduladas** hasta un 38 % por el traje | un traje apagado tiene que notarse, pero nunca apagar el indicador |
| el **reposo** | entero del traje (matiz y saturación de la mezcla de los dos colores, luz del primario) | en reposo no hay mensaje que dar |
| el **error** | rojo fijo `#ff5b6e` en los seis atuendos | una alarma que cambia con el fondo deja de ser alarma |

Con eso, y con el `sube` de cada estado (cada uno sube o baja su luz respecto a la del
atuendo: `escucha +.08`, `piensa −.07`, `habla +.02`), el peor par de los seis trajes
pasa de **2,8 a 65,3**. Los números, medidos:

| traje | peor par (distancia RGB) |
|---|---|
| Cortana | 105,1 (`reposo/escucha`) |
| JARVIS | 105,1 · Siri 107,0 · Matrix 91,3 · Atardecer 105,5 |
| Neutron | **65,3** (`escucha/piensa`) ← el que mandaba |

Y el ancla con el video sigue viva con el traje de fábrica: `escucha.b = #59cffe` a
**34,6** del `#39c2ff` leído en los fotogramas, `habla.b = #83fd46` a **9,4** del
`#7dff3f`. El umbral de la prueba son 60.

**Lo que hace el orbe con esa tabla.** `creaOrbe(THREE, {traje:[p,s]})` nace vestido y
`vestir(p, s)` cambia el atuendo **en caliente**: reescribe la tabla, vuelve a pedir el
estado puesto y deja que `pinta` interpole el color (≈20 % por frame a 30 fps). No
reconstruye la geometría, no salta a `reposo` y no da un bote de color. Un color roto
que llega del traje cae al de fábrica en vez de apagar la cara.

**Pruebas.** `prueba-colores.mjs` pasó de 28 a **51 comprobaciones** (sector [6] nuevo)
y `prueba-orbe.mjs` de 55 a **67** (sector [7] nuevo: vestir sin reconstruir). Las dos
en verde. **Y se comprobaron que no son de adorno, con seis mutaciones sobre una copia
del par de módulos:**

| mutación | rojos que saca |
|---|---|
| el matiz de `habla` sigue al traje (h=0) | **5** en `prueba-colores` (`habla/error` a 34-43 en cuatro trajes + el ancla del video a 225) |
| quitar la separación de luz (`sube` a 0) | **1**: Neutron `escucha/piensa` a 40,9 |
| el color salta al vestir (`mez = 1`) | **1**: «se ACERCA, no salta» |
| `vestir` olvida reescribir el destino | **2** |
| el error se pinta con el traje | **1**: «el error sigue siendo rojo con Matrix» |
| un `#hex` de estado escrito a mano en `orbe-plexo.js` | **1**: el candado del sector [7] |

**Lo que NO hace esta ronda:** no toca `orb.js`, `hud.css` ni `apps.css`, y no integra
nada en `ui/index.html`. Falta su aprobación a ojo (`ui/sonda-orbe.html`, que ahora tiene
los seis atuendos tocables con su chip de color) antes de mover un píxel de la cara real.

## 4.7 · El paso 1.4: el manto JARVIS, y por qué es una CAPA (2026-10-26, ronda 2.15.0)

**Lo que se pidió.** «empiezas por el chat se tiene que parecer al del video», dicho el
26/10 junto a los tres videos nuevos (la lectura está en `docs/REFERENCIAS-VIDEOS-JARVIS.md`).
El enunciado del plan decía otra cosa: *una sola piel de burbuja*, unificando la vieja
`.u/.a` (`hud.css:201-208`) con la `.gm-msgs` (`apps.css:501-503`). **No se hizo así**, y
hay que leer el porqué antes de tocar `jarvis.css`.

**La referencia, leída del fotograma y no de la memoria.** `docs/referencias/v1-charla-096.jpg`
(marco 96 s del video 1) enseña: nombre arriba con su «connecté» y su punto verde; dos
iconos redondos a la derecha; **lo tuyo en una pastilla de color** (coral en el video);
**lo del asistente como texto suelto, sin caja, alineado a la izquierda**; y STOP + micrófono
abajo. Copiamos la estructura (jerarquía, pastilla propia, respuesta desnuda, barra abajo)
y **no copiamos el coral**: el acento de CORT lo manda `apps/apk/src/com/cort/ia/Paleta.java`,
que son los seis atuendos. Un coral literal en la capa dejaría el manto fijo para siempre
y mataría el trabajo del paso 1.2. La cuenta de la capa, medida: `ui/css/jarvis.css` tiene
**124 líneas y 40 reglas**, y las cuarenta cuelgan de `html.manto-jarvis`; el único color
fijo que se permite es la tinta (`#02040a`, `#05131d`, `#9fb4c8`, `#cfe0f2`, `#eef4fb`,
`#f2f6fb`) y el ámbar de aviso `#ffcf6b`.

**Decisión 1 · una capa reversible encima de la Charla de siempre.** `ponManto()`
(`pantallas.js:658`) pone o quita la clase, se guarda en `localStorage` bajo
`cort-manto` (`'jarvis'` / `'viejo'`, y por defecto el manto puesto) y avisa a `hud.js`
con el evento `cort-manto`. `apps.css` no se tocó —y `prueba-manto.mjs` [7] lo vigila:
«`apps.css` no sabe nada del manto (es una capa, no una remodelación)». El motivo no es
estético: ella va a estar **días comparando las dos caras**, y si la nueva se hiciera
borrando la vieja, no habría vuelta atrás con un toque ni comparación posible.

**Decisión 2 · el orbe SÍ vuelve a estar detrás de la charla**, que es lo que sale en el
video y lo contrario de lo vigente desde el 22/10. No se quitó el apagón de
`hud.css:730-737` (ese regla protege las otras siete hojas); se le **ganó en rango**, y eso
se puede medir:

| regla | selectores | especificidad |
|---|---|---|
| el apagón | `html.pantallas-montadas:not(.p-orbe) #scene` | (1,2,1) = **121** |
| el manto | `html.pantallas-montadas.p-charla.manto-jarvis #scene` | (1,3,1) = **131** |

Con `:not()` contado **como lo cuenta el navegador** —suma lo de adentro, no se suma a sí
misma—, y con `display:block!important` en las dos. Hace falta el `!important` **y** la
especificidad: con los dos `!important` empatados gana el orden del archivo, y el manto va
el último a propósito (`index.html` enlaza `jarvis.css` después de `hud.css` y `apps.css`),
pero esa baza no se puede jugar dos veces: la regla del apagón (`hud.css:730-737`) apaga el
orbe **y trece cosas más del HUD** en las otras siete hojas, así que quitarla o
estrecharla era tocar las siete pantallas por arreglar una. Se ganó por rango, que es lo
que se puede comprobar con una cuenta, y no por orden de llegada.

Y el orbe detras de la charla cuesta: `hud.js:2206-2208` decide con `orbeDetras(pantalla)`,
que sólo enciende el bucle WebGL en `orbe` y en `charla` **con el manto puesto**; al quitarlo
se congela otra vez. En un teléfono de gama media un WebGL que nadie ve es CPU, RAM y batería.

**La respuesta «semi corta pero medida».** `FRASE_JARVIS` (`pantallas.js:651`) va
**DENTRO del mensaje** porque `POST /api/chat` (`backend/app/main.py:116`) sólo acepta
`{message}`: no hay campo de instrucciones. Y sólo se cuela con el manto puesto **y** el
modo `Normal`: si ella eligió un modo (Explícame, Resume…), manda el modo. Las dos
condiciones están candadas en el sector [5] de la prueba.

**Lo que hubo que arreglar en la cara real para cumplir las aceptaciones.** Cuatro cosas,
y ninguna se veía leyendo el CSS:

1. **«la hoja no re-renderiza todo el historial por mensaje»** — no se cumplía. Ahora
   `pintaCharla(nuevo)` lleva la cuenta `chPintadas` y una guarda doble (que el contador
   bata con la lista **y** que el DOM tenga exactamente las burbujas esperadas, excluida la
   de «pensando»); si algo no cuadra, se rehace entera, que es lo seguro. Entre cada
   `mensajes.push` y su pintura hay de **80 a 803 caracteres** (un `try`, un `fetch` y
   seis líneas de estado), dato que sirve más abajo.
2. **la burbuja de «pensando» es una señal, no un mensaje**: se pone y se quita sin entrar
   en la lista. Si hubiera entrado, dos respuestas seguidas dejarían dos indicadores colgados.
3. **«el texto se puede seleccionar»** — no se cumplía en el teléfono: `html.mobile …
   user-select:none` (`hud.css:411-417`) se comía la charla. La regla que devuelve la
   selección ya existía para `.scr-lista` (`hud.css:417`); lo que faltaba era **la clase**
   en la caja, y se puso en el marcado de `pantallas.js:552`. `hud.css` no se tocó.
4. **la píldora de «con qué se piensa» mentía en tres sitios**, y eso es lo que la casa
   prohíbe de forma expresa. Había **cinco escrituras a mano** de `#gm-usando` (en el envío,
   en el «sin núcleo», en la caída del núcleo, en la respuesta del teléfono y en `reciboMente`)
   compitiendo con `pintaUsandoCharla()`, que se llamaba justo después desde `pintaCharla`:

   | lo que pasaba | lo que se leía |
   |---|---|
   | respuesta de un núcleo apagado | burbuja «El núcleo de CORT no responde…» y píldora **«usando el modelo del núcleo»** |
   | ella pulsó parar | **«usando el modelo del núcleo»**, cuando nadie usó nada |
   | la respuesta llegó DESPUÉS de parar (lo que la píldora promete) | «nadie contestó a esa pregunta» pintado **encima de una respuesta que sí estaba en la pantalla** |

   El arreglo es una **fuente única de verdad**: la píldora la escribe un solo sitio, y
   sale del final de la conversación —`chPensando`, `chCortada`, y la `nota` que lleva
   puesta cada burbuja de CORT desde que se creó (`sin núcleo`, `el núcleo se cayó`,
   `llama-3.1 · cerebro local`, `cerebro del teléfono · local`). Los dos primeros estados
   se cazaron en el navegador con captura de pantalla; el tercero salió al leer el camino
   del teléfono.

**Las diez lecturas de la píldora, ejecutadas sobre la función real del archivo** (recortada
de `pantallas.js` y llamada con un `document` de pega; en esta sesión la herramienta de
navegador no estaba disponible, así que **no hay captura nueva** — la aprobación a ojo
sigue pendiente):

| estado de la charla | lo que dice `#gm-usando` |
|---|---|
| nada dicho todavía | **usando el modelo del núcleo** · modo Normal |
| esperando al núcleo | **pensando…** · modo Normal |
| esperando al teléfono | **el cerebro del teléfono** · modo Normal |
| respondió sin núcleo | **sin núcleo** · modo Normal |
| el núcleo se cayó a media respuesta | **el núcleo se cayó** · modo Normal |
| respuesta normal | **llama-3.1 · cerebro local** · modo Normal |
| cortó la espera y nadie contestó | **espera cortada** · nadie contestó a esa pregunta |
| cortó, pero la respuesta llegó tarde | **cerebro del teléfono · local** · modo Normal |
| pregunta nueva después de una cortada | **pensando…** · modo Normal |

**Pruebas.** `scripts/prueba-manto.mjs`, ocho sectores y **35 comprobaciones en verde**,
montada en `build.yml` (paso `id: manto`, con anotación `::error::` si falla). Para que no
sea decorativa se rompieron los archivos reales **catorce veces** —cinco de `jarvis.css`,
una de `hud.js` y ocho del camino de la charla en `pantallas.js`—, con respaldo y
restauración verificada byte a byte; la base daba 0 rojos y cada mutación sacó su rojo:

| mutación | rojos |
|---|---|
| una regla del manto sin su clase (tiñe todas las hojas) | 1 |
| copiado el coral de la referencia | 1 |
| el orbe levantado en todas las pantallas | **2** |
| el orbe levantado sin más especificidad que el apagón | 1 |
| un `!important` de más, fuera del orbe | 1 |
| la frase de medida mandada sin el manto | 1 |
| la frase de medida encima del modo elegido | 1 |
| el orbe vivo en todas las pantallas (`hud.js`) | 1 |
| una píldora escrita a mano de nuevo | 1 |
| una burbuja de CORT sin su `nota` | 1 |
| la pintora que deja de leer la `nota` | 1 |
| la espera cortada atada sólo a la bandera | **2** |
| rehacer la charla entera por mensaje | 1 |
| un `mensajes.push` sin su repaint | 1 |

La última no mordía al primer intento, y es la lección del sector [8]: buscar «la siguiente
`pintaCharla(`» hacia adelante en el archivo hacía que un `push` **sin** pintura encontrara
la de la función de enfrente (la distancia real llega a 803 caracteres) y diera por buena la
callejón sin salida. La comprobación ahora corta por el inicio de la siguiente función.

**Lo que NO hace esta ronda.** No unificó las dos pieles de burbuja (decisión arriba), no
tocó `orb.js` ni `apps.css` ni `hud.css` más que en una línea de `user-select`, no metió
permiso ni servicio nuevo en el manifiesto, no saca nada a la nube, y no tocó `brain.py`,
`pool.py` ni los `.java` de Android. `prueba-costura.py` sigue con **una sola roja y es
suya**: la burbuja 1.1.4 de `Flotante.java`, sin commitear. Las otras suites de la cara:
colores **51**, orbe **67**, manto **35**, descargas en verde.

## 5 · Fuera de esta fase, con su sitio

- **La superficie `chat` única** — pedida por la dueña el 2026-10-26 en el mismo mensaje
  que arrancó esta ronda: quitar los apartados y dejar **una** pantalla que se llame
  `chat`, semi-negra transparente estilo JARVIS, con la barra de tres símbolos pegados
  (historial · modo · ajustes), modelos locales y en línea con sus claves API, y las
  funciones de copiloto. Está **planificado aparte y sin código**, en
  `docs/PLAN-CHAT-UNICO.md`, con las cinco preguntas que tiene que cerrar ella antes de
  que se desmonte ninguna ventana. Lo que sí toca de esta fase: el paso 1.2 (el atuendo)
  entra por ahí, y el paso 1.4 (el chat transparente) es un trozo de C1/C2 de ese plan.
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
