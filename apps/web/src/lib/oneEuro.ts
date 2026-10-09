/**
 * Trasplante de `src/lib/oneEuro.ts` de **adewaskar/JARVIS** (MIT):
 * <https://github.com/adewaskar/jarvis>. Atribución módulo a módulo en
 * `apps/web/CREDITS.md`. Se trae sólo `OneEuro`; la variante `OneEuroPoint`
 * (un filtro por eje) se quedó fuera porque en CORT no hay todavía ninguna
 * posición 2D que suavizar.
 *
 * El filtro 1€ — Casiez, Roussel & Vogel, CHI 2012.
 *
 * La webcam que mide `defocus.ts` tiene los dos problemas en direcciones
 * opuestas. Una mano quieta delante del objetivo no está quieta: la medida de
 * nitidez tiembla de muestra a muestra, y un orbe que tiembla con el sensor
 * parece roto. Una mano que se mueve necesita lo contrario: cualquier
 * suavizado bastante para matar el temblor mete retardo, y un reactor que
 * responde tarde a un gesto se lee peor que uno que tiembla.
 *
 * Un filtro de paso bajo fijo — el `x += (objetivo - x) * k` de una línea —
 * tiene que elegir en cuál de los dos es malo. Éste no elige: estima la
 * velocidad de la señal y adapta su propio corte a ella. Suaviza a fondo
 * cuando la señal está casi quieta y casi nada cuando se mueve rápido.
 *
 * Dos parámetros, porque son toda la superficie de ajuste:
 *
 *   minCutoff — el suelo. Bajo = más suave en reposo y más lento de reflejos.
 *   beta      — cuánto se abre el corte con la velocidad. Súbelo si los
 *               movimientos rápidos se quedan atrás; bájelo si se ven nerviosos.
 *
 * El consejo de ajuste publicado es partir de beta = 0, bajar `minCutoff` hasta
 * que el temblor en reposo sea aceptable, y subir después `beta` hasta que el
 * retardo en movimiento sea aceptable. Así se eligieron los valores de
 * `defocus.ts`.
 */

const TAU = 2 * Math.PI

/** Factor de suavizado para una frecuencia de corte y un periodo de muestra dados. */
function alphaFor(cutoff: number, dt: number): number {
  const tau = 1 / (TAU * cutoff)
  return 1 / (1 + tau / dt)
}

class LowPass {
  private value: number | null = null

  filter(x: number, alpha: number): number {
    this.value = this.value === null ? x : alpha * x + (1 - alpha) * this.value
    return this.value
  }

  get last(): number | null {
    return this.value
  }

  reset() {
    this.value = null
  }
}

export class OneEuro {
  private x = new LowPass()
  private dx = new LowPass()
  private lastAt: number | null = null

  private minCutoff: number
  private beta: number
  /** Corte del estimador de velocidad, que es más ruidoso que la señal misma. */
  private dCutoff: number

  constructor(minCutoff = 1.0, beta = 0.0, dCutoff = 1.0) {
    this.minCutoff = minCutoff
    this.beta = beta
    this.dCutoff = dCutoff
  }

  /** @param at marca de tiempo en **segundos**. */
  filter(x: number, at: number): number {
    if (this.lastAt === null) {
      this.lastAt = at
      this.dx.filter(0, alphaFor(this.dCutoff, 1 / 60))
      return this.x.filter(x, 1)
    }

    // Guarda el periodo de muestra. Una pestaña que estuvo en segundo plano
    // vuelve con un dt de varios segundos: eso lleva alpha a ~1 y deja que un
    // solo cuadro viejo se imponga entero; y un dt de cero divide por nada.
    const dt = Math.min(Math.max(at - this.lastAt, 1 / 240), 1 / 5)
    this.lastAt = at

    const prev = this.x.last
    const speed = prev === null ? 0 : (x - prev) / dt
    const edx = this.dx.filter(speed, alphaFor(this.dCutoff, dt))

    // La idea entera, en una línea: cuanto más rápido se mueve la señal, más
    // alto el corte y menos se suaviza.
    const cutoff = this.minCutoff + this.beta * Math.abs(edx)
    return this.x.filter(x, alphaFor(cutoff, dt))
  }

  reset() {
    this.x.reset()
    this.dx.reset()
    this.lastAt = null
  }
}
