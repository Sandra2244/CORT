package dev.sandra.cort.movil;

import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.BatteryManager;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Los sensores del aparato (F19e). La dueña pidió «todo lo aplicado de sensores», y
 * lo primero que hace falta es no inventarse cuáles tiene: el Galaxy A16 no es el
 * teléfono de al lado, y un sensor que se anuncia y no existe es una respuesta
 * mentirosa. Aquí se pregunta al `SensorManager` y se dice lo que contestó.
 *
 * Lo que se lee y para qué:
 *
 * * **Acelerómetro** → la sacudida. «Agita para callar» es la forma de interrumpir a
 *   CORT sin buscar el botón, y no necesita ningún permiso.
 * * **Luz y proximidad** → saber si el teléfono está en el bolsillo o boca abajo.
 *   Se informan; no se usan para apagar la pantalla por su cuenta.
 * * **Batería** → nivel, temperatura y si está cargando. La temperatura sale del
 *   `ACTION_BATTERY_CHANGED`, que es la única que Android expone sin root.
 * * **Podómetro** → si el aparato lo tiene. Muchos de gama media no lo traen y se
 *   dice «no está» en vez de contar pasos con el acelerómetro y llamarlo podómetro.
 *
 * Lo que NO hace: no guarda histórico, no manda nada a la red y no pide permisos
 * (ninguno de estos sensores los necesita en Android 14; el podómetro tampoco,
 * `ACTIVITY_RECOGNITION` es para el reconocimiento de actividad, no para el contador).
 * Las lecturas viven en memoria mientras la cara está montada.
 */
public final class Sensores implements SensorEventListener {

    /** Los que se piden, en el orden en que se dicen. */
    private static final int[] TIPOS = {
            Sensor.TYPE_ACCELEROMETER, Sensor.TYPE_GYROSCOPE, Sensor.TYPE_MAGNETIC_FIELD,
            Sensor.TYPE_LIGHT, Sensor.TYPE_PROXIMITY, Sensor.TYPE_PRESSURE,
            Sensor.TYPE_AMBIENT_TEMPERATURE, Sensor.TYPE_STEP_COUNTER,
    };

    private static final String[] NOMBRES = {
            "acelerómetro", "giróscopo", "brújula", "luz", "proximidad", "presión",
            "temperatura ambiente", "podómetro",
    };

    /** Por encima de esto en la diferencia de magnitud, es una sacudida y no un temblor. */
    private static final float UMBRAL_SACUDIDA = 18.0f;
    private static final long PASO_SACUDIDA_MS = 1200L;

    private static volatile Sensores compartido;

    private final SensorManager manager;
    private final Context contexto;
    private final float[] valores = new float[TIPOS.length];
    private final boolean[] puestos = new boolean[TIPOS.length];
    private final boolean[] tiene = new boolean[TIPOS.length];
    private float ultimaMagnitud = -1f;
    private long ultimaSacudida;
    private volatile Runnable alSacudir;
    private volatile boolean escuchando;

    private Sensores(Context contexto) {
        this.contexto = contexto.getApplicationContext();
        this.manager = (SensorManager) this.contexto.getSystemService(Context.SENSOR_SERVICE);
    }

    public static Sensores compartido(Context contexto) {
        Sensores yo = compartido;
        if (yo == null) {
            synchronized (Sensores.class) {
                if (compartido == null) {
                    compartido = new Sensores(contexto);
                }
                yo = compartido;
            }
        }
        return yo;
    }

    /** Lo que se hace cuando se agita el teléfono: callar la voz, lo pone quien llama. */
    public void alSacudir(Runnable accion) {
        this.alSacudir = accion;
    }

    /**
     * Registra los que existan. `SENSOR_DELAY_UI` y no el más rápido: esto se lee
     * para informarlo y para detectar una sacudida, no para medir física, y el
     * muestreo rápido es batería que se va sin que nadie la use.
     */
    public void escucha() {
        if (escuchando || manager == null) {
            return;
        }
        for (int i = 0; i < TIPOS.length; i++) {
            Sensor sensor = manager.getDefaultSensor(TIPOS[i]);
            tiene[i] = sensor != null;
            if (sensor == null) {
                continue;
            }
            manager.registerListener(this, sensor, SensorManager.SENSOR_DELAY_UI);
        }
        escuchando = true;
    }

    public void para() {
        if (!escuchando || manager == null) {
            return;
        }
        manager.unregisterListener(this);
        escuchando = false;
        for (int i = 0; i < puestos.length; i++) {
            puestos[i] = false;
        }
    }

    @Override
    public void onSensorChanged(SensorEvent evento) {
        if (evento == null || evento.values.length == 0) {
            return;
        }
        for (int i = 0; i < TIPOS.length; i++) {
            if (evento.sensor.getType() == TIPOS[i]) {
                valores[i] = evento.values[0];
                puestos[i] = true;
                if (TIPOS[i] == Sensor.TYPE_ACCELEROMETER) {
                    miraSacudida(evento.values);
                }
                return;
            }
        }
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int precision) {
        // la precisión no cambia lo que se puede decir: se informa el valor tal cual
    }

    /**
     * La sacudida se detecta por el cambio de magnitud, no por el valor absoluto:
     * quieto sobre la mesa el acelerómetro ya marca 9,8, y ése no es un gesto.
     */
    private void miraSacudida(float[] v) {
        float magnitud = (float) Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
        float antes = ultimaMagnitud;
        ultimaMagnitud = magnitud;
        if (antes < 0f) {
            return;
        }
        long ahora = System.currentTimeMillis();
        if (Math.abs(magnitud - antes) < UMBRAL_SACUDIDA
                || ahora - ultimaSacudida < PASO_SACUDIDA_MS) {
            return;
        }
        ultimaSacudida = ahora;
        Runnable orden = alSacudir;
        if (orden != null) {
            orden.run();
        }
    }

    /* ------------------------------------------------------------------ lectura */

    /** La batería, leída en el momento: `null` en el receptor devuelve el último estado. */
    public JSONObject bateria() {
        JSONObject j = new JSONObject();
        try {
            Intent estado = contexto.registerReceiver(null,
                    new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            if (estado == null) {
                j.put("nota", "el sistema no dio el estado de la batería");
                return j;
            }
            int nivel = estado.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
            int escala = estado.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
            int temperatura = estado.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, -1);
            int enchufado = estado.getIntExtra(BatteryManager.EXTRA_PLUGGED, -1);
            j.put("porcentaje", nivel >= 0 && escala > 0 ? nivel * 100 / escala : -1);
            j.put("temperatura_c", temperatura >= 0 ? temperatura / 10.0 : -1);
            j.put("cargando", enchufado > 0);
            j.put("origen", "real");
        } catch (RuntimeException | org.json.JSONException raro) {
            try {
                j.put("nota", "no se pudo leer la batería: " + raro.getMessage());
            } catch (org.json.JSONException imposible) {
                // la clave es literal: no puede fallar
            }
        }
        return j;
    }

    /** Qué sensores tiene ESTE teléfono, dicho por el sistema y no por una ficha. */
    public JSONArray inventario() {
        JSONArray filas = new JSONArray();
        for (int i = 0; i < TIPOS.length; i++) {
            Sensor sensor = manager == null ? null : manager.getDefaultSensor(TIPOS[i]);
            JSONObject fila = new JSONObject();
            try {
                fila.put("nombre", NOMBRES[i]);
                fila.put("esta", sensor != null);
                fila.put("tipo", TIPOS[i]);
                if (sensor != null) {
                    fila.put("fabricante", sensor.getVendor());
                    fila.put("consumo_ma", sensor.getPower());
                }
            } catch (org.json.JSONException imposible) {
                // claves literales
            }
            filas.put(fila);
        }
        return filas;
    }

    /** El cuadro que viaja a la cara: valores vivos, inventario y batería. */
    public JSONObject estado() {
        JSONObject j = new JSONObject();
        try {
            j.put("type", "sensores_estado");
            j.put("origen", "real");
            j.put("escuchando", escuchando);
            JSONObject vivos = new JSONObject();
            for (int i = 0; i < TIPOS.length; i++) {
                if (puestos[i]) {
                    vivos.put(NOMBRES[i], valores[i]);
                }
            }
            j.put("valores", vivos);
            j.put("inventario", inventario());
            j.put("bateria", bateria());
            j.put("nota", "lo que no aparece en «valores» es un sensor que este teléfono "
                    + "no tiene o que aún no mandó lectura; no se inventa un cero");
        } catch (org.json.JSONException imposible) {
            // claves literales
        }
        return j;
    }

    /** La versión hablada: corta, con unidades y sin los sensores que no están. */
    public String resumen() {
        List<String> dichos = new ArrayList<>();
        JSONObject pila = bateria();
        int pct = pila.optInt("porcentaje", -1);
        if (pct >= 0) {
            dichos.add("batería al " + pct + " %"
                    + (pila.optBoolean("cargando") ? ", cargando" : ""));
        }
        double grados = pila.optDouble("temperatura_c", -1);
        if (grados >= 0) {
            dichos.add(String.format(Locale.US, "%.1f grados de batería", grados));
        }
        for (int i = 0; i < TIPOS.length; i++) {
            if (!puestos[i] || TIPOS[i] == Sensor.TYPE_ACCELEROMETER
                    || TIPOS[i] == Sensor.TYPE_GYROSCOPE
                    || TIPOS[i] == Sensor.TYPE_MAGNETIC_FIELD
                    || TIPOS[i] == Sensor.TYPE_STEP_COUNTER) {
                continue;      // los tres ejes y los pasos no se leen en voz alta enteros
            }
            dichos.add(NOMBRES[i] + ": " + numero(valores[i]));
        }
        if (puestos[7]) {
            dichos.add("pasos de hoy: " + (long) valores[7]);
        }
        if (dichos.isEmpty()) {
            return "no tengo lectura de ningún sensor todavía";
        }
        return String.join(". ", dichos) + ".";
    }

    private static String numero(float v) {
        return String.format(Locale.US, "%.1f", v);
    }
}
