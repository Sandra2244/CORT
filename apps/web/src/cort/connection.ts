import * as THREE from 'three'
import { DEFAULT_OUTFIT, SPIN, THINKING_HOT, palette, type Outfit } from './palette'

export type Msg = { from: 'user' | 'cort'; text: string }

/** Un archivo de atuendo en el disco de la usuaria (`CORT_AVATAR_DIR`). */
export type Avatar = { nombre: string; mime: string; bytes: number }

/** Puntuación, no estado: ver el protocolo en docs/ARCHITECTURE.md. */
export type UiEffect = 'glitch' | 'pulse' | 'scan' | 'shake' | 'flash'

/**
 * Los cinco se validan contra una lista en vez de fiarse del core. Un `kind`
 * escrito mal no debe colgar la capa de efectos entera: simplemente no dispara.
 */
const EFFECTS = new Set<string>(['glitch', 'pulse', 'scan', 'shake', 'flash'])

/**
 * Telemetría del core: lo que CORT puede afirmar de sí mismo. `brain` es null
 * hasta que el LLM interviene, y `ollama` lo es hasta el primer intento — un
 * panel que invente "eco" antes de haberlo probado está mintiendo.
 */
export type Status = {
  memories: number
  keep: number
  brain: string | null
  ollama: boolean | null
  actions: boolean
  /**
   * Si CORT tiene permiso de hablar primero (`CORT_INITIATIVE`). Se pinta como
   * lo que es: un hecho del proceso, medido en el core, no una decoración del
   * panel. Se lee con `!== false` porque su valor por defecto es «encendida», y
   * un marco viejo sin el campo no debe hacer creer que está apagada.
   */
  iniciativa: boolean
}

/**
 * Se valida campo a campo en vez de colgar el objeto tal cual: un número que
 * llegara como texto se metería en el panel y lo siguiente que se vería sería
 * `12 / 200` convertido en `NaN`. Aquí lo desconocido vuelve a su valor neutro.
 */
function readStatus(m: any): Status {
  const num = (v: unknown, fallback: number) => (Number.isFinite(v) ? (v as number) : fallback)
  return {
    memories: num(m.memories, 0),
    keep: num(m.keep, 0),
    brain: typeof m.brain === 'string' ? m.brain : null,
    ollama: m.ollama === true || m.ollama === false ? m.ollama : null,
    actions: Boolean(m.actions),
    iniciativa: m.iniciativa !== false,
  }
}

/**
 * Cuenta atrás en marcha, o `null`. **No hay reloj en el navegador**: este
 * objeto se escribe sólo cuando llega un cuadro del core, así que en reposo no
 * hay ningún `setInterval` contando, ni un nodo que repintar, ni memoria viva.
 * Y si el core se cae, la cuenta se apaga con él — un temporizador que sigue
 * contando sin servidor es un reloj que miente.
 */
export type Crono = { restante: number; total: number; estado: 'corre' | 'termina' }

export type Snapshot = {
  online: boolean
  outfit: Outfit
  thinking: boolean
  msgs: Msg[]
  status: Status | null
  /**
   * Clima medido por el core, o `null` si no hay ciudad configurada. Se pinta
   * sólo con datos reales: un `0°` inventado en el cabezal sería el mismo error
   * que el panel de telemetría evita con `brain: null` hasta que alguien hable.
   */
  clima: { city: string; temp_c: number } | null
  /**
   * Catálogo de atuendos en disco, o `null` si aún no se ha pedido. Se pide sólo
   * cuando la usuaria abre el selector: mientras no lo abra, el core no lee su
   * carpeta, y un listado en cada conexión sería curiosear por defecto.
   */
  avatars: Avatar[] | null
  /**
   * `at` es la marca de tiempo del mensaje, y existe sólo para que repetir el
   * mismo efecto vuelva a dispararlo: sin una clave que cambie, React no
   * remontaría el nodo y la animación CSS no tendría de dónde arrancar.
   */
  effect: { kind: UiEffect; at: number } | null
  crono: Crono | null
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
  status: null,
  clima: null,
  avatars: null,
  effect: null,
  crono: null,
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
  /**
   * Tamaño del reactor que pide la usuaria, 1 = el de siempre. Vive aquí y no
   * en estado de React por el mismo motivo que el color: la escena lo persigue
   * con lerp cada frame, así que el orbe **crece** en vez de saltar. Y mover el
   * slider no reconcilia el HUD 60 veces por segundo en una máquina de 2 núcleos.
   */
  zoom: 1,
  /**
   * Si el reactor se pinta. Con el avatar delante el orbe estorba — dos focos de
   * luz en la misma pantalla se apagan el uno al otro —, pero **el core no se
   * entera**: apagar la capa visual no apaga a CORT, que sigue escuchando por el
   * WebSocket con la misma conexión abierta.
   */
  visible: true,
}

/** El margen que el shader aguanta sin que el anillo se salga del cuadro. */
const ZOOM_MIN = 0.5
const ZOOM_MAX = 2

export function setZoom(factor: number) {
  if (!Number.isFinite(factor)) return target.zoom
  target.zoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, factor))
  return target.zoom
}

export const zoomLimits = { min: ZOOM_MIN, max: ZOOM_MAX }

/** Mostrar o esconder el reactor sin tocar la conexión ni el estado del core. */
export function setOrbeVisible(visible: boolean) {
  target.visible = visible
}

// El core y la página viven en puertos distintos (8765 y 8780), así que una
// imagen de atuendo necesita el origen completo. `location.hostname` en vez de
// 127.0.0.1 a secas: es el mismo truco del WebSocket, y es lo que hace que al
// abrir CORT desde el teléfono con `--lan` las miniaturas salgan también.
const ORIGEN_CORE = `${location.protocol === 'https:' ? 'https' : 'http'}://${location.hostname || '127.0.0.1'}:8765`

export function avatarUrl(nombre: string) {
  return `${ORIGEN_CORE}/avatars/${encodeURIComponent(nombre)}`
}

// El core escucha en 127.0.0.1; si se abre la web desde otro equipo de la red
// (`cort.py --lan`), `location.hostname` ya apunta a esa máquina y no hace falta
// reescribir la URL. El `wss` no es una promesa de HTTPS: es para que, si algún
// día la interfaz se sirve con certificado, el navegador no bloquee el cable por
// mezclar protocolos con un error que no se entiende.
const WS_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.hostname || '127.0.0.1'}:8765/ws`

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
    // `status: null` porque los números eran de un core que ya no contesta:
    // dejarlos en pantalla sería seguir afirmando "12 recuerdos" sin tenerlo
    // comprobado. Al reconectar, el core vuelve a enviarlos.
    set({ online: false, status: null, crono: null })
    timer = window.setTimeout(open, 3000)
  }
  s.onmessage = (e) => {
    const m = JSON.parse(e.data)
    if (m.type === 'state') applyState(m)
    if (m.type === 'status') set({ status: readStatus(m) })
    // El saludo es por conexión, y el log sobrevive a las reconexiones: sin el
    // `msgs.length === 0` cada reintento del WebSocket añadiría un «Hola, soy
    // CORT.» nuevo a una conversación que ya está en curso.
    if (m.type === 'greeting' && snapshot.msgs.length === 0)
      set({ msgs: [{ from: 'cort', text: m.text }] })
    if (m.type === 'assistant_message') set({ msgs: [...snapshot.msgs, { from: 'cort', text: m.text }] })
    // `proactive` es lo mismo dicho por su cuenta: viaja separado porque el core
    // decide cuándo (iniciativa, regla determinista, sin LLM) y para que alguien
    // pueda apagarlo con `CORT_INITIATIVE=0` sin tocar cómo se pinta un mensaje.
    if (m.type === 'proactive' && typeof m.text === 'string')
      set({ msgs: [...snapshot.msgs, { from: 'cort', text: m.text }] })
    if (m.type === 'intent') set({ msgs: [...snapshot.msgs, { from: 'cort', text: `→ ${m.action}` }] })
    if (m.type === 'effect' && EFFECTS.has(m.kind)) set({ effect: { kind: m.kind, at: Date.now() } })
    if (m.type === 'avatars')
      set({ avatars: Array.isArray(m.items) ? m.items.filter((i: any) => typeof i?.nombre === 'string') : [] })
    // El temporizador viaja como cuadro propio y no como mensaje de texto: lo
    // que pinta es un número que baja, no una frase. `cancela` borra el nodo,
    // `termina` lo deja en cero para que la interfaz pueda avisar y apagarse.
    if (m.type === 'timer') {
      const restante = Number.isFinite(m.restante) ? m.restante : 0
      if (m.estado === 'cancela') set({ crono: null })
      else set({ crono: { restante, total: Number.isFinite(m.total) ? m.total : restante, estado: m.estado === 'termina' ? 'termina' : 'corre' } })
    }
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

function applyState(m: { outfit?: string; thinking?: boolean; city?: string; temp_c?: number }) {
  const outfit = (m.outfit ?? DEFAULT_OUTFIT) as Outfit
  const tint = palette[outfit] ?? palette[DEFAULT_OUTFIT]
  const thinking = Boolean(m.thinking)
  target.color.set(tint.core)
  target.hot.set(thinking ? THINKING_HOT : tint.hot)
  target.spin = thinking ? SPIN.thinking : SPIN.idle
  target.open = 1.6
  // `Number.isFinite` y no `if (m.temp_c)`: 0 °C es un clima real, y con la
  // comprobación a secas el HUD lo pintaría como "sin ciudad".
  const clima = Number.isFinite(m.temp_c) && typeof m.city === 'string'
    ? { city: m.city, temp_c: m.temp_c as number }
    : null
  set({ online: true, outfit, thinking, clima })
}

export function send(text: string) {
  if (!sock || sock.readyState !== WebSocket.OPEN) return
  sock.send(JSON.stringify({ type: 'user_message', text }))
  set({ msgs: [...snapshot.msgs, { from: 'user', text }] })
}

/** Pedir al core la lista de atuendos que hay en disco. Va por el cable abierto. */
export function pedirAvatares() {
  if (!sock || sock.readyState !== WebSocket.OPEN) return
  sock.send(JSON.stringify({ type: 'list_avatars' }))
}
