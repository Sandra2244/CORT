package android.content;

import android.content.res.AssetManager;
import java.io.File;

/* Contexto de papel. En el móvil lo da el sistema; aquí lo monta la prueba:
   assets desde una carpeta del disco, preferencias en memoria y una red falsa
   para poder ejercitar las tres ramas de `Mente.preguntar`. */
public class Context {

    public static final int MODE_PRIVATE = 0;
    public static final String CONNECTIVITY_SERVICE = "connectivity";

    public AssetManager assets = new AssetManager(new File("/tmp/cort-mente/assets"));
    public final SharedPreferences prefs = new SharedPreferences.Falsa();
    public Object sistema;                      // ConnectivityManager, o null

    // `filesDir` es donde `Oido` desempaca el modelo de 60 MB. En el papel es una
    // carpeta de /tmp que la prueba crea antes de llamar.
    public java.io.File filesDir = new java.io.File("/tmp/cort-oido/archivos");

    public Context getApplicationContext() { return this; }

    public AssetManager getAssets() { return assets; }

    public java.io.File getFilesDir() { return filesDir; }

    public SharedPreferences getSharedPreferences(String nombre, int modo) { return prefs; }

    public Object getSystemService(String que) {
        return CONNECTIVITY_SERVICE.equals(que) ? sistema : null;
    }
}
