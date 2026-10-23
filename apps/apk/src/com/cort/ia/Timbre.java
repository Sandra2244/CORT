package com.cort.ia;

import android.content.Context;

/*
 * Timbre.java — el que pone el aviso, nada más.
 *
 * Bajar `qwen2.5:7b` son 4,7 GB: por la Wi-Fi de casa es media hora larga. Sin
 * aviso, la dueña tiene que dejar la hoja de Modelos abierta mirando la barra,
 * y con eso el teléfono no se suelta — que es justo lo que ella pidió
 * («que avise cuando termine»).
 *
 * Por qué vive en su propio fichero y no dentro de `Ollama`: `Ollama` es Java puro
 * (háblale por Wi-Fi, lee NDJSON, piensa en bytes) y `scripts/prueba-mente.sh` lo
 * compila y lo prueba EN EL PORTÁTIL con el JDK, con cinco gemelos de papel de
 * Android. Un `android.app.NotificationManager` de verdad ahí no compila, y
 * fingirlo con más papel sería mentir en la prueba. Así que `Ollama` llama a
 * `Timbre.bajada(...)` — que en el portátil se queda en el fichero que no se copia
 * — y el aviso, que es puroAndroid, se compila sólo en el APK. Lo que se comprueba
 * por las dos vías está en `scripts/prueba-costura.py`, sector [24].
 *
 * Es una notificación normal de `NotificationManager`, NO un servicio en primer
 * plano: no añade `foregroundServiceType` ni permisos al manifiesto, y la
 * superficie del manifiesto es lo que hizo que Play Protect rechazara al APK, así
 * que aquí no se toca ni una línea de XML — `POST_NOTIFICATIONS` ya estaba
 * declarado desde la ronda del reproductor. Los iconos (`stat_sys_download_done`,
 * `stat_notify_error`) son de `android.R.drawable`, públicos desde la API 1.
 *
 * El límite dicho en seco: el hilo que lee el `NDJSON` es de esta app. Si Android
 * mata el proceso (en un móvil con poco aire libre se hace), el aviso no llega; lo
 * que sí queda hecho es la bajada, que el PC terminó igual.
 */
public class Timbre {

    private static final String CANAL_MODELO = "cort-modelos";
    private static final int NOTA_MODELO = 4230;

    /**
     * El aviso en sí. `bien` = terminó; si no, `motivo` es lo que dijo `Ollama`
     * (o la frase honesta de que se cortó sin saber por qué). `donde` es el
     * servidor, para que el texto diga dónde está el modelo.
     */
    public static void bajada(Context app, boolean bien, String nombre,
                              long hecho, long total, String motivo, String donde) {
        try {
            android.app.NotificationManager nm = (android.app.NotificationManager)
                    app.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm == null) return;
            if (android.os.Build.VERSION.SDK_INT >= 26
                    && nm.getNotificationChannel(CANAL_MODELO) == null) {
                android.app.NotificationChannel c = new android.app.NotificationChannel(
                        CANAL_MODELO, "CORT · modelos",
                        android.app.NotificationManager.IMPORTANCE_DEFAULT);
                c.setDescription("Avisa cuando un modelo termina de bajar, o cuando la bajada se cortó.");
                c.setShowBadge(false);
                nm.createNotificationChannel(c);
            }
            /* El `NEW_TASK` no es adorno: se avisa desde un hilo de `Ollama`, sin
               Activity delante, y un `PendingIntent.getActivity` sin esa bandera no
               arranca la cara desde el background. */
            android.content.Intent abre = new android.content.Intent(app, MainActivity.class);
            abre.addFlags(android.content.Intent.FLAG_ACTIVITY_SINGLE_TOP
                          | android.content.Intent.FLAG_ACTIVITY_NEW_TASK);
            android.app.PendingIntent quien = android.app.PendingIntent.getActivity(
                    app, 4231, abre,
                    android.app.PendingIntent.FLAG_UPDATE_CURRENT | android.app.PendingIntent.FLAG_IMMUTABLE);
            String detalle = bien
                    ? (total > 0 && hecho < total
                       ? Ollama.peso(hecho) + " de " + Ollama.peso(total) : Ollama.peso(hecho))
                      + " · ya está en " + donde + ". Elige el cerebro en Charla."
                    : (motivo == null || motivo.isEmpty()
                       ? "la bajada se cortó sin decir por qué" : motivo);
            android.app.Notification.Builder b =
                    (android.os.Build.VERSION.SDK_INT >= 26)
                    ? new android.app.Notification.Builder(app, CANAL_MODELO)
                    : new android.app.Notification.Builder(app);
            b.setSmallIcon(bien ? android.R.drawable.stat_sys_download_done
                                : android.R.drawable.stat_notify_error)
             .setContentTitle(bien ? "Modelo listo · " + nombre : "La bajada de " + nombre + " paró")
             .setContentText(detalle)
             .setStyle(new android.app.Notification.BigTextStyle().bigText(detalle))
             .setContentIntent(quien)
             .setAutoCancel(true)
             .setOnlyAlertOnce(true);
            nm.notify(NOTA_MODELO, b.build());
        } catch (Exception noHayForma) {
            // Sin permiso de avisos (Android 13) `notify` se ignora en silencio; nunca
            // es motivo para cortar una descarga que va por buen camino.
            android.util.Log.i("cort", "el aviso de bajada no salió: " + noHayForma);
        }
    }
}
