/* ===== md.js · el markdown mínimo de la Charla, y la hora de sus burbujas =====
 *
 * Está aquí por la misma razón que `texto.js`: son dos trozos de la cara que deciden
 * **cómo se lee una respuesta del modelo**, y se pueden comprobar sin pantalla, sin
 * teléfono y sin red. `pantallas.js` tenía 3.200 líneas y lo primero que sobraba no
 * era una pantalla entera —era lógica de texto escondida dentro de una pantalla—.
 *
 * La regla que sostiene el archivo, y que está escrita en `md`: **primero se escapa
 * TODO, después se reconocen los bloques**. Al revés, una respuesta con `<script>` se
 * cuela como código vivo; y como el modelo contesta lo que conteste, esa orden la daría
 * el navegador de la dueña. Los bloques de código se guardan aparte (`trozos`) y se
 * devuelven al final por su marca `\u0001n\u0001`, para que las negritas o los enlaces
 * no toquen lo que hay dentro de un `<pre>`.
 */
import { esc } from './texto.js';

/** `ms` → «14:07» en español; `0`, `null` o un texto → cadena vacía (la burbuja no
 *  enseña «NaN:NaN» ni una hora de fábrica). */
export function horaDe(ms) {
  const n = Number(ms);
  if (!Number.isFinite(n) || n <= 0) return '';
  try { return new Date(n).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' }); }
  catch { return ''; }
}

/** Markdown mínimo y seguro: bloque de código, código en línea, negritas y enlaces. */
export function md(texto) {
  const trozos = [];
  let s = esc(String(texto == null ? '' : texto));
  s = s.replace(/```([^\n`]*)\n?([\s\S]*?)```/g, (_, lengua, codigo) => {
    trozos.push('<pre class="bur-pre"><code>' + codigo.replace(/\n+$/, '') + '</code></pre>');
    return '\u0001' + (trozos.length - 1) + '\u0001';
  });
  s = s.replace(/`([^`\n]+)`/g, '<code class="bur-code">$1</code>');
  s = s.replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>');
  s = s.replace(/(^|[\s(])(https?:\/\/[^\s<)]+)/g,
    '$1<a href="$2" target="_blank" rel="noopener">$2</a>');
  s = s.replace(/\n/g, '<br>');
  return s.replace(/\u0001(\d+)\u0001/g, (_, i) => trozos[+i] || '');
}
