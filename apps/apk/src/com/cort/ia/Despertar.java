package com.cort.ia;

/*
 * Lo que una alarma necesita decidir SIN tocar Android: qué hora es, qué canción
 * suena y qué nota se enseña, y **cuándo** toca el próximo disparo.
 *
 * Es Java puro a propósito, como `Elige` en F15: `Prueba7` ejecuta esto en el JDK
 * del portátil. La parte que sólo se puede medir en un teléfono —que el sistema
 * despierte a la hora, que la canción suene— vive en `Alarma.java`, y aquí no se
 * finge que esté probada.
 *
 * Las reglas del parser, escritas para poder discutirlas:
 *
 *   · la hora manda: «7:30», «a las 7 y media», «a las 8». Sin hora no hay
 *     alarma y se devuelve `null` (mejor preguntar que despertar a las 0:00);
 *   · la canción es lo que va detrás de «con» o «y suena»/«y pon»: «a las 7 con
 *     after dark»; se le quita el «la canción»/«la música» de en medio;
 *   · la nota es lo que va detrás de «para», «nota» o «que dice»: «a las 7 con
 *     after dark para el examen» → canción «after dark», nota «el examen»;
 *   · «buenos días» o «rutina» en la frase enciende la rutina de la mañana; no
 *     es una canción ni una nota y no se cuela en ninguna de las dos.
 *
 * Todo se pliega con `Elige.pliega` (minúsculas, sin tildes, sin signos), así que
 * «Canción» y «cancion» son la misma palabra también aquí.
 */
import java.text.Normalizer;
import java.util.Calendar;
import java.util.Locale;
import java.util.TimeZone;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class Despertar {

    /** Lo que se entendió de la frase. `cancion` y `nota` pueden venir vacías. */
    public static final class Plan {
        public final int hora, minuto;
        public final String cancion, nota;
        public final boolean rutina;

        Plan(int hora, int minuto, String cancion, String nota, boolean rutina) {
            this.hora = hora;
            this.minuto = minuto;
            this.cancion = cancion;
            this.nota = nota;
            this.rutina = rutina;
        }

        @Override public String toString() {
            return String.format(java.util.Locale.ROOT, "%02d:%02d", hora, minuto)
                 + (cancion.isEmpty() ? "" : " · " + cancion)
                 + (nota.isEmpty() ? "" : " · " + nota)
                 + (rutina ? " · rutina" : "");
        }
    }

    private static final Pattern DOS = Pattern.compile("\\b(\\d{1,2})\\s*[:.]\\s*(\\d{2})\\b");
    private static final Pattern Y_MEDIA = Pattern.compile("\\b(\\d{1,2})\\s+y\\s+(media|cuarto)\\b");
    private static final Pattern A_LAS = Pattern.compile("\\b(?:a\\s+las|las|a\\s+la)\\s+(\\d{1,2})\\b");
    private static final Pattern SUELTA = Pattern.compile("\\b(\\d{1,2})\\b");
    private static final Pattern NOTA = Pattern.compile("\\b(?:para|nota|que dice|diciendo)\\s+(.+)$");
    private static final Pattern CANCION = Pattern.compile(
            "\\b(?:con|y suena|y pon|y ponme|al despertar con)\\s+"
          + "(?:la cancion|la musica|el tema|una cancion|musica)?\\s*(.+)$");

    private Despertar() { }

    /** La frase, entendida; `null` si no hay hora. */
    public static Plan parte(String dicho) {
        if (dicho == null || dicho.trim().isEmpty()) return null;
        String b = pliegaConHora(dicho);
        if (b.isEmpty()) return null;

        int h = -1, m = 0, ini = -1, fin = -1;
        Matcher dos = DOS.matcher(b);
        if (dos.find()) {
            h = numero(dos.group(1), -1);
            m = numero(dos.group(2), 0);
            ini = dos.start();
            fin = dos.end();
        }
        if (h < 0) {
            Matcher media = Y_MEDIA.matcher(b);
            if (media.find()) {
                h = numero(media.group(1), -1);
                m = "media".equals(media.group(2)) ? 30 : 15;
                ini = media.start();
                fin = media.end();
            }
        }
        if (h < 0) {
            Matcher suelta = A_LAS.matcher(b);
            if (suelta.find()) {
                h = numero(suelta.group(1), -1);
                ini = suelta.start();
                fin = suelta.end();
            }
        }
        if (h < 0) {
            Matcher cualquiera = SUELTA.matcher(b);
            if (cualquiera.find()) {
                h = numero(cualquiera.group(1), -1);
                ini = cualquiera.start();
                fin = cualquiera.end();
            }
        }
        if (h < 0 || h > 23 || m > 59) return null;

        // El resto de la frase, sin la hora: ahí viven la canción y la nota.
        String resto = (b.substring(0, Math.max(0, ini)) + " " + b.substring(Math.max(0, fin))).trim();
        int corteNota = resto.length();
        String nota = "";
        Matcher n = NOTA.matcher(resto);
        if (n.find()) {
            nota = limpia(n.group(1));
            corteNota = n.start();
        }
        String cancion = "";
        Matcher c = CANCION.matcher(resto.substring(0, corteNota).trim());
        if (c.find()) {
            cancion = limpia(c.group(1));
            // «despiértame con la canción», sin nombre detrás: el `(.+)$` de la
            // expresión se come el propio relleno. Eso no es una canción, así que
            // se queda vacía y la alarma suena con su tono.
            if (cancion.matches("(?:la |el |una |un )?(?:cancion|musica|tema)")) cancion = "";
        }
        boolean rutina = b.contains("buenos dias") || b.contains("rutina");
        return new Plan(h, m, cancion, nota, rutina);
    }

    /**
     * El próximo instante en que el reloj marca esa hora, **estrictamente después**
     * de `ahora`. Si ya pasó (o es justo ahora), es mañana. La zona se pasa desde
     * fuera para que la prueba no dependa de la del portátil.
     *
     * El hueco de marzo: el último domingo a las 02:30 el reloj **no existe** (salta
     * de 02:59 a 03:00). Un despertador que suena una hora antes es peor que uno
     * que suena media hora tarde, así que la corrección va **sólo hacia adelante**:
     * si el calendario devolviera una hora anterior a la pedida, se avanza el
     * hueco. El de este JDK ya la resuelve hacia adelante (2:30 → 3:30, lo que el
     * reloj sí marca ese día) y se deja tal cual. En octubre (02:30 dos veces) la
     * hora local coincide y no hay nada que corregir.
     */
    public static long proximo(int hora, int minuto, long ahora, TimeZone zona) {
        Calendar c = Calendar.getInstance(zona == null ? TimeZone.getDefault() : zona);
        c.setTimeInMillis(ahora);
        // Dos vueltas como mucho: la de hoy y, si ya pasó, la de mañana.
        for (int intento = 0; intento < 2; intento++) {
            c.set(Calendar.HOUR_OF_DAY, hora);
            c.set(Calendar.MINUTE, minuto);
            c.set(Calendar.SECOND, 0);
            c.set(Calendar.MILLISECOND, 0);
            int pedido = hora * 60 + minuto;
            int puesto = c.get(Calendar.HOUR_OF_DAY) * 60 + c.get(Calendar.MINUTE);
            if (puesto < pedido) c.add(Calendar.MINUTE, pedido - puesto);
            if (c.getTimeInMillis() > ahora) break;
            c.add(Calendar.DAY_OF_YEAR, 1);
        }
        return c.getTimeInMillis();
    }

    /** «en 8 h 5 min» para la boca; nunca negativo. */
    public static String falta(long cuando, long ahora) {
        long min = Math.max(0, (cuando - ahora + 59_999) / 60_000);
        if (min < 60) return "en " + min + " min";
        long h = min / 60, r = min % 60;
        return "en " + h + " h" + (r == 0 ? "" : " " + r + " min");
    }

    /**
     * Como `Elige.pliega`, pero **conservando `:` y `.`**: la hora se escribe
     * «7:30» y el plegado de las canciones convierte los dos puntos en un espacio,
     * con lo que el parser se quedaría sin hora. Aquí sólo se quitan tildes,
     * mayúsculas y espacios de más.
     */
    static String pliegaConHora(String s) {
        if (s == null) return "";
        String plano = Normalizer.normalize(s.toLowerCase(Locale.ROOT), Normalizer.Form.NFD)
                .replaceAll("\\p{M}+", "")
                .replaceAll("[^a-z0-9:. ]+", " ");
        return plano.replaceAll("\\s+", " ").trim();
    }

    private static int numero(String s, int porDefecto) {
        try { return Integer.parseInt(s.trim()); }
        catch (Exception e) { return porDefecto; }
    }

    private static String limpia(String s) {
        return s == null ? "" : s.replaceAll("^[\\s,;:.-]+|[\\s,;:.-]+$", "").trim();
    }
}
