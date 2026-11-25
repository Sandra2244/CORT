package dev.sandra.cort.movil;

import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.util.Base64;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Formato y autenticación del sobre; el adaptador Android aporta la llave. */
public final class SobreSecreto {
    public static final String ALIAS = "cort-nube-v1";
    public static final String VERSION = "v1";
    private static final int IV_BYTES = 12;
    private static final int TAG_BITS = 128;
    private static final String AES_GCM = "AES/GCM/NoPadding";
    private static final SecureRandom AZAR = new SecureRandom();

    public String cifrar(String texto, SecretKey llave) throws GeneralSecurityException {
        if (texto == null || texto.isEmpty()) {
            throw new IllegalArgumentException("falta el secreto");
        }
        byte[] iv = new byte[IV_BYTES];
        AZAR.nextBytes(iv);
        Cipher cipher = Cipher.getInstance(AES_GCM);
        cipher.init(Cipher.ENCRYPT_MODE, llave, new GCMParameterSpec(TAG_BITS, iv));
        cipher.updateAAD(VERSION.getBytes(StandardCharsets.UTF_8));
        byte[] cifrado = cipher.doFinal(texto.getBytes(StandardCharsets.UTF_8));
        return VERSION + "|" + Base64.getEncoder().encodeToString(iv) + "|"
                + Base64.getEncoder().encodeToString(cifrado);
    }

    public String descifrar(String sobre, SecretKey llave) throws GeneralSecurityException {
        if (sobre == null) return "";
        String[] partes = sobre.split("\\|", -1);
        if (partes.length != 3 || !VERSION.equals(partes[0])) {
            throw new GeneralSecurityException("formato de sobre desconocido");
        }
        byte[] iv = Base64.getDecoder().decode(partes[1]);
        byte[] cifrado = Base64.getDecoder().decode(partes[2]);
        if (iv.length != IV_BYTES || cifrado.length <= TAG_BITS / 8) {
            throw new GeneralSecurityException("sobre incompleto");
        }
        Cipher cipher = Cipher.getInstance(AES_GCM);
        cipher.init(Cipher.DECRYPT_MODE, llave, new GCMParameterSpec(TAG_BITS, iv));
        cipher.updateAAD(VERSION.getBytes(StandardCharsets.UTF_8));
        return new String(cipher.doFinal(cifrado), StandardCharsets.UTF_8);
    }
}
