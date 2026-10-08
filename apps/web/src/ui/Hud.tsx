import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { getSnapshot, send, setZoom, subscribe, target, zoomLimits } from '../cort/connection'
import { palette } from '../cort/palette'

/**
 * La hora, en el borde del HUD.
 *
 * Va en su propio componente, con su propio estado, y no en el snapshot del
 * WebSocket: si la hora viajara por ahí, cada segundo se reconciliaría el HUD
 * entero —registro de mensajes incluido— en una máquina de dos núcleos. Así sólo
 * se repinta este nodo.
 *
 * El arranque se alinea con el siguiente cambio de segundo. Un `setInterval` a
 * secas nace cuando nace el componente, y el reloj se queda mirando el valor
 * viejo hasta 999 ms: parece parado, y es justo lo que no debe parecer.
 */
function Clock() {
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
    <time className="clock" aria-label="hora" dateTime={now.toISOString()}>
      {now.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' })}
    </time>
  )
}

/**
 * El tamaño del reactor.
 *
 * Mueve `target.zoom`, no estado de React: el orbe lo persigue con lerp en el
 * bucle de la escena, así que al arrastrar crece en vez de saltar, y el slider
 * no reconcilia el registro de mensajes 60 veces por segundo. Aquí sólo hay un
 * número local para que la cifra «128%» se vea.
 *
 * Botones ± además del slider: en el teléfono el pulgar no acierta con un
 * cursor de 2 px, y un botón de 44 px siempre se toca.
 */
function ZoomControl() {
  const [zoom, setZoomUi] = useState(target.zoom)

  function apply(factor: number) {
    // `setZoom` recorta al margen y devuelve el valor ya válido: la UI pinta el
    // recortado, no el que se pidió. Si no, el slider quedaría mentiroso al
    // llegar al fondo.
    setZoomUi(setZoom(factor))
  }

  return (
    <div className="zoom">
      <span className="zoom-label">tamaño</span>
      <button type="button" className="zoom-btn" aria-label="reducir el reactor" onClick={() => apply(zoom - 0.2)}>−</button>
      <input
        className="zoom-slider"
        type="range"
        min={zoomLimits.min}
        max={zoomLimits.max}
        step={0.02}
        value={zoom}
        onChange={(e) => apply(Number(e.target.value))}
        aria-label="tamaño del reactor"
      />
      <button type="button" className="zoom-btn" aria-label="agrandar el reactor" onClick={() => apply(zoom + 0.2)}>+</button>
      <span className="zoom-value">{Math.round(zoom * 100)}%</span>
    </div>
  )
}

export function Hud() {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  const [draft, setDraft] = useState('')
  const log = useRef<HTMLDivElement>(null)
  const tint = palette[s.outfit] ?? palette.work

  useEffect(() => {
    log.current?.scrollTo({ top: log.current.scrollHeight })
  }, [s.msgs.length])

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const text = draft.trim()
    if (!text) return
    send(text)
    setDraft('')
  }

  return (
    <div className="hud" style={{ ['--tint' as string]: tint.ui }}>
      <header className="status">
        <span className={`dot ${s.online ? 'on' : 'off'}`} />
        {s.online ? (s.thinking ? 'CORT procesando' : 'CORT en línea') : 'Sin conexión con el core — ejecuta: make dev'}
        {s.online && <em> · atuendo {s.outfit}</em>}
        {/* El clima sólo se pinta si el core lo midió: sin CORT_CITY en el .env
            no hay ciudad, y una pantalla que pusiera «—°» estaría inventando un
            dato que no pidió nadie. */}
        {s.clima && (
          <em>
            {' · '}
            {/* El cabezal va en minúsculas por estilo, pero el nombre de una
                ciudad no es estilo: es un nombre propio. Esta parte escapa de
                la conversión para que Bogotá siga escribiéndose Bogotá. */}
            <span className="city">{s.clima.city}</span> {s.clima.temp_c.toFixed(0)}°
          </em>
        )}
        <Clock />
      </header>

      <ZoomControl />

      <div className="log" ref={log} role="log" aria-live="polite">
        {s.msgs.map((m, i) => (
          <p key={i} className={m.from === 'user' ? 'me' : 'cort'}>{m.text}</p>
        ))}
      </div>

      <form onSubmit={submit}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Escribe a CORT"
          aria-label="Mensaje a CORT"
          autoComplete="off"
          enterKeyHint="send"
        />
        <button type="submit" disabled={!s.online}>Enviar</button>
      </form>
    </div>
  )
}
