import { useEffect, useMemo, useRef, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import type { VRM } from '@pixiv/three-vrm'
import { avatarUrl } from '../cort/connection'
import { palette, type Outfit } from '../cort/palette'

/**
 * `VRMUtils` se pide con `import()` y no con `import`: así la biblioteca de
 * avatar sale en un trozo aparte y no viaja con la página hasta que alguien elige
 * un `avatar CORT`. Se anota con `typeof import(...)` porque lo que se guarda es
 * el objeto de la biblioteca, no un tipo suyo.
 */
type Utilerias = (typeof import('@pixiv/three-vrm'))['VRMUtils']

/**
 * El cuerpo de CORT en tres dimensiones: un VRM de disco vestido con un material
 * holográfico escrito aquí.
 *
 * Dos cosas hay que decir de entrada, porque son las que se rompen:
 *
 * - **Es un experimento medido, no una promesa.** Un VRM son 16-21 MB de malla
 *   esqueletizada con sus texturas, y esta máquina no tiene GPU: si va a 8 fps,
 *   la respuesta correcta es quitarlo, no explicarlo bonito. El número está en
 *   `docs/STATUS.md`.
 * - **El material es nuestro.** La idea óptica —borde brillante donde la normal
 *   mira a un lado, una banda de escaneo que sube, mezcla aditiva sin escribir
 *   profundidad— es geometría sabida, y el shader que la implementa está escrito
 *   aquí desde cero. No viene copiado de ningún repositorio: los dos que imitan
 *   este aspecto son AGPL-3.0, y su código no entra en CORT (regla 9 de AGENTS.md).
 *
 * Se parchea el sombreador **estándar** de Three con `onBeforeCompile` en vez de
 * escribir un `ShaderMaterial` desde cero por un motivo concreto: el cuerpo es un
 * `SkinnedMesh` con huesos y morph targets, y esas dos cosas las resuelve Three
 * solo si el programa sigue siendo el de `MeshStandardMaterial`. Con un shader
 * propio habríamos tenido que incluir a mano los fragmentos de skinning, y un
 * olvido se vería como un avatar tieso en cruz.
 */

/** Altura objetivo en la escena: lo que ve la cámara a z=0 con fov 45 son ~5,1 unidades. */
const ALTURA = 3.4

/**
 * El tinte del atuendo, en la misma paleta que el reactor: si el cuerpo fuera de
 * un azul fijo y el orbe de otro, cambiar de atuendo partiría la pantalla en dos
 * colores que no combinan.
 */
function tinte(atuendo: Outfit): THREE.Color {
  const p = palette[atuendo] ?? palette.work
  return new THREE.Color(p.ui)
}

const HOLO_VERTEX = /* glsl */ `
  varying float vAlturaH;
`

/**
 * Se inyecta justo después de `skinning_vertex`, que es donde el vértice ya tiene
 * su posición con los huesos aplicados: medir la altura antes de pielar daría una
 * banda de escaneo que se queda quieta mientras el cuerpo se mueve.
 */
const HOLO_VERTEX_MAIN = /* glsl */ `
  #include <skinning_vertex>
  vAlturaH = transformed.y;
`

const HOLO_FRAGMENT = /* glsl */ `
  uniform vec3 uTinte;
  uniform float uTiempo;
  uniform float uBanda;
  uniform float uAlto;
  varying float vAlturaH;
`

/**
 * El efecto, al final del programa estándar.
 *
 * `gl_FragColor` ya trae el color del tejido (la textura del atuendo). Se
 * **multiplica** por el tinte y no se sustituye: es lo que hace que un vestido
 * rojo siga rojo y un pijama azul siga siendo pijama azul, que fue la condición
 * que puso la dueña del proyecto. Lo que sí se sustituye es el alfa.
 */
const HOLO_FRAGMENT_MAIN = /* glsl */ `
  #include <dithering_fragment>
  vec3 n = normalize( normal );
  vec3 v = normalize( vViewPosition );
  // Fresnel: donde la superficie se va de lado, el vidrio fantasma brilla.
  float filo = pow( 1.0 - abs( dot( n, v ) ), 3.0 );
  // Líneas de scan horizontales, lentas — un holograma parpadeando fuerte es un
  // error de imagen, no un efecto.
  float rayas = 0.5 + 0.5 * sin( ( vAlturaH - uTiempo * 0.12 ) * 120.0 );
  // La banda que recorre el cuerpo de abajo a arriba, en bucle.
  float d = ( vAlturaH - uBanda * uAlto ) / 0.16;
  float barrido = exp( - d * d );
  gl_FragColor.rgb = gl_FragColor.rgb * mix( vec3( 0.55, 0.7, 1.25 ), uTinte, 0.5 )
                   + uTinte * filo * 1.9
                   + uTinte * barrido * 0.8
                   + uTinte * rayas * 0.10;
  gl_FragColor.a = clamp( 0.16 + filo * 0.85 + barrido * 0.35, 0.0, 1.0 );
`

type Estado = 'cargando' | 'listo' | 'roto'

export function Vrm({ nombre, outfit, onFallo }: { nombre: string; outfit: Outfit; onFallo: () => void }) {
  const [estado, setEstado] = useState<Estado>('cargando')
  const vrm = useRef<VRM | null>(null)
  const grupo = useMemo(() => new THREE.Group(), [])
  // Un solo objeto de uniformes compartido por todas las piezas del cuerpo: si
  // cada malla tuviera el suyo, el barrido subiría desincronizado por brazo,
  // pelo y vestido.
  const reloj = useMemo(
    () => ({
      uTiempo: { value: 0 },
      uBanda: { value: 0 },
      uAlto: { value: ALTURA },
      uTinte: { value: tinte(outfit) },
    }),
    [],
  )

  useEffect(() => {
    let vivo = true
    let montado: THREE.Object3D | null = null
    let utils: Utilerias | null = null

    // El plugin se registra en el cargador, no en el modelo: sin él, un .vrm se
    // lee como un glTF corriente y se pierde todo lo que lo hace un avatar
    // (huesos humanoides, expression clips, el material MToon original).
    const loader = new GLTFLoader()
    import('@pixiv/three-vrm').then(({ VRMLoaderPlugin, VRMUtils }) => {
      utils = VRMUtils
      loader.register((parser) => new VRMLoaderPlugin(parser))
      loader.load(
        avatarUrl(nombre),
        (gltf) => {
          if (!vivo) return
          const modelo = gltf.userData.vrm as VRM | undefined
          if (!modelo) {
            setEstado('roto')
            onFallo()
            return
          }
          vrm.current = modelo

          // Un VRM 0..x mira hacia -Z; sin girarlo, CORT da la espalda.
          VRMUtils.rotateVRM0(modelo)
          // Estas dos podas quitan vértices y huesos que no usa ninguna malla. No
          // son limpieza estética: en una máquina sin GPU cada vértice y cada
          // articulación es trabajo por frame.
          VRMUtils.removeUnnecessaryVertices(gltf.scene)
          VRMUtils.removeUnnecessaryJoints(gltf.scene)
          // `combineSkeletons` (la forma nueva de acelerar esto, y la que la
          // biblioteca sugiere encima de la llamada de arriba) **no se usa a
          // propósito**: fusiona las mallas que comparten esqueleto y se queda con
          // un material, así que los ocho atuendos proyectarían el mismo color y
          // «que se vea el color de la ropa» se iría al revés. Preferimos más
          // llamadas de dibujo y la ropa visible.
          // Los hologramas no escriben profundidad, así que el orden de dibujo
          // importa y las cajas de ajuste de la malla ya no valen para recortar.
          modelo.scene.traverse((obj) => {
            obj.frustumCulled = false
          })

          modelo.scene.traverse((obj) => {
            const malla = obj as THREE.Mesh
            if (!malla.isMesh) return
            const vieja = malla.material as THREE.Material & { color?: THREE.Color; map?: THREE.Texture | null }
            const nueva = new THREE.MeshStandardMaterial({
              color: vieja.color ? vieja.color.clone() : new THREE.Color(1, 1, 1),
              map: vieja.map ?? null,
              transparent: true,
              depthWrite: false,
              side: THREE.DoubleSide,
              roughness: 1,
              metalness: 0,
            })
            nueva.onBeforeCompile = (shader) => {
              shader.vertexShader = shader.vertexShader
                .replace('void main() {', `${HOLO_VERTEX}\nvoid main() {`)
                .replace('#include <skinning_vertex>', HOLO_VERTEX_MAIN)
              shader.fragmentShader = shader.fragmentShader.replace(
                'void main() {',
                `${HOLO_FRAGMENT}\nvoid main() {`,
              )
              shader.fragmentShader = shader.fragmentShader.replace(
                '#include <dithering_fragment>',
                `#include <dithering_fragment>\n${HOLO_FRAGMENT_MAIN}`,
              )
              Object.assign(shader.uniforms, reloj)
            }
            malla.material = nueva
            vieja.dispose?.()
          })

          // Escala por caja dinámica: los VRM traen alturas distintas y un
          // «1,7 m» escrito a mano dejaría a unos fuera del cuadro y a otros
          // encogidos. El centro de la caja va al centro de la escena.
          const caja = new THREE.Box3().setFromObject(modelo.scene)
          const alto = Math.max(0.001, caja.max.y - caja.min.y)
          const factor = ALTURA / alto
          grupo.scale.setScalar(factor)
          grupo.position.set(0, -(caja.max.y + caja.min.y) * 0.5 * factor, 0)
          // El alto ya escalado, para que el barrido recorra de los pies a la
          // cabeza pase lo que mida el modelo.
          reloj.uAlto.value = Math.max(0.01, (caja.max.y - caja.min.y) * factor)
          grupo.add(modelo.scene)
          montado = modelo.scene
          setEstado('listo')
        },
        undefined,
        () => {
          if (!vivo) return
          setEstado('roto')
          onFallo()
        },
      )
    })

    return () => {
      vivo = false
      // `deepDispose` recorre el cuerpo liberando geometrías, texturas y
      // materiales. Cambiar de atuendo ocho veces sin esto sería ocho cuerpos
      // vivos en la memoria de una máquina que tiene 1,8 GiB en total.
      if (vrm.current && utils) {
        utils.deepDispose(vrm.current.scene)
        vrm.current = null
      }
      montado?.parent?.remove(montado)
      grupo.clear()
    }
  }, [nombre, grupo, reloj, onFallo])

  // El tinte se actualiza sin recargar nada: es un uniform, no un material nuevo.
  useEffect(() => {
    reloj.uTinte.value = tinte(outfit)
  }, [outfit, reloj])

  useFrame((_, dt) => {
    if (estado !== 'listo') return
    const paso = Math.min(dt, 0.1)
    vrm.current?.update(paso)
    reloj.uTiempo.value += paso
    // 14 segundos por recorrido completo: lo bastante lento para no marear y lo
    // bastante rápido para que se vea que la imagen está viva.
    reloj.uBanda.value = (reloj.uBanda.value + paso / 14) % 1
  })

  if (estado === 'roto') return null
  // `<primitive>` es la forma de meter en React un objeto de Three que no es un
  // elemento: el grupo lo creó el cargador, y React no lo reconcilia cada frame.
  return <primitive object={grupo} visible={estado === 'listo'} />
}
