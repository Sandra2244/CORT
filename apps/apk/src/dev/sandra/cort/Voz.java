package dev.sandra.cort;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import java.util.ArrayList;
import java.util.Locale;

/**
 * La boca y el oído de CORT **en el teléfono**, con los motores que Android ya
 * trae: `TextToSpeech` y `SpeechRecognizer`.
 *
 * Esto es lo que el WebView no podía dar. Desde la página servida por el
 * portátil, `SpeechRecognition` no existe dentro del WebView de Android y
 * `getUserMedia` pide un origen seguro — HTTPS — que en una LAN con `http://`
 * no hay. Medido y escrito en `docs/PLATFORM.md`: **hablar** se oía, **escuchar**
 * no. Aquí el micrófono es nativo, así que CORT por fin oye en el móvil sin
 * servidor, sin certificado y sin portátil encendido.
 *
 * El permiso `RECORD_AUDIO` se pide en tiempo de ejecución (Android 6+): sin
 * eso el recognizer devuelve `ERROR_INSUFFICIENT_PERMISSIONS` en silencio, que
 * es la peor forma de fallar — la usuaria cree que el micrófono está roto.
 */
public class Voz implements TextToSpeech.OnInitListener {
    public interface AlOir {
        void dijo(String texto);

        void fallo(String motivo);
    }

    private TextToSpeech boca;
    private boolean bocaLista;
    private String enCola;
    private SpeechRecognizer oido;
    private AlOir oyente;
    private String aviso = "";

    public Voz(Context contexto) {
        boca = new TextToSpeech(contexto.getApplicationContext(), this);
    }

    @Override
    public void onInit(int estado) {
        if (estado != TextToSpeech.SUCCESS) {
            aviso = "no pude encender la voz de Android";
            return;
        }
        int listo = boca.setLanguage(Locale.forLanguageTag("es-ES"));
        if (listo == TextToSpeech.LANG_MISSING_DATA || listo == TextToSpeech.LANG_NOT_SUPPORTED) {
            listo = boca.setLanguage(new Locale("es"));
        }
        if (listo == TextToSpeech.LANG_MISSING_DATA || listo == TextToSpeech.LANG_NOT_SUPPORTED) {
            aviso = "este teléfono no tiene voz en español instalada";
        }
        bocaLista = true;
        if (enCola != null) {
            String pendiente = enCola;
            enCola = null;
            hablar(pendiente);
        }
    }

    /** La primera frase puede llegar antes de que el motor haya contestado: se encola. */
    public void hablar(String texto) {
        if (texto == null || texto.trim().isEmpty()) {
            return;
        }
        if (!bocaLista) {
            enCola = texto;
            return;
        }
        boca.speak(texto, TextToSpeech.QUEUE_FLUSH, null, "cort");
    }

    public String aviso() {
        return aviso;
    }

    /**
     * Escucha un dictado. Debe llamarse con el permiso ya concedido y desde el
     * hilo de la interfaz; `SpeechRecognizer` no funciona en un hilo de trabajo.
     */
    public void escuchar(Context contexto, final AlOir callback) {
        oyente = callback;
        if (oido == null) {
            oido = SpeechRecognizer.createSpeechRecognizer(contexto.getApplicationContext());
            oido.setRecognitionListener(new Escucha());
        }
        Intent intento = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intento.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intento.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "es-ES");
        intento.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        intento.putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, contexto.getPackageName());
        try {
            oido.startListening(intento);
        } catch (SecurityException sinPermiso) {
            callback.fallo("falta el permiso de micrófono");
        } catch (Exception cualquierCosa) {
            callback.fallo("el reconocimiento de voz de este teléfono no respondió");
        }
    }

    public void dejarDeEscuchar() {
        if (oido != null) {
            oido.cancel();
        }
    }

    public void cerrar() {
        if (oido != null) {
            oido.destroy();
            oido = null;
        }
        if (boca != null) {
            boca.shutdown();
            boca = null;
        }
    }

    /** Un listener que nunca lanza: un fallo del motor se cuenta, no tumba la cara. */
    private final class Escucha implements RecognitionListener {
        @Override
        public void onReadyForSpeech(Bundle datos) {
        }

        @Override
        public void onBeginningOfSpeech() {
        }

        @Override
        public void onRmsChanged(float rms) {
        }

        @Override
        public void onBufferReceived(byte[] buffer) {
        }

        @Override
        public void onEndOfSpeech() {
        }

        @Override
        public void onError(int codigo) {
            if (oyente != null) {
                oyente.fallo(motivo(codigo));
            }
        }

        @Override
        public void onResults(Bundle datos) {
            // `getStringArrayList` es de API 1; `getParcelableArrayList` no llegó
            // hasta API 33 y un móvil viejo se caería con un `NoSuchMethodError`.
            ArrayList<String> opciones =
                    datos.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
            if (oyente != null) {
                String dicho = (opciones == null || opciones.isEmpty()) ? "" : opciones.get(0);
                if (dicho.isEmpty()) {
                    oyente.fallo("no te oí");
                } else {
                    oyente.dijo(dicho);
                }
            }
        }

        @Override
        public void onPartialResults(Bundle datos) {
        }

        @Override
        public void onEvent(int codigo, Bundle datos) {
        }

        private String motivo(int codigo) {
            switch (codigo) {
                case SpeechRecognizer.ERROR_AUDIO:
                    return "el micrófono no captó nada";
                case SpeechRecognizer.ERROR_CLIENT:
                    return "el reconocimiento cerró antes de tiempo";
                case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS:
                    return "falta el permiso de micrófono";
                case SpeechRecognizer.ERROR_NETWORK:
                case SpeechRecognizer.ERROR_NETWORK_TIMEOUT:
                    return "el motor de voz de Android necesita internet";
                case SpeechRecognizer.ERROR_NO_MATCH:
                    return "no entendí nada";
                case SpeechRecognizer.ERROR_RECOGNIZER_BUSY:
                    return "estoy escuchando otra cosa";
                default:
                    return "no pude escuchar (código " + codigo + ")";
            }
        }
    }
}
