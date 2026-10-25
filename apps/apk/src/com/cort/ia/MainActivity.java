package com.cort.ia;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.PendingIntent;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.media.session.MediaSession;
import android.os.Bundle;
import android.os.SystemClock;
import android.provider.Settings;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.InputMethodManager;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.Toast;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

/**
 * La cara de CORT en el teléfono.
 *
 * Es **una** actividad con un WebView y tres decisiones:
 *
 * 1. **Qué página se abre.** Si guardaste la dirección de tu portátil, se abre
 *    `http://IP:8000`: el holograma actual, con las once ventanas y el backend
 *    real (archivos, música, modelos de Ollama, optimización). Si no la hay o
 *    el PC no contesta, se abre la cara embebida en el propio APK
 *    (`assets/ui/`, copiada de `ui/` por el pipeline) bajo el origen inventado
 *    `https://cort.local`, que se corta en `shouldInterceptRequest` y se lee de
 *    los assets. No sale ni un byte del teléfono y no hay nada escuchando en la
 *    red.
 * 2. **Quién pone la voz.** `window.CortNative` (`CortNative.java`): el
 *    micrófono y el habla del aparato, porque una página en `http` de red local
 *    no es origen seguro y Chrome no presta Web Speech fuera de uno.
 * 3. **Quién la despierta.** El botón del micro de la interfaz, el gesto de
 *    asistente (CORT elegido como aplicación de asistencia predeterminada:
 *    `Asistente.java` + `Sesion.java`) y el **doble toque del auricular**
 *    (`MediaSession` abajo). El primer toque sigue mandando la música: sólo el
 *    segundo, dentro de 500 ms, abre el micrófono.
 * 4. **Qué puede leer en voz alta.** Además de lo que dice el PC, CORT lee los
 *    **avisos que llegan al teléfono** («lee mis mensajes»): los recoge
 *    `Avisos.java` en doce líneas de RAM, sin disco, y las habla el mismo
 *    `TextToSpeech` del puente. El menú del botón «CORT · PC» dice si el permiso
 *    del sistema ya está dado, que es la única parte que no se puede comprobar
 *    desde el código.
 * 5. **Qué manda en el aparato.** La ronda 2.1 (2.1.0) trae la pantalla **Equipo**
 *    con sus seis bloques —Voz, Mando, Cerebro, Memoria, Atuendos y Agenda—, que
 *    son lo que el APK original prometía y el nuestro había dejado fuera: subir el
 *    volumen, la linterna, poner alarma y temporizador, abrir apps, buscar en la
 *    red, elegir la voz (con preajustes tipo Siri/Alexa/Cortana), recordar sin el
 *    PC y cuadrar ese recuerdo con el portátil, pensar con la nube del perfil,
 *    cambiar los colores de CORT y dejar un punto flotante que abre el micrófono
 *    sin sacar de la partida. El menú de este botón tiene las cinco filas que la
 *    dueña dice más a menudo, habladas por el mismo puente.
 *
 * Sin Gradle ni AndroidX: se compila con `aapt2` + `javac` + `d8` en GitHub
 * Actions, porque el portátil de la dueña (1,8 GiB) no levanta un `gradle build`.
 */
public class MainActivity extends Activity {

    /** La bandera que mandan `Sesion.java` y `Reconocimiento.java` al invocar a CORT. */
    public static final String PIDE_ESCUCHAR = "cort.escuchar";

    /* Las tres acciones que declara `res/xml/atajos.xml`, y las dos del sistema,
       escritas como cadena en vez de `Intent.ACTION_ASSIST` / `ACTION_VOICE_COMMAND`:
       el APK se compila contra el `android.jar` que baje el pipeline, y no depende
       de qué constantes estén o no exportadas ese día. La cadena es la misma en
       cualquier Android, así que el riesgo se queda en cero por dos líneas. */
    public static final String A_ESCUCHAR = "com.cort.ia.ESCUCHAR";
    public static final String A_EQUIPO = "com.cort.ia.EQUIPO";
    public static final String A_CHARLA = "com.cort.ia.CHARLA";
    /** F16 · el despertador de CORT: abre la cara con su pantalla de alarma. */
    public static final String A_ALARMA = Alarma.ACCION;
    private static final String A_ASISTENTE = "android.intent.action.ASSIST";
    private static final String A_VOZ = "android.intent.action.VOICE_COMMAND";

    /** El código con el que se pide el rol de asistente a `RoleManager` (API 29+). */
    private static final int PETICION_ROL = 42;

    static final String ORIGEN = "https://cort.local";
    static final String INDICE = ORIGEN + "/index.html";
    /** La carpeta de la interfaz dentro de los assets del APK. */
    static final String CARPETA = "ui/";

    private WebView web;
    private CortNative puente;
    private MediaSession mandos;
    private long ultimoToque = 0L;
    private String direccionPC = "";
    private boolean cayoUnaSolaVez = false;
    /** F16 · la página ya cargó al menos una vez (para soltarle el despertador). */
    private volatile boolean paginaLista = false;
    /** F16 · el evento de alarma que llegó antes que la página; se suelta al cargar. */
    private volatile String alarmaPendiente = null;

    /** El botón de la esquina, guardado porque el traje de CORT lo pinta. */
    private Button botonMenu;

    /**
     * La cara abierta, para que el `Reproductor` pueda avisarla cuando cambia algo
     * (pista nueva, pausa, auricular). Es un `static` porque el servicio lo monta
     * Android por su cuenta y no recibe la actividad por parámetro.
     */
    private static MainActivity cara;
    static MainActivity front() { return cara; }
    CortNative puente() { return puente; }

    /* ───────────────────────────── arranque ───────────────────────────── */

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        cara = this;
        puente = new CortNative(this);

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        // `content://` SÍ se deja: es lo que permite que un <video> de la página
        // muestre un vídeo que ya está en el teléfono (el URI del índice de
        // Android), y sólo se ven los archivos que la propia app puede leer.
        s.setAllowContentAccess(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setTextZoom(100);
        web.setBackgroundColor(Color.parseColor("#05070d"));
        // El puente tiene que existir antes de cargar la página: la interfaz mira
        // `window.CortNative` en su primer script (`ui/js/android-bridge.js`).
        web.addJavascriptInterface(puente, "CortNative");
        web.setWebViewClient(cliente());
        web.setWebChromeClient(new android.webkit.WebChromeClient() {
            @Override
            public void onPermissionRequest(android.webkit.PermissionRequest peticion) {
                // Sin esto, los gestos con cámara y cualquier audio del WebView
                // quedan denegados en silencio.
                //
                // Conceder `peticion.getResources()` a ciegas era el otro medio del
                // fallo de «la cámara no funciona»: la página pide `VIDEO_CAPTURE`,
                // este `grant` le dice que sí, y como el **sistema** nunca nos dio
                // `CAMERA` el `getUserMedia` revienta con un `NotAllowedError` que la
                // cara traducía por «sin cámara» sin decir por qué. Aquí se concede
                // sólo lo que el aparato ya tiene concedido, y lo que falta se pide
                // en el mismo instante: a la segunda pulsación la mano funciona.
                boolean faltaCamara = false, faltaMicro = false;
                java.util.List<String> deja = new java.util.ArrayList<>();
                for (String recurso : peticion.getResources()) {
                    boolean esVideo = recurso != null &&
                        recurso.equals(android.webkit.PermissionRequest.RESOURCE_VIDEO_CAPTURE);
                    boolean esAudio = recurso != null &&
                        recurso.equals(android.webkit.PermissionRequest.RESOURCE_AUDIO_CAPTURE);
                    if (esVideo && checkSelfPermission(android.Manifest.permission.CAMERA)
                            != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                        faltaCamara = true;
                        continue;                       // sin `CAMERA` concedería humo
                    }
                    if (esAudio && checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)
                            != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                        faltaMicro = true;
                        continue;                       // misma regla para el oído
                    }
                    deja.add(recurso);
                }
                if (deja.isEmpty()) peticion.deny();
                else peticion.grant(deja.toArray(new String[0]));
                if (faltaCamara) pidePermiso("camara");
                if (faltaMicro) pidePermiso("mic");
            }
        });

        /* El botón nativo «CORT · PC» ya no se pinta encima de la cara: la dueña
           lo señaló como estorbo y, peor, parecía que CORT «quería arrancar en
           modo PC» cada vez que abría. El menú de siempre (asistente, avisos,
           música, agenda, burbuja, memoria) sigue vivo y se abre desde Equipo ▸
           9 · PC con `abreMenu()`; aquí no ocupa ni un píxel. */
        botonMenu = new Button(this);
        botonMenu.setText("CORT · PC");
        botonMenu.setVisibility(View.GONE);
        usaAtuendo();

        FrameLayout cara = new FrameLayout(this);
        cara.addView(web, new FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        setContentView(cara);

        mandos = new MediaSession(this, "cort-auriculares");
        mandos.setCallback(nuevosToques());
        try {
            Intent boton = new Intent(Intent.ACTION_MEDIA_BUTTON).setPackage(getPackageName());
            PendingIntent quienEscucha = PendingIntent.getBroadcast(
                this, 0, boton, PendingIntent.FLAG_IMMUTABLE);
            mandos.setMediaButtonReceiver(quienEscucha);
        } catch (Exception sinRecettore) {
            // Sin receptor, el doble toque igual funciona con la sesión activa.
        }

        // El oído propio se prepara aquí, y no dentro de `new CortNative`: desempacar
        // los 60,3 MB del modelo de español y cargar el `Model` de Vosk cuesta
        // segundos, y hacerlos en el `onCreate` es lo que saca el diálogo «CORT no
        // responde» antes de que la dueña haya visto nada. `preparaOido()` lanza su
        // propio hilo (`cort-oido`) y avisa por el puente en cada fase, así que la
        // cara pinta primero y el oído llega detrás.
        web.postDelayed(() -> puente.preparaOido(), 1200);

        pidePermiso("mic");
        abreLoQueToque(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        abreLoQueToque(intent);
    }

    /**
     * Todo lo que abre CORT **sin** pulsar su icono: el gesto de asistente
     * (`ACTION_ASSIST`), el botón del auricular mantenido (`ACTION_VOICE_COMMAND`),
     * el baldosín de la cortina y la sesión de voz (esos tres con `PIDE_ESCUCHAR`),
     * y los tres atajos del icono largo, que además de escuchar abren una hoja.
     *
     * Se concentra aquí y no repartido entre `onCreate` y `onNewIntent` porque el
     * viaje puede llegar con la cara ya abierta (`singleTop`): la actividad se
     * reutiliza, y lo único que cambia es el `Intent`.
     */
    private void abreLoQueToque(Intent intent) {
        if (intent == null) return;
        String accion = intent.getAction() == null ? "" : intent.getAction();
        // F16 · el despertador llega con su evento ya armado. Se le pasa a la
        // página tal cual; el retardo es para el arranque en frío, y el puente
        // guarda el aviso en cola si la cara aún no tiene oyente.
        if (A_ALARMA.equals(accion)) {
            final String evento = intent.getStringExtra(Alarma.EXTRA_EVENTO);
            intent.removeExtra(Alarma.EXTRA_EVENTO);
            if (paginaLista) web.postDelayed(() -> puente.alarmaEnLaCara(evento), 300);
            else alarmaPendiente = evento;
            return;
        }
        String hoja = hojaDe(accion);
        boolean oir = intent.getBooleanExtra(PIDE_ESCUCHAR, false)
                   || A_ASISTENTE.equals(accion)
                   || A_VOZ.equals(accion)
                   || A_ESCUCHAR.equals(accion);
        if (!oir && hoja == null) return;
        intent.removeExtra(PIDE_ESCUCHAR);
        // Un retardo corto: si se pide el micrófono antes de que la página exista,
        // la interfaz aún no tiene `window.__cortNative` y el resultado se pierde.
        // Con el teléfono bloqueado el retardo no basta —la cara se monta después
        // del desbloqueo—, pero `escuchaAhora()` ya tiene su guarda de micro
        // abierto y la página se recupera sola al aparecer.
        final boolean escucha = oir;
        final String cualHoja = hoja;
        web.postDelayed(() -> {
            if (cualHoja != null) puente.atajoEnLaCara(cualHoja);
            // `escuchaDelAuricular` y no `escuchaAhora`: en ninguna de estas vías la
            // dueña está mirando la pantalla cuando llega el resultado, así que la
            // insignia del micro es lo único que le dice que CORT ya la está oyendo.
            if (escucha) puente.escuchaDelAuricular();
            hideTeclado();
        }, 900);
    }

    /** Qué hoja pide cada atajo del icono; `null` para cualquier otra acción. */
    private static String hojaDe(String accion) {
        switch (accion) {
            case A_EQUIPO: return "equipo";
            case A_CHARLA: return "charla";
            default: return null;
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        primerPlano = true;
        direccionPC = prefs().getString("pc", "");
        if (web.getUrl() == null) arranca();
        if (mandos != null) mandos.setActive(true);
        // El oído vuelve: `pausa()` cerró el micrófono al irse a segundo plano y
        // sin este aviso la interfaz quedaría para siempre con «escucha en pausa».
        if (puente != null) puente.reanuda();
        // Los sentidos también vuelven. Es el ÚNICO momento en que este APK escucha
        // sensores: con la app en segundo plano se desenganchan (`onPause`) para no
        // comer batería, que es lo que la dueña nota como «el teléfono se traba».
        Sentidos.de(this).enMarcha(true);
        quitaAvisoDeFondo();            // ya está delante: su aviso sobra
    }

    @Override
    protected void onPause() {
        super.onPause();
        primerPlano = false;
        if (mandos != null) mandos.setActive(false);   // la música vuelve a su dono
        if (puente != null) puente.pausa();
        Sentidos.de(this).enMarcha(false);
        dejaAvisoDeFondo();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (cara == this) cara = null;
        if (mandos != null) { mandos.setActive(false); mandos.release(); mandos = null; }
        Sentidos.de(this).enMarcha(false);
        if (puente != null) puente.destruye();
        if (web != null) web.destroy();
    }

    /**
     * Abrir CORT **siempre** en la cara del teléfono.
     *
     * Antes, si había una dirección de PC guardada, el arranque iba derecho a
     * ella: con el portátil apagado la pantalla se quedaba esperando (o en un
     * error) y parecía que CORT «intentaba modo PC y no podía». La dirección se
     * guarda igual, pero sólo se usa cuando ella pulsa **Conectar** en
     * Equipo ▸ 9 · PC. Así abrir CORT nunca depende de que el PC esté despierto.
     */
    private void arranca() {
        cayoUnaSolaVez = false;
        web.loadUrl(INDICE);
    }

    /* ─────────────────────────── los assets ───────────────────────────── */

    private WebViewClient cliente() {
        return new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView vista,
                                                              WebResourceRequest peticion) {
                String url = peticion.getUrl().toString();
                if (!url.startsWith(ORIGEN)) return null;   // modo PC: que lo vea la red
                // Los `fetch` de la interfaz al núcleo se cortan ANTES de tocar la
                // carpeta `ui/`: sin PC no hay `/api/*`, y la cara tiene que poder
                // decirlo en español en vez de un 404 mudo.
                if (url.substring(ORIGEN.length()).startsWith("/api/")) return sinNucleo();
                String ruta = rutaDe(url);
                if (ruta == null) return noExiste();
                return sirve(ruta);
            }

            @Override
            public void onReceivedError(WebView vista, WebResourceRequest peticion,
                                        WebResourceError error) {
                String url = peticion.getUrl().toString();
                if (url.startsWith(ORIGEN)) return;
                if (cayoUnaSolaVez) return;
                cayoUnaSolaVez = true;
                avisa("Tu PC no respondió: abro la cara del teléfono");
                web.postDelayed(() -> web.loadUrl(INDICE), 400);
            }

            /**
             * F16 · el despertador puede llegar con la app cerrada. Cuando la
             * página termina de montarse se le suelta el evento que quedó
             * esperando, una sola vez. Si la alarma llegó con la cara ya abierta,
             * `abreLoQueToque` la manda directa y aquí no hay nada pendiente.
             */
            @Override
            public void onPageFinished(WebView vista, String url) {
                paginaLista = true;
                final String evento = alarmaPendiente;
                if (evento == null) return;
                alarmaPendiente = null;
                web.postDelayed(() -> puente.alarmaEnLaCara(evento), 350);
            }
        };
    }

    /** `https://cort.local/js/hud.js` → `ui/js/hud.js`; nada fuera de `ui/`. */
    private static String rutaDe(String url) {
        String resto = url.substring(ORIGEN.length());
        int corte = resto.indexOf('?');
        if (corte >= 0) resto = resto.substring(0, corte);
        if (resto.isEmpty() || "/".equals(resto)) resto = "/index.html";
        if (resto.startsWith("/")) resto = resto.substring(1);
        if (resto.contains("..")) return null;
        return CARPETA + resto;
    }

    private WebResourceResponse sirve(String ruta) {
        try {
            InputStream datos = getAssets().open(ruta);
            Map<String, String> cabeceras = new HashMap<>();
            cabeceras.put("Cache-Control", "no-store");
            // El orden real del constructor (AOSP, API 21) es
            // `mimeType, encoding, statusCode, reasonPhrase, headers, data`: el
            // `InputStream` va AL FINAL, no después del coding. Intercambiarlos es
            // el rojo que `javac` señaló como «InputStream cannot be converted to int».
            return new WebResourceResponse(mimeDe(ruta), "utf-8", 200, "OK",
                                           cabeceras, datos);
        } catch (Exception noEstaEnElAPK) {
            return noExiste();
        }
    }

    /**
     * El MIME importa más de lo que parece: un módulo ES servido como
     * `text/plain` lo rechaza Chromium y el holograma queda en negro. La lista
     * es cerrada y coincide con las carpetas que viajan en `assets/ui/`.
     */
    private static String mimeDe(String ruta) {
        String r = ruta.toLowerCase();
        if (r.endsWith(".html")) return "text/html";
        if (r.endsWith(".js") || r.endsWith(".mjs")) return "application/javascript";
        if (r.endsWith(".css")) return "text/css";
        if (r.endsWith(".json") || r.endsWith(".map")) return "application/json";
        if (r.endsWith(".svg")) return "image/svg+xml";
        if (r.endsWith(".png")) return "image/png";
        if (r.endsWith(".jpg") || r.endsWith(".jpeg")) return "image/jpeg";
        if (r.endsWith(".webp")) return "image/webp";
        if (r.endsWith(".woff2")) return "font/woff2";
        if (r.endsWith(".woff")) return "font/woff";
        if (r.endsWith(".glb") || r.endsWith(".gltf")) return "model/gltf-binary";
        if (r.endsWith(".wasm")) return "application/wasm";
        return "application/octet-stream";
    }

    private static WebResourceResponse noExiste() {
        Map<String, String> cabeceras = new HashMap<>();
        cabeceras.put("Cache-Control", "no-store");
        return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found",
            cabeceras, new java.io.ByteArrayInputStream(new byte[0]));
    }

    /**
     * La cara embebida sigue siendo el holograma del PC: si no hay núcleo, los
     * `fetch` a `/api/*` tienen que responder algo y el HUD tiene que poder
     * decir «modo supervivencia». Un 501 con `error` en español es la respuesta
     * honesta; los comandos locales, la voz y el orbe siguen funcionando.
     */
    private static WebResourceResponse sinNucleo() {
        Map<String, String> cabeceras = new HashMap<>();
        cabeceras.put("Cache-Control", "no-store");
        byte[] cuerpo = "{\"error\":\"sin PC: escribe la dirección de tu portátil en el botón CORT · PC\"}"
            .getBytes(java.nio.charset.Charset.forName("UTF-8"));
        return new WebResourceResponse("application/json", "utf-8", 501, "Not Implemented",
            cabeceras, new java.io.ByteArrayInputStream(cuerpo));
    }

    /* ─────────────────────── doble toque del auricular ─────────────────── */

    private MediaSession.Callback nuevosToques() {
        return new MediaSession.Callback() {
            @Override
            public boolean onMediaButtonEvent(Intent evento) {
                KeyEvent tecla = teclaDe(evento);
                if (tecla == null || tecla.getAction() != KeyEvent.ACTION_DOWN) return false;
                int codigo = tecla.getKeyCode();
                boolean toque = codigo == KeyEvent.KEYCODE_HEADSETHOOK
                             || codigo == KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE;
                if (!toque) return false;
                long ahora = SystemClock.elapsedRealtime();
                if (ultimoToque != 0L && ahora - ultimoToque < 500L) {
                    ultimoToque = 0L;
                    runOnUiThread(() -> {
                        Intent abrir = new Intent(MainActivity.this, MainActivity.class)
                            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                                    | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
                            .putExtra(PIDE_ESCUCHAR, true);
                        startActivity(abrir);
                        // `escuchaDelAuricular`, no `escuchaAhora`: la dueña no está
                        // mirando la pantalla, así que la insignia del micro es lo
                        // único que le dice que CORT ya la está oyendo.
                        puente.escuchaDelAuricular();
                    });
                    return true;      // el segundo toque es de CORT
                }
                ultimoToque = ahora;
                return false;          // el primero sigue siendo de la música
            }
        };
    }

    /**
     * `EXTRA_KEY_EVENT` es un `Parcelable`; se recoge con cuidado por si viene otro
     * tipo. Sin `private` a propósito: `Reproductor.dobleToque` lee la misma tecla
     * del mismo `Intent` y no hay que escribir dos veces el mismo `try/catch`.
     */
    static KeyEvent teclaDe(Intent evento) {
        try {
            Object dentro = evento.getParcelableExtra(Intent.EXTRA_KEY_EVENT);
            return dentro instanceof KeyEvent ? (KeyEvent) dentro : null;
        } catch (Exception noEsTecla) {
            return null;
        }
    }

    /* ─────────────────────────── el menú del botón ─────────────────────── */

    private void menu() {
        // El estado del oído se escribe en la propia fila: así la dueña ve si ya dio
        // el interruptor del sistema antes de pulsar, sin tener que bajar la cortina
        // a media conversación para comprobarlo.
        String oido = Avisos.activado(this) ? "hecho" : "pendiente";
        String medios = Musica.puedeLeer(this) ? "hecho" : "pendiente";
        String suena = Reproductor.estaVivo() ? "sí" : "no";
        String calendario = Agenda.conPermiso(this) ? "hecho" : "pendiente";
        String flotante = Flotante.puedeAparecer(this) ? "hecho" : "pendiente";
        String enPunto = Flotante.montada() ? "puesta" : "apagada";
        // El estado se **lee**, no se recuerda: la bandera vive en `CortNative`
        // (static volatile, con su copia en las preferencias), así que la fila dice
        // lo que hay aunque el modo lo haya puesto la pantalla de la cara.
        boolean juegoActivo = puente != null && puente.juegoActivo();
        String[] opciones = {
            "Conectar con mi PC por Wi‑Fi",
            "Cara dentro del teléfono (sin PC)",
            "Poner CORT como asistente (" + estadoAsistente() + ")",
            "Leer mis avisos en voz alta (permiso: " + oido + ")",
            "Dar el permiso de los avisos",
            "Escuchar una orden ahora",
            "Recargar la cara",
            "Poner música que me gusta (suena: " + suena + ")",
            "Parar la música",
            "Dar permiso a la música y los archivos (" + medios + ")",
            "Modo juego (silencio: " + (juegoActivo ? "sí" : "no") + ")",
            // Las cinco filas de la ronda 2.1. Están aquí, y no sólo en la pantalla
            // Equipo, porque hay frases que se dicen sin abrir nada: «qué tengo hoy»
            // o «cuadra la memoria». El orden de los `case` de abajo es ESTE orden.
            "¿Qué tengo hoy? (calendario: " + calendario + ")",
            "Mis avisos de correo",
            "Punto flotante de CORT (" + enPunto + ", permiso: " + flotante + ")",
            "Cuadrar la memoria con el PC",
            "Probar el cerebro del teléfono",
        };
        new AlertDialog.Builder(this)
            .setTitle("CORT")
            .setItems(opciones, (dialogo, cual) -> {
                switch (cual) {
                    case 0: pideDireccion(); break;
                    case 1: guardarPC(""); break;
                    case 2: abreAjustesDeAsistente(); break;
                    case 3: puente.leeAvisos(); break;
                    case 4: puente.abreAjustesAvisos(); break;
                    case 5: puente.escuchaAhora(); break;
                    case 6: arranca(); break;
                    case 7: puente.musicaAutomatica(); break;
                    case 8: puente.musicaParar(); break;
                    case 9: puente.pidePermisoMedios(); break;
                    // La fila once (índice 10) es la última del bloque viejo: los
                    // `case` van en el mismo orden que las filas de arriba — uno mal
                    // numerado es un botón que hace otra cosa.
                    case 10: puente.modoJuego(!juegoActivo); break;
                    // Las cuatro filas nuevas (índices 11 a 15) son la ronda 2.1. Cada
                    // una habla por sí sola y escribe su resultado en la cara, así que
                    // la pantalla y la voz cuentan la misma historia.
                    case 11: puente.leeAgenda("{\"que\":\"hoy\"}"); break;
                    case 12: puente.leeAgenda("{\"que\":\"correo\"}"); break;
                    case 13: {
                        String respuesta = puente.burbuja(!Flotante.montada());
                        avisa(textoCorto(respuesta));
                        break;
                    }
                    case 14: puente.sincronizaMemoria();
                        avisa("Cuadrando con tu portátil: te aviso al terminar"); break;
                    case 15: puente.pruebaCerebro();
                        avisa("Pensando: te lo digo por voz cuando termine"); break;
                    default: arranca(); break;
                }
            })
            .show();
    }

    /**
     * Mostrar u ocultar el botón flotante, hoja por hoja (`CortNative.menuPC`).
     *
     * El botón se añade encima del `WebView` (`MainActivity.java:171-186`), así que
     * no lo tapa la cara: se pinta encima de lo que ella muestre. Antes de este
     * método no existía un solo `setVisibility` para él en todo el repo, y por eso la
     * dueña lo encontró «atravesado» sobre la píldora de la música. Se oculta en las
     * hojas con barra propia y vuelve en el orbe, donde no estorba nada.
     *
     * Va con `runOnUiThread` porque el puente lo llama desde el hilo del JavaScript de
     * la WebView, y tocar una vista desde otro hilo es el `CalledFromWrongThreadException`
     * que cerraría la app.
     */
    void muestraMenuPC(boolean visible) {
        if (botonMenu == null) return;
        Button boton = botonMenu;
        runOnUiThread(() -> boton.setVisibility(visible ? View.VISIBLE : View.GONE));
    }

    /**
     * La línea que se enseña en el menú: el `dice` del JSON del puente, sin tener
     * que meter un parser en la actividad. Si el cuadro venía torcido, se dice tal
     * cual, que es peor de leer pero nunca mentira.
     */
    private static String textoCorto(String json) {
        if (json == null) return "El teléfono no contestó";
        int desde = json.indexOf("\"dice\"");
        if (desde < 0) return json.length() > 90 ? json.substring(0, 90) + "…" : json;
        int abre = json.indexOf('"', json.indexOf(':', desde) + 1);
        int cierra = abre + 1;
        while (cierra < json.length()) {
            char c = json.charAt(cierra);
            if (c == '"') break;
            cierra += c == '\\' ? 2 : 1;
        }
        return abre >= 0 && cierra > abre ? json.substring(abre + 1, Math.min(cierra, json.length()))
                                          : "El teléfono no dijo por qué";
    }

    private void pideDireccion() {
        final EditText campo = new EditText(this);
        campo.setHint("http://192.168.100.171:8000");
        campo.setText(prefs().getString("pc", ""));
        campo.setSingleLine();
        campo.setInputType(android.text.InputType.TYPE_TEXT_VARIATION_URI);
        new AlertDialog.Builder(this)
            .setTitle("Dirección de tu PC")
            .setMessage("En el portátil: bash scripts/telefono.sh y escribe la IP y el puerto que imprime.")
            .setView(campo)
            .setPositiveButton("Abrir", (a, b) -> {
                guardarPC(campo.getText().toString().trim());
                hideTeclado();
            })
            .setNegativeButton("Cancelar", null)
            .show();
    }

    /**
     * Guarda (o borra con cadena vacía) la dirección del PC y conecta **sólo
     * ahora**: vacía vuelve a la cara del teléfono; con dirección carga esa cara
     * remota. No se llama nunca desde `onCreate`, para que abrir CORT no dependa
     * de que el portátil o el VPS estén despiertos.
     */
    void guardarPC(String url) {
        String limpia = url == null ? "" : url.trim();
        prefs().edit().putString("pc", limpia).apply();
        direccionPC = limpia;
        hideTeclado();
        if (limpia.isEmpty()) arranca();
        else web.loadUrl(aseguraSlash(limpia));
    }

    /** Abrir el menú nativo de CORT desde la hoja Equipo (el botón flotante ya no existe). */
    void abreMenu() {
        runOnUiThread(this::menu);
    }

    /**
     * «Poner CORT como asistente», por el camino que SÍ funciona con una app
     * instalada a mano.
     *
     * El orden importa:
     *
     * 1. **`RoleManager.ROLE_ASSISTANT`** (Android 10, API 29+). Es la petición
     *    oficial del rol: Android muestra su propio cuadro «¿Quieres que CORT sea
     *    tu asistente?» y, al aceptar, CORT queda elegido **sin tocar los
     *    Ajustes**. Antes de esto el botón abría una pantalla genérica y la dueña
     *    no veía a CORT por ningún lado.
     * 2. Las dos pantallas de Ajustes de siempre, como respaldo para Android 8 y
     *    9 (el `minSdk` es 26) y para los fabricantes que recortan el diálogo del rol.
     * 3. Decir el camino a mano si tampoco existe la pantalla.
     *
     * Y una cosa que se arregló **fuera** de este archivo: `res/xml/asistente.xml`
     * declaraba `settingsActivity="com.cort.ia.MainActivity"`. En AOSP
     * (`VoiceInteractionServiceInfo`) una `settingsActivity` que no pertenezca a
     * una app del sistema (`FLAG_SYSTEM`) hace que el parseo falle y la app
     * **desaparezca de la lista de asistentes**. Una APK instalada por Wi‑Fi nunca
     * es del sistema: ese atributo, que parecía un detalle, era el motivo de «no
     * me sale CORT como asistente». Ahora el acceso a los ajustes lo da este
     * método por RoleManager, que es la API pública y no cuesta aparecer.
     */
    void abreAjustesDeAsistente() {
        if (android.os.Build.VERSION.SDK_INT >= 29) {
            try {
                android.app.role.RoleManager roles = getRoles();
                if (roles != null && roles.isRoleAvailable(android.app.role.RoleManager.ROLE_ASSISTANT)) {
                    startActivityForResult(
                        roles.createRequestRoleIntent(
                            android.app.role.RoleManager.ROLE_ASSISTANT), PETICION_ROL);
                    return;
                }
            } catch (Exception eseFabricanteNoOfreceElRol) { /* baja a las pantallas de siempre */ }
        }
        try {
            startActivity(new Intent("android.settings.ASSISTANT_SETTINGS"));
            return;
        } catch (Exception una) { /* sigue intentando */ }
        try {
            startActivity(new Intent(Settings.ACTION_VOICE_INPUT_SETTINGS));
            return;
        } catch (Exception dos) {
            avisa("Elige CORT en Ajustes ▸ Aplicaciones ▸ Aplicación de asistencia predeterminada");
        }
    }

    /** El `RoleManager` del aparato, o `null` si el sistema no lo presta (API < 29). */
    private android.app.role.RoleManager getRoles() {
        if (android.os.Build.VERSION.SDK_INT < 29) return null;
        Object servicio = getSystemService(ROLE_SERVICE);
        return servicio instanceof android.app.role.RoleManager
            ? (android.app.role.RoleManager) servicio : null;
    }

    /** Estado del rol para escribirlo en el menú: la dueña ve si ya es asistente. */
    private String estadoAsistente() {
        android.app.role.RoleManager roles = getRoles();
        if (roles == null) return "a mano (Android 8/9)";
        try {
            if (roles.isRoleHeld(android.app.role.RoleManager.ROLE_ASSISTANT)) return "ya elegido";
            return roles.isRoleAvailable(android.app.role.RoleManager.ROLE_ASSISTANT)
                ? "pendiente" : "bloqueado por el fabricante";
        } catch (Exception elFabricanteMiente) {
            return "sin forma de comprobarlo";
        }
    }

    /**
     * Resultado del cuadro de RoleManager. Android no dice «aceptado» con un
     * código fiable en todos los fabricantes, así que se comprueba el rol de
     * nuevo: es la única respuesta honesta que podemos dar.
     */
    @Override
    protected void onActivityResult(int codigo, int resultado, Intent datos) {
        super.onActivityResult(codigo, resultado, datos);
        if (codigo != PETICION_ROL) return;
        avisa("CORT como asistente: " + estadoAsistente());
    }

    /**
     * Pinta el botón con el traje puesto (`Paleta`), para que «ponte azul» no se
     * quede en un color de CSS que sólo se ve en la página. Es el mismo color que
     * lee la cara por `atuendo(estado)`, así que las dos superficies no pueden
     * contradecirse: una sola preferencia, dos pintores.
     */
    void usaAtuendo() {
        runOnUiThread(() -> {
            if (botonMenu == null) return;
            try {
                botonMenu.setTextColor(Paleta.primario(this));
            } catch (Exception elTrajeNoSeLee) { /* el azul de siempre hace bien */ }
        });
    }

    private static String aseguraSlash(String url) {
        return url.endsWith("/") ? url : url + "/";
    }

    /* ─────────────────────────── permisos y ayuda ──────────────────────── */

    /**
     * El cuadro de permisos, por grupos.
     *
     * Se pide en lote y desde el hilo de la interfaz (los métodos del puente
     * corren en el hilo de JavaScript, y `requestPermissions` es de la cara), y
     * lo que se pide es lo justo para cada palabra: la música no necesita los
     * contactos, y el micrófono no necesita el disco.
     */
    void pidePermiso(String kind) {
        // La burbuja no va por cuadro: «aparecer encima de otras apps» es un
        // interruptor de Ajustes que Android se niega a pedir con `requestPermissions`
        // (tiraría un `RuntimeException`). Se abre la pantalla y listo.
        String k = kind == null ? "" : kind.toLowerCase(Locale.US);
        if (k.startsWith("burbuja") || k.startsWith("encima") || k.startsWith("flotante")
            || k.startsWith("overlay")) {
            if (puente != null) puente.abreAjustesBurbuja();
            return;
        }
        // La restricción de batería tampoco es un cuadro de `requestPermissions`:
        // es una excepción que la dueña mete en la lista, y el permiso
        // `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` (declarado) permite abrir ese
        // cuadro concreto. Si el fabricante lo quita, se cae a la lista general y,
        // si ni eso, a los ajustes de la app — siempre con la pantalla abierta
        // delante, nunca con un ✓ de confianza.
        if (k.startsWith("bateri") || k.startsWith("battery") || k.startsWith("ahorro")) {
            abreAjustesDeBateria();
            return;
        }
        // «Inicio automático» lo decide el fabricante (Xiaomi, Samsung, Oppo…) y no
        // hay API para ello: lo honesto es abrir los ajustes de la app y decirle
        // dónde está la fila.
        if (k.startsWith("autostart") || k.startsWith("arranque") || k.startsWith("inicio")) {
            abreAjustesDeLaApp();
            avisa("Busca «Inicio automático» / «Segundo plano» en los ajustes de CORT");
            return;
        }
        final String[] permisos = grupoDe(kind);
        runOnUiThread(() -> {
            String[] faltan = sinConceder(permisos);
            if (faltan.length == 0) return;
            try {
                requestPermissions(faltan, 7);
            } catch (Exception elTelefonoNoPregunta) { /* la interfaz avisa sola */ }
        });
    }

    /** La pantalla de excepciones de batería, con su atajo directo si el equipo lo tiene. */
    private void abreAjustesDeBateria() {
        runOnUiThread(() -> {
            try {
                startActivity(new Intent(
                        Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
                return;
            } catch (Exception eseFabricanteSinLista) { /* al común */ }
            abreAjustesDeLaApp();
            avisa("Ajustes ▸ Aplicaciones ▸ CORT ▸ Batería sin restricción");
        });
    }

    /** Ajustes ▸ Aplicaciones ▸ CORT: la pantalla que siempre existe. */
    private void abreAjustesDeLaApp() {
        runOnUiThread(() -> {
            try {
                startActivity(new Intent(
                        Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                        android.net.Uri.fromParts("package", getPackageName(), null))
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
            } catch (Exception tampoco) {
                avisa("No se pudieron abrir los ajustes de la app");
            }
        });
    }

    private static String[] grupoDe(String kind) {
        String k = kind == null ? "" : kind.toLowerCase(Locale.US);
        if (k.startsWith("camara") || k.startsWith("camera")) {
            return new String[] { android.Manifest.permission.CAMERA };
        }
        // Misma clase de fallo que la línea de «notif»: la cara pregunta con la
        // clave corta `files` (`perms.ask('files')` en hud.js) y sin esto se
        // caía en el micrófono. `archiv` sigue cubriendo «archivos».
        if (k.startsWith("medios") || k.startsWith("music") || k.startsWith("musica")
            || k.startsWith("archiv") || k.startsWith("file") || k.startsWith("almacen")) {
            return permisosDeArchivos();
        }
        if (k.startsWith("contacto") || k.startsWith("marcar") || k.startsWith("llam")) {
            return new String[] {
                android.Manifest.permission.READ_CONTACTS,
                android.Manifest.permission.CALL_PHONE,
            };
        }
        // «notif» es la clave que usa el panel de segundo plano, y `startsWith
        // ("notific")` no la cubre: sin esta línea el botón «Dar» de los avisos se
        // caía en el micrófono.
        if (k.startsWith("aviso") || k.startsWith("notif")) {
            return new String[] { "android.permission.POST_NOTIFICATIONS" };
        }
        // La ronda 2.1 pregunta por el calendario («¿qué tengo hoy?»). Se pide SOLO
        // de lectura: CORT abre el formulario de una cita nueva y el dedo de la
        // dueña lo guarda; escribir en su agenda sin su visto bueno no entra en el
        // contrato, y por eso `WRITE_CALENDAR` no está ni en el manifiesto.
        if (k.startsWith("calendari") || k.startsWith("agenda") || k.startsWith("cita")) {
            return new String[] { android.Manifest.permission.READ_CALENDAR };
        }
        return new String[] { android.Manifest.permission.RECORD_AUDIO };
    }

    /**
     * Hasta Android 12 vale `READ_EXTERNAL_STORAGE`; desde 13 el sistema ignora
     * ése y hay que pedir los tipos sueltos. Pedir los dos a la vez no cuela
     * (Android 13 rechaza el antiguo), así que se decide por versión.
     */
    private static String[] permisosDeArchivos() {
        if (android.os.Build.VERSION.SDK_INT >= 33) {
            return new String[] {
                "android.permission.READ_MEDIA_AUDIO",
                "android.permission.READ_MEDIA_VIDEO",
                "android.permission.READ_MEDIA_IMAGES",
            };
        }
        return new String[] { android.Manifest.permission.READ_EXTERNAL_STORAGE };
    }

    private String[] sinConceder(String[] permisos) {
        java.util.ArrayList<String> faltan = new java.util.ArrayList<>();
        for (String permiso : permisos) {
            try {
                if (checkSelfPermission(permiso) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                    faltan.add(permiso);
                }
            } catch (Exception esePermisoNoExisteEnAparejo) { /* se ignora: no hay cuadro que dar */ }
        }
        return faltan.toArray(new String[0]);
    }

    @Override
    public void onRequestPermissionsResult(int codigo, String[] permisos, int[] resultados) {
        super.onRequestPermissionsResult(codigo, permisos, resultados);
        boolean concedido = resultados.length > 0;
        for (int resultado : resultados) {
            if (resultado != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                concedido = false;
                break;
            }
        }
        String kind = claseDe(permisos);
        puente.permisoRespondido(kind, concedido);
        if (!concedido && "medios".equals(kind)) {
            avisa("Sin permiso de archivos CORT no puede ver tu música ni ordenarla");
        }
    }

    /** El `kind` que entiende la cara: coincide con el de `CortNative.hasPermission`. */
    private static String claseDe(String[] permisos) {
        for (String permiso : permisos) {
            if (permiso.endsWith("CAMERA")) return "camara";
            if (permiso.contains("MEDIA") || permiso.contains("EXTERNAL_STORAGE")) return "medios";
            if (permiso.contains("CONTACTS") || permiso.contains("CALL_PHONE")) return "contactos";
            if (permiso.contains("POST_NOTIFICATIONS")) return "avisos";
            if (permiso.contains("CALENDAR")) return "calendario";
        }
        return "mic";
    }

    void avisa(String texto) {
        runOnUiThread(() -> Toast.makeText(this, texto, Toast.LENGTH_LONG).show());
    }

    /* ─────────────────── segundo plano, dicho sin mentiras ───────────────────
       El panel «▸ Segundo plano» de 07 · Perfil promete una sola cosa real: que
       CORT **sigue vivo** cuando te vas de la app, con su aviso de Android
       puesto. No promete la palabra «Oye CORT» con la pantalla apagada ni con
       la app cerrada —eso lo dice el servidor de Google y no viaja en este APK,
       y abrir el micrófono a medias es justo lo que le trababa el teléfono a la
       dueña (ronda «y ya no traba el teléfono»). Lo que sí sigue funcionando con
       el aviso puesto es el `MediaSession`, o sea el **doble toque del
       auricular**, y que la música no se caiga.
       No es un `Service` en primer plano: es una notificación normal, así que no
       necesita `foregroundServiceType` nuevo ni el permiso de micrófono en segundo
       plano, y se quita en un toque desde la propia barra. */

    private volatile boolean primerPlano = true;
    private static final String CANAL_FONDO = "cort-fondo";
    private static final int NOTA_FONDO = 4211;

    /** Lo que lee la cara como `running`: si el aviso de fondo está puesto ahora. */
    boolean avisoDeFondoPuesto() {
        try {
            android.app.NotificationManager nm =
                    (android.app.NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            return nm != null && nm.getActiveNotifications() != null
                   && java.util.Arrays.stream(nm.getActiveNotifications())
                          .anyMatch(n -> n.getId() == NOTA_FONDO);
        } catch (Exception eseAparejoNoDejaMirar) {
            return false;
        }
    }

    /** `setBackground` de la cara: si se cambia el interruptor, el aviso se pone o cae. */
    void alAvisoDeFondoLeGustaCambiar() {
        if (primerPlano) return;
        if (prefs().getBoolean("bg", false)) dejaAvisoDeFondo();
        else quitaAvisoDeFondo();
    }

    private void dejaAvisoDeFondo() {
        if (!prefs().getBoolean("bg", false)) { quitaAvisoDeFondo(); return; }
        try {
            android.app.NotificationManager nm =
                    (android.app.NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            if (nm == null) return;
            canalDeFondo(nm);
            Intent vuelve = new Intent(this, MainActivity.class);
            PendingIntent quienVuelve = PendingIntent.getActivity(this, 4212, vuelve,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            android.app.Notification.Builder b =
                    (android.os.Build.VERSION.SDK_INT >= 26)
                    ? new android.app.Notification.Builder(this, CANAL_FONDO)
                    : new android.app.Notification.Builder(this);
            b.setSmallIcon(android.R.drawable.ic_media_play)
             .setContentTitle("CORT en segundo plano")
             .setContentText("El doble toque del auricular y la música siguen. "
                             + "El micrófono está cerrado para no trabarte.")
             .setContentIntent(quienVuelve)
             .setOngoing(true)
             .setPriority(android.app.Notification.PRIORITY_LOW);
            nm.notify(NOTA_FONDO, b.build());
        } catch (Exception noDejaAvisar) {
            // Sin permiso de avisos (Android 13) no hay forma de quedarse visto:
            // la cara lo muestra como permiso pendiente, no como «activo».
            android.util.Log.i("MainActivity", "segundo plano sin aviso: " + noDejaAvisar);
        }
    }

    private void quitaAvisoDeFondo() {
        try {
            android.app.NotificationManager nm =
                    (android.app.NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            if (nm != null) nm.cancel(NOTA_FONDO);
        } catch (Exception daIgual) { /* el proceso se va igual */ }
    }

    private void canalDeFondo(android.app.NotificationManager nm) {
        if (android.os.Build.VERSION.SDK_INT < 26 || nm.getNotificationChannel(CANAL_FONDO) != null) return;
        android.app.NotificationChannel c = new android.app.NotificationChannel(
                CANAL_FONDO, "CORT · segundo plano",
                android.app.NotificationManager.IMPORTANCE_LOW);
        c.setShowBadge(false);
        nm.createNotificationChannel(c);
    }

    /**
     * El hueco por donde el puente Java mete mensajes en la página.
     *
     * `evaluateJavascript` es método de `WebView`, no de `Activity`: el puente
     * tiene `MainActivity` y por eso llama aquí. Sin este método, `javac` diría
     * «cannot find symbol: method evaluateJavascript» en `CortNative.java`.
     */
    void evalua(String js) {
        if (web != null) web.evaluateJavascript(js, null);
    }

    SharedPreferences prefs() {
        return getSharedPreferences("cort", MODE_PRIVATE);
    }

    private void hideTeclado() {
        InputMethodManager inm = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
        View foco = getCurrentFocus();
        if (inm != null && foco != null) inm.hideSoftInputFromWindow(foco.getWindowToken(), 0);
    }

    private int dp(int valor) {
        float densidad = getResources().getDisplayMetrics().density;
        return (int) (valor * densidad + 0.5f);
    }

    @Override
    public void onBackPressed() {
        // Con el PC delante puede haber historial (una ventana que navegó); en la
        // cara embebida no hay a dónde volver, así que se sale como cualquier app.
        if (web != null && web.canGoBack()
            && web.getUrl() != null && !web.getUrl().startsWith(ORIGEN)) {
            web.goBack();
            return;
        }
        super.onBackPressed();
    }
}
