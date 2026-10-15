# CORT en el teléfono (APK)

Un cliente WebView de una sola pantalla: abre la página que sirve
`cort.py --lan` en el portátil. El asistente **no se instala en el teléfono** —su
cerebro, su memoria y sus permisos viven en la máquina de siempre—; este APK sólo
es la ventana, para que la cara y el chat estén a mano en la mesa sin abrir el
portátil.

**Por qué un WebView y no Capacitor**: en el portátil de desarrollo (1,8 GiB, sin
JDK) un `gradle build` de Capacitor congela la máquina — está medido y escrito en
`docs/PLATFORM.md`. Aquí no hay Gradle ni AndroidX: una actividad Java, cuatro
herramientas que el runner de GitHub Actions ya trae (`aapt2`, `javac`, `d8`,
`apksigner`) y un script, `compilar.sh`, que **nunca corre en el portátil**.

## Usarlo

1. En el portátil: `python scripts/cort.py --lan` (necesita `CORT_LAN_TOKEN` en
   el `.env`; sin llave el lanzador se niega — `security.py`).
2. Bajar `CORT-v<versión>.apk` de la [Release](https://github.com/Sandra2244/CORT/releases),
   instalarlo (Android pide permiso para «instalar apps desconocidas»: es un
   prototipo firmado en casa, no Play Store).
3. Abrir CORT: la primera pantalla pide dos cosas — la **dirección** que imprime
   el lanzador (`http://192.168.100.xxx:8780`, se puede pegar entera con su
   `?token=`) y la **llave**, si la pegó sin token. Se guarda en
   `SharedPreferences` y no se vuelve a preguntar.
4. Mantener pulsado abre el diálogo para cambiar la dirección o salir.

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
guardada y el APK se actualiza instalando encima. La clave no viaja en el
repositorio (regla 7).

## Compilar a mano (no hace falta)

```
bash apps/apk/compilar.sh 0.13.0     # requiere ANDROID_HOME con build-tools y un platform
```

Está pensado para el pipeline (`.github/workflows/compilar-apk.yml`); en un
portátil con SDK completo también funciona. En el de la dueña, no: sin `javac`.
