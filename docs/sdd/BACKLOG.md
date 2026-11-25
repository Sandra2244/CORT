# Backlog SDD — CORT

Prioridad: **P0** impide una función esencial o puede bloquear el dispositivo; **P1** afecta el uso diario; **P2** reduce confusión o deuda.

Los asuntos empiezan como **reportados**. **Verificado en código** significa que una ruta concreta se comprobó en el repositorio; no sustituye reproducirla en el A16.

| ID | Prioridad | Plataforma | Asunto | Estado | Evidencia siguiente |
|---|---|---|---|---|---|
| CORT-AND-001 | P0 | Android | Vista de teléfono: paneles solapados y modo escritorio incómodo | Verificado en código | `cort-web/cort/cort-style.css:532-555` adapta una lista de paneles; uno nuevo puede quedar fuera. Colisiones en A16 pendientes |
| CORT-AND-002 | P0 | Android | Trabas al abrir paneles o responder | Verificado en código | `cort-ui.js:2633-2640` recorre todo el cuerpo cada 3 s; `Nexo.java:311-317` despacha en UI. Costo en A16 pendiente |
| CORT-AND-003 | P0 | Android | Escucha en segundo plano intermitente | Verificado en código | `ServicioEscucha.java:279-324` corta con pantalla apagada y a los cinco minutos; falta reproducir en A16 |
| CORT-AND-004 | P1 | Android | Saludo de reinicio y notificación tardíos | Verificado en código | `Arranque.java:32-47` notifica antes de TTS; canal LOW y cierre a 15 s. Demora física pendiente |
| CORT-AND-005 | P0 | Android | GGUF descargado que no carga por RAM o error | Verificado en código | `SPEC-ANDROID-001`: puerta inclusiva y MiB, 17/17 + 237/237; CI `45516435873` verde; fallo físico pendiente |
| CORT-AND-006 | P1 | Android | Antivirus, webcam y herramientas de PC mal presentadas | Reportado | Declarar capacidades reales por plataforma |
| CORT-AND-007 | P1 | Android | Archivos grandes y responsabilidades mezcladas | Reportado | Medir `Nexo.java` y extraer módulos sólo con pruebas |
| CORT-PC-001 | P0 | PC | Puente sobrecargado y respuestas tardías | Verificado en código | `cort_voz.py:108-109` hace `pactl` bloqueante con timeout de 4 s; `cort_server.py:2510` crea tareas sin registro. Carga real pendiente |
| CORT-PC-002 | P1 | Ambas | Errores técnicos llegan a la persona usuaria | Verificado en código | `CerebroLocal.java:492-494` convierte vacío en `null`; los códigos nativos 1/2/3 no distinguen todas sus causas |
| CORT-DOC-001 | P1 | Repo | Documentación de licencia contradictoria | Verificado | `docs/ANDROID.md` dice MIT; `LICENSE` es propia |
| CORT-SEC-001 | P0 | Ambas | Claves en `localStorage`, `SharedPreferences` en claro y estado general | Verificado en código | `cort-mock.js:364-368,519-523`; `Nube.java:23-27,37-77`; `cort_server.py:2093-2106` |
| CORT-HIB-001 | P0 | Ambas | UI ofrece nube/Gemini sin implementación equivalente | Verificado en código | PC sólo Ollama; `Nube.java` sólo Anthropic/OpenAI-compatible; modal WebView no alimenta la configuración nativa |
| CORT-PC-003 | P0 | PC | Inferencia sin cancelación completa al cerrar o detener | Verificado en código | `cort_server.py:1376-1382` cancela sólo el redactor; GGUF/nube no comparten timeout y cancelación |
| CORT-CORE-001 | P1 | Ambas | Herramientas y verificación sin paridad PC/Android | Verificado en código | PC tiene siete verbos y verificación de archivos; Android usa reglas exactas |
| CORT-DOC-002 | P1 | Repo | Documentación funcional contradictoria | Verificado | `docs/ANDROID.md:354-369` e `INFORME_FUNCIONES.md:104` discrepan sobre ajustes |

## Orden propuesto

1. **Privacidad y verdad de la nube:** CORT-SEC-001 y CORT-HIB-001.
2. **Estabilidad Android:** CORT-AND-002 y CORT-AND-005.
3. **Interfaz usable:** CORT-AND-001 y CORT-AND-006.
4. **Segundo plano confiable:** CORT-AND-003 y CORT-AND-004.
5. **Puente sin bloqueos ni trabajo huérfano:** CORT-PC-001, CORT-PC-003 y CORT-PC-002.
6. **Contratos y documentación:** CORT-CORE-001, CORT-DOC-001 y CORT-DOC-002.

El orden puede cambiar si la verificación demuestra que otro asunto es la causa raíz de varios síntomas.

## Trabajo posterior propuesto

Estas filas **no están aceptadas**; dependen del cuestionario y no adelantan los P0. Seguridad, nube y contratos ya están ordenados arriba.

| ID | Prioridad | Plataforma | Asunto | Estado |
|---|---|---|---|---|
| CORT-MEM-001 | P2 | Ambas | Memoria local con procedencia y sincronización opcional | Propuesto |
| CORT-AUTO-001 | P2 | Ambas | Automatización verificable y rutinas con confirmación | Propuesto |

Detalle y dependencias: [`INFORME_HIBRIDO_PC_ANDROID.md`](INFORME_HIBRIDO_PC_ANDROID.md).

## Qué no entra en el primer corte

- Reescribir toda la interfaz.
- Cambiar el motor de inferencia.
- Añadir nuevas funciones.
- Entrenar un modelo.
- Publicar una release sin comprobar la APK y declarar la prueba física pendiente.
