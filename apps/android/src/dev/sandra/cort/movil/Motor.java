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
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.util.Locale;
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
 * `vosk-model-small-es-0.42` — 39 817 833 bytes — **se baja en el Almacén** desde
 * `cort-v0.16.2`. La ficha de la descarga (URL, peso y suma) está en
 * `assets/oido.json`, fijada contra el zip oficial de alphacephei.com.
 *
 * Por qué el modelo salió del APK: con dos arquitecturas y las `.so` sin
 * comprimir, el archivo entero medía 162 817 475 bytes. Bajado a ~40 KB/s en la
 * casa de la dueña son 70 minutos, se cortó, y Samsung dijo «aplicación no
 * instalada» — que es lo que dice de un archivo truncado, no de un archivo
 * malo. El número de la descarga, no el del teléfono, es lo que había que bajar.
 *
 * Cuatro decisiones escritas antes del código:
 *
 * 1. **El modelo se descomprime la primera vez y no en cada arranque.** `assets`
 *    sólo se puede leer como corriente y el zip bajado vive en `filesDir`; Vosk
 *    necesita un *directorio* con `am/`, `conf/`, `graph/` y `rescorer/`. Se
 *    copia una vez a `filesDir/motor/` y se deja un marcador con el
 *    identificador del modelo; si el marcador falta, o el APK trae un modelo con
 *    otro identificador, se vuelve a descomprimir.
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

    /**
     * F19d — las dos frases que despiertan a CORT. Dos, y no una, porque «oye CORT»
     * es lo que sale dicho de manera natural y «hola CORT» es lo que la dueña pidió
     * escrito; cada palabra extra multiplica los falsos positivos, y en un teléfono
     * que pasa el día encendido eso es batería y avisos que no tocaban.
     */
    public static final String[] PALABRAS = {"hola cort", "oye cort"};

    /**
     * La gramática en el formato que pide `Recognizer(Model, float, String)`: un
     * arreglo JSON de frases con el `"[unk]"` detrás. Ese `"[unk]"` no es relleno:
     * sin él Vosk fuerza la frase conocida más parecida y CORT se despierta con
     * «ola, qué tal». Con él, lo que no sea la palabra sale como `[unk]` y se tira.
     */
    static final String GRAMATICA = armaGramatica(PALABRAS);

    /** El tope de lo que se dice *después* de la palabra: 12 s y vuelve a dormir. */
    static final int MAX_FRASE_MS = 12_000;

    private static String armaGramatica(String[] frases) {
        StringBuilder j = new StringBuilder("[");
        for (int i = 0; i < frases.length; i++) {
            j.append(i == 0 ? "" : ", ").append('"').append(frases[i]).append('"');
        }
        return j.append(", \"[unk]\"]").toString();
    }

    /**
     * Lo que avisa el despertador (F19d). Cuatro cosas distintas porque se muestran
     * distinto: la palabra (el orbe se despierta), la frase dicha después (va al
     * lazo), el nivel (la animación, solo mientras se captura) y el fallo.
     */
    public interface AlEscucha {
        void palabra(String dicha);

        void frase(String dicho);

        void nivel(float alto);

        void fallo(String motivo);
    }

    private static final String ZIP_DENTRO = "motor/vosk-model-small-es-0.42.zip";
    private static final String CARPETA_MODEL = "vosk-model-small-es-0.42";
    private static final String ID_DEL_MODELO = "small-es-0.42";
    private static final String MARCADOR = ".instalado";

    /** La ficha de la descarga: URL, peso y SHA-256 medidos, fijados en `assets/oido.json`. */
    private static final String FICHA_DENTRO = "oido.json";

    /* Los estados que la cara puede enseñar, dichos en español y sin rodeos. */
    public static final int SIN_MODELO = 0;
    public static final int DESCOMPRIMIENDO = 1;
    public static final int CARGANDO = 2;
    public static final int LISTO = 3;
    public static final int ROTO = 4;
    public static final int DESCARGANDO = 5;

    private static final String[] NOMBRES = {
        "sin el modelo de español (se baja en Almacén)", "descomprimiendo el modelo",
        "cargando el modelo", "Vosk listo", "roto", "descargando el modelo"};

    private static Motor unico;

    private final Context contexto;
    private final Handler principal = new Handler(Looper.getMainLooper());

    private volatile int estado = SIN_MODELO;
    private volatile String aviso = "";
    private volatile Model modelo;
    private volatile boolean intentoEmpezado;

    private volatile boolean escuchando;

    /* ---- el despertador (F19d) ----
     * `escuchandoPalabra` es la orden de vivir del hilo `cort-despierta`;
     * `capturaPedida` le dice que deje de vigilar la palabra y oiga la frase ahora
     * (es el ● pulsado con el servicio puesto, para que no haya dos micrófonos);
     * `oyentePendiente`/`medidorPendiente` son la cara que lo pulsó, si lo hizo. */
    private volatile boolean escuchandoPalabra;
    private volatile boolean capturaPedida;
    private volatile AlEscucha despertador;
    private volatile Voz.AlOir oyentePendiente;
    private volatile Voz.AlNivel medidorPendiente;

    /** Duración del último dictado, medida en el teléfono: es el dato que falta. */
    public volatile long ultimoDictadoMs;

    /* Lo que dice `assets/oido.json`. Se leen una vez, en el constructor: si el
     * archivo falta (un APK armado a mano sin el asset) la cara lo confiesa con
     * `sePuedeBajar()` en vez de abrir una conexión vacía. */
    private volatile String urlDelModelo = "";
    private volatile String shaDelModelo = "";
    private volatile String archivoDelModelo = CARPETA_MODEL + ".zip";
    private volatile String idDelFicha = ID_DEL_MODELO;
    private volatile String carpetaDelModelo = CARPETA_MODEL;
    private volatile long bytesDelModelo;

    private volatile long hechoDescarga;
    private volatile boolean descargaEmpezada;

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
        leeFicha();
    }

    /** Lee la ficha de la descarga; si no está o está mal, deja los valores de siempre. */
    private void leeFicha() {
        try (InputStream entrada = contexto.getAssets().open(FICHA_DENTRO)) {
            byte[] b = new byte[8192];
            java.io.ByteArrayOutputStream todo = new java.io.ByteArrayOutputStream();
            int n;
            while ((n = entrada.read(b)) > 0) {
                todo.write(b, 0, n);
            }
            JSONObject ficha = new JSONObject(new String(todo.toByteArray(), "UTF-8"));
            urlDelModelo = ficha.optString("url", "");
            shaDelModelo = ficha.optString("sha256", "").toLowerCase(Locale.ROOT);
            bytesDelModelo = ficha.optLong("bytes", 0L);
            archivoDelModelo = ficha.optString("archivo", CARPETA_MODEL + ".zip");
            carpetaDelModelo = ficha.optString("carpeta", CARPETA_MODEL);
            idDelFicha = ficha.optString("id", ID_DEL_MODELO);
        } catch (Exception noEsta) {
            urlDelModelo = "";
            aviso = "falta " + FICHA_DENTRO + " en el APK";
        }
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
        File carpeta = new File(motorDeDatos(), carpetaDelModelo);
        try {
            if (!instalado(carpeta)) {
                estado = DESCOMPRIMIENDO;
                if (!montaDesdeDisco(carpeta) && !montaDesdeAssets(carpeta)) {
                    estado = SIN_MODELO;
                    aviso = sePuedeBajar()
                            ? "toca «Bajar el oído» en Almacén (" + mb(bytesDelModelo) + " MB)"
                            : "el APK salió sin modelo";
                    return;
                }
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

    /** `filesDir/motor`, donde vive el modelo descomprimido y el zip descargado. */
    private File motorDeDatos() {
        return new File(contexto.getFilesDir(), "motor");
    }

    /** El zip ya bajado (o el que se está reanudando), en `filesDir/motor/`. */
    public File zipDelModelo() {
        return new File(motorDeDatos(), archivoDelModelo);
    }

    /** Cuánto hay que bajar: lo dice la ficha del APK, no un número escrito aquí. */
    public long pesoDelModelo() {
        return bytesDelModelo;
    }

    /** Hay ficha, o sea hay de dónde bajar el modelo. */
    public boolean sePuedeBajar() {
        return !urlDelModelo.isEmpty() && bytesDelModelo > 0;
    }

    public static String mb(long bytes) {
        return String.format(Locale.ROOT, "%.1f", bytes / 1048576.0);
    }

    /**
     * Baja el modelo si hace falta, verifica la suma y monta el oído. Se llama
     * desde el Almacén con un botón; el progreso lo lee la pantalla de
     * `descargaTexto()`, que es también lo que ve la cara.
     */
    public void bajaYMonta() {
        if (descargaEmpezada) {
            return;
        }
        descargaEmpezada = true;
        new Thread(() -> {
            boolean seBajo = true;
            try {
                if (!instalado(new File(motorDeDatos(), carpetaDelModelo))) {
                    descarga();
                }
            } catch (Throwable culpa) {
                seBajo = false;
                estado = ROTO;
                aviso = "la descarga falló: " + detalle(culpa)
                        + " — lo bajado queda, se reanada";
            } finally {
                descargaEmpezada = false;
            }
            // Sólo si la descarga terminó: si no, `abrir()` pisaría el motivo del
            // fallo con un «sin el modelo» que no dice nada de lo que pasó.
            if (seBajo) {
                abrir();
            }
        }, "cort-bajar-oido").start();
    }

    public boolean estaDescargando() {
        return descargaEmpezada;
    }

    /** Lo que el Almacén pinta cada segundo: progreso en % o el motivo del corte. */
    public String descargaTexto() {
        if (descargaEmpezada) {
            long total = bytesDelModelo > 0 ? bytesDelModelo : zipDelModelo().length();
            return "bajando " + mb(hechoDescarga) + " de " + mb(total) + " MB ("
                    + (total > 0 ? (100L * hechoDescarga / total) : 0) + " %)";
        }
        return estadoTexto();
    }

    /**
     * Descarga con resumiendo: si quedó un `.part` de un corte anterior —y el
     * corte de la luz es el caso real de esta casa— se pide `Range` desde donde
     * se paró. Al terminar se calcula la SHA-256 del archivo entero y, si no
     * cuadra, se tira: un zip truncado descomprime a medias y Vosk abre un
     * modelo roto en vez de fallar.
     *
     * El enlace no lleva token ni clave: es el zip público de alphacephei.com
     * fijado en `assets/oido.json`, y por eso puede bajarlo este hilo en vez del
     * `DownloadManager` del sistema (cuyas notificaciones se leen con la pantalla
     * bloqueada y, en otros modelos, llevan la URL escrita).
     */
    private void descarga() throws Exception {
        File destino = zipDelModelo();
        File parcial = new File(destino.getPath() + ".part");
        File padre = parcial.getParentFile();
        if (padre != null && !padre.isDirectory() && !padre.mkdirs()) {
            throw new IOException("no se pudo crear " + padre);
        }
        if (destino.isFile() && destino.length() == bytesDelModelo
                && encajaLaSuma(destino)) {
            hechoDescarga = destino.length();
            return;
        }
        long reanudado = parcial.isFile() ? parcial.length() : 0L;
        hechoDescarga = reanudado;
        HttpURLConnection conexion = (HttpURLConnection) new URL(urlDelModelo).openConnection();
        conexion.setInstanceFollowRedirects(true);
        conexion.setConnectTimeout(20_000);
        conexion.setReadTimeout(60_000);
        if (reanudado > 0) {
            conexion.setRequestProperty("Range", "bytes=" + reanudado + "-");
        }
        estado = DESCARGANDO;
        aviso = "";
        try {
            int codigo = conexion.getResponseCode();
            if (codigo != 200 && codigo != 206) {
                throw new IOException("el servidor respondió " + codigo);
            }
            if (reanudado > 0 && codigo != 206) {
                // Sin `206` el servidor manda el archivo entero desde el byte 0:
                // empezar el `.part` de nuevo, no pegar el resto encima.
                reanudado = 0;
                hechoDescarga = 0;
            }
            try (InputStream entrada = conexion.getInputStream();
                 OutputStream salida = new FileOutputStream(parcial, reanudado > 0)) {
                byte[] b = new byte[65536];
                int n;
                while ((n = entrada.read(b)) > 0) {
                    salida.write(b, 0, n);
                    hechoDescarga += n;
                }
            }
        } finally {
            conexion.disconnect();
        }
        if (parcial.length() != bytesDelModelo) {
            throw new IOException("quedaron " + parcial.length() + " bytes de " + bytesDelModelo
                    + "; se reanada al tocar otra vez");
        }
        String suma = hex(sumarDesde(parcial));
        if (!shaDelModelo.isEmpty() && !shaDelModelo.equals(suma)) {
            parcial.delete();
            throw new IOException("la SHA-256 no cuadra (" + suma.substring(0, 12)
                    + "…); se tiró el archivo");
        }
        if (!parcial.renameTo(destino) && !destino.isFile()) {
            throw new IOException("no se pudo mover el archivo verificado");
        }
    }

    /** El archivo que ya está en disco es el del zip fijado: tamaño y suma. */
    private boolean encajaLaSuma(File archivo) {
        if (shaDelModelo.isEmpty()) {
            return true;
        }
        try {
            return shaDelModelo.equals(hex(sumarDesde(archivo)));
        } catch (Exception algo) {
            return false;
        }
    }

    private static byte[] sumarDesde(File archivo) throws IOException {
        try {
            MessageDigest digiero = MessageDigest.getInstance("SHA-256");
            try (FileInputStream fuente = new FileInputStream(archivo)) {
                byte[] b = new byte[65536];
                int n;
                while ((n = fuente.read(b)) > 0) {
                    digiero.update(b, 0, n);
                }
            }
            return digiero.digest();
        } catch (java.security.NoSuchAlgorithmException imposible) {
            throw new IOException("sin SHA-256 en este Android");
        }
    }

    private static String hex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte u : bytes) {
            sb.append(String.format("%02x", u));
        }
        return sb.toString();
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
     * Descomprime el zip **ya bajado** en el almacén. Se comprueba la suma antes
     * de tocarlo: un `.zip` de 39 817 833 bytes cortado en el byte 30 millones
     * descomprime media carpeta y Vosk abre un modelo a medias en vez de fallar.
     */
    private boolean montaDesdeDisco(File carpetaFinal) {
        File zip = zipDelModelo();
        if (!zip.isFile() || (bytesDelModelo > 0 && zip.length() != bytesDelModelo)
                || !encajaLaSuma(zip)) {
            return false;
        }
        try (InputStream fuente = new FileInputStream(zip)) {
            descomprime(fuente, carpetaFinal);
            return true;
        } catch (Exception algoSaloMal) {
            aviso = "al descomprimir: " + detalle(algoSaloMal);
            return false;
        }
    }

    /** El camino de siempre: el `assets/motor/`, que es como viene el APK desde `cort-v0.17.2`. */
    private boolean montaDesdeAssets(File carpetaFinal) {
        if (!existeModeloEnElAPK()) {
            return false;
        }
        try (InputStream fuente = contexto.getAssets().open(ZIP_DENTRO)) {
            descomprime(fuente, carpetaFinal);
            return true;
        } catch (Exception algoSaloMal) {
            aviso = "al descomprimir: " + detalle(algoSaloMal);
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
            return idDelFicha.equals(new String(guardado, "UTF-8").trim());
        } catch (Exception cualquierCosa) {
            return false;
        }
    }

    private void escribeMarcador(File motor) {
        try {
            escribe(new File(motor, MARCADOR), idDelFicha.getBytes("UTF-8"));
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
     *
     * Borra **sólo la carpeta del modelo**, nunca `motor/` entero: ahí vive el
     * zip que se está descomprimiendo y, si se va, la fuente se corta a medias.
     */
    private void descomprime(InputStream origen, File carpetaFinal) throws IOException {
        File raizDeDatos = contexto.getFilesDir().getCanonicalFile();
        File motor = carpetaFinal.getParentFile();
        borraArbol(carpetaFinal);
        if (!motor.mkdirs() && !motor.isDirectory()) {
            throw new IOException("no se pudo crear la carpeta del modelo");
        }
        try (ZipInputStream zip = new ZipInputStream(origen)) {
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
            throw new IOException("el zip no traía " + carpetaDelModelo);
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
        if (modeloUsado == null) {
            avisa(oyente, null, listo() ? "ya estaba escuchando"
                    : "el oído local no está listo (" + estadoTexto() + ")");
            return;
        }
        // El despertador (F19d) ya tiene el micrófono abierto en `cort-despierta`, y
        // Android no da dos lecturas simultáneas del mismo `AudioRecord`: en vez de
        // montar un segundo hilo se le pasa la orden a ese, que suelta la frase por
        // el oyente que acaba de pedirlo. Dos micrófonos abiertos es la forma clásica
        // de que el teléfono se quede mudo hasta el reinicio.
        if (escuchandoPalabra) {
            oyentePendiente = oyente;
            medidorPendiente = medidor;
            capturaPedida = true;
            return;
        }
        if (escuchando) {
            avisa(oyente, null, "ya estaba escuchando");
            return;
        }
        escuchando = true;
        new Thread(() -> grabaYTranscribe(modeloUsado, oyente, medidor), "cort-micro").start();
    }

    public void para() {
        escuchando = false;
        // Si el ● se había apoyado en el despertador, retirar la orden y su oyente:
        // dejarlos puestos es que la frase llegue a una cara que ya cerró.
        if (escuchandoPalabra) {
            capturaPedida = false;
            oyentePendiente = null;
            medidorPendiente = null;
        }
    }

    public boolean estaEscuchando() {
        return escuchando || capturaPedida;
    }

    /* ---------------------------------------------------------------- despertador */

    /**
     * Poner a CORT a vigilar la palabra de activación (F19d). Abre el micrófono en
     * `cort-despierta` con la gramática cerrada de `GRAMATICA` y no suelta el hilo
     * hasta `dejaLaPalabra()`.
     *
     * Dos guardas escritas, porque las dos se rompen solas:
     *
     * * Sin el modelo español montado no hay gramática que evaluar —el APK delgado
     *   o el teléfono donde la descarga se cortó— y eso se dice, no se calla.
     * * Si el dictado del ● tiene el micrófono abierto, se espera a que lo suelte
     *   antes de abrir el propio: un `AudioRecord` que no se inicializa no es un
     *   fallo de CORT, es Android diciendo «ya lo tiene otra app».
     */
    public void escuchaDePalabra(AlEscucha oyente) {
        final Model modeloUsado;
        synchronized (this) {
            modeloUsado = modelo;
        }
        if (modeloUsado == null) {
            if (oyente != null) {
                oyente.fallo("el oído local no está montado (" + estadoTexto() + ")");
            }
            return;
        }
        if (escuchandoPalabra) {
            despertador = oyente;          // cambiar la cara que escucha, sin otro hilo
            return;
        }
        despertador = oyente;
        escuchandoPalabra = true;
        new Thread(() -> vigilaPalabra(modeloUsado, oyente), "cort-despierta").start();
    }

    /** Quitar la vigilancia. El hilo se sale por su cuenta en cuanto lee el flag. */
    public void dejaLaPalabra() {
        escuchandoPalabra = false;
        capturaPedida = false;
        despertador = null;
    }

    public boolean estaEnDespertar() {
        return escuchandoPalabra;
    }

    /** El ● pulsado con el servicio puesto: oír la frase ya, sin esperar la palabra. */
    public void pideFrase() {
        capturaPedida = true;
    }

    /**
     * El ciclo del despertador. Dos estados y dos reconocedores sobre el mismo
     * `Model` (Vosk permite compartir el modelo; el que guarda el estado de la frase
     * es el reconocedor): **vigilia**, con la gramática cerrada —es lo que corre casi
     * siempre y lo que cuesta batería—, y **captura**, con el modelo abierto, sólo
     * durante los segundos que duran el mandato dicho después de la palabra.
     *
     * `acceptWaveForm` devuelve `true` en el corte de silencio, así que la entrega no
     * lleva temporizador propio: lo que se dijo, se entrega. El único reloj es el
     * techo de `MAX_FRASE_MS`, para que un ruido continuo no deje el micrófono
     * abierto indefinidamente.
     */
    private void vigilaPalabra(Model modeloUsado, AlEscucha oyente) {
        AudioRecord micro = null;
        Recognizer vigilia = null;
        Recognizer captura = null;
        try {
            int min = AudioRecord.getMinBufferSize(MUESTREO,
                    AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT);
            if (min <= 0) {
                if (oyente != null) {
                    oyente.fallo("el micrófono de este teléfono no da 16 kHz mono");
                }
                return;
            }
            vigilia = new Recognizer(modeloUsado, MUESTREO, GRAMATICA);
            byte[] b = new byte[min];
            boolean capturando = false;
            long finCaptura = 0L;
            long inicioCaptura = 0L;
            while (escuchandoPalabra) {
                if (escuchando) {
                    duerme(120);                       // el ● tiene el micrófono: se espera
                    continue;
                }
                if (micro == null) {
                    micro = new AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION,
                            MUESTREO, AudioFormat.CHANNEL_IN_MONO,
                            AudioFormat.ENCODING_PCM_16BIT, min * 4);
                    if (micro.getState() != AudioRecord.STATE_INITIALIZED) {
                        sueltaMicro(micro);
                        micro = null;
                        duerme(800);                   // otra app lo tenía: se reintenta
                        continue;
                    }
                    micro.startRecording();
                }
                int leido = micro.read(b, 0, b.length);
                if (leido <= 0) {
                    continue;
                }
                if (!capturando) {
                    if (capturaPedida) {
                        capturaPedida = false;
                        capturando = true;
                        inicioCaptura = System.currentTimeMillis();
                        finCaptura = inicioCaptura + MAX_FRASE_MS;
                        captura = new Recognizer(modeloUsado, MUESTREO);
                        continue;
                    }
                    // Vigilia: la gramática cerrada y nada de nivel. El orbe no se
                    // paga despierto con el silencio de la casa.
                    if (vigilia.acceptWaveForm(b, leido)) {
                        String dicho = textoDe(vigilia.getResult());
                        if (contienePalabra(dicho)) {
                            avisaPalabra(oyente, dicho);
                            capturando = true;
                            inicioCaptura = System.currentTimeMillis();
                            finCaptura = inicioCaptura + MAX_FRASE_MS;
                            captura = new Recognizer(modeloUsado, MUESTREO);
                        }
                    }
                    continue;
                }
                // Captura: ya sonó la palabra —o la dueña pulsó el ● con el servicio
                // puesto— y lo que se oiga es el mandato.
                final Voz.AlNivel medidor = medidorPendiente;
                if (medidor != null) {
                    final float alto = nivelDe(b, leido);
                    principal.post(() -> medidor.nivel(alto));
                }
                String dicho = "";
                if (captura.acceptWaveForm(b, leido)) {
                    dicho = textoDe(captura.getResult()).trim();
                }
                boolean seAcabo = System.currentTimeMillis() >= finCaptura;
                if (dicho.isEmpty() && !seAcabo) {
                    continue;
                }
                ultimoDictadoMs = System.currentTimeMillis() - inicioCaptura;
                libera(captura);
                captura = null;
                capturando = false;
                libera(vigilia);
                vigilia = new Recognizer(modeloUsado, MUESTREO, GRAMATICA);
                if (!dicho.isEmpty()) {
                    entrega(oyente, dicho);
                } else {
                    sinFrase(oyente);
                }
            }
        } catch (Throwable caida) {
            // `Throwable`, la misma razón de `abrir()`: si la `.so` de Vosk no viajó,
            // JNA suelta `UnsatisfiedLinkError` y es un `Error`. Que lo aguante el
            // despertador, no el teléfono entero.
            if (oyente != null) {
                oyente.fallo(detalle(caida));
            }
        } finally {
            sueltaMicro(micro);
            libera(captura);
            libera(vigilia);
            escuchandoPalabra = false;
            capturaPedida = false;
            oyentePendiente = null;
            medidorPendiente = null;
        }
    }

    /** Si entre las palabras del modelo cerrado salió alguna de activación. */
    static boolean contienePalabra(String dicho) {
        String limpio = Cerebro.normaliza(dicho == null ? "" : dicho.replace("[unk]", " "));
        if (limpio.isEmpty()) {
            return false;
        }
        for (String p : PALABRAS) {
            if (limpio.contains(p)) {
                return true;
            }
        }
        return false;
    }

    private void avisaPalabra(AlEscucha oyente, String dicho) {
        if (oyente != null) {
            principal.post(() -> oyente.palabra(dicho));
        }
    }

    /** Entregando la frase: a la cara que pulsó el ● si lo hizo, si no al servicio. */
    private void entrega(AlEscucha oyente, String frase) {
        final Voz.AlOir pendiente = oyentePendiente;
        oyentePendiente = null;
        medidorPendiente = null;
        if (pendiente != null) {
            avisa(pendiente, frase, null);
            return;
        }
        if (oyente != null) {
            principal.post(() -> oyente.frase(frase));
        }
    }

    /** Doce segundos de ruido y ni una palabra: se avisa a la cara y se vuelve a la vigilia. */
    private void sinFrase(AlEscucha oyente) {
        final Voz.AlOir pendiente = oyentePendiente;
        oyentePendiente = null;
        medidorPendiente = null;
        if (pendiente != null) {
            avisa(pendiente, null, "no te oí después de la palabra");
            return;
        }
        if (oyente != null) {
            principal.post(() -> oyente.fallo("desperté, pero no oí el mandato"));
        }
    }

    /**
     * Cerrar un `Recognizer`. Va aparte porque el cierre puede fallar y un cierre que
     * falla en medio del ciclo no puede tumbar la escucha: lo que se pierde es un
     * decodificador, no el oído.
     */
    private static void libera(Recognizer r) {
        if (r == null) {
            return;
        }
        try {
            r.close();
        } catch (Exception yaCerrado) {
            // nada que hacer: el puntero nativo ya se fue
        }
    }

    /** Soltar el `AudioRecord` sea cual sea el estado en que lo encuentra. */
    private static void sueltaMicro(AudioRecord micro) {
        if (micro == null) {
            return;
        }
        try {
            if (micro.getRecordingState() == AudioRecord.RECORDSTATE_RECORDING) {
                micro.stop();
            }
        } catch (Exception yaParado) {
            // no grababa: queda liberarlo igual
        }
        micro.release();
    }

    /** Esperar sin tumbar el hilo; el `interrupt` se re-lanza porque el sistema lo pide. */
    private static void duerme(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException nadieDuerme) {
            Thread.currentThread().interrupt();
        }
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
        escuchandoPalabra = false;
        capturaPedida = false;
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
