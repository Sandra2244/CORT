package dev.sandra.cort.movil;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * CORT en el teléfono: una ventana sobre el puente de la casa.
 *
 * No hay nube. La aplicación abre la misma interfaz que corre en el PC
 * (http://IP:8766) y por eso todo lo que CORT sabe, puede y guarda sigue
 * estando en el equipo de Sandra. Lo único que hace aquí el teléfono es:
 * enseñar la interfaz, pedir el micrófono y mandar lo que se dijo.
 *
 * El micrófono se graba en el teléfono y se sube en WAV al puente, que lo
 * transccribe con Vosk. Se hace así y no con getUserMedia porque el puente
 * va por http en la red local: un origen no seguro no tiene acceso al micro
 * desde el navegador, aunque el permiso de la aplicación exista.
 */
public class MainActivity extends Activity {

    private static final String PREFS = "cort";
    private static final String CLAVE_URL = "url_puente";
    private static final int MUESTREO = 16000;
    private static final int MAX_SEGUNDOS = 20;

    private WebView web;
    private LinearLayout panelConfig;
    private EditText campoUrl;
    private Button botonMic;
    private TextView estado;
    private String urlPuente = "";

    private volatile boolean grabando = false;
    private Thread hiloGrabacion;

    @Override
    protected void onCreate(Bundle guardado) {
        super.onCreate(guardado);

        SharedPreferences p = getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        urlPuente = p.getString(CLAVE_URL, "");

        FrameLayout raiz = new FrameLayout(this);
        raiz.setBackgroundColor(0xFF04121C);

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        web.setBackgroundColor(0xFF04121C);

        web.setWebViewClient(new WebViewClient());
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest solicitud) {
                // Sólo el micro. Si la página pidiera cámara o cualquier otra
                // cosa, se niega y se dice en la raya de estado.
                String[] pidos = solicitud.getResources();
                boolean soloMicro = pidos.length > 0;
                for (String q : pidos) {
                    if (!q.equals(PermissionRequest.RESOURCE_AUDIO_CAPTURE)) soloMicro = false;
                }
                if (soloMicro) {
                    solicitud.grant(pidos);
                } else {
                    solicitud.deny();
                    muestra("la página pidió algo más que el micrófono y se lo negué");
                }
            }
        });
        raiz.addView(web, new FrameLayout.LayoutParams(-1, -1));

        panelConfig = panelDeConfiguracion();
        raiz.addView(panelConfig, new FrameLayout.LayoutParams(-1, -2, Gravity.TOP));

        estado = new TextView(this);
        estado.setTextColor(0xFF9FE8FF);
        estado.setTextSize(12f);
        estado.setBackgroundColor(0xB004121C);
        estado.setPadding(18, 8, 18, 8);
        estado.setVisibility(View.GONE);
        FrameLayout.LayoutParams le = new FrameLayout.LayoutParams(-1, -2, Gravity.BOTTOM);
        raiz.addView(estado, le);

        botonMic = new Button(this);
        botonMic.setText("● hablar");
        botonMic.setTextColor(0xFF04121C);
        botonMic.setBackgroundColor(0xFF37E0C8);
        botonMic.setOnClickListener(v -> alternaGrabacion());
        FrameLayout.LayoutParams mb = new FrameLayout.LayoutParams(-2, -2, Gravity.TOP | Gravity.END);
        mb.topMargin = 12;
        mb.rightMargin = 12;
        raiz.addView(botonMic, mb);

        setContentView(raiz);

        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[] {Manifest.permission.RECORD_AUDIO}, 7);
        }

        if (urlPuente.isEmpty()) {
            abreConfiguracion("abre el puente en la PC y copia la dirección que imprime");
        } else {
            web.loadUrl(urlPuente);
        }
    }

    private LinearLayout panelDeConfiguracion() {
        LinearLayout caja = new LinearLayout(this);
        caja.setOrientation(LinearLayout.VERTICAL);
        caja.setBackgroundColor(0xF0031018);
        caja.setPadding(24, 32, 24, 24);

        TextView titulo = new TextView(this);
        titulo.setText("¿dónde está CORT?");
        titulo.setTextColor(0xFF37E0C8);
        titulo.setTextSize(18f);
        caja.addView(titulo);

        TextView ayuda = new TextView(this);
        ayuda.setTextSize(12f);
        ayuda.setTextColor(0xFFBFD9E6);
        caja.addView(ayuda);
        this.ayuda = ayuda;

        campoUrl = new EditText(this);
        campoUrl.setHint("http://192.168.1.20:8766/index.html");
        campoUrl.setTextColor(0xFFFFFFFF);
        campoUrl.setHintTextColor(0xFF6C8B99);
        campoUrl.setTextSize(14f);
        caja.addView(campoUrl);

        Button entrar = new Button(this);
        entrar.setText("entrar");
        entrar.setOnClickListener(v -> guardaYAbre());
        caja.addView(entrar);

        caja.setVisibility(View.GONE);
        return caja;
    }

    private TextView ayuda;

    private void abreConfiguracion(String porque) {
        ayuda.setText("El puente tiene que escuchar en la red local.\nEn la PC:\n"
                + "  CORT_BIND=0.0.0.0 python3 cort-bridge/cort_server.py\n\n"
                + "y copias la dirección que imprime con la IP del equipo.\n"
                + "Lo que pasa ahora: " + porque);
        campoUrl.setText(urlPuente);
        panelConfig.setVisibility(View.VISIBLE);
        web.setVisibility(View.GONE);
    }

    private void guardaYAbre() {
        String url = campoUrl.getText().toString().trim();
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            ayuda.setText("Eso no parece una dirección. Tiene que empezar por http:// y llevar el puerto, por ejemplo http://192.168.1.20:8766/index.html");
            return;
        }
        if (!url.contains(":8766") && !url.contains(":8767")) {
            ayuda.setText("Ojo: la interfaz web del puente escucha en el puerto 8766. "
                    + "Si tu dirección usa otro, pruébalo igual, pero el puente abre 8766 por defecto.");
        }
        urlPuente = url;
        getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(CLAVE_URL, url).apply();
        panelConfig.setVisibility(View.GONE);
        web.setVisibility(View.VISIBLE);
        web.loadUrl(urlPuente);
    }

    // ---- hablar por el micrófono del teléfono --------------------------------

    private void alternaGrabacion() {
        if (grabando) {
            grabando = false;
            botonMic.setText("● hablar");
            return;
        }
        if (!tieneMicro()) return;
        if (urlPuente.isEmpty()) {
            abreConfiguracion("todavía no me dijiste dónde está el puente");
            return;
        }
        grabando = true;
        botonMic.setText("■ detener");
        muestra("grabando… pulsa detener cuando termines");
        hiloGrabacion = new Thread(this::grabaYSube, "cort-mic");
        hiloGrabacion.start();
    }

    private boolean tieneMicro() {
        return getPackageManager().hasSystemFeature("android.hardware.microphone");
    }

    private void grabaYSube() {
        int min = AudioRecord.getMinBufferSize(MUESTREO,
                AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT);
        if (min <= 0) {
            enHiloPrincipal("el micrófono de este teléfono no da 16 kHz mono; CORT no pudo grabar");
            return;
        }
        AudioRecord ar = null;
        try {
            ar = new AudioRecord(MediaRecorder.AudioSource.MIC, MUESTREO,
                    AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, min * 4);
            ByteArrayOutputStream cruda = new ByteArrayOutputStream();
            byte[] b = new byte[min];
            ar.startRecording();
            long t0 = System.currentTimeMillis();
            while (grabando && (System.currentTimeMillis() - t0) < MAX_SEGUNDOS * 1000L) {
                int n = ar.read(b, 0, b.length);
                if (n > 0) cruda.write(b, 0, n);
            }
            boolean cortada = (System.currentTimeMillis() - t0) >= MAX_SEGUNDOS * 1000L;
            grabando = false;
            ar.stop();
            byte[] muestras = cruda.toByteArray();
            if (muestras.length < MUESTREO / 5) {
                enHiloPrincipal("no se oyó nada (" + (muestras.length / 32000.0) + " s de audio)");
                return;
            }
            byte[] wav = cabeceroWav(muestras, MUESTREO);
            enHiloPrincipal(cortada
                    ? "corté a los " + MAX_SEGUNDOS + " s; subo lo grabado"
                    : "subiendo " + (muestras.length / 32000.0) + " s al puente…");
            String respuesta = sube(wav);
            JSONObject j = new JSONObject(respuesta);
            if (j.optBoolean("ok", false)) {
                String texto = j.optString("texto", "").trim();
                if (texto.isEmpty()) {
                    enHiloPrincipal("el puente oyó audio pero no sacó palabras");
                    return;
                }
                enHiloPrincipal("dijiste: " + texto);
                // La misma ruta que la caja de texto de la interfaz: el puente
                // decide con sus reglas o con el modelo y responde por el WebSocket.
                // El payload se arma con JSONObject y no con comillas a mano, para
                // que las comillas o saltos de la transcripción no rompan el JS.
                JSONObject envio = new JSONObject();
                envio.put("type", "user_input");
                envio.put("text", texto);
                final String js = "window.CORT_enviarAlCerebro && window.CORT_enviarAlCerebro("
                        + envio.toString() + ")";
                runOnUiThread(() -> web.evaluateJavascript(js, null));
            } else {
                enHiloPrincipal("el puente no pudo transcribir: " + j.optString("motivo", "sin motivo"));
            }
        } catch (Exception e) {
            enHiloPrincipal("falló el micrófono o la subida (" + e.getClass().getSimpleName() + ")");
        } finally {
            if (ar != null) {
                try { ar.release(); } catch (Exception ignorado) { }
            }
            runOnUiThread(() -> botonMic.setText("● hablar"));
        }
    }

    /** WAV PCM 16 bits mono: el formato que lee vosk.KaldiRecognizer sin dependencias. */
    private static byte[] cabeceroWav(byte[] datos, int tasa) {
        int largo = datos.length;
        byte[] w = new byte[44 + largo];
        copia(w, 0, new byte[] {'R', 'I', 'F', 'F'});
        entero(w, 4, 36 + largo);
        copia(w, 8, new byte[] {'W', 'A', 'V', 'E', 'f', 'm', 't', ' '});
        entero(w, 16, 16);
        entero(w, 20, (1 << 16) | 1);                    // PCM, un canal
        entero(w, 24, tasa);
        entero(w, 28, tasa * 2);                          // bytes por segundo
        entero(w, 32, 16);                                // 16 bits por muestra
        copia(w, 36, new byte[] {'d', 'a', 't', 'a'});
        entero(w, 40, largo);
        System.arraycopy(datos, 0, w, 44, largo);
        return w;
    }

    private static void copia(byte[] destino, int donde, byte[] de) {
        System.arraycopy(de, 0, destino, donde, de.length);
    }

    private static void entero(byte[] d, int donde, int v) {
        d[donde] = (byte) (v & 0xff);
        d[donde + 1] = (byte) ((v >> 8) & 0xff);
        d[donde + 2] = (byte) ((v >> 16) & 0xff);
        d[donde + 3] = (byte) ((v >> 24) & 0xff);
    }

    private String sube(byte[] wav) throws Exception {
        URL base = new URL(urlPuente);
        URL destino = new URL(base.getProtocol(), base.getHost(), base.getPort(), "/mic");
        HttpURLConnection c = (HttpURLConnection) destino.openConnection();
        c.setRequestMethod("POST");
        c.setDoOutput(true);
        c.setConnectTimeout(8000);
        c.setReadTimeout(30000);
        c.setRequestProperty("Content-Type", "audio/wav");
        c.setFixedLengthStreamingMode(wav.length);
        try (OutputStream salida = c.getOutputStream()) {
            salida.write(wav);
        }
        int code = c.getResponseCode();
        InputStream fuente = code >= 400 ? c.getErrorStream() : c.getInputStream();
        ByteArrayOutputStream dentro = new ByteArrayOutputStream();
        if (fuente != null) {
            byte[] b = new byte[4096];
            int n;
            while ((n = fuente.read(b)) > 0) dentro.write(b, 0, n);
            fuente.close();
        }
        String cuerpo = dentro.toString("UTF-8");
        if (code >= 400) {
            throw new Exception("el puente respondió " + code + ": " + cuerpo);
        }
        return cuerpo;
    }

    private void enHiloPrincipal(String texto) {
        runOnUiThread(() -> muestra(texto));
    }

    private void muestra(String texto) {
        estado.setText(texto);
        estado.setVisibility(View.VISIBLE);
        estado.postDelayed(() -> estado.setVisibility(View.GONE), 9000);
    }

    @Override
    public void onBackPressed() {
        if (panelConfig.getVisibility() == View.VISIBLE && !urlPuente.isEmpty()) {
            panelConfig.setVisibility(View.GONE);
            web.setVisibility(View.VISIBLE);
            return;
        }
        if (web.canGoBack()) web.goBack(); else super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        grabando = false;
        super.onDestroy();
        if (web != null) web.destroy();
    }
}
