package com.cort.ia;

/*
 * Elegir entre lo que hay: la canción que pidió, la playlist y el preset.
 *
 * Esta clase es **pura a propósito**: ni `android.*`, ni `Context`, ni JSON. Recibe
 * textos y devuelve un índice; así `Prueba6` la ejecuta en el JDK del portátil, con
 * `java -m jdk.compiler`, y la decisión de «cuál de estas tres se parece más a
 * "after dark"» no se descubre en el bolsillo de la dueña.
 *
 * Las reglas, escritas para que se puedan leer y discutir:
 *
 *   · se pliegan las dos partes igual (minúsculas, sin tildes, sin signos), porque
 *     el reconocedor de voz devuelve «canción» y la biblioteca guarda «Cancion»;
 *   · manda el título exacto, luego el título que empieza por lo pedido, luego el
 *     que lo contiene; después el artista, luego «título + artista», y al final la
 *     frase partida en palabras (todas tienen que aparecer en título, artista o
 *     género). Por debajo de 200 no se elige nada: mejor decir «no la encuentro»
 *     que poner una canción que no era;
 *   · a igualdad de nota gana la primera de la lista, y `Musica.buscar()` ya viene
 *     ordenado por lo más nuevo — así dos versiones del mismo título no bailan.
 */
import java.text.Normalizer;
import java.util.List;
import java.util.Locale;

public final class Elige {

    /** Lo mínimo que hace falta para decidir. Sin URI: eso lo pone quien la usa. */
    public static final class Candidata {
        public final String titulo, artista, genero;

        public Candidata(String titulo, String artista, String genero) {
            this.titulo = titulo == null ? "" : titulo;
            this.artista = artista == null ? "" : artista;
            this.genero = genero == null ? "" : genero;
        }
    }

    private Elige() { }

    /** Minúsculas, sin tildes, sin signos y con un solo espacio entre palabras. */
    public static String pliega(String s) {
        if (s == null) return "";
        String plano = Normalizer.normalize(s.toLowerCase(Locale.ROOT), Normalizer.Form.NFD)
                .replaceAll("\\p{M}+", "");
        return plano.replaceAll("[^a-z0-9]+", " ").trim().replaceAll("\\s+", " ");
    }

    /**
     * El índice de la candidata que mejor casa con `pedida`, o `-1` si ninguna
     * pasa del mínimo. Nunca lanza: una lista nula o vacía es «no hay».
     */
    public static int mejor(String pedida, List<Candidata> lista) {
        if (lista == null || lista.isEmpty()) return -1;
        String q = pliega(pedida);
        if (q.isEmpty()) return -1;
        int mejor = -1, nota = 0;
        for (int i = 0; i < lista.size(); i++) {
            int s = nota(lista.get(i), q);
            if (s > nota) { nota = s; mejor = i; }
        }
        return nota >= 200 ? mejor : -1;
    }

    /** La nota de una candidata frente a una petición ya plegada. */
    static int nota(Candidata c, String q) {
        String t = pliega(c.titulo);
        String a = pliega(c.artista);
        String g = pliega(c.genero);
        if (t.equals(q)) return 1000;
        if (t.startsWith(q)) return 900 - Math.min(90, t.length() - q.length());
        if (t.contains(q)) return 800 - Math.min(90, t.length() - q.length());
        if (a.equals(q)) return 700;
        if ((t + " " + a).contains(q)) return 600;
        String todo = t + " " + a + " " + g;
        boolean todas = true;
        for (String palabra : q.split(" ")) {
            if (palabra.isEmpty()) continue;
            if (!todo.contains(palabra)) { todas = false; break; }
        }
        if (todas) return 400;
        for (String palabra : q.split(" ")) {
            if (palabra.length() < 3) continue;
            if (t.contains(palabra)) return 300;
            if (a.contains(palabra)) return 250;
            if (g.contains(palabra)) return 220;
        }
        return 100;
    }

    /** El índice de la playlist que pidió, o `-1`. Vale el nombre exacto o su trozo. */
    public static int lista(String pedida, List<String> nombres) {
        if (nombres == null || nombres.isEmpty()) return -1;
        String q = pliega(pedida);
        if (q.isEmpty()) return -1;
        int mejor = -1, nota = 0;
        for (int i = 0; i < nombres.size(); i++) {
            String n = pliega(nombres.get(i));
            int s = n.equals(q) ? 100 : n.startsWith(q) ? 80 : n.contains(q) ? 60 : 0;
            if (s > nota) { nota = s; mejor = i; }
        }
        return nota > 0 ? mejor : -1;
    }

    /**
     * El nombre real del preset de este teléfono. Android los nombra en inglés y la
     * dueña los dice en español («clásica», «graves»); aquí se traduce el alias y se
     * busca el que el aparato tenga de verdad. No se inventa un preset que no exista.
     */
    public static int preset(String dicho, List<String> nombres) {
        if (nombres == null || nombres.isEmpty()) return -1;
        String q = aliasPreset(pliega(dicho));
        if (q.isEmpty()) return -1;
        int mejor = -1, nota = 0;
        for (int i = 0; i < nombres.size(); i++) {
            String n = pliega(nombres.get(i));
            int s = n.equals(q) ? 100 : n.startsWith(q) ? 80 : n.contains(q) ? 60 : 0;
            if (s > nota) { nota = s; mejor = i; }
        }
        return nota > 0 ? mejor : -1;
    }

    /** El alias español de un preset al nombre con el que suele venir en Android. */
    static String aliasPreset(String q) {
        switch (q) {
            case "clasica": case "clasico": return "classical";
            case "plana": case "plano": case "flat": return "normal";
            case "bajos": case "graves": case "bass": case "bass boost": return "bass";
            case "agudos": case "treble": return "treble";
            case "voz": case "voces": case "vocal": return "vocal";
            case "baile": case "fiesta": return "dance";
            default: return q;
        }
    }
}
