import { useEffect, useState } from 'react'
import { Scene } from './scene/Scene'
import { Hud } from './ui/Hud'
import { Effects } from './ui/Effects'
import { Bandeja } from './ui/Bandeja'
import { Avatar } from './ui/Avatar'
import { Cabecera } from './ui/Cabecera'
import { Respuesta } from './ui/Respuesta'
import { Panel, type Pestana } from './ui/Panel'
import { Temporizador } from './ui/Temporizador'
import { connect, setOrbeVisible, setZoom } from './cort/connection'

/**
 * Las capas de CORT (rediseño de docs/REDESIGN-UI.md, ejecutado 2026-10-10).
 *
 * ```text
 * L0 escena     fondo casi-negro con líneas de barrido       (siempre)
 * L1 cara       reactor/VRM + reloj con su punto de cable    (siempre)
 * L2 voz        subtítulo de la última respuesta             (8 s, auto-cierre)
 * L2+ bandeja   registro completo + entrada                  (esquina / tap / Ctrl+/)
 * L3 modal      voz · cámara · atuendos · sistema · ayuda    (desde la bandeja)
 * L4 resultados temporizador arriba a la izquierda; la       (sólo cuando existen)
 *               captura y el clima viajan por el subtítulo
 * L5 efectos    pulso/glitch/scan — intactos                 (mandados por el core)
 * ```
 *
 * Regla madre: **en reposo, tres cosas — el reactor, el reloj y la esquina.**
 * Todo lo demás se invoca y se despide, que es la gramática común de las siete
 * referencias en video.
 */
export default function App() {
  useEffect(connect, [])

  /** La bandeja (registro + entrada) arranca guardada: la cara es el reactor. */
  const [abierto, setAbierto] = useState(false)

  /** El modal de herramientas: `null` = no existe en pantalla. */
  const [pestana, setPestana] = useState<Pestana | null>(null)

  /**
   * El cuerpo de CORT: `null` = reactor; un nombre de archivo = proyección con
   * ese atuendo. Al quitarlo vuelve el orbe entero — en los dos casos la
   * conexión con el core no se toca: apagar o encoger la capa visual no apaga
   * a CORT.
   */
  const [atuendo, setAtuendo] = useState<string | null>(null)

  /**
   * Tamaño del `avatar CORT`: 1 es la figura medida en R7; la pestaña de
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
    setPestana(null)
    setAbierto(true)
    setInvocar((n) => n + 1)
  }

  useEffect(() => {
    function teclas(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        // El `Esc` jerárquico: primero despide el modal, y sólo si no hay modal
        // guarda la bandeja. Cerrar las dos superficies de un golpe obligaría a
        // reabrir todo para seguir leyendo.
        if (pestana) setPestana(null)
        else setAbierto(false)
        return
      }
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault()
        invocarEntrada()
        return
      }
      // El teclado es de primera clase, como prometía `v0.10` («se llega con tres
      // manos»): `/` invoca la entrada y `1`–`5` saltan a las cinco pestañas del
      // modal. Con la mano ya en el teclado no se busca un botón de 46 px. La
      // guarda del `target` es para que escribir '/' o un número DENTRO del campo
      // siga siendo escribir, no invocar.
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const t = e.target as HTMLElement | null
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
      if (e.key === '/') {
        e.preventDefault()
        invocarEntrada()
        return
      }
      if (e.key === '?') {
        setPestana('ayuda')
        return
      }
      const PESTANAS_TECLA = ['voz', 'camara', 'atuendos', 'sistema', 'ayuda'] as const
      const n = Number(e.key)
      if (n >= 1 && n <= PESTANAS_TECLA.length) setPestana(PESTANAS_TECLA[n - 1])
    }
    window.addEventListener('keydown', teclas)
    return () => window.removeEventListener('keydown', teclas)
  }, [pestana])

  return (
    <>
      <Scene atuendo={atuendo} tamaño={tamaño} onFallo={() => setAtuendo(null)} onInvocar={invocarEntrada} />
      <div className="scan" aria-hidden="true" />
      {!esModelo && atuendo && <Avatar nombre={atuendo} onFallo={() => setAtuendo(null)} />}
      <Cabecera />
      {/* El subtítulo no se pinta con la bandeja abierta: sería la misma frase
          dos veces, una encima de la otra. */}
      <Respuesta visible={!abierto} onAbrir={() => setAbierto(true)} />
      <Hud abierto={abierto} invocar={invocar} onAbrirPanel={(p) => setPestana(p ?? 'voz')} />
      <Bandeja abierto={abierto} onToggle={() => setAbierto((v) => !v)} />
      {pestana && (
        <Panel
          pestana={pestana}
          onPestana={setPestana}
          onCerrar={() => setPestana(null)}
          atuendo={atuendo}
          onAtuendo={setAtuendo}
          tamaño={tamaño}
          onTamaño={setTamaño}
        />
      )}
      {/* Va siempre montada y no se pinta casi nunca: devuelve `null` mientras no
          haya cuenta atrás. El temporizador no es un panel que se abre, es un
          número que aparece cuando se pide. */}
      <Temporizador />
      <Effects />
    </>
  )
}
