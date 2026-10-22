# Si Google o Play Protect no te dejan instalar el APK

Escrito el 2026-10-21 después de medir el `CORT-IA-2.3.0.apk` publicado (se bajó
entero y se leyó byte a byte en el portátil) y aumentado el 2026-10-22 con las dos
medidas de la fecha: los dos envases de `v0.2.28-demo` bloqueados por la dueña, y la
charca de permisos de los tres APK leída del binario. No es una lista de consejos: cada
renglón de la primera tabla es una comprobación hecha sobre el archivo que está en
la Release, y las de la segunda tabla son los mensajes tal cual los muestra Android.

## Y al final, el resultado: **el `nucleo` entra** (2026-10-22, noche)

La dueña instaló `CORT-IA-2.5.0-nucleo.apk` y funcionó («me gustó, funcionó… las
interfaces táctil muy bien»). Con los tres envases de la misma Release, la misma llave y
el mismo `versionCode`, la bisección queda cerrada con **una sola variable**:

| envase | permisos | servicios `BIND_*` | en su teléfono |
| --- | --- | --- | --- |
| `1.1.4` (el de siempre, 1,7 MB) | 13 | 0 | entra |
| `2.4.2` y `2.4.2-ligero` | 28 | 4 | **bloqueado** — y el ligero pesa 1,6 MB: el peso no era |
| **`2.5.0-nucleo`** | **21** | **0** | **entra y funciona** |
| `2.5.0` (completo) | 28 | 4 | **sin probar de nuevo**: es la misma superficie del `2.4.2` bloqueado, y ella no volvió a instalarlo |

Dos cosas que conviene tener claras, porque cambian las rondas siguientes:

* **El payload quedó exonerado.** El núcleo que ella usa ahora lleva dentro las cuatro
  `.so` de Vosk y el modelo de ~40 MB. No era el bulto, ni el modelo, ni JNA, ni el ZIP.
* **La reinstallabilidad es un presupuesto.** Cada superficie de integración (`BIND_*`,
  `ACTION_ASSIST`, Accesibilidad) gasta parte de él. Por eso las funciones que las
  necesitan se publican en **escalones** (`nucleo` → `nucleo+avisos` → `completo`) y se
  elige con el precio delante: `docs/PLAN-MAESTRO.md`.

Lo de abajo sigue sirviendo para lo que ya no es el caso de CORT (y para cuando cambie de
móvil o de capa de fabricante): cómo se mide un APK, qué significa cada frase de Android y
qué se pulsa en cada una.

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

## La medida del 2026-10-22 (segunda parte): el peso era inocente y el manifiesto no

La dueña probó los dos envases de `v0.2.28-demo` y trajo el resultado: **«los dos
fallan, Play Protect sigue bloqueando»**. Con eso cae la hipótesis del bulto nativo —
y cae por su propio peso, porque el ligero son 1,6 MB sin una sola `.so` y sin modelo,
y se bloquea exactamente igual que el de 47 MB. Quedaba lo que el párrafo de arriba
ya avisaba: si el `1.1.4` entra y el ligero no, la diferencia no está en lo que ocupa
sino en **lo que el archivo declara**.

Se volvió a medir, esta vez la superficie de integración entera, con el mismo método
(charco de cadenas UTF‑16 del `AndroidManifest.xml` **binario**, ahora dentro de
`scripts/audita-apk.sh`, así que el pipeline lo repite en cada Release) sobre los tres
APK que están en el mismo disco:

| APK | permisos en el binario | servicios privilegiados (`BIND_*`) | instala |
| --- | --- | --- | --- |
| `CORT-IA-1.1.0.apk` | **13** | **0** | sí |
| `CORT-IA-1.1.4.apk` | **13** | **0** | sí |
| `CORT-IA-2.4.2-ligero.apk` | **28** | **4**, repartidos en cinco servicios | no |

Los cuatro `BIND_*` del 2.x son `BIND_VOICE_INTERACTION` (ser el asistente del
sistema), `BIND_SPEECH_RECOGNIZER`, `BIND_NOTIFICATION_LISTENER_SERVICE` (leer todas
las notificaciones, WhatsApp incluido) y `BIND_QUICK_SETTINGS_TILE` (el baldosín de la
cortina rápida), más las acciones `ASSIST` y `VOICE_COMMAND`. Los permisos gordos que
todos señalaban (`MANAGE_EXTERNAL_STORAGE`, `SYSTEM_ALERT_WINDOW`,
`REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`, `READ_EXTERNAL_STORAGE`) están en **los tres**
archivos: nunca fueron la diferencia.

Lo que se parece a un troyano de accesibilidad, a ojos de un escáner sin contexto, no
es el tamaño ni el permiso de almacenar: es **declarar que uno es el asistente del
teléfono, que escucha todas las notificaciones y que contesta llamadas**. CORT lo
declara porque lo hace de verdad —es justo lo que la dueña pidió—, pero un clasificador
automático no tiene forma de saberlo.

### La respuesta: dos perfiles de manifiesto, una sola variable

`apps/apk/perfil.py` corta el `AndroidManifest.xml` en dos perfiles y el pipeline
compila **los dos**. La superficie de integración vive en tres regiones marcadas del
manifiesto (`llamadas`, `acciones-asistente`, `servicios-privilegiados`), y el perfil
`nucleo` tira esas tres regiones y nada más:

| Perfil | `<uses-permission>` en la fuente | `<service>` | cadenas privilegiadas |
| --- | --- | --- | --- |
| `completo` | 24 | 6 | 12 |
| `nucleo` | **21** | **1** (`.Reproductor`) | **0** |

Y aquí está la parte que hace que la comparación siga siendo limpia, comprobada
renglón a renglón por `scripts/prueba-costura.py` (sector 14): el manifiesto del
`completo` **es byte a byte el manifiesto de siempre**, con una sola línea añadida
(`com.cort.ia.PERFIL`) y las seis líneas de marcador fuera — los marcadores son
comentarios, y aapt2 nunca copia comentarios al binario. O sea: el `completo` de la
2.5.0 no introduce ni un cambio extra que ensucie la prueba.

Además el recorte no deja puertas mudas. El APK lleva dentro escrito su perfil
(`<meta-data android:name="com.cort.ia.PERFIL">`), `CortNative.capacidades()` lo lee,
y la cara **se niega con una frase** en vez de ofrecer el botón: en el núcleo «lee mis
avisos», «ponme de asistente» y «llama a…» contestan que ese envase no trae esa
integración, y la hoja Equipo canta `envase nucleo`. Lo que queda intacto en el núcleo:
la cara y el orbe, el chat y el código, el cerebro con sus reglas, las
automatizaciones, el reproductor con su notificación y el doble toque del auricular, el
micro (con el reconocedor del sistema o Vosk según el envase), los sensores, la cámara
de gestos, el ordenador de archivos y música, el puente Wi‑Fi con los cerebros de casa.

### Los tres envases de `v0.2.29-demo`, medidos, y el orden de la prueba

Los tres archivos están publicados y **los tres se bajaron y se leyeron por dentro en
este portátil** (2026-10-22), así que los números de abajo no los declara el guion:

| Archivo | peso | `sha256` | entradas | manifiesto binario |
| --- | --- | --- | --- | --- |
| `CORT-IA-2.5.0.apk` | 47.394.545 B | `245fd423…3a4e20f4` | 49 | 16.048 B · **28 permisos · 4 `BIND_*`** · `perfil declarado: completo` |
| `CORT-IA-2.5.0-nucleo.apk` | 47.394.545 B | `761d9bee…de22564c` | 49 | 12.636 B · **21 permisos · 0 `BIND_*`** · `perfil declarado: nucleo` |
| `CORT-IA-2.5.0-nucleo-ligero.apk` | 1.621.264 B | `344f8853…75edde30` | 44 | el **mismo** manifiesto que el núcleo (12.636 B, `sha256 b61c275d3df963a9…` en los dos) · **cero** `.so` · **cero** `assets/motor/` |

Dos detalles que valen la lectura: el completo y el núcleo **pesan lo mismo comprimido y
no son el mismo archivo** —el sin‑comprimir baja 3.412 B, que es exactamente lo que
miden los 16.048 − 12.636 del manifiesto—, y el núcleo‑ligero comparte manifiesto byte a
byte con el núcleo, así que cada variable está aislada en su propio eje: el perfil toca
el manifiesto y no el peso; la variedad toca el peso y no el manifiesto.

Instala **primero** `CORT-IA-2.5.0-nucleo.apk`. Es la prueba que decide, y las tres
variantes se pueden pisar una sobre otra porque son el mismo paquete, la misma llave
`fa:ab:ef:46…` y el mismo `versionCode` 20500:

* **Entra el `nucleo` y no el `completo`** → era la superficie privilegiada. Ahí se
  decide con la dueña qué se queda: o CORT vive sin el gesto de asistente, el baldosín
  y el oído de notificaciones (envase que entra siempre), o se acepta el aviso y se
  instala por la vía de abajo.
* **No entra el `nucleo` pero sí el `nucleo-ligero`** → se suma el modelo de 40 MB a la
  lista de sospechosos y se saca del APK (se bajaría la primera vez que se pida el
  oído). La 2.5.0 ya publica ese envase, así que la prueba no cuesta otra ronda.
* **No entra ninguno de los dos** → dentro del archivo no queda nada que cambiar: el
  veredicto es contra el par `com.cort.ia` + llave auto-firmada en la cuenta de Google
  de ella. Entonces se instala por `adb` o por Play, con los pasos de abajo, y se
  reporta la app como falsa alarma desde el propio cuadro de Play Protect.

Lo que **no** se ha tocado, a propósito: la llave de firma. Cambiarla obliga a
desinstalar y se llevan el perfil, la clave de Groq apuntada en el teléfono y las notas
guardadas, y eso está prohibido por pedido expreso de la dueña.

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
* **No se quitaron los cuatro permisos gordos** (`SYSTEM_ALERT_WINDOW` para el puntito
  de escucha, `MANAGE_EXTERNAL_STORAGE` y `READ_EXTERNAL_STORAGE` para «ordena mis
  archivos», `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` para que el micro no se corte).
  Están también en el `1.1.4` que a ella se le instala, así que **no** son la
  diferencia medida, y sin ellos esas funciones dejan de existir. Desde la 2.5.0 sí
  existe un envase que quita lo que los tres APK no comparten —los cinco servicios
  privilegiados y `CALL_PHONE`/`READ_CONTACTS`/`READ_CALENDAR`—: es el `nucleo`, y está
  publicado para que el teléfono decida, no este documento.
* **No se mete un instalador dentro de la app.** Pedir `REQUEST_INSTALL_PACKAGES`
  es justo lo que hace que un móvil se niegue en redondo, y además la
  auto-actualización ya vive en el PC (`/api/update` y `scripts/instala-apk.sh`).

## La vía sin ningún aviso: cable y `adb`

`adb install` no pasa por la pantalla de Play Protect. Hace falta un cable USB y
activar *Depuración USB* en el teléfono (Ajustes ▸ Sistema ▸ Opciones de
desarrollador). En el portátil:

```
bash scripts/instala-apk.sh                        # baja el COMPLETO de la Release y lo instala encima
bash scripts/instala-apk.sh --nucleo               # el envase sin superficie privilegiada (la prueba que decide)
bash scripts/instala-apk.sh --nucleo --ligero      # y el núcleo, además, sin el modelo dentro
bash scripts/instala-apk.sh ~/Descargas/CORT-IA-2.5.0-nucleo.apk
```

Con `adb install -r` encima del CORT que ya tienes no se pierden datos, y el `‑r` es
lo que deja pasar de un envase a otro (completo, núcleo, núcleo‑ligero) aunque pesen
distinto: mismo paquete, misma llave, mismo `versionCode`. **Ojo con el orden de la
Release**: la API enumera los archivos en el orden en que se subieron, así que el
script filtra el nombre por `‑nucleo` y por `‑ligero` en vez de tomar «el primer
`.apk`»; si alguna vez te instala un envase que no pediste, es ese filtro el que se
rompió, y los sectores [13] y [14] de `scripts/prueba-costura.py` están para cazarlo.

El script traduce cada código de error a español y no inventa: si no hay `adb` o no
hay teléfono delante, deja el `.apk` descargado y escribe los pasos de arriba.
