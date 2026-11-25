package dev.sandra.cort.movil;

import android.content.Context;
import android.os.Bundle;
import android.service.voice.VoiceInteractionSession;

/**
 * La sesión del asistente: lo que Android abre cuando la dueña pulsa la tecla de
 * asistente con la pantalla bloqueada, o hace el gesto de inicio.
 *
 * Muestra la vista rápida sobre la app actual y termina. Si falta el permiso de
 * superposición, `VistaRapida` abre Ajustes en vez de fingir que la dibujó.
 * `finish()` evita dejar una sesión del sistema esperando texto que nunca llegará.
 *
 * La firma de `onShow` es la de AOSP main: `public void onShow(@Nullable Bundle
 * args, int showFlags)`. La versión antigua, con `ActivityOptions` de tercer
 * parámetro, murió en Android 12; el suelo de este APK es API 26 y su destino
 * medido es un Samsung A16 moderno, así que se firma la nueva. Sin teléfono
 * delante, la comprobación real la hace `javac` en el runner: un `@Override` con
 * una firma que no existe no compila.
 */
public class Sesion extends VoiceInteractionSession {

    public Sesion(Context contexto) {
        super(contexto);
    }

    @Override
    public void onShow(Bundle args, int showFlags) {
        super.onShow(args, showFlags);
        VistaRapida.mostrar(getContext());
        finish();
    }
}
