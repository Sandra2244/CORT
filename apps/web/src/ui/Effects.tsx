import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { getSnapshot, subscribe, type UiEffect } from '../cort/connection'
import { palette } from '../cort/palette'

/**
 * Efectos de un solo disparo, los que manda CORT.
 *
 * Transplantado de adewaskar/JARVIS (MIT) — ver CREDITS.md.
 *
 * Son puntuación, no estado: una onda cuando algo aterrizó, un desgarro cuando
 * algo salió mal. Por eso la capa sólo existe mientras suena algo; dejarla
 * montada permanentes sería tener un elemento a pantalla completa toda la sesión
 * por medio segundo de animación.
 *
 * Cada efecto son keyframes CSS sobre un nodo recién montado. Eso es lo que hace
 * que repetir el mismo efecto vuelva a dispararse: `at` está en la clave, así
 * que pedir 'glitch' dos veces seguidas remonta el nodo y la animación arranca
 * de cero, donde re-aplicar la misma clase a un elemento vivo no haría nada.
 *
 * 'shake' es la excepción. Sacudir el marco significa mover el HUD entero, y
 * esta capa no lo posee, así que se lo presta: la clase va al ancestro `.hud`
 * durante la animación y se quita al terminar, también al desmontar.
 */

/** Lo que duran los keyframes de cada efecto. En paso con index.css. */
const DURATION: Record<UiEffect, number> = {
  glitch: 620,
  pulse: 900,
  scan: 900,
  shake: 520,
  flash: 480,
}

export function Effects() {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot)
  const effect = snapshot.effect
  const [live, setLive] = useState<UiEffect | null>(null)
  const root = useRef<HTMLDivElement | null>(null)

  const kind = effect?.kind
  const at = effect?.at ?? 0

  // Depende de la marca de tiempo y no del objeto, que es justo la razón de ser
  // de `at`: cinco 'flash' seguidos son cinco destellos.
  useEffect(() => {
    if (!kind) return
    setLive(kind)
    const done = setTimeout(() => setLive(null), DURATION[kind])
    return () => clearTimeout(done)
  }, [kind, at])

  useEffect(() => {
    if (!live || live !== 'shake') return
    const hud = root.current?.closest('.hud')
    if (!hud) return
    hud.classList.add('fx-shaking')
    const done = setTimeout(() => hud.classList.remove('fx-shaking'), DURATION.shake)
    return () => {
      clearTimeout(done)
      hud.classList.remove('fx-shaking')
    }
  }, [live])

  if (!live || !effect) return null

  // El color lo manda la misma paleta que pinta el reactor. Esta capa cuelga
  // fuera de .hud, así que no hereda su --tint: si no se fijara aquí, la onda
  // saldría de un color distinto al del anillo que acaba de expandirla.
  const tint = palette[snapshot.outfit] ?? palette.work

  return (
    <div
      className="fx"
      ref={root}
      aria-hidden="true"
      style={{ ['--accent' as string]: tint.ui }}
    >
      <div key={`${live}-${at}`} className={`fx-play fx-${live}`}>
        {live === 'glitch' && (
          <>
            <span className="fx-slice" />
            <span className="fx-slice" />
            <span className="fx-slice" />
          </>
        )}
        {live === 'pulse' && (
          <>
            <span className="fx-wave" />
            <span className="fx-wave" />
          </>
        )}
      </div>
    </div>
  )
}
