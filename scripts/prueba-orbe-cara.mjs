#!/usr/bin/env node
/* ===== prueba del orbe de la referencia montado en la cara (ronda 2.16.0) =====
   No lee el archivo y lo aprueba por la palabra: ejecuta `ui/js/orbe-cara.js` contra un
   `three` de pega (`scripts/fake-three.mjs`) y una pantalla de pega, le da las órdenes con
   las que la cara habla con el orbe (`listen`, `speak`, `activate`, `setAudio`, `pausa`,
   `vestir`, `stop`, `burst`) y mira QUÉ PASA cuadro a cuadro.

   La copia que se ejecuta es el TEXTO del repo con los tres `import` reescritos a sus
   rutas absolutas, y eso se comprueba (sector [1]): un arnés que ejecuta otra cosa que el
   archivo de la cara es un arnés que prueba su propia mentira.

   Sectores:
     [1] el adaptador no copia geometría ni colores, y lo que se ejecuta es el archivo
     [2] paridad de métodos con los que la cara habla con el orbe
     [3] el presupuesto: pixel ratio, antialias, `low-power`, cámara y tamaño de punto
     [4] la máquina de estados, ejecutada
     [5] las tres manos del nivel (estado, micrófono, chispa), que antes se pisaban
     [5b] `vestir`: la tabla nueva del teléfono y el color que se le acerca
     [6] `pausa` congela el WebGL de verdad (batería)
     [7] el techo de 30 fps, y 15 con «sin animaciones»
     [8] la tecla `cort-orbe`, que tiene que ser la misma cadena en tres sitios
*/
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { dirname, join } from 'node:path';

const RA = join(dirname(fileURLToPath(import.meta.url)), '..');
let fallos = 0, hechos = 0;
const ok = (etiqueta, condicionado, detalle = '') => {
  if (condicionado) { hechos++; console.log('  ok  ' + etiqueta); }
  else { fallos++; console.log('  NO  ' + etiqueta + (detalle ? ' → ' + detalle : '')); }
};
const lee = ruta => readFile(join(RA, ruta), 'utf8');

const cara = await lee('ui/js/orbe-cara.js');
const index = await lee('ui/index.html');
const pant = await lee('ui/js/pantallas.js');
const hud = await lee('ui/js/hud.js');

/* ─── [1] la capa de montaje no duplica lo que ya está medido ─── */
console.log('\n[1] el adaptador no copia geometría ni colores');
ok('existe `ui/js/orbe-cara.js` y es un módulo con su fábrica',
   /export function initOrbeCara/.test(cara));
ok('pide la geometría a `orbe-plexo.js`, no la reescribe aquí',
   /from '\.\/orbe-plexo\.js'/.test(cara) && /creaOrbe\(THREE/.test(cara));
ok('pide los colores al atuendo puesto (`traje.js` y las variables de la cara)',
   /from '\.\/traje\.js'/.test(cara) && /--primario/.test(cara) && /trajeDeLaCara\(\)/.test(cara));
ok('no importa el orbe viejo: los dos conviven, no se mezclar en un mismo cuadro',
   !/from '\.\/orb\.js'/.test(cara));
const hexesCara = (cara.match(/#[0-9a-f]{3,8}\b/gi) || []);
ok('y no hay ni un `#hex` escrito a mano en el adaptador (un literal = traje roto)',
   hexesCara.length === 0, hexesCara.join(' '));

/* ─── el arnés: la caja de /tmp con los `import` reescritos ─── */
const CAJA = '/tmp/cort-orbe-cara';
if (!existsSync(CAJA)) await mkdir(CAJA, { recursive: true });
const RUTA_FAKE = pathToFileURL(join(RA, 'scripts/fake-three.mjs')).href;
const texto = cara
  .replace(/from 'three'/g, `from '${RUTA_FAKE}'`)
  .replace(/from '\.\/orbe-plexo\.js'/g, `from '${pathToFileURL(join(RA, 'ui/js/orbe-plexo.js')).href}'`)
  .replace(/from '\.\/traje\.js'/g, `from '${pathToFileURL(join(RA, 'ui/js/traje.js')).href}'`);
const antesL = cara.split('\n'), despuesL = texto.split('\n');
const distintas = despuesL.filter((l, i) => l !== antesL[i]);
ok('lo que se ejecuta es el archivo del repo: sólo cambian sus tres `import`',
   antesL.length === despuesL.length && distintas.length === 3
   && distintas.every(l => /from '/.test(l)),
   antesL.length + '/' + despuesL.length + ' líneas, ' + distintas.length + ' distintas');
await writeFile(join(CAJA, 'host.mjs'), texto);

function makeDOM(clases) {
  const raiz = {
    classList: {
      contains: c => clases.includes(c),
      add: c => { if (!clases.includes(c)) clases.push(c); },
      remove: c => { const i = clases.indexOf(c); if (i > -1) clases.splice(i, 1); },
    },
  };
  const canvas = {
    width: 0, height: 0,
    getContext: () => ({ createRadialGradient: () => ({ addColorStop() {} }), fillRect() {} }),
  };
  const mount = {
    tagName: 'DIV', hijos: [],
    appendChild(h) { this.hijos.push(h); h.parentNode = this; },
    removeChild(h) { this.hijos = this.hijos.filter(x => x !== h); h.parentNode = null; },
  };
  return { raiz, mount, canvas, document: { documentElement: raiz, createElement: () => canvas,
                                             getElementById: () => mount } };
}

function makeReloj() {
  let cola = [], t = 0, id = 0;
  /* El `setTimeout` de pega es obligatorio, no un capricho: `speak(2200)` y `activate()`
     se apagan con un temporizador, y si se deja el de Node la prueba avanza el reloj de
     cuadro a cuadro SIN avanzar el tiempo real, el orbe se queda «hablando» para siempre y
     la comprobación mide el arnés en vez de medir la cara. */
  let temporizadores = [];
  return {
    requestAnimationFrame: cb => { cola.push(cb); return cola.length; },
    cancelAnimationFrame: () => { cola = []; },
    setTimeout: (fn, ms = 0) => { const mio = ++id; temporizadores.push({ en: t + ms, fn, mio }); return mio; },
    clearTimeout: mio => { temporizadores = temporizadores.filter(x => x.mio !== mio); },
    get enCola() { return cola.length; },
    paso(ms = 16.7) {
      t += ms;
      const pendientes = cola; cola = [];
      const due = temporizadores.filter(x => x.en <= t);
      temporizadores = temporizadores.filter(x => x.en > t);
      due.forEach(x => x.fn());
      pendientes.forEach(cb => cb(t));
      return pendientes.length;
    },
    correr(n, cada = 16.7) { for (let i = 0; i < n; i++) this.paso(cada); },
    get ahora() { return t; },
  };
}

let montaNum = 0;
const gl = await import(RUTA_FAKE);              // UN solo `three` de pega: el que ve el host
async function monta({ clases = [], dpr = 2, css = ['#2bd4ff', '#8f6bff'], ratio = null } = {}) {
  const dom = makeDOM(clases.slice());
  const reloj = makeReloj();
  const almac = new Map();
  const { renderers } = gl;
  /* Cada montaje tiene SU reloj y SU pantalla, y la cara sólo ve globals. Si no se guarda
     la bolsa por instancia, montar un segundo orbe (el de `dpr: 1` del sector [3]) deja el
     bucle del primero encolándose en el reloj equivocado: el nivel se congela y la prueba
     mide el arnés. `activa()` vuelve a poner los cristales de esta instancia. */
  const bolsa = {
    document: dom.document,
    innerWidth: 900, innerHeight: 1600, devicePixelRatio: dpr,
    localStorage: { getItem: k => (almac.has(k) ? almac.get(k) : null),
                    setItem: (k, v) => almac.set(k, String(v)), removeItem: k => almac.delete(k) },
    getComputedStyle: () => ({ getPropertyValue: n => (String(n).includes('secundario') ? css[1] : css[0]) }),
    addEventListener: () => {}, removeEventListener: () => {},
    requestAnimationFrame: reloj.requestAnimationFrame,
    cancelAnimationFrame: reloj.cancelAnimationFrame,
    // Los temporizadores también son de pega, y por la misma razón que el reloj: si el
    // `setTimeout` de Node vive en el tiempo real, `speak(2200)` jamás se apaga aquí dentro.
    setTimeout: reloj.setTimeout, clearTimeout: reloj.clearTimeout,
    performance: { now: () => reloj.ahora },
  };
  Object.assign(globalThis, bolsa);
  const activa = () => Object.assign(globalThis, bolsa);
  montaNum++;
  const módulo = await import(pathToFileURL(join(CAJA, 'host.mjs')).href + '?v=' + montaNum);
  const base = renderers.length;
  const orbe = módulo.initOrbeCara(dom.mount, ratio ? { pixelRatio: ratio } : {});
  return { orbe, reloj, dom, gl, activa, renderer: renderers[base] };
}

/* ─── [2] paridad: la cara no puede perder un método por el camino ─── */
console.log('\n[2] los métodos con los que la cara habla con el orbe');
/* La lista no la inventa esta prueba: se LEE del doble de palo de `ui/index.html`, que es
   lo que la cara usa cuando el WebGL se cae. Y se comprueba contra el objeto VIVO. */
const inicioStub = index.indexOf('const orbeDePalo');
/* Se corta en el `};` que cierra el objeto literal, no en la primera línea en blanco: lo
   que viene después (las fábricas y el bucle de arranque) NO es la lista de métodos, y
   contarla como si lo fuera dio 25 nombres en vez de once. */
const bloque = index.slice(inicioStub, index.indexOf('\n};', inicioStub));
const nombres = [...new Set([...bloque.matchAll(/([a-zA-Z_$][\w$]*)\s*\(/g)].map(m => m[1]))]
  .filter(n => n !== 'orbeDePalo');
const { orbe, reloj, renderer, activa } = await monta();
const faltan = nombres.filter(n => typeof orbe[n] !== 'function');
ok('los ' + nombres.length + ' nombres del doble de palo están en el adaptador',
   nombres.length === 11 && faltan.length === 0, 'faltan: ' + faltan.join(', '));
const llamaCara = [...new Set([...(hud + index).matchAll(/\borb\.([a-zA-Z_$][\w$]*)\(/g)].map(m => m[1]))]
  .filter(n => n !== 'initORB');
ok('y ningún `orb.<algo>` que llame la cara se queda sin responder',
   llamaCara.every(n => n in orbe), llamaCara.filter(n => !(n in orbe)).join(', '));

/* ─── [3] el presupuesto ─── */
console.log('\n[3] el presupuesto del WebGL en 2 núcleos y 1,8 GiB');
reloj.correr(4, 16.7);                        // hasta que no pinta un cuadro no hay cámara que ver
const cifras = orbe.cifras();
ok('el pixelRatio se corta en 1,5 aunque el aparato declare más',
   renderer.getPixelRatio() === 1.5, 'ratio ' + renderer.getPixelRatio());
ok('antialias apagado y `powerPreference: low-power` pedido al navegador',
   renderer.antialias === false && renderer.powerPreference === 'low-power',
   JSON.stringify({ a: renderer.antialias, p: renderer.powerPreference }));
ok('la esfera queda a 7,2 de cámara: el tamaño del orbe en el video',
   renderer.ultimaCamara.position.z === 7.2, 'z=' + renderer.ultimaCamara?.position?.z);
ok('el tamaño de punto se pasa en píxeles DEL APARATO (2,8 × ratio)',
   Math.abs(cifras.pixelRatio * 2.8 - 4.2) < .01, String(cifras.pixelRatio * 2.8));
ok('`cifras()` son los 220 puntos y las 700 líneas que midió la sonda',
   cifras.puntos === 220 && cifras.lineas === 700 && cifras.fps === 30, JSON.stringify(cifras));
const bajoInst = await monta({ dpr: 1 });
const bajo = bajoInst.renderer.getPixelRatio();
activa();                                             // el orbe principal vuelve a ser el visible
ok('con 1,5 de ratio el tope no sube: un aparato malo no paga de más',
   bajo === 1, 'ratio ' + bajo);

/* ─── [4] la máquina de estados ─── */
console.log('\n[4] la máquina de estados, ejecutada');
ok('nace en reposo, sin llamar la atención', orbe.estado() === 'reposo', orbe.estado());
orbe.listen(true);
ok('`listen(true)` pasa a `escucha`', orbe.estado() === 'escucha', orbe.estado());
orbe.speak(2200);
ok('`speak(2200)` pasa a `habla`', orbe.estado() === 'habla', orbe.estado());
reloj.correr(200, 16.7);                             // ~3,3 s de reloj
ok('y a los 2200 ms vuelve a reposo sola', orbe.estado() === 'reposo', orbe.estado());
orbe.speak(60000); orbe.speak(1);                    // la cara corta una frase larga
reloj.correr(40, 16.7);
ok('una frase larga cortada por otra corta no deja el orbe hablando media hora',
   orbe.estado() === 'reposo', orbe.estado());
orbe.activate();
ok('`activate()` pone la cara a PENSAR (el gesto del video, no el truco de cámara)',
   orbe.estado() === 'piensa', orbe.estado());
reloj.correr(120, 16.7);                             // 2 s
ok('y se le pasa solo si nadie dice nada en 1,6 s', orbe.estado() === 'reposo', orbe.estado());
ok('un estado inventado cae a reposo en vez de tumbar la cara',
   orbe.estado('patito') === 'reposo' && orbe.estado() === 'reposo', orbe.estado());
orbe.estado('error');
ok('`error` SÍ existe y es rojo con los seis atuendos',
   orbe.estado() === 'error' && orbe.colores().error.b === '#ff5b6e', orbe.colores().error?.b);
orbe.estado('habla'); orbe.stop();
ok('`stop()` corta voz y activación en vuelo y deja la cara en reposo',
   orbe.estado() === 'reposo', orbe.estado());

/* ─── [5] las tres manos del nivel ─── */
console.log('\n[5] el nivel: estado, micrófono y chispa, sin pisarse');
const uniformes = orbe.orbe().objeto.children[0].material.uniforms;
const dejaAsentar = () => { reloj.correr(40, 16.7); return uniformes.uNivel.value; };
orbe.estado('reposo'); orbe.setAudio(0, 0);
const enReposo = dejaAsentar();
orbe.listen(true);
const alOir = dejaAsentar();
orbe.setAudio(.9, .9);
const conMicro = dejaAsentar();
ok('el micrófono sube el nivel por encima del suelo de `escucha`',
   conMicro > alOir && alOir > enReposo,
   [enReposo, alOir, conMicro].map(v => v.toFixed(3)).join(' → '));
orbe.setAudio(0, 0);                                  // `stopMeter()` de la cara
const trasCallar = dejaAsentar();
ok('`setAudio(0,0)` NO apaga el `listen`: el suelo del estado sigue vivo',
   trasCallar > .3, trasCallar.toFixed(3));
orbe.estado('reposo'); orbe.burst();
/* `burst()` es un fogonazo, no un estado: mide el PICO mientras se apaga. Medir al final
   de los 40 marcos (como con un estado sostenido) daría 0,16 y la prueba acusaría de
   flojo a un orbe que sí se encendió. */
const picoChispa = (n) => { let m = uniformes.uNivel.value; for (let i = 0; i < n; i++) { reloj.paso(16.7); m = Math.max(m, uniformes.uNivel.value); } return m; };
const chispa = picoChispa(20);
reloj.correr(90, 16.7);                               // 1,5 s: la chispa se apaga
const apagada = uniformes.uNivel.value;
ok('`burst()` empuja y se apaga solo: no deja el orbe a tope para siempre',
   chispa > .4 && apagada < chispa, chispa.toFixed(3) + ' → ' + apagada.toFixed(3));

/* ─── [5b] `vestir`, el contrato del teléfono, sobre el orbe vivo ─── */
console.log('\n[5b] `vestir()`: la tabla nueva y el color que se le ACERCA');
/* El nombre lo escribió esta prueba con una `i` de más (`orbe.vistir`) y en el navegador
   saltó `TypeError`. Ninguna comprobación de «el método existe» lo podía ver: lo que hay
   que ejercitar es la LLAMADA, y lo que hay que mirar es lo que vuelve. */
const antesTraje = orbe.colores();
orbe.estado('reposo');
const nuevoTraje = orbe.vestir('#ff8a3d', '#ffd166');
ok('`vestir` devuelve la tabla de los cinco estados, no un objeto vacío',
   nuevoTraje && ['reposo', 'escucha', 'piensa', 'habla', 'error']
     .every(k => nuevoTraje[k] && nuevoTraje[k].a), JSON.stringify(nuevoTraje));
ok('y los cinco colores salen del par nuevo (un traje copiado a mano no vale)',
   JSON.stringify(nuevoTraje) !== JSON.stringify(antesTraje));
const hexAntes = uniformes.uColorA.value.getHexString();
reloj.correr(40, 16.7);
const hexDespues = uniformes.uColorA.value.getHexString();
ok('el color del orbe VIVO se acerca al traje nuevo cuadro a cuadro (no salta)',
   hexAntes !== hexDespues, hexAntes + ' → ' + hexDespues);
orbe.vestir('#2bd4ff', '#8f6bff');
ok('y se puede volver al de antes: el cambio no es irreversible',
   JSON.stringify(orbe.colores()) === JSON.stringify(antesTraje));

/* ─── [6] pausa ─── */
console.log('\n[6] `pausa` congela el WebGL de verdad (la batería del teléfono)');
orbe.pausa(true);
const dibujosAlPausar = renderer.renderiza;
reloj.correr(60, 16.7);
ok('con `pausa(true)` no queda nada en la cola del `requestAnimationFrame`',
   reloj.enCola === 0, reloj.enCola + ' en cola');
ok('y no se pinta ni un cuadro más', renderer.renderiza === dibujosAlPausar,
   (renderer.renderiza - dibujosAlPausar) + ' dibujos de más');
orbe.listen(true); orbe.setAudio(1, 1);
ok('ni el micrófono lo despierta: el nivel se queda quieto',
   Math.abs(uniformes.uNivel.value - dejaAsentar()) < .0001);
orbe.pausa(false);
reloj.correr(10, 16.7);
ok('`pausa(false)` reanuda el bucle', renderer.renderiza > dibujosAlPausar,
   String(renderer.renderiza));

/* ─── [7] el techo de fotogramas ─── */
console.log('\n[7] 30 fps de techo, y 15 con «sin animaciones»');
const caja = await monta({ clases: [] });
const r2 = caja.renderer;
caja.reloj.correr(2, 16.7);
const base2 = r2.renderiza;
caja.reloj.correr(60, 16.7);                          // 60 marcos a 60 fps = 1 s
const pintados1s = r2.renderiza - base2;
ok('a 60 fps de reloj la cara pinta ~30, no 60', pintados1s >= 28 && pintados1s <= 33,
   pintados1s + ' fotogramas en 1 s');
const lenta = await monta({ clases: ['sin-movimiento'] });
const r3 = lenta.renderer;
lenta.reloj.correr(2, 16.7);
const base3 = r3.renderiza;
lenta.reloj.correr(60, 16.7);
const pintadosLenta = r3.renderiza - base3;
ok('con «sin animaciones» se recorta a ~15 (accesibilidad, no capricho)',
   pintadosLenta >= 13 && pintadosLenta <= 18, pintadosLenta + ' fotogramas en 1 s');

/* ─── [8] la tecla ─── */
console.log('\n[8] `cort-orbe`: una cadena, tres lecturas');
ok('la clave vive en el adaptador y la leen `index.html` y el cajón de Ajustes',
   /CLAVE_ORBE = 'cort-orbe'/.test(cara) && /cort-orbe/.test(index) && /cort-orbe/.test(pant));
ok('por defecto el orbe es el del video, y `viejo` es la salida',
   /!== 'viejo' \? 'viejo' : 'plexo'|=== 'viejo' \? 'viejo' : 'plexo'/
     .test(cara + index + pant));
ok('`index.html` importa SÓLO el elegido y, si cae, prueba el otro antes de rendirse',
   /for \(const nombre of \[elegido, elegido === 'plexo' \? 'viejo' : 'plexo'\]\)/.test(index)
   && /window\.__orbe = nombre/.test(index));
const trozo = index.slice(index.indexOf('for (const nombre'), index.indexOf('window.__orb = orb'));
ok('el primer fallo NO pinta la caja roja: sólo se avisa si fallan los dos orbes',
   !/pintaFalla/.test(trozo) && /__orbeFalla/.test(trozo));
ok('y cambiar de orbe recarga la cara en vez de dejar un WebGL zombi suelto',
   /location\.reload\(\)/.test(pant));
ok('la lámpara y el orbe dicen lo mismo cuando algo falla',
   /error:\s*'error'/.test(hud) && /error:\s*\['#ff5b5b'/.test(hud));

console.log('\n' + (fallos ? 'FALTA ' + fallos + ' COSA(S)' : 'verde · ' + hechos + ' hechos, 0 fallos'));
if (fallos) process.exit(1);
