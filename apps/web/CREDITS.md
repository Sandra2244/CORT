# Créditos y licencias de `apps/web`

El holograma del reactor (`src/scene/Core.tsx`, `src/scene/Particles.tsx`), la
cadena de post-proceso (`src/scene/Scene.tsx`), la capa de efectos de un solo
disparo (`src/ui/Effects.tsx`, con sus keyframes en `src/index.css`), el filtro de
suavizado (`src/lib/oneEuro.ts`) y el patrón de arrastre de paneles
(`src/cort/arrastre.ts`) están **transplantados** de:

- **adewaskar/JARVIS** — <https://github.com/adewaskar/jarvis> — **MIT License**.
  Versión usada: la copia local de octubre de 2026.

Copiamos y adaptamos con atribución, como permite MIT y como manda la regla 9 de
`AGENTS.md`. Cambios respecto del original:

1. Paleta: de verde azulado (teal) JARVIS a azul/violeta Cortana, con acento
   magenta mientras piensa (`src/cort/palette.ts`).
2. La fuente de estado pasó de ser un store `zustand` del puente de Claude a ser
   el **WebSocket de CORT** (`services/core`): los mensajes `state` y
   `assistant_message` mueven color, giro y apertura del anillo, y el mensaje
   `effect` dispara las animaciones de un solo tiro. El original alimenta esa
   misma pareja `{kind, at}` desde el puente; aquí la emite el core.
3. Se quitó `uStyle` (conmutador anillo/esfera/alambre) porque no hay comando
   que lo controle aún. En el modo de fábrica todos sus factores valen 1, así que
   la imagen no cambia término a término.
4. Sin `@react-three/drei`: Core y Particles no la usan, y cada dependencia es
   espacio en el disco y memoria en un portátil de 1,8 GiB.

**No se transplantó** el `bridge/` del original: está atado al SDK de Claude, y
CORT usa su propio core en Python.

Tampoco `src/scene/Orbits.tsx`, y no por pereza: es una bandeja que hace orbitar
**imágenes** que JARVIS va capturando, y depende de un bridge HTTP que las sirva
desde disco. CORT no produce ninguna imagen todavía, así que su lista estaría
siempre vacía y el módulo sería código muerto hasta que exista un productor.

## Los dos módulos de octubre (táctil y suavizado)

**`src/lib/oneEuro.ts`** — copia de `src/lib/oneEuro.ts` del original, con el
comentario del algoritmo y los guardas de periodo de muestra intactos. Cambios:
la cabecera de procedencia en español, y fuera `OneEuroPoint` (un filtro por eje),
que en CORT no suaviza todavía ninguna posición 2D. El original lo usa para el
cursor de la mano; aquí alimenta la señal de enfoque de `src/cort/defocus.ts`, y
los parámetros se barrieron y midieron en vez de heredarse (`CORTE_REPOSO`,
`APERTURA`), porque una webcam temblando es ruido de alta frecuencia y ése es
justo el caso en el que este filtro abre el corte de más.

**`src/cort/arrastre.ts`** — el patrón de `onPointerDown`/`grab` de
`src/ui/Blades.tsx` del original: escuchar en `window` y no en el asa, limpiar los
tres escuchadores al soltar, ignorar los pulsados que caen sobre un botón. Lo que
el original no tiene y aquí hace falta: **topes**. Sus blades son paneles de
contenido que se abren y se cierran; el HUD de CORT es la única puerta a los
mensajes y un panel arrastrado fuera de la pantalla no se puede volver a agarrar.
De ahí `sujetar()` y el botón de recolocar.

No se trajo de `Blades.tsx` nada de su contenido: los `iframe` proxyados por el
bridge, el reproductor de YouTube/Vimeo con su lista cerrada de hosts, el
sanitizador de HTML ni la pantalla de la cámara. CORT no muestra páginas web, y
esa parte depende del `bridge/` que sí se descartó arriba.

Lo pendiente de ese repo, para fases siguientes: `src/lib/hands.ts` (gestos
MediaPipe — inviable en 2 núcleos y 1,8 GiB, ver `docs/STATUS.md`), el pipeline de
voz (`vad`, `kokoro`, Porcupine) y `src/ui/{Panels,Suggestions,Ignition,Boot}.tsx`.

De los repos de **jaredrhod** (`barehands`, `ai-visualizer`, `fullstack-agent`),
que son **AGPL-3.0**, no se copió ninguna línea: de ahí viene la idea de que los
paneles se puedan arrastrar y apilar, y nada de código. La distinción es la regla 9
de `AGENTS.md`, no un detalle de estilo — copiar código AGPL obligaría a publicar
CORT bajo AGPL.

## N9 — la máquina de fases (madrugada del 2026-10-10)

Dos procedencias distintas, y por eso se dicen aparte:

**`src/cort/fase.ts`** — **idea AGPL reescrita, cero líneas copiadas.** La
gramática `idle / listening / thinking / speaking` del `ai-visualizer` de
jaredrhod y su regla de que cada estado se lea «desde el otro lado de la
habitación». El archivo se escribió desde cero en español con otra prioridad
deliberada (habla > piensa > escucha; la referencia no mezcla micrófono y TTS
porque su estado viene de un solo emisor) y otra fuente de señales (aquí `core`
llega por WebSocket y `micro`/`tts` los declara la propia página). El análisis
completo, licencia por licencia, está en `docs/TRANSPLANTE.md`.

**`src/index.css` (bloques `.dot.fase-*` y `@keyframes materialise`) y la
estructura de `fase.ts`** — **copiadas y adaptadas de adewaskar/JARVIS (MIT)**,
como permite la licencia y como manda la regla 9:

1. Los dos colores de fase (`listening #19d8d2` → `escucha`, `speaking #3ef2a8`
   → `habla`) salen del `phaseColor` de su `store.ts`. Para «piensa» **no** se
   copió su ámbar `#f0a93c`: reñiría con la paleta Cortana que manda en
   `palette.ts`, y ahí sigue el magenta de esfuerzo `#ff5ce0` que ya estaba.
2. La llegada `materialise` de las ventanas y el menú es su variante de
   `Panels.tsx`, reducida a una sola de las cinco que él ofrece (las otras
   cuatro piden una gramática de gestos que aquí aún no existe) y con relleno
   `backwards` en vez de `both`: con `both` el `transform` del keyframe se queda
   clavado y anularía al del arrastre, un fallo que el original no puede tener
   porque sus paneles no se mueven con el keyframe activo.
3. La idea estructural del `store.ts` —tres señales crudas → una fase → un
   color decidido en **un solo lugar**, compartido por la escena 3D y el HUD—
   es suya; la implementación (`señales`, `sincronizarFase`, `pintarFase` en
   `connection.ts`) es de aquí.

## N13 — la bandeja viva (2026-10-11)

**`src/cort/hora.ts`, los bloques `.hud-cab`/`.hud-reloj`/`.cuerpo::before`/
`.enviar`/`.hud-pie` de `src/index.css` y el `Hud.tsx` nuevo** — **cero líneas
copiadas.** La referencia es la **demo web en vivo de Tech Enclair J.A.R.V.I.S.**
(`github.com/mirasandalucia/TechEnClair`), cuya licencia se declaró **no
estándar**: su propio aviso dice «100 % open-source» y a la vez «reventa
estrictamente prohibida», y esa condición comercial no es MIT ni Apache ni GPL.
La regla 9 de `AGENTS.md` manda reescribir lo que no tenga licencia clara, así
que de su interfaz no viaja expresión protegida alguna — sólo la **gramática
visual**, que no es copyright (una barra con un reloj y unos corchetes no es
una obra copiable), rehecha aquí con nuestros colores y nuestro idioma:

1. La **barra de mando** (`.hud-cab`): su demo pone fase/reloj `HH:MM:SS`/
   `SYS_CLOCK`/`ONLINE` en la cabecera; aquí la fase sale de `cort/fase.ts`
   (N9) con sus tres colores, la hora de `cort/hora.ts`, y el chip de red es el
   `online` del `Snapshot`. Ninguno de esos datos es decorativo: todos son
   ciertos.
2. Las **filas etiquetadas** (`.quien`): sus burbujas `eco-msg` distinguen la
   voz de la usuaria de la del asistente; aquí cada `<p>` lleva `cort`/`tú` en
   monoespaciada, y `remitente` cae al lado de CORT ante un origen desconocido.
3. Los **corchetes de marco** (`.cuerpo::before/::after`) y el **botón circular
   de envío** (`.enviar`, 46 px) imitan el *lenguaje* —esquina marcada, diana
   redonda—, no sus píxeles: grosores, radios y colores son de esta paleta.

El reloj de la bandeja se formatea **a mano** (`padStart`), sin
`toLocaleTimeString`, para que el formato sea fijo y las 7 pruebas de
`hora.test.mjs` no mientan según el `locale` de la máquina. Y su `setInterval`
sólo vive mientras la bandeja está abierta: en reposo, cero temporizadores.

## CARETA v2 fase A — la pantalla entera es el HUD (2026-10-11)

Tres diferencias respecto a la demo en vivo de Tech Enclair, que es la
referencia que inspiró la cockpit (barra superior, reloj gigante, corchetes de
marco). De su proyecto **no viaja ni una línea**: su licencia no es estándar
(«open source» + reventa prohibida) y la regla 9 del repo manda reescribir.

1. La **barra** de CORT no pinta un estado inventado: la fase la resuelve
   `cort/fase.ts` sobre señales reales (micro/tts/thinking), el `hh:mm:ss`
   sale de `cort/hora.ts` —formateado a mano, probado— y el chip de red es
   `snapshot.online`, el estado del WebSocket.
2. El **riel** izquierdo no es un menú nuevo: llama a `alternar`/`toggleMenu`
   de la pila pura `cort/ventanas.ts`, la misma que mueven las teclas `1`–`5`.
3. El **telón** no finge carga (regla 11): se levanta con la conexión real o a
   los 2,5 s, con el pie «núcleo local · en tu máquina». `?telon=lento` (×100)
   es sólo para poder verificarlo.
