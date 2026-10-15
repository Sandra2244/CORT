package dev.sandra.cort;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * La mitad del puente de memoria que vive **dentro del teléfono**, escrita en el
 * idioma del portátil (`cort_core/puente.py`) y con los mismos números.
 *
 * La deuda la dejó `v0.15.0` y la apunta `docs/PLATFORM.md`: `memory.db` (el
 * portátil) y `cort.db` (el aparato) no se sabían nada la una de la otra, así que
 * lo que la dueña enseñaba en un lado no existía en el otro. Este archivo es la
 * traducción de ese acuerdo a Java, y es **puro a propósito**:
 *
 * - no importa `java.net` ni `HttpURLConnection` — eso lo hace `Sincroniza.java`,
 *   que es el único que abre la conexión; aquí no hay red que probar en un teléfono
 *   que nadie tiene delante;
 * - no importa nada de `android.`, ni `SharedPreferences`, ni SQLite: el almacén
 *   llega como `Cabeza`, así que la lógica del puente se puede leer y cambiar sin
 *   tocar la base de datos;
 * - `Puente.java` está atado a `puente.py` por pruebas de costura
 *   (`services/core/tests/test_apk_manifesta.py`): la versión del cuadro, los tres
 *   topes, la ruta HTTP y la derivación de la URL se comparan con los valores de
 *   Python, porque un `import` compartido entre los dos lenguajes no existe.
 *
 * Las cuatro reglas del puente son las mismas, y vienen de los cuatro modos en que
 * sincronizar sale **peor** que no sincronizar: la llave de red no viaja dentro de
 * un recuerdo, fusionar no borra nunca, el dedupe es normalizado y los topes están
 * escritos.
 */
public class Puente {
    /** La versión del cuadro. `puente.py` fija la suya y la costura lo comprueba. */
    public static final int VERSION = 1;
    public static final String TIPO = "memoria";
    public static final String ORIGEN = "telefono";

    /** La ruta del portátil. No es decoración: `Sincroniza` la concatena tal cual. */
    public static final String RUTA = "/memoria/puente";

    /** El puerto del core. La página vive en el 8780 y el puente en el core. */
    public static final int PUERTO_API = 8765;

    // Los tres topes, con el mismo número que en Python. Un puente sin techo es una
    // subida que se come la memoria de un teléfono de gama de entrada.
    public static final int MAX_CONTENIDO = 300;
    public static final int MAX_FILAS = 500;
    public static final int MAX_BYTES = 262144;

    /**
     * El almacén que el puente necesita: filas hacia fuera, un recuerdo hacia dentro.
     * La implementa `Recuerdos` (SQLite) y nada más; con esta interfaz la lógica de
     * arriba se prueba sin disco y sin aparato.
     */
    public interface Cabeza {
        /** Hasta `maximo` filas, newest first, cada una `{contenido, cuando}`. */
        List<String[]> filas(int maximo);

        /** Guardando un recuerdo que llega del otro lado, en la forma de esta cabeza. */
        void recuerda(String contenido);
    }

    /**
     * Clave de comparación de un recuerdo: sin espacios de sobra y en minúsculas.
     * Espejo de `puente.normaliza`, **con las tildes puestas**: «canción» y «cancion»
     * son dos cosas distintas para la dueña y el código no decide por ella.
     *
     * Diferencia deliberada respecto a `Cerebro.normaliza` (esa sí quita marcas, para
     * que el habla case con la tabla): aquí se comparan recuerdos enteros, no frases
     * de un menú.
     */
    public static String normaliza(String texto) {
        if (texto == null) {
            return "";
        }
        return texto.replaceAll("\\s+", " ").trim().toLowerCase(Locale.ROOT);
    }

    /**
     * Cuántas filas caben **siempre** en un viaje. El peor caso no es una ocurrencia:
     * 300 caracteres con tildes son 600 bytes en UTF-8, y el envoltorio del JSON
     * (`{"contenido": …, "cuando": …}`) suma unos 64 más por fila. Con 500 filas de ese
     * tamaño el cuerpo sería de ~322 KB y el portátil lo cortaría con 413 — o sea: un
     * teléfono con muchos recuerdos no podría sincronizar **nunca**, y el fallo se
     * vería en el teléfono, que es el sitio donde nadie puede leerlo.
     *
     * Sale 271. Es el tope real de una subida, y `Sincroniza` lo enseña («subidos 271
     * de 400») en vez de dejarlo en silencio.
     */
    public static int filasQueCaben() {
        return Math.min(MAX_FILAS, MAX_BYTES / (MAX_CONTENIDO * 3 + 64));
    }

    /**
     * El cuadro viajero, listo para `POST`. `llave` es la de la red y **no** entra:
     * una fila que la contiene se oculta y se cuenta, que es la regla 1 del puente —
     * el endpoint está protegido por esa misma llave, y llevársela puesta dentro de
     * un recuerdo sería un autorrobo elegante.
     */
    public static JSONObject exportar(Cabeza cabeza, String llave) throws JSONException {
        return exportar(cabeza, llave, filasQueCaben());
    }

    /** Versión explícita del tope, para que la costura lo pueda mirar en Python. */
    public static JSONObject exportar(Cabeza cabeza, String llave, int maximo)
            throws JSONException {
        JSONArray recuerdos = new JSONArray();
        int ocultados = 0;
        for (String[] fila : cabeza.filas(Math.min(maximo, filasQueCaben()))) {
            String contenido = fila == null || fila.length == 0 ? "" : fila[0].trim();
            if (contenido.isEmpty() || contenido.length() > MAX_CONTENIDO
                    || (llave != null && !llave.isEmpty() && contenido.contains(llave))) {
                ocultados++;
                continue;
            }
            String cuando = fila.length > 1 && fila[1] != null ? fila[1] : "";
            recuerdos.put(new JSONObject().put("contenido", contenido).put("cuando", cuando));
        }
        return new JSONObject().put("tipo", TIPO).put("version", VERSION).put("origen", ORIGEN)
                .put("total", recuerdos.length()).put("ocultados", ocultados)
                .put("recuerdos", recuerdos);
    }

    /**
     * Metiendo un cuadro del portátil en esta cabeza, **sin borrar nada** (regla 3).
     *
     * Devuelve el recuento que la cara enseña: «4 nuevos, 12 ya estaban, 1 descartado».
     * Un cuadro con otra `version`, o sin la lista `recuerdos`, es `JSONException` con
     * mensaje en español: el llamador lo muestra y no deja memoria a medias, porque
     * aquí se valida todo antes del primer `recuerda()`.
     */
    public static int[] fusionar(Cabeza cabeza, JSONObject cuadro, String llave)
            throws JSONException {
        if (cuadro == null) {
            throw new JSONException("el cuadro de memoria no es un objeto");
        }
        int version = cuadro.optInt("version", -1);
        if (version != VERSION) {
            throw new JSONException("versión de cuadro " + version
                    + ": este puente habla la " + VERSION);
        }
        JSONArray recuerdos = cuadro.optJSONArray("recuerdos");
        if (recuerdos == null) {
            throw new JSONException("el cuadro no trae lista de recuerdos");
        }
        if (recuerdos.length() > MAX_FILAS) {
            throw new JSONException("demasiados recuerdos en un viaje: " + recuerdos.length()
                    + " (tope " + MAX_FILAS + ")");
        }

        Set<String> existentes = new HashSet<>();
        for (String[] fila : cabeza.filas(MAX_FILAS)) {
            existentes.add(normaliza(fila == null || fila.length == 0 ? "" : fila[0]));
        }

        int nuevos = 0;
        int repetidos = 0;
        int rechazados = 0;
        for (int i = 0; i < recuerdos.length(); i++) {
            String contenido = limpia(recuerdos.optJSONObject(i), llave);
            if (contenido == null) {
                rechazados++;
                continue;
            }
            String clave = normaliza(contenido);
            if (clave.isEmpty() || !existentes.add(clave)) {
                repetidos++;
                continue;
            }
            cabeza.recuerda(contenido);
            nuevos++;
        }
        return new int[] {nuevos, repetidos, rechazados, nuevos + repetidos + rechazados};
    }

    /**
     * El recuerdo listo para guardar, o `null` si no debe guardarse: vacío, desmedido,
     * con la llave dentro, o con caracteres de control. Espejo de `puente._limpia`, y
     * los signos raros se quitan **sin partir la frase**: un `\u0000` en un recuerdo
     * viaja por JSON y luego nadie lo puede leer en la pantalla del teléfono.
     */
    private static String limpia(JSONObject fila, String llave) {
        if (fila == null) {
            return null;
        }
        String contenido = fila.optString("contenido")
                .replaceAll("[\\u0000-\\u001f\\u007f]", " ").trim();
        if (contenido.isEmpty() || contenido.length() > MAX_CONTENIDO) {
            return null;
        }
        if (llave != null && !llave.isEmpty() && contenido.contains(llave)) {
            return null;
        }
        return contenido;
    }

    /**
     * La URL del puente a partir del enlace que el teléfono ya tiene guardado
     * (`http://192.168.100.5:8780/?token=…`, la que divulgó el lanzador por UDP o
     * pegó la dueña).
     *
     * Dos saltos, y los dos por un motivo:
     *
     * 1. **El puerto.** La página está en el 8780 y el puente lo sirve el core, en el
     *    8765. Se cambia el número y se conserva el host: es el mismo `host` al que el
     *    WebView abre su WebSocket, así que no se está adivinando una máquina distinta.
     * 2. **La llave.** Sale del `?token=` del enlace y viaja en la consulta del puente,
     *    igual que viaja en el lazo del WebView. Va **siempre al final**, y se cortan
     *    los parámetros que vinieran detrás: un `?token=x&otro=1` no puede convertirse
     *    en una URL con un query reconstruido a medias.
     *
     * `null` es un enlace que no es una dirección de CORT. `Sincroniza` lo muestra y
     * no abre la boca.
     */
    public static String urlDelPuente(String enlace) {
        if (enlace == null) {
            return null;
        }
        String limpio = enlace.trim();
        String esquema = "";
        if (limpio.startsWith("https://")) {
            esquema = "https://";
        } else if (limpio.startsWith("http://")) {
            esquema = "http://";
        } else {
            return null;
        }
        String resto = limpio.substring(esquema.length());
        int finAutoridad = resto.length();
        for (int i = 0; i < resto.length(); i++) {
            char c = resto.charAt(i);
            if (c == '/' || c == '?' || c == '#') {
                finAutoridad = i;
                break;
            }
        }
        String host = resto.substring(0, finAutoridad);
        int dosPuntos = host.lastIndexOf(':');
        if (dosPuntos >= 0) {
            host = host.substring(0, dosPuntos);   // el puerto de la página no es el del core
        }
        if (host.isEmpty()) {
            return null;
        }
        String llave = tokenDe(limpio);
        return esquema + host + ":" + PUERTO_API + RUTA
                + (llave.isEmpty() ? "" : "?token=" + llave);
    }

    /** El valor de `?token=` hasta el siguiente `&`, o vacío. */
    public static String tokenDe(String enlace) {
        if (enlace == null) {
            return "";
        }
        int donde = enlace.indexOf("?token=");
        if (donde < 0) {
            donde = enlace.indexOf("&token=");
        }
        if (donde < 0) {
            return "";
        }
        String desde = enlace.substring(donde + "?token=".length());
        int corte = desde.length();
        for (int i = 0; i < desde.length(); i++) {
            char c = desde.charAt(i);
            if (c == '&' || c == '#') {
                corte = i;
                break;
            }
        }
        return desde.substring(0, corte).trim();
    }

    /**
     * «4 nuevos, 12 ya estaban, 1 descartado» en una línea, para el chip y el registro.
     * El recuento es `{nuevos, repetidos, rechazados, total}` y el orden es el de
     * `puente.fusionar`, no un invento de aquí.
     */
    public static String recuento(int[] cuentas) {
        return cuentas[0] + " nuevos, " + cuentas[1] + " ya estaban, "
                + cuentas[2] + " descartados";
    }

    /**
     * Lo que el portátil puede leer de un hecho del teléfono: `clave: valor` tal cual
     * lo muestra `Recuerdos.lista()`. La traducción a «El usuario se llama …» la hace
     * `facts.desde_el_telefono` **al entrar**, que es donde vive la plantilla canónica.
     */
    public static String contenidoDe(String clave, String valor) {
        List<String> partes = new ArrayList<>();
        if (clave != null && !clave.trim().isEmpty()) {
            partes.add(clave.trim());
        }
        if (valor != null && !valor.trim().isEmpty()) {
            partes.add(valor.trim());
        }
        return String.join(": ", partes);
    }
}
