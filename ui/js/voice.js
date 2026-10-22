/* ===== VOZ de CORT =====
   Oído: dictado con texto EN VIVO mientras hablas + palabra de activación «Oye CORT».
   Habla: voz grave estilo JARVIS.
   En Android usa el puente nativo (SpeechRecognizer + TextToSpeech);
   en un navegador de PC cae a Web Speech API.

   ── La boca se elige SOLA, y eso es lo que faltaba (medido 2026-10-22) ──
   Hay tres bocas posibles y un cuarto caso que es no tener ninguna:

     «nativa»    el `TextToSpeech` del teléfono, a través de `CortNative.speak()`
     «navegador» las voces que da `speechSynthesis` (Windows y macOS: sí da)
     «núcleo»    el motor de voz del equipo, por `POST /api/voice/say` → WAV
     «muda»      no hay ninguna: se AVISA, no se finge que se habló

   En el Linux de Sandra el navegador responde pero **no da voces**: abriendo
   `scripts/sonda-voz.html` en este Chromium sale `motor: sí · voces: 0`, y el
   evento `voiceschanged` se dispara con la lista vacía igual. Como `speak()` sin
   voz también salta su `onend`, CORT parecía hablar y no se oía nada, y los
   deslizadores de 07 · Perfil no mandaban en nada. El equipo sí tiene `espeak-ng`
   (10 timbres en español comprobados uno a uno), así que en Linux la boca pasa a
   ser el núcleo y los tres mandos —timbre, tono, velocidad— viajan en el POST. */

const N = window.CortNative || null;

// cómo suele transcribir el reconocedor «Oye CORT»
const WAKE = /\b(?:oye|hey|ey|oie|ok|okay|hola)?[\s,]*(cort|court|kort|corte|cor|korth|cortt)\b[\s,.:]*/i;
const WAKE_ONLY = /^\s*(?:oye|hey|ey|oie|ok|okay|hola)[\s,]+(cort|court|kort|corte|cor|korth)\b|^\s*(cort|court|kort)\b/i;

export function createVoice(h = {}) {
  const lang = h.lang || 'es-MX';
  const cfg = { voice: '', pitch: 0.82, rate: 1.0 };   // JARVIS: grave y pausado
  /* `h.api()` es la base del núcleo (en Android es '' porque la pantalla la sirve
     el propio backend). Se pide como función y no como cadena porque `API` en
     hud.js aún no está descubierto cuando se construye la voz. */
  const api = () => { try { return (h.api ? h.api() : '') || ''; } catch { return ''; } };
  let nucl = null;              // respuesta de GET /api/voice: {motor, voces[], motivo}
  let audio = null;             // el <audio> que está sonando por el núcleo
  let mode = 'idle';            // idle | cmd | wake
  let wakeOn = false, speaking = false, wakeTimer = 0, backoff = 400;
  let afterSpeak = null;        // acción pendiente al terminar de hablar
  let enPausa = false;          // la app está en segundo plano: micro cerrado
  let intentos = 0;             // siestas del «Oye CORT» en las que nadie habló
  let ultimoHabla = 0;          // milisegundos del último `tts-end` (ver `hayMusica`)
  const frenos = new Set();     // motivos que no dejan rearmar el micro
  const waiters = new Map();
  let seq = 0;

  const emitState = () => h.onState && h.onState(mode, { wakeOn, speaking, freno: motivoFreno() });

  function motivoFreno() {
    if (enPausa) return 'en segundo plano';
    if (frenos.size) return [...frenos][0];
    if (typeof document !== 'undefined' && document.hidden) return 'pantalla apagada';
    if (hayMusica()) return 'música sonando';
    return '';
  }

  /** Si suena música en el aparato, el micro NO se rearma: en Android abrir el
      micrófono baja el volumen de lo demás (y en un teléfono de gama media lo
      traba). Es el motivo por el que CORT se calla el oído mientras escuchas.

      El margen de 1,5 s es lo que evita el efecto contrario: el `TextToSpeech` de
      Android también hace que `isMusicActive()` diga «sí», así que sin margen
      CORT se quedaría sin oído justo después de contestarte. */
  function hayMusica() {
    if (!N || typeof N.musicPlaying !== 'function') return false;   // app vieja / PC
    if (Date.now() - ultimoHabla < 1500) return false;               // era CORT hablando
    try { return !!N.musicPlaying(); } catch { return false; }
  }

  /** El micro en bucle cerrado es lo que consume un teléfono: si tras varias
      escucha nadie ha dicho «Oye CORT», se españa mucho más. */
  function retroceso() {
    const ESCALERA = [400, 1200, 2500, 5000, 10000];
    backoff = ESCALERA[Math.min(intentos, ESCALERA.length - 1)];
  }

  function scheduleWake(ms = backoff) {
    clearTimeout(wakeTimer);
    if (!wakeOn || speaking || mode !== 'idle') return;
    if (motivoFreno()) {                     // no hay micro que valga: se reintenta suave
      wakeTimer = setTimeout(() => scheduleWake(2000), 2000);
      return;
    }
    wakeTimer = setTimeout(() => { if (wakeOn && !speaking && mode === 'idle' && !motivoFreno()) startSession('wake'); }, ms);
  }

  /* ------------------------------ eventos ------------------------------ */
  function onFinal(text, alts) {
    const m = mode;
    if (m === 'cmd') { h.onFinal && h.onFinal(text); return; }
    if (m === 'wake') {
      const cand = [text, ...(alts || [])].find(t => WAKE_ONLY.test(t) || WAKE.test(t) && /oye|hey|ok/i.test(t));
      if (!cand) { intentos++; retroceso(); return; }   // nadie llamó: más siesta
      intentos = 0; retroceso();
      const rest = cand.replace(WAKE, ' ').replace(/\s+/g, ' ').trim();
      h.onWake && h.onWake(rest, cand);
    }
  }

  function handle(ev) {
    switch (ev.type) {
      case 'stt-start': emitState(); break;
      case 'stt-speech': h.onSpeech && h.onSpeech(mode); break;
      case 'stt-level': h.onLevel && h.onLevel(ev.level, mode); break;
      case 'stt-partial': if (mode === 'cmd') h.onPartial && h.onPartial(ev.text); break;
      case 'stt-final': backoff = 400; onFinal(ev.text, ev.alts); break;
      case 'stt-error':
        if (ev.error === 'not-allowed' || ev.error === 'service-not-allowed') {
          wakeOn = false; h.onError && h.onError(ev.error);
        } else if (ev.error === 'network') { backoff = Math.min(8000, backoff * 2); h.onError && h.onError('network'); }
        else if (ev.error === 'busy') { intentos += 2; retroceso(); }  // el micro lo tiene otro
        else if (mode === 'wake' && (ev.error === 'no-speech' || ev.error === 'abort')) { intentos++; retroceso(); }
        else if (mode === 'cmd' && ev.error === 'no-speech') h.onError && h.onError('no-speech');
        break;
      case 'stt-end':
        mode = 'idle'; emitState(); scheduleWake(); break;
      case 'tts-start': h.onSpeak && h.onSpeak(true); break;
      case 'tts-end': {
        ultimoHabla = Date.now();
        const w = waiters.get(ev.id); waiters.delete(ev.id);
        if (!waiters.size) { speaking = false; h.onSpeak && h.onSpeak(false); }
        w && w();
        if (!speaking) {
          const a = afterSpeak; afterSpeak = null;
          if (a) a(); else scheduleWake(250);
        }
        emitState();
        break;
      }
      case 'perm': h.onPermission && h.onPermission(ev.kind, ev.granted); break;
      // `pause` y `resume` los manda el Java del APK (`CortNative.pausa()` y
      // `reanuda()`) cuando la app se va a segundo plano. Sin `enPausa`, el temporizador
      // de «Oye CORT» reabría el micrófono cuatrocientos milisegundos después de
      // cerrarlo la actividad: así es como el teléfono se quedaba trabado.
      case 'pause': enPausa = true; cancel(); break;
      case 'resume': enPausa = false; intentos = 0; retroceso(); scheduleWake(600); break;
    }
  }

  /* --------------------------- motor: Android --------------------------- */
  let web = null;     // motor Web Speech (PC)
  if (N) window.__cortNative.on(handle);
  else {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    web = {
      SR, rec: null,
      listen(m) {
        if (!SR) { handle({ type: 'stt-error', error: 'service-not-allowed' }); handle({ type: 'stt-end' }); return; }
        const r = new SR(); this.rec = r;
        r.lang = lang; r.interimResults = true; r.continuous = false; r.maxAlternatives = 3;
        r.onstart = () => handle({ type: 'stt-start' });
        r.onresult = e => {
          const res = e.results[e.results.length - 1];
          if (res.isFinal) handle({ type: 'stt-final', text: res[0].transcript, alts: [...res].map(a => a.transcript) });
          else handle({ type: 'stt-partial', text: [...e.results].map(x => x[0].transcript).join('') });
        };
        r.onerror = e => handle({ type: 'stt-error', error: e.error });
        r.onend = () => { this.rec = null; handle({ type: 'stt-end' }); };
        try { r.start(); } catch { handle({ type: 'stt-end' }); }
      },
      stop() { this.rec && this.rec.stop(); },
      cancel() { this.rec && this.rec.abort(); },
      speak(text, id) {
        if (!('speechSynthesis' in window)) { setTimeout(() => handle({ type: 'tts-end', id }), 0); return; }
        speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        u.lang = lang; u.rate = cfg.rate; u.pitch = cfg.pitch;
        const v = speechSynthesis.getVoices().find(x => x.name === cfg.voice);
        if (v) u.voice = v;
        u.onstart = () => handle({ type: 'tts-start', id });
        u.onend = u.onerror = () => handle({ type: 'tts-end', id });
        speechSynthesis.speak(u);
      },
      stopSpeak() { 'speechSynthesis' in window && speechSynthesis.cancel(); },
    };
  }

  /* ------------------------------ la boca ------------------------------ */
  function vocesWeb() {
    if (!('speechSynthesis' in window)) return [];
    try { return speechSynthesis.getVoices(); } catch { return []; }
  }

  /** Qué boca tiene este aparato AHORA. Se decide en cada `speak()` porque en
      Chromium las voces llegan TARDE: la primera llamada puede no ver ninguna y
      la siguiente sí. */
  function boca() {
    if (N) return 'nativa';
    if (vocesWeb().length) return 'navegador';
    if (nucl && nucl.motor && (nucl.voces || []).length) return 'núcleo';
    return 'muda';
  }

  /** Preguntar al núcleo qué motor de voz tiene este equipo. Se llama al arrancar
      y cuando el núcleo se descubre tarde: enumerar los timbres cuesta ~1 s en el
      equipo (se sintetiza cada voz para comprobar que de verdad sale audio), así
      que el núcleo lo cachea y la cara repinta el desplegable al resolver esto. */
  async function descubreMotor() {
    if (N) return null;                       // el teléfono habla solo: no pregunta
    try {
      const r = await fetch(api() + '/api/voice');
      nucl = r.ok ? await r.json() : null;
    } catch { nucl = null; }                  // sin núcleo: la cara ya lo dice sola
    h.onBoca && h.onBoca(boca(), nucl);
    return nucl;
  }

  /** Hablar por el motor del equipo: el núcleo devuelve el WAV y aquí suena.
      El `object URL` se libera al terminar (en 1,8 GiB de RAM no se dejan audios
      colgando) y cada fallo tiene su palabra: el silencio sin motivo fue justo lo
      que hizo dudar de toda la sección de voz. */
  function hablaPorNucleo(texto, id) {
    const cuerpo = JSON.stringify({ texto, voz: cfg.voice || '',
                                    tono: cfg.pitch, velocidad: cfg.rate });
    const termina = (motivo) => {
      if (audio) {
        try { URL.revokeObjectURL(audio.src); } catch { /* ya estaba liberado */ }
        audio = null;
      }
      if (motivo) h.onError && h.onError('boca:' + motivo);
      handle({ type: 'tts-end', id });
    };
    fetch(api() + '/api/voice/say', {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: cuerpo,
    }).then(async r => {
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        termina(j.error || 'HTTP-' + r.status);
        return;
      }
      const a = new Audio(URL.createObjectURL(await r.blob()));
      audio = a;
      a.onplay = () => handle({ type: 'tts-start', id });
      a.onended = () => termina('');
      a.onerror = () => termina('no-suena-aqui');
      a.play().catch(() => termina('bloqueado-al-reproducir'));
    }).catch(() => termina('sin-nucleo'));
  }

  function startSession(m) {
    clearTimeout(wakeTimer);
    mode = m; emitState();
    if (N) N.listen(lang, m); else web.listen(m);
  }
  function cancel() {
    clearTimeout(wakeTimer);
    if (mode === 'idle') return;
    if (N) N.cancelListening(); else web.cancel();
  }

  /* ------------------------------ API ------------------------------ */
  return {
    get available() {
      if (N) { try { return JSON.parse(N.available()).stt; } catch { return true; } }
      return !!(web && web.SR);
    },
    get mode() { return mode; },
    get wakeOn() { return wakeOn; },
    get speaking() { return speaking; },
    /* Se descarta sólo `undefined`, NO la cadena vacía: vacía en `voice` quiere
       decir «automática», y con el filtro antiguo volver de una variante a la
       automática no se aplicaba nunca (el Perfil guardaba '' pero el cfg seguía
       con la voz elegida hasta reiniciar la cara). */
    configure(o) { Object.assign(cfg, Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined))); },
    config: () => ({ ...cfg }),
    get boca() { return boca(); },
    /** lo que respondió `GET /api/voice` (motor, timbres y motivo si no hay) */
    motor: () => nucl,
    descubreMotor,
    /** Escuchar UNA orden (botón 🎙). Si ya escucha, la termina. */
    listen() {
      if (mode === 'cmd') { if (N) N.stopListening(); else web.stop(); return; }
      if (speaking) this.stopSpeaking();
      if (mode === 'wake') { mode = 'switching'; if (N) N.cancelListening(); else web.cancel(); }
      intentos = 0; retroceso();               // ella ha pulsado: se le hace caso ya
      setTimeout(() => startSession('cmd'), mode === 'switching' ? 250 : 0);
    },
    /** escucha permanente «Oye CORT» */
    setWake(on) {
      wakeOn = !!on;
      if (wakeOn) { intentos = 0; retroceso(); scheduleWake(50); } else if (mode === 'wake') cancel();
      emitState();
    },
    /**
     * Freno del oído mientras se hace otra cosa cara. `motivo` es para que la
     * lámpara pueda decir POR QUÉ CORT no escucha (en el teléfono el micrófono
     * abierto en segundo plano es lo que traba el aparato y lo que baja la
     * música), y como es un conjunto admiten solaparse: «optimizando» y «música».
     */
    suspender(motivo = 'ocupada') {
      frenos.add(motivo);
      if (mode === 'wake') cancel();
      emitState();
    },
    reanudar(motivo = 'ocupada') {
      frenos.delete(motivo);
      if (!frenos.size && wakeOn && mode === 'idle') scheduleWake(400);
      emitState();
    },
    get freno() { return motivoFreno(); },
    /** Hablar. Devuelve una promesa que se cumple al terminar. */
    speak(text, then) {
      const t = String(text || '').replace(/[*_#`>]+/g, '').replace(/https?:\/\/\S+/g, 'el enlace').trim();
      if (!t) return Promise.resolve();
      if (mode === 'wake') cancel();          // que no se escuche a sí misma
      const id = 'u' + (++seq);
      speaking = true; emitState();
      if (then) afterSpeak = then;
      return new Promise(res => {
        waiters.set(id, res);
        const b = boca();
        if (N) N.speak(t.slice(0, 3800), id, cfg.voice || '', +cfg.pitch || 0.82, +cfg.rate || 1);
        else if (b === 'núcleo') hablaPorNucleo(t.slice(0, 3800), id);
        else if (b === 'navegador') web.speak(t.slice(0, 3800), id);
        else {
          /* Sin boca: se AVISA y la promesa se cumple, porque si no CORT se queda
             «hablando» para siempre y el orbe no vuelve a su sitio. En Linux con
             el núcleo apagado es el caso normal, y en Windows sólo pasa si el
             sistema no tiene ni una voz instalada. */
          h.onError && h.onError('sin-boca');
          setTimeout(() => handle({ type: 'tts-end', id }), 0);
        }
        setTimeout(() => { if (waiters.has(id)) handle({ type: 'tts-end', id }); }, 4000 + t.length * 110);
      });
    },
    stopSpeaking() {
      if (N) N.stopSpeaking();
      else {
        web && web.stopSpeak();
        if (audio) {
          try { audio.pause(); URL.revokeObjectURL(audio.src); } catch { /* ya liberado */ }
          audio = null;
        }
      }
      [...waiters.keys()].forEach(id => handle({ type: 'tts-end', id }));
    },
    voices() {
      if (N) { try { return JSON.parse(N.voices()); } catch { return { voices: [], default: '' }; } }
      const b = boca();
      /* Por el núcleo el `name` que ve la cara es el CÓDIGO que entiende espeak
         (`es`, `es+f4`, `es-419+m3`) porque es lo que hay que devolver en el POST;
         la etiqueta bonita viaja aparte en `etiqueta`. */
      if (b === 'núcleo') {
        return { voices: (nucl.voces || []).map(v => ({
          name: v.voz, etiqueta: v.nombre, locale: 'es', local: true, male: !!v.male,
        })), default: '', boca: b, motor: nucl.motor, motivo: '' };
      }
      const vs = vocesWeb().filter(v => /^es/i.test(v.lang));
      return { voices: vs.map(v => ({ name: v.name, etiqueta: v.name, locale: v.lang,
        local: v.localService, male: /male|hombre|jorge|pablo|diego|raul/i.test(v.name) && !/female/i.test(v.name) })),
        default: '', boca: b,
        motivo: b === 'muda' ? ((nucl && nucl.motivo) || '') : '' };
    },
    /** después de hablar, abre el micrófono para la orden (tras «Oye CORT») */
    listenAfterSpeaking() { afterSpeak = () => startSession('cmd'); },
  };
}

/* Permisos nativos (en PC siempre «sí») */
export const perms = {
  has: k => (N ? N.hasPermission(k) : true),
  ask: k => N && N.requestPermission(k),
  settings: () => N && N.openAppSettings(),
};
