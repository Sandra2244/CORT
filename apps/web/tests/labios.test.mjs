// La agenda de labios: qué visema y cuán abierta está la boca en cada momento.
//
// Función 27 del inventario. Se prueba aquí y no en el navegador por el mismo
// motivo que la frase de activación: es aritmética sobre un texto, y a la
// aritmética no le hace falta un DOM. Lo que **no** se puede probar en Node es
// que el `.vrm` tenga esos morph targets (función 27 lo dice en FUNCTIONS.md).
import test from 'node:test'
import assert from 'node:assert/strict'

import { silabas, duracion, boca, SILABA_MS } from './labios.mjs'

test('cada vocal cuenta una sílaba', () => {
  assert.equal(silabas('hola').length, 2)
  assert.equal(silabas('casa').length, 2)
  assert.equal(silabas('sube').length, 2)
})

test('el visema sigue a la vocal', () => {
  assert.deepEqual(silabas('hola').map((s) => s.visma), ['ou', 'aa'])
  assert.deepEqual(silabas('casa').map((s) => s.visma), ['aa', 'aa'])
  assert.deepEqual(silabas('sube').map((s) => s.visma), ['ou', 'ee'])
})

test('un diptongo es una sola sílaba y manda la vocal abierta', () => {
  // «ai», «au», «ei»: la vocal cerrada (i/u) es semivocal, así que la boca se
  // abre en la otra. Es la regla fonética, no un truco para que el test pase.
  assert.deepEqual(silabas('aire').map((s) => s.visma), ['aa', 'ee'])
  assert.equal(silabas('aire').length, 2)
  assert.deepEqual(silabas('auto').map((s) => s.visma), ['aa', 'ou'])
  assert.deepEqual(silabas('bien').map((s) => s.visma), ['ee'])
})

test('dos vocales acentuadas seguidas sí son dos sílabas', () => {
  // «ma-íz»: hiato. Sin esta regla la palabra se comería una apertura de boca.
  const plan = silabas('maíz')
  assert.equal(plan.length, 2)
  assert.deepEqual(plan.map((s) => s.visma), ['aa', 'ih'])
})

test('sin vocales no hay boca que mover', () => {
  assert.deepEqual(silabas(''), [])
  assert.deepEqual(silabas('   '), [])
  assert.deepEqual(silabas('mmm'), [])
  assert.equal(duracion([]), 0)
})

test('las sílabas van en orden y nunca se montan', () => {
  const plan = silabas('la interfaz de CORT respira y parpadea')
  assert.ok(plan.length > 8, `esperaba varias sílabas, llegó ${plan.length}`)
  assert.equal(plan[0].ini, 0)
  for (let i = 1; i < plan.length; i++) {
    assert.ok(plan[i].ini >= plan[i - 1].ini + plan[i - 1].dur, `se montan en ${i}`)
    assert.ok(plan[i].dur > 0 && plan[i].dur <= SILABA_MS, `duración rara en ${i}`)
  }
  assert.equal(duracion(plan), plan[plan.length - 1].ini + plan[plan.length - 1].dur)
})

test('la puntuación hace pausas más largas que el hueco normal', () => {
  // Dos vocales sueltas, separadas por un espacio, una coma y un punto. Con
  // consonantes intermedias no hay sílaba que comparar («b» sola no abre la boca).
  const normal = silabas('o a')
  const coma = silabas('o, a')
  const punto = silabas('o. a')
  const hueco = (plan) => plan[1].ini - (plan[0].ini + plan[0].dur)
  assert.ok(hueco(coma) > hueco(normal), 'la coma no alarga el hueco')
  assert.ok(hueco(punto) > hueco(coma), 'el punto no alarga más que la coma')
})

test('la boca se abre y se cierra dentro de la sílaba', () => {
  const plan = silabas('hola')
  const primera = plan[0]
  // En los bordes está cerrada; a mitad, abierta del todo. Es el `sin` que le da
  // la forma al golpe: un diente de sierra se leería como mandíbula de robot.
  assert.equal(boca(primera.ini, plan).abierto < 0.05, true)
  assert.equal(boca(primera.ini + primera.dur, plan).abierto < 0.05, true)
  assert.ok(boca(primera.ini + primera.dur / 2, plan).abierto > 0.85)
  assert.equal(boca(primera.ini + primera.dur / 2, plan).visma, 'ou')
})

test('en el hueco entre sílabas la boca está cerrada', () => {
  const plan = silabas('hola')
  const medio = (plan[0].ini + plan[0].dur + plan[1].ini) / 2
  assert.equal(boca(medio, plan).abierto, 0)
})

test('fuera del plan no hay gesto', () => {
  const plan = silabas('hola')
  assert.equal(boca(duracion(plan) + 1000, plan).abierto, 0)
  assert.equal(boca(-50, plan).abierto, 0)
})

test('un texto largo no se sale de la realidad', () => {
  // La boca no puede ir más rápido de lo que una voz habla: ~8 sílabas por
  // segundo como techo. Si un arreglo de 40 palabras diera más, el plan estaría
  // inventando palabras.
  const plan = silabas('la interfaz de CORT respira parpadea y se mueve despacio ' +
    'mientras la nube de puntos gira alrededor del reactor morado')
  assert.ok(plan.length <= 40, `demasiadas sílabas: ${plan.length}`)
  assert.ok(duracion(plan) / 1000 >= plan.length / 9, 'la agenda va más rápido de lo que habla nadie')
})
