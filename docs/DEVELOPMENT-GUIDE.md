# Guía de desarrollo y contexto del proyecto

Este documento es la **fuente de verdad**. Cualquier persona o agente de IA que trabaje en CORT empieza aquí. Si cambias de herramienta, solo le dices: *"Lee AGENTS.md y docs/DEVELOPMENT-GUIDE.md"*.

## 1. Qué estamos construyendo
CORT es un asistente local-first con presencia (avatar holográfico, voz, gestos) que controla PC y teléfono. Inspirado en Cortana de Halo, limitado a lo real y posible. Detalle en `VISION.md`, `ARCHITECTURE.md` y `FUNCTIONS.md`.

## 2. Herramienta de desarrollo: decisión

Tu situación: CodeGPT se queda sin cuota al día, Antigravity no te funciona bien y no te gustan las extensiones de VS Code/VSCodium.

| Opción | Veredicto |
|---|---|
| **OpenCode** | **Principal.** Agente open source (MIT) en terminal o app de escritorio, sin extensiones. Trae modelos gratuitos incluidos y acepta 75+ proveedores, incluido Ollama local. |
| **Ollama local** | **Respaldo permanente.** Sin cuota. Más lento y menos capaz. |
| **Antigravity** | **Solo apoyo ocasional.** Su capa gratuita tiene cuota semanal y, según reportes y análisis recientes, Google la ha ido reduciendo; hay usuarios de pago con bloqueos de días. No sirve como herramienta diaria. |
| **CodeGPT** | Déjalo para consultas rápidas, no para desarrollar. |
| **OmniRoute** | Opcional y avanzado. Es un enrutador que une varios proveedores bajo una URL. No lo uses hasta que OpenCode funcione. Ojo: pasar la cuota de un producto de consumo (p. ej. tu cuenta Google) por un tercero puede violar los términos de ese servicio y arriesgar la cuenta; prefiere claves de API oficiales. |

Los modelos gratuitos y sus límites cambian con frecuencia. Verifícalos con `opencode models` y en opencode.ai antes de planificar.

### Puesta en marcha (OpenCode)
```bash
# Windows: scoop install opencode  (o choco install opencode)
# Linux/macOS/Codespaces:
curl -fsSL https://opencode.ai/install | bash

cd CORT
opencode            # abre la interfaz en la terminal
/models             # elige un modelo gratuito
```
OpenCode lee `AGENTS.md` del repo automáticamente. Para Ollama de respaldo: instala Ollama, `ollama pull qwen2.5-coder:7b` y usa el `opencode.json` incluido (revisa la sintaxis actual en opencode.ai/docs/providers por si cambió).

Atajos útiles: Tab alterna entre el agente **Plan** (solo lee y propone) y **Build** (edita y ejecuta).

## 3. Método de trabajo (el que evita perder cuota)
1. **Plan primero, Build después.** Pide el plan en modo Plan (barato), revísalo, y recién entonces ejecuta.
2. **Una fase del ROADMAP por sesión.** Contexto pequeño = menos tokens y menos errores.
3. **Tareas atómicas.** "Añade la tabla `memories` y su prueba", no "haz la memoria".
4. **Pruebas siempre.** `make test` antes de cada commit. Si algo falla, pega el error exacto al agente.
5. **Commit pequeño y frecuente.** `feat|fix|docs|test: ...`. Es tu red de seguridad si el agente rompe algo.
6. **Cuando se acabe la cuota**: cambia de modelo (`/models`) sin cambiar de herramienta; el contexto está en los documentos, no en el chat.
7. **Modelo fuerte solo para lo difícil** (diseño de arquitectura, bugs que no salen). Lo rutinario va con el modelo gratuito.

## 4. Orden de las capas (no te saltes pasos)
1. Cerebro (core) → 2. Memoria → 3. Voz → 4. Avatar → 5. Control del sistema → 6. Audio → 7. Gestos → 8. Sensores → 9. Móvil.
Razón: si el cerebro no funciona, un avatar bonito no sirve; y cada capa depende de la anterior.

## 5. Estrategia con los tres repos
- Clónalos en `upstream/` (solo lectura).
- Pide al agente un **resumen por repo** en modo Plan: estructura, licencia, módulos reutilizables. Guárdalo en `docs/upstream-notes/<repo>.md`.
- Extrae **una pieza por fase**, reescrita o adaptada con atribución si la licencia lo permite.
- Nunca fusiones los repos completos.

## 6. Reglas de calidad
- Lógica pura separada de la que toca el sistema operativo (así se prueba sin hardware).
- Acciones sobre el sistema pasan por una capa de permisos; el LLM nunca ejecuta comandos arbitrarios.
- Protocolo documentado antes de implementarse (`ARCHITECTURE.md`).
- Sin secretos en git; `.env` fuera del repo.
- Diseño: una sola cosa memorable (el avatar). El resto sobrio, accesible y que respete `prefers-reduced-motion`.

## 7. Definición de "terminado" para cada tarea
Funciona, tiene prueba, `make test` pasa, documentación actualizada (`FUNCTIONS.md`/`ROADMAP.md`), commit hecho.

## 8. Plantillas de prompts
**Inicio de sesión:**
> Lee AGENTS.md, docs/DEVELOPMENT-GUIDE.md y docs/ROADMAP.md. Estamos en la Fase N. En modo Plan, propón los pasos mínimos y espera mi aprobación.

**Estudiar un repo:**
> Lee upstream/<repo>. Escribe docs/upstream-notes/<repo>.md con: licencia, estructura, módulos reutilizables para CORT y riesgos. No modifiques código.

**Arreglar un fallo:**
> Este comando falla con este error: <pegar>. Encuentra la causa, propón el arreglo mínimo y añade una prueba que lo cubra.

**Cierre:**
> Ejecuta make test, actualiza docs/FUNCTIONS.md y ROADMAP.md y sugiere el mensaje de commit.
