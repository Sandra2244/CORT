/**
 * La nube de CORT: lo que la cara es cuando nadie la está usando y cuando
 * alguien le habla.
 *
 * Dos estados de un mismo campo de partículas, tomados de las referencias que
 * trajo Sandra (el JARVIS de @techenclair):
 *
 *  - **reposo**: puntos que dibujan hilos curvos y punteados alrededor de un
 *    destello central de chispas. Casi quieto; respira.
 *  - **escucha**: los mismos puntos se juntan en un anillo que gira como un
 *    remolino, con estelas largas y grumos más brillantes. La voz lo agita.
 *
 * Todo se calcula en el vertex shader: la CPU sólo actualiza ocho números por
 * cuadro. No hay posiciones por partícula en JavaScript, así que el coste en una
 * máquina modesta es el de pintar ~11 000 puntos, y **sólo mientras la nube se
 * ve**: en uso normal (el reactor) esta malla está oculta y no pinta nada.
 *
 * Cada punto es parte de un «cometa»: la cabeza y `TRAIL - 1` muestras de su
 * propio pasado (`t - aTrail * lag`). Eso da la estela sin guardar historia, y
 * el mismo truco sirve en los dos estados: en reposo el pasado es largo y
 * espaciado (hilo punteado), en la escucha corto y apretado (estela continua).
 */
import { useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import type { Drive } from './Scene'

/** Cometas con estela, muestras por estela, chispas del centro y polvo suelto. */
const COMETAS = 1000
const TRAIL = 10
const CHISPAS = 450
const POLVO = 600

const vertex = /* glsl */ `
  uniform float uTime;
  uniform float uVis;
  uniform float uEscucha;
  uniform float uLevel;
  uniform float uSize;
  uniform float uPx;
  uniform float uSpan;      // píxeles por unidad de la nube

  attribute vec4 aR;        // cuatro azares fijos por cometa
  attribute float aTrail;   // 0 = cabeza .. 1 = cola
  attribute float aKind;    // 0 cometa, 1 chispa, 2 polvo, 3 destello central

  varying float vAlpha;
  varying float vHeat;
  varying float vAng;
  varying float vAsp;

  #define TAU 6.28318530718

  float hash1(float n) { return fract(sin(n * 12.9898 + 1.0) * 43758.5453); }

  // -- reposo: nueve hilos que se enroscan desde el centro, y chispas -------
  // Todos los cometas de un mismo hilo comparten su curva (la deducen del
  // número de hilo), y se reparten a lo largo de ella: eso es lo que hace que
  // los puntos se lean como un trazo punteado y no como una nube.
  vec2 reposo(vec4 r, float t, float kind, out float edge) {
    edge = 1.0;
    if (kind > 0.5 && kind < 1.5) {
      // Chispas: veintiocho rayos finos desde el centro; titilan en longitud.
      float ray = floor(r.z * 28.0) / 28.0;
      float a = ray * TAU + (r.y - 0.5) * 0.03;
      float rad = pow(r.x, 1.15) * 0.34 * (0.7 + 0.4 * sin(t * 1.7 + ray * 90.0));
      return vec2(cos(a), sin(a)) * rad;
    }
    if (kind > 1.5) {
      // Polvo: deriva lenta sin hilo.
      float a = r.z * TAU + t * (r.y - 0.5) * 0.10 + 0.6 * sin(t * (0.11 + r.w * 0.2) + r.y * 21.0);
      float rad = (0.35 + r.x * 1.25) * (0.60 + 0.40 * sin(t * (0.10 + r.y * 0.16) + r.x * 31.0));
      return vec2(cos(a), sin(a)) * rad;
    }
    float sid = floor(r.x * 9.0);
    float h1 = hash1(sid);
    float h2 = hash1(sid + 17.0);
    float h3 = hash1(sid + 41.0);
    float dir = h1 > 0.5 ? 1.0 : -1.0;
    // Posición sobre el hilo: avanza despacio y vuelve a empezar; los extremos
    // se desvanecen (edge) para que el salto no se vea.
    float u = fract(r.z + t * (0.012 + 0.012 * r.y));
    edge = smoothstep(0.0, 0.10, u) * (1.0 - smoothstep(0.86, 1.0, u));
    float a = sid / 9.0 * TAU + h2 * 0.7
            + dir * (u * 2.4 + 0.9 * sin(u * 5.0 + h3 * TAU)) + t * 0.025 * dir;
    float rad = 0.09 + (0.55 + 0.55 * h3) * pow(u, 0.85);
    rad *= 1.0 + 0.14 * sin(u * 9.0 + h1 * TAU + t * 0.2);
    rad += (r.y - 0.5) * 0.05;
    return vec2(cos(a), sin(a)) * rad;
  }

  // -- escucha: un anillo que gira, más rápido por dentro, con grumos --------
  vec2 anillo(vec4 r, float t, float lvl, float kind, out float clump) {
    float rr = 0.80 + (r.x - 0.5) * 0.26;
    if (kind > 1.5) rr = 0.45 + r.x * 1.0;                  // polvo: dentro y fuera
    if (kind > 0.5 && kind < 1.5) rr = 0.62 + r.x * 0.5;    // chispas: pared interior
    float om = 0.75 + 0.55 * (1.0 - r.x) + r.y * 0.25;
    if (kind > 1.5) om *= 0.35;
    float a = r.z * TAU + t * om;
    clump = 0.5 + 0.5 * sin(a * 2.0 - t * 0.45 + 1.3);
    rr += 0.07 * sin(a * 2.0 - t * 0.7 + r.y * 3.0) + 0.045 * sin(a * 5.0 + t * 1.1 + r.w * 6.0);
    // La voz abolla el anillo: ondas rápidas que crecen con el nivel.
    rr += lvl * 0.09 * sin(a * 7.0 - t * 5.0 + r.w * TAU);
    rr *= 1.0 + lvl * 0.10;
    return vec2(cos(a), sin(a)) * rr;
  }

  void main() {
    float kind = aKind;

    if (kind > 2.5) {
      // Destello central: un solo punto grande y suave. Se apaga al formarse el anillo.
      vec4 mvc = modelViewMatrix * vec4(0.0, 0.0, 0.0, 1.0);
      gl_Position = projectionMatrix * mvc;
      gl_PointSize = uSize * 26.0 * uPx * (1.0 + 0.12 * sin(uTime * 1.3)) * (6.2 / -mvc.z);
      vAlpha = uVis * (0.14 + 0.06 * sin(uTime * 0.9)) * (1.0 - uEscucha * 0.95);
      vHeat = 1.0;
      vAng = 0.0;
      vAsp = 1.0;
      return;
    }

    // Cada punto sale hacia el anillo en su propio momento: la nube se junta
    // como una ola, no como un telón.
    float k = smoothstep(0.0, 1.0,
      clamp(uEscucha * 1.8 - fract(aR.x * 7.31 + aR.z * 3.17) * 0.8, 0.0, 1.0));

    float lag = mix(9.0, 0.95, k);
    float t = uTime - aTrail * lag;

    float clump;
    float edge;
    vec2 pa = reposo(aR, t, kind, edge);
    vec2 pb = anillo(aR, t, uLevel, kind, clump);
    vec2 p = mix(pa, pb, k);

    // En el trayecto se enroscan: sin esto cruzarían en línea recta.
    float sw = sin(k * 3.14159265) * 1.6;
    float c = cos(sw), s = sin(sw);
    p = mat2(c, -s, s, c) * p;

    float z = (aR.w - 0.5) * 0.35 * (1.0 + (1.0 - k) * 1.5);
    vec4 mv = modelViewMatrix * vec4(p, z, 1.0);
    gl_Position = projectionMatrix * mv;

    float spark = (kind > 0.5 && kind < 1.5) ? 1.0 : 0.0;
    float dust = kind > 1.5 ? 1.0 : 0.0;
    float tw = 0.65 + 0.35 * sin(uTime * 2.3 + aR.y * 50.0);
    float fade = pow(1.0 - aTrail, 1.5);
    float base = dust > 0.5 ? 0.34 : (spark > 0.5 ? 1.0 : 0.85);
    float ringGlow = mix(1.0, 0.45 + 0.9 * pow(clump, 2.0), k);
    float borde = mix(edge, 1.0, k);
    vAlpha = uVis * base * fade * tw * ringGlow * borde * (1.0 + uLevel * 0.5);
    vHeat = clamp((1.0 - aTrail) * 0.35 + spark * 0.7
                  + k * pow(clump, 3.0) * 0.9 + uLevel * 0.2 * k, 0.0, 1.0);

    float roundPx = uSize * uPx * (0.5 + 0.7 * (1.0 - aTrail)) * (dust > 0.5 ? 0.6 : 1.0)
                  * (1.0 + uLevel * 0.5) * (6.2 / -mv.z);

    // En el anillo cada muestra se estira a lo largo del giro lo que separa a la
    // siguiente (≈ 0,1 rad de arco): once puntos sueltos se funden en una estela
    // continua. En reposo siguen siendo puntos.
    float streakPx = max(roundPx, 0.085 * uSpan * 1.25 * (6.2 / -mv.z));
    float stretch = dust > 0.5 ? 0.0 : k;
    gl_PointSize = mix(roundPx, streakPx, stretch);
    vAsp = mix(1.0, streakPx / max(roundPx * 0.8, 1.0), stretch);
    vAng = atan(p.y, p.x) + 1.5707963;   // tangente al giro
    vAlpha *= mix(1.0, 0.85, stretch);
  }
`

const fragment = /* glsl */ `
  uniform vec3 uColor;
  uniform vec3 uHot;
  varying float vAlpha;
  varying float vHeat;
  varying float vAng;
  varying float vAsp;

  void main() {
    vec2 d = (gl_PointCoord - 0.5) * 2.0;
    d.y = -d.y;                       // las coordenadas del punto crecen hacia abajo
    float c = cos(vAng), s = sin(vAng);
    vec2 q = vec2(c * d.x + s * d.y, -s * d.x + c * d.y);   // q.x: a lo largo del giro
    float e = q.x * q.x + q.y * q.y * vAsp * vAsp;
    float f = exp(-e * 5.0);
    vec3 col = mix(uColor, uHot, clamp(vHeat, 0.0, 1.0));
    gl_FragColor = vec4(col, vAlpha * f);
  }
`

/**
 * Unidades de la nube → mundo: el anillo de escucha (radio ≈ 0,8) ocupa lo mismo
 * que el del reactor (diámetro = 60 % del lado corto del viewport), así que al
 * pasar de uno a otro la cara no cambia de tamaño.
 */
const ESCALA = 0.3 / 0.8

export function Nube({ drive }: { drive: Drive }) {
  const mat = useRef<THREE.ShaderMaterial>(null)
  const pts = useRef<THREE.Points>(null)
  const fase = useRef(0)
  const viewport = useThree((s) => s.viewport)
  const gl = useThree((s) => s.gl)
  const size = useThree((s) => s.size)

  const { position, aR, aTrail, aKind } = useMemo(() => {
    // En una máquina de dos núcleos (sin GPU que ayude) se pintan menos puntos.
    const e = (navigator.hardwareConcurrency ?? 4) <= 2 ? 0.5 : 1
    const cometas = Math.round(COMETAS * e)
    const chispas = Math.round(CHISPAS * e)
    const polvo = Math.round(POLVO * e)
    const n = cometas * TRAIL + chispas + polvo + 1
    const position = new Float32Array(n * 3)
    const aR = new Float32Array(n * 4)
    const aTrail = new Float32Array(n)
    const aKind = new Float32Array(n)
    let i = 0
    const azar = () => {
      aR[i * 4] = Math.random()
      aR[i * 4 + 1] = Math.random()
      aR[i * 4 + 2] = Math.random()
      aR[i * 4 + 3] = Math.random()
    }
    for (let c = 0; c < cometas; c++) {
      const r = [Math.random(), Math.random(), Math.random(), Math.random()]
      for (let j = 0; j < TRAIL; j++, i++) {
        aR.set(r, i * 4)
        aTrail[i] = j / TRAIL
        aKind[i] = 0
      }
    }
    for (let c = 0; c < chispas; c++, i++) {
      azar()
      aKind[i] = 1
    }
    for (let c = 0; c < polvo; c++, i++) {
      azar()
      aKind[i] = 2
    }
    aKind[i] = 3 // el destello central
    return { position, aR, aTrail, aKind }
  }, [])

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uVis: { value: 0 },
      uEscucha: { value: 0 },
      uLevel: { value: 0 },
      uSize: { value: 3.4 },
      uPx: { value: 1 },
      uSpan: { value: 300 },
      uColor: { value: new THREE.Color('#3fd8ff') },
      uHot: { value: new THREE.Color('#dffbff') },
    }),
    [],
  )

  useFrame((_, dt) => {
    const m = mat.current
    const p = pts.current
    if (!m || !p) return
    const vis = Math.max(drive.reposo, drive.escucha)
    p.visible = drive.visible && vis > 0.003
    if (!p.visible) {
      // Invisible: buen momento para reiniciar el reloj sin que se note el salto
      // (los argumentos de los senos crecen con las horas y pierden precisión).
      if (fase.current > 7200) fase.current = 0
      return
    }
    fase.current += dt
    const u = m.uniforms
    u.uTime.value = fase.current
    u.uVis.value = vis
    u.uEscucha.value = drive.escucha
    u.uLevel.value = drive.level
    u.uPx.value = gl.getPixelRatio()
    ;(u.uColor.value as THREE.Color).lerp(drive.color, Math.min(1, dt * 3))
    ;(u.uHot.value as THREE.Color).lerp(drive.hot, Math.min(1, dt * 3))
    const mundo = ESCALA * Math.min(viewport.width, viewport.height) * drive.scale
    p.scale.setScalar(mundo)
    // Píxeles de pantalla que mide una unidad de la nube: lo usa el shader para
    // saber cuánto estirar cada muestra de la estela.
    u.uSpan.value = mundo * (size.height / viewport.height) * gl.getPixelRatio()
  })

  return (
    <points ref={pts} frustumCulled={false} visible={false}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[position, 3]} />
        <bufferAttribute attach="attributes-aR" args={[aR, 4]} />
        <bufferAttribute attach="attributes-aTrail" args={[aTrail, 1]} />
        <bufferAttribute attach="attributes-aKind" args={[aKind, 1]} />
      </bufferGeometry>
      <shaderMaterial
        ref={mat}
        uniforms={uniforms}
        vertexShader={vertex}
        fragmentShader={fragment}
        transparent
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  )
}
