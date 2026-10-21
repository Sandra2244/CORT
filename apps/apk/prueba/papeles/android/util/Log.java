package android.util;

/* El Log de Android, en versión papel: cuenta las líneas para que un prueba
   pueda ver si el código fue a la rama de excepción sin imprimir un montón. */
public final class Log {
    public static int contador = 0;

    public static int v(String t, String m) { return anota(t + " " + m); }
    public static int d(String t, String m) { return anota(t + " " + m); }
    public static int i(String t, String m) { return anota(t + " " + m); }
    public static int w(String t, String m) { return anota(t + " " + m); }
    public static int w(String t, String m, Throwable e) { return anota(t + " " + m + " :: " + e); }
    public static int e(String t, String m) { return anota(t + " " + m); }
    public static int e(String t, String m, Throwable e) { return anota(t + " " + m + " :: " + e); }

    private static int anota(String linea) { contador++; return linea.length(); }
}
