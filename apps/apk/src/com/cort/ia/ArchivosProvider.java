package com.cort.ia;

/*
 * El mueble de los archivos. Nombre largo para una clase de cinco líneas, y la
 * línea cinco es la que da la cara: desde Android 7 (API 24) regalar un `file://`
 * a otra app está prohibido y revienta con `FileUriExposedException`, así que para
 * «envíame la canción», «pásale el MV a WhatsApp» o «abre este documento» hace
 * falta un `FileProvider` que convierta la ruta en un `content://` con permiso
 * prestado para ese archivo y ese viaje.
 *
 * Está el `CORT-IA-1.1.0.apk` que la dueña tiene en el cajón (authority
 * `com.cort.ia.files`, medido en su manifiesto) y se perdió en la reescritura a
 * Java puro. Se recupera con la MISMA autoridad, que es la que aparece en las
 * direcciones que ya repartió el teléfono: cambiarla rompería a medias los permisos
 * concedidos.
 *
 * Es `android.content.FileProvider` del sistema, no `androidx.core.content.
 * FileProvider`: el primero existe desde API 24 y este APK arranca en API 26, así
 * que no hace falta AndroidX (que aquí no se usa: ni Gradle, ni Kotlin, ni
 * librerías que engorden el dex). Las rutas admitidas viven en
 * `res/xml/archivos.xml`, declaradas en el manifiesto con su `meta-data`; si se
 * pide un archivo fuera de esa lista, `getUriForFile` lanza
 * `IllegalArgumentException` y la cara lo traduce en un «no puedo compartir eso».
 */

import android.content.Context;
import android.net.Uri;

import java.io.File;

public class ArchivosProvider extends android.content.FileProvider {

    /** La autoridad del manifiesto; va en el `content://` que ve la otra app. */
    public static final String AUTORIDAD = "com.cort.ia.files";

    /**
     * Ruta real → `content://com.cort.ia.files/…`. Lanza
     * `IllegalArgumentException` si la ruta no está en `archivos.xml` o si el
     * archivo no existe: quien llama (el puente) lo captura y lo cuenta.
     */
    public static Uri de(Context c, File archivo) {
        return android.content.FileProvider.getUriForFile(c, AUTORIDAD, archivo);
    }
}
