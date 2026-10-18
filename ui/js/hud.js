/* ===== HUD de CORT: arranque, chat, archivos, clima, voz ===== */
const API = 'http://127.0.0.1:8000';
let orb; // se inyecta desde index.html

/* ---------- secuencia de arranque (como en los videos de referencia) ---------- */
const BOOT_LINES = [
  ['CORT BIOS v0.3 ......................... ', 'OK'],
  ['Núcleo holográfico (WebGL) ............. ', 'OK'],
  ['Matriz de partículas: 2600 puntos ...... ', 'OK'],
  ['Enlace con backend (localhost:8000) .... ', null],   // se resuelve en vivo
  ['Cerebro híbrido: local/online .......... ', null],   // se resuelve en vivo
  ['Micrófono (Web Speech) ................. ', null],   // se resuelve en vivo
  ['Memoria persistente (SQLite) ........... ', null],   // se resuelve en vivo
  ['Desplegando interfaz …', ''],
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

  for (let i = 0; i < BOOT_LINES.length; i++) {
    const [txt, fixed] = BOOT_LINES[i];
    const div = document.createElement('div');
    div.className = 'line';
    let val = fixed;
    if (fixed === null) {
      if (txt.includes('backend')) val = backendOK ? 'OK' : 'SIN CONEXIÓN';
      if (txt.includes('híbrido')) val = brainTxt;
      if (txt.includes('Micrófono')) val = (window.SpeechRecognition || window.webkitSpeechRecognition) ? 'OK' : 'NO DISPONIBLE';
      if (txt.includes('Memoria')) val = backendOK ? 'OK' : 'EN PAUSA';
    }
    div.innerHTML = txt + (val ? `<span class="${val==='OK'?'ok':''}">[${val}]</span>` : '');
    boot.appendChild(div);
    await new Promise(r => setTimeout(r, 160 + Math.random() * 140));
  }
  await new Promise(r => setTimeout(r, 350));
  boot.classList.add('done');
  setTimeout(() => boot.remove(), 900);
  return { backendOK, brainTxt };
}

/* ---------- reloj ---------- */
setInterval(() => document.getElementById('clock').textContent =
  new Date().toLocaleTimeString('es-MX', { hour12: false }), 500);

/* ---------- estado del cerebro ---------- */
async function refreshStatus() {
  const el = document.getElementById('status');
  try {
    const s = await (await fetch(API + '/api/status')).json();
    const b = s.brain;
    const dot = ok => `<span class="dot ${ok ? 'on' : 'off'}"></span>`;
    el.innerHTML =
      `${dot(b.ollama)} local ${b.ollama ? '· ' + b.ollama_model : '(no disponible)'}<br>` +
      `${dot(b.groq || b.gemini)} online ${b.groq ? '· Groq' : (b.gemini ? '· Gemini' : '(sin API key)')}<br>` +
      `<span style="color:#5e8cab">${s.system}</span>`;
    // barras del panel de entorno
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
function setBar(id, pct) {
  const b = document.getElementById('bar-' + id);
  b.style.width = pct + '%';
  b.parentElement.title = id.toUpperCase() + ' ' + pct + '%';
}

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

/* ---------- panel de archivos ---------- */
let filesOpen = true;
async function openFiles(path = '') {
  const panel = document.getElementById('files');
  panel.classList.remove('hidden-left');
  const list = document.getElementById('flist');
  list.innerHTML = '<div class="row">cargando…</div>';
  const r = await (await fetch(API + '/api/files?path=' + encodeURIComponent(path))).json();
  if (r.error) { list.innerHTML = `<div class="row">⚠ ${r.error}</div>`; return; }
  const rows = [];
  if (path) rows.push({ name: '↩ ..', dir: path.split('/').slice(0, -1).join('/') });
  for (const e of r.entries) rows.push({ name: (e.type === 'dir' ? '📁 ' : '📄 ') + e.name,
    dir: path ? path + '/' + e.name : e.name, type: e.type, size: e.size });
  list.innerHTML = '';
  rows.forEach((row, i) => {
    const d = document.createElement('div');
    d.className = 'row'; d.style.animationDelay = (i * 18) + 'ms';
    d.innerHTML = `<span>${row.name}</span>` +
      (row.size ? `<span class="size">${row.size > 1e6 ? (row.size / 1e6).toFixed(1) + ' MB' : Math.round(row.size / 1e3) + ' KB'}</span>` : '');
    if (row.type !== 'file' || !row.type) d.onclick = () => openFiles(row.dir);
    else d.onclick = () => sayLine(`Archivo ${row.name} seleccionado, señorita.`);
    list.appendChild(d);
  });
  document.getElementById('fpath').textContent = path || 'raíces';
}
function toggleFiles() {
  filesOpen = !filesOpen;
  document.getElementById('files').classList.toggle('hidden-left', !filesOpen);
}

/* ---------- chat + voz ---------- */
const log = document.getElementById('log');
function add(cls, text, src) {
  const p = document.createElement('p'); p.className = cls; p.textContent = text;
  if (src) { const s = document.createElement('span'); s.className = 'src'; s.textContent = ' [' + src + ']'; p.appendChild(s); }
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

export function wireUI(orbRef) {
  orb = orbRef;
  document.getElementById('go').onclick = () => send();
  document.getElementById('q').addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
  document.querySelector('#files header').onclick = toggleFiles;

  runBoot().then(({ backendOK }) => {
    add('a', backendOK ? 'Sistemas en línea. CORT a sus órdenes.' :
      'Backend no detectado: ejecuta scripts/run.sh (Linux) o run.bat (Windows).',
      backendOK ? 'sistema' : 'error');
    if (backendOK) { refreshStatus(); refreshWeather(); openFiles(); }
    setInterval(refreshStatus, 10000);
    setInterval(refreshWeather, 10 * 60000);
  });

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
}
