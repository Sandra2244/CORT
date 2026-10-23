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

    /* Los dos topes van **separados** a propósito, y el motivo es una medida de su
     * teléfono del 2026-10-22: con `MAX = 400` para todo, `buscar()` llenaba la lista
     * de audio hasta 400 y la llamada de vídeos entraba después con el cupo ya
     * agotado (`while (cur.moveToNext() && salida.size() < MAX)`). Resultado: la
     * pestaña «Vídeos» de la cara salía vacía con 1786 vídeos delante. Un tope por
     * tipo de medio, y uno por consulta. */
    private static final int MAX = 800;           // canciones por consulta
    private static final int MAX_VIDEO = 400;     // vídeos por consulta

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
        String uri, titulo, artista, genero, album;
        long dur, id, fecha;         // `fecha` = DATE_ADDED en segundos: «Más recientes»
        boolean video, letra, mv;

        Reproductor.Pista alReproductor() {
            return new Reproductor.Pista(uri, titulo, artista, genero, dur, video);
        }

        String json() {
            return "{\"uri\":\"" + Reproductor.esc(uri)
                 + "\",\"titulo\":\"" + Reproductor.esc(titulo)
                 + "\",\"artista\":\"" + Reproductor.esc(artista)
                 + "\",\"genero\":\"" + Reproductor.esc(genero)
                 + "\",\"album\":\"" + Reproductor.esc(album)
                 + "\",\"dur\":" + dur + ",\"id\":" + id + ",\"fecha\":" + fecha
                 + ",\"video\":" + video + ",\"letra\":" + letra + ",\"mv\":" + mv + "}";
        }
    }

    /* ───────────────── buscar en el índice del sistema ──────────── */

    /**
     * Lista canciones por texto: título, artista, álbum o género que contenga `q`.
     * Con `q` vacío devuelve toda la discoteca (hasta `MAX`, y `MAX_VIDEO` de vídeos).
     *
     * Dos cosas que antes no se hacían y salieron caras en su teléfono:
     *
     * 1. **El filtro se aplica aquí, en Java, plegado; no en el SQL.** Con
     *    `TITLE LIKE ?` SQLite sólo ignora las mayúsculas del ASCII: «marshmello»
     *    contra «Marshmello» acierta, pero una búsqueda con acentos o con la ñ se cae,
     *    y la fila ni siquiera llega al filtro fino de `encaja()`. Por eso «el buscador
     *    no funciona bien».
     * 2. **Cada medio tiene su tope.** Antes compartían `MAX`, el audio se lo comía
     *    entero y la pestaña de vídeos salía vacía con 1786 vídeos delante.
     *
     * El orden de consulta es `DATE_ADDED DESC` (lo más nuevo primero), que es como
     * abre Lark: con un tope por delante, ordenar por título dejaba fuera justo lo que
     * la dueña acaba de bajar.
     */
    static List<Pista> buscar(Context c, String q, boolean incluirVideo) {
        List<Pista> salida = new ArrayList<>();
        if (!puedeLeer(c)) return salida;
        String filtro = plegar(q == null ? "" : q.trim());
        List<Pista> audios = new ArrayList<>();
        List<Pista> videos = new ArrayList<>();
        leerEn(c, MediaStore.Audio.Media.EXTERNAL_CONTENT_URI, false, audios, MAX);
        if (incluirVideo) leerEn(c, MediaStore.Video.Media.EXTERNAL_CONTENT_URI, true, videos, MAX_VIDEO);

        // La píldora `MV` de Lark significa «esta canción tiene vídeo». Aquí se saca de
        // verdad: se cruzan los títulos plegados de la biblioteca de vídeo con cada
        // canción. Si no se leyeron vídeos (el modo sólo-audio) la bandera queda falsa,
        // que es la verdad de este aparato en este momento.
        java.util.HashSet<String> deVideo = new java.util.HashSet<>();
        for (Pista v : videos) if (!v.titulo.isEmpty()) deVideo.add(plegar(v.titulo));
        java.util.Set<String> tapadas = ocultas(c);

        for (Pista p : audios) {
            if (tapadas.contains(p.uri)) continue;
            if (!filtro.isEmpty() && !encaja(p, filtro)) continue;
            p.mv = deVideo.contains(plegar(p.titulo));
            salida.add(p);
        }
        for (Pista v : videos) {
            if (tapadas.contains(v.uri)) continue;
            if (!filtro.isEmpty() && !encaja(v, filtro)) continue;
            salida.add(v);
        }
        return salida;
    }

    /** Una pasada del cursor del índice, sin filtro SQL: aquí sólo se lee y se llena. */
    private static void leerEn(Context c, Uri tabla, boolean video,
                               List<Pista> salida, int tope) {
        ContentResolver cr = c.getContentResolver();
        String[] columnas = video
            ? new String[] { MediaStore.Video.Media._ID, MediaStore.Video.Media.TITLE,
                             MediaStore.Video.Media.ARTIST, MediaStore.Video.Media.DURATION,
                             MediaStore.Video.Media.DATE_ADDED, MediaStore.Video.Media.DATA }
            : new String[] { MediaStore.Audio.Media._ID, MediaStore.Audio.Media.TITLE,
                             MediaStore.Audio.Media.ARTIST, MediaStore.Audio.Media.GENRE,
                             MediaStore.Audio.Media.ALBUM, MediaStore.Audio.Media.DURATION,
                             MediaStore.Audio.Media.DATE_ADDED, MediaStore.Audio.Media.LYRICS,
                             MediaStore.Audio.Media.DATA };
        // `IS_MUSIC != 0`: sin ese filtro la discoteca de CORT se llena de tonos de
        // llamada, avisos del sistema y grabaciones de la dictadora, que también viven
        // en la tabla de audio.
        String seleccion = video ? null : MediaStore.Audio.Media.IS_MUSIC + " != 0";
        Cursor cur = null;
        try {
            cur = cr.query(tabla, columnas, seleccion, null,
                           MediaStore.MediaColumns.DATE_ADDED + " DESC");
            if (cur == null) return;
            while (cur.moveToNext() && salida.size() < tope) {
                long id = cur.getLong(0);
                if (id <= 0) continue;
                Pista p = new Pista();
                p.id = id;
                p.uri = tabla + "/" + id;
                p.titulo = texto(cur, 1);
                p.artista = texto(cur, 2);
                p.genero = video ? "" : texto(cur, 3);
                p.album = video ? "" : texto(cur, 4);
                p.dur = cur.getLong(video ? 3 : 5);
                p.fecha = cur.getLong(video ? 4 : 6);
                p.video = video;
                // La píldora `LETRAS` de Lark: sólo si la letra **existe de verdad** en
                // el teléfono — incrustada en la etiqueta LYRICS del archivo, o en un
                // `.lrc` / `.txt` con el mismo nombre al lado.
                String incrustada = video ? "" : texto(cur, 7);
                p.letra = !incrustada.isEmpty()
                    || hayArchivoDeLetra(texto(cur, video ? 5 : 8));
                salida.add(p);
            }
        } catch (Exception e) {
            /* Fabricantes con el índice raro: mejor lista vacía que app cerrada. */
        } finally {
            if (cur != null) try { cur.close(); } catch (Exception ignorado) { }
        }
    }

    /** ¿Hay `.lrc` o `.txt` hermano de esta ruta? Sin ruta (almacén con puntero raro,
     *  Android 13 sin `DATA`) dice que no, que es lo que se sabe. */
    private static boolean hayArchivoDeLetra(String ruta) {
        if (ruta == null || ruta.isEmpty()) return false;
        int punto = ruta.lastIndexOf('.');
        String base = punto > 0 ? ruta.substring(0, punto) : ruta;
        try {
            return new java.io.File(base + ".lrc").isFile()
                || new java.io.File(base + ".txt").isFile();
        } catch (Exception eseArchivoNoSePuedeMirar) {
            return false;
        }
    }

    private static boolean encaja(Pista p, String filtro) {
        return contiene(p.titulo, filtro) || contiene(p.artista, filtro)
            || contiene(p.genero, filtro) || contiene(p.album, filtro);
    }

    private static boolean contiene(String donde, String que) {
        return donde != null && plegar(donde).contains(que);
    }

    /**
     * Minúsculas y sin acentos, para comparar como compara Lark. Es la pieza que
     * faltaba: `toLowerCase()` a secas deja «Canción» y «cancion» como dos mundos.
     */
    static String plegar(String s) {
        if (s == null) return "";
        String bajo = s.toLowerCase(java.util.Locale.ROOT);
        char[] buf = bajo.toCharArray();
        for (int i = 0; i < buf.length; i++) {
            switch (buf[i]) {
                case 'á': case 'à': case 'ä': case 'â': case 'ã': buf[i] = 'a'; break;
                case 'é': case 'è': case 'ë': case 'ê': buf[i] = 'e'; break;
                case 'í': case 'ì': case 'ï': case 'î': buf[i] = 'i'; break;
                case 'ó': case 'ò': case 'ö': case 'ô': case 'õ': buf[i] = 'o'; break;
                case 'ú': case 'ù': case 'ü': case 'û': buf[i] = 'u'; break;
                case 'ñ': buf[i] = 'n'; break;
                case 'ç': buf[i] = 'c'; break;
                default: break;
            }
        }
        return new String(buf);
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

    /* ───────────────────────── ocultar pistas ──────────────────────
     *
     * «Ocultar» es la fila que Lark tiene bajo el ojo tachado: la pista deja de
     * aparecer en la lista, pero **el archivo no se toca**. Es lo que la dueña
     * necesita con una biblioteca de 1786 vídeos llena de tonterías bajadas de
     * SnapTube, y es lo contrario de «Borrar», que CORT **no** ofrece: borrar el
     * archivo de alguien sin red de seguridad no es una función, es un accidente.
     * Se guarda la URI en las mismas preferencias de siempre, con prefijo. */

    static void oculta(Context c, String uri) {
        if (uri == null || uri.isEmpty()) return;
        prefs(c).edit().putString("oculta|" + uri, "1").apply();
    }

    static java.util.Set<String> ocultas(Context c) {
        java.util.Set<String> salida = new java.util.HashSet<>();
        for (String k : prefs(c).getAll().keySet()) {
            if (k.startsWith("oculta|")) salida.add(k.substring(7));
        }
        return salida;
    }

    static void muestraTodas(Context c) {
        SharedPreferences.Editor e = prefs(c).edit();
        for (String k : ocultas(c)) e.remove("oculta|" + k);
        e.apply();
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

    /** Convertir URIs guardadas en pistas, leyendo cada una **por su URI**.
     *
     *  Antes esta función escaneaba la discoteca entera (`buscar(c, "", true)`) y
     *  buscaba el texto de la URI entre lo que cupiera en `MAX`. Con el tope de 400
     *  compartido, las URI de vídeo no estaban nunca: `musicaPoner` recibía `[]`,
     *  devolvía `false` (`CortNative.java:1077`) y **pulsar un vídeo no hacía nada**.
     *  Ahora se pregunta al índice por esa URI concreta, que es lo que MediaStore
     *  sabe hacer bien. */
    static List<Pista> porUri(Context c, List<String> uris) {
        List<Pista> salida = new ArrayList<>();
        if (uris == null) return salida;
        for (String u : uris) {
            Pista p = unaPorUri(c, u);
            if (p != null) salida.add(p);
        }
        return salida;
    }

    private static Pista unaPorUri(Context c, String u) {
        if (u == null || u.isEmpty()) return null;
        Cursor cur = null;
        try {
            // `null` en las columnas = todas: una URI de audio y una de vídeo no
            // comparten GENRE / ALBUM / LYRICS, y pedir una que no existe revienta.
            cur = c.getContentResolver().query(Uri.parse(u), null, null, null, null);
            if (cur == null || !cur.moveToFirst()) return null;
            Pista p = new Pista();
            p.uri = u;
            p.video = u.startsWith(MediaStore.Video.Media.EXTERNAL_CONTENT_URI.toString());
            p.id = largo(cur, MediaStore.MediaColumns._ID);
            p.titulo = textoDe(cur, MediaStore.MediaColumns.TITLE);
            p.artista = textoDe(cur, MediaStore.MediaColumns.ARTIST);
            p.genero = p.video ? "" : textoDe(cur, MediaStore.Audio.Media.GENRE);
            p.album = p.video ? "" : textoDe(cur, MediaStore.Audio.Media.ALBUM);
            p.dur = largo(cur, MediaStore.MediaColumns.DURATION);
            p.fecha = largo(cur, MediaStore.MediaColumns.DATE_ADDED);
            p.letra = !p.video && !textoDe(cur, MediaStore.Audio.Media.LYRICS).isEmpty();
            return p;
        } catch (Exception esaUriYaNoEstá) {
            return null;                      // borrada, o de otra app que ya no está
        } finally {
            if (cur != null) try { cur.close(); } catch (Exception ignorado) { }
        }
    }

    /* ─────────────────────────── la carátula ───────────────────────────
     *
     * Lo que Lark enseña en cada fila y CORT **no tenía**: en todo el repo no había
     * una sola línea que pidiera una portada (`Musica.Pista.json()` devolvía
     * uri/titulo/artista/genero/dur/video), así que la cara pintaba el glifo `♪` y
     * se lo decía a la dueña en un comentario. «No se ven las carátulas» no era un
     * fallo de permisos: es que nadie las pedía.
     *
     * Se pide al sistema, que ya tiene el miniatura hecho: `loadThumbnail` (API 29
     * en adelante) sirve la carátula incrustada en el MP3 **y** la miniatura del
     * vídeo, sin decodificar el archivo. Para Android 8 y 9 queda la portada del
     * álbum por `ALBUM_ID`. Y si nada funciona devuelve cadena vacía: la cara
     * mantiene el glifo, que es peor que la foto pero no es mentira.
     *
     * Sale en `base64` (`data:image/jpeg`) porque el `WebView` tiene
     * `setAllowFileAccess(false)` (`MainActivity.java:128`): un `file://` de la caché
     * no cargaría, y abrir un proveedor de ficheros para esto es más superficie de la
     * que hace falta. Se llama **por fila visible**, no para las 800 de golpe: una
     * miniatura de 220 px son ~12 KB, y 800 de ellas serían 9 MB de texto cruzando el
     * puente. */
    static String caratula(Context c, String u, int lado) {
        if (u == null || u.isEmpty()) return "";
        int ladoBueno = lado <= 0 ? 220 : Math.min(lado, 512);
        android.graphics.Bitmap bmp = null;
        try {
            Uri uri = Uri.parse(u);
            if (android.os.Build.VERSION.SDK_INT >= 29) {
                try {
                    bmp = c.getContentResolver()
                            .loadThumbnail(uri, new android.util.Size(ladoBueno, ladoBueno), null);
                } catch (Exception sinMiniaturaDelSistema) {
                    bmp = null;               // sin carátula incrustada: se intenta el álbum
                }
            }
            if (bmp == null) bmp = portadaDeAlbum(c, uri, ladoBueno);
            if (bmp == null) return "";
            java.io.ByteArrayOutputStream bytes = new java.io.ByteArrayOutputStream();
            bmp.compress(android.graphics.Bitmap.CompressFormat.JPEG, 72, bytes);
            bmp.recycle();
            return "data:image/jpeg;base64," + android.util.Base64.encodeToString(
                    bytes.toByteArray(), android.util.Base64.NO_WRAP);
        } catch (Exception nadaQuePintar) {
            return "";
        }
    }

    /** La portada del álbum al que pertenece esta pista (el camino de Android 8-9). */
    private static android.graphics.Bitmap portadaDeAlbum(Context c, Uri uri, int lado) {
        if (uri.toString().startsWith(MediaStore.Video.Media.EXTERNAL_CONTENT_URI.toString()))
            return null;                       // un vídeo no tiene álbum
        Cursor cur = null;
        long albumId = 0;
        try {
            cur = c.getContentResolver().query(uri,
                new String[] { MediaStore.Audio.Media.ALBUM_ID }, null, null, null);
            if (cur != null && cur.moveToFirst() && cur.getColumnCount() > 0) albumId = cur.getLong(0);
        } catch (Exception sinColumnaDeAlbum) {
            albumId = 0;
        } finally {
            if (cur != null) try { cur.close(); } catch (Exception ignorado) { }
        }
        if (albumId <= 0) return null;
        java.io.InputStream entrada = null;
        try {
            Uri arte = android.content.ContentUris.withAppendedId(
                Uri.parse("content://media/external/audio/albumart"), albumId);
            entrada = c.getContentResolver().openInputStream(arte);
            if (entrada == null) return null;
            android.graphics.Bitmap bmp = android.graphics.BitmapFactory.decodeStream(entrada);
            return bmp == null ? null : android.graphics.Bitmap.createScaledBitmap(bmp, lado, lado, true);
        } catch (Exception eseTelefonoNoTieneEsaPortada) {
            return null;
        } finally {
            if (entrada != null) try { entrada.close(); } catch (Exception ignorado) { }
        }
    }

    private static String textoDe(Cursor cur, String columna) {
        try {
            int i = cur.getColumnIndex(columna);
            return i < 0 ? "" : texto(cur, i);
        } catch (Exception columnaQueNoEstaba) { return ""; }
    }

    private static long largo(Cursor cur, String columna) {
        try {
            int i = cur.getColumnIndex(columna);
            return i < 0 ? 0 : cur.getLong(i);
        } catch (Exception columnaQueNoEstaba) { return 0; }
    }
}
