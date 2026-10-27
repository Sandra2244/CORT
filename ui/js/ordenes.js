/* J2.1 · la regla de la superficie A: ¿charla o ejecución?
 *
 * Nace de `docs/PLAN-FASE-2-JARVIS.md` §2: hasta aquí la cara decidía a ojo —
 * TODO se iba a `/api/chat` y las órdenes quedaban sin manos. Este módulo convierte
 * esa decisión en una regla con prueba: si la frase casa con el vocabulario de
 * ejecución del núcleo (`backend/app/actions.py`), viaja a `POST /api/command`,
 * que devuelve `{reply, source, done:[acciones]}`; si no, es conversación y va a
 * `/api/chat`.
 *
 * Espejo deliberado de las regex de `actions.py`, con sus mismas tolerancias de
 * acentos. NO es una segunda autoridad: si esto dice «orden» y el núcleo no la
 * reconoce, `run_command` cae en su propio cerebro y la burbuja lo cuenta igual —
 * la cara nunca inventa un «hecho» que el `done` no trajo.
 *
 * Dos límites escritos para que nadie los redescubra a golpes:
 *  · `cuéntame` / `recita` / `narra` se DEJAN fuera a propósito: en `actions.py`
 *    viven dentro de `RE_LEER` («lee las notas»), y la cara no puede saber si
 *    «cuéntame un chiste» habla de notas o de charla. Esas frases son conversación.
 *  · `pon / coloca / suena` casan sólo con resto de frase: «pon» solo no manda nada.
 */

const ORDENES = [
  ['nota', /^(?:apunta|anota|recuerda|nota[:\s])\s+\S/i],
  ['pendiente', /^(?:tengo que|hay que|me falta|apunta(?:\s+una)?\s+pendiente|pendiente[:\s])/i],
  ['abrir', /^(?:abre|abrir|lanza|lanzar|open)\s+\S/i],
  ['mostrar', /^(?:muestra|mu[ée]strame)\s+(?:la\s+)?(?:carpeta|archiv|el\s+archivo|la\s+ventana|mis?\s+\S+)/i],
  ['musica', /^(?:reproduce|reproducir|pon(?:e|me|lo|la)?|toca|escucha|coloca|suena)\s+\S[^\n]+/i],
  ['busca', /^busc(?:a|ar)\s+\S/i],
  ['leer', /^(?:lee|leer|l[ée]eme|l[ée]elo)\s+(?:en\s+voz\s+alta\s+)?\S/i],
  ['reproductor', /^(?:me\s+)?(?:adelanta|adelante|avanza|retrocede|atr[áa]s|atrasa|skip|siguiente|anterior|otra\s+(?:canci[oó]n|pista|tema)|pausa(?:r|lo)?|alto|haz\s+alto|quieto|silencio|m[úu]talo|det[eé]n|para(?:\s+(?:la\s+)?(?:m[uú]sica|el\s+audio))?|reanuda(?:r)?|contin[uú]a|que\s+siga|dale\s+(?:play|reproducci[oó]n))[\s.!]*(?:\d+\s*(?:s(?:eg|gs?|egundos)?)?)?[\s.!]*$/i],
  ['que-suena', /^[\s¿?]*(?:qu[ée]\s+(?:est[áa]\s+)?(?:sonando|suena|reproduciendo|poniendo)|qu[ée]\s+(?:canci[oó]n|pista|tema)\s+(?:es|est[áa]|suena)|en\s+qu[ée]\s+(?:minuto|parte|posici[oó]n|segundo)|d[óo]nde\s+voy|estado\s+del\s+reproductor|c[óo]mo\s+va\s+(?:la\s+)?(?:m[uú]sica|pista))[\s.!¿?]*$/i],
  ['modelo', /^(?:usa|usar|activa|c[áa]mbiate\s+a(?:l)?|c[áa]mbiate|pon(?:e|me)?\s+el)\s+(?:el\s+)?(?:modelo\s+)?[a-z0-9][a-z0-9._\/:-]*(?::[a-z0-9._-]+)?\s*(?:modelo)?\s*[.!]*$/i],
  ['modelos-lista', /^[¿\s]*(?:lista|cu[áa]les|mu[ée]strame|ens[ée][ñn]ame)[^\n]*\bmodelos?\b/i],
  ['ollama', /^(?:enciende|prende|levanta|arranca|apaga|para|det[ée]n|cierra)\s+(?:el\s+)?ollama/i],
  ['limpiar', /^(?:limpia(?:r)?|borra(?:r)?|vac[íi]a|libera|optimiza)\s+\S/i],
  ['sistema', /(?:cu[áa]nta\s+(?:ram|memoria)|qu[ée]\s+pesado|estado\s+del\s+equipo)/i],
];

/* Frase dicha (ya limpia de punto de cierre) → {ruta, accion} o {ruta:'charla'}.
   `accion` es el nombre que la cara enseña en el chip mientras espera; el resultado
   DEFINITIVO lo pone siempre el `done` del núcleo, nunca este nombre. */
export function clasificarOrden(texto) {
  const t = String(texto || '').trim();
  if (!t) return { ruta: 'charla', accion: '' };
  for (const [nombre, re] of ORDENES) {
    if (re.test(t)) return { ruta: 'orden', accion: nombre };
  }
  return { ruta: 'charla', accion: '' };
}

/* El vocabulario completo, para la prueba de contrato y para ` Arnés`: ninguna
   orden puede existir dos veces y toda regex debe estar anclada. */
export const VOCABULARIO_ORDENES = ORDENES.map(([nombre, re]) => ({ nombre, fuente: re.source }));
