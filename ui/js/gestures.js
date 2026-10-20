/* ===== Gestos de mano — MODO LIGERO =====
   MediaPipe Hands con 1 sola mano, cámara 160×120 y análisis cada ~250 ms.
   La cámara NO se enciende hasta pulsar el botón de mano (privacidad y RAM). */

const MP_URL = 'https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/hands.min.js';

export function initGestures({ onPalm, onPinch, onFist, video, canvas, button, label }) {
  const ctx = canvas.getContext('2d');
  let hands = null, stream = null, running = false, lastSend = 0, lastFire = 0, state = 'none';

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
    } catch (e) { label.textContent = 'sin cámara'; console.warn(e); }
  };
}
