import { useEffect, useState, useSyncExternalStore } from 'react'
import { getSnapshot, subscribe } from '../cort/connection'

const RAD = 34
const CIRC = 2 * Math.PI * RAD

/** `4500` → `1:15:00`, `95` → `1:35`. Con horas porque un «temporizador de una
 * hora» sin ellas sería un `75:00` que nadie sabe leer. */
function relojo(segundos: number): string {
  const h = Math.floor(segundos / 3600)
  const m = Math.floor((segundos % 3600) / 60)
  const s = segundos % 60
  const dos = (n: number) => String(n).padStart(2, '0')
  return h ? `${h}:${dos(m)}:${dos(s)}` : `${m}:${dos(s)}`
}

/**
 * La cuenta atrás y el cronómetro. Se pintan **sólo cuando existen**: sin cuadro
 * `timer` en el registro este componente devuelve `null` y no deja ningún nodo en
 * el DOM, ningún reloj contando y ninguna escucha puesta — que es lo que se pidió:
 * que el temporizador salga cuando se solicite y no gaste memoria estando quieto.
 *
 * El anillo no anima por sí solo: cambia un grado por segundo porque cambia un
 * cuadro por segundo. No hay `requestAnimationFrame` aquí, y a 1,8 GiB eso no es
 * una tontería — es la diferencia entre un adorno que despierta al navegador
 * sesenta veces por segundo y un número que se pinta cuando toca. Tampoco hay
 * parpadeo que quitar cuando el sistema pide movimiento reducido.
 *
 * Con el cronómetro (`sube`) el anillo va lleno: no hay total contra el que
 * medir, y un aro que avanzara «un grado por segundo» daría la vuelta al minuto
 * y volvería a empezar, que es un reloj que miente.
 */
export function Temporizador() {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  const crono = s.crono
  const [oculto, setOculto] = useState(false)

  // Al terminar no se borra de golpe: queda el cero (o el tiempo marcado) un
  // rato para que se vea que acabó, y se apaga solo. El `timeout` vive sólo
  // durante esos seis segundos y se limpia al desmontar; en reposo no hay
  // ninguno. `para` —cronómetro detenido— comparte ese mecanismo con `termina`.
  useEffect(() => {
    if (!crono || crono.estado === 'corre' || crono.estado === 'sube') {
      // Devolver el mismo valor es la forma de no provocar un repinte por segundo
      // cuando ya estaba visible.
      setOculto((v) => (v ? false : v))
      return
    }
    const t = window.setTimeout(() => setOculto(true), 6000)
    return () => clearTimeout(t)
  }, [crono])

  if (!crono || oculto) return null

  const contando = crono.estado === 'sube'
  const total = crono.total > 0 ? crono.total : 1
  const falta = contando ? 0 : CIRC * (1 - crono.restante / total)
  // `termina` y `para` son los dos estados que se despiden: comparten el aviso
  // visual de que algo terminó, cada uno con su frase.
  const listo = crono.estado === 'termina' || crono.estado === 'para'

  return (
    <div className={`crono ${listo ? 'crono-listo' : ''}`} role="timer">
      <svg className="crono-anillo" viewBox="0 0 80 80" aria-hidden="true">
        <circle className="crono-guia" cx="40" cy="40" r={RAD} />
        <circle
          className="crono-marca"
          cx="40"
          cy="40"
          r={RAD}
          strokeDasharray={CIRC}
          strokeDashoffset={falta}
          transform="rotate(-90 40 40)"
        />
      </svg>
      <div className="crono-datos">
        <span className="crono-tiempo">{relojo(crono.restante)}</span>
        <span className="crono-nombre">
          {crono.estado === 'termina'
            ? 'se acabó el tiempo'
            : crono.estado === 'para'
              ? 'cronómetro detenido'
              : contando
                ? 'cronómetro'
                : `de ${relojo(crono.total)}`}
        </span>
      </div>
    </div>
  )
}
