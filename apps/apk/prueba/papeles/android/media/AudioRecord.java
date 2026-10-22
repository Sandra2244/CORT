package android.media;

/* El gemelo de papel de `android.media.AudioRecord`. No simula el micrófono:
   simula las FIRMAS, que es lo que `kotlinc` comprueba, y deja un cebo
   (`ALIMENTAR`) para que la prueba de `Oido` pueda meterle muestras de verdad y
   ver el bucle entero — el mismo bucle que en el teléfono lee del micro. */
public final class AudioRecord {

    public static final int STATE_INITIALIZED = 1;
    public static final int STATE_UNINITIALIZED = 0;
    public static final int RECORDSTATE_STOPPED = 0;
    public static final int RECORDSTATE_RECORDING = 3;

    /** Lo que devuelve `read(...)`: `null` = silencio, o las muestras que sean. */
    public static short[] ALIMENTAR = null;
    public static int CODIGO_DE_READ = 0;        // < 0 imita el micrófono robado

    private final int boceto;
    private int estado = STATE_INITIALIZED;
    private int grabando = RECORDSTATE_STOPPED;

    public AudioRecord(int fuente, int tasa, int canales, int formato, int tamanoBoceto) {
        this.boceto = tamanoBoceto;
    }

    public static int getMinBufferSize(int tasa, int canales, int formato) { return 3200; }

    public int getState() { return estado; }
    public int getRecordingState() { return grabando; }

    public void startRecording() { grabando = RECORDSTATE_RECORDING; }
    public void stop() { grabando = RECORDSTATE_STOPPED; }
    public void release() { estado = STATE_UNINITIALIZED; }

    public int read(short[] destino, int offset, int cantidad) {
        if (estado != STATE_INITIALIZED) return -1;
        if (CODIGO_DE_READ < 0) return CODIGO_DE_READ;
        int n = Math.min(cantidad, destino.length - offset);
        short[] fuente = ALIMENTAR;
        for (int i = 0; i < n; i++) destino[offset + i] = fuente == null ? 0 : fuente[i % fuente.length];
        return n;
    }
}
