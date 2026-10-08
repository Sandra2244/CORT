import * as THREE from 'three'
import { DEFAULT_OUTFIT, SPIN, THINKING_HOT, palette, type Outfit } from './palette'

export type Msg = { from: 'user' | 'cort'; text: string }

/** Puntuación, no estado: ver el protocolo en docs/ARCHITECTURE.md. */
export type UiEffect = 'glitch' | 'pulse' | 'scan' | 'shake' | 'flash'

/**
 * Los cinco se validan contra una lista en vez de fiarse del core. Un `kind`
 * escrito mal no debe colgar la capa de efectos entera: simplemente no dispara.
 */
const EFFECTS = new Set<string>(['glitch', 'pulse', 'scan', 'shake', 'flash'])

export type Snapshot = {
  online: boolean
  outfit: Outfit
  thinking: boolean
  msgs: Msg[]
  /**
   * `at` es la marca de tiempo del mensaje, y existe sólo para que repetir el
   * mismo efecto vuelva a dispararlo: sin una clave que cambie, React no
   * remontaría el nodo y la animación CSS no tendría de dónde arrancar.
   */
  effect: { kind: UiEffect; at: number } | null
}

/**
 * Estado visible para React. Se reemplaza entero en cada cambio porque
 * `useSyncExternalStore` compara por referencia: mutarlo in situ haría que la
 * interfaz no se repintara.
 */
let snapshot: Snapshot = {
  online: false,
  outfit: DEFAULT_OUTFIT,
  thinking: false,
  msgs: [],
  effect: null,
}
const listeners = new Set<() => void>()

function set(patch: Partial<Snapshot>) {
  snapshot = { ...snapshot, ...patch }
  listeners.forEach((l) => l())
}

export const subscribe = (l: () => void) => {
  listeners.add(l)
  return () => void listeners.delete(l)
}

export const getSnapshot = () => snapshot

/**
 * Metas crudas de la escena. El WebSocket escribe aquí y `Scene` las persigue
 * con lerp cada frame: si el orbe saltara de color en cada mensaje, un cambio
 * de atuendo se vería como un parpadeo en vez de como una respiración.
 */
export const target = {
  color: new THREE.Color(palette[DEFAULT_OUTFIT].core),
  hot: new THREE.Color(palette[DEFAULT_OUTFIT].hot),
  spin: SPIN.idle,
  open: 0,
}

// El core escucha en 127.0.0.1; si se abre la web desde otro equipo de la red,
// location.hostname ya apunta a esa máquina y no hace falta reescribir la URL.
const WS_URL = `ws://${location.hostname || '127.0.0.1'}:8765/ws`

let sock: WebSocket | null = null
let timer: number | undefined

function open() {
  const s = new WebSocket(WS_URL)
  sock = s
  s.onopen = () => set({ online: true })
  // El reintento sólo vale para la conexión que sigue siendo la actual. Sin
  // esta comprobación, cerrar a propósito (StrictMode, o una reconexión
  // nueva) programa otro intento tres segundos después y el cliente acaba
  // con dos sockets abiertos a la vez: el core saluda una vez por conexión,
  // así que cada mensaje del log se ve duplicado.
  s.onclose = () => {
    if (sock !== s) return
    set({ online: false })
    timer = window.setTimeout(open, 3000)
  }
  s.onmessage = (e) => {
    const m = JSON.parse(e.data)
    if (m.type === 'state') applyState(m)
    if (m.type === 'assistant_message') set({ msgs: [...snapshot.msgs, { from: 'cort', text: m.text }] })
    if (m.type === 'intent') set({ msgs: [...snapshot.msgs, { from: 'cort', text: `→ ${m.action}` }] })
    if (m.type === 'effect' && EFFECTS.has(m.kind)) set({ effect: { kind: m.kind, at: Date.now() } })
  }
}

export function connect() {
  open()
  return () => {
    if (timer) clearTimeout(timer)
    timer = undefined
    const s = sock
    sock = null
    s?.close()
    set({ online: false })
  }
}

function applyState(m: { outfit?: string; thinking?: boolean }) {
  const outfit = (m.outfit ?? DEFAULT_OUTFIT) as Outfit
  const tint = palette[outfit] ?? palette[DEFAULT_OUTFIT]
  const thinking = Boolean(m.thinking)
  target.color.set(tint.core)
  target.hot.set(thinking ? THINKING_HOT : tint.hot)
  target.spin = thinking ? SPIN.thinking : SPIN.idle
  target.open = 1.6
  set({ online: true, outfit, thinking })
}

export function send(text: string) {
  if (!sock || sock.readyState !== WebSocket.OPEN) return
  sock.send(JSON.stringify({ type: 'user_message', text }))
  set({ msgs: [...snapshot.msgs, { from: 'user', text }] })
}
