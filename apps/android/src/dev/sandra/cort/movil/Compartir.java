package dev.sandra.cort.movil;

import android.app.Activity;
import android.content.Intent;

final class Compartir {
    private static final int MAX_TEXTO = 4000;

    private Compartir() {}

    static String problema(String texto) {
        if (texto == null || texto.trim().isEmpty()) return "falta el texto para compartir";
        if (texto.length() > MAX_TEXTO) return "el texto supera los 4000 caracteres";
        for (int i = 0; i < texto.length(); i++) {
            char c = texto.charAt(i);
            if (Character.isISOControl(c) && c != '\n' && c != '\r' && c != '\t') {
                return "el texto contiene caracteres de control";
            }
        }
        return null;
    }

    static boolean abrir(Activity actividad, String texto) {
        if (problema(texto) != null) return false;
        Intent intento = new Intent(Intent.ACTION_SEND);
        intento.setType("text/plain");
        intento.putExtra(Intent.EXTRA_TEXT, texto);
        try {
            actividad.startActivity(Intent.createChooser(intento, "Compartir texto confirmado con"));
            return true;
        } catch (RuntimeException sinDestino) {
            return false;
        }
    }
}
