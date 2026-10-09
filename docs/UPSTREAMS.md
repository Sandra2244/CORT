# Qué tomar de cada repositorio

Los repos se clonan en `upstream/` (ignorado por git) **solo para leer y reutilizar ideas**. Revisa la licencia de cada uno antes de copiar código; si es MIT/Apache puedes adaptar con atribución. Si no la tiene, no copies: reescribe la idea.

Las estrellas y las licencias de las tablas de abajo **no son de memoria ni de una captura**: se leyeron el **2026-10-08** en la API de GitHub (`/repos/<dueño>/<repo>`, sin autenticar), y se volverán a leer antes de citar un número en otro documento. Un número de estrellas mal copiado en un README público es exactamente el tipo de afirmación que este proyecto no hace (regla 11 de `AGENTS.md`).

## Lo que ya está dentro del prototipo

| Repo | ★ | Licencia | Estado en CORT |
|---|---|---|---|
| [adewaskar/JARVIS](https://github.com/adewaskar/jarvis) | 417 | **MIT** | **Código copiado y adaptado**: el reactor GLSL, las partículas, la cadena de post-proceso y los efectos de un disparo. La atribución módulo a módulo está en `apps/web/CREDITS.md`. *Nota: cuando se transplantó tenía 12 ★; la diferencia es que el repo creció, no que se midiera mal* |
| [OpenJarvis](https://github.com/open-jarvis/OpenJarvis) | 10 821 | **Apache-2.0** | **Sólo ideas y estructura**, ningún archivo copiado. Si se copia código arrastra la nota de licencia de Apache |
| [jaredrhod/fullstack-agent](https://github.com/jaredrhod/fullstack-agent) | 1 042 | **AGPL-3.0** | **Ninguna línea copiada, a propósito.** Su desglose «memory · voice · face · hands» sí se leyó como mapa de fases. Tomar código AGPL obligaría a relicenciar CORT entero bajo AGPL — y una línea "traducida" a Python cuenta como obra derivada |

## Candidatos con más de 1000 ★ (medición del 2026-10-08)

Filtrados por lo que pidió Sandra: JARVIS / Cortana / Halo / asistente de escritorio.

| Repo | ★ | Licencia | Lenguaje | Último push | Qué tiene que le sirva a CORT | Se puede copiar |
|---|---|---|---|---|---|---|
| [sukeesh/Jarvis](https://github.com/sukeesh/Jarvis) | 3 750 | MIT | Python | 2025-12-01 | Asistente de terminal con comandos modulares: el patrón «una habilidad, un archivo» encaja con `intents.py` + `actions.py` | Sí, con atribución |
| [Priler/jarvis](https://github.com/Priler/jarvis) | 2 972 | sin licencia usable (`NOASSERTION`) | Rust | 2026-02-18 | Pipeline de voz en tiempo real por partes | **No** |
| [isair/jarvis](https://github.com/isair/jarvis) | 1 966 | `NOASSERTION` | Python | 2026-10-05 | Asistente web autoalojado: despliegue y estructura de proyecto | **No** |
| [wzpan/dingdang-robot](https://github.com/wzpan/dingdang-robot) | 1 872 | `NOASSERTION` | Python | 2018-04-13 | Sistema de plugins de voz (inactivo desde 2018) | **No**, y además viejo |
| [kalliope-project/kalliope](https://github.com/kalliope-project/kalliope) | 1 781 | GPL-3.0 | Python | 2023-07-02 | Arquitectura de actores/habilidades para asistentes de voz | **No** (GPL) — sólo inspiración |
| [GauravSingh9356/J.A.R.V.I.S](https://github.com/GauravSingh9356/J.A.R.V.I.S) | 1 399 | MIT | Python | 2025-12-02 | Orquestación sencilla de comandos y TTS | Sí, con atribución |
| [FarazzShaikh/THREE-CustomShaderMaterial](https://github.com/FarazzShaikh/THREE-CustomShaderMaterial) | 1 341 | MIT | TypeScript | 2025-10-12 | Extender los materiales estándar de Three.js con GLSL propio: es la forma ordenada de añadirle más capas al orbe | Sí, con atribución — **pero añade dependencias, y cada dependencia es RAM**: ver advertencia abajo |
| [sdkcarlos/artyom.js](https://github.com/sdkcarlos/artyom.js) | 1 268 | MIT | JavaScript | 2023-01-24 | Control por voz desde el navegador (`SpeechRecognition` del propio Chrome) | Sí, con atribución — **y no sirve todavía**: necesita micrófono, que esta máquina no tiene |
| [swapagarwal/JARVIS-on-Messenger](https://github.com/swapagarwal/JARVIS-on-Messenger) | 1 391 | MIT | Python | 2024-04-24 | Patrón mínimo «intención → respuesta», muy parecido a `intents.py` | Sí, con atribución |
| [Kochava-Studios/witsy](https://github.com/Kochava-Studios/witsy) | 2 038 | AGPL-3.0 | TypeScript | 2026-04-23 | Cliente de escritorio con Ollama: referencia de UX (listas, modelos, perfiles) | **No** (AGPL) |
| [szczyglis-dev/py-gpt](https://github.com/szczyglis-dev/py-gpt) | 1 985 | licencia propia restrictiva (`NOASSERTION`) | Python | 2026-10-06 | Asistente de escritorio con memoria y voz: referencia de alcance | **No** |

### Descartado por sospechoso

[jev-chat/jev-chat-jarvis](https://github.com/jev-chat/jev-chat-jarvis) anuncia **7 483 ★** con **10 personas siguiéndolo** y fue creado el **2026-09-21**. Esos tres números juntos son la firma de una granja de estrellas, no de un proyecto adoptado. No se trasplanta nada de ahí, y se anota para que nadie pierda una tarde leyéndolo.

## Qué se transplantará, en orden de coste

Nada de esto está hecho todavía; es la lista de lo que sigue, con su criterio para que no se cuele humo:

1. **Modularidad de habilidades** (sukeesh/Jarvis, MIT). CORT ya tiene `intents.py` + `actions.py`; lo que se toma es la *convención* de una habilidad por archivo con su prueba, no su código. Coste: cero RAM.
2. **Capas extra en el orbe** (THREE-CustomShaderMaterial, MIT). Antes de añadir la librería hay que medirla: el reactor actual va a **18 fps sin GPU** y esa librería trae passes adicionales. Si el recuento de cuadros baja, se implementa el efecto concreto en el shader que ya existe y no se añade la dependencia. **Esta es la regla que manda sobre el trasplante.**
3. **Voz por navegador** (artyom.js, MIT). Bloqueada por hardware, no por código: `arecord -l` no lista ningún dispositivo de captura en esta máquina. Se deja escrito el enlace para cuando haya micrófono.

## Advertencias antes de trasplantar

- **Cualquier pipeline de voz local** (kalliope, dingdang, py-gpt, witsy) y cualquier cadena Ollama con modelos ≥3 B: no caben. Esta máquina tiene **1,8 GiB** y descarta por tamaño los modelos de más de 700 MiB antes de intentar cargarlos — uno de 2,6 GB la congeló.
- **NextChat y LibreChat** (88 835 ★ y 45 418 ★, MIT) aparecen en toda búsqueda de «asistente», pero son servidores Node monolíticos multi-proveedor: no tienen nada que ver con un orbe de escritorio local y no se adoptan como base.
- **Sin GPU**: los shaders que se trasplanten tienen que medir su coste en cuadros por segundo en esta máquina, no en la del autor del repo.

## Cómo clonar
1. Edita `scripts/upstreams.txt` con las URLs **exactas** (verificadas contra la API, como las tablas de arriba).
2. `bash scripts/clone-upstreams.sh`
3. Pídele a tu agente: "lee `upstream/<repo>` y resume qué módulos son reutilizables para CORT según docs/UPSTREAMS.md".

## Regla
No fusiones repos enteros. Extrae piezas pequeñas, una por fase, con prueba. Y si la licencia es AGPL, GPL o no aparece, **la pieza se reescribe o no se hace**: una sola línea ajena bajo esas licencias cambia la licencia de todo CORT.
