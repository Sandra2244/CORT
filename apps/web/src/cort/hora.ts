/**
 * El reloj de la cara y de la bandeja (N13 — bandeja viva; CARETA v2 se lo
 * llevó también a la barra de comandos).
 *
 * Vive en la lógica pura y no dentro de un componente por lo único que se
 * puede probar con verdad: el formato. Desde la fase A la barra de arriba usa
 * `hh:mm:ss` entero —el reloj grande es el cronómetro de la cara, no ruido— y
 * la bandeja abierta lo sigue pidiendo: quien está escribiendo quiere ver el
 * minuto a minuto de su conversación, como en las referencias.
 *
 * Se formatea a mano y no con `toLocaleTimeString`: el formato de la referencia
 * es fijo (`hh:mm:ss` en 24 h, `dd/mm/aaaa`), y una función que depende del
 * `locale` del navegador no se puede probar con verdad — en otra máquina
 * devolvería `AM/PM` y el test mentaría según dónde corre.
 */
const dos = (n: number) => String(n).padStart(2, '0')

/** `04:07:09` — horas 24, siempre dos dígitos por campo. */
export function hhmmss(d: Date): string {
  return `${dos(d.getHours())}:${dos(d.getMinutes())}:${dos(d.getSeconds())}`
}

/** `11/10/2026` — día y mes con cero, año completo. */
export function fechaCorta(d: Date): string {
  return `${dos(d.getDate())}/${dos(d.getMonth() + 1)}/${d.getFullYear()}`
}

/**
 * La etiqueta de quién habla en una fila del registro. `cort` en minúsculas por
 * la misma regla que `FASE_TEXTO`: en esta interfaz las minúsculas son el tono
 * de la máquina, y «tú» le devuelve a la usuaria la primera persona.
 */
export function remitente(from: 'user' | 'cort'): string {
  return from === 'user' ? 'tú' : 'cort'
}
