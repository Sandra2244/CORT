#!/usr/bin/env node
/* Prueba del MANTO JARVIS (paso 1.4 de la Fase 1, `docs/PLAN-FASE-1.md`).
 *
 * El manto es una capa de CSS (`ui/css/jarvis.css`) que se pone con una clase en
 * `<html>` y viste la Charla de siempre como la del video de referencia: el orbe
 * detrás, la pastilla de acento para lo tuyo y texto suelto para lo de CORT.
 *
 * No se puede probar «cómo se ve» desde node —eso lo mira la dueña en el navegador—,
 * pero SÍ se prueba todo lo que hace que la capa sea una capa y no un destrozo:
 *
 *   [1] el archivo existe, está enlazado y va DESPUÉS de `apps.css` (si fuera antes,
 *       la ropa de cada app ganaría y el manto no se vería);
 *   [2] TODA regla cuelga de `manto-jarvis` — una regla suelta teñiría otra hoja y
 *       ahí es cuando una capa de «rediseño» se convierte en ocho bugs;
 *   [3] no hay ningún color de traje escrito a mano: los seis `--primario` de
 *       `Paleta.java` no aparecen literales aquí, porque el manto tiene que seguir
 *       al atuendo (lo del video es coral porque ése es SU traje);
 *   [4] la regla que devuelve el orbe a la charla GANA al apagón de `hud.css`: más
 *       especificidad e `!important`, medido sobre el texto de las dos hojas;
 *   [5] la respuesta medida sólo se cuela con el manto puesto y el modo Normal, y se
 *       guarda la preferencia en `localStorage`;
 *   [6] `hud.js` ya no congela el WebGL en la charla con el manto, y lo sigue
 *       congelando en las demás hojas (en un teléfono de 1,8 GiB un orbe que nadie ve
 *       es CPU, RAM y batería);
 *   [7] el botón «parar» no promete más de lo que hace y sólo existe mientras se
 *       espera; el estado de la cabecera sale de lo que el aparato confirma.
 *
 * Uso:  node scripts/prueba-manto.mjs     (una fracción de segundo)
 */
import { readFile } from 'node:fs/promises';

let fallos = 0, hechos = 0;
const ok = (etiqueta, condicionado, detalle = '') => {
  if (condicionado) { hechos++; console.log('  ok  ' + etiqueta); }
  else { fallos++; console.log('  NO  ' + etiqueta + (detalle ? ' → ' + detalle : '')); }
};
const lee = ruta => readFile(new URL(ruta, import.meta.url), 'utf8');

const css = await lee('../ui/css/jarvis.css');
const html = await lee('../ui/index.html');
const pant = await lee('../ui/js/pantallas.js');
const hudj = await lee('../ui/js/hud.js');
const hud = await lee('../ui/css/hud.css');
const apps = await lee('../ui/css/apps.css');
const paleta = await lee('../apps/apk/src/com/cort/ia/Paleta.java');

/* ─── [1] el enlace y su orden ─── */
console.log('\n[1] la capa está puesta y llega la última');
const orden = { hud: html.indexOf('css/hud.css'), apps: html.indexOf('css/apps.css'),
                jarvis: html.indexOf('css/jarvis.css') };
ok('`index.html` enlaza `css/jarvis.css`', orden.jarvis > 0);
ok('va DESPUÉS de `hud.css` y de `apps.css` (si no, la ropa de cada app gana)',
   orden.jarvis > orden.hud && orden.jarvis > orden.apps, JSON.stringify(orden));

/* ─── [2] todo cuelga de la clase ─── */
console.log('\n[2] ninguna regla se atreve sin la clase');
const cuerpo = css.replace(/\/\*[\s\S]*?\*\//g, '');      // los comentarios no cuentan
/* Se parsea `selector { cuerpo }` con el regex, no partiendo por `{`: partir por `{`
   se traga los `{` que hay dentro de las declaraciones (`rgba(…)`, `@media`) y sale
   una lista de «selectores» que son en realidad trozos de propiedades. */
const reglas = [...cuerpo.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
  .map(([, sel, decl]) => ({ sel: sel.trim().replace(/\s+/g, ' '), decl }));
const selectores = reglas.flatMap(r => r.sel.split(',').map(s => s.trim()));
const fuera = selectores.filter(s => !s.includes('manto-jarvis'));
ok(`las ${reglas.length} reglas llevan ` + '`manto-jarvis` en cada selector',
   reglas.length >= 20 && fuera.length === 0, fuera.join(' | '));
ok('y la clase la pone `pantallas.js`, no el HTML a pelo',
   /classList\.toggle\('manto-jarvis'/.test(pant) && !/class="[^"]*manto-jarvis/.test(html));

/* ─── [3] sin colores de traje escritos a mano ─── */
console.log('\n[3] el acento lo manda el atuendo');
const primarios = [...paleta.matchAll(/\{"(\w+)",\s*"(#[0-9a-f]{6})",\s*"(#[0-9a-f]{6})"\}/g)]
  .map(m => ({ nombre: m[1], p: m[2].toLowerCase(), s: m[3].toLowerCase() }));
ok('los seis trajes salen de `Paleta.java` (la fuente de verdad, no una copia)',
   primarios.length === 6, primarios.map(t => t.nombre).join(','));
const copiados = primarios.filter(t => css.toLowerCase().includes(t.p) || css.toLowerCase().includes(t.s));
ok('ningún `--primario`/`--secundario` de los seis está escrito literal en el manto',
   copiados.length === 0, copiados.map(t => t.nombre).join(','));
ok('el manto usa `var(--primario)` para TODO lo que se tiñe con el traje',
   (css.match(/var\(--primario\)/g) || []).length >= 5,
   `${(css.match(/var\(--primario\)/g) || []).length} usos`);
/* El coral del video NO se copia: se hereda del traje. Y si alguien pone un fijo, la
   prueba de arriba no lo caza (no es de los seis), así que se mira directo: un registro
   CERRADO de los colores del manto —tinta, velo y el ámbar del aviso—. Cualquier literal
   fuera de la lista es una mancha escrita a mano, venga de un video o de donde sea. */
const TINTA = new Set(['#02040a', '#05131d', '#9fb4c8', '#cfe0f2', '#eef4fb',
  '#f2f6fb', '#ffcf6b']);
const literales = [...new Set((css.match(/#[0-9a-f]{3,8}\b/gi) || []).map(h => h.toLowerCase()))];
ok('y no se copió el coral de la referencia: sólo tinta, velo y el ámbar de aviso',
   literales.every(h => TINTA.has(h)), literales.filter(h => !TINTA.has(h)).join(' '));

/* ─── [4] ganarle al apagón ─── */
console.log('\n[4] el orbe vuelve a estar detrás, y sólo en la charla');
/** `#id`·100 + clases/atributos/pseudo-clases·10 + tipos.
 *  `:not(...)` no suma por sí mismo: en CSS la pseudo-clase negativa cuenta por lo que
 *  hay DENTRO del paréntesis, así que `:not` se excluye de la cuenta de pseudo-clases y
 *  el `.p-orbe` de adentro ya lo aportan los puntos. Sin ese detalle el apagón de
 *  `hud.css` salía con un punto de más y el manto no le ganaba en la prueba. */
function especificidad(sel) {
  const s = sel.trim();
  const ids = (s.match(/#[\w-]+/g) || []).length;
  const cls = (s.match(/\.[\w-]+/g) || []).length + (s.match(/\[[^\]]+\]/g) || []).length
            + (s.match(/:(?!:)(?!not\b)[\w-]+/g) || []).length;
  const limpio = s.replace(/#[\w-]+|\.[\w-]+|\[[^\]]+\]|:(?!:)[\w-]+(\([^)]*\))?/g, ' ');
  const elem = (limpio.match(/[a-z][\w-]*/gi) || []).length;
  return ids * 100 + cls * 10 + elem;
}
ok('la cuenta de especificidad está probada con los dos casos de la casa',
   especificidad('html.pantallas-montadas:not(.p-orbe) #scene') === 121
   && especificidad('html.pantallas-montadas.p-charla.manto-jarvis #scene') === 131,
   `apagón ${especificidad('html.pantallas-montadas:not(.p-orbe) #scene')}, `
   + `manto ${especificidad('html.pantallas-montadas.p-charla.manto-jarvis #scene')}`);
/* El apagón de `hud.css`: `display:none!important` sobre `#scene` en cualquier hoja
   que no sea la del orbe. Para levantarlo hacen falta las dos cosas a la vez.
   Se cortan los comentarios antes de medir: si no, el texto de la explicación que
   cuelga sobre la regla (`.pantallas-montadas` hay dentro del comentario) suma un
   punto de especificidad que en el navegador no existe. */
const hudCuerpo = hud.replace(/\/\*[\s\S]*?\*\//g, '');
const apagón = [...hudCuerpo.matchAll(/([^{}]+)\{([^{}]*)\}/g)]
  .filter(([, , decl]) => /display:\s*none/.test(decl) && /!important/.test(decl))
  .flatMap(([, sel]) => sel.split(',').map(s => s.trim()))
  .filter(s => /(^|[\s>+~,])#scene(\b|[\s.:#[])/.test(s));
ok('el apagón existe en `hud.css` (si desaparece, esta prueba hay que cambiarla, no quitarla)',
   apagón.length > 0, `${apagón.length} reglas`);
const levanta = reglas
  .filter(r => /#scene\b/.test(r.sel) && /display:\s*block[^{}]*!important/.test(r.decl))
  .map(r => r.sel.split(',').map(s => s.trim()).filter(s => /#scene\b/.test(s)));
ok('el manto levanta `#scene` con `!important`', levanta.length > 0);
const peor = Math.max(...apagón.map(especificidad), 0);
/* Si no hay ninguna regla que levante el orbe, `Math.min(...[])` daría `Infinity` y la
   comparación de abajo saldría «ok» por vacío — justo cuando hay que gritar. Se pone a
   cero para que el detalle se lea honesto: `manto 0 vs apagón 121`. */
const mejor = levanta.length ? Math.min(...levanta.map(lista => Math.max(...lista.map(especificidad)))) : 0;
ok('y con MÁS especificidad que el apagón (si no, el `!important` empate y gana el orden)',
   mejor > peor, `manto ${mejor} vs apagón ${peor}`);
ok('sólo en la charla: la regla que levanta el orbe exige `p-charla`',
   levanta.every(lista => lista.every(s => s.includes('p-charla') && s.includes('manto-jarvis'))),
   levanta.flat().join(' | '));
/* Que levante el orbe no puede ser el principio de una moda: el `!important` es una
   munición que se gasta una sola vez. Si mañana alguien forza otro elemento, la capa
   deja de ser una capa y empieza a tapar cosas. */
const forzados = reglas.filter(r => /!important/.test(r.decl))
  .map(r => r.sel.split(',').map(s => s.trim()).filter(s => !/#scene|#agua/.test(s)).flat());
ok('y el `!important` del manto no se usa en nada que no sea el orbe y su agua',
   forzados.every(l => l.length === 0) && forzados.length > 0,
   forzados.flat().join(' | '));

/* ─── [5] la respuesta medida y la preferencia guardada ─── */
console.log('\n[5] semi-corta y medida, sólo con el manto y sin modo');
ok('la frase de medida existe y manda no inventar',
   /FRASE_JARVIS/.test(pant) && /inventarlo/.test(pant));
ok('sólo se cuela con el manto puesto Y el modo Normal (los modos mandan sobre ella)',
   /chManto && modo\.id === 'normal'/.test(pant));
ok('y viaja DENTRO del mensaje: `POST /api/chat` sólo acepta `{message}`',
   /const envio = \[jarvis, modo\.pide/.test(pant));
ok('la preferencia se guarda en `localStorage` con su clave',
   /CLAVE_MANTO = 'cort-manto'/.test(pant) && /localStorage\.setItem\(CLAVE_MANTO/.test(pant));
ok('y se lee al nacer, cayendo al manto puesto si no hay nada guardado',
   /localStorage\.getItem\(CLAVE_MANTO\) !== 'viejo'/.test(pant));

/* ─── [6] el WebGL detrás ─── */
console.log('\n[6] el orbe vivo cuesta: se deja sólo donde se ve');
ok('`hud.js` decide con `orbeDetras`, no con la cuenta a pelo de siempre',
   /orb\.pausa\(!orbeDetras\(/.test(hudj) && !/orb\.pausa\(e\.detail !== 'orbe'\)/.test(hudj));
const fn = hudj.slice(hudj.indexOf('const orbeDetras'), hudj.indexOf('const orbeDetras') + 400);
ok('la función sólo enciende en `orbe` y en `charla` con el manto',
   /pantalla === 'orbe'/.test(fn) && /pantalla === 'charla'/.test(fn)
   && /manto-jarvis/.test(fn) && !/musica|codigo|centro|arnes/.test(fn), fn.split('\n')[1] || '');
ok('y `pantallas.js` avisa cuando cambia, que es cuando hay que encenderlo o apagarlo',
   /dispatchEvent\(new CustomEvent\('cort-manto'/.test(pant)
   && /addEventListener\('cort-manto'/.test(hudj));

/* ─── [7] lo que la cara dice de sí misma ─── */
console.log('\n[7] el «parar» y el estado, sin prometer lo que no hay');
const para = pant.slice(pant.indexOf('function charlaPara'), pant.indexOf('function charlaPara') + 520);
ok('`charlaPara` corta la ESPERA y lo dice, sin fingir que apaga al modelo',
   /chPensando = false/.test(para) && /espera cortada/.test(para)
   && !/abort|AbortController/.test(para));
ok('el botón sólo existe mientras se espera',
   /alto\.hidden = !chPensando/.test(pant));
/* La píldora de «con qué se piensa» no puede quedarse diciendo «usando el modelo del
   núcleo» después de que ella cortara: nadie usó nada. Se prueba el candado y que el
   escrito a mano de `charlaPara` haya desaparecido, que era justo como se tapaba.
   La tajada es SOLO la función: cortarla hasta el final del archivo dejaba dentro los
   escritos a mano de `charla()`, y la prueba daba por bueno el desorden. */
const pastilla = pant.slice(pant.indexOf('function pintaUsandoCharla'),
                            pant.indexOf('function pintaAdjunto'));
ok('cortada la espera, la píldora dice «espera cortada» en vez de «usando …»',
   /else if \(chCortada && ultimo && ultimo\.de === 'tu'\)/.test(pastilla)
   && /espera cortada/.test(pastilla)
   && !/getElementById\('gm-usando'\)/.test(para));
/* La casa no admite dos fuentes de verdad para una línea: cada camino que escribía
   `usando` a mano perdía la carrera contra `pintaCharla`, que llamaba a la pintora
   justo después. Queda una sola, y lo que dice cada respuesta viaja con la respuesta
   (`nota`), no con un `innerHTML` suelto. */
const escribePildora = (pant.match(/getElementById\('gm-usando'\)/g) || []).length;
ok('y esa única pintora es la fuente de la píldora: ningún otro camino la escribe',
   escribePildora === 1 && pastilla.includes("getElementById('gm-usando')")
   && !/usando\.innerHTML/.test(pant),
   `${escribePildora} lectura del elemento`);
const notas = [...pant.matchAll(/de: 'cort'/g)]
  .map(m => /nota:/.test(pant.slice(m.index, m.index + 260)));
/* Seis desde J2.1 (`a3e980b`), y esta cuenta se quedó pidiendo cuatro. Las cuatro de
   antes eran: sin núcleo, la respuesta buena con su fuente, el «se cayó a media
   respuesta» y el recibo del cerebro del teléfono. J2.1 sumó dos caminos nuevos —la
   burbuja que lleva el `hecho` de `/api/command` y el «el núcleo se cayó a media
   orden»—. La cuenta exacta es parte de la prueba: si `matchAll` no encontrara
   ninguno, `every(Boolean)` daría por bueno un desorden vacío. */
ok('cada burbuja de CORT lleva escrita su `nota`, y la píldora la lee del final',
   notas.length === 6 && notas.every(Boolean)
   && /ultimo\?\.de === 'cort' && ultimo\.nota/.test(pastilla),
   `${notas.filter(Boolean).length}/${notas.length} con nota`);
/* Y la condición del final es la que la apaga: si dependiera sólo de la bandera, una
   respuesta que llega TARDE (después de parar, que es lo que la píldora promete) dejaría
   el «nadie contestó» pintado encima de una respuesta que sí está en la pantalla.
   Se cuentan por indentación: la declaración `let chCortada = false;` va pegada al
   margen y las reasignaciones van dentro de una función; contar la cadena a secas daba
   un apagado de más por culpa de la propia declaración, y la prueba mentía. */
ok('y se apaga sola cuando la respuesta llega, aunque llegue después de parar',
   /ultimo\.de === 'tu'/.test(pastilla)
   && (pant.match(/^ {2,}chCortada = true/gm) || []).length === 1
   && (pant.match(/^ {2,}chCortada = false/gm) || []).length === 2,
   `${(pant.match(/^ {2,}chCortada = true/gm) || []).length} encendidos, `
   + `${(pant.match(/^ {2,}chCortada = false/gm) || []).length} apagados`);
ok('el estado de la cabecera sale de `hayNucleo()`, no de un texto fijo',
   /hayNucleo\(\)\.then\(ok => jmEstado\(ok \? 'conectado' : 'sin núcleo'/.test(pant));
ok('y escribe las dos barras (la genérica y la del manto) con las mismas palabras',
   /function jmEstado/.test(pant) && /scr-charla \.scr-estado/.test(pant)
   && /getElementById\('jm-estado'\)/.test(pant));
/* La regla de la casa: una capa nueva no puede reescribir la ropa de siempre. */
ok('`apps.css` no sabe nada del manto (es una capa, no una remodelación)',
   !/manto-jarvis/.test(apps));

/* ─── [8] las dos aceptaciones del paso 1.4 que se pueden medir sin ojos ─── */
console.log('\n[8] la charla no se rehace entera, y su letra se puede seleccionar');
/* Aceptación del plan: «la hoja no re-renderiza todo el historial por mensaje». Se
   comprueba el mecanismo, no la fe: que exista la guarda de `chPintadas` y que TODOS
   los sitios que añaden un mensaje la avisen. Un `pintaCharla()` olvidado detrás de un
   `push` no rompe la cara —simplemente vuelve a lo de antes—, y por eso se cuenta. */
const pinta = pant.slice(pant.indexOf('let chPintadas'));
ok('existe la cuenta de lo ya colgado y la guarda de «sólo cambió el final»',
   /let chPintadas/.test(pant) && /chPintadas === mensajes\.length - 1/.test(pant)
   && /querySelectorAll\('\.burbuja:not\(\.gm-pensando\)'\)/.test(pinta));
/* Se recorre el archivo y, por cada mensaje que entra en la lista, se mira si su
   FUNCIÓN lo pinta antes de terminar. Buscar «la siguiente `pintaCharla(`» a secas fue
   el fallo: la distancia real entre un `push` y su pintura es de 80 a 800 caracteres
   (entre medias hay un `try`, un `fetch` y seis líneas de estado), así que un `push` al
   que se le borra su pintura encontraba la de la función de enfrente y la prueba daba
   por buena la callejón sin salida. Cortar por el inicio de la siguiente función es lo
   que se quiere decir de verdad: «nadie se queda sin aviso DENTRO de lo que lo añadió». */
const finDeFuncion = i => {
  const resto = pant.slice(i);
  const c = resto.match(/\n(?:async )?function /);
  return i + (c ? c.index : resto.length);
};
const empuja = [...pant.matchAll(/mensajes\.push\(/g)]
  .map(m => /pintaCharla\(true\)/.test(pant.slice(m.index, finDeFuncion(m.index))));
ok('cada `mensajes.push` va seguido de su `pintaCharla(true)` (' + empuja.length + ' sitios)',
   empuja.length >= 5 && empuja.every(Boolean), empuja.join(', '));
/* Y la de «pensando», que es una señal y no un mensaje: si se tratara como uno más,
   dos respuestas seguidas dejarían dos indicadores colgados. */
ok('la burbuja de «pensando» se pone y se quita sin rehacer la lista',
   /\.gm-pensando/.test(pinta) && /pensando\.remove\(\)/.test(pinta));
/* Aceptación: «el texto se puede seleccionar». En el teléfono el cuerpo entero está en
   `user-select:none` (hud.css) y sólo ciertas clases la recuperan; la caja de la
   charla tiene que estar entre ellas o la dueña no puede copiar lo que CORT dijo. */
ok('la caja de la charla lleva la clase que le devuelve la selección',
   /class="scr-lista gm-msgs" id="ch-msgs"/.test(pant)
   && /html\.mobile [^{]*\.scr-lista\{[^}]*user-select:\s*text/.test(hud),
   'o se perdió `scr-lista`, o se perdió la regla de `hud.css`');

console.log(`\n${fallos ? 'ROJO' : 'verde'} · ${hechos} hechos, ${fallos} fallos\n`);
process.exit(fallos ? 1 : 0);
