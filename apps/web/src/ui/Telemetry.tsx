import { useSyncExternalStore } from 'react'
import { getSnapshot, subscribe } from '../cort/connection'
import { palette } from '../cort/palette'

/**
 * Telemetría: lo que CORT sabe de sí mismo, en el borde de la pantalla.
 *
 * Cada fila es una comprobación, no un adorno, y es la parte del holograma que
 * sirve para algo más que mirar: si el core está en modo eco, si las acciones
 * del sistema están apagadas o cuántos recuerdos hay guardados se ve sin abrir
 * una consola.
 *
 * Sin dependencias nuevas —ni zustand ni framer-motion—: esta máquina tiene
 * 1,8 GiB de RAM y cada librería es memoria que el reactor deja de tener para
 * sí.
 *
 * No se pinta hasta que llega el primer `status`. Con el core apagado el panel
 * no tiene nada que decir, y un cuadro de ceros sería peor que ningún cuadro.
 */

/** El techo de recuerdos lo pone el core (`CORT_MEMORY_KEEP`); si mandara 0, «12 / 0» sería un bug suyo convertido en texto. */
function memories(n: number, keep: number): string {
  return keep > 0 ? `${n} / ${keep}` : `${n}`
}

/**
 * Se describe el cerebro que se midió, no el que la cadena preferiría.
 *
 * `brain` sólo tiene nombre después de que un modelo contestara de verdad, así
 * que adelantar el primero de la lista sería mentir: puede que ese modelo no
 * quepa en memoria y nunca llegue a usarse.
 */
function brainLabel(brain: string | null, ollama: boolean | null): string {
  if (brain) return brain
  if (ollama === false) return 'eco · sin Ollama'
  if (ollama === true) return 'eco · aún sin usar'
  return 'sin probar'
}

export function Telemetry({ oculto = false }: { oculto?: boolean }) {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  if (!s.status) return null
  const st = s.status
  // El tinte viene del atuendo, como en el HUD: el panel es parte del mismo
  // cuerpo y si fuera siempre del mismo cyan, cambiar de atuendo se leería
  // como un fallo del panel.
  const tint = palette[s.outfit] ?? palette.work

  return (
    <aside
      className={`telemetry ${oculto ? 'oculto' : ''}`}
      aria-hidden={oculto}
      aria-label="Estado del sistema"
      style={{ ['--tint' as string]: tint.ui }}
    >
      <div className="tl-row">
        <span>recuerdos</span>
        <b>{memories(st.memories, st.keep)}</b>
      </div>
      <div className="tl-row">
        <span>cerebro</span>
        <b>{brainLabel(st.brain, st.ollama)}</b>
      </div>
      <div className="tl-row">
        <span>acciones</span>
        <b className={st.actions ? undefined : 'tl-warn'}>{st.actions ? 'activas' : 'apagadas'}</b>
      </div>
    </aside>
  )
}
