/**
 * CORT — motor de marca e idiomas
 *
 * Hace tres cosas sobre la interfaz:
 *   1. Renombra JARVIS → CORT en todo lo visible (y J.A.R.V.I.S → CORT).
 *   2. Traduce la interfaz a español por defecto, con conmutador es / fr / en.
 *   3. Fuerza la voz del navegador a español.
 *
 * No modifica el bundle minificado: actúa sobre el DOM ya renderizado y sobre
 * los atributos de texto. Es reversible quitando una línea de index.html.
 *
 * Cobertura MEDIBLE: window.CORT.estado() dice cuántas cadenas visibles hay,
 * cuántas están traducidas y cuáles faltan. No se afirma nada sin medirlo.
 */
(function () {
  "use strict";

  // ---- 1. Marca -----------------------------------------------------------
  const MARCA = [
    [/J\.A\.R\.V\.I\.S/g, "CORT"],
    [/\bJARVIS\b/g, "CORT"],
    [/\bJarvis\b/g, "CORT"],
    [/\bjarvis\b/g, "cort"],
    [/\bF\.R\.I\.D\.A\.Y\b/g, "Sofi"],
    [/\bV10\.5\b/g, "v0"],
    [/\bv10\.5\b/g, "v0"]
  ];
  function brand(s) {
    let out = s;
    for (const [re, to] of MARCA) out = out.replace(re, to);
    return out;
  }

  // ---- 2. Diccionario [francés, español, inglés] --------------------------
  // Francés es el idioma original de la interfaz; la clave se normaliza.
  const D = [
    // HUD y estado general
    ["MENU PRINCIPAL", "MENÚ PRINCIPAL", "MAIN MENU"],
    ["Menu principal CORT", "Menú principal de CORT", "CORT main menu"],
    ["DEMANDEZ : « CORT, QUE PEUX-TU FAIRE ? »", "PREGUNTA: «CORT, ¿QUÉ PUEDES HACER?»", "ASK: “CORT, WHAT CAN YOU DO?”"],
    ['"CORT, que peux-tu faire ?"', '"CORT, ¿qué puedes hacer?"', '"CORT, what can you do?"'],
    ["veille...", "en vela…", "watching..."],
    ["connecte", "conectado", "connected"],
    ["ONLINE", "EN LÍNEA", "ONLINE"],
    ["CORT · HOLO MODE", "CORT · MODO HOLO", "CORT · HOLO MODE"],
    ["LOCAL_TIME", "HORA_LOCAL", "LOCAL_TIME"],
    ["SYS_CLOCK", "RELOJ_SIS", "SYS_CLOCK"],
    ["CONFORT THERMIQUE", "CONFORT TÉRMICO", "THERMAL COMFORT"],
    ["ATMOSPHERIC_SCAN", "ANALISIS_ATMOSFERICO", "ATMOSPHERIC_SCAN"],
    ["THERMAL_SCAN // HOME", "ESCANEO_TERMICO // INICIO", "THERMAL_SCAN // HOME"],
    ["HUMIDITÉ", "HUMEDAD", "HUMIDITY"],
    ["VENT", "VIENTO", "WIND"],
    ["ÉTAT", "ESTADO", "STATE"],
    ["RESSENTI", "SENSACIÓN", "FEELS LIKE"],
    ["ACQUIRING...", "OBTENIENDO...", "ACQUIRING..."],
    ["MERCI D'AVOIR INSTALLÉ CORT", "GRACIAS POR INSTALAR CORT", "THANK YOU FOR INSTALLING CORT"],
    ["BIENVENUE DANS CORT OS", "BIENVENIDO A CORT OS", "WELCOME TO CORT OS"],
    ["RECETTE CORT", "RECETA CORT", "CORT RECIPE"],
    ["INGRÉDIENTS", "INGREDIENTES", "INGREDIENTS"],
    ["INSTRUCTIONS", "INSTRUCCIONES", "INSTRUCTIONS"],
    ["PASSER / FERMER", "SALTAR / CERRAR", "SKIP / CLOSE"],
    ["DÉMARRAGE DU SOUS-SYSTÈME...", "ARRANCANDO EL SUBSISTEMA…", "STARTING SUBSYSTEM..."],
    ["DÉMARRAGE EN COURS...", "ARRANQUE EN CURSO…", "BOOTING..."],
    ["PRÉNOM", "NOMBRE", "FIRST NAME"],
    ["ÂGE", "EDAD", "AGE"],
    ["Fermer", "Cerrar", "Close"],
    ["Fermer (Esc)", "Cerrar (Esc)", "Close (Esc)"],
    ["❌ FERMER", "❌ CERRAR", "❌ CLOSE"],
    ["ANNULER", "CANCELAR", "CANCEL"],
    ["SAUVEGARDER", "GUARDAR", "SAVE"],
    ["SAUVEGARDER & APPLIQUER", "GUARDAR Y APLICAR", "SAVE & APPLY"],
    ["ACTUALISER", "ACTUALIZAR", "REFRESH"],
    ["INSTALLER", "INSTALAR", "INSTALL"],
    ["Fermer complètement CORT", "Cerrar CORT por completo", "Fully close CORT"],

    // Ajustes
    ["PARAMÈTRES", "AJUSTES", "SETTINGS"],
    ["CONFIGURATION API", "CONFIGURACIÓN DE APIs", "API CONFIGURATION"],
    ["CONFIGURATION PROFIL", "CONFIGURACIÓN DE PERFIL", "PROFILE CONFIGURATION"],
    ["CONFIGURATION DU STOCKAGE", "CONFIGURACIÓN DEL ALMACÉN", "STORAGE CONFIGURATION"],
    ["TÉLÉCHARGEMENT & LANCEMENT", "DESCARGA Y ARRANQUE", "DOWNLOAD & LAUNCH"],
    ["MICROPHONE", "MICRÓFONO", "MICROPHONE"],
    ["Microphone", "Micrófono", "Microphone"],
    ["Aucun microphone détecté", "No se detectó ningún micrófono", "No microphone detected"],
    ["Activer le microphone", "Activar el micrófono", "Enable the microphone"],
    ["Mode écoute permanente", "Modo de escucha permanente", "Always-listening mode"],
    ["CAMÉRA (WEB-CAM / VISION & HOLOGRAMME)", "CÁMARA (WEBCAM / VISIÓN Y HOLOGRAMA)", "CAMERA (WEBCAM / VISION & HOLOGRAM)"],
    ["📹 RETOUR CAMÉRA", "📹 VISTA DE CÁMARA", "📹 CAMERA FEED"],
    ["VILLE PAR DÉFAUT (Météo & Restaurants)", "CIUDAD POR DEFECTO (Clima y restaurantes)", "DEFAULT CITY (Weather & Restaurants)"],
    ["STYLE DE L'ORBE (ORB)", "ESTILO DEL ORBE", "ORB STYLE"],
    ["ORB ASSOCIÉ AU FOND D'ÉCRAN", "ORBE ASOCIADO AL FONDO DE PANTALLA", "ORB LINKED TO WALLPAPER"],
    ["FONDS D'ÉCRAN / ORB", "FONDOS DE PANTALLA / ORBE", "WALLPAPERS / ORB"],
    ["GALERIE OFFICIELLE DE THÈMES SCI-FI", "GALERÍA OFICIAL DE TEMAS SCI-FI", "OFFICIAL SCI-FI THEME GALLERY"],
    ["AJUSTEMENTS VISUELS", "AJUSTES VISUALES", "VISUAL ADJUSTMENTS"],
    ["APPLIQUER LE THÈME", "APLICAR EL TEMA", "APPLY THEME"],
    ["APPLIQUER LE MODE", "APLICAR EL MODO", "APPLY MODE"],
    ["VOIX DE L'IA", "VOZ DE LA IA", "AI VOICE"],
    ["MOTEUR RECHERCHE IMAGES", "MOTOR DE BÚSQUEDA DE IMÁGENES", "IMAGE SEARCH ENGINE"],
    ["🛡️ SÉCURITÉ DU SYSTÈME", "🛡️ SEGURIDAD DEL SISTEMA", "🛡️ SYSTEM SECURITY"],
    ["🤖 AGENT MODELE", "🤖 MODELO DE AGENTE", "🤖 AGENT MODEL"],
    ["IA locale (Ollama)", "IA local (Ollama)", "Local AI (Ollama)"],
    ["✅ Service Ollama connecté !", "✅ ¡Servicio Ollama conectado!", "✅ Ollama service connected!"],
    ["LANCER CORT AU DÉMARRAGE DU PC", "INICIAR CORT AL ENCENDER EL EQUIPO", "LAUNCH CORT AT STARTUP"],
    ["PERFORMANCES & ACCÈS", "RENDIMIENTO Y ACCESO", "PERFORMANCE & ACCESS"],
    ["🔴 LLM Local (Astro / Trash Mode)", "🔴 LLM local (modo Astro / chatarra)", "🔴 Local LLM (Astro / Trash Mode)"],
    ["🟢 Mode Par Défaut", "🟢 Modo por defecto", "🟢 Default Mode"],
    ["ELEVENLABS API (Voix Ultra-Réalistes)", "ELEVENLABS API (voces ultrarrealistas)", "ELEVENLABS API (Ultra-realistic voices)"],
    ["🎙️ NVIDIA NEMOTRON ASR (LOCAL)", "🎙️ NVIDIA NEMOTRON ASR (LOCAL)", "🎙️ NVIDIA NEMOTRON ASR (LOCAL)"],
    ["Toute revente est strictement interdite.", "Queda prohibida su reventa.", "Resale is strictly prohibited."],

    // Menú y paneles
    ["DOMOTIQUE", "DOMÓTICA", "HOME AUTOMATION"],
    ["🏠 DOMOTIQUE // CONNECTIVITÉ HOME ASSISTANT", "🏠 DOMÓTICA // CONEXIÓN HOME ASSISTANT", "🏠 HOME AUTOMATION // HOME ASSISTANT"],
    ["APPAREILS HOME ASSISTANT", "DISPOSITIVOS HOME ASSISTANT", "HOME ASSISTANT DEVICES"],
    ["CHARGEMENT DE LA GRILLE DOMOTIQUE...", "CARGANDO LA REJILLA DOMÓTICA…", "LOADING AUTOMATION GRID..."],
    ["LUMIÈRES", "LUCES", "LIGHTS"],
    ["PRISES & INTERS", "ENCHUFES E INTERRUPTORES", "PLUGS & SWITCHES"],
    ["ASPIRATEURS", "ASPIRADORAS", "VACUUMS"],
    ["VENTILATEURS", "VENTILADORES", "FANS"],
    ["CAPTEURS", "SENSORES", "SENSORS"],
    ["LISTE COURSES", "LISTA DE COMPRAS", "SHOPPING LIST"],
    ["VIDER LA LISTE", "VACIAR LA LISTA", "CLEAR LIST"],
    ["LECTEUR VIDÉO / IPTV", "REPRODUCTOR DE VÍDEO / IPTV", "VIDEO / IPTV PLAYER"],
    ["📺 LECTEUR IPTV & VIDÉO", "📺 REPRODUCTOR IPTV Y VÍDEO", "📺 IPTV & VIDEO PLAYER"],
    ["MES JEUX", "MIS JUEGOS", "MY GAMES"],
    ["CORT // GAME_LIBRARY", "CORT // BIBLIOTECA_DE_JUEGOS", "CORT // GAME_LIBRARY"],
    ["⟳ SCANNER LE PC", "⟳ ESCANEAR EL EQUIPO", "⟳ SCAN PC"],
    ["ANALYSE DES BIBLIOTHÈQUES EN COURS...", "ANALIZANDO BIBLIOTECAS…", "ANALYZING LIBRARIES..."],
    ["AUCUN JEU DÉTECTÉ", "NINGÚN JUEGO DETECTADO", "NO GAMES DETECTED"],
    ["0 JEU DÉTECTÉ", "0 juegos detectados", "0 games detected"],
    ["RECHERCHER UN JEU...", "BUSCAR UN JUEGO…", "SEARCH A GAME..."],
    ["ANTIVIRUS", "ANTIVIRUS", "ANTIVIRUS"],
    ["🛡️ ANTIVIRUS & SÉCURITÉ", "🛡️ ANTIVIRUS Y SEGURIDAD", "🛡️ ANTIVIRUS & SECURITY"],
    ["🛡️ FONCTIONNEMENT DE L'ANTIVIRUS", "🛡️ CÓMO FUNCIONA EL ANTIVIRUS", "🛡️ HOW THE ANTIVIRUS WORKS"],
    ["SECURITY_CORE // ANTIVIRUS_SCAN", "NUCLEO_SEGURIDAD // ESCANEO", "SECURITY_CORE // ANTIVIRUS_SCAN"],
    ["SYS_CORE_SCANNER_AWAITING_TRIGGER...", "ESCÁNER ESPERANDO ORDEN…", "SCANNER AWAITING TRIGGER..."],
    ["MENACES DÉTECTÉES: 0", "AMENAZAS DETECTADAS: 0", "THREATS DETECTED: 0"],
    ["SYS_STATUS: STANDBY", "ESTADO_SIS: EN ESPERA", "SYS_STATUS: STANDBY"],
    ["NETTOYER LES TRACES", "LIMPIAR RASTROS", "CLEAN TRACES"],
    ["IMPRESSION 3D", "IMPRESIÓN 3D", "3D PRINTING"],
    ["COMMUNICATIONS // GMAIL TERMINAL", "COMUNICACIONES // TERMINAL GMAIL", "COMMUNICATIONS // GMAIL TERMINAL"],
    ["COMMUNICATION // LECTURE", "COMUNICACIÓN // LECTURA", "COMMUNICATION // READING"],
    ["EXPÉDITEUR :", "REMITENTE:", "SENDER:"],
    ["DATE :", "FECHA:", "DATE:"],
    ["OBJET :", "ASUNTO:", "SUBJECT:"],
    ["DESTINATAIRE :", "DESTINATARIO:", "TO:"],
    ["MESSAGE :", "MENSAJE:", "MESSAGE:"],
    ["🚀 ENVOYER LE MESSAGE", "🚀 ENVIAR EL MENSAJE", "🚀 SEND MESSAGE"],
    ["↩️ RÉPONDRE", "↩️ RESPONDER", "↩️ REPLY"],
    ["🗑️ SUPPRIMER", "🗑️ ELIMINAR", "🗑️ DELETE"],
    ["🔊 RELIRE", "🔊 RELEER", "🔊 READ ALOUD"],
    ["0 NON LUS", "0 SIN LEER", "0 UNREAD"],
    ["TOUS (", "TODOS (", "ALL ("],
    ["NON LUS (", "SIN LEER (", "UNREAD ("],
    ["RESTAURANTS PROCHES", "RESTAURANTES CERCANOS", "NEARBY RESTAURANTS"],
    ["🍽️ RESTAURANTS & LIEUX", "🍽️ RESTAURANTES Y LUGARES", "🍽️ RESTAURANTS & PLACES"],
    ["SYSTÈME DE NAVIGATION", "SISTEMA DE NAVEGACIÓN", "NAVIGATION SYSTEM"],
    ["GESTURE", "GESTO", "GESTURE"],
    ["HANDS", "MANOS", "HANDS"],
    ["OUTILS SYSTEME", "HERRAMIENTAS DEL SISTEMA", "SYSTEM TOOLS"],
    ["LISTE COMMANDES", "LISTA DE COMANDOS", "COMMAND LIST"],
    ["RECHERCHER UNE COMMANDE...", "BUSCAR UN COMANDO…", "SEARCH A COMMAND..."],
    ["RECHERCHER UN APPAREIL...", "BUSCAR UN DISPOSITIVO…", "SEARCH A DEVICE..."],
    ["NAVIGATEUR SÉCURISÉ", "NAVEGADOR SEGURO", "SECURE BROWSER"],
    ["CLAVIER VISUEL", "TECLADO EN PANTALLA", "ON-SCREEN KEYBOARD"],
    ["MISES À JOUR LOGICIELS DISPONIBLES", "ACTUALIZACIONES DISPONIBLES", "SOFTWARE UPDATES AVAILABLE"],
    ["RECHERCHE DES MISES À JOUR...", "BUSCANDO ACTUALIZACIONES…", "SEARCHING FOR UPDATES..."],
    ["CONSOLE DE MISE À JOUR SYSTEME", "CONSOLA DE ACTUALIZACIÓN", "SYSTEM UPDATE CONSOLE"],
    ["FERMER LA CONSOLE", "CERRAR LA CONSOLA", "CLOSE CONSOLE"],
    ["DÉSINSTALLATEUR", "DESINSTALADOR", "UNINSTALLER"],
    ["🗑️ DÉSINSTALLER", "🗑️ DESINSTALAR", "🗑️ UNINSTALL"],
    ["CHARGEMENT DE LA LISTE DES LOGICIELS...", "CARGANDO LISTA DE PROGRAMAS…", "LOADING SOFTWARE LIST..."],
    ["CLIENT VPN", "CLIENTE VPN", "VPN CLIENT"],
    ["SE CONNECTER", "CONECTARSE", "CONNECT"],
    ["SE DÉCONNECTER", "DESCONECTARSE", "DISCONNECT"],
    ["DÉCONNECTÉ", "DESCONECTADO", "DISCONNECTED"],
    ["← RETOUR", "← VOLVER", "← BACK"],
    ["ACTIVER LA VISION", "ACTIVAR LA VISIÓN", "ENABLE VISION"],
    ["CHARGEMENT...", "CARGANDO…", "LOADING..."],
    ["COMPRIS", "ENTENDIDO", "GOT IT"],
    ["AUTRES", "OTROS", "OTHERS"],
    ["SCI-FI", "SCI-FI", "SCI-FI"],
    ["PAR DÉFAUT", "POR DEFECTO", "DEFAULT"],
    ["Fond épuré d'origine", "Fondo original limpio", "Original clean background"],
    ["Fond de mon Bureau", "Fondo de mi escritorio", "My desktop background"],
    ["Passerelle Orbitale", "Pasarela orbital", "Orbital gateway"],
    ["Circuit énergétique haute tension", "Circuito energético de alto voltaje", "High-voltage energy circuit"],
    ["Sanctuaire ANNEAUX", "Santuario ANILLOS", "RINGS sanctuary"],
    ["Orbites cyan et anneaux lumineux", "Órbitas cian y anillos luminosos", "Cyan orbits and glowing rings"],
    ["ANNEAUX", "ANILLOS", "RINGS"],
    ["Modèle 6 (Anneaux animés)", "Modelo 6 (anillos animados)", "Model 6 (animated rings)"],
    ["Modèle 6 — ANNEAUX", "Modelo 6 — ANILLOS", "Model 6 — RINGS"],
    ["Modèle 12 (HELION — Système astral doré)", "Modelo 12 (HELION — sistema astral dorado)", "Model 12 (HELION — golden astral system)"],
    ["GLOBE 3D", "GLOBO 3D", "3D GLOBE"],
    ["GLOBE TERRESTRE", "GLOBO TERRESTRE", "EARTH GLOBE"],
    ["HOLOGRAMME", "HOLOGRAMA", "HOLOGRAM"],

    // Ayuda: frases de comando
    ["Affiche le menu d'aide", "Muestra el menú de ayuda", "Shows the help menu"],
    ["Quelle heure est-il ?", "¿Qué hora es?", "What time is it?"],
    ["Né en [année], quel âge j'ai ?", "Nací en [año], ¿qué edad tengo?", "Born in [year], how old am I?"],
    ["Calcul d'âge", "Cálculo de edad", "Age calculation"],
    ["Mot de passe sécurisé", "Contraseña segura", "Secure password"],
    ["Quelle heure est-il à Tokyo / New York...", "¿Qué hora es en Tokio / Nueva York…?", "What time is it in Tokyo / New York..."],
    ["Rappelle-moi dans [X] heures", "Recuérdame en [X] horas", "Remind me in [X] hours"],
    ["État des minuteries", "Estado de temporizadores", "Timer status"],
    ["Ajoute [article] à ma liste de courses", "Añade [artículo] a mi lista de compras", "Add [item] to my shopping list"],
    ["Liste de courses", "Lista de compras", "Shopping list"],
    ["Qu'est-ce que j'ai sur ma liste de courses ?", "¿Qué tengo en mi lista de compras?", "What's on my shopping list?"],
    ["Affiche la liste de courses", "Muestra la lista de compras", "Show the shopping list"],
    ["Vide la liste de courses", "Vacía la lista de compras", "Clear the shopping list"],
    ["✨ CRÉATION IA (SITES, IMAGES, PROMPTS, MUSIQUE)", "✨ CREACIÓN CON IA (SITIOS, IMÁGENES, PROMPTS, MÚSICA)", "✨ AI CREATION (SITES, IMAGES, PROMPTS, MUSIC)"],
    ["🌤️ MÉTÉO & DOMOTIQUE (Home Assistant)", "🌤️ CLIMA Y DOMÓTICA (Home Assistant)", "🌤️ WEATHER & HOME AUTOMATION"],
    ["Météo à [ville]", "Clima en [ciudad]", "Weather in [city]"],
    ["Température dans le salon / bureau", "Temperatura en la sala / escritorio", "Temperature in the living room / office"],
    ["Quel est l'état du salon ?", "¿Cómo está la sala?", "What's the state of the living room?"],
    ["Statut entité HA", "Estado de entidad HA", "HA entity status"],
    ["Ouvre les paramètres", "Abre los ajustes", "Open settings"],
    ["Mode boulot / Au boulot", "Modo trabajo / Al trabajo", "Work mode / To work"],
    ["Ouvre mes téléchargements", "Abre mis descargas", "Open my downloads"],
    ["Dossier Téléchargements", "Carpeta de descargas", "Downloads folder"],
    ["Où est [ville] ?", "¿Dónde está [ciudad]?", "Where is [city]?"],
    ["👁️ VISION & ANALYSE D'ÉCRAN", "👁️ VISIÓN Y ANÁLISIS DE PANTALLA", "👁️ VISION & SCREEN ANALYSIS"],
    ["Trouve-moi un restaurant", "Buscame un restaurante", "Find me a restaurant"],
    ["Lance un scan antivirus", "Inicia un análisis de antivirus", "Run an antivirus scan"],
    ["Interface complète de scan", "Interfaz completa de análisis", "Full scanning interface"],
    ["Rafraîchir les états", "Actualizar estados", "Refresh states"],
    ["Fermer le navigateur", "Cerrar el navegador", "Close the browser"],
    ["Fermer la caméra", "Cerrar la cámara", "Close the camera"],
    ["CORT, LANCE [NOM DU JEU]", "CORT, inicia [NOMBRE DEL JUEGO]", "CORT, launch [GAME NAME]"],
    ["Voix : « CORT, LANCE [NOM DU JEU] »", "Voz: «CORT, inicia [NOMBRE DEL JUEGO]»", "Voice: “CORT, launch [GAME NAME]”"],

    // Modal de primer arranque (lo primero que se ve al abrir)
    ["GRACIAS POR INSTALAR CORT", "GRACIAS POR INSTALAR CORT", "THANK YOU FOR INSTALLING CORT"],
    ["CORT est un projet personnel ambitieux, conçu pour repousser les limites de l'assistance virtuelle sur ordinateur.", "CORT es un proyecto personal ambicioso, diseñado para empujar los límites de la asistencia virtual en el ordenador.", "CORT is an ambitious personal project built to push the limits of desktop virtual assistance."],
    ["Ce projet est 100% open-source et entièrement gratuit.", "Este proyecto es 100% de código abierto y totalmente gratuito.", "This project is 100% open-source and completely free."],
    ["⚠ AVERTISSEMENT LÉGAL", "⚠ AVISO LEGAL", "⚠ LEGAL NOTICE"],
    ["Ce logiciel ne peut en aucun cas être vendu ou monétisé de quelque manière que ce soit.",
     "No se puede vender ni monetizar sin atribuir la autoría a Askher Vargas y Sandra Lopez ni sin escribir a los correos de soporte.",
     "It may not be sold or monetized without crediting Askher Vargas and Sandra Lopez, or without writing to the support emails first."],
    ["Pour plus d'informations, des tutoriels ou pour soutenir le projet, visitez le site officiel.",
     "Para más información, tutoriales o para apoyar el proyecto, escribe a los correos de soporte o visita el repositorio.",
     "For more information, tutorials or to support the project, write to the support emails or visit the repository."],
    ["SITE OFFICIEL", "SOPORTE Y PERMISOS", "SUPPORT AND PERMISSIONS"],
    ["J'AI COMPRIS", "ENTENDIDO", "GOT IT"],
    ["Soporte y permisos: Sandrasofialopezgomez3@gmail.com · Carlosa3325@gmail.com",
     "Soporte y permisos: Sandrasofialopezgomez3@gmail.com · Carlosa3325@gmail.com",
     "Support and permissions: Sandrasofialopezgomez3@gmail.com · Carlosa3325@gmail.com"],

    // Teclado en pantalla
    ["ENTREZ VOTRE COMMANDE ICI...", "ESCRIBE TU COMANDO AQUÍ…", "ENTER YOUR COMMAND HERE..."],
    ["DIRECT_INPUT_OVERRIDE", "ENTRADA_DIRECTA", "DIRECT_INPUT_OVERRIDE"],
    ["AWAITING_COMMAND...", "ESPERANDO COMANDO…", "AWAITING COMMAND..."],

    // Panel de seguridad y consola
    ["[INFO] Sous-système antivirus CORT actif. En attente d'instruction.", "[INFO] Subsistema de antivirus de CORT activo. Esperando orden.", "[INFO] CORT antivirus subsystem active. Awaiting instruction."],
    ["Diagnostic matériel en cours...", "Diagnóstico de hardware en curso…", "Hardware diagnostic in progress..."],
    ["◈ TOUS SYSTÈMES OPÉRATIONNELS ◈", "◈ TODOS LOS SISTEMAS OPERATIVOS ◈", " ALL SYSTEMS OPERATIONAL ◈"],
    ["PROT. TEMPS RÉEL : OFF", "PROT. TIEMPO REAL: OFF", "REALTIME PROT: OFF"],
    ["TRACES RÉSIDUELLES DÉTECTÉES", "RASTROS RESIDUALES DETECTADOS", "LEFTOVER TRACES DETECTED"],
    ["TOUT SÉLECTIONNER", "SELECCIONAR TODO", "SELECT ALL"],
    ["En attente de la désinstallation...", "Esperando la desinstalación…", "Awaiting uninstallation..."],
    ["Suppression de l'arrière-plan...", "Eliminando el fondo…", "Removing background..."],
    ["Réparation géométrique pour l'impression...", "Reparando geometría para imprimir…", "Repairing geometry for printing..."],
    ["Fichier STL prêt", "Archivo STL listo", "STL file ready"],
    ["Préparation...", "Preparando…", "Preparing..."],
    ["Préparation de l'installation...", "Preparando la instalación…", "Preparing installation..."],
    ["INSTALLATION TERMINÉE AVEC SUCCÈS !", "¡INSTALACIÓN TERMINADA CON ÉXITO!", "INSTALLATION COMPLETED SUCCESSFULLY!"],
    ["pour que les nouveaux composants 3D soient chargés.", "para que se carguen los nuevos componentes 3D.", "so the new 3D components load."],
    ["Certaines dépendances sont manquantes. Cliquez ci-dessous pour installer automatiquement les composants nécessaires.", "Faltan algunas dependencias. Haz clic abajo para instalar automáticamente los componentes necesarios.", "Some dependencies are missing. Click below to install the needed components automatically."],
    ["MODÈLE 3D (IA)", "MODELO 3D (IA)", "3D MODEL (AI)"],
    ["QUALITÉ DU MODÈLE 3D", "CALIDAD DEL MODELO 3D", "3D MODEL QUALITY"],
    ["💎 Haute précision", "💎 Alta precisión", "💎 High precision"],
    ["FORME DE LA LITHOPHANIE", "FORMA DE LA LITOFANÍA", "LITHOPHANE SHAPE"],
    ["🌙 Courbé (Arc pour veilleuse)", "🌙 Curvado (arco para lámpara nocturna)", "🌙 Curved (nightlight arc)"],
    ["Cadre rigide renforcé (bordure solide)", "Marco rígido reforzado (borde sólido)", "Reinforced rigid frame (solid border)"],
    ["Socle d'exposition intégré (tient debout sur meuble)", "Base de exhibición integrada (se sostiene sola)", "Integrated display stand (self-standing)"],
    ["LARGEUR PHYSIQUE", "ANCHO FÍSICO", "PHYSICAL WIDTH"],
    ["GÉNÉRER LE FICHIER 3D (STL)", "GENERAR EL ARCHIVO 3D (STL)", "GENERATE 3D FILE (STL)"],
    ["Glissez-déposez une image ou photo ici", "Arrastra y suelta una imagen o foto aquí", "Drag and drop an image or photo here"],
    ["ou cliquez pour sélectionner (.png, .jpg, .webp)", "o haz clic para seleccionar (.png, .jpg, .webp)", "or click to select (.png, .jpg, .webp)"],
    ["🔄 REDÉMARRER", "🔄 REINICIAR", "🔄 RESTART"],
    ["🛑 ÉTEINDRE", "🛑 APAGAR", "🛑 SHUTDOWN"],
    ["ÉTAT: HORS LIGNE", "ESTADO: SIN LÍNEA", "STATE: OFFLINE"],
    ["📁 DOSSIER PARTAGÉ", "📁 CARPETA COMPARTIDA", "📁 SHARED FOLDER"],
    ["📦 INSTALL. PERSO.", "📦 INSTALACIÓN A MEDIDA", "📦 CUSTOM INSTALL"],
    ["Le système sera téléchargé en temps réel et accessible instantanément via cette interface.", "El sistema se descargará en tiempo real y estará disponible al instante desde esta interfaz.", "The system will download in real time and be available instantly through this interface."],
    ["Prêt à initialiser le sous-système. Le téléchargement peut prendre quelques minutes selon votre connexion.", "Listo para iniciar el subsistema. La descarga puede tardar unos minutos según tu conexión.", "Ready to start the subsystem. Download may take a few minutes depending on your connection."],
    ["Téléchargement en cours...", "Descarga en curso…", "Downloading..."],
    ["Médias", "Medios", "Media"],
    ["Développement", "Desarrollo", "Development"],
    ["Appairage téléphone", "Emparejar teléfono", "Phone pairing"],
    ["METTRE À JOUR LA SÉLECTION", "ACTUALIZAR LA SELECCIÓN", "UPDATE SELECTION"],
    ["TOUT METTRE À JOUR", "ACTUALIZAR TODO", "UPDATE ALL"],
    ["TON / PERSONNALITÉ", "TON / PERSONALIDAD", "TONE / PERSONALITY"],

    // Ayuda: comandos generales
    ["💬 COMMANDES GÉNÉRALES & IDENTITÉ", "💬 COMANDOS GENERALES E IDENTIDAD", "💬 GENERAL COMMANDS & IDENTITY"],
    ["Qui t'a créé ?", "¿Quién te creó?", "Who created you?"],
    ["CORT es de Askher Vargas y Sandra Lopez", "CORT es de Askher Vargas y Sandra Lopez",
     "CORT belongs to Askher Vargas and Sandra Lopez"],
    ["Blague aléatoire", "Chiste aleatorio", "Random joke"],
    ["Calcul mathématique", "Cálculo matemático", "Math calculation"],
    ["Combien de jours avant Noël ?", "¿Cuántos días faltan para Navidad?", "How many days until Christmas?"],
    ["Compte à rebours Noël", "Cuenta atrás de Navidad", "Christmas countdown"],
    ["Lance une pièce virtuelle", "Lanza una moneda virtual", "Flip a virtual coin"],
    ["Lance un dé à [N] faces", "Lanza un dado de [N] caras", "Roll a [N]-sided die"],
    ["Dé virtuel", "Dado virtual", "Virtual die"],
    ["Génère un nombre entre [X] et [Y]", "Genera un número entre [X] e [Y]", "Generate a number between [X] and [Y]"],
    ["Nombre aléatoire", "Número aleatorio", "Random number"],
    ["Génère un mot de passe de [N] caractères", "Genera una contraseña de [N] caracteres", "Generate a [N]-character password"],
    ["Épelle [mot] en alphabet phonétique", "Deletrea [palabra] en alfabeto fonético", "Spell [word] phonetically"],
    ["Comment s'écrit le mot [mot] ?", "¿Cómo se escribe la palabra [palabra]?", "How do you spell the word [word]?"],
    ["Épelle le mot et l'affiche sur la sphère", "Deletrea la palabra y la muestra en la esfera", "Spells the word and shows it on the sphere"],
    ["Alarme différée", "Alarma pospuesta", "Snoozed alarm"],
    ["Rappel vocal programmé", "Recordatorio vocal programado", "Scheduled voice reminder"],
    ["Coordonnées GPS", "Coordenadas GPS", "GPS coordinates"],
    ["Téléphone", "Teléfono", "Phone"],
    ["Spécialité / Avis", "Especialidad / Opiniones", "Cuisine / Reviews"],
    ["Recherche et lance sur Spotify", "Busca y reproduce en Spotify", "Search and play on Spotify"],
    ["Recherche Spotify par genre", "Búsqueda por género en Spotify", "Spotify search by genre"],
    ["Recherche et lance en plein écran 🔑", "Busca y reproduce a pantalla completa 🔑", "Search and play fullscreen 🔑"],
    ["Recherche YouTube + plein écran 🔑", "Búsqueda en YouTube + pantalla completa 🔑", "YouTube search + fullscreen 🔑"],
    ["Recherche multi-résultats 🔑", "Búsqueda multirresultado 🔑", "Multi-result search 🔑"],
    ["Résumé IA via sous-titres 🔑", "Resumen con IA vía subtítulos 🔑", "AI summary via subtitles 🔑"],
    ["Volume système Windows", "Volumen del sistema", "System volume"],
    ["Survole [ville] / Affiche [ville]", "Pasa sobre [ciudad] / Muestra [ciudad]", "Hover [city] / Show [city]"],
    ["Route entre 2 villes sur le globe", "Ruta entre 2 ciudades en el globo", "Route between 2 cities on the globe"],
    ["Saisie automatique guidée par vision", "Autocompletado guiado por visión", "Vision-guided autofill"],
    ["Restaurants proches via GPS", "Restaurantes cercanos por GPS", "Nearby restaurants via GPS"],
    ["Restaurant [cuisine] près de moi", "Restaurante de [cocina] cerca de mí", "[cuisine] restaurant near me"],
    ["Pizzeria / sushi à côté", "Pizzería / sushi aquí al lado", "Pizzeria / sushi nearby"],
    ["Recherche de proximité", "Búsqueda de proximidad", "Proximity search"],
    ["Recherche mon document Docs [titre]", "Busca mi documento de Docs [título]", "Find my Docs file [title]"],
    ["Recherche dans Google Drive", "Búsqueda en Google Drive", "Google Drive search"],
    ["Convertit et télécharge en PDF", "Convierte y descarga en PDF", "Converts and downloads as PDF"],
    ["Partage les droits d'accès", "Comparte los permisos de acceso", "Shares access rights"],
    ["Via le panel Obsidian dans l'interface", "Desde el panel Obsidian de la interfaz", "Via the Obsidian panel in the interface"],
    ["Via le bouton LECTEUR VIDÉO / IPTV dans le menu", "Desde el botón REPRODUCTOR DE VÍDEO / IPTV del menú", "Via the VIDEO / IPTV PLAYER button in the menu"],
    ["Via le bouton ANTIVIRUS dans le menu", "Desde el botón ANTIVIRUS del menú", "Via the ANTIVIRUS button in the menu"],
    ["Via le panel Obsidian dans l'interface", "Desde el panel Obsidian de la interfaz", "Via the Obsidian panel in the interface"],
    ["— la reconnaissance vocale par microphone est désactivée.", "— el reconocimiento por micrófono está desactivado.", "— microphone speech recognition is disabled."],
    ["Autoriser les applications à accéder à votre microphone", "Permitir a las aplicaciones acceder a tu micrófono", "Allow apps to access your microphone"],
    ["Comment activer la lecture de vos emails sur CORT ?", "¿Cómo activar la lectura de tus correos en CORT?", "How to enable email reading in CORT?"],
    ["Étape 3 : Activer l'API Gmail sur votre projet", "Paso 3: activar la API de Gmail en tu proyecto", "Step 3: enable the Gmail API on your project"],
    ["« ACTIVER »", "«ACTIVAR»", "“ENABLE”"],
    ["Cedar — posée et profonde", "Cedar — serena y profunda", "Cedar — calm and deep"],
    ["🔷 Phi-3.5 Mini — Microsoft", "🔷 Phi-3.5 Mini — Microsoft", "🔷 Phi-3.5 Mini — Microsoft"],
    ["NVIDIA Canary-1B", "NVIDIA Canary-1B", "NVIDIA Canary-1B"],
    ["INSTALLER PIPER (RAPIDE)", "INSTALAR PIPER (RÁPIDO)", "INSTALL PIPER (FAST)"],
    ["INSTALLER CHATTERBOX (QUALITÉ)", "INSTALAR CHATTERBOX (CALIDAD)", "INSTALL CHATTERBOX (QUALITY)"],
    ["Téléchargement du modèle vocal Kokoro (~300 Mo)...", "Descargando el modelo de voz Kokoro (~300 MB)…", "Downloading Kokoro voice model (~300 MB)..."],
    ["-- Détecter vos applications installées --", "-- Detectar tus aplicaciones instaladas --", "-- Detect your installed applications --"],
    ["Puck ✨ (M) — Dynamique & Énergique (Live 3.8)", "Puck ✨ (M) — dinámico y enérgico (Live 3.8)", "Puck ✨ (M) — dynamic & energetic (Live 3.8)"],
    ["Puck (M) — Énergique", "Puck (M) — enérgico", "Puck (M) — energetic"],
    ["🚀 Gilles (M) — Français, PC modeste", "🚀 Gilles (M) — francés, equipo modesto", "🚀 Gilles (M) — French, modest PC"],
    ["🚀 Tom (M) — Français, qualité moyenne", "🚀 Tom (M) — francés, calidad media", "🚀 Tom (M) — French, medium quality"],
    ["Modèle 3D (IA)", "Modelo 3D (IA)", "3D Model (AI)"],
    ["RECHERCHER UN PROGRAMME...", "BUSCAR UN PROGRAMA…", "SEARCH A PROGRAM..."],
    ["Désinstaller et supprimer les fichiers", "Desinstalar y borrar los archivos", "Uninstall and delete files"],
    ["🔍 Rechercher une application...", "🔍 Buscar una aplicación…", "🔍 Search an application..."],
    ["RECHERCHER UN LOGICIEL À METTRE À JOUR...", "BUSCAR UN PROGRAMA A ACTUALIZAR…", "SEARCH SOFTWARE TO UPDATE..."],
    ["Emails Gmail — Cliquez pour ouvrir la boîte de réception", "Correos Gmail — clic para abrir la bandeja", "Gmail emails — click to open inbox"],
    ["Activer le mode écoute permanente — CORT écoute tout sans mot-clé", "Activar escucha permanente — CORT oye todo sin palabra clave", "Enable always-listening — CORT hears everything without a wake word"],
    ["Effacer la recherche", "Borrar la búsqueda", "Clear search"],
    ["Rechercher une note...", "Buscar una nota…", "Search a note..."],
    ["Réafficher tous les jeux retirés", "Volver a mostrar los juegos retirados", "Restore all hidden games"],
    ["⟲ RÉAFFICHER LES RETIRÉS", "⟲ MOSTRAR LOS RETIRADOS", "⟲ RESTORE HIDDEN"],
    ["↶ RÉAFFICHER LES RETIRÉS", "↶ MOSTRAR LOS RETIRADOS", "↶ RESTORE HIDDEN"],
    ["📥 CHARGER 25 EMAILS SUPPLÉMENTAIRES", "📥 CARGAR 25 CORREOS MÁS", "📥 LOAD 25 MORE EMAILS"],
    ["+ AJOUTER UN DOSSIER", "+ AÑADIR UNA CARPETA", "+ ADD A FOLDER"],
    ["＋ AJOUTER UN DOSSIER", "＋ AÑADIR UNA CARPETA", "＋ ADD A FOLDER"],
    ["＋ AJOUTER UN PROGRAMME", "＋ AÑADIR UN PROGRAMA", "＋ ADD A PROGRAM"],
    ["SERVEUR : AUCUN", "SERVIDOR: NINGUNO", "SERVER: NONE"],
    ["VPN GATE + MIROIRS OFFICIELS", "PUERTA VPN + ESPEJOS OFICIALES", "VPN GATE + OFFICIAL MIRRORS"],
    ["CHOISIR UN PAYS :", "ELEGIR UN PAÍS:", "CHOOSE A COUNTRY:"],
    ["Chargement des pays...", "Cargando países…", "Loading countries..."],
    ["CORT // SECURE_VPN", "CORT // VPN_SEGURA", "CORT // SECURE_VPN"],
    ["CORT // SHOPPING_LIST", "CORT // LISTA_COMPRAS", "CORT // SHOPPING_LIST"],
    ["CORT // RESTAURANT_RADAR", "CORT // RADAR_DE_RESTAURANTES", "CORT // RESTAURANT_RADAR"],
    ["CORT // SOFTWARE_UNINSTALLER", "CORT // DESINSTALADOR", "CORT // SOFTWARE_UNINSTALLER"],
    ["Nom du restaurant", "Nombre del restaurante", "Restaurant name"],
    ["SYNC ACTIVE", "SINCRONIZACIÓN ACTIVA", "SYNC ACTIVE"],
    ["GMAIL_SYNC: ACTIVE", "GMAIL_SYNC: ACTIVA", "GMAIL_SYNC: ACTIVE"],
    ["CORT_HUD_UNINSTALLER_v0", "CORT_HUD_DESINSTALADOR_v0", "CORT_HUD_UNINSTALLER_v0"],
    ["CORT_HUD_SHOP_v0", "CORT_HUD_COMPRAS_v0", "CORT_HUD_SHOP_v0"],
    ["CORT_HUD_VPN_v0", "CORT_HUD_VPN_v0", "CORT_HUD_VPN_v0"],
    ["CORT_HUD_SEC_v0", "CORT_HUD_SEC_v0", "CORT_HUD_SEC_v0"],
    ["CORT_COMM_v0", "CORT_COMUN_v0", "CORT_COMM_v0"],
    ["CORT_READER_v0", "CORT_LECTOR_v0", "CORT_READER_v0"],
    ["CORT OS // INSTALLATION", "CORT OS // INSTALACIÓN", "CORT OS // INSTALLATION"],
    ["CORT OS // APP STORE", "CORT OS // TIENDA DE APPS", "CORT OS // APP STORE"],
    ["CORT OS // SUBSYSTEM", "CORT OS // SUBSISTEMA", "CORT OS // SUBSYSTEM"],
    ["PyAudio non installé", "PyAudio no instalado", "PyAudio not installed"],
    ["install.bat", "instalador de Linux: apt", "install.bat"],
    ["par le système.", "por el sistema.", "by the system."]
  ];

  // ---- 2a-bis. Diccionario extendido (pasada V0) ---------------------------
  // Capturado con window.CORT.estado() sobre el DOM real de la demo, grupo por
  // grupo: panel de comandos de voz, domótica, control del PC, webcams,
  // micrófono, modelos del orbe, voces, antivirus, Ollama, personalización.
  const D_EXT = [
    // 📝 Notas, compras y tareas
    ["📝 NOTES, COURSES & TÂCHES", "📝 NOTAS, COMPRAS Y TAREAS", "📝 NOTES, SHOPPING & TASKS"],
    ["Retiens ça / Mémorise ça", "Recuerda esto / Memoriza esto", "Remember this / Memorize this"],
    ["Affiche les 5 dernières notes", "Muestra las 5 últimas notas", "Shows the last 5 notes"],
    ["Ajoute une tâche : [texte]", "Añade una tarea: [texto]", "Add a task: [text]"],
    ["Mes tâches / Ma to-do", "Mis tareas / Mi lista de pendientes", "My tasks / My to-do list"],
    ["Affiche les tâches en cours", "Muestra las tareas en curso", "Shows current tasks"],
    ["Efface mes tâches", "Borra mis tareas", "Clear my tasks"],
    ["Crée un site internet...", "Crea un sitio web...", "Create a website..."],
    ["Génère un site web fonctionnel", "Genera un sitio web funcional", "Generates a working website"],
    ["Crée un prompt...", "Crea un prompt...", "Create a prompt..."],
    ["Génère un prompt IA ultra-détaillé", "Genera un prompt de IA ultradetallado", "Generates an ultra-detailed AI prompt"],
    ["Crée une image...", "Crea una imagen...", "Create an image..."],
    ["Génère une image via l'IA", "Genera una imagen por IA", "Generates an image via AI"],
    ["Génère une musique / Chante", "Genera una música / Canta", "Generate music / Sing"],
    ["Crée une musique par genre", "Crea una música por género", "Creates music by genre"],
    ["Génère une vidéo...", "Genera un vídeo...", "Generate a video..."],
    ["Crée une courte vidéo via IA", "Crea un vídeo corto por IA", "Creates a short AI video"],

    // ▶️ Música y vídeos
    ["▶️ MUSIQUE & VIDÉOS — YOUTUBE", "▶️ MÚSICA Y VÍDEOS — YOUTUBE", "▶️ MUSIC & VIDEOS — YOUTUBE"],
    ["Lance ta playlist Spotify configurée", "Inicia tu playlist de Spotify configurada", "Starts your configured Spotify playlist"],
    ["Ta playlist personnalisée", "Tu playlist personalizada", "Your custom playlist"],
    ["Chanson précédente", "Canción anterior", "Previous song"],
    ["Titre précédent", "Título anterior", "Previous track"],
    ["Lance ton URL YouTube configurée", "Inicia tu URL de YouTube configurada", "Starts your configured YouTube URL"],
    ["Cherche des vidéos de [sujet]", "Busca vídeos de [tema]", "Search videos about [topic]"],
    ["5 résultats YouTube listés 🔑", "5 resultados de YouTube listados 🔑", "5 YouTube results listed 🔑"],
    ["Montre-moi des vidéos de [artiste]", "Muéstrame vídeos de [artista]", "Show me videos by [artist]"],
    ["Top 5 vidéos en France 🔑", "Top 5 vídeos en Francia 🔑", "Top 5 videos in France 🔑"],
    ["Tendances par catégorie 🔑", "Tendencias por categoría 🔑", "Trends by category 🔑"],
    ["Combien d'abonnés a [chaîne] ?", "¿Cuántos suscriptores tiene [canal]?", "How many subscribers does [channel] have?"],
    ["Stats chaîne YouTube 🔑", "Estadísticas del canal de YouTube 🔑", "YouTube channel stats 🔑"],
    ["Infos sur la chaîne [chaîne]", "Información del canal [canal]", "Info on channel [channel]"],
    ["Abonnés, vidéos, vues 🔑", "Suscriptores, vídeos, vistas 🔑", "Subscribers, videos, views 🔑"],
    ["Dernières vidéos de [chaîne]", "Últimos vídeos de [canal]", "Latest videos from [channel]"],
    ["3 dernières publications 🔑", "3 últimas publicaciones 🔑", "3 latest posts 🔑"],
    ["Résume-moi cette vidéo [URL]", "Resúmeme este vídeo [URL]", "Summarize this video [URL]"],
    ["Infos sur la vidéo [URL]", "Información del vídeo [URL]", "Info on the video [URL]"],
    ["Vues, likes, durée, chaîne 🔑", "Vistas, me gusta, duración, canal 🔑", "Views, likes, duration, channel 🔑"],

    // 🌤 Clima y domótica
    ["Météo locale (HA + OpenMeteo)", "Clima local (HA + OpenMeteo)", "Local weather (HA + OpenMeteo)"],
    ["Météo d'une ville précise", "Clima de una ciudad concreta", "Weather of a specific city"],
    ["Prévisions pluie", "Pronóstico de lluvia", "Rain forecast"],
    ["Alertes météo", "Alertas meteorológicas", "Weather alerts"],
    ["Capteurs HA intérieurs", "Sensores HA interiores", "Indoor HA sensors"],
    ["Allume la lumière du salon", "Enciende la luz del salón", "Turn on the living room light"],
    ["Contrôle des lumières HA", "Control de luces HA", "HA light control"],
    ["Éteins la lumière de la chambre", "Apaga la luz de la habitación", "Turn off the bedroom light"],
    ["Extinction lumières HA", "Apagado de luces HA", "HA lights off"],
    ["Mets la lumière du salon à 50%", "Pon la luz del salón al 50%", "Set the living room light to 50%"],
    ["Luminosité HA (0-100%)", "Brillo HA (0-100%)", "HA brightness (0-100%)"],
    ["Contrôle des prises HA", "Control de enchufes HA", "HA smart plug control"],
    ["Règle le chauffage à [N] degrés", "Ajusta la calefacción a [N] grados", "Set heating to [N] degrees"],
    ["Lumière Salon", "Luz del salón", "Living Room Light"],

    // 💻 Aplicaciones y control del PC
    ["💻 APPLICATIONS & CONTRÔLE PC", "💻 APLICACIONES Y CONTROL DEL PC", "💻 APPS & PC CONTROL"],
    ["Éditeur de texte", "Editor de texto", "Text editor"],
    ["Ouvre le gestionnaire de tâches", "Abre el administrador de tareas", "Open task manager"],
    ["Paramètres Windows", "Configuración de Windows", "Windows settings"],
    ["Ouvre la capture d'écran / Snipping Tool", "Abre la captura de pantalla / Snipping Tool", "Open Snipping Tool"],
    ["Volume à [N]% / Monte le volume", "Volumen al [N]% / Sube el volumen", "Volume to [N]% / Turn up volume"],
    ["Sourdine système", "Silencio del sistema", "System mute"],
    ["Luminosité à [N]%", "Brillo al [N]%", "Brightness to [N]%"],
    ["Luminosité de l'écran", "Brillo de la pantalla", "Screen brightness"],
    ["Prends une capture d'écran", "Toma una captura de pantalla", "Take a screenshot"],
    ["Éteins l'ordinateur", "Apaga el ordenador", "Shut down the computer"],
    ["Ouvre mes vidéos", "Abre mis vídeos", "Open my videos"],
    ["Dossier Vidéos", "Carpeta Vídeos", "Videos folder"],
    ["Mosaïque de tous les dossiers", "Mosaico de todas las carpetas", "Mosaic of all folders"],
    ["Dossier personnalisé", "Carpeta personalizada", "Custom folder"],
    ["Géolocalise l'utilisateur en direct", "Geolocaliza al usuario en directo", "Geolocates the user live"],
    ["Trace un itinéraire de [A] à [B]", "Traza una ruta de [A] a [B]", "Draw a route from [A] to [B]"],
    ["Analyse l'écran avec l'IA", "Analiza la pantalla con IA", "Analyzes the screen with AI"],
    ["Regarde mon écran", "Mira mi pantalla", "Look at my screen"],
    ["Clique sur [élément]", "Haz clic en [elemento]", "Click on [element]"],
    ["Fais une capture d'écran", "Haz una captura de pantalla", "Take a screenshot"],
    ["📸 Capture + analyse IA automatique de l'écran", "📸 Captura + análisis automático de pantalla con IA", "📸 Screenshot + automatic AI screen analysis"],

    // ⚽ Deportes
    ["⚽ SPORTS & RÉSULTATS", "⚽ DEPORTES Y RESULTADOS", "⚽ SPORTS & RESULTS"],
    ["Résultat du match de [équipe]", "Resultado del partido de [equipo]", "Result of [team]'s match"],
    ["Dernier résultat de foot", "Último resultado de fútbol", "Latest football result"],
    ["Prochain match de [équipe]", "Próximo partido de [equipo]", "Next match of [team]"],
    ["Prochain match planifié", "Próximo partido programado", "Upcoming match scheduled"],

    // 📄 Google Docs / Calendar / Markdown / IPTV
    ["Crée un Google Doc [titre]", "Crea un Google Doc [título]", "Create a Google Doc [title]"],
    ["Crée un document Docs [titre] avec [texte]", "Crea un documento de Docs [título] con [texto]", "Create a Docs document [title] with [text]"],
    ["Ajoute à mon document Docs : [texte]", "Añade a mi documento de Docs: [texto]", "Add to my Docs document: [text]"],
    ["Écris dans mon dernier Google Doc : [texte]", "Escribe en mi último Google Doc: [texto]", "Write in my latest Google Doc: [text]"],
    ["Complète le document en cours", "Completa el documento actual", "Completes the current document"],
    ["Crée une Google Sheet [titre]", "Crea una Google Sheet [título]", "Create a Google Sheet [title]"],
    ["Quels sont mes événements ?", "¿Cuáles son mis eventos?", "What are my events?"],
    ["Prochains événements Google Calendar", "Próximos eventos de Google Calendar", "Upcoming Google Calendar events"],
    ["Créer, lire, modifier, supprimer des notes Markdown", "Crear, leer, modificar y borrar notas Markdown", "Create, read, edit and delete Markdown notes"],
    ['Via le bouton "LECTEUR VIDÉO / IPTV" dans le menu', 'Mediante el botón "LECTOR DE VÍDEO / IPTV" del menú', 'Via the "VIDEO / IPTV PLAYER" button in the menu'],
    ["Lire des flux M3U, vidéos locales ou URL", "Lee flujos M3U, vídeos locales o URL", "Plays M3U streams, local videos or URLs"],
    ["🔑 = Nécessite la clé API YouTube | Commandes vocales ou via le clavier visuel (⌨️)", "🔑 = Requiere la clave API de YouTube | Comandos por voz o con el teclado visual (⌨️)", "🔑 = Requires a YouTube API key | Voice commands or the visual keyboard (⌨️)"],

    // 🎬 Webcams en vivo
    ["CLÉ WEBCAMS REQUISE", "CLAVE DE WEBCAMS REQUERIDA", "WEBCAM KEY REQUIRED"],
    ["🎬 VIDÉO LIVE", "🎬 VÍDEO EN VIVO", "🎬 LIVE VIDEO"],
    ["● STREAM LIVE • Rafraîchissement dans", "● STREAM EN VIVO • Actualización en", "● LIVE STREAM • Refreshing in"],
    ["⚠ CLÉ API WINDY WEBCAMS MANQUANTE", "⚠ FALTA LA CLAVE API DE WINDY WEBCAMS", "⚠ MISSING WINDY WEBCAM API KEY"],
    ["Créez un compte gratuit sur", "Crea una cuenta gratuita en", "Create a free account at"],
    ["Générez votre clé gratuite (Plan Free v3 — 10 000 requêtes/mois)", "Genera tu clave gratuita (Plan Free v3 — 10 000 solicitudes/mes)", "Generate your free key (Plan Free v3 — 10,000 requests/month)"],
    ["et collez votre clé :", "y pega tu clave:", "and paste your key:"],
    ["Une fois renseignée, le bouton deviendra vert et les flux s'afficheront en temps réel.", "Una vez introducida, el botón se pondrá verde y los flujos se mostrarán en tiempo real.", "Once entered, the button turns green and the streams appear in real time."],
    ["-- Détection automatique --", "-- Detección automática --", "-- Automatic detection --"],
    ["Requis pour récupérer et visionner les webcams publiques en direct partout dans le monde sur le Globe 3D.", "Requerido para obtener y ver webcams públicas en directo desde cualquier parte del mundo en el Globo 3D.", "Required to fetch and watch public live webcams worldwide on the 3D Globe."],

    // 📝 Notas y lista de la compra (paneles que re-renderiza el puente en F4)
    ["MODIFIÉ :", "MODIFICADO:", "MODIFIED:"],
    ["TAILLE :", "TAMAÑO:", "SIZE:"],
    ["Aucune note", "Ninguna nota", "No notes"],
    ["Date inconnue", "Fecha desconocida", "Unknown date"],

    // 🎤 Micrófono y sensibilidad
    ["Pour résoudre ce problème :", "Para resolver este problema:", "To fix this:"],
    ["Paramètres Windows -> Confidentialité -> Microphone", "Configuración de Windows -> Privacidad -> Micrófono", "Windows Settings -> Privacy -> Microphone"],
    ["3. Activez également", "3. Activa también", "3. Also enable"],
    ["Autoriser les applications de bureau à accéder à votre microphone", "Permitir a las aplicaciones de escritorio acceder a tu micrófono", "Allow desktop apps to access your microphone"],
    ["4. Vérifiez que votre microphone est bien connecté et configuré par défaut.", "4. Comprueba que el micrófono esté conectado y configurado como dispositivo predeterminado.", "4. Make sure your microphone is connected and set as default."],
    ["SENSIBILITÉ MICRO AUTOMATIQUE (RECOMMANDÉ)", "SENSIBILIDAD DE MICRÓFONO AUTOMÁTICA (RECOMENDADO)", "AUTOMATIC MIC SENSITIVITY (RECOMMENDED)"],
    ["SEUIL DE SENSIBILITÉ :", "UMBRAL DE SENSIBILIDAD:", "SENSITIVITY THRESHOLD:"],
    ["NOM D'ÉCOUTE (WAKE WORD)", "PALABRA DE ACTIVACIÓN (WAKE WORD)", "WAKE WORD"],
    ["MOT-CLÉ OU NOM VOCAL POUR CORT :", "PALABRA CLAVE O NOMBRE VOCAL PARA CORT:", "KEYWORD OR VOICE NAME FOR CORT:"],
    ["CORT, allume [mot-clé]", "CORT, enciende [palabra clave]", "CORT, turn on [keyword]"],
    ["CORT, éteins [mot-clé]", "CORT, apaga [palabra clave]", "CORT, turn off [keyword]"],
    ["Dites : \"CORT, allume la lumière de l'", "Di: \"CORT, enciende la luz de la'", 'Say: "CORT, turn on the light of the"'],
    ["Pour transcrire votre voix à 100% localement et avec une précision extrême, CORT a besoin d'installer le modèle", "Para transcribir tu voz 100% en local y con precisión extrema, CORT necesita instalar el modelo", "To transcribe your voice 100% locally with extreme accuracy, CORT needs to install the model"],

    // 🔮 Modelos del orbe
    ["Modèle 1 (Bleu Pastel)", "Modelo 1 (Azul pastel)", "Model 1 (Pastel Blue)"],
    ["Modèle 2 (Sable / Beige)", "Modelo 2 (Arena / Beige)", "Model 2 (Sand / Beige)"],
    ["Modèle 3 (Gris / Anthracite)", "Modelo 3 (Gris / Antracita)", "Model 3 (Grey / Anthracite)"],
    ["Modèle 4 (Rouge HUD / Iron Man)", "Modelo 4 (Rojo HUD / Iron Man)", "Model 4 (HUD Red / Iron Man)"],
    ["Modèle 5 (Vert NVIDIA)", "Modelo 5 (Verde NVIDIA)", "Model 5 (NVIDIA Green)"],
    ["Modèle 7 (NEXUS — Cœur holographique réactif)", "Modelo 7 (NEXUS — Núcleo holográfico reactivo)", "Model 7 (NEXUS — Reactive holographic core)"],
    ["Modèle 8 (AETHER — Singularité vivante)", "Modelo 8 (AETHER — Singularidad viva)", "Model 8 (AETHER — Living singularity)"],
    ["Modèle 9 (QUANTA — Sphère à cœur violet)", "Modelo 9 (QUANTA — Esfera de núcleo violeta)", "Model 9 (QUANTA — Violet-core sphere)"],
    ["Modèle 10 (FRACTURE — Cœur électrique)", "Modelo 10 (FRACTURE — Núcleo eléctrico)", "Model 10 (FRACTURE — Electric core)"],
    ["Modèle 11 (CHROMA — Plasma spectral)", "Modelo 11 (CHROMA — Plasma espectral)", "Model 11 (CHROMA — Spectral plasma)"],
    ["Modèle 13 (PULSE — Membrane photonique)", "Modelo 13 (PULSE — Membrana fotónica)", "Model 13 (PULSE — Photonic membrane)"],
    ["Modèle 14 (NOVA — Noyau cosmique)", "Modelo 14 (NOVA — Núcleo cósmico)", "Model 14 (NOVA — Cosmic core)"],
    ["Modèle 15 (SPECTRA — Chaos photonique)", "Modelo 15 (SPECTRA — Caos fotónico)", "Model 15 (SPECTRA — Photonic chaos)"],
    ["Modèle 16 (ECHO — Visage holographique)", "Modelo 16 (ECHO — Rosto holográfico)", "Model 16 (ECHO — Holographic face)"],
    ["Modèle 1 — Bleu Pastel", "Modelo 1 — Azul pastel", "Model 1 — Pastel Blue"],
    ["Modèle 2 — Sable / Beige", "Modelo 2 — Arena / Beige", "Model 2 — Sand / Beige"],
    ["Modèle 3 — Gris / Anthracite", "Modelo 3 — Gris / Antracita", "Model 3 — Grey / Anthracite"],
    ["Modèle 4 — Rouge HUD / Iron Man", "Modelo 4 — Rojo HUD / Iron Man", "Model 4 — HUD Red / Iron Man"],
    ["Modèle 5 — Vert NVIDIA", "Modelo 5 — Verde NVIDIA", "Model 5 — NVIDIA Green"],
    ["Modèle 12 — HELION", "Modelo 12 — HELION", "Model 12 — HELION"],
    ["Par défaut (Bleu CORT)", "Predeterminado (Azul CORT)", "Default (CORT Blue)"]
  ];


  // El DOM escribe los apóstrofos franceses como ’ (U+2019) y las comillas como
  // «…». Sin normalizar, una clave larga escrita con ' nunca coincide.
  const norm = s => s.replace(/[’ʼ]/g, "'").replace(/\s+/g, " ").trim();
  // El panel de ayuda escribe los comandos entre comillas («…» "…" '…'):
  // buscamos en el diccionario también la versión sin comillas.
  const C_GIRAS = /^[«"'\u2018\u2019\u201c\u201d]+/u, C_CIERRE = /[»"'\u2018\u2019\u201c\u201d]+$/u;
  function descomillar(s) {
    const a = (s.match(C_GIRAS) || [""])[0];
    const b = (s.match(C_CIERRE) || [""])[0];
    return { a, b, cuerpo: s.slice(a.length, s.length - b.length || undefined).trim() };
  }
  // ---- 2a-ter. Diccionario extendido 2 (voces, IA local, antivirus) --------
  const D_EXT2 = [
    // 🗣 Voces (los nombres propios se conservan; se traduce la descripción)
    ["Charon ✨ (M) — Posé & Informatif (Live 3.8)", "Charon ✨ (voz de hombre) — Sereno e informativo (Live 3.8)", "Charon ✨ (M) — Calm & informative (Live 3.8)"],
    ["Kore ✨ (F) — Ferme & Assuré (Live 3.8)", "Kore ✨ (voz de mujer) — Firme y segura (Live 3.8)", "Kore ✨ (F) — Firm & assured (Live 3.8)"],
    ["Despina ✨ (F) — Mélodieux & Fluide (Live 3.8)", "Despina ✨ (voz de mujer) — Melódico y fluido (Live 3.8)", "Despina ✨ (F) — Melodious & fluent (Live 3.8)"],
    ["Charon (M) — Neutre & Posé", "Charon (voz de hombre) — Neutro y sereno", "Charon (M) — Neutral & calm"],
    ["Fenrir (M) — Grave & Posé (Quota 90/j)", "Fenrir (voz de hombre) — Grave y sereno (Cuota 90/día)", "Fenrir (M) — Deep & calm (Quota 90/day)"],
    ["Kore (F) — Ferme & Assuré", "Kore (voz de mujer) — Firme y segura", "Kore (F) — Firm & assured"],
    ["Despina (F) — Mélodieux", "Despina (voz de mujer) — Melódico", "Despina (F) — Melodious"],
    ["Puck ✨ (M) — dinámico y enérgico (Live 3.8)", "Puck ✨ (voz de hombre) — dinámico y enérgico (Live 3.8)", "Puck ✨ (M) — dynamic & energetic (Live 3.8)"],
    ["Puck (M) — enérgico", "Puck (voz de hombre) — enérgico", "Puck (M) — energetic"],
    ["🟢 Onyx (M) — OpenAI, grave et posé", "🟢 Onyx (voz de hombre) — OpenAI, grave y sereno", "🟢 Onyx (M) — OpenAI, deep and calm"],
    ["🟢 Alloy — OpenAI, neutre et réactif", "🟢 Alloy — OpenAI, neutro y reactivo", "🟢 Alloy — OpenAI, neutral and responsive"],
    ["🚀 Gilles (M) — français, equipo modesto", "🚀 Gilles (voz de hombre) — francés, equipo modesto", "🚀 Gilles (M) — French, modest hardware"],
    ["🚀 Tom (M) — français, calidad media", "🚀 Tom (voz de hombre) — francés, calidad media", "🚀 Tom (M) — French, medium quality"],
    ["🔊 Kokoro — Siwis (F) 🇫🇷 (Local Ultra-Réel)", "🔊 Kokoro — Siwis (voz de mujer) 🇫🇷 (Local ultrarreal)", "🔊 Kokoro — Siwis (F) 🇫🇷 (Local Ultra-Real)"],
    ["🚀 Siwis (F) — Français, rapide", "🚀 Siwis (voz de mujer) — Francés, rápido", "🚀 Siwis (F) — French, fast"],
    ["🎭 Chatterbox Français — Naturel (GPU recommandé)", "🎭 Chatterbox Francés — Natural (GPU recomendado)", "🎭 Chatterbox French — Natural (GPU recommended)"],
    ["Rémy ✨ — France 🇫🇷 (Premium)", "Rémy ✨ — Francia 🇫🇷 (Premium)", "Rémy ✨ — France 🇫🇷 (Premium)"],
    ["Gérard — Belgique 🇧🇪", "Gérard — Bélgica 🇧🇪", "Gérard — Belgium 🇧🇪"],
    ["Éloïse — France 🇫🇷", "Éloïse — Francia 🇫🇷", "Éloïse — France 🇫🇷"],
    ["Antonio (M) — Brésil 🇧🇷", "Antonio (voz de hombre) — Brasil 🇧🇷", "Antonio (M) — Brazil 🇧🇷"],
    ["Thalita ✨ (F) — Brésil 🇧🇷 (Premium)", "Thalita ✨ (voz de mujer) — Brasil 🇧🇷 (Premium)", "Thalita ✨ (F) — Brazil 🇧🇷 (Premium)"],
    ["Ballad — douce et distinguée", "Ballad — dulce y distinguida", "Ballad — soft and refined"],
    ["Alloy — neutre et équilibrée", "Alloy — neutro y equilibrado", "Alloy — neutral and balanced"],
    ["MODÈLE OPENAI REALTIME", "MODELO OPENAI REALTIME", "OPENAI REALTIME MODEL"],
    ["gpt-realtime (Officiel / Recommandé)", "gpt-realtime (Oficial / Recomendado)", "gpt-realtime (Official / Recommended)"],
    ["✨ Voix Gemini Live 3.8 active : Synthèse audio temps réel ultra-naturelle propulsée par le nouveau moteur audio de Google (Sans quota journalier).", "✨ Voz Gemini Live 3.8 activa: síntesis de audio en tiempo real ultranatural, impulsada por el nuevo motor de audio de Google (Sin cuota diaria).", "✨ Gemini Live 3.8 voice active: ultra-natural real-time audio synthesis powered by Google's new audio engine (No daily quota)."],
    ["🎙️ ElevenLabs Multilingual v2 : Voix studio ultra-réaliste activée (Nécessite une clé API dans Menu > Paramètres API).", "🎙️ ElevenLabs Multilingual v2: voz de estudio ultrarrealista activada (Requiere una clave API en Menú > Ajustes de API).", "🎙️ ElevenLabs Multilingual v2: ultra-realistic studio voice enabled (Requires an API key in Menu > API Settings)."],
    ["⚡ Rapide & Ultra-réel (Consomme très peu de VRAM — 100% Local)", "⚡ Rápido y ultrarreal (Consume muy poca VRAM — 100% local)", "⚡ Fast & ultra-real (Uses very little VRAM — 100% local)"],
    ["VÉRIFICATION...", "VERIFICANDO...", "CHECKING..."],
    ["Piper privilégie la vitesse CPU. Chatterbox est plus lourd et recommande un GPU NVIDIA.", "Piper prioriza la velocidad de CPU. Chatterbox es más pesado y recomienda una GPU NVIDIA.", "Piper favors CPU speed. Chatterbox is heavier and recommends an NVIDIA GPU."],
    ["Le moteur vocal local Kokoro-TTS n'est pas encore prêt sur ce PC.", "El motor de voz local Kokoro-TTS aún no está listo en este PC.", "The local Kokoro-TTS voice engine is not ready on this PC yet."],
    ["⚡ Avantages : Qualité studio ultra-réaliste, latence sous la seconde, fonctionne 100% hors-ligne sur ta carte graphique.", "⚡ Ventajas: calidad de estudio ultrarrealista, latencia por debajo del segundo, funciona 100% sin conexión en tu tarjeta gráfica.", "⚡ Benefits: ultra-realistic studio quality, sub-second latency, runs 100% offline on your graphics card."],
    ["👉 Clique sur le bouton ci-dessous pour télécharger et initialiser Kokoro-TTS automatiquement en 1-Click.", "👉 Pulsa el botón de abajo para descargar e inicializar Kokoro-TTS automáticamente con 1 clic.", "👉 Click the button below to download and initialize Kokoro-TTS automatically in 1 click."],
    ["🟢 KOKORO-TTS LOCAL PRÊT ET ACTIF !", "🟢 ¡KOKORO-TTS LOCAL LISTO Y ACTIVO!", "🟢 LOCAL KOKORO-TTS READY AND ACTIVE!"],
    ["🟢 Voix générée par IA avec OpenAI TTS. Une clé OPENAI_API_KEY et une connexion Internet sont obligatoires. Sans clé ou en cas d'erreur, CORT bascule automatiquement sur Kokoro local, puis sur Henri.", "🟢 Voz generada por IA con OpenAI TTS. Una clave OPENAI_API_KEY y conexión a Internet son obligatorias. Sin clave o en caso de error, CORT cambia automáticamente a Kokoro local y luego a Henri.", "🟢 AI-generated voice with OpenAI TTS. An OPENAI_API_KEY and an internet connection are required. Without a key, or on error, CORT falls back to local Kokoro and then to Henri."],
    ["💻 Moteur local optionnel. Installez-le ci-dessous avant la première utilisation. Piper téléchargera ensuite la voix choisie au premier message (~30 à 65 Mo). En cas d'indisponibilité, CORT utilise automatiquement Henri.", "💻 Motor local opcional. Instálalo abajo antes del primer uso. Piper descargará la voz elegida en el primer mensaje (~30 a 65 MB). Si no está disponible, CORT usa automáticamente Henri.", "💻 Optional local engine. Install it below before first use. Piper will download the chosen voice on the first message (~30 to 65 MB). If unavailable, CORT automatically uses Henri."],
    ["ℹ️ Les voix Gemini AI nécessitent une clé API Gemini active. Si le quota gratuit (10 req/min) est dépassé, CORT bascule automatiquement sur une voix Premium équivalente (Rémy ou Vivienne) sans coupure.", "ℹ️ Las voces de Gemini AI requieren una clave API de Gemini activa. Si se supera la cuota gratuita (10 solicitudes/min), CORT cambia automáticamente a una voz Premium equivalente (Rémy o Vivienne) sin cortes.", "ℹ️ Gemini AI voices need an active Gemini API key. If the free quota (10 req/min) is exceeded, CORT switches to an equivalent Premium voice (Rémy or Vivienne) without interruption."],
    ["Transcription 100% locale via le modèle Canary-1B (~4 Go).", "Transcripción 100% local con el modelo Canary-1B (~4 GB).", "100% local transcription via the Canary-1B model (~4 GB)."],
    ["⚙️ Requis : GPU NVIDIA (Ex: RTX 3060 8Go+ recommandé) + Ollama", "⚙️ Requerido: GPU NVIDIA (Ej: RTX 3060 8 GB+ recomendado) + Ollama", "⚙️ Required: NVIDIA GPU (e.g. RTX 3060 8GB+ recommended) + Ollama"],
    ["CHOISIR LE MODÈLE LOCAL 🖥️", "ELIGE EL MODELO LOCAL 🖥️", "CHOOSE THE LOCAL MODEL 🖥️"],
    ["Sans filtre, libre, ~4.5 Go VRAM • GPU NVIDIA 8 Go+ recommandé", "Sin filtros, libre, ~4,5 GB VRAM • GPU NVIDIA 8 GB+ recomendada", "Unfiltered, free, ~4.5 GB VRAM • NVIDIA GPU 8 GB+ recommended"],
    ["Ultra-rapide, léger, ~2.2 Go VRAM • Idéal pour PC modeste", "Ultrarrápido, ligero, ~2,2 GB VRAM • Ideal para PC modesto", "Ultra-fast, light, ~2.2 GB VRAM • Ideal for modest PCs"],
    ["Puissant, polyvalent, ~5 Go VRAM • Meilleure compréhension du contexte", "Potente, polivalente, ~5 GB VRAM • Mejor comprensión del contexto", "Powerful, versatile, ~5 GB VRAM • Best context understanding"],
    ["✅ Modèle local sauvegardé !", "✅ ¡Modelo local guardado!", "✅ Local model saved!"],
    ["Ce mode tourne 100% en local sur ta carte graphique pour garantir zéro censure et une vitesse ultra-rapide.", "Este modo funciona 100% en local en tu tarjeta gráfica para garantizar cero censura y una velocidad ultrarrápida.", "This mode runs 100% locally on your graphics card to guarantee zero censorship and ultra-fast speed."],
    ["⚠️ Config minimale recommandée : Carte Graphique NVIDIA RTX (8 Go VRAM).", "⚠️ Configuración mínima recomendada: tarjeta gráfica NVIDIA RTX (8 GB VRAM).", "⚠️ Recommended minimum setup: NVIDIA RTX graphics card (8 GB VRAM)."],
    ["👉 Étape 1 : Télécharge et installe Ollama", "👉 Paso 1: descarga e instala Ollama", "👉 Step 1: download and install Ollama"],
    ["🌐 TÉLÉCHARGER OLLAMA (OLLAMA.COM)", "🌐 DESCARGAR OLLAMA (OLLAMA.COM)", "🌐 DOWNLOAD OLLAMA (OLLAMA.COM)"],
    ["👉 Étape 2 : Relance Ollama puis clique ci-dessous :", "👉 Paso 2: reinicia Ollama y pulsa abajo:", "👉 Step 2: restart Ollama, then click below:"],
    ["🔄 VÉRIFIER LA CONNEXION OLLAMA", "🔄 VERIFICAR LA CONEXIÓN CON OLLAMA", "🔄 CHECK OLLAMA CONNECTION"],
    ["Le modèle local sélectionné n'est pas encore installé sur ton PC.", "El modelo local seleccionado aún no está instalado en tu PC.", "The selected local model is not installed on your PC yet."],
    ["📥 TÉLÉCHARGER LE MODÈLE SÉLECTIONNÉ", "📥 DESCARGAR EL MODELO SELECCIONADO", "📥 DOWNLOAD THE SELECTED MODEL"],
    ["🚀 MODÈLE LLM LOCAL PRÊT ET ACTIF !", "🚀 ¡MODELO LLM LOCAL LISTO Y ACTIVO!", "🚀 LOCAL LLM MODEL READY AND ACTIVE!"],
    ["Vérification de Claude Code…", "Verificando Claude Code…", "Checking Claude Code…"],
    ["Vérification nécessaire", "Verificación necesaria", "Verification required"],
    ["Ouvrez le guide ci-dessous pour préparer votre ordinateur.", "Abre la guía de abajo para preparar tu ordenador.", "Open the guide below to prepare your computer."],
    ["Vérifier Ollama", "Verificar Ollama", "Check Ollama"],
    ["VÉRIFIER", "VERIFICAR", "CHECK"],
    ["1. Choisir un modèle", "1. Elegir un modelo", "1. Choose a model"],
    ["Qwen3 4B · recommandé · 2,5 Go", "Qwen3 4B · recomendado · 2,5 GB", "Qwen3 4B · recommended · 2.5 GB"],

    // 🎭 Tono y personalidad del agente
    ["🎭 TON / PERSONNALITÉ DE L'AGENT", "🎭 TONO / PERSONALIDAD DEL AGENTE", "🎭 AGENT TONE / PERSONALITY"],
    ["Sarcastique, roaster, culture Twitch/stream, sans filtre. Redirigé vers xAI Grok (Temp ~0.9).", "Sarcástico, con burlas, cultura Twitch/stream, sin filtros. Redirige a xAI Grok (Temp ~0.9).", "Sarcastic, roasting, Twitch/stream culture, uncensored. Routed to xAI Grok (Temp ~0.9)."],
    ["Provocateur, séducteur, aucun tabou, second degré, incisif. Redirigé vers xAI Grok (Temp ~0.9).", "Provocador, seductor, sin tabúes, doble sentido, incisivo. Redirige a xAI Grok (Temp ~0.9).", "Provocative, flirty, no taboos, dry wit, sharp. Routed to xAI Grok (Temp ~0.9)."],
    ["CLÉ API xAI (GROK API KEY)", "CLAVE API xAI (GROK API KEY)", "xAI API KEY (GROK API KEY)"],
    ["🔑 OBTENIR CLÉ", "🔑 OBTENER CLAVE", "🔑 GET KEY"],
    ["Enregistre automatiquement la clé API xAI dans votre environnement.", "Guarda automáticamente la clave API de xAI en tu entorno.", "Automatically saves the xAI API key in your environment."],
    ["ACTIVÉ", "ACTIVADO", "ENABLED"],
    ["Choisissez l'attitude et la personnalité de CORT. Le mode par défaut conserve la configuration habituelle. Les modes spéciaux basculent dynamiquement sur l'API xAI (Grok).", "Elige la actitud y la personalidad de CORT. El modo predeterminado conserva la configuración habitual. Los modos especiales cambian dinámicamente a la API de xAI (Grok).", "Choose CORT's attitude and personality. Default mode keeps the usual configuration. Special modes switch dynamically to the xAI (Grok) API."],
    ["Garde la configuration, le System Prompt et le modèle habituels du projet CORT.", "Mantiene la configuración, el System Prompt y el modelo habituales del proyecto CORT.", "Keeps CORT's usual configuration, system prompt and model."],
    ["ℹ️ Choisissez l'intelligence artificielle à solliciter en priorité lors de vos requêtes. Les autres API resteront actives en secours (failover) s'il y a une panne ou un quota dépassé.", "ℹ️ Elige la inteligencia artificial que se usará con prioridad en tus peticiones. Las demás API seguirán activas como respaldo (failover) si hay una avería o se supera la cuota.", "ℹ️ Choose which AI to use first for your requests. The other APIs stay active as fallback in case of failure or exceeded quota."],

    // 🔑 Claves API
    ["Activez, désactivez et configurez vos clés API pour les services connectés de CORT. Vos clés sont enregistrées en direct dans votre fichier local", "Activa, desactiva y configura tus claves API para los servicios conectados de CORT. Tus claves se guardan en vivo en tu archivo local", "Enable, disable and configure your API keys for CORT's connected services. Your keys are saved live in your local file"],
    ["Requis pour l'intelligence générale de CORT et les voix ultra-réalistes (Fenrir, Aoede, etc.).", "Requerido para la inteligencia general de CORT y las voces ultrarrealistas (Fenrir, Aoede, etc.).", "Required for CORT's general intelligence and the ultra-realistic voices (Fenrir, Aoede, etc.)."],
    ["Permet à CORT de parler avec des voix studio ultra-réalistes et de charger automatiquement vos voix clonées.", "Permite que CORT hable con voces de estudio ultrarrealistas y cargue automáticamente tus voces clonadas.", "Lets CORT speak with ultra-realistic studio voices and auto-load your cloned voices."],
    ["Offre un accès ultra-rapide à des modèles comme LLaMA 3.", "Ofrece acceso ultrarrápido a modelos como LLaMA 3.", "Gives ultra-fast access to models like LLaMA 3."],
    ["Requis pour rechercher et jouer des chansons spécifiques par leur titre via YouTube.", "Requerido para buscar y reproducir canciones concretas por su título mediante YouTube.", "Required to search and play specific songs by title via YouTube."],
    ["Permet d'utiliser l'IA Grok de xAI pour des réponses alternatives.", "Permite usar la IA Grok de xAI para respuestas alternativas.", "Allows using xAI's Grok for alternative answers."],
    ["Permet d'utiliser l'IA GPT-4o de ChatGPT pour des réponses alternatives.", "Permite usar la IA GPT-4o de ChatGPT para respuestas alternativas.", "Allows using ChatGPT's GPT-4o for alternative answers."],
    ["Utilisé pour afficher des illustrations d'images sur l'écran holographique.", "Se usa para mostrar ilustraciones de imágenes en la pantalla holográfica.", "Used to display image illustrations on the holographic screen."],
    ["Permet d'utiliser le modèle souverain français Mistral Large.", "Permite usar el modelo soberano francés Mistral Large.", "Allows using the French sovereign model Mistral Large."],

    // 🛡 Antivirus y salud del PC
    ["Analyse les processus actifs, le registre de démarrage et les dossiers critiques.", "Analiza los procesos activos, el registro de arranque y las carpetas críticas.", "Analyzes active processes, the startup registry and critical folders."],
    ["PROTECTION ANTIVIRUS EN TEMPS RÉEL (LIVE)", "PROTECCIÓN ANTIVIRUS EN TIEMPO REAL (LIVE)", "REAL-TIME ANTIVIRUS PROTECTION (LIVE)"],
    ["L'antivirus intégré à CORT est un outil d'audit de sécurité local développé sur mesure pour ce projet (sans dépendance externe lourde).", "El antivirus integrado en CORT es una herramienta de auditoría de seguridad local, desarrollada a medida para este proyecto (sin dependencias externas pesadas).", "CORT's built-in antivirus is a local security-audit tool built specifically for this project (no heavy external dependency)."],
    ["Inspecte les clés de démarrage pour détecter des programmes malveillants s'exécutant automatiquement.", "Inspecta las claves de arranque para detectar programas maliciosos que se ejecutan automáticamente.", "Inspects startup keys to detect malware that runs automatically."],
    ["Surveille les applications en cours d'exécution et identifie les activités ou emplacements suspects (ex: dossiers temporaires).", "Vigila las aplicaciones en ejecución e identifica actividades o ubicaciones sospechosas (ej: carpetas temporales).", "Monitors running apps and flags suspicious activity or locations (e.g. temp folders)."],
    ["Analyse vos dossiers sensibles récents (Bureau, Téléchargements, Temp, etc.) à la recherche de signatures de test (EICAR), de doubles extensions dangereuses (ex:", "Analiza tus carpetas sensibles recientes (Escritorio, Descargas, Temp, etc.) buscando firmas de prueba (EICAR), dobles extensiones peligrosas (ej:", "Analyzes your recent sensitive folders (Desktop, Downloads, Temp, etc.) for test signatures (EICAR) and dangerous double extensions (e.g.:"],
    [") et de mots-clés malveillants.", ") y palabras clave maliciosas.", ") and malicious keywords."],
    ["🛡️ Que fait-il en cas de détection ?", "🛡️ ¿Qué hace en caso de detección?", "🛡️ What does it do when it detects something?"],
    ["Par sécurité pour vos données, il ne supprime pas de fichiers et ne bloque pas de processus automatiquement afin d'éviter tout faux positif.", "Por seguridad para tus datos, no borra archivos ni bloquea procesos automáticamente, para evitar cualquier falso positivo.", "To protect your data, it does not delete files or block processes automatically, to avoid false positives."],
    ["Santé du PC · surveillance en arrière-plan", "Salud del PC · vigilancia en segundo plano", "PC health · background monitoring"],
    ["Surveiller la santé du PC", "Vigilar la salud del PC", "Monitor PC health"],
    ["Annoncer les alertes à voix haute", "Anunciar las alertas en voz alta", "Announce alerts out loud"],
    ["Vérifier toutes les", "Comprobar todas las", "Check all the"],
    ["Seuils de surveillance configurables, en °C. Ils ne sont pas des limites constructeur : adaptez-les à votre matériel. Les seuils fournis par les capteurs sont prioritaires.", "Umbrales de vigilancia configurables, en °C. No son límites del fabricante: adáptalos a tu equipo. Los umbrales que aportan los sensores tienen prioridad.", "Configurable monitoring thresholds, in °C. They are not manufacturer limits: adapt them to your hardware. Sensor-provided thresholds take priority."],
    ["Vérification de la surveillance…", "Verificando la vigilancia…", "Checking monitoring…"],
    ["Windows : si les températures sont absentes, téléchargez", "Windows: si las temperaturas no aparecen, descarga", "Windows: if temperatures are missing, download"],
    ["Sans capteurs, CPU/RAM/espace disque restent surveillés. « Aucun problème détecté » ne constitue pas une vérification complète des ventilateurs, de la batterie ou de la santé matérielle des disques.", "Sin sensores, CPU/RAM/espacio disco siguen vigilados. «Ningún problema detectado» no es una comprobación completa de los ventiladores, la batería ni la salud física de los discos.", "Without sensors, CPU/RAM/disk space are still monitored. \"No issue detected\" is not a full check of fans, battery or disk hardware health."],
    ["Détecté", "Detectado", "Detected"],
    ["environ 3 Go de téléchargement. L'installation peut durer de 2 à 10 minutes selon votre connexion.", "unos 3 GB de descarga. La instalación puede tardar de 2 a 10 minutos según tu conexión.", "about 3 GB of download. Installation may take 2 to 10 minutes depending on your connection."],
    ["DÉSINSTALLER NEMOTRON ASR", "DESINSTALAR NEMOTRON ASR", "UNINSTALL NEMOTRON ASR"],

    // 📧 Gmail
    ["📧 INTÉGRATION GMAIL & SERVICES GOOGLE", "📧 INTEGRACIÓN DE GMAIL Y SERVICIOS GOOGLE", "📧 GMAIL & GOOGLE SERVICES INTEGRATION"],
    ["Étape 1 : Obtenir vos identifiants Google (Gratuit)", "Paso 1: obtener tus credenciales de Google (Gratuito)", "Step 1: Get your Google credentials (Free)"],
    ["Créer des identifiants → ID client OAuth", "Crear credenciales → ID de cliente OAuth", "Create credentials → OAuth client ID"],
    ["5. Téléchargez le fichier JSON et renommez-le :", "5. Descarga el archivo JSON y renómbralo:", "5. Download the JSON file and rename it:"],
    ["C'est terminé !", "¡Listo!", "Done!"],
    ["pour afficher le HUD holographique et écouter vos messages.", "para mostrar el HUD holográfico y escuchar tus mensajes.", "to show the holographic HUD and read your messages aloud."],
    ["Permet à CORT de lire vos emails et d'afficher le HUD holographique Iron Man.", "Permite que CORT lea tus correos y muestre el HUD holográfico Iron Man.", "Lets CORT read your emails and show the Iron Man holographic HUD."],
    ["CORT utilise l'API officielle et sécurisée Google OAuth pour lire vos emails directement depuis votre boîte Gmail.", "CORT usa la API oficial y segura Google OAuth para leer tus correos directamente desde tu bandeja de Gmail.", "CORT uses the official, secure Google OAuth API to read your emails straight from your Gmail inbox."],
    ['2. Créez un projet (ex: "CORT Assistant").', '2. Crea un proyecto (ej: "CORT Assistant").', '2. Create a project (e.g. "CORT Assistant").'],
    ["Étape 2 : Placer le fichier dans le dossier CORT", "Paso 2: colocar el archivo en la carpeta de CORT", "Step 2: Place the file in the CORT folder"],
    ["Dites simplement à CORT :", "Di simplemente a CORT:", "Just tell CORT:"],

    // 📦 CORT OS / almacenamiento / accesorios
    ["APPLICATIONS PERSONNALISÉES (Voice Launch)", "APLICACIONES PERSONALIZADAS (Lanzamiento por voz)", "CUSTOM APPS (Voice Launch)"],
    ["🔍 DÉTECTER", "🔍 DETECTAR", "🔍 DETECT"],
    ["☀ Lumières", "☀ Luces", "☀ Lights"],
    ["🎵 LIEN MUSIQUE PERSONNALISÉ", "🎵 ENLACE DE MÚSICA PERSONALIZADO", "🎵 CUSTOM MUSIC LINK"],
    ["AUCUN MÉDIA CHARGÉ", "NINGÚN MEDIO CARGADO", "NO MEDIA LOADED"],
    ["📡 CHAÎNES IPTV", "📡 CANALES IPTV", "📡 IPTV CHANNELS"],
    ["GLISSER UN FICHIER VIDÉO / M3U", "ARRASTRA UN ARCHIVO DE VÍDEO / M3U", "DRAG A VIDEO / M3U FILE"],
    ["⟳ RÉESSAYER", "⟳ REINTENTAR", "⟳ RETRY"],
    ["⛶ QUITTER PLEIN ÉCRAN", "⛶ SALIR DE PANTALLA COMPLETA", "⛶ EXIT FULLSCREEN"],
    ["⚡ DÉTACHER", "⚡ DESACOPLO", "⚡ UNPLUG"],
    ["Génération du code source et des images en cours...", "Generando el código fuente y las imágenes...", "Generating source code and images..."],
    ["Génération…", "Generando…", "Generating…"],
    ["PERSONNALISATION // ORB + FONDS D'ÉCRAN", "PERSONALIZACIÓN // ORBE + FONDOS DE PANTALLA", "PERSONALIZATION // ORB + WALLPAPERS"],
    ["Choisir un modèle charge son fond recommandé. Vous pouvez ensuite sélectionner librement un autre fond sans changer l'ORB.", "Elegir un modelo carga su fondo recomendado. Después puedes seleccionar libremente otro fondo sin cambiar el ORBE.", "Choosing a model loads its recommended wallpaper. You can then pick a different wallpaper without changing the ORB."],
    ["Arrière-plan Windows actuel", "Fondo de pantalla actual de Windows", "Current Windows wallpaper"],
    ["Couloir Cybernétique", "Pasillo cibernético", "Cybernetic corridor"],
    ["Esthétique néon bleu futuriste", "Estética de neón azul futurista", "Futuristic blue neon aesthetic"],
    ["Cœur Quantique", "Núcleo cuántico", "Quantum core"],
    ["Réacteur à fusion luminescent", "Reactores de fusión luminiscentes", "Luminescent fusion reactors"],
    ["Matrice Réacteur Arc", "Matriz de reactor de arco", "Arc Reactor matrix"],
    ["Observatoire astral doré", "Observatorio astral dorado", "Golden astral observatory"],
    ["Verre fissuré et cœur électrique", "Vidrio agrietado y núcleo eléctrico", "Cracked glass and electric core"],
    ["Flux éthérique et brumes spectrales", "Flujos etéreos y brumas espectrales", "Etheric flows and spectral mists"],
    ["Cathédrale NEXUS", "Catedral NEXUS", "NEXUS cathedral"],
    ["Réseau neural et connexions lumineuses", "Red neuronal y conexiones luminosas", "Neural network and glowing connections"],
    ["Estrade holographique & nébuleuse cosmique", "Escenario holográfico y nebulosa cósmica", "Holographic stage & cosmic nebula"],
    ["Image Personnalisée", "Imagen personalizada", "Custom image"],
    ["Votre propre arrière-plan", "Tu propio fondo de pantalla", "Your own wallpaper"],
    ["OU IMPORTER UNE IMAGE PERSONNALISÉE", "O IMPORTAR UNA IMAGEN PERSONALIZADA", "OR IMPORT A CUSTOM IMAGE"],
    ["Cliquez ou glissez une image ici (PNG, JPG, WebP — jusqu'à 25 Mo)", "Pulsa o arrastra una imagen aquí (PNG, JPG, WebP — hasta 25 MB)", "Click or drag an image here (PNG, JPG, WebP — up to 25 MB)"],
    ["Luminosité :", "Brillo:", "Brightness:"],
    ["Flou d'arrière-plan :", "Desenfoque del fondo:", "Background blur:"],
    ["RÉINITIALISER (NOIR)", "REINICIAR (NEGRO)", "RESET (BLACK)"],
    ["est un projet personnel ambitieux, conçu pour repousser les limites de l'assistance virtuelle sur ordinateur.", "es un proyecto personal ambicioso, diseñado para empujar los límites de la asistencia virtual en el ordenador.", "is an ambitious personal project, built to push the limits of virtual assistance on a computer."],
    ["100% open-source et entièrement gratuit", "100% de código abierto y totalmente gratuito", "100% open source and completely free"],
    ["⚠️ AVERTISSEMENT LÉGAL", "⚠️ AVISO LEGAL", "⚠️ LEGAL DISCLAIMER"],
    ["ACCÈS DISTANT HTTPS", "ACCESO REMOTO HTTPS", "HTTPS REMOTE ACCESS"],
    ["✓ Zéro compte requis", "✓ No requiere cuenta", "✓ No account required"],
    ["✓ Zéro configuration de box / routeur", "✓ Sin configurar el router", "✓ No router configuration"],
    ["🌐 ACTIVER L'ACCÈS HTTPS", "🌐 ACTIVAR EL ACCESO HTTPS", "🌐 ENABLE HTTPS ACCESS"],
    ["Générez automatiquement une URL HTTPS sécurisée pour contrôler CORT depuis n'importe où sur Internet.", "Genera automáticamente una URL HTTPS segura para controlar CORT desde cualquier lugar de Internet.", "Automatically generate a secure HTTPS URL to control CORT from anywhere on the internet."],
    ["Café en grano", "Café en grano", "Coffee beans"],
    ["Caméra", "Cámara", "Camera"],
    ["fermer complètement CORT", "cerrar CORT por completo", "completely close CORT"],
    ["CORT OS est un environnement Linux (Ubuntu) complet, sécurisé et totalement isolé du reste de votre système. Idéal pour la navigation sécurisée ou l'exécution de tâches isolées.", "CORT OS es un entorno Linux (Ubuntu) completo, seguro y totalmente aislado del resto de tu sistema. Ideal para navegar con seguridad o ejecutar tareas aisladas.", "CORT OS is a full Linux (Ubuntu) environment, secure and completely isolated from the rest of your system. Ideal for safe browsing or running isolated tasks."],
    ["CONFIGURACIÓN DEL ALMACÉN", "CONFIGURACIÓN DEL ALMACÉN", "STORAGE CONFIGURATION"],
    ["Sélectionnez le dossier de destination où seront stockées les données de CORT OS (configuration système et dossier de partage avec votre PC).", "Selecciona la carpeta de destino donde se guardarán los datos de CORT OS (configuración del sistema y carpeta compartida con tu PC).", "Select the destination folder where CORT OS data will be stored (system configuration and the folder shared with your PC)."],
    ["SYSTÈMES OPÉRATIONNELS — BONNE JOURNÉE", "SISTEMAS OPERATIVOS — BUEN DÍA", "OPERATING SYSTEMS — HAVE A GOOD DAY"],
    ["MISE À JOUR CORT", "ACTUALIZACIÓN DE CORT", "CORT UPDATE"],
    ["◈ CORT // RÉPERTOIRE DES COMMANDES VOCALES", "◈ CORT // REPERTORIO DE COMANDOS DE VOZ", "◈ CORT // SPOKEN COMMAND CATALOG"],
    ["Coupe CORT immédiatement", "Corta CORT inmediatamente", "Stops CORT immediately"],
    ["Deletrea [palabra] en alfabeto fonético", "Deletrea [palabra] en alfabeto fonético", "Spell [word] in the phonetic alphabet"],
    ["Retour à l'interface CORT", "Volver a la interfaz de CORT", "Back to the CORT interface"],
    ["Capture et description détaillée de ce que CORT voit", "Captura y descripción detallada de lo que CORT ve", "Captures and describes in detail what CORT sees"],
    ["Google Gemini (Par défaut)", "Google Gemini (Predeterminado)", "Google Gemini (Default)"],
    ["Configurer l'IA locale · Ollama, modèle et contrôle du PC", "Configurar la IA local · Ollama, modelo y control del PC", "Configure local AI · Ollama, model and PC control"],
    ["MENU PRINCIPAL", "MENÚ PRINCIPAL", "MAIN MENU"]
  ];

  // ---- 2a-quater. Guía de Ollama (texto largo, página por página) ----------
  const D_EXT3 = [
    ["Guide complet · installation, premier essai et dépannage", "Guía completa · instalación, primera prueba y solución de problemas", "Full guide · installation, first run and troubleshooting"],
    ["A. Comprendre ce qui est nécessaire", "A. Entender qué hace falta", "A. Understand what is required"],
    ["Il faut trois éléments :", "Hacen falta tres elementos:", "Three things are required:"],
    ["Ollama installé", "Ollama instalado", "Ollama installed"],
    ["un modèle téléchargé", "un modelo descargado", "a downloaded model"],
    [". Ollama peut rester en arrière-plan : sa fenêtre n'a pas besoin de rester visible.", ". Ollama puede quedarse en segundo plano: su ventana no necesita seguir visible.", ". Ollama can stay in the background: its window does not need to remain visible."],
    ["Utilisez Windows 10 22H2 ou une version plus récente, ou Windows 11.", "Usa Windows 10 22H2 o una versión más reciente, o Windows 11.", "Use Windows 10 22H2 or newer, or Windows 11."],
    ["Téléchargez l'installateur Windows officiel", "Descarga el instalador oficial de Windows", "Download the official Windows installer"],
    ["Lancez Ollama depuis le menu Démarrer. Il fonctionne ensuite en arrière-plan et peut apparaître dans la zone de notification.", "Abre Ollama desde el menú Inicio. Después funciona en segundo plano y puede aparecer en la zona de notificaciones.", "Launch Ollama from the Start menu. It then runs in the background and may appear in the notification area."],
    ["Revenez ici et cliquez sur « Vérifier Ollama ». Si vous utilisez les commandes ci-dessous, ouvrez une nouvelle fenêtre PowerShell après l'installation.", "Vuelve aquí y pulsa «Verificar Ollama». Si usas los comandos de abajo, abre una nueva ventana de PowerShell tras la instalación.", "Return here and click \"Check Ollama\". If you use the commands below, open a new PowerShell window after installation."],
    ["Consultez la procédure Linux officielle", "Consulta el procedimiento oficial de Linux", "See the official Linux procedure"],
    [". La commande officielle télécharge et exécute le script d'installation ; elle peut demander votre mot de passe administrateur.", ". El comando oficial descarga y ejecuta el script de instalación; puede pedirte tu contraseña de administrador.", ". The official command downloads and runs the install script; it may ask for your administrator password."],
    ["Avec systemd, le service reste actif sans fenêtre ouverte. Si votre installation n'utilise pas systemd, démarrez", "Con systemd, el servicio sigue activo sin ventana abierta. Si tu instalación no usa systemd, inicia", "With systemd the service stays active without a window. If your setup does not use systemd, start"],
    ["dans un terminal et laissez-le fonctionner. Ne démarrez pas un second serveur si le service répond déjà.", "en una terminal y déjalo funcionando. No inicies un segundo servidor si el servicio ya responde.", "in a terminal and leave it running. Do not start a second server if the service already responds."],
    ["C. Télécharger un modèle", "C. Descargar un modelo", "C. Download a model"],
    ["pour commencer, ou un modèle déjà installé dans la liste.", "para empezar, o un modelo ya instalado de la lista.", "to start with, or an already installed model from the list."],
    ["Prévoyez Internet pour ce téléchargement et de l'espace disque : environ 2,5 Go pour Qwen3 4B, 5,2 Go pour Qwen3 8B. Gardez une marge pour Ollama et les autres modèles.", "Necesitarás Internet para esta descarga y espacio en disco: unos 2,5 GB para Qwen3 4B, 5,2 GB para Qwen3 8B. Deja margen para Ollama y los demás modelos.", "You will need internet for this download and disk space: about 2.5 GB for Qwen3 4B, 5.2 GB for Qwen3 8B. Leave room for Ollama and other models."],
    ["Cliquez sur « Télécharger ce modèle », puis attendez la fin. Fermer les paramètres ne stoppe pas le téléchargement ; le bouton « Annuler » demande son arrêt.", "Pulsa «Descargar este modelo» y espera a que termine. Cerrar los ajustes no detiene la descarga; el botón «Cancelar» sí la detiene.", "Click \"Download this model\" and wait for it to finish. Closing settings does not stop the download; the \"Cancel\" button requests it."],
    ["Les modèles restent installés après redémarrage. Un téléchargement interrompu peut généralement être relancé. Les conseils de mémoire sont des estimations ; le contexte, les applications ouvertes et votre matériel modifient les besoins.", "Los modelos siguen instalados tras reiniciar. Una descarga interrumpida suele poder reanudarse. Las recomendaciones de memoria son estimaciones: el contexto, las aplicaciones abiertas y tu hardware cambian las necesidades.", "Models stay installed after a reboot. An interrupted download can usually be resumed. Memory advice is an estimate; context, open apps and your hardware change what is needed."],
    ["D. Vérifier et activer", "D. Verificar y activar", "D. Verify and enable"],
    ["Le diagnostic doit afficher « Modèle disponible ».", "El diagnóstico debe mostrar «Modelo disponible».", "The diagnostic must show \"Model available\"."],
    ["Cliquez sur « Tester le modèle ». Le premier chargement peut prendre jusqu'à 90 secondes. Ce test vérifie une réponse structurée simple sans exécuter d'action sur votre ordinateur.", "Pulsa «Probar el modelo». La primera carga puede tardar hasta 90 segundos. Esta prueba comprueba una respuesta estructurada simple sin ejecutar ninguna acción en tu ordenador.", "Click \"Test the model\". The first load can take up to 90 seconds. This test checks a simple structured response without performing any action on your computer."],
    ["Cochez les fonctions souhaitées puis cliquez sur « Enregistrer l'IA locale ».", "Marca las funciones deseadas y pulsa «Guardar IA local».", "Tick the desired functions, then click \"Save local AI\"."],
    ["Pour la conversation : demandez « Explique-moi simplement à quoi sert la RAM ». Pour le contrôle : demandez « ordinateur : quelle est l'utilisation du processeur et de la RAM ? ».", "Para la conversación: pregunta «Explícame simplemente para qué sirve la RAM». Para el control: pregunta «ordenador: ¿qué uso tienen el procesador y la RAM?».", "For conversation: ask \"Explain simply what RAM is for\". For control: ask \"computer: what is the CPU and RAM usage?\"."],
    ["pour les outils et dépendances de votre version.", "para las herramientas y dependencias de tu versión.", "for the tools and dependencies of your version."],
    ["F. Dépannage", "F. Solución de problemas", "F. Troubleshooting"],
    ["Ollama ne répond pas :", "Ollama no responde:", "Ollama is not responding:"],
    ["lancez-le, vérifiez le service Linux ou la zone de notification Windows, puis cliquez sur « Vérifier Ollama ». Le service attendu écoute sur le port 11434 de ce PC.", "ínicialo, revisa el servicio de Linux o la zona de notificaciones de Windows y pulsa «Verificar Ollama». El servicio esperado escucha en el puerto 11434 de este PC.", "start it, check the Linux service or the Windows notification area, then click \"Check Ollama\". The expected service listens on port 11434 of this PC."],
    ["Modèle absent :", "Modelo ausente:", "Missing model:"],
    ["téléchargez le modèle choisi ou sélectionnez un modèle déjà installé. La liste correspond à cet ordinateur, pas à un autre PC.", "descarga el modelo elegido o selecciona uno ya instalado. La lista corresponde a este ordenador, no a otro PC.", "download the chosen model or select an already installed one. The list belongs to this computer, not another PC."],
    ["Téléchargement bloqué :", "Descarga bloqueada:", "Blocked download:"],
    ["vérifiez Internet et l'espace disque ; annulez puis relancez. Une annulation peut attendre la prochaine réponse du serveur.", "revisa Internet y el espacio en disco; cancela y vuelve a empezar. Una cancelación puede esperar la próxima respuesta del servidor.", "check internet and disk space; cancel and restart. A cancellation may wait for the server's next reply."],
    ["Réponse lente ou mémoire insuffisante :", "Respuesta lenta o memoria insuficiente:", "Slow reply or not enough memory:"],
    ["fermez les applications lourdes, choisissez Qwen3 4B, mettez à jour Ollama et les pilotes graphiques officiels. Un processeur seul peut fonctionner mais être plus lent.", "cierra las aplicaciones pesadas, elige Qwen3 4B, actualiza Ollama y los drivers gráficos oficiales. Un solo procesador puede funcionar, pero será más lento.", "close heavy apps, pick Qwen3 4B, update Ollama and the official graphics drivers. CPU-only can work but will be slower."],
    ["réessayez ou changez de modèle. « Modèle disponible » indique sa présence, pas la fiabilité de toutes ses réponses.", "reintenta o cambia de modelo. «Modelo disponible» indica que está, no que todas sus respuestas sean fiables.", "retry or change model. \"Model available\" means it is present, not that every answer is reliable."],
    ["Port déjà utilisé :", "Puerto ya en uso:", "Port already in use:"],
    ["un serveur Ollama peut être déjà lancé. Vérifiez avant d'utiliser", "puede haber un servidor Ollama ya iniciado. Comprueba antes de usar", "an Ollama server may already be running. Check before using"],
    ["G. Après un redémarrage ou pour désactiver", "G. Tras reiniciar o para desactivar", "G. After a reboot, or to disable"],
    ["Vérifiez qu'Ollama est lancé ; aucun nouveau téléchargement n'est nécessaire. Pour revenir au choix automatique des IA, décochez « Conversations avec l'IA locale » et enregistrez. Décochez le contrôle avancé pour le désactiver. Les modèles restent sur le disque.", "Comprueba que Ollama esté iniciado; no hace falta descargar nada de nuevo. Para volver a la elección automática de IA, desmarca «Conversaciones con IA local» y guarda. Desmarca el control avanzado para desactivarlo. Los modelos se quedan en el disco.", "Make sure Ollama is running; no new download is needed. To go back to automatic AI selection, uncheck \"Conversations with local AI\" and save. Uncheck advanced control to disable it. Models stay on disk."],
    ["Pour gérer les modèles dans un terminal :", "Para gestionar los modelos en una terminal:", "To manage models in a terminal:"],
    ["liste les modèles,", "lista los modelos,", "lists the models,"],
    ["affiche ceux chargés en mémoire,", "muestra los cargados en memoria,", "shows the ones loaded in memory,"],
    ["libère le modèle de la mémoire, et", "libera el modelo de la memoria, y", "frees the model from memory, and"],
    ["supprime ses fichiers. La dernière commande impose de retélécharger le modèle pour le réutiliser.", "borra sus archivos. La última obliga a descargar el modelo otra vez para reutilizarlo.", "deletes its files. The last one requires re-downloading the model to use it again."],
    ["Compact : commencez ici. 16 Go de RAM conseillés, carte graphique facultative. Téléchargement : environ 2,5 Go.", "Compacto: empieza aquí. Se recomiendan 16 GB de RAM, tarjeta gráfica opcional. Descarga: unos 2,5 GB.", "Compact: start here. 16 GB RAM advised, graphics card optional. Download: about 2.5 GB."],
    ["Télécharger ce modèle", "Descargar este modelo", "Download this model"],
    ["Tester le modèle", "Probar el modelo", "Test the model"],
    ["Fiche du modèle ↗", "Ficha del modelo ↗", "Model card ↗"],
    ["Annuler le téléchargement", "Cancelar la descarga", "Cancel download"],
    ["Contrôle avancé de l'ordinateur", "Control avanzado del ordenador", "Advanced computer control"],
    ["Comprendre et combiner des actions en langage naturel. Les actions sensibles demandent une confirmation précise. Les outils disponibles dépendent de votre système.", "Entender y combinar acciones en lenguaje natural. Las acciones sensibles piden una confirmación precisa. Las herramientas disponibles dependen de tu sistema.", "Understands and combines actions in natural language. Sensitive actions need an exact confirmation. Available tools depend on your system."],
    ["Ollama fait fonctionner un modèle d'IA sur votre ordinateur. CORT lui transmet votre demande pour rédiger une réponse ou préparer une suite d'actions : chercher un fichier, organiser un dossier, utiliser une application.", "Ollama ejecuta un modelo de IA en tu ordenador. CORT le transmite tu petición para redactar una respuesta o preparar una serie de acciones: buscar un archivo, organizar una carpeta, usar una aplicación.", "Ollama runs an AI model on your computer. CORT sends it your request to write an answer or plan a set of actions: find a file, organize a folder, use an app."],
    ["Pas de clé API pour ce moteur, pas de facturation à la requête. Après installation et téléchargement du modèle, l'inférence fonctionne sans Internet. La vitesse dépend de votre PC. La voix, les recherches web et certains services de CORT peuvent encore utiliser Internet.", "Sin clave API para este motor, sin facturación por petición. Tras instalarlo y descargar el modelo, la inferencia funciona sin Internet. La velocidad depende de tu PC. La voz, las búsquedas web y algunos servicios de CORT pueden seguir usando Internet.", "No API key for this engine, no per-request billing. After install and model download, inference runs offline. Speed depends on your PC. Voice, web searches and some CORT services may still use the internet."],
    ["Utiliser ce modèle pour les réponses textuelles de CORT. En cas de panne, aucun basculement automatique vers une IA en ligne pour cette conversation.", "Usar este modelo para las respuestas de texto de CORT. Si falla, no se cambia automáticamente a una IA en línea en esta conversación.", "Use this model for CORT's text answers. On failure, no automatic fallback to an online AI for this conversation."],
    ["Surveillance locale pendant que CORT fonctionne, sans requêtes IA. Trois mesures successives sont nécessaires avant une alerte ; une même alerte est espacée d'au moins dix minutes. La voix attend la fin de la conversation en cours.", "Vigilancia local mientras CORT funciona, sin consultas a la IA. Hacen falta tres medidas consecutivas antes de una alerta; la misma alerta se espacia al menos diez minutos. La voz espera el final de la conversación en curso.", "Local monitoring while CORT runs, with no AI requests. Three consecutive readings are needed before an alert; the same alert is spaced by at least ten minutes. Voice waits for the current conversation to end."],
    ["CORT propose des conseils ; il ne ferme pas de jeu, ne supprime pas de fichiers et ne modifie pas les ventilateurs automatiquement. Vous pouvez lui demander une action : le contrôle ordinateur conserve ses confirmations.", "CORT ofrece consejos; no cierra juegos, no borra archivos y no cambia los ventiladores automáticamente. Puedes pedirle una acción: el control del ordenador mantiene sus confirmaciones.", "CORT offers advice; it does not close games, delete files or change fans automatically. You can ask it to act: computer control keeps its confirmations."],
    [", extrayez l'archive et lancez-le. Laissez-le fonctionner en arrière-plan puis actualisez ici. Certains capteurs nécessitent de lancer cet outil en administrateur. CORT lit son fournisseur WMI local quand il est disponible ; la compatibilité dépend du matériel. Aucune installation ni élévation de privilèges n'est faite par CORT. Linux utilise les capteurs exposés au système.", ", extrae el archivo y ejecútalo. Déjalo en segundo plano y actualiza aquí. Algunos sensores requieren ejecutar esta herramienta como administrador. CORT lee su proveedor WMI local cuando está disponible; la compatibilidad depende del hardware. CORT no instala nada ni eleva privilegios. Linux usa los sensores expuestos al sistema.", ", extract the archive and run it. Leave it in the background, then refresh here. Some sensors require running this tool as administrator. CORT reads its local WMI provider when available; compatibility depends on hardware. CORT installs nothing and never elevates privileges. Linux uses the sensors exposed to the system."],
    [". Ouvrir Ollama seul ne télécharge pas de modèle. CORT communique avec lui sur ce PC, à l'adresse", ". Abrir Ollama por sí solo no descarga ningún modelo. CORT se comunica con él en este PC, en la dirección", ". Opening Ollama alone does not download a model. CORT talks to it on this PC at"],
    ["Pour une action sensible, CORT affiche la proposition et un code. Dites exactement « confirme action CODE » ou « annule action CODE ». Une réussite au test simple ne garantit pas tous les plans complexes.", "Para una acción sensible, CORT muestra la propuesta y un código. Di exactamente «confirma acción CÓDIGO» o «anula acción CÓDIGO». Superar la prueba simple no garantiza todos los planes complejos.", "For a sensitive action, CORT shows the proposal and a code. Say exactly \"confirm action CODE\" or \"cancel action CODE\". Passing the simple test does not guarantee every complex plan."],
    ["Sans Ollama, les fonctions habituelles de CORT restent accessibles selon leurs propres réglages. Cette section ajoute un moteur local de conversation et de planification. Le diagnostic « Pourquoi mon PC rame ? » relève directement les mesures du PC, sans plan généré ; les demandes complexes utilisent le modèle Ollama choisi. Ollama seul ne donne pas accès à toutes les applications et n'installe pas les outils de contrôle.", "Sin Ollama, las funciones habituales de CORT siguen disponibles según sus propios ajustes. Esta sección añade un motor local de conversación y planificación. El diagnóstico «¿Por qué va lento mi PC?» lee directamente las medidas del PC, sin plan generado; las peticiones complejas usan el modelo de Ollama elegido. Ollama solo no da acceso a todas las aplicaciones ni instala las herramientas de control.", "Without Ollama, CORT's usual functions remain available under their own settings. This section adds a local conversation and planning engine. The \"Why is my PC slow?\" diagnostic reads PC measurements directly, with no generated plan; complex requests use the chosen Ollama model. Ollama alone does not unlock every app and does not install control tools."],
    ["Le contrôle des fichiers est limité aux dossiers autorisés par CORT. Certains sites, applications, écrans protégés et opérations système ne sont pas contrôlables. Consultez le guide livré", "El control de archivos se limita a las carpetas autorizadas por CORT. Ciertos sitios, aplicaciones, pantallas protegidas y operaciones del sistema no se pueden controlar. Consulta la guía incluida", "File control is limited to folders CORT is allowed to touch. Some sites, apps, protected screens and system operations cannot be controlled. See the bundled guide"],
    [". Les autres distributions utilisent leur gestionnaire de paquets. Wayland ne fournit pas un contrôle universel des fenêtres. Pour une version exécutable de CORT, utilisez une distribution incluant ces composants ; installer des paquets dans un autre Python ne modifie pas cet exécutable.", ". Las demás distribuciones usan su propio gestor de paquetes. Wayland no ofrece un control universal de ventanas. Para una versión ejecutable de CORT, usa una distribución que incluya estos componentes; instalar paquetes en otro Python no modifica este ejecutable.", ". Other distributions use their own package manager. Wayland does not provide universal window control. For a runnable CORT build, use a distribution that includes these components; installing packages into another Python does not change this executable."],
    ["CORT déconnecté :", "CORT desconectado:", "CORT disconnected:"],
    ["démarrez le moteur CORT et attendez sa reconnexion.", "inicia el motor de CORT y espera a que se reconecte.", "start the CORT engine and wait for it to reconnect."],
    ["Connexion gérée par Claude Code : CORT ne reçoit ni mot de passe ni clé Claude.", "Conexión gestionada por Claude Code: CORT no recibe ni contraseña ni clave de Claude.", "Connection handled by Claude Code: CORT receives neither a password nor a Claude key."]
  ];

  // ---- 2a-quinquies. Resto del catálogo de comandos, impresión 3D, claves --
  const D_EXT4 = [
    // Panel de comandos de voz (página 2)
    ["🔍 RECHERCHER UNE COMMANDE...", "🔍 BUSCAR UN COMANDO...", "🔍 SEARCH A COMMAND..."],
    ["Quelle est la date d'aujourd'hui ?", "¿Qué fecha es hoy?", "What is today's date?"],
    ["Date du jour", "Fecha de hoy", "Today's date"],
    ["Raconte-moi une blague", "Cuéntame un chiste", "Tell me a joke"],
    ["Inspire-moi / donne-moi une citation", "Inspírame / dame una cita", "Inspire me / give me a quote"],
    ["Comment dit-on [mot] en anglais ?", "¿Cómo se dice [palabra] en inglés?", "How do you say [word] in English?"],
    ["Quelle est la capitale de [pays] ?", "¿Cuál es la capital de [país]?", "What is the capital of [country]?"],
    ["Capitales du monde", "Capitales del mundo", "World capitals"],
    ["Quelle est la monnaie de [pays] ?", "¿Cuál es la moneda de [país]?", "What is the currency of [country]?"],
    ["Monnaies du monde", "Monedas del mundo", "World currencies"],
    ["Lance une alarme dans [X] minutes", "Pon una alarma en [X] minutos", "Set an alarm in [X] minutes"],
    ["Ajoute [X] minutes au minuteur", "Añade [X] minutos al temporizador", "Add [X] minutes to the timer"],
    ["Prolonge le minuteur en cours", "Alarga el temporizador en curso", "Extends the running timer"],
    ["Retire [X] minutes au minuteur", "Quita [X] minutos al temporizador", "Remove [X] minutes from the timer"],
    ["Raccourcit le minuteur", "Acorta el temporizador", "Shortens the timer"],
    ["Stop le minuteur / Annule le timer", "Para el temporizador / Cancela el timer", "Stop the timer / Cancel the timer"],
    ["Stoppe le minuteur actif", "Detiene el temporizador activo", "Stops the active timer"],
    ["Combien de minuteurs actifs ?", "¿Cuántos temporizadores activos hay?", "How many active timers?"],
    ["Enregistre une note rapide", "Guarda una nota rápida", "Saves a quick note"],
    ["Vide toutes les notes", "Borra todas las notas", "Clears all notes"],
    ["Compose et chante une musique", "Compone y canta una música", "Composes and sings a song"],
    ["Joue [artiste/titre] sur Spotify", "Pon [artista/título] en Spotify", "Play [artist/title] on Spotify"],
    ["Mets du [genre] / Joue de la [musique]", "Pon [género] / reproduce [música]", "Play [genre] / play [music]"],
    ["Monte le volume / Baisse le son", "Sube el volumen / Baja el sonido", "Turn up volume / turn down sound"],
    ["Lance l'app Spotify", "Abre la app de Spotify", "Launch the Spotify app"],
    ["Mets de la musique sur YouTube", "Pon música en YouTube", "Play music on YouTube"],
    ["Mets [artiste/titre] sur YouTube", "Pon [artista/título] en YouTube", "Play [artist/title] on YouTube"],
    ["Lance [titre] sur YouTube", "Reproduce [título] en YouTube", "Play [title] on YouTube"],
    ["Les tendances YouTube", "Las tendencias de YouTube", "YouTube trending"],
    ["Allume la prise du bureau", "Enciende el enchufe del escritorio", "Turn on the desk plug"],
    ["Ouvre le bloc-notes / Notepad", "Abre el bloc de notas / Notepad", "Open Notepad"],
    ["Ouvre l'explorateur de fichiers", "Abre el explorador de archivos", "Open file explorer"],
    ["Ouvre l'invite de commande / CMD", "Abre la terminal de comandos / CMD", "Open command prompt / CMD"],
    ["Applications du catalogue", "Aplicaciones del catálogo", "Catalog applications"],
    ["Ferme une application ouverte", "Cierra una aplicación abierta", "Closes an open app"],
    ["Lance toutes les apps de travail", "Abre todas las apps de trabajo", "Launch all work apps"],
    ["Coupe le son / Mute", "Corta el sonido / Silencio", "Mute sound"],
    ["Screenshot sur le bureau", "Captura de pantalla en el escritorio", "Screenshot on the desktop"],
    ["Extinction dans 5 secondes", "Apagado en 5 segundos", "Shutdown in 5 seconds"],
    ["📁 GESTION DES DOSSIERS", "📁 GESTIÓN DE CARPETAS", "📁 FOLDER MANAGEMENT"],
    ["Dossier Bureau", "Carpeta Escritorio", "Desktop folder"],
    ["Dossier Documents", "Carpeta Documentos", "Documents folder"],
    ["Dossier Images", "Carpeta Imágenes", "Pictures folder"],
    ["Dossier Musique", "Carpeta Música", "Music folder"],
    ["Ouvre le dossier [chemin]", "Abre la carpeta [ruta]", "Open the [path] folder"],
    ["Fly-to vers une ville", "Vuelo hacia una ciudad", "Fly-to a city"],
    ["Ferme le globe / Ferme la carte", "Cierra el globo / Cierra el mapa", "Close the globe / Close the map"],
    ["Qu'est-ce que tu vois ?", "¿Qué estás viendo?", "What do you see?"],
    ["Tape [texte] dans le champ", "Escribe [texto] en el campo", "Type [text] in the field"],
    ["Lecture des 3 derniers emails Gmail", "Lectura de los 3 últimos correos de Gmail", "Reads the last 3 Gmail emails"],
    ["Doc avec titre et texte initial", "Documento con título y texto inicial", "Doc with title and initial text"],
    ["Ajoute du texte au document actif", "Añade texto al documento activo", "Adds text to the active document"],
    ["Lecture vocale du contenu du doc", "Lectura en voz alta del contenido del documento", "Reads the document aloud"],
    ["Ouvre le document dans le navigateur", "Abre el documento en el navegador", "Opens the document in the browser"],
    ["Partage mon Google Doc avec [email]", "Comparte mi Google Doc con [email]", "Share my Google Doc with [email]"],
    ["Appelle [contact] sur WhatsApp", "Llama a [contacto] por WhatsApp", "Call [contact] on WhatsApp"],
    ["Analyse via le panel Antivirus", "Análisis desde el panel Antivirus", "Analysis via the Antivirus panel"],
    ['Via le bouton "ANTIVIRUS" dans le menu', 'Mediante el botón "ANTIVIRUS" del menú', 'Via the "ANTIVIRUS" button in the menu'],
    ["Cliquez pour effacer", "Pulsa para borrar", "Click to clear"],
    ["VOUS ›", "TÚ ›", "YOU ›"],
    ["Qui te a créé ?", "¿Quién te creó?", "Who created you?"],
    ["Quelle est la température de [pièce] ?", "¿Qué temperatura tiene [habitación]?", "What is the temperature of [room]?"],
    ["Combien de personnes dans la pièce ?", "¿Cuántas personas hay en la habitación?", "How many people in the room?"],

    // 🖨 Impresión 3D
    ["Lancez l'analyse ou ajoutez le dossier contenant vos jeux.", "Inicia el análisis o añade la carpeta que contiene tus juegos.", "Start the scan or add the folder containing your games."],
    ["Configuration du module Impression 3D requise", "Hace falta configurar el módulo de Impresión 3D", "3D Print module setup required"],
    ["Installer et configurer le module automatiquement", "Instalar y configurar el módulo automáticamente", "Install and configure the module automatically"],
    ["Aperçu image", "Vista previa de la imagen", "Image preview"],
    ["Optimiser pour l'impression 3D (Fermeture des trous & STL solide)", "Optimizar para impresión 3D (Cerrar agujeros y STL sólido)", "Optimize for 3D printing (Hole filling & solid STL)"],
    ["Calcul du volume 3D...", "Calculando el volumen 3D...", "Computing 3D volume..."],
    ["Finalisation du fichier STL.", "Terminando el archivo STL.", "Finalizing the STL file."],
    ["OUVRIR LE DOSSIER DES EXPORTS", "ABRIR LA CARPETA DE EXPORTACIONES", "OPEN EXPORTS FOLDER"],
    ["Aucun dossier sélectionné...", "Ninguna carpeta seleccionada...", "No folder selected..."],
    ["LANCER L'INSTALLATION", "INICIAR LA INSTALACIÓN", "START INSTALLATION"],

    // 🌐 Acceso remoto y emparejamiento
    ["Accès HTTPS désactivé (cliquez pour activer)", "Acceso HTTPS desactivado (pulsa para activar)", "HTTPS access disabled (click to enable)"],
    ["Accès HTTPS temporaire", "Acceso HTTPS temporal", "Temporary HTTPS access"],
    ["Accès distant HTTPS", "Acceso remoto HTTPS", "HTTPS remote access"],
    ["Bientôt disponible : nom de domaine stable et permanent", "Próximamente: dominio estable y permanente", "Coming soon: a stable, permanent domain"],
    ["Saisis ce code dans l'APK.", "Escribe este código en la APK.", "Enter this code in the APK."],
    ["🔗 VOIR SUR WINDY", "🔗 VER EN WINDY", "🔗 VIEW ON WINDY"],
    ["ACQUISITION DU FLUX EN DIRECT...", "OBTENIENDO LA SEÑAL EN DIRECTO...", "ACQUIRING LIVE STREAM..."],
    ["Pour activer les flux webcams publics mondiaux en direct sur le globe :", "Para activar las webcams públicas mundiales en directo en el globo:", "To enable global public live webcams on the globe:"],
    ["Ouvrez votre fichier", "Abre tu archivo", "Open your file"],

    // 🎙 ASR y utilidades
    ["NVIDIA Nemotron 3.5 ASR — Transcription vocale 100% locale (modèle Canary-1B)", "NVIDIA Nemotron 3.5 ASR — Transcripción de voz 100% local (modelo Canary-1B)", "NVIDIA Nemotron 3.5 ASR — 100% local voice transcription (Canary-1B model)"],
    ["Vide le cache WebView2 et recharge l'interface — utile après une mise à jour", "Vacía la caché de WebView2 y recarga la interfaz — útil tras una actualización", "Clears the WebView2 cache and reloads the interface — useful after an update"],
    ["Actualiser la boîte", "Actualizar la bandeja", "Refresh the box"],
    ["Actualiser les mesures", "Actualizar las medidas", "Refresh measurements"],
    ["Glisser pour redimensionner", "Arrastra para redimensionar", "Drag to resize"],
    ["Objet de votre message...", "Asunto de tu mensaje...", "Subject of your message..."],
    ["Plein Écran", "Pantalla completa", "Fullscreen"],
    ["Plein écran", "Pantalla completa", "Fullscreen"],
    ["📅 ALERTE_DE_RENDEZ_VOUS", "📅 AVISO_DE_CITA", "📅 APPOINTMENT_ALERT"],
    ["📅 RENDEZ-VOUS & RAPPELS", "📅 CITAS Y RECORDATORIOS", "📅 APPOINTMENTS & REMINDERS"],
    ["📁 CHEMIN DU COFFRE OBSIDIAN", "📁 RUTA DE LA BÓVEDA DE OBSIDIAN", "📁 OBSIDIAN VAULT PATH"],
    ["◈ INITIALISATION DES PROTOCOLES ◈", "◈ INICIALIZANDO PROTOCOLOS ◈", " INITIALIZING PROTOCOLS ◈"],
    ["Ancrer / Détacher le navigateur", "Anclar / Soltar el navegador", "Pin / Unpin the browser"],
    ["Arrêter", "Detener", "Stop"],
    ["Exemple d'instruction :", "Ejemplo de instrucción:", "Example instruction:"],
    ["AFFICHER L'HORLOGE ET INFOS HUD (SYS_CLOCK)", "MOSTRAR EL RELOJ Y INFO DEL HUD (RELOJ_SIS)", "SHOW CLOCK AND HUD INFO (SYS_CLOCK)"],
    ["Cliquez pour renommer le mot-clé vocal", "Pulsa para renombrar la palabra clave de voz", "Click to rename the voice keyword"],
    ["Épingler sur l'interface", "Fijar en la interfaz", "Pin to the interface"],
    ["VOIX : « CORT, LANCE [NOM DU JEU] »", "VOZ: «CORT, ABRE [NOMBRE DEL JUEGO]»", "VOICE: \"CORT, LAUNCH [GAME NAME]\""],
    ["Cliquez pour parler à CORT", "Pulsa para hablar con CORT", "Click to talk to CORT"],
    ["Cliquez pour stopper CORT", "Pulsa para detener a CORT", "Click to stop CORT"],
    ["Afficher le compagnon CORT", "Mostrar el compañero CORT", "Show the CORT companion"],
    ["Vérifier et télécharger la dernière version de CORT sur techenclair.fr", "Comprobar y descargar la última versión de CORT (sin enlace externo en esta construcción)", "Check and download the latest CORT version (no external link in this build)"],
    ["Assigner un mot-clé vocal pour CORT (ex: 'salon')", "Asignar una palabra clave de voz para CORT (ej: 'salón')", "Assign a voice keyword for CORT (e.g. 'living room')"],
    ["ENREGISTRER POUR CORT", "GUARDAR PARA CORT", "SAVE FOR CORT"],
    [". Les menaces s'affichent sur le radar et la console du HUD et CORT vous alerte vocalement.", ". Las amenazas aparecen en el radar y en la consola del HUD, y CORT te avisa por voz.", ". Threats appear on the radar and the HUD console, and CORT alerts you by voice."],
    ["Intercepte, bloque et met en quarantaine automatiquement les menaces actives.", "Intercepta, bloquea y pone en cuarentena automáticamente las amenazas activas.", "Intercepts, blocks and quarantines active threats automatically."],
    ["Plus d'informations sur l'antivirus", "Más información sobre el antivirus", "More information about the antivirus"],

    // 🎮 Juegos / gestos
    ["Sphère [1]", "Esfera [1]", "Sphere [1]"],
    ["Octaèdre [6]", "Octaedro [6]", "Octahedron [6]"],
    ["Jeu balle — utilise ta main pour faire rebondir la balle", "Juego de pelota — usa tu mano para hacer rebotar la pelota", "Ball game — use your hand to bounce the ball"],
    ["Inverser les mains", "Invertir las manos", "Swap hands"],
    ["Pour le corriger : relancez", "Para corregirlo: reinicia", "To fix it: relaunch"],
    ["1. Ouvrez les", "1. Abre las", "1. Open the"],
    ["2. Activez", "2. Activa", "2. Enable"],
    ["Ex: Position à configurer", "Ej: Posición por configurar", "E.g. Position to configure"],

    // 🔑 Claves API (filas del panel)
    ["VOIX OPENAI REALTIME", "VOZ OPENAI REALTIME", "OPENAI REALTIME VOICE"],
    ["VALIDER LE CHOIX", "CONFIRMAR LA ELECCIÓN", "CONFIRM SELECTION"],
    ["CHOIX DU MODE DE TON :", "ELECCIÓN DEL MODO DE TONO:", "TONE MODE CHOICE:"],
    ["GOOGLE GEMINI API (Cerveau & Voix)", "GOOGLE GEMINI API (Cerebro y voz)", "GOOGLE GEMINI API (Brain & Voice)"],
    ["Entrez votre clé API Gemini", "Introduce tu clave API de Gemini", "Enter your Gemini API key"],
    ["Obtenir une clé API Gemini (AI Studio)", "Obtener una clave API de Gemini (AI Studio)", "Get a Gemini API key (AI Studio)"],
    ["Entrez votre clé API Groq", "Introduce tu clave API de Groq", "Enter your Groq API key"],
    ["Obtenir une clé API Groq", "Obtener una clave API de Groq", "Get a Groq API key"],
    ["Entrez votre clé API YouTube", "Introduce tu clave API de YouTube", "Enter your YouTube API key"],
    ["Obtenir une clé API YouTube (Google Cloud)", "Obtener una clave API de YouTube (Google Cloud)", "Get a YouTube API key (Google Cloud)"],
    ["Entrez votre clé API xAI", "Introduce tu clave API de xAI", "Enter your xAI API key"],
    ["Obtenir une clé API xAI (Grok)", "Obtener una clave API de xAI (Grok)", "Get an xAI API key (Grok)"],
    ["Entrez votre clé API OpenAI", "Introduce tu clave API de OpenAI", "Enter your OpenAI API key"],
    ["Obtenir une clé API OpenAI", "Obtener una clave API de OpenAI", "Get an OpenAI API key"],
    ["Entrez votre clé API SerpAPI", "Introduce tu clave API de SerpAPI", "Enter your SerpAPI API key"],
    ["Obtenir une clé API SerpAPI", "Obtener una clave API de SerpAPI", "Get a SerpAPI API key"],
    ["Entrez votre clé API Anthropic", "Introduce tu clave API de Anthropic", "Enter your Anthropic API key"],
    ["Obtenir une clé API Anthropic", "Obtener una clave API de Anthropic", "Get an Anthropic API key"],
    ["Permet d'utiliser Claude 3.5 Sonnet / Opus comme cerveau alternatif.", "Permite usar Claude 3.5 Sonnet / Opus como cerebro alternativo.", "Allows using Claude 3.5 Sonnet / Opus as an alternative brain."],
    ["Entrez votre clé API Mistral", "Introduce tu clave API de Mistral", "Enter your Mistral API key"],
    ["Obtenir une clé API Mistral", "Obtener una clave API de Mistral", "Get a Mistral API key"],

    // 🖥 Sistema operativo CORT / otros
    ["Atelier d'armures & technologie", "Taller de armaduras y tecnología", "Armor & technology workshop"],
    ["Vue spectaculaire sur la Terre", "Vista espectacular de la Tierra", "Spectacular view of Earth"],
    ["Architecture d'intelligence ambre et cyan", "Arquitectura de inteligencia ámbar y cian", "Amber and cyan intelligence architecture"],
    ["Ce projet est", "Este proyecto es", "This project is"],
    ["Laissez vide pour utiliser le dossier par défaut de CORT (", "Deja vacío para usar la carpeta predeterminada de CORT (", "Leave empty to use CORT's default folder ("],
    ["dans le dossier principal de CORT.", "en la carpeta principal de CORT.", "in CORT's main folder."],
    ["📂 OUVRIR LE DOSSIER DE CORT EN 1 CLIC", "📂 ABRIR LA CARPETA DE CORT CON 1 CLIC", "📂 OPEN CORT'S FOLDER IN 1 CLICK"],
    ["Si vous utilisez CORT depuis ses sources Python", "Si usas CORT desde sus fuentes Python", "If you run CORT from its Python sources"],
    ["Dans le dossier de CORT et son environnement Python actif, installez les composants optionnels :", "En la carpeta de CORT y su entorno Python activo, instala los componentes opcionales:", "In CORT's folder and its active Python environment, install the optional components:"],
    ["Sur Windows", "En Windows", "On Windows"],
    ["Sur Linux", "En Linux", "On Linux"],
    [", puis ouvrez-le et suivez l'installation.", ", ábrelo y sigue la instalación.", ", then open it and follow the installation."],
    ["Choisissez", "Elige", "Choose"],
    ["Alternative dans PowerShell ou un terminal :", "Alternativa en PowerShell o en una terminal:", "Alternative in PowerShell or a terminal:"],
    ["Libre Hardware Monitor depuis le projet officiel", "Libre Hardware Monitor desde el proyecto oficial", "Libre Hardware Monitor from the official project"],
    ["Alerter aussi sur une charge CPU persistante de 98 % (souvent normale pendant un jeu)", "Avisar también con una carga de CPU persistente del 98% (a menudo normal durante una partida)", "Also alert on a sustained 98% CPU load (often normal during a game)"],
    ["2. Choisir les fonctions", "2. Elegir las funciones", "2. Choose the functions"],
    ["Conversations avec l'IA locale", "Conversaciones con IA local", "Conversations with local AI"],
    ["Modèle 7 — NEXUS", "Modelo 7 — NEXUS", "Model 7 — NEXUS"],
    ["Modèle 8 — AETHER", "Modelo 8 — AETHER", "Model 8 — AETHER"],
    ["Modèle 9 — QUANTA", "Modelo 9 — QUANTA", "Model 9 — QUANTA"],
    ["Modèle 10 — FRACTURE", "Modelo 10 — FRACTURE", "Model 10 — FRACTURE"],
    ["Modèle 11 — CHROMA", "Modelo 11 — CHROMA", "Model 11 — CHROMA"],
    ["Modèle 13 — PULSE", "Modelo 13 — PULSE", "Model 13 — PULSE"],
    ["Modèle 14 — NOVA", "Modelo 14 — NOVA", "Model 14 — NOVA"],
    ["Modèle 15 — SPECTRA", "Modelo 15 — SPECTRA", "Model 15 — SPECTRA"],
    ["Modèle 16 — ECHO", "Modelo 16 — ECHO", "Model 16 — ECHO"],
    ["et le", "y el", "and the"]
  ];

  // ---- 2a-sexies. Cierre: lo que quedaba pendiente tras la medición (28) ----
  const D_EXT5 = [
    ["WINDY_API_KEY=votre_cle_ici", "WINDY_API_KEY=tu_clave_aqui", "WINDY_API_KEY=your_key_here"],
    ["📖 OUVRIR LE GUIDE DE CONFIGURATION GMAIL", "📖 ABRIR LA GUÍA DE CONFIGURACIÓN DE GMAIL", "📖 OPEN THE GMAIL SETUP GUIDE"],
    ["1. Rendez-vous sur la", "1. Ve a la", "1. Go to the"],
    ["3. Allez dans", "3. Entra en", "3. Go to"],
    ["4. Cliquez sur", "4. Pulsa en", "4. Click on"],
    ["(Type d'application :", "(Tipo de aplicación:", "(Application type:"],
    ["Glissez votre fichier", "Arrastra tu archivo", "Drag your file"],
    ["Cliquez sur le lien ci-dessous et appuyez sur le bouton bleu", "Pulsa el enlace de abajo y luego el botón azul", "Click the link below and press the blue button"],
    ["🔗 ACTIVER L'API GMAIL (GOOGLE CLOUD)", "🔗 ACTIVAR LA API DE GMAIL (GOOGLE CLOUD)", "🔗 ENABLE THE GMAIL API (GOOGLE CLOUD)"],
    ["Enregistrer l'IA locale", "Guardar la IA local", "Save local AI"],
    ["Sous Linux Debian/Ubuntu avec X11, les actions sur les fenêtres nécessitent également", "En Linux Debian/Ubuntu con X11, las acciones sobre ventanas requieren además", "On Debian/Ubuntu Linux with X11, window actions also require"],
    ["ollama stop NOM_DU_MODELE", "ollama stop NOMBRE_DEL_MODELO", "ollama stop MODEL_NAME"],
    ["ollama rm NOM_DU_MODELE", "ollama rm NOMBRE_DEL_MODELO", "ollama rm MODEL_NAME"],
    ["Obtenir une clé API Mistral AI", "Obtener una clave API de Mistral AI", "Get a Mistral AI API key"],
    ["WINDY API (Webcams Live du Monde)", "WINDY API (Webcams en Vivo del Mundo)", "WINDY API (World Live Webcams)"],
    ["Entrez votre clé API Windy Webcams", "Introduce tu clave API de Windy Webcams", "Enter your Windy Webcams API key"],
    ["Obtenir une clé API Windy Webcams (Gratuit)", "Obtener una clave API de Windy Webcams (Gratis)", "Get a Windy Webcams API key (Free)"],
    ["Entrez votre clé API ElevenLabs", "Introduce tu clave API de ElevenLabs", "Enter your ElevenLabs API key"],
    ["Obtenir une clé API ElevenLabs", "Obtener una clave API de ElevenLabs", "Get an ElevenLabs API key"],
    ["Détection du matériel en cours...", "Detectando el hardware...", "Detecting hardware..."],
    ["Volume requis :", "Volumen requerido:", "Required volume:"],
    ["LANCER L'INSTALLATION AUTOMATIQUE", "INICIAR LA INSTALACIÓN AUTOMÁTICA", "START AUTOMATIC INSTALLATION"],
    ["🔍 Trois niveaux d'analyse :", "🔍 Tres niveles de análisis:", "🔍 Three analysis levels:"],
    ["Plein écran panneau", "Pantalla completa del panel", "Panel fullscreen"],
    ["Ouvrir fichier vidéo ou playlist", "Abrir archivo de vídeo o playlist", "Open video file or playlist"],
    ["Tous les groupes", "Todos los grupos", "All groups"],
    ["CHARGEMENT DU FLUX...", "CARGANDO LA SEÑAL...", "LOADING STREAM..."],
    ["Plein écran vidéo", "Pantalla completa del vídeo", "Video fullscreen"]
  ];

  // ---- 2a-septies. Cierre real: las 59 cadenas francesas que quedaban --------
  // Con el clasificador anterior («esFrances» ignoraba el francés sin tilde y unas
  // cuantas palabras corrientes) el panel presumía «cobertura 100 %» mientras el
  // menú mostraba «◈ CONTROLES_SYSTEME // MENU» e «INTELLIGENCE ARTIFICIELLE».
  // Medido paso a paso: 36 pendientes tras arreglar el clasificador y 23 más tras
  // ampliarlo con chargement / configuration / suivant / attente / modèle / caméra.
  // Las 59 vienen de window.CORT.estado() en la arena, no de una lista propia.
  const D_EXT6 = [
    // Menú y rótulos de sección
    ["◈ CONTROLES_SYSTEME // MENU", "◈ CONTROLES_SISTEMA // MENÚ", "◈ SYSTEM_CONTROLS // MENU"],
    ["INTELLIGENCE ARTIFICIELLE", "INTELIGENCIA ARTIFICIAL", "ARTIFICIAL INTELLIGENCE"],
    ["Outils", "Herramientas", "Tools"],
    ["Recherche...", "Buscar...", "Search..."],
    ["SAUVEGARDER & ENREGISTRER", "GUARDAR Y REGISTRAR", "SAVE & REGISTER"],
    ["SUPPRIMER", "ELIMINAR", "DELETE"],
    ["AJOUTER", "AÑADIR", "ADD"],
    ["Carte graphique", "Tarjeta gráfica", "Graphics card"],

    // Cronómetro y estado del puente
    ["Protocol Minuteur Actif", "Protocolo de temporizador activo", "Timer protocol active"],
    ["CONNEXION AU SERVEUR EN COURS...", "CONECTANDO AL SERVIDOR...", "CONNECTING TO SERVER..."],

    // Correo
    ["COMMUNICATION // NOUVEAU_MESSAGE", "COMUNICACIÓN // MENSAJE_NUEVO", "COMMUNICATION // NEW_MESSAGE"],
    ["Rechercher par expéditeur, sujet ou contenu... (Entrée = recherche Gmail)",
      "Buscar por remitente, asunto o contenido... (Enter = búsqueda de Gmail)",
      "Search by sender, subject or content... (Enter = Gmail search)"],

    // Lista de la compra
    ["Ajouter un article...", "Añadir un artículo...", "Add an item..."],

    // Impresión 3D / lithophanie
    ["LITHOPHANIE (PHOTO)", "LITOFANÍA (FOTO)", "LITHOPHANE (PHOTO)"],
    ["🔲 Plat (Cadre photo)", "🔲 Plano (Marco de foto)", "🔲 Flat (Photo frame)"],
    ["📷 PHOTO HD", "📷 FOTO HD", "📷 HD PHOTO"],

    // Voz local
    ["🚀 INSTALLER & LANCER KOKORO-TTS LOCAL", "🚀 INSTALAR Y ABRIR KOKORO-TTS LOCAL", "🚀 INSTALL & LAUNCH LOCAL KOKORO-TTS"],
    ["INSTALLER NVIDIA NEMOTRON ASR (LOCAL)", "INSTALAR NVIDIA NEMOTRON ASR (LOCAL)", "INSTALL NVIDIA NEMOTRON ASR (LOCAL)"],

    // Panel de salud de la IA
    ["B. Installer Ollama", "B. Instalar Ollama", "B. Install Ollama"],
    ["YOUTUBE API v3 (Recherche de musique)", "API de YOUTUBE v3 (Búsqueda de música)", "YOUTUBE API v3 (Music search)"],
    ["Lecture / Pause", "Reproducir / Pausa", "Play / Pause"],

    // Catálogo de órdenes de voz: se traduce lo que CORT dice, no lo que escucha
    ["Mets un minuteur de [X] minutes", "Pon un temporizador de [X] minutos", "Set a timer for [X] minutes"],
    ["Lance un minuteur visuel + vocal", "Inicia un temporizador visual y por voz", "Starts a visual + spoken timer"],
    ["Efface toute la liste", "Borra toda la lista", "Clears the whole list"],
    ["🎵 MUSIQUE — SPOTIFY", "🎵 MÚSICA — SPOTIFY", "🎵 MUSIC — SPOTIFY"],
    ["Mets de la musique", "Pon música", "Play some music"],
    ["Mets en pause / Stop la musique", "Pon en pausa / Detén la música", "Pause / Stop the music"],
    ["Remets la musique / Lecture", "Reanuda la música / Reproducir", "Resume the music / Play"],
    ["Reprend la lecture", "Reanuda la reproducción", "Resumes playback"],
    ["Chanson suivante / Piste suivante", "Canción siguiente / Pista siguiente", "Next song / Next track"],
    ["Volume Spotify", "Volumen de Spotify", "Spotify volume"],
    ["Tendances YouTube musique / gaming...", "Tendencias de YouTube música / gaming...", "YouTube music / gaming trends..."],
    ["Ouvre mes images / photos", "Abre mis imágenes / fotos", "Open my images / photos"],
    ["Ouvre ma musique", "Abre mi música", "Open my music"],
    ["Analyse cette image", "Analiza esta imagen", "Analyze this image"],

    // Segunda pasada (23 más): al ampliar el clasificador con «chargement»,
    // «configuration», «suivant», «attente», «modèle» o «caméra» salieron estas,
    // que estaban en paneles ocultos y el medidor viejo ni contaba.
    ["IP : Chargement...", "IP: Cargando...", "IP: Loading..."],
    ["Titre de la note...", "Título de la nota...", "Note title..."],
    ["Titre", "Título", "Title"],
    ["Titre suivant", "Título siguiente", "Next title"],
    ["SUIVANT »", "SIGUIENTE »", "NEXT »"],
    ["Suivant", "Siguiente", "Next"],
    ["PRECEDENT", "ANTERIOR", "PREVIOUS"],
    ["Précédent", "Anterior", "Previous"],
    ["CHARGEMENT... 0%", "CARGANDO... 0%", "LOADING... 0%"],
    ["CHARGEMENT... 100%", "CARGANDO... 100%", "LOADING... 100%"],
    ["ERREUR DE CHARGEMENT", "ERROR DE CARGA", "LOADING ERROR"],
    ["VIDER CACHE / RECHARGER", "VACIAR CACHÉ / RECARGAR", "CLEAR CACHE / RELOAD"],
    ["AGENT MODELE", "MODELO DE AGENTE", "AGENT MODEL"],
    ["CLAUDE CODE — AGENT LOCAL OPTIONNEL", "CLAUDE CODE — AGENTE LOCAL OPCIONAL", "CLAUDE CODE — OPTIONAL LOCAL AGENT"],
    ["VERSION 10.5", "VERSIÓN 10.5", "VERSION 10.5"],
    ["Effacer tout [Suppr]", "Borrar todo [Supr]", "Clear all [Del]"],
    ["Chatterbox en attente...", "Chatterbox en espera...", "Chatterbox on hold..."],
    ["◈ EN ATTENTE", "◈ EN ESPERA", "◈ ON HOLD"],
    ["📧 GUIDE DE CONFIGURATION GMAIL", "📧 GUÍA DE CONFIGURACIÓN DE GMAIL", "📧 GMAIL SETUP GUIDE"],
    ["🔑 CONFIGURATION API", "🔑 CONFIGURACIÓN DE LA API", "🔑 API SETUP"],
    ["Processeur", "Procesador", "Processor"],
    ["Efface mes notes", "Borra mis notas", "Clear my notes"],
    ["Vide la to-do list", "Vacía la lista de tareas", "Clears the to-do list"],
    ["Fais-moi un rap / pop / rock...", "Hazme un rap / pop / rock...", "Make me a rap / pop / rock..."]
  ];

  // ---- 2b. Reglas para rótulos dinámicos -----------------------------------
  // El nombre de la voz llega del backend y la app le pega un sufijo francés
  // fixed, así que ninguna clave exacta del diccionario puede cubrirlo.
  // Aquí se reemplaza sólo el fragmento francés y se conserva el nombre propio.
  const REGRAS = [
    // Rótulos que el bundle escribe con un sufijo dinámico pegado («Caméra (…)») o
    // en tiempo real durante la instalación de Ollama: la clave exacta del
    // diccionario no los alcanza, pero la palabra sí está y se sustituye suelta.
    [/(?<![\p{L}])Caméra(?![\p{L}])/u, { es: "Cámara", en: "Camera" }],
    [/(?<![\p{L}])Installation terminée(?![\p{L}])/u, { es: "Instalación terminada", en: "Installation complete" }],
    [/(?<![\p{L}])Installation en cours(?![\p{L}])/u, { es: "Instalación en curso", en: "Installation in progress" }],
    [/(?<![\p{L}])Téléchargement terminé(?![\p{L}])/u, { es: "Descarga terminada", en: "Download complete" }],
    // Porcentaje de descarga: el número lo pone el progreso real, así que la clave
    // exacta del diccionario sólo valdría para 0 % y 100 %.
    [/(?<![\p{L}])CHARGEMENT\.\.\.\s*(\d+)\s*%/gu, { es: "CARGANDO... $1%", en: "LOADING... $1%" }],
    [/(?<![\p{L}])Chargement(?![\p{L}])/u, { es: "Cargando", en: "Loading" }],
    // Contador del correo: el número llega del backend, así que la clave exacta
    // del diccionario sólo cubriría «0 messages». Con regla queda cubierto cualquier conteo.
    [/(?<![\p{L}])(\d+) messages(?![\p{L}])/gu, { es: "$1 mensajes", en: "$1 messages" }],
    // Panel «Configurar la IA local / Ollama»: estas cuatro etiquetas las escribe
    // el bundle en francés dentro de un nodo con más texto, así que el diccionario
    // no las alcanza. Se detectaron abriendo el panel y recorriendo sus nodos de
    // texto (antes no se medían porque el panel sólo existe al abrirlo).
    // Etiquetas del panel de notas (F4): van en el mismo nodo que la fecha y el
    // tamaño medidos, así que solo las reglas las alcanzan.
    [/MODIFIÉ\s*:/g, { es: "MODIFICADO:", en: "MODIFIED:" }],
    [/TAILLE\s*:/g, { es: "TAMAÑO:", en: "SIZE:" }],
    [/Aucune note/g, { es: "Ninguna nota", en: "No notes" }],
    [/Date inconnue/g, { es: "Fecha desconocida", en: "Unknown date" }],
    [/OPTION FACULTATIVE/g, { es: "OPCIÓN OPCIONAL", en: "OPTIONAL" }],
    [/Connexion…|Connexion\.\.\./g, { es: "Conectando…", en: "Connecting…" }],
    [/Enregistrer la surveillance/g, { es: "Guardar la vigilancia", en: "Save monitoring" }],
    [/\bIA locale\b/g, { es: "IA local", en: "Local AI" }],
    [/ElevenLabs Ultra-Réel/g, { es: "ElevenLabs ultrarrealista", en: "ElevenLabs ultra-realistic" }],
    [/\(M\)(?=\s*—)/g, { es: "(voz de hombre)", en: "(M)" }],
    [/\(F\)(?=\s*—)/g, { es: "(voz de mujer)", en: "(F)" }],
    [/\bFrançais\b/g, { es: "Francés", en: "French" }],
    // Etiquetas del panel de antivirus: el bundle las escribe en francés y unas
    // van en nodos completos (casan con el diccionario), otras dentro de una línea
    // con datos dinámicos (solo las reglas las alcanzan).
    [/\[NOYAU\]/g, { es: "[NÚCLEO]", en: "[CORE]" }],
    [/\[FICHIER\]/g, { es: "[ARCHIVO]", en: "[FILE]" }],
    [/\[PROCESSUS\]/g, { es: "[PROCESOS]", en: "[PROCESSES]" }],
    // Sin la bandera `u`, \b corta mal delante de «é»: «sécurité » no tiene borde
    // de palabra ASCII y la regla nunca casaba (así se descubrió midiendo).
    [/(?<![\p{L}])Initialisation du système de sécurité(?![\p{L}])/gu,
      { es: "Iniciando el sistema de seguridad", en: "Security system starting" }],
    [/\[TERMINE\]/g, { es: "[TERMINADO]", en: "[DONE]" }],
    [/(?<![\p{L}])Analyse terminée(?![\p{L}])\. ?(?<![\p{L}])Aucune menace détectée(?![\p{L}])\. ?(?<![\p{L}])Système entièrement sécurisé(?![\p{L}])\./gu,
      { es: "Análisis terminado. Ninguna amenaza detectada. Sistema completamente seguro.",
        en: "Scan complete. No threat detected. System fully secure." }],
    [/(?<![\p{L}])Analyse terminée(?![\p{L}])/gu, { es: "Análisis terminado", en: "Scan complete" }],
    [/(?<![\p{L}])Aucune menace détectée(?![\p{L}])/gu, { es: "Ninguna amenaza detectada", en: "No threat detected" }],
    [/(?<![\p{L}])Système entièrement sécurisé(?![\p{L}])/gu,
      { es: "Sistema completamente seguro", en: "System fully secure" }],
    [/\bSYS_STATUS:\s*SAIN\b/g, { es: "ESTADO_SIS: SANO", en: "SYS_STATUS: CLEAN" }],
    [/\bSAIN\b/g, { es: "SANO", en: "CLEAN" }],
    [/\bWEBCAMS REQUERIDA\b/g, { es: "WEBCAMS NECESARIA", en: "WEBCAMS REQUIRED" }],
    // Registro del antivirus: el bundle arma las líneas en francés con campos del
    // puente dentro. Se traducen las plantillas, no los datos.
    [/\[REGISTRE\]/g, { es: "[REGISTRO]", en: "[REGISTRY]" }],
    [/\[DANGER\]/g, { es: "[PELIGRO]", en: "[DANGER]" }],
    [/(?<![\p{L}])Menace d[ée]tect[ée]e(?![\p{L}])/gu, { es: "Amenaza detectada", en: "Threat detected" }],
    [/(?<![\p{L}])MENACES D[ÉE]TECT[ÉE]ES(?![\p{L}])/gu, { es: "AMENAZAS DETECTADAS", en: "THREATS DETECTED" }],
    [/(?<![\p{L}])Menaces d[ÉE]tect[ÉE]es(?![\p{L}])/gu, { es: "Amenazas detectadas", en: "Threats detected" }],
    [/(?<![\p{L}])Analyse termin[ée]e(?![\p{L}])/gu, { es: "Análisis terminado", en: "Scan complete" }],
    [/\bFERMER\b/g, { es: "CERRAR", en: "CLOSE" }],
    [/\bSYS_STATUS: VULN[ÉE]RABLE\b/g, { es: "ESTADO_SIS: VULNERABLE", en: "SYS_STATUS: VULNERABLE" }],
    [/\bSYS_STATUS:\s*([A-Z_]+)_SCAN\b/g, { es: "ESTADO_SIS: $1", en: "SYS_STATUS: $1_SCAN" }]
  ];

  const DICT = new Map();
  for (const [fr, es, en] of D.concat(D_EXT, D_EXT2, D_EXT3, D_EXT4, D_EXT5, D_EXT6)) DICT.set(norm(fr), { es: norm(es), fr: norm(fr), en: norm(en) });

  let lang = localStorage.getItem("cort_lang") || "es";

  function porReglas(s) {
    if (lang === "fr") return s;
    let out = s, tocado = false;
    for (const [re, tr] of REGRAS) {
      if (re.test(out)) { out = out.replace(re, tr[lang]); tocado = true; }
    }
    return tocado ? out : s;
  }

  function translate(raw) {
    const s = brand(raw);
    if (lang === "fr") return s;
    const k = norm(s);
    let hit = DICT.get(k);
    if (!hit) {
      const { a, b, cuerpo } = descomillar(k);
      if (a || b) {
        const h = DICT.get(norm(cuerpo));
        if (h) return a + h[lang] + b;
      }
      return porReglas(s);
    }
    return porReglas(hit[lang]);
  }

  // ---- 2c. Firma francesa ---------------------------------------------------
  // Para medir de forma honesta hace falta distinguir "esto está en francés"
  // de "esto ya está en español / es un nombre propio / es código".
  // Criterio: letras que el español no usa, o palabras exclusivas del francés.
  // «é» NO entra en esta lista a propósito: el español la lleva en «café», «esté»,
  // en el pretérito «hablé/miré» y en el voseo («encendé»), así que usarla como firma
  // francesa habría contado como pendiente mucho texto que ya es español. Los términos
  // franceses con tilde se reconocen uno a uno en PALABRAS_FR con la forma [eé].
  const LETRAS_FR = /[àâçèêëïîôùûüÿœæÀÂÇÈÊËÏÎÔÙÛÜŸŒÆ]/;
  // Bordes de palabra con \p{L}: sin la bandera `u`, "est" casaba dentro de
  // "esté" o "Estética" y el medidor contaba como francés lo ya traducido.
  // Palabras francesas SIN tilde también: el andamio de TechEnClair escribe
  // «SYSTEME», «ARTIFICIELLE», «MINUTEUR» o «RECHERCHE» sin acentos en los rótulos
  // en mayúsculas, y sin esta lista el medidor no las contaba como francesas y
  // presumía «cobertura 100%» con texto francés visible en el menú. Quedan fuera
  // a propósito las grafías que son palabra española igual («tres», «video»,
  // «micro», «agenda», «carte», «liste», «listas», «tache», «retro»): un falso
  // positivo aquí ensucia la lista de pendientes y el número deja de ser creíble.
  const PALABRAS_FR = /(?<![\p{L}])(une|des|du|au|aux|votre|vos|notre|nos|nous|vous|ils|elles|est|sont|être|été|avoir|avec|dans|sur|chez|vers|pour|mais|donc|car|quand|comment|combien|très|aussi|encore|déjà|cliquez|choisissez|activez|vérifiez|téléchargez|modèle|paramètres|dossier|fichier|écran|lumière|voix|requis|nécessaire|français|française|allez|faites|pouvez|êtes|systeme|systemes|artificielle|intelligence|minuteur|minuteurs|recherche|recherches|supprimer|ajouter|graphique|graphiques|protocole|programme|programmes|solliciter|priorite|priorites|connexion|serveur|visionner|monde|langage|affichage|verrouillage|nettoyage|securite|enregistrer|sauvegarde|dynamique|toujours|jamais|bienvenue|boite|outils|fenetre|fenetres|message|messages|envoyer|recu|recus|correspondance|calendrier|taches|alarmes|eclairage|volume|haut|parleur|dangereux|menace|menaces|analyse|analyser|scanner|nettoyer|desinstaller|installer|mise jour|mises jour|pays|region|regions|ville|villes|mobilite|batterie|reseau|wifi|bluetooth|camera|cameras|photo|photos|musique|chanson|chansons|lecture|arret|demarrage|lancement|telechargement|telecharger|toute|toutes|certains|aucun|aucune|rien|quelque|beaucoup|peu|chargement|configuration|processeur|cam[ée]ra|cam[ée]ras|s[ée]curit[ée]|lithophanie|suivant|suivante|suivants|pr[ée]c[ée]dent|pr[ée]c[ée]dente|pr[ée]c[ée]dents|attente|mod[èe]le|mod[èe]les|titre|titres|agent|agents|efface|effacer|vide|vider|fais|faire|traitement|r[ée]glage|r[ée]glages|version|versions|identit[ée]|m[ée]moire|resultat|resultats|surbrillance|termin[ée]e|d[ée]tect[ée]e|install[ée]|d[ée]sinstall[ée]|d[ée]marrage|d[ée]connexion|deconnexion|installation|d[ée]sinstallation|desinstallation|activation|d[ée]sactivation|desactivation|danger)(?![\p{L}])/iu;
  const ELISION_FR = /(?<![\p{L}])(d|l|qu|n|s|c|j|t|il)['\u2019]\p{L}/iu;
  function esFrances(s) {
    return LETRAS_FR.test(s) || PALABRAS_FR.test(s) || ELISION_FR.test(s);
  }

  // ---- 3. Aplicar al DOM ---------------------------------------------------
  const ATTRS = ["title", "placeholder", "aria-label", "alt"];
  // Nunca se toca el interior de <script>/<style>/<textarea>: son texto del
  // documento, no interfaz. Sin esta exclusión el medidor contaba código
  // embebido como "francés sin traducir" y cualquier reescritura ahí sería un
  // riesgo para el comportamiento de la app.
  const NO_TOCAR = ["SCRIPT", "STYLE", "TEXTAREA", "TITLE"];
  let vistas = new Set(), traducidas = new Set(), pendientes = new Set();
  let fr_vistas = new Set(), fr_traducidas = new Set();

  function cuenta(key, salio) {
    vistas.add(key);
    const fr = esFrances(key);
    if (fr) fr_vistas.add(key);
    if (salio) { traducidas.add(key); if (fr) fr_traducidas.add(key); }
    else if (fr) pendientes.add(key);
  }

  function applyTo(node) {
    if (node.nodeType === 3) {
      const raw = node.nodeValue;
      if (!raw || !raw.trim()) return;
      // Memoria por nodo: el repaso de seguridad recorre el documento cada 3 s y
      // aquí es donde se iba el tiempo (medido: 150-462 ms por pasada, y eso
      // hundía el orbe a 8-9 FPS en la Canaima). Si el texto del nodo es idéntico
      // al que ya dejamos escrito, no se vuelve a mirar ni un regex.
      if (node._cort === raw) return;
      const p = node.parentNode;
      if (p && (NO_TOCAR.includes(p.tagName) || p.closest?.("script,style,textarea"))) {
        node._cort = raw;
        return;
      }
      // El nodo suele ser un trozo de frase ("1. Ouvrez les " + "Configuración…"):
      // si no devolvemos los espacios del borde, las palabras se pegan.
      const lead = (raw.match(/^\s*/) || [""])[0];
      const trail = (raw.match(/\s*$/) || [""])[0];
      const cuerpo = raw.slice(lead.length, raw.length - trail.length);
      const out = lead + translate(cuerpo) + trail;
      const key = norm(cuerpo);
      if (key.length > 1) {
        cuenta(key, out !== raw);
        if (out !== raw) node.nodeValue = out;
        node._cort = out;
      }
      return;
    }
    if (node.nodeType !== 1) return;
    if (NO_TOCAR.includes(node.tagName)) return;
    for (const a of ATTRS) {
      const v = node.getAttribute(a);
      if (!v) continue;
      const out = translate(v);
      if (out !== v) { node.setAttribute(a, out); cuenta(norm(v), true); }
      else if (esFrances(norm(v))) pendientes.add(norm(v));
    }
  }

  function walk(root) {
    if (!root || !root.ownerDocument) root = document.body;
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, null);
    let n;
    while ((n = w.nextNode())) applyTo(n);
  }

  // ---- 4. Voz en español ---------------------------------------------------
  const U = window.SpeechSynthesisUtterance;
  if (U) {
    window.SpeechSynthesisUtterance = function (text) {
      const u = new U(translate(text));
      u.lang = lang === "es" ? "es-ES" : lang === "en" ? "en-US" : "fr-FR";
      return u;
    };
    window.SpeechSynthesisUtterance.prototype = U.prototype;
  }

  // ---- 5. Idiomas: español por defecto; es / fr / en se cambian EN AJUSTES --
  const IDIOMAS = ["es", "fr", "en"];
  const NOMBRE_IDIOMA = { es: "Español", fr: "Français", en: "English" };

  function setLang(l) {
    if (!IDIOMAS.includes(l)) return;
    lang = l;
    localStorage.setItem("cort_lang", lang);
    document.documentElement.lang = lang;
    document.title = translate(document.title || "CORT");
    walk(document.body);
    pintarFilaIdioma();
    const chip = document.getElementById("cort-boot-lang");
    if (chip) chip.textContent = lang.toUpperCase();
  }
  window.CORT_setLang = setLang;

  // Fila dentro del panel de Ajustes. El modal es un flex con
  // `.settings-container` dentro: si insertáramos en el modal, la fila saldría
  // como un panel suelto a la izquierda (así se detectó midiéndolo).
  function asegurarFilaIdioma() {
    const panel = document.querySelector("#settings-modal .settings-container");
    if (!panel) return false;
    const fila = document.getElementById("cort-lang-row");
    if (fila && panel.contains(fila)) return true;
    const nuevo = fila || document.createElement("div");
    nuevo.id = "cort-lang-row";
    const cabecera = panel.querySelector(".settings-header");
    if (cabecera && cabecera.parentElement === panel) panel.insertBefore(nuevo, cabecera.nextSibling);
    else panel.insertBefore(nuevo, panel.firstChild);
    pintarFilaIdioma();
    return true;
  }

  function pintarFilaIdioma() {
    const fila = document.getElementById("cort-lang-row");
    if (!fila) return;
    fila.innerHTML = '<span>IDIOMA&nbsp;//</span>';
    for (const l of IDIOMAS) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cort-lang-btn";
      b.textContent = NOMBRE_IDIOMA[l];
      b.dataset.activo = l === lang ? "1" : "0";
      b.addEventListener("click", () => setLang(l));
      fila.appendChild(b);
    }
  }

  // ---- 5b. Fila del cerebro: qué modelos hay en el equipo y qué falta para usarlos
  //
  // Todo lo que pinta sale del puente (`en_disco`, `ram_disponible_mb`, `catalogo`).
  // Si el puente no ha contestado todavía, la fila lo dice en voz alta en vez de
  // suponer modelos: la lista que traía la demo (dolphin3, phi3.5, llama3.1:8b) está
  // escrita a mano y ninguno de esos tres existe en esta laptop.
  let estadoCerebro = null;

  function chipTexto(t, clase) {
    const s = document.createElement("span");
    s.className = "cort-cerebro-chip" + (clase ? " " + clase : "");
    s.textContent = t;
    return s;
  }

  function botonCerebro(texto, fn, opts) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cort-cerebro-btn";
    b.textContent = texto;
    if (opts && opts.titulo) b.title = opts.titulo;
    if (opts && opts.noCabe) b.dataset.noCabe = "1";
    if (opts && opts.activo) b.dataset.activo = "1";
    b.addEventListener("click", fn);
    return b;
  }

  function revelarPanelModelos() {
    const sel = document.getElementById("settings-preferred-brain");
    if (sel) {
      sel.value = "local_uncensored";
      sel.dispatchEvent(new Event("change", { bubbles: true }));
    }
    // El selector de modelo vive dentro de #agent-model-modal, que está cerrado
    // hasta que se pulsa su botón del menú. Poner el `wrap` a display:block no lo
    // mostraba nada: el padre seguía en none (medido: altura 0 px). Se pulsa el
    // botón real, que es lo que abre el modal de verdad.
    const boton = document.getElementById("agent-modele-btn");
    const modal = document.getElementById("agent-model-modal");
    if (boton && (!modal || getComputedStyle(modal).display === "none")) boton.click();
    const wrap = document.getElementById("local-model-selector-wrap");
    if (wrap) wrap.style.display = "block";
    if (typeof window.CORT_pedirEstadoCerebro === "function") window.CORT_pedirEstadoCerebro();
  }

  function elegirModelo(nombre) {
    const radio = document.querySelector('input[name="local_model_choice"][value="' + nombre + '"]');
    if (radio) radio.checked = true;
    revelarPanelModelos();
    if (typeof window.CORT_enviarAlCerebro === "function") {
      window.CORT_enviarAlCerebro({ type: "set_local_model", model: nombre });
    }
  }

  function descargarModelo(nombre) {
    revelarPanelModelos();
    if (typeof window.CORT_enviarAlCerebro === "function") {
      window.CORT_enviarAlCerebro({ type: "pull_ollama_model", model: nombre });
    }
  }

  function asegurarFilaCerebro() {
    const panel = document.querySelector("#settings-modal .settings-container");
    if (!panel) return false;
    let fila = document.getElementById("cort-cerebro-row");
    if (fila && panel.contains(fila)) return true;
    if (!fila) fila = document.createElement("div");
    fila.id = "cort-cerebro-row";
    const filaIdioma = document.getElementById("cort-lang-row");
    if (filaIdioma) panel.insertBefore(fila, filaIdioma.nextSibling);
    else {
      const cab = panel.querySelector(".settings-header");
      panel.insertBefore(fila, cab ? cab.nextSibling : panel.firstChild);
    }
    pintarFilaCerebro();
    return true;
  }

  function pintarFilaCerebro() {
    const fila = document.getElementById("cort-cerebro-row");
    if (!fila) return;
    fila.innerHTML = "";
    const titulo = document.createElement("span");
    titulo.textContent = "CEREBRO //";
    fila.appendChild(titulo);

    const st = estadoCerebro;
    if (!st) {
      fila.appendChild(chipTexto("sin datos del puente", "aviso"));
      if (typeof window.CORT_pedirEstadoCerebro === "function") {
        fila.appendChild(botonCerebro("Preguntar al puente", () => window.CORT_pedirEstadoCerebro()));
      }
      return;
    }

    const libre = st.ram_disponible_mb || 0;
    fila.appendChild(chipTexto(st.online ? "Ollama vivo" : "Ollama apagado", st.online ? "ok" : "aviso"));
    fila.appendChild(chipTexto(libre + " MB libres de " + (st.ram_total_mb || "?")));
    fila.appendChild(chipTexto((st.nucleos || "?") + " núcleos"));
    if (st.selected_model) {
      fila.appendChild(chipTexto("elegido: " + st.selected_model, "ok"));
    }

    const disco = st.en_disco || {};
    const nombres = Object.keys(disco).sort((a, b) => disco[a].ram_est - disco[b].ram_est);
    let cabeAlguno = false;
    for (const n of nombres.slice(0, 4)) {
      const d = disco[n];
      const cabe = libre >= d.ram_est;
      if (cabe) cabeAlguno = true;
      fila.appendChild(botonCerebro(
        n + " · " + d.mb + " MB",
        () => elegirModelo(n),
        {
          noCabe: !cabe,
          activo: st.selected_model === n,
          titulo: (cabe ? "Cabe ahora (~" + d.ram_est + " MB que pide tienes)"
                        : "Pide ~" + d.ram_est + " MB y hay " + libre +
                          ": cierra navegador y editor, o usa el turno de noche") +
            " · peso medido " + d.mb + " MB"
        }
      ));
    }

    const catalog = st.catalogo || {};
    const porBajar = Object.keys(catalog)
      .filter(n => !catalog[n].instalado)
      .sort((a, b) => (catalog[a].mb || 0) - (catalog[b].mb || 0))
      .slice(0, 2);
    for (const n of porBajar) {
      fila.appendChild(botonCerebro("↓ " + n, () => descargarModelo(n),
        { titulo: "Bajar " + n + " (" + (catalog[n].tam || "tamaño sin medir") + "). " +
          "Gasta disco, no RAM: se puede durante el turno de noche." }));
    }

    fila.appendChild(botonCerebro("Panel de modelos", revelarPanelModelos,
      { titulo: "Abre el selector de la interfaz con el cerebro local activado" }));

    if (!cabeAlguno && nombres.length) {
      const falta = disco[nombres[0]].ram_est;
      fila.appendChild(chipTexto(
        "ninguno cabe con " + libre + " MB: el más ligero pide ~" + falta +
        " (estimación sobre su peso). Turno de noche: ./cort_cerebro.sh", "aviso"));
    }
  }

  // Lo llama cort-mock.js cada vez que llega un estado del puente.
  window.CORT_alEstadoCerebro = (st) => {
    estadoCerebro = st || null;
    rotuloCerebro(estadoCerebro);
    pintarFilaCerebro();
  };

  function rotuloCerebro(st) {
    const e = document.getElementById("model-status-text");
    if (!e) return;
    // La maqueta escribe «gemini» por defecto y CORT no usa nubes: el rótulo tiene
    // que decir qué modelo tiene el puente, y si no tiene ninguno, decirlo.
    e.textContent = !st ? "cerebro: sin datos del puente"
      : (st.online && st.selected_model) ? `cerebro: ${st.selected_model}`
      : st.online ? "cerebro: Ollama vivo · ningún modelo cargado"
      : "cerebro: Ollama apagado";
  }

  // Único sitio donde se cambia de idioma durante el arranque: una esquina del
  // overlay, para poder elegir español/francés/inglés antes del primer render.
  function buildBootChip() {
    const boot = document.getElementById("boot-overlay");
    if (!boot || document.getElementById("cort-boot-lang")) return;
    const chip = document.createElement("button");
    chip.id = "cort-boot-lang";
    chip.type = "button";
    chip.textContent = lang.toUpperCase();
    chip.title = "IDIOMES: " + IDIOMAS.map(l => NOMBRE_IDIOMA[l]).join(" · ");
    chip.style.cssText =
      "position:absolute;bottom:44px;right:18px;z-index:40;padding:6px 10px;" +
      "font:700 10px/1 'Courier New',monospace;letter-spacing:.18em;" +
      "color:#03070d;border:0;cursor:pointer;" +
      "background:linear-gradient(135deg,#00ffc8,#22e5ff 70%);" +
      "clip-path:polygon(0 0,100% 0,100% 70%,calc(100% - 8px) 100%,0 100%);";
    let idx = IDIOMAS.indexOf(lang);
    chip.addEventListener("click", () => {
      idx = (idx + 1) % IDIOMAS.length;
      setLang(IDIOMAS[idx]);
    });
    boot.appendChild(chip);
  }

  // ---- 5bis. F1: que ningún panel mienta ni se quede girando ---------------
  // El puente (cort-bridge/cort_server.py) responde ahora a TODAS las órdenes: o
  // con un dato medido, o con un `puente_aviso` que dice el motivo exacto y qué
  // haría falta. Esta parte lo pinta dentro del panel que corresponde, para que
  // la respuesta se vea donde estaba la pregunta y no perdida en los subtítulos.
  const avisosVistos = {};
  let ultimaTemperatura = null;

  function avisoTexto(a) {
    const partes = [];
    if (a.motivo) partes.push(a.motivo);
    if (a.nota && a.nota !== a.motivo) partes.push(a.nota);
    if (a.hace_falta) partes.push("· " + a.hace_falta);
    return partes.join(" ");
  }

  // Caja honesta: reemplaza a la rueda de carga infinita. Se pinta una vez por
  // panel y se actualiza si llega un aviso distinto.
  window.CORT_alAvisoPanel = (a) => {
    if (!a || !a.type) return;
    avisosVistos[a.orden || a.panel || "?"] = a;
    const caja = document.getElementById(a.panel || "");
    if (!caja) return avisoFlotante(a);
    const viejo = caja.querySelector(".cort-aviso");
    if (viejo) viejo.remove();
    const div = document.createElement("div");
    div.className = "cort-aviso";
    const titulo = document.createElement("div");
    titulo.className = "cort-aviso-titulo";
    titulo.textContent = "CORT · aquí no hay nada medido";
    const cuerpo = document.createElement("div");
    cuerpo.className = "cort-aviso-motivo";
    cuerpo.textContent = avisoTexto(a);
    div.appendChild(titulo);
    div.appendChild(cuerpo);
    caja.insertBefore(div, caja.firstChild);
    // Y se apagan los "Cargando…" que la plantilla deja puestos para siempre: si
    // no va a llegar nada, el texto que promete que está llegando es una mentira.
    const andamiaje = /^(cargando|loading|recherche|chargement|buscando|escaneando|analizando|\.\.\.|…)/i;
    caja.querySelectorAll("span, div, option, td, li, p").forEach(el => {
      if (el.children.length) return;
      const t = (el.textContent || "").trim();
      if (t && t.length < 40 && andamiaje.test(t)) {
        el.textContent = "— sin datos —";
        el.classList.add("cort-sin-datos");
      }
    });
  };

  // Aviso para órdenes que no tienen panel propio: una línea breve abajo del todo,
  // una sola vez por carga de página. No es un error del sistema, es una respuesta.
  function avisoFlotante(a) {
    const clave = "flotante-" + (a.orden || "?");
    if (avisosVistos[clave]) return;
    avisosVistos[clave] = a;
    let toast = document.getElementById("cort-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "cort-toast";
      document.body.appendChild(toast);
    }
    toast.textContent = "CORT: " + avisoTexto(a);
    toast.classList.add("cort-toast-visible");
    clearTimeout(avisoFlotante._t);
    avisoFlotante._t = setTimeout(() => toast.classList.remove("cort-toast-visible"), 7000);
  }

  // Temperatura real. La demo pintaba aquí un número inventado por el simulador;
  // ahora se pinta el sensor del kernel y se dice cuál es. Un dato empujado al
  // conectar no abre el panel por la cara: solo lo que ella pide.
  window.CORT_alTemperatura = (mensaje) => {
    if (!mensaje) return;
    const d = mensaje.data || {};
    ultimaTemperatura = d;
    const panel = document.getElementById("temp-panel");
    if (!panel) return;
    const pieza = document.getElementById("tp-piece");
    const grado = document.getElementById("tp-temp");
    const marca = document.getElementById("tp-marker");
    const humedad = document.getElementById("tp-hum-row");
    if (pieza) pieza.textContent = (d.piece || (d.motivo || "sin sensor")).toUpperCase();
    if (grado) grado.textContent = d.ok ? String(Math.round(d.temperature)) : "--";
    if (humedad) humedad.style.display = "none";   // no hay higrómetro: se apaga, no se finge
    if (marca && d.ok) {
      // La barra es de confort de sala (10-30 °C). Un chip a 48 °C se sale: se deja
      // el marcador en el borde y lo dice la nota, en lugar de disimularlo.
      const pct = Math.min(100, Math.max(0, (d.temperature - 10) / 20 * 100));
      marca.style.left = pct + "%";
    }
    let nota = document.getElementById("cort-temp-nota");
    if (!nota) {
      nota = document.createElement("div");
      nota.id = "cort-temp-nota";
      nota.className = "cort-aviso";
      panel.insertBefore(nota, panel.firstChild);
    }
    nota.textContent = d.ok
      ? (d.aviso || "Lectura del sensor del equipo.") +
        (d.sensores ? " Sensores: " + Object.keys(d.sensores).join(", ") + "." : "")
      : ("Sin lectura de temperatura: " + (d.motivo || "no hay sensores accesibles."));
    if (d.ok && !mensaje.empujado) panel.classList.add("tp-visible");
  };

  // ---- 5b. voz de salida y micrófono (fase F3) -------------------------------
  // La regla es la misma que en F1: si el equipo no tiene altavoz, se dice con el
  // nombre del dispositivo. Y si el puente ya sacó el sonido por sus propios altavoces,
  // el navegador NO lo vuelve a lanzar: se duplicaría y en la Canaima se oiría raro.
  let ultimaVoz = null, ultimoMic = null, reproductorVoz = null, medidorVoz = null;
  let ultimaVida = null;

  function badgeVoz() {
    let b = document.getElementById("cort-voz-badge");
    if (b) return b;
    b = document.createElement("div");
    b.id = "cort-voz-badge";
    b.innerHTML =
      '<button type="button" id="cvb-habla" class="cvb-btn" title="hablar o callar">🔇</button>' +
      '<button type="button" id="cvb-motor" class="cvb-btn" title="cambiar motor de voz">ra</button>' +
      '<button type="button" id="cvb-mic" class="cvb-btn" title="micrófono">mic</button>' +
      '<button type="button" id="cvb-pc" class="cvb-btn" title="qué ve CORT en este equipo">pc</button>' +
      '<button type="button" id="cvb-vida" class="cvb-btn" title="lista, notas y pendientes">🛒</button>' +
      '<span id="cvb-texto" class="cvb-texto"></span>';
    (document.body || document.documentElement).appendChild(b);
    b.querySelector("#cvb-habla").addEventListener("click", () => {
      const activa = !(ultimaVoz && ultimaVoz.activa);
      window.CORT_enviarAlCerebro({ type: activa ? "voz_on" : "voz_off" });
    });
    b.querySelector("#cvb-pc").addEventListener("click", () => {
      window.CORT_enviarAlCerebro({ type: "pc_estado" });
      flotante("Consultando el equipo: ventanas, volumen, brillo y programas…");
    });
    b.querySelector("#cvb-motor").addEventListener("click", () => {
      const actual = (ultimaVoz && ultimaVoz.motor) || "rapida";
      window.CORT_enviarAlCerebro({ type: "voz_motor", motor: actual === "rapida" ? "natural" : "rapida" });
    });
    b.querySelector("#cvb-vida").addEventListener("click", () => {
      window.CORT_enviarAlCerebro({ type: "vida_estado" });
      flotante("Leyendo la vida diaria: lista de compras, notas y pendientes del disco…");
    });
    b.querySelector("#cvb-mic").addEventListener("click", () => {
      const encendido = ultimoMic && ultimoMic.estado === "escuchando";
      window.CORT_enviarAlCerebro({ type: encendido ? "mic_off" : "mic_on" });
    });
    return b;
  }

  function pintarVoz() {
    const b = badgeVoz();
    const v = ultimaVoz || {}, mic = ultimoMic || {};
    const habla = b.querySelector("#cvb-habla"), motor = b.querySelector("#cvb-motor"),
          micro = b.querySelector("#cvb-mic"), texto = b.querySelector("#cvb-texto");
    const activa = v.activa !== false;
    habla.textContent = activa ? "🔊" : "🔇";
    habla.classList.toggle("cvb-apagado", !activa);
    motor.textContent = (v.motor === "natural" || v.motor === "natural2") ? "na" : "ra";
    const escuchando = mic.estado === "escuchando";
    micro.textContent = escuchando ? "● mic" : "mic";
    micro.classList.toggle("cvb-activo", escuchando);
    micro.classList.toggle("cvb-apagado", !escuchando);
    const partes = [];
    if (!v.habla && !v.motor) partes.push("consultando la voz…");
    else {
      partes.push((v.habla || v.motor || "sin motor"));
      partes.push(v.altavoz_real ? ("altavoz: " + (v.sink || "sí")) : "sin altavoz (auto_null)");
      partes.push(escuchando ? "escuchando" :
                  (mic.estado === "sin micro" ? "sin micrófono" : "mic apagado"));
      const d = (ultimaVida && ultimaVida.datos) || null;
      if (d) partes.push(`🛒 ${d.compras} · 📝 ${d.notas} · ⏰ ${d.pendientes}` +
                         (d.proximo ? ` (${Math.round(d.proximo.faltan_seg / 60)}m)` : ""));
      else if (ultimaVida) partes.push("vida leída");
    }
    texto.textContent = partes.join(" · ");
    texto.classList.toggle("cvb-alerta", v.ok === false || v.altavoz_real === false);
  }

  function analizadorDe(el, fuenteCtx) {
    // Medidor real de lo que está sonando: RMS de la propia pista, no una animación
    // inventada. Si el navegador no deja montar el grafo, simplemente no hay pulso.
    try {
      const ctx = fuenteCtx || (window.AudioContext || window.webkitAudioContext)();
      if (!ctx) return null;
      const src = ctx.createMediaElementSource(el);
      const an = ctx.createAnalyser();
      an.fftSize = 512;
      src.connect(an); an.connect(ctx.destination);
      const datos = new Uint8Array(an.fftSize);
      return { ctx, an, datos, rms() {
        an.getByteTimeDomainData(datos);
        let s = 0; for (let i = 0; i < datos.length; i++) { const d = (datos[i] - 128) / 128; s += d * d; }
        return Math.sqrt(s / datos.length);
      } };
    } catch (e) { return null; }
  }

  function sonarVoz(n) {
    if (!n || !n.url) return;
    if (n.altavoz_real) return;          // ya sonó por el altavoz del equipo
    const url = n.url + "?t=" + (n.id || Date.now());
    if (!reproductorVoz) {
      reproductorVoz = new Audio();
      reproductorVoz.preload = "auto";
      medidorVoz = analizadorDe(reproductorVoz);
    }
    reproductorVoz.src = url;
    const p = reproductorVoz.play();
    if (p && p.catch) p.catch(() => {
      // Autoplay bloqueado: se reintenta con el primer gesto de la usuaria.
      const r = () => { reproductorVoz.play().catch(() => {});
                        window.removeEventListener("pointerdown", r);
                        window.removeEventListener("keydown", r); };
      window.addEventListener("pointerdown", r, { once: true });
      window.addEventListener("keydown", r, { once: true });
    });
    if (medidorVoz && typeof window.CORT_orbe === "object") {
      const latir = () => {
        if (!reproductorVoz || reproductorVoz.paused) { window.CORT_orbe.volumen(0); return; }
        try { window.CORT_orbe.volumen(Math.min(1.6, medidorVoz.rms() * 6)); } catch (e) {}
        requestAnimationFrame(latir);
      };
      requestAnimationFrame(latir);
    }
  }

  // Aviso breve reutilizable (F5): la misma línea que usa el puente para avisos,
  // pero sin el filtro de "una vez por carga", porque las acciones se repiten.
  function flotante(texto, ok) {
    let t = document.getElementById("cort-toast");
    if (!t) {
      t = document.createElement("div");
      t.id = "cort-toast";
      (document.body || document.documentElement).appendChild(t);
    }
    t.textContent = "CORT: " + String(texto).slice(0, 300);
    t.style.borderColor = ok === false ? "rgba(255,120,120,.6)" : "rgba(255,170,0,.5)";
    t.classList.add("cort-toast-visible");
    clearTimeout(flotante._t);
    flotante._t = setTimeout(() => t.classList.remove("cort-toast-visible"), 6500);
  }

  window.CORT_alAccion = (m) => {
    if (!m) return;
    if (m.type === "pc_estado") {
      const v = m.volumen || {}, b = m.brillo || {};
      flotante(`${m.ventanas} ventanas · ${m.apps} programas · volumen ${v.porcentaje ?? "--"}%` +
               ` · brillo ${b.porcentaje ?? "--"}% (${b.sensor || "sin sensor"})` +
               ` · sink ${v.sink || "?"}`, true);
      return;
    }
    const extra = m.nota ? " — " + m.nota : "";
    flotante(`${m.ok ? "hecho" : "no"}: ${m.detalle || m.motivo || ""}${extra}`, m.ok);
  };

  window.CORT_alVida = (n) => {
    if (!n) return;
    if (n.type === "reminder_trigger") {
      // El pendiente venció en el puente: se ve y se oye, no se queda en el registro.
      flotante(`⏰ ${n.time} — ${n.text}`, true);
      ultimaVida = { type: "vida_estado", datos: null };
      window.CORT_enviarAlCerebro({ type: "vida_estado" });
      pintarVoz();
      return;
    }
    ultimaVida = n;
    pintarVoz();
  };

  // ---- 5c. bandeja de petición escrita (F9) con tirador lateral (D1) ---------
  // La plantilla sólo traía órdenes de una lista fija y el micrófono. Si el cerebro
  // entiende frases largas tiene que haber un sitio donde escribirlas: además sirve de
  // destino al dictado, porque CORT_alVoz busca #command-input y ese es este campo.
  // El cajón se guarda medio cerrado detrás de una flecha en el canto izquierdo: en el
  // teléfono no tapa el orbe hasta que lo pides, y en el PC basta pasar el cursor.
  function bandeja() {
    let b = document.getElementById("cort-bandeja");
    if (b) return b;
    const abierto = localStorage.getItem("cort_bandeja") !== "cerrada";
    b = document.createElement("form");
    b.id = "cort-bandeja";
    b.className = abierto ? "cort-abierta" : "";
    b.style.cssText = "position:fixed;left:12px;bottom:12px;z-index:9997;display:flex;gap:8px;" +
      "width:min(520px,calc(100vw - 78px));padding:8px;border-radius:14px;" +
      "background:rgba(8,16,28,.86);border:1px solid rgba(90,200,255,.42);" +
      "box-shadow:0 6px 24px rgba(0,0,0,.45),0 0 18px rgba(60,180,255,.16);" +
      "transition:transform .22s ease,opacity .22s ease";
    const campo = document.createElement("input");
    campo.id = "command-input";
    campo.type = "text";
    campo.autocomplete = "off";
    campo.placeholder = "pide lo que sea: «mueve la carpeta proyectos a documentos»";
    campo.style.cssText = "flex:1;min-width:0;padding:8px 10px;border-radius:10px;border:1px solid rgba(120,200,240,.35);" +
      "background:rgba(6,12,22,.9);color:#e9f4ff;font:14px/1.4 system-ui";
    const boton = document.createElement("button");
    boton.type = "submit";
    boton.id = "cort-bandeja-pedir";
    boton.textContent = "pedir";
    boton.style.cssText = "padding:8px 14px;border-radius:10px;cursor:pointer;border:1px solid rgba(90,210,255,.65);" +
      "background:rgba(40,150,220,.22);color:#bfeeff;font:14px/1.2 system-ui";
    b.append(campo, boton);

    // F10: el candado del oído. Con la palabra encendida, CORT escucha en silencio y
    // sólo obedece lo que va dicho después de «cort».
    const wake = document.createElement("button");
    wake.id = "cort-bandeja-wake";
    wake.type = "button";
    wake.textContent = "«cort»";
    wake.title = "palabra de despertar: sólo obedece después de oír su nombre";
    wake.style.cssText = "padding:8px 9px;border-radius:10px;cursor:pointer;font:13px/1.2 system-ui;" +
      "border:1px solid rgba(90,210,255,.45);background:rgba(20,60,90,.25);color:#9fd8ef";
    wake.addEventListener("click", () =>
      window.CORT_enviarAlCerebro({ type: wake.dataset.on === "1" ? "wake_off" : "wake_on" }));
    b.insertBefore(wake, boton);

    const tirador = document.createElement("button");
    tirador.id = "cort-bandeja-tirador";
    tirador.type = "button";
    tirador.textContent = abierto ? "‹" : "›";
    tirador.title = "bandeja de petición";
    tirador.setAttribute("aria-label", "abrir o cerrar la bandeja de petición");
    (document.body || document.documentElement).append(b, tirador);

    const abre = () => {
      b.classList.add("cort-abierta");
      b.style.transform = "translateX(0)";
      b.style.opacity = "1";
      b.style.pointerEvents = "auto";
      tirador.textContent = "‹";
      localStorage.setItem("cort_bandeja", "abierta");
    };
    const cierra = () => {
      b.classList.remove("cort-abierta");
      b.style.transform = "translateX(calc(-100% - 26px))";
      b.style.opacity = "0";
      b.style.pointerEvents = "none";
      tirador.textContent = "›";
      localStorage.setItem("cort_bandeja", "cerrada");
    };
    if (!abierto) cierra();
    tirador.addEventListener("click", () => {
      (b.classList.contains("cort-abierta") ? cierra : abre)();
      if (b.classList.contains("cort-abierta")) campo.focus();
    });
    // En PC alcanza con acercar el cursor; en el teléfono el toque del tirador hace lo
    // mismo. El hover sólo se escucha con cursor de verdad: en Android el navegador
    // dispara mouseenter antes del click, y abrir+cerrar en el mismo toque dejaba la
    // bandeja inutilizable.
    if (matchMedia("(hover: hover) and (pointer: fine)").matches) {
      tirador.addEventListener("mouseenter", abre);
      b.addEventListener("mouseenter", abre);
    }
    document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") cierra(); });

    b.addEventListener("submit", (ev) => {
      ev.preventDefault();
      const texto = campo.value.trim();
      if (!texto) return;
      window.CORT_enviarAlCerebro({ type: "user_input", text: texto });
      campo.value = "";
      flotante("pidiendo: " + texto.slice(0, 60));
    });
    return b;
  }

  function pintaWake(n) {
    const w = document.getElementById("cort-bandeja-wake");
    if (!w) return;
    const encendido = !!n.wake;
    w.dataset.on = encendido ? "1" : "0";
    w.textContent = encendido ? "«cort» ✓" : "«cort»";
    w.style.background = encendido ? "rgba(0,229,255,.30)" : "rgba(20,60,90,.25)";
    w.style.color = encendido ? "#03202e" : "#9fd8ef";
  }

  // ---- F9: lo que el cerebro entendió y qué hizo la reja ---------------------
  // La tarjeta se queda a propósito: un aviso de 6 s no alcanza para leer el plan,
  // y si la reja frenó hay que ver con qué palabras hay que confirmar.
  let ultimoPlan = null;

  function tarjetaPlan(n) {
    let c = document.getElementById("cort-plan");
    if (!c) {
      c = document.createElement("div");
      c.id = "cort-plan";
      // bottom:152 y no 78: medido, a 78 la tarjeta tapaba los botones de micrófono,
      // silencio y escucha continua (y378-436), que sí reciben clic.
      c.style.cssText = "position:fixed;left:12px;bottom:152px;z-index:9998;max-width:min(430px,88vw);" +
        "padding:10px 12px;border-radius:12px;font:12px/1.45 system-ui;color:#e9f4ff;" +
        "background:rgba(8,16,28,.88);border:1px solid rgba(90,200,255,.45);box-shadow:0 6px 22px rgba(0,0,0,.45)";
      (document.body || document.documentElement).appendChild(c);
    }
    const args = Object.entries((n.plan && n.plan.argumentos) || {})
      .filter(([, v]) => v).map(([k, v]) => `${k}: ${v}`).join(" · ");
    const pide = !n.valido && /confirmaci/i.test((n.motivo || "") + " " + (n.decir || ""));
    c.innerHTML = "";
    const titulo = document.createElement("div");
    titulo.style.cssText = "font-weight:700;letter-spacing:.4px;color:" +
      (n.valido ? "#8ff0b4" : "#ffb0b0");
    titulo.textContent = `${n.valido ? "hecho" : "no lo hice"} · ${n.intencion || "nada"} · ${n.origen}`;
    const frase = document.createElement("div");
    frase.textContent = "«" + (n.frase || "") + "»";
    const plan = document.createElement("div");
    plan.style.opacity = ".82";
    plan.textContent = args ? "argumentos: " + args : "sin argumentos";
    const decir = document.createElement("div");
    decir.style.marginTop = "4px";
    decir.textContent = n.decir || n.motivo || "";
    c.append(titulo, frase, plan, decir);
    if (pide) {
      const boton = document.createElement("button");
      boton.type = "button";
      boton.id = "cort-plan-confirmar";
      boton.textContent = "Confirmar";
      boton.style.cssText = "margin-top:8px;padding:5px 12px;border-radius:9px;cursor:pointer;" +
        "border:1px solid rgba(90,210,255,.65);background:rgba(40,150,220,.22);color:#bfeeff";
      boton.addEventListener("click", () => {
        boton.disabled = true;
        window.CORT_enviarAlCerebro({ type: "user_input", text: "confirma" });
      });
      c.appendChild(boton);
    }
    clearTimeout(tarjetaPlan._t);
    c.style.opacity = "1";
    tarjetaPlan._t = setTimeout(() => { c.style.opacity = "0"; }, 32000);
  }

  window.CORT_alPlan = (n) => {
    if (!n || n.type !== "plan_resultado") return;
    ultimoPlan = n;
    const args = Object.entries((n.plan && n.plan.argumentos) || {})
      .filter(([, v]) => v).map(([k, v]) => `${k}: ${v}`).join(" · ");
    flotante(`${n.intencion || "nada"}${args ? " (" + args + ")" : ""} — ${n.decir}`, n.valido);
    tarjetaPlan(n);
  };

  // ---- M1: panel de cerebro — qué hay en disco, bajarlo y probarlo ------------
  // El puente ya mandaba el inventario y el progreso; faltaba una pantalla donde
  // ver el peso MEDIDO, la RAM estimada y si cabe ahora. Nada de aquí carga un
  // modelo por su cuenta: «probar» pregunta la puerta de RAM antes de disparar.
  let ultimoCerebro = null;
  let ultimoPerfil = null;   // S1: el escaneo del equipo (nivel, motivo, plan)
  let ultimoVision = null;   // S2: el estado de la mirada (cuadros, ritmo, motivo)
  let ultimaMemoria = null;    // S4: qué guarda CORT de ti y en qué archivo
  let ultimaIniciativa = null; // S4: lo que CORT dijo por su cuenta al conectar
  let ultimoControl = null;    // S4: la autocrítica que cambió una respuesta del modelo
  let ultimaVersion = null;    // U1: lo que dijo el canal del repo
  let ultimaPrueba = null;   // el inventario no puede borrarse el resultado de la prueba
  const progresoPull = {};
  const BOTON_CEREBRO = "padding:3px 9px;border-radius:8px;cursor:pointer;font:11px/1.2 system-ui;" +
    "border:1px solid rgba(90,210,255,.6);background:rgba(40,150,220,.2);color:#bfeeff";

  function chipCerebro() {
    if (document.getElementById("cort-cerebro-chip")) return;
    const chip = document.createElement("button");
    chip.id = "cort-cerebro-chip";
    chip.type = "button";
    chip.textContent = "◉";
    chip.title = "cerebro: modelos en disco, descargas y prueba";
    chip.setAttribute("aria-label", "abrir el panel del cerebro");
    const aviso = document.createElement("span");
    aviso.id = "cort-cerebro-aviso";
    aviso.style.cssText = "position:absolute;top:5px;right:5px;width:9px;height:9px;" +
      "border-radius:50%;background:#ff5f7a;box-shadow:0 0 8px #ff5f7a;display:none";
    chip.appendChild(aviso);
    chip.style.cssText = "position:fixed;left:0;bottom:150px;z-index:9999;width:34px;height:44px;" +
      "border:1px solid rgba(90,200,255,.5);border-left:none;border-radius:0 12px 12px 0;" +
      "background:linear-gradient(180deg,rgba(20,70,110,.92),rgba(8,24,44,.92));" +
      "color:#bfeeff;font:700 16px/1 'Courier New',monospace;cursor:pointer;" +
      "box-shadow:0 0 14px rgba(60,180,255,.22)";
    const panel = document.createElement("div");
    panel.id = "cort-cerebro";
    panel.style.cssText = "position:fixed;left:44px;bottom:12px;z-index:9998;display:none;" +
      "width:min(430px,calc(100vw - 60px));max-height:62vh;overflow:auto;padding:10px 12px;" +
      "border-radius:12px;background:rgba(8,16,28,.94);border:1px solid rgba(90,200,255,.45);" +
      "color:#dff1ff;font:12px/1.5 system-ui";
    (document.body || document.documentElement).append(chip, panel);
    chip.addEventListener("click", () => {
      const abierto = panel.style.display === "block";
      panel.style.display = abierto ? "none" : "block";
      if (!abierto) {
        window.CORT_enviarAlCerebro({ type: "check_ollama_status" });
        window.CORT_enviarAlCerebro({ type: "buscar_actualizacion" });
        window.CORT_enviarAlCerebro({ type: "perfil_equipo" });
        window.CORT_enviarAlCerebro({ type: "vision_estado" });
        window.CORT_enviarAlCerebro({ type: "memoria_estado" });
        pintarCerebro();
      }
    });
  }

  function nodoVersion() {
    const v = document.createElement("div");
    v.id = "cort-version";
    // Va arriba, no al pie: en una pantalla de 521 px el listado de modelos empujaba
    // el aviso de versión fuera del panel y había que hacer scroll para enterarse.
    v.style.cssText = "margin:0 0 8px;padding:5px 8px;border-radius:9px;" +
      "border:1px solid rgba(120,200,240,.28);background:rgba(16,44,68,.5);opacity:.92";
    const n = ultimaVersion;
    const etiqueta = document.createElement("b");
    etiqueta.textContent = n.hay_nueva ? "nueva versión" : "canal";
    const cuerpo = document.createElement("span");
    cuerpo.textContent = " " + (n.hay_nueva
      ? `${n.remota} · local ${n.version_local} · ${n.como}`
      : (n.ok ? `${n.version_local} está al día frente a ${n.remota}` : n.motivo));
    const origen = document.createElement("span");
    origen.style.cssText = "opacity:.6";
    origen.textContent = ` · origen ${n.origen || "?"}`;
    v.append(etiqueta, cuerpo, origen);
    return v;
  }

  function nodoPerfil() {
    const p = ultimoPerfil;
    const caja = document.createElement("div");
    caja.id = "cort-perfil";
    caja.style.cssText = "margin:0 0 8px;padding:6px 8px;border-radius:9px;" +
      "border:1px solid rgba(120,220,190,.35);background:rgba(14,48,44,.5)";
    const n = p.nivel || {};
    const cab = document.createElement("div");
    cab.style.cssText = "font-weight:700;color:#c9f2e0";
    cab.textContent = p.origen === "real"
      ? `equipo · nivel ${n.nivel ?? "?"} — ${n.nombre || "?"}`
      : "equipo · escaneo no disponible";
    caja.appendChild(cab);
    if (p.origen !== "real") {
      const m = document.createElement("div");
      m.style.cssText = "opacity:.75";
      m.textContent = p.motivo || "el puente no devolvió el perfil";
      caja.appendChild(m);
      return caja;
    }
    const c = p.cpu || {}, m = p.memoria || {}, g = p.gpu || {}, t = p.temperatura || {};
    const partes = [
      `${c.modelo || "?"} · ${c.nucleos || 0} núcleos · ${c.mhz || 0} MHz`,
      `AVX ${c.avx ? "sí" : "no"} / AVX2 ${c.avx2 ? "sí" : "no"} · SSE4.2 ${c.sse42 ? "sí" : "no"}`,
      `RAM ${m.libre_mb}/${m.total_mb} MB libre`,
      `disco ${Math.round((p.disco || {}).libre_mb / 1024)} GB libres`,
      (p.camara || []).length ? `cámara ${(p.camara || []).map(x => x.nodo).join(", ")}` : "sin cámara",
      `GPU ${g.cuda ? "CUDA" : (g.etiqueta || g.descripcion || "no disponible")}`,
      `${t.celsius ?? "?"} °C (${t.sensor || "sin sensor"})`,
      `carga ${c.carga_1min ?? "?"}`,
    ];
    const datos = document.createElement("div");
    datos.style.cssText = "opacity:.8;margin:3px 0";
    datos.textContent = partes.join(" · ");
    caja.appendChild(datos);
    const motivo = document.createElement("div");
    motivo.textContent = n.motivo || "";
    caja.appendChild(motivo);
    if ((n.se_apaga_texto || []).length) {
      const apa = document.createElement("div");
      apa.style.cssText = "margin-top:3px;color:#ffd9a0";
      apa.textContent = `se apaga para que quepa: ${n.se_apaga_texto.join(", ")}`;
      caja.appendChild(apa);
    }
    if ((p.ajustes_aplicados || []).length) {
      const he = document.createElement("div");
      he.style.cssText = "color:#9fe6b2";
      he.textContent = `el puente ya cambió: ${p.ajustes_aplicados.join(", ")}`;
      caja.appendChild(he);
    }
    const pie = document.createElement("div");
    pie.style.cssText = "display:flex;gap:6px;align-items:center;margin-top:5px";
    const medido = document.createElement("span");
    medido.style.cssText = "opacity:.55";
    medido.textContent = `medido ${p.medido_en || ""}`;
    const boton = document.createElement("button");
    boton.type = "button";
    boton.textContent = "reescanear";
    boton.style.cssText = BOTON_CEREBRO;
    boton.addEventListener("click", () =>
      window.CORT_enviarAlCerebro({ type: "perfil_equipo", fuerzo: true }));
    pie.append(boton, medido);
    caja.appendChild(pie);
    return caja;
  }

  function aplicaAjustesPerfil() {
    const p = (ultimoPerfil && ultimoPerfil.plan) || null;
    if (!p) return;
    if (window.CORT_orbe && CORT_orbe.tope) CORT_orbe.tope(p.orbe_fps >= 60 ? 0 : p.orbe_fps);
    // Las scanlines son rejillas animadas sobre cada panel: en 2 núcleos se pintan
    // igual que el orbe, así que el plan las apaga de verdad y no sólo en el cartel.
    const display = p.scanlines ? "" : "none";
    document.querySelectorAll(".av-panel-scanlines,.dropdown-scanlines,.tp-scanlines," +
      ".wp-scanlines,.print3d-panel-scanlines,.uninstaller-panel-scanlines")
      .forEach((e) => { e.style.display = display; });
  }

  // S2: los gestos con nombres legibles; el identificador interno no se le muestra.
  const GESTO_NOMBRE = {
    barrido_derecha: "barrido a la derecha",
    barrido_izquierda: "barrido a la izquierda",
    levantar_mano: "mano levantada",
    palma_arriba: "palma abierta",
    punar: "puño cerrado",
    empujar_abajo: "empujar hacia abajo",
  };
  let ultimoGestoVision = null;

  function nodoMirada() {
    const v = ultimoVision || {};
    const caja = document.createElement("div");
    caja.id = "cort-mirada";
    caja.style.cssText = "margin:0 0 8px;padding:6px 8px;border-radius:9px;" +
      "border:1px solid rgba(220,170,255,.35);background:rgba(38,20,52,.5)";
    const cab = document.createElement("div");
    cab.style.cssText = "font-weight:700;color:#e7d2ff";
    const mirando = !!v.mirando;
    // Recién encendida la cámara tarda en dar el primer cuadro (2,4 s medidos en esta
    // máquina): decir «0 cuadros/s» parecería que no funciona, y no es cierto.
    cab.textContent = mirando
      ? (v.cuadros
          ? `mirada · encendida · ${v.fps_reciente || v.fps_medidos || 0} cuadros/s · ` +
            `${v.cuadros} leídos · ${v.ms_calculo || "?"} ms por cuadro`
          : "mirada · encendida, esperando el primer cuadro (la cámara tarda ~2,4 s)")
      : "mirada · apagada";
    caja.appendChild(cab);

    const pie = document.createElement("div");
    pie.style.cssText = "display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:4px";
    const boton = document.createElement("button");
    boton.type = "button";
    // 34 px de alto medidos: en el teléfono un botón de 11 px no se toca con el pulgar.
    boton.style.cssText = "padding:7px 12px;min-height:34px;border-radius:9px;cursor:pointer;" +
      "font:12px/1.2 system-ui;border:1px solid rgba(200,150,255,.6);" +
      "background:rgba(120,60,190,.22);color:#e7d2ff";
    boton.textContent = mirando ? "apagar la mirada" : "encender la mirada";
    boton.addEventListener("click", () => window.CORT_enviarAlCerebro(
      { type: mirando ? "vision_off" : "vision_on" }));
    const nota = document.createElement("span");
    nota.style.cssText = "opacity:.6";
    nota.textContent = "los cuadros se leen y se tiran: no se guarda ninguna imagen";
    pie.append(boton, nota);
    caja.appendChild(pie);

    const motivo = document.createElement("div");
    motivo.style.cssText = "margin-top:3px;opacity:.85";
    motivo.textContent = v.motivo || (mirando ? "" : "nadie ha pedido mirar todavía");
    if (motivo.textContent) caja.appendChild(motivo);

    if (ultimoGestoVision) {
      const g = document.createElement("div");
      g.style.cssText = "margin-top:3px;color:" + (ultimoGestoVision.ok ? "#9fe6b2" : "#ffd9a0");
      g.textContent = `último gesto: ${GESTO_NOMBRE[ultimoGestoVision.gesto] || ultimoGestoVision.gesto}` +
        ` → ${ultimoGestoVision.accion} · ` +
        (ultimoGestoVision.detalle || ultimoGestoVision.por || "");
      caja.appendChild(g);
    }
    return caja;
  }

  window.CORT_alVision = (n) => {
    if (!n) return;
    if (n.type === "vision_gesto") {
      ultimoGestoVision = n;
      flotante(`${GESTO_NOMBRE[n.gesto] || n.gesto} → ${n.accion}: ` +
               (n.detalle || (n.ok ? "hecho" : "no se pudo")), !!n.ok);
    } else if (n.type === "vision_estado") {
      ultimoVision = n;
    }
    pintarCerebro();
  };

  // S4: la memoria. Es la tarjeta que dice qué sabe CORT de ti, en qué archivo vive
  // y qué te propuso al conectar. Se muestra el camino entero porque «tengo 12
  // apuntes» sin decir dónde están es una promesa sin prueba.
  function nodoMemoria() {
    const m = (ultimaMemoria && ultimaMemoria.datos) || {};
    const ini = ultimaIniciativa || {};
    // El plural se escribe a propósito: «1 apuntes» delataba que la tarjeta nunca
    // se había leído con un solo dato guardado.
    const uno = (n, s, p) => `${n || 0} ${n === 1 ? s : p}`;
    const caja = document.createElement("div");
    caja.id = "cort-memoria";
    caja.style.cssText = "margin:0 0 8px;padding:6px 8px;border-radius:9px;" +
      "border:1px solid rgba(150,230,190,.35);background:rgba(18,40,32,.5)";
    const cab = document.createElement("div");
    cab.style.cssText = "font-weight:700;color:#c9f2da";
    // Tres estados, no dos: abrir la tarjeta y ver «todavía no has guardado nada»
    // mientras la consulta está en camino era afirmar algo que no se sabía.
    cab.textContent = !ultimaMemoria
      ? "memoria · consultando tu archivo…"
      : ultimaMemoria.origen !== "real"
        ? "memoria · el puente no pudo medirla"
        : m.existe
          ? `memoria · ${uno(m.hechos, "apunte", "apuntes")} · ` +
            `${uno(m.correcciones, "corrección", "correcciones")} · ` +
            `${uno(m.preferencias, "preferencia", "preferencias")}`
          : "memoria · todavía no has guardado nada";
    caja.appendChild(cab);

    // El motivo se pinta entero: una tarjeta vacía sin explicación es exactamente lo
    // que se vino a corregir desde la fase F1.
    if (ultimaMemoria && ultimaMemoria.origen !== "real" && ultimaMemoria.motivo) {
      const why = document.createElement("div");
      why.style.cssText = "margin-top:3px;color:#ffb4b4;font-size:11px";
      why.textContent = ultimaMemoria.motivo;
      caja.appendChild(why);
    }

    if (ultimaIniciativa) {
      const dicho = document.createElement("div");
      dicho.style.cssText = "margin-top:3px;color:#dff5e6";
      dicho.textContent = [ini.saludo, ini.nota].filter(Boolean).join(" · ");
      if (dicho.textContent) caja.appendChild(dicho);
    }

    // Lo que CORT está a punto de mandarle al modelo, con sus palabras: es la
    // prueba de que el apunte entró en el prompt y no una cifra suelta.
    if (ultimaMemoria && ultimaMemoria.contexto) {
      const sabe = document.createElement("div");
      sabe.style.cssText = "margin-top:3px;color:#dff5e6;font-size:11px";
      sabe.textContent = "lo que sabe de ti: " + ultimaMemoria.contexto;
      caja.appendChild(sabe);
    }

    const pie = document.createElement("div");
    pie.style.cssText = "margin-top:3px;opacity:.7;font-size:11px;word-break:break-all";
    // El resumen ya termina diciendo en qué archivo vive; repetir el camino entero
    // debajo hacía la tarjeta más larga sin decir nada nuevo.
    const ruta = m.ruta || "~/.local/share/cort/memoria.json";
    const trozos = [];
    if (!((ultimaMemoria && ultimaMemoria.contexto) || "").includes(ruta)) {
      trozos.push(ruta + " · todo en este equipo");
    }
    if (m.constitucion) trozos.push(`constitución de ${m.constitucion} caracteres`);
    if (trozos.length) { pie.textContent = trozos.join(" · "); caja.appendChild(pie); }

    if (ultimoControl && ultimoControl.ajustes && ultimoControl.ajustes.length) {
      const c = document.createElement("div");
      c.style.cssText = "margin-top:3px;color:#ffd9a0;font-size:11px";
      c.textContent = "control antes de hablar: " + ultimoControl.ajustes.join(" · ");
      caja.appendChild(c);
    }

    const prueba = document.createElement("div");
    prueba.style.cssText = "margin-top:4px;opacity:.8;font-size:11px";
    prueba.textContent = "Se prueba diciendo: «recuerda que …», «no me digas X, dime Y», " +
      "«¿qué sabes de mí?». CORT aprende de tus correcciones escribiéndolas, no " +
      "reentrenando: aquí no hay GPU y eso se dice con la medida delante.";
    caja.appendChild(prueba);
    return caja;
  }

  window.CORT_alMemoria = (n) => {
    if (!n) return;
    if (n.type === "memoria_estado") ultimaMemoria = n;
    else if (n.type === "iniciativa") {
      ultimaIniciativa = n;
      if (n.nota) flotante(n.nota, true);
    } else if (n.type === "autocritica") ultimoControl = n;
    pintarCerebro();
  };

  window.CORT_alPerfil = (n) => {
    if (!n || n.type !== "perfil_reply") return;
    ultimoPerfil = n;
    aplicaAjustesPerfil();
    chipCerebro();
    pintarCerebro();
    if (n.cambio) {
      flotante(`el equipo cambió de nivel: ${n.nivel ? n.nivel.nombre : "?"} — ` +
               `${n.memoria ? n.memoria.libre_mb : "?"} MB libres`, true);
    }
  };

  function pintarCerebro() {
    const panel = document.getElementById("cort-cerebro");
    if (!panel) return;
    const s = (ultimoCerebro && ultimoCerebro.type === "ollama_status_reply") ? ultimoCerebro.status : null;
    panel.innerHTML = "";
    const titulo = document.createElement("div");
    titulo.style.cssText = "font-weight:700;letter-spacing:.5px;color:#bfeeff";
    if (!s) {
      titulo.textContent = "cerebro — sin datos del puente todavía";
      panel.appendChild(titulo);
      if (ultimoPerfil) panel.appendChild(nodoPerfil());
      panel.appendChild(nodoMirada());
      panel.appendChild(nodoMemoria());
      return;
    }
    const libre = s.ram_disponible_mb, nucleos = s.nucleos;
    titulo.textContent = `cerebro · Ollama ${s.online ? "vivo" : "apagado"} · ` +
      `RAM libre ${libre} MB · ${nucleos} núcleos`;
    panel.appendChild(titulo);
    // El escaneo va primero: es lo que decide si tiene sentido bajar un modelo, y en
    // una pantalla de 521 px lo de abajo se lee haciendo scroll.
    if (ultimoPerfil) panel.appendChild(nodoPerfil());
    panel.appendChild(nodoMirada());
    panel.appendChild(nodoMemoria());
    const nota = document.createElement("div");
    nota.style.cssText = "opacity:.72;margin:2px 0 8px";
    nota.textContent = "El peso está medido en disco; la RAM que hace falta es estimación " +
      "sobre ese peso. «probar» no carga nada si la cuenta no cabe.";
    panel.appendChild(nota);
    if (ultimaVersion) panel.appendChild(nodoVersion());
    const cat = s.catalogo || {};
    Object.entries(cat).sort((a, b) => ((a[1].ram_uso || 1e9) - (b[1].ram_uso || 1e9)))
      .forEach(([nombre, info]) => {
        const fila = document.createElement("div");
        fila.style.cssText = "padding:6px 0;border-top:1px solid rgba(120,200,240,.18)";
        const cabe = info.instalado && libre >= 0 && info.ram_uso <= libre;
        const datos = document.createElement("div");
        datos.innerHTML = `<b>${nombre}</b> · ` +
          (info.instalado ? `en disco ${info.mb} MB` : (info.tam || "no bajado")) +
          ` · pide ~${info.ram_uso || "?"} MB` +
          `<span style="opacity:.6"> ${info.instalado ? (cabe ? "· cabe ahora" : "· no cabe ahora") : ""}</span>`;
        fila.appendChild(datos);
        const linea = document.createElement("div");
        linea.style.cssText = "display:flex;gap:6px;margin-top:4px";
        if (!info.instalado) {
          const bajar = document.createElement("button");
          bajar.type = "button"; bajar.textContent = "descargar";
          bajar.style.cssText = BOTON_CEREBRO;
          bajar.addEventListener("click", () =>
            window.CORT_enviarAlCerebro({ type: "pull_ollama_model", model: nombre }));
          linea.appendChild(bajar);
        }
        const probar = document.createElement("button");
        probar.type = "button"; probar.textContent = "probar el cerebro";
        probar.style.cssText = BOTON_CEREBRO;
        probar.disabled = !info.instalado;
        probar.addEventListener("click", () =>
          window.CORT_enviarAlCerebro({ type: "probar_cerebro", model: nombre }));
        linea.appendChild(probar);
        fila.appendChild(linea);
        if (progresoPull[nombre] !== undefined) {
          const p = document.createElement("div");
          p.style.cssText = "opacity:.8";
          p.textContent = progresoPull[nombre];
          fila.appendChild(p);
        }
        panel.appendChild(fila);
      });
    const r = ultimaPrueba;
    if (r) {
      const caja = document.createElement("div");
      caja.style.cssText = "margin-top:8px;padding:6px 8px;border-radius:9px;" +
        "border:1px solid rgba(90,200,255,.4);background:rgba(20,60,90,.35)";
      caja.textContent = r.ok
        ? `prueba con ${r.modelo}: ${r.ms} ms · ${r.tok_s} tok/s · reja: ` +
          `${r.valido ? "plan aceptado" : "rechazado"}${r.motivo ? " — " + r.motivo : ""}`
        : `prueba con ${r.modelo || "?"}: no corrió — ${r.motivo}`;
      panel.appendChild(caja);
    }
  }

  window.CORT_alVersion = (n) => {
    if (!n || n.type !== "actualizacion") return;
    ultimaVersion = n;
    const punto = document.getElementById("cort-cerebro-aviso");
    if (punto) punto.style.display = n.hay_nueva ? "block" : "none";
    if (n.hay_nueva) flotante(`hay versión nueva de CORT: ${n.remota}`, true);
    chipCerebro();
    pintarCerebro();
  };

  window.CORT_alCerebro = (n) => {
    if (!n) return;
    if (n.type === "ollama_pull_progress") {
      progresoPull[n.model] = `${n.pct || 0}% — ${n.status || ""}${n.done ? "" : " (bajando)"}`;
      if (n.done) delete progresoPull[n.model];
      flotante(n.status || "descarga terminada", n.success !== false);
    }
    if (n.type === "ollama_status_reply") ultimoCerebro = n;
    if (n.type === "cerebro_prueba" && !n.empezando) ultimaPrueba = n;
    if (n.type === "cerebro_prueba" && n.empezando) {
      flotante(`probando ${n.modelo}: ${n.frase}`);
      return;
    }
    chipCerebro();
    pintarCerebro();
  };

  window.CORT_alVoz = (n) => {
    if (!n) return;
    if (n.type === "voz_estado" || n.type === "voz_activada" || n.type === "voz_motor_result") {
      ultimaVoz = n;
    }
    if (n.type === "mic_estado") ultimoMic = n;
    if (n.type === "despierto") {
      // F10: el nombre ya se oyó; la ventana dice cuántos segundos queda de escucha.
      flotante(`despierta · te escucho ${n.ventana_seg || 8} s`, true);
      pintaWake({ wake: true });
      return;
    }
    if (n.type === "wake_estado") { pintaWake(n); return; }
    if (n.type === "voz_audio" && n.ok) sonarVoz(n);
    if (n.type === "mic_texto") {
      if (n.descartado) return;   // habló otra cosa: no era para CORT
      // Lo dictado se ve igual que lo escrito: la demo no tenía esta vía.
      const campo = document.getElementById("command-input") ||
                    document.querySelector("input[type=text][id*='input']");
      if (campo && !campo.value) campo.value = n.texto || "";
    }
    pintarVoz();
  };
  function arrancarVoz() {
    pintarVoz();
    bandeja();          // sin bandeja no hay cómo escribir una frase larga
    chipCerebro();      // y sin este canto no hay cómo bajar ni probar un modelo
    rotuloCerebro(estadoCerebro);
    // El paquete de la maqueta se inicializa después que este archivo y escribe
    // «gemini» en el rótulo. Se devuelve cada vez que lo toque: CORT no usa nubes.
    const elRotulo = document.getElementById("model-status-text");
    if (elRotulo && !elRotulo._guarda) {
      elRotulo._guarda = true;
      new MutationObserver(() => {
        if (!/^cerebro:/.test(elRotulo.textContent || "")) rotuloCerebro(estadoCerebro);
      }).observe(elRotulo, { childList: true, characterData: true, subtree: true });
    }
    // Y se pide el estado al conectar: el rótulo y la fila de Ajustes no pueden
    // quedarse con el nombre que trajo la maqueta. Reintenta 20 s, que es lo que
    // tarda el puente en tener el WebSocket listo en un equipo de dos núcleos.
    let intentos = 0;
    const pide = () => {
      if (typeof window.CORT_pedirEstadoCerebro === "function" && window.CORT_pedirEstadoCerebro()) return;
      if (++intentos < 20) setTimeout(pide, 1000);
    };
    setTimeout(pide, 1200);
  }
  if (document.readyState !== "loading") arrancarVoz();
  else document.addEventListener("DOMContentLoaded", arrancarVoz);

  // ---- 6. API de medición --------------------------------------------------
  window.CORT = {
    version: "v0",
    idioma: () => lang,
    estado() {
      const vf = fr_vistas.size;
      return {
        idioma: lang,
        cadenas_vistas: vistas.size,
        traducidas: traducidas.size,
        // Cobertura sobre LO QUE REALMENTE ESTÁ EN FRANCÉS: las cadenas que ya
        // son españolas o nombres propios no se cuentan como pendiente.
        cadenas_en_frances: vf,
        traducidas_de_frances: fr_traducidas.size,
        cobertura_frances: vf ? Math.round((fr_traducidas.size / vf) * 100) + "%" : "0%",
        cobertura_bruta: vistas.size ? Math.round((traducidas.size / vistas.size) * 100) + "%" : "0%",
        faltantes: pendientes.size,
        pendientes_de_traducir: Array.from(pendientes)
      };
    },
    diccionario: () => D.length + D_EXT.length + D_EXT2.length + D_EXT3.length + D_EXT4.length + D_EXT5.length + D_EXT6.length,
    // sonda: traduce una cadena suelta sin tocar el DOM (para depurar misses)
    prueba: s => translate(String(s)),
    esFrances: s => esFrances(String(s)),
    rewalk: () => walk(document.body),
    // F1: qué avisos honestos se pintaron y qué temperatura se leyó. Se mide desde
    // la consola sin tener que abrir el panel correspondiente.
    avisos: () => Object.keys(avisosVistos),
    avisosDetalles: () => avisosVistos,
    temperatura: () => ultimaTemperatura,
    // F3: motor de voz elegido, altavoz que ve PipeWire y estado del micrófono.
    voz: () => ultimaVoz,
    mic: () => ultimoMic
  };

  function start() {
    document.title = translate(document.title || "CORT");
    document.documentElement.lang = lang;
    walk(document.body);
    buildBootChip();
    asegurarFilaIdioma();
    asegurarFilaCerebro();
    // Al arrancar el websocket del puente todavía puede estar abriendo (el puente
    // tarda ~2 s en levantarse). Se insiste cada 3 s hasta tener estado y luego ya
    // solo cada 15 s: preguntar de más son escaneos de disco en una máquina de dos
    // núcleos.
    if (typeof window.CORT_pedirEstadoCerebro === "function") window.CORT_pedirEstadoCerebro();
    let tic = 0;
    // la app re-renderiza paneles dinámicamente: observamos y traducimos lo nuevo
    const mo = new MutationObserver(muts => {
      for (const m of muts) for (const node of m.addedNodes) walk(node);
      asegurarFilaIdioma();
      asegurarFilaCerebro();
    });
    mo.observe(document.body, { childList: true, subtree: true });
    setInterval(() => {
      walk(document.body);
      asegurarFilaIdioma();
      asegurarFilaCerebro();
      if (typeof window.CORT_pedirEstadoCerebro !== "function") return;
      if (!estadoCerebro || ++tic % 5 === 0) window.CORT_pedirEstadoCerebro();
    }, 3000); // red de seguridad
    console.log("%c[CORT] Marca, idioma y rediseño aplicados.", "color:#00ffc8;font-weight:bold;");
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
