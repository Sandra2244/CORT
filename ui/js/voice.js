/* ===== VOZ de CORT =====
   Oído: dictado con texto EN VIVO mientras hablas + palabra de activación «Oye CORT».
   Habla: voz grave estilo JARVIS.
   En Android usa el puente nativo (SpeechRecognizer + TextToSpeech);
   en un navegador de PC cae a Web Speech API. */

const N = window.CortNative || null;

// cómo suele transcribir el reconocedor «Oye CORT»
const WAKE = /\b(?:oye|hey|ey|oie|ok|okay|hola)?[\s,]*(cort|court|kort|corte|cor|korth|cortt)\b[\s,.:]*/i;
const WAKE_ONLY = /^\s*(?:oye|hey|ey|oie|ok|okay|hola)[\s,]+(cort|court|kort|corte|cor|korth)\b|^\s*(cort|court|kort)\b/i;

export function createVoice(h = {}) {
  const lang = h.lang || 'es-MX';
  const cfg = { voice: '', pitch: 0.82, rate: 1.0 };   // JARVIS: grave y pausado
  let mode = 'idle';            // idle | cmd | wake
  let wakeOn = false, speaking = false, wakeTimer = 0, backoff = 400;
  let afterSpeak = null;        // acción pendiente al terminar de hablar
  const waiters = new Map();
  let seq = 0;

  const emitState = () => h.onState && h.onState(mode, { wakeOn, speaking });

  function scheduleWake(ms = backoff) {
    clearTimeout(wakeTimer);
    if (!wakeOn || speaking || mode !== 'idle') return;
    wakeTimer = setTimeout(() => { if (wakeOn && !speaking && mode === 'idle') startSession('wake'); }, ms);
  }

  /* ------------------------------ eventos ------------------------------ */
  function onFinal(text, alts) {
    const m = mode;
    if (m === 'cmd') { h.onFinal && h.onFinal(text); return; }
    if (m === 'wake') {
      const cand = [text, ...(alts || [])].find(t => WAKE_ONLY.test(t) || WAKE.test(t) && /oye|hey|ok/i.test(t));
      if (!cand) return;
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
        else if (mode === 'cmd' && ev.error === 'no-speech') h.onError && h.onError('no-speech');
        break;
      case 'stt-end':
        mode = 'idle'; emitState(); scheduleWake(); break;
      case 'tts-start': h.onSpeak && h.onSpeak(true); break;
      case 'tts-end': {
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
      case 'pause': cancel(); break;
      case 'resume': scheduleWake(600); break;
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
    configure(o) { Object.assign(cfg, Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined && v !== ''))); },
    config: () => ({ ...cfg }),
    /** Escuchar UNA orden (botón 🎙). Si ya escucha, la termina. */
    listen() {
      if (mode === 'cmd') { if (N) N.stopListening(); else web.stop(); return; }
      if (speaking) this.stopSpeaking();
      if (mode === 'wake') { mode = 'switching'; if (N) N.cancelListening(); else web.cancel(); }
      setTimeout(() => startSession('cmd'), mode === 'switching' ? 250 : 0);
    },
    /** escucha permanente «Oye CORT» */
    setWake(on) {
      wakeOn = !!on;
      if (wakeOn) { backoff = 400; scheduleWake(50); } else if (mode === 'wake') cancel();
      emitState();
    },
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
        if (N) N.speak(t.slice(0, 3800), id, cfg.voice || '', +cfg.pitch || 0.82, +cfg.rate || 1);
        else web.speak(t.slice(0, 3800), id);
        setTimeout(() => { if (waiters.has(id)) handle({ type: 'tts-end', id }); }, 4000 + t.length * 110);
      });
    },
    stopSpeaking() {
      if (N) N.stopSpeaking(); else web.stopSpeak();
      [...waiters.keys()].forEach(id => handle({ type: 'tts-end', id }));
    },
    voices() {
      if (N) { try { return JSON.parse(N.voices()); } catch { return { voices: [], default: '' }; } }
      const vs = ('speechSynthesis' in window ? speechSynthesis.getVoices() : []).filter(v => /^es/i.test(v.lang));
      return { voices: vs.map(v => ({ name: v.name, locale: v.lang, local: v.localService, male: /male|hombre|jorge|pablo|diego|raul/i.test(v.name) && !/female/i.test(v.name) })), default: '' };
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
