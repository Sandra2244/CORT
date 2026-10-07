# Instrucciones para agentes de código (OpenCode, Cline, Continue, Claude Code, Copilot, etc.)

Eres colaborador del proyecto CORT. Antes de cambiar nada lee `README.md`, `docs/DEVELOPMENT-GUIDE.md`, `docs/ARCHITECTURE.md` y `docs/ROADMAP.md`.

## Reglas
1. Trabaja **una fase del ROADMAP a la vez**. No adelantes fases.
2. Cambios pequeños: un objetivo por commit, mensaje en formato `feat|fix|docs|test: descripción`.
3. Toda lógica nueva lleva prueba en `services/core/tests` (o la carpeta equivalente). Ejecuta `make test` antes de dar algo por terminado.
4. No añadas dependencias sin justificarlas en el mensaje del commit. Prefiere la biblioteca estándar.
5. Todo cambio al protocolo WebSocket se documenta primero en `docs/ARCHITECTURE.md`.
6. Acciones sobre el sistema (volumen, apps, archivos, mensajes) deben pasar por una capa de permisos; nunca ejecutes comandos arbitrarios del usuario o del LLM.
7. Nunca subas `.env`, claves ni modelos pesados.
8. Código en inglés, documentación y textos de interfaz en español.
9. Los repos de `upstream/` son de solo lectura: se estudian, se respeta su licencia y se reescribe lo que no tenga licencia clara.
10. Si algo es inviable o depende del sistema operativo, dilo y actualiza `docs/FUNCTIONS.md` en lugar de simularlo.

## Prompt de arranque sugerido
> Lee AGENTS.md y docs/ROADMAP.md. Implementa la Fase 1 (memoria persistente con SQLite en services/core). Escribe primero las pruebas, luego el código, ejecuta `make test` y resume qué cambió.
