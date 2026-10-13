/**
 * Paleta de CORT: azul y violeta de Cortana (Halo), con un acento magenta que
 * solo aparece cuando el reactor está esforzándose.
 *
 * Cada atuendo define su color de núcleo y su alto brillante; el resto de la
 * escena no decide colores por su cuenta, para que HUD y orbe nunca discrepen.
 */

export type Outfit = 'night' | 'hoodie' | 'light' | 'work' | 'casual'

export const palette: Record<Outfit, { core: string; hot: string; ui: string }> = {
  night:  { core: '#8f5cff', hot: '#e7d6ff', ui: '#a479ff' },
  hoodie: { core: '#4f8dff', hot: '#d6e9ff', ui: '#6ea0ff' },
  light:  { core: '#6f7cff', hot: '#dfe2ff', ui: '#8b96ff' },
  work:   { core: '#5c8dff', hot: '#dbe6ff', ui: '#7aa6ff' },
  casual: { core: '#7f5cff', hot: '#e6dcff', ui: '#9b7bff' },
}

/**
 * `night` por defecto: es el morado de Cortana, el color que Sandra pidió para su
 * estética (2026-10-11) y el que coincide con el `--tint` de `index.css`. Antes
 * era `work` y salía cian de consola. El core manda el atuendo según hora y
 * temperatura (`services/core/cort_core/outfit.py`), así que esto sólo decide el
 * color de la interfaz **antes** de que el core conteste.
 */
export const DEFAULT_OUTFIT: Outfit = 'night'

/** Acento de esfuerzo: el orbe tira a magenta mientras CORT piensa. */
export const THINKING_HOT = '#ff5ce0'

/** Giro del reactor por estado, en multiplicadores sobre la animación base. */
export const SPIN = { idle: 0.55, thinking: 2.8 }
