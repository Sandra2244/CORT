/* ===== HUD de CORT: arranque, ventanas, chat, sensores, voz y gestos ===== */
import { createWin } from './windows.js';
import { createVoice, perms } from './voice.js';

// Dónde está el núcleo de CORT. En Android la pantalla la sirve el propio
// backend (mismo origen, API = ''), en el navegador de PC vive en :8000
// mientras la interfaz va en :8080, y en el instalador de escritorio puede
// estar en cualquier puerto — por eso `discoverApi()` lo confirma consultando
// /api/port antes de usarlo.
const IS_ANDROID = !!window.CortNative;
let API = IS_ANDROID ? ''
  : (navigator.userAgent.includes('Electron') ? 'http://127.0.0.1:8000'
    : location.port === '8080' ? 'http://127.0.0.1:8000' : '');
const CANDIDATES = [
  API, '', `http://127.0.0.1:${location.port}`, 'http://127.0.0.1:8000',
  'http://localhost:8000', 'http://127.0.0.1:8081',
].filter((u, i, a) => a.indexOf(u) === i);

async function discoverApi() {
  // en el instalador de escritorio el backend arranca a la vez que la pantalla:
  // si la primera ronda falla, se intenta unas cuantas veces más sin congelar nada
  for (let intento = 0; intento < 4; intento++) {
    const tried = [];
    for (const base of CANDIDATES) {
      try {
        const r = await fetch(base + '/api/port', { signal: AbortSignal.timeout(1600) });
        if (!r.ok) continue;
        const j = await r.json();
        API = base;
        term('núcleo localizado en ' + (j.base || base || 'este origen'), 'arranque');
        return true;
      } catch (e) { tried.push(base || location.origin); }
    }
    if (intento < 3) {
      term('el núcleo aún despierta… reintento ' + (intento + 2) + ' de 4', 'arranque');
      await new Promise(r => setTimeout(r, 700));
    }
  }
  return false;
}
const mobile = () => window.isMobileHUD && window.isMobileHUD();
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
let orb, voice;

/* ---------- secuencia de arranque ---------- */
const BOOT_LINES = [
  ['CORT BIOS v0.2 ......................... ', 'OK'],
  ['Núcleo holográfico (WebGL) ............. ', 'OK'],
  ['Matriz de partículas: 2600 puntos ...... ', 'OK'],
  ['Enlace con backend local (127.0.0.1) ... ', null],
  ['Cerebro híbrido: local/online .......... ', null],
  ['Ejecutor de acciones del sistema ....... ', null],
  ['Oído y voz (reconocimiento nativo) ..... ', null],
  ['Memoria persistente (SQLite) ........... ', null],
  ['Sensor de gestos (MediaPipe ligero) .... ', 'LISTO'],
  ['Desplegando ventanas de vidrio …', ''],
];
async function runBoot() {
  const boot = document.getElementById('boot');
  let backendOK = false, brainTxt = '—', where = '';
  // se localiza el núcleo MIENTRAS se dibujan las líneas (no retrasa el arranque)
  const finding = discoverApi().then(async ok => {
    if (!ok) return null;
    try {
      const s = await (await fetch(API + '/api/status')).json();
      return { s, where: API || location.origin };
    } catch { return null; }
  });
  let found = false, s = null;
  for (const [txt, fixed] of BOOT_LINES) {
    const div = document.createElement('div'); div.className = 'line';
    let val = fixed;
    if (fixed === null) {
      if (!found) {                            // se resuelve una sola vez
        found = true;
        const r = await finding;
        s = r && r.s; backendOK = !!s; where = (r && r.where) || '';
        if (s && s.version) {
          const v = document.getElementById('hudver');
          if (v) v.textContent = 'v' + s.version;
        }
      }
      if (txt.includes('backend')) {
        val = backendOK ? (where ? 'OK · ' + where.replace(/^https?:\/\//, '') : 'OK')
                        : 'SIN CONEXIÓN';
      }
      if (txt.includes('híbrido')) {
        if (s) {
          const b = s.brain;
          brainTxt = [b.ollama && 'local', (b.groq || b.gemini) && 'online',
            (!b.ollama && !b.groq && !b.gemini) && 'offline'].filter(Boolean).join('+');
        }
        val = brainTxt;
      }
      if (txt.includes('Acciones')) val = backendOK ? 'OK' : 'EN PAUSA';
      if (txt.includes('Oído')) val = voice && voice.available ? 'OK' : 'NO DISPONIBLE';
      if (txt.includes('Memoria')) val = backendOK ? 'OK' : 'EN PAUSA';
    }
    div.innerHTML = txt + (val ? `<span class="${String(val).startsWith('OK') ? 'ok' : ''}">[${val}]</span>` : '');
    boot.appendChild(div);
    await new Promise(r => setTimeout(r, 140 + Math.random() * 130));
  }
  await new Promise(r => setTimeout(r, 300));
  boot.classList.add('done'); setTimeout(() => boot.remove(), 900);
  return { backendOK, brainTxt, where };
}

/* ---------- ventanas de vidrio (paneles numerados estilo referencia) ---------- */
let W = {};
function buildWindows() {
  const vw = innerWidth, vh = innerHeight;
  const clamp = (v, min, max) => Math.max(min, Math.min(max, v));   // que nunca se salgan de pantalla
  W.files = createWin({ id: 'files', icon: ic('folder'), title: '01 · Archivos · <span id="fpath">raíces</span>',
    x: 14, y: 112, w: Math.min(292, vw - 28), h: clamp(vh * .42, 200, 300),
    html: `<div id="ftools"><button id="fgrid" title="vista de mosaico">${ic('grid')}</button><button id="flistbtn" title="vista de lista">${ic('list')}</button></div><div id="flist"></div>` });
  W.env = createWin({ id: 'env', onShow: () => { refreshStatus(); refreshWeather(); }, icon: '◉', title: '02 · Entorno',
    x: 14, y: clamp(112 + vh * .42 + 18, 330, 440), w: Math.min(240, vw - 28),
    html: `<div id="wx">…</div>
      <div style="margin-top:8px;font-size:10px;color:#5e8cab">CPU</div><div class="bar"><i id="bar-cpu" style="width:0"></i></div>
      <div style="font-size:10px;color:#5e8cab">RAM <span id="ramgb"></span></div><div class="bar"><i id="bar-ram" style="width:0"></i></div>
      <div style="font-size:10px;color:#5e8cab">DISCO</div><div class="bar"><i id="bar-disk" style="width:0"></i></div>
      <div id="batt" style="margin-top:6px;font-size:11px"></div>
      <div id="envbrain"></div>` });
  W.chat = createWin({ id: 'chat', icon: '✦', title: '03 · Canal de voz',
    x: Math.max(14, Math.round(vw / 2) - 190), y: Math.max(140, vh - 386), w: Math.min(380, vw - 28), h: 288,
    html: `<div id="log"></div>
      <div id="inputrow"><span id="prompt" title="↑/↓ historial · Tab completa">cort@nave:~$</span>
      <input id="q" placeholder="escribe aquí o toca el micrófono…" autocomplete="off" enterkeyhint="send">
      <button id="go" aria-label="Enviar">${ic('send')}<span>Enviar</span></button></div>` });
  W.notes = createWin({ id: 'notes', onShow: () => refreshNotes(), icon: '✎', title: '04 · Notas',
    x: Math.round(vw / 2) - 170, y: 118, w: Math.min(340, vw - 28), h: 300,
    html: `<div id="notelist"></div>
      <div id="inputrow"><input id="nota" placeholder="Nueva nota…" autocomplete="off">
      <button id="notago" aria-label="Agregar nota">${ic('plus')}</button></div>` });
  W.music = createWin({ id: 'music', onShow: () => { if (!tracks.length) loadMusic(); }, icon: '♪', title: '05 · Música',
    x: clamp(vw - 530, 14, vw - 240), y: clamp(vh - 406, 112, 348), w: Math.min(302, vw - 28), h: clamp(vh * .5, 220, 392),
    html: `<div id="nowplay">— sin reproducción —</div>
      <div id="mbar"><i id="mprog"></i></div>
      <div id="mrow"><button id="mprev">${ic('prev')}</button><button id="mplay">${ic('play')}</button>
        <button id="mnext">${ic('next')}</button><input id="mvol" type="range" min="0" max="1" step=".02" value=".8">
        <span id="mtime"></span><button id="mref" title="recargar lista">${ic('refresh')}</button></div>
      <div id="plist"></div>
      <audio id="aud" crossorigin="anonymous"></audio>` });
  W.term = createWin({ id: 'term', icon: '▤', title: '06 · Consola del sistema',
    x: 14, y: Math.max(140, vh - 268), w: Math.min(340, vw - 28), h: 240,
    html: '<div id="termlog"></div>' });
  W.perfil = createWin({ id: 'perfil', icon: ic('gear'), title: '07 · Perfil',
    x: Math.round(vw / 2) - 150, y: 140, w: 300,
    html: `<label class="pf">Nombre del asistente</label><input class="pf" id="pf-asistente" placeholder="CORT">
      <label class="pf">Tu nombre</label><input class="pf" id="pf-usuario" placeholder="Sandra">
      <label class="pf">Tono</label><select class="pf" id="pf-tono">
        <option value="">(el de siempre: JARVIS elegante)</option>
        <option value="formal y técnico">Formal y técnico</option>
        <option value="cercano y desenfadado">Cercano y desenfadado</option>
        <option value="muy breve, una frase">Muy breve</option></select>
      <label class="pf">Idioma</label><select class="pf" id="pf-idioma">
        <option value="">Español (es-MX)</option>
        <option value="inglés">English</option>
        <option value="portugués">Português</option></select>
      <div class="pf-sec">▸ Segundo plano</div>
      <div id="bgbox">
        <button id="bgtoggle" class="bg-toggle"><span class="sw"></span><b>Escuchar con la app cerrada</b></button>
        <div class="bg-help">Di <b>«Oye CORT, abre WhatsApp y pon música»</b> aunque estés en otra app.
          Android muestra un aviso fijo mientras escucha.</div>
        <div id="bgperms"></div>
        <label class="bg-check"><input type="checkbox" id="bgbeeps"> Dejar sonar el pitido al escuchar</label>
      </div>
      <div class="pf-sec">▸ Voz de CORT</div>
      <label class="pf">Voz</label><select class="pf" id="pf-voz"><option value="">(automática: masculina, estilo JARVIS)</option></select>
      <label class="pf">Tono de voz <span id="pf-voz_tono-v"></span></label>
      <input class="pf" id="pf-voz_tono" type="range" min="0.5" max="1.5" step="0.02" value="0.82">
      <label class="pf">Velocidad <span id="pf-voz_velocidad-v"></span></label>
      <input class="pf" id="pf-voz_velocidad" type="range" min="0.6" max="1.6" step="0.02" value="1">
      <button id="pfprobar" class="pf-btn ghost">${ic('play')} Probar voz</button>
      <div class="pf-sec">▸ Cerebro IA</div>
      <label class="pf">Modo</label><select class="pf" id="cf-mode">
        <option value="auto">Automático (local → online → offline)</option>
        <option value="online">Solo online (Groq / Gemini)</option>
        <option value="local">Solo local (Ollama)</option>
        <option value="offline">Sin IA (comandos locales)</option></select>
      <label class="pf">Clave Groq <a class="pf-link" data-href="https://console.groq.com/keys">gratis aquí</a></label>
      <input class="pf" id="cf-groq_key" placeholder="gsk_…" autocomplete="off" spellcheck="false">
      <label class="pf">Clave Gemini <a class="pf-link" data-href="https://aistudio.google.com/apikey">gratis aquí</a></label>
      <input class="pf" id="cf-gemini_key" placeholder="AIza…" autocomplete="off" spellcheck="false">
      <label class="pf">Ollama (Termux o tu PC en el Wi-Fi)</label>
      <input class="pf" id="cf-ollama_url" placeholder="http://127.0.0.1:11434" autocomplete="off" spellcheck="false">
      <label class="pf">Modelo Ollama</label>
      <input class="pf" id="cf-ollama_model" placeholder="qwen2.5:3b" autocomplete="off" spellcheck="false">
      <button id="pftest" class="pf-btn ghost">${ic('brain')} Probar cerebro</button>
      <div id="pftestout"></div>
      <div class="pf-msg" id="pf-datos"></div>
      <div class="pf-save"><button id="pfguardar" class="pf-btn">Guardar perfil</button>
      <div id="pfmsg" class="pf-msg"></div></div>` });
  /* muro de recuerdos — la "sala de cuadros" de la referencia, en azul */
  W.cerebro = createWin({ id: 'cerebro', onShow: () => refreshMemories(), icon: '⌗', title: '08 · Cerebro · <span id="memcount">…</span>',
    x: clamp(Math.round(vw / 2) - 220, 14, Math.max(14, vw - 260)), y: 124,
    w: Math.min(440, vw - 28), h: clamp(vh * .56, 260, 420),
    html: '<div id="memwall"></div>' });
  /* ayuda viva: órdenes, atajos y soporte (los correos llegan del backend) */
  W.ayuda = createWin({ id: 'ayuda', onShow: refreshHelp, icon: ic('help'), title: '09 · Ayuda y soporte',
    x: clamp(Math.round(vw / 2) - 190, 14, Math.max(14, vw - 250)), y: 132,
    w: Math.min(380, vw - 28), h: clamp(vh * .62, 260, 430),
    html: `<div class="hp-sec">▸ Cómo hablarle</div>
      <div class="hp-txt">Escribe (o dicta) abajo y pulsa ⏎. <b>↑/↓</b> recuperan lo que
        ya dijiste y <b>Tab</b> completa el comando.</div>
      <div id="hpcmds"></div>
      <div class="hp-sec">▸ Atajos del holograma</div>
      <ul class="hp-keys">
        <li><b>Tab</b> completar comando</li><li><b>↑ / ↓</b> historial</li>
        <li><b>Enter</b> enviar</li><li><b>Esc</b> ocultar / mostrar el HUD</li>
        <li><b>arrastrar</b> la barra superior mueve la ventana</li>
        <li><b>doble clic</b> en la barra la minimiza al dock</li>
        <li><b>arrastrar</b> un chip lo coloca donde quieras</li>
      </ul>
      <div class="hp-sec">▸ Dónde está cada cosa</div>
      <ul class="hp-keys">
        <li><b>01–06</b> archivos, entorno, canal, notas, música y consola</li>
        <li><b>07 · Perfil</b> tu nombre, la voz de CORT y las claves del cerebro</li>
        <li><b>08 · Cerebro</b> el muro de recuerdos (notas + charlas, en SQLite)</li>
        <li><b>10 · Modelos</b> baja modelos de Ollama y ve cuáles caben en tu RAM</li>
        <li><b>11 · Optimizar</b> qué come memoria y cuánta caché se puede borrar</li>
        <li><b>🎙</b> una orden · <b>👂</b> escucha «Oye CORT» · <b>✋</b> gestos con la mano</li>
      </ul>
      <div class="hp-sec">▸ Soporte y contacto</div>
      <div id="hpsup">cargando…</div>` });

  /* 10 · modelos locales: catálogo de Ollama con flechas de descarga y
     el veredicto de RAM para ESTE equipo */
  const sep = vw >= 920 ? 250 : 0;   // en pantallas anchas van una al lado de la otra
  W.modelos = createWin({ id: 'modelos', onShow: refreshModels, icon: ic('download'),
    title: '10 · Modelos · <span id="molstate">…</span>',
    x: clamp(Math.round(vw / 2) - 210 - sep, 14, Math.max(14, vw - 260)), y: 118,
    w: Math.min(420, vw - 28), h: clamp(vh * .64, 260, 440),
    html: `<div id="mohead" class="mo-head">consultando el equipo…</div>
      <div id="molist"></div>` });

  /* 11 · optimización: quién come la RAM y cuánta caché se puede barrer */
  W.optimiza = createWin({ id: 'optimiza', onShow: refreshOptimize, icon: ic('gauge'),
    title: '11 · Optimización · <span id="optram">…</span>',
    x: clamp(Math.round(vw / 2) - 200 + sep, 14, Math.max(14, vw - 250)), y: 126,
    w: Math.min(400, vw - 28), h: clamp(vh * .62, 260, 430),
    html: `<div id="optr"><div class="mo-none">Pulsa «Analizar» para ver qué está comiendo
      la memoria y cuánta caché sobra.</div></div>` });
}

/* ---------- ejecutor de música (orbe → disco giratorio) ---------- */
let tracks = [], tIdx = -1, AC = null, AN = null, freqData = null, mAnim = 0;
async function loadMusic() {
  const el = document.getElementById('plist');
  try {
    const r = await (await fetch(API + '/api/music')).json();
    tracks = r.canciones || [];
    if (r.needPermission) { el.innerHTML = ''; el.appendChild(permRow('music', 'CORT necesita permiso para ver tu música', loadMusic)); return; }
    el.innerHTML = tracks.length ? '' :
      '<div class="row">no encontré canciones en el teléfono · pulsa recargar</div>';
    tracks.forEach((t, i) => {
      const d = document.createElement('div'); d.className = 'row track';
      d.innerHTML = `<span>♪ ${esc(t.nombre)}</span><span class="fecha">${esc(t.artista)}${t.dur ? ' · ' + esc(t.dur) : ''}</span>`;
      d.onclick = () => playTrack(i);
      el.appendChild(d);
    });
  } catch { el.innerHTML = '<div class="row">backend no disponible</div>'; }
}
function playTrack(i) {
  if (i < 0 || i >= tracks.length) return;
  tIdx = i;
  const aud = document.getElementById('aud');
  const k = (document.cookie.match(/(?:^|;\s*)cort=([^;]+)/) || [])[1];
  aud.src = API + '/api/audio?ruta=' + encodeURIComponent(tracks[i].ruta) + (k ? '&k=' + k : '');
  aud.play().catch(() => {});
  document.getElementById('nowplay').textContent = '♪ ' + tracks[i].nombre;
  document.getElementById('mplay').innerHTML = ic('pause');
  document.querySelectorAll('#plist .track').forEach((d, j) => d.classList.toggle('playing', j === i));
  W.music.show();
  orb.setDisc(true);                       // ¡el orbe se dispersa en disco que gira!
  ensureAnalyser(aud);
  term('reproduciendo: ' + tracks[i].nombre, 'música');
  startMeter(aud);
}
function togglePlay() {
  const aud = document.getElementById('aud');
  if (tIdx < 0) { if (tracks.length) playTrack(0); return; }
  if (aud.paused) { aud.play().catch(() => {}); document.getElementById('mplay').innerHTML = ic('pause'); orb.setDisc(true); startMeter(aud); }
  else { aud.pause(); document.getElementById('mplay').innerHTML = ic('play'); orb.setDisc(false); stopMeter(); }
}
function pauseMusic() {
  const aud = document.getElementById('aud');
  if (!aud.paused) togglePlay();
}
function resumeMusic() {
  const aud = document.getElementById('aud');
  if (aud.paused) togglePlay();
}

/* ---------- MODO OFICINA (video f7d16b9e: "JARVIS MODE BUREAU") ----------
   Las ventanas abiertas se recolocan solas en 2 niveles, con deslizamiento. */
function organizeBureau() {
  const open = Object.values(W).filter(w => w.open && !w.minimized);
  if (!open.length) return 0;
  const vw = innerWidth, vh = innerHeight;
  const half = Math.ceil(open.length / 2);
  const rows = [open.slice(0, half), open.slice(half)].filter(r => r.length);
  rows.forEach((row, ri) => {
    const gap = 12, top = ri ? Math.round(vh / 2) + 16 : 108;
    const cellW = Math.floor((vw - gap * (row.length + 1)) / row.length);
    row.forEach((w, i) => {
      w.el.classList.add('snap');
      w.el.style.left = Math.max(8, gap + i * (cellW + gap)) + 'px';
      w.el.style.top = top + 'px';
      setTimeout(() => w.el.classList.remove('snap'), 700);
    });
  });
  return open.length;
}

/* ---------- ÁRBOL DEL SISTEMA (columna persistente estilo Jared) ----------
   Filas `▸ 00 — NOMBRE` con sublínea «N carpetas · M archivos». Al tocar una
   se EXPANDE en su sitio (▾) y sus subcarpetas salen volando como chips,
   igual que cuando Jared abre DAILY NOTES y le llueven los meses. */
const openBranch = new Set();
async function refreshTree() {
  const el = document.getElementById('treebody');
  try {
    const r = await (await fetch(API + '/api/files')).json();
    el.innerHTML = '';
    if (r.needPermission) { el.appendChild(permRow('files', 'permiso de archivos', refreshTree)); return; }
    (r.entries || []).forEach((e, i) => el.appendChild(treeRow(e, i)));
    for (const root of [...openBranch]) {
      const row = el.querySelector(`[data-root="${CSS.escape(root)}"]`);
      if (row) expandBranch(row, root, true);
    }
  } catch { el.innerHTML = '<div class="trow"><b>backend no disponible</b></div>'; }
}
function treeRow(e, i) {
  const d = document.createElement('div');
  d.className = 'trow'; d.dataset.root = e.name;
  const nf = e.folders ?? 0, nx = e.files ?? 0;
  d.innerHTML = `<b>${String(i).padStart(2, '0')} — ${esc(e.name)}</b>
    <small>${nf} ${nf === 1 ? 'carpeta' : 'carpetas'} · ${nx} ${nx === 1 ? 'archivo' : 'archivos'}</small>`;
  d.onclick = () => expandBranch(d, e.name);
  return d;
}
async function expandBranch(row, root, silent = false) {
  const id = 'br-' + root;
  const old = document.getElementById(id);
  if (old) { old.remove(); row.classList.remove('open'); openBranch.delete(root); return; }
  row.classList.add('open'); openBranch.add(root);
  const r = await (await fetch(API + '/api/tree?path=' + encodeURIComponent(root))).json();
  if (r.error) { term('árbol: ' + r.error, 'error'); return; }
  const box = document.createElement('div'); box.id = id; box.className = 'branch';
  (r.children || []).forEach((c, i) => {
    const k = document.createElement('div'); k.className = 'trow kid';
    k.innerHTML = `<b>${String(i).padStart(2, '0')} — ${esc(c.name)}</b>
      <small>${c.folders} carpetas · ${c.files} archivos</small>`;
    k.onclick = ev => { ev.stopPropagation(); W.files.show(); openFiles(c.path); };
    box.appendChild(k);
  });
  row.after(box);
  if (!silent && (r.children || []).length) {
    spawnChips(r.children.map(c => ({
      txt: c.name, meta: `${c.folders + c.files} elementos · ${root}`,
      act: () => { W.files.show(); openFiles(c.path); } })), row);
    term('árbol: ' + root + ' desplegada → ' + r.children.length + ' subcarpetas', 'archivos');
  }
}

/* ---------- OCULTAR / MOSTRAR todo (el HUD desaparece como en el video) ---------- */
let lastOpen = [];
function hideAll() {
  lastOpen = Object.values(W).filter(w => w.open && !w.minimized).map(w => w.id);
  Object.values(W).forEach(w => w.close());
  clearChips(); setState('oculto');
  term('HUD oculto — solo el orbe', 'ventanas');
}
function showAll() {
  const ids = lastOpen.length ? lastOpen : Object.keys(W);
  ids.forEach(id => W[id] && W[id].show());
  setState('listo');
  term('ventanas restauradas: ' + ids.join(', '), 'ventanas');
}

/* ---------- CHIPS FLOTANTES: CORT te "lanza a las manos" notas y archivos ----------
   En la referencia los chips NO se borren solos: quedan flotando y se agarran
   con la mano. Aquí: persistentes, arrastrables, con ✕ propio y tope de 14. */
const cl = (v, a, b) => Math.max(a, Math.min(b, v));
function spawnChips(items, anchor) {
  const layer = document.getElementById('chips');
  const mob = mobile(), MAXC = mob ? 4 : 8, CAP = mob ? 6 : 14;
  items = items.slice(0, MAXC);
  while (layer.children.length + items.length > CAP) layer.firstChild.remove();
  const a = anchor ? anchor.getBoundingClientRect()
                   : { left: innerWidth * .42, top: innerHeight * .38, width: 120, height: 28 };
  const n = items.length;
  items.forEach((it, i) => {
    const c = document.createElement('div'); c.className = 'chip';
    c.innerHTML = `<b>${String(it.txt).replace(/</g, '&lt;')}</b>
      <small>${String(it.meta || '').replace(/</g, '&lt;')}</small><span class="x">✕</span>`;
    const ang = (i / n) * Math.PI * 2 + Math.random() * .9;
    const rad = 150 + Math.random() * 100;
    if (mob) {
      // celular: los chips flotan en la franja del orbe, por encima de la hoja
      const band = Math.max(150, innerHeight * .34 - 150);
      c.style.left = cl(Math.round(10 + (i % 2) * innerWidth * .44 + Math.random() * 14), 8, innerWidth - 196) + 'px';
      const row = Math.floor(i / 2), step = Math.min(56, (band - 84) / Math.max(1, Math.ceil(n / 2) - 1));
      c.style.top = Math.round(84 + row * step + (i % 2) * 22 + Math.random() * 8) + 'px';
    } else {
      c.style.left = cl(Math.round(a.left + a.width / 2 + Math.cos(ang) * rad - 70), 12, innerWidth - 210) + 'px';
      c.style.top = cl(Math.round(a.top + a.height / 2 + Math.sin(ang) * rad * .62 - 18), 92, innerHeight - 200) + 'px';
    }
    c.style.animationDelay = (i * .35) + 's';
    c.querySelector('.x').onclick = ev => { ev.stopPropagation(); gone(c); };
    dragChip(c);
    c.onclick = () => { if (!c.dataset.moved) { it.act && it.act(); } delete c.dataset.moved; };
    layer.appendChild(c);
  });
}
function dragChip(c) {
  let sx = 0, sy = 0, ox = 0, oy = 0, held = false;
  c.addEventListener('pointerdown', e => {
    if (e.target.classList.contains('x')) return;
    held = true; c.classList.add('held');
    sx = e.clientX; sy = e.clientY;
    ox = parseFloat(c.style.left); oy = parseFloat(c.style.top);
    c.setPointerCapture(e.pointerId);
  });
  c.addEventListener('pointermove', e => {
    if (!held) return;
    const dx = e.clientX - sx, dy = e.clientY - sy;
    if (Math.abs(dx) + Math.abs(dy) > 6) c.dataset.moved = '1';
    c.style.left = cl(ox + dx, 6, innerWidth - 200) + 'px';
    c.style.top = cl(oy + dy, 88, innerHeight - 120) + 'px';
  });
  const up = () => { held = false; c.classList.remove('held'); };
  c.addEventListener('pointerup', up); c.addEventListener('pointercancel', up);
}
function gone(c) { c.classList.add('gone'); setTimeout(() => c.remove(), 700); }
function clearChips() { document.querySelectorAll('#chips .chip').forEach(c => gone(c)); }
async function chipNotes() {
  const ns = await (await fetch(API + '/api/notes')).json();
  if (!ns.length) { sayLine('Aún no hay notas: dime «apunta …».'); return; }
  spawnChips(ns.slice(mobile() ? -2 : -5).reverse().map(x => ({
    txt: x.texto.slice(0, 30), meta: x.fecha.slice(5, 10) + ' · nota',
    act: () => { W.notes.show(); sayLine('Nota: ' + x.texto); } })));
  term('chips de notas lanzados: ' + Math.min(5, ns.length), 'notas');
}
async function chipRecentFiles() {
  let r = await (await fetch(API + '/api/files?path=Documentos')).json();
  if (r.needPermission) { sayLine('Necesito permiso para ver tus archivos. Te abro el ajuste.'); perms.ask('files'); return; }
  let base = 'Documentos';
  let fs = (r.entries || []).filter(e => e.type === 'file');
  if (!fs.length) { base = 'Descargas'; r = await (await fetch(API + '/api/files?path=Descargas')).json(); fs = (r.entries || []).filter(e => e.type === 'file'); }
  fs = fs.sort((a, b) => (b.fecha || '').localeCompare(a.fecha || '')).slice(0, 5);
  if (!fs.length) { sayLine('No encontré archivos recientes en Documentos ni en Descargas.'); return; }
  spawnChips(fs.map(e => ({ txt: e.name, meta: e.fecha.slice(0, 10) + ' · ' + base,
    act: () => openFile(base + '/' + e.name, e.name) })));
  term('chips de archivos lanzados: ' + fs.length, 'archivos');
}
function ensureAnalyser(aud) {
  if (AC) return;
  try {
    AC = new (window.AudioContext || window.webkitAudioContext)();
    const src = AC.createMediaElementSource(aud);
    AN = AC.createAnalyser(); AN.fftSize = 256; AN.smoothingTimeConstant = .78;
    src.connect(AN); AN.connect(AC.destination);
    freqData = new Uint8Array(AN.frequencyBinCount);
  } catch { AN = null; }
}
function startMeter(aud) {
  stopMeter();
  const step = () => {
    if (AN && !aud.paused) {
      AN.getByteFrequencyData(freqData);
      let bass = 0; for (let i = 1; i < 8; i++) bass += freqData[i]; bass /= 7 * 255;
      let lvl = 0; for (let i = 0; i < 64; i++) lvl += freqData[i]; lvl /= 64 * 255;
      orb.setAudio(lvl, Math.min(1, bass * 1.6));
    }
    const pr = document.getElementById('mprog'), tm = document.getElementById('mtime');
    if (aud.duration) {
      pr.style.width = (aud.currentTime / aud.duration * 100) + '%';
      tm.textContent = fmt(aud.currentTime) + ' / ' + fmt(aud.duration);
    }
    mAnim = requestAnimationFrame(step);
  };
  mAnim = requestAnimationFrame(step);
}
function stopMeter() { cancelAnimationFrame(mAnim); orb.setAudio(0, 0); }
const fmt = s => Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0');

/* ---------- consola del sistema (log estilo JARVIS) ---------- */
function term(txt, tag = 'sistema') {
  const el = document.getElementById('termlog');
  if (!el) return;
  const d = document.createElement('div');
  d.className = 'tl';
  const hh = new Date().toLocaleTimeString('es-MX', { hour12: false });
  d.innerHTML = `<span class="ts">${hh}</span> <span class="tg">${esc(tag)}</span> ${esc(txt)}`;
  el.appendChild(d);
  while (el.children.length > 120) el.firstChild.remove();
  el.scrollTop = el.scrollHeight;
}

/* ---------- notas ---------- */
async function refreshNotes() {
  const el = document.getElementById('notelist');
  try {
    const ns = await (await fetch(API + '/api/notes')).json();
    el.innerHTML = ns.length ? '' : '<div class="row">sin notas — escribe abajo</div>';
    ns.slice().reverse().forEach(n => {
      const d = document.createElement('div'); d.className = 'row nota';
      d.innerHTML = `<span class="ntxt">${n.texto.replace(/</g, '&lt;')}</span>
        <span class="fecha">${n.fecha.slice(5)}</span> <span class="del" title="borrar">✕</span>`;
      d.querySelector('.del').onclick = async () => {
        await fetch(API + '/api/notes/' + n.id, { method: 'DELETE' });
        term('nota #' + n.id + ' eliminada', 'notas'); refreshNotes();
      };
      el.appendChild(d);
    });
  } catch { el.innerHTML = '<div class="row">backend no disponible</div>'; }
}
async function addNote() {
  const inp = document.getElementById('nota');
  const t = inp.value.trim(); if (!t) return;
  inp.value = '';
  await fetch(API + '/api/notes', { method: 'POST',
    headers: { 'content-type': 'application/json' }, body: JSON.stringify({ texto: t }) });
  term('nota registrada: "' + t.slice(0, 32) + '"', 'notas');
  orb.burst(); refreshNotes();
}

/* ---------- perfil (+ voz de CORT + cerebro IA) ---------- */
const PF_KEYS = ['asistente', 'usuario', 'tono', 'idioma', 'voz', 'voz_tono', 'voz_velocidad'];
const CF_KEYS = ['mode', 'groq_key', 'gemini_key', 'ollama_url', 'ollama_model'];
function fillVoices(selected) {
  const sel = document.getElementById('pf-voz');
  const { voices = [], default: def = '' } = voice.voices() || {};
  sel.innerHTML = `<option value="">(automática${def ? ': ' + esc(def) : ''})</option>` +
    voices.slice().sort((a, b) => (b.male - a.male) || a.name.localeCompare(b.name)).map(v =>
      `<option value="${esc(v.name)}">${v.male ? '[M] ' : ''}${esc(v.name)} · ${esc(v.locale)}${v.local ? '' : ' (red)'}</option>`).join('');
  sel.value = selected || '';
}
function showRange(id) {
  const el = document.getElementById(id), out = document.getElementById(id + '-v');
  if (el && out) out.textContent = (+el.value).toFixed(2);
}
async function loadProfile() {
  try {
    const p = await (await fetch(API + '/api/profile')).json();
    for (const k of PF_KEYS) {
      const el = document.getElementById('pf-' + k);
      if (el && p[k]) el.value = p[k];
    }
    fillVoices(p.voz);
    voice.configure({ voice: p.voz || '', pitch: p.voz_tono ? +p.voz_tono : undefined,
      rate: p.voz_velocidad ? +p.voz_velocidad : undefined });
    showRange('pf-voz_tono'); showRange('pf-voz_velocidad');
    const c = await (await fetch(API + '/api/config')).json();
    const bb = document.getElementById('bgbeeps'); if (bb) bb.checked = c.bg_beeps === '1';
    // Dónde vive lo suyo, dicho con palabras y con la ruta: las claves y las
    // notas ya no están dentro del programa, así que actualizar no las borra.
    const dt = document.getElementById('pf-datos');
    if (dt) dt.textContent = c.datos
      ? `Tus claves y tus notas se guardan en ${c.datos} — fuera del programa, así que actualizar CORT no las borra.`
      : '';
    for (const k of CF_KEYS) {
      const el = document.getElementById('cf-' + k);
      if (!el) continue;
      if (k.endsWith('_key')) { el.value = ''; el.placeholder = c[k] ? 'guardada ' + c[k] + ' · escribe para cambiarla · «-» la borra' : 'pegar clave aquí · «-» la borra'; }
      else { el.value = c[k] || ''; if (!c[k]) el.placeholder = '(sin ajuste · «-» lo borra del .env)'; }
    }
  } catch { /* sin backend */ }
}
async function post(path, obj) {
  return (await fetch(API + path, { method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify(obj) })).json();
}
async function saveProfile() {
  const jobs = []; jobsHadKey = false;
  for (const k of PF_KEYS) {
    const el = document.getElementById('pf-' + k); if (!el) continue;
    const v = el.value.trim();
    if (!v && k !== 'voz') continue;
    jobs.push(post('/api/profile', { clave: k, valor: v }));
  }
  for (const k of CF_KEYS) {
    const el = document.getElementById('cf-' + k); if (!el) continue;
    const v = el.value.trim();
    if (!v && k.endsWith('_key')) continue;          // vacío = conservar la clave guardada
    if (k.endsWith('_key')) jobsHadKey = true;
    jobs.push(post('/api/config', { clave: k, valor: v }));
  }
  const n = (await Promise.all(jobs)).filter(r => r && r.ok).length;
  voice.configure({ voice: document.getElementById('pf-voz').value,
    pitch: +document.getElementById('pf-voz_tono').value, rate: +document.getElementById('pf-voz_velocidad').value });
  const m = document.getElementById('pfmsg');
  m.textContent = n ? `✓ ${n} ajustes guardados — el cerebro los usa desde la próxima respuesta` : 'nada que guardar';
  term('perfil actualizado (' + n + ' campos)', 'perfil');
  orb.burst(); loadProfile(); refreshStatus();
  setTimeout(() => m.textContent = '', 4500);
  if (jobsHadKey) testBrain();                    // si pegaste una clave, la probamos al momento
}
let jobsHadKey = false;
async function testBrain() {
  const out = document.getElementById('pftestout');
  out.innerHTML = '<div class="bt">probando cerebro…</div>';
  try {
    const r = await (await fetch(API + '/api/brain/test')).json();
    out.innerHTML = r.resultados.map(x => `<div class="bt ${x.ok ? 'ok' : (x.detalle === 'sin configurar' ? 'na' : 'bad')}">
      <b>${esc(x.proveedor)}</b> ${x.ok ? 'funciona' : esc(x.detalle)}${x.modelo ? ` <small>${esc(x.modelo)}${x.ms ? ' · ' + x.ms + ' ms' : ''}</small>` : ''}</div>`).join('');
    const good = r.resultados.find(x => x.ok);
    term('prueba de cerebro: ' + (good ? good.proveedor + ' OK' : 'ninguno respondió'), 'cerebro');
    if (good) sayLine(`Cerebro ${good.proveedor} en línea.`);
    refreshStatus();
  } catch { out.innerHTML = '<div class="bt bad">sin conexión con el núcleo</div>'; }
}

/* ---------- CEREBRO: muro de recuerdos enmarcados ---------- */
async function refreshMemories() {
  const el = document.getElementById('memwall');
  if (!el) return;
  try {
    const r = await (await fetch(API + '/api/memories')).json();
    const ms = (r.recuerdos || []).slice().reverse();
    const cnt = document.getElementById('memcount');
    if (cnt) cnt.textContent = ms.length + ' recuerdos';
    el.innerHTML = '';
    const hero = document.createElement('div');
    hero.className = 'frame hero';
    hero.innerHTML = `<span class="sig">◉</span><b>C.O.R.T.</b>
      <small>memoria persistente · ${ms.length} recuerdos<br>SQLite · sin nube</small>`;
    el.appendChild(hero);
    ms.forEach((m, i) => {
      const t = String(m.texto || '');
      const d = document.createElement('div');
      d.className = 'frame'; d.style.animationDelay = (i * 35) + 'ms';
      d.innerHTML = `<b>${m.tipo === 'nota' ? '✎ nota' : '✦ ' + (m.fuente || 'charla')}</b>
        <p>${t.slice(0, 76).replace(/</g, '&lt;')}${t.length > 76 ? '…' : ''}</p>
        <small>${m.fecha.slice(0, 10)}</small>`;
      d.onclick = () => {
        orb.burst(); setState('hablando');
        sayLine((m.tipo === 'nota' ? 'Apuntaste: ' : 'Recuerdo que dije: ') + t.slice(0, 140));
        term('recuerdo ' + m.fecha + ' · ' + m.tipo, 'cerebro');
      };
      el.appendChild(d);
    });
    if (!ms.length) {
      const d = document.createElement('div');
      d.className = 'frame empty';
      d.innerHTML = '<b>aún no hay recuerdos</b><small>háblame o dime «apunta …» y este muro se llenará</small>';
      el.appendChild(d);
    }
  } catch { el.innerHTML = '<div class="frame empty"><b>backend no disponible</b></div>'; }
}
function openCortex() { W.cerebro.show(); }

/* ---------- ayuda y soporte ---------- */
async function refreshHelp() {
  const box = document.getElementById('hpcmds');
  if (box && !box.children.length) {
    box.innerHTML = CMDS.map(c => `<button class="hp-cmd" data-cmd="${esc(c)}">${esc(c.trim())}</button>`).join('');
    box.querySelectorAll('.hp-cmd').forEach(b => b.onclick = () => {
      const cmd = b.dataset.cmd.trim();
      W.chat.show();
      if (/=$/.test(cmd)) { const q = document.getElementById('q'); q.value = cmd.slice(0, -1); q.focus(); }
      else send(cmd);
    });
  }
  const sup = document.getElementById('hpsup');
  if (!sup || sup.dataset.ok) return;
  try {
    const s = await (await fetch(API + '/api/support')).json();
    sup.innerHTML =
      `<div class="hp-txt">${esc(s.proyecto)}</div>` +
      (s.contacto || []).map(c => `<a class="hp-mail" href="mailto:${esc(c.correo)}">
          ✉ ${esc(c.correo)} <small>${esc(c.rol)}</small></a>`).join('') +
      `<div class="hp-note">${esc(s.nota)}</div>` +
      (s.donaciones && s.donaciones.length
        ? `<div class="hp-sec">▸ Invitar un café (opcional)</div>` +
          s.donaciones.map(d => `<a class="hp-mail" href="${esc(d.url)}" target="_blank" rel="noopener">
            ☕ ${esc(d.texto)}</a>`).join('')
        : '') +
      `<div class="hp-ver">CORT v${esc(s.version)} · ${esc(s.plataformas.join(' · '))}</div>`;
    sup.dataset.ok = '1';
  } catch { sup.innerHTML = '<div class="hp-txt">sin conexión con el núcleo: el contacto está en el README del repositorio.</div>'; }
}

/* ---------- 10 · MODELOS (Ollama) y 11 · OPTIMIZACIÓN ---------- */
let MO = null, MOtimer = null, MOrefresca = false;
const getJSON = async (url) => await (await fetch(API + url)).json();

function moBadge(m) {
  const txt = { va: 'VA BIEN', justo: 'JUSTO', 'no cabe': 'NO CABE' }[m.estado] || '—';
  return `<span class="mo-tag t-${(m.estado || '').replace(/ /g, '')}">${txt}</span>`;
}

async function refreshModels() {
  const box = document.getElementById('molist'), head = document.getElementById('mohead'),
        st = document.getElementById('molstate');
  if (!box) return;
  try { MO = await getJSON('/api/models'); }
  catch { if (head) head.innerHTML = '<div class="mo-warn">sin conexión con el núcleo: abre CORT para ver los modelos.</div>'; return; }
  const bajados = MO.modelos.filter(m => m.descargado).length;
  if (st) st.textContent = MO.instalado ? (MO.corriendo ? 'Ollama encendido' : 'Ollama apagado') : 'sin Ollama';
  head.innerHTML =
    `<div class="mo-sum">RAM de este equipo <b>${MO.ram_equipo} GB</b> · libre <b>${MO.ram_libre_gb} GB</b>` +
    ` · <b>${bajados}</b> modelo(s) en el disco (<b>${MO.disco_gb ?? '—'} GB</b>)</div>` +
    `<div class="mo-btns"><button class="mo-b" data-mo="ollama">⏻ ${MO.corriendo ? 'Apagar Ollama' : 'Encender Ollama'}</button>` +
    `<button class="mo-b" data-mo="refrescar">↻ Actualizar</button></div>` +
    (MO.aviso ? `<div class="mo-warn">${esc(MO.aviso)}</div>` : '');
  head.querySelectorAll('.mo-b').forEach(b => b.onclick = () =>
    b.dataset.mo === 'ollama' ? moverOllama(MO.corriendo) : refreshModels());
  box.innerHTML = MO.modelos.map(m => `
    <div class="mo-row${m.descargado ? ' bajado' : ''}${m.activo ? ' activo' : ''}" data-m="${esc(m.modelo)}">
      <div class="mo-top"><span class="mo-n">${esc(m.modelo)}</span>${moBadge(m)}
        ${m.activo ? '<span class="mo-tag t-usar">EN USO</span>' : ''}</div>
      <div class="mo-meta">${m.peso_real_gb ? 'ocupa ' + m.peso_real_gb + ' GB' : '≈' + m.gb + ' GB'} ·
        pide ~${m.ram ?? '—'} GB de RAM · ${esc(m.para || '')}${m.nota ? ' · ' + esc(m.nota) : ''}</div>
      <div class="mo-acc">${m.descargado
        ? `<button class="mo-b" data-a="usar">usar</button><button class="mo-b x" data-a="rm">✕ borrar</button>`
        : `<button class="mo-b d" data-a="pull" data-fit="${esc(m.estado || '')}">↓ descargar</button>`}</div>
      <div class="mo-prog"></div>
    </div>`).join('');
  box.querySelectorAll('.mo-row').forEach(r =>
    r.querySelectorAll('.mo-b').forEach(b => b.onclick = () => {
      // segunda advertencia: si no cabe en la RAM, hay que confirmarlo
      if (b.dataset.a === 'pull' && b.dataset.fit === 'no cabe' && b.dataset.ok !== '1') {
        b.dataset.ok = '1'; b.classList.remove('d'); b.classList.add('x');
        b.textContent = '↓ NO CABE · descargar igual';
        sayLine('Ese modelo pide más RAM de la que tiene este equipo: va a ir lentísimo o no abrirá. ' +
                'Púlsalo otra vez si lo quieres bajar de todos modos.');
        return;
      }
      modelAcc(r.dataset.m, b.dataset.a);
    }));
  pintarProgresos();
  clearInterval(MOtimer);
  MOtimer = setInterval(pintarProgresos, 900);
}

async function moverOllama(apagar) {
  term((apagar ? 'apagando' : 'encendiendo') + ' Ollama', 'modelos');
  sayLine(apagar ? 'Apagando Ollama para devolver tu memoria.' : 'Encendiendo Ollama…');
  try { const r = await post('/api/models/ollama', { accion: apagar ? 'stop' : 'start' });
        sayLine(r.detalle || r.error || 'listo'); } catch { sayLine('El núcleo no respondió.'); }
  setTimeout(refreshModels, 900);
}

async function modelAcc(nombre, acc) {
  const url = { pull: '/api/models/pull', rm: '/api/models/rm', usar: '/api/models/use' }[acc];
  term(`${acc} ${nombre}`, 'modelos');
  try {
    const r = await post(url, { modelo: nombre });
    if (r && r.error) { sayLine(`No pude: ${r.error}`); return; }
    if (acc === 'pull') { sayLine(`Descargando ${nombre}: mira la barra en 10 · Modelos.`); pintarProgresos(); }
    else if (acc === 'usar') { sayLine(`Listo: el cerebro local usará ${nombre}.`); setTimeout(refreshModels, 700); }
    else { sayLine(`Borrado ${nombre} del disco.`); setTimeout(refreshModels, 700); }
  } catch { sayLine('El núcleo no respondió.'); }
}

async function pintarProgresos() {
  const lista = document.getElementById('molist');
  // si la ventana ya no está abierta, no sigo martillando al núcleo
  if (!lista || !W.modelos || !W.modelos.open) { clearInterval(MOtimer); MOtimer = null; return; }
  let p = {};
  try { p = await getJSON('/api/models/progreso'); } catch { return; }
  let termino = false;
  Object.entries(p).forEach(([nombre, d]) => {
    const fila = lista.querySelector(`.mo-row[data-m="${CSS.escape(nombre)}"]`);
    if (!fila) return;
    const caja = fila.querySelector('.mo-prog');
    const pct = Math.max(0, Math.min(100, +(d.pct || 0)));
    caja.innerHTML = `<div class="mo-bar"><i style="width:${pct}%"></i></div>` +
      `<span class="mo-pt${d.estado === 'error' ? ' mal' : ''}">${esc(d.estado === 'error' ? (d.error || 'error') : `${d.detalle || ''} ${pct}%`)}</span>`;
    if (d.estado === 'listo' && !MOrefresca) { termino = true; }
  });
  if (termino) { MOrefresca = true; setTimeout(() => { MOrefresca = false; refreshModels(); }, 1200); }
}

let OPT = null;
async function refreshOptimize(fresco) {
  const box = document.getElementById('optr'), st = document.getElementById('optram');
  if (!box) return;
  if (!OPT) box.innerHTML = '<div class="mo-none">midiendo el equipo… tarda unos segundos</div>';
  try { OPT = await getJSON('/api/optimize' + (fresco ? '?fresco=1' : '')); }
  catch { box.innerHTML = '<div class="mo-warn">sin conexión con el núcleo.</div>'; return; }
  const r = OPT.ram;
  if (st) st.textContent = `${r.usado_pct} % en uso`;
  box.innerHTML =
    `<div class="op-bar"><i style="width:${r.usado_pct}%"></i><span>${r.usado_pct} % de ${r.total_gb} GB</span></div>
     <div class="mo-sum">libre <b>${r.disponible_mb} MB</b> · intercambio <b>${r.intercambio_mb} MB</b> ·
       caché borrable <b>${OPT.liberable_mb} MB</b>${OPT.modelos_gb ? ` · modelos en el disco <b>${OPT.modelos_gb} GB</b>` : ''}</div>
     <div class="hp-sec">▸ Lo que más come memoria</div>
     <div class="op-procs">${OPT.procesos.map(p => `
       <div class="op-proc"><span class="n">${esc(p.nombre)}</span><span class="mb">${Math.round(p.mb)} MB</span>
         ${p.intocable ? '<span class="mo-tag t-no">fijo</span>'
                       : `<button class="mo-b x" data-kill="${p.pid}" title="cerrar ${esc(p.nombre)}">✕</button>`}</div>`).join('')}</div>
     <div class="hp-sec">▸ Caché en disco</div>
     <div class="op-caches">${OPT.caches.map(c => `
       <div class="op-cache ${c.nivel}"><span class="n">${esc(c.ruta.replace(/^\.?cache\//, ''))}</span>
         <span class="mb">${Math.round(c.mb)} MB</span>
         <small>${esc(c.que)}${c.aprox ? ' ·≈' : ''}${c.abierta ? ' · programa abierto' : ''}</small></div>`).join('')
       || '<div class="mo-none">no encontré cachés grandes</div>'}</div>
     <div class="mo-btns">
       <button class="mo-b" data-op="fresco">↻ Analizar de nuevo</button>
       <button class="mo-b d" data-op="seguro">⌁ Limpiar segura (${OPT.liberable_mb} MB)</button>
       ${OPT.todo_mb > OPT.liberable_mb ? `<button class="mo-b x" data-op="todo">Limpiar también «cuidado» (${OPT.todo_mb} MB)</button>` : ''}
       ${OPT.papelera_mb ? `<button class="mo-b x" data-op="papelera">✕ Vaciar papelera (${OPT.papelera_mb} MB)</button>` : ''}
     </div>
     <div class="hp-sec">▸ Consejos para este equipo</div>
     <ul class="hp-keys">${OPT.sugerencias.map(s => `<li>${esc(s)}</li>`).join('')}</ul>
     <div id="opres"></div>`;
  box.querySelectorAll('[data-kill]').forEach(b => b.onclick = () => matarProceso(b.dataset.kill));
  box.querySelectorAll('[data-op]').forEach(b => b.onclick = () => limpiar(b.dataset.op));
}

async function limpiar(nivel) {
  const res = document.getElementById('opres');
  if (nivel === 'fresco') { OPT = null; return refreshOptimize(true); }
  if (res) res.innerHTML = '<div class="mo-none">barriendo caché…</div>';
  try {
    const r = await post('/api/optimize/clean', { nivel });
    const txt = r.ok ? `Barrí ${r.borrado.length} caché(s): ${r.mb_liberados} MB liberados` +
                       (r.ram_ganada_mb ? ` y ${r.ram_ganada_mb} MB de RAM devuelta` : '') + '.'
                     : `No pude limpiar: ${r.error}`;
    sayLine(txt); term(txt, 'optimizar');
    if (res) res.innerHTML = `<div class="mo-warn${r.ok ? ' ok' : ''}">${esc(txt)} ${esc(r.nota || '')}</div>`;
    OPT = null; setTimeout(() => refreshOptimize(true), 600);
  } catch { if (res) res.innerHTML = '<div class="mo-warn">el núcleo no respondió.</div>'; }
}

async function matarProceso(pid) {
  try {
    const r = await post('/api/optimize/kill', { pid: +pid });
    sayLine(r.ok ? r.detalle : `No lo cierro: ${r.error}`);
    term(r.ok ? r.detalle : `negado: ${r.error}`, 'optimizar');
    OPT = null; setTimeout(() => refreshOptimize(true), 800);
  } catch { sayLine('El núcleo no respondió.'); }
}

/* ---------- LÁMPARA DE ESTADO (la bombilla de color de la referencia) ---------- */
const LAMP = {
  reposo:   ['#39c2ff', 'en reposo'],
  escucha:  ['#8f6bff', 'escuchándote'],
  pensando: ['#ff8a3d', 'procesando'],
  hablando: ['#2bff9e', 'respondiendo'],
  listo:    ['#2bff9e', 'en línea'],
  oculto:   ['#4b7f9e', 'HUD oculto'],
  error:    ['#ff5b5b', 'sin conexión'],
};
let lampTimer = 0;
function setState(k) {
  const el = document.getElementById('lamp');
  if (!el) return;
  const [c, txt] = LAMP[k] || LAMP.reposo;
  el.classList.add('on');
  el.style.setProperty('--lc', c);
  el.title = 'CORT: ' + txt;
  el.querySelector('span').textContent = txt;
  clearTimeout(lampTimer);
  if (k === 'pensando' || k === 'hablando' || k === 'escucha')
    lampTimer = setTimeout(() => setState(k === 'escucha' ? 'reposo' : 'listo'),
                           k === 'pensando' ? 12000 : 5200);
}

/* ---------- reloj y estado (siempre fijos) ---------- */setInterval(() => document.getElementById('clock').textContent =
  new Date().toLocaleTimeString('es-MX', { hour12: false }), 500);

async function refreshStatus() {
  const el = document.getElementById('status');
  try {
    const s = await (await fetch(API + '/api/status')).json();
    const b = s.brain, dot = ok => `<span class="dot ${ok ? 'on' : 'off'}"></span>`;
    el.innerHTML =
      `${dot(b.ollama)} local ${b.ollama ? '· ' + b.ollama_model : '(no disponible)'}<br>` +
      `${dot(b.groq || b.gemini)} online ${b.groq ? '· Groq' : (b.gemini ? '· Gemini' : '(sin API key)')}<br>` +
      `<span style="color:#5e8cab">${esc(s.system)}</span>`;
    const eb = document.getElementById('envbrain');
    if (eb) eb.innerHTML = `${dot(b.ollama)} local ${b.ollama ? '· ' + esc(b.ollama_model) : '(sin Ollama)'}<br>` +
      `${dot(b.groq || b.gemini)} online ${b.groq ? '· Groq' : (b.gemini ? '· Gemini' : '(sin clave · ve a Perfil)')}<br>` +
      `<span style="color:#5e8cab">modo: ${esc(b.mode)}</span>`;
    const m = s.system.match(/CPU (\d+)\s*% · RAM (\d+)\s*% \(([\d.]+) de ([\d.]+) GB\) · Disco (\d+)\s*%/);
    if (m) {
      setBar('cpu', m[1]); setBar('ram', m[2]); setBar('disk', m[5]);
      document.getElementById('ramgb').textContent = `${m[3]} / ${m[4]} GB`;
    }
    document.getElementById('batt').textContent = s.battery;
  } catch {
    el.innerHTML = `<span class="dot off"></span> backend no detectado`;
  }
}
function setBar(id, pct) { document.getElementById('bar-' + id).style.width = pct + '%'; }

/* ---------- clima ---------- */
async function refreshWeather() {
  const el = document.getElementById('wx');
  try {
    const w = await (await fetch(API + '/api/weather')).json();
    el.innerHTML = w.ok
      ? `<span class="big">${w.temp.toFixed(0)}°C</span> · ${w.cielo}<br>
         <span style="color:#5e8cab">viento ${w.viento.toFixed(0)} km/h</span>`
      : '<span style="color:#5e8cab">clima no disponible (offline)</span>';
  } catch { el.textContent = '…'; }
}

/* ---------- archivos ---------- */
let fGrid = false, curFPath = '';
async function openFiles(path = '') {
  curFPath = path;
  W.files.show();
  const list = document.getElementById('flist');
  list.innerHTML = '<div class="row">cargando…</div>';
  const r = await (await fetch(API + '/api/files?path=' + encodeURIComponent(path))).json();
  if (r.needPermission) { list.innerHTML = ''; list.appendChild(permRow('files', r.error, () => { openFiles(path); refreshTree(); })); return; }
  if (r.error) { list.innerHTML = `<div class="row">${ic('warn')} ${esc(r.error)}</div>`; return; }
  const rows = [];
  if (path) rows.push({ name: '..', kind: 'up', dir: path.split('/').slice(0, -1).join('/') });
  for (const e of r.entries) rows.push({
    name: e.name, kind: e.type === 'dir' ? 'dir' : 'file',
    dir: path ? path + '/' + e.name : e.name, type: e.type, size: e.size,
    fecha: e.fecha });
  list.innerHTML = '';
  list.classList.toggle('grid', fGrid);
  const ICO = { up: 'back', dir: 'folder', file: 'file' };
  rows.forEach((row, i) => {
    const d = document.createElement('div');
    d.style.animationDelay = (i * 16) + 'ms';
    if (fGrid) {
      d.className = 'tile';
      d.innerHTML = `<span class="ti">${ic(ICO[row.kind])}</span><span class="tn">${esc(row.name)}</span>`;
    } else {
      d.className = 'row';
      d.innerHTML = `${ic(ICO[row.kind], 'fi')}<span class="fname">${esc(row.name)}</span>` +
        (row.fecha ? `<span class="fecha">${row.fecha.slice(0, 10)}</span>` : '') +
        (row.type === 'file' && row.size ? `<span class="size">${row.size > 1e6 ? (row.size / 1e6).toFixed(1) + ' MB' : Math.round(row.size / 1e3) + ' KB'}</span>` : '');
    }
    d.onclick = row.type === 'file' ? () => openFile(row.dir, row.name) : () => openFiles(row.dir);
    list.appendChild(d);
  });
  document.getElementById('fpath').textContent = (path || 'raíces') + ' · ' + rows.length + ' items';
  if (!rows.length || (path && rows.length === 1)) list.insertAdjacentHTML('beforeend', '<div class="row">carpeta vacía</div>');
  term('listando ' + (path || 'raíces') + ' (' + rows.length + ' entradas)', 'archivos');
}

/* ---------- SEGUNDO PLANO: escuchar «Oye CORT» con la app cerrada ---------- */
const BG_PERMS = [
  ['mic', 'Micrófono', 'para oírte'],
  ['notif', 'Notificaciones', 'el aviso fijo «CORT escuchando»'],
  ['overlay', 'Burbuja flotante', 'abrir apps desde el fondo (Android 10+)'],
  ['battery', 'Batería sin restricción', 'que Android no lo apague'],
];
function bgStatus() {
  try { return IS_ANDROID ? JSON.parse(window.CortNative.bgStatus()) : null; } catch { return null; }
}
function renderBg(st = bgStatus()) {
  const box = document.getElementById('bgbox'); if (!box) return;
  if (!st) { box.innerHTML = '<div class="bg-help">Solo disponible en la app de Android.</div>'; return; }
  const t = document.getElementById('bgtoggle');
  t.classList.toggle('on', st.enabled);
  t.querySelector('b').textContent = st.enabled ? (st.running ? 'Escucha de fondo ACTIVA' : 'Activando…') : 'Escuchar con la app cerrada';
  const rows = BG_PERMS.map(([k, name, why]) => `<div class="bgp ${st[k] ? 'ok' : ''}">
      <span class="st">${st[k] ? '✓' : '·'}</span><span class="nm">${name}<small>${why}</small></span>
      ${st[k] ? '' : `<button data-perm="${k}">Dar</button>`}</div>`).join('');
  const oem = /oppo|realme|oneplus|xiaomi|redmi|poco|huawei|honor|vivo|samsung|tecno|infinix/i.test(st.maker || '');
  document.getElementById('bgperms').innerHTML = rows + (oem ? `<div class="bgp warn"><span class="st">!</span>
      <span class="nm">${esc(st.maker)}: activa «Inicio automático» / «Actividad en segundo plano»<small>en los ajustes de la app, si no tu teléfono lo cierra</small></span>
      <button data-perm="autostart">Abrir</button></div>` : '');
  document.querySelectorAll('#bgperms [data-perm]').forEach(b => b.onclick = () => perms.ask(b.dataset.perm));
}
async function toggleBg() {
  const st = bgStatus(); if (!st) return;
  const on = !st.enabled;
  window.CortNative.setBackground(on);
  term(on ? 'escucha de fondo: activando' : 'escucha de fondo: apagada', 'voz');
  if (on) {
    voice.setWake(true);                                   // en pantalla también escucha «Oye CORT»
    add('a', 'Listo. Aunque cierres la app, di «Oye CORT» y tu orden. Para que no falle, da los permisos de la lista.', 'voz');
    speakTTS('Escucha de fondo activada.');
  }
  setTimeout(() => renderBg(), 700);
}

/* ---------- permisos y abrir archivos (Android) ---------- */
const PERM_TXT = { files: 'Dar acceso a archivos', music: 'Dar acceso a la música', mic: 'Dar acceso al micrófono', camera: 'Dar acceso a la cámara' };
const permRetry = {};
function permRow(kind, msg, retry) {
  permRetry[kind] = retry;
  const d = document.createElement('div'); d.className = 'row perm';
  d.innerHTML = `<span>${ic('lock')} ${esc(msg || 'falta permiso')}</span><button class="pf-btn">${PERM_TXT[kind] || 'Dar permiso'}</button>`;
  d.querySelector('button').onclick = ev => { ev.stopPropagation(); perms.ask(kind); };
  return d;
}
function onPermission(kind, granted) {
  term(`permiso ${kind}: ${granted ? 'concedido' : 'denegado'}`, 'sistema');
  if (granted) { permRetry[kind] && permRetry[kind](); if (kind === 'files') refreshTree(); if (kind === 'music') loadMusic(); }
  else if (kind === 'mic') add('a', 'Sin permiso de micrófono no puedo escucharte. Puedes darlo en Ajustes → Apps → CORT IA → Permisos.', 'error');
}
async function openFile(rel, name) {
  term('abrir: ' + rel, 'archivos');
  try {
    const r = await post('/api/open', { path: rel });
    if (r.needPermission) { perms.ask('files'); return; }
    sayLine(r.ok ? `Abriendo ${name}.` : `No pude abrir ${name}: ${r.error || 'sin app compatible'}.`);
  } catch { sayLine(`Archivo ${name} seleccionado.`); }
}

/* ---------- chat + voz ---------- */
function add(cls, text, src) {
  const p = document.createElement('p'); p.className = cls; p.textContent = text;
  if (src) { const s = document.createElement('span'); s.className = 'src'; s.textContent = ' [' + src + ']'; p.appendChild(s); }
  const log = document.getElementById('log');
  log.appendChild(p); log.scrollTop = log.scrollHeight;
}
function sayLine(text) { add('a', text, 'voz'); orb.speak(2200); speakTTS(text); }
function speakTTS(text, then) { return voice ? voice.speak(text, then) : Promise.resolve(); }

/* ── leer en voz alta lo que llega al teléfono ──────────────────────────────
   `window.CortNative.avisos(n)` (Java, `Avisos.java`) devuelve los últimos avisos
   que el sistema mostró —WhatsApp, Gmail, Telegram— ya convertidos en una frase.
   Se habla por `speakTTS`, la misma boca del resto de CORT, y no por un camino
   propio: así la voz, el tono y el idioma que la dueña eligió en 07 · Perfil son
   también los de los avisos.
   En PC sin app de teléfono no hay notificaciones que leer, y se dice en vez de
   quedarse callada.                                                       */
function leeAvisos() {
  const N = window.CortNative;
  if (!N || typeof N.avisos !== 'function') {
    const r = 'Los avisos del teléfono los leo en la app de CORT: necesito ver tus notificaciones.';
    add('a', r, 'avisos'); speakTTS('Eso lo leo en la app del teléfono.'); return;
  }
  let d = null;
  try { d = JSON.parse(N.avisos(3)); } catch { d = null; }
  if (!d || !d.texto) { sayLine('No tengo ningún aviso en la cabeza.'); return; }
  add('a', d.texto, 'avisos'); orb.speak(2200); speakTTS(d.texto);
  term('avisos: ' + (d.total ?? 0) + (d.escuchando ? ' · oído puesto' : ' · sin permiso'), 'avisos');
  if (!d.activado) {
    add('a', 'Para oírlos: botón CORT · PC ▸ «Dar el permiso de los avisos» ▸ y elige CORT.', 'avisos');
  }
}
function olvidaAvisos() {
  const N = window.CortNative;
  if (!N || typeof N.vaciarAvisos !== 'function') { sayLine('Aquí no hay avisos que olvidar.'); return; }
  N.vaciarAvisos();
  add('a', 'Avisos olvidados. No los guardé nunca: se van de la cabeza al cerrar la app.', 'avisos');
  speakTTS('Olvidados.');
}
/* ---------- consola de comandos: historial ↑/↓ y Tab que completa ---------- */
const HIST = [];
let hIdx = 0, draft = '';
const CMDS = ['reproduce', 'pausa', 'reanuda', 'modo oficina', 'oculta todo', 'muestra todo',
  'muéstrame las notas', 'archivos recientes', 'recoge los chips', '¿qué hora es?',
  'abre youtube', 'abre el navegador', 'apunta ', 'muéstrame tu cerebro', 'qué recuerdas',
  'muéstrame los modelos', 'descarga el modelo ', 'usa el modelo ', 'enciende ollama',
  '¿cuánta ram queda?', 'abre la optimización', 'limpia la caché',
  'lee mis avisos', 'lee mis notas', 'lee mis tareas', 'tengo que ', 'lee el documento '];
function completeCmd(v) {
  const hits = CMDS.filter(c => c.startsWith(v));
  if (!hits.length) return null;
  let best = hits[0];
  for (const h of hits.slice(1)) {
    let i = 0;
    while (i < best.length && i < h.length && best[i] === h[i]) i++;
    best = best.slice(0, i);
  }
  return best;
}
async function send(raw) {
  const q = document.getElementById('q');
  const msg = (raw ?? q.value).trim(); if (!msg) return;
  q.value = ''; add('u', msg);
  if (mobile() && raw === undefined) q.blur();     // cierra el teclado para ver la respuesta
  if (HIST[HIST.length - 1] !== msg) HIST.push(msg);
  hIdx = HIST.length; draft = '';
  setState('pensando');
  document.getElementById('top').classList.add('glitch');
  setTimeout(() => document.getElementById('top').classList.remove('glitch'), 800);
  orb.activate();                                    // ← vórtice de activación (referencia)
  term('consulta: "' + msg.slice(0, 40) + '"', 'voz');
  /* ─── órdenes directas del repertorio de la referencia (video f7d16b9e) ─── */
  if (/modo (oficina|bureau|escritorio)|organiza|ordena (las )?ventanas|ordenar el escritorio/i.test(msg)) {
    const n = organizeBureau();
    const r = n ? `Modo oficina: ${n} ventanas posicionadas en 2 niveles.`
                : 'No hay ventanas abiertas que organizar.';
    add('a', r, 'ejecutor'); speakTTS(r); term('bureau: ' + n + ' ventanas', 'ejecutor');
    orb.burst(); return;
  }
  if (/oculta (todo|las ventanas|el hud|los paneles)|esconde todo|desaparece/i.test(msg)) {
    hideAll(); add('a', 'HUD oculto — solo quedo yo, brillando. Di «muestra todo» para volver.', 'ventanas');
    speakTTS('Listo, solo el orbe.'); return;
  }
  if (/muestra (todo|las ventanas|los paneles|de vuelta)|devu[eé]lveme|aparece/i.test(msg)) {
    showAll(); add('a', 'Ventanas de vuelta en su lugar.', 'ventanas'); speakTTS('De vuelta.'); return;
  }
  if (/mu[eé]strame (las )?notas|lanza (las )?notas|notas flotando/i.test(msg)) {
    add('a', 'Tomando tus notas del archivo…', 'notas'); chipNotes(); return;
  }
  /* leer en voz alta: los avisos del teléfono son los únicos que no viven en el PC */
  if (/^(?:lee|leer|l[eé]eme|l[eé]elo|cu[eé]ntame|recita|narra)\b/i.test(msg)
      && /aviso|mensaje|whatsapp|telegram|se[nñ]al|lleg|correo/i.test(msg)) {
    setState('listo'); leeAvisos(); return;
  }
  if (/olvida (los )?avisos|borra lo que lleg[oó]/i.test(msg)) {
    setState('listo'); olvidaAvisos(); return;
  }
  if (/archivos recientes|mu[eé]strame (los )?archivos|lanza (los )?archivos/i.test(msg)) {
    add('a', 'Aquí tienes lo último de Documentos…', 'archivos'); chipRecentFiles(); return;
  }
  if (/recoge|limpia (los )?chips|guarda los chips/i.test(msg)) {
    clearChips(); add('a', 'Chips guardados. La pantalla vuelve a estar limpia.', 'ventanas');
    setState('listo'); term('chips retirados', 'ventanas'); return;
  }
  if (/mu[eé]strame tu cerebro|qu[eé] recuerdas|abre el cerebro|tus recuerdos|muro de recuerdos/i.test(msg)) {
    openCortex();
    add('a', 'Este es mi muro de recuerdos: cada cuadro es algo que apunté o hablamos.', 'cerebro');
    term('cerebro abierto', 'cerebro'); return;
  }
  if (/^(ayuda|help)|c[oó]mo (te )?(uso|funcionas)|qu[eé] puedes hacer/i.test(msg)) {
    W.ayuda.show();
    add('a', 'En 09 · Ayuda tienes las órdenes que entiendo, los atajos del teclado y el contacto de soporte.', 'ayuda');
    term('ventana de ayuda abierta', 'ayuda'); return;
  }
  /* abrir las ventanas nuevas sin pasar por el backend (la descarga sí pasa) */
  if (/mu[eé]strame los modelos|lista los modelos|qu[eé] modelos|abre los modelos|modelos locales/i.test(msg)
      && !/descarga|baja|instala|borra/i.test(msg)) {
    W.modelos.show();
    add('a', 'Modelos abiertos: cada uno dice si le cabe la RAM de este equipo y tiene su flecha ↓.', 'modelos');
    return;
  }
  if (/abre la optimizaci[oó]n|qu[eé] come la ram|optimiza el equipo|cu[aá]nta ram|cu[aá]nta memoria/i.test(msg)) {
    W.optimiza.show();
    add('a', 'Estoy midiendo el equipo: memoria, procesos pesados y caché borrable.', 'optimizar');
    return;
  }
  /* reproductor interno de CORT (cuando está abierto y sonando) */
  const aud = document.getElementById('aud');
  const single = !/\s(y|luego|despu[eé]s)\s/i.test(msg);
  if (single && tIdx >= 0 && !aud.paused && /^(pausa|para|det[eé]n)\b/i.test(msg)) {
    pauseMusic(); add('a', 'Música en pausa.', 'ejecutor'); speakTTS('Pausa'); return;
  }
  if (single && tIdx >= 0 && aud.paused && /^(reanuda|contin[uú]a|sigue|play)\b/i.test(msg)) {
    resumeMusic(); add('a', 'Continuando la reproducción.', 'ejecutor'); speakTTS('Continuando'); return;
  }
  if (single && tracks.length && /^(reproduce|pon|ponme|toca)\s+/i.test(msg)) {
    const c = msg.replace(/^(reproduce|pon|ponme|toca)\s+(la canci[oó]n\s+|el tema\s+)?/i, '').trim().toLowerCase();
    const i = c.length > 2 ? tracks.findIndex(t => t.nombre.toLowerCase().includes(c) || t.artista.toLowerCase().includes(c)) : -1;
    if (i >= 0) {
      playTrack(i);
      add('a', `Reproduciendo «${tracks[i].nombre}» de ${tracks[i].artista} en el ejecutor de CORT.`, 'ejecutor');
      speakTTS('Reproduciendo ' + tracks[i].nombre); return;
    }
  }
  /* todo lo demás: ACCIONES del teléfono (varias en una frase) y, si no, el cerebro */
  try {
    const r = await post('/api/command', { message: msg });
    // La cara dentro del APK, sin PC, no tiene núcleo: `MainActivity` corta el
    // `/api/*` y responde 501 con `{"error": …}` y **sin `reply`**. Hablar un
    // «undefined» sería enseñarle a la dueña un fallo técnico en la voz de CORT,
    // así que la respuesta del teléfono se traduce a su propia frase.
    const dicho = r.reply || (r.error ? String(r.error) : 'No entendí la orden.');
    add('a', dicho, r.source || 'sistema'); orb.burst(); speakTTS(dicho);   // ← animación de acción
    if (r.source === 'offline' && !offlineHinted) { offlineHinted = true;
      add('a', 'Consejo: en 07 · Perfil → Cerebro IA pega una clave gratis de Groq o Gemini para conversar de verdad.', 'sistema'); }
    setState('hablando');
    (r.done || []).forEach(d => term('acción: ' + d, 'ejecutor'));
    term('respuesta vía ' + r.source, 'cerebro');
    if ((r.done || []).includes('nota')) refreshNotes();
    if (!(r.done || []).length && /^(abre |muestra )?(los )?(archivos|carpetas|explorador)$/i.test(msg)) openFiles();
  } catch { add('a', IS_ANDROID ? 'El núcleo de CORT no respondió. Cierra y abre la app.' : 'Sin conexión con el backend. Ejecuta scripts/run.', 'error'); setState('error'); }
}
async function addNoteFromChat(msg) {
  const t = msg.replace(/^(apunta|nota|recuerda)[\s:]+/i, '').trim();
  if (t && t !== msg) {
    await fetch(API + '/api/notes', { method: 'POST',
      headers: { 'content-type': 'application/json' }, body: JSON.stringify({ texto: t }) });
    term('nota guardada desde el chat', 'notas'); refreshNotes();
  }
}

let offlineHinted = false;

/* ---------- botón atrás de Android: cierra lo último abierto ---------- */
window.__cortBack = () => {
  if (voice && voice.mode === 'cmd') { voice.listen(); return true; }
  const chips = document.querySelectorAll('#chips .chip:not(.gone)');
  if (chips.length) { clearChips(); return true; }
  const open = Object.values(W).filter(w => w.open && !w.minimized)
    .sort((a, b) => (+b.el.style.zIndex || 0) - (+a.el.style.zIndex || 0));
  if (open.length) { open[0].minimize(); return true; }
  return false;
};

/* ---------- todo junto ---------- */
export function wireUI(orbRef) {
  orb = orbRef;
  voice = createVoice({
    lang: 'es-MX',
    onState(mode, st) {
      const mic = document.getElementById('mic'), wake = document.getElementById('wake');
      mic.classList.toggle('on', mode === 'cmd');
      wake.classList.toggle('on', st.wakeOn);
      wake.classList.toggle('hearing', mode === 'wake');
      document.body.classList.toggle('listening', mode === 'cmd');
      if (mode === 'cmd') { orb.listen(true); setState('escucha'); }
      else if (!st.speaking) { orb.listen(false); }
    },
    onPartial(text) {                      // texto EN VIVO mientras hablas
      const q = document.getElementById('q');
      q.value = text; q.classList.add('live');
      const lv = document.getElementById('livetxt');
      if (lv) { lv.textContent = text; lv.classList.add('show'); }
    },
    onFinal(text) {
      const q = document.getElementById('q'); q.classList.remove('live');
      document.getElementById('livetxt')?.classList.remove('show');
      term('dictado: "' + text + '"', 'voz');
      send(text);
    },
    onLevel(l) { orb.setAudio(l * .9, l); const m = document.getElementById('mic'); m.style.setProperty('--lvl', l.toFixed(2)); },
    onSpeak(on) { if (on) { orb.speak(60000); setState('hablando'); } else { orb.speak(1); } },
    onWake(rest) {
      term('palabra de activación: «Oye CORT»' + (rest ? ' + "' + rest + '"' : ''), 'voz');
      orb.activate(); W.chat.show();
      if (rest.length > 2) send(rest);
      else { add('a', '¿Sí?', 'voz'); speakTTS('¿Sí?', () => voice.listen()); }
    },
    onError(e) {
      const lv = document.getElementById('livetxt'); lv && lv.classList.remove('show');
      document.getElementById('q').classList.remove('live');
      if (e === 'not-allowed') { add('a', 'Necesito permiso de micrófono para escucharte.', 'error'); document.getElementById('wake').classList.remove('on'); }
      else if (e === 'service-not-allowed') add('a', 'Este teléfono no tiene servicio de reconocimiento de voz. Instala o actualiza la app «Google» y vuelve a intentar.', 'error');
      else if (e === 'network') term('reconocimiento de voz sin red (reintento)', 'voz');
      else if (e === 'no-speech') { term('no escuché nada', 'voz'); setState('reposo'); }
    },
    onPermission,
  });
  buildWindows();
  term('CORT v0.2 — núcleo holográfico en línea', 'arranque');
  runBoot().then(({ backendOK, where }) => {
    setState(backendOK ? 'listo' : 'error');
    term(backendOK ? 'núcleo conectado en ' + (where || 'este origen') : 'backend NO detectado', 'arranque');
    add('a', backendOK ? 'Sistemas en línea. CORT a sus órdenes.' :
      (IS_ANDROID ? 'El núcleo de CORT no arrancó. Cierra y vuelve a abrir la app.' :
      'Backend no detectado: ejecuta scripts/run.sh (Linux) o run.bat (Windows).'),
      backendOK ? 'sistema' : 'error');
    if (backendOK) {
      refreshStatus(); refreshWeather(); refreshNotes(); loadProfile(); refreshTree();
      if (mobile()) {
        // celular: una ventana a la vez; arranca en el canal de voz
        setTimeout(() => W.chat.show(), 150);
        setTimeout(() => { openFiles(); W.chat.show(); }, 400);
        setTimeout(chipNotes, 2200);
        setTimeout(() => speakTTS('Sistemas en línea. CORT a sus órdenes.'), 600);
      } else {
        // los paneles se despliegan en cascada numerada, como en la referencia
        setTimeout(() => W.chat.show(), 150);
        setTimeout(() => { openFiles(); }, 500);
        setTimeout(() => W.env.show(), 800);
        setTimeout(() => W.music.show(), 1100);
        setTimeout(() => W.term.show(), 1400);
        setTimeout(chipNotes, 2600);      // bienvenida estilo Jared: notas flotando
      }
    }
    setInterval(refreshStatus, 10000);
    setInterval(refreshWeather, 10 * 60000);
    setInterval(refreshTree, 5 * 60000);
  });

  document.getElementById('go').onclick = () => send();
  // teclado abierto en el celular → la hoja ocupa la pantalla
  document.addEventListener('focusin', e => { if (/INPUT|SELECT|TEXTAREA/.test(e.target.tagName) && e.target.type !== 'range') document.body.classList.add('typing'); });
  document.addEventListener('focusout', () => setTimeout(() => {
    const a = document.activeElement; if (!a || !/INPUT|SELECT|TEXTAREA/.test(a.tagName)) document.body.classList.remove('typing'); }, 60));
  document.getElementById('q').addEventListener('keydown', e => {
    const q = e.currentTarget;
    if (e.key === 'Enter') return send();
    if (e.key === 'ArrowUp') {                       // historial hacia atrás
      if (!HIST.length) return;
      if (hIdx === HIST.length) draft = q.value;
      hIdx = Math.max(0, hIdx - 1); q.value = HIST[hIdx]; e.preventDefault();
    } else if (e.key === 'ArrowDown') {
      if (!HIST.length) return;
      hIdx = Math.min(HIST.length, hIdx + 1);
      q.value = hIdx === HIST.length ? draft : HIST[hIdx]; e.preventDefault();
    } else if (e.key === 'Tab') {                    // autocompletar comandos
      const c = completeCmd(q.value.trim().toLowerCase());
      if (c) { q.value = c; e.preventDefault(); }
    }
  });
  document.getElementById('notago').onclick = addNote;
  document.getElementById('nota').addEventListener('keydown', e => { if (e.key === 'Enter') addNote(); });
  document.getElementById('pfguardar').onclick = saveProfile;

  /* ejecutor de música */
  document.getElementById('mplay').onclick = togglePlay;
  document.getElementById('mprev').onclick = () => playTrack((tIdx - 1 + tracks.length) % tracks.length);
  document.getElementById('mnext').onclick = () => playTrack((tIdx + 1) % tracks.length);
  document.getElementById('mvol').oninput = e => { document.getElementById('aud').volume = +e.target.value; };
  document.getElementById('aud').addEventListener('ended', () => { if (tracks.length > 1) playTrack((tIdx + 1) % tracks.length); else { orb.setDisc(false); stopMeter(); } });
  document.getElementById('mbar').onclick = e => {
    const aud = document.getElementById('aud');
    if (!aud.duration) return;
    const r = e.currentTarget.getBoundingClientRect();
    aud.currentTime = (e.clientX - r.left) / r.width * aud.duration;
  };
  document.getElementById('mref').onclick = loadMusic;
  loadMusic();
  document.getElementById('fgrid').onclick = () => { fGrid = true; openFiles(curFPath); };
  document.getElementById('flistbtn').onclick = () => { fGrid = false; openFiles(curFPath); };

  /* interfaz Jared: ocultar/mostrar desde el dock + cerebro del árbol */
  document.querySelector('#dock [data-act=hide]').onclick = () => {
    Object.values(W).some(w => w.open && !w.minimized) ? hideAll() : showAll();
    orb.burst();
  };
  document.getElementById('brain').onclick = () => { openCortex(); term('cerebro abierto', 'cerebro'); };

  /* Esc oculta/muestra el HUD (solo cuando no estás escribiendo) */
  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    if (/INPUT|TEXTAREA|SELECT/.test((e.target.tagName || ''))) { e.target.blur(); return; }
    Object.values(W).some(w => w.open && !w.minimized) ? hideAll() : showAll();
  });

  /* dock nuevo: «abrir» la carpeta actual + ayuda la primera vez */
  let vista = false;
  try { vista = localStorage.getItem('cort_ayuda_vista') === '1'; } catch { /* modo privado */ }
  if (!vista) { W.ayuda.show(); try { localStorage.setItem('cort_ayuda_vista', '1'); } catch { /* nada */ } }
  document.querySelector('#dock [data-act=open]').onclick = () => {
    post('/api/open', { path: curFPath }).then(r => {
      sayLine(r.ok ? `Abriendo ${r.carpeta || r.archivo || 'la carpeta'} en el explorador.`
                   : `No pude abrir la carpeta: ${r.error || 'sin visor'}.`);
      term('abrir carpeta: ' + (curFPath || 'raíces') + (r.ok ? ' ✓' : ' ✗'), 'archivos');
      orb.burst();
    }).catch(() => sayLine('El núcleo no respondió: abre la carpeta a mano.'));
  };

  /* perfil: voz y enlaces */
  ['pf-voz_tono', 'pf-voz_velocidad'].forEach(id => document.getElementById(id).addEventListener('input', () => showRange(id)));
  document.getElementById('pftest').onclick = testBrain;
  document.getElementById('bgtoggle').onclick = toggleBg;
  document.getElementById('bgbeeps').onchange = e => post('/api/config', { clave: 'bg_beeps', valor: e.target.checked ? '1' : '0' });
  renderBg();
  window.__cortNative.on(ev => { if (ev.type === 'bg' || ev.type === 'resume' || ev.type === 'perm') setTimeout(() => renderBg(), 300); });
  { const st = bgStatus(); if (st && st.enabled) setTimeout(() => voice.setWake(true), 3000); }
  document.getElementById('pfprobar').onclick = () => {
    voice.configure({ voice: document.getElementById('pf-voz').value,
      pitch: +document.getElementById('pf-voz_tono').value, rate: +document.getElementById('pf-voz_velocidad').value });
    const n = document.getElementById('pf-usuario').value.trim();
    sayLine(`A sus órdenes${n ? ', ' + n : ''}. Todos los sistemas están en línea.`);
  };
  document.querySelectorAll('.pf-link').forEach(a => a.onclick = e => { e.preventDefault(); location.href = a.dataset.href; });
  window.__cortNative.on(ev => { if (ev.type === 'tts-ready' && ev.ok) loadProfile(); });

  /* micrófono: toca y habla — el texto aparece mientras hablas */
  const mic = document.getElementById('mic');
  mic.onclick = () => { orb.activate(); voice.listen(); };
  document.getElementById('q').addEventListener('focus', () => { if (voice.speaking) voice.stopSpeaking(); });

  /* «Oye CORT» — escucha permanente opt-in */
  const wake = document.getElementById('wake');
  wake.onclick = () => {
    const on = !voice.wakeOn;
    voice.setWake(on);
    try { window.CortNative && window.CortNative.keepAwake(on); } catch { /* app vieja */ }
    term(on ? 'escucha de activación: «Oye CORT» — activa' : 'escucha de activación apagada', 'voz');
    if (on) add('a', 'Escucha permanente activa: di «Oye CORT» y tu orden.', 'voz');
  };
  if (!voice.available && !IS_ANDROID) { mic.style.display = 'none'; wake.style.display = 'none'; }

  /* gestos — modo ligero */
  import('./gestures.js').then(({ initGestures }) => initGestures({
    video: document.getElementById('camv'), canvas: document.getElementById('gest'),
    button: document.getElementById('hand'), label: document.getElementById('gestlabel'),
    onPalm: () => {                       // palma: desplegar o plegar todas
      orb.burst(); term('gesto: palma → ' +
        (Object.values(W).some(w => w.open && !w.minimized) ? 'plegar ventanas' : 'desplegar ventanas'), 'gestos');
      const anyOpen = Object.values(W).some(w => w.open && !w.minimized);
      anyOpen ? Object.values(W).forEach(w => w.minimize())
              : Object.values(W).forEach(w => w.show());
    },
    onPinch: () => { W.chat.show(); term('gesto: pinza → canal de voz', 'gestos'); sayLine('Canal de voz al frente.'); },
    onFist: () => { hideAll(); orb.burst(); term('gesto: puño → HUD oculto (palma o «muestra todo» para volver)', 'gestos'); },
  }));
}
