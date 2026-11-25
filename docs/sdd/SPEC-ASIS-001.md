# CORT-ASIS-001 — Asistente personal híbrido con evidencia

- **Fecha:** 2026-11-25
- **Estado:** EN CURSO
- **Base:** `cort-v0.19.0`
- **Decisión:** [ADR-004](DECISIONES.md#adr-004--asistente-personal-por-subfases-verificables)
- **Necesidad:** CORT debe servir como asistente cotidiano en PC y Android, no sólo como una cara que muestra paneles. Debe responder con voz y texto, ejecutar acciones comprensibles, organizar información sin daños y seguir siendo útil sin internet.

## Resultado esperado

La persona usuaria puede invocar a CORT desde el asistente de Android o desde la aplicación, hablar o escribir frases largas, ver una conversación ordenada y ejecutar acciones con confirmación cuando corresponda. La vista principal mantiene el orbe como identidad, pero no esconde la salida ni los controles esenciales.

Cada capacidad declara en qué plataforma funciona. Una limitación del sistema, del reproductor o de una aplicación se dice en español; no se sustituye por un éxito inventado.

## Decisiones heredadas

1. Android y voz primero; cada subfase se comprueba antes de publicar.
2. `VoiceInteractionService` propio y selección en Ajustes del sistema. Android decide dónde aparece.
3. Un solo centro de acciones accesible; modo enfoque con paneles ocultos, chat de pantalla completa superpuesto y vista rápida inferior translúcida.
4. Escucha local configurable, texto provisional, silencio y frases de hasta 60 segundos.
5. Pulsación larga del sistema, controles multimedia universales y adaptador de Lark sólo tras verificarlo.
6. Archivos: raíces autorizadas, metadatos/reglas, modelo local para ambigüedad, vista previa, movimiento reversible y nunca borrar.
7. Notificaciones: lectura por accesibilidad sólo al pedirla y borrador visible antes de responder.
8. Router: reglas → GGUF local → Gemini consentido → otras API → degradación local honesta.
9. Personalidad operador/compañero equilibrada, seis estilos y voces del TTS instalado.
10. Alarmas con catálogo local, nombre, días e instrucciones; frases con autor/fuente y rutinas de mañana/noche.

## Subfases

### ASIS-1 — Invocación, enfoque, chat y escucha larga

**Alcance**

- Vista rápida superpuesta al invocar el asistente, con permiso de superposición obligatorio.
- Una sola puerta táctil de acciones en Web y Android; hablar, chat, música y cierre se eligen dentro de ella, sin flechas ni entradas duplicadas.
- Comandos escritos y dictados usando las reglas existentes; una frase no reconocida se lleva al chat completo sin inventar una ejecución.
- Modo enfoque en la cara Web: orbe, micrófono y centro de acciones visibles; paneles ocultos.
- Chat accesible de pantalla completa superpuesto, con un solo compositor, historial de la sesión, cierre visible y foco contenido.
- Dictado local de hasta 60 segundos y ventana posterior a la palabra de hasta 60 segundos, con límite configurable y cierre garantizado.
- Entrada `PIDE_CHAT` desde la vista rápida para abrir el chat existente.
- Lenguaje visual común: orbe, menta/cian/magenta, cortes angulares, superficies oscuras y objetivos táctiles de al menos 48 dp/px.

**No alcance**

- No se agrega todavía reconocimiento continuo con pantalla apagada.
- No se interceptan botones de auriculares ni se promete control de Lark.
- La vista rápida no replica todos los paneles ni el router GGUF/nube; los comandos desconocidos se abren en la cara completa.
- No se copia código de TechEnClair sin licencia; se conserva su lenguaje visual mediante una capa propia.
- No se trasplantan dependencias React/Qt de las referencias al WebView; se trasplantan patrones de interacción y accesibilidad, no arquitecturas incompatibles.

**Criterios de aceptación**

| ID | Dado / Cuando / Entonces | Prueba |
|---|---|---|
| ASIS-1.1 | Dado que Android invoca a CORT / Cuando hay permiso de superposición / Entonces aparece un panel inferior translúcido sin abrir otra actividad | Estática + build + A16 |
| ASIS-1.2 | Dado que falta el permiso / Cuando se invoca / Entonces CORT abre Ajustes para concederlo y no simula un overlay | Estática + build + A16 |
| ASIS-1.3 | Dado el panel / Cuando se toca Hablar / Entonces se pide micrófono y se muestra el texto provisional y final | Estática + build + A16 |
| ASIS-1.4 | Dado un comando escrito o dictado / Cuando la tabla lo reconoce / Entonces se ejecuta una vez y se muestra la respuesta | Prueba Java del lazo + A16 |
| ASIS-1.5 | Dado un comando desconocido / Cuando se procesa / Entonces se abre el chat completo con la frase, sin decir que se ejecutó | Estática + A16 |
| ASIS-1.6 | Dada la cara Web / Cuando entra en enfoque / Entonces el orbe y los controles esenciales siguen visibles y los paneles no reciben el foco | Estática + navegador |
| ASIS-1.7 | Dado el enfoque / Cuando se toca Chat / Entonces aparece una conversación con entrada, salida y cierre accesibles | Navegador + A16 |
| ASIS-1.8 | Dado el micrófono local / Cuando pasan 60 segundos o se cancela / Entonces se cierra y la frase no excede el límite | Estática + prueba Java + A16 |
| ASIS-1.9 | Dado un comando sensible o una salida / Cuando termina / Entonces el chat no interpreta HTML ni ejecuta código recibido | Prueba Web |
| ASIS-1.10 | Dada la cara principal / Cuando se busca una acción / Entonces hay un único centro identificado y no existen flechas, botones Chat/Paneles ni compositores duplicados | Estática + navegador |
| ASIS-1.11 | Dado el centro de acciones / Cuando se abre / Entonces expone estado ARIA, cierre accesible, foco contenido y Escape; al elegir una vista se cierra | Navegador |
| ASIS-1.12 | Dado el chat / Cuando se abre / Entonces ocupa el área visible completa, conserva el orbe detrás, tiene un solo compositor y no corta controles en 360/525 px | Navegador móvil + escritorio |
| ASIS-1.13 | Dados los controles nuevos / Cuando se miden / Entonces todos tienen al menos 48 px y respetan áreas seguras y movimiento reducido | Navegador + A16 |
| ASIS-1.14 | Dada la vista rápida nativa / Cuando se invoca con auriculares / Entonces muestra la misma jerarquía visual y una sola puerta de acciones, sin prometer chat en la nube | Estática + build + A16 |
| ASIS-1.15 | Dado el modo enfoque / Cuando se abre el centro o el chat / Entonces siguen visibles y el resto de paneles no recibe foco | Estática + navegador |

**Plan y archivos**

1. Prueba roja en `scripts/prueba_apk.py` para permiso, overlay, sesión, límites, enfoque y chat; revisión visual posterior en navegador.
2. `AndroidManifest.xml`: permiso `SYSTEM_ALERT_WINDOW` declarado, sin otorgarlo.
3. `VistaRapida.java`: una sola ventana, ciclo de cierre y controles táctiles.
4. `Sesion.java`: mostrar la vista rápida en vez de abrir siempre `MainActivity`.
5. `MainActivity.java` y `Nexo.java`: entrada para abrir chat y estado inicial del modo enfoque.
6. `Motor.java`, `Voz.java`: límites configurables y texto provisional.
7. `Acciones.java`: depender de `Context`, no de `Activity`, para poder ejecutar reglas desde la vista rápida.
8. `index.html`, `cort-ui.js`, `cort-style.css`: un único centro de acciones, chat completo superpuesto y enfoque accesible.
9. Revisión visual con referencias de HERMES/OpenJARVIS: estado ARIA, foco atrapado/restaurado, Escape, búsqueda opcional y objetivos táctiles; sin copiar su código ni dependencias.
10. `VistaRapida.java`: la misma puerta de acciones y paleta, conservando el lazo local y el cierre seguro.

**Prueba roja esperada**

La suite APK debe fallar antes del parche por ausencia de permiso, `VistaRapida`, ruta de sesión y límite de 60 segundos. La suite Web debe fallar por ausencia de modo enfoque y chat. El fallo se registra antes de implementar.

**Evidencia**

- Prueba roja inicial: `python3 scripts/prueba_apk.py` → 237/250; los 13 fallos corresponden a permiso, overlay, sesión, chat, límites y texto provisional.
- Endurecimiento posterior: 250/255 antes de añadir los controles de cierre de SQLite y del hilo; resultado verde registrado 255/255.
- Revisión de interfaz solicitada el 2026-11-25: la evidencia funcional anterior no acepta la jerarquía visual. Se añaden ASIS-1.10–1.15 y una nueva prueba roja antes de implementar.
- Prueba roja de la reorganización: `254/266`; los 12 fallos previstos correspondían a tres controles nativos y nueve comprobaciones Web.
- Resultado verde estático: `266/266 comprobaciones`; incluye centro único, diálogo accesible, chat completo, foco, Escape, búsqueda, dictado, texto seguro, enfoque y vista rápida plegable.
- Navegador same-origin, sin Ollama y con el puente aislado en `18765`:
  - `360×640`: chat de `360×640`, un compositor, cero flechas, controles de al menos 48 px y sin desborde horizontal.
  - `525×521`: chat de `525×521`; Cerrar, entrada y Enviar de 48 px; búsqueda `chat` deja sólo la acción de chat; Escape cierra el menú; el cierre del chat devuelve el foco a Acciones.
  - `1280×800`: chat de `1280×800`, menú de `560×706`, sin desborde horizontal.
- Comportamiento Web: el formulario emite una sola entrada `{type:"user_input", text:"hola"}` y limpia el campo; el dictado parcial muestra `Hablar` sin robar foco y el final deja el campo limpio y un solo mensaje; dos cargas con `<img onerror>` y `<script>` producen cero imágenes, cero scripts y texto literal.
- Enfoque: orbe, micrófono y centro visibles; Ajustes oculto; menú y chat continúan abriendo.
- Consola del arnés aislado: sólo errores esperados de `ws://127.0.0.1:18765/ws`, porque ese servidor HTTP no implementa WebSocket; no se observaron errores JavaScript de la interfaz nueva.
- Validaciones locales: `node --check cort-web/cort/cort-ui.js`, `bash -n apps/android/compilar.sh`, `python3 -m py_compile scripts/prueba_apk.py` y `git diff --check` en verde.
- Suites locales en arena `CORT_HOME`/`CORT_DATOS`: seguridad Web/puente/Android `30/30`; APK/Web `266/266`.
- Pendiente: build Android, verificación de `LimiteEscuchaTest`, actualización del servicio y prueba física en A16. No se marca VERIFICADA con sólo estática y navegador.

### ASIS-2 — Alarmas, frases y acompañamiento diario

**Alcance previsto**

- Parser puro para hora, AM/PM, nombre e instrucciones largas.
- Catálogo local de alarmas con hora, días, etiquetas e instrucciones.
- `AlarmClock.ACTION_SET_ALARM` con nombre cuando la app de reloj lo acepte; programación propia sólo con permiso exacto y receptor visible.
- Frases motivadoras locales con autor, obra/fuente y licencia o revisión de derechos.
- Rutinas «Buenos días» y «Buenas noches»; lectura al despertar o antes de dormir cuando se solicite.
- Ejemplos obligatorios: «Alarma a las 6:00 AM, despertarse para ir al ambulatorio Apamates 1» y «Alarma a las 9:00 PM, ir a dormir para despertar temprano e ir al centro a comprar ropa».

**Pruebas obligatorias antes de código:** horas inválidas, 12 AM/PM, instrucciones que contienen «y», conservación de nombre, catálogo sin duplicados y frase con procedencia completa.

### ASIS-3 — Música, auriculares y archivos reversibles

- Controles multimedia universales; Lark sólo con API/intent verificado.
- Reproducción de pista o playlist sin confundir nombre de app y canción.
- Organización por carpetas autorizadas, metadatos y similitud; vista previa, registro y deshacer.
- Ninguna prueba mueve archivos reales ni reproduce audio: arena `CORT_HOME`/`CORT_DATOS`.

### ASIS-4 — Notificaciones, personalidad, voces y router híbrido

- Lectura de notificaciones por acción explícita; borrador antes de responder.
- Seis estilos de personalidad y voces disponibles en el motor instalado, sin imitar identidades comerciales.
- Router común reglas → local → nube consentida → degradación, con presupuestos y cancelación.
- Gemini real en PC y Android; ausencia de internet produce una respuesta local útil y honesta.

### ASIS-5 — Base 1.0 estable

No se declara por completar código. Requiere suites verdes, build firmado, actualización con datos conservados, motor/oído/cara en el APK y prueba física en el Samsung A16 de GGUF, voz, segundo plano, overlay, alarmas, música y modo sin internet. No puede haber un P0 abierto.

## Borde y seguridad

- Sin permiso de superposición o micrófono: explicación y ruta a Ajustes, sin crash.
- Al cerrar la vista rápida: se retira la ventana, se detiene el dictado y se libera el micrófono.
- Texto externo y del modelo: siempre texto, nunca HTML.
- Comandos desconocidos: no se ejecutan ni se presentan como éxito.
- La nube conserva el consentimiento por turno de SEC-001.
- Alarmas, música y archivos no se ejecutan en las pruebas locales.

## Evidencia física pendiente en A16

1. Seleccionar CORT en Ajustes → Asistente de voz.
2. Conceder superposición y micrófono.
3. Invocar con pulsación larga y auriculares Bluetooth.
4. Dictar una instrucción larga, comprobar texto provisional y duración.
5. Ejecutar una regla inofensiva y comprobar una sola ejecución.
6. Abrir el chat, enviar texto y leer una respuesta.
7. Cerrar y comprobar que el micrófono se apaga.
8. Repetir sin internet y registrar qué capacidades quedan disponibles.
