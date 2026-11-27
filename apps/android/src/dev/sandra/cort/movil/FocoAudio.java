package dev.sandra.cort.movil;

import android.content.Context;
import android.media.AudioManager;
import java.util.IdentityHashMap;
import java.util.Map;

final class FocoAudio {
    interface AlPerder {
        void perdido();
    }

    private static FocoAudio compartido;

    private final AudioManager audio;
    private final Map<Object, AlPerder> duenos = new IdentityHashMap<>();
    private final AudioManager.OnAudioFocusChangeListener listener = this::alCambiar;
    private boolean concedido;

    private FocoAudio(Context contexto) {
        audio = (AudioManager) contexto.getApplicationContext()
                .getSystemService(Context.AUDIO_SERVICE);
    }

    static synchronized FocoAudio compartido(Context contexto) {
        if (compartido == null) {
            compartido = new FocoAudio(contexto);
        }
        return compartido;
    }

    synchronized boolean retener(Object dueno, AlPerder alPerder) {
        if (dueno == null || alPerder == null || audio == null) {
            return false;
        }
        if (concedido) {
            duenos.put(dueno, alPerder);
            return true;
        }
        int resultado = audio.requestAudioFocus(listener, AudioManager.STREAM_MUSIC,
                AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK);
        if (resultado != AudioManager.AUDIOFOCUS_REQUEST_GRANTED) {
            return false;
        }
        concedido = true;
        duenos.put(dueno, alPerder);
        return true;
    }

    synchronized void soltar(Object dueno) {
        duenos.remove(dueno);
        if (duenos.isEmpty() && concedido) {
            audio.abandonAudioFocus(listener);
            concedido = false;
        }
    }

    synchronized boolean activo() {
        return concedido;
    }

    private void alCambiar(int cambio) {
        Map<Object, AlPerder> avisar = new IdentityHashMap<>();
        synchronized (this) {
            if (cambio == AudioManager.AUDIOFOCUS_LOSS) {
                concedido = false;
                avisar.putAll(duenos);
                duenos.clear();
            } else if (cambio == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT
                    || cambio == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK) {
                avisar.putAll(duenos);
                duenos.clear();
                audio.abandonAudioFocus(listener);
                concedido = false;
            } else {
                return;
            }
        }
        for (AlPerder alPerder : avisar.values()) {
            try {
                alPerder.perdido();
            } catch (RuntimeException fallo) {
                // El foco ya se perdió; todos los demás dueños deben enterarse.
            }
        }
    }
}
