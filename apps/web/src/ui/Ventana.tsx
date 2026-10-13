import { useRef, type ReactNode } from 'react'
import { useArrastre } from '../cort/arrastre'

/**
 * La ventana de vidrio: la única superficie que CORT pone encima de su cara.
 *
 * Por qué existe este archivo en vez de seguir repitiendo `<div>` sueltos: el
 * rediseño anterior tenía DOS formas de panel (la bandeja del HUD y un `<dialog>`
 * modal de cinco pestañas) y las dos se pintaban, se arrastraban y se cerraban
 * distinto. Reestructurar la base significa eso: **una sola primitiva** y todo lo
 * demás contenido dentro. Voz, cámara, cuerpo, sistema, ayuda y conversación son
 * hoy instancias de esta ventana; si mañana se añade el ecualizador, no escribe
 * CSS ni lógica de arrastre nueva.
 *
 * La gramática es la de las referencias que trajo Sandra (el JARVIS de
 * @techencclair y las ventanas flotantes de `jaredrhod/fullstack-agent`): el
 * holograma es la cara, la información vive en ventanas de cristal que se pueden
 * **mover y echar** sin quitar al reactor de en medio. De `fullstack-agent` sólo
 * está copiada la *idea* — es AGPL-3.0 y de ahí no se traslada ni una línea.
 *
 * Tres decisiones que no son de adorno:
 * - **No es modal.** Un `<dialog>` con `showModal()` oscurece el fondo y deja
 *   una sola superficie a la vez; aquí se pueden tener dos o tres ventanas
 *   abiertas y colocarlas alrededor del orbe. El orden se gestiona con un
 *   `z-index` por ventana (`marco`), no con el foco atrapado.
 * - **Se arrastra del tubo de arriba** (`useArrastre`, transplantado de
 *   adewaskar/JARVIS, MIT), con sujeción: siempre quedan 72 px asomando, así un
 *   dedo nunca pierde una ventana en el borde de la pantalla.
 * - **El cierre es un botón visible.** Antes no lo había («se cierra con Esc o
 *   pulsando fuera») y en el teléfono no hay teclado ni fuera claro: si la
 *   ventana no se puede echar con el pulgar, la interfaz no es táctil.
 */

export type IdVentana = 'charla' | 'voz' | 'camara' | 'cuerpo' | 'sistema' | 'ayuda'

/** Dónde aterriza cada ventana la primera vez, en clases CSS (`.ventana--x`). */
export function clasePorDefecto(id: IdVentana): string {
  return `ventana--${id}`
}

export function Ventana({
  id,
  titulo,
  marco,
  alCerrar,
  alTraer,
  children,
}: {
  id: IdVentana
  /** Lo que se lee en el tubo. En español y en minúscula: es un rótulo, no un aviso. */
  titulo: string
  /** Profundidad: la última ventana usada queda delante de las demás. */
  marco: number
  alCerrar: () => void
  alTraer: () => void
  children: ReactNode
}) {
  const { pos, tirando, agarrar, reiniciar, nodo, desplazado } = useArrastre<HTMLDivElement>()
  const caja = useRef<HTMLDivElement>(null)

  /**
   * Sacudir hacia abajo despide la ventana — el gesto táctil que ella pidió el
   * 2026-10-09 («con gestos táctiles los quita, puede colocar, mover»).
   *
   * Se mide el **recorrido del dedo**, no la posición final de la ventana: los
   * topes de `useArrastre` sujetan el panel para que nunca se pierda, y abajo del
   * todo ya no hay hacia dónde bajarlo. Medido sobre la ventana «ayuda» a 536×521:
   * un jalon de 150 px se recortaba a ~40 y la ventana no se cerraba — el gesto
   * sería inerte justo en el borde donde alguien lo intenta. Con el recorrido del
   * puntero, el dedo manda y el cristal obedece.
   *
   * El umbral (90 px) está por encima del temblor normal al agarrar y por debajo
   * de lo que se hace de verdad para echar algo. Y sigue habiendo `✕`: el gesto es
   * un atajo, no el único camino — un gesto invisible que además fuera la única
   * salida es una trampa.
   */
  const dedo = useRef<{ y: number; suelto: (e: PointerEvent) => void } | null>(null)

  function empezar(e: React.PointerEvent) {
    const y0 = e.clientY
    const suelto = (ev: PointerEvent) => {
      window.removeEventListener('pointerup', suelto)
      window.removeEventListener('pointercancel', suelto)
      dedo.current = null
      if (ev.clientY - y0 > 90) alCerrar()
    }
    dedo.current = { y: y0, suelto }
    window.addEventListener('pointerup', suelto)
    window.addEventListener('pointercancel', suelto)
  }

  function soltarAsa(e: React.PointerEvent) {
    // Si el pulsado cae sobre `✕` o `⤾`, `useArrastre` ya lo descarta; aquí igual,
    // para que cerrar la ventana no cuente además como jalon.
    if ((e.target as HTMLElement).closest('button')) return
    empezar(e)
    agarrar(e)
  }

  return (
    <div
      ref={caja}
      className={`ventano ${clasePorDefecto(id)} ${tirando ? 'tirando' : ''}`}
      style={{
        transform: `translate(${pos.x}px, ${pos.y}px)`,
        zIndex: marco,
        // `--marco - 10` es el puesto en la pila; en móvil desplaza el aterrizaje
        // 46 px por ventana abierta para que ninguna quede enterrada (ver
        // `index.css`, `@media (max-width: 760px)`).
        ['--apilado' as string]: `${(marco - 10) * 46}px`,
      }}
      // Traer al frente con sólo tocarla (dentro o fuera del tubo) es lo que
      // hace que dos ventanas abiertas no sean un problema: la que se usa queda
      // arriba, sin menús ni gestos raros.
      onPointerDown={alTraer}
      role="dialog"
      aria-label={titulo}
    >
      <div className="ventana" ref={nodo}>
        <header className="ventana-tubo" onPointerDown={soltarAsa}>
          <span className="ventana-titulo">{titulo}</span>
          <span className="ventana-botones">
            {desplazado && (
              <button
                type="button"
                className="ventana-colocar"
                onClick={reiniciar}
                aria-label={`Devolver ${titulo} a su sitio`}
                title="Devolver a su sitio"
              >
                ⤾
              </button>
            )}
            <button
              type="button"
              className="ventana-cerrar"
              onClick={alCerrar}
              aria-label={`Cerrar ${titulo}`}
              title="Cerrar (Esc)"
            >
              ✕
            </button>
          </span>
        </header>
        <div className="ventana-cuerpo">{children}</div>
      </div>
    </div>
  )
}
