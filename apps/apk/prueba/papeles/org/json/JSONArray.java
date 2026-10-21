package org.json;

import java.util.ArrayList;
import java.util.List;

/* La lista de org.json, con los mismos `get`/`opt` que usa `Cerebro.cargar`. */
@SuppressWarnings("unchecked")
public class JSONArray {

    private final List<Object> items;

    public JSONArray() { this.items = new ArrayList<>(); }

    public JSONArray(String crudo) throws JSONException {
        Object v = new Lector(crudo).raiz();
        if (!(v instanceof List)) throw new JSONException("esto no es una lista");
        this.items = new ArrayList<Object>((List<Object>) v);
    }

    JSONArray(List<Object> d) { this.items = new ArrayList<Object>(d); }

    public JSONArray put(Object v) { items.add(v); return this; }

    public int length() { return items.size(); }

    public Object get(int i) throws JSONException {
        if (i < 0 || i >= items.size()) throw new JSONException("fuera de la lista " + i);
        return items.get(i);
    }

    public String getString(int i) throws JSONException {
        Object v = get(i);
        return v == null ? null : String.valueOf(v);
    }

    public int getInt(int i) throws JSONException {
        Object v = get(i);
        if (v instanceof Number) return ((Number) v).intValue();
        throw new JSONException("el " + i + " no es número");
    }

    public JSONObject getJSONObject(int i) throws JSONException {
        Object v = get(i);
        if (v instanceof java.util.Map) {
            return new JSONObject(JSONObject.cop(v instanceof java.util.Map ? (java.util.Map<String, Object>) v : null));
        }
        throw new JSONException("el " + i + " no es objeto");
    }

    public JSONObject optJSONObject(int i) {
        if (i < 0 || i >= items.size()) return null;
        Object v = items.get(i);
        return v instanceof java.util.Map ? new JSONObject(JSONObject.cop((java.util.Map<String, Object>) v)) : null;
    }
}
