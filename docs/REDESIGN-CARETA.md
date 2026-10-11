# CARETA v2 — la pantalla entera es el HUD

Plan de rediseño de la **cara** decidido el 2026-10-11, en la madrugada, tras
el veredicto de la dueña sobre la bandeja N13: «le faltan muchas cosas… mira lo
futurista y profesional de las referencias y rediseña desde cero». Se acepta el
diagnóstico y se acota el alcance con honestidad:

> **«Desde cero» reconstruye la CARETA, no el motor.** El núcleo probado —331
> pruebas del core, protocolo WebSocket, reactor VRM, fases N9, ventanas N1,
> menú N4— se queda: es lo único que funciona de verdad en las referencias que
> son proyectos reales (TechEnClair con su demo en vivo, `adewaskar/jarvis`). Lo
> que se rehace es la cabina entera: cómo se ve CORT antes de que nadie escriba
> una palabra.

Ley de licencias intacta (AGENTS.md regla 9, y `docs/TRANSPLANTE.md`): de
TechEnClair **cero líneas** —su licencia no es estándar—; de jaredrhod, ideas
(AGPL); de adewaskar, puertes con crédito (MIT). Aquí no viaja código externo:
viaja **gramática visual reescrita**.

## La regla madre nueva

R1 decía: «en reposo, tres cosas — el reactor, el reloj y la esquina». CARETA
v2 la sustituye:

> **En reposo no hay objetos sueltos: hay un marco.** La pantalla entera es el
> HUD — barra de mando arriba, riel de secciones a la izquierda, corchetes en
> las cuatro esquinas— y el reactor dentro. El contenido (ventanas, bandeja,
> subtítulo) sigue invocándose y despidiéndose como hasta ahora.

Es el gesto que repiten todas las referencias densas (`b2-90e21d`, `fd38b8`,
la demo en vivo de TechEnClair): la cabina no es un panel flotante, es un
**carné con bordes**. Un marco fijo además resuelve quejas concretas: el reloj
agarrable de N1 era una monada sin función una vez que la bandeja tenía hora
propia, y el lanzador del menú vivía arriba-centro, lejos del pulgar.

## Fases

| fase | qué | estado |
|------|-----|--------|
| **A — cockpit** | barra de mando arriba (marca · punto de fase · `hh:mm:ss` gigante · fecha · chip de red), riel izquierdo con los glifos de las cinco secciones + `◈` menú, carcasa de corchetes en las esquinas, telón de arranque atado a la conexión real | **hecha y medida esta sesión** |
| B — panel de conversación al canto | la bandeja deja de ser cajón inferior y se desliza desde el borde derecho, como `b2-90e21d`; el registro gana burbujeado lateral | pendiente |
| C — telemetría real | CPU/RAM/red en la barra o el riel. **Primero** `psutil`-free (stdlib `/proc`) en el core, y lo que mande por WebSocket se documenta en ARCHITECTURE antes (regla 5). Sin telemetría falsa: un número que no viene de `/proc` no entra | pendiente |
| D — partículas y blooms | el orbe respira con capas de partículas estilo `adewaskar` (MIT, puerte con crédito) — sólo si R7 fps lo aguanta **en el A16**, no aquí | pendiente |
| E — onda de voz | la fase `habla` dibuja la envolvente real del TTS (el core ya sabe cuándo habla); sin audio analizado no hay onda, y sin onda no se pinta ninguna | pendiente |

## Lo que se retira y por qué se dice

- **El reloj flotante agarrable (N1)** desaparece con la fase A. Su función —
  ver la hora sin abrir nada— la cubre mejor una barra fija con `hh:mm:ss` que
  un chisme que había que mover para no tapar el reactor. El arrastre sigue
  vivo donde sí hace falta: ventanas de vidrio y bandeja.
- **`.esquina` (el punto de entrada de R1)** se queda: con la barra arriba, el
  acceso a la bandeja en la esquina inferior sigue siendo el sitio del pulgar.
- El temporizador L4 baja de `top: 16px` a `top: 66px`: la franja superior ya
  es de la barra.

## Honestidades (reglas 10 y 11)

- El **telón de arranque no finge progreso**: no hay barra que suba ni
  checklist de BIOS (eso se rechazó al analizar `b1-aira-sigan`). Hay anillos
  girando mientras el WebSocket abre, y se levanta con el hecho real
  `snapshot.online` — o a los 2,5 s si el core no está, mostrando la cabina con
  su chip rojo «sin core». Un emblema secuestrando la pantalla sería peor que
  un arranque feo.
- Nada de la barra es decorativo: la fase la resuelve `faseDe` (N9), la hora es
  la de la máquina formateada por el módulo probado `cort/hora.ts`, y el chip
  de red es el estado del cable.
- **Sin verificar hasta que la dueña lo mire**: la sensación final en pantalla
  completa y en el A16. Las capturas de esta máquina prueban que existe y se
  mueve, no que sea «lo futurista que ella vio en los videos».

## Cómo se ejecuta

Una fase por sesión, commits `feat:` sueltos sobre `cort-nucleo`, con su
verificación (pruebas puras + `tsc` + build + humo en navegador contra el core
real de ella) y su fila en `docs/FUNCTIONS.md`. Fase A: funciones 86 de
FUNCTIONS; los componentes nuevos son `ui/Barra.tsx`, `ui/Riel.tsx` y
`ui/Arranque.tsx` sobre la pila pura que ya existía — cero cambios de
protocolo, cero dependencias nuevas.
