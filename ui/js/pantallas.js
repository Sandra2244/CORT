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
 *   en un teléfono de gama media eso también es memoria y batería. Ya no hay
 *   excepción: `p-mv` dejó de ser la hoja donde el orbe se encogía a la esquina
 *   (22/10, con sus capturas delante — «el orbe de CORT no me gusta que aparezca
 *   en MV»), y la letra con su karaoke vive dentro de Música. La regla de CSS que
 *   lo encogía estaba muerta y `hud.js` seguía reanudando el bucle WebGL: caídas
 *   las dos, como cuenta el comentario de `hud.css` junto a `.p-mv`.
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
import { montaCentro } from './centro.js';
import { montaArnes } from './arnes.js';

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
  // `sin-cab` dibujan su propia barra (Lark y Gemini), y la genérica estorba. Se
  // montan con `montables()`, no con `visibles()`: la letra es una hoja que no se
  // ofrece en el cajón pero que SÍ existe, porque el reproductor la abre.
  const CON_BARRA_PROPIA = ['musica', 'charla', 'mv'];
  montables().filter(p => p.id !== 'orbe').forEach(p => {
    const s = document.createElement('section');
    s.className = 'scr' + (CON_BARRA_PROPIA.includes(p.id) ? ' sin-cab' : '');
    s.id = 'scr-' + p.id;
    s.innerHTML = `<header class="scr-top"><button class="scr-vuelve" title="Volver al orbe">‹</button>
      <button class="scr-menu" title="Menú de CORT" aria-label="Menú de CORT">☰</button>
      <b>${esc(p.titulo)}</b><span class="scr-estado"></span></header>
      <div class="scr-cuerpo"></div>`;
    document.body.appendChild(s);
    // El ‹ genérico vuelve al orbe, salvo en la hoja de letra: ahí el sitio del que
    // se viene es el reproductor, y eso es justo lo que significa «fusionada».
    s.querySelector('.scr-vuelve').onclick = () => {
      if (p.id === 'mv') { ir('musica'); vistaMusica('player'); return; }
      ir('orbe');
    };
    s.querySelector('.scr-menu').onclick = abreCajon;
  });

  // El cartel del modo juego. Antes era un aviso mudo; ahora es **la salida**, y por
  // escrito: hasta `2.6.0` el modo se guardaba en Java y sobrevivía a cerrar la app
  // (`CortNative.java:228`), la única forma de quitarlo por voz era decir «vuelve
  // CORT» (`hud.js:1657`) y el propio modo es lo que cierra el micro
  // (`CortNative.arrancarEscucha`). La dueña se quedó clavada en «modo juego» sin
  // poder salir: el interruptor vivía dentro de la hoja Música, que tampoco sonaba.
  // Un toque aquí apaga el modo. No depende del puente para pintarse, pero sí para
  // apagarse, así que con un APK viejo el cartel se queda de aviso y no de botón.
  const juego = document.createElement('button');
  juego.id = 'pantalla-juego';
  juego.type = 'button';
  juego.hidden = true;
  juego.title = 'CORT está en silencio mientras juegas · toca para volver';
  juego.textContent = '🎮 modo juego · toca para salir';
  juego.onclick = () => {
    const dicho = modoJuego(false);
    ctx?.say?.(dicho);
    ctx?.term?.('modo juego quitado desde el cartel', 'pantallas');
  };
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
  /* El orbe: dos caras y una tecla. El de la referencia (la geometría medida en el paso
     1.1, montada en la cara por `orbe-cara.js`) es el que ella eligió el 26/10 — «me
     gusta más, tiene mejor animación» —; el de siempre sigue vivo y se vuelve con esta
     misma fila. Se guarda y SE RECARGA la cara en vez de cambiarlo sobre la marcha:
     ninguno de los dos orbes se desmonta entero a sí mismo (el viejo no expone cómo se
     borran sus mallas), y un WebGL zombi comiéndose memoria en 1,8 GiB es peor que un
     parpadeo al reiniciar la interfaz. La clave `cort-orbe` es la misma que leen
     `ui/index.html` y `CLAVE_ORBE` de `orbe-cara.js`: tres sitios, una cadena, y esa
     coincidencia la vigila `scripts/prueba-orbe-cara.mjs`. */
  let orbeNuevo = true;
  try { orbeNuevo = localStorage.getItem('cort-orbe') !== 'viejo'; } catch { /* modo privado */ }
  const bOrbe = document.createElement('button');
  bOrbe.className = 'cj-fila' + (orbeNuevo ? ' on' : '');
  bOrbe.dataset.aj = 'orbe';
  const txtOrbe = orbeNuevo ? 'Orbe del video (nuevo)' : 'Orbe de siempre';
  bOrbe.innerHTML = `<i>◉</i>${esc(txtOrbe)}`;
  bOrbe.onclick = () => {
    try { localStorage.setItem('cort-orbe', orbeNuevo ? 'viejo' : 'plexo'); } catch { /* sin almacén */ }
    location.reload();
  };
  caja.appendChild(bOrbe);
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
  // `montables()`, no `visibles()`: la hoja de letra está escondida del cajón, pero
  // existe y hay que poder entrar en ella. Con `visibles()` se habría caído al Orbe.
  const p = montables().find(x => x.id === id) || PANTALLAS[0];
  actual = p.id;
  const raiz = document.documentElement;
  montables().forEach(x => raiz.classList.remove('p-' + x.id));
  raiz.classList.add('p-' + actual);
  cierraMenu();
  cierraHoja();
  /* El botón nativo «CORT · PC» ya no existe: estorbaba y parecía que CORT
     arrancaba en modo PC. Su menú de dieciséis filas se abre desde Equipo ▸
     9 · PC (`abreMenu()`), y la conexión con el PC o el VPS también vive allí.
     No queda nada que mostrar u ocultar hoja por hoja. */
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
  // El Centro se repinta al entrar: las herramientas y los ajustes pueden haber
  // cambiado (un APK nuevo trae métodos y el cajón se repinta con ellos).
  if (actual === 'centro') pintaCentro();
  // El Arnés también: lee el puente, la Charla y el núcleo en el momento de entrar,
  // que es cuando el estado del aparato importa.
  if (actual === 'arnes') pintaArnes();
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

/* El Centro de mando (F19): una sola lista con lo que CORT ya sabe hacer.
   `apps` es `visibles()` —la misma lista que ofrece el cajón—, así que el
   Centro nunca enseña una pantalla que este aparato no tiene. */
function pintaCentro() {
  const raiz = document.querySelector('#scr-centro .scr-cuerpo');
  if (!raiz) return 0;
  return montaCentro(raiz, { ir, apps: visibles() });
}

/* El Arnés (F23): no es una app nueva ni un chat; es el tablero de lo que ya
   sostiene a CORT —el puente de Java, el núcleo del portátil, la memoria, la
   conversación local y las 91 herramientas del diccionario—. Se le pasa `api`
   como función, no como texto: la dirección puede cambiar mientras la hoja está
   cerrada (Equipo ▸ 9 · PC), y el arnés la pide al entrar. */
function pintaArnes() {
  const raiz = document.querySelector('#scr-arnes .scr-cuerpo');
  if (!raiz) return null;
  return montaArnes(raiz, {
    ir,
    api: () => (ctx?.api ? ctx.api() : ''),
    pantallas: visibles(),
  });
}

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
let chPensando = false;           // burbuja de puntos mientras se espera la respuesta
let chForzarFondo = false;        // al enviar, sí se baja aunque estuviera leyendo arriba

function montaCharla() {
  const cuerpo = document.querySelector('#scr-charla .scr-cuerpo');
  if (!cuerpo) return;
  cuerpo.innerHTML = `
    <div class="gm-cab">
      <button class="lk-btn" id="gm-menu" title="Menú de CORT">☰</button>
      <b class="jm-titulo">CORT</b>
      <button class="gm-modelo" id="gm-modelo" title="Elegir modelo">
        <span id="gm-modelo-n">leyendo…</span><em>▾</em></button>
      <span class="jm-estado" id="jm-estado">conectando…</span>
      <span class="lk-espacio"></span>
      <button class="lk-btn jm-modos" id="jm-modos" title="Cómo responde">✦</button>
      <button class="lk-btn" id="gm-manto" title="El manto JARVIS: la charla sobre el orbe, como en la referencia">◐</button>
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
    <div class="jm-barra"><button class="jm-alto" id="jm-alto" hidden>■ parar</button></div>
    <div class="gm-pildora">
      <button class="gm-redondo" id="gm-adj" title="Adjuntar un documento o una nota">+</button>
      <textarea id="ch-entrada" rows="1" placeholder="Pregunta a CORT…"></textarea>
      <button class="gm-redondo" id="gm-mic" title="Dictar con el micrófono">🎙</button>
      <button class="gm-redondo enviar" id="ch-enviar" title="Enviar">▲</button>
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
    mensajes = []; chAdj = null; chPensando = false; guardaMensajes(); pintaCharla(); pintaAdjunto();
    ctx?.say?.('Conversación nueva. Lo que CORT recuerda del núcleo sigue ahí: pulsa ⟳ para traerlo.');
  };
  cuerpo.querySelector('#gm-recuerda').onclick = () => {
    traeHistorial(true);
    ctx?.say?.('Traigo lo que recuerda el núcleo.');
  };
  /* El manto JARVIS (paso 1.4): una capa de CSS sobre la charla de siempre. Se guarda
     en `localStorage` porque la dueña va a estar unos días comparando las dos caras, y
     lo que elija tiene que seguir ahí cuando cierre la app. */
  cuerpo.querySelector('#gm-manto').onclick = () => ponManto(!chManto);
  cuerpo.querySelector('#jm-modos').onclick = () =>
    document.getElementById('gm-modos').classList.toggle('abierto');
  // El «parar» del video: corta la ESPERA, no el pensamiento del modelo. Dice lo uno,
  // no lo otro, porque prometer un botón que apaga al cerebro sería mentir.
  cuerpo.querySelector('#jm-alto').onclick = charlaPara;
  aplicaManto();
  /* El punto de la cabecera dice lo que el aparato confirma, no lo que a una le
     gustaría ver: se pregunta una vez al montar (`hayNucleo` recuerda el resultado y
     `charla()` lo vuelve a comprobar si se cae el portátil a media respuesta). */
  hayNucleo().then(ok => jmEstado(ok ? 'conectado' : 'sin núcleo', !ok));
  cuerpo.querySelectorAll('#gm-saludo [data-s]').forEach(b => b.onclick = () => {
    entrada.value = CH_SUGERENCIAS[+b.dataset.s];
    charla(entrada.value);
  });
  cargaMensajes();
}

/* ───────────────────  EL MANTO JARVIS (paso 1.4 de la Fase 1) ───────────────────
 *
 * La dueña, 26/10: «empiezas por el chat, se tiene que parecer al del video… la
 * pantalla será semi negra transparente estilo la interfaz del JARVIS».
 *
 * Lo que hace esto, y lo que NO hace:
 *  · Es una **clase en `<html>`** (`manto-jarvis`) y un archivo de CSS
 *    (`css/jarvis.css`). No se reescribió la Charla: la misma hoja, los mismos
 *    botones, el mismo `/api/chat`, el mismo puente `mente()` del teléfono. Se quita
 *    la clase y la cara vuelve a ser la de siempre.
 *  · NO es la «superficie chat única» del plan (`docs/PLAN-CHAT-UNICO.md`): ésa
 *    todavía no se monta porque hay cinco decisiones suyas sin responder (la barra de
 *    tres, si Música sigue aparte, el fondo, el motor en el APK y por dónde empezar).
 *  · El orbe de atrás cuesta: `hud.js` congela el WebGL fuera de su pantalla para no
 *    comerse los 1,8 GiB ni la batería del teléfono. Con el manto puesto se le dice
 *    que lo deje vivo en la charla, y con el manto quitado vuelve a congelarse.
 *
 * Se guarda en `localStorage` porque la dueña va a estar días comparando las dos
 * caras; lo que elija tiene que seguir ahí cuando cierre la app.
 */
const CLAVE_MANTO = 'cort-manto';
let chManto = true;
try { chManto = localStorage.getItem(CLAVE_MANTO) !== 'viejo'; } catch { chManto = true; }

/* «Respuestas semi cortas pero medidas», dicho por ella el 26/10 sobre la charla de
   conversación. Va DELANTE de la pregunta porque `POST /api/chat` sólo acepta
   `{message}`: no hay campo de instrucciones en el backend (lo dice el comentario de
   `CH_MODOS`). Con un modo elegido (Explícame, Resume…) manda el modo: no se
   pisan. Y el candado de «no inventes» está dentro de la propia frase. */
const FRASE_JARVIS = 'Responde en dos frases, tres como mucho, sin preámbulos y sin '
  + 'repetirme la pregunta. Si te falta un dato para responder bien, di en una frase '
  + 'qué te falta en vez de inventarlo.';

const mantoActivo = () => chManto;

/** Pone o quita el manto, y se lo dice a `hud.js` para que sepa si el orbe va detrás. */
function ponManto(on) {
  chManto = !!on;
  try { localStorage.setItem(CLAVE_MANTO, chManto ? 'jarvis' : 'viejo'); } catch { /* sin almacenamiento */ }
  aplicaManto();
  window.dispatchEvent(new CustomEvent('cort-manto', { detail: chManto }));
}

function aplicaManto() {
  document.documentElement.classList.toggle('manto-jarvis', chManto);
  const b = document.getElementById('gm-manto');
  if (b) {
    b.setAttribute('aria-pressed', String(chManto));
    b.title = chManto ? 'Manto JARVIS puesto · quítalo para volver a la cara de siempre'
                      : 'Manto JARVIS quitado · póntelo para charlar sobre el orbe';
  }
  // Con el manto quitado los chips de modo vuelven a su fila: si estaba abierto, se cierra.
  const m = document.getElementById('gm-modos');
  if (m && !chManto) m.classList.remove('abierto');
}

/** El estado de la cabecera. Escribe las DOS barras: la genérica (`.scr-estado`, que
 *  `apps.css` esconde en esta hoja) y la del manto, para que el texto no dependa de
 *  qué cara esté puesta. */
function jmEstado(texto, aviso) {
  const g = document.querySelector('#scr-charla .scr-estado');
  if (g) { g.textContent = texto; g.classList.toggle('aviso', !!aviso); }
  const j = document.getElementById('jm-estado');
  if (j) { j.textContent = texto; j.classList.toggle('aviso', !!aviso); }
}

/** El botón «parar» de la referencia: corta la ESPERA de la pantalla, no el pensamiento
 *  del modelo (eso no se puede, y decirlo cuesta menos que fingir un botón que manda).
 *  Si la respuesta llega después, llega y se pinta: no se tira a la basura. */
function charlaPara() {
  if (!chPensando) return;
  chPensando = false;
  chCortada = true;
  jmEstado('espera cortada', true);
  // La píldora la escribe `pintaUsandoCharla`, que ya sabe que se cortó: escrita a
  // mano aquí, la pintura de abajo la volvería a su texto de siempre (y así pasaba).
  guardaMensajes(); pintaCharla();
}

/* Los chips de modo, con el activo teñido del acento de la app. */
function pintaModosCharla() {  const caja = document.getElementById('gm-modos');
  if (!caja) return;
  caja.innerHTML = CH_MODOS.map(m => `<button class="gm-modo${m.id === chModo ? ' activa' : ''}"
    data-m="${m.id}" title="${esc(m.pide || 'sin instrucción añadida')}">
    <i>${m.ic}</i>${esc(m.txt)}</button>`).join('');
  caja.querySelectorAll('[data-m]').forEach(b => b.onclick = () => {
    chModo = b.dataset.m;
    pintaModosCharla();
    pintaUsandoCharla();
    if (chManto) caja.classList.remove('abierto');   // con el manto los chips son un desplegable
  });
}

/* La línea de abajo: modelo, modo y adjunto. Se dice aquí en vez de esconderse en
   un menú porque la dueña tiene que saber QUÉ se le está mandando al modelo. */
/* La píldora de abajo dice con qué se está pensando, y se lee SIEMPRE aquí. Es el único
   sitio del archivo que escribe `#gm-usando`: cada vez que hubo una segunda escritura a
   mano —en el envío, en el «sin núcleo», en la respuesta del teléfono— hubo una carrera
   contra `pintaCharla`, que llamaba a esta función justo después y dejaba pintado
   «usando el modelo del núcleo» encima de una burbuja que decía «el núcleo de CORT no
   responde». Dos fuentes de verdad para una sola línea. Ahora la línea sale del final de
   la conversación: `chPensando`, `chCortada`, y la `nota` que cada respuesta de CORT
   lleva encima desde que se escribió. */
let chCortada = false;

function pintaUsandoCharla() {
  const linea = document.getElementById('gm-usando');
  if (!linea) return;
  const modo = CH_MODOS.find(m => m.id === chModo) || CH_MODOS[0];
  const ultimo = mensajes[mensajes.length - 1];
  const partes = [];
  /* Mientras se espera no se dice un modelo: se dice que se espera. La respuesta que
     entra por `charla()` o por el puente es la que trae la verdad, y al llegar pinta su
     propia `nota`. El adjunto se lee del mensaje enviado, no de `chAdj`, que ya está
     vacío desde que la pregunta salió. */
  if (chPensando) partes.push(ultimo?.nota || 'pensando…', 'modo ' + modo.txt, ultimo?.adj && '📎 ' + ultimo.adj);
  /* La cortada se apaga sola cuando el cerebro termina contestando: basta con mirar el
     final de la conversación. Si lo último es una pregunta, nadie respondió y hay que
     decirlo; si ya entró la respuesta —aunque llegara DESPUÉS de que ella parara, que es
     justo lo que la píldora promete—, la línea vuelve a decir con qué se pensó. Atarlo
     sólo a la bandera fue el fallo: pintaba «nadie contestó» encima de una respuesta que
     estaba ahí abajo, en la pantalla (cazado con captura, no leyendo el código). */
  else if (chCortada && ultimo && ultimo.de === 'tu') partes.push('espera cortada', 'nadie contestó a esa pregunta');
  else if (ultimo?.de === 'cort' && ultimo.nota) partes.push(ultimo.nota, 'modo ' + modo.txt);
  else partes.push('usando ' + (chModelo || 'el modelo del núcleo'), 'modo ' + modo.txt);
  if (chAdj) partes.push('adjunto ' + chAdj.nombre);
  linea.innerHTML = partes.filter(Boolean).map((p, i) => i === 0 ? `<b>${esc(p)}</b>` : esc(p)).join(' · ');
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
  // Con el manto JARVIS puesto y sin modo elegido, la respuesta sale semi-corta y
  // medida (lo que ella pidió para la charla de conversación). Si ella eligió un modo,
  // manda su instrucción: las dos no se pisan.
  const jarvis = chManto && modo.id === 'normal' ? FRASE_JARVIS : '';
  // El adjunto va DENTRO del mensaje: `POST /api/chat` sólo acepta `{message}`, así
  // que no hay campo donde poner un archivo. Se manda el texto leído y se dice cuál.
  const envio = [jarvis, modo.pide, chAdj
      ? '[Adjunto: ' + (chAdj.ruta || chAdj.nombre) + ']\n' + chAdj.texto : '', pregunta]
    .filter(Boolean).join('\n\n');
  mensajes.push({ de: 'tu', texto: pregunta, modo: modo.id, adj: chAdj ? chAdj.nombre : '',
                  hora: Date.now() });
  chAdj = null;
  pintaAdjunto();
  chPensando = true;
  chCortada = false;          // pregunta nueva: lo cortado antes ya no cuenta
  chForzarFondo = true;
  pintaCharla(true);          // `true`: lo único nuevo es la burbuja que acaba de entrar
  const estado = document.querySelector('#scr-charla .scr-estado');
  jmEstado('pensando…');
  const hay = await avisaSinNucleo(estado);
  /* `avisaSinNucleo` escribe en la barra genérica; con el manto la barra visible es
     otra, así que se copia lo que escribió en vez de decir un estado distinto en cada
     cara. Dos maneras de decir lo mismo confunden más que una sola. */
  jmEstado(String(estado?.textContent || ''), estado?.classList.contains('aviso'));
  if (!hay) {
    /* «Charla con IA… microfono no funciona chat tampoco», dicho el 22/10 con el
       2.6.0-nucleo delante. Aquí se acababa la conversación: la hoja pedía
       `/api/chat` y sin portátil contestaba con una frase de disculpa. Pero el
       teléfono NO está tonto: Java tiene `mente()`, que contesta con Groq si el
       perfil tiene clave, y con sus reglas locales si no. Se le manda la misma
       pregunta y la respuesta llega por el puente (`escuchaMente`), como llega todo
       lo largo que hace el aparato. Con un APK sin puente, se dice la verdad. */
    if (puede('mente')) {
      const bruto = llama('mente', JSON.stringify({ que: 'preguntar',
        args: { texto: envio, eco: 'charla' } }));
      let j = null;
      // `llama` ya trapsa el `catch`, pero un puente que devuelva texto suelto no es
      // una respuesta: es un `JSON.parse` tirando la promesa de la Charla al vacío.
      try { j = typeof bruto === 'string' ? JSON.parse(bruto) : bruto; } catch { j = null; }
      if (j && j.ok !== false) {
        charlaPendiente = true;
        /* Se le pone la nota a la PREGUNTA: mientras se espera, la píldora dice dónde se
           está pensando, y la dice desde el mismo sitio que pinta la burbuja. `usando`
           ya no se escribe a mano en ningún camino. */
        const preguntaDicha = mensajes[mensajes.length - 1];
        preguntaDicha.nota = 'el cerebro del teléfono';
        pintaUsandoCharla();
        jmEstado('pensando en el teléfono…');
        if (j && !j.pendiente) reciboMente(j);      // contestó en el sitio: nada que esperar
        return;
      }
    }
    mensajes.push({ de: 'cort', texto: sinNucleoFrase(), nota: 'sin núcleo', hora: Date.now() });
    chPensando = false;
    jmEstado('sin núcleo', true);
    guardaMensajes(); pintaCharla(true); return;
  }
  try {
    const r = await fetch(ctx.api() + '/api/chat', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ message: envio }),
    });
    const j = await r.json();
    const dicho = j.reply || j.error || 'No supe qué contestar.';
    /* La nota dice lo que el aparato confirmó: con qué modelo y desde dónde. Si el
       núcleo no devolvió `source`, se dice `local` en vez de inventarse la nube. */
    mensajes.push({ de: 'cort', texto: dicho, fuente: j.source || '',
                    nota: (chModelo || 'el modelo del núcleo') + ' · cerebro ' + (j.source || 'local'),
                    hora: Date.now() });
    chPensando = false;
    jmEstado('cerebro: ' + (j.source || 'local'));
    ctx?.orb?.burst?.();
  } catch (e) {
    mensajes.push({ de: 'cort', texto: 'El núcleo se cayó a media respuesta: ' + e,
                    nota: 'el núcleo se cayó', hora: Date.now() });
    chPensando = false;
    jmEstado('sin núcleo', true);
    // El portátil dejó de responder: el «sí hay» que estaba guardado es mentira. Se
    // borra para que la siguiente pregunta se vuelva a comprobar, y si el PC no
    // vuelve, esa pregunta ya se piensa en el teléfono.
    nucleo = null;
  }
  guardaMensajes(); pintaCharla(true);
}

/* ── la Charla sin portátil: la respuesta llega por el puente ────────────────
   `Mente.mente({que:'preguntar'})` contesta `{"ok":true,"pendiente":true}` al instante
   y lanza el hilo `cort-mente`; cuando termina, Java empuja `{"type":"mente", …}` por
   `__cortNative`. Esta hoja no puede quedarse sorda a ese aviso sólo porque el Equipo
   lo escuche: la dueña preguntó en la Charla, en la Charla quiere la respuesta.

   Se filtra `de:'ollama'` porque ese mismo evento trae la lista de modelos y el
   progreso de una descarga, y no es una respuesta de nadie. `charlaPendiente` hace el
   resto: si la dueña no está esperando, el aviso se ignora y no se pinta una burbuja
   que no se pidió. */
let charlaPendiente = false;

function reciboMente(ev) {
  charlaPendiente = false;
  const dicho = ev.ok === false
    ? (ev.dice || 'El cerebro del teléfono no supo contestar.')
    : (ev.responde || ev.texto || 'Ya pensé lo mío, pero no volvió texto.');
  const de = ev.de === 'local' || ev.de === 'nube' ? ev.de : '';
  chPensando = false;
  chCortada = false;          // contestó: la píldora vuelve a decir con qué se pensó
  mensajes.push({ de: 'cort', texto: String(dicho), fuente: de,
                  nota: 'cerebro del teléfono' + (de ? ' · ' + de : ''), hora: Date.now() });
  const estado = document.querySelector('#scr-charla .scr-estado');
  if (estado) estado.textContent = 'cerebro del teléfono' + (de ? ': ' + de : '');
  jmEstado('cerebro del teléfono' + (de ? ': ' + de : ''));
  ctx?.orb?.burst?.();
  guardaMensajes(); pintaCharla(true);
}

let menteViva = false;
function escuchaMente() {
  if (menteViva || !window.__cortNative) return;
  menteViva = true;
  window.__cortNative.on(ev => {
    if (!ev || ev.type !== 'mente' || ev.de === 'ollama') return;
    if (!charlaPendiente) return;
    reciboMente(ev);
  });
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
                   texto: String(x.texto || ''), fuente: x.fuente || '',
                   hora: x.fecha ? (Date.parse(x.fecha) || 0) : 0 }));
    if (!mensajes.length) return;
    chPensando = false;
    guardaMensajes(); pintaCharla();
  } catch { /* sin núcleo o sin respuesta: la hoja queda como estaba */ }
}

/* Cuántas burbujas de `mensajes` hay colgadas ahora mismo. Con este número se decide
   si la charla se puede **añadir** o hay que rehacerla (aceptación del paso 1.4: «la
   hoja no re-renderiza todo el historial por mensaje»). */
let chPintadas = 0;

function pintaCharla(nuevo) {
  const caja = document.getElementById('ch-msgs');
  if (!caja) return;
  // El saludo de Gemini con sus sugerencias sólo mientras no hay conversación: en
  // cuanto se pregunta, la pantalla es para las respuestas.
  const saludo = document.getElementById('gm-saludo');
  if (saludo) saludo.hidden = mensajes.length > 0;
  // Como OpenJarvis: si la dueña está leyendo más arriba, una respuesta nueva no le
  // arranca la lectura. Sólo se baja si ya estaba abajo, o si acaba de enviar ella.
  const cerca = caja.scrollHeight - caja.scrollTop - caja.clientHeight < 90;
  /* Se añade la burbuja nueva y se deja el resto en su sitio SÓLO si es verdad que lo
     único que cambió fue el final: quien llama pasa `nuevo` justo después de su
     `mensajes.push`, y aquí se comprueba que la caja tiene exactamente las de antes.
     Cualquier otra cosa —borrar, traer el historial del núcleo, cambiar un modo— cae al
     reconstruido completo, que es más caro pero nunca se queda enseñando una mezcla. */
  const colgadas = caja.querySelectorAll('.burbuja:not(.gm-pensando)').length;
  if (!(nuevo && chPintadas === mensajes.length - 1 && colgadas === chPintadas)) {
    caja.innerHTML = '';
    mensajes.forEach((m, i) => caja.appendChild(burbujaCharla(m, i)));
  } else {
    caja.appendChild(burbujaCharla(mensajes[mensajes.length - 1], mensajes.length - 1));
  }
  chPintadas = mensajes.length;
  // La de «pensando» es una señal, no un mensaje: se pone y se quita sin tocar las demás.
  const pensando = caja.querySelector('.gm-pensando');
  if (chPensando && !pensando) caja.appendChild(burbujaPensando());
  if (!chPensando && pensando) pensando.remove();
  if (chForzarFondo || cerca) caja.scrollTop = caja.scrollHeight;
  chForzarFondo = false;
  pintaUsandoCharla();
  // El «parar» del manto sólo existe mientras se espera: un botón que no tiene nada
  // que cortar es ruido (y la dueña lo tocaría para averiguarlo).
  const alto = document.getElementById('jm-alto');
  if (alto) alto.hidden = !chPensando;
}

/* Una burbuja con su cara, su nombre y —en las de CORT— copiar, leer y guardar.
   El dibujo sigue la estructura de OpenJarvis (avatar, cabecera, acciones por
   mensaje), pero sin dependencias ni Markdown completo: `md()` sólo reconoce lo que
   un cerebro suele devolver —código, negritas, enlaces— y escapa TODO lo demás. */
function burbujaCharla(m, i) {
  const b = document.createElement('div');
  const mio = m.de === 'tu';
  b.className = 'burbuja ' + (mio ? 'de-tu' : 'de-cort');
  b.dataset.i = i;
  const pies = [];
  if (m.fuente) pies.push(`<span class="bur-fuente">${esc(m.fuente)}</span>`);
  if (m.modo && m.modo !== 'normal') {
    const mo = CH_MODOS.find(x => x.id === m.modo);
    pies.push(`<span class="bur-modo">${mo ? esc(mo.ic + ' ' + mo.txt) : esc(m.modo)}</span>`);
  }
  if (m.adj) pies.push(`<span class="bur-adj">📎 ${esc(m.adj)}</span>`);
  const cuando = horaDe(m.hora);
  const acciones = mio
    ? '<button class="bur-accion" data-a="copiar" title="Copiar mi pregunta">copiar</button>'
    : `<button class="bur-accion" data-a="copiar" title="Copiar esta respuesta">copiar</button>
       <button class="bur-accion" data-a="leer" title="Leerla en voz alta">leer</button>
       <button class="bur-accion" data-a="nota" title="Guardarla en 04 · Notas">nota</button>`;
  const avatar = mio ? '<span class="bur-avatar tu" aria-hidden="true">T</span>' : '';
  const avatarCort = mio ? '' : '<span class="bur-avatar" aria-hidden="true">C</span>';
  /* Con el manto JARVIS la respuesta va SIN caja y sin sus botones a la vista (así se
     ve en la referencia). Un toque sobre el mensaje los trae: esconderlos sin más sería
     quitarle a la dueña el copiar / leer / nota que ya tenía. Vale para las dos caras:
     la pastilla tuya también llevaba su «copiar» escrito. */
  b.onclick = () => b.classList.toggle('tocada');  b.innerHTML = `${mio ? '' : avatarCort}
    <div class="bur-cuerpo">
      <div class="bur-cab"><b>${mio ? 'Tú' : 'CORT'}</b>${cuando ? `<span>${cuando}</span>` : ''}${pies.join('')}</div>
      <div class="bur-texto">${md(m.texto)}</div>
      <div class="bur-acciones">${acciones}</div>
    </div>${avatar}`;
  b.querySelectorAll('.bur-accion').forEach(x => x.onclick = () => {    if (x.dataset.a === 'copiar') return copia(m.texto, 'Copiado.');
    if (x.dataset.a === 'leer') {
      if (typeof ctx?.speak !== 'function') return ctx?.say?.('La voz no está disponible aquí.');
      ctx.speak(m.texto);
      return;
    }
    if (x.dataset.a === 'nota') guardaNota(m.texto);
  });
  return b;
}

/* Los tres puntos de OpenJarvis: la espera se VE, en vez de dejar la pantalla muda. */
function burbujaPensando() {
  const b = document.createElement('div');
  b.className = 'burbuja de-cort gm-pensando';
  b.innerHTML = `<span class="bur-avatar" aria-hidden="true">C</span>
    <div class="bur-cuerpo">
      <div class="bur-cab"><b>CORT</b><span>pensando</span></div>
      <div class="gm-puntos" role="status" aria-label="pensando"><i></i><i></i><i></i></div>
    </div>`;
  return b;
}

function horaDe(ms) {
  const n = Number(ms);
  if (!Number.isFinite(n) || n <= 0) return '';
  try { return new Date(n).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' }); }
  catch { return ''; }
}

/* Markdown mínimo y seguro: primero se escapa TODO, después se reconocen los bloques
   de código, el código en línea, las negritas y los enlaces. Así una respuesta con
   `<script>` se lee como texto y nunca se ejecuta. */
function md(texto) {
  const trozos = [];
  let s = esc(String(texto == null ? '' : texto));
  s = s.replace(/```([^\n`]*)\n?([\s\S]*?)```/g, (_, lengua, codigo) => {
    trozos.push('<pre class="bur-pre"><code>' + codigo.replace(/\n+$/, '') + '</code></pre>');
    return '\u0001' + (trozos.length - 1) + '\u0001';
  });
  s = s.replace(/`([^`\n]+)`/g, '<code class="bur-code">$1</code>');
  s = s.replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>');
  s = s.replace(/(^|[\s(])(https?:\/\/[^\s<)]+)/g,
    '$1<a href="$2" target="_blank" rel="noopener">$2</a>');
  s = s.replace(/\n/g, '<br>');
  return s.replace(/\u0001(\d+)\u0001/g, (_, i) => trozos[+i] || '');
}

async function guardaNota(texto) {
  if (!ctx?.api) return ctx?.say?.('Sin núcleo no hay dónde guardar la nota.');
  try {
    const r = await fetch(ctx.api() + '/api/notes', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ texto: '[charla] ' + texto }),
    });
    ctx?.say?.(r.ok ? 'Anotado en 04 · Notas.' : 'El núcleo no dejó guardar la nota.');
  } catch { ctx?.say?.('El núcleo no respondió.'); }
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
 * Entorno de programación, terminal y **copiloto**. Dicho sin adornos y sin prometer
 * lo que Android no deja: **quien ejecuta es el PC**, porque dentro de una APK una app
 * normal no puede abrir una shell ni instalar paquetes (sandbox). Lo que hay aquí es
 * el terminal real del equipo (por `/api/command` y su ejecutor de acciones), un
 * cuaderno de código —escribes o pegas, pides que lo arregle, y lo guardas— y el modo
 * copiloto de F11: describes el objetivo, CORT piensa los comandos y ejecuta sólo los
 * que no pueden romper nada (`backend/app/copiloto.py`), dejando escritos los demás.
 */
const CLAVE_CODIGO = 'cort-codigo';
const CLAVE_COPILOTO = 'cort-copiloto';

/* ─────────────── el modo copiloto (F11 · el punto 4 de su lista) ───────────────
 * «CORT debe guiarte como copiloto y ejecutar los comandos él solo». La cara de
 * ese acuerdo es esta: escribes un OBJETIVO («cómo está el equipo», «qué ocupa
 * espacio») y CORT devuelve los PASOS con el comando exacto de cada uno. Cada paso
 * trae su ▶, y el ▶ sólo está encendido si el comando es de **sólo lectura** — el
 * veredicto no lo decide esta hoja, lo decide `backend/app/copiloto.py` con sus
 * tres listas (`LEE_SOLO`, `SUB_LECTURA`, `NUNCA`) y lo vuelve a comprobar en el
 * momento de ejecutar. Lo que escribe, borra o instalar se muestra con su motivo y
 * un botón de copiar: queda en tus manos, no en las de CORT.
 * Con el modo apagado la terminal sigue siendo la de siempre (`/api/command`), y
 * con el modo encendido se puede hacer una pausa del copiloto prefijando `> `.
 */
const copiloto = {
  activo: false, token: '', pasos: [], recetas: [], ocupado: false,
};
try { copiloto.activo = localStorage.getItem(CLAVE_COPILOTO) === '1'; } catch { /* sin localStorage */ }

function guardaCopiloto() {
  try { localStorage.setItem(CLAVE_COPILOTO, copiloto.activo ? '1' : '0'); } catch { /* nada */ }
}

/* Las sugerencias salen del propio backend (`recetas`), no escritas a mano aquí:
   si un día cambia una plantilla, la cara dice lo que de verdad sabe hacer. */
async function copilotoArranca() {
  const base = await hayNucleo();
  if (!base) return;
  if (copiloto.recetas.length) { pintaCopilotoChips(); return; }
  try {
    const r = await fetch(base + '/api/copiloto', { signal: AbortSignal.timeout(4000) });
    const j = await r.json();
    copiloto.recetas = Array.isArray(j.recetas) ? j.recetas : [];
    pintaCopilotoChips();
  } catch { /* sin catálogo: los chips simplemente no aparecen */ }
}

function pintaCopilotoChips() {
  const caja = document.getElementById('cod-cop-chips');
  if (!caja) return;
  if (!copiloto.activo) { caja.innerHTML = ''; return; }
  if (!copiloto.recetas.length) {
    caja.innerHTML = '<span class="cp-nota">pide el plan con tus palabras: «cómo está el equipo», '
      + '«qué ocupa espacio», «qué tengo instalado»…</span>';
    return;
  }
  caja.innerHTML = copiloto.recetas.map(t => '<button class="eq-chip" data-obj="'
    + esc(t) + '">' + esc(t) + '</button>').join('');
  caja.querySelectorAll('[data-obj]').forEach(b => {
    b.onclick = () => {
      const e = document.getElementById('cod-entrada');
      if (e) e.value = b.dataset.obj;
      codigo(b.dataset.obj);
    };
  });
}

async function copilotoPlan(objetivo) {
  const base = await hayNucleo();
  if (!base) {
    escribeCodigo(sinNucleoFrase(), 'aviso');
    return false;
  }
  copiloto.ocupado = true; pintaCopiloto();
  try {
    const r = await fetch(base + '/api/copiloto/plan', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ objetivo }), signal: AbortSignal.timeout(30000),
    });
    const j = await r.json();
    if (!j.ok) {
      copiloto.token = ''; copiloto.pasos = [];
      escribeCodigo(j.dice || 'no pudo hacer un plan', 'aviso');
      return false;
    }
    copiloto.token = j.token || '';
    copiloto.pasos = j.pasos || [];
    escribeCodigo('plan (' + (j.origen || 'pasos') + '): ' + (j.dice || ''), 'hecho');
    return true;
  } catch (e) {
    escribeCodigo('el copiloto no respondió: ' + e, 'aviso');
    return false;
  } finally { copiloto.ocupado = false; pintaCopiloto(); }
}

async function copilotoEjecuta(indice) {
  const base = await hayNucleo();
  if (!base || !copiloto.token) return;
  const paso = (copiloto.pasos || [])[indice];
  if (!paso) return;
  paso.resultado = null; paso.cargando = true; pintaCopiloto();
  try {
    const r = await fetch(base + '/api/copiloto/ejecuta', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ token: copiloto.token, indice }),
      signal: AbortSignal.timeout(35000),
    });
    const j = await r.json();
    paso.resultado = j;
    escribeCodigo('▶ ' + paso.orden + ' — ' + (j.dice || ''), j.ejecutado && j.ok ? 'hecho' : 'aviso');
    if (j.salida) String(j.salida).split('\n').slice(0, 30)
      .forEach(l => escribeCodigo('  ' + l, 'cort'));
  } catch (e) {
    paso.resultado = { ok: false, ejecutado: false, dice: 'no respondió: ' + e };
    escribeCodigo('▶ ' + paso.orden + ' — el copiloto no respondió: ' + e, 'aviso');
  } finally { paso.cargando = false; pintaCopiloto(); }
}

/* Ejecuta en fila los pasos que el backend marcó como seguros, uno detrás de otro.
   Se para si uno falla de verdad: un copiloto que sigue andando después de un error
   no está guiando, está acumulando basura. */
async function copilotoEjecutaSeguros() {
  const seguros = copiloto.pasos.filter(p => p.seguro);
  for (const p of seguros) {
    await copilotoEjecuta(p.indice);
    if (p.resultado && p.resultado.ejecutado && !p.resultado.ok) {
      escribeCodigo('me paro aquí: el resto lo miras tú (' + (p.resultado.dice || '') + ')', 'aviso');
      break;
    }
  }
}

function pintaCopiloto() {
  const caja = document.getElementById('cod-cop-plan');
  if (!caja) return;
  if (!copiloto.activo) { caja.innerHTML = ''; return; }
  if (!copiloto.pasos.length) {
    caja.innerHTML = copiloto.ocupado ? '<div class="cp-nota">pensando los pasos…</div>' : '';
    return;
  }
  const seguros = copiloto.pasos.filter(p => p.seguro).length;
  caja.innerHTML = '<div class="cp-pie"><span class="cp-nota">'
    + copiloto.pasos.length + ' pasos · ' + seguros + ' se ejecutan solos · '
    + (copiloto.pasos.length - seguros) + ' sólo se enseñan</span>'
    + '<button class="eq-b" id="cp-todos"' + (seguros && !copiloto.ocupado ? '' : ' disabled')
    + '>▶ ejecuta los ' + seguros + ' seguros</button>'
    + '<button class="eq-b" id="cp-cierra">cerrar el plan</button></div>'
    + copiloto.pasos.map(p => {
      const res = p.resultado || {};
      return '<div class="cp-paso' + (p.seguro ? '' : ' malo') + '">'
        + '<div class="cp-cabe"><span class="cp-tit">' + esc(p.paso || ('paso ' + (p.indice + 1)))
        + '</span><button class="cp-b" data-copia="' + p.indice + '">copiar</button>'
        + (p.seguro ? '<button class="cp-b puesta" data-ejecuta="' + p.indice + '"'
          + (copiloto.ocupado ? ' disabled' : '') + '>' + (p.cargando ? '…' : '▶') + '</button>'
          : '<button class="cp-b" disabled>▶ no</button>')
        + '</div><div class="cp-orden">' + esc(p.orden || '') + '</div>'
        + (p.seguro ? '' : '<div class="cp-motivo">' + esc(p.motivo || 'no es de sólo lectura') + '</div>')
        + (p.permitido_por_ella ? '<div class="cp-nota">permitido por ti en copiloto.json</div>' : '')
        + (res.dice ? '<div class="cp-nota">' + esc(res.dice) + '</div>' : '')
        + (res.salida ? '<div class="cp-salida">' + esc(res.salida) + '</div>' : '')
        + '</div>';
    }).join('');
  caja.querySelectorAll('[data-ejecuta]').forEach(b => {
    b.onclick = () => copilotoEjecuta(Number(b.dataset.ejecuta));
  });
  caja.querySelectorAll('[data-copia]').forEach(b => {
    b.onclick = () => copia((copiloto.pasos[Number(b.dataset.copia)] || {}).orden || '', 'Comando copiado.');
  });
  const todos = caja.querySelector('#cp-todos');
  if (todos) todos.onclick = () => copilotoEjecutaSeguros();
  const cerrar = caja.querySelector('#cp-cierra');
  if (cerrar) cerrar.onclick = () => { copiloto.pasos = []; copiloto.token = ''; pintaCopiloto(); };
}


function montaCodigo() {
  const cuerpo = document.querySelector('#scr-codigo .scr-cuerpo');
  let guardado = '';
  try { guardado = localStorage.getItem(CLAVE_CODIGO) || ''; } catch { /* nada */ }
  cuerpo.innerHTML = `
    <div class="scr-lista cod-out" id="cod-out"></div>
    <label class="cp-cab">
      <input type="checkbox" id="cod-cop-on" ${copiloto.activo ? 'checked' : ''}>
      <b>modo copiloto</b>
      <small>piensa los comandos y ejecuta solo los de sólo lectura; lo que escribe o
      borra se queda escrito para que lo copies</small>
    </label>
    <div class="cp-chips" id="cod-cop-chips"></div>
    <div class="cp-plan" id="cod-cop-plan"></div>
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

  /* El interruptor del copiloto: cambia la pista de la línea, enseña las sugerencias
     que el backend de verdad sabe hacer y se recuerda en localStorage. */
  const interruptor = cuerpo.querySelector('#cod-cop-on');
  interruptor.onchange = () => {
    copiloto.activo = !!interruptor.checked;
    guardaCopiloto();
    pistaCopiloto(entrada);
    if (copiloto.activo) { copilotoArranca(); } else { copiloto.pasos = []; copiloto.token = ''; }
    pintaCopilotoChips(); pintaCopiloto();
    ctx?.say?.(copiloto.activo ? 'Modo copiloto: dime qué quieres averiguar y te digo los comandos.'
      : 'Modo copiloto apagado: la terminal es la de siempre.');
  };
  pistaCopiloto(entrada);
  pintaCopilotoChips(); pintaCopiloto();
  if (copiloto.activo) copilotoArranca();
}

/* La pista de la línea dice qué se espera escribir: un OBJETIVO con el copiloto
   encendido, la orden de siempre con él apagado. Prefijar `> ` salta el copiloto. */
function pistaCopiloto(entrada) {
  if (!entrada) return;
  entrada.placeholder = copiloto.activo
    ?' un objetivo: «cómo está el equipo», «qué ocupa espacio»… ( > para la orden de siempre)'
    :' Instala, arregla, actualiza… (escribe y Enter)';
}

const HISTORIAL_CODIGO = [];
async function codigo(texto) {
  const linea = String(texto || '').trim();
  if (!linea) return;
  const entrada = document.getElementById('cod-entrada');
  if (entrada) entrada.value = '';
  /* `> ` al principio salta el copiloto: es la salida de emergencia para pedir la
     orden de siempre («> reproduce música») sin apagar el interruptor. */
  const saltoCopiloto = /^>/.test(linea);
  const orden = linea.replace(/^>\s*/, '');
  if (!orden) return;
  HISTORIAL_CODIGO.push(orden);
  escribeCodigo('$ ' + orden, 'orden');
  const estado = document.querySelector('#scr-codigo .scr-estado');

  /* ── el copiloto (F11) ──
     Con el modo encendido, la línea se lee como un OBJETIVO y no como un comando:
     el plan lo hace el backend y aquí sólo se pintan los pasos y su ▶. En el
     teléfono, si no hay portátil localizado, el objetivo se contesta con el cerebro
     del teléfono — mejor eso que dejar la línea muerta. */
  if (copiloto.activo && !saltoCopiloto) {
    if (enTelefono() && terminalTelefono(orden, escribeCodigo)) return;
    const base = await hayNucleo();
    if (base) { await copilotoPlan(orden); return; }
    escribeCodigo('sin tu portátil no hay comandos que mirar: el copiloto trabaja sobre el PC. '
      + 'Esto lo contesto yo.', 'aviso');
  }

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
    escribeCodigo('¿Prefieres que te lo piense yo? Enciende el «modo copiloto» de arriba y escribe un '
      + 'objetivo («cómo está el equipo», «qué ocupa espacio»): CORT te enseña los comandos y ejecuta '
      + 'sólo los que no pueden romper nada.', 'hecho');
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

   Lo que Lark tiene y CORT **no** puede copiar porque el puente no lo da: ecualizador,
   carpetas y cola de reproducción. No se pintan falsos. La carátula, en cambio, ya es
   de verdad: `musicaCaratula` devuelve un `data:image/jpeg;base64,…` y este cuadro lo
   lleva como fondo; sin carátula se queda el glifo y el acento de la app, que es la
   verdad de esa pista. */
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
    <div class="lk-pastillas lk-modos-musica">
      <button id="${p}-aleatorio" class="mu-chip" title="barajar el resto de la cola sin perder la que suena">⇄ aleatorio</button>
      <button id="${p}-repetir" class="mu-chip" title="sin repetir · repetir la cola · repetir esta pista">↻ repetir todo</button>
      <button id="${p}-fuera" class="mu-chip" title="abrir esta pista en VLC, Lark o el reproductor de tu teléfono">▶ en mi reproductor</button>
    </div>
    <div class="lk-aviso" id="${p}-nota" role="status"></div>
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
      <button id="${p}-letras" title="la letra y el vídeo, dentro de Música"><i>❝</i><span>letra</span></button>
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
  // F20 · los tres modos que antes no existían: se dicen en voz alta y se pintan
  // desde el estado real de Java, no desde un interruptor de la cara que se separa.
  $('aleatorio').onclick = () => {
    if (!puede('musicaAleatorio')) return ctx?.say?.('El aleatorio nuevo lo trae el APK de la Release.');
    const r = llama('musicaAleatorio');
    ctx?.say?.(r || 'aleatorio cambiado');
    pintaProgreso(estadoMusica());
  };
  $('repetir').onclick = () => {
    if (!puede('musicaRepetir')) return ctx?.say?.('Los modos de repetir los trae el APK de la Release.');
    const r = llama('musicaRepetir');
    ctx?.say?.(r || 'repetición cambiada');
    pintaProgreso(estadoMusica());
  };
  $('fuera').onclick = () => {
    if (!puede('musicaExterna')) return ctx?.say?.('Abrir en tu reproductor lo trae el APK de la Release.');
    const crudo = llama('musicaExterna');
    let j = null; try { j = crudo ? JSON.parse(crudo) : null; } catch { j = null; }
    ctx?.say?.(j?.dice || 'El teléfono no respondió a lo de abrir tu reproductor.');
  };
  // «Letra» es el botón `❝` de Lark, que en su reproductor sube el panel del karaoke:
  // aquí es la hoja fusionada, y volver de ella es volver al reproductor.
  $('letras').onclick = () => {
    if (actual === 'mv') { ir('musica'); vistaMusica('player'); return; }
    abreLetra();
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
  fondoCara(p.querySelector('#rp-portada'), e.pista.uri, 72);
}

/* ───────────── la hoja de Música, calco de Lark Player (F9) ─────────────
   De sus doce capturas se copió la estructura: barra arriba (nombre + buscar +
   ordenar + ⋮), fila de chips con el activo RELLENO, sección con su cuenta, lista de
   filas (carátula · título · artista · duración · pildoras `LETRAS`/`MV`), pestaña de
   vídeos en rejilla de dos columnas, mini-reproductor anclado abajo teñido con la
   portada y el reproductor a pantalla completa. Las tres acciones se hacen con las
   **hojas que suben de abajo**, igual que Lark con «Ordenar videos por» y su menú de
   contexto.

   Lo que se copió es lo que el puente da: `musicaBuscar`, `musicaCaratula`,
   `musicaPorGusto`, `musicaListas`, `musicaPerfil`, `musicaPoner…`, y desde 2.7.0
   también `musicaVelocidad`, `musicaDuerme`, `musicaOculta` y `abreEnlace`. Artistas y
   Álbumes se agrupan aquí, sobre la lista ya leída (Java ahora manda `album`), que es
   como Lark los pinta: sin volver a preguntar al índice. El orden también es cliente
   (con su `dur` y su `fecha` reales) porque `.Reproductor` no acepta un criterio; y no
   hay ecualizador ni carpetas porque el puente no los da. */
let musLista = [];          // última lista leída del índice: con ella se ordena sin volver a Java
let musVista = 'lista';     // 'lista' | 'player'
let musChip = 'canciones';  // la pestaña que va rellena
let musOrden = 'indice';    // 'indice' | 'recientes' | 'titulo' | 'artista' | 'album' | 'dur'
let musDir = 1;             // 1 hacia adelante, -1 invertido (el ↓↑ de Lark)

const MUS_CHIPS = [
  { id: 'canciones', txt: 'Canciones' },
  { id: 'videos', txt: 'Vídeos' },
  { id: 'artistas', txt: 'Artistas' },
  { id: 'albumes', txt: 'Álbumes' },
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
    <div class="mu-lista-top lk-buscador" id="mu-buscador" hidden>
      <div class="lk-busca-fila">
        <input id="mu-busca" placeholder="título, artista, álbum o género…">
        <button id="mu-buscar" class="lk-btn" title="buscar en tu música">🔍</button>
        <button id="mu-gusto" class="lk-btn" title="las que mejor encajan con tus gustos">♥</button>
        <button id="mu-busca-cierra" class="lk-btn" title="cerrar la búsqueda">✕</button>
      </div>
      <div class="lk-seccion lk-busca-titulo">Historial<small id="mu-busca-limpia">borrar</small></div>
      <div class="lk-pastillas lk-historial" id="mu-historial"></div>
      <div class="lk-seccion lk-busca-titulo">Sitios<small>abren el navegador</small></div>
      <div class="lk-pastillas lk-sitios" id="mu-sitios"></div>
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
  const buscador = cuerpo.querySelector('#mu-buscador');
  enganchaTransporte(cuerpo, 'mu');
  pintaChipsMusica();
  /* La lupa de Lark abre UNA PANTALLA de búsqueda, no un cuadrito: historial de lo que
     ya buscaste (en `localStorage`, como él) y los «Sitios» para buscar fuera del
     teléfono. Y busca **mientras se escribe** (320 ms de silencio), porque la dueña
     llamó «no funciona bien» a un buscador que había que estar pulsando «buscar». */
  let rulo = 0;
  cuerpo.querySelector('#mu-busca-btn').onclick = () => {
    buscador.hidden = !buscador.hidden;
    if (!buscador.hidden) { pintaBuscador(); q.focus(); }
  };
  cuerpo.querySelector('#mu-busca-cierra').onclick = () => { buscador.hidden = true; };
  q.addEventListener('input', () => {
    clearTimeout(rulo);
    rulo = setTimeout(() => buscaMusica(q.value, false), 320);
  });
  cuerpo.querySelector('#mu-buscar').onclick = () => buscaMusica(q.value, false);
  q.addEventListener('keydown', e => { if (e.key === 'Enter') buscaMusica(q.value, false); });
  cuerpo.querySelector('#mu-gusto').onclick = () => buscaMusica(q.value, true);
  cuerpo.querySelector('#mu-busca-limpia').onclick = () => {
    localStorage.setItem(CLAVE_BUSCA, '[]'); pintaBuscador();
    ctx?.say?.('Historial de búsquedas borrado.');
  };
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
  const enLista = ['canciones', 'videos', 'artistas', 'albumes'].includes(c);
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

/* ─────────────────────────── las carátulas de verdad ───────────────────────────
   La queja con `2.6.0-nucleo` fue literal: «no se ven las carátulas de los álbumes».
   Y era cierto de raíz: en todo el repo no había ni una línea que pidiera una imagen
   — la fila pintaba un `♪` sobre un degradado y el propio comentario lo decía. Ahora
   el puente tiene `musicaCaratula(uri, lado)`, que en Java responde con un
   `data:image/jpeg;base64,…` (el WebView del APK tiene `setAllowFileAccess(false)`, así
   que un `file://` o una ruta nunca se cargarían; base64 sí).

   Tres cosas que aquí importan en un teléfono modesto:
   · **Se pregunta una vez por pista y por tamaño** (`CARAS`): la misma canción en la
     lista, en el mini y en el reproductor grande es la misma imagen, no tres JNI.
   · **De pocas en pocas**: `musicaCaratula` es sincrónica, y pedir cuatrocientas de
     un tirón congela la cara justo cuando la dueña acaba de abrir la lista. Se
     surten de 4 en 4 con un `setTimeout` corto, y un número de generación corta la
     cola cuando la lista cambia mientras stillaba (buscar, cambiar de pestaña).
   · **Sin carátula no se miente**: si Java devuelve vacío se quita el `<img>` y queda
     el glifo de detrás, que es honesto; nunca se pone un cuadro de relleno. */
const CARAS = new Map();               // «uri@lado» → data URL ('' = ya pregunté: no hay)
const TINTOS = new Map();              // uri → «rgb(r,g,b)» medio de esa carátula
let carasGen = 0;

function caratula(uri, lado) {
  if (!uri || !puede('musicaCaratula')) return '';
  const k = uri + '@' + lado;
  if (!CARAS.has(k)) {
    let d = '';
    try { d = llama('musicaCaratula', uri, lado) || ''; } catch { d = ''; }
    CARAS.set(k, d);
  }
  return CARAS.get(k);
}

function pintaCaratulas(raiz, lado) {
  if (!raiz || !puede('musicaCaratula')) return;
  const nodos = [...raiz.querySelectorAll('img[data-cara]:not([src])')];
  const mia = ++carasGen;
  let i = 0;
  (function surte() {
    if (carasGen !== mia) return;            // ya se pintó otra lista: esta cola sobra
    const fin = Math.min(i + 4, nodos.length);
    for (; i < fin; i++) {
      const im = nodos[i];
      const d = caratula(im.dataset.cara, lado);
      if (!d) { if (im.isConnected) im.remove(); continue; }
      if (im.isConnected) im.src = d;
    }
    if (i < nodos.length) setTimeout(surte, 12);
  })();
}

/* La carátula como fondo de un cuadro grande (el reproductor, el mini, la píldora):
   con `background-image` no hace falta cambiar el nodo ni perder el glifo si no hay. */
function fondoCara(el, uri, lado) {
  if (!el) return;
  const d = uri ? caratula(uri, lado) : '';
  el.style.backgroundImage = d ? 'url("' + d + '")' : '';
  el.classList.toggle('con-foto', !!d);
}

/* El tinte de Lark: la barra y el fondo se tiñen con el color medio de la portada.
   Sacar ese promedio aquí (un lienzo de 8×8) es lo que en Android hace Lark con su
   `Palette`; sin carátula no hay tinte y se queda el acento de la app. */
function tinteDe(uri, cb) {
  if (!uri) { cb(''); return; }
  if (TINTOS.has(uri)) { cb(TINTOS.get(uri)); return; }
  const d = caratula(uri, 128);
  if (!d) { TINTOS.set(uri, ''); cb(''); return; }
  const im = new Image();
  im.onload = () => {
    try {
      const c = document.createElement('canvas');
      c.width = c.height = 8;
      const g = c.getContext('2d');
      g.drawImage(im, 0, 0, 8, 8);
      const px = g.getImageData(0, 0, 8, 8).data;
      let r = 0, gg = 0, b = 0, n = 0;
      for (let i = 0; i < px.length; i += 4) {
        if (px[i + 3] < 128) continue;                  // transparente: no cuenta
        r += px[i]; gg += px[i + 1]; b += px[i + 2]; n++;
      }
      const t = n ? 'rgb(' + [r, gg, b].map(x => Math.round(x / n)).join(',') + ')' : '';
      TINTOS.set(uri, t); cb(t);
    } catch (lienzoTorcido) { TINTOS.set(uri, ''); cb(''); }
  };
  im.onerror = () => { TINTOS.set(uri, ''); cb(''); };
  im.src = d;
}

/* El «Ordenar» de Lark, pero dicho como es: los criterios se aplican a la lista que
   ya está leída. La duración es la que manda `.Reproductor` (`dur` en ms), no un
   adorno. La flecha de la derecha es la de sus capturas (`↓↑`): invierte el criterio,
   así que «más antiguas primero» no necesita una fila más en el menú.

   Lo que NO se copió: «Más reproducido». Android no expone una columna pública de
   reproducciones para la música del índice (era dato interno del reproductor de
   Google), y pintarla con ceros sería un botón que miente. */
function hojaOrden() {
  const OPC = [
    ['recientes', 'Más recientes', 'lo que entró hace poco al índice'],
    ['indice', 'Como vinieron', 'el orden del índice, sin tocar'],
    ['titulo', 'Título', 'A → Z'],
    ['artista', 'Artista', 'A → Z'],
    ['album', 'Álbum', 'A → Z'],
    ['dur', 'Duración', 'las más largas primero'],
  ];
  const relleno = OPC.map(([id, txt, sub]) => `<div class="hoja-fila${id === musOrden ? ' elegida' : ''}"
    data-o="${id}"><i>${id === musOrden ? '✓' : '·'}</i>${txt}<small>${sub}</small>${
      id === 'indice' || id === 'dur' ? '' : `<b class="lk-flecha">${musDir < 0 ? '↑' : '↓'}</b>`
    }</div>`).join('');
  abreHoja({
    titulo: 'Ordenar por',
    html: relleno + '<div class="hoja-nota">tocar dos veces el criterio lo invierte, como el ↓↑ de Lark</div>',
    alAbrir: raiz => raiz.querySelectorAll('[data-o]').forEach(f => f.onclick = () => {
      if (f.dataset.o === musOrden) musDir = -musDir;                 // repetir criterio = girarlo
      else { musOrden = f.dataset.o; musDir = 1; }
      pintaMusicaLista();
      ctx?.say?.('Ordenado por ' + (OPC.find(o => o[0] === musOrden) || OPC[1])[1].toLowerCase()
        + (musDir < 0 ? ', al revés.' : '.'));
      cierraHoja();
    }),
  });
}

/* El menú ⋮, fila por fila como el de sus capturas (Agregar a la lista · Compartir ·
   Velocidad · Temporizador para dormir · Ocultar · Borrar), pero sólo con lo que el
   puente sabe hacer de verdad:

   · Compartir y Ocultar son nuevos y reales: `comparte(uri)` abre el cuadro de apps de
     Android, y `musicaOculta(uri)` esconde la pista del índice para CORT (vive en las
     preferencias, no borra el archivo).
   · «Borrar» de Lark **no** se copió: borraría el archivo de la memoria de la dueña, y
     un botón que tira música por accidente no es una réplica, es un peligro.
   · «Modo de ahorro de energía» tampoco: Android no deja que una app se ponga a sí misma
     en ahorro, es del sistema. Se dice en la hoja, no se finge.
   · No hay cola que editar (`.Reproductor` no la expone), así que aquí no se inventa. */
function hojaMas() {
  const e = estadoMusica();
  const pista = e?.pista;
  const tapadas = puede('musicaOcultas') ? (llama('musicaOcultas') || 0) : 0;
  const filas = [
    ['♪', 'Ponme algo de tus gustos', 'sin tocar nada', () => { llama('musicaAutomatica'); cierraHoja(); }],
    ['👍', pista ? 'Me gusta: ' + (pista.titulo || '') : 'Me gusta', 'entrena tus gustos', () => {
      if (!pista) return ctx?.say?.('No hay nada puesto que evaluar.');
      llama('musicaGustar', pista.uri, true); cierraHoja();
    }],
    ['❝', 'Letra y vídeo', 'la misma pista, sin orbe', () => { cierraHoja(); abreLetra(); }],
    ['💾', 'Agregar a la lista', pista ? (pista.titulo || '') : 'necesita una pista puesta', () => {
      if (!pista) return ctx?.say?.('Primero pon algo, que se guarda lo que está sonando.');
      const caja = document.getElementById('mu-listas');
      if (caja) caja.hidden = false;
      const nombre = document.getElementById('mu-pl-nombre');
      if (nombre) { nombre.value = pista.titulo || 'mi lista'; nombre.focus(); }
      cierraHoja(); eligeChip('listas');
    }],
    ['📤', 'Compartir', 'por WhatsApp, correo o lo que haya', () => {
      if (!pista) return ctx?.say?.('No hay nada puesto que compartir.');
      if (!puede('comparte')) return ctx?.say?.('Compartir con CORT lo trae el APK nuevo de la Release.');
      const crudo = llama('comparte', pista.uri || '');
      let r = null; try { r = crudo ? JSON.parse(crudo) : null; } catch { r = null; }
      if (r && r.ok === false) return ctx?.say?.(r.dice || 'ese archivo no se pudo compartir.');
      cierraHoja();
      ctx?.say?.('Elige por dónde lo mandas.');
    }],
    ['⏱', 'Velocidad', e?.velocidad ? 'ahora ' + e.velocidad + '×' : 'de 0,5× a 2×', () => hojaVelocidad()],
    ['🌙', 'Temporizador para dormir', 'para la música sola', () => hojaDormir()],
    ['🚫', 'Ocultar esta pista', pista ? (pista.titulo || '') : 'necesita una pista puesta', () => {
      if (!pista) return ctx?.say?.('No hay nada puesto que ocultar.');
      if (!puede('musicaOculta')) return ctx?.say?.('Ocultar pistas lo trae el APK nuevo de la Release.');
      llama('musicaOculta', pista.uri);
      ctx?.say?.('Oculta para CORT: el archivo sigue en tu teléfono.');
      cierraHoja();
      buscaMusica(document.getElementById('mu-busca')?.value || '', false);
    }],
    ['👁', 'Mostrar las ocultadas', tapadas ? tapadas + ' escondidas' : 'ninguna escondida', () => {
      if (!tapadas) return ctx?.say?.('No hay ninguna pista escondida.');
      llama('musicaMuestraTodas');
      ctx?.say?.('Enseño las ' + tapadas + ' que habías escondido.');
      cierraHoja();
      buscaMusica(document.getElementById('mu-busca')?.value || '', false);
    }],
    ['🎮', 'Modo juego', 'CORT se aparta mientras juegas', () => {
      ctx?.say?.(modoJuego(!((estadoMusica() || {}).juego))); cierraHoja();
    }],
    ['🔋', 'Ahorro de energía', 'lo pone Android, no CORT', () => {
      cierraHoja();
      ctx?.say?.('El ahorro de energía lo decide Android, no yo: está en Ajustes del teléfono ▸ Batería.');
    }],
  ];
  abreHoja({
    titulo: pista ? (pista.titulo || 'la pista') : 'Música',
    html: filas.map(([ic, txt, sub], i) => `<div class="hoja-fila" data-i="${i}">
      <i>${ic}</i>${esc(txt)}<small>${esc(sub)}</small></div>`).join(''),
    alAbrir: raiz => raiz.querySelectorAll('[data-i]').forEach(f => f.onclick = () => filas[+f.dataset.i][3]()),
  });
}

/* La velocidad de Lark (0,5× a 2×) manda a `MediaPlayer.setPlaybackParams`, que en
   Android sólo funciona con el reproductor **en pausa**: por eso `Reproductor.velocidad`
   pausa, ajusta y reanuda si estaba sonando. Se dice el resultado, no se supone. */
function hojaVelocidad() {
  if (!puede('musicaVelocidad')) {
    ctx?.say?.('Cambiar la velocidad lo trae el APK nuevo de la Release.');
    return;
  }
  const VAL = [.5, .75, 1, 1.25, 1.5, 1.75, 2];
  abreHoja({
    titulo: 'Velocidad',
    html: VAL.map(v => `<div class="hoja-fila" data-v="${v}"><i>${v === 1 ? '✓' : '·'}</i>${
      String(v).replace('.', ',') + '×'}<small>${
      v < 1 ? 'más despacio' : v > 1 ? 'más rápido' : 'normal'}</small></div>`).join('')
      + '<div class="hoja-nota">se pone en pausa un instante: Android no admite cambiar la velocidad sonando</div>',
    alAbrir: raiz => raiz.querySelectorAll('[data-v]').forEach(f => f.onclick = () => {
      const motivo = llama('musicaVelocidad', parseFloat(f.dataset.v));
      cierraHoja();
      ctx?.say?.(motivo ? motivo : 'A ' + String(parseFloat(f.dataset.v)).replace('.', ',') + '×.');
    }),
  });
}

/* «Temporizador para dormir»: Java para el `Reproductor` y avisa, con un `Handler` del
   servicio. 0 lo quita, igual que Lark con su fila «Apagar». */
function hojaDormir() {
  if (!puede('musicaDuerme')) {
    ctx?.say?.('El temporizador para dormir lo trae el APK nuevo de la Release.');
    return;
  }
  const MIN = [5, 10, 20, 30, 45, 60, 0];
  abreHoja({
    titulo: 'Duerme en…',
    html: MIN.map(m => `<div class="hoja-fila" data-m="${m}"><i>·</i>${
      m ? m + ' minutos' : 'Apagar el temporizador'}<small>${m ? 'para la música sola' : 'que siga sonando'}</small></div>`).join(''),
    alAbrir: raiz => raiz.querySelectorAll('[data-m]').forEach(f => f.onclick = () => {
      const m = +f.dataset.m;
      llama('musicaDuerme', m);
      cierraHoja();
      ctx?.say?.(m ? 'Paro la música en ' + m + ' minutos.' : 'Sin temporizador: sigue sonando.');
    }),
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
  fondoCara(document.getElementById('mus-mini-portada'), e?.pista?.uri, 96);
  if (viva && e.pista.uri) tinteDe(e.pista.uri, t => {
    if (t) mini.style.setProperty('--tinte', t);
  });
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

/* El buscador de Lark es una pantalla, no un campo suelto: arriba lo buscado antes
   («hot girl», «hard», «stereo», «douyin»… en sus capturas) y debajo los Sitios. El
   historial vive en `localStorage` (el WebView tiene `setDomStorageEnabled(true)`,
   `MainActivity.java:126`), máximo diez frases y las más recientes delante.

   Los Sitios **sí** abren: `abreEnlace(uri)` lanza un `ACTION_VIEW` en Java, que es lo
   único que puede en un WebView sin ventana nueva. Si el APK stilla viejo y no trae el
   método, se dice en vez de quedarse muda. */
const CLAVE_BUSCA = 'cort-busca-historial';
const SITIOS = [
  ['YouTube', t => 'https://www.youtube.com/results?search_query=' + encodeURIComponent(t)],
  ['SoundCloud', t => 'https://soundcloud.com/search?q=' + encodeURIComponent(t)],
  ['Instagram', t => 'https://www.instagram.com/explore/tags/' + encodeURIComponent(t.replace(/\s+/g, ''))],
  ['Facebook', t => 'https://www.facebook.com/search/top?q=' + encodeURIComponent(t)],
  ['X', t => 'https://twitter.com/search?q=' + encodeURIComponent(t)],
];

function historialBusca() {
  try {
    const v = JSON.parse(localStorage.getItem(CLAVE_BUSCA) || '[]');
    return Array.isArray(v) ? v.filter(x => typeof x === 'string' && x) : [];
  } catch (torcido) { return []; }
}

function apuntaBusca(frase) {
  const viejo = historialBusca().filter(x => x.toLowerCase() !== frase.toLowerCase());
  localStorage.setItem(CLAVE_BUSCA, JSON.stringify([frase, ...viejo].slice(0, 10)));
  pintaBuscador();
}

function pintaBuscador() {
  const hist = document.getElementById('mu-historial');
  const sitios = document.getElementById('mu-sitios');
  const q = document.getElementById('mu-busca');
  if (!hist || !sitios) return;
  montaSitios();
  const h = historialBusca();
  hist.innerHTML = h.length
    ? h.map((x, i) => `<button class="mu-chip" data-h="${i}">${esc(x)}</button>`).join('')
    : '<span class="lk-historial-vacio">aún no buscaste nada</span>';
  hist.querySelectorAll('[data-h]').forEach(b => b.onclick = () => {
    if (q) q.value = h[+b.dataset.h];
    buscaMusica(h[+b.dataset.h], false);
  });
  const uno = (q?.value || '').trim() || h[0] || '';
  sitios.querySelectorAll('[data-s]').forEach(b => b.onclick = () => {
    const url = SITIOS[+b.dataset.s][1](uno);
    if (!puede('abreEnlace')) return ctx?.say?.('Abrir enlaces con CORT lo trae el APK nuevo de la Release.');
    const motivo = llama('abreEnlace', url);
    ctx?.say?.(motivo ? motivo : 'Abriendo ' + SITIOS[+b.dataset.s][0] + '.');
    cierraHoja();
  });
}

/* Los botones de los Sitios se montan una sola vez (no cambian nunca); lo que se
   repinta es su comportamiento, que depende de lo que haya escrito la dueña. */
function montaSitios() {
  const sitios = document.getElementById('mu-sitios');
  if (!sitios || sitios.childElementCount) return;
  sitios.innerHTML = SITIOS.map(([n], i) => `<button class="mu-chip" data-s="${i}">${n}</button>`).join('');
}

function buscaMusica(texto, porGusto) {
  const caja = document.getElementById('mu-pistas');
  if (!caja) return;
  const t = String(texto || '').trim();
  if (t && !porGusto) apuntaBusca(t);
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
   lista**, sin volverle a pedir nada a Java.

   Con las capturas de Lark por delante hay dos formas de fila: la de siempre (lista
   de canciones) y la rejilla de dos columnas de la pestaña «Vídeos», que es como Lark
   enseña sus `1786 Vídeos` — miniatura grande arriba, título debajo y la duración
   escrita como él (`0:22`). Las dos llevan las pildoritas `LETRAS` y `MV` que Lark
   pega a la derecha del artista: salen de `letra` y `mv`, que ahora rellena Java
   leyendo el índice (la letra puede ser marca ID3 o un `.lrc`/`.txt` hermano), así
   que la píldora promete algo que luego la hoja de letra va a encontrar. */
/* La cuenta de cada sección, escrita como la escribe Lark: en singular cuando es una.
   «1 canciones» es de texto puesto a machine, y la dueña mira esos detalles. */
const cuentaDe = (n, uno, muchos) => n ? n + ' ' + (n === 1 ? uno : muchos) : '';

function pintaMusicaLista() {
  const caja = document.getElementById('mu-pistas');
  if (!caja) return;
  const cuenta = document.getElementById('mu-cuenta');
  if (musChip === 'artistas' || musChip === 'albumes') {
    pintaGrupos(musChip === 'artistas' ? 'artista' : 'album', caja, cuenta);
    return;
  }
  const videos = musChip === 'videos';
  let lista = videos ? musLista.filter(p => p.video) : musLista.filter(p => !p.video);
  const ordenada = musOrden === 'indice' ? lista : [...lista].sort((a, b) => musDir * (
    musOrden === 'dur' ? (b.dur || 0) - (a.dur || 0)
      : musOrden === 'recientes' ? (b.fecha || 0) - (a.fecha || 0)
      : String(a[musOrden] || '').localeCompare(String(b[musOrden] || ''), 'es', { sensitivity: 'base' })));
  if (cuenta) cuenta.textContent = videos ? cuentaDe(ordenada.length, 'vídeo', 'vídeos')
                                          : cuentaDe(ordenada.length, 'canción', 'canciones');
  caja.classList.toggle('lk-cuadricula', videos);
  caja.innerHTML = '';
  if (!ordenada.length) {
    caja.innerHTML = '<div class="mu-vacio">' + (videos
      ? 'nada de vídeo por aquí · el índice del teléfono no trae clips, o hay que dar el permiso de vídeos'
      : 'nada con ese nombre · prueba con otra palabra o «por gusto»') + '</div>';
    return;
  }
  const uris = ordenada.map(p => p.uri);
  const e = estadoMusica();
  ordenada.forEach((p, i) => {
    const d = document.createElement('div');
    d.className = 'lk-fila' + (videos ? ' lk-card' : '')
      + (e?.pista && e.pista.uri === p.uri ? ' sonando' : '');
    d.dataset.uri = p.uri || '';
    const pildoras = [p.letra ? 'LETRAS' : '', p.mv ? 'MV' : ''].filter(Boolean)
      .map(t => `<b class="lk-pilda">${t}</b>`).join('');
    const quien = esc([p.artista, p.genero].filter(Boolean).join(' · '));
    d.innerHTML = videos
      ? `<span class="lk-miniatura"><i>▣</i><img data-cara="${esc(p.uri)}" alt="" loading="lazy">
           <em>${p.dur ? reloj(p.dur) : ''}</em></span>
         <span class="lk-txt"><b>${esc(p.titulo)}</b><span>${quien}</span></span>${pildoras}`
      : `<span class="lk-portada"><i>♪</i><img data-cara="${esc(p.uri)}" alt="" loading="lazy"></span>
         <span class="lk-txt"><b>${esc(p.titulo)}</b><span>${quien || esc(p.album || '')}</span></span>
         ${pildoras}<em>${p.dur ? reloj(p.dur) : ''}</em>`;
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
  pintaCaratulas(caja, videos ? 220 : 96);
}

/* Artistas y Álbumes, que en Lark son dos pestañas más. Se agrupan **aquí**, sobre la
   lista que ya está leída: Java manda `album` y `artista` en cada pista desde 2.7.0, así
   que no hace falta otra consulta al índice. Tocar un grupo pone sus canciones en orden
   de álbum (es el mismo `musicaPoner` de la lista, con sus propias URIs), y la carátula
   del grupo es la de su primera pista — que es la del álbum, porque comparten `ALBUM_ID`. */
function pintaGrupos(clave, caja, cuenta) {
  const grupos = new Map();
  musLista.filter(p => !p.video && (p[clave] || '').trim()).forEach(p => {
    const nombre = p[clave].trim();
    if (!grupos.has(nombre)) grupos.set(nombre, []);
    grupos.get(nombre).push(p);
  });
  const nombres = [...grupos.keys()].sort((a, b) =>
    a.localeCompare(b, 'es', { sensitivity: 'base' }));
  caja.classList.remove('lk-cuadricula');
  caja.innerHTML = '';
  if (cuenta) cuenta.textContent = clave === 'album'
    ? cuentaDe(nombres.length, 'álbum', 'álbumes')
    : cuentaDe(nombres.length, 'artista', 'artistas');
  if (!nombres.length) {
    caja.innerHTML = '<div class="mu-vacio">el índice del teléfono no trae '
      + (clave === 'album' ? 'nombres de álbum' : 'nombres de artista')
      + ' en esas etiquetas · prueba a buscar una palabra</div>';
    return;
  }
  nombres.forEach(n => {
    const pistas = grupos.get(n);
    const e = estadoMusica();
    const d = document.createElement('div');
    d.className = 'lk-fila' + (e?.pista && pistas.some(x => x.uri === e.pista.uri) ? ' sonando' : '');
    d.innerHTML = `<span class="lk-portada"><i>${clave === 'album' ? '◉' : '🎤'}</i>
        <img data-cara="${esc(pistas[0].uri)}" alt="" loading="lazy"></span>
      <span class="lk-txt"><b>${esc(n)}</b>
        <span>${pistas.length} ${pistas.length === 1 ? 'canción' : 'canciones'}${
          clave === 'album' ? ' · ' + esc(pistas[0].artista || '') : ''}</span></span>`;
    d.onclick = () => {
      const uris = pistas.map(p => p.uri).join('\n');
      if (llama('musicaPoner', uris, 0) === false) ctx?.say?.('Ese grupo ya no está en el teléfono.');
      pintaMusicaLista();
      pintaMini(estadoMusica());
    };
    caja.appendChild(d);
  });
  pintaCaratulas(caja, 96);
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
  pintaModosMusica(e);     // aleatorio, repetir y el último aviso del servicio
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

/* El título y el artista, dicho una vez y pintado en las dos hojas. Y con ellos la
   carátula grande y el tinte: `ponRotulos` es el único sitio al que llegan los avisos
   de Java (`escuchaMusica`) y las entradas en la hoja (`arrancaMusica`, `arrancaMV`),
   así que poner la foto aquí es ponerla una sola vez para todas las vistas. */
function ponRotulos(e) {
  ['mu', 'mv'].forEach(p => {
    const ahora = document.getElementById(p + '-ahora');
    if (!ahora) return;
    ahora.textContent = e?.pista ? e.pista.titulo : 'nada puesto';
    const art = document.getElementById(p + '-artista');
    if (art) art.textContent = e?.pista
      ? [e.pista.artista, e.pista.genero].filter(Boolean).join(' · ') : '';
    fondoCara(document.getElementById(p + '-caratula'), e?.pista?.uri, 320);
  });
  const uri = e?.pista?.uri || '';
  if (!uri) {                     // sin pista no hay foto ni tinte: se quitan los dos
    ['mu', 'mv'].forEach(p => document.getElementById(p + '-player')
      ?.style.removeProperty('--tinte'));
    return;
  }
  tinteDe(uri, t => {
    if (!t) return;
    ['mu', 'mv'].forEach(p => document.getElementById(p + '-player')
      ?.style.setProperty('--tinte', t));
    document.getElementById('mus-mini')?.style.setProperty('--tinte', t);
  });
}

/* F20 · el estado de los dos modos, sacado de `musicaEstado()` y no de un booleano
   de la cara. Si el servicio se reinicia, lo que se pinta sigue siendo la verdad. */
function pintaModosMusica(e) {
  ['mu', 'mv'].forEach(p => {
    const al = document.getElementById(p + '-aleatorio');
    const rep = document.getElementById(p + '-repetir');
    const av = document.getElementById(p + '-nota');
    if (al) {
      const on = !!e?.aleatorio;
      al.classList.toggle('on', on);
      al.textContent = on ? '⇄ aleatorio sí' : '⇄ aleatorio';
    }
    if (rep) {
      const m = typeof e?.repetir === 'number' ? e.repetir : 1;
      rep.classList.toggle('on', m !== 0);
      rep.textContent = m === 0 ? '↻ sin repetir' : (m === 1 ? '↻ repetir cola' : '↻ repetir esta');
    }
    if (av) { av.textContent = e?.aviso || ''; av.hidden = !e?.aviso; }
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
    <div class="lk-barra">
      <button class="lk-btn" id="mv-vuelve" title="Volver al reproductor">‹</button>
      <span class="lk-nombre">Música · Letra</span>
      <span class="lk-espacio"></span>
      <button class="lk-btn" id="mv-mas" title="Más acciones">⋮</button>
    </div>
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
  cuerpo.querySelector('#mv-vuelve').onclick = () => { ir('musica'); vistaMusica('player'); };
  cuerpo.querySelector('#mv-mas').onclick = hojaMas;
  cuerpo.querySelector('#mv-rebuscar').onclick = () => pideLetra(true);
  cuerpo.querySelector('#mv-copiar').onclick = () => {
    if (!letraPlana) return ctx?.say?.('Aún no hay letra que copiar: pulsa «rebuscar la letra».');
    copia(letraPlana, 'Letra copiada.');
  };
  enganchaTransporte(cuerpo, 'mv');
}

/* El `❝ Letras` de Lark: la misma pista, pero con la imagen y el karaoke delante.
   Desde la fusión es un botón del reproductor, no una app del cajón — por eso sale de
   aquí y no de `ir('mv')` a pelo: si el puente no monta la hoja (un PC, o un APK sin
   vídeos), lo dice en vez de llevar a un sitio vacío. */
function abreLetra() {
  if (!document.getElementById('mv-video')) {
    ctx?.say?.('Sin el teléfono no hay letra dentro de CORT: la letra la trae la hoja de música del APK.');
    return false;
  }
  ir('mv');
  const caja = document.getElementById('mv-letra');
  if (caja) caja.scrollIntoView({ block: 'start' });
  return true;
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

/* ───────────────────── agua y vidrio con freno (F17) ─────────────────────
 * La cara tiene una capa de agua (#agua) y paneles de vidrio (`backdrop-filter`).
 * Las dos son bonitas y las dos cuestan: el desenfoque se recalcula en cada
 * fotograma. El freno no las quita para siempre —las deja donde se notan—; las
 * apaga donde cuestan: **poca RAM** o **modo juego**. Con `html.freno`, el CSS
 * cambia el filtro del agua por un tinte quieto y quita el `backdrop-filter`.
 *
 * `navigator.deviceMemory` redondea a potencia de dos: el portátil de 1,8 GiB
 * dice 2 y el Samsung de 4 GB dice 4. Por eso el umbral es `<= 2`, no `< 4`. */
const POCA_RAM = (() => {
  try {
    const g = Number(navigator.deviceMemory);
    return Number.isFinite(g) && g > 0 && g <= 2;
  } catch (sinMemoria) {
    return false;
  }
})();
let juegoPuesto = false;

function ponFreno() {
  const raiz = document.documentElement;
  if (!raiz) return;
  raiz.classList.toggle('freno', POCA_RAM || juegoPuesto);
  raiz.classList.toggle('freno-ram', POCA_RAM);
  raiz.classList.toggle('freno-juego', juegoPuesto);
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
  juegoPuesto = !!on;
  ponFreno();                       // jugar también frena el agua y el vidrio
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
   que no está en `montables()` cae en el Orbe sin decir nada, y un atajo que abre la
   ventana equivocada es peor que un atajo que avisa. «Equipo», por ejemplo, pide el
   puente de acciones: con un APK viejo no existe. Se usa `montables()` y no
   `visibles()` para que un atajo futuro pueda abrir también la letra fusionada. */
let atajosViva = false;
function escuchaAtajos() {
  if (atajosViva || !window.__cortNative) return;
  atajosViva = true;
  window.__cortNative.on(ev => {
    if (!ev || ev.type !== 'atajo') return;
    const id = String(ev.hoja || '');
    const p = montables().find(x => x.id === id);
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
  escuchaMente();          // la Charla también recibe al cerebro del teléfono
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
  // `pintaJuego` enciende además el freno de agua y vidrio (F17).
  ponFreno();
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
  // F19 · el índice de todo. «¿qué sabes hacer?» es la pregunta más natural y
  // antes se iba al cerebro a inventar una lista; aquí está la de verdad.
  if (/(centro de mando|todas (las|tus) (o[ró]rdenes|funciones)|qu[eé] sabe[s]? hacer|cat[aá]logo de (o[ró]rdenes|funciones))/i.test(t)) {
    ir('centro'); return 'centro';
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
