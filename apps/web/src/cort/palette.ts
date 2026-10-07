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
  light:  { core: '#56f0d8', hot: '#e6fff9', ui: '#6ef4de' },
  work:   { core: '#3fd8ff', hot: '#dffbff', ui: '#5ce1ff' },
  casual: { core: '#7f8cff', hot: '#e4e8ff', ui: '#93a0ff' },
}

export const DEFAULT_OUTFIT: Outfit = 'work'

/** Acento de esfuerzo: el orbe tira a magenta mientras CORT piensa. */
export const THINKING_HOT = '#ff5ce0'

/** Giro del reactor por estado, en multiplicadores sobre la animación base. */
export const SPIN = { idle: 0.55, thinking: 2.8 }
