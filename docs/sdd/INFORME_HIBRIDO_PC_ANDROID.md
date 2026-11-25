# Informe híbrido PC y Android — CORT

- **Fecha:** 2026-11-24
- **Estado:** BORRADOR para decisión de producto; no es una SPEC aceptada.
- **Método:** inspección estática de CORT y cuatro proyectos de referencia. No se ejecutaron los proyectos de referencia, no se usó red para probarlos y no se probó el A16.
- **Alcance:** identificar qué conviene conservar, qué está bloqueando la estabilidad y cómo combinar reglas, cerebro local y nube sin perder privacidad ni control.

## 1. Conclusión corta

CORT no necesita copiar a JARVIS ni a Cortana. Necesita una **arquitectura común con adaptadores honestos**:

1. Android resuelve primero lo que puede resolver en el teléfono.
2. La PC aporta potencia, herramientas y supervisión cuando está disponible.
3. Las reglas ejecutan acciones deterministas sin cargar un modelo.
4. El cerebro local interpreta cuando aporta; la nube sólo se usa con consentimiento y presupuesto.
5. Toda herramienta declara permisos, plataforma, costo, confirmación y forma de verificar el resultado.
6. Si falta un recurso, CORT lo dice y degrada; no bloquea la interfaz ni promete una capacidad inexistente.

La prioridad sigue siendo **cerrar P0 antes de expandir funciones**. El trabajo híbrido debe construirse sobre un puente estable, una vista táctil usable y una escucha en segundo plano confiable.

## 2. Qué se verificó en CORT

| Área | Hecho de código | Consecuencia |
|---|---|---|
| Vista Android | La adaptación móvil enumera paneles concretos en `cort-web/cort/cort-style.css:532-555` | Un panel nuevo puede quedar fuera de la regla móvil; falta una adaptación estructural |
| Trabajo en interfaz | `apps/android/src/dev/sandra/cort/movil/Nexo.java:311-317` despacha pedidos del puente con `runOnUiThread` | Una respuesta lenta puede competir con dibujo y botones |
| Sondeo de interfaz | `cort-web/cort-ui.js:2633-2640` recorre `document.body` cada tres segundos | Hay costo permanente que debe medirse antes de optimizarlo |
| Ciclo de WebView | `Nexo.cerrar()` anula la WebView sin llamar a `destroy()` | Puede quedar trabajo o recursos asociados |
| Segundo plano | `ServicioEscucha.java:279-324` detiene el micrófono al apagar pantalla y a los cinco minutos | La preferencia puede decir «despertador» aunque el servicio ya no escuche |
| Permiso de micrófono | `MainActivity.java:112-118` inicia `arrancaSiTocaba` sin comprobar `RECORD_AUDIO` | El estado visible debe reflejar el permiso real |
| Saludo de reinicio | `Arranque.java:32-47` publica antes del TTS y mantiene el receptor quince segundos | Android puede limitar la entrega; la demora física aún no está atribuida |
| GGUF/RAM | La puerta quedó aislada y probada en `SPEC-ANDROID-001`; commit `6755e62`, run `45516435873` verde | La decisión numérica ya es reproducible; cargar el modelo en el A16 sigue pendiente |
| Integridad GGUF | La descarga valida tamaño y SHA, pero `Bajada.esta()` sólo comprueba `isFile()` | Un archivo persistido puede presentarse como verificado sin revalidar su suma |
| Errores nativos | `nativeAbrir` usa códigos 1/2/3 y Java convierte una respuesta vacía en `null` | La persona puede recibir un error técnico sin causa accionable |
| Nube en PC | La UI enumera Gemini, Groq, xAI, OpenAI, Anthropic y Mistral en `cort-web/index.html:2722-2734`; la ruta real de chat usa Ollama en `cort-bridge/cort_server.py:1248-1304,2525-2598` | No hay failover ni proveedor nube real en PC; la interfaz promete más de lo que ejecuta |
| Gemini | `Nube.java:107-181` implementa Anthropic y OpenAI-compatible, no Gemini; el modal WebView no alimenta esa configuración nativa (`Nexo.java:1929-1947`) | Una clave escrita en Ajustes no necesariamente configura el cerebro del teléfono |
| Secretos | La web guarda `api_keys` dentro de `currentSettings` en `localStorage` (`cort-web/cort/cort-mock.js:364-368,519-523`); Android usa `SharedPreferences` en claro (`Nube.java:23-27,37-77`); el puente acepta campos arbitrarios al guardar (`cort_server.py:2093-2106`) | Hay que retirar claves de almacenamiento general y llevarlas a keyring/Keystore antes de ampliar proveedores |
| Modo local | `Cara.java:343-356` consulta GGUF y, si devuelve `null`, usa la nube configurada | El modo «local» puede enviar texto aun cuando el motor local falle; debe respetar la privacidad elegida |
| Cancelación | Cerrar el WebSocket sólo cancela el redactor (`cort_server.py:1376-1382`), no la inferencia; `Nube.java:184-225` no tiene cancelación y el GGUF no tiene timeout de reloj | Una petición puede seguir consumiendo recursos después de que la persona se va |
| Paridad de herramientas | PC limita siete verbos y verifica archivos (`cort_intenciones.py:44-71,163-219`; `cort_archivos.py:163-221`); Android usa reglas exactas y no tiene herramientas LLM equivalentes | La promesa de «las mismas funciones» todavía no tiene contrato común |
| Pruebas híbridas | `scripts/prueba_nucleo.py:152-236` cubre Ollama simulado y reja; `scripts/prueba_apk.py:649-724` cubre JNI/RAM | Faltan pruebas de nube, secretos, fallback, cancelación y rendimiento físico |
| Puente PC | `cort-bridge/cort_voz.py:108-109` ejecuta `pactl` con bloqueo y timeout de cuatro segundos | El audio puede detener el bucle de servicio |
| Tareas PC | `cort-bridge/cort_server.py:2510` crea tareas sin registro ni límite | No hay backpressure, cancelación ni garantía de respuesta terminal |
| Timeouts | Android usa esperas cortas; el puente admite esperas de noventa y 180 segundos | Las dos plataformas no comparten contrato de latencia |
| Capacidades | Auditoría, webcam y antivirus se presentan desde conceptos de PC | Android debe declarar «no disponible» o una capacidad distinta, no imitarlas |

Estos hallazgos explican riesgos concretos, pero **no identifican por sí solos la causa física de cada trabón**. Falta medir en el A16 y en la PC real.

## 3. Qué aportan las referencias

Base de las carpetas de referencia: `/home/Sandra/Documentos/bases o proyectos git `.

| Proyecto | Lo útil | Lo que no conviene copiar | Licencia observada |
|---|---|---|---|
| `J.A.R.V.I.S-master` | Flujo simple voz → texto → intención → acción; confirmación contextual del diccionario | No tiene LLM, router ni herramientas declaradas; usa `exec`, rutas Windows y esconde fallos; audio e IP salen a servicios externos | MIT en raíz; Apache-2.0 en `Face-Recognition` |
| `jenny-android-ai-agent-main` | WebView mismo-origen, servicio desacoplado, registro explícito de herramientas, guardas workspace/SSRF, memoria atómica | Claves en texto plano con backup, Chaquopy pesado, `python_exec` sin sandbox, autoactualización y launcher | AGPL-3.0-only |
| `LinuxJarvis-main` | Bus pub/sub, acciones como adaptadores, audio y memoria separados, cola priorizada | Proveedor Gemini único; código generado para herramientas desconocidas; éxito por «no hubo excepción»; `shell=True` | MIT |
| `OpenJarvis-main` | Composition root, contratos y registros, multi-motor, trazas, evaluación de coste/latencia/energía, memoria con procedencia | Complejidad Rust/PyO3 y muchos crates; estado Alpha; no trasladar toda su arquitectura a un teléfono modesto | Apache-2.0 |

**Regla de licencia:** adoptar patrones no autoriza copiar implementaciones. Jenny es AGPL y CORT tiene documentación de licencia contradictoria (`CORT-DOC-001`). No se copiará código de referencia hasta resolver la licencia de CORT y revisar compatibilidad, avisos y marcas.

## 4. Arquitectura objetivo propuesta

```text
Voz / texto / panel
        │
        ▼
Normalizador de intención
        │
        ▼
Reglas deterministas ───────────────► resultado verificable
        │ no resuelve
        ▼
Router híbrido
  ├─ GGUF / Ollama local, si hay presupuesto
  ├─ proveedor nube, sólo con consentimiento
  └─ degradación honesta sin red o sin recursos
        │
        ▼
Registro de capacidades → validador → ejecutor → verificador
        │
        ▼
Estado, auditoría y memoria local
```

### 4.1 Contratos compartidos

Una intención, un resultado y un error deben significar lo mismo en PC y Android. El contrato incluye:

- identificador de petición y cancelación;
- capacidad solicitada y plataforma;
- permisos y confirmación;
- presupuesto de tiempo, tokens, RAM, CPU y red;
- estado `real`, `simulado` o `no disponible`;
- resultado verificable y error legible.

El puente deja de duplicar decisiones: reparte resultados y conserva el contexto de sesión.

### 4.2 Router local-first adaptativo

Orden propuesto:

1. **Reglas:** volumen, apps permitidas, consultas locales, navegación y acciones con intención inequívoca.
2. **Cerebro local:** interpretación, conversación y planes cuando el dispositivo tenga margen.
3. **Nube consentida:** proveedor configurado, con límites y datos mínimos.
4. **Degradación:** respuesta útil, alternativa local o «no disponible» con motivo.

El router no cambia silenciosamente de local a nube. La política de privacidad decide primero; después el presupuesto y la disponibilidad.

### 4.3 Adaptadores de proveedor

- Gemini como primer proveedor nube, con adaptador propio.
- OpenAI-compatible para servicios compatibles, sin asumir que todos se comportan igual.
- Ollama en PC y GGUF/llama.cpp en Android como motores locales.
- Un resultado común de texto, uso, latencia, error y proveedor usado.

No se añadirá un proveedor sólo porque exista una clave: necesita prueba, límites y diagnóstico.

### 4.4 Custodia de secretos

- PC: keyring del sistema operativo.
- Android: Keystore y una credencial cifrada por dispositivo.
- La interfaz muestra «configurada» o «no configurada», nunca la clave.
- La clave no viaja en repo, APK, logs, respaldo automático ni consultas de enlace.
- Rotación y eliminación deben ser operaciones explícitas.

Esto sustituye la idea de guardar claves en JSON plano. Jenny sirve como advertencia, no como modelo de custodia.

### 4.5 Supervisor de tareas y presupuestos

Toda petición debe nacer en un supervisor que:

- registre la tarea y su dueño;
- limite cola y concurrencia;
- aplique timeout y cancelación;
- garantice una respuesta terminal;
- libere audio, cámara, WebView y modelos al terminar;
- registre esperas y desbordamientos sin ocultarlos.

La interfaz nunca debe esperar una operación bloqueante para seguir respondiendo.

### 4.6 Herramientas con verificación

Una herramienta declara:

- nombre y descripción;
- plataformas donde existe;
- permisos y precondiciones;
- si es destructiva y qué confirmación exige;
- timeout y presupuesto;
- resultado tipado;
- cómo comprobar que realmente ocurrió;
- error estructurado y alternativa.

El modelo propone; el registro permite; el validador decide; el ejecutor actúa; el verificador confirma.

### 4.7 Memoria y proactividad

- Android y PC guardan primero en local.
- La sincronización es opcional y tiene conflicto visible.
- Cada recuerdo conserva origen, fecha y confianza.
- La consolidación usa un presupuesto y no se ejecuta mientras la interfaz o el audio estén bajo presión.
- Una rutina proactiva necesita permiso, horario, límite y forma de silenciarla.

La meta no es que CORT hable más, sino que interrumpa menos y con mejor información.

## 5. Qué potenciar primero

### P0 — Estabilidad, privacidad y verdad de capacidades

1. Retirar claves de `localStorage`, `SharedPreferences` en claro y estado general; definir custodia y borrado.
2. Hacer que la UI sólo ofrezca nube cuando exista adaptador real, o marcarla claramente como no disponible.
3. Respetar el modo local: si GGUF falla, no pasar a nube sin consentimiento.
4. Vista táctil estructural y paneles con ancho adaptable.
5. WebView y trabajo pesado fuera del hilo de interfaz.
6. Escucha en segundo plano con estado y permiso honestos.
7. Puente PC con tareas registradas, colas acotadas, timeout, cancelación y respuesta terminal.
8. Carga GGUF con integridad persistida y errores accionables.

### P1 — Capacidades compartidas y confianza

1. Registro de capacidades PC/Android.
2. Contrato único de resultado y error.
3. Adaptador Gemini y política explícita de failover entre proveedores.
4. Paridad de herramientas mediante permisos, confirmación y verificación.
5. Auditoría local renombrada y limitada a lo que realmente puede hacer.
6. Pruebas conductuales de nube con servidores simulados, sin usar claves reales.

### P2 — Híbrido útil

1. Router reglas → local → nube consentida → degradación.
2. Adaptadores Gemini, OpenAI-compatible, Ollama y GGUF con contrato común.
3. Presupuestos observables por petición.
4. Evaluación offline con preguntas y acciones de arena.

### P3 — Compañero proactivo

1. Memoria local con sincronización opcional.
2. Rutinas y recordatorios con confirmación.
3. Investigación con fuentes y límites.
4. Voz y visión sólo donde el hardware y el permiso lo permitan.

## 6. SPECs propuestas, todavía no aceptadas

| SPEC propuesta | Backlog | Resultado esperado | Depende de |
|---|---|---|---|
| `SPEC-SEC-001` | CORT-SEC-001 | Claves fuera de almacenamiento general, custodia por dispositivo, borrado y UI sin secretos | Decisiones 5 y 6 |
| `SPEC-ANDROID-002` | CORT-AND-001/002 | Paneles usables a 531 px y trabajo pesado fuera de UI, con regresión automatizable | CORT-AND-005 |
| `SPEC-ANDROID-003` | CORT-AND-003/004 | Escucha y saludo con estado real, permiso, límite y prueba de reinicio | SPEC-ANDROID-002 |
| `SPEC-PC-001` | CORT-PC-001/CORT-PC-003 | Tareas registradas, backpressure, timeout, cancelación y respuesta terminal | Contrato compartido |
| `SPEC-CORE-001` | CORT-AND-006/CORT-PC-002 | Capacidades, herramientas y errores honestos en ambas plataformas | Decisiones del cuestionario |
| `SPEC-HIB-001` | CORT-HIB-001 | Router, proveedores reales y degradación privada con presupuestos | P0 cerrado y SPEC-CORE-001 |
| `SPEC-MEM-001` | CORT-MEM-001 | Memoria local, procedencia y sincronización opcional | SPEC-HIB-001 |

Cada SPEC debe nacer con prueba roja, criterios Dado/Cuando/Entonces y evidencia separada en estático, build y dispositivo.

## 7. Medición pendiente

No hay cifras físicas nuevas en este informe. Antes de cerrar P0 se medirán:

- latencia de apertura de paneles y fotogramas largos en el A16;
- esperas y cola del puente PC, incluyendo percentiles;
- continuidad de escucha con pantalla apagada y tras reinicio;
- RAM disponible antes y después de abrir cada GGUF;
- tiempo hasta el saludo y entrega de notificación;
- tasa de error por código y proveedor;
- costo de tokens y red por petición cuando se autorice nube.

Cada cifra debe guardar dispositivo, versión, comando o procedimiento y fecha.

## 8. Decisiones necesarias

Las diez decisiones están en [`CUESTIONARIO-HIBRIDO.md`](CUESTIONARIO-HIBRIDO.md). La propuesta recomendada es:

- cerrar P0 antes de expandir, empezando por secretos y verdad de la nube;
- operador y compañero equilibrados;
- router local-first adaptativo;
- Gemini más OpenAI-compatible y motores locales;
- secretos en keyring/Keystore;
- audio, pantalla y archivos fuera de nube salvo confirmación explícita;
- presupuestos configurables;
- automatización verificable y memoria/proactividad como siguientes capacidades;
- Android autónomo y PC opcional;
- push a `web/cort-v0` por fase verificada, sin etiqueta ni Release por defecto.

## 9. Límites de este informe

- No se ejecutó código de las referencias.
- No se instaló dependencia ni se modificó ninguna referencia.
- No se llamó a Gemini, OpenAI ni otro proveedor.
- No se compiló la APK en esta máquina.
- No se reprodujo el fallo en el A16.
- Las líneas citadas son evidencia de lectura estática, no de rendimiento.
- La publicación del parche RAM no demuestra por sí sola que el GGUF cargue en el teléfono.
