/**
 * Pruebas de la capa de paneles de la interfaz.
 *
 * Se ejecutan con `make test-web`, que transpila `src/cort/paneles.ts` con el
 * paquete `typescript` que **ya** está en `devDependencies` y corre este archivo
 * con el `node --test` que trae Node 20. No se añade ninguna librería de tests:
 * en una máquina de 1,8 GiB de RAM un `vitest` con su navegador simulado es
 * memoria que el reactor deja de tener, y lo que se comprueba aquí son funciones
 * puras —un reductor de estado y una tabla de teclas— que no necesitan DOM.
 *
 * Lo que **no** cubre este archivo: el cable entre el estado y el navegador
 * (los escuchadores de puntero, teclado y el temporizador del desvanecido).
 * Eso se verificó a mano en el navegador, y está dicho en `docs/STATUS.md`.
 */

import test from 'node:test'
import assert from 'node:assert/strict'
import {
  INACTIVO_MS,
  PANELES,
  abrir,
  alternar,
  alternarCara,
  cerrarTodo,
  debeAtenuar,
  teclaAccion,
} from './paneles.mjs'

/** El estado con el que arranca la interfaz: nada expandido, la cara encendida. */
const reposo = { abierto: null, cara: true }

test('el riel trae seis paneles, cada uno con su tecla número', () => {
  assert.equal(PANELES.length, 6)
  assert.deepEqual(PANELES.map((p) => p.id), [
    'mensajes',
    'telemetria',
    'voz',
    'atuendos',
    'camara',
    'teclas',
  ])
  // Los identificadores van en inglés (es código) y lo que se lee en pantalla en
  // español (es interfaz): son las dos lenguas que pide AGENTS.md.
  assert.deepEqual(PANELES.map((p) => p.etiqueta), [
    'mensajes',
    'telemetría',
    'voz',
    'atuendos',
    'cámara',
    'teclas',
  ])
  assert.deepEqual(PANELES.map((p) => p.tecla), ['1', '2', '3', '4', '5', '6'])
  assert.equal(new Set(PANELES.map((p) => p.id)).size, 6)
})

test('tocar un panel guardado lo abre', () => {
  assert.deepEqual(alternar(reposo, 'voz'), { abierto: 'voz', cara: true })
})

test('tocarlo otra vez lo guarda', () => {
  assert.deepEqual(alternar({ abierto: 'voz', cara: true }, 'voz'), reposo)
})

test('un panel abierto a la vez: al cambiar, el anterior se guarda solo', () => {
  // Es el patrón de los videos de referencia: un hilo del borde se ensancha y los
  // demás vuelven a su trazo fino. Dos paneles expandidos peleándose por la
  // pantalla es justo la sobrecarga que Sandra pidió eliminar.
  const conMensajes = { abierto: 'mensajes', cara: true }
  assert.deepEqual(alternar(conMensajes, 'atuendos'), { abierto: 'atuendos', cara: true })
  assert.deepEqual(abrir(conMensajes, 'teclas'), { abierto: 'teclas', cara: true })
})

test('abrir es idempotente: pulsar dos veces el mismo panel no lo cierra', () => {
  // `abrir` es el camino del cursor (entrar en el riel expande); `alternar` es el
  // del dedo y del teclado (pulsar guarda). Confundirlos haría que pasar el ratón
  // por encima de lo ya abierto lo cerrara.
  const abierto = { abierto: 'voz', cara: true }
  assert.deepEqual(abrir(abierto, 'voz'), abierto)
})

test('cerrar todo guarda el panel pero deja la cara encendida', () => {
  assert.deepEqual(cerrarTodo({ abierto: 'camara', cara: true }), reposo)
  // Con la cara apagada, `Esc` no la enciende: eso es tecla de más y manda `H`.
  assert.deepEqual(cerrarTodo({ abierto: 'camara', cara: false }), { abierto: null, cara: false })
})

test('apagar la cara se lleva los paneles por delante, y encenderla no los devuelve', () => {
  assert.deepEqual(alternarCara({ abierto: 'mensajes', cara: true }), { abierto: null, cara: false })
  assert.deepEqual(alternarCara({ abierto: null, cara: false }), reposo)
})

test('con la cara apagada, tocar un panel la enciende', () => {
  // Un panel que se abre y no se pinta es un estado huérfano: la usuaria pulsa y
  // no pasa nada. El único modo de que la cara vuelva sin teclado es ése.
  const apagada = { abierto: null, cara: false }
  assert.deepEqual(alternar(apagada, 'mensajes'), { abierto: 'mensajes', cara: true })
  assert.deepEqual(abrir(apagada, 'voz'), { abierto: 'voz', cara: true })
})

test('las teclas de siempre: `Esc` guarda, `H` apaga la cara, `?` ayuda, `/` escribe', () => {
  assert.equal(teclaAccion({ key: 'Escape' }, false), 'esc')
  assert.equal(teclaAccion({ key: 'h' }, false), 'cara')
  assert.equal(teclaAccion({ key: 'H' }, false), 'cara')
  assert.equal(teclaAccion({ key: '?' }, false), 'ayuda')
  assert.equal(teclaAccion({ key: '/' }, false), 'campo')
})

test('los números del 1 al 6 abren su panel, y el 7 no existe', () => {
  assert.equal(teclaAccion({ key: '1' }, false), 'mensajes')
  assert.equal(teclaAccion({ key: '2' }, false), 'telemetria')
  assert.equal(teclaAccion({ key: '6' }, false), 'teclas')
  assert.equal(teclaAccion({ key: '7' }, false), null)
  assert.equal(teclaAccion({ key: '0' }, false), null)
})

test('mientras se escribe, la única tecla que escucha CORT es `Esc`', () => {
  // Sin esta regla, escribir «hola, abre la cámara» en el campo de mensaje
  // mandaría dos teclas fantasma al riel. Es el atajo convertido en trampa.
  assert.equal(teclaAccion({ key: 'h' }, true), null)
  assert.equal(teclaAccion({ key: '/' }, true), null)
  assert.equal(teclaAccion({ key: '?' }, true), null)
  assert.equal(teclaAccion({ key: '1' }, true), null)
  assert.equal(teclaAccion({ key: 'Escape' }, true), 'esc')
})

test('las teclas con modificador no son de CORT', () => {
  // `Ctrl+H` es «historial» del navegador y `Cmd+…` es de la persona. Quedárselas
  // rompería dos atajos que ella ya tiene en la memoria muscular.
  for (const mod of [{ ctrlKey: true }, { metaKey: true }, { altKey: true }]) {
    assert.equal(teclaAccion({ key: 'h', ...mod }, false), null)
    assert.equal(teclaAccion({ key: '1', ...mod }, false), null)
    assert.equal(teclaAccion({ key: 'Escape', ...mod }, false), null)
  }
})

test('las teclas que no significan nada no significan nada', () => {
  for (const key of ['a', ' ', 'Enter', 'Tab', 'ArrowLeft', 'Shift', 'F5', 'ñ']) {
    assert.equal(teclaAccion({ key }, false), null, `${key} no debe hacer nada`)
  }
})

test('la interfaz se atenúa sola cuando nadie la toca y no hay nada abierto', () => {
  const ahora = 1_000_000
  assert.equal(debeAtenuar({ ...reposo, ultimaActividad: ahora - INACTIVO_MS, ahora }), true)
  // Un milisegundo antes, todavía no.
  assert.equal(
    debeAtenuar({ ...reposo, ultimaActividad: ahora - INACTIVO_MS + 1, ahora }),
    false,
  )
})

test('un panel abierto, o la cara ya apagada, no se atenúan', () => {
  const ahora = 1_000_000
  const viejo = ahora - INACTIVO_MS * 3
  assert.equal(debeAtenuar({ abierto: 'voz', cara: true, ultimaActividad: viejo, ahora }), false)
  assert.equal(debeAtenuar({ abierto: null, cara: false, ultimaActividad: viejo, ahora }), false)
})

test('con movimiento reducido no hay apagado por reloj: sólo manda la persona', () => {
  // Una interfaz que se apaga sola es una animación; si el sistema pide no
  // animar, la pantalla no tiene derecho a decidir por encima de esa petición.
  assert.equal(
    debeAtenuar({ ...reposo, ultimaActividad: 0, ahora: 10_000_000, reduceMotion: true }),
    false,
  )
})

test('el rato de inactividad es un rato razonable', () => {
  // Menos de cinco segundos parpadea mientras se lee; más de medio minuto no se
  // nota nunca. El número no es estética: es lo que hace que el gesto exista.
  assert.ok(INACTIVO_MS >= 5000 && INACTIVO_MS <= 30000, `INACTIVO_MS = ${INACTIVO_MS}`)
})
