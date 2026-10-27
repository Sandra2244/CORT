/* scripts/prueba-placa.mjs — el paso 1.3 de la Fase 1 probado con node
 *
 * La placa de arriba (hora, fecha, nodo, modelo, estado) se puede ir de dos formas:
 * pintando de menos o pintando de más. La prueba persigue LO DE MÁS, que es lo que la
 * dueña ha corregido siempre en esta casa: un `undefined`, un `—` de adorno, un modelo
 * que nadie confirmó. Sobre el módulo PURO `ui/js/placa.js`, sin DOM y sin red.
 *
 *   [1] la regla de honestidad: ningún valor sin medir llega a la placa, ni en la
 *       lista de basura más fea que se puede colar por un `String(...)`.
 *   [2] la hora y la fecha, con el reloj congelado y con un reloj roto.
 *   [3] el contrato con `hud.js`: TODOS los estados de `LAMP` tienen su palabra en la
 *       placa (si falta uno, la fila se cae en silencio y eso es un bug, no un diseño).
 *   [4] el nodo: teléfono o PC, y nada más.
 *   [5] la costura: `hud.js` importa el módulo, `setState()` alimenta el estado, la
 *       placa se pinta en el arranque (no a los diez segundos), `ctx.placa` existe y
 *       las pantallas sólo nombran un modelo cuando ella lo eligió.
 *
 * Uso:  node scripts/prueba-placa.mjs     (una fracción de segundo, sin pantalla)
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { cara } from './lib-cara.mjs';   // la cara son varios archivos desde el corte 3
import { ESTADOS_PLACA, nombreNodo, horaPlaca, fechaPlaca, medible, camposPlaca, textoPlaca }
  from '../ui/js/placa.js';

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..');
let fallos = 0, hechos = 0;
const ok = (etiqueta, condicionado, detalle = '') => {
  if (condicionado) { hechos++; console.log('  ok  ' + etiqueta); }
  else { fallos++; console.log('  NO  ' + etiqueta + (detalle ? ' → ' + detalle : '')); }
};

console.log('\n[1] la regla de honestidad: lo que no se mide no se pinta');
const basura = [undefined, null, '', '   ', 'undefined', 'null', 'NaN',
                '--', '--:--:--', '···', '—', -0, 0, false, {}, []];
const pinta = v => camposPlaca({ hora: v, fecha: v, nodo: v, modelo: v, estado: 'listo' });
for (const v of basura) {
  const cs = pinta(v);
  const dicho = cs.map(c => c.v).join('|');
  ok(`un dato roto (${JSON.stringify(v) ?? 'undefined'}) no pinta hora, fecha, nodo ni modelo`,
     cs.length === 1 && cs[0].k === 'estado', `pintó: ${dicho}`);
}
ok('textoPlaca con todo roto deja SOLO el estado', textoPlaca({ hora: 'undefined', fecha: null,
   nodo: '--:--:--', modelo: undefined, estado: 'pensando' }) === 'piensa');
ok('el campo cero y el booleano tampoco se cuelan', !medible(0) && !medible(false));
ok('un dato de verdad sí pasa', medible('qwen2.5:3b') && medible('14:28'));

console.log('\n[2] la hora y la fecha, con el reloj congelado');
const fijo = new Date('2026-10-27T14:28:00');
ok(`hora en 24 horas, sin segundos (${horaPlaca(fijo)})`, horaPlaca(fijo) === '14:28');
ok(`fecha en español (${fechaPlaca(fijo)})`, /^\d{2} \w{3,5} \d{4}$/.test(fechaPlaca(fijo)));
ok('un reloj roto no pinta hora', horaPlaca(new Date('no-es-una-fecha')) === '');
ok('un reloj roto no pinta fecha', fechaPlaca(new Date('no-es-una-fecha')) === '');
ok('acepta un instante (número), no sólo un Date', /^\d{2}:\d{2}$/.test(horaPlaca(fijo.getTime())));

console.log('\n[3] el contrato con los estados de la cara');
const hud = readFileSync(join(raiz, 'ui/js/hud.js'), 'utf8');
const lampas = [...hud.matchAll(/^\s{2}(reposo|escucha|pensa|pensando|hablando|listo|oculto|error):\s*\[/gm)]
  .map(m => m[1]);
ok(`se leyeron los estados de \`LAMP\` (${lampas.length})`, lampas.length >= 6);
for (const k of lampas) {
  ok(`el estado «${k}» tiene su palabra en la placa`, typeof ESTADOS_PLACA[k] === 'string' && ESTADOS_PLACA[k].length > 0);
}
ok('un estado que no existe en la tabla pinta CERO campos', camposPlaca({ estado: 'mandarache' }).length === 0);
ok('los estados pintados son minúsculos y de una palabra o dos',
   Object.values(ESTADOS_PLACA).every(v => /^[a-záéíóúñ ]+$/.test(v)));

console.log('\n[4] el nodo: sólo las dos palabras que son verdad');
ok('en Android dice «teléfono»', nombreNodo(true) === 'teléfono');
ok('en el PC dice «PC»', nombreNodo(false) === 'PC');
ok('y se calla si no se sabe en qué aparato corre',
   nombreNodo(undefined) === '' && nombreNodo(0) === '' && nombreNodo('cierto') === '');
ok('un nodo desconocido no pinta fila', camposPlaca({ nodo: nombreNodo(undefined) }).length === 0);

console.log('\n[5] la costura en la cara');
ok('hud.js importa la placa', /from '\.\/placa\.js'/.test(hud));
ok('setState() alimenta el estado de la placa', /function setState\(k\) \{\n  datosPlaca\(\{ estado: k \}\);/.test(hud));
ok('la placa se pinta en el arranque, no cuando toque el intervalo',
   /datosPlaca\(\{ hora: horaPlaca\(new Date\(\)\), fecha: fechaPlaca\(new Date\(\)\)/.test(hud));
ok('el nodo se mide en el arranque con IS_ANDROID', /nodo: nombreNodo\(IS_ANDROID\)/.test(hud));
ok('las pantallas reciben `placa` en su contexto', /placa: datosPlaca,/.test(hud));
const js = cara(join(raiz, 'ui', 'js'));   // marco + pantallas + charla: el `chModelo` vive en la Charla
/* La trampa que cazó la vista previa del 2026-10-27: `chModelo` trae el modelo
   ELEGIDO en la cabecera de la charla, no el que habló. Con Ollama apagado la
   respuesta salía `offline` y la placa seguía diciendo `qwen2.5:0.5b` — un modelo que
   no pensó. Las dos reglas de abajo son las que impiden que eso vuelva a pasar. */
ok('el modelo sólo se nombra si la FUENTE es de modelo (casa/nube/local)',
   /modelo: \(chModelo && \/casa\|nube\|local\/i\.test\(fuente\)\) \? chModelo : ''/.test(js));
ok('y la orden del ejecutor LO BORRA de la placa',
   /ctx\?\.placa\?\.\(\{ modelo: \/casa\|nube\|local\/i\.test\(String\(j\.source \|\| ''\)\) \? \(chModelo \|\| ''\) : '' \}\)/.test(js));
ok('ninguna de las dos pinta ya el modelo elegido a ciegas',
   !/if \(chModelo\) ctx\?\.placa\?\.\(\{ modelo: chModelo \}\)/.test(js));
const html = readFileSync(join(raiz, 'ui/index.html'), 'utf8');
ok('el HTML conserva el panel de la placa', /<div class="panel" id="clock">/.test(html));
const css = readFileSync(join(raiz, 'ui/css/hud.css'), 'utf8');
ok('cada campo tiene su estilo', ['.pl-hora', '.pl-fecha', '.pl-nodo', '.pl-modelo', '.pl-estado']
   .every(c => css.includes(c)));
ok('en el teléfono se sacrifica la fecha, nunca la hora', /html\.mobile \.pl-fecha\{display:none\}/.test(css));

console.log(fallos ? `\nFALTA ${fallos} COSA(S)`
                   : `\ntodo en orden: la placa pinta lo medido y calla lo que no (${hechos})`);
process.exit(fallos ? 1 : 0);
