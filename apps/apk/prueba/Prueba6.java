package com.cort.ia;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/* F15 · «pon After Dark»: la decisión de CUÁL de las canciones que salen es la
   que suena. `Elige` es Java puro (sin `android.*`, sin JSON), así que se mide
   aquí con el JDK del portátil; `musicaPonerNombre` sólo le pasa los datos y
   obedece el índice.

   Cada comprobación está escrita para poder CAER: si `Elige` eligiera siempre la
   primera, las de «gana el título exacto» y «gana el artista» se pondrían rojas. */
public class Prueba6 {
    static int fallos = 0, casos = 0;

    static void check(String que, boolean vale, String detalle) {
        casos++;
        if (vale) System.out.println("ok     " + que);
        else { fallos++; System.out.println("FALLO  " + que + "   (" + detalle + ")"); }
    }

    static List<Elige.Candidata> lista(String... filas) {
        List<Elige.Candidata> c = new ArrayList<>();
        for (String f : filas) {
            String[] p = f.split("\\|", -1);
            c.add(new Elige.Candidata(p.length > 0 ? p[0] : "",
                                      p.length > 1 ? p[1] : "",
                                      p.length > 2 ? p[2] : ""));
        }
        return c;
    }

    static String elige(String pedida, List<Elige.Candidata> l) {
        int i = Elige.mejor(pedida, l);
        return i < 0 ? "—" : l.get(i).titulo + " · " + l.get(i).artista;
    }

    public static void main(String[] args) {
        List<Elige.Candidata> biblioteca = lista(
            "After Dark|Mr. Kitty|synthpop",
            "After Dark (Remix)|Mr. Kitty|synthpop",
            "Dark Horse|Katy Perry|pop",
            "Canción de cuna|Ana|acústico",
            "El Horizonte de Sucesos|Nube|rock");

        // 1 · el título exacto gana a la versión remix, aunque el remix sea más nuevo
        check("el título exacto gana", elige("After Dark", biblioteca).startsWith("After Dark ·"),
              elige("After Dark", biblioteca));

        // 2 · da igual decir «after dark» sin tildes ni mayúsculas
        check("sin tildes ni mayúsculas", elige("AFTER DARK", biblioteca).startsWith("After Dark ·"),
              elige("AFTER DARK", biblioteca));

        // 3 · «canción de cuna» con tilde encuentra «Cancion de cuna»
        List<Elige.Candidata> cuna = lista("Cancion de cuna|Ana|acustico");
        check("la tilde no separa", elige("canción de cuna", cuna).startsWith("Cancion de cuna"),
              elige("canción de cuna", cuna));

        // 4 · el artista también sirve de petición
        check("por artista", elige("mr kitty", biblioteca).startsWith("After Dark ·"),
              elige("mr kitty", biblioteca));

        // 5 · la frase partida en palabras, en cualquier orden
        check("por palabras sueltas", elige("horizonte sucesos", biblioteca)
              .startsWith("El Horizonte de Sucesos"), elige("horizonte sucesos", biblioteca));

        // 6 · lo que no está no se inventa: hay que decir «no la encuentro»
        check("lo que no está se queda en —", elige("un tema que no existe", biblioteca).equals("—"),
              elige("un tema que no existe", biblioteca));

        // 7 · una palabra de menos de 3 letras no elige sola («la», «de», «y»)
        check("una palabra corta no elige", elige("la", biblioteca).equals("—"),
              elige("la", biblioteca));

        // 8 · lista vacía / nula: no revienta y no elige
        check("sin biblioteca no hay elección",
              Elige.mejor("after dark", new ArrayList<Elige.Candidata>()) == -1
              && Elige.mejor("after dark", null) == -1, "lista vacía o nula");

        // 9 · playlists: nombre exacto, trozo y desconocida
        List<String> listas = Arrays.asList("para correr", "Noche de synth", "Trabajo");
        check("la lista exacta", Elige.lista("Trabajo", listas) == 2, "índice " + Elige.lista("Trabajo", listas));
        check("la lista por su trozo", Elige.lista("synth", listas) == 1, "índice " + Elige.lista("synth", listas));
        check("la lista sin tildes", Elige.lista("NOCHE DE SYNTH", listas) == 1,
              "índice " + Elige.lista("NOCHE DE SYNTH", listas));
        check("la lista que no está", Elige.lista("gimnasio", listas) == -1,
              "índice " + Elige.lista("gimnasio", listas));

        // 10 · presets: el alias español encuentra el nombre inglés del aparato
        List<String> presets = Arrays.asList("Normal", "Classical", "Dance", "Rock",
                                             "Bass Boost", "Treble", "Vocal");
        check("«clásica» → Classical", presets.get(Elige.preset("clásica", presets)).equals("Classical"),
              "índice " + Elige.preset("clásica", presets));
        check("«graves» → Bass Boost", presets.get(Elige.preset("graves", presets)).equals("Bass Boost"),
              "índice " + Elige.preset("graves", presets));
        check("«rock» → Rock", presets.get(Elige.preset("rock", presets)).equals("Rock"),
              "índice " + Elige.preset("rock", presets));
        check("«normal» → Normal", presets.get(Elige.preset("normal", presets)).equals("Normal"),
              "índice " + Elige.preset("normal", presets));
        check("un preset que el aparato no trae", Elige.preset("ópera", presets) == -1,
              "índice " + Elige.preset("ópera", presets));
        check("sin presets, ninguno", Elige.preset("rock", new ArrayList<String>()) == -1,
              "lista vacía");

        System.out.println("\n" + (casos - fallos) + "/" + casos + " comprobaciones de Elige; fallos=" + fallos);
        System.exit(fallos == 0 ? 0 : 1);
    }
}
