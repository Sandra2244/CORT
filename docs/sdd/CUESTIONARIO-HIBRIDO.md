# Cuestionario de producto híbrido — CORT

- **Fecha:** 2026-11-24
- **Estado:** respondido y aceptado
- **Respuesta:** `1A, 2A, 3A, 4A, 5A, 6A, 7A, 8A, 9A, 10A`
- **Registro:** las diez decisiones están incorporadas en [`DECISIONES.md`](DECISIONES.md), ADR-003.
- **Compromiso:** después de tus respuestas se convierten en ADR y SPEC; se ejecuta la tanda acordada sin volver a preguntar lo mismo. Si una respuesta cambia durante el trabajo, se registra el cambio de requisito.

**Hallazgo que cambia la prioridad:** la UI ofrece nube y Gemini, pero PC sólo ejecuta Ollama; Android no tiene adaptador Gemini. Hay claves en `localStorage` y `SharedPreferences` en claro, y el modo local puede caer a nube si GGUF falla. Por eso secreto, privacidad y verdad de capacidades entran en P0.

## 1. Prioridad

¿Qué cerramos antes de añadir capacidades?

- **A. P0 primero (recomendado):** secretos y verdad de la nube, vista táctil, bloqueos de interfaz, segundo plano, puente PC y carga GGUF.
- **B. Híbrido primero:** router, proveedores y secretos antes de cerrar todos los P0.
- **C. Sólo Android:** PC queda fuera hasta estabilizar el teléfono.

## 2. Personalidad

¿Qué equilibrio quieres entre JARVIS operador y Cortana compañera?

- **A. Equilibrado (recomendado):** ejecuta con precisión y conversa con contexto; interrumpe sólo cuando aporta.
- **B. Operador:** prioriza tareas, archivos, apps y automatización; conversación breve.
- **C. Compañero:** prioriza voz, memoria, rutinas y acompañamiento; automatización más conservadora.

## 3. Router

¿Cómo elige CORT entre reglas, local y nube?

- **A. Local-first adaptativo (recomendado):** reglas → GGUF/Ollama si hay margen → nube consentida → degradación.
- **B. Manual:** tú eliges local o nube por modo; CORT no cambia automáticamente.
- **C. Nube-first:** usa la nube cuando haya clave y red; local como respaldo.

## 4. Proveedores

¿Qué proveedores entran en la primera versión híbrida?

- **A. Gemini + OpenAI-compatible + local (recomendado):** tres adaptadores con contrato común; Gemini hay que construirlo, no sólo mostrarlo.
- **B. Sólo Gemini + local:** menos superficie de integración.
- **C. Multi-nube amplia:** Gemini, OpenAI, Anthropic y otros desde el inicio.

## 5. Custodia de claves

¿Dónde viven las API keys?

- **A. Almacén seguro por dispositivo (recomendado):** keyring en PC y Keystore en Android; nunca en repo, APK, logs ni respaldo.
- **B. Sólo PC:** Android usa el puente y no guarda claves.
- **C. Config cifrada portable:** una configuración cifrada que puedas mover entre dispositivos, con custodia explícita.

## 6. Privacidad

¿Qué puede salir a la nube?

- **A. Texto mínimo con confirmación (recomendado):** audio, pantalla, cámara y archivos no salen sin una acción explícita; el texto sensible pide confirmación; si el modo local falla, no pasa a nube sin permiso.
- **B. Sólo texto:** puedes enviar conversación, pero nunca audio, imágenes ni archivos.
- **C. Todo con permiso global:** eliges un modo que permite todos los datos y CORT lo muestra siempre.

## 7. Presupuestos

¿Cómo limitamos recursos y coste?

- **A. Configurables y visibles (recomendado):** límites de tokens, coste, latencia, RAM, CPU y red; al agotarse se degrada.
- **B. Conservadores fijos:** límites seguros iniciales y ajuste manual posterior.
- **C. Sólo avisos:** CORT informa, pero no bloquea automáticamente.

## 8. Dos capacidades nuevas prioritarias

Además de estabilidad, ¿qué dos construimos primero?

- **A. Automatización verificable + memoria/proactividad (recomendado).**
- **B. Investigación con fuentes + voz/visión.**
- **C. Rutinas/notificaciones + archivos y apps.**
- **D. Sincronización PC↔Android + panel de diagnóstico.**

## 9. Relación PC y Android

¿Qué independencia debe tener el teléfono?

- **A. Autónomo con PC opcional (recomendado):** el teléfono conserva reglas, GGUF, voz y memoria; la PC aporta potencia y herramientas.
- **B. Dependiente del PC:** sin puente, Android queda limitado a lo básico.
- **C. Sincronización en nube:** ambos dispositivos comparten estado y memoria mediante un servicio.

## 10. Cadencia de publicación

¿Cuándo publicamos cada fase?

- **A. Push por fase verificada (recomendado):** `web/cort-v0`; sin etiqueta ni Release por defecto.
- **B. Push + etiqueta demo:** cada fase verde crea una etiqueta de demostración.
- **C. Tanda larga:** varias fases en local y una sola publicación al final.

## Valores recomendados

Si quieres aceptar la propuesta completa, responde:

```text
1A, 2A, 3A, 4A, 5A, 6A, 7A, 8A, 9A, 10A
```

La recomendación no añade funciones antes de cerrar P0. La sección 8 sólo ordena lo que vendrá después de la estabilidad.
