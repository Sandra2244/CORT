package com.cort.ia;

import android.content.Context;
import android.content.res.AssetManager;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

/* PRUEBA DEL DICCIONARIO, en los dos sentidos.
 *
 * Los dos ficheros de casos NO se escriben a mano: los vierte
 * `scripts/habilidades.py` desde `scripts/saber.py`, la misma lista que genera la
 * ayuda de la cara. Aquí se comprueba lo que la tabla promete:
 *
 *   1 · cada frase de CAPA RAZÓN la contesta `Razon` sin red (208 frases). En la
 *       frase de prueba de cada intención se exige además el prefijo: «cuánto es
 *       7 x 8» tiene que empezar por «Es 56», no por cualquier cosa.
 *   2 · cada frase de CASA o NUBE no la reclama `Cerebro` y tampoco la intenta
 *       `Razon`. Su dueño es el modelo; si el teléfono empieza a contestarla con
 *       una regla floja, aquí se ve antes de que la dueña lo oiga.
 *
 * Es la costura que impide que el diccionario sea una lista de deseos: una frase
 * que se cae de `Razon` deja la suite roja, y una respuesta de adorno que se
 * mete en el terreno de la nube también.
 */
public class Prueba5 {

    public static void main(String[] a) throws Exception {
        int fallos = 0;
        int razon = 0, ajenas = 0;

        for (String linea : lineas("/tmp/cort-mente/casos-razon.txt")) {
            String[] partes = linea.split("\\|", -1);
            String frase = partes[0];
            String prefijo = partes.length > 1 ? partes[1] : "";
            razon++;
            String r = Razon.intenta(frase);
            if (r == null) {
                System.out.println("  MAL razon sin respuesta «" + frase + "»");
                fallos++;
            } else if (!prefijo.isEmpty() && !r.startsWith(prefijo)) {
                System.out.println("  MAL razon «" + frase + "» → «" + r
                        + "» (se esperaba que empiece por «" + prefijo + "»)");
                fallos++;
            }
        }
        System.out.println("razon: " + razon + " frases contestadas sin red");

        Context ctx = new Context();
        ctx.assets = new AssetManager(new File("/tmp/cort-mente/assets"));
        Cerebro cerebro = new Cerebro(ctx, new Nube(ctx));
        for (String frase : lineas("/tmp/cort-mente/casos-no-locales.txt")) {
            ajenas++;
            Cerebro.Resultado c = cerebro.procesar(frase);
            if (!"desconocido".equals(c.accion)) {
                System.out.println("  MAL Cerebro reclama «" + frase + "» como " + c.accion);
                fallos++;
            }
            String r = Razon.intenta(frase);
            if (r != null) {
                System.out.println("  MAL Razon contesta «" + frase + "» → «" + r + "»");
                fallos++;
            }
        }
        System.out.println("no-locales: " + ajenas + " frases que se van al modelo");

        System.out.println(fallos == 0 ? "DICCIONARIO OK" : "DICCIONARIO CON " + fallos + " FALLOS");
        System.exit(fallos == 0 ? 0 : 1);
    }

    static List<String> lineas(String ruta) throws Exception {
        List<String> fuera = new ArrayList<>();
        for (String l : Files.readAllLines(Paths.get(ruta), StandardCharsets.UTF_8)) {
            String t = l.trim();
            if (!t.isEmpty() && !t.startsWith("#")) fuera.add(t);
        }
        return fuera;
    }
}
