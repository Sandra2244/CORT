# CEREBRO-MAESTRO · el plan para que CORT deje de ser una lista de comandos

> Documento de **análisis y arquitectura**, no de código. Nace de la ronda 2.8.0
> (`v0.2.36-demo`, 2026-10-23) y de la lista que devolvió la dueña: «todavía no
> descarga los modelos», «falta orden y bugs de botones», «el reproductor funciona
> pero que se parezca más a Lark», «le digo *pausa* y no lo hace», «que se conecte
> con el cerebro», «que se detecte como aplicación de asistencia», «que trabaje como
> núcleo y se conecte a todo», «la burbuja no cambia de color con los atuendos y yo
> quiero la de la 1.1.4».
>
> **Cómo leer esto:** cada fase es una Release. Ninguna fase se da por terminada con
> un «funciona»: se cierra con una **prueba que se puede poner roja** y con un
> **número medido**. Lo que no se pueda hacer se escribe como NEGATIVO con su motivo,
> nunca como botón falso.

---

## 1 · El diagnóstico de hoy, con la línea que lo prueba

Seis causas. Todas comprobadas en el árbol de `v0.2-demo` (commit `95c0b3b`), no
deducidas de la memoria.

### 1.1 «Le digo *pausa* y no lo hace» — el oído se calla mientras suena la música

La cadena real:

- `ui/js/voice.js:52-70` → `if (hayMusica()) return 'música sonando';` y ese freno
  **cierra el micro**. No es un descuido: el comentario de la propia función explica
  que en Android abrir el micrófono baja el volumen de lo demás y en un teléfono de
  gama media lo traba. Consecuencia: **«Oye CORT, pausa» jamás llega a oírse**.
- Si se abre el micro a pulso, `ui/js/hud.js:1749-1787` casa la pausa con
  `/^(pausa|para|det[eé]n|stop)\b/` **y** exige `e.vivo` (`hud.js:1752`): si la
  música suena en otra app, nada aplica. Y el `/^pausa$/` de la línea 1753 revienta
  contra el punto que añade el reconocedor («Pausa.»).
- Lo que no casa se manda a `post('/api/command')` (`hud.js:1808`), el APK lo corta
  con 501 (`MainActivity.java:398-406`) y la cara contesta «El núcleo de CORT no
  respondió» (`hud.js:1822`). **Eso es exactamente lo que ella oye como «parece
  pendeja».**

### 1.2 El cerebro local existe, pero no decide nada

- **Los sensores no se piensan:** `Sentidos.java:36-145` lee 11 sensores y
  `onSensorChanged` **sólo guarda la última muestra en RAM**. No hay ningún consumidor
  que tome una decisión con ellos. Además `TYPE_STEP_COUNTER` (línea 65) exige
  `ACTIVITY_RECOGNITION`, permiso **que no está declarado** → ese sensor sale siempre
  vacío.
- **Las cuentas tienen techo:** `Razon.java:127` `FIRMA_MATH` sólo admite
  `+*/^%-`. «5x5» **escrito con la letra x** no casa y se va a la nube; «cinco por
  cinco» sí. El `Parser` es numérico: ante una incógnita devuelve `null`
  (`Razon.java:155-156`) — no despeja.
- **La regla de tres no existe:** `grep -rli "regla de (tres|3)"` sobre
  `*.java`, `*.js` y `*.py` da **cero resultados** en todo el repo.
- **El clima no es comando del teléfono:** `Cerebro.java:249` lo confiesa offline y se
  sirve del backend (`brain.py:280-287` → `/api/weather`, por IP). No hay
  `ACCESS_FINE_LOCATION` declarado, así que tampoco ciudad propia.

### 1.3 La descarga de modelos falla por cinco motivos concretos

| # | Motivo | Dónde |
| --- | --- | --- |
| 1 | El teléfono **no comprueba que Ollama esté vivo** antes de tirar: muere por excepción | `Ollama.java:262`, `326-338` |
| 2 | El progreso del móvil **écrasa** `total`/`hecho` con la línea actual del NDJSON: en modelos de varias capas la barra salta 100 % → 0 % | `Ollama.java:289-292` (el PC sí suma por `digest`: `models.py:397-401`) |
| 3 | Sin **cancelar ni reintentar** en el teléfono (el PC sí tiene `/api/models/cancel`) | `main.py:407` vs cero en `Ollama.java` |
| 4 | Lectura de 90 s por trozo + Wi-Fi que duerme: corta el lado del móvil aunque el PC siga bajando | `Ollama.java:87-89`, `326-333` |
| 5 | En el PC, `models.py:23` **importa `psutil` en la cabecera**: sin ese paquete el módulo entero revienta y **no existen** las rutas `/api/models*` | `backend/app/models.py:23` |

Y el catálogo: `scripts/mede-catalogo.py` **sólo imprime** por stdout (línea 77), no
escribe ningún JSON. Por eso el catálogo está **copiado a mano en dos sitios**: los 107
de la cara (`telefono.js:943`) y los **sólo 14** del backend (`models.py:41-70`).
Muchos ↓ del móvil no tienen entrada correspondiente en la hoja de escritorio. Requisito
externo que además hay que decir en la cara: Ollama tiene que escuchar en
`0.0.0.0:11434`, no en `127.0.0.1`.

### 1.4 Los atuendos pintan la cara, pero no el orbe ni la burbuja

`telefono.js:1473-1490` (`ponVariables`) pone `--primario`, `--secundario`, `--cyan` y
`--glass-hi` en `<html>`. Y `ui/js/orb.js` tiene **unos veinte colores fijados a mano**
(`0xaee2ff` l25, `0x5fc8ff` l30, `uColor 0x4fc6ff` l56, `rgba(70,180,255,…)` l164, y
sigue l173, l182, l196, l229, l240). **`orb.js` no lee una sola variable CSS**, y en
`hud.js` no hay ni un `getPropertyValue` (comprobado: cero coincidencias). Por eso
«cambio la paleta y las partículas no se cambian». La burbuja flotante tampoco es de la
cara: es un círculo que monta Java (`Flotante.java:87-134`) con su color propio.

### 1.5 Como asistente: el envase que ella usa **no puede** aparecer en el listado

- El perfil `completo` sí tiene las puertas: `VoiceInteractionService`
  (`AndroidManifest.xml:367-378`), sesión `.Sesiones` (`:380-384`), reconocedor con
  `BIND_SPEECH_RECOGNIZER` (`:386-394`), `ACTION_ASSIST` (`:314-317`) y
  `VOICE_COMMAND` (`:322-325`) — **5 `BIND_*`** (`:357,369,382,388,402`).
- El `nucleo` —el que ella instala porque es el que funciona— **recorta esas tres
  regiones enteras** (`perfil.py:92`): **0 `BIND_*`, 0 filtros de asistencia**. Android
  no tiene dónde listarla. No es un bug: es el precio del experimento que cerró Play
  Protect.
- El **rol moderno de Android 10+ ya está pedido**, y esto hay que decirlo bien porque
  el primer vistazo engaña: `MainActivity.java:605-627` pide
  `RoleManager.ROLE_ASSISTANT` (comprobando `isRoleAvailable` antes) y
  `CortNative.java:841-854` reporta si se tiene o no — es la vía pública, API 29+, y la
  dueña puede pedirla por voz con «pon CORT como asistente». Lo que **no** existe es la
  clase `AppRoleManager` (API 33), y no hace falta: `RoleManager` es el camino.
- Entonces, ¿por qué no aparece? Porque **el envase que ella lleva instalado no tiene
  nada que listar**: el `nucleo` recorta las dos regiones del manifiesto
  (`PERFIL-DESDE:acciones-asistente` `AndroidManifest.xml:305-326` y
  `PERFIL-DESDE:servicios-privilegiados` `:346-409`), y con el servicio
  `.Asistente` fuera, `isRoleAvailable(ROLE_ASSISTANT)` no llega a pedirse. Además
  `res/xml/asistente.xml` documenta el contrato del parser de AOSP: si falta el nodo
  `voice-interaction-service`, `sessionService` o `recognitionService`, **el teléfono no
  la lista y no avisa**. Y el `settingsActivity` se quita a propósito (con él, una app
  instalada a mano desaparece de la lista).
- «Ve la pantalla» (leer lo que hay en el `WebView` de otra app) exige
  `BIND_ACCESSIBILITY_SERVICE`, que está **vetado a propósito** en
  `AndroidManifest.xml:76-79` — es el servicio con el que Google mata apps del cajón, y
  era justamente la superficie que delataba al APK.

### 1.6 Orden y botones: hay controles que dicen «no» con razón, y otros que faltan

- Ecualizador: **no existe** ni una línea de `android.media.audiofx` en `src/`; la cara
  lo declara NEGATIVO (`pantallas.js:1409`, `1576`). Se puede hacer de verdad sobre la
  sesión del `MediaPlayer` (`Reproductor.java:602-609`) en su propio fichero, fuera de
  las clases que se comprueban con el JDK.
- Auriculares: hoy sólo **escucha** pasiva (`MediaSession` `Reproductor.java:113-129`,
  `KEYCODE_HEADSETHOOK` `:538`); «conecta con los audífonos» no existe (el
  `bluetooth` de `Acciones.java:540` abre Ajustes y ya).
- «Reproduce *Afterk Dark*»: la búsqueda por nombre existe pero **sólo por tacto**
  (`pantallas.js:2113` → `musicaBuscar`, fila → `musicaPoner` `:2176`; playlists
  `:2253,2262`). Por voz, `hud.js:1781` manda `musicaAutomatica()`
  (`CortNative.java:1204`: 40 pistas por gusto, desde cero) **sin preguntar lista ni
  canción** — literalmente lo que ella pide que se cambie.
- Queda pendiente la barrido sistemático de botones (elemento que llama a un método del
  puente que no existe): es la primera tarea de la fase 1, con prueba.

---

## 2 · La visión, traducida a arquitectura

Ella lo dijo así: «un JARVIS combinado con Cortana», «que trabaje como núcleo y se
conecte a todo», «que los modelos se vayan turnando», «que no sean puros comandos que
dan errores», «que converse en primer y segundo plano». Eso son **siete capas**, y esta
es la foto de cuál existe y cuál falta:

```
        ┌──────────────────────────────────────────────────────────┐
  OÍDO  │ 1 · escucha siempre (palabra de actividad, auricular,    │  existe, se calla
        │ barge-in con la música bajita en vez de cerrar el micro) │  con música  (1.1)
        ├──────────────────────────────────────────────────────────┤
        │ 2 · DICCTIONARY: frase → intent → ejecutor → respuesta   │  35 patrones sueltos,
        │ (datos, no código; generado y probado)                   │  sin catálogo único (1.2)
        ├──────────────────────────────────────────────────────────┤
        │ 3 · NÚCLEO DE DECISIÓN: enrutador con turnos de modelos  │  no existe: hoy es
        │    local del teléfono · Ollama de casa · nube            │  regex o nube (1.2)
        ├──────────────────────────────────────────────────────────┤
        │ 4 · MANOS: música · archivos · alarma/rutinas · agenda ·  │  existen a medias,
        │ apps · sensores · memoria (mismo contrato PC y móvil)     │  desigualmente (1.6)
        ├──────────────────────────────────────────────────────────┤
        │ 5 · CARA UNIDA: hojas que comparten estado y vestido,     │  la cara pinta, el
        │ orbe y burbuja se visten con el mismo traje               │  orbe no (1.4)
        ├──────────────────────────────────────────────────────────┤
        │ 6 · RUTINAS: «cuando X, entonces Y» con contexto         │  33 reglas; falta
        │ (hora, sensores, lugar) y voz en segundo plano            │  tiempo y oído (1.5)
        ├──────────────────────────────────────────────────────────┤
        │ 7 · SEGURIDAD: default-deny, lista blanca, sin            │  existe: así se
        │ accesibilidad, dos envases con su precio dicho            │  cerró Play Protect
        └──────────────────────────────────────────────────────────┘
```

**La idea que lo cambia todo:** hoy CORT es *un ejecutor de comandos con un cuadro de
chat al lado*. Tiene que pasar a ser *un decisor con tres cerebros y unas manos*. El
comando deja de ser la unidad: la unidad es **el intent**, y el intent decide **qué
cerebro lo contesta** y **qué mano lo ejecuta**.

---

## 3 · Los dos apartados que ella pidió (una hoja, dos pestañas)

Hoy «Cerebro» es una hoja con la nube suelta y «los cerebros de casa» incrustados. Ella
pide claridad: **un apartado sin conexión y otro conectado**. Queda así:

**Pestaña A · SIN CONEXIÓN (lo primordial, sus palabras).**

1. **Cerebro del teléfono** — los patrones locales que resuelven sin red (hora, fecha,
   cuentas, unidades, porcentajes, regla de tres, apagar la linterna, abrir la
   app…) y su contador real.
2. **Cerebros de casa (Ollama por Wi-Fi)** — el PC apagado se dice como lo que es: «el
   portátil no contesta», y **la orden no se lanza** si no hay respuesta al ping.
3. **Modelos que tengo** — lista de los descargados, con peso medido, cuál está
   asignado a qué trabajo y **su turno** (ver §5).
4. **Descargar** — el catálogo de 107 con el peso real, ↓ con progreso que **suma por
   capa**, botón de cancelar, botón de reintentar, y la causa del fallo escrita en
   pantalla (no un «no respondió»). El aviso de Android al terminar ya existe
   (`Timbre.java`).
5. **Sin PC, sin nube** — verificación de que todo lo anterior funciona con el
   portátil apagado; si algo no puede, lo dice esa fila.

**Pestaña B · CONECTADO.**

1. **Nube** — proveedor, modelo y clave (lo que ya hay), con prueba de latencia real.
2. **Puente con el PC** — IP/puerto, `busca cerebros`, y el requisito dicho:
   `OLLAMA_HOST=0.0.0.0:11434` (si no, el móvil no lo ve ni con escaneo).
3. **Qué se manda fuera y qué no** — lista legible: la consigna con memoria, el texto
   de la pregunta; **nunca** la clave ni los archivos. (Hoy esto no está escrito en
   ninguna parte; es seguridad de la que ella habla mucho y el repo documenta poco.)

---

## 4 · El diccionario grande (el catálogo de intents)

Hoy las frases están repartidas en cuatro sitios (`hud.js:1749-1787`,
`telefono.js:2279-2284`, `Cerebro.java:55-277`, `Acciones.java:164-176`) y **se
contradicen entre sí**: eso es «falta orden». La propuesta es **un solo fichero de
datos** del que se generan la cara, Java y las pruebas.

Formato de una entrada (estructura, no código final):

```json
{
  "intent":  "musica.poner_cancion",
  "dice":    "«pon Afterk Dark», «cámbialo a Afterk Dark», «suena Afterk Dark»",
  "patrones":["pon {cancion}", "cambia.{0,12}a {cancion}", "suena {cancion}"],
  "hueco":   { "cancion": "nombre" },
  "pide":    "musica.poner",                    // la MANO que lo ejecuta
  "cuando_falta": "¿Qué canción te pongo?",     // pregunta en vez de fallar
  "cerebro": ["local", "casa:mini", "nube"],    // orden de decisión (§5)
  "si_no_hay": "no encuentro «{cancion}» en tu música",
  "envase":  ["completo", "nucleo", "ligero"],
  "prueba":  7
}
```

Tamaño objetivo medible (no humo): **~90 intents**, **~700 frases generadas** a partir
de ellos, un generador con su prueba (el patrón ya existe: la ronda 2.2 generó 33
reglas y 283 frases), y la costura comprobando que **cada intent tiene dueño en los dos
sentidos** — nada dicho sin ejecutor, nada ejecutado sin quien lo pida.

Domínios del diccionario (con lo que hay hoy y lo que falta):

| Dominio | Intents | Estado hoy |
| --- | --- | --- |
| Música | poner canción / poner playlist / pausa / reanuda / siguiente / anterior / saltar / volumen del aparato / volumen del reproductor / velocidad / ecualizador / letra / carátula / cola | 8 de 14, **sin voz para poner canción** |
| Agenda | alarma (con tono y etiqueta) / temporizador / cronómetro / qué tengo hoy / recordatorio | alarma y temporizador existen; **alarma con canción y etiqueta: no** |
| Archivos | ordenar por estilo / mover carpeta / buscar dentro / leer documento | plan + confirmación existe (copiloto); **por gusto real: no** |
| Apps | abrir / cerrar de verdad / responder aviso | abrir sí; **cerrar y limpiar segundo plano: NEGATIVO dicho** |
| Cuentas | suma, 5x5 (con x), porcentaje, **regla de tres**, unidades, hora, fecha | falta `x`, falta regla de tres, no despeja |
| Clima | ahora / hoy / mañana, por ciudad | **sólo con PC**; no hay clima del móvil |
| Conversación | charlar, resumir, recordar, «conóceme» | existe; **sin turnos de modelo ni contexto de sensores** |
| Cuerpo | 11 sensores, luz, proximidad, pasos, movimiento | leídos, **sin decisión**; pasos sin permiso |

---

## 5 · La política de turnos: «que los modelos se vayan turnando»

Esto no existe hoy y es el corazón de su queja («que no sean puros comandos que dan
errores»). Se haría así, con reglas duras:

**Escalera de decisión, de barato a caro** (cada peldaño dice si puede y, si no, cede):

1. **Patrones locales** (cero milisegundos, cero red): hora, fecha, cuentas, unidades,
   alarmas, abrir app, música. **Lo que se resuelve aquí nunca se manda a un modelo.**
2. **Modelo de casa, tarea concreta** — Ollama del portátil.
3. **Nube** (si la dueña la puso y hay red).
4. **Respuesta honesta**: «no tengo cerebro para eso ahora» + qué falta, que es lo que
   ya hace bien la hoja Equipo.

**Turnos entre los descargados.** A cada **familia de tarea** se le asigna una lista
ordenada de modelos, y se usa el primero **que responda** dentro de su presupuesto. El
turno avanza si el modelo falla, está ocupado o no cabe en RAM; y vuelve al primero
cuando se libera. Perfiles sugeridos para empezar (con el portátil de 1,8 GiB y el
A16 de 4 GB como techo real):

| Familia | Qué se le pide | Perfil de modelo | Presupuesto |
| --- | --- | --- | --- |
| `calendario`, `música`, `apps`, `hora` | intents cortos, respuesta de una línea | **mini** (0.5 B – 1.5 B parámetros, cuantizado) | ≤ 1,2 GB en RAM, ≤ 4 s |
| `archivos`, `organizar`, `resumir` | plan con pasos | **medio** (3 B – 7 B) | ≤ 4 GB (sólo PC/PC-portátil) |
| `charla`, `razonar`, `código` | conversación larga y análisis | **gordo** (7 B+) | solo si hay sitio; si no, nube |

Reglas no negociables, escritas para que no se rompan solas: **un modelo nunca se
carga si no cabe** (se dice con su peso medido y el sitio libre); **el turno no puede
probar todos los modelos en cada frase** (un fallo y siguiente, no tres); **el portátil
de la dueña no puede tener Ollama y el navegador y el servidor de desarrollo a la vez**
(límite duro de su máquina); y **el teléfono nunca descarga un modelo que no quepa en
su aparato**, ni siquiera en la lista.

**Dónde vive esto:** en el núcleo (PC, Python) como módulo `turnos` con su prueba, y en
el teléfono como la misma política en `Mente.java` delegando en `Ollama.java`. El
diccionario (§4) lleva el campo `cerebro` y la cara deja de decidir: hoy decide en
cuatro sitios distintos, y así no.

---

## 6 · Rutinas y segundo plano: el caso de la alarma con *Afterk Dark*

Su ejemplo, palabra por palabra: «*oye CORT, ahorita son las 3:00 AM, ponme una alarma
para las 8:30 con la música Afterk Dark de alarma para despertarme, ir al ambulatorio*»
y que CORT **la despierte** y le diga «buenos días, toca ir al ambulatorio». Eso son
cuatro piezas, y hoy existen tres a medias:

1. **Entender la frase en una sola vez** — hora, día, tono musical y nota en un intent
   compuesto (`alarma.crear` con `para`, `con`, `nota`). Hoy `Acciones.java:164-176`
   hace una alarma sin canción y la cara no extrae «para las 8:30» con «con Afterk
   Dark» en la misma frase.
2. **Despertar de verdad con una canción** — `AlarmManager.setAlarmClock` (es la vía
   que perdona el ahorro de batería) + una actividad de alarma a pantalla completa con
   `showWhenLocked`/`turnScreenOn`, sonando `Reproductor` con la pista que eligió. La
   música ya se puede poner; **la pantalla de alarma propia, no existe**.
3. **Oírla con la pantalla apagada** — aquí está el nudo: el oído se cierra con la
   música sonando (§1.1) y **no hay servicio en primer plano** de escucha (el
   manifiesto lo dice: no hay `FOREGROUND_SERVICE_MICROPHONE`). Se puede abrir el
   micrófono en primer plano con la **música bajita (ducking) en vez de cerrada**: eso
   arregla §1.1 y a la vez da el oído de segundo plano. Precio a decir: más batería.
4. **La rutina de la mañana** — al disparar la alarma, `automatiza.js` ejecuta la
   secuencia (fecha, clima, «qué tengo hoy», la nota que dejó escrita). Las reglas
   «cuando X, entonces Y» ya existen (33); falta el **disparador de hora exacta**.

**Lo que depende del fabricante y no se puede prometer** (Samsung A16, 4 GB): que el
teléfono despierte el micro cuando Android lo tiene congelado, que el listado de
asistentes la muestre, que el botón del auricular sea de CORT cuando suena otra app.
Para cada uno hay plan B (widget, baldosín, doble toque, notificación con acción) y se
dice **con esas palabras**.

---

## 7 · Cara unida: atuendos de verdad y la burbuja de la 1.1.4

- **El orbe y la burbuja se visten.** `orb.js` tiene que leer `--primario` /
  `--secundario` (una función que los convierta a `THREE.Color` al montar y al cambiar
  el traje) en lugar de sus veinte hex fijos, y `Flotante.java` tiene que recibir el
  color del atuendo puesto en vez de traer el suyo. Prueba: cambiar de traje y que
  **cada color del orbe cambie** (se puede comprobar sin teléfono, en el navegador, con
  la sonda).
- **La burbuja de la 1.1.4, que es lo que a ella le gustó**: azul, se vuelve
  transparente, se mueve, **no molesta**. Hay que recuperar esos comportamientos de
  `Flotante.java` (arrastrar, opacidad al reposo, tamaño) y medírlos contra lo que hace
  hoy. *Pendiente: mirar qué traía exactamente la 1.1.4 antes de prometer nada* — en
  este repo no hay fuente de esa versión (es del cuerpo Kotlin original, sin `.kt` en
  disco), así que se reconstruye por comportamiento descrito por ella.
- **Agua y vidrio con freno.** Animaciones de onda y desenfoque, pero con un tope
  declarado: en modo juego o con poca RAM se bajan a transformaciones baratas. Hoy no
  hay casi nada de esto (el `backdrop-filter` escaso y ningún `@keyframes` de agua);
  es la tarea #102, y entra aquí porque **la cara es un solo sistema**, no cuatro hojas.

---

## 8 · Asistente: las tres vías y su precio (esto hay que decidirlo, no adivinarlo)

| Vía | Qué da | Qué cuesta | Mi lectura |
| --- | --- | --- | --- |
| **A. Envase `completo`** (los 5 `BIND_*` ya declarados) | puede aparecer en Ajustes → Apps → Predeterminadas → Asistente | ya se sabe que la superficie ampliada **fue** lo que activó el bloqueo; ella lo probó y eligió `nucleo` | no sirve: fue el camino que ya se rechazó |
| **B. Envase intermedio `nucleo + asistencia`** (3 `BIND_*`: `VOICE_INTERACTION`, `SESSION`/reconocedor, sin notificaciones ni accesibilidad) | el mínimo que necesita Android para **listarla** como asistencia | una Release nueva que **hay que medir en su teléfono** antes de prometerla | **esta es la vía honesta**: superficie mínima, precio dicho, se prueba |
| **C. Rol de Android 10+** (`RoleManager.ROLE_ASSISTANT`) | **ya está implementado** (`MainActivity.java:605-627`, reportado en `CortNative.java:841-854`): es el cuadro de Android que de verdad te deja elegir CORT | no sirve de nada **mientras el envase no tenga el servicio `.Asistente`** que lo respalde | **no hay que escribirlo: hay que dejarlo llegar** en el envase B, y pedirlo con «pon CORT como asistente» |

Y el punto que hay que decirle sin rodeos: **«ve la pantalla» y «aparece como el
asistente de Google» son dos cosas distintas**. Lo primero necesita accesibilidad —el
servicio que vetamos para que el APK se instalara— y **no se va a recuperar** salvo que
ella decida pagar ese precio un día. Lo segundo se puede hacer sin accesibilidad (vía
B + C), y es lo que da la experiencia que ella quiere: «Oye CORT» con el botón de
siempre, y que CORT conteste.

---

## 9 · NEGATIVOS (lo que no se hace, con motivo)

| Petición | Veredicto | Motivo |
| --- | --- | --- |
| «abre la app y que no se quede en segundo plano para optimizar» | **NO se puede matar procesos de terceros** | Android no lo permite sin permiso de uso (`PACKAGE_USAGE_STATS`, vetado) ni root; lo que sí se hace: cerrar CORT, no arrancar su servicio, y decir «no puedo cerrar X app» |
| «que vea la pantalla» | **NO con accesibilidad** | `BIND_ACCESSIBILITY_SERVICE` vetado a propósito (`AndroidManifest.xml:76-79`): es lo que mata apps del cajón en Play Protect |
| «que aprenda de internet solo» | **NO sin control** | lo que se hace: el catálogo de modelos con pesos medidos y la auto-actualización **con puerta humana** (PR + CI + ella aprueba), nunca un push firmado sin que lo vea |
| «el cerebro gordo dentro del teléfono» | **NO con 4 GB** | los modelos de 7 B+ no caben; GGUF pequeño sí (tarea #79) y se dirá con peso medido |
| «descargar los modelos con el PC apagado» | **NO** | Ollama vive en el portátil; el teléfono puede bajar GGUF suyos, no modelos de Ollama de un PC que no existe |

---

## 10 · Fases: una Release por fase, con su prueba decisiva

| Fase | Qué | Prueba decisiva (se pone roja si se rompe) | Se mide |
| --- | --- | --- | --- |
| **F12 · que la voz responda** | barge-in con ducking en vez de micro cerrado; normalizar puntuación; `pausa/play/siguiente/anterior/volumen` sin `e.vivo` estricto; **barrido de botones** (elemento → método del puente que no existe) | decir «pausa» con música sonando en una prueba de cara; y la sonda con el puente falso | peso del APK y nº de botones muertos antes/después |
| **F13 · modelos que se descargan** | ping antes de tirar; progreso **sumando por capa**; cancelar y reintentar en el móvil; `psutil` opcional en el backend; catálogo **único generado** (107) para PC y móvil; el requisito `OLLAMA_HOST` dicho en pantalla | prueba del parser NDJSON con dos capas y con líneas fuera de orden | peso real de un ↓ con y sin el arreglo |
| **F14 · diccionario + turnos** | `diccionario` de datos (~90 intents / ~700 frases) del que salen cara, Java y pruebas; escalera local→casa→nube; `x` en cuentas, **regla de tres**, hora, porcentaje | generador + costura en dos sentidos (nada dicho sin dueño, nada ejecutado sin quien lo pida) | **91 intents / 736 frases** (41 mando, 26 razón, 13 casa, 11 nube); 208 frases de razón contestadas sin red |
| **F15 · cerebro de casa con nombres** | «pon *After Dark*», «qué playlist», «cámbialo a <canción>», ecualizador real (`audiofx.Equalizer` en su propio fichero, fuera de las clases de papel), auricular con acción | `Prueba6` (18/18) sobre `Elige` puro + costura [30] (7 comprobaciones) + taller de 8 mutaciones | **41 intenciones / 736 frases** (F15 añadió 4 reglas y convirtió «pon» en búsqueda); 18 elecciones de canción/listas/preset medidas en el JDK; 336 frases de tabla en `Prueba3` |
| **F16 · el despertador** | hora + canción + nota + rutina en una frase; alarma **propia** (`AlarmManager` + notificación de categoría ALARMA en canal alto), pantalla de despertador en la cara; sin permiso nuevo (sólo un `<receiver>` no exportado) | `Prueba7` (21/21) sobre `Despertar` puro, con los dos cambios de hora + costura [31] (8 comprobaciones) + taller de 18 mutaciones | exactitud **dicha** (`exacta:false` en Android 12+ sin `SCHEDULE_EXACT_ALARM`); canción resuelta al ponerla con `Elige.mejor`; 336 frases de tabla |
| **F17 · cara vestida** | orbe que lee `--primario`/`--secundario` (16 canales derivados en `traje.js`), burbuja 1.1.4 (azul translúcida, arrastrable, opacidad de reposo), agua y vidrio con freno por RAM/juego; **sin permiso nuevo** y con los 44 dp intactos | `prueba-colores.mjs` (28/28): cambiar traje ⇒ cambian **los 16** colores del orbe + costura [32] (6 comprobaciones) + taller de 19 mutaciones | variables leídas por `orb.js`: **2 al montar** (antes 0); 16 canales × 6 trajes medidos sin GPU; freno con `deviceMemory <= 2` o juego |

Cada fase termina igual: **verificar → commit → etiqueta `-demo` → pipeline verde →
medir la Release → README/docs con cifras medidas → informe con lo confesado**. Y el
envase que se instala encima del anterior **no se toca**: `versionCode` creciente, misma
llave, `nucleo` como default de ella.

---

## 11 · Decisiones de la dueña (2026-10-23, tomadas con opciones)

1. **Arranque: F13 + F12 juntas en la 2.9.0** — la descarga de modelos fiable *y* que la
   voz responda, en una sola Release. F14 (diccionario y turnos) detrás.
   *Corrección fechada el 2026-10-24:* la 2.9.0 salió sólo con F13 (`v0.2.37-demo`); F12
   se quedó local y se publica con F14–F17 en la **2.10.0**, la Release del lote. No se
   reescribe la decisión: se dice lo que pasó.
2. **Asistente: envase NUEVO, el `nucleo` no se toca.** Se añade un cuarto archivo
   `nucleo+asistencia` con la superficie mínima (servicio de voz + reconocedor + sesión)
   y su precio medido y dicho; el `nucleo` de siempre sigue siendo el recomendado y el
   que ella instala. **Nada de tocar los 12.636 B del `nucleo`.**
3. **Oído: sí al ducking, y sí al segundo plano.** Con una separación honesta:
   - **El ducking no cuesta superficie** —`requestAudioFocus` con
     `AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK` no necesita permiso—, así que **entra ya en el
     `nucleo`** de la 2.9.0: con música sonando, CORT baja el volumen un momento, escucha
     y lo devuelve.
   - **La escucha permanente con la pantalla apagada sí cuesta**: necesita un servicio en
     primer plano con `FOREGROUND_SERVICE_MICROPHONE`, y esa es justo la superficie que
     cerró Play Protect. **Esa parte se queda en el envase `nucleo+asistencia`** y se mide
     allí antes de prometerla.
4. Además del ducking, «pausa / siguiente / retrocede» tienen que valer **cuando la música
   la pone otra app** (Lark, Spotify): se manda la tecla de medios al sistema
   (`AudioManager.dispatchMediaKeyEvent`, cero permisos) en vez de exigir `e.vivo`.

---

## 12 · Reglas que se mantienen (son las suyas, puestas por escrito)

No inventar: verificar antes de afirmar y confesar el fallo antes de arreglarlo. Un
verde que no puede caerse no es prueba (mutación). Nada de relleno: ni un byte, ni un
permiso, ni un botón que no haga algo. La dueña manda con preguntas de opciones y
después ejecuta en lote. El PC de 2 núcleos y 1,8 GiB no se congela: nada de Ollama +
navegador + servidor a la vez, y respaldo antes de experimentar. Ramas `v0.2-demo`,
etiquetas `-demo`, nunca reutilizar etiqueta, nunca `force-push`, los logs de Actions no
son públicos (anotaciones). El contrato del teléfono de 5 argumentos para hablar no se
rompe. Y ninguna auto-actualización sin puerta humana.

---

## 13 · El prompt maestro (para cualquier IA que trabaje en CORT)

> Eres **arquitecta de software e IA** en el proyecto **CORT** (repo público
> `Sandra2244/CORT`, rama `v0.2-demo`): asistente de voz tipo **JARVIS + Cortana**, con
> escritorio (Electron + cara JS vanilla en `ui/` + backend FastAPI) y **APK de Android
> compilado sin Gradle dentro de GitHub Actions**, cuya cara corre en un `WebView` y
> habla con Java por el puente `CortNative`. La dueña es **Sandra**, principiante,
> habla **español**, tiene un portátil de **2 núcleos y 1,8 GiB** (nunca Ollama +
> navegador + servidor de desarrollo a la vez) y un **Samsung A16 de 4 GB** de RAM.
>
> **Objetivo único:** que CORT sea un **núcleo que decide**, no una lista de comandos
> que fallan. Tres cerebros con escalera de decisión (1 patrones locales del teléfono,
> 2 Ollama de casa por Wi-Fi con **turnos entre los modelos descargados** por familia
> de tarea, 3 nube) y unas manos (música, archivos, alarma/rutinas, agenda, apps,
> sensores). Todo pasa por el **diccionario de intents** (`docs/CEREBRO-MAESTRO.md`,
> ~90 intents, ~700 frases): el diccionario es **datos generados y probados**, y de él
> salen la cara, Java y las pruebas. Nada de frases sueltas repartidas por cuatro
> ficheros.
>
> **Reglas duras.** (1) **No inventes**: afirma sólo con lo medido; si no lo sabes,
> escribe «pendiente de medir» o el NEGATIVO con su motivo. (2) **Un verde que no puede
> caerse no es prueba**: toda comprobación nueva se muta y se ve ponerse roja (21
> mutaciones en taller, árbol de enlaces duros, `sed -i`, `cmp`, `rm -f`). (3) **Nada de
> relleno**: ningún byte, permiso o botón que no haga algo. (4) **No toques la
> superficie del `nucleo`** (0 `BIND_*`, 21 permisos, manifiesto de 12.636 B) sin decir
> el precio; las nuevas puertas de asistencia van en **un envase nuevo que se mide**.
> (5) **Las clases que compila `scripts/prueba-mente.sh` contra papeles con el JDK no
> pueden tocar `android.*`**: lo que use Android va en su propio fichero (`Timbre`,
> `Flotante`, y ahora `Tono`). (6) El contrato `CortNative.speak(texto, id, voz, tono,
> velocidad)` **no se cambia**. (7) Publicación: `-demo` en las etiquetas, nunca
> reutilizar, nunca `force-push`, Release la hace el CI, los logs de Actions no son
> públicos → anotaciones. (8) **Se instala encima**: `versionCode` creciente y misma
> llave de firma. (9) Autonomía **con puerta humana** (ella aprueba la Release).
> (10) Lee primero `docs/CEREBRO-MAESTRO.md`, `docs/CONTRATO-PUENTE-2.1.md`,
> `docs/INSTALAR-APK.md`, `docs/CEREBROS-DE-CASA.md` y `docs/COPILOTO.md`.
>
> **Trabajo por fases F12→F17** (tabla §10). Cierra cada fase con: `prueba-costura.py` y
> `prueba-mente.sh` en verde con su recuento, etiqueta, pipeline verde, **pesos y sha256
> medidos de los tres envases**, README/docs con cifras reales, e informe que empieza
> por el enlace de la Release y nombra **lo que sigue sin verse en su teléfono**.

---

## 14 · Cerrado y medido (se actualiza fase por fase)

### F13 · la mitad del PC (2026-10-23)

El **motivo nº 1** por el que «no se pueden descargar modelos» desde el teléfono era
nuestro: `models.arrancar_servidor()` levantaba `ollama serve` con el entorno de
siempre, y Ollama se quedaba escuchando sólo en `127.0.0.1`. En el portátil de la
dueña los modelos **ya están bajados** (231,71 GB libres medidos) y aun así el
teléfono no los veía.

Qué entró en `backend/app/models.py`:

| lo que se arregló | cómo se prueba ahora |
| --- | --- |
| `psutil` es opcional (antes mataba el módulo entero sin él) | se importa con bloqueador de `sys.meta_path` en un proceso aparte y se exige `PSUTIL None` + veredicto `sin medir` + cierre por `/proc` |
| Ollama se levanta con `OLLAMA_HOST=0.0.0.0:11434` | se anota el `env` que recibe `Popen` (gemelo), y se comprueba también que el `OLLAMA_HOST` que ella ya puso **no** se pisa (`setdefault`) |
| `ollama_red` es un mando de Ajustes de verdad | escrito en `config_store.DEFAULTS` (sin eso, `raw()` lo filtra y `set_value` lo rechaza), probado con JSON real en caja de arena |
| la IP que se enseña es la que responde | `info_red()` con sus cinco notas honestas; `visible_en_red()` no sale a la red con Ollama apagado (el stub de `requests` hereda de `BaseException` porque un `except Exception` se traga un `AssertionError`) |
| el disco se mira **antes** de lanzar la bajada | niega `llama3.1:8b` con 0,5 GB libres nombrando los bytes; **no** negativea un modelo fuera del catálogo ni un disco sin medir |
| `/api/models` lleva `red`, `ram_libre_gb` y `disco_libre_gb` | `estado_completo()` comprobado con gemelos: 14 entradas del catálogo y su veredicto |

Cifras: **53 comprobaciones** en `scripts/prueba-modelos.py` (1 s) y
**17 mutaciones** en `scripts/taller-modelos.sh` — todas caen, cada una nombrando la
comprobación que le faltaba a la suite, y el código limpio vuelve a dar verde. El
sector **[25]** de `scripts/prueba-costura.py` añade las tres costuras entre capas:
que el pipeline invoque la suite (y que el taller **no** se cuele en Actions), que
`quiere_red()` pregunte `ollama_red` a la config leyéndolo con `ast` (no con
subcadenas: el docstring también nombra la clave), y que el puerto del PC
(`models.PUERTO_OLLAMA`) sea el mismo que busca el teléfono (`Ollama.java:92`).
Dos mutaciones que **aguantaron** al primer intento y obligaron a reescribir la
comprobación: buscar `"ollama_red"` en el texto de `config_store.py` (lo salva
`ENV_NAMES`) y en el de `quiere_red()` (lo salva el docstring).

**Cerrado y medido (mitad del teléfono, 2026-10-23)** — `apps/apk/src/com/cort/ia/Ollama.java`,
su puente en `Mente.java` y la hoja de Modelos en `ui/js/telefono.js`:

| lo que se arregló | cómo se prueba ahora |
| --- | --- |
| la barra no se quedaba quieta: el NDJSON se **suma por `digest`** | `Prueba4` monta un modelo de dos capas intercaladas (4.000.000 + 1.000.000) y exige `hecho:4500000 / total:5000000`, `"capas":2` y que el porcentaje **nunca baje** entre cuadros |
| una línea de `verifying` (trae `digest` pero no `total`) borraba el total de su capa | el mismo cuadro, con esa línea metida en medio: el total del modelo sigue siendo 5.000.000 |
| un PC dormido se tragaba 90 s y devolvía un timeout mudo | `descarga()` hace un `GET /api/version` **delante** de `POST /api/pull`; con un servidor que sólo contesta a `/api/pull`, `Prueba4` cuenta `PULLS_SIN_VERSION == 0` y lee el aviso que nombra `OLLAMA_HOST` |
| no había forma de parar una bajada | `cancela()` sube el interruptor y **cierra la corriente y la conexión**; en el escenario `callada` (el servidor calla 3 s) la prueba espera 2 s y exige `"cancelado":true` |
| el aviso sonaba por algo que la dueña cortó | cancelando, la lista de timbres de papel está vacía, y la cara dice «bajada cancelada» en vez de prometer el aviso |
| dos bajadas a la vez se pisaban los campos del cancelar | la segunda se rechaza nombrando la que ya está bajando (`synchronized`) |
| la hoja no decía con qué PC estaba hablando | el campo `servidor` de Java se guarda y se pinta en la línea de estado (costura [26.h]) |

El cancelar **no abre ninguna superficie nueva**: entra por el puente que ya existía,
`mente({que:'ollama',accion:'cancela'})`, con su botón `✕ cancelar` y su frase de voz
(«cancela la bajada»). Cifras: `Prueba4` pasa de 39 a **58 comprobaciones**, las cuatro
suites de `scripts/prueba-mente.sh` dan verde en el portátil con los gemelos de papel,
el sector **[26]** de `scripts/prueba-costura.py` cose las tres capas (8 comprobaciones;
la suite llega a **264 `ok`**) y su taller `scripts/taller-ollama.sh` tiene **12
mutaciones que caen las 12**, cada una nombrando la comprobación que echaba de menos.

Lo que **no** salió como se esperaba, dicho en vez de fingido: el comentario del campo
aseguraba que `HttpURLConnection.disconnect()` no despierta a un `readLine()` bloqueado y
que cerrar el `InputStream` es imprescindible. El taller lo midió y **no es cierto en
esta pila del JDK**: quitando sólo una de las dos cerradas la cancelación sigue
funcionando; la mutación que cae es quitarlas **las dos**. Por eso el taller tiene una
sola mutación para el tema (y se dejó el doble cierre: en Android la implementación es
`com.android.okhttp`, otra, y aquí no se puede medir).

**Lo que queda de F13**: un catálogo generado una vez para los 107 modelos —hoy son 14
en `backend/app/models.py` y 107 en `ui/js/telefono.js`, cosidos por la comprobación
[23.d], que exige que las 14 filas del PC sean un subconjunto idéntico de las 107 del
teléfono, así que no pueden ir cada una por su lado—. Y **nada de esto llega a su
teléfono hasta que salga la Release**: el pipeline no se ha corrido todavía con esto.

### F14 · el diccionario, en los dos sentidos (2026-10-23)

Una sola lista vierte cuatro bocas: el JSON del APK, `Cerebro.tablaDelCodigo()`, la ayuda
de la cara (`ui/js/diccionario.js`) y los dos ficheros de casos de `Prueba5`. El
generador es `scripts/habilidades.py`; la mitad que no mueve el aparato vive en
`scripts/saber.py` y se importa desde allí (no se copia).

| lo que se cerró | cómo se prueba ahora |
| --- | --- |
| 41 órdenes + 50 saberes = **91 intenciones / 736 frases** (F15 sumó las cuatro de música), sin duplicados ni `{resto}` a mitad de palabra | el generador se niega a escribir si baja de `MIN_INTENTS`/`MIN_FRASES` o si una frase se repite en dos reglas |
| las 208 frases de razón se contestan **sin red** | `Prueba5` recorre `casos-razon.txt` (una frase por línea, con prefijo esperado sólo en la frase de prueba de cada intención) contra `Razon` |
| las 192 de casa/nube **no** se contestan en el teléfono con una respuesta floja | `Prueba5` exige que `Cerebro.procesar` devuelva `desconocido` y que `Razon.intenta` devuelva `null` |
| `x`, `×` y las palabras «suma/resta … y …» entran en cuentas; «dime cuánto es 3 x 3» ya no se queda a medias | `Prueba` (43/43) con el caso repetido de prefijos |
| «averigua qué día es el examen» no se lo come el calendario | `Razon.calendario` sale antes en las órdenes de investigación (`averigua`, `investiga`, `busca`, `piensa`, `explícame`) |
| «qué apps tengo» no lo roba la agenda por el «tengo» | rama propia en `telefonoPorVoz` antes de la agenda; abre la hoja Equipo y cuenta las apps |
| una acción de la tabla ya no se manda a `Acciones` cuando su boca es la cara | `ejecutaLocal()` reparte: 10 de aparato → `Acciones.java`, música → `teclaMedia` (o el reproductor propio) y 5 que la cara atiende antes de pensar; antes, tras «Hola, te escucho.» salía «todavía no sé hacer saludo» |
| la sonda no se quedó mirando la rama del APK viejo | el puente de mentira de `ui/sonda-carita.html` simula `teclaMedia`, y la costura [29] exige que simule todo lo que la cara pide |

Cifras medidas en el portátil cuando se cerró F14: `Prueba` 43/43, `Prueba2` 45,
`Prueba3` TABLA OK, `Prueba4` 58 y `Prueba5` DICCIONARIO OK (208 + 192 frases) — la línea
final dice «las 5 suites»; la costura subió a **280 `ok`**, de los que **12** son del
sector [29]. El taller de mutaciones de F14 hace caer cinco comprobaciones (una frase
menos en la cara, un total que no cuadra, una acción sin boca, un caso de razón perdido y
`Prueba5` fuera del bucle) y el código limpio vuelve a verde. Queda por verificar **en su
teléfono** que el APK real compila con estas tablas y que las voces nuevas (cronómetro,
estado y apps) se oyen.

### F15 · «pon After Dark»: la canción, la lista y el ecualizador (2026-10-23)

El cerebro ya puede devolver `musica` con `poner:<canción>`, `lista:<nombre>`, `listas`,
`ecualiza:<preset>` y `ecualizaestado`. La decisión de **cuál** de las canciones que
salen es la que suena no se toma en la cara ni en el puente: se toma en `Elige`, Java
puro y sin `android.*`, para que `Prueba6` la mida en el JDK del portátil.

| lo que se cerró | cómo se prueba ahora |
| --- | --- |
| «pon After Dark» busca en la biblioteca y **el título exacto gana al remix**; «mr kitty» elige por artista; «horizonte sucesos» por palabras | `Prueba6` (18/18): exacto, tildes, artista, palabras, y lo que no está se queda en `—` |
| una canción **no** se elige por debajo de 200 puntos: mejor decir «no la encuentro» que poner otra | la mutación del umbral (`return mejor;`) hace caer «lo que no está se queda en —» |
| «pon la playlist para correr» cruza el nombre dicho con las listas reales del teléfono (`Musica.listas`) | `Elige.lista` en `musicaPonerLista`; el puente devuelve el nombre real, no el dicho |
| «pon el ecualizador en clásica/graves» usa el `audiofx.Equalizer` del aparato, no una curva inventada | `Ecualizador.java` en su propio fichero, `usePreset` tras `Elige.preset`; si el aparato no trae ese preset, se dice cuáles tiene |
| el efecto va pegado a la sesión del `MediaPlayer` y se suelta **antes** que él | costura [30.d] por índices dentro de `onPrepared`/`onDestroy`, no por búsqueda global |
| el ecualizador no finge estar medido en el JDK | no se copia a `prueba-mente.sh`; la costura [30.c] mira la línea de `cp` (el comentario sí lo nombra) |
| «pon una alarma a las 7:30» no acaba buscando una canción con ese nombre | la sección 4d va **después** de la alarma y **antes** de los cerebros de casa; costura [30.f] por índices |
| la sección de música por nombre no corre en un APK viejo | `puede('musicaPonerNombre')` y el puente de mentira de la sonda simula las tres teclas nuevas |
| los verbos que el diccionario puede devolver tienen boca en `ejecutaLocal` | costura [30.e]: los 9 verbos atendidos; «mueve» sigue sin inventarse un salto |
| `Prueba3` cazó un `param` en camelCase que `Cerebro.normaliza` devolvía en minúsculas | el param se llama `ecualizaestado` en las cuatro bocas; antes las 8 frases del estado fallaban |

Cifras medidas en el portátil: `Prueba6` **18/18**, las **6 suites** de
`scripts/prueba-mente.sh` en verde sobre **336 frases de tabla**, la costura sube a
**287 `ok`** (7 del sector [30]) y `scripts/taller-f15.sh` tiene **8 mutaciones que caen
las 8**, cada una nombrando la comprobación que la echaba de menos. Además se añadió el
gemelo de papel de `AudioManager`/`AudioAttributes` (`apps/apk/prueba/papeles`), sin el
cual `prueba-oido.sh` no compilaba el ducking de F12: ahora da verde con sus **6
comprobaciones** sobre el Vosk real.

Lo que **no** se puede medir aquí: que el `Equalizer` de su teléfono traiga los presets
que dice, y que el ducking se oiga. Eso es de aparato. Y **nada de esto llega a su
teléfono hasta que salga la Release**: el pipeline no se ha corrido con F15 todavía.

### F16 · «despiértame a las 7 con After Dark para el examen» (2026-10-24)

Hasta aquí, «pon una alarma» abría el reloj del sistema con `SET_ALARM` y CORT se
quedaba sin saber qué había puesto: no podía elegir la canción, no podía enseñar la
nota y no podía callarla. Ahora la alarma es **suya**. La frase se parte en
`Despertar` —Java puro, sin `android.*`, medido por `Prueba7` en el JDK— y `Alarma`
sólo obedece: arma el `PendingIntent`, guarda el estado en las `SharedPreferences`
que ya existían y, cuando suena, pone una notificación de **categoría ALARMA** en un
canal propio de importancia alta con el tono de alarma del sistema.

| lo que se cerró | cómo se prueba ahora |
| --- | --- |
| «7:30», «a las 8», «7 y media», «7 y cuarto», con tilde o en mayúsculas | `Prueba7` (21/21): hora, minuto y las dos formas de los cuartos |
| la canción va detrás de «con» y la nota detrás de «para»; cada una en su sitio | `Prueba7` casos 4–6; la cara saca **primero** la canción para que «noche de synth» no pierda «de synth» como nota |
| «con la canción» sin nombre **no** inventa una canción llamada «la canción» | `Prueba7` lo exige; el taller la mete a la fuerza (`if (false)`) y la suite se pone roja |
| «buenos días»/«rutina» enciende la rutina y no se cuela ni en la canción ni en la nota | `Prueba7` caso 7; al sonar, la rutina lee `Agenda.agenda("hoy")` en ese momento |
| sin hora no hay alarma (mejor preguntar que despertar a las 0:00) | `Prueba7`; `Alarma.ponerDesde` devuelve `ok:false` con la frase que pide la hora |
| el próximo disparo es **estrictamente futuro**: justo ahora → mañana, sin doble disparo | `Prueba7` caso 12 |
| los dos cambios de hora: en octubre las 02:30 existen dos veces; en marzo no existen | `Prueba7` casos 13–14; la corrección del hueco **sólo empuja hacia adelante** (`puesto < pedido`) |
| la hora se parte en **un solo sitio** | costura [31.b]: `Despertar.parte/proximo/falta` sólo tienen dueño en `Alarma.java`; si `Alarma` trae su propio `Pattern`, se pone roja |
| la exactitud no se finge | `canScheduleExactAlarms()` en Android 12+, `setExactAndAllowWhileIdle` cuando sí, `setAndAllowWhileIdle` cuando no, `catch (SecurityException)` de plan B y `exacta:false` + «puede sonar unos minutos tarde» en la respuesta |
| el aviso despierta de verdad | costura [31.d]: canal `cort-alarma` IMPORTANCE_HIGH, `CATEGORY_ALARM`, `USAGE_ALARM`/`TYPE_ALARM`, `FLAG_INSISTENT`, `setOngoing(true)` y dos botones (Detener / 5 min) |
| el disparo es explícito y cerrado | `<receiver .AlarmaSuena exported="false">` sin `<intent-filter>`; costura [31.e]; `AlarmaSuena` atiende sonar/detener/posponer |
| la cara enseña el despertador aunque esté en otra hoja | pantalla `#cort-alarma-pantalla` pegada al `body`, atendida **antes** que cualquier otro evento y sin cerrarse sola; no se cierra hasta pulsar detener o posponer |
| arranque en frío: el evento no se pierde | `MainActivity` guarda `alarmaPendiente` y lo suelta en `onPageFinished`; costura [31.g], que exige los dos caminos |
| la frase de la tabla conserva la cola | `Cerebro.hora` reconstruye con lo de delante **y** lo de detrás; `Prueba3` mide las dos frases compuestas y el taller borra una para que se caiga |
| una sola boca para poner la alarma | la cara manda `accion` con `que:'alarma'`; `Acciones.alarma` compone la frase con los campos sueltos. `alarmaPoner` se **quitó** del puente: nadie la llamaba y habría sido una segunda forma de decidir la hora |

Cifras medidas en el portátil: `Prueba7` **21/21**, las **7 suites** de
`scripts/prueba-mente.sh` en verde sobre **336 frases de tabla**, la costura en
**295 `ok`** (8 del sector [31]) y `scripts/taller-f16.sh` con **18 mutaciones que caen
las 18**, cada una nombrando la comprobación que la echaba de menos; dos de ellas
corren la suite entera (`DST de marzo`, `sin nombre no hay canción`).

**Lo que NO se puede medir aquí, y se dice sin adornos:**

- Que el teléfono despierte a la hora. Sin `SCHEDULE_EXACT_ALARM` —que **no** se
  declara: sería un permiso nuevo— en Android 12+ `canScheduleExactAlarms()` suele
  contestar que no y la alarma puede sonar unos minutos tarde. La respuesta lo dice
  (`exacta:false` y una frase), no se promete puntualidad que no hay.
- Que el sonido se repita. `FLAG_INSISTENT` se pide, pero varios fabricantes no lo
  respetan con canales; el aviso de canal alto sigue siendo lo que despierta.
- Que la canción arranque. Va por el servicio en primer plano (`Reproductor`); si el
  sistema prohíbe arrancar servicios desde segundo plano —más probable con la alarma
  permitida, no exacta—, el tono de la notificación no depende de eso.
- Que la cara se asome con la app cerrada. Sólo se intenta si CORT tiene «aparecer
  encima de otras apps»; sin esa concesión Android no deja abrir actividades desde
  segundo plano y queda la notificación, que es la que despierta.
- Que sobreviva a reiniciar. **No** sobrevive: no se declara `RECEIVE_BOOT_COMPLETED`
  (otro permiso) y la alarma se pierde al apagar el teléfono.
- Nada de esto llega a su teléfono hasta que salga la Release: **el pipeline no se ha
  corrido con F16 todavía**.

Los dos botones de la notificación van sin icono (`0`, que Android permite): los
`android.R.drawable` que esta casa da por comprobados son cuatro y ninguno es un reloj
de alarma; inventar uno local pasaría el `javac` de casa y reventaría en el runner.


### F17 · el orbe se viste, la burbuja se arrastra y el agua tiene freno (2026-10-24)

Hasta aquí los atuendos pintaban el HUD pero **no el orbe**: `orb.js` tenía una veintena
de colores escritos a mano, así que elegir Matrix dejaba la bola azul. Y la burbuja
flotante era un punto opaco y quieto que no se parecía a la de la 1.1.4 que a ella le
gustó. Las dos cosas se cierran sin tocar la superficie: **ningún permiso nuevo**, la
firma `burbuja(Context, boolean)` intacta y los **44 dp** de siempre.

| lo que se cerró | cómo se prueba ahora |
| --- | --- |
| cambiar de traje cambia **todos** los colores del orbe | `ui/js/traje.js` deriva **16 canales** de `--primario`/`--secundario`; `prueba-colores.mjs` exige que cada uno de los otros cinco trajes difiera del de fábrica en **los 16** (28/28) |
| un canal olvidado no pasa en verde | la prueba exige `CLAVES.length === 16`; la costura [32.a] exige que `aplica()` pinte cada `c.<canal>` y que no quede un `0x……` de seis dígitos en `orb.js` |
| el traje llega al montar, no sólo al cambiarlo | `orb.js` lee las dos variables CSS con `getComputedStyle` al montar; `telefono.js` llama a `orb.vestir(p, s)` desde `ponVariables` y `vistePuesto()` aplica el `puesto` que trae `lista` al abrir CORT |
| el atuendo no es decoración: hasta el shader y la rejilla | `uColor` del shader de partículas y de las chispas, los cuatro anillos del suelo, la rejilla (centro y líneas) y las ondas de choque también se tiñen; las texturas pasan a blanco con alfa para que el tinte mande |
| la burbuja se puede **arrastrar** y no se queda en medio | `ACTION_MOVE` con `getRawX()/getRawY()`, umbral de 6 dp para no confundir toque con arrastre, `updateViewLayout` y `pegaAlBorde()` al soltar |
| el toque sigue abriendo CORT | si no hubo arrastre, `performClick()` en `ACTION_UP`; la burbuja conserva `setOnClickListener` y el extra `PIDE_ESCUCHAR` |
| azul translúcida, no molesta | `RadialGradient` de tres paradas con alfa (`0xE6`/`0xC8`/`0xF0`), aro y brillo; al reposo baja a `ALFA_REPOSO = .62` **una sola vez** (`setAlpha`), sin bucle de animación |
| el modo juego sigue mandando primero | la comprobación `if (juego(app))` va **antes** de `montarYa(app)`; costura [32.d] mide el orden y prohíbe `ValueAnimator`/`requestAnimationFrame` |
| el agua existe y se puede apagar | `#agua` en `index.html` con `@keyframes agua-ola` de `transform`; con `html.glass` se esconde y con `html.freno` se queda sin animación, sin `filter` y con opacidad `.08` |
| el freno tiene disparador | `pantallas.js` pone `html.freno` con **poca RAM** (`navigator.deviceMemory <= 2`, que es 2 para el portátil de 1,8 GiB) **o** en modo juego; `html.freno` también quita el `backdrop-filter` de paneles, ventanas, chips y FAB |
| la prueba visual no viaja al APK | `ui/sonda-colores.html` monta el orbe real, recorre los seis trajes y compara contra `orb.colores()`; `compilar.sh` sigue borrando `sonda-*.html` |

Cifras medidas en el portátil: `prueba-colores.mjs` **28/28**, la costura en **301
`ok`** (6 del sector [32]) y `scripts/taller-f17.sh` con **19 mutaciones que caen las
19**, cada una nombrando la comprobación que la echaba de menos; dos de ellas corren la
prueba de node entera (`la partícula se congela`, `el secundario se cuela`). Las seis
paletas se midieron **sin GPU**: la derivación vive en un módulo puro y el navegador no
hace falta para saber que Matrix no deja ni un color de Cortana.

**Lo que NO se puede medir aquí, y se dice sin adornos:**

- Cómo se ve. Que Three.js pinte el tinte es una línea por material y la costura la
  vigila, pero el brillo, el contraste y si el agua emborrona la lectura **sólo se ven
  en su teléfono** (o con la sonda en su navegador).
- El arrastre real. El arrastre está medido en código (`ACTION_MOVE`, coordenadas
  crudas, borde), pero que el dedo no confunda toque con arrastre en su pantalla es de
  aparato. El umbral elegido son 6 dp.
- La posición no se recuerda. Al apagar y volver a encender, la burbuja arranca otra vez
  centrada a la derecha; guardarla pediría escribir en preferencias en cada arrastre y
  no se ha hecho en esta fase.
- La opacidad de reposo es **una sola vez**: se pone al montar y tras cada toque, no hay
  temporizador que la repita. Menos batería, pero si el sistema la devuelve a opaco no
  se corrige sola.
- La 1.1.4 exacta no está en este repo (era del cuerpo Kotlin, sin `.kt` en disco): la
  burbuja se reconstruyó por el comportamiento que ella describió —azul, transparente,
  arrastrable, que no molesta—, no copiando su código.
- `Flotante.java` **no se compiló en el portátil**: aquí no hay `android.jar` y
  `compilar.sh` exige `ANDROID_HOME`. El `javac` de verdad es el del pipeline; hasta que
  corra, el arrastre y el gradiente están revisados a mano, no compilados.
- Nada de esto llega a su teléfono hasta que salga la Release: **el pipeline no se ha
  corrido con F17 todavía**.
