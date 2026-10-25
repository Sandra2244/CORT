/* ===== Cámara y gestos de mano — la vista primero =====
   MediaPipe Hands con 1 sola mano, cámara 320×240 y análisis cada ~250 ms.
   La cámara NO se enciende hasta pulsar el botón de mano (privacidad y RAM).

   Ronda 2.2: antes se lanzaba `getUserMedia()` a pelo. En el navegador eso abre
   el cuadro de permiso del propio navegador; **en el WebView de Android no**:
   ahí hay que tener concedido `CAMERA` por el sistema, y sin eso el `getUserMedia`
   falla con `NotAllowedError`. Ahora se pide el permiso al puente ANTES de
   encender nada, y el error se traduce a español con su causa.

   F22 · lo que estaba mal y aquí se arregla: la cámara se abría DESPUÉS de bajar
   MediaPipe del CDN. Sin datos (o con jsDelivr bloqueado) no se abría ni la
   vista, y el lienzo sólo tenía un esqueleto de 160×120 sobre fondo negro —no la
   imagen—, así que parecía que «los sensores no funcionan». Ahora:

     1. permiso → 2. cámara y vista pintando de verdad → 3. modelo, si se puede.

   Si el modelo no llega, la cámara sigue encendida y se avisa «cámara sí ·
   gestos no»; no se apaga lo que sí funcionaba. El vídeo se copia al lienzo sin
   espejar y el CSS espeja el lienzo entero (imagen + esqueleto), de modo que
   las dos capas coinciden. Por eso `selfieMode` va en `false`: MediaPipe debe
   devolver coordenadas del vídeo crudo, no de una imagen ya volteada. */

import { perms } from './voice.js';

const MP_URL = 'https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/hands.min.js';
const MP_BASE = 'https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1675469240/';
const ANCHO = 160, ALTO = 120;
const ESPERA_ANALISIS = 250;      // una pasada de la mano cada cuarto de segundo
const ESPERA_CUADRO = 70;         // la vista, ~14 cuadros por segundo (batería)
const TOPE_FALLOS = 3;            // tres envíos rotos y el modelo se retira

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
      largo: 'La cámara no admite el tamaño pedido; vuelve a pulsar la mano.' };
  }
  return { corto: 'no arranca', clase: '',
    largo: 'La cámara falló: ' + (clave || 'motivo desconocido') };
}

export function initGestures({ onPalm, onPinch, onFist, onError, video, canvas, button, label }) {
  const ctx = canvas.getContext('2d');
  let hands = null, stream = null, running = false;
  let lastSend = 0, lastFire = 0, state = 'none';
  let puntos = null;                 // última mano vista (para pintarla sobre el vídeo)
  let fallosEnvio = 0;
  let modeloAvisado = false;
  let turno = 0;                     // apagar y encender rápido no deja dos bucles vivos

  /**
   * El permiso de cámara, pedido al puente ANTES de tocar `getUserMedia`.
   *
   * Android no avisa por callback cuando el cuadro termina (el aviso existe —
   * `type:"perm"`— pero no sabemos si la dueña lo dejó abierto un minuto), así que
   * se pregunta `perms.has('camera')` cada seiscientos milisegundos. Veinticuatro
   * segundos: leer el cuadro con calma no puede convertirse en un fallo.
   */
  async function conPermisoDeCamara() {
    if (!puenteVivo()) return true;                 // navegador y escritorio: su propio cuadro
    let concedida = false;
    try { concedida = perms.has('camera'); } catch { concedida = false; }
    if (concedida) return true;
    label.textContent = 'dame la cámara…';
    try { perms.ask('camera'); } catch { /* sin puente no hay cuadro que abrir */ }
    return esperaRespuestaDePermiso();
  }

  /* El aviso `type:"perm"` de Java llega en cuanto la dueña toca el cuadro: con
     él se sabe al instante si dijo «Denegar», en vez de esperar veinticuatro
     segundos con la etiqueta en «dame la cámara…». La consulta periódica queda
     como respaldo para un WebView que no entregue el aviso. */
  function esperaRespuestaDePermiso() {
    return new Promise(listo => {
      let hecho = false;
      const cierra = ok => { if (!hecho) { hecho = true; listo(ok); } };
      const nativo = window.__cortNative;
      if (nativo && typeof nativo.on === 'function') {
        nativo.on(ev => {
          if (!ev || ev.type !== 'perm') return;
          const k = String(ev.kind || '').toLowerCase();
          if (k.startsWith('camara') || k.startsWith('camera')) cierra(!!ev.granted);
        });
      }
      (async () => {
        for (let n = 0; n < 40 && !hecho; n++) {
          await espera(600);
          try { if (perms.has('camera')) return cierra(true); } catch { /* sigue */ }
        }
        cierra(false);
      })();
    });
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

  function dibujaEsqueleto(lm) {
    // Sin `clearRect`: la imagen del vídeo ya está debajo y el hueso va encima.
    ctx.strokeStyle = 'rgba(80,220,255,.85)'; ctx.fillStyle = '#9fe8ff';
    const pairs = [[0,1],[1,2],[2,3],[3,7],[0,4],[4,5],[5,6],[6,8],[7,8],
                   [8,9],[9,10],[10,11],[11,12],[8,13],[13,14],[14,15],[15,16],
                   [0,17],[16,17],[5,17]];
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    for (const [a, b] of pairs) {
      ctx.moveTo(lm[a].x * ANCHO, lm[a].y * ALTO);
      ctx.lineTo(lm[b].x * ANCHO, lm[b].y * ALTO);
    }
    ctx.stroke();
    for (const p of lm) { ctx.beginPath(); ctx.arc(p.x * ANCHO, p.y * ALTO, 1.6, 0, 7); ctx.fill(); }
  }

  /* La vista: copia los cuadros de la cámara al lienzo y, si hay mano, su
     esqueleto. Es lo primero que se enciende y sigue sola aunque el modelo
     tarde o no llegue; es la prueba visible de que la cámara responde. */
  function pinta() {
    const era = turno;
    const cuadro = () => {
      if (!running || era !== turno) return;
      if (video.readyState >= 2 && video.videoWidth > 0) {
        try { ctx.drawImage(video, 0, 0, ANCHO, ALTO); } catch { /* cuadro a medias */ }
        if (puntos) dibujaEsqueleto(puntos);
      }
      setTimeout(cuadro, ESPERA_CUADRO);
    };
    cuadro();
  }

  function avisaSinModelo(e) {
    if (modeloAvisado) return;
    modeloAvisado = true;
    puntos = null;
    label.textContent = 'cámara sí · gestos no';
    if (onError) onError({
      corto: 'cámara sí · gestos no', clase: 'modelo',
      largo: 'La cámara está viendo, pero no pude cargar el modelo de gestos '
        + '(revisa los datos o la conexión). La vista sigue encendida; '
        + 'la apagas con el mismo botón de la mano.',
    }, e);
  }

  async function preparaModelo() {
    try {
      await loadScript(MP_URL);
      if (!window.Hands) throw new Error('MediaPipe cargó pero no dejó Hands');
      if (!running) return;                       // la apagaron mientras bajaba
      hands = new window.Hands({ locateFile: f => MP_BASE + f });
      hands.setOptions({
        selfieMode: false,          // las coordenadas van con el vídeo crudo; el CSS espeja
        maxNumHands: 1, modelComplexity: 0,
        minDetectionConfidence: .55, minTrackingConfidence: .5,
      });
      hands.onResults(res => {
        if (!running) return;
        const lm = res.multiHandLandmarks && res.multiHandLandmarks[0];
        puntos = lm || null;
        if (lm) fire(classify(lm));
        else {
          state = 'none';
          if (!/cámara sí/.test(label.textContent)) label.textContent = 'buscando mano…';
        }
      });
      if (!running) return;
      label.textContent = 'buscando mano…';
      analiza();
    } catch (e) {
      hands = null;
      avisaSinModelo(e);
      console.warn('gestos: sin modelo', e);
    }
  }

  /* Envía cuadros al modelo sin bloquear la vista. Si `send` falla tres veces
     seguidas (memoria, WebGL del WebView), se retira el modelo y queda la cámara:
     un fallo de gestos no puede apagar la imagen que sí funciona. */
  function analiza() {
    const era = turno;
    const paso = () => {
      if (!running || era !== turno) return;
      setTimeout(paso, ESPERA_ANALISIS);
      if (!hands || video.readyState < 2) return;
      const ahora = performance.now();
      if (ahora - lastSend < ESPERA_ANALISIS) return;
      lastSend = ahora;
      let enviando = null;
      try { enviando = hands.send({ image: video }); }
      catch (e) { enviando = Promise.reject(e); }
      if (enviando && typeof enviando.catch === 'function') {
        enviando.catch(e => {
          fallosEnvio++;
          if (fallosEnvio >= TOPE_FALLOS) { hands = null; avisaSinModelo(e); }
        });
      }
    };
    paso();
  }

  async function start() {
    label.textContent = 'encendiendo la cámara…';
    // Primero el permiso: pedir 320×240 a una cámara que Android no concedió
    // sólo da un error confuso y gasta el cuadro de la dueña.
    if (!(await conPermisoDeCamara())) {
      const negado = new Error('Android no dejó abrir la cámara');
      negado.name = 'NotAllowedError';
      throw negado;
    }
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 320 }, height: { ideal: 240 }, facingMode: 'user' },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();                  // el toque del botón ya cuenta como gesto
    turno++;
    running = true;
    fallosEnvio = 0; modeloAvisado = false;
    label.textContent = 'cámara lista · buscando el modelo…';
    pinta();                             // la imagen arranca ya
    preparaModelo();                     // sin `await`: no puede retrasar la vista
  }

  function stop() {
    turno++;
    running = false;
    puntos = null;
    stream?.getTracks().forEach(t => t.stop());
    stream = null;
    try { if (video.srcObject) video.srcObject = null; } catch { /* ya estaba suelto */ }
    label.textContent = 'apagada';
    ctx.clearRect(0, 0, ANCHO, ALTO);
  }

  button.onclick = async () => {
    if (running) {
      stop(); button.classList.remove('on');
      document.getElementById('camwrap')?.classList.remove('show');
      return;
    }
    try {
      await start();
      button.classList.add('on');
      document.getElementById('camwrap')?.classList.add('show');
    } catch (e) {
      // El error se traduce y se entrega: un «sin cámara» a secas es lo que hacía
      // que este botón pareciera roto sin decir por qué.
      const porque = porqueFallo(e);
      stop();                                   // suelta la cámara si llegó a abrirse a medias
      label.textContent = porque.corto;
      // La etiqueta y la fila de permiso viven DENTRO del panel: si no se abre,
      // el error se cuenta en el canal pero la dueña no ve dónde tocar.
      document.getElementById('camwrap')?.classList.add('show');
      if (onError) onError(porque, e);
      console.warn(e);
    }
  };
}
