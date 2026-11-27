package dev.sandra.cort.movil;

import android.app.Activity;
import android.app.KeyguardManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.provider.Settings;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.TreeSet;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

public final class Avisos extends NotificationListenerService {
    private static final String PREFERENCIAS = "cort-avisos";
    private static final String CLAVE_PAQUETES = "paquetes_permitidos";
    private static final int MAX_APPS = 12;
    private static final int MAX_AVISOS = 20;
    private static volatile Avisos instancia;

    @Override
    public void onListenerConnected() {
        instancia = this;
    }

    @Override
    public void onListenerDisconnected() {
        if (instancia == this) instancia = null;
    }

    @Override
    public void onNotificationPosted(StatusBarNotification aviso) {
    }

    @Override
    public void onNotificationRemoved(StatusBarNotification aviso) {
    }

    static JSONObject estado(Context contexto) {
        boolean habilitado = listenerHabilitado(Settings.Secure.getString(
                contexto.getContentResolver(), "enabled_notification_listeners"),
                new ComponentName(contexto, Avisos.class).flattenToString());
        boolean conectado = instancia != null;
        boolean bloqueado = ((KeyguardManager) contexto.getSystemService(Context.KEYGUARD_SERVICE))
                .isKeyguardLocked();
        JSONArray paquetes = new JSONArray(allowlist(contexto));
        String motivo = !habilitado ? "Activa el acceso de CORT en Ajustes."
                : !conectado ? "Android todavía no ha conectado el listener."
                : paquetes.length() == 0 ? "No hay aplicaciones permitidas."
                : bloqueado ? "El contenido no se lee con la pantalla bloqueada."
                : "Lectura disponible sólo bajo demanda.";
        try {
            return new JSONObject().put("type", "avisos_estado").put("origen", "real")
                    .put("habilitado", habilitado).put("conectado", conectado)
                    .put("bloqueado", bloqueado).put("paquetes", paquetes)
                    .put("motivo", motivo).put("limite", limite());
        } catch (JSONException imposible) {
            throw new IllegalStateException(imposible);
        }
    }

    static JSONObject leer(Context contexto) throws JSONException {
        Avisos servicio = instancia;
        boolean habilitado = listenerHabilitado(Settings.Secure.getString(
                contexto.getContentResolver(), "enabled_notification_listeners"),
                new ComponentName(contexto, Avisos.class).flattenToString());
        Set<String> permitidas = allowlist(contexto);
        boolean bloqueado = ((KeyguardManager) contexto.getSystemService(Context.KEYGUARD_SERVICE))
                .isKeyguardLocked();
        if (!habilitado || servicio == null || permitidas.isEmpty() || bloqueado) {
            return new JSONObject().put("type", "avisos_lista").put("origen", "real")
                    .put("ok", false).put("avisos", new JSONArray())
                    .put("motivo", estado(contexto).optString("motivo", "Lectura no disponible"))
                    .put("limite", limite());
        }
        StatusBarNotification[] activas = servicio.getActiveNotifications();
        JSONArray visibles = new JSONArray();
        PackageManager paquetes = contexto.getPackageManager();
        for (StatusBarNotification activa : activas) {
            if (!permitidas.contains(activa.getPackageName())) continue;
            String aplicacion = activa.getPackageName();
            try {
                ApplicationInfo info = paquetes.getApplicationInfo(activa.getPackageName(), 0);
                aplicacion = textoLimitado(info.loadLabel(paquetes), 120);
            } catch (PackageManager.NameNotFoundException | RuntimeException sinApp) {
                aplicacion = activa.getPackageName();
            }
            visibles.put(new JSONObject().put("id", activa.getPackageName() + ":" + activa.getId())
                    .put("paquete", activa.getPackageName()).put("aplicacion", aplicacion)
                    .put("titulo", textoLimitado(activa.getNotification().extras
                            .getCharSequence(android.app.Notification.EXTRA_TITLE), 160))
                    .put("texto", textoLimitado(activa.getNotification().extras
                            .getCharSequence(android.app.Notification.EXTRA_TEXT), 500))
                    .put("momento", activa.getPostTime()).put("en_curso", activa.isOngoing()));
            if (visibles.length() >= MAX_AVISOS) break;
        }
        return new JSONObject().put("type", "avisos_lista").put("origen", "real")
                .put("ok", true).put("avisos", visibles).put("limite", limite());
    }

    static JSONObject appsVisibles(Context contexto) throws JSONException {
        PackageManager pm = contexto.getPackageManager();
        Intent lanzador = new Intent(Intent.ACTION_MAIN);
        lanzador.addCategory(Intent.CATEGORY_LAUNCHER);
        List<android.content.pm.ResolveInfo> resueltas = pm.queryIntentActivities(lanzador, 0);
        List<JSONObject> apps = new ArrayList<>();
        Set<String> vistos = new HashSet<>();
        for (android.content.pm.ResolveInfo resuelta : resueltas) {
            String nombre = resuelta.activityInfo.packageName;
            if (nombre == null || contexto.getPackageName().equals(nombre) || !vistos.add(nombre)) continue;
            String etiqueta = nombre;
            try {
                etiqueta = textoLimitado(resuelta.loadLabel(pm), 120);
            } catch (RuntimeException sinEtiqueta) {
                etiqueta = nombre;
            }
            apps.add(new JSONObject().put("paquete", nombre).put("nombre", etiqueta));
            if (apps.size() >= 80) break;
        }
        Collections.sort(apps, (a, b) -> a.optString("nombre").toLowerCase(Locale.ROOT)
                .compareTo(b.optString("nombre").toLowerCase(Locale.ROOT)));
        return new JSONObject().put("type", "avisos_apps").put("origen", "real")
                .put("apps", new JSONArray(apps)).put("paquetes", new JSONArray(allowlist(contexto)));
    }

    static JSONObject guardarAllowlist(Context contexto, JSONArray datos) throws JSONException {
        Set<String> elegidas = new TreeSet<>();
        String problema = null;
        if (datos == null || datos.length() > MAX_APPS) {
            problema = "la lista debe tener como máximo 12 aplicaciones";
        } else {
            for (int i = 0; i < datos.length(); i++) {
                String paquete = datos.optString(i, "").trim();
                if (!paqueteValido(paquete)) {
                    problema = "hay un nombre de paquete no válido";
                    break;
                }
                elegidas.add(paquete);
            }
        }
        if (problema == null) {
            contexto.getSharedPreferences(PREFERENCIAS, Context.MODE_PRIVATE).edit()
                    .putStringSet(CLAVE_PAQUETES, elegidas).apply();
        }
        return new JSONObject().put("type", "avisos_allowlist").put("origen", "real")
                .put("ok", problema == null).put("motivo", problema == null
                        ? "Lista de aplicaciones actualizada." : problema)
                .put("paquetes", new JSONArray(allowlist(contexto)));
    }

    static void abrirAjustes(Activity actividad) {
        try {
            actividad.startActivity(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS));
        } catch (RuntimeException sinAjustes) {
            try {
                actividad.startActivity(new Intent(Settings.ACTION_SETTINGS));
            } catch (RuntimeException sinAjustesGenerales) {
            }
        }
    }

    private static Set<String> allowlist(Context contexto) {
        SharedPreferences prefs = contexto.getSharedPreferences(PREFERENCIAS, Context.MODE_PRIVATE);
        Set<String> salida = new TreeSet<>();
        for (String paquete : prefs.getStringSet(CLAVE_PAQUETES, Collections.emptySet())) {
            if (paqueteValido(paquete)) salida.add(paquete);
        }
        return salida;
    }

    static boolean listenerHabilitado(String lista, String componente) {
        if (lista == null || componente == null || componente.isEmpty()) return false;
        for (String entrada : lista.split(":")) {
            if (componente.equals(entrada.trim())) return true;
        }
        return false;
    }

    static boolean paqueteValido(String paquete) {
        return paquete != null && paquete.length() <= 160
                && paquete.matches("[A-Za-z_][A-Za-z0-9_]*(?:\\.[A-Za-z_][A-Za-z0-9_]*)+");
    }

    static String textoLimitado(CharSequence valor, int maximo) {
        if (valor == null) return "";
        StringBuilder limpio = new StringBuilder();
        boolean espacio = false;
        for (int i = 0; i < valor.length() && limpio.length() < maximo; i++) {
            char c = valor.charAt(i);
            if (Character.isISOControl(c) || Character.isWhitespace(c)) {
                espacio = limpio.length() > 0;
                continue;
            }
            if (espacio) limpio.append(' ');
            espacio = false;
            limpio.append(c);
        }
        return limpio.toString().trim();
    }

    private static String limite() {
        return "Máximo 20 avisos activos por consulta. No se guardan, no se envían a la nube "
                + "ni se exponen acciones, imágenes o respuestas de otras aplicaciones.";
    }
}
