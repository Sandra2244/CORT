package com.cort.ia;

import android.os.Bundle;
import android.service.voice.VoiceInteractionSession;
import android.service.voice.VoiceInteractionSessionService;

/**
 * La fábrica de sesiones que Android llama cuando se invoca al asistente.
 *
 * Va en archivo aparte y no como método de `Asistente` porque así está definido
 * en AOSP: `VoiceInteractionSessionService` declara
 * `public abstract VoiceInteractionSession onNewSession(Bundle args)`, y el
 * nombre de esta clase es el que aparece en `res/xml/asistente.xml` como
 * `sessionService`. Si el nombre falta, o si al servicio no le pone permiso
 * `BIND_VOICE_INTERACTION` en el manifiesto, `VoiceInteractionServiceInfo`
 * devuelve error de parseo y CORT **no sale en la lista de asistentes** del
 * teléfono.
 */
public class Sesiones extends VoiceInteractionSessionService {

    @Override
    public VoiceInteractionSession onNewSession(Bundle args) {
        return new Sesion(getApplicationContext());
    }
}
