import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { Scene } from './scene/Scene'
import { Effects } from './ui/Effects'
import { Avatar } from './ui/Avatar'
import { Cabecera } from './ui/Cabecera'
import { Respuesta } from './ui/Respuesta'
import { Muelle } from './ui/Muelle'
import { Ventanas } from './ui/Ventanas'
import { Temporizador } from './ui/Temporizador'
import type { IdVentana } from './ui/Ventana'
import { getSnapshot, connect, setOrbeVisible, setZoom, subscribe } from './cort/connection'
import { iniciarVoz } from './cort/voz'
import {
  accionDeTecla,
  conmutar as conmutarDeLista,
  despedir,
  despedirFrente,
  traerAlFrente,
} from './cort/teclas'

/**
 * Las capas de CORT, reestructuradas el 2026-10-11.
 *
 * ```text
 * L0 escena     fondo casi-negro con líneas de barrido        (siempre)
 * L1 cara       reactor/VRM + reloj con su punto de cable     (siempre)
 * L2 subtítulo  la última frase que CORT dijo                 (8 s, se despide sola)
 * L3 ventanas   charla · voz · cámara · cuerpo · sistema ·    (vidrio, móvil, echable
 *               ayuda                                         con ✕ o Esc)
 * L4 muelle     la única fila de botones que existe           (siempre, abajo)
 * L5 efectos    pulso/glitch/temblor — intactos               (mandados por el core)
 * ```
 *
 * Qué cambió respecto a la versión anterior, y por qué:
 * - Había **dos** superficies con chrome propio (el HUD con su asa y «ajustes», y
 *   un `<dialog>` modal de cinco pestañas). Ahora hay **una** primitiva,
 *   `Ventana`, y seis instancias. Reestructurar la base era eso: quitar la
 *   duplicación antes de pintar nada bonito, porque dos formas de hacer lo mismo
 *   se desordenan solas.
 * - El modal no dejaba abrir otra cosa encima y tapaba el reactor. Las ventanas
 *   no son modales: se colocan alrededor de la cara, se pueden tener varias, y la
 *   que se toca pasa al frente (`abiertas` es además el orden de pila).
 * - Los mandos estaban regados (punto de la esquina + botón «ajustes» + teclas).
 *   Ahora son seis accesos en un `Muelle`, con palabra en vez de glifo.
 *
 * Regla madre que se mantiene: **en reposo, tres cosas — el reactor, el reloj y el
 * muelle.** Las ventanas se invocan y se despiden; nada de series aparcadas.
 */
export default function App() {
  useEffect(connect, [])

  /**
   * La voz vive **fuera** de las ventanas (2026-10-12): cuando todo estaba dentro
   * del componente `Voz`, cerrar la ventana desmontaba el componente y apagaba el
   * micrófono justo cuando se quería dejarlo escuchando y mirar la cara. Aquí el
   * estado lo sostiene `cort/voz.ts` y esta línea lo enciende una sola vez; su
   * retorno es lo que lo apaga al desmontar la app.
   */
  useEffect(iniciarVoz, [])

  /**
   * Las ventanas abiertas, **en orden de pila**: el último elemento se pinta
   * delante. Un array en vez de seis booleanos porque «traer al frente» sin
   * reordenar es imposible, y porque así `abiertas.includes(id)` sigue siendo la
   * prueba de «está abierta» sin mantener dos fuentes de verdad.
   */
  const [abiertas, setAbiertas] = useState<IdVentana[]>([])

  /**
   * El cuerpo de CORT: `null` = reactor; un nombre de archivo = proyección con
   * ese atuendo. Al quitarlo vuelve el orbe entero — en los dos casos la
   * conexión con el core no se toca: apagar o encoger la capa visual no apaga
   * a CORT.
   */
  const [atuendo, setAtuendo] = useState<string | null>(null)

  /**
   * Tamaño del `avatar CORT`: 1 es la figura medida en R7; la ventana de cuerpo
   * ofrece 0,72 (compañera de escritorio) y 1,25 (protagonista). Se persigue con
   * lerp dentro de `Vrm`, no se salta.
   */
  const [tamaño, setTamaño] = useState(1)

  /** Contador que sube cada vez que alguien invoca la charla (tap al núcleo o `/`). */
  const [invocar, setInvocar] = useState(0)

  const s = useSyncExternalStore(subscribe, getSnapshot)
  const vistos = useRef(s.msgs.length)

  /** La charla abierta = sus mensajes ya leídos; el badge del muelle se apaga. */
  useEffect(() => {
    if (abiertas.includes('charla')) vistos.current = s.msgs.length
  }, [abiertas, s.msgs.length])

  const sinLeer = Math.max(0, s.msgs.length - vistos.current)

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

  /** Abrir (o traer al frente si ya estaba). Es lo que hace `/` y un toque al núcleo. */
  function abrir(id: IdVentana) {
    setAbiertas((prev) => traerAlFrente(prev, id))
    if (id === 'charla') setInvocar((n) => n + 1)
  }

  /**
   * El muelle: si está abierta, la despide; si no, la abre.
   *
   * Las tres operaciones sobre la pila (`traerAlFrente`, `conmutar`, `despedir`)
   * viven en `cort/teclas.ts` y tienen su prueba. Filtran sin mutar a propósito:
   * si devolvieran el mismo array, React no vería cambio y no pintaría nada.
   */
  function conmutar(id: IdVentana) {
    setAbiertas((prev) => conmutarDeLista(prev, id))
    if (id === 'charla') setInvocar((n) => n + 1)
  }

  function cerrar(id: IdVentana) {
    setAbiertas((prev) => despedir(prev, id))
  }

  /**
   * El teclado de la cara. La decisión de **qué tecla hace qué** ya no vive
   * aquí: está en `cort/teclas.ts`, que es lógica pura y se prueba sin navegador
   * con `make test-web`. Lo único que este efecto aporta es lo que sólo el DOM
   * sabe: si el foco está dentro de un campo, y el `preventDefault`.
   */
  useEffect(() => {
    function teclas(e: KeyboardEvent) {
      const t = e.target as HTMLElement | null
      const escribiendo =
        !!t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)
      const accion = accionDeTecla({
        key: e.key,
        ctrlKey: e.ctrlKey,
        metaKey: e.metaKey,
        altKey: e.altKey,
        escribiendo,
      })
      if (!accion) return
      if (accion.tipo === 'cerrar-frente') {
        // Cerrar la de enfrente, no todas de un golpe: si hubiera tres ventanas
        // abiertas, `Esc` debería vaciar la pantalla y obligar a reabrirlas una
        // por una para seguir trabajando.
        setAbiertas((prev) => despedirFrente(prev))
        return
      }
      if (accion.evitar) e.preventDefault()
      abrir(accion.id)
    }
    window.addEventListener('keydown', teclas)
    return () => window.removeEventListener('keydown', teclas)
  }, [])

  return (
    <>
      <Scene atuendo={atuendo} tamaño={tamaño} onFallo={() => setAtuendo(null)} onInvocar={() => abrir('charla')} />
      <div className="scan" aria-hidden="true" />
      {!esModelo && atuendo && <Avatar nombre={atuendo} onFallo={() => setAtuendo(null)} />}
      <Cabecera />
      {/* El subtítulo no se pinta con la charla abierta: sería la misma frase dos
          veces, una encima de la otra. */}
      <Respuesta visible={!abiertas.includes('charla')} onAbrir={() => abrir('charla')} />
      <Ventanas
        abiertas={abiertas}
        onCerrar={cerrar}
        onTraer={abrir}
        invocar={invocar}
        atuendo={atuendo}
        onAtuendo={setAtuendo}
        tamaño={tamaño}
        onTamaño={setTamaño}
      />
      <Muelle abiertas={abiertas} sinLeer={sinLeer} onConmutar={conmutar} />
      {/* Va siempre montada y no se pinta casi nunca: devuelve `null` mientras no
          haya cuenta atrás. El temporizador no es una ventana que se abre, es un
          número que aparece cuando se pide. */}
      <Temporizador />
      <Effects />
    </>
  )
}
