package dev.sandra.cort.movil;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public final class IntegridadGgufTest {
    private static final String ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
    private static int comprobaciones;

    public static void main(String[] args) throws Exception {
        Path temporal = Files.createTempFile("cort-gguf-", ".bin");
        try {
            Files.write(temporal, "abc".getBytes(StandardCharsets.UTF_8));
            verdad(IntegridadGguf.verificar(temporal.toFile(), 3, ABC).isEmpty(),
                    "abc con su SHA-256 conocida");
            try (java.io.FileInputStream abierto = new java.io.FileInputStream(temporal.toFile())) {
                verdad(IntegridadGguf.verificar(abierto, 3, ABC).isEmpty(),
                        "el descriptor abierto se verifica sin reabrir la ruta");
            }
            verdad(IntegridadGguf.verificar(temporal.toFile(), 3, ABC.toUpperCase()).isEmpty(),
                    "la suma hexadecimal acepta mayúsculas");
            falso(IntegridadGguf.verificar(temporal.toFile(), 4, ABC).isEmpty(),
                    "tamaño distinto rechazado");
            falso(IntegridadGguf.verificar(temporal.toFile(), 3, "0".repeat(64)).isEmpty(),
                    "contenido distinto rechazado");
            falso(IntegridadGguf.verificar(temporal.toFile(), 3, "no-es-sha").isEmpty(),
                    "SHA mal formada rechazada");
            falso(IntegridadGguf.verificar(temporal.toFile(), 3, null).isEmpty(),
                    "ausencia de SHA rechazada");
            falso(IntegridadGguf.verificar(temporal.resolve("falta.gguf").toFile(), 3, ABC).isEmpty(),
                    "archivo ausente rechazado");
            Files.write(temporal, "abd".getBytes(StandardCharsets.UTF_8));
            falso(IntegridadGguf.verificar(temporal.toFile(), 3, ABC).isEmpty(),
                    "cambio del mismo tamaño detectado");
        } finally {
            Files.deleteIfExists(temporal);
        }
        System.out.println("resultado: " + comprobaciones + "/" + comprobaciones
                + " comprobaciones de integridad GGUF");
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
