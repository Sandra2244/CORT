import { useSyncExternalStore } from 'react'
import { getSnapshot, pintaFaltaDeLlave, subscribe } from '../cort/connection'
import { useArrastre } from '../cort/arrastre'
import { SECCIONES, VIDRIOS, type Estado, type Seccion } from '../cort/ventanas'
import { Voz } from './Voz'
import { GestoCamara } from './GestoCamara'
import { Atuendos } from './Avatar'
import { Telemetry } from './Telemetry'

/**
 * Las ventanas de vidrio (capa L3 — N1 de docs/REDESIGN-NUCLEO.md).
 *
 * El modal de una sola pestaña (`ui/Panel.tsx`) se convirtió en ventanas
 * flotantes: las cinco secciones pueden estar abiertas a la vez, cada una se
 * agarra de su barra, se oculta con ✕ y vuelve con su tecla, y deja ver el
 * reactor a través de ella con tres niveles de vidrio (◐). Es la cara de las
 * referencias en video — `@techenclear` y `@sued.tiago`—: paneles translúcidos
 * sobre el escritorio real, no una caja a pantalla completa que se traga la
 * escena.
 *
 * La sujeción del arrastre es la misma que ya se midió en DOM para el HUD
 * (`cort/arrastre.ts`): por eso cada ventana usa el `useArrastre` completo y
 * `nodo` es el propio `<section>` — es lo que mide `getBoundingClientRect`, y
 * el marco del desplazamiento es el mismo elemento.
 *
 * Sin dependencias nuevas y sin `<dialog>`: las ventanas NO son modales — el
 * fondo sigue vivo mientras están abiertas, que es justo lo que el modal
 * quitaba. El orden de pila lo guarda `cort/ventanas.ts` (probado con
 * `make test-web`); aquí cada ventana recibe su `zIndex` por posición.
 */

export function Ventanas({ estado, onTraer, onOcultar, onVidrio, atuendo, onAtuendo, tamaño, onTamaño }: {
  estado: Estado
  onTraer: (id: Seccion) => void
  onOcultar: (id: Seccion) => void
  onVidrio: () => void
  atuendo: string | null
  onAtuendo: (nombre: string | null) => void
  tamaño: number
  onTamaño: (t: number) => void
}) {
  return (
    <>
      {estado.pilas.map((id, i) => (
        <Ventana
          // La clave ES el identificador: al traer una ventana al frente cambía
          // su posición en la lista, y sin esta igualdad React desmontaría el
          // componente — y con él se iría la posición arrastrada.
          key={id}
          id={id}
          z={10 + i * 2}
          vidrio={estado.vidrio}
          onTraer={onTraer}
          onOcultar={onOcultar}
          onVidrio={onVidrio}
          atuendo={atuendo}
          onAtuendo={onAtuendo}
          tamaño={tamaño}
          onTamaño={onTamaño}
        />
      ))}
    </>
  )
}

function Ventana({ id, z, vidrio, onTraer, onOcultar, onVidrio, atuendo, onAtuendo, tamaño, onTamaño }: {
  id: Seccion
  z: number
  vidrio: number
  onTraer: (id: Seccion) => void
  onOcultar: (id: Seccion) => void
  onVidrio: () => void
  atuendo: string | null
  onAtuendo: (nombre: string | null) => void
  tamaño: number
  onTamaño: (t: number) => void
}) {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  const { pos, tirando, agarrar, reiniciar, nodo, desplazado } = useArrastre<HTMLElement>()
  const info = SECCIONES.find((x) => x.id === id) ?? SECCIONES[0]
  const nivel = VIDRIOS[vidrio] ?? VIDRIOS[1]

  return (
    <section
      ref={nodo}
      className={`ventana ventana-${id} ${nivel.clase}${tirando ? ' tirando' : ''}`}
      style={{ transform: `translate(${pos.x}px, ${pos.y}px)`, zIndex: z }}
      onPointerDown={() => onTraer(id)}
      aria-label={`ventana de ${info.etiqueta}`}
    >
      <header className="ventana-cab" onPointerDown={agarrar}>
        <span className="asa" aria-hidden="true" />
        <span className="ventana-titulo">{info.etiqueta}</span>
        <span className="ventana-botones">
          {desplazado && (
            <button
              type="button"
              className="ventana-colocar"
              onClick={reiniciar}
              aria-label="Devolver la ventana a su sitio"
              title="Devolver la ventana a su sitio"
            >
              ⤾
            </button>
          )}
          <button
            type="button"
            className="ventana-vidrio"
            onClick={onVidrio}
            aria-label="Cambiar la transparencia del vidrio"
            title={`vidrio: ${nivel.nombre} — ◐ cambia a opaco · vidrio · bruma`}
          >
            ◐ {nivel.nombre}
          </button>
          <button
            type="button"
            className="ventana-cerrar"
            onClick={() => onOcultar(id)}
            aria-label={`Ocultar la ventana de ${info.etiqueta}`}
            title={`Ocultar — la tecla ${info.tecla} la devuelve`}
          >
            ✕
          </button>
        </span>
      </header>

      <div className="ventana-cuerpo">
        {id === 'voz' && <Voz />}
        {id === 'camara' && <GestoCamara />}
        {id === 'atuendos' && (
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
        {id === 'sistema' && (
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
        {id === 'ayuda' && <Ayuda />}
      </div>
    </section>
  )
}

function Ayuda() {
  return (
    <div className="ayuda">
      <p>
        <b>ventanas de vidrio</b> — las cinco ventanas flotan sobre el reactor.
        Se agarran de su barra superior —con el ratón o con el dedo— y se sueltan
        donde quieras; nunca se salen de la pantalla. <b>◐</b> cambia el vidrio
        (opaco · vidrio · bruma — transparente del todo); <b>✕</b> oculta la
        ventana y su tecla la devuelve; <b>⤾</b> la devuelve a su sitio. El reloj
        de arriba también se mueve agarrándolo.
      </p>
      <p>
        <b>atajos</b> — <code>1</code> voz · <code>2</code> cámara ·{' '}
        <code>3</code> atuendos · <code>4</code> sistema · <code>5</code> ayuda
        (cada tecla abre y oculta SU ventana, pueden estar varias a la vez);{' '}
        <code>/</code> o <code>Ctrl+/</code> abre la conversación con el cursor
        listo; <code>Esc</code> despide primero la ventana del frente y luego la
        bandeja; <code>?</code> trae esta ayuda.
      </p>
      <p>
        <b>gestos con la cámara</b> — desenfocar con los dedos delante del
        objetivo encoge el reactor; enfocar lo devuelve. Al pulsar el botón, el
        navegador pregunta: <b>permitir</b>. Por la red con <code>http://</code>{' '}
        el navegador no da la cámara: hace falta HTTPS.
      </p>
      <p>
        <b>voz</b> — <b>que me hable</b> lee en voz alta lo que CORT responde.{' '}
        <b>hablarle</b> abre el micrófono y conversa; el reconocimiento necesita
        internet (Edge o Chrome). El temporizador y las acciones se piden
        escribiendo: «pon un temporizador de 5 minutos», «baja el volumen».
      </p>
      <p>
        <b>atuendos</b> — CORT proyecta los archivos de tu carpeta. Se declara
        con <code>CORT_AVATAR_DIR=/ruta/a/tus/atuendos</code> en el{' '}
        <code>.env</code> y reiniciando CORT. Los <code>.vrm</code> se montan
        como cuerpo 3D dentro del mismo canvas.
      </p>
    </div>
  )
}
