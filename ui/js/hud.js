/* ===== HUD de CORT: arranque, ventanas, chat, sensores, voz y gestos ===== */
import { createWin } from './windows.js';
import { createVoice, perms } from './voice.js';
import { initPantallas, porVoz, ir, modoJuego, fraseSinNucleo } from './pantallas.js';
/* La cara de la ronda 2.1 (`equipo`: voz, mando, cerebro, memoria y trajes). Se
   importa SÓLO esto: `hud.js` no habla con `window.CortNative` de estas familias,
   habla a través del módulo — él es quien sabe si el puente trae `accion()`,
   `mente()` o `burbuja()`, y él es quien degrada con la frase honesta. */
import { telefonoPorVoz, handleTelefonoEvento, estadoTelefono } from './telefono.js';

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
    html: `<div id="ftools"><button id="fgrid" title="vista de mosaico">${ic('grid')}</button><button id="flistbtn" title="vista de lista">${ic('list')}</button><button id="fordena" title="preparar el orden de esta carpeta (no mueve nada hasta que digas confirmar)">⤢ ordena</button></div><div id="fplan"></div><div id="flist"></div>` });
  W.env = createWin({ id: 'env', onShow: () => { refreshStatus(); refreshWeather(); }, icon: '◉', title: '02 · Entorno',
    x: 14, y: clamp(112 + vh * .42 + 18, 330, 440), w: Math.min(240, vw - 28),
    html: `<div id="wx">…</div>
      <input id="wx-ciudad" style="width:100%;margin-top:4px;font-size:10px"
        placeholder="otra ciudad (Enter): Sevilla" autocomplete="off">
      <div id="envscope" style="font-size:10px;color:#5e8cab"></div>
      <div style="margin-top:8px;font-size:10px;color:#5e8cab">CPU <span id="envcpu"></span></div><div class="bar"><i id="bar-cpu" style="width:0"></i></div>
      <div style="font-size:10px;color:#5e8cab">RAM <span id="ramgb"></span></div><div class="bar"><i id="bar-ram" style="width:0"></i></div>
      <div style="font-size:10px;color:#5e8cab">DISCO <span id="envdisk"></span></div><div class="bar"><i id="bar-disk" style="width:0"></i></div>
      <div id="batt" style="margin-top:6px;font-size:11px"></div>
      <div id="sens" style="margin-top:6px;font-size:10px;max-height:132px;overflow:auto"></div>
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
      <label class="pf">Tu ciudad (para el clima)</label>
      <input class="pf" id="pf-ciudad" placeholder="Sevilla">
      <div class="pf-sec">▸ Segundo plano</div>
      <div id="bgbox">
        <button id="bgtoggle" class="bg-toggle"><span class="sw"></span><b>Que CORT se quede en segundo plano</b></button>
        <div class="bg-help">Al irte de la app queda un <b>aviso fijo de CORT</b>: la música y el
          <b>doble toque del auricular</b> siguen obedeciendo. El micrófono se cierra para no
          trabar el teléfono, así que «Oye CORT» con la app cerrada <b>no</b> funciona —la palabra
          de activación de Google tampoco viaja en este APK—; para eso tienes que abrir la cara o
          tocar la <b>burbuja</b>.</div>
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
        <li><b>Alt + ← / →</b> cambiar de pantalla</li>
        <li><b>Alt + 1…5</b> saltar a una pantalla</li>
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
        <li><b>☰ · Pantallas</b> el orbe, la música, el <b>MV</b> (el vídeo con su letra),
          la <b>charla</b> con tus modelos y el <b>código</b> (terminal). Se cambia con ☰,
          deslizando el dedo a un lado, con <b>Alt + ←/→</b> o diciéndolo: «abre el chat»,
          «pantalla de código», «abre el mv», «vuelve al orbe». En otra pantalla el orbe y
          sus ventanas se apagan: no se tapan (en MV el orbe se queda, hecho un disco
          chiquito en la esquina)</li>
        <li><b>⤢ ordena</b> (en 01 · Archivos) o «ordena mis archivos / mis documentos /
          la música»: CORT propone el plan y <b>no mueve nada</b> hasta que digas
          «confirmar»; con «cancelar» se queda como estaba</li>
        <li><b>🎮 modo juego</b> (en el teléfono) deja a CORT sordo y callada mientras
          juegas; «vuelve CORT» le devuelve el oído · «revisa si hay actualizaciones»
          compara tu CORT con la Release y, si dices «sí», prepara la reparación</li>
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
const PF_KEYS = ['asistente', 'usuario', 'tono', 'idioma', 'ciudad', 'voz', 'voz_tono', 'voz_velocidad'];
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
    /* La ciudad guardada manda al panel de Entorno y al cerebro por voz: si la
       caja ya tiene algo escrito (la dueña la cambió en esta sesión), no se pisa. */
    perfilCiudad = p.ciudad || '';
    const wcj = document.getElementById('wx-ciudad');
    if (wcj && !wcj.value && perfilCiudad) wcj.value = perfilCiudad;
    // El arranque ya pintó el tiempo por IP; con ciudad guardada se repinta una vez.
    if (perfilCiudad) refreshWeather();
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

const ACTIVOS = ['descargando', 'en cola', 'encendiendo', 'cancelando'];

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
    const detalle = d.estado === 'error' ? (d.error || 'error')
      : `${d.detalle || d.estado}${d.mb_total ? ` · ${d.vel || 0} MB/s` : ''}`;
    caja.innerHTML = `<div class="mo-bar"><i style="width:${pct}%"></i></div>` +
      `<span class="mo-pt${d.estado === 'error' ? ' mal' : (ACTIVOS.includes(d.estado) ? '' : ' ok')}">${esc(detalle)}</span>` +
      (ACTIVOS.includes(d.estado)
        ? `<button class="mo-b x" data-cancel="${esc(nombre)}">✕ cancelar</button>` : '');
    if (d.estado === 'listo' && !MOrefresca) { termino = true; }
  });
  lista.querySelectorAll('[data-cancel]').forEach(b => b.onclick = () => cancelarDescarga(b.dataset.cancel));
  if (termino) { MOrefresca = true; setTimeout(() => { MOrefresca = false; refreshModels(); }, 1200); }
}

async function cancelarDescarga(nombre) {
  try {
    const r = await post('/api/models/cancel', { modelo: nombre });
    sayLine(r.ok ? `Corto la descarga de ${nombre}.` : `No lo corté: ${r.error || 'ya había terminado'}`);
    term(`cancelar ${nombre}: ${r.ok ? 'cortando' : (r.error || '')}`, 'modelos');
    pintarProgresos();
  } catch { sayLine('El núcleo no respondió.'); }
}

let OPT = null, OPTtimer = 0;
async function refreshOptimize(fresco) {
  const box = document.getElementById('optr'), st = document.getElementById('optram');
  if (!box) return;
  if (!OPT) box.innerHTML = '<div class="mo-none">midiendo memoria y procesos…</div>';
  // Mientras el núcleo recorre el disco, el micrófono del teléfono (o del
  // navegador) no debe estar alborotado: se suspende y se reanuda al terminar.
  voice.suspender('optimizando');
  try { OPT = await getJSON('/api/optimize' + (fresco ? '?fresco=1' : '')); }
  catch { voice.reanudar('optimizando'); box.innerHTML = '<div class="mo-warn">sin conexión con el núcleo.</div>'; return; }
  const r = OPT.ram;
  if (st) st.textContent = `${r.usado_pct} % en uso`;
  const contando = OPT.midiendo && !OPT.caches.length;
  box.innerHTML =
    `<div class="op-bar"><i style="width:${r.usado_pct}%"></i><span>${r.usado_pct} % de ${r.total_gb} GB</span></div>
     <div class="mo-sum">libre <b>${r.disponible_mb} MB</b> · intercambio <b>${r.intercambio_mb} MB</b> ·
       ${contando ? 'contando la caché del disco…'
                  : `caché borrable <b>${OPT.liberable_mb} MB</b>${OPT.modelos_gb ? ` · modelos en el disco <b>${OPT.modelos_gb} GB</b>` : ''}`}</div>
     <div class="hp-sec">▸ Lo que más come memoria</div>
     <div class="op-procs">${OPT.procesos.map(p => `
       <div class="op-proc"><span class="n">${esc(p.nombre)}</span><span class="mb">${Math.round(p.mb)} MB</span>
         ${p.intocable ? '<span class="mo-tag t-no">fijo</span>'
                       : `<button class="mo-b x" data-kill="${p.pid}" title="cerrar ${esc(p.nombre)}">✕</button>`}</div>`).join('')}</div>
     <div class="hp-sec">▸ Caché en disco${OPT.medido_hace != null && !OPT.midiendo ? ` · medido hace ${OPT.medido_hace} s` : ''}</div>
     <div class="op-caches">${OPT.caches.map(c => `
       <div class="op-cache ${c.nivel}"><span class="n">${esc(c.ruta.replace(/^\.?cache\//, ''))}</span>
         <span class="mb">${Math.round(c.mb)} MB</span>
         <small>${esc(c.que)}${c.aprox ? ' ·≈' : ''}${c.abierta ? ' · programa abierto' : ''}</small></div>`).join('')
       || (contando ? '<div class="mo-none">el núcleo está recorriendo las carpetas: vuelve a preguntar en un momento</div>'
                    : '<div class="mo-none">no encontré cachés grandes</div>')}</div>
     <div class="mo-btns">
       <button class="mo-b" data-op="fresco">↻ Analizar de nuevo</button>
       <button class="mo-b d" data-op="seguro" ${contando ? 'disabled' : ''}>⌁ Limpiar segura (${OPT.liberable_mb} MB)</button>
       ${OPT.todo_mb > OPT.liberable_mb ? `<button class="mo-b x" data-op="todo">Limpiar también «cuidado» (${OPT.todo_mb} MB)</button>` : ''}
       ${OPT.papelera_mb ? `<button class="mo-b x" data-op="papelera">✕ Vaciar papelera (${OPT.papelera_mb} MB)</button>` : ''}
     </div>
     <div class="hp-sec">▸ Consejos para este equipo</div>
     <ul class="hp-keys">${OPT.sugerencias.map(s => `<li>${esc(s)}</li>`).join('')}</ul>
     <div id="opres"></div>`;
  box.querySelectorAll('[data-kill]').forEach(b => b.onclick = () => matarProceso(b.dataset.kill));
  box.querySelectorAll('[data-op]').forEach(b => b.onclick = () => limpiar(b.dataset.op));
  // Las cachés se miden en un hilo aparte del servidor: si aún van, se pregunta
  // otra vez sin esperar y sin congelar la ventana.
  clearTimeout(OPTtimer);
  if (OPT.midiendo) OPTtimer = setTimeout(() => refreshOptimize(false), 2500);
  voice.reanudar('optimizando');
}

async function limpiar(nivel) {
  const res = document.getElementById('opres');
  if (nivel === 'fresco') { OPT = null; return refreshOptimize(true); }
  if (res) res.innerHTML = '<div class="mo-none">barriendo caché…</div>';
  voice.suspender('barriendo');
  try {
    const r = await post('/api/optimize/clean', { nivel });
    const txt = r.ok ? `Barrí ${r.borrado.length} caché(s): ${r.mb_liberados} MB liberados` +
                       (r.ram_ganada_mb ? ` y ${r.ram_ganada_mb} MB de RAM devuelta` : '') + '.'
                     : `No pude limpiar: ${r.error}`;
    sayLine(txt); term(txt, 'optimizar');
    if (res) res.innerHTML = `<div class="mo-warn${r.ok ? ' ok' : ''}">${esc(txt)} ${esc(r.nota || '')}</div>`;
    OPT = null; setTimeout(() => refreshOptimize(true), 600);
  } catch { if (res) res.innerHTML = '<div class="mo-warn">el núcleo no respondió.</div>'; }
  voice.reanudar('barriendo');
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
  // En el teléfono las barras y la batería se miden AQUÍ, no en el portátil. Se
  // pintan antes de intentar la red para que un PC apagado no borre el panel.
  const aparato = IS_ANDROID ? leeAparato() : null;
  if (aparato) { pintaAparato(aparato); pintaSensores(leeSensores()); }
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
    // En Android esas barras ya traen SU CPU/RAM/disco; las del PC se quedan en la
    // línea de arriba (`s.system`), que es honesto: decir «RAM 40%» con la del
    // portátil mientras ella mira su teléfono es la mentira que empezó todo.
    if (m && !IS_ANDROID) {
      setBar('cpu', m[1]); setBar('ram', m[2]); setBar('disk', m[5]);
      document.getElementById('ramgb').textContent = `${m[3]} / ${m[4]} GB`;
    }
    if (!IS_ANDROID || !aparato) document.getElementById('batt').textContent = s.battery;
  } catch {
    if (aparato) {
      // Sin PC no hay «backend no detectado» que pintarrajeée el panel: el teléfono
      // ES el backend y ya se midió arriba.
      const red = aparato.red || '';
      el.innerHTML = `<span class="dot ${red ? 'on' : 'off'}"></span> CORT en tu teléfono<br>` +
        `<span style="color:#5e8cab">${esc(red ? 'red ' + red : 'sin red · el cerebro local sigue aquí dentro')}</span>`;
    } else {
      el.innerHTML = `<span class="dot off"></span> backend no detectado`;
    }
  }
}
function setBar(id, pct) { document.getElementById('bar-' + id).style.width = pct + '%'; }

/* ---------- el teléfono medido por sí mismo (Android, ronda 2.2) ---------- */
/* La queja era «hay sensores que no funcionan». Medido: el puente no tenía ni un
   método de sensores y estas barras sólo se llenaban con `/api/status` del
   portátil, así que en el móvil nacían en blanco. Ahora el teléfono se lee a sí
   mismo por `CortNative.aparato()` y `CortNative.sensores()`, y la regla es la
   misma que en Java: **lo que no se midió se pinta `—`, nunca un cero** — un `0`
   en luminancia se lee «a oscuras» y un `0%` de CPU se lee «tranquilo», y las dos
   cosas serían mentira. Con PC conectado, `#status` y `#envbrain` siguen contando
   el portátil (eso es el cerebro); estas barras cuentan el aparato. */
function leeAparato() {
  try { return IS_ANDROID ? JSON.parse(window.CortNative.aparato()) : null; } catch { return null; }
}
function leeSensores() {
  try { return IS_ANDROID ? JSON.parse(window.CortNative.sensores()) : null; } catch { return null; }
}
const gmb = v => (typeof v !== 'number' || v < 0) ? '—'
  : v >= 1024 ? (v / 1024).toFixed(1) + ' GB' : Math.round(v) + ' MB';
function pintaAparato(a) {
  if (!a || !a.ok) return;
  const txt = id => { const e = document.getElementById(id); return e; };
  setBar('cpu', a.cpu >= 0 ? a.cpu : 0);
  const ec = txt('envcpu'); if (ec) ec.textContent = a.cpu >= 0 ? a.cpu + '%' : '—';
  setBar('ram', a.ramPct >= 0 ? a.ramPct : 0);
  const rg = txt('ramgb'); if (rg) rg.textContent = `${gmb(a.ramLibreMB)} / ${gmb(a.ramTotalMB)}`;
  setBar('disk', a.discoPct >= 0 ? a.discoPct : 0);
  const ed = txt('envdisk'); if (ed) ed.textContent = a.discoPct >= 0 ? `${gmb(a.discoLibreMB)} libres` : '—';
  const bt = txt('batt');
  if (bt) bt.textContent = (a.bateria >= 0 ? `batería ${a.bateria}%` : 'batería sin leer')
    + (a.cargando ? ' · cargando' : '')
    + (a.battTemp >= 0 ? ` · ${(a.battTemp / 10).toFixed(1)} °C` : '')
    + (a.salud ? ` · ${a.salud}` : '')
    + (a.memoriaBaja ? ' · memoria justa' : '');
  const sc = txt('envscope');
  if (sc) sc.textContent = `en tu teléfono · ${a.modelo || ''} · Android ${a.android || ''}`
    + ` · red ${a.red || 'sin conexión'}`
    + (a.brillo >= 0 ? ` · brillo ${a.brillo}%` : '');
}
function pintaSensores(s) {
  const box = document.getElementById('sens'); if (!box) return;
  if (!s || !s.ok) { box.innerHTML = ''; return; }
  const fila = x => {
    if (!x.tiene) return '';
    const v = (x.valores || []).map(n => (typeof n === 'number'
      ? (Math.abs(n) >= 1000 ? n.toExponential(2) : n.toFixed(2)) : n)).join(' / ');
    const dicho = x.tieneLectura ? `${v} ${x.unidad} · hace ${x.hace}` : 'sin lectura todavía';
    return `<div class="sensrow"><span>${esc(x.tipo)}</span> <span style="color:#5e8cab">${esc(dicho)}</span></div>`;
  };
  box.innerHTML = (s.sensores || []).map(fila).join('')
    + `<div style="color:#5e8cab;margin-top:4px">${esc(s.dice || '')}</div>`;
}

/* ---------- clima ---------- */
let perfilCiudad = '';      // lo que dice la ventana PERFIL; '' = clima por IP
async function refreshWeather() {
  const el = document.getElementById('wx');
  const caja = document.getElementById('wx-ciudad');
  const lugar = (caja && caja.value.trim()) || perfilCiudad;
  try {
    const w = await (await fetch(API + '/api/weather?lugar=' + encodeURIComponent(lugar))).json();
    if (!w.ok) {
      // Dos fallos distintos y dos avisos distintos: «ese nombre no existe» no es
      // «no hay red», y decirlo importa cuando lo que se escribió fue la ciudad.
      el.innerHTML = w.error === 'sin-lugar'
        ? `<span style="color:#e0b060">no encuentro «${esc(w.busca || '')}»</span><br>` +
          `<span style="color:#5e8cab">prueba con otro nombre o pon tu ciudad en 07 · Perfil</span>`
        : '<span style="color:#5e8cab">clima no disponible (offline)</span>';
      return;
    }
    el.innerHTML = `<span class="big">${w.temp.toFixed(0)}°C</span> · ${esc(w.cielo)}<br>
       <span style="color:#5e8cab">${esc(w.lugar || '')} · viento ${(+w.viento || 0).toFixed(0)} km/h</span>` +
      (w.max != null && w.min != null
        ? `<br><span style="color:#5e8cab">hoy ${(+w.min).toFixed(0)}–${(+w.max).toFixed(0)}°` +
          (w.lluvia != null ? ` · ${(+w.lluvia).toFixed(0)}% lluvia` : '') + '</span>' : '');
  } catch { el.textContent = '…'; }
}

/* ---------- archivos ---------- */
let fGrid = false, curFPath = '';
async function openFiles(path = '') {
  /* Cambiar de carpeta cancela el plan viejo: confirmar movería archivos en una
     carpeta que la dueña ya no está mirando. Es de seguridad, no de limpieza. */
  if (planPendiente && path !== curFPath) {
    planPendiente = null;
    const caja = document.getElementById('fplan');
    if (caja) caja.innerHTML = '<div class="op-none">el plan anterior ya no vale: estás en otra carpeta; vuelve a pedir «ordena».</div>';
  }
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

/* ---------- EL ORGANIZADOR (01 · Archivos): primero el plan, luego el sí ----------
   `POST /api/organizar` sólo MIRA: devuelve la propuesta (`plan` con `de`/`a`/
   `motivo`) y un `token`. **No se mueve ni un archivo** hasta que la dueña confirme,
   y el `token` es lo que laCara lleva al aplicar — así el núcleo puede estar seguro
   de que confirma EL plan que vio, no otro. Si el backend dice `error`, se dice tal
   cual: un «no hice nada» sin motivo no es una respuesta para ella.            */
let planPendiente = null;              // { raiz, criterio, token } · lo que falta confirmar
const raizDe = path => String(path || '').split('/')[0];

function planAviso(texto, dicta, tag) {
  // El aviso del organizador vive en 01 · Archivos, que es donde se mira la
  // carpeta; lo de la actualización se cuenta por el canal de voz y el chat, no
  // dentro de la ventana de los archivos (si no, un «estás al día» quedaría
  // escrito donde mañana se pinta un plan).
  if (!tag || tag === 'archivos') {
    const caja = document.getElementById('fplan');
    if (caja) caja.innerHTML = `<div class="op-alerta">${esc(texto)}</div>`;
  }
  if (dicta) sayLine(texto); else add('a', texto, tag || 'archivos');
  term(texto, 'organizar');
}

async function ordenaArchivos(path, dicta) {
  const caja = document.getElementById('fplan');
  W.files.show();
  const raiz = raizDe(path);
  if (!raiz) return planAviso('Para ordenar hay que estar dentro de una carpeta: ábrela, o dime '
    + '«ordena mis documentos» y lo preparo ahí.', dicta);
  const criterio = 'tipo';               // el que entiende el núcleo hoy: por clase de archivo
  planPendiente = null;
  if (caja) caja.innerHTML = `<div class="op-none">pensando el orden de ${esc(raiz)}…</div>`;
  let r = null, porque = '';
  try { r = await post('/api/organizar', { raiz, criterio }); }
  catch { porque = fraseSinNucleo(); }   // sin núcleo: la misma frase que las pantallas
  if (porque) return planAviso(porque, dicta);
  if (!r || r.ok !== true) {
    // Sin `ok:true` no hay plan que confirmar: el 501 del teléfono sin PC trae sólo
    // `error` en español, y pintarlo como «no hay nada que mover» sería mentira.
    const sinPc = IS_ANDROID && /sin PC/i.test((r && r.error) || '');
    return planAviso(sinPc ? fraseSinNucleo()
      : 'No preparé el orden: ' + ((r && r.error) || 'el núcleo no respondió')
        + (r && r.reintenta ? ' · vuelve a pedirlo más tarde.' : '.'), dicta);
  }
  // El contrato llama `plan` a la lista de movimientos; se acepta también `entradas`
  // para que la cara no se quede en blanco si el núcleo tarda un latido en renombrar.
  const entradas = r.plan || r.entradas || [];
  planPendiente = { raiz, criterio, token: r.token };
  pintaPlan(entradas, r);
  const muestra = entradas.slice(0, 3).map(e => `${e.de} pasa a ${e.a}`).join('; ');
  const resumen = entradas.length
    ? `Tengo el plan: ${entradas.length} archivo(s) de ${raiz}${r.total && r.total !== entradas.length ? ` (de ${r.total} que hay)` : ''}, `
      + `ordenados por ${criterio}. Los primeros: ${muestra}. Nada se mueve hasta que me digas «confirmar».`
    : `En ${raiz} no hay nada que mover: ya está todo en su sitio.`;
  add('a', resumen, 'organizar');
  term('plan de orden: ' + entradas.length + ' movimientos en ' + raiz, 'organizar');
  if (dicta) speakTTS(resumen);
}

/* El plan se pinta en la propia ventana 01, debajo de la barra de herramientas: la
   dueña ve la carpeta que está ordenando y el plan a la vez, sin ventana nueva. */
function pintaPlan(entradas, r) {
  const caja = document.getElementById('fplan');
  if (!caja) return;
  const tope = 12;                        // 2.000 filas no caben en 1,8 GiB ni en la pantalla
  const filas = entradas.slice(0, tope).map(e => `<div class="pl-fila">
      <span class="pl-de">${esc(e.de)}</span><span class="pl-flecha">→</span>
      <span class="pl-a">${esc(e.a)}</span>${e.motivo ? `<small>${esc(e.motivo)}</small>` : ''}</div>`).join('');
  caja.innerHTML = `<div class="pl-top">orden propuesto · <b>${entradas.length}</b> archivo(s) en ${esc(r.raiz || '')}</b>`
    + (r.recorte ? ` · ${esc(String(r.recorte))}` : '') + '</div>'
    + (filas || '<div class="op-none">no hay movimientos que proponer</div>')
    + (entradas.length > tope ? `<div class="op-none">… y ${entradas.length - tope} más en la lista</div>` : '')
    + `<div class="pl-botones"><button class="mo-b d" id="fplan-ok">confirmar</button>`
    + `<button class="mo-b x" id="fplan-no">cancelar</button></div>`;
  caja.querySelector('#fplan-ok').onclick = () => aplicaPlan(false);
  caja.querySelector('#fplan-no').onclick = () => cancelaPlan(false);
}

async function aplicaPlan(dicta) {
  if (!planPendiente) {
    return planAviso('No hay ningún plan que confirmar: dime primero «ordena mis archivos».', dicta);
  }
  const { raiz, criterio, token } = planPendiente;
  const caja = document.getElementById('fplan');
  if (caja) caja.innerHTML = '<div class="op-none">moviendo lo confirmado…</div>';
  let r = null, porque = '';
  try { r = await post('/api/organizar/aplicar', { raiz, criterio, token }); }
  catch { porque = fraseSinNucleo(); }
  if (porque) return planAviso('No pude confirmar el orden: ' + porque, dicta);
  if (!r || r.ok !== true) {
    planPendiente = null;
    return planAviso('El núcleo no movió nada: ' + ((r && r.error) || 'no respondió'), dicta);
  }
  planPendiente = null;
  const errores = (r.errores || []);
  const dicho = `Movidos ${r.movidos ?? 0} archivo(s) de ${raiz}`
    + (errores.length ? ` · ${errores.length} lió: ${errores.slice(0, 2).join(' · ')}` : ' · sin errores');
  if (caja) caja.innerHTML = `<div class="op-alerta${errores.length ? '' : ' ok'}">${esc(dicho)}</div>`;
  add('a', dicho, 'organizar');
  term(dicho, 'organizar');
  if (dicta) speakTTS(dicho);
  openFiles(curFPath);                     // la lista real, no la que imaginábamos
}

function cancelaPlan(dicta) {
  if (!planPendiente) return planAviso('No había nada pendiente.', dicta);
  const caja = document.getElementById('fplan');
  const raiz = planPendiente.raiz;
  planPendiente = null;
  if (caja) caja.innerHTML = '<div class="op-none">plan cancelado: no moví nada.</div>';
  const dicho = 'Plan cancelado: ' + raiz + ' queda tal como está. No moví nada.';
  add('a', dicho, 'organizar');
  term('plan cancelado por la dueña', 'organizar');
  if (dicta) speakTTS(dicho);
}

/* ---------- AUTO-ACTUALIZACIÓN POR VOZ: mirar, contar y (si dice sí) reparar ----------
   `GET /api/update` es de lectura: compara la versión instalada con la Release.
   `POST /api/update/aplicar` es el que toca disco, y sólo se llama después de que
   ella conteste «sí». En el teléfono no se instala nada desde dentro (Android no lo
   deja): se le da el enlace y lo instala ella.                                  */
let ultimaUpdate = null;                 // la respuesta de /api/update, para elegir el asset
let repararPendiente = false;

const MB = b => Math.max(1, Math.round((b || 0) / 1024 / 1024));
const ASSETS_PC = ['.appimage', '.deb', '.exe'];

/* El instalador de SU equipo: Windows quiere .exe y el Linux de escritorio suele
   preferir el .AppImage (no necesita tocar permisos de empaquetado). */
function assetDeEscritorio(enlaces) {
  const lista = enlaces || [];
  const win = /windows|win32/i.test(navigator.userAgent || '');
  const orden = win ? ['.exe', '.appimage', '.deb'] : ['.appimage', '.deb', '.exe'];
  for (const suf of orden) {
    const d = lista.find(a => String(a.nombre || a.url || '').toLowerCase().endsWith(suf));
    if (d) return d;
  }
  return lista[0] || null;
}

async function revisaActualizacion(dicta) {
  let u = null, porque = '';
  try { u = await getJSON('/api/update'); }
  catch { porque = fraseSinNucleo(); }
  if (porque) return planAviso(porque, dicta, 'actualizar');
  // Un 501 del APK sin PC trae `error` en español y **ningún** `ok`: si aquí se
  // leyera `u.ok === false` a secas, CORT contestaría «ya tienes el CORT undefined»
  // con datos inventados. Se comprueba que la respuesta sea de verdad un informe.
  if (!u || u.ok !== true || !u.instalada) {
    const sinPc = IS_ANDROID && /sin PC/i.test((u && u.error) || '');
    return planAviso(sinPc ? fraseSinNucleo()
      : 'No pude mirar en GitHub: ' + ((u && u.error) || 'el núcleo no respondió'), dicta, 'actualizar');
  }
  ultimaUpdate = u;
  repararPendiente = false;
  const enlaces = u.enlaces || [];
  const peso = enlaces.reduce((s, a) => s + (a.bytes || 0), 0);
  if (!u.hay_actualizacion) {
    add('a', `Ya tienes el CORT ${u.instalada}, que es el último que hay (publicado ${u.publicada || '—'}). No hay nada que reparar.`, 'actualizar');
    return planAviso(`Estás al día: ${u.instalada}. No hay nada que reparar.`, dicta, 'actualizar');
  }
  const dicho = `Hay un CORT nuevo: la ${u.ultima}, y tú tienes la ${u.instalada}. `
    + `La Release trae ${enlaces.length} archivo(s) que pesan ${MB(peso)} MB en total. ¿lo reparo?`;
  add('a', dicho, 'actualizar');
  if (u.notas) add('a', 'Lo que trae: ' + u.notas.slice(0, 260), 'actualizar');
  term('hay actualización: ' + u.instalada + ' → ' + u.ultima, 'actualizar');
  repararPendiente = true;
  if (dicta) speakTTS(dicho);
}

async function reparaActualizacion() {
  repararPendiente = false;
  const elegido = assetDeEscritorio(ultimaUpdate && ultimaUpdate.enlaces);
  const asset = elegido ? (elegido.nombre || '') : '';
  add('a', 'Vale: pidiendo la reparación a tu núcleo' + (asset ? ' («' + asset + '»)' : '') + '…', 'actualizar');
  let r = null, porque = '';
  try { r = await post('/api/update/aplicar', { asset }); }
  catch { porque = fraseSinNucleo(); }
  if (porque) return add('a', 'No arranqué la reparación: ' + porque, 'actualizar');
  if (r && r.apk) {
    add('a', 'Ese archivo es el APK del teléfono: Android no deja que una app se reemplace a sí misma '
      + 'desde dentro. Instálalo tú desde este enlace' + (r.url ? ': ' + r.url : '') +
      '. ' + (r.aviso || ''), 'actualizar');
    speakTTS('Ese es el APK del teléfono: lo instalas tú desde el enlace que te acabo de poner.');
    return;
  }
  if (!r || r.ok !== true) {
    // Mismo criterio que al mirar: sin `ok:true` no hubo reparación, por mucho que
    // el 501 del teléfono no escriba `false` explícito. Decir «listo» con un error
    // por delante sería mentirle a la dueña justo con sus archivos.
    add('a', 'No pude repararlo: ' + ((r && r.error) || 'el núcleo no dio motivo') +
      (r && r.url ? ' · el archivo está en ' + r.url : ''), 'actualizar');
    speakTTS('No pude repararlo: ' + ((r && r.error) || 'el núcleo no dio motivo'));
    return;
  }
  const pasos = r && r.pasos ? r.pasos : 'bash scripts/actualiza.sh';
  const dicho = r && r.descargado
    ? 'Descargado ' + r.descargado + '. Para terminar: ' + pasos +
      (r.hecho === false ? ' (el script aún no está en el disco)' : '')
    : (r && r.pendiente
        ? 'El instalador pesa más de 100 MB, así que tu núcleo no lo baja dentro de una petición: '
          + 'lanza ' + pasos + ' cuando no estés usando el equipo.'
        : 'Listo lo que pude hacer desde aquí. Los pasos: ' + pasos);
  add('a', dicho, 'actualizar');
  term('reparación pedida: ' + dicho.slice(0, 60), 'actualizar');
  speakTTS(dicho);
}

/* ---------- SEGUNDO PLANO: que CORT siga vivo al irte de la app ---------- */
/* Las cuatro filas son las que de verdad hacen falta para que el aviso de fondo
   exista y Android no lo apague, y cada una se mide en Java (`bgStatus()`) con su
   permiso o su interruptor real: micrófono concedido, avisos de Android (13+),
   «aparecer encima de otras apps» para la burbuja, y la excepción de batería. El
   botón «Dar» de cada fila no promete nada: `perms.ask(kind)` cae en Java, que
   abre el cuadro o la pantalla de Ajustes que toque. */
const BG_PERMS = [
  ['mic', 'Micrófono', 'para oírte cuando abres la cara o la burbuja'],
  ['notif', 'Avisos de Android', 'sin ellos no se puede poner el aviso fijo (Android 13+)'],
  ['overlay', 'Burbuja flotante', 'el punto de CORT para llamarme sin abrir la app'],
  ['battery', 'Batería sin restricción', 'que Android no congele el aviso ni la música'],
];
function bgStatus() {
  try { return IS_ANDROID ? JSON.parse(window.CortNative.bgStatus()) : null; } catch { return null; }
}
function renderBg(st = bgStatus()) {
  const box = document.getElementById('bgbox'); if (!box) return;
  if (!st) { box.innerHTML = '<div class="bg-help">Solo disponible en la app de Android.</div>'; return; }
  const t = document.getElementById('bgtoggle');
  // `enabled` es lo que la dueña pidió; `running` es la prueba de que está pasando
  // (el aviso puesto ahora mismo). Las dos claves nuevas vienen de `bgStatus()`.
  t.classList.toggle('on', !!st.enabled);
  t.querySelector('b').textContent = st.enabled
    ? (st.running ? 'Segundo plano ACTIVO (aviso puesto)'
                  : 'Segundo plano pedido: activa CORT y lo verás en la barra')
    : 'Que CORT se quede en segundo plano';
  const rows = BG_PERMS.map(([k, name, why]) => `<div class="bgp ${st[k] ? 'ok' : ''}">
      <span class="st">${st[k] ? '✓' : '·'}</span><span class="nm">${name}<small>${why}</small></span>
      ${st[k] ? '' : `<button data-perm="${k}">Dar</button>`}</div>`).join('');
  const oem = /oppo|realme|oneplus|xiaomi|redmi|poco|huawei|honor|vivo|samsung|tecno|infinix/i.test(st.maker || '');
  document.getElementById('bgperms').innerHTML = rows + (oem ? `<div class="bgp warn"><span class="st">!</span>
      <span class="nm">${esc(st.maker)}: activa «Inicio automático» / «Actividad en segundo plano»<small>en los ajustes de la app, si no tu teléfono lo cierra</small></span>
      <button data-perm="autostart">Abrir</button></div>` : '');
  document.querySelectorAll('#bgperms [data-perm]').forEach(b => b.onclick = () => perms.ask(b.dataset.perm));
  if (st.dice) { const ayuda = box.querySelector('.bg-help'); if (ayuda) ayuda.innerHTML = esc(st.dice); }
}
async function toggleBg() {
  const st = bgStatus(); if (!st) return;
  const on = !st.enabled;
  window.CortNative.setBackground(on);
  term(on ? 'segundo plano: pedido' : 'segundo plano: apagado', 'voz');
  if (on) {
    voice.setWake(true);                                   // en pantalla también escucha «Oye CORT»
    add('a', 'Listo: al salir de la app queda mi aviso, y con él la música y el doble toque '
      + 'del auricular. El micrófono se cierra para no trabarte. Da los permisos de la lista '
      + 'para que Android no me congele.', 'voz');
    speakTTS('Me quedo en segundo plano.');
  } else {
    add('a', 'CORT se guarda al salir de la app: sin aviso y sin doble toque en segundo plano.', 'voz');
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
  if (!window.CORTcapaz('avisos')) {
    // Perfil `nucleo` (ronda 2.5): `.Avisos` no está declarado en el manifiesto, así
    // que el sistema no puede listar a CORT en «acceso a notificaciones» y el
    // botón prometería algo que este archivo no hace. Se dice el porqué y qué APK
    // lo trae, en vez de responder «no tengo avisos» como si estuviera vacío.
    const r = 'Esta versión de CORT —la que se instala sin el aviso de Google— viene sin el permiso de leer notificaciones: es el precio de que el instalador te deje pasar. La hoja Equipo ▸ 9 lo explica, y el APK completo lo vuelve a traer cuando el teléfono ya acepte la app.';
    add('a', r, 'avisos'); speakTTS('Esa puerta va cerrada en este envase.'); return;
  }
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

/* ── que CORT sea EL ASISTENTE del teléfono ────────────────────────────────
   En Android el asistente predeterminado es un **rol** (`RoleManager.ROLE_ASSISTANT`,
   API 29+). Lo pide Java —`MainActivity.abreAjustesDeAsistente()`— porque una página
   no puede pedir roles: sólo puede abrir el cuadro que Android muestra. Con CORT
   elegido, el gesto del asistente, la pantalla bloqueada y el **doble toque del
   auricular** abren CORT en vez de Google. El coste, dicho sin adornos: el «OK
   Google» con la pantalla apagada se pierde, porque esa palabra la decide el
   servidor de Google y no viaja con este APK.
   `assistantState()` sólo existe en el puente de este repo: en el cuerpo Kotlin
   original (el APK del teléfono sin función de asistente) la cara se degrada a
   las palabras, sin llamar a nada.                                          */
function ponAsistente() {
  const N = window.CortNative;
  if (!window.CORTcapaz('asistente')) {
    // Con el perfil `nucleo` el `VoiceInteractionService` no está declarado, y el
    // cuadro de Android de «aplicación de asistencia» no va a listar a CORT aunque
    // lo busque diez minutos. Abrir el cuadro sería una falsa promesa.
    sayLine('Este envase de CORT viene sin el traje de asistente: es lo que le quité para que Google te dejara instalarlo. Aun así me abres desde el icono, desde el widget y diciendo mi nombre con el micrófono en pantalla.');
    return;
  }
  if (!N || typeof N.openAssistantSettings !== 'function') {
    // El puente `openAssistantSettings` sólo existe en el APK de Java de este
    // repo (`apps/apk/compilar.sh`). Si la cara está corriendo dentro del cuerpo
    // Kotlin viejo —el `CORT-IA-1.1.x` que ya no se publica— no declara
    // `VoiceInteractionService` y Ajustes no va a listar a CORT aunque lo intente
    // mil veces. No le digo que busque en el menú: le digo qué instalar.
    const r = 'Ponerme como asistente lo trae el APK que se compila aquí: CORT-IA-1.3.0.apk, el único que sale ahora de la Release. Con el cuerpo Kotlin viejo no aparezco en esa lista porque no lleva puesto el traje de asistente de Android.';
    sayLine(r);
    return;
  }
  let st = null;
  try { st = JSON.parse(typeof N.assistantState === 'function' ? N.assistantState() : 'null'); }
  catch { st = null; }
  if (st && st.esAsistente) {
    sayLine('Ya soy tu asistente: dos toques en el auricular o el gesto del asistente me abren.');
    return;
  }
  N.openAssistantSettings();
  if (st && st.rol === false) {
    add('a', 'Tu Android es anterior al 10 y no trae el rol de asistente: elígeme a mano en Ajustes ▸ Aplicaciones ▸ Aplicación de asistencia predeterminada.', 'sistema');
    return;
  }
  add('a', 'Ahí sale el cuadro de Android: pulsa «Establecer asistente». Con eso el doble toque del auricular y el gesto del asistente pasan a ser míos.', 'sistema');
  term('rol de asistente solicitado' + (st && st.puede === false ? ' (no disponible en este fabricante)' : ''), 'sistema');
}
/* «llama a Samuel» / «llama al 611 22 33». Sólo en el teléfono, y sólo si el
   puente lo soporta: `Telefono.java` busca en los contactos y abre la llamada.
   Con el permiso `CALL_PHONE` concedido va directo; sin él abre el marcador con
   el número escrito para que la dueña pulse el verde — es lo que Android deja sin
   asustarla. Contestar por ella **no** está: eso exige el rol `ROLE_CALLING` con
   su `InCallService`, y mientras CORT no tenga pantalla de llamadas hecha se
   dice aquí en vez de fingirlo (el README lo cuenta igual). */
function llamarA(quien) {
  const N = window.CortNative;
  if (!N || typeof N.llamar !== 'function') {
    sayLine('Marcar lo trae el APK de Java: en esta cara no tengo acceso al teléfono.');
    return;
  }
  /* El perfil `nucleo` (ronda 2.5) no declara `READ_CONTACTS` ni `CALL_PHONE`.
     `Telefono.buscar` ya se degrada solo —sin permiso devuelve lista vacía— y
     ACTION_DIAL no necesita ninguno, así que **un número sí se puede marcar**:
     lo que no hay es búsqueda por nombre. Pedir el permiso con
     `pidePermisoTelefono()` en este envase sería peor que inútil: Android no
     muestra el cuadro de un permiso que no está en el manifiesto, y la cara
     quedaría diciendo «te estoy pidiendo el permiso» sin haberlo pedido nunca. */
  const hayDigitos = /\d[\d\s+.-]{2,}/.test(quien || '');
  if (!window.CORTcapaz('llamadas') && !hayDigitos) {
    sayLine('Este envase de CORT no lee tus contactos: dime el número y te lo pongo en el marcador para que pulses verde.');
    term('llamada por nombre sin permiso en el perfil nucleo', 'teléfono');
    return;
  }
  let r = null;
  try { r = JSON.parse(N.llamar(quien)); } catch { r = null; }
  if (!r) { sayLine('El teléfono no me dejó marcar. Prueba otra vez o dime el número.'); return; }
  if (!r.ok) {
    // casi siempre es que faltan los contactos: se pide el permiso y nada más
    const puede = window.CORTcapaz('llamadas');
    if (puede && typeof N.pidePermisoTelefono === 'function') N.pidePermisoTelefono();
    add('a', puede
      ? `No encontré a «${quien}» en tus contactos —te estoy pidiendo el permiso de contactos y de llamar; vuelve a decírmelo.`
      : `No encuentro a «${quien}»: este envase no lleva el permiso de contactos. Díme el número y lo dejo en el marcador.`, 'teléfono');
    sayLine(puede ? 'No lo tengo en los contactos. Dame un momento y pídeme la llamada otra vez.'
                  : 'Dime el número, por favor.');
    term('llamar sin datos de contacto' + (puede ? ': permiso pedido' : ' (perfil nucleo)'), 'teléfono');
    return;
  }
  orb.burst();
  const nombre = r.nombre || quien;
  add('a', r.directo
    ? `Llamando a ${nombre} (${r.numero}).`
    : `Aquí está el número de ${nombre}: ${r.numero}. Pulsa verde para llamar.`, 'teléfono');
  sayLine(r.directo ? 'Llamando a ' + nombre : 'Te puse a ' + nombre + ' en el marcador.');
  term('marcar ' + nombre + ' ' + r.numero + (r.directo ? ' (directo)' : ' (marcador)'), 'teléfono');
}
/* ── el auricular abierto, a la vista ───────────────────────────────────────
   `Reconocimiento.java`/`MainActivity.java` empujan `{type:'auricular',
   escuchando:true}` cuando el micro del auricular se abre sin que la dueña esté
   mirando la app (el doble toque, «Oye CORT» de fondo, la respuesta a un aviso).
   Sin una señal en la cara eso se siente como una escucha escondida: se pone un
   badge abajo a la izquierda y el micrófono brilla, y se quita al terminar. En el
   PC este evento no llega nunca —no hay puente—, así que el badge no se crea. */
function pintaAuricular(escuchando, nota) {
  const raiz = document.documentElement;
  raiz.classList.toggle('auricular-abierto', !!escuchando);
  let badge = document.getElementById('auricular');
  if (!badge) {
    badge = document.createElement('div');
    badge.id = 'auricular';
    badge.innerHTML = '<i>🎧</i><span></span>';
    document.body.appendChild(badge);
  }
  badge.querySelector('span').textContent = nota
    || (escuchando ? 'escuchando por el auricular' : 'auricular cerrado');
  badge.hidden = !escuchando;
  const wake = document.getElementById('wake');
  if (wake) wake.classList.toggle('auricular', !!escuchando);
}

/* ---------- consola de comandos: historial ↑/↓ y Tab que completa ---------- */
const HIST = [];
let hIdx = 0, draft = '';
const CMDS = ['reproduce', 'pausa', 'reanuda', 'modo oficina', 'oculta todo', 'muestra todo',
  'muéstrame las notas', 'archivos recientes', 'recoge los chips', '¿qué hora es?',
  'abre youtube', 'abre el navegador', 'apunta ', 'muéstrame tu cerebro', 'qué recuerdas',
  'muéstrame los modelos', 'descarga el modelo ', 'usa el modelo ', 'enciende ollama',
  '¿cuánta ram queda?', 'abre la optimización', 'limpia la caché',
  'lee mis avisos', 'lee mis notas', 'lee mis tareas', 'tengo que ', 'lee el documento ',
  'pon CORT como asistente', 'llama a ', 'ponme algo que me guste',
  'abre el chat', 'abre la pantalla de código', 'abre la pantalla de música', 'vuelve al orbe',
  'abre el mv', 'el video con la letra',
  'ordena mis archivos', 'ordena mis documentos', 'ordena la música',
  'confirmar', 'cancelar', 'modo juego', 'vuelve CORT',
  'revisa si hay actualizaciones', 'actualízate',
  /* las órdenes del contrato 2.1: sólo tienen eco en el teléfono, y la pantalla
     Equipo las enseña con su nombre. Se listan aquí para que el Tab y la ayuda
     digan lo mismo en las dos caras. */
  'abre el equipo', 'sube el volumen', 'baja el volumen', 'linterna',
  'pon una alarma a las 7:30', 'temporizador de 10 minutos', 'abre whatsapp',
  'busca ', 'qué sabes de mí', 'acuédate de ', 'voz de siri', 'cambia la voz',
  'ponte azul', 'atuendo ', 'burbuja', 'piensa ', 'sincroniza con el pc',
  '¿qué tengo hoy?', 'mi agenda', 'las citas de la semana', 'revisa el correo',
  'apunta una cita con Samuel a las 9', 'enciende la linterna',
  /* ronda 2.4 · los cerebros de casa. Se escriben igual con el portátil delante o
     desde la terminal de la pantalla Código en el teléfono (`terminalTelefono`), así
     que el Tab los ofrece en las dos caras. */
  'busca cerebros', 'modelos', 'muéstrame los modelos del teléfono',
  'usa el modelo qwen2.5:1.5b', 'descarga el modelo qwen2.5:0.5b', 'borra el modelo llama3',
  /* las automatizaciones (ronda 2.4): las mismas palabras en el Tab y en la hoja
     8 · Automatiza del teléfono; `automatiza.js` es quien las cumple. */
  'mis automatizaciones', 'automatiza cuando diga modo noche haz callar la música',
  'ayuda', 'olvida la terminal'];
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
  /* ─── cambiar de pantalla: el orbe, la charla, el código y la música ───
     Se atiende antes que nada: es una orden de interfaz, no necesita núcleo
     ni modelo, y si la dejo para después se la roba el backend. */
  const pantalla = porVoz(msg);
  if (pantalla) {
    setState('listo');
    const titulo = { orbe: 'el orbe', musica: 'la pantalla de música', mv: 'la pantalla del vídeo con la letra',
                     charla: 'la pantalla de charla', codigo: 'la pantalla de código',
                     equipo: 'la pantalla del Equipo, con lo que CORT manda en el teléfono' }[pantalla];
    add('a', `Cambié a ${titulo}. Con ☰ o deslizando el dedo de lado a lado te mueves entre ellas.`, 'pantallas');
    speakTTS('Aquí tienes ' + titulo + '.'); term('pantalla: ' + pantalla, 'pantallas');
    if (pantalla !== 'orbe') orb.burst();
    return;
  }
  /* ─── el organizador por voz: primero el plan, luego «confirmar» ───
     «ordena mis archivos / mis documentos / la música» se dice desde cualquier
     pantalla. Va ANTES del modo oficina porque ése se llevaba por las narices
     cualquier frase con «organiza»: aquí lo que se organiza son archivos, no
     ventanas. Sin carpeta a la vista se elige la raíz que nombran las palabras. */
  if (/^(ordena|organiza)\b/i.test(msg) && !/ventana|escritorio|bureau/i.test(msg)) {
    setState('listo');
    const raiz = /documentos/i.test(msg) ? 'Documentos'
      : /m[uú]sica/i.test(msg) ? 'Música'
      : /descargas/i.test(msg) ? 'Descargas'
      : (curFPath || 'Documentos');
    ordenaArchivos(raiz, true); return;
  }
  if (/^(confirmar|confirmalo|confirmo)\b/i.test(msg)) {
    setState('listo'); aplicaPlan(true); return;
  }
  if (/^cancelar\b/i.test(msg) && planPendiente) {
    setState('listo'); cancelaPlan(true); return;
  }
  /* ─── modo juego: la cara sólo lo PIDE; el silencio lo guarda Java ─── */
  if (/(modo juego|me voy a jugar|voy a jugar|silencio[, ]+cort)/i.test(msg)
      && !/sal |quita |vuelve /i.test(msg)) {
    setState('listo'); const dicho = modoJuego(true);
    add('a', dicho, 'juego'); speakTTS(dicho); return;
  }
  if (/(vuelve[, ]+cort|sal (del|de) modo juego|quita (el )?modo juego|despierta[, ]+cort)/i.test(msg)) {
    setState('listo'); const dicho = modoJuego(false);
    add('a', dicho, 'juego'); speakTTS(dicho); return;
  }
  /* ─── auto-actualización: mirar, contar y esperar un «sí» ───
     Aquí la cara no descarga nada por su cuenta: `GET /api/update` sólo informa
     y `POST /api/update/aplicar` se llama después de que ella conteste. */
  if (/(revisa si hay actualizaciones|hay versi[oó]n nueva|actual[ií]zate|nueva versi[oó]n|revisa (que hay |si hay )?actualizaci)/i.test(msg)) {
    setState('listo'); revisaActualizacion(true); return;
  }
  if (repararPendiente && /^(s[ií]|dale|vale|ok|adelante|repara)\b/i.test(msg)) {
    setState('listo'); reparaActualizacion(); return;
  }
  /* «llama a Samuel» / «marca al 611 22 33» — el teléfono, no el PC */
  const llamada = msg.match(/^(?:llama(?:r)?|marca(?:r)?|llámame|marcarme)\s+(?:a\s+|con\s+|al\s+)?(.{2,40})$/i);
  if (llamada && IS_ANDROID && !/(?:wi-?fi|pantalla|ventana|luz|puerta|asistente)/i.test(llamada[1])) {
    setState('listo');
    llamarA(llamada[1].replace(/^(?:el contacto de |mi amigo |mi amiga )/i, '').trim());
    return;
  }
  /* ─── órdenes del aparato: las atiende la cara del Equipo (contrato 2.1) ───
     «sube el volumen», «linterna», «pon una alarma a las 7:30», «abre whatsapp»,
     «busca recetas con pollo», «qué sabes de mí», «acuédate de…», «voz de siri»,
     «ponte azul», «burbuja», «piensa…», «sincroniza con el pc». Van AQUÍ, después
     del modo juego y de «llama a…», y sólo si hay puente: `telefonoPorVoz()`
     pregunta método por método (`puede('accion')`…) y devuelve `false` en el PC,
     así que ninguna de estas frases le roba el backend a nadie. Lo que el APK no
     trae se contesta con la frase honesta del módulo, no con un botón mudo. */
  if (IS_ANDROID && telefonoPorVoz(msg)) { setState('listo'); return; }
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
  /* «pon CORT como asistente» / «sé el asistente predeterminado» */
  if (/(?:pon|poner|ponme|colocate|convert|ser|activa|quiero|puedes|reemplaz)\w{0,3}[^.]{0,24}asistente/i.test(msg)
      || /asistente (?:predeterminad\w*|por defecto|de google)/i.test(msg)
      || /reemplaz\w* (?:a )?(?:google|el asistente)/i.test(msg)) {
    setState('listo'); ponAsistente(); return;
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
  /* reproductor de CORT en el teléfono: MANDA si está vivo, antes que el ejecutor
     del PC. `musicaEstado()` es el mismo JSON que pinta la pantalla Música. */
  if (IS_ANDROID && typeof (window.CortNative || {}).musicaEstado === 'function') {
    let e = null;
    try { e = JSON.parse(window.CortNative.musicaEstado()); } catch { e = null; }
    if (e && e.vivo) {
      if (/^(pausa|para|det[eé]n|stop)\b/i.test(msg) && /m[uú]sica|audio|sonido|eso/i.test(msg) || /^pausa$/i.test(msg)) {
        window.CortNative.musicaPausa();
        add('a', `Pauso «${e.pista ? e.pista.titulo : 'la canción'}». Di «sigue».`, 'música');
        speakTTS('Pausa'); return;
      }
      if (/^(sigue|contin[uú]a|reanuda|play)\b/i.test(msg)) {
        window.CortNative.musicaPlay();
        add('a', 'Sigo con la música.', 'música'); speakTTS('Continuando'); return;
      }
      if (/siguiente|qu[eé] sigue|otra canci[oó]n|pon otra/i.test(msg)) {
        window.CortNative.musicaSiguiente();
        add('a', 'Pasando a la siguiente.', 'música'); speakTTS('La siguiente'); return;
      }
      if (/anterior|la de antes/i.test(msg)) {
        window.CortNative.musicaAnterior();
        add('a', 'Voy a la anterior.', 'música'); return;
      }
      if (/cuadro|fotograma|frame/i.test(msg)) {
        window.CortNative.musicaCuadro(/atr[aá]s|antes|retro/i.test(msg));
        add('a', 'Un fotograma ' + (/atr[aá]s|antes|retro/i.test(msg) ? 'atrás' : 'adelante') + '.', 'música');
        return;
      }
      if (/parar la m[uú]sica|cierra el reproductor|silencio/i.test(msg)) {
        window.CortNative.musicaParar();
        add('a', 'Reproductor parado. La pantalla Música sigue ahí con ☰.', 'música');
        speakTTS('Listo, sin música'); return;
      }
    }
    if (/que me guste|m[uú]sica que me gusta|ponme algo|pon m[uú]sica|reproduce m[uú]sica/i.test(msg)) {
      window.CortNative.musicaAutomatica();
      ir('musica');
      add('a', 'Poniendo lo que va con tus gustos: suena aunque cierres la cara. En la pantalla Música está el control y sus 👍/👎.', 'música');
      speakTTS('Poniendo música de tu estilo'); orb.burst(); return;
    }
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
      // Si el oído está en pausa (música, optimizando, segundo plano) se ve y se
      // lee: sin esto parece que CORT «no funciona», cuando es que no le toca.
      wake.title = st.freno ? 'Oído en pausa: ' + st.freno
                            : (st.wakeOn ? 'escuchando «Oye CORT»' : '«Oye CORT» apagado');
      wake.style.opacity = (st.wakeOn && st.freno) ? '.45' : '';
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
  /* La ciudad del tiempo se puede cambiar sin abrir el Perfil, y se escribe en la
     preferencia para que «el clima» por voz la respete en el próximo arranque.
     Un Enter vacío vuelve a la IP, que es lo de siempre. */
  const wxc = document.getElementById('wx-ciudad');
  const poneCiudad = () => {
    perfilCiudad = wxc.value.trim();
    // Se guarda en el Perfil (clave libre: la lee `brain._perfil_clave('ciudad')`).
    // Si el núcleo no está, el fetch falla en silencio y la caja sigue sirviendo.
    try { post('/api/profile', { clave: 'ciudad', valor: perfilCiudad }).catch(() => {}); } catch { /* sin backend */ }
    refreshWeather();
  };
  wxc.addEventListener('keydown', e => { if (e.key === 'Enter') poneCiudad(); });
  wxc.addEventListener('change', poneCiudad);
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

  /* Mientras suena música, el oído permanente NO se rearma. En Android abrir el
     micrófono baja el volumen de la canción y, en un teléfono medio, lo traba:
     por eso CORT guarda el oído mientras ella escucha. */
  {
    const altavoz = document.getElementById('aud');
    altavoz.addEventListener('play', () => voice.suspender('música'));
    altavoz.addEventListener('pause', () => voice.reanudar('música'));
    altavoz.addEventListener('ended', () => voice.reanudar('música'));
  }
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
  // ⤢ ordena prepara el plan de la carpeta que se está viendo; NO mueve nada.
  document.getElementById('fordena').onclick = () => ordenaArchivos(curFPath, false);

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

  /* ── los avisos del contrato 2.1, juntos junto a los de siempre ─────────────
     Java empuja `{type:'auricular'}` (el micro del auricular abierto), y `{type:
     'mente'|'memoria'|'accion'}` cuando termina lo largo: pensar en la nube,
     cuadrar los recuerdos con el portátil o hacer una cosa por su cuenta. Un solo
     `on()` para las tres familias: el badge es de aquí (mandan las ventanas y el
     oído), y la hoja del Equipo se pinta sola con `handleTelefonoEvento()`. Si el
     evento llega con la pantalla cerrada no se pierde —`telefono.js` lo guarda. */
  window.__cortNative.on(ev => {
    if (!ev || typeof ev.type !== 'string') return;
    if (ev.type === 'auricular') { pintaAuricular(!!ev.escuchando, ev.dice || ev.nota); return; }
    handleTelefonoEvento(ev);
  });

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

  /* pantallas: el orbe, la música, la charla y el código. Son hojas a pantalla
     completa que se encienden con ☰, con las flechas ‹ ›, deslizando el dedo de
     lado, con Alt+←/→ o por voz («abre la pantalla de código»). Cuando una de
     ellas está encendida, el orbe y el HUD se apagan por CSS: ninguna ventana
     nueva tapa ni estorba la cara de CORT, y al revés. */
  initPantallas({
    orb, term, say: sayLine,
    api: () => API,                              // el núcleo localizado por discoverApi()
  });
  /* Qué familia del puente 2.1 trae este APK, dicho una vez y en la consola: si
     mañana la dueña pregunta «¿por qué la linterna no está?», ahí está la respuesta
     sin abrir el teléfono en modo depuración. `estadoTelefono()` es sólo una foto
     del estado del módulo: no llama a Java. */
  if (IS_ANDROID) {
    const eq = estadoTelefono();
    const traidos = Object.entries(eq.puente).filter(([, v]) => v).map(([k]) => k);
    term('puente 2.1: ' + (traidos.length ? traidos.join(' · ') : 'sin métodos nuevos (APK viejo)'), 'equipo');
  }
  // Fuera de su pantalla, el orbe no se queda dibujando a escondidas: el bucle
  // WebGL se congela (CPU, RAM y batería para el teléfono y para el portátil).
  // La excepción es MV: ahí el holograma no se apaga, se hace disco en la esquina
  // (el CSS pone #scene pequeñito sobre el vídeo) y gira mientras suena la pista.
  window.addEventListener('cort-pantalla', e => {
    if (e.detail === 'mv') { orb.pausa(false); orb.setDisc(true); }
    else { orb.setDisc(false); orb.pausa(e.detail !== 'orbe'); }
  });
  // Las pantallas piden ventanas que viven aquí: el botón «↓ bajar modelos» de la
  // Charla abre 10 · Modelos, que es donde está el descargador de verdad — no se
  // duplica en `pantallas.js`, se manda el aviso y se abre la que ya existe.
  window.addEventListener('cort-ventana', e => {
    if (e.detail === 'modelos' && W.modelos) W.modelos.show();
  });

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
    // El error de cámara llega TRADUCIDO desde `gestures.js` (ronda 2.2). Se cuenta
    // en el canal, se deja la razón en la etiqueta y —si es el permiso— se pone la
    // fila con su botón aquí mismo, en el panel de gestos. `permRow` guarda además
    // el reintento en `permRetry.camera`, así que cuando Android avise por
    // `type:"perm"` la cámara se reabre sola sin que ella vuelva a buscar el botón.
    onError: p => {
      add('a', 'Gestos: ' + p.largo + (p.clase === 'camera'
        ? ' Toca «Dar acceso a la cámara» aquí abajo y la mano vuelve a intentarlo sola.' : ''), 'error');
      term('cámara de gestos: ' + p.corto, 'gestos');
      const panel = document.getElementById('camwrap');
      if (!panel) return;
      const vieja = panel.querySelector('.perm');
      if (vieja) vieja.remove();
      if (p.clase !== 'camera') return;
      panel.appendChild(permRow('camera', 'Sin cámara: dame el permiso',
        () => document.getElementById('hand').click()));
    },
  }));
}
