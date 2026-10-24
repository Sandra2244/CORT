package android.media;

/* Gemelo de papel de `android.media.AudioFocusRequest` (API 26). En Android es
   una clase propia, NO anidada dentro de `AudioManager`; el gemelo anterior la
   puso anidada y por eso `prueba-oido.sh` daba verde con `Oido.kt` roto: el SDK
   real contestó `unresolved reference: AudioFocusRequest` en `v0.2.38-demo`.
   Aquí vive en su archivo, como en la plataforma.

   Lo que se mide en el portátil no es la política de audio del teléfono —eso
   sólo se ve en un aparato— sino que la petición lleve el uso y el tipo
   correctos y que su `Builder` no invente campos. */
public class AudioFocusRequest {
    public final int foco;
    public final AudioAttributes attrs;
    public final boolean pausaAlDuckear;
    public final AudioManager.OnAudioFocusChangeListener oyente;

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
        private AudioManager.OnAudioFocusChangeListener oyente = null;

        public Builder(int foco) { this.foco = foco; }

        public Builder setAudioAttributes(AudioAttributes a) { this.attrs = a; return this; }

        public Builder setWillPauseWhenDucked(boolean pausa) { this.pausaAlDuckear = pausa; return this; }

        public Builder setOnAudioFocusChangeListener(AudioManager.OnAudioFocusChangeListener o) {
            this.oyente = o; return this;
        }

        public AudioFocusRequest build() { return new AudioFocusRequest(this); }
    }
}
