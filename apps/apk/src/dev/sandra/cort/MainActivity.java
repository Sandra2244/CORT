package dev.sandra.cort;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.graphics.Typeface;
import android.os.Bundle;
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
 * - **No está** → `Cara`, la cara nativa: CORT oye por el micrófono de Android,
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

    private WebView web;
    private Cara cara;          // la superficie nativa, cuando no hay portátil
    private LinearLayout capa;  // root: una sola cara a la vez
    private TextView aviso;     // el motivo por el que el enlace no vale
    private TextView ayuda;     // el texto que cuenta qué está pasando
    private volatile boolean buscando;

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
        mostrarOSetup();
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
        montarCara();
        buscarATelefonoSilencio();
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
        // `final` y en una sola expresión: el `WebViewClient` anónimo de abajo
        // captura esta cadena, y una variable reasignada no la puede capturar.
        final String destino = (token.isEmpty() || base.contains("token="))
                ? base
                : base + (base.contains("?") ? "&" : "/?") + "token=" + token;
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

        ayuda = texto("Sólo si tu red no deja buscar por Wi-Fi: pega el enlace que "
                + "imprime CORT al arrancar con --lan. Se guarda y no se vuelve a pedir.",
                15f, Paleta.CLARO);
        ayuda.setLineSpacing(0f, 1.25f);
        LinearLayout.LayoutParams cuerpo = new LinearLayout.LayoutParams(-1, -2);
        cuerpo.topMargin = dp(26);
        pantalla.addView(ayuda, cuerpo);

        final EditText campo = new EditText(this);
        campo.setHint("http://192.168.100.xxx:8780/?token=…");
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
            // Amable con quien escribe la IP a mano: `192.168.x.x:8780` no es un
            // enlace, pero se adivina.
            pegado = "http://" + pegado;
        }
        if (!pegado.contains("token=")) {
            marcar("Falta la llave: copia el enlace ENTERO, el que termina en ?token=…");
            return;
        }
        prefs().edit().putString("url", pegado).putString("token", "").apply();
        esconderTeclado();
        abrir(pegado, "");
    }

    private void marcar(String motivo) {
        if (aviso != null) {
            aviso.setText(motivo);
            aviso.setVisibility(View.VISIBLE);
        }
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
        super.onDestroy();
    }
}
