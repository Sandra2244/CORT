package dev.sandra.cort.movil;

public final class LimiteEscuchaTest {
    private static final int TOTAL = 11;
    private static int comprobaciones;

    public static void main(String[] args) {
        limite(Integer.MIN_VALUE, 20, "valor extremo negativo");
        limite(-1, 20, "valor negativo");
        limite(0, 20, "cero");
        limite(19, 20, "un segundo bajo el mínimo");
        limite(20, 20, "mínimo exacto");
        limite(21, 21, "un segundo sobre el mínimo");
        limite(30, 30, "valor intermedio");
        limite(59, 59, "un segundo bajo el máximo");
        limite(60, 60, "máximo exacto");
        limite(61, 60, "un segundo sobre el máximo");
        limite(Integer.MAX_VALUE, 60, "valor extremo positivo");

        if (comprobaciones != TOTAL) {
            throw new AssertionError("faltan casos: " + comprobaciones + "/" + TOTAL);
        }
        System.out.println("Escucha: " + comprobaciones + "/" + TOTAL + " comprobaciones");
    }

    private static void limite(int pedido, int esperado, String nombre) {
        comprobaciones++;
        int real = Motor.limitarSegundos(pedido);
        if (real != esperado) {
            throw new AssertionError(nombre + ": esperaba " + esperado + ", salió " + real);
        }
    }
}
