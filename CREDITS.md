# Créditos y licencias de CORT

## Creadores

**Sandra Lopez** y **Askher Vargas**.

CORT es un proyecto independiente, desarrollado como prototipo de asistente personal holográfico *local-first*.

## Licencia del proyecto

**MIT** — © 2026 Sandra Lopez, Askher Vargas. Texto completo en [`LICENSE`](LICENSE).

La licencia MIT de CORT cubre **el código de este repositorio**. No reclama nada sobre el trabajo ajeno en el que se apoya, y no lo sublicencia como si fuera propio: cada pieza conserva la suya, que está abajo.

## Lo que viene de fuera

| Origen | Licencia | Estado en CORT |
|---|---|---|
| [adewaskar/JARVIS](https://github.com/adewaskar/jarvis) | **MIT** | **Código copiado y adaptado**: el reactor GLSL, las partículas, la cadena de post-proceso, la capa de efectos de un solo disparo, el filtro 1€ de suavizado (`apps/web/src/lib/oneEuro.ts`) y el patrón de arrastre de paneles (`apps/web/src/cort/arrastre.ts`, al que CORT añade los topes). La atribución es obligación de la licencia, no cortesía: está documentada módulo a módulo en [`apps/web/CREDITS.md`](apps/web/CREDITS.md) |
| [OpenJarvis](https://github.com/open-jarvis/OpenJarvis) | **Apache-2.0** | **Sólo ideas y estructura**. Ningún archivo copiado. Si se copia código, se arrastra la nota de licencia de Apache |
| `fullstack-agent` (jaredrhod) | **AGPL-3.0** | **Ninguna línea copiada, a propósito.** Tomar código AGPL obligaría a publicar CORT bajo AGPL; de ese repo se leyeron ideas de arquitectura y nada más |
| Rama `scaffold/fastapi-ollama-frontend` de este repo | propia | La memoria SQLite, **reescrita**: ruta de la base de datos inyectable, `created_at`, deduplicación, búsqueda por raíces de 4 letras, poda con el nombre protegido |
| [FastAPI](https://fastapi.tiangolo.com) · [uvicorn](https://www.uvicorn.org) · [React](https://react.dev) · [Vite](https://vite.dev) · [Three.js](https://threejs.org) · [Ollama](https://ollama.com) | MIT / Apache-2.0 / ISC | Dependencias de terceros por sus propios términos. No son de CORT y no se distribuyen aquí |
| [@pixiv/three-vrm](https://github.com/pixiv/three-vrm) | **MIT** | **Dependencia** (`@pixiv/three-vrm@3.5.5`), no código copiado: es el cargador del formato VRM que usa `apps/web/src/scene/Vrm.tsx` para proyectar el cuerpo 3D. 2206 ★ en GitHub, leídas en la API el 2026-10-08. Se elige sobre escribir un lector propio porque el formato tiene esqueleto humano, materiales y normalización 0.x/1.x, y eso es trabajo de quien mantiene el estándar. **El shader holográfico que lo veste es de CORT**, escrito aquí |
| **APIs de voz del navegador** (`speechSynthesis`, `SpeechRecognition`) | las del navegador — W3C Web Speech, implementada por Chrome/Edge/Firefox | **Ningún código ni modelo de terceros entra en CORT**: `apps/web/src/ui/Voz.tsx` usa las voces que ya están instaladas en el sistema y el reconocimiento que ya trae el navegador. Por eso la voz no añade ni un byte al `node_modules` ni RAM al core, y por eso **el mismo archivo corre en el portátil y en el Android**. CORT no redistribuye voces: quien escucha es la voz del propio sistema de la usuaria. **El costo va dicho en la interfaz y en `README.md`**: en Chrome y Edge el reconocimiento lo hace un servicio en línea, así que *escuchar* manda audio fuera de la máquina; *hablar* es local |
| **La voz la escribió el colaborador** — **Askher Vargas** | autoría, no licencia ajena | `apps/web/src/ui/Voz.tsx` y su montaje en el cabezal llegaron de su rama y de su copia local, donde ya funcionaba y se oía (video de la dueña del proyecto, 2026-10-09). Entra a `main` en el commit `d5991d1` con su crédito delante. `INSTALAR-WINDOWS.txt` es su instructivo de arranque en un PC de 8 GB con `llama3.2:3b` — el primero que documenta CORT corriendo fuera de este portátil de 1,8 GiB |
| **Los `.vrm` de la usuaria** (`avatar CORT …`) | **la de cada modelo; sin verificar** | **No están en este repositorio ni se distribuyen con él.** Viven en su carpeta (`services/core/data/atuendos/`, ignorada por `data/`) y el core sólo los sirve si ella misma escribe `CORT_AVATAR_DIR`. Antes de publicar ningún modelo hay que leer la licencia del archivo original: los VRM suelen venir de VRoid Studio o de un creador concreto, y «es gratuito» no es «se puede redistribuir» |
| **Los iconos de la PWA** (`apps/web/public/icons/`) | **MIT, propia** | Dibujados con código en este repo (PIL: un anillo con el `#3fd8ff` y el `#8f5cff` de `palette.ts` sobre el `#02040c` de la interfaz). **No salen de ningún pack de iconos ni de un juego**: ni un asset de Halo, ni una fuente con licencia aparte |
| **"Proyecto Jarvis — Guía de inicio" (@Xvirus, 2026-10-07)** | documento sin licencia explícita | **Sólo lectura de ideas, cero líneas copiadas** (la guía no trae código: es una tabla de tecnologías y unos pasos). Sirvió para confirmar la pila —Python + React + Ollama en local— y para escribir [`docs/PLATFORM.md`](docs/PLATFORM.md), que es donde esa guía choca con lo que esta máquina mide: sin micrófono, sin salida de audio, sin `javac` y con 263 MB libres. Sus sugerencias de Electron y Capacitor quedan anotadas como intentos medibles, no como features |
| **Open-Meteo** (`api.open-meteo.com`, `geocoding-api.open-meteo.com`) | servicio externo de datos, no código | **Se consulta, no se copia.** `cort_core/weather.py` es código propio escrito contra su API pública (sin clave); en el repositorio no entra ni un dato meteorológico ni un archivo suyo. Sólo se llama cuando la usuaria escribe `CORT_CITY` en su `.env`. **Sus condiciones de uso exactas no se han vuelto a leer hoy: sin verificar** — la atribución que piden se hace aquí, en esta tabla |
| **Los videos de referencia de interfaz** (`Referencias IA CORT`, guardados por la dueña del proyecto: clips de `@sued.tiago`, `@techenclear`, `@iacontuki` y un Jarvis de terceros) | **material audiovisual ajeno, sin licencia de reutilización** | **Analizados, no copiados.** Se miraron fotograma a fotograma (hojas de contacto de seis tomas por video) para extraer **seis patrones de distribución** —el reactor es la pantalla; los paneles son hilos, no cajas; uno se abre y los demás se apartan; con el gesto la interfaz desaparece; la entrada es una línea; se llega con tres manos— y están escritos en [`docs/REFERENCIAS.md`](docs/REFERENCIAS.md). **En el repositorio no entra ni un fotograma, ni un clip, ni un asset, ni una línea de código de ahí**, y los videos tampoco: son de su autor y de su plataforma. Lo que se copió es **distribución de paneles**, que no es expresión protegida; el look, el shader y el CSS son de CORT |
| **Cortana**, Halo y Microsoft | — | **Inspiración estética y de concepto nada más.** CORT no está afiliado, patrocinado ni autorizado por Microsoft. El nombre, la paleta y el holograma son un homenaje; los assets concretos son todos generados en este repo (shader GLSL y CSS), no extraídos de ningún juego |

## Cómo se mantiene esto al día

Cuando una fase nueva copia o adapta código ajeno, en el mismo commit:

1. se añade o actualiza la fila de esta tabla, con licencia y enlace;
2. si es código copiado, se documenta el origen y las adaptaciones en el `CREDITS.md` del módulo (como hace `apps/web/CREDITS.md`);
3. y si la licencia **no** permite copiar (AGPL, sin licencia, restrictiva), se anota la decisión de **no** tomarlo, que es tan importante como el crédito.

Esto no es trámite: una sola línea AGPL en el repositorio cambia la licencia de todo CORT.
