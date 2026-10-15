package dev.sandra.cort;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.text.InputType;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;

/**
 * La ventana de CORT en el teléfono. Escrito contra el SDK puro —sin AndroidX,
 * sin Gradle, sin Capacitor— porque cada dependencia es una descarga que el
 * pipeline tiene que traer y este proyecto no reparte sorpresas: `compilar.sh`
 * usa sólo `aapt2`, `javac` y `d8`, que vienen con las herramientas que el
 * runner de GitHub Actions ya tiene instaladas.
 *
 * El asistente NO vive aquí. Vive en el portátil (`cort.py --lan`), y lo que se
 * ve es la misma página React servida en `http://IP:8780`, abierta con el token
 * de la red como consulta — el mismo enlace que imprime el lanzador al arrancar.
 * Este archivo decide dos cosas y nada más: qué dirección abrir y con qué
 * permisos del teléfono responde el WebView.
 */
public class MainActivity extends Activity {
    private WebView web;
    private LinearLayout capa;   // root: el setup o el WebView, nunca los dos

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        capa = new LinearLayout(this);
        capa.setOrientation(LinearLayout.VERTICAL);
        setContentView(capa);
        mostrarOSetup();
    }

    private SharedPreferences prefs() {
        return getSharedPreferences("cort", MODE_PRIVATE);
    }

    /**
     * La primera vez se pregunta la dirección; después se abre en silencio.
     * Se guarda en SharedPreferences y no en memoria: cerrar la app en el
     * Android es matar el proceso, y volver a escribir una IP cada mañana
     * sería justo la fricción que este APK existe para quitar.
     */
    private void mostrarOSetup() {
        String url = prefs().getString("url", "");
        if (url.isEmpty()) {
            pantallaDeConfiguracion("");
        } else {
            abrir(url, prefs().getString("token", ""));
        }
    }

    private void pantallaDeConfiguracion(final String previo) {
        capa.removeAllViews();
        web = null;
        EditText campoUrl = new EditText(this);
        campoUrl.setHint("http://192.168.100.xxx:8780");
        campoUrl.setInputType(InputType.TYPE_TEXT_VARIATION_URI);
        if (!previo.isEmpty()) {
            campoUrl.setText(previo);
        }
        EditText campoLlave = new EditText(this);
        campoLlave.setHint("llave (la del token en el arranque)");
        campoLlave.setInputType(InputType.TYPE_CLASS_TEXT);
        Button entrar = new Button(this);
        entrar.setText("Abrir CORT");
        entrar.setOnClickListener(v -> {
            String url = campoUrl.getText().toString().trim();
            String token = campoLlave.getText().toString().trim();
            if (url.isEmpty()) {
                campoUrl.setError("pega la dirección que imprime cort.py --lan");
                return;
            }
            prefs().edit().putString("url", url).putString("token", token).apply();
            esconderTeclado();
            abrir(url, token);
        });
        LinearLayout.LayoutParams relleno =
                new LinearLayout.LayoutParams(-1, -2, 1f);
        capa.addView(campoUrl, relleno);
        capa.addView(campoLlave, relleno);
        capa.addView(entrar, relleno);
    }

    /**
     * El enlace que abre la ventana. Si la dirección ya trae `?token=` —porque
     * la usuaria copió el enlace completo del lanzador— se respeta tal cual:
     * parsearla y reconstruirla sería una forma de romper un secreto.
     */
    private void abrir(String base, String token) {
        String destino = base;
        if (!token.isEmpty() && !base.contains("token=")) {
            destino = base + (base.contains("?") ? "&" : "/?") + "token=" + token;
        }
        web = new WebView(this);
        capa.removeAllViews();
        capa.addView(web, new LinearLayout.LayoutParams(-1, -1));
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        // `speechSynthesis` y el `<video>` de los gestos son «reproducción» a
        // ojos del WebView: sin esta línea CORT quedaría muda hasta que alguien
        // toque la pantalla, y un asistente que hay que tocar para que hable no
        // es un asistente.
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);       // la página viene de la red, no del disco
        s.setAllowContentAccess(false);
        web.setWebViewClient(new WebViewClient());
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest request) {
                // Los gestos de cámara (`defocus.ts`) y el micrófono por
                // `getUserMedia` piden aquí. Se concede lo que la página solicita,
                // dentro de lo que el manifest declaró; negar todo convertiría
                // el APK en un navegador sin manos.
                request.grant(request.getResources());
            }
        });
        web.loadUrl(destino);
        // Mantener vivo el hilo del JS con la pantalla encendida es el Android
        // decidiendo, no nosotros: al apagarla, la página se congela y el core
        // sigue corriendo en el portátil — que es exactamente el reparto.
    }

    private void esconderTeclado() {
        View foco = getCurrentFocus();
        if (foco != null) {
            InputMethodManager imm = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);
            imm.hideSoftInputFromWindow(foco.getWindowToken(), 0);
        }
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
            return;
        }
        // Sin WebView histórico, el botón «atrás» **no sale a la calle a la
        // primera**: abre el cambio de dirección. En un teléfono con una sola
        // pantalla, salir sin querer significa perder a CORT de vista hasta
        // volver a deslizar el dedo por el lanzador.
        cambioDeDireccion();
    }

    /** El gesto para reconfigurar sin reinstalar: mantener pulsado. */
    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus && web != null) {
            web.setOnLongClickListener(v -> {
                cambioDeDireccion();
                return true;
            });
        }
    }

    private void cambioDeDireccion() {
        new AlertDialog.Builder(this)
                .setTitle("Dirección de CORT")
                .setMessage(prefs().getString("url", "") + "\n" + prefs().getString("token", ""))
                .setPositiveButton("Cambiar", (d, w) -> pantallaDeConfiguracion(prefs().getString("url", "")))
                .setNegativeButton("Salir", (d, w) -> finish())
                .show();
    }
}
