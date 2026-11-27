package dev.sandra.cort.movil;

import java.util.Objects;

/** Conversión pura de una lectura; no toca Android ni guarda preferencias. */
final class LecturaSensor {
    final String nombre;
    final int tipo;
    final String unidad;
    final boolean disponible;
    final float[] valores;
    final long timestampMs;
    final int precision;
    final boolean acumulado;

    private LecturaSensor(String nombre, int tipo, String unidad, boolean disponible,
                          float[] valores, long timestampMs, int precision, boolean acumulado) {
        this.nombre = nombre;
        this.tipo = tipo;
        this.unidad = unidad;
        this.disponible = disponible;
        this.valores = valores == null ? new float[0] : valores.clone();
        this.timestampMs = timestampMs;
        this.precision = precision;
        this.acumulado = acumulado;
    }

    static LecturaSensor ausente(String nombre, int tipo, String unidad) {
        return new LecturaSensor(nombre, tipo, unidad, false, null, 0L,
                android.hardware.SensorManager.SENSOR_STATUS_NO_CONTACT, false);
    }

    static LecturaSensor medida(String nombre, int tipo, String unidad, float[] valores,
                                long timestampMs, int precision, boolean acumulado) {
        return new LecturaSensor(nombre, tipo, unidad, true, valores, timestampMs,
                precision, acumulado);
    }

    float[] valores() {
        return valores.clone();
    }

    boolean tieneLectura() {
        return disponible && valores.length > 0 && timestampMs > 0L;
    }

    static ResultadoPasos pasosDelDia(long acumulado, long base, String fechaBase, String hoy) {
        boolean invalido = acumulado < 0L;
        if (invalido) {
            acumulado = 0L;
        }
        if (invalido || base < 0L || !Objects.equals(fechaBase, hoy) || acumulado < base) {
            return new ResultadoPasos(false, acumulado, true);
        }
        return new ResultadoPasos(true, acumulado - base, false);
    }

    static final class ResultadoPasos {
        final boolean esHoy;
        final long valor;
        final boolean reiniciarBase;

        ResultadoPasos(boolean esHoy, long valor, boolean reiniciarBase) {
            this.esHoy = esHoy;
            this.valor = valor;
            this.reiniciarBase = reiniciarBase;
        }
    }
}
