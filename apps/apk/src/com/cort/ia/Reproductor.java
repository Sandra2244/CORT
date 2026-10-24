package com.cort.ia;

/*
 * El reproductor de CORT — la música y el video suenan AUNQUE la cara esté
 * cerrada, la pantalla apagada o el holograma detrás de otra app.
 *
 * Por qué es un servicio y no un <audio> de la página: el WebView se congela
 * cuando CORT pasa a segundo plano, así que el sonido se paraba; y si el micro
 * seguía abierto detrás, el teléfono se trababa (lo que la dueña notó). Aquí el
 * que suena es un `MediaPlayer` dentro de un servicio en primer plano con su
 * notificación, y la cara sólo manda órdenes por el puente `CortNative`.
 *
 * Sin AndroidX, sin `MediaBrowserServiceCompat`, sin Gradle: el `MediaSession`
 * del sistema — `android.media.session.MediaSession`, API 21, el mismo que usa
 * `MainActivity` para el doble toque— es público y con él valen los botones de
 * la notificación y la pantalla de bloqueo. **No** es `android.media.MediaSession`:
 * ése existe pero está oculto (`@hide`), y `android.jar` del SDK no lo exporta:
 * `javac` lo llamó en la línea del `import` y el APK no salió.
 *
 * El video: `MediaPlayer` reproduce el .mp4 sin superficie y su audio sigue
 * sonando en segundo plano; la imagen y el avance «cuadro a cuadro» los hace la
 * página con su <video> mientras está delante. Dicho sin adornos: con la cara
 * cerrada se escucha, no se ve.
 */

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioManager;
import android.media.MediaPlayer;
import android.media.session.MediaSession;
import android.net.Uri;
import android.os.Build;
import android.os.IBinder;
import android.os.SystemClock;
import android.util.Log;
import android.view.KeyEvent;

import java.util.ArrayList;
import java.util.List;

public class Reproductor extends Service {
    private static final String TAG = "CORT-reproductor";
    private static final String CANAL = "cort-musica";
    private static final int NOTA = 4242;

    public static final String ACCION = "com.cort.ia.REPRODUCTOR";
    public static final String ORDEN = "orden";

    /* ───────────── la cola, pública para que la lea el puente ───────────── */
    public static class Pista {
        public String uri, titulo, artista, genero;
        public long dur;
        public boolean video;

        public Pista(String uri, String titulo, String artista, String genero,
                     long dur, boolean video) {
            this.uri = uri; this.titulo = titulo == null ? "sin título" : titulo;
            this.artista = artista == null ? "" : artista;
            this.genero = genero == null ? "" : genero;
            this.dur = dur; this.video = video;
        }
    }

    private static final List<Pista> cola = new ArrayList<>();
    private static volatile int idx = -1;
    private static volatile Reproductor vivo;      // null = el servicio no está

    static synchronized int tamanyo() { return cola.size(); }
    static synchronized Pista en(int i) {
        return (i >= 0 && i < cola.size()) ? cola.get(i) : null;
    }
    static synchronized int indice() { return idx; }

    /* ─────────────────────────── instancias ─────────────────────────────── */
    private MediaPlayer mp;
    private MediaSession sesion;
    private AudioManager audio;
    private AudioFocusRequest focoPeticion;
    private boolean pausadoPorFoco = false;
    /** La hora del último toque del auricular, para cazar el **segundo** (2.4.1). */
    private long ultimoToque = 0L;

    @Override public IBinder onBind(Intent i) { return null; }

    @Override public void onCreate() {
        super.onCreate();
        vivo = this;
        audio = (AudioManager) getSystemService(Context.AUDIO_SERVICE);
        canal();
        mp = new MediaPlayer();
        mp.setAudioAttributes(new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_MEDIA)
                .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                .build());
        mp.setOnCompletionListener(new MediaPlayer.OnCompletionListener() {
            @Override public void onCompletion(MediaPlayer p) { siguiente(); }
        });
        mp.setOnErrorListener(new MediaPlayer.OnErrorListener() {
            @Override public boolean onError(MediaPlayer p, int que, int extra) {
                Log.w(TAG, "fallo el MediaPlayer (" + que + "/" + extra + "), sigo con la otra");
                siguiente();
                return true;
            }
        });
        sesion = new MediaSession(this, "CORT");
        sesion.setCallback(new MediaSession.Callback() {
            @Override public void onPlay() { reproducir(); }
            @Override public void onPause() { pausar(); }
            @Override public void onSkipToNext() { siguiente(); }
            @Override public void onSkipToPrevious() { anterior(); }
            @Override public void onSeekTo(long pos) { salto((int) pos); }
            @Override public void onStop() { parar(); }
            // La tecla física, antes de que el sistema la traduzca en play/pausa.
            @Override public boolean onMediaButtonEvent(Intent evento) {
                return dobleToque(evento);
            }
        });
        sesion.setActive(true);
        // Android 14: un servicio en primer plano con tipo `mediaPlayback` exige
        // arrancarse con startForeground() antes de nada. La notificación es la
        // que trae los botones del auricular cuando la cara ya no está.
        arrancaNotificacion();

        // `ponerCola()` puede llegar ANTES de que el sistema haya creado este
        // servicio: `startForegroundService` es asíncrono y la cola es estática.
        // Si al nacer ya hay canción señalada, se pone aquí; sin esto, el primer
        // «ponme música» del día no sonaba hasta volver a pulsar play.
        if (idx >= 0) pon(idx);
    }

    @Override public int onStartCommand(Intent i, int flags, int startId) {
        if (i != null) {
            String o = i.getStringExtra(ORDEN);
            if ("pausa".equals(o)) pausar();
            else if ("sigue".equals(o)) reproducir();
            else if ("siguiente".equals(o)) siguiente();
            else if ("anterior".equals(o)) anterior();
            else if ("para".equals(o)) parar();
        }
        return START_NOT_STICKY;
    }

    @Override public void onDestroy() {
        // El efecto se suelta ANTES que su `MediaPlayer`: al revés, algunos
        // fabricantes dejan el efecto colgado de una sesión que ya no existe.
        try { Ecualizador.suelta(); } catch (Throwable yaNo) { /* se apaga igual */ }
        try { if (mp != null) { mp.release(); mp = null; } } catch (Exception e) { }
        try { if (sesion != null) { sesion.setActive(false); sesion.release(); sesion = null; } }
        catch (Exception e) { }
        sueltaFoco();
        vivo = null;
        super.onDestroy();
    }

    /* ───────────────────────── las cuatro paredes ────────────────────────── */
    private void canal() {
        if (Build.VERSION.SDK_INT < 26) return;
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (nm == null || nm.getNotificationChannel(CANAL) != null) return;
        NotificationChannel c = new NotificationChannel(CANAL, "CORT · música",
                NotificationManager.IMPORTANCE_LOW);
        c.setDescription("El reproductor de CORT, con sus botones.");
        c.setLightColor(Color.parseColor("#39C5FF"));
        c.setShowBadge(false);
        nm.createNotificationChannel(c);
    }

    private PendingIntent boton(String orden) {
        Intent i = new Intent(this, Reproductor.class);
        i.putExtra(ORDEN, orden);
        return PendingIntent.getService(this, orden.hashCode(), i,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    private Notification construir(boolean sonando) {
        Pista p = en(idx);
        String titulo = p == null ? "CORT · reproductor" : p.titulo;
        String detalle = p == null ? "sin nada puesto"
                : (p.artista.isEmpty() ? p.genero : p.artista
                   + (p.genero.isEmpty() ? "" : " · " + p.genero));
        Notification.Builder b = (Build.VERSION.SDK_INT >= 26)
                ? new Notification.Builder(this, CANAL)
                : new Notification.Builder(this);
        b.setSmallIcon(android.R.drawable.ic_media_play)
         .setContentTitle(titulo)
         .setContentText(detalle)
         .setOngoing(sonando)
         .setOnlyAlertOnce(true)
         .setContentIntent(abrirCara());
        b.addAction(new Notification.Action.Builder((android.graphics.drawable.Icon) null,
                sonando ? "⏸ pausar" : "▶ seguir", boton(sonando ? "pausa" : "sigue")).build());
        b.addAction(new Notification.Action.Builder((android.graphics.drawable.Icon) null,
                "⏭ siguiente", boton("siguiente")).build());
        if (Build.VERSION.SDK_INT >= 26 && sesion != null) {
            // `MediaStyle.fromSession(...)` es de marco interno (`@hide`): lo público
            // es pasar el `Token` de la sesión, que es lo que ven el auricular y la
            // pantalla de bloqueo.
            b.setStyle(new Notification.MediaStyle()
                    .setMediaSession(sesion.getSessionToken())
                    .setShowActionsInCompactView(0, 1));
        }
        return b.build();
    }

    private PendingIntent abrirCara() {
        Intent i = new Intent(this, MainActivity.class);
        i.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
        return PendingIntent.getActivity(this, 7, i,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    private void arrancaNotificacion() {
        try { startForeground(NOTA, construir(sonando())); }
        catch (Exception e) { Log.w(TAG, "no arrancó como primer plano: " + e); }
    }

    private void refresca() {
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (nm != null) try { nm.notify(NOTA, construir(sonando())); } catch (Exception e) { }
        if (vivo != null && vivo.sesion != null) estadoSesion();
    }

    /* Lo que CORT deja hacer desde la notificación, la pantalla de bloqueo y el
     * auricular: play, pausa, saltar, buscar y parar. Es un `long` porque el
     * sistema usa una máscara de 64 bits; pasarla como `int` (como hacía antes
     * esta línea) deja a `javac` sin ninguna sobrecarga de `setState` válida. */
    private static final long ACCIONES =
            android.media.session.PlaybackState.ACTION_PLAY
          | android.media.session.PlaybackState.ACTION_PAUSE
          | android.media.session.PlaybackState.ACTION_SKIP_TO_NEXT
          | android.media.session.PlaybackState.ACTION_SKIP_TO_PREVIOUS
          | android.media.session.PlaybackState.ACTION_SEEK_TO
          | android.media.session.PlaybackState.ACTION_STOP;

    private void estadoSesion() {
        Pista p = en(idx);
        android.media.session.PlaybackState.Builder sb =
                new android.media.session.PlaybackState.Builder().setActions(ACCIONES);
        if (p != null) sb.setExtras(extrasDe(p));
        // Sobrecarga (estado, acciones, velocidad, posición) — la más antigua que
        // lleva posición, disponible desde API 22 y con minSdk 26 no hay que
        // preguntar por la versión.
        sb.setState(sonando() ? android.media.session.PlaybackState.STATE_PLAYING
                              : android.media.session.PlaybackState.STATE_PAUSED,
                ACCIONES, 1f, p == null ? -1L : pos());
        sesion.setMetadata(metaDe(p));
        sesion.setPlaybackState(sb.build());
    }

    private android.os.Bundle extrasDe(Pista p) {
        android.os.Bundle x = new android.os.Bundle();
        x.putString("titulo", p.titulo);
        x.putString("artista", p.artista);
        return x;
    }

    private android.media.MediaMetadata metaDe(Pista p) {
        android.media.MediaMetadata.Builder m = new android.media.MediaMetadata.Builder();
        if (p != null) {
            m.putString(android.media.MediaMetadata.METADATA_KEY_TITLE, p.titulo);
            if (!p.artista.isEmpty())
                m.putString(android.media.MediaMetadata.METADATA_KEY_ARTIST, p.artista);
            if (!p.genero.isEmpty())
                m.putString(android.media.MediaMetadata.METADATA_KEY_GENRE, p.genero);
            if (p.dur > 0) m.putLong(android.media.MediaMetadata.METADATA_KEY_DURATION, p.dur);
            // Aquí había un `METADATA_KEY_MEDIA_TYPE` con `MEDIA_TYPE_MOVIE`/
            // `MEDIA_TYPE_MUSIC`: esas dos constantes son de `androidx`
            // (`MediaMetadataCompat`), no de `android.media.MediaMetadata`, y el SDK
            // las rechazó. El vídeo ya se distingue en la cara (`Pista.video`), que es
            // donde hace falta: aquí sólo se pinta el cartel de la canción.
        }
        return m.build();
    }

    /* ─────────────────────────── el foco de audio ─────────────────────────── */
    private boolean pideFoco() {
        if (audio == null) return true;
        // Modo juego: el foco es del juego. Si CORT lo pidiera, Android **duckea**
        // o corta el audio de Call of Duty, que es justo lo que la dueña no quiere.
        // Devolver `false` deja en silencio al `MediaPlayer` (`pon()` y `reproducir()`
        // sólo arrancan cuando el foco se concede), sin tocar la cola ni la notificación.
        if (CortNative.enJuego()) return false;
        if (Build.VERSION.SDK_INT < 26) {
            int r = audio.requestAudioFocus(nuevaEscucha(), AudioManager.STREAM_MUSIC,
                    AudioManager.AUDIOFOCUS_GAIN);
            return r == AudioManager.AUDIOFOCUS_REQUEST_GRANTED;
        }
        if (focoPeticion == null) {
            focoPeticion = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN)
                    .setAudioAttributes(new AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_MEDIA)
                            .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build())
                    .setWillPauseWhenDucked(true)
                    .setOnAudioFocusChangeListener(nuevaEscucha())
                    .build();
        }
        return audio.requestAudioFocus(focoPeticion) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED;
    }

    private void sueltaFoco() {
        if (audio == null) return;
        try {
            if (Build.VERSION.SDK_INT < 26) audio.abandonAudioFocus(nuevaEscucha());
            else if (focoPeticion != null) audio.abandonAudioFocusRequest(focoPeticion);
        } catch (Exception e) { }
    }

    private AudioManager.OnAudioFocusChangeListener escucha;
    private AudioManager.OnAudioFocusChangeListener nuevaEscucha() {
        if (escucha == null) {
            escucha = new AudioManager.OnAudioFocusChangeListener() {
                @Override public void onAudioFocusChange(int cambio) {
                    if (cambio == AudioManager.AUDIOFOCUS_LOSS) { pausar(); }
                    else if (cambio == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT) {
                        if (sonando()) { pausar(); pausadoPorFoco = true; }
                    } else if (cambio == AudioManager.AUDIOFOCUS_GAIN) {
                        if (pausadoPorFoco) { pausadoPorFoco = false; reproducir(); }
                    }
                }
            };
        }
        return escucha;
    }

    /* ───────────────────────────── el sonido ─────────────────────────────── */
    private boolean vivo() { return vivo != null && vivo.mp != null; }

    private void pon(int i) {
        Reproductor r = vivo;
        if (r == null) return;
        Pista p = en(i);
        if (p == null) return;
        idx = i;
        try {
            r.mp.reset();
            r.mp.setDataSource(r, Uri.parse(p.uri));
            r.mp.setOnPreparedListener(new MediaPlayer.OnPreparedListener() {
                @Override public void onPrepared(MediaPlayer m) {
                    // F15 · la sesión de audio ya existe: aquí se engancha el
                    // ecualizador de verdad, y si había un preset puesto se
                    // vuelve a poner para esta canción.
                    try { Ecualizador.engancha(m.getAudioSessionId()); }
                    catch (Throwable noHayEcualizador) { /* sin efecto, hay música */ }
                    if (pideFoco()) { m.start(); }
                    refresca();
                    avisa();
                }
            });
            r.mp.prepareAsync();
        } catch (Exception e) {
            Log.w(TAG, "no se pudo poner " + p.uri + ": " + e);
        }
        r.estadoSesion();
    }

    /**
     * La velocidad de reproducción, como la fila «Velocidad» de Lark (0,5× … 2,0×).
     *
     * Es `MediaPlayer.setPlaybackParams`, de verdad: Android obliga a **pausar**
     * antes de cambiar los parámetros y a reanudar después si estaba sonando, y así
     * está hecho. Con `Build.VERSION` por debajo de 23 no hay forma sin librerías, y
     * se dice con la cadena vacía en vez de fingir un número.
     */
    public static String velocidad(float v) {
        Reproductor r = vivo;
        if (r == null || r.mp == null) return "nada puesto";
        if (android.os.Build.VERSION.SDK_INT < 23) return "este Android no puede cambiar la velocidad";
        float buena = Math.max(0.25f, Math.min(3f, v));
        try {
            boolean sonaba = r.sonando();
            if (sonaba) r.mp.pause();
            r.mp.setPlaybackParams(r.mp.getPlaybackParams().setSpeed(buena));
            if (sonaba) r.mp.start();
            r.refresca();
            return "";
        } catch (Exception eseFabricanteNoDeja) {
            return "el teléfono no dejó cambiar la velocidad";
        }
    }

    /** Que suene lo que ya está en la cola (o lo que se acaba de poner). */
    public static void reproducir() {
        Reproductor r = vivo;
        if (r == null) return;
        try {
            if (r.mp != null && r.mp.isPlaying()) return;
            if (r.mp != null && idx >= 0 && r.mp.getDuration() > 0) {
                if (r.pideFoco()) r.mp.start();
            } else {
                r.pon(idx < 0 ? 0 : idx);
            }
        } catch (Exception e) { }
        r.refresca();
        avisa();
    }

    public static void pausar() {
        Reproductor r = vivo;
        if (r == null) return;
        try { if (r.mp != null && r.mp.isPlaying()) r.mp.pause(); } catch (Exception e) { }
        r.refresca();
        avisa();
    }

    public static void siguiente() { mueve(1); }
    public static void anterior() { mueve(-1); }

    private static void mueve(int paso) {
        Reproductor r = vivo;
        if (r == null) return;
        int n = tamanyo();
        if (n == 0) return;
        int i = idx + paso;
        if (i < 0) i = n - 1;
        if (i >= n) i = 0;
        r.pon(i);
        r.refresca();
        avisa();
    }

    /** Poner la cola entera y arrancar por la canción que se diga. */
    public static void ponerCola(Context c, List<Pista> pistas, int desde) {
        synchronized (cola) {
            cola.clear();
            if (pistas != null) cola.addAll(pistas);
            idx = (desde >= 0 && desde < cola.size()) ? desde : (cola.isEmpty() ? -1 : 0);
        }
        arrancar(c);
        Reproductor r = vivo;
        if (r != null && idx >= 0) r.pon(idx);
        if (r != null) r.refresca();
    }

    public static void arrancar(Context c) {
        Intent i = new Intent(c, Reproductor.class);
        try {
            if (Build.VERSION.SDK_INT >= 26) c.startForegroundService(i);
            else c.startService(i);
        } catch (Exception e) {
            Log.w(TAG, "no se pudo arrancar el servicio: " + e);
        }
    }

    public static void detener() {
        Reproductor r = vivo;
        if (r != null && r.getApplicationContext() != null) {
            r.stopSelf();
        }
    }

    /* ─────────────────────────── modo juego ─────────────────────────────────
     * Lo que necesita el juego es **silencio y foco fuera**, no apagar el
     * reproductor: la cola y la canción tienen que seguir en su sitio para
     * volver a sonar al desactivar el modo. De ahí que `silenciar` pause (que
     * conserva el `MediaPlayer` preparado) en vez de `stop()`, que obligaría a
     * `prepareAsync()` otra vez.
     *
     * Y lo importante es el **abandono del foco**: mientras CORT lo tenga, el
     * sistema baja o corta el audio del juego cada vez que arranca una canción.
     * `sueltaFoco()` ya lleva dentro la comprobación de versión (el
     * `abandonAudioFocusRequest` de API 26 y el `abandonAudioFocus` antiguo
     * para Android 8/9), así que se reutiliza en lugar de escribir un segundo
     * camino. `pausadoPorFoco` se limpia a propósito: si no, el `AUDIOFOCUS_GAIN`
     * del sistema reanudaría la música encima del juego.
     */
    public static void silenciar(Context c) {
        Reproductor r = vivo;
        if (r == null) return;
        try { if (r.mp != null && r.mp.isPlaying()) r.mp.pause(); } catch (Exception e) { }
        r.pausadoPorFoco = false;
        r.sueltaFoco();
        r.refresca();
        avisa();
    }

    /**
     * La sesión de medios se **desactiva** para que el auricular se lo quede el
     * juego: con la sesión de CORT activa, el doble toque se lo llevaba CORT y
     * la dueña salía de la partida. `setActive(false)` no libera la sesión — el
     * `Token` de la notificación sigue siendo válido—, así que `recuperarSesion()`
     * la devuelve tal cual estaba.
     *
     * Todo dentro de `try/catch` y con `sesion` comprobado: es el mismo cuidado
     * que pone `sesionSetActiveFalso()`, y por el mismo motivo — el servicio puede
     * estar muriéndose mientras alguien llama.
     */
    public static void soltarSesion() {
        Reproductor r = vivo;
        if (r == null) return;
        try { if (r.sesion != null) r.sesion.setActive(false); }
        catch (Exception elSistemaNoLoPermite) { }
    }

    /** Lo contrario: la sesión vuelve a existir para el auricular y el bloqueo. */
    public static void recuperarSesion() {
        Reproductor r = vivo;
        if (r == null) return;
        try {
            if (r.sesion != null) {
                r.sesion.setActive(true);
                r.estadoSesion();
            }
        } catch (Exception elSistemaNoLoPermite) { }
    }

    /* ────────────── el doble toque con la cara cerrada (2.4.1) ──────────────
     *
     * Hasta ahora el doble toque del auricular vivía sólo en `MainActivity`, y su
     * `MediaSession` se desactiva en `onPause()` — «la música vuelve a su dono»,
     * que es lo correcto para no robarle los botones a Spotify. El resultado,
     * medido en la lectura de las dos clases: con CORT **cerrado** nadie le
     * devolvía el toque a CORT, así que había que abrir la cara a mano. Aquí se
     * cierra el círculo: la sesión del reproductor vive mientras suena la música
     * (o sea, con la pantalla apagada y la cara atrás), y es esa sesión la que
     * recibe la tecla.
     *
     * Las tres reglas que comparten los dos sitios:
     *   · sólo `HEADSETHOOK` y `MEDIA_PLAY_PAUSE`, y sólo con `ACTION_DOWN`;
     *   · el **primero** toque devuelve `false` — se queda con la música, que es
     *     lo que espera cualquiera que pulsa una vez—; el **segundo** dentro de
     *     500 ms es de CORT y devuelve `true`;
     *   · en modo juego no se hace nada: ahí la sesión ya está suelta
     *     (`soltarSesion()`), y por si una capa de fabricante la trae igual, el
     *     `CortNative.enJuego()` lo corta antes de abrir el micro.
     *
     * Se pausa la canción antes de abrir la cara, y no es un detalle de educación:
     * el oído (`Oido.kt`) y el reconocedor de Google oyen por el mismo micrófono
     * que el auricular reporta, y con la música sonando CORT se transcribe a sí
     * misma los tambores. `MainActivity.abreLoQueToque()` manda después el
     * `escuchaDelAuricular()`, que es el que pinta la insignia de «te escucho».
     */

    /** `true` si el toque es de CORT; `false` si lo deja pasar a la música. */
    private boolean dobleToque(Intent evento) {
        KeyEvent tecla = MainActivity.teclaDe(evento);
        if (tecla == null || tecla.getAction() != KeyEvent.ACTION_DOWN) return false;
        int codigo = tecla.getKeyCode();
        boolean toque = codigo == KeyEvent.KEYCODE_HEADSETHOOK
                     || codigo == KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE;
        if (!toque || CortNative.enJuego()) return false;
        long ahora = SystemClock.elapsedRealtime();
        if (ultimoToque != 0L && ahora - ultimoToque < 500L) {
            ultimoToque = 0L;
            pausar();
            Intent abrir = new Intent(this, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
                .putExtra(MainActivity.PIDE_ESCUCHAR, true);
            try {
                startActivity(abrir);
            } catch (Exception noPuedeAbrir) {
                // Con la pantalla bloqueada hay capas que no dejan lanzar desde un
                // servicio. La música queda pausada y CORT sigue sonando al abrir:
                // mejor eso que un botón que cierra la app en la cara de la dueña.
                Log.w(TAG, "el doble toque no pudo abrir la cara: " + noPuedeAbrir);
            }
            return true;
        }
        ultimoToque = ahora;
        return false;
    }

    /** Parar del todo: se calla, se quita la notificación y se apaga el servicio. */
    private static void parar() {
        Reproductor r = vivo;
        if (r == null) return;
        try { if (r.mp != null) r.mp.stop(); } catch (Exception e) { }
        synchronized (cola) { idx = -1; }
        r.sesionSetActiveFalso();
        r.stopForeground(true);
        r.stopSelf();
    }

    private void sesionSetActiveFalso() {
        try { if (sesion != null) sesion.setActive(false); } catch (Exception e) { }
    }

    /** Saltar a un segundo concreto (lo usa la cara con su barra de progreso). */
    public static void salto(int ms) {
        Reproductor r = vivo;
        if (r == null) return;
        try {
            if (r.mp != null && r.mp.getDuration() > 0) {
                r.mp.seekTo(Math.max(0, Math.min(ms, r.mp.getDuration())));
                avisa();
            }
        } catch (Exception e) { }
    }

    /** Cuadro a cuadro: ±1/30 s, para mirar un video fotograma por fotograma. */
    public static void cuadro(boolean haciaAtras) {
        Reproductor r = vivo;
        if (r == null) return;
        try {
            if (r.mp != null) {
                int pos = r.mp.getCurrentPosition();
                r.mp.seekTo(Math.max(0, pos + (haciaAtras ? -33 : 33)));
                avisa();
            }
        } catch (Exception e) { }
    }

    public static void volumen(float de0a1) {
        Reproductor r = vivo;
        if (r == null) return;
        try {
            float v = Math.max(0f, Math.min(1f, de0a1));
            if (r.mp != null) r.mp.setVolume(v, v);
        } catch (Exception e) { }
    }

    /* ─────────────────────────── lo que lee la cara ────────────────────────── */
    public static boolean estaVivo() { return vivo != null; }

    private static boolean sonando() {
        Reproductor r = vivo;
        try { return r != null && r.mp != null && r.mp.isPlaying(); }
        catch (Exception e) { return false; }
    }

    private static int pos() {
        Reproductor r = vivo;
        try { return (r != null && r.mp != null) ? r.mp.getCurrentPosition() : 0; }
        catch (Exception e) { return 0; }
    }

    private static int duracion() {
        Reproductor r = vivo;
        try {
            if (r == null || r.mp == null) return 0;
            int d = r.mp.getDuration();
            if (d > 0) return d;
            Pista p = en(idx);
            return p == null ? 0 : (int) p.dur;
        } catch (Exception e) { return 0; }
    }

    /**
     * El estado, en JSON, para `CortNative.musicaEstado()`.
     *
     * `uri` y `video` van **también arriba**, repetidos de `pista`, porque la
     * pantalla que pega el vídeo (la MV, con su <video> del WebView) los necesita
     * sin tener que andar mirando si hay canción o si el objeto existe: en Java no
     * hay `?.` de JavaScript, y un `pista == null` mal tratado sería un hueco que
     * sólo aparece en el teléfono. La URI es la del índice de Android
     * (`content://media/external/...`), que es precisamente lo que un <video>
     * necesita y lo que `setAllowContentAccess(true)` de la cara deja leer.
     * `juego` es el estado del modo juego, para que el interruptor de la cara se
     * pinte como está de verdad y no como la última vez que se pulsó.
     */
    public static String estadoJson() {
        Pista p = en(idx);
        StringBuilder s = new StringBuilder(256);
        s.append('{')
         .append("\"vivo\":").append(vivo != null)
         .append(",\"suena\":").append(sonando())
         .append(",\"pos\":").append(pos())
         .append(",\"dur\":").append(duracion())
         .append(",\"idx\":").append(idx)
         .append(",\"total\":").append(tamanyo())
         .append(",\"uri\":").append(p == null || p.uri == null
                 ? "null" : "\"" + esc(p.uri) + "\"")
         .append(",\"video\":").append(p != null && p.video)
         .append(",\"juego\":").append(CortNative.enJuego());
        s.append(",\"pista\":");
        if (p == null) s.append("null");
        else {
            s.append("{\"titulo\":\"").append(esc(p.titulo))
             .append("\",\"artista\":\"").append(esc(p.artista))
             .append("\",\"genero\":\"").append(esc(p.genero))
             .append("\",\"uri\":\"").append(esc(p.uri))
             .append("\",\"video\":").append(p.video).append('}');
        }
        s.append('}');
        return s.toString();
    }

    static String esc(String t) {
        if (t == null) return "";
        StringBuilder s = new StringBuilder(t.length() + 8);
        for (int i = 0; i < t.length(); i++) {
            char c = t.charAt(i);
            if (c == '"' || c == '\\') { s.append('\\').append(c); }
            else if (c == '\n') s.append("\\n");
            else if (c == '\r') s.append(' ');
            else if (c == '\t') s.append(' ');
            else if (c < 0x20) { /* fuera */ }
            else s.append(c);
        }
        return s.toString();
    }

    /** La cara se entera de que algo cambió (play, pausa, canción nueva). */
    private static void avisa() {
        try {
            MainActivity cara = MainActivity.front();
            if (cara != null) cara.puente().musicaCambio();
        } catch (Exception e) { }
    }
}
