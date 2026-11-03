# CORT — análisis del núcleo inteligente (F9 a F13)

Escrito el 2026-11-03 con la máquina encendida y medida, no con teoría. Cada número de
aquí se tomó en la Classmate o en el A16 en las condiciones que se dicen.

---

## 1. Lo que mide esta máquina ahora mismo

| cosa | medido | qué significa |
|---|---|---|
| RAM total | **1851 MB** | techo duro, sin swap útil (swappen es congelar) |
| Qoder (agente) | **1,09 GB en 17 procesos** | mientras yo trabajo, el cerebro no cabe |
| puente CORT | **11 MB** | el puente no es el problema |
| libre con todo abierto | **150-178 MB** | ni el modelo más chico |
| libre con Qoder cerrado | **~1,25 GB** | aquí es donde CORT puede pensar |
| disco libre | **213 GB** | caben los 6 modelos de Ollama y cinco más |
| `adb` | **no instalado** | el PC no puede ver el teléfono por USB hoy |
| `~/Música/Dark Rose` | **1 pista (`2 on - tinashe … slowed reverb.mp3`)** | la playlist existe en el PC |
| `Stereo Love Slowed` en el PC | **no está** | esa pista vive en Lark Player del teléfono |
| reproductores en el PC | VLC y Strawberry (`/usr/share/applications`) | se puede mandar música aquí sin inventar nada |
| `~/Documentos` | existe | `~/Documentos/proyectos` **no existe** (buscado en 4 rutas) |

### Lo que pide cada modelo que ya está en tu disco

| modelo | en disco | RAM que pide | ¿cabe con Qoder cerrado? |
|---|---|---|---|
| smollm2:135m | 258 MB | ~511 MB | sí, sobrado |
| gemma3:270m | 278 MB | ~539 MB | sí |
| qwen2.5:0.5b | 379 MB | ~680 MB | **sí — el candidato** |
| qwen3:0.6b | 498 MB | ~847 MB | sí, justo (quedan ~400 MB de aire) |
| airaos-local | 718 MB | ~1155 MB | al límite: riesgo de congelar |
| qwen3.5:2b | 2614 MB | ~3809 MB | **no entra nunca en 1,8 GB** |

---

## 2. La verdad del cerebro, dicha sin adornos

Un modelo de 0,5 B parámetros **no** comprende ni tiene consciencia: predice la siguiente
palabra. Lo que la gente percibe como "inteligente" en un asistente no es el tamaño del
modelo, es que **cada frase rara se traduzca a una orden concreta, se ejecute contra datos
reales y se verifique después**. Siri y Gemini hacen exactamente eso: el modelo propone y
un ejecutor determinístico hace.

De ahí la regla de arquitectura de CORT:

> **El modelo nunca toca el disco, la red ni el teléfono. Sólo propone un plan en JSON.
> El ejecutor valida el plan contra el estado real; si no valida, CORT pregunta o dice
> que no, y nunca finge que lo hizo.**

Esa es la respuesta directa a "que no delire": la alucinación se corta por el medio, con
validación, no con un modelo más grande. Un modelo de 7 B (los que planifican de verdad
en varios pasos) pide 4-5 GB: en esta máquina no existe, ni con Qoder cerrado.

Lo que **sí** se consigue con 0,5-0,6 B bien usado:

* entender frases largas y con errores de dictado («muevme varios archivo»);
* elegir entre ~30 verbos propios sin diccionario de frases fijas;
* rellenar huecos (`destino`, `pista`, `playlist`, `ciudad`) con lo que hay en el equipo;
* decidir si hace falta confirmar (borrar, apagar, mover fuera de casa).

Lo que **no** se consigue aquí y no se promete: razonar en varios pasos sobre algo que no
está en el disco, investigar temas complejos con fuentes, o aprender cosas nuevas por
conversación (entrenar/ajustar un modelo pide GPU y no se hace en esta máquina).

---

## 3. Arquitectura del núcleo (cinco capas)

```
micrófono / bandeja de texto
        │
   [1] OÍDO     wake word + STT (Vosk es-42 en PC; en el A16 puede ser siempre-encendido)
        │  texto
   [2] COMPILADOR  modelo local con salida JSON obligatoria (format/schema de Ollama)
        │  {"intencion":"mover","origen":"~/Documentos/proyectos","destino":"~/Documentos"}
   [3] VALIDADOR   comprueba rutas, permisos, lista blanca de raíces, verbos peligrosos
        │  plan aceptado / pregunta / rechazo con motivo
   [4] EJECUTOR    cort_acciones (PC) o la API del APK (teléfono), sin shell
        │  resultado con números
   [5] VERIFICADOR  re-lee el estado (¿existe en el destino? ¿está sonando?) y responde
        │
   voz + subtítulo + registro auditable (registro-acciones.jsonl ya existe)
```

Piezas nuevas que hay que escribir (F9/F10):

* `cort_intenciones.py` — el compilador: esquema JSON, 12 ejemplos tuyos como `few-shot`,
  temperatura 0, y una tabla de intenciones con sus argumentos obligatorios.
* `cort_archivos.py` — verbos de archivo (buscar, mover, copiar, crear carpeta, listar)
  con raíz blanca (`~/Documentos`, `~/Descargas`, `~/Escritorio`, `~/Música`,
  `~/Imágenes`, `~/Videos`) y `mv` sólo dentro de esa lista.
* `cort_media.py` — playlists leídas del disco (carpetas y `.m3u`) y control de VLC por
  MPRIS; en el teléfono, la misma interfaz la contesta el APK.
* en `cort_server.py`: la rama `plan` (frase → JSON → ejecutar → verificar) y el botón de
  "¿qué entendí?" para que se pueda corregir en una frase.

---

## 4. Tus cuatro frases, resueltas una por una

**a) «Investígame en Google qué es la toxoplasmosis»**
Ruta: [2] `intencion=investigar, fuente=google, tema="toxoplasmosis"` → [3] el puente
busca en tu disco si hay algo guardado de eso (nota/`~/Documentos`) → [4] abre la URL de
búsqueda en el navegador real (`cort_acciones.abrir_url`) y, si hay red, lee el primer
fragmento con `open-meteo`-style fetch propio → [5] responde con la fuente y la hora de la
lectura. **Sin red te lo dice, no lo inventa.** Hoy el puente ya sabe abrir el navegador
(F5 medido). Falta la capa `investigar` (F9).

**b) «Mueve la carpeta proyectos a Documentos»**
Ruta: [2] `mover` → [3] `~/Documentos/proyectos` **no existe** (acabo de buscarlo en 4
rutas): CORT responde «no encuentro esa carpeta; sí existe ~/Documentos. ¿La creo o te
refieres a otra?» en vez de mover lo que sea que casque por parecido. Cuando existe:
`mv` dentro de la raíz blanca, y [5] verifica con `ls` el destino y dice
«3 archivos movidos a ~/Documentos/proyectos (verificado)». **Nunca** `rm`, y fuera de las
raíces listas pide confirmación por escrito.

**c) «Pon en Lark Player la playlist Dark Rose y reproduce Stereo Love Slowed»**
Ésta es la difícil y tiene dos mitades distintas:
* En el **PC** se puede hoy: `~/Música/Dark Rose` existe; se lee la lista, se busca la
  pista por parecido de nombre y se manda a VLC por MPRIS. Si la pista no está (como
  `Stereo Love Slowed`, que no está en el PC) CORT dice «no está en ~/Música; está en el
  teléfono» — con el dato real, no con un silencio.
* En el **teléfono** hace falta el APK (F11/F12). Lark Player no tiene API pública; se le
  llega por dos vías reales: **(1) MediaStore** — leer `MediaStore.Playlists` y
  `MediaStore.Audio` (con `READ_MEDIA_AUDIO` en Android 13+) y abrir la pista con
  `Intent(ACTION_VIEW, content://media/external/audio/media/<id>)`, que Lark intercepta;
  **(2) MediaSession** — `MediaController`/`AudioPlaybackCapture` requiere permiso de
  notificaciones y sólo controla lo que ya suena (pausa, siguiente), no puede pedir
  "busca tal pista". La vía (1) es la que da el "reproduce Stereo Love Slowed".
  **adb no está instalado** y el teléfono no se ve por USB: sin APK no hay forma de que
  el PC toque la música del teléfono.

**d) «Que arranque con el teléfono, te salude y se quede en segundo plano»**
Es un trabajo de app nativa, no de web: `RECEIVE_BOOT_COMPLETED` + `ACTION_USER_PRESENT`
para el «hola, buenos días Sandra» (con tu nombre, que ya está en el estado del puente),
un **servicio en primer plano** con tipo `microphone` para no que cuando la pantalla se
apaga, y en One UI 7 hace falta pedir `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` o el sistema
lo mata (medido en cualquier app de dictado). El botón de auricular mantenido y el botón
Función de la pantalla bloqueada se atienden con `MediaButton` + `KEYCODE_ASSIST` y con
ser la **aplicación de asistente digital** elegida: para eso el APK declara un
`VoiceInteractionService` con `BIND_VOICE_INTERACTION`; sólo así CORT aparece en la
pantalla que tú fotografiaste (hoy esa lista sólo tiene Google, porque ninguna otra app
declara ese servicio). La pantalla transparente con la estética de CORT es una ventana de
superposición (`SYSTEM_ALERT_WINDOW`, permiso "mostrar sobre otras apps") dibujada por el
propio `VoiceInteractionSession`. **Una PWA no puede hacer nada de esto**: el navegador no
tiene permisos de asistente, no arranca con el teléfono y no se superpone a otras apps.

---

## 5. Presupuesto de latencia (tu objetivo: 4-5 s)

Tramos medidos o estimados, marcados como tales:

| tramo | PC (Classmate) | A16 | estado |
|---|---|---|---|
| wake word + fin de frase | 0,4-1,2 s | 0,3-0,8 s | **por medir** (F10) |
| STT Vosk es-42 | **1,8× el audio** (medido: 3,9 s de audio = 7,0 s) | ~0,5× esperado | medido en PC |
| compilador qwen 0,5-0,6 B | ~1,5-3 s (2 núcleos) | no aplica (va al PC por Wi-Fi) | **por medir** (F9) |
| validación + ejecución | 0,1-0,5 s | 0,2-1 s (MediaStore) | medido en F5 |
| verificación | 0,1-0,3 s | 0,1-0,3 s | medido en F4 |
| síntesis de voz | **0,14 ms/ms** (espeak-ng, medido) | 0,1× (media/nativo) | medido |

Conclusión honesta: **en el PC no se cumplen los 4-5 s** con una frase de 6-8 s de audio
(sólo el oído tarda ~10 s). **En el A16 sí es alcanzable** (8 núcleos para el oído y el
cerebro de 0,5 B en el PC por Wi-Fi, o el modelo pequeño dentro del teléfono). Ésa es la
razón por la que el teléfono es el frente donde CORT tiene que oír, y el PC donde actúa.

---

## 6. Fases propuestas

| fase | qué entrega | se corta si… |
|---|---|---|
| **F9 — compilador de intenciones** | `cort_intenciones.py` + `cort_archivos.py` + `cort_media.py`; tus frases largas → JSON → ejecutar → verificar. Prueba: 12 frases tuyas, con el modelo cargado y Qoder cerrado | — (es el corazón que pides) |
| **F10 — oído en el PC** | wake word «oye CORT» con gramática de Vosk + botón para hablar; medida real de factor de tiempo | se aplaza si el factor >1,5× (se dice con número) |
| **F11 — APK asistente (F7 pendiente)** | `VoiceInteractionService` + overlay transparente + saludo al encender + dictado en segundo plano; instalada y elegida como asistente en tu A16 | — |
| **F12 — manos del teléfono** | MediaStore: listar playlists y pistas, reproducir por nombre, pausar/siguiente; API local al puente por Wi-Fi con token | se recorta a "abrir la playlist" si MediaStore no expone las listas de Lark |
| **F13 — investigación con fuentes** | `investigar` = búsqueda real + lectura del fragmento + cita con URL y hora; sin red lo dice | entra al final |

**No entra** (y por qué): entrenar o afinar un modelo propio (sin GPU y sin tarjeta para
alquilar una); un cerebro que razone en 6 pasos (pide 4-5 GB de RAM); controlar el teléfono
por adb (el PC no lo ve y no se instala software de terceros de un acortador).

---

## 7. Cómo se mide el cerebro sin congelar la máquina

`scripts/sonda_cerebro.sh` (escrito en esta fase) hace la única prueba decisiva: mide la
RAM disponible, **se niega** a cargar si no hay 900 MB, arranca Ollama, y corre
`scripts/cerebro_prueba.py` con los dos candidatos (`qwen2.5:0.5b` y `qwen3:0.6b`, ambos
ya en disco): pasa tus 12 frases reales por el compilador, apunta cuántas JSON salieron
bien y cuántos tokens/s da, y libera el modelo al terminar. Se corre **con Qoder cerrado**,
porque con el agente abierto la RAM libre medida hoy es 170 MB y el resultado sería una
máquina congelada, no una medida.

Salida esperada en el archivo `~/.local/share/cort/registro-cerebro.jsonl`: por cada frase,
el JSON que propuso el modelo, si el validador lo aceptó y los milisegundos que tardó. Con
eso se decide el modelo (0,5 B vs 0,6 B) con datos, y no por gusto.

---

## 8. La reja ya está construida y medida (2026-11-03, 01:00)

El modelo todavía no se midió (hace falta Qoder cerrado), pero la parte que no depende
de él ya corre y ya tiene número: `cort_archivos.py`, `cort_media.py`,
`cort_intenciones.py` y su prueba `scripts/prueba_intenciones.py`.

| qué | medido |
|---|---|
| casos de la reja | **18 / 18 correctos**, salida 0 |
| planes buenos ejecutados | 6 (mover, listar, crear, reproducir, JSON en cercado, JSON plano en inglés) |
| planes malos frenados | 12 (borrar, `/etc`, `../../../../etc/passwd`, prosa en vez de JSON, verbo inexistente, argumento faltante, sobrescribir sin confirmar, vacío, dos rutas ambiguas) |
| raíces reales en esta laptop | `Documentos`, `Descargas`, `Escritorio`, `Imágenes`, `Música` — `Videos` **no existe** |
| pistas encontradas en `~/Música` | **16** (la carpeta `Dark Rose` está entre ellas) |
| reproductor | `vlc` presente; `playerctl` **ausente** → pausar/siguiente responden «no puedo» en vez de fingir |
| borra algo CORT? | no existe el verbo: `dir(cort_archivos)` no tiene `borrar`, `rm` ni `vaciar` |
| sobrescribir | con `confirmar=True` lo anterior se rescata como `informe-cort-010058.txt`; sin confirmar, se pide |

Lo que falta para cerrar F9 es el primer tramo (frase → JSON): el modelo, que mide la
sonda. La reja no cambia cuál sea el modelo que se elija.
