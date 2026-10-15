package dev.sandra.cort;

import android.os.Bundle;
import android.service.voice.VoiceInteractionSession;
import android.service.voice.VoiceInteractionSessionService;

/**
 * La fábrica de sesiones que Android llama cuando se invoca al asistente.
 *
 * Es un archivo aparte y no un método de `Asistente` porque **así está definido
 * en el fuente de AOSP**: `VoiceInteractionSessionService` declara
 * `public abstract VoiceInteractionSession onNewSession(Bundle args)`, y el
 * nombre de esta clase es el que va escrito en `res/xml/asistente.xml` como
 * `sessionService`. Si ese nombre falta o no tiene permiso
 * `BIND_VOICE_INTERACTION` en el manifiesto, el parser del sistema
 * (`VoiceInteractionServiceInfo`) devuelve un error de parseo y CORT **no aparece
 * en la lista de asistentes** del teléfono — sin ninguna pantalla que lo diga —.
 */
public class Sesiones extends VoiceInteractionSessionService {

    @Override
    public VoiceInteractionSession onNewSession(Bundle args) {
        return new Sesion(getApplicationContext());
    }
}
