package dev.sandra.cort.movil;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.util.Locale;

/**
 * Un GGUF bajado del catálogo, con lo que hace falta para bajarlo de verdad en una
 * casa donde la red se corta: `Range` para reanudar, un `.part` mientras dura, y
 * SHA-256 antes de que el archivo se use.
 *
 * Está aquí porque la cara del PC (F19) ofrece el botón «descargar» de su panel de
 * cerebros y ese botón no puede depender de que la dueña abra la pantalla nativa
 * `Cerebros.java`: los dos caminos tienen que prometer lo mismo. La copia de la
 * lógica está anotada como deuda en `docs/STATUS.md` — el siguiente paso es que
 * `Cerebros` y `Motor` llamen a esta, no que cada uno lleve la suya — y se dejó
 * así a propósito durante esta fase: `Cerebros.java` ya está probado en el aparato
 * de la dueña y reescribir su descarga mientras se estrena la cara nueva mezclaría
 * dos riesgos en un solo envío.
 *
 * Lo que NO hace: no elige el modelo, no escribe preferencias y no toca el motor
 * nativo. Baja bytes, los comprueba y los deja en su sitio; lo demás lo decide
 * quien lo llama.
 */
public class Bajada {

    /** Cuánto va. `texto` es una línea ya formada, para no reescribirla en cada llamada. */
    public interface AlProgreso {
        void avance(long hechos, long total, int pct, String texto);
    }

    private final File destino;
    private final File parcial;
    private volatile boolean cancelada;

    public Bajada(File destino) {
        this.destino = destino;
        this.parcial = new File(destino.getPath() + ".part");
    }

    /** El sitio donde `CerebroLocal` espera el archivo de una ficha. */
    public static Bajada de(android.content.Context contexto, CerebroLocal.Ficha ficha) {
        return new Bajada(CerebroLocal.archivoDe(contexto, ficha.archivo));
    }

    /** Descarga terminada y verificada: el `.part` ya se renombró, así que basta con mirar. */
    public boolean esta() {
        return destino.isFile();
    }

    public File archivo() {
        return destino;
    }

    /** Lo que queda a medio bajar, para saber si una descarga se puede reanudar. */
    public long reanudado() {
        return parcial.isFile() ? parcial.length() : 0L;
    }

    /** corta() deja el `.part` donde está: a la próxima se sigue de ahí. */
    public void corta() {
        cancelada = true;
    }

    /**
     * Baja la ficha entera. Bloquea — es un hilo aparte del llamador, siempre — y
     * lanza con el motivo en español cuando algo no cuadra, incluida la suma: un
     * archivo que no coincide con el SHA-256 del catálogo se borra y no se usa.
     */
    public void ejecutar(CerebroLocal.Ficha ficha, AlProgreso progreso) throws Exception {
        File directorio = parcial.getParentFile();
        if (directorio != null && !directorio.isDirectory() && !directorio.mkdirs()) {
            throw new IOException("no se pudo crear " + directorio);
        }
        long reanudado = reanudado();
        HttpURLConnection conexion = (HttpURLConnection) new URL(ficha.url).openConnection();
        try {
            conexion.setInstanceFollowRedirects(true);
            conexion.setConnectTimeout(20_000);
            conexion.setReadTimeout(60_000);
            if (reanudado > 0) {
                conexion.setRequestProperty("Range", "bytes=" + reanudado + "-");
            }
            int codigo = conexion.getResponseCode();
            boolean continua = codigo == 206 && reanudado > 0;
            if (codigo != 200 && !continua) {
                throw new IOException("HTTP " + codigo + " al pedir " + ficha.url);
            }
            // Un 200 cuando se pidió `Range` quiere decir que el servidor hizo caso
            // omiso: lo que hay en el `.part` no es el principio de este archivo.
            long base = continua ? reanudado : 0L;
            if (!continua && reanudado > 0) {
                parcial.delete();
            }

            long ofrece = conexion.getContentLengthLong();
            if (ofrece > 0 && base + ofrece != ficha.bytes) {
                throw new IOException("el servidor ofrece " + (base + ofrece)
                        + " bytes y el catálogo fija " + ficha.bytes);
            }

            MessageDigest digiero = MessageDigest.getInstance("SHA-256");
            if (base > 0) {
                sumarDesde(digiero, parcial, base);
            }

            long escrito = base;
            long antes = System.currentTimeMillis();
            long ultimoAviso = 0L;
            try (InputStream entrada = conexion.getInputStream();
                 OutputStream salida = new FileOutputStream(parcial, base > 0)) {
                byte[] trozo = new byte[64 * 1024];
                int n;
                while (!cancelada && (n = entrada.read(trozo)) > 0) {
                    salida.write(trozo, 0, n);
                    digiero.update(trozo, 0, n);
                    escrito += n;
                    long ahora = System.currentTimeMillis();
                    if (progreso != null && ahora - ultimoAviso > 500L) {
                        ultimoAviso = ahora;
                        long kbps = (escrito - base) * 1000 / Math.max(1L, ahora - antes) / 1024L;
                        progreso.avance(escrito, ficha.bytes,
                                (int) tantoPorCiento(escrito, ficha.bytes),
                                "bajando: " + mb(escrito) + " de " + mb(ficha.bytes)
                                        + " MB (" + tantoPorCiento(escrito, ficha.bytes)
                                        + " %) · " + kbps + " KB/s");
                    }
                }
            }
            if (cancelada) {
                throw new IOException("descarga cortada a " + mb(escrito) + " MB; "
                        + "queda guardada y se reanuda sola");
            }
            if (escrito != ficha.bytes) {
                throw new IOException("la conexión cortó en " + escrito + " bytes, se "
                        + "esperaban " + ficha.bytes);
            }
            String suma = hex(digiero.digest());
            if (!suma.equalsIgnoreCase(ficha.sha256)) {
                parcial.delete();
                throw new IOException("la SHA-256 no cuadra (" + recorta(suma)
                        + "… contra " + recorta(ficha.sha256) + "…): se borró");
            }
            if (!parcial.renameTo(destino)) {
                throw new IOException("verificado, pero no se pudo renombrar el archivo");
            }
            if (progreso != null) {
                progreso.avance(ficha.bytes, ficha.bytes, 100, ficha.nombre + " instalado");
            }
        } finally {
            conexion.disconnect();
        }
    }

    /**
     * Vuelve a pasar el digesto sobre lo que ya está bajado. Es leer el archivo una
     * vez más, y es el precio de no fiarse de lo que hubo antes: si el `.part` se
     * corrompió, la suma final lo dice antes de que el motor intente abrirlo.
     */
    private static void sumarDesde(MessageDigest digiero, File archivo, long hasta)
            throws IOException {
        byte[] trozo = new byte[128 * 1024];
        try (InputStream in = new FileInputStream(archivo)) {
            long leido = 0L;
            int n;
            while (leido < hasta
                   && (n = in.read(trozo, 0, (int) Math.min(trozo.length, hasta - leido))) > 0) {
                digiero.update(trozo, 0, n);
                leido += n;
            }
            if (leido != hasta) {
                throw new IOException("lo ya bajado se acortó mientras se verificaba");
            }
        }
    }

    private static String hex(byte[] bytes) {
        StringBuilder cuadro = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            cuadro.append(Character.forDigit((b >> 4) & 0xF, 16));
            cuadro.append(Character.forDigit(b & 0xF, 16));
        }
        return cuadro.toString();
    }

    private static String recorta(String hex) {
        return hex != null && hex.length() > 12 ? hex.substring(0, 12) : hex;
    }

    public static String mb(long bytes) {
        return String.format(Locale.US, "%.2f", bytes / 1024.0 / 1024.0);
    }

    public static long tantoPorCiento(long hecho, long total) {
        return total > 0 ? hecho * 100 / total : 0L;
    }
}
