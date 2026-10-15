package dev.sandra.cort;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraManager;
import android.media.AudioManager;
import android.net.Uri;
import android.provider.AlarmClock;
import android.provider.Settings;
import java.io.UnsupportedEncodingException;
import java.net.URLEncoder;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.List;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Las manos de CORT en el teléfono. Recibe un `Cerebro.Resultado` —una acción de
 * la lista cerrada y su resto— y hace **una** de esas cosas, todas con las
 * intenciones públicas de Android, con `AudioManager`, con `CameraManager` o con
 * el `PackageManager` del aparato: sin `Runtime.exec`, sin shell y sin permisos
 * peligrosos, que es la regla 6 del repo respetada en el aparato y no sólo en el
 * portátil.
 *
 * Desde `v0.15.3` la lista cerrada sigue cerrada **y** cubre cualquier app: lo
 * que se abre por nombre no es una cadena que se ejecute, es un componente que
 * devolvió `queryIntentActivities`, filtrado por el `<queries>` del manifiesto.
 *
 * Devuelve la frase que se dice (y que `Voz` lee en voz alta), o `null` cuando
 * no supo: la cara lo aprovecha para proponer aprender, que es el lazo de Hermes
 * portado como idea y no como código.
 */
public class Acciones {
    private static final Pattern HORA = Pattern.compile("(\\d{1,2})\\s*(?::|\\.)\\s*(\\d{2})");
    private static final Pattern HORA_SOLA = Pattern.compile("(\\d{1,2})");
    private static final Pattern DURACION = Pattern.compile(
            "(\\d+)\\s*(hora|horas|minuto|minutos|min|segundo|segundos|s)");
    private static final String[] NUMEROS = {"dos", "tres", "cuatro", "cinco", "seis", "siete",
            "ocho", "nueve", "diez", "once", "doce"};
    private static final Locale ES = Locale.forLanguageTag("es-ES");

    private final Activity actividad;
    private final Recuerdos recuerdos;

    public Acciones(Activity actividad, Recuerdos recuerdos) {
        this.actividad = actividad;
        this.recuerdos = recuerdos;
    }

    public String ejecutar(Cerebro.Resultado r) {
        switch (r.accion) {
            case "hora":
            case "fecha":
            case "listar":
                return rellena(r.plantilla, r);
            case "volumen":
                return volumen(r.param);
            case "abrir":
                return abrir(r.param);
            case "app":
                return app(r.resto);
            case "poner":
                return poner(r.resto);
            case "llamar":
                return llamar(r.resto);
            case "linterna":
                return linterna(r.param);
            case "alarma":
                return alarma(r.resto);
            case "cronometro":
                return cronometro(r.resto);
            case "guardar":
                return recuerdos.guardarFrase(r.resto);
            case "saber":
                return saber(r);
            case "buscar":
                return buscar(r.resto);
            case "decir":
                return vacia(r.plantilla) ? null : r.plantilla;
            default:
                return null;
        }
    }

    private static boolean vacia(String texto) {
        return texto == null || texto.trim().isEmpty();
    }

    /* ------------------------------------------------------------------ volumen */

    /**
     * `adjustStreamVolume` pide `MODIFY_AUDIO_SETTINGS`, que es un permiso
     * **normal**: se concede solo en la instalación y no sale en ningún aviso. Se
     * usa el paso (`ADJUST_RAISE`) en vez de un valor absoluto justamente para no
     * escribir el volumen de la dueña sin querer.
     */
    private String volumen(String direccion) {
        AudioManager audio = (AudioManager) actividad.getSystemService(Context.AUDIO_SERVICE);
        if (audio == null) {
            return "No encontré el control de volumen de este teléfono.";
        }
        if ("silencio".equals(direccion)) {
            audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_MUTE,
                    AudioManager.FLAG_SHOW_UI);
            return "Dejo la música en silencio.";
        }
        if ("maximo".equals(direccion)) {
            int tope = audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
            for (int i = 0; i < 25 && audio.getStreamVolume(AudioManager.STREAM_MUSIC) < tope; i++) {
                audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, AudioManager.ADJUST_RAISE, 0);
            }
            return "Volumen al máximo.";
        }
        int pasos = "subir".equals(direccion) ? 3 : "bajar".equals(direccion) ? 3 : 0;
        if (pasos == 0) {
            return null;
        }
        int subir = "subir".equals(direccion) ? AudioManager.ADJUST_RAISE
                : AudioManager.ADJUST_LOWER;
        for (int i = 0; i < pasos; i++) {
            audio.adjustStreamVolume(AudioManager.STREAM_MUSIC, subir, AudioManager.FLAG_SHOW_UI);
        }
        return "Volumen a " + audio.getStreamVolume(AudioManager.STREAM_MUSIC) + " de "
                + audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC) + ".";
    }

    /* ------------------------------------------------------------------ abrir */

    /**
     * Abrir **lo que Android ya expone** por categoría: navegador, reloj, música,
     * mensajes, marcador, ajustes, teclado y los dos paneles de red. Es la mitad
     * fija del «abre»; la otra mitad —el nombre de cualquier app instalada— vive
     * en `app()`, y las dos juntas son lo que la dueña pidió: «abre Lark player».
     *
     * Sigue sin haber `QUERY_ALL_PACKAGES`: `app()` ve los lanzadores porque el
     * manifiesto declara un `<queries>` con `MAIN`/`LAUNCHER`, que es la forma
     * estrecha y aprobada de preguntar lo mismo.
     */
    private String abrir(String destino) {
        Intent intento = new Intent();
        intento.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        switch (destino) {
            case "ajustes":
                intento.setAction(Settings.ACTION_SETTINGS);
                break;
            case "teclado":
                intento.setAction(Settings.ACTION_INPUT_METHOD_SETTINGS);
                break;
            case "wifi":
                intento.setAction(Settings.ACTION_WIFI_SETTINGS);
                break;
            case "bluetooth":
                intento.setAction(Settings.ACTION_BLUETOOTH_SETTINGS);
                break;
            case "navegador":
                intento.setAction(Intent.ACTION_MAIN);
                intento.addCategory(Intent.CATEGORY_APP_BROWSER);
                break;
            case "reloj":
                // `ACTION_SHOW_ALARMS` es de API 29; el suelo del APK es 26 y el
                // teléfono de la dueña está muy por encima, pero se comprueba
                // igual: un intento que no existe no debe tumbar la cara.
                if (android.os.Build.VERSION.SDK_INT >= 29) {
                    intento.setAction(AlarmClock.ACTION_SHOW_ALARMS);
                } else {
                    intento.setAction(Settings.ACTION_DATE_SETTINGS);
                }
                break;
            case "musica":
                intento.setAction(Intent.ACTION_MAIN);
                intento.addCategory(Intent.CATEGORY_APP_MUSIC);
                break;
            case "mensajeria":
                intento.setAction(Intent.ACTION_MAIN);
                intento.addCategory(Intent.CATEGORY_APP_MESSAGING);
                break;
            case "telefono":
                intento.setAction(Intent.ACTION_DIAL);
                break;
            default:
                return "Puedo abrir ajustes, la red, el navegador, el reloj, la música, los "
                        + "mensajes, el marcador y el teclado. Y si me dices el nombre de una "
                        + "app instalada, la abro también.";
        }
        try {
            actividad.startActivity(intento);
            return "Abriendo " + destino + ".";
        } catch (ActivityNotFoundException noHay) {
            return "Este teléfono no trae una app para " + destino + ".";
        }
    }

    /* ------------------------------------------------------------------ cualquier app */

    /**
     * «Abre Lark player», «abre Spotify»: CORT busca el nombre **entre los
     * lanzadores del teléfono** y arranca la actividad que gana. Es la diferencia
     * entre un menú de ocho categorías y un asistente, y se consigue sin
     * `QUERY_ALL_PACKAGES` —el permiso que Google castiga—: el manifiesto declara
     * un `<queries>` con `MAIN`/`LAUNCHER`, así que `queryIntentActivities` sólo
     * ve iconos de arranque, que es exactamente lo que hace falta y nada más.
     *
     * No hay shell ni comandos: se arma un `Intent` con el componente que el
     * propio sistema devolvió (regla 6 dentro del aparato).
     */
    private String app(String nombre) {
        if (vacia(nombre)) {
            return null;
        }
        PackageManager pm = actividad.getPackageManager();
        if (pm == null) {
            return "Este teléfono no me deja mirar sus aplicaciones.";
        }
        String buscado = Cerebro.normaliza(nombre);
        if (buscado.isEmpty()) {
            return null;
        }
        Intent pregunta = new Intent(Intent.ACTION_MAIN);
        pregunta.addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> vistas = pm.queryIntentActivities(pregunta, 0);
        ResolveInfo mejor = null;
        int puntos = 0;
        for (ResolveInfo vista : vistas) {
            if (vista == null || vista.activityInfo == null
                    || vista.activityInfo.packageName == null
                    || vista.activityInfo.name == null) {
                continue;
            }
            // Abrirse a sí misma no es abrir una app: «abre CORT» ya lo hace el
            // lanzador del sistema, y por el puente de la cara no tiene sentido.
            if (vista.activityInfo.packageName.equals(actividad.getPackageName())) {
                continue;
            }
            int marcado = parecido(pm, vista, buscado);
            if (marcado > puntos) {
                puntos = marcado;
                mejor = vista;
            }
        }
        if (mejor == null) {
            return "No encontré «" + nombre + "» entre las apps de este teléfono. "
                    + "Pruébalo con el nombre exacto que ves en su icono.";
        }
        Intent arranque = new Intent(Intent.ACTION_MAIN);
        arranque.addCategory(Intent.CATEGORY_LAUNCHER);
        arranque.setClassName(mejor.activityInfo.packageName, mejor.activityInfo.name);
        arranque.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        String como_se_llama = mejor.loadLabel(pm).toString();
        try {
            actividad.startActivity(arranque);
            return "Abriendo " + como_se_llama + ".";
        } catch (ActivityNotFoundException noPuede) {
            return "Encontré " + como_se_llama + " pero este teléfono no me deja abrirla.";
        } catch (SecurityException protegida) {
            return "Encontré " + como_se_llama + ", pero está protegida y no puedo abrirla.";
        }
    }

    /**
     * Cuánto se parece una app instalada a lo que la dueña nombró, de 5 (idéntico)
     * a 0 (nada). Se compara **normalizado** —minúsculas, sin tildes— porque el
     * habla llega así y los iconos dicen «Música», «Configuración» o «Ajustes».
     */
    private static int parecido(PackageManager pm, ResolveInfo vista, String buscado) {
        String etiqueta = Cerebro.normaliza(vista.loadLabel(pm).toString());
        if (etiqueta.isEmpty()) {
            return 0;
        }
        if (etiqueta.equals(buscado)) {
            return 5;
        }
        if (etiqueta.startsWith(buscado)) {
            return 4;
        }
        if (buscado.startsWith(etiqueta)) {
            return 3;
        }
        if (etiqueta.contains(buscado)) {
            return 3;
        }
        // Muchas apps se llaman distinto en el icono que en su paquete
        // («ajustes» → `com.android.settings`): el paquete rescata los nombres en
        // inglés que la dueña usa de memoria, como «spotify» o «lark».
        String paquete = Cerebro.normaliza(vista.activityInfo.packageName);
        if (paquete.contains(buscado)) {
            return 2;
        }
        return buscado.contains(etiqueta) ? 1 : 0;
    }

    /* ------------------------------------------------------------------ música y enlaces */

    /**
     * «Pon After dark»: CORT abre **una búsqueda de ese tema en internet**, que es
     * lo máximo que se puede hacer sin meterse dentro de la app de nadie. No hay
     * deep links por aplicación —una tabla de «Spotify = uri:spotify:search:...»
     * se oxida en cuanto el servicio cambia de forma— y sí hay un enlace público
     * que cualquier navegador o reproductor del teléfono sabe abrir.
     *
     * Lo que CORT **no** hace aquí, y se dice en vez de fingirlo: no pulsa el play
     * de una app de terceros, y si el enlace lo abre una app distinta de la que la
     * dueña esperaba, eso se ve en la pantalla del teléfono, no en esta máquina.
     */
    private String poner(String obra) {
        if (vacia(obra)) {
            return null;
        }
        String enlace = "https://www.youtube.com/results?search_query=" + codifica(obra);
        Intent intento = new Intent(Intent.ACTION_VIEW, Uri.parse(enlace))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            actividad.startActivity(intento);
            return "Pongo «" + obra + "»: abro su búsqueda en internet.";
        } catch (ActivityNotFoundException noHayNavegador) {
            return "Nada en este teléfono abre un enlace. Dime «busca " + obra + "».";
        }
    }

    /** `URLEncoder` con el charset por nombre: la variante de `Charset` es de API 29. */
    static String codifica(String texto) {
        try {
            return URLEncoder.encode(texto.trim(), "UTF-8");
        } catch (UnsupportedEncodingException nuncaPasa) {
            return texto.trim().replace(" ", "+");
        }
    }

    /* ------------------------------------------------------------------ llamar */

    /**
     * «Llama a la pediátra»: abre el **marcador** con lo dicho dentro. No marca
     * solo —eso pediría `CALL_PHONE`, un permiso peligroso que esta app no pide—,
     * y no busca agendas: `READ_CONTACTS` tampoco. El dedo de la dueña aprieta
     * «llamar»; CORT deja el número o el nombre en la pantalla.
     */
    private String llamar(String a_quien) {
        if (vacia(a_quien)) {
            return null;
        }
        Intent intento = new Intent(Intent.ACTION_DIAL,
                Uri.fromParts("tel", a_quien.trim(), null))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            actividad.startActivity(intento);
            return "Abro el marcador con «" + a_quien + "». Tú aprietas llamar.";
        } catch (ActivityNotFoundException noHayMarcador) {
            return "Este teléfono no tiene marcador para «" + a_quien + "».";
        }
    }

    /* ------------------------------------------------------------------ linterna */

    /**
     * La linterna por `CameraManager.setTorchMode`, que es API 23 y por tanto
     * está por debajo del suelo de este APK (26): no hace falta comprobar la
     * versión. Pide el permiso de cámara —el mismo que la cara ya pide para
     * enseñar el cuerpo 3D desde el WebView—, y si la dueña no lo ha dado aún,
     * `SecurityException` se contesta en español en vez de tumbar la app.
     */
    private String linterna(String modo) {
        boolean encendida = "enciende".equals(modo);
        CameraManager camara = (CameraManager) actividad
                .getSystemService(Context.CAMERA_SERVICE);
        if (camara == null) {
            return "Este teléfono no tiene linterna controlable.";
        }
        try {
            String[] ids = camara.getCameraIdList();
            if (ids.length == 0) {
                return "No encuentro la cámara que manda la linterna.";
            }
            // La linterna suele estar en la cámara trasera —la id «0» en casi todos
            // los teléfonos—, pero se recorre la lista entera: un
            // `IllegalArgumentException` significa «esta cámara no tiene flash» y no
            // es un fallo, es la siguiente.
            for (String id : ids) {
                try {
                    camara.setTorchMode(id, encendida);
                    return encendida ? "Enciendo la linterna." : "Apago la linterna.";
                } catch (IllegalArgumentException noTorch) {
                    // sin linterna en esta cámara: sigue
                }
            }
            return "Las cámaras de este teléfono no traen linterna.";
        } catch (CameraAccessException noHayAccesso) {
            return "No pude mirar las cámaras del teléfono.";
        } catch (SecurityException faltaPermiso) {
            return "Para la linterna necesito el permiso de cámara: dámelo en ajustes.";
        }
    }


    /* ------------------------------------------------------------------ tiempo */

    private String alarma(String resto) {
        int[] hm = hora(resto);
        if (hm == null) {
            // Mejor preguntar que poner una alarma a las 0:00: un fallo así en un
            // asistente se paga a las siete de la mañana.
            return null;
        }
        Intent intento = new Intent(AlarmClock.ACTION_SET_ALARM)
                .putExtra(AlarmClock.EXTRA_HOUR, hm[0])
                .putExtra(AlarmClock.EXTRA_MINUTES, hm[1])
                .putExtra(AlarmClock.EXTRA_MESSAGE, "CORT")
                .putExtra(AlarmClock.EXTRA_SKIP_UI, true)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            actividad.startActivity(intento);
            return "Alarma puesta a las " + hm[0] + ":"
                    + String.format(Locale.ROOT, "%02d", hm[1]) + ".";
        } catch (ActivityNotFoundException noHayApp) {
            return "No encontré la app de reloj de este teléfono.";
        }
    }

    private String cronometro(String resto) {
        long millis = duracionAMillis(resto);
        // `EXTRA_LENGTH` (entero, **segundos**, de 1 a 86 400) es lo que AOSP
        // define para `ACTION_SET_TIMER`. Aquí llegaron a escribirse
        // `EXTRA_TIME_IN_MILLIS` y `EXTRA_COUNTDOWN`, y los dos **no existen**:
        // dos Runs rojos por confiar en la memoria. La lista de constantes
        // verificadas está en `apps/apk/simbolos-android.json`, generada con
        // `scripts/simbolos_android.py`, y la prueba de esa costura es
        // `test_apk_cerebro.py`.
        int segundos = (int) Math.min(86400L, Math.max(0L, millis / 1000L));
        if (segundos < 1) {
            return null;
        }
        Intent intento = new Intent(AlarmClock.ACTION_SET_TIMER)
                .putExtra(AlarmClock.EXTRA_LENGTH, segundos)
                .putExtra(AlarmClock.EXTRA_MESSAGE, "CORT")
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            actividad.startActivity(intento);
            return "Cronómetro de " + resto + ".";
        } catch (ActivityNotFoundException noHayApp) {
            return "La app de reloj no me dejó abrir el cronómetro.";
        }
    }

    /* ------------------------------------------------------------------ memoria y nube */

    private String buscar(String resto) {
        Intent intento = new Intent(Intent.ACTION_WEB_SEARCH)
                .putExtra("query", resto)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            actividad.startActivity(intento);
            return "Busco «" + resto + "».";
        } catch (ActivityNotFoundException noHayBuscador) {
            return "No hay buscador en este teléfono para «" + resto + "».";
        }
    }

    private String saber(Cerebro.Resultado r) {
        String hallado = "yo".equals(r.param) ? recuerdos.quienSoy() : recuerdos.buscar(r.resto);
        if (hallado == null) {
            return null;   // la cara propone aprender, en vez de inventar
        }
        return vacia(r.plantilla) ? hallado : rellena(r.plantilla, r, hallado);
    }

    /** Sustituye los huecos de la plantilla por lo que se sabe ahora. */
    private String rellena(String plantilla, Cerebro.Resultado r) {
        return rellena(plantilla, r, null);
    }

    /**
     * Sostituye los huecos de la plantilla por lo que se sabe ahora. `valor` es
     * lo que encontro la memoria: la plantilla «Esto sé de {resto}: {valor}»
     * existe para que el tono de la frase se lea en la tabla y no enterrado en
     * el Java, que es lo que estas pruebas vigilan desde `test_apk_cerebro.py`.
     */
    private String rellena(String plantilla, Cerebro.Resultado r, String valor) {
        Calendar hoy = Calendar.getInstance();
        String salida = plantilla == null ? "" : plantilla;
        salida = salida.replace("{hora}", new SimpleDateFormat("H:mm", ES).format(hoy.getTime()));
        salida = salida.replace("{fecha}",
                new SimpleDateFormat("EEEE d 'de' MMMM", ES).format(hoy.getTime()));
        salida = salida.replace("{resto}", r.resto == null ? "" : r.resto);
        salida = salida.replace("{lista}", recuerdos.lista(8));
        salida = salida.replace("{valor}", valor == null ? "" : valor);
        return vacia(salida) ? null : salida;
    }

    /* ------------------------------------------------------------------ parseo puro */

    /** «7:30», «las 8 y media», «siete y cuarto» → {7, 30}. `null` si no hay hora. */
    public static int[] hora(String dicho) {
        if (dicho == null || dicho.trim().isEmpty()) {
            return null;
        }
        Matcher m = HORA.matcher(dicho);
        if (m.find()) {
            int h = entero(m.group(1));
            int mi = entero(m.group(2));
            return (h > 23 || mi > 59) ? null : new int[] {h, mi};
        }
        Matcher suelta = HORA_SOLA.matcher(dicho);
        if (suelta.find()) {
            int h = entero(suelta.group(1));
            return h > 23 ? null : new int[] {h, minutos(dicho)};
        }
        int h = numeroEnLetras(dicho);
        return h > 0 ? new int[] {h, minutos(dicho)} : null;
    }

    private static int minutos(String dicho) {
        return dicho.contains("media") ? 30 : dicho.contains("cuarto") ? 15 : 0;
    }

    /** «5 minutos», «30 segundos», «2 horas» → milisegundos; 0 si no se entiende. */
    public static long duracionAMillis(String dicho) {
        Matcher m = DURACION.matcher(dicho == null ? "" : dicho);
        if (!m.find()) {
            return 0L;
        }
        long n = entero(m.group(1));
        String unidad = m.group(2);
        if (unidad.startsWith("h")) {
            return n * 3600000L;
        }
        if (unidad.startsWith("m")) {
            return n * 60000L;
        }
        return n * 1000L;
    }

    private static int numeroEnLetras(String dicho) {
        for (int i = 0; i < NUMEROS.length; i++) {
            if (dicho.contains(NUMEROS[i])) {
                return i + 2;
            }
        }
        return 0;
    }

    private static int entero(String texto) {
        try {
            return Integer.parseInt(texto);
        } catch (NumberFormatException noEs) {
            return 0;
        }
    }
}
