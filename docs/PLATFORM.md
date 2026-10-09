# Plataforma — la guía de @Xvirus contra esta máquina

Documento de decisión, no de intenciones. Nace de la **guía "Proyecto Jarvis — Guía de inicio" (@Xvirus, 2026-10-07)** que trajo Sandra, y de lo que se midió en el portátil de desarrollo el **2026-10-08** ejecutando comandos. Si la guía y la máquina discrepan, manda la máquina y esto queda escrito con el número delante.

## Qué dice la guía, y dónde está CORT en cada punto

| Pieza de la guía | Para qué la pide | Estado en CORT | Evidencia |
|---|---|---|---|
| **Python** | Backend: lógica, voz, conexión con la IA | ✅ Igual. `services/core/cort_core/` con FastAPI + WebSocket | `make test` → 124 pruebas |
| **JavaScript / React** | Interfaz y comportamiento | ✅ Igual. `apps/web` en React 19 + Vite + TypeScript | `npm run build` → `✓ built`, servido en `:8780` |
| **Node.js** | Herramientas de JavaScript | ✅ Presente (`node`, `npm` en `/usr/bin`) | medido con `command -v` |
| **Ollama + Qwen** | Cerebro local, atado a `localhost` | ✅ Igual, con **guarda de RAM** que la guía no tiene: descarta los modelos que no caben antes de intentarlos | `test_brain` (10) + medición real |
| **Electron** | Convertir la web en app de escritorio instalable | ⚠️ **No está, y hoy no cabe.** Ver "Las dos piezas que la guía no puede cumplir aquí" | — |
| **Capacitor** | Llevar la misma interfaz a móvil como app nativa | ⚠️ **No está.** La alternativa que sí se sirve hoy es la capa PWA (`manifest.webmanifest`), y el bloqueo es el mismo que el del core en `127.0.0.1` | `200 application/manifest+json` medido |
| **SpeechRecognition** (escucharte) | STT local | ❌ **Inviable en este equipo, medido:** `arecord -l` lista *"List of CAPTURE Hardware Devices"* **vacía** y `wpctl status` no muestra ni un *Source* de audio. No hay micrófono que leer | — |
| **pyttsx3** (hablarte) | TTS local | ⚠️ El motor **sí está** (`/usr/bin/espeak-ng`), pero el único *Sink* es *Dummy Output*: no hay por dónde sacar sonido. El `returncode` de un mando no prueba que alguien lo oiga (ya se vio con `wpctl`) | — |

**Seguridad:** la guía dice *"dejar Ollama y el backend atados a `localhost`, sin exponer puertos a internet"*. CORT ya lo hace (`127.0.0.1` a propósito). **Pero la guía se contradice a sí misma en el paso 6**: una app móvil empaquetada con Capacitor no puede hablar con un backend atado a `localhost`, porque `localhost` del teléfono es el teléfono. O se abre el core a la LAN (con token, y aun así cualquiera de tu WiFi ve el puerto), o el móvil lleva su propio core. **Esa decisión es de Sandra, no de código**, y está sin tomar.

## Las dos piezas que la guía no puede cumplir aquí

**Electron.** No es "otro instalador": Electron **es un Chromium extra**. Este portátil tiene 1,8 GiB de RAM y **263 MB disponibles** con el escritorio ya encendido (medido con `free -m`). El core + la interfaz ya se sirven en el navegador que existe; meter una ventana Electron encima es pagar 200–350 MB por el mismo HTML. **Y hay que decirlo con la regla 10 por delante: no se ha probado, porque instalarlo y levantarlo es justo la carga que ya congeló esta máquina.** Si algún día se prueba, se prueba con el navegador cerrado y midiendo `free -m` antes de abrir la ventana, y el resultado —quepa o no— se escribe aquí.

Lo que sí existe hoy y cubre el 90 % de lo que la guía pide de Electron: **el lanzador de doble clic** (`CORT.desktop`, `cort.bat`) que arranca core + interfaz y abre la ventana del navegador a pantalla completa. Se pierde la ventana "sin barra del navegador", se gana que CORT quepa en la máquina.

**Capacitor.** Empaquetar para Android pide **JDK** (aquí sólo hay *runtime*: `java` sí, `javac` **no**, medido), **Android SDK** (varios GB) y un build de **Gradle** que se come más de 1 GiB de RAM en su pico. En dos núcleos a 1,46 GHz eso no es "tardar más": es congelar el PC. **El APK, si se hace, se hace en otra máquina** (o en un runner de CI) y aquí sólo se escribe y se revisa el código. Mientras tanto, la PWA instalable es la vía real en el Samsung A16: mismo React, mismo `manifest`, sin Gradle.

## Y sobre C++ / Java

La guía **no los menciona**: su tabla de tecnologías es Python, JavaScript, React, Node.js, Electron y Capacitor. Aun así, medido por si vuelve la idea:

- **Java:** hay OpenJDK 21 *runtime*, no hay compilador (`javac` ausente). Escribir CORT en Java exigiría instalar un JDK y, sobre todo, tirar 124 pruebas y el core entero que hoy funciona.
- **C++:** `g++` y `gcc` sí están. Pero C++ no aporta multiplataforma aquí —la interfaz ya es multiplataforma *porque* es web— y sí costaría reescribir el backend que ya ejecuta acciones reales y verifica sus resultados.
- **Lo multiplataforma ya está resuelto por arquitectura, no por lenguaje:** un core Python que habla por WebSocket + una interfaz React que corre en cualquier navegador (PC, teléfono, tablet). Cambiar de lenguaje no añade ni un dispositivo donde funcione; añade una segunda implementación que mantener.

Donde **sí** tiene sentido un lenguaje compilado, y está en el roadmap, es en el borde: **firmware ESP32** (C++/MicroPython, Fase 7) para sensores reales. Ahí no hay navegador, y ahí iremos.

## Qué se adopta de la guía, dicho en una lista

1. **La pila se confirma tal como está** (Python + React + Ollama, todo en local). No se reescribe nada.
2. **La voz** (pasos 3 y 4) queda **bloqueada por hardware, no por código**: sin micrófono y sin salida de audio no hay nada que verificar. Con un USB de audio o auriculares Bluetooth conectados, `espeak-ng` ya está instalado y el paso 4 es corto.
3. **Escritorio**: el lanzador de doble clic hace el trabajo que la guía pide de Electron, con la mitad de RAM. Electron queda anotado como intento medible, no como feature.
4. **Móvil**: PWA ahora (hecho y servido); Capacitor sólo cuando haya dónde compilar el APK y una decisión tomada sobre la LAN.
5. **La guía entra en `CREDITS.md`** como referencia de ideas: no se copió una línea de ella porque no trae código.
