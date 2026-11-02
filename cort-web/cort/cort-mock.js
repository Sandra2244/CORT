/**
 * CORT — Cerebro híbrido: puente real + simulador de respaldo
 *
 * Reemplaza window.WebSocket igual que hacía el mock de la demo de TechEnClair,
 * con el MISMO protocolo de mensajes para que la interfaz no note la diferencia.
 *
 * Desde la fase del cerebro real este archivo es un ENRUTADOR:
 *   lo que cort-bridge/cort_server.py puede medir de verdad (Ollama, clima,
 *   auditoría de seguridad, Jarvis OS, chat con modelo) se reenvía al puente en
 *   ws://<host>:8765/ws; lo demás se sigue simulando aquí, y se dice como
 *   simulación con la palabra «simulador» en pantalla. Si el puente no está,
 *   nada deja de funcionar: se vuelve al camino simulado.
 *
 * Base de protocolo: demo web de J.A.R.V.I.S (TechEnClair). Ver PROCEDENCIA.md.
 * Este archivo es código propio de CORT.
 */
(function () {
  "use strict";

  const STORAGE_KEY = "cort_web_v1";

  console.log("%c[CORT] Inicializando cerebro (puente real + simulador de respaldo)…", "color:#22d3ee;font-weight:bold;");

  // ---- el puente real ------------------------------------------------------------
  const WS_NATIVA = window.WebSocket;   // hay que capturarla antes de sustituir el global

  // Tipos que solo el puente puede responder con datos medidos.
  const REALES = new Set([
    "check_ollama_status", "pull_ollama_model", "set_local_model", "start_ollama",
    "get_agent_models", "set_agent_models",
    "av_scan_start", "av_scan_cancel", "av_threat_action",
    "check_jarvis_os_status", "jarvis_os_install", "jarvis_os_install_app",
    "jarvis_os_open_shared", "jarvis_os_restart", "jarvis_os_stop", "jarvis_os_uninstall",
    "user_input", "weather", "location_update"
  ]);
  // Estos también van al puente, pero la interfaz necesita su eco local inmediato.
  const REALES_CON_ECO = new Set(["update_settings"]);

  // Fase F1 — los paneles que en el censo del 2026-11-02 se quedaban girando sin
  // que nadie respondiera. Con el puente vivo, la orden viaja y el puente contesta
  // lo que mide o un `puente_aviso` con el motivo exacto y lo que haría falta; ya
  // no se pinta un dato inventado ni una rueda de carga eterna. Con el puente caído
  // se vuelve al simulador de esta página, que es lo único que queda.
  const VAN_AL_PUENTE = new Set([
    "vpn_get_status", "vpn_get_countries", "vpn_connect", "vpn_disconnect", "vpn_cancel",
    "get_winget_upgrades", "run_winget_upgrade",
    "get_installed_programs", "uninstall_program", "clean_leftovers",
    "games_get_library", "games_scan", "games_launch", "games_hide", "games_pick_folder", "detect_apps",
    "get_desktop_wallpaper",
    "ha_get_states", "ha_call_service", "ha_add_voice_alias",
    "get_shopping_list", "update_shopping_list",
    "print3d_check_deps", "print3d_check_hardware", "print3d_generate", "print3d_generate_lithophane",
    "print3d_install", "print3d_open_folder",
    "read_obsidian_note", "save_obsidian_note", "delete_obsidian_note",
    "get_windy_webcams", "iptv_open_file", "iptv_parse_m3u", "iptv_parse_url",
    "open_browser", "close_browser", "get_https_tunnel_status", "mobile_auth",
    "get_elevenlabs_voices", "check_local_tts_status", "check_kokoro_status",
    "claude_code_status", "av_speak", "toggle_mic", "toggle_fullscreen",
    "toggle_always_listen", "clear_cache", "temperatura"
  ]);

  // La demo lee unas respuestas por `s.type` y otras por `s.action` (live_subtitles,
  // jarvis_text, weather_panel, system_stats van por `action`). El puente siempre
  // manda `type`, así que se duplica el discriminador antes de entregar el mensaje.
  function normalizar(m) {
    const t = m.type || m.action;
    if (!t) return m;
    if (m.type !== t) m.type = t;
    if (m.action !== t) m.action = t;
    return m;
  }

  const PUENTE = {
    url: "ws://" + (location.hostname || "127.0.0.1") + ":8765/ws",
    ws: null,
    estado: "sin iniciar",
    reenviados: 0,
    recibidos: 0,
    ultimo_status: null,
    ultima_temperatura: null,
    avisos: {},
    escuchas: new Set(),
    _intento: 0,

    conectar() {
      if (this.ws && (this.ws.readyState === 0 || this.ws.readyState === 1)) return;
      this.estado = "conectando";
      let s;
      try { s = new WS_NATIVA(this.url); } catch (e) { this.estado = "bloqueado por el navegador"; return; }
      this.ws = s;
      s.onopen = () => {
        this.estado = "abierto";
        this._intento = 0;
        console.log("%c[CORT] puente real conectado en " + this.url + " — las medidas dejan de ser simuladas",
          "color:#10b981;font-weight:bold;");
      };
      s.onmessage = (ev) => {
        this.recibidos++;
        let m;
        try { m = JSON.parse(ev.data); } catch (e) { return; }
        this.difundir(m);
      };
      s.onclose = () => {
        this.estado = "caído";
        this.ws = null;
        this._intento++;
        // reintento suave: 3 intentos rápidos y luego uno cada 30 s para no martillar
        const espera = this._intento <= 3 ? 2000 * this._intento : 30000;
        setTimeout(() => this.conectar(), espera);
      };
      s.onerror = () => { try { s.close(); } catch (e) {} };
    },

    vivo() { return !!(this.ws && this.ws.readyState === 1); },

    enviar(obj) {
      if (!this.vivo()) return false;
      try { this.ws.send(JSON.stringify(obj)); this.reenviados++; return true; }
      catch (e) { return false; }
    },

    difundir(m) {
      const n = normalizar(m);
      // El estado del cerebro se guarda aparte: la fila de Ajustes lo pinta aunque
      // en ese instante no haya ninguna conexión de interfaz escuchando.
      if (n.type === "ollama_status_reply") {
        this.ultimo_status = n.status || null;
        if (typeof window.CORT_alEstadoCerebro === "function") {
          try { window.CORT_alEstadoCerebro(this.ultimo_status); } catch (e) {}
        }
      }
      // Los dos mensajeros nuevos del puente (fase F1) se guardan aparte y se
      // entregan a la pantalla por su propia vía: un aviso de "aquí no hay nadie"
      // tiene que pintarse dentro del panel afectado, no perderse entre subtítulos.
      if (n.type === "sala_temperatura") {
        this.ultima_temperatura = n.data || null;
        if (typeof window.CORT_alTemperatura === "function") {
          try { window.CORT_alTemperatura(n); } catch (e) {}
        }
      }
      if (n.type === "puente_aviso") {
        this.avisos[n.orden || n.panel || "?"] = n;
        if (typeof window.CORT_alAvisoPanel === "function") {
          try { window.CORT_alAvisoPanel(n); } catch (e) {}
        }
      }
      const a = Array.from(this.escuchas);
      if (!a.length) return;
      // La demo abre tres canales a la vez y solo uno es el que renderiza: el que
      // realmente envía las órdenes. Entregar a todos duplicaba cada subtítulo y
      // cada línea del escáner; entregar al primero no llegaba a la pantalla.
      let mejor = a[0];
      for (const w of a) if ((w._enviados || 0) > (mejor._enviados || 0)) mejor = w;
      // Regla de la fase F1: un dato EMPUJADO por el puente (nadie lo pidió) pinta
      // sus números, pero no tiene derecho a tapar la pantalla. La demo abre el
      // panel de clima en cuanto llega un `weather_panel`, así que se cierra justo
      // después si estaba cerrado. Lo que la usuaria pide sigue abriendo su panel.
      const climaAbiertoAntes = (() => {
        const p = document.getElementById("weather-panel");
        return !!(p && p.classList.contains("wp-visible"));
      })();
      mejor.dispatchServerMessage(n);
      if (n.empujado && n.type === "weather_panel" && !climaAbiertoAntes) {
        const p = document.getElementById("weather-panel");
        if (p) p.classList.remove("wp-visible");
      }
    }
  };

  // API de medición: se usa desde la consola del navegador para comprobar cuántos
  // mensajes contesta de verdad el puente frente a los que simula la página.
  window.CORT_puente = () => ({
    url: PUENTE.url,
    estado: PUENTE.estado,
    vivo: PUENTE.vivo(),
    reenviados: PUENTE.reenviados,
    recibidos_del_puente: PUENTE.recibidos,
    conexiones_ui: PUENTE.escuchas.size,
    urls_ui: Array.from(PUENTE.escuchas).map(w => w.url),
    // Diagnóstico de entrega: qué oyentes tiene la página y si comparten el mismo
    // manejador. Sirve para saber por qué un mensaje se ve una, dos o ninguna vez.
    oyentes: (() => {
      const a = Array.from(PUENTE.escuchas);
      return a.map((w, i) => ({
        i,
        url: w.url,
        listo: w.readyState,
        onmessage: typeof w.onmessage,
        oyeMensaje: !!w._oyeMensaje,
        igual_al_primero: i === 0 ? null : (w.onmessage === a[0].onmessage),
        entregados: w._entregados || 0,
        enviados: w._enviados || 0
      }));
    })(),
    tipos_reales: Array.from(REALES),
    tipos_al_puente: Array.from(VAN_AL_PUENTE),
    ultima_temperatura: PUENTE.ultima_temperatura,
    avisos: Object.keys(PUENTE.avisos),
    ultimo_status: PUENTE.ultimo_status
  });

  // El puente tiene un único canal real con Python. La fila de Ajustes manda por él
  // sus órdenes (elegir modelo, pedir descarga) en vez de abrir otro websocket: una
  // conexión extra se convertiría en otro oyente y se repartiría los mensajes con la
  // interfaz, que es justo lo que duplicaba los subtítulos.
  window.CORT_enviarAlCerebro = (obj) => PUENTE.enviar(obj);
  window.CORT_pedirEstadoCerebro = () => PUENTE.enviar({ type: "check_ollama_status" });

  // ---- datos reales que el navegador sí puede medir (no inventados) ----
  const HARDWARE = {
    nucleos: navigator.hardwareConcurrency || 0,
    ram_aprox_gib: navigator.deviceMemory || 0,
    idioma: navigator.language || "es",
    plataforma: navigator.platform || "desconocida"
  };

  // ---- estado inicial (claves idénticas a las que espera la interfaz) ----
  const defaultSettings = {
    user_name: "Sandra",
    user_age: "",
    user_city: "",
    image_search_engine: "duckduckgo",
    orb_style: "default",
    wallpaper: "/wallpapers/wallpaper_18.png",
    voice: "cort_sofi",
    realtime_voice: "marin",
    wake_word: "cort",
    musique_lien: "https://www.youtube.com",
    obsidian_vault_path: "",
    reminders: [
      { id: "1", text: "Probar la interfaz de CORT", time: "18:00", active: true }
    ],
    custom_apps: [
      { id: "terminal", label: "Terminal", exe_path: "x-terminal-emulator" },
      { id: "editor", label: "Editor de código", exe_path: "codium" }
    ],
    ha_custom_entities: {
      lumieres: [
        { nom: "Escritorio principal", entity_id: "light.bureau" },
        { nom: "Tira LED azul", entity_id: "light.salon_led" }
      ],
      prises: [{ nom: "Estación de trabajo", entity_id: "switch.pc_bureau" }],
      capteurs: [{ nom: "Temperatura interior", entity_id: "sensor.temp_bureau" }]
    }
  };

  let currentSettings = Object.assign({}, defaultSettings);
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) currentSettings = Object.assign({}, defaultSettings, JSON.parse(saved));
  } catch (e) { /* almacenamiento no disponible: seguimos con los valores por defecto */ }

  let shoppingItems = ["Café en grano", "Filamento 3D azul", "Cable USB-C trenzado"];

  // entity_id se conservan (son el identificador técnico); friendly_name va en español
  let haEntities = [
    { entity_id: "light.bureau", state: "on", attributes: { friendly_name: "Luz del escritorio", brightness: 220 } },
    { entity_id: "light.salon_led", state: "on", attributes: { friendly_name: "Tira LED del salón", rgb_color: [34, 211, 238] } },
    { entity_id: "light.cuisine", state: "off", attributes: { friendly_name: "Plafón de la cocina" } },
    { entity_id: "switch.pc_bureau", state: "on", attributes: { friendly_name: "Enchufe del PC" } },
    { entity_id: "switch.imprimante_3d", state: "off", attributes: { friendly_name: "Enchufe impresora 3D" } },
    { entity_id: "sensor.temp_bureau", state: "21.8", attributes: { friendly_name: "Sensor de temperatura", unit_of_measurement: "°C" } },
    { entity_id: "sensor.humidity_bureau", state: "48", attributes: { friendly_name: "Humedad del escritorio", unit_of_measurement: "%" } }
  ];

  // ---- el escáner de seguridad: la demo lo tenía como panel vacío; aquí responde ----
  const FALSOS_POSITIVOS = [
    { name: "cache_navegador.tmp", desc: "archivos temporales acumulados", target: "/tmp/cache_navegador.tmp" },
    { name: "informe_parcial.docx", desc: "documento huérfano en papelera", target: "~/.local/share/Trash/informe_parcial.docx" }
  ];

  class MockWebSocket extends EventTarget {
    // Constantes de clase: la interfaz compara `readyState === WebSocket.OPEN`.
    // Sin esto el canal parece cerrado y NINGÚN comando de chat se envía.
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSING = 2;
    static CLOSED = 3;

    constructor(url) {
      super();
      this.url = url;
      this.readyState = 0;
      this.onopen = null;
      this.onmessage = null;
      this.onerror = null;
      this.onclose = null;

      setTimeout(() => {
        this.readyState = 1;
        PUENTE.escuchas.add(this);
        PUENTE.conectar();
        console.log("%c[CORT] Canal de la interfaz abierto — puente real en " + PUENTE.url,
          "color:#10b981;font-weight:bold;");
        console.log(
          `%c[CORT] Hardware visto por el navegador: ${HARDWARE.nucleos} núcleos · ~${HARDWARE.ram_aprox_gib} GiB RAM · ${HARDWARE.idioma} · ${HARDWARE.plataforma}. La CPU y la RAM de verdad las mide el puente, no esta página.`,
          "color:#94a3b8;"
        );
        const ev = new Event("open");
        if (typeof this.onopen === "function") this.onopen(ev);
        this.dispatchEvent(ev);
        this.startSystemStats();
      }, 80);
    }

    send(dataStr) {
      this._enviados = (this._enviados || 0) + 1;
      try {
        this.handleClientMessage(JSON.parse(dataStr));
      } catch (err) {
        console.warn("[CORT MOCK] mensaje no parseable:", dataStr);
      }
    }

    close() {
      this.readyState = 3;
      PUENTE.escuchas.delete(this);
      if (this._statsInterval) clearInterval(this._statsInterval);
      const ev = new Event("close");
      if (typeof this.onclose === "function") this.onclose(ev);
      this.dispatchEvent(ev);
    }

    addEventListener(tipo, fn, ops) {
      if (tipo === "message") this._oyeMensaje = true;
      return super.addEventListener(tipo, fn, ops);
    }

    dispatchServerMessage(dataObj) {
      if (this.readyState !== 1) return;
      this._entregados = (this._entregados || 0) + 1;
      const ev = new MessageEvent("message", { data: JSON.stringify(dataObj) });
      if (typeof this.onmessage === "function") this.onmessage(ev);
      this.dispatchEvent(ev);
    }

    // CPU y RAM NO son legibles desde el navegador: si el puente está caído esto
    // es simulado y se dice como tal; si está vivo, callamos (él empuja lo medido).
    startSystemStats() {
      if (this._statsInterval) clearInterval(this._statsInterval);
      this._statsInterval = setInterval(() => {
        if (PUENTE.vivo()) return;
        this.dispatchServerMessage({
          action: "system_stats",
          cpu: 14 + Math.round(Math.random() * 12),
          ram: 38 + Math.round(Math.random() * 5),
          origen: "simulado"
        });
      }, 4000);
    }

    // Aviso una sola vez por carga de página: mejor que un mensaje por clic.
    avisoSimulacion(type) {
      console.warn(`[CORT] puente ausente: «${type}» lo responde el simulador, no una medida`);
      if (window._cort_avisopuente) return;
      window._cort_avisopuente = true;
      this.speak("El puente de CORT no responde en el puerto 8765, así que esto lo contesta el simulador: " +
                 "los números pueden no ser reales. Arranca cort-bridge/cort_server.py para medir de verdad.");
    }

    handleClientMessage(msg) {
      const type = msg.type;

      // ---- 1. Enrutador al puente real ------------------------------------
      const vaAlPuente = REALES.has(type) || REALES_CON_ECO.has(type) || VAN_AL_PUENTE.has(type);
      if (vaAlPuente) {
        if (!PUENTE.vivo()) PUENTE.conectar();
        if (PUENTE.vivo() && PUENTE.enviar(msg)) {
          if (!REALES_CON_ECO.has(type)) return;   // contesta el puente, no se simula
        } else if (REALES.has(type)) {
          this.avisoSimulacion(type);              // puente caído: se cae a la simulación
        }
      }

      // ---- 2. Respuestas locales para lo que el puente ya no puede tapar ---
      if (type === "check_ollama_status") {
        this.dispatchServerMessage({
          type: "ollama_status_reply",
          status: { online: false, found_local_models: {}, selected_model: "", origen: "simulado" }
        });
        return;
      }
      if (type === "check_jarvis_os_status") {
        this.dispatchServerMessage({ type: "jarvis_os_status_reply", installed: false, port: 3000,
                                     motivo: "puente ausente", origen: "simulado" });
        return;
      }
      if (type === "get_agent_models") {
        this.dispatchServerMessage({
          type: "agent_models_info",
          data: { available_models: { principal: ["qwen2.5:0.5b"], rapido: ["qwen2.5:0.5b"], seguro: ["qwen2.5:0.5b"] } },
          origen: "simulado"
        });
        return;
      }

      if (type === "get_settings") {
        this.dispatchServerMessage({ type: "settings_data", data: currentSettings });
        return;
      }

      if (type === "update_settings" && msg.settings) {
        currentSettings = Object.assign({}, currentSettings, msg.settings);
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(currentSettings)); } catch (e) {}
        this.dispatchServerMessage({ type: "settings_data", data: currentSettings });
        return;
      }

      if (type === "ha_get_states") {
        this.dispatchServerMessage({ type: "ha_states", success: true, states: haEntities });
        return;
      }

      if (type === "ha_call_service") {
        const ent = haEntities.find(e => e.entity_id === msg.entity_id);
        if (ent) {
          if (msg.service === "turn_on") ent.state = "on";
          else if (msg.service === "turn_off") ent.state = "off";
          else if (msg.service === "toggle") ent.state = ent.state === "on" ? "off" : "on";
          this.dispatchServerMessage({ type: "ha_state_changed", entity_id: ent.entity_id, state: ent });
        }
        return;
      }

      if (type === "get_shopping_list") {
        this.dispatchServerMessage({ type: "shopping_list", items: shoppingItems });
        return;
      }
      if (type === "shopping_add" && msg.item) {
        shoppingItems.push(msg.item);
        this.dispatchServerMessage({ type: "shopping_list", items: shoppingItems });
        return;
      }
      if (type === "shopping_remove" && typeof msg.index === "number") {
        shoppingItems.splice(msg.index, 1);
        this.dispatchServerMessage({ type: "shopping_list", items: shoppingItems });
        return;
      }
      if (type === "shopping_clear") {
        shoppingItems = [];
        this.dispatchServerMessage({ type: "shopping_list", items: shoppingItems });
        return;
      }

      if (type === "get_elevenlabs_voices") {
        this.dispatchServerMessage({
          type: "elevenlabs_voices_result",
          voices: [
            { voice_id: "cort_sofi", name: "Sofi (voz femenina, local)" },
            { voice_id: "cort_voz", name: "CORT (voz neutra, local)" },
            { voice_id: "cort_espeak", name: "espeak-ng (voz del sistema, sin descargar nada)" }
          ]
        });
        return;
      }

      // escáner de seguridad: la interfaz espera av_progress {percent, step, message},
      // av_threat_detected {threat}, av_complete {status}
      if (type === "av_scan_start") {
        this.runSecurityScan();
        return;
      }
      if (type === "av_scan_cancel") {
        this._scanCancelled = true;
        return;
      }

      if (type === "user_input" && typeof msg.text === "string") {
        this.handleUserChat(msg.text);
        return;
      }
    }

    runSecurityScan() {
      this._scanCancelled = false;
      const pasos = [
        [12, "núcleos del sistema", "analizando procesos en ejecución"],
        [34, "arranque", "revisando servicios iniciados con la sesión"],
        [58, "sistema de archivos", "recorriendo carpetas de usuario"],
        [79, "caché temporales", "midiendo espacio recuperable"],
        [100, "informe", "cerrando el análisis"]
      ];
      let i = 0;
      const tick = () => {
        if (this._scanCancelled) return;
        if (i >= pasos.length) {
          this.dispatchServerMessage({ type: "av_complete", status: "clean", threats: FALSOS_POSITIVOS.length });
          this.speak("Análisis terminado. No encontré amenazas reales, pero hay dos archivos huérfanos que puedo limpiar.");
          return;
        }
        const [pct, step, message] = pasos[i];
        this.dispatchServerMessage({ type: "av_progress", percent: pct, step: step, message: message });
        i++;
        if (i === 3) {
          FALSOS_POSITIVOS.forEach((t, k) => setTimeout(() => {
            if (!this._scanCancelled) this.dispatchServerMessage({ type: "av_threat_detected", threat: t });
          }, 400 * (k + 1)));
        }
        setTimeout(tick, 900);
      };
      this.dispatchServerMessage({ type: "av_start" });
      setTimeout(tick, 500);
    }

    handleUserChat(rawText) {
      const q = (rawText || "").toLowerCase();
      const nombre = currentSettings.user_name || "señora";
      const ciudad = currentSettings.user_city;

      this.dispatchServerMessage({ action: "user_speech", text: rawText });
      this.dispatchServerMessage({ state: "thinking" });

      setTimeout(() => {
        const tiene = (...v) => v.some(x => q.includes(x));

        if (tiene("hola", "buenos días", "buenas", "saludos", "cort", "sofi")) {
          return this.speak(`Buenos días, ${nombre}. Todos los sistemas de CORT en orden. ¿Qué necesitas?`);
        }
        if (tiene("qué hora", "la hora", "hora es")) {
          const h = new Date().toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" });
          return this.speak(`Son las ${h}.`);
        }
        if (tiene("qué día", "el día", "fecha")) {
          const d = new Date().toLocaleDateString("es", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
          return this.speak(`Hoy es ${d}.`);
        }
        if (tiene("clima", "tiempo", "temperatura exterior", "lluvia", "va a llover")) {
          // Con el puente vivo esta frase la contesta cort_server.py con open-meteo
          // y aquí no se llega. Si se llega, es que el puente está caído: no se
          // inventan grados, se dice.
          this.dispatchServerMessage({
            type: "puente_aviso", orden: "weather", panel: "weather-panel", origen: "simulado",
            motivo: "puente caído: sin medida de clima",
            hace_falta: "arranca cort-bridge/cort_server.py y vuelve a preguntar"
          });
          return this.speak("No te doy el clima: el puente que lo mide está apagado y no pienso inventarme los grados.");
        }
        if (tiene("temperatura", "grado", "cuánto marca")) {
          this.dispatchServerMessage({
            type: "puente_aviso", orden: "temperatura", panel: "temp-panel", origen: "simulado",
            motivo: "puente caído: sin lectura de sensores",
            hace_falta: "arranca cort-bridge/cort_server.py (lee /sys/class/thermal)"
          });
          return this.speak("Nada de números inventados: con el puente apagado no hay quién lea los sensores del equipo.");
        }
        if (tiene("música", "musica", "canción", "cancion", "playlist", "reproduce", "pon")) {
          this.dispatchServerMessage({
            type: "media_playing",
            title: "Reproduciendo (simulado) — lista de CORT",
            lyrics: "Aquí aparecerían la letra y el control real cuando conectemos el reproductor."
          });
          return this.speak(`Poniendo tu lista. Aún no controlo el reproductor de verdad: eso es lo siguiente.`);
        }
        if (tiene("enciende", "apaga", "prende", "luz", "luces", "lámpara", "lampara", "enchufe")) {
          const apagar = tiene("apaga", "apagar", "enciende no", "off");
          const luz = haEntities.find(e => e.entity_id === "light.bureau");
          if (luz) {
            luz.state = apagar ? "off" : "on";
            this.dispatchServerMessage({ type: "ha_state_changed", entity_id: luz.entity_id, state: luz });
          }
          return this.speak(apagar ? "Luces del escritorio apagadas." : "Luces del escritorio al cien por ciento.");
        }
        if (tiene("compra", "lista", "mercado")) {
          this.dispatchServerMessage({ type: "shopping_open" });
          this.dispatchServerMessage({ type: "shopping_list", items: shoppingItems });
          return this.speak(`Tu lista tiene ${shoppingItems.length} artículos. Te la abrí en pantalla.`);
        }
        if (tiene("cpu", "ram", "memoria", "sistema", "rendimiento", "peso")) {
          return this.speak(
            `Este navegador reporta ${HARDWARE.nucleos} núcleos y unos ${HARDWARE.ram_aprox_gib} gigabytes de RAM. ` +
            "El porcentaje que ves arriba en el HUD todavía es simulado: el navegador no puede leer la CPU real. Eso lo trae el backend."
          );
        }
        if (tiene("virus", "amenaza", "escaneo", "análisis", "analisis", "seguridad", "optimiza")) {
          this.dispatchServerMessage({ type: "av_open" });
          this.runSecurityScan();
          return this.speak("Iniciando el análisis de seguridad. Te aviso cuando termine.");
        }
        if (tiene("busca", "google", "encuentra")) {
          return this.speak(`Entendido: buscar «${rawText}». La búsqueda real depende del módulo de navegador, que aún no está conectado.`);
        }
        if (tiene("quién eres", "quien eres", "qué eres", "que eres", "tu nombre")) {
          return this.speak("Soy CORT: Cognitiva, Omnipresente, Rapsodia, Terminal. Puedo llamarme Sofi cuando quieras voz femenina.");
        }
        if (tiene("gracias")) {
          return this.speak(`A sus órdenes, ${nombre}.`);
        }

        this.speak(`Recibido: «${rawText}». Estoy en modo simulador, así que respondo con lo que ya tengo implementado: hora, fecha, clima, temperatura, música, luces, lista de compras, estado del sistema, escaneo de seguridad y mi presentación. Lo demás llegará con el backend.`);
      }, 700);
    }

    // Un solo camino para hablar: estado del orbe + subtítulo vivo + texto + reposo
    speak(texto) {
      const id = "cort-" + Date.now();
      this.dispatchServerMessage({ state: "speaking" });
      // live_subtitles es lo que hace aparecer el HUD de subtítulos de verdad
      this.dispatchServerMessage({ action: "live_subtitles", id, phase: "start" });
      const trozos = texto.match(/.{1,24}/g) || [texto];
      trozos.forEach((t, k) => {
        setTimeout(() => this.dispatchServerMessage({ action: "live_subtitles", id, phase: "delta", text: t + " " }), 60 * (k + 1));
      });
      setTimeout(() => {
        this.dispatchServerMessage({ action: "live_subtitles", id, phase: "end" });
        this.dispatchServerMessage({ action: "jarvis_text", text: texto });
      }, 60 * (trozos.length + 1));
      setTimeout(() => this.dispatchServerMessage({ state: "idle" }), Math.max(3500, texto.length * 45));
    }
  }

  window.WebSocket = MockWebSocket;

  // Evitamos el popup de geolocalización sin fingir una ciudad real
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition = function (success) {
      if (typeof success === "function") {
        success({ coords: { latitude: 0, longitude: 0, accuracy: 0 } });
      }
    };
  }

  console.log("%c[CORT] Simulador listo. Palabra de activación configurada: «" + currentSettings.wake_word + "»", "color:#10b981;font-weight:bold;");
})();
