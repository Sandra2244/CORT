package com.cort.ia;

/*
 * Los seis trajes de CORT y lo que la cara tiene que pintar con cada uno.
 * Sección 5 de `docs/CONTRATO-PUENTE-2.1.md`: entra `{"que":"lista"}` o
 * `{"que":"poner","nombre":"Matrix"}` por `atuendo(String)` y sale JSON.
 *
 * Es la portación de `dev.sandra.cort.Paleta` (allí eran siete enteros de marca
 * para la cara nativa; aquí son los atuendos que faltaban en el APK publicado,
 * que sólo sabía de uno).
 *
 * Lo que NO puede hacer, dicho sin adornos:
 *
 * · **No pinta nada.** CORT no toca el CSS: devuelve la cadena
 *   `--primario:#…;--secundario:#…` y la cara (`ui/`) se viste. Por eso el puesto
 *   se guarda en `SharedPreferences` y no en una variable: la cara puede estar
 *   cerrada cuando se pide el traje, y al volver tiene que seguir vestida igual.
 * · **No admite colores escritos por la dueña.** La tabla es fija y cerrada: un
 *   `#` que venga del habla acabaría dentro de una hoja de estilo, y eso no se
 *   hace ni en broma. Si el nombre no está en la tabla, `ok:false` con la lista.
 * · **No descarga trajes de la red ni lee temas del sistema**: no hay API pública
 *   para eso, y prometer «ponte como tu teléfono» sin poder leerlo sería mentira.
 * · **No lanza excepciones**: `atuendo` devuelve siempre JSON, incluso con el
 *   `peticion` roto o vacío.
 * · **No tiene estado raro**: un único campo, `atuendo`, en las preferencias
 *   `cort` — el mismo archivo donde viven `pc` y `juego`, para que el respaldo
 *   y el borrado sigan siendo una sola cosa.
 */

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.util.Log;

import org.json.JSONException;
import org.json.JSONObject;

import java.text.Normalizer;
import java.util.Locale;

public class Paleta {

    private static final String LOG = "cort";

    /** El archivo de preferencias compartido con `MainActivity` y `CortNative`. */
    private static final String ARCHIVO = "cort";
    private static final String CLAVE = "atuendo";

    /**
     * nombre ▸ primario ▸ secundario. Los dos primeros literales de `Cortana` son
     * los que fija el contrato (§ 5) y los mismos de la cara de PC; el resto están
     * elegidos para que el contraste con fondo oscuro aguante en una pantalla de
     * calle bajo el sol, que es donde vive este teléfono.
     */
    private static final String[][] TRAJES = {
        {"Cortana",   "#59d9ff", "#0a3d62"},
        {"JARVIS",    "#ffc46b", "#241405"},
        {"Siri",      "#ff5fa2", "#3d0f33"},
        {"Matrix",    "#22ff88", "#04160c"},
        {"Atardecer", "#ff7a45", "#3d1a4d"},
        {"Neutron",   "#e8eef2", "#1b2226"},
    };

    /** El traje con el que nace CORT: el de la cara de siempre. */
    private static final String POR_DEFECTO = "Cortana";

    private final Context contexto;

    /**
     * Mismo molde que `Acciones`: la construye `CortNative` con su `Activity`. Se
     * guarda el `Context` de aplicación, que es el que sobrevive a que se gire la
     * pantalla o se cierre la cara: leer y escribir una preferencia no necesita
     * una Activity viva.
     */
    public Paleta(Activity act) {
        Context app = act == null ? null : act.getApplicationContext();
        this.contexto = app != null ? app : act;
    }

    /* ────────────────────────────── la entrada ────────────────────────────── */

    /**
     * `atuendo({"que":"lista"})` y `atuendo({"que":"poner","nombre":"Siri"})`.
     * Devuelve siempre JSON y nunca lanza.
     */
    public String atuendo(String peticion) {
        try {
            String que = normaliza(clave(peticion, "que"));
            if (que.isEmpty()) {
                return error("no sé qué hacer con el atuendo: me llega sin «que». "
                        + "Vale lista o poner.");
            }
            if (que.equals("lista") || que.equals("todos")) {
                return lista();
            }
            if (que.equals("poner") || que.equals("cambiar") || que.equals("usa")) {
                return poner(peticion);
            }
            if (que.equals("estado") || que.equals("puesto")) {
                return Json.ok().p("puesto", puesto(contexto)).fin();
            }
            return error("no conozco ese «que» del atuendo («" + que + "»): vale lista o poner.");
        } catch (Throwable todo) {
            Log.e(LOG, "atuendo falló: " + peticion, todo);
            return error("algo se rompió dentro de CORT al cambiar de traje.");
        }
    }

    /* ───────────────────────────────── lista ──────────────────────────────── */

    /**
     * `{"ok":true,"atuendos":[{"nombre":"…","primario":"#…","secundario":"#…"}],
     *  "puesto":"…"}` exactamente como promete el contrato.
     */
    private String lista() {
        StringBuilder s = new StringBuilder("[");
        for (int i = 0; i < TRAJES.length; i++) {
            if (i > 0) s.append(',');
            s.append("{\"nombre\":\"").append(esc(TRAJES[i][0]))
             .append("\",\"primario\":\"").append(esc(TRAJES[i][1]))
             .append("\",\"secundario\":\"").append(esc(TRAJES[i][2]))
             .append("\",\"puesto\":")
             .append(TRAJES[i][0].equalsIgnoreCase(puesto(contexto)) ? "true" : "false")
             .append('}');
        }
        s.append(']');
        return new Json(true).crudo("atuendos", s.toString())
                .p("puesto", puesto(contexto))
                .p("total", TRAJES.length)
                .fin();
    }

    /* ───────────────────────────────── poner ──────────────────────────────── */

    /**
     * Busca el traje en la tabla (normalizado, con `jarvis`/`JARVIS`/`Jarvis`
     * valiendo lo mismo) y guarda el nombre. `llevate`/`predeterminada` vuelven al
     * traje de nacimiento.
     */
    private String poner(String peticion) {
        String pedido = normaliza(clave(peticion, "nombre", "atuendo", "a", "args", "suelto"));
        if (pedido.isEmpty()) {
            return error("¿de qué traje? Tengo " + nombres() + ".");
        }
        if (pedido.equals("ninguno") || pedido.equals("el de siempre")
                || pedido.equals("predeterminada") || pedido.equals("defecto")
                || pedido.equals("normal")) {
            return guarda(filaDe(POR_DEFECTO));
        }
        String[] traje = busca(pedido);
        if (traje == null) {
            return error("No tengo ese traje («" + pedido + "»). Los míos son " + nombres()
                    + ". Dime «atuendo lista» y te los leo.");
        }
        return guarda(traje);
    }

    /** La respuesta del contrato: `{"ok":true,"css":"--primario:#…;--secundario:#…"}`. */
    private String guarda(String[] traje) {
        pone(contexto, traje[0]);
        return Json.ok()
                .p("nombre", traje[0])
                .p("puesto", traje[0])
                .p("primario", traje[1])
                .p("secundario", traje[2])
                .p("css", "--primario:" + traje[1] + ";--secundario:" + traje[2])
                .fin();
    }

    /* ─────────────────────────── la tabla, en claro ───────────────────────── */

    private static String[] busca(String pedido) {
        for (String[] traje : TRAJES) {
            if (normaliza(traje[0]).equals(pedido)) return traje;
        }
        // Sin tildes ni mayúsculas: «neutrón» llega como «neutron» y «Atardecer»
        // como «atardecer». También se acepta el color, que es como lo piden.
        for (String[] traje : TRAJES) {
            if (normaliza(traje[1]).equals(pedido) || normaliza(traje[2]).equals(pedido)) {
                return traje;
            }
        }
        for (String[] traje : TRAJES) {
            if (normaliza(traje[0]).contains(pedido) || pedido.contains(normaliza(traje[0]))) {
                return traje;
            }
        }
        return null;
    }

    private static String[] filaDe(String nombre) {
        String[] traje = busca(normaliza(nombre));
        return traje != null ? traje : TRAJES[0];
    }

    private static String nombres() {
        StringBuilder s = new StringBuilder();
        for (int i = 0; i < TRAJES.length; i++) {
            if (i > 0) s.append(i + 1 == TRAJES.length ? " y " : ", ");
            s.append(TRAJES[i][0]);
        }
        return s.toString();
    }

    /* ──────────────────────────── lo que se guarda ────────────────────────── */

    private static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences(ARCHIVO, Context.MODE_PRIVATE);
    }

    /** El traje puesto; `Cortana` si aún nadie lo eligió o las prefs no están. */
    public static String puesto(Context c) {
        try {
            String guardado = prefs(c).getString(CLAVE, POR_DEFECTO);
            if (guardado == null || guardado.trim().isEmpty()) return POR_DEFECTO;
            String[] traje = filaDe(guardado);
            return traje[0];                       // normalizado contra la tabla
        } catch (Throwable sinPreferencias) {
            return POR_DEFECTO;
        }
    }

    private static void pone(Context c, String nombre) {
        try {
            prefs(c).edit().putString(CLAVE, nombre).apply();
        } catch (Throwable noEscribe) {
            Log.e(LOG, "no pude guardar el atuendo", noEscribe);
        }
    }

    /**
     * El color primario del traje puesto, como entero ARGB: es lo que pinta
     * `Flotante` en el círculo de la burbuja para que el puntito vista el mismo
     * traje que la cara. `Color.parseColor` es API 1 y no necesita guarda.
     */
    public static int primario(Context c) {
        return color(filaDe(puesto(c))[1], 0xFF59D9FF);
    }

    /** El secundario del traje puesto, para el aro exterior de la burbuja. */
    public static int secundario(Context c) {
        return color(filaDe(puesto(c))[2], 0xFF0A3D62);
    }

    private static int color(String hex, int siFalla) {
        try {
            return Color.parseColor(hex);
        } catch (Throwable hexRoto) {
            return siFalla;
        }
    }

    /* ───────────────────────────── JSON a mano ────────────────────────────── */

    /**
     * Lee una clave de la petición: primero la raíz, luego `args` si era un objeto,
     * y al final `args` dicho a pelo. La clave `args` **nunca** se devuelve como
     * texto: `optString` de un objeto imprimido sería `{...}` viajando al habla.
     *
     * El `JSONObject` se construye sólo con el constructor de texto, que es el que
     * declara `throws JSONException` en Android (allí es una excepción comprobada,
     * no de tipo runtime, a diferencia de la librería `org.json` de Maven) y por
     * eso el `catch` es obligatorio.
     */
    private static String clave(String peticion, String... claves) {
        if (peticion == null || peticion.trim().isEmpty()) return "";
        String recio = peticion.trim();
        if (!recio.startsWith("{")) {
            return recio;                       // la cara vieja mandaba la palabra suelta
        }
        try {
            JSONObject raiz = new JSONObject(recio);
            Object dentro = raiz.opt("args");
            JSONObject args = dentro instanceof JSONObject ? (JSONObject) dentro : null;
            for (String clave : claves) {
                if (clave.equals("args")) continue;
                String valor = leo(raiz, clave);
                if (!valor.isEmpty()) return valor;
                valor = leo(args, clave);
                if (!valor.isEmpty()) return valor;
            }
            if (args == null && dentro != null) {
                String suelto = dentro.toString().trim();
                if (!suelto.isEmpty() && !suelto.startsWith("{")) return suelto;
            }
            return "";
        } catch (JSONException noEsJson) {
            return "";
        }
    }

    private static String leo(JSONObject donde, String clave) {
        if (donde == null) return "";
        String valor = donde.optString(clave, "");
        return valor == null ? "" : valor.trim();
    }

    private static String error(String dice) {
        return "{\"ok\":false,\"dice\":\"" + esc(dice) + "\"}";
    }

    private static String esc(String texto) {
        if (texto == null) return "";
        StringBuilder s = new StringBuilder(texto.length() + 8);
        for (int i = 0; i < texto.length(); i++) {
            char c = texto.charAt(i);
            if (c == '"' || c == '\\') { s.append('\\').append(c); }
            else if (c == '\n') s.append("\\n");
            else if (c == '\r') s.append(' ');
            else if (c == '\t') s.append(' ');
            else if (c < 0x20) { /* fuera */ }
            else s.append(c);
        }
        return s.toString();
    }

    /** Mismo molde que el de `Acciones`: `{"ok":true, …}` escrito a mano. */
    private static final class Json {
        private final StringBuilder s;

        Json(boolean ok) {
            s = new StringBuilder("{\"ok\":").append(ok);
        }

        static Json ok() {
            return new Json(true);
        }

        Json p(String clave, String valor) {
            s.append(",\"").append(clave).append("\":\"").append(esc(valor)).append('"');
            return this;
        }

        Json p(String clave, int valor) {
            s.append(",\"").append(clave).append("\":").append(valor);
            return this;
        }

        Json crudo(String clave, String valor) {
            s.append(",\"").append(clave).append("\":").append(valor);
            return this;
        }

        String fin() { return s.append('}').toString(); }
    }

    /** Minúsculas y sin tildes: «Neutrón» y «neutron» son el mismo traje. */
    private static String normaliza(String texto) {
        if (texto == null) return "";
        String bajo = Normalizer.normalize(texto, Normalizer.Form.NFD)
                .replaceAll("\\p{Mn}+", "").toLowerCase(Locale.ROOT);
        bajo = bajo.replaceAll("[¿?¡!.,;:\"“”'()]", " ");
        return bajo.replaceAll("\\s+", " ").trim();
    }
}
