package android.content;

import java.util.HashMap;
import java.util.Map;

/* Preferencias de memoria: `Nube` guarda aquí proveedor, modelo y clave. */
public interface SharedPreferences {

    String getString(String clave, String porDefecto);
    boolean getBoolean(String clave, boolean porDefecto);
    int getInt(String clave, int porDefecto);
    boolean contains(String clave);
    Map<String, ?> getAll();
    Editor edit();

    interface Editor {
        Editor putString(String clave, String valor);
        Editor putBoolean(String clave, boolean valor);
        Editor putInt(String clave, int valor);
        Editor remove(String clave);
        boolean commit();
        void apply();
    }

    /** El bulto de papel que usa la prueba. */
    class Falsa implements SharedPreferences {
        private final Map<String, Object> datos = new HashMap<>();

        @Override public String getString(String k, String d) {
            Object v = datos.get(k); return v == null ? d : String.valueOf(v);
        }
        @Override public boolean getBoolean(String k, boolean d) {
            Object v = datos.get(k); return v instanceof Boolean ? (Boolean) v : d;
        }
        @Override public int getInt(String k, int d) {
            Object v = datos.get(k); return v instanceof Number ? ((Number) v).intValue() : d;
        }
        @Override public boolean contains(String k) { return datos.containsKey(k); }
        @Override public Map<String, ?> getAll() { return new HashMap<>(datos); }
        @Override public Editor edit() { return new EditorDe(); }

        private class EditorDe implements Editor {
            @Override public Editor putString(String k, String v) { datos.put(k, v); return this; }
            @Override public Editor putBoolean(String k, boolean v) { datos.put(k, v); return this; }
            @Override public Editor putInt(String k, int v) { datos.put(k, v); return this; }
            @Override public Editor remove(String k) { datos.remove(k); return this; }
            @Override public boolean commit() { return true; }
            @Override public void apply() { }
        }
    }
}
