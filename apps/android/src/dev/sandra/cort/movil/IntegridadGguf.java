package dev.sandra.cort.movil;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Locale;

public final class IntegridadGguf {
    private IntegridadGguf() {
    }

    public static String verificar(File archivo, long bytes, String sha256) {
        if (archivo == null || !archivo.isFile()) return "el archivo no existe";
        try (FileInputStream entrada = new FileInputStream(archivo)) {
            return verificar(entrada, bytes, sha256);
        } catch (IOException error) {
            return "no se pudo abrir el archivo: " + error.getMessage();
        }
    }

    public static String verificar(FileInputStream entrada, long bytes, String sha256) {
        if (entrada == null) return "el archivo no está abierto";
        if (bytes < 0) return "el catálogo anuncia un tamaño inválido";
        String esperada = sha256 == null ? "" : sha256.trim().toLowerCase(Locale.ROOT);
        if (!esperada.matches("[0-9a-f]{64}")) return "el catálogo no trae una SHA-256 válida";
        try {
            if (entrada.getChannel().size() != bytes) {
                return "el archivo no tiene el tamaño del catálogo";
            }
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] trozo = new byte[128 * 1024];
            int leido;
            while ((leido = entrada.read(trozo)) >= 0) digest.update(trozo, 0, leido);
            StringBuilder hex = new StringBuilder(64);
            for (byte b : digest.digest()) hex.append(String.format(Locale.ROOT, "%02x", b));
            if (!esperada.equals(hex.toString())) return "la SHA-256 del archivo no coincide";
            if (entrada.getChannel().size() != bytes) {
                return "el archivo cambió mientras se verificaba";
            }
            return "";
        } catch (IOException | NoSuchAlgorithmException error) {
            return "no se pudo verificar el archivo: " + error.getMessage();
        }
    }
}
