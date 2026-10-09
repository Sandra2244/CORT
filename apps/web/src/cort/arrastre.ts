import { useCallback, useRef, useState } from 'react'

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
 * Lo que CORT añade y el original no necesitaba: la **sujeción**. Un panel de
 * escritorio se puede tirar fuera de la pantalla; un HUD que desaparece no se
 * puede volver a agarrar, así que siempre tienen que quedar píxeles asomando por
 * algún borde.
 */

/** Píxeles del panel que han de seguir visibles por dondequiera que se arrastre. */
const ASOMA_MIN = 72

type Punto = { x: number; y: number }

function recortar(v: number, min: number, max: number): number {
  return Math.min(Math.max(v, min), max)
}

/**
 * El destino tras un paso de `dx`/`dy`, con el panel ya donde está.
 *
 * `caja` es el rectángulo **ya con el desplazamiento aplicado** (es lo que
 * devuelve `getBoundingClientRect`) y `actual` la posición del panel en este
 * instante, así que el tope se calcula en cada cuadro y sobre el cuadro que se
 * acaba de dar. No una vez al agarrar y sobre el arrancada entera: el propio panel
 * cambia de alto a media arrancada —el botón de recolocar aparece y la barra
 * partida se va a una segunda línea—, y con la medida vieja el tope se queda
 * corto unos 25 px.
 *
 * Cada borde se empareja con el opuesto de la ventana: para que el panel siga
 * asomando por la izquierda tiene que haber por lo menos `ASOMA_MIN` píxeles entre
 * el borde izquierdo de la ventana y el **suyo derecho**. La otra pareja —izquierda
 * con izquierda— no sujeta nada, y fue la que dejó el panel sin poder moverse ni un
 * píxel hacia abajo desde su propio sitio.
 *
 * Cuando el panel es más ancho que la ventana los límites de un eje se cruzan (el
 * mínimo queda por encima del máximo); las dos variantes se prueban con `min`/`max`
 * en vez de asumir un orden.
 */
function sujetar(caja: DOMRect, actual: Punto, dx: number, dy: number): Punto {
  const izq = actual.x + (ASOMA_MIN - caja.right)
  const der = actual.x + (window.innerWidth - ASOMA_MIN - caja.left)
  const sup = actual.y + (ASOMA_MIN - caja.bottom)
  const inf = actual.y + (window.innerHeight - ASOMA_MIN - caja.top)
  return {
    x: recortar(actual.x + dx, Math.min(izq, der), Math.max(izq, der)),
    y: recortar(actual.y + dy, Math.min(sup, inf), Math.max(sup, inf)),
  }
}

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
      setPos((actual) => sujetar(el.getBoundingClientRect(), actual, dx, dy))
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
