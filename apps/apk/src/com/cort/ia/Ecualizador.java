package com.cort.ia;

/*
 * El ecualizador de VERDAD del teléfono (`android.media.audiofx.Equalizer`), en su
 * propio fichero.
 *
 * Vive aparte por dos motivos, y los dos son de método, no de estética:
 *
 *   1. `scripts/prueba-mente.sh` compila `Cerebro`, `Razon`, `Mente`, `Nube` y
 *      `Ollama` con gemelos de papel que simulan Android. Este fichero NO se copia
 *      allí: el ecualizador sólo se puede medir en un teléfono de verdad, y fingir
 *      que el JDK lo ha probado sería justo el tipo de verde que la dueña no quiere.
 *   2. El ecualizador va pegado a una sesión de audio concreta. Si se queda vivo
 *      cuando el `MediaPlayer` se suelta, en algunos fabricantes se oye un chasquido
 *      y en otros no suena nada. Por eso `Reproductor` lo engancha en `onPrepared`
 *      (la sesión ya existe) y lo suelta en `onDestroy`.
 *
 * Lo que se elige es un preset del aparato, no una curva inventada: `Elige.preset`
 * traduce «clásica»/«graves» al nombre que este teléfono trae, y si no lo trae se
 * dice con la lista de los que sí tiene. Nada de prometer un «modo rock» que suene
 * igual que «Normal».
 */

import android.media.audiofx.Equalizer;

import java.util.ArrayList;
import java.util.List;

public final class Ecualizador {

    private static Equalizer eq;
    private static int sesion = -1;
    /** El preset que la dueña pidió, para volver a ponerlo en la siguiente canción. */
    private static String puesto = "";

    private Ecualizador() { }

    /**
     * Engancha el ecualizador a la sesión del `MediaPlayer`. Idempotente: si ya está
     * en esa sesión no crea otro (dos `Equalizer` sobre la misma sesión es un error
     * de Android). Devuelve el JSON del estado, para que el puente pueda contarlo.
     */
    static synchronized String engancha(int sesionAudio) {
        if (sesionAudio <= 0) return error("el reproductor no tiene sesión de audio todavía");
        if (eq != null && sesion == sesionAudio) return estadoJson();
        suelta();
        try {
            eq = new Equalizer(0, sesionAudio);
            eq.setEnabled(true);
            sesion = sesionAudio;
            if (!puesto.isEmpty()) {
                // La canción nueva abre una sesión nueva: se vuelve a poner lo que
                // ella eligió, sin volver a pedírselo.
                String otra = aplica(puesto);
                if (otra != null && otra.contains("\"ok\":false")) puesto = "";
            }
            return estadoJson();
        } catch (Throwable esteAparatoNoDeja) {
            suelta();
            return error("este teléfono no me deja ecualizar: " + esteAparatoNoDeja.getMessage());
        }
    }

    /** Suelta el efecto antes de que el `MediaPlayer` desaparezca. */
    static synchronized void suelta() {
        if (eq != null) {
            try { eq.setEnabled(false); } catch (Throwable yaNo) { /* se va igual */ }
            try { eq.release(); } catch (Throwable yaNo) { /* se va igual */ }
        }
        eq = null;
        sesion = -1;
    }

    /**
     * Pone un preset por su nombre dicho. Devuelve JSON con `ok`, `puesto`, la lista
     * de presets del aparato y una frase para la boca. Si no hay música sonando, lo
     * dice en vez de fingir que cambió el sonido.
     */
    static synchronized String aplica(String dicho) {
        if (eq == null) {
            return error("primero pon algo de música: el ecualizador va pegado al reproductor");
        }
        List<String> nombres = nombresPreset();
        int i = Elige.preset(dicho, nombres);
        if (i < 0) {
            return "{\"ok\":false,\"dice\":\"" + Reproductor.esc(
                    "Este teléfono no trae el preset «" + dicho + "»."
                    + (nombres.isEmpty() ? "" : " Tiene: " + String.join(", ", nombres) + "."))
                    + "\",\"presets\":" + listaJson(nombres) + "}";
        }
        try {
            eq.usePreset((short) i);
            puesto = nombres.get(i);
            return "{\"ok\":true,\"puesto\":\"" + Reproductor.esc(puesto)
                    + "\",\"dice\":\"" + Reproductor.esc("Ecualizador en «" + puesto + "».")
                    + "\",\"presets\":" + listaJson(nombres) + "}";
        } catch (Throwable noDeja) {
            return error("el teléfono no aplicó «" + nombres.get(i) + "»: " + noDeja.getMessage());
        }
    }

    /** El estado actual, con las bandas que este aparato tenga de verdad. */
    static synchronized String estadoJson() {
        if (eq == null) {
            return "{\"ok\":false,\"puesto\":\"\",\"activo\":false,"
                 + "\"dice\":\"El ecualizador se enciende con la música.\"}";
        }
        List<String> nombres = nombresPreset();
        StringBuilder bandas = new StringBuilder("[");
        try {
            short cuantas = eq.getNumberOfBands();
            for (short b = 0; b < cuantas; b++) {
                if (b > 0) bandas.append(',');
                bandas.append("{\"hz\":").append(eq.getCenterFreq(b) / 1000)
                      .append(",\"nivel\":").append(eq.getBandLevel(b)).append('}');
            }
        } catch (Throwable sinBandas) {
            // Un fabricante puede negar las bandas; el preset sigue siendo útil.
        }
        bandas.append(']');
        String activo = puesto.isEmpty() ? "sin preset" : puesto;
        return "{\"ok\":true,\"activo\":true,\"puesto\":\"" + Reproductor.esc(puesto)
             + "\",\"dice\":\"" + Reproductor.esc("Ecualizador " + activo + ".")
             + "\",\"presets\":" + listaJson(nombres) + ",\"bandas\":" + bandas + "}";
    }

    private static List<String> nombresPreset() {
        List<String> nombres = new ArrayList<>();
        if (eq == null) return nombres;
        try {
            short cuantos = eq.getNumberOfPresets();
            for (short i = 0; i < cuantos; i++) nombres.add(eq.getPresetName(i));
        } catch (Throwable sinPresets) {
            // Se queda la lista vacía: «no tiene presets» es una respuesta honesta.
        }
        return nombres;
    }

    private static String listaJson(List<String> nombres) {
        StringBuilder s = new StringBuilder("[");
        for (int i = 0; i < nombres.size(); i++) {
            if (i > 0) s.append(',');
            s.append('"').append(Reproductor.esc(nombres.get(i))).append('"');
        }
        return s.append(']').toString();
    }

    private static String error(String dice) {
        return "{\"ok\":false,\"dice\":\"" + Reproductor.esc(dice) + "\"}";
    }
}
