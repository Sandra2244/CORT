package android.media;

/* Gemelo de papel de `AudioManager`, lo justo para que `Oido.kt` compile y para
   que la prueba pueda CONTAR que el foco se pide y se devuelve (F12).

   En Android `requestAudioFocus` devuelve un entero y el sistema decide; aquí
   devuelve `AUDIOFOCUS_REQUEST_GRANTED` siempre, porque lo que se mide en el
   portátil no es la política de audio del teléfono —eso sólo se ve en un
   aparato— sino que el código pida el foco ANTES de abrir el micro y lo suelte
   en el `finally`. Los contadores son la evidencia de ese orden. */
public class AudioManager {

    public static final int AUDIOFOCUS_LOSS = -1;
    public static final int AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK = 3;
    public static final int AUDIOFOCUS_REQUEST_GRANTED = 1;
    public static final int AUDIOFOCUS_REQUEST_FAILED = 0;

    /** Cuántas veces se pidió y se devolvió el foco: la prueba los lee. */
    public int pedidos = 0;
    public int soltados = 0;
    /** Lo último que se pidió, para poder mirar el uso y el tipo. */
    public AudioAttributes ultimo = null;

    public interface OnAudioFocusChangeListener {
        void onAudioFocusChange(int cambio);
    }

    /* `AudioFocusRequest` NO es una clase anidada de `AudioManager`: vive en
       `android.media` como clase propia (API 26). El gemelo lo copió anidado y
       por eso el portátil compilaba un código que el SDK de verdad rechaza; el
       pipeline lo cazó en `v0.2.38-demo`. Ahora el gemelo tiene su archivo. */

    public int requestAudioFocus(AudioFocusRequest peticion) {
        pedidos++;
        ultimo = peticion == null ? null : peticion.attrs;
        return AUDIOFOCUS_REQUEST_GRANTED;
    }

    public void abandonAudioFocusRequest(AudioFocusRequest peticion) { soltados++; }

    public void abandonAudioFocus(OnAudioFocusChangeListener oyente) { soltados++; }
}
