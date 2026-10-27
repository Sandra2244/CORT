/* scripts/prueba-md.mjs — el markdown de la Charla, su hora, y la letra con marcas
 *
 * Son tres trozos que `pantallas.js` tenía dentro y que ahora viven en `ui/js/md.js`
 * y `ui/js/letra.js`: el primer corte de la refactorización por tamaño que pide el
 * prompt de la dueña («la interfaz mil líneas máximo, divides y conectas»). Se
 * prueban aparte por lo mismo que `texto.js` — deciden **cómo se lee lo que contesta
 * un modelo**, y eso no se puede dejar a medio comprobar dentro de una hoja de 3.000
 * líneas. Lo decisivo no es el adorno: es que una respuesta con `<script>` se lea
 * como texto, y que un `[0:07.5]` del karaoke no se vuelva siete minutos.
 *
 * Uso:  node scripts/prueba-md.mjs
 */
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { md, horaDe } from '../ui/js/md.js';
import { parseaLetra } from '../ui/js/letra.js';

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..');
const sinComentarios = s => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
let fallos = 0, hechos = 0;
const ok = (t, c, d = '') => { if (c) { hechos++; console.log('  ok  ' + t); }
  else { fallos++; console.log('  NO  ' + t + (d ? ' → ' + d : '')); } };

console.log('\n[1] `md`: primero se escapa TODO, después se adornan los bloques');
const seguro = md('<script>alert("hola")</script>');
ok('una respuesta con `<script>` se lee como texto y no se ejecuta',
   !/<script/i.test(seguro) && /&lt;script&gt;/.test(seguro));
ok('las comillas del modelo salen escapadas (no rompen un atributo de la burbuja)',
   /&quot;/.test(md('dice "esto"')) && !/"/.test(md('dice "esto"')));
ok('el bloque de código sale en su `<pre>` con su clase',
   /<pre class="bur-pre"><code>hola<\/code><\/pre>/.test(md('```\nhola\n```')));
ok('y lo de dentro sigue escapado: un `<b>` dentro del bloque no se vuelve negrita',
   /&lt;b&gt;/.test(md('```\n<b>x</b>\n```')));
ok('el código en línea va en su `<code>`',
   /<code class="bur-code">df -h<\/code>/.test(md('usa `df -h` ya')));
ok('las negritas se vuelven `<b>`', md('esto es **fuerte**') === 'esto es <b>fuerte</b>');
ok('un enlace se abre en su propia pestaña y con `rel="noopener"`',
   /<a href="https:\/\/x\.es\/a" target="_blank" rel="noopener">https:\/\/x\.es\/a<\/a>/.test(md('mira https://x.es/a')));
ok('el enlace entre paréntesis se ciñe al URL: el `)` se queda fuera del enlace',
   md('(https://x.es/a)') === '(<a href="https://x.es/a" target="_blank" rel="noopener">https://x.es/a</a>)',
   md('(https://x.es/a)'));
ok('los saltos de línea se ven', md('a\nb') === 'a<br>b');
ok('no queda ni una marca de bloque suelta: los dos bloques se devuelven',
   !md('```\nuno\n```\ntexto\n```\ndos\n```').includes('\u0001')
   && (md('```\nuno\n```\ntexto\n```\ndos\n```').match(/<pre /g) || []).length === 2);
ok('`null`, `undefined` y la cadena vacía no pintan «undefined» en la pantalla',
   md(null) === '' && md(undefined) === '' && md('') === '');
ok('un bloque sin cerrar no deja la marca tirada: o se cierra o no se finge código',
   !/<pre /.test(md('``\ntexto sin bloque')));

console.log('\n[2] `horaDe`: la hora de la burbuja, y silencio cuando no hay');
ok('un `ms` de verdad sale como hora de dos dígitos',
   /^\d{2}[:.]\d{2}$/.test(horaDe(1730000000000)), horaDe(1730000000000));
ok('cero, vacío, `null`, negativo y texto no dan «NaN:NaN»',
   horaDe(0) === '' && horaDe(null) === '' && horaDe(undefined) === ''
   && horaDe(-5) === '' && horaDe('mañana') === '' && horaDe(NaN) === '');
ok('el texto de una hora no se cuela: `Number` antes de pintar', !/mañana/.test(horaDe('mañana')));

console.log('\n[3] `parseaLetra`: el karaoke con las marcas de LRCLIB');
const una = parseaLetra('[00:13.42] primera línea');
ok('el formato normal sale en segundos', una.length === 1
   && Math.abs(una[0].s - 13.42) < 1e-9 && una[0].texto === 'primera línea',
   JSON.stringify(una));
const corta = parseaLetra('[0:07.5] centésimas cortas');
ok('«[0:07.5]» son 7,50 s y no 7,05 ni 7 minutos', corta.length === 1
   && Math.abs(corta[0].s - 7.5) < 1e-9, JSON.stringify(corta));
const sinCs = parseaLetra('[01:05] sin centésimas');
ok('sin centésimas sigue siendo minuto y segundo', sinCs.length === 1
   && Math.abs(sinCs[0].s - 65) < 1e-9, JSON.stringify(sinCs));
const dosPuntos = parseaLetra('[00:13:42] separador de dos puntos');
ok('el separador también puede ser `:` (algunas letras llegan así)',
   dosPuntos.length === 1 && Math.abs(dosPuntos[0].s - 13.42) < 1e-9, JSON.stringify(dosPuntos));
ok('una línea sin marca no es letra', parseaLetra('letra suelta sin tiempo').length === 0);
ok('una marca sin texto tampoco: en el karaoke ocupa hueco y corta el canto',
   parseaLetra('[00:13.42]   ').length === 0);
const mezcla = parseaLetra('[00:00.00] una\nbasura\n[00:30.10] dos\n[1:02.30] tres');
ok('las buenas se quedan en su orden y las basuras fuera',
   mezcla.length === 3 && mezcla.map(l => l.texto).join('|') === 'una|dos|tres'
   && Math.abs(mezcla[2].s - 62.3) < 1e-9, JSON.stringify(mezcla));
ok('`null` o vacío devuelven lista, no `undefined` (la pintora recorre sin mirar)',
   Array.isArray(parseaLetra(null)) && parseaLetra('').length === 0);
const larga = parseaLetra('[100:59.99] tres dígitos de minuto');
ok('un minuto de tres dígitos no se cae', larga.length === 1
   && Math.abs(larga[0].s - (100 * 60 + 59.99)) < 1e-9, JSON.stringify(larga));

console.log('\n[4] la cadena: estos tres no vuelven a vivir dentro de una pantalla');
const carpeta = join(raiz, 'ui', 'js');
const nombres = ['md', 'horaDe', 'parseaLetra'];
const fuera = [];
for (const f of readdirSync(carpeta).filter(f => f.endsWith('.js'))) {
  const s = sinComentarios(readFileSync(join(carpeta, f), 'utf8'));
  for (const n of nombres) {
    const define = new RegExp(`(^|\\n)\\s*(export\\s+)?(const|let|var|function)\\s+${n}\\b`);
    if (define.test(s) && !(f === 'md.js' && (n === 'md' || n === 'horaDe'))
                        && !(f === 'letra.js' && n === 'parseaLetra'))
      fuera.push(`${f} · ${n}`);
  }
}
ok('cada uno está definido una sola vez, en su hoja', fuera.length === 0, fuera.join(', '));
const pant = readFileSync(join(carpeta, 'pantallas.js'), 'utf8');
const charlaJs = readFileSync(join(carpeta, 'charla.js'), 'utf8');
/* Desde el corte 3 la Charla es su propio archivo, así que «dónde se usa cada cosa» se
   comprueba **nombrando el archivo** en vez de leer un solo fichero y alegrarse de que
   aparezca por ahí: el markdown y la hora de la burbuja viven en `charla.js`, el parser
   de la letra sigue en `pantallas.js` (lo necesita MV). */
ok('`charla.js` importa el markdown y la hora; `pantallas.js` importa el parser de la letra',
   /import \{ md, horaDe \} from '\.\/md\.js'/.test(charlaJs)
   && /import \{ parseaLetra \} from '\.\/letra\.js'/.test(pant));
ok('y `pantallas.js` no sigue importando lo que ya no usa: la Charla se lo llevó',
   !/from '\.\/md\.js'/.test(pant));
ok('cada uno se usa donde toca: la burbuja con su hora y su markdown en la Charla, la letra en MV',
   /const cuando = horaDe\(m\.hora\)/.test(charlaJs) && /\bmd\(/.test(charlaJs)
   && /letraLineas = parseaLetra\(/.test(pant));
const mdjs = readFileSync(join(carpeta, 'md.js'), 'utf8');
ok('`md.js` escapa antes de adornar —es la única línea que lo garantiza—',
   /let s = esc\(/.test(mdjs) && /from '\.\/texto\.js'/.test(mdjs));

console.log(fallos ? `\nFALTA ${fallos} COSA(S)`
  : `\ntodo en orden: la Charla y el karaoke tienen su hoja y su comprobación (${hechos})`);
process.exit(fallos ? 1 : 0);
