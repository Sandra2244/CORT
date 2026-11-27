package dev.sandra.cort.movil;

import android.app.ActivityOptions;
import android.content.Context;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.service.voice.VoiceInteractionSession;

/** La sesión que Android conserva mientras CORT atiende una invocación del asistente. */
public class Sesion extends VoiceInteractionSession {
    private static volatile Sesion actual;

    private final Handler principal = new Handler(Looper.getMainLooper());
    private final Runnable escuchaDeRespaldo = () -> {
        if (actual == this && VistaRapida.visible(this) && !Reconocimiento.activa()) {
            VistaRapida.escuchar(this);
        }
    };
    private boolean vistaPedida;
    private boolean duplicada;

    public Sesion(Context contexto) {
        super(contexto);
        synchronized (Sesion.class) {
            if (actual != null && actual != this) {
                duplicada = true;
                principal.post(this::finish);
            } else {
                actual = this;
            }
        }
    }

    @Override
    public void onShow(Bundle args, int showFlags) {
        super.onShow(args, showFlags);
        mostrar();
    }

    // Android 26–28 conserva esta firma, ausente del SDK actual.
    @Deprecated
    public void onShow(Bundle args, ActivityOptions options) {
        mostrar();
    }

    private void mostrar() {
        principal.removeCallbacks(escuchaDeRespaldo);
        if (duplicada || actual != this || vistaPedida) return;
        vistaPedida = VistaRapida.mostrar(getContext(), this, this::finish);
        if (vistaPedida) {
            principal.postDelayed(escuchaDeRespaldo, 900);
        } else {
            finish();
        }
    }

    @Override
    public void onHide() {
        super.onHide();
        principal.removeCallbacks(escuchaDeRespaldo);
        if (actual == this) Reconocimiento.cancelar();
        finish();
    }

    @Override
    public void onDestroy() {
        principal.removeCallbacks(escuchaDeRespaldo);
        if (actual == this) Reconocimiento.cancelar();
        VistaRapida.cerrar(this);
        synchronized (Sesion.class) {
            if (actual == this) actual = null;
        }
        super.onDestroy();
    }

    static boolean activa() {
        return actual != null;
    }
}
