import { useMemo, useSyncExternalStore } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Bloom, ChromaticAberration, EffectComposer, Noise, Vignette } from '@react-three/postprocessing'
import { BlendFunction } from 'postprocessing'
import * as THREE from 'three'
import { Core } from './Core'
import { Particles } from './Particles'
import { Nube } from './Nube'
import { Vrm } from './Vrm'
import { REPOSO_MS, getSnapshot, setOrbeVisible, subscribe, target } from '../cort/connection'

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
  /** 0..1 cuánto se ha deshecho el reactor en la nube de reposo. */
  reposo: number
  /** 0..1 cuánto se ha formado el anillo de escucha. */
  escucha: number
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
      reposo: 0,
      escucha: 0,
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

    const t = state.clock.elapsedTime

    // -- qué cara toca ------------------------------------------------------
    // Escucha: el micrófono está abierto y nadie más tiene la palabra.
    // Reposo: nada ha pasado en REPOSO_MS (ni gesto, ni mensaje, ni voz) y CORT
    // ni piensa ni habla. Si no, el reactor de siempre.
    const quiereEscucha = target.forzar === 'escucha' || target.escucha
    const quiereReposo =
      !quiereEscucha &&
      (target.forzar === 'reposo' ||
        (REPOSO_MS > 0 &&
          !target.habla &&
          !getSnapshot().thinking &&
          performance.now() - target.actividad > REPOSO_MS))
    drive.escucha += ((quiereEscucha ? 1 : 0) - drive.escucha) * Math.min(1, dt * 1.3)
    drive.reposo += ((quiereReposo ? 1 : 0) - drive.reposo) * Math.min(1, dt * 0.8)
    // El reactor y su polvo se apagan a medida que la nube se enciende.
    drive.intensity = 1 - Math.max(drive.escucha, drive.reposo)

    // -- nivel --------------------------------------------------------------
    // Sin medidor de micrófono: el navegador no entrega el volumen del
    // reconocimiento de voz, así que el nivel se arma con lo que sí avisa
    // (empieza a hablar, llega una palabra, CORT pronuncia una palabra).
    target.nivel *= Math.exp(-dt * 4.5)
    const idle = 0.05 + (target.spin > 1 ? 0.22 : 0)
    const breathe = (Math.sin(t * 0.9) * 0.5 + 0.5) * idle
    // Respaldo mientras CORT habla: las voces «Natural» en línea no siempre
    // mandan el aviso de cada palabra, y el reactor no puede quedarse quieto.
    const habla = target.habla ? 0.28 + 0.22 * Math.abs(Math.sin(t * 7.1)) * (0.6 + 0.4 * Math.sin(t * 2.3)) : 0
    const oye = quiereEscucha
      ? target.oyendo
        ? 0.5
        : target.forzar === 'escucha'
          ? 0.35 + 0.3 * Math.max(0, Math.sin(t * 0.7)) * Math.abs(Math.sin(t * 5.0))
          : 0.16 + 0.05 * Math.sin(t * 1.3)
      : 0
    const meta = Math.max(breathe, habla, oye, target.nivel)
    drive.level += (meta - drive.level) * Math.min(1, dt * 9)

    // Deriva lenta de la cámara: mantiene la imagen viva sin ser un barrido.
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
      <Nube drive={drive} />
    </>
  )
}

export function Scene({ atuendo, tamaño = 1, onFallo, onInvocar }: {
  atuendo: string | null
  /** R7+: tamaño del `avatar CORT` elegido en la pestaña de atuendos. */
  tamaño?: number
  onFallo: () => void
  /** R5: tocar la zona del núcleo invoca la entrada (ver `App.tsx`). */
  onInvocar?: () => void
}) {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  // Un VRM se pinta **dentro del mismo canvas** que el reactor y no en un segundo
  // WebGL: dos contextos en esta máquina son dos colas de GPU, dos búferes y una
  // tasa de imágenes a la mitad. El orbe ya se apaga solo con `target.visible`.
  const vrm = atuendo && /\.vrm$/i.test(atuendo) ? atuendo : null
  return (
    <Canvas
      className="scene"
      camera={{ position: [0, 0, 6.2], fov: 45 }}
      gl={{ antialias: true, alpha: true }}
      onPointerDown={(e) => {
        // El gesto pertenece al centro, no a la pantalla entera: tocar un borde
        // no debe abrir la conversación mientras se mira el reactor. El rango
        // (20 %..80 % / 15 %..85 %) deja fuera la esquina de la bandeja y el
        // reloj de arriba. `e.nativeEvent` porque dentro del canvas R3F entrega
        // su propio evento sintético.
        const { clientX, clientY } = e.nativeEvent
        const x = clientX / window.innerWidth
        const y = clientY / window.innerHeight
        if (x > 0.2 && x < 0.8 && y > 0.15 && y < 0.85) onInvocar?.()
      }}
      // Con cuerpo 3D se fija `dpr` a 1: en un móvil con pantalla de 2x eso es
      // **la cuarta parte de píxeles** que rellenar, y aquí no hay GPU que ayude.
      dpr={vrm ? 1 : [1, 2]}
    >
      <Rig />
      {vrm && (
        <Vrm
          key={vrm}
          nombre={vrm}
          outfit={s.outfit}
          tamaño={tamaño}
          onFallo={() => {
            // Se vuelve al reactor sin dejar el cuerpo a medio cargar: el orbe
            // manda otro aviso y la usuaria ve que CORT sigue ahí.
            setOrbeVisible(true)
            onFallo()
          }}
        />
      )}
      {/*
        multisampling={0} a propósito: no hay una sola arista poligonal que
        suavizar, todo es blob aditivo, puntos y líneas ya difuminados por bloom.
        En 1,8 GiB de RAM este ahorro de búfer no es cosmético.

        Y con un cuerpo 3D montado la cadena **se quita entera**. Medido el
        2026-10-09: el orbe solo va a 18 fps, y con el `.vrm` encima más los cuatro
        pases de postproceso la pantalla cayó a **0,7 fps** (un cuadro cada metro
        y pico de segundo). Cuatro pasadas a pantalla completa sobre software
        rasterizer no las paga esta máquina; el filo de Fresnel del material ya
        brilla por sí solo, así que lo que se pierde es el halo del orbe, que
        estaba apagado de todos modos.
      */}
      {!vrm && (
        <EffectComposer multisampling={0}>
          {/* El bloom es lo que convierte líneas aditivas en "holograma". */}
          <Bloom intensity={1.15} luminanceThreshold={0.22} luminanceSmoothing={0.85} mipmapBlur radius={0.72} />
          <ChromaticAberration offset={new THREE.Vector2(0.0009, 0.0012)} radialModulation={false} modulationOffset={0} />
          <Noise opacity={0.035} blendFunction={BlendFunction.OVERLAY} />
          <Vignette eskil={false} offset={0.22} darkness={0.95} />
        </EffectComposer>
      )}
    </Canvas>
  )
}
