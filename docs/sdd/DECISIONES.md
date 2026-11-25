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
