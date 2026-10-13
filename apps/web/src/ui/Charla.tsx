import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { getSnapshot, pintaFaltaDeLlave, send, subscribe } from '../cort/connection'
import { ventanaPorComando } from '../cort/comandos'
import type { IdVentana } from './Ventana'

/**
 * El cuerpo de la ventana «charla»: registro + entrada. Nada más.
 *
 * Es lo que quedó del antiguo `Hud.tsx` cuando la interfaz se reestructuró. El
 * HUD de antes cargaba encima su cabecera de estado, el botón «ajustes», el asa
 * de arrastre y la telemetría; ese chrome ahora es de `Ventana` (una vez para
 * todas) y el punto de luz de la esquina es del `Muelle`. Quitarlos de aquí no
 * es estética: es que **estaban duplicados** en las dos superficies, y un interfaz
 * con dos formas de hacer lo mismo es el principio de por qué se veía desordenado.
 *
 * El auto-scroll y el foco al invocar se conservan tal cual, porque ya estaban
 * medidos y porque sin ellos la ventana es un cuadro de texto que no sigue la
 * conversación.
 */

/**
 * Los comandos locales **no se deciden aquí**: viven en `cort/comandos.ts`, que es
 * lógica pura y tiene su prueba (`apps/web/tests/comandos.test.mjs`). Lo que el
 * componente aporta es sólo lo que necesita un DOM: recibir el texto, abrir la
 * ventana que el módulo nombre y mandar la frase al core igual.
 */

export function Charla({
  invocar,
  onAbrir,
}: {
  /** Contador que sube cuando alguien invocó la charla (tap al núcleo o `Ctrl+/`). */
  invocar: number
  /** Para que escribir «activa la cámara» también levante esa ventana. */
  onAbrir: (id: IdVentana) => void
}) {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  const [draft, setDraft] = useState('')
  const log = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)

  useEffect(() => {
    log.current?.scrollTo({ top: log.current.scrollHeight })
  }, [s.msgs.length])

  // Quien invoca la charla quiere escribir, no mirar un campo vacío.
  useEffect(() => {
    if (invocar > 0) input.current?.focus()
  }, [invocar])

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const text = draft.trim()
    if (!text) return
    const destino = ventanaPorComando(text)
    if (destino) onAbrir(destino)
    send(text)
    setDraft('')
  }

  return (
    <div className="charla">
      {!s.online && (
        <p className="charla-aviso">
          {pintaFaltaDeLlave()
            // El rechazo del core por no traer llave llega al navegador como un `403`
            // sin motivo legible: si la página se abrió desde otro equipo y no trae
            // `?token=`, eso es exactamente lo que pasó — y decirlo ahorra buscar un
            // core que sí está arriba.
            ? 'falta la llave de la red — abre la dirección que imprime cort.py --lan'
            : 'sin conexión con el core — ejecuta: make dev'}
        </p>
      )}
      <div className="log" ref={log} role="log" aria-live="polite">
        {s.msgs.map((m, i) => (
          <p key={i} className={m.from === 'user' ? 'me' : 'cort'}>
            {m.text}
          </p>
        ))}
      </div>
      <form onSubmit={submit}>
        <input
          ref={input}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Escribe a CORT"
          aria-label="Mensaje a CORT"
          autoComplete="off"
          enterKeyHint="send"
        />
        <button type="submit" disabled={!s.online}>
          Enviar
        </button>
      </form>
    </div>
  )
}
