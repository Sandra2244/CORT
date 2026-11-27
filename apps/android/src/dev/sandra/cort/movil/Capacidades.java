package dev.sandra.cort.movil;

import java.util.LinkedHashMap;

import org.json.JSONArray;
import org.json.JSONObject;

/** La verdad que la cara Web consume para no ofrecer herramientas de otro aparato. */
final class Capacidades {
    private static final String PLATAFORMA = "android";

    private Capacidades() {}

    static JSONArray todas() {
        LinkedHashMap<String, JSONObject> porId = new LinkedHashMap<>();

        agregar(porId, cap("chat", "Conversación", "A", "existe",
                "Chat completo superpuesto; usa el mismo compositor que el dictado.", "cort-chat-btn"));
        agregar(porId, cap("enfoque", "Modo enfoque", "A", "existe",
                "Conserva orbe, micrófono, centro, chat y parada.", "cort-foco-btn"));
        agregar(porId, cap("voz", "Voz de Android", "A", "existe",
                "Usa el motor de texto a voz instalado; la disponibilidad de una voz concreta depende del teléfono."));
        agregar(porId, completa("micro", "Micrófono y dictado", "B", "parcial",
                "real", new String[] {"RECORD_AUDIO"}, "micrófono", "medio", "usuario", true,
                "hasta 60 segundos por dictado", new String[] {"Motor", "Voz"},
                "Requiere permiso runtime; Vosk es local y el respaldo de Android puede usar red."));
        agregar(porId, completa("wake_word", "Palabra «CORT»", "B", "parcial",
                "real", new String[] {"RECORD_AUDIO", "POST_NOTIFICATIONS"}, "micrófono", "medio",
                "usuario", true, "foreground acotado; consumo de batería", new String[] {"ServicioEscucha"},
                "Escucha «hola/oye CORT» con gramática cerrada. Se corta con pantalla apagada y tras cinco minutos; no es vigilancia 24/7.",
                "cort-wake-btn"));
        agregar(porId, cap("memoria", "Memoria local", "A", "parcial",
                "SQLite v3 conserva hechos, procedencia, confirmación, versiones e historial; borrado reversible local y cambios de interfaz con aprobación de un solo uso. Migración y A16 pendientes de verificar.", "vida-btn"));
        agregar(porId, cap("vida", "Vida diaria", "A", "parcial",
                "Panel local para memoria, alarmas y rutinas. No sincroniza con la nube ni ejecuta rutinas al crearlas; verificación física pendiente.", "vida-btn"));
        agregar(porId, cap("compras", "Lista de compras", "A", "existe",
                "Lista local compartida con el chat.", "shopping-toggle-btn"));
        agregar(porId, cap("apps", "Abrir aplicaciones", "A", "parcial",
                "Usa Intents y la lista de apps visibles que Android permite consultar."));
        agregar(porId, cap("clima", "Clima", "C", "parcial",
                "Requiere red o una fuente compatible; un fallo se informa y no inventa temperatura."));
        agregar(porId, cap("pc_estado", "Estado del equipo", "A", "parcial",
                "Muestra volumen, brillo, batería y recursos disponibles en el teléfono."));
        agregar(porId, cap("navegador", "Abrir navegador", "A", "existe",
                "Abre enlaces http/https en una app compatible mediante ACTION_VIEW.", "browser-btn"));
        agregar(porId, cap("cache", "Limpiar caché Web", "A", "existe",
                "Vacía sólo la caché del WebView; no borra memoria ni modelos.", "clear-cache-btn"));
        agregar(porId, cap("ajustes", "Ajustes", "A", "existe",
                "Preferencias locales, duración de dictado y vista del teléfono.", "settings-button"));
        agregar(porId, cap("comandos", "Comandos", "A", "existe",
                "Catálogo de frases; la ejecución pasa por el plan y la política de CORT.", "commands-btn"));
        agregar(porId, cap("personalidad", "Tono y personalidad", "A", "parcial",
                "Ajustes de tono disponibles; no cambia la voz ni copia personalidades de terceros.", "agent-tone-btn"));
        agregar(porId, cap("wallpapers", "Fondos y orbe", "A", "existe",
                "Recursos visuales locales de CORT.", "menu-wallpaper-btn"));
        agregar(porId, cap("hud_texto", "Subtítulos y HUD de texto", "A", "existe",
                "Muestra la respuesta por streaming de texto.", "subtitle-toggle"));
        agregar(porId, completa("agente_modelos", "Cerebros locales", "A", "parcial",
                "real", new String[] {}, "RAM y almacenamiento suficientes", "medio", "usuario", true,
                "modelos de 100 MB o más", new String[] {"CerebroLocal", "Almacén"},
                "La carga depende de RAM libre y de que el modelo haya bajado con su suma verificada.", "agent-modele-btn"));
        agregar(porId, completa("bolsillo_pc", "Bolsillo de la PC", "B", "parcial",
                "real", new String[] {"INTERNET"}, "PC enlazada", "medio", "usuario", false,
                "red local y token", new String[] {"Puente", "cort_server.py"},
                "Necesita una PC de CORT enlazada; no sustituye una nube pública."));
        agregar(porId, completa("parlamento_pc", "Parlamento con la PC", "B", "parcial",
                "real", new String[] {"INTERNET", "RECORD_AUDIO"}, "auriculares y PC enlazada", "medio",
                "usuario", false, "hasta 20 segundos por turno", new String[] {"Puente", "cort_parlamento.py"},
                "Necesita el puente de PC y enruta el audio según las salidas detectadas."));
        agregar(porId, cap("lectura", "Leer con CORT", "A", "existe",
                "Aparece en el menú de selección de otras apps y lee por el motor de Android."));
        agregar(porId, cap("qr", "Enlace por QR", "A", "existe",
                "Usa la cámara sólo en primer plano y no guarda fotogramas."));
        agregar(porId, cap("equipo", "Ficha del teléfono", "A", "existe",
                "RAM, disco y estado del motor medidos en el aparato."));
        agregar(porId, completa("auriculares", "Botones y salidas de audio", "B", "parcial",
                "real", new String[] {}, "cable, USB o Bluetooth", "bajo", "usuario", true,
                "sin costo adicional", new String[] {"Audifonos"},
                "Detecta salidas y desconexión; la MediaSession de CORT pausa la locución al perder una salida. Android decide la ruta activa y el control de apps externas aún no está implementado."));
        agregar(porId, completa("medios", "Voz y MediaSession", "B", "parcial",
                "real", new String[] {}, "salida de audio compatible", "bajo", "usuario", true,
                "sin costo adicional", new String[] {"Medios", "Voz", "Audifonos"},
                "La MediaSession controla la voz y la lectura de CORT; pausar detiene la locución y reproducir reinicia la última respuesta. Detecta auriculares sin afirmar la ruta activa. No controla aún música de otras apps.", "medios-btn"));
        agregar(porId, completa("sensores", "Sensores y panel de dispositivo", "B", "parcial",
                "real", new String[] {"ACTIVITY_RECOGNITION"}, "sensores presentes", "bajo", "usuario", true,
                "lectura acotada en foreground", new String[] {"Sensores"},
                "Inventario y última lectura en foreground; pasos requiere permiso bajo demanda y línea base. No hay histórico ni sensores en segundo plano.", "sensores-btn"));
        agregar(porId, completa("notificaciones", "Notificaciones de otras apps", "C", "parcial",
                "real", new String[] {"BIND_NOTIFICATION_LISTENER_SERVICE"}, "Android y apps compatibles",
                "alto", "usuario", true, "allowlist de 12 apps y 20 avisos por consulta", new String[] {"Avisos"},
                "Activación manual y allowlist vacía por defecto. Lee título y texto sólo al pulsar; no guarda, registra ni envía avisos ni expone acciones o imágenes.",
                "avisos-btn"));
        agregar(porId, completa("compartir", "Compartir con confirmación", "B", "parcial",
                "real", new String[] {}, "aplicaciones que aceptan texto", "medio", "usuario", true,
                "texto de hasta 4000 caracteres", new String[] {"Compartir", "Aprobaciones"},
                "Prepara el texto exacto y abre ACTION_SEND con createChooser tras una aprobación de 120 segundos. CORT no envía automáticamente ni confirma la entrega.",
                "avisos-btn"));
        agregar(porId, cap("rutinas", "Rutinas", "B", "parcial",
                "Pasos allowlisted, plan visible, aprobación de 120 segundos, ejecución única, historial y cancelación entre pasos. No incluye llamadas, mensajes, compras ni shell; A16 pendiente.", "vida-btn"));
        agregar(porId, cap("alarmas", "Alarmas y recordatorios", "A", "parcial",
                "Entrega alarmas y temporizadores a AlarmClock para confirmación visible y registra sólo la entrega. No lee ni cancela el catálogo del sistema ni pide permisos de alarma exacta; A16 pendiente.", "vida-btn"));
        agregar(porId, cap("proactividad", "Ayuda proactiva", "C", "no implementado",
                "Fase 8: sólo sugerencias acotadas; ninguna acción sensible automática."));
        agregar(porId, completa("camara_gestos", "Cámara y gestos", "B", "no implementado",
                "no disponible", new String[] {"CAMERA"}, "cámara frontal", "medio", "usuario", true,
                "preview visible en foreground", new String[] {},
                "Fase 9: empieza con HUD 2D; no se integrará código AGPL/CC sin revisión de licencia."));
        agregar(porId, completa("asistente_predeterminado", "Asistente predeterminado", "B", "parcial",
                "real", new String[] {"SYSTEM_ALERT_WINDOW", "RECORD_AUDIO"}, "servicios del asistente", "medio", "usuario", true,
                "sin costo adicional", new String[] {"Asistente", "Sesiones", "Reconocimiento"},
                "CORT declara el contrato de asistente, mantiene la vista rápida y entrega reconocimiento; la selección es manual y falta verificar en el A16. No desinstala ni deshabilita a Gemini.",
                "asistente-btn"));
        agregar(porId, cap("nube", "Nube y claves API", "C", "no verificado",
                "El enrutador híbrido se cerrará en la Fase 10; no se ofrece como disponible estable.", "api-keys-button"));
        agregar(porId, cap("actualizacion", "Actualización del APK", "D", "no implementado",
                "La actualización y publicación pertenecen al cierre final autorizado, no a una promesa del panel.", "update-jarvis-btn"));
        agregar(porId, cap("globe_3d", "Globo 3D", "D", "no implementado",
                "Visualización de escritorio; se difiere a la fase PC.", "menu-globe-btn"));
        agregar(porId, cap("holograma", "Holograma", "D", "no implementado",
                "Visualización de escritorio; no se ofrece como panel Android.", "holo-button"));
        agregar(porId, cap("iptv", "Vídeo e IPTV", "C", "no implementado",
                "Requiere fuente y reproductor compatibles; no hay lista ni licencia de canales verificada.", "iptv-toggle-btn"));
        agregar(porId, cap("desinstalador", "Desinstalador", "D", "no implementado",
                "Herramienta de escritorio; Android gestiona la desinstalación desde Ajustes.", "uninstaller-toggle-btn"));
        agregar(porId, cap("winget", "Winget y paquetes", "D", "no implementado",
                "Winget es de Windows.", "winget-toggle-btn"));
        agregar(porId, cap("antivirus", "Antivirus y protección", "D", "no implementado",
                "No hay un escáner privilegiado equivalente en Android estándar; no se simulará una amenaza.", "menu-av-scan-btn", "menu-av-live-btn"));
        agregar(porId, cap("vpn", "Cliente VPN", "C", "no implementado",
                "Requiere un proveedor o configuración compatible; no se promete tunelización universal.", "menu-vpn-btn"));
        agregar(porId, cap("juegos", "Juegos", "D", "no implementado",
                "Catálogo de escritorio; no se integra en Android.", "menu-games-btn"));
        agregar(porId, cap("webcam_pc", "Webcam física de PC", "D", "no implementado",
                "La cámara del teléfono no es una webcam de PC; esta función pertenece a la fase PC.", "webcam-toggle-btn"));
        agregar(porId, completa("domotica", "Domótica", "C", "no implementado",
                "no disponible", new String[] {}, "servidor Home Assistant y token", "alto", "usuario", false,
                "red local y servicio externo", new String[] {},
                "Requiere un servidor configurado; no se incluyen credenciales en el código.", "ha-toggle-btn"));
        agregar(porId, cap("impresion3d", "Impresión 3D", "C", "no implementado",
                "Depende de una impresora y un adaptador compatibles; hoy no hay control verificado.", "print3d-toggle-btn"));
        agregar(porId, cap("obsidiana", "Obsidiana", "C", "no implementado",
                "Depende de una bóveda y permisos de almacenamiento; no se copiará memoria sin decisión de formato y licencia."));
        agregar(porId, cap("teclado_visual", "Teclado visual", "D", "no implementado",
                "Control flotante de escritorio; Android usa su teclado del sistema.", "keyboard-toggle"));
        agregar(porId, cap("jarvis_os", "Jarvis OS", "D", "no implementado",
                "Jarvis OS es un programa de escritorio.", "jarvis-os-toggle-btn"));
        agregar(porId, cap("gpu_boost", "GPU Boost", "D", "no implementado",
                "Ajuste de escritorio; no se promete aceleración privilegiada en Android.", "gpu-button"));
        agregar(porId, cap("nemotron", "Nemotron ASR", "D", "no implementado",
                "Modelo de escritorio; el oído del teléfono es Vosk o el reconocedor de Android.", "nemotron-asr-toggle"));
        agregar(porId, cap("vision_pc", "Visión de PC", "D", "no implementado",
                "La mirada con cámara de PC no existe en el teléfono; los gestos Android serán una capacidad distinta.", "vision-button"));
        agregar(porId, cap("tunel", "Túneles", "D", "no implementado",
                "Herramienta de red de escritorio; no se ofrece en Android."));
        agregar(porId, cap("paquetes", "Paquetes del sistema", "D", "no implementado",
                "Gestión de paquetes de escritorio; Android no expone el mismo control."));

        JSONArray lista = new JSONArray();
        for (JSONObject capacidad : porId.values()) lista.put(capacidad);
        return lista;
    }

    private static JSONObject cap(String id, String etiqueta, String viabilidad, String estado,
                                  String motivo, String... controles) {
        String origen = "existe".equals(estado) || "parcial".equals(estado) ? "real" : "no disponible";
        return completa(id, etiqueta, viabilidad, estado, origen, new String[] {}, "software",
                "bajo".equals(viabilidad) || "A".equals(viabilidad) ? "bajo" : "medio",
                "ninguna", true, "sin costo adicional", new String[] {}, motivo, controles);
    }

    private static JSONObject completa(String id, String etiqueta, String viabilidad, String estado,
                                       String origen, String[] permisos, String hardware, String riesgo,
                                       String confirmacion, boolean offline, String presupuesto,
                                       String[] dependencias, String motivo, String... controles) {
        if (id == null || id.trim().isEmpty()) {
            throw new IllegalArgumentException("el id de una capacidad está vacío");
        }
        if (!("A".equals(viabilidad) || "B".equals(viabilidad)
                || "C".equals(viabilidad) || "D".equals(viabilidad))) {
            throw new IllegalArgumentException("viabilidad desconocida: " + viabilidad);
        }
        JSONObject j = new JSONObject();
        try {
            j.put("id", id);
            j.put("etiqueta", etiqueta);
            j.put("plataforma", PLATAFORMA);
            j.put("viabilidad", viabilidad);
            j.put("estado", estado);
            j.put("origen", origen);
            j.put("permisos", arreglo(permisos));
            j.put("hardware", hardware);
            j.put("riesgo", riesgo);
            j.put("confirmacion", confirmacion);
            j.put("offline", offline);
            j.put("presupuesto", presupuesto);
            j.put("dependencias", arreglo(dependencias));
            j.put("motivo_no_disponible", motivo);
            j.put("controles", arreglo(controles));
        } catch (org.json.JSONException imposible) {
            throw new IllegalStateException(imposible);
        }
        return j;
    }

    private static JSONArray arreglo(String[] valores) {
        JSONArray lista = new JSONArray();
        if (valores != null) for (String valor : valores) lista.put(valor);
        return lista;
    }

    private static void agregar(LinkedHashMap<String, JSONObject> porId, JSONObject capacidad) {
        String id = capacidad.optString("id", "");
        if (porId.containsKey(id)) throw new IllegalArgumentException("id repetido: " + id);
        porId.put(id, capacidad);
    }
}
