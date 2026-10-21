package com.cort.ia;

/*
 * La agenda y el correo de la dueña, desde el teléfono, dicho sin adornos.
 *
 * · **Agenda sí**: «¿qué tengo hoy?», «mis citas de esta semana». Se lee
 *   `CalendarContract.Instances`, que es la tabla de las citas ya materializadas,
 *   y para eso hace falta `READ_CALENDAR`, que se pide la primera vez que se
 *   pregunta (no al abrir la app, que es la norma de esta casa: permiso que no se
 *   usa no se pide). Sin el permiso, `ok:false` con la explicación; nunca un cero
 *   disfrazado de «no tienes nada».
 * · **Correo: lo que Android deja**. No hay API para leer el Gmail de otra app, y
 *   simularlo con `AccessibilityService` es justo lo que Google castiga. Lo que sí
 *   hay es el **buzón ya sonando en la barra de notificaciones**: `Avisos.java` oye
 *   lo que el sistema muestra, y desde ahí CORT puede decir «tienes 2 avisos de
 *   Gmail» y abrir la app con un toque. Eso es real y no pide un permiso de más.
 * · **Escribir un correo o una cita**: se abre la app con la intención correcta
 *   (`ACTION_INSERT` sobre `Events` para «apunta cena con Samuel el jueves a las
 *   9»), no se rellena a medias por detrás.
 *
 * No hay aquí ni escritura sobre las citas de otras apps ni borrado de correos:
 * eso es tocar la vida de la dueña, y se hace con su dedo delante.
 */

import android.content.ContentUris;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.provider.CalendarContract;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Calendar;
import java.util.Locale;

public class Agenda {

    private static final String[] PROYECCION = new String[] {
        CalendarContract.Instances.BEGIN,
        CalendarContract.Instances.END,
        CalendarContract.Instances.TITLE,
        CalendarContract.Instances.CALENDAR_ID,
    };

    /** El permiso de calendario, que es de los que preguntan. */
    public static boolean conPermiso(Context c) {
        try {
            return c.checkSelfPermission(android.Manifest.permission.READ_CALENDAR)
                   == PackageManager.PERMISSION_GRANTED;
        } catch (Exception elSistemaNoPregunta) {
            return false;
        }
    }

    /**
     * Entrada única del puente. `peticion` es `{"que":"hoy|proximos|abrir|correo|apunta",…}`.
     * Nunca lanza: lo que no se puede se cuenta en `dice`.
     */
    public static String agenda(Context c, String peticion) {
        String que = "hoy";
        int dias = 7;
        String titulo = "";
        long hora = 0L;
        try {
            JSONObject p = new JSONObject(peticion == null ? "{}" : peticion);
            que = p.optString("que", "hoy").toLowerCase(Locale.US);
            dias = Math.max(1, Math.min(60, p.optInt("dias", 7)));
            titulo = p.optString("titulo", "");
            hora = p.optLong("hora", 0L);
        } catch (Exception jsonTorcido) {
            return "{\"ok\":false,\"dice\":\"No entendí la petición de agenda.\"}";
        }

        if ("abrir".equals(que))      return abrirApp(c, CalendarContract.CONTENT_URI
                                                .buildUpon().appendPath("time").build());
        if ("correo".equals(que))     return correo(c);
        if ("apunta".equals(que))     return apuntar(c, titulo, hora);
        if ("estado".equals(que))     return "{\"ok\":" + conPermiso(c)
                                                + ",\"permiso\":\"calendario\""
                                                + ",\"avisosEscuchando\":" + Avisos.escuchando() + "}";
        return citas(c, "proximos".equals(que) ? dias : 1);
    }

    /** Las citas de los próximos `dias`, en JSON listo para leer o pintar. */
    private static String citas(Context c, int dias) {
        if (!conPermiso(c)) {
            return "{\"ok\":false,\"permiso\":\"calendario\",\"dice\":\"No tengo permiso "
                 + "de calendario. Pídemelo otra vez y te lo pido; sin él no sé qué tienes "
                 + "hoy, y no te lo voy a inventar.\"}";
        }
        Calendar desde = Calendar.getInstance();
        desde.set(Calendar.HOUR_OF_DAY, 0);
        desde.set(Calendar.MINUTE, 0);
        desde.set(Calendar.SECOND, 0);
        Calendar hasta = (Calendar) desde.clone();
        hasta.add(Calendar.DAY_OF_YEAR, dias);

        JSONArray lista = new JSONArray();
        try {
            Uri.Builder construccion = CalendarContract.Instances.CONTENT_URI.buildUpon();
            ContentUris.appendId(construccion, desde.getTimeInMillis());
            ContentUris.appendId(construccion, hasta.getTimeInMillis());
            Cursor cur = c.getContentResolver().query(construccion.build(), PROYECCION,
                    null, null, CalendarContract.Instances.BEGIN + " ASC");
            try {
                while (cur != null && cur.moveToNext() && lista.length() < 40) {
                    long inicio = cur.getLong(0);
                    long fin = cur.getLong(1);
                    String nombre = cur.getString(2);
                    Calendar cuando = Calendar.getInstance();
                    cuando.setTimeInMillis(inicio);
                    lista.put(new JSONObject()
                            .put("titulo", nombre == null ? "sin título" : nombre)
                            .put("empieza", inicio)
                            .put("termina", fin)
                            .put("cuando", String.format(Locale.US, "%02d:%02d",
                                    cuando.get(Calendar.HOUR_OF_DAY),
                                    cuando.get(Calendar.MINUTE)))
                            .put("dia", cuando.get(Calendar.DAY_OF_MONTH) + "/"
                                    + (cuando.get(Calendar.MONTH) + 1)));
                }
            } finally {
                if (cur != null) cur.close();
            }
        } catch (Exception elCalendarioNoAbre) {
            return "{\"ok\":false,\"dice\":\"El calendario del teléfono no me deja leerlo "
                 + "(" + esc(elCalendarioNoAbre.toString()) + ").\"}";
        }

        String plazo = dias == 1 ? "hoy" : "en " + dias + " días";
        if (lista.length() == 0) {
            return "{\"ok\":true,\"vacias\":true,\"dias\":" + dias
                 + ",\"eventos\":[],\"dice\":\"No tienes nada " + plazo + ".\"}";
        }
        return "{\"ok\":true,\"vacias\":false,\"dias\":" + dias
             + ",\"total\":" + lista.length() + ",\"eventos\":" + lista.toString()
             + ",\"dice\":\"Tienes " + lista.length() + " cosa"
             + (lista.length() == 1 ? "" : "s") + " " + plazo + ".\"}";
    }

    /**
     * El correo: lo que se puede saber sin entrar en Gmail. Se cuenta lo que
     * `Avisos` oyó del paquete de Gmail y se abre la app. Sin el interruptor de
     * notificaciones, lo dice, en vez de contar ceros.
     */
    private static String correo(Context c) {
        int deGmail = 0;
        if (Avisos.escuchando()) {
            try {
                String oido = Avisos.resumen(12);
                if (oido != null) {
                    String minus = oido.toLowerCase(Locale.US);
                    int desde = 0;
                    while ((desde = minus.indexOf("gmail", desde)) >= 0) {
                        deGmail++;
                        desde += 5;
                    }
                }
            } catch (Exception elOidoTorcido) {
                deGmail = 0;
            }
        }
        String dicho = Avisos.escuchando()
                ? (deGmail == 0 ? "No veo avisos de Gmail en la barra."
                               : "Tienes " + deGmail + " aviso" + (deGmail == 1 ? "" : "s")
                                 + " de Gmail.")
                : "No escucho tus avisos: en Ajustes ▸ Notificaciones ▸ Acceso a "
                  + "notificaciones elige CORT y te lo cuento. Te la abro igual.";
        Intent abre = c.getPackageManager().getLaunchIntentForPackage("com.google.android.gm");
        boolean abrio = false;
        if (abre != null) {
            abre.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            try { c.startActivity(abre); abrio = true; } catch (Exception noPuede) { abrio = false; }
        }
        return "{\"ok\":true,\"gmail\":" + deGmail + ",\"abre\":" + abrio
             + ",\"escuchando\":" + Avisos.escuchando() + ",\"dice\":" + esc(dicho) + "}";
    }

    /** «apunta cena con Samuel el jueves a las 9»: se abre el formulario lleno. */
    private static String apuntar(Context c, String titulo, long hora) {
        Intent nuevo = new Intent(Intent.ACTION_INSERT, CalendarContract.Events.CONTENT_URI);
        if (!titulo.isEmpty()) nuevo.putExtra(CalendarContract.Events.TITLE, titulo);
        if (hora > 0L) nuevo.putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME, hora);
        if (hora > 0L) nuevo.putExtra(CalendarContract.EXTRA_EVENT_ALL_DAY, false);
        nuevo.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            c.startActivity(nuevo);
            return "{\"ok\":true,\"abre\":\"calendario\",\"dice\":\"Te lo abro listo para "
                 + "guardar.\"}";
        } catch (Exception noHayCalendario) {
            return "{\"ok\":false,\"dice\":\"No encuentro la app de calendario de este "
                 + "teléfono.\"}";
        }
    }

    private static String abrirApp(Context c, Uri destino) {
        Intent ver = new Intent(Intent.ACTION_VIEW, destino);
        ver.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            c.startActivity(ver);
            return "{\"ok\":true,\"abre\":\"calendario\"}";
        } catch (Exception noHayCalendario) {
            return "{\"ok\":false,\"dice\":\"Este teléfono no tiene app de calendario que "
                 + "yo pueda abrir.\"}";
        }
    }

    private static String esc(String texto) {
        return "\"" + (texto == null ? "" : texto
                .replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", " ").replace("\r", " ")) + "\"";
    }
}
