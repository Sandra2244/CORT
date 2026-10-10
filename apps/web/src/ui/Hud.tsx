import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { getSnapshot, pintaFaltaDeLlave, send, subscribe } from '../cort/connection'
import { palette } from '../cort/palette'
import { useArrastre } from '../cort/arrastre'
import type { Pestana } from './Panel'

/**
 * La conversación (capa L2 abierta).
 *
 * Rediseño por capas (docs/REDESIGN-UI.md, R1/R2): este panel **antes** era la
 * cara entera — cabezal con estado, atuendo, ciudad y clima, el riel de botones
 * de cámara/voz/atuendos con sus párrafos de manual, el registro y el
 * formulario. Hoy sólo es el registro y el formulario: el estado viaja en el
 * color del anillo (y en el puntito de `Cabecera`), las herramientas se mudaron
 * al modal `Panel`, y la línea que CORT dice en voz alta la subtitula
 * `Respuesta` sin necesidad de abrir nada.
 *
 * Lo que se conserva tal cual porque ya estaba medido y bien:
 * - el arrastre con sujeción (`useArrastre`) y los dos nodos (`hud-marco` para
 *   el desplazamiento, `hud` para el temblor del efecto `shake`),
 * - el registro con auto-scroll,
 * - `aria-hidden` + `visibility` en retardo cuando está guardado, para que los
 *   campos ocultos no sigan en el orden de tabulación.
 */
export function Hud({ abierto, invocar, onAbrirPanel }: {
  abierto: boolean
  /** Contador que sube cuando alguien invocó la entrada (tap al núcleo o `Ctrl+/`). */
  invocar: number
  onAbrirPanel: (pestana?: Pestana) => void
}) {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  const [draft, setDraft] = useState('')
  const log = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const tint = palette[s.outfit] ?? palette.work
  const { pos, tirando, agarrar, reiniciar, nodo, desplazado } = useArrastre<HTMLDivElement>()

  useEffect(() => {
    log.current?.scrollTo({ top: log.current.scrollHeight })
  }, [s.msgs.length])

  // La invocación pide el cursor puesto: quien toca el núcleo o pulsa Ctrl+/
  // quiere escribir, no mirar un campo vacío.
  useEffect(() => {
    if (abierto && invocar > 0) input.current?.focus()
  }, [abierto, invocar])

  /**
   * Comandos locales escritos en la propia bandeja, como en las referencias
   * (el señor de `fullstack-agent` invoca la cámara hablando): la frase abre su
   * pestaña del modal **además** de viajar al core, para que quede en el
   * registro y CORT pueda comentarla. No reemplaza al modelo — le ahorra a la
   * usuaria buscar el botón con el dedo.
   */
  const LOCALES: [RegExp, Pestana][] = [
    [/(?:activa|abre|enciende|prende)\s+(?:la\s+|mi\s+)?c[áa]mara/i, 'camara'],
    [/(?:activa|abre)\s+(?:el\s+|la\s+)?(?:micr[oó]fono|voz)/i, 'voz'],
    [/(?:cambia|pon|muestra|elige)\s+(?:el\s+|mi\s+)?atuendo/i, 'atuendos'],
    [/(?:estado|diagn[oó]stico|sistema)/i, 'sistema'],
  ]

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const text = draft.trim()
    if (!text) return
    const local = LOCALES.find(([re]) => re.test(text))
    if (local) onAbrirPanel(local[1])
    send(text)
    setDraft('')
  }

  return (
    <div
      className={`hud-marco ${tirando ? 'tirando' : ''}`}
      style={{ transform: `translate(${pos.x}px, ${pos.y}px)` }}
    >
      <div className="hud" ref={nodo} style={{ ['--tint' as string]: tint.ui }}>
        <span className="asa" aria-hidden="true" onPointerDown={agarrar} />
        <div className={`cuerpo ${abierto ? '' : 'cerrado'}`} aria-hidden={!abierto}>
          <header className="status" onPointerDown={agarrar}>
            {!s.online && (
              <span className="status-aviso">
                {pintaFaltaDeLlave()
                  // El rechazo del core por no traer llave llega al navegador como un
                  // `403` sin motivo legible (heredado de `v0.10`): si la página se
                  // abrió desde otro equipo y no trae `?token=`, eso es exactamente
                  // lo que pasó, y decirlo ahorra buscar un core que sí está arriba.
                  ? 'falta la llave de la red — abre la dirección que imprime cort.py --lan'
                  : 'sin conexión con el core — ejecuta: make dev'}
              </span>
            )}
            <span className="status-herramientas">
              {desplazado && (
                <button
                  type="button"
                  className="hud-colocar"
                  onClick={reiniciar}
                  aria-label="Devolver el panel a su sitio"
                  title="Devolver el panel a su sitio"
                >
                  ⤾
                </button>
              )}
              <button type="button" className="hud-ajustes" onClick={() => onAbrirPanel()}>
                ajustes
              </button>
            </span>
          </header>

          <div className="log" ref={log} role="log" aria-live="polite">
            {s.msgs.map((m, i) => (
              <p key={i} className={m.from === 'user' ? 'me' : 'cort'}>{m.text}</p>
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
            <button type="submit" disabled={!s.online}>Enviar</button>
          </form>
        </div>
      </div>
    </div>
  )
}
