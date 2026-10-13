/**
 * La agenda de labios: de un texto dicho a la boca que hay que pintar ahora.
 *
 * Función 27 del inventario. Por qué va por texto y no por audio: la voz de CORT
 * es `speechSynthesis` del navegador (función 13), y **ese audio no pasa por
 * ningún sitio que el código pueda mirar** — no hay `AudioNode`, no hay samples,
 * no hay espectro que analizar. Lo único que el navegador devuelve son avisos de
 * palabra (`onboundary`), y las voces «Natural» en línea tampoco los mandan
 * siempre. Así que la boca se programa **desde el texto** y el aviso de palabra
 * sólo sirve para realinear el reloj cuando llega. Está dicho en
 * `docs/FUNCTIONS.md`: es un labio sincronizado con lo que se va a decir, no con
 * la onda que suena.
 *
 * El plan es determinista y puro: mismo texto, misma agenda, sin reloj global ni
 * azar. Se prueba con `make test-web` (`apps/web/tests/labios.test.mjs`), que es
 * lo que la regla 3 de `AGENTS.md` pide cuando nace una capa de la cara.
 *
 * Las cifras vienen de fonética barata, no de un modelo: una sílaba española
 * dura 120-180 ms hablando normal, la vocal se abre en el centro de esa ventana
 * y se cierra en los bordes. Todo lo que hace este archivo es repartir ese
 * contorno sobre las vocales que hay en la frase.
 */

/** Los cinco morph targets de vocal que trae un `.vrm` (VRM `aa/ih/ou/ee/oh`). */
export type Visma = 'aa' | 'ee' | 'ih' | 'oh' | 'ou'

export type Sílaba = {
  /** ms desde que empezó la frase. */
  ini: number
  /** duración del abrir-y-cerrar, en ms. */
  dur: number
  visma: Visma
}

/** Ventana de una sílaba: ni un golpe seco ni un aleteo de mosca. */
export const SILABA_MS = 120
/** Hueco entre palabras: la mandíbula se cierra un instante. */
const HUECO_MS = 55
/** Coma o punto y coma. */
const PAUSA_CORTA_MS = 140
/** Punto, exclamación, interrogación, puntos suspensivos. */
const PAUSA_LARGA_MS = 240

const VOCALES = 'aeiouáéíóúü'
const ABIERTAS = 'áéíóú'
/** Con tilde o sin ella la boca hace el mismo gesto: la tilde sólo marca el hiato. */
const SIN_TILDE: Record<string, string> = { á: 'a', é: 'e', í: 'i', ó: 'o', ú: 'u', ü: 'u' }
const POR_VOCAL: Record<string, Visma> = {
  a: 'aa',
  e: 'ee',
  i: 'ih',
  o: 'ou',
  u: 'ou',
}

/** La vocal que abre la boca de un grupo: la del núcleo del diptongo. */
function nucleo(run: string): string {
  // En «ai», «au», «ei» la última vocal es cerrada (i/u) y funciona de
  // semivocal: la boca se abre en la anterior. En «ie», «io», «ea» la abierta ya
  // está al final, y se toma tal cual.
  const sin = (c: string) => SIN_TILDE[c] ?? c
  const ult = sin(run[run.length - 1])
  return (ult === 'i' || ult === 'u') && run.length > 1 ? sin(run[run.length - 2]) : ult
}

function esVocal(c: string) {
  return VOCALES.includes(c)
}

/**
 * El plan de una frase. Los grupos de vocales seguidas son una sílaba, salvo
 * cuando llevan una vocal acentuada dentro: «ma-íz», «pa-ís» son hiato y son dos
 * aperturas de boca, no una.
 */
export function silabas(texto: string): Sílaba[] {
  const t = (texto ?? '').toLowerCase()
  const plan: Sílaba[] = []
  let i = 0
  let anterior = { fin: 0, hasta: 0 }
  while (i < t.length) {
    if (!esVocal(t[i])) {
      i++
      continue
    }
    let j = i
    while (j < t.length && esVocal(t[j])) j++
    const run = t.slice(i, j)
    const acento = [...run].some((c) => ABIERTAS.includes(c))
    // Hiato: cada vocal del grupo cuenta sola. Diptongo o vocal única: una.
    const piezas = acento && run.length > 1 ? [...run] : [run]
    // Qué separa esta sílaba de la anterior: el trozo de texto que queda entre
    // el grupo anterior y éste. Con punto, la boca se cierra más tiempo.
    const medio = t.slice(anterior.hasta, i)
    const hueco = anterior.fin === 0
      ? 0
      : /[.!?…]/.test(medio)
        ? PAUSA_LARGA_MS
        : /[,;:]/.test(medio)
          ? PAUSA_CORTA_MS
          : /\s/.test(medio)
            ? HUECO_MS
            : 0
    let cursor = anterior.fin === 0 ? 0 : anterior.fin + hueco
    for (const p of piezas) {
      plan.push({ ini: cursor, dur: SILABA_MS, visma: POR_VOCAL[nucleo(p)] ?? 'aa' })
      cursor += SILABA_MS
    }
    anterior = { fin: cursor, hasta: j }
    i = j
  }
  return plan
}

/** Cuánto dura la frase entera, en ms. `0` si no tiene una sola vocal. */
export function duracion(plan: Sílaba[]): number {
  if (plan.length === 0) return 0
  const u = plan[plan.length - 1]
  return u.ini + u.dur
}

/**
 * La boca en el instante `t` de la frase: `abierto` es el peso que se le da al
 * visema (0 cerrada, 1 abierta del todo) y sigue el centro de la sílaba, que es
 * donde está la vocal. `sin(πk)` en vez de un diente de sierra: la mandíbula
 * sube y baja, no se pega al maxilar de golpe.
 */
export function boca(t: number, plan: Sílaba[]): { visma: Visma; abierto: number } {
  for (const s of plan) {
    if (t < s.ini) break
    if (t >= s.ini + s.dur) continue
    const k = (t - s.ini) / s.dur
    return { visma: s.visma, abierto: Math.sin(Math.PI * Math.min(1, Math.max(0, k))) }
  }
  return { visma: 'aa', abierto: 0 }
}

// ── El reloj de la frase en curso ──────────────────────────────────────────────
// Tres líneas de estado con su `performance.now()`. No se prueba (no hay reloj
// en Node y no hace falta): lo que se prueba es `silabas` y `boca`, arriba.

let plan: Sílaba[] = []
let inicio = -1

/** Empezar a mover la boca con una frase. La llame quien la llame, el plan es puro. */
export function empezar(texto: string) {
  plan = silabas(texto)
  inicio = plan.length ? performance.now() : -1
}

/**
 * Realineación con el aviso de palabra del navegador: se tira lo que ya se dijo
 * y se agenda el resto. Si el aviso no llega nunca (voces en línea), el plan
 * original sigue valiendo — es el motivo de que la agenda se calcule del texto.
 */
export function alinear(textoRestante: string) {
  if (!textoRestante) return
  plan = silabas(textoRestante)
  inicio = plan.length ? performance.now() : -1
}

export function parar() {
  plan = []
  inicio = -1
}

/** Lo que la escena pregunta cada cuadro. Cerrada si no hay frase en curso. */
export function ahora(): { visma: Visma; abierto: number } {
  if (inicio < 0) return { visma: 'aa', abierto: 0 }
  return boca(performance.now() - inicio, plan)
}
