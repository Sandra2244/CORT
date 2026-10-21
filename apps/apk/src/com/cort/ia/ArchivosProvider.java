package com.cort.ia;

/*
 * El mueble de los archivos: el `ContentProvider` que convierte una ruta del disco
 * en un `content://` que otra app puede leer.
 *
 * Por qué existe: desde Android 7 (API 24) regalar un `file://` a otra app está
 * prohibido y revienta con `FileUriExposedException`. Para que «envíame la canción»,
 * «pásale el MV a WhatsApp» o «abre este documento» funcionen hace falta un proveedor
 * con su lista de rutas. El `CORT-IA-1.1.0.apk` que la dueña tiene en el cajón ya lo
 * traía (authority `com.cort.ia.files`, medida en su manifiesto) y se perdió en la
 * reescritura a Java puro: se recupera **con la misma autoridad**, que es la que ya
 * apareció en los permisos concedidos.
 *
 * Por qué está escrito a mano y no con `FileProvider`: el `FileProvider` de AndroidX
 * (`androidx.core.content.FileProvider`) sería la vía fácil, pero aquí no se usa
 * AndroidX ni Kotlin ni librerías —el método de compilación es `aapt2` + `javac` +
 * `d8`, y el `android.content.FileProvider` que uno cree que es del sistema **no
 * existe**: `javac` lo demuestra («cannot find symbol: class FileProvider»). Lo que
 * sí es del sistema es la clase base, `android.content.ContentProvider`, y cinco
 * métodos. La lista de rutas sigue siendo la de `res/xml/archivos.xml` —se lee de
 * ahí en tiempo de ejecución, con `XmlResourceParser`—, así que el XML y el código
 * no se pueden separar: cambiar una carpeta en el manifiesto cambia lo que este
 * proveedor deja abrir.
 *
 * La puerta es estrecha a propósito: `exported="false"`, la lectura se concede
 * archivo por archivo con `FLAG_GRANT_READ_URI_PERMISSION`, `Android/` (los datos de
 * otras apps) queda fuera aunque el XML liste la raíz del almacenamiento público, y
 * si la lista no se puede leer **no se permite nada** (fallar cerrado, no abierto).
 */

import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.Context;
import android.content.res.Resources;
import android.content.res.XmlResourceParser;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.Environment;
import android.os.ParcelFileDescriptor;
import android.provider.MediaStore;
import android.webkit.MimeTypeMap;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class ArchivosProvider extends ContentProvider {

    /** La autoridad del manifiesto; va en el `content://` que ve la otra app. */
    public static final String AUTORIDAD = "com.cort.ia.files";

    /** El tramo fijo de la ruta: `content://com.cort.ia.files/ficheros/<ruta>`. */
    private static final String TRAMO = "ficheros";

    private Context app;
    private volatile List<File> raices;

    /* ────────────────────────── la parte estática ────────────────────────── */

    /**
     * Ruta real → `content://com.cort.ia.files/…`. Lanza
     * `IllegalArgumentException` si la ruta no está en `archivos.xml` o si el
     * archivo no existe: quien llama (`CortNative.comparte`) lo captura y lo cuenta
     * con palabras, en vez de mandar un `file://` que Android cortaría.
     */
    public static Uri de(Context c, File archivo) {
        if (c == null || archivo == null) {
            throw new IllegalArgumentException("no hay archivo que enviar");
        }
        if (!archivo.isFile()) {
            throw new IllegalArgumentException("eso no es un archivo: " + archivo);
        }
        ArchivosProvider espejo = new ArchivosProvider();
        espejo.app = c.getApplicationContext();
        if (!espejo.dentroDeLoPermitido(archivo)) {
            throw new IllegalArgumentException(
                    "esa ruta no está en la lista de archivos que CORT puede enseñar");
        }
        // `appendPath` escapa los `/` del camino: queda un solo segmento, que es lo
        // que Android entiende y lo que `caminoDe()` vuelve a destapar.
        return new Uri.Builder().scheme("content").authority(AUTORIDAD)
                .appendPath(TRAMO).appendPath(archivo.getAbsolutePath()).build();
    }

    /* ─────────────────────────── el proveedor ─────────────────────────── */

    @Override
    public boolean onCreate() {
        app = getContext().getApplicationContext();
        return true;
    }

    @Override
    public String getType(Uri uri) {
        return mimeDe(caminoDe(uri));
    }

    @Override
    public ParcelFileDescriptor openFile(Uri uri, String modo) throws FileNotFoundException {
        String camino = caminoDe(uri);
        if (camino == null) throw new FileNotFoundException("no entiendo esa dirección de CORT");
        File archivo = new File(camino);
        // Sólo lectura: el `mode` que manda la otra app («w», «rw») se ignora a
        // propósito. CORT enseña sus archivos, no deja que otra app los pise.
        if (!dentroDeLoPermitido(archivo)) {
            throw new FileNotFoundException("ese archivo no está entre los que CORT puede compartir");
        }
        if (!archivo.isFile()) throw new FileNotFoundException("no es un archivo: " + camino);
        return ParcelFileDescriptor.open(archivo, ParcelFileDescriptor.MODE_READ_ONLY);
    }

    /**
     * Muchas apps receptoras (el correo, el propio selector de Android) preguntan
     * el nombre y el tamaño antes de aceptar nada: sin estas dos columnas el envío
     * sale con un nombre raro o se corta. Es la misma consulta que responde el
     * índice de medios, así que la cara puede usar `OpenableColumns` con las dos
     * procedencias.
     */
    @Override
    public Cursor query(Uri uri, String[] proyeccion, String seleccion,
                        String[] args, String orden) {
        String camino = caminoDe(uri);
        File archivo = camino == null ? null : new File(camino);
        MatrixCursor salida = new MatrixCursor(
                new String[] { MediaStore.MediaColumns.DISPLAY_NAME, MediaStore.MediaColumns.SIZE });
        if (archivo != null && archivo.isFile() && dentroDeLoPermitido(archivo)) {
            salida.newRow().add(archivo.getName()).add(archivo.length());
        }
        return salida;
    }

    /** Aquí no se escribe: el proveedor sólo deja mirar. */
    @Override
    public Uri insert(Uri uri, ContentValues valores) { return null; }

    @Override
    public int delete(Uri uri, String seleccion, String[] args) { return 0; }

    @Override
    public int update(Uri uri, ContentValues valores, String seleccion, String[] args) { return 0; }

    /* ─────────────────────────── lo que se permite ─────────────────────── */

    /** El camino del disco que esconde ese `content://`, o `null` si no es de CORT. */
    private static String caminoDe(Uri uri) {
        if (uri == null || !AUTORIDAD.equals(uri.getAuthority())) return null;
        List<String> tramos = uri.getPathSegments();
        if (tramos.size() != 2 || !TRAMO.equals(tramos.get(0))) return null;
        return tramos.get(1);
    }

    /** La lista de `res/xml/archivos.xml`, leída una vez y guardada. */
    private List<File> raices() {
        List<File> guardadas = raices;
        if (guardadas != null) return guardadas;
        List<File> nuevas = new ArrayList<>();
        try {
            Resources res = app.getResources();
            int id = res.getIdentifier("archivos", "xml", app.getPackageName());
            if (id != 0) {
                XmlResourceParser xml = res.getXml(id);
                try {
                    for (int evento = xml.next(); evento != org.xmlpull.v1.XmlPullParser.END_DOCUMENT;
                             evento = xml.next()) {
                        if (evento != org.xmlpull.v1.XmlPullParser.START_TAG) continue;
                        File base = raizDe(xml.getName());
                        if (base == null) continue;
                        String sub = xml.getAttributeValue(null, "path");
                        if (sub == null) sub = "";
                        sub = sub.replace("/", File.separator);
                        if (sub.isEmpty() || ".".equals(sub)) nuevas.add(base);
                        else nuevas.add(new File(base, sub));
                    }
                } finally {
                    xml.close();
                }
            }
        } catch (Exception elXmlNoSeLee) {
            // Sin lista no hay permisos: `nuevas` queda como vaya, y si está vacía
            // `dentroDeLoPermitido` no deja pasar nada. Fallar cerrado.
            nuevas.clear();
        }
        raices = nuevas;
        return nuevas;
    }

    /** Las cinco etiquetas que usa el XML del proyecto, traducidas a su raíz real. */
    private File raizDe(String etiqueta) {
        if ("external-path".equals(etiqueta)) return Environment.getExternalStorageDirectory();
        if ("external-cache-path".equals(etiqueta)) return app.getExternalCacheDir();
        if ("external-files-path".equals(etiqueta)) return app.getExternalFilesDir(null);
        if ("cache-path".equals(etiqueta)) return app.getCacheDir();
        if ("files-path".equals(etiqueta)) return app.getFilesDir();
        return null;                      // `root-path` etc.: no hace falta aquí
    }

    /** Si ese archivo puede salir del teléfono con CORT. */
    private boolean dentroDeLoPermitido(File archivo) {
        try {
            String ruta = archivo.getCanonicalPath();
            // El XML lista la raíz pública («.»), que de otra forma abriría también
            // `Android/`: los datos privados de otras apps. Ésa es la línea que no
            // se pasa, y se corta aquí, en el código, no sólo en el comentario.
            if (ruta.contains(File.separator + "Android" + File.separator)) return false;
            for (File raiz : raices()) {
                if (raiz == null) continue;
                String caminoRaiz = raiz.getCanonicalPath();
                if (ruta.equals(caminoRaiz) || ruta.startsWith(caminoRaiz + File.separator)) return true;
            }
        } catch (IOException elCaminoNoSePuedeLeer) {
            return false;
        } catch (Exception loQueSea) {
            return false;
        }
        return false;
    }

    /** `canción.mp3` → `audio/mpeg`, y `application/octet-stream` si no se pilla. */
    private static String mimeDe(String camino) {
        String extension = camino == null ? "" :
                MimeTypeMap.getFileExtensionFromUrl(Uri.fromFile(new File(camino)).toString());
        if (extension != null && !extension.isEmpty()) {
            String dicho = MimeTypeMap.getSingleton()
                    .getMimeTypeFromExtension(extension.toLowerCase(Locale.US));
            if (dicho != null) return dicho;
        }
        return "application/octet-stream";
    }
}
