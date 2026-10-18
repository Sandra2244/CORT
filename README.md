# C.O.R.T. — Cognitive Orchestrator / Real-Time

Asistente personal holográfico inspirado en JARVIS (Iron Man) y Cortana (Halo).
Cerebro **híbrido**: funciona con IA local (Ollama), IA online gratuita (Groq/Gemini),
o ambos a la vez, eligiendo automáticamente la mejor ruta según el equipo.
Multiplataforma: Linux, Windows y (fase final) Android vía APK.

## Arquitectura

```
┌───────────── Interfaz (ui/index.html → Electron en F6) ─────────────
│  Three.js: orb de partículas + anillos   Paneles HUD · chat · reloj │
│  Web Speech API: micrófono y voz (gratis, sin instalar nada)        │
└───────────────┬──────────────────────────────────────────────────────┘
                │ HTTP localhost:8000
┌───────────────┴───────────────┐
│  Backend Python (FastAPI)     │
│  brain.py — enrutador híbrido:│
│   1. comando local instantáneo│  hora, fecha, batería, CPU… (sin internet)
│   2. Ollama local             │  equipos 8 GB+ RAM
│   3. Groq → Gemini online     │  capa gratuita, sin tarjeta
│   4. modo supervivencia       │  siempre responde algo útil
│  memory.py — SQLite persistente
└───────────────────────────────┘
```

## Instalación (3 pasos)

> **Si llegas por ZIP:** descomprime y entra en la carpeta `CORT-0.2-demo`
> antes del paso 2. Si prefieres git: `git clone -b v0.2-demo
> https://github.com/Sandra2244/CORT.git`.

1. **Requisitos**: Python 3.10+ y un navegador Chrome/Edge (para voz y micrófono).
2. **Arrancar**:
   - Linux: `bash scripts/run.sh`
   - Windows: doble clic en `scripts\run.bat`
3. **Abrir el holograma**: escribe `http://localhost:8080` en Chrome/Edge.

### Opcional — activar la IA conversacional

- **Online (recomendado, gratis):** crea `backend/.env` (copia de `.env.example`) y
  pega tu `GROQ_API_KEY` de <https://console.groq.com/keys> o `GEMINI_API_KEY` de
  <https://aistudio.google.com/apikey>. Reinicia el backend.
- **Local (equipos potentes):** instala [Ollama](https://ollama.com), ejecuta
  `ollama pull qwen2.5:3b` y CORT lo detecta solo.
- `CORT_MODE` en `.env` fuerza la ruta: `auto` (por defecto), `local`, `online`, `offline`.

## Estructura

| Ruta | Qué es |
|------|--------|
| `backend/app/main.py` | API FastAPI (`/api/chat`, `/api/status`, `/api/files`, `/api/weather`, `/api/history`, `/api/profile`) |
| `backend/app/brain.py` | Cerebro híbrido y enrutador |
| `backend/app/local_commands.py` | Comandos instantáneos sin IA |
| `backend/app/sensors.py` | Explorador de archivos seguro + clima (Open-Meteo) |
| `backend/app/memory.py` | Memoria persistente SQLite |
| `ui/index.html` + `ui/css` + `ui/js` | Holograma: orb Three.js + HUD + voz |
| `desktop/main.cjs` | Ventana Electron (modo cabina / modo vidrio) |
| `docs/` | Plan de arquitectura y fotogramas de referencia |
| `scripts/run.sh` / `run.bat` | Arranque en Linux / Windows |
| `scripts/run-desktop.sh` | Arranque del holograma de escritorio (Electron) |
| `.github/workflows/build.yml` | CI que compila los instaladores .exe/.AppImage/.deb |

## Estado del proyecto (hoja de ruta F0–F7)

- [x] F1 Backend híbrido + memoria + comandos locales — **probado en Linux**
- [x] F2 Orb Three.js + chat + reloj + micrófono — **probado en navegador**
- [x] F3 Paneles HUD: secuencia de arranque, explorador de archivos (raíces
      seguras), clima real, barras CPU/RAM/disco animadas, orb con núcleo
      naranja + cáscara azul + anillos de suelo (referencia azul) — **probado**
- [x] F3+ Ventanas de vidrio estilo Cortana: arrastrar por barra de título,
      ─ minimizar al dock, ✕ cerrar con animación, foco por z-order, dock con
      indicadores de estado — **probado (cerrar/reabrir/arrastrar/minimizar)**
- [x] F4 (modo ligero) Gestos MediaPipe: ✋ enciende cámara 160×120 con 1 mano,
      ~4 análisis/s — palma despliega/plega ventanas, pinza trae el chat,
      puño las cierra; esqueleto dibujado en mini-vista — **código listo,
      probar con cámara física**
- [x] Animación de acción: al responder, el orbe emite dos ondas de choque,
      las partículas se dispersan en espiral y se recomponen (referencia azul)
- [x] Re-análisis profundo de referencias (montajes por detección de escena):
      **consola del sistema** (registro en vivo de cada acción), **notas 01·**
      (persistentes en SQLite, se crean desde el chat escribiendo "apunta …"),
      **perfil** (nombre del asistente/usuario/tono/idioma → el cerebro lo usa
      en cada respuesta), columna de **fechas** en archivos, rejilla en
      perspectiva + arcos laterales + gemelo digital (referencia azul)
- [x] **Ejecutor de música ♪** (descubierto en el video 07bf): reproduce tu
      carpeta `~/Música` (API segura con streaming HTTP), lista con artistas,
      play/pausa/anterior/siguiente/volumen, barra de progreso con búsqueda,
      auto-siguiente al terminar. El **orbe se dispersa y forma un anillo hueco
      de partículas que gira** al estilo de la referencia: la rotación y el
      "latido" del núcleo van sincronizados con el bajo y el nivel de audio
      (Web Audio Analyser). También **vista mosaico ▦** en Archivos.
- [x] **Orbe 100 % azul + vórtice de activación** (segunda pasada al video
      francés, 214–252 s): ya no hay núcleo naranja — centro azul claro como en
      BLACKBOX. Al recibir una orden (`orb.activate()`, desde chat o wake word)
      estalla, **gira en vórtice tipo embudo** y se comprime en un anillo-portal
      antes de recomponerse. Paneles **numerados 01·–08·** estilo Jared/BLACKBOX
      (archivos, entorno, canal de voz, notas, música, consola, perfil y la
      mini-vista de gestos como panel de vidrio).
- [x] **Ejecutor del sistema**: dile o escribe «reproduce música» (o «reproduce
      <nombre de canción>») y CORT abre tu **reproductor predeterminado**
      (VLC/Strawberry/etc.) con una canción al azar de `~/Música`, o reproduce
      la que nombraste en su propio panel ♪. Probado en vivo en esta PC.
- [x] **Orbe 3D (video f7d16b9e, Michaël JARVIS)**: **plexus** — 160 anclas
      unidas por hilos de luz según su posición real (constelación que respira);
      el portal de activación ahora es un **toro 3D inclinado** que gira y
      cabecea (no un anillo plano); todo el conjunto tiene **meciimiento de
      profundidad** (rotaciones X/Z lentas). Depuración: `?vortex` `?portal` `?disc`.
- [x] **Modo oficina** («organiza las ventanas»): las ventanas abiertas se
      recolocan solas en **2 niveles** deslizándose (MODE BUREAU de la referencia).
- [x] **Más órdenes de voz del video**: «pausa» / «reanuda» el reproductor,
      «¿qué hora es?» **offline** (reloj local, sin backend), «abre youtube /
      navegador» → `POST /api/launch` con **lista blanca estricta** (nunca se
      lanza nada que no esté en `LAUNCH_ALLOWLIST`). Probado en vivo: Chrome
      abrió YouTube y la orden «terminal» fue rechazada.
- [x] **Orbe con cámara de cine + estética Jared Hood** (commit 88e0fc4): las
      partículas ahora usan un **shader con plano focal** — cercanas al foco =
      puntos pequeños y brillantes; fuera de foco = bolas suaves tenues (bokeh
      3D real, sin post-proceso). El plano **respira** solo y al activar una
      orden **barre de cerca a lejos** (desenfoque → re-enfoque). El núcleo dejó
      de ser una esfera plana: ahora es una **bola de luz aditiva** con corazón
      blanco caliente. La activación empieza con un **estallido de esquirlas**
      (cada partícula sale eyectada con fuerza distinta) → vórtice → portal →
      re-enfoque. Plexus reducido a hilos cortísimos y tenues (ya no parece
      "pantalla con líneas"). Depuración: `?burst` congela el estallido.
      **UI estilo Jared**: dock de chips rectangulares con icono + etiqueta
      monoespaciada en mayúsculas, barras de ventana `▸ NN · NOMBRE`, filas de
      archivos/notas/canciones como tiras en filo con ▸, botones ─/✕ cuadrados
      y la pista "playing" crece y brilla como el panel PROPS del video.
- [x] **Interfaz Jared Hood completa** (análisis profundo de su video, commit
      eaccfcc): **Árbol del sistema** — columna derecha persistente con las
      raíces numeradas `▸ 00 · Documentos` + subtira «39 items · fecha» (el
      conteo lo calcula el backend) y pie **CORT'S BRAIN** que abre el perfil;
      **HUD ocultable** — «oculta todo» / «muestra todo», botón ◫ OCULTAR en el
      dock y gesto de puño (recuerda qué ventanas estaban abiertas y las
      devuelve); **chips flotantes** — «muéstrame las notas» / «archivos
      recientes» lanza a la pantalla virutas con borde en filo que flotan y se
      pueden tocar (como cuando Jared agarra archivos con las manos), y al
      arrancar CORT te saluda mostrando tus últimas notas; **chispas azules**
      que salen eyectadas del portal toroidal al ejecutar (el anillo de fuego
      del video, en versión CORT). Títulos de ventana con contadores en vivo
      («raíces · 6 items»).
- [x] **Segunda pasada por el video de Jared Hood** (lo que quedaba pendiente):
      el **árbol ahora se EXPANDE** — cada raíz muestra «15 carpetas · 24
      archivos» (dos conteos reales, como «6 folders · 2 notes» del video) y al
      tocarla cambia `▸`→`▾`, inserta sus subcarpetas indentadas y **les lanza
      chips a la mano** (`GET /api/tree` calcula los conteos hijos); los **chips
      ya no desaparecen solos**: quedan flotando, se **arrastran** con el puntero
      y al agarrlos crecen y brillan (14 como máximo, `✕` para retirar uno, «recoge
      los chips» para guardarlos todos); ventana **08 · Cerebro**, el muro de
      recuerdos enmarcados (cada nota y cada conversación es un cuadro con fecha;
      el héroe central lleva el sello C.O.R.T. y el total — `GET /api/memories`
      desde SQLite) que también abre **CORT'S BRAIN** o «muéstrame tu cerebro»;
      **lámpara de estado** en el dock que cambia de color según lo que hace CORT
      (morado escuchando, naranja procesando, verde respondiendo/en línea, gris
      con el HUD oculto, rojo sin backend) igual que el foco del video; y el canal
      de voz se volvió **consola de comandos**: prompt `cort@nave:~$`, historial
      con ↑/↓ y **Tab que completa** («repro» → «reproduce»).
- [x] F5 (parte) Wake word «Oye CORT» con botón 👂 (escucha permanente opt-in);
      falta Piper TTS (recomendado solo en equipos con GPU — Web Speech ya voz gratis)
- [~] F6 Escritorio Electron: **modo cabina** (ventana sin marco, oscura, siempre
      al frente, arrastrable) probado y funcionando en Linux 1.8 GB; **modo vidrio**
      transparente (`CORT_GLASS=1`) listo para equipos con GPU/compositor y Windows.
      electron-builder configurado (.exe NSIS / .AppImage / .deb) + icono propio;
      los instaladores se construyen en GitHub Actions (`build.yml`), no en tu PC:
      `git tag v0.2.0 && git push --tags`
- [ ] F7 APK Android con Capacitor

Todo el software usado es gratuito. Ningún puerto se expone a internet: backend y
Ollama solo escuchan en `localhost`.
