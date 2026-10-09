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
