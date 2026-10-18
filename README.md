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
