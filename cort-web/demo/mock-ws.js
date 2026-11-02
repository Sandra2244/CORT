/**
 * J.A.RV.I.S — Simulateur WebSocket pour Démo Web Publique (TechEnClair)
 * Remplace window.WebSocket pour faire fonctionner l'interface complète
 * (orbs, réglages, domotique, météo, courses, commandes chat interactives)
 * sans aucun backend Python.
 */
(function () {
  console.log("%c[JARVIS DEMO] Initialisation du simulateur WebSocket embarqué...", "color:#22d3ee;font-weight:bold;");

  // Stockage local persistant des réglages démo
  const STORAGE_KEY = "jarvis_demo_settings_v1";

  const defaultSettings = {
    user_name: "Invité",
    user_age: "",
    user_city: "Paris",
    image_search_engine: "duckduckgo",
    orb_style: "default",
    wallpaper: "/wallpapers/wallpaper_18.jpg",
    voice: "elevenlabs_jarvis",
    realtime_voice: "marin",
    wake_word: "jarvis",
    musique_lien: "https://www.youtube.com",
    obsidian_vault_path: "",
    reminders: [
      { id: "1", text: "Tester l'interface JARVIS", time: "18:00", active: true }
    ],
    custom_apps: [
      { id: "terminal", label: "Terminal Stark", exe_path: "cmd.exe" },
      { id: "editor", label: "Code Studio", exe_path: "code.exe" }
    ],
    ha_custom_entities: {
      lumieres: [
        { nom: "Bureau Principal", entity_id: "light.bureau" },
        { nom: "Bandeau LED Cyan", entity_id: "light.salon_led" }
      ],
      prises: [
        { nom: "Station Gaming", entity_id: "switch.pc_bureau" }
      ],
      capteurs: [
        { nom: "Température Intérieure", entity_id: "sensor.temp_bureau" }
      ]
    }
  };

  let currentSettings = Object.assign({}, defaultSettings);
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) currentSettings = Object.assign({}, defaultSettings, JSON.parse(saved));
  } catch (e) {}

  let shoppingItems = ["Café en grains", "Filament 3D Cyan", "Câble USB-C tressé"];
  let haEntities = [
    { entity_id: "light.bureau", state: "on", attributes: { friendly_name: "Lumière Bureau", brightness: 220 } },
    { entity_id: "light.salon_led", state: "on", attributes: { friendly_name: "Bandeau LED Salon", rgb_color: [34, 211, 238] } },
    { entity_id: "light.cuisine", state: "off", attributes: { friendly_name: "Plafonnier Cuisine" } },
    { entity_id: "switch.pc_bureau", state: "on", attributes: { friendly_name: "Prise Station PC" } },
    { entity_id: "switch.imprimante_3d", state: "off", attributes: { friendly_name: "Prise Imprimante 3D" } },
    { entity_id: "sensor.temp_bureau", state: "21.8", attributes: { friendly_name: "Capteur Température Bureau", unit_of_measurement: "°C" } },
    { entity_id: "sensor.humidity_bureau", state: "48", attributes: { friendly_name: "Humidité Bureau", unit_of_measurement: "%" } }
  ];

  class MockWebSocket extends EventTarget {
    constructor(url) {
      super();
      this.url = url;
      this.readyState = 0; // CONNECTING
      this.onopen = null;
      this.onmessage = null;
      this.onerror = null;
      this.onclose = null;

      setTimeout(() => {
        this.readyState = 1; // OPEN
        console.log("%c[JARVIS DEMO] WebSocket connecté (Mode Virtuel)", "color:#10b981;font-weight:bold;");
        const openEv = new Event("open");
        if (typeof this.onopen === "function") this.onopen(openEv);
        this.dispatchEvent(openEv);

        // Déclencher les stats système périodiques
        this.startSystemStats();
      }, 80);
    }

    send(dataStr) {
      try {
        const msg = JSON.parse(dataStr);
        this.handleClientMessage(msg);
      } catch (err) {
        console.warn("[MOCK WS] Message client invalide:", dataStr);
      }
    }

    close() {
      this.readyState = 3; // CLOSED
      const closeEv = new Event("close");
      if (typeof this.onclose === "function") this.onclose(closeEv);
      this.dispatchEvent(closeEv);
    }

    dispatchServerMessage(dataObj) {
      if (this.readyState !== 1) return;
      const str = JSON.stringify(dataObj);
      const ev = new MessageEvent("message", { data: str });
      if (typeof this.onmessage === "function") this.onmessage(ev);
      this.dispatchEvent(ev);
    }

    startSystemStats() {
      if (this._statsInterval) clearInterval(this._statsInterval);
      this._statsInterval = setInterval(() => {
        const cpu = 14 + Math.round(Math.random() * 12);
        const ram = 38 + Math.round(Math.random() * 5);
        this.dispatchServerMessage({
          action: "system_stats",
          cpu: cpu,
          ram: ram
        });
      }, 4000);
    }

    handleClientMessage(msg) {
      const type = msg.type;

      // 1. Initialisation des paramètres
      if (type === "get_settings") {
        this.dispatchServerMessage({
          type: "settings_data",
          data: currentSettings
        });
        return;
      }

      // 2. Mise à jour des paramètres (Orbs, Wallpaper, Nom...)
      if (type === "update_settings" && msg.settings) {
        currentSettings = Object.assign({}, currentSettings, msg.settings);
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(currentSettings)); } catch (e) {}
        this.dispatchServerMessage({
          type: "settings_data",
          data: currentSettings
        });
        return;
      }

      // 3. Home Assistant
      if (type === "ha_get_states") {
        this.dispatchServerMessage({
          type: "ha_states",
          success: true,
          states: haEntities
        });
        return;
      }

      if (type === "ha_call_service") {
        const ent = haEntities.find(e => e.entity_id === msg.entity_id);
        if (ent) {
          if (msg.service === "turn_on") ent.state = "on";
          else if (msg.service === "turn_off") ent.state = "off";
          else if (msg.service === "toggle") ent.state = ent.state === "on" ? "off" : "on";
          this.dispatchServerMessage({
            type: "ha_state_changed",
            entity_id: ent.entity_id,
            state: ent
          });
        }
        return;
      }

      // 4. Liste de courses
      if (type === "get_shopping_list") {
        this.dispatchServerMessage({
          type: "shopping_list",
          items: shoppingItems
        });
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

      // 5. Clarté micro / voix
      if (type === "get_elevenlabs_voices") {
        this.dispatchServerMessage({
          type: "elevenlabs_voices_result",
          voices: [
            { voice_id: "elevenlabs_jarvis", name: "J.A.R.V.I.S (TechEnClair Official)" },
            { voice_id: "elevenlabs_friday", name: "F.R.I.D.A.Y (Assistante)" },
            { voice_id: "elevenlabs_adam", name: "Adam (Voix Profonde)" }
          ]
        });
        return;
      }

      // 6. Entrée Utilisateur : Commandes Textuelles / Chat interactif
      if (type === "user_input" && typeof msg.text === "string") {
        this.handleUserChat(msg.text);
        return;
      }

      // 7. Actions diverses : notification conviviale mode démo
      if (type === "desktop_wallpaper_result" || type === "get_desktop_wallpaper") {
        return;
      }
    }

    handleUserChat(rawText) {
      const q = (rawText || "").trim().toLowerCase();

      // 1. Afficher ce que l'utilisateur a dit
      this.dispatchServerMessage({
        action: "user_speech",
        text: rawText
      });

      // 2. Orb passe en écoute / réflexion
      this.dispatchServerMessage({ state: "thinking" });

      setTimeout(() => {
        // Scénarios prédéfinis riches
        if (q.includes("meteo") || q.includes("météo") || q.includes("temps")) {
          this.dispatchServerMessage({ state: "speaking" });
          this.dispatchServerMessage({
            action: "weather_panel",
            data: {
              ville: currentSettings.user_city || "Paris",
              temperature: 22,
              ressenti: 23,
              humidite: 50,
              vent: 14,
              code: 1,
              description: "Éclaircies agréables"
            }
          });
          this.streamJarvisResponse(`Voici les prévisions météo pour ${currentSettings.user_city || "Paris"} : 22°C avec un ciel partiellement dégagé, conditions idéales.`);
          return;
        }

        if (q.includes("temp") || q.includes("temperature") || q.includes("température")) {
          this.dispatchServerMessage({ state: "speaking" });
          this.dispatchServerMessage({
            action: "temp_panel",
            data: {
              piece: "Bureau Principal",
              temperature: "21.8",
              humidite: "48%"
            }
          });
          this.streamJarvisResponse("La température dans votre bureau est actuellement stabilisée à 21.8 degrés.");
          return;
        }

        if (q.includes("musique") || q.includes("music") || q.includes("chanson") || q.includes("playlist")) {
          this.dispatchServerMessage({ state: "speaking" });
          this.dispatchServerMessage({
            type: "media_playing",
            title: "AC/DC — Back In Black (Stark Lab Mix)",
            lyrics: "Back in black, I hit the sack / I've been too long, I'm glad to be back..."
          });
          this.streamJarvisResponse("Lancement de la playlist Stark Industries. Volume ajusté.");
          return;
        }

        if (q.includes("lumiere") || q.includes("lumière") || q.includes("allume") || q.includes("eteint") || q.includes("éteint")) {
          const bureau = haEntities.find(e => e.entity_id === "light.bureau");
          if (bureau) {
            bureau.state = q.includes("eteint") || q.includes("éteint") ? "off" : "on";
            this.dispatchServerMessage({ type: "ha_state_changed", entity_id: bureau.entity_id, state: bureau });
          }
          this.dispatchServerMessage({ state: "speaking" });
          this.streamJarvisResponse(bureau && bureau.state === "on" ? "Lumières du bureau passées à 100% de puissance." : "Extinction des luminaires effectuée.");
          return;
        }

        if (q.includes("course") || q.includes("liste")) {
          this.dispatchServerMessage({ state: "speaking" });
          this.dispatchServerMessage({ type: "shopping_open" });
          this.streamJarvisResponse(`Votre liste contient actuellement ${shoppingItems.length} article(s). Le panneau a été ouvert.`);
          return;
        }

        if (q.includes("bonjour") || q.includes("salut") || q.includes("hello") || q.includes("jarvis")) {
          this.dispatchServerMessage({ state: "speaking" });
          this.streamJarvisResponse(`Bonjour ${currentSettings.user_name || "Monsieur"} ! Tous les systèmes de l'armure sont opérationnels. Comment puis-je vous assister ?`);
          return;
        }

        if (q.includes("orb") || q.includes("theme") || q.includes("thème") || q.includes("visage")) {
          this.dispatchServerMessage({ state: "speaking" });
          this.streamJarvisResponse("Vous pouvez changer l'orbe réactif 3D à tout moment dans le menu Paramètres ou via la palette de raccourcis.");
          return;
        }

        // Réponse générale bienveillante rappelant le mode démo
        this.dispatchServerMessage({ state: "speaking" });
        this.streamJarvisResponse(`Commande bien reçue : « ${rawText} ». En mode démo en ligne, certaines fonctions natives (ex: contrôle Windows, IA Realtime OpenAI, Impression 3D) nécessitent l'installation de J.A.R.V.I.S sur votre PC.`);
      }, 700);
    }

    streamJarvisResponse(fullText) {
      this.dispatchServerMessage({
        action: "jarvis_text",
        text: fullText
      });
      // Réinitialiser l'orb à idle après quelques secondes
      setTimeout(() => {
        this.dispatchServerMessage({ state: "idle" });
      }, Math.max(3500, fullText.length * 45));
    }
  }

  // Remplacement global du constructeur WebSocket
  window.WebSocket = MockWebSocket;

  // Intercepter les requêtes de géolocalisation pour éviter le popup du navigateur
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition = function (success) {
      if (typeof success === "function") {
        success({
          coords: { latitude: 48.8566, longitude: 2.3522, accuracy: 10 }
        });
      }
    };
  }

  console.log("%c[JARVIS DEMO] Simulateur WebSocket activé avec succès.", "color:#10b981;font-weight:bold;");
})();


  // Injection correctif CSS global pour forcer le masquage des panneaux inactifs
  const fixStyle = document.createElement("style");
  fixStyle.id = "jarvis-demo-panel-fix";
  fixStyle.textContent = `
    .uninstaller-panel:not(.visible),
    .uninstaller-panel.hidden,
    .uninstaller-leftovers-container.hidden,
    .av-panel:not(.visible),
    .av-panel.hidden,
    .vpn-panel:not(.visible),
    .vpn-panel.hidden,
    .games-panel:not(.visible),
    .games-panel.hidden,
    .email-hud-panel:not(.visible),
    .email-hud-panel.hidden,
    .shopping-panel:not(.visible),
    .shopping-panel.hidden,
    .restaurant-panel:not(.visible),
    .restaurant-panel.hidden,
    .obsidian-panel:not(.visible),
    .obsidian-panel.hidden,
    .print3d-panel:not(.visible),
    .print3d-panel.hidden,
    .iptv-panel:not(.visible),
    .iptv-panel.hidden,
    .ha-panel:not(.visible),
    .ha-panel.hidden,
    .webcam-preview-panel.hidden,
    #winget-panel,
    #winget-logs-container {
      display: none !important;
    }
  `;
  document.head.appendChild(fixStyle);

  // Élimination automatique de l'écran de chargement de boot si bloqué
  function clearBootOverlay() {
    const ov = document.getElementById("boot-overlay");
    if (ov) {
      ov.style.transition = "opacity 0.4s ease";
      ov.style.opacity = "0";
      setTimeout(() => { ov.style.display = "none"; }, 400);
    }
  }

  window.addEventListener("DOMContentLoaded", () => {
    setTimeout(clearBootOverlay, 1500);
  });
  window.addEventListener("load", () => {
    setTimeout(clearBootOverlay, 1200);
  });