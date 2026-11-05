package dev.sandra.cort.movil;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Handler;
import android.os.Looper;

import java.util.Calendar;

/**
 * El saludo al encender el teléfono (U2). La dueña quiere que CORT viva en el aparato:
 * se enciende la pantalla de mañana y es ella la que dice «buenos días» y lo que hay
 * pendiente, sin que nadie abra la aplicación.
 *
 * Dos cosas honestas escritas aquí, porque si no el código miente:
 *
 * 1. Samsung (One UI) cierra procesos en segundo plano. Sin eximir a CORT de la
 *    optimización de batería este aviso puede no llegar nunca, y la pantalla de enlace
 *    lleva el paso escrito. No se promete el saludo: se mide.
 * 2. Con el teléfono bloqueado hay motores de texto-a-voz que no sueltan sonido. Por eso
 *    el saludo sale **además** por la notificación: la frase se vea aunque no se oiga.
 */
public class Arranque extends BroadcastReceiver {

    public static final String CANAL = "cort-saludo";

    @Override
    public void onReceive(Context contexto, Intent orden) {
        if (!Intent.ACTION_BOOT_COMPLETED.equals(orden.getAction())) {
            return;
        }
        final PendingResult fin = goAsync();
        final Context app = contexto.getApplicationContext();
        String dicho = saludo();
        notifica(app, dicho);
        final Voz boca = new Voz(app);
        boca.hablar(dicho);
        // El motor de voz tarda en arrancar después del encendido; se le deja aire antes
        // de soltar el receptor, o el sistema mata el proceso con la frase en la cola.
        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            boca.cerrar();
            fin.finish();
        }, 15_000);
    }

    /** El momento del día y la pila, que es lo que se puede saber sin despertar a nadie. */
    static String saludo() {
        Calendar ahora = Calendar.getInstance();
        int hora = ahora.get(Calendar.HOUR_OF_DAY);
        String momento = hora < 12 ? "Buenos días" : (hora < 19 ? "Buenas tardes" : "Buenas noches");
        return momento + ". Soy CORT y sigo aquí, en tu teléfono, sin red.";
    }

    private void notifica(Context contexto, String dicho) {
        NotificationManager manager = (NotificationManager)
                contexto.getSystemService(Context.NOTIFICATION_SERVICE);
        NotificationChannel canal = new NotificationChannel(CANAL, "Saludos de CORT",
                NotificationManager.IMPORTANCE_LOW);
        canal.setDescription("El momento del día y lo pendiente; sin sonido de aviso.");
        manager.createNotificationChannel(canal);

        Intent abrir = new Intent(contexto, MainActivity.class);
        abrir.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        Notification aviso = new Notification.Builder(contexto, CANAL)
                .setSmallIcon(iconoDeAviso(contexto))
                .setContentTitle(dicho)
                .setContentText(toqueParaAbrir(contexto))
                .setContentIntent(android.app.PendingIntent.getActivity(
                        contexto, 0, abrir,
                        android.app.PendingIntent.FLAG_IMMUTABLE | android.app.PendingIntent.FLAG_UPDATE_CURRENT))
                .setAutoCancel(true)
                .build();
        manager.notify(24, aviso);
    }

    /**
     * `ic_cort_aviso` busca su número de recurso a mano. La cadena de compilación de
     * esta rama (`aapt2` + `javac` + `d8`, sin Gradle) nunca genera `R.java`, así que
     * en el Java no existe la clase `R` con la que se escribe `R.drawable.ic_cort_aviso`
     * en un proyecto normal; `getIdentifier` es el camino que no obliga a tocar el
     * `compilar.sh`. Si el recurso faltara, el aviso sale con el icono del sistema en
     * vez de no salir.
     */
    private int iconoDeAviso(Context contexto) {
        int numero = contexto.getResources().getIdentifier("ic_cort_aviso", "drawable",
                contexto.getPackageName());
        return numero != 0 ? numero : android.R.drawable.stat_notify_chat;
    }

    /** Con Android 13 la notificación sólo se ve si la dueña dio el permiso. */
    private String toqueParaAbrir(Context contexto) {
        int concedido = contexto.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS);
        return concedido == android.content.pm.PackageManager.PERMISSION_GRANTED
                ? "Toca para abrir CORT."
                : "Sin permiso de notificaciones esto no se ve: ábrelo desde el lanzador.";
    }
}
