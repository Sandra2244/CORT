package dev.sandra.cort.movil;

import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.RemoteException;
import android.speech.RecognitionService;
import android.speech.SpeechRecognizer;

import java.util.ArrayList;
import java.util.Locale;

/** El oído que Android invoca cuando CORT es la aplicación de asistencia. */
public class Reconocimiento extends RecognitionService {
    private static volatile Reconocimiento instancia;

    private final Handler principal = new Handler(Looper.getMainLooper());
    private Voz voz;
    private Callback oyente;
    private boolean escuchando;
    private long generacion;

    @Override
    public void onCreate() {
        super.onCreate();
        instancia = this;
        voz = new Voz(this);
    }

    @Override
    protected void onStartListening(Intent recognizerIntent, Callback listener) {
        principal.post(() -> empezar(listener));
    }

    private void empezar(Callback listener) {
        cancelar(false);
        if (voz == null) {
            fallar(listener, SpeechRecognizer.ERROR_CLIENT,
                    "el oído de CORT todavía no está listo");
            return;
        }
        if (checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            fallar(listener, SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS,
                    "falta el permiso de micrófono para el asistente");
            return;
        }

        oyente = listener;
        escuchando = true;
        long turno = ++generacion;
        Medios.compartido(this).pausar("el asistente necesita el micrófono");
        VistaRapida.prepararReconocimiento();
        EscuchaEstadoGlobal.pon(EscuchaEstado.ESCUCHANDO_MANDATO, "te escucho");
        try {
            listener.beginningOfSpeech();
        } catch (RemoteException servicioCaido) {
            limpiarTurno(turno);
            return;
        }
        voz.escuchar(this, new Voz.AlOir() {
            @Override
            public void dijo(String texto) {
                principal.post(() -> entregar(texto, turno));
            }

            @Override
            public void fallo(String motivo) {
                principal.post(() -> fallarTurno(turno, motivo));
            }

            @Override
            public void parcial(String texto) {
                if (turno == generacion) VistaRapida.parcial(texto);
            }
        });
    }

    private void entregar(String texto, long turno) {
        if (turno != generacion || !escuchando) return;
        Callback actual = oyente;
        if (texto == null || texto.trim().isEmpty()) {
            fallar(actual, SpeechRecognizer.ERROR_NO_MATCH, "no entendí el mandato");
            VistaRapida.error("no entendí el mandato");
            return;
        }
        oyente = null;
        escuchando = false;
        ArrayList<String> resultados = new ArrayList<>();
        resultados.add(texto);
        Bundle paquete = new Bundle();
        paquete.putStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION, resultados);
        try {
            actual.endOfSpeech();
            actual.results(paquete);
        } catch (RemoteException servicioCaido) {
            // La vista ya recibió el mandato; el servicio del sistema puede haberse ido.
        }
        EscuchaEstadoGlobal.pon(EscuchaEstado.PROCESANDO, "mandato recibido");
        VistaRapida.respuesta(texto);
    }

    private void fallarTurno(long turno, String motivo) {
        if (turno != generacion || !escuchando) return;
        String mensaje = motivo == null || motivo.trim().isEmpty()
                ? "no pude reconocer la voz" : motivo;
        String menor = mensaje.toLowerCase(Locale.ROOT);
        int codigo = menor.contains("permiso") ? SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS
                : menor.contains("red") || menor.contains("internet")
                        ? SpeechRecognizer.ERROR_NETWORK : SpeechRecognizer.ERROR_NO_MATCH;
        fallar(oyente, codigo, mensaje);
        VistaRapida.error(mensaje);
    }

    private void fallar(Callback listener, int codigo, String mensaje) {
        oyente = null;
        escuchando = false;
        generacion++;
        if (voz != null) voz.dejarDeEscuchar();
        if (EscuchaEstadoGlobal.estado() != EscuchaEstado.DETENIDO) {
            EscuchaEstadoGlobal.pon(EscuchaEstado.ERROR, mensaje);
        }
        try {
            listener.error(codigo);
        } catch (RemoteException servicioCaido) {
            // No queda un destinatario al que informar el error.
        }
    }

    @Override
    protected void onCancel(Callback listener) {
        principal.post(() -> cancelar(true));
    }

    @Override
    protected void onStopListening(Callback listener) {
        principal.post(() -> cancelar(true));
    }

    private void cancelar(boolean avisar) {
        Callback anterior = oyente;
        boolean habiaEscucha = escuchando;
        oyente = null;
        escuchando = false;
        generacion++;
        if (voz != null) voz.dejarDeEscuchar();
        if (habiaEscucha && EscuchaEstadoGlobal.estado() != EscuchaEstado.DETENIDO) {
            EscuchaEstadoGlobal.pon(EscuchaEstado.DETENIDO, "reconocimiento detenido");
        }
        if (avisar && habiaEscucha && anterior != null) {
            try {
                anterior.error(SpeechRecognizer.ERROR_CLIENT);
            } catch (RemoteException servicioCaido) {
                // La cancelación local ya terminó la captura.
            }
        }
    }

    private void limpiarTurno(long turno) {
        if (turno == generacion) cancelar(false);
    }

    static boolean activa() {
        Reconocimiento servicio = instancia;
        return servicio != null && servicio.escuchando;
    }

    static void cancelar() {
        Reconocimiento servicio = instancia;
        if (servicio != null) servicio.principal.post(() -> servicio.cancelar(false));
    }

    @Override
    public void onDestroy() {
        principal.post(() -> {
            cancelar(false);
            if (voz != null) voz.cerrar();
            voz = null;
            if (instancia == this) instancia = null;
        });
        super.onDestroy();
    }
}
