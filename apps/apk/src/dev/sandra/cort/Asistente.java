package dev.sandra.cort;

import android.service.voice.VoiceInteractionService;

/**
 * La puerta por la que Android deja que CORT **sea el asistente del teléfono**.
 * Antes de `v0.15.3` CORT sólo podía abrirse desde su icono; con este servicio la
 * dueña puede elegirlo en Ajustes → Aplicaciones → Aplicación de asistencia
 * predeterminada, y entonces el gesto de inicio y la tecla de asistente de la
 * pantalla bloqueada abren CORT en vez de Google.
 *
 * La clase está casi vacía **a propósito**: `VoiceInteractionService` es una
 * clase concreta de Android, no una abstracta (verificado en el fuente de AOSP
 * `core/java/android/service/voice/VoiceInteractionService.java`, rama main), y
 * todo lo que el sistema pide está en el manifiesto —el `intent-filter` con la
 * acción `android.service.voice.VoiceInteractionService`, el permiso
 * `BIND_VOICE_INTERACTION` y la meta-datos `android.voice_interaction` que apunta
 * a `res/xml/asistente.xml`—. Escribir métodos que el sistema no llama sería
 * adorno.
 *
 * Lo que este archivo **no** es: un reconocedor de voz. El contrato de AOSP
 * (`VoiceInteractionServiceInfo`) exige un `sessionService` **y** un
 * `recognitionService`, y el segundo es `Reconocimiento.java`; ahí está escrita
 * la verdad incómoda — para ser el asistente del sistema CORT tiene que oír por
 * su cuenta, y un modelo de speech propio no cabe ni en este APK ni en el
 * portátil de 1,8 GiB de la dueña (`docs/PLATFORM.md`)—. Lo que sí hace el traje
 * es abrir la cara y poner el micrófono del aparato a escuchar (`Sesion.java` →
 * `Cara.escucharAhora()`), que es el mismo `SpeechRecognizer` que funciona desde
 * `v0.15.0`.
 *
 * Consecuencia que la dueña tiene que saber antes de elegirlo: al pasar el
 * asistente a CORT se pierde el «OK Google» con la pantalla apagada, porque ese
 * hotword lo dice Google y no viaja con este APK. `supportsAssist=true` es lo que
 * queda: el gesto, la tecla y la pantalla de bloqueo.
 */
public class Asistente extends VoiceInteractionService {
}
