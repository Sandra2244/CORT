package dev.sandra.cort.movil;

public final class AvisosTest {
    private static int comprobadas;

    public static void main(String[] args) {
        paquetes();
        listener();
        textoLimitado();
        compartir();
        aprobacionExacta();
        System.out.println("AvisosTest: " + comprobadas + " comprobaciones");
    }

    private static void paquetes() {
        verdad(Avisos.paqueteValido("com.whatsapp"), "paquete válido");
        verdad(Avisos.paqueteValido("org.ejemplo.app_2"), "subrayado y dígitos válidos");
        falso(Avisos.paqueteValido(null), "paquete nulo rechazado");
        falso(Avisos.paqueteValido("whatsapp"), "paquete sin dominio rechazado");
        falso(Avisos.paqueteValido(".whatsapp"), "segmento inicial vacío rechazado");
        falso(Avisos.paqueteValido("com.whatsapp."), "segmento final vacío rechazado");
        falso(Avisos.paqueteValido("com.2whatsapp"), "segmento numérico inicial rechazado");
        falso(Avisos.paqueteValido("com.whatsapp;shell"), "inyección rechazada");
        falso(Avisos.paqueteValido("com." + repetir('a', 170)), "longitud máxima aplicada");
    }

    private static void listener() {
        String componente = "dev.sandra.cort.movil/.Avisos";
        verdad(Avisos.listenerHabilitado(componente, componente), "listener exacto habilitado");
        verdad(Avisos.listenerHabilitado("otro/.Avisos: " + componente, componente),
                "componente dentro de la lista del sistema");
        falso(Avisos.listenerHabilitado(componente + ".copia", componente), "prefijo no autoriza");
        falso(Avisos.listenerHabilitado("", componente), "lista vacía no autoriza");
        falso(Avisos.listenerHabilitado(null, componente), "lista ausente no autoriza");
        falso(Avisos.listenerHabilitado(componente, null), "componente ausente no autoriza");
    }

    private static void textoLimitado() {
        verdad("Hola mundo".equals(Avisos.textoLimitado("  Hola\n\tmundo  ", 20)),
                "espacios y controles normalizados");
        verdad("abc".equals(Avisos.textoLimitado("abcdef", 3)), "límite de caracteres");
        verdad("".equals(Avisos.textoLimitado(null, 10)), "texto ausente vacío");
        verdad("".equals(Avisos.textoLimitado("\u0000\n\t", 10)), "sólo controles vaciados");
    }

    private static void compartir() {
        verdad(Compartir.problema("Hola\nsegunda línea\tcon tab") == null,
                "saltos y tabulaciones permitidos");
        verdad(Compartir.problema("   ") != null, "texto vacío rechazado");
        verdad(Compartir.problema(null) != null, "texto nulo rechazado");
        verdad(Compartir.problema(repetir('a', 4001)) != null, "límite de compartir aplicado");
        verdad(Compartir.problema("antes\u0000después") != null,
                "carácter de control rechazado");
    }

    private static void aprobacionExacta() {
        Aprobaciones aprobaciones = new Aprobaciones("sesion-compartir");
        String token = aprobaciones.preparar("compartir", "enviar", "texto", "1", "Mensaje exacto");
        verdad(token != null, "token de compartir preparado");
        falso(aprobaciones.consumir("compartir", "enviar", "texto", "1", "Mensaje distinto", token),
                "cambiar el texto invalida la confirmación");
        falso(aprobaciones.consumir("rutinas", "enviar", "texto", "1", "Mensaje exacto", token),
                "otra capacidad no puede compartir");
        falso(aprobaciones.consumir("compartir", "enviar", "texto", "1", "Mensaje exacto", token),
                "el intento inválido consume el token");
        String segundo = aprobaciones.preparar("compartir", "enviar", "texto", "1", "Mensaje exacto");
        verdad(aprobaciones.consumir("compartir", "enviar", "texto", "1", "Mensaje exacto", segundo),
                "texto exacto permitido una vez");
        falso(aprobaciones.consumir("compartir", "enviar", "texto", "1", "Mensaje exacto", segundo),
                "reutilización rechazada");
        String revocado = aprobaciones.preparar("compartir", "enviar", "texto", "1", "Revocar");
        verdad(aprobaciones.revocar(revocado), "compartir revocable");
        falso(aprobaciones.consumir("compartir", "enviar", "texto", "1", "Revocar", revocado),
                "token revocado inutilizable");
    }

    private static String repetir(char caracter, int cantidad) {
        StringBuilder salida = new StringBuilder(cantidad);
        for (int i = 0; i < cantidad; i++) salida.append(caracter);
        return salida.toString();
    }

    private static void verdad(boolean valor, String nombre) {
        comprobadas++;
        if (!valor) throw new AssertionError(nombre);
    }

    private static void falso(boolean valor, String nombre) {
        comprobadas++;
        if (valor) throw new AssertionError(nombre);
    }
}
