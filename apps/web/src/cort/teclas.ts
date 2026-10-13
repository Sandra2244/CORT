/**
 * El teclado de la cara, **solo y sin DOM** (función 76).
 *
 * Por qué existe este archivo. Hasta el 2026-10-13 la tabla de teclas vivía
 * escrita a mano dentro del `useEffect` de `App.tsx`, y la ayuda en pantalla
 * (`ui/Ayuda.tsx`) y el muelle (`ui/Muelle.tsx`) repetían cada nombre y cada
 * número por su cuenta. Tres listas que hay que mantener sincronizadas a ojo son
 * tres fuentes de verdad: la ayuda puede prometer una tecla que el manejador ya
 * no escucha, y el muelle puede enseñar el número equivocado. Aquí la tabla se
 * escribe **una vez** y los tres lados la leen.
 *
 * Y por qué es un módulo y no parte del componente, que es lo que pide la regla 3
 * de `AGENTS.md`: `App.tsx` toca `window`, `useState` y el WebSocket, así que en
 * Node no se puede ni importar. Decidir **qué tecla hace qué** no necesita nada
 * de eso — es una función que recibe un objeto con `key` y tres modificadores y
 * devuelve una acción—, así que se prueba sin navegador:
 * `apps/web/tests/teclas.test.mjs`, ejecutada con `make test-web`.
 *
 * Las decisiones que este módulo protege, cada una con su motivo:
 *
 * 1. **`Esc` cierra sólo la ventana de enfrente**, nunca todas. Con tres
 *    ventanas abiertas, vaciar la pantalla de un golpe obligaría a reabrirlas
 *    una por una para seguir trabajando.
 * 2. **`Esc` y `Ctrl+/` funcionan aunque se esté escribiendo.** Son las dos
 *    salidas que uno necesita con las manos dentro del campo de la charla.
 * 3. **El resto de teclas se retira dentro de un campo**: escribir `/` o un
 *    número en un mensaje tiene que seguir siendo escribir `/` o un número. Es
 *    la guarda que hacía falta cuando el riel, y se conserva aquí.
 * 4. **Con `Ctrl`/`Meta`/`Alt` no hace nada** salvo el `Ctrl+/` dicho arriba.
 *    Atajo nuevo = tecla nueva que la ayuda no conoce.
 * 5. **Los números van por orden de la tabla**, no por orden alfabético ni por
 *    recordatorio de memoria: la posición que se ve en el muelle es la que se
 *    pulsa. Por eso `1` es charla y `6` ayuda, en el mismo orden en que están
 *    pintados los accesos.
 */

/** Las superficies que existen, en el orden en que se pintan en el muelle. */
export type IdVentana = 'charla' | 'voz' | 'camara' | 'cuerpo' | 'sistema' | 'ayuda'

export type Acceso = {
  id: IdVentana
  /** Lo que se lee en el muelle y en la ayuda: en español, con su tilde. */
  etiqueta: string
  /** La tecla que lo levanta. Se deriva del puesto, no se teclea a mano. */
  tecla: string
}

const ETIQUETAS: Record<IdVentana, string> = {
  charla: 'charla',
  voz: 'voz',
  camara: 'cámara',
  cuerpo: 'cuerpo',
  sistema: 'sistema',
  ayuda: 'ayuda',
}

/**
 * La única lista de ventanas que existe. Añadir una superficie nueva es escribir
 * su fila aquí: el muelle la muestra, el teclado la obedece y la ayuda la
 * enumera sola.
 */
export const ACCESOS: readonly Acceso[] = (
  ['charla', 'voz', 'camara', 'cuerpo', 'sistema', 'ayuda'] as IdVentana[]
).map((id, puesto) => ({
  id,
  etiqueta: ETIQUETAS[id],
  tecla: String(puesto + 1),
}))

/** La ventana que corresponde a una tecla numérica; `null` si el número no existe. */
export function ventanaPorTecla(tecla: string): IdVentana | null {
  const acceso = ACCESOS.find((a) => a.tecla === tecla)
  return acceso ? acceso.id : null
}

/** Lo que el navegador entrega, recortado a lo que esta función mira. */
export type EventoDeTecla = {
  key: string
  ctrlKey?: boolean
  metaKey?: boolean
  altKey?: boolean
  /**
   * `true` si el foco está dentro de un campo de texto. Lo decide el llamador
   * (`App.tsx`, que sí conoce el DOM); aquí entra como dato para que la regla 3
   * se pueda probar sin un `<input>` delante.
   */
  escribiendo?: boolean
}

/**
 * La acción pedida. `evitar` dice si hay que llamar a `preventDefault()`: solo
 * hace falta con `/`, porque sin eso la barra se escribiría en el campo que acabe
 * de recibir el foco.
 */
export type Accion =
  | { tipo: 'cerrar-frente' }
  | { tipo: 'abrir'; id: IdVentana; evitar: boolean }
  | null

/**
 * Traduce una pulsación a una acción. Es pura: no lee `window`, no escribe
 * estado, no llama a `preventDefault` — eso le toca al componente, y es justo lo
 * que permite tener esta prueba.
 */
export function accionDeTecla(e: EventoDeTecla): Accion {
  if (e.key === 'Escape') return { tipo: 'cerrar-frente' }

  // `Ctrl+/` (o `Cmd+/`) invoca la charla **aunque se esté escribiendo**: es la
  // forma de saltar al campo con las manos ya puestas.
  if ((e.ctrlKey || e.metaKey) && e.key === '/') {
    return { tipo: 'abrir', id: 'charla', evitar: true }
  }

  if (e.ctrlKey || e.metaKey || e.altKey) return null
  if (e.escribiendo) return null

  if (e.key === '/') return { tipo: 'abrir', id: 'charla', evitar: true }
  // `?` exige `Shift` en la mayoría de teclados, y `Shift` no está en la lista de
  // modificadores que retiran la tecla: sin eso, la ayuda sería inalcanzable.
  if (e.key === '?') return { tipo: 'abrir', id: 'ayuda', evitar: false }

  const id = ventanaPorTecla(e.key)
  return id ? { tipo: 'abrir', id, evitar: false } : null
}

/**
 * Qué ventana queda de enfrente tras cerrar la última. `App.tsx` guarda la pila
 * como array y el frente es el último elemento; esta función existe porque el
 * `Esc` mal —`[]` en vez de quitar una— es de los fallos que no se ven hasta que
 * alguien tiene tres ventanas abiertas.
 */
export function despedirFrente(pila: readonly IdVentana[]): IdVentana[] {
  return pila.slice(0, -1)
}

/** Traer una ventana al frente sin duplicarla (es lo que hace un toque o `/`). */
export function traerAlFrente(pila: readonly IdVentana[], id: IdVentana): IdVentana[] {
  return [...pila.filter((x) => x !== id), id]
}

/** El muelle: si está abierta la despide, si no la abre. */
export function conmutar(pila: readonly IdVentana[], id: IdVentana): IdVentana[] {
  return pila.includes(id) ? despedir(pila, id) : [...pila, id]
}

/** Echar una ventana concreta con su `✕`. Filtrar sin mutar: React vería el
 *  mismo array y no pintaría nada. */
export function despedir(pila: readonly IdVentana[], id: IdVentana): IdVentana[] {
  return pila.filter((x) => x !== id)
}
