# Plataforma — la guía de @Xvirus contra esta máquina

Documento de decisión, no de intenciones. Nace de la **guía "Proyecto Jarvis — Guía de inicio" (@Xvirus, 2026-10-07)** que trajo Sandra, y de lo que se midió en el portátil de desarrollo el **2026-10-08** ejecutando comandos. Si la guía y la máquina discrepan, manda la máquina y esto queda escrito con el número delante.

## Qué dice la guía, y dónde está CORT en cada punto

| Pieza de la guía | Para qué la pide | Estado en CORT | Evidencia |
|---|---|---|---|
| **Python** | Backend: lógica, voz, conexión con la IA | ✅ Igual. `services/core/cort_core/` con FastAPI + WebSocket | `make test` → 571 pruebas (medido 2026-10-15) |
| **JavaScript / React** | Interfaz y comportamiento | ✅ Igual. `apps/web` en React 19 + Vite + TypeScript | `npm run build` → `✓ built`, servido en `:8780` |
| **Node.js** | Herramientas de JavaScript | ✅ Presente (`node`, `npm` en `/usr/bin`) | medido con `command -v` |
| **Ollama + Qwen** | Cerebro local, atado a `localhost` | ✅ Igual, con **guarda de RAM** que la guía no tiene: descarta los modelos que no caben antes de intentarlos | `test_brain` (10) + medición real |
| **Electron** | Convertir la web en app de escritorio instalable | ⚠️ **No está, y hoy no cabe.** Ver "Las dos piezas que la guía no puede cumplir aquí" | — |
| **Capacitor** | Llevar la misma interfaz a móvil como app nativa | ✅ **Resuelto por otra vía:** no hace falta Capacitor ni Gradle. Desde `v0.15.0` hay **APK nativo propio** (`apps/apk`, Java puro, quince acciones y SQLite dentro del teléfono) y se compila en el pipeline. La PWA sigue viva como alternativa | Run verde `38771718345`, `CORT-v0.15.0.apk` = 70 526 B |
| **SpeechRecognition** (escucharte) | STT local | ❌ **Inviable en este equipo, medido:** `arecord -l` lista *"List of CAPTURE Hardware Devices"* **vacía** y `wpctl status` no muestra ni un *Source* de audio. No hay micrófono que leer | — |
| **pyttsx3** (hablarte) | TTS local | ⚠️ El motor **sí está** (`/usr/bin/espeak-ng`), pero el único *Sink* es *Dummy Output*: no hay por dónde sacar sonido. El `returncode` de un mando no prueba que alguien lo oiga (ya se vio con `wpctl`) | — |

**Seguridad:** la guía dice *"dejar Ollama y el backend atados a `localhost`, sin exponer puertos a internet"*. CORT ya lo hace (`127.0.0.1` a propósito). **Pero la guía se contradice a sí misma en el paso 6**: una app móvil empaquetada con Capacitor no puede hablar con un backend atado a `localhost`, porque `localhost` del teléfono es el teléfono. O se abre el core a la LAN (con token, y aun así cualquiera de tu WiFi ve el puerto), o el móvil lleva su propio core. **Esa decisión es de Sandra, no de código**, y está sin tomar.

## Las dos piezas que la guía no puede cumplir aquí

**Electron.** No es "otro instalador": Electron **es un Chromium extra**. Este portátil tiene 1,8 GiB de RAM y **263 MB disponibles** con el escritorio ya encendido (medido con `free -m`). El core + la interfaz ya se sirven en el navegador que existe; meter una ventana Electron encima es pagar 200–350 MB por el mismo HTML. **Y hay que decirlo con la regla 10 por delante: no se ha probado, porque instalarlo y levantarlo es justo la carga que ya congeló esta máquina.** Si algún día se prueba, se prueba con el navegador cerrado y midiendo `free -m` antes de abrir la ventana, y el resultado —quepa o no— se escribe aquí.

Lo que sí existe hoy y cubre el 90 % de lo que la guía pide de Electron: **el lanzador de doble clic** (`CORT.desktop`, `cort.bat`) que arranca core + interfaz y abre la ventana del navegador a pantalla completa. Se pierde la ventana "sin barra del navegador", se gana que CORT quepa en la máquina.

**Capacitor.** Empaquetar para Android pide **JDK** (aquí sólo hay *runtime*: `java` sí, `javac` **no**, medido), **Android SDK** (varios GB) y un build de **Gradle** que se come más de 1 GiB de RAM en su pico. En dos núcleos a 1,46 GHz eso no es "tardar más": es congelar el PC. **El APK, si se hace, se hace en otra máquina** (o en un runner de CI) y aquí sólo se escribe y se revisa el código — así fue: desde `v0.15.0` el APK se compila en un runner de GitHub Actions con `aapt2` + `javac --release 11` + `d8` + `apksigner`, sin Gradle ni AndroidX, y el resultado se vuelve a medir aquí descargando el binario publicado—. Mientras tanto, la PWA instalable **sigue** siendo la vía en el Samsung A16 para quien quiera el React de siempre: mismo `manifest`, sin Gradle.

## Y sobre C++ / Java

La guía **no los menciona**: su tabla de tecnologías es Python, JavaScript, React, Node.js, Electron y Capacitor. Aun así, medido por si vuelve la idea:

- **Java:** hay OpenJDK 21 *runtime*, no hay compilador (`javac` ausente). Escribir CORT en Java exigiría instalar un JDK y, sobre todo, tirar 571 pruebas y el core entero que hoy funciona. **Y esta línea se corrigió a medias en `v0.15.0`**: Java nativo *no* reemplaza el core — está en el teléfono, donde el core Python no corre—, así que la frase exacta hoy es «Java en el PC: descartado; Java en el teléfono: hecho y publicado».
- **C++:** `g++` y `gcc` sí están. Pero C++ no aporta multiplataforma aquí —la interfaz ya es multiplataforma *porque* es web— y sí costaría reescribir el backend que ya ejecuta acciones reales y verifica sus resultados.
- **Lo multiplataforma ya está resuelto por arquitectura, no por lenguaje:** un core Python que habla por WebSocket + una interfaz React que corre en cualquier navegador (PC, teléfono, tablet). Cambiar de lenguaje no añade ni un dispositivo donde funcione; añade una segunda implementación que mantener.

Donde **sí** tiene sentido un lenguaje compilado, y está en el roadmap, es en el borde: **firmware ESP32** (C++/MicroPython, Fase 7) para sensores reales. Ahí no hay navegador, y ahí iremos.

## La decisión de `v0.15.0`: Java **en el teléfono**, no en el portátil

Regla 13: la pila no cambia por una sugerencia externa, y para alterar una
decisión de plataforma hay que traer **un número**, no una opinión. El número lo
puso la dueña del proyecto, que es a quién sirve esta pila:

> «no necesito nada más abrirlo en mi PC y luego el cel… que funcione de forma
> local en mi cel, ya que no tengo servidor y mi PC no tiene los recursos para
> usarlo»

El número es **cero**. Cero servidores, cero portátil encendido, cero RAM de la
casa gastada: el Samsung A16 tiene que poder con CORT **solo**. Y el otro número
que pesa es el de siempre — 1,8 GiB y 263 MB disponibles —, que es exactamente
por lo que la respuesta no puede ser «entonces mueve el core al portátil de
otro».

Lo que se decidió, dicho sin eufemismos sobre su alcance:

- **El core de escritorio sigue siendo Python + React + Ollama, y la cara del teléfono se copia de él, no se re-inventa.** Desde `v0.16.0` los literales del orbe (`Scene.tsx`, `Core.tsx`, `Particles.tsx`, `palette.ts`) y de la voz (`cort/voz.ts`) están **leídos por una prueba** (`test_apk_orbe.py`, 27): un cambio estético o de acento en un aparato que no viaje al otro rompe `make test`. Es la forma ejecutable de «lo mismo funcione en PC que en el APK».
   No se reescribe
  nada: las **722** pruebas de `services/core` (ejecutadas el 2026-10-15), el
  WebSocket, el cuerpo 3D y la memoria del portátil se quedan donde están. Un
  segundo CORT en Java en el PC sería pagar una segunda implementación sin ganar
  ni un dispositivo.
- **En el teléfono sí hay Java nativo** (`apps/apk/src`), y no es el core
  portado: es una **segunda cara** con su propio cerebro de quince acciones, su
  SQLite y su voz. Cuando el portátil aparece por la Wi-Fi se usa el core de
  siempre en el WebView; cuando no, el teléfono no se queda en un formulario.
- **El coste de esa duplicación está escrito y es real.** Son **tres deudas**, y se llevan
  aquí delante en orden:
  1. ~~No había forma de escribir la clave de nube desde el teléfono~~: **cerrada el
     2026-10-15 con `v0.15.1`** (`Cara.abrirAjustes()` — función 105; la clave se teclea una
     vez en el aparato, nunca vuelve a la pantalla y nunca entra al repo, regla 7).
  2. ~~`memory.db` (el portátil) y `cort.db` (el teléfono) **no se sincronizan**~~:
     **cerrada el 2026-10-15 con `v0.15.2`** (función 106). Son dos rutas HTTP
     (`GET`/`POST /memoria/puente`) detrás de la **misma** llave del WebSocket, un módulo
     puro espejado en los dos lenguajes (`puente.py` ↔ `Puente.java`) y una sola clase que
     abre el socket (`Sincroniza.java`). Sólo suma, nunca borra, la llave de red no viaja
     dentro de un recuerdo, y lo que llega con forma `nombre: Sandra` se guarda en la
     plantilla que el otro lado entiende. **Sin verificar en dedo**: el cruce lo ejecutó
     `make test` con dos bases y las dos rutas, no un Samsung.
  3. **Abierta**: conviven **dos cuerpos de reglas** — `herramientas.py` en Python
     (19 herramientas) y `habilidades.json` en Java (quince acciones)— que se parecen pero no
     son el mismo archivo, así que una mejora en un lado no viaja al otro.
  Mientras el teléfono esté solo, 3 es invisible; en cuanto se usen los dos, se nota.
- **La verificación se compra con datos, no con fe**: como aquí no hay `javac`,
  la tabla de frases es un JSON probado por `make test`, y las constantes de
  Android que puede nombrar el Java salen de un diccionario descargado de AOSP
  (`scripts/simbolos_android.py`): **1044 constantes en doce clases**, medido el 2026-10-15.
  Dos Runs costó aprenderlo. **Desde `v0.15.5` el mismo guion escribe un segundo
  diccionario**, `apps/apk/lanza-android.json`, con las **firmas `throws`** de los métodos que
  el Java llama sobre objetos del sistema —**10 firmas**, las diez de `RecognitionService.Callback`
  lanzando `RemoteException`—, porque `javac` no sólo mira que el símbolo exista: mira lo que
  declara. Ese segundo error costó otros dos Runs (`v0.15.3` y `v0.15.4`, las dos páginas sin APK). **Desde `v0.16.0` escribe un tercero**, `apps/apk/devuelve-android.json` —**7 retornos en dos clases**: `getVoices → Set<Voice>`, `isSpeaking → boolean`, `getStringArrayList → ArrayList<String>`…—, porque la tercera clase de error que sólo existe al compilar es **recibir un método del SDK en el tipo equivocado**: el Java nuevo escribía `List<Voice> disponibles = boca.getVoices()`. Esta vez lo cazó `TestLoQueElSdkDevuelve` aquí mismo, sin pagar un Run.
- **Ser el asistente del teléfono tiene un coste, y se dice antes de prometerlo.** Desde
  `v0.15.3` el APK lleva el traje que el sistema pide para aparecer en Ajustes → *Asistente
  por defecto* (`VoiceInteractionService` + su `SessionService` + `RecognitionService`, con
  `res/xml/asistente.xml`). Los cuatro contratos se leyeron del fuente de AOSP, no de un
  Samsung A16, y **no hay `javac` en esta máquina**: la primera verificación real es el runner.
  Lo que falta no es código sino un **modelo de reconocimiento propio**, y en este build no
  puede haberlo (sin Gradle, sin modelos pesados en el repo — regla 7—, y 1,8 GiB en el PC de
  desarrollo). Así que `Reconocimiento` cede la escucha al micrófono de la cara
  (`SpeechRecognizer` + `Cara.escucharAhora()`) y cierra la petición del sistema con
  `ERROR_NO_MATCH`. **Consecuencia: el «OK Google» no se transfiere a CORT.** Elegir a CORT
  como asistente es decisión de la dueña, no un ticket, y mientras no se decida el traje está
  montado pero sin usar.
## Qué se adopta de la guía, dicho en una lista

1. **La pila se confirma tal como está** (Python + React + Ollama, todo en local). No se reescribe nada.
2. **La voz** (pasos 3 y 4) queda **bloqueada por hardware, no por código**: sin micrófono y sin salida de audio no hay nada que verificar. Con un USB de audio o auriculares Bluetooth conectados, `espeak-ng` ya está instalado y el paso 4 es corto.
3. **Escritorio**: el lanzador de doble clic hace el trabajo que la guía pide de Electron, con la mitad de RAM. Electron queda anotado como intento medible, no como feature.
4. **Móvil**: PWA ahora (hecho y servido); Capacitor sólo cuando haya dónde compilar el APK y una decisión tomada sobre la LAN.
5. **La guía entra en `CREDITS.md`** como referencia de ideas: no se copió una línea de ella porque no trae código.
