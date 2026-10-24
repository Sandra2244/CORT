package com.cort.ia;

/*
 * El despertador de CORT: suena CORT, no la app de reloj de otro.
 *
 * Hasta F16, «pon una alarma» abría el reloj del sistema con `SET_ALARM` y ahí se
 * acababa la historia: CORT no sabía la hora que había puesto, no podía elegir la
 * canción ni apagarla. Esta clase lo pone ella misma con `AlarmManager` y una
 * notificación de categoría ALARMA en su propio canal.
 *
 * Lo que se decide aquí, y lo que se dice sin adornos:
 *
 * · **La hora la parte `Despertar`**, que es Java puro y está probado en el JDK
 *   (`Prueba7`): hora, canción, nota y rutina. Aquí sólo se obedece.
 * · **El minuto exacto no siempre se puede prometer.** Desde Android 12, para que
 *   una alarma sea exacta hace falta `SCHEDULE_EXACT_ALARM`, y esta casa no añade
 *   permisos: sin él, `canScheduleExactAlarms()` devuelve `false` y se usa
 *   `setAndAllowWhileIdle`, que el sistema puede retrasar unos minutos. Se dice en
 *   la respuesta (`exacta:false` y una frase), no se finge puntualidad que no hay.
 *   En Android 8–11 sí es exacta (`setExactAndAllowWhileIdle`).
 * · **La canción se busca al ponerla, no a las siete de la mañana.** Si el título
 *   no está en el teléfono, se dice ahí mismo y la alarma suena con su tono. Si
 *   falta el permiso de música, se pide en ese momento, no cuando ya está sonando.
 * · **Suena una notificación de canal alto con el sonido de alarma del sistema**,
 *   que es lo que despierta de verdad, y además se intenta poner la canción con
 *   `Reproductor` (servicio en primer plano). El intento de canción puede fallar
 *   si el sistema no deja arrancar servicios desde segundo plano; el tono de la
 *   notificación no depende de eso.
 * · **No sobrevive a apagar el teléfono.** Sin `RECEIVE_BOOT_COMPLETED` (no se
 *   declara: es un permiso y una superficie más) una alarma puesta se pierde al
 *   reiniciar. Se dice en la cara, no se promete lo que no hay.
 *
 * La estado se guarda en `SharedPreferences` («cort»), que ya existe: no hay ni un
 * fichero nuevo, ni un permiso nuevo. El manifiesto sólo gana el `<receiver>` de
 * `AlarmaSuena`, que no pide nada y no es exportado.
 */

import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.media.AudioAttributes;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import android.util.Log;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;

public final class Alarma {

    private static final String TAG = "CORT-alarma";
    static final String CANAL = "cort-alarma";
    static final int NOTA = 4700;
    static final int CITA = 4701;
    static final int CITA_DETENER = 4702;
    static final int CITA_POSPONER = 4703;

    static final String ACCION = "com.cort.ia.ALARMA";
    static final String ACCION_DETENER = "com.cort.ia.ALARMA_DETENER";
    static final String ACCION_POSPONER = "com.cort.ia.ALARMA_POSPONER";
    static final String EXTRA_EVENTO = "alarma";

    /** Los cinco minutos del botón «5 min» de la notificación. */
    static final int POSPONE_MIN = 5;

    private Alarma() { }

    /* ─────────────────────────── poner ─────────────────────────────── */

    /**
     * «despiértame a las 7:30 con After Dark para el examen» → alarma puesta.
     * Devuelve JSON siempre; nunca lanza. La frase se entiende con `Despertar`.
     */
    static String ponerDesde(Context c, String dicho) {
        Despertar.Plan plan = Despertar.parte(dicho);
        if (plan == null) {
            return mal("No oí la hora. Dime «despiértame a las 7:30»"
                     + " o «a las 7 con after dark para el examen».");
        }

        String cancionPedida = plan.cancion;
        String uri = "", titulo = "", artista = "";
        boolean faltaPermiso = false, noLaTengo = false;
        if (!cancionPedida.isEmpty()) {
            if (!Musica.puedeLeer(c)) {
                faltaPermiso = true;
                if (c instanceof MainActivity) ((MainActivity) c).pidePermiso("medios");
            } else {
                List<Musica.Pista> salen = Musica.buscar(c, cancionPedida, false);
                List<Elige.Candidata> candidatas = new ArrayList<>();
                for (Musica.Pista p : salen) {
                    candidatas.add(new Elige.Candidata(p.titulo, p.artista, p.genero));
                }
                int cual = Elige.mejor(cancionPedida, candidatas);
                if (cual < 0) {
                    noLaTengo = true;
                } else {
                    Musica.Pista p = salen.get(cual);
                    uri = p.uri == null ? "" : p.uri;
                    titulo = p.titulo == null ? "" : p.titulo;
                    artista = p.artista == null ? "" : p.artista;
                }
            }
        }

        long ahora = System.currentTimeMillis();
        long cuando = Despertar.proximo(plan.hora, plan.minuto, ahora,
                                        TimeZone.getDefault());
        boolean exacta = exacta(c);
        String hora = String.format(Locale.ROOT, "%02d:%02d", plan.hora, plan.minuto);
        if (!arma(c, cuando)) {
            return mal("El teléfono no me dejó poner la alarma. Revisa que CORT pueda"
                     + " usar alarmas en Ajustes ▸ Aplicaciones ▸ CORT.");
        }
        guarda(c, hora, cuando, plan, uri, titulo, artista, exacta);

        StringBuilder dice = new StringBuilder("Despertador a las ").append(hora)
                .append(", ").append(Despertar.falta(cuando, ahora)).append('.');
        if (!titulo.isEmpty()) {
            dice.append(" Con «").append(titulo).append('»')
                .append(artista.isEmpty() ? "" : " de " + artista).append('.');
        } else if (faltaPermiso) {
            dice.append(" No puedo leer tu música: dame el permiso y te pongo la canción;"
                      + " mientras, sonará el tono del despertador.");
        } else if (noLaTengo) {
            dice.append(" No encuentro «").append(cancionPedida)
                .append("» en el teléfono: sonará el tono del despertador.");
        }
        if (!plan.nota.isEmpty()) dice.append(" Nota: ").append(plan.nota).append('.');
        if (plan.rutina) dice.append(" Con la rutina de la mañana.");
        if (!exacta) {
            dice.append(" Este Android no me da el minuto exacto: puede sonar unos"
                      + " minutos tarde.");
        }

        return "{\"ok\":true,\"puesta\":true,\"alarma\":\"" + esc(hora) + "\""
             + ",\"cuando\":" + cuando
             + ",\"en\":\"" + esc(Despertar.falta(cuando, ahora)) + "\""
             + ",\"exacta\":" + exacta
             + ",\"cancion\":\"" + esc(cancionPedida) + "\""
             + ",\"titulo\":\"" + esc(titulo) + "\""
             + ",\"artista\":\"" + esc(artista) + "\""
             + ",\"nota\":\"" + esc(plan.nota) + "\""
             + ",\"rutina\":" + plan.rutina
             + ",\"dice\":\"" + esc(dice.toString()) + "\"}";
    }

    /** ¿Este Android deja prometer el minuto exacto? Sin permiso, no. */
    static boolean exacta(Context c) {
        if (Build.VERSION.SDK_INT < 31) return true;
        try {
            AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
            return am != null && am.canScheduleExactAlarms();
        } catch (Throwable noSePuedeSaber) {
            return false;
        }
    }

    /** Arma el `PendingIntent` del disparo. Exacto si se puede; si no, permitido. */
    private static boolean arma(Context c, long cuando) {
        AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
        if (am == null) return false;
        Intent i = new Intent(c, AlarmaSuena.class).setAction(ACCION);
        PendingIntent pi = PendingIntent.getBroadcast(c, CITA, i,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        try {
            if (exacta(c)) {
                am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, cuando, pi);
            } else {
                am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, cuando, pi);
            }
            return true;
        } catch (SecurityException aunqueDijeraQueSi) {
            // Un fabricante puede negar lo exacto pese a contestar que sí. Se cae a
            // la permitida: tarde es mejor que nunca, y la respuesta ya dirá `exacta`.
            try {
                am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, cuando, pi);
                return true;
            } catch (Throwable niAsi) {
                Log.w(TAG, "no se pudo armar: " + niAsi);
                return false;
            }
        } catch (Throwable raro) {
            Log.w(TAG, "no se pudo armar: " + raro);
            return false;
        }
    }

    private static void guarda(Context c, String hora, long cuando, Despertar.Plan plan,
                               String uri, String titulo, String artista, boolean exacta) {
        prefs(c).edit()
                .putString("alarma_hora", hora)
                .putLong("alarma_cuando", cuando)
                .putBoolean("alarma_exacta", exacta)
                .putString("alarma_cancion", plan.cancion)
                .putString("alarma_uri", uri)
                .putString("alarma_titulo", titulo)
                .putString("alarma_artista", artista)
                .putString("alarma_nota", plan.nota)
                .putBoolean("alarma_rutina", plan.rutina)
                .putBoolean("alarma_sonando", false)
                .apply();
    }

    /* ─────────────────────────── estado ────────────────────────────── */

    /** Qué hay puesto, para la cara y para el arranque. */
    static String estadoJson(Context c) {
        SharedPreferences p = prefs(c);
        long cuando = p.getLong("alarma_cuando", 0L);
        if (cuando <= 0L) {
            return "{\"ok\":true,\"puesta\":false,"
                 + "\"dice\":\"No tienes ninguna alarma puesta.\"}";
        }
        long ahora = System.currentTimeMillis();
        if (cuando <= ahora) {
            // El disparo ya pasó (o el teléfono se reinició con la alarma dentro):
            // se limpia en vez de enseñar una cuenta atrás negativa.
            limpiaPuesta(p);
            return "{\"ok\":true,\"puesta\":false,"
                 + "\"dice\":\"La alarma ya pasó.\"}";
        }
        String hora = p.getString("alarma_hora", "");
        String titulo = p.getString("alarma_titulo", "");
        String artista = p.getString("alarma_artista", "");
        String nota = p.getString("alarma_nota", "");
        boolean rutina = p.getBoolean("alarma_rutina", false);
        boolean exacta = p.getBoolean("alarma_exacta", true);
        String en = Despertar.falta(cuando, ahora);
        String dice = "Despertador a las " + hora + ", " + en + ".";
        if (!titulo.isEmpty()) dice += " Con «" + titulo + "».";
        if (!nota.isEmpty()) dice += " Nota: " + nota + ".";
        return "{\"ok\":true,\"puesta\":true,\"alarma\":\"" + esc(hora) + "\""
             + ",\"cuando\":" + cuando
             + ",\"en\":\"" + esc(en) + "\""
             + ",\"exacta\":" + exacta
             + ",\"cancion\":\"" + esc(p.getString("alarma_cancion", "")) + "\""
             + ",\"titulo\":\"" + esc(titulo) + "\""
             + ",\"artista\":\"" + esc(artista) + "\""
             + ",\"nota\":\"" + esc(nota) + "\""
             + ",\"rutina\":" + rutina
             + ",\"dice\":\"" + esc(dice) + "\"}";
    }

    /* ─────────────────────── cancelar / detener ────────────────────── */

    static String cancela(Context c) {
        SharedPreferences p = prefs(c);
        boolean habia = p.getLong("alarma_cuando", 0L) > 0L;
        try {
            AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
            if (am != null) {
                am.cancel(PendingIntent.getBroadcast(c, CITA,
                        new Intent(c, AlarmaSuena.class).setAction(ACCION),
                        PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE));
            }
        } catch (Throwable yaNo) {
            Log.w(TAG, "no se pudo desarmar: " + yaNo);
        }
        apagaElSonido(c);
        limpiaPuesta(p);
        return habia
            ? "{\"ok\":true,\"puesta\":false,\"dice\":\"Alarma cancelada.\"}"
            : "{\"ok\":true,\"puesta\":false,\"dice\":\"No había ninguna alarma puesta.\"}";
    }

    /** El botón «Detener»: calla la notificación y la canción que puso la alarma. */
    static String detener(Context c) {
        apagaElSonido(c);
        SharedPreferences p = prefs(c);
        p.edit().putLong("alarma_cuando", 0L).putBoolean("alarma_sonando", false).apply();
        return "{\"ok\":true,\"sonando\":false,\"dice\":\"Despertador detenido.\"}";
    }

    private static void apagaElSonido(Context c) {
        SharedPreferences p = prefs(c);
        try {
            NotificationManager nm = (NotificationManager)
                    c.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null) nm.cancel(NOTA);
        } catch (Throwable noHayBuzon) { /* sin notificación que apagar */ }
        if (p.getBoolean("alarma_sonando", false)) {
            // Sólo se toca el reproductor si la alarma fue quien lo puso: si la
            // dueña puso su música y la alarma sonó encima, detener no se la lleva.
            try { Reproductor.pausar(); } catch (Throwable sinReproductor) { }
        }
        p.edit().putBoolean("alarma_sonando", false).apply();
    }

    /* ─────────────────────────── posponer ──────────────────────────── */

    static String posponer(Context c) {
        SharedPreferences p = prefs(c);
        String hora = p.getString("alarma_hora", "");
        if (hora.isEmpty()) {
            return mal("No hay ninguna alarma sonando que posponer.");
        }
        apagaElSonido(c);
        long cuando = System.currentTimeMillis() + POSPONE_MIN * 60_000L;
        if (!arma(c, cuando)) return mal("El teléfono no me dejó posponer la alarma.");
        p.edit().putLong("alarma_cuando", cuando)
                .putBoolean("alarma_sonando", false).apply();
        String dice = "Te despierto otra vez en " + POSPONE_MIN + " minutos.";
        return "{\"ok\":true,\"puesta\":true,\"alarma\":\"" + esc(hora) + "\""
             + ",\"cuando\":" + cuando + ",\"en\":\"en " + POSPONE_MIN + " min\""
             + ",\"dice\":\"" + esc(dice) + "\"}";
    }

    /* ─────────────────────────── el disparo ────────────────────────── */

    /**
     * Lo que hace `AlarmaSuena` al despertar: el aviso de canal alto, la canción
     * (si la hay) y el cuadro de la cara. Devuelve el JSON que se emite.
     */
    static String sono(Context c) {
        SharedPreferences p = prefs(c);
        String hora = p.getString("alarma_hora", "");
        String titulo = p.getString("alarma_titulo", "");
        String artista = p.getString("alarma_artista", "");
        String uri = p.getString("alarma_uri", "");
        String nota = p.getString("alarma_nota", "");
        boolean rutina = p.getBoolean("alarma_rutina", false);
        // La alarma es de una sola vez: queda el recuerdo de lo que sonó, no una
        // alarma armada otra vez mañana. Ponerla a diario será otra ronda.
        p.edit().putLong("alarma_cuando", 0L).putBoolean("alarma_sonando", true).apply();

        String detalle = "";
        if (!nota.isEmpty()) detalle = nota;
        if (!titulo.isEmpty()) {
            detalle += (detalle.isEmpty() ? "" : " · ") + "«" + titulo + "»"
                     + (artista.isEmpty() ? "" : " de " + artista);
        }
        String rutinaTexto = rutina ? rutina(c) : "";
        if (!rutinaTexto.isEmpty()) {
            detalle += (detalle.isEmpty() ? "" : " · ") + rutinaTexto;
        }
        if (detalle.isEmpty()) detalle = "Buenos días.";

        String dice = "Buenos días. Son las " + hora + "."
                     + (nota.isEmpty() ? "" : " " + nota + ".")
                     + (titulo.isEmpty() ? "" : " Suena «" + titulo + "».");
        String evento = "{\"ok\":true,\"hora\":\"" + esc(hora) + "\""
                      + ",\"nota\":\"" + esc(nota) + "\""
                      + ",\"titulo\":\"" + esc(titulo) + "\""
                      + ",\"artista\":\"" + esc(artista) + "\""
                      + ",\"rutina\":" + rutina
                      + ",\"dice\":\"" + esc(dice) + "\"}";

        aviso(c, hora, detalle, evento);
        if (!uri.isEmpty()) ponLaCancion(c, uri, titulo, artista);

        MainActivity cara = MainActivity.front();
        if (cara != null) {
            try { cara.puente().alarmaEnLaCara(evento); } catch (Throwable sinCara) { }
        }
        // Si la cara no está abierta y CORT tiene «aparecer encima de otras apps»,
        // se trae sola. Sin esa concesión Android no deja abrir actividades desde
        // segundo plano, y se queda la notificación (que es la que despierta).
        if (cara == null && puedeAsomarse(c)) {
            try {
                Intent abre = new Intent(c, MainActivity.class)
                        .setAction(MainActivity.A_ALARMA)
                        .putExtra(EXTRA_EVENTO, evento)
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                                | Intent.FLAG_ACTIVITY_SINGLE_TOP);
                c.startActivity(abre);
            } catch (Throwable noDeja) {
                Log.i(TAG, "la cara no se pudo asomar: " + noDeja);
            }
        }
        return evento;
    }

    private static void aviso(Context c, String hora, String detalle, String evento) {
        try {
            NotificationManager nm = (NotificationManager)
                    c.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm == null) return;
            if (Build.VERSION.SDK_INT >= 26 && nm.getNotificationChannel(CANAL) == null) {
                NotificationChannel canal = new NotificationChannel(CANAL, "CORT · alarma",
                        NotificationManager.IMPORTANCE_HIGH);
                canal.setDescription("El despertador de CORT: hora, canción y nota.");
                canal.enableVibration(true);
                canal.setVibrationPattern(new long[] { 0, 700, 500, 700 });
                canal.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
                try {
                    AudioAttributes deAlarma = new AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_ALARM)
                            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                            .build();
                    Uri tono = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM);
                    if (tono == null) tono = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION);
                    if (tono != null) canal.setSound(tono, deAlarma);
                } catch (Throwable sinTono) {
                    // Un aparato sin sonido de alarma se queda con la vibración.
                }
                nm.createNotificationChannel(canal);
            }

            Intent abre = new Intent(c, MainActivity.class)
                    .setAction(MainActivity.A_ALARMA)
                    .putExtra(EXTRA_EVENTO, evento)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            PendingIntent cara = PendingIntent.getActivity(c, 4710, abre,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

            PendingIntent detener = PendingIntent.getBroadcast(c, CITA_DETENER,
                    new Intent(c, AlarmaSuena.class).setAction(ACCION_DETENER),
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            PendingIntent posponer = PendingIntent.getBroadcast(c, CITA_POSPONER,
                    new Intent(c, AlarmaSuena.class).setAction(ACCION_POSPONER),
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

            Notification.Builder b = Build.VERSION.SDK_INT >= 26
                    ? new Notification.Builder(c, CANAL)
                    : new Notification.Builder(c);
            b.setSmallIcon(android.R.drawable.stat_notify_error)
             .setContentTitle("Despertador · " + hora)
             .setContentText(detalle)
             .setStyle(new Notification.BigTextStyle().bigText(detalle))
             .setCategory(Notification.CATEGORY_ALARM)
             .setVisibility(Notification.VISIBILITY_PUBLIC)
             .setOngoing(true)
             .setAutoCancel(false)
             .setWhen(System.currentTimeMillis())
             .setShowWhen(true)
             .setContentIntent(cara)
             // Los dos botones van sin icono (`0` es legal y lo omite). Los
             // `android.R.drawable` que esta casa da por comprobados son otros
             // cuatro; inventar aquí un `ic_media_pause` local pasaría el `javac`
             // de casa y reventaría en el runner, que es la trampa ya medida.
             .addAction(new Notification.Action.Builder(0,
                     "Detener", detener).build())
             .addAction(new Notification.Action.Builder(0,
                     POSPONE_MIN + " min", posponer).build());
            Notification n = b.build();
            // El sonido del canal suena una vez; esta bandera le pide al sistema
            // que lo repita hasta que se cancele. No todos los fabricantes la
            // respetan con canales, y por eso no se promete «suena sin parar».
            n.flags |= Notification.FLAG_INSISTENT;
            nm.notify(NOTA, n);
        } catch (Throwable noHayAviso) {
            Log.w(TAG, "el aviso de alarma no salió: " + noHayAviso);
        }
    }

    private static void ponLaCancion(Context c, String uri, String titulo, String artista) {
        try {
            List<Reproductor.Pista> una = new ArrayList<>();
            una.add(new Reproductor.Pista(uri, titulo.isEmpty() ? "Despertador" : titulo,
                                          artista, "", 0, false));
            Reproductor.ponerCola(c, una, 0);
            Reproductor.reproducir();
        } catch (Throwable noSePudo) {
            // Arrancar el servicio desde segundo plano puede estar prohibido si la
            // alarma fue permitida (no exacta). El tono de la notificación sigue.
            Log.i(TAG, "la canción del despertar no arrancó: " + noSePudo);
        }
    }

    /** «Tienes 2 cosas hoy», leído en el momento, si la agenda tiene permiso. */
    private static String rutina(Context c) {
        try {
            if (!Agenda.conPermiso(c)) return "";
            JSONObject j = new JSONObject(Agenda.agenda(c, "{\"que\":\"hoy\"}"));
            if (!j.optBoolean("ok", false)) return "";
            String dicho = j.optString("dice", "");
            return dicho == null ? "" : dicho.trim();
        } catch (Throwable sinAgenda) {
            return "";
        }
    }

    private static boolean puedeAsomarse(Context c) {
        try {
            return Build.VERSION.SDK_INT < 23 || Settings.canDrawOverlays(c);
        } catch (Throwable noSeSabe) {
            return false;
        }
    }

    /* ─────────────────────────── utilidades ────────────────────────── */

    private static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences("cort", Context.MODE_PRIVATE);
    }

    private static void limpiaPuesta(SharedPreferences p) {
        p.edit().putLong("alarma_cuando", 0L)
                .putString("alarma_uri", "")
                .putString("alarma_titulo", "")
                .putString("alarma_artista", "")
                .putString("alarma_cancion", "")
                .putString("alarma_nota", "")
                .putBoolean("alarma_rutina", false)
                .putBoolean("alarma_sonando", false)
                .apply();
    }

    private static String mal(String dice) {
        return "{\"ok\":false,\"dice\":\"" + esc(dice) + "\"}";
    }

    private static String esc(String t) {
        return Reproductor.esc(t == null ? "" : t);
    }
}
