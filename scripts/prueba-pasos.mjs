/* scripts/prueba-pasos.mjs — la máquina de estados del hilo del copiloto (J2.3)
 *
 * `ui/js/pasos.js` decide qué se puede tocar en cada paso del plan. Aquí se prueba lo
 * que en la cara no se ve pero se paga caro: el doble toque que corre un comando dos
 * veces, el verde que se le escapa a un paso no seguro, y el «rechazado» que debería
 * ser terminal. Sin DOM, sin red, sin teléfono.
 *
 * Uso:  node scripts/prueba-pasos.mjs
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { ESTADOS_PASO, puedeAceptar, puedeRechazar, puedeCopiar, arranca, rechaza, cierra,
         resumenPasos } from '../ui/js/pasos.js';
import { cara } from './lib-cara.mjs';

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..');
let fallos = 0, hechos = 0;
const ok = (t, c, d = '') => { if (c) { hechos++; console.log('  ok  ' + t); }
  else { fallos++; console.log('  NO  ' + t + (d ? ' → ' + d : '')); } };
const paso = (x = {}) => ({ indice: 0, orden: 'df -h', seguro: true, estado: 'pendiente', ...x });

console.log('\n[1] la tabla de estados');
ok('los seis estados tienen su color y su palabra',
   Object.keys(ESTADOS_PASO).length === 6
   && Object.values(ESTADOS_PASO).every(e => /^#[0-9a-f]{6}$/i.test(e.color) && e.dice));
ok('el verde y el rojo no comparten color (en el teléfono se miran con el pulgar)',
   ESTADOS_PASO.ok.color !== ESTADOS_PASO.rechazado.color
   && ESTADOS_PASO.falló.color !== ESTADOS_PASO.ok.color);
ok('rechazar se lee distinto que «aún no»', ESTADOS_PASO.rechazado.dice.includes('tuyo'));

console.log('\n[2] el verde: sólo pasos seguros y pendientes');
ok('un paso seguro y pendiente sí se puede aceptar', puedeAceptar(paso()) === true);
ok('uno NO seguro jamas (la puerta la custodia copiloto.py)',
   puedeAceptar(paso({ seguro: false })) === false);
ok('un paso ya corrido no se vuelve a ejecutar', puedeAceptar(paso({ estado: 'ok' })) === false);
ok('un paso rechazado no se puede-arrepentir con un toque',
   puedeAceptar(paso({ estado: 'rechazado' })) === false);
ok('mientras corre, no se toca (doble toque = comando dos veces)',
   puedeAceptar(paso({ estado: 'corriendo' })) === false);
ok('un paso sin objeto no se acepta', puedeAceptar(undefined) === false);

console.log('\n[3] el rojo: siempre a mano, y terminal');
ok('se puede rechazar un pendiente', puedeRechazar(paso()) === true);
ok('y también uno que sólo se enseñó', puedeRechazar(paso({ estado: 'enseñado', seguro: false })) === true);
ok('no se rechaza lo que ya está corriendo', puedeRechazar(paso({ estado: 'corriendo' })) === false);
const r = paso();
ok('rechazar lo deja en `rechazado`', rechaza(r) === 'rechazado' && r.estado === 'rechazado');
ok('y deja escrito el motivo, no un silencio', /no lo ejecuté/.test(r.resultado.dice));
ok('después del rojo el verde está muerto', puedeAceptar(r) === false && arranca(r) === 'rechazado');
ok('rechazar dos veces no cambia nada', rechaza(r) === 'rechazado');

console.log('\n[4] el cierre: lo que dice el núcleo, traducido sin adornos');
const a = paso(); arranca(a);
ok('arrancar lo pone en `corriendo`', a.estado === 'corriendo');
ok('ejecutado + ok → `ok`', (() => { const p = paso(); arranca(p);
   return cierra(p, { ejecutado: true, ok: true }) === 'ok'; })());
ok('ejecutado + !ok → `falló` (no se disfraza de enseñado)', (() => { const p = paso(); arranca(p);
   return cierra(p, { ejecutado: true, ok: false }) === 'falló'; })());
ok('el núcleo dice que NO ejecutó → `enseñado`, que no es «hizo»', (() => {
   const p = paso(); arranca(p); return cierra(p, { ejecutado: false, ok: false, dice: 'requiere permiso' }) === 'enseñado'; })());
ok('la salida del comando se guarda para enseñarla', (() => {
   const p = paso(); arranca(p); cierra(p, { ejecutado: true, ok: true, salida: 'Filesystem  1K-blocks' });
   return p.resultado.salida.includes('1K-blocks'); })());
ok('cerrar un paso que no estaba corriendo no lo toca', cierra(paso({ estado: 'rechazado' }), { ejecutado: true, ok: true }) === 'rechazado');

console.log('\n[5] el resumen del hilo');
const lote = [paso({ estado: 'ok' }), paso({ estado: 'pendiente' }), paso({ estado: 'rechazado' }),
              paso({ estado: 'enseñado', seguro: false })];
const c = resumenPasos(lote);
ok('cuenta por estado, sin inventarse ninguno', c.ok === 1 && c.pendiente === 1 && c.rechazado === 1 && c.enseñado === 1);
ok('un lote vacío no rompe', Object.keys(resumenPasos([])).length === 0);
ok('copiar siempre se puede si hay comando', puedeCopiar(paso()) && !puedeCopiar(paso({ orden: '' })));

console.log('\n[6] la costura en la cara');
/* Desde el corte 4 la máquina de estados la usa `codigo.js`, no la carcasa. Se lee la
   cara entera —la MISMA lista que lee `prueba-costura.py`— para que la comprobación
   signifique «el hilo del copiloto está cosido a la cara» y no «en qué archivo vive
   hoy». Las cadenas exigidas no cambian ni una. */
const js = cara(join(raiz, 'ui/js'));
ok('la cara importa la máquina de estados', /from '\.\/pasos\.js'/.test(js));
ok('el plan nace con su estado (seguro→pendiente, no seguro→enseñado)',
   /estado: p\.seguro \? 'pendiente' : 'enseñado'/.test(js));
ok('el verde pasa por `arranca` antes de tocar la red', /if \(arranca\(paso\) !== 'corriendo'\) return;/.test(js));
ok('el resultado pasa por `cierra`', /cierra\(paso, j\)/.test(js));
ok('un corte del núcleo es `falló`, no `enseñado`', /paso\.estado = 'falló';/.test(js));
ok('el rojo está en el hilo', /data-rechaza=/.test(js) && /rechaza\(p\) !== 'rechazado'/.test(js));
ok('el botón de lote cuenta sólo los pendientes de ahora',
   /p\.seguro && p\.estado === 'pendiente'/.test(js));
const css = readFileSync(join(raiz, 'ui/css/hud.css'), 'utf8');
ok('el rojo tiene su estilo y su separación del verde', /\.cp-b\.rojo\{[^}]*margin-left:6px/.test(css));
ok('y el estado pintado tiene su clase', /\.cp-est\{/.test(css));

console.log(fallos ? `\nFALTA ${fallos} COSA(S)` : `\ntodo en orden: el hilo tiene sus dos botones y sus estados de verdad (${hechos})`);
process.exit(fallos ? 1 : 0);
