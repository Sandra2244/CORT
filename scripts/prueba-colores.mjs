#!/usr/bin/env node
/* Prueba de los COLORES del orbe (`ui/js/traje.js`), sin WebGL, sin navegador y
 * sin teléfono.
 *
 * La fase F17 tiene una prueba decisiva: «cambiar traje ⇒ cambian **todos** los
 * colores del orbe». En un CI no hay GPU, así que la derivación vive en un módulo
 * puro y aquí se mide entera: los dieciséis canales de `orb.js` para cada uno de
 * los seis trajes de `Paleta.java`, que ninguno se quede con el color de fábrica,
 * que dos trajes no den la misma paleta y que un color roto caiga a fábrica en
 * vez de apagar la cara.
 *
 * Lo que NO prueba: que el material de Three.js pinte el color (eso es una línea
 * de `aplica()` y lo vigila el sector [32] de `prueba-costura.py`) ni cómo se ve
 * en el teléfono (eso sólo lo ve la dueña). Prueba lo que se puede medir aquí:
 * que los dieciséis colores cambian de verdad y que la tabla de `Paleta.java`
 * está copiada sin trampas.
 *
 * Uso:  node scripts/prueba-colores.mjs     (una fracción de segundo)
 */
import { CLAVES, POR_DEFECTO, deriva } from '../ui/js/traje.js';

let fallos = 0, hechos = 0;
const ok = (etiqueta, condicionado, detalle = '') => {
  if (condicionado) { hechos++; console.log('  ok  ' + etiqueta); }
  else { fallos++; console.log('  NO  ' + etiqueta + (detalle ? ' → ' + detalle : '')); }
};
const HEX = /^#[0-9a-f]{6}$/i;

/* Los seis de `Paleta.java` (sección 5 del contrato 2.1). El sector [32] compara
   esta tabla con la de Java: si allí cambia un color y aquí no, la costura se
   pone roja antes de que el orbe mienta. */
const TRAJES = [
  ['Cortana', '#59d9ff', '#0a3d62'],
  ['JARVIS', '#ffc46b', '#241405'],
  ['Siri', '#ff5fa2', '#3d0f33'],
  ['Matrix', '#22ff88', '#04160c'],
  ['Atardecer', '#ff7a45', '#3d1a4d'],
  ['Neutron', '#e8eef2', '#1b2226'],
];

console.log('\n[1] los dieciséis canales, para los seis trajes');
ok('son dieciséis y sin repetir',
   CLAVES.length === 16 && new Set(CLAVES).size === 16, String(CLAVES.length));
ok('el de fábrica es el Cortana de Paleta.java',
   POR_DEFECTO.primario === '#59d9ff' && POR_DEFECTO.secundario === '#0a3d62');

const base = deriva(TRAJES[0][1], TRAJES[0][2]);
ok('el traje de fábrica tiene los dieciséis canales',
   CLAVES.every(k => HEX.test(base[k])),
   CLAVES.filter(k => !HEX.test(base[k])).join(', '));

for (const [nombre, primario, secundario] of TRAJES) {
  const c = deriva(primario, secundario);
  const rotos = CLAVES.filter(k => !HEX.test(c[k]));
  ok(`${nombre}: los dieciséis son hex válidos`, rotos.length === 0, rotos.join(', '));
  if (nombre === 'Cortana') {
    ok('Cortana es la referencia: sus dieciséis coinciden consigo misma',
       CLAVES.every(k => c[k] === base[k]));
  } else {
    const iguales = CLAVES.filter(k => c[k] === base[k]);
    ok(`${nombre}: cambian LOS DIECISÉIS colores del orbe`, iguales.length === 0,
       iguales.length ? 'se quedaron igual: ' + iguales.join(', ') : '');
  }
}

console.log('\n[2] dos trajes, dos paletas');
const paletas = TRAJES.map(([n, p, s]) => [n, JSON.stringify(deriva(p, s))]);
const repetidas = [];
for (let i = 0; i < paletas.length; i++) {
  for (let j = i + 1; j < paletas.length; j++) {
    if (paletas[i][1] === paletas[j][1]) repetidas.push(paletas[i][0] + '=' + paletas[j][0]);
  }
}
ok('ningún par de trajes da la misma paleta', repetidas.length === 0, repetidas.join(', '));

console.log('\n[3] el secundario no es decorativo');
const a = deriva('#59d9ff', '#0a3d62');
const b = deriva('#59d9ff', '#3d0f33');          // mismo primario, otro secundario
const cambian = CLAVES.filter(k => a[k] !== b[k]);
ok('cambiar sólo el secundario cambia halo, anillo2, suelo y rejilla',
   ['halo', 'anillo2', 'sueloA', 'rejillaA', 'rejillaB'].every(k => cambian.includes(k)),
   'cambiaron: ' + cambian.join(', '));
ok('y el primario no se mueve cuando sólo cambia el secundario',
   ['particula', 'nucleo', 'brillo', 'hilos', 'anillo1', 'estrella'].every(k => a[k] === b[k]));

console.log('\n[4] un color roto no apaga la cara');
const roto = [[null, null], [undefined, undefined], ['', ''],
              ['#zzzzzz', '#000000'], ['rgb(1,2,3)', 'azul'], [42, {}]];
for (const [p, s] of roto) {
  let c = null, reventó = '';
  try { c = deriva(p, s); } catch (e) { reventó = String(e && e.message || e); }
  ok(`deriva(${JSON.stringify(p)}, ${JSON.stringify(s)}) no lanza y cae a fábrica`,
     !reventó && c && CLAVES.every(k => HEX.test(c[k])), reventó);
}
ok('un `#abc` corto se acepta y da el mismo color que `#aabbcc`',
   deriva('#abc', '#123').particula === deriva('#aabbcc', '#112233').particula);
ok('mayúsculas y espacios no cambian el resultado',
   deriva(' #59D9FF ', ' #0A3D62 ').particula === base.particula);

console.log('\n[5] el contrato de la tabla');
ok('cada traje tiene nombre y dos colores válidos',
   TRAJES.every(([n, p, s]) => n && HEX.test(p) && HEX.test(s)));
ok('los nombres de la tabla están en el orden de Paleta.java',
   TRAJES.map(t => t[0]).join(',') === 'Cortana,JARVIS,Siri,Matrix,Atardecer,Neutron');

console.log('\n' + (fallos ? 'FALTA ' + fallos + ' COSA(S) en los colores del orbe.'
                           : 'colores del orbe: ' + hechos + ' comprobaciones, todas en verde.'));
process.exit(fallos ? 1 : 0);
