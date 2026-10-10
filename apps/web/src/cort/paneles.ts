/**
 * El estado de la cara: qué panel está expandido y si hay cara.
 *
 * Nace del análisis de `docs/REFERENCIAS.md`. En los cuatro videos de interfaz
 * que se miraron fotograma a fotograma no hay un panel de control abierto de
 * golpe: hay **hilos finos en los bordes**, uno se ensancha cuando se le apunta y
 * los demás vuelven a su trazo. CORT tenía un tirador en la esquina que abría
 * **todo a la vez** —mensajes, telemetría, voz, atuendos y cámara apelmazados—,
 * que es justo la sobrecarga que la dueña del proyecto pidió quitar.
 *
 * Este archivo es **lógica pura**: no toca `window`, ni el DOM, ni React. Se
 * prueba con `make test-web` (Node 20 + el `typescript` que ya está en
 * `devDependencies`) porque las decisiones que viven aquí —cuántos paneles se
 * abren a la vez, qué tecla le pertenece a quién, cuándo se apaga la interfaz—
 * son las que se rompen en silencio cuando alguien añade un panel séptimo.
 */

export type PanelId = 'mensajes' | 'telemetria' | 'voz' | 'atuendos' | 'camara' | 'teclas'

/**
 * Los seis paneles del riel, en el orden en que se leen de arriba abajo.
 *
 * `id` va en inglés porque es código; `etiqueta` en español porque es lo que se
 * ve en pantalla. `tecla` es el número con el que se abre desde el teclado, y
 * vive pegada a la lista a propósito: si alguien mete un panel en medio, la
 * prueba de `tests/paneles.test.mjs` se queja en vez de dejar dos paneles con el
 * mismo `3`.
 */
export const PANELES: readonly { id: PanelId; etiqueta: string; tecla: string }[] = [
  { id: 'mensajes', etiqueta: 'mensajes', tecla: '1' },
  { id: 'telemetria', etiqueta: 'telemetría', tecla: '2' },
  { id: 'voz', etiqueta: 'voz', tecla: '3' },
  { id: 'atuendos', etiqueta: 'atuendos', tecla: '4' },
  { id: 'camara', etiqueta: 'cámara', tecla: '5' },
  { id: 'teclas', etiqueta: 'teclas', tecla: '6' },
]

/** El índice del riel, convertido en tecla: el primero es el `1`. */
export const PANEL_POR_TECLA: Readonly<Record<string, PanelId>> = Object.fromEntries(
  PANELES.map((p) => [p.tecla, p.id]),
)

export type Estado = {
  /** El panel expandido ahora mismo, o `null` si el riel está en su trazo fino. */
  abierto: PanelId | null
  /** `false` = sólo el reactor: la cara apagada con `H`. */
  cara: boolean
}

export const REPOSO: Estado = { abierto: null, cara: true }

/**
 * Abrir un panel guardando el que estuviera, y encendiendo la cara si estaba
 * apagada: un panel que se abre y no se ve no es un panel, es un estado huérfano.
 *
 * Uno a la vez no es una limitación de implementación: es el patrón 3 de las
 * referencias. Con dos expandidos, en la pantalla de un teléfono de 4 GB el
 * segundo empuja al primero fuera del cuadro.
 */
export function abrir(estado: Estado, id: PanelId): Estado {
  return estado.abierto === id && estado.cara ? estado : { ...estado, abierto: id, cara: true }
}

/** Lo que hace un toque o un `Enter`: si ya estaba abierto y visible, lo guarda. */
export function alternar(estado: Estado, id: PanelId): Estado {
  return estado.abierto === id && estado.cara
    ? { ...estado, abierto: null }
    : { ...estado, abierto: id, cara: true }
}

/** `Esc`: guarda el panel, pero **no** enciende una cara que estaba apagada. */
export function cerrarTodo(estado: Estado): Estado {
  return { ...estado, abierto: null }
}

/** `H`: apaga la interfaz entera y deja el reactor solo. */
export function alternarCara(estado: Estado): Estado {
  return estado.cara ? { abierto: null, cara: false } : { abierto: null, cara: true }
}

/** Lo que devuelve la tabla de teclas: una acción, o `null` si la tecla no es de CORT. */
export type Tecla = 'esc' | 'cara' | 'ayuda' | 'campo' | PanelId | null

/**
 * Un panel por número, y cuatro teclas con nombre.
 *
 * La tabla es un objeto y no una cadena de `if` porque las dos cosas que hay que
 * comprobar con ella son independientes: que la tecla exista, y que no esté
 * secuestrada por un modificador o por el campo de escritura.
 */
const TECLAS: Readonly<Record<string, Exclude<Tecla, PanelId>>> = {
  Escape: 'esc',
  h: 'cara',
  H: 'cara',
  '?': 'ayuda',
  '/': 'campo',
}

/**
 * La tecla pulsada → la acción que le corresponde, o `null`.
 *
 * `escribiendo` es el caso que convierte un atajo en una trampa: mientras el
 * cursor está en el campo de mensaje, `h` es una `h`, `/` es parte de una
 * dirección y `1` es parte de una orden. Ahí sólo se escucha `Esc`, que es lo que
 * cualquiera espera de una tecla de salida.
 *
 * Con `Ctrl`, `Cmd` o `Alt` pulsados no se hace nada: `Ctrl+H` es el historial
 * del navegador y los atajos de la persona no se le pueden quitar.
 */
export function teclaAccion(
  e: { key: string; ctrlKey?: boolean; metaKey?: boolean; altKey?: boolean },
  escribiendo: boolean,
): Tecla {
  if (e.ctrlKey || e.metaKey || e.altKey) return null
  if (escribiendo) return e.key === 'Escape' ? 'esc' : null
  const nombrada = TECLAS[e.key]
  if (nombrada) return nombrada
  return PANEL_POR_TECLA[e.key] ?? null
}

/**
 * Cuánto hay que llevar sin tocar nada para que la interfaz se aparte.
 *
 * Cinco segundos parpadea mientras se está leyendo un mensaje; un minuto no se
 * nota nunca. Doce es el punto donde el apagado se ve y todavía no interrumpe.
 */
export const INACTIVO_MS = 12000

/**
 * Si la cara debe atenuarse ahora mismo.
 *
 * Puro a propósito: recibe `ahora` y la marca de la última actividad en vez de
 * llamar a `Date.now()` por su cuenta, porque la única forma de probar un
 * temporizador sin esperar a que suene es poder mentirle con el reloj.
 *
 * Con `reduceMotion` no se atenúa por reloj. Una interfaz que se apaga sola es
 * una animación, y si el sistema operativo pidió no animar, la pantalla no tiene
 * derecho a decidir por encima de esa petición: ahí apagar la cara se hace con
 * `H` y nada más.
 */
export function debeAtenuar(e: {
  abierto: PanelId | null
  cara: boolean
  ultimaActividad: number
  ahora: number
  reduceMotion?: boolean
}): boolean {
  if (e.reduceMotion) return false
  if (!e.cara || e.abierto !== null) return false
  return e.ahora - e.ultimaActividad >= INACTIVO_MS
}
