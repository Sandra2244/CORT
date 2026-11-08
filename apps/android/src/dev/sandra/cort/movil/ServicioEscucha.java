package dev.sandra.cort.movil;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;

/**
 * La palabra de activación en segundo plano (F19d): «hola CORT» u «oye CORT» dicho
 * a secas, con la pantalla apagada o la app en otra ventana.
 *
 * Por qué un servicio y no un hilo de la cara. La dueña lo pidió con una frase que
 * no admite réplica: quiere llamarla sin desbloquear. Un hilo dentro de `MainActivity`
 * se muere cuando One UI cierra la actividad; un `Service` en primer plano es lo único
 * que Android deja vivir, y a cambio obliga a decirlo en la bandeja — por eso el aviso
 * está puesto y no escondido.
 *
 * Las tres decisiones que recortan el gasto, escritas antes del código:
 *
 * 1. **Vosk con gramática cerrada, no el modelo abierto.** `Motor.escuchaDePalabra`
 *    decodifica contra `["hola cort", "oye cort", "[unk]"]`, que es unas cuantas
 *    veces más barato que transcribir la casa entera, y el modelo ya viaja dentro del
 *    APK (`assets/motor/`) desde `cort-v0.17.2`: no hay descarga nueva que esperar.
 * 2. **Se apaga sola en los dos casos que la hacen inútil**: cinco minutos sin que
 *    suene la palabra, y la pantalla apagada. Con la pantalla apagada nadie le habla,
 *    y dejar el micrófono abierto ahí es gastar batería por nada. El tiempo se
 *    reinicia con cada palabra oída, no con cada fotograma de audio.
 * 3. **El aviso no dice lo que se oyó.** Título fijo, `VISIBILITY_PRIVATE` y ni una
 *    palabra de la llave del enlace: una bandeja se lee con el teléfono bloqueado, y
 *    ésa es la misma razón por la que las descargas de `Bajada` no usan
 *    `DownloadManager`.
 *
 * Lo que este archivo **no** promete: que arranque sola con el teléfono encendido.
 * Android 14 no deja levantar un servicio con micrófono desde segundo plano —lo hace
 * fallar con `ForegroundServiceStartNotAllowedException`—, así que `Arranque.java` no
 * la intenta: el despertador se enciende cuando la dueña abre CORT o desde la baldosa,
 * y el botón de Ajustes queda recordando que está encendido. El costo de batería real
 * es una de las ocho medidas del ensayo físico en su A16; aquí no se inventa.
 */
public class ServicioEscucha extends Service {

    /** La orden: `extra` `ENCENDER` dice si toca vigilar o apagar. */
    public static final String ACCION = "dev.sandra.cort.movil.ESCUCHA";
    public static final String ENCENDER = "cort-encender";

    /** La preferencia que manda: sin `true` aquí, nada despierta a CORT. */
    public static final String CLAVE = "despertador";

    static final String CANAL = "cort-escucha";
    private static final int ID_AVISO = 26;

    /** Cinco minutos de casa en silencio y el micrófono se cierra solo. */
    private static final long CORTE_SILENCIO_MS = 5 * 60_000L;

    /** La cara montada ahora mismo, si lo está. Es lo que evita reabrir `MainActivity`. */
    public interface AlFrase {
        void frase(String dicho);
    }

    private static volatile AlFrase caraViva;
    private static volatile ServicioEscucha vivo;

    private final Handler principal = new Handler(Looper.getMainLooper());
    private NotificationManager avisos;
    private Appagado appagado;
    private volatile boolean enMarcha;

    /** Encender o apagar desde cualquier pantalla; `on` es la orden, no el estado actual. */
    public static void cambia(Context contexto, boolean on) {
        Intent orden = new Intent(contexto, ServicioEscucha.class);
        orden.putExtra(ENCENDER, on);
        if (on) {
            // Esto **no** se puede envolver en un `try/catch` para avisar con una
            // notificación: levantar un servicio con micrófono desde segundo plano
            // lanza `ForegroundServiceStartNotAllowedException` (una subclase de
            // `IllegalStateException`), y para cuando ese aviso se escribiera el
            // sistema ya lo habría cortado igual. Las tres llamadas del repo
            // (`MainActivity`, `Cerebros`, `Arranque`) se hacen con una actividad en
            // primer plano, que es el único momento en que Android lo deja.
            if (Build.VERSION.SDK_INT >= 26) {
                contexto.startForegroundService(orden);
            } else {
                contexto.startService(orden);
            }
            return;
        }
        contexto.startService(orden);
    }

    /** Lo que escribe Ajustes: si la dueña dejó el interruptor puesto, se intenta al abrir. */
    public static void arrancaSiTocaba(Context contexto) {
        if (!prefs(contexto).getBoolean(CLAVE, false) || vivo != null) {
            return;
        }
        cambia(contexto, true);
    }

    /** Si hay escucha montada ahora mismo, para que la pantalla diga la verdad. */
    public static boolean montada() {
        return vivo != null;
    }

    /** Lo que dejó escrito el interruptor, esté o no montado el servicio en este momento. */
    public static boolean encendida(Context contexto) {
        return prefs(contexto).getBoolean(CLAVE, false);
    }

    /** La cara que está puesta: `Nexo` o `Cara` la registran al montarse. */
    public static void registra(AlFrase cara) {
        caraViva = cara;
    }

    /** Sólo se quita a sí misma: si la cara nueva ya se registró, la vieja no la pisa. */
    public static void desregistra(AlFrase cara) {
        if (caraViva == cara) {
            caraViva = null;
        }
    }

    /** Si nadie está mirando, la frase abre la app en vez de tirarse a la basura. */
    static void entregaAlAparato(Context contexto, String dicho) {
        AlFrase cara = caraViva;
        if (cara != null) {
            cara.frase(dicho);
            return;
        }
        Intent abrir = new Intent(contexto, MainActivity.class);
        abrir.putExtra(MainActivity.PIDE_ESCUCHAR, true);
        abrir.putExtra(MainActivity.PIDE_FRASE, dicho);
        abrir.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            contexto.startActivity(abrir);
        } catch (RuntimeException nadieAbre) {
            // Con la pantalla bloqueada y sin permiso de actividad desde atrás, la
            // frase se pierde: es el caso que mide el ensayo físico, no un bug nuevo.
        }
    }

    private static SharedPreferences prefs(Context contexto) {
        return contexto.getSharedPreferences("cort", Context.MODE_PRIVATE);
    }

    /* ------------------------------------------------------------------ servicio */

    @Override
    public void onCreate() {
        super.onCreate();
        avisos = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        canal();
    }

    @Override
    public int onStartCommand(Intent intento, int flags, int arranque) {
        boolean encender = intento == null || intento.getBooleanExtra(ENCENDER, true);
        if (!encender) {
            prefs(this).edit().putBoolean(CLAVE, false).apply();
            apaga();
            return START_NOT_STICKY;
        }
        if (!prefs(this).getBoolean(CLAVE, true)) {
            prefs(this).edit().putBoolean(CLAVE, true).apply();
        }
        vivo = this;
        enMarcha = true;
        montaAviso("CORT está escuchando la palabra de activación…");
        // `startForeground` con el tipo puesto: en Android 14 sin `MICROPHONE` el
        // sistema corta el micrófono a los pocos segundos, con aviso o sin él.
        try {
            if (Build.VERSION.SDK_INT >= 29) {
                startForeground(ID_AVISO, aviso("CORT escucha «hola cort» u «oye cort»"),
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
            } else {
                startForeground(ID_AVISO, aviso("CORT escucha «hola cort» u «oye cort»"));
            }
        } catch (RuntimeException noDeja) {
            prefs(this).edit().putBoolean(CLAVE, false).apply();
            montaAviso("El teléfono no deja abrir el micrófono en segundo plano: "
                    + "abre CORT y vuelve a encenderla.");
            apaga();
            return START_NOT_STICKY;
        }
        vigilaPantalla();
        intentPreparaElOido();
        return START_STICKY;
    }

    /**
     * El oído puede estar descomprimiendo el modelo (primer arranque) o sin bajar.
     * `Motor.prepara()` es idempotente y no corta la interfaz; si al intentarlo
     * tampoco llega, el aviso dice qué falta con palabras y el servicio se cierra:
     * quedarse escuchando sin modelo es gastar batería en silencio.
     */
    private void intentPreparaElOido() {
        final Motor oido = Motor.compartido(getApplicationContext());
        oido.prepara();
        principal.post(new Runnable() {
            @Override
            public void run() {
                if (!enMarcha) {
                    return;
                }
                if (oido.listo()) {
                    arranca(oido);
                    return;
                }
                if (oido.estado() == Motor.DESCOMPRIMIENDO
                        || oido.estado() == Motor.CARGANDO
                        || oido.estado() == Motor.DESCARGANDO) {
                    principal.postDelayed(this, 2000L);   // todavía está montando
                    return;
                }
                montaAviso("Sin el modelo de español no hay palabra de activación: "
                        + "bájalo en Almacén de cerebros.");
                apaga();
            }
        });
    }

    private void arranca(Motor oido) {
        oido.escuchaDePalabra(new Motor.AlEscucha() {
            @Override
            public void palabra(String dicha) {
                respira();
                montaAviso("Te oí. Di el mandato.");
            }

            @Override
            public void frase(String dicho) {
                respira();
                montaAviso("Escuché: «" + recorta(dicho) + "»");
                entregaAlAparato(ServicioEscucha.this, dicho);
            }

            @Override
            public void nivel(float alto) {
                // El nivel lo consume la cara montada, no la bandeja: aquí se ignora a
                // propósito para no escribir quince notificaciones por frase.
            }

            @Override
            public void fallo(String motivo) {
                montaAviso("La escucha se paró: " + motivo);
                apaga();
            }
        });
        respira();
    }

    /** Reiniciar el reloj de los cinco minutos: cada cosa oída vale, cada fotograma no. */
    private void respira() {
        principal.removeCallbacks(cortePorSilencio);
        principal.postDelayed(cortePorSilencio, CORTE_SILENCIO_MS);
    }

    private final Runnable cortePorSilencio = new Runnable() {
        @Override
        public void run() {
            if (!enMarcha) {
                return;
            }
            montaAviso("Cinco minutos sin que nadie me llamara: cerré el micrófono. "
                    + "Se vuelve a abrir al encender la pantalla y decir la palabra.");
            apaga();
        }
    };

    /**
     * El receptor de la pantalla. `ACTION_SCREEN_OFF` no se puede declarar en el
     * manifiesto desde Android 8: tiene que ser dinámico, y ésa es la única razón de
     * que exista. Se apaga el servicio con la pantalla porque con la pantalla apagada
     * nadie le habla a CORT.
     */
    private void vigilaPantalla() {
        if (appagado != null) {
            return;
        }
        appagado = new Appagado();
        registerReceiver(appagado, new IntentFilter(Intent.ACTION_SCREEN_OFF));
    }

    private final class Appagado extends BroadcastReceiver {
        @Override
        public void onReceive(Context contexto, Intent orden) {
            if (!enMarcha) {
                return;
            }
            montaAviso("Pantalla apagada: cerré el micrófono para no gastar batería. "
                    + "Al encenderla y abrir CORT vuelvo a escuchar la palabra.");
            apaga();
        }
    }

    /**
     * Apagar de verdad: soltar el micrófono, quitar el receptor y el aviso, y dejar
     * morir el servicio. Se llama desde las cuatro salidas posibles (pantalla apagada,
     * silencio de cinco minutos, fallo del oído y orden de la dueña) y es la única que
     * libera `Motor`, así que no puede quedarse a medias.
     */
    private void apaga() {
        enMarcha = false;
        principal.removeCallbacks(cortePorSilencio);
        Motor.compartido(getApplicationContext()).dejaLaPalabra();
        if (appagado != null) {
            try {
                unregisterReceiver(appagado);
            } catch (IllegalArgumentException yaFuera) {
                // nunca llegó a registrarse: no hay nada que quitar
            }
            appagado = null;
        }
        vivo = null;
        try {
            stopForeground(STOP_FOREGROUND_REMOVE);
        } catch (Exception noHuboPila) {
            // `stopForeground` no lanza en este nivel, pero un fallo aquí no puede
            // dejar vivo un servicio que ya se despide.
        }
        if (avisos != null) {
            avisos.cancel(ID_AVISO);
        }
        stopSelf();
    }

    @Override
    public void onDestroy() {
        apaga();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intento) {
        return null;        // es un servicio empezado, no enlazado
    }

    /* ------------------------------------------------------------------- aviso */

    private void canal() {
        if (Build.VERSION.SDK_INT < 26 || avisos == null) {
            return;
        }
        NotificationChannel canal = new NotificationChannel(CANAL, "CORT te escucha",
                NotificationManager.IMPORTANCE_LOW);
        canal.setDescription("Mientras el micrófono está abierto por la palabra de "
                + "activación. Sin sonido de aviso.");
        canal.setShowBadge(false);
        avisos.createNotificationChannel(canal);
    }

    /** El aviso que va en la pila: `ongoing`, sin sonido y sin lo que se oyó. */
    private Notification aviso(String detalle) {
        Intent abrir = new Intent(this, MainActivity.class);
        abrir.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        Notification.Builder cuadro = new Notification.Builder(this, CANAL)
                .setSmallIcon(icono())
                .setContentTitle("CORT · palabra de activación")
                .setContentText(detalle)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setVisibility(Notification.VISIBILITY_PRIVATE)
                .setContentIntent(PendingIntent.getActivity(this, 0, abrir,
                        PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT));
        return cuadro.build();
    }

    /** Cambiar la línea del aviso sin volver a montar la pila. */
    private void montaAviso(final String detalle) {
        if (avisos == null) {
            return;
        }
        avisos.notify(ID_AVISO, aviso(detalle));
    }

    /**
     * `ic_cort_aviso` a mano: esta cadena de compilación (`aapt2` + `javac` + `d8`, sin
     * Gradle) no genera `R.java`, así que no existe un `R.drawable.ic_cort_aviso` que
     * escribir. Es el mismo truco documentado de `Arranque.java`.
     */
    private int icono() {
        int numero = getResources().getIdentifier("ic_cort_aviso", "drawable", getPackageName());
        return numero != 0 ? numero : android.R.drawable.btn_microphone;
    }

    /** Una frase oída cabe en una línea de la bandeja; el resto no se escribe. */
    private static String recorta(String dicho) {
        String limpio = dicho == null ? "" : dicho.trim();
        return limpio.length() <= 48 ? limpio : limpio.substring(0, 48) + "…";
    }
}
