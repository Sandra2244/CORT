# La voz de CORT — qué boca usa en cada equipo y cómo se cambian timbre, tono y velocidad

Ronda **F7m**. Es lo que ella pidió con «variables de voz etc… muchas cosas»: que los
tres mandos de **07 · Perfil** (timbre, tono, velocidad) no fueran un adorno y que
CORT **se oiga** en el portátil.

Primero el dato que lo explica todo, medido el 2026-10-22 en el Chromium de esta casa
(`scripts/sonda-voz.html`, abierta en el navegador de la aplicación):

| lo que mide la sonda | qué devolvió |
|---|---|
| `window.speechSynthesis` | existe (`motor: "si"`) |
| `window.SpeechRecognition` | existe (`recognition: true`) |
| `speechSynthesis.getVoices()` | **0 voces** |
| `voiceschanged` | se dispara, y la lista sigue en **0** |
| re-mirada a los 400 / 1200 / 3000 ms | **0 / 0 / 0** |

En Linux el Web Speech no tiene con qué hablar: el motor de voz del navegador depende
del sistema (SAPI en Windows, AVFoundation en macOS) y aquí no hay ninguno detrás. Por
eso CORT «escuchaba» y contestaba en la pantalla pero **no sonaba**, y los deslizadores
no movían nada. El teléfono no estaba afectado (habla por `TextToSpeech` de Android) y
Windows/macOS tampoco.

---

## 1 · Las cuatro bocas, por orden de preferencia

La cara (`ui/js/voice.js`) elige una al hablar y **dice cuál** está usando:

| boca | qué es | cuándo toca |
|---|---|---|
| **`nativa`** | el puente del APK: `CortNative.speak(texto, id, voz, tono, velocidad)` | en el teléfono, siempre |
| **`navegador`** | Web Speech | Windows, macOS, y cualquier equipo donde `getVoices()` dé voces |
| **`núcleo`** | `POST /api/voice/say` → un WAV → `<audio>` | **el portátil de Linux**: el motor local `espeak-ng` |
| **`muda`** | no hay nada con qué hablar | se **anuncia** (`sin-boca` en la terminal y en el aviso), nunca se calla en silencio |

La terminal tiene que mostrar una línea como esta al arrancar con el backend levantado:

```
16:29:50 VOZ boca de voz: núcleo (espeak-ng, 10 timbres)
```

## 2 · Elegir timbre, tono y velocidad en el portátil

1. Abre CORT (doble clic, o `scripts/run.sh`) con el backend en marcha.
2. Ve a **07 · Perfil** → bloque **Voz**.
3. **Timbre**: el desplegable ya no viene de una lista copiada; el equipo **sondea** sus
   propias voces sintetizando cada candidata y se queda con las que de verdad suenan y
   suenan distinto. Aquí salen **11 opciones**: `(automática)` + 10 timbres, con `[M]` /
   `[F]` y el nombre en español (ej. `Español (Latinoamérica) · voz de mujer grave`).
   Lo que el motor no puede pronunciar **no se ofrece** (mbrola aparece en la lista del
   motor pero falla; una variante ignorada también se descarta).
4. **Tono** (0,5 grave → 1,5 agudo) y **Velocidad** (0,6 lenta → 1,6 rápida): se aplican
   **al moverlos**, sin Guardar.
5. Pulsa **Probar voz**. Se oye la frase por los altavoces y en el log del backend queda
   el `POST /api/voice/say` con las cabeceras `x-cort-voz`, `x-cort-pitch`, `x-cort-wpm`
   (medido hoy: `200`, **74.254 B** de `audio/wav`, `es+f4`, pitch **41**, **193** ppm).

Qué hace cada mando dentro, para que sepas qué esperarte:

| mando | rango en la cara | qué se le manda al motor |
|---|---|---|
| tono | 0,5 … 1,5 | `-p` de 26 a 74 (1,0 natural = 50; tope del motor 99) |
| velocidad | 0,6 … 1,6 | `-s` palabras por minuto, 1,0 = **175**, topes 80…450 |
| timbre | la lista sondeada | `-v es`, `-v es+f2`, `-v es-419+f4`… |

## 3 · Si no suena, compruébalo tú en dos minutos

Abre `scripts/sonda-voz.html` (doble clic, o en el navegador: no necesita backend ni
internet). Dice el motor, cuántas voces hay y en qué momento, y tiene deslizadores con
«Probar voz» para oír el Web Speech directamente.

* Si la sonda dice **0 voces** y CORT dice `boca de voz: núcleo` → está funcionando
  como toca, con el motor local.
* Si además el núcleo falla, mira `GET /api/voice` (ej. `curl localhost:8000/api/voice`):
  responde `motor`, `binario` y los timbres, o un `motivo` con nombre. Los motivos son
  `sin-motor` (no está `espeak-ng` / `espeak`), `vacio`, `no-suena` (el motor contestó
  algo), `no-responde` (tarda más de 30 s) y `binario-fallando`.
* `no-suena` en un equipo nuevo casi siempre es que falta el paquete: en Debian/Ubuntu,
  `sudo apt install espeak-ng`. No se descarga ni se compila nada dentro de CORT.

## 4 · Qué está probado desde el repo

* `scripts/prueba-voz.py` — **56 comprobaciones** sin sonido y sin red: los mandos y sus
  topes, el análisis de la salida real de `--voices`, el **argv exacto** que se le manda
  al motor (voz desconocida ⇒ sale **sin** `-v`; nada de `;`, `|` ni `&`), los motivos de
  error con nombre, y que no queden ficheros `cort-voz-*` sueltos en `/tmp`. Paso
  «Probar la boca del escritorio» del pipeline.
* `scripts/prueba-costura.py` — sector **[16] F7m**: que la suite esté de verdad llamada
  en el workflow, que las dos rutas y las cuatro bocas existan, y que la llamada del
  teléfono siga siendo la misma de **5 argumentos** (el contrato del puente no se mueve).

## 5 · Lo que falta, dicho en vez de fingido

* `espeak-ng` es **inteligible, no bonito**. Suena a robot claro. La voz natural de
  calidad (`piper`) es un modelo de varios megabytes por idioma; en un portátil de
  2 núcleos y 1,8 GiB no se mete sin decidirlo con la dueña. Es la vía si quieres que
  suene como una persona.
* Decirle **«más grave»**, «más rápido», «pon voz de mujer»** por voz o por chat
  todavía no funciona: esta ronda es que el deslizador funcione y se oiga. Es el
  siguiente paso natural (los números ya existen, sólo falta la frase que los mueva).
* En el **teléfono** los timbres son los de `TextToSpeech` del sistema — si tu capa de
  fabricante no trae más voces, CORT no puede inventarlas.
* Windows y macOS **no usan el núcleo**: siguen con su voz de navegador de siempre, que
  ahí sí tiene voces.
