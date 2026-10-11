import { useEffect, useState, useSyncExternalStore } from 'react'
import { getSnapshot, subscribe } from '../cort/connection'
import { FASE_TEXTO } from '../cort/fase'
import { fechaCorta, hhmmss } from '../cort/hora'

/**
 * La barra de mando (CARETA v2, fase A — `docs/REDESIGN-CARETA.md`).
 *
 * El gesto más grande del rediseño: **la pantalla entera es el HUD**. La
 * referencia lo dice sin ambigüedad —en la demo en vivo de Tech Enclair y en
 * los videos de `b2-90e21d`/`fd38b8` la cabina no es un panel suelto, es un
 * marco—: una barra fija arriba lleva la palabra mayor de la pantalla, el
 * reloj `HH:MM:SS` en monoespaciada con resplandor, y a sus lados la marca,
 * el estado y la fecha. El reloj flotante y agarrable de N1 se retira con
 * este cambio: su función (ver la hora sin abrir nada) la cubre ahora la
 * barra, y el arrastre vive desde siempre en las ventanas y en la bandeja.
 *
 * La hora se formatea con `cort/hora.ts` —el mismo `hhmmss` probado de la
 * bandeja (N13)—, no con `toLocaleTimeString`: formato fijo 24 h y pruebas
 * que no mienten según el `locale`.
 *
 * El temporizador es el de siempre: un `setTimeout` hasta el siguiente segundo
 * exacto y luego un `setInterval` de a uno, **dentro de este componente y no
 * en el snapshot** — colgado del estado global, cada segundo reconciliaría el
 * árbol entero en una máquina de dos núcleos.
 *
 * Nada de lo que dice la barra es decorativo: la fase la resuelve
 * `faseDe` (N9), el punto respira con ella, y el chip de red es el `online`
 * del WebSocket. Una cabina que miente no es una cabina.
 */
export function Barra() {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    let tick = 0
    const align = window.setTimeout(() => {
      setNow(new Date())
      tick = window.setInterval(() => setNow(new Date()), 1000)
    }, 1000 - (Date.now() % 1000))
    return () => {
      clearTimeout(align)
      clearInterval(tick)
    }
  }, [])

  return (
    <header className="barra">
      <div className="barra-izq">
        <span className="barra-marca" aria-hidden="true">C·O·R·T</span>
        <span
          className={`dot ${s.online ? `on fase-${s.fase}` : 'off'}`}
          title={s.online ? FASE_TEXTO[s.fase] : 'sin conexión con el core'}
        />
        <span className={`barra-fase fase-${s.online ? s.fase : 'off'}`}>
          {s.online ? FASE_TEXTO[s.fase] : 'buscando el core'}
        </span>
      </div>
      <time className="barra-reloj" dateTime={now.toISOString()}>{hhmmss(now)}</time>
      <div className="barra-der">
        <span className="barra-fecha">{fechaCorta(now)}</span>
        <span className={`barra-red ${s.online ? 'on' : ''}`}>{s.online ? 'en línea' : 'sin core'}</span>
      </div>
    </header>
  )
}
