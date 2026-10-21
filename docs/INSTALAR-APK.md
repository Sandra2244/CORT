# Instalar el CORT del teléfono sin que salte un error

Escrito después de medir las firmas de todos los APK publicados (2026-10-21). No es
una lista de consejos generales: cada fila de la tabla salió de `keytool
-printcert -jarfile` sobre el archivo que está en la Release.

## La tabla de llaves, medida

| Archivo de la Release | SHA-256 del certificado | Se instala encima de |
| --- | --- | --- |
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

## Con el teléfono por USB (si algún día tienes `adb`)

```
bash scripts/instala-apk.sh              # baja el último y lo instala si hay teléfono
bash scripts/instala-apk.sh ~/Descargas/CORT-IA-2.2.0.apk
```

El script traduce la salida de `adb install -r` a español con las filas de arriba y
no se calla ningún código raro: lo imprime tal cual.

## Cómo se comprueba que un APK es el publicado

Cada Release trae, junto al `.apk`, un archivo `…-firma.txt` con el peso exacto, las
entradas del ZIP, la proporción de compresión y las huellas del certificado. Si el
`.apk` que instalas pesa lo que dice esa hoja y su huella es `fa:ab:ef:46…`, es el
mismo que salió del compilador de este repo.
