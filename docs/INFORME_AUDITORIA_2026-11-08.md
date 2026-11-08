# Informe de auditoría CORT — 2026-11-08

**Alcance:** repo local `web/cort-v0` (commit `3e4960b` + trabajo F20 sin commit), release GitHub `cort-v0.17.2`, APK `CORT-movil.apk` y 35 capturas del Galaxy A16 (SM-A165M).
**Método:** todo hallazgo tiene evidencia verificada (archivo:línea o captura). Nada estimado se presenta como medido.

---

## 1. Resumen ejecutivo

CORT v0.17.2 es más sólida de lo que parece en pantalla: APK nativa Java real (sin frameworks), llama.cpp embebido para las dos ABIs, Vosk con modelo español offline, WebView que sirve la misma cara del PC, y un puente Python funcional. El trabajo F20 en tu árbol (escucha en segundo plano, accesibilidad, sensores, TLS) existe pero **no está publicado en la APK**.

Los tres problemas que más te afectan tienen causa raíz concreta y corrección acotada:

1. **La RAM se muestra en bytes etiquetados como MB** → cifras absurdas y el cerebro parece imposible de cargar.
2. **La puerta de RAM (2× el peso del archivo) es demasiado estricta para un A16 de 4 GB** → ni el Qwen2.5 0.5B pasa, aunque con mmap y contexto corto podría correr.
3. **La cara del PC se sirve sin adaptación móvil** → todo se corta a la derecha y aparecen módulos de Windows/Linux/NVIDIA en Android.

El francés residual no es un fallo del selector de idioma: la plantilla nunca se reescribió; se traduce el DOM por encima con un diccionario, y las frases que faltan en él quedan en francés.

---

## 2. Arquitectura real (verificada)

| Pieza | Qué es | Estado |
|---|---|---|
| `apps/android/` | Java nativo, build `aapt2→javac→d8→zipalign→apksigner` (sin Gradle). WebView sirve `assets/web/` interceptando `http://cort.local`; `cort-android.js` sustituye `window.WebSocket` por el puente Java `CortNative` | Funcional |
| `apps/android/jni/cort_motor.cpp` | llama.cpp b12121 (NDK r26d), `libcortmotor.so` arm64-v8a + armeabi-v7a | Funcional |
| Voz oído | Vosk + `vosk-model-small-es-0.42.zip` (39,8 MB) empaquetado; gramática `["hola cort","oye cort","[unk]"]` (Motor.java:87) | Funcional offline |
| Voz habla | `Voz.java` TTS nativo Android es-ES (offline con voz descargada); PC: espeak-ng/Piper | Funcional, sin ducking |
| `cort-bridge/` | Python: HTTP 8766 + WS 8765, intenciones, acciones Linux, Ollama real, antivirus-auditor | Funcional en PC |
| `cort-web/` | HTML + bundle React minificado TechEnClair (francés en origen) + capas propias `cort-ui.js`, `cort-mock.js`, `cort-orbe.js`; i18n por diccionario DOM (~958 triples fr/es/en) | Funcional con fugas de francés |
| Fósiles de plantilla | `backend/`, `frontend/`, `apps/web/`, `services/` — scaffolds que el producto NO usa | Confunden el mapa |

**Dato clave:** en el teléfono **no hay Ollama**. El cerebro local es GGUF vía llama.cpp. Cuando la app está enlazada al puente del PC, quien mide la RAM es el PC, no el teléfono (Nexo.java:943-979, cort_server.py:264-272).

**Verificación de identidad:** SHA-256 de tu APK local = `7883495f…fbfe2` = asset oficial de la release v0.17.2. Las capturas corresponden exactamente a esa versión.

---

## 3. Catálogo de errores (con evidencia)

### E1 · P0 — RAM en bytes mostrada como MB, y cabecera/cuerpo desincronizados
- **Evidencia código:** `Nexo.java:972` → `"ram_disponible_mb", libre` donde `libre = cerebroLocal.memoriaLibre()` devuelve `availMem` **en bytes** (CerebroLocal.java:136-142). Falta dividir entre 1024×1024.
- **Evidencia pantalla:** capturas 130839–131157 y 132147–132301: «RAM libre 653840384 MB … de 3653», «670228480 MB libres de 3653». Cabecera y cuerpo muestran cifras distintas (se actualizan por separado).
- **Impacto:** hace ilegible el estado del equipo y alimenta el mito de que «el cerebro no cabe nunca».

### E2 · P0 — Puerta de RAM demasiado estricta + dos cálculos incoherentes
- **Teléfono:** `cabe = availMem > bytesDelModelo × 2` (CerebroLocal.java:145-150, Equipo.java:92-94, Cerebros.java:325-328). Qwen2.5 0.5B q4_K_M = 491.400.032 B → puerta 983 MB (cerebros.json, MB decimales) pero la UI calcula 936 MB (binarios, Nexo.java:964). **Dos cifras distintas para la misma puerta.**
- **PC:** `ram_estimada = int(mb × 1,4) + 150` (cort_server.py:223-226) → un blob de 569 MB da exactamente los **946 MB** que citaste.
- **Realidad del A16:** ~600-700 MB libres reales (capturas). La RAM virtual de One UI no cuenta para inferencia (y es correcto que no cuente). Con la regla 2×, ningún modelo del catálogo pasa.
- **Matiz honesto:** 2× es conservador pero no absurdo (pesos + KV cache). El problema es que es un **bloqueo duro sin alternativa**: no ofrece cuantización menor, contexto reducido, mmap, ni «intentar bajo tu riesgo». `CerebroLocal.asegurar()` (L262-277) sí intenta en modo `local`, pero el botón «probar» de la cara rechaza antes.

### E3 · P0 — UI de escritorio sin adaptación móvil (desbordamiento sistemático)
- **Evidencia:** 30+ capturas con textos/botones cortados a la derecha (Ajustes, Modelo de Agente, Antivirus, widget CPU/RELOJ, botón «reescanear» tapado por la barra de navegación).
- **Causa:** el WebView carga la cara del PC tal cual («copia exacta», Nexo.java:52-55). No hay `UseWideViewPort`/`setUserAgent` ni toggle «vista escritorio» en el repo (búsqueda exhaustiva: AUSENTE). El perfil S1 solo apaga scanlines en pantallas pequeñas.
- **Tu petición explícita:** toggle en Ajustes «vista escritorio táctil ↔ vista teléfono adaptada». Hoy no existe ninguna de las dos vías.

### E4 · P1 — Francés residual, voz francesa y versión falsa
- **Causa raíz:** i18n = traducción DOM post-hoc (cort-ui.js:34-1205, MutationObserver + repaso cada 3 s). Strings del bundle que no están en el diccionario quedan en francés. Verificado sin coincidencia en DICT: `Réglages enregistrés`, `Recherche des paroles...`, `Exécution en cours sur votre machine...`, `Analyseur de paquets réseau`, `Quel cerveau dois-je utiliser...`.
- **En capturas:** «MAJ LOGICIELS (WINGET)», «PROT. TEMPS RÉEL : ON», «WEBCAM PHYSIQUE», «CONNECTER MON C…», «CONNEXION AU NOYAU DE SÉCURITÉ», «[INTERROMPU] L'analyse antivirus a été annulée.», «LANCER UN SCAN ANTIVIRUS», «PRISES/CAPTEURS», placeholders «Nom/Chemin/Sujet/Nom vocal», «Dites… mets de la musique», «Utilisateur».
- **Voz:** con idioma Español, «VOZ DE LA IA = Henri – France 🇫🇷» (captura 132321).
- **Versión:** pie de app «VERSIÓN 10.5» (herencia plantilla) y seguridad «v2.6», cuando la release es 0.17.2 (capturas 131320, 131808).
- **Nota legal:** `cort-web/PROCEDENCIA.md` documenta que la plantilla TechEnClair no tiene licencia y el permiso no fue enviado. Traducir en origen mitiga pero no resuelve la atribución.

### E5 · P1 — Contenido de PC dentro de Android
- Ayuda de micrófono con pasos de **Windows** («Abre las Configuración de Windows → Privacidad…», capturas 132147-132311), rutas `C:\Users\Utilisateur\...`, apps Linux (`x-terminal-emulator`, `codium`), «WEBCAM», «GPU BOOST», «NVIDIA NEMOTRON ASR», «MAJ LOGICIELS (WINGET)», «INICIAR CORT AL ENCENDER EL EQUIPO».
- Algunos ya responden honestamente desde Java (Nexo.java:588, 705-734), pero la cara sigue ofreciéndolos. Falta filtrado por plataforma en la UI.

### E6 · P1 — El segundo plano y la accesibilidad existen en tu árbol pero NO en la APK publicada
- `ServicioEscucha.java` (foreground service microphone, Vosk wake word, corte a 5 min de silencio/pantalla apagada), `Pantalla.java` (AccessibilityService real: leer pantalla/escribir), `accesibilidad.xml`, `ServicioBajada.java`, `Sensores.java`, `PuenteWs.java`, `AutoCerebro.java`, `cort_tls.py`: **sin trackear** (`git status ??`). El README de v0.17.2 (L470) dice «no está, falta el código».
- Es decir: lo que pediste (escucha continua, tocar la pantalla por ti) ya está escrito en local, pero tu teléfono instalado no lo tiene.
- Límites reales ya contemplados en el código: Android 14 prohíbe arrancar FGS de micrófono con BOOT → se enciende desde app/baldosa QS (correcto). MediaSession: solo planificado.

### E7 · P1 — Lectura estilo podcast incompleta
- `Lectura.java`: «Leer con CORT» vía texto seleccionado/compartido (`ACTION_PROCESS_TEXT`/`ACTION_SEND`), trozos de 380 caracteres, velocidades 1.0/1.4/1.9, para al quitar audífonos. **No abre PDFs ni archivos completos** (tus apuntes de medicina).
- **AudioFocus/ducking: AUSENTE** en todo el repo. Nada baja la música cuando CORT habla (tu petición explícita).
- Lo bueno: TTS nativo es-ES funciona offline; el oído Vosk también. La base es correcta.

### E8 · P1 — Auto-actualización rota por repo privado
- Captura 131142: «el repositorio de CORT es privado: desde el teléfono, sin token, la etiqueta más alta no se puede leer · origen no disponible».
- Sin repo público (o manifiesto de versión público), «ACTUALIZAR CORT» nunca funcionará en teléfonos ajenos.
- **Aviso externo visto en tu captura de Chrome:** GitHub exige 2FA antes del **20 de diciembre de 2026**; actívalo ya o perderás acceso al repo.

### E9 · P2 — Antivirus: no-op honesto en Android, auditor (no AV) en PC
- Android: `av_scan_start` responde «en Android no hay procesos ni archivos que revisar» y cancela (Nexo.java:569-584). Capturas: INTERROMPU al 0%, mensaje en francés.
- PC: auditoría real de 4 pasos (autostart, procesos, dobles extensiones + firma EICAR, scripts escribibles) — informa, no bloquea ni tiene base de firmas (cort_server.py:570-753).
- No es un fallo de código sino de expectativa: en Android el sandbox impide escanear otras apps. Debe ocultarse o reconvertirse en «salud del dispositivo».

### E10 · P2 — 14 de 18 wallpapers son la misma imagen
- Verificado por CRC dentro de la APK: 14 archivos comparten CRC `46c36fd2` (203.835 B cada uno); solo 4 son distintos. ~2,6 MB desperdiciados y catálogo engañoso.

### E11 · P2 — Directorios fósiles de la plantilla
- `backend/`, `frontend/`, `apps/web/`, `services/` no los usa el producto. Confunden a cualquiera que lea el repo (y a los agentes que lo analizan).

### E12 · P2 — Tráfico LAN en claro
- `usesCleartextTraffic=true`; TLS del puente en progreso (`cort_tls.py` sin trackear, F14). En LAN doméstica el riesgo es acotado, pero la API del puente (8765/8766) sin TLS ni token es accesible por cualquier dispositivo de la red.

### E13 · P2 — Claim incoherente «SIN ENLACES DE SALIDA»
- Pie de Ajustes: «🔒 CONSTRUCCIÓN LOCAL — SIN ENLACES DE SALIDA» (captura 132408) con DuckDuckGo, Gemini, YouTube y Home Assistant configurados en la misma pantalla.

---

## 4. Tu visión JARVIS: qué es viable y cómo

| Deseo | Viabilidad | Camino |
|---|---|---|
| Cerebro liviano que funcione en el A16 | **Viable con ajustes** | Cuantización menor + contexto corto + mmap + puerta blanda (E2). 0.5B q4 con ctx 1024 puede correr; medir tokens/s real, no prometer |
| «Oye CORT» en segundo plano | **Ya escrito (F20), falta publicar** | ServicioEscucha + baldosa QS; Android 14+ no permite arranque con BOOT ni pantalla apagada infinita |
| Desbloquear el teléfono con la voz | **NO viable** | Android no permite saltar el keyguard seguro desde accesibilidad (es una barrera de seguridad del SO, no un bug). Sí: encender pantalla + mostrar sobre lockscreen |
| Mover la pantalla / escribir por ti | **Viable** | `Pantalla.java` (AccessibilityService) ya existe en tu árbol; gestos con `dispatchGesture`, escritura con `ACTION_SET_TEXT` |
| Leer apuntes/PDF por audífonos sin cortar música | **Viable** | Lector de archivos (PdfRenderer/texto) + `AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK` (E7). 100% offline con TTS nativo |
| «Pon alarma 4-8 pm», «agenda en calendario» | **Viable, fácil** | Intents nativos: `AlarmClock.ACTION_SET_ALARM`, `CalendarContract` — sin accesibilidad, permiso normal |
| Abrir nota «tema 15 MORFO 3» de Samsung Notes | **Parcial** | Intent de búsqueda/nota si la app lo expone; si no, accesibilidad + búsqueda por texto |
| Pasar info a WhatsApp / bloc de notas | **Viable** | `ACTION_SEND` a WhatsApp; escribir en notas vía accesibilidad o archivo local |
| Bloquear TikTok en estudio | **Parcial** | UsageStats + overlay de accesibilidad que devuelve al inicio; no puede matar apps ajenas. Alternativa honesta: modo foco con bienestar digital |
| «Eliminar procesos para jugar» | **NO viable como se imagina** | Android ya gestiona su RAM; una app no puede matar procesos de otras. Sí: liberar el propio cerebro GGUF y parar servicios al detectar juego |
| Antivirus real en Android | **NO viable** | Sandbox. Reconvertir en auditoría de permisos/salud (E9) |
| Investigar y guardar por ti | **Viable** | Ya hay Investigación.java en F20 + acciones del puente; falta el enrutado por complejidad («1-2 neuronas») = selección de modelo por tarea, no magia |

---

## 5. Plan de corrección priorizado por impacto

Esfuerzos = estimación de trabajo, no medición. Dependencias indicadas.

### P0 — Desbloquear lo esencial (empezar aquí)
| # | Acción | Errores | Esfuerzo | Resultado visible |
|---|---|---|---|---|
| P0-1 | Corregir unidades RAM: `libre / 1024 / 1024` en Nexo.java:972 y unificar cabecera/cuerpo a una sola fuente | E1 | ~1 h | «623 MB libres de 3653» — cifras creíbles |
| P0-2 | Cerebro utilizable en A16: unificar las dos puertas (936 vs 983), añadir Qwen2.5 0.5B q2_K/q4_0 al catálogo, contexto 1024, mmap, y «probar bajo tu riesgo» con tokens/s medidos en vez de bloqueo duro | E2 | 1-2 días | «probar el cerebro» responde de verdad en tu teléfono |
| P0-3 | Adaptación móvil: CSS responsive para paneles (overflow, anchos, safe-areas) + toggle Ajustes «vista escritorio / vista teléfono» (WebView wide-viewport conmutable) | E3 | 2-3 días | Nada cortado; tú eliges el modo |

### P1 — Lo que pediste explícitamente
| # | Acción | Errores | Esfuerzo | Depende |
|---|---|---|---|---|
| P1-1 | Commit + CI + release del trabajo F20 (ServicioEscucha, Pantalla/accesibilidad, ServicioBajada, TLS) | E6, E12 | 1-2 días | Probar en el A16 antes de publicar |
| P1-2 | Completar DICT con los strings dinámicos listados en E4; voz por defecto es-ES; versión real en el pie | E4 | ~1 día | — |
| P1-3 | Filtrado por plataforma: ocultar en Android lo de Windows/Linux/NVIDIA (winget, webcam, Nemotron, rutas C:\, ayuda Windows del micro) | E5 | 1 día | — |
| P1-4 | Podcast de apuntes: abrir PDF/texto completo + AudioFocus ducking + cola de lectura de principio a fin | E7 | 2-3 días | — |
| P1-5 | Actualizador: repo público (o manifiesto de versión público) + activar 2FA antes del 20-dic-2026 | E8 | ~2 h | Decisión tuya: hacer público el repo |

### P2 — Honestidad y limpieza
| # | Acción | Errores | Esfuerzo |
|---|---|---|---|
| P2-1 | Antivirus Android → «Salud del dispositivo» (o ocultar); renombrar el de PC como «auditoría», no AV | E9 | ~1 día |
| P2-2 | Deduplicar wallpapers (14 copias fuera) | E10 | ~1 h |
| P2-3 | Archivar/eliminar fósiles (`backend/`, `frontend/`, `apps/web/`, `services/`) | E11 | ~2 h |
| P2-4 | Quitar/arreglar el claim «sin enlaces de salida» | E13 | ~30 min |

### P3 — Visión JARVIS por hitos tocables (después de P0-P1)
1. **Órdenes del sistema por intent**: alarmas, calendario, abrir apps, compartir a WhatsApp (fácil, alto valor para tu estudio).
2. **Modo estudio**: lectura de apuntes + bloqueo suave de distracciones + recordatorios («recuérdame en 10 min»).
3. **Enrutado por complejidad**: tarea simple → 0.5B; investigación → modelo grande en PC vía puente; el «tercio de neuronas» se vuelve selección de modelo + presupuesto de contexto.
4. **MediaSession + escucha larga**: instrucciones ultra-detalladas sin corte de 5 min (subir el timeout con notificación visible).

### Lo que NO haremos (y por qué)
- Saltar el bloqueo de pantalla con voz: barrera de seguridad de Android, imposible legalmente desde una app.
- Matar procesos de otras apps / «antivirus» que escanee apps ajenas: el sandbox no lo permite; prometerlo sería mentira.
- Reescribir el bundle React de la plantilla: sin fuentes originales, el camino es completar el diccionario y ocultar lo que no aplica.

---

## 6. Nota sobre hardware (honestidad técnica)

Tu SM-A165M (Helio G99, 4 GB físicos + RAM Plus virtual): la RAM virtual es swap sobre almacenamiento — no sirve para inferencia y puede empeorar la latencia. El presupuesto real es ~600-900 MB libres según lo que tengas abierto. Un 0.5B bien cuantizado con mmap y ctx 1024 entra en ese presupuesto; un 1.5B q4 (2.235 MB de puerta) no entrará nunca en este teléfono — para eso está el modo «PC o nube» del catálogo, que ya existe (Cerebros.java:108-109).

---

*Auditoría realizada el 2026-11-08 sobre el repo local, la release v0.17.2 y 35 capturas. Evidencia completa citada por archivo:línea y por captura.*

---

## Adenda — P0-1 y P0-2 aplicados el 2026-11-08 (sin publicar aún)

**P0-1 (unidades RAM):** corregidas las 5 fugas de bytes-crudos en `Nexo.java` (`estadoCerebro`, `perfilReply` —que además decidía mal los FPS del orbe—, `iniciativa`, `pc_estado`). Cabecera y cuerpo ahora leen MB reales de la misma fuente.

**P0-2 (cerebro utilizable):**
- Regla nueva en `CerebroLocal`: puerta **holgada** = archivo + 200 MB de reserva (estimada, etiquetada como tal); **suelo de intento** = media puerta. El motor ya usaba mmap por defecto: los pesos son páginas desalojables, el ×2 anterior era innecesariamente duro. Sin cambios en C++ (no hay que recompilar la `.so`).
- «probar el cerebro» ya no bloquea: carga directamente y reporta código de error o tokens/s medidos. El modo `auto` intenta si hay suelo.
- Catálogo: nuevo **Qwen2.5 0.5B q2_K** (415.182.688 B, SHA-256 verificado contra la API de Hugging Face el 2026-11-08), contexto 1024 para los 0.5B. Con ~650 MB libres: puerta holgada 596 MB → **cabe**.
- Puerta unificada en un solo método (`puertaMB`): se acabaron el 936 vs 983.
- Textos actualizados en `Cerebros`, `Equipo`, `AutoCerebro` y la cara web; las 2 comprobaciones de `prueba_apk.py` que codificaban la regla vieja ahora verifican la nueva.

**Verificación local:** suite estática 231/231, sintaxis JS OK, catálogo cotejado contra HF. **Pendiente de verdad medida:** la compilación Java la verifica el CI (aquí no hay JDK completo) y los tokens/s reales hay que medirlos en el A16 con la APK nueva. Respaldo de todos los archivos tocados en `.respaldo-p0/` con sumas md5.