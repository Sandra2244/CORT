/**
 * Del `mood` que manda el core a los pesos que entiende el cuerpo 3D.
 *
 * Función 29 del inventario. El `mood` ya viajaba en cada `assistant_message`
 * desde que se escribió el marco, pero siempre con el literal `"calm"`: era un
 * campo decorativo. Ahora lo llena `cort_core/affect.py` —señales medidas, y
 * cuando no hay señal, un léxico determinista— y aquí se traduce a lo único que
 * sabe hacer un `.vrm`: **pesos de expresión**.
 *
 * Tres reglas que estas funciones fijan:
 *
 * 1. **Conjunto cerrado.** El VRM trae cinco expresiones faciales de fábrica
 *    (`happy`, `sad`, `surprised`, `relaxed`, `angry`) y cinco visemas. Un mood
 *    que no esté en el inventario del core no puede pintar nada, así que se cae
 *    al reposo *antes* de llegar a la escena. Es el mismo criterio con el que
 *    `connection.ts` valida los `effect`: un nombre mal escrito no cuelga la
 *    cara, simplemente no dispara.
 * 2. **`angry` se queda en cero siempre.** El enfado no es algo que CORT pueda
 *    afirmar de sí mismo (regla 11 de `AGENTS.md`): si una orden falla, la cara
 *    lo dice con tristeza y con el `glitch` del orbe, no con hostilidad.
 * 3. **Todo caduca.** Un gesto persistente es una máscara: la usuaria diría que
 *    la figura se quedó mirando. Se persigue el peso durante `MOOD_MS` y luego
 *    vuelve solo al reposo, que es lo que hace que un estado *cambiado* se note.
 *
 * Se prueba en `apps/web/tests/afecto.test.mjs` (`make test-web`).
 */

export type Mood = 'calm' | 'happy' | 'sad' | 'surprised' | 'relaxed'

/** Lo que sabe decir el core. Si él añade uno, se añade aquí y en la escena. */
export const MOODS: Mood[] = ['calm', 'happy', 'sad', 'surprised', 'relaxed']

/** Cuánto se sostiene una cara antes de volver a su sitio. */
export const MOOD_MS = 6000

/** Los cinco morph targets faciales de un `.vrm`, en peso 0..1. */
export type Expresiones = {
  happy: number
  sad: number
  surprised: number
  relaxed: number
  angry: number
}

/**
 * La tabla. Los números son la medida de la cara, no una opinión: en reposo
 * `happy` queda en 0,12 porque un holograma sin ninguna sonrisa parece un
 * maniquí, y 0,8 se eligió porque por encima la boca se abre tanto que tapa el
 * labio superior del modelo que hay en disco. `angry` no aparece: es cero en
 * todos los estados.
 */
const TABLA: Record<Mood, Expresiones> = {
  calm: { happy: 0.12, sad: 0, surprised: 0, relaxed: 0.08, angry: 0 },
  happy: { happy: 0.8, sad: 0, surprised: 0.05, relaxed: 0.15, angry: 0 },
  sad: { happy: 0.02, sad: 0.65, surprised: 0, relaxed: 0.05, angry: 0 },
  surprised: { happy: 0.2, sad: 0, surprised: 0.75, relaxed: 0, angry: 0 },
  relaxed: { happy: 0.25, sad: 0, surprised: 0, relaxed: 0.6, angry: 0 },
}

/** El nombre como lo manda el core, tolerando mayúsculas y espacios. */
export function esMood(valor: unknown): Mood | null {
  if (typeof valor !== 'string') return null
  const limpio = valor.trim().toLowerCase()
  return (MOODS as string[]).includes(limpio) ? (limpio as Mood) : null
}

/** Los pesos a perseguir. Lo desconocido es reposo, nunca un gesto a medias. */
export function expresionesPara(mood: unknown): Expresiones {
  return { ...TABLA[esMood(mood) ?? 'calm'] }
}

/**
 * Si el estado sigue vigente o ya hay que dejarlo ir. `desde` es la marca de
 * `performance.now()` en la que llegó el mensaje; un reloj que vuelve atrás (una
 * pestaña dormida, un reinicio) se trata como caducado, no como eterno.
 */
export function moodVigente(mood: unknown, desde: number, ahora: number): Mood {
  if (ahora - desde > MOOD_MS || ahora < desde) return 'calm'
  return esMood(mood) ?? 'calm'
}
