import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { getSnapshot, send, subscribe } from '../cort/connection'

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
 */

const SR: any = (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition

const IDIOMA = 'es-CO'

/** La mejor voz en español disponible: primero las «Natural», luego la región. */
function elegirVoz(): SpeechSynthesisVoice | null {
  const voces = window.speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith('es'))
  const puntos = (v: SpeechSynthesisVoice) =>
    (/natural/i.test(v.name) ? 0 : /online/i.test(v.name) ? 1 : 3) +
    (/es-(co|mx|us|419)/i.test(v.lang) ? 0 : 1)
  return [...voces].sort((a, b) => puntos(a) - puntos(b))[0] ?? null
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

export function Voz() {
  const s = useSyncExternalStore(subscribe, getSnapshot)
  const [habla, setHabla] = useState(false)
  const [escucha, setEscucha] = useState(false)
  const [oyendo, setOyendo] = useState('')
  const [error, setError] = useState<string | null>(null)

  // Refs: los manejadores del navegador viven más que cada render y tienen que
  // ver siempre el valor de ahora, no el de cuando se crearon.
  const hablaRef = useRef(false)
  const escuchaRef = useRef(false)
  const hablandoRef = useRef(false)
  const esperandoRef = useRef(false)
  const recRef = useRef<any>(null)
  const leidos = useRef(s.msgs.length)

  function arrancarReconocimiento() {
    if (!SR || !escuchaRef.current || hablandoRef.current || esperandoRef.current) return
    if (recRef.current) return
    const rec = new SR()
    rec.lang = IDIOMA
    rec.continuous = false
    rec.interimResults = true
    rec.onresult = (e: any) => {
      let texto = ''
      let final = false
      for (let i = e.resultIndex; i < e.results.length; i++) {
        texto += e.results[i][0].transcript
        if (e.results[i].isFinal) final = true
      }
      setOyendo(texto)
      if (final && texto.trim()) {
        esperandoRef.current = true
        setOyendo('')
        send(texto.trim())
      }
    }
    rec.onerror = (e: any) => {
      // `no-speech` y `aborted` no son fallos: es silencio, o somos nosotros.
      if (e.error === 'no-speech' || e.error === 'aborted') return
      setError(explicarErrorVoz(e.error))
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed' || e.error === 'audio-capture') {
        apagarEscucha()
      }
    }
    rec.onend = () => {
      recRef.current = null
      setOyendo('')
      // Un respiro antes de reabrir: reabrir en el mismo tick da `aborted`.
      if (escuchaRef.current) window.setTimeout(arrancarReconocimiento, 350)
    }
    recRef.current = rec
    try {
      rec.start()
    } catch {
      recRef.current = null
    }
  }

  function pararReconocimiento() {
    const rec = recRef.current
    recRef.current = null
    if (rec) {
      rec.onend = null
      try {
        rec.abort()
      } catch {
        /* ya estaba parado */
      }
    }
    setOyendo('')
  }

  function apagarEscucha() {
    escuchaRef.current = false
    setEscucha(false)
    pararReconocimiento()
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
      u.onstart = () => {
        hablandoRef.current = true
        // Mientras CORT habla, el micrófono se cierra: no debe oírse a sí mismo.
        pararReconocimiento()
      }
      u.onend = u.onerror = () => {
        if (window.speechSynthesis.speaking || window.speechSynthesis.pending) return
        hablandoRef.current = false
        esperandoRef.current = false
        if (escuchaRef.current) window.setTimeout(arrancarReconocimiento, 350)
      }
      window.speechSynthesis.speak(u)
    })
  }

  // Lo que CORT dice llega por el snapshot: se lee sólo lo nuevo, nunca el
  // historial que ya estaba cuando se encendió la voz.
  useEffect(() => {
    const nuevos = s.msgs.slice(leidos.current)
    leidos.current = s.msgs.length
    if (nuevos.some((m) => m.from === 'cort')) {
      esperandoRef.current = false
    }
    if (hablaRef.current) {
      nuevos
        .filter((m) => m.from === 'cort' && !m.text.startsWith('→'))
        .forEach((m) => hablar(m.text))
    }
    // Si no habla en voz alta, la conversación sigue: reabre el micrófono.
    if (!hablaRef.current && escuchaRef.current && !esperandoRef.current) arrancarReconocimiento()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s.msgs])

  // Si el core se cae mientras se espera respuesta, no se queda esperando.
  useEffect(() => {
    if (!s.online) esperandoRef.current = false
  }, [s.online])

  useEffect(() => {
    // Las voces cargan tarde en Chrome/Edge: tocar la lista la despierta.
    window.speechSynthesis?.getVoices()
    return () => {
      escuchaRef.current = false
      pararReconocimiento()
      window.speechSynthesis?.cancel()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function alternarHabla() {
    setError(null)
    const nuevo = !hablaRef.current
    if (!nuevo && escuchaRef.current) apagarEscucha()
    hablaRef.current = nuevo
    setHabla(nuevo)
    leidos.current = getSnapshot().msgs.length
    if (nuevo) {
      // Pulsar es el gesto que el navegador exige antes de dejar hablar; la
      // frase de prueba confirma además que hay salida de audio.
      hablar('Voz activada.')
    } else {
      window.speechSynthesis.cancel()
      hablandoRef.current = false
    }
  }

  function alternarEscucha() {
    setError(null)
    if (escuchaRef.current) {
      apagarEscucha()
      return
    }
    if (!SR) {
      setError('este navegador no tiene reconocimiento de voz: usa Microsoft Edge o Google Chrome')
      return
    }
    if (!hablaRef.current) {
      hablaRef.current = true
      setHabla(true)
    }
    leidos.current = getSnapshot().msgs.length
    escuchaRef.current = true
    esperandoRef.current = false
    setEscucha(true)
    arrancarReconocimiento()
  }

  const sinHabla = typeof window.speechSynthesis === 'undefined'

  return (
    <div className="gesto">
      <button
        type="button"
        className={`gesto-btn ${habla ? 'on' : ''}`}
        onClick={alternarHabla}
        aria-pressed={habla}
        disabled={sinHabla}
      >
        {habla ? 'voz activa' : 'que me hable'}
      </button>
      <button
        type="button"
        className={`gesto-btn ${escucha ? 'on' : ''}`}
        onClick={alternarEscucha}
        aria-pressed={escucha}
      >
        {escucha ? 'escuchando…' : 'hablarle'}
      </button>
      {escucha && oyendo && <span className="gesto-medida">{oyendo}</span>}
      {!habla && !escucha && !error && (
        <p className="gesto-nota">
          <b>que me hable</b> lee en voz alta lo que CORT responde. <b>hablarle</b> abre el micrófono y
          conversa: el navegador pide permiso la primera vez, y el reconocimiento necesita internet.
        </p>
      )}
      {error && <p className="gesto-aviso">{error}</p>}
    </div>
  )
}
