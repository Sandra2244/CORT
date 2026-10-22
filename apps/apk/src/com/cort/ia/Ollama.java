package com.cort.ia;

/*
 * Ollama.java — los cerebros grandes de la casa, manejados desde el teléfono.
 *
 * Por qué existe: la dueña dijo «necesito que CORT sí pueda instalar modelos
 * locales de Ollama y que la terminal funcione con esos cerebros, porque online
 * con Gemini me da fallas». Hay que decir la verdad por delante: **Ollama no cabe
 * dentro de un APK** — es un servidor escrito en Go que espera Linux y una API de
 * red; no hay forma de meterlo en Android sin Gradle, NDK y medio mundo. Lo que
 * SÍ cabe, y es lo que ella quiere decir, es *mandarlo*: los modelos que instala
 * Ollama son archivos GGUF con un servidor HTTP al lado, y un servidor HTTP se
 * maneja perfectamente desde el teléfono por Wi-Fi.
 *
 * Este archivo habla con ese servidor por su API propia, leída en la documentación
 * oficial de `ollama/ollama` (`docs/api.md` y `docs/faq.mdx`, consultadas el
 * 2026-10-21 antes de escribir una sola línea):
 *
 *   GET    /api/tags     → `{"models":[{"name","model","size","digest",
 *                            "modified_at","parameter_size","quantization_level"}]}`
 *   POST   /api/pull     → streams NDJSON: `{"status","digest","total","completed"}`
 *   DELETE /api/delete   → cuerpo `{"model": …}` (las versiones viejas aceptaban
 *                          `POST /api/delete` con `{"name": …}`: se prueba uno y, si
 *                          el servidor lo rechaza, el otro; no se adivina la versión)
 *   GET    /api/version  → `{"version": …}`
 *
 * Y el detalle que decide que esto funcione o no: por defecto Ollama sólo escucha
 * en `localhost`, así que desde el teléfono NO se ve. En el PC hay que arrancarlo
 * con `OLLAMA_HOST=0.0.0.0:11434` (en Linux, `systemctl edit ollama.service` ▸
 * `Environment="OLLAMA_HOST=0.0.0.0:11434"` ▸ `daemon-reload` ▸ `restart`). La cara
 * lo recuerda en cada pantalla, porque sin eso el error de CORT sería «no encuentro
 * ningún servidor» y la culpa sería de un ajuste del PC, no de la app.
 *
 * Tres reglas que heredan de `Nube` y no se rompen aquí:
 *
 * 1. **Nada de red en el hilo del puente.** Todos los métodos de esta clase son
 *    BLOQUEANTES y los llama sólo el hilo `cort-mente` (o `cort-ollama`) que
 *    despacha `Mente`. Un `@JavascriptInterface` que abriera `HttpURLConnection`
 *    revienta con `NetworkOnMainThreadException`.
 * 2. **Nunca lanza.** Cualquier fallo deja `ultimoFallo` escrito y devuelve un
 *    `{"ok":false,"dice":…}`; la cara sigue funcionando con `Cerebro`/`Razon`.
 * 3. **El escaneo es de su casa y se pide.** `descubre` sólo barre el /24 de la
 *    propia dirección del teléfono (la que da `NetworkInterface`, sin permiso
 *    nuevo) y sólo cuando la dueña pulsa «buscar». No se hace por detrás, no se
 *    envía a internet, y ni siquiera se abre un socket fuera de esa subred.
 *
 * La descarga de un modelo es lenta (gigabytes) y viene en trozos: por eso `pull`
 * emite progreso por callback en vez de esperar al final, igual que hace `Oido`
 * con el desempaque del modelo de Vosk.
 */

import android.content.Context;
import android.content.SharedPreferences;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.net.SocketTimeoutException;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Enumeration;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

public class Ollama {

    /** Cómo llega la cara al resultado largo de una descarga: un cuadro por trozo. */
    public interface Progreso { void dice(String json); }

    private static final int CONEXION_MS = 2500;      // en casa contestan enseguida
    private static final int LECTURA_MS = 12000;      // /api/tags y /api/version
    private static final int LECTURA_PULL_MS = 90000; // un trozo de gigabyte tarda
    private static final int SONDEO_MS = 260;         // qué dirección tiene el puerto abierto
    private static final int HILOS_BUSQUEDA = 24;     // 254 direcciones, 24 a la vez
    private static final int PUERTO = 11434;          // el puerto de casa de Ollama

    private final SharedPreferences prefs;
    private String ultimoFallo = "";

    Ollama(Context contexto) {
        this.prefs = contexto.getApplicationContext()
                             .getSharedPreferences("cort", Context.MODE_PRIVATE);
    }

    /* ───────────────────────────── de dónde hablo ───────────────── */

    /** La dirección elegida: `host` o `host:puerto`. Vacía = la que diga `Nube`. */
    public String servidor() {
        String guardado = prefs.getString("ollama-servidor", "").trim();
        if (!guardado.isEmpty()) return guardado;
        // Sin elección propia se aprovecha lo que ya está puesto: si el proveedor
        // es `ollama`, su base lleva el host dentro (`http://IP:11434/v1`).
        String origen = origen(prefs.getString("nube-base", ""));
        return origen.isEmpty() ? "" : hostDe(origen);
    }

    public int puerto() {
        String s = servidor();
        int i = s.indexOf(':');
        if (i < 0) return PUERTO;
        try { return Integer.parseInt(s.substring(i + 1).trim()); }
        catch (NumberFormatException mal) { return PUERTO; }
    }

    /** `http://192.168.1.5:11434` a partir de una base, con `/v1` o sin él. */
    static String origen(String base) {
        String b = base == null ? "" : base.trim();
        if (b.isEmpty()) return "";
        if (!b.startsWith("http")) b = "http://" + b;
        while (b.endsWith("/")) b = b.substring(0, b.length() - 1);
        if (b.endsWith("/v1")) b = b.substring(0, b.length() - 3);
        while (b.endsWith("/")) b = b.substring(0, b.length() - 1);
        return b;
    }

    /** El `host:puerto` que hay dentro de una URL de origen. */
    static String hostDe(String url) {
        String s = url.startsWith("http://") ? url.substring(7)
                 : url.startsWith("https://") ? url.substring(8) : url;
        int barra = s.indexOf('/');
        if (barra >= 0) s = s.substring(0, barra);
        return s;
    }

    private String raiz() {
        String s = servidor();
        if (s.isEmpty()) return "";
        return s.contains("://") ? origen(s) : "http://" + s;
    }

    public String ultimoFallo() { return ultimoFallo; }

    /* ─────────────────────────── estado (sin red) ───────────────── */

    /** Lo que la cara pinta antes de preguntar nada: a dónde iría a hablar. */
    public String estadoJson() {
        String r = raiz();
        return "{\"ok\":true,\"de\":\"ollama\",\"que\":\"estado\""
             + ",\"servidor\":" + comilla(servidor())
             + ",\"origen\":" + comilla(r)
             + ",\"puerto\":" + puerto()
             + ",\"modelo\":" + comilla(prefs.getString("nube-modelo", ""))
             + ",\"eligeNube\":\"" + ("ollama".equals(prefs.getString("nube-proveedor", ""))) + "\""
             + "}";
    }

    /* ───────────────────────────── versión y lista ──────────────── */

    /** `GET /api/version` — el ping corto que usa `descubre` y el botón de probar. */
    public String version(String servidorCandidato) {
        String url = "http://" + quitaEsquema(servidorCandidato) + "/api/version";
        try {
            JSONObject j = new JSONObject(get(url, CONEXION_MS, 3500));
            return j.optString("version", "?");
        } catch (Exception noContesta) {
            return null;
        }
    }

    /**
     * `GET /api/tags` — los modelos que ya están instalados en ese PC.
     * Devuelve el cuadro completo para la cara (con `modelos`), o `ok:false`.
     */
    public String lista() {
        ultimoFallo = "";
        String r = raiz();
        if (r.isEmpty()) { ultimoFallo = "no sé dónde está Ollama: pulsa «buscar en tu Wi-Fi»"; return mal("lista", ultimoFallo); }
        try {
            JSONObject j = new JSONObject(get(r + "/api/tags", CONEXION_MS, LECTURA_MS));
            JSONArray bruto = j.optJSONArray("models");
            JSONArray limpios = new JSONArray();
            if (bruto != null) {
                for (int i = 0; i < bruto.length(); i++) {
                    JSONObject m = bruto.optJSONObject(i);
                    if (m == null) continue;
                    // La documentacion trae `name` y `model`; las versiones viejas
                    // sólo `name`. Se toman los dos y se elige el que venga.
                    String nombre = m.optString("name", m.optString("model", ""));
                    if (nombre.isEmpty()) continue;
                    JSONObject det = m.optJSONObject("details");    // anidada en las nuevas
                    limpios.put(new JSONObject()
                        .put("nombre", nombre)
                        .put("tamano", m.optLong("size", 0))
                        .put("parametros", primero(m, det, "parameter_size"))
                        .put("cuantizacion", primero(m, det, "quantization_level"))
                        .put("modificado", m.optString("modified_at", "")));
                }
            }
            // `/api/tags` NO trae la versión del servidor (eso es de `/api/version`),
            // así que se pide aparte y, si falla, se deja vacío: la lista de modelos
            // vale aunque la versión no conteste.
            String ver = j.optString("version", "");
            if (ver.isEmpty()) { String v = version(servidor()); ver = v == null ? "" : v; }
            return "{\"ok\":true,\"de\":\"ollama\",\"que\":\"lista\""
                 + ",\"servidor\":" + comilla(servidor())
                 + ",\"version\":" + comilla(ver)
                 + ",\"modelos\":" + limpios.toString()
                 + ",\"total\":" + limpios.length() + "}";
        } catch (SocketTimeoutException tardo) {
            ultimoFallo = "el PC no contestó a tiempo: ¿está Ollama arrancado con OLLAMA_HOST=0.0.0.0:11434?";
            return mal("lista", ultimoFallo);
        } catch (IOException noHay) {
            ultimoFallo = "no llego a " + servidor() + " por esta Wi-Fi";
            return mal("lista", ultimoFallo);
        } catch (Exception bulto) {
            ultimoFallo = "Ollama respondió algo que no es JSON";
            Log.w("cort", "ollama-lista", bulto);
            return mal("lista", ultimoFallo);
        }
    }

    private static String primero(JSONObject m, JSONObject det, String clave) {
        if (det != null && det.has(clave)) return det.optString(clave, "");
        return m.optString(clave, "");
    }

    /* ───────────────────────────── descargar ────────────────────── */

    /**
     * `POST /api/pull` con el modelo pedido. El servidor va tirando líneas NDJSON
     * (`status`, `digest`, `total`, `completed`); de ahí sale el progreso real, que
     * es lo que la dueña espera ver moverse. Se emite un cuadro cuando cambia el
     * estado, cuando el porcentaje salta 5 puntos, cuando pasan ~400 ms, y uno
     * final con `listo`, para no ahogar a la cara de eventos.
     */
    public String descarga(String modelo, Progreso sigue) {
        ultimoFallo = "";
        String r = raiz();
        if (r.isEmpty()) { ultimoFallo = "no sé dónde está Ollama: pulsa «buscar en tu Wi-Fi»"; return mal("descarga", ultimoFallo); }
        if (modelo == null || modelo.trim().isEmpty()) { ultimoFallo = "dime qué modelo bajar"; return mal("descarga", ultimoFallo); }
        String nombre = modelo.trim();
        long ultimoEnvio = 0;
        double puntoEnvio = 0;
        try {
            HttpURLConnection c = post(r + "/api/pull", "{\"model\":\"" + escapa(nombre)
                                  + "\",\"name\":\"" + escapa(nombre) + "\",\"insecure\":true}",
                                  CONEXION_MS, LECTURA_PULL_MS);
            InputStream entrada = c.getInputStream();          // 2xx: stream abierto
            java.io.BufferedReader lector = new java.io.BufferedReader(
                new java.io.InputStreamReader(entrada, StandardCharsets.UTF_8));
            String linea;
            String estado = "empezando";
            long total = 0, hecho = 0;
            boolean error = false, motes = false;
            while ((linea = lector.readLine()) != null) {
                if (linea.trim().isEmpty()) continue;
                JSONObject j;
                try { j = new JSONObject(linea); } catch (Exception basura) { continue; }
                if (j.has("error")) {
                    error = true;
                    ultimoFallo = j.optString("error", "el servidor no pudo bajar el modelo");
                    break;
                }
                String antes = estado;
                estado = j.optString("status", estado);
                total = j.optLong("total", total);
                hecho = j.optLong("completed", hecho);
                if ("success".equals(estado)) motes = true;
                double pct = total > 0 ? Math.min(1.0, (double) hecho / total) : 0;
                long ahora = System.currentTimeMillis();
                /* Tres motivos para emitir, en este orden de importancia: cambió el
                   estado ("descargando" → "verificando" → "success"), el porcentaje
                   se movió 5 puntos o más, o ya pasó medio segundo. Con sólo el
                   reloj, una descarga rápida por red local manda dos cuadros y la
                   barra de la cara no se mueve nunca; con los tres, el progreso se
                   ve aunque el servidor responda en un suspiro. */
                boolean cambioEstado = !estado.equals(antes);
                boolean salto = pct - puntoEnvio >= 0.05;
                if (sigue != null && (cambioEstado || salto || ahora - ultimoEnvio > 400 || motes)) {
                    ultimoEnvio = ahora;
                    puntoEnvio = pct;
                    sigue.dice("{\"ok\":true,\"de\":\"ollama\",\"que\":\"descarga\""
                        + ",\"modelo\":" + comilla(nombre)
                        + ",\"estado\":" + comilla(estado)
                        + ",\"hecho\":" + hecho + ",\"total\":" + total
                        + ",\"porcentaje\":" + String.format(java.util.Locale.ROOT, "%.4f", pct) + "}");
                }
            }
            cerr(lector);
            c.disconnect();
            if (error) return mal("descarga", ultimoFallo);
            if (!motes) Log.i("cort", "ollama-pull terminó sin 'success': " + estado);
            return "{\"ok\":true,\"de\":\"ollama\",\"que\":\"descarga\""
                 + ",\"modelo\":" + comilla(nombre)
                 + ",\"listo\":" + motes
                 + ",\"estado\":" + comilla(estado)
                 + ",\"hecho\":" + hecho + ",\"total\":" + total + "}";
        } catch (SocketTimeoutException tardo) {
            ultimoFallo = "el PC dejó de mandar trozos: el modelo sigue bajando por su lado o se cortó la Wi-Fi";
            return mal("descarga", ultimoFallo);
        } catch (IOException noHay) {
            ultimoFallo = "no llego a " + servidor() + " (" + noHay.getMessage() + ")";
            return mal("descarga", ultimoFallo);
        } catch (Exception bulto) {
            ultimoFallo = "no pude bajar " + nombre;
            Log.w("cort", "ollama-pull", bulto);
            return mal("descarga", ultimoFallo);
        }
    }

    /* ─────────────────────────── borrar y usar ──────────────────── */

    /** `DELETE /api/delete`; si el servidor es viejo, prueba el `POST {"name":…}`. */
    public String borra(String modelo) {
        ultimoFallo = "";
        String r = raiz();
        String nombre = modelo == null ? "" : modelo.trim();
        if (r.isEmpty() || nombre.isEmpty()) { ultimoFallo = "sin servidor o sin modelo"; return mal("borra", ultimoFallo); }
        try {
            int codigo = método(r + "/api/delete", "{\"model\":\"" + escapa(nombre) + "\"}", "DELETE");
            if (codigo >= 200 && codigo < 300) return cuadroBorra(nombre, "borrado");
            if (codigo == 405 || codigo == 400 || codigo == 404) {     // el modo viejo
                int viejo = método(r + "/api/delete", "{\"name\":\"" + escapa(nombre) + "\"}", "POST");
                if (viejo >= 200 && viejo < 300) return cuadroBorra(nombre, "borrado (API antigua)");
            }
            ultimoFallo = "el servidor contestó " + codigo;
            return mal("borra", ultimoFallo);
        } catch (Exception noSePudo) {
            ultimoFallo = "no pude borrar " + nombre;
            Log.w("cort", "ollama-delete", noSePudo);
            return mal("borra", ultimoFallo);
        }
    }

    private String cuadroBorra(String nombre, String como) {
        return "{\"ok\":true,\"de\":\"ollama\",\"que\":\"borra\",\"modelo\":"
             + comilla(nombre) + ",\"como\":" + comilla(como) + "}";
    }

    /**
     * Poner este modelo como cerebro: escribe lo que `Nube` lee para hablar
     * (`nube-proveedor`, `nube-base`, `nube-modelo`) y deja además el host en
     * `ollama-servidor`, que es la preferencia de esta clase. A partir de aquí
     * «pregunta» se contesta con el modelo local, sin clave y sin internet.
     */
    public String usa(String modelo) {
        String r = raiz();
        String nombre = modelo == null ? "" : modelo.trim();
        if (r.isEmpty() || nombre.isEmpty()) { ultimoFallo = "sin servidor o sin modelo"; return mal(ultimoFallo); }
        SharedPreferences.Editor e = prefs.edit();
        e.putString("ollama-servidor", servidor());
        e.putString("nube-proveedor", "ollama");
        e.putString("nube-base", r + "/v1");
        e.putString("nube-modelo", nombre);
        e.apply();
        return "{\"ok\":true,\"de\":\"ollama\",\"que\":\"usa\",\"modelo\":" + comilla(nombre)
             + ",\"base\":" + comilla(r + "/v1")
             + ",\"dice\":" + comilla("listo: pienso con " + nombre + " en " + servidor()) + "}";
    }

    /**
     * La dirección que la dueña escribe a mano (o la que encontró `descubre`).
     * Acepta `192.168.1.20`, `192.168.1.20:11434`, `http://…:11434` y hasta la base
     * con `/v1` que sale de `usa`. Se guarda SIEMPRE —puede que el PC esté dormido—
     * y se avisa honestamente de si contestó o no, que es lo que decide si la lista
     * de modelos va a salir.
     */
    public String fija(String direccion) {
        ultimoFallo = "";
        String r = origen(direccion == null ? "" : direccion.trim());
        String host = hostDe(r);
        if (host.isEmpty() || !host.matches("[A-Za-z0-9._-]+([:][0-9]{1,5})?")) {
            ultimoFallo = "esa dirección no la entiendo: escribe algo como 192.168.1.20:11434";
            return mal("fija", ultimoFallo);
        }
        SharedPreferences.Editor e = prefs.edit();
        e.putString("ollama-servidor", host);
        e.apply();
        String ver = version(host);
        boolean contesta = ver != null;
        String dicho = contesta
            ? "listo: Ollama " + ver + " en " + host
            : "guardado en " + host + ", pero ahora no contesta. Que el PC esté encendido, "
              + "en la misma Wi-Fi y con OLLAMA_HOST=0.0.0.0:11434.";
        if (!contesta) ultimoFallo = dicho;
        return "{\"ok\":true,\"de\":\"ollama\",\"que\":\"fija\",\"servidor\":" + comilla(host)
             + ",\"origen\":" + comilla(r)
             + ",\"version\":" + comilla(contesta ? ver : "")
             + ",\"contesta\":" + contesta
             + ",\"dice\":" + comilla(dicho) + "}";
    }

    /* ───────────────────────── buscar en la Wi-Fi ───────────────── */

    /**
     * Barre el /24 de la propia dirección del teléfono buscando el puerto 11434 y
     * devuelve los Ollama que contestan, con su versión. Se hace en paralelo y con
     * sockets de 260 ms: en una red de casa son dos o tres segundos.
     *
     * No pide ningún permiso nuevo: `NetworkInterface.getNetworkInterfaces()` no
     * necesita `ACCESS_WIFI_STATE` (eso es para el SSID); aquí sólo se mira la
     * dirección IPv4 local del teléfono y se deriva el rango.
     */
    public String descubre() { return descubre(""); }

    /**
     * Igual, pero con la lista de host(es) que manda la cara separados por coma o
     * espacio. Sirve para dos cosas: decir «mira sólo en 192.168.1.20» en vez de
     * barrer el /24 entero, y probar sin tocar la red de nadie (la suite `Prueba4`
     * pasa el `127.0.0.1:puerto` del servidor de mentira; en un runner de GitHub el
     * barrido completo no debería hacerse nunca).
     */
    public String descubre(String explicito) {
        ultimoFallo = "";
        List<String> candidatos = new ArrayList<>();
        Set<String> vistos = new LinkedHashSet<>();
        String prefijo = "";
        boolean barrido = explicito == null || explicito.trim().isEmpty();
        if (barrido) {
            // 1 · lo que ya se conoce: el servidor elegido y la IP del PC del modo holograma
            if (!servidor().isEmpty()) candidatos.add(conPuerto(servidor()));
            // La dirección del portátil se guarda con el puerto del backend (`:8000`),
            // así que aquí se quita el puerto y se pone el de Ollama: si no, se estaría
            // llamando a la puerta de FastAPI y el barrido no diría nada útil.
            String pc = sinPuerto(hostDe(origen(prefs.getString("pc", ""))));
            if (!pc.isEmpty() && vistos.add(pc)) candidatos.add(pc + ":" + PUERTO);
            // 2 · el /24 propio
            prefijo = prefijoLocal();
            if (!prefijo.isEmpty()) for (int i = 1; i <= 254; i++) candidatos.add(prefijo + "." + i);
        } else {
            for (String h : explicito.split("[,\\s]+")) if (!h.trim().isEmpty()) candidatos.add(conPuerto(h));
        }
        if (candidatos.isEmpty()) { ultimoFallo = "no encuentro la dirección Wi-Fi de este teléfono"; return mal("descubre", ultimoFallo); }

        ExecutorService pool = Executors.newFixedThreadPool(HILOS_BUSQUEDA);
        List<String> vivos = Collections.synchronizedList(new ArrayList<String>());
        try {
            List<Future<String>> tareas = new ArrayList<>();
            for (final String host : candidatos) {
                tareas.add(pool.submit(new Callable<String>() {
                    @Override public String call() {
                        String h = conPuerto(host);
                        String v = version(h);
                        return v == null ? null : h + "|" + v;
                    }
                }));
            }
            for (Future<String> t : tareas) {
                try {
                    String r = t.get(4, TimeUnit.SECONDS);
                    if (r != null) {
                        String[] partes = r.split("\\|", 2);
                        if (vistos.add(partes[0])) {
                            vivos.add("{\"host\":" + comilla(partes[0])
                                    + ",\"version\":" + comilla(partes.length > 1 ? partes[1] : "") + "}");
                        }
                    }
                } catch (Exception eseHostNo) { /* un futuro roto no cancela el barrido */ }
            }
        } catch (Exception elBarridoSeTorcio) {
            Log.w("cort", "ollama-descubre", elBarridoSeTorcio);
        } finally {
            pool.shutdownNow();
        }
        if (vivos.isEmpty()) {
            ultimoFallo = "nadie contesta al 11434 en " + (prefijo.isEmpty() ? "la red" : prefijo + ".0/24")
                        + ": arranca Ollama en el PC con OLLAMA_HOST=0.0.0.0:11434";
            return mal("descubre", ultimoFallo);
        }
        StringBuilder s = new StringBuilder("[");
        for (int i = 0; i < vivos.size(); i++) { if (i > 0) s.append(','); s.append(vivos.get(i)); }
        return "{\"ok\":true,\"de\":\"ollama\",\"que\":\"descubre\""
             + ",\"rango\":" + comilla(prefijo.isEmpty() ? "(sólo conocidos)" : prefijo + ".0/24")
             + ",\"probados\":" + candidatos.size()
             + ",\"servidores\":" + s.append(']').toString() + "}";
    }

    /** `192.168.1` a partir de la IPv4 `site-local` del teléfono; vacío si no la hay. */
    static String prefijoLocal() {
        try {
            Enumeration<NetworkInterface> ifs = NetworkInterface.getNetworkInterfaces();
            while (ifs != null && ifs.hasMoreElements()) {
                NetworkInterface ni = ifs.nextElement();
                if (!ni.isUp() || ni.isLoopback()) continue;
                Enumeration<InetAddress> as = ni.getInetAddresses();
                while (as.hasMoreElements()) {
                    InetAddress a = as.nextElement();
                    if (a instanceof Inet4Address && a.isSiteLocalAddress()) {
                        String[] p = a.getHostAddress().split("\\.");
                        if (p.length == 4) return p[0] + "." + p[1] + "." + p[2];
                    }
                }
            }
        } catch (Exception sinRed) {
            Log.w("cort", "prefijoLocal", sinRed);
        }
        return "";
    }

    private static String sinPuerto(String host) {
        int i = host.indexOf(':');
        return i < 0 ? host : host.substring(0, i);
    }

    private static String conPuerto(String host) {
        String s = quitaEsquema(host);
        return s.contains(":") ? s : s + ":" + PUERTO;
    }

    private static String quitaEsquema(String s) {
        String t = s == null ? "" : s.trim();
        if (t.startsWith("http://")) t = t.substring(7);
        if (t.startsWith("https://")) t = t.substring(8);
        int barra = t.indexOf('/');
        return barra >= 0 ? t.substring(0, barra) : t;
    }

    /* ───────────────────────────── HTTP claro ───────────────────── */

    private static String get(String url, int conexion, int lectura) throws IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(conexion);
        c.setReadTimeout(lectura);
        c.setRequestMethod("GET");
        c.setRequestProperty("Accept", "application/json");
        int codigo = c.getResponseCode();
        String cuerpo = lee(codigo >= 400 ? c.getErrorStream() : c.getInputStream());
        c.disconnect();
        if (codigo >= 400) throw new IOException("HTTP " + codigo + " en " + url);
        return cuerpo;
    }

    private static HttpURLConnection post(String url, String cuerpo, int conexion, int lectura) throws IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(conexion);
        c.setReadTimeout(lectura);
        c.setRequestMethod("POST");
        c.setRequestProperty("Content-Type", "application/json");
        c.setRequestProperty("Accept", "application/json");
        c.setDoOutput(true);
        byte[] p = cuerpo.getBytes(StandardCharsets.UTF_8);
        OutputStream salida = c.getOutputStream();
        try { salida.write(p); salida.flush(); } finally { cerr(salida); }
        if (c.getResponseCode() >= 400) {
            String detalle = lee(c.getErrorStream());
            c.disconnect();
            throw new IOException("HTTP " + c.getResponseCode() + ": " + recorta(detalle, 160));
        }
        return c;
    }

    /** Una llamada que sólo importa por su código de respuesta (el `DELETE`). */
    private static int método(String url, String cuerpo, String metodo) throws IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(CONEXION_MS);
        c.setReadTimeout(LECTURA_MS);
        c.setRequestMethod(metodo);
        c.setRequestProperty("Content-Type", "application/json");
        c.setDoOutput(true);
        OutputStream salida = c.getOutputStream();
        try { salida.write(cuerpo.getBytes(StandardCharsets.UTF_8)); salida.flush(); } finally { cerr(salida); }
        int codigo = c.getResponseCode();
        // El cuerpo se lee y se tira: en `DELETE` sólo importa el código, y dejar
        // la corriente sin consumir deja el socket sucio en algunos servidores.
        if (entradaSirve(codigo)) lee(c.getInputStream()); else lee(c.getErrorStream());
        c.disconnect();
        return codigo;
    }

    private static boolean entradaSirve(int codigo) { return codigo < 400; }

    private static String lee(InputStream entrada) throws IOException {
        if (entrada == null) return "";
        try {
            ByteArrayOutputStream b = new ByteArrayOutputStream();
            byte[] trozo = new byte[4096];
            int n;
            while ((n = entrada.read(trozo)) > 0) b.write(trozo, 0, n);
            return new String(b.toByteArray(), StandardCharsets.UTF_8);
        } finally {
            cerr(entrada);
        }
    }

    private static void cerr(java.io.Closeable c) {
        if (c != null) try { c.close(); } catch (Exception ignorado) { }
    }

    private static String recorta(String s, int n) {
        String t = s == null ? "" : s.trim();
        return t.length() <= n ? t : t.substring(0, n);
    }

    /* ───────────────────────────── JSON a mano ──────────────────── */

    private static String mal(String dice) {
        return "{\"ok\":false,\"de\":\"ollama\",\"dice\":" + comilla(dice) + "}";
    }

    /**
     * Como `mal`, pero diciendo QUÉ acción falló. La cara lo necesita: sin el `que`
     * no se sabe si hay que bajar la barra de una descarga o sólo avisar en la hoja.
     */
    private static String mal(String que, String dice) {
        return "{\"ok\":false,\"de\":\"ollama\",\"que\":" + comilla(que) + ",\"dice\":" + comilla(dice) + "}";
    }

    private static String escapa(String s) {
        return s == null ? "" : s.replace("\\", "\\\\").replace("\"", "\\\"");
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
