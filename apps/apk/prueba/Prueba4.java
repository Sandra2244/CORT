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
    static HttpServer sinVersion;           // el PC con el puerto abierto y sin Ollama
    static int puertoSinVersion;
    static volatile int PULLS_SIN_VERSION = 0;
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
                } else if (peticion.contains("lenta")) {
                    /* Cuatro segundos de bajada a propósito: lo que se comprueba con
                       ella es `cancela()`, y para eso hace falta que la bajada siga
                       viva cuando el otro hilo cierre el stream. */
                    s.write("{\"status\":\"pulling manifest\"}\n".getBytes(StandardCharsets.UTF_8));
                    s.flush();
                    for (int i = 1; i <= 40; i++) {
                        s.write(("{\"status\":\"downloading\",\"digest\":\"z\",\"total\":40000,"
                            + "\"completed\":" + (i * 1000) + "}\n").getBytes(StandardCharsets.UTF_8));
                        s.flush();
                        try { Thread.sleep(100); } catch (InterruptedException yaNo) { break; }
                    }
                    s.write("{\"status\":\"success\"}\n".getBytes(StandardCharsets.UTF_8));
                } else if (peticion.contains("callada")) {
                    /* El caso que decide si el cancelar es de verdad o es una mentira:
                       dos líneas y tres segundos de silencio, como el PC que se queda
                       pensando mientras el teléfono mira la barra. La prueba espera DOS
                       segundos, así que sólo pasa si algo desbloquea el `readLine()` —
                       cerrar la corriente o soltar la conexión, que en el JDK bastan por
                       separado (el taller lo midió: quitar una sola sigue dando verde;
                       quitar las dos cae). Si aquí nadie cerrara nada, el hilo seguiría
                       clavado hasta el segundo 3 y `resultado2[0]` sería `null`. */
                    s.write("{\"status\":\"pulling manifest\"}\n".getBytes(StandardCharsets.UTF_8));
                    s.write(("{\"status\":\"downloading\",\"digest\":\"q\",\"total\":900000,"
                            + "\"completed\":100000}\n").getBytes(StandardCharsets.UTF_8));
                    s.flush();
                    try { Thread.sleep(3000); } catch (InterruptedException yaNo) { }
                    s.write("{\"status\":\"success\"}\n".getBytes(StandardCharsets.UTF_8));
                } else if (peticion.contains("capas")) {
                    /* El NDJSON de un modelo de VARIAS capas, intercalado y con una
                       línea de verificación que trae `digest` pero no `total`. Cada
                       línea habla de SU capa: sumar mal (o sobrescribir) se ve aquí
                       enseguida, porque el total del modelo son 5.000.000 y los de
                       las capas sueltas no llegan a esa cifra. */
                    s.write("{\"status\":\"pulling manifest\"}\n".getBytes(StandardCharsets.UTF_8));
                    s.flush();
                    String[][] lineas = {
                        {"downloading", "aaa", "4000000", "100000"},
                        {"downloading", "bbb", "1000000", "20000"},
                        {"downloading", "aaa", "4000000", "2000000"},
                        {"downloading", "bbb", "1000000", "500000"},
                        {"downloading", "aaa", "4000000", "4000000"},
                        {"downloading", "bbb", "1000000", "500000"},
                        {"verifying sha256 digest", "aaa", "", ""},
                        {"writing manifest", "", "", ""},
                        {"success", "", "", ""},
                    };
                    for (String[] l : lineas) {
                        StringBuilder j = new StringBuilder("{\"status\":\"" + l[0] + "\"");
                        if (!l[1].isEmpty()) j.append(",\"digest\":\"" + l[1] + "\"");
                        if (!l[2].isEmpty()) j.append(",\"total\":" + l[2]);
                        if (!l[3].isEmpty()) j.append(",\"completed\":" + l[3]);
                        s.write((j.append("}\n").toString()).getBytes(StandardCharsets.UTF_8));
                        s.flush();
                    }
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

        /* Un segundo servidor que SÍ tiene `/api/pull` y NO tiene `/api/version`: es
           el PC con el puerto abierto pero sin Ollama detrás (el backend de CORT, un
           servidor a medio arrancar, cualquier cosa que escuche). Sin el ping de
           delante, la bajada se iría a los 90 s de timeout; con él, `descarga` tiene
           que cortar antes y —esto es lo que se comprueba— sin llamar a `/api/pull`. */
        sinVersion = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        sinVersion.createContext("/api/pull", new HttpHandler() {
            @Override public void handle(HttpExchange e) throws java.io.IOException {
                leido(e);
                PULLS_SIN_VERSION++;
                e.getResponseHeaders().set("Content-Type", "application/x-ndjson");
                e.sendResponseHeaders(200, 0);
                OutputStream s = e.getResponseBody();
                s.write("{\"status\":\"success\"}\n".getBytes(StandardCharsets.UTF_8));
                s.close();
            }
        });
        sinVersion.setExecutor(null);
        sinVersion.start();
        puertoSinVersion = sinVersion.getAddress().getPort();

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
        Timbre.limpia();                       // la libreta de avisos, en cero
        final List<String> progreso = new ArrayList<>();
        String fin = ollama.descarga("qwen2.5:0.5b", cuadro -> { synchronized (progreso) { progreso.add(cuadro); } });
        check("descarga: emite varios cuadros de progreso", progreso.size() >= 3, String.valueOf(progreso.size()));
        check("descarga: el porcentaje sube", progreso.get(progreso.size() - 1).contains("\"porcentaje\":1.0000"),
            progreso.get(progreso.size() - 1));
        check("descarga: termina con listo", fin.contains("\"listo\":true") && fin.contains("\"ok\":true"), fin);
        check("descarga: dice 1000 de 1000", fin.contains("\"hecho\":1000") && fin.contains("\"total\":1000"), fin);

        // El aviso de que la bajada terminó (#119) se dispara DESDE AQUÍ, no desde la
        // cara: la hoja se cierra y el teléfono se va, y el hilo que lee el NDJSON es
        // este. Aquí se prueba la llamada con el `Timbre` de papel; el `notify` de
        // Android se comprueba en `prueba-costura.py` [24] sobre el fichero real.
        check("aviso: al terminar bien ya se puso uno",
            Timbre.PUESTOS.size() == 1 && Timbre.PUESTOS.get(0).startsWith("listo qwen2.5:0.5b"),
            String.valueOf(Timbre.PUESTOS));
        check("aviso: el texto trae el peso (1 KB, nunca un 0 MB) y el servidor",
            !Timbre.PUESTOS.isEmpty() && Timbre.PUESTOS.get(0).contains("|1 KB|1 KB|"),
            String.valueOf(Timbre.PUESTOS));

        String roto = ollama.descarga("roto", null);
        check("descarga rota: ok:false y el error del servidor se ve",
            roto.contains("\"ok\":false") && roto.contains("no such model"), roto);
        check("aviso: la bajada cortada también avisa, y dice por qué",
            Timbre.PUESTOS.size() == 2 && Timbre.PUESTOS.get(1).startsWith("paró roto")
            && Timbre.PUESTOS.get(1).contains("no such model"),
            String.valueOf(Timbre.PUESTOS));

        // ── 6b · varias capas: el progreso se SUMA, no se sobrescribe ──────
        // El bug que la dueña veía («la barra no se mueve, o se va a atrás»): un
        // modelo son N capas y el servidor intercala sus líneas. Cada línea trae el
        // total y lo bajado de ESA capa, así que asignar (`total = j.total`) hacía
        // que la última línea leída mandara sobre el modelo entero.
        Timbre.limpia();
        final List<String> porCapas = new ArrayList<>();
        String multi = ollama.descarga("varias-capas",
            c -> { synchronized (porCapas) { porCapas.add(c); } });
        check("capas: el total del modelo es la suma de sus capas (4.500.000 de 5.000.000)",
            multi.contains("\"hecho\":4500000") && multi.contains("\"total\":5000000"), multi);
        check("capas: dice cuántas capas lleva el modelo", multi.contains("\"capas\":2"), multi);
        check("capas: una línea de verificación sin `total` no borra el de su capa",
            multi.contains("\"total\":5000000") && multi.contains("\"capas\":2"), multi);
        check("capas: el último cuadro trae el porcentaje SUMADO (90 %)",
            !porCapas.isEmpty()
              && porCapas.get(porCapas.size() - 1).contains("\"porcentaje\":0.9000"),
            porCapas.isEmpty() ? "sin cuadros" : porCapas.get(porCapas.size() - 1));
        check("capas: ningún cuadro de progreso retrocede",
            subeSiempre(porCapas), String.valueOf(porCapas.size()));

        // ── 6c · el ping delante: un puerto abierto sin Ollama detrás ───────
        Timbre.limpia();
        ollama.fija("127.0.0.1:" + puertoSinVersion);
        String sinVer = ollama.descarga("cualquiera", null);
        check("ping delante: lo que no contesta se dice en español, no con un timeout",
            sinVer.contains("\"ok\":false") && sinVer.contains("no contesta nadie")
              && sinVer.contains("OLLAMA_HOST"), sinVer);
        check("ping delante: con el PC mudo no se llega a llamar a /api/pull",
            PULLS_SIN_VERSION == 0, String.valueOf(PULLS_SIN_VERSION));
        check("ping delante: el aviso cuenta lo mismo (falló, y dice por qué)",
            Timbre.PUESTOS.size() == 1 && Timbre.PUESTOS.get(0).startsWith("paró cualquiera")
              && Timbre.PUESTOS.get(0).contains("no contesta nadie"), String.valueOf(Timbre.PUESTOS));
        ollama.fija("127.0.0.1:" + puerto);                     // y se vuelve a casa

        // ── 6d · cancelar una bajada en curso ──────────────────────────────
        Timbre.limpia();
        final List<String> enVivo = new ArrayList<>();
        final String[] resultado = new String[1];
        Thread bajada = new Thread(() -> {
            resultado[0] = ollama.descarga("lenta", c -> { synchronized (enVivo) { enVivo.add(c); } });
        });
        bajada.start();
        for (int n = 0; n < 160 && enVivo.isEmpty(); n++) Thread.sleep(10);
        check("cancelar: sólo se puede cortar una bajada que esté abierta",
            ollama.bajando() && "lenta".equals(ollama.queBaja()), ollama.queBaja());
        String otra = ollama.descarga("mientras", null);
        check("una sola bajada: pedir la segunda se dice, no pisa la primera",
            otra.contains("\"ok\":false") && otra.contains("ya está bajando lenta")
              && "lenta".equals(ollama.queBaja()), otra + " | " + ollama.queBaja());
        long t0 = System.currentTimeMillis();
        String aviso = ollama.cancela();
        long tardo = System.currentTimeMillis() - t0;
        bajada.join(6000);
        check("cancelar: contesta enseguida y dice qué estaba bajando",
            aviso.contains("\"ok\":true") && aviso.contains("\"cancelado\":true")
              && aviso.contains("lenta") && tardo < 2000, aviso + " | " + tardo + " ms");
        check("cancelar: el hilo de la bajada para, no espera al final del servidor",
            resultado[0] != null && resultado[0].contains("\"cancelado\":true"),
            String.valueOf(resultado[0]));
        check("cancelar: la cara recibe `ok:false` con su `dice` (la barra se suelta)",
            resultado[0] != null && resultado[0].contains("\"ok\":false")
              && resultado[0].contains("cancelaste"), String.valueOf(resultado[0]));
        check("cancelar: NO se avisa de algo que la dueña cortó por su mano",
            Timbre.PUESTOS.isEmpty(), String.valueOf(Timbre.PUESTOS));
        check("cancelar: después de cortar no queda ninguna bajada abierta",
            !ollama.bajando() && ollama.queBaja().isEmpty(), ollama.queBaja());
        String segunda = ollama.cancela();
        check("cancelar dos veces: la segunda dice que no había nada que cortar",
            segunda.contains("\"ok\":false") && segunda.contains("no había ninguna bajada"), segunda);
        Timbre.limpia();
        String cuadroCancela = cuadroContrato(mente, "{\"que\":\"ollama\",\"accion\":\"cancela\"}");
        check("cancelar: por el contrato de la cara (`accion:cancela`) contesta `que:cancela`",
            cuadroCancela.contains("\"que\":\"cancela\""), cuadroCancela);

        // ── 6e · cancelar con el PC CALLADO (el caso que arregla el silencio) ──
        Timbre.limpia();
        final List<String> mudos = new ArrayList<>();
        final String[] resultado2 = new String[1];
        Thread callada = new Thread(() -> resultado2[0] = ollama.descarga("callada",
            c -> { synchronized (mudos) { mudos.add(c); } }));
        callada.start();
        for (int n = 0; n < 160 && mudos.isEmpty(); n++) Thread.sleep(10);
        ollama.cancela();
        callada.join(2000);              // el servidor calla 3 s: esperarlos sería el fallo
        check("cancelar con el PC callado: cerrar la corriente despierta al lector",
            resultado2[0] != null && resultado2[0].contains("\"cancelado\":true"),
            String.valueOf(resultado2[0]));
        check("cancelar con el PC callado: lo bajado hasta el corte se dice, no se inventa",
            resultado2[0] != null && resultado2[0].contains("\"ok\":false")
              && !resultado2[0].contains("\"listo\":true"), String.valueOf(resultado2[0]));
        Timbre.limpia();

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
        sinVersion.stop(0);
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

    /**
     * Que la barra no retroceda nunca: se leen los `porcentaje` de los cuadros en el
     * orden en que salieron. Con el progreso mal sumado, un cuadro de una capa chica
     * valía menos que el anterior y la cara veía la barra irse hacia atrás.
     */
    static boolean subeSiempre(List<String> cuadros) {
        double antes = -1;
        for (String c : cuadros) {
            int i = c.indexOf("\"porcentaje\":");
            if (i < 0) continue;
            int j = i + 13, k = j;
            while (k < c.length() && (Character.isDigit(c.charAt(k)) || c.charAt(k) == '.')) k++;
            double p;
            try { p = Double.parseDouble(c.substring(j, k)); } catch (Exception rara) { return false; }
            if (p < antes - 1e-9) return false;
            antes = p;
        }
        return antes > 0;
    }

    /**
     * Manda una orden por el CONTRATO que usa la cara (`mente` con `que:"ollama"`,
     * que contesta `pendiente` y entrega el cuadro por el evento) y devuelve el
     * primer cuadro que llegue con `de:"ollama"`. Es la comprobación que ata la hoja
     * del teléfono con Java: si `Mente` no conoce la acción, lo que llega es el aviso
     * de «no conozco esa acción» y aquí se ve, en vez de quedarse la cara sin nada.
     */
    static String cuadroContrato(Mente mente, String orden) {
        final List<String> caja = new ArrayList<>();
        mente.engancha(json -> { synchronized (caja) { caja.add(json); } });
        mente.mente(orden);
        for (int n = 0; n < 100; n++) {
            synchronized (caja) {
                for (String c : caja) if (c.contains("\"de\":\"ollama\"")) return c;
            }
            try { Thread.sleep(20); } catch (InterruptedException cortan) { break; }
        }
        return "(no llegó ningún cuadro de ollama)";
    }

    static String leido(HttpExchange e) throws java.io.IOException {        java.io.ByteArrayOutputStream b = new java.io.ByteArrayOutputStream();
        byte[] trozo = new byte[4096];
        int n;
        while ((n = e.getRequestBody().read(trozo)) > 0) b.write(trozo, 0, n);
        return new String(b.toByteArray(), StandardCharsets.UTF_8);
    }
}
