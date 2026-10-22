package org.json;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/* La cara de org.json que miran los ficheros del APK. Guarda LinkedHashMap y
   ArrayList; los `opt` nunca lanzan, los `get` sí, igual que en Android. */
public class JSONObject {

    protected final Map<String, Object> datos;

    public JSONObject() { this.datos = new LinkedHashMap<>(); }

    public JSONObject(String crudo) throws JSONException {
        Object v = new Lector(crudo).raiz();
        if (!(v instanceof Map)) throw new JSONException("esto no es un objeto");
        this.datos = copia((Map<?, ?>) v);
    }

    JSONObject(Map<String, Object> d) { this.datos = d; }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> copia(Map<?, ?> origen) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (Map.Entry<?, ?> e : origen.entrySet()) out.put(String.valueOf(e.getKey()), e.getValue());
        return out;
    }

    public JSONObject put(String k, Object v) { datos.put(k, v); return this; }

    public Iterator<String> keys() { return datos.keySet().iterator(); }

    public int length() { return datos.size(); }

    public boolean has(String k) { return datos.containsKey(k); }

    public boolean isNull(String k) { return !datos.containsKey(k) || datos.get(k) == null; }

    public Object get(String k) throws JSONException {
        if (!datos.containsKey(k)) throw new JSONException("no hay clave " + k);
        return datos.get(k);
    }

    public String getString(String k) throws JSONException {
        Object v = get(k);
        return v == null ? null : String.valueOf(v);
    }

    public int getInt(String k) throws JSONException {
        Object v = get(k);
        if (v instanceof Number) return ((Number) v).intValue();
        throw new JSONException(k + " no es número");
    }

    public JSONObject getJSONObject(String k) throws JSONException {
        Object v = get(k);
        if (v instanceof Map) return new JSONObject((Map<String, Object>) v);
        throw new JSONException(k + " no es objeto");
    }

    public JSONArray getJSONArray(String k) throws JSONException {
        Object v = get(k);
        if (v instanceof List) return new JSONArray((List<Object>) v);
        throw new JSONException(k + " no es lista");
    }

    public String optString(String k) { return optString(k, ""); }

    public String optString(String k, String porDefecto) {
        Object v = datos.get(k);
        return v == null ? porDefecto : String.valueOf(v);
    }

    public int optInt(String k, int porDefecto) {
        Object v = datos.get(k);
        return v instanceof Number ? ((Number) v).intValue() : porDefecto;
    }

    // El tamaño de un modelo se dice en bytes y caben mal en un `int` (1,1 GB es
    // 1.100.000.000 > 2^31-2 … justito). `Ollama` lee `size`, `total` y `completed`
    // con `optLong`, que es lo que trae el `org.json` de Android de verdad.
    public long optLong(String k, long porDefecto) {
        Object v = datos.get(k);
        return v instanceof Number ? ((Number) v).longValue() : porDefecto;
    }

    public boolean optBoolean(String k, boolean porDefecto) {
        Object v = datos.get(k);
        return v instanceof Boolean ? (Boolean) v : porDefecto;
    }

    public JSONObject optJSONObject(String k) {
        Object v = datos.get(k);
        return v instanceof Map ? new JSONObject((Map<String, Object>) v) : null;
    }

    public JSONArray optJSONArray(String k) {
        Object v = datos.get(k);
        return v instanceof List ? new JSONArray((List<Object>) v) : null;
    }

    public String toString() {
        StringBuilder b = new StringBuilder("{");
        boolean primero = true;
        for (Map.Entry<String, Object> e : datos.entrySet()) {
            if (!primero) b.append(',');
            primero = false;
            b.append(comilla(e.getKey())).append(':').append(pinta(e.getValue()));
        }
        return b.append('}').toString();
    }

    static String comilla(String s) {
        StringBuilder o = new StringBuilder("\"");
        for (int n = 0; n < s.length(); n++) {
            char c = s.charAt(n);
            switch (c) {
                case '"':  o.append("\\\""); break;
                case '\\': o.append("\\\\"); break;
                case '\n': o.append("\\n");  break;
                case '\t': o.append("\\t");  break;
                case '\r': o.append("\\r");  break;
                default: o.append(c);
            }
        }
        return o.append('"').toString();
    }

    static String pinta(Object v) {
        if (v == null) return "null";
        if (v instanceof Boolean || v instanceof Number) return String.valueOf(v);
        // Un `JSONObject` de papel metido dentro de otro (o de un `JSONArray`) no es
        // un `Map`: hay que preguntarle primero por su clase, si no se imprimiría
        // `org.json.JSONObject@…` dentro del JSON y la cara no lo leería.
        if (v instanceof JSONObject) return ((JSONObject) v).toString();
        if (v instanceof JSONArray) return v.toString();
        if (v instanceof Map) return new JSONObject(cop((Map<String, Object>) v)).toString();
        if (v instanceof List) return new JSONArray(new ArrayList<Object>((List<Object>) v)).toString();
        return comilla(String.valueOf(v));
    }

    @SuppressWarnings("unchecked")
    static Map<String, Object> cop(Map<?, ?> m) {
        Map<String, Object> out = new LinkedHashMap<>();
        for (Map.Entry<?, ?> e : m.entrySet()) out.put(String.valueOf(e.getKey()), e.getValue());
        return out;
    }
}
