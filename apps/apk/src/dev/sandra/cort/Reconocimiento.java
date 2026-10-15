package dev.sandra.cort;

import android.content.Intent;
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
        listener.error(SpeechRecognizer.ERROR_NO_MATCH);
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
