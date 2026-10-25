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

Cifras medidas en el portátil: `prueba-colores.mjs` **28/28**, la costura en **303
`ok`** (6 del sector [32], el gemelo 27.f del foco de audio y el [33] de los enlaces) y `scripts/taller-f17.sh` con **19 mutaciones que caen las
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
- `Flotante.java` **ya pasó por un compilador de verdad**: el `job apk` de
  `v0.2.39-demo` lo compiló con `javac` + `d8`, y aquí se comprobó además con el
  `android-34.jar` bajado y un doble de `Oido` (javac salió 0). Eso prueba que compila,
  no que el gesto se sienta bien en la pantalla.
- **La Release ya salió:** `v0.2.39-demo` (run 40124250499, 2026-10-24), con los tres
  APK de la 2.10.0 medidos: completo y núcleo **47.484.933 B** (`a745098b…` /
  `aaa2225b…`), ligero **1.715.748 B** (`89106db2…`), `versionCode` **21000**, la misma
  llave `fa:ab:ef:46…` y `assets/ui/` con **18 archivos**. Lo que falta es que ella la
  instale y mire el orbe, el agua y la burbuja en su teléfono.

## Ronda 2.10.1 · el parche de la cara muerta (2026-10-24)

La 2.10.0 se instaló y la dueña reportó lo que ninguna prueba de escritorio podía
ver: el orbe no cargaba, los botones no respondían, la voz no arrancaba, la pantalla
se veía rojiza y el botón nativo «CORT · PC» estorbaba encima de la píldora. **La
causa era una línea:** `ui/js/hud.js` importa `handleTelefonoEvento` de
`telefono.js` y la función estaba declarada sin `export`. Chromium rechaza **todo**
el grafo de módulos antes de ejecutar nada, de modo que ni `initORB` ni `wireUI`
llegaban a correr; lo rojizo era el agua pintada con su atuendo guardado, sin orbe
delante.

| lo que se cerró | cómo se prueba ahora |
| --- | --- |
| un `import` sin su `export` no puede volver a viajar en un APK | costura **[33]**: resuelve cada `import` relativo de `ui/` contra su archivo y exige que cada nombre exista como `export` (28 nombres, 17 archivos); quitarlo pone la costura en rojo nombrando el enlace |
| un fallo de módulo ya no deja la cara muda | `index.html` importa con `await import()` por partes, usa un orbe de respaldo y pinta el error en una franja visible (`#falla`) |
| el botón nativo «CORT · PC» no vuelve | `MainActivity` lo deja `GONE` y **no** lo añade al layout; la costura [20.e] lo prohíbe y `pantallas.js` ya no manda `menuPC` |
| abrir CORT no depende del PC | `arranca()` carga siempre `INDICE`; `guardarPC(dir)` sólo carga la cara remota en el momento en que ella pulsa Conectar |
| el PC o el VPS se conectan desde Ajustes | **Equipo ▸ 9 · PC o VPS**: `setPc(dir)` para conectar, `setPc('')` para volver, `abreMenu()` para el menú nativo; la sonda comprueba los tres viajes y el rechazo de una dirección sin `http://` |
| la conexión remota se dice con sus límites | la propia hoja avisa: LAN en la misma Wi‑Fi o VPS con `https://` detrás de contraseña/VPN; CORT no trae login propio y no se deja el 8000 abierto a internet |

**Medido en el portátil:** costura **303 `ok`**, sonda de la cara **178/178 sin un
`NO`** (montada con el núcleo de verdad y el puente de mentira), las **7 suites**
Java sobre **336 frases**, `prueba-colores.mjs` **28/28**, mandos **63/63**,
automatizaciones **45/45**, oído **6/6**, talleres F16 **18/18** y F17 **19/19**.
**Publicado:** `v0.2.40-demo` (run 40132928413, los cuatro trabajos en verde), APK
**2.10.1** / `versionCode` **21001**, misma llave `fa:ab:ef:46…`; descargados y
hasheados aquí: completo **47.489.029 B** (`e9e529a1…`), núcleo **47.484.933 B**
(`91859e1e…`) y ligero **1.715.748 B** (`2831d4b9…`). El `export` se comprobó
dentro de los tres, `assets/ui/` sigue con **18 archivos** y **sin `sonda-*.html`**;
el manifiesto no crece (16.208 / 12.792 B) y no hay permisos nuevos.

**Lo que sólo su teléfono puede confirmar:** que el orbe aparezca y gire, que los
botones respondan, que la voz suene, que el dedo distinga toque de arrastre en la
burbuja y que el agua no estorbe la lectura. La sonda prueba la lógica de la cara en
un navegador, no el WebView de su Samsung ni su GPU.

## Ronda 2.10.2 · el orbe con ánimo y el Centro de mando (2026-10-24)

La dueña lo pidió sin rodeos: el orbe «se ve muy genérico» y las funciones «están
regadas, falta más orden profesional». Esta ronda ataca las dos mitades.

**F18 · el orbe deja de ser una bola.** Alrededor del núcleo de partículas hay una
cáscara de energía (Fresnel + cuatro senos de ruido + barrido vertical) y tres arcos
de instrumento que giran a distinta velocidad. El orbe tiene cuatro ánimos visibles
—`reposo`, `escucha`, `piensa`, `habla`— y `hud.js` los manda con la misma lámpara
que ya cambiaba al hablar o al pensar. Todo se pinta desde los **dieciséis canales**
de F17 (cáscara `hilos`; arcos `anillo1`/`hilos`/`anillo2`), así que cambiar de traje
sigue cambiando **todos** los colores: no hay un decimoséptimo canal ni se toca
`Paleta.java`. Con `html.freno` la cáscara y los arcos se apagan, igual que el agua.

**F19 · el Centro de mando.** Una pantalla nueva (`⌘ · Centro`, también por voz) que
junta las **91 intenciones / 736 frases** del diccionario generado, las hojas de este
aparato y las herramientas del cajón: **107 filas** con búsqueda que pliega tildes y
filtros por capa (mando 41, razón 26, casa 13, nube 11). Tocar una orden no inventa un
camino nuevo: manda su frase de ejemplo por `cort:orden` y `hud.js` la entrega al
**mismo `send()` que la voz**.

| lo que se cerró | cómo se prueba ahora |
| --- | --- |
| el orbe tiene cuatro ánimos y un nombre desconocido cae a reposo | costura **[34]**: exige `reposo/escucha/piensa/habla` y que `estado(nombre)` devuelva el puesto o `reposo` |
| la cáscara y los arcos no vuelven al cian de fábrica con otro traje | costura [34]: exige que `aplica()` pinte `shellMat` con `c.hilos` y los arcos con `anillo1`/`anillo2` |
| el freno de poca RAM también apaga la mitad nueva | costura [34]: exige `shell.visible = !frenoOn` y `a.m.visible = !frenoOn` |
| la lámpara de la cara llega al orbe | costura [34]: `ORBE_ESTADO` traduce `pensando: 'piensa'` y `setState` llama a `orb.estado()` |
| el Centro ejecuta lo que enseña | costura [34]: importa `DICCIONARIO`/`TOTALES`, pliega tildes con NFD, no escribe frases a mano y despacha `cort:orden` con `b.dataset.frase`; `hud.js` lo recibe en `send()` |
| la hoja del Centro se ve, no queda negra | `hud.css` lleva su regla `display:flex` y la sonda mide `getComputedStyle(...).display === 'flex'`; el cuerpo va en `display:block` para que los chips no se compriman |
| el Centro no ofrece lo que el aparato no tiene | `ir('centro')` lo pinta con `visibles()`, no con una lista fija; en el PC se caen Música y Equipo |
| las quince promesas no son decoración | taller **F18**: 15 mutaciones, una por promesa; las 15 caen nombrando su comprobación |

**Medido en el portátil:** costura **307 `ok`** (sector [34] nuevo), sonda de la cara
**187/187 sin un `NO`** (incluye hoja visible, 107 filas, búsqueda, filtros y la orden
que viaja), las **7 suites** Java sobre **336 frases**, `prueba-colores.mjs` **28/28**,
mandos **63/63**, automatizaciones **45/45**, oído **6/6** y talleres F16 **18/18**,
F17 **19/19** y F18 **15/15**.

**Publicado:** `v0.2.41-demo` (run **40140931041**, los cuatro trabajos en verde), APK
**2.10.2** / `versionCode` **21002**, misma llave `fa:ab:ef:46…`; descargados y
hasheados aquí: completo **47.493.193 B** (`67515c90…`), núcleo **47.493.193 B**
(`663679b5…`) y ligero **1.724.008 B** (`d8db709f…`). Los tres dicen `INSTALABLE`;
núcleo y ligero, **21 permisos y cero `BIND_*`**; el completo, **28 y 4**. La cara
embebida sube a **19 archivos** (entra `js/centro.js`, 8.620 B; `assets/ui/` queda en
1.955.467 B sueltos y 468.786 comprimidos), **sin `sonda-*.html`**, y el manifiesto no
crece (16.208 / 12.792 B).

**Lo que sólo su teléfono puede confirmar:** que el WebGL del APK dibuje la cáscara
con fluidez, que el freno de poca RAM la apague, que el Centro se desplace con el dedo
y que una orden tocada responda en voz alta. La sonda mide la lógica de la cara en un
navegador de escritorio, no la GPU ni el WebView de su Samsung.

## Ronda 2.11.0 · la música obedece, la charla se viste, la cámara abre y el Arnés se ve (2026-10-25)

La dueña trajo la lista sin adornos: «en el reproductor le doy los botones de la
flecha y sigue a múltiples canciones y nunca se para», «que reproduzca música
directo del reproductor predeterminado del teléfono o PC —VLC, Lark Player—», «la
burbuja de chat no se ve como la de la 1.1.4… no se oculta ni se pone transparente
cuando anda inactiva», «necesito agregarle arneses… rediseñar la arquitectura y
visión de CORT», «ni siquiera los sensores de la cámara funcionan». Esta ronda
cierra las cuatro, en el orden en que duelen.

**F20 · el reproductor deja de irse solo.** Estaba medido en el código, no en la
queja: `siguiente()` se llamaba desde dos caminos casi a la vez (el toque y la
terminación de la pista anterior) y `onError` encadenaba saltos hasta vaciar la
cola. Ahora `Reproductor.mueve(paso, manual)` sella el toque manual durante
`PASO_MIN_MS = 420` y la terminación automática llama con `manual=false` y no
lleva sello; una pista que ya no es la actual no puede mover nada (`preparando`);
y `saltaPorFallo` permite **dos** intentos y luego se para con el motivo escrito
(`aviso`). Aleatorio y repetir son estado, no decoración: `colaOriginal` guarda
el orden de llegada para poder deshacer el barullo, `modoAleatorio` conserva
delante la pista que suena y `modoRepetir` cyclea `0 se para / 1 cola / 2 esta
pista`, todo guardado en `SharedPreferences` (`musica_aleatorio`,
`musica_repetir`). Y para «reproduce con tu reproductor» existe
`Reproductor.abrirFuera`, que entrega el `content://` de la pista con
`ACTION_VIEW` y `FLAG_GRANT_READ_URI_PERMISSION`: lo abre VLC, Lark o el de
Samsung; si no hay predeterminado, sale el cuadro del sistema. No se copia
ningún archivo y no se pide ningún permiso. El puente expone `musicaExterna()`,
`musicaAleatorio()` y `musicaRepetir()`.

**F21 · la charla con cara y la burbuja de la 1.1.4.** `burbujaCharla` copia la
*estructura* de OpenJarvis —avatar, cabecera, acciones por mensaje (copiar, leer
en voz alta, guardar), `burbujaPensando` con los tres puntos mientras contesta el
modelo y `md()` con Markdown corto y escapado— sin arrastrar sus dependencias. La
burbuja flotante vuelve a ser el círculo azul translúcido que a ella le gustaba:
`ALFA_REPOSO = .28f`, el icono de la app **dentro** del cristal (leído de `mipmap`
por nombre, porque el pipeline sin Gradle no genera `R.java`; si faltara queda el
cristal y nunca un cuadro negro), y al soltar el arrastre **no salta al borde**: se
queda donde ella la dejó.

**F22 · la cámara, que no era un problema de sensores.** El WebView negaba
`getUserMedia` porque la cara lo llamaba **antes** de que Android concediera
`CAMERA`; el `NotAllowedError` no se enseñaba en ningún sitio. Y había un segundo
medio del fallo: `onPermissionRequest` del `WebChromeClient` concedía
`peticion.getResources()` **a ciegas** —la página pedía `VIDEO_CAPTURE`, el WebView
decía «sí», y como el sistema nunca había dado `CAMERA` el vídeo reventaba igual—.
Ahora sólo se concede lo que el aparato ya tiene concedido, lo que falta se pide en
ese instante con `pidePermiso("camara")` (y `CortNative.permiso` lo sabe medir en
las dos grafías, `camara` y `camera`), y si no hay nada que conceder se
`deny()` en vez de prometer. La vista real se pinta en el lienzo con `drawImage` y
MediaPipe pasa a ser **opcional**, desde el CDN, con `selfieMode:false` para que
las coordenadas cuadren con el espejo del CSS. Si el CDN no carga, la hoja dice
`cámara sí · gestos no` en vez de prometer dedos. Un `turno` corta los bucles
duplicados —era lo que dejaba la cámara encendida—.

**F23 · el Arnés.** Es lo que ella pidió como «arnés» mirando Open Claw y Hermes
Agent, pero con una regla: **el Arnés no ejecuta nada**. `ui/js/arnes.js` es un
módulo puro que lee cinco voces del puente (`capacidades`, `memoria`, `bgStatus`,
`musicaEstado`, `hasPermission`) y cuatro endpoints del núcleo (`/api/port`,
`/api/status`, `/api/history?n=40`, `/api/memories`), y pinta seis cajas —Nodos,
Herramientas, Sesiones, Memoria, Salud, Puerta—. Las cuentas (91 intenciones, 736
frases, 41/26/13/11 por capa) salen de `TOTALES` del diccionario generado, no
escritas a mano. Pinta lo local **antes** de esperar al portátil, con tope de
1800 ms, y si el núcleo calla lo dice con esas palabras: «no entregó su estado del
cerebro» en vez de «Ollama no». Los ejemplos que enseña se mandan con
`cort:orden` al mismo `send()` de la voz, y nada más. La arquitectura completa,
con lo que **no** promete (varias sesiones, agentes autónomos, nodos remotos,
Ollama dentro del APK), está escrita en [`ARNES-CORT.md`](ARNES-CORT.md).

| lo que se cerró | cómo se prueba ahora |
| --- | --- |
| un toque de flecha mueve **una** pista | sonda de la cara (apartado de Música: «un toque, un paso», con un puente de mentira que cuenta las órdenes mandadas); en Java `mueve(1, true)` lleva el sello de 420 ms y la terminación llama con `false` |
| una pista ilegible no barre la cola | `saltaPorFallo` con tope de dos intentos y `aviso` escrito, que la sonda lee en `musicaEstado()` y lo enseña |
| aleatorio y repetir son estado, no dibujo | sonda: `musicaAleatorio()` y `musicaRepetir()` devuelven la frase del aparato y la caja cambia; en Java `colaOriginal`, `modoAleatorio` y `modoRepetir` (0/1/2) persisten en `SharedPreferences` |
| «que suene en tu reproductor» existe y no miente | costura **[28]** (ningún botón de la cara puede llamar a un método que Java no tenga: `musicaExterna`, `musicaAleatorio` y `musicaRepetir` están en `CortNative.java`) + sonda; en Java `abrirFuera` usa `ACTION_VIEW` con chooser de regalo, y el `-firma.txt` del envase **confirma por medida** que el manifiesto sigue en 21 permisos y cero `BIND_*` |
| la cámara pide permiso antes de abrirse | costura **[35]**: orden permiso → `getUserMedia` → `drawImage` → modelo, medido con dobles, y `ui/sonda-camara.html` (13 comprobaciones) lo recorre en el navegador |
| si MediaPipe no carga la hoja lo dice | costura **[35]**: exige la frase `cámara sí · gestos no` y que `selfieMode` vaya en `false` |
| la burbuja es la de la 1.1.4 | costura **[32]** (renglón «F17/F21 · la burbuja»): icono dentro del cristal, `ALFA_REPOSO = .28f` y arrastre que **no** salta al borde |
| el Arnés lee, no inventa | costura **[36]**: las cinco voces y los cuatro `/api` presentes, `TOTALES` importado, cero cuentas a mano, pinta antes de esperar al PC y **no** llama a `requestPermission` |
| el Arnés no manda órdenes raras | costura [36]: sólo `cort:orden` con la frase que enseña y `ir?.('centro')`; su hoja tiene regla de visibilidad propia y luces verde/ámbar/apagada |
| la hoja del Arnés se ve y se desplaza | sonda 5d: seis cajas, 91/736, 41/26/13/11, sesión de 3 mensajes, memoria del puente, Salud con sus siete filas y Puerta con las siete hojas; cuerpo en `display:block` con scroll |
| el documento no vende humo | costura [36]: `docs/ARNES-CORT.md` tiene que decir qué **NO** promete y nombrar las 91 intenciones y las «varias sesiones» como pendiente |

**Medido en el portátil:** costura **314 `ok`** con **0 `NO`** (sectores [35] F22
y [36] F23 nuevos), sonda de la cara **213 comprobaciones sin un rojo** (entra la
sección 5d del Arnés), sonda de la cámara **13/13**, taller F23 **12 mutaciones y
las 12 caen** nombrando la comprobación que falta, `prueba-colores.mjs` **28/28**,
mandos **63/63**, automatizaciones **45/45** y los `.java` del APK parsean con
**0 errores**.

**Publicado:** `v0.2.42-demo` (run **40161626985**, los cuatro trabajos en verde:
`apk`, `build windows`, `build ubuntu`, `release`), APK **2.11.0** /
`versionCode` **21100**, misma llave `fa:ab:ef:46…`. Descargados y hasheados aquí,
exactos a su `-firma.txt` y con el CRC íntegro: completo **47.509.644 B**
(`4d392040…`, 55 entradas, 62.268.978 B sueltos), núcleo **47.509.644 B**
(`87b1642e…`, mismo peso comprimido por el relleno de alineación, 62.265.562 B
sueltos) y ligero **1.740.459 B** (`4fc7f8dc…`, 50 entradas, 4.834.619 B sueltos,
cero `.so` y cero modelo). Los tres con veredicto `INSTALABLE`; el núcleo y el
ligero, **21 permisos y cero `BIND_*`**; el completo, **28 y 4**. La cara embebida
sube de **19 a 20 archivos** (entra `js/arnes.js`, 14.481 B) y es **byte a byte**
la del commit `97441d8`; sigue **sin `sonda-*.html`**. El crecimiento sobre la
2.10.2 es de **16.451 B de archivo** en los tres envases: 37.224 B de cara nueva,
5.380 B de dex (las clases de F20/F22) y 186 B de las dos entradas de `META-INF`
que enumeran la entrada extra. **El manifiesto no crece** (16.208 / 12.792 B) y no
hay permisos nuevos: la cámara usa el `CAMERA` que CORT ya declaraba.

**Lo que sólo su teléfono puede confirmar:** que el WebView abra la cámara de
verdad y se vea el movimiento, que la flecha salte una sola canción y se pare, que
VLC o Lark Player acepten la pista entregada, que la burbuja se vea como la de la
1.1.4 con el dedo arrastrándola, y que el Arnés pinte sus seis cajas con el
portátil encendido y conectado a la misma Wi‑Fi. La sonda mide la lógica en un
navegador de escritorio, no el WebView ni la GPU de su Samsung.

## Fase 0 · paso 0.1 · leer OpenJarvis antes de tocar nada (2026-10-25)

La dueña entregó el **mega prompt v2** con el método nuevo: una fase por sesión, un paso
por sesión, plan y OK antes de implementar, informe al cerrar, y **fase 0 de sólo lectura**
antes de tocar el código. Este es el paso 0.1. **No se cambió ni una línea de `apps/apk`,
`ui/` o `backend/`** — por eso no sube el `versionCode` ni hay nada nuevo que instalar:
sigue la 2.11.0.

Se leyó el clon local (`/home/Sandra/OpenJarvis`, commit `a6dcf84`) en sus cuatro sitios:
la cara (`frontend/src/`), el arrancador Rust (`frontend/src-tauri/src/lib.rs`), el paquete
Python (`src/openjarvis/`) y las páginas de `docs/architecture/*`. El resultado es
**`docs/referencia-openjarvis.md`**, con cada afirmación suya en `archivo:línea`.

**Lo más valioso del paso no es lo que se toma, es lo que se cae.** El mega prompt daba
por tomado de OpenJarvis cuatro cosas que **él no tiene**:

| lo que se esperaba de la referencia | lo que hay en su código |
| --- | --- |
| barra de progreso al descargar un modelo | sólo spinner con «Downloading...» (`CommandPalette.tsx:428-430`); el progreso real (`pct = done/total`) vive en la **CLI** (`cli/model.py:169-186`) |
| pausar / reanudar / cancelar una descarga | no existe en el repo; el escritorio llama a Ollama con `stream: false` y 600 s de timeout (`lib.rs:2429-2436`) |
| comprobar espacio libre antes de bajar | no se hace; sólo umbrales de RAM (`lib.rs:22-30`, `min_vram_gb`) |
| pool de proveedores con cuotas | una clave por proveedor (`engine.md:165-168`); sin cuotas ni recambio |

Y tres cosas **sí** aprovechables, medidas: las **fórmulas de hardware**
(`core/config.py:288-308`: GPU `vram×unidades×0,9`, sin GPU `(ram−4)×0,8`, niveles
2B/4B/9B/27B, peso estimado `param_b×0,5×1,1` GB), la **transparencia por mensaje**
(`Chat/XRayFooter.tsx:28-49` dice motor, `model_id`, tiempo y tokens) y el ciclo
**proponer → aprobar → ejecutar** con caja aislada `--network none`
(`tools/proactive_tools.py:5-20,119`). La Charla que le gustó a la dueña persiste en
`localStorage` (`lib/store.ts:37,57-92`) con el título en los primeros 50 caracteres
(`:420-424`) y **sin renombrar, sin buscar por contenido y sin exportar un chat suelto**:
eso de T6 lo tendremos que inventar nosotros.

**Cómo afecta al plan.** La pantalla «Cerebro» (Fase 2, T7) se dibuja sobre estas
conclusiones: catálogo fusionado (lo instalado en el motor + lo descargable), progreso **por
capas desde el NDJSON de Ollama** —que ya sabemos sumar desde la 2.9.0—, y pausar /
cancelar / espacio libre como **aportes nuestros**, no como copia. El pool de T20 se
diseña desde cero. Quedan **0.2** (mapa del repo) y **0.3** (línea base medida) para
cerrar la puerta de la Fase 0.

**Lo que sigue sin comprobar:** no se ejecutó la app; los `.deb` y `.AppImage` de
`~/Descargas` no se abrieron, y el `JARVIS-HRZ-3.1.0.exe` es otro proyecto. Nada de su
código ni de sus recursos pasó a CORT: es Apache-2.0 y aquí quedó sólo el análisis.

## Fase 0 · paso 0.2 · mapa del repo en `docs/mapa-del-repo.md` (2026-10-25)

Segundo paso de la fase de sólo lectura. Se midió el repo sobre el disco —`git ls-files`,
`wc -l`, `du -sh`, `grep -c` y lectura de cada línea citada— y salió
**`docs/mapa-del-repo.md`**, once secciones con sus `archivo:línea`. **Otro paso sin tocar
código**, así que sigue la 2.11.0 / `versionCode` 21100 sin subir.

**Tres cifras que estaban mal y aquí quedan corregidas.**

| lo publicado / lo que parecía | lo medido |
| --- | --- |
| «85 métodos del puente» (lo que sale de `grep -c`) | **83**: dos están dentro de comentarios de javadoc (`CortNative.java:52` y `:1632`) |
| «28 permisos y 4 servicios `BIND_*`» | **24 `<uses-permission>`** (`AndroidManifest.xml:110-210`) + **5 servicios** protegidos por **4 cadenas `BIND_*` distintas** (`.Asistente` `:372` y `.Sesiones` `:385` comparten `BIND_VOICE_INTERACTION`). El auditor (`audita-apk.sh:244-259`) cuenta cadenas del `strings` binario, así que **el número cuadra y la palabra «servicios» no** |
| «T3 (íconos) está por empezar» | Está **a medias**: `ui/js/icons.js` ya trae **24 íconos SVG de línea**, pero sólo lo consumen `index.html` (11 `data-ic=`) y `hud.js` (21 `ic(`). Quedan **135 glifos a color en 9 archivos** (39 distintos) |

**Dos cosas que no son bugs sino decisiones pendientes de la dueña.** `v0.2-demo` y
`origin/main` **no tienen ancestro común** (`git merge-base` vacío): 100 commits la nuestra
frente a 143 de `main`, parada el 2026-10-17 y con otra arquitectura (`AGENTS.md`,
`services/`, `packaging/`, etiquetas `v0.15.1`…`v0.17.0`, **sin `apps/apk/src/com/cort/ia/`**).
`main` es la rama por defecto de GitHub, así que quien entra al repo ve otra README. Y
**no existe un script que corra las 21 suites en fila**: lo más cerca es el job `apk` del
workflow (`build.yml:152-399`), que no corre en este portátil porque exige SDK de Android.

**Y un choque entre la ficha T1 y lo que ya está escrito a propósito.** La burbuja que ella
eligió (58 dp, sin icono) contradice dos cosas de `Flotante.java`: el icono que la 2.11.0
metió dentro del cristal (`:468-487`) y el **latido apagado deliberadamente** para no gastar
batería en un teléfono de dos núcleos (`:37-38`). Se documenta aquí en vez de improvisarlo
en el paso 1.1.

**Para qué sirve, en concreto.** La sección 10 del mapa deja cada ficha con su dirección:
T1 → `Flotante.java:89/91/93/95/332/351/401-404/456/468-487`; T2 → el `v0.2` fijo de
`ui/index.html:42` que sólo se corrige si el backend responde (`hud.js:93-96`) —casi
seguro lo que ella ve como «versiones raras»; T3 → la trampa de `fill()` (`icons.js:36-37`,
sólo rellena al cargar, no el HTML generado después); T15/T16 → la cifra 91/736 escrita a
mano en cuatro sitios fuera de `TOTALES` (`diccionario.js:1593`); Fase 2 → **las siete rutas
`/api/models*` ya existen** (`main.py:395-432`), así que 2.2 es terminar, no empezar;
Fase 5 → los 24 permisos y las tres regiones recortables (`perfil.py:90-93`), donde pedir
un permiso nuevo obliga a decidir **en qué envase** vive.

**Qué se hizo además de escribir:** se pasó un validador propio que resuelve cada
`archivo:línea` —y cada atajo `:NN` dentro de la misma línea— contra `git ls-files` y
comprueba que la línea exista en ese archivo: **53 citas explícitas, 108 contando los
atajos, 0 inexistentes y 0 fuera de rango**. El paso dejó **cinco correcciones propias**
sobre lo que yo mismo había escrito: una cita que apuntaba a un `import` en vez de al
`new Handler(…)` de `Flotante.java:270`; una ruta `/api/ollama` que no existe y es
`/api/models/ollama` (`main.py:432`); cinco rutas (`support:167`, `weather:291` y las tres
de `copiloto`) que faltaban para que mis agrupaciones sumaran las 45; las 14.310 líneas del
aparato, que eran **sólo los `.java`** y se quedan en **14.926** con `Oido.kt`; y las 14.040
de la cara, que son **las que viajan** —con las tres sondas son 15.533.

**Lo que este paso no hizo:** no ejecutó ninguna suite salvo la costura (para confirmar que
el repo estaba intacto), no compiló, no cambió código, no tocó `main` ni las otras ramas, y
**no arregló** ninguna de las once deudas que describe —eso sería saltarse el método.

## Paso aparte · los comentarios del JDK decían que no había Java, y sí lo hay (2026-10-25)

Salió al medir la línea base: cuatro comentarios del repo afirmaban que este portátil no
traía JDK. **No es cierto.** `keytool` está (`/usr/bin/keytool`, y `dpkg -S` del binario
real lo apunta a `openjdk-21-jre-headless`), y el mismo paquete trae el módulo
`jdk.compiler@21.0.12.1` (`java --list-modules`), que es a lo que cae el `si_javac` de
`prueba-mente.sh:72-76`. La consecuencia práctica es la que importa: **las 7 suites Java
corren en casa** —`MENTE OK: las 7 suites pasan sobre las 336 frases de la tabla`, 60 s—.
`kotlinc` tampoco se baja (`~/.cache/cort-kotlin`, 96 MB) ni el Vosk (`~/.cache/cort-motor`,
77 MB con `vosk-0.3.45.jar`, `jna-5.13.0.jar` y el modelo en español): a `prueba-oido.sh` no
le falta red, le falta RAM.

**Qué se cambió:** sólo comentarios y textos de `ok` —`prueba-llave.sh:6-9`, `:64-65` y su
rama `else` en `:69`, `prueba-costura.py:3-6` y `:481`, `prueba-mente.sh:54`— y cuatro filas
de `docs/mapa-del-repo.md`. **Prueba de que no se tocó lógica:** tras el cambio, costura
**314 `ok` / rc=0**, llave **rc=0**, mente **rc=0**, y `taller-f15.sh` imprime **exactamente
la misma salida** que antes (diff vacío).

**Y el matiz que cambia su `[DECISIÓN]`:** instalar `openjdk-21-jdk` no desbloquea nada que
las pruebas necesiten —lo único que añade es el binario `javac` y banderas como
`--release 11`—. Lo que impide compilar el APK aquí es el **SDK de Android** (`aapt2`, `d8`,
`zipalign`, `apksigner`; `compilar.sh:162` muere sin `ANDROID_HOME`), varios cientos de MB.
O sea: probar Java en local ya se puede sin instalar nada; compilar el APK en casa es una
decisión distinta y más cara.
