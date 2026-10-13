import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { getSnapshot, subscribe } from '../cort/connection'
import { DEFAULT_OUTFIT, palette } from '../cort/palette'

/**
 * La superficie de conversación (capa L2 del rediseño).
 *
 * Regla sacada de las referencias: el reactor es la cara, y CORT responde
 * *debajo* de él como un subtítulo holográfico — no con un chat de veinte
 * mensajes tapándole el pecho (eso era el problema que se veía en el video de
 * la pantalla). Aquí vive la última cosa que dijo; el historial completo sigue
 * en la bandeja.
 *
 * Se auto-oculta ocho segundos después de llegar el mensaje: lo que CORT dijo ya
 * fue dicho, y un subtítulo perpetuo vuelve a ser un panel fijo. El temporizador
 * sólo existe mientras el subtítulo está en pantalla — en reposo no queda ningún
 * `setTimeout` vivo, que es la misma disciplina del temporizador del core.
 *
 * El botón ✕ la despide antes (es el cierre de la "tarjeta de resultado", R6 en
 * su versión mínima: captura, clima y cuenta atrás también caben en esta línea),
 * y tocar el subtítulo abre la bandeja para leer la conversación entera.
 */
const VIDA_MS = 8000

export function Respuesta({ visible, onAbrir }: { visible: boolean; onAbrir: () => void }) {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  const [mostrar, setMostrar] = useState(false)
  const despido = useRef(0) // cantidad de mensajes que la usuaria ya cerró

  // Cada mensaje nuevo de CORT levanta el subtítulo y reinicia los ocho segundos.
  useEffect(() => {
    let ultimo = -1
    for (let i = s.msgs.length - 1; i >= 0; i--) {
      if (s.msgs[i].from === 'cort') { ultimo = i; break }
    }
    if (ultimo < 0 || ultimo + 1 <= despido.current) { setMostrar(false); return }
    setMostrar(true)
    const t = window.setTimeout(() => setMostrar(false), VIDA_MS)
    return () => clearTimeout(t)
  }, [s.msgs])

  if (!visible || !mostrar) return null

  let texto = ''
  for (let i = s.msgs.length - 1; i >= 0; i--) {
    if (s.msgs[i].from === 'cort') { texto = s.msgs[i].text; break }
  }
  const tint = palette[s.outfit] ?? palette[DEFAULT_OUTFIT]

  return (
    <div className="respuesta" style={{ ['--tint' as string]: tint.ui }} role="status">
      <button
        type="button"
        className="respuesta-cuerpo"
        onClick={onAbrir}
        aria-label="Abrir la conversación completa"
      >
        {texto}
      </button>
      <button
        type="button"
        className="respuesta-cerrar"
        aria-label="Cerrar el aviso"
        onClick={() => { despido.current = s.msgs.length; setMostrar(false) }}
      >
        ✕
      </button>
    </div>
  )
}
