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
                    + "|" + peso(hecho) + "|" + (total > 0 ? peso(total) : "0 GB")
                    + "|" + motivo + "|" + donde);
    }

    /** La libreta se limpia entre pruebas, para que un aviso viejo no tape un rojo. */
    public static void limpia() { PUESTOS.clear(); }

    /* El mismo recibo que `Ollama.peso`, COPYADO a propósito y no llamado: este papel
       lo compila también `scripts/prueba-oido.sh`, que compila ÚNICAMENTE los gemelos
       (sin `Ollama.java` delante), y allí un `Ollama.peso` sería un `cannot find
       symbol` en mitad del pipeline. Copiar una línea de formato cuesta menos que
       romperle a la dueña un step que no tenía nada que ver con el aviso. */
    private static String peso(long b) {
        if (b <= 0) return "0 GB";
        if (b >= 100_000_000L) return String.format(java.util.Locale.ROOT, "%.1f GB", b / 1e9);
        if (b >= 100_000L) return String.format(java.util.Locale.ROOT, "%.0f MB", b / 1e6);
        return String.format(java.util.Locale.ROOT, "%.0f KB", b / 1e3);
    }
}
