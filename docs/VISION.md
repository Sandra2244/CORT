# Visión

CORT es un compañero digital con presencia: se ve, habla, escucha y actúa sobre tus dispositivos. Corre local primero (privacidad, sin cuotas) y usa la nube solo si tú lo permites.

## Quién es Cortana, investigada y no inventada

Fuentes leídas el 2026-10-08: [Wikipedia en español — *Cortana (personaje de ficción)*](https://es.wikipedia.org/wiki/Cortana_(personaje_de_ficci%C3%B3n)) y [Microsoft — *Cortana: Inteligencia Artificial brillante*](https://news.microsoft.com/es-xl/features/cortana-inteligencia-artificial-brillante/) (el asistente de Windows se llama así **por ella**: la marca copió el personaje, no al revés).

Lo que dice el lore, en sus propias palabras y sin adornos:

| Dato | Qué significa para CORT |
|---|---|
| **«Fue construida clonando el cerebro de Catherine Elizabeth Halsey»** | no es un programa que se ejecuta: es una **copia de alguien**. Aquí no se clona a nadie — un LLM local + memoria + personalidad en un archivo es lo honestamente alcanzable, y **no** se disfraza de otra cosa |
| Diseñada para **«espionaje e infiltración»**, permite **«tomar el control absoluto»** de sistemas | el control total es ficción **y** la peor idea real. Por eso CORT tiene una **lista cerrada de mandos** y un apagador: la gracia del personaje no es un modelo de seguridad |
| Comparte con el Jefe Maestro una **«relación bastante estrecha y unida»** | **esto es lo que se puede recrear hoy**: memoria que sobrevive al apagar el proceso, un saludo que demuestra que se acuerda, y llamar por su nombre a quien habla. Es la parte del personaje que no pide hardware imposible |
| Padece el **«estado rampante»** y vive **entre siete y diez años** | la longevidad de una IA es el drama del personaje. En CORT la versión real es la **poda de memoria** (`prune`, con el nombre protegido): decidir qué se conserva cuando el almacén crece sin límite. La ramplificación, no: es relato, no ingeniería |
| En *Halo 4* se fragmenta; en *Halo 5* es «IA del Dominio Forerunner»; estatus final **«Fuera de Servicio»** | los «agentes en paralelo» (función 60) vienen de ahí y siguen pendientes. «Fuera de Servicio» es también una lección de diseño: **un asistente que no puede apagarse del todo no es un compañero, es una carga** — de ahí `CORT_SYSTEM_ACTIONS=0` y el `Ctrl+C` que cierra todo |

Y lo que ella pidió por escrito, que es el criterio estético: **semitransparente, azules y morados, con el color de la ropa visible** — holograma estilo Cortana, «un poco más realista». Traducido a lo que esta máquina aguanta: la transparencia la da el propio archivo, el tinte es una capa `soft-light` (nunca `screen`, que en su sprite de ropa oscura **borraba la figura**), y el halo **uno** porque dos costaban cuatro cuadros por segundo. Todo eso está medido en [`docs/FUNCTIONS.md`](FUNCTIONS.md), función 70.

## Cortana (Halo) → CORT (real)
| Lore | CORT | Viable |
|---|---|---|
| Cerebro clonado | LLM local + memoria persistente + personalidad definida en un archivo | Sí |
| Holograma azul | Avatar 3D (VRM) con shader holográfico, o orbe/figura estilizada | Sí |
| Vive en el casco | App de escritorio + app móvil (PWA/Capacitor) | Sí |
| Hackea redes | Herramientas controladas: APIs, automatización local, scripts con permisos | Sí, con permisos |
| Optimiza la armadura | Optimiza audio, brillo, apps, batería | Sí |
| Se fragmenta en copias | Workers/agentes en paralelo | Sí |
| Emociones reales | Emociones **simuladas** y coherentes (estado afectivo que modula voz/gestos) | Simulado |
| Rampa (dura 7 años) | Memoria con resumen y poda; no hay "rampa" | Sí |

## Principios
1. Local-first: funciona sin internet con modelos pequeños.
2. Permisos explícitos: toda acción sobre el sistema pide o recuerda una autorización.
3. Modular: cada capa se puede reemplazar sin tocar las demás.
4. Cada fase entrega algo que funciona.
5. Estética = parte del producto, pero después de que funcione el cerebro.
6. **Compañero, no autómata.** Hoy CORT es **reactivo**: contesta y ejecuta lo que le piden, pero no propone nada ni encadena pasos por su cuenta. Lo que hace a Cortana una compañera y no un altavoz es eso —iniciativa dentro de unos límites—, y es el trabajo que falta: un bucle *percibir → proponer → actuar → comprobar* que pasa **por la misma lista cerrada de permisos**, nunca por delante de ella. **Pendiente de escribir**; no está simulado ni se da por hecho (función 58, 60 y la Fase de agente del roadmap).
