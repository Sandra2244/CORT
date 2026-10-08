import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { getSnapshot, send, subscribe } from '../cort/connection'
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
        <Clock />
      </header>

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
