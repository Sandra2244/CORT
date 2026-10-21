package com.cort.ia;

/*
 * La mitad de nube de CORT: pensar por internet cuando el portátil está apagado.
 *
 * Porte de `dev.sandra.cort.Nube` (la línea hermana CORT-TELEFONO), con la lista
 * de proveedores ENSANCHADA y los nombres adaptados al contrato del puente 2.1
 * (`docs/CONTRATO-PUENTE-2.1.md`, sección 4 · `mente`). Los ajustes viven en
 * `SharedPreferences` (`cort`, las mismas preferencias que usa `MainActivity`)
 * bajo las claves `nube-proveedor`, `nube-base`, `nube-modelo`, `nube-clave`.
 *
 * Tres verdades escritas antes del código:
 *
 * 1. **La clave no sale del teléfono.** `estado` jamás enseña el valor: sólo
 *    `clavePuesta` (booleano) y, como mucho, su longitud. Ni en la cara, ni en
 *    los logs, ni en `ultimoFallo`.
 * 2. **La red no va en el hilo del puente.** Ningún método de esta clase hace
 *    HTTP por sí mismo en el hilo de `@JavascriptInterface`: `mente` despacha
 *    `estado`/`ajustar` (sin red) y `probar`/`preguntar` contestan enseguida con
 *    `{"pendiente":true}`. El que dispara el hilo es `Mente`. Un
 *    `NetworkOnMainThreadException` aquí tiraría la app entera.
 * 3. **Nube es un añadido, nunca un requisito.** Cualquier fallo —sin internet,
 *    cuota, 401, timeout— deja `ultimoFallo` escrito y devuelve `null`; la cara
 *    sigue respondiendo con la tabla local de `Cerebro`.
 *
 * HTTP claro: `HttpURLConnection` con `https` normal y timeouts de 8 s de conexión
 * y 25 s de lectura. Para `ollama` (el modelo local del PC) la base es
 * `http://127.0.0.1:11434/v1`, que es texto plano (`http`) contra localhost; eso
 * sólo funciona porque el manifiesto declara `android:usesCleartextTraffic` para
 * el loopback. Sin esa bandera del manifiesto, Android bloquearía la llamada.
 */

import android.content.Context;
import android.content.SharedPreferences;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.util.Log;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

public class Nube {

    private static final int CONEXION_MS = 8000;
    private static final int LECTURA_MS = 25000;

    /** Las claves donde `MainActivity` ya guarda todo lo de CORT. */
    private final SharedPreferences prefs;
    private final Context app;

    private String ultimoFallo = "";

    /* ─────────────────────────── proveedores ────────────────────── */

    /** Un proveedor conocido: base por defecto, modelo por defecto, estilo y si exige clave. */
    static final class Proveedor {
        final String id, base, modelo, estilo;    // estilo: "openai" o "anthropic"
        final boolean conClave;
        Proveedor(String id, String base, String modelo, String estilo, boolean conClave) {
            this.id = id; this.base = base; this.modelo = modelo;
            this.estilo = estilo; this.conClave = conClave;
        }
    }

    private static final Map<String, Proveedor> CATALOGO = new LinkedHashMap<>();
    static {
        // Bases REALES de cada casa, con el modelo por defecto que la dueña pidió.
        CATALOGO.put("groq",      new Proveedor("groq", "https://api.groq.com/openai/v1",
                                                "llama-3.1-8b-instant", "openai", true));
        CATALOGO.put("openai",    new Proveedor("openai", "https://api.openai.com/v1",
                                                "gpt-4o-mini", "openai", true));
        CATALOGO.put("deepseek",  new Proveedor("deepseek", "https://api.deepseek.com/v1",
                                                "deepseek-chat", "openai", true));
        CATALOGO.put("mistral",   new Proveedor("mistral", "https://api.mistral.ai/v1",
                                                "mistral-small-latest", "openai", true));
        CATALOGO.put("qwen",      new Proveedor("qwen",
                                                "https://dashscope.aliyuncs.com/compatible-mode/v1",
                                                "qwen-plus", "openai", true));
        // El modelo local del PC: sin clave, y en claro (http) sólo por localhost.
        CATALOGO.put("ollama",    new Proveedor("ollama", "http://127.0.0.1:11434/v1",
                                                "llama3.2", "openai", false));
        CATALOGO.put("anthropic", new Proveedor("anthropic", "https://api.anthropic.com/v1/messages",
                                                "claude-3-5-sonnet-20241022", "anthropic", true));
    }

    /** La lista de motores que la cara puede elegir (para `estado`). */
    public static List<String> motores() {
        return new ArrayList<>(CATALOGO.keySet());
    }

    /* ───────────────────────────── construcción ─────────────────── */

    public Nube(Context contexto) {
        this.app = contexto.getApplicationContext();
        this.prefs = app.getSharedPreferences("cort", Context.MODE_PRIVATE);
    }

    /* ───────────────────────────── getters ──────────────────────── */

    public String proveedor() {
        return prefs.getString("nube-proveedor", "groq");
    }

    public String base() {
        Proveedor p = CATALOGO.get(proveedor());
        String guardada = prefs.getString("nube-base", "");
        if (!guardada.isEmpty()) return guardada;
        return p == null ? "" : p.base;
    }

    public String modelo() {
        Proveedor p = CATALOGO.get(proveedor());
        String guardada = prefs.getString("nube-modelo", "");
        if (!guardada.isEmpty()) return guardada;
        return p == null ? "" : p.modelo;
    }

    /** La clave real: sólo se usa dentro de esta clase para firmar la petición. */
    public String clave() {
        return prefs.getString("nube-clave", "");
    }

    public String ultimoFallo() {
        return ultimoFallo;
    }

    /** Configurada = hay base y modelo, y clave si el proveedor la exige (ollama no). */
    public boolean configurada() {
        if (base().isEmpty() || modelo().isEmpty()) return false;
        Proveedor p = CATALOGO.get(proveedor());
        boolean necesitaClave = p == null || p.conClave;
        return !necesitaClave || !clave().isEmpty();
    }

    /* ───────────────────────────── ajustar ──────────────────────── */

    /**
     * Escribe los ajustes. `clave` vacía = NO tocar la guardada (contrato §4).
     * Si cambia el proveedor y no se trae base/modelo, se ponen sus defectos.
     */
    public void ajustar(String proveedorNuevo, String baseNueva, String modeloNuevo, String claveNueva) {
        SharedPreferences.Editor e = prefs.edit();
        String prov = proveedor(proveedorNuevo);
        if (prov != null) e.putString("nube-proveedor", prov);
        // Los defectos son del proveedor que VA a quedar escrito, no del anterior:
        // todavía no se ha hecho `apply`, así que se toma `prov` si viene.
        Proveedor p = CATALOGO.get(prov != null ? prov : proveedor());

        String b = sinBarras(baseNueva);
        if (b.isEmpty() && prov != null && p != null) b = p.base;         // defecto de la casa
        if (!b.isEmpty()) e.putString("nube-base", b);

        String m = modeloNuevo == null ? "" : modeloNuevo.trim();
        if (m.isEmpty() && prov != null && p != null) m = p.modelo;
        if (!m.isEmpty()) e.putString("nube-modelo", m);

        if (claveNueva != null && !claveNueva.isEmpty()) {
            e.putString("nube-clave", claveNueva.trim());
        }
        e.apply();
    }

    private static String proveedor(String cruda) {
        if (cruda == null) return null;
        String s = cruda.trim().toLowerCase(java.util.Locale.ROOT);
        if (s.isEmpty()) return null;
        return CATALOGO.containsKey(s) ? s : s;   // se guarda tal cual si es nuevo
    }

    private static String sinBarras(String url) {
        String s = url == null ? "" : url.trim();
        while (s.endsWith("/")) s = s.substring(0, s.length() - 1);
        return s;
    }

    /* ───────────────────────────── estado ───────────────────────── */

    /** El JSON de `estado`. La clave nunca sale: sólo si está puesta y su longitud. */
    public String estadoJson() {
        return "{\"ok\":true"
             + ",\"proveedor\":" + comilla(proveedor())
             + ",\"base\":" + comilla(base())
             + ",\"modelo\":" + comilla(modelo())
             + ",\"clavePuesta\":" + (!clave().isEmpty())
             + ",\"claveLongitud\":" + clave().length()
             + ",\"conRed\":" + hayRed()
             + ",\"configurada\":" + configurada()
             + ",\"ultimoFallo\":" + comilla(ultimoFallo)
             + ",\"motores\":" + arreglo(motores())
             + "}";
    }

    /* ───────────────────────── despachador `mente` ──────────────── */

    /**
     * Resuelve `estado` y `ajustar` en el sitio (sin red). `probar` devuelve el
     * acuse `pendiente` porque su red la lanza `Mente`. `preguntar` NO es de esta
     * clase: se devuelve `null` y lo toma `Mente`.
     *
     * `peticion` es el JSON `{\"que\":\"…\", …}` que manda la cara. Cualquier
     * lio al leerlo se contesta con `ok:false` y un `dice`, nunca con una excepción.
     */
    public String mente(String peticion) {
        JSONObject j = parsea(peticion);
        if (j == null) return mal("no entendí la petición");
        String que = j.optString("que", "").toLowerCase(java.util.Locale.ROOT);
        try {
            if ("estado".equals(que)) return estadoJson();
            if ("ajustar".equals(que)) {
                JSONObject args = j.optJSONObject("args");
                ajustar(
                    campo(j, args, "proveedor"),
                    campo(j, args, "base"),
                    campo(j, args, "modelo"),
                    campo(j, args, "clave"));
                ultimoFallo = "";
                return estadoJson();
            }
            if ("probar".equals(que)) {
                // Acuse inmediato; el hilo y la red son de `Mente`.
                return "{\"ok\":true,\"pendiente\":true}";
            }
            if ("preguntar".equals(que)) return null;   // lo decide `Mente`
        } catch (Exception cualquierCosa) {
            Log.w("cort", "mente(ajustar)", cualquierCosa);
            return mal("no pude guardar los ajustes");
        }
        return mal("no conozco ese que de mente: " + que);
    }

    /* ───────────────────────────── red (bloqueante) ─────────────── */

    /**
     * Pregunta al modelo. **Bloqueante**: sólo se llama desde el hilo `cort-mente`
     * de `Mente`, jamás desde el hilo del puente. Devuelve el texto o `null`
     * (dejando el motivo en `ultimoFallo`); nunca lanza.
     */
    public String preguntar(String pregunta, String memoria) {
        ultimoFallo = "";
        if (!configurada()) { ultimoFallo = "sin configurar"; return null; }
        if (pregunta == null || pregunta.trim().isEmpty()) { ultimoFallo = "pregunta vacía"; return null; }
        String sistema = "Eres CORT, el asistente local de la dueña, hablando desde su "
            + "teléfono Android. Responde en español, en dos o tres frases como mucho, "
            + "sin markdown y sin listas. Si no sabes algo, dilo corto y no lo inventes."
            + (memoria == null || memoria.isEmpty() ? "" : " Datos que ya conoces: " + memoria);
        try {
            String texto = "anthropic".equals(estilo())
                ? porAnthropic(sistema, pregunta)
                : porOpenAICompatible(sistema, pregunta);
            return texto;
        } catch (IOException red) {
            ultimoFallo = "sin internet o el servicio no contestó";
            return null;
        } catch (JSONException malFormado) {
            ultimoFallo = "la nube respondió mal";
            return null;
        } catch (Exception cualquierCosa) {
            ultimoFallo = "fallo raro preguntando a la nube";
            Log.w("cort", "nube-preguntar", cualquierCosa);
            return null;
        }
    }

    /** Un ping corto para `probar`. Devuelve la muestra o `null` con el motivo en `ultimoFallo`. */
    public String prueba() {
        return preguntar("Responde sólo con estas dos palabras: 'cerebro listo'.", null);
    }

    private String estilo() {
        Proveedor p = CATALOGO.get(proveedor());
        return p == null ? "openai" : p.estilo;
    }

    /* ───────────────────────── dos dialectos de API ─────────────── */

    /**
     * `JSONException` va en las firmas porque en Android es excepción COMPROBADA
     * (`org.json.JSONException extends Exception`); omitirla es un `unreported
     * exception` de `javac` estricto y un Run rojo en el pipeline.
     */
    private String porAnthropic(String sistema, String pregunta)
            throws IOException, JSONException {
        JSONObject cuerpo = new JSONObject();
        cuerpo.put("model", modelo());
        cuerpo.put("max_tokens", 400);
        cuerpo.put("system", sistema);
        cuerpo.put("messages", new JSONArray().put(
            new JSONObject().put("role", "user").put("content", pregunta)));
        HttpURLConnection conexion = abrir(endpointAnthropic());
        conexion.setRequestProperty("x-api-key", clave());
        conexion.setRequestProperty("anthropic-version", "2023-06-01");
        JSONObject respuesta = enviar(conexion, cuerpo);
        JSONArray contenido = respuesta.optJSONArray("content");
        if (contenido == null || contenido.length() == 0) { ultimoFallo = "respuesta vacía"; return null; }
        return textoDe(contenido.getJSONObject(0).optString("text"));
    }

    private String porOpenAICompatible(String sistema, String pregunta)
            throws IOException, JSONException {
        JSONObject cuerpo = new JSONObject();
        cuerpo.put("model", modelo());
        cuerpo.put("messages", new JSONArray()
            .put(new JSONObject().put("role", "system").put("content", sistema))
            .put(new JSONObject().put("role", "user").put("content", pregunta)));
        HttpURLConnection conexion = abrir(endpointOpenAI());
        if (!clave().isEmpty()) conexion.setRequestProperty("Authorization", "Bearer " + clave());
        JSONObject respuesta = enviar(conexion, cuerpo);
        JSONArray opciones = respuesta.optJSONArray("choices");
        if (opciones == null || opciones.length() == 0) { ultimoFallo = "respuesta vacía"; return null; }
        return textoDe(opciones.getJSONObject(0).getJSONObject("message").optString("content"));
    }

    /* ───────────────────────── abrir / enviar / leer ────────────── */

    private String endpointAnthropic() {
        String b = base();
        if (b.contains("/messages")) return b;
        if (b.endsWith("/v1")) return b + "/messages";
        return b + "/v1/messages";
    }

    private String endpointOpenAI() {
        String b = base();
        if (b.endsWith("/chat/completions")) return b;
        if (b.endsWith("/v1")) return b + "/chat/completions";
        return b + "/v1/chat/completions";
    }

    private HttpURLConnection abrir(String url) throws IOException {
        HttpURLConnection conexion = (HttpURLConnection) new URL(url).openConnection();
        conexion.setConnectTimeout(CONEXION_MS);
        conexion.setReadTimeout(LECTURA_MS);
        conexion.setRequestMethod("POST");
        conexion.setRequestProperty("Content-Type", "application/json");
        conexion.setRequestProperty("Accept", "application/json");
        conexion.setDoOutput(true);
        return conexion;
    }

    private JSONObject enviar(HttpURLConnection conexion, JSONObject cuerpo)
            throws IOException, JSONException {
        byte[] peticion = cuerpo.toString().getBytes(StandardCharsets.UTF_8);
        OutputStream salida = conexion.getOutputStream();
        try {
            salida.write(peticion);
            salida.flush();
        } finally {
            cerrar(salida);
        }
        int codigo = conexion.getResponseCode();
        String leido = lee(codigo >= 400 ? conexion.getErrorStream() : conexion.getInputStream());
        conexion.disconnect();
        if (codigo >= 400) {
            ultimoFallo = "el servicio contestó " + codigo;
            throw new IOException(ultimoFallo);
        }
        return new JSONObject(leido);
    }

    private static String lee(InputStream entrada) throws IOException {
        if (entrada == null) return "";
        try {
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();
            byte[] trozo = new byte[4096];
            int n;
            while ((n = entrada.read(trozo)) > 0) buffer.write(trozo, 0, n);
            return new String(buffer.toByteArray(), StandardCharsets.UTF_8);
        } finally {
            cerrar(entrada);
        }
    }

    private static void cerrar(java.io.Closeable c) {
        if (c != null) try { c.close(); } catch (Exception ignorado) { }
    }

    /** Recorta a lo que cabe dicho en voz alta y le quita el markdown. */
    private static String textoDe(String crudo) {
        String limpio = crudo == null ? "" : crudo.replace("*", "").replace("#", "").trim();
        while (limpio.endsWith("\n")) limpio = limpio.substring(0, limpio.length() - 1);
        return limpio.length() <= 600 ? limpio : limpio.substring(0, 600);
    }

    /* ───────────────────────────── conectividad ─────────────────── */

    /**
     * ¿Hay red usable? `getActiveNetwork` + `NetworkCapabilities` existen desde
     * API 23, y este APK arranca en 26 (`minSdk 26`), así que no hace falta guarda
     * de versión: sólo se consulta el estado, no se hace ninguna conexión.
     */
    public boolean hayRed() {
        try {
            ConnectivityManager cm = (ConnectivityManager)
                app.getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm == null) return false;
            Network red = cm.getActiveNetwork();
            if (red == null) return false;
            NetworkCapabilities cap = cm.getNetworkCapabilities(red);
            return cap != null && cap.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET);
        } catch (Exception sinGestor) {
            Log.w("cort", "hayRed", sinGestor);
            return false;
        }
    }

    /* ───────────────────────────── JSON a mano ──────────────────── */

    private static JSONObject parsea(String crudo) {
        if (crudo == null || crudo.trim().isEmpty()) return null;
        try {
            return new JSONObject(crudo);
        } catch (Exception noEsJson) {
            return null;
        }
    }

    /** Lee un campo probando primero el objeto y luego su `args`. */
    private static String campo(JSONObject j, JSONObject args, String clave) {
        if (j.has(clave)) return j.optString(clave, "");
        if (args != null && args.has(clave)) return args.optString(clave, "");
        return "";
    }

    private static String mal(String dice) {
        return "{\"ok\":false,\"dice\":" + comilla(dice) + "}";
    }

    private static String arreglo(List<String> items) {
        StringBuilder s = new StringBuilder("[");
        for (int i = 0; i < items.size(); i++) {
            if (i > 0) s.append(',');
            s.append(comilla(items.get(i)));
        }
        return s.append(']').toString();
    }

    private static String comilla(String s) {
        if (s == null) return "null";
        StringBuilder out = new StringBuilder("\"");
        for (int n = 0; n < s.length(); n++) {
            char c = s.charAt(n);
            switch (c) {
                case '"':  out.append("\\\""); break;
                case '\\': out.append("\\\\"); break;
                case '\n': out.append("\\n");  break;
                case '\r': out.append("\\r");  break;
                case '\t': out.append("\\t");  break;
                default:
                    if (c < 0x20) out.append(String.format("\\u%04x", (int) c));
                    else out.append(c);
            }
        }
        return out.append('"').toString();
    }
}
