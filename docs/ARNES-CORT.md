# El Arnés de CORT

> La capa que une la voz con las herramientas, y el tablero donde se ve si cada
> pieza está sana. Este documento explica **la arquitectura que CORT tiene hoy**
> —no la que nos gustaría tener— y deja por escrito lo que la hoja **Arnés**
> enseña, de dónde lo lee y qué no promete.

CORT es un JARVIS de escritorio y de bolsillo con la voz y la presencia de
Cortana: un orbe que escucha, un puente con Android, un núcleo en el portátil y
un diccionario de órdenes que se ejecutan sin pedir permiso a la nube. El arnés
es lo que ata esas piezas entre sí; la hoja `⌬ Arnés` es donde eso se puede
mirar.

---

## 1 · Las seis capas

| Capa | Qué es | Dónde vive |
|---|---|---|
| **Puerta** | Por donde se entra: voz, avisos, burbuja, segundo plano, pantallas | `apps/apk/.../MainActivity.java`, `ui/js/hud.js` |
| **Puente** | Los métodos que Android le presta a la cara (texto JSON, nunca objetos) | `apps/apk/.../CortNative.java` |
| **Razón** | El diccionario de órdenes, el cerebro del teléfono y el del portátil | `backend/app/`, `ui/js/diccionario.js`, `Mente.java`, `Cerebro.java` |
| **Herramientas** | Lo que CORT sabe hacer: 91 intenciones y 736 frases, en cuatro capas | `ui/js/diccionario.js` |
| **Memoria y sesiones** | Lo que recuerda el teléfono, el muro del núcleo y la conversación local | `Recuerdos.java`, `ui/js/pantallas.js`, `backend/app/memoria.py` |
| **Arnés y salud** | El tablero que lee las cinco capas y dice cuál contesta y cuál no | `ui/js/arnes.js` |

La regla que sostiene todo: **cada capa habla texto**. El puente devuelve JSON,
el núcleo devuelve JSON, la cara pinta HTML. Ninguna capa inventa un objeto que
la otra no pueda contestar, y ninguna se cae porque un campo venga raro.

```
        voz / texto / toque
                │
        ┌───────▼────────┐
        │     PUERTA     │  asistente, auricular, baldosín, burbuja, atajos
        └───────┬────────┘
                │
        ┌───────▼────────┐        ┌──────────────────┐
        │     PUENTE     │◄──────►│  Android (APK)   │
        │  CortNative    │        │  permisos, voz,  │
        └───────┬────────┘        │  música, cámara  │
                │                 └──────────────────┘
        ┌───────▼────────┐        ┌──────────────────┐
        │     RAZÓN      │◄──────►│  Núcleo (PC)     │
        │ diccionario +  │  HTTP  │  FastAPI + Ollama│
        │ cerebro local  │        │  /api/*          │
        └───────┬────────┘        └──────────────────┘
                │
        ┌───────▼────────┐
        │  HERRAMIENTAS  │  91 intenciones · 736 frases · 4 capas
        └───────┬────────┘
                │
        ┌───────▼────────┐
        │    MEMORIA     │  hechos, recuerdos, habilidades, Charla
        └───────┬────────┘
                │
        ┌───────▼────────┐
        │     ARNÉS      │  lee, cuenta y enciende luces. No ejecuta.
        └────────────────┘
```

---

## 2 · Qué enseña la hoja Arnés

Se abre desde el cajón (`☰ ▸ Arnés`) y se repinta **cada vez que se entra**.
Primero pinta lo que el aparato ya sabe de sí mismo; después, cuando el portátil
contesta —o cuando se agota el tope de 1,8 s—, pinta lo del núcleo. Si el
portátil no contesta, la fila lo dice; no se queda esperando ni rellena con un
cero bonito.

Son seis cajas:

1. **Nodos** — este aparato (perfil y número de métodos del puente), sus seis
   servicios (`asistente`, `avisos`, `cortina`, `reconocedor`, `llamadas`,
   `agenda`) y el portátil, con su cerebro y su `system` real.
2. **Herramientas** — las 91 intenciones y 736 frases que salen del
   diccionario generado, sus cuatro capas (mando 41, razón 26, casa 13, nube 11)
   y un ejemplo por capa. Al tocar un ejemplo se manda su frase por
   `cort:orden`, igual que si se dijera en voz alta, y se vuelve al orbe.
3. **Sesiones** — los mensajes de `localStorage['cort-charla']` (los últimos 40),
   la hora del último y lo que el núcleo guardó en `/api/history`. Dice en
   palabras que **no hay varias sesiones a la vez**.
4. **Memoria** — `memoria('{"que":"estado"}')`: hechos, recuerdos, habilidades,
   si hay portátil y su dirección, y si está sincronizando. Debajo, el muro del
   núcleo (`/api/memories`).
5. **Salud** — siete luces: puente, núcleo, micrófono, cámara, memoria del
   teléfono, sesión local y música. Verde es «contesta», ámbar es «existe pero
   falta algo», apagada es «este aparato no lo tiene».
6. **Puerta** — reconocedor, avisos, segundo plano, burbuja, número de hojas y
   fabricante. Sólo se enciende lo que `capacidades()` y `bgStatus()` dicen.

Y un pie que recuerda la hora de la lectura y la regla de la casa: **el arnés
enseña; no ejecuta nada por su cuenta**. Las únicas dos acciones que tiene son
las que ya existían: mandar una frase (como la voz) y abrir el Centro.

---

## 3 · De dónde lee (y qué pasa si no contesta)

| Fuente | Qué entrega | Si falla |
|---|---|---|
| `CortNative.capacidades()` | perfil y los seis servicios | la caja dice «APK sin capacidades»; no se enciende nada por suposición |
| `CortNative.memoria('{"que":"estado"}')` | cuentas y portátil | «El puente no entregó el estado de la memoria» |
| `CortNative.bgStatus()` | fondo, micrófono, burbuja, fabricante | la fila de Puerta se queda apagada |
| `CortNative.musicaEstado()` | si suena y qué pista | «en silencio» |
| `CortNative.hasPermission('camara')` | permiso real de cámara | «no comprobable sin puente» |
| `localStorage['cort-charla']` | la conversación local | 0 mensajes, sin inventar |
| `/api/port` | ¿hay núcleo? | la caja del portátil dice «sin respuesta» |
| `/api/status` | cerebro y `system` | la fila se queda sin datos del PC |
| `/api/history?n=40` | respuestas guardadas | 0, y se dice |
| `/api/memories` | el muro del núcleo | 0, y se dice |

Ninguna llamada al puente puede tumbar la hoja: todas pasan por `intenta()` y
por `objeto()`. Un JSON roto se convierte en `{}`, no en una excepción.

---

## 4 · Lo que el Arnés NO promete

Es tan importante como lo anterior. CORT **no** tiene hoy:

- **Varias sesiones simultáneas** ni pestañas de conversación: hay una Charla
  local y un historial del núcleo.
- **Agentes autónomos en segundo plano** que se reparten tareas: las
  automatizaciones son reglas «cuando X, entonces Y», y se ejecutan cuando pasa
  X, no cuando a un agente le parece.
- **Nodos remotos** ni una malla de aparatos: hay este aparato y, si está en la
  misma red, el portátil con su núcleo.
- **Ollama dentro del APK**: Ollama es un servidor y no cabe en un teléfono. El
  APK lleva su cliente (`Ollama.java`) y el modelo vive en el portátil; el
  cerebro propio del teléfono es el reconocedor y las reglas de `Cerebro.java`.
- **Permisos nuevos**: el Arnés no pide ni uno. Lee los que ya existen y, si
  falta uno, lo dice con la ruta a Ajustes.

Copiar de OpenClaw, Hermes Agent u OpenJarvis lo que sirve —el chat con acciones
por mensaje, el arnés como capa visible, la separación entre puerta, razón y
herramientas— no es prometer que CORT sea esos proyectos. Es ordenar lo que
CORT ya hace para que se pueda ver y arreglar.

---

## 5 · Cómo se comprueba

Tres instrumentos, ninguno necesita el teléfono:

1. **`ui/sonda-carita.html`** monta la cara real con un puente de mentira y mide
   la hoja: seis cajas, 91/736, capas 41/26/13/11, memoria y salud, la sesión
   local y que un ejemplo mande su frase. Su sección `5d` espera a que el núcleo
   conteste antes de medir; no duerme un rato fijo.
2. **`scripts/prueba-costura.py` § [36]** cruza el módulo con la hoja, el CSS y
   la sonda: que el Arnés lea el diccionario y no una copia, que pinte antes de
   esperar al PC, que su hoja tenga `display:flex`, que no ejecute nada por su
   cuenta y que la sonda lo mida de verdad.
3. **El taller de mutaciones** de la ronda: quitar una fuente, cambiar el orden
   de las pinturas o borrar la regla CSS tiene que poner rojo algún sector. Un
   verde que no se puede romper no es una prueba.

---

## 6 · Por qué esta arquitectura y no otra

La dueña lo pidió así: «necesito agregarle arneses basados en OpenClaw y Hermes
Agent, mejorar y rediseñar la arquitectura y visión de CORT, que es un JARVIS
combinado con Cortana de Halo». La respuesta no fue añadir un chat nuevo ni un
menú más, sino **poner nombre a las capas que ya existían** y darles un tablero:

- La **puerta** ya estaba en `MainActivity` y `hud.js`.
- El **puente** ya estaba en `CortNative`, con su contrato 2.1.
- La **razón** ya estaba en el diccionario y en `Mente`/`Cerebro`.
- Las **herramientas** ya estaban contadas en `TOTALES`.
- La **memoria** ya estaba en `Recuerdos` y en la Charla.
- Faltaba el **arnés**: alguien que las leyera a la vez y dijera la verdad.

Eso es lo que se añadió en esta ronda. Nada de lo anterior cambió de sitio, y
ninguna función nueva pide un permiso nuevo.

---

## 7 · Lo que viene después (y no está en esta ronda)

- Sesiones de verdad (varias conversaciones con nombre) si la dueña las pide:
  hoy la Charla guarda una sola, y el Arnés lo dice en vez de fingir pestañas.
- Un registro de lo que hizo cada herramienta (quién, cuándo, con qué
  resultado), para que la caja de Salud pueda enseñar el último fallo y no sólo
  el estado.
- Nodos: el día que haya más de un aparato con CORT, el Arnés tendrá una caja
  más. Hoy no la tiene porque no hay nada que enseñar.

Mientras tanto, la promesa es la de siempre: **lo que se enciende, contesta; lo
que no, se dice**.
