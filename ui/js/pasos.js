/* ── los pasos del copiloto: su estado y sus dos botones (J2.3) ───────────────
   La superficie B no es una charla bonita: es un **hilo de pasos** donde cada paso
   tiene un verde (▶ corre éste) y un rojo (✕ no corra, me lo quedo yo escrito). El
   plano de la Fase 2 (`docs/PLAN-FASE-2-JARVIS.md` §3.1) lo pide así, y su puerta de
   salida dice «un plan de 3 pasos: uno aceptado, uno RECHAZADO delante de ella, uno
   fallido con su salida». Hasta hoy la cara sólo tenía el verde; el paso rechazado no
   existía como estado, así que «no» se confundía con «aún no le di».

   Módulo PURO, como `mandos.js`, `ordenes.js` y `placa.js`: sin DOM, sin `fetch`, sin
   `localStorage`. Lo que se decide aquí se puede probar con node en el pipeline:

   · la tabla de estados y sus colores, y que un paso en `corriendo` no se pueda volver
     a tocar (doble toque = dos ejecuciones del mismo comando, y eso en un terminal es
     un desastre);
   · que `rechazado` sea TERMINAL: ni verde ni rojo después de decir «no»;
   · que lo que el núcleo marca como NO seguro (`seguro: false`) no se pueda aceptar ni
     aunque la cara lo intente —la puerta la custodia `copiloto.py`, no esta hoja—;
   · y que el resultado que llega del núcleo se traduzca en el estado que de verdad
     ocurrió: `ejecutado && ok` → ok; `ejecutado && !ok` → falló; no ejecutado → se
     enseñó, que no es lo mismo que «hecho». */

export const ESTADOS_PASO = {
  pendiente:  { color: '#7fb6d8', dice: 'pendiente' },
  corriendo:  { color: '#ff8a3d', dice: 'corriendo' },
  ok:         { color: '#2bff9e', dice: 'hizo' },
  falló:      { color: '#ff5b5b', dice: 'falló' },
  rechazado:  { color: '#c8a24b', dice: 'rechazado · tuyo' },
  enseñado:   { color: '#8f6bff', dice: 'se enseñó' },
};

/* Un paso sólo se puede aceptar si el núcleo lo marcó como seguro y si todavía está
   pendiente. Las dos cosas van juntas a propósito: sin la primera la cara se salta la
   puerta de `copiloto.py`; sin la segunda, un dedo impaciente corre el comando dos
   veces. */
export function puedeAceptar(paso) {
  return !!paso && paso.seguro === true && paso.estado === 'pendiente';
}

/* El rojo sirve para cualquier paso —también para los seguros—: rechazar nunca es
   peligroso, ejecutar sin permiso sí. */
export function puedeRechazar(paso) {
  return !!paso && (paso.estado === 'pendiente' || paso.estado === 'enseñado');
}

export function puedeCopiar(paso) {
  return !!paso && typeof paso.orden === 'string' && paso.orden.length > 0;
}

/* Las transiciones. Devuelven el estado nuevo sin tocar el objeto: quien llama
   (`pantallas.js`) decide cuándo lo pinta. */
export function arranca(paso) {
  if (!puedeAceptar(paso)) return paso ? paso.estado : 'pendiente';
  paso.estado = 'corriendo';
  return paso.estado;
}

export function rechaza(paso) {
  if (!puedeRechazar(paso)) return paso ? paso.estado : 'pendiente';
  paso.estado = 'rechazado';
  paso.resultado = { dice: 'no lo ejecuté: te lo dejo escrito para que lo corras tú' };
  return paso.estado;
}

/* Lo que devuelve `POST /api/copiloto/ejecuta`: `{ok, ejecutado, dice, salida}`. El
   matiz que importa es `ejecutado`: si el núcleo no lo ejecutó (porque le faltaba
   permiso o porque él mismo lo frenó), decir «hizo» sería mentira —va `enseñado`. */
export function cierra(paso, r = {}) {
  if (!paso || paso.estado !== 'corriendo') return paso ? paso.estado : 'pendiente';
  if (r.ejecutado && r.ok) paso.estado = 'ok';
  else if (r.ejecutado) paso.estado = 'falló';
  else paso.estado = 'enseñado';
  paso.resultado = r;
  return paso.estado;
}

/* El resumen que ve ella arriba del hilo: cuántos van de cada, dicho con los números
   que salieron de la tabla, no de un texto fijo. */
export function resumenPasos(pasos = []) {
  const cuenta = {};
  for (const p of pasos) cuenta[p.estado || 'pendiente'] = (cuenta[p.estado || 'pendiente'] || 0) + 1;
  return cuenta;
}
