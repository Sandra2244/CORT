#!/usr/bin/env node
/* Prueba de los MANDOS de CORT (`ui/js/mandos.js`), sin teléfono y sin pantalla.
 *
 * El módulo es puro a propósito —no toca el DOM, ni `window.CortNative`, ni
 * `fetch`— y esa es la razón de existir de esta suite: los tres fallos que la
 * dueña llamó «le digo pausa y no lo hace» viven todos en la lógica de casar la
 * frase, y hasta ahora ninguno se podía comprobar sin un Android delante.
 *
 * Lo que se prueba aquí, en orden:
 *   [1] `paraCasar` — el punto que el reconocedor pega al final («Pausa.»), los
 *       espacios de más y las comillas. Con el punto delante, `/^pausa$/` no
 *       casa, la frase se va al backend y vuelve con el 501 del APK.
 *   [2] `mandoDe`    — qué mando es cada frase suya, con sus acentos; y cuáles
 *       NO lo son («¿cuál es la palabra anterior?» no es un mando).
 *   [3] `rutaDe`     — la tabla de verdad de los destinos: reproductor propio,
 *       otra app con teclas, otra app sin teclas, y nada sonando.
 *   [4] `resuelve`   — el viaje completo, frase → lo que la cara va a hacer y a
 *       decir. Aquí cae el «mando pausa» inventado cuando el puente no tiene
 *       `teclaMedia`.
 *   [5] el contrato de la tabla — ids y métodos sin repetir, ningún texto vacío.
 *
 * Uso:  node scripts/prueba-mandos.mjs     (una fracción de segundo)
 * Va en `build.yml` junto a las demás pruebas de lógica, antes de firmar.
 */
import { paraCasar, TRANSPORTE, mandoDe, rutaDe, resuelve } from '../ui/js/mandos.js';

let fallos = 0, hechos = 0;
const ok = (etiqueta, condicionado, detalle = '') => {
  if (condicionado) { hechos++; console.log('  ok  ' + etiqueta); }
  else { fallos++; console.log('  NO  ' + etiqueta + (detalle ? ' → ' + detalle : '')); }
};

console.log('\n[1] paraCasar: lo que el reconocedor escribe de más');
ok('punto final fuera: «Pausa.» → «Pausa»', paraCasar('Pausa.') === 'Pausa');
ok('el caso reportado: «Pausa.» casa con /pausa/ sin tocar la expresión',
   /^pausa$/i.test(paraCasar('Pausa.')));
ok('espacios de más: «pausa  la   música» → «pausa la música»',
   paraCasar('pausa  la   música') === 'pausa la música');
ok('comillas y guiones bajos fuera: ««Siguiente.»» → «Siguiente»',
   paraCasar('«Siguiente.»') === 'Siguiente');
ok('signos de apertura fuera: «¿Qué sigue?» → «Qué sigue»',
   paraCasar('¿Qué sigue?') === 'Qué sigue');
ok('la puntuación de ENMEDIO se conserva (no es un mando, es su frase)',
   paraCasar('pausa, la música') === 'pausa, la música');
ok('vacío sigue vacío', paraCasar('   ') === '');
ok('null no revienta', paraCasar(null) === '' && paraCasar(undefined) === '');
ok('números y palabras raras sobreviven', paraCasar('5x5.') === '5x5');

console.log('\n[2] mandoDe: qué frase es un mando y cuál no');
const ES = (frase, id) => {
  const m = mandoDe(frase);
  ok(`«${frase}» → ${id}`, !!m && m.id === id, m ? `salió ${m.id}` : 'no casó ningún mando');
};
const NO = frase => ok(`«${frase}» NO es un mando`, mandoDe(frase) === null,
                       'casó ' + (mandoDe(frase) || {}).id);
ES('Pausa.', 'pausa');            // ← el bug de la dueña, de punta a punta
ES('pausa', 'pausa');
ES('pausa la música', 'pausa');
ES('detén eso', 'pausa');
ES('para el audio', 'pausa');
ES('Sigue.', 'sigue');
ES('continúa la canción', 'sigue');
ES('play', 'sigue');
ES('la siguiente', 'siguiente');
ES('¿Qué sigue?', 'siguiente');   // con el punto y el signo del reconocedor
ES('pon otra canción', 'siguiente');
ES('anterior', 'anterior');
ES('ve a la anterior', 'anterior');
ES('la de antes', 'anterior');
ES('cuadro', 'cuadro');
ES('fotograma atrás', 'cuadro');
ES('frame adelante', 'cuadro');
ES('silencio', 'parar');
ES('parar la música', 'parar');
ES('cierra el reproductor', 'parar');
NO('stop');                       // suelto no dice qué parar: se queda en el núcleo
NO('hola cort');
NO('¿cuál es la palabra anterior?');   // hablaba de la palabra, no de la canción
NO('explícame qué sigue después');      // «siguiente» sin mando
NO('un cuadro de la casa');             // «cuadro» sin reproductor delante

console.log('\n[3] rutaDe: la tabla de verdad de los destinos');
const pausa = mandoDe('pausa');
const cuadro = mandoDe('cuadro');
ok('reproductor propio vivo → propio', rutaDe(pausa, { mio: true }).a === 'propio');
ok('otra app suena y hay teclas → ajeno',
   rutaDe(pausa, { mio: false, ajeno: true, teclas: true }).a === 'ajeno');
ok('otra app suena y NO hay teclas → otro-sin-teclas',
   rutaDe(pausa, { mio: false, ajeno: true, teclas: false }).a === 'otro-sin-teclas');
ok('no suena nada → nada (la frase sigue su camino)',
   rutaDe(pausa, { mio: false, ajeno: false, teclas: true }).a === 'nada');
ok('el fotograma sólo existe en el reproductor propio',
   rutaDe(cuadro, { mio: false, ajeno: true, teclas: true }).a === 'nada');
ok('propio manda aunque no suene nada más (el reproductor está vivo, pausado)',
   rutaDe(pausa, { mio: true, ajeno: true, teclas: true }).a === 'propio');
ok('sin mando no hay ruta', rutaDe(null, { mio: true }).a === 'nada');
ok('toda ruta trae su porqué dicho con palabras',
   ['propio', 'ajeno', 'otro-sin-teclas', 'nada'].every(a => typeof rutaDe(pausa, {
     mio: a === 'propio', ajeno: a === 'ajeno' || a === 'otro-sin-teclas', teclas: a !== 'otro-sin-teclas',
   }).porque === 'string' && rutaDe(pausa, { mio: true }).porque.length > 10));

console.log('\n[4] resuelve: el viaje completo, frase → hecho y palabra');
{
  const e = { vivo: true, pista: { titulo: 'Dark' } };
  const r = resuelve('Pausa.', { e, mio: true, ajeno: false, teclas: true });
  ok('«Pausa.» con mi reproductor → musicaPausa', !!r && r.a === 'propio' && r.met === 'musicaPausa');
  ok('el texto dice la canción que estaba sonando', !!r && /Dark/.test(r.dijo));
  ok('y habla la respuesta corta', !!r && r.habla === 'Pausa');

  const aj = resuelve('pausa la música', { e: { vivo: false }, mio: false, ajeno: true, teclas: true });
  ok('«pausa la música» con Spotify puesto → la tecla del aparato',
     !!aj && aj.a === 'ajeno' && aj.tecla === 'pausa');
  ok('y lo dice claro: no es nuestro el reproductor', !!aj && /no es mío/.test(aj.dijo));

  const sin = resuelve('pausa', { e: { vivo: false }, mio: false, ajeno: true, teclas: false });
  ok('sin `teclaMedia` NO se miente: no promete mandar la pausa',
     !!sin && sin.a === 'otro-sin-teclas' && !/^Mando/.test(sin.dijo));
  ok('sin teclas dice quédese ahí o actualízame', !!sin && /no tiene teclas/.test(sin.dijo));
  ok('sin teclas avisa por la boca', !!sin && sin.habla === 'Esa música no es mía');

  ok('no suena nada → la cara no consume la frase', resuelve('pausa', { mio: false, ajeno: false, teclas: true }) === null);
  ok('frase que no es mando → null', resuelve('qué hora es', { mio: true, ajeno: false, teclas: true }) === null);

  const c = resuelve('fotograma atrás', { e: { vivo: true }, mio: true, ajeno: false, teclas: true });
  ok('el cuadro hacia atrás se decide por la frase', !!c && /atrás/.test(c.dijo));
  const c2 = resuelve('cuadro', { e: { vivo: true }, mio: true, ajeno: false, teclas: true });
  ok('«cuadro» a secas va adelante', !!c2 && /adelante/.test(c2.dijo));

  const nulo = resuelve('anterior', { e: { vivo: true }, mio: true, ajeno: false, teclas: true });
  ok('«anterior» no habla, sólo pinta (como siempre)', !!nulo && nulo.habla === '' && /anterior/.test(nulo.dijo));
}

console.log('\n[5] el contrato de la tabla');
ok('son seis mandos', TRANSPORTE.length === 6);
ok('ids sin repetir', new Set(TRANSPORTE.map(t => t.id)).size === TRANSPORTE.length);
ok('métodos del puente sin repetir', new Set(TRANSPORTE.map(t => t.met)).size === TRANSPORTE.length);
ok('cada mando tiene su casa, su dijo y su habla (aunque sea vacío)',
   TRANSPORTE.every(t => typeof t.casa === 'function' && typeof t.dijo === 'function'
                      && typeof t.habla === 'string' && typeof t.met === 'string'));
ok('sólo el fotograma se queda sin tecla ajena',
   TRANSPORTE.filter(t => t.tecla === null).map(t => t.id).join() === 'cuadro');
ok('las teclas son las cinco que entiende el puente',
   TRANSPORTE.filter(t => t.tecla).map(t => t.tecla).sort().join(',')
     === 'anterior,parar,pausa,play,siguiente');
ok('los mandos que van a otra app tienen su texto para esa app',
   TRANSPORTE.every(t => t.tecla === null || /no es el mío|no es mío/.test(t.ajeno)));
ok('ningún texto de la cara sale vacío',
   TRANSPORTE.every(t => t.ajeno === '' || t.ajeno.length > 20));

console.log('\n' + (fallos ? 'FALTA ' + fallos + ' COSA(S) en los mandos de CORT.'
                           : 'mandos: ' + hechos + ' comprobaciones, todas en verde.'));
process.exit(fallos ? 1 : 0);
