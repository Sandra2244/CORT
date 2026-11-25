# Backlog SDD — CORT

Prioridad: **P0** impide una función esencial o puede bloquear el dispositivo; **P1** afecta el uso diario; **P2** reduce confusión o deuda.

Los asuntos empiezan como **reportados**. **Verificado en código** significa que una ruta concreta se comprobó en el repositorio; no sustituye reproducirla en el A16.

| ID | Prioridad | Plataforma | Asunto | Estado | Evidencia siguiente |
|---|---|---|---|---|---|
| CORT-AND-001 | P0 | Android | Vista de teléfono: paneles solapados y modo escritorio incómodo | Verificado en código | `cort-style.css:532-555` adapta una lista de paneles; quedan anchos fijos. Colisiones en A16 pendientes |
| CORT-AND-002 | P0 | Android | Trabas al abrir paneles o responder | Verificado en código | `cort-ui.js:2633-2640` recorre todo el cuerpo cada 3 s; `Nexo.java:311-317` despacha en UI. Costo en A16 pendiente |
| CORT-AND-003 | P0 | Android | Escucha en segundo plano intermitente | Verificado en código | `ServicioEscucha.java:266-300` corta con pantalla apagada y a los cinco minutos; falta reproducir en A16 |
| CORT-AND-004 | P1 | Android | Saludo de reinicio y notificación tardíos | Verificado en código | `Arranque.java:32-47` notifica antes de TTS; canal LOW y cierre a 15 s. Demora física pendiente |
| CORT-AND-005 | P0 | Android | GGUF descargado que no carga por RAM o error | Verificado en código | `SPEC-ANDROID-001`: puerta inclusiva y MiB, 17/17 + 237/237; build y fallo físico pendientes |
| CORT-AND-006 | P1 | Android | Antivirus, webcam y herramientas de PC mal presentadas | Reportado | Declarar capacidades reales por plataforma |
| CORT-AND-007 | P1 | Android | Archivos grandes y responsabilidades mezcladas | Reportado | Medir `Nexo.java` y extraer módulos sólo con pruebas |
| CORT-PC-001 | P0 | PC | Puente sobrecargado y respuestas tardías | Verificado en código | `cort_voz.py:108-109` hace `pactl` bloqueante con timeout de 4 s; `cort_server.py:2510` crea tareas sin registro. Carga real pendiente |
| CORT-PC-002 | P1 | Ambas | Errores técnicos llegan a la persona usuaria | Verificado en código | `CerebroLocal.java:492-494` convierte vacío en `null`; los códigos nativos 1/2/3 no distinguen todas sus causas |
| CORT-DOC-001 | P1 | Repo | Documentación de licencia contradictoria | Verificado | `docs/ANDROID.md` dice MIT; `LICENSE` es propia |

## Orden propuesto

1. **Estabilidad Android:** CORT-AND-002 y CORT-AND-005.
2. **Interfaz usable:** CORT-AND-001 y CORT-AND-006.
3. **Segundo plano confiable:** CORT-AND-003 y CORT-AND-004.
4. **Puente sin bloqueos:** CORT-PC-001 y CORT-PC-002.
5. **Limpieza documental:** CORT-DOC-001.

El orden puede cambiar si la verificación demuestra que otro asunto es la causa raíz de varios síntomas.

## Qué no entra en el primer corte

- Reescribir toda la interfaz.
- Cambiar el motor de inferencia.
- Añadir nuevas funciones.
- Entrenar un modelo.
- Publicar una release sin comprobar la APK y declarar la prueba física pendiente.
