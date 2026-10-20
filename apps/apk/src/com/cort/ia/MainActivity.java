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
 *
 * Sin Gradle ni AndroidX: se compila con `aapt2` + `javac` + `d8` en GitHub
 * Actions, porque el portátil de la dueña (1,8 GiB) no levanta un `gradle build`.
 */
public class MainActivity extends Activity {

    /** La bandera que mandan `Sesion.java` y `Reconocimiento.java` al invocar a CORT. */
    public static final String PIDE_ESCUCHAR = "cort.escuchar";

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

    /* ───────────────────────────── arranque ───────────────────────────── */

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        puente = new CortNative(this);

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
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
                peticion.grant(peticion.getResources());
            }
        });

        Button rincon = new Button(this);
        rincon.setText("CORT · PC");
        rincon.setAlpha(0.55f);
        rincon.setTextSize(12f);
        rincon.setOnClickListener(v -> menu());
        FrameLayout.LayoutParams botas = new FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        botas.bottomMargin = dp(14);
        botas.leftMargin = dp(10);
        botas.gravity = android.view.Gravity.BOTTOM | android.view.Gravity.START;

        FrameLayout cara = new FrameLayout(this);
        cara.addView(web, new FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        cara.addView(rincon, botas);
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

        pidePermiso("mic");
        abreLoQueToque(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        abreLoQueToque(intent);
    }

    /** El asistente y el doble toque llegan con `PIDE_ESCUCHAR`: escucha al abrir. */
    private void abreLoQueToque(Intent intent) {
        if (intent == null || !intent.getBooleanExtra(PIDE_ESCUCHAR, false)) return;
        // Un retardo corto: si se pide el micrófono antes de que la página exista,
        // la interfaz aún no tiene `window.__cortNative` y el resultado se pierde.
        web.postDelayed(() -> { puente.escuchaAhora(); hideTeclado(); }, 900);
        intent.removeExtra(PIDE_ESCUCHAR);
    }

    @Override
    protected void onResume() {
        super.onResume();
        direccionPC = prefs().getString("pc", "");
        if (web.getUrl() == null) arranca();
        if (mandos != null) mandos.setActive(true);
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (mandos != null) mandos.setActive(false);   // la música vuelve a su dono
        if (puente != null) puente.pausa();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (mandos != null) { mandos.setActive(false); mandos.release(); mandos = null; }
        if (puente != null) puente.destruye();
        if (web != null) web.destroy();
    }

    private void arranca() {
        String guardada = prefs().getString("pc", "");
        cayoUnaSolaVez = false;
        web.loadUrl(guardada.trim().isEmpty() ? INDICE : aseguraSlash(guardada.trim()));
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
                        puente.escuchaAhora();
                    });
                    return true;      // el segundo toque es de CORT
                }
                ultimoToque = ahora;
                return false;          // el primero sigue siendo de la música
            }
        };
    }

    /** `EXTRA_KEY_EVENT` es un `Parcelable`; se recoge con cuidado por si viene otro tipo. */
    private static KeyEvent teclaDe(Intent evento) {
        try {
            Object dentro = evento.getParcelableExtra(Intent.EXTRA_KEY_EVENT);
            return dentro instanceof KeyEvent ? (KeyEvent) dentro : null;
        } catch (Exception noEsTecla) {
            return null;
        }
    }

    /* ─────────────────────────── el menú del botón ─────────────────────── */

    private void menu() {
        String[] opciones = {
            "Conectar con mi PC por Wi‑Fi",
            "Cara dentro del teléfono (sin PC)",
            "Poner CORT como asistente",
            "Escuchar una orden ahora",
            "Recargar la cara",
        };
        new AlertDialog.Builder(this)
            .setTitle("CORT")
            .setItems(opciones, (dialogo, cual) -> {
                switch (cual) {
                    case 0: pideDireccion(); break;
                    case 1: guardarPC(""); break;
                    case 2: abreAjustesDeAsistente(); break;
                    case 3: puente.escuchaAhora(); break;
                    default: arranca(); break;
                }
            })
            .show();
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

    /** Guarda (o borra con cadena vacía) la dirección del PC y recarga la cara. */
    void guardarPC(String url) {
        String limpia = url == null ? "" : url.trim();
        prefs().edit().putString("pc", limpia).apply();
        direccionPC = limpia;
        hideTeclado();
        arranca();
    }

    void abreAjustesDeAsistente() {
        // Android no tiene una sola pantalla para esto y el nombre cambia entre
        // marcas: se prueban las dos rutas públicas y, si ninguna existe, se dice
        // el camino a mano en vez de quedarse con un botón que no hizo nada.
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

    private static String aseguraSlash(String url) {
        return url.endsWith("/") ? url : url + "/";
    }

    /* ─────────────────────────── permisos y ayuda ──────────────────────── */

    void pidePermiso(String kind) {
        String permiso = "camara".equalsIgnoreCase(kind) || "camera".equalsIgnoreCase(kind)
            ? android.Manifest.permission.CAMERA
            : android.Manifest.permission.RECORD_AUDIO;
        if (checkSelfPermission(permiso) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            try {
                requestPermissions(new String[] { permiso }, 7);
            } catch (Exception elTelefonoNoPregunta) { /* la interfaz avisa sola */ }
        }
    }

    @Override
    public void onRequestPermissionsResult(int codigo, String[] permisos, int[] resultados) {
        super.onRequestPermissionsResult(codigo, permisos, resultados);
        boolean concedido = resultados.length > 0 && resultados[0]
            == android.content.pm.PackageManager.PERMISSION_GRANTED;
        String kind = (permisos.length > 0 && permisos[0].endsWith("CAMERA")) ? "camara" : "mic";
        puente.permisoRespondido(kind, concedido);
    }

    void avisa(String texto) {
        runOnUiThread(() -> Toast.makeText(this, texto, Toast.LENGTH_LONG).show());
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
