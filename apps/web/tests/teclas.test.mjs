// Del teclado a la pila de ventanas, sin navegador.
//
// Función 76 (regla 3 de `AGENTS.md`). Lo que se prueba aquí son **decisiones**,
// y son decisiones que se rompen en silencio: si alguien mueve un acceso de sitio
// en el muelle, si el campo de la charla se traga un `Esc`, si un `Cmd+1` del
// navegador acaba abriendo una ventana. Ninguna de esas se ve hasta que alguien
// pulsa, y todas caben en una función pura.
import test from 'node:test'
import assert from 'node:assert/strict'

import {
  ACCESOS,
  ventanaPorTecla,
  accionDeTecla,
  despedirFrente,
  traerAlFrente,
  conmutar,
  despedir,
} from './teclas.mjs'

const IDS = ['charla', 'voz', 'camara', 'cuerpo', 'sistema', 'ayuda']

test('la tabla tiene seis accesos, en orden, y cada uno con su número', () => {
  assert.deepEqual(
    ACCESOS.map((a) => a.id),
    IDS,
  )
  assert.deepEqual(
    ACCESOS.map((a) => a.tecla),
    ['1', '2', '3', '4', '5', '6'],
  )
  for (const a of ACCESOS) {
    assert.ok(a.etiqueta.length > 0, `${a.id} no tiene nombre`)
  }
})

test('el muelle y el teclado leen la misma tabla: a su tecla corresponde su ventana', () => {
  for (const a of ACCESOS) {
    assert.equal(ventanaPorTecla(a.tecla), a.id)
  }
  for (const sobrero of ['0', '7', '9', 'a', '', ' 1', '1 ']) {
    assert.equal(ventanaPorTecla(sobrero), null, `«${sobrero}» no debía abrir nada`)
  }
})

test('Esc despide la ventana de enfrente, y lo hace aunque se esté escribiendo', () => {
  assert.deepEqual(accionDeTecla({ key: 'Escape' }), { tipo: 'cerrar-frente' })
  assert.deepEqual(
    accionDeTecla({ key: 'Escape', escribiendo: true }),
    { tipo: 'cerrar-frente' },
    'sin esto, Esc no te saca del campo de la charla',
  )
})

test('Ctrl+/ y Cmd+/ saltan a la charla con las manos dentro del campo', () => {
  for (const e of [
    { key: '/', ctrlKey: true },
    { key: '/', metaKey: true },
    { key: '/', ctrlKey: true, escribiendo: true },
  ]) {
    assert.deepEqual(
      accionDeTecla(e),
      { tipo: 'abrir', id: 'charla', evitar: true },
      JSON.stringify(e),
    )
  }
})

test('dentro de un campo, `/` y los números vuelven a ser texto', () => {
  for (const key of ['/', '?', '1', '6']) {
    assert.equal(
      accionDeTecla({ key, escribiendo: true }),
      null,
      `«${key}» writing no debía invocar una ventana`,
    )
  }
})

test('`/` abre la charla y pide anular el tecleo; `?` abre la ayuda sin anular nada', () => {
  assert.deepEqual(accionDeTecla({ key: '/' }), { tipo: 'abrir', id: 'charla', evitar: true })
  // `?` sale con Shift en casi todos los teclados: si Shift contara como
  // modificador, la ayuda sería inalcanzable con el teclado.
  assert.deepEqual(
    accionDeTecla({ key: '?', shiftKey: true }),
    { tipo: 'abrir', id: 'ayuda', evitar: false },
  )
})

test('los números abren su ventana; con Ctrl, Alt o Meta no se toca nada', () => {
  assert.deepEqual(accionDeTecla({ key: '3' }), {
    tipo: 'abrir',
    id: 'camara',
    evitar: false,
  })
  assert.deepEqual(accionDeTecla({ key: '6' }), { tipo: 'abrir', id: 'ayuda', evitar: false })
  for (const e of [
    { key: '1', ctrlKey: true },
    { key: '1', metaKey: true },
    { key: '1', altKey: true },
  ]) {
    assert.equal(accionDeTecla(e), null, JSON.stringify(e))
  }
  assert.equal(accionDeTecla({ key: 'x' }), null)
})

test('Esc cierra sólo la de enfrente: con tres abiertas quedan las otras dos', () => {
  assert.deepEqual(despedirFrente(['charla', 'voz', 'ayuda']), ['charla', 'voz'])
  assert.deepEqual(despedirFrente(['charla']), [])
  assert.deepEqual(despedirFrente([]), [], 'sin ventanas, Esc no inventa nada')

  const pila = ['charla', 'voz']
  despedirFrente(pila)
  assert.deepEqual(pila, ['charla', 'voz'], 'mutó la pila: React no pintaría el cambio')
})

test('traer al frente mueve, no duplica', () => {
  const pila = ['charla', 'voz', 'ayuda']
  assert.deepEqual(traerAlFrente(pila, 'charla'), ['voz', 'ayuda', 'charla'])
  assert.deepEqual(traerAlFrente(pila, 'sistema'), ['charla', 'voz', 'ayuda', 'sistema'])
  assert.deepEqual(pila, ['charla', 'voz', 'ayuda'])
})

test('el muelle enciende y apaga: conmutar abre si no estaba y despide si estaba', () => {
  assert.deepEqual(conmutar(['voz'], 'charla'), ['voz', 'charla'])
  assert.deepEqual(conmutar(['voz', 'charla'], 'voz'), ['charla'])
  assert.deepEqual(conmutar([], 'ayuda'), ['ayuda'])
})

test('despedir quita una sola y deja el orden de las demás', () => {
  assert.deepEqual(despedir(['charla', 'voz', 'ayuda'], 'voz'), ['charla', 'ayuda'])
  assert.deepEqual(despedir(['charla'], 'ayuda'), ['charla'], 'cerrar lo cerrado')
})

test('apilar y despide son coherentes: abrir y cerrar una deja la pila como estaba', () => {
  const inicial = ['charla', 'voz']
  const abierta = conmutar(inicial, 'ayuda')
  assert.deepEqual(despedir(abierta, 'ayuda'), inicial)
  assert.deepEqual(despedirFrente(abierta), inicial)
})
