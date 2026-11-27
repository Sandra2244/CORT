package dev.sandra.cort.movil;

import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.provider.Settings;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

/** Lecturas acotadas al ciclo de vida de la actividad visible. */
final class Sensores {
    interface Entrega {
        void estado(JSONObject estado);
        void pasos(JSONObject pasos);
    }

    private static final String[] TIPOS = {
            "acelerometro", "giroscopio", "magnetometro", "luz", "proximidad",
            "presion", "temperatura_ambiente", "humedad", "pasos", "detector_pasos",
            "bateria", "temperatura_bateria"
    };
    private static final String[] UNIDADES = {
            "m/s²", "rad/s", "µT", "lx", "cm", "hPa", "°C", "%", "pasos", "pasos", "%", "°C"
    };
    private static final int[] CODIGOS = {
            Sensor.TYPE_ACCELEROMETER, Sensor.TYPE_GYROSCOPE, Sensor.TYPE_MAGNETIC_FIELD,
            Sensor.TYPE_LIGHT, Sensor.TYPE_PROXIMITY, Sensor.TYPE_PRESSURE,
            Sensor.TYPE_AMBIENT_TEMPERATURE, Sensor.TYPE_RELATIVE_HUMIDITY,
            Sensor.TYPE_STEP_COUNTER, Sensor.TYPE_STEP_DETECTOR
    };
    private static final long INTERVALO_MS = 2000L;

    private final Context contexto;
    private final SensorManager gestor;
    private final Handler hilo = new Handler(Looper.getMainLooper());
    private final LinkedHashMap<String, LecturaSensor> ultimas = new LinkedHashMap<>();
    private final Map<String, Sensor> hardware = new LinkedHashMap<>();
    private final Map<String, Integer> precision = new LinkedHashMap<>();
    private final SharedPreferences preferencias;
    private Entrega entrega;

    private boolean escuchando;
    private boolean tienePasos;
    private long basePasos = -1L;
    private String fechaBase = "";

    private final SensorEventListener oyente = new SensorEventListener() {
        @Override
        public void onSensorChanged(SensorEvent evento) {
            LecturaSensor anterior = ultimas.get(nombre(evento.sensor.getType()));
            boolean acumulado = evento.sensor.getType() == Sensor.TYPE_STEP_COUNTER;
            ultimas.put(nombre(evento.sensor.getType()), LecturaSensor.medida(
                    nombre(evento.sensor.getType()), evento.sensor.getType(),
                    unidad(evento.sensor.getType()), evento.values,
                    evento.timestamp / 1_000_000L, evento.accuracy, acumulado));
            if (acumulado) {
                actualizarPasos(anterior);
            }
        }

        @Override
        public void onAccuracyChanged(Sensor sensor, int exactitud) {
            precision.put(nombre(sensor.getType()), exactitud);
        }
    };

    Sensores(Context contexto) {
        this.contexto = contexto.getApplicationContext();
        this.gestor = (SensorManager) this.contexto.getSystemService(Context.SENSOR_SERVICE);
        this.preferencias = this.contexto.getSharedPreferences("cort-sensores", Context.MODE_PRIVATE);
        this.basePasos = preferencias.getLong("pasos_base", -1L);
        this.fechaBase = preferencias.getString("pasos_fecha", "");
        if (arranqueActual() != preferencias.getLong("pasos_arranque", -1L)) {
            this.basePasos = -1L;
            this.fechaBase = "";
        }
        for (int i = 0; i < TIPOS.length; i++) {
            ultimas.put(TIPOS[i], LecturaSensor.ausente(TIPOS[i], i, UNIDADES[i]));
        }
        if (gestor != null) {
            for (int i = 0; i < CODIGOS.length; i++) {
                Sensor sensor = gestor.getDefaultSensor(CODIGOS[i]);
                hardware.put(TIPOS[i], sensor);
                if (sensor != null) {
                    precision.put(TIPOS[i], SensorManager.SENSOR_STATUS_NO_CONTACT);
                }
            }
        }
    }

    void alEntregar(Entrega entrega) {
        this.entrega = entrega;
    }

    boolean empezar(boolean incluirPasos) {
        if (gestor == null) {
            return false;
        }
        if (!escuchando) {
            for (int i = 0; i < TIPOS.length; i++) {
                ultimas.put(TIPOS[i], LecturaSensor.ausente(TIPOS[i], i, UNIDADES[i]));
            }
        }
        tienePasos = incluirPasos;
        escuchando = true;
        gestor.unregisterListener(oyente);
        for (int i = 0; i < CODIGOS.length; i++) {
            Sensor sensor = hardware.get(TIPOS[i]);
            boolean esPaso = TIPOS[i].equals("pasos") || TIPOS[i].equals("detector_pasos");
            if (sensor != null && (!esPaso || incluirPasos)) {
                gestor.registerListener(oyente, sensor, SensorManager.SENSOR_DELAY_NORMAL);
            }
        }
        hilo.removeCallbacks(latido);
        hilo.postDelayed(latido, INTERVALO_MS);
        publicarEstado();
        return true;
    }

    void apagar() {
        escuchando = false;
        tienePasos = false;
        if (gestor != null) {
            gestor.unregisterListener(oyente);
        }
        hilo.removeCallbacks(latido);
        publicarEstado();
    }

    void cerrar() {
        apagar();
        entrega = null;
    }

    boolean activo() {
        return escuchando;
    }

    boolean tienePasos() {
        return tienePasos;
    }

    JSONObject estado() {
        JSONObject raiz = cuadro("sensores_estado");
        try {
            raiz.put("escuchando", escuchando);
            raiz.put("intervalo_ms", INTERVALO_MS);
            JSONObject valores = new JSONObject();
            JSONArray inventario = new JSONArray();
            for (int i = 0; i < TIPOS.length; i++) {
                String nombre = TIPOS[i];
                LecturaSensor lectura = ultimas.get(nombre);
                Sensor sensor = hardware.get(nombre);
                boolean presente = !nombre.equals("bateria")
                        && !nombre.equals("temperatura_bateria");
                if (!presente) {
                    lectura = LecturaSensor.medida(nombre, i, UNIDADES[i],
                            bateria(nombre), SystemClock.elapsedRealtime(), 0,
                            false);
                }
                valores.put(nombre, lecturaJson(lectura, presente));
                inventario.put(inventarioJson(nombre, lectura, presente));
            }
            raiz.put("valores", valores);
            raiz.put("inventario", inventario);
            raiz.put("pasos", estadoPasos());
        } catch (Exception error) {
            try {
                raiz.put("error", "no pude preparar las lecturas: " + error.getMessage());
            } catch (JSONException imposible) {
                throw new IllegalStateException(imposible);
            }
        }
        return raiz;
    }

    JSONObject estadoPasos() {
        JSONObject raiz = cuadro("sensores_pasos");
        try {
            raiz.put("activo", escuchando && tienePasos);
            LecturaSensor lectura = ultimas.get("pasos");
            if (!tienePasos()) {
                raiz.put("estado", "inactivo");
                raiz.put("motivo", "activa Pasos para solicitar el permiso y leer el contador");
            } else if (!lectura.tieneLectura()) {
                raiz.put("estado", "sin_lectura");
                raiz.put("motivo", hardware.get("pasos") == null
                        ? "este dispositivo no tiene contador de pasos"
                        : "el contador aún no ha entregado una lectura");
            } else {
                String hoy = fechaHoy();
                long acumulado = (long) lectura.valores()[0];
                boolean sinBase = basePasos < 0L || !fechaBase.equals(hoy) || acumulado < basePasos;
                LecturaSensor.ResultadoPasos resultado = LecturaSensor.pasosDelDia(
                        acumulado, basePasos, fechaBase, hoy);
                if (resultado.reiniciarBase) {
                    basePasos = acumulado;
                    fechaBase = hoy;
                    preferencias.edit().putLong("pasos_base", basePasos)
                            .putString("pasos_fecha", fechaBase)
                            .putLong("pasos_arranque", arranqueActual()).apply();
                }
                raiz.put("estado", "listo");
                raiz.put("ambito", sinBase ? "acumulado_disponible" : "hoy");
                raiz.put("pasos", sinBase ? acumulado : acumulado - basePasos);
                raiz.put("acumulado_dispositivo", acumulado);
                raiz.put("timestamp_ms", lectura.timestampMs);
                raiz.put("origen_conteo", "sensor del dispositivo");
                if (sinBase) {
                    raiz.put("aviso", "se fijó una línea base nueva; este valor es el acumulado disponible, no el total de hoy");
                }
            }
        } catch (Exception error) {
            try {
                raiz.put("estado", "no disponible");
                raiz.put("motivo", error.getMessage());
            } catch (JSONException imposible) {
                throw new IllegalStateException(imposible);
            }
        }
        return raiz;
    }

    private final Runnable latido = new Runnable() {
        @Override
        public void run() {
            if (!escuchando) {
                return;
            }
            publicarEstado();
            hilo.postDelayed(this, INTERVALO_MS);
        }
    };

    private void actualizarPasos(LecturaSensor anterior) {
        if (entrega == null) {
            return;
        }
        LecturaSensor actual = ultimas.get("pasos");
        if (anterior == null || !anterior.tieneLectura()
                || actual.valores()[0] < anterior.valores()[0]) {
            entrega.pasos(estadoPasos());
        }
    }

    private void publicarEstado() {
        if (entrega != null) {
            entrega.estado(estado());
        }
    }

    private JSONObject lecturaJson(LecturaSensor lectura, boolean presente) {
        JSONObject j = new JSONObject();
        try {
            boolean disponible = lectura.tieneLectura();
            j.put("nombre", lectura.nombre);
            j.put("tipo", lectura.tipo);
            j.put("unidad", lectura.unidad);
            j.put("disponible", disponible);
            j.put("estado", disponible ? "leido"
                    : !presente ? "sin_lectura"
                    : hardware.get(lectura.nombre) == null ? "ausente" : "sin_lectura");
            j.put("valores", new JSONArray(lectura.valores()));
            j.put("timestamp_ms", lectura.timestampMs);
            j.put("timestamp_origen", "monotonico_desde_arranque");
            j.put("precision", presente
                    ? precision.getOrDefault(lectura.nombre, lectura.precision) : 0);
            j.put("acumulado", lectura.acumulado);
            if ("bateria".equals(lectura.nombre)) {
                j.put("cargando", estaCargando());
            }
            if (!presente && !lectura.tieneLectura()) {
                j.put("motivo", "lectura no disponible en este dispositivo");
            }
        } catch (Exception ignorado) {
        }
        return j;
    }

    private JSONObject inventarioJson(String nombre, LecturaSensor lectura, boolean presente) {
        JSONObject j = new JSONObject();
        try {
            j.put("nombre", nombre);
            j.put("unidad", lectura.unidad);
            j.put("presente", presente || hardware.get(nombre) != null);
            if (nombre.equals("pasos") || nombre.equals("detector_pasos")) {
                j.put("permiso", Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q
                        ? "ACTIVITY_RECOGNITION" : "no requerido por esta versión");
            }
            if (nombre.equals("temperatura_bateria")) {
                j.put("aviso", "es temperatura de la batería, no temperatura ambiente");
            }
        } catch (Exception ignorado) {
        }
        return j;
    }

    private boolean estaCargando() {
        Intent bateria = contexto.registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if (bateria == null) {
            return false;
        }
        int estado = bateria.getIntExtra(BatteryManager.EXTRA_STATUS, -1);
        return estado == BatteryManager.BATTERY_STATUS_CHARGING
                || estado == BatteryManager.BATTERY_STATUS_FULL;
    }

    private float[] bateria(String nombre) {
        Intent bateria = contexto.registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        float[] valores = new float[0];
        if (bateria == null) {
            return valores;
        }
        if (nombre.equals("bateria")) {
            int nivel = bateria.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
            int escala = bateria.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
            if (nivel >= 0 && escala > 0) {
                valores = new float[]{nivel * 100f / escala};
            }
        } else {
            int decimas = bateria.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, -1);
            if (decimas >= 0) {
                valores = new float[]{decimas / 10f};
            }
        }
        return valores;
    }

    private JSONObject cuadro(String tipo) {
        try {
            return new JSONObject().put("type", tipo).put("origen", "real")
                    .put("plataforma", "android");
        } catch (JSONException imposible) {
            throw new IllegalStateException(imposible);
        }
    }

    private static String nombre(int tipo) {
        for (int i = 0; i < CODIGOS.length; i++) {
            if (CODIGOS[i] == tipo) {
                return TIPOS[i];
            }
        }
        return "sensor_" + tipo;
    }

    private static String unidad(int tipo) {
        for (int i = 0; i < CODIGOS.length; i++) {
            if (CODIGOS[i] == tipo) {
                return UNIDADES[i];
            }
        }
        return "";
    }

    private long arranqueActual() {
        try {
            return Settings.Global.getInt(contexto.getContentResolver(), Settings.Global.BOOT_COUNT, -1);
        } catch (RuntimeException sinAjustes) {
            return -1L;
        }
    }

    private static String fechaHoy() {
        return new SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).format(new Date());
    }
}
