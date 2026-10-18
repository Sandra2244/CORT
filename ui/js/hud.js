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

/* ---------- ventanas de vidrio ---------- */
let W = {};
function buildWindows() {
  const vw = innerWidth, vh = innerHeight;
  W.files = createWin({ id: 'files', icon: '🗀', title: 'Archivos · <span id="fpath">raíces</span>',
    x: 14, y: 112, w: Math.min(300, vw - 28), h: Math.min(340, vh * .48),
    html: '<div id="flist"></div>' });
  W.env = createWin({ id: 'env', icon: '◉', title: 'Entorno',
    x: vw - 254, y: 112, w: 240,
    html: `<div id="wx">…</div>
      <div style="margin-top:8px;font-size:10px;color:#5e8cab">CPU</div><div class="bar"><i id="bar-cpu" style="width:0"></i></div>
      <div style="font-size:10px;color:#5e8cab">RAM <span id="ramgb"></span></div><div class="bar"><i id="bar-ram" style="width:0"></i></div>
      <div style="font-size:10px;color:#5e8cab">DISCO</div><div class="bar"><i id="bar-disk" style="width:0"></i></div>
      <div id="batt" style="margin-top:6px;font-size:11px"></div>` });
  W.chat = createWin({ id: 'chat', icon: '✦', title: 'CORT · canal de voz',
    x: Math.max(14, vw - 394), y: vh - 306, w: Math.min(380, vw - 28), h: 288,
    html: `<div id="log"></div>
      <div id="inputrow"><input id="q" placeholder="Háblame, CORT está escuchando…" autocomplete="off">
      <button id="go">⏎</button></div>` });
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
async function openFiles(path = '') {
  W.files.show();
  const list = document.getElementById('flist');
  list.innerHTML = '<div class="row">cargando…</div>';
  const r = await (await fetch(API + '/api/files?path=' + encodeURIComponent(path))).json();
  if (r.error) { list.innerHTML = `<div class="row">⚠ ${r.error}</div>`; return; }
  const rows = [];
  if (path) rows.push({ name: '↩ ..', dir: path.split('/').slice(0, -1).join('/') });
  for (const e of r.entries) rows.push({
    name: (e.type === 'dir' ? '🗁 ' : '🗎 ') + e.name,
    dir: path ? path + '/' + e.name : e.name, type: e.type, size: e.size });
  list.innerHTML = '';
  rows.forEach((row, i) => {
    const d = document.createElement('div');
    d.className = 'row'; d.style.animationDelay = (i * 16) + 'ms';
    d.innerHTML = `<span>${row.name}</span>` +
      (row.size ? `<span class="size">${row.size > 1e6 ? (row.size / 1e6).toFixed(1) + ' MB' : Math.round(row.size / 1e3) + ' KB'}</span>` : '');
    d.onclick = row.type === 'file'
      ? () => sayLine(`Archivo ${row.name} seleccionado.`)
      : () => openFiles(row.dir);
    list.appendChild(d);
  });
  document.getElementById('fpath').textContent = path || 'raíces';
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
  orb.speak(900);
  try {
    const r = await (await fetch(API + '/api/chat', { method: 'POST',
      headers: { 'content-type': 'application/json' }, body: JSON.stringify({ message: msg }) })).json();
    add('a', r.reply, r.source); orb.speak(3200); speakTTS(r.reply);
    if (/archivo|carpeta|explorador/i.test(msg)) openFiles();
  } catch { add('a', 'Sin conexión con el backend. Ejecuta scripts/run.', 'error'); }
}

/* ---------- todo junto ---------- */
export function wireUI(orbRef) {
  orb = orbRef;
  buildWindows();
  runBoot().then(({ backendOK }) => {
    add('a', backendOK ? 'Sistemas en línea. CORT a sus órdenes.' :
      'Backend no detectado: ejecuta scripts/run.sh (Linux) o run.bat (Windows).',
      backendOK ? 'sistema' : 'error');
    if (backendOK) {
      refreshStatus(); refreshWeather();
      // las ventanas se despliegan en cascada, como en la referencia
      setTimeout(() => W.chat.show(), 150);
      setTimeout(() => { openFiles(); }, 500);
      setTimeout(() => W.env.show(), 800);
    }
    setInterval(refreshStatus, 10000);
    setInterval(refreshWeather, 10 * 60000);
  });

  document.getElementById('go').onclick = () => send();
  document.getElementById('q').addEventListener('keydown', e => { if (e.key === 'Enter') send(); });

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
  } else mic.style.display = 'none';

  /* gestos — modo ligero */
  import('./gestures.js').then(({ initGestures }) => initGestures({
    video: document.getElementById('camv'), canvas: document.getElementById('gest'),
    button: document.getElementById('hand'), label: document.getElementById('gestlabel'),
    onPalm: () => {                       // palma: desplegar o plegar todas
      orb.speak(1800);
      const anyOpen = Object.values(W).some(w => w.open && !w.minimized);
      anyOpen ? Object.values(W).forEach(w => w.minimize())
              : Object.values(W).forEach(w => w.show());
    },
    onPinch: () => { W.chat.show(); sayLine('Canal de voz al frente.'); },
    onFist: () => { Object.values(W).forEach(w => w.close()); orb.speak(2600); },
  }));
}
