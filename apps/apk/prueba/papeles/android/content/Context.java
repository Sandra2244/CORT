package android.content;

import android.content.res.AssetManager;
import java.io.File;

/* Contexto de papel. En el móvil lo da el sistema; aquí lo monta la prueba:
   assets desde una carpeta del disco, preferencias en memoria y una red falsa
   para poder ejercitar las tres ramas de `Mente.preguntar`. */
public class Context {

    public static final int MODE_PRIVATE = 0;
    public static final String CONNECTIVITY_SERVICE = "connectivity";
    public static final String AUDIO_SERVICE = "audio";

    public AssetManager assets = new AssetManager(new File("/tmp/cort-mente/assets"));
    public final SharedPreferences prefs = new SharedPreferences.Falsa();
    public Object sistema;                      // ConnectivityManager, o null
    // F12 · el auricular de papel: cuenta los focos pedidos y devueltos. Sin él,
    // `Oido.audio` sería null y la rama de ducking no se compilaría siquiera.
    public final android.media.AudioManager auricular = new android.media.AudioManager();

    // `filesDir` es donde `Oido` desempaca el modelo de 60 MB. En el papel es una
    // carpeta de /tmp que la prueba crea antes de llamar.
    public java.io.File filesDir = new java.io.File("/tmp/cort-oido/archivos");

    public Context getApplicationContext() { return this; }

    public AssetManager getAssets() { return assets; }

    public java.io.File getFilesDir() { return filesDir; }

    public SharedPreferences getSharedPreferences(String nombre, int modo) { return prefs; }

    public Object getSystemService(String que) {
        if (AUDIO_SERVICE.equals(que)) return auricular;
        return CONNECTIVITY_SERVICE.equals(que) ? sistema : null;
    }
}
