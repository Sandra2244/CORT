package dev.sandra.cort.movil;

import java.security.GeneralSecurityException;
import java.util.Base64;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;

/** Prueba el sobre real con una llave de arena; no abre AndroidKeyStore. */
public final class SecretoTest {
    private static final int TOTAL = 12;
    private static int comprobaciones;
    private static SecretKey llave;

    public static void main(String[] args) throws Exception {
        KeyGenerator generador = KeyGenerator.getInstance("AES");
        generador.init(256);
        llave = generador.generateKey();
        SobreSecreto sobre = new SobreSecreto();

        String primero = sobre.cifrar("clave-de-prueba", llave);
        String segundo = sobre.cifrar("clave-de-prueba", llave);
        igual(sobre.descifrar(primero, llave), "clave-de-prueba", "recupera el texto");
        igual(sobre.descifrar(segundo, llave), "clave-de-prueba", "recupera el segundo");
        distinto(iv(primero), iv(segundo), true, "cada cifrado usa otro IV");
        formato(primero, true, "formato versionado");
        boolean rechazo = false;
        try {
            String[] partes = primero.split("\\|", -1);
            byte[] cifrado = Base64.getDecoder().decode(partes[2]);
            cifrado[cifrado.length - 1] ^= 1;
            sobre.descifrar(partes[0] + "|" + partes[1] + "|"
                    + Base64.getEncoder().encodeToString(cifrado), llave);
        } catch (GeneralSecurityException esperado) {
            rechazo = true;
        }
        igual(rechazo, true, "el tag detecta una modificación");
        rechazo = false;
        try {
            sobre.descifrar("v2|AAAA|AAAA", llave);
        } catch (GeneralSecurityException esperado) {
            rechazo = true;
        }
        igual(rechazo, true, "rechaza otra versión");
        rechazo = false;
        try {
            sobre.cifrar("", llave);
        } catch (IllegalArgumentException esperado) {
            rechazo = true;
        }
        igual(rechazo, true, "no cifra vacío");
        igual(sobre.descifrar(null, llave), "", "un sobre nulo no es una clave");
        rechazo = false;
        try {
            String[] partes = primero.split("\\|", -1);
            sobre.descifrar(partes[0] + "|" + Base64.getEncoder().encodeToString(new byte[1])
                    + "|" + partes[2], llave);
        } catch (GeneralSecurityException esperado) {
            rechazo = true;
        }
        igual(rechazo, true, "rechaza un IV de tamaño incorrecto");
        igual(SobreSecreto.ALIAS, "cort-nube-v1", "el alias de producción es cort-nube-v1");
        igual(sobre.descifrar(primero, llave).isEmpty(), false, "descifrar no modifica el sobre");
        igual(comprobaciones, TOTAL, "todas las comprobaciones");
        System.out.println("Secretos: " + TOTAL + "/" + TOTAL + " comprobaciones");
    }

    private static String iv(String sobre) {
        return sobre.split("\\|", -1)[1];
    }

    private static void formato(String sobre, boolean esperado, String nombre) {
        comprobaciones++;
        String[] partes = sobre.split("\\|", -1);
        boolean real = partes.length == 3 && "v1".equals(partes[0])
                && Base64.getDecoder().decode(partes[1]).length == 12
                && Base64.getDecoder().decode(partes[2]).length > 16;
        igual(real, esperado, nombre);
    }

    private static void igual(Object real, Object esperado, String nombre) {
        comprobaciones++;
        if (!java.util.Objects.equals(real, esperado)) {
            throw new AssertionError(nombre + ": esperaba " + esperado + ", salió " + real);
        }
    }

    private static void distinto(Object real, Object esperado, boolean distinto, String nombre) {
        igual(java.util.Objects.equals(real, esperado), !distinto, nombre);
    }
}
