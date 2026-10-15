package dev.sandra.cort;

import android.content.Context;
import android.content.SharedPreferences;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * El idioma abierto de CORT cuando el teléfono está solo: **nube opcional, con
 * la clave escrita una vez en el propio aparato**. La dueña eligió «nube si hay
 * internet, local si no», y esta clase es la mitad de nube.
 *
 * Tres cosas escritas antes de tocar el código:
 *
 * 1. **La clave no vive en el repo ni en el APK.** Se teclea una vez en el
 *    teléfono y se guarda en `SharedPreferences` del modo privado de la app. Eso
 *    es almacenamiento en claro en el dispositivo: suficiente para un prototipo
 *    propio, y se dice en `apps/apk/README.md` en vez de prometer un cifrado que
 *    aquí necesitaría AndroidX (`security-crypto`) y Gradle.
 * 2. **Nube es un añadido, nunca un requisito.** Cualquier fallo —sin internet,
 *    cuota, 401, timeout— devuelve `null` y la cara sigue respondiendo con la
 *    tabla local. Un asistente que se calla porque no hay red no es un asistente.
 * 3. **La memoria viaja en el `system`, no en el historial.** Es el bug que ya
 *    cazó el core de Python (`brain.py`): si los hechos de la usuaria entran como
 *    un mensaje más, los filtros de turnos alternantes los barren antes de llegar
 *    al modelo. Aquí no hay filtros, pero el `system` es el sitio correcto igual.
 */
public class Nube {
    public static final String PREFERENCIAS = "cort-nube";
    private static final int CONEXION_MS = 12000;
    private static final int LECTURA_MS = 25000;

    private final SharedPreferences prefs;
    private String ultimoFallo = "";

    public Nube(Context contexto) {
        prefs = contexto.getApplicationContext()
                .getSharedPreferences(PREFERENCIAS, Context.MODE_PRIVATE);
    }

    public boolean configurada() {
        return !clave().isEmpty() && !base().isEmpty() && !modelo().isEmpty();
    }

    public String proveedor() {
        return prefs.getString("proveedor", "anthropic");
    }

    public String base() {
        return prefs.getString("base", "https://api.anthropic.com");
    }

    public String modelo() {
        return prefs.getString("modelo", "");
    }

    public String clave() {
        return prefs.getString("clave", "");
    }

    public String ultimoFallo() {
        return ultimoFallo;
    }

    public void ajustar(String proveedor, String base, String modelo, String clave) {
        prefs.edit().putString("proveedor", proveedor)
                .putString("base", sinBarras(base))
                .putString("modelo", modelo)
                .putString("clave", clave).apply();
    }

    private static String sinBarras(String url) {
        String s = url == null ? "" : url.trim();
        while (s.endsWith("/")) {
            s = s.substring(0, s.length() - 1);
        }
        return s;
    }

    /**
     * Pregunta al modelo. **Bloqueante**: se llama desde un hilo de trabajo y el
     * resultado se devuelve a la interfaz con `runOnUiThread`, por el mismo
     * motivo por el que la búsqueda por UDP no va en el hilo de la UI.
     */
    public String preguntar(String pregunta, String memoria) {
        ultimoFallo = "";
        if (!configurada()) {
            ultimoFallo = "sin configurar";
            return null;
        }
        String sistema = "Eres CORT, el asistente local de Sandra Lopez, hablando desde su "
                + "teléfono Android. Responde en español, en dos o tres frases como mucho, "
                + "sin markdown y sin listas. Si no sabes algo, dilo corto y no lo inventes."
                + (memoria == null || memoria.isEmpty() ? "" : " Datos que ya conoces: " + memoria);
        try {
            return "openai".equals(proveedor())
                    ? porOpenAICompatible(sistema, pregunta)
                    : porAnthropic(sistema, pregunta);
        } catch (IOException red) {
            ultimoFallo = "sin internet o el servicio no contestó";
            return null;
        } catch (Exception cualquierCosa) {
            ultimoFallo = "la nube respondió mal (" + cualquierCosa.getMessage() + ")";
            return null;
        }
    }

    /**
     * `JSONException` va en las firmas **porque en Android es una excepción
     * comprobada** (`org.json.JSONException extends Exception`, a diferencia de la
     * librería `org.json` de Maven, donde es de runtime). Omitirla es un
     * `unreported exception` de `javac` y un Run rojo: el coste de haberlo
     * adivinado mal se mide en minutos de pipeline, no en segundos aquí.
     */
    private String porAnthropic(String sistema, String pregunta)
            throws IOException, JSONException {
        JSONObject cuerpo = new JSONObject();
        cuerpo.put("model", modelo());
        cuerpo.put("max_tokens", 400);
        cuerpo.put("system", sistema);
        cuerpo.put("messages", new JSONArray().put(
                new JSONObject().put("role", "user").put("content", pregunta)));
        HttpURLConnection conexion = abrir(base() + "/v1/messages");
        conexion.setRequestProperty("x-api-key", clave());
        conexion.setRequestProperty("anthropic-version", "2023-06-01");
        JSONObject respuesta = enviar(conexion, cuerpo);
        JSONArray contenido = respuesta.optJSONArray("content");
        if (contenido == null || contenido.length() == 0) {
            ultimoFallo = "respuesta vacía";
            return null;
        }
        return textoDe(contenido.getJSONObject(0).optString("text"));
    }

    private String porOpenAICompatible(String sistema, String pregunta)
            throws IOException, JSONException {
        JSONObject cuerpo = new JSONObject();
        cuerpo.put("model", modelo());
        cuerpo.put("messages", new JSONArray()
                .put(new JSONObject().put("role", "system").put("content", sistema))
                .put(new JSONObject().put("role", "user").put("content", pregunta)));
        HttpURLConnection conexion = abrir(base() + "/chat/completions");
        conexion.setRequestProperty("Authorization", "Bearer " + clave());
        JSONObject respuesta = enviar(conexion, cuerpo);
        JSONArray opciones = respuesta.optJSONArray("choices");
        if (opciones == null || opciones.length() == 0) {
            ultimoFallo = "respuesta vacía";
            return null;
        }
        return textoDe(opciones.getJSONObject(0).getJSONObject("message")
                .optString("content"));
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
        } finally {
            salida.close();
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
        if (entrada == null) {
            return "";
        }
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        byte[] trozo = new byte[4096];
        int n;
        while ((n = entrada.read(trozo)) > 0) {
            buffer.write(trozo, 0, n);
        }
        entrada.close();
        return new String(buffer.toByteArray(), StandardCharsets.UTF_8);
    }

    /** Recorta el texto a lo que cabe dicho en voz alta, y le quita el markdown. */
    private static String textoDe(String crudo) {
        String limpio = crudo == null ? "" : crudo.replace("*", "").replace("#", "").trim();
        while (limpio.endsWith("\n")) {
            limpio = limpio.substring(0, limpio.length() - 1);
        }
        return limpio.length() <= 600 ? limpio : limpio.substring(0, 600);
    }
}
