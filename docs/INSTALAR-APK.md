# Instalar el CORT del teléfono sin que salte un error

Escrito después de medir las firmas de todos los APK publicados (2026-10-21). No es
una lista de consejos generales: cada fila de la tabla salió de `keytool
-printcert -jarfile` sobre el archivo que está en la Release.

## La tabla de llaves, medida

| Archivo de la Release | SHA-256 del certificado | Se instala encima de |
| --- | --- | --- |
| `CORT-IA-2.8.0.apk` (v0.2.36-demo) | la misma `fa:ab:ef:46:8f:3a…` (leída en su `-firma.txt` y **comprobada bajando el archivo en este portátil**: **47.443.765 bytes** sobre 62.077.803 sin comprimir, **50 entradas**, proporción 0,76, `sha256 2734c20c1649cddccbc58af0a4fb199857ba345f0e06c4bc5c4e0fb16856c0a9` — exacto a su hoja, al `-firma.txt` y al digest que declara la API; CRC de las 50 entradas íntegros; `versionCode` **20800**, veredicto `INSTALABLE`; manifiesto binario **16.048 B, 28 permisos y 4 servicios `BIND_*`**, `perfil declarado: completo`; y **la cara F11 dentro**: `assets/ui/` con **15 archivos**, 1.844.863 B sueltos / 435.789 B comprimidos, **sin sonda del taller**) | cualquier 2.x: **20800 > 20700**, así que entra ENCIMA del 2.7.0 sin desinstalar y sin perder perfil, clave de Groq, micrófono concedido ni gustos |
| `CORT-IA-2.8.0-nucleo.apk` (v0.2.36-demo) | **la misma** (`versionCode` **20800**; **47.443.765 bytes** —pesa igual que el completo y **no es el mismo archivo**: `sha256 b010f2a539b9c427e8365a5c70faa147309e0ccafafc16d383f8f2bfafaec320`, 62.074.391 sin comprimir, **3.412 B menos**, que es exactamente la diferencia de manifiesto—, bajado y hasheado aquí, CRC íntegros; su `AndroidManifest.xml` binario **cuenta 21 permisos y CERO `BIND_*`** y pesa **12.636 B —los mismos que en la 2.7.0**: el aviso de la bajada no añadió ni una línea al manifiesto—; `-firma.txt` de 3.746 B con veredicto `INSTALABLE`) | igual que el completo. **Es el envase recomendado**: el `nucleo` ya está probado y funcionando en el teléfono de la dueña desde el 2026-10-22, y es el que lleva la cara de la F11 con su aviso de bajada |
| `CORT-IA-2.8.0-nucleo-ligero.apk` (v0.2.36-demo) | **la misma** (`versionCode` **20800**; **1.674.580 bytes** sobre 4.643.436 sin comprimir, 45 entradas, proporción 0,36, `sha256 9c5f38757557cd8d6050daef28eaf46b167e00c8c6b4cacab1b5c3d5f13d3e98`, bajado y hasheado aquí; **cero** entradas `lib/*.so` y **cero** `assets/motor/`, leído dentro del `.apk`; su `AndroidManifest.xml` es **byte a byte el del núcleo** —los dos, 12.636 B y `sha256 20c2d51167dff910…`—, así que la variedad no toca el manifiesto y el perfil no toca el peso. *La huella del manifiesto cambia con cada versión porque dentro va escrita la `versionName`: para comparar, compara los dos envases de LA MISMA etiqueta* | los otros dos. Existe para separar las dos variables de Play Protect, no para el uso diario |
| `CORT-IA-2.7.0.apk` (v0.2.33-demo) | la misma `fa:ab:ef:46:8f:3a…` (leída en su `-firma.txt` y **comprobada bajando el archivo en este portátil**: **47.435.573 bytes** sobre 62.049.149 sin comprimir, **50 entradas**, proporción 0,76, `sha256 6d3c95c2c685f0a40fd6843a0d5860db0800765d19d5244b1486fc2e39e8d998` — exacto a su hoja y CRC de las 50 entradas íntegros; `versionCode` **20700**, veredicto `INSTALABLE`; manifiesto binario **16.048 B, 28 permisos y 4 servicios `BIND_*`**, `perfil declarado: completo`; y **la cara F10 dentro**: `assets/ui/` con **15 archivos**, 1.818.285 B sueltos / 428.148 B comprimidos, **sin la sonda del taller** —el `sonda-*.html` que en la 2.6.0 viajaba sin utilidad ya no está, leído dentro del `.apk`—) | cualquier 2.x: **20700 > 20600**, así que entra ENCIMA del 2.6.0 sin desinstalar y sin perder perfil, clave de Groq, micrófono concedido ni gustos |
| `CORT-IA-2.7.0-nucleo.apk` (v0.2.33-demo) | **la misma** (`versionCode` **20700**; **47.435.573 bytes** —pesa igual que el completo y **no es el mismo archivo**: `sha256 f2ffbf26fbc10f0bd1482253a30bedac729a2d600a0c281090be81ec7bcefc5c`, 62.045.737 sin comprimir, **3.412 B menos**, que es exactamente la diferencia de manifiesto—, bajado y hasheado aquí, CRC íntegros; su `AndroidManifest.xml` binario **cuenta 21 permisos y CERO `BIND_*`** y pesa 12.636 B (`sha256 5118287f97be22df…`); `-firma.txt` de 3.746 B con veredicto `INSTALABLE`) | igual que el completo. **Es el envase recomendado**: el `nucleo` ya está probado y funcionando en el teléfono de la dueña desde el 2026-10-22, y es el que lleva la Música de la F10 |
| `CORT-IA-2.7.0-nucleo-ligero.apk` (v0.2.33-demo) | **la misma** (`versionCode` **20700**; **1.662.292 bytes** sobre 4.614.778 sin comprimir, 45 entradas, proporción 0,36, `sha256 937ad3284c5af727257c1bffb8f4da1bdb78f10f43561c4b954417b58a1a5e5e`, bajado y hasheado aquí; **cero** entradas `lib/*.so` y **cero** `assets/motor/`, leído dentro del `.apk`; su `AndroidManifest.xml` es **byte a byte el del núcleo** —los dos, 12.636 B y `sha256 5118287f97be22df…`—, así que la variedad no toca el manifiesto y el perfil no toca el peso. *La huella del manifiesto cambia con cada versión porque dentro va escrita la `versionName`: para comparar, compara los dos envases de LA MISMA etiqueta* | los otros dos. Existe para separar las dos variables de Play Protect, no para el uso diario |
| `CORT-IA-2.6.0.apk` (v0.2.31-demo) | la misma `fa:ab:ef:46:8f:3a…` (leída en su `-firma.txt`; **47.431.550 bytes** comprimidos sobre 62.036.282 sin comprimir, **51 entradas**, proporción 0,76, `sha256 795b5bd04b62cbd9cdcefdcdb9447c25f8e3a927b1a8c49e145f9963fbbd8ebf` — **bajado y hasheado en este portátil: exacto a su hoja**, CRC de las 51 entradas íntegros; `versionCode` **20600**, firma v1+v2+v3, `resources.arsc` sin comprimir y alineado, no depurable, veredicto `INSTALABLE`; manifiesto binario: **28 permisos y 4 servicios `BIND_*`**, `perfil declarado: completo`; y **la cara F9 dentro**: `assets/ui/` con 16 archivos, 1.811.416 B sueltos / 426.628 B comprimidos, con `css/apps.css` ya dentro —y con la sonda del taller viajando de más, corregido en la 2.7.0—) | cualquier 2.x: **20600 > 20500**, así que se instala ENCIMA del 2.5.0 sin desinstalar y sin perder perfil, clave de Groq, micrófono concedido ni gustos |
| `CORT-IA-2.6.0-nucleo.apk` (v0.2.31-demo) | **la misma** (`versionCode` **20600**; **47.431.550 bytes** — pesan igual que el completo y **no son el mismo archivo**: `sha256 7336d73722ddb68cff9ddf1958eaf6c8d5b3a2513df8c700a50236669a7a63b0`, 62.032.870 sin comprimir, **3.412 B menos**, que es exactamente la diferencia de manifiesto — bajado y hasheado aquí, CRC íntegros; su `AndroidManifest.xml` binario **cuenta 21 permisos y CERO `BIND_*`**, con un solo `<service>` (`.Reproductor`) y 12.636 B frente a los 16.048 B del completo; `-firma.txt` de 3.746 B con veredicto `INSTALABLE`) | igual que el completo. **Es el envase recomendado**: el `2.5.0-nucleo` ya está probado y funcionando en el teléfono de la dueña desde el 2026-10-22 |
| `CORT-IA-2.6.0-nucleo-ligero.apk` (v0.2.31-demo) | **la misma** (`versionCode` **20600**; **1.658.269 bytes**, 46 entradas, proporción 0,36, `sha256 3847bb7638e11dc2bc50a3abc5cda275881fb7a66d760636d9c637217e040881`, bajado y hasheado aquí; **cero** entradas `lib/*.so` y **cero** `assets/motor/`; su `AndroidManifest.xml` es **byte a byte el del núcleo** —los dos, 12.636 B y `sha256 2eb742ce3b2a8e74…`—, así que la variedad no toca el manifiesto y el perfil no toca el peso. *La huella del manifiesto cambia con cada versión porque dentro va escrita la `versionName`: para comparar, compara los dos envases de LA MISMA etiqueta* | los otros dos. Existe para separar las dos variables de Play Protect, no para el uso diario |
| `CORT-IA-2.5.0.apk` (v0.2.29-demo) | la misma `fa:ab:ef:46:8f:3a…` (leída en su `-firma.txt`; **47.394.545 bytes** comprimidos sobre 61.923.190 sin comprimir, **49 entradas**, `sha256 245fd423391f0a4c5b440aa112404bef79aee4de7e4d60c46726135e3a4e20f4` — **comprobado bajando el archivo en este portátil**: hashea exacto y las 49 CRC pasan; `versionCode` **20500**, firma v1+v2+v3, `resources.arsc` sin comprimir y alineado, no depurable, veredicto `INSTALABLE`; manifiesto binario leído del `.apk`: **28 permisos y 4 servicios `BIND_*`**, `perfil declarado: completo`. Es el envase **COMPLETO**: oído offline dentro y superficie entera) | cualquier 2.x, y los otros dos envases: misma llave y mismo `versionCode`, así que el `nucleo` entra encima del `completo` y al revés, sin desinstalar y sin perder perfil, claves ni gustos |
| `CORT-IA-2.5.0-nucleo.apk` (v0.2.29-demo) | **la misma** `fa:ab:ef:46:8f:3a…` (`versionCode` **20500**; **47.394.545 bytes** — pesan igual que el completo y **no son el mismo archivo**: `sha256 761d9bee5f7976ac899f5cb382921984977d71d28bdf7f30edd6482ade22564c`, 61.919.778 sin comprimir, 3.412 B menos, que es exactamente la diferencia de manifiesto — descargado y hasheado aquí, CRC íntegros; su `AndroidManifest.xml` binario **cuenta 21 permisos y CERO `BIND_*`** y pesa 12.636 B frente a los 16.048 B del completo; `-firma.txt` de 3.746 B con veredicto `INSTALABLE`) | igual que el completo. **Es el envase que hay que probar primero** si Play Protect te viene bloqueando los 2.x: su superficie declarada es la del `1.1.4` que se instala |
| `CORT-IA-2.5.0-nucleo-ligero.apk` (v0.2.29-demo) | **la misma** (`versionCode` **20500**; **1.621.264 bytes**, 44 entradas, `sha256 344f8853034b349a5a0a4a035e728280d9060dcfc7b169cf1fb97a5c75edde30`, bajado y hasheado aquí; **cero** entradas `lib/*.so` y **cero** `assets/motor/`; su `AndroidManifest.xml` es **byte a byte el del núcleo** —los dos, 12.636 B y `sha256 b61c275d3df963a9…`—, así que la variedad no toca el manifiesto y el perfil no toca el peso) | los otros dos. Existe para separar las dos variables de Play Protect, no para el uso diario |
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

## ¿Cuál de los tres envases del 2.8.0 bajo?

La Release `v0.2.36-demo` (el **2.8.0**) publica tres APK del mismo CORT. Dentro llevan
la cara de la F10 que ella pidió —las carátulas reales, la pestaña de Vídeos con su
propio tope y en rejilla, el buscador que acierta con tildes y ñ, la letra fusionada
dentro del reproductor, el botón «CORT · PC» que ya no tapa la píldora, el `⋮` con
Velocidad/Dormir/Ocultar/Compartir y la Charla que piensa en el teléfono cuando el
portátil no está— y la de la **F11**: el catálogo de **107 cerebros de casa con el peso
medido en el registro**, la pantalla **Código convertida en copiloto** (planea y ejecuta
los comandos de sólo lectura, con el mando en el portátil), la **paleta de atuendos** y
**el aviso de Android cuando la bajada de un modelo termina o se corta** (`Timbre.java`).
Los cuatro se quedan **en los tres envases**: el aviso no añadió ni un permiso ni un
componente, y el manifiesto del `nucleo` pesa en la 2.8.0 lo mismo exacto que en la 2.7.0
(**12.636 B**, medido dentro del `.apk`), que es la condición que se puso para no volver a
despertar al escáner. Se diferencian por dos cosas, y nada más: la **superficie
privilegiada** que declara el manifiesto y si el **oído sin internet** viaja dentro del
archivo o no.

| Archivo | superficie privilegiada | oído offline dentro | permisos leídos del manifiesto binario |
| --- | --- | --- | --- |
| `CORT-IA-2.8.0.apk` | sí: asistente del sistema, oído de notificaciones, baldosín de la cortina, llamadas y agenda | sí | **28** (y 4 servicios `BIND_*`) |
| `CORT-IA-2.8.0-nucleo.apk` | **no**: cero servicios `BIND_*`, cero `CALL_PHONE`/`READ_CONTACTS`/`READ_CALENDAR` | sí | **21** |
| `CORT-IA-2.8.0-nucleo-ligero.apk` | **no** | no: la hoja Equipo ▸ 7 dice `sin-modelo` y escucha con el reconocedor del sistema | **21** |

**Empieza por el `nucleo`.** Es el envase que tiene que instalarse sí o sí, porque su
superficie declarada es la que tenía el `1.1.4` que a ella le funciona bien. Sigue
siendo el mismo CORT por dentro: la cara y el orbe, el chat, la hoja de código, el
cerebro con sus reglas y sus automatizaciones, el reproductor con su notificación y el
doble toque del auricular, el micrófono, los sensores, la cámara de gestos, el ordenador
de archivos y de música, el puente Wi‑Fi con los cerebros de casa. Lo único que no
ofrece es el gesto del asistente del sistema, el baldosín de la cortina rápida, leer las
notificaciones de WhatsApp, marcar un número y mirar el calendario.

Y no lo esconde a medias: cada envase lleva escrito dentro su perfil
(`<meta-data android:name="com.cort.ia.PERFIL">`), `CortNative.capacidades()` lo lee, la
hoja Equipo canta `envase nucleo`, y las puertas que se fueron contestan con una frase
honesta en vez de con un botón que no hace nada.

Si el `nucleo` entra y el `completo` no, la culpa queda localizada y se decide con ella
qué vía se queda. Si no entra ninguno, dentro del archivo ya no queda nada que cambiar:
está explicado, con la tabla de los tres APK leídos del binario, en
[`docs/BLOQUEO-PLAY-PROTECT.md`](BLOQUEO-PLAY-PROTECT.md).

Para pasar de un envase a otro **no hay que desinstalar nada**: los tres comparten el
paquete `com.cort.ia`, la llave `fa:ab:ef:46…` y el `versionCode` **20800**, así que el
segundo entra encima del primero como reinstalación (el número no baja, luego no es
bajada) y se conservan el micrófono concedido, los gustos de música y la dirección del
PC. Es lo que declara la medida, no lo que se probó en un teléfono: si el instalador de
tu marca pusiera una pega con el mismo número de versión, se desinstala una vez y se
instala el que se quiera dejar —con eso se pierden los ajustes, igual que siempre—.

`bash scripts/instala-apk.sh` por defecto baja el **completo**; `--nucleo` pide el
recortado y `--nucleo-ligero` (o `--nucleo --ligero`) el que además no lleva modelo.

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

Con el **completo** ya puesto, tres gestos valen más que cualquier ajuste: decirle **«pon
CORT como asistente»** (Android abre su cuadro de rol y ahí se elige CORT en vez de
Google — con esto se pierde el «OK Google» con la pantalla apagada, porque eso lo decide
el servidor de Google y no el repo), arrastrar la cortina de ajustes rápidos y **añadir el
baldosín «CORT escucha»** (en Samsung y Xiaomi hay que darle a editar/pulsar «+»), y **mantener
pulsado el icono de CORT** para ver los tres atajos (Escucha · Equipo · Charla). Si tiene
auriculares puestos, prueba el **doble toque** en el botón del auricular: pausa la música y
abre el oído. Todo esto, con los pasos por marca y lo que **no** se puede comprobar sin el
teléfono en la mano, está en [`docs/ABRIR-CORT.md`](ABRIR-CORT.md).

Con el **núcleo** los dos primeros no existen, y la app no finge que existen: al pedirlos
contesta que el envase no trae esa integración. Lo que se prueba entonces es lo que sí
viaja dentro de los tres archivos — **«hola CORT»** con la hoja de escucha abierta,
`☰ ▸ Equipo` para ver la línea `envase nucleo` y el estado de cada bloque, «¿qué hora es?»
o «ordena mis descargas», y el doble toque del auricular sobre el reproductor—.

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
bash scripts/instala-apk.sh                            # baja el COMPLETO de la Release y lo instala por USB
bash scripts/instala-apk.sh --nucleo                   # el envase sin superficie privilegiada (la prueba que decide)
bash scripts/instala-apk.sh --nucleo-ligero            # y el núcleo sin el modelo de 40 MB dentro
bash scripts/instala-apk.sh ~/Descargas/CORT-IA-2.8.0-nucleo.apk
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
