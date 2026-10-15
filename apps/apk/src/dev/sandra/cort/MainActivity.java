package dev.sandra.cort;

import android.animation.ValueAnimator;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.animation.LinearInterpolator;
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

/**
 * La ventana de CORT en el teléfono. Escrito contra el SDK puro —sin AndroidX,
 * sin Gradle, sin Capacitor— porque cada dependencia es una descarga que el
 * pipeline tiene que traer y este proyecto no reparte sorpresas: `compilar.sh`
 * usa sólo `aapt2`, `javac` y `d8`, que vienen con las herramientas que el
 * runner de GitHub Actions ya tiene instaladas.
 *
 * El asistente NO vive aquí. Vive en el portátil (`cort.py --lan`), y lo que se
 * ve es la misma página React servida en `http://IP:8780`, abierta con la llave
 * de la red como consulta — el mismo enlace que imprime el lanzador al arrancar.
 * Este archivo decide dos cosas y nada más: qué dirección abrir y con qué
 * permisos del teléfono responde el WebView.
 *
 * La pantalla de estreno (2026-10-15) dejó de ser el formulario gris de Android:
 * es oscura como la cara del asistente, tiene su anillo girando y pide **un**
 * campo — el enlace completo del arranque, con su `?token=` incluido. Se hizo
 * uno y no dos porque la llave ya no la pide esta app ni la escribe la dueña:
 * la inventa el lanzador y la guarda en su `.env`. Lo que quedaba de fricción
 * estaba aquí dentro, y era de tamaño teclado.
 */
public class MainActivity extends Activity {
    /* Los mismos literales de `scripts/marca.py`, que son los de
       `apps/web/src/cort/palette.ts`. Nada de imágenes: el anillo se dibuja con
       `Canvas` y el fondo es un entero, así que esta pantalla no puede
       desentonar con la PWA ni costarle un kilobyte al APK. */
    private static final int FONDO = 0xFF02040C;      // --bg
    private static final int CIAN = 0xFF5CE1FF;       // --tint
    private static final int VIOLETA = 0xFF8F5CFF;    // night.core
    private static final int CLARO = 0xFFDFFBFF;      // work.hot
    private static final int SUAVE = 0x8ADFFBFF;      // el mismo blanco al 54 %
    private static final int AVISO = 0xFFFFC46B;      // el ámbar del subtítulo
    private static final int CAMPO = 0xFF0A1620;      // el vidrio de las ventanas

    private WebView web;
    private LinearLayout capa;    // root: el setup o el WebView, nunca los dos
    private TextView aviso;       // el motivo por el que el enlace no vale

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().getDecorView().setBackgroundColor(FONDO);
        // Con el teclado abierto, la pantalla de estreno se recoloca en vez de
        // quedar tapada: el campo del enlace está en el centro y el botón debajo.
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        capa = new LinearLayout(this);
        capa.setOrientation(LinearLayout.VERTICAL);
        capa.setBackgroundColor(FONDO);
        setContentView(capa);
        mostrarOSetup();
    }

    private SharedPreferences prefs() {
        return getSharedPreferences("cort", MODE_PRIVATE);
    }

    /**
     * La primera vez se pregunta el enlace; después se abre en silencio. Se
     * guarda en SharedPreferences y no en memoria: cerrar la app en Android es
     * matar el proceso, y volver a escribir una IP cada mañana sería justo la
     * fricción que este APK existe para quitar.
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
        ScrollView desplazable = new ScrollView(this);
        LinearLayout pantalla = new LinearLayout(this);
        pantalla.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(24);
        pantalla.setPadding(pad, pad, pad, pad);
        desplazable.addView(pantalla, new LinearLayout.LayoutParams(-1, -2));
        capa.addView(desplazable, new LinearLayout.LayoutParams(-1, -1));

        Anillo anillo = new Anillo(this);
        LinearLayout.LayoutParams marca = new LinearLayout.LayoutParams(dp(150), dp(150));
        marca.topMargin = dp(26);
        marca.gravity = Gravity.CENTER_HORIZONTAL;
        pantalla.addView(anillo, marca);

        TextView titulo = texto("CORT", 40f, CIAN);
        titulo.setTypeface(Typeface.create("sans-serif-light", Typeface.BOLD));
        titulo.setLetterSpacing(0.16f);
        pantalla.addView(titulo, centrado(-2));

        TextView sumario = texto("LA VENTANA A TU PORTÁTIL", 12f, SUAVE);
        sumario.setLetterSpacing(0.32f);
        pantalla.addView(sumario, centrado(-2));

        TextView ayuda = texto("Pega el enlace que CORT imprime al arrancar: empieza en "
                + "http://192.168… y lleva su ?token= al final. Se guarda en el teléfono "
                + "y no se vuelve a pedir.", 15f, CLARO);
        ayuda.setLineSpacing(0f, 1.25f);
        LinearLayout.LayoutParams cuerpo = new LinearLayout.LayoutParams(-1, -2);
        cuerpo.topMargin = dp(34);
        pantalla.addView(ayuda, cuerpo);

        final EditText campo = new EditText(this);
        campo.setHint("http://192.168.100.xxx:8780/?token=…");
        campo.setInputType(InputType.TYPE_TEXT_VARIATION_URI
                | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        campo.setSingleLine(true);
        campo.setTextColor(CLARO);
        campo.setHintTextColor(SUAVE);
        campo.setBackgroundColor(CAMPO);
        campo.setTextSize(15f);
        campo.setPadding(dp(14), dp(16), dp(14), dp(16));
        if (!previo.isEmpty()) {
            campo.setText(previo);
        }
        LinearLayout.LayoutParams caja = new LinearLayout.LayoutParams(-1, -2);
        caja.topMargin = dp(18);
        pantalla.addView(campo, caja);

        aviso = texto("", 13f, AVISO);
        aviso.setVisibility(View.INVISIBLE);
        pantalla.addView(aviso, centrado(-2));

        Button entrar = new Button(this);
        entrar.setText("Abrir CORT");
        entrar.setTextColor(CIAN);
        entrar.setBackgroundColor(0xFF0F2B3A);
        entrar.setTextSize(17f);
        entrar.setLetterSpacing(0.06f);
        LinearLayout.LayoutParams boton = new LinearLayout.LayoutParams(-1, dp(54));
        boton.topMargin = dp(14);
        pantalla.addView(entrar, boton);

        TextView pie = texto("¿No lo tienes? En el portátil:  python scripts/cort.py --lan\n"
                + "El enlace sale en la línea «red» del arranque, con su llave.", 12f, SUAVE);
        pie.setLineSpacing(0f, 1.3f);
        LinearLayout.LayoutParams piecaja = new LinearLayout.LayoutParams(-1, -2);
        piecaja.topMargin = dp(26);
        pantalla.addView(pie, piecaja);

        entrar.setOnClickListener(v -> intentar(campo));
        // `Enter`/«Ir» del teclado hace lo mismo que el botón: con las manos
        // ocupadas, el enlace se pega y se entra sin buscar el botón a ciegas.
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
            // enlace, pero se adivina, y obligar a escribir el protocolo es
            // otrafricción que este APK no necesita.
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
        aviso.setText(motivo);
        aviso.setVisibility(View.VISIBLE);
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

    /**
     * El enlace que abre la ventana. Si ya trae `?token=` —porque la usuaria copió
     * el enlace completo del lanzador— se respeta tal cual: parsearlo y
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
        // blanco antes de que la página arranque, y el «enciende y ya está» se
        // convierte en un destello de navegador.
        web.setBackgroundColor(FONDO);
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
        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedError(WebView vista, WebResourceRequest peticion,
                                        WebResourceError error) {
                if (!peticion.isForMainFrame()) {
                    return;   // un icono que falta no es CORT caído
                }
                // El caso normal no es un fallo raro: el portátil está apagado o
                // su IP cambió. Android lo diría en inglés y en blanco; se dice
                // aquí, y se ofrece el único arreglo que existe.
                avisar("No se ve a CORT en " + recortar(destino));
                cambioDeDireccion();
            }
        });
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
        final String guardada = prefs().getString("url", "");
        new AlertDialog.Builder(this)
                .setTitle("Dirección de CORT")
                .setMessage(guardada.isEmpty() ? "Aún no hay ninguna guardada." : recortar(guardada))
                .setPositiveButton("Cambiar", (d, w) -> pantallaDeConfiguracion(guardada))
                .setNegativeButton("Salir", (d, w) -> finish())
                .show();
    }

    /**
     * El anillo de la marca, dibujado con `Canvas`: la misma geometría de
     * `scripts/marca.py` (banda cian de radio 0,68 del semitamaño, halo violeta
     * por dentro y núcleo caliente en el centro) girando despacio. Gira porque
     * una pantalla de arranque quieta es un formulario, y CORT se presenta.
     */
    private static class Anillo extends View {
        private final Paint pincel = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF aro = new RectF();
        private float angulo;
        private ValueAnimator giro;

        Anillo(Context contexto) {
            super(contexto);
            setBackgroundColor(FONDO);
            giro = ValueAnimator.ofFloat(0f, 360f);
            giro.setDuration(4200L);
            giro.setRepeatCount(ValueAnimator.INFINITE);
            giro.setInterpolator(new LinearInterpolator());
            giro.addUpdateListener(animacion -> {
                angulo = (float) animacion.getAnimatedValue();
                invalidate();
            });
            giro.start();
        }

        @Override
        protected void onDetachedFromWindow() {
            super.onDetachedFromWindow();
            if (giro != null) {
                giro.cancel();   // irse a la ventana sin soltar el hilo de animación
            }
        }

        @Override
        protected void onDraw(Canvas lienzo) {
            float cx = getWidth() / 2f;
            float cy = getHeight() / 2f;
            float mitad = Math.min(cx, cy);
            float radio = mitad * 0.68f;
            aro.set(cx - radio, cy - radio, cx + radio, cy + radio);
            pincel.setStyle(Paint.Style.STROKE);
            // Halo violeta: más grueso, más suave y por dentro de la banda, como
            // en el PNG. Alpha fijo porque aquí no hay que sumar exposición, hay
            // que dar profundidad con dos trazos.
            pincel.setColor(VIOLETA);
            pincel.setAlpha(90);
            pincel.setStrokeWidth(mitad * 0.11f);
            lienzo.drawArc(aro, angulo + 150f, 210f, false, pincel);
            // Banda cian: el trazo fino, con un tercio del aro abierto para que
            // el giro se vea.
            pincel.setAlpha(255);
            pincel.setStrokeWidth(mitad * 0.035f);
            lienzo.drawArc(aro, angulo, 240f, false, pincel);
            // Núcleo caliente.
            pincel.setColor(CLARO);
            pincel.setStyle(Paint.Style.FILL);
            lienzo.drawCircle(cx, cy, mitad * 0.07f, pincel);
        }
    }
}
