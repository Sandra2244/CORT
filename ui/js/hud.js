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
    x: vw - 254, y: 112, w: 240,
    html: `<div id="wx">…</div>
      <div style="margin-top:8px;font-size:10px;color:#5e8cab">CPU</div><div class="bar"><i id="bar-cpu" style="width:0"></i></div>
      <div style="font-size:10px;color:#5e8cab">RAM <span id="ramgb"></span></div><div class="bar"><i id="bar-ram" style="width:0"></i></div>
      <div style="font-size:10px;color:#5e8cab">DISCO</div><div class="bar"><i id="bar-disk" style="width:0"></i></div>
      <div id="batt" style="margin-top:6px;font-size:11px"></div>` });
  W.chat = createWin({ id: 'chat', icon: '✦', title: '03 · Canal de voz',
    x: Math.max(14, Math.round(vw / 2) - 190), y: Math.max(140, vh - 386), w: Math.min(380, vw - 28), h: 288,
    html: `<div id="log"></div>
      <div id="inputrow"><input id="q" placeholder="Háblame, CORT está escuchando…" autocomplete="off">
      <button id="go">⏎</button></div>` });
  W.notes = createWin({ id: 'notes', icon: '✎', title: '04 · Notas',
    x: Math.round(vw / 2) - 170, y: 118, w: Math.min(340, vw - 28), h: 300,
    html: `<div id="notelist"></div>
      <div id="inputrow"><input id="nota" placeholder="Nueva nota…" autocomplete="off">
      <button id="notago">＋</button></div>` });
  W.music = createWin({ id: 'music', icon: '♪', title: '05 · Música',
    x: clamp(vw - 316, 14, vw - 240), y: clamp(vh - 406, 112, 348), w: Math.min(302, vw - 28), h: clamp(vh * .5, 220, 392),
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

/* ---------- reloj y estado (siempre fijos) ---------- */
setInterval(() => document.getElementById('clock').textContent =
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
        (row.size ? `<span class="size">${row.size > 1e6 ? (row.size / 1e6).toFixed(1) + ' MB' : Math.round(row.size / 1e3) + ' KB'}</span>` : '');
    }
    d.onclick = row.type === 'file'
      ? () => { sayLine(`Archivo ${row.name} seleccionado.`); term('archivo: ' + row.name, 'archivos'); }
      : () => openFiles(row.dir);
    list.appendChild(d);
  });
  document.getElementById('fpath').textContent = path || 'raíces';
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
async function send(raw) {
  const q = document.getElementById('q');
  const msg = (raw ?? q.value).trim(); if (!msg) return;
  q.value = ''; add('u', msg);
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
  try {
    const r = await (await fetch(API + '/api/chat', { method: 'POST',
      headers: { 'content-type': 'application/json' }, body: JSON.stringify({ message: msg }) })).json();
    add('a', r.reply, r.source); orb.burst(); speakTTS(r.reply);   // ← animación de acción
    term('respuesta vía ' + r.source, 'cerebro');
    if (/archivo|carpeta|explorador/i.test(msg)) openFiles();
    if (/nota|apunta|recuerda/i.test(msg)) { W.notes.show(); addNoteFromChat(msg); }
  } catch { add('a', 'Sin conexión con el backend. Ejecuta scripts/run.', 'error'); }
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
    term(backendOK ? 'backend conectado (localhost:8000)' : 'backend NO detectado', 'arranque');
    add('a', backendOK ? 'Sistemas en línea. CORT a sus órdenes.' :
      'Backend no detectado: ejecuta scripts/run.sh (Linux) o run.bat (Windows).',
      backendOK ? 'sistema' : 'error');
    if (backendOK) {
      refreshStatus(); refreshWeather(); refreshNotes(); loadProfile();
      // los paneles se despliegan en cascada numerada, como en la referencia
      setTimeout(() => W.chat.show(), 150);
      setTimeout(() => { openFiles(); }, 500);
      setTimeout(() => W.env.show(), 800);
      setTimeout(() => W.music.show(), 1100);
      setTimeout(() => W.term.show(), 1400);
    }
    setInterval(refreshStatus, 10000);
    setInterval(refreshWeather, 10 * 60000);
  });

  document.getElementById('go').onclick = () => send();
  document.getElementById('q').addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
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

  /* micrófono */
  const mic = document.getElementById('mic');
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SR) {
    const rec = new SR(); rec.lang = 'es-MX'; rec.interimResults = false;
    let on = false;
    mic.onclick = () => { on ? rec.stop() : rec.start(); };
    rec.onstart = () => { on = true; mic.classList.add('on'); orb.listen(true); };
    rec.onend = () => { on = false; mic.classList.remove('on'); orb.listen(false); };
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
    onFist: () => { Object.values(W).forEach(w => w.close()); orb.burst(); term('gesto: puño → todo cerrado', 'gestos'); },
  }));
}
