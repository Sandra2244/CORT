#!/usr/bin/env node
/* ===== prueba del MARCO de las pantallas (`ui/js/marco.js`) =====

   Segundo corte de la refactorización por tamaño (la regla de la dueña: «la interfaz debe
   ser mil líneas máximo y si necesitas crear otros de otras líneas más conectas y divides
   entre si pero que funcione correctamente»). Aquí se fue lo que todas las hojas miraban:
   el `ctx` vivo, el puente de Java, la tabla de hojas, las bottom sheets, el cajón, la
   pregunta «¿hay núcleo?» y el router `ir()`.

   No lee el archivo y lo aprueba por la palabra: **ejecuta `marco.js` de verdad** contra una
   pantalla y un puente de pega, le da las órdenes con las que juega la dueña (entrar en una
   hoja, deslizar, abrir el cajón, copiar una letra) y mira qué pasa. Con veintinueve
   `export` hay mucho que se puede romper sin que ningún texto lo note: un `Map` mal
   recorrido, un gancho registrado dos veces, o un `export let` que alguien asigna de fuera.

   Por qué hace falta aparte de `prueba-costura.py`: la de costura comprueba que las piezas
   **se nombran lo mismo** (Java ↔ cara ↔ núcleo). Ésta comprueba el **comportamiento** del
   marco, que es lo otro que falla en silencio y que en el teléfono no se ve: Chromium no da
   consola, y un `ir()` que no despache los registros abre hojas vacías.

   Sectores:
     [1] el módulo se ejecuta: no toca el DOM al cargarse y exporta lo que promete
     [2] `ir()`: la clase de la hoja, el orden de los ganchos y el evento
     [3] `ir()` con una id desconocida: cae al Orbe, no revienta
     [4] `abreCajon()`: repinta y abre; cambiar de hoja cierra
     [5] `montables()` / `visibles()`: el teléfono, el puente que falta y lo escondido
     [6] `puede()` / `llama()`: el `typeof` del APK viejo y el `try/catch` del puente
     [7] `ctx` es un enlace VIVO: quien lo importa ve el cambio sin re-importar
     [8] `hayNucleo()`: el éxito se recuerda, el fallo se vuelve a intentar
     [9] `abreHoja()`: una instancia viva, y `hayHoja()`
    [10] `copia()`: el portapapeles async y la reserva por `execCommand`
    [11] `mueve()`: el deslizamiento recorre `visibles()` en círculo

   Uso:  node scripts/prueba-marco.mjs
*/
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const RA = join(dirname(fileURLToPath(import.meta.url)), '..');
let fallos = 0, hechos = 0;
const ok = (etiqueta, condicionado, detalle = '') => {
  if (condicionado) { hechos++; console.log('  ok  ' + etiqueta); }
  else { fallos++; console.log('  NO  ' + etiqueta + (detalle ? ' → ' + detalle : '')); }
};

/* ─────────────────────────── la pantalla y el puente de pega ───────────────────
   Sin `document` no hay marco que valga, pero sin una pantalla de verdad tampoco hace
   falta: al módulo sólo le interesan las clases de `<html>`, los nodos que crea para la
   hoja, y si el puente está o no. Nada de Three.js ni de WebGL: eso lo prueba
   `prueba-orbe-cara.mjs`. */
class Lista {
  constructor(nodos) { this.n = new Set(nodos || []); }
  add(...c) { c.forEach(x => this.n.add(x)); }
  remove(...c) { c.forEach(x => this.n.delete(x)); }
  contains(c) { return this.n.has(c); }
  toString() { return [...this.n].join(' '); }
}
const nodo = (clases = []) => {
  const el = {
    classList: new Lista(clases), className: clases.join(' '),
    children: [], style: {}, value: '', textContent: '',
    appendChild(h) { h._padre = this; this.children.push(h); return h; },
    remove() { this._padre?.removeChild(this); },
    removeChild(h) { this.children = this.children.filter(x => x !== h); },
    querySelector: () => nodo(), querySelectorAll: () => [],
    setAttribute() {}, focus() {}, select() {},
  };
  return el;
};
const html = nodo(['sin-movimiento']);
/* `pon` en vez de `globalThis.x = …` a secas: desde Node 21 `navigator` vive en el
   global como un `get` sin `set`, y en el runner (Node 24, el aviso lo pone GitHub)
   `globalThis.navigator = {}` revienta con «Cannot set property navigator of
   #<Object> which has only a getter». Aquí pasa en Node 20 y en Actions con 24, así
   que se define con `defineProperty`, que vale en las dos. */
const pon = (nombre, valor) =>
  Object.defineProperty(globalThis, nombre, { value: valor, writable: true, configurable: true });
globalThis.document = {
  documentElement: html, body: nodo(), createElement: () => nodo(),
  getElementById: () => null, querySelector: () => null, execCommand: () => true,
};
const eventos = [];
globalThis.CustomEvent = class { constructor(t, d) { this.type = t; Object.assign(this, d || {}); } };
globalThis.window = {
  isSecureContext: true, dispatchEvent: e => { eventos.push(e); return true; },
  addEventListener: () => {}, CortNative: null,
};
pon('navigator', {});
globalThis.localStorage = { getItem: () => null, setItem: () => {} };
globalThis.requestAnimationFrame = fn => fn();
globalThis.setTimeout = fn => { fn(); return 0; };
globalThis.AbortSignal = { timeout: () => null };

const M = await import('../ui/js/marco.js');

/* ─── [1] el módulo se ejecuta y exporta lo que promete ─── */
console.log('\n[1] el marco se carga antes de que exista la cara');
ok('es un módulo ES que no toca el DOM al cargarse', typeof M.ir === 'function');
const promesas = ['N', 'enTelefono', 'puede', 'llama', 'ctx', 'ponCtx', 'actual', 'nucleo',
  'PANTALLAS', 'montables', 'visibles', 'TINTE', 'abreHoja', 'cierraHoja', 'hayHoja',
  'hayNucleo', 'sinNucleoFrase', 'fraseSinNucleo', 'avisaSinNucleo', 'copia', 'reserva',
  'alEntrar', 'alCerrar', 'alRepintar', 'alPintar', 'ir', 'pantallaActual', 'mueve', 'abreCajon'];
const faltan = promesas.filter(n => !(n in M));
ok('y están los ' + promesas.length + ' nombres que importan la carcasa y las hojas',
   faltan.length === 0, faltan.join(', '));
const js = readFileSync(join(RA, 'ui/js/marco.js'), 'utf8');
ok('no importa ninguna hoja: el marco no sabe quién existe, y así no hay círculo',
   !/from '\.\/(pantallas|charla|musica|mv|codigo)\.js'/.test(js));

/* ─── [2] `ir()`: la clase, el orden de los ganchos y el evento ─── */
console.log('\n[2] el cambio de hoja ejecuta los ganchos en orden');
const bitácora = [];
M.alCerrar(() => bitácora.push('cerrar'));
M.alRepintar(() => bitácora.push('repintar'));
M.alPintar(() => bitácora.push('pintar'));
M.alEntrar('charla', () => bitácora.push('entrar-charla'));
M.alEntrar('centro', () => bitácora.push('entrar-centro'));
eventos.length = 0;
bitácora.length = 0;
M.ir('charla');
bitácora.length = 0;                      // lo que se mide es ESTE cambio, no el anterior
M.ir('centro');
ok('quita la clase de la hoja anterior y pone la de la nueva',
   !html.classList.contains('p-charla') && html.classList.contains('p-centro'), String(html.classList));
ok('arranca SOLO la hoja que toca, no todas',
   bitácora.includes('entrar-centro') && !bitácora.includes('entrar-charla'), bitácora.join(' → '));
ok('el orden es cerrar → repintar → entrar → pintar',
   bitácora.slice(-4).join(' → ') === 'cerrar → repintar → entrar-centro → pintar',
   bitácora.join(' → '));
ok('avisa a `hud.js` con el evento y el id de la hoja',
   eventos.at(-1)?.type === 'cort-pantalla' && eventos.at(-1)?.detail === 'centro');
bitácora.length = 0;
M.alEntrar('centro', () => bitácora.push('segunda'));   // re-registrar: el Map pisa, no suma
M.ir('centro');
ok('una hoja registrada dos veces se arranca UNA vez (es un `Map`, no una lista)',
   bitácora.filter(x => x === 'segunda').length === 1 && !bitácora.includes('entrar-centro'),
   bitácora.join(' → '));

/* ─── [3] una hoja que no existe ─── */
console.log('\n[3] una id desconocida no revienta: cae al Orbe');
bitácora.length = 0;
M.ir('no-existe');
ok('se queda en `orbe`, que es la hoja que siempre está',
   M.pantallaActual() === 'orbe' && html.classList.contains('p-orbe'), M.pantallaActual());
ok('y no arranca el registro de otra hoja', !bitácora.includes('segunda'), bitácora.join(' → '));

/* ─── [4] el cajón ─── */
console.log('\n[4] el botón ☰ de cualquier hoja');
M.alCerrar(() => html.classList.remove('cajon-abierto'));   // lo que registra la carcasa
bitácora.length = 0;
M.abreCajon();
ok('abre el cajón poniendo su clase en `<html>`', html.classList.contains('cajon-abierto'));
ok('y antes de abrirlo repinta lo registrado: el cajón tiene que ofrecer el puente ACTUAL',
   bitácora.includes('repintar'), bitácora.join(' → '));
M.ir('charla');
ok('cambiar de hoja lo cierra, sin que cada hoja tenga que acordarse',
   !html.classList.contains('cajon-abierto'));

/* ─── [5] qué hojas se montan y cuáles se ofrecen ─── */
console.log('\n[5] montables frente a visibles');
const ids = M.PANTALLAS.map(p => p.id);
ok('la tabla tiene las ocho hojas, sin duplicadas',
   ids.length === new Set(ids).size && ['orbe', 'musica', 'mv', 'charla', 'codigo',
     'equipo', 'centro', 'arnes'].every(i => ids.includes(i)), ids.join(','));
ok('sin puente no se monta Música, Letra ni Equipo: son del teléfono',
   M.montables().every(p => !p.telefono), M.montables().map(p => p.id).join(','));
globalThis.window.CortNative = { accion: () => 'ok' };   // teléfono con el contrato 2.1
ok('la hoja escondida se MONTA (el botón «letra» tiene que tener adónde ir) pero no se ofrece',
   M.montables().some(p => p.escondida) && !M.visibles().some(p => p.escondida),
   M.visibles().map(p => p.id).join(','));
ok('y `ir()` entra en ella aunque no esté en el cajón',
   (M.ir('mv'), M.pantallaActual() === 'mv'), M.pantallaActual());
globalThis.window.CortNative = {};           // teléfono con un APK viejo
ok('un APK viejo con puente a medias no ofrece Equipo: pregunta su método antes de ofrecerlo',
   !M.montables().some(p => p.id === 'equipo'), M.montables().map(p => p.id).join(','));
globalThis.window.CortNative = { accion: () => 'ok' };
ok('y con el método del contrato 2.1 puesto, la hoja aparece',
   M.montables().some(p => p.id === 'equipo'));
globalThis.window.CortNative = null;

/* ─── [6] el puente de Java ─── */
console.log('\n[6] `puede()` y `llama()`, con el APK de siempre delante');
ok('sin puente, `puede` dice que no y `llama` devuelve `null` en vez de reventar',
   M.puede('musicaPoner') === false && M.llama('musicaPoner', 'x') === null);
let oido = null;
globalThis.window.CortNative = { musicaPoner: v => { oido = v; return 'ok'; } };
ok('con el método puesto, la llamada llega y trae la respuesta',
   M.puede('musicaPoner') === true && M.llama('musicaPoner', '3') === 'ok' && oido === '3');
globalThis.window.CortNative = { rompo: () => { throw new Error('Java tosió'); } };
ok('y si Java lanza, lo que se oye es el terminal, no un `TypeError` en la consola',
   M.llama('rompo') === null);
globalThis.window.CortNative = null;

/* ─── [7] `ctx` es un enlace vivo ─── */
console.log('\n[7] el `export let` que evitó reescribir el millar de `ctx?.term?.()`');
ok('al importarlo, `ctx` empieza vacío (nadie ha montado la cara todavía)', M.ctx === null);
M.ponCtx({ term: () => {}, say: () => {} });
ok('después de `ponCtx`, el mismo nombre que ya se importó trae el contexto', M.ctx !== null);
let ruido = [];
globalThis.window.CortNative = { otra: () => 'sí hay puente' };   // APK sin ese método
M.ponCtx({ term: t => ruido.push(t), say: () => {} });
ok('un APK que no trae el método devuelve `null` EN SILENCIO: el `typeof` es lo que evita '
   + 'que la cara se ponga a contar TypeErrors a una hoja que no existe',
   M.llama('musicaPoner') === null && ruido.length === 0, ruido.join(' | '));
globalThis.window.CortNative = null;
M.ponCtx({ term: (t, q) => bitácora.push(q), say: () => {} });
let tiro = null;
try { M.ctx = { term: () => {} }; } catch (e) { tiro = e.constructor.name; }
/* Medido aquí, no por la teoría: el objeto de espacio de nomes no es un objeto normal —el
   descriptor dice `writable: true` y aun así el `[[Set]]` lanza—. Lo que le importa a la
   cara es que un intento de poner un `ctx` de pega desde fuera se corte en seco. */
ok('y desde fuera NO se puede asignar: el enlace importado lanza, así que nadie puede poner '
   + 'un `ctx` de pega',
   tiro === 'TypeError' && M.ctx && typeof M.ctx.term === 'function', String(tiro));
bitácora.length = 0;
M.ponCtx({ term: (t, q) => bitácora.push(q), say: () => {} });
M.ir('charla');
ok('el cambio de hoja se anota en el terminal con el módulo de siempre',
   bitácora.includes('pantallas'), bitácora.join(','));

/* ─── [8] ¿hay núcleo? ─── */
console.log('\n[8] la pregunta del portátil: el sí se recuerda, el no se vuelve a intentar');
let peticiones = 0;
M.ponCtx({ api: () => 'http://192.168.1.9:8123', term: () => {}, say: () => {} });
globalThis.fetch = async () => { peticiones++; throw new Error('sin red'); };
ok('si el portátil no responde, `hayNucleo` da `false` (no `undefined`: las frases lo distinguen)',
   (await M.hayNucleo()) === false);
await M.hayNucleo();
ok('y no se queda dormida en el fallo: sin éxito vuelve a preguntar, que es cuando despierta el PC',
   peticiones === 2, 'peticiones=' + peticiones);
globalThis.fetch = async () => { peticiones++; return { ok: true, status: 200 }; };
const base = await M.hayNucleo();
const antes = peticiones;
await M.hayNucleo(); await M.hayNucleo();
ok('la respuesta buena queda guardada: una sola petición para siempre',
   base === 'http://192.168.1.9:8123' && peticiones === antes, 'peticiones=' + peticiones);
const aviso = nodo();
await M.avisaSinNucleo(aviso);
ok('y `avisaSinNucleo` pone el rótulo de «listo» sin volver a la red',
   peticiones === antes && aviso.textContent === 'núcleo listo'
   && !aviso.classList.contains('aviso'), aviso.textContent);
globalThis.window.CortNative = {};
ok('en el teléfono la frase habla del portátil apagado, y `fraseSinNucleo` dice la misma',
   M.sinNucleoFrase().includes('portátil') && M.fraseSinNucleo() === M.sinNucleoFrase());
globalThis.window.CortNative = null;
ok('en el PC es otra frase, porque allí no hay puente que abrir: se arranca el núcleo',
   M.sinNucleoFrase().includes('scripts/run'), M.sinNucleoFrase());

/* ─── [9] las bottom sheets ─── */
console.log('\n[9] una hoja encima de la pantalla');
ok('no hay hoja viva al principio', M.hayHoja() === false);
const raiz = M.abreHoja({ titulo: 'Ordenar', html: '<div>x</div>' });
ok('abrir una hoja la construye con su asidero, su título y su ✕',
   raiz.className === 'hoja' && raiz.innerHTML.includes('hoja-asidero')
   && raiz.innerHTML.includes('Ordenar'), raiz.className);
ok('y la pone por delante y la marca como abierta',
   M.hayHoja() === true && raiz.classList.contains('abierta'));
M.abreHoja({ titulo: 'Más', html: '<div>y</div>' });
ok('abrir otra deja UNA sola hoja viva: dos apiladas en 5 pulgadas es un accidente',
   M.hayHoja() === true && document.body.children.filter(c => c.className === 'hoja').length === 1);
M.cierraHoja();
ok('y cerrada ya no queda nada vivo', M.hayHoja() === false);

/* ─── [10] el portapapeles ─── */
console.log('\n[10] copiar, que en el WebView no siempre se puede');
let dicho = null;
M.ponCtx({ term: () => {}, say: t => { dicho = t; } });
let asyncOk = false;
globalThis.navigator.clipboard = { writeText: async () => { asyncOk = true; } };
M.copia('hola');
await new Promise(r => setImmediate(r));
ok('con portapapeles async, ése es el camino', asyncOk && dicho === 'Copiado.', String(dicho));
dicho = null;
globalThis.navigator.clipboard = { writeText: async () => { throw new Error('prohibido'); } };
M.copia('hola', 'Letra copiada.');
await new Promise(r => setImmediate(r));
ok('y si el WebView lo prohíbe, cae en el campo invisible con `execCommand` sin quedarse muda',
   dicho === 'Letra copiada.', String(dicho));
globalThis.document.execCommand = () => { throw new Error('tampoco'); };
dicho = null;
M.copia('hola');
await new Promise(r => setImmediate(r));
ok('si tampoco, la dueña recibe una instrucción, no un silencio',
   dicho === 'No pude copiarlo: selecciónalo con el dedo.', String(dicho));

/* ─── [11] deslizar ─── */
console.log('\n[11] el dedo de lado a lado');
const lista = M.visibles().map(p => p.id);
M.ir(lista[0]);
M.mueve(1);
ok('un deslizamiento lleva a la siguiente hoja OFRECIDA',
   M.pantallaActual() === lista[1], M.pantallaActual());
M.ir(lista.at(-1));
M.mueve(1);
ok('y el último, con un paso más, vuelve al principio (no se sale de la lista)',
   M.pantallaActual() === lista[0], M.pantallaActual());
M.ir(lista[2]);
M.mueve(-1);
ok('hacia atrás recorre la misma lista en sentido contrario',
   M.pantallaActual() === lista[1], M.pantallaActual());
ok('nunca cae en una hoja escondida: el deslizamiento usa `visibles()`',
   !lista.some(i => M.PANTALLAS.find(p => p.id === i)?.escondida), lista.join(','));

console.log(fallos ? `\nROJO · ${hechos} hechos, ${fallos} fallos`
                   : `\ntodo en orden: el marco cambia de hoja, pregunta y copia sin la cara delante (${hechos})`);
process.exit(fallos ? 1 : 0);
