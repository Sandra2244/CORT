package dev.sandra.cort;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.media.AudioManager;
import android.provider.AlarmClock;
import android.provider.Settings;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Las manos de CORT en el teléfono. Recibe un `Cerebro.Resultado` —una acción de
 * la lista cerrada y su resto— y hace **una** de esas cosas, todas con las
 * intenciones públicas de Android o con `AudioManager`: sin `Runtime.exec`, sin
 * shell y sin permisos peligrosos, que es la regla 6 del repo respetada en el
 * aparato y no sólo en el portátil.
 *
 * Devuelve la frase que se dice (y que `Voz` lee en voz alta), o `null` cuando
 * no supo: la cara lo aprovecha para proponer aprender, que es el lazo de Hermes
 * portado como idea y no como código.
 */
public class Acciones {
    private static final Pattern HORA = Pattern.compile("(\\d{1,2})\\s*(?::|\\.)\\s*(\\d{2})");
    private static final Pattern HORA_SOLA = Pattern.compile("(\\d{1,2})");
    private static final Pattern DURACION = Pattern.compile(
            "(\\d+)\\s*(hora|horas|minuto|minutos|min|segundo|segundos|s)");
    private static final String[] NUMEROS = {"dos", "tres", "cuatro", "cinco", "seis", "siete",
            "ocho", "nueve", "diez", "once", "doce"};
    private static final Locale ES = Locale.forLanguageTag("es-ES");

    private final Activity actividad;
    private final Recuerdos recuerdos;

    public Acciones(Activity actividad, Recuerdos recuerdos) {
        this.actividad = actividad;
        this.recuerdos = recuerdos;
    }

    public String ejecutar(Cerebro.Resultado r) {
        switch (r.accion) {
            case "hora":
            case "fecha":
            case "listar":
                return rellena(r.plantilla, r);
            case "volumen":
                return volumen(r.param);
            case "abrir":
                return abrir(r.param);
            case "alarma":
                return alarma(r.resto);
            case "cronometro":
                return cronometro(r.resto);
            case "guardar":
                return recuerdos.guardarFrase(r.resto);
            case "saber":
                return saber(r);
            case "buscar":
                return buscar(r.resto);
            case "decir":
                return vacia(r.plantilla) ? null : r.plantilla;
            default:
                return null;
        }
    }

    private static boolean vacia(String texto) {
        return texto == null || texto.trim().isEmpty();
    }

    /* ------------------------------------------------------------------ volumen */

    /**
     * `adjustStreamVolume` pide `MODIFY_AUDIO_SETTINGS`, que es un permiso
     * **normal**: se concede solo en la instalación y no sale en ningún aviso. Se
     * usa el paso (`ADJUST_RAISE`) en vez de un valor absoluto justamente para no
     * escribir el volumen de la dueña sin querer.
     */
    private String volumen(String direccion) {
        AudioManager audio = (AudioManager) actividad.getSystemService(Context.AUDIO_SERVICE);
        if (audio == null) {
            return "No encontré el control de volumen de este teléfono.";
        }
        if ("silencio".equals(direccion)) {
            audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_MUTE,
                    AudioManager.FLAG_SHOW_UI);
            return "Dejo la música en silencio.";
        }
        if ("maximo".equals(direccion)) {
            int tope = audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
            for (int i = 0; i < 25 && audio.getStreamVolume(AudioManager.STREAM_MUSIC) < tope; i++) {
                audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_RAISE, 0);
            }
            return "Volumen al máximo.";
        }
        int pasos = "subir".equals(direccion) ? 3 : "bajar".equals(direccion) ? 3 : 0;
        if (pasos == 0) {
            return null;
        }
        int subir = "subir".equals(direccion) ? AudioManager.ADJUST_RAISE
                : AudioManager.ADJUST_LOWER;
        for (int i = 0; i < pasos; i++) {
            audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, subir, AudioManager.FLAG_SHOW_UI);
        }
        return "Volumen a " + audio.getStreamVolume(AudioManager.STREAM_MUSIC) + " de "
                + audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC) + ".";
    }

    /* ------------------------------------------------------------------ abrir */

    /**
     * Abrir **lo que Android ya expone** por categoría: navegador, reloj, música,
     * mensajes, marcador, ajustes, teclado. No hay `QUERY_ALL_PACKAGES` ni lista
     * de paquetes instalados — Google castiga ese permiso y este APK no lo pide —,
     * así que «abre Spotify» no está; está «abre la música».
     */
    private String abrir(String destino) {
        Intent intento = new Intent();
        intento.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        switch (destino) {
            case "ajustes":
                intento.setAction(Settings.ACTION_SETTINGS);
                break;
            case "teclado":
                intento.setAction(Settings.ACTION_INPUT_METHOD_SETTINGS);
                break;
            case "navegador":
                intento.setAction(Intent.ACTION_MAIN);
                intento.addCategory(Intent.CATEGORY_APP_BROWSER);
                break;
            case "reloj":
                // `ACTION_SHOW_ALARMS` es de API 29; el suelo del APK es 26 y el
                // teléfono de la dueña está muy por encima, pero se comprueba
                // igual: un intento que no existe no debe tumbar la cara.
                if (android.os.Build.VERSION.SDK_INT >= 29) {
                    intento.setAction(AlarmClock.ACTION_SHOW_ALARMS);
                } else {
                    intento.setAction(Settings.ACTION_DATE_SETTINGS);
                }
                break;
            case "musica":
                intento.setAction(Intent.ACTION_MAIN);
                intento.addCategory(Intent.CATEGORY_APP_MUSIC);
                break;
            case "mensajeria":
                intento.setAction(Intent.ACTION_MAIN);
                intento.addCategory(Intent.CATEGORY_APP_MESSAGING);
                break;
            case "telefono":
                intento.setAction(Intent.ACTION_DIAL);
                break;
            default:
                return "Puedo abrir ajustes, navegador, reloj, música, mensajes, marcador y teclado.";
        }
        try {
            actividad.startActivity(intento);
            return "Abriendo " + destino + ".";
        } catch (ActivityNotFoundException noHay) {
            return "Este teléfono no trae una app para " + destino + ".";
        }
    }

    /* ------------------------------------------------------------------ tiempo */

    private String alarma(String resto) {
        int[] hm = hora(resto);
        if (hm == null) {
            // Mejor preguntar que poner una alarma a las 0:00: un fallo así en un
            // asistente se paga a las siete de la mañana.
            return null;
        }
        Intent intento = new Intent(AlarmClock.ACTION_SET_ALARM)
                .putExtra(AlarmClock.EXTRA_HOUR, hm[0])
                .putExtra(AlarmClock.EXTRA_MINUTES, hm[1])
                .putExtra(AlarmClock.EXTRA_MESSAGE, "CORT")
                .putExtra(AlarmClock.EXTRA_SKIP_UI, true)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            actividad.startActivity(intento);
            return "Alarma puesta a las " + hm[0] + ":"
                    + String.format(Locale.ROOT, "%02d", hm[1]) + ".";
        } catch (ActivityNotFoundException noHayApp) {
            return "No encontré la app de reloj de este teléfono.";
        }
    }

    private String cronometro(String resto) {
        long millis = duracionAMillis(resto);
        if (millis <= 0) {
            return null;
        }
        // `ACTION_SET_TIMER` + `EXTRA_COUNTDOWN` (milisegundos, API 14): es lo que
        // la documentación de Android define para temporizadores. `ACTION_SHOW_TIMER`
        // y `EXTRA_TIME_IN_MILLIS` **no existen** — los escribí de memoria en el
        // primer borrador y habrían costado un Run rojo, que aquí es el único
        // `javac` que hay—. Se deja la UI: ver arrancar el cronómetro es el trato.
        Intent intento = new Intent(AlarmClock.ACTION_SET_TIMER)
                .putExtra(AlarmClock.EXTRA_COUNTDOWN, millis)
                .putExtra(AlarmClock.EXTRA_MESSAGE, "CORT")
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            actividad.startActivity(intento);
            return "Cronómetro de " + resto + ".";
        } catch (ActivityNotFoundException noHayApp) {
            return "La app de reloj no me dejó abrir el cronómetro.";
        }
    }

    /* ------------------------------------------------------------------ memoria y nube */

    private String buscar(String resto) {
        Intent intento = new Intent(Intent.ACTION_WEB_SEARCH)
                .putExtra("query", resto)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            actividad.startActivity(intento);
            return "Busco «" + resto + "».";
        } catch (ActivityNotFoundException noHayBuscador) {
            return "No hay buscador en este teléfono para «" + resto + "».";
        }
    }

    private String saber(Cerebro.Resultado r) {
        String hallado = "yo".equals(r.param) ? recuerdos.quienSoy() : recuerdos.buscar(r.resto);
        if (hallado == null) {
            return null;   // la cara propone aprender, en vez de inventar
        }
        return vacia(r.plantilla) ? hallado : rellena(r.plantilla, r, hallado);
    }

    /** Sustituye los huecos de la plantilla por lo que se sabe ahora. */
    private String rellena(String plantilla, Cerebro.Resultado r) {
        return rellena(plantilla, r, null);
    }

    /**
     * Sostituye los huecos de la plantilla por lo que se sabe ahora. `valor` es
     * lo que encontro la memoria: la plantilla «Esto sé de {resto}: {valor}»
     * existe para que el tono de la frase se lea en la tabla y no enterrado en
     * el Java, que es lo que estas pruebas vigilan desde `test_apk_cerebro.py`.
     */
    private String rellena(String plantilla, Cerebro.Resultado r, String valor) {
        Calendar hoy = Calendar.getInstance();
        String salida = plantilla == null ? "" : plantilla;
        salida = salida.replace("{hora}", new SimpleDateFormat("H:mm", ES).format(hoy.getTime()));
        salida = salida.replace("{fecha}",
                new SimpleDateFormat("EEEE d 'de' MMMM", ES).format(hoy.getTime()));
        salida = salida.replace("{resto}", r.resto == null ? "" : r.resto);
        salida = salida.replace("{lista}", recuerdos.lista(8));
        salida = salida.replace("{valor}", valor == null ? "" : valor);
        return vacia(salida) ? null : salida;
    }

    /* ------------------------------------------------------------------ parseo puro */

    /** «7:30», «las 8 y media», «siete y cuarto» → {7, 30}. `null` si no hay hora. */
    public static int[] hora(String dicho) {
        if (dicho == null || dicho.trim().isEmpty()) {
            return null;
        }
        Matcher m = HORA.matcher(dicho);
        if (m.find()) {
            int h = entero(m.group(1));
            int mi = entero(m.group(2));
            return (h > 23 || mi > 59) ? null : new int[] {h, mi};
        }
        Matcher suelta = HORA_SOLA.matcher(dicho);
        if (suelta.find()) {
            int h = entero(suelta.group(1));
            return h > 23 ? null : new int[] {h, minutos(dicho)};
        }
        int h = numeroEnLetras(dicho);
        return h > 0 ? new int[] {h, minutos(dicho)} : null;
    }

    private static int minutos(String dicho) {
        return dicho.contains("media") ? 30 : dicho.contains("cuarto") ? 15 : 0;
    }

    /** «5 minutos», «30 segundos», «2 horas» → milisegundos; 0 si no se entiende. */
    public static long duracionAMillis(String dicho) {
        Matcher m = DURACION.matcher(dicho == null ? "" : dicho);
        if (!m.find()) {
            return 0L;
        }
        long n = entero(m.group(1));
        String unidad = m.group(2);
        if (unidad.startsWith("h")) {
            return n * 3600000L;
        }
        if (unidad.startsWith("m")) {
            return n * 60000L;
        }
        return n * 1000L;
    }

    private static int numeroEnLetras(String dicho) {
        for (int i = 0; i < NUMEROS.length; i++) {
            if (dicho.contains(NUMEROS[i])) {
                return i + 2;
            }
        }
        return 0;
    }

    private static int entero(String texto) {
        try {
            return Integer.parseInt(texto);
        } catch (NumberFormatException noEs) {
            return 0;
        }
    }
}
