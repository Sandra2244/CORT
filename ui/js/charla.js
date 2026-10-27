/* ===== 01 · CHARLA: la pantalla donde se conversa con los modelos =====
 *
 * Tercer corte de la refactorización por tamaño (la regla de la dueña: «la interfaz debe
 * ser mil líneas máximo y si necesitas crear otros de otras líneas más conectas y divides
 * entre si pero que funcione correctamente»). Estos 856 líneas eran el sector «01 · CHARLA»
 * de `pantallas.js`, que había llegado a 3.035. Salen **tal cual**, sin reescribir ni una
 * coma de lo que hace: lo único nuevo son los `import` de arriba y los `export` de abajo.
 *
 * Con quién habla y por qué no forma círculo:
 *  · `marco.js` —el puente con Java, el `ctx` vivo, las bottom sheets, el portapapeles y
 *    la pregunta «¿hay núcleo?»—. Se importa, no se recibe: la Charla ya no es una
 *    función a la que le pasan el marco a mano.
 *  · `pantallas.js` —que la monta desde `initPantallas` y la registra con `alEntrar`—
 *    importa DE aquí, nunca al revés. Si la Charla importara la cara, los módulos ES
 *    dejarían `montaCharla` sin definir en el primer arranque.
 *  · El cajón se abre con `abreCajon()`, que está en el marco y repinta a través del
 *    gancho `alRepintar` que registró la carcasa: así el botón ☰ de esta hoja no necesita
 *    saber quién pinta el cajón.
 *
 * Lo que sigue midiéndose aquí, sin cambio: los modos de entrada (`CH_MODOS`), el manto
 * Jarvis (`aplicaManto`), el adjunto, las notas, el historial del portátil, los modelos
 * de `/api/models` y el corte honesto cuando no hay núcleo. `scripts/prueba-md.mjs` sigue
 * comprobando el markdown y la hora; `scripts/prueba-manto.mjs`, la ropa.
 */

import { esc } from './texto.js';
import { md, horaDe } from './md.js';
import { clasificarOrden } from './ordenes.js';
import {
  enTelefono, puede, llama, ctx, nucleo,
  abreHoja, cierraHoja,
  hayNucleo, sinNucleoFrase, avisaSinNucleo,
  copia, abreCajon,
} from './marco.js';

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
  const habiaAdjunto = !!chAdj;
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
  /* ─── J2.1 · la regla de la superficie A: orden → `/api/command`, charla → `/api/chat` ───
     Hasta aquí TODO se iba al cerebro y las órdenes quedaban sin manos. Si la frase casa
     con el vocabulario del ejecutor (`ordenes.js`, espejo de `actions.py`), la manda a
     `POST /api/command`, que responde `{reply, source, done:[acciones]}`; la burbuja
     enseña `hecho:` SOLO con lo que el núcleo trajo en `done` — si volvió vacío, la cara
     no inventa acciones. Con adjunto o con modo elegido, la frase sigue siendo charla:
     ahí lo que ella pidió es análisis, no ejecutar. */
  const orden = modo.id === 'normal' && !habiaAdjunto ? clasificarOrden(pregunta) : null;
  if (orden && orden.ruta === 'orden') {
    jmEstado('ejecutando: ' + orden.accion + '…');
    try {
      const r = await fetch(ctx.api() + '/api/command', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ message: pregunta }),
      });
      const j = await r.json();
      const hecho = Array.isArray(j.done) ? j.done.filter(Boolean) : [];
      const dicho = j.reply || j.error || 'No supe qué contestar.';
      mensajes.push({ de: 'cort', texto: String(dicho), fuente: j.source || '', hecho,
                      nota: hecho.length ? 'ejecutor · ' + hecho.join(' · ')
                                         : 'cerebro ' + (j.source || 'local'),
                      hora: Date.now() });
      chPensando = false;
      /* El aviso del estado se decide con la palabra del núcleo, no con la nuestra:
         una orden que volvió `done:['carpeta']` pero cuyo texto dice «No pude»
         también pinta el estado en ámbar. Lo que falló se dice fallando. */
      const falló = /no pude|no hay|no encontr|fallo|error/i.test(String(dicho));
      /* Misma regla que la charla: una orden cumplida por el ejecutor no la pensó
         ningún modelo, así que la placa tiene que dejar de nombrarlo. */
      ctx?.placa?.({ modelo: /casa|nube|local/i.test(String(j.source || '')) ? (chModelo || '') : '' });
      jmEstado(hecho.length ? (falló ? 'intentó: ' + hecho.join(' · ')
                                     : 'hizo: ' + hecho.join(' · '))
                            : 'cerebro ' + (j.source || 'local'), falló);
      ctx?.orb?.burst?.();
    } catch (e) {
      mensajes.push({ de: 'cort', texto: 'El núcleo se cayó a media orden: ' + e,
                      nota: 'el núcleo se cayó', hora: Date.now() });
      chPensando = false;
      jmEstado('sin núcleo', true);
      nucleo = null;   // mismo trato que la charla: el «sí hay» guardado dejó de ser cierto
    }
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
    /* La placa de arriba (1.3) dice con qué se contestó, y aquí está la trampa que
       cazó la vista previa: `chModelo` trae el modelo SELECCIONADO (qwen2.5:0.5b), no
       el que habló. Si la respuesta salió `offline` o del `ejecutor`, ningún modelo
       pensó —poner el elegido era inventarse una respuesta, lo mismo que el paso 1.3
       prohibe—. Se pinta el nombre SÓLO cuando la fuente es de modelo (casa / nube /
       local), y se LIMPIA con un '' en cualquier otro caso para que la placa deje de
       reclamar un modelo que ya no contestó. */
    const fuente = String(j.source || '');
    ctx?.placa?.({ modelo: (chModelo && /casa|nube|local/i.test(fuente)) ? chModelo : '' });
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
  // J2.1 · el chip «qué hizo», poblado sólo con el `done` que devolvió el ejecutor.
  if (Array.isArray(m.hecho) && m.hecho.length) {
    pies.push(`<span class="bur-hecho">hizo: ${esc(m.hecho.join(' · '))}</span>`);
  }
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


/* La superficie real de este archivo: lo único que necesita `pantallas.js`.
   `montaCharla()` construye la hoja; las tres siguientes son lo que hace el registro de
   entrada `alEntrar('charla', …)` cuando la dueña llega aquí; `escuchaMente()` se engancha
   una sola vez, en el arranque. `charla(texto)` —la puerta por la que entra una frase— no
   se exporta: sólo la llaman el botón Enviar, la tecla Enter y el propio historial de esta
   hoja, y quien quiere hablar con CORT usa el `send()` de `hud.js`. */
export { montaCharla, pintaCharla, cargaModelos, traeHistorial, escuchaMente };
