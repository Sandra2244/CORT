// De una frase escrita en la charla a la ventana que le toca.
//
// Función 80, y cuarta capa pura de la cara con su prueba (regla 3 de
// `AGENTS.md`). Lo que está en juego aquí es **una ventana que se abre sola**:
// mientras el patrón de `ui/Charla.tsx` buscaba la palabra suelta, preguntar
// «¿en qué estado está el volumen?» levantaba la ventana de sistema. Nadie ve el
// error en la consola; lo ve cuando tiene tres ventanas encima del reactor.
import test from 'node:test'
import assert from 'node:assert/strict'

import { MANDOS, ventanaPorComando } from './comandos.mjs'
import { ACCESOS } from './teclas.mjs'

test('la lista de comandos está completa y cada uno apunta a una ventana que existe', () => {
  assert.deepEqual(
    MANDOS.map((m) => m.id),
    ['camara', 'voz', 'cuerpo', 'sistema'],
  )
  const ids = ACCESOS.map((a) => a.id)
  for (const m of MANDOS) {
    assert.ok(ids.includes(m.id), `${m.id} no está en el muelle: ventana fantasma`)
    assert.ok(m.ejemplo.length > 0, `${m.id} no tiene ejemplo que enseñar en la ayuda`)
    assert.equal(ventanaPorComando(m.ejemplo), m.id, `su propio ejemplo no lo enciende`)
  }
})

test('las cuatro frases piden su ventana', () => {
  const casos = [
    ['activa la cámara', 'camara'],
    ['abre camara', 'camara'], // sin tilde: así se teclea en un teclado de móvil
    ['enciende la cámara', 'camara'],
    ['prende mi cámara', 'camara'],
    ['activa el micrófono', 'voz'],
    ['abre voz', 'voz'],
    ['ACTIVA LA VOZ', 'voz'],
    ['cambia el atuendo', 'cuerpo'],
    ['proyecta atuendo', 'cuerpo'],
    ['elige mi atuendo', 'cuerpo'],
    ['estado', 'sistema'],
    ['diagnóstico', 'sistema'],
    ['sistema', 'sistema'],
  ]
  for (const [frase, id] of casos) {
    assert.equal(ventanaPorComando(frase), id, `«${frase}»`)
  }
})

test('mencionar la palabra no es pedirla: aquí estaba el fallo', () => {
  for (const frase of [
    '¿en qué estado está el volumen?',
    'haz una captura con la cámara',
    'qué voz usaste',
    'el atuendo de Cortana es el que más me gusta',
    'baja el volumen del sistema',
    'hola cort',
    'cuántos recuerdos tienes',
  ]) {
    assert.equal(ventanaPorComando(frase), null, `«${frase}» no debía abrir nada`)
  }
})

test('el sistema también se pide con verbo por delante', () => {
  for (const frase of [
    'muestra el sistema',
    'muéstrame el estado',
    'revisa diagnóstico',
    'abre el sistema',
    'cort, estado',
  ]) {
    assert.equal(ventanaPorComando(frase), 'sistema', `«${frase}»`)
  }
})

test('lo que no es texto no levanta una ventana', () => {
  for (const vacio of ['', '   ', '\n\t ', '     ']) {
    assert.equal(ventanaPorComando(vacio), null, JSON.stringify(vacio))
  }
})

test('si una frase casa con dos mandos, gana el primero de la lista y se sabe', () => {
  // No es cosmético: `find` devuelve el primer patrón, así que el orden **es** la
  // prioridad. La prueba fija que «activa la cámara y el micrófono» no dependa del
  // azar ni de cómo venga el te.
  assert.equal(ventanaPorComando('activa la cámara y el micrófono'), 'camara')
})
