# Decisiones de arquitectura — CORT

Formato: una decisión por sección. No borrar decisiones antiguas; marcarlas como sustituidas.

## ADR-001 — Android es el primer frente de estabilidad

- **Fecha:** 2026-11-24
- **Estado:** Aceptada
- **Contexto:** la persona usuaria reporta trabas, paneles solapados, fallos de segundo plano y cerebros que no cargan en Android.
- **Decisión:** estabilizar primero la APK. El puente de PC se corrige cuando sea la causa raíz de un fallo Android o exista un SPEC propio.
- **Consecuencia:** no se añaden funciones nuevas hasta cerrar los P0 con evidencia.

## ADR-002 — SDD ligero antes que una herramienta nueva

- **Fecha:** 2026-11-24
- **Estado:** Aceptada
- **Contexto:** CORT ya tiene documentación extensa; falta trazabilidad entre necesidad, código, prueba y evidencia.
- **Decisión:** usar archivos Markdown con identificadores estables. No instalar Spec Kit ni otra dependencia en este primer corte.
- **Consecuencia:** el método puede aplicarse desde Sublime Text, Git y cualquier agente sin configuración adicional.

## ADR-003 — Arquitectura híbrida con contratos compartidos

- **Fecha:** 2026-11-24
- **Estado:** Aceptada
- **Decisión de producto:** [`CUESTIONARIO-HIBRIDO.md`](CUESTIONARIO-HIBRIDO.md), respuestas `1A, 2A, 3A, 4A, 5A, 6A, 7A, 8A, 9A, 10A`.
- **Contexto:** PC y Android tienen capacidades distintas; la UI ofrece nube y Gemini sin adaptador equivalente, hay claves en almacenamiento general y el modo local puede caer a nube. El puente también duplica decisiones y no comparte límites ni cancelación.
- **Decisión:** reglas deterministas primero; cerebro local cuando haya presupuesto; nube sólo con consentimiento; degradación honesta. Adaptadores de proveedor y herramientas detrás de contratos comunes. Secretos en keyring/Keystore e interfaz limitada a capacidades reales.
- **Decisiones aceptadas:**
  - P0 antes de funciones nuevas: secretos, verdad de la nube, vista táctil, bloqueos, segundo plano, puente PC y GGUF.
  - Personalidad equilibrada entre operador y compañero.
  - Router local-first adaptativo: reglas → GGUF/Ollama → nube consentida → degradación.
  - Proveedores objetivo: Gemini, OpenAI-compatible y local. Gemini debe construirse, no sólo mostrarse.
  - Custodia por dispositivo: keyring en PC y Keystore en Android.
  - Texto mínimo con confirmación; audio, pantalla, cámara y archivos no salen sin acción explícita; modo local sin caída a nube.
  - Presupuestos configurables y visibles de tokens, coste, latencia, RAM, CPU y red.
  - Después de P0: automatización verificable y memoria/proactividad.
  - Android autónomo; la PC es opcional.
  - Publicación por fase verificada en `web/cort-v0`; sin etiqueta ni Release por defecto.
- **Consecuencia:** primero `SPEC-SEC-001`; después los P0 de estabilidad. La construcción de proveedores queda para `SPEC-HIB-001`, sin volver a ofrecerlos como capacidades presentes.
- **Cadencia:** cada fase nueva abre su propio cuestionario. La tanda actual se ejecuta después de las respuestas, sin volver a preguntar lo ya decidido.

## ADR-004 — Asistente personal por subfases verificables

- **Fecha:** 2026-11-25
- **Estado:** Aceptada como criterio operativo, corregible
- **Contexto:** [`CUESTIONARIO-ASISTENTE-001.md`](CUESTIONARIO-ASISTENTE-001.md). La persona usuaria pidió comenzar el desarrollo completo sin marcar las opciones; no se atribuye una respuesta textual que no dio.
- **Decisión:** ejecutar las recomendaciones A, en este orden:
  1. Asistente Android, enfoque del orbe, chat, escucha larga y alarmas con instrucciones.
  2. Música, auriculares y organización de archivos con vista previa y deshacer.
  3. Notificaciones, personalidad, voces y rutinas con frases trazables.
  4. Router híbrido común con Gemini y degradación local.
  5. Verificación física en el A16 y evaluación de una base 1.0.
- **Límites:** el asistente lo selecciona Android; la superposición exige permiso; no se suplanta a Gemini, no se clonan voces, no se mueven ni borran archivos sin autorización y no se declara estabilidad sin evidencia física.
- **Consecuencia:** [`SPEC-ASIS-001.md`](SPEC-ASIS-001.md) se cierra por subfases. Una función pendiente se muestra como pendiente, no como promesa cumplida.

## ADR-005 — Un centro de acciones y chat de pantalla completa

- **Fecha:** 2026-11-25
- **Estado:** Aceptada
- **Contexto:** la usuaria rechazó la jerarquía anterior: flechas, botones Chat/Paneles y compositores distintos abren funciones parecidas. Pidió una UI accesible, futura y ordenada, con chat completo superpuesto y la misma vista previa al invocar CORT con auriculares.
- **Decisión:** reutilizar el menú existente como única puerta de acciones; mover Chat, Enfoque y palabra de despertar a su interior; retirar la bandeja lateral y su flecha; convertir el chat en diálogo de pantalla completa con un solo compositor; alinear la vista rápida nativa con la misma paleta y jerarquía.
- **Referencias verificadas:** HERMES aporta el patrón de centro accesible y tacto de 44 px; OpenJARVIS aporta rutas/pantallas separadas y diálogos con fondo; LinuxJarvis respalda «un menú, distintas pantallas». Se implementan los patrones en el WebView, sin trasplantar React, Qt ni código TechEnClair sin licencia.
- **Consecuencia:** ASIS-1.10–1.15 son bloqueantes. La evidencia anterior de chat y selector se conserva, pero no basta para cerrar la fase.
