package dev.sandra.cort.movil;

import android.app.Activity;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioRecord;
import android.media.AudioTrack;
import android.media.MediaRecorder;
import android.os.Bundle;
import android.util.Base64;
import android.view.Gravity;
import android.view.MotionEvent;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Random;
import org.json.JSONObject;

/**
 * El parlamento (F16): hablarle a CORT desde el teléfono y oírla **por el auricular**,
 * con el oído y la boca de la PC.
 *
 * El reparto lo eligió la dueña y es el que se puede defender con números: el móvil no
 * tiene memoria para un cerebro ni para una voz grande (medido el 2026-11-04, el GGUF
 * pesa 718 MB), pero en la PC ya viven Vosk y la síntesis de CORT. Aquí se graba, se
 * sube y se escucha; lo demás ocurre al otro lado del cable, en
 * `cort-bridge/cort_parlamento.py`, que monta la ruta sobre el mismo core de la memoria
 * (`Puente.PUERTO_API`) y despacha la frase por el **mismo** `atender_input` que el
 * WebSocket. No hay un segundo cerebro que pueda irse por su cuenta.
 *
 * Cuatro condiciones que no son adornos y se rompen si se tocan sin medir:
 *
 * 1. **El audio no llega nunca a un archivo.** Se graba en un arreglo de bytes en
 *    memoria, aquí dentro se le escribe la cabecera WAVE y se manda ese mismo arreglo.
 *    Este archivo no abre ni una sola ruta del teléfono: lo que sale de esta pantalla es
 *    el dictado de la dueña, y guardarlo en un aparato que comparte casa no es opción.
 * 2. **16 kHz, un canal, 16 bits.** Es lo único que el oído de la PC acepta al otro
 *    lado: rechaza cualquier WAV que no sea mono de 16 bits, así que un muestreo
 *    distinto no es un matiz, es un parlamento mudo.
 * 3. **Se corta a los 20 segundos.** El portátil topa el cuerpo a 3 MB; 20 s a 16 kHz
 *    mono 16-bit son 640 KB, así que el teléfono siempre llega antes que el techo. Un
 *    dictado más largo se parte en dos vueltas y se avisa, no se tira en silencio.
 * 4. **Se oye por el auricular, no por el altavoz.** `AudioManager.MODE_IN_COMMUNICATION`
 *    enruta la voz de dos vías al receptor de la oreja; si se quedara en el modo que
 *    había, Android sacaría el `AudioTrack` por el altoparlante de atrás y CORT
 *    contestaría en voz alta delante de toda la casa. El modo se **restaura** al terminar
 *    —y se restaura el que había, no uno inventado— porque dejar el teléfono en modo
 *    llamada rompe el altavoz de las llamadas siguientes.
 *
 * El `?token=` viaja en la consulta, con la misma comparación de tiempo constante del
 * enlace, y no se muestra por ninguna parte: ni en un botón, ni en un aviso, ni en el
 * recuento. Sin llave la PC contesta 401 y aquí eso se traduce a «vuelve a escanear el
 * cuadro», porque «error 401» no le dice a la dueña qué tiene que tocar.
 */
public class Parlamento extends Activity {

    /** Lo que escucha el oído de la PC: 16 kHz, un canal, 16 bits con signo. */
    public static final int TASA = 16000;

    /** Techo propio, elegido para quedar muy por debajo de los 3 MB del portátil. */
    private static final int MAX_MS = 20_000;

    /** 3 200 bytes = 1 600 muestras = 100 ms: bastante para no despertar el hilo cada dos por tres. */
    private static final int TROZO = 3200;

    /** `Sincroniza` espera 20 s de lectura; un parlamento tiene escucha + cerebro + voz dentro. */
    private static final int CONEXION_MS = 8000;
    private static final int LECTURA_MS = 45000;

    /** Lo mínimo que merece una respuesta antes de decir «no se oyó nada». */
    private static final int MIN_BYTES = 3200;

    private TextView estado;
    private Button botonHablar;
    private SharedPreferences prefs;
    private AudioManager gestor;

    private volatile boolean grabando;
    private volatile boolean ocupado;
    private volatile boolean cerrado;
    private ByteArrayOutputStream audio = new ByteArrayOutputStream();
    private AudioRecord microfono;
    private AudioTrack pista;
    private int modoAnterior = AudioManager.MODE_NORMAL;
    private String destino = "";

    @Override
    protected void onCreate(Bundle guardado) {
        super.onCreate(guardado);
        prefs = getSharedPreferences("cort", MODE_PRIVATE);
        gestor = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
        getWindow().getDecorView().setBackgroundColor(Paleta.FONDO);

        ScrollView desplazable = new ScrollView(this);
        LinearLayout pantalla = new LinearLayout(this);
        pantalla.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(22);
        pantalla.setPadding(pad, pad, pad, pad);
        desplazable.addView(pantalla, new LinearLayout.LayoutParams(-1, -2));
        setContentView(desplazable);

        TextView titulo = texto("PARLAMENTO · CORT OYE Y HABLA EN LA PC", 13f, Paleta.CIAN);
        titulo.setLetterSpacing(0.12f);
        pantalla.addView(titulo);

        TextView guia = texto(
                "Mantén pulsado y habla. Lo que digas viaja a la PC: allí está el modelo "
                + "de español que transcribe, el cerebro que responde si lo hay, y la voz "
                + "que te contesta al oído.\n\n"
                + "Tu dictado no se guarda en ningún sitio: se arma en memoria y se envía. "
                + "Si sueltas, sale; si te pasas de 20 segundos, se corta ahí y se envía lo "
                + "dicho.",
                15f, Paleta.CLARO);
        guia.setLineSpacing(0f, 1.25f);
        pantalla.addView(guia, conMargen());

        estado = texto("", 15f, Paleta.CLARO);
        estado.setLineSpacing(0f, 1.3f);
        pantalla.addView(estado, conMargen());

        botonHablar = boton("Mantén pulsado para hablar");
        LinearLayout.LayoutParams cajaHablar = new LinearLayout.LayoutParams(-1, dp(64));
        cajaHablar.topMargin = dp(18);
        pantalla.addView(botonHablar, cajaHablar);

        Button cortar = boton("Cortar la conversación");
        cortar.setTextSize(15f);
        LinearLayout.LayoutParams cajaCortar = new LinearLayout.LayoutParams(-1, dp(54));
        cajaCortar.topMargin = dp(10);
        pantalla.addView(cortar, cajaCortar);

        Button volver = boton("Volver");
        volver.setTextColor(Paleta.SUAVE);
        volver.setBackgroundColor(Paleta.FONDO);
        volver.setTextSize(14f);
        pantalla.addView(volver, new LinearLayout.LayoutParams(-1, dp(48)));

        // `ACTION_DOWN` graba y `ACTION_UP` envía: es el único gesto que no obliga a
        // mirar la pantalla para saber si CORT está escuchando.
        botonHablar.setOnTouchListener((v, evento) -> {
            int accion = evento.getActionMasked();
            if (accion == MotionEvent.ACTION_DOWN) {
                empezarAHablar();
                return true;
            }
            if (accion == MotionEvent.ACTION_UP || accion == MotionEvent.ACTION_CANCEL) {
                soltar();
                return true;
            }
            return false;
        });
        cortar.setOnClickListener(v -> cortar());
        volver.setOnClickListener(v -> finish());

        avisarDondeEstaLaPC();
    }

    /**
     * Sin enlace guardado no hay a quién hablarle, y eso se dice antes de que nadie
     * mantenga pulsado nada. Con enlace pero sin llave, igual: desde F14a el parlamento
     * contesta 401 sin token, y un 401 sin traducción es una pantalla que no dice nada.
     */
    private void avisarDondeEstaLaPC() {
        String delParlamento = Puente.urlDelParlamento(prefs.getString("url", ""));
        destino = delParlamento == null ? "" : delParlamento;
        if (destino.isEmpty()) {
            estado.setText("No sé dónde está tu portátil: busca la Wi-Fi o escanea otra vez "
                    + "el cuadro que pinta CORT en la pantalla de la PC.");
            return;
        }
        if (Puente.tokenDe(destino).isEmpty()) {
            estado.setText("El enlace está a medias: sin su llave la PC no te va a oír. "
                    + "Escanea el QR o pega la línea entera del arranque.");
            return;
        }
        estado.setText("Avisada la PC. Mantén pulsado cuando quieras hablarle.");
    }

    /* ------------------------------------------------------------------ grabar */

    private void empezarAHablar() {
        if (grabando || ocupado || cerrado) {
            return;
        }
        if (destino.isEmpty()) {
            avisarDondeEstaLaPC();
            return;
        }
        if (checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{android.Manifest.permission.RECORD_AUDIO}, 44);
            return;
        }
        int minimo = AudioRecord.getMinBufferSize(TASA, AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT);
        if (minimo <= 0) {
            estado.setText("Este teléfono no puede grabar a 16 kHz (el sistema dijo "
                    + minimo + "): no hay de dónde mandarle audio a la PC.");
            return;
        }
        AudioRecord nuevo = null;
        try {
            nuevo = new AudioRecord(MediaRecorder.AudioSource.VOICE_COMMUNICATION, TASA,
                    AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT,
                    Math.max(minimo, TROZO * 4));
        } catch (Exception noHayMicrofono) {
            estado.setText("No pude abrir el micrófono: " + loQueDice(noHayMicrofono));
            return;
        }
        if (nuevo.getState() != AudioRecord.STATE_INITIALIZED) {
            nuevo.release();
            estado.setText("El micrófono no se inicializó: lo tiene ocupado otra app "
                    + "(una llamada, la grabadora). Ciérrala y prueba otra vez.");
            return;
        }
        microfono = nuevo;
        audio = new ByteArrayOutputStream();
        try {
            nuevo.startRecording();
        } catch (Exception seOcup) {
            nuevo.release();
            microfono = null;
            estado.setText("El micrófono se ocupó entre el toque y la grabación: inténtalo de nuevo.");
            return;
        }
        grabando = true;
        botonHablar.setText("Hablando… suelta para enviar");
        estado.setText("Escuchando por tu micrófono, transcribiendo en la PC.");
        new Thread(this::volcar).start();
    }

    @Override
    public void onRequestPermissionsResult(int peticion, String[] permisos, int[] resultados) {
        super.onRequestPermissionsResult(peticion, permisos, resultados);
        if (resultados.length > 0 && resultados[0] == PackageManager.PERMISSION_GRANTED) {
            empezarAHablar();
        } else {
            estado.setText("Sin permiso de micrófono no hay parlamento: la PC no puede oír "
                    + "lo que este teléfono no escucha.");
        }
    }

    /**
     * Copiando bytes mientras el dedo aguante. Sale por las tres salidas posibles —
     * soltar el botón, el corte de 20 s, o irse de la pantalla— y **siempre** entrega el
     * envío: lo grabado no se pierde por un descuido del orden entre hilos.
     */
    private void volcar() {
        byte[] trozo = new byte[TROZO];
        long inicio = System.currentTimeMillis();
        boolean cortada = false;
        AudioRecord microfonoActivo = microfono;
        while (grabando && microfonoActivo != null) {
            int leido = microfonoActivo.read(trozo, 0, trozo.length);
            if (leido > 0) {
                audio.write(trozo, 0, leido);
            }
            if (System.currentTimeMillis() - inicio > MAX_MS) {
                cortada = true;
                break;
            }
        }
        grabando = false;
        final boolean pasoDeCorte = cortada;
        runOnUiThread(() -> enviar(pasoDeCorte));
    }

    private void soltar() {
        if (!grabando) {
            return;
        }
        grabando = false;      // `volcar` cierra el micrófono y hace el envío
        botonHablar.setText("Enviando a la PC…");
    }

    /** Soltando el micrófono ya: si no, el teléfono queda con el aviso de escucha puesto. */
    private void cerrarMicrofono() {
        AudioRecord microfonoAbierto = microfono;
        microfono = null;
        if (microfonoAbierto == null) {
            return;
        }
        try {
            if (microfonoAbierto.getRecordingState() == AudioRecord.RECORDSTATE_RECORDING) {
                microfonoAbierto.stop();
            }
        } catch (Exception yaParado) {
            // ya no grababa; lo que sigue es liberarlo igual
        }
        microfonoAbierto.release();
    }

    /* ------------------------------------------------------------------ enviar */

    private void enviar(boolean cortada) {
        cerrarMicrofono();
        if (cerrado) {
            return;      // la pantalla ya se fue: no hay a quién mostrarle la respuesta
        }
        botonHablar.setText("Mantén pulsado para hablar");
        byte[] pcm = audio.toByteArray();
        audio = new ByteArrayOutputStream();     // el dictado deja de existir en cuanto tiene cabecera
        if (pcm.length < MIN_BYTES) {
            estado.setText("No se oyó nada útil (" + pcm.length + " bytes, menos de un "
                    + "segundo): mantén pulsado mientras hablas y suelta al terminar.");
            return;
        }
        ocupado = true;
        final byte[] wav = construirWav(pcm);
        estado.setText(cortada
                ? "Corté el dictado en 20 s y lo mando igual: si querías decir más, da otra vuelta."
                : "Mandando " + (wav.length / 1024) + " KB a la PC…");
        new Thread(() -> {
            final String[] dicho = llamar(wav);
            runOnUiThread(() -> {
                ocupado = false;
                estado.setText(dicho[0] + (dicho[1].isEmpty() ? "" : "\n\n" + dicho[1]));
            });
        }).start();
    }

    /**
     * La cabecera WAVE de 44 bytes, en memoria y con los enteros en little-endian como
     * pide el formato. Se arma a mano porque no hay forma de que un dictado termine en
     * un archivo del teléfono.
     *
     * Los tamaños no son decorativos: `audioformat`, `canales`, `cuadro` y `bits` son de
     * **16 bits** en la especificación, y `tasa`, `bytes_por_segundo` y las longitudes
     * son de 32. Escrito todo de cuatro bytes, el bloque `fmt ` mide 28 en vez de 16, la
     * cabecera sale de 52 y el oído de la PC —que abre el WAV con `wave`— no lo lee. El
     * espejo `wav_estilo_java` de `scripts/prueba_parlamento.py` compara estos bytes con
     * los que escribe Python, y esa comprobación es la que encontró el fallo.
     */
    static byte[] construirWav(byte[] pcm) {
        ByteArrayOutputStream wav = new ByteArrayOutputStream(pcm.length + 44);
        cuatro(wav, "RIFF");
        entero(wav, 36 + pcm.length);
        cuatro(wav, "WAVE");
        cuatro(wav, "fmt ");
        entero(wav, 16);          // lo que mide este bloque: justo los seis campos de abajo
        dos(wav, 1);              // PCM sin comprimir
        dos(wav, 1);              // un canal
        entero(wav, TASA);        // muestras por segundo
        entero(wav, TASA * 2);    // bytes por segundo (16 bits por muestra)
        dos(wav, 2);              // bytes por muestra
        dos(wav, 16);             // bits por muestra
        cuatro(wav, "data");
        entero(wav, pcm.length);
        wav.write(pcm, 0, pcm.length);
        return wav.toByteArray();
    }

    private static void cuatro(ByteArrayOutputStream salida, String magicos) {
        for (int i = 0; i < 4; i++) {
            salida.write(magicos.charAt(i));
        }
    }

    private static void dos(ByteArrayOutputStream salida, int valor) {
        salida.write(valor & 0xFF);
        salida.write((valor >> 8) & 0xFF);
    }

    private static void entero(ByteArrayOutputStream salida, int valor) {
        salida.write(valor & 0xFF);
        salida.write((valor >> 8) & 0xFF);
        salida.write((valor >> 16) & 0xFF);
        salida.write((valor >> 24) & 0xFF);
    }

    /**
     * Llamando a la PC. Devuelve `{lo que se lee grande, lo que se lee chico}` y no
     * lanza nada: cualquier fallo —sin red, apagado, 401, cuerpo que no es JSON— sale
     * dicho, porque la dueña decide con esas palabras (arrancar CORT, escanear otra vez,
     * o hablar más claro).
     */
    private String[] llamar(byte[] wav) {
        try {
            HttpURLConnection conexion = (HttpURLConnection)
                    new URL(conHilo(destino)).openConnection();
            conexion.setConnectTimeout(CONEXION_MS);
            conexion.setReadTimeout(LECTURA_MS);
            conexion.setRequestMethod("POST");
            conexion.setDoOutput(true);
            conexion.setRequestProperty("Content-Type", "audio/wav");
            conexion.setRequestProperty("Accept", "application/json");
            // Modo de longitud fija: el portátil no acepta troceado y el WAV ya está
            // entero en memoria.
            conexion.setFixedLengthStreamingMode(wav.length);
            OutputStream salida = conexion.getOutputStream();
            try {
                salida.write(wav);
            } finally {
                salida.close();
            }
            int codigo = conexion.getResponseCode();
            String leido = lee(codigo >= 400 ? conexion.getErrorStream() : conexion.getInputStream());
            conexion.disconnect();
            if (codigo == 401 || codigo == 403) {
                return new String[]{"La PC no reconoció tu llave.",
                        "El enlace cambia cuando CORT se reinicia: vuelve a escanear el QR "
                        + "o pega la línea nueva."};
            }
            if (codigo >= 400) {
                return new String[]{"La PC contestó " + codigo + ".", recorta(leido)};
            }
            JSONObject cuadro = new JSONObject(leido);
            if (!cuadro.optBoolean("ok", false)) {
                return new String[]{"La PC no pudo contestarte.",
                        cuadro.optString("motivo", "el oído no devolvió ningún texto")};
            }
            double segundos = cuadro.optDouble("segundos", 0.0);
            String vozBase64 = cuadro.optString("audio", "");
            if (!vozBase64.isEmpty() && segundos > 0.0) {
                hablarPorElAuricular(Base64.decode(vozBase64, Base64.DEFAULT),
                        cuadro.optInt("tasa", 22050));
            }
            String entero = cuadro.optString("respuesta", "(la PC no devolvió texto)");
            String detalle = "Tú: " + cuadro.optString("oido", "") + "\n";
            if (cuadro.optBoolean("auricular_recortado", false)) {
                detalle += "El auricular dijo el principio; el resto está escrito arriba.\n";
            }
            return new String[]{entero, detalle + tiempos(cuadro)};
        } catch (IOException noLlego) {
            return new String[]{"Tu portátil no contestó en el puerto " + Puente.PUERTO_API + ".",
                    "Arranca CORT en la PC con `--lan` y déjalo abierto (la red dijo: "
                    + loQueDice(noLlego) + ")"};
        } catch (Exception cualquierCosa) {
            return new String[]{"El parlamento no cerró.", loQueDice(cualquierCosa)};
        }
    }

    /** La misma conversación a lo largo de varios arranques de esta pantalla. */
    private String hilo() {
        String guardado = prefs.getString("parlamento_hilo", "");
        if (!guardado.isEmpty()) {
            return guardado;
        }
        String nuevo = "movil-" + Long.toString((new Random().nextLong() & Long.MAX_VALUE)
                % 4733162304L, 36);
        prefs.edit().putString("parlamento_hilo", nuevo).apply();
        return nuevo;
    }

    /**
     * El `?hilo=` va detrás del token, que ya trae el `?`. El valor sale de un número
     * pasado a base 36: letra y número, sin `&`, `=` ni espacios que rompan la consulta.
     */
    private String conHilo(String url) {
        return url + (url.contains("?") ? "&" : "?") + "hilo=" + hilo();
    }

    /**
     * Meter un tramo en el **camino** sin romper la consulta. `destino` ya lleva
     * `?token=…` al final, así que concatenar `/colgar` a secas daría
     * `/parlamento?token=x/colgar` y el portátil contestaría 404 con toda la razón.
     */
    private static String conTramo(String url, String tramo) {
        int consulta = url.indexOf('?');
        if (consulta < 0) {
            return url + tramo;
        }
        return url.substring(0, consulta) + tramo + url.substring(consulta);
    }

    /** Cortando por lo sano: el historial de la PC se tira y aquí se olvida el hilo. */
    private void cortar() {
        prefs.edit().remove("parlamento_hilo").apply();
        if (destino.isEmpty()) {
            estado.setText("Conversación cortada aquí. No había portátil a quien avisar.");
            return;
        }
        final String url = conHilo(conTramo(destino, "/colgar"));
        ocupado = true;
        new Thread(() -> {
            final String dicho = avisa(url);
            runOnUiThread(() -> {
                ocupado = false;
                botonHablar.setText("Mantén pulsado para hablar");
                estado.setText(dicho);
            });
        }).start();
    }

    private String avisa(String url) {
        try {
            HttpURLConnection conexion = (HttpURLConnection) new URL(url).openConnection();
            conexion.setConnectTimeout(CONEXION_MS);
            conexion.setReadTimeout(LECTURA_MS);
            conexion.setRequestMethod("POST");
            conexion.setDoOutput(true);
            conexion.setFixedLengthStreamingMode(0);
            int codigo = conexion.getResponseCode();
            String leido = lee(codigo >= 400 ? conexion.getErrorStream() : conexion.getInputStream());
            conexion.disconnect();
            if (codigo >= 400) {
                return "Cortada aquí, pero la PC no lo confirmó (contestó " + codigo + ").";
            }
            JSONObject cuadro = new JSONObject(leido);
            return cuadro.optBoolean("colgada", false)
                    ? "Cortada: la PC ya no tiene esta conversación en memoria."
                    : "Cortada aquí; en la PC no quedaba ninguna conversación con este hilo.";
        } catch (Exception algo) {
            return "Cortada aquí, pero no pude avisar a la PC (" + loQueDice(algo) + ").";
        }
    }

    /* ------------------------------------------------------------------ oir */

    /**
     * Reproduciendo por el auricular. Se puede llamar desde el hilo de red —así llega de
     * `llamar`—: `AudioTrack` no exige el hilo de la interfaz, y copiar la pista entera
     * ahí dentro congelaría la pantalla.
     */
    private void hablarPorElAuricular(byte[] pcm, int tasa) {
        if (cerrado || pcm.length < 2) {
            return;      // una respuesta que llega tarde no le habla a una pantalla que ya fue
        }
        modoAnterior = gestor.getMode();
        // El modo de comunicación es lo que manda la voz de dos vías al receptor de la
        // oreja. Sin esto Android saca por el altavoz trasero y CORT contesta en voz alta.
        gestor.setMode(AudioManager.MODE_IN_COMMUNICATION);
        estadoDesdeHilo("CORT te habla por el auricular…");
        int minimo = AudioTrack.getMinBufferSize(tasa, AudioFormat.CHANNEL_OUT_MONO,
                AudioFormat.ENCODING_PCM_16BIT);
        if (minimo <= 0) {
            gestor.setMode(modoAnterior);
            estadoDesdeHilo("La PC te contestó por escrito: el auricular no acepta "
                    + tasa + " Hz en este teléfono.");
            return;
        }
        AudioTrack nueva = new AudioTrack(gestor, tasa, AudioFormat.CHANNEL_OUT_MONO,
                AudioFormat.ENCODING_PCM_16BIT, Math.max(minimo, pcm.length),
                AudioTrack.MODE_STATIC);
        if (nueva.getState() != AudioTrack.STATE_INITIALIZED) {
            nueva.release();
            gestor.setMode(modoAnterior);
            estadoDesdeHilo("La PC te contestó por escrito: no pude abrir el auricular.");
            return;
        }
        pista = nueva;
        try {
            nueva.write(pcm, 0, pcm.length);
            nueva.setNotificationMarkerPosition(pcm.length / 2);   // en muestras, no en bytes
            nueva.setPlaybackPositionUpdateListener(new AudioTrack.OnPlaybackPositionUpdateListener() {
                @Override public void onMarkerReached(AudioTrack track) {
                    terminarAuricular();
                }

                @Override public void onPeriodicNotification(AudioTrack track) {
                }
            });
            nueva.play();
        } catch (Exception seFue) {
            terminarAuricular();
        }
    }

    /**
     * Soltando la pista y devolviendo el modo de audio que había antes de hablar.
     *
     * Se llama desde el hilo del marcador de reproducción (no es el de la interfaz) y
     * también desde `onPause`, así que los dos textos van dentro de `runOnUiThread`:
     * tocar un `View` desde otro hilo termina en
     * «Only the original thread that created a view hierarchy can touch its views».
     */
    private void terminarAuricular() {
        AudioTrack activa = pista;
        pista = null;
        if (activa != null) {
            try {
                activa.stop();
            } catch (Exception yaAcabada) {
                // en modo estático una pista terminada lanza al pararla: no hay nada que parar
            }
            activa.release();
        }
        try {
            gestor.setMode(modoAnterior);
        } catch (Exception sinGestor) {
            // sin gestor de audio no hay modo que restaurar, y tampoco pantalla que engañar
        }
        runOnUiThread(() -> {
            estado.setText("Ya está: mantén pulsado para hablarle otra vez.");
            botonHablar.setText("Mantén pulsado para hablar");
        });
    }

    /**
     * La pantalla se toca desde tres hilos distintos (red, reproducción, interfaz).
     * `TextView.setText` desde fuera del hilo de la interfaz lanza, así que todo texto
     * que no nazca de un clic pasa por aquí.
     */
    private void estadoDesdeHilo(String dicho) {
        runOnUiThread(() -> estado.setText(dicho));
    }

    private static String tiempos(JSONObject cuadro) {
        return "Escucha " + cuadro.optInt("ms_escucha") + " ms · respuesta "
                + cuadro.optInt("ms_respuesta") + " ms · voz " + cuadro.optInt("ms_voz")
                + " ms · total " + cuadro.optInt("ms_total") + " ms · vuelta "
                + cuadro.optInt("vueltas") + " · oído en " + cuadro.optString("oido_en", "PC")
                + " · voz en " + cuadro.optString("voz_en", "auricular")
                + " (" + cuadro.optString("origen", "?") + ")";
    }

    private String lee(InputStream entrada) throws IOException {
        if (entrada == null) {
            return "";
        }
        ByteArrayOutputStream acumulado = new ByteArrayOutputStream();
        byte[] trozo = new byte[4096];
        int n;
        while ((n = entrada.read(trozo)) > 0) {
            acumulado.write(trozo, 0, n);
        }
        entrada.close();
        return new String(acumulado.toByteArray(), StandardCharsets.UTF_8);
    }

    /** Un cuerpo de error no puede llenar la pantalla; 240 caracteres y basta. */
    private static String recorta(String texto) {
        String limpio = texto == null ? "" : texto.trim();
        return limpio.length() <= 240 ? limpio : limpio.substring(0, 240) + "…";
    }

    private static String loQueDice(Exception e) {
        String mensaje = e.getMessage();
        if (mensaje == null || mensaje.trim().isEmpty()) {
            return e.getClass().getSimpleName();
        }
        return recorta(mensaje);
    }

    private TextView texto(String contenido, float tamanio, int color) {
        TextView etiqueta = new TextView(this);
        etiqueta.setText(contenido);
        etiqueta.setTextSize(tamanio);
        etiqueta.setTextColor(color);
        etiqueta.setGravity(Gravity.START);
        return etiqueta;
    }

    private Button boton(String rotulo) {
        Button nuevo = new Button(this);
        nuevo.setText(rotulo);
        nuevo.setTextColor(Paleta.CIAN);
        nuevo.setBackgroundColor(0xFF0F2B3A);
        nuevo.setTextSize(17f);
        nuevo.setLetterSpacing(0.04f);
        return nuevo;
    }

    private LinearLayout.LayoutParams conMargen() {
        LinearLayout.LayoutParams caja = new LinearLayout.LayoutParams(-1, -2);
        caja.topMargin = dp(18);
        return caja;
    }

    private int dp(float valor) {
        return Math.round(valor * getResources().getDisplayMetrics().density);
    }

    /**
     * Saliendo de la pantalla se suelta el micrófono **y** el modo de audio. Sin esto el
     * teléfono se queda con el indicador de escucha encendido, o —peor— en modo llamada,
     * y la siguiente llamada de la dueña sale por el auricular con la voz de CORT dentro.
     */
    @Override
    protected void onPause() {
        super.onPause();
        // Si el hilo de copia está dentro de `read`, soltarle el micrófono desde aquí es
        // cerrar un objeto que otro hilo está usando: se le avisa (`grabando = false`) y
        // `volcar` lo cierra al entregar el envío, que es el orden que no revienta.
        boolean estabaGrabando = grabando;
        grabando = false;
        if (!estabaGrabando) {
            cerrarMicrofono();
        }
        terminarAuricular();
    }

    @Override
    protected void onDestroy() {
        cerrado = true;
        grabando = false;
        cerrarMicrofono();
        AudioTrack activa = pista;
        pista = null;
        if (activa != null) {
            try {
                activa.stop();
            } catch (Exception yaAcabada) {
                // nada que parar
            }
            activa.release();
        }
        if (gestor != null && gestor.getMode() != modoAnterior) {
            try {
                gestor.setMode(modoAnterior);
            } catch (Exception sinGestor) {
                // sin gestor no hay modo que devolver
            }
        }
        super.onDestroy();
    }
}
