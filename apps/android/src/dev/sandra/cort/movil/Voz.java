package dev.sandra.cort.movil;

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
 * La boca y el oído de CORT **en el teléfono**.
 *
 * La boca es `TextToSpeech`, que Android ya trae. El oído tiene **dos motores**, y
 * el orden es el de la promesa del proyecto:
 *
 * 1. `Motor` (Vosk dentro del APK): el dictado se resuelve en el propio aparato,
 *    sin red y sin salir de la mano de la dueña. Se prepara solo, en segundo
 *    plano, la primera vez que se monta la cara.
 * 2. `android.speech.SpeechRecognizer`, el del aparato: **respaldo**, y en un
 *    Samsung con los servicios de Google es un reconocimiento que funciona por
 *    internet. Se usa cuando el modelo aún no está cargado o el APK se compiló
 *    sin él, y se dice cuál de los dos se está usando (`oido()`), para que
 *    ninguna frase de la cara prometa localismo donde no lo hay.
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
    /** Los trozos del lector que llegaron antes de que el motor contestara. */
    private final ArrayList<String> enColaLectura = new ArrayList<>();
    /** El paso elegido por el lector, 1,0 por defecto; se aplica encima de `VELOCIDAD`. */
    private float pasoLectura = 1.0f;
    private SpeechRecognizer oido;
    private Motor motor;
    /** `true` si el último dictado lo resolvió Vosk dentro del teléfono. */
    private volatile boolean dictadoLocal;
    private AlOir oyente;
    private AlNivel medidor;
    private String aviso = "";
    private String vozElegida = "";

    /**
     * La voz **es la misma que la de la cara de PC**, y en esta rama se sabe cuál
     * es la de PC porque está medida: `cort-bridge/cort_voz.py` habla con
     * `espeak-ng` (español de España) por defecto y, si se elige el motor
     * `natural`, con Piper `es_ES-mls_10246-low` (1,90× tiempo real) o
     * `es_ES-davefx-medium` (2,55×). Las dos son **castellanas**, así que el
     * teléfono pide `es-ES`; el orden de reserva baja del castellano al
     * latinoamericano y, al final, a cualquier español que el aparato tenga.
     *
     * El detalle importa porque la dueña lo oyó: «la voz no sé si sea la misma,
     * parece otra». La lista de preferidas y el baremo vienen de la otra línea
     * del repo (allí la cara de PC usa `speechSynthesis` con `es-CO`); en esta
     * rama `scripts/prueba_apk.py` comprueba que el idioma del Java sea el idioma
     * del `.onnx` que usa el puente.
     */
    static final String IDIOMA = "es-ES";
    static final float VELOCIDAD = 0.95f;
    static final float TONO = 1.0f;
    static final String[] PREFERIDAS = {
        "jorge", "gonzalo", "alvaro", "alonso", "tomas", "lorenzo", "raul", "pablo"};
    // Natural 0, en línea 20, local 40; más el puesto en la lista de preferidas
    // (o 10 si no está) y un punto si el acento no es el del PC (es-ES).
    // Gana el número más bajo.
    static final int PUNTOS_NATURAL = 0, PUNTOS_EN_LINEA = 20, PUNTOS_LOCAL = 40;

    private static final String[] ACENTOS = {"es"};

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
        // El oído local se prepara aquí, en segundo plano, mientras la boca
        // todavía está iniciando. Es idempotente: si la cara se monta dos veces,
        // el modelo se carga una.
        motor = Motor.compartido(contexto);
        motor.prepara();
    }

    @Override
    public void onInit(int estado) {
        if (estado != TextToSpeech.SUCCESS) {
            aviso = "no pude encender la voz de Android";
            return;
        }
        int listo = TextToSpeech.LANG_NOT_SUPPORTED;
        // Del acento del PC (es-ES, que es `IDIOMA`) hacia abajo; si el teléfono
        // no tiene castellano, cualquier español sirve mejor que callarse.
        for (String variante : new String[] {IDIOMA, "es-419", "es-MX", "es-US", "es-CO"}) {
            listo = boca.setLanguage(Locale.forLanguageTag(variante));
            if (listo != TextToSpeech.LANG_MISSING_DATA && listo != TextToSpeech.LANG_NOT_SUPPORTED) {
                break;
            }
        }
        if (listo == TextToSpeech.LANG_MISSING_DATA || listo == TextToSpeech.LANG_NOT_SUPPORTED) {
            aviso = "este teléfono no tiene voz en español instalada";
        }
        boca.setSpeechRate(VELOCIDAD * pasoLectura);
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
        if (!enColaLectura.isEmpty()) {
            ArrayList<String> pendientes = new ArrayList<>(enColaLectura);
            enColaLectura.clear();
            for (String trozo : pendientes) {
                seguir(trozo);
            }
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
            if (!acentoDelPc(sitio)) {
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

    /**
     * ¿Habla esta voz con el acento del PC? En esta rama el PC habla castellano
     * (`espeak-ng` español y Piper `es_ES-*`), así que el baremo premia `es-ES` y
     * castiga un punto a los demás —también a `es-419`, que en la otra línea era
     * el acento bueno porque allí la cara de PC usaba `es-CO`—.
     */
    static boolean acentoDelPc(Locale sitio) {
        String pais = sitio.getCountry() == null ? "" : sitio.getCountry().toLowerCase();
        if (pais.isEmpty() && sitio.getVariant() != null) {
            pais = sitio.getVariant().toLowerCase();
        }
        for (String candidato : ACENTOS) {
            if (pais.equals(candidato)) {
                return true;
            }
        }
        return false;
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
     * Lee un trozo más sin cortar el que suena. `hablar` usa QUEUE_FLUSH —es la
     * respuesta a una pregunta, tiene que atropellar lo anterior—; un lector de
     * documentos dice párrafo por párrafo y necesita QUEUE_ADD entre medias.
     */
    public void seguir(String texto) {
        if (texto == null || texto.trim().isEmpty()) {
            return;
        }
        if (!bocaLista) {
            // el motor todavía no ha contestado: el trozo se guarda y sale en cuanto esté
            enColaLectura.add(texto);
            return;
        }
        boca.speak(texto, boca.isSpeaking() ? TextToSpeech.QUEUE_ADD : TextToSpeech.QUEUE_FLUSH,
                null, "cort-lector");
    }

    /** El paso de la lectura: 1,0 es el normal y 2,0 releer volando. Se mide en el aparato. */
    public void ritmo(float factor) {
        pasoLectura = factor;
        if (bocaLista && boca != null) {
            // sobre `VELOCIDAD`, no en vez de ella: el paso normal tiene que sonar igual
            // que el resto de CORT en la PC
            boca.setSpeechRate(VELOCIDAD * factor);
        }
    }

    /** Callar ahora: lo que espera un lector es un botón, no esperar a que se acabe. */
    public void callar() {
        enCola = null;
        enColaLectura.clear();
        if (boca != null) {
            boca.stop();
        }
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
     * Escucha un dictado. Debe llamarse con el permiso ya concedido. Con el motor
     * de Android hay una condición más: `SpeechRecognizer` no funciona en un hilo
     * de trabajo, así que esa rama se arranca desde el hilo de la interfaz. La
     * rama de Vosk abre su propio hilo y puede llamarse desde cualquiera.
     */
    public void escuchar(Context contexto, final AlOir callback) {
        oyente = callback;
        if (motor != null && motor.listo()) {
            dictadoLocal = true;
            motor.escuchar(callback, medidor);
            return;
        }
        dictadoLocal = false;
        if (oido == null) {
            oido = SpeechRecognizer.createSpeechRecognizer(contexto.getApplicationContext());
            oido.setRecognitionListener(new Escucha());
        }
        Intent intento = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intento.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intento.putExtra(RecognizerIntent.EXTRA_LANGUAGE, IDIOMA);
        intento.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1);
        // No se pide modo sin conexión: desde un `SpeechRecognizer` ordinario no
        // hay forma honesta de exigirlo, y prometerlo sería mentir. Por eso el
        // respaldo se anuncia como respaldo en `oido()`.
        intento.putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, contexto.getPackageName());
        try {
            oido.startListening(intento);
        } catch (SecurityException sinPermiso) {
            callback.fallo("falta el permiso de micrófono");
        } catch (Exception cualquierCosa) {
            callback.fallo("el reconocimiento de voz de este teléfono no respondió");
        }
    }

    /**
     * Qué oído está mandando ahora mismo, en español. Se muestra en la cara: la
     * diferencia entre «Vosk dentro del teléfono» y «el motor de Android, que va
     * por internet» es justamente lo que la dueña pidió que no le escondieran.
     */
    public String oido() {
        if (motor != null && motor.listo()) {
            return "Vosk dentro del teléfono (sin red)";
        }
        if (motor != null && motor.estado() != Motor.SIN_MODELO) {
            return "todavía " + motor.estadoTexto() + "; use el motor de Android";
        }
        return "el motor de voz del aparato";
    }

    /** Tiempo del último dictado local, en milisegundos (cero si aún no hay ninguno). */
    public long ultimoDictadoMs() {
        return motor == null ? 0L : motor.ultimoDictadoMs;
    }

    public void dejarDeEscuchar() {
        if (motor != null) {
            motor.para();
        }
        if (oido != null) {
            oido.cancel();
        }
    }

    public void cerrar() {
        if (motor != null) {
            // Se suelta el micrófono, no el modelo: cargar 39,8 MB otra vez cada
            // vez que la cara se remonta costaría segundos por nada.
            motor.para();
        }
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
            // Si el dictado lo está resolviendo Vosk en su propio hilo, el motor
            // de Android no tiene nada que decir: sin esta guarda la cara vería
            // dos respuestas —la buena y un «no te oí»— del mismo intento.
            if (dictadoLocal || oyente == null) {
                return;
            }
            oyente.fallo(motivo(codigo));
        }

        @Override
        public void onResults(Bundle datos) {
            if (dictadoLocal) {
                return;
            }
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
