/**
 * La pila de ventanas de vidrio (capa L3, rediseño N1 de docs/REDESIGN-NUCLEO.md).
 *
 * El modal de una sola pestaña (`ui/Panel.tsx`, rediseño por capas de
 * docs/REDESIGN-UI.md) se convierte en **ventanas flotantes**: cada sección —
 * voz · cámara · atuendos · sistema · ayuda— es una ventana de vidrio que puede
 * estar abierta a la vez que las demás, se arrastra con el asa de arriba
 * (`cort/arrastre.ts`, ya medido en DOM), se oculta y vuelve con su tecla, y se
 * mira a través de ella con tres niveles de transparencia.
 *
 * Este archivo es **lógica pura sin DOM**: una pila ordenada (lo último = al
 * frente, que es como piensan las ventanas desde Smalltalk) y un nivel de
 * vidrio. Por eso se prueba con `make test-web` —el mismo patrón `node --test`
 * sin dependencias del antiguo `paneles.ts`— y el navegador sólo pone los
 * `<section>` encima.
 *
 * La gramática heredada del modal se conserva a propósito: `Esc` despide
 * primero la ventana del frente y sólo si no queda ninguna guarda la bandeja
 * (el `Esc` jerárquico de `v0.11`), y `1`–`5` siguen siendo la mano en el
 * teclado, pero ahora **alternan** su ventana en vez de cambiar de pestaña.
 */

export type Seccion = 'voz' | 'camara' | 'atuendos' | 'sistema' | 'ayuda'

/** Las cinco secciones con su etiqueta visible y su tecla. El orden es la tabla. */
export const SECCIONES: { id: Seccion; etiqueta: string; tecla: string }[] = [
  { id: 'voz', etiqueta: 'voz', tecla: '1' },
  { id: 'camara', etiqueta: 'cámara', tecla: '2' },
  { id: 'atuendos', etiqueta: 'atuendos', tecla: '3' },
  { id: 'sistema', etiqueta: 'sistema', tecla: '4' },
  { id: 'ayuda', etiqueta: 'ayuda', tecla: '5' },
]

/**
 * Los tres niveles de vidrio, de más opaco a más bruma. Son clases CSS
 * prefijadas (`.vidrio-*`) y no un `--variable` con `calc()`: en el navegador
 * de una máquina de 1,8 GiB menos calc en el paint, mejor. El nombre se
 * muestra en el `title` del botón ◐ para que el ciclo sea legible.
 */
export const VIDRIOS: { clase: string; nombre: string }[] = [
  { clase: 'vidrio-opaco', nombre: 'opaco' },
  { clase: 'vidrio-normal', nombre: 'vidrio' },
  { clase: 'vidrio-bruma', nombre: 'bruma' },
]

/** El nivel con el que nace cada ventana abierta: el del medio, el JARVIS. */
export const VIDRIO_INICIAL = 1

export type Estado = {
  /** Ventanas abiertas, de abajo de la pila (índice 0) al frente (último). */
  readonly pilas: readonly Seccion[]
  /** Índice de `VIDRIOS`. */
  readonly vidrio: number
}

/** En reposo: ninguna ventana. La cara sigue siendo reactor, reloj y esquina. */
export const reposo: Estado = { pilas: [], vidrio: VIDRIO_INICIAL }

/** Abrir (o traer al frente si ya estaba). Es también el gesto de tocar una ventana. */
export function abrir(st: Estado, id: Seccion): Estado {
  const sin = st.pilas.filter((s) => s !== id)
  return { pilas: [...sin, id], vidrio: st.vidrio }
}

/** Ocultar una ventana. No borra nada: las ventanas se guardan, no se destruyen. */
export function cerrar(st: Estado, id: Seccion): Estado {
  const sin = st.pilas.filter((s) => s !== id)
  if (sin.length === st.pilas.length) return st
  return { pilas: sin, vidrio: st.vidrio }
}

/** La tecla 1–5: si su ventana estaba, se oculta; si no, se abre al frente. */
export function alternar(st: Estado, id: Seccion): Estado {
  return st.pilas.includes(id) ? cerrar(st, id) : abrir(st, id)
}

/** La ventana del frente — la que despide un `Esc` — o `null` si no hay ninguna. */
export function frente(st: Estado): Seccion | null {
  return st.pilas.length > 0 ? st.pilas[st.pilas.length - 1] : null
}

/**
 * El `Esc` sobre la pila: devuelve el estado con la ventana del frente despedida,
 * o `null` si no quedaba ninguna — y entonces el llamador (`App.tsx`) sabe que
 * el `Esc` sigue bajando a la bandeja, como en `v0.11`.
 */
export function esc(st: Estado): Estado | null {
  const f = frente(st)
  return f === null ? null : cerrar(st, f)
}

/** Despider todas de un golpe (invocar la entrada: la cara se limpia para escribir). */
export function cerrarTodo(st: Estado): Estado {
  return st.pilas.length === 0 ? st : { pilas: [], vidrio: st.vidrio }
}

/** El botón ◐: opaco → ventana → bruma → opaco. */
export function siguienteVidrio(n: number): number {
  return (n + 1) % VIDRIOS.length
}

/** Qué sección manda la tecla `k` (`'1'`–`'5'`), o `null` si la tecla no es de ventana. */
export function seccionPorTecla(k: string): Seccion | null {
  const s = SECCIONES.find((x) => x.tecla === k)
  return s ? s.id : null
}
