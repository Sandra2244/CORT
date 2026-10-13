import { useSyncExternalStore } from 'react'
import { getSnapshot, pintaFaltaDeLlave, subscribe } from '../cort/connection'
import { Ventana, type IdVentana } from './Ventana'
import { Charla } from './Charla'
import { Ayuda } from './Ayuda'
import { Voz } from './Voz'
import { GestoCamara } from './GestoCamara'
import { Atuendos } from './Avatar'
import { Telemetry } from './Telemetry'

/**
 * Las seis ventanas de CORT, montadas desde el estado de `App`.
 *
 * Este archivo es la lista viva de lo que se puede abrir: si mañana hay que
 * añadir «ecualizador», se escribe una entrada en `TITULOS`, su cuerpo en
 * `cuerpoDe`, y el muelle lo enseña solo — sin tocar CSS ni arrastre. Eso es lo
 * que se ganó al reestructurar: **una primitiva y un registro**, en lugar de
 * cuatro superficies que se parecían pero no eran iguales.
 *
 * El `zIndex` sale del orden del array `abiertas`: la última tocida se reescribe
 * al final en `App`, así «traer al frente» es mover un elemento de una lista, no
 * pelearse con estilos en línea por todos lados.
 */

export const TITULOS: Record<IdVentana, string> = {
  charla: 'charla',
  voz: 'voz',
  camara: 'cámara',
  cuerpo: 'cuerpo',
  sistema: 'sistema',
  ayuda: 'ayuda',
}

function Sistema() {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  return (
    <div className="sistema">
      <Telemetry />
      <div className="tl-row">
        <span>atuendo</span>
        <b>{s.online ? s.outfit : '—'}</b>
      </div>
      {s.clima && (
        <div className="tl-row">
          <span>clima</span>
          <b>
            <span className="city">{s.clima.city}</span> {s.clima.temp_c.toFixed(0)}°
          </b>
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
  )
}

export function Ventanas({
  abiertas,
  onCerrar,
  onTraer,
  invocar,
  atuendo,
  onAtuendo,
  tamaño,
  onTamaño,
}: {
  /** En orden de pila: la última se dibuja delante. */
  abiertas: IdVentana[]
  onCerrar: (id: IdVentana) => void
  onTraer: (id: IdVentana) => void
  invocar: number
  atuendo: string | null
  onAtuendo: (nombre: string | null) => void
  tamaño: number
  onTamaño: (t: number) => void
}) {
  function cuerpoDe(id: IdVentana) {
    switch (id) {
      case 'charla':
        return <Charla invocar={invocar} onAbrir={onTraer} />
      case 'voz':
        return <Voz />
      case 'camara':
        return <GestoCamara />
      case 'cuerpo':
        return (
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
        )
      case 'sistema':
        return <Sistema />
      case 'ayuda':
        return <Ayuda />
    }
  }

  return (
    <>
      {abiertas.map((id, i) => (
        <Ventana
          // `key` por id: cambiar de ventana no reutiliza el arrastre de la otra.
          key={id}
          id={id}
          titulo={TITULOS[id]}
          marco={10 + i}
          alCerrar={() => onCerrar(id)}
          alTraer={() => onTraer(id)}
        >
          {cuerpoDe(id)}
        </Ventana>
      ))}
    </>
  )
}
