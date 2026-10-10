# REFERENCIAS — lo que dicen los videos de `Referencias IA CORT`

Documento de trabajo. Nace de la pregunta de la dueña del proyecto: *«¿de verdad analizaste los videos?»*.
Está escrito después de verlos fotograma a fotograma, no de recordarlos de un chat anterior.

## Cómo se miraron

Los siete archivos miden entre 16 s y 5 min. Nadie los ve enteros en una sesión de trabajo, así que se
muestrearon: **6 fotogramas por video** repartidos a lo largo de su duración, y esos fotogramas se
unieron en hojas de 3×2 para poder comparar dos videos a la vez.

- **No hay `ffmpeg` en esta máquina** (comprobado: `command -v ffmpeg` vacío; `cvlc --video-filter=scene`
  decodifica pero no escribe el cuadro). Se usó un `ffmpeg` estático 7.0.2 instalado en un entorno
  virtual **desechable fuera del repositorio** (`~/.cache/ffenv`), sólo como herramienta de oficina.
  **No es dependencia de CORT**: el proyecto sigue sin necesitarlo, y `make doctor` no lo pide.
- La foto de referencia (`Cortana` / `What if…`, `@hal9_mc`) es un render, no una interfaz: se mira por
  el **cuerpo** (transparencia, líneas de barrido, halo) y por las **expresiones**, no por sus paneles.

| archivo | duración | qué es |
|---|---|---|
| `035346b7…mp4` | 16,7 s | `@sued.tiago` — capa de cristal con un **anillo de luz que sigue la mano** y agarra, mueve y escala una imagen |
| `fb05698a…mp4` | 132,8 s | `@techenclear` — HUD a pantalla completa: armilar central, columnas de telemetría en ambos bordes, `pinch`, explorador de archivos, panel flotante de tareas señalado con el dedo |
| `90e21d….mp4` | 211,2 s | reactor central con **rieles verticales de iconos en los dos bordes**; al gesticular, el HUD **se apaga casi todo** y deja **un panel de texto centrado** |
| `07bf92….mp4` | 311 s | «Jarvis»: HUD reducido a **líneas finas apiladas en el borde derecho**; una de ellas **se expande** y se convierte en una fila de escritura |
| `fd38b8….mp4` | 45,3 s | `@iacontuki` — *«SYSTEMS IS TERMINAL»*: la interfaz entera es una **consola monoespaciada**, sin marcos ni botones |
| `f7d16b….mp4`, `My AI agent….mp4` | 192 s / 198 s | instalación y configuración (logs de `pip`, `.env`, asistentes de puesta a punto). **No son referencia de interfaz**: aportan el guion de arranque, que ya está cubierto en `README.md` |

## Los seis patrones que se repiten

1. **El reactor es la pantalla.** En los cuatro videos de interfaz no hay ni una barra de título, ni un
   fondo de escritorio asomando: lo que ocupa el cuadro es el núcleo luminoso. Todo lo demás vive en los
   **bordes**.
2. **Los paneles son hilos, no cajas.** Jarvis tiene el HUD entero reducido a cuatro o cinco líneas
   finas de un solo renglón apiladas en el borde derecho. El de `90e21d` son dos rieles de iconos sin
   texto. Ninguno muestra a la vez lo que muestra CORT hoy.
3. **Uno se abre; los demás se apartan.** Al tocar un hilo, ese se ensancha hasta volverse una fila de
   escritura o un panel, y **los demás se atenúan**. Nunca hay dos paneles expandidos peleándose.
4. **Cuando el gesto manda, la interfaz desaparece.** En `90e21d`, mientras la mano trabaja, el HUD se
   apaga y queda **un solo panel de texto centrado**; en `035346b` no hay más que un anillo de luz
   siguiendo los dedos. La interfaz se aparta del camino de la mano.
5. **La entrada es una línea, y se ve poco.** O un campo de una sola fila dentro del hilo expandido
   (Jarvis) o una consola monoespaciada sin ningún adorno (`fd38b8`). En ninguno de los siete videos hay
   un formulario con etiqueta, botón de «Enviar» y caja de texto grande.
6. **Se llega con tres manos distintas.** Dedo (señalar y tocar el panel flotante), cursor (recorrer los
   rieles y que se abran solos al pasar por encima) y **teclado** (la consola: se escribe, y se ve el
   comando antes de ejecutarlo). Los tres son de primera clase; ninguno es el "plan B" de otro.

## Dónde está CORT frente a eso

Lo que ya coincide: la pantalla es el reactor (`Scene` a sangre, `scan` de líneas de barrido encima), el
cuerpo holográfico con transparencia y halo, la telemetría en el borde, el gesto de desenfoque con la
cámara, arrastrar paneles con el dedo o el ratón, y la bandeja que se guarda.

Lo que **no** coincide, y es exactamente lo que pidió Sandra:

| patrón | CORT antes de este corte |
|---|---|
| hilos finos en el borde | un solo tirador en la esquina inferior derecha que abre **todo a la vez** |
| uno se abre, los demás se apartan | `abierto` es un booleano: mensajes, voz, atuendos, cámara y telemetría se muestran juntos y apelmazados |
| la interfaz se aparta del gesto | nada se atenúa solo; el HUD está igual de presente con la cámara abierta que sin ella |
| entrada de una línea | la caja existe pero va acompañada de un botón `Enviar` grande y de tres bloques de control encima |
| teclado | **una sola tecla**: `Esc`. Ni atajo para el campo, ni tecla para ocultar la cara, ni índice por panel |

## Qué se adopta en este corte

Tres cosas, en este orden, y todas **sin dependencias nuevas** (seguimos en 1,8 GiB de RAM; cada
librería de animación es memoria que el orbe deja de tener):

1. **Riel de bordes en vez de tirador único.** Una columna de marcas de luz en el borde, una por panel
   (`mensajes`, `telemetría`, `voz`, `atuendos`, `cámara`, `teclas`). En reposo son un trazo y una
   etiqueta fina en vertical. Al tocar, al pasar el cursor o al enfocar con el teclado, **una se expande
   y las demás se guardan**.
2. **La interfaz se aparta.** Si nadie toca nada un rato y no hay ningún panel abierto, el cromo baja de
   opacidad y deja el reactor solo — el patrón 4. Cualquier movimiento de puntero, tecla o toque lo hace
   volver. Con `prefers-reduced-motion` no se atenúa por temporizador: ahí el apagado sólo es decisión
   de la usuaria.
3. **Teclado de primera clase.** `Esc` guarda todo, `H` apaga y enciende la cara, `/` salta al campo de
   mensaje, `?` despliega la lista de teclas, y `1`–`6` abren cada panel por su número. Mientras se
   escribe, ninguna de esas teclas secuestra el texto: ésa es la única regla que hace que un atajo no
   sea una trampa.

## Qué se deja fuera, y por qué se dice

- **El anillo que sigue la mano y agarra objetos** (`035346b`) necesita seguimiento de mano. Hay un
  intento medido y descartado en `docs/STATUS.md` (`src/lib/hands.ts`): sin GPU, el coste en esta máquina
  no sale. Se puede volver a intentar con las **celdas de hash de MediaPipe**, no con un modelo grande.
- **El explorador de archivos en 3D con iconos-esfera** (`fb05698`) es otra capa de aplicación, no de
  interfaz: exigiría un modo de navegación que CORT todavía no tiene.
- **La consola monoespaciada como cara única** (`fd38b8`) choca con que CORT se usa desde un teléfono de
  4 GB: el teclado en pantalla de un Android sobre una consola de texto es una mala experiencia. La línea
  de comando de CORT es el lenguaje natural, y ése es el motivo por el que el campo de mensaje se queda.
- **Ningún asset, ningún fotograma, ningún código de estos videos entra en el repositorio.** Son
  grabaciones de TikTok y de películas sin licencia declarada; lo que se copia es **distribución** —dónde
  vive un panel y qué hace el resto cuando se abre—, que no es obra protegida. La atribución de la
  inspiración va en `CREDITS.md`, y lo que sí tiene licencia (el patrón de arrastre de JARVIS, MIT) ya
  está documentado con su origen en `apps/web/CREDITS.md`.

## Cómo volver a mirar esto

El muestreo es desechable y está fuera del repo. Para repetirlo: `ffmpeg -i <video> -vf "fps=6/duración,scale=…"`
seis cuadros por video y `tile=3x2` para unirlos. No hace falta para trabajar en la interfaz; hace
falta para **no volver a afirmar sin haber visto**.
