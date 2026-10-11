/**
 * Pruebas de la pila de ventanas de vidrio (capa L3, N1 de docs/REDESIGN-NUCLEO.md).
 *
 * Se ejecutan con `make test-web`, que transpila `src/cort/ventanas.ts` con el
 * paquete `typescript` que **ya** está en `devDependencies` y corre este archivo
 * con el `node --test` de Node 20. Sin `vitest` ni jsdom: lo que se comprueba
 * aquí son funciones puras —una pila de ventanas y una tabla de teclas—, y a
 * las funciones puras no les hace falta un DOM.
 *
 * Lo que **no** cubre este archivo: el arrastre con sujeción (ya medido en DOM
 * desde `v0.11` y reusado tal cual), el `backdrop-filter` de los tres vidrios y
 * el cable estado→pantalla. Eso se verifica en navegador y se cuenta en
 * `docs/STATUS.md`.
 */

import test from 'node:test'
import assert from 'node:assert/strict'
import {
  SECCIONES,
  VIDRIOS,
  VIDRIO_INICIAL,
  abrir,
  alternar,
  cerrar,
  cerrarTodo,
  esc,
  frente,
  reposo,
  seccionPorTecla,
  siguienteVidrio,
} from './ventanas.mjs'

test('las cinco secciones con su etiqueta y su tecla, en orden', () => {
  assert.deepEqual(SECCIONES.map((s) => s.id), ['voz', 'camara', 'atuendos', 'sistema', 'ayuda'])
  assert.deepEqual(SECCIONES.map((s) => s.tecla), ['1', '2', '3', '4', '5'])
  assert.deepEqual(SECCIONES.map((s) => s.etiqueta), ['voz', 'cámara', 'atuendos', 'sistema', 'ayuda'])
})

test('en reposo no hay ninguna ventana y el vidrio es el del medio', () => {
  assert.deepEqual(reposo.pilas, [])
  assert.equal(reposo.vidrio, VIDRIO_INICIAL)
  assert.equal(VIDRIO_INICIAL, 1)
  assert.equal(frente(reposo), null)
})

test('abrir apila al frente y abrir dos veces no duplica: trae al frente', () => {
  let st = abrir(reposo, 'voz')
  st = abrir(st, 'sistema')
  assert.deepEqual(st.pilas, ['voz', 'sistema'])
  assert.equal(frente(st), 'sistema')
  st = abrir(st, 'voz')
  assert.deepEqual(st.pilas, ['sistema', 'voz'])
  assert.equal(frente(st), 'voz')
})

test('tocar una ventana detrás la trae al frente sin cerrar las demás', () => {
  const st = abrir(abrir(abrir(reposo, 'camara'), 'ayuda'), 'voz')
  const traida = abrir(st, 'camara')
  assert.deepEqual(traida.pilas, ['ayuda', 'voz', 'camara'])
  assert.equal(traida.pilas.length, 3)
})

test('cerrar oculta sólo esa ventana; cerrar lo que no está no cambia nada', () => {
  const st = abrir(abrir(reposo, 'voz'), 'atuendos')
  assert.deepEqual(cerrar(st, 'voz').pilas, ['atuendos'])
  assert.deepEqual(cerrar(st, 'ayuda').pilas, ['voz', 'atuendos'])
  assert.equal(cerrar(st, 'ayuda'), st, 'sin cambios, el mismo objeto: el state no se sacude')
})

test('alternar es la tecla: abre si no estaba, oculta si estaba', () => {
  const abierto = alternar(reposo, 'sistema')
  assert.deepEqual(abierto.pilas, ['sistema'])
  assert.deepEqual(alternar(abierto, 'sistema').pilas, [])
  // Alternar una ventana que existe pero NO está al frente la oculta sin tocar la pila de las demás.
  const dos = abrir(abierto, 'ayuda')
  assert.deepEqual(alternar(dos, 'sistema').pilas, ['ayuda'])
})

test('el Esc despide el frente y devuelve null sólo cuando ya no queda ninguna', () => {
  const st = abrir(abrir(reposo, 'voz'), 'ayuda')
  const tras = esc(st)
  assert.notEqual(tras, null)
  assert.deepEqual(tras.pilas, ['voz'])
  const tras2 = esc(tras)
  assert.deepEqual(tras2.pilas, [])
  assert.equal(esc(tras2), null, 'null es la señal de que el Esc sigue bajando a la bandeja')
})

test('cerrarTodo limpia la pila de un golpe y no inventa cambios en vacío', () => {
  const st = abrir(abrir(reposo, 'voz'), 'camara')
  assert.deepEqual(cerrarTodo(st).pilas, [])
  assert.equal(cerrarTodo(reposo), reposo)
})

test('el vidrio cyclea opaco → vidrio → bruma → opaco', () => {
  assert.equal(VIDRIOS.length, 3)
  assert.equal(siguienteVidrio(0), 1)
  assert.equal(siguienteVidrio(1), 2)
  assert.equal(siguienteVidrio(2), 0)
  assert.deepEqual(VIDRIOS.map((v) => v.nombre), ['opaco', 'vidrio', 'bruma'])
})

test('la tecla manda su sección y nada más; el resto no es de ventanas', () => {
  assert.equal(seccionPorTecla('1'), 'voz')
  assert.equal(seccionPorTecla('5'), 'ayuda')
  assert.equal(seccionPorTecla('0'), null)
  assert.equal(seccionPorTecla('6'), null)
  assert.equal(seccionPorTecla('x'), null)
})

test('las operaciones puras no tocan el estado anterior', () => {
  const st = abrir(abrir(reposo, 'voz'), 'ayuda')
  const copia = { pilas: [...st.pilas], vidrio: st.vidrio }
  cerrar(st, 'voz')
  abrir(st, 'sistema')
  siguienteVidrio(st.vidrio)
  assert.deepEqual(st, copia, 'el estado viejo sigue intacto tras cerrar, abrir y cyclear')
})
