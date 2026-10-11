import { test } from 'node:test'
import assert from 'node:assert/strict'
import { faseDe, FASE_TEXTO } from './fase.mjs'

const S = (micro, tts, core) => ({ micro, tts, core })

/**
 * Ocho señales, ocho respuestas: la tabla completa de combinaciones. No es una
 * prueba por gusto — la prioridad (habla > piensa > escucha) es lo único que
 * impide que la cara mienta mientras el micrófono sigue encendido durante la
 * respuesta, y una prioridad sólo se ve romperse en las combinaciones donde dos
 * señales son ciertas a la vez.
 */
test('sin señales, reposo', () => {
  assert.equal(faseDe(S(false, false, false)), 'reposo')
})

test('el micrófono solo es escucha', () => {
  assert.equal(faseDe(S(true, false, false)), 'escucha')
})

test('el core solo es piensa', () => {
  assert.equal(faseDe(S(false, false, true)), 'piensa')
})

test('la voz sola es habla', () => {
  assert.equal(faseDe(S(false, true, false)), 'habla')
})

test('habla gana a todo: la prioridad es deliberada', () => {
  assert.equal(faseDe(S(true, true, true)), 'habla')
  assert.equal(faseDe(S(true, true, false)), 'habla')
  assert.equal(faseDe(S(false, true, true)), 'habla')
})

test('piensa gana a escucha', () => {
  assert.equal(faseDe(S(true, false, true)), 'piensa')
})

test('apagar las tres de una vez devuelve reposo, no la fase anterior', () => {
  // La pureza importa: `connection.ts` cachea la fase y sólo avisa cuando
  // cambia; si el cálculo dependiera de estado, la cara se anclaría en 'habla'.
  assert.equal(faseDe(S(true, true, true)), 'habla')
  assert.equal(faseDe(S(false, false, false)), 'reposo')
})

test('los campos ausentes cuentan como false, no como fase inventada', () => {
  // Los manejadores del navegador pueden llamar con un hueco; `faseDe` defensivo.
  assert.equal(faseDe({}), 'reposo')
  assert.equal(faseDe({ micro: undefined, tts: true }), 'habla')
})

test('la función no muta las señales que recibe', () => {
  const s = S(true, false, false)
  const copia = { ...s }
  faseDe(s)
  assert.deepEqual(s, copia)
})

test('cada fase tiene su etiqueta legible', () => {
  // El `title` del punto de fase: la cara explica sin párrafos.
  for (const f of ['reposo', 'escucha', 'piensa', 'habla']) {
    assert.equal(typeof FASE_TEXTO[f], 'string')
    assert.ok(FASE_TEXTO[f].length > 0)
  }
  assert.deepEqual(Object.keys(FASE_TEXTO).sort(), ['escucha', 'habla', 'piensa', 'reposo'])
})
