import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { getSnapshot, send, setZoom, subscribe, target, zoomLimits } from '../cort/connection'
import { iniciarCamara, type Muestra } from '../cort/defocus'
import { Atuendos } from './Avatar'
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
 *
 * Con la cámara activa el deslizador **obedece y se lee**, no se pelea: lo que
 * pinta es el valor que sale del gesto, porque un control que sigue mostrando
 * 100 % mientras el orbe se encoge es un control mentiroso.
 */
function ZoomControl({ zoomCamara }: { zoomCamara: number | null }) {
  const [zoom, setZoomUi] = useState(target.zoom)

  function apply(factor: number) {
    // `setZoom` recorta al margen y devuelve el valor ya válido: la UI pinta el
    // recortado, no el que se pidió. Si no, el slider quedaría mentiroso al
    // llegar al fondo.
    setZoomUi(setZoom(factor))
  }

  // `zoomCamara` llega 5 veces por segundo con el gesto: manda sobre el estado
  // local, porque el orbe ya se está moviendo con ese valor.
  const mostrado = zoomCamara ?? zoom
  const movido = zoomCamara !== null

  return (
    <div className="zoom">
      <span className="zoom-label">{movido ? 'tamaño · cámara' : 'tamaño'}</span>
      <button
        type="button"
        className="zoom-btn"
        aria-label="reducir el reactor"
        disabled={movido}
        onClick={() => apply(mostrado - 0.2)}
      >
        −
      </button>
      <input
        className="zoom-slider"
        type="range"
        min={zoomLimits.min}
        max={zoomLimits.max}
        step={0.02}
        value={mostrado}
        disabled={movido}
        onChange={(e) => apply(Number(e.target.value))}
        aria-label="tamaño del reactor"
      />
      <button
        type="button"
        className="zoom-btn"
        aria-label="agrandar el reactor"
        disabled={movido}
        onClick={() => apply(mostrado + 0.2)}
      >
        +
      </button>
      <span className="zoom-value">{Math.round(mostrado * 100)}%</span>
    </div>
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
 */
function GestoCamara({ onZoom }: { onZoom: (zoom: number | null) => void }) {
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
      onZoom(null)
      // Sin la cámara mirando no hay quién mueva el reactor: vuelve a su tamaño
      // natural, que es el valor desde el que el deslizador de nuevo obedece.
      setZoom(1)
      return
    }
    try {
      parar.current = await iniciarCamara((nueva) => {
        setM(nueva)
        onZoom(nueva.zoom)
      })
    } catch (e) {
      parar.current = null
      setM(null)
      onZoom(null)
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
  const [zoomCamara, setZoomCamara] = useState<number | null>(null)
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

      <div className={`cuerpo ${abierto ? '' : 'cerrado'}`} aria-hidden={!abierto}>
        <ZoomControl zoomCamara={zoomCamara} />
        <GestoCamara onZoom={setZoomCamara} />
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
  )
}
