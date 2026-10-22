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
  { id: 'orbe',   titulo: 'Orbe',    sub: 'el holograma de siempre' },
  { id: 'musica', titulo: 'Música',   sub: 'el reproductor de CORT', telefono: true },
  { id: 'mv',     titulo: 'MV',       sub: 'el video con su letra', telefono: true },
  { id: 'charla', titulo: 'Charla',   sub: 'conversa con tus modelos' },
  { id: 'codigo', titulo: 'Código',   sub: 'terminal y programar' },
  // La hoja del contrato 2.1: manda sobre el aparato. Sin puente no existe — en el
  // PC no hay volumen que subir ni linterna que encender, y un botón que no hace
  // nada es peor que un botón que no se ofrece.
  // `puente: 'accion'` es la segunda condición: un APK viejo sí tiene `CortNative`
  // pero no trae los métodos del contrato 2.1, y ahí la hoja entera sobra.
  { id: 'equipo', titulo: 'Equipo',   sub: 'lo que manda CORT en el teléfono',
    telefono: true, puente: 'accion' },
];
// `visibles()` es la única lista que se pinta (menú, teclas, deslizar, `ir`). Una
// hoja con `puente` solo se ofrece si el puente de Java trae ese método de verdad.
const visibles = () => PANTALLAS.filter(p => (!p.telefono || enTelefono())
  && (!p.puente || puede(p.puente)));

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

function montaCarcasa() {
  if (document.getElementById('pantalla-bar')) return;

  const barra = document.createElement('div');
  barra.id = 'pantalla-bar';
  barra.innerHTML = `
    <button id="menu3" title="Cambiar de pantalla" aria-label="Menú de pantallas">
      <i></i><i></i><i></i></button>
    <span id="pantalla-titulo">Orbe</span>
    <span id="pantalla-sub">el holograma de siempre</span>
    <span id="pantalla-juego" hidden title="CORT está en silencio mientras juegas">🎮 modo juego</span>`;
  document.body.appendChild(barra);

  const menu = document.createElement('nav');
  menu.id = 'pantalla-menu';
  menu.innerHTML = visibles().map(p =>
    `<button data-p="${p.id}" class="${p.id === actual ? 'activa' : ''}">` +
    `<b>${esc(p.titulo)}</b><span>${esc(p.sub)}</span></button>`).join('')
    + '<div class="pm-pista">o desliza el dedo a un lado</div>';
  document.body.appendChild(menu);
  menu.querySelectorAll('[data-p]').forEach(b => b.onclick = () => { cierraMenu(); ir(b.dataset.p); });
  document.getElementById('menu3').onclick = e => {
    e.stopPropagation();
    document.documentElement.classList.toggle('menu-abierto');
  };
  document.addEventListener('pointerdown', e => {
    if (!document.documentElement.classList.contains('menu-abierto')) return;
    if (menu.contains(e.target) || e.target.closest('#menu3')) return;
    cierraMenu();
  });

  // Secciones: sólo la charla y el código existen en los dos aparatos; la música
  // se monta igual y queda oculta en el PC (el menú ni la lista).
  visibles().filter(p => p.id !== 'orbe').forEach(p => {
    const s = document.createElement('section');
    s.className = 'scr'; s.id = 'scr-' + p.id;
    s.innerHTML = `<header class="scr-top"><button class="scr-vuelve" title="Volver al orbe">◂ orbe</button>
      <b>${esc(p.titulo)}</b><span class="scr-estado"></span></header>
      <div class="scr-cuerpo"></div>`;
    document.body.appendChild(s);
    s.querySelector('.scr-vuelve').onclick = () => ir('orbe');
  });

  const fletas = document.createElement('div');
  fletas.id = 'pantalla-fletas';
  fletas.innerHTML = '<button id="pf-left" title="pantalla anterior">‹</button>'
                   + '<button id="pf-right" title="pantalla siguiente">›</button>';
  document.body.appendChild(fletas);
  document.getElementById('pf-left').onclick = () => mueve(-1);
  document.getElementById('pf-right').onclick = () => mueve(1);
}

const cierraMenu = () => document.documentElement.classList.remove('menu-abierto');

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
  const NO_ES_GESTO = '#pantalla-menu, button, a, input, textarea, select, output,'
    + ' .scr-lista, #plist, #flist, .mu-transporte, .mu-fila2, .mu-volumen, .mu-barra,'
    + ' #mic, #dock, #repro-pildora, #pantalla-fletas';
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
   una concreta. No uso Escape: ése ya es de las ventanas de vidrio en hud.js, y
   dos dueñas para la misma tecla terminan peleándose. */
function montaTeclas() {
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
  const titulo = document.getElementById('pantalla-titulo');
  if (titulo) titulo.textContent = p.titulo;
  const sub = document.getElementById('pantalla-sub');
  if (sub) sub.textContent = p.sub;
  document.querySelectorAll('#pantalla-menu [data-p]').forEach(b =>
    b.classList.toggle('activa', b.dataset.p === actual));
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

function montaCharla() {
  const cuerpo = document.querySelector('#scr-charla .scr-cuerpo');
  cuerpo.innerHTML = `
    <div class="ch-modelos" id="ch-modelos"><span class="ch-cargando">leyendo tus modelos…</span></div>
    <div class="scr-lista ch-msgs" id="ch-msgs"></div>
    <div class="ch-fila">
      <textarea id="ch-entrada" rows="1" placeholder="pregúntale lo que sea · Enter envía, Mayús+Enter salto de línea"></textarea>
      <button id="ch-enviar" title="Enviar">▲</button>
    </div>
    <div class="ch-herramientas">
      <button id="ch-copiar-ultimo" title="Copiar la última respuesta">copiar respuesta</button>
      <button id="ch-nota" title="Guardar la última respuesta como nota">guardar en Notas</button>
      <button id="ch-vaciar" title="Vaciar esta conversación">limpiar</button>
    </div>`;
  const entrada = cuerpo.querySelector('#ch-entrada');
  cuerpo.querySelector('#ch-enviar').onclick = () => charla(entrada.value);
  entrada.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); charla(entrada.value); }
  });
  entrada.addEventListener('input', () => {
    entrada.style.height = 'auto';
    entrada.style.height = Math.min(140, entrada.scrollHeight) + 'px';
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
        body: JSON.stringify({ text: '[charla] ' + ultimo.texto }),
      });
      ctx?.say?.(r.ok ? 'Anotado en 04 · Notas.' : 'El núcleo no dejó guardar la nota.');
    } catch { ctx?.say?.('El núcleo no respondió.') }
  };
  cuerpo.querySelector('#ch-vaciar').onclick = () => {
    mensajes = []; guardaMensajes(); pintaCharla();
  };
  cargaMensajes();
}

async function charla(texto) {
  const pregunta = String(texto || '').trim();
  if (!pregunta) return;
  const entrada = document.getElementById('ch-entrada');
  if (entrada) { entrada.value = ''; entrada.style.height = 'auto'; }
  mensajes.push({ de: 'tu', texto: pregunta });
  pintaCharla();
  const estado = document.querySelector('#scr-charla .scr-estado');
  estado.textContent = 'pensando…';
  if (!await avisaSinNucleo(estado)) {
    mensajes.push({ de: 'cort', texto: sinNucleoFrase() });
    estado.textContent = 'sin núcleo'; guardaMensajes(); pintaCharla(); return;
  }
  try {
    const r = await fetch(ctx.api() + '/api/chat', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ message: pregunta }),
    });
    const j = await r.json();
    const dicho = j.reply || j.error || 'No supe qué contestar.';
    mensajes.push({ de: 'cort', texto: dicho, fuente: j.source || '' });
    estado.textContent = 'cerebro: ' + (j.source || 'local');
    ctx?.orb?.burst?.();
  } catch (e) {
    mensajes.push({ de: 'cort', texto: 'El núcleo se cayó a media respuesta: ' + e });
    estado.textContent = 'sin núcleo';
  }
  guardaMensajes(); pintaCharla();
}

/* El historial de verdad está en el núcleo (`GET /api/history`), y la cara nunca lo
   pedía: al reinstalar la app, cambiar de aparato o vaciar el almacén del navegador,
   la Charla se abría en blanco aunque CORT se acordara de lo hablado. Se trae sólo
   cuando la hoja está VACÍA: si la dueña ya tiene su conversación local, mezclar los
   dos listados saldría un desorden peor que dejar el suyo. Un fallo de red aquí no
   dice nada ni estorba —la charla funciona igual sin historial—, así que se traga
   en silencio; lo que no se traga es una respuesta que no sea 200. */
async function traeHistorial() {
  if (mensajes.length || !ctx?.api) return;
  try {
    const r = await fetch(ctx.api() + '/api/history?n=40',
                          { signal: AbortSignal.timeout(2500) });
    if (!r.ok) return;
    const filas = await r.json();
    if (!Array.isArray(filas) || !filas.length) return;
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
  caja.innerHTML = mensajes.length ? '' :
    '<div class="ch-vacio">Aquí se conversa de verdad: escribe o toca el micrófono. ' +
    'Lo que responda se puede copiar o guardar como nota.</div>';
  mensajes.forEach(m => {
    const b = document.createElement('div');
    b.className = 'burbuja ' + (m.de === 'tu' ? 'de-tu' : 'de-cort');
    b.innerHTML = `<div class="bur-texto">${esc(m.texto).replace(/\n/g, '<br>')}</div>
      <div class="bur-pie"><span>${m.de === 'tu' ? 'tú' : 'CORT' + (m.fuente ? ' · ' + esc(m.fuente) : '')}</span>
      <button class="bur-copiar" title="Copiar este texto">copiar</button></div>`;
    b.querySelector('.bur-copiar').onclick = () => copia(m.texto, 'Copiado.');
    caja.appendChild(b);
  });
  caja.scrollTop = caja.scrollHeight;
}

async function cargaModelos() {
  const caja = document.getElementById('ch-modelos');
  if (!caja) return;
  const enPC = !enTelefono();
  // El teléfono no tiene modelos: los tiene Ollama, y Ollama vive en el portátil.
  // Sin PC la lista NO se pinta vacía en silencio —eso parece un fallo de CORT—,
  // se pone el aviso de «sin PC» con la misma frase del resto de la cara.
  if (!await hayNucleo()) {
    caja.innerHTML = '<span class="ch-cargando ch-sinpc">' + esc(sinNucleoFrase()) + '</span>';
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
    caja.innerHTML = '<span class="ch-cargando ch-sinpc">no leí la lista de modelos: ' + esc(porque) + '</span>';
    return;
  }
  const bajados = (data.modelos || []).filter(m => m.descargado);
  if (!bajados.length) {
    caja.innerHTML = '<span class="ch-cargando">' + esc(enPC
      ? 'ningún modelo descargado todavía: bájalo en 10 · Modelos (flecha ↓)'
      : 'en el teléfono no hay modelos que bajar: viven en tu portátil. '
        + 'Con CORT abierto ahí, la charla ya usa el que tengas puesto.') + '</span>'
      + (enPC ? botonBajarModelos() : '');
    if (enPC) enganchaBajarModelos(caja);
    if (enTelefono()) avisaModelosEnPC();
    return;
  }
  caja.innerHTML = '<span class="ch-piego">modelos:</span>' + bajados.map(m =>
    `<button class="ch-mo${m.activo ? ' activa' : ''}" data-m="${esc(m.modelo)}">${esc(m.modelo)}</button>`).join('')
    + (enPC ? botonBajarModelos()
            : '<span class="ch-piego ch-nota">en el portátil: allí bajan y allí corren</span>');
  if (enPC) enganchaBajarModelos(caja);
  else avisaModelosEnPC();
  caja.querySelectorAll('.ch-mo').forEach(b => b.onclick = async () => {
    try {
      const r = await fetch(ctx.api() + '/api/models/use', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ modelo: b.dataset.m }),
      });
      const j = await r.json();
      ctx?.say?.(j.error ? 'No pude cambiar de modelo: ' + j.error : 'Usando ' + b.dataset.m + '.');
      caja.querySelectorAll('.ch-mo').forEach(o => o.classList.toggle('activa', o === b));
    } catch { ctx?.say?.('El núcleo no respondió el cambio de modelo.') }
  });
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
        body: JSON.stringify({ text: '[código] ' + editor.value }),
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
   duplicarlos sería tener dos transportes que un día mandan distinto. `extra` es lo
   que sólo aporta MV (mover también la imagen). */
const transporteHTML = p => `
    <div class="mu-barra" id="${p}-barra"><i id="${p}-prog"></i></div>
    <div class="mu-tiempos"><span id="${p}-t0">0:00</span><span id="${p}-t1">—</span></div>
    <div class="mu-transporte">
      <button id="${p}-prev" title="anterior">⏮</button>
      <button id="${p}-play" title="play / pausa">▶</button>
      <button id="${p}-next" title="siguiente">⏭</button>
      <button id="${p}-stop" title="parar del todo">⏹</button>
    </div>
    <div class="mu-fila2">
      <button id="${p}-gusta" class="mu-chip">👍 me gusta</button>
      <button id="${p}-no" class="mu-chip">👎 quítala</button>
      <button id="${p}-envia" class="mu-chip" title="enviar esta pista por WhatsApp, correo o lo que quieras">📤 enviar</button>
      <button id="${p}-cuadro-a" class="mu-chip" title="un fotograma atrás (±1/30 s en vídeo)">◂ cuadro</button>
      <button id="${p}-cuadro-b" class="mu-chip" title="un fotograma adelante (±1/30 s en vídeo)">cuadro ▸</button>
      <button id="${p}-auto" class="mu-chip">♪ ponme algo</button>
      <button id="${p}-juego" class="mu-chip" title="CORT se calla y no escucha mientras juegas">🎮 modo juego</button>
    </div>
    <div class="mu-volumen"><span>volumen</span><input id="${p}-vol" type="range" min="0" max="1" step=".05" value=".8"></div>`;

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

function montaMusica() {
  const cuerpo = document.querySelector('#scr-musica .scr-cuerpo');
  if (!cuerpo) return;
  cuerpo.innerHTML = `
    <div class="mu-ahora" id="mu-ahora">nada puesto</div>
    <div class="mu-datos"><span id="mu-artista"></span></div>
    ${transporteHTML('mu')}
    <div class="mu-lista-top">
      <input id="mu-busca" placeholder="busca título, artista o género…">
      <button id="mu-buscar">buscar</button>
      <button id="mu-gusto" title="las que mejor encajan con tus gustos">por gusto</button>
    </div>
    <div class="scr-lista mu-pistas" id="mu-pistas"></div>
    <div class="mu-playlists">
      <div class="mu-pl-top">
        <input id="mu-pl-nombre" placeholder="nombre de la lista">
        <button id="mu-pl-guarda">guardar la cola</button>
        <button id="mu-pl-refresca">mis listas</button>
      </div>
      <div class="mu-pl-caja" id="mu-pl-caja"></div>
      <div class="mu-perfil" id="mu-perfil"></div>
    </div>`;

  const q = cuerpo.querySelector('#mu-busca');
  enganchaTransporte(cuerpo, 'mu');
  cuerpo.querySelector('#mu-buscar').onclick = () => buscaMusica(q.value, false);
  q.addEventListener('keydown', e => { if (e.key === 'Enter') buscaMusica(q.value, false); });
  cuerpo.querySelector('#mu-gusto').onclick = () => buscaMusica(q.value, true);
  cuerpo.querySelector('#mu-pl-guarda').onclick = () => guardaLista();
  cuerpo.querySelector('#mu-pl-refresca').onclick = () => {
    document.querySelector('#scr-musica .scr-cuerpo').querySelector('#mu-pl-caja').textContent = ''; pintaListas();
  };
  pintaListas();
  perfil();
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
  let lista = [];
  try { lista = JSON.parse(crudo || '[]'); } catch { lista = []; }
  caja.innerHTML = '';
  if (!lista.length) {
    caja.innerHTML = '<div class="mu-vacio">nada con ese nombre · prueba con otra palabra o «por gusto»</div>';
    return;
  }
  const uris = lista.map(p => p.uri);
  lista.forEach((p, i) => {
    const d = document.createElement('div');
    d.className = 'mu-pista' + (p.video ? ' es-video' : '');
    d.innerHTML = `<span class="mu-ico">${p.video ? '▣' : '♪'}</span>
      <span class="mu-n">${esc(p.titulo)}</span>
      <span class="mu-a">${esc(p.artista)}${p.genero ? ' · ' + esc(p.genero) : ''}</span>`;
    d.onclick = () => {
      if (llama('musicaPoner', uris.join('\n'), i) === false) {
        ctx?.say?.('Esa pista no está en el índice: recarga la lista.');
        return;
      }
      ctx?.orb?.burst?.();
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
    <div class="mu-ahora" id="mv-ahora">nada puesto</div>
    <div class="mu-datos"><span id="mv-artista"></span></div>
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
  montaCarcasa();
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
