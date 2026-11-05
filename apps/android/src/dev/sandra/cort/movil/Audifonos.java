package dev.sandra.cort.movil;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.media.AudioDeviceInfo;
import android.media.AudioManager;
import android.media.AudioManager.AudioDeviceCallback;

/**
 * El sensor de audífonos. CORT habla al oído por el receptor del teléfono, pero si
 * la dueña lleva auriculares puestos la voz tiene que salir por ahí y no por el
 * auricular de la oreja ni por el altavoz de la casa.
 *
 * Se lee el estado con `getDevices` (API 23) y los cambios con `AudioDeviceCallback`,
 * que es lo único que avisa también del Bluetooth; el `ACTION_AUDIO_BECOMING_NOISY` del
 * receptor llega cuando se suelta el cable **mientras algo está sonando**, que es el
 * caso en el que el teléfono se queda hablando solo por el altavoz de la casa. Ninguno
 * de los dos pide permiso.
 */
public final class Audifonos {

    /** Nombre corto de la salida, para imprimirlo en pantalla. */
    public static final int SIN_AUDIFONOS = 0;
    public static final int CON_CABLE = 1;
    public static final int POR_BLUETOOTH = 2;

    private Audifonos() {
    }

    public static int estado(AudioManager gestor) {
        if (gestor == null) {
            return SIN_AUDIFONOS;
        }
        AudioDeviceInfo[] salida = gestor.getDevices(AudioManager.GET_DEVICES_OUTPUTS);
        for (AudioDeviceInfo dispositivo : salida) {
            switch (dispositivo.getType()) {
                case AudioDeviceInfo.TYPE_WIRED_HEADPHONES:
                case AudioDeviceInfo.TYPE_WIRED_HEADSET:
                case AudioDeviceInfo.TYPE_USB_HEADSET:
                    return CON_CABLE;
                case AudioDeviceInfo.TYPE_BLUETOOTH_A2DP:
                case AudioDeviceInfo.TYPE_BLUETOOTH_SCO:
                    return POR_BLUETOOTH;
                default:
                    break;
            }
        }
        return SIN_AUDIFONOS;
    }

    public static boolean hay(AudioManager gestor) {
        return estado(gestor) != SIN_AUDIFONOS;
    }

    /** Dónde va a sonar la próxima frase, dicho con palabras. */
    public static String salida(AudioManager gestor) {
        switch (estado(gestor)) {
            case CON_CABLE:
                return "los audífonos de cable";
            case POR_BLUETOOTH:
                return "los audífonos Bluetooth";
            default:
                return "el auricular del teléfono";
        }
    }

    /** Aviso de que la salida cambió: quien escucha vuelve a leer `estado`. */
    public interface AlCambiar {
        void cambioDeSalida();
    }

    /** El alta y el baja por cable: un receptor de contexto, sin permiso y sin servicio. */
    public static class Receptor extends BroadcastReceiver {
        private final AlCambiar alCambiar;

        public Receptor(AlCambiar alCambiar) {
            this.alCambiar = alCambiar;
        }

        @Override
        public void onReceive(Context contexto, Intent orden) {
            alCambiar.cambioDeSalida();
        }

        public static IntentFilter filtro() {
            return new IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY);
        }
    }

    /** El alta y el baja de todo, Bluetooth incluido (API 23; el mínimo de la rama es 26). */
    public static class Cambios extends AudioDeviceCallback {
        private final AlCambiar alCambiar;

        public Cambios(AlCambiar alCambiar) {
            this.alCambiar = alCambiar;
        }

        @Override
        public void onAudioDevicesAdded(AudioDeviceInfo[] anadidos) {
            alCambiar.cambioDeSalida();
        }

        @Override
        public void onAudioDevicesRemoved(AudioDeviceInfo[] quitados) {
            alCambiar.cambioDeSalida();
        }
    }
}
