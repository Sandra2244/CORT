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
 * del sistema (`android.media.MediaSession`, API 21) es público y con él valen
 * el doble toque del auricular y los botones de la notificación.
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
import android.media.MediaSession;
import android.net.Uri;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;

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
            b.setStyle(Notification.MediaStyle.fromSession(sesion)
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

    private void estadoSesion() {
        Pista p = en(idx);
        android.media.session.PlaybackState.Builder sb =
                new android.media.session.PlaybackState.Builder()
                .setActions(android.media.session.PlaybackState.ACTION_PLAY
                        | android.media.session.PlaybackState.ACTION_PAUSE
                        | android.media.session.PlaybackState.ACTION_SKIP_TO_NEXT
                        | android.media.session.PlaybackState.ACTION_SKIP_TO_PREVIOUS
                        | android.media.session.PlaybackState.ACTION_SEEK_TO
                        | android.media.session.PlaybackState.ACTION_STOP);
        if (p != null) sb.setExtras(extrasDe(p));
        sb.setState(sonando() ? android.media.session.PlaybackState.STATE_PLAYING
                              : android.media.session.PlaybackState.STATE_PAUSED,
                p == null ? 0 : pos(), -1f, 1f,
                p == null ? 0 : p.dur, System.currentTimeMillis());
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
            m.putInt(android.media.MediaMetadata.METADATA_KEY_MEDIA_TYPE,
                    p.video ? android.media.MediaMetadata.MEDIA_TYPE_MOVIE
                            : android.media.MediaMetadata.MEDIA_TYPE_MUSIC);
        }
        return m.build();
    }

    /* ─────────────────────────── el foco de audio ─────────────────────────── */
    private boolean pideFoco() {
        if (audio == null) return true;
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

    /** El estado, en JSON, para `CortNative.musicaEstado()`. */
    public static String estadoJson() {
        Pista p = en(idx);
        StringBuilder s = new StringBuilder(192);
        s.append('{')
         .append("\"vivo\":").append(vivo != null)
         .append(",\"suena\":").append(sonando())
         .append(",\"pos\":").append(pos())
         .append(",\"dur\":").append(duracion())
         .append(",\"idx\":").append(idx)
         .append(",\"total\":").append(tamanyo());
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
