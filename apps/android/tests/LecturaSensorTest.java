package dev.sandra.cort.movil;

import java.util.Objects;

public final class LecturaSensorTest {
    private static final int TOTAL = 14;
    private static int comprobaciones;

    public static void main(String[] args) {
        vectores();
        ausencia();
        pasos();

        if (comprobaciones != TOTAL) {
            throw new AssertionError("faltan casos: " + comprobaciones + "/" + TOTAL);
        }
        System.out.println("Lecturas de sensores: " + comprobaciones + "/" + TOTAL + " comprobaciones");
    }

    private static void vectores() {
        float[] original = {1f, 2f, 3f};
        LecturaSensor lectura = LecturaSensor.medida("acelerómetro", 1, "m/s²",
                original, 1234L, 3, false);
        original[0] = 99f;
        igual(lectura.valores()[0], 1f, "el vector no conserva el valor recibido");
        float[] copia = lectura.valores();
        copia[1] = 99f;
        igual(lectura.valores()[1], 2f, "el vector se entrega por copia");
        igual(lectura.valores().length, 3, "se conservan los tres ejes");
        igual(lectura.timestampMs, 1234L, "se conserva el timestamp");
        igual(lectura.precision, 3, "se conserva la precisión");
        igual(lectura.unidad, "m/s²", "se conserva la unidad");
    }

    private static void ausencia() {
        LecturaSensor ausente = LecturaSensor.ausente("podómetro", 19, "pasos");
        if (ausente.disponible || ausente.tieneLectura()) {
            throw new AssertionError("un sensor ausente no puede producir lectura");
        }
        comprobaciones++;
        if (ausente.valores().length != 0) {
            throw new AssertionError("un sensor ausente no inventa un vector cero");
        }
        comprobaciones++;
    }

    private static void pasos() {
        LecturaSensor.ResultadoPasos sinBase = LecturaSensor.pasosDelDia(
                500L, -1L, "", "2026-11-27");
        si(!sinBase.esHoy && sinBase.valor == 500L && sinBase.reiniciarBase,
                "sin línea base se muestra acumulado disponible, no pasos de hoy");
        sinBase = LecturaSensor.pasosDelDia(900L, 500L, "2026-11-26", "2026-11-27");
        si(!sinBase.esHoy && sinBase.valor == 900L && sinBase.reiniciarBase,
                "el cambio de día reinicia la línea base sin inventar el día completo");
        sinBase = LecturaSensor.pasosDelDia(1200L, 500L, "2026-11-27", "2026-11-27");
        si(sinBase.esHoy && sinBase.valor == 700L && !sinBase.reiniciarBase,
                "con la misma fecha se resta la línea base");
        sinBase = LecturaSensor.pasosDelDia(300L, 500L, "2026-11-27", "2026-11-27");
        si(!sinBase.esHoy && sinBase.valor == 300L && sinBase.reiniciarBase,
                "un reinicio del contador no produce pasos negativos");
        sinBase = LecturaSensor.pasosDelDia(-4L, 0L, "2026-11-27", "2026-11-27");
        si(!sinBase.esHoy && sinBase.valor == 0L && sinBase.reiniciarBase,
                "un acumulado inválido se acota a cero");
        si(sinBase.valor >= 0L, "el acumulado disponible nunca es negativo");
    }

    private static void si(boolean condicion, String nombre) {
        comprobaciones++;
        if (!condicion) {
            throw new AssertionError(nombre);
        }
    }

    private static void igual(float real, float esperado, String nombre) {
        si(Float.compare(real, esperado) == 0, nombre);
    }

    private static void igual(long real, long esperado, String nombre) {
        si(real == esperado, nombre);
    }

    private static void igual(String real, String esperado, String nombre) {
        si(Objects.equals(real, esperado), nombre);
    }
}
