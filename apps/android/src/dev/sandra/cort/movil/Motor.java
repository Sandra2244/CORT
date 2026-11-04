package dev.sandra.cort.movil;

import android.content.Context;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.os.Handler;
import android.os.Looper;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import org.json.JSONObject;
import org.vosk.Model;
import org.vosk.Recognizer;

/**
 * El oído de verdad: **Vosk dentro del teléfono**, sin IP, sin servidor y sin
 * el motor de voz de Google.
 *
 * Por qué existe esta clase. Hasta ahora el dictado salía de `Voz.escuchar()`,
 * que usa `android.speech.SpeechRecognizer` — el reconocimiento que trae el
 * aparato. En un Samsung con los servicios de Google eso funciona **por
 * internet**: el audio sale del teléfono y vuelve escrito. Es la razón por la
 * que el motivo de fallo decía «el motor de voz de Android necesita internet».
 * CORT prometía ser local y su oído no lo era.
 *
 * Aquí el audio no sale del aparato. `libvosk.so` y `libjnidispatch.so` viajan
 * dentro del APK (`compilar.sh` los saca de los AAR oficiales de Maven Central,
 * con la suma SHA-256 fijada en `deps.txt`), y el modelo español
 * `vosk-model-small-es-0.42` viaja en `assets/motor/` — 39 817 833 bytes, con
 * su suma en el mismo archivo—. Eso es lo que contesta a «el APK no pesa nada»:
 * pesa porque el oído está dentro, no porque le sobre código.
 *
 * Tres decisiones escritas antes del código:
 *
 * 1. **El modelo se descomprime la primera vez y no en cada arranque.** `assets`
 *    sólo se puede leer como corriente; Vosk necesita un *directorio* con `am/`,
 *    `conf/`, `graph/` y `rescorer/`. Se copia una vez a `filesDir/motor/` y se
 *    deja un marcador con el identificador del modelo; si el marcador falta, o
 *    el APK trae un modelo con otro identificador, se vuelve a descomprimir.
 *    Coste: unos segundos y ~90 MB en los datos de la app la primera vez.
 * 2. **Si el modelo no está, CORT no se queda muda: cede el oído.** El APK
 *    delgado —el que se compila sin `vendor/`— o un teléfono donde la
 *    descompresión falló siguen dictando por `SpeechRecognizer`. La cara dice
 *    cuál se usó; no se finge un oído local que no está.
 * 3. **Nada de AndroidX ni de los servicios de escucha de la biblioteca.** El
 *    ciclo de `Model` y `Recognizer` es JNA sobre un puntero nativo: se crean y
 *    se cierran en el mismo hilo, y el único hilo que abre el micrófono es el de
 *    esta clase. Un `Model` se puede compartir entre varios `Recognizer`, pero
 *    aquí sólo hay un dictado a la vez.
 *
 * Lo que **no** está verificado: el tiempo real de carga y los MB de RAM que
 * ocupa en el A16. Sin el teléfono delante no se puede afirmar, y por eso aquí
 * sólo se dan los números de los archivos (39,8 MB el modelo, 10,0 MB la
 * biblioteca) y la cara muestra el tiempo medido de cada dictado.
 */
public final class Motor {

    /** Frecuencia del modelo pequeño de español: 16 kHz, mono, PCM de 16 bits. */
    static final int MUESTREO = 16000;

    /** El dictado se corta solo: sin esto el micrófono quedaría abierto si la cara se va. */
    static final int MAX_SEGUNDOS = 20;

    private static final String ZIP_DENTRO = "motor/vosk-model-small-es-0.42.zip";
    private static final String CARPETA_MODEL = "vosk-model-small-es-0.42";
    private static final String ID_DEL_MODELO = "small-es-0.42";
    private static final String MARCADOR = ".instalado";

    /* Los estados que la cara puede enseñar, dichos en español y sin rodeos. */
    public static final int SIN_MODELO = 0;
    public static final int DESCOMPRIMIENDO = 1;
    public static final int CARGANDO = 2;
    public static final int LISTO = 3;
    public static final int ROTO = 4;

    private static final String[] NOMBRES = {
        "sin modelo dentro del APK", "descomprimiendo el modelo",
        "cargando el modelo", "Vosk listo", "roto"};

    private static Motor unico;

    private final Context contexto;
    private final Handler principal = new Handler(Looper.getMainLooper());

    private volatile int estado = SIN_MODELO;
    private volatile String aviso = "";
    private volatile Model modelo;
    private volatile boolean intentoEmpezado;

    private volatile boolean escuchando;

    /** Duración del último dictado, medida en el teléfono: es el dato que falta. */
    public volatile long ultimoDictadoMs;

    /** Una sola instancia: el modelo son decenas de MB y no se cargan dos veces. */
    public static Motor compartido(Context contexto) {
        synchronized (Motor.class) {
            if (unico == null) {
                unico = new Motor(contexto.getApplicationContext());
            }
            return unico;
        }
    }

    private Motor(Context contexto) {
        this.contexto = contexto;
    }

    /* ---------------------------------------------------------------- preparación */

    /**
     * Descomprime (si hace falta) y carga el modelo en un hilo aparte. Se llama
     * una vez al montar la cara: es idempotente y no corta la interfaz, porque
     * el primer arranque tarda lo que tarda descomprimir 39,8 MB.
     */
    public void prepara() {
        if (intentoEmpezado) {
            return;
        }
        synchronized (this) {
            if (intentoEmpezado) {
                return;
            }
            intentoEmpezado = true;
        }
        new Thread(this::abrir, "cort-oido").start();
    }

    private void abrir() {
        if (!existeModeloEnElAPK()) {
            estado = SIN_MODELO;
            aviso = "el APK salió sin modelo";
            return;
        }
        File carpeta = new File(new File(contexto.getFilesDir(), "motor"), CARPETA_MODEL);
        try {
            if (!instalado(carpeta)) {
                estado = DESCOMPRIMIENDO;
                descomprime(carpeta);
            }
            estado = CARGANDO;
            Model nuevo = new Model(carpeta.getAbsolutePath());
            synchronized (this) {
                modelo = nuevo;
            }
            estado = LISTO;
            aviso = "";
        } catch (Throwable caida) {
            // `Throwable` y no `Exception`: si `libvosk.so` no viajó en el APK o
            // el teléfono es de otra arquitectura, JNA suelta `UnsatisfiedLinkError`,
            // que es un `Error`. Que se lo trague el oído, no la cara.
            estado = ROTO;
            aviso = detalle(caida);
        }
    }

    public boolean listo() {
        return estado == LISTO && modelo != null;
    }

    public int estado() {
        return estado;
    }

    /** Lo que la cara escribe en su registro: qué oído manda ahora mismo. */
    public String estadoTexto() {
        String nombre = estado >= 0 && estado < NOMBRES.length ? NOMBRES[estado] : "desconocido";
        return aviso.isEmpty() ? nombre : nombre + " — " + aviso;
    }

    public String aviso() {
        return aviso;
    }

    private boolean existeModeloEnElAPK() {
        try (InputStream entrada = contexto.getAssets().open(ZIP_DENTRO)) {
            return entrada.read() >= 0;
        } catch (IOException noEsta) {
            return false;
        }
    }

    /**
     * Vale sólo si la carpeta existe y el marcador dice el identificador del
     * modelo que este APK espera. Así, una actualización con otro modelo se
     * descomprime sola en vez de servir el viejo.
     */
    private boolean instalado(File carpeta) {
        File marcador = new File(carpeta.getParentFile(), MARCADOR);
        if (!carpeta.isDirectory() || !marcador.isFile()) {
            return false;
        }
        try {
            byte[] guardado = leeArchivo(marcador);
            return ID_DEL_MODELO.equals(new String(guardado, "UTF-8").trim());
        } catch (Exception cualquierCosa) {
            return false;
        }
    }

    private void escribeMarcador(File motor) {
        try {
            escribe(new File(motor, MARCADOR), ID_DEL_MODELO.getBytes("UTF-8"));
        } catch (IOException noSePudoAnotar) {
            // Sin marcador la próxima vez se vuelve a descomprimir: lento, no roto.
        }
    }

    private static byte[] leeArchivo(File archivo) throws IOException {
        try (FileInputStream fuente = new FileInputStream(archivo)) {
            byte[] todo = new byte[(int) archivo.length()];
            int leido = 0;
            while (leido < todo.length) {
                int n = fuente.read(todo, leido, todo.length - leido);
                if (n <= 0) {
                    break;
                }
                leido += n;
            }
            return todo;
        }
    }

    private static void escribe(File destino, byte[] contenido) throws IOException {
        File padre = destino.getParentFile();
        if (padre != null && !padre.isDirectory() && !padre.mkdirs()) {
            throw new IOException("no se pudo crear " + padre.getName());
        }
        try (OutputStream salida = new FileOutputStream(destino)) {
            salida.write(contenido);
        }
    }

    /**
     * Descompresión con guarda contra el truco del `../`: un zip puede declarar
     * un archivo llamado `../../otro/aplicacion.xml` y escribir fuera del
     * directorio de la app. El modelo de Vosk no lo hace, pero este código no lo
     * sabe: se comprueba la ruta resuelta y si sale del sitio, se aborta.
     */
    private void descomprime(File carpetaFinal) throws IOException {
        File raizDeDatos = contexto.getFilesDir().getCanonicalFile();
        File motor = carpetaFinal.getParentFile();
        borraArbol(motor);
        if (!motor.mkdirs() && !motor.isDirectory()) {
            throw new IOException("no se pudo crear la carpeta del modelo");
        }
        try (ZipInputStream zip = new ZipInputStream(contexto.getAssets().open(ZIP_DENTRO))) {
            ZipEntry entrada;
            byte[] b = new byte[65536];
            while ((entrada = zip.getNextEntry()) != null) {
                File destino = new File(motor, entrada.getName()).getCanonicalFile();
                if (!destino.getPath().startsWith(raizDeDatos.getPath() + File.separator)) {
                    throw new IOException("el zip pide escribir fuera de la app: " + entrada.getName());
                }
                if (entrada.isDirectory()) {
                    if (!destino.mkdirs() && !destino.isDirectory()) {
                        throw new IOException("no se pudo crear " + destino.getName());
                    }
                    continue;
                }
                File padre = destino.getParentFile();
                if (padre != null && !padre.isDirectory() && !padre.mkdirs()) {
                    throw new IOException("no se pudo crear " + padre.getName());
                }
                try (OutputStream salida = new FileOutputStream(destino)) {
                    int n;
                    while ((n = zip.read(b)) > 0) {
                        salida.write(b, 0, n);
                    }
                }
                zip.closeEntry();
            }
        }
        if (!carpetaFinal.isDirectory()) {
            throw new IOException("el zip no traía " + CARPETA_MODEL);
        }
        escribeMarcador(motor);
    }

    private static void borraArbol(File donde) {
        if (donde == null || !donde.exists()) {
            return;
        }
        if (donde.isDirectory()) {
            File[] hijos = donde.listFiles();
            if (hijos != null) {
                for (File hijo : hijos) {
                    borraArbol(hijo);
                }
            }
        }
        // Sin comprobar el código: si no se borra, la escritura de encima falla y
        // `abrir()` lo cuenta como modelo roto. No hay nada que recoverar aquí.
        donde.delete();
    }

    /* --------------------------------------------------------------------- dictado */

    /**
     * Escucha hasta que se llame a `para()` o pasen `MAX_SEGUNDOS` segundos. El
     * callback llega en el hilo de la interfaz, que es donde `Cara` toca los
     * colores del orbe y escribe en el registro.
     */
    public void escuchar(final Voz.AlOir oyente, final Voz.AlNivel medidor) {
        final Model modeloUsado;
        synchronized (this) {
            modeloUsado = modelo;
        }
        if (modeloUsado == null || escuchando) {
            avisa(oyente, null, listo() ? "ya estaba escuchando"
                    : "el oído local no está listo (" + estadoTexto() + ")");
            return;
        }
        escuchando = true;
        new Thread(() -> grabaYTranscribe(modeloUsado, oyente, medidor), "cort-micro").start();
    }

    public void para() {
        escuchando = false;
    }

    public boolean estaEscuchando() {
        return escuchando;
    }

    private void grabaYTranscribe(Model modeloUsado, Voz.AlOir oyente, Voz.AlNivel medidor) {
        AudioRecord micro = null;
        Recognizer reconocedor = null;
        String dicho = "";
        boolean huboCorte = false;
        long inicio = System.currentTimeMillis();
        try {
            int min = AudioRecord.getMinBufferSize(MUESTREO,
                    AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT);
            if (min <= 0) {
                avisa(oyente, null, "el micrófono de este teléfono no da 16 kHz mono");
                return;
            }
            micro = new AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION, MUESTREO,
                    AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, min * 4);
            if (micro.getState() != AudioRecord.STATE_INITIALIZED) {
                avisa(oyente, null, "nadie quiso abrir el micrófono");
                return;
            }
            reconocedor = new Recognizer(modeloUsado, MUESTREO);
            byte[] b = new byte[min];
            micro.startRecording();
            while (escuchando && (System.currentTimeMillis() - inicio) < MAX_SEGUNDOS * 1000L) {
                int n = micro.read(b, 0, b.length);
                if (n <= 0) {
                    continue;
                }
                if (medidor != null) {
                    final float nivel = nivelDe(b, n);
                    principal.post(() -> medidor.nivel(nivel));
                }
                // Vosk avisa (`true`) cuando detecta silencio: ahí la frase está
                // completa y se puede leer el resultado sin esperar al final.
                if (reconocedor.acceptWaveForm(b, n)) {
                    dicho = une(dicho, textoDe(reconocedor.getResult()));
                    huboCorte = true;
                }
            }
            String cola = textoDe(reconocedor.getFinalResult());
            if (!cola.isEmpty()) {
                dicho = une(dicho, cola);
            }
            ultimoDictadoMs = System.currentTimeMillis() - inicio;
            boolean porTiempo = (System.currentTimeMillis() - inicio) >= MAX_SEGUNDOS * 1000L;
            if (dicho.trim().isEmpty()) {
                // Los tres casos se dicen distinto porque se sienten distinto:
                // silencio, palabras que el modelo no conoce, y el corte de 20 s.
                avisa(oyente, null, porTiempo ? "corté el dictado a los " + MAX_SEGUNDOS + " s"
                        : (huboCorte ? "no entendí nada" : "no te oí"));
            } else {
                avisa(oyente, dicho.trim(), null);
            }
        } catch (Throwable caida) {
            ultimoDictadoMs = System.currentTimeMillis() - inicio;
            avisa(oyente, null, detalle(caida));
        } finally {
            if (micro != null) {
                try {
                    if (micro.getRecordingState() == AudioRecord.RECORDSTATE_RECORDING) {
                        micro.stop();
                    }
                } catch (Exception ignorado) {
                }
                micro.release();
            }
            if (reconocedor != null) {
                reconocedor.close();
            }
            escuchando = false;
        }
    }

    /* ------------------------------------------------------------------ utilidades */

    private void avisa(Voz.AlOir oyente, String texto, String motivo) {
        if (oyente == null) {
            return;
        }
        if (texto != null) {
            principal.post(() -> oyente.dijo(texto));
        } else {
            final String causa = motivo == null ? "no te oí" : motivo;
            principal.post(() -> oyente.fallo(causa));
        }
    }

    /** El modelo de español devuelve las palabras en `text`; si no hay, cadena vacía. */
    private static String textoDe(String json) {
        try {
            return new JSONObject(json).optString("text", "");
        } catch (Exception formatoRaro) {
            return "";
        }
    }

    private static String une(String previo, String nuevo) {
        if (nuevo == null || nuevo.trim().isEmpty()) {
            return previo;
        }
        return previo.trim().isEmpty() ? nuevo : previo.trim() + " " + nuevo.trim();
    }

    /**
     * Nivel del micrófono en 0..1 para el orbe: la raíz media de las muestras que
     * Vosk está leyendo en este instante. `Voz` normaliza de otra forma porque el
     * `SpeechRecognizer` entrega decibelios; aquí se parte del PCM crudo, cuyo
     * tope es 32 767. La división suaviza para que el orbe no se pegue al máximo
     * con la voz normal.
     */
    private static float nivelDe(byte[] b, int n) {
        long muestras = n / 2;
        if (muestras <= 0) {
            return 0f;
        }
        double suma = 0.0;
        for (int i = 0; i + 1 < n; i += 2) {
            int corta = (short) ((b[i] & 0xff) | (b[i + 1] << 8));
            suma += (double) corta * (double) corta;
        }
        double raiz = Math.sqrt(suma / (double) muestras);
        double f = raiz / 8000.0;
        return f > 1.0 ? 1.0f : (float) f;
    }

    /** El nombre técnico en español claro, para que un fallo se pueda entender. */
    private static String detalle(Throwable caida) {
        String clase = caida.getClass().getSimpleName();
        String mensaje = caida.getMessage();
        if (mensaje == null || mensaje.trim().isEmpty()) {
            return clase.toLowerCase();
        }
        return clase + ": " + mensaje.trim();
    }

    /**
     * El puntero nativo vive mientras el proceso exista: esto se llama al cerrar
     * la cara y deja el motor preparado por si la cara vuelve a montarse.
     */
    public synchronized void cerrar() {
        escuchando = false;
        if (modelo != null) {
            try {
                modelo.close();
            } catch (Throwable yaNoImporta) {
            }
            modelo = null;
            estado = SIN_MODELO;
            intentoEmpezado = false;
        }
    }
}
