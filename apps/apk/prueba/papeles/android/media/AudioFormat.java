package android.media;

/* Dos constantes de `android.media.AudioFormat`, las que mira `Oido.kt`. Gemelo
   de papel: sirve para que `kotlinc` compruebe nombres y tipos sin SDK. */
public final class AudioFormat {
    public static final int CHANNEL_IN_MONO = 0x00000010;
    public static final int ENCODING_PCM_16BIT = 2;
    private AudioFormat() {}
}
