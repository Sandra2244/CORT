# Qué copiloto usar sin quedarte sin cuota

> Nota: estas herramientas cambian rápido. Verifica precios y límites en sus sitios oficiales antes de depender de ellos.

## Idea clave
Separa **la herramienta** (el editor/agente) del **modelo** (quien piensa). Si la herramienta es abierta y acepta cualquier modelo, nunca te quedas "sin copiloto": cambias de modelo cuando se acaba la cuota.

## Recomendación en 3 niveles
**1. Modelo local (cuota infinita).** Instala Ollama y descarga un modelo de código (por ejemplo `qwen2.5-coder`; elige el tamaño según tu RAM/GPU). Más lento y menos capaz, pero siempre disponible. Es el respaldo.

**2. Modelos gratuitos en la nube.** Varios proveedores (Google Gemini API, Groq, OpenRouter con modelos marcados como gratis, etc.) ofrecen capas gratuitas con límites. Cambian a menudo; revisa sus páginas.

**3. Agente/editor abierto que conecta todo lo anterior.** Opciones:
- **OpenCode**: agente en terminal, open source, elige proveedor y modelo. Funciona en Codespaces porque es terminal.
- **Cline** o **Continue**: extensiones de VS Code/VSCodium con modelo configurable. Continue es la opción más natural en VSCodium.
- **Claude Code / Copilot**: potentes, pero con cuota; úsalos para tareas difíciles (arquitectura, bugs raros), no para todo.

## Sobre OmniRoute
No pude verificar su documentación desde mi entorno, así que no te voy a inventar cómo se configura. Por lo que se entiende de su propósito, es un enrutador/pasarela que junta varios proveedores de IA detrás de una sola dirección compatible con la API de OpenAI, para saltar de uno a otro cuando uno se agota. Si lo usas: instálalo según su README, anota la URL local que expone, y en OpenCode/Continue/Cline configúrala como proveedor "OpenAI-compatible" con esa URL. Si algo falla, pega aquí el mensaje de error y lo resolvemos.

## Flujo recomendado para este proyecto
1. Abre la carpeta CORT en VSCodium o Codespaces.
2. Instala Continue (o usa OpenCode en la terminal).
3. Configura un modelo principal gratuito en la nube y Ollama como respaldo.
4. Cada sesión empieza con: *"Lee AGENTS.md y docs/ROADMAP.md. Trabaja solo en la fase X."*
5. Al terminar: `make test` y commit pequeño. Así cualquier otro agente retoma exactamente donde quedó, porque el contexto vive en los documentos, no en el chat.

## Por qué esto te protege
Todo el conocimiento del proyecto está en `docs/` y `AGENTS.md`. Si cambias de copiloto, solo le dices que lea esos archivos.
