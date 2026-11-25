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
