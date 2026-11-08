package dev.sandra.cort.movil;

import android.content.Context;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * El carácter de CORT (F20d). La dueña lo pidió así: «que investigue, hable contigo
 * y tenga personalidad gracias a sus cerebros descargables y el GGUF integrado».
 *
 * La personalidad **no** se escribe en Java. Vive en `assets/consticion.json` por la
 * misma razón que la tabla de frases: en esta máquina no hay `javac`, así que el
 * JSON lo valida `make test` en dos segundos y el Java sólo se comprueba en el
 * runner. Cambiar el tono de CORT no puede costar una corrida de diez minutos.
 *
 * Tres decisiones que conviene tener escritas:
 *
 * 1. **Va en el `system`, nunca en el historial.** Un modelo pequeño obedece mucho
 *    mejor las instrucciones que están en el turno de sistema, y meterlas como si
 *    fueran algo que la dueña dijo sería enseñarle a imitar su voz.
 * 2. **El historial lo manda quien llama.** `CerebroLocal.preguntar` recibe los
 *    turnos de viejos a nuevos y el nativo limpia la caché antes de procesar: aquí
 *    no se guarda estado de conversación por detrás, se lee de SQLite (`Recuerdos`).
 * 3. **El tope de tokens no se sube sin medir.** `max_tokens` sigue en 120, el que
 *    ya estaba: los tokens/s de este aparato son una de las ocho medidas del ensayo
 *    físico en el A16. Subirlo «porque queda mejor» sería prometer una velocidad
 *    que nadie ha visto.
 */
public final class Consticion {

    private static final Object CERRADURA = new Object();
    private static JSONObject tabla;
    private static String aviso = "";

    private Consticion() {
    }

    /** El archivo, leído una vez por proceso. Si está roto se devuelve `null` y se dice por qué. */
    private static JSONObject tabla(Context contexto) {
        synchronized (CERRADURA) {
            if (tabla != null || !aviso.isEmpty()) {
                return tabla;
            }
            try (InputStream entrada = contexto.getAssets().open("consticion.json")) {
                byte[] buffer = new byte[entrada.available()];
                int leido = 0;
                while (leido < buffer.length) {
                    int n = entrada.read(buffer, leido, buffer.length - leido);
                    if (n <= 0) {
                        break;
                    }
                    leido += n;
                }
                tabla = new JSONObject(new String(buffer, 0, leido, StandardCharsets.UTF_8));
            } catch (IOException | org.json.JSONException roto) {
                aviso = "no pude leer mi carácter (" + roto.getMessage() + ")";
            }
            return tabla;
        }
    }

    /** Lo que salió mal leyendo el archivo, para que la pantalla lo diga y no se quede muda. */
    public static String avisoDeCarga(Context contexto) {
        tabla(contexto);
        return aviso;
    }

    private static String texto(Context contexto, String clave, String porDefecto) {
        JSONObject j = tabla(contexto);
        return j == null ? porDefecto : j.optString(clave, porDefecto);
    }

    private static String lista(Context contexto, String clave) {
        JSONObject j = tabla(contexto);
        JSONArray filas = j == null ? null : j.optJSONArray(clave);
        if (filas == null || filas.length() == 0) {
            return "";
        }
        StringBuilder junto = new StringBuilder();
        for (int i = 0; i < filas.length(); i++) {
            String fila = filas.optString(i, "").trim();
            if (fila.isEmpty()) {
                continue;
            }
            if (junto.length() > 0) {
                junto.append(' ');
            }
            junto.append(fila);
        }
        return junto.toString();
    }

    /**
     * El turno de sistema completo: quién es, cómo habla, qué no hace, el formato y
     * lo que ya sabe de ella. Es lo que `CerebroLocal.preguntar` manda como `system`.
     *
     * Si el archivo falta, cae al texto que ya estaba escrito en `CerebroLocal`:
     * un carácter que no se puede leer no puede dejar a CORT sin personalidad ni
     * sin respuesta.
     */
    public static String sistema(Context contexto, String memoria) {
        JSONObject j = tabla(contexto);
        if (j == null) {
            return CerebroLocal.sistemaCort(memoria);
        }
        StringBuilder junto = new StringBuilder();
        junto.append(texto(contexto, "quien", "")).append(' ')
             .append(texto(contexto, "tono", "")).append(' ')
             .append(lista(contexto, "rasgos")).append(' ')
             .append(lista(contexto, "limites")).append(' ')
             .append(texto(contexto, "formato", ""));
        String nombre = nombre(contexto);
        if (!nombre.isEmpty()) {
            junto.append(" La dueña se llama ").append(nombre).append('.');
        }
        if (memoria != null && !memoria.isEmpty() && !"nada todavía".equals(memoria)) {
            junto.append(" Datos que ya conoces: ").append(memoria);
        }
        return junto.toString().trim();
    }

    /**
     * Cómo se llama ella, leído de la memoria del teléfono y no del archivo: el
     * nombre por defecto del JSON es el de la dueña del repo, pero si ella enseñó
     * otro («recuerda que me llamo …») manda el que enseñó.
     */
    public static String nombre(Context contexto) {
        try {
            Recuerdos recuerdos = new Recuerdos(contexto);
            for (String clave : new String[] {"nombre", "me llamo", "soy"}) {
                String v = recuerdos.valor(clave);
                if (v != null && !v.trim().isEmpty()) {
                    return v.trim();
                }
            }
        } catch (RuntimeException sinBase) {
            // sin memoria todavía: se usa el nombre del archivo
        }
        return texto(contexto, "duena", "");
    }

    /** El saludo de la primera vez, cuando todavía no hay ni un turno guardado. */
    public static String primerSaludo(Context contexto) {
        return texto(contexto, "saludo_primero",
                "Hola, soy CORT y ya vivo en tu teléfono.");
    }

    /** El tope de la vuelta. Sale del archivo para poder cambiarlo sin recompilar el tono. */
    public static int maxTokens(Context contexto) {
        JSONObject j = tabla(contexto);
        int pedido = j == null ? 120 : j.optInt("max_tokens", 120);
        // Techo duro: por encima de 400 una vuelta en este teléfono se alarga tanto
        // que la dueña cierra la app antes de oírla. El valor real se mide en el A16.
        return Math.max(32, Math.min(400, pedido));
    }

    public static float temperatura(Context contexto) {
        JSONObject j = tabla(contexto);
        double pedido = j == null ? 0.7 : j.optDouble("temperatura", 0.7);
        return (float) Math.max(0.1, Math.min(1.2, pedido));
    }

    /** Cuántos turnos viejos viajan con la pregunta. Más turnos = más contexto = más lento. */
    public static int turnos(Context contexto) {
        JSONObject j = tabla(contexto);
        int pedido = j == null ? 8 : j.optInt("turnos", 8);
        return Math.max(2, Math.min(24, pedido));
    }

    /** La línea que la pantalla del Almacén imprime debajo del interruptor de carácter. */
    public static String resumen(Context contexto) {
        if (!avisoDeCarga(contexto).isEmpty()) {
            return avisoDeCarga(contexto);
        }
        return "carácter: " + texto(contexto, "nombre", "CORT") + " · "
                + turnos(contexto) + " turnos de memoria · tope "
                + maxTokens(contexto) + " tokens · temperatura "
                + temperatura(contexto);
    }
}
