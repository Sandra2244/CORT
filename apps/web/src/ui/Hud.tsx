import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { getSnapshot, send, setZoom, subscribe } from '../cort/connection'
import { iniciarCamara, type Muestra } from '../cort/defocus'
import { useArrastre } from '../cort/arrastre'
import { Atuendos } from './Avatar'
import { Voz } from './Voz'
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
 * El porqué del texto de error, en orden de lo que pasa de verdad: primero el
 * navegador no da contexto seguro, luego el usuario no dio permiso, y al final la
 * cámara está ocupada.
 *
 * Van separados a propósito. Decir «necesitas HTTPS» cuando el contexto sí era
 * seguro y quien negó el acceso fue el navegador manda a la usuaria a arreglar
 * algo que no está roto.
 */
function explicarError(e: unknown): string {
  const nombre = (e as { name?: string })?.name ?? ''
  if (!window.isSecureContext) {
    return 'la cámara está bloqueada por no ser un origen seguro: por la red con `http://` el navegador no la da, aunque CORT responda'
  }
  if (nombre === 'NotAllowedError' || nombre === 'PermissionDeniedError') {
    return 'el navegador negó el permiso de cámara — se concede en el icono de la dirección'
  }
  if (nombre === 'SecurityError') return 'el navegador bloqueó la cámara por seguridad'
  if (nombre === 'NotReadableError') return 'otra aplicación está usando la cámara'
  if (nombre === 'NotFoundError' || nombre === 'OverconstrainedError') return 'no se encontró ninguna cámara'
  return `no se pudo abrir la cámara (${nombre || 'error desconocido'})`
}

/**
 * Gestos con la cámara: desenfocar con los dedos encoge el orbe, enfocar lo
 * devuelve a su tamaño.
 *
 * El botón es la única puerta. La cámara se abre al pulsarlo y se **cierra**
 * volviendo a pulsarlo: parar las pistas del stream es lo que apaga el LED, y el
 * cleanup del efecto cubre el caso de cerrar la pestaña con la cámara encendida.
 *
 * No hay deslizador de tamaño al lado, y es a propósito: quien manda sobre el
 * reactor es la cámara. El valor lo aplica `defocus.ts` con `setZoom` cinco veces
 * por segundo, sin pasar por el estado de React, y un control que se quedara
 * quieto mientras el orbe se encoge sería un control mentiroso.
 */
function GestoCamara() {
  const [m, setM] = useState<Muestra | null>(null)
  const [error, setError] = useState<string | null>(null)
  const parar = useRef<(() => void) | null>(null)

  useEffect(() => {
    return () => {
      parar.current?.()
      parar.current = null
    }
  }, [])

  async function alternar() {
    setError(null)
    if (parar.current) {
      parar.current()
      parar.current = null
      setM(null)
      // Sin la cámara mirando no hay quién mueva el reactor: vuelve a su tamaño
      // natural.
      setZoom(1)
      return
    }
    try {
      parar.current = await iniciarCamara(setM)
    } catch (e) {
      parar.current = null
      setM(null)
      setError(explicarError(e))
    }
  }

  const activa = m !== null

  return (
    <div className="gesto">
      <button
        type="button"
        className={`gesto-btn ${activa ? 'on' : ''}`}
        onClick={alternar}
        aria-pressed={activa}
      >
        {activa ? 'cámara activa' : 'gestos con la cámara'}
      </button>
      {activa && (
        <span className="gesto-medida">
          <span className="gesto-barra" style={{ ['--r' as string]: `${Math.round((m?.relacion ?? 1) * 100)}%` }} aria-hidden="true" />
          {/* `nitidez` cruda no es legible para una persona: lo que importa es
              qué tan cerca está del mejor enfoque que CORT ha visto. */}
          enfoque {Math.round((m?.relacion ?? 1) * 100)} %
        </span>
      )}
      {/* Sin pulsar todavía: la pregunta que ella hizo —«¿y cómo le pido el
          permiso?»— merece estar escrita antes del fallo y no después. El
          navegador lo pide él solo al pulsar; lo que no se adivina es dónde se
          cambia si se negó una vez. */}
      {!activa && !error && (
        <p className="gesto-nota">
          al pulsar, el navegador pregunta arriba a la izquierda: <b>permitir</b>. Si dijo que no una vez,
          se corrige en el candado o el icono de la dirección → <b>Permisos → Cámara</b>.
        </p>
      )}
      {error && <p className="gesto-aviso">{error}</p>}
    </div>
  )
}

export function Hud({ abierto, atuendo, onAtuendo }: {
  abierto: boolean
  atuendo: string | null
  onAtuendo: (nombre: string | null) => void
}) {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  const [draft, setDraft] = useState('')
  const log = useRef<HTMLDivElement>(null)
  const tint = palette[s.outfit] ?? palette.work
  const { pos, tirando, agarrar, reiniciar, nodo, desplazado } = useArrastre<HTMLDivElement>()

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
    // Dos nodos y dos transformaciones, no una. El marco lleva el desplazamiento
    // que la usuaria arrastra y el HUD lleva el temblor del efecto `shake`: en un
    // solo elemento la animación CSS escribe `transform` cada cuadro y el
    // desplazamiento del arrastre volvería al sitio original a media arrancada.
    <div
      className={`hud-marco ${tirando ? 'tirando' : ''}`}
      style={{ transform: `translate(${pos.x}px, ${pos.y}px)` }}
    >
      <div className="hud" ref={nodo} style={{ ['--tint' as string]: tint.ui }}>
        <span className="asa" aria-hidden="true" onPointerDown={agarrar} />
        <header className="status" onPointerDown={agarrar}>
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
          {/* Aparece sólo si el panel está movido: un botón que recoloca algo que
              ya está recolocado es ruido en la barra. */}
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
        </header>

        <div className={`cuerpo ${abierto ? '' : 'cerrado'}`} aria-hidden={!abierto}>
          <GestoCamara />
          <Voz />
          <Atuendos visible={abierto} elegido={atuendo} onElegir={onAtuendo} />

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
      </div>
    </div>
  )
}
