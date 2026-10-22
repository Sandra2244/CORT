package com.cort.ia;

import android.app.Notification;
import android.content.Context;
import android.os.Bundle;
import android.provider.Settings;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import java.text.SimpleDateFormat;
import java.util.ArrayDeque;
import java.util.Date;
import java.util.Iterator;
import java.util.Locale;

/**
 * El oído de los avisos: lo que le llega al teléfono mientras CORT está en otra
 * parte, CORT lo puede **leer en voz alta** («lee mis mensajes», «qué me llegó»).
 *
 * No es un permiso que el APK pida al instalar: es un interruptor del sistema
 * (Ajustes ▸ Notificaciones ▸ Acceso a notificaciones ▸ CORT) que la dueña da una
 * sola vez. Por eso esta clase se declara en `AndroidManifest.xml` como
 * `<service>` con `android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE"`
 * — sin eso Android ni lo mira — y **no** añade ningún `<uses-permission>`: la
 * lista de permisos del manifiesto sigue siendo la misma cuatro líneas de siempre.
 *
 * WhatsApp no publica una API para leer sus chats, y este corte no la simula: lo
 * que se lee es lo que el propio sistema muestra en la barra, que es exactamente
 * lo que se pidió (que CORT diga qué le llegó). Sin el interruptor dado, `resumen`
 * dice que no escucha en vez de inventarse un mensaje.
 *
 * La memoria es **de un dedo de largo y no toca disco**: doce líneas en la cabeza de
 * este proceso, que se van solas al reiniciar el teléfono. Es a propósito: copiar los
 * chats de la dueña a un archivo los mandaría después a cualquier sitio con la cara
 * conectada al PC por Wi-Fi. Leer y olvidar es la decisión escrita aquí.
 */
public class Avisos extends NotificationListenerService {

    /** Cuántos avisos caben en el oído; el resto se cae por la punta vieja. */
    static final int TOPE = 12;

    /** Cuántos lee `resumen` de una vez cuando nadie dice el número. */
    static final int EN_VOZ_ALTA = 3;

    private static final ArrayDeque<String> OIDO = new ArrayDeque<>();
    private static volatile boolean escuchando;

    private static final Locale ES = Locale.forLanguageTag("es-ES");
    private static final String HORA = "H:mm";

    /**
     * La clave donde Android apunta los escuchadores de avisos que la dueña eligió.
     * Se nombra la cadena tal cual la lee el sistema: `Settings.Secure` no tiene una
     * constante pública para esto en la API mínima del APK (26), y adivinar el nombre
     * de un método de Android cuesta un run rojo — aquí no hay `javac` local, el
     * único compilador real del proyecto es el del runner.
     */
    private static final String LISTENERES = "enabled_notification_listeners";

    @Override
    public void onListenerConnected() {
        escuchando = true;
    }

    @Override
    public void onListenerDisconnected() {
        escuchando = false;
    }

    @Override
    public void onNotificationPosted(StatusBarNotification aviso) {
        if (aviso == null || aviso.isOngoing()) {
            return;                       // un reproductor o un cronómetro no es un mensaje
        }
        Notification cuerpo = aviso.getNotification();
        if (cuerpo == null || (cuerpo.flags & Notification.FLAG_GROUP_SUMMARY) != 0) {
            return;                       // el resumen del grupo duplica lo que dicen sus hijos
        }
        Bundle extras = cuerpo.extras;
        if (extras == null) {
            return;
        }
        String de = deQuien(aviso.getPackageName());
        String asunto = extras.getString(Notification.EXTRA_TITLE);
        String texto = extras.getString(Notification.EXTRA_TEXT);
        String dicho = linea(de, asunto, texto,
                             new SimpleDateFormat(HORA, ES).format(new Date(aviso.getPostTime())));
        if (dicho != null) {
            guarda(dicho);
            /* Ronda 2.4 · la cara se entera EN EL MOMENTO. Las automatizaciones
               («cuando llegue un aviso de WhatsApp, haz X») viven en `automatiza.js`
               y necesitan la señal recién llegada, no cuando la dueña abra la hoja
               Equipo y se lea el resumen. Sin Activity —o con la página cerrada—
               `front()` es `null` y esto no hace nada: el aviso igual se guarda y se
               puede leer después, que es lo que ya hacía CORT.
               `cuadro` hace el favor de ir al hilo de la UI, así que desde el hilo
               del `NotificationListener` se puede llamar tranquilo. */
            try {
                MainActivity cara = MainActivity.front();
                if (cara != null) cara.puente().avisoEnLaCara(de, dicho);
            } catch (Exception laCaraNoEsta) { }
        }
    }

    /* ───────────────────────────── puro: lo que se puede pensar sin teléfono ─────────────────────────── */

    /**
     * La frase que se va a leer, o `null` si el aviso no trae nada que leer.
     * Estática y sin tipos de Android a propósito: es la mitad de esta clase que se
     * puede comprobar en cualquier máquina.
     */
    static String linea(String de, String asunto, String texto, String hora) {
        String asuntoLimpio = limpio(asunto);
        String textoLimpio = limpio(texto);
        if (textoLimpio == null && asuntoLimpio == null) {
            return null;
        }
        StringBuilder sb = new StringBuilder();
        sb.append(de == null ? "algo" : de);
        if (hora != null && !hora.isEmpty()) {
            sb.append(", a las ").append(hora);
        }
        sb.append(": ");
        if (asuntoLimpio != null) {
            sb.append(asuntoLimpio);
            if (textoLimpio != null) {
                sb.append(" dice ").append(textoLimpio);
            }
        } else {
            sb.append(textoLimpio);
        }
        return recorta(sb.toString(), 180);
    }

    /** Deja el oído con la línea nueva al final y sin pasar del TOPE. */
    static void guarda(String dicho) {
        synchronized (OIDO) {
            OIDO.addLast(dicho);
            while (OIDO.size() > TOPE) {
                OIDO.removeFirst();
            }
        }
    }

    /**
     * Lo que va a hablar CORT: los últimos `max`, del más viejo al más nuevo, con su
     * conteo delante. `null` si el oído está vacío: entonces la cara tiene que decir
     * otra cosa, y no un «tus mensajes:» seguido de silencio.
     */
    static String texto(ArrayDeque<String> oido, int max) {
        synchronized (oido) {
            if (oido.isEmpty()) {
                return null;
            }
            int cuantos = Math.min(max, oido.size());
            int seSaltan = oido.size() - cuantos;
            Iterator<String> it = oido.iterator();
            while (it.hasNext() && seSaltan > 0) {
                it.next();
                seSaltan--;
            }
            StringBuilder sb = new StringBuilder();
            sb.append(cuantos == 1 ? "Un aviso: " : "Tus ").append(cuantos).append(" avisos: ");
            boolean primero = true;
            while (it.hasNext()) {
                if (!primero) {
                    sb.append(". ");
                }
                sb.append(recorta(it.next(), 180));
                primero = false;
            }
            return sb.append(".").toString();
        }
    }

    static int cuantos() {
        synchronized (OIDO) {
            return OIDO.size();
        }
    }

    static void vaciar() {
        synchronized (OIDO) {
            OIDO.clear();
        }
    }

    /* ─────────────────────────────────── Android ─────────────────────────────────── */

    /** El resumen hablado, con la frase de puertas cerradas si no hay nada que leer. */
    public static String resumen(int max) {
        String dicho = texto(OIDO, max);
        if (dicho != null) {
            return dicho;
        }
        return "No tengo nada oído"
             + (escuchando ? " desde que abriste CORT."
                           : ". Todavía no escucho tus avisos: en Ajustes ▸ Notificaciones ▸ "
                           + "Acceso a notificaciones elige CORT.");
    }

    public static boolean escuchando() {
        return escuchando;
    }

    /**
     * Si la dueña ya le dio el interruptor al sistema. Se lee en `Settings.Secure`
     * porque es donde Android apunta a los escuchadores elegidos, y el paquete tiene
     * que salir en esa lista: sin esto CORT diría «tus 3 avisos» con el oído cerrado.
     */
    public static boolean activado(Context contexto) {
        String lista = Settings.Secure.getString(contexto.getContentResolver(), LISTENERES);
        return lista != null && lista.contains(contexto.getPackageName());
    }

    /**
     * El nombre que se dice en voz alta. `PackageManager.getApplicationLabel` daría el
     * nombre bonito del sistema, pero lanza `NameNotFoundException` y obligaría a
     * traer otro diccionario de AOSP para una palabra: con las marcas conocidas y el
     * último tramo del paquete basta, y así lo puede releer cualquiera en este archivo.
     */
    static String deQuien(String paquete) {
        if (paquete == null || paquete.isEmpty()) {
            return "algo";
        }
        String bajo = paquete.toLowerCase(Locale.ROOT);
        if (bajo.contains("whatsapp")) {
            return "WhatsApp";
        }
        if (bajo.contains("messenger")) {
            return "Messenger";
        }
        if (bajo.contains("instagram")) {
            return "Instagram";
        }
        if (bajo.contains("facebook")) {
            return "Facebook";
        }
        if (bajo.contains("gmail")) {
            return "Gmail";
        }
        if (bajo.contains("telegram")) {
            return "Telegram";
        }
        if (bajo.contains("signal")) {
            return "Signal";
        }
        if (bajo.contains("android.system")) {
            return "el sistema";
        }
        int corte = paquete.lastIndexOf('.');
        return corte > 0 && corte < paquete.length() - 1 ? paquete.substring(corte + 1) : paquete;
    }

    private static String limpio(String texto) {
        if (texto == null) {
            return null;
        }
        String dicho = texto.replace('\n', ' ').trim();
        return dicho.isEmpty() ? null : dicho;
    }

    private static String recorta(String texto, int tope) {
        return texto.length() <= tope ? texto : texto.substring(0, tope - 1) + "…";
    }
}
