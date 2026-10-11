/**
 * La fase de CORT: una palabra que dice qué está pasando **ahora** en la cara.
 *
 * La gramática es un trasplante de ideas (ver `docs/TRANSPLANTE.md`): las cuatro
 * fases del `ai-visualizer` de Jared Rhodenizer (`idle / listening / thinking /
 * speaking`, AGPL — aquí reescritas desde cero) y la estructura del `store.ts`
 * de Aditya Dewaskar (MIT), donde la fase sale de señales separadas y un solo
 * lugar decide qué color le toca. La regla de los dos que CORT se lleva puesta:
 * los estados tienen que leerse *desde el otro lado de la habitación* — no sólo
 * ser distintos en la matemática.
 *
 * Las señales vienen de tres sitios que ya existen, y por eso **el protocolo no
 * cambia** (regla 5 de AGENTS.md intacta):
 *
 *  - `core`: el campo `thinking` que el core ya manda por el WebSocket.
 *  - `micro`: lo sabe `Voz.tsx` cuando enciende el reconocimiento.
 *  - `tts`: lo sabe `Voz.tsx` en `onstart`/`onend` del habla.
 *
 * La prioridad es deliberada y distinta a la del visualizer de referencia:
 * **habla gana a piensa, y piensa gana a escucha.** Quien tiene la palabra es
 * quien se ve; un micrófono abierto mientras CORT responde no debe pintarse
 * como si ella estuviera escuchando (se oiría a sí misma — el mismo motivo por
 * el que `Voz.tsx` cierra el micrófono al hablar).
 */

export type Fase = 'reposo' | 'escucha' | 'piensa' | 'habla'

export type Señales = { micro: boolean; tts: boolean; core: boolean }

/**
 * Verdad de campo a campo en vez de fiarse del llamador: las señales llegan de
 * manejadores del navegador (evento de voz, error de reconocimiento), y un
 * `undefined` colado no debe convertir «habla» en una fase inventada. Es el
 * mismo `Boolean()` defensivo que `readStatus` en `connection.ts`.
 */
export function faseDe(s: Señales): Fase {
  if (s?.tts) return 'habla'
  if (s?.core) return 'piensa'
  if (s?.micro) return 'escucha'
  return 'reposo'
}

/** Etiqueta para el `title` del punto de fase: la cara explica sin párrafos. */
export const FASE_TEXTO: Record<Fase, string> = {
  reposo: 'CORT en línea',
  escucha: 'escuchando',
  piensa: 'pensando',
  habla: 'hablando',
}
