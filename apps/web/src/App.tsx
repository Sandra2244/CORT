import { useEffect, useState } from 'react'
import { Scene } from './scene/Scene'
import { Hud } from './ui/Hud'
import { Effects } from './ui/Effects'
import { Riel, usePaneles } from './ui/Riel'
import { Avatar } from './ui/Avatar'
import { Temporizador } from './ui/Temporizador'
import { connect, setOrbeVisible } from './cort/connection'

export default function App() {
  useEffect(connect, [])

  /**
   * La cara de CORT son **dos líneas y un riel**.
   *
   * El reactor ocupa la pantalla; abajo quedan el cabezal y el campo de mensaje,
   * que son lo único siempre visible; y en el borde derecho, seis hilos de luz
   * que se ensanchan uno a la vez. El estado de ese riel —qué hilo está abierto,
   * si la cara está apagada con `H`, si ya se atenuó por inactividad— vive en
   * `usePaneles()` y sus reglas puras en `cort/paneles.ts`, que es donde se
   * prueban con `make test-web`.
   */
  const paneles = usePaneles()

  /**
   * El cuerpo de CORT: `null` = reactor; un nombre de archivo = proyección con
   * ese atuendo. Al poner el avatar el orbe se apaga, y al quitarlo vuelve — en
   * los dos casos la conexión con el core no se toca: apagar la capa visual no
   * apaga a CORT.
   */
  const [atuendo, setAtuendo] = useState<string | null>(null)

  useEffect(() => setOrbeVisible(atuendo === null), [atuendo])

  /**
   * Un `.vrm` se proyecta dentro del canvas del reactor; una imagen se pinta
   * encima como capa HTML. Dos mundos distintos para dos formas de cuerpo, y la
   * distinción la decide la extensión del archivo que ella eligió, no un botón
   * nuevo que habría que explicar.
   */
  const esModelo = atuendo !== null && /\.vrm$/i.test(atuendo)

  return (
    <>
      <Scene atuendo={atuendo} onFallo={() => setAtuendo(null)} />
      <div className="scan" aria-hidden="true" />
      {!esModelo && atuendo && <Avatar nombre={atuendo} onFallo={() => setAtuendo(null)} />}
      <Hud cara={paneles.estado.cara} atenuado={paneles.atenuado} />
      <Riel paneles={paneles} atuendo={atuendo} onAtuendo={setAtuendo} />
      {/* Va siempre montada y no se pinta casi nunca: devuelve `null` mientras no
          haya cuenta atrás. El temporizador no es un panel que se abre, es un
          número que aparece cuando se pide. */}
      <Temporizador />
      <Effects />
    </>
  )
}
