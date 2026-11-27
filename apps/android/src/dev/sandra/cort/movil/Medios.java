package dev.sandra.cort.movil;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.media.AudioAttributes;
import android.media.AudioDeviceCallback;
import android.media.AudioDeviceInfo;
import android.media.AudioManager;
import android.media.MediaMetadata;
import android.media.session.MediaSession;
import android.media.session.PlaybackState;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.view.KeyEvent;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

final class Medios {
    interface AlEstado {
        void estado(JSONObject estado);
    }

    private static final int MAX_RESPUESTAS = 12;
    private static final int MAX_CARACTERES = 20000;
    private static final long ACCIONES = PlaybackState.ACTION_PLAY
            | PlaybackState.ACTION_PAUSE | PlaybackState.ACTION_STOP
            | PlaybackState.ACTION_SKIP_TO_NEXT | PlaybackState.ACTION_SKIP_TO_PREVIOUS;

    private static Medios compartido;

    private final Context contexto;
    private final Handler principal = new Handler(Looper.getMainLooper());
    private final AudioManager audio;
    private final MediaSession sesion;
    private final List<Vinculo> vinculos = new ArrayList<>();
    private final List<String> historial = new ArrayList<>();
    private List<String> trozosActuales;
    private final Voz.AlHabla oyenteVoz = this::cambioVoz;
    private final BroadcastReceiver ruido = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (AudioManager.ACTION_AUDIO_BECOMING_NOISY.equals(intent.getAction())) {
                pausar("se desconectó una salida de audio");
            }
        }
    };
    private final AudioDeviceCallback dispositivos = new AudioDeviceCallback() {
        @Override
        public void onAudioDevicesAdded(AudioDeviceInfo[] agregados) {
            publicar();
        }

        @Override
        public void onAudioDevicesRemoved(AudioDeviceInfo[] retirados) {
            if (!Audifonos.hay(audio)) pausar("no queda un auricular detectado");
            else publicar();
        }
    };

    private Voz voz;
    private String actual = "";
    private int posicion = -1;
    private String estado = "detenido";
    private String mensaje = "";
    private boolean receptoresActivos;

    private Medios(Context context) {
        contexto = context.getApplicationContext();
        audio = (AudioManager) contexto.getSystemService(Context.AUDIO_SERVICE);
        sesion = new MediaSession(contexto, "cort-voz");
        sesion.setFlags(MediaSession.FLAG_HANDLES_MEDIA_BUTTONS
                | MediaSession.FLAG_HANDLES_TRANSPORT_CONTROLS);
        sesion.setCallback(new Callback());
        sesion.setMetadata(new MediaMetadata.Builder()
                .putString(MediaMetadata.METADATA_KEY_TITLE, "Respuesta de CORT")
                .putString(MediaMetadata.METADATA_KEY_ARTIST, "CORT")
                .build());
        sesion.setPlaybackToLocal(new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ASSISTANT)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .build());
        sesion.setPlaybackState(estadoAlambre());
    }

    static synchronized Medios compartido(Context context) {
        if (compartido == null) compartido = new Medios(context);
        return compartido;
    }

    void vincular(Voz nuevaVoz, AlEstado entrega) {
        principal.post(() -> {
            for (int i = vinculos.size() - 1; i >= 0; i--) {
                if (vinculos.get(i).voz == nuevaVoz) vinculos.remove(i);
            }
            if (voz != null && voz != nuevaVoz) {
                voz.quitarAlHablar(oyenteVoz);
                voz.callar();
            }
            detener();
            vinculos.add(new Vinculo(nuevaVoz, entrega));
            voz = nuevaVoz;
            voz.alHablar(oyenteVoz);
            actual = "";
            trozosActuales = null;
            historial.clear();
            posicion = -1;
            activarReceptores();
            publicar();
        });
    }

    void desvincular(Voz vozQueCierra, AlEstado entrega) {
        principal.post(() -> {
            for (int i = vinculos.size() - 1; i >= 0; i--) {
                Vinculo vinculo = vinculos.get(i);
                if (vinculo.voz == vozQueCierra && vinculo.entrega == entrega) {
                    vinculos.remove(i);
                }
            }
            if (voz != vozQueCierra) return;
            voz.quitarAlHablar(oyenteVoz);
            voz.callar();
            voz = vinculos.isEmpty() ? null : vinculos.get(vinculos.size() - 1).voz;
            if (voz != null) voz.alHablar(oyenteVoz);
            actual = "";
            trozosActuales = null;
            historial.clear();
            posicion = -1;
            estado = "detenido";
            mensaje = "";
            sesion.setActive(false);
            sesion.setPlaybackState(estadoAlambre());
            if (voz == null) desactivarReceptores();
            publicar();
        });
    }

    boolean hablar(String texto) {
        if (!prepararRespuesta(texto)) return false;
        return decirActual();
    }

    boolean hablarLectura(List<String> trozos) {
        if (trozos == null || trozos.isEmpty()) return false;
        if (!prepararRespuesta(android.text.TextUtils.join(" ", trozos))) return false;
        trozosActuales = new ArrayList<>(trozos);
        return decirActual();
    }

    private boolean prepararRespuesta(String texto) {
        if (texto == null || texto.trim().isEmpty()) return false;
        if (texto.length() > MAX_CARACTERES) {
            mensaje = "la respuesta supera el límite de locución de 20 000 caracteres";
            publicar();
            return false;
        }
        if (voz == null) {
            mensaje = "no hay una superficie de voz activa";
            publicar();
            return false;
        }
        if (!historial.contains(texto)) {
            historial.add(texto);
            while (historial.size() > MAX_RESPUESTAS) historial.remove(0);
        }
        posicion = historial.indexOf(texto);
        actual = texto;
        trozosActuales = null;
        return true;
    }

    void accion(String accion) {
        principal.post(() -> {
            if (!ReglasMedios.permitida(accion)) {
                mensaje = "esa acción de medios no está permitida";
                publicar();
                return;
            }
            if (ReglasMedios.REPRODUCIR.equals(accion)) reproducir();
            else if (ReglasMedios.PAUSAR.equals(accion)) pausar("locución pausada");
            else if (ReglasMedios.DETENER.equals(accion)) detener();
            else if (ReglasMedios.SIGUIENTE.equals(accion)) desplazar(1);
            else desplazar(-1);
        });
    }

    void pausar(String motivo) {
        if (Looper.myLooper() == Looper.getMainLooper()) pausarAhora(motivo);
        else principal.post(() -> pausarAhora(motivo));
    }

    private void pausarAhora(String motivo) {
        if (voz != null) voz.callar();
        estado = actual.isEmpty() ? "detenido" : "pausado";
        mensaje = motivo;
        sesion.setActive(false);
        sesion.setPlaybackState(estadoAlambre());
        publicar();
    }

    void detener() {
        if (voz != null) voz.callar();
        actual = "";
        trozosActuales = null;
        estado = "detenido";
        mensaje = "";
        sesion.setActive(false);
        sesion.setPlaybackState(estadoAlambre());
        publicar();
    }

    JSONObject estado() {
        try {
            JSONObject j = new JSONObject();
            j.put("type", "medios_estado");
            j.put("origen", "real");
            j.put("estado", estado);
            j.put("mensaje", mensaje);
            j.put("puede_reproducir", !actual.isEmpty() && voz != null);
            j.put("puede_siguiente", posicion >= 0 && posicion + 1 < historial.size());
            j.put("puede_anterior", posicion > 0);
            j.put("salida", Audifonos.salida(audio));
            j.put("salida_confirmada", false);
            j.put("control_externo", "no disponible");
            j.put("limite", "Controla sólo la voz de CORT. Pausar detiene la locución; "
                    + "Reproducir reinicia la última respuesta. La música de otras apps "
                    + "queda a cargo de su reproductor.");
            return j;
        } catch (org.json.JSONException imposible) {
            throw new IllegalStateException(imposible);
        }
    }

    private void cambioVoz(boolean hablando) {
        principal.post(() -> {
            if (voz == null) return;
            if (!hablando && voz.hablando()) return;
            if (hablando) {
                estado = "reproduciendo";
                mensaje = "";
                sesion.setActive(true);
            } else {
                estado = actual.isEmpty() ? "detenido" : "pausado";
                sesion.setActive(false);
            }
            sesion.setPlaybackState(estadoAlambre());
            publicar();
        });
    }

    private void reproducir() {
        if (actual.isEmpty() || voz == null) {
            mensaje = "todavía no hay una respuesta de CORT para reproducir";
            publicar();
            return;
        }
        decirActual();
    }

    private boolean decirActual() {
        estado = "preparando";
        mensaje = "preparando la voz de CORT";
        sesion.setActive(true);
        sesion.setPlaybackState(estadoAlambre());
        publicar();
        if (trozosActuales != null) {
            for (String trozo : trozosActuales) {
                if (voz == null || !voz.seguir(trozo)) return false;
            }
            return true;
        }
        return voz != null && voz.hablar(actual);
    }

    private void desplazar(int paso) {
        int destino = posicion + paso;
        if (destino < 0 || destino >= historial.size()) {
            mensaje = paso > 0 ? "no hay otra respuesta posterior" : "no hay otra respuesta anterior";
            publicar();
            return;
        }
        posicion = destino;
        actual = historial.get(posicion);
        trozosActuales = null;
        decirActual();
    }

    private PlaybackState estadoAlambre() {
        int codigo;
        if ("reproduciendo".equals(estado)) codigo = PlaybackState.STATE_PLAYING;
        else if ("preparando".equals(estado)) codigo = PlaybackState.STATE_BUFFERING;
        else if ("pausado".equals(estado)) codigo = PlaybackState.STATE_PAUSED;
        else codigo = PlaybackState.STATE_STOPPED;
        return new PlaybackState.Builder().setState(codigo, 0L, 1.0f)
                .setActions(ACCIONES).build();
    }

    private void activarReceptores() {
        if (receptoresActivos) return;
        receptoresActivos = true;
        IntentFilter filtro = new IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            contexto.registerReceiver(ruido, filtro, Context.RECEIVER_NOT_EXPORTED);
        } else {
            contexto.registerReceiver(ruido, filtro);
        }
        audio.registerAudioDeviceCallback(dispositivos, principal);
    }

    private void desactivarReceptores() {
        if (!receptoresActivos) return;
        receptoresActivos = false;
        try {
            contexto.unregisterReceiver(ruido);
        } catch (IllegalArgumentException yaCerrado) {
        }
        audio.unregisterAudioDeviceCallback(dispositivos);
    }

    private void publicar() {
        JSONObject estadoActual = estado();
        for (Vinculo vinculo : vinculos) {
            try {
                vinculo.entrega.estado(estadoActual);
            } catch (RuntimeException superficieCerrada) {
                // El transporte sigue aunque una vista ya no esté montada.
            }
        }
    }

    private final class Callback extends MediaSession.Callback {
        @Override
        public void onPlay() {
            reproducir();
        }

        @Override
        public void onPause() {
            pausar("locución pausada desde los controles del sistema");
        }

        @Override
        public void onStop() {
            detener();
        }

        @Override
        public void onSkipToNext() {
            desplazar(1);
        }

        @Override
        public void onSkipToPrevious() {
            desplazar(-1);
        }

        @Override
        public boolean onMediaButtonEvent(Intent evento) {
            KeyEvent tecla = evento.getParcelableExtra(Intent.EXTRA_KEY_EVENT);
            if (tecla == null || !ReglasMedios.teclaMedia(
                    tecla.getKeyCode(), tecla.getAction(), tecla.getRepeatCount())) {
                return super.onMediaButtonEvent(evento);
            }
            switch (tecla.getKeyCode()) {
                case KeyEvent.KEYCODE_MEDIA_PLAY:
                    reproducir();
                    break;
                case KeyEvent.KEYCODE_MEDIA_PAUSE:
                    pausar("locución pausada desde una tecla de audio");
                    break;
                case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:
                    if ("reproduciendo".equals(estado) || "preparando".equals(estado)) {
                        pausar("locución pausada desde una tecla de audio");
                    } else {
                        reproducir();
                    }
                    break;
                case KeyEvent.KEYCODE_MEDIA_STOP:
                    detener();
                    break;
                case KeyEvent.KEYCODE_MEDIA_NEXT:
                    desplazar(1);
                    break;
                case KeyEvent.KEYCODE_MEDIA_PREVIOUS:
                    desplazar(-1);
                    break;
                default:
                    return false;
            }
            return true;
        }

        @Override
        public void onFastForward() {
            mensaje = "CORT no permite avanzar dentro de una locución de texto a voz";
            publicar();
        }

        @Override
        public void onRewind() {
            mensaje = "CORT no permite retroceder dentro de una locución de texto a voz";
            publicar();
        }

        @Override
        public void onSeekTo(long posicion) {
            mensaje = "la posición exacta no está disponible en la voz de Android";
            publicar();
        }
    }

    private static final class Vinculo {
        final Voz voz;
        final AlEstado entrega;

        Vinculo(Voz voz, AlEstado entrega) {
            this.voz = voz;
            this.entrega = entrega;
        }
    }
}
