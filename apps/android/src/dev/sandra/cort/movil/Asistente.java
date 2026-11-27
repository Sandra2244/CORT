package dev.sandra.cort.movil;

import android.app.role.RoleManager;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import android.service.voice.VoiceInteractionService;

import org.json.JSONObject;

/** El servicio registrado y las rutas manuales para elegir o probar a CORT. */
public class Asistente extends VoiceInteractionService {

    static JSONObject estado(Context contexto) {
        JSONObject j = new JSONObject();
        try {
            j.put("type", "asistente_estado");
            j.put("origen", "real");
            j.put("plataforma", "android");
            j.put("registrado", true);
            j.put("predeterminado", predeterminado(contexto));
            j.put("sesion_activa", Sesion.activa());
            j.put("superposicion", Settings.canDrawOverlays(contexto));
            j.put("coexistencia", "Elegir CORT no desinstala ni deshabilita a Gemini; Android deja volver a cambiarlo.");
            j.put("limite", "Un APK ordinario no se preinstala ni recibe privilegios de asistente del sistema.");
        } catch (org.json.JSONException imposible) {
            throw new IllegalStateException(imposible);
        }
        return j;
    }

    private static Object predeterminado(Context contexto) {
        if (Build.VERSION.SDK_INT < 29) return "lo gestiona Ajustes";
        try {
            RoleManager roles = contexto.getSystemService(RoleManager.class);
            return roles != null && roles.isRoleHeld(RoleManager.ROLE_ASSISTANT);
        } catch (RuntimeException sinAcceso) {
            return "no disponible";
        }
    }

    static void abrirAjustes(Context contexto) {
        String[] rutas = {
                Settings.ACTION_MANAGE_DEFAULT_APPS_SETTINGS,
                Settings.ACTION_VOICE_INPUT_SETTINGS,
                Settings.ACTION_SETTINGS
        };
        for (String ruta : rutas) {
            try {
                contexto.startActivity(new Intent(ruta).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
                return;
            } catch (ActivityNotFoundException noEstaEstaPantalla) {
                // Cada fabricante puede exponer una ruta distinta a Ajustes.
            }
        }
    }

    static void abrirSuperposicion(Context contexto) {
        Intent permiso = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:" + contexto.getPackageName()))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            contexto.startActivity(permiso);
        } catch (ActivityNotFoundException noEstaEstaPantalla) {
            contexto.startActivity(new Intent(Settings.ACTION_SETTINGS)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
        }
    }

    static boolean probar(Context contexto) {
        return VistaRapida.mostrar(contexto);
    }
}
