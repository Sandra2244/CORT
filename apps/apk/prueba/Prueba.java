package com.cort.ia;

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
        espera("cuántos días faltan para navidad", "Faltan");
        espera("a cuánto falta para el 1 de enero", "días");
        espera("qué día es hoy", "miercoles 21 de octubre de 2026");
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
