package dev.sandra.cort.movil;

import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class EspecificacionAlarma {
    static final String ALARMA = "alarma";
    static final String TEMPORIZADOR = "temporizador";

    final String tipo;
    final int hora;
    final int minuto;
    final int segundos;
    final int dias;
    final String etiqueta;
    final String texto;
    final boolean valida;
    final String motivo;

    private EspecificacionAlarma(String tipo, int hora, int minuto, int segundos, int dias,
                                 String etiqueta, String texto, boolean valida, String motivo) {
        this.tipo = tipo;
        this.hora = hora;
        this.minuto = minuto;
        this.segundos = segundos;
        this.dias = dias;
        this.etiqueta = etiqueta;
        this.texto = texto;
        this.valida = valida;
        this.motivo = motivo;
    }

    static EspecificacionAlarma parsear(String entrada) {
        String original = entrada == null ? "" : entrada.trim();
        String texto = Cerebro.normaliza(original);
        if (texto.length() > 300) {
            return invalida("el texto de la alarma es demasiado largo", original);
        }
        if (texto.contains("cronometro") || texto.contains("temporizador")) {
            int segundos = duracionEnSegundos(texto);
            if (segundos < 1 || segundos > 86400) {
                return invalida("indica una duración de 1 segundo a 24 horas", original);
            }
            return new EspecificacionAlarma(TEMPORIZADOR, 0, 0, segundos, 0,
                    etiqueta(texto, true), original, true, "");
        }
        return parsearAlarma(texto, original);
    }

    private static EspecificacionAlarma parsearAlarma(String texto, String original) {
        int hora = -1;
        int minuto = 0;
        Matcher numerica = Pattern.compile("(\\d{1,2})\\s*[:.]\\s*(\\d{2})").matcher(original);
        if (numerica.find()) {
            hora = entero(numerica.group(1));
            minuto = entero(numerica.group(2));
        } else {
            Matcher suelta = Pattern.compile("(?:^|\\s)(\\d{1,2})(?:\\s|$)").matcher(texto);
            if (suelta.find()) {
                hora = entero(suelta.group(1));
                minuto = minutos(texto);
            } else {
                hora = numeroEnLetras(texto);
                minuto = minutos(texto);
            }
        }
        if (hora < 0) {
            return invalida("no encontré una hora válida", original);
        }
        boolean doceHoras = texto.contains(" am") || texto.contains(" pm")
                || texto.contains("manana") || texto.contains("tarde") || texto.contains("noche");
        if (doceHoras) {
            if (hora < 1 || hora > 12) {
                return invalida("con am/pm la hora debe estar entre 1 y 12", original);
            }
            if (texto.contains(" pm") || texto.contains("tarde") || texto.contains("noche")) {
                if (hora != 12) hora += 12;
            } else if (hora == 12) {
                hora = 0;
            }
        }
        if (hora > 23 || minuto > 59) {
            return invalida("la hora o los minutos están fuera de rango", original);
        }
        return new EspecificacionAlarma(ALARMA, hora, minuto, 0, dias(texto),
                etiqueta(texto, false), original, true, "");
    }

    private static int minutos(String texto) {
        if (texto.contains("y media") || texto.contains("media")) return 30;
        if (texto.contains("y cuarto") || texto.contains("cuarto")) return 15;
        Matcher m = Pattern.compile("y\\s+(\\d{1,2})(?:\\s|$)").matcher(texto);
        return m.find() ? entero(m.group(1)) : 0;
    }

    private static int dias(String texto) {
        if (texto.contains("todos los dias") || texto.contains("cada dia")) {
            return 0b1111111;
        }
        if (texto.contains("entre semana")) return 0b0111110;
        if (texto.contains("fin de semana")) return 0b1000001;
        int mascara = 0;
        String[] nombres = {"domingo", "lunes", "martes", "miercoles", "jueves",
                "viernes", "sabado"};
        for (int i = 0; i < nombres.length; i++) {
            if (texto.contains(nombres[i])) mascara |= 1 << i;
        }
        return mascara;
    }

    private static String etiqueta(String texto, boolean temporizador) {
        Matcher m = Pattern.compile("(?:llamada|llamado|nombre|con nombre|que diga)"
                + "(?:\\s+es|\\s+de|\\s+con\\s+el\\s+nombre\\s+de)?\\s+(.+)$").matcher(texto);
        if (!m.find()) return temporizador ? "CORT" : "Alarma de CORT";
        String valor = m.group(1).replaceAll("\\s+(?:todos los dias|cada dia|entre semana|fin de semana"
                + "|domingo|lunes|martes|miercoles|jueves|viernes|sabado)(?:\\s+y\\s+"
                + "(?:domingo|lunes|martes|miercoles|jueves|viernes|sabado))*$", "").trim();
        if (valor.isEmpty()) return temporizador ? "CORT" : "Alarma de CORT";
        return valor.substring(0, Math.min(80, valor.length()));
    }

    static int duracionEnSegundos(String texto) {
        Matcher m = Pattern.compile("(\\d+)\\s*(hora|horas|minuto|minutos|min|segundo|segundos|s)")
                .matcher(texto);
        long total = 0L;
        while (m.find()) {
            long cantidad = entero(m.group(1));
            String unidad = m.group(2);
            if (unidad.startsWith("h")) total += cantidad * 3600L;
            else if (unidad.startsWith("m")) total += cantidad * 60L;
            else total += cantidad;
            if (total > 86400L) return 86401;
        }
        return (int) Math.min(86401L, total);
    }

    private static final String[] NUMEROS = {"uno", "dos", "tres", "cuatro", "cinco", "seis",
            "siete", "ocho", "nueve", "diez", "once", "doce"};

    private static int numeroEnLetras(String texto) {
        Matcher contextual = Pattern.compile(
                "(?:a|para)\\s+las?\\s+(una|un|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce)(?:\\s|$)")
                .matcher(texto);
        if (contextual.find()) return indiceNumero(contextual.group(1));
        for (int i = 0; i < NUMEROS.length; i++) {
            if (texto.matches(".*\\b" + NUMEROS[i] + "\\b.*")) return i + 1;
        }
        return texto.matches(".*\\b(?:una|un)\\b.*") ? 1 : -1;
    }

    private static int indiceNumero(String palabra) {
        if ("una".equals(palabra) || "un".equals(palabra) || "uno".equals(palabra)) return 1;
        for (int i = 1; i < NUMEROS.length; i++) {
            if (NUMEROS[i].equals(palabra)) return i + 1;
        }
        return -1;
    }

    private static int entero(String texto) {
        try {
            return Integer.parseInt(texto);
        } catch (NumberFormatException error) {
            return -1;
        }
    }

    private static EspecificacionAlarma invalida(String motivo, String original) {
        return new EspecificacionAlarma(ALARMA, 0, 0, 0, 0, "", original, false, motivo);
    }

    String resumen() {
        if (!valida) return motivo;
        if (TEMPORIZADOR.equals(tipo)) {
            return "Temporizador de " + segundos + " segundos para «" + etiqueta + "».";
        }
        return String.format(Locale.ROOT, "Alarma a las %02d:%02d para «%s»%s.",
                hora, minuto, etiqueta, dias == 0 ? "" : " en los días indicados");
    }
}
