# PLAN MAESTRO — de «la app que se instala» a «el núcleo que hace de todo»

Escrito la noche del **2026-10-22**, el día que CORT se quedó en su teléfono:
**`CORT-IA-2.5.0-nucleo.apk` se instaló y funciona** («me gustó, funcionó… las
interfaces táctil muy bien»). Este documento no es código: es el mapa. Sirve para que
cualquier ronda —conmigo, con otra IA, o con ella misma abriendo el repo— sepa **qué se
pide, qué se puede, qué cuesta y en qué orden se hace**.

---

## 0 · Lo que acabamos de cerrar, porque manda sobre todo lo demás

| envase del mismo CORT | superficie del manifiesto | resultado en su teléfono |
|---|---|---|
| `CORT-IA-1.1.4` (peso 1,7 MB) | 13 permisos, **0** `BIND_*` | se instala |
| `CORT-IA-2.4.2` / `‑ligero` | 28 permisos, **4** `BIND_*` en cinco servicios | **bloqueado** (los dos) |
| **`CORT-IA-2.5.0-nucleo`** | **21 permisos, 0 `BIND_*`** | **se instala y funciona** |

El experimento de cinco rondas terminó con una sola variable confirmada: **la superficie
de integración** (ser asistente del sistema, leer notificaciones, baldosín, llamadas).
El payload quedó **exonerado por completo**: el núcleo que ella usa ahora lleva dentro
las cuatro `.so` de Vosk y el modelo de ~40 MB, y entra igual.

De ahí sale la **regla de oro** de todas las rondas que vienen:

> Cada función que pida una superficie privilegiada **cuesta reinstallabilidad**. No se
> añade en silencio: se dice el precio, y ella decide con la escalera de envases
> (`nucleo` → `nucleo+avisos` → `completo`, tarea #97). El envase por defecto de su
> teléfono es el **núcleo**. La llave de firma `fa:ab:ef:46…` y el `versionCode` no se
> mueven: cambiarla obliga a desinstalar y se lleva su perfil, su clave de Groq y sus notas.

---

## 1 · Los doce deseos de su mensaje, en cuatro frentes

Ella escribió de corrido; aquí está repartido. Entre paréntesis, la tarea del listado.

**Frente A — la CARA (que parezca un producto, no botones montados)**
- Menú con apartados reales: herramientas, ajustes, accesibilidad, cada cosa en su sitio (#92).
- La música **fuera de la bandeja inferior**: botón accesible y píldora recogida en una esquina/lateral para que no esté «atravesada» (#93).
- Los botones del reproductor **se traban**: reproducir, encontrar la causa, arreglar y dejar prueba (#94).
- La hoja **MV/AMV**: calco de la interfaz y el gesto de **Lark Player** (#96).
- Animaciones de **vidrio y agua**: bonitas y ligeras, y **que se apaguen** jugando o con poca RAM (#102).

**Frente B — que CORT ACTÚE por ella**
- «Reproduce música» → en el **reproductor predeterminado** (Lark) si se lo dice; el propio de CORT sigue existiendo, y en modo juego que no estorbe ni se bugee (#95).
- «Manda un mensaje a mi madre… dile que ya voy saliendo» → contactos por nombre y apodo, redactar y **enviar con un toque** (#98).
- La escalera de envases para poder leer avisos sin volver a provocar el bloqueo (#97).
- Guardián anti-malware/spyware, auto-reparación y **encender la pantalla por voz** (#99).

**Frente C — el CEREBRO y sus modelos**
- Hoja **interactiva** de modelos: ver, descargar, elegir, borrar (Ollama de casa y modelos del teléfono) (#101, y #79 para GGUF dentro del aparato).
- Vocabulario y órdenes sin nube: ya hay 283 frases en 33 reglas; se amplían por área, no a lo loco (#66, #69).
- Clima por ciudad **también sin PC** (#90) y mandos de voz pedidos **por frase** (#91).

**Frente D — que sepa QUIÉN es y a QUIEN sirve**
- Perfil editable: **nombre de la IA**, rol o personalidad, inspirada en una persona, y un bloque **«sobre mí»** (gustos, vivencias, su gente) que entre en la consigna (#100).
- Que las funciones **se adapten al aparato** (PC / teléfono / cámara) y no prometan en uno lo que sólo puede en otro — la matriz del §3.

---

## 1.5 · Cómo está la cara HOY, leído en el código (para no rediseñar a ciegas)

Esto es lo que hay dentro ahora mismo, con su sitio exacto. Cambia más de un diagnóstico.

- **La «bandeja de abajo» es `#dock`**: doce botones escritos a mano en `ui/index.html:74-89`
  (Archivos · Entorno · Canal · Notas · Musica · Consola · Perfil · Cerebro · Modelos ·
  Optimizar · Ayuda + abrir/ocultar + la lámpara). En PC está centrado abajo y casi a todo
  el ancho (`ui/css/hud.css:84-85`, `max-width:96vw` con `flex-wrap`); en el teléfono es una
  **tira horizontal que se desplaza** (`hud.css:419-424`). Y ya se esconde en las hojas que
  no son el Orbe (`hud.css:670-677`). **No existe ningún mecanismo para ponerlo lateral o en
  una esquina**: hay que construirlo (precedente útil: la barra de hojas sí se reubica a la
  esquina en móvil, `hud.css:634-635`).
- **Por qué «se traban los botones» del reproductor** — dos candidatas con nombre y línea,
  no teorías:
  1. El **deslizar para cambiar de hoja** escucha `touchstart`/`touchend` en la pantalla
     entera y con 90 px de recorrido ya salta de hoja; ignora las listas (`.scr-lista`,
     `#plist`, `#flist`) pero **no ignora los botones del transporte**
     (`ui/js/pantallas.js:142-159`). Resultado: pulsar «play» con el dedo un poco torcido
     no reproduce, **te lleva a otra hoja**.
  2. El botón flotante del micrófono se reubica **justo encima** de la hoja de música
     (`hud.css:711-714`, `right:16px; bottom:18px`, con `.scr` en `z-index:66`) y el
     transporte de Música y MV comparte plantilla (`pantallas.js:602-620`): el último botón
     de la fila queda bajo el FAB.
  Los manejadores son `.onclick` (no `touchstart` duplicado) y cada hoja se monta con
  `innerHTML` fresco, así que **no** son listeners dobles. El freno de 1,5 s es del oído
  (`ui/js/voice.js:67`), no de los botones.
- **El «optimizador» del teléfono no está roto: no existe.** Lo real vive en el PC (ventana
  11 + `backend/app/optimize.py`, con lista cerrada de cachés e intocables). En el APK no hay
  matador de apps ni limpiador: sólo `modoJuego()` (`pantallas.js:1113-1130` →
  `CortNative.java:1227`, que suelta micro y foco audio). Lo que sí existe es el **botón
  «Optimizar» del dock en el teléfono**, que lleva a una hoja pensada para el PC. Eso explica
  su queja mejor que cualquier bug.
- **Los modelos de Ollama ya son interactivos, pero en el sitio equivocado**: la hoja Equipo
  tiene input de servidor, botones buscar/míos/bajar/fijar, lista con tamaño y cuantización y
  **barra de progreso de verdad** (`ui/js/telefono.js:316-338`, `#eq-oll-barra`,
  `telefono.js:916-917, 993-1004`). En la hoja Código son sólo frases. #101 es por tanto
  **sacar eso a su propio apartado del menú**, no inventarlo.
- **El perfil ya medio sirve**: en PC la ventana 07 guarda `asistente` (nombre de CORT),
  `usuario`, `tono` (JARVIS elegante / formal / cercano / muy breve), `idioma`, `ciudad` y
  los tres mandos de voz (`hud.js:561`, `hud.js:157-215`), y `brain.py:165-183` mete
  «Tu nombre es …» y «El usuario se llama …» en la consigna de Groq y Gemini. **Lo que falta
  es en el teléfono**: no hay campo para renombrar a CORT ni editor de personalidad, y no hay
  bloque «sobre mí» (gustos, su gente) más allá de que `Recuerdos.java` aprende su nombre.
- **El chat**: la hoja **Charla** sí tiene copiar por burbuja, «copiar respuesta», guardar en
  Notas y 40 líneas en `localStorage` (`pantallas.js:245-271, 344-345`), y se puede
  seleccionar texto. En cambio la ventana **03 · Canal** del PC en móvil queda bajo
  `user-select:none` (`hud.css:380`) y **nadie restaura el historial**: el backend lo guarda
  en SQLite y sirve `GET /api/history` (`main.py:160-161`), pero ni `hud.js` ni `pantallas.js`
  lo llaman. Es un «no se ve mi charla de ayer» con causa exacta.

Con estos cinco hechos, el rediseño deja de ser «ponlo bonito» y se convierte en una lista
de cosas concretas que están mal puestas, a medias, o en el sitio equivocado.

---

## 2 · Tabla de viabilidad: qué se puede, a qué precio, dicho antes

Sin adornos. «Se puede» = hay una API pública que lo hace sin root; «a medir» = hay una
vía concreta pero no lo afirmo hasta probarla en su teléfono; «no» = no lo voy a fingir.

| lo que ella quiere | veredicto | por qué / qué hace falta |
|---|---|---|
| Menú, secciones, ajustes, accesibilidad, chat con historial y copiar texto | **se puede** | es HTML/CSS/JS de `ui/`, que se copia tal cual al APK. Cero permisos. La hoja Charla ya copia y selecciona; lo que falta es el historial restaurado (`/api/history` existe y nadie lo llama) y que la ventana 03 en móvil permita seleccionar. |
| Píldora de música en el lateral, fuera de la bandeja | **se puede** | CSS y un botón; hoy el dock no tiene ninguna opción de posición, así que hay que añadirla (y guardarla). |
| Botones que se traban | **se puede arreglar, y ya tiene dos causas concretas** | el gesto de cambiar de hoja no ignora los botones del transporte (`pantallas.js:142-159`) y el FAB del micro cae encima de esa fila (`hud.css:711-714`). Se arreglan las dos y se deja prueba. |
| Poner música en **otro** reproductor (Lark) | **se puede** | `Intent` con el `package` o `ACTION_VIEW` sobre `audio/*`. Sin permisos nuevos. |
| CORT suene en segundo plano mientras juega | **se puede** | ya existe `modoJuego` (suelta el foco audio y cierra el micro); falta que la cara no pelee con el reproductor del sistema. |
| Leer avisos de WhatsApp y contestar **ella sola** | **cuesta superficie** | leer = `BIND_NOTIFICATION_LISTENER_SERVICE` (es de lo que delata al envase). Escribir y **enviar sin tocar** = Accesibilidad: la superficie más vigilada por Google. Lo que sí entra en el núcleo: redactar y abrir el chat **con el texto puesto**, y que ella pulse enviar. |
| «Enciende la pantalla» / desbloquear desde suspensión | **a medir** | un `WAKE_LOCK` solo no enciende la pantalla. La vía honesta es notificación con `USE_FULL_SCREEN_INTENT` + `setShowWhenLocked(true)`/`setTurnScreenOn(true)`: **no** es una superficie `BIND_*`, así que cabe en el núcleo. Se prueba y se dice si a su teléfono le vale. |
| Auto-reparación «ejecutando comandos de terminal» en el Android | **no, sin ayuda externa** | una app normal no puede lanzar `input`, `settings put` ni `svc`. O se hace con lo que sí es de app (intents, ajustes, reiniciar sus propios servicios) o con **Shizuku / depuración por Wi-Fi**, que es decisión de ella y se documenta antes. |
| Antivirus real que bloquee malware/spyware | **no** | no hay motor AV que quepa ni licencia para uno. Lo que sí: auditar permisos concedidos, avisar si otra app pide Accesibilidad o ser administradora, revisar APKs recién bajados (firma, empaquetado) y decir qué ve Play Protect. Eso es un **guardián**, y se llama guardián. |
| Optimizador / game booster del teléfono | **no está roto: no existe** | en el APK no hay matador de apps ni limpiador — sólo `modoJuego()`. Lo que hay es un **botón «Optimizar» en el dock del teléfono** que abre una hoja pensada para el PC. Y aunque se escribiera, matar otras apps y «limpiar RAM» no lo deja Android (el permiso de uso de aplicaciones **ella ya lo rechazó**). Lo real: apagar WebGL y animaciones, cerrar su micro y soltar el foco audio, bajar el refresco de paneles, elegir cerebro local/nube y abrir los ajustes de batería del sistema (#103). |
| Modelos de Ollama desde el teléfono | **se puede y ya está hecho a medias** | el servidor Ollama **no cabe** en un APK (es Go, pide un ordenador); lo que viaja es el cliente, que ya busca, lista, descarga con **barra de progreso real** y elige por Wi-Fi de casa — pero **dentro de la hoja Equipo**. Falta sacarlo a su propio apartado del menú (#101). |
| Modelo GGUF corriendo **en el propio teléfono** | **se puede, con coste** | llama.cpp cruzado-compile en el pipeline (tarea #79). Coste real: 1–4 GB de sitio, batería y calor. Se decide con números delante, no por entusiasmo. |
| Voz natural (Piper) en el PC | **se puede, pesa** | modelo de varios MB por voz en un portátil de 1,8 GiB: descarga opcional, decisión de ella (#91). |
| «Que se integre sin rechazo» y «haga de todo» | **tensión real, y se gestiona** | son los dos extremos de la misma cuerda: cuanto más se integra (asistente, accesibilidad, leer todo), más se parece —a los ojos de un clasificador sin contexto— a un troyano. Por eso existen los envases: **ella elige cuánto integration por aparato**. |

Lo que **no** voy a volver a prometer: que un cambio en el repo borre un veredicto de
Google o de SmartScreen, y que una app normal haga lo que Android reserva al sistema.

---

## 3 · Matriz de funciones por aparato (lo que ella llamó «que se adapte a cada dispositivo»)

| capacidad | PC (Linux/Windows) | Teléfono (Android) | Cámara / otros |
|---|---|---|---|
| Hablar | **núcleo con `espeak-ng`** (el navegador da 0 voces, medido) | `TextToSpeech` del sistema | — |
| Oír | navegador (donde haya voces) / micrófono del sistema | oído propio **Vosk sin nube** dentro del APK | gesto de mano con MediaPipe (cámara del PC) |
| Cerebro | Ollama local si cabe (2 núcleos / 1,8 GiB: **no** con el navegador abierto) + Groq/Gemini por clave | nube con su clave en el aparato, o el Ollama del PC **por Wi-Fi** | — |
| Leer sus cosas | SQLite de notas, documentos, carpetas | avisos (sólo en el envase que lleve el lector), música, vídeos | — |
| Actuar | abrir apps, terminal, organizar archivos con plan y confirmación | intents, volumen, linterna, alarma, abrir app, reproductor | — |
| Animación pesada | sí, con freno si falta RAM | **no** con modo juego activo | — |

Regla de diseño: **la misma cara, y cada botón pregunta si su aparato puede**. Si no
puede, dice qué falta (permiso, envase, PC o red) en vez de fingir que lo hizo. Eso ya
existe (`window.CORTcapaz(puerta)`, las hojas que cantan `envase nucleo`) y hay que
extenderlo a las funciones nuevas.

---

## 4 · El orden de rondas que propongo

Cada ronda termina en algo que ella **ve y usa**, se prueba desde el repo, y se instala
**encima del núcleo** sin desinstalar nada. Ninguna abre una superficie privilegiada sin
pedírselo antes.

1. **F8 · La cara ordenada** (#92, #93, #94, #102) — el dock de doce botones convertido en
   menú por secciones, la música con píldora lateral, el gesto de hoja que ya no se come los
   botones del reproductor, el FAB del micro fuera de esa fila, el historial del chat
   restaurado desde `/api/history`, y vidrio y agua con freno. *Puro `ui/` + CSS: no toca el
   manifiesto, así que el envase sigue siendo el que entra.* Es la que más se nota y la más
   barata.
2. **F9 · Música sin pelearse** (#95, #96) — predeterminado vs propio, Lark Player por
   nombre, MV con el gesto de Lark, ligero en juego.
3. **F10 · Perfil vivo y voz por frase** (#100, #91, #90) — nombre de la IA, rol,
   «sobre mí», «más grave / más rápido», clima en el teléfono sin PC.
4. **F11 · CORT actúa por ella** (#97, #98) — la escalera de envases y el mensaje
   dictado con un toque. *Aquí es donde se habla del precio de superficie, con números.*
5. **F12 · Modelos a la vista** (#101, #79) — hoja interactiva de Ollama y decisión
   informada del GGUF en el aparato.
6. **F13 · Guardián y pantalla** (#99, #103) — lo que se puede auditar y reparar de
   verdad, el intento medido de encender pantalla, y la hoja de optimizador reescrita
   con honestidad.

Y en paralelo, sin ronda propia: **la auto-actualización del escritorio desde la
Release** (#87), que es lo que convierte esto en un producto con soporte.

---

## 5 · El prompt maestro (lo que ella pidió: «ayúdame a construir mejor este prompt»)

Su mensaje original tenía doce ideas, erratas y ningún orden, y con eso cualquier IA —
esta o la de su otra cuenta, que también usa— se pierde. Este bloque es el que le
recomiendo copiar y pegar **siempre** antes de pedir nada. Está escrito para que quepa en
la cuota de cualquiera y para que la respuesta sea accionable.

```text
PROYECTO: C.O.R.T. — asistente tipo JARVIS/Cortana. Repo público github.com/Sandra2244/CORT,
rama v0.2-demo. Cara = HTML/CSS/JS plano en ui/ (misma en PC y dentro del APK). Núcleo =
FastAPI en backend/app. Escritorio = Electron (desktop/). Teléfono = APK compilado SIN Gradle
en GitHub Actions (aapt2 + kotlinc + javac + d8 + zipalign + apksigner, fuente en apps/apk/).

MIS APARATOS (importante, no me des soluciones que no corran aquí):
- Portátil Linux Xfce, 2 núcleos, 1,8 GiB de RAM. NO puedo tener Ollama + navegador + servidor a la vez.
- Android 8+ (arm64), con CORT-IA-2.5.0-nucleo.apk instalado y funcionando.

REGLAS DURAS, no negociables:
1. El APK que uso es el NÚCLEO: 21 permisos y CERO servicios BIND_*. Cualquier función que
   necesite superficie privilegiada (leer notificaciones, ser asistente del sistema, toque
   automático por Accesibilidad) DEBE decirme el precio antes de añadirla, y proponer un
   envase aparte, nunca tocar el núcleo.
2. No cambies la llave de firma ni bajes el versionCode: obligarían a desinstalar y pierdo
   perfil, clave de Groq y notas. Actualizar = instalar ENCIMA.
3. No leas ni muestres mis claves (backend/.env, «Api keys personales»). No subas secretos.
4. No construyas el APK ni los instaladores en mi portátil: se compila en Actions.
5. No inventes. Si no lo mediste o no lo probaste, dilo como sospecha o di que falta medir.
   Las tablas del README y los docs llevan sólo números medidos.
6. Nada de relleno: ningún byte, permiso o botón que no haga algo.
7. Cada cambio suyo lleva su prueba en scripts/prueba-*.py (o .mjs/.sh), stdlib, en español,
   y se monta en el pipeline con anotación ::error:: si falla (los logs de Actions son privados).
8. Corrige hacia delante: no reescribas etiquetas ni hagas force-push de lo publicado.

CÓMO PEDIRTE LAS COSAS: te doy UNA área por mensaje, con este orden:
  QUÉ quiero (una frase) · DÓNDE se ve (PC / teléfono / qué hoja) · PARA QUÉ (mi caso real)
  y si sé que hay un obstáculo, lo digo.
CÓMO CONTESTARME: (a) si se puede con lo que ya hay, hazlo y prueba; (b) si necesita permiso,
envase o decisión mía, dime el precio en una línea y espera; (c) si Android/Windows no lo
permiten, dilo claro y dame la alternativa más parecida. Sin sermones y sin listas de 30 ideas.

MI OBJETIVO DE FONDO: que CORT sea un compañero de día a día (programación, clima, música,
mensajes, archivos, memoria, personalidad editable) que se integre en cada aparato sin que el
sistema lo rechace, y que se actualice solo desde GitHub. En el PC mando yo el sistema
operativo; en el teléfono manda Android: las mismas funciones, adaptadas, nunca fingidas.
```

Y cuando quiera algo concreto, una línea detrás de ese bloque, por ejemplo:

> `Frente A · la cara: la barra de música está atravesada en el borde inferior y estorba
> cuando hablo con CORT. Quiero una píldora en el lateral derecho, que se pliegue sola.
> Teléfono y PC a la vez. Sin permisos nuevos.`

Tres frases. Con eso no hay que adivinar, y la ronda sale entera.

---

## 6 · Dudas que sólo ella puede resolver (no bloquean la F8)

1. **«Uno dice CORT PC y está atravesado»**: lo he leído como *la barra de música cruza el
   ancho de la pantalla por abajo y estorba*, y por eso va al lateral. Si te referías a otra
   cosa (que la voz «CORT» se confunde con «PC», o que la barra tapa el teclado), dime cuál.
2. **Lark Player**: ¿el de la Play Store que usas ahora es «Lark Player» o **Musico/Music
   Player** u otro con la misma cara? Lo necesito para copiar el gesto correcto y no uno
   inventado. (Si me pasas capturas, mejor que el vídeo.)
3. **El mensaje «a mi madre»**: ¿por WhatsApp, SMS o ambos? Cambia el camino, no el deseo.
4. **Shizuku / depuración por Wi-Fi**: es la única vía a «comandos de terminal» en Android
   sin root. Requiere que actives el desarrollo inalámbrico. ¿Sí o prefieres que el
   auto-cuidado del teléfono se quede en lo que una app normal puede tocar?
5. **Cuánto estás dispuesta a perder de integración por aparato**: el `nucleo` entra y no
   lee avisos; el `nucleo+avisos` lee avisos y **puede** volver a provocar el aviso de
   Google. Es tu elección y la respeto en los dos sentidos.
