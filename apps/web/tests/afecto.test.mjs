// De la palabra que manda el core a los pesos que entiende el cuerpo 3D.
//
// Función 29. Lo que se prueba aquí es el **mapeo**, y es la parte que puede
// romperse en silencio: si un `mood` llegara escrito distinto, o llegara un
// estado que no está en el inventario, la cara no debe quedarse con la sonrisa
// del mensaje anterior ni pintarse de un gesto que nadie pidió.
import test from 'node:test'
import assert from 'node:assert/strict'

import { MOODS, esMood, expresionesPara, moodVigente, MOOD_MS } from './afecto.mjs'

const CLAVES = ['happy', 'sad', 'surprised', 'relaxed', 'angry'].sort()

test('el vocabulario es el que viaja por el cable', () => {
  assert.deepEqual([...MOODS].sort(), ['calm', 'happy', 'relaxed', 'sad', 'surprised'])
})

test('todo mood conocido tiene su cara, y toda la cara está entre 0 y 1', () => {
  for (const mood of MOODS) {
    const e = expresionesPara(mood)
    assert.deepEqual(Object.keys(e).sort(), CLAVES, `${mood} no trae las cinco expresiones`)
    for (const k of CLAVES) {
      assert.ok(e[k] >= 0 && e[k] <= 1, `${mood}.${k} = ${e[k]} está fuera de 0..1`)
    }
  }
})

test('lo que la interfaz no conoce es reposo, no un gesto a medias', () => {
  for (const raro of [null, undefined, '', 'enfado', 'ANGRY', 42, {}, 'calmdown']) {
    assert.deepEqual(expresionesPara(raro), expresionesPara('calm'), `${String(raro)} no cayó a reposo`)
  }
})

test('la cara de reposo no sonríe de más ni frunce', () => {
  const calma = expresionesPara('calm')
  assert.ok(calma.happy <= 0.2, 'reposo con sonrisa alta es una máscara fija')
  assert.equal(calma.sad, 0)
  assert.equal(calma.surprised, 0)
})

test('cada estado tiene su firma legible', () => {
  assert.ok(expresionesPara('happy').happy > 0.6)
  assert.ok(expresionesPara('sad').sad > 0.5)
  assert.ok(expresionesPara('surprised').surprised > 0.5)
  assert.ok(expresionesPara('relaxed').relaxed > 0.4)
})

test('la tristeza no se pinta con sonrisa', () => {
  const triste = expresionesPara('sad')
  assert.ok(triste.happy < 0.1, `happy ${triste.happy} en un estado triste`)
  assert.ok(triste.happy < expresionesPara('calm').happy, 'triste no puede sonreír más que en reposo')
})

test('CORT no le devuelve el enfado a quien le habla', () => {
  // `angry` existe en el VRM y el mapeo lo deja en cero a propósito: el enfado
  // no es un estado que el asistente pueda afirmar de sí mismo (regla 11).
  for (const mood of [...MOODS, 'fallo', null]) {
    assert.equal(expresionesPara(mood).angry, 0, `${String(mood)} puso enfado`)
  }
})

test('el nombre se reconoce con mayúsculas y espacios de sobra', () => {
  assert.equal(esMood(' Happy '), 'happy')
  assert.equal(esMood('no_sé_qué_es_esto'), null)
  assert.equal(esMood('calm'), 'calm')
})

test('un estado caduca: la cara vuelve a su sitio sola', () => {
  assert.equal(moodVigente('happy', 1000, 1000 + MOOD_MS - 1), 'happy')
  assert.equal(moodVigente('happy', 1000, 1000 + MOOD_MS + 1), 'calm')
  assert.equal(moodVigente('relaxed', 5000, 0), 'calm', 'el reloj no puede volver atrás')
})

test('un estado desconocido no caduca nunca porque no llegó a empezar', () => {
  assert.equal(moodVigente('ira', 0, 10), 'calm')
})
