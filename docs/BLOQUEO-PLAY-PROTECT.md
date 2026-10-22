# Si Google o Play Protect no te dejan instalar el APK

Escrito el 2026-10-21 después de medir el `CORT-IA-2.3.0.apk` publicado (se bajó
entero y se leyó byte a byte en el portátil). No es una lista de consejos: cada
renglón de la primera tabla es una comprobación hecha sobre el archivo que está en
la Release, y las de la segunda tabla son los mensajes tal cual los muestra Android.

## Primero: el APK no está roto. Esto es lo que se midió

| Lo que mira el instalador | Qué salió en el `CORT-IA-2.3.0.apk` |
| --- | --- |
| El ZIP abre y no está cortado | 47 entradas, CRC íntegro, 47.365.737 bytes |
| sha256 del archivo | `2aacd93a0d8d051f6947b80be78258481de9559091eaa76ea796f50c52488811` |
| Esquemas de firma | **v1** (`META-INF/CORT.RSA`) **+ v2 + v3** — los tres |
| Huella del certificado | `faabef468f3ae04fdfab9659…` (la `fa:ab:ef:46…` de siempre) |
| Validez del certificado | desde **2026-10-21 11:19 GMT** hasta 2056-10-13 |
| `resources.arsc` | sin comprimir y alineado a 4 (obligatorio desde Android 11) |
| ¿Marcado como depurable? | no |
| `REQUEST_INSTALL_PACKAGES` | no se pide: CORT no instala APKs por su cuenta |

O sea: no hay ningún defecto que justifique un bloqueo. Lo que pasa es otra cosa.

## La regla de Google, dicha sin adornos

Play Protect avisa de **cualquier** app que no esté en Google Play y que esté
firmada con un certificado auto-firmado como el de CORT. No hay bandera dentro del
APK que apague ese aviso: se quita publicando la app en Play (cuesta una cuenta de
desarrollador y una revisión), y no es el caso. Lo que sí se puede hacer desde el
repo —y se hizo en el `2.3.1`— es no dar ningún motivo extra: firmar por los tres
esquemas a la fuerza, que el `sha256` y la ventana del certificado viajen publicados
en el `-firma.txt` de cada Release, y que el pipeline **se ponga rojo** si algún APK
sale sin firmar, truncado o marcado como depurable.

Ese aviso es **dismissible** casi siempre. En la pantalla hay que tocar el texto
pequeño: casi nadie lo ve porque está debajo del titular, gris, y en Android 14
además hay que desplegar «Opciones avanzadas» para que aparezca.

## Qué pulsar según la frase exacta que te sale

| Lo que ves en la pantalla | Qué es de verdad | Cómo se pasa |
| --- | --- | --- |
| «Este archivo puede dañar tu dispositivo» y **no se descarga** (Chrome) | es el escáner del navegador, no del teléfono | en Chrome: menú ⋮ ▸ Descargas ▸ en la fila del `.apk`, «Mantener» / «Permitir de todos modos». Si no aparece: bájalo con Firefox o con el navegador del propio teléfono, o bájalo en el portátil y pásalo por cable / tarjeta SD / LocalSend |
| «Play Protect no reconoce esta aplicación» / «Puede poner en peligro tu dispositivo» | el aviso de app desconocida | pulsa el titular o **«Más información»** ▸ luego **«Instalar esta aplicación de todos modos»**. No desinstala nada: tus datos y tus permisos se quedan |
| «Para tu seguridad, no se permite instalar aplicaciones desconocidas» | falta el permiso **por app** | Ajustes ▸ Aplicaciones ▸ ⋮ ▸ *Instalar apps desconocidas* ▸ elige el **explorador de archivos** (o Chrome) ▸ activa «Confiar en fuentes desconocidas» ▸ vuelve al `.apk` |
| «No se ha podido instalar porque la firma no coincide» / `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | otra cosa: vienes de un 1.x o del APK original, que llevan **otra llave** | desinstalar **una** vez y reinstalar; desde el 2.0.0 la llave no se mueve. Está explicado en `docs/INSTALAR-APK.md` |
| «El certificado no es válido», «la fecha del certificado es incorrecta», «aún no válido» | el reloj del teléfono va mal | Ajustes ▸ Sistema ▸ **Fecha y hora** ▸ «Automática». El certificado de CORT empieza a ser válido el 2026-10-21 11:19 GMT: si el móvil marca una fecha anterior, Android lo rechaza y el fallo parece de seguridad pero es de hora |
| «Espere a que Play Protect analice la aplicación» y se queda girando | está consultando la reputación por red y no la encuentra | instala **sin red**: activa el modo avión (o apaga Wi‑Fi y datos) y abre el `.apk` otra vez. Sin conexión no hay consulta, y el aviso se puede aceptar |
| Pantalla roja de «riesgo» con cuenta atrás (Xiaomi / Redmi / HyperOS) | el escáneo de MIUI, aparte de Play | en esa pantalla: **«Detalles» ▸ «Instalar»**; y una sola vez: Ajustes ▸ Apps ▸ ⋮ ▸ *Permisos especiales* ▸ *Instalar apps desconocidas* ▸ Archivos. Si repite, en Ajustes ▸ Seguridad ▸ desactiva «Escanear apps» mientras instalas |
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
bash scripts/instala-apk.sh              # baja el último de la Release y lo instala encima
bash scripts/instala-apk.sh ~/Descargas/CORT-IA-2.3.1.apk
```

El script traduce cada código de error a español y no inventa: si no hay `adb` o no
hay teléfono delante, deja el `.apk` descargado y escribe los pasos de arriba.
