import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { getSnapshot, pintaFaltaDeLlave, send, subscribe } from '../cort/connection'
import { palette } from '../cort/palette'
import { useArrastre } from '../cort/arrastre'
import { FASE_TEXTO } from '../cort/fase'
import { fechaCorta, hhmmss, remitente } from '../cort/hora'
import type { Seccion } from '../cort/ventanas'

/**
 * La conversación (capa L2 abierta).
 *
 * Rediseño por capas (docs/REDESIGN-UI.md, R1/R2): este panel **antes** era la
 * cara entera — cabezal con estado, atuendo, ciudad y clima, el riel de botones
 * de cámara/voz/atuendos con sus párrafos de manual, el registro y el
 * formulario. Hoy sólo es el registro y el formulario: el estado viaja en el
 * color del anillo (y en el punto de `Barra`), las herramientas se mudaron
 * a las ventanas de vidrio (`ui/Ventanas.tsx`, N1) —con el menú de secciones
 * (`ui/Menu.tsx`, N4) como puerta única— y la línea que CORT dice en voz alta
 * la subtitula `Respuesta` sin necesidad de abrir nada.
 *
 * N13 — bandeja viva (docs/TRANSPLANTE.md, la gramática visual de Tech
 * Enclair reescrita: de su proyecto no viaja ni una línea, la licencia no es
 * estándar). Lo que le faltaba a la bandeja era exactamente lo que las
 * referencias le sobra: **que hable de sí misma mientras está abierta**. Una
 * barra de mando con la fase, la hora con segundos, la fecha y el estado de la
 * red; cada fila del registro con su etiqueta de quién habló; corchetes en las
 * esquinas del marco; botón circular de envío; y una marca de agua al pie. El
 * reloj de la barra no basta: está arriba, lejos del panel, y la conversación
 * quiere el minuto a minuto junto a las filas.
 *
 * Lo que se conserva tal cual porque ya estaba medido y bien:
 * - el arrastre con sujeción (`useArrastre`) y los dos nodos (`hud-marco` para
 *   el desplazamiento, `hud` para el temblor del efecto `shake`),
 * - el registro con auto-scroll,
 * - `aria-hidden` + `visibility` en retardo cuando está guardado, para que los
 *   campos ocultos no sigan en el orden de tabulación.
 */
export function Hud({ abierto, invocar, onAbrirVentana, onAbrirMenu }: {
  abierto: boolean
  /** Contador que sube cuando alguien invocó la entrada (tap al núcleo o `Ctrl+/`). */
  invocar: number
  onAbrirVentana: (seccion?: Seccion) => void
  /** N4: el botón de la barra ya no abre «la ventana de siempre», abre el lanzador. */
  onAbrirMenu: () => void
}) {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  const [draft, setDraft] = useState('')
  const log = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const tint = palette[s.outfit] ?? palette.work
  const { pos, tirando, agarrar, reiniciar, nodo, desplazado } = useArrastre<HTMLDivElement>()

  /**
   * N13: la hora de la barra de mando. El `setInterval` **sólo existe mientras
   * la bandeja está abierta** — en reposo este componente no tiene ningún
   * temporizador vivo, la misma disciplina del `Temporizador` y del "no hay
   * reloj que mienta sin servidor" de `connection.ts`.
   */
  const [ahora, setAhora] = useState(() => new Date())
  useEffect(() => {
    if (!abierto) return
    setAhora(new Date())
    const t = window.setInterval(() => setAhora(new Date()), 1000)
    return () => clearInterval(t)
  }, [abierto])

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
   * ventana de vidrio **además** de viajar al core, para que quede en el
   * registro y CORT pueda comentarla. No reemplaza al modelo — le ahorra a la
   * usuaria buscar el botón con el dedo.
   */
  const LOCALES: [RegExp, Seccion][] = [
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
    if (local) onAbrirVentana(local[1])
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
          {/* La barra de mando (N13): fase, hora con segundos, fecha y red. En
              las referencias el panel abierto siempre dice algo de sí mismo
              antes de decir nada de ti; aquí esos datos son todos ciertos —
              la fase la resuelve `faseDe`, la hora es la del reloj de la
              máquina, y el estado de red es el del cable, no un adorno. */}
          <div className="hud-cab">
            <span className={`hud-fase fase-${s.fase}`}>{FASE_TEXTO[s.fase]}</span>
            <span className="hud-punto" aria-hidden="true">·</span>
            <span className="hud-fecha">{fechaCorta(ahora)}</span>
            <span className="hud-reloj" aria-hidden="true">{hhmmss(ahora)}</span>
            <span className={`hud-red ${s.online ? 'on' : ''}`}>{s.online ? 'en línea' : 'sin core'}</span>
          </div>
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
              <button type="button" className="hud-ajustes" onClick={onAbrirMenu}>
                menú
              </button>
            </span>
          </header>

          <div className="log" ref={log} role="log" aria-live="polite">
            {s.msgs.length === 0 && (
              // R4 pedía estados vacíos diseñados y la bandeja era la asignatura
              // suspendida: un panel abierto en negro no invita, intimida. La
              // línea dice qué hay detrás del cristal sin prometer nada falso —
              // si el core no contesta, el aviso de arriba ya lo dice también.
              <p className="vacia">aún no hay conversación — pulsa <kbd>/</kbd> y dile algo a CORT</p>
            )}
            {s.msgs.map((m, i) => (
              <p key={i} className={`fila ${m.from === 'user' ? 'me' : 'cort'}`}>
                <span className="quien" aria-hidden="true">{remitente(m.from)}</span>
                <span className="texto">{m.text}</span>
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
            {/* El botón de texto «Enviar» se volvió la flecha circular de las
                referencias: 46 px de blanco fácil para el dedo, y la flecha se
                entiende sin leer — la etiqueta completa vive en el `aria-label`. */}
            <button type="submit" className="enviar" disabled={!s.online} aria-label="Enviar a CORT" title="Enviar a CORT">↑</button>
          </form>
          <div className="hud-pie" aria-hidden="true">cort · local</div>
        </div>
      </div>
    </div>
  )
}
