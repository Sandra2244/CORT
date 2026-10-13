# Notas de las Release

Texto listo para pegar en GitHub — y desde este corte, **listo para que lo pegue la máquina**:
`.github/workflows/publicar-release.yml` abre la página de Release con el texto de la sección que
corresponda (`scripts/nota_release.py`, con sus 11 pruebas en `test_nota_release.py`). Se dispara
empujando una etiqueta `v*`, empujando `main`, o a mano desde *Actions → publicar-release → Run
workflow* escribiendo la etiqueta. Es idempotente: la etiqueta que ya tenga su página se omite, y la
que no tenga sección se publica con notas generadas antes que con una página muda.

Las etiquetas `v0.7.0`, `v0.8.0`, `v0.9.0`, `v0.10.0` y `v0.10.1` nacieron **antes** de este pipeline,
y como un `push` de etiqueta busca su YAML en el commit de esa etiqueta, quien las convirtió en
Release fue el disparo por `main` — no hizo falta borrar ni recrear ninguna. **Las seis
(`v0.7.0` … `v0.11.0`) están publicadas**, `v0.11.0` desde el 2026-10-11 con su nota recortada de
este documento — comprobado con `curl` a la API pública sin credenciales el 2026-10-12: seis
páginas, y cada cuerpo terminando en su propia línea `**Zip**`—, en
[github.com/Sandra2244/CORT/releases](https://github.com/Sandra2244/CORT/releases). Sigue sin poder
crearse una Release por API desde esta máquina: no hay sesión de `gh` (medido tres veces), ni
`GH_TOKEN` en el entorno, ni `~/.config/gh`.

**La lista de tareas para cortar la siguiente (v0.12.0), en orden** — el orden importa porque el
pipeline lee las notas **siempre desde la rama por defecto**, no desde el commit de la etiqueta:

1. `docs/RELEASE-NOTES.md` tiene la sección `## \`v0.12.0\` — …` escrita, con su línea **Zip** — la
   prueba `test_cada_etiqueta_del_documento_tiene_su_nota` la exige y `make test` lo recuerda.
2. La rama se revisa y **se fusiona a `main`** (fast-forward, sin `--force`: `main` es ancestro de
   `cort-local-verified`, comprobado con `git merge-base --is-ancestor`). Sin este paso la Release
   saldría con `--generate-notes`: el workflow busca la sección en `main`, y ahí todavía no existiría.
3. Se etiqueta el commit de `main`: `git tag v0.12.0 && git push origin v0.12.0`. Ahí se dispara
   `publicar-release.yml` y GitHub ya adjunta solos el código fuente en `.zip` y `.tar.gz` —
   esa es el acta «.zip como proyecto profesional» sin construir nada.
4. Los **instaladores reales** (setup de Windows, APK) no los produce esta máquina —medido y
   justificado en `docs/PLATFORM.md`—: se construyen en un PC Windows con la receta de
   `packaging/` y se adjuntan a la Release ya abierta con `gh release upload v0.12.0 <archivo>`.
   Nunca hace falta tocar nada de datos: la Release son artefactos nuevos; el historial, los
   recuerdos y el `.env` de quien usa CORT viven fuera del repo y una actualización no los borra.

---

## `v0.12.0` — ventanas de vidrio, la voz que no se apaga al cerrar la ventana y la cara del cuerpo

Cuatro cortes en una sola Release, porque venían del mismo sitio: **la cara**. El `avatar CORT` pasa
de ser una foto proyectada a **mirar, gesticular y mover la boca con lo que dice**; la voz se va del
componente al módulo y deja de morirse cuando se cierra su ventana; y el reactor tiene dos estados
más — **reposo** y **escucha**— dibujados en el *vertex shader*. La pila no cambia (Python + React +
Ollama, todo en local), no entra ninguna dependencia nueva y **no se añade ni un marco al
WebSocket**: la expresión viaja dentro del `assistant_message` que ya existía.

- **Ventanas de vidrio en vez de modal** (`ui/Ventana.tsx` + `ui/Ventanas.tsx` + `ui/Muelle.tsx`,
  función 82 ✅): **una sola primitiva** de chrome —tubo arrastrable, rótulo, `⤾` para devolverla a
  su sitio y `✕`— con seis cuerpos dentro (charla · voz · cámara · cuerpo · sistema · ayuda) que
  levantan su acceso en el **muelle**, la única fila de mandos que existe. **No son modales**: se
  pueden tener varias abiertas, la que se toca pasa al frente, `Esc` despide sólo la de enfrente y
  cada ventana de móvil aterriza 46 px más abajo que la anterior. Salen `Hud.tsx`, `Bandeja.tsx` y
  `Panel.tsx` con **29 reglas de CSS duplicadas**. `backdrop-filter: blur(14px) saturate(150%)` sólo
  en ventana y muelle —cada desenfoque cuesta un búfer y esta máquina no tiene GPU—; `:root` pasa a
  tokens (`--glass-*`, `--tint`, `--glow`) y el atuendo por defecto es `night`, el morado de Cortana.
- **La voz es un módulo, no un componente** (`cort/voz.ts`, 582 líneas; funciones 12 · 13 · 11 · 83):
  el arreglo de fondo es un fallo concreto — mientras el reconocimiento vivió dentro de `ui/Voz.tsx`,
  **cerrar la ventana «voz» apagaba el micrófono**, justo cuando se quería dejarlo escuchando y
  mirar la cara. Ahora el estado lo sostiene el módulo, la ventana queda en 100 líneas de botones y
  la escena lee `escucha · habla · oyendo · nivel` **sin pasar por React**. Elige la mejor voz en
  español puntuando las instaladas, limpia el markdown y los emojis que el sintetizador deletrea,
  parte por oraciones para que haya pausas y **cierra el micrófono mientras CORT habla** para no
  oírse a sí misma. **La frase de activación** «OK CORT / oye CORT / hola CORT» vive en
  `cort/activacion.ts`, lógica pura con 12 pruebas que fijan que hace falta el saludo delante y que
  «cortometraje», «corte» y «cortedad» no despiertan a CORT a media conversación.
- **Reposo y escucha** (`scene/Nube.tsx`, función 83): si pasan 30 s sin que nadie toque nada, el
  reactor se deshace en una **nube de ~11 000 puntos** con hilos curvos y un destello central; con el
  micrófono abierto esa misma nube se junta en un **anillo que gira** y se agita con la voz. Todo el
  movimiento se resuelve en el *vertex shader*: la CPU sube ocho uniformes por cuadro y no calcula
  ninguna posición por partícula en JavaScript. Se puede invocar sin esperar: `?demo=reposo`,
  `?demo=escucha`, `?reposo=10`.
- **La cara del cuerpo siente lo que dice** (funciones 29 ✅ y 27 🔨): el `mood` viajaba en cada
  mensaje **vacío**, porque los once sitios de `server.py` escribían `"calm"` a mano y `Vrm.tsx`
  ponía una sonrisa fija al cargar — por eso CORT sonreía siempre. Ahora lo rellena
  `cort_core/affect.py` con **cinco señales medidas** del servidor (una acción que `actions.perform`
  verificó, un plan con un paso caído, un recuerdo nuevo contado con dos `COUNT`, una cuenta atrás
  que termina, un aviso de la iniciativa) y un léxico determinista cuando no hay señal;
  `cort/afecto.ts` lo traduce a los cinco pesos del `.vrm` con **`angry` en cero en los cinco
  estados** — CORT no devuelve el enfado a quien le habla— y caducidad a los 6 s, porque un gesto que
  no se apaga es una máscara. `cort/labios.ts` le agenda la boca al texto: una apertura por grupo
  vocálico, **diptongo cuenta una, hiato con tilde dos**, y el hueco lo elige la puntuación real.
- **Regla 3 de vuelta en la cara**: `make test-web` existió hasta `v0.10.1` con 17 pruebas del riel,
  el rediseño del 2026-10-10 borró el riel y su módulo, y las pruebas se fueron **con lo que
  probaban**. Vuelven y se quedan: **33 pruebas en Node** sin navegador (`scripts/pruebas-web.mjs`
  transpila con el `typescript` que ya era `devDependency`; cero dependencias nuevas, porque un DOM
  simulado cuesta justo la RAM que el reactor necesita).

- **Medido en esta máquina** (2 núcleos, 1,8 GiB, sin GPU): `tsc --noEmit` limpio, `vite build`
  limpio, `make test` → **Ran 353 tests in 72,043 s — OK** y `make test-web` → **33/33 en 5,6 s**.
  En navegador con el core real: **1,21 fps el reactor · 1,09 fps la nube en reposo · 1,09 fps el
  anillo de escucha**; el cuerpo 3D con expresión y boca en movimiento, **12,56 fps**; la cara
  `surprised` sube `0,28 → 0,51 → 0,64 → 0,75` cuadro a cuadro y caduca sola a los 6,5 s; la boca
  recorre `ou 0,73 → ou 0,8 → ee 0,84` y se cierra al acabarse la frase; en reposo, 0 ventanas en el
  DOM; arrastre de 108 → 304 px con `⤾` devolviendo la ventana a su aterrizaje. Capturas:
  `docs/assets/ventanas-vidrio-2026-10-11.png`, `docs/assets/nube-reposo-2026-10-12.png` y
  `docs/assets/nube-escucha-2026-10-12.png`.

**Sin verificar aquí** (regla 11, con su motivo delante): **la boca vista con la voz sonando por un
altavoz real** — `speechSynthesis` no expone ningún flujo de audio que mirar, así que el lip-sync se
agenda desde el texto y esta máquina no tiene ni sink real (*Dummy Output*) ni *Source*: por eso la
función 27 va 🔨 y no ✅; cualquier frase **oída** por el micrófono (función 12) — medido de nuevo el
2026-10-12 con Bluetooth conectado, `wpctl status` sigue sin dar ninguna entrada —, y el reconocimiento
del navegador es además un **servicio en línea** (Chrome habla con Google, Edge con Microsoft):
*escuchar* necesita internet y saca el audio de la máquina, *hablar* no; **el dedo humano** en un
Android físico (esquina de 56 px, que la ventana no tape el reactor a 360 px, y el teclado de Android
con `1`–`6`) y **`Enter` para enviar**, ambos escritos y compilados pero no re-verificados tecla por
tecla; los cuatro cantos de escritorio con el navegador del agente, que no se pudo redimensionar; y
los fps **en un equipo con GPU** — los números de arriba son de este portátil y ninguna cifra es
promesa para otra máquina.

**Zip**: `https://github.com/Sandra2244/CORT/archive/refs/tags/v0.12.0.zip`

---

## `v0.11.0` — la cara por capas y el avatar CORT con vida

La cara que proponía `docs/REDESIGN-UI.md` (analizada frame a frame contra los videos de
referencia de la dueña) **se ejecuta y se porta sobre `main`**, y el `.vrm` deja de ser una foto
pegada: sale del reactor, respira y parpadea. Nada de lo que trajo `main` se pierde en el camino —
la llave de la red, las 327 pruebas y el pipeline de Release siguen donde estaban—.

- **Tres capas en vez de riel**: en reposo sólo quedan el reactor, el reloj y una esquina; la
  respuesta vive 8 segundos como subtítulo; y las herramientas entran en **un único `<dialog>`**
  de cinco pestañas (voz · cámara · atuendos · sistema · ayuda). `ui/Riel.tsx` y `cort/paneles.ts`
  se van, y con ellos sus 17 pruebas —retiradas junto al módulo que probaban, no reescritas de
  relleno—; `make test-web` sale del Makefile con nota de despedida.
- **Teclado re-escrito en la cara nueva**: `1`–`5` abren cada pestaña, `/` salta al campo, `?`
  lista las teclas, `Esc` despide el modal; nada con `Ctrl`/`Meta`/`Alt` y nada mientras se
  escribe, salvo `Escape`.
- **El avatar CORT se materializa**: uniforme `uMateria` (cortina de alfa + filo fresnel durante
  1,8 s), la figura **sube desde el zócalo** y crece de 0,86 a 1 —no aparece de golpe—; brazos,
  cadera, cuello y cabeza en reposo animado; **parpadeo cada 2,4–5,4 s** y media sonrisa vía el
  `expressionManager` de three-vrm; y **tres tamaños** (pequeño · medio · grande) elegibles desde
  atuendos. Todo con las dependencias que ya estaban: ninguna nueva.
- **Se habla desde la propia bandeja**: escribir «activa la cámara» (o «activa el micrófono»,
  «cambia el atuendo», «estado») abre su panel además de enviar el mensaje —los gestos con la
  cámara ya se pueden probar sin buscar el botón—.
- **La llave de la red sigue viva en la cara nueva**: `pintaFaltaDeLlave` está cableado en el Hud
  y en el panel de sistema, y el aviso dice «abre la dirección que imprime `cort.py --lan`».
- Un detalle mentiroso corregido: con sólo `.vrm` en el catálogo la interfaz decía «no hay
  atuendos que mostrar». Ahora el vacío se decide entre imágenes **y** modelos.
- **Medido en este árbol portado**: `npx tsc --noEmit` limpio, `npm run build` limpio y
  `make test` → **Ran 327 tests, OK**.

**Sin verificar aquí** (y así lo firma la regla 11, porque la dueña pidió cerrar el navegador ese
día): la pantalla portada en el navegador, la materialización con un `.vrm` real de los ocho
conectados, el parpadeo, los fps con cuerpo puesto, el teclado y los comandos de la bandeja. La
caminata con animaciones oficiales exige archivos `.vrma` que aún no existen (función 78), y la
mascota que sale de la ventana pide Electron/Tauri, medido y descartado para esta máquina
(función 79).

**Zip**: `https://github.com/Sandra2244/CORT/archive/refs/tags/v0.11.0.zip`

---

## `v0.10.1` — las pruebas dejan de depender del apodo de tu carpeta

Corte de parche, y lo provocó una comprobación honesta: se clonó `main` en una carpeta recién
creada llamada `CORT-nueva` (mismo commit, mismo hash de build) y `make test` respondió
`FAILED (failures=1)`. Nada estaba roto en CORT; lo estaba la manera de contarlo.

- **`test_env.py` afirmaba `ROOT.name == "CORT"`** — o sea el nombre del directorio, no el
  comportamiento. Quien clona con otro nombre, o quien baja el ZIP y se le queda en `CORT-main/`,
  veía fallar la suite entera. Se cambió la afirmación de nombre por tres de **forma**: dentro de
  `ROOT` tienen que estar `Makefile`, `AGENTS.md` y `services/core/cort_core/env.py`, y la raíz que
  ve el cargador tiene que ser la que ven las pruebas, contada desde dos ficheros distintos. Al
  escribirla falló (`parents[2]` en vez de `parents[3]`) — que es exactamente el error que esa
  prueba existe para cazar.
- **El techo de la prueba de red sube de 60 a 180 s.** `test_security.TestLanzadorNiegaRedSinToken`
  arranca el lanzador de verdad (`python -m cort_core.server` con `CORT_HOST=0.0.0.0` y sin llave) y
  espera que se niegue y salga con código 1. **Medido solo: 3,629 s**. En una máquina de dos núcleos
  con el resto de la suite encima no daba terminado en 60 y saltaba `TimeoutExpired`, así que fallaba
  por reloj y no por la guarda. La guarda sigue caducando: si alguien quitara el rechazo, el proceso
  se quedaría escuchando y la prueba esperaría sus tres minutos.
- **Medido en la copia con nombre distinto, que es el caso que estaba roto:** `make test` →
  `Ran 316 tests in 94,240 s … OK` (exit code leído del log, no del aviso: un `| tail` en la tubería
  devuelve el código del `tail`, y así se me colaron dos «completed exit code 0» que eran `FAILED`).
  `test_security` aparte: 26 en verde.
- Documentado: la nota en la fila de las pruebas de `docs/STATUS.md` y un párrafo en el **paso 1** del
  README diciendo en voz alta que **la carpeta puede llamarse como quieras**.

**Sin verificar aquí**: nada nuevo —es el mismo producto con dos pruebas corregidas—. La Release de
GitHub y la prueba con el dedo en el teléfono siguen como estaban.

**Zip**: `https://github.com/Sandra2244/CORT/archive/refs/tags/v0.10.1.zip`

---

## `v0.10.0` — la cara se aparta cuando deja de hacer falta

Hasta ahora la pantalla de CORT tenía **un tirador que abría cinco paneles a la vez**. Esta
versión la rediseña contra los videos de referencia que la dueña del proyecto aportó, y el
resultado es **un riel de seis hilos en el borde derecho, uno por panel, y uno cada vez**.

- **`docs/REFERENCIAS.md`** — el análisis, por escrito y por primera vez: siete clips, seis
  fotogramas por clip en hojas de contacto, dos resultaron ser tutoriales de instalación y no
  interfaz, y de los demás salen **seis patrones** (el reactor es la pantalla; los paneles son
  hilos, no cajas; uno se abre y los demás se apartan; con el gesto la interfaz desaparece; la
  entrada es una línea; se llega con tres manos). **Cero assets, cero fotogramas, cero líneas de
  código de terceros en el repositorio**: lo que se copia es distribución, y está dicho en el doc.
- **`cort/paneles.ts`** — todo el estado de la cara en **lógica pura, sin DOM**: seis paneles con
  su etiqueta y su tecla en una sola lista, `alternar` que **sustituye** al panel abierto en vez
  de acumular, y un apagado por inactividad que no atenúa nada si hay un panel abierto, si la cara
  está apagada o si el sistema pide `prefers-reduced-motion`.
- **`ui/Riel.tsx`** — seis hilos de luz con el número de su tecla; el panel se monta y se desmonta,
  así que en reposo **no hay registro ni controles en el DOM**. El contador de mensajes sin leer
  vive ahora dentro del hilo de mensajes.
- **Se llega con tres manos**: el dedo toca el hilo; con el cursor basta pasar por encima
  (filtrado por `pointerType === 'mouse'`, porque en una pantalla táctil el `hover` no existe y
  fingirlo abriría paneles al deslizar); y el teclado es de primera clase — `1`–`6` abren cada
  panel, `/` salta al campo, `Esc` guarda, `h` apaga la cara y deja sólo el reactor, `?` abre la
  ayuda, que se genera de la misma lista que el riel, así que no puede desincronizarse.
  **Mientras se escribe en el campo ninguna tecla manda sobre la interfaz**: sólo `Escape`.
- **La interfaz se aparta sola**: doce segundos sin gesto y el riel con la barra de abajo bajan al
  26 % de opacidad; cualquier movimiento los despierta. Es **un `setTimeout` rearmado**, no un
  reloj contando, y el despertar por `pointermove` va recortado a 250 ms para no reconciliar el
  árbol a 60 Hz en dos núcleos.
- **Las primeras pruebas de JavaScript del repo, sin instalar nada**: `make test-web` transpila
  `paneles.ts` con el paquete `typescript` que **ya estaba** en `devDependencies` y lo ejecuta con
  `node --test`. **17 pruebas** que fijan lo que de verdad se rompe (atajos mientras se escribe,
  teclas con modificador, el segundo exacto del apagado). Van separadas de `make test` porque las
  316 de Python tienen que poder correr en una máquina sin Node.
- `ui/Bandeja.tsx` **se elimina**; `ui/Hud.tsx` queda en una sola línea abajo, y `Telemetry.tsx`
  pierde su prop `oculto` (si no hay panel abierto, no se monta).
- **Sin marco nuevo en el protocolo** (el riel no habla con el core) y **sin dependencias nuevas**.
- `make test` → **316 en verde**; `make test-web` → **17**; `npx tsc --noEmit` limpio;
  `npm run build` limpio (1 289,96 kB, gzip 358,00 kB).

**Sin verificar aquí**: el dedo sobre el teléfono físico (la pasada de navegador fue de cursor y
teclado), el teclado del Android con `1`–`6`, y **`Enter` para enviar** — el `<form onSubmit>` no
cambió con el riel y `form.requestSubmit()` envía y limpia el campo, pero con `press_key "Enter"`
del navegador automatizado no disparó, así que esa tecla no se afirma. La portada del README sigue
siendo la captura de `v0.6.0`, y el README lo dice: el tirador `⌃ mensajes` que se ve en ella ya no está.

**Zip**: `https://github.com/Sandra2244/CORT/archive/refs/tags/v0.10.0.zip`

---

## `v0.9.0` — CORT ya hace más de una cosa por mensaje

Un asistente reactivo contesta una orden. Éste ahora **encadena, ejecuta y comprueba**:
«sube el volumen, haz una captura y pausa la música» deja de resolverse con la primera frase
y se convierte en tres pasos ejecutados uno detrás de otro, cada uno con su verificación en
el mundo real.

- **`cort_core/planner.py` + `intents.match_all()`** (función 75): el mensaje se parte por
  `;`, `,`, `y`, `luego`, `después`, `entonces`, `además`; cada trozo pasa **por los mismos
  patrones de la lista cerrada de siempre** —lo que no está en ella no se convierte en paso—,
  se hereda el verbo del tramo anterior («abre la terminal y el gestor de archivos») y hay un
  tope de cuatro pasos por latencia, no por estética.
- **Nada de herramientas para el LLM** (regla 6 de `AGENTS.md`): `planner.py` no arma comandos
  ni tiene vía al shell, y hay una prueba que le lee el propio fuente para afirmarlo.
- **Sin marco nuevo en el protocolo**: los pasos viajan en los `intent` y `effect` que la
  interfaz ya entiende y el cierre es un `assistant_message`. Un cliente viejo no se rompe.
- **Medido en esta máquina**, con el ejecutor real, memoria en `/tmp` y sin Ollama ni navegador:
  8 marcos en **2,30 s** y este resumen saliendo del core —
  `2 de 3 pasos hechos: la captura de pantalla, pausar la reproducción. No pude: subir el
  volumen (el mando obedeció pero el nivel sigue en 100 % (¿salida de audio en Dummy?))`.
  La captura dejó un PNG de 161 KB en disco y el volumen **no se contó como hecho** aunque el
  mando respondiera 0: el comprobador sabe negar.
- **316 pruebas en verde** (66,6 s en esta máquina de dos núcleos; 27 nuevas en `test_planner.py`
  y 5 nuevas de protocolo).
- Documentación: sección nueva en `docs/ARCHITECTURE.md`, fila 75 en `docs/FUNCTIONS.md`
  (75 funciones: 24 hechas, 11 en curso, 40 pendientes) y `README.md` actualizado en el mismo commit.

**Sin verificar aquí**: la interfaz pintando los tres pasos en la ventana (se afirma por el
código del cliente, no por captura nueva), el teléfono físico y cualquier oída de la voz.

**Zip**: `https://github.com/Sandra2244/CORT/archive/refs/tags/v0.9.0.zip`

---

## `v0.8.0` — lo que se rechaza queda escrito

Primera pieza de la «base y proyección contra malware»: no bastaba con cerrar la puerta
(`v0.7.0`), hacía falta poder decir **qué** se pidió, desde dónde y que no pasó.

- **`cort_core/audit.py`** (función 74): una línea JSON por puerta cerrada en
  `services/core/data/rechazos.jsonl` (carpeta fuera de git), con seis motivos de **lista
  cerrada** y hora UTC.
- **El secreto nunca entra en el registro**: se guarda el *camino* pedido y no la URL, porque
  un `?token=` apuntado sería un archivo de claves; y si la llave aparece dentro de un nombre
  de archivo, se sustituye por `«llave»`. Comprobado con `grep` sobre el archivo crudo.
- **Un carácter de control no fabrica una segunda línea** (inyección clásica en log), un motivo
  inventado no se escribe, y un disco que no puede escribir devuelve `False` **sin lanzar
  excepción**: apuntar es secundario, cerrar la puerta no.
- **Leíble**: `make rechazos` o `python -m cort_core.audit [n]`.
- **Medido en vivo**: core publicado en `0.0.0.0`, cinco `curl` contra la IP de la Wi-Fi de
  esta máquina → `401 / 401 / 404 / 404 / 200`, cuatro líneas en la bitácora con su origen, y
  el apretón de manos del WebSocket sin llave cortado con `403`.
- **284 pruebas en verde** (20 nuevas en `test_audit.py`, 6 en `test_avatars.py`, más el
  aislamiento que impide que las pruebas de red escriban en la bitácora real).

**Zip**: `https://github.com/Sandra2244/CORT/archive/refs/tags/v0.8.0.zip`

---

## `v0.7.0` — la voz, y la red con llave

- **Voz en el navegador** (función 13): CORT lee cada respuesta con las voces del sistema,
  puntuando las *Natural* y la región; es la voz que se oye en el video del colaborador.
  **Escuchar** sigue en curso: el botón está escrito y montado, pero esta máquina no tiene
  ningún dispositivo de captura (`wpctl status` no lista *Source*, medido otra vez con
  auriculares Bluetooth delante).
- **Puerta de red** (función 73, `cort_core/security.py`): `--lan` **no abre el puerto** sin
  `CORT_LAN_TOKEN` —el lanzador y `python -m cort_core.server` se niegan y salen con código 1—;
  en `127.0.0.1` no se pide nada; la comparación es `hmac.compare_digest`; el `401` de un
  atuendo llega **antes** de tocar el disco y el WebSocket se cierra con **4401 antes de
  `accept()`**.
- **README público en español**: siete etiquetas de colores, índice, ocho pasos de instalación,
  tabla de «si algo no arranca» y el inventario de funciones contado sobre `docs/FUNCTIONS.md`.
- **257 pruebas en verde**.

**Sin verificar**: el teléfono físico (Samsung A16) abierto desde la red, y TLS —por `http://`
la llave viaja en claro y el navegador no da cámara ni micrófono fuera de `127.0.0.1`.

**Zip**: `https://github.com/Sandra2244/CORT/archive/refs/tags/v0.7.0.zip`
