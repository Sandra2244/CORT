package dev.sandra.cort;

import android.content.Context;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.regex.Pattern;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * El oído de CORT dentro del teléfono: lee `assets/habilidades.json`, normaliza
 * lo que la dueña dijo y devuelve la regla que casó. **No ejecuta nada** — eso es
 * `Acciones` —, y no sabe hablar: sólo empareja.
 *
 * La tabla vive en un archivo de datos y no escrita en Java por una razón
 * practica: en esta máquina no hay `javac`, así que el Java sólo se comprueba en
 * el runner, mientras que el JSON lo valida `make test` en dos segundos. Poner
 * las frases en el código sería dejar la parte que mas se toca sin ninguna
 * prueba hasta que alguien instale un APK.
 *
 * El orden importa: primero las habilidades que la dueña enseñó (son suyas y
 * ganan), después la tabla cerrada, y si ninguna casó la cara propone aprender.
 */
public class Cerebro {
    /** Una regla casada: qué acción es, con qué parámetro y con qué resto. */
    public static final class Resultado {
        public final String id;
        public final String accion;
        public final String param;
        public final String plantilla;
        public final String resto;

        Resultado(String id, String accion, String param, String plantilla, String resto) {
            this.id = id;
            this.accion = accion;
            this.param = param;
            this.plantilla = plantilla;
            this.resto = resto;
        }
    }

    private static final class Regla {
        final String id;
        final String accion;
        final String param;
        final String respuesta;
        final List<String> patrones;

        Regla(String id, String accion, String param, String respuesta, List<String> patrones) {
            this.id = id;
            this.accion = accion;
            this.param = param;
            this.respuesta = respuesta;
            this.patrones = patrones;
        }
    }

    private final List<Regla> reglas = new ArrayList<>();
    private final Recuerdos recuerdos;
    private String avisoDeCarga = "";

    public Cerebro(Context contexto, Recuerdos recuerdos) {
        this.recuerdos = recuerdos;
        cargar(contexto);
    }

    /** Lo que salió mal leyendo la tabla, para que la cara lo diga y no se quede muda. */
    public String avisoDeCarga() {
        return avisoDeCarga;
    }

    private void cargar(Context contexto) {
        try (InputStream entrada = contexto.getAssets().open("habilidades.json")) {
            byte[] buffer = new byte[entrada.available()];
            int leido = 0;
            while (leido < buffer.length) {
                int n = entrada.read(buffer, leido, buffer.length - leido);
                if (n <= 0) {
                    break;
                }
                leido += n;
            }
            JSONObject tabla = new JSONObject(new String(buffer, 0, leido,
                    StandardCharsets.UTF_8));
            JSONArray lista = tabla.optJSONArray("patrones");
            if (lista == null) {
                avisoDeCarga = "la tabla no trae patrones";
                return;
            }
            for (int i = 0; i < lista.length(); i++) {
                JSONObject regla = lista.getJSONObject(i);
                List<String> patrones = new ArrayList<>();
                JSONArray ps = regla.optJSONArray("patrones");
                for (int j = 0; ps != null && j < ps.length(); j++) {
                    patrones.add(normaliza(ps.getString(j)));
                }
                reglas.add(new Regla(regla.optString("id"), regla.getString("accion"),
                        regla.optString("param", ""), regla.optString("respuesta"), patrones));
            }
        } catch (IOException | org.json.JSONException roto) {
            avisoDeCarga = "no pude leer mi tabla de frases (" + roto.getMessage() + ")";
        }
    }

    public List<String> acciones() {
        List<String> unicas = new ArrayList<>();
        for (Regla r : reglas) {
            if (!unicas.contains(r.accion)) {
                unicas.add(r.accion);
            }
        }
        return Collections.unmodifiableList(unicas);
    }

    /**
     * Empareja la frase. `null` significa «no la conozco», y la cara lo aprovecha
     * para proponer aprenderla o para preguntar a la nube.
     */
    public Resultado procesar(String entrada) {
        String dicho = normaliza(entrada);
        if (dicho.isEmpty()) {
            return null;
        }
        String[] aprendida = recuerdos == null ? null : recuerdos.habilidad(dicho);
        if (aprendida != null) {
            return new Resultado("aprendida", aprendida[0], aprendida[1], aprendida[2], dicho);
        }
        for (Regla regla : reglas) {
            for (String patron : regla.patrones) {
                String resto = encaja(patron, dicho);
                if (resto != null) {
                    return new Resultado(regla.id, regla.accion, regla.param,
                            regla.respuesta, resto);
                }
            }
        }
        return null;
    }

    /**
     * Un patrón sin `{resto}` casó sólo si es exactamente la frase. Con
     * `{resto}` casó por prefijo y devuelve lo que sobra, ya recortado.
     */
    private static String encaja(String patron, String dicho) {
        int hueco = patron.indexOf("{resto}");
        if (hueco < 0) {
            return patron.equals(dicho) ? "" : null;
        }
        String prefijo = patron.substring(0, hueco).trim();
        if (prefijo.isEmpty() || !dicho.startsWith(prefijo)) {
            return null;
        }
        String resto = dicho.substring(prefijo.length()).trim();
        return resto.isEmpty() ? null : resto;
    }

    /* ------------------------------------------------------------------ encadenar */

    /**
     * Las junturas con las que la dueña encadena dos mandatos en un aliento:
     * «abre Lark player **y** pon After dark», «baja el volumen **luego** pon
     * silencio». La `y` suelta también entra, y por eso el paso siguiente es la
     * guarda que evita el daño que hace: *cada* trozo tiene que casar en la
     * tabla, si no la frase se procesa entera. Sin esa guarda, «pon una alarma a
     * las ocho **y** media» se partiría en dos y CORT pondría una alarma a las
     * ocho y contestaría algo de «media».
     */
    private static final Pattern UNION = Pattern.compile(
            " (?:y luego|luego|y despues|despues de|despues|y) ");

    /** Parte la frase por las junturas, tirando los trozos vacíos. Pura: sin Android. */
    public static List<String> partir(String entrada) {
        List<String> piezas = new ArrayList<>();
        // Se parte sobre la forma **normalizada**: así «Y», «y» y «después» valen lo
        // mismo, y cada trozo que sale ya está en la forma que `procesar` espera.
        for (String trozo : normaliza(entrada).split(UNION)) {
            String limpio = trozo.trim();
            if (!limpio.isEmpty()) {
                piezas.add(limpio);
            }
        }
        return piezas;
    }

    /**
     * Los pasos de una frase, casi siempre uno. El orden **no es** el que parece:
     * primero se parte y se comprueba que *todos* los trozos se conozcan, y sólo
     * si no hay cadena se procesa la frase entera.
     *
     * Se probó al revés —entera primero— y falló con la frase literal de la dueña:
     * «abre Lark player y pon After dark» casa entera contra la regla genérica
     * «abre {resto}», así que el segundo mandato se iba dentro del nombre de la
     * app y CORT contestaba «no encontré «lark player y pon after dark»». Partir
     * primero es lo que hace que los dos mandatos lleguen a sus dos acciones, y la
     * guarda de «todos los trozos» es la que evita que «pon una alarma a las ocho
     * **y** media» se ejecute como dos.
     *
     * Si ningún camino casa sale la lista vacía, y la cara hace lo de siempre:
     * preguntar a la nube o proponer aprender.
     */
    public List<Resultado> cadena(String entrada) {
        List<String> piezas = partir(entrada);
        if (piezas.size() > 1) {
            List<Resultado> pasos = new ArrayList<>();
            for (String pieza : piezas) {
                Resultado r = procesar(pieza);
                if (r == null) {
                    break;          // no es una cadena: se intenta la frase entera
                }
                pasos.add(r);
            }
            if (pasos.size() > 1) {
                return pasos;
            }
        }
        Resultado entera = procesar(entrada);
        if (entera == null) {
            return Collections.emptyList();
        }
        return Collections.singletonList(entera);
    }

    /**
     * Minúsculas, sin tildes, sin signos y con un solo espacio: la forma en que
     * se compara el habla. `assets/habilidades.json` está escrito **así**, y
     * `test_apk_cerebro.py` lo comprueba — un patrón con tilde en la tabla sería
     * un patrón que nunca puede casar.
     */
    public static String normaliza(String texto) {
        if (texto == null) {
            return "";
        }
        String bajo = Normalizer.normalize(texto, Normalizer.Form.NFD)
                .replaceAll("\\p{Mn}+", "").toLowerCase(java.util.Locale.ROOT);
        bajo = bajo.replaceAll("[¿?¡!.,;:\"“”'()]", " ");
        return bajo.replaceAll("\\s+", " ").trim();
    }
}
