# Si Google o Play Protect no te dejan instalar el APK

Escrito el 2026-10-21 después de medir el `CORT-IA-2.3.0.apk` publicado (se bajó
entero y se leyó byte a byte en el portátil). No es una lista de consejos: cada
renglón de la primera tabla es una comprobación hecha sobre el archivo que está en
la Release, y las de la segunda tabla son los mensajes tal cual los muestra Android.

## Primero: el APK no está roto. Esto es lo que se midió

Se bajaron los dos APK publicados (`2.3.0` y `2.3.1`) y se leyeron byte a byte. El
`2.3.1` es el que está ahora en la Release:

| Lo que mira el instalador | Qué salió en el `CORT-IA-2.3.1.apk` |
| --- | --- |
| El ZIP abre y no está cortado | 47 entradas, CRC íntegro, 47.365.737 bytes |
| sha256 del archivo | `68dce45384573744e43b9a7f04c368715a8dfb3419f1fc2f4ee231b13488ebb5` |
| Esquemas de firma | **v1** (`META-INF/CORT.RSA`) **+ v2 + v3** — los tres |
| La v1, comprobada fuera de `apksigner` | `keytool -printcert -jarfile` la lee, imprime la huella y sale con código **0**, sin una queja |
| Huella del certificado | `faabef468f3ae04fdfab9659…` (la `fa:ab:ef:46…` de siempre) |
| Validez del certificado | desde **2026-10-21 11:19 GMT** hasta 2056-10-13 |
| `resources.arsc` | sin comprimir y alineado a 4 (obligatorio desde Android 11) |
| `minSdk` / `targetSdk` | 26 (Android 8) / 34 (Android 14) |
| ¿Marcado como depurable? | no |
| `REQUEST_INSTALL_PACKAGES` | no se pide: CORT no instala APKs por su cuenta |

Todo eso está impreso también en `CORT-IA-2.3.1-firma.txt`, que viaja al lado del
`.apk`, porque sin sesión de GitHub los registros del pipeline dan 403.

> **Un detalle de la hoja que puede confundir.** En el `-firma.txt` verás dos
> afirmaciones que parecen peleadas: la auditoría dice `firma: v1+v2+v3` y más
> abajo `apksigner verify --verbose` imprime `Verified using v1 scheme (JAR
> signing): false` **mientras sale con código 0**. Las dos son verdad y no hay
> nada que arreglar: `META-INF/CORT.RSA` está, y `keytool` la verifica sin error
> (medido). `apksigner` reserva el `true` de esa línea para el caso en que la v1
> *hiciera falta* para instalar, y con `minSdk 26` nunca hace falta — Android 8+
> comprueba el bloque de firma v2/v3, y ahí la hoja dice `true`. Lo que
> decide si puedes instalar **encima** del CORT que ya tienes es la **llave**
> (`fa:ab:ef:46…`), no el esquema, y esa llave no se ha movido desde el 2.0.0.

O sea: no hay ningún defecto que justifique un bloqueo. Lo que pasa es otra cosa.

## La regla de Google, dicha sin adornos

Play Protect **analiza** cualquier app que no esté en Google Play y que esté firmada
con un certificado auto-firmado como el de CORT, y decide por archivo: a veces deja
instalar con un aviso que se puede descartar y a veces **bloquea** sin dar opción. No
hay bandera dentro del APK que apague ese veredicto: lo único que lo quita de encima
es publicar la app en Play (cuenta de desarrollador y revisión), y no es el caso. Lo
que sí se puede hacer desde el repo —y se hizo en el `2.3.1`— es no dar ningún motivo
extra: firmar por los tres esquemas a la fuerza, que el `sha256` y la ventana del
certificado viajen publicados en el `-firma.txt` de cada Release, y que el pipeline
**se ponga rojo** si algún APK sale sin firmar, truncado o marcado como depurable.

Que el aviso sea **dismissible** o **bloqueante** no lo decide el APK: en la pantalla
hay que buscar el texto pequeño, que casi nadie ve porque está debajo del titular,
gris, y en Android 14 además hay que desplegar «Opciones avanzadas» para que
aparezca. Cuando no aparece ningún botón, el cuadro ya está en la segunda categoría, y
lo que hay que determinar es **por qué archivo** lo bloqueó Google — eso es lo que
resuelve la prueba de la sección siguiente.

## La medida del 2026-10-22: el «es por ser auto-firmado» no se sostiene

La dueña trajo un dato que vale más que cualquier teoría: **el
`CORT-IA-1.1.4.apk` se le instala bien, y el `2.x` le sale «aplicación bloqueada para
proteger tu dispositivo»**. Los dos son auto-firmados, los dos los compilé yo, y los
dos certificados tienen la misma pinta (ventana corta, asunto `CN=CORT`). Se bajaron
los dos y se leyó el `AndroidManifest.xml` de cada uno (el charco de cadenas UTF-16
del binario, que es lo que ve el instalador). Los **permisos gordos no son la
diferencia**:

| Permiso | `1.1.4` (se instala) | `2.4.1` (bloqueado) |
| --- | --- | --- |
| `MANAGE_EXTERNAL_STORAGE` | sí | sí |
| `SYSTEM_ALERT_WINDOW` | sí | sí |
| `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` | sí | sí |
| `READ_MEDIA_AUDIO`, `RECORD_AUDIO`, `POST_NOTIFICATIONS`, `CAMERA`, `SET_ALARM`… | sí | sí |
| **`.so` nativas dentro** | **ninguna** | **cuatro** (Vosk + JNA, 5.868.445 B) |
| **modelo de español dentro** | **no** | **sí** (39.817.833 B comprimidos, 60.286.598 B al desempacar) |
| Peso del archivo | 1.756.727 B | 47.390.449 B |

Es decir: lo único que tienen los 2.x y no tiene el 1.1.4 es **el bulto nativo del
oído sin nube**. Y eso es justo el patrón que más pesa en un clasificador automático:
código que carga bibliotecas nativas por medio de **JNA** (`libjnidispatch.so`, un
clásico de los empaquetadores de malware) y un **ZIP de 40 MB metido dentro** del APK.
No es que CORT sea malware; es que *parece* empaquetado, y el veredicto lo da el
escáner de Google, no este repo.

**No se puede comprobar desde el portátil.** El bloqueo lo produce el servicio de
Google en el teléfono (o su análisis en la nube contra el hash del archivo); aquí no
hay forma local de pedir ese veredicto. Lo que sí se puede hacer es **dejar una sola
variable por medir**, y para eso la Release `v0.2.28-demo` sube dos APK:

1. **`CORT-IA-2.4.2-ligero.apk`** — **1.621.264 bytes**, 44 entradas, `sha256`
   `aac4aa2524f9bd4f…8d9d5043`: mismo manifiesto, mismos permisos, misma llave, mismo
   `versionCode` 20402, misma cara, sus vías de arranque, mismo reproductor, mismos
   avisos, mismo cerebro, mismas automatizaciones. **Sin las `.so` ni el modelo**: el
   bloque `Equipo ▸ 7 · Oído` muestra `sin-modelo` y la escucha va con el reconocedor
   del sistema, igual que en el 2.2.0.
2. **`CORT-IA-2.4.2.apk`** — **47.390.449 bytes**, 49 entradas, `sha256`
   `39a5a7d0849f5e29…82b2e3`: el completo, con el oído dentro.

Los dos archivos se bajaron en este portátil y se leyeron por dentro, así que la
afirmación «es el mismo CORT menos el bulto nativo» no es una promesa del guion: los
`AndroidManifest.xml` de los dos `.apk` **son los mismos byte a byte** (15.860 B,
`sha256` `8a2a74c2f077e5c5…`), en el ligero no hay **ni una** entrada `lib/` ni `assets/motor/`
(leídas dentro del ZIP), y el `-firma.txt` de cada uno canta
`INSTALABLE` con v1+v2+v3 y la llave `fa:ab:ef:46…`. Fíjate en el detalle que salta:
el ligero pesa **menos** (1.621.264 B) que el `1.1.4` que a ella se le instala bien
(1.756.727 B). Si el `1.1.4` entra y el ligero no, el problema ya no es ni el peso ni
el bulto nativo: es la cuenta o el paquete.

La prueba son dos minutos y el resultado manda:

* **Se instala el ligero y no el completo** → el culpable es el bulto del oído. La
  solución de verdad es sacarlo del APK: el modelo se bajaría la primera vez que
  enciendas el oído (ya hay código de desempaque y de «¿cabe?» en `Oido.kt`, sólo que
  hoy lee del `assets` en vez de una URL) y el APK vuelve a pesar 2 MB con el oído
  disponible. Lo anoto como la ronda siguiente.
* **Se bloquean los dos** → el peso y las `.so` son inocentes y lo que está marcado es
  el par `com.cort.ia` + la llave `fa:ab:ef:46…` en el servicio de Google. Ahí no hay
  nada que compilar: se pulsa «instalar de todos modos» cuando aparece, se reporta la
  app como falsa alarma desde el propio cuadro de Play Protect, o se pasa por la vía
  de abajo (`adb`).
* **Se instala el completo** → el aviso de antes era transitorio (hash nuevo, análisis
  pendiente) y no hay que cambiar nada.

> La comparación con el `1.1.4` **no** es una invitación a usarlo: pesa poco porque le
> falta media app (sin reproductor, sin avisos, sin hojas, sin oído, sin
> automatizaciones). Sirve sólo como prueba de que el teléfono de ella instala APK
> auto-firmados míos sin bloquear.

## Qué pulsar según la frase exacta que te sale

| Lo que ves en la pantalla | Qué es de verdad | Cómo se pasa |
| --- | --- | --- |
| «Este archivo puede dañar tu dispositivo» y **no se descarga** (Chrome) | es el escáner del navegador, no del teléfono | en Chrome: menú ⋮ ▸ Descargas ▸ en la fila del `.apk`, «Mantener» / «Permitir de todos modos». Si no aparece: bájalo con Firefox o con el navegador del propio teléfono, o bájalo en el portátil y pásalo por cable / tarjeta SD / LocalSend |
| «Play Protect no reconoce esta aplicación» / «Puede poner en peligro tu dispositivo» | el aviso de app desconocida | pulsa el titular o **«Más información»** ▸ luego **«Instalar esta aplicación de todos modos»**. No desinstala nada: tus datos y tus permisos se quedan |
| «Para tu seguridad, no se permite instalar aplicaciones desconocidas» | falta el permiso **por app** | Ajustes ▸ Aplicaciones ▸ ⋮ ▸ *Instalar apps desconocidas* ▸ elige el **explorador de archivos** (o Chrome) ▸ activa «Confiar en fuentes desconocidas» ▸ vuelve al `.apk` |
| «No se ha podido instalar porque la firma no coincide» / `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | otra cosa: vienes de un 1.x o del APK original, que llevan **otra llave** | desinstalar **una** vez y reinstalar; desde el 2.0.0 la llave no se mueve. Está explicado en `docs/INSTALAR-APK.md` |
| «El certificado no es válido», «la fecha del certificado es incorrecta», «aún no válido» | el reloj del teléfono va mal | Ajustes ▸ Sistema ▸ **Fecha y hora** ▸ «Automática». El certificado de CORT empieza a ser válido el 2026-10-21 11:19 GMT: si el móvil marca una fecha anterior, Android lo rechaza y el fallo parece de seguridad pero es de hora |
| «Espere a que Play Protect analice la aplicación» y se queda girando | está consultando la reputación por red y no la encuentra | instala **sin red**: activa el modo avión (o apaga Wi‑Fi y datos) y abre el `.apk` otra vez. Sin conexión no hay consulta, y el aviso se puede aceptar |
| Pantalla roja de «riesgo» con cuenta atrás (Xiaomi / Redmi / HyperOS) | el escaneo propio de MIUI, aparte de Play | en esa pantalla: **«Detalles» ▸ «Instalar»**; y una sola vez: Ajustes ▸ Apps ▸ ⋮ ▸ *Permisos especiales* ▸ *Instalar apps desconocidas* ▸ Archivos. Si repite, en Ajustes ▸ Seguridad ▸ desactiva «Escanear apps» mientras instalas |
| «Bloqueo de descargas desconocidas» (Samsung) | el interruptor propio de Samsung | Ajustes ▸ Biometría y seguridad ▸ desactiva **«Bloquear descargas desconocidas»** un momento; o Play Store ▸ Play Protect ▸ ⚙ ▸ «Analizar aplicaciones» OFF, instalar, y volverlo a ON |
| «Instalación bloqueada por tu administrador» | hay un perfil de trabajo o de escuela en el teléfono | ahí no hay truco honesto: hace falta quitar el perfil o instalar desde el perfil personal |

El orden que más rápido funciona (pruébalo tal cual, paso a paso):

1. Que el archivo **no haya pasado por Chrome**: baja el `.apk` en el portátil y
   pásalo por cable o por SD, o usa otro navegador en el teléfono.
2. Ábrelo desde la app **Archivos** del teléfono, no desde el navegador.
3. Si sale el aviso: **despliega «Más información»** y pulsa **«Instalar de todos
   modos»**.
4. Si no deja: **modo avión** y repite el paso 2.
5. Si todavía no: **Play Protect ▸ ⚙ ▸ «Analizar aplicaciones» OFF** unos minutos,
   instala, y vuelve a activarlo. Ninguno de estos pasos borra tus datos.

## Cómo saber que el archivo que tienes es el que salió del compilador

Cada Release trae a la par `CORT-IA-<versión>.apk` y `CORT-IA-<versión>-firma.txt`.
En esa hoja están el peso exacto, el `sha256`, los esquemas de firma y la ventana
del certificado, medidos sobre el archivo ya firmado. En el portátil:

```
sha256sum Descargas/CORT-IA-2.3.1.apk     # y compara con la hoja
stat -c '%s' Descargas/CORT-IA-2.3.1.apk  # el peso, byte a byte
```

Si los dos cuadran, lo que tienes en la mano es idéntico a lo que produjo el
pipeline; si el peso es menor, la descarga se cortó a mitad y Play Protect tiene
razón en avisar.

## Lo que NO se hizo, y por qué se dejó a propósito

* **No se cambió el certificado** por uno con nombre y apellidos en el asunto. El
  actual dice `CN=CORT, OU=asistente local, O=local`. Cambiarlo es **cambiar de
  llave**, y para Android eso significa desinstalar el CORT que ya tienes: se irían
  el perfil, la clave de Groq apuntada en el teléfono, tus notas y los permisos
  concedidos. Se pidió expresamente no perder esos datos, así que la llave es la
  misma desde el 2.0.0.
* **No se quitaron los permisos que Play Protect pesa más** (`SYSTEM_ALERT_WINDOW`
  para el puntito de escucha, `MANAGE_EXTERNAL_STORAGE` para «ordena mis
  archivos»). Sin ellos esas dos funciones dejan de existir. Si tu teléfono aun así
  no lo deja entrar, se puede publicar una **variante sin esos dos permisos** con
  todo lo demás igual; dilo y se monta.
* **No se mete un instalador dentro de la app.** Pedir `REQUEST_INSTALL_PACKAGES`
  es justo lo que hace que un móvil se niegue en redondo, y además la
  auto-actualización ya vive en el PC (`/api/update` y `scripts/instala-apk.sh`).

## La vía sin ningún aviso: cable y `adb`

`adb install` no pasa por la pantalla de Play Protect. Hace falta un cable USB y
activar *Depuración USB* en el teléfono (Ajustes ▸ Sistema ▸ Opciones de
desarrollador). En el portátil:

```
bash scripts/instala-apk.sh                       # baja el COMPLETO de la Release y lo instala encima
bash scripts/instala-apk.sh --ligero              # baja el envase sin el oído dentro (la prueba)
bash scripts/instala-apk.sh ~/Descargas/CORT-IA-2.4.2.apk
```

Con `adb install -r` encima del CORT que ya tienes no se pierden datos, y el `‑r` es
lo que deja instalar el ligero sobre el completo (o al revés) aunque pesen distinto:
mismo paquete, misma llave, mismo `versionCode`. **Ojo con el orden de la Release**:
la API enumera el ligero *antes* que el completo, así que el script filtra por nombre;
si alguna vez te instala el que dice `sin-modelo` sin que lo pidieras, es ese filtro
el que se rompió, y el sector [13] de `scripts/prueba-costura.py` está para cazarlo.

El script traduce cada código de error a español y no inventa: si no hay `adb` o no
hay teléfono delante, deja el `.apk` descargado y escribe los pasos de arriba.
