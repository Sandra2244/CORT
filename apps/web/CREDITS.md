# Créditos y licencias de `apps/web`

El holograma del reactor (`src/scene/Core.tsx`, `src/scene/Particles.tsx`), la
cadena de post-proceso (`src/scene/Scene.tsx`) y la capa de efectos de un solo
disparo (`src/ui/Effects.tsx`, con sus keyframes en `src/index.css`) están
**transplantados** de:

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

Lo pendiente de ese repo, para fases siguientes: `src/ui/Blades.tsx` (paneles del
HUD), `src/lib/hands.ts` (gestos MediaPipe) y el pipeline de voz (`vad`,
`kokoro`, Porcupine).
