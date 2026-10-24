/* ===== El traje del orbe, en color puro =====
 *
 * `orb.js` tenía veinte colores escritos a mano (`0x4fc6ff`, `0x7f6bff`, …). Eso
 * hacía que cambiar de atuendo pintara el HUD pero dejara el orbe azul para
 * siempre: dos CORT distintas en la misma pantalla. Aquí vive la traducción de un
 * atuendo (`primario` + `secundario`, los mismos del contrato 2.1) a los dieciséis
 * colores que el orbe usa de verdad.
 *
 * Es un módulo PURO a propósito: no toca `THREE`, ni el DOM, ni `window`. Así
 * `scripts/prueba-colores.mjs` lo mide en node, sin WebGL ni teléfono, y puede
 * exigir lo que de verdad importa: que al cambiar de traje cambien **todos** los
 * colores del orbe, no sólo el del núcleo.
 *
 * Lo que NO hace: no adivina nombres de traje ni lee preferencias. Recibe dos
 * colores y devuelve colores; quien decide cuáles son es `Paleta.java` y la cara.
 * Si un color llega roto, cae al de fábrica de ese canal —nunca lanza, porque una
 * cara que no arranca por un `#` mal escrito no es una cara.
 */

/** Los dieciséis canales que `orb.js` pinta. Si se añade uno al orbe, va aquí. */
export const CLAVES = Object.freeze([
  'nucleo', 'brillo', 'particula', 'halo', 'hilos', 'anillo1', 'anillo2',
  'sueloA', 'sueloB', 'rejillaA', 'rejillaB', 'haz', 'estrella', 'disco',
  'chispa', 'onda',
]);

/** El azul de siempre: el mismo de `Paleta.java` (`Cortana`). */
export const POR_DEFECTO = Object.freeze({
  primario: '#59d9ff',
  secundario: '#0a3d62',
});

const HEX = /^#(?:[0-9a-f]{3}|[0-9a-f]{6})$/i;

/** `#abc` o `#aabbcc` → [r, g, b]; cualquier otra cosa → null. */
function tres(hex) {
  if (typeof hex !== 'string') return null;
  const t = hex.trim();
  if (!HEX.test(t)) return null;
  let s = t.slice(1);
  if (s.length === 3) s = s[0] + s[0] + s[1] + s[1] + s[2] + s[2];
  return [parseInt(s.slice(0, 2), 16), parseInt(s.slice(2, 4), 16), parseInt(s.slice(4, 6), 16)];
}

function aHex(rgb) {
  return '#' + rgb.map(v => {
    const n = Math.max(0, Math.min(255, Math.round(v)));
    return n.toString(16).padStart(2, '0');
  }).join('');
}

/** Mezcla lineal: `t` 0 devuelve `a`, `t` 1 devuelve `b`. */
function mezcla(a, b, t) {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}

const BLANCO = [255, 255, 255];

/** Aclara hacia blanco sin llegar nunca a perder el matiz. */
function aclara(rgb, t) { return mezcla(rgb, BLANCO, t); }

/** Rueda el matiz en grados, conservando saturación y luz. */
function gira(rgb, grados) {
  const r = rgb[0] / 255, g = rgb[1] / 255, b = rgb[2] / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  if (d === 0) return rgb.slice();               // gris: no hay matiz que girar
  const s = l > .5 ? d / (2 - max - min) : d / (max + min);
  let h;
  if (max === r) h = (g - b) / d + (g < b ? 6 : 0);
  else if (max === g) h = (b - r) / d + 2;
  else h = (r - g) / d + 4;
  h = (h / 6 + grados / 360) % 1;
  if (h < 0) h += 1;
  const q = l < .5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const canal = t => {
    let u = t;
    if (u < 0) u += 1;
    if (u > 1) u -= 1;
    if (u < 1 / 6) return p + (q - p) * 6 * u;
    if (u < 1 / 2) return q;
    if (u < 2 / 3) return p + (q - p) * (2 / 3 - u) * 6;
    return p;
  };
  return [canal(h + 1 / 3) * 255, canal(h) * 255, canal(h - 1 / 3) * 255];
}

/** Los dieciséis colores del orbe para un atuendo. Nunca lanza. */
export function deriva(primario, secundario) {
  const p = tres(primario) || tres(POR_DEFECTO.primario);
  const s = tres(secundario) || tres(POR_DEFECTO.secundario);
  return {
    nucleo: aHex(aclara(p, .55)),                 // corazón casi blanco
    brillo: aHex(aclara(p, .22)),                 // halo del núcleo
    particula: aHex(p),                           // cáscara de 2.600 partículas
    halo: aHex(aclara(mezcla(s, p, .45), .05)),   // esfera interior
    hilos: aHex(aclara(p, .18)),                  // plexus
    anillo1: aHex(p),                             // anillo orbital 1
    anillo2: aHex(aclara(gira(mezcla(p, s, .35), 14), .10)),  // orbital 2, girado
    sueloA: aHex(mezcla(p, s, .55)),              // plato, anillos pares
    sueloB: aHex(aclara(p, .08)),                 // plato, anillos impares
    rejillaA: aHex(mezcla(s, p, .50)),            // rejilla, líneas centrales
    rejillaB: aHex(aclara(s, .10)),               // rejilla, líneas normales
    haz: aHex(aclara(p, .12)),                    // haces que caen
    estrella: aHex(aclara(p, .60)),               // estrellas de fondo
    disco: aHex(aclara(p, .45)),                  // borde del vinilo
    chispa: aHex(aclara(p, .28)),                 // chispas del portal
    onda: aHex(aclara(p, .42)),                   // ondas de choque
  };
}
