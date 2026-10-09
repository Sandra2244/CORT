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
12. La cara pública del prototipo es `README.md`. Al cerrar una fase se actualiza **en el mismo commit** junto con `CREDITS.md` (autores y terceros) y `LICENSE` (año y titulares): si una fila nueva de "qué hace hoy" no está verificada, no va al README.
13. La pila es **Python + React + Ollama, todo en local**, y no se cambia de lenguaje por una sugerencia externa. Las decisiones de plataforma (escritorio, móvil, voz, C++/Java) están medidas y justificadas en `docs/PLATFORM.md`: para alterar una hay que traer un número nuevo de esta máquina, no una opinión.

## Prompt de arranque sugerido
> Lee AGENTS.md, docs/STATUS.md y docs/ROADMAP.md. Implementa la fase que STATUS.md marque como siguiente (hoy, corte `v0.9.0`: **la voz ya vive en el navegador, la red ya tiene llave, lo que se rechaza queda apuntado y CORT ya encadena varios pasos por mensaje con su comprobación** (`audit.py` función 74 + `make rechazos`, `planner.py` función 75), así que lo que avanza es **el lip-sync y las expresiones del cuerpo 3D** (27 y 29, con sus fps medidos), **el cerebro que propone** (hoy ejecuta lo que se le pide y comprueba cada paso; que decida un paso él sola exige su propia comprobación y su forma de decir «eso no», y sigue sin haber herramientas para el LLM —regla 6—) y **convertir la bitácora en aviso**: que CORT diga algo tras varios rechazos seguidos en vez de esperar a que alguien lea el archivo (marco nuevo en el WebSocket ⇒ se documenta antes en docs/ARCHITECTURE.md, regla 5). **Oír la voz con auriculares y probar «hablarle» con un micrófono delante** sigue siendo hardware, no código: medido otra vez con Bluetooth, `wpctl status` no da ningún *Source* en esta máquina. Abrir CORT desde el teléfono físico con `--lan` y su `?token=`, y la **Release** en la web de GitHub (`gh` sin sesión) dependen de ella. La red por `http://` sin TLS y Windows siguen siendo decisiones de Sandra, no tickets). Se trabaja sobre **`main`**, que desde `v0.7.0` es la rama pública y única. Mira `docs/PLATFORM.md` antes de prometer nada. Escribe primero las pruebas, luego el código, ejecuta `make test` y actualiza docs/STATUS.md y README.md al cerrar.