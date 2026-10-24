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
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.json.JSONObject;

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
 * La ronda 2.1 añade los seis nombres del contrato de `docs/CONTRATO-PUENTE-2.1.md`
 * —`accion`, `ajusteVoz`, `memoria`, `mente`, `atuendo`, `burbuja`, más `agenda` y
 * `comparte`—, que es lo que había dentro del APK original y fuera del nuestro. El
 * puente sigue sin librerías: cada uno de esos métodos delega en una clase del
 * paquete (`Acciones`, `VozNueva`, `Recuerdos`, `Mente`, `Paleta`, `Flotante`,
 * `Agenda`, `ArchivosProvider`) y le pasa/le devuelve **texto JSON**, no objetos.
 * Todos devuelven `{"ok":true,…}` o `{"ok":false,"dice":"…"}` y ninguno lanza.
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

    /* ────────────── el oído propio (Kotlin, sin nube) ──────────────
     *
     * `Oido` es el reconocimiento de español que vive dentro del APK: Vosk con su
     * modelo de 39.817.833 B comprimidos en `assets/motor/`, que la primera vez se
     * desempaca a `filesDir/motor/` (60.286.598 B) y se carga en un hilo aparte.
     * Sale aquí y no en Google por tres cosas que ella pidió: que CORT funcione
     * sin internet, que no dependa de los servicios de voz de Google (en muchos
     * teléfonos de gama baja no vienen instalados, y ahí el micrófono se quedaba
     * mudo), y que conteste rápido cuando el auricular pide la palabra.
     *
     * `porOido` dice CUÁL de los dos oídos está abierto ahora mismo, porque el
     * `cancel()` y el `stop()` tienen que ir al mismo sitio que abrió la escucha:
     * mandarlos al otro deja un micrófono abierto detrás, y un micro abierto que
     * nadie cierra es lo que ella nota como «el teléfono se traba».
     */
    private volatile Oido oido;
    private volatile boolean porOido = false;
    /** `true` sólo en la variedad ligera: el motor del oído no viaja en este APK. */
    private volatile boolean sinOidoPropio = false;

    /** El oído que abrió el **doble toque del auricular**: su insignia se apaga con él. */
    private volatile boolean porAuricular = false;

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

    /* ─────────────── las piezas de la ronda 2.1 (perezosas) ────────────────
     *
     * Se montan **la primera vez que se piden**, no en el `onCreate`: la dueña
     * abre CORT para poner música y para leerle avisos muchas veces sin tocar
     * nunca la pantalla Equipo, y un `SQLiteDatabase` abierto, un segundo enlace
     * de `TextToSpeech` y el cliente HTTP del cerebro valen memoria que en un
     * teléfono de gama baja se nota. Cada getter es `synchronized` porque el hilo
     * del puente de WebView y el de la cara pueden llamarlos a la vez.
     *
     * Los resultados largos (la nube, la sincronía con el portátil) no vuelven
     * por el `return`: vuelven como evento `window.__cortNative.emit(...)` por
     * el `engancha` de cada pieza, con su `type` ya puesto.
     */

    private volatile Nube nube;
    private volatile Cerebro cerebro;
    private volatile Mente mente;
    private volatile Recuerdos recuerdos;
    private volatile VozNueva boca;
    private volatile Acciones acciones;
    private volatile Paleta paleta;

    private synchronized Nube nube() {
        if (nube == null) nube = new Nube(act);
        return nube;
    }

    private synchronized Cerebro cerebro() {
        if (cerebro == null) cerebro = new Cerebro(act, nube());
        return cerebro;
    }

    private synchronized Mente mente() {
        if (mente == null) {
            Mente nueva = new Mente(act, nube(), cerebro());
            // `Mente` devuelve el cuadro SIN `type`: lo pone aquí, que es donde
            // vive el camino de salida hacia la página.
            nueva.engancha(json -> cuadro(conTipo(json, "mente")));
            mente = nueva;
        }
        return mente;
    }

    private synchronized Recuerdos recuerdos() {
        if (recuerdos == null) {
            Recuerdos nueva = new Recuerdos(act);
            // `Recuerdos` ya escribe `type:"memoria"` en su cuadro de sincronía.
            nueva.engancha(json -> cuadro(json));
            recuerdos = nueva;
        }
        return recuerdos;
    }

    /**
     * El enlace de voz que lista e imita voces. Se monta en un hilo **con
     * `Looper`**, y eso no es una manía: `TextToSpeech` invita a su callback en
     * el hilo donde se construyó, y el hilo del puente de WebView no tiene
     * `Looper`. Montarlo ahí deja el enlace esperando un aviso que nunca llega —
     * el error que sólo se ve en el teléfono.
     */
    private VozNueva boca() {
        VozNueva viva = boca;
        if (viva != null) return viva;
        synchronized (this) {
            if (boca != null) return boca;
            if (android.os.Looper.myLooper() != null) {
                boca = new VozNueva(act);            // hilo de la cara: adelante
            } else {
                final CountDownLatch despierto = new CountDownLatch(1);
                act.runOnUiThread(() -> { boca = new VozNueva(act); despierto.countDown(); });
                try { despierto.await(3, TimeUnit.SECONDS); }
                catch (InterruptedException elPuenteDurmio) { /* devuelve null y la cara lo dice */ }
            }
            return boca;
        }
    }

    private synchronized Acciones acciones() {
        if (acciones == null) acciones = new Acciones(act);
        return acciones;
    }

    private synchronized Paleta paleta() {
        if (paleta == null) paleta = new Paleta(act);
        return paleta;
    }

    /**
     * El oído propio, perezoso como las demás piezas: montar `Oido` no carga nada
     * (eso lo hace `preparaOido()`, en su hilo), así que aquí sólo se construye el
     * objeto y se engancha su salida al puente.
     *
     * El enganche no es un `cuadro(json)` pelado: cuando el oído manda su
     * `stt-end` hay que apagar **la insignia del auricular**, y ése es el detalle
     * que el reconocedor de Google hace por `oidoCerrado()`. Se hace a mano porque
     * `Oido` ya emite su `stt-end` —llamar aquí a `oidoCerrado()` mandaría dos y
     * `voice.js` cerraría el oído dos veces.
     *
     * Devuelve `null` si la dueña apagó el oído propio en Ajustes: la cara sigue
     * funcionando con el reconocedor de siempre, que es la otra mitad del trato.
     */
    private synchronized Oido oido() {
        if (!act.prefs().getBoolean("oido", true)) return null;
        if (oido == null) {
            try {
                oido = new Oido(act, json -> {
                    cuadro(json);
                    if (json.contains("\"stt-end\"")) {
                        sttVivo = false;
                        apagaInsignia();
                    }
                });
            } catch (Throwable motorFuera) {
                // La **variedad ligera** (`APK_SIN_OIDO=1` en `compilar.sh`): las
                // clases de Vosk y JNA no viajaron en el dex, así que ni siquiera se
                // puede construir el oído. No es un fallo del teléfono ni hay que
                // reabrir el micro de otra manera: se marca el caso, se dice
                // `sin-modelo` en la hoja Equipo y toda la escucha va al
                // reconocedor del sistema, que es el plan B de siempre.
                sinOidoPropio = true;
                return null;
            }
        }
        return oido;
    }

    /** Apaga sólo la insignia del auricular; el `stt-end` ya lo mandó quien cierra. */
    private void apagaInsignia() {
        if (porAuricular) {
            porAuricular = false;
            cuadro("{\"type\":\"auricular\",\"escuchando\":false}");
        }
    }

    /** Arranca el desempaque y la carga del modelo. Se llama desde `MainActivity`. */
    void preparaOido() {
        Oido propio = oido();
        if (propio != null) propio.prepara();
    }

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

    /**
     * Lo mismo, pero desde Java: el doble toque del auricular y el asistente.
     *
     * La guarda de `sttVivo` existe porque desde la ronda 2.4.1 hay vías que abren
     * el micro **y además** traen la cara al frente con `PIDE_ESCUCHAR` (el doble
     * toque, el baldosín): sin ella las dos rutas llaman a `arrancarEscucha` y el
     * segundo `startListening` corta la frase que se estaba diciendo a media
     * palabra. El oído ya abierto se deja abierto.
     */
    void escuchaAhora() {
        if (sttVivo) return;
        act.runOnUiThread(() -> arrancarEscucha("es-MX", "cmd"));
    }

    /**
     * El doble toque del auricular, que es el único sitio donde la cara necesita
     * una insignia: la dueña pulsa dos veces en el audífono y no ve la pantalla,
     * así que el botón del micro de la página le tiene que decir «te estoy
     * escuchando» o «ya terminé». Con `escuchaAhora()` a secas la página se queda
     * con la duda, y una duda en el oído es la que hace volver a tocar.
     */
    void escuchaDelAuricular() {
        porAuricular = true;
        cuadro("{\"type\":\"auricular\",\"escuchando\":true}");
        escuchaAhora();
    }

    /** El oído se cierra: el `stt-end` de siempre y, si era del auricular, su insignia. */
    private void oidoCerrado() {
        cuadro("{\"type\":\"stt-end\"}");
        apagaInsignia();
    }

    private void arrancarEscucha(String lang, String modo) {
        // Modo juego: ni micro abierto. `pausa()` ya mandó `pause` a la cara, así
        // que voice.js no va a rearmar; estos dos eventos son sólo para que el orbe
        // no se quede pintando «escuchando» cuando no se está escuchando nada.
        //
        // Medido en el teléfono de la dueña el 2026-10-22 con `2.6.0-nucleo`: se
        // reportaba como `abort`, y `ui/js/voice.js` **no tiene rama para `abort` en
        // modo `cmd`** —sólo en `wake`—, así que el `onError` de la cara nunca se
        // disparaba y el botón del micrófono parecía roto: ni oía, ni explicaba por
        // qué. Ahora se nombra el motivo (`juego`), voice.js lo sube a `onError`, y
        // la cara dice «estoy en modo juego» en vez de callarse.
        //
        // Sigue **sin** ser `not-allowed` a propósito: `voice.js` apaga la palabra de
        // activación al ver «not-allowed», y apagarla por un capricho del
        // interruptor sería dejarla muda para siempre.
        if (juego) {
            cuadro("{\"type\":\"stt-error\",\"error\":\"juego\"}");
            oidoCerrado();
            return;
        }
        if (!permiso("mic")) {
            cuadro("{\"type\":\"stt-error\",\"error\":\"not-allowed\"}");
            oidoCerrado();
            pedir("mic");
            return;
        }
        // Primero el oído propio. `escucha()` devuelve `false` en los tres casos en
        // que todavía no puede responder —está desempacando el modelo, el micro está
        // ocupado, o el motor se cayó— y entonces se cae al reconocedor de Google,
        // que es lo que hacía CORT antes de existir esta clase. La cara no ve la
        // diferencia: los dos caminos emiten `stt-start`, `stt-speech`, `stt-level`,
        // `stt-partial`, `stt-final`, `stt-error` y `stt-end` con los mismos nombres.
        // Aquí **no** se manda el `stt-start`: lo manda `Oido` con su `modo`, para
        // que no salga duplicado y voice.js cuente aperturas de más.
        Oido propio = oido();
        if (propio != null
                && propio.escucha(modo, "wake".equals(modo) ? Oido.MAX_WAKE : Oido.MAX_CMD)) {
            porOido = true;
            sttVivo = true;
            return;
        }
        porOido = false;
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
            oidoCerrado();
        }
    }

    @JavascriptInterface
    public void stopListening() {
        act.runOnUiThread(() -> {
            // Se cierra EL oído que se abrió, no «el de siempre»: si el cierre va al
            // reconocedor de Google mientras habla Vosk, el micro del oído propio se
            // queda agarrado y la siguiente escucha no puede empezar.
            if (porOido && oido != null) { oido.para(); return; }
            if (stt != null) stt.stopListening();
        });
    }

    @JavascriptInterface
    public void cancelListening() {
        act.runOnUiThread(() -> {
            sttVivo = false;
            if (porOido && oido != null) { porOido = false; oido.cancela(); return; }
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
            oidoCerrado();
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
            oidoCerrado();
            return;
        }
        ArrayList<String> partes =
            resultados.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if (partes == null || partes.isEmpty()) {
            if (final_) oidoCerrado();
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
        if (final_) oidoCerrado();
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
        // La voz que habla es la que la dueña eligió, venga de donde venga la orden.
        // `ui/js/voice.js` manda siempre la suya (los valores de 07 · Perfil), así que
        // ésa manda; cuando habla Java por su cuenta —el aviso de los mensajes, el
        // saludo, el menú— `voz` llega vacía y `tono`/`velocidad` llegan a 0, y entonces
        // manda lo que se escribió en la pantalla Equipo (`ajusteVoz`). Sin este orden,
        // «pon voz de Siri» cambiaría la voz en la pantalla y no en la calle.
        SharedPreferences preferencias = act.prefs();
        String elegida = (voz == null || voz.isEmpty())
            ? preferencias.getString("voz-nombre", "") : voz;
        if (elegida != null && !elegida.isEmpty()) ponVoz(elegida);
        double vel = velocidad > 0 ? velocidad : preferencias.getFloat("voz-velocidad", 1.0f);
        double tonoReal = tono > 0 ? tono : preferencias.getFloat("voz-tono", 0.82f);
        try {
            tts.setPitch((float) Math.max(0.5, Math.min(2.0, tonoReal)));
            tts.setSpeechRate((float) Math.max(0.5, Math.min(2.0, vel)));
        } catch (Exception sigueConLaVozDeSiempre) { /* nada */ }
        Bundle sinExtras = new Bundle();
        tts.speak(texto, TextToSpeech.QUEUE_ADD, sinExtras, uid);
    }

    private void sueltaPendiente() {
        ArrayList<String[]> cola = new ArrayList<>(ttsPendiente);
        ttsPendiente.clear();
        for (String[] pedido : cola) {
            // Cero = «no me importa el valor, mira las preferencias»: `dice` decide
            // con lo que la dueña eligió en la pantalla Equipo.
            double tono = 0, vel = 0;
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
               + ",\"tts\":" + ttsListo
               + ",\"oido\":" + (oido != null && oido.listo()) + "}";
    }

    /**
     * El estado del oído propio en JSON: qué fase va (`sin-intentar`, `extrayendo`,
     * `cargando`, `listo`, `sin-sitio`, `roto`…), cuánto pesa el modelo, cuántos MB
     * libres hay y por qué se cayó si se cayó. Es la respuesta a «¿por qué CORT no me
     * entiende sin internet?» sin tener que abrir el teléfono por USB.
     */
    @JavascriptInterface
    public String oidoEstado() {
        Oido propio = oido;
        if (sinOidoPropio) {
            // Variedad ligera: no es que el teléfono no pueda, es que este archivo
            // no trae el motor. La cara lo pinta con su frase de `sin-modelo`.
            return "{\"type\":\"motor\",\"oido\":\"sin-modelo\",\"listo\":false}";
        }
        if (propio == null) {
            return act.prefs().getBoolean("oido", true)
                ? "{\"type\":\"motor\",\"oido\":\"sin-arrancar\",\"listo\":false}"
                : "{\"type\":\"motor\",\"oido\":\"apagado\",\"listo\":false}";
        }
        return propio.estadoJson();
    }

    /**
     * El interruptor de Ajustes: «que CORT escuche sin internet». Apagado, el oído
     * propio se suelta (devuelve sus ~50 MB) y toda la escucha vuelve al reconocedor
     * de Google, que es como funcionaba antes. Encendido, se prepara otra vez.
     */
    @JavascriptInterface
    public String oidoPropio(final boolean on) {
        act.prefs().edit().putBoolean("oido", on).apply();
        final Oido propio = oido;
        oido = null;
        if (propio != null) {
            Thread soltar = new Thread(() -> {
                propio.frena(true);
                propio.suelta();
            }, "cort-oido-suelta");
            soltar.setDaemon(true);
            soltar.start();
        }
        porOido = false;
        if (on) preparaOido();
        return "{\"ok\":true,\"oido\":" + on + "}";
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
        // Y `hasPermission('files')`, la clave corta del explorador de archivos: sin
        // `startsWith("file")` caía en el `return true` de abajo y CORT prometía ver
        // carpetas que el teléfono no le había dejado ver.
        if (k.startsWith("medios") || k.startsWith("music") || k.startsWith("musica")
            || k.startsWith("archiv") || k.startsWith("file") || k.startsWith("almacen")) {
            return Musica.puedeLeer(act);
        }
        if (k.startsWith("contacto") || k.startsWith("marcar") || k.startsWith("llam")) {
            return act.checkSelfPermission(android.Manifest.permission.READ_CONTACTS)
                   == PackageManager.PERMISSION_GRANTED;
        }
        // Igual que en `MainActivity.grupoDe`: el panel pregunta con la clave corta
        // «notif», y `startsWith("notific")` no la cubría.
        if (k.startsWith("aviso") || k.startsWith("notif")) {
            // Android 13 es el único que pregunta; antes la notificación existe sin permiso.
            if (android.os.Build.VERSION.SDK_INT < 33) return true;
            return act.checkSelfPermission("android.permission.POST_NOTIFICATIONS")
                   == PackageManager.PERMISSION_GRANTED;
        }
        // La ronda 2.1 añade dos preguntas nuevas de la cara: el calendario para
        // «qué tengo hoy» y aparecer encima de otras apps para la burbuja. El
        // segundo no es un permiso de cuadro: es un interruptor de Ajustes, así que
        // se comprueba como interruptor y la cara lo dice como interruptor.
        if (k.startsWith("calendari") || k.startsWith("agenda") || k.startsWith("cita")) {
            return Agenda.conPermiso(act);
        }
        if (k.startsWith("burbuja") || k.startsWith("encima") || k.startsWith("flotante")
            || k.startsWith("overlay")) {
            return Flotante.puedeAparecer(act);
        }
        // Las dos últimas preguntas del panel de segundo plano. `battery` es la
        // restricción de Android (se mide, no se supone) y `autostart` es el
        // ajuste del fabricante, que CORT no puede leer: se abre la pantalla y la
        // dueña lo ve, en vez de marcar un ✓ que no se comprobó en ninguna parte.
        if (k.startsWith("bateri") || k.startsWith("battery") || k.startsWith("ahorro")) {
            return sinRestriccionDeBateria();
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

    /**
     * Lo que lee el panel «▸ Segundo plano» de 07 · Perfil.
     *
     * Este método es la prueba de que la pantalla no miente: antes devolvía sólo
     * `bg` y `pc`, y la cara leía `enabled`, `running`, `mic`, `notif`, `overlay`,
     * `battery` y `maker` —claves que no existían—, así que el interruptor nunca se
     * iluminaba, los cuatro permisos salían siempre sin marcar y apagarlo era
     * imposible (`on = !undefined` daba `true` todas las veces). Ahora cada clave
     * que la cara pregunta tiene su medida real aquí, y lo que CORT **no** puede
     * hacer con la app cerrada lo dice `dice` en vez de prometerlo.
     */
    @JavascriptInterface
    public String bgStatus() {
        SharedPreferences p = act.prefs();
        boolean quiereFondo = p.getBoolean("bg", false);
        return "{\"bg\":" + quiereFondo
               + ",\"pc\":" + comilla(p.getString("pc", ""))
               + ",\"enabled\":" + quiereFondo
               + ",\"running\":" + act.avisoDeFondoPuesto()
               + ",\"mic\":" + permiso("mic")
               + ",\"notif\":" + permiso("avisos")
               + ",\"overlay\":" + permiso("burbuja")
               + ",\"battery\":" + sinRestriccionDeBateria()
               + ",\"maker\":" + comilla(android.os.Build.MANUFACTURER + " "
                                          + android.os.Build.BRAND)
               + ",\"microAbierto\":" + sttVivo
               + ",\"dice\":" + comilla(quiereFondo
                   ? "Sigo en segundo plano con mi aviso: la música y el doble toque"
                     + " del auricular obedecen. El micrófono se queda cerrado para"
                     + " no trabarte — «Oye CORT» con la app cerrada no viaja en este APK."
                   : "Sin el interruptor puesto, al irte de la app CORT se guarda.")
               + "}";
    }

    /** `PowerManager.isIgnoringBatteryOptimizations` sobre su propio paquete. */
    private boolean sinRestriccionDeBateria() {
        try {
            android.os.PowerManager pm = (android.os.PowerManager)
                    act.getSystemService(android.content.Context.POWER_SERVICE);
            return pm != null && pm.isIgnoringBatteryOptimizations(act.getPackageName());
        } catch (Exception eseAparejoNoLoDejaLeer) {
            return false;      // sin dato, sin marca: la cara ofrece «Dar» y ya
        }
    }

    /**
     * El interruptor de «que CORT se quede en segundo plano». No abre el
     * micrófono a escondidas: decide si al irte de la app queda puesto el aviso de
     * Android (ver `MainActivity.dejaAvisoDeFondo`), que es lo que de verdad
     * mantiene vivo el doble toque del auricular.
     */
    @JavascriptInterface
    public void setBackground(boolean on) {
        act.prefs().edit().putBoolean("bg", on).apply();
        act.alAvisoDeFondoLeGustaCambiar();
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
     * ¿Suena música ahora mismo? Lo pregunta `ui/js/voice.js` para saber **cómo**
     * abrir el oído, no para cerrarlo.
     *
     * Desde la 2.4 la cara usaba esta respuesta como freno: con música sonando no
     * se reabría el micrófono, porque abrirlo baja el volumen de lo demás y en un
     * teléfono de gama media además lo traba. El resultado medido era el que la
     * dueña llamaba «parece pendeja»: decir «pausa» con una canción puesta no se
     * oía jamás, porque el oído estaba cerrado antes de escuchar nada.
     *
     * Ahora el oído propio pide `AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK` (`Oido.kt`),
     * así que con música sonando **sí** se abre el micro y la música se agacha
     * mientras CORT oye. Esta respuesta queda para dos cosas: decirle a la cara
     * que tenga más calma al rearmar (los rearmas sobre audio activo son los que
     * trababan el aparato) y pintarle el motivo en la lámpara.
     *
     * El detalle honesto: `isMusicActive()` también es `true` mientras CORT habla
     * por `TextToSpeech` (el TTS va por el stream de multimedia), y por eso la
     * cara ignora el primer segundo y medio después de cada frase.
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
     * Si CORT puede escuchar **con la música puesta** sin cerrarle el audio al
     * aparato: o sea si el ducking de `Oido.kt` está disponible aquí.
     *
     * Es `false` en dos casos reales y la cara tiene que decirlo distinto: un APK
     * `ligero` sin el modelo (ahora manda el reconocedor del sistema, que no
     * pide foco) y un teléfono cuyo sistema no armaron el `AudioFocusRequest`.
     * Ahí la cara conserva el freno viejo en vez de fingir un ducking que no hay
     * y de dejar el micro abierto rearmándose contra la música.
     */
    @JavascriptInterface
    public boolean duckOk() {
        Oido propio = oido;
        return propio != null && propio.listo() && propio.puedeDuck();
    }

    /**
     * La tecla de transporte para **el reproductor que sea** del aparato.
     *
     * `musicaPausa()` y sus hermanas mandan en `Reproductor`, el reproductor de
     * CORT; si la música suena en Spotify o en YouTube, ese `isPlaying()` no es
     * vivo y la orden se iba al backend, el backend a `main.py`, y el APK cortaba
     * con 501. `dispatchMediaKeyEvent` es el camino que Android diseñó para esto:
     * la tecla va al `MediaSession` que esté activo, sea de quien sea, y no pide
     * ningún permiso nuevo —lo mismo que hacen los botones del auricular.
     *
     * Devuelve `false` si el sistema no la aceptó, para que la cara lo diga en
     * vez de prometer un «pauso la canción» que no ocurrió.
     */
    @JavascriptInterface
    public boolean teclaMedia(final String que) {
        if (que == null) return false;
        Object servicio = act.getSystemService(android.content.Context.AUDIO_SERVICE);
        if (!(servicio instanceof android.media.AudioManager)) return false;
        android.media.AudioManager audio = (android.media.AudioManager) servicio;
        int tecla;
        switch (que) {
            case "pausa":     tecla = android.view.KeyEvent.KEYCODE_MEDIA_PAUSE; break;
            case "play":      tecla = android.view.KeyEvent.KEYCODE_MEDIA_PLAY; break;
            case "siguiente": tecla = android.view.KeyEvent.KEYCODE_MEDIA_NEXT; break;
            case "anterior":  tecla = android.view.KeyEvent.KEYCODE_MEDIA_PREVIOUS; break;
            case "parar":     tecla = android.view.KeyEvent.KEYCODE_MEDIA_STOP; break;
            default: return false;
        }
        try {
            long ahora = android.os.SystemClock.uptimeMillis();
            audio.dispatchMediaKeyEvent(new android.view.KeyEvent(
                ahora, ahora, android.view.KeyEvent.ACTION_DOWN, tecla, 0));
            audio.dispatchMediaKeyEvent(new android.view.KeyEvent(
                ahora, ahora, android.view.KeyEvent.ACTION_UP, tecla, 0));
            return true;
        } catch (Exception elSistemaNoObedece) {
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

    /**
     * Qué puertas puede ofrecer **este** APK. Ronda 2.5.
     *
     * Por qué hace falta: desde la 2.5 salen dos perfiles del mismo cuerpo. El
     * `completo` declara el traje de asistente, el reconocedor, el lector de
     * avisos, el baldosín de la cortina y las llamadas; el `nucleo` no declara
     * ninguno de esos cinco servicios con `BIND_*` — es la superficie exacta del
     * `1.1.4` que a la dueña se le instala — porque esa superficie es lo único que
     * separa, medido, lo que Play Protect deja abrir de lo que bloquea.
     *
     * El Kotlin de esas puertas sigue dentro del APK en los dos perfiles (los
     * `.class` no aparecen en ningún escáner público; lo que se mira es el
     * manifiesto). Lo que **no** puede pasar es que la cara ofrezca un botón cuya
     * puerta no está declarada: un `startService` de un servicio que no está en el
     * manifiesto no arranca nada, y un «pídeme el rol de asistente» en el `nucleo`
     * lleva a una lista de Ajustes donde CORT no aparece. Por eso la cara pregunta
     * esto antes de pintar esas cuatro fichas de Equipo.
     *
     * El perfil se lee del `<meta-data>` que clava `apps/apk/perfil.py`, o sea del
     * manifiesto **del archivo instalado** — no de una constante compilada que
     * podría no corresponderse con el APK que llegó al teléfono. Si no hay
     * meta-datos (un APK anterior a la 2.5, o un fabricante que la tira), se
     * devuelve `completo`: es lo que siempre fue, y las cuatro puertas existían.
     */
    @JavascriptInterface
    public String capacidades() {
        String perfil = "completo";
        try {
            android.content.pm.ApplicationInfo info =
                act.getPackageManager().getApplicationInfo(
                    act.getPackageName(), android.content.pm.PackageManager.GET_META_DATA);
            if (info.metaData != null) {
                Object v = info.metaData.get("com.cort.ia.PERFIL");
                if (v != null) perfil = v.toString();
            }
        } catch (Exception elPaqueteNoContesta) { /* queda completo, como siempre */ }
        boolean nucleo = "nucleo".equals(perfil);
        return "{\"perfil\":" + comilla(perfil)
               + ",\"nucleo\":" + nucleo
               + ",\"asistente\":" + !nucleo
               + ",\"avisos\":" + !nucleo
               + ",\"cortina\":" + !nucleo
               + ",\"reconocedor\":" + !nucleo
               + ",\"llamadas\":" + !nucleo
               + ",\"agenda\":" + !nucleo + "}";
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
            // Los ceros son el aviso de «habla con la voz que ella eligió», no con una
            // voz impuesta desde aquí: `dice` lee `voz-nombre`/`voz-tono`/`voz-velocidad`.
            if (ttsListo && tts != null) {
                dice(texto, "aviso", "", 0, 0);
                return;
            }
            ttsPendiente.add(new String[] { texto, "aviso", "", "0", "0" });
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

    /**
     * La carátula de una pista, en `data:image/jpeg;base64,…`, o cadena vacía si el
     * teléfono no la tiene. Ver el comentario de `Musica.caratula`: es lo que faltaba
     * para que la hoja Música pareciera Lark Player en vez de una lista de glifos.
     *
     * Se llama por fila visible desde la cara (`musicaCaratula` en `pantallas.js`),
     * nunca para la lista entera: son ~12 KB por imagen y 800 imágenes cruzando el
     * puente de una vez es la traba que CORT prometió no dar.
     */
    @JavascriptInterface
    public String musicaCaratula(final String uri, final int lado) {
        return Musica.caratula(act, uri, lado);
    }

    /** «Velocidad», la fila de Lark: 0,75× · 1× · 1,25×… Devuelve el motivo si no pudo. */
    @JavascriptInterface
    public String musicaVelocidad(final float x) {
        return Reproductor.velocidad(x);
    }

    /** «Ocultar» de Lark: esta pista deja de salir en la lista (no se borra nada). */
    @JavascriptInterface
    public void musicaOculta(final String uri) {
        Musica.oculta(act, uri);
    }

    /** Cuántas hay ocultadas, para enseñarlo en Ajustes como hace Lark. */
    @JavascriptInterface
    public int musicaOcultas() {
        return Musica.ocultas(act).size();
    }

    /** «Mostrar las ocultadas»: devuelve todo a la lista. */
    @JavascriptInterface
    public void musicaMuestraTodas() {
        Musica.muestraTodas(act);
    }

    /**
     * «Temporizador para dormir» de Lark: a los `minutos` se pausa la música sola.
     * Con `0` se quita el temporizador puesto. Es un `postDelayed` sobre el hilo
     * principal llamando al `pausar()` que ya existe — no hay hilo nuevo ni permiso
     * nuevo, y si la app se cierra el aviso muere con ella, que es lo honesto.
     */
    @JavascriptInterface
    public void musicaDuerme(final int minutos) {
        android.os.Handler h = new android.os.Handler(android.os.Looper.getMainLooper());
        if (temporizador != null) h.removeCallbacks(temporizador);
        temporizador = null;
        if (minutos <= 0) { act.avisa("Temporizador quitado: suena hasta que tú digas"); return; }
        temporizador = () -> {
            Reproductor.pausar();
            act.avisa("Se acabó el tiempo: pauso la música como pediste");
            musicaCambio();
        };
        h.postDelayed(temporizador, minutos * 60000L);
        act.avisa("Me callo sola en " + minutos + " minutos");
    }
    private Runnable temporizador;

    /**
     * Abrir una dirección con la app que corresponda (los «Sitios» de la pantalla de
     * búsqueda de Lark: YouTube, Instagram, SoundCloud…). Si el teléfono no tiene app
     * para ese enlace, se dice con palabras en vez de quedarse muda.
     */
    @JavascriptInterface
    public String abreEnlace(final String url) {
        try {
            Intent i = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            act.startActivity(i);
            return "";
        } catch (Exception noHayAppParaEso) {
            return "ese teléfono no tiene app abierta para " + url;
        }
    }

    /**
     * Que el botón flotante «CORT · PC» se vea o no, hoja por hoja.
     *
     * La queja de la dueña con `2.6.0-nucleo` fue literal: «el botón CORT PC está
     * atravesado, no se oculta». Y tenía razón: el botón lo añade `MainActivity` por
     * encima del `WebView` (`MainActivity.java:171-186`) y en todo el repo no había un
     * solo `setVisibility` para él — estaba en la misma esquina inferior izquierda
     * donde la cara pinta la píldora de la música (`ui/css/hud.css:732`). Ahora la cara
     * lo esconde cuando entra en una hoja con barra propia y lo devuelve en el orbe.
     */
    @JavascriptInterface
    public void menuPC(final boolean visible) {
        act.muestraMenuPC(visible);
    }

    /**
     * Abrir el menú nativo desde la hoja Equipo. El botón flotante «CORT · PC»
     * se ocultó porque estorbaba y parecía que CORT arrancaba en modo PC; sus
     * dieciséis filas (asistente, avisos, música, agenda, burbuja, memoria)
     * siguen aquí, a un toque desde Ajustes.
     */
    @JavascriptInterface
    public void abreMenu() {
        act.abreMenu();
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
        salirDeJuegoPorMusica();
        Reproductor.ponerCola(act, pistas, desde);
        Reproductor.reproducir();
        return true;
    }

    /** Lo mismo con una playlist guardada por nombre. */
    @JavascriptInterface
    public boolean musicaPonerLista(final String nombre, final int desde) {
        // F15 · el nombre dicho no tiene que ser exacto: `Elige.lista` lo cruza con
        // las listas que hay («para correr» encuentra «Para correr»). Si no hay
        // ninguna, se sigue con el nombre tal cual y la respuesta honesta de abajo.
        String real = nombre == null ? "" : nombre;
        java.util.List<String> listas = Musica.listas(act);
        int cual = Elige.lista(real, listas);
        if (cual >= 0) real = listas.get(cual);
        java.util.List<Reproductor.Pista> pistas =
            alReproductor(Musica.porUri(act, Musica.urisDeLista(act, real)));
        if (pistas.isEmpty()) return false;
        salirDeJuegoPorMusica();
        Reproductor.ponerCola(act, pistas, desde);
        Reproductor.reproducir();
        return true;
    }

    /**
     * F15 · «pon la canción X» / «cámbialo a X»: busca en la música DEL TELÉFONO y
     * pone la que más se parece (la decisión es `Elige`, pura y probada en el JDK).
     *
     * Devuelve JSON siempre, con `dice` para la boca: si no hay permiso lo pide; si
     * la biblioteca no tiene nada parecido lo dice con el nombre que buscó — así la
     * cara puede ofrecer el camino de internet sin fingir que sonó. La cola es la
     * lista de resultados desde la elegida, para que «siguiente» siga teniendo sentido.
     */
    @JavascriptInterface
    public String musicaPonerNombre(final String nombre) {
        String pedida = nombre == null ? "" : nombre.trim();
        if (pedida.isEmpty()) {
            return "{\"ok\":false,\"dice\":\"¿Qué canción te pongo?\"}";
        }
        if (!Musica.puedeLeer(act)) {
            act.pidePermiso("medios");
            return "{\"ok\":false,\"dice\":\"Para buscar en tu música necesito leerla: "
                 + "te pido el permiso y me lo dices otra vez.\"}";
        }
        java.util.List<Musica.Pista> encontradas = Musica.buscar(act, pedida, false);
        java.util.List<Elige.Candidata> candidatas = new java.util.ArrayList<>();
        for (Musica.Pista p : encontradas) {
            candidatas.add(new Elige.Candidata(p.titulo, p.artista, p.genero));
        }
        int cual = Elige.mejor(pedida, candidatas);
        if (cual < 0) {
            return "{\"ok\":false,\"candidatas\":" + encontradas.size()
                 + ",\"buscado\":\"" + Reproductor.esc(pedida)
                 + "\",\"dice\":\"" + Reproductor.esc(
                     encontradas.isEmpty()
                         ? "No encuentro «" + pedida + "» en la música del teléfono."
                         : "No sé cuál de las " + encontradas.size()
                           + " que salen es «" + pedida + "».")
                 + "\"}";
        }
        salirDeJuegoPorMusica();
        Reproductor.ponerCola(act, alReproductor(encontradas), cual);
        Reproductor.reproducir();
        Musica.Pista p = encontradas.get(cual);
        String dice = "Pongo «" + p.titulo + "»"
                + (p.artista == null || p.artista.trim().isEmpty() ? "" : " de " + p.artista) + ".";
        return "{\"ok\":true,\"titulo\":\"" + Reproductor.esc(p.titulo)
             + "\",\"artista\":\"" + Reproductor.esc(p.artista)
             + "\",\"candidatas\":" + encontradas.size()
             + ",\"dice\":\"" + Reproductor.esc(dice) + "\"}";
    }

    /** F15 · el ecualizador de verdad: preset por nombre, o el estado si viene vacío. */
    @JavascriptInterface
    public String ecualiza(final String preset) {
        if (preset == null || preset.trim().isEmpty()) return Ecualizador.estadoJson();
        return Ecualizador.aplica(preset.trim());
    }

    /** F15 · qué ecualizador hay puesto y qué presets trae este teléfono. */
    @JavascriptInterface
    public String ecualizaEstado() {
        return Ecualizador.estadoJson();
    }

    /* ─────────────────────────── F16 · el despertador ────────────────────────
     * La cara no arma `AlarmManager` ni toca notificaciones: manda la frase y la
     * decisión (hora, canción, nota, rutina) la toma `Despertar`/`Alarma`, que es
     * lo que se mide en el JDK y lo que se puede leer en un solo sitio.
     */

    /* Poner la alarma NO tiene tecla propia: la cara manda la frase por `accion`
       (`que:"alarma"`), y `Acciones.alarma` la compone con los campos sueltos y la
       entrega a `Alarma.ponerDesde`. Una segunda boca para lo mismo sería una
       segunda forma de decidir la hora. */

    @JavascriptInterface
    public String alarmaEstado() { return Alarma.estadoJson(act); }

    @JavascriptInterface
    public String alarmaCancela() { return Alarma.cancela(act); }

    @JavascriptInterface
    public String alarmaDetener() { return Alarma.detener(act); }

    @JavascriptInterface
    public String alarmaPosponer() { return Alarma.posponer(act); }

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
        salirDeJuegoPorMusica();
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
    public void musicaPlay() { salirDeJuegoPorMusica(); Reproductor.reproducir(); }

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

    /**
     * Lo llama `.Avisos` cuando llega un aviso nuevo (ronda 2.4).
     *
     * Antes la cara sólo se enteraba de los avisos cuando la dueña abría la hoja o
     * cuando CORT los leía; para una automatización («cuando llegue algo de
     * WhatsApp, haz X») eso llega tarde. Es un cuadro **sin pedir nada**: la página
     * lo recibe por `window.__cortNative.emit` como los demás, y si la página no
     * está, `cuadro` cae en el `null` de `evalua` y no pasa nada.
     *
     * No añade permiso: `Avisos` ya escucha el buzón porque la dueña dio de alta el
     * lector de notificaciones en Ajustes.
     */
    void avisoEnLaCara(String de, String dicho) {
        cuadro("{\"type\":\"aviso\",\"de\":" + comilla(de) + ",\"dice\":" + comilla(dicho) + "}");
    }

    /**
     * El atajo del icono largo (ronda 2.4.1): «Equipo» o «Charla» llegan a Java
     * antes de que la página exista, así que no hay a quién pedirle la hoja. Se
     * emite `{"type":"atajo","hoja":"…"}` y `pantallas.js` hace el `ir(hoja)` de
     * siempre — el mismo que ejecuta un toque en la barra de pantallas.
     *
     * Sale por `cuadro`, que es la boca única del puente: si la cara aún no tiene
     * oyente, el evento se pierde como se pierden los demás, y la página abre en
     * el orbe. No se guarda en cola a propósito: un atajo de hace ocho segundos ya
     * no es un atajo, es CORT saltando solo.
     */
    void atajoEnLaCara(String hoja) {
        cuadro("{\"type\":\"atajo\",\"hoja\":" + comilla(hoja) + "}");
    }

    /**
     * F16 · el despertador está sonando: la cara enseña su pantalla de alarma con
     * lo que trae el evento (`hora`, `nota`, `titulo`, `rutina`, `dice`).
     *
     * `datos` ya es un objeto JSON salido de `Alarma`; aquí sólo se le pone el
     * `type` que escucha la página. Se comprueba que sea un objeto y se le quitan
     * las llaves de fuera: pegar `{"type":"alarma",` delante de algo que no empieza
     * por `{` dejaría un cuadro roto que la cara no podría leer.
     */
    void alarmaEnLaCara(String datos) {
        String dentro = datos == null ? "" : datos.trim();
        String cuerpo = "";
        if (dentro.startsWith("{") && dentro.endsWith("}")) {
            cuerpo = dentro.substring(1, dentro.length() - 1).trim();
        }
        cuadro("{\"type\":\"alarma\"" + (cuerpo.isEmpty() ? "" : "," + cuerpo) + "}");
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
            // La burbuja, si estaba puesta, se quita: es un punto de CORT flotando
            // encima de la pantalla, y «encima de la pantalla» en modo juego es
            // encima del Call of Duty. Se retira aunque la dueña la vuelva a pedir
            // luego — arriba, `burbuja()` se niega mientras el modo esté puesto.
            try { Flotante.burbuja(act, false); }
            catch (Exception noEstabaPuesta) { /* nada que retirar */ }
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

    /**
     * Que la dueña pida una canción **es** salir del modo juego.
     *
     * El modo existe para no estorbar dentro de una partida, y lo que hace es
     * negarse a pedir el foco de audio (`Reproductor.pideFoco()`, línea 287 de esa
     * clase). Medido el 2026-10-22 en su teléfono con `2.6.0-nucleo`: el interruptor
     * se quedó puesto y CORT cargaba las pistas **en silencio** — `onPrepared` llama
     * a `m.start()` sólo si el foco se concede (`Reproductor.java:342-347`) —, de
     * manera que «no reproduce música» y «el micrófono no hace nada» eran el mismo
     * fallo con dos caras, y la única salida era meterse en la hoja Música.
     *
     * La regla que cierra el callejón: una orden **explícita** de música gana al
     * modo. Nadie que está en plena partida se pone a tocar la lista de canciones
     * desde dentro de CORT; si lo hace, quiere oír. Y al desactivar se hace por el
     * camino de siempre (`modoJuego(false)`), que devuelve el oído y la sesión de
     * audio, en vez de escribir la preferencia a mano y dejar la bandera mintiendo.
     */
    private void salirDeJuegoPorMusica() {
        if (!juego) return;
        modoJuego(false);
        act.avisa("Salgo del modo juego: ahora sí suena CORT");
    }

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

    /* ─────────────── la pantalla Equipo: lo que manda en el aparato ───────────────
     *
     * Los seis métodos de la ronda 2.1 (`docs/CONTRATO-PUENTE-2.1.md`) son la
     * respuesta a «el APK pesa poco y le falta todo lo prometido»: peso en **hechos
     * que se pueden tocar**, no en librerías. Cada uno es síncrono, devuelve una
     * cadena JSON con `ok`, y **nunca** lanza una excepción a la cara: lo que el
     * teléfono no dejó hacer se cuenta en `dice`, en español y con el camino de
     * Ajustes, que es la diferencia entre un botón roto y un botón que dice
     * «toca esto y vuelve».
     *
     * Lo largo —la nube, el viaje a la LAN— no espera al `return`: se contesta
     * `{"ok":true,"pendiente":true}` enseguida y el resultado entra por el evento
     * que engancharon `Mente` y `Recuerdos` arriba. Un `@JavascriptInterface` que
     * tarda seis segundos congela el botón que la pulsó, y eso se llama «se traba».
     */

    /** «súbelo», «linterna», «alarma a las 7:30», «abre WhatsApp», «busca recetas». */
    @JavascriptInterface
    public String accion(final String peticion) {
        String respuesta;
        try {
            respuesta = acciones().accion(peticion);
        } catch (Exception elTelefonoNoDejo) {
            return mal("el teléfono no respondió a esa orden");
        }
        // La linterna es el único `que` que necesita un permiso de cuadro y no lo
        // pide solo (así lo escribió `Acciones`: sin `CAMERA` lo dice, no lo fuerza).
        // Aquí se cierra el círculo: si la dueña la pidió y falta la cámara, se lo
        // pregunta al sistema en este momento, para que la segunda pulsación funcione.
        if (pideLinterna(peticion) && !permiso("camara")) pedir("camara");
        return respuesta;
    }

    private static boolean pideLinterna(String peticion) {
        if (peticion == null) return false;
        try {
            JSONObject j = new JSONObject(peticion);
            return "linterna".equals(j.optString("que", "").toLowerCase(Locale.US));
        } catch (Exception noEsJSON) {
            return peticion.contains("linterna");
        }
    }

    /** La voz: lista, elegir estilo, velocidad, tono, descargar datos, probar. */
    @JavascriptInterface
    public String ajusteVoz(final String peticion) {
        VozNueva enlace = boca();
        if (enlace == null) return mal("el teléfono no dejó montar el enlace de voz");
        String respuesta;
        try {
            respuesta = enlace.ajusteVoz(peticion);
        } catch (Exception elMotorNoContesta) {
            return mal("el motor de voz de este teléfono no contestó");
        }
        // Lo elegido se aplica en el acto a la boca del puente (la que habla los
        // avisos y el saludo), no sólo a la del bloque: `dice` ya lee las
        // preferencias, y esto es el «ya, cámbialo ahora» que la dueña espera.
        act.runOnUiThread(this::aplicaVozGuardada);
        return respuesta;
    }

    /** Deja la voz del puente como lo guardado por `VozNueva` en `cort.xml`. */
    private void aplicaVozGuardada() {
        if (tts == null || !ttsListo) return;
        SharedPreferences p = act.prefs();
        String nombre = p.getString("voz-nombre", "");
        if (nombre != null && !nombre.isEmpty()) ponVoz(nombre);
        try {
            tts.setSpeechRate(p.getFloat("voz-velocidad", 1.0f));
            tts.setPitch(p.getFloat("voz-tono", 0.82f));
        } catch (Exception eseMotorNoAcepta) { /* la voz de siempre sigue sirviendo */ }
    }

    /** «acuédate de…», «¿qué sabes de mí?», «sincroniza con el portátil». */
    @JavascriptInterface
    public String memoria(final String peticion) {
        try {
            return recuerdos().memoria(peticion);
        } catch (Exception laBaseNoAbrio) {
            return mal("la memoria del teléfono no se abrió");
        }
    }

    /** «piensa…», «qué proveedor usas», «cambia el modelo y la clave». */
    @JavascriptInterface
    public String mente(final String peticion) {
        try {
            return mente().mente(peticion);
        } catch (Exception pensandoTorcido) {
            return mal("no pude pensar eso ahora");
        }
    }

    /** Los trajes de CORT: `lista` y `poner`. La cara pinta el CSS, Java el botón. */
    @JavascriptInterface
    public String atuendo(final String peticion) {
        String respuesta;
        try {
            respuesta = paleta().atuendo(peticion);
        } catch (Exception elTrajeNoSalio) {
            return mal("no pude cambiar el traje");
        }
        act.usaAtuendo();
        return respuesta;
    }

    /** «¿qué tengo hoy?», «mis próximos planes», «el correo», «apunta una cita». */
    @JavascriptInterface
    public String agenda(final String peticion) {
        String respuesta;
        try {
            respuesta = Agenda.agenda(act, peticion);
        } catch (Exception elCalendarioNoContesta) {
            return mal("no pude mirar tu calendario");
        }
        // Igual que la linterna: si la pregunta era de citas y falta el permiso de
        // calendario, se pregunta **ahora**, que es cuando la dueña lo quiere dar.
        if (pideCalendario(peticion) && !Agenda.conPermiso(act)) pedir("calendario");
        return respuesta;
    }

    private static boolean pideCalendario(String peticion) {
        if (peticion == null) return true;                 // sin JSON = «qué tengo hoy»
        try {
            String que = new JSONObject(peticion).optString("que", "hoy")
                                                .toLowerCase(Locale.US);
            return !("abrir".equals(que) || "correo".equals(que) || "estado".equals(que));
        } catch (Exception noEsJSON) {
            return true;
        }
    }

    /**
     * El punto de CORT flotando sobre lo que sea. Con modo juego puesto **no
     * aparece nunca**, ni aunque se lo pidan: es la promesa del interruptor, y la
     * rompe un solo toque que saque a la dueña de la partida.
     */
    @JavascriptInterface
    public String burbuja(final boolean on) {
        if (juego) return mal("estoy en modo juego: no me meto encima de tu partida");
        try {
            return Flotante.burbuja(act, on);
        } catch (Exception elSistemaNoDeja) {
            return mal("Android no dejó poner el punto flotante en este teléfono");
        }
    }

    /** La pantalla del interruptor de «aparecer encima de otras apps». */
    @JavascriptInterface
    public void abreAjustesBurbuja() {
        act.runOnUiThread(() -> {
            try {
                act.startActivity(new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                                             Uri.fromParts("package", act.getPackageName(), null))
                                      .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
                return;
            } catch (Exception eseFabricanteNoTieneEsaPantalla) { /* al común */ }
            openAppSettings();
            act.avisa("Ajustes ▸ Aplicaciones ▸ CORT ▸ Aparecer encima de otras apps");
        });
    }

    /**
     * «Envíame ese archivo»: sale por `ACTION_SEND` con un URI del proveedor del
     * APK (`ArchivosProvider`), que es la forma legal de enseñar un archivo a otra
     * app sin darle el camino del disco. Sin el proveedor, Android corta el `Uri`
     * con un `FileUriExposedException` en Android 7+, y este APK soporta 8 en
     * adelante: sería un fallo que aparecería siempre y en ningún sitio.
     *
     * Acepta las dos formas que la cara tiene de nombrar un archivo: el camino del
     * disco (`/storage/emulated/0/Download/informe.pdf`) y el URI del índice de
     * Android (`content://media/external/audio/media/42`), que es lo único que sabe
     * la pantalla de Música. Con el `content://` no hace falta el proveedor —el
     * propio índice ya lo enseña— y quien lo recibe cobra permiso de lectura por la
     * bandera del `Intent`.
     */
    @JavascriptInterface
    public String comparte(final String ruta) {
        String limpia = ruta == null ? "" : ruta.trim();
        if (limpia.isEmpty()) return mal("no me dijiste qué archivo quieres enviar");
        if (limpia.startsWith("content://")) {
            final Uri delIndice = Uri.parse(limpia);
            if (!sePuedeAbrir(delIndice)) {
                return mal("ese archivo ya no está en el teléfono o no lo puedo leer");
            }
            return envia(delIndice, nombreDel(delIndice));
        }
        java.io.File archivo = new java.io.File(limpia);
        if (!archivo.isFile()) {
            return mal("eso no es un archivo que exista en el teléfono: " + nombreDe(limpia));
        }
        final Uri destino;
        try {
            destino = ArchivosProvider.de(act, archivo);
        } catch (Exception elProveedorNoLoVe) {
            return mal("no puedo enseñar ese archivo: está fuera de las carpetas que "
                     + "Android me deja compartir (música, videos, fotos, descargas, documentos)");
        }
        return envia(destino, archivo.getName());
    }

    /** El `ACTION_SEND` con selector de app, en la cara, que es donde Android lo deja. */
    private String envia(final Uri destino, final String nombre) {
        final Intent manda = new Intent(Intent.ACTION_SEND)
            .setType(mimeDeArchivo(nombre))
            .putExtra(Intent.EXTRA_STREAM, destino)
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
        act.runOnUiThread(() -> {
            try {
                act.startActivity(Intent.createChooser(manda, "Enviar con CORT"));
            } catch (Exception nadiePuedeRecibirlo) {
                act.avisa("Ninguna app de este teléfono puede recibir ese archivo");
            }
        });
        return "{\"ok\":true,\"envia\":" + comilla(nombre) + "}";
    }

    /** ¿Existe de verdad ese URI? El índice conteste `null` no es un fallo: es que no está. */
    private boolean sePuedeAbrir(Uri uri) {
        java.io.InputStream ahora = null;
        try {
            ahora = act.getContentResolver().openInputStream(uri);
            return ahora != null;
        } catch (Exception noLoDeja) {
            return false;
        } finally {
            try { if (ahora != null) ahora.close(); }
            catch (Exception yaEstaCerrado) { /* nada */ }
        }
    }

    /** El nombre bonito (`DISPLAY_NAME`) del índice; si no hay, el último tramo del URI. */
    private String nombreDel(Uri uri) {
        try {
            android.database.Cursor cur = act.getContentResolver().query(
                uri, new String[] { android.provider.OpenableColumns.DISPLAY_NAME },
                null, null, null);
            try {
                if (cur != null && cur.moveToFirst() && !cur.isNull(0)) return cur.getString(0);
            } finally {
                if (cur != null) cur.close();
            }
        } catch (Exception elIndiceNoContesta) { /* sigue con lo que diga el URI */ }
        String ultimo = uri.getLastPathSegment();
        return ultimo == null || ultimo.isEmpty() ? "archivo" : ultimo;
    }

    /** El MIME por extensión, de la lista corta que se ordena en el teléfono. */
    private static String mimeDeArchivo(String nombre) {
        String n = nombre == null ? "" : nombre.toLowerCase(Locale.US);
        if (n.endsWith(".mp3") || n.endsWith(".m4a") || n.endsWith(".aac")
            || n.endsWith(".ogg") || n.endsWith(".flac") || n.endsWith(".wav")) return "audio/*";
        if (n.endsWith(".mp4") || n.endsWith(".mkv") || n.endsWith(".webm")
            || n.endsWith(".mov") || n.endsWith(".avi")) return "video/*";
        if (n.endsWith(".jpg") || n.endsWith(".jpeg") || n.endsWith(".png")
            || n.endsWith(".webp") || n.endsWith(".gif")) return "image/*";
        if (n.endsWith(".pdf")) return "application/pdf";
        if (n.endsWith(".doc") || n.endsWith(".docx")) return "application/msword";
        if (n.endsWith(".xls") || n.endsWith(".xlsx")) {
            return "application/vnd.ms-excel";
        }
        if (n.endsWith(".zip")) return "application/zip";
        if (n.endsWith(".apk")) return "application/vnd.android.package-archive";
        if (n.endsWith(".txt") || n.endsWith(".md") || n.endsWith(".srt")
            || n.endsWith(".lrc") || n.endsWith(".csv")) return "text/plain";
        return "*/*";
    }

    private static String nombreDe(String camino) {
        int corte = Math.max(camino.lastIndexOf('/'), camino.lastIndexOf('\\'));
        return corte >= 0 ? camino.substring(corte + 1) : camino;
    }

    /* ─────────────── el teléfono medido por sí mismo (ronda 2.2) ───────────────
     *
     * Los dos métodos que faltaban para que la queja «hay sensores que no
     * funcionan» tuviera respuesta honesta. El diagnóstico medido: la ventana
     * «02 · Entorno» se llenaba **sólo** con `/api/status` del portátil
     * (`refreshStatus` en `ui/js/hud.js`), y en el teléfono sin PC ese panel
     * nacía vacío —no era que el acelerómetro o el giroscopio no existieran,
     * es que el puente no tenía ni un método donde pedirlos (`SensorManager`
     * no aparecía en ninguno de los 21 archivos Java de la 2.1).
     *
     * `sentido` y `aparato` son síncronos y baratos: leen la última muestra ya
     * guardada (`Sentidos`) o el estado que el sistema contesta al momento
     * (`Aparato`). Ninguno de los dos lanza excepción a la cara: lo que Android
     * no deja medir sale en `dice`, y lo que no se midió sale como `-1` para
     * que la cara pinte `—` en vez de un cero disfrazado.
     */

    /** Los once sentidos que CORT sabe leer, con su última muestra y su antigüedad. */
    @JavascriptInterface
    public String sensores() {
        try {
            return Sentidos.de(act).lectura();
        } catch (Exception elSistemaNoPrestaNada) {
            return mal("Android no me dejó mirar los sensores de este teléfono");
        }
    }

    /** Batería, RAM, disco, red, CPU y brillo del propio teléfono, sin portátil. */
    @JavascriptInterface
    public String aparato() {
        try {
            return Aparato.de(act).estado(act);
        } catch (Exception nadieDejaMedir) {
            return mal("no pude medir el teléfono ahora mismo");
        }
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
            // `frena` cierra el oído propio si estaba abierto (y su `cancela()` manda
            // el `stt-end` y la insignia por el enganche de `oido()`); el `cancel` de
            // siempre sigue para el reconocedor de Google.
            Oido propio = oido;
            if (propio != null) propio.frena(true);
            if (porOido) porOido = false;
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
        // Las piezas de la ronda 2.1 se apagan también: `VozNueva` es UN SEGUNDO
        // enlace de `TextToSpeech` (el del puente y el de ella son bocas distintas, y
        // dejarla abierta es dejar un motor de voz respirando en el teléfono), y
        // `Recuerdos` es una base SQLite con su manija de disco.
        //
        // `Oido` se suelta **aquí y no en `pausa()`**: el `Model` de Vosk es código
        // nativo y trae unos 50 MB detrás (medido por Alpha Cephei), que en un teléfono
        // de gama baja es la diferencia entre que CORT sobreviva en segundo plano o que
        // Android lo cierre. Al cerrar la app se devuelven; al volver, `preparaOido()`
        // los vuelve a pedir, y el modelo ya está desempacado en `filesDir`, así que no
        // se copia nada: sólo se carga.
        final VozNueva enlace = boca;
        final Recuerdos base = recuerdos;
        final Oido elOido = oido;
        boca = null;
        recuerdos = null;
        oido = null;
        porOido = false;
        act.runOnUiThread(() -> {
            if (stt != null) { stt.destroy(); stt = null; }
            if (tts != null) { tts.shutdown(); tts = null; ttsListo = false; }
            if (enlace != null) enlace.suelta();
        });
        if (elOido != null) {
            Thread soltar = new Thread(elOido::suelta, "cort-oido-suelta");
            soltar.setDaemon(true);
            soltar.start();
        }
        if (base != null) {
            try { base.close(); } catch (Exception laBaseYaEstabaCerrada) { /* nada */ }
        }
    }

    /* ─────────────── lo que llama `MainActivity` sin pasar por JS ───────────────
     *
     * El menú del botón «CORT · PC» no tiene página que le responda: habla él.
     * Estos métodos existen para que el menú pueda prometer lo mismo que la
     * pantalla Equipo, porque la dueña usa las dos cosas y una frase suya no
     * debería sonar distinto según por dónde entró. Todos escriben en la cara
     * además de hablar, para que la pantalla y la voz no sean dos verdades.
     */

    /** «¿Qué tengo hoy?»: lee las citas y lo cuenta en voz, sin pasar por la página. */
    void leeAgenda(final String peticion) {
        new Thread(() -> {
            String respuesta;
            try { respuesta = Agenda.agenda(act, peticion); }
            catch (Exception elCalendarioNoContesta) { respuesta = mal("no pude mirar el calendario"); }
            // Sin permiso, `Agenda` ya lo dice en su `dice`; aquí además se pregunta
            // al sistema, que es lo que hace que la segunda vez sí salgan las citas.
            if (pideCalendario(peticion) && !Agenda.conPermiso(act)) pedir("calendario");
            diAlto(textoDe(respuesta, "dice", "No vi nada apuntado para hoy"));
        }, "cort-agenda").start();
    }

    /** «Probar el cerebro» desde el menú: el mismo `que` que usa la cara. */
    void pruebaCerebro() {
        mente("{\"que\":\"probar\"}");
    }

    /** «Cuadrar la memoria» desde el menú: el viaje largo, con su aviso al volver. */
    void sincronizaMemoria() {
        memoria("{\"que\":\"sincronizar\"}");
    }

    /** El `dice` del cuadro, o un sustituto honesto si no lo trae. */
    private static String textoDe(String json, String clave, String porSiNo) {
        try {
            String dicho = new JSONObject(json).optString(clave, "");
            return dicho.trim().isEmpty() ? porSiNo : dicho;
        } catch (Exception noEsJSON) {
            return porSiNo;
        }
    }

    /* ─────────────────────────── JSON a mano ────────────────────── */

    private void cuadro(final String json) {
        // `evaluateJavascript` vive en el `WebView`, y el WebView es de
        // `MainActivity`; el puente pide el favor por su método `evalua`.
        act.runOnUiThread(() -> act.evalua(
            "window.__cortNative&&window.__cortNative.emit(" + json + ")"));
    }

    /** `{"ok":false,"dice":"…"}` — la única forma de fallar contra la cara. */
    private static String mal(String dice) {
        return "{\"ok\":false,\"dice\":" + comilla(dice) + "}";
    }

    /**
     * El cuadro de un trabajo largo, con el `type` que la cara escucha.
     *
     * `Mente` y `Recuerdos` devuelven su JSON sin `type`: no saben si el destino es
     * la página o el registro. Escribirlo aquí, en el único camino de salida hacia
     * `window.__cortNative.emit`, es lo que hace que `handleTelefonoEvento` reciba
     * `{type:"mente", ok, responde}` tal y como promete el contrato.
     */
    private static String conTipo(String json, String tipo) {
        try {
            JSONObject cuadro = new JSONObject(json == null || json.trim().isEmpty()
                                               ? "{}" : json);
            cuadro.put("type", tipo);
            return cuadro.toString();
        } catch (Exception noEraJSON) {
            return "{\"type\":" + comilla(tipo) + ",\"ok\":false,\"dice\":"
                 + comilla("el teléfono contestó algo que no es JSON") + "}";
        }
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
