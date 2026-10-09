import { setZoom, zoomLimits } from './connection'
import { OneEuro } from '../lib/oneEuro'

/**
 * El gesto de la cámara: **desenfocar y enfocar ajusta el tamaño del orbe**.
 *
 * Acerca los dedos al objetivo y la imagen se vuelve borrosa; retíralos y
 * vuelve a estar nítida. Eso es lo que mide este módulo: la nitidez de lo que ve
 * la cámara, sin modelos de IA y sin dependencias nuevas, con la varianza del
 * Laplaciano — el criterio de enfoque que usa cualquier motor de cámara.
 *
 * El suavizado que hay encima no es un factor fijo: es un filtro 1€
 * (`lib/oneEuro.ts`, transplantado de adewaskar/JARVIS con MIT) que suaviza a
 * fondo mientras la mano está quieta y casi nada cuando se mueve. Un factor fijo
 * no puede hacer las dos cosas a la vez; éste elige según la velocidad de la
 * señal.
 *
 * Por qué así: MediaPipe y cualquier red de manos cargan modelos de megas, y esta
 * máquina tiene ~286 MiB disponibles. Éste análisis cuesta 3072 píxeles por
 * muestra a 5 muestras por segundo.
 *
 * La privacidad no es un detalle: la cámara **no se abre sola**. La activa la
 * usuaria desde el panel, y al apagarla se detienen las pistas del stream, que es
 * lo que apaga el LED del portátil. Ningún cuadro sale de este archivo: se
 * analiza en memoria y se tira.
 */

/** Tamaño del recuadro que se analiza. 64×48 es suficiente para medir nitidez. */
const W = 64
const H = 48

/** ms entre muestras. A 60 fps la máquina no aguantaría analizar cada frame. */
const INTERVALO = 200

/**
 * Los dos mandos del filtro 1€ (ver `lib/oneEuro.ts`), elegidos con el criterio
 * que publica el propio papel: primero se deja `beta` en 0 y se baja el corte
 * hasta que el reposo no tiembla; después se sube `beta` hasta que el gesto
 * rápido no se queda atrás.
 *
 * La barrida se midió, no se intuyó: el filtro se alimentó con el peor caso que
 * le espera — ruido blanco de ±0,04 sobre una señal quieta (lo que hace el sensor
 * de la webcam) y una rampa de 0,5 a 1 en un segundo (lo que hace una mano) — y
 * se comparó con el suavizado fijo que había antes:
 *
 *   fijo 0,25 (el anterior)     temblor en reposo 0,045 · llega al 95 % en 1,8 s
 *   corte 0,08 · beta 1,0       temblor en reposo 0,036 · llega al 95 % en 1,0 s
 *
 * Gana en las dos cosas, y las dos celdas cercanas explican por qué ésas son las
 * cifras: con `beta` 0 y el mismo corte el temblor baja a 0,024 pero la rampa
 * tarda 4,8 s en llegar, que es un orbe que sigue a los dedos cuando la mano ya
 * está retirada. Con `beta` 2,0 vuela (0,9 s) pero deja pasar el temblor entero
 * (0,042): un filtro que estima la velocidad confunde el ruido de alta frecuencia
 * con un gesto, y una webcam temblando es exactamente ruido de alta frecuencia.
 *
 * Lo que queda **sin medir aquí**: el valor con una cámara real delante. Hay
 * `/dev/video0`, pero comprobarlo pide una ventana de navegador visible y esta
 * sesión no la tuvo.
 */
const CORTE_REPOSO = 0.08
const APERTURA = 1.0

/** `relacion` es nitidez / mejor-nitidez recortada a 0..1: lo que se pinta. */
export type Muestra = { nitidez: number; luz: number; relacion: number; zoom: number }

/**
 * Gris de BT.601 sobre los píxeles que llegan del canvas.
 *
 * Los coeficientes no son ceremonia: sin ellos una cara iluminada por una
 * pantalla azul se leería como oscuridad y la nitidez saldría por las nubes.
 */
export function aGris(d: Uint8ClampedArray, out: Float32Array): number {
  let total = 0
  for (let i = 0, p = 0; i < out.length; i++, p += 4) {
    const v = (0.299 * d[p] + 0.587 * d[p + 1] + 0.114 * d[p + 2]) / 255
    out[i] = v
    total += v
  }
  return total / out.length
}

/**
 * Varianza del Laplaciano: dónde hay borde, hay enfoque.
 *
 * Una imagen desenfocada tiene diferencias segundas casi planas, así que la
 * varianza se desploma. Es la misma señal que usa la cámara para decidir cuándo
 * ya está enfocada.
 */
export function nitidez(g: Float32Array, w = W, h = H): number {
  let sum = 0
  let sum2 = 0
  let n = 0
  for (let y = 1; y < h - 1; y++) {
    for (let x = 1; x < w - 1; x++) {
      const i = y * w + x
      const lap = 4 * g[i] - g[i - 1] - g[i + 1] - g[i - w] - g[i + w]
      sum += lap
      sum2 += lap * lap
      n++
    }
  }
  if (n === 0) return 0
  const media = sum / n
  return Math.max(0, sum2 / n - media * media)
}

/**
 * Nitidez medida → tamaño del orbe.
 *
 * Se compara con la **mejor nitidez vista** (`base`) y no con un número
 * absoluto: una webcam de portátil no enfoca igual contra una pared que contra
 * una ventana, y un umbral fijo haría que el gesto dependiera de la habitación.
 * Con la imagen nítida el reactor queda en su tamaño natural (1); al desenfocarse
 * se encoge hasta el mínimo del shader, y vuelve a crecer solo cuando los dedos
 * se retiran.
 */
export function escalaDesdeNitidez(medida: number, base: number): number {
  if (!Number.isFinite(medida) || !Number.isFinite(base) || base <= 0) return 1
  const r = Math.min(1, Math.max(0, medida / base))
  return zoomLimits.min + (1 - zoomLimits.min) * r
}

/**
 * Abre la cámara y devuelve la función que la cierra.
 *
 * Rechaza si el navegador no da permiso o si no hay contexto seguro: en el móvil
 * por `http://192.168.x.x` el navegador bloquea la cámara aunque la red funcione,
 * y eso no se disimula con un valor neutro — se muestra en el panel.
 */
export async function iniciarCamara(alMuestra: (m: Muestra) => void): Promise<() => void> {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: 160 }, height: { ideal: 120 }, frameRate: { ideal: 15 } },
    audio: false,
  })

  const video = document.createElement('video')
  video.srcObject = stream
  video.muted = true
  video.playsInline = true
  await video.play()

  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  if (!ctx) {
    stream.getTracks().forEach((t) => t.stop())
    throw new Error('sin canvas 2D: no se puede analizar la cámara')
  }

  const gris = new Float32Array(W * H)
  const filtro = new OneEuro(CORTE_REPOSO, APERTURA)
  let base = 0

  const id = window.setInterval(() => {
    if (video.readyState < 2) return
    ctx.drawImage(video, 0, 0, W, H)
    const luz = aGris(ctx.getImageData(0, 0, W, H).data, gris)
    const n = nitidez(gris)

    // La base sube en cuanto se ve algo más nítido y baja muy despacio, para que
    // cambiar de escena (girar la silla) no deje el gesto colgado en el máximo.
    base = Math.max(base * 0.995, n)
    if (base <= 0) base = 1e-6

    // Se suaviza la **relación** (0..1), no la varianza cruda: `beta` trabaja con
    // la velocidad de la señal, y esa palabra sólo significa algo en una
    // magnitud acotada. Con varianzas de centenares la velocidad estimada es tan
    // grande que el corte no se cierra nunca y el filtro no suaviza nada.
    const cruda = Math.min(1, Math.max(0, n / base))
    // Segundo, no milisegundos: es la unidad que espera `filter`.
    const relacion = filtro.filter(cruda, performance.now() / 1000)

    // Devuelta a unidades de varianza para que `escalaDesdeNitidez` siga
    // comparando lo mismo contra lo mismo. El primer cuadro vale 1 porque sale de
    // su propia base: el orbe nace en su tamaño natural.
    const suave = relacion * base
    const zoom = escalaDesdeNitidez(suave, base)
    setZoom(zoom)
    alMuestra({ nitidez: suave, luz, relacion, zoom })
  }, INTERVALO)

  return () => {
    window.clearInterval(id)
    stream.getTracks().forEach((t) => t.stop())
    video.srcObject = null
  }
}
