/* ===== Gestos de mano — MODO LIGERO =====
   MediaPipe Hands con 1 sola mano, cámara 160×120 y análisis cada ~250 ms.
   La cámara NO se enciende hasta pulsar el botón de mano (privacidad y RAM).

   Ronda 2.2: antes se lanzaba `getUserMedia()` a pelo. En el navegador eso abre
   el cuadro de permiso del propio navegador; **en el WebView de Android no**:
   ahí hay que tener concedido `CAMERA` por el sistema, y sin eso el `getUserMedia`
   falla con `NotAllowedError`. Como el `catch` escribía sólo «sin cámara» y se
   callaba el motivo, la dueña veía un fallo sin explicación y sin botón para
   arreglarlo — la misma familia de bug que `notif`, `burbuja` y `files`: la cara
   preguntaba una cosa y Java esperaba otra. Ahora se pide el permiso al puente
   ANTES de encender nada (ni el CDN de MediaPipe, que baja el modelo a costa de
   sus datos), y el error se traduce a español con su causa. */

import { perms } from './voice.js';

const MP_URL = 'https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/hands.min.js';

const espera = ms => new Promise(r => setTimeout(r, ms));
const puenteVivo = () => !!window.CortNative;

/** El motivo real del fallo, en español: corto para la etiqueta, largo para el chat. */
function porqueFallo(e) {
  const clave = String((e && (e.name || e.message)) || '');
  if (/NotAllowedError|Permission denied|denied/i.test(clave)) {
    return { corto: 'permiso denegado', clase: 'camera',
      largo: 'Android no me dejó abrir la cámara: falta el permiso de cámara.' };
  }
  if (/NotFoundError|DevicesNotFound/i.test(clave)) {
    return { corto: 'sin cámara', clase: '',
      largo: 'Este teléfono no tiene una cámara que CORT pueda usar para gestos.' };
  }
  if (/NotReadableError|TrackStartError|in use/i.test(clave)) {
    return { corto: 'cámara ocupada', clase: '',
      largo: 'Otra app tiene la cámara abierta. Ciérra y vuelve a pulsar la mano.' };
  }
  if (/SecurityError/i.test(clave)) {
    return { corto: 'cámara bloqueada', clase: '',
      largo: 'El sistema bloqueó la cámara dentro de la app (WebSettings sin permiso o sin cuadro).' };
  }
  if (/OverconstrainedError/i.test(clave)) {
    return { corto: 'modo no soportado', clase: '',
      largo: 'La cámara no admite 160×120; pídelo otra vez desde el botón.' };
  }
  return { corto: 'no arranca', clase: '',
    largo: 'La cámara falló: ' + (clave || 'motivo desconocido') };
}

export function initGestures({ onPalm, onPinch, onFist, onError, video, canvas, button, label }) {
  const ctx = canvas.getContext('2d');
  let hands = null, stream = null, running = false, lastSend = 0, lastFire = 0, state = 'none';

  /**
   * El permiso de cámara, pedido al puente ANTES de tocar `getUserMedia`.
   *
   * Android no avisa por callback cuando el cuadro termina (el aviso existe —
   * `type:"perm"`— pero no sabemos si la dueña lo dejó abierto un minuto), así que
   * se pregunta `perms.has('camera')` cada seiscientos milisegundos durante quince
   * segundos. Si vuelve concedida, se sigue; si no, se corta con `NotAllowedError`
   * para que el mensaje sea el mismo que el de un «Denegar» explícito.
   */
  async function conPermisoDeCamara() {
    if (!puenteVivo()) return true;                 // navegador y escritorio: su propio cuadro
    let concedida = false;
    try { concedida = perms.has('camera'); } catch { concedida = false; }
    if (concedida) return true;
    label.textContent = 'dame la cámara…';
    try { perms.ask('camera'); } catch { /* sin puente no hay cuadro que abrir */ }
    for (let n = 0; n < 25; n++) {
      await espera(600);
      try { if (perms.has('camera')) return true; } catch { /* sigue esperando */ }
    }
    return false;
  }

  function loadScript(src) {
    return new Promise((res, rej) => {
      const s = document.createElement('script');
      s.src = src; s.onload = res; s.onerror = () => rej(new Error('fallo CDN MediaPipe'));
      document.head.appendChild(s);
    });
  }

  function classify(lm) {
    const d = (a, b) => Math.hypot(lm[a].x - lm[b].x, lm[a].y - lm[b].y);
    const wrist = 0;
    let ext = 0;
    for (const [tip, pip] of [[8, 6], [12, 10], [16, 14], [20, 18]])
      if (d(tip, wrist) > d(pip, wrist) * 1.15) ext++;
    if (d(4, 8) < .07) return 'pinch';
    if (ext >= 4) return 'palm';
    if (ext <= 1) return 'fist';
    return 'none';
  }

  function fire(g) {
    const now = performance.now();
    if (g === state || now - lastFire < 900) return;
    state = g; lastFire = now;
    label.textContent = { palm: 'PALMA ABIERTA', pinch: 'PINZA', fist: 'PUÑO', none: '…' }[g];
    ({ palm: onPalm, pinch: onPinch, fist: onFist })[g]?.();
  }

  function drawSkeleton(lm) {
    ctx.clearRect(0, 0, 160, 120);
    ctx.strokeStyle = 'rgba(80,220,255,.8)'; ctx.fillStyle = '#9fe8ff';
    const pairs = [[0,1],[1,2],[2,3],[3,7],[0,4],[4,5],[5,6],[6,8],[7,8],
                   [8,9],[9,10],[10,11],[11,12],[8,13],[13,14],[14,15],[15,16],
                   [0,17],[16,17],[5,17]];
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (const [a, b] of pairs) {
      ctx.moveTo(lm[a].x * 160, lm[a].y * 120);
      ctx.lineTo(lm[b].x * 160, lm[b].y * 120);
    }
    ctx.stroke();
    for (const p of lm) { ctx.beginPath(); ctx.arc(p.x * 160, p.y * 120, 1.6, 0, 7); ctx.fill(); }
  }

  async function start() {
    label.textContent = 'cargando…';
    // Primero el permiso, después todo lo demás: pedir 160×120 a una cámara que
    // Android no concedió sólo da un error confuso y gasta el cuadro de la dueña.
    if (!(await conPermisoDeCamara())) {
      const negado = new Error('Android no dejó abrir la cámara');
      negado.name = 'NotAllowedError';
      throw negado;
    }
    if (!hands) {
      await loadScript(MP_URL);
      hands = new window.Hands({ locateFile: f =>
        `https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/${f}` });
      hands.setOptions({ selfieMode: true, maxNumHands: 1, modelComplexity: 0,
        minDetectionConfidence: .55, minTrackingConfidence: .5 });
      hands.onResults(res => {
        if (res.multiHandLandmarks?.length) { drawSkeleton(res.multiHandLandmarks[0]);
          fire(classify(res.multiHandLandmarks[0])); }
        else { state = 'none'; label.textContent = 'buscando mano…'; }
      });
    }
    stream = await navigator.mediaDevices.getUserMedia(
      { video: { width: 160, height: 120, facingMode: 'user' } });
    video.srcObject = stream; await video.play();
    running = true;
    (function loop() {
      if (!running) return;
      requestAnimationFrame(loop);
      const now = performance.now();
      if (now - lastSend > 250 && video.readyState >= 2) { lastSend = now; hands.send({ image: video }); }
    })();
  }

  function stop() {
    running = false;
    stream?.getTracks().forEach(t => t.stop());
    stream = null; label.textContent = 'apagada';
    ctx.clearRect(0, 0, 160, 120);
  }

  button.onclick = async () => {
    if (running) { stop(); button.classList.remove('on'); document.getElementById('camwrap').classList.remove('show'); return; }
    try {
      await start();
      button.classList.add('on'); document.getElementById('camwrap').classList.add('show');
    } catch (e) {
      // El error se traduce y se entrega: un «sin cámara» a secas es lo que hacía
      // que este botón pareciera roto sin decir por qué.
      const porque = porqueFallo(e);
      stop();                                   // suelta la cámara si llegó a abrirse a medias
      label.textContent = porque.corto;
      if (onError) onError(porque, e);
      console.warn(e);
    }
  };
}
