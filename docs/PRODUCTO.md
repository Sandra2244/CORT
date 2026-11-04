# Bases del producto: cómo funcionan de verdad las IA del día a día, y qué le toca a CORT

Escrito a las 01:30 del 2026-11-04, después de cerrar S4 y S5. Sirve para dos cosas:
entender qué es lo que se está imitando (y qué no se puede imitar en esta máquina) y dejar
decidido el producto en tres frentes: **Windows, Android (APK) y GitHub**.

Lo que va marcado como **medido** salió de este repo con su número. Lo que va marcado como
**patrón** es cómo funciona la industria en general; **pendiente de verificar** es lo que no
se puede afirmar hasta comprobarlo en el equipo de Sandra.

---

## 1. Qué es realmente una Claude o una Gemini

No son «un servidor con una base de datos de respuestas». Son cuatro piezas:

1. **Un modelo con pesos**, entrenado prediciendo el token siguiente miles de millones de
   veces. De ahí sale tanto la «anticipación de los hechos» (lo más probable que sigue) como
   la «intuición» (patrones semánticos que nadie escribió como regla).
2. **Una constitución** —un texto de principios— que se usó en el entrenamiento para que el
   modelo se auto-juzgue, en lugar de filtrarle cada respuesta a mano. Claude es el caso más
   visible; Gemini y Siri tienen las suyas, en forma de políticas de seguridad.
3. **Herramientas alrededor del modelo**: búsqueda web, ejecución de código, lectura del
   correo/calendario, control del dispositivo. El modelo decide *qué* pedir; el producto hace
   que eso ocurra.
4. **Memoria y contexto**: lo que sabe de ti se re-inyecta en cada conversación. En Claude y
   Gemini es un texto que viaja con el prompt (más un índice de tus documentos cuando lo
   activas). Es exactamente el mecanismo que CORT implementó en S4.

**El patrón de las tres superficies.** Todo asistente grande existe a la vez en tres sitios y
los cuatro hablan con el mismo servicio:

| Superficie | Para qué sirve de verdad | Ejemplo |
|---|---|---|
| App nativa (Android/iOS) | micrófono permanente, notificaciones, atajo del botón, leer la selección y compartir con otras apps | Gemini en el A16, Siri en el iPhone |
| Página web | sesiones largas, pegar documentos, historial editable | gemini.google.com, claude.ai |
| Escritorio | bandeja, atajos de teclado, acceso a archivos y a otras apps | Copilot en Windows, Claude desktop |
| El servicio | cuenta, sincronización, historial, límites de uso | lo que hace que la conversación empiece en el teléfono y siga en el PC |

**Siri y Alexa, que son el caso que más se parece a CORT:** el detector de la palabra de
despertiar corre **en el dispositivo**, en hardware pequeño, y sólo se envía a la nube lo que
se dice después del despertar. Siri además hace un montón de cosas localmente (hora,
calculadora, controles del teléfono) sin red. Alexa depende más de la nube, pero el chip de
escucha siempre está local. Por eso «funcionan aunque se caiga internet» para lo básico. En
CORT el equivalente ya existe y es local: la palabra de despertar con Vosk (F10) y las reglas
de la reja (F9), que contestan sin modelo si la frase es de las conocidas.

**Lenguajes que lleva un producto así** (patrón de la industria, no dato de CORT): Python y
C++ para el entrenamiento y el runtime del modelo; Rust o C++ en el borde y en los servicios
de inferencia; Kotlin/Java en Android; Swift en iOS; C# en el cliente de Windows;
TypeScript en la web. Un proyecto personal no elige el lenguaje por moda: lo elige la
superficie a la que tiene que tocar.

---

## 2. Qué puede imitar CORT en esta máquina, y qué no

| Lo que hace grande a Gemini/Claude | ¿Puede CORT? | Cómo, con número |
|---|---|---|
| Entender lenguaje natural | sí, en pequeño | modelos de 0,5–2 B en Ollama; en esta laptop ninguno cabe cargado con la interfaz abierta (158–268 MB libres medidos), así que manda la **reja de reglas** (F9) y el modelo es un añadido cuando hay máquina |
| Constitución + auto-crítica | **sí, y ya está** | `cort_memoria.py`: 7 principios (786 caracteres) en el `system` + `revisar()` que quita markdown y tumba promesas sin prueba; 1,56–3,21 ms por frase |
| Memoria de ti | **sí** | texto escrito en `memoria.json` y re-inyectado; no embeddings (una red semántica no cabe en 2 núcleos) |
| Anticipación | sí, por regla | iniciativa al conectar con enfriamiento de 30 min / 1 h / 6 h + pendientes con fecha (F4) |
| Voz con personalidad | a medias | TTS local (espeak-ng; Piper si cabe) y oído Vosk; el tono se varia por texto, no por prosodia |
| Buscar en la web | sí, con límite | el puente puede consultar APIs (clima ya lo hace); un buscador general requiere clave y red |
| Visión con modelo | no aquí | sin AVX/AVX2 y con ~200 MB libres, no cabe; S2 hace detección propia por piel+movimiento a 15 cuadros/s |
| Aprender de otros modelos (destilar) | **sí, en la única forma honesta que cabe** | banco local de ejemplos buenos que devolvió un modelo grande, recuperados por palabra clave y pegados en el prompt. Queda pendiente de construir; no es ajustar pesos |

---

## 3. Los tres frentes del producto

### 3.1 Windows — el setup de escritorio

Lo que ya sirve: el puente es Python 3.11+ y la interfaz es HTML/JS, así que corre en Windows
casi sin tocar nada. Lo que **no** sirve: `cort_acciones.py` habla con `wmctrl`, `xdotool`,
`pactl` y X11 —eso no existe en Windows.

Fase propuesta (**W1**, capa nativa de Windows), con las rutas reales por donde se ve:

| Acción en CORT | Linux (hecho) | Windows (por hacer) |
|---|---|---|
| listar/activar/minimizar ventanas | `wmctrl`, `xdotool` | PowerShell con `user32.dll` (`EnumWindows`, `SetForegroundWindow`, `ShowWindow`) |
| volumen | `pactl` | `nircmd` no: la API de extremo de audio (`Core Audio` por PowerShell o un helper C#) |
| abrir app | `xdg-open` | `start` / `ShellExecute` |
| apagar/suspender | `systemctl`, `loginctl` | `shutdown /h`, `rundll32 powrprof` |
| leer selección | `xsel`/primaria | `Get-Clipboard` |

Fase **W2** (instalador): un `CORT-Setup.exe` generado en GitHub Actions con **Inno Setup**
(open source) que lleve: Python embebido, el repo, el venv ya resuelto y el servicio de
usuario registrado. El instalador se escribe aquí, en el repo, y se puede leer línea por línea
antes de compilarlo —la regla de la casa es que ningún instalador de terceros se ejecuta a
ciegas, y la de CORT tampoco se le pide a nadie que lo bote de un dominio suelto: se descarga
del release con su SHA-256.

### 3.2 Android — el APK núcleo

Aquí hay que decir la verdad del peso, porque de ella depende la decisión:

| Opción | Qué trae dentro | Peso esperado | Estado |
|---|---|---|---|
| **APK cliente** (propuesto primero) | WebView con la misma interfaz, servicio en primer plano, emparejamiento con el PC (S3), micrófono y altavoz | **5–15 MB** | pendiente de compilar en Actions |
| **APK con Python embebido** | Chaquopy o python-for-android: el puente entero corriendo en el teléfono | **60–120 MB** comprimido, y baja la autonomía | pendiente; 100 MB es aceptable si de verdad aporta algo |
| **APK con Vosk en el teléfono** | modelo pequeño de español (~40 MB) para que el oído funcione sin PC | **45–60 MB** | pendiente de medir la latencia en el A16 |

Lo que se puede afirmar ya: 100 MB no es el problema; el problema es qué se trae dentro. El
núcleo (la reja, la memoria, la voz, la cámara) es Python y funciona igual en el A16 que en la
Canaima **porque el mismo puente corre en ambos**; el APK no reescribe el cerebro, lo envuelve.
El peso final se publica medido en el release, no estimado aquí.

Requisito duro antes de cualquier APK útil: **S3 (emparejar PC ↔ teléfono)**. Sin emparejamiento
y sin HTTPS en la red local, el navegador del A16 no deja usar el micrófono ni instalar la PWA,
y la memoria compartida quedaría en claro en la red de la casa.

### 3.3 GitHub — la página, el soporte y el canal

`Sandra2244/CORT` es a la vez el código, la página y la mesa de ayuda:

- **Página**: `README.md` en español con arquitectura e instructivo paso a paso (ya está), y
  GitHub Pages sirviendo `cort-web/` para que se pueda ver sin instalar.
- **Soporte**: los dos correos de `AVISO_LEGAL.md`; Issues con plantilla de «qué equipo, qué
  versión, qué salió en consola».
- **Canal de actualización**: U1 ya lee las etiquetas del repo y avisa sin auto-instalarse. Las
  notas de release se etiquetan `cort-vX.Y.Z` (la línea del trasplante, distinta de `v0.x` del
  repo viejo).
- **Artefactos por release**: el ZIP del código, el instalador de Windows, el APK y los
  **SHA-256** de cada archivo. Un instalador sin suma es un instalador que no se puede
  verificar, y verificar es la regla de la casa.

---

## 4. Las integraciones que se pidieron, una por una, sin prometer lo que no existe

| Pedido | Qué se puede hacer de verdad | Cómo se decide |
|---|---|---|
| «anota en mis notas del PC / Geany» | **sí**: F4 ya escribe notas en disco; falta `geany <ruta>` para abrirla y una orden «lee la nota que tengo abierta» | se comprueba en la Canaima con Geany instalado |
| «ponlo en Samsung Notes» | **pendiente de verificar**: Samsung Notes no expone una API pública para que otra app escriba. Lo honesto hoy es dejar el texto en el portapapeles y decir «pégalo» | se prueba con `adb shell pm list packages` y un Intent real en el A16; si no hay Intent, se dice y no se finge |
| «mándalo por WhatsApp» | **sí, con límite**: `wa.me/<número>?text=…` abre el chat con el texto escrito y el envío lo haces tú; o el menú de compartir de Android (`ACTION_SEND`). El envío automático exige WhatsApp Business y aprobación de Meta: no es un proyecto personal | se implementa como «preparar el mensaje», no como «enviar» |
| «tarea pendiente para tal fecha» | **ya está** (F4: `recordatorios.json`, con `reminder_trigger` medido por WebSocket) | — |
| «que investigue por mí» | a medias: puede consultar APIs que tengan clave (clima ya; buscador general pendiente) y puede leer lo que tú le pases | se decide en la fase de búsqueda |
| «que me ayude a ensayar» | **sí, y es barato**: con la memoria de S4 y la voz de F3 se puede hacer lectura por turnos («dime tú la definición, yo corrijo»); es una capa de diálogos, no un modelo nuevo | fase propia, pequeña |

---

## 5. Orden propuesto (hitos que se pueden tocar)

1. **S3** emparejar PC ↔ teléfono con código de 6 dígitos —sin esto nada del teléfono existe.
2. **F12-lite** APK cliente en Actions (5–15 MB) con el peso publicado.
3. **N1** notas: Geany + portapapeles + `wa.me` (las tres rutas honestas de arriba).
4. **W1** capa nativa de Windows (PowerShell) y **W2** instalador con SHA-256.
5. **D1** diálogos de ensayo sobre la memoria de S4.
6. **R1** el siguiente release de la línea del trasplante: hoy sólo existe `cort-v0.9.0`, así
   que el que cierre estos frentes sería `cort-v0.10.0`, con ZIP, instalador, APK y notas.

Lo que **no** entra en esta lista, dicho para que no se cuente: entrenar pesos, embeddings,
un modelo de visión en la Canaima, y cualquier instalador de terceros que no se haya leído.
