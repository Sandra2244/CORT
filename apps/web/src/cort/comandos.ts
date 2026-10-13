/**
 * Los comandos que se escriben en la charla y **levantan su ventana**, módulo puro
 * y sin DOM (función 80).
 *
 * Por qué existe este archivo. Las cuatro frases estaban dentro de `ui/Charla.tsx`
 * como una lista de `RegExp` pegada al componente, y eso costaba dos cosas: no se
 * podían probar (regla 3 de `AGENTS.md` —un `.tsx` con `useSyncExternalStore` no
 * se importa en Node) y no aparecían en ningún sitio: quien no sabe que «activa la
 * cámara» existe no lo escribe, y la ayuda tenía que copiarlas a mano para
 * enseñarlas. Aquí la lista vive **una vez**: el componente la obedece y la ventana
 * «ayuda» la enumera desde ella.
 *
 * Qué es un mando local y qué no. Se levanta una ventana cuando la frase **pide
 * esa superficie**, no cuando la menciona: «haz una captura con la cámara» no debe
 * abrir la ventana de cámara, y por eso los tres primeros van con su verbo
 * (`activa`, `abre`, `cambia`, `proyecta`). El cuarto llevaba la regla al revés:
 * `/(?:estado|diagnóstico|sistema)/i` casaba con **cualquier** frase que mencionara
 * alguna de las tres palabras, así que «¿en qué estado está el volumen?» levantaba
 * la ventana de sistema sin que nadie la pidiera. Aquí va anclada: la palabra abre
 * la frase, o la precede un verbo de enseñar. Es el criterio que ella pidió el
 * 2026-10-10 —«no sobrecargues de paneles»— aplicado a una ventana que se abría
 * sola.
 *
 * El permiso verdadero NO está aquí. «activa la cámara» abre la ventana; el botón
 * de dentro es el que pregunta al navegador, y el navegador sólo da la cámara en
 * origen seguro. Este módulo lleva a la usuaria al sitio, no finge el permiso.
 */

import type { IdVentana } from './teclas'

export type MandoLocal = {
  /** La frase que lo enciende, tal cual se escribe. */
  re: RegExp
  /** La ventana que levanta. */
  id: IdVentana
  /** Lo que se lee en la ayuda: un ejemplo real, no el patrón. */
  ejemplo: string
}

/**
 * La lista, en el orden en que se mira. `find` devuelve el primero que casa, así
 * que un mando nuevo se añade **debajo** de los que ya existan si su frase puede
 * confundirse con otra.
 */
export const MANDOS: readonly MandoLocal[] = [
  {
    re: /(?:activa|abre|enciende|prende)\s+(?:la\s+|mi\s+)?c[áa]mara/i,
    id: 'camara',
    ejemplo: 'activa la cámara',
  },
  {
    re: /(?:activa|abre)\s+(?:el\s+|la\s+)?(?:micr[oó]fono|voz)/i,
    id: 'voz',
    ejemplo: 'activa el micrófono',
  },
  {
    re: /(?:cambia|pon|muestra|elige|proyecta)\s+(?:el\s+|mi\s+)?atuendo/i,
    id: 'cuerpo',
    ejemplo: 'cambia el atuendo',
  },
  {
    // Dos formas, y sólo dos: que la palabra **abra** la frase («estado»,
    // «cort, diagnóstico») o que la preceda un verbo de enseñar («muestra el
    // sistema»). Cualquier otra cosa que mencione la palabra es conversación.
    re: /(?:^(?:cort[:.,\s]*)?(?:estado|diagn[oó]stico|sistema)\b)|(?:\b(?:muestra|mu[ée]strame|ens[ée][ñm]ame|dime|revisa|verifica|abre|activa)\s+(?:el\s+|la\s+|mi\s+)?(?:estado|diagn[oó]stico|sistema)\b)/i,
    id: 'sistema',
    ejemplo: 'estado',
  },
]

/**
 * A qué ventana pertenece una frase escrita en la charla; `null` si no es ninguna
 * de las cuatro y el texto sólo viaja al core.
 */
export function ventanaPorComando(texto: string): IdVentana | null {
  const limpio = texto.trim()
  if (!limpio) return null
  const mando = MANDOS.find(({ re }) => re.test(limpio))
  return mando ? mando.id : null
}
