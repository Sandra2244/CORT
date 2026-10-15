package dev.sandra.cort;

import android.content.Context;
import android.content.SharedPreferences;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import org.json.JSONObject;

/**
 * El puente **asomado a la red del teléfono**: la única clase del APK que habla con
 * el portátil por HTTP, y la única que abre una conexión hacia la LAN.
 *
 * La división es la misma que en Python, donde `puente.py` es puro y `server.py` es
 * el que lo asoma al mundo: aquí `Puente.java` sabe serializar, deduplicar y fusionar,
 * y este archivo sólo viaja. Con esa separación las pruebas de costura
 * (`services/core/tests/test_apk_manifesta.py`) pueden exigir que la lógica del cuadro
 * siga sin nombrar `java.net`, y que la red siga concentrada en un sitio.
 *
 * Tres decisiones, todas nacidas de cómo se cae un teléfono de verdad:
 *
 * 1. **Bloqueante y fuera del hilo de la interfaz.** Igual que la búsqueda por UDP y
 *    que `Nube.preguntar`: `HttpURLConnection` no tiene tiempo de espera en Android
 *    sin `StrictMode` de por medio, y congelar el anillo por un portátil apagado es
 *    peor que no sincronizar. Quien llama (la cara) mete esto en un `Thread` y
 *    devuelve el aviso con `runOnUiThread`.
 * 2. **Primero se baja, después se sube.** Bajar es lo que le da a CORT datos que le
 *    faltan; subir es lo que la dueña acumula en el aparato. Si el portátil está
 *    apagado a la mitad, lo único perdido es la subida, y se dice.
 * 3. **Nunca un error en silencio.** Cualquier fallo —sin enlace guardado, sin wifi,
 *    el core en otro puerto, 401, 413, un cuadro de otra versión— se devuelve **dicho**
 *    en español por `ultimoFallo()`. Un puente que no avisa es un puente roto.
 *
 * La llave de red (`?token=` del enlace que divulgó el lanzador) se usa para llamar **y
 * se pasa al puente como `llave`**: así ningún recuerdo que la contenga sube ni baja.
 * Es la regla 1 del acuerdo, y es la razón de que este archivo no pueda olvidar ese
 * argumento.
 */
public class Sincroniza {
    private static final int CONEXION_MS = 8000;
    private static final int LECTURA_MS = 20000;

    private final SharedPreferences prefs;
    private final Recuerdos recuerdos;
    private String ultimoFallo = "";

    public Sincroniza(Context contexto, Recuerdos recuerdos) {
        // La misma hoja de preferencias donde el lanzador guarda el enlace que divulgó
        // el UDP o la usuaria pegó (`MainActivity.prefs()`, `"cort"`). Nada nuevo que
        // escribir: si el portátil se encontró solo, el puente ya sabe dónde está.
        this.prefs = contexto.getApplicationContext()
                .getSharedPreferences("cort", Context.MODE_PRIVATE);
        this.recuerdos = recuerdos;
    }

    public String ultimoFallo() {
        return ultimoFallo;
    }

    /** El enlace guardado, o vacío. Sin enlace no hay portátil que llamar. */
    public boolean hayPortatil() {
        return Puente.urlDelPuente(prefs.getString("url", "")) != null;
    }

    /**
     * La ida y la vuelta, en una frase legible para el chip y el registro.
     *
     * Devuelve `null` si algo falló — y entonces `ultimoFallo()` dice qué — porque la
     * cara necesita distinguir «no hay portátil» de «bajaron 12, subieron 3».
     */
    public String sincronizar() {
        ultimoFallo = "";
        String url = Puente.urlDelPuente(prefs.getString("url", ""));
        if (url == null) {
            ultimoFallo = "no sé dónde está tu portátil: busca la red o pega el enlace";
            return null;
        }
        String llave = Puente.tokenDe(url);
        try {
            JSONObject delPortatil = bajar(url, llave);
            int[] bajados = Puente.fusionar(recuerdos, delPortatil, llave);
            JSONObject cuadro = Puente.exportar(recuerdos, llave);
            int subidos = cuadro.optInt("total", 0);
            int ocultados = cuadro.optInt("ocultados", 0);
            JSONObject respuesta = subir(url, cuadro, llave);
            int nuevos = respuesta.optInt("nuevos", 0);
            return "del portátil: " + Puente.recuento(bajados)
                    + " · al portátil: " + nuevos + " nuevos de " + subidos + " que hay aquí"
                    + (ocultados > 0 ? " (" + ocultados + " guardados para sí)" : "");
        } catch (IOException red) {
            // El motivo **dicho**, no «sin internet»: «la llave de red no vale» y «no
            // llego al portátil en el puerto 8765» son frases distintas y la dueña
            // decide con ellas (una es pegar el enlace otra vez, la otra es arrancar CORT).
            String motivo = red.getMessage();
            ultimoFallo = (motivo == null || motivo.trim().isEmpty())
                    ? "el portátil no contestó en el puerto " + Puente.PUERTO_API
                    : motivo;
            return null;
        } catch (Exception cualquierCosa) {
            // `JSONException` (comprobada en Android) entra aquí a propósito: un cuadro
            // de otra versión o un cuerpo que no es JSON es un fallo que hay que decir,
            // no un motivo para cerrar la app.
            ultimoFallo = "el puente no cerró: " + cualquierCosa.getMessage();
            return null;
        }
    }

    /** `GET /memoria/puente?token=…` — el cuadro del portátil, sin tocar disco. */
    private JSONObject bajar(String url, String llave) throws IOException {
        HttpURLConnection conexion = abrir(url, "GET", null, llave);
        int codigo = conexion.getResponseCode();
        String leido = lee(codigo >= 400 ? conexion.getErrorStream() : conexion.getInputStream());
        conexion.disconnect();
        if (codigo == 401 || codigo == 403) {
            throw new IOException("la llave de red no vale para este portátil");
        }
        if (codigo >= 400) {
            throw new IOException("el core contestó " + codigo);
        }
        return cuadro(leido);
    }

    /** `POST /memoria/puente?token=…` — y el recuento del portátil en la respuesta. */
    private JSONObject subir(String url, JSONObject cuadro, String llave) throws IOException {
        byte[] cuerpo = cuadro.toString().getBytes(StandardCharsets.UTF_8);
        if (cuerpo.length > Puente.MAX_BYTES) {
            // No puede pasar con `exportar` contando los bytes por delante, pero si
            // algún día el cuadro cambia de forma, mejor decirlo aquí que un 413.
            throw new IOException("el cuadro pesa " + cuerpo.length + " bytes, y el tope es "
                    + Puente.MAX_BYTES);
        }
        HttpURLConnection conexion = abrir(url, "POST", cuadro.toString(), llave);
        int codigo = conexion.getResponseCode();
        String leido = lee(codigo >= 400 ? conexion.getErrorStream() : conexion.getInputStream());
        conexion.disconnect();
        if (codigo == 401 || codigo == 403) {
            throw new IOException("la llave de red no vale para este portátil");
        }
        if (codigo >= 400) {
            throw new IOException("el core contestó " + codigo + " " + leido);
        }
        return cuadro(leido);
    }

    /**
     * La conexión, con la llave **en el query** y no en una cabecera: el core pide
     * `?token=` en estas dos rutas por el mismo motivo por el que lo pide en el
     * WebSocket y en `/avatars/{nombre}`, y `security.py` sólo mira esa forma.
     */
    private HttpURLConnection abrir(String url, String metodo, String cuerpo, String llave)
            throws IOException {
        HttpURLConnection conexion = (HttpURLConnection) new URL(url).openConnection();
        conexion.setConnectTimeout(CONEXION_MS);
        conexion.setReadTimeout(LECTURA_MS);
        conexion.setRequestMethod(metodo);
        conexion.setRequestProperty("Accept", "application/json");
        if (cuerpo == null) {
            conexion.connect();
            return conexion;
        }
        conexion.setRequestProperty("Content-Type", "application/json");
        conexion.setDoOutput(true);
        byte[] bytes = cuerpo.getBytes(StandardCharsets.UTF_8);
        // `fixedLengthMode` en vez de `chunked`: un servidor que no acepta troceado
        // corta el POST, y aquí el cuerpo ya está entero en memoria.
        conexion.setFixedLengthStreamingMode(bytes.length);
        OutputStream salida = conexion.getOutputStream();
        try {
            salida.write(bytes);
        } finally {
            salida.close();
        }
        return conexion;
    }

    /** JSON de verdad, o el motivo por el que no lo es. */
    private static JSONObject cuadro(String leido) throws IOException {
        try {
            return new JSONObject(leido);
        } catch (Exception noEsJson) {
            throw new IOException("el otro lado no contestó con un cuadro de memoria");
        }
    }

    private static String lee(InputStream entrada) throws IOException {
        if (entrada == null) {
            return "";
        }
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        byte[] trozo = new byte[4096];
        int n;
        while ((n = entrada.read(trozo)) > 0) {
            buffer.write(trozo, 0, n);
        }
        entrada.close();
        return new String(buffer.toByteArray(), StandardCharsets.UTF_8);
    }
}
