# Instalar el CORT del teléfono sin que salte un error

Escrito después de medir las firmas de todos los APK publicados (2026-10-21). No es
una lista de consejos generales: cada fila de la tabla salió de `keytool
-printcert -jarfile` sobre el archivo que está en la Release.

## La tabla de llaves, medida

| Archivo de la Release | SHA-256 del certificado | Se instala encima de |
| --- | --- | --- |
| `CORT-IA-2.4.2.apk` (v0.2.28-demo) | la misma `fa:ab:ef:46:8f:3a…` (leída en su `-firma.txt`; **47.390.449 bytes** sobre 61.916.323 sin comprimir, **49 entradas**, `sha256 39a5a7d0…82b2e3`, **comprobado bajando el archivo en este portátil**: hashea exacto y los 49 CRC pasan; `versionCode` **20402**, firma v1+v2+v3, `resources.arsc` sin comprimir y alineado, no depurable, veredicto `INSTALABLE`. Es la **variedad COMPLETA**: lleva el oído offline dentro) | cualquier 2.x **y también el otro envase**: se instala encima del `2.0.0` … del `2.4.1` sin desinstalar ni perder datos, y como el `‑ligero` comparte `versionCode` y llave, uno entra encima del otro |
| `CORT-IA-2.4.2-ligero.apk` (v0.2.28-demo) | **la misma** `fa:ab:ef:46:8f:3a…` (`versionCode` **20402**; **1.621.264 bytes** sobre 4.485.356 sin comprimir, **44 entradas**, `sha256 aac4aa25…8d9d5043`, descargado y hasheado aquí: exacto a su hoja y CRC íntegros; **cero** entradas `lib/*.so` y **cero** `assets/motor/`, leído dentro del `.apk`; su `AndroidManifest.xml` es **byte a byte** el del completo —los dos, 15.860 B y `sha256 8a2a74c2f077e5c5…`—). Es la **variedad LIGERA**: sin el oído offline dentro, `Oido.kt` dice `sin-modelo` y se escucha con el reconocedor del sistema) | igual que el completo: misma llave y mismo `versionCode`. Existe para la bisección de Play Protect, no para el uso diario |
| `CORT-IA-2.4.1.apk` (v0.2.27-demo) | la misma `fa:ab:ef:46:8f:3a…` (leída en su `-firma.txt` y en el `apksigner verify --print-certs` del run: huella `faabef468f3ae04f…`; **47.390.449 bytes**, `sha256 ed5761f3…0908a6df`, **comprobado bajando el archivo en este portátil**, las 49 entradas con CRC íntegro, `versionCode` 20401, firma v1+v2+v3 y veredicto `INSTALABLE`) | cualquier 2.x: se instala encima del `2.0.0`, del `2.1.0`, del `2.2.0`, del `2.3.0`, del `2.3.1` y del `2.4.0` **sin desinstalar y sin perder datos** |
| `CORT-IA-2.4.0.apk` (v0.2.25-demo) | la misma `fa:ab:ef:46:8f:3a…` (leída en su `-firma.txt` y en el `apksigner verify --print-certs` del run: huella `faabef468f3ae04f…`; 47.386.289 bytes, `sha256 ee5eb11f…d8b57a`, **comprobado bajando el archivo en este portátil**, firma v1+v2+v3 y veredicto `INSTALABLE`) | cualquier 2.x: se instala encima del `2.0.0`, del `2.1.0`, del `2.2.0`, del `2.3.0` y del `2.3.1` **sin desinstalar y sin perder datos** |
| `CORT-IA-2.3.1.apk` (v0.2.24-demo) | la misma `fa:ab:ef:46:8f:3a…` (leída en su `-firma.txt` **y** verificada en el portátil con `keytool -printcert -jarfile`, que sale en 0; 47.365.737 bytes, `sha256 68dce453…8ebb5`) | cualquier 2.x: se instala encima del `2.0.0`, del `2.1.0`, del `2.2.0` y del `2.3.0` **sin desinstalar y sin perder datos** |
| `CORT-IA-2.3.0.apk` (v0.2.23-demo) | la misma `fa:ab:ef:46:8f:3a…` (leída en su `-firma.txt`; 47.365.737 bytes medidos, `sha256 2aacd93a…8811`) | cualquier 2.x: se instala encima del `2.0.0`, del `2.1.0` y del `2.2.0` **sin desinstalar y sin perder datos** |
| `CORT-IA-2.2.0.apk` (v0.2.18-demo) | la misma `fa:ab:ef:46:8f:3a…` (leída en su `-firma.txt`, y 998.536 bytes medidos) | cualquier 2.x: se instala encima del 2.0.0 y del 2.1.0 |
| `CORT-IA-2.1.0.apk` (v0.2.16-demo) | `fa:ab:ef:46:8f:3a:e0:4f:df:ab:96:59:d6:a0:51:c4:53:d6:de:d7:b9:65:46:8c:9c:3b:85:ca:ff:a3:19:77` | cualquier 2.x |
| `CORT-IA-2.0.0.apk` (v0.2.13-demo) | la misma `fa:ab:ef:46…` | y de ahí se pasa a 2.1.0 sin desinstalar |
| `CORT-IA-1.1.4.apk` (v0.2.10-demo) | `eb:d6:25:04:41:bc:f0:a3:d6:30:e5:71:0c:91:0a:49:cc:94:03:8a:9f:ed:eb:70:8e:59:69:9b:7e:f4:fe:5b` | **otra llave**: un 1.x no acepta un 2.x encima |
| `CORT-v0.17.0.apk` (el APK original) | `52:70:15:47:38:23:87:b7:78:cd:2a:4b:d8:5e:fa:e5:76:89:25:7d:b5:06:11:72:cc:22:54:e6:ca:a4:0f:f3` | **otra llave**: tampoco |
| `CORT-IA-1.1.0.apk` (v0.2.3-demo) | sin firma v1 legible en el portátil (sólo trae v2/v3) | se comprueba en el teléfono |

Android sólo deja instalar una versión nueva por encima si la firma es **la misma**.
Por eso «sale error al instalar» justo al saltar de un 1.x (o del APK original) a un
2.x: no está roto el APK, es otra llave. Desde el 2.0.0 la llave es estable — la del
secreto `CORT_APK_KEYSTORE_B64` del repo — así que el costo es de **una sola vez**.

## ¿Cuál de los dos APK del 2.4.2 bajo?

Por defecto, **el completo** (`CORT-IA-2.4.2.apk`): es el que oye sin internet. El
`CORT-IA-2.4.2-ligero.apk` se baja **sólo si el completo te lo bloquea Play Protect**
—mismo CORT, misma llave, mismos permisos, lo único que le falta dentro es el oído
offline, y en la hoja Equipo ▸ 7 dirá `sin-modelo` y escuchará con el reconocedor del
sistema—. No hay que desinstalar nada para pasar de uno a otro: comparten `versionCode`
20402 y llave, así que el segundo entra encima del primero como reinstalación (el número
no baja, luego no es bajada) y se conservan el micrófono concedido, los gustos y la
dirección del PC. Es lo que declara la medida, no lo que se probó en un teléfono: si el
instalador de tu marca pusiera una pega con el mismo número de versión, se desinstala
una vez y se instala el que se quiera dejar —con eso se pierden los ajustes, igual que
siempre. Si entras en la prueba de la bisección,
cuenta qué pasó con cada uno (la frase exacta del aviso, si es que sale) — eso es lo
que decide la ronda que viene: [`docs/BLOQUEO-PLAY-PROTECT.md`](BLOQUEO-PLAY-PROTECT.md).

> **¿Y si no es la firma, sino Google?** Si lo que sale es un aviso de Play Protect
> («no reconoce esta aplicación», «puede dañar tu dispositivo», «este archivo puede
> dañar tu dispositivo») o el teléfono directamente no deja abrir el `.apk`, ese es
> **otro asunto** y tiene su propia guía, renglón por renglón y por mensaje exacto:
> [`docs/BLOQUEO-PLAY-PROTECT.md`](BLOQUEO-PLAY-PROTECT.md). Ahí está medido que el
> APK viene firmado por las tres vías (v1+v2+v3), con el `resources.arsc` alineado y
> el certificado vigente: no es un defecto del archivo, es el aviso que Google da a
> cualquier app con certificado auto-firmado que no está en Play.

## Los tres pasos, sin cable y sin ordenador

1. Baja `CORT-IA-<versión>.apk` de <https://github.com/Sandra2244/CORT/releases/latest>
   (o corre `bash scripts/instala-apk.sh` en el portátil y pásalo al teléfono).
2. Si dentro del teléfono sigue habiendo un CORT 1.x o el APK original:
   **Ajustes ▸ Aplicaciones ▸ CORT ▸ Desinstalar**. Esto borra lo que CORT recuerda en
   ese teléfono: el perfil, las claves apuntadas ahí y las notas. Anota antes tu clave
   de Groq si la tenías puesta.
3. Abre el `.apk` con el explorador de archivos del teléfono y acepta
   «instalar apps desconocidas» si lo pide. Las veces siguientes ya no hará falta
   desinstalar nada.

## Recién instalado: qué se toca primero

Con el `2.4.2` ya puesto, tres gestos valen más que cualquier ajuste: decirle **«pon
CORT como asistente»** (Android abre su cuadro de rol y ahí se elige CORT en vez de
Google — con esto se pierde el «OK Google» con la pantalla apagada, porque eso lo decide
el servidor de Google y no el repo), arrastrar la cortina de ajustes rápidos y **añadir el
baldosín «CORT escucha»** (en Samsung y Xiaomi hay que darle a editar/pulsar «+»), y **mantener
pulsado el icono de CORT** para ver los tres atajos (Escucha · Equipo · Charla). Si tiene
auriculares puestos, prueba el **doble toque** en el botón del auricular: pausa la música y
abre el oído. Todo esto, con los pasos por marca y lo que **no** se puede comprobar sin el
teléfono en la mano, está en [`docs/ABRIR-CORT.md`](ABRIR-CORT.md).

## El `2.3.0` trae oído: dos cosas que se notan al instalar

* **Pide sitio, no permisos nuevos.** El APK son 45,2 MB. Al instalar, Android
  saca del archivo las cuatro `.so` del motor (**17.433.208 bytes** en crudo, una
  por arquitectura), y en el **primer arranque** CORT desempaca su modelo de español
  (**60.286.598 bytes** sueltos) en su carpeta privada: en total hay que contar unos
  **78 MB libres**. No borra ni mueve nada de tus archivos: si no cabe, la hoja
  `☰ ▸ Equipo ▸ 7 · Oído` dice `sin-sitio`, el oído propio queda apagado y CORT
  sigue escuchando con el reconocedor del sistema. Se puede reintentar liberando
  sitio y volviendo a encender el interruptor del bloque. Con `installLocation="auto"`
  en el manifiesto, si el almacenamiento interno va justo **es Android quien coloca la
  app en la tarjeta**, sin que tengas que hacer nada.
* **No hace falta desinstalar nada** si ya tenías un `2.0.0`, `2.1.0` o `2.2.0`: la
  llave es la misma (`fa:ab:ef:46…`, escrita en el `-firma.txt` de cada Release) y el
  `versionCode` sube (20200 → 20300), así que Android lo ve como una actualización
  normal. El permiso del micrófono, el de los avisos, la dirección del PC y los gustos
  de música se quedan donde estaban.

## Qué significa cada error

| Lo que dice Android | Qué pasa de verdad | Qué hacer |
| --- | --- | --- |
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` / «no se ha podido instalar porque la firma no coincide» | el CORT viejo se firmó con otra llave (tabla de arriba) | desinstalar una vez y reintentar |
| `INSTALL_FAILED_OLDER_SDK` | el teléfono tiene Android 7 o anterior; el suelo del APK es Android 8 (API 26) | no hay arreglo en este APK: hace falta Android 8 o más nuevo |
| `INSTALL_FAILED_VERSION_DOWNGRADE` | ya hay un CORT más nuevo instalado | no instalar; usar el que hay |
| `INSTALL_FAILED_INSUFFICIENT_STORAGE` | no cabe | liberar sitio |
| `INSTALL_PARSE_FAILED_NOT_APK`, «central directory», el peso no cuadra | la descarga se cortó | volver a bajar (el script compara el peso con el que anuncia la Release) |
| `INSTALL_PARSE_FAILED_NO_CERTIFICATES`, «signing failed» | el archivo no es de la Release | bajar el `.apk` oficial |
| «no tienes permiso para instalar apps desconocidas» | falta el permiso por app | Ajustes ▸ Aplicaciones ▸ Instalar apps desconocidas ▸ activarlo para el explorador que uses |
| «El certificado no es válido», «aún no válido», «la fecha es incorrecta» | el **reloj** del teléfono va atrasado: el certificado de CORT empieza a ser válido el 2026-10-21 11:19 GMT (medido en su `META-INF/CORT.RSA`) | Ajustes ▸ Sistema ▸ Fecha y hora ▸ ponerla en automática y reintentar |
| Aviso de Play Protect sin ningún código, y no hay botón de instalar | app auto-firmada y fuera de Google Play: es el aviso, no el APK | la tabla por frase exacta de [`docs/BLOQUEO-PLAY-PROTECT.md`](BLOQUEO-PLAY-PROTECT.md) |

## Con el teléfono por USB (si algún día tienes `adb`)

```
bash scripts/instala-apk.sh              # baja el último y lo instala si hay teléfono
bash scripts/instala-apk.sh ~/Descargas/CORT-IA-2.3.1.apk
```

El script traduce la salida de `adb install -r` a español con las filas de arriba y
no se calla ningún código raro: lo imprime tal cual.

## Cómo se comprueba que un APK es el publicado

Cada Release trae, junto al `.apk`, un archivo `…-firma.txt` con el peso exacto, las
entradas del ZIP, la proporción de compresión y las huellas del certificado. Desde
el `2.3.1` esa hoja trae además la **auditoría de instalabilidad leída del archivo
final**: el `sha256` del APK, los esquemas de firma que realmente están dentro
(v1/v2/v3), la ventana de validez del certificado, si `resources.arsc` va sin
comprimir y alineado y si la app está o no marcada como depurable. Si el `.apk` que
instalas pesa y hashea lo que dice esa hoja, y su huella es `fa:ab:ef:46…`, es el
mismo que salió del compilador de este repo. Si el pipeline saca un APK truncado,
sin firma v2 o depurable, **el run se pone rojo y no se publica**: lo comprueba
`scripts/audita-apk.sh` antes de subir nada.
