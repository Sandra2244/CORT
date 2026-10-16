package dev.sandra.cort;

import android.app.Activity;
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
import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * La cara del portátil dentro del teléfono, sin portátil.
 *
 * Desde `v0.17.0` el APK lleva consigo el `dist` de `apps/web` (los mismos
 * archivos que serve `cort.py --lan`) y los abre en un `WebView` propio. Eso es
 * lo que la dueña pidió con una frase que no admite interpretación: «es
 * literalmente replicar todo el de PC, compilado a Android». No es un parecido:
 * es el mismo React, el mismo orbe de tres.js y los mismos paneles.
 *
 * Dos decisiones que no son de gusto, sino de física:
 *
 * 1. **Un origen inventado y cortado, no `file://`.** El `dist` de Vite es un
 *    módulo ES, y Chromium bloquea un módulo ES cargado desde `file://` por CORS
 *    — pantalla en blanco—. La otra salida sería un servidor HTTP local con su
 *    socket y su puerto abierto en el aparato; se opta por lo tercero: la página
 *    vive en `https://cort.local`, un host que no existe, y cada petición que el
 *    WebView intenta hacer contra él se corta en `shouldInterceptRequest` y se
 *    sirve desde los `assets`. No sale ni un byte del teléfono, y no hay nada que
 *    escuchar.
 *
 * 2. **El cerebro es el de siempre.** Detrás del cristal no hay un core de
 *    Python: está `Cerebro` (la tabla de `assets/habilidades.json`), `Acciones`
 *    (las quince intenciones), `Recuerdos` (SQLite) y `Voz` (el `TextToSpeech`
 *    `es-CO` elegido con las mismas reglas de `apps/web/src/cort/voz.ts`). La
 *    página habla por `window.Nexo`, y Java devuelve los **mismos cuadros** que
 *    viajan por el WebSocket del portátil: un manejador en el cliente
 *    (`maneja`, en `connection.ts`), dos transportes. Lo que se gana es que una
 *    actualización de la cara no obligue a reescribir la del teléfono.
 *
 * La cara nativa de `Cara.java` —con su orbe de `Canvas`— sigue ahí y es el
 * respaldo: si el `WebView` no arranca, si el `dist` no viajó en el APK o si
 * Android se niega, la dueña ve CORT igualmente. Y el lazo de esta clase
 * **no** sustituye al de `Cara`: lo duplica en pequeño (tabla → acción → nube),
 * con la tabla y las acciones compartidas de verdad. La extracción de un `Lazo`
 * único para las dos caras está apuntada como deuda en `docs/STATUS.md`, no como
 * algo que ya sea.
 */
public class Nexo {
    /** El origen inventado. No se resuelve: se intercepta. */
    public static final String ORIGEN = "https://cort.local";
    public static final String INDICE = ORIGEN + "/index.html";

    /** La carpeta del `dist` dentro de los `assets` del APK, y su nombre suelto. */
    static final String DOSSIER = "web";
    static final String CARPETA = DOSSIER + "/";

    /**
     * Lo único que se sirve del `dist`: la raíz exacta y estas dos carpetas. La
     * lista es cerrada a propósito —es la regla 6 del repo aplicada a un archivo—
     * y `rutaDe` devuelve `null` con cualquier otra cosa, incluido un `..`.
     */
    static final String[] RAICES = {"index.html", "manifest.webmanifest", "favicon.ico"};
    static final String[] PREFIJOS = {"assets/", "icons/"};

    private final Activity actividad;
    private final Runnable seCayo;      // la cara nativa, si esto no levanta
    private WebView web;
    private final Recuerdos recuerdos;
    private final Cerebro cerebro;
    private final Acciones acciones;
    private final Voz voz;
    private final Nube nube;
    private boolean pensando;
    private float nivel;
    private long ultimoNivel;

    public Nexo(Activity actividad, Runnable seCayo) {
        this.actividad = actividad;
        this.seCayo = seCayo;
        this.recuerdos = new Recuerdos(actividad);
        this.cerebro = new Cerebro(actividad, recuerdos);
        this.acciones = new Acciones(actividad, recuerdos);
        this.voz = new Voz(actividad);
        this.nube = new Nube(actividad);
        // Los datos del aparato, la primera vez, sin que nadie los teclee: la
        // misma siembra de `Cara.sembrar()`, para que el teléfono que abre esta
        // cara sepa ya quién es su dueña y en qué aparato está.
        recuerdos.sembrarDispositivo("teléfono",
                android.os.Build.MANUFACTURER + " " + android.os.Build.MODEL);
        recuerdos.sembrarDispositivo("android", "API " + android.os.Build.VERSION.SDK_INT);
    }

    /* ------------------------------------------------------------------ montar */

    public void montar(LinearLayout capa) {
        web = new WebView(actividad);
        // Oscuro desde el primer fotograma, como la ventana del portátil: sin esto
        // el WebView pinta su fondo blanco antes de que la cara arranque.
        web.setBackgroundColor(Paleta.FONDO);
        capa.removeAllViews();
        capa.addView(web, new LinearLayout.LayoutParams(-1, -1));
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        // `speechSynthesis` no se usa en esta cara (habla Java), pero el pitido de
        // «te oí» de `voz.ts` sí es reproducción, y sin esta línea Android la
        // condiciona a un dedo encima.
        s.setMediaPlaybackRequiresUserGesture(false);
        // `setAllowFileAccess` se queda en su defecto: **no** se abre el disco. Lo
        // que lee esta cara es `getAssets()`, por mano propia y con la lista
        // cerrada de `rutaDe`, que es más estrecho que el permiso de archivo.
        web.addJavascriptInterface(this, "Nexo");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView vista,
                                                              WebResourceRequest peticion) {
                if (!esDeLaCara(peticion.getUrl().toString())) {
                    return null;   // no es nuestro origen: que lo resuelva Android
                }
                String ruta = rutaDe(peticion.getUrl().toString());
                return ruta == null ? noExiste() : sirve(ruta);
            }

            @Override
            public void onPageFinished(WebView vista, String url) {
                // `window.cortRecibe` ya existe: es el momento de saludar, y no
                // antes. Empezar por el saludo sin esperar aquí era mandar un cuadro
                // contra un `undefined` y perderlo. Es de `WebViewClient` —en
                // `WebChromeClient` no existe—, y eso no se supo de memoria: lo
                // dijo `scripts/simbolos_android.py` al no encontrarlo.
                if (esDeLaCara(url)) {
                    saludo();
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
                // `defocus.ts` pide la cámara y el micrófono de la página. Se
                // concede lo que hay dentro de lo que el manifiesto declaró, como ya
                // hace la ventana del portátil.
                pedido.grant(pedido.getResources());
            }
        });
        web.loadUrl(INDICE);
    }

    public void cerrar() {
        voz.cerrar();
        web = null;
    }

    /** El estado del aparato, en cuanto la cara está montada. */
    private void saludo() {
        String nombre = recuerdos.valor("nombre");
        dice(nombre == null || nombre.isEmpty()
                ? "Hola, soy CORT en tu teléfono."
                : "Hola de nuevo, " + nombre + ".");
        thinking(false);
        envia("{\"type\":\"status\",\"memories\":" + recuerdos.cuentasDeHechos()
                + ",\"keep\":200"
                + ",\"brain\":" + (nube.configurada() ? "\"" + escapa(nube.modelo()) + "\"" : "null")
                + ",\"ollama\":false,\"actions\":true,\"iniciativa\":false}");
        // `keep: 200` es el techo con el que se poda la memoria del core (fase 1.1
        // del ROADMAP), y `iniciativa: false` dice la verdad de este cuerpo: el
        // teléfono todavía no habla por su cuenta.
    }

    /* ---------------------------------------------------------------- lazo */

    /** Lo que la página teclea o dicta. Llega al hilo del JS: hay que subirlo. */
    @JavascriptInterface
    public void enviar(final String texto) {
        if (texto == null) {
            return;
        }
        final String dicho = texto.trim();
        if (dicho.isEmpty()) {
            return;
        }
        actividad.runOnUiThread(() -> procesar(dicho));
    }

    private void procesar(final String dicho) {
        thinking(true);
        List<Cerebro.Resultado> pasos = cerebro.cadena(dicho);
        if (pasos.size() > 1) {
            encadenar(pasos);
            return;
        }
        Cerebro.Resultado r = pasos.isEmpty() ? null : pasos.get(0);
        if (r != null) {
            String respuesta = acciones.ejecutar(r);
            if (respuesta != null) {
                envia("{\"type\":\"intent\",\"action\":\"" + escapa(r.accion) + "\"}");
                responde(respuesta);
                return;
            }
            responde("¿Cómo? Necesito el dato: pruébalo con «" + pideEjemplo(r) + "».");
            return;
        }
        porNube(dicho);
    }

    private void encadenar(List<Cerebro.Resultado> pasos) {
        StringBuilder texto = new StringBuilder();
        for (Cerebro.Resultado paso : pasos) {
            String respuesta = acciones.ejecutar(paso);
            if (respuesta == null) {
                responde("¿Cómo? Necesito el dato: pruébalo con «" + pideEjemplo(paso) + "».");
                return;
            }
            if (texto.length() > 0) {
                texto.append(" ");
            }
            texto.append(respuesta);
        }
        responde(texto.toString());
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
     * Lo que la tabla no conoce va a la nube **en su propio hilo**, igual que en
     * `Cara.porNube`: `HttpURLConnection` bloquea, y una cara congelada es peor
     * que una cara que dice «no la conozco».
     */
    private void porNube(final String dicho) {
        if (!nube.configurada()) {
            // Aquí la cara del teléfono dice lo que sabe hacer, en vez de abrir el
            // lazo de aprender: elegir la acción nueva es una pantalla que todavía
            // sólo existe en `Cara.java`. Está escrito en el README, no callado.
            responde("Esa frase no la conozco sin el portátil. Sé hacer: "
                    + String.join(", ", cerebro.acciones()) + ".");
            thinking(false);
            return;
        }
        final String memoria = recuerdos.lista(12);
        new Thread(() -> {
            final String respuesta = nube.preguntar(dicho, memoria);
            actividad.runOnUiThread(() -> {
                if (respuesta == null) {
                    thinking(false);
                    responde("La nube no respondió: " + nube.ultimoFallo());
                    return;
                }
                responde(respuesta);
            });
        }).start();
    }

    private void responde(String texto) {
        thinking(false);
        dice(texto);
        voz.hablar(texto);
    }

    /* ------------------------------------------------------ lo que pide la página */

    /**
     * El micrófono de esta cara es el de Android, no el de la página: el WebView
     * no expone `SpeechRecognition`, así que sin este camino el botón de hablar
     * no haría nada. Lo que se reconoce vuelve como cuadro `user_message` y se
     * procesa aquí mismo.
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
            thinking(false);
            voz.ponerNivel(alto -> midiendo(alto));
            voz.escuchar(actividad, new Voz.AlOir() {
                @Override
                public void dijo(String texto) {
                    envia("{\"type\":\"user_message\",\"text\":\"" + escapa(texto) + "\"}");
                    // Al hilo de arriba: `procesar` mueve `startActivity`, y el
                    // aviso del reconocedor no promete venir en él.
                    actividad.runOnUiThread(() -> procesar(texto));
                }

                @Override
                public void fallo(String motivo) {
                    dice("No te oí: " + motivo);
                }
            });
        });
    }

    @JavascriptInterface
    public void callar() {
        actividad.runOnUiThread(() -> voz.dejarDeEscuchar());
    }

    /** La voz del teléfono, con las reglas de `voz.ts`: `es-CO` y las preferidas. */
    @JavascriptInterface
    public void hablar(final String texto) {
        if (texto == null || texto.trim().isEmpty()) {
            return;
        }
        actividad.runOnUiThread(() -> voz.hablar(texto));
    }

    /**
     * Offline no hay `.vrm` en el APK —regla 7: nada de modelos en el repo—, y por
     * eso esto responde una lista vacía en vez de colgar la cara esperando un
     * `avatars` que no llega. El cuerpo 3D se ve cuando el portátil está delante.
     */
    @JavascriptInterface
    public void pedirAvatares() {
        actividad.runOnUiThread(() -> envia("{\"type\":\"avatars\",\"items\":[]}"));
    }

    /* ---------------------------------------------------------------- cuadros */

    private void envia(String cuadro) {
        final WebView ventana = web;
        if (ventana == null) {
            return;
        }
        // `evaluateJavascript` es del hilo de la interfaz, y `envia` se llama desde
        // el hilo de la nube y desde el del reconocedor.
        actividad.runOnUiThread(() ->
                ventana.evaluateJavascript("window.cortRecibe && window.cortRecibe(" + cuadro + ")", null));
    }

    private void dice(String texto) {
        envia("{\"type\":\"assistant_message\",\"text\":\"" + escapa(texto) + "\"}");
    }

    private void thinking(boolean alto) {
        pensando = alto;
        envia("{\"type\":\"state\",\"thinking\":" + (alto ? "true" : "false") + "}");
    }

    /**
     * El nivel real del micrófono, que el portátil simula y el teléfono **sí
     * puede medir** (`onRmsChanged`). Viaja en el mismo cuadro `state` porque
     * `applyState` pinta el reactor con lo que ahí venga; se manda poco (cada
     * 120 ms) porque cada cuadro es un `evaluateJavascript`.
     */
    private void midiendo(float alto) {
        nivel = Math.max(0f, Math.min(1f, alto));
        long ahora = System.currentTimeMillis();
        if (ahora - ultimoNivel < 120L) {
            return;
        }
        ultimoNivel = ahora;
        envia("{\"type\":\"state\",\"thinking\":" + (pensando ? "true" : "false")
                + ",\"nivel\":" + numeroDe(nivel) + "}");
    }

    /* --------------------------------------------- servir el `dist` (todo puro) */

    private static boolean esDeLaCara(String url) {
        return url != null && url.startsWith(ORIGEN + "/");
    }

    /**
     * De la dirección a la ruta del `asset`, o `null` si no es del `dist`. Es la
     * única puerta a los archivos del APK desde la red, así que la lista es
     * cerrada: raíz exacta o las dos carpetas del bundle, y nunca un `..`.
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
     * cuadro y `JSON.parse` deja la frase sin contestar. `Locale` no importa aquí;
     * lo que importa es el control de `v0.17.0`: el texto que CORT dice lleva
     * comillas, y el nombre de la dueña también.
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
     * El número como lo quiere JSON. **Con `Locale.ROOT` y no con el del aparato**:
     * en un teléfono con idioma español `String.format("%.2f", 0.4)` da `0,4`, y
     * una coma en un cuadro JSON lo revienta del otro lado. Es la diferencia entre
     * un CORT que anima el orbe y uno que no contesta.
     */
    public static String numeroDe(float valor) {
        return String.format(Locale.ROOT, "%.2f", valor);
    }

    private WebResourceResponse sirve(String ruta) {
        try {
            InputStream datos = actividad.getAssets().open(ruta);
            return new WebResourceResponse(mimeDe(ruta), "utf-8", datos);
        } catch (IOException noEsta) {
            // El `dist` no viajó en el APK (un compilado sin `npm run build`): se
            // responde 404 en vez de dejar que el WebView salga a la red tras un
            // host que no existe.
            return noExiste();
        }
    }

    private static WebResourceResponse noExiste() {
        Map<String, String> cabeceras = new HashMap<>();
        return new WebResourceResponse("text/plain", "utf-8", 404, "Not Found",
                cabeceras, new ByteArrayInputStream(new byte[0]));
    }
}
