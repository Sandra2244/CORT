import { useEffect, useRef, useSyncExternalStore } from 'react'
import { getSnapshot, pintaFaltaDeLlave, subscribe } from '../cort/connection'
import { Voz } from './Voz'
import { GestoCamara } from './GestoCamara'
import { Atuendos } from './Avatar'
import { Telemetry } from './Telemetry'

/**
 * El modal de herramientas (capa L3 del rediseño, docs/REDESIGN-UI.md).
 *
 * Las referencias que trajo Sandra —el JARVIS de @techencclair sobre todo— no
 * tienen rieles: tienen UN modal centrado que aparece, cumple y desaparece. Aquí
 * vive ahora todo lo que antes era pila de botones con manual: voz, cámara,
 * atuendos, sistema y ayuda. Cinco pestañas, una superficie.
 *
 * Se abre desde la bandeja («ajustes») y se cierra con `Esc` o pulsando fuera.
 * No hay botón de cerrar flotando en la cara: si hay que buscarlo, la cara está
 * otra vez llena de chrome.
 *
 * Sin dependencias nuevas: es un `<dialog>` nativo con `showModal()` — overlay,
 * bloqueo del fondo, `Esc` y foco atrapado los regala el navegador, que en una
 * máquina de 1,8 GiB es la mejor librería de moda.
 */

export type Pestana = 'voz' | 'camara' | 'atuendos' | 'sistema' | 'ayuda'

const PESTANAS: { id: Pestana; etiqueta: string }[] = [
  { id: 'voz', etiqueta: 'voz' },
  { id: 'camara', etiqueta: 'cámara' },
  { id: 'atuendos', etiqueta: 'atuendos' },
  { id: 'sistema', etiqueta: 'sistema' },
  { id: 'ayuda', etiqueta: 'ayuda' },
]

function Ayuda() {
  return (
    <div className="ayuda">
      <p>
        <b>gestos con la cámara</b> — desenfocar con los dedos delante del objetivo encoge el
        reactor; enfocar lo devuelve. Al pulsar el botón, el navegador pregunta arriba a la
        izquierda: <b>permitir</b>. Si dijo que no una vez, se corrige en el candado o el icono
        de la dirección → <b>Permisos → Cámara</b>. Por la red con <code>http://</code> el
        navegador no da la cámara: hace falta HTTPS.
      </p>
      <p>
        <b>voz</b> — <b>que me hable</b> lee en voz alta lo que CORT responde. <b>hablarle</b>
        abre el micrófono y conversa: el navegador pide permiso la primera vez, y el
        reconocimiento necesita internet (Edge o Chrome).
      </p>
      <p>
        <b>atuendos</b> — CORT proyecta los archivos de tu carpeta. Se declara con{' '}
        <code>CORT_AVATAR_DIR=/ruta/a/tus/atuendos</code> en el <code>.env</code> y reiniciando
        CORT. Los <code>.vrm</code> se montan como cuerpo 3D dentro del mismo canvas.
      </p>
      <p>
        <b>atajos</b> — <code>Ctrl+/</code> abre la conversación con el cursor listo;{' '}
        <code>Esc</code> cierra modal y bandeja; tocar el centro de la pantalla hace lo mismo
        que <code>Ctrl+/</code>. El temporizador y las acciones se piden escribiendo: «pon un
        temporizador de 5 minutos», «baja el volumen».
      </p>
    </div>
  )
}

export function Panel({ pestana, onPestana, onCerrar, atuendo, onAtuendo, tamaño, onTamaño }: {
  pestana: Pestana
  onPestana: (p: Pestana) => void
  onCerrar: () => void
  atuendo: string | null
  onAtuendo: (nombre: string | null) => void
  tamaño: number
  onTamaño: (t: number) => void
}) {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  const caja = useRef<HTMLDialogElement>(null)

  // `showModal()` y no el atributo `open`: sólo en modal el navegador pone el
  // `::backdrop` (así pulsar fuera es pulsar el propio dialog, y ahí se cierra),
  // atrapa el foco y deja que `Esc` lo cancele. Este componente se monta justo
  // cuando alguien abre la pestaña, así que el efecto **es** la apertura.
  useEffect(() => {
    const el = caja.current
    if (el && !el.open) el.showModal()
  }, [])

  return (
    <dialog ref={caja} className="panel" onClose={onCerrar} aria-label="ajustes de CORT" onClick={(e) => {
      // Pulsar el overlay (el propio dialog) cierra; pulsar contenido no.
      if (e.target === e.currentTarget) onCerrar()
    }}>
      <div className="panel-cab">
        {PESTANAS.map((p) => (
          <button
            key={p.id}
            type="button"
            className={`pestana ${pestana === p.id ? 'activa' : ''}`}
            onClick={() => onPestana(p.id)}
            aria-pressed={pestana === p.id}
          >
            {p.etiqueta}
          </button>
        ))}
      </div>

      <div className="panel-cuerpo">
        {pestana === 'voz' && <Voz />}
        {pestana === 'camara' && <GestoCamara />}
        {pestana === 'atuendos' && (
          <>
            <Atuendos visible elegido={atuendo} onElegir={onAtuendo} />
            {atuendo && /\.vrm$/i.test(atuendo) && (
              <div className="tamanos" role="group" aria-label="tamaño del avatar">
                <span className="zoom-label">tamaño</span>
                {([[0.72, 'pequeño'], [1, 'medio'], [1.25, 'grande']] as [number, string][]).map(
                  ([v, etiqueta]) => (
                    <button
                      key={v}
                      type="button"
                      className={`tamano ${Math.abs(tamaño - v) < 0.01 ? 'activo' : ''}`}
                      onClick={() => onTamaño(v)}
                      aria-pressed={Math.abs(tamaño - v) < 0.01}
                    >
                      {etiqueta}
                    </button>
                  ),
                )}
              </div>
            )}
          </>
        )}
        {pestana === 'sistema' && (
          <div className="sistema">
            <Telemetry />
            <div className="tl-row">
              <span>atuendo</span>
              <b>{s.online ? s.outfit : '—'}</b>
            </div>
            {s.clima && (
              <div className="tl-row">
                <span>clima</span>
                <b><span className="city">{s.clima.city}</span> {s.clima.temp_c.toFixed(0)}°</b>
              </div>
            )}
            {!s.online && (
              <p className="gesto-aviso">
                {pintaFaltaDeLlave()
                  ? 'falta la llave de la red — abre la dirección que imprime cort.py --lan'
                  : 'sin conexión con el core — ejecuta: make dev'}
              </p>
            )}
          </div>
        )}
        {pestana === 'ayuda' && <Ayuda />}
      </div>
    </dialog>
  )
}
