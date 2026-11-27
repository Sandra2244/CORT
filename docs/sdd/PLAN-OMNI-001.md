# PLAN-OMNI-001 — Implementación por fases

- **Estado:** EN CURSO
- **SPEC:** [SPEC-OMNI-001.md](SPEC-OMNI-001.md)
- **Base:** `web/cort-v0` @ `7880dbc55cd9da7331d3b5b3cab0d7d0b2dcccd4`
- **Fecha:** 2026-11-26
- **Regla de entrada:** no se ejecuta código de producto hasta aceptar la SPEC y las decisiones `D-OMNI-01`–`D-OMNI-10`.
- **Regla de salida:** cada fase deja código mínimo, prueba roja→verde, evidencia y una decisión explícita de continuar o detener.
- **Regla de seguridad:** una fase no concede permisos que otra fase necesitará. Si aparece un requisito nuevo, se actualiza la SPEC antes de programarlo.

## 1. Orden y dependencias

```text
FASE 0 — P0 y evidencia
    ↓
FASE 1 — Contrato de capacidades y centro único
    ↓
FASE 2 — Sensores y dispositivo
    ↓
FASE 3 — Escucha, voz y estados
    ↓
FASE 4 — Medios, audio focus y auriculares
    ↓
FASE 5 — Asistente predeterminado
    ↓
FASE 6 — Memoria, rutinas, alarmas y vida diaria
    ↓
FASE 7 — Notificaciones, apps externas y bolsillo PC
    ↓
FASE 8 — Proactividad acotada
    ↓
FASE 9 — Cámara y gestos foreground
    ↓
FASE 10 — Router híbrido y preparación de base 1.0
    ↓
PC — Escritorio, webcam/gestos y paridad de herramientas
```

La Fase 4 puede comenzar después de la 3 sin esperar la 5. La Fase 6 puede dividirse en memoria y rutinas. Ninguna fase de proactividad, nube o cámara debe adelantar el cierre de los P0 que le afecten.

## 2. Fase 0 — P0 y reconciliación de evidencia

**Objetivo:** que la base sea verificable antes de ampliarla.

**Incluye:**

- Reconciliar [SPEC-ASIS-001.md:104](SPEC-ASIS-001.md#L104) con la evidencia real de build y `LimiteEscuchaTest`.
- Mantener A16 como pendiente.
- Ejecutar, sin modificar dependencias, las pruebas existentes que el entorno permita.
- Registrar resultados negativos y dependencias faltantes.
- Confirmar el estado de `CORT-AND-001`, `CORT-AND-002`, `CORT-AND-005`, `CORT-SEC-001` y `CORT-HIB-001/002`.
- No añadir paneles nuevos durante esta fase.

**Archivos previstos:** sólo documentación SDD y pruebas existentes; no se cambia producto todavía.

**Prueba roja:** la SPEC madre afirma trabajo pendiente que ya tiene evidencia parcial, o una prueba P0 falla en el entorno.

**Salida:** evidencia separada en estático/compilado/navegador/dispositivo; P0 cerrado, bloqueado o aplazado con responsable y motivo.

**Rollback:** no hay cambios de producto; cualquier corrección documental es reversible.

**Resultado 2026-11-26:**

- `SPEC-ASIS-001.md` reconciliada: la suite estática sigue en `266/266`; `LimiteEscuchaTest` está integrado, pero no ejecutado localmente.
- `bash -n apps/android/compilar.sh` y `python -m py_compile scripts/prueba_apk.py`: verdes.
- Build Android: bloqueado por ausencia de `ANDROID_HOME`/`ANDROID_SDK_ROOT`; no se instaló el SDK.
- `prueba_secretos.py`: bloqueado porque `node` no está en el `PATH`; no se instaló Node.
- PC diferido: `prueba_intenciones.py` conserva 3 fallos de 18 y `prueba_perfil.py` falla en Windows por `os.getloadavg`.
- A16 y actualización del servicio: pendientes. `CORT-AND-001`, `CORT-AND-002`, `CORT-AND-005`, `CORT-SEC-001` y `CORT-HIB-001/002` no se cierran con esta evidencia estática.
- Fase 0: **completada con bloqueos explícitos**; no cambió producto.

## 3. Fase 1 — Contrato de capacidades y centro único

**Objetivo:** una sola puerta de acciones y una verdad compartida entre Java y Web.

### Tarea 1.1 — Registro de capacidades

**Archivos existentes:** `Nexo.java`, `apps/android/res/xml/asistente.xml`, `cort-web/cort/cort-ui.js`, `cort-web/index.html`.

**Nuevo archivo propuesto:** `Capacidades.java`, sólo si el registro no cabe limpiamente en `Nexo.java` sin duplicar código.

**Contenido mínimo:** identificador, etiqueta, plataforma, viabilidad, estado, origen, permisos, hardware, riesgo, confirmación, offline, presupuesto, dependencias, motivo y una lista opcional `controles` con los IDs Web que gobierna esa capacidad.

**Prueba roja:** una prueba estática exige que la Web use el contrato y que un panel `D` no se renderice como activo. Debe fallar antes del cambio.

**Código:** publicar el registro desde el puente; validar solicitudes desconocidas; no introducir comandos de shell ni eval.

**Prueba verde:** el registro cubre el catálogo de la SPEC; una petición desconocida se rechaza; una capacidad D queda oculta.

### Tarea 1.2 — Centro accesible y sin duplicados

**Archivos existentes:** `cort-web/cort/cort-style.css`, `cort-web/cort/cort-ui.js`, `VistaRapida.java`.

**Prueba roja:** la interfaz actual duplica entradas o deja visibles controles de PC en viewport Android.

**Código:** generar el menú desde el catálogo, conservar chat completo/modo enfoque y mantener 48 dp/px. No reescribir el orbe ni la personalidad en esta fase.

**Prueba verde:** 360/525/desktop sin desborde; una búsqueda devuelve una entrada; teclado, foco, Escape y descripciones funcionan; regresión Web previa no empeora.

### Tarea 1.3 — Estados visuales y parada prominente

**Archivos existentes:** `cort-web/cort/cort-ui.js`, `cort-web/cort/cort-style.css`, `Nexo.java`.

**Prueba roja:** la interfaz no distingue reposo, escucha, procesamiento y habla con texto/icono; `Detener` no permanece accesible durante una sesión.

**Código:** mapear el estado único de escucha a indicadores visuales y textuales; mantener una parada prominente. No copiar avatares, footage ni recursos de los videos. La animación debe respetar movimiento reducido y no bloquear el hilo Web.

**Prueba verde:** cada estado es distinguible, `Detener` cancela, la vista compacta no duplica controles y no hay regresión Web.

**Permisos nuevos:** ninguno.

**Salida:** todos los paneles actuales están clasificados A/B/C/D; no se muestra un panel D como botón activo.

**Rollback:** revertir sólo la publicación del registro y el renderizado del catálogo; la base anterior sigue disponible.

## 4. Fase 2 — Sensores y panel de dispositivo

**Objetivo:** lecturas reales, acotadas y comprensibles, reutilizando `Sensores.java`.

### Tarea 2.1 — Modelo puro de sensores

**Archivo existente:** `Sensores.java`.

**Nuevo archivo propuesto:** `LecturasSensor.java` o un helper equivalente, sólo para separar la conversión pura del callback de Android.

**Prueba roja:** acelerómetro con `values=[1,2,3]` conserva los tres ejes; sensor ausente no produce cero; temperatura de batería no ocupa el campo ambiental; pasos sin línea base no se muestran como «hoy».

**Código:** conservar vectores, unidades, timestamp y precisión; etiquetar acumulado hasta calcular línea base.

**Prueba verde:** pruebas Java de vectores, unidades, timestamp, ausencia y acumulado.

### Tarea 2.2 — Ciclo de vida y podómetro

**Archivos existentes:** `Sensores.java`, `MainActivity.java`, `AndroidManifest.xml`.

**Prueba roja:** no hay registro/liberación desde el ciclo de vida; el podómetro no declara `ACTIVITY_RECOGNITION`; no hay manejo de línea base.

**Código:** registrar al entrar en foreground y liberar al pausar; solicitar el permiso de actividad sólo al activar podómetro; persistir línea base y fecha. Si el valor es menor que la base, reiniciar la base y mostrar el total acumulado disponible, no un número negativo.

**Permiso nuevo:** `android.permission.ACTIVITY_RECOGNITION` sólo con la función de pasos. No `BODY_SENSORS` ni ubicación en esta fase.

**Prueba verde:** permiso denegado/concedido/revocado; cambio de día; reinicio del teléfono; listener liberado al pausar.

### Tarea 2.3 — Panel de dispositivo

**Archivos existentes:** `Nexo.java`, `cort-web/cort/cort-ui.js`, `cort-web/cort/cort-style.css`.

**Contenido:** inventario, última lectura, precisión, ausencia, batería, red y enlace a Ajustes.

**Prueba roja:** no existe una ruta Web que consulte sensores; el panel inventa disponibilidad.

**Prueba verde:** la Web muestra `real`, `sin lectura` o `no disponible`; un sensor no presente no rompe el panel.

**Salida:** panel funcional con lectura acotada; sin histórico ni frecuencia cardíaca.

**Rollback:** retirar el panel y los listeners; conservar el modelo puro y no borrar datos de línea base.

**A16 pendiente:** disponibilidad real, precisión, consumo, pasos con One UI y comportamiento al pausar.

## 5. Fase 3 — Escucha, voz y estados visibles

**Objetivo:** corregir la base de escucha antes de añadir nuevos modos.

### Tarea 3.1 — Privacidad y parada inmediata

**Archivos existentes:** `ServicioEscucha.java`, `AndroidManifest.xml`, `Baldosa.java`.

**Prueba roja:** la notificación contiene la transcripción; no tiene acción `Detener`; la baldosa no refleja el estado.

**Código:** título/detalle fijos, `VISIBILITY_PRIVATE`, acción `Detener`, estado único observable y limpieza completa de motor/listeners.

**Prueba verde:** la frase reconocida no aparece en la notificación; `Detener` apaga todo; la baldosa y la UI cambian de estado.

### Tarea 3.2 — Audio focus para voz

**Archivos existentes:** `Voz.java`, `ServicioEscucha.java`, `Nexo.java`, `VistaRapida.java`.

**Prueba roja:** no hay solicitud/abandono de foco ni reacción a llamadas o reproducción.

**Código:** solicitar foco antes de escuchar/hablar; pausar o detener según pérdida; abandonar al cerrar.

**Prueba verde:** foco concedido/perdido/recuperado; cierre durante sesión; sin reanudación automática indebida.

### Tarea 3.3 — Estado de escucha y límites

**Archivos existentes:** `ServicioEscucha.java`, `Nexo.java`, `Baldosa.java`, `MainActivity.java`.

**Prueba roja:** la preferencia y el estado montado se confunden; no hay transición única.

**Código:** exponer `APAGADO/PIDIENDO_PERMISO/PREPARANDO/ESCUCHANDO_PALABRA/ESCUCHANDO_MANDATO/PROCESANDO/DETENIDO/ERROR`; conservar corte por pantalla apagada y cinco minutos en esta fase.

**Prueba verde:** cada salida actualiza UI y notificación; `BOOT_COMPLETED` no intenta micrófono.

**Permisos nuevos:** ninguno; se usan los actuales.

**Salida:** palabra de activación foreground/background con pantalla encendida, visible y detenible. La captura con pantalla apagada queda apagada.

**Rollback:** volver al servicio anterior sin transcripción pública y con parada; no borrar preferencias.

**A16 pendiente:** micrófono, notificación, baldosa, foco, pantalla apagada, batería y One UI.

## 6. Fase 4 — Medios, audio focus y auriculares

**Objetivo:** controles reales sin prometer control universal.

### Tarea 4.1 — `MediaSession` de CORT

**Archivo existente:** `Acciones.java` para abrir apps; se añadirá una clase de medios si no existe un adaptador adecuado.

**Nuevo archivo propuesto:** `Medios.java`.

**Prueba roja:** no hay sesión/metadatos; no hay play/pausa real; la acción «Música» sólo abre una app.

**Código:** publicar sesión, callbacks allowlisted, atributos de medios, foco de audio y estado.

**Prueba verde:** play/pausa/siguiente/anterior/stop de CORT; cierre libera sesión y foco.

### Tarea 4.2 — Rutas y botones

**Archivo existente:** `Audifonos.java`.

**Prueba roja:** `ACTION_AUDIO_BECOMING_NOISY` no pausa; no hay manejo de `KeyEvent`/`MediaSession`; la salida se afirma sin conocer varias rutas.

**Código:** registrar receptor/callback con ciclo de vida, pausar al ruido/desconexión y manejar controles estándar.

**Permiso nuevo:** `BLUETOOTH_CONNECT` sólo si se usan APIs Bluetooth que lo requieran. La detección básica de audio no lo añade por defecto.

### Tarea 4.3 — Sesiones externas opcionales

**Prueba roja:** no hay forma de listar sesiones; el botón promete control externo sin permiso.

**Código:** si el usuario habilita acceso a notificaciones, permitir consulta/control de sesiones compatibles; si no, ofrecer sólo controles de CORT y apertura de app.

**Prueba verde:** sin listener se informa el límite; con listener, sólo sesiones compatibles; otra app reteniendo foco no se ve interrumpida indebidamente.

**Salida:** controles de CORT completos y controles externos condicionados. Doble toque y pulsación larga quedan desactivados.

**Rollback:** retirar sesión y callbacks; conservar detección de auriculares.

**A16 pendiente:** cable, USB, Bluetooth A2DP/SCO, varias salidas, foco y apps reales.

## 7. Fase 5 — Asistente predeterminado

**Objetivo:** que la selección de CORT abra una experiencia de voz real y coexistente.

### Tarea 5.1 — `RecognitionService` real

**Archivo existente:** `Reconocimiento.java`.

**Prueba roja:** `onStartListening` abre `MainActivity` y devuelve `ERROR_NO_MATCH` sin resultado.

**Código:** ejecutar el motor de reconocimiento disponible, entregar resultados por callback, cancelar y liberar. Si se usa el motor del sistema, declarar que puede usar red. No mantener una actividad como sustituto del contrato.

**Prueba verde:** compilación; resultados, error, cancelación y cierre; no se cuelga el servicio.

### Tarea 5.2 — Sesión de conversación

**Archivos existentes:** `Sesion.java`, `Asistente.java`, `VistaRapida.java`, `Voz.java`.

**Prueba roja:** `onShow` muestra overlay y termina; no existe conversación.

**Código:** mantener la sesión hasta completar/cancelar, abrir la vista completa para conversación y cerrar recursos. Evitar trabajo pesado en `VoiceInteractionService`; usar el servicio de sesión.

**Prueba verde:** invocación, resultado, vista rápida, chat, cierre y nueva invocación no duplican instancias.

### Tarea 5.3 — Selección y coexistencia

**Archivos existentes:** `MainActivity.java`, `cort-web/cort/cort-ui.js`.

**Prueba roja:** no se explica la pérdida del hotword ni el cambio de asistente.

**Código:** instrucciones para Ajustes, aviso de consecuencia y botón para volver a abrir ajustes. No desinstalar ni deshabilitar ninguna app.

**Permisos nuevos:** los ya declarados para asistente; no se añade `CALL_PHONE`, contactos ni SMS.

**Salida:** asistente seleccionable con contrato funcional, sujeto a A16.

**Rollback:** registrar la selección anterior no es posible de forma programática universal; la UI guía a la persona a cambiarla en Ajustes. El código puede revertirse sin tocar apps externas.

**A16 pendiente:** selección, tecla/gesto, keyguard, Bluetooth, resultado y vuelta al asistente anterior.

## 8. Fase 6 — Memoria, rutinas, alarmas y vida diaria

### Tarea 6.1 — Memoria con procedencia

**Archivo existente:** `Recuerdos.java`.

**Prueba roja:** no hay procedencia/confirmación; la migración podría borrar hechos/habilidades/turnos.

**Código:** migración SQLite versionada y conservadora; añadir campos de procedencia y confirmación; limitar escritura autónoma; UI para ver/corregir/borrar.

**Prueba verde:** migración idempotente, datos conservados, registro inválido rechazado y borrado local efectivo.

### Tarea 6.2 — Alarmas del sistema

**Archivos existentes:** `Acciones.java`, `Cerebro.java`, pruebas de intenciones.

**Prueba roja:** parser no cubre los casos de ASIS-2 o el Intent no incluye todos los campos necesarios.

**Código:** completar parser puro y `AlarmClock`; no pedir permiso exacto.

**Prueba verde:** 12 AM/PM, «y», nombre, días, timer, hora inválida y confirmación del catálogo.

### Tarea 6.3 — Rutinas y frases

**Archivos existentes:** `Recuerdos.java`, `Nexo.java`, `cort-web/cort/cort-ui.js`.

**Prueba roja:** no hay modelo de rutina, límites ni trazabilidad.

**Código:** rutina de pasos allowlisted, ejecución una vez, cancelación, historial y fuente/licencia de frases.

**Prueba verde:** rutina válida/ inválida, paso sensible que exige confirmación, fallo parcial y cancelación.

**Permisos nuevos:** ninguno en esta primera fase.

**Salida:** memoria y acompañamiento útiles sin ejecución autónoma.

**Rollback:** conservar base y ofrecer exportación local; revertir sólo UI/ejecución, no borrar datos.

**A16 pendiente:** reloj, voz, One UI, reinicios y conservación de datos.

## 9. Fase 7 — Notificaciones, apps externas y bolsillo

### Tarea 7.1 — Listener de notificaciones

**Archivos existentes:** `AndroidManifest.xml`, `Nexo.java`, `cort-web/cort/cort-ui.js`.

**Nuevo archivo propuesto:** `Avisos.java` como `NotificationListenerService`.

**Prueba roja:** no hay servicio declarado; el manifiesto no tiene `BIND_NOTIFICATION_LISTENER_SERVICE`; no hay allowlist.

**Código:** servicio `exported` según el contrato del sistema, permiso de bind, habilitación manual, allowlist y lectura bajo demanda. No responder.

**Permiso/configuración:** no es un permiso runtime; se habilita desde Ajustes.

**Prueba verde:** deshabilitado no lee; habilitado lee sólo allowlist; reconexión y revocación no filtran contenido.

### Tarea 7.2 — Borradores y compartir

**Archivos existentes:** `Lectura.java`, `VistaRapida.java`, `Nexo.java`.

**Prueba roja:** no hay borrador/confirmación; una intención de mensaje intenta enviarse.

**Código:** `ACTION_SEND` con texto mostrado y confirmación; no API privada de WhatsApp/SMS; no respuesta automática.

**Prueba verde:** cancelar no comparte; confirmar abre el selector; texto sensible no se registra en logs.

### Tarea 7.3 — Bolsillo y enlace PC

**Prueba roja:** la capacidad se ofrece sin puente activo o sin límites de cancelación.

**Código:** mostrar `no disponible` si no hay enlace; reutilizar contrato seguro/cancelable. No ampliar red en claro.

**Salida:** lectura de notificaciones y compartir seguro; PC opcional.

**Rollback:** deshabilitar listener y allowlist; no borrar notificaciones del sistema.

**A16 pendiente:** Ajustes, revocación, reconexión, One UI y privacidad en pantalla de bloqueo.

## 10. Fase 8 — Proactividad acotada

**Objetivo:** ayudar sin interrumpir ni ejecutar de más.

**Archivos previstos:** un adaptador de sugerencias y el centro Web; sin servicio persistente nuevo al inicio.

**Prueba roja:** no hay política de frecuencia, batería, consentimiento o límite.

**Código:** sugerencia dentro del centro, apagada por defecto, una por intervalo, razón visible, descarte y bloqueo de acciones sensibles.

**Prueba verde:** consentimiento denegado no genera sugerencias; límite de frecuencia; sin red no simula contexto; no envía mensajes/llamadas.

**Salida:** sugerencias descartables. Despertar proactivo y ejecución automática quedan diferidos.

**Rollback:** apagar sugerencias; no se crean alarmas propias.

**A16 pendiente:** batería, frecuencia, molestia y comportamiento en segundo plano.

## 11. Fase 9 — Cámara y gestos foreground

**Objetivo:** prototipo visible y medible, no una promesa de omnipresencia.

### Tarea 9.1 — Decisión del motor

**Prueba roja/documental:** no hay medición de tamaño, RAM, latencia, licencia y disponibilidad de las alternativas.

**Salida:** decisión escrita sobre Camera2/ML Kit/MediaPipe u otra opción, con dependencia mínima justificada y revisión de licencia de cada componente. No se importa código de `barehands` sin cumplimiento AGPL.

### Tarea 9.2 — Preview y permiso

**Archivos existentes:** `MainActivity.java`, `Escaner.java`, `Nexo.java`, `AndroidManifest.xml`.

**Prueba roja:** el WebView concede cámara automáticamente; no hay preview/cierre.

**Código:** sesión foreground con preview, indicador, permiso runtime, timeout y cierre. Cambiar `onPermissionRequest` para validar antes de conceder.

**Permiso:** `CAMERA` ya declarado. No se añade `FOREGROUND_SERVICE_CAMERA` hasta que exista un servicio real que lo necesite.

### Tarea 9.3 — Un gesto

**Prueba roja:** no hay detector ni acción visible.

**Código:** detectar un gesto sencillo y mostrar la acción propuesta; confirmación para cualquier acción sensible. Sin guardar fotogramas. El HUD será 2D y discreto antes de plantear una pizarra 3D.

**Prueba verde:** permiso denegado, cámara ocupada, gesto ausente, falso positivo, cierre, pausa y límite de RAM/latencia.

**Salida:** prototipo experimental visible. Si no cumple presupuesto, se declara no disponible y se mantiene el control táctil.

**Rollback:** retirar preview, listener y modelo; conservar QR y cámara existente.

**A16 pendiente:** térmica, RAM, latencia, orientación, auriculares y cierre durante llamada.

## 12. Fase 10 — Router híbrido y preparación de base 1.0

**Objetivo:** completar capacidades sin ocultar límites y cerrar la fase ASIS-5.

**Incluye:**

- Router común reglas → local → nube consentida → degradación.
- Gemini real sólo después de proveedor, secreto, presupuesto y consentimiento verificados.
- Presupuestos visibles de tokens, coste, latencia, RAM, CPU y red.
- Suites, build, actualización, conservación de datos y revisión de licencias.
- Prueba física completa en A16.
- Cierre de P0 y ausencia de promesas sin evidencia.

**Prueba roja:** una capacidad Web/nativa sigue divergente o una acción sensible puede saltarse consentimiento.

**Prueba verde:** matriz de capacidades coincide con código; todas las CA-OMNI tienen evidencia; A16 completado o la base no se declara 1.0.

**Permisos nuevos:** sólo los que cada proveedor/adaptador demuestre; ninguno por defecto.

**Salida:** candidata a verificación 1.0, no publicación automática.

**Rollback:** desactivar proveedor/adaptador y volver a reglas/local; conservar secretos y preferencias.

## 13. Fase PC — Después de Android

**Objetivo:** reutilizar contratos, no la UI ni las APIs de escritorio.

**Incluye:**

- Centro de acciones filtrado por capacidades PC.
- Router común y adaptadores de herramientas existentes.
- Memoria/skills con licencias revisadas.
- Webcam y gestos `fullstack-agent` como patrón, no trasplante.
- Paridad de herramientas con verificación y raíces permitidas.
- Bridge sin bloqueos, cancelación completa y trabajo registrado.

**No incluye:** ejecutar comandos de escritorio desde Android ni exponer shell como herramienta por defecto.

**Prueba roja:** una acción PC no tiene adaptador, allowlist, presupuesto o verificación.

**Salida:** SPEC PC propia y plan; no se implementa bajo esta SPEC Android sin ampliación aprobada.

## 14. Matriz de permisos nuevos

| Permiso/configuración | Fase | Cuándo se solicita | Cuándo no se pide |
|---|---|---|---|
| `ACTIVITY_RECOGNITION` | 2 | Al activar podómetro/detector de pasos | Si el usuario no usa pasos |
| `BLUETOOTH_CONNECT` | 4 | Sólo si se usa una API Bluetooth que lo exija | Para detección básica de salida de audio |
| Listener de notificaciones | 7 | Al activar lectura de notificaciones | Si no se usa la función |
| `BODY_SENSORS` | Diferida | SPEC propia de salud | Nunca en esta primera SPEC |
| Ubicación | Diferida | SPEC propia de clima/ubicación | No se pide para sensores generales |
| `SCHEDULE_EXACT_ALARM`/`USE_EXACT_ALARM` | Diferida | Necesidad visible y permiso concedido | Alarmas mediante reloj del sistema |
| `HIGH_SAMPLING_RATE_SENSORS` | Diferida | Muestreo >200 Hz justificado | Primera fase usa `SENSOR_DELAY_UI` |
| `FOREGROUND_SERVICE_CAMERA` | Diferida | Servicio de cámara real | Preview foreground en actividad |
| `MEDIA_CONTENT_CONTROL` | No usar | No es una vía inicial | Se prefiere listener habilitado |
| `QUERY_ALL_PACKAGES` | No usar | Nunca para el catálogo | `<queries>` + Intents |

## 15. Matriz de riesgo y rollback

| Riesgo | Mitigación | Rollback |
|---|---|---|
| Más paneles aumentan trabajo UI | Catálogo filtrado y una sola entrada | Ocultar capacidades no verificadas |
| Batería por sensores/escucha | Muestreo lento, foreground, timeout, parada | Liberar listeners y detener servicio |
| Fuga de transcripción | Notificación fija y sin logs sensibles | Detener escucha y limpiar aviso |
| Otra app retiene audio/botones | Respetar foco y sesión activa | Sólo controles de CORT |
| Permisos denegados/revocados | Estado y alternativa visibles | Desactivar función sin fallback simulado |
| Memoria corrupta | Migración versionada y backup/exportación | Conservar copia local y no borrar datos |
| Dependencia AGPL/derechos | Revisar licencia antes de decidir motor o recurso visual | Usar patrón, no código, footage, marca ni voz |
| Modelo no cabe | Medir antes de integrar | Declarar no disponible |
| Cámara invade privacidad | Preview, permiso, timeout y cierre | Retirar sesión y modelo |
| Nube filtra datos | Consentimiento por turno y minimización | Modo local sin caída |

## 16. Evidencia mínima por entrega

Cada entrega debe registrar:

```text
Fase/tarea:
SPEC/CA:
Archivos cambiados:
Prueba roja (comando y resultado):
Prueba verde (comando y resultado):
Estático:
Compilado:
Navegador:
Dispositivo y versión:
Permisos añadidos:
Rendimiento/batería:
Fallos conocidos:
Rollback:
Siguiente paso:
```

No se rellena un campo con «listo» o «funciona». Si no se ejecutó, se escribe **no ejecutado** y el motivo.

## 17. Primera tarea recomendada tras aprobar la SPEC

**Fase 1.1 — registro de capacidades**, precedida por la Fase 0 de reconciliación.

1. Inventariar el catálogo actual con identificadores estables.
2. Añadir una prueba que falle porque la Web no consume capacidades.
3. Publicar el contrato desde `Nexo.java` sin añadir permisos.
4. Filtrar paneles D y mostrar motivos A/B/C.
5. Ejecutar pruebas estáticas/Web y revisar el diff.
6. Dejar la Fase 2 lista sólo si la 1 está verde.

Esta primera tarea es pequeña, reversible y no modifica micrófono, cámara, red, memoria ni servicios.

## 18. Cambios de plan

| Fecha | Qué cambió | Por qué | Aprobación |
|---|---|---|---|
| 2026-11-26 | Se creó el plan OMNI | Convertir la visión amplia en fases pequeñas y verificables | Pendiente |
| 2026-11-27 | Cierre intermedio `cort-v0.20.2`: fases 0–7 y router Android implementados; 8–10 y PC quedan abiertos | La usuaria autorizó publicar lo verificado y documentar el resto para continuar mañana | Autorizada por la usuaria |

## 19. Cierre intermedio `cort-v0.20.2`

- **Código:** fases 0–7 implementadas; catálogo Ollama, router híbrido, proveedores
  cifrados, personalidades y planificador neural allowlisted integrados.
- **Estático:** `scripts/prueba_apk.py` 337/337 antes de añadir la guarda de firma; el
  workflow repite la suite sobre el APK final.
- **JVM:** 383/383. La migración SQLite real sigue pendiente como evidencia física,
  no como resultado inventado.
- **Seguridad e integridad:** 40/40; la suite del APK queda 337/337 en local.
- **JavaScript:** sintaxis verde para UI, mock, orbe y puente Android.
- **Build:** GitHub Actions con `aapt2 → javac --release 11 → d8 → zipalign → apksigner`;
  motor nativo, oído, cara Web, alineación y certificado se comprueban antes de publicar.
- **Dispositivo:** A16 no ejecutado. No se declara 1.0 ni conversación larga verificada.
- **Pendiente:** Fase 8, Fase 9, matriz conductual completa de Fase 10, navegador,
  rendimiento/batería/térmica del A16 y fases PC.
