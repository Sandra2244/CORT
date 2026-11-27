package dev.sandra.cort.movil;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

final class ReglasMedios {
    static final String REPRODUCIR = "reproducir";
    static final String PAUSAR = "pausar";
    static final String DETENER = "detener";
    static final String SIGUIENTE = "siguiente";
    static final String ANTERIOR = "anterior";

    private static final Set<String> ACCIONES = new HashSet<>(Arrays.asList(
            REPRODUCIR, PAUSAR, DETENER, SIGUIENTE, ANTERIOR));

    private ReglasMedios() {}

    static boolean permitida(String accion) {
        return accion != null && ACCIONES.contains(accion);
    }

    static boolean teclaMedia(int codigo, int accion, int repeticiones) {
        if (accion != android.view.KeyEvent.ACTION_DOWN || repeticiones != 0) return false;
        switch (codigo) {
            case android.view.KeyEvent.KEYCODE_MEDIA_PLAY:
            case android.view.KeyEvent.KEYCODE_MEDIA_PAUSE:
            case android.view.KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:
            case android.view.KeyEvent.KEYCODE_MEDIA_STOP:
            case android.view.KeyEvent.KEYCODE_MEDIA_NEXT:
            case android.view.KeyEvent.KEYCODE_MEDIA_PREVIOUS:
                return true;
            default:
                return false;
        }
    }
}
