#!/usr/bin/env node
/* Prueba del ORBE NUEVO (`ui/js/orbe-plexo.js`), sin WebGL, sin navegador y sin
 * teléfono.
 *
 * Paso 1.1 de la Fase 1 nueva (ver `docs/PLAN-FASE-1.md`). Lo que se juega aquí es el
 * argumento del rediseño: que el orbe de la referencia sea MÁS BARATO que el actual.
 * En un CI no hay GPU, así que se mide lo que sí se puede medir:
 *   · la geometría (puntos repartidos de verdad, aristas sin duplicados, y que se
 *     calcule UNA vez y no por frame),
 *   *  el presupuesto (número de puntos, de líneas y de dibujos),
 *   · los colores por estado (hex válidos y distinguibles),
 *   · que `creaOrbe` monte y anime con un THREE de mentira: eso caza el error tonto
 *     que apaga la cara, el identificador que no existe.
 *
 * Lo que NO prueba: cómo se ve (eso lo ve la dueña en `ui/sonda-orbe.html`) ni los
 * fps reales (se miden en el portátil y van al informe del paso).
 *
 * Uso:  node scripts/prueba-orbe.mjs     (una fracción de segundo)
 */
import { readFile } from 'node:fs/promises';
import {
  N_PUNTOS, VECINOS, RADIOS, GRANO, ESTADOS, ESTADO_INICIAL,
  RITMOS, formaDelVortice, GIRO,
  puntosFibonacci, aristasCercanas, creaOrbe, SHADERS,
} from '../ui/js/orbe-plexo.js';
import { estados as coloresDelTraje, POR_DEFECTO } from '../ui/js/traje.js';

let fallos = 0, hechos = 0;
const ok = (etiqueta, condicionado, detalle = '') => {
  if (condicionado) { hechos++; console.log('  ok  ' + etiqueta); }
  else { fallos++; console.log('  NO  ' + etiqueta + (detalle ? ' → ' + detalle : '')); }
};
const HEX = /^#[0-9a-f]{6}$/i;

/* ---------- [1] los puntos ---------- */
console.log('\n[1] los puntos sobre la esfera');
const g = puntosFibonacci();
ok('llegan de tres en tres', g.pos.length === N_PUNTOS * 3, `${g.pos.length} floats`);
ok('uno por punto, la fase de su onda', g.fase.length === N_PUNTOS);
let radioMin = Infinity, radioMax = -Infinity;
for (let i = 0; i < N_PUNTOS; i++) {
  const r = Math.hypot(g.pos[i * 3], g.pos[i * 3 + 1], g.pos[i * 3 + 2]);
  radioMin = Math.min(radioMin, r); radioMax = Math.max(radioMax, r);
}
// El orbe del video NO es una esfera perfecta: es un bulto. `GRANO` desplaza cada
// punto dentro y fuera, y esta comprobación vigila que se quede en la banda prometida
// (ni una esfera, ni una explosión).
ok('dentro de la banda de grano prometida',
   radioMin >= 1 - GRANO / 2 - 1e-5 && radioMax <= 1 + GRANO / 2 + 1e-5,
   `mín ${radioMin.toFixed(4)} máx ${radioMax.toFixed(4)} · grano ±${(GRANO / 2).toFixed(3)}`);
let masCercanas = Infinity;
for (let i = 0; i < N_PUNTOS; i++) {
  for (let j = i + 1; j < N_PUNTOS; j++) {
    const d = Math.hypot(g.pos[i * 3] - g.pos[j * 3], g.pos[i * 3 + 1] - g.pos[j * 3 + 1],
                         g.pos[i * 3 + 2] - g.pos[j * 3 + 2]);
    if (d < masCercanas) masCercanas = d;
  }
}
// Con un `Math.random()` dos puntos caerían casi encima; la retícula de Fibonacci no.
// El listón (0.07) sale de la cuenta: 220 puntos sobre la esfera dan un vecino medio a
// ~0,13, y el grano puede recortar eso a la mitad en el peor par.
ok('sin grumos: el vecino más cercano no se pega', masCercanas > 0.07,
   `distancia mínima ${masCercanas.toFixed(3)}`);
const mismo = puntosFibonacci(), otraSemilla = puntosFibonacci(N_PUNTOS, RADIOS.esfera, 11);
ok('la misma semilla da el mismo orbe', g.pos.join() === mismo.pos.join() && g.fase.join() === mismo.fase.join());
ok('cambiar de semilla cambia el orbe entero (sitio y fase) sin romper la banda',
   otraSemilla.pos.join() !== g.pos.join() && otraSemilla.fase.join() !== g.fase.join());

/* ---------- [2] las aristas ---------- */
console.log('\n[2] las líneas entre vecinos');
const t0 = performance.now();
const aristas = aristasCercanas(g.pos);          // frío: paga el JIT del motor
const tFrio = performance.now() - t0;
const t1 = performance.now();
const otra = aristasCercanas(g.pos);           // caliente: lo que cuesta de verdad
const tGeom = performance.now() - t1;
ok('la geometría es determinista', aristas.join() === otra.join());
/* Aquí NO se prueba el tiempo. Medido en esta ronda sobre el portátil de la dueña
   (2 núcleos, con Qoder abierto): un bucle vacío del mismo orden de trabajo tardó entre
   20 y 40 ms según la carga, y `aristasCercanas` entre 2 y 60 ms en la MISMA máquina con
   el MISMO código. Una prueba que depende de cuánto esté ocupado el equipo se pone roja
   sola y deja de merecerse. Lo que sí se prueba es lo que hace barato al orbe y no
   depende del reloj: que la geometría se calcule una vez y no por frame (sector de
   `prueba-costura.py`), que no haya duplicados, y que el coste real —fps y % de núcleo
   dibujando— se mide en `ui/sonda-orbe.html`, que es donde se ve. */
let acc = 0;
const tCal0 = performance.now();
for (let i = 0; i < N_PUNTOS; i++) for (let j = 0; j < N_PUNTOS; j++) acc += i * j;
for (let i = 0; i < N_PUNTOS; i++) for (let m = 0; m < VECINOS; m++)
  for (let j = 0; j < N_PUNTOS; j++) acc += j;
const tCal = performance.now() - tCal0;
console.log(`  ·  geometría: ${tGeom.toFixed(1)} ms en caliente, ${tFrio.toFixed(1)} ms en frío · ` +
            `sonda del mismo orden de trabajo ${tCal.toFixed(1)} ms · se calcula UNA vez, al nacer`);
const n = aristas.length / 2;
/* El tipo del índice NO es opcional: con `Int32Array` Three.js le pide a OpenGL un tipo
   que no existe y las líneas no se dibujan. Medido en el navegador:
   `GL_INVALID_ENUM: glDrawElements`. En node no hay GL, así que se prueba el tipo. */
ok('los índices son Uint16Array (WebGL no sabe qué hacer con Int32)',
   aristas instanceof Uint16Array, aristas.constructor.name);
/* Presupuesto de líneas. Subió de 600 a 900 cuando el orbe pasó de 120 a 220 puntos:
   la bola de hilo del video está muy cruzada y con 322 líneas se leía como poliedro.
   Lo que sigue siendo barato no es el número en sí, que TODAS quepan en UN solo
   `LineSegments` (900 líneas = 1.800 vértices, frente a los 2.600 puntos + 1.280
   triángulos + rejilla + estrellas del orbe viejo). */
ok('presupuesto: menos de 900 líneas', n > 0 && n < 900, `${n} líneas`);
ok('y ninguna de más: ninguna pasa de los ' + VECINOS + ' vecinos pedidos',
   n <= N_PUNTOS * VECINOS, `${n} ≤ ${N_PUNTOS * VECINOS}`);
let malas = 0, bucles = 0;
const vistas = new Set();
let duplicadas = 0;
for (let e = 0; e < aristas.length; e += 2) {
  const [i, j] = [aristas[e], aristas[e + 1]];
  if (i >= j) malas++;
  if (i === j) bucles++;
  const clave = `${i}-${j}`;
  if (vistas.has(clave)) duplicadas++;
  vistas.add(clave);
}
ok('siempre i < j', malas === 0, `${malas} invertidas`);
ok('ningún punto se enlaza consigo mismo', bucles === 0);
ok('ninguna línea repetida', duplicadas === 0, `${duplicadas} duplicadas`);
const cubiertos = new Set([...aristas]);
ok('todos los puntos tienen línea', cubiertos.size === N_PUNTOS,
   `${cubiertos.size}/${N_PUNTOS}`);

/* ---------- [3] los estados ---------- */
console.log('\n[3] los estados y su color');
const CLAVE = ['reposo', 'escucha', 'piensa', 'habla', 'error'];
ok('los cinco estados de la cara están',
   CLAVE.every(k => ESTADOS[k]), CLAVE.filter(k => !ESTADOS[k]).join(','));
ok('el estado inicial no llama la atención', ESTADO_INICIAL === 'reposo');
for (const k of CLAVE) {
  const e = ESTADOS[k];
  ok(`${k}: colores válidos y numéricos`,
     HEX.test(e.a) && HEX.test(e.b) && e.opacidad > 0 && e.opacidad <= 1 &&
     e.empuje > 0 && e.giro >= 0, JSON.stringify(e));
}
const colores = CLAVE.map(k => ESTADOS[k].b);
ok('dos estados no comparten el color de las líneas',
   new Set(colores).size === colores.length, colores.join(' '));
ok('habla empuja más que reposo (el orbe se agita al hablar)',
   ESTADOS.habla.empuje > ESTADOS.reposo.empuje);
ok('pensar gira rápido (el remolino de la referencia)',
   ESTADOS.piensa.giro > ESTADOS.habla.giro);

/* ---------- [4] los shaders ---------- */
console.log('\n[4] los cuatro textos GLSL');
ok('hay cuatro y ninguno está vacío',
   Object.values(SHADERS).every(s => typeof s === 'string' && s.length > 80));
ok('el de los puntos declara uTamano y lo usa topeado',
   /uniform float uTamano;/.test(SHADERS.puntos) &&
   /gl_PointSize\s*=\s*clamp\(uTamano/.test(SHADERS.puntos));
ok('el de las líneas NO usa gl_PointSize (no existe en LineSegments)',
   !/gl_PointSize/.test(SHADERS.lineas));
ok('ambos declaran todo lo que usan',
   ['uTiempo', 'uNivel', 'uEmpuje', 'aFase', 'vBrillo'].every(u =>
     SHADERS.puntos.includes(u) && SHADERS.lineas.includes(u)));
ok('ningún uniform huérfano en el fragmento',
   /uniform vec3 uColorA;/.test(SHADERS.fragPuntos) && /uniform vec3 uColorB;/.test(SHADERS.fragLineas));
ok('no quedó ningún parcheo de cadena sin resolver',
   !/undefined/.test(SHADERS.puntos + SHADERS.lineas));
/* CANDADO, y no es teórico: un comentario con acentos graves metido DENTRO de una
   cadena GLSL cierra el literal antes de tiempo. El archivo seguía siendo JS válido
   (`node --check` lo daba por bueno) pero el módulo reventaba al importar y la cara
   quedaba en blanco sin decir nada —el mismo sabor que el import roto de la 2.10.0—. */
for (const [nombre, glsl] of Object.entries(SHADERS)) {
  ok(`${nombre}: sin acentos graves ni comentarios incrustados`,
     !glsl.includes('`') && !glsl.includes('/*') && !glsl.includes('*/'));
  ok(`${nombre}: llaves equilibradas`,
     (glsl.match(/{/g) || []).length === (glsl.match(/}/g) || []).length);
  ok(`${nombre}: termina con el cierre de main()`, /\}\s*$/.test(glsl));
}

/* ---------- [5] el orbe montado, con un THREE de mentira ---------- */
/* Suficiente para ejecutar el módulo de arriba abajo. Si mañana `creaOrbe` usa un
   método que el módulo no define, o un nombre que no existe, esto revienta aquí
   —que es exactamente como se cayó la cara entera en la 2.10.0—. */
class Color {
  constructor(v) { this.r = this.g = this.b = 1; if (v) this.set(v); }
  set(hex) { const s = String(hex).replace('#', '');
    this.r = parseInt(s.slice(0, 2), 16) / 255; this.g = parseInt(s.slice(2, 4), 16) / 255;
    this.b = parseInt(s.slice(4, 6), 16) / 255; return this; }
  copy(o) { this.r = o.r; this.g = o.g; this.b = o.b; return this; }
  clone() { return new Color().copy(this); }
  lerp(o, t) { this.r += (o.r - this.r) * t; this.g += (o.g - this.g) * t; this.b += (o.b - this.b) * t; return this; }
}
const obj3d = () => ({ children: [], rotation: { x: 0, y: 0, z: 0 },
  scale: { x: 1, y: 1, z: 1, set(a, b) { this.x = a; this.y = b; } },
  add(...h) { this.children.push(...h); } });
const THREE = {
  Color, Group: class { constructor() { Object.assign(this, obj3d()); } },
  BufferGeometry: class { constructor() { this.attrs = {}; }
    setAttribute(n, a) { this.attrs[n] = a; } getAttribute(n) { return this.attrs[n]; }
    setIndex(a) { this.index = a; } dispose() { this.dispuesto = true; } },
  BufferAttribute: class { constructor(a, i) { this.array = a; this.itemSize = i; } },
  Points: class { constructor(g, m) { this.geometry = g; this.material = m; } },
  LineSegments: class { constructor(g, m) { this.geometry = g; this.material = m; } },
  ShaderMaterial: class { constructor(o) { Object.assign(this, o); this.uniforms = o.uniforms; } dispose() {} },
  Sprite: class { constructor(m) { this.material = m; Object.assign(this, obj3d()); } },
  SpriteMaterial: class { constructor(o) { Object.assign(this, o); this.color = o.color; } dispose() {} },
  CanvasTexture: class { constructor(c) { this.canvas = c; } dispose() { this.dispuesto = true; } },
  AdditiveBlending: 2,
};
globalThis.document = { createElement: () => ({ width: 0, height: 0,
  getContext: () => ({ createRadialGradient: () => ({ addColorStop() {} }),
    fillRect() {}, set fillStyle(v) {} }) }) };

console.log('\n[5] `creaOrbe` de punta a punta, con THREE de mentira');
let orbe = null, armó = true, error = '';
try { orbe = creaOrbe(THREE); } catch (e) { armó = false; error = e.message; }
ok('monta sin lanzar', armó, error);
if (armó) {
  ok('tres dibujos y la geometría contada', orbe.cifras().dibujos === 3 &&
     orbe.cifras().puntos === N_PUNTOS && orbe.cifras().lineas === n,
     JSON.stringify(orbe.cifras()));
  ok('empieza en reposo', orbe.estado() === ESTADO_INICIAL);
  ok('un estado inventado no tumba nada', orbe.setEstado('marte') === false && orbe.estado() === 'reposo');
  ok('los cinco estados reales se ponen', CLAVE.every(k => orbe.setEstado(k) === true));
  let animó = true, e2 = '';
  try { for (let i = 0; i < 90; i++) orbe.pinta(1 / 30, i / 90); }
  catch (e) { animó = false; e2 = e.message; }
  ok('noventa frames de animación sin romperse', animó, e2);
  const u = orbe.objeto.children[0].material.uniforms;
  ok('el tiempo y el nivel avanzan en los uniforms', u.uTiempo.value > 2.5 && u.uNivel.value > 0.5,
     `t=${u.uTiempo.value.toFixed(2)} nivel=${u.uNivel.value.toFixed(2)}`);
  ok('un hilo dormido no hace saltar el orbe', (() => {
      const antes = u.uTiempo.value; orbe.pinta(9.5, 0);
      return u.uTiempo.value - antes < 0.2; })());   // topa en 0,1 s; el margen es coma flotante
  let borró = true; try { orbe.borrar(); } catch (e) { borró = false; }
  ok('libera la geometría y las texturas', borró && orbe.objeto.children[0].geometry.dispuesto === true);
  const flojo = creaOrbe(THREE, { modo: 'bajo' });
  ok('el modo bajo (para el teléfono) deja 2 dibujos', flojo.cifras().dibujos === 2 &&
     flojo.objeto.children.length === 2, String(flojo.objeto.children.length));
}

/* ---------- [6] lo que hace barato al orbe, en el texto del módulo ----------
   En vez de medir relojes, se comprueba la estructura: si la geometría se reconstruye
   por frame, el orbe es caro por mucho que el equipo esté descansado. Este sector es
   determinista y no se pone rojo porque sí. */
console.log('\n[6] el presupuesto, leído en el código');
const fuente = await readFile(new URL('../ui/js/orbe-plexo.js', import.meta.url), 'utf8');
/* Se leen los comentarios fuera: este módulo EXPLICA en su cabecera que el orbe viejo
   tenía una cáscara con Fresnel, y una prueba que grepa el texto entero se pondría roja
   por un comentario. Lo que interesa es el código. */
const codigo = fuente.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
const cuerpo = codigo.slice(codigo.indexOf('function pinta'));
ok('la geometría se calcula en un único sitio del código',
   (codigo.match(/aristasCercanas\(/g) || []).length === 2 &&
   /export function aristasCercanas\(/.test(codigo) &&
   /const aristas = aristasCercanas\(geo\.pos/.test(codigo),
   `${(codigo.match(/aristasCercanas\(/g) || []).length} apariciones`);
ok('el bucle (`pinta`) no toca la geometría',
   !/setAttribute|new Buffer|aristasCercanas|puntosFibonacci|Float32Array/.test(cuerpo));
ok('el bucle sólo escribe uniforms y rotación',
   /comp\.uTiempo\.value|objeto\.rotation/.test(cuerpo));
ok('no hay Fresnel ni cáscara de 1280 triángulos de vuelta',
   !/Icosahedron|Fresnel|GridHelper/.test(codigo));

/* ---------- [7] vestir el orbe (paso 1.2) ----------
   El color del orbe ya no está escrito aquí: lo da `traje.js`. Lo que se vigila es el
   reparto y el precio: que el traje cambie los cinco estados, que NO reconstruya la
   geometría (cuesta lo que cuesta escribir el destino), y que el color no salte —un
   orbe que hace un bote al mudar de atuendo se ve roto aunque el color sea correcto. */
console.log('\n[7] vestir el orbe, sin reconstruirlo');
const FABRICA = coloresDelTraje(POR_DEFECTO.primario, POR_DEFECTO.secundario);
ok('la tabla de fábrica del orbe ES la de `traje.js`, estado por estado',
   CLAVE.every(k => ESTADOS[k].a === FABRICA[k].a && ESTADOS[k].b === FABRICA[k].b));
/* El candado del paso: si alguien vuelve a escribir un `#hex` de estado en el módulo,
   el orbe dejará de vestirse y la prueba [1] de la Fase 1 («cambiar traje ⇒ cambia
   TODO el orbe») volverá a mentir. */
ok('en el código del orbe no queda ni un color de estado escrito a mano',
   !/['"]#[0-9a-f]{3,6}['"]/i.test(codigo),
   (codigo.match(/['"]#[0-9a-f]{3,6}['"]/gi) || []).slice(0, 3).join(' '));

const hexDel = c => '#' + [c.r, c.g, c.b].map(v =>
  Math.round(Math.max(0, Math.min(1, v)) * 255).toString(16).padStart(2, '0')).join('');
const JARVIS = ['#ffc46b', '#241405'];
const MATRIX = ['#22ff88', '#04160c'];
const vestido = creaOrbe(THREE, { traje: JARVIS });
ok('`creaOrbe` con traje monta la tabla de ESE traje',
   vestido.estados().escucha.b === coloresDelTraje(...JARVIS).escucha.b &&
   vestido.estados().escucha.b !== FABRICA.escucha.b);
ok('y los uniforms nacen con su color, no con el de fábrica',
   hexDel(vestido.objeto.children[0].material.uniforms.uColorB.value) === coloresDelTraje(...JARVIS).reposo.b,
   hexDel(vestido.objeto.children[0].material.uniforms.uColorB.value));

vestido.setEstado('escucha');
for (let i = 0; i < 60; i++) vestido.pinta(1 / 30, 0.3);      // se asienta en el cian
const uniformEscucha = vestido.objeto.children[0].material.uniforms;
const colorAntes = hexDel(uniformEscucha.uColorB.value);
ok('asentado, el uniform coincide con el estado puesto',
   colorAntes === hexDel(new Color(coloresDelTraje(...JARVIS).escucha.b)), `${colorAntes}`);
const geoAntes = vestido.objeto.children[0].geometry;
const cifrasAntes = JSON.stringify(vestido.cifras());
vestido.vestir(...MATRIX);
ok('vestir deja puesto el MISMO estado (no vuelve a reposo)', vestido.estado() === 'escucha');
ok('vestir cambia la tabla entera, incluida la de hablar',
   vestido.estados().habla.b === coloresDelTraje(...MATRIX).habla.b);
ok('vestir NO reconstruye la geometría: es el mismo objeto y las mismas cifras',
   vestido.objeto.children[0].geometry === geoAntes &&
   JSON.stringify(vestido.cifras()) === cifrasAntes, cifrasAntes);
/* El candado del «no salta»: con un solo frame el color tiene que haberse MOVIDO pero
   tiene que seguir más cerca del anterior que del destino. `pinta` interpola ~20 % por
   frame a 30 fps, así que el bote sólo se daría si alguien pusiera el color a mano. */
vestido.pinta(1 / 30, 0.3);
const movido = hexDel(uniformEscucha.uColorB.value);
const d = (x, y) => Math.hypot(...[1, 3, 5].map(i =>
  parseInt(x.slice(i, i + 2), 16) - parseInt(y.slice(i, i + 2), 16)));
ok('y el color se ACERCA al nuevo traje, no salta',
   movido !== colorAntes && d(movido, colorAntes) < d(movido, coloresDelTraje(...MATRIX).escucha.b),
   `${colorAntes} → ${movido}, destino ${coloresDelTraje(...MATRIX).escucha.b}`);
for (let i = 0; i < 90; i++) vestido.pinta(1 / 30, 0.3);
ok('tras dos segundos de interpolación el orbe ya va vestido',
   d(hexDel(uniformEscucha.uColorB.value), coloresDelTraje(...MATRIX).escucha.b) < 3,
   hexDel(uniformEscucha.uColorB.value));
ok('un traje roto no tumba el orbe: cae al de fábrica y sigue animando',
   vestido.vestir('#zzzzzz', null) === true &&
   vestido.estados().escucha.b === FABRICA.escucha.b);
vestido.borrar();

/* ---------- [8] la animación dispersiva (video f7d16b9e…) ---------- */
/* Lo que ella pidió: «cuando responde CORT o ejecuta una respuesta forma esa clase de
   vórtice, hazlo igual que en el video». «Igual que en el video» sólo se puede exigir en
   dos sitios desde node: en la CURVA (los segundos de cada fase, medidos fotograma a
   fotograma en `docs/REFERENCIAS-VIDEOS-JARVIS.md` §5.2) y en el HECHO de que la forma
   nueva no toque ni un vértice. Lo que se ve lo mira la dueña en la sonda. */
console.log('\n[8] la animación dispersiva: su curva y su presupuesto');
const T = 1 / 30;
ok('el ritmo del video: 0,5 de explosión, 2,0 de montaje, 4,0 de anillo, 1,5 de cierre',
   RITMOS.activa.estalla === 0.5 && RITMOS.activa.monta === 2.0 &&
   RITMOS.activa.mantiene === 4.0 && RITMOS.activa.cierra === 1.5, JSON.stringify(RITMOS.activa));
ok('y al responder es MÁS corto que al ejecutar (no puede tapar la charla)',
   RITMOS.responde.estalla + RITMOS.responde.monta + RITMOS.responde.mantiene + RITMOS.responde.cierra
   < RITMOS.activa.estalla + RITMOS.activa.monta + RITMOS.activa.mantiene + RITMOS.activa.cierra);
const total = RITMOS.activa.estalla + RITMOS.activa.monta + RITMOS.activa.mantiene + RITMOS.activa.cierra;
ok('fuera del rango no hay baile: antes de empezar y al terminar, null',
   formaDelVortice(-0.1) === null && formaDelVortice(total) === null && formaDelVortice(0) !== null);
/* Los tres tramos, en los segundos que marca el video. */
const en = (t) => formaDelVortice(t);
ok('a los 0,5 s está TODA dispersa y el portal aún apagado',
   en(0.5).dispersa > 0.99 && en(0.5).portal === 0, JSON.stringify(en(0.5)));
ok('a los 2,5 s el anillo ya está montado y la dispersión casi recogida',
   en(2.5).portal > 0.99 && en(2.5).dispersa < 0.3, JSON.stringify(en(2.5)));
ok('a mitad del anillo (5 s) se MANTIENE: portal al máximo y vórtice flojo',
   en(5).portal === 1 && en(5).vortice < 0.4, JSON.stringify(en(5)));
ok('y al cerrar (7,9 s) ya casi no queda nada',
   en(total - 0.1).portal < 0.05 && en(total - 0.1).dispersa < 0.02, JSON.stringify(en(total - 0.1)));
/* El candado del «sin costuras»: si alguien cambia un tramo y olvida el siguiente, la
   curva salta. Se mide frame a frame, que es como la va a ver la cara. El tope de 0,11
   no es un número redondo: la pendiente más fuerte de la curva es la explosión
   (smoothstep de 0 a 1 en 0,5 s → 3 unidades por segundo → 0,1 por frame a 30 fps), y
   deja margen justo para que un salto de tramo —que sería de ~0,2 o más— no pase. */
let salto = 0;
for (let t = 0; t < total; t += T) {
  const a = formaDelVortice(t - T / 2), b = formaDelVortice(t + T / 2);
  if (a && b) for (const k of ['dispersa', 'portal', 'vortice'])
    salto = Math.max(salto, Math.abs(b[k] - a[k]));
}
ok('ningún frame salta de golpe (el mayor bote por frame, en 8 s de baile)',
   salto < 0.11, `mayor salto ${salto.toFixed(4)} por frame`);
ok('la curva nace en 0 y muere en 0: el orbe vuelve solo a su forma de siempre',
   en(0).dispersa < 1e-6 && en(0).portal < 1e-6);

/* Y montado: los uniforms, y que la geometría NO se toca. */
const v = creaOrbe(THREE);
const u = v.objeto.children[0].material.uniforms;
ok('los tres mandos del vórtice nacen en 0 (sin `dispara`, el orbe es el de la 2.16.0)',
   u.uDispersa.value === 0 && u.uVortice.value === 0 && u.uPortal.value === 0);
ok('y `vortice()` dice que no hay baile', v.vortice() === null);
const posAntes = v.objeto.children[0].geometry.attrs.position.array;
const sumaAntes = Array.from(posAntes).reduce((a, x) => a + x, 0);
v.dispara('activa');
let picoD = 0, picoP = 0, frames = 0;
for (let t = 0; t < total + 0.5; t += T) {
  v.pinta(T, 0.2); frames++;
  picoD = Math.max(picoD, u.uDispersa.value);
  picoP = Math.max(picoP, u.uPortal.value);
}
ok('el anillo se forma de verdad en los uniforms: dispersa llega a ~1 y portal también',
   picoD > 0.95 && picoP > 0.95, `dispersa ${picoD.toFixed(2)}, portal ${picoP.toFixed(2)}`);
ok('y se apaga solo: terminada la coreografía, los tres vuelven a 0',
   u.uDispersa.value === 0 && u.uVortice.value === 0 && u.uPortal.value === 0 && v.vortice() === null);
ok('DISPARAR DE NUEVO reinicia el baile (ejecuta dos cosas seguidas)',
   (v.dispara('responde'), v.pinta(T, 0), v.vortice() !== null));
const posDespues = v.objeto.children[0].geometry.attrs.position.array;
ok('LA GEOMETRÍA INTACTA: el vórtice es el MISMO array y con la MISMA suma de vértices',
   posAntes === posDespues && Math.abs(Array.from(posDespues).reduce((a, x) => a + x, 0) - sumaAntes) < 1e-9,
   `${posDespues.length} floats`);
v.dispara('activa'); v.pinta(0.3, 0);
const aMitad = u.uPortal.value + u.uDispersa.value;
v.corta();
ok('`corta()` para en seco (el «para» de la cara sí puede con el vórtice)',
   aMitad > 0 && u.uPortal.value === 0 && u.uDispersa.value === 0 && u.uVortice.value === 0,
   `antes ${aMitad.toFixed(2)}`);
v.borrar();

/* Los textos GLSL: que los dos vertex shader lleven el morph y los dos fragmento sepan
   leer el calor. Si el de las líneas se queda fuera, los hilos no siguen a los puntos. */
ok('ambos vertex shader declaran y usan los tres mandos',
   ['uDispersa', 'uVortice', 'uPortal'].every(k =>
     SHADERS.puntos.includes(`uniform float ${k};`) && SHADERS.lineas.includes(`uniform float ${k};`)));
/* Declarar el uniform no basta: si el CUERPO del morph se va del shader de las líneas,
   los hilos se quedan en la esfera mientras los puntos salen disparados, y eso se vería
   como una cara rota. Se exige el `if` de cada tramo en las DOS cadenas. */
ok('y los dos llevan el CUERPO del morph, no sólo la declaración',
   ['if (uDispersa > 0.001)', 'if (uPortal > 0.001)', 'vCalor = clamp('].every(k =>
     SHADERS.puntos.includes(k) && SHADERS.lineas.includes(k)));
ok('el toro usa el radio medido del video, no un número suelto',
   SHADERS.puntos.includes(`float R = ${RADIOS.anillo};`), RADIOS.anillo);
ok('los dos fragmento declaran `vCalor` y lo mezclan hacia el blanco-cian de la estela',
   SHADERS.fragPuntos.includes('varying float vCalor;') &&
   SHADERS.fragLineas.includes('varying float vCalor;') &&
   /mix\(uColor[AB], vec3\(0\.85, 0\.97, 1\.0\)/.test(SHADERS.fragPuntos) &&
   /mix\(uColor[AB], vec3\(0\.85, 0\.97, 1\.0\)/.test(SHADERS.fragLineas));
ok('y el varying del calor está declarado una sola vez en cada vertex',
   (SHADERS.puntos.match(/varying float vCalor;/g) || []).length === 1 &&
   (SHADERS.lineas.match(/varying float vCalor;/g) || []).length === 1);

/* ─── los candados que dejó la pasada en el navegador ───
   Ninguno se puede comprobar midiendo píxeles en node (no hay GPU), pero todos son de
   texto o de número y cada uno corresponde a un fallo que SÍ se vio en pantalla:
     · el anillo inclinado en el espacio del OBJETO barría la cámara con el `giro` del
       orbe y volvía a verse de canto (caja proyectada 272x315: más ALTO que ancho);
     · el mismo giro pivotando sobre la LENTE mandaba el orbe fuera de la pantalla
       (caja de 93x93 px en una esquina);
     · las 700 líneas vivas durante el morfeado tapaban el agujero (una tela blanca);
     · el tubo suelto (0,29) cambiaba la proporción del agujero en cuanto se movía el
       radio del anillo.
   La primera versión de estos candados buscaba `float ang = uPortal *` A SECAS, y la
   batería de mutaciones lo cazó: poniendo el ángulo en 0 (o sea, quitando el anillo de
   la cara y dejándolo de canto) la suite seguía verde. Por eso `GIRO` se exporta y se
   exige su valor, no su sombra. */
ok('la inclinación del anillo se aplica EN ESPACIO DE CÁMARA, con el ángulo medido, en los dos vertex',
   ['puntos', 'lineas'].every(k =>
     SHADERS[k].includes('vec4 mv = modelViewMatrix * vec4(p, 1.0);') &&
     SHADERS[k].includes('gl_Position = projectionMatrix * vis;') &&
     SHADERS[k].includes(`float ang = uPortal * ${GIRO};`)) &&
   !SHADERS.puntos.includes('t = vec3(t.x,') && !SHADERS.lineas.includes('t = vec3(t.x,'),
   'GIRO = ' + GIRO + ' rad (' + (GIRO * 180 / Math.PI).toFixed(0) + '°)');
/* El número detrás de la cadena: con el portal a tope la elipse proyectada mide
   `sin(GIRO)` de alto por 1 de ancho, y el video (215 x 206 px) es 0,958. Se exige
   entre 0,90 y 0,97: por debajo de 0,90 el anillo se está viendo de canto (el fallo de
   la primera versión), y clavarse en 1,0 sería un aro perfectamente de frente, sin la
   profundidad del video. El tope «sin < 1» a secas NO valía: con GIRO = 1,5708 (90°, el
   anillo plano del todo) el seno da 0,99999999 y la mutación M17 pasó verde. La ventana
   tiene que cerrarse por arriba con un número, no con 1. */
ok('y el ángulo deja el anillo casi de frente, como el video (relación 0,96)',
   Math.sin(GIRO) >= 0.90 && Math.sin(GIRO) <= 0.97, 'sin(GIRO) = ' + Math.sin(GIRO).toFixed(3));
ok('y el giro pivota sobre el CENTRO del orbe, no sobre la lente',
   ['puntos', 'lineas'].every(k =>
     SHADERS[k].includes('vec3 centro = modelViewMatrix[3].xyz;') &&
     SHADERS[k].includes('vec3 r = mv.xyz - centro;') &&
     SHADERS[k].includes('r.x + centro.x')));
/* Sin portal no hay giro: con los tres mandos a 0 el orbe tiene que proyectarse EXACTO
   como en la 2.16.0, y eso sólo se cumple si el ángulo se MULTIPLICA por uPortal. */
ok('el giro vale 0 con el portal apagado (reposo idéntico a la 2.16.0)',
   ['puntos', 'lineas'].every(k => SHADERS[k].includes(`float ang = uPortal * ${GIRO};`)));
ok('las líneas se APAGAN durante el morfeado (la tela tapaba el agujero)',
   SHADERS.fragLineas.includes('float tela = 1.0 - 0.85 * max(uDispersa, uPortal);') &&
   SHADERS.fragLineas.includes('* tela);') &&
   !SHADERS.fragPuntos.includes('tela'),
   'los puntos siguen a tope: son las estelas del video');
ok('el tubo del toro va ATADO al radio, no es un número suelto',
   /float R = [\d.]+;\s*float rt = R \* [\d.]+;/.test(SHADERS.puntos));

console.log(`\n${fallos ? 'ROJO' : 'verde'} · ${hechos} hechos, ${fallos} fallos · ` +
            `${N_PUNTOS} puntos, ${n} líneas\n`);
process.exit(fallos ? 1 : 0);
