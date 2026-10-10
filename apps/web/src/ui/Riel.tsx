import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { getSnapshot, subscribe } from '../cort/connection'
import {
  PANELES,
  REPOSO,
  INACTIVO_MS,
  abrir,
  alternar,
  alternarCara,
  cerrarTodo,
  debeAtenuar,
  teclaAccion,
  type Estado,
  type PanelId,
} from '../cort/paneles'
import { GestoCamara } from './Hud'
import { Voz } from './Voz'
import { Atuendos } from './Avatar'
import { Telemetry } from './Telemetry'

/**
 * El riel de la derecha: seis hilos de luz, uno por panel.
 *
 * Sale del análisis de `docs/REFERENCIAS.md`. En los videos de interfaz el HUD
 * nunca es un cuadro grande: son **líneas finas apiladas en un borde**, y una de
 * ellas se ensancha cuando se le apunta (Jarvis), o se convierte en el único
 * panel que queda en pantalla mientras la mano trabaja (`90e21d`). CORT tenía un
 * tirador en la esquina que abría mensajes, telemetría, voz, atuendos y cámara
 * **todos a la vez**, que es la sobrecarga que la dueña del proyecto pidió quitar.
 *
 * Tres caminos, el mismo estado:
 *  - **dedo** → `pointerdown` en el hilo: abre, y vuelve a abrirlo lo guarda;
 *  - **cursor** → `pointerenter` solo si `pointerType === 'mouse'`: pasar por
 *    encima expande, porque el hover no existe en una pantalla táctil y fingirlo
 *    haría que el dedo abriera paneles al deslizar;
 *  - **teclado** → `Tab` hasta el hilo (y `onFocus` expande), o el número
 *    `1`–`6` desde cualquier sitio.
 */

/** Si el foco está dentro de un campo de texto: ahí las teclas son texto, no atajos. */
function escribiendo(nodo: EventTarget | null): boolean {
  const el = nodo as HTMLElement | null
  if (!el) return false
  return el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable === true
}

/**
 * El estado de la cara, con sus tres gestos y su desvanecido.
 *
 * Vive en un `useState` de React y no en el almacén del WebSocket porque no tiene
 * nada que ver con el core: es una decisión de esta pantalla. Y el desvanecido
 * necesita un temporizador, que en el almacén de conexión juramos no tener
 * (`connection.ts`: "en reposo no hay ningún `setInterval` contando"). Aquí sí lo
 * hay, y es **uno** `setTimeout` rearmado, no un contador continuo: en reposo
 * absoluto esta interfaz despierta una vez cada doce segundos y vuelve a dormirse.
 */
export function usePaneles() {
  const [estado, setEstado] = useState<Estado>(REPOSO)
  const [atenuado, setAtenuado] = useState(false)
  const ultima = useRef(Date.now())
  const reduce = useRef(false)
  /** Sube con cada actividad: es lo que rearma el temporizador del desvanecido. */
  const [despertar, setDespertar] = useState(0)

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    reduce.current = mq.matches
    const cambio = () => {
      reduce.current = mq.matches
      setDespertar((v) => v + 1)
    }
    mq.addEventListener('change', cambio)
    return () => mq.removeEventListener('change', cambio)
  }, [])

  useEffect(() => {
    /**
     * Despertar la interfaz.
     *
     * El recorte de 250 ms no es pereza: `pointermove` llega sesenta veces por
     * segundo, y re-renderizar el árbol entero a 60 Hz en una máquina de dos
     * núcleos es exactamente congelarle el PC a alguien. Con el recorte, mover el
     * ratón cuesta cuatro actualizaciones por segundo como mucho — y cero si ya
     * estaba despierta, que es el caso normal.
     */
    const despierta = () => {
      const ahora = Date.now()
      const antes = ultima.current
      ultima.current = ahora
      if (ahora - antes < 250) return
      setAtenuado(false)
      setDespertar((v) => v + 1)
    }
    const teclas = (e: KeyboardEvent) => {
      const accion = teclaAccion(e, escribiendo(e.target))
      if (!accion) return
      // `/` en Firefox busca en la página, y `1`…`6` con el dedo meñique en el
      // teclado del teléfono escriben en el campo: si la tecla es de CORT, el
      // navegador no se entera.
      e.preventDefault()
      despierta()
      if (accion === 'esc') setEstado(cerrarTodo)
      else if (accion === 'cara') setEstado(alternarCara)
      else if (accion === 'ayuda') setEstado((s) => abrir(s, 'teclas'))
      else if (accion === 'campo') document.getElementById('cort-campo')?.focus()
      else setEstado((s) => abrir(s, accion))
    }
    window.addEventListener('keydown', teclas)
    window.addEventListener('pointerdown', despierta)
    window.addEventListener('pointermove', despierta)
    window.addEventListener('wheel', despierta, { passive: true })
    return () => {
      window.removeEventListener('keydown', teclas)
      window.removeEventListener('pointerdown', despierta)
      window.removeEventListener('pointermove', despierta)
      window.removeEventListener('wheel', despierta)
    }
  }, [])

  useEffect(() => {
    if (atenuado || reduce.current) return
    const restante = Math.max(500, INACTIVO_MS - (Date.now() - ultima.current))
    const id = window.setTimeout(() => {
      // Nadie escribe en la barra de abajo: esa regla no puede vivir en el
      // reductor puro —no sabe qué tiene el foco—, así que está aquí. Un campo
      // atenuándose mientras se está redactando una orden no es la interfaz
      // apartándose del camino: es la interfaz estorbando.
      if (escribiendo(document.activeElement)) {
        ultima.current = Date.now()
        setDespertar((v) => v + 1)
        return
      }
      if (
        debeAtenuar({
          abierto: estado.abierto,
          cara: estado.cara,
          ultimaActividad: ultima.current,
          ahora: Date.now(),
          reduceMotion: reduce.current,
        })
      )
        setAtenuado(true)
      // Si todavía no toca, se rearma para el rato que falta. Sin esto el
      // desvanecido se perdería una vez y no volvería hasta el siguiente toque.
      else setDespertar((v) => v + 1)
    }, restante)
    return () => clearTimeout(id)
  }, [estado, atenuado, despertar])

  return {
    estado,
    atenuado,
    /** Dedo o clic: abre el hilo, y lo guarda si ya estaba abierto. */
    tocar: (id: PanelId) => {
      ultima.current = Date.now()
      setAtenuado(false)
      setEstado((s) => alternar(s, id))
    },
    /** Cursor o `Tab`: expande sin prometer cerrar nada al salir. */
    mirar: (id: PanelId) => {
      ultima.current = Date.now()
      setAtenuado(false)
      setEstado((s) => abrir(s, id))
    },
    guardar: () => setEstado(cerrarTodo),
    apagarCara: () => setEstado(alternarCara),
  }
}

/**
 * Cuántos mensajes llegaron con el panel de `mensajes` guardado.
 *
 * Herencia directa de la bandeja anterior: si CORT contesta mientras la pantalla
 * está limpia, tiene que haber una señal de que algo pasó por leer. Va en el hilo
 * correspondiente y no en una esquina suelta, que es lo que hace que el riel se
 * lea de un vistazo.
 */
function useSinLeer(abierto: boolean): number {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  const vistos = useRef(s.msgs.length)
  useEffect(() => {
    if (abierto) vistos.current = s.msgs.length
  }, [abierto, s.msgs.length])
  return Math.max(0, s.msgs.length - vistos.current)
}

/** El registro de la conversación, que es lo que expande el hilo `mensajes`. */
function Registro() {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  const caja = useRef<HTMLDivElement>(null)
  useEffect(() => {
    caja.current?.scrollTo({ top: caja.current.scrollHeight })
  }, [s.msgs.length])
  return (
    <div className="log" ref={caja} role="log" aria-live="polite">
      {s.msgs.map((m, i) => (
        <p key={i} className={m.from === 'user' ? 'me' : 'cort'}>
          {m.text}
        </p>
      ))}
    </div>
  )
}

/** La ayuda de teclado: la tabla se genera de `PANELES`, para que no se desincronice. */
function Teclas() {
  return (
    <div className="ayuda">
      <p className="ayuda-fila"><kbd>1</kbd>—<kbd>6</kbd><span>abren cada panel del riel</span></p>
      <p className="ayuda-fila"><kbd>/</kbd><span>escribir a CORT</span></p>
      <p className="ayuda-fila"><kbd>Esc</kbd><span>guardar lo abierto</span></p>
      <p className="ayuda-fila"><kbd>H</kbd><span>apagar la cara y dejar el reactor</span></p>
      <p className="ayuda-fila"><kbd>?</kbd><span>esta lista</span></p>
      <p className="ayuda-nota">
        con el dedo se toca el hilo; con el cursor basta pasar por encima; con el teclado, <kbd>Tab</kbd>
        {' '}recorre el riel. Arrastrar la barra de abajo mueve la interfaz, y desenfoque con los dedos
        {' '}delante de la cámara agranda o encoge el reactor.
      </p>
    </div>
  )
}

export function Riel({ paneles, atuendo, onAtuendo }: {
  paneles: ReturnType<typeof usePaneles>
  atuendo: string | null
  onAtuendo: (nombre: string | null) => void
}) {
  const { estado, atenuado, tocar, mirar, guardar } = paneles
  const sinLeer = useSinLeer(estado.abierto === 'mensajes')
  const s = useSyncExternalStore(subscribe, getSnapshot)

  const { abierto } = estado
  const etiqueta = PANELES.find((p) => p.id === abierto)?.etiqueta ?? ''

  return (
    <>
      <nav className={`riel ${atenuado ? 'atenuado' : ''} ${estado.cara ? '' : 'cara-apagada'}`} aria-label="paneles de CORT">
        {PANELES.map((p) => (
          <button
            key={p.id}
            type="button"
            className={`hilo ${abierto === p.id ? 'abierto' : ''}`}
            aria-expanded={abierto === p.id}
            aria-label={`${p.etiqueta} (tecla ${p.tecla})`}
            /*
             * Un solo `onClick`, y sirve para el dedo y para el ratón. Con
             * `onPointerDown` **y** `onClick` a la vez, un toque del teléfono
             * dispararía los dos y el panel se abriría para cerrarse enseguida: el
             * `click` del navegador ya sabe distinguir un puntero del otro. Lo que
             * sí hay que separar a mano es el `hover`, que no existe en una
             * pantalla táctil.
             */
            onClick={() => tocar(p.id)}
            onPointerEnter={(e) => {
              if (e.pointerType === 'mouse') mirar(p.id)
            }}
            onFocus={() => mirar(p.id)}
          >
            {/* El número es la tecla y el aviso son los mensajes sin leer. En la
                casilla de 30 px no caben los dos: se pisaban, y se vio en la
                captura. Con aviso, el número se va — la tecla sigue escrita en el
                `aria-label` y en el panel de `teclas`. */}
            {p.id === 'mensajes' && !abierto && sinLeer > 0 ? (
              <span className="hilo-aviso">{sinLeer}</span>
            ) : (
              <span className="hilo-numero" aria-hidden="true">{p.tecla}</span>
            )}
            <span className="hilo-nombre">{p.etiqueta}</span>
          </button>
        ))}
      </nav>

      {abierto && (
        <section className={`panel panel-${abierto}`} aria-label={etiqueta}>
          <header className="panel-cabezal">
            <span className="panel-titulo">{etiqueta}</span>
            <button
              type="button"
              className="chip"
              onClick={guardar}
              aria-label="guardar este panel"
              title="guardar (Esc)"
            >
              guardar
            </button>
          </header>
          {abierto === 'mensajes' && <Registro />}
          {abierto === 'telemetria' && <Telemetry />}
          {abierto === 'voz' && <Voz />}
          {abierto === 'atuendos' && <Atuendos visible elegido={atuendo} onElegir={onAtuendo} />}
          {abierto === 'camara' && <GestoCamara />}
          {abierto === 'teclas' && <Teclas />}
          {/* El aviso de conexión no se esconde detrás de un panel: si no hay
              core, la telemetría está guardada y es lo primero que no se ve. */}
          {!s.online && abierto !== 'mensajes' && (
            <p className="panel-aviso">sin conexión con el core — ejecuta <code>make dev</code></p>
          )}
        </section>
      )}
    </>
  )
}
