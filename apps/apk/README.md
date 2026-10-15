# CORT en el teléfono (APK)

Un cliente WebView de una sola pantalla: abre la página que sirve
`cort.py --lan` en el portátil. El asistente **no se instala en el teléfono** —su
cerebro, su memoria y sus permisos viven en la máquina de siempre—; este APK sólo
es la ventana, para que la cara y el chat estén a mano en la mesa sin abrir el
portátil.

**Por qué un WebView y no Capacitor**: en el portátil de desarrollo (1,8 GiB) un
`gradle build` de Capacitor congela la máquina — está medido y escrito en
`docs/PLATFORM.md`—, y además aquí no hace falta: `javac` no está (lo que hay es
el JRE 21 y su `keytool`, medido 2026-10-15), así que no hay nada que compilar
en esta máquina ni que descargar. Una actividad Java, cuatro herramientas que el
runner de GitHub Actions ya trae (`aapt2`, `javac`, `d8`, `apksigner`) y un
script, `compilar.sh`, que **nunca corre en el portátil**.

## Usarlo

1. En el portátil: `python scripts/cort.py --lan`. La **llave de red ya no se
   pide**: si no hay `CORT_LAN_TOKEN` en el `.env`, el lanzador la inventa, la
   escribe ahí (archivo ignorado por git, permiso 0600) y sigue arrancando. Para
   que el doble clic del escritorio publique sin escribir banderas, `CORT_LAN=1`
   en el `.env`; para negarlo un arranque, `--sin-lan`.
2. Copiar **el enlace entero** que sale en la línea `● red` del arranque
   (`http://192.168.x.x:8780/?token=…`).
3. Bajar `CORT-v<versión>.apk` de la [Release](https://github.com/Sandra2244/CORT/releases)
   e instalarlo (lea «Instalar aunque Android avise» abajo).
4. Abrir CORT: la primera pantalla tiene **un solo campo**, y lo que se pega en
   él es el enlace del paso 2 tal cual — la llave viaja dentro. Se guarda en
   `SharedPreferences` y no se vuelve a preguntar; las veces siguientes la app
   entra directo a la cara animada.
5. Mantener pulsado (o el botón «atrás») abre el diálogo para cambiar la
   dirección o salir. La dirección se muestra con la llave tapada.

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

| | |
|---|---|
| Chat, reactor, ventanas, muelle, teclado táctil | ✅ la misma cara que en el navegador |
| **Que CORT hable** (`speechSynthesis`) | ✅ en WebView con Chrome, **con la nota del audio sin verificar en dedo** — medido sólo en escritorio |
| **Que CORT escuche** (`SpeechRecognition`) | ❌ **límite real**: el API de reconocimiento de voz del WebView **no existe sin los servicios de Google y no corre en un WebView embebido**. En el teléfono, la escucha se usa abriendo la **PWA** (Chrome → «instalar app»), que es lo que `apps/web` ya trae. Este APK es la ventana; la voz que escucha vive en Chrome |
| Gestos de cámara (`defocus.ts`, `getUserMedia`) | 🔨 sin verificar en dedo: el WebView concede el permiso, pero nadie lo ha medido con esta ventana |
| Memoria, cerebro, acciones, temporizador, agenda | ✅ todo en el core del portátil; el teléfono no guarda nada |

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

El `versionCode` creciente es lo que hace que «instalar encima» con la **llave
estable** sea una actualización y no la misma versión repetida; con firma
desechable, en cambio, cada APK nuevo exige desinstalar el anterior aunque el
número suba.

## Si tocas el manifiesto

`AndroidManifest.xml` se compila con `aapt2 link`, que es **estricto con los
comentarios**: dentro de un bloque de comentario no pueden aparecer dos guiones
seguidos. Escribir ahí el nombre de un flag largo es la forma más rápida de
romper el build, y el fallo se ve en el runner, no en `make test`. Por eso
`services/core/tests/test_apk_manifesta.py` lee el archivo y lo valida, además de
vigilar que el `<manifest>` no vuelva a fijar su propia versión, que el paquete
`dev.sandra.cort` sea el mismo en el manifiesto y en el Java, que ningún import
saque de `android.*` / `java.*` / `dev.sandra.cort` (aquí no hay AndroidX) y que
`compilar.sh` siga pasando el `versionCode` derivado en lugar del `1` clavado.
Las **10** pruebas corren con `make test`.

## Compilar a mano (no hace falta)

```
bash apps/apk/compilar.sh 0.14.3     # requiere ANDROID_HOME con build-tools y un platform
```

Está pensado para el pipeline (`.github/workflows/compilar-apk.yml`); en un
portátil con SDK completo también funciona. En el de la dueña, no: sin `javac`.
