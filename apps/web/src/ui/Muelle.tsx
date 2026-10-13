/**
 * El muelle: la única fila de botones que existe en pantalla.
 *
 * Diagnóstico de lo que había antes: los mandos estaban **regados** — el punto de
 * la esquina (`Bandeja`), el botón «ajustes» dentro del HUD, la tecla `?`, las
 * teclas `1`–`5`, y encima el modal repartía su contenido en cinco pestañas que
 * había que adivinar. Reestructurar la base es juntarlos: **un solo muelle** con
 * seis accesos, cada uno enciende y apaga su ventana de vidrio.
 *
 * Se eligieron palabras y no iconos por dos motivos medidos en el teléfono: un
 * glifo raro («⤾», «✦») se confunde con ruido de la interfaz, y el dedo acierta
 * mejor en un blanco de 44 px con texto que en un dibujo de 24 px. La palabra
 * además explica qué va a pasar, que es lo que ella pidió: que se entienda sin
 * manual.
 *
 * El muelle no es una barra de estado: no dice nada. Sólo manda. La información
 * vive en el reactor (color = ánimo) y dentro de las ventanas.
 */

import { ACCESOS } from '../cort/teclas'
import type { IdVentana } from './Ventana'

export function Muelle({
  abiertas,
  sinLeer,
  onConmutar,
}: {
  abiertas: IdVentana[]
  /** Mensajes llegados que aún no se han leído; sólo pinta un número. */
  sinLeer: number
  onConmutar: (id: IdVentana) => void
}) {
  return (
    <nav className="muelle" aria-label="ventanas de CORT">
      {ACCESOS.map(({ id, etiqueta, tecla }) => {
        const activa = abiertas.includes(id)
        return (
          <button
            key={id}
            type="button"
            className={`muelle-acceso ${activa ? 'activa' : ''}`}
            onClick={() => onConmutar(id)}
            aria-pressed={activa}
            // El número de su tecla, leído de la misma tabla que obedece el
            // teclado: si `App.tsx` cambiara el orden, aquí cambiaría el aviso.
            title={`${etiqueta} · tecla ${tecla}`}
          >
            {etiqueta}
            <span className="muelle-tecla" aria-hidden="true">
              {tecla}
            </span>
            {id === 'charla' && !activa && sinLeer > 0 && (
              <span className="muelle-aviso" aria-label={`${sinLeer} sin leer`}>
                {sinLeer}
              </span>
            )}
          </button>
        )
      })}
    </nav>
  )
}
