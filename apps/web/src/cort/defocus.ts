import { setZoom, zoomLimits } from './connection'

/**
 * El gesto de la cámara: **desenfocar y enfocar ajusta el tamaño del orbe**.
 *
 * Acerca los dedos al objetivo y la imagen se vuelve borrosa; retíralos y
 * vuelve a estar nítida. Eso es lo que mide este módulo: la nitidez de lo que ve
 * la cámara, sin modelos de IA y sin dependencias nuevas, con la varianza del
 * Laplaciano — el criterio de enfoque que usa cualquier motor de cámara.
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
  let suave = 0
  let base = 0
  let primer = true

  const id = window.setInterval(() => {
    if (video.readyState < 2) return
    ctx.drawImage(video, 0, 0, W, H)
    const luz = aGris(ctx.getImageData(0, 0, W, H).data, gris)
    const n = nitidez(gris)

    // Suavizado: el sensor tiembla solo, y un orbe que tiembla con el sensor
    // parece roto en vez de vivo.
    suave = primer ? n : suave + (n - suave) * 0.25
    // La base sube en cuanto se ve algo más nítido y baja muy despacio, para que
    // cambiar de escena (girar la silla) no deje el gesto colgado en el máximo.
    base = Math.max(base * 0.995, suave)
    if (base <= 0) base = 1e-6
    primer = false

    const relacion = Math.min(1, Math.max(0, suave / base))
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
