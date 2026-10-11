import { useEffect, useState } from 'react'
import { Scene } from './scene/Scene'
import { Hud } from './ui/Hud'
import { Effects } from './ui/Effects'
import { Bandeja } from './ui/Bandeja'
import { Avatar } from './ui/Avatar'
import { Cabecera } from './ui/Cabecera'
import { Respuesta } from './ui/Respuesta'
import { Ventanas } from './ui/Ventanas'
import { Temporizador } from './ui/Temporizador'
import { abrir, alternar, cerrar, cerrarTodo, esc, reposo, seccionPorTecla, siguienteVidrio } from './cort/ventanas'
import { connect, setOrbeVisible, setZoom } from './cort/connection'

/**
 * Las capas de CORT (rediseño por capas de docs/REDESIGN-UI.md, ejecutado
 * 2026-10-10; la capa L3 pasó de modal a **ventanas de vidrio** con N1 de
 * docs/REDESIGN-NUCLEO.md).
 *
 * ```text
 * L0 escena     fondo casi-negro con líneas de barrido       (siempre)
 * L1 cara       reactor/VRM + reloj arrastrable con su punto (siempre)
 * L2 voz        subtítulo de la última respuesta             (8 s, auto-cierre)
 * L2+ bandeja   registro completo + entrada                  (esquina / tap / Ctrl+/)
 * L3 ventanas   voz · cámara · atuendos · sistema · ayuda    (teclas 1–5, apilables)
 * L4 resultados temporizador arriba a la izquierda; la       (sólo cuando existen)
 *               captura y el clima viajan por el subtítulo
 * L5 efectos    pulso/glitch/scan — intactos                 (mandados por el core)
 * ```
 *
 * Regla madre: **en reposo, tres cosas — el reactor, el reloj y la esquina.**
 * Lo demás se invoca y se despide; ahora además se mueve: la pila de ventanas
 * vive en `cort/ventanas.ts` (pura, probada con `make test-web`) y el vidrio
 * regula cuánto reactor se ve a través de ella.
 */
export default function App() {
  useEffect(connect, [])

  /** La bandeja (registro + entrada) arranca guardada: la cara es el reactor. */
  const [abierto, setAbierto] = useState(false)

  /** La pila de ventanas de vidrio: en reposo vacía, la cara manda. */
  const [ventanas, setVentanas] = useState(reposo)

  /**
   * El cuerpo de CORT: `null` = reactor; un nombre de archivo = proyección con
   * ese atuendo. Al quitarlo vuelve el orbe entero — en los dos casos la
   * conexión con el core no se toca: apagar o encoger la capa visual no apaga
   * a CORT.
   */
  const [atuendo, setAtuendo] = useState<string | null>(null)

  /**
   * Tamaño del `avatar CORT`: 1 es la figura medida en R7; la ventana de
   * atuendos ofrece 0,72 (compañera de escritorio) y 1,25 (protagonista).
   * Se persigue con lerp dentro de `Vrm`, no se salta.
   */
  const [tamaño, setTamaño] = useState(1)

  /** Contador que sube cada vez que alguien invoca la entrada (tap al núcleo o `Ctrl+/`). */
  const [invocar, setInvocar] = useState(0)

  /**
   * Un `.vrm` se proyecta dentro del canvas del reactor; una imagen se pinta
   * encima como capa HTML. Dos mundos distintos para dos formas de cuerpo.
   */
  const esModelo = atuendo !== null && /\.vrm$/i.test(atuendo)

  /**
   * R7 — con cuerpo 3D el reactor **no se apaga**: se encoge a zócalo (55 %)
   * y el VRM se para encima, como el holograma pequeño de las referencias v3/v5
   * pero invertido: aquí el cuerpo es la cara y el anillo su pedestal. Con un
   * sprite 2D el orbe sí se apaga — la figura llena la pantalla y dos focos de
   * luz se borran el uno al otro (medido el 2026-10-08).
   */
  useEffect(() => {
    setOrbeVisible(esModelo || atuendo === null)
    setZoom(esModelo ? 0.55 : 1)
  }, [atuendo, esModelo])

  function invocarEntrada() {
    // Invocar la entrada limpia la pila: quien invoca quiere escribir, no
    // apartar ventanas de en medio. Las teclas 1–5 las devuelven.
    setVentanas(cerrarTodo)
    setAbierto(true)
    setInvocar((n) => n + 1)
  }

  useEffect(() => {
    function teclas(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        // El `Esc` jerárquico de `v0.11`, con ventanas apiladas: primero
        // despide la ventana del frente; `esc` devuelve `null` cuando ya no
        // queda ninguna, y sólo entonces el Esc guarda la bandeja.
        const tras = esc(ventanas)
        if (tras) setVentanas(tras)
        else setAbierto(false)
        return
      }
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault()
        invocarEntrada()
        return
      }
      // El teclado es de primera clase, como prometía `v0.10` («se llega con tres
      // manos»): `/` invoca la entrada y `1`–`5` abren y ocultan SU ventana —
      // cada tecla alterna su cristal, pueden convivir varias a la vez. Con la
      // mano ya en el teclado no se busca un botón de 46 px. La guarda del
      // `target` es para que escribir '/' o un número DENTRO del campo siga
      // siendo escribir, no invocar.
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const t = e.target as HTMLElement | null
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
      if (e.key === '/') {
        e.preventDefault()
        invocarEntrada()
        return
      }
      if (e.key === '?') {
        setVentanas((v) => abrir(v, 'ayuda'))
        return
      }
      const id = seccionPorTecla(e.key)
      if (id) setVentanas((v) => alternar(v, id))
    }
    window.addEventListener('keydown', teclas)
    return () => window.removeEventListener('keydown', teclas)
  }, [ventanas])

  return (
    <>
      <Scene atuendo={atuendo} tamaño={tamaño} onFallo={() => setAtuendo(null)} onInvocar={invocarEntrada} />
      <div className="scan" aria-hidden="true" />
      {!esModelo && atuendo && <Avatar nombre={atuendo} onFallo={() => setAtuendo(null)} />}
      <Cabecera />
      {/* El subtítulo no se pinta con la bandeja abierta: sería la misma frase
          dos veces, una encima de la otra. */}
      <Respuesta visible={!abierto} onAbrir={() => setAbierto(true)} />
      <Hud
        abierto={abierto}
        invocar={invocar}
        onAbrirVentana={(id) => setVentanas((v) => abrir(v, id ?? 'voz'))}
      />
      <Bandeja abierto={abierto} onToggle={() => setAbierto((v) => !v)} />
      <Ventanas
        estado={ventanas}
        onTraer={(id) => setVentanas((v) => abrir(v, id))}
        onOcultar={(id) => setVentanas((v) => cerrar(v, id))}
        onVidrio={() => setVentanas((v) => ({ pilas: v.pilas, vidrio: siguienteVidrio(v.vidrio) }))}
        atuendo={atuendo}
        onAtuendo={setAtuendo}
        tamaño={tamaño}
        onTamaño={setTamaño}
      />
      {/* Va siempre montada y no se pinta casi nunca: devuelve `null` mientras no
          haya cuenta atrás. El temporizador no es un panel que se abre, es un
          número que aparece cuando se pide. */}
      <Temporizador />
      <Effects />
    </>
  )
}
