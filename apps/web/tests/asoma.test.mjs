// La geometría de arrastrar una ventana sin perderla de vista.
//
// Función 82, y sexta capa pura de la cara con su prueba (regla 3 de
// `AGENTS.md`). Se separó del gancho de React por un motivo concreto: esta cuenta
// **ya estuvo mal**. Los topes emparejaban el borde de arriba del panel con el
// borde de arriba de la ventana, así que soltada la ventana en su sitio no había
// manera de bajarla —el máximo salía exactamente 0 y cualquier `dy` positivo se
// recortaba contra sí mismo—. Estaba documentado en un comentario y seguía
// estando mal; escrito como prueba, el número ya no se vuelve a ir.
import test from 'node:test'
import assert from 'node:assert/strict'

import { ASOMA_MIN, sujetar } from './asoma.mjs'

// El escenario de siempre: una ventana de 200×100 en el hueco de arriba a la
// izquierda, sobre una pantalla de 800×600 y todavía sin desplazar.
const VENTANA = { x: 800, y: 600 }
const CAJA = { left: 100, right: 300, top: 50, bottom: 150 }
const EN_SU_SITIO = { x: 0, y: 0 }

test('ASOMA_MIN son 72 píxeles, y es lo que queda de ventana por dondequiera que se suelte', () => {
  assert.equal(ASOMA_MIN, 72)

  // Hacia la izquierda: el panel sale hasta que su borde derecho toca los 72 px.
  const lejos_izq = sujetar(CAJA, EN_SU_SITIO, -5000, 0, VENTANA)
  assert.equal(lejos_izq.x, -228, 'se pasó del tope: -5000 debía recortarse a -228')
  assert.equal(CAJA.right + lejos_izq.x, ASOMA_MIN, 'el borde derecho debe quedar a 72 px del filo')

  // Hacia la derecha: entra hasta que su borde izquierdo deja 72 px al filo derecho.
  const lejos_der = sujetar(CAJA, EN_SU_SITIO, 5000, 0, VENTANA)
  assert.equal(lejos_der.x, 628)
  assert.equal(VENTANA.x - (CAJA.left + lejos_der.x), ASOMA_MIN)

  // Hacia arriba: el borde inferior del panel es el que asoma.
  const lejos_arr = sujetar(CAJA, EN_SU_SITIO, 0, -5000, VENTANA)
  assert.equal(lejos_arr.y, -78)
  assert.equal(CAJA.bottom + lejos_arr.y, ASOMA_MIN)

  // Hacia abajo: el borde superior es el que asoma.
  const lejos_abj = sujetar(CAJA, EN_SU_SITIO, 0, 5000, VENTANA)
  assert.equal(lejos_abj.y, 478)
  assert.equal(VENTANA.y - (CAJA.top + lejos_abj.y), ASOMA_MIN)
})

test('la regresión: desde su propio sitio SÍ se puede bajar la ventana', () => {
  // Con el emparejamiento viejo (borde de arriba del panel contra borde de
  // arriba de la ventana) el tope no sujetaba nada y este paso de +50
  // desaparecía: la ventana se quedaba clavada. Es el fallo de esta prueba.
  const bajada = sujetar(CAJA, EN_SU_SITIO, 0, 50, VENTANA)
  assert.deepEqual(bajada, { x: 0, y: 50 })

  // Y subida libre, mientras el panel conserve sus 72 px asomando por abajo.
  assert.deepEqual(sujetar(CAJA, EN_SU_SITIO, -40, -30, VENTANA), { x: -40, y: -30 })
})

test('un paso dentro de los topes se aplica tal cual, sin deriva', () => {
  const medio = { x: 120, y: 90 }
  assert.deepEqual(sujetar(CAJA, medio, 10, -10, VENTANA), { x: 130, y: 80 })

  // dx y dy nulos: la posición se queda donde estaba (el llamador ya corta antes,
  // pero el módulo tampoco inventa un píxel).
  assert.deepEqual(sujetar(CAJA, medio, 0, 0, VENTANA), medio)
})

test('un panel más grande que la ventana no se sale del rango ni devuelve NaN', () => {
  // Ventanita de 40×40 y caja de 100×100: los dos topes del eje se cruzan
  // (el mínimo queda por encima del máximo). Aquí es donde `recortar` con orden
  // asumido se rompería.
  const chica = { x: 40, y: 40 }
  const enorme = { left: 0, right: 100, top: 0, bottom: 100 }

  const a_la_derecha = sujetar(enorme, EN_SU_SITIO, 1000, 1000, chica)
  const a_la_izquierda = sujetar(enorme, EN_SU_SITIO, -1000, -1000, chica)
  for (const p of [a_la_derecha, a_la_izquierda]) {
    assert.ok(Number.isFinite(p.x), 'el eje x tiene que seguir siendo un número')
    assert.ok(Number.isFinite(p.y))
  }
  // Choca contra los dos topes, y se mueve de uno a otro: no se queda clavado.
  assert.notEqual(a_la_derecha.x, a_la_izquierda.x)
  assert.notEqual(a_la_derecha.y, a_la_izquierda.y)
})

test('sólo lee left/right/top/bottom: un DOMRect de verdad vale, y nadie muta', () => {
  const caja_con_todo = { ...CAJA, width: 200, height: 100, x: 100, y: 50 }
  const actual = { x: 7, y: 9 }
  const viewport = { x: 800, y: 600 }
  const antes = { ...actual }

  assert.deepEqual(sujetar(caja_con_todo, actual, 1, 1, viewport), { x: 8, y: 10 })

  // `useArrastre` guarda el resultado en el estado de React: si `sujetar`
  // devolviera el mismo objeto que recibió, la cara no se repintaría.
  const r = sujetar(caja_con_todo, actual, 0, 0, viewport)
  assert.notEqual(r, actual, 'devuelve un punto nuevo, no el mismo mutado')
  assert.deepEqual(actual, antes, 'no toca el punto que le pasa el llamador')
})
