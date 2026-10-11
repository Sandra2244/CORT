import { useEffect, useRef, useSyncExternalStore } from 'react'
import { getSnapshot, subscribe } from '../cort/connection'

/**
 * El punto de entrada.
 *
 * Regla del rediseño (R1, revisitada por CARETA v2): en reposo la pantalla es
 * cockpit — reactor, barra de comandos, riel, carcasa y ESTE botón. Antes era
 * una pestaña con texto («⌃ mensajes»); ahora es
 * un punto de luz en la esquina, que es como lo pintan todas las referencias:
 * un indicio, no un letrero. El contador de mensajes llegados por leer sigue
 * ahí — es la única palabra que se permite, y sólo cuando hay algo que decir.
 *
 * El `aria-label` conserva la explicación completa para quien lee la pantalla
 * con lector de pantalla: que el botón sea mudo no significa que el interfaz
 * lo sea.
 */
export function Bandeja({ abierto, onToggle }: { abierto: boolean; onToggle: () => void }) {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  const vistos = useRef(s.msgs.length)

  useEffect(() => {
    if (abierto) vistos.current = s.msgs.length
  }, [abierto, s.msgs.length])

  const sinLeer = Math.max(0, s.msgs.length - vistos.current)

  return (
    <button
      type="button"
      className={`esquina ${abierto ? 'abierta' : ''}`}
      onClick={onToggle}
      aria-expanded={abierto}
      aria-label={abierto ? 'ocultar la conversación' : 'mostrar la conversación'}
    >
      <span className="esquina-nucleo" aria-hidden="true" />
      {!abierto && sinLeer > 0 && <span className="esquina-aviso">{sinLeer}</span>}
    </button>
  )
}
