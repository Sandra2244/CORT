import { useEffect, useMemo, useRef, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import type { VRM, VRMHumanBoneName } from '@pixiv/three-vrm'
import { avatarUrl } from '../cort/connection'
import { DEFAULT_OUTFIT, palette, type Outfit } from '../cort/palette'

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

/**
 * Altura objetivo en la escena: lo que ve la cámara a z=0 con fov 45 son ~5,1 unidades.
 *
 * R7 del rediseño: el cuerpo **bajó de 3,4 a 2,3**. Con el reactor encogido a
 * zócalo (zoom 0,55) la figura ya no llena la pantalla: es la cara de pie sobre
 * su pedestal, como el holograma pequeño de las referencias. Y el número tiene
 * una razón de hardware: menos píxeles de malla que rasterizar en una máquina
 * sin GPU. La ganancia de fps hay que medirla, no afirmarla (STATUS.md).
 */
const ALTURA = 2.3

/** Cuánto sube el cuerpo sobre el centro para que los pies descansen en el zócalo. */
const PEDESTAL = 0.9

/**
 * Segundos que dura la materialización: el cuerpo no aparece de golpe, sube
 * desde el zócalo mientras el alfa se revela, como en las referencias v3/v5.
 */
const MATERIA = 1.8

/**
 * Cuánto se bajan los brazos desde la pose en T del `.vrm` (radianes). 1,2 es el
 * número que salió de la barrida: deja el húmero a lo largo del cuerpo con los
 * dedos separados de la cadera. A π/2 (1,57) el brazo se clava contra el muslo.
 */
const BRAZOS = 1.2

/**
 * El tinte del atuendo, en la misma paleta que el reactor: si el cuerpo fuera de
 * un azul fijo y el orbe de otro, cambiar de atuendo partiría la pantalla en dos
 * colores que no combinan.
 */
function tinte(atuendo: Outfit): THREE.Color {
  const p = palette[atuendo] ?? palette[DEFAULT_OUTFIT]
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
  uniform float uMateria;
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
                   + uTinte * rayas * 0.10
                   // Durante la materialización el filo arde más: la energía se
                   // ve en el borde antes de que el cuerpo esté entero.
                   + uTinte * filo * ( 1.0 - uMateria ) * 1.6;
  // uMateria es la cortina del alfa: 0 = aun dentro del reactor, 1 = holograma
  // completo. Sin multiplicar aqui, el cuerpo apareceria recortado de golpe.
  gl_FragColor.a = clamp( 0.16 + filo * 0.85 + barrido * 0.35, 0.0, 1.0 ) * uMateria;
`

type Estado = 'cargando' | 'listo' | 'roto'

/**
 * Un hueso con deriva: la rotación de reposo capturada al cargar y la amplitud
 * con la que respira alrededor. Se escribe siempre sobre el **reposo** (suma, no
 * sustitución) para que cambiar de pose base no borre la animación.
 */
type HuesoVivo = {
  nodo: THREE.Object3D
  bx: number
  by: number
  fx: number
  ax: number
  fy: number
  ay: number
  fase: number
}

export function Vrm({ nombre, outfit, tamaño = 1, onFallo }: {
  nombre: string
  outfit: Outfit
  /** Multiplicador de escala: 1 = la figura medida de R7; 0,72 y 1,25 son sus tamaños. */
  tamaño?: number
  onFallo: () => void
}) {
  const [estado, setEstado] = useState<Estado>('cargando')
  const vrm = useRef<VRM | null>(null)
  const grupo = useMemo(() => new THREE.Group(), [])
  // Los huesos que respiran, llenos al cargar el modelo.
  const vivos = useRef<HuesoVivo[]>([])
  // El gestor de expresiones del `.vrm` (pestañas, sonrisa); `undefined` si el
  // archivo no las trae — `setValue` con un nombre desconocido no lanza nada,
  // leído en la fuente de `@pixiv/three-vrm@3`, así que no hace falta try/catch.
  const expresiones = useRef<VRM['expressionManager']>(undefined)
  // Geometría de apoyo: el centro de la caja sin pedestal y el factor de escala,
  // para poder rehacer posición y tamaño cada cuadro sin volver a medir la malla.
  const apoyo = useRef({ centro: 0, factor: 1 })
  const materia = useRef(0)
  const tiempo = useRef(0)
  const tama = useRef(1)
  const parpadeo = useRef({ siguiente: 2.4, cerrando: -1 })
  // Un solo objeto de uniformes compartido por todas las piezas del cuerpo: si
  // cada malla tuviera el suyo, el barrido subiría desincronizado por brazo,
  // pelo y vestido.
  const reloj = useMemo(
    () => ({
      uTiempo: { value: 0 },
      uBanda: { value: 0 },
      uAlto: { value: ALTURA },
      uMateria: { value: 0 },
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

          // Sonda de medición: con `?sonda` en la URL el modelo queda a mano desde
          // la consola, que es como se barrió el eje de los brazos en vez de
          // adivinarlo. Sin el parámetro no se publica ningún objeto global.
          if (new URLSearchParams(window.location.search).has('sonda')) {
            ;(window as unknown as Record<string, unknown>).__cort_vrm = modelo
          }

          // Un VRM 0..x mira hacia -Z; sin girarlo, CORT da la espalda.
          VRMUtils.rotateVRM0(modelo)
          // **Postura, no adorno:** un `.vrm` llega en T y una chica flotando con
          // los brazos en cruz es un maniquí de tienda, no Cortana.
          //
          // Se escribe el hueso **crudo** y se apaga la copia que lo borraba.
          // `VRMHumanoid.update()` no hace nada más que copiar el esqueleto
          // normalizado sobre el crudo — es la única línea de su cuerpo, leída en
          // la fuente de `@pixiv/three-vrm` —, así que con
          // `autoUpdateHumanBones = false` lo que se escribe aquí es lo que se
          // pinta, sin trabajo por frame. Medido con `?sonda` sobre
          // `avatar CORT base.vrm`: escribiendo en el **normalizado** la rotación
          // leía `[0, 0, 0]` poco después y el cuerpo seguía en cruz; escribiendo
          // en el crudo la muñeca izquierda pasó de `[1,117 · y 0,96]` a
          // `[0,547 · y 0,126]` y la derecha, en espejo, de `[-1,117 · 0,96]` a
          // `[-0,547 · 0,126]`. Aquí no se pierde nada al apagar la copia: CORT no
          // hace retargeting ni reproduce animaciones, sólo sostiene una pose.
          //
          // Ni el eje ni el signo se adivinaron: se barrieron los seis
          // (x, y, z × ±) midiendo la muñeca en el mundo. Sólo el **Z** baja el
          // brazo; x e y lo llevan adelante o atrás (`dy ≈ 0`). Y el reposo no es
          // simétrico — el izquierdo arranca en `z = +0,141`, el derecho en
          // `z = -0,141` —, por eso el giro se **suma sobre el reposo** en vez de
          // sustituirlo. Codos y muñecas se quedan como vienen: lo que se veía mal
          // era la cruz, y esa ya está resuelta.
          const humano = modelo.humanoid
          if (humano) {
            humano.autoUpdateHumanBones = false
            vivos.current = []
            // Registra un hueso para la respiración procedural: primero se le da
            // su giro de reposo (los brazos bajan de la cruz), y de ahí se
            // capturan las rotaciones como base. Las amplitudes son pequeñas a
            // propósito — 0,01-0,05 rad: un holograma que se sacude entero es un
            // error de imagen; lo que vende vida es que *nada* esté perfectamente
            // quieto. Las frecuencias van desfasadas entre huesos para que cadera,
            // cuello y cabeza no cabeceen al unísono.
            const registrar = (
              hueso: VRMHumanBoneName,
              giroZ = 0,
              deriva: { fx?: number; ax?: number; fy?: number; ay?: number; fase?: number } = {},
            ) => {
              const nodo = humano.getRawBoneNode(hueso)
              if (!nodo) return
              if (giroZ) nodo.rotation.z += giroZ
              vivos.current.push({
                nodo,
                bx: nodo.rotation.x,
                by: nodo.rotation.y,
                fx: deriva.fx ?? 0,
                ax: deriva.ax ?? 0,
                fy: deriva.fy ?? 0,
                ay: deriva.ay ?? 0,
                fase: deriva.fase ?? 0,
              })
            }
            // Los brazos respiran con el pecho (misma frecuencia ~0,9 rad/s que
            // el `breathe` del reactor en `Scene.tsx`, para que cuerpo y zócalo
            // no latan desincronizados). Cadera, cuello y cabeza llevan deriva
            // propia: quien mira un punto fijo no está rígido, micro-mira.
            registrar('leftUpperArm', -BRAZOS, { fx: 0.9, ax: 0.014, fase: 0 })
            registrar('rightUpperArm', BRAZOS, { fx: 0.9, ax: 0.014, fase: 1.1 })
            registrar('hips', 0, { fx: 0.21, ax: 0.014, fase: 0.4 })
            registrar('neck', 0, { fx: 0.23, ax: 0.02, fy: 0.19, ay: 0.03, fase: 2.1 })
            registrar('head', 0, { fx: 0.17, ax: 0.03, fy: 0.13, ay: 0.05, fase: 0.6 })
          }
          // Expresiones: la sonrisa de reposo queda puesta una sola vez (el peso
          // es persistente; `expressionManager.update()`, que corre dentro de
          // `vrm.update(dt)`, la mantiene aplicada). El parpadeo se anima por
          // cuadro más abajo. Si el `.vrm` no trae un ojo que cierre, `setValue`
          // no hace nada y CORT simplemente no parpadea.
          expresiones.current = modelo.expressionManager
          modelo.expressionManager?.setValue('happy', 0.18)
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
            const parchear = (vieja: THREE.Material) => {
              const origen = vieja as THREE.Material & {
                color?: THREE.Color
                map?: THREE.Texture | null
              }
              // Tres cosas de `three` construyen el macro `MAP_UV` como
              // `'uv' + texture.channel`. Las texturas que entrega
              // `@pixiv/three-vrm@3.5.5` no traen `channel` numérico, el macro sale
              // literalmente `uvundefined`, el navegador **no compila el programa**
              // y el cuerpo queda invisible: medido el 2026-10-09 con
              // `'uvundefined' : undeclared identifier` y 259 avisos por cuadro de
              // `useProgram: program not valid`. Se normaliza en el único sitio
              // donde CORT decide qué textura entra en el material nuevo.
              const mapa = origen.map ?? null
              if (mapa && typeof mapa.channel !== 'number') mapa.channel = 0
              const nueva = new THREE.MeshStandardMaterial({
                color: origen.color ? origen.color.clone() : new THREE.Color(1, 1, 1),
                map: mapa,
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
              vieja.dispose?.()
              return nueva
            }
            // Una malla puede traer varios materiales (cara, ropa, pelo). Si se le
            // pone uno solo, los `groups` de la geometría apuntarían al índice
            // equivocado y media cara vestiría el color de la otra.
            malla.material = Array.isArray(malla.material)
              ? malla.material.map(parchear)
              : parchear(malla.material)
          })

          // Escala por caja dinámica: los VRM traen alturas distintas y un
          // «1,7 m» escrito a mano dejaría a unos fuera del cuadro y a otros
          // encogidos. El centro de la caja va al centro de la escena.
          const caja = new THREE.Box3().setFromObject(modelo.scene)
          const alto = Math.max(0.001, caja.max.y - caja.min.y)
          const factor = ALTURA / alto
          // Se guardan el centro y el factor en crudo porque la materialización y
          // el selector de tamaño reescriben escala y posición **cada cuadro**:
          // el pie derecho sobre el zócalo es `PEDESTAL + centro·escala`, y si la
          // escala cambia sin rehacer el término de centro, los pies flotan o se
          // hunden según el tamaño.
          apoyo.current = { centro: -(caja.max.y + caja.min.y) * 0.5, factor }
          // Estado inicial de la materialización: encogida y hundida en el
          // reactor; `useFrame` la yergue. El alfa arranca en 0 (`uMateria`), así
          // que estos primeros cuadros no se ven todavía.
          materia.current = 0
          reloj.uMateria.value = 0
          grupo.scale.setScalar(factor * 0.86)
          grupo.position.set(0, PEDESTAL + apoyo.current.centro * factor - ALTURA * 0.55, 0)
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
    const t = (tiempo.current += paso)
    vrm.current?.update(paso)
    reloj.uTiempo.value += paso
    // 14 segundos por recorrido completo: lo bastante lento para no marear y lo
    // bastante rápido para que se vea que la imagen está viva.
    reloj.uBanda.value = (reloj.uBanda.value + paso / 14) % 1

    // ── Materialización ─────────────────────────────────────────────────────
    // `smoothstep` sobre un contador lineal: arranca suave (nace en el zócalo),
    // acelera a mitad y se asienta sin rebote — un rebote elástico se leería
    // como gelatina, y esto es luz, no goma.
    materia.current = Math.min(1, materia.current + paso / MATERIA)
    const m = materia.current
    const revelado = m * m * (3 - 2 * m)
    reloj.uMateria.value = revelado

    // El tamaño elegido se persigue, no se salta: el mismo patrón de `target`
    // con lerp que rige el color y el zoom del orbe desde el primer día.
    tama.current += (tamaño - tama.current) * Math.min(1, dt * 3)
    const escala = apoyo.current.factor * tama.current * (0.86 + 0.14 * revelado)
    grupo.scale.setScalar(escala)
    // Pies sobre el zócalo a cualquier tamaño (ver `apoyo`), hundida ALTURA·0,55
    // al principio de la materialización, y encima la respiración: 1,2 cm de
    // ascenso y descenso lento que es lo primero que el ojo lee como "viva".
    grupo.position.y =
      PEDESTAL +
      apoyo.current.centro * escala -
      (1 - revelado) * ALTURA * 0.55 +
      Math.sin(t * 1.05) * 0.012

    // ── Reposo animado ──────────────────────────────────────────────────────
    for (const h of vivos.current) {
      if (h.fx) h.nodo.rotation.x = h.bx + Math.sin(t * h.fx + h.fase) * h.ax
      if (h.fy) h.nodo.rotation.y = h.by + Math.sin(t * h.fy + h.fase) * h.ay
    }

    // ── Parpadeo ────────────────────────────────────────────────────────────
    // Triángulo de 140 ms cada 2,4-5,4 s: abrir y cerrar a diente de sierra se
    // ve mecánico; medio ciclo de subida, medio de bajada, es lo que hace un
    // ojo. Sin `AnimationMixer` ni clips `.vrma` — dos restas y un contador.
    const em = expresiones.current
    if (em) {
      const pa = parpadeo.current
      if (pa.cerrando < 0 && t >= pa.siguiente) pa.cerrando = t
      if (pa.cerrando >= 0) {
        const q = (t - pa.cerrando) / 0.14
        if (q >= 1) {
          pa.cerrando = -1
          pa.siguiente = t + 2.4 + Math.random() * 3
          em.setValue('blink', 0)
        } else {
          em.setValue('blink', 1 - Math.abs(q * 2 - 1))
        }
      }
    }
  })

  if (estado === 'roto') return null
  // `<primitive>` es la forma de meter en React un objeto de Three que no es un
  // elemento: el grupo lo creó el cargador, y React no lo reconcilia cada frame.
  return <primitive object={grupo} visible={estado === 'listo'} />
}
