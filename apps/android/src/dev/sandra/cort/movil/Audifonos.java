package dev.sandra.cort.movil;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.media.AudioDeviceCallback;
import android.media.AudioDeviceInfo;
import android.media.AudioManager;

/**
 * El sensor de audífonos detecta salidas compatibles. Android decide la ruta
 * activa; con varias salidas conectadas CORT no afirma cuál está sonando.
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

    /** Qué salidas están detectadas, sin afirmar cuál eligió Android. */
    public static int cantidad(AudioManager gestor) {
        if (gestor == null) return 0;
        int total = 0;
        for (AudioDeviceInfo dispositivo : gestor.getDevices(AudioManager.GET_DEVICES_OUTPUTS)) {
            switch (dispositivo.getType()) {
                case AudioDeviceInfo.TYPE_WIRED_HEADPHONES:
                case AudioDeviceInfo.TYPE_WIRED_HEADSET:
                case AudioDeviceInfo.TYPE_USB_HEADSET:
                case AudioDeviceInfo.TYPE_BLUETOOTH_A2DP:
                case AudioDeviceInfo.TYPE_BLUETOOTH_SCO:
                    total++;
                    break;
                default:
                    break;
            }
        }
        return total;
    }

    public static String salida(AudioManager gestor) {
        if (cantidad(gestor) > 1) {
            return "varias salidas detectadas; Android no confirma la activa";
        }
        switch (estado(gestor)) {
            case CON_CABLE:
                return "audífonos de cable detectados; Android decide la ruta";
            case POR_BLUETOOTH:
                return "audífonos Bluetooth detectados; Android decide la ruta";
            default:
                return "sin auriculares detectados; Android decide la salida";
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
