package dev.sandra.cort;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.speech.tts.Voice;
import java.util.ArrayList;
import java.util.Locale;
import java.util.Set;

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

    /** El nivel del micrófono mientras se escucha, en 0..1, para el orbe. */
    public interface AlNivel {
        void nivel(float alto);
    }

    private TextToSpeech boca;
    private boolean bocaLista;
    private String enCola;
    private SpeechRecognizer oido;
    private AlOir oyente;
    private AlNivel medidor;
    private String aviso = "";
    private String vozElegida = "";

    /**
     * La voz **es la misma que la de la cara de PC**, por construcción y no por
     * casualidad: `apps/web/src/cort/voz.ts` dice `IDIOMA = 'es-CO'`,
     * `velocidad 0.95`, `tono 1` y una lista de preferidas (`jorge, gonzalo,
     * alvaro, alonso, tomas, lorenzo, raul, pablo`) con el mismo baremo. Hasta
     * `v0.15.5` el teléfono usaba `es-ES` con la voz que Android trajera, y la
     * dueña lo notó: «la voz no sé si sea la misma, parece otra». `test_apk_orbe.py`
     * compara estos literales con los del TypeScript.
     */
    static final String IDIOMA = "es-CO";
    static final float VELOCIDAD = 0.95f;
    static final float TONO = 1.0f;
    static final String[] PREFERIDAS = {
        "jorge", "gonzalo", "alvaro", "alonso", "tomas", "lorenzo", "raul", "pablo"};
    // El baremo de `voz.ts`: Natural 0, online 20, local 40; más el puesto en la
    // lista de preferidas (o 10 si no está) y un punto si el acento no es
    // es-CO/MX/US/419. Gana el número más bajo.
    static final int PUNTOS_NATURAL = 0, PUNTOS_EN_LINEA = 20, PUNTOS_LOCAL = 40;

    private static final String[] ACENTOS = {"co", "mx", "us", "419"};

    /**
     * `AudioManager.getMaxAmplitude()` va de 0 a 32 767 y el `rms` que Android
     * entrega a `onRmsChanged` son decibelios aproximados entre -2 y 10: son dos
     * aparatos distintos, así que se normaliza **por el rango del recognizer** y se
     * documenta el origen del número.
     */
    static float normalizarRms(float decibelios) {
        float f = (decibelios + 2f) / 12f;
        return f < 0f ? 0f : (f > 1f ? 1f : f);
    }

    public Voz(Context contexto) {
        boca = new TextToSpeech(contexto.getApplicationContext(), this);
    }

    @Override
    public void onInit(int estado) {
        if (estado != TextToSpeech.SUCCESS) {
            aviso = "no pude encender la voz de Android";
            return;
        }
        int listo = TextToSpeech.LANG_NOT_SUPPORTED;
        for (String variante : new String[] {IDIOMA, "es-419", "es-MX", "es-US", "es-ES"}) {
            listo = boca.setLanguage(Locale.forLanguageTag(variante));
            if (listo != TextToSpeech.LANG_MISSING_DATA && listo != TextToSpeech.LANG_NOT_SUPPORTED) {
                break;
            }
        }
        if (listo == TextToSpeech.LANG_MISSING_DATA || listo == TextToSpeech.LANG_NOT_SUPPORTED) {
            aviso = "este teléfono no tiene voz en español instalada";
        }
        boca.setSpeechRate(VELOCIDAD);
        boca.setPitch(TONO);
        Voice mejor = mejorVoz();
        if (mejor != null) {
            boca.setVoice(mejor);
            vozElegida = mejor.getName() + " · " + mejor.getLocale().toLanguageTag();
        }
        bocaLista = true;
        if (enCola != null) {
            String pendiente = enCola;
            enCola = null;
            hablar(pendiente);
        }
    }

    /**
     * El mismo orden de mérito que el navegador, adaptado a lo que Android expone:
     * una voz `Voice` dice su nombre, su `Locale` y si necesita red. Se recorre la
     * lista del aparato y gana el puntaje más bajo; si el teléfono no tiene voces
     * en español se queda la que ya venga ajustada.
     */
    private Voice mejorVoz() {
        Set<Voice> disponibles = boca.getVoices();
        if (disponibles == null || disponibles.isEmpty()) {
            return null;
        }
        Voice mejor = null;
        int mejorPuntos = Integer.MAX_VALUE;
        for (Voice voz : disponibles) {
            Locale sitio = voz.getLocale();
            if (sitio == null || !"es".equalsIgnoreCase(sitio.getLanguage())) {
                continue;
            }
            String nombre = voz.getName() == null ? "" : voz.getName().toLowerCase();
            int puntos = voz.isNetworkConnectionRequired() ? PUNTOS_EN_LINEA : PUNTOS_LOCAL;
            if (nombre.contains("natural")) {
                puntos = PUNTOS_NATURAL;
            }
            int puesto = puestoEnPreferidas(nombre);
            puntos += puesto >= 0 ? puesto : 10;
            if (!paisAmericano(sitio)) {
                puntos += 1;
            }
            if (puntos < mejorPuntos) {
                mejorPuntos = puntos;
                mejor = voz;
            }
        }
        return mejor;
    }

    static int puestoEnPreferidas(String nombreEnMinusculas) {
        for (int i = 0; i < PREFERIDAS.length; i++) {
            if (nombreEnMinusculas.contains(PREFERIDAS[i])) {
                return i;
            }
        }
        return -1;
    }

    static boolean paisAmericano(Locale sitio) {
        String pais = sitio.getCountry() == null ? "" : sitio.getCountry().toLowerCase();
        if (pais.isEmpty() && sitio.getVariant() != null) {
            pais = sitio.getVariant().toLowerCase();
        }
        for (String candidato : ACENTOS) {
            if (pais.equals(candidato)) {
                return true;
            }
        }
        return "419".equals(sitio.getVariant());
    }

    /** Lo que el registro de la cara puede mostrar: «voz: …» para comparar con el PC. */
    public String voz() {
        return vozElegida;
    }

    public void ponerNivel(AlNivel oyenteDelNivel) {
        medidor = oyenteDelNivel;
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

    /**
     * Si la boca todavía está sonando. La cara de PC no lo puede saber (el
     * `speechSynthesis` del navegador no expone un muestreo del sintetizador), pero
     * Android sí, y es lo que dice al orbe cuándo vuelve de `HABLA` a reposo.
     */
    public boolean hablando() {
        return bocaLista && boca != null && boca.isSpeaking();
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
        intento.putExtra(RecognizerIntent.EXTRA_LANGUAGE, IDIOMA);
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
            // Aquí sí hay medidor de micrófono — el que la cara de PC no tiene.
            // El valor alimenta el orbe para que se mueva con la voz de la dueña.
            if (medidor != null) {
                medidor.nivel(normalizarRms(rms));
            }
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
