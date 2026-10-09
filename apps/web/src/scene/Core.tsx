/**
 * El reactor de CORT.
 *
 * Transplantado de adewaskar/JARVIS (https://github.com/adewaskar/jarvis),
 * licencia MIT (c) su autor. Se conserva el shader tal cual; ver CREDITS.md.
 * Se eliminó el uniforme `uStyle` y sus ponderaciones: en el modo de fábrica
 * (`ring`) todos los factores valen 1 y el relleno del cuerpo vale 0, así que
 * la imagen resultante es idéntica término a término.
 *
 * Se dibuja como un solo plano de cara a la cámara con un fragment shader polar,
 * en vez de como geometría: todo es función del radio y del ángulo, lo que
 * permite que el borde erosionado sea turbulencia real por píxel en lugar de una
 * malla deformada fingiendo ser un anillo.
 */
import { useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import type { Drive } from './Scene'

const vertex = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`

const fragment = /* glsl */ `
  uniform vec3  uColor;
  uniform vec3  uHot;
  uniform float uLevel;
  uniform float uPhase;
  uniform float uOpen;
  uniform float uZoom;
  uniform float uIntensity;

  varying vec2 vUv;

  vec2 hash(vec2 p) {
    p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
    return -1.0 + 2.0 * fract(sin(p) * 43758.5453123);
  }

  float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(
      mix(dot(hash(i + vec2(0.0, 0.0)), f - vec2(0.0, 0.0)),
          dot(hash(i + vec2(1.0, 0.0)), f - vec2(1.0, 0.0)), u.x),
      mix(dot(hash(i + vec2(0.0, 1.0)), f - vec2(0.0, 1.0)),
          dot(hash(i + vec2(1.0, 1.0)), f - vec2(1.0, 1.0)), u.x),
      u.y);
  }

  float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 5; i++) {
      v += a * noise(p);
      p *= 2.02;
      a *= 0.5;
    }
    return v;
  }

  /** Círculo suave de radio r0 y grosor w. */
  float band(float r, float r0, float w) {
    return exp(-pow((r - r0) / w, 2.0));
  }

  #define TAU 6.28318530718

  void main() {
    vec2 p = (vUv * 2.0 - 1.0) * uZoom;
    float r = length(p);
    float a = atan(p.y, p.x);

    // Muestrear la turbulencia sobre el círculo unitario y no sobre p mantiene
    // el patrón continuo a través de la costura -pi/pi, que una búsqueda directa
    // por atan rompe.
    vec2 ring = vec2(cos(a), sin(a));

    // -- el anillo principal -------------------------------------------------
    // El radio oscila en dos escalas, así el contorno nunca es un círculo limpio.
    float wob   = fbm(ring * 2.6 + vec2(uPhase * 0.22, 0.0)) * 0.055;
    float grain = fbm(ring * 9.0 - vec2(uPhase * 0.4, 0.0)) * 0.020;
    float R = 0.74 + wob + grain + uLevel * 0.03;

    // Erosión: el borde exterior se come a parches, así el anillo se ve luminoso
    // e inestable en vez de un trazo dibujado.
    float erode = smoothstep(-0.25, 0.35, fbm(ring * 5.0 + vec2(uPhase * 0.5, 3.0)));

    float outer = band(r, R, 0.030) * (0.45 + erode * 0.6);
    // Una segunda pasada más apretada por dentro da al anillo una pared interior,
    // que es lo que lo hace leerse como un tubo visto ligeramente de frente.
    float wall  = band(r, R - 0.055, 0.020) * 0.5;
    // Filamento fino y brillante sobre el borde exterior.
    float edge  = band(r, R + 0.004, 0.007) * (0.5 + uLevel * 0.45);

    // Polvo adherido al borde: es el detalle que hace que el anillo se disuelva
    // en granos en lugar de terminar en una línea.
    float speck = fbm(ring * 46.0 + vec2(uPhase * 0.15, 11.0));
    speck = pow(max(speck, 0.0), 3.0);
    float dust = speck * band(r, R + 0.028, 0.055) * (1.4 + uLevel);

    // -- barrido tipo radar --------------------------------------------------
    float sweepA = mod(uPhase * 0.55, TAU);
    float dA = mod(a - sweepA + TAU + 3.14159, TAU) - 3.14159;
    float wake = smoothstep(-2.6, -0.15, dA) * (1.0 - smoothstep(0.0, 0.22, dA));
    float radar = wake * band(r, R - 0.02, 0.075) * (0.55 + uLevel * 0.45);

    // -- filetes concéntricos interiores ------------------------------------
    float lines =
        band(r, 0.615, 0.0035) * 0.45
      + band(r, 0.560, 0.0030) * 0.28
      + band(r, 0.470, 0.0035) * 0.36;

    // -- disco texturado del núcleo -----------------------------------------
    // Dos mallas polares girando en sentidos opuestos: se lee como una membrana
    // tejida, no como rayas.
    float m1 = (sin(a * 96.0 + uPhase * 0.6) * 0.5 + 0.5)
             * (sin(r * 210.0) * 0.5 + 0.5);
    float m2 = (sin(a * 60.0 - uPhase * 0.4) * 0.5 + 0.5)
             * (sin(r * 150.0 - uPhase) * 0.5 + 0.5);
    float mesh = mix(m1, m2, 0.5);
    float core = smoothstep(0.40, 0.36, r);
    float coreTex = core * (0.04 + mesh * 0.12) * (0.55 + uLevel * 0.9);
    float coreEdge = band(r, 0.385, 0.010) * (0.55 + uLevel * 0.5);

    // Pulso lento que ondula hacia afuera: el latido del reactor.
    float pulse = band(r, fract(uPhase * 0.08) * 0.40, 0.020) * core * 0.45;

    float bloom = exp(-r * 3.4) * (0.16 + uLevel * 0.34);

    float v = (outer + wall + edge)
            + dust
            + radar
            + lines
            + coreTex + pulse
            + bloom;

    // Los brillos en movimiento corren calientes; el cuerpo del anillo conserva
    // su matiz.
    vec3 col = mix(uColor, uHot,
      clamp(edge * 1.3 + radar * 0.7 + pulse * 0.5 + dust * 0.4, 0.0, 1.0));

    // Revelado radial al encender: el anillo se construye desde el centro.
    v *= smoothstep(0.0, 0.35, uOpen - r * 0.45);

    v *= uIntensity;

    gl_FragColor = vec4(col * v, v);
  }
`

/** Semiancho del plano en unidades de mundo. */
const HALF = 2.7
/** Radio del anillo en unidades del propio campo del shader. */
const RING_R = 0.74
/**
 * Diámetro del anillo como fracción de la dimensión MÁS CORTA del viewport.
 * El encuadre tiene que depender del viewport: el mismo ajuste que deja margen
 * cómodo en un monitor 16:9 saca el anillo por los dos bordes en vertical.
 */
const FIT = 0.60

export function Core({ drive }: { drive: Drive }) {
  const mat = useRef<THREE.ShaderMaterial>(null)
  const mesh = useRef<THREE.Mesh>(null)
  const viewport = useThree((s) => s.viewport)

  const uniforms = useMemo(
    () => ({
      uColor: { value: new THREE.Color('#3fd8ff') },
      uHot: { value: new THREE.Color('#dffbff') },
      uLevel: { value: 0 },
      uPhase: { value: 0 },
      uOpen: { value: 0 },
      uZoom: { value: 1.2 },
      uIntensity: { value: 1 },
    }),
    [],
  )

  useFrame((_, dt) => {
    if (!mat.current || !mesh.current) return
    const u = mat.current.uniforms

    mesh.current.visible = drive.visible
    mesh.current.scale.setScalar(drive.scale)

    const fit = Math.min(viewport.width, viewport.height)
    u.uZoom.value = (RING_R * HALF) / (FIT * 0.5 * fit)
    u.uLevel.value += (drive.level - u.uLevel.value) * Math.min(1, dt * 8)
    // Se acumula en vez de derivar del reloj escalado por el nivel: escalar el
    // reloj reescribiría toda la turbulencia ya ocurrida.
    u.uPhase.value += dt * (0.5 + u.uLevel.value * 0.7) * drive.spin
    u.uOpen.value += (drive.open - u.uOpen.value) * Math.min(1, dt * 1.6)
    u.uIntensity.value = drive.intensity
    ;(u.uColor.value as THREE.Color).lerp(drive.color, Math.min(1, dt * 2.5))
    ;(u.uHot.value as THREE.Color).lerp(drive.hot, Math.min(1, dt * 2.5))
  })

  return (
    <mesh ref={mesh} frustumCulled={false}>
      <planeGeometry args={[5.4, 5.4]} />
      <shaderMaterial
        ref={mat}
        uniforms={uniforms}
        vertexShader={vertex}
        fragmentShader={fragment}
        transparent
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </mesh>
  )
}
