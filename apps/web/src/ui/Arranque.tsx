import { useEffect, useState, useSyncExternalStore } from 'react'
import { getSnapshot, subscribe } from '../cort/connection'

/**
 * El emblema de arranque (CARETA v2, fase A — `docs/REDESIGN-CARETA.md`).
 *
 * La escena que abren casi todas las referencias —el `J.A.R.V.I.S` dentro del
 * anillo de `fd38b8`, el núcleo encendiéndose de `b1-1000057225`, el
 * `SYSTEM LOCKED` de `@pablicoia`— es un **frontispicio**: unos segundos de
 * marca antes de la cabina. Aquí son anillos concéntricos girando sobre negro
 * con la palabra CORT en el centro, en monoespaciada muy espaciada.
 *
 * Y aquí viene la línea que no se cruza (regla 11): el emblema **no finge una
 * carga que no existe**. Se va en cuanto el WebSocket abre —el hecho real de
 * `snapshot.online`, el mismo que enciende el punto de la barra—, con un tope
 * de dos segundos y medio por si el core tarda o no está: un emblema
 * secuestrando la pantalla sería peor que un arranque feo. No hay barra de
 * progreso falsa ni checklist simulado; sólo la marca, y su despedida atada a
 * un estado verdadero de la máquina.
 */
const TOPE_MS = 2500

/**
 * `?telon=lento` multiplica el reloj del telón por cien. No es un modo de la
 * cara — es la llave para poder **verificarlo**: capturar una ventana de 3,2 s
 * con herramientas cuyo viaje redondo ronda los 30 s sería imposible, y un
 * telón que nadie ha visto renderizado es un telón sin verificar (regla 11).
 */
const LENTO = new URLSearchParams(location.search).get('telon') === 'lento'
const FACTOR = LENTO ? 100 : 1

export function Arranque() {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  const [visible, setVisible] = useState(true)
  const [despidiendose, setDespidiendose] = useState(false)

  // La señal de irse es real (`online`) o el tope honesto; nunca un guion.
  useEffect(() => {
    if (!s.online) return
    setDespidiendose(true)
    const t = window.setTimeout(() => setVisible(false), 700 * FACTOR)
    return () => clearTimeout(t)
  }, [s.online])

  useEffect(() => {
    const t = window.setTimeout(() => setDespidiendose(true), TOPE_MS * FACTOR)
    return () => clearTimeout(t)
  }, [])

  useEffect(() => {
    if (!despidiendose) return
    const t = window.setTimeout(() => setVisible(false), 700 * FACTOR)
    return () => clearTimeout(t)
  }, [despidiendose])

  if (!visible) return null
  return (
    <div className={`arranque ${despidiendose ? 'fuera' : ''}`} aria-hidden="true">
      <div className="arranque-anillos">
        <span className="arranque-a a1" />
        <span className="arranque-a a2" />
        <span className="arranque-a a3" />
        <span className="arranque-nucleo" />
        <span className="arranque-nombre">CORT</span>
      </div>
      <span className="arranque-pie">núcleo local · en tu máquina</span>
    </div>
  )
}
