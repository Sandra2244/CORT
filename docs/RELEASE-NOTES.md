# Notas de las Release

Texto listo para pegar en GitHub — y desde este corte, **listo para que lo pegue la máquina**:
`.github/workflows/publicar-release.yml` abre la página de Release con el texto de la sección que
corresponda (`scripts/nota_release.py`, con sus 11 pruebas en `test_nota_release.py`). Se dispara
empujando una etiqueta `v*`, empujando `main`, o a mano desde *Actions → publicar-release → Run
workflow* escribiendo la etiqueta. Es idempotente: la etiqueta que ya tenga su página se omite, y la
que no tenga sección se publica con notas generadas antes que con una página muda.

Las etiquetas `v0.7.0`, `v0.8.0`, `v0.9.0`, `v0.10.0` y `v0.10.1` nacieron **antes** de este pipeline,
y como un `push` de etiqueta busca su YAML en el commit de esa etiqueta, quien las convirtió en
Release fue el disparo por `main` — no hizo falta borrar ni recrear ninguna. **Las ocho
(`v0.7.0` … `v0.13.0`) están publicadas**: `v0.11.0` desde el 2026-10-11, `v0.12.0` desde el
2026-10-13 y `v0.13.0` desde el 2026-10-15 con su nota recortada de este documento — `v0.13.0`
comprobado por la API pública sin credenciales en su corte: id `413388728`, `published_at`
`2026-10-15T03:28:49Z`, cuerpo de 8 266 caracteres, `…/archive/refs/tags/v0.13.0.zip` → `200` —,
en [github.com/Sandra2244/CORT/releases](https://github.com/Sandra2244/CORT/releases). Sigue sin poder
crearse una Release por API desde esta máquina: no hay sesión de `gh` (medido tres veces), ni
`GH_TOKEN` en el entorno, ni `~/.config/gh`.

> **`v0.13.0` salió con su página de texto pero SIN el APK**: la etiqueta se cortó sobre `af34cef`,
> cuando `compilar.sh` todavía tenía el bug de `pipefail`, así que el `run` disparado por esa etiqueta
> falló y no colgó artefacto. El arreglo del pipeline vive en `v0.13.1`, que es la primera Release que
> lleva `CORT-v*.apk` descargable desde el teléfono.
>
> **`v0.14.0` repitió el caso por otro motivo**: su etiqueta la creó `gh release create` desde el propio
> workflow, y un `push` hecho con `GITHUB_TOKEN` no dispara otros trabajos —el APK se compiló verde pero
> su paso de subida sólo escuchaba eventos de etiqueta—. Dejó la página con el texto y los `.zip` de
> fuente, sin `CORT-v0.14.0.apk`. **La descarga válida de estas funciones es `v0.14.1`**, mismo código
> con el hueco cerrado.

> **Diez de las trece páginas publicadas no tienen APK** (medido por la API, sin credenciales), y ya se sabe
> por qué cada vez: ocho nacieron antes de que existiera el pipeline del APK, `v0.14.0` vio su etiqueta
> creada por el propio workflow —y eso no dispara el trabajo del APK—, y `v0.14.2` tuvo el manifiesto mal
> formado. Las tres con adjunto — `v0.13.1`, `v0.14.1`, `v0.14.3` — se comprobaron **descargándolas**, no
> leyendo una log que es privada.

**La lista de tareas para cortar la siguiente (v0.14.5), en orden** — el orden importa porque el
pipeline lee las notas **siempre desde la rama por defecto**, no desde el commit de la etiqueta:

0. Si se quiere **la firma estable** (que el APK nuevo se instale encima del viejo sin desinstalar):
   pegar los dos secretos `CORT_APK_KEYSTORE_B64` y `CORT_APK_KEYSTORE_PASS` en Settings → Secrets and
   variables → Actions, con el contenido de `apps/apk/llave/cort.keystore.b64` y
   `apps/apk/llave/cort.keystore.pass` (archivos locales, ignorados por git). Sin ellos el pipeline
   firma desechable y lo dice — se comprueba leyendo el `CORT-v<etiqueta>-firma.txt` de la Release,
   no hace falta abrir una log que es privada.
1. `docs/RELEASE-NOTES.md` tiene la sección `## \`v0.14.4\` — …` escrita, con su línea **Zip** — la
   prueba `test_cada_etiqueta_del_documento_tiene_su_nota` la exige y `make test` lo recuerda.
2. La rama se revisa y **se fusiona a `main`** (fast-forward, sin `--force`: `main` es ancestro de
   `cort-local-verified`, comprobado con `git merge-base --is-ancestor`). Sin este paso la Release
   saldría con `--generate-notes`: el workflow busca la sección en `main`, y ahí todavía no existiría.
3. Se empuja `main`. **Con eso basta** desde `v0.14.1`: `publicar-release.yml` lee las notas de la rama,
   ve que `v0.14.5` tiene sección y no tiene página, llama a `gh release create v0.14.5` —que crea la
   etiqueta sobre el commit si no existía— y GitHub adjunta solos el código fuente en `.zip` y
   `.tar.gz`: ésa es el acta «.zip como proyecto profesional» sin construir nada. En paralelo
   `compilar-apk.yml` compila `CORT.apk` con el SDK del runner y, al terminar, busca la etiqueta que
   apunta a *su* commit: si la encuentra (o aparece en los dos minutos siguientes) sube
   `CORT-v0.14.5.apk` y su `CORT-v0.14.5-firma.txt` a esa Release. Etiquetar a mano
   (`git tag v0.14.5 && git push origin v0.14.5`) sigue siendo válido y dispara el mismo camino por la
   vía del evento de etiqueta; lo que **no** hay que hacer es empujar la etiqueta antes de tener la
   sección en `main`, o la página saldría con notas generadas.
4. Los **instaladores reales** (setup de Windows, APK) no los produce esta máquina —medido y
   justificado en `docs/PLATFORM.md`—: el Windows se construye en un PC Windows con la receta de
   `packaging/` y se adjunta a la Release ya abierta con `gh release upload v0.14.5 <archivo>`; el
   **APK se hace solo**, desde el pipeline. Nunca hace falta tocar nada de datos: la Release son
   artefactos nuevos; el historial, los recuerdos y el `.env` de quien usa CORT viven fuera del repo
   y una actualización no los borra.

---

## `v0.14.4` — el teléfono abre CORT sin que nadie pegue nada

Después de `v0.14.0` quedaba un muro de tamaño teclado: la primera pantalla del APK **es** la cara de
CORT, pero para verla funcionar hay que **leer** un enlace en la terminal del portátil y **copiarlo** en
el teléfono. Este corte quita ese último tecleo con dos datagramas, y lo hace enseñando la animación en
vez que el formulario.

- **El protocolo**, escrito en `docs/ARCHITECTURE.md` antes de codificarse (regla 5): sonda
  `CORT-ENCONTRARSO-1` al broadcast `:8781`, respuesta `CORT-AQUI-1|http://<ip>:8780/?token=…`. No hay
  HTTP ni core en el medio: pregunta el teléfono y contesta **el lanzador**, que es el que sabe la IP, el
  puerto y la llave. El 8781 es un puerto aparte — el 8780 sigue siendo la página y el 8765 el WebSocket.
- **El coste está dicho con todas sus letras**: la respuesta lleva la llave, así que quien esté **dentro
  de la misma Wi-Fi** y sepa la mágica la recibe. Es una decisión tomada, no un descuido: `--lan` ya
  publica el puerto a esa Wi-Fi y el enlace ya viaja en claro, sin HTTPS. Contra eso hay tres frenos —
  sólo se responde con `--lan` publicado y la página en modo `dist`, **cada respuesta se imprime en la
  terminal con la IP que la pidió** («a quién le di la llave» se ve), y `--sin-descubrimiento` o
  `CORT_LAN_DISCOVER=0` apagan el puerto sin tocar nada más.
- **En el teléfono**: el anillo girando con «Buscando a CORT en tu Wi-Fi…», tres intentos de 900 ms
  lanzados **en su propio hilo** —`DatagramSocket.receive` bloquea, y bloquear el hilo de la interfaz
  congela el anillo: una pantalla de arranque congelada vuelve a ser un formulario—; si llega respuesta,
  se guarda en `SharedPreferences` y la ventana abre sola. Mientras busca, el campo **no pide el foco**,
  para que no salte el teclado encima de la cara de CORT.
- **El campo de pegar no se va**: hay redes donde el broadcast no pasa (VLAN de oficina, puntos de acceso
  con aislamiento de cliente). Si la búsqueda no contesta, la misma pantalla lo dice en español y queda el
  camino de siempre.
- **Quince pruebas nuevas**: 10 en `test_launcher.py` (el lazo UDP probado en `127.0.0.1` con un puerto
  libre de verdad: sonda buena → enlace completo + la IP queda apuntada; sonda basura → silencio; sin
  `--lan` → silencio; el puerto del `.env` manda y un valor absurdo no detiene el arranque) y 5 en
  `test_apk_manifesta.py`, que leen el Java y exigen que sus tres literales estén formados **con las
  constantes del lanzador** — no existe un import compartido entre los dos lenguajes; la prueba es la
  costura, y sin ella cambiar la mágica en un lado dejaría mudo a un teléfono que nadie tiene delante.
- **Medido en esta máquina** con el lanzador real (`cort.py --lan --demo --no-browser`): la sonda volvió
  con el enlace completo, la terminal imprimió `127.0.0.1 preguntó por CORT: se le dio el enlace con su
  llave`, un `HOLA` y un `CORT-ENCONTRARSO-1x` **no sacaron respuesta**, y la barra `red` cambió de texto:
  ya no manda a pegar nada. Suite completa: `TMPDIR=/tmp make test` **532** en verde y `make test-web`
  **56** — **588**.
- **Sin verificar**: que el Java compile (aquí no hay `javac`; lo dirá el run de `compilar-apk` que dispara
  este mismo `push`) y, otra vez, que nadie lo ha visto ocurrir en el Samsung A16.

**Zip**: https://github.com/Sandra2244/CORT/archive/refs/tags/v0.14.4.zip

---

## `v0.14.3` — el manifiesto del APK vuelve a ser XML, y hay pruebas que lo vigilan

Corte **pequeño y de obra**, como el anterior: el código Python, la cara React y el Java de la pantalla de
estreno son los de `v0.14.2`. Lo que se arregla es lo que impidió que `v0.14.2` llegara al teléfono: el
`AndroidManifest.xml` estaba **mal formado** y `aapt2` lo rechazaba.

- **La regla que no sabíamos**: un comentario XML no puede contener `--` en ningún punto, ni siquiera
  dentro de una frase. El texto que avisaba de `aapt2 link` llevaba el nombre del flag con su guion doble y
  partía el manifiesto. Reescrito sin guiones juntos; validado aquí mismo con `xml.etree.ElementTree`, que
  reporta `comentarios con dos guiones: 0` y lee la raíz, el `package` y los atributos.
- **Y salió un bug de verdad, no de forma**: el cabecero del manifiesto prometía que el micrófono y la
  cámara no eran obligatorios, pero `RECORD_AUDIO` y `CAMERA` no llevaban `android:required="false"` —el
  valor por defecto es `true`—, así que el aviso estaba mintiendo. Ahora el atributo está en las dos líneas
  y el `<uses-feature>` y el permiso dicen lo mismo.
- **Diez pruebas nuevas que no dependen de un runner** (`test_apk_manifesta.py`): que ningún comentario
  tenga `--`, que el `<manifest>` no vuelva a fijar
  `versionCode`/`versionName`, que el paquete `dev.sandra.cort` sea idéntico en manifiesto y Java, que los
  imports del Java sean sólo `android.*`, `java.*` o propios (el muro contra AndroidX), que haya una única
  actividad `exported` con `MAIN`+`LAUNCHER`, y que `compilar.sh` siga pasando el `versionCode` derivado
  (`--version-code "$CODE"`) en lugar del 1 clavado. **Esto es lo que faltaba en `v0.14.2`**: la prueba
  vivía en GitHub, con token y con espera.
- **Contado, no mirado**: `TMPDIR=/tmp make test` **517** en verde en **72,516 s** y `make test-web`
  **56** (`# pass 56`) — **573** en total. El Java se compila en el runner; en esta máquina no hay
  `javac`, y sigue sin verse nada en un dedo (regla 11).
- **Qué lleva la página (medido después de empujar)**: run **19** de `compilar-apk` **verde** sobre
  `923b396`, y la Release `v0.14.3` —abierta primero por `publicar-release` run 27, que creó la etiqueta
  sobre este mismo commit— con sus **dos adjuntos**: `CORT-v0.14.3.apk` (49 977 B) y
  `CORT-v0.14.3-firma.txt` (421 B), cuyo primer renglón es `APK de CORT 0.14.3 (versionCode 1403)`. El
  `.apk` se descargó y se abrió en esta máquina: su `AndroidManifest.xml` binario lleva la cadena `0.14.3`
  —y no `main`, ni el `0.13.0` viejo— y entre sus enteros está el **1403**, que es lo que Android lee para
  decidir si es *una versión nueva* o *la misma instalada*. Por la API pública: **trece Releases**, tres
  con adjunto (`v0.13.1`, `v0.14.1`, `v0.14.3`) y diez sin él, por las dos causas explicadas arriba. No se
  mueve ninguna etiqueta publicada.

**Zip**: https://github.com/Sandra2244/CORT/archive/refs/tags/v0.14.3.zip

---

## `v0.14.2` — el APK lleva escrita su versión, y el pipeline la encuentra él solo

Corte pequeño y de obra, pero **se ve desde el teléfono**: hasta ahora el `versionName` del APK salía con
el nombre de la rama. Medido descargando el `CORT-v0.14.1.apk` que subió el pipeline del corte anterior —
`compilar.sh` recibió `main` como versión porque el run vino por rama y el YAML hacía
`${GITHUB_REF_NAME#v}`, y eso es lo que se lee en Ajustes → Aplicaciones.

- **`scripts/etiqueta_del_commit.py`** (nuevo, con sus **10 pruebas** en `test_etiqueta_commit.py`): dada
  la lista de tags de la API pública, devuelve la etiqueta cuyo commit es el del run. Acepta el SHA corto
  de siete que escriben los pasos y las mayúsculas, y **devuelve cadena vacía en vez de explotar** con un
  JSON roto, sin forma de lista, sin `commit`, o con un prefijo tan corto que casaría con medio repo. El
  fallo que cubre es justo ése: adivinar la versión por dónde llegó el evento.
- **El paso «Averiguar la versión» corre antes de compilar** y deja `version` y `etiqueta` en los outputs
  del trabajo. Sin etiqueta sobre el commit sale `0.0.0`: un build de comprobación del Java no se disfraza
  de Release. Que la API falle no lo pone rojo (aquí el `|| true` es deliberado y está explicado en el
  propio YAML); el paso de subida, en cambio, **sí falla** si no puede leer los tags —quedarse sin adjunto
  en silencio es peor que un run en rojo—.
- **`versionCode` deja de valer 1 para siempre**: se deriva de la versión — `0.14.2` → **1402**,
  `0.15.0` → 1500, y cualquier cosa que no sea `X.Y.Z` vuelve a 1, con suelo 1 porque un APK con código 0 no
  lo instala Android—. Con el código fijado en 1 el sistema creía que cada Release era *la misma*
  aplicación ya instalada; con código creciente, el «instalar encima» de la llave estable significa
  actualizar de verdad.
- **Una sola verdad de la versión**: el manifiesto llevaba `android:versionName="0.13.0"` fijado, que
  sobrevivía a todas las Releases. Se quitó; ahora lo escribe `aapt2 link` desde `compilar.sh`, y la prueba
  pública `CORT-v<etiqueta>-firma.txt` cabecea con `APK de CORT 0.14.2 (versionCode 1402)` — se lee sin
  abrir el APK ni tener sesión.
- **Medido antes de empujar**: `bash -n` de los tres guiones del YAML, la derivación de `versionCode`
  ejecutada con cinco versiones de mentira (`0.14.1`→1401, `0.15.0`→1500, `1.2.3`→10203, `0.0.0`→1,
  `main`→1), y `make test` **507** en verde en **74,4 s** (las 10 nuevas del resolutor) con
  `make test-web` **56**. **Lo que no se ha visto todavía**: este APK instalado en el Samsung — nadie lo ha
  encendido en un dedo, regla 11.

> **Después de cortar (medido el 2026-10-15)**: la página `v0.14.2` salió **con cero adjuntos**, y no por
> el token de la etiqueta esta vez. El run 18 de `compilar-apk` se puso **rojo** en «Compilar»: `aapt2
> link` rechazó el manifiesto porque el comentario que explica esta misma sección contenía **dos guiones
> seguidos**, y eso dentro de un `<!-- -->` no es comentario — es XML roto. Como los logs de Actions son
> privados y `gh` no tiene sesión en esta máquina, el fallo se leyó por **anotaciones públicas**
> (`/check-runs/<job>/annotations`), que es el único canal que queda abierto. El arreglo va en `v0.14.3`.

**Zip**: https://github.com/Sandra2244/CORT/archive/refs/tags/v0.14.2.zip

---

## `v0.14.1` — la Release se abre sola con el `push` de `main`, y el APK ya la acompaña

Corte de **pipeline**, no de cara: el teléfono y el lanzador llevan el mismo código que `v0.14.0`
(llave de red auto-creada, pantalla de estreno con la cara de CORT, firma estable opcional). Lo que se
arregla aquí es que la página saliera con su texto **y sin su APK**, que es justo lo que la dueña no
puede descargar.

- **Qué pasó con `v0.14.0`** (medido el 2026-10-15 por la API pública, sin credenciales): el `push` de
  `main` disparó `publicar-release.yml`, que al no existir la etiqueta llama a
  `gh release create v0.14.0` y GitHub crea el tag sobre ese commit. Siete segundos después la página
  estaba abierta (`published_at 2026-10-15T05:32:24Z`). Pero ese `push` de etiqueta lo produjo el token
  del propio workflow, y **los eventos generados con `GITHUB_TOKEN` no disparan otros trabajos**: no
  llegó ningún run con `head_branch: v0.14.0`. `compilar-apk.yml` corrió sólo por la rama (run 15,
  verde, artefacto `CORT-apk` de 42 574 B), y su paso de subida estaba atado a
  `startsWith(github.ref, 'refs/tags/v')` — condición falsa en un `push` de rama—. Release con cero
  adjuntos.
- **El arreglo**: el paso de subida deja de preguntar de dónde viene el evento y pregunta **si hay una
  etiqueta que apunta a su propio commit** (`gh api repos/…/tags` contrastado con `GITHUB_SHA`). Si aún
  no la ve, espera dos minutos a que la abra su hermana `publicar-release` —compilar ya dura minuto y
  pico, así que la carrera está a favor—. Y si sobre ese commit no hay etiqueta ninguna, lo dice y sale
  **0**: seguir comprobando el Java en cada `push` de `main` no debe costar una Release.
- **Comprobado en esta máquina antes de empujar**: `bash -n` sobre el guion extraído del YAML, y la
  resolución de etiqueta ejecutada a mano con la respuesta real de la API de tags —devuelve
  `v0.14.0` cuando el SHA coincide y cadena vacía cuando no—. Suite verde: **497** del core (72,3 s) y
  **56** de la cara, **553** en total.
- **Qué hace la dueña con esto**: descargar el `CORT-v0.14.1.apk` de la Release, instalarlo y pegar **una
  sola vez** el enlace completo que imprime `python3 scripts/cort.py --lan` en el portátil. La primera
  instalación con la llave estable exige desinstalar el APK anterior (firma distinta); el aviso de
  Android «app desconocida» sigue mientras no esté en la Play Store —guía en `apps/apk/README.md`—.

**Zip**: https://github.com/Sandra2244/CORT/archive/refs/tags/v0.14.1.zip

---

## `v0.14.0` — el teléfono deja de ser un muro: la llave se crea sola y la app arranca con su cara

Lo que se quitó aquí no es una regla de seguridad, es **fricción medida por la dueña del proyecto**
(2026-10-15): «sale una pantalla de `py --lan` y hay que colocar el token de arranque; ¿no puede
iniciar con su animación como una IA normal?», y «en el teléfono dice que la app es desconocida».
Tres cosas cambiaron, y la protección de la red quedó entera.

- **El lanzador se inventa la llave y la guarda** (`scripts/cort.py`: `asegurar_token_lan()` +
  `llave_de_red()`). Con `--lan` y `CORT_LAN_TOKEN` vacío, genera un secreto con `secrets`, lo añade
  al `.env` con una nota encima y **permiso `0600`**, y sigue arrancando. **Medido en esta máquina**:
  `cort.py --lan --demo` dejó `llave de red: CORT la creó sola y la guardó en …/CORT/.env — no vuelve
  a pedirla`, la barra `red` imprimió `http://192.168.100.xxx:8780/?token=…` y CORT salió en línea sin
  panel rojo; el `.env` quedó con una sola línea `CORT_LAN_TOKEN=` y `stat -c %a` dando `600`.
  Se añade además `CORT_LAN=1` (la red se publica en **cada** arranque, sin banderas — es lo que hace
  que el doble clic deje a CORT accesible desde el teléfono; ya está puesto en el `.env` de esta
  máquina) y `--sin-lan` para negarla un arranque. Lo que **no** cambió: sin secreto y sin disco donde
  escribir, `--lan` no abre el puerto, y `python -m cort_core.server` con `CORT_HOST=0.0.0.0` sin
  token sigue saliendo con código 1 (lo prueba `test_security` por subprocess). El valor **no se
  imprime en el aviso** — la terminal de arranque acaba en una captura —, la llave viaja una sola vez:
  en la dirección de la barra. **7 pruebas nuevas** en `test_launcher.py`.
- **La primera vez en el teléfono es la cara de CORT** (`apps/apk/…/MainActivity.java`, reescrito).
  Fondo espacial `#02040c`, el **anillo de la marca dibujado con `Canvas` girando** (misma geometría
  que `scripts/marca.py`: banda cian, halo violeta por dentro, núcleo caliente; el `ValueAnimator` se
  cancela al descolgar la vista), **un solo campo** — la llave ya viene dentro del enlace, así que el
  segundo cuadro sobraba—, botón de 54 dp, `Enter` del teclado igual que el botón, `http://` añadido
  si se pega sólo `IP:puerto`, aviso en español si el enlace llega sin `?token=`, WebView **con fondo
  oscuro desde el primer fotograma** (nada de destello blanco), y si el portátil está apagado el
  error se dice en español con diálogo para reescribir la dirección en vez de la página de error del
  navegador. El diálogo muestra la dirección **con la llave tapada**. Persisten `SharedPreferences`,
  mantener pulsado para reconfigurar y el «atrás» que no sale a la calle a la primera.
  **Sin verificar en dedo**: se compila en el pipeline, y en esta máquina no hay `javac` (medido: hay
  JRE 21 y su `keytool`, no el compilador).
- **La firma estable existe** (`apps/apk/llave/`, ignorada por git **antes** de escribir nada, regla
  7): `keytool` generó el keystore PKCS12 — RSA 2048, validez 10 000 días, huella SHA-256
  `6e4ec4ce7a0cd6c0d3480ec7e0abc5a16849e2a9b383623fbfc230204a6b67f6`— y `compilar.sh` firma con él si
  el repo tiene los secretos `CORT_APK_KEYSTORE_B64` / `CORT_APK_KEYSTORE_PASS`. Con esa llave, **un
  APK nuevo se instala encima del viejo**; sin ella cada Release pedía desinstalar. Como las logs de
  Actions no son públicas, cada run sube a la Release un `CORT-v<etiqueta>-firma.txt` con el modo de
  firma y la huella del certificado: así se comprueba desde fuera, sin sesión, con qué llave salió.
  **Falta que la dueña pegue los dos secretos** (dos clics en Settings → Secrets and variables →
  Actions; la guía está en `apps/apk/README.md`), y eso es decisión suya, no un ticket de código.
- **El aviso de Android («app desconocida / puede ser dañina») no se puede quitar, y aquí se dice en
  vez de simularlo**: lo pone Play Protect a *cualquier* APK que no venga de la Play Store, y eso pide
  una cuenta de desarrollador y una subida, no un commit. Lo que sí se arregló es el conflicto de
  firma. `apps/apk/README.md` gana la sección **«Instalar aunque Android avise»**, con los pasos de un
  Samsung One UI — «Detalles → Instalar de todos modos», el interruptor de apps desconocidas y el
  aviso de volver a apagarlo — y la nota de que **la llave merece una copia fuera del portátil**:
  perderla es no poder volver a instalar encima.

Pruebas de este corte: **497** del core en verde — `Ran 497 tests in 72,545 s … OK`, y 80,990 s la
primera vez con la máquina más cargada —, con `--lan` y `CORT_LAN=1` ejecutados de verdad en esta
máquina, y **56** de la cara (`# pass 56`, sin navegador).
Documentado en `docs/ARCHITECTURE.md` (regla 1 de «La red», reescrita), `README.md` (paso 7, la tabla
de variables con `CORT_LAN`, el aviso de la tabla de problemas) y `docs/FUNCTIONS.md` (funciones
**95**, **96** y **97**; el recuento sube a 97 funciones: 39 hechas, 20 en curso, 38 pendientes).

**Zip**: `https://github.com/Sandra2244/CORT/archive/refs/tags/v0.14.0.zip`

---

## `v0.13.1` — el pipeline del APK, domeado: la ventana al teléfono ya compila y sube

Corte pequeño y honesto: el código del asistente **no cambia** respecto a `v0.13.0`; lo que cambia es
que **el pipeline del APK pasó de fallar a salir verde**, y desde esta etiqueta la Release llega con
`CORT-v0.13.1.apk` colgado. Lo que se cuenta aquí es la cruz de los nueve `run`s que costó, porque
cada una es una decisión de ingeniería, no ruido:

- **`pipefail` matando antes de la guarda** (`apps/apk/compilar.sh`, commit `fb9529e`): bajo
  `set -euo pipefail`, la línea `BT="$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)"` **abortaba el
  script** si el `glob` no casaba nada —el `ls` devuelve 1 y `pipefail` lo propaga—, justo antes del
  `[ -z "$BT" ]` que debía detectar el hueco. Arreglado envolviendo cada sonda en `{ ls … || true; }`.
  Un fallo de 1 segundo sin log no se diagnostica: este fue el primer `run` ciego (38676464493).
- **El log de Actions no es público** (se descubrió a golpes): la API de logs pide `admin:read` y la
  URL web pide sesión — el comentario del YAML afirmaba lo contrario y estaba mal, corregido—. Los
  *annotations* del check-run **sí** se leen sin credenciales, así que el paso `Compilar` ahora
  **convierte el final de su propio log en un `::error::`** (`.github/workflows/compilar-apk.yml`,
  commit `6186d35`): es la única ventana honesta que hay desde fuera, y es lo que permitió ver los
  cinco fallos siguientes en vez de adivinarlos.
- **El shell por defecto de GitHub se comporta como `bash -e`** (commit `49c1845`): en el `run`
  38677344363 el paso murió en la línea de `compilar.sh` **antes** de `st=$?` y del `echo ::error::`,
  así que la instrumentación no se ejecutaba y el fallo volvía mudo. `set +e` al principio del bloque
  lo arregla; sin eso, el annotation que debía explicar el siguiente fallo no salía nunca.
- **`AndroidManifest.xml` con `--` dentro de un comentario** (run 38677901897, `AndroidManifest.xml:4:
  error: not well-formed (invalid token)`): la línea que ponía `` `cort.py --lan` `` como ejemplo
  rompía el XML, que no admite dos guiones seguidos dentro de `<!-- -->`. Reescrita la frase (commit
  `96d2243`). Este fallo concreto tardó tres runs en **verse** porque el `bash -e` de arriba lo tapaba.
- **`javac` con `-bootclasspath` y target 11** (run 38678109143, salió con 2): esa combinación está
  **prohibida desde JDK 9**. Pasado a `--release 11` con `android.jar` al classpath (commit `4e7ee91`)
  — el `java.*` lo pone el módulo del JDK y el `android.*` la plataforma; para una actividad que sólo
  usa `android.app` + `android.webkit`, el mismo bytecode.
- **`keytool` firmando a escondidas** (run 38678678013, trazado con `bash -x`): el script tenía un
  `>/dev/null` que **se comía el mensaje de error** de `keytool`; el paso moría con 1 sin decir nada.
  Quitado el redirect (commit `c10f10a`) y el annotation por fin lo contó. Debajo había **dos** bugs
  reales: la contraseña desechable `cort` tenía 4 caracteres y **JDK exige 6+** (run 38678972941,
  alargada a `cortapk` en `6d9f345`), y el JDK del runner **no pone `-keyalg` por defecto** (run
  38679183347, añadido `-keyalg RSA -keysize 2048` en `961c31a`).
- **Una prueba que chupaba del disco** (`tests/test_initiative.py`): `TestBucle` aísla la memoria y
  el clima, pero no el recuento de puertas cerradas —`_cuidar_iniciativa` llama a
  `audit.rechazos_de_acceso()`, que lee el `CORT_AUDIT_LOG` real—. En el `discover` completo `test_audit`
  (que va antes por orden alfabético) deja rechazos escritos en ese archivo compartido, y la regla
  `rechazos` —diseñada para hablar DELANTE de todas— tapaba a `sin_nombre` y falsaba tres pruebas del
  bucle. No es un bug del producto sino una fuga de estado entre pruebas, y se cierra aislándola igual
  que el clima (`rechazos_de_acceso` devolviendo 0 en `TestBucle`); la medición real de rechazos sigue
  probada en su propio `TestReglas`. La suite completa volvió a correr con `mktemp -u` en el log de
  auditoría: **Ran 490 tests in 64,966 s — OK** (antes del aislamiento, tres fallos dependientes del
  orden).
- **El primer verde, medido**: run **38679448057** sobre `main` (commit `961c31a`) — pasos `Compilar`
  y `Dejar el APK como artefacto` en `success`; artefacto `CORT-apk` de **38 442 bytes** (digest
  `sha256:f5fb4f12…`).

**Sin verificar aquí** (regla 11): **el APK instalado en un dedo** — el pipeline ya lo compila y lo
cuelga, pero nadie lo ha instalado en el Samsung de la dueña; la firma es desechable mientras el repo
no tenga el secreto `CORT_APK_KEYSTORE_B64`, así que cada APK nuevo pide **desinstalar el anterior**.
Nada del cerebro, la memoria ni la red cambió en este corte: es `v0.13.0` con la ventana al teléfono
por fin construida en CI.

**Zip**: `https://github.com/Sandra2244/CORT/archive/refs/tags/v0.13.1.zip`

---

## `v0.13.0` — el cerebro que actúa solo, la bitácora que avisa, la alarma que suena y la ventana al teléfono

Lo que pidió el colaborador después de usarlo fue exactamente esto: *«su lógica y cerebro fallan al
ejecutar acciones»*. Y lo que pidió la dueña: usarlo en su teléfono, sin tener que repetirle quién es
ni qué aparato usa. Esta Release trae el **cerebro JARVIS** portado desde el árbol verificado a
`main` —registro cerrado de 19 herramientas, agenda que despierta, un lazo que propone, ejecuta y
**mide el después**—, la bitácora de rechazos convertida en **aviso**, la memoria del **dispositivo**,
un cerebro **opcionalmente en la nube** que por defecto no saca un solo paquete de la máquina, y el
**primer APK compilado por el pipeline**. Cuesta un marco nuevo en el protocolo —`alarm`, el duodécimo
tipo—, documentado antes en `docs/ARCHITECTURE.md` como manda la regla 5. La pila no cambia (Python +
React + Ollama, todo local) y no entra ninguna dependencia.

- **19 herramientas de lista cerrada** (`cort_core/herramientas.py`, función 84): «pon una alarma a
  las 7», «qué hora es», «qué día es hoy», «cuántos días faltan para mi cumpleaños», «baja el brillo»,
  «escribe una nota», «abre la calculadora», «abre YouTube con lo de Bach», «pon música relajante»,
  «cuánto llevo». Van **delante** de `intents` y del LLM — preguntar «pon una alarma» a un modelo que
  tarda 15-60 s por turno en este portátil es pagar caro lo que es una tabla —, y cada ejecución pasa
  por la misma frontera de `actions.py`: **el modelo elige claves, no comandos** (regla 6). Se apaga
  todo con `CORT_TOOLS=0` y vuelve el CORT de antes sin tocar código. Una prueba le **lee el fuente**
  al registro buscando `subprocess` y `os.system`, y `TestHerramientasPorElSocket` le habla por
  WebSocket de verdad con `TestClient`.
- **El lazo que comprueba** (`agente.py` + `planner.dicho()`, funciones 87 y 88): cuando lo pedido
  encadena, CORT propone un paso, lo ejecuta, **mide el resultado en el mundo** y devuelve la medida
  al modelo antes de afirmar nada — tope 4 vueltas, no por estética sino por latencia medida—, con
  forma fija de decir «No pude hacer eso: …». El cierre del plan lo escribe el **recuento de lo
  medido**, no la prosa del modelo. Si la frase se entiende sólo a medias, el cabo suelto viaja a la
  nube — nunca la conversación entera, y nunca el cabo a Ollama.
- **La agenda suena** (`agenda.py` + el marco nuevo `alarm`, función 86): alarmas y recordatorios
  quedan en SQLite y se difunden a **todas** las pestañas abiertas; si no había ninguna, el aviso
  queda **pendiente** y llega al conectar — una alarma nunca se da por entregada sin haberla
  entregado—, y `atrasada: true` avisa cuando tocaba hace más de dos minutos. El `timer` preexistente
  aprendió dos estados más: `sube` y `para` son un **cronómetro** que cuenta hacia arriba en el anillo
  (`total: 0`, y el aro se llena entero en vez de fingir una cuenta que no es).
- **Nube opcional, local por defecto** (`brain.py`, función 89): `CORT_LLM_PROVIDER=ollama|anthropic|openai`
  — con `ollama` como siempre, **cero paquetes salen de la máquina si nadie lo enciende**—; si la nube
  falla, el turno se cierra con un aviso visible («[nube no disponible: …]») en vez de quedarse
  callado, y las claves nunca se cuelan en los mensajes. En el camino salió un bug silencioso: los
  hechos de la usuaria viajaban como mensaje `system` dentro del historial, y `_alternating` los
  barría antes de llegar a Claude — o sea, la nube olvidaba justo lo que la dueña no quiere repetir.
  Ahora van **mergeados en un solo `system`**, con dos pruebas que leen el cuerpo exacto de la
  petición. 18 pruebas en `test_brain.py` con `httpx.MockTransport`: **ninguna llamada real**, la
  cuota de la dueña no se gastó para probar.
- **La bitácora convertida en aviso** (`audit.rechazos_de_acceso()` + primera regla de `initiative.py`,
  función 92): tres intentos de puerta sin llave en diez minutos y CORT **lo dice solo**, delante de
  todas las demás reglas y con el número medido en la frase — «He bloqueado 3 intentos de entrar sin
  la llave. Si no fuiste tú, `make rechazos` enseña quién y desde dónde.». Contar vive en `audit` y
  en el server; `initiative.py` sigue sin importar nada ejecutable, y la guarda AST del reloj del
  server se actualizó **a mano** para aceptar la nueva llamada — que es exactamente para lo que esa
  guarda existe. Medido en vivo: tres rechazos escritos → la regla `rechazos` es la primera que habla.
- **Ya sabe qué teléfono usas** (`memory/facts.py`, función 93): «uso un Samsung A16» o «mi teléfono
  es un Redmi Note 12» se guardan como hechos, junto al nombre, y viajan con los prompts — locales y
  de la nube. La lista de marcas es **cerrada** porque «uso el cronómetro» es una frase real y
  guardarla sería llenar la memoria de basura: hay una prueba de la trampa.
- **El teléfono ve a CORT** (`apps/apk/` + `.github/workflows/compilar-apk.yml`, función 94): **una
  sola actividad Java pura, sin Gradle ni AndroidX ni Capacitor** — estas máquinas no tienen RAM para
  esa fiesta (`docs/PLATFORM.md`) — que abre la URL que imprime `cort.py --lan` con su llave pegada y
  la recuerda en `SharedPreferences`; el icono se **dibuja** con `scripts/marca.py` en cada build,
  como el resto de la marca. El pipeline lo compila con las herramientas del SDK preinstalado del
  runner (`aapt2`/`javac`/`d8`/`zipalign`/`apksigner`) y sube `CORT-v0.13.0.apk` a esta misma
  Release; corre también con cada `push` de `main`, para verlo verde **antes** de etiquetar. **Y así
  se cumplió, medido**: el primer verde salió el 2026-10-15 en el run 38679448057 sobre `main`
  (commit `961c31a`), con `CORT.apk` de **38 442 bytes** como artefacto. Costó nueve runs domear el
  pipeline, y cada fallo lo contó él mismo por un *annotation* público del check-run — las logs de
  Actions no son públicas, los annotations sí—: el `ls` del SDK muerto por `pipefail`, un `--` dentro
  de un comentario del manifiesto (ilegal en XML), `-bootclasspath` prohibido con target 11 desde
  JDK 9, `keytool` firmando a escondidas tras un `>/dev/null`, una contraseña de cuatro caracteres
  que JDK rechaza y un `-keyalg` que el JDK del runner no pone solo. Límites
  escritos en `apps/apk/README.md`, no escondidos: `SpeechRecognition` **no existe dentro del
  WebView** — escuchar es la PWA en Chrome, ya instalable—, y sin el secreto `CORT_APK_KEYSTORE_B64`
  la firma es desechable.
- **La cara entiende lo nuevo** (función 91): `connection.ts` pinta la alarma como mensaje con su
  hora y su «llegó tarde», y `Temporizador.tsx` distingue cuenta atrás de cronómetro — en `sube` el
  aro va **lleno**, porque un aro que diera la vuelta cada minuto sería un reloj que miente—; `termina`
  y `para` dejan el cartel seis segundos y se apaga solo.

- **Medido en esta máquina** (2 núcleos, 1,8 GiB, sin GPU): `make test` → **Ran 490 tests in 70,169 s
  — OK** (137 desde `v0.12.0: 87 del registro y su lazo, 37 del server cableado, la agenda y el
  cronómetro, 6 de la memoria de dispositivo y el `system` de la nube, 7 del aviso), `make test-web`
  → **56/56 en 11,4 s**, `npx tsc --noEmit` limpio y `npm run build` limpio. El aviso de rechazos,
  medido **en vivo** fuera de la suite: tres puertas cerradas escritas → `rechazos_de_acceso()` da 3,
  y `initiative.sugerir` responde `rechazos` delante de todas.

**Sin verificar aquí** (regla 11, con su motivo): **el APK en un dedo** — no hay `javac` ni SDK en
esta máquina (así está medido en `docs/PLATFORM.md`); el pipeline **sí** corrió y salió verde sobre
`main` (run 38679448057, `CORT.apk` de 38 442 bytes), pero nadie lo ha instalado todavía—; **la alarma vista sonar en una
pantalla y el anillo del cronómetro pintado** — el navegador va cerrado por pedido expreso de la dueña
desde el 2026-10-12—; **la voz dentro del WebView** (escuchar no: ahí no existe `SpeechRecognition`,
y hablar está escrito pero nadie lo oyó salir de un teléfono—); **el hecho del dispositivo recordado
por un modelo real** en una charla de verdad —probado contra cuerpos de petición simulados, sin gastar
cuota—; y la nube con cuenta real sigue sin medición: su falta de TLS en la LAN es la misma deuda
escrita desde `v0.7.0`, ahora con la bitácora avisando de quien prueba la puerta.

**Zip**: `https://github.com/Sandra2244/CORT/archive/refs/tags/v0.13.0.zip`

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
