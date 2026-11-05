package dev.sandra.cort.movil;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.view.inputmethod.InputMethodManager;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import java.io.IOException;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.net.SocketTimeoutException;
import java.nio.charset.StandardCharsets;

/**
 * La ventana de CORT en el teléfono, y desde `v0.15.0` también su cuerpo.
 * Escrito contra el SDK puro —sin AndroidX, sin Gradle, sin Capacitor— porque
 * cada dependencia es una descarga que el pipeline tiene que traer y este
 * proyecto no reparte sorpresas: `compilar.sh` usa sólo `aapt2`, `javac` y `d8`.
 *
 * El reparto nuevo, en tres caminos y ninguno obligatorio:
 *
 * - **El portátil está publicado en la Wi-Fi** → `WebView` con la página React:
 *   la cara buena, el cuerpo 3D, los atuendos. Se encuentra solo, con el
 *   protocolo UDP de `v0.14.4`.
 * - **No está** → `Nexo`: desde `v0.17.0` la **misma cara del PC**, servida
 *   desde los `assets` del APK sobre el origen inventado
 *   `https://cort.local`, con el cerebro Java detrás (`Cerebro`, `Acciones`,
 *   `Recuerdos`, `Voz`) y los mismos cuadros que viajan por el WebSocket.
 * - **Tampoco viajó el `dist`, o el WebView se cayó** → `Cara`, la cara nativa: CORT oye por el micrófono de Android,
 *   habla por su altavoz, maneja el aparato y recuerda en SQLite. Sin servidor,
 *   sin HTTPS y sin abrir el portátil — que es lo que la dueña pidió.
 * - **Ninguna de las dos funciona** (red aislada, core caído) → el campo de
 *   siempre para pegar el enlace, escondido detrás de un toque largo.
 *
 * Esta clase decide **qué superficie se ve** y nada más: el lazo está en
 * `Cerebro`/`Acciones`, la memoria en `Recuerdos`, la voz en `Voz` y la nube
 * opcional en `Nube`.
 */
public class MainActivity extends Activity {
    /* El protocolo de divulgación: dos datagramas, y su otra mitad vive en
       `scripts/cort.py` (`DESCUBRIR`, `DESCUBRIR_RESPUESTA`, `DESCUBRIR_PUERTO`).
       `test_apk_manifesta.py` comprueba que los dos lados sigan diciendo lo
       mismo — aquí no hay import compartido posible entre Java y Python, así
       que la prueba es la costura. */
    private static final String SONDA = "CORT-ENCONTRARSO-1";
    private static final String RESPUESTA = "CORT-AQUI-1|";
    private static final int PUERTO_DIVULGACION = 8781;
    private static final int MILISEGAS_POR_INTENTO = 900;
    private static final int INTENTOS = 3;

    /**
     * La bandera que ponen `Sesion.java` y `Reconocimiento.java` al abrir la cara
     * desde fuera: «ábrete y ponte a escuchar». Vive aquí, y no como cadena
     * suelta en los dos archivos, porque las tres mitades tienen que decir
     * literalmente lo mismo y aquí no hay un test de Android que lo compruebe.
     */
    public static final String PIDE_ESCUCHAR = "cort-escuchar";

    private WebView web;
    private Nexo nexo;          // la cara del PC, servida desde el propio APK
    private Cara cara;          // la superficie nativa, cuando no hay portátil
    private LinearLayout capa;  // root: una sola cara a la vez
    private TextView aviso;     // el motivo por el que el enlace no vale
    private TextView ayuda;     // el texto que cuenta qué está pasando
    private EditText campoEnlace;   // el campo de la pantalla de enlace, para rellenarlo desde la cámara
    private volatile boolean buscando;

    /** El identificador de la vuelta del escáner de QR (F14b). */
    private static final int ESCANEO = 43;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().getDecorView().setBackgroundColor(Paleta.FONDO);
        // Con el teclado abierto la pantalla se recoloca en vez de quedar
        // tapada: el campo está en el centro y el botón debajo.
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        capa = new LinearLayout(this);
        capa.setOrientation(LinearLayout.VERTICAL);
        capa.setBackgroundColor(Paleta.FONDO);
        setContentView(capa);
        pideNotificaciones();
        mostrarOSetup();
        escuchaSiPidenDesdeFuera();
    }

    /**
     * El saludo al encender (`Arranque.java`) sale también por notificación, porque con
     * el teléfono bloqueado hay motores de voz que no sueltan sonido; y con Android 13
     * esa notificación no se ve si nadie pidió `POST_NOTIFICATIONS`. Se pide una sola
     * vez —queda escrito en las preferencias— y se pide aquí, donde la dueña acaba de
     * abrir la app y espera que algo pase, no desde un receptor que se despierta solo.
     */
    private void pideNotificaciones() {
        if (android.os.Build.VERSION.SDK_INT < 33 || prefs().getBoolean("aviso_pedido", false)) {
            return;
        }
        prefs().edit().putBoolean("aviso_pedido", true).apply();
        if (checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
                != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{android.Manifest.permission.POST_NOTIFICATIONS}, 44);
        }
    }

    @Override
    protected void onNewIntent(Intent intento) {
        super.onNewIntent(intento);
        // `singleTop` en el manifiesto: el asistente que se vuelve a pulsar no
        // monta una segunda cara encima de la primera, entrega aquí su bandera.
        setIntent(intento);
        escuchaSiPidenDesdeFuera();
    }

    /**
     * Si quien abrió la app fue el traje de asistente (`Sesion.java`,
     * `Reconocimiento.java`), CORT se pone a escuchar sin que nadie pulse el ●.
     *
     * Va con `post()` y no en línea: en el primer arranque `mostrarOSetup()` está
     * decidiendo si la cara es la nativa o el WebView del portátil, y `cara` aún
     * es `null`. Si el portátil apareció y manda la ventana, **no** se escucha
     * por este camino: esa cara tiene su propio micrófono en la página.
     */
    private void escuchaSiPidenDesdeFuera() {
        final Intent pedido = getIntent();
        if (pedido == null || !pedido.getBooleanExtra(PIDE_ESCUCHAR, false)) {
            return;
        }
        capa.post(() -> {
            if (nexo != null && web == null) {
                // La cara embebida no tiene micrófono propio: el WebView no expone
                // `SpeechRecognition`. Quien oye es el `SpeechRecognizer` de Java,
                // por el mismo puente que usa el botón ● de la página.
                nexo.escuchar();
                return;
            }
            if (cara != null && web == null) {
                cara.escucharAhora();
            }
        });
    }

    private SharedPreferences prefs() {
        return getSharedPreferences("cort", MODE_PRIVATE);
    }

    /**
     * Ya no se espera a nadie: la cara nativa se monta **siempre**, y encima se
     * busca el portátil. Si aparece, se cambia de superficie; si no, CORT sigue
     * siendo útil aquí dentro.
     *
     * Cuando hay una dirección guardada de otra sesión se prueba primero el
     * WebView, que es la cara completa; si falla la carga se cae a la nativa en
     * vez de dejar la pantalla en blanco de Android.
     */
    private void mostrarOSetup() {
        String url = prefs().getString("url", "");
        if (!url.isEmpty()) {
            abrir(url, prefs().getString("token", ""));
            return;
        }
        // `v0.17.0`: sin portátil ya no hace falta montar la cara nativa. El APK
        // trae consigo la cara del PC (`assets/web/`), y mientras ese `dist` exista
        // es la que se ve: la misma React, el mismo orbe, los mismos paneles.
        // `Cara` queda de respaldo, y si la página no viajó en el compilado o el
        // WebView se cae, se monta igual.
        if (hayCaraEmbebida()) {
            montarWebLocal();
        } else {
            montarCara();
        }
        buscarATelefonoSilencio();
    }

    private Boolean embebida;

    /**
     * Si el `dist` de la cara viajó dentro de este APK. Se mira una sola vez y se
     * guarda: `AssetManager.list` toca disco, y esto se decide en cada `onCreate`.
     */
    private boolean hayCaraEmbebida() {
        if (embebida == null) {
            boolean encontrada = false;
            try {
                for (String nombre : getAssets().list(Nexo.DOSSIER)) {
                    if ("index.html".equals(nombre)) {
                        encontrada = true;
                    }
                }
            } catch (IOException noHay) {
                encontrada = false;   // sin dossier no hay cara embebida, y no pasa nada
            }
            embebida = encontrada;
        }
        return embebida;
    }

    /** La cara del portátil, montada sobre los archivos del propio teléfono. */
    private void montarWebLocal() {
        nexo = new Nexo(this, () -> {
            // El `WebView` se cayó de verdad: sin `dist` en el APK, sin WebView en
            // el aparato, o con el arranque cortado. La nativa funciona sin página,
            // así que nunca se queda la dueña en blanco.
            runOnUiThread(this::volverACara);
        });
        nexo.montar(capa);
    }

    /** La superficie nativa, con sus datos de aparato ya sembrados. */
    private void montarCara() {
        if (cara != null) {
            capa.removeAllViews();
            cara.montar(capa);
            return;
        }
        cara = new Cara(this);
        capa.removeAllViews();
        cara.montar(capa);
    }

    /**
     * Pregunta en la red, y si CORT contesta cambia a la ventana del portátil
     * sin que nadie toque nada — que es lo que la dueña pidió: «que inicie con
     * su animación como una IA normal».
     *
     * Corre en su propio hilo porque `DatagramSocket.receive` bloquea, y
     * bloquear el hilo de la interfaz congela el anillo. El resultado se aplica
     * con `runOnUiThread`, y **sólo si la usuaria sigue sin haber abierto nada**:
     * si mientras tanto escribió o salió, no se le cambia la pantalla.
     */
    private void buscarATelefonoSilencio() {
        if (buscando) {
            return;
        }
        buscando = true;
        new Thread(() -> {
            final String encontrado = preguntarEnLaRed();
            buscando = false;
            runOnUiThread(() -> {
                if (encontrado == null) {
                    if (cara != null) {
                        cara.decirDondeEstaElPortatil(false);
                        cara.hablar("Estoy en el teléfono. Tu portátil no aparece por "
                                + "la Wi-Fi, pero funcionamos igual.");
                    }
                    return;
                }
                if (web != null) {
                    return;
                }
                if (nexo != null) {
                    // Apareció el portátil: la cara embebida se quita y manda el
                    // core, que es la misma regla de siempre con la cara nativa.
                    nexo.cerrar();
                    nexo = null;
                }
                prefs().edit().putString("url", encontrado).putString("token", "").apply();
                abrir(encontrado, "");
            });
        }).start();
    }

    /**
     * La sonda, tres intentos de 900 ms, y la primera respuesta válida vale.
     *
     * `255.255.255.255` es el broadcast del segmento: llega al portátil sin
     * saber su IP, que es justo el conocimiento que faltaba. Hay redes donde el
     * broadcast no pasa —VLAN de oficina, puntos de acceso con aislamiento de
     * cliente—, así que esto devuelve `null` sin dramas: desde `v0.15.0` el
     * silencio ya no deja a la usuaria delante de un formulario, deja la cara
     * nativa encendida.
     */
    private String preguntarEnLaRed() {
        DatagramSocket socket = null;
        try {
            socket = new DatagramSocket();
            socket.setBroadcast(true);
            socket.setSoTimeout(MILISEGAS_POR_INTENTO);
            byte[] sonda = SONDA.getBytes(StandardCharsets.UTF_8);
            InetAddress difusion = InetAddress.getByName("255.255.255.255");
            byte[] buffer = new byte[1024];
            for (int intento = 0; intento < INTENTOS; intento++) {
                try {
                    socket.send(new DatagramPacket(sonda, sonda.length, difusion,
                            PUERTO_DIVULGACION));
                    DatagramPacket respuesta = new DatagramPacket(buffer, buffer.length);
                    socket.receive(respuesta);
                    String texto = new String(respuesta.getData(), respuesta.getOffset(),
                            respuesta.getLength(), StandardCharsets.UTF_8);
                    if (texto.startsWith(RESPUESTA)) {
                        String enlace = texto.substring(RESPUESTA.length()).trim();
                        if (enlace.startsWith("http://") || enlace.startsWith("https://")) {
                            return enlace;
                        }
                    }
                } catch (SocketTimeoutException nadieAun) {
                    // silencio en este turno: se insiste mientras gira el anillo
                } catch (IOException noSePuede) {
                    return null;   // ni sonda sale ni respuesta entra: CORT se queda en el teléfono
                }
            }
            return null;
        } catch (IOException sinSocket) {
            return null;   // sin UDP no hay descubrimiento, y la cara nativa sigue ahí
        } finally {
            if (socket != null) {
                socket.close();
            }
        }
    }

    /* ------------------------------------------------------------------ WebView */

    /**
     * El enlace que abre la ventana. Si ya trae `?token=` —porque la usuaria
     * copió el enlace completo del lanzador— se respeta tal cual: parsearlo y
     * reconstruirlo sería una forma de romper un secreto.
     */
    private void abrir(String base, String token) {
        // El enlace que se guarda es el que imprime la PC y cabe en el QR —`…:8765/memoria/puente`—
        // y la ventana necesita la interfaz. `urlDeLaCara` cambia el puerto y la ruta
        // conservando la llave; si ya era una dirección de página, devuelve lo mismo.
        String vuelta = Puente.urlDeLaCara(base);
        final String pagina = vuelta == null ? base : vuelta;
        // `final` y en una sola expresión: el `WebViewClient` anónimo de abajo
        // captura esta cadena, y una variable reasignada no la puede capturar.
        final String destino = token.isEmpty() || pagina.contains("token=")
                ? pagina
                : pagina + (pagina.contains("?") ? "&" : "?") + "token=" + token;
        web = new WebView(this);
        // Oscuro desde el primer fotograma: sin esto el WebView pinta su fondo
        // blanco antes de que la página arranque.
        web.setBackgroundColor(Paleta.FONDO);
        capa.removeAllViews();
        capa.addView(web, new LinearLayout.LayoutParams(-1, -1));
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        // `speechSynthesis` y el `<video>` de los gestos son «reproducción» a
        // ojos del WebView: sin esta línea CORT quedaría muda hasta que alguien
        // toque la pantalla.
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);       // la página viene de la red, no del disco
        s.setAllowContentAccess(false);
        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedError(WebView vista, WebResourceRequest peticion,
                                        WebResourceError error) {
                if (!peticion.isForMainFrame()) {
                    return;   // un icono que falta no es CORT caído
                }
                // El caso normal no es un fallo raro: el portátil se apagó o su IP
                // cambió. Antes esto dejaba la cara de Android; desde `v0.15.0` se
                // cae a la nativa, que funciona sin él.
                avisar("Se fue el portátil. Sigo en el teléfono.");
                prefs().edit().putString("url", "").apply();
                volverACara();
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest request) {
                // Los gestos de cámara (`defocus.ts`) y el micrófono por
                // `getUserMedia` piden aquí. Se concede lo que la página solicita,
                // dentro de lo que el manifest declaró.
                request.grant(request.getResources());
            }
        });
        web.loadUrl(destino);
    }

    /** Cerrar el WebView y devolver el control a la cara nativa. */
    private void volverACara() {
        if (web != null) {
            web.destroy();
            web = null;
        }
        if (nexo != null) {
            nexo.cerrar();
            nexo = null;
        }
        montarCara();
        buscarATelefonoSilencio();
    }

    /* ------------------------------------------------------------------ pegado de respaldo */

    private void pantallaDeConfiguracion(final String previo) {
        capa.removeAllViews();
        if (web != null) {
            web.destroy();
            web = null;
        }
        ScrollView desplazable = new ScrollView(this);
        LinearLayout pantalla = new LinearLayout(this);
        pantalla.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(24);
        pantalla.setPadding(pad, pad, pad, pad);
        desplazable.addView(pantalla, new LinearLayout.LayoutParams(-1, -2));
        capa.addView(desplazable, new LinearLayout.LayoutParams(-1, -1));

        Anillo anillo = new Anillo(this);
        LinearLayout.LayoutParams marca = new LinearLayout.LayoutParams(dp(120), dp(120));
        marca.topMargin = dp(14);
        marca.gravity = Gravity.CENTER_HORIZONTAL;
        pantalla.addView(anillo, marca);

        TextView titulo = texto("CORT", 32f, Paleta.CIAN);
        titulo.setTypeface(Typeface.create("sans-serif-light", Typeface.BOLD));
        titulo.setLetterSpacing(0.16f);
        pantalla.addView(titulo, centrado(-2));

        ayuda = texto("Dos formas de enlazar la PC (F14). En la PC, con CORT abierto a la red:\n"
                + "  python3 cort-bridge/cort_enlace.py --qr\n"
                + "y escanea el cuadro, o pega aquí la línea entera que imprime el arranque —"
                + "con su `?token=`, que es la llave de la red de la casa—. Se guarda y no se "
                + "vuelve a pedir. Sin enlace el teléfono sigue funcionando solo: lo que hay "
                + "aquí es la ventana hacia el portátil y su memoria, no su requisito.",
                15f, Paleta.CLARO);
        ayuda.setLineSpacing(0f, 1.25f);
        LinearLayout.LayoutParams cuerpo = new LinearLayout.LayoutParams(-1, -2);
        cuerpo.topMargin = dp(26);
        pantalla.addView(ayuda, cuerpo);

        final EditText campo = new EditText(this);
        campo.setHint("http://192.168.1.xxx:8765/memoria/puente?token=…");
        campo.setInputType(InputType.TYPE_TEXT_VARIATION_URI
                | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        campo.setSingleLine(true);
        campo.setTextColor(Paleta.CLARO);
        campo.setHintTextColor(Paleta.SUAVE);
        campo.setBackgroundColor(Paleta.CAMPO);
        campo.setTextSize(15f);
        campo.setPadding(dp(14), dp(16), dp(14), dp(16));
        if (!previo.isEmpty()) {
            campo.setText(previo);
        }
        LinearLayout.LayoutParams caja = new LinearLayout.LayoutParams(-1, -2);
        caja.topMargin = dp(18);
        pantalla.addView(campo, caja);
        campoEnlace = campo;

        aviso = texto("", 13f, Paleta.AVISO);
        aviso.setVisibility(View.INVISIBLE);
        pantalla.addView(aviso, centrado(-2));

        Button entrar = new Button(this);
        entrar.setText("Abrir CORT");
        entrar.setTextColor(Paleta.CIAN);
        entrar.setBackgroundColor(0xFF0F2B3A);
        entrar.setTextSize(17f);
        entrar.setLetterSpacing(0.06f);
        LinearLayout.LayoutParams boton = new LinearLayout.LayoutParams(-1, dp(54));
        boton.topMargin = dp(14);
        pantalla.addView(entrar, boton);

        // Leer el cuadro con la cámara del teléfono es lo que quita de en medio teclear una
        // llave de 24 caracteres en una pantalla de 6 pulgadas. Es un botón más, no el único
        // camino: si la cámara falla, el campo de arriba sigue funcionando igual.
        Button escanear = new Button(this);
        escanear.setText("Escanear el QR del portátil");
        escanear.setTextColor(Paleta.CIAN);
        escanear.setBackgroundColor(0xFF132F3F);
        escanear.setTextSize(15f);
        escanear.setLetterSpacing(0.04f);
        LinearLayout.LayoutParams leedor = new LinearLayout.LayoutParams(-1, dp(54));
        leedor.topMargin = dp(10);
        pantalla.addView(escanear, leedor);

        // El parlamento (F16): la frase se graba aquí, se transcribe y se responde en la
        // PC, y la contesta llega al auricular. Es un botón más —el micrófono de la cara
        // nativa y el del WebView siguen haciendo lo suyo— y sin enlace guardado la propia
        // pantalla de parlamento lo dice con palabras antes de dejar pulsando a nadie.
        Button hablar = new Button(this);
        hablar.setText("Hablar con la PC (voz)");
        hablar.setTextColor(Paleta.CIAN);
        hablar.setBackgroundColor(0xFF132F3F);
        hablar.setTextSize(15f);
        hablar.setLetterSpacing(0.04f);
        LinearLayout.LayoutParams parlamento = new LinearLayout.LayoutParams(-1, dp(54));
        parlamento.topMargin = dp(10);
        pantalla.addView(hablar, parlamento);

        // U2 y F17, en la misma pantalla porque las tres viven del enlace.
        Button pendiente = new Button(this);
        pendiente.setText("Lo pendiente en la PC");
        pendiente.setTextColor(Paleta.CIAN);
        pendiente.setBackgroundColor(0xFF132F3F);
        pendiente.setTextSize(15f);
        LinearLayout.LayoutParams cajaPendiente = new LinearLayout.LayoutParams(-1, dp(54));
        cajaPendiente.topMargin = dp(10);
        pantalla.addView(pendiente, cajaPendiente);

        Button aparato = new Button(this);
        aparato.setText("El aparato, medido (RAM para el cerebro local)");
        aparato.setTextColor(Paleta.AVISO);
        aparato.setBackgroundColor(0xFF132F3F);
        aparato.setTextSize(15f);
        LinearLayout.LayoutParams cajaAparato = new LinearLayout.LayoutParams(-1, dp(54));
        cajaAparato.topMargin = dp(10);
        pantalla.addView(aparato, cajaAparato);

        // U1: la despensa. Desde aquí se bajan los cerebros GGUF y se elige cuál
        // piensa; hace falta también sin portátil encendido, pero la pantalla vive
        // junto a la medida de RAM porque las dos se leen juntas.
        Button almacen = new Button(this);
        almacen.setText("Almacén de cerebros (bajar y usar)");
        almacen.setTextColor(Paleta.CIAN);
        almacen.setBackgroundColor(0xFF132F3F);
        almacen.setTextSize(15f);
        LinearLayout.LayoutParams cajaAlmacen = new LinearLayout.LayoutParams(-1, dp(54));
        cajaAlmacen.topMargin = dp(10);
        pantalla.addView(almacen, cajaAlmacen);

        Button pila = new Button(this);
        pila.setText("Que el teléfono no cierre CORT");
        pila.setTextColor(Paleta.SUAVE);
        pila.setBackgroundColor(0xFF0C1F2B);
        pila.setTextSize(14f);
        LinearLayout.LayoutParams cajaPila = new LinearLayout.LayoutParams(-1, dp(50));
        cajaPila.topMargin = dp(10);
        pantalla.addView(pila, cajaPila);

        TextView nota = texto("El saludo al encender y la baldosa del panel rápido sólo "
                + "funcionan si Samsung no cierra CORT en segundo plano. Se abre el ajuste "
                + "del sistema con esta app escrita: se confirma y ya.\n\n"
                + "Y una cosa que no puede: levantar el portátil apagado. Medido el "
                + "4/11/2026 sin privilegios: el puerto de red (r8169) no anunció Wake-on "
                + "y está sin cable, y el Wi-Fi (rtl8723be) no anuncia wake inalámbrico. "
                + "Con un cable y el permiso de red se vuelve a comprobar.", 12f, Paleta.SUAVE);
        nota.setLineSpacing(0f, 1.3f);
        LinearLayout.LayoutParams cajaNota = new LinearLayout.LayoutParams(-1, -2);
        cajaNota.topMargin = dp(12);
        pantalla.addView(nota, cajaNota);

        Button volver = new Button(this);
        volver.setText("Seguir en el teléfono");
        volver.setTextColor(Paleta.SUAVE);
        volver.setBackgroundColor(Paleta.FONDO);
        volver.setTextSize(14f);
        pantalla.addView(volver, new LinearLayout.LayoutParams(-1, dp(48)));

        TextView pie = texto("¿No lo tienes? En el portátil:  python scripts/cort.py --lan\n"
                + "El enlace sale en la línea «red» del arranque, con su llave.",
                12f, Paleta.SUAVE);
        pie.setLineSpacing(0f, 1.3f);
        LinearLayout.LayoutParams piecaja = new LinearLayout.LayoutParams(-1, -2);
        piecaja.topMargin = dp(20);
        pantalla.addView(pie, piecaja);

        entrar.setOnClickListener(v -> intentar(campo));
        escanear.setOnClickListener(v ->
                startActivityForResult(new Intent(this, Escaner.class), ESCANEO));
        hablar.setOnClickListener(v -> startActivity(new Intent(this, Parlamento.class)));
        pendiente.setOnClickListener(v -> startActivity(new Intent(this, Bolsillo.class)));
        aparato.setOnClickListener(v -> startActivity(new Intent(this, Equipo.class)));
        almacen.setOnClickListener(v -> startActivity(new Intent(this, Cerebros.class)));
        pila.setOnClickListener(v -> pideSinOptimizacion());
        volver.setOnClickListener(v -> montarCara());
        campo.setOnEditorActionListener((v, accion, ev) -> {
            intentar(campo);
            return true;
        });
        campo.post(() -> campo.requestFocus());
    }

    /** Validar el enlace pegado, guardarlo y abrir la ventana. */
    private void intentar(EditText campo) {
        String pegado = campo.getText().toString().trim();
        if (pegado.isEmpty()) {
            marcar("Pega el enlace que imprime CORT al arrancar.");
            return;
        }
        if (!pegado.startsWith("http://") && !pegado.startsWith("https://")) {
            // Amable con quien escribe la IP a mano: `192.168.x.x` no es un enlace,
            // pero se adivina — y en esta rama la interfaz del puente vive en el
            // 8766, así que si no trae puerto se le pone ése.
            pegado = "http://" + pegado;
        }
        if (!pegado.matches("https?://[^/]+:\\d+.*")) {
            pegado = pegado.replaceFirst("(https?://[^/]+)", "$1:8766");
        }
        // Desde F14a el puente **sí** pide llave: sin `?token=` responde 401 y `Sincroniza`
        // lo dice con palabras. La ventana, en cambio, abre igual —por eso aquí no se
        // rechaza el enlace—, pero se avisa: una dirección sin llave es media CORT.
        if (!pegado.contains("token=")) {
            // `Toast` y no `marcar`: justo debajo se monta el WebView, y el `TextView` de
            // aviso se va con la pantalla. Lo que la dueña tiene que leer sobrevive al cambio.
            Toast.makeText(this, "Sin la llave no hay memoria compartida: pega la línea "
                            + "completa que imprime la PC, con su «?token=…». La ventana abre igual.",
                    Toast.LENGTH_LONG).show();
        }
        prefs().edit().putString("url", pegado).putString("token", "").apply();
        esconderTeclado();
        abrir(pegado, "");
    }

    /**
     * La vuelta del escáner (F14b). Con cuadro leído se rellena el campo y se abre: la llave
     * ya venía dentro del enlace, así que pedirle a la dueña otro toque sería inventárselo.
     */
    @Override
    protected void onActivityResult(int peticion, int resultado, Intent datos) {
        super.onActivityResult(peticion, resultado, datos);
        if (peticion != ESCANEO || campoEnlace == null) {
            return;
        }
        String leido = datos == null ? null : datos.getStringExtra(Escaner.TEXTO);
        if (resultado == RESULT_OK && leido != null && !leido.trim().isEmpty()) {
            campoEnlace.setText(leido.trim());
            intentar(campoEnlace);
            return;
        }
        marcar(leido == null || leido.trim().isEmpty()
                ? "el cuadro no se leyó: acerca el teléfono a la pantalla y prueba otra vez"
                : leido);
    }

    private void marcar(String motivo) {
        if (aviso != null) {
            aviso.setText(motivo);
            aviso.setVisibility(View.VISIBLE);
        }
    }

    /**
     * El permiso de pila: sin él One UI mata el proceso y con él se van el saludo al
     * encender y la baldosa. La intención del sistema abre el cuadro con esta app ya
     * escrita, pero en Samsung no siempre está registrada, así que se prueba la ruta
     * larga del listado de apps y, si tampoco, se dicen los toques a mano. En los tres
     * casos decide la dueña: CORT no se exime de la suspensión por su cuenta.
     */
    private void pideSinOptimizacion() {
        try {
            startActivity(new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                    Uri.parse("package:" + getPackageName())));
            return;
        } catch (ActivityNotFoundException noHayCuadro) {
            // sigue por la ruta larga
        }
        try {
            startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:" + getPackageName())));
            return;
        } catch (ActivityNotFoundException tampocoAjustes) {
            // se cuenta en pantalla
        }
        marcar("El teléfono no abrió el ajuste: Ajustes › Aplicaciones › CORT › Batería › "
                + "«Sin restricciones». Sin ese toque el saludo al encender puede no llegar.");
    }

    private LinearLayout.LayoutParams centrado(int alto) {
        LinearLayout.LayoutParams l = new LinearLayout.LayoutParams(-1, alto);
        l.gravity = Gravity.CENTER_HORIZONTAL;
        return l;
    }

    private TextView texto(String contenido, float sp, int color) {
        TextView t = new TextView(this);
        t.setText(contenido);
        t.setTextSize(sp);
        t.setTextColor(color);
        t.setGravity(Gravity.CENTER_HORIZONTAL);
        return t;
    }

    private int dp(float valor) {
        return Math.round(valor * getResources().getDisplayMetrics().density);
    }

    private void avisar(String mensaje) {
        Toast.makeText(this, mensaje, Toast.LENGTH_LONG).show();
    }

    /** La llave no va en un toast que puede acabar en una captura. */
    private String recortar(String enlace) {
        int corte = enlace.indexOf("?token=");
        return corte > 0 ? enlace.substring(0, corte) + "/?token=…" : enlace;
    }

    private void esconderTeclado() {
        View foco = getCurrentFocus();
        if (foco != null) {
            InputMethodManager inm = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
            inm.hideSoftInputFromWindow(foco.getWindowToken(), 0);
        }
    }

    /* ------------------------------------------------------------------ gestos */

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
            return;
        }
        // El botón «atrás» no sale a la calle a la primera: abre el menú de
        // conexión. En un teléfono con una sola pantalla, salir sin querer
        // significa perder a CORT de vista.
        menu();
    }

    /** Mantener pulsado, en cualquier superficie: el menú de siempre. */
    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (!hasFocus) {
            return;
        }
        View.OnLongClickListener pulso = v -> {
            menu();
            return true;
        };
        capa.setOnLongClickListener(pulso);
        if (web != null) {
            web.setOnLongClickListener(pulso);
        }
    }

    private void menu() {
        final String guardada = prefs().getString("url", "");
        new AlertDialog.Builder(this)
                .setTitle("Dónde está CORT")
                .setMessage(guardada.isEmpty()
                        ? "Ahora mismo vivo en este teléfono. Busco tu portátil por la "
                        + "Wi-Fi y, si aparece, abro su cara completa."
                        : "Conectado a " + recortar(guardada))
                // El parlamento se alcanza desde cualquier superficie (nativa, embebida o
                // WebView) con el mismo pulso largo de siempre: la lista va arriba y los
                // tres botones de antes no cambian de sitio.
                .setItems(new String[]{"Hablar con la PC (voz)"},
                        (d, w) -> startActivity(new Intent(this, Parlamento.class)))
                .setPositiveButton("Buscar el portátil", (d, w) -> {
                    prefs().edit().putString("url", "").apply();
                    montarCara();
                    buscarATelefonoSilencio();
                })
                .setNeutralButton("Pegar un enlace", (d, w) -> pantallaDeConfiguracion(guardada))
                .setNegativeButton("Salir", (d, w) -> finish())
                .show();
    }

    @Override
    protected void onDestroy() {
        if (cara != null) {
            cara.cerrar();
        }
        if (nexo != null) {
            nexo.cerrar();
        }
        super.onDestroy();
    }
}
