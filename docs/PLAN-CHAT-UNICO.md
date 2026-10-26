# PLAN · la superficie `chat` única (una pantalla, tres símbolos)

26 oct 2026 · ronda 2.14.0 · **estado: plan, sin tocar código todavía**
Base: cara `ui/` (misma HTML en PC y en el WebView de Android) · núcleo FastAPI
`backend/app/main.py` · puente Android `apps/apk/src/com/cort/ia/` · contrato
`docs/CONTRATO-PUENTE-2.1.md`

Este documento es la respuesta a un pedido de la dueña y **no ejecuta nada**. Antes de
desmontar una sola ventana quiere ella ver el orden propuesto y aprobarlo.

---

## 1. Lo que pidió, dicho en claro

> «todos los apartados quitarás y harás uno solo que se llame chat y será igual que
> este entorno tuyo Qoder osea chat, otro apartado así normal, pero la pantalla será
> semi negra transparente estilo la interfaz del JARVIS que usamos de referencia y ahí
> agregarás los botones, barras, la barrita de 3 símbolos pegados donde estará
> historial, ajustes etc. todo eso debes saber cómo ordenarlo (…) como OPEN JARVIS de
> la universidad de stanford de github, que tiene muy buen chat y ajustes todo
> ordenado, y ahí también le agregarás tus funciones de copiloto, agregarás modelos de
> todo tipo locales y en línea, en los ajustes conectes api keys y se agreguen (…)
> quiero que sea como un copiloto, investígate y funcione como núcleo»

Y antes de eso, dos cosas más del mismo mensaje:

> «que los modelos también se descarguen en pc y en móviles y que puedan trabajar
> aparte, o sea que el fallo que dice CORT no puede iniciar sin PC, o que con pantalla
> de emergencia, eso no tiene nada que ver»

Cinco exigencias, que son las que ordenan todo lo demás:

1. **Una sola superficie que se llame `chat`.** Los demás apartados dejan de ser
   ventanas.
2. **Pantalla semi-negra transparente**, estilo la interfaz JARVIS de referencia.
3. **Una barra de tres símbolos pegados** con historial, ajustes y lo demás. El orden
   lo decido yo y se propone aquí.
4. **Modelos de todo tipo: locales y en línea**, con sus claves API metidas desde los
   propios ajustes.
5. **Que el PC apagado no corte nada**: que el teléfono y el PC trabajen aparte, sin la
   pantalla de emergencia cruzándose en medio.

---

## 2. Lo que hay hoy, con nombre y línea

### 2.1 Las ventanas (el `dock`)

`ui/index.html:102-113` — once botones, y ése es el listado que hay que reducir a uno:

| id | rótulo | ¿sólo PC? |
|---|---|---|
| `files` | 01 · Archivos | sí (`data-pc`) |
| `env` | 02 · Entorno | sí |
| `chat` | 03 · Canal de voz | no |
| `notes` | 04 · Notas | no |
| `music` | 05 · Música | sí |
| `term` | 06 · Consola | sí |
| `perfil` | 07 · Perfil | no |
| `cerebro` | 08 · Cerebro (muro de recuerdos) | no |
| `modelos` | 10 · Modelos locales (Ollama) | no |
| `optimiza` | 11 · Optimización RAM/caché | sí |
| `ayuda` | 09 · Ayuda, atajos y soporte | no |

Más dos acciones que no son ventana: `Abrir` (carpeta en el explorador) y `Ocultar`
(Esc), y la lámpara de estado `#lamp`.

### 2.2 Las hojas (lo que sale del cajón)

`ui/js/pantallas.js:55-81` — `orbe`, `musica`, `mv` (letra del vídeo), `charla`,
`codigo`, `equipo`, `centro`, `arnes`. Con su propia maquinaria de abrir/cerrar
(`abreHoja` en `pantallas.js:274`, `cierraHoja` en `:262`, el cajón en `:236-253`).

O sea: **hoy la cara tiene dos sistemas de navegación superpuestos** — el `dock` de
once ventanas y el cajón de ocho hojas — y once de esas diecinueve entradas apuntan a
lo mismo con otro nombre. Ésa es la duplicidad que ella quiere quitar.

### 2.3 La puerta «sin PC», que es el punto 5 del pedido

Tres piezas, todas verificadas:

- `apps/apk/src/com/cort/ia/MainActivity.java:355` — en el teléfono **todo** `fetch`
  que empiece por `/api/` se corta antes de tocar la carpeta `ui/` y cae en
  `sinNucleo()`.
- `sinNucleo()` (misma clase, ~`:451-458`) responde `501` con
  `{"error":"sin PC: escribe la dirección de tu portátil en el botón CORT · PC"}`.
- `ui/js/pantallas.js:431-444` — `hayNucleo()` pregunta una vez `GET /api/port` (con
  1,8 s de espera) y recuerda; si no hay, cada hoja sustituye su contenido por
  `sinNucleoFrase()`, que en el teléfono dice «sin tu portátil no hay cerebro que
  consulte…».

**Lo que está mal aquí no es el aviso: es que el aviso ocupe el sitio del trabajo.**
Con el PC apagado el teléfono sí puede: oír (Vosk), hablar (TTS), razonar con la tabla
local de `Cerebro`, mandar órdenes del aparato (volumen, linterna, alarma, abrir),
reproducir música, y —esto es lo que casi nadie sabe— **pensar en la nube y descargar
modelos en el Ollama de otro equipo de la casa**:

- `apps/apk/src/com/cort/ia/Nube.java:78-97` — catálogo de siete proveedores ya
  escrito: `groq`, `openai`, `deepseek`, `mistral`, `qwen`, `ollama`, `anthropic`, con
  sus bases reales y su modelo por defecto. La clave se guarda en
  `SharedPreferences` y **nunca sale** en `estado` (sólo `clavePuesta`, verdad nº 1 del
  comentario de la clase).
- `docs/CONTRATO-PUENTE-2.1.md` §4b — `mente({que:'ollama', accion:'descarga',
  modelo})` ya existe y ya manda cuadros de progreso con `porcentaje`; `lista`,
  `descubre`, `fija`, `borra` y `usa` también. Ollama no cabe en el APK (es Go), pero
  su **cliente** sí, y manda la descarga en el servidor de la casa.

Con esto, el punto 5 del pedido no pide inventar un motor nuevo: pide **dejar de
tapar** lo que ya funciona y quitar la pantalla que lo esconde.

### 2.4 Los ajustes y las claves, que ya existen pero repartidos

- `backend/app/config_store.py:1-9` — config en `~/.cort/cort_config.json`, leída al
  vuelo, pensada literalmente «porque en un teléfono no se puede editar un `.env`»;
  `GET /api/config` **devuelve sólo máscara**.
- Claves que ya tienen ranura: `groq_key`, `gemini_key` (`config_store.py:31-33`,
  `ENV_NAMES:46-47`). Las que faltan para el catálogo del teléfono: `openai`,
  `deepseek`, `mistral`, `qwen`, `anthropic`.
- `backend/app/brain.py:359` — el enrutado de cabeza: `local | ollama | groq | gemini |
  offline`. Ampliarlo a los siete proveedores es seguir la misma forma.
- `apps/apk/.../Nube.java` — en el teléfono el mismo reparto vive en
  `SharedPreferences` (`nube-proveedor`, `nube-base`, `nube-modelo`, `nube-clave`).
  **Dos almacenes, una pantalla**: los ajustes tienen que hablar con el que corresponda
  y no con los dos a la vez.

### 2.5 El copiloto, que ya está hecho y sin pantalla propia

- `backend/app/copiloto.py:1` — «piensa el plan, y sólo ejecuta lo que no puede romper
  nada». `~/.cort/copiloto.json` (`:145`) guarda lo que ella permite y lo que niega.
- `backend/app/main.py:521-540` — tres extremos: `GET /api/copiloto` (qué puede correr
  solo), `POST /api/copiloto/plan` (propuesta con token, no ejecuta nada),
  `POST /api/copiloto/ejecuta` (un paso, sólo lectura, token fresco).
- El mismo patrón `propuesta → token → aplicar` está en `/api/organizar`
  (`main.py:508-518`).

Es decir: **la función del copiloto existe en el núcleo y hoy no tiene un sitio visible
en la cara.** En la superficie `chat` es el hilo de pasos bajo la burbuja.

---

## 3. La referencia externa: OpenJarvis

Lo que copio de ahí es **el orden**, no el código (es otro stack, Next.js y TS, y
nuestro orbe es HTML llano dentro de un WebView).

| lo que hace OpenJarvis | qué significa aquí |
|---|---|
| Una página = zona de charla + panel del sistema al lado | Una superficie; el panel del sistema **no** es una ventana, es lo que saca el tercer símbolo |
| Historial en el almacén local, con sesiones recuperables | `/api/history` (`main.py:170`) + `cort-charla` en `localStorage` (`pantallas.js:465`) ya existen: hay que unirlos en una lista |
| Ajustes en secciones apiladas, una tras otra | Un solo panel con secciones, no ocho ventanas |
| Claves: se escriben, se guardan al salir del campo y **no se vuelven a leer** | Encaja con `GET /api/config` enmascarado: la cara nunca pinta una clave |
| Paleta de modelos con pestañas *instalados · catálogo *nube* | La pantalla de Modelos que ya rediseñé en 2.13.0, con una pestaña más |
| Pie «XRay»: cada respuesta dice qué modelo la produjo | El `de:"casa" / "nube" / "local"` del puente (`CONTRATO §4`) y el `fuente` de `/api/history` |
| Sino de aprobación: propone → aprueba → ejecuta | `copiloto/plan` + `copiloto/ejecuta`, tal cual |

---

## 4. La pantalla

```
┌──────────────────────────────────────────────────────────────┐
│ 10:40:01 · lunes, 26 de octubre          [● orbe]   [⌄ 3]    │  placa fina, sin fondo
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   · burbuja de CORT (semi-transparente, 1 color de acento)   │
│     └ qué hizo: 3 pasos · 2 leídos · 0 escritos   [ver]      │  hilo del copiloto
│   · burbuja de ella                                            │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  [ ≡ ]  [ ⌂ ]  [ ⚙ ]        ⟨ entrada ⟩            [ ⌁ ]     │  la barra de 3
└──────────────────────────────────────────────────────────────┘
```

**Fondo.** Semi-negro transparente de verdad: `rgba(6,14,26,.62)` sobre el orbe. El
`backdrop-filter: blur(...)` **está puesto en duda hasta medirlo**: en C0 se prueba en
el WebView de su teléfono y en el Chromium del portátil, y si el coste de composición
se come los cuadros, se queda sólo la capa translúcida sin desenfoque. Sin desenfoque el
semi-negro sigue siendo semi-negro: el orbe se ve detrás atenuado. El valor de la
opacidad no se decide a ojo: sale de la placa de `sonda-orbe.html`, que ya es
translúcida.

**Una sola capa de navegación.** El `dock` de once botones (`index.html:102-113`)
desaparece como fila permanente; el cajón (`pantallas.js:236`) pasa a ser el contenido
del primer símbolo. No se borra ninguna pantalla: se **reubica**.

## 5. La barra de tres símbolos, y por qué en este orden

Tres botones pegados, abajo a la izquierda, del más usado al más raro:

| # | símbolo | abre | por qué ahí |
|---|---|---|---|
| 1 | `≡` **Historial** | la lista de sesiones y de mensajes (`/api/history` + `cort-charla`), con «seguir aquí» y «borrar esta sesión» | Es lo que se toca cada vez que se vuelve a la cara. Y es la única de las tres que no cambia el estado del aparato |
| 2 | `⌥` **Modo** (lo que ella llama «los apartados») | un abanico de **modos de la misma superficie**, no ventanas: `charla · código · música · archivos · equipo` | Los cinco son *la misma charla* mirando distinto: código manda a `/api/command`, música a `/api/play`, archivos a `/api/tree`. Cambiar de modo no abre una ventana, cambia qué se ve debajo de la burbuja y qué botones acompañan a la entrada |
| 3 | `⚙` **Ajustes** | el panel de una pieza, con las secciones de §6 | Lo que menos se toca y lo que más rompe si está a medias: al final |

Dentro de cada uno, sub-barras de iconos sueltos, nunca más de cinco.

**Lo que se lleva cada apartado viejo** (para que no se pierda una función):

| ventana/hoja de hoy | para dónde se va |
|---|---|
| `chat` (Canal de voz) | modo `charla`, la burbuja misma |
| `charla` (hoja) | modo `charla` — es la misma, se queda ella |
| `codigo` + `term` | modo `código` (consola dentro de la charla, con su propio hilo) |
| `music` + `mv` | modo `música` |
| `files` + `Abrir` | modo `archivos` |
| `env` + `equipo` + `optimiza` | modo `equipo` (entorno, RAM/caché y lo que manda CORT en el teléfono) |
| `notes` | **Ajustes ▸ Notas**, y un botón «fijar» que las sube a la placa |
| `cerebro` (muro de recuerdos) | **Historial ▸ Recuerdos** (`/api/memories`) |
| `modelos` | **Ajustes ▸ Modelos** (con las pestañas de §6.2) |
| `perfil` | **Ajustes ▸ Perfil y claves** |
| `centro` (todas las órdenes) | **Ajustes ▸ Órdenes**, y el hilo del copiloto en la burbuja |
| `arnes` (permisos y puente) | **Ajustes ▸ Arnés** |
| `ayuda` | **Ajustes ▸ Ayuda**, y `?` en la placa |

Once ventanas y ocho hojas → **una superficie, dos barras**.

## 6. Ajustes: las secciones, en el orden en que se necesitan

Una columna, secciones apiladas (como OpenJarvis), con buscador arriba:

1. **Apariencia** — el atuendo (los seis de `Paleta.java`), opacidad del fondo,
   desenfoque sí/no, tamaño del orbe. Aquí entra `vestir()` del paso 1.2.
2. **Voz** — a oír (Vosk, idiomas), a hablar (voces del aparato, tono, velocidad).
3. **Modelos** — ver §6.2.
4. **Claves API** — ver §6.3.
5. **Copiloto** — la lista de lo que puede correr solo, lo negado siempre, y el archivo
   `~/.cort/copiloto.json` (`copiloto.py:145`) como texto editable.
6. **Órdenes** — lo que hoy es `centro`, más el motor `automatiza.js` («cuando X,
   entonces Y»).
7. **Arnés** — permisos, puente, nodos (teléfono ↔ PC ↔ VPS).
8. **Notas** y **Recuerdos** — lo suyo, con «borrar todo» doble-confirmado.
9. **Equipo** — RAM, caché, optimización (`/api/optimize`).
10. **Ayuda** — atajos, gestos, soporte.
11. **Avanzado** — dirección del núcleo, `OLLAMA_HOST`, modo de arranque.
12. **Cuenta** — perfil (`/api/profile`), nombre con que la llama.

### 6.2 Modelos: dos pestañas, no dos mundos

- **En casa (Ollama)** — la pantalla que ya rediseñé en 2.13.0: una línea por modelo,
  `Modèle:` a la izquierda, tamaño a la derecha, barra de progreso y ✕ para cancelar.
  Con la subida de 2.13.0 ya sabe reanudar (medido: corté al 74,5 % y siguió desde el
  blob `-partial` de 193 MB).
- **En la nube** — los siete del catálogo de `Nube.java:78-97`, cada uno con su modelo
  por defecto y su coste dicho en claro. Elegir uno escribe `nube-proveedor` /
  `nube-base` / `nube-modelo` en el teléfono, y `mode`/`*_key` en `cort_config.json` en
  el PC.

**«Que se descarguen en PC y en móviles»**, dicho sin adornos: un modelo **local** se
baja donde está Ollama. En el PC, desde la cara. En el teléfono, la orden ya existe por
el puente (`mente({que:'ollama', accion:'descarga'})`, contrato §4b) y **baja el modelo
en el equipo que hospeda Ollama**, no en la memoria del móvil — Ollama es un servidor
Go que no cabe en un APK. Lo que sí puede correr en el móvil sin PC es el modo nube
(clave + internet) y el modo local de órdenes del aparato. Cualquier cosa que prometa
«el modelo dentro del teléfono» necesita un motor nuevo (llama.cpp por NDK), y eso es
otra fase, con su propia discusión de tamaño, batería y manifiesto.

### 6.3 Claves: cómo entran y cómo se ven

- Un campo por proveedor, **guardado al salir del campo** (sin botón «guardar» que se
  olvida).
- Al escribirse, se envían una sola vez y **no se vuelven a leer**: la cara muestra
  `•••• 24` y un «cambiada hace 3 días». Es lo que ya hace `GET /api/config`
  (`config_store.py:6-7`), y lo que jura `Nube.java` en su verdad nº 1.
- Nunca en un log, nunca en `ultimoFallo`, nunca en un mensaje de Actions.
- Falta por añadir al almacén del PC: `openai_key`, `deepseek_key`, `mistral_key`,
  `qwen_key`, `anthropic_key`, y sus modelos por defecto. Cinco ranuras, misma forma.
- **Cuota**: con la que ella convive (varias IAs, sin tarjeta), el panel de claves
  muestra qué proveedor tiene saldo dicho por él mismo, y el modo `auto` baja de
  proveedor cuando uno falla — el enrutado de `brain.py:359` ya lo hace con tres.

## 7. El «sin PC» quitado de en medio

Qué se toca y qué pasa a ser:

| hoy | mañana |
|---|---|
| `MainActivity.java:355` corta **todo** `/api/*` y responde 501 | El corte se queda **sólo para lo que de verdad necesita el portátil** (archivos, música del PC, optimización, organizar). Lo demás tiene respuesta en el propio teléfono: `mente` por el puente, `Nube` con clave, `Cerebro` local |
| Cada hoja sustituye su contenido por `sinNucleoFrase()` (`pantallas.js:442-444`) | La superficie `chat` **nunca se queda vacía**: la burbuja y la entrada funcionan siempre. Lo que falta se dice en una línea de la placa («sin portátil: archivos y música del PC apagados»), no en una pantalla de emergencia |
| La palabra «emergencia» | Desaparece de la cara. Un aparato que avisa de lo que no hace no está en emergencia |

Límite duro que se mantiene: **esto no añade permisos ni servicios al manifiesto**. El
corte de `MainActivity` es un `if` sobre la URL, y aflojarlo para cuatro rutas no
declara nada nuevo. Si al medir hiciera falta algo del manifiesto, se pide antes.

## 8. Las funciones de copiloto que entran en la charla

Lo que yo hago en este entorno y que aquí tiene traducción directa:

1. **Buscar antes de responder** — `/api/files`, `/api/lee`, `/api/tree` ya existen; el
   hilo de pasos los enseña como «3 lecturas, 0 escrituras».
2. **Proponer y esperar** — `copiloto/plan` con su token; la burbuja muestra los pasos y
   un botón por paso. Nada se ejecuta sin tocarlo ella.
3. **Hacerse cargo del trabajo largo** — una tarea que tarda sale de la charla a
   `Órdenes` y vuelve con su resultado, en vez de bloquear la entrada.
4. **Decir qué modelo respondió** — el pie XRay con `de:"casa"|"nube"|"local"`, que el
   puente ya trae.
5. **Aprender el contexto** — `/api/memories` y `/api/profile`, con un «esto no lo
   guardes» visible.

## 9. Fases, con su puerta de salida

Ninguna avanza si la anterior no está operando (su regla). Cada una: su prueba, su
versión, su commit de mis rutas, nada de APK local.

| paso | qué hace | puerta de salida |
|---|---|---|
| **C0** | La placa y la barra de tres símbolos sobre la cara **actual**, sin mover ninguna ventana todavía | se ve y se toca en PC y en el teléfono; `prueba-costura.py` en verde (salvo el rojo suyo de `Flotante.java`) |
| **C1** | Modo `charla` absorbido: la burbuja pasa a la superficie nueva, historial en `≡` | charlar, oír y hablar sin abrir ninguna ventana |
| **C2** | Ajustes con las 12 secciones, empezando por Apariencia (atuendo → `vestir()`) y Modelos | cambiar de traje cambia **todo** el orbe, medido por `prueba-colores.mjs` |
| **C3** | Claves de los siete proveedores, en PC y teléfono, enmascaradas | una pregunta resuelta por `openai` sin tocar un `.env`, y la clave no aparece en ningún log |
| **C4** | Modos `código`, `archivos`, `música`, `equipo` | los cinco modos sobre una superficie; el `dock` ya no existe |
| **C5** | El «sin PC» reducido a lo que de verdad lo necesita | con el portátil apagado: charla, voz, nube y órdenes del aparato funcionan, y no hay pantalla de emergencia |
| **C6** | Copiloto en la burbuja (propuesta → paso → resultado) | un plan de 3 pasos ejecutado con su token, y un paso de escritura **rechazado** delante de ella |

Una vez cerradas C1–C6, la Fase 1 se etiqueta. Este plan **no** toca `orb.js`,
`hud.css` ni `apps.css` hasta que ella apruebe la superficie a ojo.

## 10. Lo que no se toca, dicho para que conste

- Su trabajo sin commitear: `CortNative.java`, `Flotante.java`, `MainActivity.java`,
  `brain.py`, `pool.py`, `docs/ALOJAR-CORT.md`, `scripts/prueba-pool.py`. **Este plan
  propone cambios en `MainActivity.java` (el corte de `/api/*`) y en `brain.py` (más
  proveedores): los haré sólo cuando ella lo diga y sobre su versión limpia.**
- Nada de permisos, servicios ni componentes nuevos en el manifiesto sin autorización
  explícita. Ningún puerto abierto a internet.
- El APK se sigue compilando en Actions, nunca en su portátil.
- Secretos: archivo local fuera del repo, enmascarados en la cara, fuera de los logs.

## 11. Lo que necesito que decida ella (cinco cosas, y cierro)

**Actualizado el 26/10 con su mensaje de los tres videos.** Tres de las cinco ya
tienen respuesta, y la 5 cambia de raíz:

1. La barra de tres símbolos — **sin responder todavía**, y deja de ser urgente: el paso
   1.4 puso arriba lo que el video de referencia enseña (nombre, estado, y a la derecha
   los dos botones que sí hacen falta: modos ✦ y el interruptor del manto ◐).
2. Los cinco modos en el símbolo 2 — **sin responder**, misma razón.
3. ¿El fondo semi-negro va **sobre el orbe** o sobre negro liso? → **Sobre el orbe.**
   Ella dijo «el chat se tiene que parecer al del video», y en el video el chat va
   encima del fondo animado. Así está hecho: `ui/css/jarvis.css` levanta `#scene` sólo
   en la charla con el manto puesto, y `hud.js` deja el WebGL vivo ahí y lo sigue
   congelando en las demás hojas.
4. «Modelos en el móvil» → **descargar en casa y pensar en la nube sigue siendo el
   camino** (funciona y está probado). Lo nuevo que ella pidió —motor dentro del
   cerebro que ejecuta en terminal y manda mensajes— no es un motor en el APK: es la
   ampliación del backend, y vive en `docs/PLAN-FASE-2-JARVIS.md` §4.
5. «¿Empiezo por C0 o por C2?» → **ninguna de las dos: «empiezas por el chat».** Y ése
   fue el paso 1.4. El orden C0→C6 de §9 queda subordinado a la Fase 2 del plan nuevo,
   que es la que ya dice qué superficie se monta en cada paso.

Lo que su mensaje **añade** y no estaba en este plan: una **segunda** superficie de
trabajo con código (réplica de Qoder, escritorio y teléfono), respuestas semi-cortas y
medidas en la de conversación, múltiples voces en Ajustes y el aviso por llamada. Eso
está en `docs/PLAN-FASE-2-JARVIS.md`, no aquí; este documento sigue siendo sólo la
superficie de conversación.
