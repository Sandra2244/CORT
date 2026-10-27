/* ===== el tope de líneas de la interfaz, medido y con la deuda a la vista =====

   La regla de la dueña, escrita en su prompt: «la interfaz debe ser mil líneas máximo y si
   necesitas crear otros de otras líneas más conectas y divides entre si pero que funcione
   correctamente». Esta comprobación la convierte en algo que se puede cumplir y que además
   **no se puede olvidar ni a medias**:

     · ningún archivo de la cara puede pasar de 1.000 líneas;
     · los que hoy la pasan están en deuda, y la deuda sólo se admite mientras **BAJE**: el
       techo de cada uno vive en `scripts/tope-lineas.json`, y si un corte deja un archivo
       más largo que el techo registrado, esto sale en rojo con los números delante.
     · subir un techo se llama «aflojar la prueba». Por eso el registro se escribe con una
       orden expresada (`--baja`), se commitea, y cualquier subida se ve en el `git diff`.

   Por qué no basta con «ya lo miraré»: `telefono.js` mide 2.770 líneas, `hud.js` 2.572 y
   `pantallas.js` 2.185, y ningún sitio lo decía. Aquí lo dice en cada compilación, archivo
   por archivo, y se anota la deuda hacia abajo conforme salen los cortes.

   Uso:  node scripts/prueba-tope.mjs            (comprueba)
         node scripts/prueba-tope.mjs --baja     (registra las cuentas de ahora, para bajar desde ellas)
*/
import { readFileSync, writeFileSync, readdirSync, existsSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const RA = join(dirname(fileURLToPath(import.meta.url)), '..');
const REGISTRO = join(RA, 'scripts', 'tope-lineas.json');
const LÍMITE = 1000;
const bajo = process.argv.includes('--baja');

/* Sólo la capa que ve la dueña: TODO módulo de `ui/js`, descubierto leyendo la carpeta y no
   de memoria. Con una lista escrita a mano, el archivo nuevo de un corte se queda sin medir
   y el rojo no llega: la regla sólo vale mientras lo que hay en el repo sea lo que se mira. */
const CARA = readdirSync(join(RA, 'ui', 'js')).filter(n => n.endsWith('.js')).sort();

const cuenta = {};
for (const n of CARA) cuenta[n] = readFileSync(join(RA, 'ui', 'js', n), 'utf8').split('\n').length;

let techo = {};
const hayRegistro = existsSync(REGISTRO);
if (hayRegistro) {
  try { techo = JSON.parse(readFileSync(REGISTRO, 'utf8')).archivos || {}; }
  catch { console.log('  NO  `scripts/tope-lineas.json` no es JSON legible: sin registro no hay medida de la deuda'); }
} else if (!bajo) {
  console.log('  NO  no hay registro en `scripts/tope-lineas.json`: la deuda del millar no la mide nadie.'
    + '\n      Corre `node scripts/prueba-tope.mjs --baja` y commitea el archivo que sale.');
}
/* El registro committed es la única medida de la deuda, así que alguien podría BORRAR una
   fila o escribirla más alta y quedarse tan ancho. Se compara con el mismo archivo tal como
   está en `HEAD`: subir un techo (o quitar su fila) sale en rojo aquí, y deja de ser
   «aflojar la prueba en silencio» para ser una línea visible en el `git diff` del commit. */
let techoViejo = {};
try {
  const git = execSync(
    'git show HEAD:scripts/tope-lineas.json', { cwd: RA, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
  techoViejo = JSON.parse(git).archivos || {};
} catch { /* sin git, sin registro viejo o el archivo no estaba en HEAD: manda el propio archivo */ }
const subidos = Object.keys(techo).filter(n => techoViejo[n] !== undefined && techo[n] > techoViejo[n]);
const desaparecidas = Object.keys(techoViejo).filter(n => techo[n] === undefined && cuenta[n] > LÍMITE);

const viejos = Object.keys(techo).filter(n => !(n in cuenta));
if (viejos.length) console.log('  aviso  ya no están en `ui/js` y salen del registro: ' + viejos.join(', '));

let rotos = 0, sinTope = 0;
for (const n of subidos) {
  rotos++;
  console.log(`  NO  ${n}: el techo del registro subió de ${techoViejo[n]} a ${techo[n]} `
    + 'sin que el archivo creciera de verdad — éso es aflojar la prueba');
}
for (const n of desaparecidas) {
  rotos++;
  console.log(`  NO  ${n}: su fila desapareció del registro con ${cuenta[n]} líneas por encima del tope`);
}
const nuevos = {};
for (const [n, lineas] of Object.entries(cuenta)) {
  const tope = techo[n];
  if (lineas <= LÍMITE) { nuevos[n] = LÍMITE; continue; }   // cumplida: el techo de la regla
  if (tope === undefined) {
    sinTope++;
    nuevos[n] = lineas;
    console.log(`  NO  ${n}: ${lineas} líneas y no está en el registro — o es un corte nuevo, o se borró su fila`);
    continue;
  }
  if (lineas > tope) {
    rotos++;
    console.log(`  NO  ${n}: ${lineas} líneas, y el registro decía ${tope}. La deuda se admite mientras BAJE; `
      + 'subir la fila es aflojar la prueba.');
  } else {
    nuevos[n] = lineas;                    // la deuda se anota hacia abajo y queda escrita
    console.log(`  deuda  ${n}: ${lineas} líneas (techo ${tope}) — sigue baja y el tope se escribirá solo en 1000`);
  }
}

console.log(`\n${CARA.length} archivos medidos · tope ${LÍMITE} · `
  + `${Object.values(cuenta).filter(l => l > LÍMITE).length} por encima (deuda visible) · `
  + `${rotos} que subieron · ${sinTope} sin registrar`);

if (bajo && !rotos) {
  writeFileSync(REGISTRO, JSON.stringify({
    tope: LÍMITE,
    nota: 'La regla de la dueña: mil líneas máximo por archivo de interfaz. Los techos sólo bajan; '
      + 'al llegar a 1000 el archivo queda cumplido. Subir uno es aflojar la prueba.',
    deudas: Object.entries(nuevos).filter(([, v]) => v > LÍMITE).map(([k]) => k),
    archivos: nuevos,
  }, null, 2) + '\n', 'utf8');
  console.log('registro escrito con las cuentas de ahora (`git diff` deja vista cualquier subida)');
}
process.exit(rotos || sinTope || (!bajo && !hayRegistro) ? 1 : 0);
