# SPEC-OMNI-001 — CORT Android integrado y verificable

- **Estado:** ACEPTADA
- **Prioridad:** P0 para los cimientos; P1/P2 para las capacidades según la fase
- **Plataforma:** Android primero; PC en una fase posterior
- **Fecha:** 2026-11-26
- **Base inspeccionada:** `web/cort-v0`, commit `7880dbc55cd9da7331d3b5b3cab0d7d0b2dcccd4`
- **SPEC madre:** [SPEC-ASIS-001.md](SPEC-ASIS-001.md)
- **Decisiones heredadas:** [ADR-003](DECISIONES.md#adr-003--arquitectura-híbrida-con-contratos-compartidos), [ADR-004](DECISIONES.md#adr-004--asistente-personal-por-subfases-verificables) y [ADR-005](DECISIONES.md#adr-005--un-centro-de-acciones-y-chat-de-pantalla-completa)
- **Plan:** [PLAN-OMNI-001.md](PLAN-OMNI-001.md)

## 1. Problema

CORT ya tiene una base Android útil, pero la experiencia todavía no corresponde a un asistente personal integrado. La inspección estática de la rama base muestra estas brechas:

1. La cara Web mezcla paneles de PC y Android. `Nexo.java:329-351` publica banderas como `apps`, `vision`, `vpn` o `juegos`, pero la interfaz no las consume para filtrar el catálogo.
2. `Sensores.java` existe, pero no hay referencias a él fuera de su propia clase. Además, conserva sólo `evento.values[0]`, muestra el contador de pasos acumulado como «pasos de hoy» y no declara el ciclo de registro/liberación desde la interfaz.
3. `Audifonos.java` detecta cable, USB y Bluetooth, pero no implementa `MediaSession`, audio focus ni botones multimedia. La acción «Música» de `VistaRapida` sólo abre una aplicación por categoría.
4. `ServicioEscucha.java` es una escucha foreground acotada: se detiene al apagar la pantalla y tras cinco minutos de silencio. Su comentario afirma que el aviso no contiene lo oído, pero `ServicioEscucha.java:241` publica un fragmento de la transcripción.
5. `Reconocimiento.java` abre `MainActivity` y devuelve `ERROR_NO_MATCH`; no entrega resultados de reconocimiento. `Sesion.java` muestra la vista rápida y termina inmediatamente. CORT puede registrarse como asistente, pero el contrato de voz no está completo ni verificado.
6. `MainActivity.java:455-459` y `Nexo.java:224-229` conceden automáticamente los recursos que pide el WebView. No es una base segura para añadir cámara o micrófono Web.
7. No existe un registro común de capacidades que la nativa y la Web consuman, ni un estado único para permisos, disponibilidad, origen y aprobaciones. Añadir más paneles sin ese contrato duplicaría decisiones y promesas falsas.

Estos hechos provienen de inspección estática. No se ha compilado una APK nueva ni probado un dispositivo físico en esta fase.

## 2. Resultado esperado

La persona usuaria puede:

- seleccionar CORT como asistente de Android sin desinstalar ni inhabilitar otra aplicación;
- encontrar todas las acciones en un único centro, con paneles filtrados según el dispositivo y el permiso real;
- consultar sensores presentes, ausentes o todavía sin lectura sin que CORT invente valores;
- controlar la reproducción de CORT y, cuando Android lo permita, la sesión multimedia activa de otra app;
- usar controles de auriculares con un comportamiento explícito y límites visibles;
- activar dictado, invocación del asistente o palabra de activación en modos diferenciados;
- detener toda escucha desde la interfaz y desde la notificación permanente;
- crear memoria, rutinas, alarmas y recordatorios con procedencia y confirmación;
- leer notificaciones sólo tras habilitar manualmente el acceso y elegir las apps permitidas;
- probar gestos de cámara en primer plano, con preview visible y cierre inmediato;
- conservar una experiencia local útil cuando falten red, modelo, hardware o permiso.

CORT no promete escucha continua garantizada con pantalla apagada, control universal de cualquier app, envío automático de mensajes ni automatización arbitraria por accesibilidad.

## 3. Alcance

### Incluye

1. Catálogo y contrato de todos los paneles actuales y propuestos.
2. Registro de capacidades compartido entre Java y Web.
3. Sensor de dispositivo: inventario, valores, unidades, ciclo de vida y presupuesto.
4. Detección de rutas de audio, `MediaSession`, audio focus y botones de auriculares.
5. Modos de escucha foreground/background y sus límites reales.
6. Completado del contrato de asistente de voz y coexistencia con el asistente anterior.
7. Memoria local, rutinas, alarmas, frases y recordatorios.
8. Notificaciones de otras apps con acceso manual, allowlist y lectura inicial.
9. Compartir contenido y abrir apps mediante Intents verificados.
10. Gestos de cámara visibles en Android y contrato reutilizable para PC.
11. Proactividad sugerida, nunca ejecución sensible automática.
12. Pruebas estáticas, unitarias, Web, build y matriz física A16.

### No incluye

- Publicar APK, release, etiqueta, push o merge.
- Reemplazar, desinstalar o modificar la aplicación del asistente del sistema.
- Root, shell remoto, exploits, evasión de detección o acceso a datos de otras apps fuera de APIs públicas.
- Lectura universal de pantalla, contactos, SMS o WhatsApp.
- Envío automático de mensajes o llamadas.
- Control universal de botones de auriculares cuando otra app o el asistente del sistema los retiene.
- Escucha 24/7 garantizada, arranque del micrófono desde `BOOT_COMPLETED` o dependencia de excepciones OEM.
- Captura de cámara en segundo plano.
- Entrenar un modelo, añadir dependencias pesadas o trasplantar código AGPL sin decisión de licencia.
- Implementar ahora las capacidades reservadas a PC.

## 4. Definiciones y niveles de viabilidad

### 4.1 Origen del dato

Toda capacidad y lectura declara uno de estos valores:

- `real`: obtenida del sistema, hardware o adaptador ejecutado.
- `simulado`: dato de demostración, claramente etiquetado y nunca mezclado con una lectura real.
- `no disponible`: no existe adaptador, permiso, hardware, red o app compatible; incluye motivo y alternativa.

Un panel vacío, un cero inventado o un botón que no hace nada no es una respuesta válida.

### 4.2 Viabilidad Android

| Nivel | Significado | Tratamiento en la interfaz |
|---|---|---|
| **A — Disponible** | Integrable con APIs estándar y los componentes actuales; puede requerir un permiso runtime ordinario ya existente | Se ofrece; el permiso se pide al usarla |
| **B — Viable con configuración** | Requiere permiso adicional, habilitación manual en Ajustes, hardware concreto o una sesión foreground | Se ofrece con explicación y ruta de activación |
| **C — Limitada/condicional** | Depende de Android, One UI, otra app, conectividad, precisión o un modelo que debe caber en el A16 | Se ofrece como experimental o limitada; nunca como universal |
| **D — No viable en Android estándar / reservada a PC** | La implementación actual es de escritorio o exigiría APIs privilegiadas | Se oculta del catálogo Android; se puede consultar en una sección informativa |

La viabilidad no equivale a implementación. El estado actual se declara por separado como `existe`, `parcial`, `dormido`, `no implementado` o `no verificado`.

## 5. Decisiones de comportamiento

### 5.1 Un centro, un catálogo

1. Se conserva ADR-005: un único centro de acciones, chat completo superpuesto y modo enfoque.
2. Cada panel tiene identificador estable, etiqueta, plataforma, nivel de viabilidad, estado actual, permisos, riesgo, confirmación, soporte offline, presupuesto y motivo de indisponibilidad.
3. La Web no decide por su cuenta qué panel existe: consume el registro que entrega Android.
4. Los paneles D no aparecen como controles activos en Android. La sección «No disponible en este dispositivo» es informativa y opcional.
5. Ninguna acción duplicada abre el mismo panel por dos entradas distintas.
6. Los controles nuevos mantienen al menos 48 dp/px, descripciones accesibles, foco visible, Escape donde corresponda y respeto por movimiento reducido.

### 5.2 Contrato de capacidad

El registro mínimo será:

```text
id, etiqueta, plataforma, viabilidad, estado, origen,
permisos, hardware, riesgo, confirmacion, offline,
presupuesto, dependencias, motivo_no_disponible,
controles (opcional: IDs Web asociados)
```

Reglas:

- El identificador no cambia al traducir la etiqueta.
- `estado` describe la implementación; `viabilidad` describe lo que Android permite.
- `origen` describe el último resultado, no la intención.
- Un permiso concedido no implica que el hardware exista.
- Una app instalada no implica que exponga la API o el Intent necesario.
- La interfaz debe poder mostrar «requiere permiso», «no hay sensor» y «no disponible» sin ejecutar una acción simulada.

### 5.3 Pipeline de acciones

```text
ENTRADA → INTENCIÓN → CONTEXTO → PLAN → POLÍTICA →
APROBACIÓN → EJECUCIÓN → VERIFICACIÓN → RESPUESTA
```

1. Las reglas deterministas siguen siendo el primer camino.
2. El modelo puede proponer una intención; sólo el código valida y ejecuta.
3. La respuesta del modelo nunca se convierte directamente en un comando de shell.
4. Toda acción sensible pasa por una allowlist y una aprobación asociada a la sesión y al dispositivo.
5. No se añade un `PENDIENTE` global. Una aprobación caduca, se puede revocar y no autoriza capacidades distintas.
6. La ejecución fallida devuelve motivo verificable; no se presenta como éxito.

### 5.4 Aprobaciones

| Clase | Ejemplos | Regla inicial |
|---|---|---|
| Informativa | inventario de sensores, batería, memoria local | Sin aprobación adicional |
| Reversible | abrir app, ajustar volumen, crear alarma en el reloj del sistema | Acción explícita del turno |
| Sesión | dictado, palabra de activación, cámara visible | Consentimiento visible y parada inmediata |
| Sensible | compartir mensaje, responder borrador, mover archivo, programar recordatorio propio | Confirmación por acción; «siempre» no se usa en la primera versión |
| Prohibida inicial | shell, envío automático, llamada automática, control arbitrario de apps | No se expone |

### 5.5 Privacidad y presupuesto

- Local-first: audio, sensores, memoria y cámara no salen del dispositivo sin una acción y consentimiento específicos.
- La palabra de activación usa la gramática cerrada existente; no se transcribe ni almacena el ambiente antes de activar CORT.
- La notificación de escucha no contiene transcripciones, nombres de contactos ni contenido sensible.
- Toda sesión de micrófono, cámara o sensor tiene inicio, estado visible, límite y cierre.
- No se declara autonomía de batería, RAM o latencia sin medición en A16.
- La carga se reparte: si no hay presupuesto, CORT degrada o rechaza la capacidad; no la simula.

## 6. Catálogo de paneles y herramientas

### 6.1 Núcleo Android

| Panel o herramienta | Viabilidad | Estado actual inspeccionado | Permiso o límite | Fase |
|---|---|---|---|---|
| Centro de acciones | A | Existe; ASIS-1.10–1.15 bloqueantes | Debe consumir el registro | OMNI-1 |
| Chat completo | A | Existe; evidencia Web previa | Sin HTML ejecutable | OMNI-1 / ASIS-1 |
| Enfoque | A | Existe; evidencia Web previa | Paneles sin foco | OMNI-1 |
| Vista rápida del asistente | B | Existe; `SYSTEM_ALERT_WINDOW` | Permiso especial y A16 | OMNI-1 |
| Voz/TTS | A | Existe con TTS del sistema | Voz instalada; audio focus pendiente | OMNI-3 |
| Dictado foreground | A | Existe con Vosk o motor del sistema | `RECORD_AUDIO`; límite 60 s | OMNI-3 |
| Palabra de activación | B | Parcial; `ServicioEscucha` | Foreground service; pantalla encendida | OMNI-3 |
| Escucha background | C | Parcial; se corta con pantalla apagada | Inicio desde foreground; One UI y batería | OMNI-3 |
| Memoria | A | SQLite local; procedencia limitada | Sin nube; migración conservando datos | OMNI-6 |
| Vida diaria y compras | A | Existe | Datos locales | OMNI-6 |
| Perfil, personalidad y voces | A | Parcial | Sólo voces instaladas; no imitar identidades | OMNI-6 |
| Apps instaladas | A | Existe mediante Intents y `<queries>` | Sólo apps lanzables visibles | OMNI-1 |
| Cerebros y router | C | Parcial; P0 de RAM/nube abiertos | Modelo, RAM, red y consentimiento | P0 / OMNI-6 |
| Clima | C | Existe por red | Ubicación manual/ciudad; sin sensor inventado | OMNI-6 |
| Ajustes | A | Existe | Debe exponer permisos y capacidades reales | OMNI-1 |
| Actualización | C | No verificada; canal no demostrado | No prometer actualización sin canal | P0 |
| Navegador | A | Apertura por Intent | No automatización de páginas | OMNI-1 |
| Escáner QR | B | Existe en `Escaner` | `CAMERA`; foreground | OMNI-9 |
| Leer texto compartido | A | Existe en `Lectura` | `ACTION_PROCESS_TEXT`/`ACTION_SEND` | OMNI-1 |
| Bolsillo | C | Existe; depende del enlace PC | Red y puente | OMNI-7 |
| Equipo/RAM | A | Existe en `Equipo` | Lectura del sistema | OMNI-2 |
| Almacén de cerebros | C | Existe; carga GGUF pendiente en A16 | RAM, descarga y SHA | P0 |
| Parlamento | C | Existe; depende del puente | Red, micrófono y PC | OMNI-7 |
| Sensores | A/B | `Sensores.java` dormido y con correcciones pendientes | Hardware, `ACTIVITY_RECOGNITION` para pasos | OMNI-2 |
| Medios y auriculares | B/C | Sólo detección de salida | `MediaSession`; apps compatibles; foco de audio | OMNI-4 |
| Rutinas, alarmas y frases | B | Parser/alarmas parciales en ASIS-2 | Reloj del sistema primero | OMNI-6 |
| Notificaciones | B | No implementado | Habilitación manual y allowlist | OMNI-7 |
| Cámara y gestos | B/C | No implementado | Foreground, preview, modelo y RAM | OMNI-9 |
| Dispositivo, batería y red | A | Lecturas parciales | Sin permisos amplios | OMNI-2 |
| Archivos propios | B | Almacenamiento propio | SAF sólo con selección del usuario | OMNI-6 |
| Privacidad, permisos y registro | A | No implementado como panel | Sin contenido sensible por defecto | OMNI-1 |
| Proactividad | C | No implementado | Sugerencias; nunca envío automático | OMNI-8 |
| Compartir/mensajería | C | No implementado | `ACTION_SEND` y confirmación humana | OMNI-7 |

### 6.2 Paneles actuales orientados a PC

| Panel actual | Viabilidad Android | Tratamiento |
|---|---|---|
| Antivirus / protección en tiempo real | D | Android no puede escanear otras apps como un antivirus de escritorio. Sustituir por «Salud y permisos de CORT». |
| GPU Boost, Nemotron ASR y controles de motor de PC | D | Ocultar en Android; conservar para PC. |
| Jarvis OS, control de ventanas y escritorio | D | Ocultar en Android. |
| Webcam de PC | D | No confundir con la futura cámara de gestos foreground. |
| VPN | C | `VpnService` requiere configuración y consentimiento; no entra en la primera fase. |
| Domótica / Home Assistant | C | Posible mediante un adaptador de red verificado; no implementado. |
| Impresión 3D | C | Posible mediante API de impresora; no implementado. |
| Obsidiana | C | Sólo apertura/compartición de vaults mediante SAF o Intents verificados. |
| Juegos | D para la implementación actual | Ocultar la biblioteca de PC; una futura vista Android listará apps, no juegos de escritorio. |
| Desinstalador | C | Android permite abrir Ajustes de una app o lanzar desinstalación; no desinstalación masiva silenciosa. |
| Winget / paquetes | D | Ocultar en Android. |
| IPTV | C | Requiere reproductor y fuente válidos; no implementado. |
| Tienda de apps propia | D | Ocultar; como alternativa se puede abrir la tienda del sistema. |
| Email HUD | C | Requiere proveedor/API; no hay acceso universal al correo. |
| Restaurantes | C | Requiere servicio externo y ubicación consentida; no implementado. |
| Holograma, Globe 3D y HUD de voz de escritorio | C/P2 | Son visuales, no capacidades del asistente. No adelantan funciones P0. |
| Limpiar caché | A | Ya existe para WebView; no borrar memoria ni modelos. |
| Lista de comandos | A | Debe generarse desde el registro de capacidades. |
| Temperatura | A/B | Usar sensor ambiental si existe; la temperatura de batería se etiqueta como batería. |

## 7. Sensores

### 7.1 Matriz

| Sensor o fuente | Viabilidad | Permiso/hardware | Semántica obligatoria | Fase |
|---|---|---|---|---|
| Acelerómetro | A | Hardware habitual; sin permiso runtime | Conservar x/y/z en m/s²; no confundir reposo con movimiento | OMNI-2 |
| Giróscopo | A | Hardware variable | Conservar x/y/z en rad/s | OMNI-2 |
| Campo magnético | A | Hardware variable | Conservar x/y/z en µT; calibración/precisión visibles | OMNI-2 |
| Luz | A | Hardware variable | Lux; una lectura no es una calibración automática | OMNI-2 |
| Proximidad | A | Hardware variable | Valor del sensor; no afirmar «en bolsillo» sin umbral validado | OMNI-2 |
| Presión | A | Hardware poco común | hPa/mbar; ausencia explícita | OMNI-2 |
| Temperatura ambiente | A | Hardware poco común | °C ambiental; nunca mezclar con batería | OMNI-2 |
| Humedad relativa | A | Hardware poco común | % HR; no asumir que existe | OMNI-2 |
| Batería | A | Siempre que Android exponga el estado | Nivel, carga y temperatura de batería por separado | OMNI-2 |
| Podómetro | B | `ACTIVITY_RECOGNITION` en API 29+ y sensor | Acumulado desde el último arranque mientras el sensor estuvo activo; calcular «hoy» con línea base | OMNI-2 |
| Detector de pasos | B | Igual que podómetro | Un evento por paso; no equivale al total diario | OMNI-2 |
| Movimiento significativo | C | Sensor trigger y permiso de actividad | Evento one-shot; no medición continua | OMNI-8 |
| Rotación/gravedad/aceleración lineal | C | Sensores virtuales o hardware | Unidades y fusión correctas; no duplicar acelerómetro | OMNI-8 |
| Frecuencia cardíaca y sensores corporales | C | `BODY_SENSORS`, hardware y restricciones while-in-use | No disponible en la mayoría de teléfonos; fuera de la primera fase | Diferida |
| Ubicación | C | `ACCESS_COARSE_LOCATION`/`ACCESS_FINE_LOCATION` | Consentimiento específico; no se añade en esta SPEC sin subfase propia | Diferida |
| Cámara para gestos | B/C | `CAMERA`, preview y modelo | Foreground visible; sin persistencia por defecto | OMNI-9 |

### 7.2 Ciclo de vida

1. El inventario se consulta al abrir el panel y no depende de que el sensor esté emitiendo.
2. Los listeners continuos se registran al entrar en foreground y se retiran al pausar o cerrar.
3. Un servicio foreground sólo mantiene sensores cuando una función visible y voluntaria lo necesita.
4. Desde Android 9, los sensores continuos/on-change/one-shot no reciben eventos en background salvo una ejecución foreground válida.
5. `SENSOR_DELAY_UI` es una sugerencia de aproximadamente 60 ms, no una garantía. Se usa el muestreo más lento que satisfaga la función.
6. No se solicita `HIGH_SAMPLING_RATE_SENSORS` en la primera fase. Si una función futura supera 200 Hz en sensores de movimiento, requiere SPEC y permiso propios.
7. `onSensorChanged` sólo copia/encola datos; filtros y persistencia no bloquean el callback.
8. Un sensor sin lectura se muestra como «sin lectura», no como cero.
9. El histórico es opcional y acotado. La primera fase conserva sólo el estado en memoria.
10. Sacudir el teléfono puede callar CORT, pero no ejecuta acciones sensibles.

### 7.3 Correcciones obligatorias a `Sensores.java`

- Conservar todos los ejes de los sensores tridimensionales.
- Separar temperatura ambiental de temperatura de batería.
- Añadir `ACTIVITY_RECOGNITION` sólo cuando se habilite el podómetro/detector de pasos.
- Calcular «pasos de hoy» contra una línea base persistente y reiniciarla al cambiar de día o reiniciarse el dispositivo.
- Etiquetar el valor acumulado si no hay línea base.
- Conectar el registro y la liberación al ciclo de vida real.
- Mostrar precisión, marca de tiempo y procedencia `real`.
- No afirmar que todos los sensores no necesitan permisos.

## 8. Auriculares, medios y audio

### 8.1 Contrato

1. `Audifonos.java` se reutiliza para detectar cable, USB y Bluetooth.
2. CORT publica una `MediaSession` propia para su reproducción y metadatos.
3. CORT solicita audio focus antes de reproducir y lo abandona cuando termina.
4. La voz usa atributos de asistente/discurso; la música usa atributos de medios.
5. Ante pérdida permanente de foco, CORT pausa y no reanuda automáticamente.
6. Ante pérdida transitoria, CORT pausa o baja volumen según el tipo de contenido.
7. `ACTION_AUDIO_BECOMING_NOISY` pausa la reproducción al desconectarse auriculares.
8. La ruta de salida se muestra como estado real; si hay varias, no se afirma cuál es la activa sin una API que lo confirme.

### 8.2 Botones

| Botón/evento | Comportamiento inicial | Límite |
|---|---|---|
| Reproducir/pausar | Controlar la sesión de CORT o la sesión multimedia activa compatible | Depende de la app y de la prioridad de la sesión |
| Siguiente/anterior | Enviar el control estándar | Puede no existir en la app activa |
| Detener | Detener reproducción de CORT | No detener contenido de otra app sin sesión compatible |
| Subir/bajar volumen | Ajustar el flujo activo | No robar el volumen de llamada |
| Pulsación larga | No se remapea por defecto | Puede pertenecer al asistente del sistema o a otra app |
| Doble toque | Experimental, desactivado por defecto | No es un evento universal garantizado |
| Botón de llamada | No se intercepta | Reservado para telefonía |

Para descubrir y controlar sesiones de otras apps, Android requiere `MEDIA_CONTENT_CONTROL` o un `NotificationListenerService` habilitado. CORT usará la segunda vía sólo si la persona usuaria habilita el acceso; no pedirá un permiso privilegiado que no puede conceder.

### 8.3 Viabilidad

- **Control de medios de CORT:** A/B, implementable con `MediaSession`.
- **Control de una app externa compatible:** C; depende de su `MediaSession` y del acceso a sesiones activas.
- **Interceptar cualquier toque de auriculares:** D como promesa universal.
- **Información detallada de dispositivo Bluetooth:** B; puede requerir `BLUETOOTH_CONNECT` en Android 12+.
- **Cambiar la asignación del asistente del sistema:** fuera de esta SPEC; Android lo controla en Ajustes.

## 9. Escucha

### 9.1 Modos

| Modo | Inicio | Captura | Estado visible | Detención | Viabilidad |
|---|---|---|---|---|---|
| Dictado foreground | Botón Hablar o entrada del asistente | Vosk local o reconocimiento del sistema | Orbe/texto provisional | Cancelar, silencio o 60 s | A |
| Invocación del asistente | Gesto/tecla del sistema | Requiere completar `RecognitionService` | Vista rápida y luego conversación | Cerrar/cancelar | C hasta completar contrato |
| Palabra de activación foreground | App abierta o baldosa | Vosk con gramática cerrada | Notificación permanente | Detener, pantalla apagada o 5 min de silencio | B |
| Palabra de activación background con pantalla encendida | Servicio iniciado desde foreground | Vosk con gramática cerrada | Notificación permanente y estado en app | Detener, timeout u OEM | B/C |
| Captura con pantalla apagada | Opcional, apagada por defecto | Sólo si el usuario lo activa y el A16 lo permite | Notificación permanente | Detener inmediato | C; requiere medición física |
| Escucha 24/7 | No se ofrece | — | — | — | D |
| Arranque del micrófono al reiniciar | No se intenta | — | Saludo/notificación solamente | — | D bajo condiciones normales de Android 14 |

### 9.2 Estados

```text
APAGADO → PIDIENDO_PERMISO → PREPARANDO →
ESCUCHANDO_PALABRA → ESCUCHANDO_MANDATO →
PROCESANDO → DETENIDO / ERROR
```

La interfaz, la baldosa y la notificación deben leer el mismo estado. La preferencia «quería escuchar» no es lo mismo que «el servicio está montado».

### 9.3 Reglas obligatorias

1. El micrófono se inicia sólo desde una interacción foreground o una excepción documentada; `BOOT_COMPLETED` no inicia el micrófono.
2. Android 14 exige `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_MICROPHONE`, permiso runtime `RECORD_AUDIO` y tipo `microphone`.
3. La notificación permanente tiene título fijo, visibilidad privada y acción `Detener`.
4. La notificación nunca publica la frase reconocida.
5. La acción `Detener` libera el motor, retira listeners y elimina el servicio.
6. La baldosa muestra el estado real, no siempre «inactiva».
7. Al apagar la pantalla, el comportamiento inicial sigue siendo detener la escucha.
8. La captura con pantalla apagada sólo se añade tras una decisión explícita y una prueba de batería/OEM en A16.
9. `START_STICKY` no se presenta como garantía de supervivencia.
10. Si falta el modelo local, CORT informa y no consume batería «escuchando» sin motor.
11. La voz y el micrófono no se solapan salvo una función de interrupción verificada.
12. No se guarda audio ni transcripciones ambientales por defecto.

## 10. Asistente predeterminado y coexistencia

1. CORT puede aparecer en Ajustes como asistente seleccionable.
2. Seleccionar CORT no desinstala ni inhabilita Gemini ni otra app; la persona usuaria puede volver a cambiar la selección.
3. CORT debe completar `VoiceInteractionService`, `VoiceInteractionSessionService` y `RecognitionService` antes de declarar asistente de voz funcional.
4. `Reconocimiento` debe entregar resultados o errores reales mediante su callback; abrir una actividad y devolver `ERROR_NO_MATCH` no cuenta como reconocimiento.
5. La sesión no termina antes de que exista una conversación o una cancelación real.
6. La selección puede cambiar el comportamiento del gesto, la tecla de asistente y la pantalla de bloqueo. Android decide las superficies disponibles.
7. Al seleccionar CORT se puede perder el hotword del asistente anterior con pantalla apagada; esta consecuencia se muestra antes de la selección.
8. No se afirma que CORT intercepte toda pulsación larga de auriculares.
9. La verificación final requiere A16: selección, gesto, keyguard, auriculares Bluetooth, resultado de voz, cierre y vuelta al asistente anterior.

## 11. Memoria, rutinas y acompañamiento

### 11.1 Memoria

- Se reutiliza `Recuerdos.java` y su SQLite; no se borra la base existente.
- Hechos y procedimientos están separados: memoria para datos; habilidades para acciones repetibles.
- Cada hecho guarda procedencia, fecha y confirmación.
- La escritura autónoma está desactivada inicialmente. CORT puede proponer recordar; la persona confirma.
- No se almacenan secretos, credenciales, audio, mensajes sensibles ni transcripciones ambientales.
- La interfaz permite consultar, corregir y borrar recuerdos.
- No se añade una base vectorial o dependencia pesada sin una SPEC que demuestre necesidad y presupuesto.

### 11.2 Rutinas y alarmas

1. La primera implementación usa `AlarmClock.ACTION_SET_ALARM`/`ACTION_SET_TIMER` y el catálogo del sistema.
2. No se solicita `SCHEDULE_EXACT_ALARM` ni `USE_EXACT_ALARM` en la primera fase.
3. Una alarma propia sólo se añade si se demuestra una necesidad visible de precisión y Android concede el permiso.
4. Las rutinas son listas deterministas de capacidades allowlisted.
5. Cada paso declara permiso, riesgo, confirmación y resultado.
6. Una rutina se ejecuta una vez por activación y puede cancelarse.
7. Las frases incluyen autor, obra/fuente y licencia o revisión de derechos.
8. Los saludos de mañana/noche no prometen entrega si One UI, notificaciones o TTS fallan.

### 11.3 Notificaciones y apps externas

- `NotificationListenerService` se habilita manualmente desde Ajustes; no es un permiso runtime ordinario.
- La primera versión lee notificaciones sólo de apps allowlisted y sólo cuando la persona lo pide.
- No se responden notificaciones automáticamente.
- Si se añade respuesta, primero se muestra un borrador y se exige confirmación.
- WhatsApp/SMS no se controlan como una API general. La vía inicial es `ACTION_SEND` con confirmación humana.
- La accesibilidad existente no se convierte en un control remoto genérico.
- Los archivos se limitan al almacenamiento propio o a rutas seleccionadas con SAF.

### 11.4 Proactividad

- Está apagada por defecto.
- CORT puede sugerir una acción con motivo y contexto; no la ejecuta sin permiso.
- No envía mensajes, llamadas, compras ni borrados de forma autónoma.
- Todo trigger declara frecuencia, batería, red y límite.
- La primera forma es una tarjeta «Sugerencia» dentro del centro de acciones, no una interrupción.

## 12. Cámara y gestos

1. La cámara de gestos es una sesión foreground visible con preview, indicador del sistema y botón de cierre.
2. Requiere `CAMERA` concedido y una justificación en la interfaz.
3. No captura ni analiza en segundo plano ni desde `BOOT_COMPLETED`.
4. No guarda fotogramas por defecto.
5. Un gesto sólo selecciona o confirma una acción visible; no ejecuta acciones sensibles sin confirmación.
6. La primera fase es un prototipo técnico: abrir cámara, mostrar preview, detectar un gesto sencillo y cerrar.
7. La elección entre Camera2 nativo, ML Kit, MediaPipe u otro motor queda como decisión de implementación tras medir tamaño, RAM, latencia y licencia. No se instala dependencia antes de esa decisión.
8. Si el modelo no cabe o el hardware no rinde, CORT muestra «gestos no disponibles» y conserva el control táctil.
9. La experiencia de interacción puede reutilizarse en PC, pero el código de webcam/escritorio no se trasplanta a Android.

### 12.1 Patrones adoptados de los videos y `fullstack-agent`

La inspección visual de los tres videos y del código de referencia aporta estos patrones, no código ni recursos que se puedan copiar:

1. **Estado visible y sincronizable:** el orbe/avatar debe distinguir reposo, escucha, procesamiento y habla. El teléfono no duplica todos los controles del escritorio; muestra texto, micrófono y una parada prominente.
2. **Interrupción siempre disponible:** hablar, cerrar o pulsar `Detener` debe cancelar la escucha o el habla sin esperar a que termine el modelo.
3. **HUD 2D antes que escena 3D:** el primer prototipo Android usa anillo, tarjetas y etiquetas discretas. La pizarra espacial, pinch, arrastre y escala con dos manos queda para una fase medida después.
4. **Memoria portable:** la bóveda Markdown de `ai-memory-vault` respalda separar hechos, notas y prioridades. CORT usará SQLite y procedencia local; no añade Obsidian ni una base vectorial como requisito.
5. **Voz por capas:** `backtalk` separa captura, cerebro y habla por frases. CORT conserva esa separación conceptual mediante adaptadores locales; no importa Python, PortAudio, `pynput`, Claude Code ni el Agent SDK al APK.
6. **Telefonía:** el video de llamada muestra una interacción familiar, pero no demuestra cómo se colocó la llamada. Android sólo podrá usar telefonía ordinaria o un `ConnectionService`/VoIP autorizado. CORT no imita identidad de llamada, números, voces ni interfaces del operador, y no coloca llamadas automáticamente.
7. **Manos opcionales:** los gestos de `barehands` son una entrada experimental, no el centro de control. Toda acción sensible requiere confirmación táctil.

### 12.2 Licencias y límites de reutilización

- `fullstack-agent`, `backtalk`, `ai-visualizer` y `barehands` declaran **AGPL-3.0-or-later** en sus fuentes.
- `ai-memory-vault` declara **CC BY-SA-4.0**.
- La reutilización o modificación de código AGPL, especialmente en un servicio de red, requiere revisión de cumplimiento y una decisión de licencia del proyecto antes de integrarse.
- Las dependencias, voces de terceros y servicios externos tienen términos adicionales.
- Los videos no conceden permiso para copiar footage, marca, retratos, voces, música, números ni recursos de interfaz.
- En esta fase se adoptan únicamente patrones de arquitectura e interacción descritos arriba.

## 13. Seguridad y límites de ejecución

1. El registro de capacidades es una allowlist; una petición desconocida se rechaza.
2. Toda petición se valida contra plataforma, permiso, estado, presupuesto y riesgo.
3. Las aprobaciones son por capacidad, sesión y dispositivo, con expiración y revocación.
4. La nube exige consentimiento por turno y no recibe audio, cámara, sensores o notificaciones implícitamente.
5. Los secretos siguen en AndroidKeyStore; nunca se devuelven a la Web ni a los logs.
6. `WebChromeClient.onPermissionRequest` no concede automáticamente micrófono/cámara. Debe comprobar permiso runtime y consentimiento visible.
7. `usesCleartextTraffic="true"` es una deuda P0 existente. Esta SPEC no amplía tráfico en claro; el emparejamiento seguro debe resolverla antes de nuevos servicios de red.
8. No se usa `QUERY_ALL_PACKAGES` para listar apps.
9. No se piden contactos, SMS, `CALL_PHONE`, ubicación, `ACTIVITY_RECOGNITION`, `BODY_SENSORS`, Bluetooth runtime o alarmas exactas hasta que una subfase los necesite y los explique.
10. Los registros de auditoría guardan tipo de acción, resultado y tiempo; no guardan contenido sensible por defecto.
11. Un fallo de seguridad produce parada y mensaje, no un fallback inseguro.

## 14. Criterios de aceptación

- [ ] **CA-OMNI-01 —** Dado el catálogo Android, cuando se carga, entonces la Web consume el registro nativo y no muestra como activos los paneles D.
- [ ] **CA-OMNI-02 —** Dada una capacidad sin permiso/hardware/adaptador, cuando se consulta, entonces devuelve `no disponible` con motivo y alternativa, no un éxito simulado.
- [ ] **CA-OMNI-03 —** Dado el centro de acciones, cuando se busca una herramienta, entonces hay una sola entrada y todos los controles nuevos cumplen 48 dp/px y foco accesible.
- [ ] **CA-OMNI-04 —** Dado un sensor tridimensional, cuando emite una lectura, entonces se conservan sus tres ejes, unidades, precisión y marca de tiempo.
- [ ] **CA-OMNI-05 —** Dado un sensor ausente, cuando se muestra el inventario, entonces aparece como no presente y no se inventa un cero.
- [ ] **CA-OMNI-06 —** Dado el podómetro sin permiso `ACTIVITY_RECOGNITION`, cuando se intenta activar en API 29+, entonces no se lee y se explica cómo concederlo.
- [ ] **CA-OMNI-07 —** Dado el podómetro con permiso, cuando se muestra «hoy», entonces el valor se calcula con línea base o se etiqueta como acumulado.
- [ ] **CA-OMNI-08 —** Dada una escucha foreground, cuando termina o se pausa la actividad, entonces los listeners y el micrófono se liberan.
- [ ] **CA-OMNI-09 —** Dada la notificación de escucha, cuando hay una frase reconocida, entonces la notificación no la contiene y ofrece `Detener`.
- [ ] **CA-OMNI-10 —** Dado el botón `Detener`, cuando se pulsa, entonces el motor, la sesión y el servicio quedan cerrados y el estado visible cambia a apagado.
- [ ] **CA-OMNI-11 —** Dada la baldosa, cuando el servicio cambia de estado, entonces la baldosa refleja el estado real.
- [ ] **CA-OMNI-12 —** Dado `BOOT_COMPLETED`, cuando Android reinicia, entonces no se intenta iniciar el micrófono.
- [ ] **CA-OMNI-13 —** Dada la reproducción de CORT, cuando comienza, entonces solicita audio focus y publica estado/metadatos en `MediaSession`.
- [ ] **CA-OMNI-14 —** Dada una pérdida de audio focus o desconexión de auriculares, cuando ocurre, entonces la reproducción se pausa y no se reanuda sin acción.
- [ ] **CA-OMNI-15 —** Dado un botón multimedia, cuando la app activa no lo retiene ni expone sesión compatible, entonces CORT informa el límite y no afirma control universal.
- [ ] **CA-OMNI-16 —** Dado el asistente seleccionado, cuando Android invoca voz, entonces `RecognitionService` entrega resultado/error real y la sesión se cierra de forma controlada.
- [ ] **CA-OMNI-17 —** Dada la coexistencia, cuando se selecciona CORT, entonces ninguna app del asistente anterior se desinstala, deshabilita ni modifica.
- [ ] **CA-OMNI-18 —** Dada una memoria nueva, cuando se guarda, entonces conserva procedencia y confirmación; la escritura autónoma está desactivada.
- [ ] **CA-OMNI-19 —** Dada una alarma, cuando se crea, entonces usa el reloj del sistema salvo que una subfase posterior demuestre y apruebe programación propia.
- [ ] **CA-OMNI-20 —** Dado el acceso a notificaciones, cuando no está habilitado manualmente, entonces no se leen notificaciones de otras apps.
- [ ] **CA-OMNI-21 —** Dada una notificación allowlisted, cuando se propone responder, entonces se muestra un borrador y no se envía sin confirmación.
- [ ] **CA-OMNI-22 —** Dada la cámara de gestos, cuando se activa, entonces hay preview visible, permiso concedido, límite de sesión y cierre inmediato.
- [ ] **CA-OMNI-23 —** Dada una petición Web de cámara/micrófono, cuando llega, entonces no se concede automáticamente sin permiso runtime y consentimiento.
- [ ] **CA-OMNI-24 —** Dada una salida del modelo, cuando contiene un comando o texto sensible, entonces el código lo trata como propuesta y lo valida antes de ejecutar.
- [ ] **CA-OMNI-25 —** Dada la fase completada, cuando se revisa la evidencia, entonces se distinguen estático, compilado, navegador, dispositivo y límites; el A16 no se marca verde sin prueba física.
- [ ] **CA-OMNI-26 —** Dado el orbe/avatar, cuando cambia de reposo a escucha, procesamiento o habla, entonces el estado es visual y textualmente distinguible y `Detener` permanece accesible.
- [ ] **CA-OMNI-27 —** Dada una intención de llamada, cuando CORT la recibe, entonces no imita identidad ni coloca una llamada sin una acción explícita y una vía de telefonía/VoIP autorizada.
- [ ] **CA-OMNI-28 —** Dada una referencia AGPL/CC BY-SA, cuando se propone reutilizar código o recursos, entonces no se integra hasta registrar licencia, atribución y compatibilidad.

## 15. Casos de borde

- Sin micrófono, cámara, sensor, modelo Vosk, voz española, RAM, red o permiso.
- Pantalla apagada durante dictado, palabra de activación o reproducción.
- Auriculares Bluetooth desconectados, varias salidas simultáneas o app sin `MediaSession`.
- Botón multimedia retenido por otra app o por el asistente del sistema.
- Paso acumulado menor que la línea base por reinicio o cambio de sensor.
- Día cambiado a medianoche con el podómetro activo.
- Notificación revocada mientras el servicio sigue montado.
- `NotificationListenerService` habilitado pero desconectado o reiniciado.
- `RECORD_AUDIO` revocado durante una sesión.
- Audio focus perdido por llamada, navegación u otra app.
- Cámara ocupada por otra app o permiso revocado durante preview.
- Modelo de gestos que supera RAM o latencia aceptable.
- Entrada inválida, callback duplicado, cancelación tardía o cierre durante procesamiento.
- Memoria existente que debe migrarse sin pérdida.
- Reloj del sistema que rechaza nombre/días de alarma.
- Una app externa que no expone Intent, API o sesión compatible.

## 16. Pruebas y evidencia

### 16.1 Pruebas obligatorias por fase

| ID | Tipo | Procedimiento | Estado |
|---|---|---|---|
| T-OMNI-01 | Estática | El registro declara todos los paneles y la Web lo consume | Pendiente |
| T-OMNI-02 | Navegador | Paneles D ocultos; 360/525/desktop sin desborde ni controles duplicados | Pendiente |
| T-OMNI-03 | Java | Ejes, unidades, precisión y timestamp de sensores | Pendiente |
| T-OMNI-04 | Java | Línea base de pasos, reinicio y cambio de día | Pendiente |
| T-OMNI-05 | Estática/dispositivo | Registro y liberación de sensores en `onResume`/`onPause` | Pendiente |
| T-OMNI-06 | Estática | Notificación sin transcripción y con acción Detener | Pendiente |
| T-OMNI-07 | Dispositivo | Detener libera micrófono y actualiza UI/baldosa | Pendiente A16 |
| T-OMNI-08 | Estática | `BOOT_COMPLETED` no inicia micrófono | Pendiente |
| T-OMNI-09 | Java/dispositivo | `MediaSession`, foco, play/pausa y desconexión | Pendiente |
| T-OMNI-10 | Dispositivo | Botones con auriculares cable/Bluetooth y apps compatibles | Pendiente A16 |
| T-OMNI-11 | Compilación | `VoiceInteractionService`, sesión y reconocedor compilan | Pendiente |
| T-OMNI-12 | Dispositivo | Selección de asistente, resultado de voz y coexistencia | Pendiente A16 |
| T-OMNI-13 | SQLite | Migración de memoria y procedencia sin pérdida | Pendiente |
| T-OMNI-14 | Java | Alarmas y parser; 12 AM/PM, «y», nombres e instrucciones | Pendiente |
| T-OMNI-15 | Estática/dispositivo | Listener de notificaciones, allowlist y borrador | Pendiente |
| T-OMNI-16 | Cámara/dispositivo | Preview, permiso, gesto, límite y cierre | Pendiente A16 |
| T-OMNI-17 | Seguridad | WebView no concede cámara/micrófono automáticamente | Pendiente |
| T-OMNI-18 | Regresión | Suites APK/Web/secretos y build previos no empeoran | Pendiente |
| T-OMNI-19 | Rendimiento A16 | Batería, RAM, latencia y térmica por modo | Pendiente |
| T-OMNI-20 | Navegador/A16 | Estados del orbe distinguibles y `Detener` accesible | Pendiente |
| T-OMNI-21 | Seguridad/licencia | Llamadas no automáticas; referencias AGPL/CC no integradas sin revisión | Pendiente |

### 16.2 Evidencia actual

- Rama y commit inspeccionados: `web/cort-v0` @ `7880dbc`.
- Inspección estática de manifiesto, Java, Web y documentación: completada.
- SPEC aceptada por la usuaria el 2026-11-26 para implementar Android por fases; PC queda diferido y la publicación sólo se autoriza al cerrar el trabajo completo.
- Base Fase 0: `python scripts/prueba_apk.py` → `266/266`; `bash -n apps/android/compilar.sh` y `python -m py_compile scripts/prueba_apk.py` → verdes.
- Resultados negativos conservados: `prueba_secretos.py` bloqueado por `node` ausente del `PATH`; PC `prueba_intenciones.py` 3/18 fallos y `prueba_perfil.py` fallo por `os.getloadavg` en Windows.
- Build Android nuevo y ejecución local de `LimiteEscuchaTest`: **no ejecutados**; faltan `ANDROID_HOME`/`ANDROID_SDK_ROOT`. No se instaló el SDK ni dependencias nuevas.
- Navegador nuevo de la Fase 1: pendiente hasta implementar el contrato y ejecutar el arnés.
- A16: **verificación física pendiente**.

### 16.3 Resultado de implementación al 2026-11-27

- Fases 0–7 implementadas en código. Fase 8 y Fase 9 permanecen pendientes; Fase 10
  tiene router y planificador Android, pero no cierre conductual ni 1.0.
- `scripts/prueba_apk.py`: 337/337 en local; suites JVM: 383/383; secretos,
  consentimiento e integridad: 40/40; sintaxis JavaScript de UI, mock, orbe y puente:
  verde.
- El planificador neural valida JSON, allowlist, tipos, límites y firmas; ningún efecto
  se ejecuta sin confirmación exacta y de un solo uso. No expone shell, llamadas,
  mensajes, compras ni escritura autónoma de memoria.
- Android ofrece 272 modelos Ollama como catálogo, cuatro GGUF verificados y ocho
  proveedores nube. El teléfono usa `llama.cpp`, no un demonio Ollama. La puerta
  `INTENTAR` con `mmap` permite probar el 0.5B q2_K con 500–600 MB libres.
- Los criterios que dependen de hardware, One UI, migración SQLite real, navegador o
  rendimiento no se marcan cumplidos. La release puede publicarse como corte intermedio,
  no como verificación 1.0.

## 17. Dependencias y decisiones pendientes de aceptación

1. **D-OMNI-01:** CORT será seleccionable como asistente y coexistirá con la app anterior; se mostrará la pérdida posible del hotword del sistema.
2. **D-OMNI-02:** El catálogo Android oculta paneles D y sólo muestra capacidades reales o explicadas.
3. **D-OMNI-03:** La primera escucha background será foreground, visible y con pantalla encendida; la captura con pantalla apagada queda experimental y apagada por defecto.
4. **D-OMNI-04:** Las notificaciones de otras apps serán lectura allowlisted; no habrá respuesta automática.
5. **D-OMNI-05:** Las alarmas usarán el reloj del sistema; no se pedirán alarmas exactas en la primera fase.
6. **D-OMNI-06:** La cámara de gestos será foreground y su motor/dependencia se decidirá después de un prototipo de presupuesto.
7. **D-OMNI-07:** La memoria autónoma y la proactividad ejecutora quedan desactivadas; primero sugerencias y confirmación.
8. **D-OMNI-08:** P0 y la reconciliación de ASIS-1 se cierran o declaran antes de añadir capacidades nuevas.
9. **D-OMNI-09:** Las referencias de Hermes/OpenJarvis/OpenClaw aportan patrones, no código ni dependencias; `fullstack-agent` aporta la idea de memoria/visualizador/manos, sujeto a licencia y a un prototipo Android.
10. **D-OMNI-10:** Android empezará con estados visuales claros y un HUD 2D; la pizarra 3D, la telefonía y cualquier integración AGPL/CC quedan fuera de la primera implementación.

## 18. Fuentes oficiales de diseño

- [Tipos de servicios foreground](https://developer.android.com/develop/background-work/services/fgs/service-types)
- [Restricciones para iniciar servicios foreground](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- [Sensores: disponibilidad y ciclo de vida](https://developer.android.com/develop/sensors-and-location/sensors/sensors_overview)
- [Sensores de movimiento y podómetro](https://developer.android.com/develop/sensors-and-location/sensors/sensors_motion)
- [Audio focus](https://developer.android.com/media/optimize/audio-focus)
- [MediaSessionManager y sesiones activas](https://developer.android.com/reference/android/media/session/MediaSessionManager)
- [NotificationListenerService](https://developer.android.com/reference/android/service/notification/NotificationListenerService)
- [VoiceInteractionService](https://developer.android.com/reference/android/service/voice/VoiceInteractionService)
- [Alarmas exactas en Android 14](https://developer.android.com/about/versions/14/changes/schedule-exact-alarms)
- [`jaredrhod/fullstack-agent`](https://github.com/jaredrhod/fullstack-agent)
- [`jaredrhod/ai-memory-vault`](https://github.com/jaredrhod/ai-memory-vault)
- [`jaredrhod/backtalk`](https://github.com/jaredrhod/backtalk)
- [`jaredrhod/ai-visualizer`](https://github.com/jaredrhod/ai-visualizer)
- [`jaredrhod/barehands`](https://github.com/jaredrhod/barehands)

## 19. Cambios de requisito

| Fecha | Qué cambió | Por qué | Aprobación |
|---|---|---|---|
| 2026-11-26 | Se creó la SPEC ampliada OMNI | Integrar la visión de asistente Android, paneles, sensores, auriculares y escucha sin contradrir ASIS-001 | Pendiente |
