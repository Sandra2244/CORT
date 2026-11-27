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
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.KeyStore;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

public class Nube {
    public static final String PREFERENCIAS = "cort-nube";
    private static final String CLAVE_PLANA = "clave";
    private static final String CLAVE_SOBRE = "clave_sobre_v1";
    private static final String CLAVE_PERFILES = "perfiles_v1";
    private static final String CLAVE_ACTIVO = "perfil_activo";
    private static final int CONEXION_MS = 12000;
    private static final int LECTURA_MS = 25000;
    private static final int MAX_RESPUESTA = 1024 * 1024;

    private final SharedPreferences prefs;
    private final SobreSecreto sobre = new SobreSecreto();
    private volatile String ultimoFallo = "";
    private volatile boolean guardadoRechazado = false;

    public Nube(Context contexto) {
        prefs = contexto.getApplicationContext()
                .getSharedPreferences(PREFERENCIAS, Context.MODE_PRIVATE);
    }

    public static final class Perfil {
        public final String id;
        public final String nombre;
        public final String proveedor;
        public final String base;
        public final String modelo;
        public final String claveSobre;

        private Perfil(String id, String nombre, String proveedor, String base,
                       String modelo, String claveSobre) {
            this.id = id;
            this.nombre = nombre;
            this.proveedor = proveedor;
            this.base = base;
            this.modelo = modelo;
            this.claveSobre = claveSobre;
        }

        public boolean tieneClave() {
            return claveSobre != null && !claveSobre.isEmpty();
        }

        public JSONObject publico() {
            try {
                return new JSONObject().put("id", id).put("nombre", nombre)
                        .put("proveedor", proveedor).put("base", base)
                        .put("modelo", modelo).put("tiene_clave", tieneClave());
            } catch (JSONException imposible) {
                throw new IllegalStateException(imposible);
            }
        }
    }

    public synchronized List<Perfil> perfiles() {
        if (!prefs.contains(CLAVE_PERFILES)) migrarLegacy();
        List<Perfil> lista = new ArrayList<>();
        JSONArray j = new JSONArray();
        try {
            j = new JSONArray(prefs.getString(CLAVE_PERFILES, "[]"));
        } catch (JSONException roto) {
            ultimoFallo = "el registro de proveedores está dañado; vuelve a configurarlo";
            return lista;
        }
        for (int i = 0; i < j.length(); i++) {
            JSONObject p = j.optJSONObject(i);
            if (p == null) continue;
            String id = p.optString("id", "").trim();
            String proveedor = ProveedorNube.normalizar(p.optString("proveedor", ""));
            String base = sinBarras(p.optString("base", ""));
            String modelo = p.optString("modelo", "").trim();
            if (!idValido(id) || proveedor.isEmpty() || !ProveedorNube.baseOficial(proveedor, base)
                    || !modeloValido(modelo)) continue;
            String nombre = p.optString("nombre", proveedor).trim();
            lista.add(new Perfil(id, nombre.length() > 60 ? nombre.substring(0, 60) : nombre,
                    proveedor, base, modelo, p.optString("clave_sobre", "")));
        }
        return lista;
    }

    public Perfil activo() {
        List<Perfil> lista = perfiles();
        String id = prefs.getString(CLAVE_ACTIVO, "");
        for (Perfil p : lista) if (p.id.equals(id)) return p;
        for (Perfil p : lista) if (p.tieneClave()) return p;
        return lista.isEmpty() ? null : lista.get(0);
    }

    public String idActivo() {
        Perfil p = activo();
        return p == null ? "" : p.id;
    }

    public String nombreActivo() {
        Perfil p = activo();
        return p == null ? "" : p.nombre;
    }

    public boolean configurada() {
        Perfil p = activo();
        return p != null && !clave(p).isEmpty() && ProveedorNube.baseOficial(p.proveedor, p.base)
                && modeloValido(p.modelo);
    }

    public String proveedor() {
        Perfil p = activo();
        return p == null ? "anthropic" : p.proveedor;
    }

    public String base() {
        Perfil p = activo();
        return p == null ? ProveedorNube.basePorDefecto("anthropic") : p.base;
    }

    public String modelo() {
        Perfil p = activo();
        return p == null ? "" : p.modelo;
    }

    public boolean hayClave() {
        if (guardadoRechazado) return false;
        Perfil p = activo();
        return p != null && p.tieneClave();
    }

    public String clave() {
        return clave(activo());
    }

    private String clave(Perfil p) {
        if (p == null || !p.tieneClave()) return "";
        try {
            return sobre.descifrar(p.claveSobre, llaveKeystore());
        } catch (GeneralSecurityException | IOException error) {
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
        Perfil p = activo();
        guardarPerfil(p == null ? "principal" : p.id,
                p == null ? proveedor : p.nombre, proveedor, base, modelo, clave);
    }

    public boolean guardarPerfil(String id, String nombre, String proveedor,
                                 String base, String modelo, String clave) {
        String idLimpio = id == null ? "" : id.trim().toLowerCase(Locale.ROOT);
        String proveedorLimpio = ProveedorNube.normalizar(proveedor);
        String baseLimpia = sinBarras(base);
        String modeloLimpio = modelo == null ? "" : modelo.trim();
        String nombreLimpio = nombre == null ? "" : nombre.trim();
        if (!idValido(idLimpio) || proveedorLimpio.isEmpty()
                || !ProveedorNube.baseOficial(proveedorLimpio, baseLimpia) || !modeloValido(modeloLimpio)) {
            ultimoFallo = "revisa el identificador, proveedor, endpoint oficial y modelo";
            return false;
        }
        if (nombreLimpio.isEmpty()) nombreLimpio = proveedorLimpio;
        List<Perfil> lista = perfiles();
        String sobreClave = "";
        for (Perfil p : lista) if (p.id.equals(idLimpio)) sobreClave = p.claveSobre;
        if (clave != null && !clave.isEmpty()) {
            try {
                sobreClave = sobre.cifrar(clave, llaveKeystore());
                String recuperada = sobre.descifrar(sobreClave, llaveKeystore());
                if (!clave.equals(recuperada)) throw new GeneralSecurityException("verificación fallida");
            } catch (GeneralSecurityException | IOException | IllegalArgumentException error) {
                ultimoFallo = "no se pudo proteger la clave; no se escribió en claro";
                return false;
            }
        }
        JSONArray j = new JSONArray();
        boolean puesto = false;
        for (Perfil p : lista) {
            if (p.id.equals(idLimpio)) {
                j.put(registro(idLimpio, nombreLimpio, proveedorLimpio, baseLimpia,
                        modeloLimpio, sobreClave));
                puesto = true;
            } else {
                j.put(registro(p.id, p.nombre, p.proveedor, p.base, p.modelo, p.claveSobre));
            }
        }
        if (!puesto) j.put(registro(idLimpio, nombreLimpio, proveedorLimpio, baseLimpia,
                modeloLimpio, sobreClave));
        SharedPreferences.Editor editor = prefs.edit().putString(CLAVE_PERFILES, j.toString())
                .putString(CLAVE_ACTIVO, idLimpio).remove(CLAVE_PLANA).remove(CLAVE_SOBRE)
                .remove("proveedor").remove("base").remove("modelo");
        if (!editor.commit()) {
            guardadoRechazado = true;
            ultimoFallo = "no se pudieron guardar los ajustes";
            return false;
        }
        guardadoRechazado = false;
        ultimoFallo = "";
        return true;
    }

    public boolean usarPerfil(String id) {
        for (Perfil p : perfiles()) {
            if (p.id.equals(id)) {
                boolean ok = prefs.edit().putString(CLAVE_ACTIVO, id).commit();
                if (!ok) ultimoFallo = "no se pudo seleccionar el proveedor";
                return ok;
            }
        }
        ultimoFallo = "ese proveedor no está registrado";
        return false;
    }

    public void borrarClave() {
        Perfil p = activo();
        if (p != null) guardarPerfil(p.id, p.nombre, p.proveedor, p.base, p.modelo, "");
        Perfil limpio = activo();
        if (limpio != null && !limpio.tieneClave()) {
            List<Perfil> lista = perfiles();
            JSONArray j = new JSONArray();
            for (Perfil q : lista) j.put(registro(q.id, q.nombre, q.proveedor,
                    q.base, q.modelo, ""));
            prefs.edit().putString(CLAVE_PERFILES, j.toString()).commit();
        }
    }

    public boolean borrarPerfil(String id) {
        List<Perfil> lista = perfiles();
        JSONArray j = new JSONArray();
        boolean encontrado = false;
        boolean quedaClave = false;
        for (Perfil p : lista) {
            if (p.id.equals(id)) {
                encontrado = true;
            } else {
                j.put(registro(p.id, p.nombre, p.proveedor, p.base, p.modelo, p.claveSobre));
                quedaClave |= p.tieneClave();
            }
        }
        if (!encontrado) return false;
        JSONObject primero = j.optJSONObject(0);
        String siguiente = primero == null ? "" : primero.optString("id", "");
        if (!prefs.edit().putString(CLAVE_PERFILES, j.toString())
                .putString(CLAVE_ACTIVO, siguiente).commit()) {
            ultimoFallo = "no se pudo borrar el proveedor";
            return false;
        }
        if (!quedaClave) borrarAlias();
        return true;
    }

    private void migrarLegacy() {
        boolean hay = false;
        for (String k : new String[] {"proveedor", "base", "modelo", CLAVE_PLANA, CLAVE_SOBRE}) {
            hay |= prefs.contains(k);
        }
        if (!hay) return;
        String antigua = prefs.getString(CLAVE_PLANA, "");
        String cifrada = prefs.getString(CLAVE_SOBRE, "");
        try {
            if (!antigua.isEmpty()) {
                cifrada = sobre.cifrar(antigua, llaveKeystore());
            }
            if (!cifrada.isEmpty()) {
                String comprobada = sobre.descifrar(cifrada, llaveKeystore());
                if (comprobada.isEmpty()) throw new GeneralSecurityException("clave vacía");
            }
        } catch (GeneralSecurityException | IOException | IllegalArgumentException error) {
            ultimoFallo = "la clave antigua no se pudo verificar; se conservó sin migrar";
            return;
        }
        String proveedorGuardado = prefs.getString("proveedor", "anthropic");
        String proveedor = ProveedorNube.normalizar(proveedorGuardado);
        String base = prefs.getString("base", "");
        String modelo = prefs.getString("modelo", "");
        if (proveedor.isEmpty() || (base.isEmpty() && !prefs.contains("base"))) {
            ultimoFallo = "la configuración anterior no es válida; se conservó sin migrar";
            return;
        }
        if (base.isEmpty()) base = ProveedorNube.basePorDefecto(proveedor);
        if (!ProveedorNube.baseOficial(proveedor, base) || !modeloValido(modelo)) {
            ultimoFallo = "el endpoint o modelo anterior no es válido; se conservó sin migrar";
            return;
        }
        JSONArray j = new JSONArray().put(registro("principal", "Principal", proveedor,
                sinBarras(base), modelo, cifrada));
        if (!prefs.edit().putString(CLAVE_PERFILES, j.toString())
                .putString(CLAVE_ACTIVO, "principal").remove(CLAVE_PLANA).remove(CLAVE_SOBRE)
                .remove("proveedor").remove("base").remove("modelo").commit()) {
            ultimoFallo = "no se pudo migrar la configuración anterior";
        }
    }

    private static JSONObject registro(String id, String nombre, String proveedor,
                                        String base, String modelo, String claveSobre) {
        try {
            return new JSONObject().put("id", id).put("nombre", nombre)
                    .put("proveedor", proveedor).put("base", base).put("modelo", modelo)
                    .put("clave_sobre", claveSobre);
        } catch (JSONException imposible) {
            throw new IllegalStateException(imposible);
        }
    }

    private static boolean idValido(String id) {
        return id != null && id.matches("[a-z0-9][a-z0-9-]{0,39}");
    }

    private static boolean modeloValido(String modelo) {
        if (modelo == null || modelo.isEmpty() || modelo.length() > 120) return false;
        for (int i = 0; i < modelo.length(); i++) {
            if (Character.isISOControl(modelo.charAt(i))) return false;
        }
        return true;
    }

    private SecretKey llaveKeystore() throws GeneralSecurityException, IOException {
        KeyStore almacen = KeyStore.getInstance("AndroidKeyStore");
        almacen.load(null);
        if (!almacen.containsAlias(SobreSecreto.ALIAS)) {
            KeyGenerator generador = KeyGenerator.getInstance("AES", "AndroidKeyStore");
            generador.init(new KeyGenParameterSpec.Builder(SobreSecreto.ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                    .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .setKeySize(256).build());
            generador.generateKey();
        }
        return (SecretKey) almacen.getKey(SobreSecreto.ALIAS, null);
    }

    private void borrarAlias() {
        try {
            KeyStore almacen = KeyStore.getInstance("AndroidKeyStore");
            almacen.load(null);
            if (almacen.containsAlias(SobreSecreto.ALIAS)) almacen.deleteEntry(SobreSecreto.ALIAS);
        } catch (GeneralSecurityException | IOException error) {
            ultimoFallo = "se quitaron los sobres, pero no se pudo borrar el alias";
        }
    }

    private static String sinBarras(String url) {
        String s = url == null ? "" : url.trim();
        while (s.endsWith("/")) s = s.substring(0, s.length() - 1);
        return s;
    }

    public String preguntar(String pregunta, String memoria) {
        return preguntar(CerebroLocal.sistemaCort(memoria), pregunta, null);
    }

    public String preguntar(String sistema, String pregunta, List<String[]> historial) {
        ultimoFallo = "";
        Perfil p = activo();
        if (p == null || !p.tieneClave() || !ProveedorNube.baseOficial(p.proveedor, p.base)
                || !modeloValido(p.modelo)) {
            ultimoFallo = "sin configurar";
            return null;
        }
        String claveApi = clave(p);
        if (claveApi.isEmpty()) return null;
        try {
            JSONArray mensajes = new JSONArray();
            if (historial != null) {
                for (String[] turno : historial) {
                    if (turno == null || turno.length < 2 || turno[1].isEmpty()) continue;
                    mensajes.put(new JSONObject().put("role", normalizarRol(turno[0], p.proveedor))
                            .put("content", turno[1]));
                }
            }
            mensajes.put(new JSONObject().put("role", normalizarRol("user", p.proveedor))
                    .put("content", pregunta));
            if (ProveedorNube.antropico(p.proveedor)) return porAnthropic(p, sistema, mensajes, claveApi);
            if (ProveedorNube.gemini(p.proveedor)) return porGemini(p, sistema, mensajes, claveApi);
            return porOpenAICompatible(p, sistema, mensajes, claveApi);
        } catch (IOException red) {
            ultimoFallo = "sin internet o el servicio no contestó";
            return null;
        } catch (Exception cualquierCosa) {
            ultimoFallo = "la nube respondió mal (" + cualquierCosa.getMessage() + ")";
            return null;
        }
    }

    private static String normalizarRol(String rol, String proveedor) {
        boolean asistente = "assistant".equals(rol);
        return ProveedorNube.gemini(proveedor) && asistente ? "model" : rol;
    }

    private String porAnthropic(Perfil p, String sistema, JSONArray mensajes, String claveApi)
            throws IOException, JSONException {
        JSONObject cuerpo = new JSONObject().put("model", p.modelo).put("max_tokens", 400)
                .put("system", sistema).put("messages", mensajes);
        HttpURLConnection conexion = abrir(p, "/v1/messages");
        conexion.setRequestProperty("x-api-key", claveApi);
        conexion.setRequestProperty("anthropic-version", "2023-06-01");
        JSONObject respuesta = enviar(conexion, cuerpo);
        JSONArray contenido = respuesta.optJSONArray("content");
        if (contenido == null) {
            ultimoFallo = "respuesta vacía";
            return null;
        }
        StringBuilder texto = new StringBuilder();
        for (int i = 0; i < contenido.length(); i++) {
            JSONObject parte = contenido.optJSONObject(i);
            if (parte != null && "text".equals(parte.optString("type"))) {
                texto.append(parte.optString("text"));
            }
        }
        return textoDe(texto.toString());
    }

    private String porGemini(Perfil p, String sistema, JSONArray mensajes, String claveApi)
            throws IOException, JSONException {
        JSONObject instruccion = new JSONObject().put("parts", new JSONArray()
                .put(new JSONObject().put("text", sistema)));
        JSONObject cuerpo = new JSONObject().put("systemInstruction", instruccion)
                .put("contents", mensajes).put("generationConfig",
                        new JSONObject().put("maxOutputTokens", 400));
        String modelo = URLEncoder.encode(p.modelo, StandardCharsets.UTF_8.name());
        HttpURLConnection conexion = abrir(p, "/models/" + modelo + ":generateContent");
        conexion.setRequestProperty("x-goog-api-key", claveApi);
        JSONObject respuesta = enviar(conexion, cuerpo);
        JSONArray candidatos = respuesta.optJSONArray("candidates");
        if (candidatos == null || candidatos.length() == 0) {
            ultimoFallo = "respuesta vacía";
            return null;
        }
        JSONObject contenido = candidatos.getJSONObject(0).optJSONObject("content");
        JSONArray partes = contenido == null ? null : contenido.optJSONArray("parts");
        if (partes == null) {
            ultimoFallo = "respuesta sin texto";
            return null;
        }
        StringBuilder texto = new StringBuilder();
        for (int i = 0; i < partes.length(); i++) texto.append(partes.optJSONObject(i).optString("text"));
        return textoDe(texto.toString());
    }

    private String porOpenAICompatible(Perfil p, String sistema, JSONArray mensajes, String claveApi)
            throws IOException, JSONException {
        JSONArray turnos = new JSONArray().put(new JSONObject().put("role", "system")
                .put("content", sistema));
        for (int i = 0; i < mensajes.length(); i++) turnos.put(mensajes.get(i));
        JSONObject cuerpo = new JSONObject().put("model", p.modelo).put("messages", turnos);
        HttpURLConnection conexion = abrir(p, "/chat/completions");
        conexion.setRequestProperty("Authorization", "Bearer " + claveApi);
        JSONObject respuesta = enviar(conexion, cuerpo);
        JSONArray opciones = respuesta.optJSONArray("choices");
        if (opciones == null || opciones.length() == 0) {
            ultimoFallo = "respuesta vacía";
            return null;
        }
        JSONObject mensaje = opciones.getJSONObject(0).optJSONObject("message");
        return textoDe(mensaje == null ? "" : mensaje.optString("content"));
    }

    private HttpURLConnection abrir(Perfil p, String ruta) throws IOException {
        if (p == null || !ProveedorNube.baseOficial(p.proveedor, p.base)
                || ruta == null || !ruta.startsWith("/") || ruta.contains("?")
                || ruta.contains("#") || ruta.contains("..") || ruta.contains("\\")) {
            throw new IOException("la petición no corresponde al endpoint oficial");
        }
        String url = sinBarras(p.base) + ruta;
        if (!ProveedorNube.baseSegura(url)) throw new IOException("la petición no es HTTPS pública");
        HttpURLConnection conexion = (HttpURLConnection) new URL(url).openConnection();
        conexion.setInstanceFollowRedirects(false);
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
        try {
            byte[] peticion = cuerpo.toString().getBytes(StandardCharsets.UTF_8);
            OutputStream salida = conexion.getOutputStream();
            try {
                salida.write(peticion);
            } finally {
                salida.close();
            }
            int codigo = conexion.getResponseCode();
            if (codigo >= 300 && codigo < 400) throw new IOException("la nube intentó redirigir; se rechazó");
            String leido = lee(codigo >= 400 ? conexion.getErrorStream() : conexion.getInputStream());
            if (codigo >= 400) throw new IOException("el servicio contestó " + codigo);
            return new JSONObject(leido);
        } finally {
            conexion.disconnect();
        }
    }

    private static String lee(InputStream entrada) throws IOException {
        if (entrada == null) return "";
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        byte[] trozo = new byte[4096];
        int n;
        while ((n = entrada.read(trozo)) > 0) {
            if (buffer.size() + n > MAX_RESPUESTA) throw new IOException("respuesta demasiado grande");
            buffer.write(trozo, 0, n);
        }
        entrada.close();
        return new String(buffer.toByteArray(), StandardCharsets.UTF_8);
    }

    private static String textoDe(String crudo) {
        String limpio = crudo == null ? "" : crudo.replace("*", "").replace("#", "").trim();
        while (limpio.endsWith("\n")) limpio = limpio.substring(0, limpio.length() - 1);
        return limpio.length() <= 600 ? limpio : limpio.substring(0, 600);
    }
}
