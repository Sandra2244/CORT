package dev.sandra.cort.movil;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.NetworkCapabilities;
import android.os.StatFs;
import java.io.File;
import java.util.List;

/**
 * El cerebro que se baja solo (F20e). La dueña lo pidió sin rodeos: «el gguf
 * integrado que se descargará por defecto al conectarse a internet». Aquí vive la
 * **decisión**; la descarga en sí es la misma `Bajada` de siempre con `Range`,
 * `.part` y SHA-256, metida en `ServicioBajada` para que sobreviva a que se cierre
 * la ventana.
 *
 * Cuatro guardas, y las cuatro se pueden leer en la pantalla del Almacén:
 *
 * 1. **Red sin medir.** `NET_CAPABILITY_NOT_METERED`, o sea la Wi-Fi de la casa. Con
 *    datos del teléfono no se sueltan cientos de megas: la misma regla que Android
 *    pide para `WorkManager` y que aquí se escribe a mano porque no hay AndroidX.
 * 2. **Elegir el que cabe, no el que presume.** El catálogo de `assets/cerebros.json`
 *    está ordenado de menor a mayor, así que el primero que pasa la puerta de RAM es
 *    el que se baja. Medido con los números del catálogo, el 0,5B q4_K_M pide
 *    983 MB libres y son 491 400 032 bytes; el 1,5B q2_K pide 1 506 MB.
 * 3. **El hueco en disco.** `StatFs` sobre la carpeta del almacén: hace falta el
 *    archivo **más un margen** (el `.part` y el destino conviven un instante cuando
 *    se renombra, y Samsung no avisa de un disco lleno).
 * 4. **Una sola vez.** Si ya hay cualquier GGUF bajado —porque ella lo bajó a mano o
 *    porque esto ya lo hizo— no se descarga nada: la lista del almacén es suya y
 *    duplicarla sería llenarle el teléfono.
 *
 * Lo que se dice con número y no con promesa: a los 40 KB/s medidos en su casa la
 * vez del APK, los 491 MB del 0,5B son unos 3 h 20 min de bajada continua. Por eso
 * el interruptor viene **apagado por defecto** y el costo está escrito junto a él.
 */
public final class AutoCerebro {

    /** Las preferencias de la app entera, no las del cerebro (`CerebroLocal`). */
    public static final String PREFERENCIAS = "cort";

    /** El interruptor que escribe la pantalla. Apagado hasta que ella lo encienda. */
    public static final String CLAVE = "cerebro_automatico";

    /** La última decisión que se tomó, para que la pantalla la diga en vez de callar. */
    public static final String CLAVE_MOTIVO = "cerebro_auto_motivo";

    private AutoCerebro() {
    }

    public static boolean quiere(Context contexto) {
        return contexto.getSharedPreferences(PREFERENCIAS, Context.MODE_PRIVATE)
                .getBoolean(CLAVE, false);
    }

    public static void pon(Context contexto, boolean on) {
        contexto.getSharedPreferences(PREFERENCIAS, Context.MODE_PRIVATE)
                .edit().putBoolean(CLAVE, on).apply();
    }

    /** Lo que se contableó la última vez, en español, para pintarlo tal cual. */
    public static String motivo(Context contexto) {
        return contexto.getSharedPreferences(PREFERENCIAS, Context.MODE_PRIVATE)
                .getString(CLAVE_MOTIVO, "sin comprobar todavía");
    }

    private static void anota(Context contexto, String dicho) {
        contexto.getSharedPreferences(PREFERENCIAS, Context.MODE_PRIVATE)
                .edit().putString(CLAVE_MOTIVO, dicho).apply();
    }

    /** La red activa ¿no es medida? Sin `ConnectivityManager` o sin red, la respuesta es no. */
    public static boolean redSinLimite(Context contexto) {
        ConnectivityManager red = (ConnectivityManager)
                contexto.getSystemService(Context.CONNECTIVITY_SERVICE);
        if (red == null) {
            return false;
        }
        NetworkCapabilities capacidades =
                red.getNetworkCapabilities(red.getActiveNetwork());
        if (capacidades == null) {
            return false;
        }
        return capacidades.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED);
    }

    /** Bytes libres en el sitio donde caen los cerebros, con `StatFs` y sin adivinar. */
    public static long huecoLibre(Context contexto) {
        File carbajo = CerebroLocal.carbajo(contexto);
        File mide = carbajo;
        // `StatFs` necesita un camino que exista: si el almacén todavía no se creó,
        // se mide el padre, que está en el mismo volumen.
        if (!mide.isDirectory() && mide.getParentFile() != null) {
            mide = mide.getParentFile();
        }
        try {
            return new StatFs(mide.getAbsolutePath()).getAvailableBytes();
        } catch (RuntimeException raro) {
            return 0L;      // sin medida no se arriesga una descarga de cientos de MB
        }
    }

    /**
     * El candidato: el **primero** del catálogo que no esté en disco y que quepa en
     * la RAM libre de ahora. `null` si no hay nada que bajar (o si nada cabe).
     */
    public static CerebroLocal.Ficha elige(Context contexto) {
        CerebroLocal cerebro = new CerebroLocal(contexto);
        List<CerebroLocal.Ficha> catalogo = CerebroLocal.catalogo(contexto);
        for (CerebroLocal.Ficha f : catalogo) {
            if (CerebroLocal.archivoDe(contexto, f.archivo).isFile()) {
                continue;                  // ya está: no se paga dos veces
            }
            if (!cerebro.cabe(f.bytes)) {
                continue;                  // la puerta de RAM, la misma que usa el Almacén
            }
            if (f.bytes + 64L * 1024 * 1024 > huecoLibre(contexto)) {
                continue;                  // el disco tampoco deja
            }
            return f;
        }
        return null;
    }

    /**
     * La comprobación entera, dicha con palabras y devolviendo si se arrancó algo.
     * Se llama con una actividad en primer plano (abrir CORT, o la pantalla del
     * Almacén) porque `startForegroundService` desde atrás está prohibido en Android 14.
     */
    public static boolean revisa(Context contexto) {
        if (!quiere(contexto)) {
            anota(contexto, "el interruptor está apagado: nada se baja solo");
            return false;
        }
        if (new CerebroLocal(contexto).tieneAlguno()) {
            anota(contexto, "ya hay un cerebro en el teléfono: no se baja otro");
            return false;
        }
        if (!CerebroLocal.hayLibreria()) {
            anota(contexto, "este APK salió sin la librería del motor: bajar un GGUF "
                    + "no serviría de nada");
            return false;
        }
        if (ServicioBajada.enCurso(contexto)) {
            // Antes que la red: si algo se está bajando, éso es lo que hay que decir,
            // aunque acabe de cambiar el tipo de conexión.
            anota(contexto, "ya hay una bajada en curso: " + ServicioBajada.texto(contexto));
            return false;
        }
        if (!redSinLimite(contexto)) {
            anota(contexto, "la red activa es medida (datos del teléfono) o no hay red: "
                    + "así no se bajan cientos de megas");
            return false;
        }
        CerebroLocal.Ficha f = elige(contexto);
        if (f == null) {
            anota(contexto, "ningún cerebro cabe holgado ahora: la puerta pide el archivo "
                    + "más la reserva de contexto en RAM libre y hay "
                    + new CerebroLocal(contexto).memoriaLibre()
                    / 1024 / 1024 + " MB, y en disco "
                    + huecoLibre(contexto) / 1024 / 1024 + " MB");
            return false;
        }
        anota(contexto, "bajando " + f.nombre + " (" + Bajada.mb(f.bytes) + " MB) por "
                + "la Wi-Fi: a 40 KB/s son unos " + minutos(f.bytes) + " min; sigue "
                + "aunque cierres esta pantalla");
        ServicioBajada.arranca(contexto, f.id);
        return true;
    }

    /**
     * Los minutos que dura, con la velocidad **medida** en esta casa la vez del APK
     * (40 KB/s). No es una promesa de rapidez: es el costo dicho antes de que nadie
     * deje el teléfono enchufado esperando.
     */
    public static int minutos(long bytes) {
        return (int) (bytes / (40.0 * 1024.0 * 60.0));
    }

    /** La orden que arranca el servicio desde fuera de este archivo. */
    public static void olvidaElMotivo(Context contexto) {
        anota(contexto, "sin comprobar todavía");
    }
}
