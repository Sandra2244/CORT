package dev.sandra.cort.movil;

import java.util.concurrent.CopyOnWriteArrayList;

enum EscuchaEstado {
    APAGADO,
    PIDIENDO_PERMISO,
    PREPARANDO,
    ESCUCHANDO_PALABRA,
    ESCUCHANDO_MANDATO,
    PROCESANDO,
    DETENIDO,
    ERROR;

    String alambre() {
        return name().toLowerCase(java.util.Locale.ROOT);
    }

    boolean activa() {
        return this == PREPARANDO || this == ESCUCHANDO_PALABRA
                || this == ESCUCHANDO_MANDATO || this == PROCESANDO;
    }
}

final class EscuchaEstadoGlobal {
    interface Oyente {
        void cambio(EscuchaEstado estado, String motivo);
    }

    private static final CopyOnWriteArrayList<Oyente> OYENTES = new CopyOnWriteArrayList<>();
    private static volatile EscuchaEstado actual = EscuchaEstado.APAGADO;
    private static volatile String motivoActual = "";

    private EscuchaEstadoGlobal() {
    }

    static EscuchaEstado estado() {
        return actual;
    }

    static String motivo() {
        return motivoActual;
    }

    static void pon(EscuchaEstado estado, String motivo) {
        if (estado == null) {
            throw new IllegalArgumentException("estado de escucha nulo");
        }
        String limpio = motivo == null ? "" : motivo;
        if (actual == estado && motivoActual.equals(limpio)) {
            return;
        }
        actual = estado;
        motivoActual = limpio;
        for (Oyente oyente : OYENTES) {
            try {
                oyente.cambio(estado, limpio);
            } catch (RuntimeException fallo) {
                // Un observador no puede impedir que el micrófono se detenga.
            }
        }
    }

    static void observar(Oyente oyente) {
        if (oyente != null && !OYENTES.contains(oyente)) {
            OYENTES.add(oyente);
        }
    }

    static void desobservar(Oyente oyente) {
        OYENTES.remove(oyente);
    }
}
