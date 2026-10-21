package com.cort.ia;

/*
 * Los sentidos del teléfono: lo que la ventana «02 · Entorno» enseña cuando CORT
 * vive en el aparato y no hay portátil delante.
 *
 * Por qué existe: hasta la ronda 2.1 la cara sólo sabía de CPU, RAM y disco
 * preguntándole al **PC** (`/api/status` del backend). En el teléfono, sin PC, ese
 * panel se quedaba en blanco, y de ahí salió la queja de «hay sensores que no
 * funcionan». La culpa no era de los sensores: es que el puente no tenía ni un solo
 * método de sensores —`SensorManager` no aparecía en ninguno de los 21 archivos
 * Java—, así que la cara no tenía de dónde leer.
 *
 * La regla que manda aquí, la misma que en el resto del APK: **se mide o se calla**.
 * Cada fila sale con el valor que devolvió el sistema en el último `onSensorChanged`,
 * con la antigüedad de esa lectura; si el aparato no tiene ese sensor la fila dice
 * «no lo tiene», y si lo tiene pero todavía no ha soltado ni una muestra dice «sin
 * lectura todavía». Nunca un cero disfrazado de medida, porque un `0` en luminancia
 * se lee «a oscuras» y no «no lo sé».
 *
 * Gasto: los oyentes se enganchan sólo mientras la app está en primer plano
 * (`MainActivity.onResume` / `onPause` → `enMarcha`), y con `SENSOR_DELAY_UI`, que
 * es el ritmo lento de los cinco tipos que valen la pena. Con la pantalla apagada
 * este objeto no escucha nada y no despierta a nadie.
 *
 * API: sólo lo público del SDK 34 (`SensorManager`, `Sensor`, `SensorEvent`,
 * `SensorEventListener`). Nada de `Sensor.getStringType()` (no está en la lista
 * pública que revisa `javac`) ni de matemáticas de vectores de rotación: se muestran
 * los ejes crudos, que es lo que el sistema entrega.
 */

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class Sentidos implements SensorEventListener {

    private static Sentidos unico;

    private final SensorManager sm;
    private volatile boolean escuchando;

    /**
     * Los tipos que este proyecto enseña, en el orden en que salen por pantalla.
     * `TYPE_HEART_RATE` u otros exóticos no entran: no porque no existan, sino
     * porque la cara no tiene dónde pintarlos y prometerlos sería inventar.
     */
    private static final int[] TIPOS = {
        Sensor.TYPE_ACCELEROMETER,
        Sensor.TYPE_GYROSCOPE,
        Sensor.TYPE_MAGNETIC_FIELD,
        Sensor.TYPE_PROXIMITY,
        Sensor.TYPE_LIGHT,
        Sensor.TYPE_PRESSURE,
        Sensor.TYPE_AMBIENT_TEMPERATURE,
        Sensor.TYPE_RELATIVE_HUMIDITY,
        Sensor.TYPE_GRAVITY,
        Sensor.TYPE_LINEAR_ACCELERATION,
        Sensor.TYPE_STEP_COUNTER,
    };

    private static final String[] NOMBRES = {
        "acelerometro", "giroscopio", "brujula", "proximidad", "luz",
        "presion", "temperatura", "humedad", "gravedad", "aceleracion lineal",
        "pasos",
    };

    private static final String[] UNIDADES = {
        "m/s²", "rad/s", "µT", "cm", "lx", "hPa", "°C", "%HR", "m/s²", "m/s²", "pasos",
    };

    /** La última muestra por tipo, y cuándo llegó. `null` = todavía no sé nada. */
    private final float[][] muestras = new float[TIPOS.length][];
    private final long[] nanos = new long[TIPOS.length];
    private final String[] nombres = new String[TIPOS.length];

    private Sentidos(Context c) {
        sm = (SensorManager) c.getApplicationContext()
             .getSystemService(Context.SENSOR_SERVICE);
        // Apunta qué sensores existen aunque no estén en marcha, para poder decir
        // «no lo tienes» en vez de «no lo sé».
        List<Sensor> todos = new ArrayList<>();
        try {
            if (sm != null) todos = sm.getSensorList(Sensor.TYPE_ALL);
        } catch (Exception elSistemaNoLista) {
            todos = new ArrayList<>();
        }
        for (int i = 0; i < TIPOS.length; i++) {
            for (Sensor s : todos) {
                if (s != null && s.getType() == TIPOS[i]) {
                    nombres[i] = s.getName();
                    break;
                }
            }
        }
    }

    static synchronized Sentidos de(Context c) {
        if (unico == null) unico = new Sentidos(c);
        return unico;
    }

    /* ─────────────────────────── en marcha / parado ─────────────────────────── */

    /**
     * Engancha los oyentes. Se llama desde el primer plano de `MainActivity`; si ya
     * está enganchado no vuelve a hacerlo (`registerListener` dos veces es un oyente
     * duplicado comiendo batería).
     */
    synchronized void enMarcha(boolean on) {
        if (sm == null || escuchando == on) return;
        escuchando = on;
        if (!on) {
            try { sm.unregisterListener(this); } catch (Exception yaNoEscucha) { /* da igual */ }
            return;
        }
        for (int tipo : TIPOS) {
            Sensor s = null;
            try { s = sm.getDefaultSensor(tipo); } catch (Exception eseTipoNoExiste) { s = null; }
            if (s == null) continue;                 // no lo tiene: sin oyente, sin ruido
            try {
                sm.registerListener(this, s, SensorManager.SENSOR_DELAY_UI);
            } catch (Exception elFabricanteLoNiega) {
                // Algunos fabricantes no dejan oír ciertos tipos sin permiso de app
                // de sistema. Se registra la ausencia y la cara lo dice.
            }
        }
    }

    /* ─────────────────────────── las muestras ─────────────────────────── */

    @Override
    public void onSensorChanged(SensorEvent e) {
        if (e == null || e.sensor == null) return;
        int i = lugarDe(e.sensor.getType());
        if (i < 0) return;
        muestras[i] = e.values == null ? new float[0] : e.values.clone();
        nanos[i] = e.timestamp;                      // nanosegundos desde el arranque
    }

    @Override
    public void onAccuracyChanged(Sensor s, int exactitud) {
        // La exactitud sólo interesa en la brújula, y ahí la enseña el propio dato
        // (`exacta` / `baja`), no hace falta guardarla aparte.
    }

    private static int lugarDe(int tipo) {
        for (int i = 0; i < TIPOS.length; i++) if (TIPOS[i] == tipo) return i;
        return -1;
    }

    /* ─────────────────────────── lo que ve la cara ─────────────────────────── */

    /**
     * `{"ok":true,"escuchando":true,"sensores":[{nombre,tipo,unidad,tiene,
     * tieneLectura,valores:[..],hace:"3s",exactitud:"…"}],"dice":"…"}`.
     *
     * Las claves son las que pinta `hud.js`; si aquí falta una, el sector [10] de
     * `scripts/prueba-costura.py` se pone rojo (es la lección de `bgStatus()` y de
     * `burbuja`: la cara pregunta claves y Java tiene que emitirlas).
     */
    String lectura() {
        StringBuilder v = new StringBuilder();
        int conLectura = 0, presentes = 0;
        long ahora = System.nanoTime();
        for (int i = 0; i < TIPOS.length; i++) {
            if (i > 0) v.append(',');
            boolean tiene = nombres[i] != null;
            float[] m = muestras[i];
            boolean hay = tiene && m != null && m.length > 0;
            if (tiene) presentes++;
            if (hay) conLectura++;
            v.append('{')
             .append("\"tipo\":").append(comilla(NOMBRES[i]))
             .append(",\"unidad\":").append(comilla(UNIDADES[i]))
             .append(",\"nombre\":").append(comilla(tiene ? nombres[i] : ""))
             .append(",\"tiene\":").append(tiene)
             .append(",\"tieneLectura\":").append(hay)
             .append(",\"valores\":[");
            if (hay) {
                for (int j = 0; j < m.length && j < 3; j++) {
                    if (j > 0) v.append(',');
                    v.append(numero(m[j]));
                }
            }
            v.append(']')
             .append(",\"hace\":").append(hay ? comilla(hace(ahora - nanos[i])) : "\"\"")
             .append('}');
        }
        String dice;
        if (!escuchando) {
            dice = "La app está en segundo plano: CORT no está escuchando los sensores "
                 + "para no comerte la batería. Vuelve a abrir la cara y vuelven.";
        } else if (conLectura == 0) {
            dice = presentes == 0
                 ? "Este teléfono no expone ninguno de los " + TIPOS.length + " sensores que CORT sabe leer."
                 : "Tengo " + presentes + " sensores a la vista y todavía no me ha llegado "
                   + "ninguna muestra: en algunos aparatos hay que moverlos un poco.";
        } else {
            dice = conLectura + " de " + TIPOS.length + " sensores mandando datos ahora mismo.";
        }
        return "{\"ok\":true,\"escuchando\":" + escuchando
             + ",\"sensores\":[" + v + "],\"dice\":" + comilla(dice) + "}";
    }

    /** El «hace» legible: 800 ms, 3 s, 1 min… Sin medir el reloj del sistema. */
    private static String hace(long nanosAtras) {
        double s = nanosAtras / 1_000_000_000.0;
        if (s < 0) s = 0;
        if (s < 1) return Math.round(s * 1000) + " ms";
        if (s < 60) return String.format(Locale.US, "%.0f s", s);
        if (s < 3600) return String.format(Locale.US, "%.0f min", s / 60);
        return String.format(Locale.US, "%.1f h", s / 3600);
    }

    /** `0.0098` → `0.0098`; ni notación científica ni `1.0E9` por pantalla. */
    private static String numero(float x) {
        if (Float.isNaN(x) || Float.isInfinite(x)) return "0";
        double a = Math.abs(x);
        if (a >= 1000 || a < 0.001) return String.format(Locale.US, "%.4g", x);
        return String.format(Locale.US, "%.3f", x);
    }

    private static String comilla(String s) {
        if (s == null) return "\"\"";
        StringBuilder b = new StringBuilder("\"");
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '"') b.append("\\\"");
            else if (c == '\\') b.append("\\\\");
            else if (c == '\n') b.append("\\n");
            else if (c == '\r') b.append("\\r");
            else if (c == '\t') b.append("\\t");
            else if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
            else b.append(c);
        }
        return b.append('"').toString();
    }
}
