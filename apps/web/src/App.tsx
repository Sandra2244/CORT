import { useEffect } from 'react'
import { Scene } from './scene/Scene'
import { Hud } from './ui/Hud'
import { connect } from './cort/connection'

export default function App() {
  useEffect(connect, [])

  return (
    <>
      <Scene />
      <div className="scan" aria-hidden="true" />
      <Hud />
    </>
  )
}
