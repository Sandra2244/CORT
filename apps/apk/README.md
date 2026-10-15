# CORT en el teléfono (APK)

Desde `v0.15.0` este APK es **dos cosas**. Si el portátil está publicado en la
Wi-Fi, abre la página que sirve `cort.py --lan`: la cara completa, con su cuerpo
3D y su memoria del core. Y si no lo está, **CORT funciona dentro del teléfono**:
una cara nativa en Java con su propio cerebro de once acciones, su memoria en
SQLite, su voz y su micrófono, sin servidor y sin abrir el portátil.

**Por qué** — el número lo puso la dueña del proyecto, no una sugerencia externa:
«que funcione de forma local en mi cel, que no tengo servidor y mi PC no tiene
recursos para eso». Está escrito en `docs/PLATFORM.md`, con su coste: de las
**tres deudas** de ese acuerdo quedan cerradas dos (la pantalla de la clave de
nube, `v0.15.1`, y **el puente que sincroniza las dos memorias**, `v0.15.2`) y
abierta una (los dos cuerpos de reglas).

**Por qué un WebView y no Capacitor**: en el portátil de desarrollo (1,8 GiB) un
`gradle build` de Capacitor congela la máquina — está medido y escrito en
`docs/PLATFORM.md`—, y además aquí no hace falta: `javac` no está (lo que hay es
el JRE 21 y su `keytool`, medido 2026-10-15), así que no hay nada que compilar
en esta máquina ni que descargar. **Once archivos de Java puro** contra el SDK
(2 943 líneas, 118 KB medidos el 2026-10-15), cuatro herramientas que el runner
de GitHub Actions ya trae (`aapt2`, `javac`, `d8`, `apksigner`) y un script,
`compilar.sh`, que **nunca corre en el portátil**.

## Qué hay dentro

| archivo | qué decide |
|---|---|
| `MainActivity.java` | **qué superficie se ve**: el WebView si el portátil contesta, la cara nativa si no, el campo de pegar sólo si nadie tiene la culpa |
| `Cara.java` | la interfaz nativa: registro, campo, micrófono, el lazo oír → tabla → ejecutar → (nube) → proponer aprender, la **pantalla de ajustes de nube** (`⚙` bajo el anillo, `v0.15.1`) y la fila que **cruza el puente** (`↔ traer y llevar mis recuerdos al portátil`, `v0.15.2`) |
| `Cerebro.java` | lee `assets/habilidades.json`, normaliza la frase y dice qué acción es. **No ejecuta nada** |
| `Acciones.java` | las manos: once acciones, todas con intenciones públicas de Android o `AudioManager`. Sin shell, sin `QUERY_ALL_PACKAGES` |
| `Recuerdos.java` | `cort.db` (SQLite): los hechos de la dueña y las habilidades que aprende. Desde `v0.15.2` es además **la cabeza** que el puente lee y en la que escribe, y Traduce al revés: `El usuario se llama Sandra` que viene del portátil se guarda con la clave `nombre` |
| `Puente.java` | el **espejo exacto** de `cort_core/puente.py`: el cuadro, `exportar`, `fusionar`, `normaliza`, los topes. Puro — sólo `java.util` y `org.json`, y una prueba le prohíbe nombrar red, disco o Android |
| `Sincroniza.java` | la **única** clase del APK que abre un socket: baja el cuadro del portátil, lo fusiona, sube el de aquí, y devuelve el recuento o `null` con su motivo en español |
| `Voz.java` | `TextToSpeech` y `SpeechRecognizer`: hablar **y escuchar**, que el WebView no podía |
| `Nube.java` | la nube opcional, con la clave escrita una vez en el aparato |
| `Paleta.java`, `Anillo.java` | los literales de la marca y el anillo dibujado con `Canvas`, compartidos por las dos caras |
| `assets/habilidades.json` | **la tabla de frases**: el dato que `make test` sí puede validar en esta máquina |
| `simbolos-android.json` | el diccionario de constantes del SDK, descargado de AOSP por `scripts/simbolos_android.py` |

## Usarlo

1. Bajar `CORT-v<versión>.apk` de la [Release](https://github.com/Sandra2244/CORT/releases)
   e instalarlo (lea «Instalar aunque Android avise» abajo).
2. **Abrirlo y ya.** Si el portátil está lanzado con `--lan` en la misma Wi-Fi,
   el teléfono lo encuentra (función 98) y abre la cara completa. Si no está,
   aparece **CORT en el teléfono**: se le escribe en el campo de abajo o se pulsa
   ● y se le habla. No hay que pegar nada en ninguno de los dos casos.
3. Frases que contesta solo, sin portátil y sin nube —**comprobadas una por una
   contra la tabla con el espejo Python de `Cerebro.encaja`**, no de oído—:
   «qué hora es» / «dime la hora», «qué día es hoy», «sube el volumen»,
   «baja el volumen», «silencio», «ponlo al máximo», «abre los ajustes», «abre el
   navegador», «abre la música», «abre los mensajes», «abre el reloj», «abre el
   teclado», «pon una alarma a las 7:30» (o «despiértame a las 6:45»),
   «cronómetro de 5 minutos», «recuerda que mi nombre es Sandra»,
   «¿qué sabes de mí?» y «qué recuerdas» (la lista entera), «¿qué sabes de mis
   gustos?» (un dato suelto), «¿quién soy?», «busca el tiempo en Madrid»,
   «quién eres», «qué puedes hacer», «hola», «gracias», «¿me oyes?» y «adiós».
   La regla de la tabla: **una frase casa si es exacta**, o si empieza por una de
   las formadas con hueco (`busca …`, `recuerda que …`, `alarma a las …`) y le
   sobra algo. «baja» a secas **no** está; «baja el volumen» sí. Y el orden
   importa: «¿qué sabes de mí?» contesta la lista porque la regla exacta vive
   delante de la del hueco — había al revés, se llamaba un hecho clave `mi`, y
   hay dos pruebas que ya no lo permiten.
4. Si no conoce una frase, **propone aprenderla**: enseña las acciones que ya
   sabe hacer y guarda la que la dueña elija. Nunca se le ocurre ejecutar algo
   que no esté en esa lista.
5. Para la cara del portátil hace falta lanzarlo: `python scripts/cort.py --lan`.
   La **llave de red ya no se pide**: si no hay `CORT_LAN_TOKEN` en el `.env`, el
   lanzador la inventa, la escribe ahí (archivo ignorado por git, permiso 0600)
   y sigue arrancando. Para que el doble clic del escritorio publique sin
   banderas, `CORT_LAN=1` en el `.env`; para negarlo un arranque, `--sin-lan`.
6. **Mantener pulsado** (o el botón «atrás») abre el menú: *Buscar el portátil* /
   *Pegar un enlace* / *Salir*. El pegado de enlace es el respaldo para las redes
   donde el broadcast no pasa (VLAN, puntos de acceso con aislamiento de
   cliente); se pega el enlace entero de la línea `● red` — la llave viaja dentro
   — y queda guardado. La dirección se muestra con la llave tapada.
7. **La nube, si se quiere** (opcional, y nunca necesaria): en el teléfono, **el chip
   que vive bajo el anillo** —`⚙ nube apagada · toca para escribirla`— abre la pantalla
   de ajustes (función 105, desde `v0.15.1`). Ahí se elige proveedor (`anthropic` o
   cualquier servicio compatible con OpenAI), se escribe la dirección base, el modelo y
   la clave; se guarda en `SharedPreferences` «cort-nube» y CORT pregunta al modelo lo
   que la tabla no conoce. Con la nube encendida hay un botón «▶ probar la conexión»
   que contesta en español si no hay respuesta, y «⌫ borrar la clave de este teléfono»
   devuelve la cara a local puro. Tres cosas que importan: **la clave guardada no se
   vuelve a mostrar nunca** (el campo arranca vacío y sólo dice cuántos caracteres hay),
   dejarla en blanco al guardar **la conserva** (no la borra), y sin internet o sin
   clave responde la tabla local y punto.
8. **Que lo aprendido en un aparato se sepa en el otro** (función 106, desde
   `v0.15.2`): el mismo `⚙` tiene la fila `↔ traer y llevar mis recuerdos al
   portátil`. Con el portátil lanzado (`cort.py --lan`) y en la misma Wi-Fi, un
   toque baja lo que hay en `memory.db`, lo guarda en `cort.db`, sube lo de aquí,
   y cuenta los números: cuántos son nuevos, cuántos ya estaban, cuántos se
   descartaron y cuántos se quedó cada lado guardando para sí. **No pide ninguna
   dirección nueva** — la del core se deriva del enlace que ya guardó el
   descubrimiento, cambiando el puerto —, **no borra nada en ningún lado**, y si
   el portátil no contesta lo dice en español en vez de quedarse callado. La
   llave de red viaja en la URL, como en `/ws`, y **nunca dentro de un recuerdo**:
   una fila que la contenga no sale del teléfono.

**Qué va a la nube y qué no**: sólo la frase dicha y un resumen de los hechos
guardados (van en el `system`, no en el historial — el bug que ya cazó
`brain.py`—). La API key **no entra en el repositorio ni en el APK**: se escribe
una vez en el aparato y vive en su almacenamiento privado, que es en claro —es
suficiente para un prototipo propio, y se dice aquí en vez de prometer un
cifrado que pediría Gradle—.

**Qué sale del teléfono hacia el portátil** por el puente: el texto de los
recuerdos y su fecha, con tres topes escritos (`MAX_CONTENIDO` 300 caracteres por
fila, `MAX_BYTES` 256 KiB de cuerpo, y un tope de filas **calculado** — 271 — para
que el cuerpo nunca sobre-pase los 256 KiB y el server conteste 413). La clave de
nube **no** viaja: vive en `SharedPreferences` y el puente sólo mueve `hechos`.

## Instalar aunque Android avise

Android avisa con **cualquier** APK que no venga de Google Play, y CORT es un
prototipo firmado en casa: el aviso («¿Instalar esta app desconocida?» / «La app
puede ser dañina») **no se puede quitar de verdad** mientras no esté en la Play
Store —eso pide una cuenta de desarrollador (25 USD) y una subida, no un commit—.
Lo que sí se puede —y se ha hecho— es que el aviso sea el mismo de siempre y que
el APK nuevo se instale **encima** del viejo. Eso depende de la firma (ver abajo).

En un Samsung (One UI, medido en la documentación de Android, no en esta máquina
— **sin verificar en dedo**):

1. Abrir el archivo descargado desde «Descargas» (Chrome) y pulsar «Instalar».
2. Si dice que la app es desconocida: «Detalles» → «Instalar de todos modos».
3. Si pide permiso suelto: Ajustes → Apps → ⋮ → «Instalar apps desconocidas» →
   activar para el navegador con el que se descargó. Después, volver a intentar.
4. Al terminar, quitarle el permiso a esa app: es un interruptor que no debe
   quedarse encendido.
5. Si Android dice «no se puede instalar porque una versión anterior existe con
   otra firma» (o «conflicto de firma»): hay que desinstalar la vez anterior.
   Eso pasa mientras el repo no tenga la llave estable, y sólo esa vez.

## Lo que funciona en el teléfono y lo que no

Dos columnas, porque hay dos CORT en el mismo APK. Lo de la izquierda es la cara
del portátil (`WebView`); lo de la derecha vive dentro del teléfono y **no
necesita al portátil encendido**.

| | con el portátil en la Wi-Fi | **solo en el teléfono (v0.15.0)** |
|---|---|---|
| Chat, reactor, ventanas, muelle, teclado táctil | ✅ la misma cara que en el navegador | 🔨 cara nativa Java (`Cara.java`): compilada y firmada, **sin verla un dedo todavía** |
| **Que CORT hable** | 🔨 en WebView con `speechSynthesis`, medido sólo en escritorio | 🔨 `TextToSpeech` del sistema: código escrito, **sin oírse en dedo** |
| **Que CORT escuche** | ❌ **límite real del WebView**: el API de reconocimiento no corre en un WebView embebido; ahí la escucha se usa desde la **PWA** de `apps/web` | 🔨 **ésta es la vía que abre la cara nativa**: `SpeechRecognizer` con su permiso de micrófono pedido en pantalla. Sin verificar en dedo |
| Volumen, alarma, cronómetro, abrir apps del sistema | 🔨 a través del core del portátil | 🔨 once acciones con intenciones públicas de Android y `AudioManager`, validadas contra el diccionario AOSP; **sin ejecutar en el teléfono** |
| Memoria de quién soy, qué sé de mí | ✅ `memory.db` del core | 🔨 `cort.db` en SQLite, propia del teléfono y **con puente desde `v0.15.2`**: la fila `↔` del `⚙` trae lo que hay en el portátil y lleva lo de aquí. **Sin verificar en dedo** — lo ejecutó `make test` con dos bases, no un Samsung |
| Hablarle a un modelo por internet | 🔨 en el core, con Ollama local | 🔨 opcional (`Nube.java`) **y ya escribible desde el teléfono** (`v0.15.1`): el chip `⚙` bajo el anillo abre la pantalla donde se pega la clave. Responde cuando hay clave; sin ella, la tabla local. **Sin ver en dedo** |
| Gestos de cámara (`defocus.ts`, `getUserMedia`) | 🔨 sin verificar en dedo | ❌ no existen en la cara nativa |

Lo único **visto en dedo** hasta hoy (dos capturas, 2026-10-15) es lo de `v0.14.4`:
el APK instalado, la pantalla oscura con el anillo, el aviso «No encontré a CORT
en la Wi-Fi…» y el campo de pegar con el teclado de Android. Nada de la columna
derecha: esa cara entra en este corte y aún no se ha instalado.

## La firma

Mientras el repo **no** tenga los secretos `CORT_APK_KEYSTORE_B64` y
`CORT_APK_KEYSTORE_PASS`, cada Release firma con una llave desechable que se
genera en el propio run: hay que **desinstalar el APK anterior** antes de
instalar el nuevo. Con los secretos puestos, `compilar.sh` firma con la llave
guardada y el APK se actualiza instalando encima. La llave no viaja en el
repositorio (regla 7): vive en `apps/apk/llave/`, ignorada por git.

Poner la llave estable, una sola vez:

1. `github.com/Sandra2244/CORT` → **Settings** → **Secrets and variables** →
   **Actions** → **New repository secret**.
2. Crear `CORT_APK_KEYSTORE_B64` con el contenido íntegro de
   `apps/apk/llave/cort.keystore.b64` (un solo bloque de texto; abrirlo con un
   editor de texto, no con el visor de imágenes).
3. Crear `CORT_APK_KEYSTORE_PASS` con el contenido de
   `apps/apk/llave/cort.keystore.pass` (una sola línea, sin saltos).
4. Cortar la etiqueta siguiente: el pipeline firma con la llave del repo y
   `compilar.sh` lo dice en `build/firma.txt`, que se sube a la Release como
   `CORT-v<etiqueta>-firma.txt`.

Comprobarlo sin leer un log privado (las logs de Actions no son públicas): abrir
ese archivo en la Release y buscar la huella. Con la llave estable tiene que
aparecer el SHA-256 `6e4ec4ce7a0cd6c0d3480ec7e0abc5a16849e2a9b383623fbfc230204a6b67f6`
—el mismo que imprime `keytool -list -v` sobre `apps/apk/llave/cort.keystore`,
sólo que sin los dos puntos— junto a un sujeto `CN=CORT, OU=prototipo local,
O=local`, y la primera línea del archivo tiene que decir `llave: la del repo`.
El texto exacto de esas líneas lo escribe `apksigner --print-certs`, que es el
que lo genera: la huella y el modo son lo comprobable. Si pone
`llave: desechable` y una huella distinta, el secreto no llegó. Esta huella es
pública —vive dentro del APK— y no es el secreto: el secreto es la clave privada
del `.keystore`.

**Perder la llave** significa no poder volver a instalar encima: cada APK nuevo
con otra firma obliga a desinstalar. `apps/apk/llave/` es, por tanto, un archivo
que merece una copia fuera del portátil.

## Qué versión lleva escrita el APK

Desde `v0.14.2` el binario sabe de qué corte es: `compilar.sh` recibe la versión
(`0.14.3`) y con ella fija `versionName` y un `versionCode` derivado (`1403`).
Antes el número estaba fijado en el manifiesto (`0.13.0`) y el pipeline, cuando
el run llegaba por rama, pasaba el nombre de la rama: el `CORT-v0.14.1.apk` se
instaló rotulado como **`main`**, y así lo enseña Ajustes → Aplicaciones → CORT.
Para comprobar el rotulado sin instalar nada, el primer renglón del
`CORT-v<etiqueta>-firma.txt` de la Release dice `APK de CORT <versión>
(versionCode <número>)` — en `v0.14.3`, `APK de CORT 0.14.3 (versionCode 1403)`;
ésa es la línea que hay que mirar para saber que el adjunto es de este corte y no
del anterior. **Medido el 2026-10-15 con el `CORT-v0.14.3.apk` descargado**: el
renglón dice exacto `APK de CORT 0.14.3 (versionCode 1403)`, y en el manifiesto
binario del propio APK aparece la cadena `0.14.3` y el entero `1403` — no el `main`
que salió en `v0.14.1`, ni el `0.13.0` que vivía fijado en el archivo—.

`v0.14.4` ya está comprobado (**medido el 2026-10-15**, bajando el `.apk` de la
Release): su `…-firma.txt` arranca con `APK de CORT 0.14.4 (versionCode 1404)`, en
el manifiesto binario aparece la cadena `0.14.4` y el entero **1404**, y el
`classes.dex` trae las palabras del descubrimiento (`CORT-ENCONTRARSO-1`,
`CORT-AQUI-1|`, `Buscando a CORT en tu Wi-Fi`). El sha-256 del archivo es distinto
del de `v0.14.3`, así que no es el mismo binario repetido. Lo compiló el run **21**
de `compilar-apk` —en esta máquina no hay `javac`, así que el SDK es del runner—.
**Éste sí lo vio un dedo**: dos capturas de la dueña (2026-10-15) enseñan la
pantalla oscura con el anillo y el aviso de que no encontró al portátil, con el
campo de pegar y el teclado de Android abierto. Lo que no ha visto nadie todavía es
la cara nativa que entra con `v0.15.0`.

`CORT-v0.15.0.apk` **ya está publicado y abierto también en esta máquina** (medido
el 2026-10-15 tras empujar la etiqueta): **70 526 B**, sha-256 `d1d0e7ee…a563` —el
mismo *digest* que anuncia la API—, y su `…-firma.txt` arranca con
`APK de CORT 0.15.0 (versionCode 1500)`. Dentro del `AndroidManifest.xml` binario
están la cadena `0.15.0` y el entero **1500**, y **no** está `0.14.4`, con los
cuatro permisos (`INTERNET`, `RECORD_AUDIO`, `CAMERA`, `MODIFY_AUDIO_SETTINGS`). En
`classes.dex` aparecen las **nueve** clases `dev/sandra/cort/*` —`Acciones`,
`Anillo`, `Cara`, `Cerebro`, `MainActivity`, `Nube`, `Paleta`, `Recuerdos`, `Voz`—,
`cort.db`, `TextToSpeech`, `SpeechRecognizer` y la sonda `CORT-ENCONTRARSO-1`; y
**no** aparecen `Runtime`, `ProcessBuilder` ni `exec(`, que es la prueba de que la
lista cerrada de acciones viaja en el binario y no sólo en el fuente. El
`assets/habilidades.json` del APK trae **once acciones**, **26 patrones** y
`listar` antes de `saber-algo` (posición 16 contra 17): el arreglo de
«¿qué sabes de mí?» va instalado, no prometido. Lo compiló el run **38778796522**
de `compilar-apk` sobre `1ec9638`, con `publicar-release` 38778796447 abriendo la
página. **Lo que esto no prueba**: que la cara nativa funcione en un dedo —nadie la
ha instalado aún—, que el micrófono oiga, que la voz suene por el altavoz o que las
once acciones muevan el teléfono.

`CORT-v0.15.1.apk` **también está publicado, bajado y abierto aquí** (medido el
2026-10-15). **74 622 B**, sha-256 `9d42bc0b0f56f32716fd9527d0644c54851f2bcffd2d7cbd78979c312f582beb`
— el mismo que anuncia la API de GitHub —, y doce archivos dentro del zip. El
`AndroidManifest.xml` binario trae `0.15.1` y `versionCode 1501` **y ya no** la cadena
`0.15.0` ni el `1500`, con sus cuatro permisos de siempre. En `classes.dex` están las
**nueve** clases del fuente y **35 más** generadas (`Cara$0…$16`, `MainActivity$0…$11`,
los `…$0` de `Anillo` y `Cerebro`, `Cerebro$Regla`, `Cerebro$Resultado`, `Voz$AlOir`,
`Voz$Escucha`): **44 descriptores frente a los 37 de `v0.15.0`**, medidos sobre los dos
binarios — y sólo en `Cara` pasan de 10 clases generadas a 17, que es exactamente el número
de listeners nuevos de esta pantalla —, la referencia
`InputType`, y **literalmente escrita** la cara nueva: `⚙ nube apagada`,
`▶  probar la conexión`, `La nube, si quieres`, `⌫  borrar la clave de este teléfono`.
Un matiz honesto: `TYPE_TEXT_VARIATION_PASSWORD` **no** aparece como texto porque `javac`
inlinea las constantes `static final int`; lo comprobable es la clase y el comportamiento,
y eso lo fija la prueba sobre el fuente. **No** hay `Runtime.getRuntime`, `ProcessBuilder`,
`exec(`, `/system/bin` ni `QUERY_ALL_PACKAGES`, y **ningún archivo del APK** lleva una cadena
con forma de clave (`sk-…`) — la llave se teclea en el aparato, regla 7—.
`assets/habilidades.json` sigue con **once acciones**, **26 patrones** y `listar` en la
posición 16, delante de `saber-algo` en la 17. Su `…-firma.txt` (421 B) arranca con
`APK de CORT 0.15.1 (versionCode 1501)` y `llave: desechable (hay que desinstalar la
versión anterior)` con la huella `721bf5f4…15dcf`, que **no** es la de la llave estable
(`6e4ec4ce…a6b67f6`): los dos secretos del repo siguen sin estar pegados. Compilaron los
runs **38786879687** y **38786887027** de `compilar-apk` sobre `01cb1b9`, y
`publicar-release` 38786879665 / 38786886950 abrieron y completaron la página.
**Lo que esto sigue sin probar**: lo mismo que arriba, y además que la pantalla de ajustes
se vea, que la nube conteste con una cuenta real y que «probar» no trabe la interfaz.

El `versionCode` creciente es lo que hace que «instalar encima» con la **llave
estable** sea una actualización y no la misma versión repetida; con firma
desechable, en cambio, cada APK nuevo exige desinstalar el anterior aunque el
número suba.

## El teléfono encuentra a CORT solo (`v0.14.4`)

Desde este corte, la app **no espera que nadie pegue nada**: al abrirse por primera
vez pregunta en la Wi-Fi y, si el portátil está lanzado con `--lan`, se abre solo.

El cambio está en el lanzador, no en el core. `scripts/cort.py` abre un socket UDP
en el puerto **8781** (el 8780 sigue siendo la página) y contesta a un datagrama
que empiece exacto por `CORT-ENCONTRARSO-1` con `CORT-AQUI-1|http://IP:8780/?token=…`.
El Java hace el viaje inverso: `DatagramSocket` con `setBroadcast(true)`, tres
intentos de 900 ms a `255.255.255.255:8781`, y el enlace que vuelve se guarda en
`SharedPreferences` y se abre — con la búsqueda **en un hilo aparte**, porque
preguntar en la red desde el hilo de la interfaz congela la pantalla.

Qué hay que saber:

- La respuesta **lleva la llave**. Quien esté en tu Wi-Fi y formule la sonda exacta
  recibe el enlace con su `?token=`. Es el precio de quitar el tecleo, y está
  escrito en `docs/ARCHITECTURE.md`. Los frenos: sólo se contesta con `--lan` y con
  `--serve dist`; una sonda que no coincide se ignora en silencio; cada IP que
  pregunta se imprime en la terminal del arranque (`[red] 192.168.x.x preguntó por
  CORT…`), y hay apagador: `python3 scripts/cort.py --lan --sin-descubrimiento`
  o `CORT_LAN_DISCOVER=0`.
- **Si la red no deja emitir broadcasts** (algunos puntos de acceso los bloquean),
  el campo de siempre sigue ahí: se abre la pantalla, se pega el enlace de la línea
  `red` y listo. La búsqueda no sustituye al pegado, lo precede.
- **Si el móvil no encuentra a CORT**: comprueba que el portátil lanzó con `--lan`
  (la barra `red` en verde), que están en la misma Wi-Fi y que el puerto 8781 no lo
  tiene ocupado otro programa. Si no, usa el campo.

Las **33** pruebas de `test_apk_manifesta.py` (16 del manifiesto, el build y el
paquete + 6 del protocolo de divulgación + 11 de la pantalla de ajustes de nube)
vigilan además que los literales del
Java sean **los mismos** que las constantes del lanzador: `SONDA`, `RESPUESTA` y
`PUERTO_DIVULGACION` se comparan contra `cort.py`, así que cambiar el puerto o la
palabra mágica en un lado sin cambiarlo en el otro revienta en `make test` y no
en un teléfono.

## Si tocas el manifiesto

`AndroidManifest.xml` se compila con `aapt2 link`, que es **estricto con los
comentarios**: dentro de un bloque de comentario no pueden aparecer dos guiones
seguidos. Escribir ahí el nombre de un flag largo es la forma más rápida de
romper el build, y el fallo se ve en el runner, no en `make test`. Por eso
`services/core/tests/test_apk_manifesta.py` lee el archivo y lo valida, además de
vigilar que el `<manifest>` no vuelva a fijar su propia versión, que el paquete
`dev.sandra.cort` sea el mismo en el manifiesto, en la actividad y en las **nueve**
capas de archivo del Java, que ningún import saque de la lista cerrada (`android.*`,
`java.*`, `org.json.*` y `dev.sandra.cort`: aquí no hay AndroidX ni Kotlin porque
no hay Gradle), que los cuatro permisos declarados sean exactamente los cuatro que
usa el código y que todos los que se pueden negar sean *requitable*, y que
`compilar.sh` siga pasando el `versionCode` derivado en lugar del `1` clavado y
siga enlazando los `assets` donde vive la tabla.

**Cincuenta y cuatro** pruebas vigilan esta carpeta desde `make test`: **33** de manifiesto,
build, paquete, protocolo y pantalla de nube (`test_apk_manifesta.py`) y **21** del cerebro
(`test_apk_cerebro.py`). Éstas son las que de verdad sustituyen al compilador que
no existe en el portátil de la dueña: validan `habilidades.json` (una acción por
fuera de la lista cerrada, un patrón sin normalizar, un hueco prometido y no
rellenado: todo eso revienta aquí), cosean cada acción de la tabla con su `case`
del Java, y comparan cada `Clase.CONSTANTE` que aparece en el código contra
`simbolos-android.json` — el diccionario de **1044** constantes descargadas de AOSP
en **doce** clases por `scripts/simbolos_android.py`. Sin ese diccionario, la verdad del SDK vivía en
mi memoria, y salió `AlarmClock.EXTRA_COUNTDOWN`: un nombre inventado que costó un
run fallido (116541550041, medido 2026-10-15). La pantalla de ajustes de `v0.15.1`
pidió `InputType`, y el procedimiento fue el contrario: primero se bajó
`core/java/android/text/InputType.java` de AOSP y se verificó que los dos nombres
que quería usar existen, y **después** se escribieron en el Java.

## La cara nativa, en una línea por archivo

`MainActivity` decide qué se ve; `Cara` la pinta; `Cerebro` lee la tabla y dice
qué acción es; `Acciones` la ejecuta; `Recuerdos` la recuerda; `Voz` la oye y la
habla; `Nube` la pregunta cuando hay internet. Cada una de esas piezas tiene su
prueba en `test_apk_cerebro.py` o en `test_apk_manifesta.py`, y la regla de siempre
sigue en pie dentro del teléfono: **las acciones son una lista cerrada** (regla 6)
— **once**: `abrir`, `alarma`, `buscar`, `cronometro`, `decir`, `fecha`, `guardar`,
`hora`, `listar`, `saber`, `volumen`. Ninguna frase, aprendida o propuesta por la
nube, puede invocar algo que no esté ahí, y en `Acciones.java` no hay shell ni
`QUERY_ALL_PACKAGES`: las pruebas buscan literalmente `Runtime.getRuntime`,
`ProcessBuilder`, `exec(` y `/system/bin`.

## Aprender, con aprobación de la dueña

Cuando la tabla no conoce una frase y no hay nube, `Cara` **propone**: enseña las
cuatro acciones que pueden guardarse con una frase nueva (`decir`, `hora`, `fecha`,
`listar`) y sólo guarda la que ella elija. La restricción no es cosmética: una
habilidad aprendida guarda la frase entera como texto, así que las tres acciones
que piden un parámetro (`abrir`, `saber`, `volumen`) no son aprendibles, y
`test_apk_cerebro.py` falla si alguien las mete en `APRENDIBLES`.

## La nube se configura en el teléfono (`v0.15.1`)

El chip `⚙` bajo el anillo abre un `AlertDialog` con cuatro campos y dos botones. Lo
que no se ve desde fuera son las tres reglas que sus pruebas defienden, y son las que
hacen que meter una clave aquí sea seguro de usar:

- **La clave guardada no vuelve a la pantalla.** Nunca hay un `setText(nube.clave())`:
  el campo arranca vacío y la pista dice sólo `clave guardada (N caracteres)`. Un
  `EditText` que se rellena con la llave es una llave en claro legible por encima del
  hombro, y la prueba cuenta las apariciones de `nube.clave()` fuera de comentarios y
  literales para que no se cuele una cuarta.
- **En blanco conserva.** Guardar sin teclear no borra la llave: se pueden corregir el
  modelo o la dirección sin volver a buscarla. Borrarla es un acto explícito, con su
  botón.
- **Probar no congela la cara.** «▶ probar la conexión» pregunta en su propio `Thread`
  y contesta con `runOnUiThread`. La prueba parte el fuente en `new Thread(` y exige
  que el `preguntar()` quede del lado de atrás.

La escritura de la clave vive **sólo** en `Nube.ajustar()`: `Cara` no toca el
almacén, y `.putString("clave", …)` aparece una única vez en todo el proyecto. Ningún
`.java` ni asset lleva un literal con forma de clave (`sk-…`), y la verificación de
eso corre en `make test`, no de palabra.

Dos bugs de `v0.15.0` salieron al escribir esta pantalla y van arreglados aquí: el
diálogo de aprender una frase cerraba con `«` y `"`, y su campo pintaba texto claro
sobre el blanco del `AlertDialog` de Android —nadie lo había visto porque nadie había
instalado la cara nativa—; los tres `new EditText(actividad)` del proyecto llevan
ahora su fondo `Paleta.CAMPO`. **Sin verificar en dedo**, igual que el resto de la
cara: que la pantalla se vea, que la nube conteste y que «probar» no trabe la interfaz
es lo que hay que mirar al instalar este APK.

## Compilar a mano (no hace falta)

```
bash apps/apk/compilar.sh 0.15.0     # requiere ANDROID_HOME con build-tools y un platform
```

Está pensado para el pipeline (`.github/workflows/compilar-apk.yml`); en un
portátil con SDK completo también funciona. En el de la dueña, no: sin `javac`.
