import { SECCIONES, type Estado, type Seccion } from '../cort/ventanas'

/**
 * El riel de secciones (CARETA v2, fase A — `docs/REDESIGN-CARETA.md`).
 *
 * Todas las referencias lo pintan igual —`b2-90e21d`, `b2-fb0569`, la demo de
 * Tech Enclair—: una tira vertical fina a la izquierda con dianas circulares,
 * tenue hasta que la mano se acerca. CORT ya tiene las cinco ventanas y el
 * menú; lo que no tenía era **una mano corta**: llegar sin mirar a la esquina
 * de arriba para abrir «sistema» es un dedo torpe. El riel pone cada sección
 * a un pulgar de distancia, con su glifo, su tecla escrita y su anillo
 * encendido cuando la ventana está abierta.
 *
 * No es un menú nuevo ni un estado nuevo: cada botón llama exactamente a lo
 * mismo que la tecla (`alternar`) o a `toggleMenu`, sobre la pila pura de
 * `cort/ventanas.ts` — la misma puerta, un pomos más a mano.
 */
const GLIFOS: Record<Seccion, string> = {
  voz: '≋',
  camara: '◎',
  atuendos: '◍',
  sistema: '⌗',
  ayuda: '?',
}

export function Riel({ estado, onAlternar, onMenu }: {
  estado: Estado
  onAlternar: (s: Seccion) => void
  onMenu: () => void
}) {
  return (
    <nav className="riel" aria-label="secciones de CORT">
      {SECCIONES.map((sec) => {
        const abierta = estado.pilas.includes(sec.id)
        return (
          <button
            key={sec.id}
            type="button"
            className={`riel-btn ${abierta ? 'on' : ''}`}
            onClick={() => onAlternar(sec.id)}
            aria-pressed={abierta}
            title={`${sec.etiqueta} — tecla ${sec.tecla}`}
          >
            <span className="riel-glifo" aria-hidden="true">{GLIFOS[sec.id]}</span>
            <span className="riel-tecla" aria-hidden="true">{sec.tecla}</span>
          </button>
        )
      })}
      <span className="riel-sep" aria-hidden="true" />
      <button
        type="button"
        className={`riel-btn ${estado.menu ? 'on' : ''}`}
        onClick={onMenu}
        aria-pressed={estado.menu}
        title="menú de secciones — tecla m"
      >
        <span className="riel-glifo" aria-hidden="true">◈</span>
        <span className="riel-tecla" aria-hidden="true">m</span>
      </button>
    </nav>
  )
}
