/**
 * La frase de activación de CORT, sola y sin DOM.
 *
 * Por qué es un módulo aparte y no tres líneas dentro de `voz.ts`: `voz.ts` toca
 * `speechSynthesis`, `SpeechRecognition` y `localStorage`, así que en Node no se
 * puede ni importar. Aquí sólo hay una función que recibe un string y devuelve
 * otro —lo que la prueba puede ejecutar sin navegador (regla 3 de `AGENTS.md`:
 * la lógica pura de la cara lleva su prueba; la tabla de la cara ya se probó
 * así con `cort/paneles.ts` antes del rediseño).
 *
 * Lo que se decidió aquí y no es decorativo:
 *
 *  - **Hace falta el saludo delante.** «cort» suelto se cuela en cualquier frase
 *    («el cortometraje», «cortar», «corte»), y una cara que despierta con
 *    palabras parecidas es una cara que se abre sola en medio de una videollamada.
 *  - **El nombre va recortado por un `(?![a-záéíóúñ])`:** «cortometraje» y
 *    «corte» tienen que dar `null`, no la orden vacía.
 *  - **Las variantes con «k» y con erre doble** son lo que los reconocedores
 *    entienden cuando la palabra sale rápida o con ruido de fondo.
 *  - **Devuelve lo que se dijo DESPUÉS de la frase**, no toda la frase: así
 *    «ok cort sube el volumen» ya trae la orden hecha en un solo reconocimiento
 *    y no hay que esperar un segundo dictado.
 */

/** Lo que hay que decir antes del nombre: `ok`, `oye`, `hey`, `hola`… */
const SALUDO = '(?:ok|okey|okay|o\\.?\\s?k\\.?|oye|hey|ey|hola)'

/** Cómo puede llegar el nombre desde el reconocedor de voz. */
const NOMBRE = '(?:cort|kort|cohort|cortte|cqrt)'

const ACTIVACION = new RegExp(
  `(?:^|[\\s,.!¡¿?])${SALUDO}[\\s,.!¡:;-]*${NOMBRE}(?![a-záéíóúñ])[\\s,.!¡:;-]*(.*)$`,
  'i',
)

/**
 * `null` si no hay frase de activación; la orden dicha detrás, posiblemente
 * vacía (vacía = «te escucho», y ahí `voz.ts` abre el micrófono un turno).
 */
export function buscarActivacion(texto: string): string | null {
  const m = texto.match(ACTIVACION)
  return m ? m[1].trim() : null
}
