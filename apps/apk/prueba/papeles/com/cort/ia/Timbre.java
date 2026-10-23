package com.cort.ia;

import android.content.Context;
import java.util.ArrayList;
import java.util.List;

/*
 * Timbre de papel. El aviso verdadero (`apps/apk/src/com/cort/ia/Timbre.java`)
 * habla con `NotificationManager`, y eso en el JDK no existe ni debe fingirse con
 * más que un hueco: aquí lo que importa es comprobar que `Ollama` LLAMA al aviso
 * en el momento justo y con los datos justos. La firma es la misma, así que si el
 * día de mañana cambian una por una y el `javac` de `scripts/prueba-mente.sh` no
 * compila, el rojo se ve aquí y no en el teléfono.
 *
 * `PUESTOS` es la libreta: cada aviso que el código de producción habría pegado se
 * apunta como texto, y `Prueba4` la lee.
 */
public class Timbre {

    public static final List<String> PUESTOS = new ArrayList<>();

    public static void bajada(Context app, boolean bien, String nombre,
                              long hecho, long total, String motivo, String donde) {
        PUESTOS.add((bien ? "listo " : "paró ") + nombre
                    + "|" + Ollama.peso(hecho) + "|" + (total > 0 ? Ollama.peso(total) : "0 GB")
                    + "|" + motivo + "|" + donde);
    }

    /** La libreta se limpia entre pruebas, para que un aviso viejo no tape un rojo. */
    public static void limpia() { PUESTOS.clear(); }
}
