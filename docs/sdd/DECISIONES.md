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
- **Estado:** BORRADOR; depende de [`CUESTIONARIO-HIBRIDO.md`](CUESTIONARIO-HIBRIDO.md)
- **Contexto:** PC y Android tienen capacidades distintas; la UI ofrece nube y Gemini sin adaptador equivalente, hay claves en almacenamiento general y el modo local puede caer a nube. El puente también duplica decisiones y no comparte límites ni cancelación.
- **Propuesta:** reglas deterministas primero; cerebro local cuando haya presupuesto; nube sólo con consentimiento; degradación honesta. Adaptadores de proveedor y herramientas detrás de contratos comunes. Secretos en keyring/Keystore y interfaz limitada a capacidades reales.
- **Consecuencia si se acepta:** las claves pasan a keyring/Keystore, las capacidades se declaran por plataforma y el puente deja de ser una segunda autoridad.
- **No decide todavía:** proveedores exactos, presupuestos, sincronización ni cadencia de publicación.
