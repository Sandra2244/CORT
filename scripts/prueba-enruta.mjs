#!/usr/bin/env node
/* Prueba de la REGLA J2.1 (`ui/js/ordenes.js` y su costura en `pantallas.js`).
 *
 * El plan (`docs/PLAN-FASE-2-JARVIS.md` §2 y §6) pide dos puertas de salida, y
 * esta suite las muerde las dos:
 *   [1] una orden real ENRUTADA: las frases del vocabulario del ejecutor van a
 *       `orden`, con su acción nombrada — ninguna se queda pidiendo caridad al cerebro.
 *   [2] la conversación NO secuestrada: preguntas normales (y las trampas con
 *       «cuéntame») siguen yendo a `charla`.
 *   [3] la imposible sigue siendo orden: «abre la carpeta que no existe» se ENRUTA
 *       a `/api/command` — la honestidad del «no pude» la pone el `done` y el `reply`
 *       del núcleo, no un filtro cobarde de la cara.
 *   [4] el contrato del vocabulario: nombres únicos, regex compilables, espejo de
 *       los verbos que de verdad existen en `backend/app/actions.py`.
 *   [5] la costura en la cara: `pantallas.js` importa la regla, POSTea a
 *       `/api/command` sólo con `ruta==='orden'`, el chip `hecho:` se pinta sólo
 *       desde `m.hecho` (nunca inventado), y el adjunto/modo elegido no se desvían.
 *
 * Uso:  node scripts/prueba-enruta.mjs     (una fracción de segundo, sin pantalla)
 * Va en `build.yml` junto a las demás pruebas de lógica, antes de firmar.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { cara } from './lib-cara.mjs';   // la cara son varios archivos desde el corte 3
import { clasificarOrden, VOCABULARIO_ORDENES } from '../ui/js/ordenes.js';

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..');
let fallos = 0, hechos = 0;
const ok = (etiqueta, condicionado, detalle = '') => {
  if (condicionado) { hechos++; console.log('  ok  ' + etiqueta); }
  else { fallos++; console.log('  NO  ' + etiqueta + (detalle ? ' → ' + detalle : '')); }
};
const ruta = t => clasificarOrden(t).ruta;
const accion = t => clasificarOrden(t).accion;

console.log('\n[1] órdenes del ejecutor: enrutadas, no regaladas al cerebro');
for (const [frase, nombre] of [
  ['apunta que llego a las 6', 'nota'],
  ['anota comprar tinta', 'nota'],
  ['recuerda que Joao es mi hermano', 'nota'],
  ['tengo que ir al ambulatorio', 'pendiente'],
  ['abre la calculadora', 'abrir'],
  ['abre la carpeta Documentos', 'abrir'],
  ['lanza el archivo informe.pdf', 'abrir'],
  ['reproduce Brooklyn Blood', 'musica'],
  ['pon música de Dark Rose', 'musica'],
  ['pausa', 'reproductor'],
  ['adelanta 10 segundos', 'reproductor'],
  ['siguiente', 'reproductor'],
  ['¿qué suena?', 'que-suena'],
  ['dónde voy', 'que-suena'],
  ['lee mis notas', 'leer'],
  ['busca recetas con pollo', 'busca'],
  ['limpia la caché', 'limpiar'],
  ['cuánta RAM estamos usando', 'sistema'],
  ['estado del equipo', 'sistema'],
  ['enciende ollama', 'ollama'],
  ['¿cuáles son los modelos?', 'modelos-lista'],
  ['muéstrame los modelos', 'modelos-lista'],
  ['usa qwen2.5:3b', 'modelo'],
]) ok(`orden «${frase}» → ${nombre}`, ruta(frase) === 'orden' && accion(frase) === nombre,
     `volvieron ${ruta(frase)}/${accion(frase)}`);

console.log('\n[2] la conversación queda intacta');
for (const frase of [
  'hola cort', '¿qué día es hoy?', '¿qué hora es?',
  'cuéntame un chiste', 'narra una historia de la ubrea',   // trampa: `cuéntame`/`narra` son charla a propósito
  'explícame el ciclo de la urea', '¿qué recuerdas de mí?',
  'me llamo Sandra', '', '   ',
]) ok(`charla «${frase || '(vacío)'}»`, ruta(frase) === 'charla',
      `se fue a ${accion(frase)}`);

console.log('\n[3] la orden imposible TAMBIÉN se enruta (el «no pude» lo dice el núcleo)');
for (const [frase, nombre] of [
  ['abre la carpeta que no existe', 'abrir'],
  ['reproduce la canción de la que nunca oí hablar', 'musica'],
  ['apunta', 'charla'],                       // sin resto de frase no es orden: «apunta» solo es ruido
]) {
  if (nombre === 'charla') ok(`«${frase}» no finge una orden a medias`, ruta(frase) === 'charla');
  else ok(`«${frase}» → ${nombre}`, ruta(frase) === 'orden' && accion(frase) === nombre);
}

console.log('\n[4] el contrato del vocabulario');
const nombres = VOCABULARIO_ORDENES.map(v => v.nombre);
ok(`nombres únicos (${nombres.length})`, new Set(nombres).size === nombres.length);
ok('todas las regex compilan', VOCABULARIO_ORDENES.every(v => { try { new RegExp(v.fuente, 'i'); return true; } catch { return false; } }));
const py = readFileSync(join(raiz, 'backend/app/actions.py'), 'utf8');
/* El verbo tiene que estar ALSO en el núcleo, o la cara enrutaría a una ruta que no
   lo conoce. Pero `actions.py` lo escribe con clase de acento —`cu[aá]nta`, no
   «cuánta»—, así que la comparación literal mentía. Se aplana el andamio de regex
   (`[ ]`, `\`, espacios `\s+`) y se comparan las dos letras sin tilde: sigue sin
   encontrar un verbo inventado, y ahora encuentra el que ella sí tiene. */
const aplana = s => s.replace(/\[[^\]]*\]/g, m => m.slice(1, -1).replace(/\\/g, ''))
                     .replace(/\\s\+/g, ' ').replace(/\\/g, '');
// misma transformación para los dos lados: sin tildes, sin mayúsculas y con las
// letras repetidas juntas («cu[aá]nta» → «cunta», «cuánta» → «cunta»).
const mocho = s => aplana(s).normalize('NFD').replace(/[\u0300-\u036f]/g, '')
                    .toLowerCase().replace(/(.)\1+/g, '$1');
const pyPlano = mocho(py);
for (const verbo of ['apunta', 'abre', 'reproduce', 'pausa', 'lee', 'limpia', 'ollama', 'cuánta', 'estado del equipo']) {
  ok(`el verbo «${verbo}» existe también en actions.py`, pyPlano.includes(mocho(verbo)));
}
ok('y un verbo que el núcleo no tiene NO pasa', !pyPlano.includes('zarandajas'));

console.log('\n[5] la costura en la cara (`pantallas.js`)');
const js = cara(join(raiz, 'ui', 'js'));   // el POST y el chip los escribe la Charla
ok('la cara importa la regla', /import \{ clasificarOrden \} from '\.\/ordenes\.js'/.test(js));
ok('la orden viaja a /api/command', /await fetch\(ctx\.api\(\) \+ '\/api\/command'/.test(js));
ok('el payload es {message}, como exige la ruta', /body: JSON\.stringify\(\{ message: pregunta \}\)/.test(js));
ok('el chip se pinta sólo desde m.hecho', /Array\.isArray\(m\.hecho\)[\s\S]{0,120}hizo: /.test(js));
ok('la nota del ejecutor sale del done, no de la cara', /nota: hecho\.length \? 'ejecutor · '/.test(js));
ok('el adjunto no se desvía a la orden', /modo\.id === 'normal' && !habiaAdjunto \? clasificarOrden/.test(js));
ok('un modo elegido sigue siendo charla', js.includes("const orden = modo.id === 'normal'"));
ok('el fallo del núcleo se nombra en ámbar', /const falló = \/no pude\|no hay\|no encontr/.test(js));
const css = readFileSync(join(raiz, 'ui/css/apps.css'), 'utf8');
ok('el chip tiene su color de ejecutor, no de modo', /\.bur-hecho\{color:#6fdc8c/.test(css));

console.log(fallos ? `\nFALTA ${fallos} COSA(S)` : `\ntodo en orden: la superficie A distingue hablar de ejecutar (${hechos})`);
process.exit(fallos ? 1 : 0);
