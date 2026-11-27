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

import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Vigilia de «hola CORT» u «oye CORT» con la pantalla encendida. El micrófono
 * pertenece a un foreground service, se cierra a los cinco minutos de silencio
 * o al apagar la pantalla y siempre puede detenerse desde la notificación.
 *
 * La notificación es fija y privada: nunca contiene una transcripción. El
 * estado observable es el mismo que consumen la interfaz y la baldosa.
 */
public class ServicioEscucha extends Service {

    public static final String ACCION = "dev.sandra.cort.movil.ESCUCHA";
    public static final String ENCENDER = "cort-encender";
    public static final String DETENER = "cort-detener";
    public static final String CLAVE = "despertador";

    static final String CANAL = "cort-escucha";
    private static final int ID_AVISO = 26;
    private static final long CORTE_SILENCIO_MS = 5 * 60_000L;

    interface AlFrase {
        void frase(String dicho);
    }

    interface AlDetener {
        void detener();
    }

    private static volatile AlFrase caraViva;
    private static final CopyOnWriteArrayList<AlDetener> DETENERES =
            new CopyOnWriteArrayList<>();
    private static volatile ServicioEscucha vivo;

    private final Handler principal = new Handler(Looper.getMainLooper());
    private NotificationManager avisos;
    private Appagado appagado;
    private FocoAudio foco;
    private Motor oido;
    private volatile boolean enMarcha;

    public static void cambia(Context contexto, boolean on) {
        Intent orden = new Intent(contexto, ServicioEscucha.class);
        orden.putExtra(ENCENDER, on);
        if (on) {
            if (Build.VERSION.SDK_INT >= 26) {
                contexto.startForegroundService(orden);
            } else {
                contexto.startService(orden);
            }
            return;
        }
        ServicioEscucha actual = vivo;
        if (actual != null) {
            actual.detenerYa();
            return;
        }
        prefs(contexto).edit().putBoolean(CLAVE, false).apply();
        EscuchaEstadoGlobal.pon(EscuchaEstado.DETENIDO, "escucha detenida");
        contexto.startService(orden);
    }

    public static void arrancaSiTocaba(Context contexto) {
        if (!prefs(contexto).getBoolean(CLAVE, false) || vivo != null) {
            return;
        }
        cambia(contexto, true);
    }

    public static boolean montada() {
        return vivo != null;
    }

    public static boolean encendida(Context contexto) {
        return prefs(contexto).getBoolean(CLAVE, false);
    }

    public static void registra(AlFrase cara) {
        caraViva = cara;
    }

    public static void desregistra(AlFrase cara) {
        if (caraViva == cara) {
            caraViva = null;
        }
    }

    public static void registraDetener(AlDetener oyente) {
        if (oyente != null && !DETENERES.contains(oyente)) {
            DETENERES.add(oyente);
        }
    }

    public static void desregistraDetener(AlDetener oyente) {
        DETENERES.remove(oyente);
    }

    static boolean entregaAlAparato(Context contexto, String dicho) {
        AlFrase cara = caraViva;
        if (cara != null) {
            try {
                cara.frase(dicho);
                return true;
            } catch (RuntimeException fallo) {
                return false;
            }
        }
        Intent abrir = new Intent(contexto, MainActivity.class);
        abrir.putExtra(MainActivity.PIDE_ESCUCHAR, true);
        abrir.putExtra(MainActivity.PIDE_FRASE, dicho);
        abrir.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            contexto.startActivity(abrir);
            return true;
        } catch (RuntimeException nadieAbre) {
            return false;
        }
    }

    private static SharedPreferences prefs(Context contexto) {
        return contexto.getSharedPreferences("cort", Context.MODE_PRIVATE);
    }

    @Override
    public void onCreate() {
        super.onCreate();
        avisos = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        foco = FocoAudio.compartido(this);
        canal();
    }

    @Override
    public int onStartCommand(Intent intento, int flags, int arranque) {
        boolean encender = intento == null || intento.getBooleanExtra(ENCENDER, true);
        if (!encender || (intento != null && DETENER.equals(intento.getAction()))) {
            detenerYa();
            return START_NOT_STICKY;
        }
        if (checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)
                != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            prefs(this).edit().putBoolean(CLAVE, false).apply();
            EscuchaEstadoGlobal.pon(EscuchaEstado.ERROR, "falta el permiso de micrófono");
            stopSelf();
            return START_NOT_STICKY;
        }
        if (enMarcha && vivo == this) {
            return START_STICKY;
        }
        prefs(this).edit().putBoolean(CLAVE, true).apply();
        vivo = this;
        enMarcha = true;
        EscuchaEstadoGlobal.pon(EscuchaEstado.PREPARANDO, "preparando el oído local");
        try {
            if (Build.VERSION.SDK_INT >= 29) {
                startForeground(ID_AVISO, aviso(), ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
            } else {
                startForeground(ID_AVISO, aviso());
            }
        } catch (RuntimeException noDeja) {
            prefs(this).edit().putBoolean(CLAVE, false).apply();
            cierra(EscuchaEstado.ERROR, "Android no permitió abrir el micrófono en segundo plano");
            return START_NOT_STICKY;
        }
        if (!foco.retener(this, this::perdioFoco)) {
            prefs(this).edit().putBoolean(CLAVE, false).apply();
            cierra(EscuchaEstado.ERROR, "otra app retiene el audio del teléfono");
            return START_NOT_STICKY;
        }
        vigilaPantalla();
        intentPreparaElOido();
        return START_STICKY;
    }

    private void perdioFoco() {
        cierra(EscuchaEstado.APAGADO, "otra app tomó el audio; no se reanudó automáticamente");
    }

    private void intentPreparaElOido() {
        oido = Motor.compartido(getApplicationContext());
        oido.prepara();
        principal.post(new Runnable() {
            @Override
            public void run() {
                if (!enMarcha) {
                    return;
                }
                if (oido.listo()) {
                    if (EscuchaEstadoGlobal.estado() != EscuchaEstado.ESCUCHANDO_PALABRA
                            || !oido.estaEnDespertar()) {
                        arranca(oido);
                    }
                    return;
                }
                if (oido.estado() == Motor.DESCOMPRIMIENDO
                        || oido.estado() == Motor.CARGANDO
                        || oido.estado() == Motor.DESCARGANDO) {
                    principal.postDelayed(this, 2000L);
                    return;
                }
                cierra(EscuchaEstado.ERROR,
                        "sin el modelo de español no hay palabra de activación");
            }
        });
    }

    private void arranca(Motor motor) {
        EscuchaEstadoGlobal.pon(EscuchaEstado.ESCUCHANDO_PALABRA, "vigilando «hola CORT» u «oye CORT»");
        motor.escuchaDePalabra(new Motor.AlEscucha() {
            @Override
            public void palabra(String dicha) {
                respira();
                EscuchaEstadoGlobal.pon(EscuchaEstado.ESCUCHANDO_MANDATO, "di el mandato");
            }

            @Override
            public void frase(String dicho) {
                respira();
                EscuchaEstadoGlobal.pon(EscuchaEstado.PROCESANDO, "mandato recibido");
                if (!entregaAlAparato(ServicioEscucha.this, dicho)) {
                    EscuchaEstadoGlobal.pon(EscuchaEstado.ESCUCHANDO_PALABRA,
                            "Android no permitió abrir la conversación");
                }
            }

            @Override
            public void nivel(float alto) {
                // La animación la consume la cara; la bandeja no se actualiza por frame.
            }

            @Override
            public void fallo(String motivo) {
                cierra(EscuchaEstado.ERROR, motivo);
            }
        });
        respira();
    }

    private void respira() {
        principal.removeCallbacks(cortePorSilencio);
        principal.postDelayed(cortePorSilencio, CORTE_SILENCIO_MS);
    }

    private final Runnable cortePorSilencio = new Runnable() {
        @Override
        public void run() {
            if (enMarcha) {
                cierra(EscuchaEstado.APAGADO, "cinco minutos sin llamar a CORT");
            }
        }
    };

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
            if (enMarcha) {
                cierra(EscuchaEstado.APAGADO, "pantalla apagada; micrófono cerrado");
            }
        }
    }

    private void detenerYa() {
        prefs(this).edit().putBoolean(CLAVE, false).apply();
        cierra(EscuchaEstado.DETENIDO, "detenida por la usuaria");
        for (AlDetener oyente : DETENERES) {
            try {
                oyente.detener();
            } catch (RuntimeException fallo) {
                // El micrófono ya está cerrado aunque una superficie no responda.
            }
        }
    }

    private void cierra(EscuchaEstado estado, String motivo) {
        if (!enMarcha && vivo != this) {
            stopSelf();
            return;
        }
        enMarcha = false;
        principal.removeCallbacks(cortePorSilencio);
        if (oido != null) {
            oido.dejaLaPalabra();
        }
        if (foco != null) {
            foco.soltar(this);
        }
        if (appagado != null) {
            try {
                unregisterReceiver(appagado);
            } catch (IllegalArgumentException yaFuera) {
                // El receptor no llegó a registrarse.
            }
            appagado = null;
        }
        if (vivo == this) {
            vivo = null;
        }
        try {
            stopForeground(STOP_FOREGROUND_REMOVE);
        } catch (RuntimeException sinPila) {
            // La limpieza del micrófono ya se completó.
        }
        if (avisos != null) {
            avisos.cancel(ID_AVISO);
        }
        stopSelf();
        EscuchaEstadoGlobal.pon(estado, motivo);
    }

    @Override
    public void onDestroy() {
        cierra(EscuchaEstado.APAGADO, "servicio cerrado");
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intento) {
        return null;
    }

    private void canal() {
        if (Build.VERSION.SDK_INT < 26 || avisos == null) {
            return;
        }
        NotificationChannel canal = new NotificationChannel(CANAL, "CORT te escucha",
                NotificationManager.IMPORTANCE_LOW);
        canal.setDescription("Micrófono abierto para la palabra de activación. Sin sonido.");
        canal.setShowBadge(false);
        avisos.createNotificationChannel(canal);
    }

    private Notification aviso() {
        Intent abrir = new Intent(this, MainActivity.class);
        abrir.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        Intent detener = new Intent(this, ServicioEscucha.class)
                .setAction(DETENER).putExtra(ENCENDER, false);
        PendingIntent parar = PendingIntent.getService(this, 1, detener,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);
        return new Notification.Builder(this, CANAL)
                .setSmallIcon(icono())
                .setContentTitle("CORT · palabra de activación")
                .setContentText("Micrófono abierto para «hola CORT» u «oye CORT». "
                        + "Toca Detener para cerrarlo.")
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .setVisibility(Notification.VISIBILITY_PRIVATE)
                .setContentIntent(PendingIntent.getActivity(this, 0, abrir,
                        PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT))
                .addAction(new Notification.Action.Builder(icono(), "Detener", parar).build())
                .build();
    }

    private int icono() {
        int numero = getResources().getIdentifier("ic_cort_aviso", "drawable", getPackageName());
        return numero != 0 ? numero : android.R.drawable.ic_btn_speak_now;
    }
}
