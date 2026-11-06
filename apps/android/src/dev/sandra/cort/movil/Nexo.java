package dev.sandra.cort.movil;

import android.app.Activity;
import android.app.ActivityManager;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.hardware.camera2.CameraManager;
import android.media.AudioManager;
import android.net.Uri;
import android.os.BatteryManager;
import android.os.Build;
import android.os.StatFs;
import android.provider.Settings;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.LinearLayout;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * La cara del portátil dentro del teléfono, y el puente que la atiende.
 *
 * La dueña lo pidió sin margen: «necesito que sea la copia exacta de la versión de
 * PC incluyendo sus funciones». Desde `cort-v0.17.0` el APK lleva en `assets/web/`
 * los **mismos archivos** que sirve `cort.py --lan` en el portátil —el `dist` de
 * Vite, el orbe de three.js, `cort-ui.js` con sus 2560 líneas de paneles— y esta
 * clase hace las dos mitades que faltaban:
 *
 * 1. **Servirlos** desde el propio teléfono, sin servidor y sin red: el origen
 *    `http://cort.local` no se resuelve, cada petición se corta en
 *    `shouldInterceptRequest` y sale de `getAssets()` con la lista cerrada de
 *    `rutaDe`.
 * 2. **Contestar el protocolo** que esa página habla por `ws://<host>:8765/ws`.
 *    `web/cort-android.js` (viajado como `assets/web/cort-android.js`) sustituye
 *    `window.WebSocket` antes de que cargue `cort-mock.js`; desde entonces cada
 *    orden llega aquí por `CortNative.recibir(json)` y cada respuesta sale por
 *    `window.__cortNative.emit(cuadro)`. Un solo transporte nuevo y los mismos
 *    cuadros: lo que el puente de Python medía en la PC, el teléfono lo mide con
 *    sus propias APIs —o contesta un `puente_aviso` con el motivo, que es la regla
 *    F1 de «que nada mienta» llevada al aparato.
 *
 * Por qué `http` y no `https`, medido en el bundle de la demo (`main-s6G6kMTO.js`):
 * la página calcula una bandera con `window.location.protocol === "https:"`, y con
 * esa bandera encendida **silencia `live_subtitles`** —el subtítulo animado que en
 * la PC se ve— y manda cada respuesta a `window.speechSynthesis` en `fr-FR`, o sea
 * CORT hablando dos veces y con la voz equivocada. Con origen `http` la página se
 * comporta igual que en el portátil: subtítulos vivos, y la voz la pone Java. El
 * coste real es que el WebView no da `getUserMedia` en origen no seguro; no
 * importa, porque en el teléfono el oído y la cámara son de Java (`Motor`,
 * `Escaner`), nunca de la página.
 *
 * La cara nativa de `Cara.java` sigue ahí como respaldo: si el `WebView` no
 * arranca o la cara no viajó en el compilado, la dueña ve CORT igualmente.
 */
public class Nexo {
    /** El origen inventado. No se resuelve: se intercepta. Ver el porqué arriba. */
    public static final String ORIGEN = "http://cort.local";
    public static final String INDICE = ORIGEN + "/index.html";

    /** La carpeta de la cara dentro de los `assets` del APK, y su nombre suelto. */
    static final String DOSSIER = "web";
    static final String CARPETA = DOSSIER + "/";

    /**
     * Lo que se sirve de la cara: estas raíces exactas y estas cuatro carpetas. La
     * lista es cerrada a propósito —regla 6 del repo aplicada a un archivo— y
     * `rutaDe` devuelve `null` con cualquier otra cosa, incluido un `..`.
     */
    static final String[] RAICES = {"index.html", "manifest.webmanifest", "favicon.ico",
            "cort-sw.js", "cort-android.js"};
    static final String[] PREFIJOS = {"cort/", "assets/", "iconos/", "wallpapers/"};

    /**
     * El puente Java se inyecta justo detrás de `<head>`, antes que cualquier
     * módulo de la cara, porque `cort-mock.js` hace `const WS_NATIVA =
     * window.WebSocket` en su primera línea: si llega tarde, la página guarda el
     * WebSocket de Chromium, intenta `ws://cort.local:8765/ws`, no hay nada
     * escuchando y la cara se queda en modo simulación.
     */
    static final String ETIQUETA_PUENTE = "<script src=\"/cort-android.js\"></script>";

    /** Donde se guardan lo que la página escribe en Ajustes y la lista de compras. */
    static final String PREFERENCIAS = "cort-cara";
    static final String CLAVE_COMPRAS = "compras";
    static final String CLAVE_CIUDAD = "ciudad";
    static final String CLAVE_RECORDATORIOS = "recordatorios";
    static final String CLAVE_HABLA = "habla";

    private final Activity actividad;
    private final Runnable seCayo;
    private final SharedPreferences prefs;
    private WebView web;
    private final Recuerdos recuerdos;
    private final Cerebro cerebro;
    private final Acciones acciones;
    private final Voz voz;
    private final Nube nube;
    /** El GGUF del teléfono (U1): contesta antes que la nube cuando cabe. */
    private final CerebroLocal cerebroLocal;

    private volatile boolean corriendo;
    private Thread estadistas;
    private long cpuTotalPrevio = -1L;
    private long cpuOcioPrevio = -1L;
    private long ultimoNivel;
    /** La última ciudad que la página guardó en Ajustes, para no preguntar la IP. */
    private volatile double lat, lon;
    private volatile Bajada bajada;
    private volatile boolean bajando;
    private boolean escuchaContinua;
    /** Si el micrófono está abierto AHORA, medido por quien lo abrió y lo cerró. */
    private volatile boolean escuchando;
    private boolean pantallaCompleta;

    public Nexo(Activity actividad, Runnable seCayo) {
        this.actividad = actividad;
        this.seCayo = seCayo;
        this.prefs = actividad.getSharedPreferences(PREFERENCIAS, Context.MODE_PRIVATE);
        this.recuerdos = new Recuerdos(actividad);
        this.cerebro = new Cerebro(actividad, recuerdos);
        this.acciones = new Acciones(actividad, recuerdos);
        this.voz = new Voz(actividad);
        this.nube = new Nube(actividad);
        this.cerebroLocal = new CerebroLocal(actividad.getApplicationContext());
        // Los datos del aparato, la primera vez, sin que nadie los teclee: la misma
        // siembra de `Cara.sembrar()`, para que el teléfono que abre esta cara sepa
        // ya quién es su dueña y en qué aparato está.
        recuerdos.sembrarDispositivo("teléfono",
                android.os.Build.MANUFACTURER + " " + android.os.Build.MODEL);
        recuerdos.sembrarDispositivo("android", "API " + android.os.Build.VERSION.SDK_INT);
    }

    /* ------------------------------------------------------------------ montar */

    public void montar(LinearLayout capa) {
        web = new WebView(actividad);
        // Oscuro desde el primer fotograma, como la ventana del portátil.
        web.setBackgroundColor(Paleta.FONDO);
        capa.removeAllViews();
        capa.addView(web, new LinearLayout.LayoutParams(-1, -1));
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        // `speechSynthesis` no habla en el teléfono (habla Java), pero el pitido de
        // «te oí» y cualquier `<audio>` de la cara sí son reproducción, y sin esta
        // línea Android la condiciona a un dedo encima.
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setCacheMode(WebSettings.LOAD_NO_CACHE);
        // `setAllowFileAccess` se queda en su defecto: **no** se abre el disco. Lo
        // que lee esta cara es `getAssets()`, por mano propia y con la lista
        // cerrada de `rutaDe`, que es más estrecho que el permiso de archivo.
        web.addJavascriptInterface(this, "CortNative");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView vista,
                                                              WebResourceRequest peticion) {
                String url = peticion.getUrl().toString();
                if (!esDeLaCara(url)) {
                    return null;   // no es nuestro origen: que lo resuelva Android
                }
                String ruta = rutaDe(url);
                if (ruta == null) {
                    return noExiste();
                }
                // La única costura del HTML: la cara no sabe que está en un teléfono
                // hasta que lee este puente, y tiene que leerlo antes que nada.
                if ("web/index.html".equals(ruta)) {
                    return sirveConPuente(ruta);
                }
                return sirve(ruta);
            }

            @Override
            public void onPageFinished(WebView vista, String url) {
                if (esDeLaCara(url)) {
                    arranque();
                }
            }

            @Override
            public void onReceivedError(WebView vista, WebResourceRequest peticion,
                                        WebResourceError error) {
                if (!peticion.isForMainFrame()) {
                    return;   // un icono que falta no es CORT caído
                }
                seCayo.run();
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(android.webkit.PermissionRequest pedido) {
                // Lo pide la página; en origen `http` Chromium no concede
                // `getUserMedia`, así que en la práctica este camino queda cerrado y
                // el oído del teléfono es el de Java. Se deja el gesto por si el
                // WebView de algún fabricante sí lo ofrece.
                pedido.grant(pedido.getResources());
            }
        });
        web.loadUrl(INDICE);
    }

    public void cerrar() {
        corriendo = false;
        if (estadistas != null) {
            estadistas.interrupt();
            estadistas = null;
        }
        if (bajada != null) {
            bajada.corta();
        }
        voz.dejarDeEscuchar();
        voz.cerrar();
        web = null;
    }

    /**
     * Lo que el puente de Python empuja nada más conectar y que la cara espera
     * sin pedirlo: `connected`, el estado del cerebro, el de la voz, el perfil del
     * equipo, la primera muestra de sistema y la iniciativa. Sin esto el HUD se
     * queda en «sin datos del puente todavía» hasta el primer clic.
     */
    private void arranque() {
        envia(cuadro("type", "connected", "origen", "real",
                "puente", "cort-puente-android v" + versionApp()));
        if (!corriendo) {
            corriendo = true;
            estadistas = new Thread(this::bombea, "cort-stats");
            estadistas.start();
        }
        envia(estadoCerebro());
        envia(vozEstado());
        envia(perfilReply());
        envia(iniciativa());
    }

    /** 3. Lo que CORT dice por su cuenta al conectar, con la medida delante. */
    private JSONObject iniciativa() {
        String nombre = recuerdos.valor("nombre");
        CerebroLocal.Ficha ficha = cerebroLocal.elegido();
        long libre = cerebroLocal.memoriaLibre();
        String nota = ficha != null
                ? "cerebro local en el teléfono: " + ficha.nombre + " · RAM libre " + libre + " MB"
                : "sin cerebro local cargado: pregunta y uso la tabla de CORT"
                        + (nube.configurada() ? " o la nube" : "")
                        + " · RAM libre " + libre + " MB";
        return cuadro("type", "iniciativa", "origen", "real",
                "saludo", nombre == null || nombre.isEmpty()
                        ? "CORT en tu teléfono, lista." : "CORT en tu teléfono, " + nombre + ".",
                "nota", nota,
                "memoria", recuerdos.cuentasDeHechos());
    }

    private String versionApp() {
        try {
            String v = actividad.getPackageManager()
                    .getPackageInfo(actividad.getPackageName(), 0).versionName;
            return v == null ? "?" : v;
        } catch (PackageManager.NameNotFoundException imposible) {
            return "?";
        }
    }

    /* ---------------------------------------------------------------- el puente */

    /**
     * La única puerta de entrada: la página manda un cuadro JSON y llega aquí en el
     * hilo del JS. Todo lo que mueva Android (`startActivity`, `TextToSpeech`) sube
     * a la interfaz; lo que bloquea (disco, red, un modelo GGUF) baja a un hilo.
     */
    @JavascriptInterface
    public void recibir(final String cuadro) {
        if (cuadro == null || cuadro.isEmpty()) {
            return;
        }
        final JSONObject pedido;
        try {
            pedido = new JSONObject(cuadro);
        } catch (JSONException noEsCuadro) {
            return;   // `cort-mock.js` ya avisa de lo no parseable; no se duplica
        }
        actividad.runOnUiThread(() -> {
            try {
                despachar(pedido);
            } catch (RuntimeException roto) {
                android.util.Log.w("CORT", "orden sin atender: " + roto, roto);
            }
        });
    }

    /**
     * Puertas para el diagnóstico por consola (`window.CORTcapaz('clima')`). No las
     * lee ninguna capa de la cara de la PC —son del APK viejo—; se mantienen porque
     * son la forma corta de preguntar «esto, en este aparato, ¿existe?».
     */
    @JavascriptInterface
    public String capacidades() {
        JSONObject j = new JSONObject();
        pone(j, "clima", true);
        pone(j, "cerebroLocal", CerebroLocal.hayLibreria());
        pone(j, "ollama", false);
        pone(j, "voz", true);
        pone(j, "micro", true);
        pone(j, "memoria", true);
        pone(j, "vida", true);
        pone(j, "compras", true);
        pone(j, "pc_estado", true);
        pone(j, "apps", true);
        pone(j, "antivirus", false);
        pone(j, "domotica", false);
        pone(j, "vpn", false);
        pone(j, "impresion3d", false);
        pone(j, "obsidiana", false);
        pone(j, "juegos", false);
        pone(j, "paquetes", false);
        pone(j, "tunel", false);
        pone(j, "actualizacion", false);
        pone(j, "vision", false);
        return j.toString();
    }

    /** El encaminador. Una rama por orden; lo que no la tiene se contesta en honesto. */
    private void despachar(JSONObject d) {
        String t = d.optString("type", "");
        if (t.isEmpty()) {
            t = d.optString("action", "");
        }
        if (t.isEmpty()) {
            return;
        }
        // ---------------- la conversación y su cerebro ----------------
        if ("user_input".equals(t)) {
            String dicho = d.optString("text", "").trim();
            if (!dicho.isEmpty()) {
                new Thread(() -> conversar(dicho), "cort-lazo").start();
            }
            return;
        }
        if ("check_ollama_status".equals(t)) {
            envia(estadoCerebro());
            return;
        }
        if ("pull_ollama_model".equals(t)) {
            bajar(d.optString("model", ""));
            return;
        }
        if ("set_local_model".equals(t)) {
            elegirModelo(d.optString("model", ""));
            return;
        }
        if ("probar_cerebro".equals(t)) {
            probar(d.optString("model", ""));
            return;
        }
        if ("get_agent_models".equals(t)) {
            envia(modelosDeAgente());
            return;
        }
        if ("perfil_equipo".equals(t)) {
            envia(perfilReply());
            return;
        }
        // ---------------- clima, temperatura, aparato ----------------
        if ("weather".equals(t)) {
            clima(d.optString("city", d.optString("ville", d.optString("ciudad", ""))));
            return;
        }
        if ("location_update".equals(t)) {
            double la = d.optDouble("lat", 0.0);
            double lo = d.optDouble("lon", d.optDouble("lng", 0.0));
            // `cort-mock.js` sustituye la geolocalización del navegador por (0,0)
            // para no abrir un permiso que no sirve de nada; guardar ese cero sería
            // cambiar la ciudad por el golfo de Guinea.
            if (Math.abs(la) > 0.01 || Math.abs(lo) > 0.01) {
                lat = la;
                lon = lo;
            }
            return;
        }
        if ("temperatura".equals(t)) {
            envia(salaTemperatura());
            return;
        }
        if ("pc_estado".equals(t)) {
            envia(pcEstado());
            return;
        }
        if ("pc_accion".equals(t)) {
            accionDirecta(d);
            return;
        }
        if ("detect_apps".equals(t)) {
            envia(appsDetectadas());
            return;
        }
        if ("get_installed_programs".equals(t)) {
            envia(programasInstalados());
            return;
        }
        // ---------------- la vida diaria ----------------
        if ("vida_estado".equals(t)) {
            envia(vidaEstado());
            return;
        }
        if ("get_shopping_list".equals(t)) {
            envia(listaDeCompras());
            return;
        }
        if ("update_shopping_list".equals(t)) {
            guardaLista(d.optJSONArray("items"));
            envia(listaDeCompras());
            return;
        }
        if ("memoria_estado".equals(t)) {
            envia(memoriaEstado());
            return;
        }
        if ("get_settings".equals(t)) {
            // La página la contesta sola desde su `localStorage` y el mock hace de
            // espejo: si Java respondiera un `settings_data` con un objeto vacío,
            // `main-*.js` limpiaría los campos de Ajustes y pondría los recordatorios
            // a cero. Aquí esta orden no tiene nada que decir.
            return;
        }
        if ("update_settings".equals(t)) {
            cacheaAjustes(d.optJSONObject("settings"));
            return;
        }
        // ---------------- la voz y el oído ----------------
        if ("voz_estado".equals(t) || "mic_estado".equals(t)) {
            envia(vozEstado());
            envia(micEstado());
            return;
        }
        if ("voz_on".equals(t)) {
            prefs.edit().putBoolean(CLAVE_HABLA, true).apply();
            envia(cuadro("type", "voz_activada", "origen", "real"));
            envia(vozEstado());
            return;
        }
        if ("voz_off".equals(t)) {
            prefs.edit().putBoolean(CLAVE_HABLA, false).apply();
            voz.callar();
            envia(cuadro("type", "voz_desactivada", "origen", "real",
                    "nota", "la voz del teléfono se apaga y se calla lo que estaba hablando"));
            envia(vozEstado());
            return;
        }
        if ("voz_motor".equals(t)) {
            envia(cuadro("type", "voz_motor_result", "origen", "real", "ok", false,
                    "motor", motorDeVoz(),
                    "aviso", "en el teléfono manda el motor de texto a voz de Android: no hay "
                            + "Piper ni espeak-ng que cambiar. Se elige la voz en Ajustes de Android.",
                    "micro", voz.voz()));
            return;
        }
        if ("av_speak".equals(t)) {
            String texto = d.optString("text", d.optString("mensaje", ""));
            if (!texto.trim().isEmpty()) {
                voz.hablar(texto);
            }
            return;
        }
        if ("stop_audio".equals(t)) {
            voz.callar();
            return;
        }
        if ("mic_on".equals(t) || "toggle_mic".equals(t)) {
            escuchar();
            return;
        }
        if ("mic_off".equals(t)) {
            callar();
            return;
        }
        if ("toggle_always_listen".equals(t)) {
            escuchaContinua = !escuchaContinua;
            if (escuchaContinua) {
                escuchar();
            } else {
                callar();
            }
            envia(micEstado());
            return;
        }
        // ---------------- la cara y su caché ----------------
        if ("clear_cache".equals(t)) {
            WebView w = web;
            if (w != null) {
                w.clearCache(true);
            }
            envia(cuadro("type", "cort_accion", "origen", "real", "ok", true,
                    "detalle", "caché del WebView vaciada: la cara vuelve a leer los archivos "
                            + "del APK", "nota", "la memoria y los modelos no se tocan"));
            return;
        }
        if ("toggle_fullscreen".equals(t)) {
            pantallaCompleta = !pantallaCompleta;
            actividad.runOnUiThread(() -> {
                if (pantallaCompleta) {
                    actividad.getWindow().addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
                } else {
                    actividad.getWindow().clearFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);
                }
            });
            envia(cuadro("type", "cort_accion", "origen", "real", "ok", true,
                    "detalle", pantallaCompleta ? "pantalla completa" : "pantalla normal"));
            return;
        }
        if ("open_browser".equals(t)) {
            String url = d.optString("url", "").trim();
            if (url.isEmpty() || !(url.startsWith("http://") || url.startsWith("https://"))) {
                aviso(t, "browser-panel", "no llega ninguna dirección que abrir",
                        "escribe una URL en el panel y vuelve a pedirlo");
                return;
            }
            try {
                actividad.startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
                envia(cuadro("type", "browser_state", "origen", "real", "state", "abierto",
                        "url", url, "nota", "se abrió en el navegador de Android"));
            } catch (RuntimeException noHayNavegador) {
                aviso(t, "browser-panel", "este teléfono no tiene un navegador que abra enlaces",
                        "instala uno o pídelo en la PC");
            }
            return;
        }
        // ---------------- lo que en el teléfono no existe ----------------
        if ("av_scan_start".equals(t)) {
            envia(cuadro("type", "av_start", "origen", "real",
                    "message", "el escáner de CORT revisa procesos y archivos del portátil"));
            aviso(t, "av-panel", "en Android no hay procesos ni archivos de usuario que revisar: "
                    + "cada app vive en su propia caja y el sistema no los expone",
                    "pedirlo desde la PC, o enlazar el teléfono con ella (fase S3)");
            envia(cuadro("type", "av_cancel", "origen", "real"));
            return;
        }
        if ("av_scan_cancel".equals(t)) {
            return;   // ya no hay nada corriendo
        }
        if ("av_threat_action".equals(t)) {
            envia(cuadro("type", "av_action_result", "origen", "real", "ok", false,
                    "message", "sin escáner en el teléfono no hay amenaza que limpiar"));
            return;
        }
        if ("check_jarvis_os_status".equals(t)) {
            envia(cuadro("type", "jarvis_os_status_reply", "origen", "real", "installed", false,
                    "port", 0, "motivo", "Jarvis OS es un programa de Windows; aquí no hay nada "
                            + "que instalar ni que arrancar"));
            return;
        }
        if ("buscar_actualizacion".equals(t)) {
            envia(cuadro("type", "actualizacion", "origen", "no disponible",
                    "hay_nueva", false, "local", versionApp(), "remota", "",
                    "motivo", "el repositorio de CORT es privado: desde el teléfono, sin token, "
                            + "la etiqueta más alta no se puede leer",
                    "nota", "la comprobación la hace la PC; el APK se actualiza instalando el "
                            + "de la release"));
            return;
        }
        if ("vision_estado".equals(t)) {
            envia(cuadro("type", "vision_estado", "origen", "no disponible", "ok", false,
                    "mirando", false, "cuadros", 0, "fps", 0,
                    "motivo", "la mirada por cámara del teléfono (gestos → ventana) es la fase "
                            + "F19e; en esta cara no hay ningún cuadro que contar todavía",
                    "nota", "el micrófono sí funciona: es el oído de Java, no el de la página"));
            return;
        }
        if ("set_agent_models".equals(t)) {
            aviso(t, "ajustes", "los papeles de modelo (principal/rápido/seguro) son de Ollama; "
                    + "el teléfono tiene un solo GGUF a la vez",
                    "elige el GGUF en la fila «cerebro» de esta misma cara");
            return;
        }
        if ("start_ollama".equals(t)) {
            aviso(t, "cort-cerebro", "en Android no existe el servicio de Ollama: el cerebro del "
                    + "teléfono es el GGUF cargado por llama.cpp dentro de la app",
                    "baja un modelo en la fila «cerebro» y pulsa «probar el cerebro»");
            return;
        }
        String[] panel = panelDe(t);
        if (panel != null) {
            aviso(t, panel[0], panel[1], panel[2]);
            return;
        }
        aviso(t, "", "nadie atiende «" + t + "» en el puente de este teléfono",
                "está anotado en PLAN_MOVIL.md y se decide en la fase que corresponda");
    }

    /** Lo que la cara pregunta y el teléfono no tiene: se dice, no se simula. */
    private void aviso(String orden, String panel, String motivo, String haceFalta) {
        envia(cuadro("type", "puente_aviso", "origen", "real", "orden", orden,
                "panel", panel, "motivo", motivo, "hace_falta", haceFalta,
                "nota", "teléfono " + Build.MANUFACTURER + " " + Build.MODEL
                        + " · Android " + Build.VERSION.RELEASE));
    }

    /**
     * La tabla de lo que en el teléfono no hay, escrita con la razón de cada cosa.
     * Es el equivalente android del `FALTA_EN_EL_PUENTE` de `cort_server.py`.
     */
    private String[] panelDe(String t) {
        if (t.startsWith("vpn_")) {
            return new String[] {"vpn-panel",
                    "la VPN que ofrece CORT es el cliente que corre en la PC; Android no deja "
                            + "montar un tunel desde una app que no sea la suya",
                    "activarla en Ajustes de Android, o pedirla con el teléfono enlazado a la PC"};
        }
        if (t.startsWith("ha_")) {
            return new String[] {"home-assistant-panel",
                    "la domótica cuelga de un servidor Home Assistant con su token; en este "
                            + "teléfono no está configurado ninguno",
                    "configurar el servidor en Ajustes de la PC y enlazar los dos aparatos"};
        }
        if (t.startsWith("print3d_")) {
            return new String[] {"print3d-panel",
                    "el laminador y la carpeta de STL viven en la PC; desde el teléfono no hay "
                            + "slicer que llamar",
                    "pedirlo en la PC"};
        }
        if (t.contains("obsidian")) {
            return new String[] {"obsidian-panel",
                    "la bóveda de Obsidian es una carpeta del portátil",
                    "abrir la bóveda en la PC, o sincronizarla con un cliente de notas propio"};
        }
        if (t.startsWith("games_") || "games_scan".equals(t)) {
            return new String[] {"games-panel",
                    "la biblioteca de juegos lee los lanzadores de escritorio (Steam, Lutris); "
                            + "en Android la lista equivalente son las apps, y ya están en «apps»",
                    "usar el panel de apps de esta cara"};
        }
        if (t.startsWith("winget") || t.startsWith("run_winget") || t.startsWith("get_winget")) {
            return new String[] {"updater-panel",
                    "winget es el gestor de paquetes de Windows; en Android los paquetes los "
                            + "mueve la tienda del fabricante",
                    "actualizar desde el almacén de apps del teléfono"};
        }
        if ("uninstall_program".equals(t) || "clean_leftovers".equals(t)) {
            return new String[] {"uninstaller-panel",
                    "desinstalar en Android pasa por el diálogo del sistema, app por app, y "
                            + "borrar archivos de otras apps no lo permite ningún permiso normal",
                    "desinstalar desde Ajustes › Aplicaciones del teléfono"};
        }
        if (t.startsWith("iptv_") || "get_windy_webcams".equals(t)) {
            return new String[] {"media-panel",
                    "esas pestañas son de un navegador de escritorio con su clave o su fichero "
                            + "m3u en disco",
                    "pedirlas en la PC"};
        }
        if ("get_desktop_wallpaper".equals(t)) {
            return new String[] {"wallpaper-panel",
                    "el fondo del teléfono lo pone Android; CORT no escribe en él sin el "
                            + "permiso de la dueña",
                    "cambiarlo desde Ajustes › Fondo de pantalla"};
        }
        if (t.contains("elevenlabs")) {
            return new String[] {"ajustes",
                    "las voces de ElevenLabs piden clave de API, y el teléfono no la guarda: "
                            + "la voz de aquí es la de Android",
                    "escribir la clave en Ajustes de la PC"};
        }
        if (t.contains("kokoro") || t.contains("local_tts") || t.startsWith("install_")
                || t.startsWith("uninstall_nemotron")) {
            return new String[] {"ajustes",
                    "esos motores de voz son programas que se instalan en el portátil; en "
                            + "Android el motor es el del sistema y ya está montado",
                    "instalar una voz en Ajustes › Idioma y entrada › Texto a voz"};
        }
        if (t.startsWith("claude_code")) {
            return new String[] {"ajustes",
                    "Claude Code es una herramienta de terminal del portátil",
                    "usarla en la PC"};
        }
        if (t.contains("tunnel") || "mobile_auth".equals(t)) {
            return new String[] {"ajustes",
                    "el enlace cifrado del teléfono con la PC (TLS + token) está aparcado por "
                            + "decisión medida: sin él no hay auth que hacer",
                    "ver fase S3 de PLAN_MOVIL.md"};
        }
        if (t.contains("browser")) {
            return new String[] {"browser-panel",
                    "cerrar la pestaña de otro desde una app no lo permite Android; sólo se "
                            + "puede abrir",
                    "deslizar el navegador para cerrarlo en el teléfono"};
        }
        if (t.startsWith("create_mobile_pairing") || t.contains("pairing")) {
            return new String[] {"mobile-pairing-dialog",
                    "el código de emparejamiento lo genera el puente de la PC con su token; "
                            + "un teléfono no puede emitir uno",
                    "abrir «emparejar teléfono» en la cara del portátil (fase S3)"};
        }
        if (t.startsWith("jarvis_os_")) {
            return new String[] {"jarvis-panel",
                    "el OS de la plantilla es un programa de Windows: no hay nada que "
                            + "instalar ni que abrir en este teléfono",
                    "usar la cara del portátil"};
        }
        return null;
    }

    /* ------------------------------------------------------------- la respuesta */

    /**
     * El lazo de la cara: frase → tabla de 33 reglas → acciones, y si la tabla no
     * la conoce, el GGUF del teléfono antes que la nube (U1). Corre en su hilo
     * porque abrir el modelo desde disco y `HttpURLConnection` bloquean.
     */
    private void conversar(String dicho) {
        envia(cuadro("state", "thinking"));
        String texto;
        String intencion;
        String motivo = "";
        boolean valido = true;
        String origenCerebro;
        String modeloUsado;
        String crudo = dicho;
        JSONObject argumentos = new JSONObject();
        List<Cerebro.Resultado> pasos = cerebro.cadena(dicho);
        if (!pasos.isEmpty()) {
            StringBuilder junta = new StringBuilder();
            intencion = pasos.get(0).accion;
            pone(argumentos, "accion", pasos.get(0).accion);
            if (!pasos.get(0).param.isEmpty()) {
                pone(argumentos, "param", pasos.get(0).param);
            }
            modeloUsado = "tabla de CORT";
            origenCerebro = "tabla";
            for (Cerebro.Resultado paso : pasos) {
                String salida = ejecutaEnLaInterfaz(paso);
                if (salida == null) {
                    valido = false;
                    motivo = "la regla está reconocida pero falta el dato";
                    junta.append("¿Cómo? Necesito el dato: pruébalo con «").append(pideEjemplo(paso)).append("».");
                    break;
                }
                if (junta.length() > 0) {
                    junta.append(" ");
                }
                junta.append(salida);
            }
            texto = junta.toString();
        } else {
            intencion = "respuesta";
            modeloUsado = "tabla de CORT";
            origenCerebro = "tabla";
            String memoria = recuerdos.lista(12);
            String local = cerebroLocal.contestar(dicho, memoria);
            if (local != null) {
                texto = local;
                CerebroLocal.Ficha ficha = cerebroLocal.elegido();
                modeloUsado = ficha == null ? "cerebro local" : ficha.nombre;
                origenCerebro = "gguf del teléfono";
                crudo = texto;
            } else if (nube.configurada()) {
                String deNube = nube.preguntar(dicho, memoria);
                texto = deNube != null ? deNube : null;
                if (texto != null) {
                    modeloUsado = nube.modelo();
                    origenCerebro = "nube";
                    crudo = texto;
                } else {
                    texto = "Esa frase no la conozco y la nube tampoco contestó: "
                            + nube.ultimoFallo();
                    motivo = "fallo de la nube";
                    origenCerebro = "sin respuesta";
                }
            } else {
                texto = "Esa frase no la conozco"
                        + (cerebroLocal.modo().equals("nube") ? " sin el portátil" : "")
                        + " (" + (local == null ? cerebroLocal.porqueNoLocal() : "")
                        + "). Sé hacer: " + String.join(", ", cerebro.acciones()) + ".";
                motivo = cerebroLocal.porqueNoLocal();
                origenCerebro = "sin respuesta";
            }
        }
        envia(cuadro("type", "plan_resultado", "origen", "real",
                "intencion", intencion, "valido", valido, "decir", texto,
                "motivo", motivo, "plan", cuadro("intencion", intencion, "argumentos", argumentos),
                "detalle", texto, "crudo", crudo, "frase", dicho));
        envia(cuadro("type", "brain_used", "modelo", modeloUsado, "origen", origenCerebro));
        dice(texto);
    }

    /** `Acciones.ejecutar` mueve `startActivity`: sólo vale en la interfaz. */
    private String ejecutaEnLaInterfaz(final Cerebro.Resultado paso) {
        final String[] salida = new String[1];
        final CountDownLatch lista = new CountDownLatch(1);
        actividad.runOnUiThread(() -> {
            salida[0] = acciones.ejecutar(paso);
            lista.countDown();
        });
        try {
            if (!lista.await(15, TimeUnit.SECONDS)) {
                return null;
            }
        } catch (InterruptedException cortada) {
            Thread.currentThread().interrupt();
            return null;
        }
        return salida[0];
    }

    private String pideEjemplo(Cerebro.Resultado r) {
        if ("alarma".equals(r.accion)) {
            return "pon una alarma a las 7:30";
        }
        if ("cronometro".equals(r.accion)) {
            return "cronometro de 5 minutos";
        }
        return r.accion;
    }

    /**
     * La ráfaga que la cara espera cuando CORT habla: estado, subtítulo vivo por
     * trozos, el texto en la consola, la voz de Android y el reposo. Son los mismos
     * cuadros y el mismo orden que `decir()` en `cort_server.py`, medidos allí.
     */
    private void dice(String texto) {
        envia(cuadro("state", "speaking"));
        subtitulos(texto);
        envia(cuadro("type", "jarvis_text", "text", texto, "origen", "real"));
        actividad.runOnUiThread(() -> {
            if (prefs.getBoolean(CLAVE_HABLA, true)) {
                voz.hablar(texto);
            }
        });
        double segundos = Math.min(4.0, Math.max(1.2, texto.length() * 0.03));
        duerme((long) (segundos * 1000));
        envia(cuadro("state", "idle"));
    }

    /** 26 caracteres por cuadro, con su espacio: el mismo paso del puente de Python. */
    private void subtitulos(String texto) {
        String id = "cort-" + System.currentTimeMillis();
        envia(cuadro("type", "live_subtitles", "id", id, "phase", "start"));
        for (int i = 0; i < texto.length(); i += 26) {
            envia(cuadro("type", "live_subtitles", "id", id, "phase", "delta",
                    "text", texto.substring(i, Math.min(texto.length(), i + 26)) + " "));
            duerme(50);
        }
        envia(cuadro("type", "live_subtitles", "id", id, "phase", "end"));
    }

    /* ------------------------------------------------------------- el cerebro */

    /**
     * El inventario que pinta la fila «cerebro». En el portátil es Ollama; aquí no
     * hay demonio que consultar, así que `online` dice **false porque es verdad** y
     * el catálogo son los GGUF del teléfono con su peso medido en disco y la RAM
     * libre de ahora, que es exactamente lo que la cara quiere mostrar.
     */
    private JSONObject estadoCerebro() {
        long libre = cerebroLocal.memoriaLibre();
        JSONArray instalados = new JSONArray();
        JSONObject catalogo = new JSONObject();
        List<CerebroLocal.Ficha> lista = CerebroLocal.catalogo(actividad);
        for (CerebroLocal.Ficha f : lista) {
            File gguf = CerebroLocal.archivoDe(actividad, f.archivo);
            boolean es = gguf.isFile();
            if (es) {
                puso(instalados, f.nombre);
            }
            pone(catalogo, f.nombre, cuadro(
                    "instalado", es,
                    "mb", es ? gguf.length() / 1024 / 1024 : f.bytes / 1024 / 1024,
                    "tam", "≈ " + (f.bytes / 1024 / 1024) + " MB",
                    "nota", f.nota,
                    "ram_uso", f.bytes / 1024 / 1024 * 2,
                    "origen", "disco del teléfono"));
        }
        CerebroLocal.Ficha activo = cerebroLocal.elegido();
        JSONObject estado = cuadro(
                "online", false,
                "found_local_models", nuevosClaves(instalados),
                "selected_model", activo == null ? "" : activo.nombre,
                "ram_disponible_mb", libre,
                "ram_total_mb", ramTotalMb(),
                "nucleos", Runtime.getRuntime().availableProcessors(),
                "en_disco", enDisco(lista),
                "catalogo", catalogo,
                "origen", "real",
                "nota", "el teléfono no tiene Ollama: estos son los GGUF que carga llama.cpp "
                        + "dentro de la app, medidos en su carpeta de datos");
        String aviso = CerebroLocal.avisoDeCatalogo();
        if (!aviso.isEmpty()) {
            pone(estado, "aviso_catalogo", aviso);
        }
        if (!CerebroLocal.hayLibreria()) {
            pone(estado, "aviso_motor", CerebroLocal.motivoSinLibreria());
        }
        return cuadro("type", "ollama_status_reply", "status", estado);
    }

    /** `found_local_models` en la forma que lee la cara: nombre → nombre. */
    private static JSONObject nuevosClaves(JSONArray nombres) {
        JSONObject j = new JSONObject();
        for (int i = 0; i < nombres.length(); i++) {
            String nombre = nombres.optString(i, "");
            if (!nombre.isEmpty()) {
                pone(j, nombre, nombre);
            }
        }
        return j;
    }

    /** Peso instalado por modelo, como `en_disco` del puente. */
    private JSONObject enDisco(List<CerebroLocal.Ficha> lista) {
        JSONObject j = new JSONObject();
        for (CerebroLocal.Ficha f : lista) {
            File gguf = CerebroLocal.archivoDe(actividad, f.archivo);
            if (gguf.isFile()) {
                pone(j, f.nombre, cuadro("mb", gguf.length() / 1024 / 1024,
                        "ram_est", gguf.length() / 1024 / 1024 * 2));
            }
        }
        return j;
    }

    private JSONObject modelosDeAgente() {
        JSONArray hay = new JSONArray();
        for (CerebroLocal.Ficha f : CerebroLocal.catalogo(actividad)) {
            if (CerebroLocal.archivoDe(actividad, f.archivo).isFile()) {
                puso(hay, f.nombre);
            }
        }
        JSONObject cada = cuadro("principal", hay, "rapido", hay, "seguro", hay);
        return cuadro("type", "agent_models_info", "origen", "real",
                "data", cuadro("available_models", cada),
                "nota", "un solo GGUF por papel: el teléfono no tiene un servidor de modelos");
    }

    /** El botón «descargar» de la cara, en el teléfono: baja el GGUF con su SHA-256. */
    private void bajar(final String nombre) {
        final CerebroLocal.Ficha ficha = buscaFicha(nombre);
        if (ficha == null) {
            envia(cuadro("type", "ollama_pull_progress", "model", nombre, "origen", "real",
                    "status", "ese modelo no está en la lista del teléfono", "pct", 0,
                    "done", true, "success", false));
            return;
        }
        if (bajando) {
            envia(cuadro("type", "ollama_pull_progress", "model", ficha.nombre, "origen", "real",
                    "status", "ya hay una descarga en curso: espera a que termine", "pct", 0,
                    "done", false, "success", true));
            return;
        }
        final Bajada viaje = Bajada.de(actividad, ficha);
        if (viaje.esta()) {
            envia(estadoCerebro());
            return;
        }
        bajada = viaje;
        bajando = true;
        new Thread(() -> {
            envia(cuadro("type", "ollama_pull_progress", "model", ficha.nombre, "origen", "real",
                    "status", "empezando la descarga de " + (ficha.bytes / 1024 / 1024) + " MB",
                    "pct", 0, "done", false, "success", true));
            try {
                viaje.ejecutar(ficha, (hechos, total, pct, texto) -> {
                    if (pct >= 100) {
                        envia(cuadro("type", "ollama_pull_progress", "model", ficha.nombre,
                                "origen", "real", "status", texto, "pct", 100,
                                "done", true, "success", true));
                        return;
                    }
                    // Cada cuadro es un `evaluateJavascript`; se empuja uno por
                    // porcentaje, que en un 0,5 GB son quinientas entregas.
                    envia(cuadro("type", "ollama_pull_progress", "model", ficha.nombre,
                            "origen", "real", "status", texto, "pct", pct,
                            "done", false, "success", true));
                });
                envia(estadoCerebro());
            } catch (Exception roto) {
                envia(cuadro("type", "ollama_pull_progress", "model", ficha.nombre,
                        "origen", "real", "status", "la descarga se cortó: " + roto,
                        "pct", 0, "done", true, "success", false));
            } finally {
                bajando = false;
                bajada = null;
            }
        }, "cort-bajada").start();
    }

    private void elegirModelo(String nombre) {
        CerebroLocal.Ficha ficha = buscaFicha(nombre);
        if (ficha == null) {
            envia(cuadro("type", "local_model_set", "model", nombre, "origen", "real",
                    "aviso", "ese nombre no está en la lista del teléfono"));
            return;
        }
        if (!CerebroLocal.archivoDe(actividad, ficha.archivo).isFile()) {
            envia(cuadro("type", "local_model_set", "model", ficha.nombre, "origen", "real",
                    "aviso", "todavía no está en disco: pulsa «descargar» primero"));
            return;
        }
        actividad.getSharedPreferences(CerebroLocal.PREFERENCIAS, Context.MODE_PRIVATE)
                .edit().putString(CerebroLocal.CLAVE_ACTIVO, ficha.archivo).apply();
        envia(cuadro("type", "local_model_set", "model", ficha.nombre, "origen", "real",
                "aviso", "elegido: " + ficha.nombre + " · " + cerebroLocal.falta(ficha.bytes)));
        envia(estadoCerebro());
    }

    /** «probar el cerebro»: cargar el GGUF y decir cuántos tokens por segundo sale. */
    private void probar(final String nombre) {
        final CerebroLocal.Ficha ficha = buscaFicha(nombre);
        if (ficha == null) {
            envia(cuadro("type", "cerebro_prueba", "origen", "real", "modelo", nombre,
                    "ok", false, "valido", false,
                    "motivo", "no está en la lista del teléfono"));
            return;
        }
        envia(cuadro("type", "cerebro_prueba", "origen", "real", "empezando", true,
                "modelo", ficha.nombre,
                "frase", "cargando " + (ficha.bytes / 1024 / 1024) + " MB y pidiendo una frase"));
        new Thread(() -> {
            JSONObject respuesta = cuadro("type", "cerebro_prueba", "origen", "real",
                    "modelo", ficha.nombre);
            try {
                actividad.getSharedPreferences(CerebroLocal.PREFERENCIAS, Context.MODE_PRIVATE)
                        .edit().putString(CerebroLocal.CLAVE_ACTIVO, ficha.archivo).apply();
                if (!cerebroLocal.asegurar()) {
                    envia(pone(respuesta, "ok", false, "valido", false,
                            "motivo", cerebroLocal.porqueNoLocal()));
                    return;
                }
                long desde = System.currentTimeMillis();
                List<String[]> turno = new ArrayList<>();
                turno.add(new String[] {"user", "Di en una frase quién eres."});
                // `preguntar` empuja token a token; la cara no tiene dónde leerlos,
                // pero el orbe late: se deja el oyente vacío y se toma el texto entero.
                String dicho = cerebroLocal.preguntar(CerebroLocal.sistemaCort(null),
                        turno, pieza -> { }, 120, 0.7f);
                long ms = System.currentTimeMillis() - desde;
                String medida = cerebroLocal.ultimaMedida();
                long tokens = valorDe(medida, "tokens");
                double porSegundo = ms > 0 ? tokens * 1000.0 / ms : 0.0;
                boolean hay = dicho != null && !dicho.trim().isEmpty();
                envia(pone(respuesta,
                        "ok", hay, "valido", hay,
                        "frase", "Di en una frase quién eres.",
                        "crudo", dicho == null ? "" : dicho,
                        "plan", cuadro("intencion", "respuesta"),
                        "ms", ms, "tok_s", redondea(porSegundo),
                        "medida", medida,
                        "motivo", hay ? "" : "el modelo no devolvió texto"));
            } catch (RuntimeException | Error roto) {
                envia(pone(respuesta, "ok", false, "valido", false,
                        "motivo", "el motor falló al responder: " + roto));
            }
        }, "cort-prueba").start();
    }

    private static long valorDe(String cuadroMedido, String clave) {
        for (String trozo : cuadroMedido.split("&")) {
            if (trozo.startsWith(clave + "=")) {
                try {
                    return Long.parseLong(trozo.substring(clave.length() + 1).trim());
                } catch (NumberFormatException noEsNumero) {
                    return 0L;
                }
            }
        }
        return 0L;
    }

    private static double redondea(double valor) {
        return Math.round(valor * 100.0) / 100.0;
    }

    /** El nombre que manda la cara («Qwen2.5 0,5B…» o el archivo) a su ficha. */
    private CerebroLocal.Ficha buscaFicha(String nombre) {
        if (nombre == null || nombre.trim().isEmpty()) {
            return cerebroLocal.elegido();
        }
        String busca = nombre.trim().toLowerCase(Locale.ROOT);
        List<CerebroLocal.Ficha> lista = CerebroLocal.catalogo(actividad);
        for (CerebroLocal.Ficha f : lista) {
            if (f.nombre.toLowerCase(Locale.ROOT).equals(busca)
                    || f.archivo.toLowerCase(Locale.ROOT).equals(busca)
                    || f.id.toLowerCase(Locale.ROOT).equals(busca)) {
                return f;
            }
        }
        for (CerebroLocal.Ficha f : lista) {
            String archivo = f.archivo.toLowerCase(Locale.ROOT);
            String id = f.id.toLowerCase(Locale.ROOT);
            if (archivo.contains(busca) || id.contains(busca)
                    || busca.contains(id.replace("-", "."))) {
                return f;
            }
        }
        return null;
    }

    /* ------------------------------------------------------- el equipo medido */

    /** El `system_stats` que el puente empuja cada cuatro segundos. */
    private JSONObject sistemaStats() {
        double[] cpu = cpuDelta();
        double ram = -1.0;
        long libreMb = -1L;
        long totalMb = ramTotalMb();
        try {
            ActivityManager gestor = (ActivityManager) actividad.getSystemService(
                    Context.ACTIVITY_SERVICE);
            ActivityManager.MemoryInfo ahora = new ActivityManager.MemoryInfo();
            gestor.getMemoryInfo(ahora);
            libreMb = ahora.availMem / 1024 / 1024;
            if (totalMb > 0) {
                ram = (totalMb - libreMb) * 100.0 / totalMb;
            }
        } catch (RuntimeException noHayGestor) {
            // sin `activity_service` no hay RAM: se manda el -1 de «no medido»
        }
        JSONObject j = cuadro("type", "system_stats", "origen", "real",
                "ram", ram < 0 ? -1 : redondea(ram),
                "ram_disponible_mb", libreMb,
                "ram_total_mb", totalMb,
                "nucleos", Runtime.getRuntime().availableProcessors(),
                "disco_pct", redondea(discoUsadoPorCiento()));
        if (cpu != null) {
            pone(j, "cpu", redondea(cpu[0]));
        }
        pone(j, "bateria", nivelDePila());
        return j;
    }

    /**
     * `% de CPU` entre dos lecturas de `/proc/stat`. Con una sola muestra no hay
     * delta posible: se devuelve `null` y el cuadro sale sin la clave, que es como
     * el puente dice «no medido» sin fingir un número.
     */
    private double[] cpuDelta() {
        try {
            String linea = "";
            for (String candidata : new String(Files.readAllBytes(
                    new File("/proc/stat").toPath()), StandardCharsets.UTF_8).split("\n")) {
                if (candidata.startsWith("cpu ")) {
                    linea = candidata;
                    break;
                }
            }
            String[] campos = linea.trim().split("\\s+");
            long total = 0L;
            long ocio = 0L;
            for (int i = 1; i < campos.length; i++) {
                long v = Long.parseLong(campos[i]);
                total += v;
                if (i == 4 || i == 5) {          // idle + iowait
                    ocio += v;
                }
            }
            if (total <= 0L) {
                return null;
            }
            Double porcentaje = null;
            if (cpuTotalPrevio > 0 && total > cpuTotalPrevio) {
                long dt = total - cpuTotalPrevio;
                long do_ = ocio - cpuOcioPrevio;
                porcentaje = (dt - do_) * 100.0 / dt;
            }
            cpuTotalPrevio = total;
            cpuOcioPrevio = ocio;
            return porcentaje == null ? null : new double[] {porcentaje};
        } catch (IOException | NumberFormatException | IndexOutOfBoundsException sinStat) {
            return null;
        }
    }

    private long ramTotalMb() {
        try {
            for (String linea : new String(Files.readAllBytes(
                    new File("/proc/meminfo").toPath()), StandardCharsets.UTF_8).split("\n")) {
                if (linea.startsWith("MemTotal:")) {
                    return Long.parseLong(linea.replaceAll("\\D", "")) / 1024L;
                }
            }
        } catch (IOException | NumberFormatException sinMeminfo) {
            // se queda en -1 y el cuadro lo dice como número, no como excusa
        }
        return -1L;
    }

    private double discoUsadoPorCiento() {
        try {
            StatFs disco = new StatFs(actividad.getDataDir().getPath());
            long total = disco.getTotalBytes();
            return total > 0 ? (total - disco.getAvailableBytes()) * 100.0 / total : -1.0;
        } catch (RuntimeException sinStatFs) {
            return -1.0;
        }
    }

    /** 0..100 de la pila. `registerReceiver(null, filtro)` lee el intent pegajoso. */
    private int nivelDePila() {
        try {
            Intent pila = actividad.registerReceiver(null,
                    new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            if (pila == null) {
                return -1;
            }
            int nivel = pila.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
            int tope = pila.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
            return nivel >= 0 && tope > 0 ? nivel * 100 / tope : -1;
        } catch (RuntimeException sinPila) {
            return -1;
        }
    }

    /** Los grados del sensor de la pila, dichos **como lo que son**. */
    private JSONObject salaTemperatura() {
        try {
            Intent pila = actividad.registerReceiver(null,
                    new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            int decimas = pila == null ? -1 : pila.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, -1);
            if (decimas < 0) {
                return cuadro("type", "sala_temperatura", "origen", "no disponible",
                        "data", cuadro("ok", false,
                                "motivo", "este teléfono no expone ningún sensor de temperatura "
                                        + "legible desde la app"));
            }
            double grados = decimas / 10.0;
            return cuadro("type", "sala_temperatura", "origen", "real",
                    "data", cuadro("ok", true,
                            "piece", "BATERÍA DEL TELÉFONO",
                            "temperature", redondea(grados),
                            "sensor", "BatteryManager.EXTRA_TEMPERATURE",
                            "aviso", "no es la temperatura de la habitación: es la de la "
                                    + "batería, que es el único termómetro que Android deja "
                                    + "leer sin permisos. En la PC el puente lee /sys/class/thermal."));
        } catch (RuntimeException sinSensor) {
            return cuadro("type", "sala_temperatura", "origen", "no disponible",
                    "data", cuadro("ok", false, "motivo", "el intent de la pila no contestó"));
        }
    }

    /** El escaneo S1 del aparato, en la forma exacta que pinta `nodoPerfil`. */
    private JSONObject perfilReply() {
        long libre = cerebroLocal.memoriaLibre();
        long total = ramTotalMb();
        List<CerebroLocal.Ficha> lista = CerebroLocal.catalogo(actividad);
        CerebroLocal.Ficha elegido = cerebroLocal.elegido();
        JSONArray ajustes = new JSONArray();
        int nivel;
        String nombre;
        String motivo;
        JSONArray seApaga = new JSONArray();
        if (!CerebroLocal.hayLibreria()) {
            nivel = 1;
            nombre = "sin motor GGUF";
            motivo = CerebroLocal.motivoSinLibreria();
        } else if (elegido != null) {
            nivel = 3;
            nombre = "cerebro local en el teléfono";
            motivo = elegido.nombre + " cabe: la puerta pide " + (elegido.bytes / 1024 / 1024 * 2)
                    + " MB libres y hay " + libre;
        } else {
            nivel = 2;
            nombre = "tabla de CORT, sin GGUF cargado";
            motivo = libre + " MB libres: ninguno de los " + lista.size()
                    + " modelos de la lista pasa la puerta del doble de su peso";
        }
        JSONObject cpu = cuadro("modelo", Build.MANUFACTURER + " " + Build.MODEL,
                "nucleos", Runtime.getRuntime().availableProcessors(),
                "mhz", mhzMedidos(),
                "avx", false, "avx2", false, "sse42", false,
                "carga_1min", carga1min(),
                "instrucciones", String.join(", ", Build.SUPPORTED_ABIS));
        pone(cpu, "nota", "AVX/AVX2/SSE4.2 son juego de instrucciones x86: en este ARM no "
                + "aplican, y por eso van en no y no en «sin medir»");
        JSONObject plan = cuadro("orbe30", total > 3000 && libre > 1500,
                "orbe24", true, "scanlines", false,
                "voz_natural", false, "escucha", true, "vision", false,
                "orbe_fps", total > 3000 ? 30 : 24);
        puso(ajustes, "scanlines apagadas: la cara se ve entera en 521 px");
        puso(ajustes, elegido == null
                ? "el cerebro local sigue apagado hasta que la RAM lo permita"
                : "cerebro local fijado a " + elegido.nombre);
        // Lo que el nivel de este teléfono deja fuera, dicho en texto: la tarjeta
        // del escáner muestra esta lista y no tiene derecho a callar los recortes.
        puso(seApaga, "scanlines");
        puso(seApaga, "voz natural por nube");
        puso(seApaga, "mirada con cámara (va en la fase F19e)");
        if (total <= 3000 || libre <= 1500) {
            puso(seApaga, "orbe a 30 fotogramas por segundo");
        }
        if (elegido == null) {
            puso(seApaga, "cerebro GGUF local");
        }
        return cuadro("type", "perfil_reply", "origen", "real",
                "cpu", cpu,
                "memoria", cuadro("libre_mb", libre, "total_mb", total,
                        "swap_libre_mb", deMeminfo("SwapFree:"), "swap_total_mb", deMeminfo("SwapTotal:")),
                "disco", cuadro("libre_mb", actividad.getDataDir().getUsableSpace() / 1024 / 1024,
                        "total_mb", actividad.getDataDir().getTotalSpace() / 1024 / 1024),
                "gpu", cuadro("nodos_dri", 0, "cuda", false,
                        "descripcion", Build.SUPPORTED_ABIS[0] + " · GLES por el sistema",
                        "etiqueta", "sin lectura de GPU desde CORT"),
                "camara", camara(),
                "temperatura", cuadro("celsius", temperaturaDePila(),
                        "sensor", "batería (el único termómetro legible en Android)"),
                "audio", cuadro("suena", voz.voz() != null && !voz.voz().isEmpty(),
                        "escucha", Motor.compartido(actividad.getApplicationContext()).listo(),
                        "micros", new JSONArray(),
                        "nota", "la salida es el motor de texto a voz de Android; el oído local "
                                + "es Vosk dentro de la app"),
                "nivel", cuadro("nivel", nivel, "nombre", nombre, "motivo", motivo,
                        "se_apaga", seApaga, "se_apaga_texto", seApaga),
                "plan", plan,
                "medido_en", "el propio teléfono, sin preguntar a la PC",
                "ajustes_aplicados", ajustes);
    }

    /** La frecuencia de reloj, si `sysfs` la deja leer; si no, -1 («sin medir»). */
    private long mhzMedidos() {
        String[] rutas = {"/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq",
                "/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq"};
        for (String ruta : rutas) {
            try {
                String texto = new String(Files.readAllBytes(new File(ruta).toPath()),
                        StandardCharsets.UTF_8).trim();
                return Long.parseLong(texto.replaceAll("\\D", "")) / 1000L;   // kHz → MHz
            } catch (IOException | NumberFormatException sinPermiso) {
                // la siguiente ruta
            }
        }
        return -1L;
    }

    private String carga1min() {
        try {
            return new String(Files.readAllBytes(new File("/proc/loadavg").toPath()),
                    StandardCharsets.UTF_8).trim().split("\\s+")[0];
        } catch (IOException sinLoadavg) {
            return "-1";
        }
    }

    private long deMeminfo(String clave) {
        try {
            for (String linea : new String(Files.readAllBytes(
                    new File("/proc/meminfo").toPath()), StandardCharsets.UTF_8).split("\n")) {
                if (linea.startsWith(clave)) {
                    return Long.parseLong(linea.replaceAll("\\D", "")) / 1024L;
                }
            }
        } catch (IOException | NumberFormatException sinMeminfo) {
            // -1 es «no medido», y la cara lo pinta como número
        }
        return -1L;
    }

    private double temperaturaDePila() {
        Intent pila;
        try {
            pila = actividad.registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        } catch (RuntimeException sinPila) {
            return -1;
        }
        int decimas = pila == null ? -1 : pila.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, -1);
        return decimas < 0 ? -1 : decimas / 10.0;
    }

    /**
     * Las cámaras que Android ve. `getCameraIdList` necesita `CAMERA` concedida; sin
     * ella se contesta la lista vacía **y el motivo**, que es la diferencia entre un
     * «sin cámara» falso y uno honesto.
     */
    private JSONArray camara() {
        JSONArray lista = new JSONArray();
        try {
            CameraManager gestor = (CameraManager) actividad.getSystemService(
                    Context.CAMERA_SERVICE);
            if (gestor != null) {
                for (String id : gestor.getCameraIdList()) {
                    puso(lista, cuadro("nodo", "cámara " + id, "nombre", "id " + id));
                }
            }
        } catch (Exception noSePuedeVer) {
            android.util.Log.w("CORT", "cámaras sin leer: " + noSePuedeVer);
        }
        return lista;
    }

    /* ------------------------------------------------- la voz, el oído, la vida */

    private String motorDeVoz() {
        String asignado;
        try {
            asignado = Settings.Secure.getString(actividad.getContentResolver(),
                    "tts_default_synth");
        } catch (RuntimeException sinAjuste) {
            asignado = "";
        }
        return asignado == null || asignado.isEmpty() ? "el motor de Android, sin asignar" : asignado;
    }

    private JSONObject vozEstado() {
        String sink = "";
        try {
            AudioManager audio = (AudioManager) actividad.getSystemService(Context.AUDIO_SERVICE);
            sink = Audifonos.salida(audio);
        } catch (RuntimeException sinAudio) {
            sink = "sin leer";
        }
        return cuadro("type", "voz_estado", "origen", "real",
                "ok", true,
                "habla", voz.voz() == null ? "sin voz montada todavía" : voz.voz(),
                "motor", motorDeVoz(),
                "activa", prefs.getBoolean(CLAVE_HABLA, true),
                "sintetiza_ms", -1,
                "stt", Motor.compartido(actividad).listo() ? "Vosk small-es-0.42" : "el reconocedor de Android",
                "stt_mb", Motor.compartido(actividad).pesoDelModelo() / 1024 / 1024,
                "altavoz_real", true,
                "sink", sink,
                "micro", voz.oido(),
                "microfonos", new JSONArray(),
                "entradas_que_ve", new JSONArray(),
                "escucha", escuchaContinua,
                "wake", escuchaContinua,
                "despierto", false,
                "nota", "en el teléfono la voz la pone Android y el oído local es Vosk; "
                        + "el aviso de qué altavoz suena lo da la propia app");
    }

    private JSONObject micEstado() {
        return cuadro("type", "mic_estado", "origen", "real",
                "estado", escuchando ? "escuchando" : "apagado",
                "ok", true,
                "microfonos", new JSONArray(),
                "nota", "el micrófono es el de Android, abierto por Java; la página no usa "
                        + "getUserMedia en este origen");
    }

    /** Lo que la cara lee en su tarjeta de vida: lista, notas y pendientes. */
    private JSONObject vidaEstado() {
        JSONArray compras = comprasGuardadas();
        JSONArray notas = new JSONArray();
        for (String[] fila : recuerdos.filas(20)) {
            puso(notas, cuadro("texto", fila[0], "cuando", fila[1]));
        }
        JSONArray pendientes = new JSONArray();
        long faltan = -1L;
        String proximoTexto = "";
        JSONArray recordatorios = arregloDe(prefs.getString(CLAVE_RECORDATORIOS, "[]"));
        // Los pendientes de la página son horas del día («18:00»); en el teléfono no
        // hay ningún planificador que los dispare todavía (F19d), así que se listan
        // y se dice, pero no se promete la alarma.
        java.util.Calendar ahora = java.util.Calendar.getInstance();
        long hoyMinutos = ahora.get(java.util.Calendar.HOUR_OF_DAY) * 60L
                + ahora.get(java.util.Calendar.MINUTE);
        for (int i = 0; i < recordatorios.length(); i++) {
            JSONObject r = recordatorios.optJSONObject(i);
            if (r == null || !r.optBoolean("active", true)) {
                continue;
            }
            String hora = r.optString("time", "");
            puso(pendientes, cuadro("texto", r.optString("text", ""), "cuando", hora,
                    "origen", "Ajustes de la cara"));
            if (hora.contains(":")) {
                try {
                    long minutos = Long.parseLong(hora.split(":")[0]) * 60L
                            + Long.parseLong(hora.split(":")[1]);
                    long faltanMin = (minutos - hoyMinutos + 1440L) % 1440L;
                    if (faltan < 0 || faltanMin * 60 < faltan) {
                        faltan = faltanMin * 60;
                        proximoTexto = r.optString("text", hora);
                    }
                } catch (RuntimeException horaRara) {
                    // se queda sin el «próximo», y la nota lo dice
                }
            }
        }
        JSONObject proximo = faltan < 0 ? null
                : cuadro("texto", proximoTexto, "faltan_seg", faltan,
                        "origen", "reloj del teléfono");
        return cuadro("type", "vida_estado", "origen", "real",
                "datos", cuadro("carpeta", actividad.getFilesDir().getAbsolutePath(),
                        "existe", true,
                        "compras", compras.length(),
                        "notas", recuerdos.cuentasDeHechos(),
                        "pendientes", pendientes.length(),
                        "vencidos", 0,
                        "proximo", proximo == null ? JSONObject.NULL : proximo,
                        "vela", 0),
                "compras", compras,
                "notas", notas,
                "pendientes", pendientes,
                "resumen", "en el teléfono: " + compras.length() + " cosas de compra, "
                        + recuerdos.cuentasDeHechos() + " apuntes y " + pendientes.length()
                        + " pendientes escritos en Ajustes. Las alarmas que se ponen con «pon "
                        + "una alarma» van a la app Reloj de Android y desde aquí no se leen.");
    }

    private JSONArray comprasGuardadas() {
        return arregloDe(prefs.getString(CLAVE_COMPRAS, "[]"));
    }

    private void guardaLista(JSONArray nueva) {
        JSONArray lista = nueva == null ? new JSONArray() : nueva;
        prefs.edit().putString(CLAVE_COMPRAS, lista.toString()).apply();
    }

    private JSONObject listaDeCompras() {
        JSONArray lista = comprasGuardadas();
        return cuadro("type", "shopping_list", "items", lista, "origen", "real",
                "nota", lista.length() == 0 ? "lista vacía: se guarda en este teléfono" : "");
    }

    /** `contexto` es literalmente lo que se le manda al modelo: la prueba de que entró. */
    private JSONObject memoriaEstado() {
        int hechos = recuerdos.cuentasDeHechos();
        int preferencias = 0;
        String[] claves = {"nombre", "edad", "ciudad", "me llamo", "soy"};
        for (String clave : claves) {
            String v = recuerdos.valor(clave);
            if (v != null && !v.isEmpty()) {
                preferencias++;
            }
        }
        String sistema = CerebroLocal.sistemaCort(recuerdos.lista(12));
        return cuadro("type", "memoria_estado", "origen", "real",
                "datos", cuadro("modulo", "cort-móvil", "version", 1, "origen", "teléfono",
                        "ruta", actividad.getDatabasePath("cort.db").getAbsolutePath(),
                        "existe", true,
                        "hechos", hechos,
                        "preferencias", preferencias,
                        "correcciones", 0,
                        "constitucion", sistema.length()),
                "contexto", recuerdos.lista(12),
                "nota", "las correcciones se anotan en la PC (fase F4): en el teléfono aún no "
                        + "hay una tabla que las guarde");
    }

    /** Lo que la cara llama «el equipo», en versión teléfono. */
    private JSONObject pcEstado() {
        int volumen = -1;
        int tope = 1;
        boolean mudo = false;
        String sink = "sin leer";
        try {
            AudioManager audio = (AudioManager) actividad.getSystemService(Context.AUDIO_SERVICE);
            volumen = audio.getStreamVolume(AudioManager.STREAM_MUSIC);
            tope = audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
            mudo = volumen == 0 || audio.getRingerMode() == AudioManager.RINGER_MODE_SILENT;
            sink = Audifonos.salida(audio);
        } catch (RuntimeException sinAudio) {
            // se queda en -1 y la cara lo pinta como «--»
        }
        int brillo = -1;
        try {
            float bruto = Settings.System.getFloat(actividad.getContentResolver(),
                    Settings.System.SCREEN_BRIGHTNESS, -1f);
            if (bruto >= 0) {
                brillo = Math.round(bruto * 100 / 255);
            }
        } catch (RuntimeException sinPermiso) {
            // Android no lo deja leer en algún fabricante: -1 es «sin medir»
        }
        JSONObject herramientas = cuadro(
                "linterna", "sí, con la cámara",
                "reproduccion", "no: CORT no controla el reproductor de Android",
                "alarmas", "las pone la app Reloj y no se leen desde aquí");
        return cuadro("type", "pc_estado", "origen", "real",
                "apps", 0, "ventanas", 0, "ventanas_lista", new JSONArray(),
                "volumen", cuadro("sink", sink, "porcentaje",
                        volumen < 0 ? JSONObject.NULL : volumen * 100 / Math.max(1, tope),
                        "mudo", mudo),
                "brillo", cuadro("porcentaje", brillo < 0 ? JSONObject.NULL : brillo,
                        "sensor", brillo < 0 ? "sin lectura" : "Settings.System.SCREEN_BRIGHTNESS"),
                "herramientas", herramientas,
                "fondo", "el fondo del teléfono lo pone Android",
                "bateria", nivelDePila(),
                "ram_libre_mb", cerebroLocal.memoriaLibre(),
                "nota", "Android 14 no deja listar las apps en primer plano ni sus ventanas: "
                        + "los ceros de arriba son «no legible», no «no hay nada». Lo que sí "
                        + "se mide aquí es volumen, brillo, pila y RAM.");
    }

    /** `pc_accion` dicho en castellano de teléfono: volumen y abrir cosas. */
    private void accionDirecta(JSONObject d) {
        String que = d.optString("accion", "");
        if ("volumen".equals(que)) {
            int porcentaje = d.optInt("valor", d.optInt("porcentaje", d.optInt("nivel", -1)));
            try {
                AudioManager audio = (AudioManager) actividad.getSystemService(
                        Context.AUDIO_SERVICE);
                if (porcentaje >= 0) {
                    int tope = audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
                    audio.setStreamVolume(AudioManager.STREAM_MUSIC,
                            Math.max(0, Math.min(tope, tope * porcentaje / 100)),
                            AudioManager.FLAG_SHOW_UI);
                    envia(cuadro("type", "cort_accion", "origen", "real", "ok", true,
                            "detalle", "volumen al " + porcentaje + "%"));
                    return;
                }
            } catch (RuntimeException sinAudio) {
                // sigue al aviso
            }
            aviso("pc_accion", "pc-panel", "no puedo poner el volumen sin un número",
                    "manda «valor» de 0 a 100");
            return;
        }
        if ("abrir".equals(que) || "url".equals(que) || "navegador".equals(que)) {
            String url = d.optString("url", d.optString("target", d.optString("programa", "")));
            if (!url.isEmpty()) {
                JSONObject imita = new JSONObject();
                pone(imita, "url", url);
                pone(imita, "type", "open_browser");
                despachar(imita);
                return;
            }
        }
        aviso("pc_accion", "pc-panel", "«" + que + "» es una acción del escritorio: en el "
                + "teléfono sólo hay volumen y abrir enlaces", "pedirlo en la PC o enlazarla");
    }

    /** Las apps que se pueden lanzar: el equivalente androide de `detect_apps`. */
    private JSONObject appsDetectadas() {
        JSONArray lista = new JSONArray();
        try {
            PackageManager pm = actividad.getPackageManager();
            Intent lanzar = new Intent(Intent.ACTION_MAIN);
            lanzar.addCategory(Intent.CATEGORY_LAUNCHER);
            List<ResolveInfo> vistas = pm.queryIntentActivities(lanzar, 0);
            for (ResolveInfo ri : vistas) {
                if (ri.activityInfo == null || ri.activityInfo.packageName == null) {
                    continue;
                }
                puso(lista, cuadro("nom", String.valueOf(ri.loadLabel(pm)),
                        "chemin", ri.activityInfo.packageName));
            }
        } catch (RuntimeException sinLista) {
            android.util.Log.w("CORT", "apps sin listar", sinLista);
        }
        return cuadro("type", "detected_apps", "origen", "real", "apps", lista,
                "nota", "las apps con icono de arranque que este teléfono deja ver: el bloque "
                        + "`queries` del manifiesto limita la lista a esa intención");
    }

    /** Idéntica lectura, en la forma del panel de programas. */
    private JSONObject programasInstalados() {
        JSONArray lista = new JSONArray();
        try {
            PackageManager pm = actividad.getPackageManager();
            List<ApplicationInfo> todas = pm.getInstalledApplications(0);
            for (ApplicationInfo info : todas) {
                String version = "";
                try {
                    version = pm.getPackageInfo(info.packageName, 0).versionName;
                } catch (PackageManager.NameNotFoundException seFue) {
                    version = "?";
                }
                puso(lista, cuadro("name", String.valueOf(pm.getApplicationLabel(info)),
                        "version", version == null ? "?" : version,
                        "publisher", "PackageManager de Android",
                        "hive", "sin medir"));
            }
        } catch (RuntimeException sinLista) {
            android.util.Log.w("CORT", "programas sin listar", sinLista);
        }
        return cuadro("type", "installed_programs", "origen", "real", "programs", lista,
                "nota", "el tamaño de cada APK no lo expone el `PackageManager` sin permisos "
                        + "de especial: va en «sin medir» en lugar de inventarlo");
    }

    /* ------------------------------------------------------------ el clima real */

    /**
     * Los dos servicios sin clave que ya usa `cort_server.py` en la PC: la búsqueda
     * de ciudad y el parte. Misma dirección, mismos campos, mismo orden. La ciudad
     * sale de lo que la página guardó en Ajustes; si no hay ninguna, se pregunta por
     * la IP, igual que allí.
     *
     * Con `ipapi` se respeta la lección del puente: su ruta `/{nombre}/json/` pide
     * una IP y con un nombre contesta `{"error": true}`, así que sólo se usa cuando
     * NO hay ciudad escrita. Y si nada sale, **no se manda el panel**: `Yg()` de la
     * cara hace `t.ville.toUpperCase()` sin comprobar, y un cuadro roto en vez de
     * ningún cuadro sería un error de consola y un panel con «undefined». Lo que
     * hace la PC —devolver la frase honesta y dejar el panel como estaba— es lo que
     * se reproduce aquí.
     */
    private void clima(final String pedida) {
        new Thread(() -> {
            String ciudad = pedida == null || pedida.trim().isEmpty()
                    ? prefs.getString(CLAVE_CIUDAD, "") : pedida.trim();
            try {
                JSONObject parte = ciudad.trim().isEmpty() ? porIp() : parte(ciudad);
                envia(cuadro("type", "weather_panel", "data", parte, "origen", "real",
                        "ciudad_pedida", parte.optString("ville", ciudad)));
            } catch (Exception noLlega) {
                // Última coordenada buena, como el `aviso` del puente de la PC.
                if (lat != 0.0 || lon != 0.0) {
                    try {
                        JSONObject parte = parteDe(lat, lon,
                                prefs.getString(CLAVE_CIUDAD, "tu ubicación por IP"), true);
                        envia(cuadro("type", "weather_panel", "data", parte, "origen", "real"));
                        return;
                    } catch (Exception tampoco) {
                        dice("No pude leer el clima real: " + tampoco);
                        return;
                    }
                }
                dice("No pude leer el clima real: " + noLlega);
            }
        }, "cort-clima").start();
    }

    /** Sin ciudad escrita: la ubicación que da la propia IP, igual que `resolver_ubicacion`. */
    private JSONObject porIp() throws IOException, JSONException {
        String geo = lee("https://ipapi.co/json/");
        JSONObject j = new JSONObject(geo);
        if (j.optBoolean("error", false)) {
            throw new IOException("ipapi dijo «" + j.optString("reason", "no respondió") + "»");
        }
        double la = j.getDouble("latitude");
        double lo = j.getDouble("longitude");
        String nombre = j.optString("city", "");
        lat = la;
        lon = lo;
        return parteDe(la, lo, nombre.isEmpty() ? "tu ubicación" : nombre, false);
    }

    private JSONObject parte(String ciudad) throws IOException, JSONException {
        String geo = lee("https://geocoding-api.open-meteo.com/v1/search?count=1&language=es&name="
                + Uri.encode(ciudad));
        JSONArray resultados = new JSONObject(geo).optJSONArray("results");
        if (resultados == null || resultados.length() == 0) {
            throw new IOException("la ciudad «" + ciudad + "» no apareció en el buscador");
        }
        JSONObject donde = resultados.getJSONObject(0);
        double la = donde.getDouble("latitude");
        double lo = donde.getDouble("longitude");
        String nombre = donde.optString("name", ciudad);
        lat = la;
        lon = lo;
        return parteDe(la, lo, nombre, false);
    }

    /** Coordenadas -> open-meteo -> el cuadro exacto que pinta `Yg()`. */
    private JSONObject parteDe(double la, double lo, String nombre, boolean deCache)
            throws IOException, JSONException {
        String datos = lee("https://api.open-meteo.com/v1/forecast?latitude=" + la
                + "&longitude=" + lo
                + "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
                + "weather_code,wind_speed_10m&timezone=auto");
        JSONObject actual = new JSONObject(datos).optJSONObject("current");
        if (actual == null) {
            throw new IOException("el parte no traía la hora actual");
        }
        int codigo = actual.optInt("weather_code", -1);
        return cuadro("ok", true, "origen", "open-meteo medido desde el teléfono",
                "ville", nombre,
                "temperature", actual.optDouble("temperature_2m", 0.0),
                "ressenti", actual.optDouble("apparent_temperature", 0.0),
                "humidite", actual.optDouble("relative_humidity_2m", 0.0),
                "vent", actual.optDouble("wind_speed_10m", 0.0),
                "code", codigo,
                "description", descripcionDe(codigo),
                "resolucion", "600 s",
                "desde_cache", deCache,
                "aviso", deCache ? "el punto del mapa es la última ubicación leída, "
                        + "no la que acabas de pedir" : "",
                "coordenadas", cuadro("lat", la, "lon", lo));
    }

    private static String descripcionDe(int codigo) {
        switch (codigo) {
            case 0: return "despejado";
            case 1: return "mayormente despejado";
            case 2: return "parcialmente nublado";
            case 3: return "nublado";
            case 45: case 48: return "niebla";
            case 51: case 53: case 55: return "llovizna";
            case 56: case 57: return "llovizna helada";
            case 61: return "lluvia débil";
            case 63: return "lluvia";
            case 65: return "lluvia fuerte";
            case 66: case 67: return "lluvia helada";
            case 71: return "nevada débil";
            case 73: return "nevada";
            case 75: return "nevada fuerte";
            case 77: return "granos de nieve";
            case 80: return "chubascos débiles";
            case 81: return "chubascos";
            case 82: return "chubascos fuertes";
            case 85: case 86: return "chubascos de nieve";
            case 95: return "tormenta";
            case 96: case 99: return "tormenta con granizo";
            default: return "sin código";
        }
    }

    private static String lee(String url) throws IOException {
        HttpURLConnection conexion = (HttpURLConnection) new URL(url).openConnection();
        conexion.setConnectTimeout(8000);
        conexion.setReadTimeout(12000);
        conexion.setRequestProperty("User-Agent", "CORT-movil");
        try (InputStream entrada = conexion.getInputStream()) {
            ByteArrayOutputStream fuera = new ByteArrayOutputStream();
            byte[] trozo = new byte[8192];
            int n;
            while ((n = entrada.read(trozo)) > 0) {
                fuera.write(trozo, 0, n);
            }
            return fuera.toString("UTF-8");
        } finally {
            conexion.disconnect();
        }
    }

    /* ---------------------------------------------------------------- ajustes */

    /**
     * Lo que la página escribe en Ajustes viaja por `update_settings`: aquí sólo se
     * guarda lo que Java necesita para responder (la ciudad del clima y los
     * pendientes de la tarjeta de vida). El resto vive en su `localStorage`.
     */
    private void cacheaAjustes(JSONObject ajustes) {
        if (ajustes == null) {
            return;
        }
        String ciudad = ajustes.optString("user_city", "");
        if (!ciudad.isEmpty()) {
            prefs.edit().putString(CLAVE_CIUDAD, ciudad).apply();
        }
        JSONArray recordatorios = ajustes.optJSONArray("reminders");
        if (recordatorios != null) {
            prefs.edit().putString(CLAVE_RECORDATORIOS, recordatorios.toString()).apply();
        }
        // `wake_word` y `voice` se guardan en la página; el oído del teléfono usa la
        // gramática de `Motor` y la voz del sistema, así que no se copian aquí.
    }

    /* ------------------------------------------------------------------ el oído */

    /**
     * El micrófono de esta cara es el de Android: el WebView no expone
     * `SpeechRecognition` y en origen no seguro tampoco `getUserMedia`. Si el oído
     * local de Vosk está montado manda él; si no, el reconocedor del sistema.
     */
    @JavascriptInterface
    public void escuchar() {
        actividad.runOnUiThread(() -> {
            if (actividad.checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)
                    != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                actividad.requestPermissions(
                        new String[] {android.Manifest.permission.RECORD_AUDIO}, 42);
                return;
            }
            envia(cuadro("state", "listening"));
            Voz.AlOir oyente = new Voz.AlOir() {
                @Override
                public void dijo(String texto) {
                    escuchando = false;
                    envia(cuadro("type", "mic_texto", "texto", texto, "origen", "real"));
                    envia(micEstado());
                    new Thread(() -> conversar(texto), "cort-lazo").start();
                }

                @Override
                public void fallo(String motivo) {
                    escuchando = false;
                    envia(cuadro("type", "mic_error", "origen", "real", "motivo", motivo));
                    envia(cuadro("state", "idle"));
                }
            };
            Motor oido = Motor.compartido(actividad.getApplicationContext());
            if (oido.listo()) {
                escuchando = true;
                oido.escuchar(oyente, alto -> midiendo(alto));
            } else {
                escuchando = true;
                voz.ponerNivel(alto -> midiendo(alto));
                voz.escuchar(actividad, oyente);
            }
        });
    }

    @JavascriptInterface
    public void callar() {
        escuchaContinua = false;
        actividad.runOnUiThread(() -> {
            voz.dejarDeEscuchar();
            Motor.compartido(actividad.getApplicationContext()).para();
            envia(micEstado());
        });
    }

    /** La voz del teléfono, con las reglas de `Voz`: español y las voces preferidas. */
    @JavascriptInterface
    public void hablar(final String texto) {
        if (texto == null || texto.trim().isEmpty()) {
            return;
        }
        actividad.runOnUiThread(() -> voz.hablar(texto));
    }

    /**
     * El nivel real del micrófono. No va en un cuadro —la cara de la PC no tiene
     * `state.nivel`— sino directo al orbe, que es lo que en el portátil produce el
     * analizador de audio de la página y aquí produce `onRmsChanged`.
     */
    private void midiendo(float alto) {
        long ahora = System.currentTimeMillis();
        if (ahora - ultimoNivel < 120L) {
            return;
        }
        ultimoNivel = ahora;
        final WebView ventana = web;
        if (ventana == null) {
            return;
        }
        final double v = Math.max(0.0, Math.min(1.0, alto));
        actividad.runOnUiThread(() -> ventana.evaluateJavascript(
                "window.CORT_orbe&&window.CORT_orbe.volumen(" + v + ")", null));
    }

    /* ------------------------------------------------------------- el bombeo */

    private void bombea() {
        while (corriendo) {
            envia(sistemaStats());
            duerme(4000);
        }
    }

    private void duerme(long milisegundos) {
        try {
            Thread.sleep(milisegundos);
        } catch (InterruptedException cortada) {
            corriendo = false;
            Thread.currentThread().interrupt();
        }
    }

    /* --------------------------------------------- servir la cara (todo puro) */

    private static boolean esDeLaCara(String url) {
        return url != null && url.startsWith(ORIGEN + "/");
    }

    /**
     * De la dirección a la ruta del `asset`, o `null` si no es de la cara. Es la
     * única puerta a los archivos del APK desde la página, así que la lista es
     * cerrada: raíz exacta o las cuatro carpetas del bundle, y nunca un `..`.
     */
    public static String rutaDe(String url) {
        if (url == null || !url.startsWith(ORIGEN + "/")) {
            return null;
        }
        String camino = url.substring(ORIGEN.length() + 1);
        int interrogacion = camino.indexOf('?');
        if (interrogacion >= 0) {
            camino = camino.substring(0, interrogacion);
        }
        int almohadilla = camino.indexOf('#');
        if (almohadilla >= 0) {
            camino = camino.substring(0, almohadilla);
        }
        if (camino.isEmpty()) {
            camino = "index.html";
        }
        if (camino.contains("..") || camino.startsWith("/")) {
            return null;
        }
        boolean permitido = false;
        for (String exacta : RAICES) {
            if (exacta.equals(camino)) {
                permitido = true;
            }
        }
        for (String carpeta : PREFIJOS) {
            if (camino.startsWith(carpeta)) {
                permitido = true;
            }
        }
        return permitido ? CARPETA + camino : null;
    }

    /** El tipo de contenido, por extensión y sin preguntar al sistema. */
    public static String mimeDe(String ruta) {
        int punto = ruta.lastIndexOf('.');
        String ext = punto < 0 ? "" : ruta.substring(punto + 1).toLowerCase(Locale.ROOT);
        switch (ext) {
            case "html": return "text/html";
            case "js": return "text/javascript";
            case "css": return "text/css";
            case "json": return "application/json";
            case "webmanifest": return "application/manifest+json";
            case "svg": return "image/svg+xml";
            case "png": return "image/png";
            case "jpg": return "image/jpeg";
            case "webp": return "image/webp";
            case "ico": return "image/x-icon";
            case "woff": return "font/woff";
            case "woff2": return "font/woff2";
            default: return "application/octet-stream";
        }
    }

    /**
     * Una cadena dentro de un JSON. Sin esto, un `"` en un recuerdo rompe el
     * cuadro y `JSON.parse` deja la frase sin contestar.
     */
    public static String escapa(String texto) {
        if (texto == null) {
            return "";
        }
        StringBuilder salida = new StringBuilder(texto.length() + 8);
        for (int i = 0; i < texto.length(); i++) {
            char c = texto.charAt(i);
            if (c == '"' || c == '\\') {
                salida.append('\\').append(c);
            } else if (c == '\n') {
                salida.append("\\n");
            } else if (c == '\r') {
                salida.append("\\r");
            } else if (c == '\t') {
                salida.append("\\t");
            } else if (c < 0x20) {
                salida.append(String.format(Locale.ROOT, "\\u%04x", (int) c));
            } else {
                salida.append(c);
            }
        }
        return salida.toString();
    }

    /**
     * El número como lo quiere JSON, **con `Locale.ROOT`**: en un teléfono con
     * idioma español `String.format("%.2f", 0.4)` da `0,4` y una coma en un cuadro
     * lo revienta del otro lado.
     */
    public static String numeroDe(float valor) {
        return String.format(Locale.ROOT, "%.2f", valor);
    }

    private WebResourceResponse sirve(String ruta) {
        try {
            InputStream datos = actividad.getAssets().open(ruta);
            return new WebResourceResponse(mimeDe(ruta), "utf-8", datos);
        } catch (IOException noEsta) {
            // La cara no viajó en el APK (un compilado sin la fase F19): se responde
            // 404 en vez de dejar que el WebView salga a la red tras un host falso.
            return noExiste();
        }
    }

    /**
     * `index.html` con el puente Java metido detrás de `<head>`. Se lee entero a
     * memoria —son 90 KB medidos— porque la costura es una cadena y el WebView no
     * deja insertar en medio de un `InputStream`.
     */
    private WebResourceResponse sirveConPuente(String ruta) {
        try (InputStream entrada = actividad.getAssets().open(ruta)) {
            ByteArrayOutputStream fuera = new ByteArrayOutputStream();
            byte[] trozo = new byte[16384];
            int n;
            while ((n = entrada.read(trozo)) > 0) {
                fuera.write(trozo, 0, n);
            }
            String html = fuera.toString("UTF-8");
            int cabe = html.toLowerCase(Locale.ROOT).indexOf("<head>");
            String cosido;
            if (cabe >= 0) {
                int despues = cabe + "<head>".length();
                cosido = html.substring(0, despues) + ETIQUETA_PUENTE + html.substring(despues);
            } else {
                cosido = ETIQUETA_PUENTE + html;
            }
            return new WebResourceResponse("text/html", "utf-8",
                    new ByteArrayInputStream(cosido.getBytes(StandardCharsets.UTF_8)));
        } catch (IOException noEsta) {
            return noExiste();
        }
    }

    private static WebResourceResponse noExiste() {
        Map<String, String> cabeceras = new HashMap<>();
        return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found",
                cabeceras, new ByteArrayInputStream(new byte[0]));
    }

    /* -------------------------------------------------------------- JSON sin ruido */

    /**
     * `JSONObject.put` en Android lanza `JSONException` **comprobada**. Aquí las
     * claves son literales y los valores texto, número o booleano —nunca un `NaN`,
     * que es lo único que la dispara—, así que se atrapa una vez dentro de `pone`
     * en vez de ensuciar las cuarenta firmas que arman cuadros.
     *
     * Acepta varios pares `clave, valor` de una vez, que es como lo llaman las
     * ramas que rellenan una respuesta entera después de armarla.
     */
    private static JSONObject pone(JSONObject j, Object... pares) {
        for (int i = 0; i + 1 < pares.length; i += 2) {
            try {
                Object v = pares[i + 1];
                j.put(String.valueOf(pares[i]), v == null ? JSONObject.NULL : v);
            } catch (JSONException imposible) {
                // clave vacía: ningún cuadro de abajo la produce
            }
        }
        return j;
    }

    /** `cuadro("a", 1, "b", "x")` → `{"a":1,"b":"x"}`. Los pares sueltos se ignoran. */
    private static JSONObject cuadro(Object... pares) {
        JSONObject j = new JSONObject();
        for (int i = 0; i + 1 < pares.length; i += 2) {
            pone(j, String.valueOf(pares[i]), pares[i + 1]);
        }
        return j;
    }

    private static JSONArray puso(JSONArray lista, Object valor) {
        // `JSONArray.put(Object)` no declara `JSONException`: envolverlo en un
        // `try/catch` es error de compilación («never thrown»), así que la lista
        // se llena directo y nunca se devuelve `null` por el camino.
        lista.put(valor == null ? JSONObject.NULL : valor);
        return lista;
    }

    /**
     * Un arreglo guardado como texto de preferencia. `new JSONArray(String)` lanza
     * `JSONException` **comprobada**, y lo que hay en `SharedPreferences` lo escribió
     * la página: si un día quedó cortado a medias, el panel se queda vacío en vez de
     * tumbar el puente.
     */
    private static JSONArray arregloDe(String guardado) {
        try {
            return new JSONArray(guardado == null || guardado.isEmpty() ? "[]" : guardado);
        } catch (JSONException roto) {
            return new JSONArray();
        }
    }

    private void envia(final JSONObject cuadro) {
        final WebView ventana = web;
        if (ventana == null) {
            return;
        }
        final String texto = cuadro.toString();
        // `evaluateJavascript` es del hilo de la interfaz, y esto se llama desde el
        // hilo del lazo, del de la descarga y del bombeo de estadísticas.
        actividad.runOnUiThread(() -> ventana.evaluateJavascript(
                "window.__cortNative&&window.__cortNative.emit(" + texto + ")", null));
    }
}
