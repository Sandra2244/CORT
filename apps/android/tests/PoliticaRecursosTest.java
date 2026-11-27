package dev.sandra.cort.movil;

/** Fronteras de RAM, batería, calor y disco; no necesitan Android. */
public final class PoliticaRecursosTest {
    private static final long MIB = 1024L * 1024;
    private static int comprobaciones;

    public static void main(String[] args) {
        long modelo = 500L * MIB;
        PoliticaRecursos.Estado sano = estado(1200 * MIB, 600 * MIB, 80, true, 30);
        verdad(PoliticaRecursos.carga(sano, modelo, false).permitida,
                "carga manual con RAM, batería y temperatura sanas");
        verdad(PoliticaRecursos.carga(sano, modelo, true).permitida,
                "carga automática holgada");

        PoliticaRecursos.Estado justo = estado(600 * MIB, 600 * MIB, 80, true, 30);
        verdad(PoliticaRecursos.carga(justo, modelo, false).permitida,
                "la orden manual puede intentar con mmap");
        verdad(PoliticaRecursos.carga(justo, modelo, true).permitida,
                "auto también intenta con mmap cuando hay 500-600 MB libres");
        verdad(PoliticaRecursos.carga(estado(500 * MIB, 600 * MIB, 80, false, 30),
                415L * MIB, true).permitida, "el 0,5B q2_K arranca con 500 MB libres");
        falso(PoliticaRecursos.carga(estado(349 * MIB, 600 * MIB, 80, true, 30),
                modelo, false).permitida, "bajo el suelo no se carga");

        falso(PoliticaRecursos.carga(estado(1200 * MIB, 600 * MIB, 9, false, 30),
                modelo, false).permitida, "batería crítica bloquea carga manual");
        falso(PoliticaRecursos.carga(estado(1200 * MIB, 600 * MIB, 19, false, 30),
                modelo, true).permitida, "automática espera al 20 por ciento");
        falso(PoliticaRecursos.carga(estado(1200 * MIB, 600 * MIB, -1, false, 30),
                modelo, true).permitida, "sin medir batería automática no arriesga");
        falso(PoliticaRecursos.carga(estado(1200 * MIB, 600 * MIB, 80, true, 43),
                modelo, false).permitida, "43 grados bloquean inferencia");
        verdad(PoliticaRecursos.carga(estado(1200 * MIB, 600 * MIB, 80, true, 42),
                modelo, false).permitida, "42 grados es el límite inclusivo");

        verdad(PoliticaRecursos.descarga(estado(1200 * MIB, 564 * MIB, 80, true, 30),
                modelo, true).permitida, "descarga con margen exacto de 64 MiB");
        falso(PoliticaRecursos.descarga(estado(1200 * MIB, 563 * MIB, 80, true, 30),
                modelo, true).permitida, "sin margen de disco no descarga");
        verdad(PoliticaRecursos.descarga(sano, modelo, true).permitida,
                "una descarga automática sana no se rechaza");
        PoliticaRecursos.Estado sinCargar = estado(1200 * MIB, 600 * MIB, 90, false, 30);
        verdad(PoliticaRecursos.descarga(sinCargar, modelo, false).permitida,
                "la dueña puede descargar sin cargador");
        falso(PoliticaRecursos.descarga(sinCargar, modelo, true).permitida,
                "automática sólo con cargador");
        falso(PoliticaRecursos.descarga(estado(1200 * MIB, 600 * MIB, 29, true, 30),
                modelo, true).permitida, "automática espera 30 por ciento de pila");
        falso(PoliticaRecursos.descarga(estado(1200 * MIB, 600 * MIB, 80, true, 41),
                modelo, true).permitida, "automática se detiene a más de 40 grados");
        falso(PoliticaRecursos.descarga(sano, Long.MAX_VALUE, true).permitida,
                "tamaño inválido no desborda el cálculo");

        System.out.println("resultado: " + comprobaciones + "/" + comprobaciones
                + " comprobaciones de política de recursos");
    }

    private static PoliticaRecursos.Estado estado(long ram, long disco, int bateria,
                                                   boolean cargando, double temperatura) {
        return new PoliticaRecursos.Estado(ram, disco, bateria, cargando, temperatura);
    }

    private static void verdad(boolean valor, String motivo) {
        comprobaciones++;
        if (!valor) throw new AssertionError(motivo);
    }

    private static void falso(boolean valor, String motivo) {
        comprobaciones++;
        if (valor) throw new AssertionError(motivo);
    }
}
