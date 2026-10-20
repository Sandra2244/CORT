package com.cort.ia;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.service.voice.VoiceInteractionSession;

/**
 * La sesión del asistente: lo que Android abre cuando la dueña hace el gesto de
 * asistente, pulsa la tecla del auricular, o invoca al asistente con la
 * pantalla bloqueada.
 *
 * Hace **una** cosa y se termina: abre la cara de CORT pidiéndole que escuche.
 * El `finish()` justo después del `startActivity` está escrito a propósito; la
 * alternativa es dejar una sesión del sistema abierta esperando texto que
 * `Reconocimiento.java` nunca le va a dar, y eso en Android se paga con un
 * «no te he entendido» encima del holograma.
 *
 * La firma de `onShow` es la de AOSP moderno: `public void onShow(Bundle args,
 * int showFlags)`. La variante antigua con `ActivityOptions` de tercer
 * parámetro murió en Android 12. Como este APK no se puede probar en el
 * portátil, quien revisa la firma es `javac` en el pipeline: un `@Override` con
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
