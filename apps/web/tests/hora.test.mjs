import { test } from 'node:test'
import assert from 'node:assert/strict'
import { hhmmss, fechaCorta, remitente } from './hora.mjs'

/**
 * El reloj de la bandeja (N13) se formatea a mano, sin `locale`: lo que se
 * prueba aquí es el relleno a dos dígitos y el orden de campos — justo lo que
 * `toLocaleTimeString` cambiaría según la máquina y convertiría el test en
 * una mentira según dónde corre.
 */

// Los ceros por defecto no son pereza: `new Date(a, m, d, undefined, …)` con
// más de tres argumentos construye una fecha Inválida (NaN), y el test fallaría
// por el auxiliar, no por el formato.
const d = (a, m, dia, h = 0, mi = 0, s = 0) => new Date(a, m - 1, dia, h, mi, s)

test('hhmmss rellena con ceros cada campo', () => {
  assert.equal(hhmmss(d(2026, 10, 11, 4, 7, 9)), '04:07:09')
})

test('medianoche y fin de día: 00 y 23, nunca 24 ni 12 h', () => {
  assert.equal(hhmmss(d(2026, 10, 11, 0, 0, 0)), '00:00:00')
  assert.equal(hhmmss(d(2026, 10, 11, 23, 59, 59)), '23:59:59')
})

test('los segundos también cuentan (es lo que separa este reloj del de la cara)', () => {
  assert.equal(hhmmss(d(2026, 10, 11, 12, 0, 5)), '12:00:05')
})

test('fechaCorta: día y mes con cero, año completo', () => {
  assert.equal(fechaCorta(d(2026, 10, 11)), '11/10/2026')
  assert.equal(fechaCorta(d(2026, 1, 5)), '05/01/2026')
})

test('fechaCorta no depende del locale del navegador', () => {
  //meses 1..12 → 01..12, y el año sale entero aunque el milenio cambie
  assert.equal(fechaCorta(d(2000, 12, 31)), '31/12/2000')
})

test('remitente etiqueta las dos voces del registro', () => {
  assert.equal(remitente('user'), 'tú')
  assert.equal(remitente('cort'), 'cort')
})

test('remitente no inventa una tercera voz', () => {
  // Un `from` inesperado (core viejo, cuadro a mano) cae al lado de CORT: la
  // etiqueta nunca debe quedarse vacía ni decir una mentira sobre el origen.
  assert.equal(remitente('otro'), 'cort')
})
