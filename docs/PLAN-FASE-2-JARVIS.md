# FASE 2 · JARVIS — dos chats, un cerebro con manos y una boca que ella elige

26 oct 2026 · ronda 2.15.0 · **estado: plan, sin tocar código todavía**

Nace del mensaje de la dueña del 26/10 con tres videos. Ésta es su parte textual,
copiada sin corregir para que no se le cambie el sentido:

> «empiezas por el chat se tiene que parecer al del video y pues otro apartado es donde
> hará el chat real con entorno de código y eso en sí la primera será como para conversar
> con CORT y funcione de esta misma forma luego el otro chat donde tendrá copiloto
> entorno de código todo igual que QODER una réplica la interfaz de escritorio para PC y
> la de android adaptada que CORT tenga una ampliación en su cerebro para ejecutar esas
> funciones de ejecutar cosas en tras en terminal enviar mensajes y responde como tú de
> forma profesional en cambio en la primera de conversación será como en el del video y
> será para darle órdenes y la respuestas sean semi cortas pero medidas o desarrolles el
> JARVIS con estos referencia y ese video el primero estilo logica modelos como funcionara
> en pc y en android telefono y el segundo sera todo lo que sera logica cerebro
> automatizacion y pasos para crear un JARVIS haras eso en base esos dos videos sera la
> proxima fase vale abarcara todo eso y el tercer video como hablara sera de inteligente no
> tendra limites y luego se agregaran multiples voces y esas cosas en sus ajustes lo
> integras al CORT funcional para ir mejorandolo con su rediseño»

Traducida a cosas que se pueden construir y probar:

1. **Dos superficies de chat, no una.** Una de conversación y órdenes (estilo el video,
   respuesta **semi-corta pero medida**), y otra de **trabajo con código** (réplica de
   este entorno: hilo de pasos, terminal, aceptar/rechazar).
2. **Réplica en dos tamaños**: escritorio para el PC y adaptada para el teléfono.
3. **Una ampliación del cerebro**: ejecutar en segundo plano / en terminal, enviar
   mensajes, y contestar **en modo profesional** (como contesto yo aquí).
4. **La boca**: múltiples voces en Ajustes, y —del video 3— avisar **por llamada**.
5. El video 2 (los siete pasos) es el esqueleto de la fase.

La evidencia de los videos, con fotogramas y transcripciones, está en
`docs/REFERENCIAS-VIDEOS-JARVIS.md`. Éste plan no repite mediciones: las cita.

---

## 0 · La puerta, antes de nada

La Fase 1 no está cerrada: faltan el paso 1.3 (la placa de arriba) y el 1.5 (ejecutar y
confirmar), y su puerta dice que **sin las cinco cosas funcionando no empieza la Fase
2** (`docs/PLAN-FASE-1.md` §4). Este plan se escribe ahora porque ella lo pidió, pero
**sus pasos no arrancan hasta que la Fase 1 esté aprobada por ella a ojo**. Lo único que
se hizo ya de este plan es el paso 1.4 (el manto de la charla), porque es Fase 1 y es la
superficie A de aquí abajo.

El hueco más grande del video 2 —el paso 7, «ponerlo a trabajar solo»— no tiene ni una
línea de planificador en el repo (buscado: `grep -rni "apscheduler|cron|schedule"
backend` sólo devuelve `crontab -l` como comando de lectura en `copiloto.py:87`). Eso
define el orden del §7: primero las manos, luego la agenda.

---

## 1 · Inventario honesto: qué hay ya, con archivo y línea

Lo que ella llama «ampliación del cerebro» no empieza de cero. Empezar de cero habría
sido la señal de que no leí mi propio repo.

| lo que pidió | lo que ya existe | qué le falta |
|---|---|---|
| chat estilo video (superficie A) | `ui/css/jarvis.css` + el interruptor en `ui/js/pantallas.js:642-680` (paso 1.4) | nada: está montado, pendiente de su visto |
| respuestas semi-cortas y medidas | `FRASE_JARVIS` en `pantallas.js:651`, colada dentro del mensaje en `:854` | el núcleo no tiene `num_predict`: la longitud la pide la cara, no la impone el motor |
| darle órdenes | `POST /api/command` (`backend/app/main.py:128`) → `actions.run_command` (`actions.py:80`): nota, abrir carpeta/archivo, sitio, música, leer, recordar | la cara decide a ojo cuándo va a `/api/chat` y cuándo a `/api/command` |
| copiloto que ejecuta | `backend/app/copiloto.py`: `plan()` en `:288`, `ejecutar()` en `:333`; rutas `main.py:521/528/534` | **sólo comandos de lectura** (`LEE_SOLO` `:54`, `SUB_LECTURA` `:77`, `NUNCA` `:98`); no hay cara que enseñe el hilo |
| entorno de código | `ui/js/pantallas.js` tiene su hoja `codigo` y el árbol/archivos del PC (`/api/tree`, `/api/lee`, `/api/files`) | no hay editor, ni diff, ni «aceptar/rechazar» |
| ejecutar en segundo plano | `models.py:421` levanta `ollama serve` desvinculado; `sensors.py` usa `Popen` para abrir cosas | no hay cola de tareas ni forma de consultar «qué está corriendo» |
| enviar mensajes | APK: `Acciones.java:106-108` abre WhatsApp (y Business) y `:533` la app de mensajería; `Avisos.java` **sólo lee** la barra de notificaciones; `Telefono.java` marca | **no escribe ni manda**: falta el `ACTION_SEND` con el texto aprobado y el verde pulsado |
| múltiples voces | `VozNueva.java` (contrato 2.1 `ajusteVoz`: lista/poner/predefinida/descargar/probar/estado) y su cliente en `ui/js/telefono.js:653-730`; en PC `backend/app/voz.py` con `VARIANTES` en `:75` | no hay **sección de Ajustes** en la cara nueva: hoy se toca por consola |
| avisar por llamada | `Telefono.java` marca (con `CALL_PHONE`, `AndroidManifest.xml:183`) | no hay regla de urgencia guardada ni disparador |
| modelos en PC y teléfono | 10 · Modelos calcada del video (`PLAN-FASE-1.md` §4.5), `models.py` con reintentos y resanación | nada estructural; sí el tope de contexto en `brain.py` (en manos de ella) |

**Consecuencia:** esta fase es, sobre todo, **caras y permisos**, no motores nuevos.
Donde sí hace falta código de fondo es en dos sitios: la cola de tareas (§5.3) y el
modo profesional del cerebro (§5.4).

---

## 2 · Superficie A — «CORT, óyeme» (conversación y órdenes)

Es la que ya existe con el manto puesto. Su definición, para que no se derrame:

- **Para qué**: hablar, preguntar, mandar cosas del día («apunta esto», «pon música»,
  «¿qué recuerdas de mí?»), voz y micrófono.
- **Cómo contesta**: dos frases, tres como mucho; si falta un dato, dice qué falta en
  vez de inventarlo (`FRASE_JARVIS`). Éste es el modo **de casa**.
- **Qué NO es**: no enseña trazas de comandos, no abre diffs, no propone planes de
  varios pasos. Si la dueña necesita eso, cambia de superficie; no se mezcla.
- **Enrutamiento**: la cara decide entre `POST /api/chat` (habla) y `POST /api/command`
  (hace). Hoy esa decisión está en JS y es a pelo; el paso J2.1 la convierte en una
  regla con prueba: si la frase contiene una orden del diccionario de `actions.py`, se
  ejecuta y **además** se cuenta en la burbuja (qué hizo, con qué resultado).

## 3 · Superficie B — «CORT, trabaja conmigo» (copiloto con entorno de código)

La réplica de este entorno, en dos tamaños. Lo que la hace distinta de la A no es el
color: es que **hay un hilo de pasos con su resultado, y nada se ejecuta sin que ella
lo apruebe**.

### 3.1 Lo que se copia de Qoder (y lo que no)

Del video 1, minuto 2:39 (`docs/referencias/v1-agente-159.jpg`): ventana oscura, arriba
dos desplegables y un selector de modelo, y abajo una fila de botones donde **rojo y
verde son los protagonistas**. Eso es el patrón. De ahí se toman cuatro cosas:

1. **El hilo, no la burbuja.** Cada turno se ve como *petición → pasos → resultado*, con
   el comando exacto de cada paso y su salida recortada. `copiloto.py` ya devuelve
   exactamente esa estructura (`plan()` da los pasos con su `argv`; `ejecutar()` da la
   salida cortada a `SALIDA_MAX = 8000` caracteres, `:49`).
2. **Aceptar / rechazar por paso.** Verde = corre este paso. Rojo = no corre, y se
   enseña escrito para copiarlo. Sin tercero: nada de «aceptar todo» en la primera
   versión, porque un `permito todo` en un equipo que se comparte por Wi-Fi es justo lo
   que el docstring de `copiloto.py` se niega a abrir.
3. **La terminal al lado, no debajo.** En PC: panel de dos columnas (hilo a la
   izquierda, salida bruta a la derecha, colapsable). En el teléfono: una sola columna
   con la salida plegada detrás de un «ver 40 líneas». Mismo estado, dos densidades.
4. **El modelo que respondió, siempre visible** (pie con `source`: `casa | nube |
   local`), porque en esta superficie un modelo u otro cambia lo que se puede confiar.

Lo que **no** se copia: un editor de verdad con líneas y cursor. No hace falta para
gobernar un plan de pasos, pesa en el WebView y `ui/js/pantallas.js` ya tiene hoja de
código con árbol de archivos. Si algún día hace falta editar, entra como su propio paso
con su propia discusión, no de contrabando en éste.

### 3.2 Las dos medidas

| | PC (Electrón/Chromium) | teléfono (WebView del APK) |
|---|---|---|
| ancho | dos columnas, hilo 55 % / salida 45 % | una columna; la salida, plegada |
| botones | Accept/Reject a la derecha de cada paso | los mismos, a **48 dp** de alto y separados (un dedo no es un puntero) |
| teclado | `Ctrl+Enter` ejecuta el paso propuesto | sin atajos: el botón o la voz |
| qué se oculta | nada | la barra de estado del orbe, para que el hilo respire |
| qué no cambia | el estado del paso (`pendiente → corriendo → ok / falló / rechazado`) es idéntico en las dos caras; la diferencia es de espacio, nunca de información |

## 4 · La ampliación del cerebro

Cuatro piezas. Las tres primeras tocan el equipo; la cuarta toca el texto.

### 4.1 Ejecutar en terminal — con la puerta de mando intacta

Hoy: `LEE_SOLO` / `SUB_LECTURA` / `NUNCA` y el archivo `~/.cort/copiloto.json`
(`copiloto.py:145`) que relee en cada ejecución, de modo que **quitar** un permiso
surte en el acto. Se añade un escalón, no se quita ninguno:

- **Escalón nuevo: `ESCRIBE_CON_PERMISO`** — verbos que escriben y que sólo corren si
  están en su `copiloto.json` **y** si el paso se aceptó con el botón verde en los
  últimos `TTL_S` (900 s). Sin botón, ni intento. `mkdir`, `touch`, `git add`, `pip
  list --outdated`… lo que ella nombre.
- **`NUNCA` sigue siendo `NUNCA`** (`rm`, `dd`, `mkfs`, `curl`, `ssh`, `apt`…): ni aun
  permitida se ejecuta en automático. Lo destructivo va por `/api/organizar`, que ya
  tiene su plan + token + confirmación, o se enseña escrito.
- **Nada de `shell=True`**, timeout y salida cortada como hoy, y el `argv` se muestra
  **antes** de correr, tal cual se va a ejecutar.

Por qué tan tieso, otra vez y por escrito: el mismo backend se sirve al teléfono por
Wi-Fi (`scripts/telefono.sh`). Una puerta a ejecutar cualquier cosa en el portátil es
una puerta abierta en la red de casa.

### 4.2 En segundo plano — la cola que no existe

`ejecutar()` es síncrono: mientras corre, la cara espera. Para tareas largas hace falta
un mínimo:

- `tareas.py` (nuevo, sólo stdlib): un `dict` en memoria + un hilo, con
  `POST /api/tarea` (lanzar), `GET /api/tareas` (listar con estado) y
  `GET /api/tarea/{id}` (salida). Cada tarea guarda quién la pidió, su `argv`, su
  estado (`corriendo | ok | falló | cortada`), su salida recortada y su tiempo.
- **El orbe lo dice**: una tarea que corre pone el estado en `piensa` y al terminar
  suelta un chip en la superficie A («terminó: organizar Descargas · 41 archivos»).
- **Límites, no promesas**: un máximo de tareas a la vez (2 en este portátil de 1,8
  GiB), un tope de salida por tarea y caducidad. Si el equipo se reinicia, la cola se
  pierde y **se dice** en la cara; no se finge continuidad.

### 4.3 Enviar mensajes — dicho sin adornos

«Enviar mensajes» tiene tres grados, y hay que decirlos sin adornos porque el video 3
vende el tercero y aquí no se puede prometer:

1. **Abrir la app con el contacto** — ya hecho: `Acciones.java:106-108` abre WhatsApp
   (y Business) y `:533-534` abre la app de mensajería del sistema.
2. **Abrir la app con el texto ya escrito, y que ella toque «enviar»** — **no está
   hecho**: en el repo no hay ni un `ACTION_SEND` con `EXTRA_TEXT` (buscado en
   `Acciones.java`). Es el grado al que apunta esta fase, y no pide ningún permiso: es
   intent explícito, con el texto que la dueña aprobó en la superficie B.
3. **Mandar solo, por detrás** — no. Exigiría ser la app de mensajería predeterminada,
   y **responder desde un lector de notificaciones tampoco tiene API pública estable**:
   `Avisos.java` hoy **sólo lee** la barra (`resumen(int)` en `:190`), no pulsa botones.
   (El comentario de cabecera de `Telefono.java` dice que «desde ahí se puede responder
   a un chat que tenga su botón de respuesta»; eso sólo es cierto con una API de Android
   16, y en los teléfonos de la dueña no está garantizada. Se corrige hacia delante en
   J2.8 en vez de construir encima de esa frase.)
   Añadir el rol de mensajería necesita autorización explícita de ella, y este plan no
   la pide.

Lo que se puede prometer, entonces: «CORT, dile a Samuel que llego tarde» → superficie B
redacta el texto, se lo enseña, ella toca verde, y se abre WhatsApp **con el texto
puesto**. El último dedo sigue siendo suyo, y la cara nunca dice «enviado» si sólo pudo
abrir la app.

### 4.4 «Responde como tú, de forma profesional» — el modo, no el motor

La diferencia entre la superficie A y la B es el registro. Se implementa igual que
`FRASE_JARVIS`: una instrucción que viaja **dentro** del mensaje, porque
`POST /api/chat` sigue aceptando sólo `{message}` (`main.py:116`, modelo `Msg` en
`:108`). El texto del modo profesional:

> Responde como ingeniero senior: primero la decisión, después el porqué en dos o tres
> líneas, y al final lo que hay que comprobar. Si no sabes algo, dilo y di qué dato lo
> resolvería. No reescribas el problema. Si propones un comando, escríbelo exacto.

Y su pareja, que es la que de verdad cambia la respuesta: **un tope de tokens por
petición**. `brain.py` está en sus manos (sin commitear), así que el `options.num_predict`
que falta en `_ollama_chat` se pide cuando esa versión se asiente; mientras tanto la
cara sólo puede pedir, no imponer.

## 5 · La boca y el teléfono

- **Voces en Ajustes** (lo que ella pidió explícitamente): una sección nueva con la
  lista que devuelve `GET /api/voice` en PC o `ajusteVoz{que:'lista'}` en el teléfono,
  cada una **probada de verdad** antes de ofrecerse (`voz.py` ya sintetiza una sonda y
  descarta las que no suenan), más los deslizadores de tono y velocidad que ya existen
  en 07 · Perfil. Antes de tocar esto hay que limpiar el `_suena` duplicado de
  `voz.py:126` y `:161` (código muerto que engaña a quien lea el archivo).
- **Avisar por llamada**: un archivo de reglas (`~/.cort/urgente.json`: qué temas, de
  quién, en qué horario) + el disparador de §4.2 + `Telefono.java`. La regla se
  configura hablando («avísame por llamada si es la oficina»), y **cada llamada se
  anuncia antes de marcar**: la cara dice «voy a llamar a Samuel» y da dos segundos. Sin
  eso, un día marca solo y a las tres de la mañana.
- **Contestar llamadas**: fuera de esta fase, con la razón escrita en `Telefono.java`.

## 6 · Pasos, con su puerta de salida

Versión `2.1x.0` por paso, etiqueta sólo al cerrar la fase (su regla). Ningún paso
empieza si el anterior no está operando.

| paso | qué entrega | puerta de salida |
|---|---|---|
| **J2.0** | (Fase 1) placa 1.3 y flujo 1.5, y su aprobado a ojo | Fase 1 etiquetada |
| **J2.1** | Superficie A enruta órdenes a `/api/command` y cuenta **qué hizo** en la burbuja | una orden real ejecutada y contada; una orden imposible que dice «no pude» sin fingir |
| **J2.2** | La cola de tareas (`tareas.py` + 3 rutas + chips en la cara) | dos tareas a la vez, una cortada a mano, y la cara diciendo la verdad de cada una |
| **J2.3** | Superficie B en PC: hilo de pasos + salida + verde/rojo por paso | un plan de 3 pasos: uno aceptado, uno **rechazado** delante de ella, uno fallido con su salida |
| **J2.4** | Superficie B adaptada al teléfono (una columna, botones de 48 dp) | lo mismo, con el pulgar |
| **J2.5** | El escalón `ESCRIBE_CON_PERMISO` + el modo profesional | un `mkdir` aceptado con verde y **prohibido sin él**; `NUNCA` sigue muriendo aunque esté en `copiloto.json` |
| **J2.6** | Voces en Ajustes (PC y teléfono) + limpieza de `voz.py` | cambiar de voz desde la cara, en los dos aparatos, con la voz probada antes de ofrecerse |
| **J2.7** | Reglas de urgencia + llamada saliente anunciada | una regla guardada hablando y una llamada de prueba que se puede cancelar |
| **J2.8** | Redactar y abrir WhatsApp con el texto escrito (paso 4.3, grado 2) | un mensaje redactado, enseñado, y enviado **por su dedo** |

Cada paso: su suite `scripts/prueba-*.{mjs,py}` enganchada a
`.github/workflows/build.yml` con anotación `::error::`, y sus mutaciones para probar
que muerde. J2.5 y J2.7 son los únicos que pueden pedirle una decisión de permisos, y se
paran antes de tocar el manifiesto.

## 7 · Lo que no se toca

- Su trabajo sin commitear: `CortNative.java`, `Flotante.java`, `MainActivity.java`,
  `brain.py`, `pool.py`, `docs/ALOJAR-CORT.md`, `scripts/prueba-pool.py`. Los pasos que
  necesiten `MainActivity` o `brain.py` esperan a que estén limpios.
- **Sin permisos, servicios ni componentes nuevos en el manifiesto** sin autorización
  explícita. **Ningún puerto expuesto a internet.** Nada de `READ_SMS`,
  `QUERY_ALL_PACKAGES`, `WRITE_CALENDAR` ni `PROCESS_OUTGOING_CALLS`.
- El APK se compila en Actions; nada de instaladores en su portátil. Secretos fuera del
  repo y enmascarados en la cara.
- La cara sigue sin enseñar `undefined` ni estados no confirmados: si el aparato no lo
  dice, no sale.

## 8 · Cuatro decisiones suyas antes de J2.1

1. ¿La superficie B se abre **desde el cajón como una app más** («Trabajo»), o sustituye
   a la hoja `codigo` que ya existe (`ui/js/pantallas.js`, la pantalla `p-codigo`)?
2. El verde/rojo por paso: ¿cada paso se aprueba **uno por uno**, o prefiere «aprobar el
   plan entero» con los pasos de escritura fuera del lote? (Recomendado: uno por uno
   hasta que confíe; luego ella abre el lote.)
3. ¿Le doy al escalón `ESCRIBE_CON_PERMISO` verbos de desarrollo (`git add`, `pip
   install`) o empiezo sólo con los de archivos (`mkdir`, `touch`, `cp`)?
4. La llamada del video 3: ¿su número, o también el de otra persona de confianza para
   avisos cuando ella no conteste?
