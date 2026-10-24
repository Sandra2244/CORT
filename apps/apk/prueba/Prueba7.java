package com.cort.ia;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.TimeZone;

/* F16 · «despiértame a las 7 con After Dark para el examen»: la decisión de QUÉ
   hora, QUÉ canción y QUÉ nota, y CUÁNDO toca el próximo disparo. `Despertar` es
   Java puro, así que se mide aquí con el JDK; `Alarma` (AlarmManager, notificación)
   sólo se puede mirar en un teléfono y no se finge probada.

   Cada comprobación puede CAER: si el parser se comiera la canción, la de la nota
   se pone roja; si `proximo` devolviera una hora pasada, la de «ya pasó» también. */
public class Prueba7 {
    static int fallos = 0, casos = 0;
    static final ZoneId ZONA = ZoneId.of("Europe/Madrid");
    static final TimeZone TZ = TimeZone.getTimeZone("Europe/Madrid");

    static void check(String que, boolean vale, String detalle) {
        casos++;
        if (vale) System.out.println("ok     " + que);
        else { fallos++; System.out.println("FALLO  " + que + "   (" + detalle + ")"); }
    }

    static String plan(Despertar.Plan p) { return p == null ? "—" : p.toString(); }

    static long ms(int y, int mo, int d, int h, int mi) {
        return LocalDateTime.of(y, mo, d, h, mi).atZone(ZONA).toInstant().toEpochMilli();
    }

    public static void main(String[] a) {
        // 1 · la hora sola, con dos puntos
        Despertar.Plan p = Despertar.parte("pon una alarma a las 7:30");
        check("7:30 a secas", p != null && p.hora == 7 && p.minuto == 30
              && p.cancion.isEmpty() && p.nota.isEmpty(), plan(p));

        // 2 · la hora sola, suelta
        p = Despertar.parte("despiertame a las 8");
        check("las 8", p != null && p.hora == 8 && p.minuto == 0, plan(p));

        // 3 · «y media» / «y cuarto» no se pierden
        p = Despertar.parte("a las 7 y media");
        check("7 y media", p != null && p.hora == 7 && p.minuto == 30, plan(p));
        p = Despertar.parte("a las 7 y cuarto con after dark");
        check("7 y cuarto con canción", p != null && p.hora == 7 && p.minuto == 15
              && "after dark".equals(p.cancion), plan(p));

        // 4 · la canción detrás de «con»
        p = Despertar.parte("pon una alarma a las 7:30 con after dark");
        check("la canción se oye", p != null && "after dark".equals(p.cancion), plan(p));

        // 5 · canción y nota, cada una en su sitio
        p = Despertar.parte("despiertame a las 6:15 con la cancion noche de synth para el examen");
        check("canción y nota juntas", p != null && "noche de synth".equals(p.cancion)
              && "el examen".equals(p.nota), plan(p));

        // 6 · una nota sin canción
        p = Despertar.parte("despiertame a las 6 para el tren");
        check("nota sin canción", p != null && p.cancion.isEmpty()
              && "el tren".equals(p.nota), plan(p));

        // 7 · «buenos días» enciende la rutina y no se cuela en la nota
        p = Despertar.parte("buenos dias a las 6 con after dark");
        check("la rutina se enciende", p != null && p.rutina && "after dark".equals(p.cancion)
              && p.nota.isEmpty(), plan(p));

        // 8 · sin hora no hay alarma (mejor preguntar que despertar a las 0:00)
        p = Despertar.parte("pon una alarma");
        check("sin hora no hay plan", p == null, plan(p));
        p = Despertar.parte("a las 25");
        check("25 no es una hora", p == null, plan(p));

        // 9 · la tilde no separa
        p = Despertar.parte("despiértame a las 7 con la canción Canción de cuna");
        check("tildes y mayúsculas", p != null && "cancion de cuna".equals(p.cancion), plan(p));

        // 10 · el próximo disparo: hoy si aún no ha pasado
        long ahora = ms(2026, 10, 24, 6, 0);
        long cuando = Despertar.proximo(7, 30, ahora, TZ);
        check("hoy a las 7:30", cuando == ms(2026, 10, 24, 7, 30),
              String.valueOf(cuando - ahora));

        // 11 · si ya pasó, mañana
        ahora = ms(2026, 10, 24, 8, 0);
        cuando = Despertar.proximo(7, 30, ahora, TZ);
        check("mañana a las 7:30", cuando == ms(2026, 10, 25, 7, 30),
              String.valueOf(cuando - ahora));

        // 12 · justo ahora también es mañana: la alarma no se dispara dos veces
        ahora = ms(2026, 10, 24, 7, 30);
        check("justo ahora → mañana", Despertar.proximo(7, 30, ahora, TZ)
              == ms(2026, 10, 25, 7, 30), "strictamente después");

        // 13 · el cambio de hora de octubre (02:30 existe dos veces): la hora local
        //      sigue siendo 2:30 y el instante es futuro.
        ahora = ms(2026, 10, 24, 12, 0);
        cuando = Despertar.proximo(2, 30, ahora, TZ);
        ZonedDateTime enZona = java.time.Instant.ofEpochMilli(cuando).atZone(ZONA);
        check("DST de octubre", cuando > ahora && enZona.getHour() == 2
              && enZona.getMinute() == 30, enZona.toString());

        // 14 · el salto de marzo (02:30 no existe): nunca devuelve el pasado y la
        //      hora local cae en el hueco que el reloj sí tiene.
        ahora = ms(2026, 3, 28, 12, 0);
        cuando = Despertar.proximo(2, 30, ahora, TZ);
        enZona = java.time.Instant.ofEpochMilli(cuando).atZone(ZONA);
        check("DST de marzo", cuando > ahora && enZona.getHour() >= 2
              && enZona.getHour() <= 3, enZona.toString());

        // 15 · lo que falta, dicho en palabras
        check("falta en horas", "en 8 h 5 min".equals(Despertar.falta(
              ms(2026, 10, 24, 15, 5), ms(2026, 10, 24, 7, 0))), "8 h 5 min");
        check("falta menos de una hora", "en 1 min".equals(Despertar.falta(
              ms(2026, 10, 24, 7, 1), ms(2026, 10, 24, 7, 0))), "1 min");
        check("falta nunca es negativo", "en 0 min".equals(Despertar.falta(
              ms(2026, 10, 24, 7, 0), ms(2026, 10, 24, 9, 0))), "0 min");

        // 16 · los dos puntos sobreviven al plegado (si no, no habría hora)
        p = Despertar.parte("ALARMA A LAS 07:30");
        check("mayúsculas y dos puntos", p != null && p.hora == 7 && p.minuto == 30, plan(p));

        // 17 · «con la canción» sin nombre no inventa una canción
        p = Despertar.parte("despiertame a las 6 con la cancion");
        check("sin nombre no hay canción", p != null && p.cancion.isEmpty(), plan(p));

        System.out.println("\n" + (casos - fallos) + "/" + casos
                + " comprobaciones de Despertar; fallos=" + fallos);
        System.exit(fallos == 0 ? 0 : 1);
    }
}
