import { useEffect, useState, useSyncExternalStore } from 'react'
import { getSnapshot, subscribe } from '../cort/connection'

/**
 * La hora de CORT — y ahora **es** el cabezal.
 *
 * Rediseño por capas (docs/REDESIGN-UI.md, R1): en reposo la pantalla tiene
 * exactamente tres cosas — el reactor, el reloj y un punto de entrada. Todo lo
 * que antes viajaba por la barra de estado (atuendo, ciudad, clima, el texto
 * «CORT en línea») se comunica de otra forma: el estado va en el COLOR del
 * anillo, que ya lo llevaba, y los datos se leen en la pestaña «sistema» del
 * modal. Lo que se queda aquí es lo único que alguien mira sin pedirlo: la hora.
 *
 * El puntito del lado derecho es el cable: verde-azulado si el core contesta,
 * rojo si no. Un punto y no una frase — «Sin conexión con el core — ejecuta:
 * make dev» sigue existiendo, pero dentro de la bandeja, que es donde alguien
 * que va a arreglar algo la necesita.
 *
 * Mismo `Clock()` de antes: componente con su propio temporizador, alineado al
 * segundo exacto y con `tabular-nums`. Si la hora viviera en el snapshot global,
 * cada segundo reconciliaría el árbol entero en una máquina de dos núcleos.
 */
function Reloj() {
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
    <time dateTime={now.toISOString()}>
      {now.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })}
    </time>
  )
}

export function Cabecera() {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  return (
    <div className="reloj" aria-label="hora y conexión">
      <Reloj />
      <span className={`dot ${s.online ? 'on' : 'off'}`} title={s.online ? 'CORT en línea' : 'sin conexión con el core'} />
    </div>
  )
}
