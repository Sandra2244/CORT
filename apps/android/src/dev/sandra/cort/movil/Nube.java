package dev.sandra.cort.movil;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.KeyStore;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
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
 *    teléfono, se cifra con AES-256/GCM y la llave queda en AndroidKeyStore. El
 *    `SharedPreferences` privado sólo guarda el sobre; el campo plano se elimina
 *    en el mismo `commit()` que instala la migración verificada.
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
    private static final String CLAVE_PLANA = "clave";
    private static final String CLAVE_SOBRE = "clave_sobre_v1";
    private static final int CONEXION_MS = 12000;
    private static final int LECTURA_MS = 25000;

    private final SharedPreferences prefs;
    private final SobreSecreto sobre = new SobreSecreto();
    private String ultimoFallo = "";
    private boolean guardadoRechazado = false;

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

    public boolean hayClave() {
        if (guardadoRechazado) return false;
        if (!prefs.contains(CLAVE_SOBRE) && !prefs.contains(CLAVE_PLANA)) return false;
        String antigua = prefs.getString(CLAVE_PLANA, "");
        if (!antigua.isEmpty()) {
            if (!migrar(antigua)) {
                ultimoFallo = "no se pudo proteger la clave; vuelve a teclearla";
                return false;
            }
        }
        return !prefs.getString(CLAVE_SOBRE, "").isEmpty();
    }

    /** Sólo se usa para una petición; ninguna pantalla ni respuesta la recibe. */
    public String clave() {
        if (!hayClave()) return "";
        try {
            return sobre.descifrar(prefs.getString(CLAVE_SOBRE, ""), llaveKeystore());
        } catch (GeneralSecurityException | java.io.IOException error) {
            ultimoFallo = "no se pudo abrir la clave cifrada";
            return "";
        } catch (IllegalArgumentException error) {
            ultimoFallo = "la clave cifrada está dañada; vuelve a teclearla";
            return "";
        }
    }

    public String ultimoFallo() {
        return ultimoFallo;
    }

    public void ajustar(String proveedor, String base, String modelo, String clave) {
        SharedPreferences.Editor editor = prefs.edit()
                .putString("proveedor", proveedor)
                .putString("base", sinBarras(base))
                .putString("modelo", modelo);
        boolean sobreValido = true;
        if (clave == null || clave.isEmpty()) {
            editor.remove(CLAVE_PLANA).remove(CLAVE_SOBRE);
        } else if (!guardarSobre(editor, clave)) {
            editor.remove(CLAVE_PLANA).remove(CLAVE_SOBRE);
            sobreValido = false;
            ultimoFallo = "no se pudo guardar la clave cifrada; no se escribió en claro";
        }
        if (!editor.commit()) {
            guardadoRechazado = true;
            ultimoFallo = "no se pudieron guardar los ajustes; vuelve a intentarlo";
            return;
        }
        guardadoRechazado = false;
        ultimoFallo = sobreValido
                ? ""
                : "no se pudo guardar la clave cifrada; no se escribió en claro";
    }

    public void borrarClave() {
        SharedPreferences.Editor editor = prefs.edit().remove(CLAVE_PLANA).remove(CLAVE_SOBRE);
        if (!editor.commit()) {
            guardadoRechazado = true;
            ultimoFallo = "no se pudo borrar la clave; vuelve a intentarlo";
            return;
        }
        guardadoRechazado = false;
        try {
            KeyStore almacen = KeyStore.getInstance("AndroidKeyStore");
            almacen.load(null);
            if (almacen.containsAlias(SobreSecreto.ALIAS)) almacen.deleteEntry(SobreSecreto.ALIAS);
            ultimoFallo = "";
        } catch (GeneralSecurityException | java.io.IOException error) {
            ultimoFallo = "se quitó el sobre, pero no se pudo borrar el alias";
        }
    }

    private boolean migrar(String antigua) {
        SharedPreferences.Editor editor = prefs.edit();
        if (!guardarSobre(editor, antigua)) return false;
        if (!editor.commit()) {
            guardadoRechazado = true;
            return false;
        }
        guardadoRechazado = false;
        return true;
    }

    private boolean guardarSobre(SharedPreferences.Editor editor, String texto) {
        try {
            String cifrado = sobre.cifrar(texto, llaveKeystore());
            String recuperado = sobre.descifrar(cifrado, llaveKeystore());
            if (!texto.equals(recuperado)) return false;
            editor.putString(CLAVE_SOBRE, cifrado).remove(CLAVE_PLANA);
            return true;
        } catch (GeneralSecurityException | java.io.IOException | IllegalArgumentException error) {
            return false;
        }
    }

    private SecretKey llaveKeystore() throws GeneralSecurityException, java.io.IOException {
        KeyStore almacen = KeyStore.getInstance("AndroidKeyStore");
        almacen.load(null);
        if (!almacen.containsAlias(SobreSecreto.ALIAS)) {
            KeyGenerator generador = KeyGenerator.getInstance("AES", "AndroidKeyStore");
            generador.init(new KeyGenParameterSpec.Builder(SobreSecreto.ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .setKeySize(256)
                    .build());
            generador.generateKey();
        }
        return (SecretKey) almacen.getKey(SobreSecreto.ALIAS, null);
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
        return preguntar(CerebroLocal.sistemaCort(memoria), pregunta, null);
    }

    /**
     * La misma pregunta con el carácter que arma `Consticion` y los turnos ya
     * dichos (F20d). El `sistema` se recibe en vez de escribirse aquí para que la
     * personalidad no quede en dos archivos: la del GGUF y la de la nube tienen que
     * ser la misma, o CORT cambia de carácter según el camino que eligió.
     *
     * Los hechos de la dueña siguen yendo en el `system` (punto 3 de arriba); el
     * historial son sólo turnos de conversación, que es lo que los filtros de
     * turnos alternantes de los proveedores esperan encontrar.
     */
    public String preguntar(String sistema, String pregunta, java.util.List<String[]> historial) {
        ultimoFallo = "";
        String claveApi = clave();
        if (claveApi.isEmpty() || base().isEmpty() || modelo().isEmpty()) {
            if (ultimoFallo.isEmpty()) ultimoFallo = "sin configurar";
            return null;
        }
        try {
            JSONArray mensajes = new JSONArray();
            if (historial != null) {
                for (String[] turno : historial) {
                    if (turno == null || turno.length < 2 || turno[1].isEmpty()) {
                        continue;
                    }
                    mensajes.put(new JSONObject().put("role", turno[0]).put("content", turno[1]));
                }
            }
            mensajes.put(new JSONObject().put("role", "user").put("content", pregunta));
            return "openai".equals(proveedor())
                    ? porOpenAICompatible(sistema, mensajes, claveApi)
                    : porAnthropic(sistema, mensajes, claveApi);
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
    private String porAnthropic(String sistema, JSONArray mensajes, String claveApi)
            throws IOException, JSONException {
        JSONObject cuerpo = new JSONObject();
        cuerpo.put("model", modelo());
        cuerpo.put("max_tokens", 400);
        cuerpo.put("system", sistema);
        cuerpo.put("messages", mensajes);
        HttpURLConnection conexion = abrir(base() + "/v1/messages");
        conexion.setRequestProperty("x-api-key", claveApi);
        conexion.setRequestProperty("anthropic-version", "2023-06-01");
        JSONObject respuesta = enviar(conexion, cuerpo);
        JSONArray contenido = respuesta.optJSONArray("content");
        if (contenido == null || contenido.length() == 0) {
            ultimoFallo = "respuesta vacía";
            return null;
        }
        return textoDe(contenido.getJSONObject(0).optString("text"));
    }

    private String porOpenAICompatible(String sistema, JSONArray mensajes, String claveApi)
            throws IOException, JSONException {
        JSONArray turnos = new JSONArray()
                .put(new JSONObject().put("role", "system").put("content", sistema));
        for (int i = 0; i < mensajes.length(); i++) {
            turnos.put(mensajes.get(i));
        }
        JSONObject cuerpo = new JSONObject();
        cuerpo.put("model", modelo());
        cuerpo.put("messages", turnos);
        HttpURLConnection conexion = abrir(base() + "/chat/completions");
        conexion.setRequestProperty("Authorization", "Bearer " + claveApi);
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
