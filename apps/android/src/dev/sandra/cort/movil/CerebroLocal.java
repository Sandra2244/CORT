package dev.sandra.cort.movil;

import android.app.ActivityManager;
import android.content.Context;
import android.content.SharedPreferences;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * El cerebro GGUF dentro del teléfono (U1). Java decide qué modelo, cuándo cabe y
 * dónde se pinta; el C++ (`apps/android/jni/cort_motor.cpp`) es lo único que habla
 * con llama.cpp. Nadie más toca la librería nativa.
 *
 * Tres cosas escritas antes del código, porque son las que se pueden romper mañana:
 *
 * 1. **La librería nativa puede faltar.** El APK se arma con las `.so` que saca
 *    `motor-local.yml`; si un día ese artefacto no está, `System.loadLibrary` lanza
 *    `UnsatisfiedLinkError`. Eso no es un cierre: es una respuesta. CORT sigue
 *    valiendo con la nube o con sus 33 reglas y la pantalla dice por qué.
 * 2. **El modelo NO viaja en el APK.** 752 880 160 bytes de qwen2.5-1,5B q2_k (peso
 *    medido el 2026-11-05 en el árbol público de Hugging Face, `Qwen/Qwen2.5-1.5B-
 *    Instruct-GGUF`, sha256 5ede348e…5b3a) se bajan aparte, verificables por suma,
 *    y viven en el carbajo de la app. Borrar la app los borra: se avisa en la pantalla.
 * 3. **La puerta es RAM libre, no la del catálogo.** `cabe` (holgada) pide el
 *    archivo entero más una reserva de contexto; como el motor mapea el GGUF con
 *    mmap, por debajo aún se puede intentar (`sePuedeIntentar`). La verdad la dice
 *    el intento y la medida de tokens/s, no la estimación.
 */
public class CerebroLocal {

    /** La dueña ve las palabras salir una a una, no la respuesta de golpe. */
    public interface Oyente {
        void token(String pieza);
    }

    public static final String PREFERENCIAS = "cort-cerebro";
    /** `auto` = teléfono si cabe, si no la PC/nube. `local` fuerza el GGUF. `nube` lo salta. */
    public static final String CLAVE_MODO = "modo";
    public static final String CLAVE_ACTIVO = "activo";

    private static final Object CERRADURA = new Object();
    private static volatile boolean nativaCargada;
    private static String falloNativo = "";

    private final Context contexto;
    private final SharedPreferences prefs;
    private File activo;
    private int codigo = -1;         // lo que devolvió nativeAbrir; -1 es «no se intentó»

    public CerebroLocal(Context contexto) {
        this.contexto = contexto.getApplicationContext();
        this.prefs = contexto.getSharedPreferences(PREFERENCIAS, Context.MODE_PRIVATE);
    }

    /**
     * La misma voz que `Nube.preguntar` (esa cadena está ahí desde `v0.15.0`): el
     * GGUF y la nube tienen que contestar igual de corto, si no el teléfono cambia
     * de carácter según qué camino eligió y la dueña lo nota. Va en el `system`,
     * nunca en el historial, por el mismo motivo que allí se explica.
     */
    public static String sistemaCort(String memoria) {
        return "Eres CORT, el asistente local de Sandra Lopez, hablando desde su "
                + "teléfono Android. Responde en español, en dos o tres frases como "
                + "mucho, sin markdown y sin listas. Si no sabes algo, dilo corto y "
                + "no lo inventes."
                + (memoria == null || memoria.isEmpty() ? "" : " Datos que ya conoces: "
                        + memoria);
    }

    // ---------------------------------------------------------------- nativo

    static {
        try {
            System.loadLibrary("cortmotor");
            nativaCargada = true;
        } catch (UnsatisfiedLinkError algo) {
            nativaCargada = false;
            // Sin esto la pantalla no tendría número que dar: sólo el motivo.
            falloNativo = algo.getMessage() == null ? algo.toString() : algo.getMessage();
        }
    }

    private static native void nativeIniciar();
    private static native String nativeSistema();
    private static native String nativeBackends();
    private static native void nativeInterrumpe();
    private static native void nativeOir(Object escucha);
    private static native int nativeAbrir(String ruta, int contexto, int hilos);
    private static native void nativeCerrar();
    private static native int nativeHayCerebro();
    private static native String nativeUltimaMedida();
    private static native String nativePreguntar(String[] roles, String[] textos,
                                                 int maxTokens, float temperatura);
    private static native void nativeAjustarMuestreo(float temperatura, int semilla);

    /** Si la librería del motor está en este APK. No dice nada del modelo. */
    public static boolean hayLibreria() {
        return nativaCargada;
    }

    public static String motivoSinLibreria() {
        return nativaCargada ? "" : falloNativo;
    }

    /** La arquitectura del aparato dicha por el propio motor, para copiarla en el informe. */
    public static String infoSistema() {
        return nativaCargada ? nativeSistema() : "sin librería nativa (" + falloNativo + ")";
    }

    /**
     * Los backends dichos por el motor. `try/catch` y no más: JNI resuelve cada
     * símbolo en el momento de llamarlo, así que un APK armado con un artefacto
     * `motor-local` viejo (sin `nativeBackends`) cargaba la librería bien y reventaba
     * al pintar la pantalla. Un nombre que falta no puede tumbar la cara.
     */
    public static String backends() {
        if (!nativaCargada) {
            return "ninguno";
        }
        try {
            return nativeBackends();
        } catch (UnsatisfiedLinkError algo) {
            return "sin `nativeBackends` en esta .so";
        }
    }

    // ------------------------------------------------------------------ puertas

    /**
     * Reserva estimada para la caché clave-valor y los búferes de cálculo. No es
     * medición: el contexto de 1024-2048 tokens de estos modelos pide decenas de MB
     * y se deja margen. Si no alcanza, `nativeAbrir` devuelve 2 y se dice.
     */
    public static final long RESERVA_CONTEXTO = 200L * 1024 * 1024;

    /** Bytes libres ahora mismo en ESTE teléfono, no los que anuncia el catálogo. */
    public long memoriaLibre() {
        ActivityManager sistema =
                (ActivityManager) contexto.getSystemService(Context.ACTIVITY_SERVICE);
        ActivityManager.MemoryInfo libre = new ActivityManager.MemoryInfo();
        sistema.getMemoryInfo(libre);
        return libre.availMem;
    }

    /**
     * Puerta holgada: el archivo entero residente más la reserva. El motor mapea
     * con mmap (pesos = páginas desalojables), así que esto es comodidad, no un
     * requisito físico: por debajo se puede intentar.
     */
    public boolean cabe(long bytesDelModelo) {
        return memoriaLibre() > bytesDelModelo + RESERVA_CONTEXTO;
    }

    /**
     * Suelo del intento: media puerta holgada. Con mmap el kernel desaloja lo que
     * no cabe; por debajo de la mitad, el teléfono se arrastraría y CORT lo dice
     * en vez de fingir.
     */
    public boolean sePuedeIntentar(long bytesDelModelo) {
        return memoriaLibre() > bytesDelModelo / 2 + RESERVA_CONTEXTO / 2;
    }

    public String falta(long bytesDelModelo) {
        return puertaMB(bytesDelModelo) + " MB libres";
    }

    /** La puerta holgada en MB binarios: el único número que pintan cara y Almacén. */
    public static long puertaMB(long bytesDelModelo) {
        return (bytesDelModelo + RESERVA_CONTEXTO) / 1024 / 1024;
    }

    /** El sitio donde viven los cerebros bajados: carbajo de la app, se borra con ella. */
    public static File carbajo(Context contexto) {
        File externo = contexto.getExternalFilesDir("modelos");
        return externo != null ? externo : new File(contexto.getFilesDir(), "modelos");
    }

    public static File archivoDe(Context contexto, String nombre) {
        return new File(carbajo(contexto), nombre);
    }

    // ---------------------------------------------------------------- catálogo

    /**
     * Una fila de `assets/cerebros.json`. Está aquí y no sólo en `Cerebros` porque
     * la ruta automática necesita saber qué archivo abrir, con qué contexto y con
     * cuántos hilos, y eso es dato del catálogo: duplicarlo en la pantalla y en el
     * encaminador es la forma clásica de que uno de los dos se quede antiguo.
     */
    public static final class Ficha {
        public String id, nombre, archivo, url, sha256, nota;
        public long bytes;
        public int contexto, hilos;
    }

    /** Los cerebros ofrecidos, en el orden del archivo (el más chico primero). */
    public static List<Ficha> catalogo(Context contexto) {
        List<Ficha> lista = new ArrayList<>();
        try (InputStream entrada = contexto.getAssets().open("cerebros.json")) {
            byte[] buffer = new byte[entrada.available()];
            int leido = 0;
            while (leido < buffer.length) {
                int n = entrada.read(buffer, leido, buffer.length - leido);
                if (n <= 0) {
                    break;
                }
                leido += n;
            }
            JSONArray cerebros = new JSONObject(new String(buffer, 0, leido,
                    StandardCharsets.UTF_8)).optJSONArray("cerebros");
            for (int i = 0; cerebros != null && i < cerebros.length(); i++) {
                JSONObject j = cerebros.getJSONObject(i);
                Ficha f = new Ficha();
                f.id = j.getString("id");
                f.nombre = j.getString("nombre");
                f.archivo = j.getString("archivo");
                f.url = j.getString("url");
                f.sha256 = j.getString("sha256");
                f.nota = j.optString("nota", "");
                f.bytes = j.getLong("bytes");
                f.contexto = j.optInt("contexto", 2048);
                f.hilos = j.optInt("hilos", 2);
                lista.add(f);
            }
        } catch (IOException | org.json.JSONException roto) {
            // Catálogo roto = sin cerebro local, y `estado()` lo dice con la causa.
            avisoCatalogo = roto.getMessage() == null ? roto.toString() : roto.getMessage();
        }
        return lista;
    }

    private static String avisoCatalogo = "";

    public static String avisoDeCatalogo() {
        return avisoCatalogo;
    }

    /**
     * Si ya hay algún GGUF del catálogo bajado y entero en el teléfono. Lo pregunta
     * `AutoCerebro` para no duplicar lo que ella ya bajó a mano: la lista del almacén
     * es suya, y llenarle el disco con un segundo modelo «por si acaso» no es ayuda.
     */
    public boolean tieneAlguno() {
        for (Ficha f : catalogo(contexto)) {
            File archivo = archivoDe(contexto, f.archivo);
            if (archivo.isFile() && archivo.length() == f.bytes) {
                return true;
            }
        }
        return false;
    }

    /**
     * El modelo que la ruta va a usar: primero el que ella eligió y sigue en disco;
     * si no queda ninguno elegido, el **primero del catálogo que esté bajado y que
     * quepa en la RAM libre de ahora**. Si tampoco, `null` y la cara usa otro camino.
     */
    public Ficha elegido() {
        List<Ficha> lista = catalogo(contexto);
        String guardado = prefs.getString(CLAVE_ACTIVO, "");
        for (Ficha f : lista) {
            if (f.archivo.equals(guardado) && archivoDe(contexto, f.archivo).isFile()) {
                return f;
            }
        }
        for (Ficha f : lista) {
            if (archivoDe(contexto, f.archivo).isFile() && sePuedeIntentar(f.bytes)) {
                return f;
            }
        }
        return null;
    }

    /**
     * El portón de la ruta, dicho una sola vez para que `Cara` y `Nexo` no lo
     * reescriban cada uno a su manera: con `nube` el GGUF no entra; con `auto` se
     * intenta si hay suelo de mmap; con `local` se intenta aunque apriete.
     *
     * Bloquea (abrir 752 MB del disco tarda): sólo se llama desde un hilo.
     */
    public boolean asegurar() {
        if (abierto()) {
            return true;
        }
        if ("nube".equals(modo())) {
            return false;
        }
        Ficha f = elegido();
        if (f == null) {
            return false;
        }
        if ("auto".equals(modo()) && !sePuedeIntentar(f.bytes)) {
            return false;
        }
        return cargar(archivoDe(contexto, f.archivo), f.contexto, f.hilos) == 0;
    }

    /**
     * La vuelta entera de la ruta, en un solo sitio para que `Cara` y `Nexo` no la
     * reescriban cada uno a su manera: si el modo y la RAM dejan, contesta el GGUF;
     * si no, `null` y la cara pregunta a la nube o propone aprender.
     *
     * **Bloquea** (abrir el modelo tarda segundos y generar más), así que va en su
     * hilo, y **nunca lanza**: un cerebro que se cae no puede dejar muda a la cara,
     * que es justo lo que esta rama vino a arreglar. El tope de 120 tokens existe por
     * lo mismo — en un teléfono lento una vuelta sin tope se alarga hasta que la dueña
     * cierra la app. Cuánto tarda de verdad se mide en su A16 (está pendiente).
     */
    public String contestar(String dicho, String memoria) {
        return contestar(sistemaCort(memoria), dicho, null, null, 120, 0.7f);
    }

    /**
     * La vuelta con conversación continua (F20d): `sistema` es el carácter que arma
     * `Consticion` desde `assets/consticion.json`, `historial` son los turnos ya
     * dichos de viejos a nuevos, y `oyente` recibe cada pieza según el nativo la
     * genera — es lo que permite que la cara escriba mientras CORT piensa en vez de
     * esperar la frase entera. `null` en historial u oyente vale: sin historial es
     * una pregunta suelta, sin oyente se devuelve el texto completo al final.
     */
    public String contestar(String sistema, String dicho, List<String[]> historial,
                            Oyente oyente, int maxTokens, float temperatura) {
        try {
            if (!asegurar()) {
                return null;
            }
            List<String[]> vueltas = new ArrayList<>();
            if (historial != null) {
                vueltas.addAll(historial);
            }
            vueltas.add(new String[] {"user", dicho});
            return preguntar(sistema, vueltas, oyente, maxTokens, temperatura);
        } catch (UnsatisfiedLinkError | RuntimeException cualquierCosa) {
            return null;
        }
    }

    /** Por qué la ruta no usó el teléfono, en una línea que se puede imprimir. */
    public String porqueNoLocal() {
        if (!nativaCargada) {
            return "sin librería nativa en el APK";
        }
        if ("nube".equals(modo())) {
            return "el modo elegido es PC o nube";
        }
        if (elegido() == null) {
            return "ningún cerebro bajado en el almacén";
        }
        if (!sePuedeIntentar(elegido().bytes)) {
            return "RAM muy justa para intentarlo: hay " + memoriaLibre() / 1024 / 1024
                    + " MB libres";
        }
        return "el archivo no abrió";
    }

    // --------------------------------------------------------------- cargar/uso

    /**
     * Abre el GGUF. Se llama desde un hilo aparte: leer 752 MB del disco y repartir
     * la caché tarda segundos, y la cara congelada es peor que una cara que avisa.
     */
    public int cargar(File gguf, int contextoTokens, int hilos) {
        synchronized (CERRADURA) {
            if (!nativaCargada) {
                return -1;
            }
            if (gguf == null || !gguf.isFile()) {
                return 1;
            }
            if (activo == gguf && nativeHayCerebro() == 1) {
                return codigo;                   // ya estaba abierto: no se paga dos veces
            }
            nativeIniciar();
            codigo = nativeAbrir(gguf.getAbsolutePath(), contextoTokens, hilos);
            if (codigo == 0) {
                activo = gguf;
                prefs.edit().putString(CLAVE_ACTIVO, gguf.getName()).apply();
                nativeAjustarMuestreo(0.7f, (int) (System.currentTimeMillis() % 100000));
            } else {
                activo = null;
            }
            return codigo;
        }
    }

    public void cerrar() {
        synchronized (CERRADURA) {
            if (nativaCargada) {
                nativeCerrar();
            }
            activo = null;
            codigo = -1;
        }
    }

    public boolean abierto() {
        return nativaCargada && activo != null && codigo == 0 && nativeHayCerebro() == 1;
    }

    public File modeloActivo() {
        return activo;
    }

    public void interrumpir() {
        if (nativaCargada) {
            nativeInterrumpe();
        }
    }

    /** `tokens=..&prepar_ms=..&gen_ms=..&contexto=..` de la última vuelta. */
    public String ultimaMedida() {
        return nativaCargada ? nativeUltimaMedida() : "";
    }

    /**
     * Una vuelta de conversación. `historial` son los turnos ya dichos, de viejos a
     * nuevos; la cara manda siempre todo el historial y el nativo limpia la caché
     * antes de procesar, así que no hay estado que se acumule por detrás.
     *
     * Bloquea: se llama desde un hilo, nunca desde la interfaz.
     */
    public String preguntar(String sistema, List<String[]> historial, Oyente oyente,
                            int maxTokens, float temperatura) {
        synchronized (CERRADURA) {
            if (!abierto()) {
                return null;
            }
            List<String> roles = new ArrayList<>();
            List<String> textos = new ArrayList<>();
            if (sistema != null && !sistema.isEmpty()) {
                roles.add("system");
                textos.add(sistema);
            }
            for (String[] turno : historial) {
                if (turno == null || turno.length < 2 || turno[1].isEmpty()) {
                    continue;
                }
                roles.add(turno[0]);
                textos.add(turno[1]);
            }
            roles.add("assistant");
            textos.add("");                      // el hueco que rellena el modelo
            nativeOir(oyente);
            nativeAjustarMuestreo(temperatura, (int) (System.currentTimeMillis() % 100000));
            String[] r = roles.toArray(new String[0]);
            String[] t = textos.toArray(new String[0]);
            String salida = nativePreguntar(r, t, maxTokens, temperatura);
            nativeOir(null);
            return salida == null || salida.isEmpty() ? null : salida;
        }
    }

    // ------------------------------------------------------------------- modo

    public String modo() {
        String guardado = prefs.getString(CLAVE_MODO, "auto");
        return Arrays.asList("auto", "local", "nube").contains(guardado) ? guardado : "auto";
    }

    public void ponerModo(String modo) {
        prefs.edit().putString(CLAVE_MODO, modo).apply();
    }

    /** Lo que la pantalla de enlace y Ajustes imprimen sin que nadie tenga que adivinar. */
    public String estado() {
        if (!nativaCargada) {
            return "sin librería nativa: " + falloNativo;
        }
        String guardado = prefs.getString(CLAVE_ACTIVO, "");
        if (abierto()) {
            return "abierto: " + activo.getName() + " · " + backends() + " · " + ultimaMedida();
        }
        if (codigo == 1) {
            return "el archivo " + guardado + " no abrió (¿cortado o cambiado?)";
        }
        if (codigo == 2) {
            return "sin memoria para el contexto: hay " + memoriaLibre() / 1024 / 1024
                    + " MB libres y el modelo pide más";
        }
        return "sin cerebro abierto (" + porqueNoLocal() + ").";
    }
}
