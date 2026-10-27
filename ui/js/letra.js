/* ===== letra.js · la letra con marcas de tiempo (karaoke de la hoja Música) =====
 *
 * Sale de `pantallas.js` en el primer corte de la refactorización por tamaño: es texto
 * que entra y una lista que sale, sin DOM ni red, así que se puede comprobar con node
 * en el portátil. Y hace falta, porque el formato que llega de LRCLIB tiene tres
 * variantes que en la cara se ven igual de mal si alguna se pierde: una línea sin
 * marca no es letra, `[0:07.5]` no son 7,5 segundos de la columna de los minutos, y
 * `.5` son 50 centésimas.
 */

/** `[mm:ss.cc] texto` → `{ s, texto }`, en segundos y ordenados como vienen.
 *  Las líneas sin marca de tiempo, o con la marca y nada de texto, se descartan:
 *  en el karaoke una línea vacía ocupa su hueco y corta el canto. */
export function parseaLetra(texto) {
  const sale = [];
  String(texto || '').split('\n').forEach(linea => {
    // LRCLIB escribe `[00:13.42]`; también cabe `[0:07.5]` (un dígito de centésimas)
    // y el punto o los dos puntos como separador. Sin marca de tiempo → no es línea.
    const m = linea.match(/^\s*\[(\d{1,3}):(\d{2})(?:[.:](\d{1,2}))?\](.*)$/);
    if (!m) return;
    const textoLinea = (m[4] || '').trim();
    if (!textoLinea) return;
    // «.5» son 50 centésimas, no 5: se rellena a la derecha antes de dividir.
    const cent = (m[3] || '').padEnd(2, '0');
    sale.push({ s: (+m[1]) * 60 + (+m[2]) + (+cent) / 100, texto: textoLinea });
  });
  return sale;
}
