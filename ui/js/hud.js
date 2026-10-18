/* ===== HUD de CORT: arranque, ventanas, chat, sensores, voz y gestos ===== */
import { createWin } from './windows.js';

const API = 'http://127.0.0.1:8000';
let orb;

/* ---------- secuencia de arranque ---------- */
const BOOT_LINES = [
  ['CORT BIOS v0.4 ......................... ', 'OK'],
  ['Núcleo holográfico (WebGL) ............. ', 'OK'],
  ['Matriz de partículas: 2600 puntos ...... ', 'OK'],
  ['Enlace con backend (localhost:8000) .... ', null],
  ['Cerebro híbrido: local/online .......... ', null],
  ['Micrófono (Web Speech) ................. ', null],
  ['Memoria persistente (SQLite) ........... ', null],
  ['Sensor de gestos (MediaPipe ligero) .... ', 'LISTO'],
  ['Desplegando ventanas de vidrio …', ''],
];
async function runBoot() {
  const boot = document.getElementById('boot');
  let backendOK = false, brainTxt = '—';
  try {
    const s = await (await fetch(API + '/api/status')).json();
    backendOK = true;
    const b = s.brain;
    brainTxt = [b.ollama && 'local', (b.groq || b.gemini) && 'online',
      (!b.ollama && !b.groq && !b.gemini) && 'offline'].filter(Boolean).join('+');
  } catch { /* sin backend */ }
  for (const [txt, fixed] of BOOT_LINES) {
    const div = document.createElement('div'); div.className = 'line';
    let val = fixed;
    if (fixed === null) {
      if (txt.includes('backend')) val = backendOK ? 'OK' : 'SIN CONEXIÓN';
      if (txt.includes('híbrido')) val = brainTxt;
      if (txt.includes('Micrófono')) val = (window.SpeechRecognition || window.webkitSpeechRecognition) ? 'OK' : 'NO DISPONIBLE';
      if (txt.includes('Memoria')) val = backendOK ? 'OK' : 'EN PAUSA';
    }
    div.innerHTML = txt + (val ? `<span class="${val === 'OK' ? 'ok' : ''}">[${val}]</span>` : '');
    boot.appendChild(div);
    await new Promise(r => setTimeout(r, 140 + Math.random() * 130));
  }
  await new Promise(r => setTimeout(r, 300));
  boot.classList.add('done'); setTimeout(() => boot.remove(), 900);
  return { backendOK, brainTxt };
}

/* ---------- ventanas de vidrio (paneles numerados estilo referencia) ---------- */
let W = {};
function buildWindows() {
  const vw = innerWidth, vh = innerHeight;
  const clamp = (v, min, max) => Math.max(min, Math.min(max, v));   // que nunca se salgan de pantalla
  W.files = createWin({ id: 'files', icon: '🗀', title: '01 · Archivos · <span id="fpath">raíces</span>',
    x: 14, y: 112, w: Math.min(292, vw - 28), h: clamp(vh * .42, 200, 300),
    html: `<div id="ftools"><button id="fgrid" title="vista de mosaico">▦</button><button id="flistbtn" title="vista de lista">☰</button></div><div id="flist"></div>` });
  W.env = createWin({ id: 'env', icon: '◉', title: '02 · Entorno',
    x: 14, y: clamp(112 + vh * .42 + 18, 330, 440), w: Math.min(240, vw - 28),
    html: `<div id="wx">…</div>
      <div style="margin-top:8px;font-size:10px;color:#5e8cab">CPU</div><div class="bar"><i id="bar-cpu" style="width:0"></i></div>
      <div style="font-size:10px;color:#5e8cab">RAM <span id="ramgb"></span></div><div class="bar"><i id="bar-ram" style="width:0"></i></div>
      <div style="font-size:10px;color:#5e8cab">DISCO</div><div class="bar"><i id="bar-disk" style="width:0"></i></div>
      <div id="batt" style="margin-top:6px;font-size:11px"></div>` });
  W.chat = createWin({ id: 'chat', icon: '✦', title: '03 · Canal de voz',
    x: Math.max(14, Math.round(vw / 2) - 190), y: Math.max(140, vh - 386), w: Math.min(380, vw - 28), h: 288,
    html: `<div id="log"></div>
      <div id="inputrow"><span id="prompt" title="↑/↓ historial · Tab completa">cort@nave:~$</span>
      <input id="q" placeholder="háblame, o escribe un comando y pulsa Tab…" autocomplete="off">
      <button id="go">⏎</button></div>` });
  W.notes = createWin({ id: 'notes', icon: '✎', title: '04 · Notas',
    x: Math.round(vw / 2) - 170, y: 118, w: Math.min(340, vw - 28), h: 300,
    html: `<div id="notelist"></div>
      <div id="inputrow"><input id="nota" placeholder="Nueva nota…" autocomplete="off">
      <button id="notago">＋</button></div>` });
  W.music = createWin({ id: 'music', icon: '♪', title: '05 · Música',
    x: clamp(vw - 530, 14, vw - 240), y: clamp(vh - 406, 112, 348), w: Math.min(302, vw - 28), h: clamp(vh * .5, 220, 392),
    html: `<div id="nowplay">— sin reproducción —</div>
      <div id="mbar"><i id="mprog"></i></div>
      <div id="mrow"><button id="mprev">⏮</button><button id="mplay">▶</button>
        <button id="mnext">⏭</button><input id="mvol" type="range" min="0" max="1" step=".02" value=".8">
        <span id="mtime"></span><button id="mref" title="recargar lista">↻</button></div>
      <div id="plist"></div>
      <audio id="aud" crossorigin="anonymous"></audio>` });
  W.term = createWin({ id: 'term', icon: '▤', title: '06 · Consola del sistema',
    x: 14, y: Math.max(140, vh - 268), w: Math.min(340, vw - 28), h: 240,
    html: '<div id="termlog"></div>' });
  W.perfil = createWin({ id: 'perfil', icon: '⚙', title: '07 · Perfil',
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
      <button id="pfguardar" class="pf-btn">Guardar perfil</button>
      <div id="pfmsg" class="pf-msg"></div>` });
  /* muro de recuerdos — la "sala de cuadros" de la referencia, en azul */
  W.cerebro = createWin({ id: 'cerebro', icon: '⌗', title: '08 · Cerebro · <span id="memcount">…</span>',
    x: clamp(Math.round(vw / 2) - 220, 14, Math.max(14, vw - 260)), y: 124,
    w: Math.min(440, vw - 28), h: clamp(vh * .56, 260, 420),
    html: '<div id="memwall"></div>' });
}

/* ---------- ejecutor de música (orbe → disco giratorio) ---------- */
let tracks = [], tIdx = -1, AC = null, AN = null, freqData = null, mAnim = 0;
async function loadMusic() {
  const el = document.getElementById('plist');
  try {
    const r = await (await fetch(API + '/api/music')).json();
    tracks = r.canciones || [];
    el.innerHTML = tracks.length ? '' :
      '<div class="row">pon canciones en ~/Música y pulsa ↻</div>';
    tracks.forEach((t, i) => {
      const d = document.createElement('div'); d.className = 'row track';
      d.innerHTML = `<span>🗎 ${t.nombre.replace(/</g,'&lt;')}</span><span class="fecha">${t.artista.replace(/</g,'&lt;')}</span>`;
      d.onclick = () => playTrack(i);
      el.appendChild(d);
    });
  } catch { el.innerHTML = '<div class="row">backend no disponible</div>'; }
}
function playTrack(i) {
  if (i < 0 || i >= tracks.length) return;
  tIdx = i;
  const aud = document.getElementById('aud');
  aud.src = API + '/api/audio?ruta=' + encodeURIComponent(tracks[i].ruta);
  aud.play();
  document.getElementById('nowplay').textContent = '♪ ' + tracks[i].nombre;
  document.getElementById('mplay').textContent = '⏸';
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
  if (aud.paused) { aud.play(); document.getElementById('mplay').textContent = '⏸'; orb.setDisc(true); startMeter(aud); }
  else { aud.pause(); document.getElementById('mplay').textContent = '▶'; orb.setDisc(false); stopMeter(); }
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
  d.innerHTML = `<b>${String(i).padStart(2, '0')} — ${e.name}</b>
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
    k.innerHTML = `<b>${String(i).padStart(2, '0')} — ${c.name}</b>
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
  while (layer.children.length + Math.min(items.length, 8) > 14) layer.firstChild.remove();
  const a = anchor ? anchor.getBoundingClientRect()
                   : { left: innerWidth * .42, top: innerHeight * .38, width: 120, height: 28 };
  const n = Math.min(items.length, 8);
  items.slice(0, 8).forEach((it, i) => {
    const c = document.createElement('div'); c.className = 'chip';
    c.innerHTML = `<b>${String(it.txt).replace(/</g, '&lt;')}</b>
      <small>${String(it.meta || '').replace(/</g, '&lt;')}</small><span class="x">✕</span>`;
    const ang = (i / n) * Math.PI * 2 + Math.random() * .9;
    const rad = 150 + Math.random() * 100;
    c.style.left = cl(Math.round(a.left + a.width / 2 + Math.cos(ang) * rad - 70), 12, innerWidth - 210) + 'px';
    c.style.top = cl(Math.round(a.top + a.height / 2 + Math.sin(ang) * rad * .62 - 18), 92, innerHeight - 200) + 'px';
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
  spawnChips(ns.slice(-5).reverse().map(x => ({
    txt: x.texto.slice(0, 30), meta: x.fecha.slice(5, 10) + ' · nota',
    act: () => { W.notes.show(); sayLine('Nota: ' + x.texto); } })));
  term('chips de notas lanzados: ' + Math.min(5, ns.length), 'notas');
}
async function chipRecentFiles() {
  const r = await (await fetch(API + '/api/files?path=Documentos')).json();
  const fs = (r.entries || []).filter(e => e.type === 'file').slice(-5).reverse();
  if (!fs.length) { sayLine('No encontré archivos recientes en Documentos.'); return; }
  spawnChips(fs.map(e => ({ txt: e.name, meta: e.fecha.slice(0, 10) + ' · archivo',
    act: () => { W.files.show(); openFiles('Documentos'); sayLine('Archivo ' + e.name + ' seleccionado.'); } })));
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
  d.innerHTML = `<span class="ts">${hh}</span> <span class="tg">${tag}</span> ${txt}`;
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

/* ---------- perfil ---------- */
async function loadProfile() {
  try {
    const p = await (await fetch(API + '/api/profile')).json();
    for (const k of ['asistente', 'usuario', 'tono', 'idioma'])
      if (p[k]) document.getElementById('pf-' + k).value = p[k];
  } catch { /* sin backend */ }
}
async function saveProfile() {
  const vals = {};
  for (const k of ['asistente', 'usuario', 'tono', 'idioma'])
    vals[k] = document.getElementById('pf-' + k).value.trim();
  let n = 0;
  for (const [k, v] of Object.entries(vals)) {
    if (!v) continue; n++;
    await fetch(API + '/api/profile', { method: 'POST',
      headers: { 'content-type': 'application/json' }, body: JSON.stringify({ clave: k, valor: v }) });
  }
  const m = document.getElementById('pfmsg');
  m.textContent = n ? `✓ ${n} preferencias guardadas — el cerebro las usará en la próxima respuesta`
                    : 'nada que guardar';
  term('perfil actualizado (' + n + ' campos)', 'perfil');
  orb.burst();
  setTimeout(() => m.textContent = '', 4000);
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
function openCortex() { W.cerebro.show(); refreshMemories(); }

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
      `<span style="color:#5e8cab">${s.system}</span>`;
    const m = s.system.match(/CPU (\d+)\s*% · RAM (\d+)\s*% \(([\d.]+) de ([\d.]+) GB\) · Disco (\d+)\s*%/);
    if (m) {
      setBar('cpu', m[1]); setBar('ram', m[2]); setBar('disk', m[5]);
      document.getElementById('ramgb').textContent = `${m[3]} / ${m[4]} GB`;
    }
    document.getElementById('batt').textContent = s.battery;
  } catch {
    el.innerHTML = `<span class="dot off"></span> backend no detectado (puerto 8000)`;
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
  if (r.error) { list.innerHTML = `<div class="row">⚠ ${r.error}</div>`; return; }
  const rows = [];
  if (path) rows.push({ name: '↩ ..', dir: path.split('/').slice(0, -1).join('/') });
  for (const e of r.entries) rows.push({
    name: (e.type === 'dir' ? '🗁 ' : '🗎 ') + e.name,
    dir: path ? path + '/' + e.name : e.name, type: e.type, size: e.size,
    fecha: e.fecha });
  list.innerHTML = '';
  list.classList.toggle('grid', fGrid);
  rows.forEach((row, i) => {
    const d = document.createElement('div');
    d.style.animationDelay = (i * 16) + 'ms';
    if (fGrid) {
      d.className = 'tile';
      d.innerHTML = `<span class="ti">${row.type === 'file' ? '🗎' : (row.name.includes('..') ? '↩' : '🗁')}</span>
        <span class="tn">${row.name.replace(/^(🗁|🗎)\s*/, '')}</span>`;
    } else {
      d.className = 'row';
      d.innerHTML = `<span>${row.name}</span>` +
        (row.fecha ? `<span class="fecha">${row.fecha.slice(0, 10)}</span>` : '') +
        (row.type === 'file' && row.size ? `<span class="size">${row.size > 1e6 ? (row.size / 1e6).toFixed(1) + ' MB' : Math.round(row.size / 1e3) + ' KB'}</span>` : '');
    }
    d.onclick = row.type === 'file'
      ? () => { sayLine(`Archivo ${row.name} seleccionado.`); term('archivo: ' + row.name, 'archivos'); }
      : () => openFiles(row.dir);
    list.appendChild(d);
  });
  document.getElementById('fpath').textContent = (path || 'raíces') + ' · ' + rows.length + ' items';
  term('listando ' + (path || 'raíces') + ' (' + rows.length + ' entradas)', 'archivos');
}

/* ---------- chat + voz ---------- */
function add(cls, text, src) {
  const p = document.createElement('p'); p.className = cls; p.textContent = text;
  if (src) { const s = document.createElement('span'); s.className = 'src'; s.textContent = ' [' + src + ']'; p.appendChild(s); }
  const log = document.getElementById('log');
  log.appendChild(p); log.scrollTop = log.scrollHeight;
}
function sayLine(text) { add('a', text, 'voz'); orb.speak(2200); speakTTS(text); }
function speakTTS(text) {
  if (!('speechSynthesis' in window)) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text.slice(0, 400));
  u.lang = 'es-MX'; u.rate = 1.05; speechSynthesis.speak(u);
}
/* ---------- consola de comandos: historial ↑/↓ y Tab que completa ---------- */
const HIST = [];
let hIdx = 0, draft = '';
const CMDS = ['reproduce', 'pausa', 'reanuda', 'modo oficina', 'oculta todo', 'muestra todo',
  'muéstrame las notas', 'archivos recientes', 'recoge los chips', '¿qué hora es?',
  'abre youtube', 'abre el navegador', 'apunta ', 'muéstrame tu cerebro', 'qué recuerdas'];
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
  if (HIST[HIST.length - 1] !== msg) HIST.push(msg);
  hIdx = HIST.length; draft = '';
  setState('pensando');
  document.getElementById('top').classList.add('glitch');
  setTimeout(() => document.getElementById('top').classList.remove('glitch'), 800);
  orb.activate();                                    // ← vórtice de activación (referencia)
  term('consulta: "' + msg.slice(0, 40) + '"', 'voz');
  /* peticiones de música: "reproduce …" — primero tu playlist (por nombre de
     canción o artista); si no, el reproductor predeterminado del sistema */
  if (/reproduc|suena|\bpon\b|reproductor|vlc|playlist|un tema|una canci[oó]n/i.test(msg)) {
    const clean = msg
      .replace(/por\s+fav?or|reproduc\w*|suena|pon(er|ga|me)?|reproductor|vlc|playlist|un[ao]?\s+(canci[oó]n|tema)|la\s+m[uú]sica|m[uú]sica|\b(de|en|mi|el|que)\b/gi, ' ')
      .replace(/\s+/g, ' ').trim();
    let i = -1;
    if (clean.length > 2 && tracks.length) {
      const c = clean.toLowerCase();
      i = tracks.findIndex(t => t.nombre.toLowerCase().includes(c) || t.artista.toLowerCase().includes(c));
    }
    if (i >= 0) {
      playTrack(i);
      add('a', `Reproduciendo «${tracks[i].nombre}» de ${tracks[i].artista} en el ejecutor de CORT.`, 'ejecutor');
      speakTTS('Reproduciendo ' + tracks[i].nombre);
      return;
    }
    try {
      const r = await (await fetch(API + '/api/play', { method: 'POST',
        headers: { 'content-type': 'application/json' }, body: '{}' })).json();
      if (r.ok) {
        add('a', (clean ? `No la encontré en tu playlist, así que abrí tu reproductor predeterminado con ` :
                    `Abriendo tu reproductor predeterminado con `) + `«${r.cancion}».`, 'ejecutor');
        term('ejecutado en el sistema: ' + r.cancion, 'ejecutor');
        speakTTS('Abriendo tu reproductor con ' + r.cancion);
      } else add('a', 'No encontré música en tu carpeta Música: ' + (r.error || ''), 'error');
    } catch { add('a', 'Sin conexión con el backend para ejecutar música.', 'error'); }
    return;
  }
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
  if (/\bpausa\b|mets pausa|det[eé]n la m[uú]sica|alto a la m[uú]sica/i.test(msg)) {
    pauseMusic();
    add('a', 'Música en pausa, como en la referencia.', 'ejecutor');
    speakTTS('Pausa'); term('pausa de reproducción', 'música'); return;
  }
  if (/reanuda|continua (la )?m[uú]sica|sigue con la m[uú]sica|play de nuevo/i.test(msg)) {
    resumeMusic();
    add('a', 'Continuando la reproducción.', 'ejecutor');
    speakTTS('Continuando'); term('reanudada', 'música'); return;
  }
  if (/qu[eé] hora es|dime la hora|hora actual/i.test(msg)) {
    const h = new Date().toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
    add('a', `Son las ${h} — hora local, sin necesitar internet (como en el video).`, 'sistema');
    speakTTS('Son las ' + h); orb.burst(); term('hora local: ' + h, 'sistema'); return;
  }
  const mAbrir = msg.match(/\babre\b|\babrir\b|\blanza\b|\abinicia\b/i);
  if (mAbrir && /youtube|navegador/i.test(msg)) {
    const app = /youtube/i.test(msg) ? 'youtube' : 'navegador';
    add('a', `Lanzando ${app}…`, 'ejecutor'); term('launch: ' + app, 'ejecutor');
    try {
      const r = await (await fetch(API + '/api/launch', { method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ app }) })).json();
      add('a', r.ok ? `Aplicación lanzada: ${r.app} ✓` : 'El backend lo bloqueó: ' + (r.error || ''),
        'ejecutor');
      speakTTS(r.ok ? 'Aplicación lanzada' : 'No pude lanzar la aplicación');
    } catch {
      window.open(app === 'youtube' ? 'https://www.youtube.com' : 'https://duckduckgo.com');
      add('a', 'Sin backend: lo abrí directo en el navegador.', 'error');
    }
    return;
  }
  try {
    const r = await (await fetch(API + '/api/chat', { method: 'POST',
      headers: { 'content-type': 'application/json' }, body: JSON.stringify({ message: msg }) })).json();
    add('a', r.reply, r.source); orb.burst(); speakTTS(r.reply);   // ← animación de acción
    setState('hablando');
    term('respuesta vía ' + r.source, 'cerebro');
    if (/archivo|carpeta|explorador/i.test(msg)) openFiles();
    if (/nota|apunta|recuerda/i.test(msg)) { W.notes.show(); addNoteFromChat(msg); }
  } catch { add('a', 'Sin conexión con el backend. Ejecuta scripts/run.', 'error'); setState('error'); }
}
async function addNoteFromChat(msg) {
  const t = msg.replace(/^(apunta|nota|recuerda)[\s:]+/i, '').trim();
  if (t && t !== msg) {
    await fetch(API + '/api/notes', { method: 'POST',
      headers: { 'content-type': 'application/json' }, body: JSON.stringify({ texto: t }) });
    term('nota guardada desde el chat', 'notas'); refreshNotes();
  }
}

/* ---------- todo junto ---------- */
export function wireUI(orbRef) {
  orb = orbRef;
  buildWindows();
  term('CORT BIOS v0.4 — núcleo holográfico en línea', 'arranque');
  runBoot().then(({ backendOK }) => {
    setState(backendOK ? 'listo' : 'error');
    term(backendOK ? 'backend conectado (localhost:8000)' : 'backend NO detectado', 'arranque');
    add('a', backendOK ? 'Sistemas en línea. CORT a sus órdenes.' :
      'Backend no detectado: ejecuta scripts/run.sh (Linux) o run.bat (Windows).',
      backendOK ? 'sistema' : 'error');
    if (backendOK) {
      refreshStatus(); refreshWeather(); refreshNotes(); loadProfile(); refreshTree();
      // los paneles se despliegan en cascada numerada, como en la referencia
      setTimeout(() => W.chat.show(), 150);
      setTimeout(() => { openFiles(); }, 500);
      setTimeout(() => W.env.show(), 800);
      setTimeout(() => W.music.show(), 1100);
      setTimeout(() => W.term.show(), 1400);
      setTimeout(chipNotes, 2600);      // bienvenida estilo Jared: notas flotando
    }
    setInterval(refreshStatus, 10000);
    setInterval(refreshWeather, 10 * 60000);
    setInterval(refreshTree, 5 * 60000);
  });

  document.getElementById('go').onclick = () => send();
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

  /* micrófono */
  const mic = document.getElementById('mic');
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SR) {
    const rec = new SR(); rec.lang = 'es-MX'; rec.interimResults = false;
    let on = false;
    mic.onclick = () => { on ? rec.stop() : rec.start(); };
    rec.onstart = () => { on = true; mic.classList.add('on'); orb.listen(true); setState('escucha'); };
    rec.onend = () => { on = false; mic.classList.remove('on'); orb.listen(false); setState('reposo'); };
    rec.onresult = e => send(e.results[0][0].transcript);

    /* wake word "Oye CORT" — escucha permanente opt-in (botón 👂) */
    const wake = document.getElementById('wake');
    let wakeOn = false, wakeRec = null;
    wake.onclick = () => {
      wakeOn = !wakeOn;
      wake.classList.toggle('on', wakeOn);
      if (wakeOn) {
        term('escucha de activación: «Oye CORT» — activa', 'voz');
        startWake();
      } else if (wakeRec) { wakeRec.stop(); wakeRec = null; }
    };
    function startWake() {
      if (!wakeOn) return;
      wakeRec = new SR(); wakeRec.lang = 'es-MX'; wakeRec.interimResults = false;
      wakeRec.continuous = false;
      wakeRec.onresult = e => {
        const t = e.results[0][0].transcript;
        if (/oye\s+cort|cort[,.]?$/i.test(t)) {
          term('palabra de activación detectada: "' + t + '"', 'voz');
          orb.activate(); W.chat.show();                     // vórtice al ser llamada
          sayLine('¿Sí?'); send(t.replace(/oye\s+cort[,.\s]*/i, ''));
        }
      };
      wakeRec.onend = () => { if (wakeOn) setTimeout(startWake, 400); };
      wakeRec.onerror = err => { if (wakeOn && err === 'not-allowed') { wakeOn = false; wake.classList.remove('on'); } };
      try { wakeRec.start(); } catch { /* ya activa */ }
    }
  } else { mic.style.display = 'none'; document.getElementById('wake').style.display = 'none'; }

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
