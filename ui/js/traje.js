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
 * Desde el paso 1.2 de la Fase 1 vive aquí también `estados()`, la tabla de los
 * cinco estados del orbe nuevo (`orbe-plexo.js`): el color ES el estado, y si ese
 * color estuviera escrito a mano en el otro módulo, un atuendo pintaría el HUD y
 * dejaría el orbe cian para siempre.
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

/* ───────────── los cinco ESTADOS del orbe nuevo (paso 1.2) ────────────────────
 *
 * `orbe-plexo.js` (el orbe de la referencia, `docs/PLAN-FASE-1.md`) pinta cinco
 * estados y el color ES el indicador: blanco en reposo, cian al oír, turquesa al
 * pensar, lima al hablar, rojo al fallar. Esos cinco colores estaban escritos a mano
 * en el prototipo, y a mano no siguen al atuendo.
 *
 * **El reparto, dicho en claro porque es una decisión y no un detalle:**
 *  · El **matiz** de cada estado es FIJO — es el idioma. Un orbe que con el traje
 *    JARVIS pusiera el «habla» en ámbar en vez de en lima dejaría de decir nada con
 *    el color, y el video de referencia dice exactamente lo contrario: el color es
 *    el indicador.
 *  · Cada estado trae además su **propia saturación y luz de fábrica**, y el atuendo
 *    las MODULA, no las manda. Es el segundo borrador: en el primero el estado bebía
 *    entero su saturación del traje, y `scripts/prueba-colores.mjs` [6] lo cazó — con
 *    `Neutron` (un gris casi blanco) los cinco estados quedaban a 2,8 de distancia
 *    entre sí, o sea cinco estados que se leían como uno solo. El color tiene que
 *    decir el estado AUNQUE el atuendo sea apagado; por eso la base es del estado y
 *    el traje empuja, como mucho, un 38 % de ella.
 *  · El **reposo** sí es entero del atuendo: casi blanco con su matiz y su temperatura.
 *    O sea: con JARVIS el orbe respira ámbar en reposo y sus blancos son cálidos,
 *    pero al oír sigue poniéndose cian y al hablar sigue poniéndose lima.
 *  · El **error** es rojo en los seis atuendos. Una alarma que cambia de color con
 *    el fondo deja de ser alarma.
 *
 * Los cuatro matizos no los inventé: son los que medí sobre los fotogramas del video
 * con el traje de fábrica, y caen a ~197° (cian), ~164° (turquesa), ~100° (lima) y
 * ~354° (rojo). Las saturaciones y luces base tampoco: `#39c2ff` del video es
 * hsl(198, 1.00, .61) y `#7dff3f` es hsl(101, 1.00, .62), y con el traje de fábrica
 * salen `escucha.b = #59cffe` (a 34,6 del cian leído) y `habla.b = #83fd46` (a 9,4 del
 * lima leído) — el umbral que fija la prueba son 60, así que holgado. El `sube` de cada
 * estado es lo que los separa también en LUZ, porque 33° de matiz a saturación baja se
 * aprietan mucho en RGB: con él el peor par de los seis atuendos sube de 2,8 a 65
 * (Neutron, el gris casi blanco, manda) y `scripts/prueba-colores.mjs` [6] lo exige
 * a 45.
 */

/** Los cinco estados, en el orden en que la cara los enciende. */
export const ESTADOS_CLAVES = Object.freeze(['reposo', 'escucha', 'piensa', 'habla', 'error']);

/**
 * Fábrica de cada estado: matiz, saturación, luz y cuánto sube de luz respecto a la
 * del atuendo. El matiz no se toca nunca (es el idioma); lo demás se modula abajo.
 */
const ESTADO_BASE = Object.freeze({
  escucha: { h: 197, s: 1.0, l: .55, sube: +.08 },
  piensa:  { h: 164, s: .96, l: .50, sube: -.07 },
  habla:   { h: 100, s: .98, l: .57, sube: +.02 },
});

/**
 * El rojo de alarma, FIJO a propósito (ver el comentario de arriba). `a` es el mismo
 * rojo aclarado un tercio, no un rosa inventado: los puntos del orbe en fallo tienen
 * que decir LO MISMO que sus líneas, sólo que más claro.
 */
const ALARMA = Object.freeze({ a: '#ff95a3', b: '#ff5b6e' });

/** [matiz 0-360, saturación 0-1, luz 0-1] de un rgb 0-255. */
function hsl(rgb) {
  const r = rgb[0] / 255, g = rgb[1] / 255, b = rgb[2] / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
  const l = (max + min) / 2;
  if (d === 0) return [0, 0, l];
  const s = l > .5 ? d / (2 - max - min) : d / (max + min);
  let h;
  if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
  else if (max === g) h = ((b - r) / d + 2) / 6;
  else h = ((r - g) / d + 4) / 6;
  return [h * 360, s, l];
}

/** `hsl` → `#rrggbb`. `h` en grados, `s` y `l` de 0 a 1. */
function hslHex(h, s, l) {
  const k = n => (h / 30 + n) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = n => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return aHex([f(0) * 255, f(8) * 255, f(4) * 255]);
}

/**
 * Los cinco estados (puntos `a`, líneas `b`) para un atuendo. Nunca lanza: un color
 * roto cae al de fábrica, igual que `deriva`.
 */
export function estados(primario, secundario) {
  const p = tres(primario) || tres(POR_DEFECTO.primario);
  const s = tres(secundario) || tres(POR_DEFECTO.secundario);
  const [, sP, lP] = hsl(p);
  // El reposo se tiñe con la MEZCLA de los dos colores del traje, como el `halo` de
  // `deriva`: si sólo mirara el primario, un atuendo cambiaría el reposo a medias.
  const [hR, sR] = hsl(mezcla(p, s, .40));
  // La identidad del traje: nunca un gris total (el orbe desaparecería) ni un neón
  // quemado (las líneas aditivas se suben en el centro y el orbe se ve como un disco).
  const sat = Math.min(.95, Math.max(.35, sP));
  const luz = Math.min(.70, Math.max(.42, lP));
  // Cuánto manda el atuendo: 0 con un traje gris, 1 con uno saturado. El estado conserva
  // al menos el 72 % de su propia saturación para que NINGÚN traje apague el idioma.
  const fuerza = (sat - .35) / .60;
  const salida = {};
  for (const k of ESTADOS_CLAVES) {
    if (k === 'error') { salida[k] = { a: ALARMA.a, b: ALARMA.b }; continue; }
    if (k === 'reposo') {
      // El reposo SÍ es del traje: casi blanco, con el matiz y la saturación de la
      // mezcla, pero con la LUZ del primario — en el video el reposo es pálido, y una
      // mezcla con un secundario oscuro lo volvería gris. Es el único de los cinco cuyo
      // color NO es un idioma.
      salida[k] = {
        a: hslHex(hR, Math.min(.30, sR * .35 + .04), Math.min(.98, luz + .30)),
        b: hslHex(hR, Math.max(.14, sR * .42), Math.min(.88, luz + .20)),
      };
      continue;
    }
    const base = ESTADO_BASE[k];
    const sE = Math.min(.99, base.s * (.62 + .38 * fuerza));
    const lE = Math.min(.80, Math.max(.40, base.l + (luz - .56) * .38 + base.sube * (.5 + .5 * fuerza)));
    salida[k] = {
      // Los puntos: el mismo color del estado, más claro y menos cargado, pero
      // NUNCA casi blanco — si no, en el prototipo los puntos no decían el estado.
      a: hslHex(base.h, Math.min(.92, sE * .90), Math.min(.84, lE + .10)),
      b: hslHex(base.h, sE, lE),
    };
  }
  return salida;
}

