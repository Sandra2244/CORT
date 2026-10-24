/* ===== MANDOS de CORT — la capa PURA =====

   Aquí vive lo que CORT **entiende** y a **dónde** lo manda, sin tocar el DOM,
   sin `window.CortNative` y sin `fetch`. Es puro a propósito por dos motivos:

   1. Se puede probar con `node` en el portátil de la dueña
      (`scripts/prueba-mandos.mjs`), que es como se cazan los acentos, el punto
      que añade el reconocedor y las frases que no debían casar. Con el código
      metido dentro de `hud.js` nada de esto era comprobable: `hud.js` necesita
      pantalla, y en el teléfono no hay consola donde ver el fallo.
   2. `hud.js` deja de tener seis `if` sueltos con sus seis llamadas al puente.
      Un mando nuevo es una fila de esta tabla, y la fila se prueba sola.

   ── Por qué existe este archivo ahora (la ronda F12) ──
   La dueña reportó «le digo *pausa* y no lo hace». La cadena real eran **tres**
   fallos distintos, y los tres vivían en la lógica de casar la frase:

   · El micrófono se cerraba mientras sonaba música, así que «pausa» nunca llegó
     a oírse. (Ese freno está en `ui/js/voice.js` y se arregla con el ducking de
     `Oido.kt`.)
   · El reconocedor escribe «Pausa.» **con punto**, y la cara casaba contra
     `/^pausa$/`: con el punto delante no casaba, la frase se mandaba a
     `POST /api/command`, el APK la cortaba con 501 y ella oía «El núcleo de CORT
     no respondió». Se arregla con `paraCasar()`.
   · Los seis mandos de transporte estaban dentro de `if (e && e.vivo)`, o sea
     sólo cuando suena el reproductor **de CORT**. Con Spotify o YouTube puestos
     no había camino posible. Se arregla con `tecla` → `CortNative.teclaMedia()`
     (la tecla va al `MediaSession` del aparato, que es lo mismo que llega del
     auricular). */

/** El punto final del reconocedor, y el resto de la puntuación que no deja casar. */
export function paraCasar(texto) {
  return String(texto ?? '')
    .replace(/\s+/g, ' ')                                  // «Pausa  la   música»
    .replace(/^[\s"'«¿¡]+|[\s"'.,;:!?»«¡¿]+$/g, '')        // «Pausa.» → «Pausa»
    .trim();
}

/**
 * Los mandos de transporte. Cada fila dice cuatro cosas:
 *
 * `casa(m)`  la frase ya normalizada; `m` es minúscula sólo para los textos, las
 *            expresiones llevan su propia `/i`.
 * `met`      el método del puente propio (`Reproductor` de CORT).
 * `tecla`    la que se manda al reproductor del aparato cuando NO es el nuestro.
 *            `null` = sólo existe en nuestro reproductor (el fotograma).
 * `dijo`/`habla` lo que pinta en pantalla y lo que dice la boca, distintos porque
 *            hay mandos que se responden por escrito únicamente.
 */
export const TRANSPORTE = [
  { id: 'pausa', met: 'musicaPausa', tecla: 'pausa', habla: 'Pausa',
    casa: m => (/^(pausa|para|det[eé]n|stop)\b/i.test(m) && /m[uú]sica|audio|sonido|eso/i.test(m))
            || /^pausa$/i.test(m),
    dijo: e => `Pauso «${e && e.pista ? e.pista.titulo : 'la canción'}». Di «sigue».`,
    ajeno: 'Mando «pausa» al reproductor que suena en el aparato: no es mío, así que si no se detiene, ábrelo y dalo tú.' },

  { id: 'sigue', met: 'musicaPlay', tecla: 'play', habla: 'Continuando',
    casa: m => /^(sigue|contin[uú]a|reanuda|play)\b/i.test(m),
    dijo: () => 'Sigo con la música.',
    ajeno: 'Mando «sigue» al reproductor del aparato (no es el mío).' },

  { id: 'siguiente', met: 'musicaSiguiente', tecla: 'siguiente', habla: 'La siguiente',
    /* Las tres vías con las que la dueña lo pide y nada más: «la siguiente»,
       «pon otra», «¿qué sigue?». La última va anclada al principio y al final a
       propósito: «explícame qué sigue después» es una pregunta, no un mando, y
       con la expresión suelta de antes saltaba a la canción siguiente. */
    casa: m => /^(?:la |pon la |ve a la |pon |sigue con la )?siguiente\b/i.test(m)
            || /^pon otra\b/i.test(m) || /^otra canci[oó]n\b/i.test(m)
            || /^qu[eé] sigue\??$/i.test(m),
    dijo: () => 'Pasando a la siguiente.',
    ajeno: 'Mando «siguiente» al reproductor del aparato (no es el mío).' },

  { id: 'anterior', met: 'musicaAnterior', tecla: 'anterior', habla: '',
    casa: m => /^(?:la |pon la |ve a la |pon |volt[aá]r?date a la )?anterior\b/i.test(m)
            || /^la de antes\b/i.test(m),
    dijo: () => 'Voy a la anterior.',
    ajeno: 'Mando «anterior» al reproductor del aparato (no es el mío).' },

  { id: 'cuadro', met: 'musicaCuadro', tecla: null, habla: '',
    /* Igual que arriba: «cuadro», «fotograma atrás», «dame el cuadro», pero NO
       «un cuadro de la casa». La expresión suelta `/cuadro/` se comía cualquier
       frase con la palabra, y con música sonando eso es un salto de fotograma
       donde ella hablaba de otra cosa. */
    casa: m => (/^(?:el |la |un |paso de |salto de )?(?:cuadro|fotograma|frame)(?:\s|$)/i.test(m)
              && m.split(/\s+/).length <= 3)
            || /^(?:dame|mueve|pasa|avanza|retrocede)\s+(?:me\s+)?(?:el |un )?(?:cuadro|fotograma|frame)\b/i.test(m),
    dijo: (e, m) => 'Un fotograma ' + (/atr[aá]s|antes|retro/i.test(m) ? 'atrás' : 'adelante') + '.',
    ajeno: '' },

  { id: 'parar', met: 'musicaParar', tecla: 'parar', habla: 'Listo, sin música',
    casa: m => /parar la m[uú]sica|cierra el reproductor|silencio/i.test(m),
    dijo: () => 'Reproductor parado. La pantalla Música sigue ahí con ☰.',
    ajeno: 'Mando «parar» al reproductor del aparato (no es el mío).' },
];

/** Qué mando de transporte es esta frase (ya normalizada), o `null`. */
export function mandoDe(msg) {
  const m = paraCasar(msg);
  if (!m) return null;
  return TRANSPORTE.find(t => t.casa(m)) || null;
}

/**
 * A dónde va el mando, dicho con una palabra y con la **razón** en la otra.
 *
 * `propio` suena el reproductor de CORT → se manda el método de siempre.
 * `ajeno`  suena otra app y el puente tiene teclas → `teclaMedia`.
 * `otro-sin-teclas` la música es ajena pero este APK no tiene `teclaMedia`
 *          (un envase anterior a la 2.9.1): se dice, no se finge.
 * `nada`   no suena absolutamente nada, o el mando sólo existe en nuestro
 *          reproductor: la frase sigue su camino normal hacia el núcleo.
 */
export function rutaDe(mando, { mio = false, ajeno = false, teclas = false } = {}) {
  if (!mando) return { a: 'nada', porque: 'no es un mando de transporte' };
  if (mio) return { a: 'propio', porque: 'suena el reproductor de CORT' };
  if (!mando.tecla) return { a: 'nada', porque: `«${mando.id}» sólo existe en mi reproductor` };
  if (!ajeno) return { a: 'nada', porque: 'no hay música sonando en el aparato' };
  return teclas ? { a: 'ajeno', porque: 'suena otra aplicación y el puente presta sus teclas' }
                : { a: 'otro-sin-teclas', porque: 'suena otra aplicación y este CORT no tiene teclas' };
}

/** El mando que entiende la cara en la pantalla Música: `null` si la frase no es suya. */
export function resuelve(msg, estado = {}) {
  const mando = mandoDe(msg);
  if (!mando) return null;
  const ruta = rutaDe(mando, estado);
  if (ruta.a === 'nada') return null;
  const m = paraCasar(msg);
  return {
    id: mando.id,
    a: ruta.a,
    porque: ruta.porque,
    met: mando.met,
    tecla: mando.tecla,
    /* El texto depende del destino, y el de «sin teclas» no puede prometer una orden
       que no se dio: decir «mando pausa» cuando el puente no tiene `teclaMedia` es
       justo la respuesta inventada que hizo perder la confianza en CORT. */
    dijo: ruta.a === 'propio' ? mando.dijo(estado.e, m)
         : ruta.a === 'ajeno' ? mando.ajeno
         : 'Suena música en otra aplicación y este CORT no tiene teclas de transporte: ábrela y mándala tú, o actualízame.',
    habla: ruta.a === 'otro-sin-teclas' ? 'Esa música no es mía' : mando.habla,
  };
}
