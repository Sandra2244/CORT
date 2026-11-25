# Plantilla de especificación — CORT

Copiar este archivo como `SPEC-<AREA>-<NUMERO>.md`.

```markdown
# SPEC-<AREA>-<NUMERO> — <título corto>

- **Estado:** BORRADOR
- **Prioridad:** P0 | P1 | P2
- **Plataforma:** PC | Android | Ambas
- **Reportado por:** <persona o prueba>
- **Fecha:** AAAA-MM-DD

## Problema

Qué ocurre hoy, con evidencia de archivo:línea o reproducción. Separar hechos de hipótesis.

## Resultado esperado

Una frase que una persona usuaria pueda comprobar.

## Alcance

- Incluye: ...
- No incluye: ...

## Decisiones de comportamiento

Unidades, umbrales, estados, tiempos y límites. No escribir nombres de funciones si el comportamiento todavía no está decidido.

## Criterios de aceptación

- [ ] **CA-1 — Dado** ..., **cuando** ..., **entonces** ...
- [ ] **CA-2 — ...**

## Casos de borde

- Valor exactamente en el umbral.
- Sin permiso, red, RAM o hardware.
- Repetición, cancelación y reinicio.
- Entrada inválida o respuesta tardía.

## Plan

1. Prueba que reproduce el defecto.
2. Cambio mínimo de código.
3. Prueba de regresión.
4. Documentación y evidencia.

## Pruebas

| ID | Tipo | Comando o procedimiento | Resultado |
|---|---|---|---|
| T-01 | estática | ... | pendiente |
| T-02 | comportamiento | ... | pendiente |
| T-03 | dispositivo | ... | pendiente |

## Evidencia

- Commit o diff:
- Fecha y entorno:
- Resultado:
- Límites de verificación:

## Cambios de requisito

| Fecha | Qué cambió | Por qué | Quién lo aprobó |
|---|---|---|---|
```
