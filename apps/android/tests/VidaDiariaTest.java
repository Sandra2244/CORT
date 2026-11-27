package dev.sandra.cort.movil;

public final class VidaDiariaTest {
    private static int comprobadas;

    public static void main(String[] args) {
        alarma("alarma a las 7:30", 7, 30, 0);
        alarma("alarma a las 7.30 de la tarde", 19, 30, 0);
        alarma("alarma a las siete y media", 7, 30, 0);
        alarma("pon una alarma a las siete", 7, 0, 0);
        alarma("alarma para la una de la mañana", 1, 0, 0);
        alarma("alarma a la una de la mañana", 1, 0, 0);
        alarma("alarma a las 12 am", 0, 0, 0);
        alarma("alarma a las 12 pm", 12, 0, 0);
        alarma("alarma a las 7 y cuarto", 7, 15, 0);
        alarma("alarma a las 7 y 45", 7, 45, 0);
        alarma("alarma a las 6:15 llamada despertar lunes y martes", 6, 15, 0b110);
        alarma("alarma a las 8 todos los días", 8, 0, 0b1111111);
        alarma("alarma a las 9 entre semana", 9, 0, 0b0111110);
        alarma("alarma a las 10 fin de semana", 10, 0, 0b1000001);
        invalida("alarma a las 25:00");
        invalida("alarma a las 7:75");
        invalida("alarma sin hora");
        invalida("alarma a las 13 pm");

        temporizador("temporizador de 5 minutos y 30 segundos", 330);
        temporizador("cronómetro de 1 hora y 5 minutos", 3900);
        temporizador("temporizador de 90 segundos", 90);
        invalida("temporizador de 0 minutos");
        invalida("temporizador de 25 horas");
        invalida("temporizador sin duración");

        EspecificacionAlarma etiquetada = EspecificacionAlarma.parsear(
                "alarma a las 6:30 llamada despertar lunes");
        verdad(etiquetada.valida, "alarma etiquetada válida");
        verdad("despertar".equals(etiquetada.etiqueta), "etiqueta sin día pegado");

        aprobaciones();
        politicaRutinas();
        System.out.println("VidaDiariaTest: " + comprobadas + " comprobaciones");
    }

    private static void alarma(String texto, int hora, int minuto, int dias) {
        EspecificacionAlarma especificacion = EspecificacionAlarma.parsear(texto);
        verdad(especificacion.valida, "alarma válida: " + texto + " · " + especificacion.motivo);
        verdad(EspecificacionAlarma.ALARMA.equals(especificacion.tipo), "tipo alarma: " + texto);
        verdad(especificacion.hora == hora, "hora: " + texto);
        verdad(especificacion.minuto == minuto, "minuto: " + texto);
        verdad(especificacion.dias == dias, "días: " + texto);
    }

    private static void temporizador(String texto, int segundos) {
        EspecificacionAlarma especificacion = EspecificacionAlarma.parsear(texto);
        verdad(especificacion.valida, "temporizador válido: " + texto + " · " + especificacion.motivo);
        verdad(EspecificacionAlarma.TEMPORIZADOR.equals(especificacion.tipo), "tipo temporizador: " + texto);
        verdad(especificacion.segundos == segundos, "duración: " + texto);
    }

    private static void invalida(String texto) {
        EspecificacionAlarma especificacion = EspecificacionAlarma.parsear(texto);
        falso(especificacion.valida, "entrada inválida rechazada: " + texto);
        verdad(especificacion.motivo != null && !especificacion.motivo.isEmpty(), "motivo explícito: " + texto);
    }

    private static void aprobaciones() {
        Aprobaciones aprobaciones = new Aprobaciones("sesion-a");
        String token = aprobaciones.preparar("memoria", "editar", "nombre", "2", "Ana");
        verdad(token != null && !token.isEmpty(), "token de memoria");
        falso(aprobaciones.consumir("rutinas", "editar", "nombre", "2", "Ana", token),
                "otra capacidad no consume el token");
        falso(aprobaciones.consumir("memoria", "editar", "nombre", "2", "Ana", token),
                "token consumido una sola vez");
        String otroValor = aprobaciones.preparar("memoria", "editar", "nombre", "2", "Ana");
        falso(aprobaciones.consumir("memoria", "editar", "nombre", "2", "Otra", otroValor),
                "el valor debe coincidir con lo confirmado");
        String otro = aprobaciones.preparar("memoria", "borrar", "nombre", "2", "");
        verdad(aprobaciones.consumir("memoria", "borrar", "nombre", "2", "", otro),
                "confirmación exacta");
        String revocar = aprobaciones.preparar("memoria", "editar", "ciudad", "1", "Madrid");
        verdad(aprobaciones.revocar(revocar), "confirmación revocable");
        falso(aprobaciones.consumir("memoria", "editar", "ciudad", "1", "Madrid", revocar),
                "token revocado no se consume");
        String cerrar = aprobaciones.preparar("memoria", "editar", "ciudad", "1", "Madrid");
        aprobaciones.cerrar();
        falso(aprobaciones.consumir("memoria", "editar", "ciudad", "1", "Madrid", cerrar),
                "cerrar sesión invalida tokens");
        verdad(aprobaciones.preparar(null, "editar", "nombre", "2", "Ana") == null,
                "capacidad nula rechazada");
    }

    private static void politicaRutinas() {
        verdad(Rutinas.Paso.informativa("hora"), "hora informativa");
        verdad(Rutinas.Paso.informativa("decir"), "frase informativa");
        falso(Rutinas.Paso.informativa("linterna"), "linterna requiere confirmación");
        verdad("bajo".equals(Rutinas.Paso.riesgoCalculado("listar")), "riesgo informativo");
        verdad("medio".equals(Rutinas.Paso.riesgoCalculado("linterna")), "riesgo linterna");
        verdad("CAMERA".equals(Rutinas.Paso.permisoCalculado("linterna")), "permiso linterna");
        verdad("MODIFY_AUDIO_SETTINGS".equals(Rutinas.Paso.permisoCalculado("volumen")),
                "permiso volumen");
        verdad(paso("hora", "", "").error() == null, "paso hora permitido");
        verdad(paso("decir", "", "Buenos días").error() == null, "paso decir permitido");
        verdad(paso("abrir", "reloj", "").error() == null, "destino reloj permitido");
        verdad(paso("abrir", "cualquier app", "").error() != null, "app arbitraria rechazada");
        verdad(paso("volumen", "subir", "").error() == null, "volumen permitido");
        verdad(paso("volumen", "999", "").error() != null, "volumen arbitrario rechazado");
        verdad(paso("linterna", "encender", "").error() == null, "linterna permitida");
        verdad(paso("linterna", "parpadear", "").error() != null, "linterna arbitraria rechazada");
        verdad(paso("alarma", "", "a las 7:30").error() == null, "alarma válida en rutina");
        verdad(paso("cronometro", "", "5 minutos").error() == null, "temporizador válido en rutina");
        for (String accion : new String[] {"llamar", "guardar", "shell", "mensaje", "comprar"}) {
            verdad(paso(accion, "", "").error() != null, "acción sensible rechazada: " + accion);
        }
        Rutinas.Reto reto = new Rutinas.Reto("rutina-a", 2, "token-a", 500L);
        verdad(Rutinas.retoCoincide(reto, "rutina-a", "token-a"), "plan de rutina exacto");
        falso(Rutinas.retoCoincide(reto, "rutina-b", "token-a"), "otra rutina no coincide");
        falso(Rutinas.retoCoincide(reto, "rutina-a", "token-b"), "otro token no coincide");
        falso(Rutinas.retoCoincide(null, "rutina-a", "token-a"), "plan ausente no coincide");
    }

    private static Rutinas.Paso paso(String accion, String param, String resto) {
        return new Rutinas.Paso(accion, param, resto, "", "bajo", "ninguno", false,
                "CORT", "proyecto CORT", "licencia del proyecto");
    }

    private static void verdad(boolean valor, String nombre) {
        comprobadas++;
        if (!valor) throw new AssertionError(nombre);
    }

    private static void falso(boolean valor, String nombre) {
        comprobadas++;
        if (valor) throw new AssertionError(nombre);
    }
}
