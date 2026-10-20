package com.cort.ia;

import android.service.voice.VoiceInteractionService;

/**
 * La puerta por la que Android deja que CORT **sea el asistente del teléfono**.
 *
 * La clase está vacía **a propósito**: `VoiceInteractionService` es una clase
 * concreta de AOSP, no abstracta, y todo lo que el sistema pide está escrito en
 * el manifiesto —el `intent-filter` con la acción
 * `android.service.voice.VoiceInteractionService`, el permiso
 * `BIND_VOICE_INTERACTION` y la meta-datos `android.voice_interaction` que
 * apunta a `res/xml/asistente.xml`—. Inventar métodos que el sistema no llama
 * sería adorno.
 *
 * Para la dueña significa: Ajustes → Aplicaciones → Aplicación de asistencia
 * predeterminada → **CORT**. A partir de ahí, el gesto de asistente, la tecla
 * del auricular y la pantalla de bloqueo abren CORT en vez de Google.
 *
 * Lo que este archivo **no** es: un reconocedor de palabra de activación. El
 * hotword «OK Google» lo decide el servidor de Google y no se muda con este
 * APK; eso está escrito también en el manifiesto y en el README.
 */
public class Asistente extends VoiceInteractionService {
}
