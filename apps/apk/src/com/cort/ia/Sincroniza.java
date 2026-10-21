package com.cort.ia;

/*
 * El puente **asomado a la red del teléfono**: la única clase del APK que habla
 * con el portátil por HTTP. Sin librerías: `java.net.HttpURLConnection`, que
 * Android ya trae, y `org.json`, que viene en el `android.jar`.
 *
 * Las rutas están miradas en el backend de verdad —
 * `backend/app/main.py`, grep de `@app.get`/`@app.post` — y no inventadas:
 * **la puerta `/api/memoria` del encargo no existe**. Lo que el portátil
 * realmente ofrece para la memoria es:
 *
 * · `GET  /api/profile`  → objeto plano `{clave: valor, …}`
 *   (`memory.get_profile`, la memoria de preferencias).
 * · `POST /api/profile`  → cuerpo `{"clave":"…","valor":"…"}` → `{"ok":true}`
 *   (`memory.set_profile`, un hecho por petición; no hay lote).
 * · `GET  /api/memories?n=40` → `{"recuerdos":[{tipo,texto,fuente,fecha},…]}`
 *   (`memory.memories`, el muro de notas y conversaciones).
 *
 * Así que este cliente baja hechos por `/api/profile`, baja el muro por
 * `/api/memories` y sube sus hechos hechos uno a uno con `POST /api/profile`,
 * con tope por viaje para no machacar el portátil con 600 peticiones.
 *
 * Tres decisiones portadas de la línea hermana, nacidas de cómo se cae un
 * teléfono de verdad:
 *
 * 1. **Bloqueante y fuera del hilo de la cara.** Este método sólo se llama
 *    desde el hilo `cort-memoria-sync` que arranca `Recuerdos`; jamás desde
 *    el hilo del puente de WebView. Los timeouts van a 6 s por ley del
 *    encargo: un portátil apagado no tiene por qué congelar el orbe ni
 *    treinta segundos.
 * 2. **Primero se baja, después se sube.** Bajar es lo que le da a CORT datos
 *    que le faltan; si el portátil se apaga a la mitad, lo perdido es la
 *    subida, y se dice en el recuento.
 * 3. **Nunca un error en silencio.** Sin enlace guardado, sin wifi, otro
 *    puerto, un 404 o un cuerpo que no es JSON se devuelven **dichos** en
 *    español dentro de `dice`. Un puente que no avisa es un puente roto.
 *
 * La clave, si la dueña la puso (`cort` / `clave`), viaja sólo como cabecera
 * `Authorization` y **sólo si hay clave**; no se imprime en ningún cuadro, no
 * se mete en ninguna URL (las URLs acaban en los logs del router de la casa),
 * y ninguna respuesta del portátil se reenvía tal cual a la cara: la cara ve
 * recuentos y frases, nunca cuerpos crudos que pudieran traer datos de más.
 */

import android.content.Context;
import android.content.SharedPreferences;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Locale;
import org.json.JSONArray;
import org.json.JSONObject;

public class Sincroniza {

    private static final int CONEXION_MS = 6000;   // 6 s por contrato de la dueña
    private static final int LECTURA_MS = 6000;
    private static final int TOPE_SUBIDA = 60;     // hechos por viaje: POST no es lote aquí
    private static final int MURO_BAJADO = 40;     // lo que cabe en una pantalla

    private final SharedPreferences prefs;
    private final Recuerdos recuerdos;
    private String ultimoFallo = "";

    public Sincroniza(android.content.Context c, Recuerdos r) {
        this.prefs = c.getApplicationContext()
                       .getSharedPreferences("cort", Context.MODE_PRIVATE);
        this.recuerdos = r;
    }

    /** El último motivo dicho en español; vacío si el último viaje fue bien. */
    public String ultimoFallo() { return ultimoFallo; }

    /** La dirección guardada (`cort` / `pc`) existe y tiene forma de URL. */
    public boolean hayPortatil() {
        return base() != null;
    }

    /* ─────────────────────────────── el viaje ─────────────────────────────── */

    /**
     * La ida y la vuelta. Devuelve SIEMPRE un cuadro `{"ok":…, "subidos":…,
     * "bajados":…, "dice":…}` y nunca lanza: quien llama está en un hilo sin
     * red propia que lo gestione. `Recuerdos` le añade el `type:"memoria"` y
     * lo manda por el callback.
     */
    public String sincronizar() {
        ultimoFallo = "";
        String b = base();
        if (b == null) {
            ultimoFallo = "no sé dónde está tu portátil: dime su dirección primero";
            return "{\"ok\":false,\"dice\":" + comilla(ultimoFallo) + "}";
        }
        int bajados = 0;
        int subidos = 0;
        try {
            bajados += bajarHechos(b);        // GET  /api/profile
            bajados += bajarMuro(b);          // GET  /api/memories?n=40
            subidos += subirHechos(b);        // POST /api/profile, a uno por viaje
            subidos += subirFrases(b);        // POST /api/memories, en un solo viaje
            String dice = "del portátil: " + bajados + " nuevos"
                        + " · al portátil: " + subidos + " subidos";
            return "{\"ok\":true,\"subidos\":" + subidos
                 + ",\"bajados\":" + bajados
                 + ",\"dice\":" + comilla(dice) + "}";
        } catch (IOException red) {
            // El motivo **dicho**, no «sin internet»: «no llego al 8000» y
            // «el portátil no tiene esa puerta» son decisiones distintas de la
            // dueña (una es encender el backend, otra es actualizarlo).
            String motivo = red.getMessage();
            ultimoFallo = (motivo == null || motivo.trim().isEmpty())
                        ? "el portátil no contestó" : motivo;
            return "{\"ok\":false,\"subidos\":" + subidos
                 + ",\"bajados\":" + bajados
                 + ",\"dice\":" + comilla(ultimoFallo) + "}";
        } catch (Exception cualquierCosa) {
            // Un JSON de otra versión o un cuerpo raro entra aquí a propósito:
            // es un fallo que hay que decir, no un motivo para tumbar el hilo.
            ultimoFallo = "el puente no cerró: " + (cualquierCosa.getMessage() == null
                            ? cualquierCosa.getClass().getSimpleName()
                            : cualquierCosa.getMessage());
            return "{\"ok\":false,\"subidos\":" + subidos
                 + ",\"bajados\":" + bajados
                 + ",\"dice\":" + comilla(ultimoFallo) + "}";
        }
    }

    /* ──────────────────────────────── bajar ────────────────────────────────── */

    /**
     * `GET /api/profile` — el objeto `{clave: valor}` del portátil. Sólo se
     * guarda lo que el teléfono **no** sabe ya: la cabeza local manda, y una
     * sincronía no puede pisar un hecho que la dueña corrigió aquí ayer.
     */
    private int bajarHechos(String b) throws IOException {
        String leido = llamar(b + "/api/profile", "GET", null);
        JSONObject perfil = cuadro(leido, "el portátil no contestó con su perfil");
        int nuevos = 0;
        java.util.Iterator<String> ks = perfil.keys();
        while (ks.hasNext()) {
            String k = ks.next();
            String v = perfil.optString(k, "");
            if (k.isEmpty() || v.isEmpty()) continue;
            if (recuerdos.valor(k) == null) {
                recuerdos.guarda(k, v);
                nuevos++;
            }
        }
        return nuevos;
    }

    /** `GET /api/memories?n=40` — el muro del portátil, deduplicado al bajar. */
    private int bajarMuro(String b) throws IOException {
        String leido = llamar(b + "/api/memories?n=" + MURO_BAJADO, "GET", null);
        JSONObject cuadro = cuadro(leido, "el portátil no contestó con su muro");
        JSONArray lista = cuadro.optJSONArray("recuerdos");
        if (lista == null) return 0;
        int nuevos = 0;
        for (int n = 0; n < lista.length(); n++) {
            JSONObject r = lista.optJSONObject(n);
            if (r == null) continue;
            String texto = r.optString("texto", "").trim();
            if (texto.isEmpty()) continue;
            if (recuerdos.recuerda(texto)) nuevos++;
        }
        return nuevos;
    }

    /* ──────────────────────────────── subir ────────────────────────────────── */

    /**
     * Cada hecho del teléfono, de uno en uno, a `POST /api/profile`. El
     * backend real no acepta lotes en esa ruta (lo comprobado en `main.py`:
     * el modelo `Perfil` es `{clave, valor}` suelto), así que se suben los
     * `TOPE_SUBIDA` más nuevos por viaje y el resto queda para el siguiente;
     * mejor dos viajes honestos que una puerta inventada que devuelva 422.
     */
    private int subirHechos(String b) throws Exception {
        List<String[]> fila = recuerdos.hechos(TOPE_SUBIDA);
        int subidos = 0;
        for (String[] kv : fila) {
            JSONObject cuerpo = new JSONObject();
            cuerpo.put("clave", kv[0]);
            cuerpo.put("valor", kv[1]);
            String leido = llamar(b + "/api/profile", "POST", cuerpo.toString());
            JSONObject respuesta = cuadro(leido, "el portátil contestó cualquiercosa");
            if (respuesta.optBoolean("ok", false)) subidos++;
        }
        return subidos;
    }

    /**
     * Las frases sueltas que CORT apuntó en el teléfono («acuédate de que…») viajan
     * en UN solo `POST /api/memories`, que es la puerta que el backend abrió en
     * esta ronda para que la sincronía dejara de ser de una sola dirección: antes
     * el móvil leía al portátil, pero lo que aprendía se quedaba en el aparato y se
     * perdía al cambiar de teléfono.
     *
     * El portátil responde `{"ok":true,"guardados":N,"ignorados":M}` y deduplica él
     * solo, así que repetir el viaje no duplica el muro. Si la puerta no está (un PC
     * con el backend de una Release vieja) **no se corta el resto de la sincronía**:
     * se cuenta cero subidas, se anota el motivo en `ultimoFallo` y los hechos siguen
     * viajando por `/api/profile`.
     */
    private int subirFrases(String b) {
        List<String> listas = recuerdos.recuerdos(TOPE_SUBIDA);
        if (listas.isEmpty()) return 0;
        JSONArray carga = new JSONArray();
        for (String dicho : listas) carga.put(dicho);
        try {
            JSONObject cuerpo = new JSONObject();
            cuerpo.put("recuerdos", carga);
            String leido = llamar(b + "/api/memories", "POST", cuerpo.toString());
            JSONObject respuesta = cuadro(leido, "el portátil contestó cualquiercosa");
            return respuesta.optInt("guardados", 0);
        } catch (Exception elPortatilNoLaTiene) {
            ultimoFallo = "el portátil no admite /api/memories: mis frases se quedan "
                        + "en el teléfono (actualiza el PC)";
            return 0;
        }
    }

    /* ──────────────────────────────── HTTP ─────────────────────────────────── */

    /**
     * La conexión: 6 + 6 segundos, JSON en las dos puntas y la clave (si la
     * dueña la puso) sólo en cabecera `Authorization`, jamás en la URL ni en
     * el mensaje de un fallo.
     */
    private String llamar(String url, String metodo, String cuerpo) throws IOException {
        HttpURLConnection conexion = null;
        try {
            conexion = (HttpURLConnection) new URL(url).openConnection();
            conexion.setConnectTimeout(CONEXION_MS);
            conexion.setReadTimeout(LECTURA_MS);
            conexion.setRequestMethod(metodo);
            conexion.setRequestProperty("Accept", "application/json");
            String clave = prefs.getString("clave", "");
            if (clave != null && !clave.trim().isEmpty()) {
                conexion.setRequestProperty("Authorization", "Bearer " + clave.trim());
            }
            if (cuerpo != null) {
                conexion.setRequestProperty("Content-Type", "application/json");
                conexion.setDoOutput(true);
                byte[] bytes = cuerpo.getBytes(StandardCharsets.UTF_8);
                // `fixedLengthMode` en vez de `chunked`: un servidor que no
                // acepta troceado cortaría el POST, y el cuerpo ya está entero.
                conexion.setFixedLengthStreamingMode(bytes.length);
                OutputStream salida = conexion.getOutputStream();
                try {
                    salida.write(bytes);
                } finally {
                    salida.close();
                }
            }
            int codigo = conexion.getResponseCode();
            if (codigo == 404) {
                throw new IOException("el portátil no tiene esa puerta (404): "
                        + "¿backend sin /api/profile o /api/memories?");
            }
            if (codigo == 401 || codigo == 403) {
                throw new IOException("el portátil no reconoce la llave puesta");
            }
            String leido = lee(codigo >= 400 ? conexion.getErrorStream()
                                             : conexion.getInputStream());
            if (codigo >= 400) {
                throw new IOException("el portátil contestó " + codigo);
            }
            return leido;
        } finally {
            if (conexion != null) {
                try { conexion.disconnect(); } catch (Exception yaCayo) { /* nada */ }
            }
        }
    }

    /** JSON de verdad, o el motivo por el que no lo es. */
    private static JSONObject cuadro(String leido, String motivo) throws IOException {
        try {
            return new JSONObject(leido);
        } catch (Exception noEsJson) {
            throw new IOException(motivo);
        }
    }

    /** Leer un InputStream entero a UTF-8, sin librerías y cerrando siempre. */
    private static String lee(InputStream entrada) throws IOException {
        if (entrada == null) return "";
        try {
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();
            byte[] trozo = new byte[4096];
            int n;
            while ((n = entrada.read(trozo)) > 0) {
                buffer.write(trozo, 0, n);
            }
            return new String(buffer.toByteArray(), StandardCharsets.UTF_8);
        } finally {
            try { entrada.close(); } catch (Exception yaCerrado) { /* nada */ }
        }
    }

    /* ─────────────────────────────── la dirección ──────────────────────────── */

    /**
     * `cort` / `pc` como la escribe `MainActivity.guardarPC` (p.ej.
     * `http://192.168.1.30:8000`). Sin esquema se asume `http://` — la LAN no
     * sirve HTTPS por sí sola — y se corta la barra final para no montar
     * `//api`. Vacío o nulo es `null`: no hay portátil que llamar.
     */
    private String base() {
        String cruda;
        try { cruda = prefs.getString("pc", ""); } catch (Exception prefsRaras) { return null; }
        if (cruda == null) return null;
        String limpia = cruda.trim();
        if (limpia.isEmpty()) return null;
        String baja = limpia.toLowerCase(Locale.US);
        if (!baja.startsWith("http://") && !baja.startsWith("https://")) {
            limpia = "http://" + limpia;
        }
        while (limpia.endsWith("/")) limpia = limpia.substring(0, limpia.length() - 1);
        return limpia.contains("://") && limpia.length() > "http://".length() ? limpia : null;
    }

    /* ────────────────────────────── JSON a mano ───────────────────────────── */

    /** El mismo patrón que `CortNative.comilla`; la clave nunca pasa por aquí. */
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
