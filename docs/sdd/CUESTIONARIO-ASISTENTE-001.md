# Cuestionario del asistente personal — CORT-ASIS-001

- **Fecha:** 2026-11-25
- **Estado:** EN ESPERA DE RESPUESTA
- **Base publicada:** `cort-v0.19.0`
- **Objetivo:** convertir a CORT en un asistente híbrido utilizable a diario en PC y Android, con el orbe como identidad y una vista rápida superpuesta inspirada en el asistente de Galaxy.

Este documento no autoriza código todavía. Cuando estén elegidas las diez opciones se registrará el ADR, la SPEC, el plan y la prueba roja.

## Decisiones

### 1. Orden de entrega

- **A (recomendado):** asistente Android y voz → música y archivos → router híbrido. Cada subfase se prueba y publica; al final se evalúa 1.0.
- **B:** una sola entrega con todas las funciones.
- **C:** organizador de archivos primero.

### 2. Cómo aparece CORT como asistente Android

- **A (recomendado):** `VoiceInteractionService` propio, selección de CORT en Ajustes y permiso de superposición para la vista rápida.
- **B:** sólo burbuja flotante mediante accesibilidad, sin registro como asistente.
- **C:** mantener únicamente la aplicación a pantalla completa.

Android y One UI deciden dónde aparece CORT en el selector. No se puede hacer que CORT se haga pasar por Google ni saltarse permisos.

### 3. Orbe, chat y vista previa

- **A (recomendado):** pantalla principal en modo enfoque —fondo oscurecido, orbe protagonista, paneles ocultos— con chat a un toque; overlay inferior translúcido con Chat, Acciones y Música.
- **B:** chat siempre visible y orbe reducido, con el mismo diseño en el overlay.
- **C:** alternar automáticamente entre enfoque y chat según la actividad.

### 4. Escucha y frases largas

- **A (recomendado):** oído local continuo configurable, texto provisional, silencio ajustable y frases de hasta 60 segundos; pulsar-para-hablar para lugares ruidosos. Reconocimiento de Android sólo con permiso.
- **B:** micrófono siempre abierto sin límite de duración.
- **C:** reconocimiento en la nube por defecto.

El coste de RAM, batería y segundo plano debe medirse. La palabra de activación y el micrófono no se confunden con una autorización permanente para enviar audio.

### 5. Auriculares, reproductor y Lark Player

- **A (recomendado):** asistente por pulsación larga del sistema, controles multimedia universales y adaptador de Lark Player sólo después de verificar qué API o intents permite.
- **B:** intentar interceptar todos los botones de auriculares, incluso con root.
- **C:** dejar auriculares y música para otra fase.

El doble toque para cambiar de canción depende de que el reproductor respete la sesión multimedia. No se promete control específico de Lark Player antes de probarlo.

### 6. Organización de archivos y gusto musical

- **A (recomendado):** carpetas autorizadas; metadatos y reglas primero, modelo local para casos ambiguos; vista previa, movimiento reversible, registro de cambios y nunca borrar.
- **B:** mover automáticamente sin mostrar los cambios.
- **C:** limitarse a ordenar alfabéticamente.

Las carpetas como `Musicas/looksmaxing` o `Musicas/dark rose` se usan como destinos configurados. Una canción parecida no se mueve por su nombre: se proponen coincidencias y se conserva una forma de deshacer.

### 7. Notificaciones y respuestas

- **A (recomendado):** lectura por accesibilidad cuando se pida, identificación de quién escribió y borrador visible antes de responder; permiso por acción.
- **B:** escuchar todas las notificaciones y responder automáticamente.
- **C:** no incluir notificaciones en esta fase.

Android puede impedir acciones directas según la aplicación. CORT debe decir cuándo sólo puede leer y cuándo puede responder, sin inventar que lo hizo.

### 8. Router híbrido y ausencia de internet

- **A (recomendado):** reglas → GGUF local → Gemini con consentimiento → otras API configuradas → respuesta local honesta con explicación y alternativas.
- **B:** nube primero para ahorrar RAM.
- **C:** exclusivamente local.

Los presupuestos de tokens, coste, latencia y memoria deben ser visibles. Sin internet, CORT puede responder con memoria local, herramientas y razonamiento limitado; no puede inventar el clima, el correo o el tráfico actuales.

### 9. Personalidad y voces

- **A (recomendado):** operador/compañero equilibrado, seis estilos seleccionables y voces disponibles en el motor TTS instalado.
- **B:** intentar reproducir exactamente las voces comerciales de Gemini, Siri o Alexa.
- **C:** una sola voz fija.

No se copian voces ni identidades comerciales. La naturalidad depende del motor TTS del dispositivo y debe medirse con latencia real.

### 10. Alarmas, rutinas, frases y acompañamiento diario

- **A (recomendado):** catálogo local de alarmas con nombre, hora, días, etiquetas e instrucciones largas; intents nativos cuando sean suficientes y programación propia sólo con el permiso correspondiente. Añadir frases motivadoras con fuente y preferencia personal, leídas al despertar o antes de dormir cuando la alarma o rutina lo solicite.
- **B:** alarmas simples sin nombres ni instrucciones, y frases generadas por la nube cada mañana.
- **C:** alarmas actuales sin catálogo, frases ni rutinas.

Ejemplos que debe aceptar la SPEC:

- «Alarma a las 6:00 AM, despertarse para ir al ambulatorio Apamates 1».
- «Alarma a las 9:00 PM, ir a dormir para despertar temprano e ir al centro a comprar ropa».
- «Buenos días, ¿qué frase me ayudará hoy?».
- «Buenas noches, lee una frase de Kafka, Platón o Aristóteles».

Las frases deben tener autor, obra o fuente y trazabilidad. Kafka requiere revisar derechos y traducción; Platón y Aristóteles ofrecen textos en dominio público, pero la traducción concreta también debe tener licencia clara.

## Qué significa 1.0 estable

No se declara por tener el código terminado. Se declara cuando:

1. Las diez decisiones están registradas y cada criterio de aceptación tiene prueba.
2. Las suites de PC, Web, puente y Android pasan.
3. La instalación conserva datos y firma, y el APK incluye motor, oído y cara.
4. El A16 prueba GGUF, voz, segundo plano, overlay, alarmas, música y respuesta sin internet.
5. No se borran archivos ni se envían secretos en las pruebas de organización.
6. Los fallos conocidos tienen impacto y workaround escritos; no hay un P0 abierto.

## Fuera de alcance por defecto

- Root, modificaciones del sistema o suplantar a Gemini.
- Clonar voces comerciales.
- Mover o borrar archivos sin autorización y vista previa.
- Escuchar pantalla, notificaciones o audio de forma permanente sin una acción explícita.
- Afirmar que una función funciona en el teléfono sin medirla allí.

## Respuesta

Elegir una letra por punto, por ejemplo: `1A, 2A, 3A, 4A, 5A, 6A, 7A, 8A, 9A, 10A`.
