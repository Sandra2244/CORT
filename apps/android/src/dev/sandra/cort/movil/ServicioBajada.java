package dev.sandra.cort.movil;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import java.util.List;

/**
 * Bajar un cerebro sin tener la pantalla del Almacén abierta (F20e). La dueña pidió
 * que el GGUF integrado se baje **solo** al conectarse a internet; una descarga de
 * 491 MB que se corta cuando ella desbloquea y guarda el teléfono no es eso. Android
 * mata el hilo de una actividad cerrada, y lo único que sigue corriendo es un servicio
 * en primer plano con su aviso puesto.
 *
 * Qué hay dentro y qué no:
 *
 * 1. **La descarga es `Bajada`, la misma de siempre.** `Range` para reanudar, `.part`
 *    mientras dura y SHA-256 entera antes de renombrar. Este archivo no baja bytes:
 *    sólo le da una vida más larga y un lugar donde escribir el progreso.
 * 2. **Ni `DownloadManager` ni `WorkManager`.** No están en el APK (no hay AndroidX)
 *    y aunque estuvieran: un gestor del sistema se describe a sí mismo en la
 *    bandeja, y ahí es donde acabaría el enlace de descarga. El aviso de este
 *    servicio escribe nombre, megas y porcentaje — nunca una dirección.
 * 3. **El progreso va a `SharedPreferences`.** La cara del PC y la pantalla nativa
 *    lo leen de ahí, sin `Binder` ni IPC propio: es lo que se puede probar sin
 *    AndroidX y lo que sigue funcionando si la actividad se montó después de
 *    arrancar la bajada.
 * 4. **Se puede cortar.** El botón «Detener» del aviso llama a `Bajada.corta()`: lo
 *    bajado se queda en el `.part` y la siguiente vez se sigue de ahí, que es la
 *    promesa que `Cerebros.java` ya hacía en primer plano.
 *
 * Lo que no hace: no decide qué modelo bajar (eso es `AutoCerebro.elige`), no abre el
 * GGUF en memoria y no cambia el modo. Terminado el archivo, la dueña —o la ruta—
 * decide cuándo cargarlo.
 */
public class ServicioBajada extends Service {

    /** La orden. Un `Intent` con `FICHA` arranca; uno con `CORTAR` la para. */
    public static final String ACCION = "dev.sandra.cort.movil.BAJAR";
    public static final String FICHA = "cort-ficha";
    public static final String CORTAR = "cort-cortar";

    static final String CANAL = "cort-bajada";
    private static final int ID_AVISO = 27;

    /* ------------------------------------------------- lo que lee la pantalla */

    /** Las preferencias de la app, las mismas del despertador. */
    public static final String CLAVE_ID = "bajada_id";
    public static final String CLAVE_TEXTO = "bajada_texto";
    public static final String CLAVE_PCT = "bajada_pct";
    public static final String CLAVE_CURSO = "bajada_en_curso";

    /** El porcentaje tope del aviso: `Bajada` avisa cada 500 ms y la bandeja no lo aguanta. */
    private static final long PASO_AVISO_MS = 1500L;

    private final Handler principal = new Handler(Looper.getMainLooper());
    private NotificationManager avisos;
    private volatile Bajada enEjecucion;
    private volatile String bajando = "";
    private long ultimoAviso;

    /* ------------------------------------------------------------------- estática */

    /**
     * Arrancar una bajada. Con una actividad en primer plano (abrir CORT, el Almacén,
     * o el interruptor de Ajustes): Android 14 no deja levantar un servicio en
     * segundo plano desde el aire, y por eso `AutoCerebro.revisa` se llama desde
     * dentro de la app, no desde el encendido del teléfono.
     */
    public static void arranca(Context contexto, String id) {
        if (id == null || id.trim().isEmpty()) {
            return;
        }
        Intent orden = new Intent(contexto, ServicioBajada.class);
        orden.putExtra(FICHA, id);
        if (Build.VERSION.SDK_INT >= 26) {
            contexto.startForegroundService(orden);
        } else {
            contexto.startService(orden);
        }
    }

    /** Parar lo que haya. Sin bajada en curso no escribe nada raro: su `id` está vacío. */
    public static void detener(Context contexto) {
        if (!enCurso(contexto)) {
            return;
        }
        Intent orden = new Intent(contexto, ServicioBajada.class);
        orden.putExtra(CORTAR, true);
        contexto.startService(orden);
    }

    public static boolean enCurso(Context contexto) {
        return prefs(contexto).getBoolean(CLAVE_CURSO, false);
    }

    /** La línea tal cual la escribió el servicio, para pintarla sin reformularla. */
    public static String texto(Context contexto) {
        return prefs(contexto).getString(CLAVE_TEXTO, "");
    }

    public static int pct(Context contexto) {
        return prefs(contexto).getInt(CLAVE_PCT, 0);
    }

    /** Qué se está bajando ahora mismo, o cadena vacía. `AutoCerebro` lo usa de cerrojo. */
    public static String idEnCurso(Context contexto) {
        return enCurso(contexto) ? prefs(contexto).getString(CLAVE_ID, "") : "";
    }

    private static SharedPreferences prefs(Context contexto) {
        return contexto.getSharedPreferences(AutoCerebro.PREFERENCIAS, Context.MODE_PRIVATE);
    }

    /* -------------------------------------------------------------------- servicio */

    @Override
    public void onCreate() {
        super.onCreate();
        avisos = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        canal();
    }

    @Override
    public int onStartCommand(Intent intento, int flags, int arranque) {
        // Un `null` es el sistema reavivando el servicio después de matarlo por
        // memoria. Sin ficha que bajar no hay nada que reanudar: se apaga y ya,
        // porque `START_STICKY` con un aviso de descarga vacío es peor que callarse.
        if (intento == null) {
            stopSelf();
            return START_NOT_STICKY;
        }
        if (intento.getBooleanExtra(CORTAR, false)) {
            para();
            return START_NOT_STICKY;
        }
        String id = intento.getStringExtra(FICHA);
        if (id == null || id.isEmpty()) {
            para();
            return START_NOT_STICKY;
        }
        if (bajando.equals(id)) {
            return START_STICKY;          // ya está en marcha: no se abre un segundo `.part`
        }
        CerebroLocal.Ficha ficha = busca(id);
        if (ficha == null) {
            avisaFinal("Ese cerebro no está en la lista del APK (" + id
                    + "): nada se bajó.");
            stopSelf();
            return START_NOT_STICKY;
        }
        if (Bajada.de(this, ficha).esta()) {
            avisaFinal(ficha.nombre + " ya está en el teléfono: no se bajó nada.");
            stopSelf();
            return START_NOT_STICKY;
        }
        monta(id, ficha.nombre);
        bajando = id;
        try {
            Notification aviso = aviso("Preparando " + ficha.nombre + "…", 0, true);
            if (Build.VERSION.SDK_INT >= 29) {
                startForeground(ID_AVISO, aviso, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
            } else {
                startForeground(ID_AVISO, aviso);
            }
        } catch (RuntimeException noDeja) {
            // Sin primer plano la bajada moriría a los pocos segundos; es mejor
            // decirlo que fingir que sigue.
            escribe(id, "el teléfono no dejó abrir la descarga en segundo plano: "
                    + "abre el Almacén y bájalo ahí", 0, false);
            bajando = "";
            avisaFinal("No se pudo bajar " + ficha.nombre
                    + " en segundo plano. Ábrelo en Almacén de cerebros.");
            stopSelf();
            return START_NOT_STICKY;
        }
        trabaja(ficha);
        return START_STICKY;
    }

    private CerebroLocal.Ficha busca(String id) {
        List<CerebroLocal.Ficha> catalogo = CerebroLocal.catalogo(getApplicationContext());
        for (CerebroLocal.Ficha f : catalogo) {
            if (f.id.equals(id)) {
                return f;
            }
        }
        return null;
    }

    /**
     * El lazo, en su hilo: `Bajada.ejecutar` bloquea lo que tarde el archivo
     * (a los 40 KB/s medidos en esta casa, 3 h 20 min para los 491 MB del 0,5B).
     * Todo lo que toca la bandeja o las preferencias vuelve por `principal`, que es
     * el único hilo que puede llamar a `stopForeground` sin carrera con `onDestroy`.
     */
    private void trabaja(final CerebroLocal.Ficha f) {
        final Bajada b = Bajada.de(this, f);
        enEjecucion = b;
        escribe(f.id, "bajando " + f.nombre + " (" + Bajada.mb(f.bytes) + " MB)…", 0, true);
        Thread trabajo = new Thread(() -> {
            String culpa = null;
            try {
                b.ejecutar(f, (hechos, total, pct, texto) -> {
                    if (texto != null) {
                        principal.post(() -> {
                            escribe(f.id, texto, pct, true);
                            long ahora = System.currentTimeMillis();
                            if (ahora - ultimoAviso >= PASO_AVISO_MS) {
                                ultimoAviso = ahora;
                                if (avisos != null) {
                                    avisos.notify(ID_AVISO, aviso(texto, pct, true));
                                }
                            }
                        });
                    }
                });
            } catch (Exception algo) {
                culpa = algo.getMessage() == null ? algo.toString() : algo.getMessage();
            }
            final String motivo = culpa;
            principal.post(() -> termina(f, motivo));
        }, "cort-bajada-" + f.id);
        trabajo.setDaemon(true);
        trabajo.start();
    }

    /** El cierre, siempre por el hilo principal: escribe, avisa y suelta el primer plano. */
    private void termina(CerebroLocal.Ficha f, String motivo) {
        enEjecucion = null;
        bajando = "";
        if (motivo == null) {
            escribe(f.id, f.nombre + " instalado y verificado con su SHA-256", 100, false);
            cierraAviso(f.nombre + " quedó instalado en el teléfono. "
                    + "Ya lo puedes elegir en Almacén de cerebros.");
            return;
        }
        boolean cortada = motivo.startsWith("descarga cortada");
        escribe(f.id, motivo, pct(this), false);
        cierraAviso((cortada ? "Descarga parada: " : "No se pudo bajar " + f.nombre + ": ")
                + motivo + (cortada ? "" : " · lo bajado queda y se reanuda sola"));
    }

    /** El botón de «Detener»: corta la bajada y deja el `.part` donde está. */
    private void para() {
        Bajada b = enEjecucion;
        if (b != null) {
            b.corta();
            return;
        }
        // Sin nada en marcha, la orden sólo borra un aviso viejo que quedó anclado.
        if (avisos != null) {
            avisos.cancel(ID_AVISO);
        }
        stopSelf();
    }

    private void escribe(String id, String texto, int pct, boolean curso) {
        prefs(this).edit()
                .putString(CLAVE_ID, id)
                .putString(CLAVE_TEXTO, texto)
                .putInt(CLAVE_PCT, pct)
                .putBoolean(CLAVE_CURSO, curso)
                .apply();
    }

    /** Poner el aviso por primera vez: `startForeground` necesita que exista ya. */
    private void monta(String id, String nombre) {
        escribe(id, "preparando " + nombre + "…", 0, true);
    }

    /* ---------------------------------------------------------------------- aviso */

    private void canal() {
        if (Build.VERSION.SDK_INT < 26 || avisos == null) {
            return;
        }
        NotificationChannel canal = new NotificationChannel(CANAL, "Descargas de CORT",
                NotificationManager.IMPORTANCE_LOW);
        canal.setDescription("El GGUF que se está bajando, con su porcentaje. "
                + "Sin sonido de aviso.");
        canal.setShowBadge(false);
        avisos.createNotificationChannel(canal);
    }

    /**
     * El aviso de la pila. Lleva nombre, megas y porcentaje y **nunca la dirección**
     * de la que baja: la bandeja se lee con el teléfono bloqueado.
     */
    private Notification aviso(String detalle, int pct, boolean enMarcha) {
        Intent abrir = new Intent(this, MainActivity.class);
        abrir.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        Notification.Builder cuadro = new Notification.Builder(this, CANAL)
                .setSmallIcon(icono())
                .setContentTitle("CORT · bajando un cerebro")
                .setContentText(detalle)
                .setOngoing(enMarcha)
                .setOnlyAlertOnce(true)
                .setVisibility(Notification.VISIBILITY_PRIVATE)
                .setProgress(100, pct, pct <= 0)
                .setContentIntent(PendingIntent.getActivity(this, 0, abrir,
                        PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT));
        if (enMarcha) {
            Intent cortar = new Intent(this, ServicioBajada.class);
            cortar.putExtra(CORTAR, true);
            cuadro.addAction(new Notification.Action.Builder(null, "Detener",
                    PendingIntent.getService(this, 1, cortar,
                            PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT))
                    .build());
        }
        return cuadro.build();
    }

    /** El aviso mientras el servicio sigue vivo (ficha rara, cancelado antes de empezar). */
    private void avisaFinal(String detalle) {
        if (avisos != null) {
            avisos.notify(ID_AVISO, aviso(detalle, 0, false));
        }
    }

    /** El aviso que **sobrevive** al servicio: se despega de la pila y se puede borrar. */
    private void cierraAviso(String detalle) {
        try {
            stopForeground(STOP_FOREGROUND_DETACH);
        } catch (Exception noHuboPila) {
            // si nunca llegó a montarse, queda sólo el aviso de abajo
        }
        if (avisos != null) {
            avisos.notify(ID_AVISO, aviso(detalle, 100, false));
        }
        stopSelf();
    }

    /**
     * `ic_cort_aviso` buscado a mano: la cadena `aapt2` + `javac` + `d8` no genera
     * `R.java`, así que no existe un `R.drawable.ic_cort_aviso` que escribir. El
     * mismo camino de `Arranque.java` y `ServicioEscucha.java`.
     */
    private int icono() {
        int numero = getResources().getIdentifier("ic_cort_aviso", "drawable", getPackageName());
        return numero != 0 ? numero : android.R.drawable.stat_sys_download_done;
    }

    @Override
    public void onDestroy() {
        Bajada b = enEjecucion;
        if (b != null) {
            b.corta();                 // que no se quede un hilo bajando a servicio muerto
        }
        bajando = "";
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intento) {
        return null;        // es un servicio empezado, no enlazado
    }
}
