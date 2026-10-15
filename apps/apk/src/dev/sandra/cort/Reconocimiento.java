package dev.sandra.cort;

import android.content.Intent;
import android.os.RemoteException;
import android.speech.RecognitionService;
import android.speech.SpeechRecognizer;

/**
 * El servicio de reconocimiento que el contrato de `VoiceInteractionService`
 * **exige** y que CORT no puede cumplir del todo.
 *
 * Por qué existe este archivo, dicho sin adornos: `VoiceInteractionServiceInfo`
 * (AOSP) rechaza la meta-datos de un asistente si no trae `sessionService` **y**
 * `recognitionService`, y devuelve el error de parseo «No recognitionService
 * specified». O sea: sin esta clase, CORT ni siquiera aparece en la lista de
 * «aplicación de asistencia predeterminada» del teléfono.
 *
 * Pero un `RecognitionService` de verdad necesita un modelo que convierta audio
 * en texto dentro del proceso, y eso no cabe aquí: el APK se compila con
 * `javac`+`d8` sin Gradle ni dependencias (`apps/apk/compilar.sh`), la regla 7
 * prohíbe meter modelos pesados en el repo, y el portátil de la dueña — 1,8 GiB
 * de RAM — ya congeló con un `gradle build` (medido, `docs/PLATFORM.md`).
 *
 * Lo que hace entonces es lo honesto: **ceder el oído**. Abre la cara de CORT
 * pidiéndole que escuche por el `SpeechRecognizer` del aparato — el mismo que
 * funciona desde `v0.15.0` — y termina su propia petición con el código de error
 * que Android define para «aquí no hay texto que leer»
 * (`SpeechRecognizer.ERROR_NO_MATCH`, que es de las constantes verificadas en
 * `apps/apk/simbolos-android.json`). El usuario ve la cara de CORT escuchando;
 * lo que **no** ve es un hotword propio, y `docs/PLATFORM.md` lo dice en su
 * sitio: «sin verificar en dedo».
 */
public class Reconocimiento extends RecognitionService {

    @Override
    protected void onStartListening(Intent recognizerIntent, Callback listener) {
        Intent abrir = new Intent(this, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
                .putExtra(MainActivity.PIDE_ESCUCHAR, true);
        startActivity(abrir);
        // `Callback.error(int)` **declara** `throws RemoteException` en AOSP: el
        // `Callback` es un proxy a otro proceso (el del servicio de voz del sistema),
        // y si ese proceso se cayó antes de oír el código no hay a quién avisarle.
        // El run 38812262724 de `compilar-apk` se cayó justo aquí —«unreported
        // exception RemoteException; must be caught or declared to be thrown»— y dejó
        // `v0.15.4` publicado sin APK. Aquí no hay `javac`, así que el `throws` de cada
        // método lo vigila `lanza-android.json` con sus pruebas en
        // `test_apk_manifesta.py`.
        try {
            listener.error(SpeechRecognizer.ERROR_NO_MATCH);
        } catch (RemoteException caraYaPidiendo) {
            // No hay nada que hacer: la cara ya está abierta y ya está pidiendo el
            // micrófono. Avisar al servicio de voz del sistema era un extra, y si su
            // proceso se cayó antes, ya no hay a quién.
        }
    }

    @Override
    protected void onCancel(Callback listener) {
        // Nada que soltar: no hay grabación abierta en este proceso.
    }

    @Override
    protected void onStopListening(Callback listener) {
        // Idem. Se escriben los dos vacíos en vez de omitirlos porque son los tres
        // métodos abstractos que `RecognitionService` declara en AOSP, y omitir uno
        // es un `javac` rojo en el runner.
    }
}
