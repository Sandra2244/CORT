/* La cara leída como lo que es: varios módulos, no uno.

   La regla de la dueña es que ningún archivo de interfaz pase de mil líneas, así que la
   cara se está partiendo por sectores (`marco.js` = el marco; `pantallas.js` = la carcasa
   y las pantallas que quedan; `charla.js` = la Charla). Las suites que comprueban
   **costuras de texto** —la frase exacta con la que la cara POSTea, el `classList.toggle`
   del manto, el chip del ejecutor— no pueden quedarse mirando un solo archivo: verían un
   hueco donde no lo hay. Ésa es la razón de este helper, y no la de aflojar nada: la
   cadena exigida sigue siendo la misma, lo que cambia es **dónde se mira**.

   Lo que NO se hace con esto: sustituir una comprobación de «esta pieza vive en ESTE
   archivo» por un vago «está en la cara». Las que miden dónde vive algo siguen nombrando
   el archivo, y `scripts/prueba-md.mjs` lo hace delante.

   Uso:
     import { cara, caraAsync } from './lib-cara.mjs';
     const js = cara(join(raiz, 'ui/js'));            // síncrona
     const js = await caraAsync(dirJs);               // para las suites con fs/promises
*/
import { readFileSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

/* En el orden en que los carga Chromium: primero el marco (no importa a nadie de la
   cara), luego la carcasa, luego las hojas separadas. AÑADIR AQUÍ es el paso que cierra
   un corte: mientras una pantalla viva en `pantallas.js` no hace falta nombrarla; en
   cuanto sale a su archivo entra en esta lista, y `scripts/prueba-costura.py` lee la
   MISMA lista de este archivo (no la copia), así que las dos mitades —node y python— no
   pueden separarse sin que la suite lo grite. */
export const ARCHIVOS_CARA = ['marco.js', 'pantallas.js', 'charla.js'];

export function cara(dirJs, extras = []) {
  return ARCHIVOS_CARA.concat(extras)
    .map(n => readFileSync(join(dirJs, n), 'utf8')).join('\n');
}

export async function caraAsync(dirJs, extras = []) {
  const textos = await Promise.all(ARCHIVOS_CARA.concat(extras)
    .map(n => readFile(join(dirJs, n), 'utf8')));
  return textos.join('\n');
}
