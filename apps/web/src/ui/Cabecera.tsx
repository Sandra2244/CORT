import { useEffect, useState, useSyncExternalStore } from 'react'
import { getSnapshot, subscribe } from '../cort/connection'
import { FASE_TEXTO } from '../cort/fase'
import { useArrastre } from '../cort/arrastre'

/**
 * La hora de CORT — y ahora **se mueve**.
 *
 * Rediseño R1 (docs/REDESIGN-UI.md): en reposo la pantalla tiene exactamente
 * tres cosas — el reactor, el reloj y un punto de entrada. N1
 * (docs/REDESIGN-NUCLEO.md) le añade una palabra a la tercera: el reloj, como
 * en las referencias en video, **se agarra y se lleva** — quien pone un
 * cronómetro encima del reactor puede apartar la hora con el dedo. La sujeción
 * es la misma de siempre (`cort/arrastre.ts`), y `⤾` lo devuelve arriba al
 * centro. `translate` (centrado) e `inline transform` (arrastre) siguen siendo
 * propiedades separadas a propósito: se componen y no se pisan.
 *
 * El puntito del lado derecho es el cable: verde-azulado si el core contesta,
 * rojo si no. Desde N9 el punto además **respira con la fase** (escucha,
 * piensa, habla): color y latido salen de `Snapshot.fase`, y el `title` dice la
 * palabra. Sigue siendo un punto y no una frase — «Sin conexión con el core —
 * ejecuta: make dev» sigue existiendo, pero dentro de la bandeja, que es donde
 * alguien que va a arreglar algo la necesita.
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
  const { pos, tirando, agarrar, reiniciar, nodo, desplazado } = useArrastre<HTMLDivElement>()
  return (
    <div
      ref={nodo}
      className={`reloj${tirando ? ' tirando' : ''}`}
      style={{ transform: `translate(${pos.x}px, ${pos.y}px)` }}
      onPointerDown={agarrar}
      aria-label="hora y conexión — se agarra y se mueve"
    >
      <Reloj />
      <span
        className={`dot ${s.online ? `on fase-${s.fase}` : 'off'}`}
        title={s.online ? FASE_TEXTO[s.fase] : 'sin conexión con el core'}
      />
      {desplazado && (
        <button
          type="button"
          className="reloj-colocar"
          onClick={reiniciar}
          aria-label="Devolver el reloj a su sitio"
          title="Devolver el reloj a su sitio"
        >
          ⤾
        </button>
      )}
    </div>
  )
}
