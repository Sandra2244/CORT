package dev.sandra.cort.movil;

public final class PuertaRamTest {
    private static final long MIB = 1024L * 1024L;
    private static final long RESERVA = 200L * MIB;
    private static final int TOTAL = 17;
    private static int comprobaciones;

    public static void main(String[] args) {
        long pequeno = 415_182_688L;
        long puertaPequena = pequeno + RESERVA;
        long sueloPequeno = pequeno / 2 + RESERVA / 2;

        decision(puertaPequena, pequeno, PuertaRam.Decision.CABE, "puerta exacta");
        decision(puertaPequena - 1, pequeno, PuertaRam.Decision.INTENTAR, "un byte bajo la puerta");
        decision(puertaPequena + 1, pequeno, PuertaRam.Decision.CABE, "un byte sobre la puerta");
        decision(sueloPequeno, pequeno, PuertaRam.Decision.INTENTAR, "suelo exacto");
        decision(sueloPequeno - 1, pequeno, PuertaRam.Decision.NO_CABE, "un byte bajo el suelo");

        long impar = 1L;
        decision(RESERVA / 2, impar, PuertaRam.Decision.INTENTAR, "modelo impar en el suelo");
        decision(RESERVA, impar, PuertaRam.Decision.INTENTAR, "modelo impar bajo la puerta");
        decision(RESERVA + 1, impar, PuertaRam.Decision.CABE, "modelo impar en la puerta");

        decision(RESERVA, 0L, PuertaRam.Decision.NO_CABE, "modelo cero");
        decision(RESERVA, -1L, PuertaRam.Decision.NO_CABE, "modelo negativo");
        decision(-1L, pequeno, PuertaRam.Decision.NO_CABE, "RAM negativa");

        decision(Long.MAX_VALUE, Long.MAX_VALUE, PuertaRam.Decision.INTENTAR,
                "la puerta enorme no se desborda");
        miB(Long.MAX_VALUE, Long.MAX_VALUE / MIB + 200L, "conversion enorme sin desbordarse");

        miB(415_182_688L, 595L, "0,5B q2_K");
        miB(491_400_032L, 668L, "0,5B q4_K_M");
        miB(752_880_160L, 918L, "1,5B q2_K");
        miB(1_117_320_736L, 1265L, "1,5B q4_K_M");

        if (comprobaciones != TOTAL) {
            throw new AssertionError("faltan casos: " + comprobaciones + "/" + TOTAL);
        }
        System.out.println("RAM: " + comprobaciones + "/" + TOTAL + " comprobaciones");
    }

    private static void decision(long libre, long modelo, PuertaRam.Decision esperado, String nombre) {
        comprobaciones++;
        PuertaRam.Decision real = PuertaRam.evaluar(libre, modelo);
        if (real != esperado) {
            throw new AssertionError(nombre + ": esperaba " + esperado + ", salió " + real);
        }
    }

    private static void miB(long modelo, long esperado, String nombre) {
        comprobaciones++;
        long real = PuertaRam.puertaMiB(modelo);
        if (real != esperado) {
            throw new AssertionError(nombre + ": esperaba " + esperado + " MiB, salió " + real);
        }
    }
}
