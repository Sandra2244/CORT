package dev.sandra.cort.movil;

import android.os.Build;
import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.EOFException;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;
import java.util.Base64;
import java.util.Locale;
import java.util.concurrent.LinkedBlockingDeque;
import java.util.concurrent.TimeUnit;
import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSession;
import javax.net.ssl.SSLSocket;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;
import org.json.JSONObject;

/**
 * El WebSocket **de verdad** del teléfono (F20a): RFC 6455 escrito a mano sobre
 * `java.net.Socket` y `javax.net.ssl.SSLSocket`.
 *
 * Hasta ahora el aparato no hablaba con nadie: `apps/android/web/cort-android.js`
 * sustituye `window.WebSocket` por un invento local que llama a `Nexo.java`, así que
 * la cara de la PC que se veía en el `WebView` era la cara del propio teléfono. Para
 * que los paneles viajen entre las dos máquinas hace falta un cliente que abra el
 * puerto del core y hable el protocolo del puente.
 *
 * **Por qué a mano.** La cadena de compilación de este APK es `aapt2` +
 * `javac --release 11` + `d8` (`apps/android/compilar.sh`): no hay Gradle, no hay
 * AndroidX y no hay OkHttp — en la Classmate de 1,8 GiB un `gradle build` la congeló.
 * Sólo están el JDK y `android.jar` (API 34, mínimo 26). Antes que meter una
 * dependencia nueva con su descarga y su suma, se escriben aquí los trescientos
 * renglones que faltan: la máscara del cliente, los dos formatos de longitud y el
 * reensamblado de fragmentos. Es código aburrido y comprobable contra el RFC.
 *
 * **La llave va siempre.** El puente de la PC (`cort-bridge/cort_server.py`) perdona
 * el `?token=` cuando quien llama es loopback, porque ése es el navegador del propio
 * portátil. El teléfono **nunca** es loopback para la PC: por eso la llave viaja en el
 * query del handshake y además dentro del primer cuadro (`mobile_auth`), que es lo
 * que la PC usa para apuntar el emparejamiento. Sin llave no se intenta: se dice con
 * palabras y no se reintenta, porque insistir no va a fabricar un token.
 *
 * **El candado (F21) y la decisión del pin.** Un certificado de la casa es
 * autofirmado: `cort-bridge/cort_tls.py` lo genera con los SAN de las IP de la LAN y
 * publica su huella (SHA-256 del DER, en hex). Aquí eso se traduce en una regla
 * única: `wss://` **sólo** se abre si `fijarHuella()` recibió esa huella y el
 * certificado que llega tiene exactamente esa suma. Sin huella fijada, `wss://` se
 * rechaza. No hay modo «confía en todos»: un `TrustManager` que devuelve sin mirar
 * convierte el candado en decoración y deja el puente a merced de cualquiera que
 * esté en el wifi de la cafetería, que es justo el agujero que esta fase cierra.
 * Como la cadena no la valida nadie, el nombre del certificado tampoco se puede
 * validar contra una CA: el `HostnameVerifier` de aquí acepta **sólo** el host
 * fijado y sólo si la huella coincide, y se dice honestamente que lo que autentica
 * es la huella, no el nombre.
 *
 * **Lo que NO está implementado**, dicho antes de que alguien lo suponga:
 * - `permessage-deflate` ni ninguna extensión: no se pide en el handshake y los bits
 *   RSV que lleguen encendidos se toman como error de protocolo;
 * - subprotocolos (`Sec-WebSocket-Protocol`): el puente habla JSON pelado;
 * - cuadros binarios: se avisa por `estado()` y se ignoran, porque el vocabulario del
 *   puente (`type`/`action`, el mismo de `Nexo.envia`) es texto;
 * - fragmentación **de salida**: lo que se manda sale en un solo cuadro con FIN=1
 *   (sí se reensamblan los fragmentos que lleguen);
 * - `wss://` sin huella, y proxies HTTP: no hay túnel CONNECT.
 *
 * **Nunca la llave en pantalla.** Todo lo que sale por `estado()` pasa por
 * `sinLlave()`, y las URL se dicen sin query. Una notificación y la pantalla de
 * bloqueo muestran estas frases: es la misma regla que sigue `ServicioEscucha` con
 * lo que oye el micrófono.
 *
 * Nada de aquí toca la interfaz de Android: los cuadros y los dichos salen por
 * `AlCuadro` en el hilo del lector, y quien llama decide si los sube con
 * `runOnUiThread`, igual que hace `Nexo.envia`.
 */
public class PuenteWs {

    /** El camino del WebSocket en el core. Lo sirve `ws_handler` de `cort_server.py`. */
    public static final String RUTA_WS = "/ws";

    /** El GUID del RFC 6455 §1.3: no es un número nuestro, es el del protocolo. */
    private static final String GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";

    /**
     * El techo de un mensaje. Se reutiliza `Puente.MAX_BYTES` (262144), que es el
     * mismo número que usan el puente de memoria y Python: un teléfono de gama de
     * entrada no puede reservar memoria sin techo porque sí.
     */
    private static final int TOPE_MENSAJE = Puente.MAX_BYTES;

    /** El techo de las cabeceras del handshake: si no caben aquí, no es nuestro servidor. */
    private static final int TOPE_CABECERAS = 16384;

    private static final int CONEXION_MS = 8000;

    /**
     * El read es bloqueante (`setSoTimeout(0)`) y el latido lo vigila otro hilo. La
     * PC ya manda su heartbeat cada 25 s (`WebSocketResponse(heartbeat=25)`), así que
     * un minuto sin nada es raro y minuto y medio sin nada es un enlace muerto: el
     * wifi del teléfono se duerme y el socket queda abierto sin que nadie lo sepa.
     */
    private static final long SIN_NADA_MS = 60_000L;
    private static final long SIN_PONG_MS = 30_000L;
    private static final long PASO_LATIDO_MS = 1000L;

    /** La cola de salida. Con 64 cuadros pendientes el problema no es la cola. */
    private static final int COLA_MAX = 64;

    private static final int OP_CONTINUACION = 0x0;
    private static final int OP_TEXTO = 0x1;
    private static final int OP_BINARIO = 0x2;
    private static final int OP_CIERRE = 0x8;
    private static final int OP_PING = 0x9;
    private static final int OP_PONG = 0xA;

    private static final int CIERRE_NORMAL = 1000;
    private static final int CIERRE_PROTOCOLO = 1002;
    private static final int CIERRE_DEMASIADO = 1009;

    /** Lo que la cara quiere saber: un cuadro JSON y una frase en español. */
    public interface AlCuadro {
        void cuadro(String json);

        void estado(String dicho);
    }

    private final String url;
    private final String llave;
    private final AlCuadro oyente;
    private final SecureRandom azar = new SecureRandom();
    private final LinkedBlockingDeque<String> cola = new LinkedBlockingDeque<>(COLA_MAX);

    /** Un solo candado para escribir: el lector (pong), el latido (ping) y la cola. */
    private final Object candadoEscritura = new Object();

    private volatile String huella;
    private volatile String version = "";
    private volatile String ultimoEstado = "sin conectar todavía";
    private volatile boolean cerrado;
    private volatile boolean sinReintento;
    private volatile boolean vivo;
    private volatile long ultimoTrafico;
    private volatile long pingEnviado;

    /**
     * Si el `mobile_auth_result` llegó con `ok:true` en esta sesión. Sirve para
     * devolver la espera de reconexión a 1 s: un enlace que estuvo bueno y se cayó
     * merece un reintento rápido, no los 30 s de una PC apagada.
     */
    private volatile boolean autenticado;

    private volatile Socket zocalo;
    private volatile OutputStream salida;
    private volatile Thread hiloVida;
    private Thread hiloEscritura;
    private Thread hiloLatido;

    /**
     * `urlConToken` puede ser `ws://` o `wss://`; si viene de la cara, pásala antes
     * por `aWs()`. La llave se saca del query con `Puente.tokenDe`, que es el mismo
     * corte que usan `Sincroniza` y el puente de memoria: no hay dos formas de leer
     * un token en este APK.
     */
    public PuenteWs(String urlConToken, AlCuadro oyente) {
        this.url = urlConToken == null ? "" : urlConToken.trim();
        this.llave = Puente.tokenDe(this.url);
        this.oyente = oyente;
    }

    /**
     * La huella del certificado de la casa: SHA-256 del DER en hex (64 caracteres),
     * la misma cuenta que imprime `cort-bridge/cort_tls.py` y
     * `openssl x509 -fingerprint -sha256`. Se aceptan dos puntos y espacios por si
     * se pega de la salida de openssl, y se compara sin mirar mayúsculas.
     *
     * Sin esto (o con algo que no sea una huella) `wss://` **no se abre**: es la
     * decisión de la fase, no un descuido. `ws://` sigue funcionando sin huella,
     * porque en la LAN de casa sin TLS es lo que hay hoy y no se finge lo contrario.
     */
    public void fijarHuella(String sha256Hex) {
        if (sha256Hex == null) {
            huella = null;
            return;
        }
        String limpio = sha256Hex.replaceAll("[:\\s]", "").toLowerCase(Locale.ROOT);
        if (limpio.length() != 64 || !limpio.matches("[0-9a-f]{64}")) {
            huella = null;
            dice("la huella del certificado no son 64 caracteres hex: "
                    + "no abriré el enlace cifrado hasta tener la buena");
            return;
        }
        huella = limpio;
    }

    /**
     * El `versionName` del APK para el cuadro `mobile_auth`. Hace falta este setter
     * porque leerlo pide un `Context` (`getPackageManager().getPackageInfo(...)`, lo
     * que hace `Nexo.versionApp()`) y este constructor no recibe ninguno a
     * propósito: así la clase se puede probar sin aparato. Quien monta el puente le
     * pasa la versión antes de `conectar()`; si no, viaja vacía y la PC escribe
     * «no dicha» en vez de inventarla.
     */
    public void fijarVersion(String versionName) {
        version = versionName == null ? "" : versionName.trim();
    }

    /**
     * Arranca su propio hilo y devuelve enseguida. Idempotente: si ya hay un hilo
     * vivo no se abre otro enlace. Después de `cerrar()` no se reabre —para eso se
     * construye otro `PuenteWs`— porque «cerrado» tiene que significar cerrado.
     */
    public synchronized void conectar() {
        if (cerrado) {
            dice("este puente ya se cerró: abre uno nuevo para volver a conectar");
            return;
        }
        if (hiloVida != null && hiloVida.isAlive()) {
            return;
        }
        if (url.isEmpty()) {
            dice("no sé a qué portátil llamar: no hay dirección de WebSocket");
            return;
        }
        if (!url.startsWith("ws://") && !url.startsWith("wss://")) {
            dice("la dirección del puente no es ws:// ni wss://: " + sinQuery(url));
            return;
        }
        sinReintento = false;
        hiloVida = new Thread(this::vivir, "cort-ws");
        hiloVida.setDaemon(true);
        hiloVida.start();
    }

    /**
     * Encola un cuadro para el hilo de escritura. Se puede llamar desde cualquier
     * hilo (el del JS, el del oído, el de la interfaz) y nunca espera a la red.
     *
     * Sin enlace abierto el cuadro **se tira y se dice**: guardarlo para «luego» es
     * cómo una orden de hace diez minutos se ejecuta sola cuando la PC vuelve.
     */
    public void enviar(String json) {
        if (json == null || json.trim().isEmpty()) {
            return;
        }
        if (!conectado()) {
            dice("no hay enlace con la PC: descarté un cuadro que quería salir");
            return;
        }
        if (json.getBytes(StandardCharsets.UTF_8).length > TOPE_MENSAJE) {
            dice("un cuadro queria salir con más de " + TOPE_MENSAJE
                    + " bytes: lo descarté, ese es el tope del puente");
            return;
        }
        if (!cola.offer(json)) {
            String viejo = cola.poll();
            cola.offer(json);
            dice("la cola de salida está llena (" + COLA_MAX + " cuadros): "
                    + (viejo == null ? "descarté uno" : "descarté el más viejo")
                    + " para que salga el nuevo");
        }
    }

    /**
     * El cierre limpio: cuadro de cierre con código 1000, y se acabaron los
     * reintentos. El cuadro lo escribe un hilo aparte porque escribir en un socket
     * con el buffer lleno puede bloquear, y a quien cierra (la interfaz) no se la
     * puede dejar esperando a la red.
     */
    public void cerrar() {
        if (cerrado) {
            return;
        }
        cerrado = true;
        vivo = false;
        Thread despedida = new Thread(() -> {
            try {
                escribeCierre(CIERRE_NORMAL, "el teléfono cerró el puente");
            } catch (Exception yaNoEsta) {
                // El enlace ya estaba roto: no hay nada que despedir.
            } finally {
                cierraZocalo();
                Thread vida = hiloVida;
                if (vida != null) {
                    vida.interrupt();
                }
            }
        }, "cort-ws-cierre");
        despedida.setDaemon(true);
        despedida.start();
        dice("cerré el enlace con la PC");
    }

    /**
     * Si el WebSocket está abierto (handshake hecho). El emparejamiento es cosa
     * aparte: la cara se enterá por el cuadro `mobile_auth_result`, que también se
     * le entrega como cualquier otro.
     */
    public boolean conectado() {
        Socket z = zocalo;
        return vivo && !cerrado && z != null && z.isConnected() && !z.isClosed();
    }

    /** La última frase dicha, siempre sin la llave. */
    public String ultimoEstado() {
        return ultimoEstado;
    }

    /**
     * `http` → `ws`, `https` → `wss`, conservando camino y query; sin camino (o con
     * `/`) se pone `/ws`, que es la ruta del core. `ws://` y `wss://` pasan tal cual,
     * así que llamarla dos veces no rompe nada.
     *
     * El puerto sí se toca, y por el mismo motivo que `Puente.urlDelPuente`: la cara
     * vive en `PUERTO_CARA` (8766) y el WebSocket en `PUERTO_API` (8765). Si la
     * dirección trae el de la cara, o no trae ninguno, se pone el del core; cualquier
     * otro puerto explícito se respeta (un banco de pruebas escucha donde le digan).
     * El **camino** no se reescribe: quien tenga guardado
     * `http://ip:8766/index.html?token=…` tiene que quitarle el `/index.html` antes,
     * porque aquí no se adivina si un camino es la cara o un endpoint.
     *
     * `null` = eso no es una dirección que se pueda convertir.
     */
    public static String aWs(String httpUrl) {
        if (httpUrl == null) {
            return null;
        }
        String limpio = httpUrl.trim();
        String esquema;
        int salta;
        if (limpio.startsWith("https://")) {
            esquema = "wss://";
            salta = "https://".length();
        } else if (limpio.startsWith("http://")) {
            esquema = "ws://";
            salta = "http://".length();
        } else if (limpio.startsWith("wss://")) {
            esquema = "wss://";
            salta = "wss://".length();
        } else if (limpio.startsWith("ws://")) {
            esquema = "ws://";
            salta = "ws://".length();
        } else {
            return null;
        }
        String resto = limpio.substring(salta);
        int finAutoridad = resto.length();
        for (int i = 0; i < resto.length(); i++) {
            char c = resto.charAt(i);
            if (c == '/' || c == '?' || c == '#') {
                finAutoridad = i;
                break;
            }
        }
        String autoridad = resto.substring(0, finAutoridad);
        String colaUrl = resto.substring(finAutoridad);
        if (autoridad.isEmpty()) {
            return null;
        }
        String host = autoridad;
        int puerto = Puente.PUERTO_API;
        // IPv6 entre corchetes: el último ':' de "::1" no es un puerto.
        int corchete = autoridad.lastIndexOf(']');
        int dosPuntos = autoridad.indexOf(':', Math.max(0, corchete + 1));
        if (corchete < 0) {
            dosPuntos = autoridad.lastIndexOf(':');
        }
        if (dosPuntos >= 0) {
            host = autoridad.substring(0, dosPuntos);
            String numero = autoridad.substring(dosPuntos + 1);
            if (!numero.isEmpty()) {
                try {
                    puerto = Integer.parseInt(numero);
                } catch (NumberFormatException noEsPuerto) {
                    return null;
                }
                if (puerto == Puente.PUERTO_CARA) {
                    puerto = Puente.PUERTO_API;
                }
            }
        }
        if (host.isEmpty() || puerto <= 0 || puerto > 65535) {
            return null;
        }
        int dondeQuery = colaUrl.indexOf('?');
        String camino = dondeQuery < 0 ? colaUrl : colaUrl.substring(0, dondeQuery);
        if (camino.isEmpty() || "/".equals(camino)) {
            camino = RUTA_WS + (dondeQuery < 0 ? "" : colaUrl.substring(dondeQuery));
        }
        return esquema + host + ":" + puerto + camino;
    }

    /* ------------------------------------------------------------------ el lazo */

    /**
     * El hilo de vida: abre, autentica, lee hasta que se caiga, y vuelve a abrir con
     * espera creciente (1, 2, 4, 8 y luego 30 s). Los reintentos se dicen siempre.
     *
     * Dos fallos **no** se reintentan, y es a propósito: el emparejamiento rechazado
     * (`mobile_auth_result` con `ok:false`) y el 401/403 del handshake. Reintentar
     * cada 30 s con una llave que no vale es martillear la PC de por vida sin que
     * nada pueda mejorar: lo que arregla eso es escanear el QR otra vez, y se dice.
     */
    private void vivir() {
        int intento = 0;
        while (!cerrado && !sinReintento) {
            boolean limpio = false;
            try {
                if (llave.isEmpty()) {
                    sinReintento = true;
                    dice("el enlace no trae llave (?token=…): fuera del propio equipo "
                            + "la PC no abre el puente. Vuelve a escanear el QR del portátil");
                    return;
                }
                if (url.startsWith("wss://") && huella == null) {
                    sinReintento = true;
                    dice("el enlace es cifrado pero no tengo la huella del certificado "
                            + "de tu PC: no lo abro a ciegas. Fija la huella que imprime "
                            + "CORT en el portátil");
                    return;
                }
                dice("conectando con " + sinQuery(url) + "…");
                DataInputStream entrada = saluda();
                // El primer cuadro del teléfono, antes que nada: es el que la PC usa
                // para apuntar el emparejamiento en su estado.
                escribe(OP_TEXTO, cuadroDeAuth());
                vivo = true;
                ultimoTrafico = System.currentTimeMillis();
                pingEnviado = 0L;
                arrancaEscritura();
                arrancaLatido();
                limpio = escuchar(entrada);
            } catch (IOException red) {
                if (!cerrado) {
                    dice("el enlace con " + sinQuery(url) + " se cayó: " + sinLlave(motivo(red)));
                }
            } catch (Exception raro) {
                if (!cerrado) {
                    dice("el puente no pudo abrirse: " + sinLlave(motivo(raro)));
                }
            } finally {
                if (autenticado) {
                    intento = 0;      // estuvo emparejado: la próxima caída se reintenta pronto
                }
                suelta();
            }
            if (cerrado || sinReintento) {
                break;
            }
            intento++;
            long espera = intento <= 4 ? 1000L * (1L << (intento - 1)) : 30_000L;
            dice((limpio ? "la PC cerró el enlace" : "sin enlace con la PC")
                    + ": intento " + intento + " en " + (espera / 1000L) + " s");
            try {
                Thread.sleep(espera);
            } catch (InterruptedException despierta) {
                Thread.currentThread().interrupt();
                return;
            }
        }
    }

    /** Se puso en marcha con el handshake; el `mobile_auth_result` dice si vale. */

    /** Se puso en marcha con el handshake; el `mobile_auth_result` dice si vale. */

    /**
     * El socket y el saludo del RFC 6455 §4. Devuelve el flujo ya colocado justo
     * detrás de la línea en blanco de las cabeceras, listo para leer cuadros.
     */
    private DataInputStream saluda() throws IOException {
        String esquema = url.startsWith("wss://") ? "wss://" : "ws://";
        String resto = url.substring(esquema.length());
        int finAutoridad = resto.length();
        for (int i = 0; i < resto.length(); i++) {
            char c = resto.charAt(i);
            if (c == '/' || c == '?' || c == '#') {
                finAutoridad = i;
                break;
            }
        }
        String autoridad = resto.substring(0, finAutoridad);
        String camino = resto.substring(finAutoridad);
        if (camino.isEmpty() || camino.startsWith("?")) {
            camino = RUTA_WS + camino;
        }
        int corte = camino.indexOf('#');
        if (corte >= 0) {
            camino = camino.substring(0, corte);      // un fragmento no viaja al servidor
        }
        String host = autoridad;
        int puerto = Puente.PUERTO_API;
        int corchete = autoridad.lastIndexOf(']');
        int dosPuntos = corchete >= 0 ? autoridad.indexOf(':', corchete + 1)
                : autoridad.lastIndexOf(':');
        if (dosPuntos >= 0) {
            host = autoridad.substring(0, dosPuntos);
            try {
                puerto = Integer.parseInt(autoridad.substring(dosPuntos + 1));
            } catch (NumberFormatException noEsPuerto) {
                throw new IOException("el puerto de la dirección no es un número");
            }
        }
        if (host.isEmpty()) {
            throw new IOException("la dirección del puente no trae máquina");
        }
        String sinCorchetes = host.startsWith("[") && host.endsWith("]")
                ? host.substring(1, host.length() - 1) : host;

        Socket crudo = new Socket();
        zocalo = crudo;
        try {
            crudo.connect(new InetSocketAddress(sinCorchetes, puerto), CONEXION_MS);
            crudo.setTcpNoDelay(true);
            Socket seguro = crudo;
            if (esquema.equals("wss://")) {
                seguro = cifra(crudo, sinCorchetes, puerto);
                zocalo = seguro;
            }
            // El saludo sí tiene tiempo de espera: una PC que acepta el TCP y se
            // queda callada no puede dejar este hilo colgado para siempre.
            seguro.setSoTimeout(CONEXION_MS);
            salida = seguro.getOutputStream();
            DataInputStream entrada = new DataInputStream(
                    new BufferedInputStream(seguro.getInputStream(), 8192));

            byte[] semilla = new byte[16];
            azar.nextBytes(semilla);
            String clave = Base64.getEncoder().encodeToString(semilla);
            String peticion = "GET " + camino + " HTTP/1.1\r\n"
                    + "Host: " + autoridad + "\r\n"
                    + "Upgrade: websocket\r\n"
                    + "Connection: Upgrade\r\n"
                    + "Sec-WebSocket-Key: " + clave + "\r\n"
                    + "Sec-WebSocket-Version: 13\r\n"
                    + "\r\n";
            salida.write(peticion.getBytes(StandardCharsets.UTF_8));
            salida.flush();
            compruebaSaludo(entrada, clave);
            // Desde aquí el read es bloqueante sin reloj: el latido vigila el silencio.
            seguro.setSoTimeout(0);
            return entrada;
        } catch (IOException fallo) {
            cierraZocalo();
            throw fallo;
        } catch (Exception fallo) {
            cierraZocalo();
            throw new IOException(sinLlave(motivo(fallo)));
        }
    }

    /**
     * El TLS de la casa. Dos comprobaciones de la misma huella, y las dos hacen
     * falta: el `X509TrustManager` corta durante el handshake, y la comprobación
     * posterior mira el certificado que de verdad quedó en la sesión — si algún
     * proveedor se salta al gestor por reanudación de sesión, la segunda lo caza.
     */
    private SSLSocket cifra(Socket crudo, String host, int puerto) throws IOException {
        final String fijada = huella;
        if (fijada == null) {
            throw new IOException("sin huella del certificado no abro un enlace cifrado");
        }
        try {
            SSLContext contexto = SSLContext.getInstance("TLS");
            contexto.init(null, new javax.net.ssl.TrustManager[] {new Fijado(fijada)}, azar);
            SSLSocketFactory fabrica = contexto.getSocketFactory();
            SSLSocket seguro = (SSLSocket) fabrica.createSocket(crudo, host, puerto, true);
            seguro.setUseClientMode(true);
            seguro.setSoTimeout(CONEXION_MS);
            seguro.startHandshake();
            SSLSession sesion = seguro.getSession();
            if (!new VerificadorFijado(host, fijada).verify(host, sesion)) {
                seguro.close();
                throw new IOException("el certificado que contesta en " + host
                        + " no es el de tu portátil: corté el enlace cifrado");
            }
            return seguro;
        } catch (IOException red) {
            throw red;
        } catch (Exception noCifra) {
            throw new IOException("no pude cifrar el enlace con la PC: "
                    + sinLlave(motivo(noCifra)));
        }
    }

    /**
     * El `TrustManager` del pin. No mira fechas, ni emisores, ni cadena: mira la
     * suma del DER. Es lo único que se puede comprobar de un certificado autofirmado
     * de la LAN, y es suficiente **si** la huella llegó a las manos de la dueña por
     * un camino honesto (el QR o la pantalla de la PC). Sin huella, excepción.
     */
    private static final class Fijado implements X509TrustManager {
        private final String fijada;

        Fijado(String fijada) {
            this.fijada = fijada;
        }

        @Override
        public void checkClientTrusted(X509Certificate[] cadena, String tipo)
                throws CertificateException {
            // El teléfono no presenta certificado de cliente: el puente no lo pide.
            throw new CertificateException("este puente no presenta certificado de cliente");
        }

        @Override
        public void checkServerTrusted(X509Certificate[] cadena, String tipo)
                throws CertificateException {
            if (cadena == null || cadena.length == 0) {
                throw new CertificateException("la PC no enseñó certificado");
            }
            if (!coincide(cadena[0], fijada)) {
                throw new CertificateException("el certificado de la PC no coincide "
                        + "con la huella fijada en el teléfono");
            }
        }

        @Override
        public X509Certificate[] getAcceptedIssuers() {
            return new X509Certificate[0];
        }
    }

    /**
     * El nombre no se puede validar: un certificado de la casa no tiene cadena hasta
     * una CA que este Android conozca, y muchas veces ni siquiera un nombre DNS, sólo
     * IP en los SAN. Lo que autentica este enlace es la **huella**; este verificador
     * acepta el host fijado y sólo si la huella del certificado que llegó coincide.
     * Se aplica a mano porque `SSLSocket` (a diferencia de `HttpsURLConnection`) no
     * consulta ningún `HostnameVerifier`.
     */
    private static final class VerificadorFijado implements HostnameVerifier {
        private final String host;
        private final String fijada;

        VerificadorFijado(String host, String fijada) {
            this.host = host;
            this.fijada = fijada;
        }

        @Override
        public boolean verify(String pedido, SSLSession sesion) {
            if (pedido == null || !pedido.equalsIgnoreCase(host) || sesion == null) {
                return false;
            }
            try {
                java.security.cert.Certificate[] certs = sesion.getPeerCertificates();
                return certs.length > 0 && certs[0] instanceof X509Certificate
                        && coincide((X509Certificate) certs[0], fijada);
            } catch (Exception sinPareja) {
                return false;
            }
        }
    }

    /** SHA-256 del DER contra la huella fijada, sin mirar mayúsculas. */
    private static boolean coincide(X509Certificate cert, String fijada) {
        if (cert == null || fijada == null) {
            return false;
        }
        try {
            MessageDigest digiero = MessageDigest.getInstance("SHA-256");
            return hex(digiero.digest(cert.getEncoded())).equalsIgnoreCase(fijada);
        } catch (Exception noSePuede) {
            return false;
        }
    }

    private static String hex(byte[] bytes) {
        StringBuilder listo = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            listo.append(Character.forDigit((b >> 4) & 0xF, 16));
            listo.append(Character.forDigit(b & 0xF, 16));
        }
        return listo.toString();
    }

    /**
     * Las cabeceras de la respuesta. Se leen byte a byte **del mismo flujo con
     * buffer** que después leerá los cuadros: si se leyera de más en otro flujo, los
     * primeros bytes del primer cuadro se perderían.
     */
    private void compruebaSaludo(DataInputStream entrada, String clave) throws IOException {
        String estadoLinea = linea(entrada);
        String[] partes = estadoLinea.trim().split("\\s+");
        if (partes.length < 2 || !partes[0].startsWith("HTTP/")) {
            throw new IOException("lo que contesta ahí no habla HTTP: no es el puente de CORT");
        }
        int codigo;
        try {
            codigo = Integer.parseInt(partes[1]);
        } catch (NumberFormatException noEsCodigo) {
            throw new IOException("la respuesta del saludo no trae código");
        }
        String sube = "";
        String conexion = "";
        String accept = "";
        int leidos = estadoLinea.length();
        while (true) {
            String cabecera = linea(entrada);
            leidos += cabecera.length();
            if (leidos > TOPE_CABECERAS) {
                throw new IOException("el saludo del otro lado no cabe en "
                        + TOPE_CABECERAS + " bytes: corté");
            }
            if (cabecera.isEmpty()) {
                break;
            }
            int dosPuntos = cabecera.indexOf(':');
            if (dosPuntos <= 0) {
                continue;
            }
            String nombre = cabecera.substring(0, dosPuntos).trim().toLowerCase(Locale.ROOT);
            String valor = cabecera.substring(dosPuntos + 1).trim();
            if ("upgrade".equals(nombre)) {
                sube = valor.toLowerCase(Locale.ROOT);
            } else if ("connection".equals(nombre)) {
                conexion = valor.toLowerCase(Locale.ROOT);
            } else if ("sec-websocket-accept".equals(nombre)) {
                accept = valor;
            }
        }
        if (codigo == 401 || codigo == 403) {
            sinReintento = true;
            throw new IOException("la PC no acepta la llave de red (contestó " + codigo
                    + "): vuelve a escanear el QR del puente; no insisto con una llave que no vale");
        }
        if (codigo == 404) {
            throw new IOException("ahí no hay WebSocket en " + RUTA_WS
                    + ": el CORT del portátil es más viejo que el enlace. Reinícialo en la PC");
        }
        if (codigo != 101) {
            throw new IOException("el otro lado contestó " + codigo
                    + " en vez de cambiar a WebSocket (101)");
        }
        if (!sube.contains("websocket") || !conexion.contains("upgrade")) {
            throw new IOException("contestó 101 pero no sube a WebSocket: no es un puente válido");
        }
        if (!accept.equals(aceptacionDe(clave))) {
            throw new IOException("la clave del saludo no cuadra (Sec-WebSocket-Accept): "
                    + "eso no es un servidor WebSocket de verdad");
        }
    }

    /** Base64(SHA-1(clave + GUID)), la cuenta del RFC 6455 §1.3. */
    private static String aceptacionDe(String clave) throws IOException {
        try {
            MessageDigest digiero = MessageDigest.getInstance("SHA-1");
            byte[] suma = digiero.digest((clave + GUID).getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(suma);
        } catch (Exception sinSha1) {
            throw new IOException("este Android no tiene SHA-1: no puedo comprobar el saludo");
        }
    }

    /** Una línea CRLF, sin los dos bytes finales. El EOF a medias es un fallo dicho. */
    private static String linea(DataInputStream entrada) throws IOException {
        StringBuilder listo = new StringBuilder();
        while (true) {
            int b = entrada.read();
            if (b < 0) {
                throw new EOFException("la PC cerró el enlace en mitad del saludo");
            }
            if (b == '\n') {
                int largo = listo.length();
                if (largo > 0 && listo.charAt(largo - 1) == '\r') {
                    listo.setLength(largo - 1);
                }
                return listo.toString();
            }
            if (listo.length() > TOPE_CABECERAS) {
                throw new IOException("una cabecera del saludo no termina nunca: corté");
            }
            listo.append((char) (b & 0xFF));
        }
    }

    /** El primer cuadro del teléfono: el emparejamiento que acordamos con la PC. */
    private byte[] cuadroDeAuth() throws IOException {
        String modelo = Build.MODEL == null || Build.MODEL.trim().isEmpty()
                ? "teléfono Android" : Build.MODEL.trim();
        try {
            return new JSONObject().put("type", "mobile_auth").put("token", llave)
                    .put("dispositivo", modelo).put("version", version)
                    .toString().getBytes(StandardCharsets.UTF_8);
        } catch (Exception noSerializa) {
            throw new IOException("no pude escribir el cuadro de emparejamiento");
        }
    }

    /* --------------------------------------------------------------- los cuadros */

    /**
     * El lazo de lectura. Devuelve `true` si el cierre fue limpio (llegó un cuadro
     * de cierre) y lanza `IOException` con el motivo en español si no.
     */
    private boolean escuchar(DataInputStream entrada) throws IOException {
        ByteArrayOutputStream partes = new ByteArrayOutputStream();
        int tipoAbierto = -1;
        while (!cerrado && vivo) {
            int primero = entrada.read();
            if (primero < 0) {
                throw new EOFException("la PC colgó el socket sin cuadro de cierre");
            }
            int segundo = entrada.readUnsignedByte();
            ultimoTrafico = System.currentTimeMillis();
            pingEnviado = 0L;
            boolean fin = (primero & 0x80) != 0;
            if ((primero & 0x70) != 0) {
                // No negociamos ninguna extensión: un bit RSV encendido es alguien
                // hablando otro dialecto (o deflate sin pedirlo).
                throw protocolo("llegaron bits reservados (RSV) y este puente no negoció "
                        + "ninguna extensión");
            }
            int op = primero & 0x0F;
            if ((segundo & 0x80) != 0) {
                throw protocolo("la PC mandó un cuadro enmascarado: sólo el cliente enmascara");
            }
            long largo = segundo & 0x7F;
            if (largo == 126) {
                largo = entrada.readUnsignedShort();
            } else if (largo == 127) {
                largo = entrada.readLong();
                if (largo < 0) {
                    throw protocolo("la longitud de un cuadro llegó con el bit alto puesto");
                }
            }
            boolean control = (op & 0x08) != 0;
            if (control && (!fin || largo > 125)) {
                throw protocolo("un cuadro de control llegó fragmentado o con más de 125 bytes");
            }
            if (largo > TOPE_MENSAJE || partes.size() + largo > TOPE_MENSAJE) {
                escribeCierre(CIERRE_DEMASIADO, "cuadro mayor que el tope del puente");
                throw new IOException("la PC mandó un mensaje de más de " + TOPE_MENSAJE
                        + " bytes: cerré el enlace, ese es el tope del teléfono");
            }
            byte[] datos = new byte[(int) largo];
            entrada.readFully(datos);

            if (op == OP_PING) {
                escribe(OP_PONG, datos);          // el mismo payload, dice el RFC
                continue;
            }
            if (op == OP_PONG) {
                continue;                          // el latido ya vio el tráfico
            }
            if (op == OP_CIERRE) {
                byte[] eco = datos.length >= 2 ? new byte[] {datos[0], datos[1]}
                        : codigoDe(CIERRE_NORMAL);
                escribeCierreSinMotivo(eco);
                return true;
            }
            if (op == OP_TEXTO || op == OP_BINARIO) {
                if (tipoAbierto >= 0) {
                    throw protocolo("empezó un mensaje nuevo sin terminar el anterior");
                }
                if (!fin) {
                    tipoAbierto = op;
                    partes.write(datos, 0, datos.length);
                    continue;
                }
                entrega(op, datos);
                continue;
            }
            if (op == OP_CONTINUACION) {
                if (tipoAbierto < 0) {
                    throw protocolo("llegó una continuación sin mensaje empezado");
                }
                partes.write(datos, 0, datos.length);
                if (fin) {
                    byte[] entero = partes.toByteArray();
                    partes.reset();
                    int tipo = tipoAbierto;
                    tipoAbierto = -1;
                    entrega(tipo, entero);
                }
                continue;
            }
            throw protocolo("llegó un cuadro con opcode " + op + " que no conozco");
        }
        return false;
    }

    /** Un mensaje entero, ya reensamblado, hacia la cara. */
    private void entrega(int op, byte[] datos) {
        if (op == OP_BINARIO) {
            dice("la PC mandó un cuadro binario y este puente sólo lee texto JSON: lo ignoré");
            return;
        }
        String json = new String(datos, StandardCharsets.UTF_8);
        miraAuth(json);
        AlCuadro cara = oyente;
        if (cara == null) {
            return;
        }
        try {
            cara.cuadro(json);
        } catch (RuntimeException laCaraRompio) {
            // Un fallo en quien escucha no puede tumbar el enlace: se dice y se sigue.
            dice("quien recibe los cuadros falló: " + sinLlave(motivo(laCaraRompio)));
        }
    }

    /**
     * El resultado del emparejamiento. Con `ok:false` se cierra y **no** se vuelve a
     * intentar: una llave equivocada no se arregla sola, y reintentar cada 30 s sería
     * martillear la PC hasta que la dueña se dé cuenta. Lo que la arregla es otro QR.
     */
    private void miraAuth(String json) {
        try {
            JSONObject cuadro = new JSONObject(json);
            if (!"mobile_auth_result".equals(cuadro.optString("type"))) {
                return;
            }
            if (cuadro.optBoolean("ok", false)) {
                autenticado = true;
                String maquina = cuadro.optString("maquina", "tu portátil");
                dice("emparejada con " + maquina + " · el puente es de verdad");
            } else {
                sinReintento = true;
                vivo = false;
                dice("la PC no aceptó el emparejamiento: "
                        + cuadro.optString("motivo", "no dijo por qué")
                        + ". No reintento: escanea otra vez el QR del puente");
            }
        } catch (Exception noEsJson) {
            // El puente también manda texto que no es un objeto (ecos, pruebas):
            // se entrega igual y no es un fallo.
        }
    }

    private IOException protocolo(String dicho) {
        try {
            escribeCierre(CIERRE_PROTOCOLO, dicho);
        } catch (Exception yaNoEsta) {
            // Si no se puede ni despedir, el motivo de abajo sigue siendo el bueno.
        }
        return new IOException("la PC habló mal el protocolo: " + dicho);
    }

    /* -------------------------------------------------------------- la escritura */

    private void arrancaEscritura() {
        hiloEscritura = new Thread(this::bombear, "cort-ws-sale");
        hiloEscritura.setDaemon(true);
        hiloEscritura.start();
    }

    /** El único que vacía la cola, para que los cuadros salgan en el orden en que entraron. */
    private void bombear() {
        while (!cerrado && vivo) {
            String json;
            try {
                json = cola.poll(400L, TimeUnit.MILLISECONDS);
            } catch (InterruptedException basta) {
                Thread.currentThread().interrupt();
                return;
            }
            if (json == null) {
                continue;
            }
            try {
                escribe(OP_TEXTO, json.getBytes(StandardCharsets.UTF_8));
            } catch (IOException noSale) {
                if (!cerrado) {
                    dice("no pude mandar un cuadro a la PC: " + sinLlave(motivo(noSale)));
                }
                vivo = false;
                cierraZocalo();
                return;
            }
        }
    }

    /**
     * Un cuadro completo, con FIN=1 y **enmascarado**: RFC 6455 §5.3 obliga al
     * cliente a enmascarar siempre, y un servidor conforme corta el enlace si no lo
     * hace. Todo pasa por el mismo candado: el pong del lector, el ping del latido y
     * los cuadros de la cola no pueden mezclarse en el cable.
     */
    private void escribe(int op, byte[] datos) throws IOException {
        byte[] mascara = new byte[4];
        azar.nextBytes(mascara);
        byte[] cuadro = trama(op, datos, mascara);
        synchronized (candadoEscritura) {
            OutputStream flujo = salida;
            if (flujo == null) {
                throw new IOException("el enlace ya está cerrado");
            }
            flujo.write(cuadro);
            flujo.flush();
        }
    }

    /**
     * El montaje de los bytes, separado del socket para que se pueda comprobar
     * contra el RFC sin abrir la red (el banco de pruebas de Python hace exactamente
     * esta cuenta y compara los bytes):
     *
     * byte 0: FIN | RSV(0) | opcode · byte 1: MASK | longitud(7) ·
     * 126 → 2 bytes de longitud · 127 → 8 bytes · luego 4 de máscara y el payload
     * con XOR `datos[i] ^ mascara[i % 4]`.
     */
    static byte[] trama(int op, byte[] datos, byte[] mascara) {
        int largo = datos.length;
        int extra = largo < 126 ? 0 : (largo <= 0xFFFF ? 2 : 8);
        byte[] cuadro = new byte[2 + extra + 4 + largo];
        cuadro[0] = (byte) (0x80 | (op & 0x0F));
        int cursor = 2;
        if (extra == 0) {
            cuadro[1] = (byte) (0x80 | largo);
        } else if (extra == 2) {
            cuadro[1] = (byte) (0x80 | 126);
            cuadro[cursor++] = (byte) ((largo >>> 8) & 0xFF);
            cuadro[cursor++] = (byte) (largo & 0xFF);
        } else {
            cuadro[1] = (byte) (0x80 | 127);
            for (int i = 7; i >= 0; i--) {
                cuadro[cursor++] = (byte) ((largo >>> (8 * i)) & 0xFF);
            }
        }
        for (int i = 0; i < 4; i++) {
            cuadro[cursor++] = mascara[i];
        }
        for (int i = 0; i < largo; i++) {
            cuadro[cursor++] = (byte) (datos[i] ^ mascara[i & 3]);
        }
        return cuadro;
    }

    private static byte[] codigoDe(int codigo) {
        return new byte[] {(byte) ((codigo >>> 8) & 0xFF), (byte) (codigo & 0xFF)};
    }

    /** El cierre con código y un motivo corto (el payload de control tope 125 bytes). */
    private void escribeCierre(int codigo, String motivo) throws IOException {
        byte[] razon = motivo.getBytes(StandardCharsets.UTF_8);
        int cuanto = Math.min(razon.length, 123);
        byte[] datos = new byte[2 + cuanto];
        byte[] dos = codigoDe(codigo);
        datos[0] = dos[0];
        datos[1] = dos[1];
        System.arraycopy(razon, 0, datos, 2, cuanto);
        escribe(OP_CIERRE, datos);
    }

    private void escribeCierreSinMotivo(byte[] datos) throws IOException {
        synchronized (candadoEscritura) {
            OutputStream flujo = salida;
            if (flujo == null) {
                throw new IOException("el enlace ya está cerrado");
            }
            byte[] mascara = new byte[4];
            azar.nextBytes(mascara);
            flujo.write(trama(OP_CIERRE, datos, mascara));
            flujo.flush();
        }
    }

    /* ------------------------------------------------------------------ el latido */

    private void arrancaLatido() {
        hiloLatido = new Thread(this::late, "cort-ws-latido");
        hiloLatido.setDaemon(true);
        hiloLatido.start();
    }

    /**
     * El vigilante del silencio. El read se queda bloqueado sin reloj (así no hay
     * que trocear la lectura de un cuadro grande), y este hilo mira el reloj por
     * fuera: al minuto sin nada manda un ping; si en los 30 s siguientes no llega
     * ni pong ni tráfico, cierra el socket —eso desbloquea al lector con un
     * `IOException`— y el lazo de vida vuelve a conectar.
     */
    private void late() {
        while (!cerrado && vivo) {
            try {
                Thread.sleep(PASO_LATIDO_MS);
            } catch (InterruptedException basta) {
                Thread.currentThread().interrupt();
                return;
            }
            if (!vivo || cerrado) {
                return;
            }
            long ahora = System.currentTimeMillis();
            long ping = pingEnviado;
            try {
                if (ping == 0L && ahora - ultimoTrafico >= SIN_NADA_MS) {
                    escribe(OP_PING, new byte[0]);
                    pingEnviado = ahora;
                } else if (ping != 0L && ahora - Math.max(ping, ultimoTrafico) >= SIN_PONG_MS) {
                    dice("la PC lleva " + ((ahora - ultimoTrafico) / 1000L)
                            + " s sin decir nada ni contestar al ping: doy el enlace por muerto");
                    vivo = false;
                    cierraZocalo();
                    return;
                }
            } catch (IOException noLate) {
                vivo = false;
                cierraZocalo();
                return;
            }
        }
    }

    /* ------------------------------------------------------------------- limpieza */

    /** Dejar la sesión como estaba antes de abrir: nada de hilos ni colas colgando. */
    private void suelta() {
        vivo = false;
        autenticado = false;
        Thread escritor = hiloEscritura;
        if (escritor != null) {
            escritor.interrupt();
            hiloEscritura = null;
        }
        Thread latido = hiloLatido;
        if (latido != null) {
            latido.interrupt();
            hiloLatido = null;
        }
        cierraZocalo();
        int pendientes = cola.size();
        cola.clear();
        if (pendientes > 0 && !cerrado) {
            dice("se cayeron " + pendientes + " cuadros que estaban esperando salir: "
                    + "no los guardo para el próximo enlace");
        }
    }

    private void cierraZocalo() {
        OutputStream flujo = salida;
        salida = null;
        if (flujo != null) {
            try {
                flujo.close();
            } catch (Exception yaCerrado) {
                // nada que hacer
            }
        }
        Socket z = zocalo;
        zocalo = null;
        if (z != null) {
            try {
                z.close();
            } catch (Exception yaCerrado) {
                // nada que hacer
            }
        }
    }

    /* --------------------------------------------------------------------- dichos */

    /**
     * La única boca del puente. Guarda la frase y la entrega; nunca deja que un
     * fallo de quien escucha mate el hilo de la red.
     */
    private void dice(String dicho) {
        String seguro = sinLlave(dicho);
        ultimoEstado = seguro;
        AlCuadro cara = oyente;
        if (cara == null) {
            return;
        }
        try {
            cara.estado(seguro);
        } catch (RuntimeException laCaraRompio) {
            // Se queda en `ultimoEstado`, que es consultable: mejor eso que romper el lazo.
        }
    }

    /**
     * La regla dura del proyecto: la llave no aparece en ningún dicho, ni aunque
     * llegue dentro del mensaje de una excepción (una URL de un `IOException`, por
     * ejemplo). Estas frases acaban en notificaciones y en la pantalla de bloqueo.
     */
    private String sinLlave(String texto) {
        String limpio = texto == null ? "sin motivo dicho" : texto;
        if (!llave.isEmpty()) {
            limpio = limpio.replace(llave, "«llave oculta»");
        }
        return limpio;
    }

    /** La URL sin query ni fragmento: el host se puede decir, la llave no. */
    private static String sinQuery(String direccion) {
        int corte = direccion.length();
        for (int i = 0; i < direccion.length(); i++) {
            char c = direccion.charAt(i);
            if (c == '?' || c == '#') {
                corte = i;
                break;
            }
        }
        return direccion.substring(0, corte);
    }

    /** El mensaje de una excepción, o su clase si no dijo nada. Nunca la URL con query. */
    private static String motivo(Exception algo) {
        String dicho = algo.getMessage();
        if (dicho == null || dicho.trim().isEmpty()) {
            return algo instanceof SocketTimeoutException
                    ? "no contestó a tiempo" : algo.getClass().getSimpleName();
        }
        return dicho;
    }
}