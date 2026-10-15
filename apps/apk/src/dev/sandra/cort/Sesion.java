package dev.sandra.cort;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.service.voice.VoiceInteractionSession;

/**
 * La sesión del asistente: lo que Android abre cuando la dueña pulsa la tecla de
 * asistente con la pantalla bloqueada, o hace el gesto de inicio.
 *
 * Hace **una** cosa y se termina: abre la cara de CORT pidiéndole que escuche.
 * `finish()` está escrito a propósito justo después del `startActivity` — la
 * alternativa es dejar una sesión del sistema abierta esperando texto que
 * `Reconocimiento.java` no le va a dar nunca, y eso en Android se paga con el
 * aviso de «no te he entendido» encima de la cara de CORT.
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
        Intent abrir = new Intent(getContext(), MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
                .putExtra(MainActivity.PIDE_ESCUCHAR, true);
        getContext().startActivity(abrir);
        finish();
    }
}
