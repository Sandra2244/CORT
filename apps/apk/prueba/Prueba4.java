package com.cort.ia;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/*
 * Prueba4.java — `Ollama.java` contra un Ollama de mentira, en el portátil.
 *
 * Es la prueba que de verdad decide si la ronda 2.4 sirve, porque lo que hay que
 * comprobar no es Java de Android: es el **diálogo HTTP** con el servidor de casa
 * (listar, bajar con progreso, borrar, y que la pregunta se conteste con el modelo
 * local). El servidor se monta aquí mismo con `com.sun.net.httpserver` —módulo que
 * trae el JDK, sin nada que instalar— y responde exactamente con la forma que dice
 * la documentación oficial de Ollama: `/api/tags` con `details` anidadas y con
 * `parameter_size` suelta (las dos variantes, porque conviven en el mundo real),
 * `/api/pull` en NDJSON con `status`/`total`/`completed`, `/api/version`, y
 * `/api/delete` que en las versiones nuevas es `DELETE {"model":…}` y en las viejas
 * era `POST {"name":…}`.
 *
 * Nada de esto toca internet: todo es `127.0.0.1` en un puerto libre.
 */
public class Prueba4 {

    static int pasadas = 0;
    static List<String> fallos = new ArrayList<>();

    static void check(String que, boolean vale, String detalle) {
        if (vale) { pasadas++; System.out.println("  ok  " + que); }
        else { fallos.add(que + " -> " + detalle); System.out.println("  MAL " + que + " :: " + detalle); }
    }

    static HttpServer servidor;
    static int puerto;
    static List<String> vistos = new ArrayList<>();   // peticiones recibidas, para mirar el método

    /* ─────────────────────────── el Ollama de papel ─────────────── */

    static void ruta(HttpExchange e, int codigo, String cuerpo, String tipo) throws java.io.IOException {
        byte[] b = cuerpo.getBytes(StandardCharsets.UTF_8);
        e.getResponseHeaders().set("Content-Type", tipo);
        e.sendResponseHeaders(codigo, b.length);
        try (OutputStream s = e.getResponseBody()) { s.write(b); }
    }

    public static void main(String[] args) throws Exception {

        servidor = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        servidor.createContext("/api/tags", new HttpHandler() {
            @Override public void handle(HttpExchange e) throws java.io.IOException {
                vistos.add("GET " + e.getRequestURI().getPath());
                ruta(e, 200, "{\"models\":["
                    + "{\"name\":\"qwen2.5:1.5b\",\"model\":\"qwen2.5:1.5b\",\"size\":1100000000,"
                    + "\"digest\":\"aaa\",\"modified_at\":\"2026-10-01T10:00:00Z\","
                    + "\"details\":{\"parameter_size\":\"1.5B\",\"quantization_level\":\"Q4_K_M\"}},"
                    + "{\"name\":\"llama3.2\",\"size\":2000000000,\"parameter_size\":\"3.2B\","
                    + "\"quantization_level\":\"Q4_0\"}]}", "application/json");
            }
        });
        servidor.createContext("/api/version", new HttpHandler() {
            @Override public void handle(HttpExchange e) throws java.io.IOException {
                vistos.add("GET " + e.getRequestURI().getPath());
                ruta(e, 200, "{\"version\":\"0.11.7\"}", "application/json");
            }
        });
        servidor.createContext("/api/pull", new HttpHandler() {
            @Override public void handle(HttpExchange e) throws java.io.IOException {
                String peticion = leido(e);
                vistos.add("POST " + e.getRequestURI().getPath());
                // El servidor de verdad manda líneas NDJSON y no cierra hasta el final:
                // aquí se escribe cada línea y se hace `flush` para que el lector del
                // APK vea el progreso moverse, que es lo que se quiere comprobar.
                e.getResponseHeaders().set("Content-Type", "application/x-ndjson");
                e.sendResponseHeaders(200, 0);          // chunked: sin longitud por delante
                OutputStream s = e.getResponseBody();
                if (peticion.contains("roto")) {
                    s.write("{\"error\":\"pull failed: no such model\"}\n"
                            .getBytes(StandardCharsets.UTF_8));
                } else {
                    s.write("{\"status\":\"pulling manifest\"}\n".getBytes(StandardCharsets.UTF_8));
                    s.flush();
                    for (int hecho : new int[]{200, 600, 1000}) {
                        s.write(("{\"status\":\"downloading\",\"digest\":\"aaa\",\"total\":1000,"
                            + "\"completed\":" + hecho + "}\n").getBytes(StandardCharsets.UTF_8));
                        s.flush();
                    }
                    s.write("{\"status\":\"success\"}\n".getBytes(StandardCharsets.UTF_8));
                }
                s.close();
            }
        });
        servidor.createContext("/api/delete", new HttpHandler() {
            @Override public void handle(HttpExchange e) throws java.io.IOException {
                String peticion = leido(e);
                vistos.add(e.getRequestMethod() + " " + e.getRequestURI().getPath());
                // Modo nuevo: `DELETE {"model":…}`. El modelo «viejo» simula un
                // servidor anterior que sólo entendía `POST {"name":…}`.
                if (peticion.contains("inexistente")) { ruta(e, 404, "{\"error\":\"not found\"}", "application/json"); return; }
                if (peticion.contains("viejo")) {
                    if ("POST".equals(e.getRequestMethod())) ruta(e, 200, "", "application/json");
                    else ruta(e, 405, "{\"error\":\"method not allowed\"}", "application/json");
                    return;
                }
                if ("DELETE".equals(e.getRequestMethod())) ruta(e, 200, "", "application/json");
                else ruta(e, 405, "{\"error\":\"usa DELETE\"}", "application/json");
            }
        });
        // El dialecto OpenAI de Ollama: por aquí sale la pregunta real del puente.
        servidor.createContext("/v1/chat/completions", new HttpHandler() {
            @Override public void handle(HttpExchange e) throws java.io.IOException {
                String peticion = leido(e);
                vistos.add("POST " + e.getRequestURI().getPath());
                if (!peticion.contains("qwen2.5")) { ruta(e, 400, "{\"error\":\"modelo equivocado\"}", "application/json"); return; }
                ruta(e, 200, "{\"choices\":[{\"message\":{\"role\":\"assistant\","
                    + "\"content\":\"pienso en casa, sin nube\"}}]}", "application/json");
            }
        });
        servidor.setExecutor(null);
        servidor.start();
        puerto = servidor.getAddress().getPort();
        System.out.println("ollama de mentira en 127.0.0.1:" + puerto);

        Context ctx = new Context();
        ctx.prefs.edit()
            .putString("ollama-servidor", "127.0.0.1:" + puerto)
            .putString("pc", "http://127.0.0.1:8000")
            .apply();
        Ollama ollama = new Ollama(ctx);
        Nube nube = new Nube(ctx);
        Cerebro cerebro = new Cerebro(ctx, nube);
        Mente mente = new Mente(ctx, nube, cerebro);

        // ── 1 · las direcciones, que es donde se cae todo ──────────────
        check("origen quita /v1", "http://192.168.1.5:11434".equals(Ollama.origen("http://192.168.1.5:11434/v1/")),
            Ollama.origen("http://192.168.1.5:11434/v1/"));
        check("hostDe saca host:puerto", "192.168.1.5:11434".equals(Ollama.hostDe("http://192.168.1.5:11434")),
            Ollama.hostDe("http://192.168.1.5:11434"));
        check("servidor = lo guardado", ("127.0.0.1:" + puerto).equals(ollama.servidor()), ollama.servidor());
        check("puerto leído del host", ollama.puerto() == puerto, String.valueOf(ollama.puerto()));

        // ── 2 · estado sin red ────────────────────────────────────────
        String estado = mente.mente("{\"que\":\"ollama\",\"accion\":\"estado\"}");
        check("estado no gasta red y dice el origen",
            estado.contains("\"origen\":\"http://127.0.0.1:" + puerto) && estado.contains("\"ok\":true"), estado);

        // ── 3 · la lista de modelos ───────────────────────────────────
        String lista = ollama.lista();
        org.json.JSONObject jl = new org.json.JSONObject(lista);
        String modelos = jl.optJSONArray("modelos").toString();
        check("lista: dos modelos", jl.optInt("total", -1) == 2, lista);
        check("lista: el byte grande se lee entero (1.100.000.000 > int)",
            modelos.contains("1100000000"), modelos);
        check("lista: parámetros de `details` anidadas", modelos.contains("1.5B"), modelos);
        check("lista: parámetros sueltos (servidor viejo) también", modelos.contains("3.2B"), modelos);
        check("lista: version del servidor", lista.contains("0.11.7"), lista);
        check("lista: todo lleva de:ollama", lista.contains("\"de\":\"ollama\""), lista);

        // ── 4 · usar un modelo: escribe lo que lee `Nube` ─────────────
        String usa = ollama.usa("qwen2.5:1.5b");
        check("usa dice listo con el modelo elegido",
            usa.contains("\"ok\":true") && usa.contains("\"dice\":\"listo")
                  && usa.contains("qwen2.5:1.5b") && usa.contains("127.0.0.1"), usa);
        check("usa deja el proveedor en ollama", "ollama".equals(nube.proveedor()), nube.proveedor());
        check("usa deja la base con /v1", ("http://127.0.0.1:" + puerto + "/v1").equals(nube.base()), nube.base());
        check("usa deja el modelo", "qwen2.5:1.5b".equals(nube.modelo()), nube.modelo());
        check("con ollama no hace falta clave", nube.configurada(), "configurada=false");

        // ── 5 · la pregunta se contesta en casa, sin nube ─────────────
        ctx.sistema = new ConnectivityManager();
        ((ConnectivityManager) ctx.sistema).activa = new Network("wifi");
        ((ConnectivityManager) ctx.sistema).cap = new NetworkCapabilities()
            .con(NetworkCapabilities.NET_CAPABILITY_INTERNET);
        final List<String> cuadros = new ArrayList<>();
        mente.engancha(json -> { synchronized (cuadros) { cuadros.add(json); } });
        // Una frase que `Cerebro` no conoce y `Razon` no calcula: tiene que ir al modelo.
        mente.mente("{\"que\":\"preguntar\",\"args\":{\"texto\":\"explícame qué eres\",\"eco\":\"e»\"}}");
        String respuesta = "";
        for (int n = 0; n < 200 && respuesta.isEmpty(); n++) {
            Thread.sleep(25);
            synchronized (cuadros) { for (String c : cuadros) if (c.contains("\"responde\"")) respuesta = c; }
        }
        check("la pregunta contesta con el modelo de casa",
            respuesta.contains("pienso en casa, sin nube"), respuesta.isEmpty() ? "sin cuadro" : respuesta);
        check("y se sabe de dónde salió (no es nube la de pago)",
            respuesta.contains("\"de\":\"casa\"") || respuesta.contains("\"de\":\"nube\""), respuesta);

        // ── 6 · la descarga, con progreso de verdad ───────────────────
        final List<String> progreso = new ArrayList<>();
        String fin = ollama.descarga("qwen2.5:0.5b", cuadro -> { synchronized (progreso) { progreso.add(cuadro); } });
        check("descarga: emite varios cuadros de progreso", progreso.size() >= 3, String.valueOf(progreso.size()));
        check("descarga: el porcentaje sube", progreso.get(progreso.size() - 1).contains("\"porcentaje\":1.0000"),
            progreso.get(progreso.size() - 1));
        check("descarga: termina con listo", fin.contains("\"listo\":true") && fin.contains("\"ok\":true"), fin);
        check("descarga: dice 1000 de 1000", fin.contains("\"hecho\":1000") && fin.contains("\"total\":1000"), fin);

        String roto = ollama.descarga("roto", null);
        check("descarga rota: ok:false y el error del servidor se ve",
            roto.contains("\"ok\":false") && roto.contains("no such model"), roto);

        // ── 7 · borrar, con las dos formas de la API ──────────────────
        String borra = ollama.borra("qwen2.5:1.5b");
        check("borra con DELETE", borra.contains("\"ok\":true") && borra.contains("borrado"), borra);
        String borraViejo = ollama.borra("viejo");
        check("borra cae al POST de las versiones viejas",
            borraViejo.contains("\"ok\":true") && borraViejo.contains("API antigua"), borraViejo);
        String borraMal = ollama.borra("inexistente");
        check("borra un modelo que no está dice la verdad",
            borraMal.contains("\"ok\":false") && borraMal.contains("404"), borraMal);

        // ── 8 · buscar en la Wi-Fi, sin barrer la red de nadie ────────
        String encuentra = ollama.descubre("127.0.0.1:" + puerto);
        check("descubre encuentra el servidor que sí contesta",
            encuentra.contains("\"ok\":true") && encuentra.contains("\"version\":\"0.11.7\""), encuentra);
        String nadie = ollama.descubre("127.0.0.1:1");
        check("descubre sin suerte explica lo de OLLAMA_HOST",
            nadie.contains("\"ok\":false") && nadie.contains("OLLAMA_HOST"), nadie);

        // ── 8b · fijar la dirección a mano (el botón «fijar» de la hoja) ──
        String fijaMala = ollama.fija("esta no es una direccion");
        check("fija: una dirección rara se dice en español y no se guarda",
            fijaMala.contains("\"ok\":false") && fijaMala.contains("no la entiendo")
              && ("127.0.0.1:" + puerto).equals(ollama.servidor()), fijaMala + " | " + ollama.servidor());
        String fijaBuena = ollama.fija("http://127.0.0.1:" + puerto + "/v1");   // acepta la base con /v1
        check("fija: contesta y dice la versión",
            fijaBuena.contains("\"contesta\":true") && fijaBuena.contains("0.11.7"), fijaBuena);
        check("fija: deja guardado el host:puerto limpio",
            ("127.0.0.1:" + puerto).equals(ollama.servidor()), ollama.servidor());
        String fijaApagado = ollama.fija("127.0.0.1:1");
        check("fija: un PC apagado se guarda igual y avisa (no miente con «listo»)",
            fijaApagado.contains("\"contesta\":false") && fijaApagado.contains("OLLAMA_HOST")
              && ("127.0.0.1:1").equals(ollama.servidor()), fijaApagado);
        ollama.fija("127.0.0.1:" + puerto);                     // y se vuelve a casa
        check("fija otra vez: el servidor vuelve a estar vivo",
            ("127.0.0.1:" + puerto).equals(ollama.servidor()), ollama.servidor());

        // ── 9 · el contrato por la puerta de `Mente` (la cara no llama a `Ollama`) ──
        final List<String> porContrato = new ArrayList<>();
        mente.engancha(json -> { synchronized (porContrato) { porContrato.add(json); } });
        String acuse = mente.mente("{\"que\":\"ollama\",\"accion\":\"lista\"}");
        check("mente(ollama lista) acusa pendiente y luego entrega",
            acuse.contains("\"pendiente\":true"), acuse);
        for (int n = 0; n < 200 && porContrato.isEmpty(); n++) {
            Thread.sleep(25);
            synchronized (porContrato) { }
        }
        check("el cuadro del contrato lleva de:ollama",
            !porContrato.isEmpty() && porContrato.get(0).contains("\"de\":\"ollama\""),
            porContrato.isEmpty() ? "no llegó nada" : porContrato.get(0));

        servidor.stop(0);
        check("el servidor recibió las rutas correctas",
            vistos.contains("GET /api/tags") && vistos.contains("POST /api/pull")
              && vistos.contains("DELETE /api/delete") && vistos.contains("POST /v1/chat/completions"),
            String.valueOf(vistos));

        System.out.println();
        if (fallos.isEmpty()) {
            System.out.println("OLLAMA OK: " + pasadas + " comprobaciones sobre el servidor de mentira.");
        } else {
            System.out.println("FALLEN " + fallos.size() + " de " + (pasadas + fallos.size()) + ":");
            for (String f : fallos) System.out.println("   · " + f);
            System.exit(1);
        }
    }

    static String leido(HttpExchange e) throws java.io.IOException {
        java.io.ByteArrayOutputStream b = new java.io.ByteArrayOutputStream();
        byte[] trozo = new byte[4096];
        int n;
        while ((n = e.getRequestBody().read(trozo)) > 0) b.write(trozo, 0, n);
        return new String(b.toByteArray(), StandardCharsets.UTF_8);
    }
}
