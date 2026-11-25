package dev.sandra.cort.movil;

/** Decisión pura para poder probar la puerta sin Android ni un GGUF. */
public final class PuertaRam {
    /** Reserva estimada, no medición, para KV y búferes de cálculo. */
    public static final long RESERVA_CONTEXTO = 200L * 1024 * 1024;
    private static final long MIB = 1024L * 1024;

    public enum Decision {
        CABE,
        INTENTAR,
        NO_CABE
    }

    private PuertaRam() {
    }

    public static Decision evaluar(long libre, long modelo) {
        if (libre < 0 || modelo <= 0) {
            return Decision.NO_CABE;
        }
        long suelo = modelo / 2 + RESERVA_CONTEXTO / 2;
        if (libre < suelo) {
            return Decision.NO_CABE;
        }
        if (libre >= RESERVA_CONTEXTO && libre - RESERVA_CONTEXTO >= modelo) {
            return Decision.CABE;
        }
        return Decision.INTENTAR;
    }

    public static long puertaMiB(long modelo) {
        return modelo / MIB + RESERVA_CONTEXTO / MIB
                + (modelo % MIB + RESERVA_CONTEXTO % MIB) / MIB;
    }
}
