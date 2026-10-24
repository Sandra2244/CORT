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

    /** La petición inmutable, con su `Builder`, como la de Android. */
    public static class AudioFocusRequest {
        public final int foco;
        public final AudioAttributes attrs;
        public final boolean pausaAlDuckear;
        public final OnAudioFocusChangeListener oyente;

        private AudioFocusRequest(Builder b) {
            this.foco = b.foco;
            this.attrs = b.attrs;
            this.pausaAlDuckear = b.pausaAlDuckear;
            this.oyente = b.oyente;
        }

        public static class Builder {
            private final int foco;
            private AudioAttributes attrs = null;
            private boolean pausaAlDuckear = true;
            private OnAudioFocusChangeListener oyente = null;

            public Builder(int foco) { this.foco = foco; }

            public Builder setAudioAttributes(AudioAttributes a) { this.attrs = a; return this; }

            public Builder setWillPauseWhenDucked(boolean pausa) { this.pausaAlDuckear = pausa; return this; }

            public Builder setOnAudioFocusChangeListener(OnAudioFocusChangeListener o) {
                this.oyente = o; return this;
            }

            public AudioFocusRequest build() { return new AudioFocusRequest(this); }
        }
    }

    public int requestAudioFocus(AudioFocusRequest peticion) {
        pedidos++;
        ultimo = peticion == null ? null : peticion.attrs;
        return AUDIOFOCUS_REQUEST_GRANTED;
    }

    public void abandonAudioFocusRequest(AudioFocusRequest peticion) { soltados++; }

    public void abandonAudioFocus(OnAudioFocusChangeListener oyente) { soltados++; }
}
