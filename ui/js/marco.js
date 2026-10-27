/* ===== El marco de las pantallas: el estado, el puente, las hojas y el cambio de hoja =====
 *
 * Segundo corte de la refactorización por tamaño (la regla de la dueña: «la interfaz
 * debe ser mil líneas máximo y si necesitas crear otros de otras líneas más conectas
 * y divides entre si pero que funcione correctamente»). `pantallas.js` había vuelto a
 * 3.187 líneas porque TODO el mundo hablaba con las mismas cinco cosas: el `ctx` de
 * `hud.js`, el puente de Java, la tabla de hojas, las bottom sheets y la pregunta
 * «¿hay núcleo?». Aquí se va esa parte compartida, y cada pantalla que salga de
 * `pantallas.js` importa de aquí en vez de recibir el marco a mano.
 *
 * Por qué esto no forma un círculo con `pantallas.js`:
 *  · `ir()` ya no llama a las funciones de cada hoja por su nombre. Cada hoja se
 *    **registra** (`alEntrar`, `antesDeCambiar`, `despuesDeCambiar`), y `ir` recorre
 *    el registro. Así `marco.js` no necesita saber qué archivos existen: la carcasa
 *    y las pantallas lo importan a él, nunca al revés. Los imports circulares en
 *    módulos ES «dan sorpresas feas» —palabras del cabecero de este mismo archivo
 *    antes de la división— y aquí se evitan con un `Map`, no con piruetas.
 *  · `ctx`, `actual` y `nucleo` salen con `export let`: los módulos que los importan
 *    ven el valor **vivo** (así lo define el estándar ES), por eso el millar largo de
 *    `ctx?.term?.(…)` repartido por la cara no se reescribió: sigue leyéndose igual.
 *    Sólo `marco.js` los asigna, y para eso están `ponCtx` y `hayNucleo`.
 *
 * El orden de `ir()` es el de siempre, dicho con los ganchos: cerrar lo que haya que
 * cerrar (`alCerrar` → el cajón), soltar la hoja viva, repintar el cajón
 * (`alRepintar`), arrancar la hoja que toca (`alEntrar`), y lo último del estado que
 * depende del aparato (`alPintar` → el avispón y la píldora de Música). Antes esas
 * cuatro cosas estaban escritas a mano dentro de `ir()` y ataban la carcasa y las
 * cinco apps al mismo archivo; `scripts/prueba-marco.mjs` comprueba el orden real.
 */

import { esc } from './texto.js';

/* ───────────────────────────── el puente de Java ───────────────────────────── */

const N = () => window.CortNative || null;
const enTelefono = () => !!N();

const puede = nombre => {
  // Mismo `typeof` que `llama()`, pero sólo para PREGUNTAR: sirve para avisar con
  // palabras de que un APK viejo no trae el método, en vez de llamarlo a ciegas.
  const p = N();
  return !!p && typeof p[nombre] === 'function';
};

const llama = (nombre, ...args) => {
  const p = N();
  // `typeof` antes de llamar: un APK viejo (o el cuerpo de siempre) no conoce los
  // métodos nuevos, y un `TypeError` en la consola no es un mensaje para la dueña.
  if (!p || typeof p[nombre] !== 'function') return null;
  try { return p[nombre](...args); } catch (e) { ctx?.term?.('el puente dijo: ' + e, 'puente'); return null; }
};

/* ───────────────────────────── el estado vivo ───────────────────────────── */

let ctx = null;                     // { api, term, say, orb, voice }
let actual = 'orbe';
let nucleo = null;                  // null = sin comprobar, false = no hay, base = sí hay

/** Lo llama `initPantallas` una sola vez, y a partir de ahí todo el mundo lee `ctx`. */
const ponCtx = contexto => { ctx = contexto; };

/* ───────────────────────────── las hojas que existen ───────────────────────────── */

const PANTALLAS = [
  { id: 'orbe',   titulo: 'Orbe',    sub: 'el holograma de siempre', ic: '◉' },
  { id: 'musica', titulo: 'Música',   sub: 'el reproductor de CORT', telefono: true, ic: '♪' },
  /* La letra y el vídeo siguen siendo SU propia pantalla completa (con su `<video>`
     y su karaoke), pero **ya no se ofrecen solas en el cajón**: la dueña lo pidió el
     22/10 «debería fusionarse directamente con el reproductor de música… se llamará
     reproductor de música o otro nombre pero será una réplica exacta a Lark Player».
     En Lark eso es el botón `❝ Letras` del reproductor, y aquí es `abreLetra()`, que
     entra y sale con ‹ sin que la hoja aparezca como otra app. */
  { id: 'mv',     titulo: 'Letra',    sub: 'el vídeo con su letra', telefono: true,
    ic: '❝', escondida: true },
  { id: 'charla', titulo: 'Charla',   sub: 'conversa con tus modelos', ic: '✦' },
  { id: 'codigo', titulo: 'Código',   sub: 'terminal y programar', ic: '⌗' },
  // La hoja del contrato 2.1: manda sobre el aparato. Sin puente no existe — en el
  // PC no hay volumen que subir ni linterna que encender, y un botón que no hace
  // nada es peor que un botón que no se ofrece.
  // `puente: 'accion'` es la segunda condición: un APK viejo sí tiene `CortNative`
  // pero no trae los métodos del contrato 2.1, y ahí la hoja entera sobra.
  { id: 'equipo', titulo: 'Equipo',   sub: 'lo que manda CORT en el teléfono',
    telefono: true, puente: 'accion', ic: '⚙' },
  // F19 · el índice de todo: las 91 intenciones del diccionario real, las
  // pantallas, las herramientas y los ajustes, con búsqueda. No promete nada
  // nuevo: ordena lo que ya hay y manda la frase de verdad al tocarla.
  { id: 'centro', titulo: 'Centro',   sub: 'todas las órdenes en un solo sitio', ic: '⌘' },
  // F23 · el arnés: qué sostiene a CORT por dentro (puente, núcleo, memoria,
  // sesiones, herramientas) y si cada pieza está sana. Es un tablero de lo que
  // ESTE aparato ya hace; no promete agentes autónomos ni sesiones paralelas.
  { id: 'arnes',  titulo: 'Arnés',    sub: 'lo que sostiene a CORT', ic: '⌬' },
];
// `montables()` es lo que se construye en el DOM (todas, escondidas o no); `visibles()`
// es la única lista que se OFRECE (cajón, teclas, deslizar). Una hoja con `puente` solo
// existe si el puente de Java trae ese método de verdad.
const montables = () => PANTALLAS.filter(p => (!p.telefono || enTelefono())
  && (!p.puente || puede(p.puente)));
const visibles = () => montables().filter(p => !p.escondida);

/* Cada hoja es SU app: el color con el que se pinta su icono del cajón, su fondo y su
   acento. Los valores coinciden con las variables `--app-*` de `css/apps.css`, que es
   donde se visten de verdad; aquí sólo hace falta el tinte del icono. */
const TINTE = { orbe: '#39c2ff', musica: '#ff9a8b', mv: '#ffb27a',
                charla: '#8ab4f8', codigo: '#2bff9e', equipo: '#7ce7c8',
                centro: '#c9a6ff', arnes: '#9ad7ff' };

/* ─────────────────── las hojas que suben desde abajo (bottom sheets) ───────────
   Calco de Lark y de Gemini: panel redondo por arriba, asidero, título y filas con
   icono. Una sola instancia viva: abrir otra cierra la anterior, porque dos hojas
   apiladas en una pantalla de 5 pulgadas es un accidente. */
let hojaViva = null;

function cierraHoja() {
  if (!hojaViva) return;
  const { raiz, cortina } = hojaViva;
  raiz.classList.remove('abierta');
  cortina.classList.remove('abierta');
  const cierra = () => { raiz.remove(); cortina.remove(); };
  document.documentElement.classList.contains('sin-movimiento') ? cierra() : setTimeout(cierra, 260);
  hojaViva = null;
}

/* `html` es el contenido ya pintado; `alAbrir` recibe la hoja por si hay que
   enganchar botones después (se hace aquí para que nadie tenga que acordarse). */
function abreHoja({ titulo, html, botones = '', alAbrir = null }) {
  cierraHoja();
  const cortina = document.createElement('div');
  cortina.className = 'hoja-cortina abierta';
  const raiz = document.createElement('div');
  raiz.className = 'hoja';
  raiz.innerHTML = `<div class="hoja-asidero"></div>
    <div class="hoja-cab"><b>${esc(titulo)}</b>${botones}
      <button class="hoja-cierra" title="Cerrar">✕</button></div>
    <div class="hoja-cuerpo">${html}</div>`;
  document.body.appendChild(cortina);
  document.body.appendChild(raiz);
  const cierra = () => { cierraHoja(); };
  cortina.onclick = cierra;
  raiz.querySelector('.hoja-asidero').onclick = cierra;
  raiz.querySelector('.hoja-cierra').onclick = cierra;
  requestAnimationFrame(() => raiz.classList.add('abierta'));
  hojaViva = { raiz, cortina };
  alAbrir?.(raiz);
  return raiz;
}

/* Si hay una hoja abierta lo necesita la carcasa (la tecla Escape), no el DOM: por
   eso se pregunta aquí en vez de exporting la variable. */
const hayHoja = () => !!hojaViva;

/* ───────────────────────── ¿hay núcleo de PC? ─────────────────────────
   Se pregunta una vez y se recuerda: `nucleo` es `null` antes de la primera
   llamada, `false` si el portátil no responde, y la base (`http://…:8123`) si sí. */
async function hayNucleo() {
  if (nucleo) return nucleo;
  const base = ctx?.api ? ctx.api() : '';
  try {
    const r = await fetch(base + '/api/port', { signal: AbortSignal.timeout(1800) });
    if (!r.ok) throw new Error(String(r.status));
    nucleo = base;
  } catch { nucleo = false; }
  return nucleo;
}

const sinNucleoFrase = () => enTelefono()
  ? 'Sin tu portátil no hay cerebro que consulte: conéctalo y abre CORT con «CORT · PC», o escribe la dirección en el menú del botón. Aquí lo que sí funciona sin PC es la pantalla de Música.'
  : 'El núcleo de CORT no responde: arráncalo con scripts/run (o run.bat) y vuelve a abrir esta pantalla.';

/* La misma frase, para `hud.js`: cuando el portátil no está, la cara tiene que sonar
   igual en las pantallas que en el canal de voz — dos maneras de decir lo mismo
   confunden más que una sola. */
const fraseSinNucleo = () => sinNucleoFrase();

async function avisaSinNucleo(donde) {
  const ok = await hayNucleo();
  if (ok === false && donde) { donde.textContent = 'sin núcleo'; donde.classList.add('aviso'); }
  else if (donde) { donde.textContent = 'núcleo listo'; donde.classList.remove('aviso'); }
  return ok;
}

/* ───────────────────────── el portapapeles ───────────────────────── */

function copia(texto, aviso) {
  const listo = () => ctx?.say?.(aviso || 'Copiado.');
  if (navigator.clipboard && window.isSecureContext !== false) {
    navigator.clipboard.writeText(texto).then(listo).catch(() => reserva(texto, listo));
  } else reserva(texto, listo);
}
function reserva(texto, listo) {
  // En el WebView del APK (`https://cort.local`) el portapapeles async no siempre
  // está permitido: se recurda con un campo invisible y `execCommand`.
  const area = document.createElement('textarea');
  area.value = texto; area.style.position = 'fixed'; area.style.opacity = '0';
  document.body.appendChild(area); area.select();
  try { document.execCommand('copy'); listo(); } catch { ctx?.say?.('No pude copiarlo: selecciónalo con el dedo.'); }
  area.remove();
}

/* ─────────────────── el registro de hojas y el cambio de pantalla ───────────────────
 * `ir()` es lo que ejecuta un toque en el cajón, una tecla, un deslizamiento, un
 * atajo del icono y una frase de voz. Antes llamaba a cada hoja **por su nombre**,
 * así que la hoja nueva que se separa tenía que estar aquí dentro: la carcasa y las
 * cinco apps vivían enlazadas por esas cinco líneas. Con registro, cada hoja dice
 * qué hay que hacer al entrar y `ir` no sabe ni necesita saber quién es.
 */

const ENTRADAS = new Map();   // id -> función que hay que arrancar al entrar
const CIERRES = [];           // antes de soltar la hoja viva (la carcasa cierra el cajón)
const REPINTOS = [];          // después de cerrarla y antes de entrar: el cajón marca la hoja activa
const PINTURAS = [];          // lo último, con la pantalla ya montada (Música: avispón y píldora)

/** Qué hay que arrancar cuando la dueña entra en `id`. */
const alEntrar = (id, fn) => { ENTRADAS.set(id, fn); };
/** Algo que hay que **cerrar** en cuanto cambia de hoja (se puede registrar más de uno). */
const alCerrar = fn => { CIERRES.push(fn); };
/** Algo que hay que repintar con la hoja ya elegida, antes de arrancarla. */
const alRepintar = fn => { REPINTOS.push(fn); };
/** Lo último del cambio: se ejecuta con la pantalla nueva montada. */
const alPintar = fn => { PINTURAS.push(fn); };

function ir(id) {
  // `montables()`, no `visibles()`: la hoja de letra está escondida del cajón, pero
  // existe y hay que poder entrar en ella. Con `visibles()` se habría caído al Orbe.
  const p = montables().find(x => x.id === id) || PANTALLAS[0];
  actual = p.id;
  const raiz = document.documentElement;
  montables().forEach(x => raiz.classList.remove('p-' + x.id));
  raiz.classList.add('p-' + actual);
  CIERRES.forEach(fn => fn());
  cierraHoja();
  /* El botón nativo «CORT · PC» ya no existe: estorbaba y parecía que CORT
     arrancaba en modo PC. Su menú de dieciséis filas se abre desde Equipo ▸
     9 · PC (`abreMenu()`), y la conexión con el PC o el VPS también vive allí.
     No queda nada que mostrar u ocultar hoja por hoja. */
  // El cajón es la única tira de botones que queda, así que la hoja activa se marca
  // ahí. Se repinta siempre: `visibles()` puede haber cambiado (un aviso de Java trae
  // un método que antes no estaba) y un cajón desactualizado ofrecería una hoja muerta.
  // (Eso es el gancho que registró la carcasa con `alRepintar`.)
  REPINTOS.forEach(fn => fn());
  ENTRADAS.get(actual)?.();
  PINTURAS.forEach(fn => fn());
  ctx?.term?.('pantalla: ' + p.titulo, 'pantallas');
  window.dispatchEvent(new CustomEvent('cort-pantalla', { detail: actual }));
}

const pantallaActual = () => actual;

/* El botón ☰ de cualquier hoja abre el cajón, y abrirlo son dos cosas: repintarlo —por
   si el puente trajo un método que antes no estaba y hay que ofrecer más hojas— y poner
   la clase. La cara registra su `montaCajon` con `alRepintar`, así que la Charla o el
   Código pueden abrirlo desde aquí sin importar `pantallas.js`: el import sigue yendo
   en una sola dirección. */
const abreCajon = () => {
  REPINTOS.forEach(fn => fn());
  document.documentElement.classList.add('cajon-abierto');
};

/* Deslizar a un lado: se mide en la propia carcasa, nunca en un botón, y se ignora
   si el dedo empezó encima de una lista (ahí lo que quiere la dueña es desplazar la
   lista, no cambiarse de pantalla). */
function mueve(paso) {
  const l = visibles().map(p => p.id);
  const i = Math.max(0, l.indexOf(actual));
  ir(l[(i + paso + l.length) % l.length]);
}

export {
  N, enTelefono, puede, llama,
  ctx, ponCtx, actual, nucleo,
  PANTALLAS, montables, visibles, TINTE,
  abreHoja, cierraHoja, hayHoja,
  hayNucleo, sinNucleoFrase, fraseSinNucleo, avisaSinNucleo,
  copia, reserva,
  alEntrar, alCerrar, alRepintar, alPintar, ir, pantallaActual, mueve, abreCajon,
};
