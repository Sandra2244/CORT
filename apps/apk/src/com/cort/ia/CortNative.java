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

    public CortNative(MainActivity actividad) {
        this.act = actividad;
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
        if (kind.equalsIgnoreCase("mic") || kind.equalsIgnoreCase("micro")
            || kind.equalsIgnoreCase("audio")) {
            return act.checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)
                   == PackageManager.PERMISSION_GRANTED;
        }
        if (kind.equalsIgnoreCase("camara") || kind.equalsIgnoreCase("camera")) {
            return act.checkSelfPermission(android.Manifest.permission.CAMERA)
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

    /* ───────────────────────── ciclo de vida ────────────────────── */

    void pausa() {
        act.runOnUiThread(() -> {
            if (sttVivo && stt != null) stt.cancel();
            sttVivo = false;
            if (tts != null) tts.stop();
            ttsPendiente.clear();
        });
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
