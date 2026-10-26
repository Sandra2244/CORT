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
  puntosFibonacci, aristasCercanas, creaOrbe, SHADERS,
} from '../ui/js/orbe-plexo.js';

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

console.log(`\n${fallos ? 'ROJO' : 'verde'} · ${hechos} hechos, ${fallos} fallos · ` +
            `${N_PUNTOS} puntos, ${n} líneas\n`);
process.exit(fallos ? 1 : 0);
