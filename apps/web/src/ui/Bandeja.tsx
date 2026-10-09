import { useEffect, useRef, useSyncExternalStore } from 'react'
import { getSnapshot, subscribe } from '../cort/connection'

/**
 * La esquina que abre la bandeja.
 *
 * La pantalla de CORT **es el reactor**, no un formulario: el registro de
 * mensajes, la telemetría y los controles están guardados hasta que se piden. Se
 * abren tocando esta esquina con el dedo o pulsándola con el ratón, y se cierran
 * igual — o con `Esc`.
 *
 * El número que sale es cuántos mensajes llegaron con la bandeja cerrada. No es
 * decoración: si CORT contesta mientras la pantalla está limpia, tiene que haber
 * una señal de que algo pasó por leer.
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
      aria-label={abierto ? 'ocultar la bandeja de entrada' : 'mostrar la bandeja de entrada'}
    >
      <span className="esquina-flecha" aria-hidden="true">{abierto ? '⌄' : '⌃'}</span>
      <span className="esquina-texto">{abierto ? 'ocultar' : 'mensajes'}</span>
      {!abierto && sinLeer > 0 && <span className="esquina-aviso">{sinLeer}</span>}
    </button>
  )
}
