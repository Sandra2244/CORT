package android.os;

import java.io.File;

/* `StatFs(ruta).getAvailableBytes()`. En el portátil mide el disco de verdad,
   así que la rama de «no cabe» se puede ejercitar con un número a mano. */
public class StatFs {
    public static long FALSO_LIBRE = -1;         // la prueba lo pone para forzar la rama
    private final File raiz;

    public StatFs(String ruta) { this.raiz = new File(ruta); }

    public long getAvailableBytes() {
        if (FALSO_LIBRE >= 0) return FALSO_LIBRE;
        return raiz.getTotalSpace() - raiz.getUsableSpace() >= 0 ? raiz.getUsableSpace() : 0;
    }
}
