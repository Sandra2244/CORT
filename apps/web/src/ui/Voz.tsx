import { useSyncExternalStore } from 'react'
import {
  ajustarVoz,
  alternarEscucha,
  alternarHabla,
  alternarVigilia,
  elegirVozPorNombre,
  estadoVoz,
  hayHabla,
  probarVoz,
  suscribirVoz,
} from '../cort/voz'

/**
 * Los dos botones de voz. Toda la lógica (reconocimiento, síntesis, turnos) vive
 * en `cort/voz.ts`: este componente sólo la muestra. Así cerrar el modal no
 * apaga el micrófono — el estado ya no depende de que esta pestaña esté abierta.
 */
export function Voz() {
  const v = useSyncExternalStore(suscribirVoz, estadoVoz)

  return (
    <div className="gesto">
      <button
        type="button"
        className={`gesto-btn ${v.habla ? 'on' : ''}`}
        onClick={alternarHabla}
        aria-pressed={v.habla}
        disabled={!hayHabla}
      >
        {v.habla ? 'voz activa' : 'que me hable'}
      </button>
      <button
        type="button"
        className={`gesto-btn ${v.escucha ? 'on' : ''}`}
        onClick={alternarEscucha}
        aria-pressed={v.escucha}
      >
        {v.escucha ? 'escuchando…' : 'hablarle'}
      </button>
      <button
        type="button"
        className={`gesto-btn ${v.vigilia ? 'on' : ''}`}
        onClick={alternarVigilia}
        aria-pressed={v.vigilia}
        title="El micrófono queda abierto esperando «OK CORT». El audio lo procesa el servicio del navegador."
      >
        {v.turno ? 'te escucho…' : v.vigilia ? 'esperando «OK CORT»' : 'activar «OK CORT»'}
      </button>
      {(v.escucha || v.turno) && v.oyendo && <span className="gesto-medida">{v.oyendo}</span>}
      {/* El párrafo que explicaba qué hace cada botón se mudó a la ventana
          «ayuda»: en la cara no se leen manuales. */}
      {hayHabla && (
        <div className="voz-ajustes">
          <label className="voz-campo">
            <span>voz</span>
            <select
              value={v.vozNombre}
              onChange={(e) => elegirVozPorNombre(e.target.value)}
              disabled={v.voces.length === 0}
            >
              {v.voces.length === 0 && <option value="">(cargando voces…)</option>}
              {v.voces.map((n) => (
                <option key={n} value={n}>
                  {n.replace(/^Microsoft\s+/, '').replace(/\s*-\s*Spanish.*$/, '')}
                </option>
              ))}
            </select>
          </label>
          <label className="voz-campo">
            <span>velocidad {v.velocidad.toFixed(2)}</span>
            <input
              type="range"
              min={0.6}
              max={1.5}
              step={0.05}
              value={v.velocidad}
              onChange={(e) => ajustarVoz({ velocidad: Number(e.target.value) })}
            />
          </label>
          <label className="voz-campo">
            <span>tono {v.tono.toFixed(2)}</span>
            <input
              type="range"
              min={0.5}
              max={1.5}
              step={0.05}
              value={v.tono}
              onChange={(e) => ajustarVoz({ tono: Number(e.target.value) })}
            />
          </label>
          <button type="button" className="gesto-btn" onClick={probarVoz}>
            probar voz
          </button>
        </div>
      )}
      {v.error && <p className="gesto-aviso">{v.error}</p>}
    </div>
  )
}
