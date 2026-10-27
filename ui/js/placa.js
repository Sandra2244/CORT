/* ── la placa de arriba (paso 1.3 de la Fase 1) ─────────────────────────────────
   El cuadro monoespaciado de la referencia: hora, fecha, el nodo que contesta
   (PC o teléfono), el modelo que respondió y el estado de CORT. Vive en un módulo
   PURO —sin DOM, sin `window`, sin red— por la misma razón que `mandos.js` y
   `ordenes.js`: se puede ejercitar con node en el pipeline, y ahí se comprueba la
   única regla que importa, la *honestidad*:

   · Lo que no se puede medir NO se pinta. Nunca sale `undefined`, ni `null`, ni un
     guiño inventado. Si el núcleo no dijo con qué modelo habló, esa fila se omite;
     si Java no ha medido el aparato, no se pone «teléfono» de adorno.
   · Cada campo entra por su nombre y se valida antes de rendersar; el valor se
     escapa en `hud.js`, que es donde toca el DOM.

   `hud.js` es el único que la monta: el reloj corre en un intervalo, el estado lo
   cambia `setState()`, el nodo y el modelo los trae `refreshStatus()` / las respuestas
   del núcleo. Aquí sólo hay reglas. */

/* Los estados de la cara, con la palabra corta que pinta la placa. Vienen de `LAMP`
   en `hud.js`; si un estado no está en la tabla, la placa se queda como estaba en vez
   de imprimir la clave cruda. */
export const ESTADOS_PLACA = {
  escucha: 'escuchando',
  pensando: 'piensa',
  hablando: 'habla',
  listo: 'lista',
  reposo: 'reposo',
  oculto: 'hud oculto',
  error: 'sin conexión',
};

/* El nodo: sólo las dos palabras que son verdad según el aparato, y NINGUNA si el
   dato no es un booleano limpio. Decir «PC» porque `IS_ANDROID` llegó `undefined`
   sería mentir en el teléfono: la regla de la placa es callarse cuando no se mide.
   `IS_ANDROID` lo decide `hud.js`, que es el que conoce el puente. */
export function nombreNodo(esAndroid) {
  if (esAndroid === true) return 'teléfono';
  if (esAndroid === false) return 'PC';
  return '';
}

/* Hora y fecha en español, de 24 horas, sin segundos para que la placa no parpadee.
   `ahora` entra por parámetro para que la prueba pueda congelar el reloj. */
export function horaPlaca(ahora) {
  const d = ahora instanceof Date ? ahora : new Date(ahora);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString('es-MX', { hour12: false, hour: '2-digit', minute: '2-digit' });
}
export function fechaPlaca(ahora) {
  const d = ahora instanceof Date ? ahora : new Date(ahora);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' });
}

/* La regla dura. `medible()` descarta todo lo que no es un dato: el `undefined`, el
   `null`, el vacío, el espacio, los objetos (que stringueados dan `[object Object]`,
   el peor cuadro que se puede pintar), los booleanos, los ceros y —por si algún
   llamador stringueó antes de llegar aquí— las palabras «undefined», «null» y «NaN»
   escritas tal cual, que son las que alguna vez se vieron en la placa. También quita
   el `--:--:--` de fábrica, que es un adorno del HTML, no una hora medida. */
export function medible(v) {
  if (typeof v !== 'string' && typeof v !== 'number') return false;
  if (typeof v === 'number' && (!Number.isFinite(v) || v === 0)) return false;
  const s = String(v).trim();
  if (!s) return false;
  if (s === 'undefined' || s === 'null' || s === 'NaN') return false;
  if (/^[-–—:.· ]+$/.test(s)) return false;     // «--», «--:--:--», «·», «…»
  return true;
}

/* Los campos que se van a pintar, en el orden fijo de la placa. Cada uno es
   `{ k, v }` con `v` ya limpio; los que no miden nada sencillamente no están. */
export function camposPlaca(d = {}) {
  const estado = ESTADOS_PLACA[d.estado] || '';
  const pares = [
    ['hora', d.hora],
    ['fecha', d.fecha],
    ['nodo', d.nodo],
    ['modelo', d.modelo],
    ['estado', estado],
  ];
  return pares.filter(([k, v]) => medible(v)).map(([k, v]) => ({ k, v: String(v).trim() }));
}

/* El texto plano, para la prueba y para el `title` del panel (un lector de pantalla
   lee la placa entera, no cinco nodos sueltos). */
export function textoPlaca(d = {}, sep = ' · ') {
  return camposPlaca(d).map(c => c.v).join(sep);
}
