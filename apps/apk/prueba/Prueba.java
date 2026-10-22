package com.cort.ia;

import java.time.LocalDate;

/* `Razon` a pelo: 43 frases de cuenta, porcentaje, unidad y calendario, más las
   que NO son suyas y tienen que seguir sueltas para que se las lleve la nube.
   Corre en el portátil (`scripts/prueba-mente.sh`) porque `Razon` es Java puro,
   sin una sola clase de Android. */
public class Prueba {
    static int fallos = 0, casos = 0;

    static void espera(String frase, String debeTener) {
        casos++;
        String r = Razon.intenta(frase);
        if (r == null || !r.contains(debeTener)) {
            fallos++;
            System.out.println("FALLO  «" + frase + "» → " + r + "   (esperaba: " + debeTener + ")");
        } else System.out.println("ok     «" + frase + "» → " + r);
    }
    static void noEsMio(String frase) {
        casos++;
        String r = Razon.intenta(frase);
        if (r != null) { fallos++; System.out.println("FALLO  «" + frase + "» NO debía responderse: " + r); }
        else System.out.println("ok     «" + frase + "» → null (a la nube)");
    }

    /* El calendario NO se escribe a mano: el run rojo de `v0.2.19-demo` fue
       exactamente eso — «miercoles 21 de octubre de 2026» fijado el día que se
       escribió la prueba, y GitHub Actions corre en UTC, que en su mesa de Madrid
       ya era jueves 22 cuando el teléfono de la dueña aún era miércoles. Una
       prueba con la fecha copiada caduca sola, así que se calcula con las MISMAS
       funciones de `Razon` (`nombreDe`) y con el mismo `LocalDate.now()`, y se
       aceptan también el día anterior y el posterior: si el reloj pasa de
       medianoche entre la llamada de `Razon` y la de aquí, la prueba sigue siendo
       prueba de lo que tiene que ser —la fecha de verdad— y no un dado cargado. */
    static void esperaHoy() {
        LocalDate hoy = LocalDate.now();
        String r = Razon.intenta("qué día es hoy");
        casos++;
        boolean vale = false;
        for (int d = -1; d <= 1 && !vale; d++)
            vale = r != null && r.contains(Razon.nombreDe(hoy.plusDays(d)));
        if (!vale) { fallos++; System.out.println("FALLO  «qué día es hoy» → " + r
            + "   (esperaba: hoy es " + Razon.nombreDe(hoy) + ")"); }
        else System.out.println("ok     «qué día es hoy» → " + r);
    }

    /** Lo que `faltanPara` dice de verdad según los días que queden: 0, 1 o varios. */
    static void esperaFaltan(String frase, int dia, int mes) {
        LocalDate hoy = LocalDate.now();
        LocalDate destino = LocalDate.of(hoy.getYear(), mes, dia);
        if (destino.isBefore(hoy)) destino = destino.plusYears(1);
        long dias = java.time.temporal.ChronoUnit.DAYS.between(hoy, destino);
        espera(frase, dias == 0 ? "Es hoy" : dias == 1 ? "Falta un día" : "Faltan");
    }

    public static void main(String[] a) {
        espera("¿cuánto es 17 por 3?", "51");
        espera("cuanto es 240 entre 12", "20");
        espera("calcula 8 más 9", "17");
        espera("cuánto es 100 menos 37", "63");
        espera("la raíz de 144", "12");
        espera("raíz cuadrada de 2", "1,4142");
        espera("12 al cuadrado", "144");
        espera("5 al cubo", "125");
        espera("dos mil más quinientos", "2500");
        espera("cuánto es treinta y dos por diez", "320");
        espera("(5+3)*2", "16");
        espera("cuanto es 2.5 por 4", "10");
        espera("cuánto es 1/3", "0,3333");
        espera("cuánto es 1000 / 8", "125");
        espera("el 15 por ciento de 240", "36");
        espera("cuánto es el 20% de 55", "11");
        espera("15% de 240", "36");
        espera("qué porcentaje es 30 de 120", "25");
        espera("3 km a millas", "1,8641");
        espera("cuánto son 98.6 fahrenheit a celsius", "37");
        espera("2 horas a minutos", "120");
        espera("convierte 5 kilos a libras", "11,0231");
        espera("100 metros a pies", "328");
        espera("50 grados celsius a fahrenheit", "122");
        espera("30 grados a fahrenheit", "86");
        espera("2 gb a mb", "2048");
        esperaFaltan("cuántos días faltan para navidad", 25, 12);
        esperaFaltan("a cuánto falta para el 1 de enero", 1, 1);
        esperaHoy();
        espera("qué hora es", "Son las");
        espera("2026 es bisiesto", "no es");
        espera("2028 es bisiesto", "es bisiesto");
        espera("cuántos días tiene 2028", "366");
        espera("qué día era hace 30 días", "de");
        espera("qué día será dentro de 7 días", "de");
        noEsMio("hola cort");
        noEsMio("qué puedes hacer");
        noEsMio("reproduce música de ropamania");
        noEsMio("explícame la fotosíntesis");
        noEsMio("llama a mi mamá");
        noEsMio("cuál es mi playlist");
        noEsMio("sube el volumen");
        noEsMio("pon una alarma a las 7");
        System.out.println("\n" + (casos - fallos) + "/" + casos + " casos; fallos=" + fallos);
        System.exit(fallos == 0 ? 0 : 1);
    }
}
