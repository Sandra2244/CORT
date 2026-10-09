import { useEffect, useState } from 'react'
import { Scene } from './scene/Scene'
import { Hud } from './ui/Hud'
import { Effects } from './ui/Effects'
import { Telemetry } from './ui/Telemetry'
import { Bandeja } from './ui/Bandeja'
import { Avatar } from './ui/Avatar'
import { connect, setOrbeVisible } from './cort/connection'

export default function App() {
  useEffect(connect, [])

  /**
   * La bandeja arranca **guardada**. La cara del proyecto es el reactor ocupando
   * la pantalla entera, no un panel de texto: el registro, la telemetría y los
   * controles se abren desde la esquina, con el dedo o con el ratón, y se cierran
   * con `Esc`.
   */
  const [abierto, setAbierto] = useState(false)

  /**
   * El cuerpo de CORT: `null` = reactor; un nombre de archivo = proyección con
   * ese atuendo. Al poner el avatar el orbe se apaga, y al quitarlo vuelve — en
   * los dos casos la conexión con el core no se toca: apagar la capa visual no
   * apaga a CORT.
   */
  const [atuendo, setAtuendo] = useState<string | null>(null)

  useEffect(() => setOrbeVisible(atuendo === null), [atuendo])

  useEffect(() => {
    function teclas(e: KeyboardEvent) {
      if (e.key === 'Escape') setAbierto(false)
    }
    window.addEventListener('keydown', teclas)
    return () => window.removeEventListener('keydown', teclas)
  }, [])

  return (
    <>
      <Scene />
      <div className="scan" aria-hidden="true" />
      {atuendo && <Avatar nombre={atuendo} onFallo={() => setAtuendo(null)} />}
      <Telemetry oculto={!abierto} />
      <Hud abierto={abierto} atuendo={atuendo} onAtuendo={setAtuendo} />
      <Bandeja abierto={abierto} onToggle={() => setAbierto((v) => !v)} />
      <Effects />
    </>
  )
}
