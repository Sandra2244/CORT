package dev.sandra.cort.movil;

import android.content.Context;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.UnsupportedEncodingException;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Investigar y analizar con el origen dicho (F20c). La dueña pidió que CORT
 * «investigue» y «analice», y la diferencia entre eso y un loro es que cada respuesta
 * lleva de dónde salió. Aquí no hay un buscador de pago ni una clave que guardar:
 * se consultan **dos fuentes públicas** y se nombran las dos.
 *
 * Cuáles son y qué se puede esperar de ellas, escrito para no prometer de más:
 *
 * 1. **Wikipedia en español** (`es.wikipedia.org/w/api.php`, `list=search`): devuelve
 *    títulos, un fragmento y el `pageid`, con el que se arma el enlace canónico. Es
 *    una enciclopedia: buena para «qué es», mala para «qué pasó hoy».
 * 2. **DuckDuckGo Instant Answer** (`api.duckduckgo.com`): devuelve el `AbstractText`
 *    y los `RelatedTopics` con su `FirstURL`. No es
 *    una búsqueda web completa —muchas preguntas traen el abstracto vacío— y cuando
 *    viene vacío se dice que no hubo hallazgo en vez de inventar uno.
 *
 * El análisis de lo que ella está viendo (F19e + F20c) va al cerebro que toque, con
 * una advertencia que no se puede callar: **si contesta la nube, el texto de su
 * pantalla salió del teléfono**. Se escribe en la respuesta, no en una letra chica.
 *
 * Todo bloquea, así que las dos entradas arrancan su propio hilo y entregan por
 * `AlTerminar`. Nada de esto se guarda: ni las consultas ni lo leído en la pantalla.
 */
public final class Investigacion {

    /** Un hallazgo con su origen. Sin `url` no se entrega: sería una afirmación sin fuente. */
    public static final class Hallazgo {
        public final String titulo;
        public final String fragmento;
        public final String url;
        public final String fuente;

        Hallazgo(String titulo, String fragmento, String url, String fuente) {
            this.titulo = titulo;
            this.fragmento = fragmento;
            this.url = url;
            this.fuente = fuente;
        }
    }

    public interface AlTerminar {
        void llega(String dicho, List<Hallazgo> fuentes);
    }

    private static final int CONEXION_MS = 10_000;
    private static final int LECTURA_MS = 15_000;

    /** Tope de lo que se lee de una respuesta: una consulta no puede llenar la RAM. */
    private static final int MAX_BYTES = 512 * 1024;

    /** Tope del texto de pantalla que viaja al modelo: el contexto del GGUF es finito. */
    private static final int MAX_ANALISIS = 4000;

    private Investigacion() {
    }

    /* ------------------------------------------------------------------ buscar */

    /**
     * Pregunta a las dos fuentes y contesta con lo que hubo. El orden es Wikipedia
     * primero porque su fragmento es texto plano y el de DuckDuckGo a veces viene con
     * etiquetas; las dos se consultan igual y se listan las dos.
     */
    public static void busca(final Context contexto, final String pregunta,
                             final AlTerminar oyente) {
        final String limpio = pregunta == null ? "" : pregunta.trim();
        if (limpio.isEmpty()) {
            oyente.llega("Dime qué quieres que investigue.", new ArrayList<Hallazgo>());
            return;
        }
        new Thread(() -> {
            List<Hallazgo> fuentes = new ArrayList<>();
            String enciclopedia = wikipedia(limpio, fuentes);
            String instantanea = duckduckgo(limpio, fuentes);
            StringBuilder junto = new StringBuilder();
            if (!enciclopedia.isEmpty()) {
                junto.append(enciclopedia);
            }
            if (!instantanea.isEmpty()) {
                if (junto.length() > 0) {
                    junto.append(' ');
                }
                junto.append(instantanea);
            }
            if (junto.length() == 0) {
                junto.append("No encontré nada sobre «").append(limpio)
                     .append("» en Wikipedia en español ni en las respuestas instantáneas "
                     + "de DuckDuckGo. No es una búsqueda web completa: si necesitas algo "
                     + "más reciente o más específico, ábrelo en el navegador.");
            } else {
                junto.append(" Fuentes: ");
                for (int i = 0; i < fuentes.size(); i++) {
                    if (i > 0) {
                        junto.append("; ");
                    }
                    junto.append(fuentes.get(i).fuente).append(' ').append(fuentes.get(i).url);
                }
            }
            oyente.llega(junto.toString(), fuentes);
        }, "cort-investiga").start();
    }

    private static String wikipedia(String pregunta, List<Hallazgo> fuentes) {
        try {
            String url = "https://es.wikipedia.org/w/api.php?action=query&list=search"
                    + "&srsearch=" + codifica(pregunta) + "&srlimit=3&format=json";
            JSONObject j = new JSONObject(pide(url));
            JSONArray filas = j.optJSONObject("query") == null
                    ? null : j.getJSONObject("query").optJSONArray("search");
            if (filas == null || filas.length() == 0) {
                return "";
            }
            StringBuilder junto = new StringBuilder();
            for (int i = 0; i < filas.length(); i++) {
                JSONObject fila = filas.getJSONObject(i);
                String titulo = fila.optString("title", "");
                // El fragmento viene con `<span class="searchmatch">`: se quita porque
                // esto se lee en voz alta y las etiquetas no se pronuncian.
                String fragmento = sinEtiquetas(fila.optString("snippet", ""));
                long pagina = fila.optLong("pageid", 0L);
                if (titulo.isEmpty() || fragmento.isEmpty() || pagina == 0L) {
                    continue;
                }
                String enlace = "https://es.wikipedia.org/?curid=" + pagina;
                fuentes.add(new Hallazgo(titulo, fragmento, enlace, "Wikipedia"));
                if (junto.length() > 0) {
                    junto.append(' ');
                }
                junto.append(titulo).append(": ").append(fragmento);
                if (i == 0) {
                    break;      // el primero es el que casa; los otros quedan como fuente
                }
            }
            return junto.toString();
        } catch (IOException | org.json.JSONException raro) {
            return "";
        }
    }

    private static String duckduckgo(String pregunta, List<Hallazgo> fuentes) {
        try {
            String url = "https://api.duckduckgo.com/?q=" + codifica(pregunta)
                    + "&format=json&no_html=1&skip_disambig=1";
            JSONObject j = new JSONObject(pide(url));
            String abstracto = j.optString("AbstractText", "").trim();
            String enlace = j.optString("AbstractURL", "").trim();
            if (!abstracto.isEmpty() && !enlace.isEmpty()) {
                fuentes.add(new Hallazgo(j.optString("Heading", pregunta), abstracto,
                        enlace, "DuckDuckGo"));
                return abstracto;
            }
            JSONArray temas = j.optJSONArray("RelatedTopics");
            if (temas == null) {
                return "";
            }
            for (int i = 0; i < temas.length() && i < 3; i++) {
                JSONObject tema = temas.optJSONObject(i);
                if (tema == null) {
                    continue;
                }
                String texto = tema.optString("Text", "").trim();
                String primero = tema.optString("FirstURL", "").trim();
                if (texto.isEmpty() || primero.isEmpty()) {
                    continue;
                }
                fuentes.add(new Hallazgo(texto, texto, primero, "DuckDuckGo"));
                return texto;
            }
            return "";
        } catch (IOException | org.json.JSONException raro) {
            return "";
        }
    }

    /* ---------------------------------------------------------------- analizar */

    /**
     * Analiza un texto que ella está viendo. `deDonde` es la app o «lo seleccionado»,
     * y se dice en la respuesta para que sepa qué se analizó. El cerebro lo elige la
     * ruta de siempre (GGUF si cabe, si no nube), y si contesta la nube se avisa que
     * el texto salió del teléfono: eso no es una opción que se pueda esconder.
     */
    public static void analiza(final Context contexto, final String texto,
                               final String deDonde, final CerebroLocal cerebro,
                               final Nube nube, final Recuerdos recuerdos,
                               final AlTerminar oyente) {
        final String limpio = texto == null ? "" : texto.trim();
        if (limpio.isEmpty()) {
            oyente.llega("No hay texto que analizar: " + Pantalla.motivo(),
                    new ArrayList<Hallazgo>());
            return;
        }
        new Thread(() -> {
            String recorte = limpio.length() > MAX_ANALISIS
                    ? limpio.substring(0, MAX_ANALISIS) : limpio;
            boolean cortado = limpio.length() > MAX_ANALISIS;
            String pregunta = "Analiza este texto que estoy viendo"
                    + (deDonde == null || deDonde.isEmpty() ? "" : " en " + deDonde)
                    + ". Di en tres frases qué es y qué es lo importante, y si hay algo "
                    + "que deba revisar. Texto: " + recorte;
            String sistema = Consticion.sistema(contexto, recuerdos.lista(12));
            String respuesta = cerebro.contestar(sistema, pregunta, null, null,
                    Consticion.maxTokens(contexto), Consticion.temperatura(contexto));
            String aviso = "";
            if (respuesta == null && nube != null && nube.configurada()) {
                respuesta = nube.preguntar(sistema, pregunta, null);
                if (respuesta != null) {
                    aviso = "Esto lo contestó la nube: el texto de tu pantalla salió del "
                            + "teléfono. Si no quieres que vuelva a pasar, pon el modo "
                            + "«sólo el teléfono» en el Almacén de cerebros.";
                }
            }
            if (respuesta == null) {
                oyente.llega("No pude analizarlo: no hay cerebro local abierto y la nube "
                        + "no está configurada. Baja un GGUF en el Almacén o configura la "
                        + "nube, y vuelve a pedírmelo.", new ArrayList<Hallazgo>());
                return;
            }
            String junto = respuesta
                    + (cortado ? " (Leí los primeros " + MAX_ANALISIS
                            + " caracteres de " + limpio.length() + ": el resto no cupo en "
                            + "el contexto del modelo.)" : "")
                    + (aviso.isEmpty() ? "" : " " + aviso);
            oyente.llega(junto, new ArrayList<Hallazgo>());
        }, "cort-analiza").start();
    }

    /* --------------------------------------------------------------- utilería */

    private static String codifica(String texto) {
        try {
            return URLEncoder.encode(texto, "UTF-8");
        } catch (UnsupportedEncodingException imposible) {
            // UTF-8 está en todos los Android; si no estuviera, la consulta va sin codificar
            return texto.replace(' ', '+');
        }
    }

    /** GET con topes de tiempo y de tamaño. Lanza con el motivo si algo no cuadra. */
    private static String pide(String url) throws IOException {
        HttpURLConnection conexion = (HttpURLConnection) new URL(url).openConnection();
        try {
            conexion.setConnectTimeout(CONEXION_MS);
            conexion.setReadTimeout(LECTURA_MS);
            conexion.setRequestProperty("User-Agent", "CORT-Android/0.17 (asistente local)");
            conexion.setRequestProperty("Accept", "application/json");
            int codigo = conexion.getResponseCode();
            if (codigo != 200) {
                throw new IOException("HTTP " + codigo);
            }
            InputStream entrada = conexion.getInputStream();
            ByteArrayOutputStream junto = new ByteArrayOutputStream();
            try {
                byte[] trozo = new byte[8192];
                int n;
                while ((n = entrada.read(trozo)) > 0) {
                    junto.write(trozo, 0, n);
                    if (junto.size() > MAX_BYTES) {
                        throw new IOException("la respuesta pasó de " + MAX_BYTES + " bytes");
                    }
                }
            } finally {
                entrada.close();
            }
            return new String(junto.toByteArray(), StandardCharsets.UTF_8);
        } finally {
            conexion.disconnect();
        }
    }

    /** Quita las etiquetas y decodifica las tres entidades que trae el fragmento de búsqueda. */
    private static String sinEtiquetas(String crudo) {
        return crudo.replaceAll("<[^>]*>", "")
                .replace("&quot;", "\"").replace("&amp;", "&").replace("&#039;", "'")
                .replace("&lt;", "<").replace("&gt;", ">").trim();
    }
}
