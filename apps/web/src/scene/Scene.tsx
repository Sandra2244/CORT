import { useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Bloom, ChromaticAberration, EffectComposer, Noise, Vignette } from '@react-three/postprocessing'
import { BlendFunction } from 'postprocessing'
import * as THREE from 'three'
import { Core } from './Core'
import { Particles } from './Particles'
import { target } from '../cort/connection'

/**
 * Todo lo que la escena anima por frame, en un único objeto mutable.
 * No es estado de React: el orbe se actualiza por mutación 60 veces por segundo
 * y React solo monta la escena.
 */
export type Drive = {
  color: THREE.Color
  hot: THREE.Color
  /** 0..1 "sonoridad" simulada: respiración en reposo, sube al pensar. */
  level: number
  spin: number
  scale: number
  intensity: number
  /** 0..1.6 revelado del anillo desde el centro. */
  open: number
  visible: boolean
}

function Rig() {
  const drive = useMemo<Drive>(
    () => ({
      color: target.color.clone(),
      hot: target.hot.clone(),
      level: 0,
      spin: target.spin,
      scale: 1,
      intensity: 1,
      open: 0,
      visible: true,
    }),
    [],
  )

  useFrame((state, dt) => {
    const k = Math.min(1, dt * 2.5)
    drive.color.lerp(target.color, k)
    drive.hot.lerp(target.hot, k)
    drive.spin += (target.spin - drive.spin) * Math.min(1, dt * 2)
    drive.open += (target.open - drive.open) * Math.min(1, dt * 1.6)
    // El tamaño que pidió la usuaria, perseguido igual que el color: un salto
    // directo se vería como un tirón, y esto es un holograma que respira.
    drive.scale += (target.zoom - drive.scale) * Math.min(1, dt * 3)
    // El orbe se esconde cuando el avatar toma la pantalla. Es un booleano y no
    // un fundido: fundir un ShaderMaterial querría un uniform más por partícula,
    // y aquí 1 fps valen.
    drive.visible = target.visible

    // Sin micrófono todavía: el nivel es una respiración, y pensar la agita.
    const idle = 0.05 + (target.spin > 1 ? 0.22 : 0)
    const breathe = (Math.sin(state.clock.elapsedTime * 0.9) * 0.5 + 0.5) * idle
    drive.level += (breathe - drive.level) * Math.min(1, dt * 9)

    // Deriva lenta de la cámara: mantiene la imagen viva sin ser un barrido.
    const t = state.clock.elapsedTime
    state.camera.position.x = Math.sin(t * 0.13) * 0.35
    state.camera.position.y = Math.cos(t * 0.17) * 0.22
    state.camera.lookAt(0, 0, 0)
  })

  // Nada de esto está iluminado: núcleo y polvo son ShaderMaterials crudos, que
  // no leen la lista de luces. La escena no tiene luces.
  return (
    <>
      <Core drive={drive} />
      <Particles drive={drive} />
    </>
  )
}

export function Scene() {
  return (
    <Canvas
      className="scene"
      camera={{ position: [0, 0, 6.2], fov: 45 }}
      gl={{ antialias: true, alpha: true }}
      dpr={[1, 2]}
    >
      <Rig />
      {/*
        multisampling={0} a propósito: no hay una sola arista poligonal que
        suavizar, todo es blob aditivo, puntos y líneas ya difuminados por bloom.
        En 1,8 GiB de RAM este ahorro de búfer no es cosmético.
      */}
      <EffectComposer multisampling={0}>
        {/* El bloom es lo que convierte líneas aditivas en "holograma". */}
        <Bloom intensity={1.15} luminanceThreshold={0.22} luminanceSmoothing={0.85} mipmapBlur radius={0.72} />
        <ChromaticAberration offset={new THREE.Vector2(0.0009, 0.0012)} radialModulation={false} modulationOffset={0} />
        <Noise opacity={0.035} blendFunction={BlendFunction.OVERLAY} />
        <Vignette eskil={false} offset={0.22} darkness={0.95} />
      </EffectComposer>
    </Canvas>
  )
}
