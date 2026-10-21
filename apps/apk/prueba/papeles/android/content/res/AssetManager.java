package android.content.res;

import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.File;

/* `getAssets().open(...)` sobre una carpeta del disco: así la prueba puede
   darle a Cerebro el `habilidades.json` auténtico del repo. */
public final class AssetManager {
    private final File raiz;

    public AssetManager(File raiz) { this.raiz = raiz; }

    public InputStream open(String nombre) throws IOException {
        return new FileInputStream(new File(raiz, nombre));
    }
}
