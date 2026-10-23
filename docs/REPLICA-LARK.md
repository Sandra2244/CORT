# La réplica de Lark Player — especificación leída de las capturas

**Fuente:** las 13 capturas que Sandra puso el 2026-10-22 en
`~/Escritorio/Capturas de pantalla para contexto CORT` (teléfono real, Samsung con
One UI, Android 13+, Lark Player en español con su biblioteca de verdad: 1786 vídeos
y varios cientos de canciones). Este documento es **la especificación**: lo que CORT
Música tiene que parecer y lo que tiene que hacer. Cada afirmación lleva la captura
de donde se sacó. Lo que no sale en una captura no se inventa: se marca como
«decisión» o como «no está en Lark».

Las capturas están en el escritorio de Sandra, **no viajan dentro del repo** (son
material de trabajo, no parte del producto). Quien lea este documento sin ellas tiene
aquí la descripción completa.

---

## 0 · El idioma visual (común a todas las pantallas)

Sacado de las ocho capturas de Lark con la biblioteca delante.

| Cosa | Lo que se ve | Regla para CORT |
|---|---|---|
| Fondo | negro puro `#000` en la lista; el reproductor y las hojas teñidas del color de la portada (`#3B2A2A` marrón con la de Tom Welling, `#1E2A1E` verdoso con la de M4) | el tinte se **calcula de la carátula**, no se fija |
| Título de app | «Lark Player» en blanco, negrita, ~28 px, esquina superior izquierda | en CORT: «Música» con el mismo peso |
| Cabecera | a la derecha del título: lupa, ordenar (tres líneas con flecha), ajustes (hexágono/tuerca) | tres botones, sin texto |
| Chips de sección | píldoras: `▶ Videos` · `Canciones` · `Playlists` · `Carpetas` · `Artistas` · `Álbumes`. La activa va en **azul `#2B7FE3` con letra blanca**; las demás en gris `#2A2A2A` con letra gris clara. Entre la primera y la segunda hay un **palito vertical** separador. La fila **se desliza** (en `182021` ya se ven Playlists/Carpetas/Artistas/Álbumes y `Videos` ha salido) | fila deslizante, una activa, sin recargar la página al cambiar |
| Contador | «1786 Vídeos» en gris, y a la derecha un icono de carpeta | el recuento va **debajo del chip**, arriba de la lista |
| Fila de canción | cuadrada: portada de ~88 px con esquinas muy redondeadas, título en blanco negrita de dos líneas con `…`, debajo artista y álbum en gris; si tiene letra, una **píldora `LETRAS`** con borde fino antes del artista; si tiene videoclip, otra píldora `MV` | los badges son de datos, no decorativos |
| Mini-reproductor | pegado abajo, **translúcido teñido del color de la portada**, con portada, título, artista, icono de repetir y botón de pausa en círculo | siempre visible mientras suena algo |
| Hojas que suben | panel a pantalla completa con una **chaveta `⌄`** centrada arriba (arriba queda el mini-reproductor) | las hojas ⋮ / Ordenar / Ecualizador / Letras / Fila son así |

## 1 · La lista de canciones — `182010`

Filas reales de su biblioteca: «You Needed - Slowed / ShadowStorm - You Needed Remixs»,
«Sub Urban - CRADLES [Ultra S… / `LETRAS` MAZK00», «wutiwant / `LETRAS` `MV` saraunh0ly - wutiwant».

Lo que CORT tiene que copiar tal cual: **portada real**, dos líneas de texto, badges
`LETRAS` y `MV`, y que la fila entera sea pulsable para poner esa canción **con su cola**
(no la canción sola).

## 2 · La pestaña Vídeos — `182014` y `182021`

Rejilla de **dos columnas**: miniatura grande, debajo el nombre del fichero
(`3fcaa15be8c2318…`) y debajo «576P | 0:22» — resolución y duración. Arriba, «1786 Vídeos».

> **Medido en el código de CORT:** hoy la pestaña Vídeos sale **vacía** porque
> `Musica.buscar()` rellena audio hasta `MAX = 400` (`apps/apk/src/com/cort/ia/Musica.java:41`)
> y el mismo tope se lo aplica a los vídeos (`:137`). Con su biblioteca, los vídeos
> nunca llegan. No es un permiso: es un contador mal puesto.

## 3 · El buscador — `182025`

Pantalla completa: atrás circular + **campo pastilla** «Buscar mi música y vídeos» con
la lupa **dentro** del campo a la derecha. Debajo:

- **Historial** (con papelera a la derecha) en píldoras grises: `hot girl` `hard` `stereo`
  `douyin` `doutin` `illusionary` `once upon` `a time` `once upon a t…` `marshmello`.
- **Sitios** (con ⓘ a la derecha): YouTube · Instagram · Facebook · SoundCloud · X, cada uno
  con su icono redondo y su nombre debajo.

Es la pantalla que se abre **antes** de escribir, no un campo escondido tras un icono.

> **Medido:** CORT empuja el filtro al SQL (`TITLE LIKE ?`, `Musica.java:116-121`) y SQLite
> sólo ignora mayúsculas en ASCII: «marshmello» contra «Marshmello» acierta, pero
> «a time» contra «A Time» con acentos o eñes se cae, y el filtro fino de Java (`encaja`,
> `:160`) compara sin plegar acentos. Por eso «el buscador no funciona bien».

## 4 · Ordenar — `182029`

Hoja que sube con chaveta: título «Ordenar videos por» y cuatro filas:
**Más recientes** (en azul, con `↓↑` a la derecha marcando que está elegida y en qué sentido),
Más reproducido, A a Z, Duración más larga.

> **Medido:** CORT ordena la lista en el navegador sobre lo que ya trajo
> (`pintaMusicaLista`, `ui/js/pantallas.js:1519`) y Java siempre consulta con `TITLE ASC`
> (`Musica.java:126`). O sea: «Más recientes» y «Más reproducido» **no pueden existir** con
> ese orden fijo, porque lo más nuevo no entra en los 400 primeros alfabéticamente.

## 5 · El reproductor a pantalla completa — `182055` y `182100`

De arriba abajo:

1. La **portada grande** (casi cuadrada, ocupando el ancho), sobre un fondo que es su propio
   color muy oscurecido.
2. Título en **el color de la portada** (`#F0938B` salmón con Tom Welling), dos líneas.
3. Una fila a la derecha con: píldora **`MV`**, **corazón** relleno (ya le di a «me gusta»),
   y **⋮**.
4. Barra de progreso fina con punto; debajo `0:02` a la izquierda y `3:11` a la derecha.
5. Tres botones gordos del color del tinte: `◀◀` (anterior), `⏸` (pausa, el doble de grande),
   `▶▶` (siguiente).
6. Abajo: icono de **ecualizador con la etiqueta `ON`** (izquierda), píldora **`❝ Letras`**
   (centro), icono de **fila/repetir** (derecha).

> **Medido:** `Musica.Pista.json()` (`Musica.java:69-75`) devuelve
> `uri,titulo,artista,genero,dur,video` y **no hay en todo el repo una sola línea que lea
> una portada** (grep `portada|artwork|album_art` en `apps/apk/`: vacío). El propio código
> de la cara lo confiesa en `ui/js/pantallas.js:1084-1086` y pinta un glifo `♪`.
> «No se ven las carátulas» no es un fallo: es que **nadie las pide al sistema**.

## 6 · La hoja ⋮ — `182119`

Con el mini-reproductor arriba, siete filas con su icono:
**Agregar a la lista de reproducción** · **Compartir** · (separador) · **Velocidad** ·
**Temporizador para dormir** · **Modo de ahorro de energía** · (separador) ·
**Ocultar** · **Borrar**.

## 7 · Ecualizador — `182107`

Cabecera «Ecualizador» + **interruptor** encendido. Debadajo `🎧 TWS` (el dispositivo al que
suena: ecualizar por sesión, no por app). **Diez barras verticales** con su valor arriba
(`-12 …`) y su frecuencia abajo: `31 63 125 250 500 1K 2K 4K 8K 16K`. Y una rejilla de dos
columnas con las presets en tarjetas: **Personalizado** (elegida, rellena), Aumento de
graves, Aumento de voz, Aumento de agudos, y más debajo.

> **Decisión:** esto **sí se puede hacer de verdad** en Android con
> `android.media.audiofx.Equalizer` atado al `getAudioSessionId()` del `MediaPlayer`, sin
> librerías. No se pinta un ecualizador de adorno.

## 8 · Letras — `182111`

Estado vacío honesto: el icono de las comillas en marca de agua, el texto «Sin letras», y
dos botones redondos: `+` (contorno) para **añadir la letra a mano** y `🔍` (relleno) para
**buscarla**. Nada de pantallas en negro.

## 9 · Fila (la cola) — `182115`

Título «Fila», con un icono de escanear y una **escoba** (vaciar la cola). Filas con
portada, título (la que suena, en el color del tinte y con barritas de equalizador sobre la
portada), **debajo la app de origen** («SnapTube Video», «K PLUS», «THE IRANIAN» con su
`LETRAS`, «M4», «OPM») y una **asidera `≡`** a la derecha para arrastrar. Abajo tres
píldoras: repetir una, **repetir todo (elegida, rellena)**, aleatorio.

## 10 · Ajustes — `182033`

Tres grupos en tarjetas redondeadas: [Tiempo de reproducción · `209h 6m`] [Respaldar y
guardar · Google Drive] / [Tema · `Clásico / Medio`] [Idioma · `Español`] [Temporizador para
dormir · `Apagar`] [Quitar anuncios · `Apagar 50%`] / [Archivos ocultos · `40 archivos`]
[Eliminado recientemente · `1 archivo`]. Cada fila con su icono y su `›`.

> **Decisión:** CORT copia la **forma** (grupos, valor a la derecha, `›`) y llena sólo lo
> que tiene detrás: tema, idioma, temporizador, tiempo escuchado, archivos ocultos.
> «Quitar anuncios» y «Respaldar en Drive» **no se copian**: CORT no tiene anuncios y no
> sube nada a una cuenta que la dueña no ha conectado. Poner una fila que no hace nada es
> exactamente el relleno que ella prohibió.

---

## 11 · Lo que ella decidió y cambia el plano

- **MV deja de ser una hoja aparte** y se fusiona en el reproductor de Música, como el
  botón `MV` de Lark: si la pista tiene vídeo, la portada grande **es** el vídeo.
- **El orbe de CORT no aparece en el reproductor ni en MV.** Hoy está puesto a la fuerza
  con `html.pantallas-montadas.p-mv #scene{display:block!important;z-index:68}`
  (`ui/css/hud.css:691-692`). Se quita.
- El reproductor de CORT se llama **Música** y es la app entera: lista, mini, pantalla
  completa, fila, ecualizador y letras, sin salir de ahí.

## 12 · Los cuatro fallos que hay que cerrar antes de copiar nada

Por orden de lo que estorba, todos con su línea:

1. **El modo juego se queda clavado y silencia dos cosas a la vez.** `CortNative.java:308-312`
   se niega a abrir el micro con un `stt-error: abort`, y `ui/js/voice.js:113` sólo maneja
   `abort` en modo `wake`: en modo `cmd` **no dispara `onError`**, así que el botón del
   micrófono no hace ni dice nada. Y `Reproductor.pideFoco()` devuelve `false` con el modo
   puesto (`Reproductor.java:287`), por lo que `onPrepared` nunca llama a `m.start()`
   (`:342-347`): **la música se carga en silencio**. El modo se guarda en `SharedPreferences`
   (`CortNative.java:1228`) y se recarga al arrancar (`:246`), y la salida por voz
   («vuelve CORT», `ui/js/hud.js:1657`) necesita el micro que el propio modo cerró.
   **Callejón sin salida.** El único interruptor está dentro de la hoja Música
   (`pantallas.js:1115`).
2. **Pulsar un vídeo no hace nada** porque `musicaPoner` reconstruye la cola con
   `Musica.porUri()` (`:322-329`), que vuelve a escanear el índice con el tope de 400
   canciones: la URI del vídeo no está en esa lista y `pistas.isEmpty()` devuelve `false`
   (`CortNative.java:1077`).
3. **La letra del MV nunca llega sin PC**: `ui/js/pantallas.js:1817` pide `/api/letras`, y
   `MainActivity.shouldInterceptRequest` corta cualquier `/api/*` con 501 cuando no hay
   núcleo (`MainActivity.java:320, 401-408`).
4. **El botón «CORT · PC» es nativo y nunca se oculta** (`MainActivity.java:171-186`, un
   `FrameLayout` en `BOTTOM|START` por encima del `WebView`): no hay un solo
   `setVisibility` para él en el repo, así que pisa la píldora de música, que se pintó en la
   misma esquina (`ui/css/hud.css:732`).
