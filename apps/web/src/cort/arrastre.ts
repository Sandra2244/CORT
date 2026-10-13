import { useCallback, useRef, useState } from 'react'
import { sujetar } from './asoma'
import type { Punto } from './asoma'

/**
 * Arrastrar un panel con el dedo o con el ratón.
 *
 * El patrón de escucha viene de `src/ui/Blades.tsx` de **adewaskar/JARVIS** (MIT,
 * copia local de octubre de 2026; atribución en `apps/web/CREDITS.md`), junto con
 * la decisión que allí está documentada y que aquí se repite por el mismo motivo:
 * los escuchadores van en `window`, no en el elemento. Un dedo sobre una barra
 * de 40 px sale de ella en el primer movimiento; si el `pointermove` estuviera
 * pegado a la barra, la arrancada se cortaría al primer cuadro y el panel
 * quedaría medio cogido. Escuchando en `window` el evento sigue llegando aunque
 * el puntero ya no esté encima del asa, y en cuanto sueltas dejan de escucharse
 * los tres: no queda ningún escuchador pendiente mientras el panel está quieto.
 *
 * Lo que CORT añade y el original no necesitaba: la **sujeción** — un panel de
 * escritorio se puede tirar fuera de la pantalla, y un HUD que desaparece no se
 * puede volver a agarrar. Esa geometría ya no vive aquí: se fue a `cort/asoma.ts`
 * (función 82), que es pura, sin `window` ni nodos, y lleva sus pruebas porque
 * **ya estuvo equivocada una vez**: los topes emparejaban el borde de arriba del
 * panel con el de arriba de la ventana y, desde su propio sitio, no se podía
 * arrastrar hacia abajo ni un píxel. Aquí queda lo que sí necesita un DOM: medir
 * el nodo, leer el tamaño de la ventana y enterarse de los puntos del puntero.
 */

export type { Punto } from './asoma'

/**
 * Devuelve el desplazamiento del panel, si se está tirando de él ahora mismo y
 * la función que empieza la arrancada. `nodo` es el elemento que se mide para
 * los topes: el panel visible, no el marco que lleva el `transform`.
 */
export function useArrastre<T extends HTMLElement = HTMLDivElement>() {
  const [pos, setPos] = useState<Punto>({ x: 0, y: 0 })
  const [tirando, setTirando] = useState(false)
  const nodo = useRef<T | null>(null)
  /** Un solo arrastre a la vez: con dos dedos en la barra ganarían los dos. */
  const enCurso = useRef(false)

  const agarrar = useCallback((e: React.PointerEvent) => {
    // Los controles viven en la misma barra que sirve de asa: si no, empezar a
    // arrastrar desde el botón de recolocar se comería su propio clic.
    if ((e.target as HTMLElement).closest('button,input,a')) return
    if (enCurso.current) return
    const el = nodo.current
    if (!el) return

    e.preventDefault()
    enCurso.current = true
    setTirando(true)

    let ultX = e.clientX
    let ultY = e.clientY

    const mover = (ev: PointerEvent) => {
      const dx = ev.clientX - ultX
      const dy = ev.clientY - ultY
      ultX = ev.clientX
      ultY = ev.clientY
      if (!dx && !dy) return
      setPos((actual) =>
        // El tope se recalcula cada cuadro, sobre la caja que el panel tiene
        // ahora: cambia de alto a media arrancada cuando asoma el `⤾`.
        sujetar(el.getBoundingClientRect(), actual, dx, dy, {
          x: window.innerWidth,
          y: window.innerHeight,
        }),
      )
    }

    const soltar = () => {
      enCurso.current = false
      setTirando(false)
      window.removeEventListener('pointermove', mover)
      window.removeEventListener('pointerup', soltar)
      window.removeEventListener('pointercancel', soltar)
    }

    window.addEventListener('pointermove', mover)
    window.addEventListener('pointerup', soltar)
    window.addEventListener('pointercancel', soltar)
  }, [])

  const reiniciar = useCallback(() => setPos({ x: 0, y: 0 }), [])

  return { pos, tirando, agarrar, reiniciar, nodo, desplazado: pos.x !== 0 || pos.y !== 0 }
}
