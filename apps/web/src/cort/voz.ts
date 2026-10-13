import { getSnapshot, send, subscribe, target, tocarActividad } from './connection'
// La frase de activación vive en su propio módulo puro (`activacion.ts`) para poder
// probarse sin navegador. Aquí se usa.
import { buscarActivacion } from './activacion'
// La agenda de labios (`labios.ts`) también es pura y probada sin navegador; aquí
// sólo se le pasa el texto que se va a decir y se la realinea con el aviso de
// palabra, cuando el navegador se digna mandarlo.
import { alinear, empezar, parar } from './labios'

/**
 * Voz de CORT, hecha con lo que ya trae el navegador: nada que instalar y nada
 * que gaste RAM del core.
 *
 *  - Hablar: `speechSynthesis` (las voces de Windows; en Edge, además, las
 *    «Natural» como Salome o Dalia, que suenan mucho mejor).
 *  - Escuchar: `SpeechRecognition`. En Edge y Chrome el reconocimiento lo hace un
 *    servicio en línea, así que necesita internet y el permiso de micrófono.
 *
 * El micrófono es una conversación: escucha, manda lo dicho a CORT, calla
 * mientras CORT responde (si no, se oiría a sí mismo) y vuelve a escuchar.
 *
 * Por qué es un módulo y no un componente: esto antes vivía dentro de `Voz.tsx`,
 * que sólo existe mientras el modal está abierto en su pestaña. Al cerrar el
 * modal el componente se desmontaba y **apagaba el micrófono** — justo cuando la
 * usuaria quería dejarlo escuchando y mirar la cara. Aquí el estado vive aparte
 * y `Voz.tsx` es sólo el par de botones que lo manejan. Además deja que la
 * escena sepa cuándo CORT escucha o habla (`target.escucha`, `target.habla`,
 * `target.nivel`) sin pasar por React.
 */

const SR: any = (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition

const IDIOMA = 'es-CO'

export const hayReconocimiento = Boolean(SR)
export const hayHabla = typeof window.speechSynthesis !== 'undefined'

export type EstadoVoz = {
  /** «que me hable»: CORT lee sus respuestas en voz alta. */
  habla: boolean
  /** «hablarle»: el micrófono está en conversación. */
  escucha: boolean
  /** Lo que el reconocimiento va entendiendo, antes de enviarlo. */
  oyendo: string
  error: string | null
  /** «OK CORT»: el micrófono vigila esperando la frase de activación. */
  vigilia: boolean
  /** Se dijo «OK CORT» y se está esperando la orden. */
  turno: boolean
  /** Voces en español que el navegador tiene, la mejor primero. */
  voces: string[]
  /** La que se usa ahora (la elegida, o la mejor si no se eligió ninguna). */
  vozNombre: string
  /** Velocidad y tono de la voz: 1 es lo normal. */
  velocidad: number
  tono: number
}

// -- Ajustes de la voz (se recuerdan entre sesiones) --------------------------
const CLAVE = 'cort.voz'
type Ajustes = { voz: string | null; velocidad: number; tono: number }
// 0,95: un poco más pausada que lo normal; a velocidad 1 las voces de Windows
// atropellan las frases. El tono sólo lo respetan las voces locales de Windows;
// las «Natural» en línea lo ignoran.
const AJUSTES_BASE: Ajustes = { voz: null, velocidad: 0.95, tono: 1 }

function leerAjustes(): Ajustes {
  try {
    const a = JSON.parse(localStorage.getItem(CLAVE) ?? 'null')
    if (a && typeof a === 'object') {
      return {
        voz: typeof a.voz === 'string' ? a.voz : null,
        velocidad: Math.min(1.5, Math.max(0.6, Number(a.velocidad) || AJUSTES_BASE.velocidad)),
        tono: Math.min(1.5, Math.max(0.5, Number(a.tono) || AJUSTES_BASE.tono)),
      }
    }
  } catch {
    /* almacenamiento bloqueado o dañado: se usan los valores base */
  }
  return { ...AJUSTES_BASE }
}
let ajustes: Ajustes = leerAjustes()
function guardarAjustes() {
  try {
    localStorage.setItem(CLAVE, JSON.stringify(ajustes))
  } catch {
    /* sin almacenamiento: la elección vale sólo para esta sesión */
  }
}

let estado: EstadoVoz = {
  habla: false,
  escucha: false,
  oyendo: '',
  error: null,
  vigilia: false,
  turno: false,
  voces: [],
  vozNombre: '',
  velocidad: ajustes.velocidad,
  tono: ajustes.tono,
}
const oyentes = new Set<() => void>()

function poner(p: Partial<EstadoVoz>) {
  estado = { ...estado, ...p }
  oyentes.forEach((l) => l())
}

export const suscribirVoz = (l: () => void) => {
  oyentes.add(l)
  return () => void oyentes.delete(l)
}
export const estadoVoz = () => estado

// Estado interno: lo que los manejadores del navegador necesitan ver siempre al
// día, sin esperar a un render.
let hablaOn = false
let escuchaOn = false
let hablando = false
let esperando = false
let rec: any = null
/** Vigilia por frase de activación (estilo Alexa) y el turno que abre al oírla. */
let vigiliaOn = false
let turnoVigilia = false
let turnoTimer: number | undefined
let leidos = 0
let ultimosMsgs = getSnapshot().msgs

/**
 * Lo que la escena pinta: la nube de escucha sólo se forma cuando de verdad se
 * está escuchando. Con el micrófono encendido pero CORT hablando o pensando, la
 * cara vuelve al reactor — y así se ve quién tiene la palabra.
 */
function sincronizarEscena() {
  target.escucha = escuchaOn && !hablando && !esperando
  target.habla = hablando
  if (!target.escucha) target.oyendo = false
  tocarActividad()
}

/**
 * Voces masculinas serenas, en orden de preferencia: las «Natural» de Edge que
 * mejor suenan en español. Si ninguna está, se cae a la lógica de siempre.
 */
const PREFERIDAS = ['jorge', 'gonzalo', 'alvaro', 'alonso', 'tomas', 'lorenzo', 'raul', 'pablo']

function vocesEspanol(): SpeechSynthesisVoice[] {
  const todas = window.speechSynthesis?.getVoices() ?? []
  const es = todas.filter((v) => v.lang.toLowerCase().startsWith('es'))
  const puntos = (v: SpeechSynthesisVoice) => {
    const n = v.name.toLowerCase()
    const pref = PREFERIDAS.findIndex((p) => n.includes(p))
    return (
      (/natural/i.test(v.name) ? 0 : /online/i.test(v.name) ? 20 : 40) +
      (pref >= 0 ? pref : 10) +
      (/es-(co|mx|us|419)/i.test(v.lang) ? 0 : 1)
    )
  }
  return [...es].sort((a, b) => puntos(a) - puntos(b))
}

/** La elegida por la usuaria si existe; si no, la mejor disponible. */
function elegirVoz(): SpeechSynthesisVoice | null {
  const voces = vocesEspanol()
  return voces.find((v) => v.name === ajustes.voz) ?? voces[0] ?? null
}

/** Las voces cargan tarde (y a veces cambian): se refresca la lista del estado. */
function refrescarVoces() {
  const voces = vocesEspanol()
  poner({
    voces: voces.map((v) => v.name),
    vozNombre: elegirVoz()?.name ?? '',
  })
}

/** Lo que se lee en voz alta: sin marcas de markdown ni emojis. */
function limpiar(texto: string): string {
  return texto
    .replace(/[*_`#>~]/g, '')
    .replace(/\p{Extended_Pictographic}/gu, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function explicarErrorVoz(codigo: string): string {
  switch (codigo) {
    case 'not-allowed':
    case 'service-not-allowed':
      return 'el navegador negó el micrófono — se concede en el candado de la dirección → Permisos → Micrófono'
    case 'audio-capture':
      return 'no se encontró ningún micrófono'
    case 'network':
      return 'el reconocimiento de voz del navegador necesita internet'
    default:
      return `el reconocimiento de voz falló (${codigo})`
  }
}

/** Un pitido corto que confirma «te oí»: no depende de la voz ni del idioma. */
let audio: AudioContext | null = null
function pitido() {
  try {
    audio ??= new AudioContext()
    void audio.resume()
    const t0 = audio.currentTime
    const o = audio.createOscillator()
    const g = audio.createGain()
    o.type = 'sine'
    o.frequency.setValueAtTime(620, t0)
    o.frequency.exponentialRampToValueAtTime(980, t0 + 0.12)
    g.gain.setValueAtTime(0.0001, t0)
    g.gain.exponentialRampToValueAtTime(0.18, t0 + 0.03)
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.22)
    o.connect(g).connect(audio.destination)
    o.start(t0)
    o.stop(t0 + 0.25)
  } catch {
    /* sin audio: el anillo ya avisa */
  }
}

function arrancarReconocimiento() {
  if (!SR || hablando || esperando) return
  // Dos usos del mismo reconocedor: la conversación (una frase por vez) y la
  // vigilia (continuo, sólo busca la frase de activación).
  const enVigilia = vigiliaOn && !escuchaOn
  if (!escuchaOn && !enVigilia) return
  if (rec) return
  const r = new SR()
  r.lang = IDIOMA
  r.continuous = enVigilia
  r.interimResults = true
  // Alguien empieza y termina de hablar: la nube lo siente antes de que haya texto.
  r.onspeechstart = () => {
    if (enVigilia) return // en vigilia nadie está «hablándole» todavía: no se agita nada
    // Empezó a decir la orden: se le da tiempo de terminarla.
    if (turnoVigilia) {
      window.clearTimeout(turnoTimer)
      turnoTimer = window.setTimeout(terminarTurno, 20000)
    }
    target.oyendo = true
    target.nivel = Math.max(target.nivel, 0.7)
    tocarActividad()
  }
  r.onspeechend = () => {
    target.oyendo = false
  }
  r.onresult = (e: any) => {
    if (enVigilia) {
      // Sólo cuentan los resultados finales: «ok» a medias no es una orden.
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (!e.results[i].isFinal) continue
        const resto = buscarActivacion(e.results[i][0].transcript)
        if (resto !== null) {
          despertar(resto)
          return
        }
      }
      return
    }
    let texto = ''
    let final = false
    for (let i = e.resultIndex; i < e.results.length; i++) {
      texto += e.results[i][0].transcript
      if (e.results[i].isFinal) final = true
    }
    // Cada resultado parcial es una palabra nueva: un golpe de luz en el anillo.
    target.nivel = Math.max(target.nivel, 0.9)
    tocarActividad()
    poner({ oyendo: texto })
    if (final && texto.trim()) {
      esperando = true
      sincronizarEscena()
      poner({ oyendo: '' })
      send(texto.trim())
      // En un turno de vigilia, si la respuesta no llega (core caído, nada que
      // decir en voz alta) no se queda el micrófono esperando para siempre.
      if (turnoVigilia) {
        window.clearTimeout(turnoTimer)
        turnoTimer = window.setTimeout(terminarTurno, 45000)
      }
    }
  }
  r.onerror = (e: any) => {
    // `no-speech` y `aborted` no son fallos: es silencio, o somos nosotros.
    if (e.error === 'no-speech' || e.error === 'aborted') return
    poner({ error: explicarErrorVoz(e.error) })
    if (
      e.error === 'not-allowed' ||
      e.error === 'service-not-allowed' ||
      e.error === 'audio-capture' ||
      e.error === 'network'
    ) {
      // Sin permiso, sin micrófono o sin internet no hay nada que reintentar cada
      // 350 ms: se apaga todo y el aviso explica por qué.
      apagarTodo()
    }
  }
  r.onend = () => {
    rec = null
    target.oyendo = false
    poner({ oyendo: '' })
    // Un respiro antes de reabrir: reabrir en el mismo tick da `aborted`.
    if (escuchaOn || vigiliaOn) window.setTimeout(arrancarReconocimiento, 350)
  }
  rec = r
  try {
    r.start()
  } catch {
    rec = null
  }
}

function pararReconocimiento() {
  const r = rec
  rec = null
  if (r) {
    r.onend = null
    try {
      r.abort()
    } catch {
      /* ya estaba parado */
    }
  }
  target.oyendo = false
  poner({ oyendo: '' })
}

function apagarEscucha() {
  escuchaOn = false
  poner({ escucha: false })
  pararReconocimiento()
  sincronizarEscena()
}

/** Se oyó la frase de activación: pitido, anillo y a esperar la orden. */
function despertar(resto: string) {
  pararReconocimiento()
  pitido()
  turnoVigilia = true
  escuchaOn = true
  esperando = false
  poner({ turno: true, oyendo: '' })
  window.clearTimeout(turnoTimer)
  if (resto) {
    // «OK CORT, pon música» en una sola frase: la orden ya viene dicha.
    esperando = true
    sincronizarEscena()
    send(resto)
    turnoTimer = window.setTimeout(terminarTurno, 45000)
  } else {
    sincronizarEscena()
    // Medio segundo: que el pitido no entre al micrófono como si fuera la orden.
    window.setTimeout(arrancarReconocimiento, 500)
    turnoTimer = window.setTimeout(terminarTurno, 9000)
  }
}

/** Fin de la orden (respondida, o que nunca llegó): vuelve a vigilar. */
function terminarTurno() {
  window.clearTimeout(turnoTimer)
  if (!turnoVigilia) return
  turnoVigilia = false
  escuchaOn = false
  esperando = false
  pararReconocimiento()
  poner({ turno: false })
  sincronizarEscena()
  if (vigiliaOn) window.setTimeout(arrancarReconocimiento, 350)
}

function apagarVigilia() {
  vigiliaOn = false
  window.clearTimeout(turnoTimer)
  if (turnoVigilia) {
    turnoVigilia = false
    escuchaOn = false
    esperando = false
  }
  poner({ vigilia: false, turno: false })
  pararReconocimiento()
  sincronizarEscena()
}

/** Para los fallos que no tienen arreglo reintentando: todo el micrófono, apagado. */
function apagarTodo() {
  apagarVigilia()
  apagarEscucha()
}

function hablar(texto: string) {
  const limpio = limpiar(texto)
  if (!limpio) return
  const frases = limpio.match(/[^.!?…]+[.!?…]*/g) ?? [limpio]
  const voz = elegirVoz()
  frases.forEach((frase) => {
    const u = new SpeechSynthesisUtterance(frase.trim())
    u.lang = voz?.lang ?? IDIOMA
    if (voz) u.voice = voz
    u.rate = ajustes.velocidad
    u.pitch = ajustes.tono
    u.onstart = () => {
      hablando = true
      // La boca se agenda con la frase que **empieza** a sonar, no con el texto
      // entero: `speechSynthesis` lanza una frase por `Utterance` y la cola puede
      // tardar. Función 27.
      empezar(frase)
      // Mientras CORT habla, el micrófono se cierra: no debe oírse a sí mismo.
      pararReconocimiento()
      sincronizarEscena()
    }
    // Cada palabra pronunciada sacude el reactor. Las voces «Natural» en línea no
    // siempre mandan este aviso: la escena tiene su propio pulso de respaldo
    // mientras `target.habla` esté encendido.
    u.onboundary = (ev: SpeechSynthesisEvent) => {
      target.nivel = Math.max(target.nivel, 0.85)
      // Y cuando el aviso llega con la posición de la palabra, se realinea la
      // agenda: se tira lo que ya se dijo y se programa el resto desde ahí. Si
      // nunca llega, la agenda original sigue valiendo — es el motivo de calcularla
      // del texto y no del audio, que este navegador tampoco deja mirar.
      if (typeof ev?.charIndex === 'number' && ev.charIndex > 0) {
        alinear((frase ?? '').slice(ev.charIndex))
      }
    }
    u.onend = u.onerror = () => {
      if (window.speechSynthesis.speaking || window.speechSynthesis.pending) return
      hablando = false
      esperando = false
      // Boca cerrada: si no, la última sílaba se quedaría abierta para siempre
      // hasta el siguiente mensaje.
      parar()
      sincronizarEscena()
      if (turnoVigilia) {
        terminarTurno()
        return
      }
      if (escuchaOn || vigiliaOn) window.setTimeout(arrancarReconocimiento, 350)
    }
    window.speechSynthesis.speak(u)
  })
}

/** Lo que CORT dice llega por el snapshot: se lee sólo lo nuevo, nunca el historial. */
function alCambiar() {
  const s = getSnapshot()
  // Si el core se cae mientras se espera respuesta, no se queda esperando.
  if (!s.online && esperando) {
    esperando = false
    sincronizarEscena()
  }
  if (s.msgs === ultimosMsgs) return
  ultimosMsgs = s.msgs
  const nuevos = s.msgs.slice(leidos)
  leidos = s.msgs.length
  if (nuevos.some((m) => m.from === 'cort')) {
    esperando = false
    sincronizarEscena()
  }
  if (hablaOn) {
    nuevos
      .filter((m) => m.from === 'cort' && !m.text.startsWith('→'))
      .forEach((m) => hablar(m.text))
  }
  // Si no habla en voz alta, la conversación sigue: reabre el micrófono.
  if (!hablaOn && escuchaOn && !esperando) arrancarReconocimiento()
}

/** Se llama una vez al montar la app; devuelve la función que lo deshace. */
export function iniciarVoz() {
  leidos = getSnapshot().msgs.length
  ultimosMsgs = getSnapshot().msgs
  // Las voces cargan tarde en Chrome/Edge: tocar la lista la despierta, y el
  // aviso `voiceschanged` dice cuándo ya están.
  refrescarVoces()
  window.speechSynthesis?.addEventListener?.('voiceschanged', refrescarVoces)
  const baja = subscribe(alCambiar)
  return () => {
    baja()
    window.speechSynthesis?.removeEventListener?.('voiceschanged', refrescarVoces)
    vigiliaOn = false
    turnoVigilia = false
    window.clearTimeout(turnoTimer)
    escuchaOn = false
    hablaOn = false
    hablando = false
    esperando = false
    pararReconocimiento()
    // La boca se apaga con la voz: `parar()` deja la agenda vacía, así que la
    // escena vuelve a los labios cerrados en el cuadro siguiente.
    parar()
    window.speechSynthesis?.cancel()
    poner({ habla: false, escucha: false, vigilia: false, turno: false })
    sincronizarEscena()
  }
}

export function alternarHabla() {
  poner({ error: null })
  const nuevo = !hablaOn
  if (!nuevo && vigiliaOn) apagarVigilia()
  if (!nuevo && escuchaOn) apagarEscucha()
  hablaOn = nuevo
  poner({ habla: nuevo })
  leidos = getSnapshot().msgs.length
  if (nuevo) {
    // Pulsar es el gesto que el navegador exige antes de dejar hablar; la
    // frase de prueba confirma además que hay salida de audio.
    hablar('Voz activada.')
  } else {
    window.speechSynthesis.cancel()
    hablando = false
    parar()
    sincronizarEscena()
  }
}

export function alternarEscucha() {
  poner({ error: null })
  if (escuchaOn) {
    apagarEscucha()
    return
  }
  if (!SR) {
    poner({ error: 'este navegador no tiene reconocimiento de voz: usa Microsoft Edge o Google Chrome' })
    return
  }
  if (vigiliaOn) apagarVigilia() // una cosa o la otra: o conversa, o vigila
  if (!hablaOn) {
    hablaOn = true
    poner({ habla: true })
  }
  leidos = getSnapshot().msgs.length
  escuchaOn = true
  esperando = false
  poner({ escucha: true })
  sincronizarEscena()
  arrancarReconocimiento()
}

/**
 * «OK CORT»: deja el micrófono vigilando y sólo se abre a una orden cuando oye
 * la frase de activación. Al terminar la orden, vuelve a vigilar.
 *
 * Lo que esto NO es: una palabra de activación local. El reconocimiento de voz
 * del navegador no tiene ese modo, así que vigilar es **reconocimiento continuo**:
 * el audio sale al servicio del navegador (Google en Chrome, Microsoft en Edge)
 * todo el rato que esté encendido. Por eso es un interruptor y no el estado de
 * fábrica, y por eso hace falta la pestaña abierta e internet.
 */
export function alternarVigilia() {
  poner({ error: null })
  if (vigiliaOn) {
    apagarVigilia()
    return
  }
  if (!SR) {
    poner({ error: 'este navegador no tiene reconocimiento de voz: usa Microsoft Edge o Google Chrome' })
    return
  }
  if (escuchaOn) apagarEscucha() // la conversación continua y la vigilia no conviven
  if (!hablaOn) {
    hablaOn = true
    poner({ habla: true })
  }
  leidos = getSnapshot().msgs.length
  vigiliaOn = true
  poner({ vigilia: true })
  // El pitido necesita un gesto para existir: este clic lo es. Se crea ya, mudo.
  try {
    audio ??= new AudioContext()
    void audio.resume()
  } catch {
    /* sin audio */
  }
  tocarActividad()
  arrancarReconocimiento()
}

/** Cambia de voz y la prueba en el acto: oírla es la única forma de elegir bien. */
export function elegirVozPorNombre(nombre: string) {
  ajustes = { ...ajustes, voz: nombre }
  guardarAjustes()
  refrescarVoces()
  probarVoz()
}

export function ajustarVoz(cambio: { velocidad?: number; tono?: number }) {
  ajustes = {
    ...ajustes,
    velocidad: cambio.velocidad ?? ajustes.velocidad,
    tono: cambio.tono ?? ajustes.tono,
  }
  guardarAjustes()
  poner({ velocidad: ajustes.velocidad, tono: ajustes.tono })
}

/** Una frase de muestra con el tono que se busca: serena, cortés, sin prisa. */
export function probarVoz() {
  if (!hayHabla) return
  window.speechSynthesis.cancel()
  hablar('Buenas tardes. Todos los sistemas funcionan con normalidad.')
}
