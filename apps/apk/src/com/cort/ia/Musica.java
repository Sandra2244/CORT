package com.cort.ia;

/*
 * La música que YA está en el teléfono, y lo que CORT sabe de los gustos de la
 * dueña.
 *
 * Sin AndroidX y sin biblioteca de música: se pregunta al `MediaStore` del
 * sistema, que es el índice que mantiene Android cuando cae un archivo nuevo.
 * De ahí salen el título, el artista, el género y la duración sin leer un solo
 * byte del archivo, y la URI con la que `Reproductor` puede sonarlo.
 *
 * Los gustos viven en `SharedPreferences` (una linea por artista y por género,
 * con su cuenta): «me gustan estas» sube puntos, «no me gustan» los baja. Con
 * eso `porGusto()` arma una cola sin que nadie le escriba una lista. Es
 * deliberadamente tonto y transparente: se puede leer y borrar desde el propio
 * teléfono, y no hace falta ningún modelo para ordenar una discoteca.
 *
 * Dicho sin adornos: en Android 13+ hace falta el permiso de leer audio
 * (`READ_MEDIA_AUDIO`), y sin él `buscar()` devuelve la lista vacía con un
 * aviso en vez de fingir que no hay música.
 */

import android.content.ContentResolver;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.provider.MediaStore;
import android.net.Uri;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class Musica {

    private static final int MAX = 400;          // canciones por consulta

    /* ───────────────────────── permisos ─────────────────────────── */

    static boolean puedeLeer(Context c) {
        return tiene(c, "android.permission.READ_MEDIA_AUDIO")
            || tiene(c, android.Manifest.permission.READ_EXTERNAL_STORAGE);
    }

    private static boolean tiene(Context c, String permiso) {
        try {
            return c.checkSelfPermission(permiso) == PackageManager.PERMISSION_GRANTED;
        } catch (Exception e) {
            return false;
        }
    }

    /* ───────────────────────── una pista ────────────────────────── */

    static class Pista {
        String uri, titulo, artista, genero;
        long dur;
        boolean video;

        Reproductor.Pista alReproductor() {
            return new Reproductor.Pista(uri, titulo, artista, genero, dur, video);
        }

        String json() {
            return "{\"uri\":\"" + Reproductor.esc(uri)
                 + "\",\"titulo\":\"" + Reproductor.esc(titulo)
                 + "\",\"artista\":\"" + Reproductor.esc(artista)
                 + "\",\"genero\":\"" + Reproductor.esc(genero)
                 + "\",\"dur\":" + dur + ",\"video\":" + video + "}";
        }
    }

    /* ───────────────── buscar en el índice del sistema ──────────── */

    /**
     * Lista canciones por texto: título, artista o género que contenga `q`.
     * Con `q` vacío devuelve toda la discoteca (hasta `MAX`).
     */
    static List<Pista> buscar(Context c, String q, boolean incluirVideo) {
        List<Pista> salida = new ArrayList<>();
        if (!puedeLeer(c)) return salida;
        String filtro = q == null ? "" : q.trim().toLowerCase();
        buscarEn(c, MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, false, filtro, salida, incluirVideo);
        if (incluirVideo) {
            buscarEn(c, MediaStore.Video.Media.EXTERNAL_CONTENT_URI, true, filtro, salida, true);
        }
        return salida;
    }

    private static void buscarEn(Context c, Uri tabla, boolean video, String filtro,
                                 List<Pista> salida, boolean permiteVideo) {
        if (video && !permiteVideo) return;
        ContentResolver cr = c.getContentResolver();
        String[] columnas = video
            ? new String[] { MediaStore.Video.Media._ID, MediaStore.Video.Media.TITLE,
                             MediaStore.Video.Media.ARTIST, MediaStore.Video.Media.DURATION }
            : new String[] { MediaStore.Audio.Media._ID, MediaStore.Audio.Media.TITLE,
                             MediaStore.Audio.Media.ARTIST, MediaStore.Audio.Media.GENRE,
                             MediaStore.Audio.Media.DURATION };
        String[] argu = null;
        String seleccion = null;
        if (!video) {
            // `IS_MUSIC != 0`: sin ese filtro la discoteca de CORT se llena de
            // tonos de llamada, avisos del sistema y grabaciones de la dictadora,
            // que también viven en la tabla de audio.
            seleccion = MediaStore.Audio.Media.IS_MUSIC + " != 0";
        }
        if (!filtro.isEmpty()) {
            String como = "%" + filtro + "%";
            if (video) {
                seleccion = "(TITLE LIKE ? OR ARTIST LIKE ?)";
                argu = new String[] { como, como };
            } else {
                seleccion = "(TITLE LIKE ? OR ARTIST LIKE ? OR GENRE LIKE ?) AND "
                          + MediaStore.Audio.Media.IS_MUSIC + " != 0";
                argu = new String[] { como, como, como };
            }
        }
        Cursor cur = null;
        try {
            cur = cr.query(tabla, columnas, seleccion, argu, video ? null : "TITLE ASC");
            if (cur == null) return;
            int iId = cur.getColumnIndexOrThrow(video ? MediaStore.Video.Media._ID
                                                     : MediaStore.Audio.Media._ID);
            int iTit = cur.getColumnIndexOrThrow(video ? MediaStore.Video.Media.TITLE
                                                      : MediaStore.Audio.Media.TITLE);
            int iArt = cur.getColumnIndexOrThrow(video ? MediaStore.Video.Media.ARTIST
                                                      : MediaStore.Audio.Media.ARTIST);
            int iGen = video ? -1 : cur.getColumnIndexOrThrow(MediaStore.Audio.Media.GENRE);
            int iDur = cur.getColumnIndexOrThrow(video ? MediaStore.Video.Media.DURATION
                                                      : MediaStore.Audio.Media.DURATION);
            while (cur.moveToNext() && salida.size() < MAX) {
                long id = cur.getLong(iId);
                // Las pistas de vídeo del sistema (clips) no tienen URI de audio:
                // se salta la fila si el índice no devuelve ninguna de las dos.
                if (id <= 0) continue;
                Pista p = new Pista();
                p.uri = (video ? MediaStore.Video.Media.EXTERNAL_CONTENT_URI
                               : MediaStore.Audio.Media.EXTERNAL_CONTENT_URI) + "/" + id;
                p.titulo = texto(cur, iTit);
                p.artista = texto(cur, iArt);
                p.genero = iGen >= 0 ? texto(cur, iGen) : "";
                p.dur = cur.getLong(iDur);
                p.video = video;
                if (!filtro.isEmpty() && !encaja(p, filtro)) continue;
                salida.add(p);
            }
        } catch (Exception e) {
            /* Fabricantes con el índice raro: mejor lista vacía que app cerrada. */
        } finally {
            if (cur != null) try { cur.close(); } catch (Exception ignorado) { }
        }
    }

    private static boolean encaja(Pista p, String filtro) {
        return contiene(p.titulo, filtro) || contiene(p.artista, filtro)
            || contiene(p.genero, filtro);
    }

    private static boolean contiene(String donde, String que) {
        return donde != null && donde.toLowerCase().contains(que);
    }

    private static String texto(Cursor cur, int i) {
        try {
            String s = cur.getString(i);
            return s == null || "<unknown>".equalsIgnoreCase(s) ? "" : s;
        } catch (Exception e) { return ""; }
    }

    static String listaJson(List<Pista> pistas) {
        StringBuilder s = new StringBuilder("[");
        for (int i = 0; i < pistas.size(); i++) {
            if (i > 0) s.append(',');
            s.append(pistas.get(i).json());
        }
        return s.append(']').toString();
    }

    /* ─────────────────────── los gustos, en claro ───────────────── */

    private static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences("cort-musica", Context.MODE_PRIVATE);
    }

    /** «me gustan estas» sube; «quítalas» baja. Se cuenta por artista y por género. */
    static void gustar(Context c, List<Pista> pistas, boolean meGusta) {
        if (pistas == null) return;
        SharedPreferences p = prefs(c);
        SharedPreferences.Editor e = p.edit();
        int peso = meGusta ? 3 : -2;
        for (Pista pista : pistas) {
            if (pista == null) continue;
            sumar(p, e, "a|" + bajo(pista.artista), peso);
            sumar(p, e, "g|" + bajo(pista.genero), peso);
        }
        e.apply();
    }

    private static void sumar(SharedPreferences p, SharedPreferences.Editor e,
                              String clave, int delta) {
        if (clave.length() < 3) return;                 // «a|» vacío
        int nuevo = p.getInt(clave, 0) + delta;
        e.putInt(clave, Math.max(-9, Math.min(9, nuevo)));
    }

    private static String bajo(String s) {
        return s == null ? "" : s.trim().toLowerCase();
    }

    /**
     * Las canciones que mejor encajan con lo que ha oído: puntúa artista +
     * género y ordena de más a menos. Si aún no sabe nada, devuelve las más
     * largas (una discoteca sin gustos todavía).
     */
    static List<Pista> porGusto(Context c, String filtro, int cuantas) {
        List<Pista> todas = buscar(c, filtro, true);
        SharedPreferences p = prefs(c);
        Map<String, Integer> puntos = new HashMap<>();
        for (Pista pista : todas) {
            int s = p.getInt("a|" + bajo(pista.artista), 0) + p.getInt("g|" + bajo(pista.genero), 0);
            puntos.put(pista.uri, s);
        }
        List<Pista> orden = new ArrayList<>(todas);
        final Map<String, Integer> f = puntos;
        java.util.Collections.sort(orden, new Comparator<Pista>() {
            @Override public int compare(Pista x, Pista y) {
                int a = f.containsKey(x.uri) ? f.get(x.uri) : 0;
                int b = f.containsKey(y.uri) ? f.get(y.uri) : 0;
                if (a != b) return b - a;
                return x.titulo.compareToIgnoreCase(y.titulo);
            }
        });
        if (orden.size() > cuantas) return new ArrayList<>(orden.subList(0, cuantas));
        return orden;
    }

    /** El perfil, para que la cara lo lea en voz alta: «te gusta X y Y». */
    static String perfilJson(Context c) {
        Map<String, Integer> top = mayores(c, 'g', 5);
        Map<String, Integer> topA = mayores(c, 'a', 5);
        StringBuilder s = new StringBuilder("{\"generos\":[");
        boolean primero = true;
        for (Map.Entry<String, Integer> en : top.entrySet()) {
            if (!primero) s.append(',');
            primero = false;
            s.append("{\"nombre\":\"").append(Reproductor.esc(en.getKey()))
             .append("\",\"puntos\":").append(en.getValue()).append('}');
        }
        s.append("],\"artistas\":[");
        primero = true;
        for (Map.Entry<String, Integer> en : topA.entrySet()) {
            if (!primero) s.append(',');
            primero = false;
            s.append("{\"nombre\":\"").append(Reproductor.esc(en.getKey()))
             .append("\",\"puntos\":").append(en.getValue()).append('}');
        }
        return s.append("]}").toString();
    }

    private static Map<String, Integer> mayores(Context c, char tipo, int n) {
        Map<String, Integer> todo = nuevos(c, tipo);
        List<Map.Entry<String, Integer>> lista = new ArrayList<>(todo.entrySet());
        lista.sort(new Comparator<Map.Entry<String, Integer>>() {
            @Override public int compare(Map.Entry<String, Integer> x,
                                         Map.Entry<String, Integer> y) {
                return y.getValue() - x.getValue();
            }
        });
        Map<String, Integer> salida = new LinkedHashMap<>();
        for (int i = 0; i < Math.min(n, lista.size()); i++) {
            Map.Entry<String, Integer> en = lista.get(i);
            if (en.getValue() > 0) salida.put(en.getKey(), en.getValue());
        }
        return salida;
    }

    private static Map<String, Integer> nuevos(Context c, char tipo) {
        Map<String, Integer> m = new HashMap<>();
        for (Map.Entry<String, ?> en : prefs(c).getAll().entrySet()) {
            String k = en.getKey();
            if (k.length() > 2 && k.charAt(0) == tipo && k.charAt(1) == '|') {
                Object v = en.getValue();
                m.put(k.substring(2), v instanceof Integer ? (Integer) v : 0);
            }
        }
        return m;
    }

    /* ─────────────────────────── listas ─────────────────────────── */

    /** Guardar una playlist con nombre: son URIs separados por `;`. */
    static void guardaLista(Context c, String nombre, List<String> uris) {
        if (nombre == null || nombre.trim().isEmpty()) return;
        prefs(c).edit().putString("playlist|" + nombre.trim(), String.join(";", uris)).apply();
    }

    static List<String> urisDeLista(Context c, String nombre) {
        String guardado = prefs(c).getString("playlist|" + nombre, null);
        if (guardado == null || guardado.isEmpty()) return new ArrayList<>();
        return new ArrayList<>(Arrays.asList(guardado.split(";")));
    }

    static String listasJson(Context c) {
        StringBuilder s = new StringBuilder("[");
        boolean primero = true;
        for (String k : prefs(c).getAll().keySet()) {
            if (!k.startsWith("playlist|")) continue;
            if (!primero) s.append(',');
            primero = false;
            s.append('"').append(Reproductor.esc(k.substring(9))).append('"');
        }
        return s.append(']').toString();
    }

    /** Convertir URIs guardadas en pistas, buscando en el índice por URI. */
    static List<Pista> porUri(Context c, List<String> uris) {
        List<Pista> todas = buscar(c, "", true);
        List<Pista> salida = new ArrayList<>();
        for (String u : uris) {
            for (Pista p : todas) if (p.uri.equals(u)) { salida.add(p); break; }
        }
        return salida;
    }
}
