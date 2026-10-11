import { useEffect, useRef, useState } from 'react'
import { setZoom } from '../cort/connection'
import { iniciarCamara, type Muestra } from '../cort/defocus'

/**
 * Gestos con la cámara: desenfocar con los dedos delante del objetivo encoge el
 * orbe, enfocar lo devuelve.
 *
 * Vivió dentro de `Hud.tsx` formando parte del riel; el rediseño (R2) lo trajo
 * acá adentro de la ventana «cámara» (modal de una pieza en R2, vidrio suelto
 * desde N1), sin cambiar nada del mecanismo: la cámara
 * se abre al pulsar y se cierra volviendo a pulsar — parar las pistas del stream
 * es lo que apaga el LED —, y el valor lo aplica `defocus.ts` con `setZoom`
 * cinco veces por segundo sin pasar por React.
 *
 * El párrafo que explicaba dónde se concede el permiso **ya no está**: se mudó a
 * la ventana «ayuda». En la cara no se leen manuales; en la ayuda sí,
 * y la pregunta de la dueña del proyecto («¿y cómo le pido el permiso?») sigue
 * contestada, apenas que en su sitio.
 */

/** El porqué del fallo, en orden de lo que pasa de verdad. Ver `Hud.tsx` viejo. */
export function explicarError(e: unknown): string {
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

export function GestoCamara() {
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
          enfoque {Math.round((m?.relacion ?? 1) * 100)} %
        </span>
      )}
      {error && <p className="gesto-aviso">{error}</p>}
    </div>
  )
}
