# Créditos y licencias de `apps/web`

El holograma del reactor (`src/scene/Core.tsx`, `src/scene/Particles.tsx`) y la
cadena de post-proceso (`src/scene/Scene.tsx`) están **transplantados** de:

- **adewaskar/JARVIS** — <https://github.com/adewaskar/jarvis> — **MIT License**.
  Versión usada: la copia local de octubre de 2026.

Copiamos y adaptamos con atribución, como permite MIT y como manda la regla 9 de
`AGENTS.md`. Cambios respecto del original:

1. Paleta: de verde azulado (teal) JARVIS a azul/violeta Cortana, con acento
   magenta mientras piensa (`src/cort/palette.ts`).
2. La fuente de estado pasó de ser un store `zustand` del puente de Claude a ser
   el **WebSocket de CORT** (`services/core`): los mensajes `state` y
   `assistant_message` mueven color, giro y apertura del anillo.
3. Se quitó `uStyle` (conmutador anillo/esfera/alambre) porque no hay comando
   que lo controle aún. En el modo de fábrica todos sus factores valen 1, así que
   la imagen no cambia término a término.
4. Sin `@react-three/drei`: Core y Particles no la usan, y cada dependencia es
   espacio en el disco y memoria en un portátil de 1,8 GiB.

**No se transplantó** el `bridge/` del original: está atado al SDK de Claude, y
CORT usa su propio core en Python.

Lo pendiente de ese repo, para fases siguientes: `src/scene/Orbits.tsx` (anillos
giroscópicos), `src/ui/Blades.tsx` (paneles del HUD), `src/lib/hands.ts` (gestos
MediaPipe) y el pipeline de voz (`vad`, `kokoro`, Porcupine).
