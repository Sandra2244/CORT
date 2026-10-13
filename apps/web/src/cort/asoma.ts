/**
 * La sujeción de un panel arrastrado, sola y sin DOM (función 82).
 *
 * `cort/arrastre.ts` hace la parte pegajosa: escuchar el puntero en `window` y
 * medir el elemento con `getBoundingClientRect`. Aquí no hay ni `window` ni
 * nodos: entra un rectángulo como cuatro números y sale la posición nueva. Se
 * separó por la razón que la regla 3 de `AGENTS.md` lleva repitiendo desde que
 * el riel se cayó —esta geometría **ya estuvo mal una vez** (los topes emparejaban
 * el borde de arriba del panel con el de arriba de la ventana, y desde su propio
 * sitio no se podía mover hacia abajo ni un píxel), y un fallo así se arregla con
 * la pantalla cerrada si tiene su prueba, o se vuelve a colar con la pantalla
 * abierta si no la tiene—.
 *
 * La decisión que protege: un panel que se tira fuera de la ventana deja de tener
 * asa, y un HUD sin asa no se vuelve a agarrar. Por eso cada eje sujeta con el
 * borde **opuesto** del panel contra el borde de la ventana, y siempre tienen que
 * quedar `ASOMA_MIN` píxeles asomando por dondequiera que se suelte.
 */

/** Píxeles del panel que han de seguir visibles por dondequiera que se arrastre. */
export const ASOMA_MIN = 72

/** Cuatro números de `DOMRect` — lo que se lee del nodo antes de venir aquí. */
export type Caja = { left: number; right: number; top: number; bottom: number }

export type Punto = { x: number; y: number }

function recortar(v: number, min: number, max: number): number {
  return Math.min(Math.max(v, min), max)
}

/**
 * El destino tras un paso de `dx`/`dy`, con el panel ya donde está.
 *
 * `caja` es el rectángulo **ya con el desplazamiento aplicado** (es lo que
 * devuelve `getBoundingClientRect`), `actual` la posición del panel en este
 * instante y `viewport` el tamaño de la ventana. Así el tope se calcula en cada
 * cuadro y sobre el cuadro que se acaba de dar, no una vez al agarrar: el propio
 * panel cambia de alto a media arrancada —el botón de recolocar aparece y la barra
 * partida se va a una segunda línea—, y con la medida vieja el tope se queda
 * corto unos 25 px.
 *
 * Cada borde se empareja con el opuesto del panel. Para que siga asomando por la
 * izquierda tiene que haber por lo menos `ASOMA_MIN` píxeles entre el borde
 * izquierdo de la ventana y el **suyo derecho**; la otra pareja —izquierda con
 * izquierda— no sujeta nada.
 *
 * Cuando el panel es más grande que la ventana los límites de un eje se cruzan
 * (el mínimo queda por encima del máximo). Las dos variantes se prueban con
 * `min`/`max` en vez de asumir un orden, así que un panel enorme en una ventana
 * de 40 px sigue devolviendo un número y no se sale del rango.
 */
export function sujetar(
  caja: Caja,
  actual: Punto,
  dx: number,
  dy: number,
  viewport: Punto,
): Punto {
  const izq = actual.x + (ASOMA_MIN - caja.right)
  const der = actual.x + (viewport.x - ASOMA_MIN - caja.left)
  const sup = actual.y + (ASOMA_MIN - caja.bottom)
  const inf = actual.y + (viewport.y - ASOMA_MIN - caja.top)
  return {
    x: recortar(actual.x + dx, Math.min(izq, der), Math.max(izq, der)),
    y: recortar(actual.y + dy, Math.min(sup, inf), Math.max(sup, inf)),
  }
}
