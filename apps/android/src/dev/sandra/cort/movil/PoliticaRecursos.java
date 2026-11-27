package dev.sandra.cort.movil;

/** Decide con medidas actuales; no con el tamaño de parámetros ni con promesas. */
public final class PoliticaRecursos {
    public static final long MARGEN_DISCO = 64L * 1024 * 1024;
    private static final int BATERIA_CRITICA = 10;
    private static final int BATERIA_AUTO_CARGA = 20;
    private static final int BATERIA_AUTO_DESCARGA = 30;
    private static final double CALOR_CARGA = 42.0;
    private static final double CALOR_DESCARGA_AUTO = 40.0;

    private PoliticaRecursos() {
    }

    public static final class Estado {
        public final long ramLibre;
        public final long discoLibre;
        public final int bateria;
        public final boolean cargando;
        public final double temperaturaBateria;

        public Estado(long ramLibre, long discoLibre, int bateria,
                      boolean cargando, double temperaturaBateria) {
            this.ramLibre = ramLibre;
            this.discoLibre = discoLibre;
            this.bateria = bateria;
            this.cargando = cargando;
            this.temperaturaBateria = temperaturaBateria;
        }
    }

    public static final class Resultado {
        public final boolean permitida;
        public final String motivo;

        private Resultado(boolean permitida, String motivo) {
            this.permitida = permitida;
            this.motivo = motivo;
        }

        public static Resultado si() {
            return new Resultado(true, "");
        }

        public static Resultado no(String motivo) {
            return new Resultado(false, motivo);
        }
    }

    public static Resultado carga(Estado e, long modelo, boolean automatica) {
        if (modelo <= 0) return Resultado.no("el modelo no tiene un tamaño verificable");
        PuertaRam.Decision ram = PuertaRam.evaluar(e.ramLibre, modelo);
        if (ram == PuertaRam.Decision.NO_CABE) {
            return Resultado.no("RAM insuficiente: hace falta al menos la mitad del modelo "
                    + "más 100 MiB de reserva");
        }
        if (e.bateria == -1 && automatica) {
            return Resultado.no("sin medición de batería no se carga automáticamente");
        }
        int minimo = automatica ? BATERIA_AUTO_CARGA : BATERIA_CRITICA;
        if (e.bateria >= 0 && e.bateria < minimo) {
            return Resultado.no("batería al " + e.bateria + " %: hace falta al menos " + minimo + " %");
        }
        if (e.temperaturaBateria < 0 && automatica) {
            return Resultado.no("sin medición de temperatura no se carga automáticamente");
        }
        if (e.temperaturaBateria > CALOR_CARGA) {
            return Resultado.no("batería a " + e.temperaturaBateria + " °C: espera a que baje de 42 °C");
        }
        return Resultado.si();
    }

    public static Resultado descarga(Estado e, long modelo, boolean automatica) {
        if (modelo <= 0 || modelo > Long.MAX_VALUE - MARGEN_DISCO) {
            return Resultado.no("el tamaño de descarga no es verificable");
        }
        if (e.discoLibre < modelo || e.discoLibre - modelo < MARGEN_DISCO) {
            return Resultado.no("disco insuficiente: faltan el archivo y 64 MiB de margen");
        }
        if (automatica && e.bateria == -1) {
            return Resultado.no("sin medición de batería no se descarga automáticamente");
        }
        int minimo = automatica ? BATERIA_AUTO_DESCARGA : BATERIA_CRITICA;
        if (e.bateria >= 0 && e.bateria < minimo) {
            return Resultado.no("batería al " + e.bateria + " %: la descarga exige al menos " + minimo + " %");
        }
        if (automatica && !e.cargando) {
            return Resultado.no("la descarga automática espera a que el teléfono esté cargando");
        }
        if (e.temperaturaBateria < 0 && automatica) {
            return Resultado.no("sin medición de temperatura no se descarga automáticamente");
        }
        double limite = automatica ? CALOR_DESCARGA_AUTO : CALOR_CARGA;
        if (e.temperaturaBateria > limite) {
            return Resultado.no("batería a " + e.temperaturaBateria + " °C: no se descarga por encima de "
                    + limite + " °C");
        }
        return Resultado.si();
    }
}
