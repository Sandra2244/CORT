/* ===== texto.js · los tres pliegues de texto que la cara usaba copiados a mano =====
 *
 * Por qué existe este módulo: `esc` estaba **definido cinco veces** (en `hud.js`,
 * `pantallas.js`, `telefono.js`, `arnes.js` y `centro.js`) y `normaliza` dos veces,
 * byte a byte, en `automatiza.js` y `telefono.js`. Cinco definiciones son cinco
 * oportunidades de que una se quede atrás: si el día de mañana `esc` no escapa la
 * comilla simple en un archivo y sí en otro, la cara se rompe en una sola pantalla y
 * el bug no se parece a nada de lo que se ve en las otras cuatro. Aquí se define una
 * vez y las seis hojas lo importan; `scripts/prueba-texto.mjs` comprueba, además del
 * comportamiento, que **no vuelve a aparecer una segunda definición** en `ui/js`.
 *
 * No hay más: ni dependencias, ni estado, ni DOM. Es texto que entra y texto que sale,
 * y por eso se puede probar con node en el portátil, sin teléfono y sin navegador.
 */

/** HTML seguro a partir de cualquier cosa. `null`/`undefined` dan cadena vacía — pintar
 *  «undefined» en la placa fue un bug que ya se corrigió una vez (paso 1.3). */
export const esc = s => String(s ?? '').replace(/[&<>"']/g,
  c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/** Minúsculas y sin tildes, conservando la puntuación: sirve para buscar y comparar. */
export const sinTilde = s => String(s ?? '').toLowerCase()
  .normalize('NFD').replace(/[\u0300-\u036f]/g, '');

/** La forma estricta: minúsculas, sin tildes y **sin símbolos** — «Modo Noche»,
 *  «modo  noche» y «MODO noche» son la misma cadena, y «¡apaga!» se queda en «apaga».
 *  Es la que comparan las reglas de `automatiza.js` y el mando de `telefono.js`. */
export const normaliza = s => sinTilde(s).replace(/[^a-z0-9 ]+/g, ' ')
  .replace(/\s+/g, ' ').trim();
