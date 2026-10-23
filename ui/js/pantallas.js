/* ===== Pantallas de CORT: el orbe, la música, el MV, la charla, el código y el equipo =====
 *
 * La dueña pidió **pantallas nuevas que no tengan nada que ver con el orbe y que
 * no lo obstruyan**: se cambia con el menú de tres líneas o deslizando el dedo a
 * un lado, y cada pantalla es su propio entorno. Esto es esa capa.
 *
 * Cómo encaja sin romper lo de siempre:
 *
 * · La pantalla `orbe` **es** la interfaz actual (el holograma, el dock, las
 *   once ventanas de vidrio). No se mueve ni se duplica: sólo se le pone clase
 *   al `<html>` (`p-orbe`, `p-charla`, `p-codigo`, `p-musica`, `p-mv`) y el CSS esconde
 *   lo que no va. Por eso el orbe no se tapa nunca: cuando no es su pantalla, el
 *   lienzo WebGL se apaga en vez de quedarse debajo dibujando a escondidas —
 *   en un teléfono de gama media eso también es memoria y batería. Hay UNA
 *   excepción, `p-mv`: ahí el holograma no se apaga, se encoge a una esquina y
 *   hace de disco que gira mientras suena la pista.
 *
 * · Cada pantalla nueva es un `<section class="scr">` de pantalla completa, con
 *   su propia barra arriba (menú ☰ + título + estado) y su contenido debajo.
 *
 * · En el **teléfono** (con `window.CortNative`) la pantalla de música manda de
 *   verdad: habla con `.Reproductor`, el servicio en primer plano del APK. En el
 *   PC esa pantalla no existe — ahí ya está la ventana 05 · Música con su
 *   `<audio>` — y el menú la omite en vez de ofrecer un botón vacío.
 *
 * · Donde no hay núcleo de PC (el teléfono sin Wi-Fi con el portátil) la charla y
 *   el código **lo dicen**, no inventan una respuesta: el `MainActivity` del APK
 *   corta los `/api/*` y contesta 501, así que se comprueba una vez y se avisa.
 *
 * · La hoja `equipo` (los cinco bloques del contrato 2.1: voz, mando, cerebro,
 *   memoria y trajes) vive en `js/telefono.js`. Aquí sólo se **monta** y se le
 *   pasa el mismo `ctx` de siempre más `ir`, para que una frase de voz pueda
 *   traer la pantalla delante sin que `telefono.js` tenga que saber quién es su
 *   vecina (nada de imports circulares ni de estado compartido por las paredes).
 */

import { montaTelefono, terminalTelefono } from './telefono.js';

const N = () => window.CortNative || null;
const enTelefono = () => !!N();
const esc = s => String(s ?? '').replace(/[&<>"']/g,
  c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

let ctx = null;                     // { api, term, say, orb, voice }
let actual = 'orbe';
let nucleo = null;                  // null = sin comprobar, false = no hay, base = sí hay
let telefono = { pinta: () => {} }; // lo que monta `telefono.js`; en el PC es un no-op

const PANTALLAS = [
  { id: 'orbe',   titulo: 'Orbe',    sub: 'el holograma de siempre', ic: '◉' },
  { id: 'musica', titulo: 'Música',   sub: 'el reproductor de CORT', telefono: true, ic: '♪' },
  { id: 'mv',     titulo: 'MV',       sub: 'el video con su letra', telefono: true, ic: '▣' },
  { id: 'charla', titulo: 'Charla',   sub: 'conversa con tus modelos', ic: '✦' },
  { id: 'codigo', titulo: 'Código',   sub: 'terminal y programar', ic: '⌗' },
  // La hoja del contrato 2.1: manda sobre el aparato. Sin puente no existe — en el
  // PC no hay volumen que subir ni linterna que encender, y un botón que no hace
  // nada es peor que un botón que no se ofrece.
  // `puente: 'accion'` es la segunda condición: un APK viejo sí tiene `CortNative`
  // pero no trae los métodos del contrato 2.1, y ahí la hoja entera sobra.
  { id: 'equipo', titulo: 'Equipo',   sub: 'lo que manda CORT en el teléfono',
    telefono: true, puente: 'accion', ic: '⚙' },
];
// `visibles()` es la única lista que se pinta (cajón, teclas, deslizar, `ir`). Una
// hoja con `puente` solo se ofrece si el puente de Java trae ese método de verdad.
const visibles = () => PANTALLAS.filter(p => (!p.telefono || enTelefono())
  && (!p.puente || puede(p.puente)));

/* Cada hoja es SU app: el color con el que se pinta su icono del cajón, su fondo y su
   acento. Los valores coinciden con las variables `--app-*` de `css/apps.css`, que es
   donde se visten de verdad; aquí sólo hace falta el tinte del icono. */
const TINTE = { orbe: '#39c2ff', musica: '#ff9a8b', mv: '#ffb27a',
                charla: '#8ab4f8', codigo: '#2bff9e', equipo: '#7ce7c8' };

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

/* ─────────────────────────── la carcasa ─────────────────────────── */

/* F9 · «el orbe será sólo pantalla principal, sin botones; sólo uno de las acciones
   o menú». Lo que antes era la tira de doce botones del borde inferior MÁS el menú ☰
   de hojas es ahora UNA sola cosa: el cajón (`#cajon`), que abre el único botón que
   queda en el orbe (`#orb-menu`) y se organiza en tres bloques —tus apps, las
   herramientas, los ajustes—.

   Dos decisiones que importan:
   · `#dock` NO se duplica ni se reescribe: viaja dentro del cajón con sus mismos
     nodos, porque `windows.js` engancha cada ventana buscando `#dock [data-win=…]`
     y esos manejadores son los que ya funcionan. Lo que sólo existe en el PC lleva
     `data-pc` y en el teléfono se esconde con CSS (su queja del «Optimizar»).
   · `#wake` y `#hand` se **reubican** dentro del cajón, igual que el dock: al mover
     el nodo se va con él el manejador que les puso `hud.js`.
*/
function montaCarcasa() {
  if (document.getElementById('scr-charla')) return;

  montaCajon();

  // Las hojas: cada `<section>` es la pantalla completa de SU app. Las que llevan
  // `sin-cab` dibujan su propia barra (Lark y Gemini), y la genérica estorba.
  const CON_BARRA_PROPIA = ['musica', 'charla'];
  visibles().filter(p => p.id !== 'orbe').forEach(p => {
    const s = document.createElement('section');
    s.className = 'scr' + (CON_BARRA_PROPIA.includes(p.id) ? ' sin-cab' : '');
    s.id = 'scr-' + p.id;
    s.innerHTML = `<header class="scr-top"><button class="scr-vuelve" title="Volver al orbe">‹</button>
      <button class="scr-menu" title="Menú de CORT" aria-label="Menú de CORT">☰</button>
      <b>${esc(p.titulo)}</b><span class="scr-estado"></span></header>
      <div class="scr-cuerpo"></div>`;
    document.body.appendChild(s);
    s.querySelector('.scr-vuelve').onclick = () => ir('orbe');
    s.querySelector('.scr-menu').onclick = abreCajon;
  });

  // El cartel del modo juego: aviso flotante, no botón (la barra de hojas ya no está).
  const juego = document.createElement('div');
  juego.id = 'pantalla-juego';
  juego.hidden = true;
  juego.title = 'CORT está en silencio mientras juegas';
  juego.textContent = '🎮 modo juego';
  document.body.appendChild(juego);
}

/* El contenido del cajón: las apps, con su color y su descripción. Se vuelve a
   pintar cada vez porque `visibles()` depende del puente (un APK viejo no ofrece
   Equipo, y sin teléfono no hay Música ni MV). */
function montaCajon() {
  const caja = document.getElementById('cj-apps');
  if (!caja) return;
  caja.innerHTML = visibles().map(p => `<button class="cj-app" data-p="${p.id}"
      style="--tinte:${TINTE[p.id] || '#39c2ff'}">
      <i>${p.ic || '◦'}</i><span class="cj-n"><b>${esc(p.titulo)}</b><span>${esc(p.sub)}</span></span>
    </button>`).join('');
  caja.querySelectorAll('[data-p]').forEach(b => {
    b.onclick = () => { cierraCajon(); ir(b.dataset.p); };
    b.classList.toggle('activa', b.dataset.p === actual);
  });
  montaAjustesCajon();
}

/* Ajustes y accesibilidad dentro del cajón: los dos conmutadores que ya existían
   como botones flotantes, más dos filas nuevas que cuestan dos líneas y valen para
   una pantalla de 5 pulgadas con letra pequeña. */
function montaAjustesCajon() {
  const caja = document.getElementById('cj-ajustes');
  if (!caja) return;
  [['wake', 'Escucha permanente «Oye CORT»'], ['hand', 'Gestos con la mano']].forEach(([id, nombre]) => {
    const b = document.getElementById(id);
    if (!b || b.parentElement === caja) return;
    b.dataset.nombre = nombre;
    caja.appendChild(b);
  });
  const fila = (id, icono, texto, clase) => {
    const b = document.createElement('button');
    b.className = 'cj-fila' + (document.documentElement.classList.contains(clase) ? ' on' : '');
    b.dataset.aj = id;
    b.innerHTML = `<i>${icono}</i>${esc(texto)}`;
    b.onclick = () => {
      const on = document.documentElement.classList.toggle(clase);
      b.classList.toggle('on', on);
      try { localStorage.setItem('cort-' + id, on ? '1' : '0'); } catch { /* modo privado */ }
      ctx?.say?.(texto + (on ? ' activado.' : ' desactivado.'));
    };
    return b;
  };
  caja.querySelectorAll('.cj-fila').forEach(b => b.remove());
  caja.appendChild(fila('letra', 'A', 'Letra más grande', 'letra-grande'));
  caja.appendChild(fila('movimiento', '≈', 'Sin animaciones', 'sin-movimiento'));
}

/* Los dos trajes de accesibilidad sobreviven al arranque: se leen del almacén local
   antes de pintar nada, para que la dueña no tenga que tocarlos cada vez. */
function aplicaAccesibilidad() {
  let g = '0', m = '0';
  try { g = localStorage.getItem('cort-letra') || '0'; m = localStorage.getItem('cort-movimiento') || '0'; }
  catch { /* sin almacén: queda como está */ }
  const raiz = document.documentElement;
  if (g === '1') raiz.classList.add('letra-grande');
  if (m === '1') raiz.classList.add('sin-movimiento');
}

const abreCajon = () => {
  montaCajon();                      // por si el puente cambió desde el último arranque
  document.documentElement.classList.add('cajon-abierto');
};
const cierraCajon = () => document.documentElement.classList.remove('cajon-abierto');
const cajonAbierto = () => document.documentElement.classList.contains('cajon-abierto');
const cierraMenu = cierraCajon;      // nombre de siempre, para no romper lo que lo llama

/* El único botón que queda en el orbe, su cortina y la ✕ del cajón. Se enganchan
   aquí y no dentro de `montaCajon()`, porque `montaCajon()` se repinta con cada
   cambio de hoja y estos tres nodos son fijos del índice. */
function montaNavegacion() {
  const boton = document.getElementById('orb-menu');
  const cortina = document.getElementById('cortina');
  const cierre = document.getElementById('cj-cierra');
  if (boton) boton.onclick = () => cajonAbierto() ? cierraCajon() : abreCajon();
  if (cortina) cortina.onclick = cierraCajon;
  if (cierre) cierre.onclick = cierraCajon;
}

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

/* Deslizar a un lado: se mide en la propia carcasa, nunca en un botón, y se ignora
   si el dedo empezó encima de una lista (ahí lo que quiere la dueña es desplazar la
   lista, no cambiarse de pantalla).

   F8: la lista de exclusiones era corta y por eso «se traban los botones» del
   reproductor. El transporte de Música/MV es una fila de botones **horizontal**
   (⏮ ▶ ⏭ ⏹ y debajo siete chips), y el pulgar al apoyar describe justo esos ~90 px
   que aquí significaban «cámbiame de hoja»: la dueña pulsaba play, la cara se iba a
   otra pantalla y la canción no empezaba. Un gesto de página no puede nacer encima
   de un control: quedan fuera también la píldora de música y el micrófono flotante,
   que en móvil vive en la misma esquina que el final de la fila. */
function montaGesto() {
  let x0 = null, y0 = null, objetivo = null;
  const NO_ES_GESTO = '#cajon, #cortina, .hoja, .hoja-cortina, button, a, input, textarea,'
    + ' select, output, .scr-lista, .lk-lista, .lk-pestanas, .gm-msgs, .gm-modos, .lk-fila,'
    + ' #plist, #flist, .mu-transporte, .mu-fila2, .mu-volumen, .mu-barra,'
    + ' #mic, #dock, #repro-pildora';
  document.addEventListener('touchstart', e => {
    const t = e.target;
    if (t.closest && t.closest(NO_ES_GESTO)) return;
    x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; objetivo = t;
  }, { passive: true });
  document.addEventListener('touchend', e => {
    if (x0 === null) return;
    const dx = e.changedTouches[0].clientX - x0;
    const dy = e.changedTouches[0].clientY - y0;
    x0 = null;
    // 90 px hacia un lado, casi sin bajar el dedo: es un cambio de pantalla, no un
    // Scroll. Con el teclado abierto tampoco se cambia (escribe, no desliza).
    if (Math.abs(dx) < 90 || Math.abs(dy) > Math.abs(dx) * .6) return;
    if (document.activeElement && /INPUT|TEXTAREA/.test(document.activeElement.tagName)) return;
    mueve(dx < 0 ? 1 : -1);
  }, { passive: true });
}

function mueve(paso) {
  const l = visibles().map(p => p.id);
  const i = Math.max(0, l.indexOf(actual));
  ir(l[(i + paso + l.length) % l.length]);
}

/* Teclado (PC e instalador): Alt+←/→ se mueve entre pantallas y Alt+1…5 salta a
   una concreta.

   Escape: en el orbe es de las ventanas de vidrio (`hud.js`), y dos dueñas para la
   misma tecla terminan peleándose. Así que sólo se toma cuando hay algo propio que
   cerrar —primero la hoja, después el cajón— y en ese caso se corta el evento con
   `stopImmediatePropagation` en la **fase de captura de `window`**: el oyente del
   HUD está puesto en `document` (fase de burbuja), va después, y al cortarlo no
   llega a esconder las ventanas justo cuando la dueña sólo quería cerrar un menú. */
function montaTeclas() {
  window.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    if (hojaViva) { e.preventDefault(); e.stopImmediatePropagation(); cierraHoja(); return; }
    if (cajonAbierto()) { e.preventDefault(); e.stopImmediatePropagation(); cierraCajon(); }
  }, { capture: true });
  document.addEventListener('keydown', e => {
    if (!e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.key === 'ArrowRight') { e.preventDefault(); mueve(1); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); mueve(-1); }
    else if (/^[1-9]$/.test(e.key)) {
      const p = visibles()[+e.key - 1];
      if (p) { e.preventDefault(); ir(p.id); }
    }
  });
}

export function ir(id) {
  const p = visibles().find(x => x.id === id) || PANTALLAS[0];
  actual = p.id;
  const raiz = document.documentElement;
  visibles().forEach(x => raiz.classList.remove('p-' + x.id));
  raiz.classList.add('p-' + actual);
  cierraMenu();
  cierraHoja();
  // El cajón es la única tira de botones que queda, así que la hoja activa se marca
  // ahí. Se repinta siempre: `visibles()` puede haber cambiado (un aviso de Java trae
  // un método que antes no estaba) y un cajón desactualizado ofrecería una hoja muerta.
  montaCajon();
  if (actual === 'musica') arrancaMusica();
  if (actual === 'mv') arrancaMV();
  if (actual === 'charla') { cargaModelos(); pintaCharla(); traeHistorial(); }
  if (actual === 'codigo') { pintaCodigo(); }
  // El Equipo se releé al entrar (voces, volumen, cerebro, recuerdos, trajes): es
  // la foto del aparato, y el aparato cambia mientras la hoja está cerrada.
  if (actual === 'equipo') telefono.pinta();
  pintaJuego((estadoMusica() || {}).juego);
  // Cambiar de hoja es justo lo que hace aparecer o desaparecer la píldora: en
  // Música y MV ya está el transporte completo, y en el Orbe o el Chat no debe
  // tapar nada. Se repinta aquí y no sólo con el aviso de Java porque al entrar
  // en una hoja puede no llegar ningún aviso.
  pintaPildora(estadoMusica());
  ctx?.term?.('pantalla: ' + p.titulo, 'pantallas');
  window.dispatchEvent(new CustomEvent('cort-pantalla', { detail: actual }));
}

export const pantallaActual = () => actual;

/* ¿Hay núcleo de PC? Se pregunta una vez y se recuerda. */
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
export const fraseSinNucleo = () => sinNucleoFrase();

async function avisaSinNucleo(donde) {
  const ok = await hayNucleo();
  if (ok === false && donde) { donde.textContent = 'sin núcleo'; donde.classList.add('aviso'); }
  else if (donde) { donde.textContent = 'núcleo listo'; donde.classList.remove('aviso'); }
  return ok;
}

/* ─────────────────────────── 01 · CHARLA ─────────────────────────── */
/*
 * Un chat como los de siempre: burbujas, entrada abajo, Historial arriba, y cada
 * respuesta se puede **copiar** o seleccionar con el dedo. Los modelos salen de
 * `/api/models` (los que ya están descargados en el PC); «usar uno» es
 * `/api/models/use`, que es lo que ya hace la ventana 10 · Modelos.
 */
const CLAVE_CHARLA = 'cort-charla';
let mensajes = [];

function cargaMensajes() {
  try { mensajes = JSON.parse(localStorage.getItem(CLAVE_CHARLA) || '[]'); }
  catch { mensajes = []; }
  if (!Array.isArray(mensajes)) mensajes = [];
}
function guardaMensajes() {
  try { localStorage.setItem(CLAVE_CHARLA, JSON.stringify(mensajes.slice(-40))); }
  catch { /* modo privado: se pierde al cerrar y no pasa nada */ }
}

/* ────────── la Charla, calco de Gemini (y de la estructura de Qoder) ──────────
 *
 * Copiado de sus ocho capturas de Google/Gemini: barra arriba con el nombre del
 * **modelo y su ▾**, saludo grande centrado sobre un degradado, chips de sugerencia,
 * y abajo la **píldora** con `+`, el campo, el micrófono y el botón redondo de enviar.
 * Las respuestas van sin caja (tuya a la derecha, la de CORT a la izquierda) y cada
 * una con su «copiar» y su fuente.
 *
 * Lo que se copió de Qoder es la **estructura**, no el dibujo: el menú es un sitio
 * distinto de la conversación (el cajón), el chat cambia de **modo** y **adjunta**
 * archivos, y el modelo se elige desde la propia barra.
 *
 * Dos honestidades que importan:
 *  · El **modo** añade una instrucción delante de tu pregunta. Se hace aquí porque
 *    `POST /api/chat` sólo acepta `{message}` — no hay parámetro de modo en el
 *    backend —, y el modelo sigue siendo el de tu portátil.
 *  · El **adjunto** es texto de verdad: se lee con `GET /api/lee` (el mismo candado
 *    de `sensors.leer_texto`: sólo dentro de tus carpetas permitidas) y se manda
 *    dentro del mensaje. Un PDF no se puede leer letra a letra, y eso se dice en
 *    pantalla en vez de resumir algo que nadie ha leído.
 */
const CH_MODOS = [
  { id: 'normal', ic: '✦', txt: 'Normal', pide: '' },
  { id: 'explica', ic: '💡', txt: 'Explícame',
    pide: 'Explícamo despacio, como a quien aprende, y con un ejemplo sencillo.' },
  { id: 'resume', ic: '≡', txt: 'Resume', pide: 'Responde en tres frases como mucho.' },
  { id: 'traduce', ic: '🌐', txt: 'Traduce',
    pide: 'Traduce lo que te pido al inglés y avísame de cualquier falso amigo.' },
  { id: 'codigo', ic: '⌗', txt: 'Código',
    pide: 'Dame código comentado en español y después dime qué hace cada parte.' },
  { id: 'plan', ic: '🗒', txt: 'Plan',
    pide: 'Hazme un plan por pasos, en orden, y di qué comprobar en cada paso.' },
];

/* Las sugerencias del saludo: cosas que CORT **ya sabe hacer** por su backend, no
   frases decorativas. Cada una se envía como si la hubiera escrito la dueña. */
const CH_SUGERENCIAS = [
  '¿Qué tiempo hace hoy?',
  '¿Qué modelos tengo bajados?',
  'Lee mis notas',
  'Muéstrame mis documentos',
  '¿Qué recuerdas de mí?',
];

let chModo = 'normal';
let chAdj = null;                 // {nombre, ruta, texto} lo que va pegado a la próxima pregunta
let chModelo = '';                // el nombre del modelo activo, para el rótulo de la barra

function montaCharla() {
  const cuerpo = document.querySelector('#scr-charla .scr-cuerpo');
  if (!cuerpo) return;
  cuerpo.innerHTML = `
    <div class="gm-cab">
      <button class="lk-btn" id="gm-menu" title="Menú de CORT">☰</button>
      <button class="gm-modelo" id="gm-modelo" title="Elegir modelo">
        <span id="gm-modelo-n">leyendo…</span><em>▾</em></button>
      <span class="lk-espacio"></span>
      <button class="lk-btn" id="gm-nueva" title="Empezar de cero">✚</button>
      <button class="lk-btn" id="gm-recuerda" title="Traer lo que CORT recuerda del núcleo">⟳</button>
    </div>
    <div class="gm-desplegable" id="gm-despl"></div>
    <div class="gm-saludo" id="gm-saludo">
      <b id="gm-saludo-t">Hola. ¿Qué hacemos?</b>
      <span id="gm-saludo-s">Tus modelos viven en el portátil: ahí corren. Aquí se eligen,
        se pregunta, se adjunta un documento y se guarda.</span>
      <div class="gm-sugerencias">${CH_SUGERENCIAS.map((s, i) =>
        `<button data-s="${i}">${esc(s)}</button>`).join('')}</div>
    </div>
    <div class="scr-lista gm-msgs" id="ch-msgs"></div>
    <div class="gm-usando" id="gm-usando"></div>
    <div class="gm-modos" id="gm-modos"></div>
    <div class="gm-pildora">
      <button class="gm-redondo" id="gm-adj" title="Adjuntar un documento o una nota">+</button>
      <textarea id="ch-entrada" rows="1" placeholder="Pregunta a CORT…"></textarea>
      <button class="gm-redondo" id="gm-mic" title="Dictar con el micrófono">🎙</button>
      <button class="gm-redondo enviar" id="ch-enviar" title="Enviar">▲</button>
    </div>
    <div class="gm-pie-gm">
      <button class="mu-chip" id="ch-copiar-ultimo" title="Copiar la última respuesta">copiar respuesta</button>
      <button class="mu-chip" id="ch-nota" title="Guardar la última respuesta como nota">guardar en Notas</button>
    </div>`;

  const entrada = cuerpo.querySelector('#ch-entrada');
  pintaModosCharla();
  pintaUsandoCharla();
  cuerpo.querySelector('#gm-menu').onclick = abreCajon;
  cuerpo.querySelector('#gm-modelo').onclick = () => {
    const d = cuerpo.querySelector('#gm-despl');
    if (d.classList.toggle('abierto')) cargaModelos();
  };
  document.addEventListener('click', e => {
    // Un toque fuera del desplegable lo cierra (es lo que hace Gemini, y deja de
    // tapar la conversación).
    const d = document.getElementById('gm-despl');
    if (d && d.classList.contains('abierto') && !e.target.closest('#gm-despl, #gm-modelo'))
      d.classList.remove('abierto');
  });
  cuerpo.querySelector('#ch-enviar').onclick = () => charla(entrada.value);
  entrada.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); charla(entrada.value); }
  });
  entrada.addEventListener('input', () => {
    entrada.style.height = 'auto';
    entrada.style.height = Math.min(140, entrada.scrollHeight) + 'px';
  });
  cuerpo.querySelector('#gm-adj').onclick = hojaAdjuntar;
  // El micro de la píldora es el de siempre (`#mic` de hud.js): se le dice a la
  // dueña, porque capturar el audio desde esta hoja sería otro camino distinto.
  cuerpo.querySelector('#gm-mic').onclick = () => {
    const m = document.getElementById('mic');
    if (m) m.click(); else ctx?.say?.('Toca el micrófono flotante para dictar.');
  };
  cuerpo.querySelector('#gm-nueva').onclick = () => {
    mensajes = []; chAdj = null; guardaMensajes(); pintaCharla(); pintaAdjunto();
    ctx?.say?.('Conversación nueva. Lo que CORT recuerda del núcleo sigue ahí: pulsa ⟳ para traerlo.');
  };
  cuerpo.querySelector('#gm-recuerda').onclick = () => {
    traeHistorial(true);
    ctx?.say?.('Traigo lo que recuerda el núcleo.');
  };
  cuerpo.querySelectorAll('#gm-saludo [data-s]').forEach(b => b.onclick = () => {
    entrada.value = CH_SUGERENCIAS[+b.dataset.s];
    charla(entrada.value);
  });
  cuerpo.querySelector('#ch-copiar-ultimo').onclick = () => {
    const ultimo = [...mensajes].reverse().find(m => m.de === 'cort');
    if (!ultimo) return ctx?.say?.('Aún no hay respuesta que copiar.');
    copia(ultimo.texto, 'Respuesta copiada.');
  };
  cuerpo.querySelector('#ch-nota').onclick = async () => {
    const ultimo = [...mensajes].reverse().find(m => m.de === 'cort');
    if (!ultimo) return ctx?.say?.('Aún no hay nada que guardar.');
    try {
      const r = await fetch(ctx.api() + '/api/notes', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ texto: '[charla] ' + ultimo.texto }),
      });
      ctx?.say?.(r.ok ? 'Anotado en 04 · Notas.' : 'El núcleo no dejó guardar la nota.');
    } catch { ctx?.say?.('El núcleo no respondió.') }
  };
  cargaMensajes();
}

/* Los chips de modo, con el activo teñido del acento de la app. */
function pintaModosCharla() {
  const caja = document.getElementById('gm-modos');
  if (!caja) return;
  caja.innerHTML = CH_MODOS.map(m => `<button class="gm-modo${m.id === chModo ? ' activa' : ''}"
    data-m="${m.id}" title="${esc(m.pide || 'sin instrucción añadida')}">
    <i>${m.ic}</i>${esc(m.txt)}</button>`).join('');
  caja.querySelectorAll('[data-m]').forEach(b => b.onclick = () => {
    chModo = b.dataset.m;
    pintaModosCharla();
    pintaUsandoCharla();
  });
}

/* La línea de abajo: modelo, modo y adjunto. Se dice aquí en vez de esconderse en
   un menú porque la dueña tiene que saber QUÉ se le está mandando al modelo. */
function pintaUsandoCharla() {
  const linea = document.getElementById('gm-usando');
  if (!linea) return;
  const modo = CH_MODOS.find(m => m.id === chModo) || CH_MODOS[0];
  const partes = ['usando ' + (chModelo || 'el modelo del núcleo'), 'modo ' + modo.txt];
  if (chAdj) partes.push('adjunto ' + chAdj.nombre);
  linea.innerHTML = partes.map((p, i) => i === 0 ? `<b>${esc(p)}</b>` : esc(p)).join(' · ');
}

function pintaAdjunto() {
  pintaUsandoCharla();
  const chip = document.getElementById('gm-adj-chip');
  if (chip) chip.remove();
  if (!chAdj) return;
  const pill = document.querySelector('.gm-pildora');
  if (!pill) return;
  const b = document.createElement('button');
  b.className = 'mu-chip gm-adj-chip';
  b.id = 'gm-adj-chip';
  b.textContent = '📎 ' + chAdj.nombre + ' ✕';
  b.title = 'Quitar el adjunto';
  b.onclick = () => { chAdj = null; pintaAdjunto(); };
  pill.before(b);
}

/* La hoja del `+`, calco de la de Gemini: botones redondos arriba. Aquí sólo hay
   opciones que CORT puede cumplir de verdad, y se dice por qué no están las otras. */
function hojaAdjuntar() {
  const enPC = !enTelefono();
  const opciones = [
    ['📄', 'Un documento', 'texto de tus carpetas', () => hojaArchivos('')],
    ['🗒', 'Una nota', 'lo que ya apuntaste', () => hojaNotas()],
    ['💬', 'Lo último de la charla', 'para preguntar sobre eso', () => {
      const ultimo = [...mensajes].reverse().find(m => m.de === 'cort');
      if (!ultimo) return ctx?.say?.('Aún no hay ninguna respuesta que adjuntar.');
      chAdj = { nombre: 'última respuesta', ruta: '', texto: ultimo.texto };
      pintaAdjunto(); cierraHoja();
    }],
  ];
  abreHoja({
    titulo: 'Adjuntar a la pregunta',
    html: `<div class="gm-adjuntar">${opciones.map(([ic, txt], i) =>
      `<button data-a="${i}"><i>${ic}</i>${esc(txt)}</button>`).join('')}</div>
      <div class="hoja-fila" style="cursor:default"><i>ℹ</i>
        ${enPC ? 'Sólo texto (.txt, .md, .log) hasta 400 KB: es lo que se puede leer letra a letra. '
               : 'Tus documentos y tus notas están en el portátil: sin CORT abierto ahí no hay nada que adjuntar. '
               + 'El audio del micrófono y las fotos del teléfono se mandan desde el propio Android, no por aquí.'}
        <small></small></div>`,
    alAbrir: raiz => raiz.querySelectorAll('[data-a]').forEach(b => b.onclick = () => {
      cierraHoja(); opciones[+b.dataset.a][3]();
    }),
  });
}

/* Explorador sencillo dentro de la hoja: carpetas y archivos de la raíz que se elija.
   Se apoya en `GET /api/files`, que ya candada por el backend (fuera de las carpetas
   permitidas devuelve error y aquí se muestra ese error, no se tapa). */
async function hojaArchivos(path) {
  const base = await hayNucleo();
  if (!base) return ctx?.say?.('Sin el núcleo del portátil no hay documentos que abrir.');
  let d = null;
  try {
    d = await (await fetch(base + '/api/files?path=' + encodeURIComponent(path),
      { signal: AbortSignal.timeout(6000) })).json();
  } catch { return ctx?.say?.('El portátil no contestó a lo de listar archivos.'); }
  if (!d || d.error) return ctx?.say?.(d?.error || 'No pude leer esa carpeta.');
  const filas = (d.entries || []).map((e, i) => {
    const texto = e.type === 'dir' ? '📁 ' + e.name : e.name;
    return `<div class="hoja-fila" data-i="${i}"><i>${e.type === 'dir' ? '▸' : '·'}</i>${esc(texto)}
      <small>${e.type === 'dir' ? 'carpeta' : Math.round((e.size || 0) / 1024) + ' KB'}</small></div>`;
  }).join('');
  abreHoja({
    titulo: path || 'Tus carpetas',
    botones: path ? '<button class="lk-btn" id="ah-sub">‹</button>' : '',
    html: filas || '<div class="mu-vacio">vacía</div>',
    alAbrir: raiz => {
      raiz.querySelector('#ah-sub')?.addEventListener('click', () => {
        const padre = path.split('/').slice(0, -1).join('/');
        cierraHoja(); hojaArchivos(padre);
      });
      raiz.querySelectorAll('[data-i]').forEach(f => f.onclick = () => {
        const e = (d.entries || [])[+f.dataset.i];
        if (!e) return;
        const ruta = (path ? path + '/' : '') + e.name;
        if (e.type === 'dir') { cierraHoja(); hojaArchivos(ruta); return; }
        cierraHoja(); adjuntaArchivo(ruta);
      });
    },
  });
}

async function adjuntaArchivo(ruta) {
  const base = await hayNucleo();
  if (!base) return ctx?.say?.('Sin el núcleo no puedo leer el archivo.');
  ctx?.say?.('Leyendo ' + ruta.split('/').pop() + '…');
  let r = null;
  try {
    r = await (await fetch(base + '/api/lee?path=' + encodeURIComponent(ruta),
      { signal: AbortSignal.timeout(8000) })).json();
  } catch { return ctx?.say?.('El portátil no contestó a lo de leer el archivo.'); }
  if (!r || r.ok === false) {
    return ctx?.say?.((r && r.error) || 'Ese archivo no lo puedo leer aquí.');
  }
  chAdj = { nombre: r.archivo, ruta, texto: r.texto };
  pintaAdjunto();
  ctx?.say?.('Adjuntado ' + r.archivo + (r.entero ? ', entero.' : ', lo que cabe de ' + r.caracteres + ' caracteres.'));
}

async function hojaNotas() {
  const base = await hayNucleo();
  if (!base) return ctx?.say?.('Sin el núcleo no hay notas que traer.');
  let ns = [];
  try {
    ns = await (await fetch(base + '/api/notes', { signal: AbortSignal.timeout(6000) })).json();
  } catch { return ctx?.say?.('El portátil no contestó a lo de las notas.'); }
  if (!Array.isArray(ns) || !ns.length) return ctx?.say?.('No tienes notas guardadas todavía.');
  abreHoja({
    titulo: 'Una nota guardada',
    html: ns.slice(-14).reverse().map((n, i) => `<div class="hoja-fila" data-i="${i}">
      <i>🗒</i>${esc(String(n.texto || '').slice(0, 60))}<small>${esc(String(n.fecha || ''))}</small></div>`).join(''),
    alAbrir: raiz => raiz.querySelectorAll('[data-i]').forEach(f => f.onclick = () => {
      const n = ns.slice(-14).reverse()[+f.dataset.i];
      chAdj = { nombre: 'nota ' + (n.fecha || ''), ruta: '', texto: String(n.texto || '') };
      pintaAdjunto(); cierraHoja();
      ctx?.say?.('Nota adjuntada.');
    }),
  });
}

async function charla(texto) {
  const pregunta = String(texto || '').trim();
  if (!pregunta) return;
  const entrada = document.getElementById('ch-entrada');
  if (entrada) { entrada.value = ''; entrada.style.height = 'auto'; }
  const modo = CH_MODOS.find(m => m.id === chModo) || CH_MODOS[0];
  // El adjunto va DENTRO del mensaje: `POST /api/chat` sólo acepta `{message}`, así
  // que no hay campo donde poner un archivo. Se manda el texto leído y se dice cuál.
  const envio = [modo.pide, chAdj
      ? '[Adjunto: ' + (chAdj.ruta || chAdj.nombre) + ']\n' + chAdj.texto : '', pregunta]
    .filter(Boolean).join('\n\n');
  mensajes.push({ de: 'tu', texto: pregunta, modo: modo.id, adj: chAdj ? chAdj.nombre : '' });
  const adjUntado = chAdj; chAdj = null;
  pintaAdjunto();
  pintaCharla();
  const estado = document.querySelector('#scr-charla .scr-estado');
  const usando = document.getElementById('gm-usando');
  if (usando) usando.innerHTML = '<b>pensando…</b> · modo ' + esc(modo.txt)
    + (adjUntado ? ' · 📎 ' + esc(adjUntado.nombre) : '');
  estado.textContent = 'pensando…';
  if (!await avisaSinNucleo(estado)) {
    mensajes.push({ de: 'cort', texto: sinNucleoFrase() });
    estado.textContent = 'sin núcleo';
    if (usando) usando.innerHTML = '<b>sin núcleo</b> · ' + esc(sinNucleoFrase());
    guardaMensajes(); pintaCharla(); return;
  }
  try {
    const r = await fetch(ctx.api() + '/api/chat', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ message: envio }),
    });
    const j = await r.json();
    const dicho = j.reply || j.error || 'No supe qué contestar.';
    mensajes.push({ de: 'cort', texto: dicho, fuente: j.source || '' });
    estado.textContent = 'cerebro: ' + (j.source || 'local');
    if (usando) usando.innerHTML = '<b>' + esc(chModelo || 'el modelo del núcleo') + '</b> · cerebro '
      + esc(j.source || 'local') + ' · modo ' + esc(modo.txt);
    ctx?.orb?.burst?.();
  } catch (e) {
    mensajes.push({ de: 'cort', texto: 'El núcleo se cayó a media respuesta: ' + e });
    estado.textContent = 'sin núcleo';
    if (usando) usando.innerHTML = '<b>sin núcleo</b>';
  }
  guardaMensajes(); pintaCharla();
}

/* El historial de verdad está en el núcleo (`GET /api/history`), y la cara nunca lo
   pedía: al reinstalar la app, cambiar de aparato o vaciar el almacén del navegador,
   la Charla se abría en blanco aunque CORT se acordara de lo hablado. Se trae sólo
   cuando la hoja está VACÍA: si la dueña ya tiene su conversación local, mezclar los
   dos listados saldría un desorden peor que dejar el suyo. Un fallo de red aquí no
   dice nada ni estorba —la charla funciona igual sin historial—, así que se traga
   en silencio; lo que no se traga es una respuesta que no sea 200.

   `forzar` (el botón ⟳ de la barra) sí sustituye lo local: lo manda el núcleo, que es
   donde CORT recuerda de verdad, y la dueña lo pidió con un toque. */
async function traeHistorial(forzar) {
  if (mensajes.length && !forzar) return;
  if (!ctx?.api) return;
  try {
    const r = await fetch(ctx.api() + '/api/history?n=40',
                          { signal: AbortSignal.timeout(2500) });
    if (!r.ok) return;
    const filas = await r.json();
    if (!Array.isArray(filas) || !filas.length) {
      if (forzar) ctx?.say?.('El núcleo no guarda ninguna conversación todavía.');
      return;
    }
    mensajes = filas.filter(x => x && (x.rol === 'user' || x.rol === 'assistant'))
      .map(x => ({ de: x.rol === 'user' ? 'tu' : 'cort',
                   texto: String(x.texto || ''), fuente: x.fuente || '' }));
    if (!mensajes.length) return;
    guardaMensajes(); pintaCharla();
  } catch { /* sin núcleo o sin respuesta: la hoja queda como estaba */ }
}

function pintaCharla() {
  const caja = document.getElementById('ch-msgs');
  if (!caja) return;
  // El saludo de Gemini con sus sugerencias sólo mientras no hay conversación: en
  // cuanto se pregunta, la pantalla es para las respuestas.
  const saludo = document.getElementById('gm-saludo');
  if (saludo) saludo.hidden = mensajes.length > 0;
  caja.innerHTML = '';
  mensajes.forEach(m => {
    const b = document.createElement('div');
    b.className = 'burbuja ' + (m.de === 'tu' ? 'de-tu' : 'de-cort');
    const pies = [];
    if (m.de === 'tu') pies.push('tú');
    else pies.push('CORT');
    if (m.fuente) pies.push(`<span class="bur-fuente">${esc(m.fuente)}</span>`);
    if (m.modo && m.modo !== 'normal') {
      const mo = CH_MODOS.find(x => x.id === m.modo);
      pies.push(`<span class="bur-modo">${mo ? esc(mo.ic + ' ' + mo.txt) : esc(m.modo)}</span>`);
    }
    if (m.adj) pies.push(`<span class="bur-adj">📎 ${esc(m.adj)}</span>`);
    b.innerHTML = `<div class="bur-texto">${esc(m.texto).replace(/\n/g, '<br>')}</div>
      <div class="bur-pie"><span>${pies.join(' · ')}</span>
      <button class="bur-copiar" title="Copiar este texto">copiar</button></div>`;
    b.querySelector('.bur-copiar').onclick = () => copia(m.texto, 'Copiado.');
    caja.appendChild(b);
  });
  caja.scrollTop = caja.scrollHeight;
  pintaUsandoCharla();
}

/* El desplegable del modelo, calco del de Gemini: nombre arriba con ▾, filas con su
   ✓ y su explicación, y un pie que abre 10 · Modelos en el PC.
   Los datos salen de `GET /api/models` (los que Ollama ya tiene bajados) y elegir uno
   es `POST /api/models/use`, exactamente lo que hace la ventana 10. */
async function cargaModelos() {
  const caja = document.getElementById('gm-despl');
  if (!caja) return;
  const enPC = !enTelefono();
  const rotulo = document.getElementById('gm-modelo-n');
  const pinta = html => { caja.innerHTML = html; };
  const deja = nombre => { if (rotulo) rotulo.textContent = nombre || 'modelo del núcleo'; };
  // El teléfono no tiene modelos: los tiene Ollama, y Ollama vive en el portátil.
  // Sin PC la lista NO se pinta vacía en silencio —eso parece un fallo de CORT—,
  // se pone el aviso de «sin PC» con la misma frase del resto de la cara.
  if (!await hayNucleo()) {
    deja('sin portátil');
    pinta(`<div class="gm-opc"><span class="marca">!</span><span><b>El portátil está apagado o fuera de la red</b>
      <small>${esc(sinNucleoFrase())}</small></span></div>`);
    if (enTelefono()) avisaModelosEnPC();
    return;
  }
  let data = null, porque = '';
  try {
    data = await (await fetch(ctx.api() + '/api/models', { signal: AbortSignal.timeout(6000) })).json();
  } catch (e) {
    // Dos causas distintas, dos frases distintas: «el PC está apagado/fuera de red»
    // ya lo contesta `hayNucleo()`; aquí el PC contestó antes y ahora se calló.
    porque = /Timeout|Abort/i.test(String(e && e.name || e))
      ? 'tu PC está conectado pero tardó demasiado en contestar'
      : 'tu PC está conectado pero no contestó (¿cerraste CORT en el portátil?)';
    nucleo = false;                      // la próxima vez se vuelve a preguntar
  }
  if (!data) {
    deja('sin lista');
    pinta(`<div class="gm-opc"><span class="marca">!</span><span><b>no leí la lista de modelos</b>
      <small>${esc(porque)}</small></span></div>`);
    return;
  }
  const bajados = (data.modelos || []).filter(m => m.descargado);
  const activo = bajados.find(m => m.activo);
  deja(activo?.modelo || (bajados.length ? bajados[0].modelo : ''));
  if (!bajados.length) {
    pinta(`<div class="gm-opc"><span class="marca">·</span><span><b>${esc(enPC
      ? 'ningún modelo descargado todavía'
      : 'en el teléfono no hay modelos que bajar: viven en tu portátil')}${enPC ? ''
      : ', con CORT abierto ahí la charla ya usa el que tengas puesto'}</b>
      <small>${esc(enPC ? 'bájalo en 10 · Modelos (flecha ↓)' : 'aquí sólo se eligen y se conversa con ellos')}</small></span></div>`)
      + (enPC ? botonBajarModelos() : '');
    if (enPC) enganchaBajarModelos(caja);
    if (enTelefono()) avisaModelosEnPC();
    pintaUsandoCharla();
    return;
  }
  pinta(bajados.map(m => `<button class="gm-opc${m.activo ? ' activa' : ''}" data-m="${esc(m.modelo)}">
      <span class="marca">${m.activo ? '✓' : '·'}</span>
      <span><b>${esc(m.modelo)}</b><small>${m.activo ? 'el que está puesto ahora' : 'tocado, se usa en la próxima respuesta'}</small></span>
    </button>`).join('')
    + `<div class="gm-opc" style="cursor:default"><span class="marca">≡</span><span><b>Nivel de razonamiento</b>
       <small>lo que se añade con el modo de abajo: Explícame, Resume, Plan…</small></span></div>`
    + (enPC ? botonBajarModelos()
            : '<div class="gm-opc" style="cursor:default"><span class="marca">🏠</span><span><b>Los modelos están en el portátil</b>'
              + '<small>allí bajan y allí corren</small></span></div>'));
  if (enPC) enganchaBajarModelos(caja);
  else avisaModelosEnPC();
  caja.querySelectorAll('.gm-opc[data-m]').forEach(b => b.onclick = async () => {
    try {
      const r = await fetch(ctx.api() + '/api/models/use', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ modelo: b.dataset.m }),
      });
      const j = await r.json();
      ctx?.say?.(j.error ? 'No pude cambiar de modelo: ' + j.error : 'Usando ' + b.dataset.m + '.');
      caja.querySelectorAll('.gm-opc[data-m]').forEach(o => {
        o.classList.toggle('activa', o === b);
        o.querySelector('.marca').textContent = o === b ? '✓' : '·';
      });
      chModelo = b.dataset.m;
      deja(chModelo);
      pintaUsandoCharla();
    } catch { ctx?.say?.('El núcleo no respondió el cambio de modelo.') }
  });
  // El rótulo de la barra y el modelo activo se conocen aquí, que es donde sale la
  // lista: `pintaUsandoCharla` lee `chModelo` para la línea de abajo.
  chModelo = activo?.modelo || '';
  pintaUsandoCharla();
}

/* En el PC la pantalla Charla se limita a lo que ya sabe hacer: enseñar la lista,
   el chip activo y UN botón que abre la ventana 10 · Modelos de `hud.js` — que es
   donde están las flechas ↓, la barra de progreso y el veredicto de RAM. No se
   duplica el descargador aquí: se abre el que existe. El aviso va por un evento
   porque `hud.js` es dueño de las ventanas y `pantallas.js` no las ve. */
const botonBajarModelos = () =>
  '<button class="ch-mo ch-bajar" id="ch-bajar" title="Abrir 10 · Modelos">↓ bajar modelos</button>';

function enganchaBajarModelos(caja) {
  const b = caja.querySelector('#ch-bajar');
  if (!b) return;
  b.onclick = () => {
    window.dispatchEvent(new CustomEvent('cort-ventana', { detail: 'modelos' }));
    ctx?.term?.('abriendo 10 · Modelos desde la Charla', 'pantallas');
  };
}

/* Lo de los modelos en el teléfono se dice una sola vez por arranque: si no, cada
   vez que la dueña entra en Charla CORT le repite la misma explicación. */
let modelosAvisados = false;
function avisaModelosEnPC() {
  if (modelosAvisados) return;
  modelosAvisados = true;
  ctx?.say?.('Tus modelos viven en el portátil: ahí se bajan y ahí corren. '
    + 'Aquí en el teléfono sólo los elijo y converso con ellos.');
}

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

/* ─────────────────────────── 02 · CÓDIGO ─────────────────────────── */
/*
 * Entorno de programación y terminal. Dicho sin adornos y sin prometer lo que
 * Android no deja: **quien ejecuta es el PC**, porque dentro de una APK una app
 * normal no puede abrir una shell ni instalar paquetes (sandbox). Lo que hay aquí
 * es el terminal real del equipo (por `/api/command` y su ejecutor de acciones) y
 * un cuaderno de código: escribes o pegas, pides que lo arregle, y lo guardas.
 */
const CLAVE_CODIGO = 'cort-codigo';

function montaCodigo() {
  const cuerpo = document.querySelector('#scr-codigo .scr-cuerpo');
  let guardado = '';
  try { guardado = localStorage.getItem(CLAVE_CODIGO) || ''; } catch { /* nada */ }
  cuerpo.innerHTML = `
    <div class="scr-lista cod-out" id="cod-out"></div>
    <div class="cod-fila">
      <span class="cod-prompt">cort@pc:~$</span>
      <input id="cod-entrada" placeholder=" Instala, arregla, actualiza… (escribe y Enter)" autocomplete="off">
      <button id="cod-enviar" title="Ejecutar">▲</button>
    </div>
    <details class="cod-nota" ${guardado ? 'open' : ''}>
      <summary>cuaderno de código (lo que escribas aquí no se pierde)</summary>
      <textarea id="cod-editor" spellcheck="false"
        placeholder="pega o escribe tu código…&#10;&#10;p.ej. un script de Python que ordene descargas"></textarea>
      <div class="cod-botones">
        <button id="cod-arregla">pide a CORT que lo arregle</button>
        <button id="cod-copia">copiar</button>
        <button id="cod-guarda">guardar en Notas</button>
      </div>
    </details>`;
  const editor = cuerpo.querySelector('#cod-editor');
  editor.value = guardado;
  editor.addEventListener('input', () => {
    try { localStorage.setItem(CLAVE_CODIGO, editor.value); } catch { /* nada */ }
  });
  cuerpo.querySelector('#cod-copia').onclick = () => copia(editor.value, 'Código copiado.');
  cuerpo.querySelector('#cod-guarda').onclick = async () => {
    if (!editor.value.trim()) return ctx?.say?.('El cuaderno está vacío.')
    try {
      const r = await fetch(ctx.api() + '/api/notes', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        // `texto`, NO `text`: el modelo `Nota` del núcleo sólo tiene ese campo, y con
        // `text` FastAPI contesta 422 —el botón decía «el núcleo no dejó guardarlo»
        // sin que nadie hubiera probado a guardarlo de verdad (cazado al coser [18]).
        body: JSON.stringify({ texto: '[código] ' + editor.value }),
      });
      ctx?.say?.(r.ok ? 'Guardado en 04 · Notas.' : 'El núcleo no dejó guardarlo.');
    } catch { ctx?.say?.('Sin núcleo: no pude guardarlo.') }
  };
  cuerpo.querySelector('#cod-arregla').onclick = () => {
    const texto = editor.value.trim();
    if (!texto) return ctx?.say?.('Escribe o pega algo primero.')
    ir('charla');
    const entrada = document.getElementById('ch-entrada');
    if (entrada) {
      entrada.value = 'Revisa este código, dime qué está mal y devuélvemelo arreglado, comentado en español:\n\n' + texto;
      entrada.focus();
    }
  };
  const entrada = cuerpo.querySelector('#cod-entrada');
  cuerpo.querySelector('#cod-enviar').onclick = () => codigo(entrada.value);
  entrada.addEventListener('keydown', e => { if (e.key === 'Enter') codigo(entrada.value); });
}

const HISTORIAL_CODIGO = [];
async function codigo(texto) {
  const orden = String(texto || '').trim();
  if (!orden) return;
  const entrada = document.getElementById('cod-entrada');
  if (entrada) entrada.value = '';
  HISTORIAL_CODIGO.push(orden);
  escribeCodigo('$ ' + orden, 'orden');
  const estado = document.querySelector('#scr-codigo .scr-estado');

  /* ── la terminal AMPLIADA del teléfono (ronda 2.4) ──
     Hasta ahora, sin el portátil delante esta pantalla sólo sabía decir «sin
     núcleo». Ahora la línea se atiende en el propio aparato, en dos niveles:
     1) las órdenes del puente —volumen, linterna, alarma, apps, memoria, voz,
        atuendo, agenda y las de los cerebros de casa (`busca cerebros`, `modelos`,
        `usa el modelo …`, `descarga el modelo …`, `borra el modelo …`)—, y
     2) lo que no es orden: se le pregunta al cerebro del teléfono (`Mente`), que
        contesta con `Cerebro`/`Razon` sin red, o con el modelo local de Ollama si
        lo elegiste. La respuesta NO se espera aquí: llega por el evento `mente` y
        se escribe en esta misma terminal (el `espejo` de `telefono.js`), porque
        bloquear el hilo del puente es justo lo que traba el teléfono.
     Se necesita `CortNative.mente`: un instalador anterior lo echa de menos y cae
     en la frase honesta de siempre, no en un botón mudo. */
  if (enTelefono() && typeof (window.CortNative || {}).mente === 'function') {
    if (terminalTelefono(orden, escribeCodigo)) return;
    escribeCodigo('la contesto yo, sin el portátil…', 'aviso');
    try {
      window.CortNative.mente(JSON.stringify({ que: 'preguntar', texto: orden, eco: orden.slice(0, 40) }));
      return;
    } catch (e) { escribeCodigo('el cerebro del teléfono no respondió: ' + e, 'aviso'); return; }
  }

  if (!await avisaSinNucleo(estado)) {
    escribeCodigo(sinNucleoFrase(), 'aviso'); return;
  }
  try {
    const r = await fetch(ctx.api() + '/api/command', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ message: orden }),
    });
    const j = await r.json();
    escribeCodigo(j.reply || j.error || 'sin respuesta', 'cort');
    (j.done || []).forEach(a => escribeCodigo('· hecho: ' + a, 'hecho'));
    ctx?.orb?.burst?.();
  } catch (e) {
    escribeCodigo('el núcleo no respondió: ' + e, 'aviso');
  }
}
function escribeCodigo(linea, clase) {
  const caja = document.getElementById('cod-out');
  if (!caja) return;
  const d = document.createElement('div');
  d.className = 'cod-linea ' + (clase || '');
  d.textContent = linea;
  caja.appendChild(d);
  caja.scrollTop = caja.scrollHeight;
}
function pintaCodigo() {
  if (!document.getElementById('cod-out')) montaCodigo();
  const caja = document.getElementById('cod-out');
  if (caja && !caja.childElementCount) {
    escribeCodigo('Terminal de CORT — las órdenes se ejecutan en tu PC: «crea la carpeta Apuntes en Documentos», '
      + '«instala ffmpeg», «arregla el permiso de la carpeta».', 'aviso');
    if (enTelefono()) escribeCodigo(
      'En el teléfono esta terminal manda SOBRE EL TELÉFONO: volumen, linterna, alarma, apps, '
      + 'memoria, voz, agenda y los cerebros de tu PC por Wi-Fi (`busca cerebros`, `modelos`, '
      + '`usa el modelo …`, `descarga el modelo …`). Lo que no sea orden lo piensa el cerebro '
      + 'del teléfono, con o sin internet. Instalar paquetes o tocar archivos del ordenador '
      + 'sigue necesitando el portátil: conecta (menú del botón «CORT · PC») y escribe ahí. '
      + 'Escribe `ayuda` para ver la lista.', 'aviso');
  }
}

/* ─────────────────────────── 03 · MÚSICA (teléfono) ─────────────────────── */
/*
 * El reproductor de CORT en el teléfono. Manda sobre `.Reproductor` (servicio con
 * notificación y `MediaSession`), así que la música sigue sonando con la pantalla
 * apagada y el auricular obedece. La barra de progreso se pinta sola con los
 * avisos `type:"music"` que manda Java: **no** hay `setInterval` preguntando, que
 * es justo lo que traba un teléfono modesto.
 */
let musViva = false;

/* ─────────────────────── el transporte, común a Música y MV ───────────────────
   La barra de progreso, el play/pausa, el anterior/siguiente, el parar, el cuadro a
   cuadro, el «me gusta» y el volumen son los mismos botones que mandan sobre
   `.Reproductor`. Se pintan con un prefijo de id y se enganchan **una sola vez**:
   duplicarlos sería tener dos transportes que un día mandan distinto.

   F9: la disposición es la del reproductor a pantalla completa de Lark Player (sus
   doce capturas), pero **los ids no cambian** — `pintaProgreso`, `ponRotulos` y el
   `enganchaTransporte` de siempre siguen buscando `mu-play`, `mv-prog`, etc. Lo que
   se movió es el envoltorio: portada cuadrada arriba, título teñido, línea fina con
   `0:02 / 3:11`, los tres botones gordos, el volumen, la fila de chips y abajo las
   tres acciones de Lark («ponme algo», «letra», «modo juego»).

   Lo que Lark tiene y CORT **no** puede copiar porque el puente no lo da: carátula
   real (`.Reproductor` no devuelve ninguna imagen), ecualizador, carpetas y cola.
   No se pintan falsos: el cuadro grande lleva el glifo y el acento de la app. */
const transporteHTML = p => `
  <div class="lk-player">
    <div class="lk-portada-grande" id="${p}-caratula"><i>♪</i></div>
    <div class="lk-titulo" id="${p}-ahora">nada puesto</div>
    <div class="lk-artista"><span id="${p}-artista"></span></div>
    <div class="lk-linea">
      <span id="${p}-t0">0:00</span>
      <div class="mu-barra" id="${p}-barra"><i id="${p}-prog"></i></div>
      <span id="${p}-t1">—</span>
    </div>
    <div class="lk-fila-botones">
      <button id="${p}-prev" class="lk-gordo" title="anterior">⏮</button>
      <button id="${p}-play" class="lk-gordo lk-play" title="play / pausa">▶</button>
      <button id="${p}-next" class="lk-gordo" title="siguiente">⏭</button>
    </div>
    <div class="mu-volumen"><span>volumen</span>
      <input id="${p}-vol" type="range" min="0" max="1" step=".05" value=".8"></div>
    <div class="mu-fila2 lk-pastillas">
      <button id="${p}-gusta" class="mu-chip">👍 me gusta</button>
      <button id="${p}-no" class="mu-chip">👎 quítala</button>
      <button id="${p}-envia" class="mu-chip" title="enviar esta pista por WhatsApp, correo o lo que quieras">📤 enviar</button>
      <button id="${p}-cuadro-a" class="mu-chip" title="un fotograma atrás (±1/30 s en vídeo)">◂ cuadro</button>
      <button id="${p}-cuadro-b" class="mu-chip" title="un fotograma adelante (±1/30 s en vídeo)">cuadro ▸</button>
      <button id="${p}-stop" class="mu-chip" title="parar del todo">⏹ parar</button>
    </div>
    <div class="lk-abajo">
      <button id="${p}-auto" title="una pista sacada de tus gustos"><i>♪</i><span>ponme algo</span></button>
      <button id="${p}-letras" title="el vídeo con su letra (MV)"><i>▣</i><span>letra</span></button>
      <button id="${p}-juego" title="CORT se calla y no escucha mientras juegas"><i>🎮</i><span>modo juego</span></button>
    </div>
  </div>`;

function enganchaTransporte(donde, p) {
  // El prefijo lleva GUION: los ids se escriben `${p}-play`, así que buscar
  // `'#' + p + s` daba `#muplay`, que no existe. Medido en la sonda (F8): el `null`
  // del primer botón tiraba `TypeError`, y como `montaMusica()` es el paso previo a
  // MV, Equipo, Charla y Código, la cara nueva Entera se caía en silencio — por eso
  // en el teléfono instalado seguía saliendo la tira de botones de siempre.
  const $ = s => donde.querySelector('#' + p + '-' + s);
  const ponTema = tema => {
    const ahora = $('ahora'), artista = $('artista');
    if (ahora) ahora.textContent = tema ? tema.titulo : 'nada puesto';
    if (artista) artista.textContent =
      tema ? [tema.artista, tema.genero].filter(Boolean).join(' · ') : '';
  };
  $('play').onclick = alternaReproduccion;
  $('prev').onclick = () => llama('musicaAnterior');
  $('next').onclick = () => llama('musicaSiguiente');
  $('stop').onclick = () => { llama('musicaParar'); ponTema(null); pintaProgreso({ vivo: false }); };
  $('gusta').onclick = () => {
    const e = estadoMusica(); if (!e?.pista) return ctx?.say?.('Nada puesto para evaluar.');
    llama('musicaGustar', e.pista.uri, true); ctx?.say?.('Anotado: te gusta esto.');
  };
  $('no').onclick = () => {
    const e = estadoMusica(); if (!e?.pista) return ctx?.say?.('Nada puesto para quitar.');
    llama('musicaGustar', e.pista.uri, false); llama('musicaSiguiente');
  };
  // «Envíame esa canción»: `comparte` acepta el `content://` del índice, que es lo
  // único que la cara conoce de la pista. Android saca su cuadro de apps, así que la
  // dueña elige WhatsApp, correo o Drive sin que CORT decida por ella.
  $('envia').onclick = () => {
    const e = estadoMusica(); if (!e?.pista) return ctx?.say?.('No hay nada puesto que enviar.');
    if (!puede('comparte')) return ctx?.say?.('Enviar archivos con CORT lo trae el APK nuevo de la Release.');
    const crudo = llama('comparte', e.pista.uri || e.pista.video || '');
    let r = null; try { r = crudo ? JSON.parse(crudo) : null; } catch (torcido) { r = null; }
    if (!r) return ctx?.say?.('El teléfono no respondió a lo de enviar.');
    if (r.ok === false) return ctx?.say?.(r.dice || 'ese archivo no se pudo enviar.');
    ctx?.say?.('Te enseño ' + (r.envia || 'el archivo') + ': elige por dónde lo mandas.');
  };
  // Cuadro a cuadro: manda al servicio (±1/30 s, lo hace Java) y, si la imagen de MV
  // está viva, se mueve con él — es la misma pista, no tiene sentido que vayan a dos
  // sitios. Por eso se hace aquí y no sólo en MV.
  $('cuadro-a').onclick = () => { llama('musicaCuadro', true); mueveVideoLocal(-1 / 30); };
  $('cuadro-b').onclick = () => { llama('musicaCuadro', false); mueveVideoLocal(1 / 30); };
  $('auto').onclick = () => llama('musicaAutomatica');
  // «Letra» es el botón de Lark que sube el vídeo con su karaoke: es OTRA hoja del
  // mismo servicio, así que se cambia de hoja en vez de duplicar el reproductor.
  $('letras').onclick = () => {
    ir('mv');
    const caja = document.getElementById('mv-letra');
    if (caja) caja.scrollIntoView({ block: 'start' });
  };
  $('vol').oninput = e => llama('musicaVolumen', +e.target.value);
  $('barra').onclick = ev => {
    const e = estadoMusica(); if (!e || !e.dur) return;
    const r = ev.currentTarget.getBoundingClientRect();
    const seg = (ev.clientX - r.left) / r.width * e.dur / 1000;
    llama('musicaSalto', Math.round(seg * 1000));
    saltaVideo(seg);
  };
  // El modo juego es del teléfono; el botón está en los dos transportes por si la
  // dueña llega antes a Música que a MV. La respuesta, en voz alta, siempre.
  $('juego').onclick = () => ctx?.say?.(modoJuego(!((estadoMusica() || {}).juego)));
}

/* ───────────────────────── la píldora de música, en la esquina ─────────────────
   Lo que la dueña pidió con «si es otra interfaz de música, ya no debe aparecer en
   la bandeja de abajo: debe estar en un botón accesible, en una esquina, para que no
   moleste, porque uno dice CORT PC y está atravesado». Antes no existía tal cosa:
   cuando sonaba algo, o te ibas a la hoja Música entera, o te quedabas con la tira
   del dock cruzando todo el borde inferior — justo donde el pulgar trabaja.
   El calco es el mini-reproductor de Lark Player (portada · título · play/pausa),
   pero **encogido en la esquina inferior izquierda**: a la derecha del todo vive el
   micrófono flotante, y en medio la fila del transporte. Se pliega con su ✕ y se
   queda plegado hasta que la pista pare (si no, reaparecería cada refresco de
   estado); con el modo juego activo no aparece — ahí CORT se aparta, que es la
   promesa del modo juego — y en las hojas Música y MV tampoco: ahí ya está el
   transporte completo. */
let pildoraPlegada = false;

const alternaReproduccion = () => {
  const e = estadoMusica();
  if (!e || !e.vivo) { llama('musicaAutomatica'); return; }
  e.suena ? llama('musicaPausa') : llama('musicaPlay');
};

function montaPildora() {
  if (document.getElementById('repro-pildora')) return;
  const p = document.createElement('div');
  p.id = 'repro-pildora';
  p.innerHTML = '<button id="rp-portada" title="abrir la música">♪</button>'
    + '<div id="rp-texto"><b id="rp-titulo">—</b><span id="rp-artista"></span></div>'
    + '<button id="rp-play" title="pausa o sigue">▶</button>'
    + '<button id="rp-cierra" title="recoger hasta que pare la pista">✕</button>';
  document.body.appendChild(p);
  const abre = () => ir('musica');
  p.querySelector('#rp-portada').onclick = abre;
  p.querySelector('#rp-texto').onclick = abre;
  p.querySelector('#rp-play').onclick = alternaReproduccion;
  p.querySelector('#rp-cierra').onclick = () => {
    pildoraPlegada = true; p.classList.remove('viva');
  };
}

function pintaPildora(e) {
  const p = document.getElementById('repro-pildora');
  if (!p) return;
  const viva = !!e && !!e.vivo && !!e.pista && !e.juego && !pildoraPlegada
    && actual !== 'musica' && actual !== 'mv';
  p.classList.toggle('viva', viva);
  if (!viva) { if (!e || !e.pista) pildoraPlegada = false; return; }
  p.querySelector('#rp-titulo').textContent = e.pista.titulo || 'sin título';
  p.querySelector('#rp-artista').textContent =
    [e.pista.artista, e.pista.genero].filter(Boolean).join(' · ');
  p.querySelector('#rp-play').textContent = e.suena ? '⏸' : '▶';
}

/* ───────────── la hoja de Música, calco de Lark Player (F9) ─────────────
   De sus doce capturas se copió la estructura: barra arriba (nombre + buscar +
   ordenar + ⋮), fila de chips con el activo RELLENO, sección con su cuenta, lista de
   filas (miniatura · título · artista · duración) y mini-reproductor anclado abajo
   que, al tocarlo, sube el reproductor a pantalla completa. Las tres acciones se
   hacen con las **hojas que suben de abajo**, igual que Lark con «Ordenar videos por»
   y su menú de contexto.

   Lo que se copió es lo que el puente da: `musicaBuscar`, `musicaPorGusto`,
   `musicaListas`, `musicaPerfil`, `musicaPoner…`. El orden es cliente (sobre la
   lista ya leída, con su `dur` real) porque `.Reproductor` no acepta un criterio de
   orden; y no hay carátula, carpetas ni ecualizador por el mismo motivo. */
let musLista = [];          // última lista leída del índice: con ella se ordena sin volver a Java
let musVista = 'lista';     // 'lista' | 'player'
let musChip = 'canciones';  // la pestaña que va rellena
let musOrden = 'indice';    // 'indice' | 'titulo' | 'artista' | 'dur'

const MUS_CHIPS = [
  { id: 'canciones', txt: 'Canciones' },
  { id: 'videos', txt: 'Vídeos' },
  { id: 'listas', txt: 'Playlists' },
  { id: 'gustos', txt: 'Tus gustos' },
];

function montaMusica() {
  const cuerpo = document.querySelector('#scr-musica .scr-cuerpo');
  if (!cuerpo) return;
  cuerpo.innerHTML = `
    <div class="lk-barra">
      <button class="lk-btn" id="mu-vuelve" title="Volver">‹</button>
      <span class="lk-nombre">Música</span>
      <span class="lk-espacio"></span>
      <button class="lk-btn" id="mu-busca-btn" title="Buscar en tu música">🔍</button>
      <button class="lk-btn" id="mu-orden-btn" title="Ordenar">↕</button>
      <button class="lk-btn" id="mu-mas-btn" title="Más acciones">⋮</button>
    </div>
    <div class="mu-lista-top" id="mu-buscador" hidden>
      <input id="mu-busca" placeholder="busca título, artista o género…">
      <button id="mu-buscar">buscar</button>
      <button id="mu-gusto" title="las que mejor encajan con tus gustos">por gusto</button>
    </div>
    <div class="lk-pestanas" id="mu-chips"></div>
    <div id="mu-lista">
      <div class="lk-seccion"><span id="mu-seccion-t">Canciones</span><small id="mu-cuenta"></small></div>
      <div class="lk-lista scr-lista" id="mu-pistas"></div>
      <div class="mu-playlists" id="mu-listas" hidden>
        <div class="lk-seccion">Mis listas<small>guardadas en el teléfono</small></div>
        <div class="mu-pl-caja lk-pastillas" id="mu-pl-caja"></div>
        <div class="mu-pl-top">
          <input id="mu-pl-nombre" placeholder="nombre de la lista">
          <button id="mu-pl-guarda">guardar la que suena</button>
          <button id="mu-pl-refresca">recargar</button>
        </div>
      </div>
      <div id="mu-gustos" hidden>
        <div class="lk-seccion">Lo que más te gusta<small>de tus 👍</small></div>
        <div class="mu-perfil" id="mu-perfil"></div>
        <div class="lk-pastillas" id="mu-perfil-chips"></div>
      </div>
      <div class="lk-mini" id="mus-mini" hidden>
        <button id="mus-mini-portada" title="abrir el reproductor">♪</button>
        <div class="lk-mini-txt"><b id="mus-mini-t">—</b><span id="mus-mini-a"></span></div>
        <button id="mus-mini-play" title="pausa o sigue">▶</button>
      </div>
    </div>
    <div id="mu-player" hidden>${transporteHTML('mu')}</div>`;

  const q = cuerpo.querySelector('#mu-busca');
  enganchaTransporte(cuerpo, 'mu');
  pintaChipsMusica();
  cuerpo.querySelector('#mu-busca-btn').onclick = () => {
    const caja = cuerpo.querySelector('#mu-buscador');
    caja.hidden = !caja.hidden;
    if (!caja.hidden) q.focus();
  };
  cuerpo.querySelector('#mu-buscar').onclick = () => buscaMusica(q.value, false);
  q.addEventListener('keydown', e => { if (e.key === 'Enter') buscaMusica(q.value, false); });
  cuerpo.querySelector('#mu-gusto').onclick = () => buscaMusica(q.value, true);
  cuerpo.querySelector('#mu-orden-btn').onclick = hojaOrden;
  cuerpo.querySelector('#mu-mas-btn').onclick = hojaMas;
  cuerpo.querySelector('#mu-vuelve').onclick = () => {
    if (musVista === 'player') vistaMusica('lista'); else ir('orbe');
  };
  cuerpo.querySelector('#mus-mini').onclick = () => vistaMusica('player');
  cuerpo.querySelector('#mus-mini-portada').onclick = () => vistaMusica('player');
  cuerpo.querySelector('#mus-mini-play').onclick = ev => {
    ev.stopPropagation();            // tocar el play no debe abrir el reproductor entero
    alternaReproduccion();
    pintaMini(estadoMusica());
  };
  cuerpo.querySelector('#mu-pl-guarda').onclick = () => guardaLista();
  cuerpo.querySelector('#mu-pl-refresca').onclick = () => {
    cuerpo.querySelector('#mu-pl-caja').textContent = ''; pintaListas();
  };
  vistaMusica('lista');
  pintaListas();
  perfil();
  buscaMusica('', false);            // Lark abre con la lista ya delante, no con un buscador vacío
}

/* Las dos vistas de la hoja (lista ↔ reproductor a pantalla completa) y los chips.
   Se esconde en vez de montar y desmontar: el transporte tiene que seguir vivo para
   que `pintaProgreso` siga pintando la barra aunque la dueña esté mirando la lista. */
function vistaMusica(que) {
  musVista = que;
  const lista = document.getElementById('mu-lista');
  const player = document.getElementById('mu-player');
  if (lista) lista.hidden = que !== 'lista';
  if (player) player.hidden = que !== 'player';
  const vuelve = document.getElementById('mu-vuelve');
  if (vuelve) vuelve.title = que === 'player' ? 'Volver a la lista' : 'Volver al orbe';
  pintaMini(estadoMusica());
}

function pintaChipsMusica() {
  const caja = document.getElementById('mu-chips');
  if (!caja) return;
  caja.innerHTML = MUS_CHIPS.map(c =>
    `<button class="lk-pestana${c.id === musChip ? ' activa' : ''}" data-c="${c.id}">${c.txt}</button>`).join('');
  caja.querySelectorAll('[data-c]').forEach(b => b.onclick = () => eligeChip(b.dataset.c));
}

function eligeChip(c) {
  musChip = c;
  pintaChipsMusica();
  const seccion = document.getElementById('mu-seccion-t');
  const pistas = document.getElementById('mu-pistas');
  const listas = document.getElementById('mu-listas');
  const gustos = document.getElementById('mu-gustos');
  const enLista = c === 'canciones' || c === 'videos';
  if (pistas) pistas.hidden = !enLista;
  if (seccion) seccion.textContent = (MUS_CHIPS.find(x => x.id === c) || {}).txt || 'Canciones';
  if (listas) listas.hidden = c !== 'listas';
  if (gustos) gustos.hidden = c !== 'gustos';
  if (c === 'listas') {
    const caja = document.getElementById('mu-pl-caja');
    if (caja) caja.textContent = '';              // obliga a releer: Java pudo cambiar las listas
    pintaListas();
  }
  if (c === 'gustos') { perfil(); pintaGustos(); }
  if (enLista) buscaMusica(document.getElementById('mu-busca')?.value || '', false);
}

/* El «Ordenar» de Lark, pero dicho como es: los criterios se aplican a la lista que
   ya está leída. La duración es la que manda `.Reproductor` (`dur` en ms), no un
   adorno. */
function hojaOrden() {
  const OPC = [
    ['indice', 'Como vinieron', 'el orden del índice'],
    ['titulo', 'Título', 'A → Z'],
    ['artista', 'Artista', 'A → Z'],
    ['dur', 'Duración', 'las más largas primero'],
  ];
  abreHoja({
    titulo: 'Ordenar por',
    html: OPC.map(([id, txt, sub]) => `<div class="hoja-fila${id === musOrden ? ' elegida' : ''}"
      data-o="${id}"><i>${id === musOrden ? '✓' : '·'}</i>${txt}<small>${sub}</small></div>`).join(''),
    alAbrir: raiz => raiz.querySelectorAll('[data-o]').forEach(f => f.onclick = () => {
      musOrden = f.dataset.o;
      pintaMusicaLista();
      ctx?.say?.('Ordenado por ' + (OPC.find(o => o[0] === musOrden) || ['', 'el índice'])[1].toLowerCase() + '.');
      cierraHoja();
    }),
  });
}

/* El menú ⋮: sólo cosas que el puente sabe hacer. «Añadir a la lista» guarda la
   pista actual con `musicaGuardarLista`; no hay cola que editar (`.Reproductor` no
   la expone), así que aquí no se finge. */
function hojaMas() {
  const e = estadoMusica();
  const pista = e?.pista;
  const filas = [
    ['♪', 'Ponme algo de tus gustos', 'sin tocar nada', () => { llama('musicaAutomatica'); cierraHoja(); }],
    ['👍', pista ? 'Me gusta: ' + (pista.titulo || '') : 'Me gusta', 'entrena tus gustos', () => {
      if (!pista) return ctx?.say?.('No hay nada puesto que evaluar.');
      llama('musicaGustar', pista.uri, true); cierraHoja();
    }],
    ['▣', 'Letra y vídeo (MV)', 'la misma pista', () => { cierraHoja(); ir('mv'); }],
    ['💾', 'Guardar en una lista', pista ? (pista.titulo || '') : 'necesita una pista puesta', () => {
      if (!pista) return ctx?.say?.('Primero pon algo, que se guarda lo que está sonando.');
      const caja = document.getElementById('mu-listas');
      if (caja) caja.hidden = false;
      const nombre = document.getElementById('mu-pl-nombre');
      if (nombre) { nombre.value = pista.titulo || 'mi lista'; nombre.focus(); }
      cierraHoja(); eligeChip('listas');
    }],
    ['🎮', 'Modo juego', 'CORT se aparta mientras juegas', () => {
      ctx?.say?.(modoJuego(!((estadoMusica() || {}).juego))); cierraHoja();
    }],
  ];
  abreHoja({
    titulo: pista ? (pista.titulo || 'la pista') : 'Música',
    html: filas.map(([ic, txt, sub], i) => `<div class="hoja-fila" data-i="${i}">
      <i>${ic}</i>${esc(txt)}<small>${esc(sub)}</small></div>`).join(''),
    alAbrir: raiz => raiz.querySelectorAll('[data-i]').forEach(f => f.onclick = () => filas[+f.dataset.i][3]()),
  });
}

/* El mini-reproductor anclado de Lark: portada · título · artista · play. Se pinta
   desde `pintaProgreso`, que es el único sitio que recibe los avisos de Java, así
   que no hay temporizador propio. */
function pintaMini(e) {
  const mini = document.getElementById('mus-mini');
  if (!mini) return;
  const viva = !!(e && e.vivo && e.pista) && musVista !== 'player';
  mini.hidden = !viva;
  const tit = document.getElementById('mus-mini-t');
  const art = document.getElementById('mus-mini-a');
  const play = document.getElementById('mus-mini-play');
  if (tit) tit.textContent = e?.pista?.titulo || '—';
  if (art) art.textContent = e?.pista
    ? [e.pista.artista, e.pista.genero].filter(Boolean).join(' · ') : '';
  if (play) play.textContent = e?.suena ? '⏸' : '▶';
  // La fila que suena se tiñe, como en Lark: se compara la `uri` del índice, no el
  // título, porque dos pistas pueden llamarse igual.
  document.querySelectorAll('#mu-pistas .lk-fila').forEach(f =>
    f.classList.toggle('sonando', !!e?.pista && f.dataset.uri === (e.pista.uri || '')));
}

/* Los gustos de verdad (`musicaPerfil`): géneros y artistas con sus puntos. Cada
   chip lanza una búsqueda con ese nombre, que es lo que el índice sabe responder. */
function pintaGustos() {
  const caja = document.getElementById('mu-perfil-chips');
  if (!caja) return;
  let p = null;
  try { p = JSON.parse(llama('musicaPerfil') || 'null'); } catch { p = null; }
  const nombres = [...(p?.generos || []), ...(p?.artistas || [])]
    .filter(x => x && x.nombre).slice(0, 12);
  if (!nombres.length) {
    caja.innerHTML = '<div class="mu-vacio">aún no sé qué te gusta: pulsa 👍 cuando suene algo tuyo</div>';
    return;
  }
  caja.innerHTML = nombres.map((x, i) => `<button class="mu-chip" data-g="${i}">${esc(x.nombre)}</button>`).join('');
  caja.querySelectorAll('[data-g]').forEach(b => b.onclick = () => {
    const q = document.getElementById('mu-busca');
    if (q) q.value = nombres[+b.dataset.g].nombre;
    eligeChip('canciones');
    buscaMusica(nombres[+b.dataset.g].nombre, false);
  });
}

const estadoMusica = () => {
  const crudo = llama('musicaEstado');
  if (!crudo) return null;
  try { return JSON.parse(crudo); } catch { return null; }
};

function buscaMusica(texto, porGusto) {
  const caja = document.getElementById('mu-pistas');
  if (!caja) return;
  if (llama('musicaPuedeLeer') === false) {
    // El permiso **no** se pide solo: Android sólo deja pedirlo desde una
    // pulsación, y aquí la dueña puede pulsar este aviso o el menú del botón
    // flotante «CORT · PC» del teléfono (fila «Dar permiso a la música y los
    // archivos»). Decir «ya lo pedí» sin haberlo pedido sería mentira.
    musLista = [];
    caja.innerHTML = '<div class="mu-vacio">CORT no ve tu música todavía · pulsa '
      + '<b class="mu-dar">Dar permiso a la música y los archivos</b>'
      + ' o ábrelo desde el botón <b>CORT · PC</b> del teléfono.</div>';
    const dar = caja.querySelector('.mu-dar');
    if (dar) dar.onclick = () => {
      if (llama('pidePermisoMedios') === null) {
        ctx?.say?.('Este APK aún no pide el permiso desde aquí: usa el botón CORT · PC.');
        return;
      }
      ctx?.say?.('Ahí tienes el cuadro: acepta leer audio y vídeos.');
    };
    return;
  }
  const crudo = porGusto ? llama('musicaPorGusto', texto || '', 60)
                         : llama('musicaBuscar', texto || '', true);
  try { musLista = JSON.parse(crudo || '[]'); } catch { musLista = []; }
  if (!Array.isArray(musLista)) musLista = [];
  pintaMusicaLista();
}

/* Pintar lo leído, con el chip de en medio y el orden elegido. Se separa de la
   lectura porque las pestañas y la hoja «Ordenar por» vuelven a pintar **la misma
   lista**, sin volverle a pedir nada a Java. */
function pintaMusicaLista() {
  const caja = document.getElementById('mu-pistas');
  if (!caja) return;
  const cuenta = document.getElementById('mu-cuenta');
  let lista = musChip === 'videos' ? musLista.filter(p => p.video) : musLista;
  const ordenada = musOrden === 'indice' ? lista : [...lista].sort((a, b) =>
    musOrden === 'dur' ? (b.dur || 0) - (a.dur || 0)
      : String(a[musOrden] || '').localeCompare(String(b[musOrden] || ''), 'es', { sensitivity: 'base' }));
  if (cuenta) cuenta.textContent = ordenada.length
    ? ordenada.length + (musChip === 'videos' ? ' vídeos' : ' canciones') : '';
  caja.innerHTML = '';
  if (!ordenada.length) {
    caja.innerHTML = '<div class="mu-vacio">nada con ese nombre · prueba con otra palabra o «por gusto»</div>';
    return;
  }
  const uris = ordenada.map(p => p.uri);
  const e = estadoMusica();
  ordenada.forEach((p, i) => {
    const d = document.createElement('div');
    d.className = 'lk-fila' + (e?.pista && e.pista.uri === p.uri ? ' sonando' : '');
    d.dataset.uri = p.uri || '';
    d.innerHTML = `<span class="lk-portada">${p.video ? '▣' : '♪'}</span>
      <span class="lk-txt"><b>${esc(p.titulo)}</b>
        <span>${esc([p.artista, p.genero].filter(Boolean).join(' · '))}</span></span>
      <em>${p.dur ? reloj(p.dur) : ''}</em>`;
    d.onclick = () => {
      if (llama('musicaPoner', uris.join('\n'), i) === false) {
        ctx?.say?.('Esa pista no está en el índice: recarga la lista.');
        return;
      }
      ctx?.orb?.burst?.();
      pintaMusicaLista();
      pintaMini(estadoMusica());
    };
    caja.appendChild(d);
  });
}

function guardaLista() {
  const nombre = document.getElementById('mu-pl-nombre');
  const e = estadoMusica();
  if (!nombre || !nombre.value.trim()) return ctx?.say?.('Ponle nombre a la lista primero.');
  if (!e || !e.pista) return ctx?.say?.('No hay nada sonando que guardar.');
  // Se guarda la canción actual y su URI; las listas son URIs separadas, y Java las
  // vuelve a buscar en el índice cuando se ponen.
  llama('musicaGuardarLista', nombre.value.trim() + ' · ' + e.pista.titulo, e.pista.uri);
  nombre.value = '';
  ctx?.say?.('Lista guardada en «mis listas».');
  document.getElementById('mu-pl-caja').textContent = '';
  pintaListas();
}

function pintaListas() {
  const caja = document.getElementById('mu-pl-caja');
  if (!caja || caja.childElementCount) return;
  let nombres = [];
  try { nombres = JSON.parse(llama('musicaListas') || '[]'); } catch { nombres = []; }
  if (!nombres.length) {
    caja.innerHTML = '<div class="mu-vacio">aún no guardaste ninguna lista</div>';
    return;
  }
  nombres.forEach(n => {
    const b = document.createElement('button');
    b.className = 'mu-chip'; b.textContent = n;
    b.onclick = () => {
      if (llama('musicaPonerLista', n, 0) === false) ctx?.say?.('Esa lista ya no tiene canciones en el teléfono.');
    };
    caja.appendChild(b);
  });
}

function perfil() {
  const caja = document.getElementById('mu-perfil');
  if (!caja) return;
  let p = null;
  try { p = JSON.parse(llama('musicaPerfil') || 'null'); } catch { p = null; }
  const nombres = (g, a) => [(g || []).map(x => x.nombre), (a || []).map(x => x.nombre)]
    .flat().filter(Boolean).slice(0, 5);
  const top = nombres(p?.generos, p?.artistas);
  caja.innerHTML = top.length
    ? 'lo que más te gusta: <b>' + esc(top.join(', ')) + '</b>'
    : 'aún no sé qué te gusta: pulsa 👍 cuando suene algo que te guste.';
}

/* La barra, el título y el tiempo se pintan en la hoja que esté montada (Música o
   MV): es la misma pista, y dos barras que avanzan distinto serían peor que una. */
function pintaProgreso(e) {
  if (!e) return;
  pintaPildora(e);
  pintaMini(e);            // el mini anclado de Lark y la fila teñida van con el mismo aviso
  ['mu', 'mv'].forEach(p => {
    const barra = document.getElementById(p + '-prog');
    if (!barra) return;
    const pct = e.dur ? Math.max(0, Math.min(100, e.pos / e.dur * 100)) : 0;
    barra.style.width = pct + '%';
    const t0 = document.getElementById(p + '-t0');
    const t1 = document.getElementById(p + '-t1');
    if (t0) t0.textContent = reloj(e.pos || 0);
    if (t1) t1.textContent = e.dur ? reloj(e.dur) : '—';
    const play = document.getElementById(p + '-play');
    if (play) play.textContent = e.suena ? '⏸' : '▶';
    // cuadro a cuadro sólo sirve con vídeo delante: sin él, el botón estorba
    const video = !!(e.pista && e.pista.video);
    document.querySelectorAll('#' + p + '-cuadro-a,#' + p + '-cuadro-b')
      .forEach(b => b.style.display = video ? '' : 'none');
  });
}

/* El título y el artista, dicho una vez y pintado en las dos hojas. */
function ponRotulos(e) {
  ['mu', 'mv'].forEach(p => {
    const ahora = document.getElementById(p + '-ahora');
    if (!ahora) return;
    ahora.textContent = e?.pista ? e.pista.titulo : 'nada puesto';
    const art = document.getElementById(p + '-artista');
    if (art) art.textContent = e?.pista
      ? [e.pista.artista, e.pista.genero].filter(Boolean).join(' · ') : '';
  });
}

const reloj = ms => {
  const s = Math.round((ms || 0) / 1000);
  return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
};

function arrancaMusica() {
  const e = estadoMusica();
  pintaProgreso(e);
  ponRotulos(e);
}

/* ─────────────────────────── 04 · MV (teléfono) ─────────────────────────── */
/*
 * La hoja del videoclip, al estilo Lark Player: imagen arriba y letra en karaoke
 * debajo. **No es un reproductor nuevo**: es la misma pista que ya manda
 * `.Reproductor`, así que el audio lo sigue poniendo el servicio (con notificación,
 * auricular y bloqueo) y esta hoja sólo pone la imagen y la letra.
 *
 * El `<video>` va MUDO a propósito: si reprodujera su propio sonido, la canción se
 * oiría doble y desfasada. Y si el WebView no puede abrir el `content://…`, se dice
 * tal cual y el audio del servicio sigue sonando — no se inventa una imagen con un
 * `<canvas>`, que sería mentir con el dibujo.
 *
 * Nada de `setInterval` preguntando la posición: la letra se desplaza con los mismos
 * avisos `type:"music"` de Java que mueven la barra.
 */
let letraLineas = [];            // [{s: segundos, texto}] de la letra sincronizada
let letraPlana = '';             // la letra sin marcas, para copiar
let letraDe = '';                // «artista — título» de lo que hay pintado
let lineaActiva = -1;
let abriendo = 0;                // temporero del aviso honesto de imagen

function montaMV() {
  const cuerpo = document.querySelector('#scr-mv .scr-cuerpo');
  if (!cuerpo) return;                       // en el PC esta hoja no existe
  cuerpo.innerHTML = `
    <div class="mv-pantalla">
      <video id="mv-video" playsinline preload="metadata" muted></video>
      <div class="mv-aviso" id="mv-aviso" hidden></div>
    </div>
    ${transporteHTML('mv')}
    <div class="mv-letra-top">
      <button id="mv-rebuscar" class="mu-chip" title="volver a pedir la letra de esta canción">↻ rebuscar la letra</button>
      <button id="mv-copiar" class="mu-chip" title="copiar la letra entera, sin marcas de tiempo">copiar letra</button>
      <span class="mv-letra-estado" id="mv-letra-estado"></span>
    </div>
    <div class="scr-lista mv-letra" id="mv-letra"></div>`;
  const video = cuerpo.querySelector('#mv-video');
  // Sin la fila de botones de Android encima: el transporte que manda es el de CORT,
  // y dos filas de botones en un teléfono pequeño se estorban entre sí.
  video.controls = false;
  video.addEventListener('error', () => avisoImagen(
    'La imagen no abrió: este WebView no sabe qué hacer con esa dirección de vídeo '
    + '(content://). La canción sigue sonando —el audio lo pone el servicio, no esta página.'));
  video.addEventListener('loadeddata', () => avisoImagen(''));
  cuerpo.querySelector('#mv-rebuscar').onclick = () => pideLetra(true);
  cuerpo.querySelector('#mv-copiar').onclick = () => {
    if (!letraPlana) return ctx?.say?.('Aún no hay letra que copiar: pulsa «rebuscar la letra».');
    copia(letraPlana, 'Letra copiada.');
  };
  enganchaTransporte(cuerpo, 'mv');
}

function arrancaMV() {
  if (!document.getElementById('mv-video')) return;
  const e = estadoMusica();
  pintaProgreso(e);
  ponRotulos(e);
  ponVideo(e);
  pideLetra();
}

/* ── la imagen: misma pista, otro par de ojos ── */
function ponVideo(e) {
  const video = document.getElementById('mv-video');
  if (!video) return;
  const uri = (e && e.pista && e.pista.video) ? (e.pista.uri || e.uri || '') : '';
  if (!uri) {                                 // audio suelto o nada puesto: hoja limpia
    if (video.dataset.uri) { video.removeAttribute('src'); video.load(); video.dataset.uri = ''; }
    avisoImagen(e && e.pista ? 'Esto es audio, no vídeo. La letra sí está aquí abajo.' : '');
    return;
  }
  if (video.dataset.uri !== uri) {
    video.dataset.uri = uri;
    video.src = uri;
    video.load();
    avisoImagen('abriendo la imagen…');
    // Un aviso honesto en vez de un rectángulo negro eterno: si en cuatro segundos
    // no hay imagen, el WebView no pudo (y el audio del servicio ni se entera).
    clearTimeout(abriendo);
    abriendo = setTimeout(() => {
      if (!videoListo()) avisoImagen(
        'La imagen no abrió: este WebView no sabe qué hacer con esa dirección de vídeo '
        + '(content://). La canción sigue sonando —el audio lo pone el servicio, no esta página.');
    }, 4000);
  }
  sincronizaPlay(!!(e && e.suena));
}

function sincronizaPlay(suena) {
  const video = document.getElementById('mv-video');
  if (!video || !video.dataset.uri) return;
  if (suena) {
    // `play()` puede rechazar el `content://`: no es un error de la dueña, se dice.
    const intento = video.play();
    if (intento && intento.catch) intento.catch(() => avisoImagen(
      'La imagen no quiere abrir en esta pantalla. La canción sigue sonando igual.'));
  } else video.pause();
}

const videoListo = () => {
  const v = document.getElementById('mv-video');
  return (v && v.dataset.uri && v.readyState > 0 && isFinite(v.duration)) ? v : null;
};

function avisoImagen(texto) {
  const caja = document.getElementById('mv-aviso');
  if (!caja) return;
  caja.textContent = texto || '';
  caja.hidden = !texto;
}

/* Saltar es una sola cosa para las dos mitades de la hoja: se le manda al servicio
   (`musicaSalto`, en milisegundos) y se mueve también la imagen si está viva. */
function saltaVideo(seg) {
  const v = videoListo();
  if (v) v.currentTime = Math.max(0, seg);
}
function mueveVideoLocal(dS) {
  const v = videoListo();
  if (!v) return;
  const dur = isFinite(v.duration) ? v.duration : 0;
  v.currentTime = Math.max(0, Math.min(dur ? dur - .05 : 0, v.currentTime + dS));
}

/* ── la letra: `/api/letras` y sus marcadores [mm:ss.xx] ── */
function parseaLetra(texto) {
  const sale = [];
  String(texto || '').split('\n').forEach(linea => {
    // LRCLIB escribe `[00:13.42]`; también cabe `[0:07.5]` (un dígito de centésimas)
    // y el punto o los dos puntos como separador. Sin marca de tiempo → no es línea.
    const m = linea.match(/^\s*\[(\d{1,3}):(\d{2})(?:[.:](\d{1,2}))?\](.*)$/);
    if (!m) return;
    const textoLinea = (m[4] || '').trim();
    if (!textoLinea) return;
    // «.5» son 50 centésimas, no 5: se rellena a la derecha antes de dividir.
    const cent = (m[3] || '').padEnd(2, '0');
    sale.push({ s: (+m[1]) * 60 + (+m[2]) + (+cent) / 100, texto: textoLinea });
  });
  return sale;
}

async function pideLetra(forzada) {
  const caja = document.getElementById('mv-letra');
  if (!caja) return;
  const estado = document.getElementById('mv-letra-estado');
  const e = estadoMusica();
  const pista = e && e.pista;
  if (!pista) {
    letraLineas = []; letraPlana = ''; letraDe = ''; lineaActiva = -1;
    caja.innerHTML = '<div class="mu-vacio">nada puesto: en cuanto suene algo, su letra sale aquí.</div>';
    if (estado) estado.textContent = '';
    return;
  }
  const clave = (pista.artista || '') + ' — ' + (pista.titulo || '');
  if (!forzada && letraDe === clave && (letraLineas.length || letraPlana)) return;
  letraDe = clave; letraLineas = []; letraPlana = ''; lineaActiva = -1;
  if (estado) estado.textContent = 'buscando…';
  caja.innerHTML = '<div class="mu-vacio">buscando «' + esc(pista.titulo) + '» en el buscador de letras…</div>';
  const base = await hayNucleo();
  if (base === false) {
    if (estado) estado.textContent = 'sin PC';
    caja.innerHTML = '<div class="mu-vacio">' + esc(sinNucleoFrase()) + '</div>';
    return;
  }
  // La duración va en segundos: es como LRCLIB desambigua las versiones de un mismo
  // título, y `musicaEstado()` la trae en milisegundos.
  const q = new URLSearchParams({
    artista: pista.artista || '', titulo: pista.titulo || '',
    duracion: String(Math.round((e.dur || 0) / 1000)),
  });
  let j = null, porque = '';
  try {
    const r = await fetch(ctx.api() + '/api/letras?' + q.toString(),
      { signal: AbortSignal.timeout(15000) });
    j = await r.json();
  } catch (err) { porque = 'El buscador de letras no contestó: ' + err; }
  if (porque) {
    if (estado) estado.textContent = 'letra pendiente';
    dejaAviso(porque + ' · pulsa «rebuscar la letra» cuando quieras.');
    ctx?.term?.(porque, 'mv');
    return;
  }
  if (!j || j.ok === false) {
    const dicho = (j && j.error) || 'el núcleo no me dio la letra';
    if (estado) estado.textContent = 'letra pendiente';
    dejaAviso(dicho + (j && j.reintenta ? ' · vuelve a rebuscar más tarde' : ''));
    return;
  }
  letraPlana = j.plana || '';
  letraLineas = parseaLetra(j.sincronizada);
  pintaLetra();
  if (estado) estado.textContent = (letraLineas.length ? 'karaoke' : 'sin tiempos')
    + (j.fuente ? ' · ' + j.fuente : '');
  marcaLinea((estadoMusica() || {}).pos || 0);
}

function dejaAviso(texto) {
  const caja = document.getElementById('mv-letra');
  if (caja) caja.innerHTML = '<div class="mu-vacio">' + esc(texto) + '</div>';
}

function pintaLetra() {
  const caja = document.getElementById('mv-letra');
  if (!caja) return;
  caja.innerHTML = '';
  if (!letraLineas.length && !letraPlana) {
    dejaAviso('no llegó letra para esta canción: prueba con «rebuscar la letra» o '
      + 'ponte otra, que a veces el artista y el título vienen con otros nombres.');
    return;
  }
  if (!letraLineas.length) {
    // Sin marcas de tiempo se puede leer y copiar, pero no se resalta sola — se dice,
    // no se finge un karaoke que no tiene relojes.
    letraPlana.split('\n').map(l => l.trim()).filter(Boolean).forEach(l => {
      const d = document.createElement('div');
      d.className = 'mv-l sin-tiempo'; d.textContent = l;
      caja.appendChild(d);
    });
    return;
  }
  letraLineas.forEach((l, i) => {
    const d = document.createElement('div');
    d.className = 'mv-l';
    d.innerHTML = `<span class="mv-s">${esc(reloj(l.s * 1000))}</span><span class="mv-x">${esc(l.texto)}</span>`;
    d.onclick = () => {
      llama('musicaSalto', Math.round(l.s * 1000));
      saltaVideo(l.s);
      marcaLinea(l.s * 1000, true);
    };
    caja.appendChild(d);
  });
}

/* La línea activa, en el centro del panel. El desplazamiento se calcula a mano:
   `scrollIntoView` también movería la página entera y en el teléfono eso salta. */
function marcaLinea(posMs, forzar) {
  const caja = document.getElementById('mv-letra');
  if (!caja || !letraLineas.length) return;
  const t = (posMs || 0) / 1000;
  let i = -1;
  for (let k = 0; k < letraLineas.length; k++) { if (letraLineas[k].s <= t + .15) i = k; else break; }
  if (i === lineaActiva && !forzar) return;
  lineaActiva = i;
  caja.querySelectorAll('.mv-l').forEach((el, k) => el.classList.toggle('activa', k === i));
  const activa = caja.querySelector('.mv-l.activa');
  if (activa) caja.scrollTop = Math.max(0, activa.offsetTop - caja.clientHeight / 2 + activa.offsetHeight / 2);
}

/* ─────────────────────────── el modo juego ───────────────────────────
 * «Me voy a jugar»: una página no puede hacerse sorda a sí misma en Android, así
 * que lo hace Java (`CortNative.modoJuego`): suelta el micrófono, cede el foco de
 * audio y devuelve el toque del auricular al juego. La cara sólo lo pide y lo cuenta.
 * Fuera del teléfono NO se finge: aquí nadie escucha «Oye CORT» mientras juegas. */
export function modoJuego(on) {
  if (!enTelefono()) {
    return 'El modo juego es del teléfono, que es donde te escucho con un juego delante. '
      + 'En el portátil no hay nada que silenciar: la música la pone el navegador.';
  }
  if (!puede('modoJuego')) {
    return 'El modo juego lo trae el APK que se compila aquí (el de Java). '
      + 'Con este cuerpo todavía no puedo callarme ni soltar el micrófono: instala el APK nuevo.';
  }
  llama('modoJuego', !!on);
  const pregunta = puede('juegoActivo') ? llama('juegoActivo') : null;
  const activo = pregunta === null ? !!on : !!pregunta;
  pintaJuego(activo);
  ctx?.term?.('modo juego: ' + (activo ? 'puesto' : 'quitado'), 'pantallas');
  return activo
    ? 'Modo juego puesto: no escucho «Oye CORT», no hablo por encima y el auricular es tuyo. Cuando termines dime «vuelve CORT».'
    : 'Modo juego quitado: vuelvo a escucharte y a avisarte.';
}

/* El avispón vive en la barra de la pantalla activa: discreto, y no tapa el vídeo. */
function pintaJuego(on) {
  const aviso = document.getElementById('pantalla-juego');
  if (!aviso) return;
  aviso.hidden = !on;
  aviso.classList.toggle('viva', !!on);
}

/* Los avisos de Java: play, pausa, canción nueva, cuadro a cuadro y modo juego. Sin
   ellos la barra se quedaría quieta (y preguntar cada 200 ms es lo que traba un
   teléfono). */
function escuchaMusica() {
  if (musViva || !window.__cortNative) return;
  musViva = true;
  window.__cortNative.on(ev => {
    if (!ev || ev.type !== 'music') return;
    const e = ev.estado;
    pintaProgreso(e);
    ponRotulos(e);
    if (e && typeof e.juego !== 'undefined') pintaJuego(e.juego);
    if (e?.pista) perfil();
    if (document.getElementById('mv-video')) {
      ponVideo(e);
      marcaLinea(e?.pos || 0);
      // Canción nueva → letra nueva: se pide sola, sin martillar al buscador.
      const clave = e?.pista ? (e.pista.artista || '') + ' — ' + (e.pista.titulo || '') : '';
      if (clave && clave !== letraDe) pideLetra();
    }
  });
}

/* Los atajos del icono (ronda 2.4.1). Mantener pulsado el icono de CORT en el cajón
   ofrece «Escuchar», «Equipo» y «Charla»; las dos hojas no son una orden de voz, son
   un `Intent` que llega a Java **antes** de que la página exista, así que Java lo
   guarda y lo suelta por el puente (`{"type":"atajo","hoja":"…"}`) cuando la cara ya
   está montada. Aquí se escucha ese aviso y se hace el `ir(hoja)` de siempre, el
   mismo que ejecuta un toque en la barra.

   Se comprueba que la hoja exista en este aparato antes de saltar: `ir()` con un id
   que no está en `visibles()` cae en el Orbe sin decir nada, y un atajo que abre la
   ventana equivocada es peor que un atajo que avisa. «Equipo», por ejemplo, pide el
   puente de acciones: con un APK viejo no existe. */
let atajosViva = false;
function escuchaAtajos() {
  if (atajosViva || !window.__cortNative) return;
  atajosViva = true;
  window.__cortNative.on(ev => {
    if (!ev || ev.type !== 'atajo') return;
    const id = String(ev.hoja || '');
    const p = visibles().find(x => x.id === id);
    if (!p) { ctx?.term?.('ese atajo pide una hoja que no está en este aparato: ' + id, 'pantallas'); return; }
    ir(id);
    ctx?.term?.('atajo: ' + p.titulo, 'pantallas');
  });
}

/* ─────────────────────────── el puente hacia hud.js ─────────────────────── */

export function initPantallas(contexto) {
  ctx = contexto;
  aplicaAccesibilidad();            // antes de pintar: la letra grande no se espera
  montaCarcasa();
  montaNavegacion();
  montaGesto();
  montaTeclas();
  escuchaMusica();
  escuchaAtajos();
  if (enTelefono()) { montaMusica(); montaMV(); montaPildora(); }
  // El Equipo lleva el `ctx` de siempre **más `ir`**: si la dueña dice «cambia la
  // voz» y no nombra ninguna, la hoja tiene que traer la pantalla delante, y eso
  // es de aquí. Se lo pasamos como función para no importar este módulo desde
  // `telefono.js` (los imports circulares en módulos ES dan sorpresas feas).
  telefono = montaTelefono({ ...(ctx || {}), ir }) || { pinta: () => {} };
  montaCharla();
  montaCodigo();
  document.documentElement.classList.add('pantallas-montadas', 'p-orbe');
  // El modo juego sobrevive a cerrar la app (lo guarda Java): si la dueña se fue a
  // jugar y vuelve, el avispón tiene que estar encendido desde el primer instante.
  pintaJuego(!!(estadoMusica() || {}).juego);
  // Y la píldora: si la dueña vuelve a la app con la pista todavía sonando, el
  // aviso de Java puede no llegar hasta que algo cambie. Se pinta una vez al
  // montar, con el estado que ya trae el servicio.
  pintaPildora(estadoMusica());
  // La interfaz nueva de Android no estaba: si el puente existe, la barra de
  // pantallas sustituye al botón flotante que ya había (no se apila encima).
  ctx?.term?.('pantallas listas: ' + visibles().map(p => p.titulo).join(' · '), 'pantallas');
}

/* Que la dueña lo diga y CORT se mueve: se llama desde `send()` en hud.js. */
export function porVoz(texto) {
  const t = String(texto || '').toLowerCase();
  // «vuelve CORT» y «sal del modo juego» son del silencio del teléfono, no de hojas:
  // sin este filtro, la dueña diría «vuelve CORT» y se cambiaría de pantalla en vez
  // de volverle el oído. El resto de «vuelve al orbe» sigue funcionando igual.
  if (/(vuelve|regresa|al orbe|pantalla orbe|la cara de siempre)/i.test(t)
      && !/juego|jugando|\bcort\b/i.test(t)) { ir('orbe'); return 'orbe'; }
  // MV es hoja de teléfono (la imagen sale del servicio de `.Reproductor`): en el PC
  // no se ofrece, y la frase se deja pasar al backend como cualquier otra orden.
  if (enTelefono() && (/(^|[^\w])mv([^\w]|$)/i.test(t)
      || /(videoclip|video[ -]?clip|\bclip\b)/i.test(t)
      || /el video\b/i.test(t)
      || /(pantalla|abre|cambia|mu[eé]strame).{0,14}(mv|video)/i.test(t))) {
    ir('mv'); return 'mv';
  }
  if (/(pantalla|abre|cambia|mu[eé]strame).{0,14}(m[uú]sica|reproductor)/i.test(t) && enTelefono()) { ir('musica'); return 'musica'; }
  if (/(pantalla|abre|cambia|mu[eé]strame).{0,14}(charla|chat|conversa)/i.test(t)) { ir('charla'); return 'charla'; }
  if (/(pantalla|abre|cambia|mu[eé]strame).{0,14}(c[oó]digo|programar|terminal)/i.test(t)) { ir('codigo'); return 'codigo'; }
  // La hoja del teléfono: «abre el equipo», «pantalla equipo», «qué manda CORT en
  // el teléfono». Sólo se ofrece donde hay aparato que mandar, igual que la música.
  // Y con una exclusión a propósito: «optimiza el equipo» / «qué come la ram de mi
  // equipo» ya eran del PC y de 11 · Optimización, y no se los roba esta hoja.
  if (puede('accion') && !/optimiza|qu[eé] come|ram|memoria libre/i.test(t)
      && /(pantalla|abre|abrir|abreme|mu[eé]strame|cambia a|ven a|ens[eé]ñame|d[oó]nde est[aá]n).{0,18}(equipo|mando del tel[eé]fono|lo que manda|el tel[eé]fono)/i.test(t)) {
    ir('equipo'); return 'equipo';
  }
  return null;
}
