package com.cort.ia;

/*
 * La puerta única que une `Cerebro` (offline) y `Nube` (red). `CortNative` llama
 * aquí sin saber de hilos ni de proveedores: le pasa la petición del contrato y
 * recibe JSON, o engancha un callback para que le llegue el resultado largo.
 *
 * Dos caminos, según el contrato (§4 · `mente`):
 *
 *  · `estado` y `ajustar` no tocan la red: se responden en el sitio delegando en
 *    `Nube.mente`. El método devuelve el JSON completo.
 *  · `preguntar` y `probar` SÍ red: se contesta enseguida `{"ok":true,"pendiente":true}`
 *    y el trabajo largo va en un hilo aparte (`new Thread(…, "cort-mente").start()`).
 *    La respuesta vuelve por el callback `AlResponder`, que `CortNative` convertirá
 *    en el evento `window.__cortNative.emit({type:"mente", …})`.
 *
 * Regla de oro del hilo: NINGUNA red sale del hilo del puente. Un método
 * `@JavascriptInterface` que llame a `HttpURLConnection` revienta con
 * `NetworkOnMainThreadException`; por eso todo lo que habla por internet se lanza
 * aquí en su propio hilo, igual que hace `CortNative` con `cort-musica-automatica`.
 *
 * La ronda local (documentada porque la cara tiene que conocerla): cuando la
 * frase es una acción conocida, NO se ejecuta desde aquí. Se nombra. Se devuelve
 * `{"ok":true,"responde":"…","de":"local","accion":"volumen","param":"sube"}` y la
 * cara, al ver `accion` en el evento, la reenvía a `accion(que:accion, args:param)`.
 * Así `Mente` no necesita ni permisos ni el `WebView` para mover el aparato.
 *
 * Antes de la ronda local hay tres escalones, y el orden importa porque cada uno
 * es más caro que el anterior: `Cerebro` casa la frase con su tabla (coste cero,
 * mueve el aparato); si no casa, `Razon` mira si es cuenta, porcentaje, cambio de
 * unidad o fecha —puro Java, sin Android y sin red, coste cero también— y devuelve
 * `{"ok":true,"responde":"Es 51.","de":"local","eco":"…"}` SIN `accion`, que la
 * cara se limita a hablar; y sólo si los dos callan se gasta un `preguntar` de
 * nube. Bajar la nube por debajo de `Razon` sería pagar por algo que se resuelve
 * en el propio teléfono.
 */

import android.content.Context;
import android.util.Log;

public class Mente {

    /** Callback de resultado largo. `CortNative` lo engancha y hace `cuadro(json)`. */
    public interface AlResponder {
        void con(String json);
    }

    private final Context app;
    private final Nube nube;
    private final Cerebro cerebro;

    /** El emisor por defecto que usa `mente(...)` para `preguntar`/`probar`. */
    private volatile AlResponder emisor;

    public Mente(Context contexto, Nube nube, Cerebro cerebro) {
        this.app = contexto.getApplicationContext();
        this.nube = nube;
        this.cerebro = cerebro;
    }

    /** El hook que `CortNative` llama una vez para que el resultado largo llegue a la cara. */
    public void engancha(AlResponder emisor) {
        this.emisor = emisor;
    }

    /* ───────────────────────── despachador del contrato ─────────── */

    /**
     * Resuelve `que`: `estado`/`ajustar` en el sitio (sin red); `preguntar`/`probar`
     * contestan `pendiente` y lanzan el hilo `cort-mente`. Nunca lanza una excepción.
     */
    public String mente(String peticion) {
        try {
            org.json.JSONObject j = parsea(peticion);
            if (j == null) return mal("no entendí la petición de mente");
            String que = j.optString("que", "").toLowerCase(java.util.Locale.ROOT);
            if ("estado".equals(que) || "ajustar".equals(que)) {
                return nube.mente(peticion);              // sincronía sin red
            }
            org.json.JSONObject args = j.optJSONObject("args");
            if ("preguntar".equals(que)) {
                String texto = campo(j, args, "texto");
                String eco = campo(j, args, "eco");
                lanzarPreguntar(texto, eco);
                return pendiente();
            }
            if ("probar".equals(que)) {
                lanzarProbar();
                return pendiente();
            }
            return mal("no conozco ese que de mente: " + que);
        } catch (Exception cualquierCosa) {
            Log.w("cort", "mente", cualquierCosa);
            return mal("se me cruzaron los cables pensando");
        }
    }

    /* ─────────────────────────── preguntar (offline primero) ────── */

    /**
     * Entrada directa para `CortNative`: si la acción es conocida se responde aquí
     * mismo (`de:"local"`, sin red ni coste); si es desconocida y hay nube y red,
     * se lanza el hilo `cort-mente`; si no, una respuesta honesta.
     *
     * `sigue` se llama con el JSON del evento (sin `type`: eso lo añade la cara).
     */
    public void preguntar(String texto, String eco, AlResponder sigue) {
        AlResponder entrega = sigue != null ? sigue : emisor;
        try {
            Cerebro.Resultado r = cerebro.procesar(texto);
            if (r != null && !"desconocido".equals(r.accion)) {
                entregar(entrega, local(r, eco));
                return;
            }
            // Ni acción conocida: antes de gastar red, `Razon` mira si es cuenta,
            // porcentaje, unidad o fecha. Puro Java, sin Android y sin internet, así
            // que responde en el hilo del puente sin riesgo de reventar nada.
            String razon = Razon.intenta(texto);
            if (razon != null) {
                entregar(entrega, razon(razon, eco));
                return;
            }
            // Desconocida: a la nube si está lista y hay red; si no, honestidad.
            if (nube.configurada() && nube.hayRed()) {
                nuevoHilo(() -> {
                    String respuesta = nube.preguntar(texto, null);
                    if (respuesta == null) {
                        entregar(entrega, "{\"ok\":false,\"dice\":" + comilla(nube.ultimoFallo())
                             + ",\"de\":\"nube\",\"eco\":" + comilla(eco40(eco)) + "}");
                    } else {
                        entregar(entrega, "{\"ok\":true,\"responde\":" + comilla(respuesta)
                             + ",\"de\":\"nube\",\"eco\":" + comilla(eco40(eco)) + "}");
                    }
                });
            } else {
                entregar(entrega, sinCerebro(eco));
            }
        } catch (Exception cualquierCosa) {
            Log.w("cort", "preguntar", cualquierCosa);
            entregar(entrega, mal("no pude pensar eso"));
        }
    }

    private void lanzarPreguntar(String texto, String eco) {
        AlResponder entrega = emisor;
        preguntar(texto, eco, new AlResponder() {
            @Override public void con(String json) {
                if (entrega != null) { try { entrega.con(json); } catch (Exception e) { Log.w("cort", "emisor", e); } }
                else Log.w("cort", "mente: pregunta sin emisor enganchado");
            }
        });
    }

    private void lanzarProbar() {
        final AlResponder entrega = emisor;
        nuevoHilo(() -> {
            String respuesta = nube.prueba();
            String json;
            if (respuesta == null) {
                json = "{\"ok\":false,\"dice\":" + comilla(nube.ultimoFallo())
                     + ",\"de\":\"nube\",\"eco\":" + comilla("prueba") + "}";
            } else {
                json = "{\"ok\":true,\"responde\":" + comilla(respuesta)
                     + ",\"de\":\"nube\",\"eco\":" + comilla("prueba") + "}";
            }
            if (entrega != null) { try { entrega.con(json); } catch (Exception e) { Log.w("cort", "emisor", e); } }
        });
    }

    /* ───────────────────────────── piezas ───────────────────────── */

    /** El JSON de una acción conocida: se nombra, no se ejecuta aquí. */
    private static String local(Cerebro.Resultado r, String eco) {
        String dice = r.respuesta == null || r.respuesta.isEmpty()
            ? "Vale: " + r.accion : r.respuesta;
        return "{\"ok\":true,\"responde\":" + comilla(dice)
             + ",\"de\":\"local\",\"accion\":" + comilla(r.accion)
             + ",\"param\":" + comilla(r.param == null ? "" : r.param)
             + ",\"eco\":" + comilla(eco40(eco)) + "}";
    }

    /**
     * La respuesta de `Razon`: un cálculo, un cambio de unidad o la fecha, dicha
     * aquí y ahora. Lleva `de:"local"` y NO lleva `accion`: la cara habla el texto
     * y no reenvía nada, porque no hay aparato que mover.
     */
    private static String razon(String dice, String eco) {
        return "{\"ok\":true,\"responde\":" + comilla(dice)
             + ",\"de\":\"local\",\"eco\":" + comilla(eco40(eco)) + "}";
    }

    /** Sin nube y sin red: no hay cerebro, y se dice cómo encenderlo. */
    private static String sinCerebro(String eco) {
        return "{\"ok\":true,\"responde\":" + comilla(
            "Eso no lo pillo sin cerebro: no hay nube configurada y no encuentro red. "
          + "Actívala en Ajustes (proveedor, modelo y clave) o conéctate al PC por Wi‑Fi "
          + "para usar el modelo local, y vuelvo a intentarlo.")
            + ",\"de\":\"local\",\"eco\":" + comilla(eco40(eco)) + "}";
    }

    private static void entregar(AlResponder sigue, String json) {
        if (sigue == null) { Log.w("cort", "mente: resultado sin emisor"); return; }
        try {
            sigue.con(json);
        } catch (Exception rev) {
            Log.w("cort", "mente: el emisor falló", rev);
        }
    }

    /** Hilo con nombre, como `cort-musica-automatica` en el puente. */
    private static void nuevoHilo(Runnable trabajo) {
        new Thread(trabajo, "cort-mente").start();
    }

    /* ───────────────────────────── JSON a mano ──────────────────── */

    private static String eco40(String eco) {
        if (eco == null) return "";
        String s = eco.trim();
        return s.length() <= 40 ? s : s.substring(0, 40);
    }

    private static org.json.JSONObject parsea(String crudo) {
        if (crudo == null || crudo.trim().isEmpty()) return null;
        try { return new org.json.JSONObject(crudo); }
        catch (Exception noEsJson) { return null; }
    }

    private static String campo(org.json.JSONObject j, org.json.JSONObject args, String clave) {
        if (j.has(clave)) return j.optString(clave, "");
        if (args != null && args.has(clave)) return args.optString(clave, "");
        return "";
    }

    private static String pendiente() {
        return "{\"ok\":true,\"pendiente\":true}";
    }

    private static String mal(String dice) {
        return "{\"ok\":false,\"dice\":" + comilla(dice) + "}";
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
