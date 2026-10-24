package android.media;

/* Gemelo de papel de `AudioAttributes`, sólo lo que `Oido.kt` usa para pedir el
   foco: el uso (asistente) y el tipo (voz). En Android es una clase inmutable con
   un `Builder`; aquí igual, para que el Kotlin compile sin cambiar una línea y el
   `AudioManager` de papel pueda guardar lo que le pidieron.

   Los valores numéricos son los de Android (USAGE_ASSISTANT = 16,
   CONTENT_TYPE_SPEECH = 1). No se usan para decidir nada en la prueba: son para
   que un `toString` o una comprobación futura digan algo coherente. */
public class AudioAttributes {

    public static final int USAGE_ASSISTANT = 16;
    public static final int CONTENT_TYPE_SPEECH = 1;

    public final int usage;
    public final int contentType;

    private AudioAttributes(int usage, int contentType) {
        this.usage = usage;
        this.contentType = contentType;
    }

    public static class Builder {
        private int usage = 0;
        private int contentType = 0;

        public Builder setUsage(int uso) { this.usage = uso; return this; }

        public Builder setContentType(int tipo) { this.contentType = tipo; return this; }

        public AudioAttributes build() { return new AudioAttributes(usage, contentType); }
    }
}
