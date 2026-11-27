package dev.sandra.cort.movil;

import android.view.KeyEvent;

public final class ReglasMediosTest {
    private static int comprobadas;

    public static void main(String[] args) {
        for (String accion : new String[] {"reproducir", "pausar", "detener", "siguiente", "anterior"}) {
            verdad(ReglasMedios.permitida(accion), "acción permitida: " + accion);
        }
        for (String accion : new String[] {"", "shell", "abrir", "REPRODUCIR", null}) {
            falso(ReglasMedios.permitida(accion), "acción rechazada: " + accion);
        }
        for (int tecla : new int[] {KeyEvent.KEYCODE_MEDIA_PLAY, KeyEvent.KEYCODE_MEDIA_PAUSE,
                KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE, KeyEvent.KEYCODE_MEDIA_STOP,
                KeyEvent.KEYCODE_MEDIA_NEXT, KeyEvent.KEYCODE_MEDIA_PREVIOUS}) {
            verdad(ReglasMedios.teclaMedia(tecla, KeyEvent.ACTION_DOWN, 0), "tecla permitida: " + tecla);
        }
        falso(ReglasMedios.teclaMedia(KeyEvent.KEYCODE_MEDIA_PLAY, KeyEvent.ACTION_UP, 0), "action up");
        falso(ReglasMedios.teclaMedia(KeyEvent.KEYCODE_MEDIA_PLAY, KeyEvent.ACTION_DOWN, 1), "repetición larga");
        falso(ReglasMedios.teclaMedia(KeyEvent.KEYCODE_HEADSETHOOK, KeyEvent.ACTION_DOWN, 0), "doble toque");
        falso(ReglasMedios.teclaMedia(KeyEvent.KEYCODE_VOLUME_UP, KeyEvent.ACTION_DOWN, 0), "volumen");
        falso(ReglasMedios.teclaMedia(KeyEvent.KEYCODE_MENU, KeyEvent.ACTION_DOWN, 0), "menú");
        System.out.println("ReglasMediosTest: " + comprobadas + " comprobaciones");
    }

    private static void verdad(boolean valor, String nombre) {
        comprobadas++;
        if (!valor) throw new AssertionError(nombre);
    }

    private static void falso(boolean valor, String nombre) {
        comprobadas++;
        if (valor) throw new AssertionError(nombre);
    }
}
