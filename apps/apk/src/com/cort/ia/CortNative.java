package com.cort.ia;

import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.speech.tts.Voice;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import java.util.ArrayList;
import java.util.Locale;
import java.util.Set;

/**
 * El puente entre la interfaz (JavaScript, en `ui/`) y el aparato (Java).
 *
 * Viaja como `window.CortNative`, y su contrato lo fija el lado de la
 * interfaz, que ya estaba escrito antes de este archivo: `ui/js/voice.js` llama
 * a `listen(lang, modo)`, `stopListening()`, `cancelListening()`,
 * `speak(texto, id, voz, tono, velocidad)`, `stopSpeaking()`, `voices()`,
 * `available()`, `hasPermission(k)` y `requestPermission(k)`, y `ui/js/hud.js`
 * llama a `bgStatus()`, `setBackground(on)` y `keepAwake(on)`. Los eventos
 * vuelven por `window.__cortNative.emit({...})` con los mismos tipos que la
 * Web Speech API del navegador (`stt-start`, `stt-speech`, `stt-level`,
 * `stt-partial`, `stt-final`, `stt-error`, `stt-end`, `tts-start`, `tts-end`,
 * `perm`), así que la cara no tiene dos versiones de sí misma.
 *
 * Por qué hace falta un puente y no basta el WebView: por Wi‑Fi la página viaja
 * en `http`, que no es origen seguro, y Chrome no presta ni `getUserMedia` ni
 * `SpeechRecognition` fuera de un origen seguro. Aquí el micrófono y la voz los
 * pone Android: `SpeechRecognizer` y `TextToSpeech` del propio teléfono, gratis
 * y sin red.
 *
 * Hilos: los métodos `@JavascriptInterface` corren en el hilo del puente de
 * WebView, y `SpeechRecognizer` **exige** hilo con `Looper`. Por eso casi todo
 * se mete en `act.runOnUiThread(...)`: llamar el reconocedor desde el hilo
 * equivocado es un fallo que sólo aparece en el teléfono.
 */
public class CortNative {

    private final MainActivity act;

    private SpeechRecognizer stt;
    private volatile boolean sttVivo = false;

    private TextToSpeech tts;
    private volatile boolean ttsListo = false;
    private final ArrayList<String[]> ttsPendiente = new ArrayList<>();

    /**
     * El modo juego, en **estático** porque lo leen dos sitios que no viven en
     * esta clase: `Reproductor.pideFoco()` (para no pedir el foco) y
     * `Reproductor.estadoJson()` (para pintar el interruptor). `volatile` porque
     * lo escribe el hilo del puente de WebView y lo leen el hilo de la interfaz y
     * el del `OnPreparedListener` del `MediaPlayer`.
     */
    private static volatile boolean juego = false;

    public CortNative(MainActivity actividad) {
        this.act = actividad;
        // El modo juego sobrevive a que se cierre la app: si la última partida
        // terminó con el interruptor puesto, CORT no debe reabrir el micro ni
        // reclamar el foco al arrancar. La preferencia es la verdad; la bandera,
        // su copia rápida.
        juego = actividad.prefs().getBoolean("juego", false);
        act.runOnUiThread(() -> {
            tts = new TextToSpeech(act, estado -> {
                if (estado == TextToSpeech.SUCCESS) {
                    tts.setOnUtteranceProgressListener(progreso);
                    eligeIdioma();
                    ttsListo = true;
                    sueltaPendiente();
                } else {
                    ttsListo = false;
                }
            });
        });
    }

    /* ─────────────────────────── oído ─────────────────────────── */

    @JavascriptInterface
    public void listen(final String lang, final String modo) {
        act.runOnUiThread(() -> arrancarEscucha(lang, modo));
    }

    /** Lo mismo, pero desde Java: el doble toque del auricular y el asistente. */
    void escuchaAhora() {
        act.runOnUiThread(() -> arrancarEscucha("es-MX", "cmd"));
    }

    private void arrancarEscucha(String lang, String modo) {
        // Modo juego: ni micro abierto. `pausa()` ya mandó `pause` a la cara, así
        // que voice.js no va a rearmar; estos dos eventos son sólo para que el orbe
        // no se quede pintando «escuchando» cuando no se está escuchando nada. El
        // error se reporta como `abort` y **no** como `not-allowed` a propósito:
        // `voice.js` apaga la palabra de activación al ver «not-allowed», y apagarla
        // por un capricho del interruptor sería dejarla muda para siempre.
        if (juego) {
            cuadro("{\"type\":\"stt-error\",\"error\":\"abort\"}");
            cuadro("{\"type\":\"stt-end\"}");
            return;
        }
        if (!permiso("mic")) {
            cuadro("{\"type\":\"stt-error\",\"error\":\"not-allowed\"}");
            cuadro("{\"type\":\"stt-end\"}");
            pedir("mic");
            return;
        }
        if (stt == null) {
            stt = SpeechRecognizer.createSpeechRecognizer(act);
            stt.setRecognitionListener(escucha);
        }
        Intent i = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                   RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        i.putExtra(RecognizerIntent.EXTRA_LANGUAGE, lang == null || lang.isEmpty() ? "es-MX" : lang);
        i.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
        i.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);
        i.putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, act.getPackageName());
        sttVivo = true;
        try {
            stt.startListening(i);
            cuadro("{\"type\":\"stt-start\",\"modo\":" + comilla(modo) + "}");
        } catch (Exception noHayServicioDeVoz) {
            sttVivo = false;
            cuadro("{\"type\":\"stt-error\",\"error\":\"service-not-allowed\"}");
            cuadro("{\"type\":\"stt-end\"}");
        }
    }

    @JavascriptInterface
    public void stopListening() {
        act.runOnUiThread(() -> { if (stt != null) stt.stopListening(); });
    }

    @JavascriptInterface
    public void cancelListening() {
        act.runOnUiThread(() -> {
            sttVivo = false;
            if (stt != null) stt.cancel();
        });
    }

    private final RecognitionListener escucha = new RecognitionListener() {
        @Override public void onReadyForSpeech(Bundle extras) {
            cuadro("{\"type\":\"stt-speech\"}");
        }
        @Override public void onBeginningOfSpeech() {
            cuadro("{\"type\":\"stt-speech\"}");
        }
        @Override public void onRmsChanged(float rmsDb) {
            float v = (rmsDb + 2f) / 12f;
            if (v < 0f) v = 0f;
            if (v > 1f) v = 1f;
            cuadro("{\"type\":\"stt-level\",\"level\":" + v + "}");
        }
        @Override public void onBufferReceived(byte[] buffer) { /* el modelo no lo pide */ }
        @Override public void onEndOfSpeech() { /* llega el resultado justo después */ }
        @Override public void onError(int error) {
            sttVivo = false;
            cuadro("{\"type\":\"stt-error\",\"error\":" + comilla(nombreError(error)) + "}");
            cuadro("{\"type\":\"stt-end\"}");
        }
        @Override public void onResults(Bundle resultados) {
            sttVivo = false;
            finalista(resultados, true);
        }
        @Override public void onPartialResults(Bundle resultados) {
            finalista(resultados, false);
        }
        @Override public void onEvent(int eventType, Bundle params) { /* sin uso */ }
    };

    private void finalista(Bundle resultados, boolean final_) {
        if (resultados == null) {
            cuadro("{\"type\":\"stt-end\"}");
            return;
        }
        ArrayList<String> partes =
            resultados.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if (partes == null || partes.isEmpty()) {
            if (final_) cuadro("{\"type\":\"stt-end\"}");
            return;
        }
        StringBuilder alts = new StringBuilder();
        for (int n = 0; n < partes.size(); n++) {
            if (n > 0) alts.append(',');
            alts.append(comilla(partes.get(n)));
        }
        cuadro("{\"type\":\"" + (final_ ? "stt-final" : "stt-partial")
               + "\",\"text\":" + comilla(partes.get(0))
               + ",\"alts\":[" + alts + "]}");
        if (final_) cuadro("{\"type\":\"stt-end\"}");
    }

    /** Los códigos de Android traducidos a los nombres que entiende `voice.js`. */
    private static String nombreError(int error) {
        switch (error) {
            case SpeechRecognizer.ERROR_NETWORK:
            case SpeechRecognizer.ERROR_SERVER:
            case SpeechRecognizer.ERROR_CLIENT:
                return "network";
            case SpeechRecognizer.ERROR_NO_MATCH:
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT:
                return "no-speech";
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS:
                return "not-allowed";
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY:
                return "busy";
            default:
                return "abort";
        }
    }

    /* ──────────────────────────── voz ─────────────────────────── */

    @JavascriptInterface
    public void speak(final String texto, final String id, final String voz,
                      final double tono, final double velocidad) {
        final String uid = (id == null || id.isEmpty()) ? "u0" : id;
        act.runOnUiThread(() -> {
            if (!ttsListo || tts == null) {
                // El motor de voz aún está despertando: la frase se guarda y se
                // suelta al estar lista, para que CORT no pierda el saludo de arranque.
                ttsPendiente.add(new String[] { texto, uid, voz,
                                                 String.valueOf(tono), String.valueOf(velocidad) });
                return;
            }
            dice(texto, uid, voz, tono, velocidad);
        });
    }

    private void dice(String texto, String uid, String voz, double tono, double velocidad) {
        if (texto == null || texto.trim().isEmpty()) {
            cuadro("{\"type\":\"tts-end\",\"id\":" + comilla(uid) + "}");
            return;
        }
        eligeIdioma();
        if (voz != null && !voz.isEmpty()) ponVoz(voz);
        try {
            tts.setPitch((float) Math.max(0.5, Math.min(2.0, tono == 0 ? 0.82 : tono)));
            tts.setSpeechRate((float) Math.max(0.5, Math.min(2.0, velocidad == 0 ? 1.0 : velocidad)));
        } catch (Exception sigueConLaVozDeSiempre) { /* nada */ }
        Bundle sinExtras = new Bundle();
        tts.speak(texto, TextToSpeech.QUEUE_ADD, sinExtras, uid);
    }

    private void sueltaPendiente() {
        ArrayList<String[]> cola = new ArrayList<>(ttsPendiente);
        ttsPendiente.clear();
        for (String[] pedido : cola) {
            double tono = 0.82, vel = 1.0;
            try { tono = Double.parseDouble(pedido[3]); vel = Double.parseDouble(pedido[4]); }
            catch (NumberFormatException malaMedida) { /* valores de siempre */ }
            dice(pedido[0], pedido[1], pedido[2], tono, vel);
        }
    }

    @JavascriptInterface
    public void stopSpeaking() {
        act.runOnUiThread(() -> {
            ttsPendiente.clear();
            if (tts != null) tts.stop();
        });
    }

    private final UtteranceProgressListener progreso = new UtteranceProgressListener() {
        @Override public void onStart(String utteranceId) {
            cuadro("{\"type\":\"tts-start\",\"id\":" + comilla(utteranceId) + "}");
        }
        @Override public void onDone(String utteranceId) {
            cuadro("{\"type\":\"tts-end\",\"id\":" + comilla(utteranceId) + "}");
        }
        @Override public void onError(String utteranceId) {
            cuadro("{\"type\":\"tts-end\",\"id\":" + comilla(utteranceId) + "}");
        }
    };

    private void eligeIdioma() {
        if (tts == null) return;
        int resultado = tts.setLanguage(new Locale("es", "MX"));
        if (resultado == TextToSpeech.LANG_MISSING_DATA
            || resultado == TextToSpeech.LANG_NOT_SUPPORTED) {
            tts.setLanguage(new Locale("es"));
        }
    }

    private void ponVoz(String nombre) {
        if (tts == null) return;
        try {
            Set<Voice> disponibles = tts.getVoices();
            for (Voice v : disponibles) {
                // `Voice` sólo promete `getName()` (API 21); no existe un método que
                // diga si la voz está borrada, así que el nombre es la única guía.
                if (nombre.equals(v.getName())) {
                    tts.setVoice(v);
                    return;
                }
            }
        } catch (Exception sinListaDeVoces) {
            // Algunos fabricantes no exponen `getVoices()`; se habla con la voz del sistema.
        }
    }

    @JavascriptInterface
    public String voices() {
        StringBuilder j = new StringBuilder("{\"voices\":[");
        boolean primero = true;
        try {
            Set<Voice> disponibles = tts == null ? null : tts.getVoices();
            if (disponibles != null) {
                for (Voice v : disponibles) {
                    Locale l = v.getLocale();
                    if (l == null || !l.getLanguage().equalsIgnoreCase("es")) continue;
                    if (!primero) j.append(',');
                    primero = false;
                    j.append("{\"name\":").append(comilla(v.getName()))
                     .append(",\"locale\":").append(comilla(l.toLanguageTag()))
                     .append(",\"local\":").append(!v.isNetworkConnectionRequired())
                     .append(",\"male\":").append(esMasculino(v.getName()));
                }
            }
        } catch (Exception sinListaDeVoces) { /* lista vacía: la interfaz usa la voz del sistema */ }
        return j.append("],\"default\":\"\"}").toString();
    }

    private static boolean esMasculino(String nombre) {
        String n = nombre.toLowerCase(Locale.US);
        boolean hombre = n.contains("male") || n.contains("jorge") || n.contains("diego")
            || n.contains("pablo") || n.contains("raúl") || n.contains("carlos");
        return hombre && !n.contains("female");
    }

    @JavascriptInterface
    public String available() {
        return "{\"stt\":" + SpeechRecognizer.isRecognitionAvailable(act)
               + ",\"tts\":" + ttsListo + "}";
    }

    /* ───────────────────── permisos y ajustes ──────────────────── */

    @JavascriptInterface
    public boolean hasPermission(String kind) {
        return permiso(kind);
    }

    @JavascriptInterface
    public boolean requestPermission(String kind) {
        pedir(kind);
        return true;
    }

    private boolean permiso(String kind) {
        if (kind == null) return false;
        String k = kind.toLowerCase(Locale.US);
        if (k.equals("mic") || k.equals("micro") || k.equals("audio")) {
            return act.checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)
                   == PackageManager.PERMISSION_GRANTED;
        }
        if (k.startsWith("camara") || k.startsWith("camera")) {
            return act.checkSelfPermission(android.Manifest.permission.CAMERA)
                   == PackageManager.PERMISSION_GRANTED;
        }
        // Lo que la cara pregunta antes de prometer una canción o un contacto:
        // `hasPermission('medios')`, `hasPermission('contactos')`, `hasPermission('avisos')`.
        if (k.startsWith("medios") || k.startsWith("music") || k.startsWith("archiv")) {
            return Musica.puedeLeer(act);
        }
        if (k.startsWith("contacto") || k.startsWith("marcar") || k.startsWith("llam")) {
            return act.checkSelfPermission(android.Manifest.permission.READ_CONTACTS)
                   == PackageManager.PERMISSION_GRANTED;
        }
        if (k.startsWith("aviso") || k.startsWith("notific")) {
            // Android 13 es el único que pregunta; antes la notificación existe sin permiso.
            if (android.os.Build.VERSION.SDK_INT < 33) return true;
            return act.checkSelfPermission("android.permission.POST_NOTIFICATIONS")
                   == PackageManager.PERMISSION_GRANTED;
        }
        return true;
    }

    private void pedir(String kind) {
        act.pidePermiso(kind);
    }

    /** Lo llama `MainActivity.onRequestPermissionsResult`. */
    void permisoRespondido(String kind, boolean concedido) {
        cuadro("{\"type\":\"perm\",\"kind\":" + comilla(kind)
               + ",\"granted\":" + concedido + "}");
    }

    @JavascriptInterface
    public void openAppSettings() {
        act.runOnUiThread(() -> {
            try {
                Intent ajustes = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                                            Uri.fromParts("package", act.getPackageName(), null));
                ajustes.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                act.startActivity(ajustes);
            } catch (Exception noHayComoAbrirLosAjustes) {
                act.avisa("No se pudieron abrir los ajustes de la app");
            }
        });
    }

    /** Atajo para «poner CORT como asistente» desde el propio holograma. */
    @JavascriptInterface
    public void openAssistantSettings() {
        act.abreAjustesDeAsistente();
    }

    /* ─────────────────── pantalla, fondo y PC de red ────────────── */

    @JavascriptInterface
    public String bgStatus() {
        SharedPreferences p = act.prefs();
        return "{\"bg\":" + p.getBoolean("bg", false)
               + ",\"pc\":" + comilla(p.getString("pc", "")) + "}";
    }

    @JavascriptInterface
    public void setBackground(boolean on) {
        act.prefs().edit().putBoolean("bg", on).apply();
    }

    @JavascriptInterface
    public void keepAwake(final boolean on) {
        act.runOnUiThread(() -> {
            if (on) act.getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
            else    act.getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        });
    }

    /** La interfaz puede pedir que el WebView salte al PC sin usar el botón. */
    @JavascriptInterface
    public void setPc(final String url) {
        act.guardarPC(url);
    }

    /* ─────────────────── qué está pasando en el aparato ─────────────────── */

    /**
     * ¿Suena música ahora mismo? Lo pregunta `ui/js/voice.js` antes de reabrir el
     * micrófono de «Oye CORT».
     *
     * En Android abrir el micro **duckea** lo demás (baja el volumen de la música)
     * y en un teléfono de gama media además lo traba: rearma tras rearma,
     * sesión tras sesión. Con esto, mientras la dueña escucha algo, CORT cierra el
     * oído y lo reabre cuando el audio termina.
     *
     * El detalle honesto: `isMusicActive()` también es `true` mientras CORT habla
     * por `TextToSpeech` (el TTS va por el stream de multimedia). Por eso la cara
     * ignora el freno durante el primer segundo y medio después de cada frase —
     * sin ese margen, CORT se quedaría muda justo después de responderte.
     */
    @JavascriptInterface
    public boolean musicPlaying() {
        Object servicio = act.getSystemService(android.content.Context.AUDIO_SERVICE);
        if (!(servicio instanceof android.media.AudioManager)) return false;
        try {
            return ((android.media.AudioManager) servicio).isMusicActive();
        } catch (Exception elSistemaNoContesta) {
            return false;
        }
    }

    /**
     * Si CORT puede ser el asistente y si ya lo es. La cara lo pregunta para no
     * prometer un botón que el teléfono no va a cumplir.
     *
     * El rol de asistente es API 29 (Android 10); con `minSdk` 26 hay que
     * comprobar la versión antes de tocar `RoleManager`, y devolver `rol:false`
     * para que la interfaz diga «elígeme a mano en Ajustes» en los antiguos.
     */
    @JavascriptInterface
    public String assistantState() {
        boolean hayRol = android.os.Build.VERSION.SDK_INT >= 29;
        boolean puede = false, tiene = false;
        if (hayRol) {
            try {
                Object servicio = act.getSystemService(android.content.Context.ROLE_SERVICE);
                if (servicio instanceof android.app.role.RoleManager) {
                    android.app.role.RoleManager roles = (android.app.role.RoleManager) servicio;
                    puede = roles.isRoleAvailable(android.app.role.RoleManager.ROLE_ASSISTANT);
                    tiene = roles.isRoleHeld(android.app.role.RoleManager.ROLE_ASSISTANT);
                }
            } catch (Exception eseFabricanteNoTieneRoles) { /* quedan los false */ }
        }
        return "{\"rol\":" + hayRol + ",\"puede\":" + puede + ",\"esAsistente\":" + tiene + "}";
    }

    /* ──────────────────────────────── avisos ─────────────────────────────── */

    /**
     * Lo que la cara pregunta con «lee mis mensajes» / «qué me llegó».
     *
     * Devuelve JSON y **no habla**: quien habla es `speak`, así que la frase sale
     * por la misma boca que el resto de CORT y con la voz que la dueña eligió en
     * 07 · Perfil. `total`, `escuchando` y `activado` van dentro porque la cara
     * necesita los tres para no prometer un aviso inventado: `activado` es el
     * interruptor del sistema, y sin él `texto` ya dice cómo se da.
     */
    @JavascriptInterface
    public String avisos(final int cuantos) {
        int n = cuantos <= 0 ? Avisos.EN_VOZ_ALTA : Math.min(cuantos, Avisos.TOPE);
        return "{\"texto\":" + comilla(Avisos.resumen(n))
               + ",\"total\":" + Avisos.cuantos()
               + ",\"escuchando\":" + Avisos.escuchando()
               + ",\"activado\":" + Avisos.activado(act)
               + "}";
    }

    /** Para que la cara pueda decir «olvida lo que leí». */
    @JavascriptInterface
    public void vaciarAvisos() {
        Avisos.vaciar();
    }

    /**
     * La pantalla del interruptor. La acción se nombra como **cadena literal** y se
     * prueban dos rutas con su respaldo: el enlace exacto cambia entre fabricantes y
     * versiones de Android, y en este repo no hay `javac` local — si una constante no
     * existe donde dice el manual, el único que se entera es el runner, un run después.
     */
    @JavascriptInterface
    public void abreAjustesAvisos() {
        act.runOnUiThread(() -> {
            String[] rutas = {
                "android.settings.ACTION_NOTIFICATION_LISTENER_SETTINGS",
                "android.settings.NOTIFICATION_LISTENER_SETTINGS",
            };
            for (String ruta : rutas) {
                try {
                    act.startActivity(new Intent(ruta).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
                    return;
                } catch (Exception noEstaEnEseFabricante) { /* prueba la siguiente */ }
            }
            try {
                act.startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                                             Uri.fromParts("package", act.getPackageName(), null))
                                      .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
                act.avisa("Entra en Notificaciones y dame el acceso, o elige la app CORT a mano");
            } catch (Exception tampocoHayAjustes) {
                act.avisa("Ajustes ▸ Notificaciones ▸ Acceso a notificaciones ▸ CORT");
            }
        });
    }

    /** Habla desde Java (el menú del botón «CORT · PC»), por el mismo camino que `speak`. */
    void diAlto(String texto) {
        act.runOnUiThread(() -> {
            if (ttsListo && tts != null) {
                dice(texto, "aviso", "", 0.82, 1.0);
                return;
            }
            ttsPendiente.add(new String[] { texto, "aviso", "", "0.82", "1.0" });
        });
    }

    /** Lo llama el menú: leer los avisos en voz sin pasar por la página. */
    void leeAvisos() {
        diAlto(Avisos.resumen(Avisos.EN_VOZ_ALTA));
    }

    /* ─────────────────── el reproductor de CORT ─────────────────── */

    /**
     * La música y el video que **ya están** en el teléfono, el reproductor propio
     * (`.Reproductor`, que es un servicio con su notificación) y lo que CORT sabe
     * de los gustos de la dueña (`.Musica`, una cuenta por artista y por género).
     *
     * Dos cosas que conviene tener claras leyendo esto:
     *
     * · Los métodos que devuelven JSON corren en el hilo del puente, **no** en el
     *   de la interfaz. Es a propósito: preguntarle 400 filas al índice del
     *   sistema tarda lo suyo, y si se hiciera desde `runOnUiThread` el orbe se
     *   cortaría a cada «pon música». El dibujo va por su cuenta y no se entera.
     *
     * · Sin permiso de leer archivos la lista sale **vacía**, no falsa. Por eso
     *   la cara pregunta `musicaPuedeLeer()` antes de prometer una canción, y
     *   `pidePermisoMedios()` abre el cuadro de una vez.
     *
     * Las URIs viajan separadas por salto de línea o `;` — una URI de
     * `MediaStore` no lleva ninguno de los dos, así que no hay JSON que parsear
     * en Java y el APK sigue sin librerías externas.
     */

    @JavascriptInterface
    public boolean musicaPuedeLeer() {
        return Musica.puedeLeer(act);
    }

    /** El cuadro de permisos de leer la discoteca (audio + video + fotos). */
    @JavascriptInterface
    public void pidePermisoMedios() {
        act.pidePermiso("medios");
    }

    /** ¿Le falta a CORT el «acceso a todos los archivos» para poder *mover*? */
    @JavascriptInterface
    public boolean puedeOrdenarArchivos() {
        if (android.os.Build.VERSION.SDK_INT < 30) return false;
        try {
            return android.os.Environment.isExternalStorageManager();
        } catch (Exception eseAndroidNoTieneEseInterruptor) {
            return false;
        }
    }

    /** La pantalla del sistema donde está ese interruptor, para que lo ponga ella. */
    @JavascriptInterface
    public void abreAjustesArchivos() {
        act.runOnUiThread(() -> {
            if (android.os.Build.VERSION.SDK_INT >= 30) {
                try {
                    act.startActivity(new Intent(
                            Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                            Uri.fromParts("package", act.getPackageName(), null))
                            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
                    return;
                } catch (Exception eseFabricanteNoTieneEsaPantalla) { /* al final común */ }
            }
            openAppSettings();
            act.avisa("Android 10 o menos: CORT ya puede mover archivos, dime qué ordenar");
        });
    }

    /** Canciones (y videos si se pide) cuyo título, artista o género contains `q`. */
    @JavascriptInterface
    public String musicaBuscar(final String q, final boolean incluirVideo) {
        return Musica.listaJson(Musica.buscar(act, q, incluirVideo));
    }

    /** Las que mejor encajan con lo que ha oído, de más a menos. */
    @JavascriptInterface
    public String musicaPorGusto(final String filtro, final int cuantas) {
        int n = cuantas <= 0 ? 25 : Math.min(cuantas, 200);
        return Musica.listaJson(Musica.porGusto(act, filtro, n));
    }

    /** «me gustan estas» / «quítalas»: sube o baja artista y género. */
    @JavascriptInterface
    public void musicaGustar(final String uris, final boolean meGusta) {
        Musica.gustar(act, Musica.porUri(act, trocea(uris)), meGusta);
    }

    /** El perfil en claro, para que la cara lo lea: «te gusta X y Y». */
    @JavascriptInterface
    public String musicaPerfil() {
        return Musica.perfilJson(act);
    }

    @JavascriptInterface
    public String musicaListas() {
        return Musica.listasJson(act);
    }

    @JavascriptInterface
    public void musicaGuardarLista(final String nombre, final String uris) {
        Musica.guardaLista(act, nombre, trocea(uris));
    }

    /** Poner la cola entera por URI y arrancar por la posición `desde`. */
    @JavascriptInterface
    public boolean musicaPoner(final String uris, final int desde) {
        java.util.List<Reproductor.Pista> pistas = alReproductor(Musica.porUri(act, trocea(uris)));
        if (pistas.isEmpty()) return false;
        Reproductor.ponerCola(act, pistas, desde);
        Reproductor.reproducir();
        return true;
    }

    /** Lo mismo con una playlist guardada por nombre. */
    @JavascriptInterface
    public boolean musicaPonerLista(final String nombre, final int desde) {
        java.util.List<Reproductor.Pista> pistas =
            alReproductor(Musica.porUri(act, Musica.urisDeLista(act, nombre)));
        if (pistas.isEmpty()) return false;
        Reproductor.ponerCola(act, pistas, desde);
        Reproductor.reproducir();
        return true;
    }

    /**
     * «Ponme algo»: la cola se arma sola con los gustos y suena.
     *
     * Se consulta en un hilo aparte porque el menú de Java la llama desde el
     * hilo de la interfaz, y recorrer el índice del sistema ahí dentro es
     * exactamente la traba que la dueña nota cuando CORT se pone a pensar.
     */
    @JavascriptInterface
    public void musicaAutomatica() {
        if (!Musica.puedeLeer(act)) {
            act.avisa("Dame el permiso de música y te la pongo yo");
            act.pidePermiso("medios");
            return;
        }
        new Thread(() -> {
            java.util.List<Reproductor.Pista> pistas =
                alReproductor(Musica.porGusto(act, "", 40));
            if (pistas.isEmpty()) {
                act.avisa("No encuentro música que reproducir en el teléfono");
                return;
            }
            Reproductor.ponerCola(act, pistas, 0);
            Reproductor.reproducir();
            musicaCambio();
        }, "cort-musica-automatica").start();
    }

    @JavascriptInterface
    public void musicaPlay() { Reproductor.reproducir(); }

    @JavascriptInterface
    public void musicaPausa() { Reproductor.pausar(); }

    @JavascriptInterface
    public void musicaSiguiente() { Reproductor.siguiente(); }

    @JavascriptInterface
    public void musicaAnterior() { Reproductor.anterior(); }

    /** Saltar a un segundo concreto (la barra de progreso de la cara). */
    @JavascriptInterface
    public void musicaSalto(final int ms) { Reproductor.salto(Math.max(0, ms)); }

    /** Cuadro a cuadro: ±1/30 s, para mirar un video fotograma a fotograma. */
    @JavascriptInterface
    public void musicaCuadro(final boolean haciaAtras) { Reproductor.cuadro(haciaAtras); }

    @JavascriptInterface
    public void musicaVolumen(final double de0a1) {
        Reproductor.volumen((float) Math.max(0d, Math.min(1d, de0a1)));
    }

    /** Se calla y apaga el servicio (la notificación desaparece con él). */
    @JavascriptInterface
    public void musicaParar() {
        Reproductor.detener();
        musicaCambio();
    }

    @JavascriptInterface
    public String musicaEstado() {
        return Reproductor.estadoJson();
    }

    /** Lo llama `.Reproductor` cada vez que algo cambia: play, pausa, canción nueva. */
    void musicaCambio() {
        cuadro("{\"type\":\"music\",\"estado\":" + Reproductor.estadoJson() + "}");
    }

    /* ────────────────────────────── modo juego ────────────────────────────── */

    /**
     * El interruptor de «me voy a poner a jugar». Lo que resuelve es real: la dueña
     * pasa el rato al Call of Duty Mobile y CORT le estorbaba de tres maneras —
     * pedía `AudioFocus` (Android baja o corta el audio de lo demás), el doble
     * toque del auricular se lo llevaba la sesión de CORT en vez del juego, y el
     * micrófono se reabría solo cada cuatrocientos milisegundos, que en un teléfono
     * de gama media es literalmente «se traba y me saca de la partida».
     *
     * Se pone **a mano**, y no puede ser de otra forma: detectar la partida sola
     * exigiría el permiso de uso de aplicaciones (`PACKAGE_USAGE_STATS`) o
     * `QUERY_ALL_PACKAGES`, y los dos están rechazados por ella y vigilados por
     * `scripts/prueba-costura.py`. El contrato con la cara es sólo este nombre y
     * `juegoActivo()`.
     *
     * El orden importa más de lo que parece:
     *
     * 1. La preferencia y la bandera se escriben **antes** de tocar nada más,
     *    porque `Reproductor.pideFoco()` y el JSON de estado leen la bandera: si se
     *    pusiera al final, la canción arrancaría justo dentro del silencio y el
     *    interruptor de la cara saldría mentiroso.
     * 2. `pausa()` es el mecanismo que ya existe — cierra el `SpeechRecognizer`
     *    **sin rearmarlo**, limpia el habla pendiente y avisa a la cara con `pause`,
     *    que es lo único que impide que voice.js vuelva a abrir el micro. No se
     *    escribe aquí un cierre nuevo del reconocedor: sería una segunda versión de
     *    la misma regla, y esa dualidad es la que antes dejó el micro en bucle.
     * 3. `silenciar` + `soltarSesion` devuelven el foco y el auricular al juego.
     *
     * Al desactivar se hace justo lo contrario, y **no** se arranca música: CORT
     * devuelve el oído y la sesión, y si quiere canción ya la pedirá ella.
     */
    @JavascriptInterface
    public void modoJuego(final boolean on) {
        act.prefs().edit().putBoolean("juego", on).apply();
        juego = on;
        if (on) {
            pausa();
            Reproductor.silenciar(act);
            Reproductor.soltarSesion();
        } else {
            Reproductor.recuperarSesion();
            reanuda();
        }
        // El aviso lleva el estado completo, ahora con `juego`: la cara pinta el
        // interruptor con lo que hay de verdad, no con lo que creyó pulsar.
        musicaCambio();
    }

    /** El estado, para que la cara pinte el interruptor (contrato con `ui/`). */
    @JavascriptInterface
    public boolean juegoActivo() { return juego; }

    /** Lo mismo, desde Java: lo leen `Reproductor` y `MainActivity`. */
    static boolean enJuego() { return juego; }

    /* ─────────────────── contactos y marcar ─────────────────── */

    /** Si puede marcar de una vez, o si sólo abrirá el marcador con el número puesto. */
    @JavascriptInterface
    public boolean puedeMarcar() {
        return Telefono.puedeMarcarDirecto(act);
    }

    @JavascriptInterface
    public String contactos(final String quien) {
        return Telefono.contactosJson(act, quien);
    }

    /**
     * «Llama a Samuel». Con permiso marca directo; sin él abre el marcador.
     * El JSON ya trae `directo`, así que la cara puede decir «lo marco» o
     * «está marcado, pulsa tú» en vez de prometer de más.
     */
    @JavascriptInterface
    public String llamar(final String quien) {
        return Telefono.llamar(act, quien);
    }

    /** El cuadro de los permisos de marcar y de leer los contactos. */
    @JavascriptInterface
    public void pidePermisoTelefono() {
        act.pidePermiso("contactos");
    }

    /* ───────────────────────── lista y compañía ───────────────────────── */

    /** URIs separadas por `\n` o `;` → lista limpia, sin huecos. */
    private static java.util.List<String> trocea(String uris) {
        java.util.List<String> out = new ArrayList<>();
        if (uris == null) return out;
        for (String u : uris.split("[\n;]+")) {
            String t = u.trim();
            if (!t.isEmpty()) out.add(t);
        }
        return out;
    }

    private static java.util.List<Reproductor.Pista> alReproductor(java.util.List<Musica.Pista> leidas) {
        java.util.List<Reproductor.Pista> out = new ArrayList<>();
        if (leidas == null) return out;
        for (Musica.Pista p : leidas) if (p != null) out.add(p.alReproductor());
        return out;
    }

    /* ───────────────────────── ciclo de vida ────────────────────── */

    /**
     * La app se va a segundo plano: se cierra el micro **y se avisa a la cara**.
     *
     * El aviso es la parte que faltaba. `ui/js/voice.js` rearma la escucha de
     * «Oye CORT» cuatrocientos milisegundos después de cada sesión, así que
     * cerrar el reconocedor aquí sin decir nada hacía que la página lo volviera
     * a abrir inmediatamente: un micrófono abierto en bucle detrás de la app. En
     * un teléfono de gama media eso es exactamente lo que se nota como «traba»
     * mientras CORT optimiza o suena música. Con `pause`, la cara se marca
     * «en segundo plano», deja de rearma y reintenta suave cada dos segundos.
     */
    void pausa() {
        act.runOnUiThread(() -> {
            cuadro("{\"type\":\"pause\"}");
            if (sttVivo && stt != null) stt.cancel();
            sttVivo = false;
            if (tts != null) tts.stop();
            ttsPendiente.clear();
        });
    }

    /**
     * La app vuelve al frente: `voice.js` espera este aviso para reabrir el oído.
     *
     * Con el modo juego puesto **no** se devuelve el oído — se repite `pause`. Sin
     * esta comprobación, asomar la cara dos segundos dentro del juego (un aviso,
     * un cambio de app) habría reabierto el micrófono encima de la partida, que es
     * exactamente lo que el interruptor promete evitar.
     */
    void reanuda() {
        if (juego) { cuadro("{\"type\":\"pause\"}"); return; }
        cuadro("{\"type\":\"resume\"}");
    }

    void destruye() {
        act.runOnUiThread(() -> {
            if (stt != null) { stt.destroy(); stt = null; }
            if (tts != null) { tts.shutdown(); tts = null; ttsListo = false; }
        });
    }

    /* ─────────────────────────── JSON a mano ────────────────────── */

    private void cuadro(final String json) {
        // `evaluateJavascript` vive en el `WebView`, y el WebView es de
        // `MainActivity`; el puente pide el favor por su método `evalua`.
        act.runOnUiThread(() -> act.evalua(
            "window.__cortNative&&window.__cortNative.emit(" + json + ")"));
    }

    private static String comilla(String s) {
        if (s == null) return "null";
        StringBuilder out = new StringBuilder("\"");
        for (int n = 0; n < s.length(); n++) {
            char c = s.charAt(n);
            switch (c) {
                case '"':  out.append("\\\""); break;
                case '\\': out.append("\\\\"); break;
                case '\n': out.append("\\n");  break;
                case '\r': out.append("\\r");  break;
                case '\t': out.append("\\t");  break;
                default:
                    if (c < 0x20) out.append(String.format("\\u%04x", (int) c));
                    else out.append(c);
            }
        }
        return out.append('"').toString();
    }
}
