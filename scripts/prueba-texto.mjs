/* scripts/prueba-texto.mjs — los tres pliegues de texto de la cara, y su cadena
 *
 * `ui/js/texto.js` existe porque `esc` estaba definido **cinco veces** y `normaliza`
 * dos, copiados byte a byte. Este archivo comprueba dos cosas distintas, y la segunda
 * es la que vale el CI:
 *
 *   [1] que los pliegues hagan lo que prometen (escapar, plegar tildes, dejar la
 *       cadena estricta para comparar), incluida la honestidad con `null`/`undefined`
 *       —pintar «undefined» en la placa ya fue un bug corregido en el paso 1.3—;
 *   [2] que **no vuelva a aparecer una segunda definición** en la cara. Cinco copias
 *       de un escapeador son cinco oportunidades de que una se quede atrás y la cara
 *       se rompa en una sola pantalla, así que aquí se mide, no se recuerda.
 *       (En JavaScript `a === b === c` no compara tres cosas: da `false` casi siempre.
 *        Las igualdades múltiples se escriben de dos en dos, como abajo.)
 *
 * Uso:  node scripts/prueba-texto.mjs
 */
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { esc, sinTilde, normaliza } from '../ui/js/texto.js';
import { normaliza as normalizaDeAutomatiza } from '../ui/js/automatiza.js';

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..');
let fallos = 0, hechos = 0;
const ok = (t, c, d = '') => { if (c) { hechos++; console.log('  ok  ' + t); }
  else { fallos++; console.log('  NO  ' + t + (d ? ' → ' + d : '')); } };

console.log('\n[1] `esc`: HTML seguro para lo que pinta la cara');
ok('los cinco caracteres peligrosos se escapan',
   esc('&<>["\']') === '&amp;&lt;&gt;[&quot;&#39;]');
ok('el apóstrofo incluido: se mete en atributos (`data-orden="…"`) igual que el resto',
   /&#39;/.test(esc("O'Neil")));
ok('no queda ni un `<`, `>`, `"` o `\'` suelto, y cada `&` es el principio de una entidad',
   (() => { const s = esc('<b>“x”</b> & y \'z\' "w"');
     return !/[<>"']/.test(s) && s.replace(/&(amp|lt|gt|quot|#39);/g, '').indexOf('&') < 0; })());
ok('`null` y `undefined` dan cadena vacía, nunca el texto «undefined»',
   esc(null) === '' && esc(undefined) === '' && esc() === '');
ok('un número se pinta (la placa manda enteros de batería)', esc(87) === '87');
ok('una cadena ya escapada se vuelve a escapar: es texto literal, y así se enseña',
   esc('&amp;') === '&amp;amp;');
ok('los saltos de línea se conservan (la letra de una canción es multilínea)',
   esc('a\nb') === 'a\nb');

console.log('\n[2] `sinTilde`: minúsculas y sin acentos, conservando la puntuación');
ok('tildes españolas fuera', sinTilde('Canción Música') === 'cancion musica');
ok('la ñ se pliega a n — es el mismo criterio que `Cerebro.normaliza` en Java, y por eso '
   + 'se comprueba: si un día cambia aquí, tiene que cambiar allí',
   sinTilde('España') === 'espana');
ok('la puntuación se queda (sirve para mostrar, no sólo para comparar)',
   sinTilde('¡Hola, qué tal?!') === '¡hola, que tal?!');
ok('`null`/`undefined` no lanzan', sinTilde(null) === '' && sinTilde(undefined) === '');
ok('una cadena vacía sigue vacía', sinTilde('') === '');

console.log('\n[3] `normaliza`: la forma estricta con la que casan las órdenes');
ok('mayúsculas, tildes y símbolos fuera, y un solo espacio',
   normaliza('  Modo   NOCHE!  ') === 'modo noche');
ok('las tres formas de la misma orden son la misma cadena',
   normaliza('Modo Noche') === normaliza('modo  noche')
   && normaliza('modo  noche') === normaliza('MODO noche'));
ok('los signos de exclamación se convierten en hueco y luego se recortan',
   normaliza('¡apaga!') === 'apaga');
ok('los dígitos se quedan (una alarma es «alarma 7»)',
   normaliza('Alarma 7:30') === 'alarma 7 30');
ok('es `sinTilde` y luego quitar símbolos: si se separan los criterios, esto lo nota',
   normaliza('«Cámbiame  el VOLUMEN»') === 'cambiame el volumen');
ok('vacío y `null` dan cadena vacía', normaliza('') === '' && normaliza(null) === '');
ok('una cadena de sólo símbolos no deja un espacio huérfano', normaliza('!!! ???') === '');

console.log('\n[4] la cadena: ni una segunda definición en la cara');
const NOMBRES = ['esc', 'sinTilde', 'normaliza'];
const carpeta = join(raiz, 'ui', 'js');
const hoja = f => readFileSync(join(carpeta, f), 'utf8');
const definiciones = [];
for (const f of readdirSync(carpeta).filter(f => f.endsWith('.js'))) {
  if (f === 'texto.js') continue;
  const sin = hoja(f).replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
  for (const n of NOMBRES) {
    if (new RegExp(`(^|\\n)\\s*(export\\s+)?(const|let|var|function)\\s+${n}\\b`).test(sin))
      definiciones.push(`${f} · ${n}`);
  }
}
ok('en `ui/js` sólo `texto.js` define los tres pliegues',
   definiciones.length === 0, definiciones.join(', '));

/* Las hojas sueltas de `ui/` también contaban su propio `esc` (y más flojo: sin
   comillas). Se mide igual que arriba para que la copia no vuelva por el HTML. */
const htmls = readdirSync(join(raiz, 'ui')).filter(f => f.endsWith('.html'));
const enHtml = [];
for (const f of htmls) {
  const s = readFileSync(join(raiz, 'ui', f), 'utf8');
  for (const n of NOMBRES)
    if (new RegExp(`\\b(const|let|var|function)\\s+${n}\\s*[=(]`).test(s)) enHtml.push(`${f} · ${n}`);
}
ok('ningún HTML de `ui/` vuelve a definir su propio escapeador',
   enHtml.length === 0, enHtml.join(', '));

console.log('\n[5] la costura: quien usa el pliegue, lo importa');
const sinImportar = [];
for (const f of readdirSync(carpeta).filter(f => f.endsWith('.js') && f !== 'texto.js')) {
  const s = hoja(f);
  const sin = s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
  for (const n of NOMBRES) {
    if (new RegExp(`\\b${n}\\s*\\(`).test(sin) && !new RegExp(`import\\s*\\{[^}]*\\b${n}\\b[^}]*\\}\\s*from\\s*'\\./texto\\.js'`).test(s))
      sinImportar.push(`${f} usa ${n}()`);
  }
}
ok('todo el que llama a `esc`/`sinTilde`/`normaliza` lo trae de `texto.js`',
   sinImportar.length === 0, sinImportar.join(', '));
ok('`automatiza.js` sigue re-exportando `normaliza` (la suite de automatizaciones la '
   + 'importa de ahí, y romper ese export sería romper el CI por el atajo)',
   normalizaDeAutomatiza === normaliza);

console.log(fallos ? `\nFALTA ${fallos} COSA(S)`
  : `\ntodo en orden: tres pliegues definidos una sola vez (${hechos} comprobaciones)`);
process.exit(fallos ? 1 : 0);
