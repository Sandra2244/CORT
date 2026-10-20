package com.cort.ia;

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
 * `recognitionService`, con el error «No recognitionService specified». Sin
 * esta clase CORT ni aparece en la lista de «aplicación de asistencia
 * predeterminada».
 *
 * Pero un `RecognitionService` de verdad necesita un modelo que convierta audio
 * en texto dentro de su propio proceso, y eso no cabe: el APK se compila con
 * `javac` + `d8` sin Gradle ni dependencias, y el portátil de la dueña (1,8 GiB)
 * ya se congeló con un `gradle build`.
 *
 * Entonces hace lo honesto: **cede el oído**. Abre la cara de CORT pidiéndole
 * que escuche por el `SpeechRecognizer` del aparato — el mismo que usa el puente
 * `CortNative.java` — y cierra su propia petición con el código que Android
 * define para «aquí no hay texto que leer» (`SpeechRecognizer.ERROR_NO_MATCH`).
 * La dueña ve a CORT escuchando; lo que no ve es un hotword propio.
 */
public class Reconocimiento extends RecognitionService {

    @Override
    protected void onStartListening(Intent recognizerIntent, Callback listener) {
        Intent abrir = new Intent(this, MainActivity.class)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
                .putExtra(MainActivity.PIDE_ESCUCHAR, true);
        startActivity(abrir);
        // `Callback.error(int)` **declara** `throws RemoteException`: el Callback es
        // un proxy al proceso del servicio de voz del sistema, y si ese proceso se
        // cayó no hay a quién avisarle. Omitir el `try` es un rojo de `javac`.
        try {
            listener.error(SpeechRecognizer.ERROR_NO_MATCH);
        } catch (RemoteException caraYaPidiendo) {
            // La cara ya está abierta y ya está pidiendo el micrófono.
        }
    }

    @Override
    protected void onCancel(Callback listener) {
        // Nada que soltar: en este proceso no hay audio abierto.
    }

    @Override
    protected void onStopListening(Callback listener) {
        // Idem. Los tres van escritos porque son los abstractos de
        // `RecognitionService`, y omitir uno es `javac` rojo en el runner.
    }
}
