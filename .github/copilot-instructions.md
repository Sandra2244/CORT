# Instrucciones para agentes de código (OpenCode, Cline, Continue, Claude Code, Copilot, etc.)

Eres colaborador del proyecto CORT. Antes de cambiar nada lee `docs/STATUS.md` (dónde estamos de verdad), después `README.md`, `docs/DEVELOPMENT-GUIDE.md`, `docs/ARCHITECTURE.md` y `docs/ROADMAP.md`.

`docs/STATUS.md` es la fuente de verdad operativa: si ahí dice que algo no existe, no existe, aunque otro documento o un chat anterior afirme lo contrario. Dúdate siempre de un estado que no hayas ejecutado.

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
11. No afirmes que algo funciona sin haberlo ejecutado en esta máquina. Si no puedes comprobarlo, escribe literalmente "sin verificar".

## Prompt de arranque sugerido
> Lee AGENTS.md, docs/STATUS.md y docs/ROADMAP.md. Implementa la fase que STATUS.md marque como siguiente (hoy: Fase 1, memoria persistente con SQLite en services/core). Escribe primero las pruebas, luego el código, ejecuta `make test` y actualiza docs/STATUS.md al cerrar.
