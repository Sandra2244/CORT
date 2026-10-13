/**
 * Pruebas de la frase de activación de CORT — la única parte de la voz que es
 * lógica pura, y por eso la única que se puede probar sin navegador.
 *
 * Se ejecutan con `make test-web`, que transpila `src/cort/activacion.ts` con el
 * paquete `typescript` que **ya** está en `devDependencies` y corre este archivo
 * con el `node --test` que trae Node 20. No hay ninguna librería nueva: en una
 * máquina de 1,8 GiB un `vitest` con su jsdom es memoria que el reactor deja de
 * pintar, y a una función que recibe un string no le hace falta un DOM.
 *
 * Lo que **no** cubre este archivo: el micrófono, el pitido, el turno de habla y
 * el cable con la escena. Eso se comprueba en navegador y se dice como tal en
 * `docs/STATUS.md`.
 */

import test from 'node:test'
import assert from 'node:assert/strict'
import { buscarActivacion } from './activacion.mjs'

// -- despierta ---------------------------------------------------------------

test('la frase sola despierta y no deja orden', () => {
  assert.equal(buscarActivacion('ok cort'), '')
  assert.equal(buscarActivacion('hola cort'), '')
  assert.equal(buscarActivacion('oye cort'), '')
})

test('la orden de corrido ya viene separada', () => {
  assert.equal(buscarActivacion('ok cort sube el volumen'), 'sube el volumen')
  assert.equal(buscarActivacion('hola cort, haz una captura'), 'haz una captura')
  assert.equal(
    buscarActivacion('¡oye CORT! pausa la música'),
    'pausa la música',
  )
})

test('da igual mayúsculas y minúsculas', () => {
  assert.equal(buscarActivacion('OK Cort baja el volumen'), 'baja el volumen')
  assert.equal(buscarActivacion('Oye CoRt'), '')
})

test('lo que el reconocedor entiende cuando la palabra sale rápida', () => {
  assert.equal(buscarActivacion('hey kort captura la pantalla'), 'captura la pantalla')
  assert.equal(buscarActivacion('ok cortte el reloj'), 'el reloj')
  assert.equal(buscarActivacion('o.k. cort hola'), 'hola')
})

test('se puede hablar delante sin romper la frase', () => {
  assert.equal(buscarActivacion('a ver ok cort qué hora es'), 'qué hora es')
})

// -- NO despierta ------------------------------------------------------------

test('el nombre suelto no despierta: hace falta el saludo', () => {
  assert.equal(buscarActivacion('cort'), null)
  assert.equal(buscarActivacion('sube el volumen'), null)
})

test('palabras que empiezan como el nombre no lo son', () => {
  // El lookahead `(?![a-záéíóúñ])` es la única barrera entre «ok cort» y
  // «ok cortometraje»: sin él, la usuaria diría «cortar» y CORT se pondría a
  // escuchar.
  assert.equal(buscarActivacion('ok cortometraje'), null)
  assert.equal(buscarActivacion('hola corte de manga'), null)
  assert.equal(buscarActivacion('oye cortedad'), null)
})

test('un saludo sin nombre detrás no despierta', () => {
  assert.equal(buscarActivacion('hola, cómo estás'), null)
  assert.equal(buscarActivacion('ok vale'), null)
})

test('el saludo y el nombre tienen que estar pegados', () => {
  // «hola» aquí saluda a una persona; la orden no es para CORT.
  assert.equal(buscarActivacion('hola Laura, cortá la música'), null)
})

test('el espacio vacío no es una frase de activación', () => {
  assert.equal(buscarActivacion(''), null)
  assert.equal(buscarActivacion('   '), null)
})

// -- forma de la respuesta ---------------------------------------------------

test('la orden viene recortada, sin espacios sobrantes', () => {
  assert.equal(buscarActivacion('ok cort    sube el volumen   '), 'sube el volumen')
})

test('nunca devuelve la frase de activación dentro de la orden', () => {
  for (const frase of ['ok cort sube el volumen', 'oye cort, qué hora es']) {
    const resto = buscarActivacion(frase)
    assert.notEqual(resto, null)
    assert.ok(!/cort/i.test(resto), `«${resto}» aún lleva el nombre`)
  }
})
