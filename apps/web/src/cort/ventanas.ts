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
 *
 * N4 (2026-10-10) añadió el **menú de secciones** al mismo estado: el espacio
 * de trabajo es esto — la pila, el vidrio y un lanzador (`menu`) que nombra lo
 * que existe y rotula lo que viene (`PROXIMAS`), sin simular nada. El `Esc`
 * ganó una prioridad: menú primero.
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

/**
 * Las secciones **en camino** que el menú de N4 nombra pero no finge (regla 10
 * de AGENTS.md): cada una dice qué capa del plan la trae. No son ventanas: sin
 * contenido real no hay fila que abrir, y una fila muda enseñaría a desconfiar
 * del menú. `nota` es el texto que ve la usuaria.
 */
export const PROXIMAS: { id: string; etiqueta: string; nota: string }[] = [
  { id: 'agenda', etiqueta: 'agenda', nota: 'en camino — N2 (fechas naturales)' },
  { id: 'consola', etiqueta: 'consola', nota: 'en camino — N3 (chat + agente)' },
  { id: 'dispositivos', etiqueta: 'dispositivos', nota: 'en camino — N7 (lista cerrada, con permiso)' },
  { id: 'documentos', etiqueta: 'documentos', nota: 'en camino — N8 (Markdown/HTML)' },
]

export type Estado = {
  /** Ventanas abiertas, de abajo de la pila (índice 0) al frente (último). */
  readonly pilas: readonly Seccion[]
  /** Índice de `VIDRIOS`. */
  readonly vidrio: number
  /** Si está abierto el menú lanzador de secciones (N4). */
  readonly menu: boolean
}

/** En reposo: ninguna ventana ni menú abierta. La cara es reactor y cockpit. */
export const reposo: Estado = { pilas: [], vidrio: VIDRIO_INICIAL, menu: false }

/**
 * Abrir (o traer al frente si ya estaba). Es también el gesto de tocar una ventana.
 * Elegir una sección despide el menú: el lanzador era la puerta, ya se pasó por ella.
 */
export function abrir(st: Estado, id: Seccion): Estado {
  const sin = st.pilas.filter((s) => s !== id)
  return { pilas: [...sin, id], vidrio: st.vidrio, menu: false }
}

/** Ocultar una ventana. No borra nada: las ventanas se guardan, no se destruyen. */
export function cerrar(st: Estado, id: Seccion): Estado {
  const sin = st.pilas.filter((s) => s !== id)
  if (sin.length === st.pilas.length) return st
  return { pilas: sin, vidrio: st.vidrio, menu: st.menu }
}

/** La tecla 1–5: si su ventana estaba, se oculta; si no, se abre al frente. */
export function alternar(st: Estado, id: Seccion): Estado {
  return st.pilas.includes(id) ? cerrar(st, id) : abrir(st, id)
}

/** El botón «menú» de la bandeja y la tecla `m`: abre el lanzador, o lo despide. */
export function toggleMenu(st: Estado): Estado {
  return { pilas: st.pilas, vidrio: st.vidrio, menu: !st.menu }
}

/** Cerrar el menú sin tocar la pila (la ✕ del propio lanzador). */
export function cerrarMenu(st: Estado): Estado {
  return st.menu ? { pilas: st.pilas, vidrio: st.vidrio, menu: false } : st
}

/** La ventana del frente — la que despide un `Esc` — o `null` si no hay ninguna. */
export function frente(st: Estado): Seccion | null {
  return st.pilas.length > 0 ? st.pilas[st.pilas.length - 1] : null
}

/**
 * El `Esc` sobre el espacio de trabajo: **primero despide el menú** —es la capa
 * más encima—, luego la ventana del frente, y sólo cuando ya no queda ninguna
 * devuelve `null`, la señal de que el Esc sigue bajando a la bandeja (el `Esc`
 * jerárquico heredado de `v0.11`).
 */
export function esc(st: Estado): Estado | null {
  if (st.menu) return cerrarMenu(st)
  const f = frente(st)
  return f === null ? null : cerrar(st, f)
}

/** Despider todo de un golpe (invocar la entrada: la cara se limpia para escribir). */
export function cerrarTodo(st: Estado): Estado {
  if (st.pilas.length === 0 && !st.menu) return st
  return { pilas: [], vidrio: st.vidrio, menu: false }
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
