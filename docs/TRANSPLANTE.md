# Transplante: qué se lleva CORT de cada referencia, y cómo se lleva

Documento de decisión. Nace del pedido de Sandra (10-oct): que las ventanas de
vidrio y la cara funcionen «como el JARVIS de jaredrhod» — algo integrado, que
vive en la pantalla y reacciona solo —, con el avatar de Cortana como meta
estética, usando los modelos VRM propios. Aquí está lo que aprendimos leyendo
los repos citados, qué se trasplanta de cada uno, a qué incremento va cada
pieza, y qué **no** se trasplanta nunca.

Los repos de estudio viven fuera del repo de CORT (clones temporales); `upstream/`
queda para los que se persigan a largo plazo. Regla 9 de AGENTS.md: se estudian,
se respeta la licencia, se reescribe lo que no tenga licencia clara.

## La ley, repo por repo

| Repo | Licencia | Qué permite | Qué se hace aquí |
|---|---|---|---|
| `jaredrhod/ai-visualizer` | **AGPL-3.0** | Cero líneas copiadas si CORT no quiere volverse AGPL | Se transplanta **arquitectura y gramática de estados**, reescrita desde cero |
| `jaredrhod/fullstack-agent`, `barehands`, `backtalk` | **AGPL-3.0** | Ídem | Ideas ya minadas (el arrastre con «manos» vino de ahí como gesto, no como código) |
| `adewaskar/jarvis` | **MIT** | Reuso real de código con atribución | Se pueden **puertar** piezas: VAD, clap-to-wake, mapa de colores de fase, variantes de llegada de paneles |

De hecho ya ocurrió un trasplante MIT: `cort/arrastre.ts` (filtro one-euro y
sujeción de arrastre) vino del `Blades.tsx` de `barehands` con atribución en su
encabezado. Ese es el molde.

## jaredrhod/ai-visualizer — el salvapantallas que mira de vuelta

Es el proyecto de los videos: un `server.py` de stdlib (cero dependencias,
ancla en `127.0.0.1`, «ya está corriendo no es un error»), un navegador a
pantalla completa sin cursor, y una carpeta `faces/` donde cada subcarpeta con
`index.html` es una cara nueva que aparece sola en la galería. El sistema
nervioso son **tres archivos diminutos** que el agente escribe
(`.voice_state`, `.voice_waveform`, `.voice_loading_pid`) y la cara lee a ~8 Hz
por `/state`. Nada de WebSocket: el bus es el sistema de archivos.

Lo que vale la pena entender de su diseño, y CORT reescribe:

1. **La gramática de estados.** Cuatro fases (`idle / listening / thinking /
   speaking`) más `alert`. Cada fase cambia a la vez brillo base, tinte de
   color, velocidad de deriva, tráfico de partículas y qué regiones están
   calientes. La regla de diseño declarada en el código: los estados tienen que
   leerse *desde el otro lado de la habitación*, no sólo ser distintos en la
   matemática.
2. **La envoltura de voz adaptativa.** El nivel de habla no es un sí/no: es un
   ataque rápido (~50 ms) y una caída lenta (~350 ms) perseguidos contra un pico
   que decae. La frase del autor que resume el truco: *«a fresh waveform IS
   speech, whatever the state file says»* — si hay waveform reciente, habla,
   aunque el estado diga otra cosa.
3. **La regla del bloom.** Todo lo que emite luz se dibuja en UN solo lienzo de
   campo y el campo entero pasa por el bloom (dos reducciones escaladas,
   composición `lighter`). Así ninguna línea se ve a lápiz. CORT ya persigue
   algo parecido con `target` + lerp por frame en la escena.
4. **`BRIGHT_CAP`**: el color nunca se recorta a blanco; lo blanco es un color
   más, reservado al elemento protagonista (la media luna). En CORT: el alto
   brillante del atuendo, y solo el magenta de esfuerzo puede tocarlo.
5. **La filosofía de salvapantallas.** La cara vive en pantalla completa, sin
   cursor, y *no pide que la abran*: llueve, respira, y sólo «mira» cuando el
   código del agente le escribe un estado. Esto es lo que Sandra describió como
   «el salva-pantallas ya integrado». En la web de hoy se puede lograr la parte
   honesta: **modo sala** (N10). Lo que la web no puede: flotar sobre otras
   ventanas ni sobrevivir a la suspensión — eso es caparazón nativo (N12).

## adewaskar/jarvis — MIT, y por tanto sí se copia (con crédito)

Un asistente de escritorio con escena 3D + HUD 2D compartiendo un único store.
Piezas concretas que CORT puerta o puertará:

1. **`store.ts` — la fase como unión con color.** `Phase = 'boot' | 'offline' |
   'listening' | 'thinking' | 'speaking' | …` con un `phaseColor` compartido por
   la escena 3D *y* el HUD 2D: un solo lugar donde la fase decide su color, así
   el orbe y el punto del cabezal jamás discrepan. **N9.** Colores: el mapa de
   él (`listening #19d8d2`, `thinking #f0a93c`, `speaking #3ef2a8`) no se copia
   tal cual — la paleta de CORT es Cortana y manda `palette.ts` —, pero la
   **estructura** (fase → color centralizado) sí es suya.
2. **El efecto como evento con marca de tiempo.** «An effect is an event, not a
   state, but it has to travel through a state store»: `{ kind, at }`. CORT ya
   lo tiene (`Snapshot.effect = { kind, at }`); la coincidencia confirma el
   patrón y se cita.
3. **`Panels.tsx` — variantes de llegada.** Cinco formas de aparecer un panel
   (`materialise / sweep / unfold / stagger / snap`), todas con blur de entrada,
   escala y un ligero rebote elástico; en móvil degrada a fundido simple. Las
   ventanas de vidrio de CORT hoy entran sin ceremonia. **N9 lo mínimo (un
   materializar) y opcionalmente más fino después.**
4. **`vad.ts` — escucha local sin el servicio del navegador.** El encabezado
   explica por qué existe: el `SpeechRecognition` de Chrome/Edge «muere en
   silencio bajo uso siempre-abierto». Su VAD es energía pura: piso de ruido
   como media móvil, umbral con histéresis, *barge-in* (interrumpe hablando), y
   un `setGuard` que sube el umbral mientras el TTS habla para no oírse a sí
   mismo. **N11** — puerte directo con atribución (MIT).
5. **`clap.ts` — aplaudir para despertarlo.** Detección de forma de onda:
   silencio previo + subida casi instantánea (7× sobre el piso) + caída rápida,
   con mínimo de amplitud. Un gesto que no necesita modelo. **N11.**
6. **`kokoro.ts` + `start.mjs` — TTS local y WASM en el repo, no en CDN.**
   Kokoro por WebGPU (~86 MB) con repliegue a la voz del navegador; el arrancador baja
   los `.wasm` de MediaPipe **a disco** en vez de un CDN, porque «un agente de
   escritorio no puede depender de que Google esté arriba». Nota futura para
   los VRM: three-vrm y sus pesos deben vivir en el repo, no en unpkg.
7. **Lo que NO se puerta:** `chrome.mjs` — maneja el navegador real por
   native-messaging. Choca de frente con la regla 6 de AGENTS.md (nunca comandos
   arbitrarios del usuario o del LLM; toda acción de sistema pasa por capa de
   permisos). Queda fuera a propósito.

## La Cortana de «What if» y los VRM

La imagen de referencia (@hal9_mc): figura translúcida, la luz azul la atraviesa
— se distinguen el pelo y la ropa como un vidrio esmerilado —, de pie sobre un
pedestal, materializándose en vez de aparecer. Traducción a CORT:

- El avatar VRM se pinta en la **capa que ya existe** (`target.visible` apaga el
  orbe cuando el avatar toma la escena; el core no se entera y no debe).
- «Translúcida» = el material del VRM con emisión azul + alfa por shader, no un
  filtro de imagen. Se mide en el A16 antes de prometer (fila sin verificar).
- Materializarse = la variante `materialise` del punto 3 de arriba aplicada al
  avatar: subir de 0 alfa con overshoot, no un `display: block`.
- Pedestal = un anillo de `Core.tsx` reutilizado bajo los pies; cero meshes
  nuevos si la escena lo evita.

## Increments que salen de este análisis

| # | Nombre | Fuente | Licencia | Estado |
|---|---|---|---|---|
| **N9** | Máquina de fases en la cara (`cort/fase.ts`, punto de fase, reacción del reactor, llegada de ventanas) | gramática de estados de ai-visualizer + `store.ts`/`Panels.tsx` de adewaskar | reescrito + MIT con crédito | **hecha y medida 2026-10-10 (madrugada) — función 84** |
| **N10** | Modo sala: `F` pantalla completa, cursor oculto, atenuado por inactividad, despertar con gesto | filosofía de salvapantallas de ai-visualizer | idea reescrita | plan |
| **N11** | Escucha local: VAD de energía + aplauso para despertar | `vad.ts` + `clap.ts` de adewaskar | MIT, puertado con atribución | plan |
| **N12** | Caparazón nativo (Tauri): autostart, orbe siempre-encima, respuesta real en suspensión | el «integrado al SO» que la web no puede dar | — (honestidad: es el único camino) | se construye en la PC de Askher |

N9 no toca el protocolo WebSocket (regla 5 intacta): el core ya transmite
`thinking`; el micrófono y el TTS los sabe `Voz.tsx` desde dentro. La fase es,
por ahora, un hecho **de la página**, no del cable.

Orden dentro del núcleo: N9 → N2 → N3 → N10 → N5; N11 y N12 cuando el A16 y la
PC de Askher estén en el bucle.
