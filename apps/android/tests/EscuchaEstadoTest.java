package dev.sandra.cort.movil;

import java.util.ArrayList;
import java.util.List;

public final class EscuchaEstadoTest {
    private static int comprobaciones;

    public static void main(String[] args) {
        alambre();
        actividad();
        observador();
        System.out.println("EscuchaEstadoTest: " + comprobaciones + " comprobaciones");
    }

    private static void alambre() {
        si(EscuchaEstado.APAGADO.alambre().equals("apagado"), "APAGADO viaja en minúsculas");
        si(EscuchaEstado.ESCUCHANDO_MANDATO.alambre().equals("escuchando_mandato"),
                "ESCUCHANDO_MANDATO viaja completo");
        si(EscuchaEstado.ERROR.alambre().equals("error"), "ERROR viaja en minúsculas");
    }

    private static void actividad() {
        si(!EscuchaEstado.APAGADO.activa(), "apagado no está activo");
        si(!EscuchaEstado.DETENIDO.activa(), "detenido no está activo");
        si(!EscuchaEstado.ERROR.activa(), "error no está activo");
        si(!EscuchaEstado.PIDIENDO_PERMISO.activa(), "pedir permiso aún no retiene el micrófono");
        si(EscuchaEstado.PREPARANDO.activa(), "preparando forma parte de la sesión visible");
        si(EscuchaEstado.ESCUCHANDO_PALABRA.activa(), "vigilia activa");
        si(EscuchaEstado.ESCUCHANDO_MANDATO.activa(), "mandato activo");
        si(EscuchaEstado.PROCESANDO.activa(), "procesamiento mantiene la sesión visible");
    }

    private static void observador() {
        EscuchaEstadoGlobal.pon(EscuchaEstado.APAGADO, "");
        List<String> vistos = new ArrayList<>();
        EscuchaEstadoGlobal.Oyente oyente = (estado, motivo) -> vistos.add(
                estado.alambre() + ":" + motivo);
        EscuchaEstadoGlobal.observar(oyente);
        EscuchaEstadoGlobal.pon(EscuchaEstado.PREPARANDO, "cargando");
        EscuchaEstadoGlobal.pon(EscuchaEstado.PREPARANDO, "cargando");
        EscuchaEstadoGlobal.pon(EscuchaEstado.PREPARANDO, "modelo listo");
        EscuchaEstadoGlobal.desobservar(oyente);
        EscuchaEstadoGlobal.pon(EscuchaEstado.ESCUCHANDO_PALABRA, "");
        si(vistos.size() == 2, "no repite el mismo estado y motivo");
        si(vistos.get(0).equals("preparando:cargando"), "entrega estado y motivo");
        si(vistos.get(1).equals("preparando:modelo listo"), "un motivo nuevo sí notifica");
        si(EscuchaEstadoGlobal.estado() == EscuchaEstado.ESCUCHANDO_PALABRA,
                "el estado global queda actualizado sin observador");
        EscuchaEstadoGlobal.pon(EscuchaEstado.APAGADO, "");
    }

    private static void si(boolean condicion, String nombre) {
        comprobaciones++;
        if (!condicion) {
            throw new AssertionError(nombre);
        }
    }
}
