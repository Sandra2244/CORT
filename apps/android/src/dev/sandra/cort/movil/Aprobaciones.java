package dev.sandra.cort.movil;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

final class Aprobaciones {
    private static final long DURACION_MS = 120_000L;

    private static final class Reto {
        final String sesion;
        final String capacidad;
        final String accion;
        final String id;
        final String version;
        final String valor;
        final long expira;
        final String token;

        Reto(String sesion, String capacidad, String accion, String id, String version,
             String valor, long expira, String token) {
            this.sesion = sesion;
            this.capacidad = capacidad;
            this.accion = accion;
            this.id = id;
            this.version = version;
            this.valor = valor;
            this.expira = expira;
            this.token = token;
        }
    }

    private final String sesion;
    private final Map<String, Reto> retos = new HashMap<>();

    Aprobaciones(String sesion) {
        this.sesion = sesion;
    }

    synchronized String preparar(String capacidad, String accion, String id, String version,
                                 String valor) {
        if (sesion == null || capacidad == null || accion == null || id == null || version == null) {
            return null;
        }
        String token = UUID.randomUUID().toString();
        retos.put(token, new Reto(sesion, capacidad, accion, id, version,
                valor == null ? "" : valor, System.currentTimeMillis() + DURACION_MS, token));
        return token;
    }

    synchronized boolean consumir(String capacidad, String accion, String id, String version,
                                  String valor, String token) {
        if (token == null) return false;
        Reto reto = retos.remove(token);
        String propuesto = valor == null ? "" : valor;
        return reto != null && reto.expira >= System.currentTimeMillis()
                && sesion.equals(reto.sesion) && capacidad.equals(reto.capacidad)
                && accion.equals(reto.accion) && id.equals(reto.id) && version.equals(reto.version)
                && propuesto.equals(reto.valor);
    }

    synchronized boolean revocar(String token) {
        return token != null && retos.remove(token) != null;
    }

    synchronized void cerrar() {
        retos.clear();
    }
}
