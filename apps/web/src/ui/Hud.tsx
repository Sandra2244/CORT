import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { getSnapshot, send, subscribe } from '../cort/connection'
import { palette } from '../cort/palette'

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
        />
        <button type="submit" disabled={!s.online}>Enviar</button>
      </form>
    </div>
  )
}
