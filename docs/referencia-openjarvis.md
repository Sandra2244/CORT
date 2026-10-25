# Referencia · OpenJarvis (Stanford) — paso 0.1 de la Fase 0

**Escrito:** 2026-10-25 · **Base leída:** el repo clonado en `/home/Sandra/OpenJarvis`,
commit `a6dcf84` · **Licencia de lo leído:** Apache-2.0.

**Cómo se hizo esta lectura (y hasta dónde llega).** Se leyó el **código real** del
clon local: `frontend/src/` (la cara React de la app de escritorio),
`frontend/src-tauri/src/lib.rs` (el arrancador Rust), `src/openjarvis/` (el paquete
Python: `intelligence/`, `engine/`, `agents/`, `memory/`, `skills/`, `scheduler/`,
`security/`, `sessions/`, `cli/`, `server/`) y las páginas de
`docs/architecture/*.md` y `docs/showcase/*.md`. Cada afirmación lleva su
`archivo:línea`.

**Lo que NO se hizo, dicho en vez de fingido:** no ejecuté la app (quedan sin ver los
`.deb` y `.AppImage` de `~/Descargas` ni el `JARVIS-HRZ-3.1.0.exe`, que es otro
proyecto), no se abrió internet, y **no se copió una sola línea de su código ni un
recurso gráfico**. Lo que sigue es descripción y adaptación a nuestro stack; cuando
algún día entrara código suyo, tocaría conservar su aviso de licencia y la atribución.

Una nota de mapa: el directorio `desktop/` del repo está casi vacío (un binario de
Ollama y un `overlay.html`). La app de escritorio de verdad es `frontend/` envuelta
con Tauri en `frontend/src-tauri/`.

---

## 1. Mapa de pantallas

Rutas dentro de `Layout` (`frontend/src/App.tsx:184-193`; envoltorio
`components/Layout.tsx:27-73`):

| ruta | página | qué se ve |
| --- | --- | --- |
| `/` | `ChatPage` | `ChatArea` + `SystemPanel` (`pages/ChatPage.tsx:8-15`) |
| `/dashboard` | `DashboardPage` | «System Overview»: `EnergyDashboard`, `CostComparison`, `TraceDebugger` (`pages/DashboardPage.tsx:14-31`) |
| `/data-sources` | `DataSourcesPage` | conexiones a Gmail, Slack, iMessage, etc. |
| `/agents` | `AgentsPage` | agentes autónomos y sus tareas |
| `/logs` | `LogsPage` | registro en texto; vacío dice «No log entries yet…» (`pages/LogsPage.tsx:72`) |
| `/settings` | `SettingsPage` | tema, URL del backend, clave, modelo por defecto, temperatura, `maxTokens`, voz; export/import y «Clear all data» |
| `/get-started` | `GetStartedPage` | detecta host/desktop/selfhosted y ofrece instaladores (`pages/GetStartedPage.tsx:32-79`) |

La navegación vive en la barra lateral (`components/Sidebar/Sidebar.tsx:55-63`),
colapsable (`:68-84`), y en su cabecera hay un **distintivo del modelo activo que abre
la paleta** (`:130-169`) más un buscador de chats (`:171-187`). Atajos: `⌘/Ctrl+K` abre
`CommandPalette`, `⌘/Ctrl+I` alterna el panel lateral (`App.tsx:161-174`).

Dos piezas que nos interesan por principio (A4 «transparente»):

- **`SystemPulse`**: una barra de 3 px en toda la pantalla que cambia según
  `idle` / `inferencing` / `agent-active` (`components/SystemPulse.tsx:5-20,48-58`).
  El estado del sistema se ve sin abrir ninguna pantalla.
- **`ApprovalBell`**: campana de aprobaciones pendientes de los agentes
  (`components/ApprovalBell.tsx:83`, texto «Agent approvals»). La aprobación de una
  acción irreversible tiene un lugar fijo en la cara, no en un diálogo suelto.

## 2. Los modelos: cómo los representan y cómo los descargan

**Un modelo es un dataclass `ModelSpec`** con campos
`model_id, name, parameter_count_b, context_length, active_parameter_count_b,
quantization, min_vram_gb, supported_engines, provider, requires_api_key, metadata`
(`docs/architecture/intelligence.md:27-40`). **No hay tamaño en bytes, ni ruta, ni
campo «instalado»**: el tamaño se infiere de los parámetros y la licencia es una clave
libre de `metadata` (por ejemplo `"license": "apache-2.0"` en
`src/openjarvis/intelligence/model_catalog.py:572`). La ruta de pesos es del config, no
del catálogo (`intelligence.md:135-136`).

**El catálogo está embebido en Python**, no es JSON ni se descarga:
`BUILTIN_MODELS: List[ModelSpec]` en `intelligence/model_catalog.py:10-1067` (~50
entradas: Qwen3/3.5, Llama, MoE, GGUF de Unsloth, y modelos de nube con
`pricing_input/output`). Se registran con `register_builtin_models()` (`:1084-1088`) y
lo que el motor tenga instalado se **fusiona** con `merge_discovered_models()`
(`:1091-1102`). `~/.openjarvis/` guarda config y estado, no el catálogo.

La lista que ve el usuario para descargar es otra cosa: **12 modelos escritos a mano**
con su talla aproximada en texto —`{ id: 'qwen3.5:4b', size: '~3.4 GB', desc: 'Qwen 3.5
4B — recommended default' }`— en `frontend/src/components/CommandPalette.tsx:15-28`, más
un campo libre «Or enter any Ollama model name:» con su botón «Pull» (`:435-453`) y un
pie que aclara de dónde vienen: «Models are downloaded from the Ollama registry»
(`:569`).

**El flujo de descarga, medido en el código.** Hay tres caminos y solo uno tiene
progreso:

1. CLI `jarvis model pull` → `ollama_pull()` hace `POST {host}/api/pull` con
   `stream: true`, lee NDJSON, calcula `% = completed / total` y lo pinta con
   `\r` (`src/openjarvis/cli/model.py:156-194`, el cálculo en `:169-186`).
2. HTTP `POST /v1/models/pull` → vuelve a pedirlo a Ollama con **`stream: false`**,
   espera y responde `{"status":"ok"}`; si el motor no es Ollama devuelve 501
   (`src/openjarvis/server/routes.py:1150-1185`, el 501 en `:1161`).
3. App de escritorio → comando Tauri `pull_ollama_model` → `pull_model()` en Rust con
   **600 s de_timeout y `stream: false`** (`frontend/src-tauri/src/lib.rs:2429-2436`,
   `:753-769`); la cara prefiere Tauri y si no usa HTTP
   (`frontend/src/lib/api.ts:201-222`, donde `pullModel(): Promise<void>`).

**Consecuencia, y es un hecho no una opinión: la pantalla de modelos del escritorio no
tiene barra de progreso.** El botón solo tiene tres apariencias —spinner con
«Downloading...», «Installed» y «Download» (`CommandPalette.tsx:428-430`)—, el éxito
dice «Downloaded {id} successfully» (`:336-340`) y el error pinta en rojo el mensaje
del backend o «Download failed» (`:331-335,186`). La única barra con porcentaje del
repo es la de **actualización de la propia app**: «Downloading update... {progress}%»
(`components/Desktop/UpdateChecker.tsx:135`). El progreso real vive en la CLI.

**Reanudar, cancelar, poner en cola y comprobar espacio libre: no lo implementa
OpenJarvis.** Busqué `resume`, `Range`, cancelación y verificación de disco en
`cli/model.py` y en el pull de Rust: no están. Si el modelo falla al arrancar, el
arrancador reintenta con uno ya instalado y cae a `FALLBACK_MODEL = "qwen3:0.6b"`, y si
eso tampoco, muestra el error (`lib.rs:1074-1105`). Los archivos los guarda el daemon
de Ollama; OpenJarvis no toca esa ruta. Por HF delega en `huggingface-cli download`
(`cli/model.py:205-223`).

## 3. Estados, con el texto literal que muestran

| estado | qué ve la persona | dónde |
| --- | --- | --- |
| descargando | spinner + «Downloading...», botón deshabilitado | `CommandPalette.tsx:428-430` |
| descargado | «Installed» y «Downloaded {id} successfully» | `:430`, `:336-340` |
| fallo | `pullError` en rojo con el texto del backend o «Download failed» | `:331-335,186` |
| sin modelos | «No models available — switch to "Download" to get started» | `:352-354` |
| modelo elegido pero cargando | «Loading model...» con spinner en la barra lateral | `:146-164`; `Sidebar.tsx:141-158` |
| nube conectada | casilla de clave con ojo, distintivo «Connected» y «Remove», nota «API keys are stored locally and never sent to OpenJarvis servers» | `:37-74,459-571` |
| backend caído | banner global «Cannot reach OpenJarvis backend» + enlace «Change URL», sondeo cada 30 s | `components/Layout.tsx:16,33-47` |
| sin modelo elegido | aviso «Pick a model first (⌘K)» y el placeholder del input lo repite | `InputArea.tsx:178`, `:611` |
| borrando | papelera en cada fila (título «Delete model», aviso «Deleted {model}») | `CommandPalette.tsx:389-401`, `:202` |
| primer arranque | tres pasos con «Ready»/«Waiting...» y barra al `pasos × 33,33 %` | `SetupScreen.tsx:14-18`, `:61`, `:246-263` |

Los textos están en inglés; lo que tomamos es la **variedad de estados**, no las
cadenas (nuestra cara va en español y con su tuteo).

## 4. La Charla, que es lo que a Sandra le gustó

- **Persistencia:** conversaciones en `localStorage` bajo la clave
  `openjarvis-conversations` (`frontend/src/lib/store.ts:37,57-92`) y el título se
  deduce de los **primeros 50 caracteres** del primer mensaje del usuario
  (`store.ts:420-424`). No hay renombrar. La lista lateral muestra tiempo relativo
  («Just now», «5m ago»…) y **deshabilita la papelera mientras hay generación en
  curso**, con el título «Stop generating before deleting this conversation»
  (`components/Sidebar/ConversationList.tsx:9-19,84-103`). Buscar es solo por título
  (`Sidebar.tsx:180`). Vacío: «No conversations yet» / «No matching chats»
  (`ConversationList.tsx:40`).
- **Render:** `ReactMarkdown` con `remarkGfm`, `remarkMath`, `rehypeHighlight`,
  `rehypeKatex` y un plugin propio de citas `rehypeCitations`; se eliminan las etiquetas
  `<think>`; los bloques de código llevan cabecera con el lenguaje y botón
  «Copy»/«Copied» (`components/Chat/MessageBubble.tsx:16-20,40-80,118-122,169-177`).
- **Transparencia por mensaje:** el pie `XRayFooter` suma capa de complejidad, tiempo
  total, tokens de entrada y salida, y al desplegar dice `Engine: <motor> (<model_id>)`
  (`components/Chat/XRayFooter.tsx:28-49`). Esto es exactamente el principio A4
  «dice qué modelo y qué herramienta usó».
- **Streaming:** contenido acumulado con vaciado cada 80 ms (`InputArea.tsx:314,442-449`),
  puntos animados con fase legible —«Generating...», «Agent thinking...», «Calling
  {tool}...», «Researching...», «Searching: {query}»—
  (`components/Chat/StreamingDots.tsx:5-28`; `InputArea.tsx:238,268,385-403`), botón
  rojo de parada (`:617-625`) y al abortar deja escrito «(Generation stopped)»
  (`:459`). Sin respuesta: «No response was generated. Please try again.» (`:473-475`).
- **Modos:** un único interruptor «Deep Research» con aviso de sincronización
  («Searching over N items — sync in progress…», `:568-596`). No hay presets de
  explicar/resumir/traducir, ni regenerar, ni editar un mensaje, ni leer en voz alta
  por mensaje, ni adjuntar archivos (el icono `Paperclip` está importado en
  `InputArea.tsx:2` y nunca se pinta). Nuestros cuatro modos (Normal, Explícame,
  Resume, Traduce) son nuestros y no tienen referencia en ellos.

## 5. Hardware detectado y recomendación (la fórmula real)

`detect_hardware()` está en `src/openjarvis/core/config.py:249-258`. NVIDIA por
`nvidia-smi` (nombre, VRAM de MB a GB, unidades, `compute_cap`) en `:114-141`; AMD por
`rocm-smi --showmeminfo vram` en `:144-176`; en Apple la VRAM es la RAM total del
sistema porque la memoria es unificada (`:179-192`); la RAM por `sysctl hw.memsize` o
`/proc/meminfo` (`:212-240`).

- Memoria utilizable: con GPU, `vram_gb × unidades × 0,9`; sin GPU, `(ram_gb − 4) × 0,8`
  (`config.py:288-295`).
- Tabla de niveles, literal (`config.py:302-308`): ≤8 GB → `qwen3.5:2b`, ≤16 → `4b`,
  ≤32 → `9b`, ≤64 → `27b`, respaldo `qwen3.5:27b`. Usan MoE porque «solo una fracción
  de parámetros está activa por token» (comentario en `:298-301`).
- Peso estimado de una descarga: `param_b × 0,5 × 1,1` GB (cuantización Q4_K_M)
  (`config.py:358-360`).
- El arrancador Rust aplica otra regla: `default_local_model(ram_gb)` (`lib.rs:93-100`)
  toma **el segundo más grande de los que caben** (`fitting[n - 2]`), con respaldo en
  `FALLBACK_MODEL` si no cabe ninguno, y la tabla de tallas con umbrales 4/6/8/12/24/32/96
  GB está en `lib.rs:22-30`.

Los motores soportados, en su tabla (`docs/architecture/engine.md:109-124`): Ollama,
vLLM, SGLang, llama.cpp, MLX, LM Studio, Exo, Nexa, Lemonade, Uzu, Apple FM, LiteLLM y
nube, sobre una base `_OpenAICompatibleEngine` (`:345-352`).

## 6. Enrutado y caída de motor

Orden de preferencia: bandera de CLI → `intelligence.preferred_engine` →
`engine.default` → primer motor sano (`intelligence.md:206-211`). En
`engine/_discovery.py:176-255`: un motor pedido explícitamente **nunca se sustituye**
(`:208-216`), y el por defecto cae a candidatos sanos priorizando **la misma clase**
(local con local, nube con nube); «sano» exige `health()` y `can_serve(model)`
(`:198-199`, lógica `:240-255`). `MultiEngine` enruta por nombre de modelo y los
prefijos `gpt-`, `claude-`, `gemini-`, `openrouter/` van a nube, pero **un modelo local
no cae en silencio a la nube: lanza `ValueError`** (`engine/multi.py:43-70`). Hay un
`HeuristicRouter` que elige local/nube por tamaño con respaldo
`default_model → fallback_model → primer disponible` (`learning/routing/router.py:112-181`,
nivel nube `:54-68`).

**Cuotas y pool de claves: no existen.** Una clave por variable de entorno
(`engine.md:165-168`), una clave por proveedor guardada en el almacén seguro del sistema
(`lib.rs:2421-2426`), y solo hay `estimate_cost()` (`cloud.py:206`). Nuestro T20
(pool con cuotas y recambio cuando una se agota) **no tiene referencia en OpenJarvis**:
lo tendremos que diseñar nosotros.

## 7. Memoria, habilidades, agentes y horario

**Memoria en dos capas.** Conversaciones en SQLite `~/.openjarvis/sessions.db`, con
consolidación al pasar de 100 mensajes (`sessions/session.py:66-77,229-237`) y
`decay(max_age_hours)` para purgar (`:268`). Hechos persistentes en JSONL
`~/.openjarvis/memory_facts.jsonl` con bloqueo multiproceso (`memory/store.py:74-76,94`);
un `FactExtractor` pide al modelo «preferences, identity, goals, ongoing projects»
(`memory/extractor.py:25,55`), cada hecho lleva confianza y se promociona tras revisión
(`store.py:138,193`), y existe `clear_facts()` (`memory/service.py:250`). Además hay
**tres markdown por personaje** —`SOUL.md`, `MEMORY.md`, `USER.md`— que se leen al
construir el prompt (`prompt/builder.py:266,285-287`) y se editan a mano. La
recuperación de documentos usa un ABC `MemoryBackend` con SQLite/FTS5 (BM25) por defecto,
FAISS con `all-MiniLM-L6-v2`, ColBERTv2 o híbrido con RRF; la inyección va como mensaje
system con etiquetas `[Source: …]`, `top_k=5`, `min_score=0.1` y tope de 2048 tokens
(`docs/architecture/memory.md`). **Backup de memoria: no lo tienen** (solo copian sus
`.md` a iCloud, `docs/showcase/persistent-memory.md`), así que nuestro T22 sí añade algo.

**Habilidades en archivos, con nombre.** `SKILL.md` con front-matter compatible con
agentskills.io —campos `name, description, license, compatibility, metadata,
allowed-tools`, obligatorios `name` y `description`— o `skill.toml` por pasos; una
carpeta es un skill si contiene uno de los dos (`skills/parser.py:1-6,33`;
`skills/manager.py:409`). Se descubren escaneando directorios por orden de precedencia
(`manager.py:68-80`), las dependencias se validan con detección de ciclos y profundidad
máxima 5. Cada skill se envuelve como `SkillTool(BaseTool)` y se genera un catálogo XML
`<available_skills>` en el system prompt **para que sea el modelo quien lo invoque**
(`docs/architecture/skills.md`); no hay activación determinista por frase. Nuestros 736
patrones de Mente sí lo son: en esto CORT responde más rápido y sin red.

**Agentes.** Contrato único `BaseAgent.run(input, context) -> AgentResult`; el
`OrchestratorAgent` itera generar → ¿hay `tool_calls`? → ejecutar → añadir el resultado
como mensaje TOOL, hasta la respuesta final o `max_turns`
(`docs/architecture/agents.md`). `NativeReActAgent` parsea
Thought/Action/Action Input/Observation con `Final Answer:`. El doc dice ocho tipos,
pero el código registra ~20 claves (`agents/simple.py:11`, `orchestrator.py:31`,
`native_react.py:131`, `rlm.py:133`, `deep_research.py:158`, `morning_digest.py:41`,
`proactive_agent.py:294`, siete híbridos en `agents/hybrid/`…). Límites: `max_turns=10`
por defecto y `LoopGuard` corta llamadas idénticas repetidas y presupuesto de 5 llamadas
a una herramienta de sondeo (`agents/loop_guard.py:20,94-118`); **no hay presupuesto
global de tokens ni de tiempo por misión**. Herramientas: ABC `BaseTool` con `spec`,
`execute(**params)` y `to_openai_function()`, despacho por nombre con latencia y eventos
`TOOL_CALL_START/END`, registro con `@AgentRegistry.register("nombre")`.

**Horario.** Scheduler propio (`scheduler/scheduler.py:1,28-29,92-119`) con
`schedule_type ∈ {cron, interval, once}`, hilo que consulta cada 60 s, persistencia
SQLite y registro de ejecuciones. No es systemd: el «Morning Brief» se arma con agente
`orchestrator` + canales + scheduler en un TOML (`docs/showcase/morning-brief.md`) y un
agente dedicado `morning_digest.py:41`. Canales: ABC `BaseChannel` con seis métodos y
**hilo daemon de escucha en lugar de asyncio** (~30 canales: telegram, discord, slack,
whatsapp, signal, matrix, email, irc).

**Seguridad (esto sí lo queremos tal cual).** Ciclo **proponer → aprobar → ejecutar**
con `ApprovalStore` y respuestas por canal («yes», «always yes {id}», «no all»)
(`tools/proactive_tools.py:5-20,119`) más rutas HTTP de aprobación
(`server/approval_routes.py`). Capacidades por agente y recurso con
`CapabilityPolicy.grant/deny/check` (`security/capabilities.py:48-96`). Caja aislada:
`ContainerRunner` con `docker run --rm --network none`, lista blanca de montos y patrones
bloqueados (`.ssh`, `.env`, `*.pem`). `GuardrailsEngine` escanea entrada y salida con
detectores de secretos y PII en modos WARN/REDACT/BLOCK, `BoundaryGuard` limpia antes de
salir a nube, la política de archivos impide leer sensibles y excluirlos de la ingesta,
y hay auditoría solo-append en `~/.openjarvis/audit.db` (`docs/architecture/security.md`).
Su límite declarado: en streaming el bloqueo de salida es posterior, solo se aplica de
verdad a la entrada.

## 8. Qué se adapta a CORT, qué no, y qué no existe en la referencia

**Se adapta (Fase 2 en adelante).**

1. Separar catálogo embebido (lo que *podría* instalarse) de lo descubierto en el motor
   (lo que *está*), y fusionarlos en una sola lista: `model_catalog.py:1084-1102`.
   Nuestro `catalogo-modelos.json` puede copiar esa estructura, no sus valores.
2. Campos `min_vram_gb`, `quantization`, `parameter_count_b`, `active_parameter_count_b`
   como base de «Cerebro»; añadirle nosotros los que OpenJarvis no tiene: bytes reales y
   estado instalado.
3. Recomendación por hardware con fórmula pública (`config.py:288-308`) en vez de
   tamaños adivinados: es literalmente lo que pide A5 («el gestor de modelos recomienda
   según el hardware detectado»).
4. `XRayFooter`: transparencia por respuesta (modelo, motor, tiempo, tokens) → nuestro
   «la interfaz muestra qué modelo respondió».
5. `SystemPulse` de 3 px para el estado del nodo → nuestra franja de «PC / teléfono /
   sin conexión», barata y sin tocar el orbe.
6. Tres estados de botón (descargar / descargando / instalado) y el distintivo «Active»
   en el sidebar: la paleta de modelos visible en la cara.
7. `propose → approve → execute` con campana de aprobaciones → T18/T19 (acciones) y
   nuestra regla de «confirmación en lo irreversible».
8. `SOUL.md` / `MEMORY.md` / `USER.md` editables a mano → T22 (memoria y habilidades
   como archivos). Es el mismo espíritu y se entiende sin programa.
9. Sondeo de salud cada 30 s con banner «Cannot reach backend» + enlace «Change URL» →
   nuestro nodo PC apagado, dicho en español y con la frase que nombra `OLLAMA_HOST`.

**No se adapta a nuestro stack (y no lo vamos a forzar).**

- React + Tauri + zustand + Vite: nuestra cara es HTML/JS modular dentro de un WebView
  sin Node en el aparato. Tomamos pantallas y estados, no componentes.
- `localStorage` para el historial: en Android el almacenamiento de la cara no es
  fiable para datos que la dueña quiere conservar; nuestro historial debe vivir del lado
  de Java (`CortNative`) o del backend, no del navegador.
- Scheduler con hilo de sondeo cada 60 s dentro del proceso Python: en el teléfono eso
  lo hacen `AlarmManager` y nuestro `Alarma.java`, que ya existe.
- Docker con `--network none` para aislar herramientas: no hay Docker en el teléfono ni
  en su portátil; nos quedamos con la idea de lista blanca de rutas y patrones bloqueados.
- Canales por hilo daemon (~30 mensajería): no es nuestra prioridad y cada uno pediría
  permisos que no vamos a añadir sin autorización.
- Modelos MoE Qwen3.5 y su catálogo de ~50 entradas: son sus valores, no los nuestros;
  el nuestro se arma contra el `ollama list` real de su PC.

**No existe en OpenJarvis, aunque nuestro mega prompt lo da por tomado de ahí.**

- Barra de progreso de descarga (porcentaje, bytes, velocidad). Solo spinner en la app;
  el progreso real está en la CLI.
- Pausar, reanudar o cancelar una descarga, y cola de descargas simultáneas.
- Comprobación de espacio libre antes de descargar.
- Pool de proveedores con cuotas y recambio automático.
- Página dedicada de modelos (es un modal de la paleta), renombrar conversación, buscar
  por contenido, regenerar, editar un mensaje, leer en voz alta una respuesta, adjuntar
  archivos, modo «explicar/resumir/traducir».

## 9. Propuesta de pantalla «Cerebro» (para la Fase 2, sin código todavía)

La regla del documento: no afirmar nada de su interfaz que no se haya leído —ya está
leído— y luego **no copiar su pantalla, sino superarla donde la nuestra sea más honesta**
(principio A3: la interfaz solo muestra lo que el aparato confirma).

Bloques, de arriba abajo:

1. **Cabecera con el nodo.** «Cerebro de <nombre del aparato> · Ollama <versión> ·
   <X GiB libres>». Si el PC no responde: «El portátil no respondió (hace 12 s) ·
   usando lo que hay en el teléfono». Nada de `undefined`. *(Del `SystemPulse` + el
   banner de `Layout.tsx:16,33-47`, en español y con nombres de aparato.)*
2. **Recomendación por hardware, con la fórmula a la vista.** «Tu PC tiene 8 GB de RAM
   libre aprovechable → cabe un modelo de hasta ~4 B». *(De `config.py:288-308`;
   mostramos el cálculo, no solo el resultado, para cumplir «transparente».)*
3. **Lista de modelos en tres grupos**: instalados · disponibles para descargar ·
   de nube desactivados. Cada fila: nombre, familia, parámetros, peso **real en bytes**
   (el nuestro lo lee de Ollama; OpenJarvis no lo tiene), barra de espacio que ocupa, y
   qué nivel de la tabla A5 sirve (básicas / conversación / investigación).
4. **Estados por fila**, con texto español y siempre completo:
   `sin instalar` · `descargando 34 % (1,2 GB de 3,4 GB · 4,1 MB/s · queda ~9 min)` ·
   `pausado` · `listo` · `en uso` · `falló: se acabó el espacio` ·
   `falló: el portátil se apagó a mitad`. *(Aquí es donde CORT hace lo que la referencia
   no hace: progreso real, pausar, cancelar y avisos que dicen qué falló.)*
5. **Barra de progreso con capas**, no con bytes sueltos: Ollama informa por NDJSON con
   `completed/total`, que es justo lo que nuestra 2.9.0 ya aprendió a sumar capa por capa
   en vez de quedarse con la última línea. *(La idea de la fuente es la de
   `cli/model.py:169-186`; la suma por capas es nuestra.)*
6. **Cola abajo**: qué está bajando, qué espera, y un solo «✕ cancelar» que suelte la
   conexión abierta del teléfono (ya existe desde la 2.9.0).
7. **Asignación por nivel**: tres huecos —básicas, conversación, investigación— cada uno
   con su modelo elegido y un «probar» que manda una frase corta y dice cuánto tardó. El
   enrutador (T8) lee esos tres huecos.
8. **Borrar** con confirmación explícita y su lista de lo que se va a borrar, como exige
   A3 en las acciones destructivas.

Qué falta antes de dibujarla: leer las pantallas de los 14 vídeos de
`Referencias IA CORT` y las 17 capturas de `CORT IA App` (su teléfono con la 2.11.0),
para que la propuesta contraste con lo que ella ya ve, y la 0.2/0.3 de esta fase.

## 10. Choques entre esta lectura y el mega prompt v2

Lo digo aquí para que lo respondas antes de la Fase 2, no para improvisar después:

1. **B1 dice «Engine… autodetecta el hardware y recomienda»**: es cierto y está medido
   arriba. **Pero la tabla A5 de niveles (0,5–3B / 7–8B) no coincide** con la de
   OpenJarvis (2B / 4B / 9B / 27B por RAM, con MoE de parámetros activos). ¿Nivel medio
   son 7–8 B denso o 9 B MoE? *(Mi recomendación: dejar la tabla A5 como intención y
   llenar los números con lo que confirme `ollama list` + la RAM de tu portátil.)*
2. **T7 pide progreso en streaming, pausar, cancelar y reanudar** como si fuera el patrón
   de OpenJarvis. **Pausar y reanudar no existen en él.** Los diseñamos nosotros contra
   el NDJSON de Ollama; se puede, pero es diseño nuestro, no referencia.
3. **T20 (pool con cuotas)**: tampoco hay nada que copiar; OpenJarvis tiene una clave por
   proveedor. El pool es invención nuestra.
4. **T6 (Charla)**: lo que te gustó de ellos es el render con citas, la transparencia por
   mensaje y la lista lateral con tiempo relativo. **Renombrar, exportar por chat,
   adjuntar y leer en voz alta no los tienen** → hay que construirlos, no adaptarlos.
5. La frase de B1 «Descargas (incluye la app de escritorio con interfaz gráfica)» puede
   leerse como que esa app gestiona descargas con barra: **gestiona descargas, sin barra**.

## 11. Lo que quedó sin leer o sin comprobar

No ejecuté nada, así que no sé de primera mano: cómo se ve realmente la ventana de
Tauri (los `.deb`/`.AppImage` de `~/Descargas`), el aspecto del `overlay.html` de
`desktop/`, ni el comportamiento de las rutas `docs/deployment/*` y
`docs/development/mining*` (minería de «perlas» en Apple Silicon y vLLM), que no tocan
a CORT pero son buena parte del repo. Las cifras de coste/ahorro de
`docs/showcase/cost-savings.md` tampoco las he verificado; no las uso.

---

**Atribución y licencia.** OpenJarvis es de Hazy Research y del Scaling Intelligence Lab
de Stanford, bajo **Apache-2.0**:
<https://github.com/open-jarvis/OpenJarvis> · <https://openjarvis.stanford.edu/> ·
<https://open-jarvis.github.io/OpenJarvis/> · <https://arxiv.org/abs/2605.17172>.
Este documento es descripción y análisis para adaptar conceptos; no contiene código suyo
ni recursos gráficos suyos.
