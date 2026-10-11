import { useArrastre } from '../cort/arrastre'
import { PROXIMAS, SECCIONES, type Seccion } from '../cort/ventanas'

/**
 * El menú de secciones (N4 de docs/REDESIGN-NUCLEO.md).
 *
 * Las referencias en video no muestran un riel de seis hilos ni una bandeja que
 * abre todo a la vez: muestran un **espacio de trabajo** — una cara que manda
 * y un lanzador desde el que se elige qué ventana flotante ocupar. Eso es este
 * panel: la puerta única a las cinco secciones reales (voz · cámara · atuendos
 * · sistema · ayuda), cada fila con su tecla escrita, y debajo las cuatro
 * secciones **en camino** (agenda N2, consola N3, dispositivos N7, documentos
 * N8) nombradas pero apagadas. Regla 10 de AGENTS.md: se nombra lo que viene,
 * no se simula — una fila gris que dice «en camino — N2» enseña el plan; una
 * fila que abre una ventana vacía enseñaría a desconfiar.
 *
 * Es una ventana de vidrio más, no un modal: fondo vivo, arrastre con sujeción
 * (`useArrastre`, el mismo medido), y el `Esc` la despide **antes** que a las
 * ventanas — es la capa más encima. Abre y cierra con `m` o con el botón
 * «menú» de la bandeja; el estado vive en `ventanas.menu` (puro, probado).
 */
export function Menu({ abierto, onElegir, onCerrar }: {
  abierto: boolean
  onElegir: (id: Seccion) => void
  onCerrar: () => void
}) {
  const { pos, tirando, agarrar, reiniciar, nodo, desplazado } = useArrastre<HTMLElement>()

  // Desmontado, no escondido: en reposo el menú no deja filas ocultas en el
  // orden de tabulación (la lección del `aria-hidden` del viejo HUD).
  if (!abierto) return null

  return (
    <section
      ref={nodo}
      className={`menu vidrio-normal${tirando ? ' tirando' : ''}`}
      style={{ transform: `translate(${pos.x}px, ${pos.y}px)` }}
      aria-label="menú de secciones"
    >
      <header className="ventana-cab" onPointerDown={agarrar}>
        <span className="asa" aria-hidden="true" />
        <span className="ventana-titulo">secciones</span>
        <span className="ventana-botones">
          {desplazado && (
            <button
              type="button"
              className="ventana-colocar"
              onClick={reiniciar}
              aria-label="Devolver el menú a su sitio"
              title="Devolver el menú a su sitio"
            >
              ⤾
            </button>
          )}
          <button
            type="button"
            className="ventana-cerrar"
            onClick={onCerrar}
            aria-label="Cerrar el menú"
            title="Cerrar — la tecla m lo devuelve"
          >
            ✕
          </button>
        </span>
      </header>

      <div className="menu-cuerpo">
        {SECCIONES.map((s) => (
          <button
            key={s.id}
            type="button"
            className="menu-fila"
            onClick={() => onElegir(s.id)}
          >
            <span className="menu-etiqueta">{s.etiqueta}</span>
            <span className="menu-tecla">{s.tecla}</span>
          </button>
        ))}
        {PROXIMAS.map((p) => (
          <div key={p.id} className="menu-fila en-camino" aria-disabled="true">
            <span className="menu-etiqueta">{p.etiqueta}</span>
            <span className="menu-nota">{p.nota}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
